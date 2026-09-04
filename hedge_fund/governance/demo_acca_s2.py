"""
S2 — Material Model Substitution

Purpose
-------
Demonstrate that replacing an approved model with a different model can make
otherwise valid model-specific assurance evidence non-applicable, causing the
supported assurance claim to degrade and effective authority to contract.

The experiment deliberately holds constant:
    - prompt
    - tools
    - credentials
    - declared authority
    - stakeholder risk policy
    - evidence artifact
    - evidence validity
    - operating environment

Only model_id changes:

    MODEL-APPROVED-01
        ->
    MODEL-NEW-02
        ->
    MODEL-APPROVED-01

Expected causal chain
---------------------
Approved model:
    model applicable
        -> evidence applicable
        -> SAFE_AUTONOMOUS_TRADING supported
        -> full policy-authorized authority

Substituted model:
    model changes
        -> evidence remains VALID
        -> evidence becomes NON-APPLICABLE
        -> SAFE_AUTONOMOUS_TRADING becomes UNASSURED
        -> effective authority contracts
        -> authority epoch advances

Recovery:
    approved model restored
        -> evidence applicable again
        -> assurance support restored
        -> policy-authorized authority restored
        -> authority epoch advances again
"""

from __future__ import annotations

from dataclasses import dataclass

from governance.acca import ACCAEngine
from governance.assurance_graph import AssuranceDependencyGraph
from governance.context import GovernanceContext
from governance.control import GovernanceControlPlane
from governance.evidence import AssuranceEvidence
from governance.materiality import MaterialityEvaluator
from governance.models import AssuranceState
from governance.policy import StakeholderRiskPolicy


CLAIM_ID = "SAFE_AUTONOMOUS_TRADING"

APPROVED_MODEL = "MODEL-APPROVED-01"
SUBSTITUTED_MODEL = "MODEL-NEW-02"

PROMPT_ID = "PROMPT-FIXED-01"
TOOLS_ID = "TOOLS-FIXED-01"
CREDENTIALS_ID = "CREDENTIAL-FIXED-01"
TGP_ID = "TGP-FIXED-01"


@dataclass(frozen=True)
class S2Snapshot:
    """
    Observable state captured at one point in the S2 experiment.
    """

    label: str

    model_id: str

    evidence_valid: bool
    evidence_applicable: bool

    claim_state: AssuranceState

    authority_epoch: int
    aal: int
    max_order_value: float | None

    paper_allowed: bool
    live_allowed: bool

    prompt_id: str
    tools_id: str
    credentials_id: str
    declared_authority_id: str


@dataclass(frozen=True)
class S2Result:
    """
    Complete normal -> substituted -> restored S2 experiment.
    """

    approved: S2Snapshot
    substituted: S2Snapshot
    recovered: S2Snapshot

    substitution_transition: object
    recovery_transition: object


def _make_context() -> GovernanceContext:
    """
    Construct the fixed S2 operating context.

    model_id is the only value intentionally changed during the experiment.
    """

    return GovernanceContext(
        values={
            "model_id": APPROVED_MODEL,
            "prompt_id": PROMPT_ID,
            "tools_id": TOOLS_ID,
            "credentials_id": CREDENTIALS_ID,
            "declared_authority_id": TGP_ID,
            "environment": "paper/live",
        }
    )


def _make_evidence() -> AssuranceEvidence:
    """
    Model-specific assurance evidence.

    Important:
        This evidence remains VALID throughout S2.

    It was evaluated for MODEL-APPROVED-01 only, so changing model_id to
    MODEL-NEW-02 causes the evidence to become non-applicable rather than
    invalid.
    """

    return AssuranceEvidence(
        evidence_id="E-MODEL-01",
        subject="portfolio_manager",
        evidence_type="model_evaluation",
        supports={CLAIM_ID},
        assumptions={
            "model_id": {APPROVED_MODEL},
        },
        valid=True,
    )


def _make_policy() -> StakeholderRiskPolicy:
    """
    Conservative policy used for the S2 experiment.

    When SAFE_AUTONOMOUS_TRADING is not assured:
        - live order authority is removed
        - maximum order value is reduced to $1,000
        - autonomy contracts to AAL 1 / human-gated operation
    """

    return StakeholderRiskPolicy(
        policy_id="s2-model-substitution-policy",
        unassured_max_order_value=1_000.0,
        allow_live_when_unassured=False,
        require_human_gate_when_unassured=True,
    )


def build_s2() -> tuple[
    GovernanceContext,
    AssuranceEvidence,
    AssuranceDependencyGraph,
    GovernanceControlPlane,
    ACCAEngine,
]:
    """
    Build the S2 experiment using the existing ACCA implementation.
    """

    context = _make_context()
    evidence = _make_evidence()

    graph = AssuranceDependencyGraph(
        evidence=[evidence],
    )

    materiality = MaterialityEvaluator(
        evidence=[evidence],
    )

    policy = _make_policy()

    control = GovernanceControlPlane.acca_trading_demo(
        "example-fund",
        max_order_value=10_000.0,
        policy=policy,
    )

    engine = ACCAEngine(
        context=context,
        assurance_graph=graph,
        materiality=materiality,
        control_plane=control,
    )

    return context, evidence, graph, control, engine


