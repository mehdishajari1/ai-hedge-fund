from hedge_fund.governance.evidence import AssuranceEvidence
from hedge_fund.governance.materiality import MaterialityEvaluator


def make_evidence():
    return AssuranceEvidence(
        evidence_id="E-17",
        subject="portfolio_manager",
        evidence_type="evaluation",
        supports={"safe_autonomous_trading"},
        assumptions={
            "market_regime": {"normal", "elevated"},
        },
    )


def test_market_regime_change_is_material():
    evaluator = MaterialityEvaluator([make_evidence()])

    change = evaluator.evaluate(
        dependency="market_regime",
        old_value="normal",
        new_value="extreme",
    )

    assert change.material is True
    assert change.affected_evidence == {"E-17"}
    assert change.affected_claims == {
        "safe_autonomous_trading"
    }


def test_dashboard_theme_change_is_not_material():
    evaluator = MaterialityEvaluator([make_evidence()])

    change = evaluator.evaluate(
        dependency="dashboard_theme",
        old_value="dark",
        new_value="light",
    )

    assert change.material is False
    assert change.affected_evidence == set()
    assert change.affected_claims == set()
