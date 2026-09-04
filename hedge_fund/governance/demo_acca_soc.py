"""
ACCA + Security Operations Governance Profile (SGP)
Cross-Domain Proof of Concept

Purpose
-------
Demonstrate that the same ACCA assurance machinery used in the trading
experiments can govern a materially different application domain:
agentic security operations.

The experiment composes:

    SOC action request
        ->
    SGP declared authority
        ->
    ACCA assurance-conditioned effective authority
        ->
    runtime decision

The SGP profile itself remains unchanged throughout the experiment.

Only an assurance-relevant operating condition changes:

    edr_telemetry: healthy -> degraded -> healthy

Evidence remains historically valid throughout.

When EDR telemetry becomes degraded:
    - evidence becomes non-applicable
    - AUTONOMOUS_CONTAINMENT becomes UNASSURED
    - effective SOC authority contracts
    - isolate_endpoint moves from ALLOW to HUMAN_GATE
    - investigative authority remains available
    - actions outside SGP declared authority remain DENY

When telemetry recovers:
    - evidence becomes applicable again
    - assurance returns to HEALTHY
    - autonomous containment authority is restored
    - a new authority epoch is created
"""

from __future__ import annotations

from dataclasses import dataclass, field

from governance.acca import ACCAEngine
from governance.assurance_graph import AssuranceDependencyGraph
from governance.context import GovernanceContext
from governance.evidence import AssuranceEvidence
from governance.materiality import MaterialityEvaluator
from governance.models import AssuranceState
from governance.sgp import (
    SOCAction,
    SOCEnvironment,
    SOCRequest,
    SGPAuthorizer,
    SGPDecision,
    example_sgp_profile,
)


CLAIM_ID = "SAFE_AUTONOMOUS_CONTAINMENT"

APPROVED_MODEL = "SOC-MODEL-APPROVED-01"

EDR_HEALTHY = "healthy"
EDR_DEGRADED = "degraded"


# ---------------------------------------------------------------------------
# SOC effective-authority layer
# ---------------------------------------------------------------------------


@dataclass
class SOCEffectiveAuthority:
    """
    Effective SOC authority derived from declared SGP authority plus
    current assurance state.

    This is intentionally small for the proof of concept.
    """

    epoch: int = 1

    allowed_actions: set[str] = field(default_factory=set)
    human_gate_actions: set[str] = field(default_factory=set)
    prohibited_actions: set[str] = field(default_factory=set)


