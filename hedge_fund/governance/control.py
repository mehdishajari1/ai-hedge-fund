"""Assurance-conditioned authority and material-change reauthorization."""
from __future__ import annotations
from copy import deepcopy
from hedge_fund.brokers.models import Order
from .models import AssuranceClaim, AssuranceState, AuthorityVector, Decision, GovernanceDecision, MaterialChange

class GovernanceControlPlane:
    """External authority owner. Agents/models never mutate this object themselves."""
    def __init__(self, authority: AuthorityVector, claims: list[AssuranceClaim]):
        self._baseline = deepcopy(authority)
        self.authority = deepcopy(authority)
        self.claims = {c.claim_id: c for c in claims}
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
        claim = self.claims[claim_id]
        claim.state = AssuranceState.HEALTHY
        claim.reason = reason
        self.recalculate_authority()

    def recalculate_authority(self) -> AuthorityVector:
        """Rebuild effective authority from approved baseline; every recalculation bumps epoch."""
        old_epoch = self.authority.epoch
        effective = deepcopy(self._baseline)
        effective.epoch = old_epoch + 1
        if any(self.claims[c].state in {AssuranceState.DEGRADED, AssuranceState.UNASSURED, AssuranceState.INCIDENT}
               for c in effective.required_claims):
            effective.allowed_actions.discard("paper_order")
        self.authority = effective
        return self.authority

    def decide_order(self, order: Order, *, live: bool = False) -> GovernanceDecision:
        action = "live_order" if live else "paper_order"
        a = self.authority
        if action in a.prohibited_actions or action not in a.allowed_actions:
            return GovernanceDecision(action=action, ticker=order.ticker, decision=Decision.DENY,
                reason_code="AUTH_ACTION_DENIED", authority_epoch=a.epoch,
                explanation="Action is outside current effective authority")
        unhealthy = [c for c in a.required_claims if self.claims[c].state != AssuranceState.HEALTHY]
        if unhealthy:
            return GovernanceDecision(action=action, ticker=order.ticker, decision=Decision.DENY,
                reason_code="ASSURANCE_UNAVAILABLE", authority_epoch=a.epoch,
                explanation=f"Required assurance not healthy: {sorted(unhealthy)}")
        value = abs(order.quantity * order.price)
        if a.max_order_value is not None and value > a.max_order_value:
            return GovernanceDecision(action=action, ticker=order.ticker, decision=Decision.DENY,
                reason_code="AUTH_LIMIT_EXCEEDED", authority_epoch=a.epoch,
                explanation=f"Order value {value:.2f} exceeds {a.max_order_value:.2f}")
        if a.allowed_tickers and order.ticker not in a.allowed_tickers:
            return GovernanceDecision(action=action, ticker=order.ticker, decision=Decision.DENY,
                reason_code="AUTH_RESOURCE_DENIED", authority_epoch=a.epoch)
        return GovernanceDecision(action=action, ticker=order.ticker, decision=Decision.ALLOW,
            reason_code="ALLOW", authority_epoch=a.epoch,
            explanation="Current authority and assurance permit the order")

    def assert_epoch(self, expected_epoch: int) -> None:
        if expected_epoch != self.authority.epoch:
            raise AuthorityPreempted(
                f"authority changed from epoch {expected_epoch} to {self.authority.epoch}; re-evaluation required"
            )

    def assurance_snapshot(self):
        return {k: v.state for k, v in sorted(self.claims.items())}

class AuthorityPreempted(RuntimeError):
    """Raised when a material change supersedes authorization before commit."""
