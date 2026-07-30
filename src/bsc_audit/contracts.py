"""Strict, package-owned identities for independently versioned components."""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from importlib.resources import files
from pathlib import Path
from typing import Any


CONTRACT_RESOURCE = "component_contract.json"
CONTRACT_SCHEMA = "bsc-component-contract/v2"
SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
TOKEN_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._/-]{0,191}$")
SCHEMA_NAME_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]*\.schema\.json$")


@dataclass(frozen=True)
class ProtocolIdentity:
    source_path: str
    version: str
    sha256: str


@dataclass(frozen=True)
class TheoremKernelIdentity:
    language: str
    certificate_version: str
    gate_id: str
    authority: str
    authority_scope: str
    schema: str
    schema_sha256: str


@dataclass(frozen=True)
class CensusKernelIdentity:
    language: str
    certificate_version: str
    gate_id: str
    authority: str
    authority_scope: str
    schema: str
    schema_sha256: str


@dataclass(frozen=True)
class ReturnContractIdentity:
    version: str
    authority: str
    schema: str
    schema_sha256: str


@dataclass(frozen=True)
class ComponentContract:
    contract_schema: str
    protocol: ProtocolIdentity
    theorem_kernel: TheoremKernelIdentity
    census_kernel: CensusKernelIdentity
    return_contract: ReturnContractIdentity
    sha256: str

    def release_record(self) -> dict[str, object]:
        """Return the component bill of materials embedded in release metadata."""

        return {
            "contract_schema": self.contract_schema,
            "contract_sha256": self.sha256,
            "census_kernel": {
                "authority": self.census_kernel.authority,
                "authority_scope": self.census_kernel.authority_scope,
                "certificate_version": self.census_kernel.certificate_version,
                "gate_id": self.census_kernel.gate_id,
                "language": self.census_kernel.language,
                "schema": self.census_kernel.schema,
                "schema_sha256": self.census_kernel.schema_sha256,
            },
            "protocol": {
                "sha256": self.protocol.sha256,
                "version": self.protocol.version,
            },
            "return_contract": {
                "authority": self.return_contract.authority,
                "schema": self.return_contract.schema,
                "schema_sha256": self.return_contract.schema_sha256,
                "version": self.return_contract.version,
            },
            "theorem_kernel": {
                "authority": self.theorem_kernel.authority,
                "authority_scope": self.theorem_kernel.authority_scope,
                "certificate_version": self.theorem_kernel.certificate_version,
                "gate_id": self.theorem_kernel.gate_id,
                "language": self.theorem_kernel.language,
                "schema": self.theorem_kernel.schema,
                "schema_sha256": self.theorem_kernel.schema_sha256,
            },
        }


def _strict_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    value: dict[str, Any] = {}
    for key, item in pairs:
        if key in value:
            raise ValueError(f"duplicate component-contract key: {key!r}")
        value[key] = item
    return value


def _exact_keys(value: object, expected: set[str], path: str) -> dict[str, Any]:
    if not isinstance(value, dict) or set(value) != expected:
        observed = sorted(value) if isinstance(value, dict) else type(value).__name__
        raise ValueError(
            f"{path} keys differ: expected {sorted(expected)!r}, found {observed!r}"
        )
    return value


def _token(value: object, path: str) -> str:
    if not isinstance(value, str) or TOKEN_RE.fullmatch(value) is None:
        raise ValueError(f"{path} must be a canonical component token")
    return value


def _digest(value: object, path: str) -> str:
    if not isinstance(value, str) or SHA256_RE.fullmatch(value) is None:
        raise ValueError(f"{path} must be one lowercase SHA-256 digest")
    return value


def _schema_name(value: object, path: str) -> str:
    if not isinstance(value, str) or SCHEMA_NAME_RE.fullmatch(value) is None:
        raise ValueError(f"{path} must be a portable schema filename")
    return value


