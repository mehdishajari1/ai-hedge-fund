"""Machine-evaluable governance models for consequential fund actions."""
from __future__ import annotations
from enum import Enum
from pydantic import BaseModel, Field

class AssuranceState(str, Enum):
    HEALTHY = "healthy"
    WATCH = "watch"
    DEGRADED = "degraded"
    UNASSURED = "unassured"
    INCIDENT = "incident"

class Decision(str, Enum):
    ALLOW = "allow"
    DENY = "deny"
    HUMAN_GATE = "human_gate"

class AuthorityVector(BaseModel):
    actor_id: str
    acl: int = Field(ge=0)
    aal: int = Field(ge=0)
    epoch: int = Field(default=1, ge=1)
    allowed_actions: set[str] = Field(default_factory=set)
    prohibited_actions: set[str] = Field(default_factory=set)
    max_order_value: float | None = Field(default=None, gt=0)
    allowed_tickers: set[str] = Field(default_factory=set)
    required_claims: set[str] = Field(default_factory=set)

class AssuranceClaim(BaseModel):
    claim_id: str
    state: AssuranceState = AssuranceState.HEALTHY
    dependencies: set[str] = Field(default_factory=set)
    reason: str = ""

class MaterialChange(BaseModel):
    change_type: str
    dependency: str
    description: str

class GovernanceDecision(BaseModel):
    action: str
    ticker: str | None = None
    decision: Decision
    reason_code: str
    authority_epoch: int
    explanation: str = ""

class GovernanceCycleRecord(BaseModel):
    actor_id: str
    authority_epoch: int
    assurance: dict[str, AssuranceState]
    decisions: list[GovernanceDecision] = Field(default_factory=list)
