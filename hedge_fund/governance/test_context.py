from hedge_fund.governance.context import GovernanceContext


def test_market_regime_change():
    context = GovernanceContext(
        values={
            "market_regime": "normal",
            "dashboard_theme": "dark",
        }
    )

    assert context.get("market_regime") == "normal"

    old_value, new_value = context.set(
        "market_regime",
        "extreme",
    )

    assert old_value == "normal"
    assert new_value == "extreme"
    assert context.get("market_regime") == "extreme"


def test_context_snapshot():
    context = GovernanceContext(
        values={
            "market_regime": "normal",
        }
    )

    snapshot = context.snapshot()

    assert snapshot == {
        "market_regime": "normal",
    }
