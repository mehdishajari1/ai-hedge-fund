"""
S7 — Stakeholder Policy Divergence

Purpose
-------
Demonstrate that identical evidence, assurance state, context, declared
authority, and system configuration can produce different effective authority
when stakeholder risk policies differ.

The experiment uses two stakeholders:

1. CONSERVATIVE
   - unassured max order value: $1,000
   - live trading disabled when unassured
   - human gate required
   - resulting AAL contracts to 1

2. RISK-TOLERANT
   - unassured max order value: $5,000
   - constrained live trading remains permitted
   - no mandatory human gate
   - baseline AAL remains available

Both stakeholders observe exactly the same material change:

    market_regime: normal -> novel

The same assurance evidence remains historically valid but becomes
non-applicable. Both therefore derive the same assurance state:

    SAFE_AUTONOMOUS_TRADING -> UNASSURED

Only stakeholder policy differs.

Expected result
---------------
Same evidence + same assurance != same operational authority.

Instead:

    Evidence
        -> Assurance
        -> Stakeholder Policy
        -> Effective Authority
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

MODEL_ID = "MODEL-APPROVED-01"
PROMPT_ID = "PROMPT-FIXED-01"
TOOLS_ID = "TOOLS-FIXED-01"
CREDENTIALS_ID = "CREDENTIAL-FIXED-01"
TGP_ID = "TGP-FIXED-01"

NORMAL_REGIME = "normal"
NOVEL_REGIME = "novel"


@dataclass(frozen=True)
class S7Snapshot:
    label: str
    stakeholder: str
    policy_id: str

    model_id: str
    market_regime: str
    prompt_id: str
    tools_id: str
    credentials_id: str
    declared_authority_id: str

    evidence_id: str
    evidence_valid: bool
    evidence_applicable: bool

    claim_state: AssuranceState

    authority_epoch: int
    aal: int
    max_order_value: float | None

    paper_allowed: bool
    live_allowed: bool


@dataclass(frozen=True)
class S7StakeholderResult:
    before: S7Snapshot
    after: S7Snapshot
    transition: object


@dataclass(frozen=True)
class S7Result:
    conservative: S7StakeholderResult
    tolerant: S7StakeholderResult


def _make_context() -> GovernanceContext:
    return GovernanceContext(
        values={
            "model_id": MODEL_ID,
            "market_regime": NORMAL_REGIME,
            "prompt_id": PROMPT_ID,
            "tools_id": TOOLS_ID,
            "credentials_id": CREDENTIALS_ID,
            "declared_authority_id": TGP_ID,
            "environment": "paper/live",
        }
    )


def _make_evidence() -> AssuranceEvidence:
    """
    Identical evidence definition for both stakeholders.

    The evaluation remains valid throughout S7, but its applicability depends
    on the current market regime.
    """

    return AssuranceEvidence(
        evidence_id="E-S7-01",
        subject="portfolio_manager",
        evidence_type="evaluation",
        supports={CLAIM_ID},
        assumptions={
            "model_id": {MODEL_ID},
            "market_regime": {"normal", "elevated"},
        },
        valid=True,
    )


def _conservative_policy() -> StakeholderRiskPolicy:
    return StakeholderRiskPolicy(
        policy_id="S7-CONSERVATIVE",
        unassured_max_order_value=1_000.0,
        allow_live_when_unassured=False,
        require_human_gate_when_unassured=True,
    )


def _tolerant_policy() -> StakeholderRiskPolicy:
    return StakeholderRiskPolicy(
        policy_id="S7-RISK-TOLERANT",
        unassured_max_order_value=5_000.0,
        allow_live_when_unassured=True,
        require_human_gate_when_unassured=False,
    )


def _build_stakeholder(
    policy: StakeholderRiskPolicy,
) -> tuple[
    GovernanceContext,
    AssuranceEvidence,
    AssuranceDependencyGraph,
    GovernanceControlPlane,
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
    stakeholder: str,
    policy: StakeholderRiskPolicy,
    context: GovernanceContext,
    evidence: AssuranceEvidence,
    graph: AssuranceDependencyGraph,
    control: GovernanceControlPlane,
) -> S7Snapshot:
    authority = control.authority

    return S7Snapshot(
        label=label,
        stakeholder=stakeholder,
        policy_id=policy.policy_id,

        model_id=context.get("model_id"),
        market_regime=context.get("market_regime"),
        prompt_id=context.get("prompt_id"),
        tools_id=context.get("tools_id"),
        credentials_id=context.get("credentials_id"),
        declared_authority_id=context.get("declared_authority_id"),

        evidence_id=evidence.evidence_id,
        evidence_valid=evidence.valid,
        evidence_applicable=evidence.is_applicable(context),

        claim_state=_claim_state(graph, context),

        authority_epoch=authority.epoch,
        aal=authority.aal,
        max_order_value=authority.max_order_value,

        paper_allowed="paper_order" in authority.allowed_actions,
        live_allowed="live_order" in authority.allowed_actions,
    )


def _run_stakeholder(
    *,
    stakeholder: str,
    policy: StakeholderRiskPolicy,
) -> S7StakeholderResult:
    context, evidence, graph, control, engine = _build_stakeholder(policy)

    before = _snapshot(
        label="BEFORE MATERIAL CHANGE",
        stakeholder=stakeholder,
        policy=policy,
        context=context,
        evidence=evidence,
        graph=graph,
        control=control,
    )

    transition = engine.observe_context(
        "market_regime",
        NOVEL_REGIME,
    )

    after = _snapshot(
        label="AFTER MATERIAL CHANGE",
        stakeholder=stakeholder,
        policy=policy,
        context=context,
        evidence=evidence,
        graph=graph,
        control=control,
    )

    return S7StakeholderResult(
        before=before,
        after=after,
        transition=transition,
    )


def run_s7() -> S7Result:
    return S7Result(
        conservative=_run_stakeholder(
            stakeholder="CONSERVATIVE",
            policy=_conservative_policy(),
        ),
        tolerant=_run_stakeholder(
            stakeholder="RISK-TOLERANT",
            policy=_tolerant_policy(),
        ),
    )


def _yes_no(value: bool) -> str:
    return "YES" if value else "NO"


def _money(value: float | None) -> str:
    if value is None:
        return "None"

    return f"${value:,.0f}"


def _print_snapshot(snapshot: S7Snapshot) -> None:
    print()
    print(snapshot.label)
    print("-" * len(snapshot.label))

    print(f"Stakeholder:            {snapshot.stakeholder}")
    print(f"Policy:                 {snapshot.policy_id}")
    print(f"Model:                  {snapshot.model_id}")
    print(f"Market regime:          {snapshot.market_regime}")

    print(f"Evidence ID:            {snapshot.evidence_id}")
    print(f"Evidence valid:         {_yes_no(snapshot.evidence_valid)}")
    print(f"Evidence applicable:    {_yes_no(snapshot.evidence_applicable)}")
    print(f"Assurance claim:        {snapshot.claim_state.value}")

    print(f"Authority epoch:        {snapshot.authority_epoch}")
    print(f"AAL:                    {snapshot.aal}")
    print(f"Max order value:        {_money(snapshot.max_order_value)}")
    print(f"Paper authority:        {_yes_no(snapshot.paper_allowed)}")
    print(f"Live authority:         {_yes_no(snapshot.live_allowed)}")


def _print_stakeholder(result: S7StakeholderResult) -> None:
    _print_snapshot(result.before)
    _print_snapshot(result.after)


def print_s7_result(result: S7Result) -> None:
    print()
    print("=" * 74)
    print("S7 — STAKEHOLDER POLICY DIVERGENCE")
    print("=" * 74)

    print()
    print("A. CONSERVATIVE STAKEHOLDER")
    print("=" * 74)

    _print_stakeholder(result.conservative)

    print()
    print("B. RISK-TOLERANT STAKEHOLDER")
    print("=" * 74)

    _print_stakeholder(result.tolerant)

    c = result.conservative.after
    t = result.tolerant.after

    print()
    print("CONTROLLED COMPARISON AFTER IDENTICAL MATERIAL CHANGE")
    print("-" * 74)

    print(f"Context equal:           {_yes_no(c.market_regime == t.market_regime)}")
    print(f"Model equal:             {_yes_no(c.model_id == t.model_id)}")
    print(f"Evidence equal:          {_yes_no(c.evidence_id == t.evidence_id)}")
    print(f"Evidence valid equal:    {_yes_no(c.evidence_valid == t.evidence_valid)}")
    print(
        f"Applicability equal:     "
        f"{_yes_no(c.evidence_applicable == t.evidence_applicable)}"
    )
    print(f"Assurance equal:         {_yes_no(c.claim_state == t.claim_state)}")
    print(
        f"Declared authority same: "
        f"{_yes_no(c.declared_authority_id == t.declared_authority_id)}"
    )

    print()
    print("POLICY-DERIVED AUTHORITY")
    print("-" * 74)

    print(
        f"Conservative AAL:        {c.aal}"
    )
    print(
        f"Risk-tolerant AAL:       {t.aal}"
    )

    print(
        f"Conservative max order:  {_money(c.max_order_value)}"
    )
    print(
        f"Risk-tolerant max order: {_money(t.max_order_value)}"
    )

    print(
        f"Conservative live:       {_yes_no(c.live_allowed)}"
    )
    print(
        f"Risk-tolerant live:      {_yes_no(t.live_allowed)}"
    )

    print()
    print("CAUSAL RESULT")
    print("-" * 74)

    print(
        "Both stakeholders observed the same evidence-applicability loss "
        "and derived the same UNASSURED assurance state."
    )

    print(
        "Different stakeholder risk policies then produced different "
        "effective authority."
    )

    print()
    print(
        "Interpretation: assurance constrains the evidence available for "
        "authorization, but assurance does not uniquely determine authority. "
        "Stakeholder risk policy mediates assurance into operational authority."
    )


def main() -> None:
    result = run_s7()
    print_s7_result(result)


if __name__ == "__main__":
    main()
