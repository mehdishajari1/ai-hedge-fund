"""S1 end-to-end experiment.

Demonstrates the composed authorization path:

    request
      -> TGP declared-authority boundary
      -> ACCA effective-authority decision
      -> authority epoch check
      -> SimBroker consequence boundary

S1-A traverses the complete path.

S1-B and S1-C are intentionally stopped at TGP before an AIHF Order
is constructed or downstream ACCA/broker processing occurs.
"""

from __future__ import annotations

from dataclasses import dataclass

from hedge_fund.brokers.models import Fill, Order
from hedge_fund.brokers.sim import SimBroker

from .control import GovernanceControlPlane
from .demo_tgp_s1 import build_s1_profile
from .gateway import GovernedExecutionGateway
from .tgp import (
    ActionRequest,
    AuthorizationResult,
    GovernanceStage,
    TGPAuthorizer,
    TGPDecision,
)


class CountingGovernanceControlPlane(GovernanceControlPlane):
    """Governance control plane instrumented for experimental tracing."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.decision_calls = 0
        self.epoch_check_calls = 0

    def decide_order(self, order: Order, *, live: bool = False):
        self.decision_calls += 1
        return super().decide_order(order, live=live)

    def assert_epoch(self, expected_epoch: int) -> None:
        self.epoch_check_calls += 1
        return super().assert_epoch(expected_epoch)


class CountingSimBroker(SimBroker):
    """SimBroker instrumented to count consequential executions."""

    def __init__(self, cash: float):
        super().__init__(cash)
        self.place_order_calls = 0

    def place_order(self, order: Order) -> Fill:
        self.place_order_calls += 1
        return super().place_order(order)


class CountingTGPAuthorizer(TGPAuthorizer):
    """TGP authorizer instrumented for experimental tracing."""

    def __init__(self, profile):
        super().__init__(profile)
        self.authorization_calls = 0

    def authorize(self, request: ActionRequest, *, capability=None):
        self.authorization_calls += 1
        return super().authorize(request, capability=capability)


@dataclass(frozen=True)
class E2EScenarioResult:
    scenario: str
    description: str
    request: ActionRequest
    tgp_decision: TGPDecision
    tgp_calls: int
    acca_calls: int
    epoch_checks: int
    broker_calls: int
    fill: Fill | None


def _build_acca() -> CountingGovernanceControlPlane:
    """Build healthy ACCA authority for the authorized S1 path."""

    base = GovernanceControlPlane.paper_trading_default(
        "s1-e2e",
        max_order_value=10_000.0,
    )

    return CountingGovernanceControlPlane(
        base.authority,
        list(base.claims.values()),
        policy=base.policy,
    )


def _run_authorized_equity() -> E2EScenarioResult:
    """S1-A: execute the complete TGP -> ACCA -> epoch -> broker path."""

    request = ActionRequest(
        action="place_order",
        stage=GovernanceStage.OPERATIONAL,
        asset_class="equity",
        symbol="NVDA",
    )

    tgp = CountingTGPAuthorizer(build_s1_profile())
    governance = _build_acca()
    broker = CountingSimBroker(cash=100_000.0)

    gateway = GovernedExecutionGateway(
        broker,
        governance,
        live=False,
        tgp=tgp,
        stage=GovernanceStage.OPERATIONAL,
    )

    order = Order(
        ticker="NVDA",
        side="buy",
        quantity=10,
        price=100.0,
    )

    fill = gateway.place_order(order)

    # The gateway owns the actual TGP decision for S1-A.
    decision = gateway.tgp_decisions[-1]

    return E2EScenarioResult(
        scenario="S1-A",
        description="Explicitly authorized equity order",
        request=request,
        tgp_decision=decision,
        tgp_calls=tgp.authorization_calls,
        acca_calls=governance.decision_calls,
        epoch_checks=governance.epoch_check_calls,
        broker_calls=broker.place_order_calls,
        fill=fill,
    )


def _run_tgp_denied(
    *,
    scenario: str,
    description: str,
    request: ActionRequest,
) -> E2EScenarioResult:
    """Run a request that must terminate at the TGP boundary.

    No AIHF Order is constructed because the principal has not granted
    authority for the requested consequential action/scope.
    """

    tgp = CountingTGPAuthorizer(build_s1_profile())
    governance = _build_acca()
    broker = CountingSimBroker(cash=100_000.0)

    decision = tgp.authorize(request)

    fill = None

    if decision.result == AuthorizationResult.ALLOW:
        raise AssertionError(
            f"{scenario} unexpectedly passed the TGP boundary"
        )

    return E2EScenarioResult(
        scenario=scenario,
        description=description,
        request=request,
        tgp_decision=decision,
        tgp_calls=tgp.authorization_calls,
        acca_calls=governance.decision_calls,
        epoch_checks=governance.epoch_check_calls,
        broker_calls=broker.place_order_calls,
        fill=fill,
    )


def run_s1_e2e() -> list[E2EScenarioResult]:
    """Execute all three S1 end-to-end authorization cases."""

    return [
        _run_authorized_equity(),
        _run_tgp_denied(
            scenario="S1-B",
            description="Known action outside declared asset-class scope",
            request=ActionRequest(
                action="place_order",
                stage=GovernanceStage.OPERATIONAL,
                asset_class="option",
                symbol="NVDA",
            ),
        ),
        _run_tgp_denied(
            scenario="S1-C",
            description="Novel consequential action absent from declared authority",
            request=ActionRequest(
                action="trade_structured_derivative",
                stage=GovernanceStage.OPERATIONAL,
                asset_class="structured_derivative",
                symbol="NVDA",
            ),
        ),
    ]


def format_s1_e2e_report(results: list[E2EScenarioResult]) -> str:
    lines = [
        "",
        "S1 END-TO-END - DEFAULT DENY / CAPABILITY != AUTHORITY",
        "=" * 62,
    ]

    for result in results:
        lines.extend(
            [
                "",
                f"{result.scenario}: {result.description}",
                f"  Action:             {result.request.action}",
                f"  Asset class:        {result.request.asset_class}",
                f"  Symbol:             {result.request.symbol}",
                f"  TGP decision:       {result.tgp_decision.result.value}",
                (
                    f"  TGP reason:         {result.tgp_decision.reason.value}"
                    if result.tgp_decision.reason is not None
                    else "  TGP reason:         explicitly within declared authority"
                ),
                f"  TGP calls:           {result.tgp_calls}",
                f"  ACCA calls:          {result.acca_calls}",
                f"  Epoch checks:        {result.epoch_checks}",
                f"  Broker calls:        {result.broker_calls}",
                f"  Fill produced:       {'YES' if result.fill is not None else 'NO'}",
            ]
        )

    lines.extend(
        [
            "",
            "Composition demonstrated:",
            "  TGP ALLOW -> eligible for ACCA -> epoch check -> broker",
            "  TGP DENY  -> ACCA not invoked -> broker not invoked",
            "",
            "Governance properties:",
            "  capability != declared authority",
            "  effective authority is contained within declared authority",
            "  A_eff(t) subset-of A_d",
            "",
        ]
    )

    return "\n".join(lines)


def main() -> None:
    results = run_s1_e2e()
    print(format_s1_e2e_report(results))


if __name__ == "__main__":
    main()
