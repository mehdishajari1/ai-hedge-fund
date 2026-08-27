"""Visible end-to-end demonstration of ACCA governance.

Run:

    poetry run python -m hedge_fund.governance.demo_acca
"""

from hedge_fund.brokers.models import Order

from hedge_fund.governance.acca import ACCAEngine
from hedge_fund.governance.assurance_graph import (
    AssuranceDependencyGraph,
)
from hedge_fund.governance.context import GovernanceContext
from hedge_fund.governance.control import GovernanceControlPlane
from hedge_fund.governance.evidence import AssuranceEvidence
from hedge_fund.governance.materiality import MaterialityEvaluator
from hedge_fund.governance.policy import StakeholderRiskPolicy


CLAIM = "SAFE_AUTONOMOUS_TRADING"


def divider(title: str) -> None:
    print()
    print("=" * 72)
    print(title)
    print("=" * 72)


def print_state(
    label: str,
    context: GovernanceContext,
    control: GovernanceControlPlane,
    evidence: AssuranceEvidence,
) -> None:

    claim = control.claims[CLAIM]
    authority = control.authority

    print()
    print(label)
    print("-" * 72)

    print(
        f"Market regime          : "
        f"{context.get('market_regime')}"
    )

    print(
        f"Evidence E-17          : "
        f"{'APPLICABLE' if evidence.is_applicable(context) else 'NOT APPLICABLE'}"
    )

    print(
        f"Assurance claim        : "
        f"{claim.state.value.upper()}"
    )

    print(
        f"Authority epoch        : "
        f"{authority.epoch}"
    )

    print(
        f"Live order             : "
        f"{'ALLOWED' if 'live_order' in authority.allowed_actions else 'DENIED'}"
    )

    print(
        f"Paper order            : "
        f"{'ALLOWED' if 'paper_order' in authority.allowed_actions else 'DENIED'}"
    )

    max_value = (
        "UNLIMITED"
        if authority.max_order_value is None
        else f"${authority.max_order_value:,.0f}"
    )

    print(
        f"Maximum order value    : "
        f"{max_value}"
    )

    print(
        f"Allowed autonomy (AAL) : "
        f"{authority.aal}"
    )

    print(
        f"Human gate             : "
        f"{'REQUIRED' if authority.aal <= 1 else 'NO'}"
    )


def build_acca(
    *,
    policy: StakeholderRiskPolicy,
):
    context = GovernanceContext(
        values={
            "market_regime": "normal",
            "dashboard_theme": "dark",
        }
    )

    evidence = AssuranceEvidence(
        evidence_id="E-17",
        subject="portfolio_manager",
        evidence_type="trading_evaluation",
        supports={CLAIM},
        assumptions={
            "market_regime": {
                "normal",
                "elevated",
            },
        },
    )

    graph = AssuranceDependencyGraph(
        [evidence]
    )

    materiality = MaterialityEvaluator(
        [evidence]
    )

    control = GovernanceControlPlane.acca_trading_demo(
        policy.policy_id,
        max_order_value=10_000.0,
        policy=policy,
    )

    engine = ACCAEngine(
        context=context,
        assurance_graph=graph,
        materiality=materiality,
        control_plane=control,
    )

    return engine, context, evidence, control


def print_change(result) -> None:
    print(
        f"Dependency relevant    : "
        f"{result.dependency_relevant}"
    )

    print(
        f"Assurance changed      : "
        f"{result.assurance_changed}"
    )

    print(
        f"Affected evidence      : "
        f"{sorted(result.affected_evidence)}"
    )

    print(
        f"Affected claims        : "
        f"{sorted(result.affected_claims)}"
    )

    print(
        f"Authority epoch        : "
        f"{result.old_epoch} -> {result.new_epoch}"
    )


def print_decision(
    label: str,
    control: GovernanceControlPlane,
    order: Order,
) -> None:

    decision = control.decide_order(
        order,
        live=True,
    )

    value = abs(
        order.quantity * order.price
    )

    print()
    print(label)
    print("-" * 72)

    print(f"Ticker                  : {order.ticker}")
    print(f"Quantity                : {order.quantity}")
    print(f"Price                   : ${order.price:,.2f}")
    print(f"Order value             : ${value:,.2f}")

    print(
        f"Governance decision     : "
        f"{decision.decision.value.upper()}"
    )

    print(
        f"Reason code             : "
        f"{decision.reason_code}"
    )

    print(
        f"Authority epoch         : "
        f"{decision.authority_epoch}"
    )

    print(
        f"Explanation             : "
        f"{decision.explanation}"
    )


