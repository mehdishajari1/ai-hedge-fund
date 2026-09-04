"""
S10 — Stale Authorization / Authority Epoch Rejection

Purpose
-------
Demonstrate that an action authorized under an earlier authority epoch cannot
cross the runtime enforcement boundary after a material change advances the
authority epoch.

The experiment contains two paths.

A. Material-change path
-----------------------
1. Agent receives authorization at epoch 1.
2. Before execution, a material context change occurs.
3. ACCA recalculates authority and advances the epoch to 2.
4. The action attempts execution using epoch 1.
5. Runtime epoch enforcement rejects the stale authorization.
6. Broker is not invoked.

B. Non-material control path
----------------------------
1. Agent receives authorization at epoch 1.
2. An irrelevant context value changes.
3. Authority remains unchanged and epoch stays 1.
4. The epoch-1 action remains current.
5. Runtime execution proceeds.

This experiment validates the runtime consequence of authority epochs.
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

NORMAL_REGIME = "normal"
NOVEL_REGIME = "novel"


@dataclass
class RecordingBroker:
    """
    Minimal broker stub for verifying whether execution crossed the
    enforcement boundary.
    """

    calls: int = 0

    def place_order(self, order: object) -> str:
        self.calls += 1
        return "FILLED"


@dataclass(frozen=True)
class S10Snapshot:
    label: str

    market_regime: str
    dashboard_theme: str

    evidence_valid: bool
    evidence_applicable: bool
    claim_state: AssuranceState

    authority_epoch: int
    aal: int
    max_order_value: float | None

    live_allowed: bool


@dataclass(frozen=True)
class S10MaterialResult:
    before: S10Snapshot
    after_material_change: S10Snapshot

    authorized_epoch: int

    stale_rejected: bool
    exception_type: str | None

    broker_calls_before: int
    broker_calls_after: int

    transition: object


@dataclass(frozen=True)
class S10NonMaterialResult:
    before: S10Snapshot
    after_non_material_change: S10Snapshot

    authorized_epoch: int

    execution_succeeded: bool

    broker_calls_before: int
    broker_calls_after: int

    transition: object


@dataclass(frozen=True)
class S10Result:
    material: S10MaterialResult
    non_material: S10NonMaterialResult


def _make_context() -> GovernanceContext:
    return GovernanceContext(
        values={
            "model_id": MODEL_ID,
            "market_regime": NORMAL_REGIME,
            "dashboard_theme": "light",
        }
    )


def _make_evidence() -> AssuranceEvidence:
    """
    Evidence remains valid throughout the experiment.

    It applies only in normal/elevated regimes.
    """

    return AssuranceEvidence(
        evidence_id="E-S10-01",
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
        policy_id="s10-policy",
        unassured_max_order_value=1_000.0,
        allow_live_when_unassured=False,
        require_human_gate_when_unassured=True,
    )


def build_s10() -> tuple[
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
) -> S10Snapshot:
    authority = control.authority

    return S10Snapshot(
        label=label,
        market_regime=context.get("market_regime"),
        dashboard_theme=context.get("dashboard_theme"),
        evidence_valid=evidence.valid,
        evidence_applicable=evidence.is_applicable(context),
        claim_state=_claim_state(graph, context),
        authority_epoch=authority.epoch,
        aal=authority.aal,
        max_order_value=authority.max_order_value,
        live_allowed="live_order" in authority.allowed_actions,
    )


def run_material_path() -> S10MaterialResult:
    """
    Authorize at epoch 1, then trigger a material change and attempt execution
    using the stale epoch.
    """

    context, evidence, graph, control, engine = build_s10()
    broker = RecordingBroker()

    before = _snapshot(
        label="AUTHORIZED STATE",
        context=context,
        evidence=evidence,
        graph=graph,
        control=control,
    )

    # This represents the authority epoch bound to the action authorization.
    authorized_epoch = control.authority.epoch

    broker_calls_before = broker.calls

    # Material change:
    # evidence remains valid but becomes non-applicable.
    transition = engine.observe_context(
        "market_regime",
        NOVEL_REGIME,
    )

    after_material_change = _snapshot(
        label="AFTER MATERIAL CHANGE",
        context=context,
        evidence=evidence,
        graph=graph,
        control=control,
    )

    stale_rejected = False
    exception_type = None

    try:
        # Runtime PEP check immediately before consequential execution.
        control.assert_epoch(authorized_epoch)

        # This must never execute after the authority epoch changes.
        broker.place_order(
            {
                "ticker": "NVDA",
                "action": "live_order",
                "value": 5_000.0,
            }
        )

    except Exception as exc:
        stale_rejected = True
        exception_type = type(exc).__name__

    broker_calls_after = broker.calls

    return S10MaterialResult(
        before=before,
        after_material_change=after_material_change,
        authorized_epoch=authorized_epoch,
        stale_rejected=stale_rejected,
        exception_type=exception_type,
        broker_calls_before=broker_calls_before,
        broker_calls_after=broker_calls_after,
        transition=transition,
    )


def run_non_material_path() -> S10NonMaterialResult:
    """
    Demonstrate that an irrelevant change does not invalidate the epoch.
    """

    context, evidence, graph, control, engine = build_s10()
    broker = RecordingBroker()

    before = _snapshot(
        label="AUTHORIZED STATE",
        context=context,
        evidence=evidence,
        graph=graph,
        control=control,
    )

    authorized_epoch = control.authority.epoch
    broker_calls_before = broker.calls

    transition = engine.observe_context(
        "dashboard_theme",
        "dark",
    )

    after_non_material_change = _snapshot(
        label="AFTER NON-MATERIAL CHANGE",
        context=context,
        evidence=evidence,
        graph=graph,
        control=control,
    )

    execution_succeeded = False

    try:
        control.assert_epoch(authorized_epoch)

        broker.place_order(
            {
                "ticker": "NVDA",
                "action": "live_order",
                "value": 5_000.0,
            }
        )

        execution_succeeded = True

    except Exception:
        execution_succeeded = False

    broker_calls_after = broker.calls

    return S10NonMaterialResult(
        before=before,
        after_non_material_change=after_non_material_change,
        authorized_epoch=authorized_epoch,
        execution_succeeded=execution_succeeded,
        broker_calls_before=broker_calls_before,
        broker_calls_after=broker_calls_after,
        transition=transition,
    )


def run_s10() -> S10Result:
    return S10Result(
        material=run_material_path(),
        non_material=run_non_material_path(),
    )


def _yes_no(value: bool) -> str:
    return "YES" if value else "NO"


def _money(value: float | None) -> str:
    if value is None:
        return "None"

    return f"${value:,.0f}"


def _print_snapshot(snapshot: S10Snapshot) -> None:
    print()
    print(snapshot.label)
    print("-" * len(snapshot.label))

    print(f"Market regime:          {snapshot.market_regime}")
    print(f"Dashboard theme:        {snapshot.dashboard_theme}")
    print(f"Evidence valid:         {_yes_no(snapshot.evidence_valid)}")
    print(f"Evidence applicable:    {_yes_no(snapshot.evidence_applicable)}")
    print(f"Assurance claim:        {snapshot.claim_state.value}")
    print(f"Authority epoch:        {snapshot.authority_epoch}")
    print(f"AAL:                    {snapshot.aal}")
    print(f"Max order value:        {_money(snapshot.max_order_value)}")
    print(f"Live authority:         {_yes_no(snapshot.live_allowed)}")


def print_s10_result(result: S10Result) -> None:
    print()
    print("=" * 72)
    print("S10 — STALE AUTHORIZATION / AUTHORITY EPOCH REJECTION")
    print("=" * 72)

    print()
    print("A. MATERIAL CHANGE PATH")
    print("=" * 72)

    _print_snapshot(result.material.before)
    _print_snapshot(result.material.after_material_change)

    print()
    print("Runtime enforcement")
    print("-" * 72)

    print(
        f"Authorization bound to epoch: "
        f"{result.material.authorized_epoch}"
    )

    print(
        f"Current authority epoch:       "
        f"{result.material.after_material_change.authority_epoch}"
    )

    print(
        f"Stale authorization rejected:  "
        f"{_yes_no(result.material.stale_rejected)}"
    )

    print(
        f"Exception:                     "
        f"{result.material.exception_type}"
    )

    print(
        f"Broker calls:                  "
        f"{result.material.broker_calls_before}"
        f" -> {result.material.broker_calls_after}"
    )

    print()
    print("B. NON-MATERIAL CONTROL PATH")
    print("=" * 72)

    _print_snapshot(result.non_material.before)
    _print_snapshot(result.non_material.after_non_material_change)

    print()
    print("Runtime enforcement")
    print("-" * 72)

    print(
        f"Authorization bound to epoch: "
        f"{result.non_material.authorized_epoch}"
    )

    print(
        f"Current authority epoch:       "
        f"{result.non_material.after_non_material_change.authority_epoch}"
    )

    print(
        f"Execution succeeded:           "
        f"{_yes_no(result.non_material.execution_succeeded)}"
    )

    print(
        f"Broker calls:                  "
        f"{result.non_material.broker_calls_before}"
        f" -> {result.non_material.broker_calls_after}"
    )

    print()
    print("CAUSAL RESULT")
    print("-" * 72)

    print(
        "Material change -> authority recalculation -> epoch advance -> "
        "old authorization becomes stale -> runtime enforcement rejects "
        "execution before the broker boundary."
    )

    print(
        "Non-material change -> no authority recalculation -> epoch remains "
        "current -> previously authorized action can proceed."
    )


def main() -> None:
    result = run_s10()
    print_s10_result(result)


if __name__ == "__main__":
    main()
