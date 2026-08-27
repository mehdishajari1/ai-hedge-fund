"""Assurance evidence and applicability for ACCA governance.

Evidence supports assurance claims only while the assumptions under which
the evidence was established remain satisfied by the operating context.
"""

from dataclasses import dataclass, field
from typing import Any

from hedge_fund.governance.context import GovernanceContext


@dataclass
class AssuranceEvidence:
    """Evidence supporting one or more assurance claims."""

    evidence_id: str
    subject: str
    evidence_type: str
    supports: set[str]

    # Contextual assumptions under which this evidence remains applicable.
    # Example:
    # {"market_regime": {"normal", "elevated"}}
    assumptions: dict[str, set[Any]] = field(default_factory=dict)

    valid: bool = True

    def is_applicable(self, context: GovernanceContext) -> bool:
        """Determine whether this evidence applies in the current context."""

        if not self.valid:
            return False

        for dependency, allowed_values in self.assumptions.items():
            current_value = context.get(dependency)

            if current_value not in allowed_values:
                return False

        return True

    def failed_assumptions(
        self,
        context: GovernanceContext,
    ) -> dict[str, Any]:
        """Return assumptions that are not satisfied by current context."""

        failures = {}

        for dependency, allowed_values in self.assumptions.items():
            current_value = context.get(dependency)

            if current_value not in allowed_values:
                failures[dependency] = current_value

        return failures
