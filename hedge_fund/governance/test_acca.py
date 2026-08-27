from hedge_fund.governance.acca import ACCAEngine
from hedge_fund.governance.assurance_graph import AssuranceDependencyGraph
from hedge_fund.governance.context import GovernanceContext
from hedge_fund.governance.control import GovernanceControlPlane
from hedge_fund.governance.evidence import AssuranceEvidence
from hedge_fund.governance.materiality import MaterialityEvaluator
from hedge_fund.governance.models import AssuranceState
from hedge_fund.governance.policy import StakeholderRiskPolicy

def make_acca():

    context = GovernanceContext(
        values={
            "market_regime": "normal",
            "dashboard_theme": "dark",
        }
    )

    evidence = AssuranceEvidence(
        evidence_id="E-17",
        subject="portfolio_manager",
        evidence_type="evaluation",
        supports={
            "SAFE_AUTONOMOUS_TRADING",
        },
        assumptions={
            "market_regime": {
                "normal",
                "elevated",
            },
        },
    )

    graph = AssuranceDependencyGraph([evidence])

    materiality = MaterialityEvaluator([evidence])

    control = GovernanceControlPlane.acca_trading_demo(
        "example-fund",
        max_order_value=10_000.0,
    )

    return (
        ACCAEngine(
            context=context,
            assurance_graph=graph,
            materiality=materiality,
            control_plane=control,
        ),
        control,
    )


def test_irrelevant_change_does_not_change_authority_epoch():

    acca, control = make_acca()

    epoch_before = control.authority.epoch

    result = acca.observe_context(
        "dashboard_theme",
        "light",
    )

    assert result.dependency_relevant is False
    assert result.assurance_changed is False

    assert control.authority.epoch == epoch_before

    assert (
        control.claims[
            "SAFE_AUTONOMOUS_TRADING"
        ].state
        == AssuranceState.HEALTHY
    )


def test_elevated_market_touches_dependency_but_preserves_assurance():

    acca, control = make_acca()

    epoch_before = control.authority.epoch

    result = acca.observe_context(
        "market_regime",
        "elevated",
    )

    assert result.dependency_relevant is True
    assert result.assurance_changed is False

    assert control.authority.epoch == epoch_before

    assert (
        control.claims[
            "SAFE_AUTONOMOUS_TRADING"
        ].state
        == AssuranceState.HEALTHY
    )

    assert "live_order" in control.authority.allowed_actions


def test_extreme_market_invalidates_assurance_and_contracts_authority():

    acca, control = make_acca()

    epoch_before = control.authority.epoch

    assert "live_order" in control.authority.allowed_actions

    result = acca.observe_context(
        "market_regime",
        "extreme",
    )

    assert result.dependency_relevant is True
    assert result.assurance_changed is True

    assert (
        control.claims[
            "SAFE_AUTONOMOUS_TRADING"
        ].state
        == AssuranceState.UNASSURED
    )

    assert control.authority.epoch > epoch_before

    # Current generic control-plane behavior removes
    # consequential ordering authority when a required
    # assurance claim becomes unhealthy.
    assert "paper_order" not in control.authority.allowed_actions


def make_acca_with_policy(policy):

    context = GovernanceContext(
        values={"market_regime": "normal"}
    )

    evidence = AssuranceEvidence(
        evidence_id="E-17",
        subject="portfolio_manager",
        evidence_type="evaluation",
        supports={"SAFE_AUTONOMOUS_TRADING"},
        assumptions={
            "market_regime": {"normal", "elevated"},
        },
    )

    graph = AssuranceDependencyGraph([evidence])

    control = GovernanceControlPlane.acca_trading_demo(
        policy.policy_id,
        max_order_value=10_000.0,
        policy=policy,
    )

    return ACCAEngine(
        context=context,
        assurance_graph=graph,
        materiality=MaterialityEvaluator([evidence]),
        control_plane=control,
    ), control


def test_same_assurance_different_risk_policy_produces_different_authority():

    conservative = StakeholderRiskPolicy(
        policy_id="conservative",
        unassured_max_order_value=1_000.0,
        allow_live_when_unassured=False,
        require_human_gate_when_unassured=True,
    )

    tolerant = StakeholderRiskPolicy(
        policy_id="tolerant",
        unassured_max_order_value=1_000.0,
        allow_live_when_unassured=True,
        require_human_gate_when_unassured=True,
    )

    acca_c, control_c = make_acca_with_policy(
        conservative
    )

    acca_t, control_t = make_acca_with_policy(
        tolerant
    )

    # Both stakeholders observe exactly the same environmental event.
    acca_c.observe_context(
        "market_regime",
        "extreme",
    )

    acca_t.observe_context(
        "market_regime",
        "extreme",
    )

    # Both have exactly the same assurance outcome.
    assert (
        control_c.claims[
            "SAFE_AUTONOMOUS_TRADING"
        ].state
        == AssuranceState.UNASSURED
    )

    assert (
        control_t.claims[
            "SAFE_AUTONOMOUS_TRADING"
        ].state
        == AssuranceState.UNASSURED
    )

    # But stakeholder policy derives different authority.
    assert (
        "live_order"
        not in control_c.authority.allowed_actions
    )

    assert (
        "live_order"
        in control_t.authority.allowed_actions
    )

    assert (
        control_c.authority.max_order_value
        == 1_000.0
    )

    assert (
        control_t.authority.max_order_value
        == 1_000.0
    )

    # Both require stronger human involvement.
    assert control_c.authority.aal == 1
    assert control_t.authority.aal == 1