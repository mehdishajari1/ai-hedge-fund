from governance.demo_acca_s10 import run_s10
from governance.models import AssuranceState


def test_s10_material_path_starts_with_current_authorization():
    result = run_s10()
    m = result.material

    assert m.before.evidence_valid is True
    assert m.before.evidence_applicable is True
    assert m.before.claim_state == AssuranceState.HEALTHY

    assert m.before.authority_epoch == 1
    assert m.authorized_epoch == 1

    assert m.before.aal == 3
    assert m.before.max_order_value == 10_000.0
    assert m.before.live_allowed is True


def test_s10_material_change_contracts_authority_and_advances_epoch():
    result = run_s10()
    m = result.material

    before = m.before
    after = m.after_material_change

    assert before.evidence_valid is True
    assert after.evidence_valid is True

    assert before.evidence_applicable is True
    assert after.evidence_applicable is False

    assert before.claim_state == AssuranceState.HEALTHY
    assert after.claim_state == AssuranceState.UNASSURED

    assert before.authority_epoch == 1
    assert after.authority_epoch == 2

    assert before.aal == 3
    assert after.aal == 1

    assert before.max_order_value == 10_000.0
    assert after.max_order_value == 1_000.0

    assert before.live_allowed is True
    assert after.live_allowed is False


def test_s10_material_transition_affects_expected_evidence_and_claim():
    result = run_s10()
    transition = result.material.transition

    assert transition.assurance_changed is True

    assert transition.affected_evidence == {
        "E-S10-01"
    }

    assert transition.affected_claims == {
        "SAFE_AUTONOMOUS_TRADING"
    }

    assert transition.new_epoch > transition.old_epoch


def test_s10_stale_epoch_is_rejected():
    result = run_s10()
    m = result.material

    assert m.authorized_epoch == 1
    assert m.after_material_change.authority_epoch == 2

    assert m.stale_rejected is True
    assert m.exception_type == "AuthorityPreempted"


def test_s10_stale_action_never_reaches_broker():
    result = run_s10()
    m = result.material

    assert m.broker_calls_before == 0
    assert m.broker_calls_after == 0


def test_s10_non_material_change_does_not_advance_epoch():
    result = run_s10()
    n = result.non_material

    assert n.before.dashboard_theme == "light"
    assert n.after_non_material_change.dashboard_theme == "dark"

    assert n.transition.affected_evidence == set()
    assert n.transition.affected_claims == set()
    assert n.transition.assurance_changed is False

    assert n.authorized_epoch == 1
    assert n.before.authority_epoch == 1
    assert n.after_non_material_change.authority_epoch == 1

    assert n.transition.old_epoch == n.transition.new_epoch


def test_s10_current_epoch_action_can_cross_broker_boundary():
    result = run_s10()
    n = result.non_material

    assert n.execution_succeeded is True

    assert n.broker_calls_before == 0
    assert n.broker_calls_after == 1

    assert n.before.evidence_applicable is True
    assert n.after_non_material_change.evidence_applicable is True

    assert n.before.claim_state == AssuranceState.HEALTHY
    assert n.after_non_material_change.claim_state == AssuranceState.HEALTHY

    assert n.before.aal == n.after_non_material_change.aal == 3
    assert (
        n.before.max_order_value
        == n.after_non_material_change.max_order_value
        == 10_000.0
    )

    assert n.before.live_allowed is True
    assert n.after_non_material_change.live_allowed is True
