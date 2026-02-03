import time
from typing import List, Set
from .types import DecisionTrace, SelfAuditReport

class SelfAuditor:
    """
    Executes governance self-audit to detect hidden risks in long-term operations.
    """
    
    def audit(self, history: List[DecisionTrace]) -> SelfAuditReport:
        findings = []
        health_score = 100

        if len(history) < 5:
            return SelfAuditReport(
                timestamp=time.time(),
                healthScore=health_score,
                findings=findings
            )

        # 1. Policy Drift Detection
        recent = history[:10]
        older = history[10:30]
        
        if len(older) >= 5:
            recent_rate = sum(1 for t in recent if t.allowed) / len(recent)
            older_rate = sum(1 for t in older if t.allowed) / len(older)

            if abs(recent_rate - older_rate) > 0.4:
                health_score -= 20
                findings.append({
                    "severity": "medium",
                    "type": "policy-drift",
                    "message": f"Decision pattern alignment shifted significantly: {recent_rate:.2f} vs {older_rate:.2f}"
                })

        # 2. Permission Creep Detection
        touched_dirs: Set[str] = set()
        for t in history:
            for f in t.proposal.files:
                touched_dirs.add(self._get_top_dir(f))
        
        if len(touched_dirs) > 15:
            health_score -= 15
            findings.append({
                "severity": "low",
                "type": "permission-creep",
                "message": f"Agent is interacting with a wide variety of directories ({len(touched_dirs)}). Review scope boundaries."
            })

        # 3. Risk Accumulation
        high_risk_count = sum(1 for t in history if t.riskLevel == 'high')
        if high_risk_count / len(history) > 0.3:
            health_score -= 30
            findings.append({
                "severity": "high",
                "type": "risk-accumulation",
                "message": f"High percentage of high-risk operations ({high_risk_count / len(history) * 100:.1f}%). System is under strain."
            })

        return SelfAuditReport(
            timestamp=time.time(),
            healthScore=max(0, health_score),
            findings=findings
        )

    def _get_top_dir(self, file_path: str) -> str:
        parts = file_path.split('/')
        return parts[0] if parts else '.'
