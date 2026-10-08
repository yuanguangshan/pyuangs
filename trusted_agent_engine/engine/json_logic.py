"""Safe, dependency-free JSON Logic for Python 3.

Why this exists
---------------
The published ``json-logic==0.6.3`` package is Python 2 era code:
``tests.keys()[0]`` raises ``TypeError: 'dict_keys' object is not subscriptable``
on Python 3, and it calls ``reduce`` without importing it.  Every rule
evaluation therefore failed and was silently swallowed as ``False`` by the
caller — meaning ``condition`` rules never fired and ``check`` rules always
fired.  We implement the semantics ourselves (a small, auditable subset of
https://json-logic.com/) instead of depending on unmaintained code.

Safety
------
No ``eval`` / ``exec`` / ``compile``: every operator is a plain function in a
dict, so a policy file cannot execute arbitrary code.  Recursion depth is
bounded so a handcrafted rule tree cannot blow the stack.
"""

from __future__ import annotations

from typing import Any, Callable, Dict, List, Optional

__all__ = ["json_logic", "JsonLogicError", "MAX_DEPTH"]

MAX_DEPTH = 50


class JsonLogicError(ValueError):
    """Raised when a rule cannot be evaluated (unknown operator, bad arity...)."""


def _is_number(v: Any) -> bool:
    return isinstance(v, (int, float)) and not isinstance(v, bool)


def _to_number(v: Any) -> Optional[float]:
    """Best-effort numeric coercion, mirroring how JSON Logic coerces scalars."""
    if _is_number(v):
        return float(v)
    if isinstance(v, bool):
        return 1.0 if v else 0.0
    if isinstance(v, str):
        try:
            return float(v.strip())
        except (TypeError, ValueError):
            return None
    if v is None:
        return 0.0
    return None


def _cmp(op: Callable[[Any, Any], bool], a: Any, b: Any) -> bool:
    """Compare with numeric coercion, falling back to identity/equality."""
    if _is_number(a) or _is_number(b) or (a is None or b is None):
        na, nb = _to_number(a), _to_number(b)
        if na is not None and nb is not None:
            return op(na, nb)
    if isinstance(a, str) and isinstance(b, str):
        return op(a, b)
    # 无法比较的类型（如 dict/list vs 标量）按 JSON Logic 的宽松语义走相等性
    return op(a, b) if type(a) is type(b) else op(a, b)


def _truthy(v: Any) -> bool:
    """Truthy semantics close to JS: '' / 0 / null / false are falsy."""
    if v is None or v is False:
        return False
    if _is_number(v):
        return v != 0
    if isinstance(v, str):
        return v != ""
    if isinstance(v, (list, tuple, dict, set)):
        return len(v) > 0
    return bool(v)


def _get_var(data: Any, path: str, not_found: Any = None) -> Any:
    """``var`` operator: dotted path lookup, tolerant of lists/dicts."""
    if path in ("", None):
        return data
    cur = data
    for key in str(path).split("."):
        if isinstance(cur, dict):
            if key in cur:
                cur = cur[key]
            elif key == "length":
                # JS 语义：obj.length
                cur = len(cur)
            else:
                return not_found
        elif isinstance(cur, str):
            # JS 语义：str.length —— 自带策略用 payload.diff.length 判空
            if key == "length":
                cur = len(cur)
            else:
                return not_found
        elif isinstance(cur, (list, tuple)):
            if key == "length":
                cur = len(cur)
            elif key.lstrip("-").isdigit():
                idx = int(key)
                if -len(cur) <= idx < len(cur):
                    cur = cur[idx]
                else:
                    return not_found
            else:
                return not_found
        else:
            return not_found
    return cur


def _reduce(op: str, args: List[Any]) -> Any:
    """``and`` / ``or`` short-circuit like the JS reference implementation."""
    if op == "and":
        last: Any = True
        for a in args:
            last = a
            if not _truthy(a):
                return a
        return last
    last = False
    for a in args:
        last = a
        if _truthy(a):
            return a
    return last


def _flat(args: List[Any]) -> List[Any]:
    out: List[Any] = []
    for a in args:
        if isinstance(a, (list, tuple)):
            out.extend(_flat(list(a)))
        else:
            out.append(a)
    return out


