from governance.demo_acca_s9 import run_s9
from governance.models import AssuranceState


def test_s9_initial_state_is_healthy_and_fully_authorized():
    result = run_s9()

    s = result.before

    assert s.dashboard_theme == "light"
    assert s.evidence_valid is True
    assert s.evidence_applicable is True
    assert s.claim_state == AssuranceState.HEALTHY

    assert s.authority_epoch == 1
    assert s.aal == 3
    assert s.max_order_value == 10_000.0

    assert s.paper_allowed is True
    assert s.live_allowed is True


def test_s9_irrelevant_context_value_changes():
    result = run_s9()

    assert result.before.dashboard_theme == "light"
    assert result.after.dashboard_theme == "dark"


def test_s9_irrelevant_change_affects_no_evidence_or_claims():
    result = run_s9()

    transition = result.transition

    assert transition.affected_evidence == set()
    assert transition.affected_claims == set()
    assert transition.assurance_changed is False


def test_s9_irrelevant_change_does_not_change_authority():
    result = run_s9()

    before = result.before
    after = result.after

    assert after.evidence_valid == before.evidence_valid
    assert after.evidence_applicable == before.evidence_applicable
    assert after.claim_state == before.claim_state

    assert after.aal == before.aal
    assert after.max_order_value == before.max_order_value

    assert after.paper_allowed == before.paper_allowed
    assert after.live_allowed == before.live_allowed


def test_s9_irrelevant_change_does_not_advance_epoch():
    result = run_s9()

    transition = result.transition

    assert result.before.authority_epoch == 1
    assert result.after.authority_epoch == 1

    assert transition.old_epoch == transition.new_epoch
    assert transition.old_epoch == 1
