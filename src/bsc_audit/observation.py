from __future__ import annotations

from typing import Any, Hashable, Iterable, Mapping, Sequence

from .findings import Finding, Severity


Pair = tuple[Hashable, Hashable]
MAX_STATES = 10000
MAX_RELATION_PAIRS = 100000
MAX_QUERIES = 10000


def descent_witness(relation: Iterable[Pair], query: Mapping[Hashable, Any]) -> dict[str, Any] | None:
    for left, right in relation:
        if left not in query or right not in query:
            return {"left": left, "right": right, "reason": "query undefined on related state"}
        if query[left] != query[right]:
            return {"left": left, "right": right, "left_value": query[left], "right_value": query[right]}
    return None


def descends(relation: Iterable[Pair], query: Mapping[Hashable, Any]) -> bool:
    return descent_witness(relation, query) is None


def kernel_of_queries(states: Sequence[Hashable], queries: Sequence[Mapping[Hashable, Any]]) -> set[Pair]:
    for query in queries:
        missing = [state for state in states if state not in query]
        if missing:
            raise ValueError(f"queries must be total on the declared states; missing {missing!r}")
    return {
        (left, right)
        for left in states
        for right in states
        if all(query[left] == query[right] for query in queries)
    }


def audit_observation_document(raw: dict[str, Any]) -> list[Finding]:
    findings: list[Finding] = []
    if not isinstance(raw, dict):
        return [Finding(Severity.ERROR, "OBS_DOCUMENT_TYPE", "$", "observation document must be a JSON object")]

    states = raw.get("states")
    if not isinstance(states, list) or not states:
        findings.append(Finding(Severity.ERROR, "OBS_STATES_MISSING", "states", "finite observation audit requires declared states"))
        return findings
    if len(states) > MAX_STATES:
        return [Finding(Severity.ERROR, "OBS_STATES_LIMIT", "states", f"at most {MAX_STATES} states may be audited at once")]

    for index, state in enumerate(states):
        try:
            hash(state)
        except TypeError:
            findings.append(Finding(Severity.ERROR, "OBS_STATE_TYPE", f"states.{index}", "state identifiers must be hashable JSON scalars"))
    if findings:
        return findings
    if len(set(states)) != len(states):
        findings.append(Finding(Severity.ERROR, "OBS_STATE_DUPLICATE", "states", "state identifiers must be unique"))
    state_keys = [state if isinstance(state, str) else str(state) for state in states]
    if len(set(state_keys)) != len(state_keys):
        findings.append(Finding(Severity.ERROR, "OBS_STATE_KEY_COLLISION", "states", "state identifiers collide when used as JSON object keys"))

    relation_raw = raw.get("relation", [])
    if not isinstance(relation_raw, list):
        findings.append(Finding(Severity.ERROR, "OBS_RELATION_TYPE", "relation", "relation must be a list of state pairs"))
        return findings
    if len(relation_raw) > MAX_RELATION_PAIRS:
        return findings + [Finding(Severity.ERROR, "OBS_RELATION_LIMIT", "relation", f"at most {MAX_RELATION_PAIRS} related pairs may be audited at once")]
    relation: list[Pair] = []
    state_set = set(states)
    for index, pair in enumerate(relation_raw):
        path = f"relation.{index}"
        if not isinstance(pair, (list, tuple)) or len(pair) != 2:
            findings.append(Finding(Severity.ERROR, "OBS_RELATION_PAIR", path, "each relation entry must contain exactly two states"))
            continue
        left, right = pair
        try:
            endpoints_known = left in state_set and right in state_set
        except TypeError:
            endpoints_known = False
        if not endpoints_known:
            findings.append(Finding(Severity.ERROR, "OBS_RELATION_ENDPOINT", path, "relation endpoints must be declared state identifiers", witness={"left": left, "right": right}))
            continue
        relation.append((left, right))

    relation_kind = raw.get("relation_kind", "relation")
    require_equivalence = raw.get("require_equivalence", False)
    if relation_kind not in {"relation", "equivalence"}:
        findings.append(Finding(Severity.ERROR, "OBS_RELATION_KIND", "relation_kind", "relation_kind must be 'relation' or 'equivalence'"))
    if not isinstance(require_equivalence, bool):
        findings.append(Finding(Severity.ERROR, "OBS_EQUIVALENCE_FLAG", "require_equivalence", "require_equivalence must be boolean"))
    elif relation_kind == "equivalence" or require_equivalence:
        relation_set = set(relation)
        missing_reflexive = [(state, state) for state in states if (state, state) not in relation_set]
        missing_symmetric = [(left, right) for left, right in relation_set if (right, left) not in relation_set]
        missing_transitive: list[Pair] = []
        successors: dict[Hashable, set[Hashable]] = {}
        for left, right in relation_set:
            successors.setdefault(left, set()).add(right)
        for left, middle in relation_set:
            for right in successors.get(middle, set()):
                if (left, right) not in relation_set:
                    missing_transitive.append((left, right))
                    if len(missing_transitive) >= 10:
                        break
            if len(missing_transitive) >= 10:
                break
        if missing_reflexive or missing_symmetric or missing_transitive:
            findings.append(
                Finding(
                    Severity.ERROR,
                    "OBS_RELATION_NOT_EQUIVALENCE",
                    "relation",
                    "declared equivalence relation is not reflexive, symmetric, and transitive",
                    witness={
                        "missing_reflexive": missing_reflexive[:10],
                        "missing_symmetric": missing_symmetric[:10],
                        "missing_transitive": sorted(set(missing_transitive), key=repr)[:10],
                    },
                )
            )

    queries = raw.get("queries")
    if not isinstance(queries, dict) or not queries:
        findings.append(Finding(Severity.ERROR, "OBS_QUERIES_MISSING", "queries", "finite observation audit requires at least one declared query"))
        return findings
    if len(queries) > MAX_QUERIES:
        return findings + [Finding(Severity.ERROR, "OBS_QUERIES_LIMIT", "queries", f"at most {MAX_QUERIES} queries may be audited at once")]

    parsed_queries: dict[str, dict[Hashable, Any]] = {}
    for name, values in queries.items():
        path = f"queries.{name}"
        if not isinstance(name, str) or not name:
            findings.append(Finding(Severity.ERROR, "OBS_QUERY_NAME", "queries", "query names must be nonempty strings"))
            continue
        if not isinstance(values, dict):
            findings.append(Finding(Severity.ERROR, "OBS_QUERY_TYPE", path, "query values must be a JSON object keyed by state identifier"))
            continue
        query: dict[Hashable, Any] = {}
        missing: list[Hashable] = []
        for state, key in zip(states, state_keys):
            if state in values:
                query[state] = values[state]
            elif key in values:
                query[state] = values[key]
            else:
                missing.append(state)
        if missing:
            findings.append(Finding(Severity.ERROR, "OBS_QUERY_NOT_TOTAL", path, "query must be defined on every declared state", witness={"missing_states": missing}))
            continue
        allowed_keys = set(state_keys) | state_set
        unknown_keys = sorted((key for key in values if key not in allowed_keys), key=repr)
        if unknown_keys:
            findings.append(Finding(Severity.ERROR, "OBS_QUERY_UNKNOWN_STATE", path, "query contains values for undeclared states", witness={"unknown_keys": unknown_keys}))
            continue
        parsed_queries[name] = query

    if any(finding.severity == Severity.ERROR for finding in findings):
        return findings

    for name, query in parsed_queries.items():
        witness = descent_witness(relation, query)
        if witness is None:
            findings.append(Finding(Severity.INFO, "QUERY_DESCENDS", f"queries.{name}", "query is constant on every declared related pair"))
        else:
            findings.append(
                Finding(
                    Severity.BLOCKED,
                    "QUERY_DESCENT_FAILURE",
                    f"queries.{name}",
                    "query distinguishes states that the observation relation identifies",
                    witness,
                    "refine the observation, weaken the query, or retain the kernel-pair groupoid",
                )
            )
    return findings
