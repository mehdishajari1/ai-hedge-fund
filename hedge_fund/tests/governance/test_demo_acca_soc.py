from governance.demo_acca_soc import (
    CLAIM_ID,
    EDR_DEGRADED,
    EDR_HEALTHY,
    run_acca_soc,
)
from governance.models import AssuranceState
from governance.sgp import SGPDecision


def test_acca_soc_healthy_state_supports_autonomous_containment():
    result = run_acca_soc()

    s = result.healthy

    assert s.edr_telemetry == EDR_HEALTHY

    assert s.evidence_valid is True
    assert s.evidence_applicable is True

    assert s.claim_state == AssuranceState.HEALTHY

    assert s.authority_epoch == 1

    assert s.isolate_declared_in_sgp is True

    assert (
        s.query_endpoint_decision
        == SGPDecision.ALLOW
    )

    assert (
        s.isolate_endpoint_decision
        == SGPDecision.ALLOW
    )

    assert (
        s.disable_account_decision
        == SGPDecision.HUMAN_GATE
    )

    assert (
        s.modify_firewall_decision
        == SGPDecision.DENY
    )


def test_acca_soc_degradation_preserves_evidence_validity_but_loses_applicability():
    result = run_acca_soc()

    before = result.healthy
    after = result.degraded

    assert before.evidence_valid is True
    assert after.evidence_valid is True

    assert before.evidence_applicable is True
    assert after.evidence_applicable is False

    assert after.edr_telemetry == EDR_DEGRADED

    assert (
        after.claim_state
        == AssuranceState.UNASSURED
    )


def test_acca_soc_material_change_advances_authority_epoch():
    result = run_acca_soc()

    transition = result.degradation_transition

    assert transition.assurance_changed is True

    assert transition.affected_evidence == {
        "E-SOC-01"
    }

    assert transition.affected_claims == {
        CLAIM_ID
    }

    assert transition.old_epoch == 1
    assert transition.new_epoch == 2

    assert result.degraded.authority_epoch == 2


def test_acca_soc_degradation_selectively_contracts_containment():
    result = run_acca_soc()

    before = result.healthy
    after = result.degraded

    # Investigative authority remains available.
    assert (
        before.query_endpoint_decision
        == SGPDecision.ALLOW
    )

    assert (
        after.query_endpoint_decision
        == SGPDecision.ALLOW
    )

    # Autonomous containment contracts.
    assert (
        before.isolate_endpoint_decision
        == SGPDecision.ALLOW
    )

    assert (
        after.isolate_endpoint_decision
        == SGPDecision.HUMAN_GATE
    )


def test_acca_soc_declared_sgp_authority_does_not_change():
    result = run_acca_soc()

    assert (
        result.healthy.declared_actions
        == result.degraded.declared_actions
        == result.recovered.declared_actions
    )

    assert (
        result.healthy.isolate_declared_in_sgp
        is True
    )

    assert (
        result.degraded.isolate_declared_in_sgp
        is True
    )

    assert (
        result.recovered.isolate_declared_in_sgp
        is True
    )


def test_acca_soc_preexisting_human_gate_remains_human_gated():
    result = run_acca_soc()

    assert (
        result.healthy.disable_account_decision
        == SGPDecision.HUMAN_GATE
    )

    assert (
        result.degraded.disable_account_decision
        == SGPDecision.HUMAN_GATE
    )

    assert (
        result.recovered.disable_account_decision
        == SGPDecision.HUMAN_GATE
    )


def test_acca_soc_action_outside_declared_authority_remains_denied():
    result = run_acca_soc()

    assert (
        result.healthy.modify_firewall_decision
        == SGPDecision.DENY
    )

    assert (
        result.degraded.modify_firewall_decision
        == SGPDecision.DENY
    )

    assert (
        result.recovered.modify_firewall_decision
        == SGPDecision.DENY
    )


def test_acca_soc_recovery_restores_autonomous_containment():
    result = run_acca_soc()

    s = result.recovered

    assert s.edr_telemetry == EDR_HEALTHY

    assert s.evidence_valid is True
    assert s.evidence_applicable is True

    assert s.claim_state == AssuranceState.HEALTHY

    assert (
        s.query_endpoint_decision
        == SGPDecision.ALLOW
    )

    assert (
        s.isolate_endpoint_decision
        == SGPDecision.ALLOW
    )


def test_acca_soc_recovery_creates_new_epoch():
    result = run_acca_soc()

    assert (
        result.healthy.authority_epoch
        < result.degraded.authority_epoch
        < result.recovered.authority_epoch
    )

    assert result.healthy.authority_epoch == 1
    assert result.degraded.authority_epoch == 2
    assert result.recovered.authority_epoch == 3


def test_acca_soc_same_acca_pattern_as_trading_domain():
    """
    Cross-domain architectural invariant.

    Domain-specific actions differ, but the ACCA causal pattern remains:

        relevant context change
            ->
        evidence applicability change
            ->
        assurance change
            ->
        effective authority change
            ->
        epoch advance
    """

    result = run_acca_soc()

    transition = result.degradation_transition

    assert transition.assurance_changed is True

    assert result.healthy.evidence_applicable is True
    assert result.degraded.evidence_applicable is False

    assert (
        result.healthy.claim_state
        == AssuranceState.HEALTHY
    )

    assert (
        result.degraded.claim_state
        == AssuranceState.UNASSURED
    )

    assert (
        result.healthy.isolate_endpoint_decision
        != result.degraded.isolate_endpoint_decision
    )

    assert (
        result.degraded.authority_epoch
        > result.healthy.authority_epoch
    )
