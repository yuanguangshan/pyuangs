"""SafeEvaluator：字符串表达式拒绝 + 求值失败 fail-closed。"""
import pytest

from trusted_agent_engine.engine.safe_evaluator import (
    PolicyEvaluationError,
    SafeEvaluator,
)


def test_string_expression_rejected():
    """旧版用 eval 执行字符串条件 —— 这是 RCE 后门，必须直接拒绝。"""
    with pytest.raises(PolicyEvaluationError) as err:
        SafeEvaluator.evaluate("process.exit(1)", {})
    assert "disabled" in str(err.value)
    # 抛错而不是返回 False：返回 False 对 condition 规则就是 fail-open
    with pytest.raises(PolicyEvaluationError):
        SafeEvaluator.evaluate("engine.riskLevel == 'high'", {"engine": {"riskLevel": "high"}})


def test_non_dict_expression_rejected():
    with pytest.raises(PolicyEvaluationError):
        SafeEvaluator.evaluate(12345, {})


def test_json_logic_object_evaluates():
    ctx = {"engine": {"riskLevel": "high"}, "payload": {"files": ["src/a.ts"], "isScoped": True}}
    assert SafeEvaluator.evaluate({"==": [{"var": "engine.riskLevel"}, "high"]}, ctx) is True
    assert SafeEvaluator.evaluate({"var": "payload.isScoped"}, ctx) is True
    assert SafeEvaluator.evaluate({"==": [{"var": "engine.riskLevel"}, "low"]}, ctx) is False


def test_unknown_operator_raises_instead_of_returning_false():
    """以前任何异常都 return False（= 条件不成立 = 放行），现在必须抛。"""
    with pytest.raises(PolicyEvaluationError) as err:
        SafeEvaluator.evaluate({"unknown_op": [1, 2]}, {})
    assert "fail-closed" in str(err.value)


def test_expression_errors_are_policy_errors_not_raw_errors():
    with pytest.raises(PolicyEvaluationError):
        SafeEvaluator.evaluate({"/": [1, 0]}, {})   # 除零