def _claim_state(
    graph: AssuranceDependencyGraph,
    context: GovernanceContext,
) -> AssuranceState:
    """
    Return the current state of SAFE_AUTONOMOUS_TRADING.
    """

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
    control: GovernanceControlPlane,
) -> S2Snapshot:
    """
    Capture the observable experimental state.
    """

    authority = control.authority

    return S2Snapshot(
        label=label,
        model_id=context.get("model_id"),
        evidence_valid=evidence.valid,
        evidence_applicable=evidence.is_applicable(context),
        claim_state=_claim_state(graph, context),
        authority_epoch=authority.epoch,
        aal=authority.aal,
        max_order_value=authority.max_order_value,
        paper_allowed="paper_order" in authority.allowed_actions,
        live_allowed="live_order" in authority.allowed_actions,
        prompt_id=context.get("prompt_id"),
        tools_id=context.get("tools_id"),
        credentials_id=context.get("credentials_id"),
        declared_authority_id=context.get("declared_authority_id"),
    )


def run_s2() -> S2Result:
    """
    Execute the complete S2 experiment.

    Phase 1:
        Approved model.

    Phase 2:
        Substitute MODEL-NEW-02.

    Phase 3:
        Restore MODEL-APPROVED-01.
    """

    context, evidence, graph, control, engine = build_s2()

    # ---------------------------------------------------------
    # Phase 1 — Approved model
    # ---------------------------------------------------------

    approved = _snapshot(
        label="APPROVED MODEL",
        context=context,
        evidence=evidence,
        graph=graph,
        control=control,
    )

    # ---------------------------------------------------------
    # Phase 2 — Material model substitution
    # ---------------------------------------------------------

    substitution_transition = engine.observe_context(
        "model_id",
        SUBSTITUTED_MODEL,
    )

    substituted = _snapshot(
        label="SUBSTITUTED MODEL",
        context=context,
        evidence=evidence,
        graph=graph,
        control=control,
    )

    # ---------------------------------------------------------
    # Phase 3 — Restore approved model
    # ---------------------------------------------------------

    recovery_transition = engine.observe_context(
        "model_id",
        APPROVED_MODEL,
    )

    recovered = _snapshot(
        label="RESTORED APPROVED MODEL",
        context=context,
        evidence=evidence,
        graph=graph,
        control=control,
    )

    return S2Result(
        approved=approved,
        substituted=substituted,
        recovered=recovered,
        substitution_transition=substitution_transition,
        recovery_transition=recovery_transition,
    )


def _yes_no(value: bool) -> str:
    return "YES" if value else "NO"


def _money(value: float | None) -> str:
    if value is None:
        return "None"

    return f"${value:,.0f}"


def _print_snapshot(snapshot: S2Snapshot) -> None:
    print()
    print(snapshot.label)
    print("-" * len(snapshot.label))

    print(f"Model:                 {snapshot.model_id}")
    print(f"Evidence valid:        {_yes_no(snapshot.evidence_valid)}")
    print(
        f"Evidence applicable:   "
        f"{_yes_no(snapshot.evidence_applicable)}"
    )
    print(f"Assurance claim:       {snapshot.claim_state.value}")
    print(f"Authority epoch:       {snapshot.authority_epoch}")
    print(f"AAL:                   {snapshot.aal}")
    print(
        f"Max order value:       "
        f"{_money(snapshot.max_order_value)}"
    )
    print(
        f"Paper authority:       "
        f"{_yes_no(snapshot.paper_allowed)}"
    )
    print(
        f"Live authority:        "
        f"{_yes_no(snapshot.live_allowed)}"
    )

    print()
    print("Fixed controls")
    print(f"  Prompt:              {snapshot.prompt_id}")
    print(f"  Tools:               {snapshot.tools_id}")
    print(f"  Credentials:         {snapshot.credentials_id}")
    print(
        f"  Declared authority:  "
        f"{snapshot.declared_authority_id}"
    )


def print_s2_result(result: S2Result) -> None:
    print()
    print("=" * 70)
    print("S2 — MATERIAL MODEL SUBSTITUTION")
    print("=" * 70)

    _print_snapshot(result.approved)
    _print_snapshot(result.substituted)
    _print_snapshot(result.recovered)

    print()
    print("CAUSAL RESULT")
    print("-" * 70)

    print(
        "Approved model -> evidence applicable -> "
        "assurance supported -> full policy-authorized autonomy."
    )

    print(
        "Substituted model -> evidence remains VALID -> "
        "becomes NON-APPLICABLE -> assurance UNASSURED -> "
        "effective authority contracts -> epoch advances."
    )

    print(
        "Approved model restored -> evidence applicable again -> "
        "assurance support restored -> policy-authorized authority "
        "restored -> epoch advances again."
    )

    print()
    print("CONTROLLED VARIABLE")
    print("-" * 70)

    print(
        f"model_id: {result.approved.model_id}"
        f" -> {result.substituted.model_id}"
        f" -> {result.recovered.model_id}"
    )

    print()
    print("FIXED")
    print("-" * 70)

    print("Prompt")
    print("Tools")
    print("Credentials")
    print("Declared authority")
    print("Stakeholder policy")
    print("Evidence artifact")
    print("Evidence validity")
    print("Operating environment")

    print()
    print("AUTHORITY EPOCHS")
    print("-" * 70)

    print(
        f"{result.approved.authority_epoch}"
        f" -> {result.substituted.authority_epoch}"
        f" -> {result.recovered.authority_epoch}"
    )

    print()
    print(
        "Interpretation: model substitution did not invalidate the "
        "historical evaluation artifact. The artifact remains valid "
        "for the model for which it was evaluated, but it does not "
        "provide assurance support for the substituted model."
    )


def main() -> None:
    result = run_s2()
    print_s2_result(result)


if __name__ == "__main__":
    main()