def parse_component_contract(data: bytes) -> ComponentContract:
    """Parse one canonical strict-JSON component contract."""

    try:
        text = data.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise ValueError("component contract must be UTF-8") from exc
    try:
        raw = json.loads(
            text,
            object_pairs_hook=_strict_object,
            parse_constant=lambda value: (_ for _ in ()).throw(ValueError(value)),
        )
    except (json.JSONDecodeError, ValueError) as exc:
        raise ValueError(f"component contract is not strict JSON: {exc}") from exc
    root = _exact_keys(
        raw,
        {
            "census_kernel",
            "contract_schema",
            "protocol",
            "return_contract",
            "theorem_kernel",
        },
        "$",
    )
    if root["contract_schema"] != CONTRACT_SCHEMA:
        raise ValueError(
            f"unsupported component contract schema: {root['contract_schema']!r}"
        )

    protocol = _exact_keys(
        root["protocol"],
        {"sha256", "source_path", "version"},
        "$.protocol",
    )
    source_path = _token(protocol["source_path"], "$.protocol.source_path")
    if "/" in source_path or source_path != "BSC_AUDIT_LLM_PACKET.md":
        raise ValueError("$.protocol.source_path must name the canonical root packet")
    returned = _exact_keys(
        root["return_contract"],
        {"authority", "schema", "schema_sha256", "version"},
        "$.return_contract",
    )
    theorem = _exact_keys(
        root["theorem_kernel"],
        {
            "authority",
            "authority_scope",
            "certificate_version",
            "gate_id",
            "language",
            "schema",
            "schema_sha256",
        },
        "$.theorem_kernel",
    )
    census = _exact_keys(
        root["census_kernel"],
        {
            "authority",
            "authority_scope",
            "certificate_version",
            "gate_id",
            "language",
            "schema",
            "schema_sha256",
        },
        "$.census_kernel",
    )

    canonical = (
        json.dumps(
            raw,
            indent=2,
            sort_keys=True,
            ensure_ascii=False,
            allow_nan=False,
        )
        + "\n"
    ).encode("utf-8")
    if data != canonical:
        raise ValueError("component contract must use canonical sorted JSON with LF")

    return ComponentContract(
        contract_schema=CONTRACT_SCHEMA,
        protocol=ProtocolIdentity(
            source_path=source_path,
            version=_token(protocol["version"], "$.protocol.version"),
            sha256=_digest(protocol["sha256"], "$.protocol.sha256"),
        ),
        theorem_kernel=TheoremKernelIdentity(
            language=_token(theorem["language"], "$.theorem_kernel.language"),
            certificate_version=_token(
                theorem["certificate_version"],
                "$.theorem_kernel.certificate_version",
            ),
            gate_id=_token(theorem["gate_id"], "$.theorem_kernel.gate_id"),
            authority=_token(
                theorem["authority"],
                "$.theorem_kernel.authority",
            ),
            authority_scope=_token(
                theorem["authority_scope"],
                "$.theorem_kernel.authority_scope",
            ),
            schema=_schema_name(theorem["schema"], "$.theorem_kernel.schema"),
            schema_sha256=_digest(
                theorem["schema_sha256"],
                "$.theorem_kernel.schema_sha256",
            ),
        ),
        census_kernel=CensusKernelIdentity(
            language=_token(census["language"], "$.census_kernel.language"),
            certificate_version=_token(
                census["certificate_version"],
                "$.census_kernel.certificate_version",
            ),
            gate_id=_token(census["gate_id"], "$.census_kernel.gate_id"),
            authority=_token(census["authority"], "$.census_kernel.authority"),
            authority_scope=_token(
                census["authority_scope"],
                "$.census_kernel.authority_scope",
            ),
            schema=_schema_name(census["schema"], "$.census_kernel.schema"),
            schema_sha256=_digest(
                census["schema_sha256"],
                "$.census_kernel.schema_sha256",
            ),
        ),
        return_contract=ReturnContractIdentity(
            version=_token(returned["version"], "$.return_contract.version"),
            authority=_token(returned["authority"], "$.return_contract.authority"),
            schema=_schema_name(returned["schema"], "$.return_contract.schema"),
            schema_sha256=_digest(
                returned["schema_sha256"],
                "$.return_contract.schema_sha256",
            ),
        ),
        sha256=hashlib.sha256(data).hexdigest(),
    )