def _math(op: str, args: List[Any]) -> Any:
    nums = [_to_number(a) or 0.0 for a in args]
    if op == "+":
        total = 0.0
        for n in nums:
            total += n
        return total
    if op == "*":
        total = 1.0
        for n in nums:
            total *= n
        return total
    if op == "-":
        return -nums[0] if len(nums) == 1 else nums[0] - nums[1]
    if op == "*":  # pragma: no cover - unreachable guard
        return 0.0
    if op == "/":
        divisor = nums[1] if len(nums) > 1 else 1.0
        if divisor == 0:
            raise JsonLogicError("division by zero")
        return nums[0] / divisor
    if op == "%":
        divisor = nums[1] if len(nums) > 1 else 1.0
        if divisor == 0:
            raise JsonLogicError("modulo by zero")
        return nums[0] % divisor
    raise JsonLogicError(f"unknown math operator: {op}")


OPERATORS: Dict[str, Callable[[List[Any], Any], Any]] = {
    "==": (lambda a, d: len(a) > 1 and _cmp(lambda x, y: x == y, a[0], a[1])),
    "===": (lambda a, d: len(a) > 1 and a[0] is a[1]),
    "!=": (lambda a, d: len(a) > 1 and not _cmp(lambda x, y: x == y, a[0], a[1])),
    "!==": (lambda a, d: len(a) > 1 and a[0] is not a[1]),
    ">": (lambda a, d: len(a) > 1 and _cmp(lambda x, y: x > y, a[0], a[1])),
    ">=": (lambda a, d: len(a) > 1 and _cmp(lambda x, y: x >= y, a[0], a[1])),
    "<": (lambda a, d: len(a) > 1 and _cmp(lambda x, y: x < y, a[0], a[1])),
    "<=": (lambda a, d: len(a) > 1 and _cmp(lambda x, y: x <= y, a[0], a[1])),
    "!": (lambda a, d: not _truthy(a[0] if a else None)),
    "!!": (lambda a, d: _truthy(a[0] if a else None)),
    "and": (lambda a, d: _reduce("and", a)),
    "or": (lambda a, d: _reduce("or", a)),
    "?:" : (lambda a, d: a[1] if _truthy(a[0]) else (a[2] if len(a) > 2 else None)),
    "if": (lambda a, d: a[1] if _truthy(a[0]) else (a[2] if len(a) > 2 else None)),
    "in": (lambda a, d: a[0] in a[1] if isinstance(a[1], (list, tuple, str, dict)) and len(a) > 1 else False),
    "not in": (lambda a, d: not (a[0] in a[1]) if isinstance(a[1], (list, tuple, str, dict)) and len(a) > 1 else True),
    "cat": (lambda a, d: "".join("" if x is None else str(x) for x in _flat(a))),
    "substr": (lambda a, d: str(a[0])[a[1]: a[2] if len(a) > 2 and a[2] is not None else None]),
    "merge": (lambda a, d: _flat(a)),
    "missing": (lambda a, d: [k for k in a if _get_var(d, k) is None]),
    "missing_some": (lambda a, d: [] if len([k for k in (a[1] or []) if _get_var(d, k) is not None]) >= a[0]
                    else [k for k in (a[1] or []) if _get_var(d, k) is None]),
    "+": (lambda a, d: _math("+", a)),
    "-": (lambda a, d: _math("-", a)),
    "*": (lambda a, d: _math("*", a)),
    "/": (lambda a, d: _math("/", a)),
    "%": (lambda a, d: _math("%", a)),
}
# 无条件求值的特殊算子（其入参需先完成递归求值）
SPECIAL_OPS = {"var", "missing", "missing_some"}


def json_logic(rule: Any, data: Any = None, _depth: int = 0) -> Any:
    """Evaluate ``rule`` against ``data``.  Raises :class:`JsonLogicError` on failure."""
    if _depth > MAX_DEPTH:
        raise JsonLogicError(f"rule nesting exceeds {MAX_DEPTH} levels")

    # 标量直接返回（JSON Logic 的字面量语义）
    if rule is None or not isinstance(rule, dict):
        return rule
    if not rule:
        return None

    op, args = next(iter(rule.items()))
    if not isinstance(args, list):
        args = [args]

    if op == "var":
        path = args[0] if args else ""
        not_found = args[1] if len(args) > 1 else None
        return _get_var(data, path, not_found)

    if op in ("missing", "missing_some"):
        # 这两个算子的入参是"字段名"，不做递归求值
        return OPERATORS[op](args, data)

    if op not in OPERATORS:
        raise JsonLogicError(f"unknown operator: {op!r}")

    resolved = [json_logic(a, data, _depth + 1) for a in args]
    return OPERATORS[op](resolved, data)
