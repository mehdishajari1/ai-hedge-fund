"""Stakeholder-specific risk policy for ACCA authority derivation."""

from dataclasses import dataclass
from copy import deepcopy

from hedge_fund.governance.models import (
    AssuranceClaim,
    AssuranceState,
    AuthorityVector,
)


@dataclass
class StakeholderRiskPolicy:
    """Derive effective authority from assurance under stakeholder risk tolerance."""

    policy_id: str

    # Maximum order value permitted when required assurance is unavailable.
    unassured_max_order_value: float | None = None

    # Whether live execution survives loss of required assurance.
    allow_live_when_unassured: bool = False

    # Whether human approval is required when assurance is unavailable.
    require_human_gate_when_unassured: bool = True

    def derive_authority(
        self,
        baseline: AuthorityVector,
        claims: dict[str, AssuranceClaim],
    ) -> AuthorityVector:
        """Derive an effective authority envelope."""

        effective = deepcopy(baseline)

        unhealthy = any(
            claims[claim_id].state
            in {
                AssuranceState.DEGRADED,
                AssuranceState.UNASSURED,
                AssuranceState.INCIDENT,
            }
            for claim_id in effective.required_claims
        )

        if not unhealthy:
            return effective

        if not self.allow_live_when_unassured:
            effective.allowed_actions.discard("live_order")
            effective.prohibited_actions.add("live_order")

        if self.unassured_max_order_value is not None:
            if (
                effective.max_order_value is None
                or effective.max_order_value
                > self.unassured_max_order_value
            ):
                effective.max_order_value = (
                    self.unassured_max_order_value
                )

        if self.require_human_gate_when_unassured:
            effective.aal = min(effective.aal, 1)

        return effective
