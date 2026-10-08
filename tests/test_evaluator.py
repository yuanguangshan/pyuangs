"""PolicyEngine 核心行为测试。

覆盖本次修复的全部关键点：
  * evaluate() 不再因 auditLog 字段名崩溃（原 bug：decision.audit_log = ...）
  * 字符串表达式 → fail-closed 拦截而不是抛出/放行
  * 高危动作必须声明 privileges
  * meta.mode=monitor 演练模式只报告不拦截
  * 风险等级取最大值，与 risks 书写顺序无关
  * scope 用 minimatch 语义（src/* 不能穿透到 src/deep/）
  * 异常检测只是信号，是否拦截由策略决定
  * 仁慈钩子失败不发放仁慈
"""
from trusted_agent_engine.engine.evaluator import PolicyEngine
from trusted_agent_engine.engine.types import PolicyConfig, Proposal, ValueManifesto


def prop(files=("src/a.ts",), reasoning="修复登录逻辑中的一个明显问题", diff="+code", tags=None) -> Proposal:
    return Proposal(id="p1", timestamp=1.0, author="human",
                    reasoning=reasoning, files=list(files), diff=diff, tags=tags)


def policy(rules=None, risks=None, scopes=None, mode="strict", privileges=("high-risk-decision",)) -> PolicyConfig:
    meta = {"mode": mode}
    if privileges is not None:
        meta["privileges"] = list(privileges)
    return PolicyConfig.model_validate({
        "meta": meta,
        "scopes": scopes or [{"id": "s", "allow": ["src/**", "docs/**"]}],
        "risks": risks or [],
        "rules": rules or [],
    })


# ---------- 回归：曾经必崩的字段名 ----------

def test_evaluate_returns_audit_log():
    d = PolicyEngine(policy()).evaluate(prop())
    assert d.auditLog                      # 原 bug：decision.audit_log 赋值到不存在的字段
    assert "proposalId" in d.auditLog
    assert d.allowed is True


# ---------- 四态裁决 ----------

def test_block_rule_blocks():
    cfg = policy(rules=[{"id": "no-secrets", "condition": {"==": [{"var": "payload.id"}, "p1"]},
                         "action": "block", "description": "d"}])
    d = PolicyEngine(cfg).evaluate(prop())
    assert d.allowed is False
    assert [v.ruleId for v in d.violations] == ["no-secrets"]


def test_require_human():
    cfg = policy(rules=[{"id": "human", "condition": {"==": [1, 1]},
                         "action": "require_human", "description": "d"}])
    d = PolicyEngine(cfg).evaluate(prop())
    assert d.requiresHuman is True and d.allowed is False


def test_check_rule_fires_when_check_is_false():
    cfg = policy(rules=[{"id": "need-diff", "check": {">": [{"var": "payload.diff.length"}, 0]},
                         "action": "block", "description": "d"}])
    assert PolicyEngine(cfg).evaluate(prop(diff="")).allowed is False
    assert PolicyEngine(cfg).evaluate(prop(diff="+x")).allowed is True


# ---------- privilege 强制 ----------

def test_high_risk_action_without_privilege_is_blocked():
    cfg = policy(rules=[{"id": "r", "condition": {"==": [1, 1]},
                         "action": "block", "description": "d"}], privileges=None)
    d = PolicyEngine(cfg).evaluate(prop())
    assert d.allowed is False
    assert "privilege-violation" in [v.ruleId for v in d.violations]


# ---------- fail-closed：字符串表达式 ----------

def test_string_expression_blocks_instead_of_crashing():
    cfg = policy(rules=[{"id": "legacy", "check": "payload.diff.length > 0",
                         "action": "warn", "description": "legacy"}])
    d = PolicyEngine(cfg).evaluate(prop())
    assert d.allowed is False                       # 拦截，而不是异常或放行
    assert "legacy:eval-error" in [v.ruleId for v in d.violations]


# ---------- monitor 演练模式 ----------

def test_monitor_mode_reports_but_does_not_block():
    cfg = policy(rules=[{"id": "r", "condition": {"==": [1, 1]},
                         "action": "block", "description": "d"}], mode="monitor")
    d = PolicyEngine(cfg).evaluate(prop())
    assert d.allowed is True
    assert d.requiresHuman is False
    assert d.actions == ["warn"]
    assert all(v.level == "warn" for v in d.violations)


# ---------- 风险等级取最大值 ----------

def _risk_engine(risks):
    return PolicyEngine(policy(risks=risks)).evaluate(prop(["src/a.ts"]))

def test_risk_level_is_order_independent():
    high = {"id": "h", "level": "high", "match": ["src/**"]}
    med = {"id": "m", "level": "medium", "match": ["src/*.ts"]}
    assert _risk_engine([high, med]).riskLevel == "high"   # 原 bug：后写的覆盖先写的
    assert _risk_engine([med, high]).riskLevel == "high"


