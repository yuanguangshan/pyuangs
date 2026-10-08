"""内置 JSON Logic 实现的单元测试。

这个模块替换了 Py2 时代的 json-logic==0.6.3（它在 Py3 上 100% 抛错），
所以这里既要覆盖正常算子，也要覆盖失败路径（必须抛错，不能吞）。
"""
import pytest

from trusted_agent_engine.engine.json_logic import (
    JsonLogicError,
    MAX_DEPTH,
    json_logic,
)


def test_literals_pass_through():
    assert json_logic(True) is True
    assert json_logic(42) == 42
    assert json_logic(None) is None
    assert json_logic({}) is None


def test_var_simple_and_dotted():
    data = {"payload": {"files": ["src/a.ts"], "reasoning": "long enough"}, "n": 3}
    assert json_logic({"var": "payload.reasoning"}, data) == "long enough"
    assert json_logic({"var": "payload.files.0"}, data) == "src/a.ts"
    assert json_logic({"var": "missing.path"}, data) is None
    assert json_logic({"var": "payload.files.9"}, data) is None


def test_var_default_value():
    data = {}
    assert json_logic({"var": ["nope", "fallback"]}, data) == "fallback"


def test_comparisons_numeric_coercion():
    assert json_logic({">": [5, 3]}) is True
    assert json_logic({">": ["5", 3]}) is True          # 数字字符串按 JS 语义强转
    assert json_logic({"<=": [3, 3]}) is True
    assert json_logic({"==": [1, "1"]}) is True
    assert json_logic({"===": [1, "1"]}) is False        # 严格比较不强转
    assert json_logic({"!=": [1, 2]}) is True
    assert json_logic({"!==": [1, "1"]}) is True


def test_boolean_operators():
    assert json_logic({"!": [False]}) is True
    assert json_logic({"and": [True, 1, "x"]}) == "x"    # JS 语义：返回最后一个真值
    assert json_logic({"and": [True, 0, "x"]}) == 0      # 遇到假值短路返回它
    assert json_logic({"or": [False, 0, "v"]}) == "v"
    assert json_logic({"or": [False, False]}) is False


def test_if_and_in():
    assert json_logic({"if": [{"var": "x"}, "yes", "no"]}, {"x": 1}) == "yes"
    assert json_logic({"if": [{"var": "x"}, "yes", "no"]}, {"x": 0}) == "no"
    assert json_logic({"in": ["emergency", ["emergency", "drill"]]}) is True
    assert json_logic({"in": ["nope", ["emergency"]]}) is False
    assert json_logic({"not in": ["nope", ["emergency"]]}) is True


def test_arithmetic():
    assert json_logic({"+": [1, 2, 3]}) == 6
    assert json_logic({"-": [10, 4]}) == 6
    assert json_logic({"-": [5]}) == -5
    assert json_logic({"*": [2, 3]}) == 6
    assert json_logic({"/": [10, 4]}) == 2.5
    assert json_logic({"%": [10, 3]}) == 1


def test_string_ops_and_missing():
    assert json_logic({"cat": ["a", 1, None]}) == "a1"
    assert json_logic({"merge": [[1, 2], [3]]}) == [1, 2, 3]
    data = {"a": 1, "b": None}
    assert json_logic({"missing": ["a", "b", "c"]}, data) == ["b", "c"]
    assert json_logic({"missing_some": [1, ["a", "c"]]}, data) == []


def test_unknown_operator_raises():
    with pytest.raises(JsonLogicError):
        json_logic({"definitely_not_an_op": [1]}, {})


def test_division_by_zero_raises():
    with pytest.raises(JsonLogicError):
        json_logic({"/": [1, 0]})


def test_depth_limit_blocks_runaway_rules():
    rule = {"var": "x"}
    for _ in range(MAX_DEPTH + 10):
        rule = {"if": [True, rule, False]}
    with pytest.raises(JsonLogicError):
        json_logic(rule, {"x": 1})
