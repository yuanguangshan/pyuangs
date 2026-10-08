from typing import Any, Dict

from .json_logic import JsonLogicError, json_logic


class PolicyEvaluationError(ValueError):
    """A policy condition could not be evaluated.

    Callers must treat this as **fail-closed** (block), never as "condition
    false" — because ``condition: false`` means "rule does not fire", which
    would let a broken rule silently open the gate.
    """

    def __init__(self, expression: Any, message: str):
        super().__init__(message)
        self.expression = expression


class SafeEvaluator:
    """
    v1.1 Safe Evaluator
    Uses JSON Logic to prevent RCE attacks and allow static auditing.

    Fail-closed contract:
      * string expressions are rejected outright (they used to be ``eval``'d);
      * any evaluation error raises :class:`PolicyEvaluationError`
        instead of returning ``False``.
    """

    @staticmethod
    def evaluate(expression: Any, context: Dict[str, Any]) -> bool:
        """Execute expression evaluation using JSON Logic."""
        if isinstance(expression, str):
            # v1.1 Hardening: Disable string expressions to eliminate RCE backdoors
            raise PolicyEvaluationError(
                expression,
                "[Governance Critical] String-based policy conditions are disabled for security. "
                f"Detected unsafe condition: '{expression}'. Please migrate to JSON Logic.",
            )

        if not isinstance(expression, dict):
            raise PolicyEvaluationError(
                expression,
                "[Governance Critical] Rule must be a JSON Logic object, "
                f"got {type(expression).__name__}.",
            )

        try:
            return bool(json_logic(expression, context))
        except JsonLogicError as e:
            raise PolicyEvaluationError(
                expression,
                f"[Governance Critical] Rule evaluation failed (fail-closed): {e}",
            )
        except Exception as e:  # 防御性：绝不把异常吞成 False
            raise PolicyEvaluationError(
                expression,
                f"[Governance Critical] Rule evaluation failed (fail-closed): {e}",
            )
