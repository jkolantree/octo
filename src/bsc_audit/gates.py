from __future__ import annotations

from collections import defaultdict, deque
from pathlib import Path
from typing import Any

from .findings import Finding, Severity
from .manifest import DEPLOYMENT_STATES, EVIDENCE_MATURITY, evidence_index, verified_evidence_ids


GATE_STATES = {"unrun", "pass", "fail", "conflict"}


def _bound_evidence_is_valid(
    gate_id: str,
    state: str,
    references: object,
    records: dict[str, dict[str, Any]],
    verified_ids: set[str],
) -> tuple[bool, dict[str, Any]]:
    if not isinstance(references, list) or not all(isinstance(value, str) for value in references):
        return False, {"reason": "evidence references must be a list of identifiers"}
    if state == "unrun":
        return (not references), {"reason": "unrun gates cannot carry result evidence"}
    if not references:
        return False, {"reason": "a concluded gate requires evidence"}
    missing = sorted(set(references) - set(records))
    unverified = sorted(set(references) - verified_ids)
    unbound = sorted(
        evidence_id
        for evidence_id in references
        if evidence_id in records and gate_id not in records[evidence_id].get("verifies_gates", [])
    )
    expected_results = {"pass"} if state == "pass" else ({"fail"} if state == "fail" else {"pass", "fail"})
    observed_results = {
        records[evidence_id].get("result")
        for evidence_id in references
        if evidence_id in records and evidence_id in verified_ids
    }
    result_mismatch = not expected_results.issubset(observed_results)
    witness = {
        "missing": missing,
        "unverified": unverified,
        "unbound": unbound,
        "expected_results": sorted(expected_results),
        "observed_results": sorted(value for value in observed_results if isinstance(value, str)),
    }
    return not (missing or unverified or unbound or result_mismatch), witness


def audit_gate_product(raw: dict[str, Any], artifact_root: Path | None = None) -> list[Finding]:
    """Audit independent gate coordinates and verified failure propagation."""

    findings: list[Finding] = []
    claim = raw.get("claim")
    admission = raw.get("admission")
    if not isinstance(claim, dict) or not isinstance(admission, dict):
        return [Finding(Severity.ERROR, "GATE_DOCUMENT_TYPE", "$", "claim and admission must be objects")]
    maturity = claim.get("evidence_maturity")
    deployment = claim.get("deployment_status")
    if maturity not in EVIDENCE_MATURITY:
        findings.append(Finding(Severity.ERROR, "EVIDENCE_MATURITY", "claim.evidence_maturity", f"maturity must be one of {sorted(EVIDENCE_MATURITY)}"))
    if deployment not in DEPLOYMENT_STATES:
        findings.append(Finding(Severity.ERROR, "DEPLOYMENT_STATUS", "claim.deployment_status", f"deployment status must be one of {sorted(DEPLOYMENT_STATES)}"))

    hard_values = admission.get("hard_gates", [])
    gate_records = admission.get("gate_results", [])
    if not isinstance(hard_values, list) or not all(isinstance(value, str) for value in hard_values):
        return findings + [Finding(Severity.ERROR, "HARD_GATES_TYPE", "admission.hard_gates", "hard gates must be a list of identifiers")]
    if not isinstance(gate_records, list):
        return findings + [Finding(Severity.ERROR, "GATE_RESULTS_TYPE", "admission.gate_results", "gate results must be a list")]
    declared_hard = set(hard_values)
    records = evidence_index(raw)
    verified_ids = verified_evidence_ids(raw, artifact_root)
    by_id: dict[str, dict[str, Any]] = {}
    verified_results: set[str] = set()
    verified_failures: set[str] = set()
    for index, record in enumerate(gate_records):
        path = f"admission.gate_results.{index}"
        if not isinstance(record, dict):
            findings.append(Finding(Severity.ERROR, "GATE_RECORD_TYPE", path, "gate result must be an object"))
            continue
        gate_id = record.get("id")
        state = record.get("state")
        if not isinstance(gate_id, str) or not gate_id or gate_id in by_id:
            findings.append(Finding(Severity.ERROR, "GATE_ID", f"{path}.id", "gate identifiers must be present and unique"))
            continue
        by_id[gate_id] = record
        if state not in GATE_STATES:
            findings.append(Finding(Severity.ERROR, "GATE_STATE", f"{path}.state", f"state must be one of {sorted(GATE_STATES)}"))
            continue
        if gate_id in declared_hard and record.get("fatal") is not True:
            findings.append(Finding(Severity.ERROR, "HARD_GATE_NOT_FATAL", path, "every declared hard gate must be marked fatal"))
        valid_binding, witness = _bound_evidence_is_valid(gate_id, state, record.get("evidence", []), records, verified_ids)
        if not valid_binding:
            findings.append(
                Finding(
                    Severity.BLOCKED,
                    "GATE_RESULT_UNVERIFIED",
                    path,
                    "gate conclusion is not backed by verified evidence with a matching result and gate binding",
                    witness=witness,
                )
            )
        else:
            verified_results.add(gate_id)
        if state == "conflict":
            findings.append(
                Finding(
                    Severity.BLOCKED,
                    "GATE_CONFLICT",
                    path,
                    "this gate has verified passing and failing evidence; averaging is forbidden",
                    witness=record.get("evidence", []),
                    repair="resolve the conflicting certificates or restrict the claim scope",
                )
            )
        if record.get("fatal") is True and state == "fail" and valid_binding:
            verified_failures.add(gate_id)
            findings.append(
                Finding(
                    Severity.DEMOTION,
                    "FATAL_GATE_FAILED",
                    path,
                    "a verified fatal prospective gate failed",
                    witness={"gate": gate_id, "evidence": record.get("evidence", [])},
                )
            )

    missing = sorted(declared_hard - set(by_id))
    if missing:
        findings.append(Finding(Severity.BLOCKED, "HARD_GATE_RESULTS_MISSING", "admission.gate_results", "declared hard gates lack product-state records", witness=missing))
    if deployment == "admitted":
        unresolved = sorted(
            gate_id
            for gate_id in declared_hard
            if gate_id not in by_id or by_id[gate_id].get("state") != "pass" or gate_id not in verified_results
        )
        if unresolved:
            findings.append(Finding(Severity.BLOCKED, "ADMISSION_WITHOUT_FATAL_PASSES", "claim.deployment_status", "admission requires every hard-gate coordinate to have a verified pass", witness=unresolved))

    findings.extend(_dependency_propagation(raw, verified_failures))
    return findings


