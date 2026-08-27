"""ACCA orchestration between context, evidence, assurance, and authority."""

from dataclasses import dataclass

from hedge_fund.governance.assurance_graph import AssuranceDependencyGraph
from hedge_fund.governance.context import GovernanceContext
from hedge_fund.governance.control import GovernanceControlPlane
from hedge_fund.governance.materiality import MaterialityEvaluator
from hedge_fund.governance.models import AssuranceState


@dataclass
class ACCAChangeResult:
    dependency: str
    old_value: object
    new_value: object

    dependency_relevant: bool
    assurance_changed: bool

    affected_evidence: set[str]
    affected_claims: set[str]

    old_epoch: int
    new_epoch: int


class ACCAEngine:
    """Coordinate material change, assurance, and effective authority."""

    def __init__(
        self,
        *,
        context: GovernanceContext,
        assurance_graph: AssuranceDependencyGraph,
        materiality: MaterialityEvaluator,
        control_plane: GovernanceControlPlane,
    ):
        self.context = context
        self.assurance_graph = assurance_graph
        self.materiality = materiality
        self.control_plane = control_plane

    def observe_context(
        self,
        dependency: str,
        value: object,
    ) -> ACCAChangeResult:

        old_value = self.context.get(dependency)

        # Nothing changed.
        if old_value == value:
            epoch = self.control_plane.authority.epoch

            return ACCAChangeResult(
                dependency=dependency,
                old_value=old_value,
                new_value=value,
                dependency_relevant=False,
                assurance_changed=False,
                affected_evidence=set(),
                affected_claims=set(),
                old_epoch=epoch,
                new_epoch=epoch,
            )

        # Evaluate dependency relevance before modifying context.
        material = self.materiality.evaluate(
            dependency=dependency,
            old_value=old_value,
            new_value=value,
        )

        old_epoch = self.control_plane.authority.epoch

        # Irrelevant change: update context, but do nothing else.
        if not material.material:
            self.context.set(dependency, value)

            return ACCAChangeResult(
                dependency=dependency,
                old_value=old_value,
                new_value=value,
                dependency_relevant=False,
                assurance_changed=False,
                affected_evidence=set(),
                affected_claims=set(),
                old_epoch=old_epoch,
                new_epoch=old_epoch,
            )

        # Snapshot old claim state before the environmental change.
        before = {
            claim_id: self.assurance_graph.evaluate_claim(
                claim_id,
                self.context,
            )
            for claim_id in material.affected_claims
        }

        # Apply the context change.
        self.context.set(dependency, value)

        assurance_changed = False

        for claim_id in material.affected_claims:
            after = self.assurance_graph.evaluate_claim(
                claim_id,
                self.context,
            )

            if before[claim_id].supported != after.supported:
                assurance_changed = True

                if after.supported:
                    self.control_plane.set_claim_state(
                        claim_id,
                        AssuranceState.HEALTHY,
                        reason=(
                            f"Applicable evidence restored: "
                            f"{sorted(after.supporting_evidence)}"
                        ),
                    )
                else:
                    self.control_plane.set_claim_state(
                        claim_id,
                        AssuranceState.UNASSURED,
                        reason=(
                            f"No applicable evidence after "
                            f"{dependency} changed from "
                            f"{old_value} to {value}"
                        ),
                    )

        return ACCAChangeResult(
            dependency=dependency,
            old_value=old_value,
            new_value=value,
            dependency_relevant=True,
            assurance_changed=assurance_changed,
            affected_evidence=material.affected_evidence,
            affected_claims=material.affected_claims,
            old_epoch=old_epoch,
            new_epoch=self.control_plane.authority.epoch,
        )
