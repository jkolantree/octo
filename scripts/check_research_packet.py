#!/usr/bin/env python3
"""Verify the derived-descent packet and replay its recovered generators."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
import subprocess
import sys
import tempfile
from decimal import Decimal, InvalidOperation, localcontext
from fractions import Fraction
from pathlib import Path, PurePosixPath
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
PACKET = ROOT / "research" / "derived-witnessed-descent"
LEDGER_NAME = "DIGESTS.sha256"
GENERATOR_DIRECTORY = "verification/generators"
RECOVERY_ARCHIVE_SHA256 = "76e2fb455db5f7b95f8e64156d6eddd02e08177ebde253840a0695a6650d4a5e"
RECOVERY_BASE_COMMIT = "182d71578a523d372e71d03ce75ee2631560c75d"
GENERATOR_LEDGER_SHA256 = "dcdd4894234c30c61c0a8dc46622efd50f4a5f077283553f7c01d0e52e11358d"
GENERATOR_RECORDS = (
    {
        "script": "derived_holonomy_exact.py",
        "script_sha256": "2a04f2d58072b11b2ae0e77222f58909d23fc95a94232c3fb4d8659de15a9f5d",
        "report": "derived_holonomy_report.json",
        "report_sha256": "5c7908809e6b96b45ab88d622f890284e9900aea46b13b63bb16da95c1372417",
    },
    {
        "script": "shifted_ladder_reproduce.py",
        "script_sha256": "47c33defbf2af60b15cc892cc3eadfa763a233e9575577e4398276e0458e45d3",
        "report": "shifted_ladder_report.json",
        "report_sha256": "d3b73d22536d0db325aedde452ab087f32594f7d07b58676baf2d0b7781a7428",
    },
    {
        "script": "prime_block_obstruction.py",
        "script_sha256": "91f46a5d0e83bd2e45b012b2e0d7b4647fd07b44ebac7f66da27e7385e11eb84",
        "report": "prime_block_obstruction_report.json",
        "report_sha256": "b3eee91fa1ce5454741adba7c1c038b969eee6232aa6e01c9e562d1c3d5e4054",
    },
)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def strict_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    value: dict[str, Any] = {}
    for key, item in pairs:
        if key in value:
            raise ValueError(f"duplicate JSON key {key!r}")
        value[key] = item
    return value


def load_json(path: Path) -> Any:
    return json.loads(
        path.read_text(encoding="utf-8"),
        object_pairs_hook=strict_object,
        parse_constant=lambda token: (_ for _ in ()).throw(ValueError(f"non-finite number {token}")),
    )


def parse_digest_ledger(path: Path) -> dict[str, str]:
    declared: dict[str, str] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        match = re.fullmatch(r"([0-9a-f]{64})  ([A-Za-z0-9_.-]+(?:/[A-Za-z0-9_.-]+)*)", line)
        if not match:
            raise ValueError("digest ledger contains a malformed line")
        name = match.group(2)
        pure = PurePosixPath(name)
        if pure.is_absolute() or ".." in pure.parts or name in declared:
            raise ValueError("digest ledger contains an unsafe or duplicate path")
        declared[name] = match.group(1)
    return declared


def parse_flat_digest_ledger(path: Path) -> dict[str, str]:
    declared: dict[str, str] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        match = re.fullmatch(r"([0-9a-f]{64})  ([A-Za-z0-9_.-]+)", line)
        if not match or match.group(2) in declared:
            raise ValueError("generator checksum ledger contains a malformed or duplicate line")
        declared[match.group(2)] = match.group(1)
    return declared


def verify_recovery_record(recovery: Any) -> list[str]:
    failures: list[str] = []
    if not isinstance(recovery, dict) or recovery.get("schema") != "bsc-research-generator-recovery/v1":
        return ["generator recovery record has an unsupported schema"]
    expected_keys = {
        "archive_sha256",
        "embedded_checksum_ledger",
        "generators",
        "prior_release",
        "schema",
        "source_authentication",
        "verification",
    }
    if set(recovery) != expected_keys:
        failures.append("generator recovery record has unexpected fields")
    if recovery.get("archive_sha256") != RECOVERY_ARCHIVE_SHA256:
        failures.append("generator recovery archive digest changed")
    if recovery.get("embedded_checksum_ledger") != {
        "path": f"{GENERATOR_DIRECTORY}/SCRIPT_SHA256SUMS",
        "sha256": GENERATOR_LEDGER_SHA256,
    }:
        failures.append("generator recovery embedded checksum record changed")
    if recovery.get("prior_release") != {
        "commit_sha": RECOVERY_BASE_COMMIT,
        "status": "published_without_generators",
        "tag": "v0.3.0-alpha.3",
    }:
        failures.append("generator recovery prior-release boundary changed")
    expected_records = [
        {
            "path": f"{GENERATOR_DIRECTORY}/{record['script']}",
            "report_path": f"verification/{record['report']}",
            "report_sha256": record["report_sha256"],
            "sha256": record["script_sha256"],
            "status": "exact_source_recovered_and_replayed",
        }
        for record in GENERATOR_RECORDS
    ]
    if recovery.get("generators") != expected_records:
        failures.append("generator recovery records changed")
    expected_verification = {
        "archive_safety": "pass_flat_regular_files_no_path_traversal_or_name_collision",
        "embedded_checksum_ledger": "pass",
        "isolated_replay": "pass",
        "python_syntax": "pass",
        "report_comparison": "exact_after_crlf_to_lf_canonicalization",
        "static_import_scope": "standard_library_only",
    }
    if recovery.get("verification") != expected_verification:
        failures.append("generator recovery verification record changed")
    if recovery.get("source_authentication") != "user-supplied archive; origin not independently authenticated":
        failures.append("generator recovery source-authentication boundary changed")
    return failures


def verify_generator_integrity(packet: Path) -> list[str]:
    failures: list[str] = []
    generator_root = packet / PurePosixPath(GENERATOR_DIRECTORY)
    expected_names = {record["script"] for record in GENERATOR_RECORDS} | {"SCRIPT_SHA256SUMS"}
    actual_names = {path.name for path in generator_root.iterdir() if path.is_file()} if generator_root.is_dir() else set()
    if actual_names != expected_names:
        failures.append("recovered generator directory contents changed")
    for record in GENERATOR_RECORDS:
        script = generator_root / record["script"]
        if not script.is_file() or sha256(script) != record["script_sha256"]:
            failures.append(f"trusted generator digest mismatch: {record['script']}")
    ledger = generator_root / "SCRIPT_SHA256SUMS"
    if not ledger.is_file() or sha256(ledger) != GENERATOR_LEDGER_SHA256:
        failures.append("recovered generator checksum ledger digest mismatch")
    try:
        declared = parse_flat_digest_ledger(ledger)
    except (OSError, UnicodeError, ValueError) as exc:
        failures.append(str(exc))
    else:
        expected = {record["script"]: record["script_sha256"] for record in GENERATOR_RECORDS}
        if declared != expected:
            failures.append("generator checksum ledger does not exactly bind the recovered scripts")
    return failures


def canonical_lf_report(payload: bytes) -> bytes:
    if b"\r" in payload.replace(b"\r\n", b""):
        raise ValueError("generated report contains a non-CRLF carriage return")
    return payload.replace(b"\r\n", b"\n")


def replay_recovered_generators(packet: Path) -> list[str]:
    """Execute only the hard-coded, hash-verified scripts in an isolated directory."""

    failures: list[str] = []
    source_root = packet / PurePosixPath(GENERATOR_DIRECTORY)
    with tempfile.TemporaryDirectory(prefix="bsc-research-generators-") as directory:
        staging = Path(directory)
        for record in GENERATOR_RECORDS:
            shutil.copyfile(source_root / record["script"], staging / record["script"])
        for record in GENERATOR_RECORDS:
            try:
                result = subprocess.run(
                    [sys.executable, "-I", "-B", record["script"]],
                    cwd=staging,
                    capture_output=True,
                    text=True,
                    encoding="utf-8",
                    errors="strict",
                    timeout=60,
                    check=False,
                )
            except (OSError, subprocess.TimeoutExpired, UnicodeError) as exc:
                failures.append(f"generator execution failed: {record['script']}: {type(exc).__name__}")
                continue
            if result.returncode != 0:
                failures.append(f"generator returned nonzero: {record['script']}")
                continue
            if result.stderr:
                failures.append(f"generator wrote unexpected stderr: {record['script']}")
            printed = re.findall(r"report_sha256=([0-9a-f]{64})", result.stdout)
            if printed != [record["report_sha256"]]:
                failures.append(f"generator printed an unexpected report digest: {record['script']}")
            generated = staging / record["report"]
            preserved = packet / "verification" / record["report"]
            try:
                generated_bytes = canonical_lf_report(generated.read_bytes())
            except (OSError, ValueError) as exc:
                failures.append(f"generated report unavailable or malformed: {record['report']}: {exc}")
                continue
            if generated_bytes != preserved.read_bytes():
                failures.append(f"generated report differs from preserved bytes: {record['report']}")
            if hashlib.sha256(generated_bytes).hexdigest() != record["report_sha256"]:
                failures.append(f"generated report digest mismatch: {record['report']}")
        expected_outputs = {
            *(record["script"] for record in GENERATOR_RECORDS),
            *(record["report"] for record in GENERATOR_RECORDS),
        }
        actual_outputs = {path.name for path in staging.iterdir() if path.is_file()}
        if actual_outputs != expected_outputs:
            failures.append("generator replay created unexpected files")
    return failures


def replay_derived_cases(cases: Any) -> list[str]:
    if not isinstance(cases, list):
        return ["derived report cases must be an array"]
    failures: list[str] = []
    for index, case in enumerate(cases):
        try:
            matrix = [[Fraction(value) for value in row] for row in case["homotopy_matrix_A"]]
            omega = [Fraction(value) for value in case["omega"]]
            certificate = case["certificate"]
            columns = len(matrix[0]) if matrix else len(certificate.get("x", []))
            if len(matrix) != len(omega) or any(len(row) != columns for row in matrix):
                raise ValueError("matrix shape mismatch")
            status = certificate["status"]
            if status == "pass":
                solution = [Fraction(value) for value in certificate["x"]]
                replay = [sum((row[column] * solution[column] for column in range(columns)), Fraction(0)) for row in matrix]
                claimed = [Fraction(value) for value in certificate["Ax"]]
                if len(solution) != columns or replay != omega or claimed != replay:
                    raise ValueError("primal equation mismatch")
            elif status == "fail":
                dual = [Fraction(value) for value in certificate["y"]]
                annihilator = [
                    sum((dual[row] * matrix[row][column] for row in range(len(matrix))), Fraction(0))
                    for column in range(columns)
                ]
                pairing = sum((dual[row] * omega[row] for row in range(len(matrix))), Fraction(0))
                claimed_annihilator = [Fraction(value) for value in certificate["yTA"]]
                claimed_pairing = Fraction(certificate["yTb"])
                if len(dual) != len(matrix) or annihilator != [Fraction(0)] * columns or claimed_annihilator != annihilator or pairing == 0 or claimed_pairing != pairing:
                    raise ValueError("dual equation mismatch")
            else:
                raise ValueError("unknown certificate status")
            if (status == "pass") != (case["derived_holonomy"] == "pass"):
                raise ValueError("certificate and derived verdict disagree")
            if bool(case["induced_homology_equal"]) != (status == "pass"):
                raise ValueError("certificate and induced-homology verdict disagree")
        except (IndexError, KeyError, TypeError, ValueError, ZeroDivisionError):
            failures.append(f"derived report certificate replay failed at case {index}")
    return failures


def verify_packet(packet: Path = PACKET) -> list[str]:
    failures: list[str] = []
    ledger_path = packet / LEDGER_NAME
    if not ledger_path.is_file():
        return ["complete digest ledger is missing"]
    try:
        declared = parse_digest_ledger(ledger_path)
    except (OSError, UnicodeError, ValueError) as exc:
        return [str(exc)]
    actual = {
        path.relative_to(packet).as_posix()
        for path in packet.rglob("*")
        if path.is_file() and path.name != LEDGER_NAME
    }
    if set(declared) != actual:
        failures.append("digest ledger paths do not exactly cover the packet")
    for name, digest in declared.items():
        path = packet / PurePosixPath(name)
        if not path.is_file() or sha256(path) != digest:
            failures.append(f"digest mismatch: {name}")

    json_names = (
        "PROVENANCE.json",
        "RECOVERY.json",
        "verification/derived_holonomy_report.json",
        "verification/prime_block_obstruction_report.json",
        "verification/shifted_ladder_report.json",
    )
    documents: dict[str, Any] = {}
    for name in json_names:
        try:
            documents[name] = load_json(packet / name)
        except (OSError, UnicodeError, ValueError, json.JSONDecodeError):
            failures.append(f"strict JSON parse failed: {name}")
    if failures:
        return sorted(set(failures))

    provenance = documents["PROVENANCE.json"]
    imports = provenance.get("imports", []) if isinstance(provenance, dict) else []
    if not isinstance(imports, list):
        failures.append("provenance imports must be an array")
    else:
        for record in imports:
            if not isinstance(record, dict) or set(record) != {"path", "sha256", "status"}:
                failures.append("provenance import record has unexpected fields")
                continue
            relative = record["path"]
            if not isinstance(relative, str) or PurePosixPath(relative).is_absolute() or ".." in PurePosixPath(relative).parts:
                failures.append("provenance contains an unsafe path")
                continue
            path = packet / PurePosixPath(relative)
            if not path.is_file() or sha256(path) != record["sha256"]:
                failures.append(f"provenance digest mismatch: {relative}")

    failures.extend(verify_recovery_record(documents["RECOVERY.json"]))

    try:
        source_records = parse_flat_digest_ledger(packet / "verification" / "SOURCE_SHA256SUMS.partial.sha256")
    except (OSError, UnicodeError, ValueError):
        failures.append("source partial checksum record is malformed")
        source_records = {}
    supplied_map = {
        "README.md": "verification/SOURCE_README.md",
        "derived_holonomy_report.json": "verification/derived_holonomy_report.json",
        "prime_block_obstruction_report.json": "verification/prime_block_obstruction_report.json",
        "shifted_ladder_report.json": "verification/shifted_ladder_report.json",
    }
    for source_name, stored_name in supplied_map.items():
        if source_records.get(source_name) != sha256(packet / stored_name):
            failures.append(f"source partial checksum mismatch: {source_name}")
    for record in GENERATOR_RECORDS:
        if source_records.get(record["script"]) != record["script_sha256"]:
            failures.append(f"source partial checksum mismatch: {record['script']}")
    expected_source_names = set(supplied_map) | {record["script"] for record in GENERATOR_RECORDS}
    if set(source_records) != expected_source_names:
        failures.append("source partial checksum record names unexpected artifacts")

    failures.extend(verify_generator_integrity(packet))
    if failures:
        return sorted(set(failures))
    failures.extend(replay_recovered_generators(packet))

    derived = documents["verification/derived_holonomy_report.json"]
    if derived.get("schema") != "derived-holonomy-exact-report/v1":
        failures.append("derived report schema is unsupported")
    exhaustive = derived.get("exhaustive_small_model_check", {})
    if exhaustive.get("map_pairs_checked") != 153 or exhaustive.get("result") != "homotopy-system verdict equals induced-homology-map equality in every case":
        failures.append("derived report exhaustive-case record changed")
    cases = derived.get("cases")
    if not isinstance(cases, list) or not all(isinstance(case, dict) for case in cases) or [case.get("derived_holonomy") for case in cases] != ["pass", "fail", "fail", "pass"]:
        failures.append("derived report fixture verdict sequence changed")
    failures.extend(replay_derived_cases(cases))

    prime = documents["verification/prime_block_obstruction_report.json"]
    if prime.get("schema") != "orthogonal-prime-block-obstruction/v1":
        failures.append("prime report schema is unsupported")
    jets = prime.get("exact_jet_annihilation")
    if not isinstance(jets, list) or len(jets) != 9:
        failures.append("prime report jet ledger changed")
    elif any(
        row.get("maximum_jet_order") != index
        or row.get("annihilating_derivative_order") != index + 1
        or row.get("exact_result") != []
        for index, row in enumerate(jets)
    ):
        failures.append("prime report exact jet annihilation record is inconsistent")
    prime_rows = prime.get("prime_growth_experiment")
    expected_counts = [(100, 25), (1000, 168), (10000, 1229), (100000, 9592), (1000000, 78498)]
    if not isinstance(prime_rows, list) or [
        (row.get("prime_cutoff"), row.get("prime_count")) for row in prime_rows
    ] != expected_counts:
        failures.append("prime report cutoff/count ledger changed")
    else:
        series: dict[str, list[Decimal]] = {}
        try:
            for row in prime_rows:
                for key, value in row["partial_lower_bounds"].items():
                    series.setdefault(key, []).append(Decimal(value))
            if any(any(value <= 0 for value in values) or values != sorted(values) for values in series.values()):
                failures.append("prime report finite lower-bound tables are not positive and monotone")
        except (InvalidOperation, KeyError, TypeError):
            failures.append("prime report decimal table is malformed")

    shifted = documents["verification/shifted_ladder_report.json"]
    if shifted.get("schema") != "shifted-ladder-reproduction/v1":
        failures.append("shifted-ladder report schema is unsupported")
    exact = shifted.get("exact_checks", {})
    if exact.get("arithmetic") != "fractions.Fraction over Q(i)" or exact.get("coefficient_identity") != "pass" or exact.get("integer_range") != [-500, 500]:
        failures.append("shifted-ladder exact finite identity record changed")
    trace_rows = shifted.get("trace_norm_convergence")
    if not isinstance(trace_rows, list) or [row.get("N") for row in trace_rows] != [4, 8, 16, 32, 64, 128, 256]:
        failures.append("shifted-ladder trace-norm cutoff ledger changed")
    else:
        try:
            with localcontext() as context:
                context.prec = 100
                for row in trace_rows:
                    partial = Decimal(row["partial_trace_norm"])
                    tail = Decimal(row["analytic_tail_bound_80digit_evaluation"])
                    enclosure = Decimal(row["enclosure_upper"])
                    if partial <= 0 or tail <= 0 or abs(enclosure - partial - tail) > Decimal("1e-59"):
                        failures.append("shifted-ladder enclosure arithmetic is inconsistent beyond final-place rounding")
                        break
        except (InvalidOperation, KeyError, TypeError):
            failures.append("shifted-ladder decimal table is malformed")
    return sorted(set(failures))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--packet", type=Path, default=PACKET)
    args = parser.parse_args(argv)
    failures = verify_packet(args.packet)
    payload = {
        "decision": "pass" if not failures else "blocked",
        "checks_run": [
            "complete_packet_digests",
            "strict_json_parse",
            "source_partial_ledger_consistency",
            "recovered_generator_hash_binding",
            "isolated_generator_execution",
            "canonical_report_byte_regeneration",
            "selected_exact_record_invariants",
            "selected_decimal_table_invariants",
        ],
        "checks_not_run": [
            "proof_assistant_kernel_verification",
            "historical_novelty_review",
            "external_source_authentication",
        ],
        "recovered_generators": sorted(record["script"] for record in GENERATOR_RECORDS),
        "findings": failures,
    }
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0 if not failures else 1


if __name__ == "__main__":
    raise SystemExit(main())
