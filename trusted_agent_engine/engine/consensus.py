from typing import List, Set
from .types import Vote, ConsensusResult, Decision, Violation

class ConsensusEngine:
    """
    ConsensusEngine implements multi-party decision making.
    Rules:
    1. Veto: If any high-weight voter blocks, the whole thing is blocked.
    2. Weighted Average: Calculates approval rating based on weights.
    """
    
    def resolve(self, votes: List[Vote]) -> ConsensusResult:
        if not votes:
            raise ValueError("No votes provided for consensus")

        voters = [v.voterId for v in votes]
        is_vetoed = False
        total_weight = 0.0
        allowed_weight = 0.0

        all_violations: List[Violation] = []
        all_actions: List[str] = []
        max_risk_score = 0
        risk_map = {'high': 3, 'medium': 2, 'low': 1}
        score_to_risk = {3: 'high', 2: 'medium', 1: 'low', 0: 'low'}

        total_value_score = 0.0

        for vote in votes:
            d = vote.decision
            total_weight += vote.weight
            total_value_score += (d.valueScore or 0.0) * vote.weight

            # Track risk level
            current_score = risk_map.get(d.riskLevel, 0)
            if current_score > max_risk_score:
                max_risk_score = current_score

            all_violations.extend(d.violations)
            all_actions.extend(d.actions)

            # Veto logic
            if not d.allowed and vote.weight >= 0.5:
                is_vetoed = True

            if d.allowed:
                allowed_weight += vote.weight

        agreement_rate = allowed_weight / total_weight if total_weight > 0 else 0.0
        final_allowed = not is_vetoed and agreement_rate > 0.6

        # Build final decision
        final_decision = Decision(
            allowed=final_allowed,
            requiresHuman=any(v.decision.requiresHuman for v in votes),
            riskLevel=score_to_risk.get(max_risk_score, 'low'),
            actions=list(set(all_actions)),
            violations=self._unique_violations(all_violations),
            valueScore=total_value_score / total_weight if total_weight > 0 else 0.0,
            auditLog=f"Consensus reached by {len(votes)} voters. Rate: {agreement_rate:.2f}"
        )

        return ConsensusResult(
            finalDecision=final_decision,
            agreementRate=agreement_rate,
            isVetoed=is_vetoed,
            voters=voters
        )

    def _unique_violations(self, violations: List[Violation]) -> List[Violation]:
        seen: Set[str] = set()
        unique = []
        for v in violations:
            key = f"{v.ruleId}-{v.level}"
            if key not in seen:
                seen.add(key)
                unique.append(v)
        return unique
