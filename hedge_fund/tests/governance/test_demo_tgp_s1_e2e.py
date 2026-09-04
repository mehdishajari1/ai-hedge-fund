from governance.demo_tgp_s1_e2e import run_s1_e2e
from governance.tgp import AuthorizationResult, DenialReason


def _results():
    return {r.scenario: r for r in run_s1_e2e()}


def test_s1_a_traverses_complete_governance_path():
    result = _results()["S1-A"]

    assert result.tgp_decision.result == AuthorizationResult.ALLOW

    assert result.tgp_calls == 1
    assert result.acca_calls == 1
    assert result.epoch_checks == 1
    assert result.broker_calls == 1

    assert result.fill is not None
    assert result.fill.ticker == "NVDA"
    assert result.fill.quantity == 10
    assert result.fill.price == 100.0


def test_s1_b_stops_at_tgp_scope_boundary():
    result = _results()["S1-B"]

    assert result.tgp_decision.result == AuthorizationResult.DENY
    assert result.tgp_decision.reason == DenialReason.OUTSIDE_SCOPE

    assert result.tgp_calls == 1
    assert result.acca_calls == 0
    assert result.epoch_checks == 0
    assert result.broker_calls == 0
    assert result.fill is None


def test_s1_c_stops_at_closed_world_boundary():
    result = _results()["S1-C"]

    assert result.tgp_decision.result == AuthorizationResult.DENY
    assert (
        result.tgp_decision.reason
        == DenialReason.NOT_EXPLICITLY_AUTHORIZED
    )

    assert result.tgp_calls == 1
    assert result.acca_calls == 0
    assert result.epoch_checks == 0
    assert result.broker_calls == 0
    assert result.fill is None


def test_tgp_denial_never_reaches_downstream_authority():
    results = _results()

    for scenario in ("S1-B", "S1-C"):
        result = results[scenario]

        assert result.acca_calls == 0
        assert result.epoch_checks == 0
        assert result.broker_calls == 0


def test_only_declared_and_effectively_authorized_action_reaches_broker():
    results = _results()

    assert results["S1-A"].broker_calls == 1
    assert results["S1-B"].broker_calls == 0
    assert results["S1-C"].broker_calls == 0

    assert sum(r.broker_calls for r in results.values()) == 1