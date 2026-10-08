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

        # 只检查真正的不可见/控制字符（零宽、Bidi 覆写、控制码）。
        # 不能用"非 ASCII"当混淆信号：中文/日文注释是正常内容，
        # 本项目通篇中文，用 non-ASCII 会把合法改动误判成"二进制走私"。
        invisible_pattern = (r'[\u0000-\u0008\u000B\u000C\u000E-\u001F\u007F-\u009F'
                             r'\u00AD\u200B-\u200F\u202A-\u202E\u2060-\u2064'
                             r'\u2066-\u2069\uFEFF]')
        matches = re.findall(invisible_pattern, diff)
        if matches and len(matches) > 20:
            return True

        return False
