"""Runtime consequence boundary between financial risk and the Broker."""
from __future__ import annotations
from hedge_fund.brokers.models import Fill, Order
from hedge_fund.brokers.protocol import Broker
from .control import GovernanceControlPlane
from .models import Decision, GovernanceDecision

class GovernedExecutionGateway:
    def __init__(self, broker: Broker, governance: GovernanceControlPlane):
        self.broker = broker
        self.governance = governance
        self.decisions: list[GovernanceDecision] = []

    def place_order(self, order: Order) -> Fill | None:
        decision = self.governance.decide_order(order)
        self.decisions.append(decision)
        if decision.decision != Decision.ALLOW:
            return None
        # Commit-boundary epoch check. With today's synchronous SimBroker,
        # place_order is atomic; future async/paper/live adapters should also
        # check the epoch immediately before their irreversible commit.
        self.governance.assert_epoch(decision.authority_epoch)
        return self.broker.place_order(order)
