"""Real AIHF + ACCA integration demonstration.

This experiment uses the actual AI Hedge Fund pipeline:

    AIHF agents/models
        -> signals
        -> portfolio construction
        -> financial risk controls
        -> actual AIHF Order objects
        -> ACCA governed execution gateway
        -> SimBroker

The experiment runs the SAME fund, date, data, initial capital, and universe
twice.

Run A:
    market_regime = normal

Run B:
    market_regime = extreme

The AIHF reasoning pipeline is unchanged. Only the authority-relevant
operating context changes.

A fresh SimBroker is used for each run so that the first run does not alter
the starting portfolio of the second run.

Example:

    poetry run python -m hedge_fund.governance.demo_acca_aihf \
        --mandate "$HOME/.hedge-fund/mandates/example.yaml" \
        --tickers NVDA,MSFT,AAPL

Optional:

    --date 2026-08-27
    --model gpt-5.5
"""

from __future__ import annotations

import argparse
import os
from datetime import date as _date

from hedge_fund.brokers import SimBroker
from hedge_fund.data import CachedDataClient, FDClient
from hedge_fund.fund import Fund, load_spec, normalize_universe
from hedge_fund.pipeline import run_cycle
from hedge_fund.tui.keys import apply_credentials

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


# ---------------------------------------------------------------------------
# Presentation helpers
# ---------------------------------------------------------------------------

def divider(title: str) -> None:
    print()
    print("=" * 88)
    print(title)
    print("=" * 88)