class SOCControlPlane:
    """
    Minimal SOC authority adapter used by ACCAEngine.

    SGP defines declared authority.

    This control plane derives effective SOC authority from assurance state.

    It deliberately implements the same conceptual contract used in the
    trading experiments:

        assurance claim update
            ->
        authority recalculation
            ->
        monotonically increasing authority epoch
    """

    def __init__(self):
        self.profile = example_sgp_profile()

        self.claim_state = AssuranceState.HEALTHY
        self.claim_reason = "Initial applicable assurance evidence."

        self.authority = SOCEffectiveAuthority(
            epoch=1,
            allowed_actions=set(),
            human_gate_actions=set(),
            prohibited_actions=set(),
        )

        self._derive_authority(
            advance_epoch=False,
        )

    def _derive_authority(
        self,
        *,
        advance_epoch: bool,
    ) -> None:
        old_epoch = self.authority.epoch

        allowed = set(self.profile.allowed_actions)
        human_gate = set(self.profile.human_gate_actions)
        prohibited = set(self.profile.prohibited_actions)

        # Human-gated actions are not autonomously executable.
        allowed -= human_gate

        if self.claim_state in {
            AssuranceState.DEGRADED,
            AssuranceState.UNASSURED,
            AssuranceState.INCIDENT,
        }:
            # Preserve investigative capabilities while contracting
            # autonomous containment authority.
            for action in {
                SOCAction.ISOLATE_ENDPOINT.value,
                SOCAction.REVOKE_TOKEN.value,
                SOCAction.KILL_SESSION.value,
            }:
                if action in self.profile.allowed_actions:
                    allowed.discard(action)
                    human_gate.add(action)

        new_epoch = (
            old_epoch + 1
            if advance_epoch
            else old_epoch
        )

        self.authority = SOCEffectiveAuthority(
            epoch=new_epoch,
            allowed_actions=allowed,
            human_gate_actions=human_gate,
            prohibited_actions=prohibited,
        )

    def set_claim_state(
        self,
        claim_id: str,
        state: AssuranceState,
        reason: str,
    ) -> None:
        """
        Interface consumed by ACCAEngine.

        Authority is recalculated only when assurance state/reason changes.
        """

        if claim_id != CLAIM_ID:
            return

        if (
            state == self.claim_state
            and reason == self.claim_reason
        ):
            return

        self.claim_state = state
        self.claim_reason = reason

        self._derive_authority(
            advance_epoch=True,
        )

    def decide_action(
        self,
        request: SOCRequest,
    ) -> SGPDecision:
        """
        Compose declared SGP authority with ACCA effective authority.

        SGP executes first.

        Anything outside declared authority remains denied regardless of
        effective authority.
        """

        sgp_result = SGPAuthorizer(
            self.profile
        ).authorize(request)

        # Declared-authority denial always wins.
        if sgp_result.decision == SGPDecision.DENY:
            return SGPDecision.DENY

        action = request.action

        if action in self.authority.prohibited_actions:
            return SGPDecision.DENY

        if action in self.authority.human_gate_actions:
            return SGPDecision.HUMAN_GATE

        if action in self.authority.allowed_actions:
            return SGPDecision.ALLOW

        # Closed-world fallback.
        return SGPDecision.DENY


# ---------------------------------------------------------------------------
# Experiment state
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class SOCACCASnapshot:
    label: str

    edr_telemetry: str

    evidence_valid: bool
    evidence_applicable: bool

    claim_state: AssuranceState

    authority_epoch: int

    query_endpoint_decision: SGPDecision
    isolate_endpoint_decision: SGPDecision
    disable_account_decision: SGPDecision
    modify_firewall_decision: SGPDecision

    isolate_declared_in_sgp: bool
    declared_actions: frozenset[str]


@dataclass(frozen=True)
class SOCACCAResult:
    healthy: SOCACCASnapshot
    degraded: SOCACCASnapshot
    recovered: SOCACCASnapshot

    degradation_transition: object
    recovery_transition: object


# ---------------------------------------------------------------------------
# ACCA construction
# ---------------------------------------------------------------------------


def _make_context() -> GovernanceContext:
    return GovernanceContext(
        values={
            "detection_model": APPROVED_MODEL,
            "edr_telemetry": EDR_HEALTHY,
        }
    )


def _make_evidence() -> AssuranceEvidence:
    """
    Evidence supporting safe autonomous SOC containment.

    Important:
        valid=True remains unchanged throughout the experiment.

    The evidence was established under:
        - the approved detection model
        - healthy EDR telemetry

    Degraded EDR telemetry therefore makes the artifact non-applicable rather
    than historically invalid.
    """

    return AssuranceEvidence(
        evidence_id="E-SOC-01",
        subject="soc_agent",
        evidence_type="soc_containment_evaluation",
        supports={CLAIM_ID},
        assumptions={
            "detection_model": {
                APPROVED_MODEL,
            },
            "edr_telemetry": {
                EDR_HEALTHY,
            },
        },
        valid=True,
    )


def build_acca_soc() -> tuple[
    GovernanceContext,
    AssuranceEvidence,
    AssuranceDependencyGraph,
    SOCControlPlane,
    ACCAEngine,
]:
    context = _make_context()
    evidence = _make_evidence()

    graph = AssuranceDependencyGraph(
        evidence=[evidence],
    )

    materiality = MaterialityEvaluator(
        evidence=[evidence],
    )

    control = SOCControlPlane()

    engine = ACCAEngine(
        context=context,
        assurance_graph=graph,
        materiality=materiality,
        control_plane=control,
    )

    return (
        context,
        evidence,
        graph,
        control,
        engine,
    )