# ---------- scope 的 minimatch 语义 ----------

def test_scope_star_does_not_cross_directories():
    """fnmatch 下 src/* 会放行 src/deep/secret.ts —— 对治理引擎是 fail-open。"""
    cfg = policy(scopes=[{"id": "s", "allow": ["src/*"]}],
                 rules=[{"id": "scope", "check": {"var": "engine.isScoped"},
                         "action": "block", "description": "scope"}])
    assert PolicyEngine(cfg).evaluate(prop(["src/a.ts"])).allowed is True
    assert PolicyEngine(cfg).evaluate(prop(["src/deep/a.ts"])).allowed is False   # 不再穿透


def test_scope_globstar_allows_nested():
    cfg = policy(scopes=[{"id": "s", "allow": ["src/**"]}],
                 rules=[{"id": "scope", "check": {"var": "engine.isScoped"},
                         "action": "block", "description": "scope"}])
    assert PolicyEngine(cfg).evaluate(prop(["src/deep/a.ts"])).allowed is True


# ---------- 异常检测是信号不是裁决 ----------

def test_anomaly_is_signal_unless_policy_acts_on_it():
    big = "line\n" * 600
    many = [f"src/f{i}.ts" for i in range(11)]
    p = prop(files=many, diff=big)
    # 策略没写异常规则 → 只报告，不拦截
    plain = PolicyEngine(policy(scopes=[{"id": "s", "allow": ["src/**"]}])).evaluate(p)
    assert plain.anomalyReport.isAnomaly is True
    assert plain.allowed is True
    # 策略显式接管 → 拦截
    gated = policy(scopes=[{"id": "s", "allow": ["src/**"]}],
                   rules=[{"id": "gate", "condition": {"var": "engine.isAnomaly"},
                           "action": "block", "description": "d"}])
    assert PolicyEngine(gated).evaluate(p).allowed is False


def test_chinese_comments_are_not_an_anomaly():
    """中文注释曾被当成"二进制走私"（非 ASCII > 20 即 +0.6）。"""
    zh = "// 修复登录逻辑，同时补充单元测试用例说明。\n" * 8
    p = prop(diff=zh)
    d = PolicyEngine(policy()).evaluate(p)
    assert d.anomalyReport.score == 0.0
    assert d.anomalyReport.isAnomaly is False


# ---------- 价值与仁慈 ----------

MANIFESTO = ValueManifesto.model_validate({
    "values": [{"id": "security", "weight": 1.0, "description": "d"}],
    "mercy_hooks": [],
})


def test_value_score_drops_for_violated_value():
    cfg = policy(rules=[{"id": "no-secrets", "condition": {"==": [1, 1]}, "action": "block",
                         "description": "d", "valueId": "security"}])
    d = PolicyEngine(cfg, MANIFESTO).evaluate(prop())
    assert d.valueScore is not None and d.valueScore < 1.0


def test_mercy_hook_downgrades_block():
    manifesto = ValueManifesto.model_validate({
        "values": [{"id": "security", "weight": 1.0, "description": "d"}],
        "mercy_hooks": [{"id": "emergency", "action": "downgrade_to_warn",
                         "condition": {"in": ["emergency", {"var": "payload.tags"}]},
                         "description": "d"}],
    })
    cfg = policy(rules=[{"id": "no-secrets", "condition": {"==": [1, 1]}, "action": "block",
                         "description": "d"}])
    assert PolicyEngine(cfg, manifesto).evaluate(prop(tags=["emergency"])).allowed is True
    assert PolicyEngine(cfg, manifesto).evaluate(prop(tags=["normal"])).allowed is False


def test_broken_mercy_hook_grants_no_mercy():
    """仁慈钩子求值失败 = 不发放仁慈（fail-closed），而不是崩掉或直接放行。"""
    manifesto = ValueManifesto.model_validate({
        "values": [],
        "mercy_hooks": [{"id": "bad", "action": "auto_allow",
                         "condition": "this is not json logic", "description": "d"}],
    })
    cfg = policy(rules=[{"id": "no-secrets", "condition": {"==": [1, 1]}, "action": "block",
                         "description": "d"}])
    d = PolicyEngine(cfg, manifesto).evaluate(prop())
    assert d.allowed is False        # 仁慈没有发放


# ---------- 责任归属 ----------

def test_accountability_present_and_typed():
    cfg = policy(rules=[{"id": "r", "condition": {"==": [1, 1]}, "action": "block",
                         "description": "d"}])
    d = PolicyEngine(cfg, workspace_root=None).evaluate(prop())
    assert d.accountability is None            # 没给 workspace 就不落账
    assert d.signatureVerified is None         # 由 TrustedGuard 填写
