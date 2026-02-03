from __future__ import annotations
from typing import List, Optional, Literal, Any, Dict, Union
from pydantic import BaseModel, Field
import time

class Proposal(BaseModel):
    id: str
    timestamp: float = Field(default_factory=time.time)
    author: Literal['ai-agent', 'human']
    reasoning: str
    files: List[str]
    diff: str
    tags: Optional[List[str]] = None

class ScopeConfig(BaseModel):
    id: str
    allow: List[str]

class RiskConfig(BaseModel):
    id: str
    level: Literal['low', 'medium', 'high']
    match: List[str]

class RuleConfig(BaseModel):
    id: str
    check: Optional[Any] = None
    condition: Optional[Any] = None
    action: Literal['allow', 'warn', 'block', 'require_human']
    description: str
    valueId: Optional[str] = None

class PolicyConfig(BaseModel):
    meta: Dict[str, Any]
    scopes: List[ScopeConfig]
    risks: List[RiskConfig]
    rules: List[RuleConfig]
    requiresConsensus: bool = False

class ValueItem(BaseModel):
    id: str
    weight: float
    description: str

class MercyHook(BaseModel):
    id: str
    condition: Any
    action: str
    description: str

class ValueManifesto(BaseModel):
    values: List[ValueItem]
    mercy_hooks: List[MercyHook]

class Accountability(BaseModel):
    responsibleEntity: Literal['ai-agent', 'human-approver', 'policy-author', 'system-fault']
    signature: str
    creditImpact: float

class Vote(BaseModel):
    voterId: str
    decision: Decision
    weight: float

class ConsensusResult(BaseModel):
    finalDecision: Decision
    agreementRate: float
    isVetoed: bool
    voters: List[str]

class AnomalyReport(BaseModel):
    isAnomaly: bool
    score: float
    reasons: List[str]

class GovernanceAsset(BaseModel):
    id: str
    type: Literal['frequent-violation', 'trusted-pattern']
    description: str
    evidenceCount: int
    suggestedAction: Optional[Literal['promote-to-scope', 'harden-rule']] = None
    pattern: str

class SelfAuditReport(BaseModel):
    timestamp: float
    healthScore: float
    findings: List[Dict[str, str]]

class Violation(BaseModel):
    ruleId: str
    description: str
    level: Literal['warn', 'block']
    valueWeight: Optional[float] = None

class Decision(BaseModel):
    allowed: bool
    requiresHuman: bool
    riskLevel: Literal['low', 'medium', 'high']
    actions: List[Literal['allow', 'warn', 'block', 'require_human']]
    violations: List[Violation]
    valueScore: Optional[float] = None
    accountability: Optional[Accountability] = None
    anomalyReport: Optional[AnomalyReport] = None
    auditLog: str

class DecisionTrace(Decision):
    proposal: Proposal
    outcome: Literal['applied', 'rejected', 'pending']

# Resolve forward references
Vote.model_rebuild()
ConsensusResult.model_rebuild()