def main() -> None:

    divider(
        "ACCA — ASSURANCE-CONDITIONED CONTINUOUS AUTHORIZATION"
    )

    print()
    print(
        "Scenario: the AI trading agent does NOT change."
    )
    print(
        "Only the market environment changes."
    )

    conservative = StakeholderRiskPolicy(
        policy_id="conservative-trader",
        unassured_max_order_value=1_000.0,
        allow_live_when_unassured=False,
        require_human_gate_when_unassured=True,
    )

    tolerant = StakeholderRiskPolicy(
        policy_id="tolerant-trader",
        unassured_max_order_value=1_000.0,
        allow_live_when_unassured=True,
        require_human_gate_when_unassured=True,
    )

    (
        acca_c,
        context_c,
        evidence_c,
        control_c,
    ) = build_acca(
        policy=conservative
    )

    (
        acca_t,
        context_t,
        evidence_t,
        control_t,
    ) = build_acca(
        policy=tolerant
    )

    # For now this represents an order proposed by the AIHF
    # portfolio-management/execution pipeline.
    #
    # In the next step we will replace this construction with
    # an actual order produced by the AIHF pipeline.
    
    proposed_order = Order(
        ticker="NVDA",
        side="buy",
        quantity=40,
        price=200.0,
    )

    divider(
        "T0 — NORMAL MARKET"
    )

    print_state(
        "CONSERVATIVE TRADER",
        context_c,
        control_c,
        evidence_c,
    )

    print_decision(
        "PROPOSED NVDA ORDER — BEFORE EVENT",
        control_c,
        proposed_order,
    )

    divider(
        "T1 — NON-MATERIAL CHANGE"
    )

    print(
        "\nEVENT: dashboard_theme dark -> light\n"
    )

    result = acca_c.observe_context(
        "dashboard_theme",
        "light",
    )

    print_change(result)

    divider(
        "T2 — RELEVANT BUT STILL-SUPPORTED CHANGE"
    )

    print(
        "\nEVENT: market_regime normal -> elevated\n"
    )

    result = acca_c.observe_context(
        "market_regime",
        "elevated",
    )

    print_change(result)

    print_state(
        "CONSERVATIVE TRADER",
        context_c,
        control_c,
        evidence_c,
    )

    divider(
        "T3 — EXTREME MARKET EVENT"
    )

    print(
        "\nEVENT: market_regime elevated -> extreme\n"
    )

    result_c = acca_c.observe_context(
        "market_regime",
        "extreme",
    )

    # Same external event for the second trader.
    acca_t.observe_context(
        "market_regime",
        "extreme",
    )

    print_change(result_c)

    print_state(
        "CONSERVATIVE TRADER",
        context_c,
        control_c,
        evidence_c,
    )

    print_state(
        "TOLERANT TRADER",
        context_t,
        control_t,
        evidence_t,
    )

    divider(
        "T4 — SAME AIHF ORDER AFTER ASSURANCE LOSS"
    )

    print_decision(
        "CONSERVATIVE TRADER",
        control_c,
        proposed_order,
    )

    print_decision(
        "TOLERANT TRADER",
        control_t,
        proposed_order,
    )

    small_order = Order(
        ticker="NVDA",
        side="buy",
        quantity=4,
        price=200.0,
    )

    divider(
        "T5 — CONSTRAINED ACTION AFTER ASSURANCE LOSS"
    )

    print_state(
        "CONSERVATIVE TRADER — CURRENT STATE",
        context_c,
        control_c,
        evidence_c,
    )

    print_decision(
        "CONSERVATIVE TRADER — $800 NVDA ORDER",
        control_c,
        small_order,
    )

    print_state(
        "TOLERANT TRADER — CURRENT STATE",
        context_t,
        control_t,
        evidence_t,
    )

    print_decision(
        "TOLERANT TRADER — $800 NVDA ORDER",
        control_t,
        small_order,
    )

    divider(
        "DEMONSTRATION COMPLETE"
    )

    print()
    print(
        "Agent capability       : unchanged"
    )
    print(
        "Model                  : unchanged"
    )
    print(
        "Credentials            : unchanged"
    )
    print(
        "Proposed order         : unchanged"
    )
    print(
        "Operating environment  : changed"
    )
    print(
        "Evidence applicability : changed"
    )
    print(
        "Assurance state        : changed"
    )
    print(
        "Effective authority    : policy-dependent"
    )
    print()


if __name__ == "__main__":
    main()
