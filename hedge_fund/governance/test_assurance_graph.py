from hedge_fund.governance.assurance_graph import (
    AssuranceDependencyGraph,
)
from hedge_fund.governance.context import GovernanceContext
from hedge_fund.governance.evidence import AssuranceEvidence


def make_graph():
    evidence = AssuranceEvidence(
        evidence_id="E-17",
        subject="portfolio_manager",
        evidence_type="evaluation",
        supports={"safe_autonomous_trading"},
        assumptions={
            "market_regime": {"normal", "elevated"},
        },
    )

    return AssuranceDependencyGraph([evidence])


def test_claim_supported_under_normal_market():
    context = GovernanceContext(
        values={"market_regime": "normal"}
    )

    graph = make_graph()

    claim = graph.evaluate_claim(
        "safe_autonomous_trading",
        context,
    )

    assert claim.supported is True
    assert claim.supporting_evidence == {"E-17"}


def test_claim_remains_supported_when_market_becomes_elevated():
    context = GovernanceContext(
        values={"market_regime": "normal"}
    )

    graph = make_graph()

    before = graph.evaluate_claim(
        "safe_autonomous_trading",
        context,
    )

    context.set("market_regime", "elevated")

    after = graph.evaluate_claim(
        "safe_autonomous_trading",
        context,
    )

    assert before.supported is True
    assert after.supported is True
    assert after.supporting_evidence == {"E-17"}


def test_claim_loses_support_when_market_becomes_extreme():
    context = GovernanceContext(
        values={"market_regime": "normal"}
    )

    graph = make_graph()

    before = graph.evaluate_claim(
        "safe_autonomous_trading",
        context,
    )

    context.set("market_regime", "extreme")

    after = graph.evaluate_claim(
        "safe_autonomous_trading",
        context,
    )

    assert before.supported is True
    assert after.supported is False
    assert after.supporting_evidence == set()


def test_irrelevant_change_does_not_affect_claim():
    context = GovernanceContext(
        values={
            "market_regime": "normal",
            "dashboard_theme": "dark",
        }
    )

    graph = make_graph()

    before = graph.evaluate_claim(
        "safe_autonomous_trading",
        context,
    )

    context.set("dashboard_theme", "light")

    after = graph.evaluate_claim(
        "safe_autonomous_trading",
        context,
    )

    assert before.supported is True
    assert after.supported is True