# ---------------------------------------------------------------------------
# Requests
# ---------------------------------------------------------------------------


def _query_endpoint_request() -> SOCRequest:
    return SOCRequest(
        actor_id="soc_agent",
        action=SOCAction.QUERY_ENDPOINT.value,
        resource_id="WORKSTATION-17",
        resource_type="endpoint",
        environment=SOCEnvironment.PRODUCTION,
    )


def _isolate_endpoint_request() -> SOCRequest:
    return SOCRequest(
        actor_id="soc_agent",
        action=SOCAction.ISOLATE_ENDPOINT.value,
        resource_id="WORKSTATION-17",
        resource_type="endpoint",
        environment=SOCEnvironment.PRODUCTION,
    )


def _disable_account_request() -> SOCRequest:
    return SOCRequest(
        actor_id="soc_agent",
        action=SOCAction.DISABLE_ACCOUNT.value,
        resource_id="USER-4421",
        resource_type="identity",
        environment=SOCEnvironment.PRODUCTION,
    )


def _modify_firewall_request() -> SOCRequest:
    return SOCRequest(
        actor_id="soc_agent",
        action=SOCAction.MODIFY_FIREWALL_RULE.value,
        resource_id="FIREWALL-PROD-01",
        resource_type="network_control",
        environment=SOCEnvironment.PRODUCTION,
    )


# ---------------------------------------------------------------------------
# Snapshot helpers
# ---------------------------------------------------------------------------


def _claim_state(
    graph: AssuranceDependencyGraph,
    context: GovernanceContext,
) -> AssuranceState:
    claim = graph.evaluate_claim(
        CLAIM_ID,
        context,
    )

    return (
        AssuranceState.HEALTHY
        if claim.supported
        else AssuranceState.UNASSURED
    )


def _snapshot(
    *,
    label: str,
    context: GovernanceContext,
    evidence: AssuranceEvidence,
    graph: AssuranceDependencyGraph,
    control: SOCControlPlane,
) -> SOCACCASnapshot:
    profile = control.profile

    return SOCACCASnapshot(
        label=label,

        edr_telemetry=context.get(
            "edr_telemetry"
        ),

        evidence_valid=evidence.valid,

        evidence_applicable=evidence.is_applicable(
            context
        ),

        claim_state=_claim_state(
            graph,
            context,
        ),

        authority_epoch=control.authority.epoch,

        query_endpoint_decision=control.decide_action(
            _query_endpoint_request()
        ),

        isolate_endpoint_decision=control.decide_action(
            _isolate_endpoint_request()
        ),

        disable_account_decision=control.decide_action(
            _disable_account_request()
        ),

        modify_firewall_decision=control.decide_action(
            _modify_firewall_request()
        ),

        isolate_declared_in_sgp=(
            SOCAction.ISOLATE_ENDPOINT.value
            in profile.allowed_actions
        ),

        declared_actions=frozenset(
            profile.allowed_actions
        ),
    )


# ---------------------------------------------------------------------------
# Experiment
# ---------------------------------------------------------------------------


def run_acca_soc() -> SOCACCAResult:
    (
        context,
        evidence,
        graph,
        control,
        engine,
    ) = build_acca_soc()

    # ---------------------------------------------------------------
    # Phase 1 — Healthy telemetry
    # ---------------------------------------------------------------

    healthy = _snapshot(
        label="HEALTHY SOC OPERATING STATE",
        context=context,
        evidence=evidence,
        graph=graph,
        control=control,
    )

    # ---------------------------------------------------------------
    # Phase 2 — Material telemetry degradation
    # ---------------------------------------------------------------

    degradation_transition = engine.observe_context(
        "edr_telemetry",
        EDR_DEGRADED,
    )

    degraded = _snapshot(
        label="DEGRADED SOC OPERATING STATE",
        context=context,
        evidence=evidence,
        graph=graph,
        control=control,
    )

    # ---------------------------------------------------------------
    # Phase 3 — Telemetry recovery
    # ---------------------------------------------------------------

    recovery_transition = engine.observe_context(
        "edr_telemetry",
        EDR_HEALTHY,
    )

    recovered = _snapshot(
        label="RECOVERED SOC OPERATING STATE",
        context=context,
        evidence=evidence,
        graph=graph,
        control=control,
    )

    return SOCACCAResult(
        healthy=healthy,
        degraded=degraded,
        recovered=recovered,
        degradation_transition=degradation_transition,
        recovery_transition=recovery_transition,
    )


