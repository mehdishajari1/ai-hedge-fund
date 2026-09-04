from __future__ import annotations
from dataclasses import dataclass, field
from enum import Enum
from typing import FrozenSet, Iterable, Optional

class GovernanceStage(str, Enum):
    SANDBOX = 'sandbox'
    ASSURANCE_STAGING = 'assurance-staging'
    OPERATIONAL = 'operational'

class AuthorizationResult(str, Enum):
    ALLOW = 'ALLOW'
    DENY = 'DENY'

class DenialReason(str, Enum):
    NOT_EXPLICITLY_AUTHORIZED = 'NOT_EXPLICITLY_AUTHORIZED'
    OUTSIDE_SCOPE = 'OUTSIDE_SCOPE'
    NOT_ASSURED = 'NOT_ASSURED_FOR_OPERATIONAL_USE'
    NOT_APPROVED = 'NOT_APPROVED_FOR_OPERATIONAL_USE'
    HARD_CONSTRAINT = 'HARD_CONSTRAINT'

@dataclass(frozen=True)
class CapabilityRecord:
    action: str
    discovered: bool = False
    assured: bool = False
    approved: bool = False

@dataclass(frozen=True)
class TGPProfile:
    profile_id: str
    allowed_actions: FrozenSet[str] = field(default_factory=frozenset)
    allowed_asset_classes: FrozenSet[str] = field(default_factory=frozenset)
    allowed_symbols: FrozenSet[str] = field(default_factory=frozenset)
    hard_prohibited_actions: FrozenSet[str] = field(default_factory=frozenset)

    @classmethod
    def build(cls, profile_id: str, *, allowed_actions: Iterable[str]=(),
              allowed_asset_classes: Iterable[str]=(), allowed_symbols: Iterable[str]=(),
              hard_prohibited_actions: Iterable[str]=()):
        return cls(profile_id, frozenset(allowed_actions), frozenset(allowed_asset_classes),
                   frozenset(allowed_symbols), frozenset(hard_prohibited_actions))

@dataclass(frozen=True)
class ActionRequest:
    action: str
    stage: GovernanceStage
    asset_class: Optional[str] = None
    symbol: Optional[str] = None

@dataclass(frozen=True)
class TGPDecision:
    result: AuthorizationResult
    reason: Optional[DenialReason] = None
    detail: str = ''

class TGPAuthorizer:
    def __init__(self, profile: TGPProfile):
        self.profile = profile

    def authorize(self, request: ActionRequest, *, capability: Optional[CapabilityRecord]=None):
        if request.action in self.profile.hard_prohibited_actions:
            return TGPDecision(AuthorizationResult.DENY, DenialReason.HARD_CONSTRAINT)

        if request.stage is not GovernanceStage.OPERATIONAL:
            # Broader discovery/evaluation, but hard constraints still dominate.
            return TGPDecision(AuthorizationResult.ALLOW)

        # Closed-world/default-deny operational semantics.
        if request.action not in self.profile.allowed_actions:
            return TGPDecision(AuthorizationResult.DENY, DenialReason.NOT_EXPLICITLY_AUTHORIZED)

        if capability is not None and not capability.assured:
            return TGPDecision(AuthorizationResult.DENY, DenialReason.NOT_ASSURED)
        if capability is not None and not capability.approved:
            return TGPDecision(AuthorizationResult.DENY, DenialReason.NOT_APPROVED)

        if request.asset_class and self.profile.allowed_asset_classes and request.asset_class not in self.profile.allowed_asset_classes:
            return TGPDecision(AuthorizationResult.DENY, DenialReason.OUTSIDE_SCOPE)
        if request.symbol and self.profile.allowed_symbols and request.symbol not in self.profile.allowed_symbols:
            return TGPDecision(AuthorizationResult.DENY, DenialReason.OUTSIDE_SCOPE)
        return TGPDecision(AuthorizationResult.ALLOW)

def promote_capability(capability: CapabilityRecord, *, assurance_passed: bool, principal_approved: bool):
    # Records evidence/approval only. It never mutates TGP declared authority.
    return CapabilityRecord(capability.action, True, bool(assurance_passed), bool(assurance_passed and principal_approved))
