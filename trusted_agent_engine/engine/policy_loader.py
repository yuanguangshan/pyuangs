import os
import yaml
from typing import Optional
from .types import PolicyConfig
from .sovereign import SovereignManager

def load_policy(path: str, public_key: Optional[str] = None, signature_path: Optional[str] = None,
                allow_unsigned: bool = False) -> PolicyConfig:
    """Load and (by default) verify a policy file.

    Fail-closed: when no public key is available the policy is **not** silently
    accepted — pass ``allow_unsigned=True`` to explicitly opt out.  Without
    that, deleting ``.ai/sovereign.pub`` would disable every guarantee this
    package advertises, with no warning at all.
    """
    if not os.path.exists(path):
        raise FileNotFoundError(f"Policy file not found at {path}")

    with open(path, 'r', encoding='utf-8') as f:
        content = f.read()

    if not public_key and not allow_unsigned:
        raise ValueError(
            f"[Sovereignty] No public key provided for {path}. "
            "Refusing to load an unverifiable policy (fail-closed). "
            "Run 'trusted-engine init' to create keys, or pass allow_unsigned=True to opt out."
        )

    if public_key:
        sig_path = signature_path or f"{path}.sig"
        if not os.path.exists(sig_path):
            raise ValueError(f"Policy signature missing at {sig_path}. Sovereign requirement not met.")
        
        with open(sig_path, 'r', encoding='utf-8') as f:
            signature = f.read().strip()
            
        is_valid = SovereignManager.verify_policy(content, signature, public_key)
        if not is_valid:
            raise ValueError("Policy signature verification failed. Unauthorized policy modification detected!")

    data = yaml.safe_load(content)
    return PolicyConfig.model_validate(data)
