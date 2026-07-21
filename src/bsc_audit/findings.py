from __future__ import annotations

from dataclasses import asdict, dataclass
from enum import Enum
from typing import Any


class Severity(str, Enum):
    ERROR = "ERROR"
    BLOCKED = "BLOCKED"
    WARNING = "WARNING"
    INFO = "INFO"
    DEMOTION = "DEMOTION"


BLOCKING = {Severity.ERROR, Severity.BLOCKED, Severity.DEMOTION}


@dataclass(frozen=True)
class Finding:
    severity: Severity
    code: str
    path: str
    message: str
    witness: Any | None = None
    repair: str | None = None

    def to_dict(self) -> dict[str, Any]:
        result = asdict(self)
        result["severity"] = self.severity.value
        return {key: value for key, value in result.items() if value is not None}


def is_blocked(findings: list[Finding]) -> bool:
    return any(finding.severity in BLOCKING for finding in findings)


def exit_code(findings: list[Finding]) -> int:
    """Map findings to the stable CLI contract.

    ``0`` is structurally valid, ``1`` is a meaningful but blocked or demoted
    claim, and ``2`` is malformed input. Internal failures are handled by the
    CLI as exit ``70``.
    """

    severities = {finding.severity for finding in findings}
    if Severity.ERROR in severities:
        return 2
    if Severity.BLOCKED in severities or Severity.DEMOTION in severities:
        return 1
    return 0


def decision(findings: list[Finding]) -> str:
    severities = {finding.severity for finding in findings}
    if Severity.ERROR in severities:
        return "prohibited"
    if Severity.DEMOTION in severities:
        return "demoted"
    if Severity.BLOCKED in severities:
        return "blocked"
    if Severity.WARNING in severities:
        return "no_blocking_findings_with_warnings"
    return "no_blocking_findings"
