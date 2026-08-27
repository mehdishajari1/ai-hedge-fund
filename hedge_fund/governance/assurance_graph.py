"""Assurance dependency graph for ACCA governance.

The graph connects assurance evidence to the claims it supports and
evaluates those claims against the current operating context.
"""

from dataclasses import dataclass, field

from hedge_fund.governance.context import GovernanceContext
from hedge_fund.governance.evidence import AssuranceEvidence


@dataclass
class AssuranceClaim:
    """An assurance claim whose support is derived from evidence."""

    claim_id: str
    supported: bool = False
    supporting_evidence: set[str] = field(default_factory=set)


class AssuranceDependencyGraph:
    """Minimal evidence-to-claim dependency graph."""

    def __init__(self, evidence: list[AssuranceEvidence]):
        self.evidence = evidence

    def evaluate_claim(
        self,
        claim_id: str,
        context: GovernanceContext,
    ) -> AssuranceClaim:
        """Evaluate whether a claim currently has applicable evidence."""

        supporting_evidence: set[str] = set()

        for item in self.evidence:
            if (
                claim_id in item.supports
                and item.is_applicable(context)
            ):
                supporting_evidence.add(item.evidence_id)

        return AssuranceClaim(
            claim_id=claim_id,
            supported=bool(supporting_evidence),
            supporting_evidence=supporting_evidence,
        )
