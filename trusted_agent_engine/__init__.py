import os
import yaml
import asyncio
from typing import Optional

from .engine.evaluator import PolicyEngine
from .engine.policy_loader import load_policy
from .engine.types import Proposal, Decision, ValueManifesto, DecisionTrace
from .engine.context_bank import ContextBank
from .engine.sovereign import SovereignManager
from .engine.diff_parser import parse_unified_diff
from .engine.asset_manager import AssetManager
from .engine.anomaly_detector import AnomalyDetector
from .engine.self_audit import SelfAuditor

__all__ = [
    'PolicyEngine',
    'load_policy',
    'Proposal',
    'Decision',
    'ValueManifesto',
    'DecisionTrace',
    'ContextBank',
    'SovereignManager',
    'parse_unified_diff',
    'AssetManager',
    'AnomalyDetector',
    'SelfAuditor',
    'TrustedGuard'
]

class TrustedGuard:
    """
    TrustedGuard - High-level integration wrapper.
    Provides "zero-config" rapid governance capability for other projects.
    """
    
    @staticmethod
    async def evaluate(workspace_root: str, proposal: Proposal) -> Decision:
        """
        One-click decision check.
        """
        policy_path = os.path.join(workspace_root, 'agent.policy.yaml')
        manifesto_path = os.path.join(workspace_root, 'value_manifesto.yaml')
        pub_key_path = os.path.join(workspace_root, '.ai', 'sovereign.pub')

        # 1. Load sovereign public key (if exists)
        public_key = None
        if os.path.exists(pub_key_path):
            with open(pub_key_path, 'r', encoding='utf-8') as f:
                public_key = f.read()

        # 2. Load policy (with signature verification)
        config = load_policy(policy_path, public_key=public_key)

        # 3. Load manifesto (optional)
        manifesto = None
        if os.path.exists(manifesto_path):
            with open(manifesto_path, 'r', encoding='utf-8') as f:
                data = yaml.safe_load(f)
                manifesto = ValueManifesto.model_validate(data)

        # 4. Execute evaluation
        engine = PolicyEngine(config, manifesto, workspace_root)
        decision = engine.evaluate(proposal)

        # 5. Record trace to ContextBank
        bank = ContextBank(workspace_root)
        trace = DecisionTrace(
            **decision.model_dump(),
            proposal=proposal,
            outcome='applied' if decision.allowed else 'rejected'
        )
        
        # We can't easily do fire-and-forget in sync-looking code unless we use a background task
        # But for simplicity in Python, we'll just await it or wrap it.
        await bank.record(trace)

        return decision
