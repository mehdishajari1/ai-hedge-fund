from governance.demo_acca_s4u import run_s4u
from governance.models import AssuranceState


def test_s4u_normal_regime_has_applicable_evidence_and_full_authority():

    result = run_s4u()
    state = result.normal

    assert state.market_regime == "normal"

    assert state.evidence_valid is True
    assert state.evidence_applicable is True

    assert state.claim_state == AssuranceState.HEALTHY

    assert state.aal == 3
    assert state.max_order_value == 10_000.0

    assert state.paper_allowed is True
    assert state.live_allowed is True


def test_s4u_novel_regime_preserves_evidence_validity_but_loses_applicability():

    result = run_s4u()

    before = result.normal
    after = result.novel

    assert before.evidence_valid is True
    assert after.evidence_valid is True

    assert before.evidence_applicable is True
    assert after.evidence_applicable is False

    assert (
        after.claim_state
        == AssuranceState.UNASSURED
    )


def test_s4u_novel_regime_selectively_contracts_authority():

    result = run_s4u()

    before = result.normal
    after = result.novel

    assert before.aal == 3
    assert after.aal == 1

    assert before.max_order_value == 10_000.0
    assert after.max_order_value == 1_000.0

    assert before.paper_allowed is True
    assert after.paper_allowed is True

    assert before.live_allowed is True
    assert after.live_allowed is False

    assert after.authority_epoch > before.authority_epoch


def test_s4u_agent_and_declared_authority_remain_unchanged():

    result = run_s4u()

    states = [
        result.normal,
        result.novel,
        result.recovered,
    ]

    assert len({s.model_id for s in states}) == 1
    assert len({s.prompt_id for s in states}) == 1
    assert len({s.toolset_id for s in states}) == 1
    assert len({s.credential_id for s in states}) == 1
    assert len(
        {s.declared_authority_id for s in states}
    ) == 1


def test_s4u_novel_transition_is_material_and_changes_assurance():

    result = run_s4u()
    transition = result.transition_to_novel

    assert transition.dependency == "market_regime"
    assert transition.old_value == "normal"
    assert transition.new_value == "novel"

    assert transition.dependency_relevant is True
    assert transition.assurance_changed is True

    assert transition.affected_evidence == {
        "E-REGIME-01"
    }

    assert transition.affected_claims == {
        "SAFE_AUTONOMOUS_TRADING"
    }

    assert transition.new_epoch > transition.old_epoch


def test_s4u_return_to_evaluated_regime_restores_assurance_and_authority():

    result = run_s4u()

    novel = result.novel
    recovered = result.recovered

    assert recovered.market_regime == "normal"

    assert recovered.evidence_valid is True
    assert recovered.evidence_applicable is True

    assert (
        recovered.claim_state
        == AssuranceState.HEALTHY
    )

    assert recovered.aal == 3
    assert recovered.max_order_value == 10_000.0

    assert recovered.paper_allowed is True
    assert recovered.live_allowed is True

    assert (
        recovered.authority_epoch
        > novel.authority_epoch
    )


def test_s4u_recovery_is_new_epoch_not_reuse_of_old_authorization():

    result = run_s4u()

    assert (
        result.normal.authority_epoch
        < result.novel.authority_epoch
        < result.recovered.authority_epoch
    )
