from governance.demo_acca_s7 import run_s7
from governance.models import AssuranceState


def test_s7_stakeholders_begin_from_equivalent_governance_state():
    result = run_s7()

    c = result.conservative.before
    t = result.tolerant.before

    assert c.model_id == t.model_id
    assert c.market_regime == t.market_regime == "normal"
    assert c.evidence_id == t.evidence_id
    assert c.evidence_valid == t.evidence_valid is True
    assert c.evidence_applicable == t.evidence_applicable is True
    assert c.claim_state == t.claim_state == AssuranceState.HEALTHY

    assert c.authority_epoch == t.authority_epoch == 1
    assert c.aal == t.aal == 3
    assert c.max_order_value == t.max_order_value == 10_000.0
    assert c.paper_allowed == t.paper_allowed is True
    assert c.live_allowed == t.live_allowed is True


def test_s7_same_material_change_produces_same_assurance_state():
    result = run_s7()

    c = result.conservative.after
    t = result.tolerant.after

    assert c.market_regime == t.market_regime == "novel"

    assert c.evidence_valid == t.evidence_valid is True
    assert c.evidence_applicable == t.evidence_applicable is False

    assert c.claim_state == t.claim_state == AssuranceState.UNASSURED
    assert c.authority_epoch == t.authority_epoch == 2


def test_s7_only_stakeholder_policy_differs():
    result = run_s7()

    c = result.conservative.after
    t = result.tolerant.after

    assert c.model_id == t.model_id
    assert c.market_regime == t.market_regime

    assert c.prompt_id == t.prompt_id
    assert c.tools_id == t.tools_id
    assert c.credentials_id == t.credentials_id

    assert c.declared_authority_id == t.declared_authority_id

    assert c.evidence_id == t.evidence_id
    assert c.evidence_valid == t.evidence_valid
    assert c.evidence_applicable == t.evidence_applicable
    assert c.claim_state == t.claim_state

    assert c.policy_id != t.policy_id


def test_s7_both_material_transitions_affect_same_evidence_and_claim():
    result = run_s7()

    c = result.conservative.transition
    t = result.tolerant.transition

    assert c.assurance_changed is True
    assert t.assurance_changed is True

    assert c.affected_evidence == t.affected_evidence == {
        "E-S7-01"
    }

    assert c.affected_claims == t.affected_claims == {
        "SAFE_AUTONOMOUS_TRADING"
    }

    assert c.old_epoch == t.old_epoch == 1
    assert c.new_epoch == t.new_epoch == 2


def test_s7_conservative_policy_contracts_authority_strongly():
    result = run_s7()

    c = result.conservative.after

    assert c.claim_state == AssuranceState.UNASSURED

    assert c.aal == 1
    assert c.max_order_value == 1_000.0

    assert c.paper_allowed is True
    assert c.live_allowed is False


def test_s7_risk_tolerant_policy_retains_greater_authority():
    result = run_s7()

    t = result.tolerant.after

    assert t.claim_state == AssuranceState.UNASSURED

    assert t.aal == 3
    assert t.max_order_value == 5_000.0

    assert t.paper_allowed is True
    assert t.live_allowed is True


def test_s7_identical_assurance_can_produce_different_effective_authority():
    result = run_s7()

    c = result.conservative.after
    t = result.tolerant.after

    # Assurance inputs are identical.
    assert c.evidence_valid == t.evidence_valid
    assert c.evidence_applicable == t.evidence_applicable
    assert c.claim_state == t.claim_state

    # Effective authority differs because policy differs.
    assert c.aal != t.aal
    assert c.max_order_value != t.max_order_value
    assert c.live_allowed != t.live_allowed
