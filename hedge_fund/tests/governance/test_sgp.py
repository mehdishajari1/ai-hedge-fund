from governance.sgp import (
    SOCAction,
    SOCEnvironment,
    SOCRequest,
    SGPAuthorizer,
    SGPDecision,
    SGPDenialReason,
    example_sgp_profile,
)


def make_authorizer() -> SGPAuthorizer:
    return SGPAuthorizer(
        example_sgp_profile()
    )


def test_sgp_investigative_action_is_allowed():
    authorizer = make_authorizer()

    result = authorizer.authorize(
        SOCRequest(
            actor_id="soc_agent",
            action=SOCAction.QUERY_ENDPOINT.value,
            resource_id="WORKSTATION-17",
            resource_type="endpoint",
            environment=SOCEnvironment.PRODUCTION,
        )
    )

    assert result.decision == SGPDecision.ALLOW
    assert result.reason is None


def test_sgp_bounded_containment_is_allowed():
    authorizer = make_authorizer()

    result = authorizer.authorize(
        SOCRequest(
            actor_id="soc_agent",
            action=SOCAction.ISOLATE_ENDPOINT.value,
            resource_id="WORKSTATION-17",
            resource_type="endpoint",
            environment=SOCEnvironment.PRODUCTION,
        )
    )

    assert result.decision == SGPDecision.ALLOW
    assert result.reason is None


def test_sgp_higher_impact_action_requires_human_gate():
    authorizer = make_authorizer()

    result = authorizer.authorize(
        SOCRequest(
            actor_id="soc_agent",
            action=SOCAction.DISABLE_ACCOUNT.value,
            resource_id="USER-4421",
            resource_type="identity",
            environment=SOCEnvironment.PRODUCTION,
        )
    )

    assert result.decision == SGPDecision.HUMAN_GATE
    assert result.reason == SGPDenialReason.HUMAN_APPROVAL_REQUIRED


def test_sgp_explicitly_prohibited_action_is_denied():
    authorizer = make_authorizer()

    result = authorizer.authorize(
        SOCRequest(
            actor_id="soc_agent",
            action=SOCAction.MODIFY_FIREWALL_RULE.value,
            resource_id="FIREWALL-PROD-01",
            resource_type="network_control",
            environment=SOCEnvironment.PRODUCTION,
        )
    )

    assert result.decision == SGPDecision.DENY
    assert result.reason == SGPDenialReason.NOT_EXPLICITLY_AUTHORIZED


def test_sgp_unknown_consequential_action_is_denied_by_default():
    authorizer = make_authorizer()

    result = authorizer.authorize(
        SOCRequest(
            actor_id="soc_agent",
            action="rotate_domain_admin_credentials",
            resource_id="DOMAIN-01",
            resource_type="identity",
            environment=SOCEnvironment.PRODUCTION,
        )
    )

    assert result.decision == SGPDecision.DENY
    assert result.reason == SGPDenialReason.NOT_EXPLICITLY_AUTHORIZED


def test_sgp_known_action_against_out_of_scope_resource_type_is_denied():
    authorizer = make_authorizer()

    result = authorizer.authorize(
        SOCRequest(
            actor_id="soc_agent",
            action=SOCAction.QUERY_ENDPOINT.value,
            resource_id="PROD-DATABASE-01",
            resource_type="database",
            environment=SOCEnvironment.PRODUCTION,
        )
    )

    assert result.decision == SGPDecision.DENY
    assert result.reason == SGPDenialReason.RESOURCE_OUT_OF_SCOPE


def test_sgp_actor_mismatch_is_denied():
    authorizer = make_authorizer()

    result = authorizer.authorize(
        SOCRequest(
            actor_id="different_agent",
            action=SOCAction.QUERY_ENDPOINT.value,
            resource_id="WORKSTATION-17",
            resource_type="endpoint",
            environment=SOCEnvironment.PRODUCTION,
        )
    )

    assert result.decision == SGPDecision.DENY
    assert result.reason == SGPDenialReason.NOT_EXPLICITLY_AUTHORIZED


def test_sgp_human_gate_action_is_inside_declared_authority():
    profile = example_sgp_profile()

    action = SOCAction.DISABLE_ACCOUNT.value

    assert action in profile.allowed_actions
    assert action in profile.human_gate_actions
    assert action not in profile.prohibited_actions


def test_sgp_prohibited_actions_are_not_autonomously_authorized():
    profile = example_sgp_profile()

    for action in profile.prohibited_actions:
        assert action not in profile.human_gate_actions


def test_sgp_default_deny_prevents_capability_self_promotion():
    authorizer = make_authorizer()

    technically_possible_but_undeclared_action = (
        "rotate_domain_admin_credentials"
    )

    result = authorizer.authorize(
        SOCRequest(
            actor_id="soc_agent",
            action=technically_possible_but_undeclared_action,
            resource_id="DOMAIN-01",
            resource_type="identity",
            environment=SOCEnvironment.PRODUCTION,
        )
    )

    assert result.decision == SGPDecision.DENY
    assert (
        result.reason
        == SGPDenialReason.NOT_EXPLICITLY_AUTHORIZED
    )
