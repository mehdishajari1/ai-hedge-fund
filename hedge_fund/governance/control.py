"""Assurance-conditioned authority and material-change reauthorization."""
from __future__ import annotations
from copy import deepcopy
from hedge_fund.brokers.models import Order
from .models import AssuranceClaim, AssuranceState, AuthorityVector, Decision, GovernanceDecision, MaterialChange
from .policy import StakeholderRiskPolicy

class GovernanceControlPlane:
    """External authority owner. Agents/models never mutate this object themselves."""
    def __init__(
        self,
        authority: AuthorityVector,
        claims: list[AssuranceClaim],
        policy: StakeholderRiskPolicy | None = None,
    ):
        self._baseline = deepcopy(authority)
        self.authority = deepcopy(authority)
        self.claims = {c.claim_id: c for c in claims}
        self.policy = policy
        # Last observed values for material dependencies. The first observation
        # establishes a baseline; a subsequent value change creates a
        # MaterialChange and can immediately contract authority.
        self.dependency_values: dict[str, str] = {}
        self.material_changes: list[MaterialChange] = []

    @classmethod
    def paper_trading_default(cls, fund_name: str, *, max_order_value: float | None = None):
        claims = [
            AssuranceClaim(claim_id="MODEL_ASSURANCE", dependencies={"model", "prompt", "model_config"}),
            AssuranceClaim(claim_id="DATA_ASSURANCE", dependencies={"market_data", "fundamentals"}),
            AssuranceClaim(claim_id="RISK_CONTROL_HEALTH", dependencies={"risk_config", "risk_engine"}),
            AssuranceClaim(claim_id="BROKER_HEALTH", dependencies={"broker", "broker_config"}),
            AssuranceClaim(claim_id="MONITORING_HEALTH", dependencies={"telemetry", "monitoring"}),
        ]
        authority = AuthorityVector(
            actor_id=f"fund:{fund_name}", acl=4, aal=2,
            allowed_actions={"paper_order"}, prohibited_actions={"live_order"},
            max_order_value=max_order_value,
            required_claims={c.claim_id for c in claims},
        )
        return cls(authority, claims)

    @classmethod
    def acca_trading_demo(
        cls,
        fund_name: str,
        *,
        max_order_value: float = 10_000.0,
        policy: StakeholderRiskPolicy | None = None,
    ):
        claims = [
            AssuranceClaim(
                claim_id="SAFE_AUTONOMOUS_TRADING",
                dependencies=set(),
            ),
        ]

        authority = AuthorityVector(
            actor_id=f"fund:{fund_name}",
            acl=4,
            aal=3,
            allowed_actions={
                "paper_order",
                "live_order",
            },
            prohibited_actions=set(),
            max_order_value=max_order_value,
            required_claims={
                "SAFE_AUTONOMOUS_TRADING",
            },
        )

        return cls(
            authority,
            claims,
            policy=policy,
        )

    def apply_material_change(self, change: MaterialChange) -> set[str]:
        self.material_changes.append(change)
        affected = set()
        for claim in self.claims.values():
            if change.dependency in claim.dependencies:
                claim.state = AssuranceState.UNASSURED
                claim.reason = change.description
                affected.add(claim.claim_id)
        if affected:
            self.recalculate_authority()
        return affected


    def observe_dependency(
        self, dependency: str, value: str, *, change_type: str, description: str | None = None,
    ) -> MaterialChange | None:
        """Observe a dependency and automatically trigger governance on change.

        First observation establishes the approved/current baseline. A later
        change is treated as material if any assurance claim depends on that
        dependency. The change takes effect immediately by bumping authority
        epoch through ``apply_material_change``.
        """
        previous = self.dependency_values.get(dependency)
        self.dependency_values[dependency] = value
        if previous is None or previous == value:
            return None
        change = MaterialChange(
            change_type=change_type,
            dependency=dependency,
            description=description or f"{dependency} changed from {previous} to {value}",
            previous_value=previous,
            new_value=value,
        )
        self.apply_material_change(change)
        return change

    def observe_model(self, model_id: str) -> MaterialChange | None:
        """Record the active reasoning model; substitution invalidates model assurance."""
        return self.observe_dependency(
            "model", model_id, change_type="model_substitution",
            description=None,
        )

    def reauthorize_model(self, reason: str = "model evaluation and governance review passed") -> None:
        """Explicitly restore model assurance after a model substitution.

        This does not run an evaluation itself; callers should invoke it only
        after the required evidence has actually been produced and accepted.
        """
        self.set_claim_healthy("MODEL_ASSURANCE", reason)

    def clone_for_actor(self, actor_id: str) -> "GovernanceControlPlane":
        """Copy current assurance/authority state for a concrete fund actor."""
        clone = deepcopy(self)
        clone._baseline.actor_id = actor_id
        clone.authority.actor_id = actor_id
        return clone

    def set_claim_healthy(self, claim_id: str, reason: str = "") -> None:
        self.set_claim_state(
            claim_id,
            AssuranceState.HEALTHY,
            reason,
        )

    def set_claim_state(
        self,
        claim_id: str,
        state: AssuranceState,
        reason: str = "",
    ) -> None:
        """Update an assurance claim from evaluated evidence and recalculate authority.

        ACCA evidence/context evaluation should use this method rather than
        directly mutating claims. The control plane remains the owner of
        effective authority.
        """
        claim = self.claims[claim_id]

        if claim.state == state and claim.reason == reason:
            return

        claim.state = state
        claim.reason = reason
        self.recalculate_authority()


    def recalculate_authority(self) -> AuthorityVector:
        """Derive current effective authority from assurance and stakeholder policy."""

        old_epoch = self.authority.epoch

        if self.policy is not None:
            effective = self.policy.derive_authority(
                self._baseline,
                self.claims,
            )
        else:
            # Preserve Increment 1/2 behavior.
            effective = deepcopy(self._baseline)

            if any(
                self.claims[c].state
                in {
                    AssuranceState.DEGRADED,
                    AssuranceState.UNASSURED,
                    AssuranceState.INCIDENT,
                }
                for c in effective.required_claims
            ):
                effective.allowed_actions.discard("paper_order")

        effective.epoch = old_epoch + 1

        self.authority = effective

        return self.authority

    def decide_order(
        self,
        order: Order,
        *,
        live: bool = False,
    ) -> GovernanceDecision:
        """Evaluate a proposed order against current effective authority."""

        action = "live_order" if live else "paper_order"
        a = self.authority

        # 1. Effective authority controls whether the action exists at all.
        if (
            action in a.prohibited_actions
            or action not in a.allowed_actions
        ):
            return GovernanceDecision(
                action=action,
                ticker=order.ticker,
                decision=Decision.DENY,
                reason_code="AUTH_ACTION_DENIED",
                authority_epoch=a.epoch,
                explanation=(
                    "Action is outside current effective authority"
                ),
            )

        # 2. Legacy Increment 1/2 behavior:
        # when no stakeholder policy exists, unhealthy required claims
        # directly deny execution.
        if self.policy is None:
            unhealthy = [
                c
                for c in a.required_claims
                if self.claims[c].state
                != AssuranceState.HEALTHY
            ]

            if unhealthy:
                return GovernanceDecision(
                    action=action,
                    ticker=order.ticker,
                    decision=Decision.DENY,
                    reason_code="ASSURANCE_UNAVAILABLE",
                    authority_epoch=a.epoch,
                    explanation=(
                        "Required assurance not healthy: "
                        f"{sorted(unhealthy)}"
                    ),
                )

        # 3. Machine-enforced value limit.
        value = abs(order.quantity * order.price)

        if (
            a.max_order_value is not None
            and value > a.max_order_value
        ):
            return GovernanceDecision(
                action=action,
                ticker=order.ticker,
                decision=Decision.DENY,
                reason_code="AUTH_LIMIT_EXCEEDED",
                authority_epoch=a.epoch,
                explanation=(
                    f"Order value {value:.2f} exceeds "
                    f"{a.max_order_value:.2f}"
                ),
            )

        # 4. Resource restriction.
        if (
            a.allowed_tickers
            and order.ticker not in a.allowed_tickers
        ):
            return GovernanceDecision(
                action=action,
                ticker=order.ticker,
                decision=Decision.DENY,
                reason_code="AUTH_RESOURCE_DENIED",
                authority_epoch=a.epoch,
                explanation="Ticker is outside current authority",
            )

        # 5. For ACCA policy-controlled authority, AAL <= 1 means
        # consequential execution requires human approval.
        if self.policy is not None and a.aal <= 1:
            return GovernanceDecision(
                action=action,
                ticker=order.ticker,
                decision=Decision.HUMAN_GATE,
                reason_code="HUMAN_APPROVAL_REQUIRED",
                authority_epoch=a.epoch,
                explanation=(
                    "Current stakeholder policy requires "
                    "human approval"
                ),
            )

        return GovernanceDecision(
            action=action,
            ticker=order.ticker,
            decision=Decision.ALLOW,
            reason_code="ALLOW",
            authority_epoch=a.epoch,
            explanation=(
                "Current authority and assurance permit the order"
            ),
        )

    def assert_epoch(self, expected_epoch: int) -> None:
        if expected_epoch != self.authority.epoch:
            raise AuthorityPreempted(
                f"authority changed from epoch {expected_epoch} to {self.authority.epoch}; re-evaluation required"
            )

    def assurance_snapshot(self):
        return {k: v.state for k, v in sorted(self.claims.items())}

class AuthorityPreempted(RuntimeError):
    """Raised when a material change supersedes authorization before commit."""
