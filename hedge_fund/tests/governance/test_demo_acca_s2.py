from governance.demo_acca_s2 import (
    APPROVED_MODEL,
    SUBSTITUTED_MODEL,
    run_s2,
)
from governance.models import AssuranceState


def test_approved_model_has_applicable_evidence_and_full_authority():
    result = run_s2()

    s = result.approved

    assert s.model_id == APPROVED_MODEL
    assert s.evidence_valid is True
    assert s.evidence_applicable is True
    assert s.claim_state == AssuranceState.HEALTHY

    assert s.authority_epoch == 1
    assert s.aal == 3
    assert s.max_order_value == 10_000.0

    assert s.paper_allowed is True
    assert s.live_allowed is True


def test_model_substitution_preserves_evidence_validity_but_loses_applicability():
    result = run_s2()

    before = result.approved
    after = result.substituted

    assert before.evidence_valid is True
    assert after.evidence_valid is True

    assert before.evidence_applicable is True
    assert after.evidence_applicable is False

    assert after.model_id == SUBSTITUTED_MODEL


def test_model_substitution_contracts_authority():
    result = run_s2()

    before = result.approved
    after = result.substituted

    assert before.claim_state == AssuranceState.HEALTHY
    assert after.claim_state == AssuranceState.UNASSURED

    assert before.aal == 3
    assert after.aal == 1

    assert before.max_order_value == 10_000.0
    assert after.max_order_value == 1_000.0

    assert before.paper_allowed is True
    assert after.paper_allowed is True

    assert before.live_allowed is True
    assert after.live_allowed is False

    assert after.authority_epoch > before.authority_epoch


def test_non_model_controls_remain_unchanged():
    result = run_s2()

    a = result.approved
    b = result.substituted
    c = result.recovered

    assert a.prompt_id == b.prompt_id == c.prompt_id
    assert a.tools_id == b.tools_id == c.tools_id
    assert a.credentials_id == b.credentials_id == c.credentials_id
    assert (
        a.declared_authority_id
        == b.declared_authority_id
        == c.declared_authority_id
    )


def test_model_substitution_is_material_and_affects_expected_assurance_path():
    result = run_s2()

    transition = result.substitution_transition

    assert transition.assurance_changed is True

    assert transition.affected_evidence == {
        "E-MODEL-01"
    }

    assert transition.affected_claims == {
        "SAFE_AUTONOMOUS_TRADING"
    }

    assert transition.new_epoch > transition.old_epoch


def test_restoring_approved_model_restores_assurance_and_authority():
    result = run_s2()

    s = result.recovered

    assert s.model_id == APPROVED_MODEL
    assert s.evidence_valid is True
    assert s.evidence_applicable is True
    assert s.claim_state == AssuranceState.HEALTHY

    assert s.aal == 3
    assert s.max_order_value == 10_000.0

    assert s.paper_allowed is True
    assert s.live_allowed is True


def test_recovery_creates_new_epoch_instead_of_reusing_old_authorization():
    result = run_s2()

    assert (
        result.approved.authority_epoch
        < result.substituted.authority_epoch
        < result.recovered.authority_epoch
    )

    assert result.approved.authority_epoch == 1
    assert result.substituted.authority_epoch == 2
    assert result.recovered.authority_epoch == 3
