from hedge_fund.brokers.models import Order
from hedge_fund.governance import AssuranceState, Decision, GovernanceControlPlane, MaterialChange

def gov(limit=None):
    return GovernanceControlPlane.paper_trading_default("test-fund", max_order_value=limit)

def test_default_paper_order_allowed():
    g = gov()
    d = g.decide_order(Order(ticker="AAPL", side="buy", quantity=10, price=200))
    assert d.decision == Decision.ALLOW

def test_live_order_is_explicitly_prohibited():
    g = gov()
    d = g.decide_order(Order(ticker="AAPL", side="buy", quantity=1, price=200), live=True)
    assert d.decision == Decision.DENY

def test_order_value_limit_is_machine_enforced():
    g = gov(500)
    d = g.decide_order(Order(ticker="MSFT", side="buy", quantity=2, price=400))
    assert d.reason_code == "AUTH_LIMIT_EXCEEDED"

def test_model_change_invalidates_evidence_contracts_authority_and_bumps_epoch():
    g = gov()
    old = g.authority.epoch
    affected = g.apply_material_change(MaterialChange(change_type="model_substitution", dependency="model", description="LLM changed"))
    assert affected == {"MODEL_ASSURANCE"}
    assert g.authority.epoch == old + 1
    assert "paper_order" not in g.authority.allowed_actions
    assert g.claims["MODEL_ASSURANCE"].state == AssuranceState.UNASSURED

def test_reauthorization_restores_baseline_authority_with_new_epoch():
    g = gov()
    g.apply_material_change(MaterialChange(change_type="model_substitution", dependency="model", description="LLM changed"))
    contracted = g.authority.epoch
    g.set_claim_healthy("MODEL_ASSURANCE", "evaluation passed")
    assert g.authority.epoch == contracted + 1
    assert "paper_order" in g.authority.allowed_actions

def test_stale_epoch_is_preempted():
    import pytest
    from hedge_fund.governance import AuthorityPreempted
    g = gov()
    epoch = g.authority.epoch
    g.apply_material_change(MaterialChange(change_type="monitoring_failure", dependency="monitoring", description="telemetry unavailable"))
    with pytest.raises(AuthorityPreempted):
        g.assert_epoch(epoch)
