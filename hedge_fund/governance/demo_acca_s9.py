"""
S9 — Non-Material Context Change / Selectivity

Purpose
-------
Demonstrate that ACCA does not recalculate assurance or authority when a
context change is unrelated to any evidence dependency.

The experiment changes only an irrelevant context attribute:

    dashboard_theme: "light" -> "dark"

All assurance-relevant dependencies remain unchanged.

Expected result
---------------
- no affected evidence
- no affected assurance claims
- assurance does not change
- effective authority does not change
- authority epoch does not advance

This demonstrates selectivity and avoids unnecessary governance churn.
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


@dataclass(frozen=True)
class S9Snapshot:
    label: str

    dashboard_theme: str

    evidence_valid: bool
    evidence_applicable: bool
    claim_state: AssuranceState

    authority_epoch: int
    aal: int
    max_order_value: float | None

    paper_allowed: bool
    live_allowed: bool


@dataclass(frozen=True)
class S9Result:
    before: S9Snapshot
    after: S9Snapshot

    transition: object


def _make_context() -> GovernanceContext:
    return GovernanceContext(
        values={
            "model_id": MODEL_ID,
            "market_regime": "normal",
            "dashboard_theme": "light",
            "prompt_id": PROMPT_ID,
            "tools_id": TOOLS_ID,
            "credentials_id": CREDENTIALS_ID,
            "declared_authority_id": TGP_ID,
            "environment": "paper/live",
        }
    )


def _make_evidence() -> AssuranceEvidence:
    """
    Evidence depends on model_id and market_regime.

    It deliberately does NOT depend on dashboard_theme.
    """

    return AssuranceEvidence(
        evidence_id="E-S9-01",
        subject="portfolio_manager",
        evidence_type="evaluation",
        supports={CLAIM_ID},
        assumptions={
            "model_id": {MODEL_ID},
            "market_regime": {"normal", "elevated"},
        },
        valid=True,
    )


def _make_policy() -> StakeholderRiskPolicy:
    return StakeholderRiskPolicy(
        policy_id="s9-selectivity-policy",
        unassured_max_order_value=1_000.0,
        allow_live_when_unassured=False,
        require_human_gate_when_unassured=True,
    )


def build_s9() -> tuple[
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
) -> S9Snapshot:
    authority = control.authority

    return S9Snapshot(
        label=label,
        dashboard_theme=context.get("dashboard_theme"),
        evidence_valid=evidence.valid,
        evidence_applicable=evidence.is_applicable(context),
        claim_state=_claim_state(graph, context),
        authority_epoch=authority.epoch,
        aal=authority.aal,
        max_order_value=authority.max_order_value,
        paper_allowed="paper_order" in authority.allowed_actions,
        live_allowed="live_order" in authority.allowed_actions,
    )


def run_s9() -> S9Result:
    context, evidence, graph, control, engine = build_s9()

    before = _snapshot(
        label="BEFORE IRRELEVANT CHANGE",
        context=context,
        evidence=evidence,
        graph=graph,
        control=control,
    )

    transition = engine.observe_context(
        "dashboard_theme",
        "dark",
    )

    after = _snapshot(
        label="AFTER IRRELEVANT CHANGE",
        context=context,
        evidence=evidence,
        graph=graph,
        control=control,
    )

    return S9Result(
        before=before,
        after=after,
        transition=transition,
    )


def _yes_no(value: bool) -> str:
    return "YES" if value else "NO"


def _money(value: float | None) -> str:
    if value is None:
        return "None"

    return f"${value:,.0f}"


def _print_snapshot(snapshot: S9Snapshot) -> None:
    print()
    print(snapshot.label)
    print("-" * len(snapshot.label))

    print(f"Dashboard theme:        {snapshot.dashboard_theme}")
    print(f"Evidence valid:         {_yes_no(snapshot.evidence_valid)}")
    print(f"Evidence applicable:    {_yes_no(snapshot.evidence_applicable)}")
    print(f"Assurance claim:        {snapshot.claim_state.value}")
    print(f"Authority epoch:        {snapshot.authority_epoch}")
    print(f"AAL:                    {snapshot.aal}")
    print(f"Max order value:        {_money(snapshot.max_order_value)}")
    print(f"Paper authority:        {_yes_no(snapshot.paper_allowed)}")
    print(f"Live authority:         {_yes_no(snapshot.live_allowed)}")


def print_s9_result(result: S9Result) -> None:
    print()
    print("=" * 70)
    print("S9 — NON-MATERIAL CONTEXT CHANGE / SELECTIVITY")
    print("=" * 70)

    _print_snapshot(result.before)
    _print_snapshot(result.after)

    transition = result.transition

    print()
    print("TRANSITION")
    print("-" * 70)

    print(f"Affected evidence:      {transition.affected_evidence}")
    print(f"Affected claims:        {transition.affected_claims}")
    print(f"Assurance changed:      {_yes_no(transition.assurance_changed)}")
    print(
        f"Authority epoch:        "
        f"{transition.old_epoch} -> {transition.new_epoch}"
    )

    print()
    print("CAUSAL RESULT")
    print("-" * 70)

    print(
        "dashboard_theme changed, but no evidence depends on that "
        "context attribute."
    )

    print(
        "Therefore no evidence applicability changed, no assurance claim "
        "changed, effective authority remained unchanged, and the "
        "authority epoch did not advance."
    )

    print()
    print(
        "Interpretation: ACCA reacts selectively to material changes "
        "rather than treating every context change as a reason to "
        "re-authorize the agent."
    )


def main() -> None:
    result = run_s9()
    print_s9_result(result)


if __name__ == "__main__":
    main()
