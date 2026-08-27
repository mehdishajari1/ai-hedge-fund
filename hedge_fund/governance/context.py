"""Authority-relevant operating context for ACCA governance.

Context represents conditions outside the agent that may affect whether
existing assurance evidence remains applicable.
"""

from dataclasses import dataclass, field
from typing import Any


@dataclass
class GovernanceContext:
    """Current authority-relevant operating conditions."""

    values: dict[str, Any] = field(default_factory=dict)

    def get(self, key: str, default: Any = None) -> Any:
        return self.values.get(key, default)

    def set(self, key: str, value: Any) -> tuple[Any, Any]:
        """Update a context value and return (old_value, new_value)."""
        old_value = self.values.get(key)
        self.values[key] = value
        return old_value, value

    def snapshot(self) -> dict[str, Any]:
        """Return a copy of the current context."""
        return dict(self.values)
