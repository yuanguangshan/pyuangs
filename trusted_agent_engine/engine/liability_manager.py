import os
import json
import hashlib
from typing import Dict, Any, Literal, Optional
from .types import Proposal, Decision, Accountability

class LiabilityManager:
    def __init__(self, workspace_root: str):
        self.ledger_path = os.path.join(workspace_root, '.ai', 'credits.json')
        self._ensure_storage_exists()

    def _ensure_storage_exists(self):
        directory = os.path.dirname(self.ledger_path)
        if not os.path.exists(directory):
            os.makedirs(directory, exist_ok=True)
        if not os.path.exists(self.ledger_path):
            with open(self.ledger_path, 'w', encoding='utf-8') as f:
                json.dump({"agentCredits": 100}, f, indent=2)

    def generate_signature(self, proposal: Proposal, decision: Decision) -> str:
        data = {
            "p": proposal.id,
            "f": proposal.files,
            "v": [v.ruleId for v in decision.violations],
            "a": decision.allowed
        }
        encoded = json.dumps(data, sort_keys=True).encode('utf-8')
        return hashlib.sha256(encoded).hexdigest()[:16]

    def attribute(self, decision: Decision) -> Literal['ai-agent', 'human-approver', 'policy-author', 'system-fault']:
        # Logic hole detection
        if not decision.allowed and not decision.violations:
            if decision.anomalyReport and decision.anomalyReport.isAnomaly:
                return 'policy-author'
            return 'system-fault'

        if not decision.allowed:
            if 'require_human' in decision.actions:
                return 'human-approver'
            return 'ai-agent'
        
        if decision.violations:
            return 'policy-author'
        
        return 'ai-agent'

    def calculate_credit_impact(self, decision: Decision) -> float:
        if decision.allowed:
            return 1.0
        if decision.riskLevel == 'high':
            return -10.0
        return -2.0

    def update_credits(self, impact: float) -> float:
        with open(self.ledger_path, 'r+', encoding='utf-8') as f:
            data = json.load(f)
            data['agentCredits'] += impact
            f.seek(0)
            json.dump(data, f, indent=2)
            f.truncate()
            return data['agentCredits']

    def get_credits(self) -> float:
        with open(self.ledger_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            return data['agentCredits']
