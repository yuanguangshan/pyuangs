# Trusted AI Agent Governance Engine (TAAGE) 🛡️

TAAGE 是一个专为 AI 代理设计的、具备**主权意识**与**自我演进**能力的治理引擎。它通过物理脱钩的规则热加载、Ed25519 签名校验、以及信用分博弈机制，为 AI 行为提供坚实的防御边界。

[English Version](README_EN.md)

## 🌟 核心理念

1. **主权先于智能 (Sovereignty Over Intelligence)**: 只有拥有私钥的人类才是项目的最高统帅，AI 的规则修改必须经过主权者签名。
2. **信任但不放任 (Trust, but Verify)**: 每一行 Diff 都会经过多层感知引擎（异常检测、熵值分析、风险匹配）的剥离审查。
3. **自我感知 (Self-Audit)**: 系统会自动监控治理健康度，识别性能漂移与权限蔓延。

---

## 🚀 快速开始 (Python)

### 1. 安装 (Installation)

```bash
pip install trusted-agent-engine
```

### 2. 初始化主权密钥 (Init Sovereignty)

生成属于你的治理身份：

```bash
trusted-engine init
```

- `.ai/sovereign.key`: 你的主权私钥（**绝不要提交到 Git**）。
- `.ai/sovereign.pub`: 你的主权公钥。

### 3. 配置并签署政策 (Sign Policy)

创建 `agent.policy.yaml`，并使用私钥签署它，确保规则不被 AI 篡改：

```bash
# 1. 编写规则
cat > agent.policy.yaml <<EOF
meta:
  mode: strict
  privileges: ["high-risk-decision"]
scopes:
  - id: "src"
    allow: ["src/**"]
rules:
  - id: "scope-enforcement"
    check: {"!": {"var": "engine.isScoped"}}
    action: "block"
    description: "Unauthorized file access detected"
EOF

# 2. 物理签署
trusted-engine sign agent.policy.yaml
```

---

## 🛠 本地集成 (Integration Guide)

### 姿势 A：一键式封装集成 (Python)

```python
import asyncio
from trusted_agent_engine import TrustedGuard, Proposal

async def main():
    proposal = Proposal(
        id='p-001',
        author='ai-agent',
        reasoning='Update user login logic',
        files=['src/auth.py'],
        diff='... standard git diff ...'
    )

    # 一键评估：自动加载政策、校验签名、执行审计并记录日志
    decision = await TrustedGuard.evaluate("./", proposal)

    if not decision.allowed:
        print(f"🚫 拦截原因: {decision.audit_log}")
        return

    print(f"✅ 准入通过，价值得分: {decision.valueScore}")

if __name__ == "__main__":
    asyncio.run(main())
```

### 姿势 B：CLI 级联拦截

在你的 AI Agent 运行任务前执行：

```bash
# 如果是中国区 AI，可以标记 author 为 ai
trusted-engine check --author=ai
```

---

## 🌐 API 服务模式

你可以启动一个独立的治理网关：

```bash
trusted-engine serve
```

默认运行在 `http://localhost:3000`。

---

## 📊 治理洞察 (Insights)

引擎运行一段时间后，会自动发现：

- **Trusted Patterns**: AI 经常成功修改的路径，会建议你提拔为信任域。
- **Frequent Violations**: 频繁被拦下的规则，会建议你加强硬化。

所有洞察均存储在 `.ai/governance_assets.json`。

---

## ⚖️ 许可证

基于 MIT 协议分发。开发者拥有对 AI 的最高指挥权。
