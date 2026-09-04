"""
SGP v0.1 demonstration.

Shows that the Security Operations Governance Profile:
    - explicitly allows low-risk investigative activity
    - allows bounded containment
    - human-gates higher-impact remediation
    - denies undeclared consequential actions
    - enforces resource scope
"""

from governance.sgp import (
    SOCAction,
    SOCEnvironment,
    SOCRequest,
    SGPAuthorizer,
    example_sgp_profile,
)


def _run(label: str, authorizer: SGPAuthorizer, request: SOCRequest) -> None:
    result = authorizer.authorize(request)

    print()
    print(label)
    print("-" * len(label))

    print(f"Action:          {request.action}")
    print(f"Resource:        {request.resource_id}")
    print(f"Resource type:   {request.resource_type}")
    print(f"Environment:     {request.environment.value}")
    print(f"Decision:        {result.decision.value}")

    if result.reason is not None:
        print(f"Reason:          {result.reason.value}")


def main() -> None:
    profile = example_sgp_profile()
    authorizer = SGPAuthorizer(profile)

    print()
    print("=" * 72)
    print("SECURITY OPERATIONS GOVERNANCE PROFILE — SGP v0.1")
    print("=" * 72)

    _run(
        "S1 — INVESTIGATIVE ACTION",
        authorizer,
        SOCRequest(
            actor_id="soc_agent",
            action=SOCAction.QUERY_ENDPOINT.value,
            resource_id="WORKSTATION-17",
            resource_type="endpoint",
            environment=SOCEnvironment.PRODUCTION,
        ),
    )

    _run(
        "S2 — BOUNDED CONTAINMENT",
        authorizer,
        SOCRequest(
            actor_id="soc_agent",
            action=SOCAction.ISOLATE_ENDPOINT.value,
            resource_id="WORKSTATION-17",
            resource_type="endpoint",
            environment=SOCEnvironment.PRODUCTION,
        ),
    )

    _run(
        "S3 — HIGHER-IMPACT HUMAN GATE",
        authorizer,
        SOCRequest(
            actor_id="soc_agent",
            action=SOCAction.DISABLE_ACCOUNT.value,
            resource_id="USER-4421",
            resource_type="identity",
            environment=SOCEnvironment.PRODUCTION,
        ),
    )

    _run(
        "S4 — PROHIBITED CONSEQUENTIAL ACTION",
        authorizer,
        SOCRequest(
            actor_id="soc_agent",
            action=SOCAction.MODIFY_FIREWALL_RULE.value,
            resource_id="FIREWALL-PROD-01",
            resource_type="network_control",
            environment=SOCEnvironment.PRODUCTION,
        ),
    )

    _run(
        "S5 — NOVEL / UNDECLARED ACTION",
        authorizer,
        SOCRequest(
            actor_id="soc_agent",
            action="rotate_domain_admin_credentials",
            resource_id="DOMAIN-01",
            resource_type="identity",
            environment=SOCEnvironment.PRODUCTION,
        ),
    )

    _run(
        "S6 — OUT-OF-SCOPE RESOURCE TYPE",
        authorizer,
        SOCRequest(
            actor_id="soc_agent",
            action=SOCAction.QUERY_ENDPOINT.value,
            resource_id="PROD-DATABASE-01",
            resource_type="database",
            environment=SOCEnvironment.PRODUCTION,
        ),
    )

    print()
    print("=" * 72)
    print("INTERPRETATION")
    print("=" * 72)

    print(
        "SGP separates technical capability from declared operational authority."
    )

    print(
        "Actions absent from declared authority are denied by default, even if "
        "the underlying agent is technically capable of performing them."
    )

    print(
        "Higher-impact actions can remain within declared authority while "
        "requiring explicit human approval."
    )


if __name__ == "__main__":
    main()