import re
from typing import List
from .types import Proposal, AnomalyReport

class AnomalyDetector:
    """
    Executes anomaly detection logic, including:
    1. Size Variance: Flags unusually large diffs.
    2. Obfuscation/Entropy: Detects potential code obfuscation.
    3. Complexity: Checks for excessive number of files modified.
    """
    
    def detect(self, proposal: Proposal) -> AnomalyReport:
        reasons: List[str] = []
        score = 0.0

        # 1. Size Detection
        lines = proposal.diff.split('\n')
        line_count = len(lines)
        if line_count > 500:
            score += 0.4
            reasons.append(f"Unusually large diff ({line_count} lines). Potential smuggling.")

        # 2. Obfuscation Analysis
        if self._detect_obfuscation(proposal.diff):
            score += 0.6
            reasons.append("Possible code obfuscation or binary smuggling detected.")

        # 3. File Dispersion
        if len(proposal.files) > 10:
            score += 0.3
            reasons.append(f"Too many files touched ({len(proposal.files)}). High collateral risk.")

        return AnomalyReport(
            isAnomaly=score >= 0.7,
            score=min(1.0, score),
            reasons=reasons
        )

    def _detect_obfuscation(self, diff: str) -> bool:
        # Check for long hex or base64 patterns
        hex_pattern = r'[0-9a-fA-F]{50,}'
        base64_pattern = r'[A-Za-z0-9+/]{100,}={0,2}'
        
        if re.search(hex_pattern, diff) or re.search(base64_pattern, diff):
            return True

        # Check for excessive non-ASCII characters
        non_ascii_pattern = r'[^\x00-\x7F]'
        matches = re.findall(non_ascii_pattern, diff)
        if matches and len(matches) > 20:
            return True

        return False