def _dependency_propagation(raw: dict[str, Any], failed: set[str]) -> list[Finding]:
    graph = raw.get("dependency_graph", {})
    if not graph:
        return []
    if not isinstance(graph, dict):
        return [Finding(Severity.ERROR, "DEPENDENCY_GRAPH_TYPE", "dependency_graph", "dependency graph must be an object")]
    node_values = graph.get("nodes", [])
    edges = graph.get("edges", [])
    root = graph.get("root")
    if not isinstance(node_values, list) or not all(isinstance(node, str) for node in node_values):
        return [Finding(Severity.ERROR, "DEPENDENCY_NODES_TYPE", "dependency_graph.nodes", "dependency nodes must be a list of identifiers")]
    if len(node_values) != len(set(node_values)):
        return [Finding(Severity.ERROR, "DEPENDENCY_NODE_DUPLICATE", "dependency_graph.nodes", "dependency nodes must be unique")]
    if not isinstance(edges, list):
        return [Finding(Severity.ERROR, "DEPENDENCY_EDGES_TYPE", "dependency_graph.edges", "dependency edges must be a list")]
    nodes = set(node_values)
    if root not in nodes:
        return [Finding(Severity.ERROR, "DEPENDENCY_ROOT", "dependency_graph.root", "dependency root must be a declared node")]
    findings: list[Finding] = []
    indegree: dict[str, int] = {node: 0 for node in nodes}
    forward: dict[str, list[str]] = defaultdict(list)
    for index, edge in enumerate(edges):
        if not isinstance(edge, dict):
            findings.append(Finding(Severity.ERROR, "DEPENDENCY_EDGE_TYPE", f"dependency_graph.edges.{index}", "dependency edge must be an object"))
            continue
        source = edge.get("source")
        target = edge.get("target")
        if source not in nodes or target not in nodes:
            findings.append(Finding(Severity.ERROR, "DEPENDENCY_EDGE", f"dependency_graph.edges.{index}", "dependency edge endpoint is undeclared"))
            continue
        forward[source].append(target)
        indegree[target] += 1
    if any(f.severity == Severity.ERROR for f in findings):
        return findings
    queue = deque(node for node, degree in indegree.items() if degree == 0)
    visited = 0
    while queue:
        node = queue.popleft()
        visited += 1
        for target in forward[node]:
            indegree[target] -= 1
            if indegree[target] == 0:
                queue.append(target)
    if visited != len(nodes):
        findings.append(Finding(Severity.ERROR, "DEPENDENCY_CYCLE", "dependency_graph.edges", "claim dependencies must form an acyclic graph"))
        return findings

    affected: set[str] = set()
    queue = deque(failed & nodes)
    while queue:
        node = queue.popleft()
        for target in forward[node]:
            if target not in affected:
                affected.add(target)
                queue.append(target)
    if root in affected:
        findings.append(Finding(Severity.DEMOTION, "FATAL_DEPENDENCY_PROPAGATION", "dependency_graph.root", "the root claim depends on a verified failed fatal gate", witness={"failed_gates": sorted(failed), "affected_root": root}))
    return findings
