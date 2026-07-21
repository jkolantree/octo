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
) -> tuple[bool, str, dict[str, Any]]:
    if not isinstance(references, list) or not all(isinstance(value, str) for value in references):
        return False, "unrun", {"reason": "evidence references must be a list of identifiers"}
    duplicate_references = len(references) != len(set(references))
    bound_ids = {
        evidence_id
        for evidence_id, record in records.items()
        if gate_id in record.get("verifies_gates", [])
    }
    referenced_ids = set(references)
    missing_references = sorted(bound_ids - referenced_ids)
    extraneous_references = sorted(referenced_ids - bound_ids)
    missing_records = sorted(referenced_ids - set(records))
    unverified = sorted(bound_ids - verified_ids)
    observed_results = {
        records[evidence_id].get("result")
        for evidence_id in bound_ids & verified_ids
        if evidence_id in records
    }
    decisive = observed_results & {"pass", "fail"}
    if not decisive:
        computed_state = "unrun"
    elif observed_results == {"pass"}:
        computed_state = "pass"
    elif observed_results == {"fail"}:
        computed_state = "fail"
    else:
        computed_state = "conflict"
    state_mismatch = state != computed_state
    witness = {
        "computed_state": computed_state,
        "bound_evidence": sorted(bound_ids),
        "duplicate_references": duplicate_references,
        "missing_references": missing_references,
        "extraneous_references": extraneous_references,
        "missing_records": missing_records,
        "unverified": unverified,
        "observed_results": sorted(value for value in observed_results if isinstance(value, str)),
        "declared_state": state,
    }
    valid = not (
        duplicate_references
        or missing_references
        or extraneous_references
        or missing_records
        or unverified
        or state_mismatch
    )
    return valid, computed_state, witness


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
    computed_states: dict[str, str] = {}
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
        valid_binding, computed_state, witness = _bound_evidence_is_valid(gate_id, state, record.get("evidence", []), records, verified_ids)
        computed_states[gate_id] = computed_state
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
        if computed_state == "conflict":
            findings.append(
                Finding(
                    Severity.BLOCKED,
                    "GATE_CONFLICT",
                    path,
                    "this gate has incompatible or inconclusive verified evidence; averaging or omission is forbidden",
                    witness=witness,
                    repair="resolve the conflicting certificates or restrict the claim scope",
                )
            )
        if record.get("fatal") is True and computed_state == "fail" and valid_binding:
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
            if gate_id not in by_id or computed_states.get(gate_id) != "pass" or gate_id not in verified_results
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
