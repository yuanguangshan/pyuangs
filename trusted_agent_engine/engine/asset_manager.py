import time
from typing import List, Dict
from .types import DecisionTrace, GovernanceAsset

class AssetManager:
    """
    Transforms raw traces into governance assets.
    """
    
    def mine(self, history: List[DecisionTrace]) -> List[GovernanceAsset]:
        assets: List[GovernanceAsset] = []
        violation_map: Dict[str, int] = {}
        success_map: Dict[str, int] = {}

        for trace in history:
            if trace.allowed:
                for f in trace.proposal.files:
                    pattern = self._get_dir_pattern(f)
                    success_map[pattern] = success_map.get(pattern, 0) + 1
            else:
                for v in trace.violations:
                    files_str = ",".join(trace.proposal.files)
                    key = f"{v.ruleId}:{files_str}"
                    violation_map[key] = violation_map.get(key, 0) + 1

        # 1. Frequent Violations (Threshold: 3)
        for key, count in violation_map.items():
            if count >= 3:
                rule_id, files = key.split(':', 1)
                assets.append(GovernanceAsset(
                    id=f"asset-harden-{int(time.time())}-{len(assets)}",
                    type='frequent-violation',
                    description=f"Rule {rule_id} violated {count} times on {files}",
                    evidenceCount=count,
                    suggestedAction='harden-rule',
                    pattern=files
                ))

        # 2. Frequent Successes (Threshold: 5)
        for pattern, count in success_map.items():
            if count >= 5:
                assets.append(GovernanceAsset(
                    id=f"asset-promote-{int(time.time())}-{len(assets)}",
                    type='trusted-pattern',
                    description=f"Pattern {pattern} successfully applied {count} times.",
                    evidenceCount=count,
                    suggestedAction='promote-to-scope',
                    pattern=pattern
                ))

        return assets

    def _get_dir_pattern(self, file_path: str) -> str:
        parts = file_path.split('/')
        if len(parts) <= 1:
            return '*'
        return f"{'/'.join(parts[:-1])}/**"
