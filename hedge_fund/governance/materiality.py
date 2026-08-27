"""Dependency-aware material-change analysis for ACCA governance."""

from dataclasses import dataclass, field
from typing import Any

from hedge_fund.governance.evidence import AssuranceEvidence


@dataclass
class MaterialChange:
    """Result of evaluating a change for assurance relevance."""

    dependency: str
    old_value: Any
    new_value: Any
    material: bool

    affected_evidence: set[str] = field(default_factory=set)
    affected_claims: set[str] = field(default_factory=set)


class MaterialityEvaluator:
    """Determine materiality from assurance dependencies."""

    def __init__(self, evidence: list[AssuranceEvidence]):
        self.evidence = evidence

    def evaluate(
        self,
        dependency: str,
        old_value: Any,
        new_value: Any,
    ) -> MaterialChange:

        affected_evidence: set[str] = set()
        affected_claims: set[str] = set()

        # A change is assurance-relevant when current assurance
        # evidence explicitly depends on the changed property.
        for item in self.evidence:
            if dependency in item.assumptions:
                affected_evidence.add(item.evidence_id)
                affected_claims.update(item.supports)

        return MaterialChange(
            dependency=dependency,
            old_value=old_value,
            new_value=new_value,
            material=bool(affected_evidence),
            affected_evidence=affected_evidence,
            affected_claims=affected_claims,
        )
