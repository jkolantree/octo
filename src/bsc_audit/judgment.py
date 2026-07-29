from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from .provenance import is_sha256


JUDGMENT_VERSION = "bsc-checked-judgment/v1"
JudgmentResult = Literal["pass", "fail", "inconclusive", "not_run"]


@dataclass(frozen=True)
class CheckedJudgment:
    """A replay result whose authority cannot be inferred from its label alone."""

    subject_id: str
    subject_sha256: str
    predicate: str
    scope: str
    method_id: str
    evidence_id: str
    evidence_sha256: str
    authority: str
    result: JudgmentResult

    def __post_init__(self) -> None:
        for field in (
            "subject_id",
            "predicate",
            "scope",
            "method_id",
            "evidence_id",
            "authority",
        ):
            value = getattr(self, field)
            if not isinstance(value, str) or not value.strip():
                raise ValueError(
                    f"checked judgment {field} must be a nonempty string"
                )
        if not is_sha256(self.subject_sha256):
            raise ValueError("checked judgment subject_sha256 is invalid")
        if not is_sha256(self.evidence_sha256):
            raise ValueError("checked judgment evidence_sha256 is invalid")
        if self.result not in {"pass", "fail", "inconclusive", "not_run"}:
            raise ValueError("checked judgment result is invalid")

    def supports(
        self,
        *,
        subject_id: str,
        subject_sha256: str,
        predicate: str,
        scope: str,
        method_id: str,
        evidence_id: str,
        evidence_sha256: str,
        authority: str,
        result: JudgmentResult,
    ) -> bool:
        return (
            self.subject_id == subject_id
            and self.subject_sha256 == subject_sha256
            and self.predicate == predicate
            and self.scope == scope
            and self.method_id == method_id
            and self.evidence_id == evidence_id
            and self.evidence_sha256 == evidence_sha256
            and self.authority == authority
            and self.result == result
        )

    def to_dict(self) -> dict[str, object]:
        return {
            "judgment_version": JUDGMENT_VERSION,
            "subject": {
                "id": self.subject_id,
                "sha256": self.subject_sha256,
            },
            "predicate": self.predicate,
            "scope": self.scope,
            "method_id": self.method_id,
            "evidence_identity": {
                "id": self.evidence_id,
                "sha256": self.evidence_sha256,
            },
            "authority": self.authority,
            "result": self.result,
        }
