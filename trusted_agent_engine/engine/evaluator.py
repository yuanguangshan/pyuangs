import json
import fnmatch
from typing import List, Optional, Any, Dict
from .types import Proposal, PolicyConfig, Decision, Violation, ValueManifesto, Accountability, AnomalyReport
from .anomaly_detector import AnomalyDetector
from .liability_manager import LiabilityManager
from .safe_evaluator import SafeEvaluator

class PolicyEngine:
    def __init__(self, policy: PolicyConfig, manifesto: Optional[ValueManifesto] = None, workspace_root: Optional[str] = None):
        self.policy = policy
        self.manifesto = manifesto
        self.anomaly_detector = AnomalyDetector()
        self.liability = LiabilityManager(workspace_root) if workspace_root else None

    def evaluate(self, proposal: Proposal) -> Decision:
        violations: List[Violation] = []
        actions: List[str] = []

        # -----------------------------
        # 1. Signals Preparation
        # -----------------------------
        risk_level = 'low'
        for risk in self.policy.risks:
            for pattern in risk.match:
                if any(fnmatch.fnmatch(f, pattern) for f in proposal.files):
                    risk_level = risk.level
                    break

        anomaly_report = self.anomaly_detector.detect(proposal)
        
        evaluation_context = {
            "payload": proposal.model_dump(),
            "engine": {
                "riskLevel": risk_level,
                "isAnomaly": anomaly_report.isAnomaly,
                "anomalyScore": anomaly_report.score,
                "isOnlyDocs": all(f.endswith('.md') or f.startswith('docs/') for f in proposal.files),
                "isScoped": self._is_within_scope(proposal.files),
            },
            "anomaly": anomaly_report.model_dump()
        }

        # -----------------------------
        # 2. Rule Evaluation
        # -----------------------------
        for rule in self.policy.rules:
            # condition: if matched, execute action
            if rule.condition:
                if SafeEvaluator.evaluate(rule.condition, evaluation_context):
                    self._apply_rule_action(rule, actions, violations)

            # check: if NOT matched, execute action
            if rule.check:
                if not SafeEvaluator.evaluate(rule.check, evaluation_context):
                    self._apply_rule_action(rule, actions, violations)

        # -----------------------------
        # 3. Value & Mercy
        # -----------------------------
        value_score = 1.0
        if self.manifesto:
            # Calculate value score
            for v in violations:
                rule = next((r for r in self.policy.rules if r.id == v.ruleId), None)
                if rule and rule.valueId:
                    val_item = next((vi for vi in self.manifesto.values if vi.id == rule.valueId), None)
                    if val_item:
                        v.valueWeight = val_item.weight
                        value_score -= (val_item.weight * 0.2)

            # Mercy hooks
            for hook in self.manifesto.mercy_hooks:
                if SafeEvaluator.evaluate(hook.condition, evaluation_context):
                    if hook.action == 'downgrade_to_warn':
                        actions = ['warn' if a in ('block', 'require_human') else a for a in actions]
                        for v in violations:
                            v.level = 'warn'
                    elif hook.action == 'auto_allow':
                        actions = []
                        violations = []
                        break

        # -----------------------------
        # 4. Final Decision
        # -----------------------------
        is_hard_blocked = 'block' in actions
        requires_human = 'require_human' in actions

        decision = Decision(
            allowed=not is_hard_blocked and not requires_human,
            requiresHuman=requires_human,
            riskLevel=risk_level,
            actions=actions,
            violations=violations,
            valueScore=max(0.0, value_score),
            anomalyReport=anomaly_report,
            auditLog=""
        )

        if self.liability:
            responsible_entity = self.liability.attribute(decision)
            credit_impact = self.liability.calculate_credit_impact(decision)
            
            decision.accountability = Accountability(
                responsibleEntity=responsible_entity,
                signature=self.liability.generate_signature(proposal, decision),
                creditImpact=credit_impact
            )
            
            if responsible_entity != 'system-fault':
                self.liability.update_credits(credit_impact)

        decision.audit_log = self._build_audit_log(proposal, actions, violations)

        if self.policy.requiresConsensus:
            raise RuntimeError(
                'Policy requires consensus, but consensus enforcement is not yet active in Python v2.0. '
                'Please disable requiresConsensus or implement consensus flow.'
            )

        return decision

    def _apply_rule_action(self, rule: Any, actions: List[str], violations: List[Violation]):
        high_risk_actions = ['block', 'require_human']
        
        # Privilege check
        privileges = self.policy.meta.get('privileges', [])
        if rule.action in high_risk_actions and 'high-risk-decision' not in privileges:
            violations.append(Violation(
                ruleId='privilege-violation',
                description=f'Policy rule "{rule.id}" lacks privilege for action: {rule.action}.',
                level='block'
            ))
            actions.append('block')
            return

        actions.append(rule.action)
        level = 'block' if rule.action in high_risk_actions else 'warn'
        violations.append(Violation(
            ruleId=rule.id,
            description=rule.description or rule.id,
            level=level
        ))

    def _is_within_scope(self, files: List[str]) -> bool:
        allowed_patterns = [p for s in self.policy.scopes for p in s.allow]
        return all(any(fnmatch.fnmatch(f, p) for p in allowed_patterns) for f in files)

    def _build_audit_log(self, proposal: Proposal, actions: List[str], violations: List[Violation]) -> str:
        return json.dumps({
            "proposalId": proposal.id,
            "timestamp": proposal.timestamp,
            "actions": actions,
            "violations": [v.model_dump() for v in violations]
        }, indent=2)