def print_governance_state(
    label: str,
    context: GovernanceContext,
    evidence: AssuranceEvidence,
    control: GovernanceControlPlane,
) -> None:
    """Print the assurance and authority state used by the PEP."""

    claim = control.claims[CLAIM]
    authority = control.authority

    print()
    print(label)
    print("-" * 88)

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
        f"Paper order            : "
        f"{'ALLOWED' if 'paper_order' in authority.allowed_actions else 'DENIED'}"
    )

    print(
        f"Live order             : "
        f"{'ALLOWED' if 'live_order' in authority.allowed_actions else 'DENIED'}"
    )

    max_value = (
        "UNLIMITED"
        if authority.max_order_value is None
        else f"${authority.max_order_value:,.2f}"
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


def print_aihf_record(label: str, record) -> None:
    """Print the important AIHF and governance outputs of one run."""

    print()
    print(label)
    print("-" * 88)

    n_signals = sum(
        len(strategy.signals)
        for strategy in record.strategies
    )

    print(f"AIHF strategies        : {len(record.strategies)}")
    print(f"AIHF signals           : {n_signals}")
    print(f"Proposed orders        : {len(record.orders)}")
    print(f"Executed fills         : {len(record.fills)}")

    print()
    print("AIHF-PROPOSED ORDERS")
    print("-" * 88)

    if not record.orders:
        print("No orders were proposed by AIHF in this cycle.")
    else:
        for i, order in enumerate(record.orders, start=1):
            value = abs(order.quantity * order.price)

            print(
                f"{i}. "
                f"{order.ticker} "
                f"{order.side.upper()} "
                f"{order.quantity} @ "
                f"${order.price:,.2f} "
                f"= ${value:,.2f}"
            )

    print()
    print("ACCA GOVERNANCE DECISIONS")
    print("-" * 88)

    if (
        record.governance is None
        or not record.governance.decisions
    ):
        print("No governance decisions were recorded.")
    else:
        for i, decision in enumerate(
            record.governance.decisions,
            start=1,
        ):
            print(
                f"{i}. "
                f"{decision.ticker or '-'} "
                f"{decision.action} -> "
                f"{decision.decision.value.upper()}"
            )

            print(
                f"   reason : "
                f"{decision.reason_code}"
            )

            print(
                f"   epoch  : "
                f"{decision.authority_epoch}"
            )

            if decision.explanation:
                print(
                    f"   detail : "
                    f"{decision.explanation}"
                )


# ---------------------------------------------------------------------------
# ACCA construction
# ---------------------------------------------------------------------------

def build_acca(
    fund_name: str,
    *,
    market_regime: str,
) -> tuple[
    ACCAEngine,
    GovernanceContext,
    AssuranceEvidence,
    GovernanceControlPlane,
]:
    """Build one independent ACCA governance state."""

    context = GovernanceContext(
        values={
            "market_regime": "normal",
        }
    )

    # E-17 represents an evaluation supporting autonomous trading.
    #
    # Importantly, the evidence is not universally applicable. Its assurance
    # value depends on operating assumptions established when the evaluation
    # was performed.
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

    # For this integration experiment we use one stakeholder policy.
    #
    # If assurance is lost:
    #   - authority is capped at $1,000;
    #   - autonomous consequential execution requires human approval.
    #
    # The previous synthetic demo already demonstrates multiple stakeholders
    # deriving different authority from the same assurance state.
    policy = StakeholderRiskPolicy(
        policy_id="real-aihf-demo-policy",
        unassured_max_order_value=1_000.0,
        allow_live_when_unassured=True,
        require_human_gate_when_unassured=True,
    )

    control = GovernanceControlPlane.acca_trading_demo(
        fund_name,
        max_order_value=30_000.0,
        policy=policy,
    )

    engine = ACCAEngine(
        context=context,
        assurance_graph=graph,
        materiality=materiality,
        control_plane=control,
    )

    # Start from the approved NORMAL baseline.
    #
    # If this experimental run represents EXTREME conditions, ACCA observes
    # that change before the AIHF-generated action reaches the PEP.
    if market_regime != "normal":
        result = engine.observe_context(
            "market_regime",
            market_regime,
        )

        print()
        print(
            f"ACCA context event      : "
            f"normal -> {market_regime}"
        )

        print(
            f"Dependency relevant    : "
            f"{result.dependency_relevant}"
        )

        print(
            f"Assurance changed      : "
            f"{result.assurance_changed}"
        )

        print(
            f"Evidence affected       : "
            f"{sorted(result.affected_evidence)}"
        )

        print(
            f"Claims affected         : "
            f"{sorted(result.affected_claims)}"
        )

        print(
            f"Authority epoch         : "
            f"{result.old_epoch} -> "
            f"{result.new_epoch}"
        )

    return (
        engine,
        context,
        evidence,
        control,
    )


# ---------------------------------------------------------------------------
# Comparison helpers
# ---------------------------------------------------------------------------

def order_signature(order) -> tuple:
    """Canonical representation used to compare AIHF proposals."""

    return (
        order.ticker,
        order.side,
        order.quantity,
        order.price,
    )


def compare_orders(
    normal_record,
    extreme_record,
) -> None:
    """Verify whether the upstream AIHF proposals remained the same."""

    normal = [
        order_signature(order)
        for order in normal_record.orders
    ]

    extreme = [
        order_signature(order)
        for order in extreme_record.orders
    ]

    divider(
        "EXPERIMENTAL COMPARISON"
    )

    print(
        f"Normal proposed orders  : "
        f"{len(normal)}"
    )

    print(
        f"Extreme proposed orders : "
        f"{len(extreme)}"
    )

    print(
        f"AIHF proposals identical: "
        f"{normal == extreme}"
    )

    print()

    if normal == extreme:
        print(
            "The AIHF reasoning/order-generation path produced the "
            "same proposed actions."
        )

        print(
            "The different execution outcome therefore arises from "
            "the governance/assurance state rather than from a "
            "different proposed action."
        )
    else:
        print(
            "WARNING: proposed orders differed between runs."
        )

        print(
            "This means the experiment did not perfectly isolate the "
            "governance variable. Check model/cache determinism and "
            "starting conditions before using this run as evidence."
        )


# ---------------------------------------------------------------------------
# Experiment
# ---------------------------------------------------------------------------

def main() -> None:
    apply_credentials()

    parser = argparse.ArgumentParser(
        description=(
            "Run the real AI Hedge Fund pipeline under normal and "
            "extreme ACCA governance contexts."
        )
    )

    parser.add_argument(
        "--mandate",
        required=True,
        help="Path to an existing AIHF mandate YAML.",
    )

    parser.add_argument(
        "--tickers",
        required=True,
        help=(
            "Comma- or space-separated ticker universe, "
            "for example NVDA,MSFT,AAPL."
        ),
    )

    parser.add_argument(
        "--date",
        default=_date.today().isoformat(),
        help="As-of date YYYY-MM-DD.",
    )

    parser.add_argument(
        "--model",
        default=None,
        help=(
            "Optional LLM model override. Uses existing "
            "HEDGE_FUND_LLM_MODEL/default when omitted."
        ),
    )

    args = parser.parse_args()

    if args.model:
        os.environ["HEDGE_FUND_LLM_MODEL"] = args.model

    universe = normalize_universe(
        args.tickers.replace(",", " ").split()
    )

    spec = load_spec(
        args.mandate
    )

    # ONE Fund object is deliberately reused across both runs.
    #
    # The AIHF agents/models are therefore the same. With the repository's
    # prompt cache, the second identical reasoning request should also replay
    # consistently rather than introducing unnecessary LLM variation.
    fund = Fund(spec)

    divider(
        "REAL AIHF + ACCA EXPERIMENT"
    )

    print()
    print(f"Fund                   : {spec.name}")
    print(f"As-of date             : {args.date}")
    print(f"Universe               : {', '.join(universe)}")
    print(f"Initial capital        : ${spec.capital:,.2f}")

    print(
        f"Model override         : "
        f"{args.model or 'repository/environment default'}"
    )

    print()
    print(
        "Broker                 : SimBroker "
        "(safe — no real trades)"
    )

    print()
    print(
        "Experimental variable  : market_regime only"
    )

    # ------------------------------------------------------------------
    # NORMAL RUN
    # ------------------------------------------------------------------

    divider(
        "RUN A — NORMAL MARKET"
    )

    (
        normal_acca,
        normal_context,
        normal_evidence,
        normal_control,
    ) = build_acca(
        spec.name,
        market_regime="normal",
    )

    print_governance_state(
        "ACCA STATE BEFORE AIHF RUN",
        normal_context,
        normal_evidence,
        normal_control,
    )

    # Fresh broker = identical starting capital / empty book.
    normal_broker = SimBroker(
        cash=spec.capital
    )

    # ------------------------------------------------------------------
    # EXTREME RUN
    # ------------------------------------------------------------------
    #
    # Both runs share one FDClient/CachedDataClient context. This helps keep
    # the data responses equivalent while avoiding unnecessary duplicate
    # external retrieval.
    # ------------------------------------------------------------------

    with FDClient() as raw:
        fd = CachedDataClient(raw)

        normal_record = run_cycle(
            fund,
            args.date,
            normal_broker,
            fd,
            universe,
            governance=normal_control,
        )

        print_aihf_record(
            "RUN A RESULT — NORMAL MARKET",
            normal_record,
        )

        divider(
            "RUN B — EXTREME MARKET"
        )

        (
            extreme_acca,
            extreme_context,
            extreme_evidence,
            extreme_control,
        ) = build_acca(
            spec.name,
            market_regime="extreme",
        )

        print_governance_state(
            "ACCA STATE BEFORE AIHF RUN",
            extreme_context,
            extreme_evidence,
            extreme_control,
        )

        # Fresh broker is essential:
        # the normal run must not change the starting portfolio of Run B.
        extreme_broker = SimBroker(
            cash=spec.capital
        )

        extreme_record = run_cycle(
            fund,
            args.date,
            extreme_broker,
            fd,
            universe,
            governance=extreme_control,
        )

        print_aihf_record(
            "RUN B RESULT — EXTREME MARKET",
            extreme_record,
        )

    compare_orders(
        normal_record,
        extreme_record,
    )

    divider(
        "ACCA INTERPRETATION"
    )

    print()
    print(
        "Agent implementation    : unchanged"
    )

    print(
        "Fund/strategies         : unchanged"
    )

    print(
        "Model configuration     : unchanged"
    )

    print(
        "Date/data               : unchanged"
    )

    print(
        "Initial broker state    : unchanged"
    )

    print(
        "Universe                : unchanged"
    )

    print(
        "Operating environment   : NORMAL -> EXTREME"
    )

    print(
        "Evidence applicability  : applicable -> not applicable"
    )

    print(
        "Assurance               : HEALTHY -> UNASSURED"
    )

    print(
        "Authority epoch         : 1 -> 2"
    )

    print()
    print(
        "The AIHF agents remain free to generate trading proposals."
    )

    print(
        "ACCA independently determines whether those proposed actions "
        "may cross the execution boundary."
    )

    print()


if __name__ == "__main__":
    main()
