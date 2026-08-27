from hedge_fund.governance.context import GovernanceContext
from hedge_fund.governance.evidence import AssuranceEvidence


def make_trading_evidence():
    return AssuranceEvidence(
        evidence_id="E-17",
        subject="portfolio_manager",
        evidence_type="evaluation",
        supports={"safe_autonomous_trading"},
        assumptions={
            "market_regime": {"normal", "elevated"},
        },
    )


def test_evidence_applicable_under_normal_market():
    context = GovernanceContext(
        values={"market_regime": "normal"}
    )

    evidence = make_trading_evidence()

    assert evidence.is_applicable(context) is True


def test_market_crash_makes_evidence_inapplicable():
    context = GovernanceContext(
        values={"market_regime": "normal"}
    )

    evidence = make_trading_evidence()

    assert evidence.is_applicable(context) is True

    context.set("market_regime", "extreme")

    assert evidence.is_applicable(context) is False

    assert evidence.failed_assumptions(context) == {
        "market_regime": "extreme"
    }


def test_irrelevant_context_change_does_not_affect_evidence():
    context = GovernanceContext(
        values={
            "market_regime": "normal",
            "dashboard_theme": "dark",
        }
    )

    evidence = make_trading_evidence()

    assert evidence.is_applicable(context) is True

    context.set("dashboard_theme", "light")

    assert evidence.is_applicable(context) is True
