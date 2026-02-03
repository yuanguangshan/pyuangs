import os
import yaml
from typing import Optional
from .types import PolicyConfig
from .sovereign import SovereignManager

def load_policy(path: str, public_key: Optional[str] = None, signature_path: Optional[str] = None) -> PolicyConfig:
    if not os.path.exists(path):
        raise FileNotFoundError(f"Policy file not found at {path}")

    with open(path, 'r', encoding='utf-8') as f:
        content = f.read()

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