def _load_component_contract() -> ComponentContract:
    resource = files("bsc_audit").joinpath(CONTRACT_RESOURCE)
    return parse_component_contract(resource.read_bytes())


COMPONENT_CONTRACT = _load_component_contract()
PROTOCOL_VERSION = COMPONENT_CONTRACT.protocol.version
PROTOCOL_SHA256_HEX = COMPONENT_CONTRACT.protocol.sha256
PROTOCOL_SHA256 = f"sha256:{PROTOCOL_SHA256_HEX}"


def _load_strict_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(
            path.read_text(encoding="utf-8"),
            object_pairs_hook=_strict_object,
            parse_constant=lambda item: (_ for _ in ()).throw(ValueError(item)),
        )
    except (OSError, UnicodeError, json.JSONDecodeError, ValueError) as exc:
        raise ValueError(f"{path.name} is not readable strict JSON: {exc}") from exc
    if not isinstance(value, dict):
        raise ValueError(f"{path.name} must contain one JSON object")
    return value


def verify_repository_component_contract(root: Path) -> list[str]:
    """Verify canonical repository bytes against the package-owned identities."""

    failures: list[str] = []
    protocol_path = root / COMPONENT_CONTRACT.protocol.source_path
    try:
        protocol = protocol_path.read_bytes()
    except OSError as exc:
        failures.append(f"canonical protocol is unavailable: {exc}")
    else:
        actual = hashlib.sha256(protocol).hexdigest()
        if actual != COMPONENT_CONTRACT.protocol.sha256:
            failures.append(
                "canonical protocol digest differs from component contract: "
                f"expected {COMPONENT_CONTRACT.protocol.sha256}, found {actual}"
            )
        header = (
            f"**Protocol version:** `{COMPONENT_CONTRACT.protocol.version}`<br>"
        ).encode("utf-8")
        if header not in protocol.splitlines()[:8]:
            failures.append(
                "canonical protocol header differs from component-contract version"
            )

    schema_root = root / "schemas"
    for label, identity in (
        ("theorem", COMPONENT_CONTRACT.theorem_kernel),
        ("census", COMPONENT_CONTRACT.census_kernel),
        ("return", COMPONENT_CONTRACT.return_contract),
    ):
        path = schema_root / identity.schema
        try:
            data = path.read_bytes()
            schema = _load_strict_json(path)
        except (OSError, ValueError) as exc:
            failures.append(f"{label} schema is unavailable or invalid: {exc}")
            continue
        actual = hashlib.sha256(data).hexdigest()
        if actual != identity.schema_sha256:
            failures.append(
                f"{label} schema digest differs from component contract: "
                f"expected {identity.schema_sha256}, found {actual}"
            )
            continue
        try:
            if label == "theorem":
                if (
                    schema["properties"]["certificate_version"]["const"]
                    != COMPONENT_CONTRACT.theorem_kernel.certificate_version
                    or schema["$defs"]["formalStatement"]["properties"]["language"][
                        "const"
                    ]
                    != COMPONENT_CONTRACT.theorem_kernel.language
                ):
                    failures.append(
                        "theorem schema semantic identity differs from component contract"
                    )
            elif label == "census":
                if (
                    schema["properties"]["certificate_version"]["const"]
                    != COMPONENT_CONTRACT.census_kernel.certificate_version
                    or schema["$defs"]["formalStatement"]["properties"][
                        "language"
                    ]["const"]
                    != COMPONENT_CONTRACT.census_kernel.language
                ):
                    failures.append(
                        "census schema semantic identity differs from component contract"
                    )
            elif (
                schema["properties"]["return_version"]["const"]
                != COMPONENT_CONTRACT.return_contract.version
                or schema["properties"]["authority"]["const"]
                != COMPONENT_CONTRACT.return_contract.authority
            ):
                failures.append(
                    "return schema semantic identity differs from component contract"
                )
        except (KeyError, TypeError):
            failures.append(
                f"{label} schema lacks its component-identity declarations"
            )
    return failures
