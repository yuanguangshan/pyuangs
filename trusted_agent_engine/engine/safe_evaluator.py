from typing import Any, Dict
import json_logic

class SafeEvaluator:
    """
    v1.1 Safe Evaluator
    Uses JSON Logic to prevent RCE attacks and allow static auditing.
    """
    
    @staticmethod
    def evaluate(expression: Any, context: Dict[str, Any]) -> bool:
        """
        Executes expression evaluation using JSON Logic.
        """
        if isinstance(expression, str):
            # v1.1 Hardening: Disable string expressions to eliminate RCE backdoors
            raise ValueError(
                f"[Governance Critical] String-based policy conditions are disabled for security. "
                f"Detected unsafe condition: '{expression}'. Please migrate to JSON Logic."
            )

        try:
            return bool(json_logic.jsonLogic(expression, context))
        except Exception as e:
            print(f"[Governance Error] Failed to evaluate JSON Logic: {e}")
            return False
