from __future__ import annotations

from fractions import Fraction
from typing import Any

from .exact import rational, scalar_json
from .findings import Finding, Severity


MAX_EXPONENT = 64
MAX_COMPACTS = 1000
MAX_SAMPLES_PER_COMPACT = 10000


def audit_atomic_modulus(raw: dict[str, Any]) -> list[Finding]:
    """Validate exact finite records supporting a declared power concentration modulus.

    Passing checks only internal consistency of the finite record.  The opaque proof
    identifier is not dereferenced: an external proof must establish uniformity over
    the full tail, all centers in each compact, and a genuine compact exhaustion.
    """

    findings: list[Finding] = []
    if not isinstance(raw, dict):
        return [Finding(Severity.ERROR, "ATOMIC_DOCUMENT_TYPE", "$", "atomic-modulus document must be a JSON object")]
    modulus = raw.get("modulus", {})
    if not isinstance(modulus, dict):
        return [Finding(Severity.ERROR, "ATOMIC_MODULUS_TYPE", "modulus", "modulus must be a JSON object")]
    try:
        constant = rational(modulus.get("constant"))
        exponent_raw = modulus.get("exponent")
        if isinstance(exponent_raw, bool):
            raise TypeError("boolean exponent is not allowed")
        exponent = int(exponent_raw)
        if str(exponent) != str(exponent_raw):
            raise ValueError("exponent must be an exact integer")
    except (TypeError, ValueError, ZeroDivisionError) as exc:
        return [Finding(Severity.ERROR, "ATOMIC_MODULUS_TYPE", "modulus", f"invalid exact power modulus: {exc}")]
    if constant < 0 or exponent < 1:
        findings.append(Finding(Severity.ERROR, "ATOMIC_MODULUS_NONVANISHING", "modulus", "require C >= 0 and integer exponent >= 1 so C epsilon^alpha tends to zero"))
    if exponent > MAX_EXPONENT:
        findings.append(Finding(Severity.ERROR, "ATOMIC_EXPONENT_LIMIT", "modulus.exponent", f"executable records limit the integer exponent to {MAX_EXPONENT}"))
    proof_id = modulus.get("proof_id")
    if not isinstance(proof_id, str) or not proof_id.strip():
        findings.append(Finding(Severity.BLOCKED, "ATOMIC_MODULUS_PROOF_MISSING", "modulus.proof_id", "finite samples do not prove a uniform concentration modulus; supply an external proof identifier"))

    compacts = raw.get("compacts")
    if not isinstance(compacts, list) or not compacts:
        findings.append(Finding(Severity.ERROR, "ATOMIC_COMPACTS_MISSING", "compacts", "declare a nonempty finite list of compact test regions away from the origin"))
        return findings
    if len(compacts) > MAX_COMPACTS:
        return findings + [Finding(Severity.ERROR, "ATOMIC_COMPACTS_LIMIT", "compacts", f"at most {MAX_COMPACTS} compact records may be audited at once")]
    for compact_index, compact in enumerate(compacts):
        path = f"compacts.{compact_index}"
        if not isinstance(compact, dict):
            findings.append(Finding(Severity.ERROR, "ATOMIC_COMPACT_TYPE", path, "compact record must be a JSON object"))
            continue
        try:
            distance = rational(compact.get("distance_from_origin"))
        except (TypeError, ValueError, ZeroDivisionError) as exc:
            findings.append(Finding(Severity.ERROR, "ATOMIC_COMPACT_TYPE", path, f"invalid distance from origin: {exc}"))
            continue
        if distance <= 0:
            findings.append(Finding(Severity.ERROR, "ATOMIC_COMPACT_HITS_ORIGIN", f"{path}.distance_from_origin", "atomic-rigidity compacts must be disjoint from the origin"))
        samples = compact.get("samples")
        if not isinstance(samples, list) or not samples:
            findings.append(Finding(Severity.ERROR, "ATOMIC_SAMPLES_MISSING", f"{path}.samples", "each compact record requires at least one finite sample"))
            continue
        if len(samples) > MAX_SAMPLES_PER_COMPACT:
            findings.append(Finding(Severity.ERROR, "ATOMIC_SAMPLES_LIMIT", f"{path}.samples", f"at most {MAX_SAMPLES_PER_COMPACT} samples are allowed per compact record"))
            continue
        for sample_index, sample in enumerate(samples):
            sample_path = f"{path}.samples.{sample_index}"
            if not isinstance(sample, dict):
                findings.append(Finding(Severity.ERROR, "ATOMIC_SAMPLE_TYPE", sample_path, "sample must be a JSON object"))
                continue
            try:
                epsilon = rational(sample.get("epsilon"))
                mass = rational(sample.get("mass_upper"))
            except (TypeError, ValueError, ZeroDivisionError) as exc:
                findings.append(Finding(Severity.ERROR, "ATOMIC_SAMPLE_TYPE", sample_path, f"invalid exact sample: {exc}"))
                continue
            if epsilon <= 0 or mass < 0:
                findings.append(Finding(Severity.ERROR, "ATOMIC_SAMPLE_RANGE", sample_path, "require epsilon > 0 and mass_upper >= 0"))
                continue
            allowed = constant * epsilon**exponent
            if mass > allowed:
                findings.append(
                    Finding(
                        Severity.DEMOTION,
                        "ATOMIC_CONCENTRATION_EVASION",
                        sample_path,
                        "off-origin concentration exceeds the declared vanishing modulus",
                        witness={"epsilon": scalar_json(epsilon), "mass_upper": scalar_json(mass), "allowed": scalar_json(allowed)},
                        repair="strengthen the uniform-integrability proof or reject the counterterm family",
                    )
                )
    if not findings:
        findings.append(Finding(Severity.INFO, "ATOMIC_MODULUS_RECORD_VALID", "$", "finite samples are internally consistent with the declared integer-power modulus; tail uniformity, compact exhaustion, and proof validity are not inferred"))
    return findings
