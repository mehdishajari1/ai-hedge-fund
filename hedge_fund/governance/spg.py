"""
Security Operations Governance Profile (SGP) v0.1

Purpose
-------
Provide a domain governance profile for agentic security operations.

SGP defines:
    - consequential SOC actions
    - resource/scope constraints
    - operational environment
    - autonomy expectations
    - approval requirements
    - default-deny behavior

SGP does NOT implement:
    - detection
    - incident classification
    - SIEM
    - EDR
    - identity systems
    - an LLM agent
    - ACCA itself

It maps SOC-specific semantics into explicit declared authority that can later
be conditioned by ACCA assurance and stakeholder policy.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum


class SOCEnvironment(str, Enum):
    SIMULATION = "simulation"
    STAGING = "staging"
    PRODUCTION = "production"


class SOCAction(str, Enum):
    # Informational / investigative
    READ_ALERT = "read_alert"
    QUERY_LOGS = "query_logs"
    QUERY_ENDPOINT = "query_endpoint"
    QUERY_IDENTITY = "query_identity"
    ENRICH_INDICATOR = "enrich_indicator"
    CREATE_CASE = "create_case"

    # Containment
    KILL_SESSION = "kill_session"
    REVOKE_TOKEN = "revoke_token"
    ISOLATE_ENDPOINT = "isolate_endpoint"
    QUARANTINE_FILE = "quarantine_file"
    BLOCK_INDICATOR = "block_indicator"

    # Higher-impact remediation
    DISABLE_ACCOUNT = "disable_account"
    MODIFY_FIREWALL_RULE = "modify_firewall_rule"
    DELETE_RESOURCE = "delete_resource"

    # Governance-sensitive
    MODIFY_DETECTION_RULE = "modify_detection_rule"
    CHANGE_SECURITY_POLICY = "change_security_policy"
    DELEGATE_AUTHORITY = "delegate_authority"


class SGPDecision(str, Enum):
    ALLOW = "allow"
    DENY = "deny"
    HUMAN_GATE = "human_gate"


class SGPDenialReason(str, Enum):
    NOT_EXPLICITLY_AUTHORIZED = "not_explicitly_authorized"
    RESOURCE_OUT_OF_SCOPE = "resource_out_of_scope"
    ENVIRONMENT_NOT_ALLOWED = "environment_not_allowed"
    HUMAN_APPROVAL_REQUIRED = "human_approval_required"


@dataclass(frozen=True)
class SOCRequest:
    actor_id: str
    action: str
    resource_id: str
    resource_type: str
    environment: SOCEnvironment
    criticality: str = "standard"


@dataclass
class SGPProfile:
    """
    Declared SOC authority profile.

    This represents domain-level declared authority, not ACCA effective
    authority.
    """

    profile_id: str
    actor_id: str

    allowed_actions: set[str] = field(default_factory=set)

    allowed_resource_types: set[str] = field(default_factory=set)

    allowed_resources: set[str] = field(default_factory=set)

    allowed_environments: set[SOCEnvironment] = field(
        default_factory=lambda: {
            SOCEnvironment.SIMULATION,
            SOCEnvironment.STAGING,
        }
    )

    human_gate_actions: set[str] = field(default_factory=set)

    prohibited_actions: set[str] = field(default_factory=set)


@dataclass(frozen=True)
class SGPAuthorization:
    decision: SGPDecision
    reason: SGPDenialReason | None = None


class SGPAuthorizer:
    """
    Closed-world/default-deny SOC profile authorizer.
    """

    def __init__(self, profile: SGPProfile):
        self.profile = profile

    def authorize(self, request: SOCRequest) -> SGPAuthorization:
        profile = self.profile

        # Actor mismatch.
        if request.actor_id != profile.actor_id:
            return SGPAuthorization(
                decision=SGPDecision.DENY,
                reason=SGPDenialReason.NOT_EXPLICITLY_AUTHORIZED,
            )

        # Explicit prohibition wins.
        if request.action in profile.prohibited_actions:
            return SGPAuthorization(
                decision=SGPDecision.DENY,
                reason=SGPDenialReason.NOT_EXPLICITLY_AUTHORIZED,
            )

        # Closed-world/default deny.
        if request.action not in profile.allowed_actions:
            return SGPAuthorization(
                decision=SGPDecision.DENY,
                reason=SGPDenialReason.NOT_EXPLICITLY_AUTHORIZED,
            )

        # Environment scope.
        if request.environment not in profile.allowed_environments:
            return SGPAuthorization(
                decision=SGPDecision.DENY,
                reason=SGPDenialReason.ENVIRONMENT_NOT_ALLOWED,
            )

        # Resource-type scope.
        if (
            profile.allowed_resource_types
            and request.resource_type not in profile.allowed_resource_types
        ):
            return SGPAuthorization(
                decision=SGPDecision.DENY,
                reason=SGPDenialReason.RESOURCE_OUT_OF_SCOPE,
            )

        # Optional explicit resource scope.
        if (
            profile.allowed_resources
            and request.resource_id not in profile.allowed_resources
        ):
            return SGPAuthorization(
                decision=SGPDecision.DENY,
                reason=SGPDenialReason.RESOURCE_OUT_OF_SCOPE,
            )

        # Human-gated actions are inside declared authority but not autonomously
        # executable.
        if request.action in profile.human_gate_actions:
            return SGPAuthorization(
                decision=SGPDecision.HUMAN_GATE,
                reason=SGPDenialReason.HUMAN_APPROVAL_REQUIRED,
            )

        return SGPAuthorization(
            decision=SGPDecision.ALLOW,
        )


def example_sgp_profile() -> SGPProfile:
    """
    Example SOC analyst-agent profile used by the SGP proof of concept.

    The agent can investigate broadly and perform a limited set of containment
    actions, but higher-impact remediation remains human-gated or prohibited.
    """

    return SGPProfile(
        profile_id="SGP-SOC-ANALYST-01",
        actor_id="soc_agent",

        allowed_actions={
            SOCAction.READ_ALERT.value,
            SOCAction.QUERY_LOGS.value,
            SOCAction.QUERY_ENDPOINT.value,
            SOCAction.QUERY_IDENTITY.value,
            SOCAction.ENRICH_INDICATOR.value,
            SOCAction.CREATE_CASE.value,

            SOCAction.KILL_SESSION.value,
            SOCAction.REVOKE_TOKEN.value,
            SOCAction.ISOLATE_ENDPOINT.value,

            SOCAction.DISABLE_ACCOUNT.value,
        },

        allowed_resource_types={
            "endpoint",
            "identity",
            "session",
            "alert",
        },

        allowed_environments={
            SOCEnvironment.SIMULATION,
            SOCEnvironment.STAGING,
            SOCEnvironment.PRODUCTION,
        },

        human_gate_actions={
            SOCAction.DISABLE_ACCOUNT.value,
        },

        prohibited_actions={
            SOCAction.MODIFY_FIREWALL_RULE.value,
            SOCAction.DELETE_RESOURCE.value,
            SOCAction.CHANGE_SECURITY_POLICY.value,
            SOCAction.DELEGATE_AUTHORITY.value,
        },
    )
