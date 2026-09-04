from governance.demo_tgp_s1 import build_s1_profile, run_s1

from governance.tgp import AuthorizationResult, DenialReason


def result_by_scenario():
    return {result.scenario: result for result in run_s1()}


def test_s1_profile_is_operationally_default_deny():
    profile = build_s1_profile()

    assert "place_order" in profile.allowed_actions

    # The novel action is deliberately not explicitly allowed.
    assert "trade_structured_derivative" not in profile.allowed_actions

    # It is also deliberately NOT explicitly prohibited.
    #
    # Therefore S1-C demonstrates default deny rather than merely
    # matching a prohibition list.
    assert "trade_structured_derivative" not in profile.hard_prohibited_actions


def test_s1_a_authorized_equity_proceeds_to_acca():
    result = result_by_scenario()["S1-A"]

    assert result.decision.result == AuthorizationResult.ALLOW
    assert result.decision.reason is None

    # TGP is only the declared-authority boundary.
    # ALLOW means the action may proceed to ACCA, not directly to Broker.
    assert result.acca_reached is True
    assert result.broker_reached is False


def test_s1_b_option_order_is_denied_as_outside_scope():
    result = result_by_scenario()["S1-B"]

    assert result.decision.result == AuthorizationResult.DENY
    assert result.decision.reason == DenialReason.OUTSIDE_SCOPE

    # TGP denial terminates the authorization path before ACCA.
    assert result.acca_reached is False
    assert result.broker_reached is False


def test_s1_c_novel_action_is_denied_by_default():
    result = result_by_scenario()["S1-C"]

    assert result.decision.result == AuthorizationResult.DENY
    assert (
        result.decision.reason
        == DenialReason.NOT_EXPLICITLY_AUTHORIZED
    )

    assert result.acca_reached is False
    assert result.broker_reached is False


def test_s1_c_is_default_deny_not_explicit_prohibition():
    profile = build_s1_profile()
    result = result_by_scenario()["S1-C"]

    assert result.request.action not in profile.allowed_actions
    assert result.request.action not in profile.hard_prohibited_actions

    assert result.decision.result == AuthorizationResult.DENY
    assert (
        result.decision.reason
        == DenialReason.NOT_EXPLICITLY_AUTHORIZED
    )