# ---------------------------------------------------------------------------
# Console output
# ---------------------------------------------------------------------------


def _yes_no(value: bool) -> str:
    return "YES" if value else "NO"


def _print_snapshot(
    snapshot: SOCACCASnapshot,
) -> None:
    print()
    print(snapshot.label)
    print("-" * len(snapshot.label))

    print(
        f"EDR telemetry:             "
        f"{snapshot.edr_telemetry}"
    )

    print(
        f"Evidence valid:            "
        f"{_yes_no(snapshot.evidence_valid)}"
    )

    print(
        f"Evidence applicable:       "
        f"{_yes_no(snapshot.evidence_applicable)}"
    )

    print(
        f"Assurance claim:           "
        f"{snapshot.claim_state.value}"
    )

    print(
        f"Authority epoch:           "
        f"{snapshot.authority_epoch}"
    )

    print(
        f"isolate_endpoint in SGP:   "
        f"{_yes_no(snapshot.isolate_declared_in_sgp)}"
    )

    print()
    print("Effective action decisions")

    print(
        f"  query_endpoint:          "
        f"{snapshot.query_endpoint_decision.value}"
    )

    print(
        f"  isolate_endpoint:        "
        f"{snapshot.isolate_endpoint_decision.value}"
    )

    print(
        f"  disable_account:         "
        f"{snapshot.disable_account_decision.value}"
    )

    print(
        f"  modify_firewall_rule:    "
        f"{snapshot.modify_firewall_decision.value}"
    )


def print_acca_soc_result(
    result: SOCACCAResult,
) -> None:
    print()
    print("=" * 76)
    print(
        "ACCA + SGP — CROSS-DOMAIN SECURITY OPERATIONS PROOF OF CONCEPT"
    )
    print("=" * 76)

    _print_snapshot(
        result.healthy
    )

    _print_snapshot(
        result.degraded
    )

    _print_snapshot(
        result.recovered
    )

    print()
    print("DECLARED AUTHORITY INVARIANT")
    print("-" * 76)

    declared_authority_unchanged = result.healthy.declared_actions == result.degraded.declared_actions == result.recovered.declared_actions
    print(f"SGP declared actions unchanged: {_yes_no(declared_authority_unchanged)}")

    print()
    print("CAUSAL RESULT")
    print("-" * 76)

    print(
        "Healthy EDR telemetry -> evidence applicable -> "
        "autonomous containment assured -> isolate_endpoint ALLOW."
    )

    print(
        "Degraded EDR telemetry -> evidence remains VALID but becomes "
        "NON-APPLICABLE -> containment becomes UNASSURED -> "
        "isolate_endpoint HUMAN_GATE."
    )

    print(
        "Investigative authority remains available during degradation."
    )

    print(
        "Actions outside SGP declared authority remain DENY throughout."
    )

    print(
        "Telemetry recovery -> evidence applicable again -> assurance "
        "restored -> autonomous containment restored under a new epoch."
    )

    print()
    print("INTERPRETATION")
    print("-" * 76)

    print(
        "SGP determines whether a SOC action is within declared operational "
        "authority. ACCA determines how much of that declared authority is "
        "currently justified by applicable assurance evidence."
    )


def main() -> None:
    result = run_acca_soc()
    print_acca_soc_result(
        result
    )


if __name__ == "__main__":
    main()
