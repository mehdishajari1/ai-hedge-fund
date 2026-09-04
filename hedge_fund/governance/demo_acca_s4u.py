"""S4-U: Novel-regime / uncertainty applicability experiment.

Demonstrates that an unchanged agent can lose and later regain
consequential authority when the operating context moves outside,
and then back inside, the conditions represented by its assurance
evidence.

The experiment does not treat an uncertainty or novelty detector as
an authorization oracle. The detector's output is represented as
authority-relevant context. ACCA determines whether existing evidence
remains applicable and derives authority through the assurance graph
and stakeholder risk policy.
"""

from __future__ import annotations

from dataclasses import dataclass

from hedge_fund.governance.acca import ACCAEngine, ACCAChangeResult
from hedge_fund.governance.assurance_graph import AssuranceDependencyGraph
from hedge_fund.governance.context import GovernanceContext
from hedge_fund.governance.control import GovernanceControlPlane
from hedge_fund.governance.evidence import AssuranceEvidence
from hedge_fund.governance.materiality import MaterialityEvaluator
from hedge_fund.governance.models import AssuranceState
from hedge_fund.governance.policy import StakeholderRiskPolicy


CLAIM_ID = "SAFE_AUTONOMOUS_TRADING"
EVIDENCE_ID = "E-REGIME-01"


@dataclass(frozen=True)
class S4UState:
    label: str
    market_regime: str

    evidence_valid: bool
    evidence_applicable: bool

    claim_state: AssuranceState

    authority_epoch: int
    aal: int
    max_order_value: float | None

    paper_allowed: bool
    live_allowed: bool

    model_id: str
    prompt_id: str
    toolset_id: str
    credential_id: str
    declared_authority_id: str


@dataclass(frozen=True)
class S4UExperimentResult:
    normal: S4UState
    novel: S4UState
    recovered: S4UState

    transition_to_novel: ACCAChangeResult
    transition_to_recovered: ACCAChangeResult


def build_s4u():
    """Build a controlled S4-U experiment."""

    # These identifiers are experimental controls. They remain
    # unchanged across all three states.
    fixed_configuration = {
        "model_id": "MODEL-FIXED-01",
        "prompt_id": "PROMPT-FIXED-01",
        "toolset_id": "TOOLS-FIXED-01",
        "credential_id": "CREDENTIAL-FIXED-01",
        "declared_authority_id": "TGP-FIXED-01",
    }

    context = GovernanceContext(
        values={
            "market_regime": "normal",
        }
    )

    evidence = AssuranceEvidence(
        evidence_id=EVIDENCE_ID,
        subject="portfolio_manager",
        evidence_type="evaluation",
        supports={CLAIM_ID},
        assumptions={
            "market_regime": {
                "normal",
                "elevated",
            },
        },
        valid=True,
    )

    graph = AssuranceDependencyGraph([evidence])

    policy = StakeholderRiskPolicy(
        policy_id="s4u-policy",
        unassured_max_order_value=1_000.0,
        allow_live_when_unassured=False,
        require_human_gate_when_unassured=True,
    )

    control = GovernanceControlPlane.acca_trading_demo(
        "s4u-fund",
        max_order_value=10_000.0,
        policy=policy,
    )

    engine = ACCAEngine(
        context=context,
        assurance_graph=graph,
        materiality=MaterialityEvaluator([evidence]),
        control_plane=control,
    )

    return (
        engine,
        control,
        context,
        evidence,
        fixed_configuration,
    )


def snapshot(
    *,
    label: str,
    control: GovernanceControlPlane,
    context: GovernanceContext,
    evidence: AssuranceEvidence,
    fixed_configuration: dict[str, str],
) -> S4UState:

    authority = control.authority

    return S4UState(
        label=label,
        market_regime=context.get("market_regime"),
        evidence_valid=evidence.valid,
        evidence_applicable=evidence.is_applicable(context),
        claim_state=control.claims[CLAIM_ID].state,
        authority_epoch=authority.epoch,
        aal=authority.aal,
        max_order_value=authority.max_order_value,
        paper_allowed="paper_order" in authority.allowed_actions,
        live_allowed="live_order" in authority.allowed_actions,
        **fixed_configuration,
    )


def run_s4u() -> S4UExperimentResult:

    (
        engine,
        control,
        context,
        evidence,
        fixed_configuration,
    ) = build_s4u()

    normal = snapshot(
        label="NORMAL / EVALUATED REGIME",
        control=control,
        context=context,
        evidence=evidence,
        fixed_configuration=fixed_configuration,
    )

    transition_to_novel = engine.observe_context(
        "market_regime",
        "novel",
    )

    novel = snapshot(
        label="NOVEL / OUTSIDE EVIDENCE COVERAGE",
        control=control,
        context=context,
        evidence=evidence,
        fixed_configuration=fixed_configuration,
    )

    transition_to_recovered = engine.observe_context(
        "market_regime",
        "normal",
    )

    recovered = snapshot(
        label="RETURN TO EVALUATED REGIME",
        control=control,
        context=context,
        evidence=evidence,
        fixed_configuration=fixed_configuration,
    )

    return S4UExperimentResult(
        normal=normal,
        novel=novel,
        recovered=recovered,
        transition_to_novel=transition_to_novel,
        transition_to_recovered=transition_to_recovered,
    )


def _yes_no(value: bool) -> str:
    return "YES" if value else "NO"


def format_state(state: S4UState) -> str:

    max_value = (
        "NONE"
        if state.max_order_value is None
        else f"${state.max_order_value:,.2f}"
    )

    return "\n".join(
        [
            state.label,
            "-" * len(state.label),
            f"Market regime:          {state.market_regime}",
            f"Evidence valid:         {_yes_no(state.evidence_valid)}",
            f"Evidence applicable:    {_yes_no(state.evidence_applicable)}",
            f"Assurance claim:        {state.claim_state.value}",
            f"Authority epoch:        {state.authority_epoch}",
            f"AAL:                    {state.aal}",
            f"Max order value:        {max_value}",
            f"Paper authority:        {_yes_no(state.paper_allowed)}",
            f"Live authority:         {_yes_no(state.live_allowed)}",
            "",
            "Fixed experimental controls:",
            f"  Model:                {state.model_id}",
            f"  Prompt:               {state.prompt_id}",
            f"  Tools:                {state.toolset_id}",
            f"  Credentials:          {state.credential_id}",
            f"  Declared authority:   {state.declared_authority_id}",
        ]
    )


def format_s4u_report(result: S4UExperimentResult) -> str:

    return "\n\n".join(
        [
            "",
            "S4-U - NOVEL REGIME / EVIDENCE APPLICABILITY",
            "=" * 58,
            format_state(result.normal),
            format_state(result.novel),
            format_state(result.recovered),
            "\n".join(
                [
                    "CAUSAL RESULT",
                    "-------------",
                    "normal context",
                    "  -> evidence applicable",
                    "  -> assurance supported",
                    "  -> full policy-authorized autonomy",
                    "",
                    "novel context",
                    "  -> evidence remains VALID",
                    "  -> evidence becomes NON-APPLICABLE",
                    "  -> assurance becomes UNASSURED",
                    "  -> effective authority contracts",
                    "  -> authority epoch advances",
                    "",
                    "return to evaluated context",
                    "  -> evidence becomes applicable again",
                    "  -> assurance support is restored",
                    "  -> policy-derived authority is restored",
                    "  -> authority epoch advances again",
                ]
            ),
        ]
    )


def main() -> None:
    result = run_s4u()
    print(format_s4u_report(result))


if __name__ == "__main__":
    main()
