"""S1 demo: Default-deny and capability != authority.

This experiment demonstrates three cases:

S1-A:
    An explicitly authorized equity action proceeds past TGP.

S1-B:
    An options action uses a known action name but falls outside the
    declared asset-class scope and is denied.

S1-C:
    A novel consequential action is technically representable but is not
    explicitly included in declared authority. It is denied even though it
    does not appear on a prohibition list.

The experiment demonstrates the TGP invariant:

    a not in A_d  ->  DENY

and the broader governance principle:

    capability != authority
"""

from __future__ import annotations

from dataclasses import dataclass

from .tgp import (
    ActionRequest,
    AuthorizationResult,
    DenialReason,
    GovernanceStage,
    TGPAuthorizer,
    TGPDecision,
    TGPProfile,
)


@dataclass(frozen=True)
class ScenarioResult:
    scenario: str
    description: str
    request: ActionRequest
    decision: TGPDecision
    acca_reached: bool
    broker_reached: bool


def build_s1_profile() -> TGPProfile:
    """Create the principal-declared authority used in S1.

    The principal allows equity-order placement for a small stock universe.

    Notice that:
    - options are not allowed by asset-class scope;
    - the novel action is not listed as allowed;
    - the novel action is also not listed as explicitly prohibited.

    This lets us distinguish explicit prohibition from default-deny behavior.
    """
    return TGPProfile.build(
        "s1-equity-only",
        allowed_actions={
            "analyze_security",
            "generate_recommendation",
            "propose_order",
            "place_order",
            "cancel_order",
        },
        allowed_asset_classes={
            "equity",
        },
        allowed_symbols={
            "NVDA",
            "MSFT",
            "AAPL",
        },
        hard_prohibited_actions={
            "withdraw_cash",
            "change_risk_policy",
            "modify_credentials",
        },
    )


def run_s1() -> list[ScenarioResult]:
    """Execute the three TGP S1 cases.

    This demo isolates the TGP declared-authority boundary.

    For S1-A, ``acca_reached=True`` means that TGP would permit the
    request to proceed to the existing ACCA effective-authority check.

    For S1-B and S1-C, TGP denial terminates the authorization path
    before ACCA or broker execution.
    """
    authorizer = TGPAuthorizer(build_s1_profile())

    scenarios = [
        (
            "S1-A",
            "Explicitly authorized equity order",
            ActionRequest(
                action="place_order",
                stage=GovernanceStage.OPERATIONAL,
                asset_class="equity",
                symbol="NVDA",
            ),
        ),
        (
            "S1-B",
            "Known action outside declared asset-class scope",
            ActionRequest(
                action="place_order",
                stage=GovernanceStage.OPERATIONAL,
                asset_class="option",
                symbol="NVDA",
            ),
        ),
        (
            "S1-C",
            "Novel consequential action absent from declared authority",
            ActionRequest(
                action="trade_structured_derivative",
                stage=GovernanceStage.OPERATIONAL,
                asset_class="structured_derivative",
                symbol="NVDA",
            ),
        ),
    ]

    results: list[ScenarioResult] = []

    for scenario, description, request in scenarios:
        decision = authorizer.authorize(request)

        permitted_by_tgp = decision.result == AuthorizationResult.ALLOW

        # In the full runtime path, a TGP ALLOW means the action is eligible
        # to proceed to ACCA. It does NOT mean the action is automatically
        # broker-executable.
        acca_reached = permitted_by_tgp

        # This isolated S1 demo deliberately does not invoke a Broker.
        # Broker reachability is therefore always False here.
        broker_reached = False

        results.append(
            ScenarioResult(
                scenario=scenario,
                description=description,
                request=request,
                decision=decision,
                acca_reached=acca_reached,
                broker_reached=broker_reached,
            )
        )

    return results


def format_s1_report(results: list[ScenarioResult]) -> str:
    """Render a compact human-readable experiment report."""
    lines = [
        "",
        "TGP S1 — DEFAULT DENY / CAPABILITY != AUTHORITY",
        "=" * 54,
    ]

    for result in results:
        lines.extend(
            [
                "",
                f"{result.scenario}: {result.description}",
                f"  Action:       {result.request.action}",
                f"  Asset class:  {result.request.asset_class}",
                f"  Symbol:       {result.request.symbol}",
                f"  Stage:        {result.request.stage.value}",
                f"  TGP decision: {result.decision.result.value}",
                (
                    f"  Reason:       {result.decision.reason.value}"
                    if result.decision.reason is not None
                    else "  Reason:       explicitly within declared authority"
                ),
                f"  ACCA reached: {'YES' if result.acca_reached else 'NO'}",
                f"  Broker:       {'YES' if result.broker_reached else 'NO'}",
            ]
        )

    lines.extend(
        [
            "",
            "Invariant demonstrated:",
            "  operational action absent from declared authority -> DENY",
            "",
            "Interpretation:",
            "  Capability or technical representability does not create",
            "  operational permission.",
            "",
        ]
    )

    return "\n".join(lines)


def main() -> None:
    results = run_s1()
    print(format_s1_report(results))


if __name__ == "__main__":
    main()
