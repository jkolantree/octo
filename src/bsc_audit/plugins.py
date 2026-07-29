from __future__ import annotations

from typing import Any

from .findings import Finding, Severity


TRACE_DIMENSIONS = {"finite", "infinite"}
TRACE_TARGETS = {"exact_prime_power_comb", "finite_truncation", "distributional_prime_increment"}
TRACE_REQUIRED_OBLIGATIONS = frozenset(
    {
        "self_adjointness",
        "trace_class_resolvent",
        "exact_prime_increment",
        "joint_trace_norm_cauchy",
        "atomic_rigidity",
    }
)
DOMAIN_CHECK_FIELDS = {
    "arithmetic_trace": frozenset(
        {
            "model_dimension",
            "target",
            "uses_zero_ordinates",
            "primary_gram_uses_zero_table",
            "counterterm_singular_support",
            "certified_obligations",
            "obligation_evidence",
        }
    ),
    "global_recovery": frozenset(
        {
            "local_nondegenerate",
            "claims_global_recovery",
            "fiber_unique",
            "boundary_complete",
        }
    ),
}


def arithmetic_trace_findings(raw: dict[str, Any]) -> list[Finding]:
    if raw.get("claim", {}).get("family") != "arithmetic_trace":
        return []
    domain_checks = raw.get("domain_checks")
    if not isinstance(domain_checks, dict) or "arithmetic_trace" not in domain_checks:
        return [Finding(Severity.ERROR, "ARITHMETIC_TRACE_CONFIG_MISSING", "domain_checks.arithmetic_trace", "arithmetic-trace claims require a typed domain configuration")]
    config = domain_checks.get("arithmetic_trace")
    if not isinstance(config, dict):
        return [Finding(Severity.ERROR, "ARITHMETIC_TRACE_TYPE", "domain_checks.arithmetic_trace", "arithmetic-trace checks must be an object")]
    findings: list[Finding] = []
    dimension = config.get("model_dimension")
    target = config.get("target")
    if dimension not in TRACE_DIMENSIONS:
        findings.append(Finding(Severity.ERROR, "ARITHMETIC_TRACE_DIMENSION_UNSUPPORTED", "domain_checks.arithmetic_trace.model_dimension", f"model_dimension must be one of {sorted(TRACE_DIMENSIONS)}"))
    if target not in TRACE_TARGETS:
        findings.append(Finding(Severity.ERROR, "ARITHMETIC_TRACE_TARGET_UNSUPPORTED", "domain_checks.arithmetic_trace.target", f"target must be one of {sorted(TRACE_TARGETS)}"))
    for field in ("uses_zero_ordinates", "primary_gram_uses_zero_table"):
        if not isinstance(config.get(field), bool):
            findings.append(Finding(Severity.ERROR, "ARITHMETIC_TRACE_FLAG_TYPE", f"domain_checks.arithmetic_trace.{field}", "arithmetic-trace control flags must be boolean"))
    if any(finding.severity == Severity.ERROR for finding in findings):
        return findings
    if dimension == "finite" and target == "exact_prime_power_comb":
        findings.append(Finding(Severity.DEMOTION, "FINITE_PRIME_COMB_NO_GO", "domain_checks.arithmetic_trace.model_dimension", "a finite analytic exponential sum cannot equal the infinite prime-power delta comb on C_c^infinity", repair="move to an infinite-dimensional distributional trace construction or declare a finite truncation only"))
    if config.get("uses_zero_ordinates"):
        findings.append(Finding(Severity.ERROR, "ZERO_FITTED_OPERATOR", "domain_checks.arithmetic_trace.uses_zero_ordinates", "zeta-zero ordinates may not enter the operator definition"))
    if config.get("primary_gram_uses_zero_table"):
        findings.append(Finding(Severity.ERROR, "GRAM_ZERO_TABLE_LEAKAGE", "domain_checks.arithmetic_trace.primary_gram_uses_zero_table", "zero tables are forbidden in the primary arithmetic Gram calculation"))
    support = config.get("counterterm_singular_support", [])
    if not isinstance(support, list) or not all(isinstance(item, str) for item in support):
        findings.append(Finding(Severity.ERROR, "COUNTERTERM_SUPPORT_TYPE", "domain_checks.arithmetic_trace.counterterm_singular_support", "singular support must be a list of declared support labels"))
        support = []
    counterterm_support = set(support)
    if counterterm_support - {"origin"}:
        findings.append(Finding(Severity.DEMOTION, "COUNTERTERM_RECONSTRUCTS_COMB", "domain_checks.arithmetic_trace.counterterm_singular_support", "off-origin atomic counterterms can reconstruct the forbidden arithmetic comb", witness=sorted(counterterm_support - {"origin"})))
    required = TRACE_REQUIRED_OBLIGATIONS
    obligations = config.get("certified_obligations", [])
    if not isinstance(obligations, list) or not all(isinstance(item, str) for item in obligations):
        findings.append(Finding(Severity.ERROR, "TRACE_OBLIGATIONS_TYPE", "domain_checks.arithmetic_trace.certified_obligations", "certified obligations must be a list of obligation identifiers"))
        obligations = []
    certified = set(obligations)
    unknown_obligations = sorted(certified - required)
    if unknown_obligations:
        findings.append(
            Finding(
                Severity.ERROR,
                "TRACE_OBLIGATION_UNREGISTERED",
                "domain_checks.arithmetic_trace.certified_obligations",
                "certified obligations contain identifiers with no registered replay predicate",
                witness=unknown_obligations,
            )
        )
    missing = sorted(required - certified)
    if dimension == "infinite" and missing:
        findings.append(Finding(Severity.BLOCKED, "TRACE_CONSTRUCTION_INCOMPLETE", "domain_checks.arithmetic_trace.certified_obligations", "infinite-dimensional construction is missing required certificates", witness=missing))
    if dimension == "infinite" and not missing:
        bindings = config.get("obligation_evidence", {})
        if not isinstance(bindings, dict):
            findings.append(Finding(Severity.ERROR, "TRACE_EVIDENCE_BINDING_TYPE", "domain_checks.arithmetic_trace.obligation_evidence", "obligation evidence bindings must be an object"))
        else:
            for obligation in sorted(required):
                ids = bindings.get(obligation, [])
                if not isinstance(ids, list) or not all(
                    isinstance(identifier, str) for identifier in ids
                ):
                    findings.append(
                        Finding(
                            Severity.ERROR,
                            "TRACE_EVIDENCE_BINDING_TYPE",
                            f"domain_checks.arithmetic_trace.obligation_evidence.{obligation}",
                            "obligation evidence bindings must be lists of evidence identifiers",
                        )
                    )
                    continue
                if not ids:
                    findings.append(Finding(Severity.BLOCKED, "TRACE_OBLIGATION_EVIDENCE_MISSING", f"domain_checks.arithmetic_trace.obligation_evidence.{obligation}", "a declared obligation is not bound to evidence with a registered exact replay"))
                    continue
                findings.append(
                    Finding(
                        Severity.BLOCKED,
                        "TRACE_OBLIGATION_EVIDENCE_UNVERIFIED",
                        f"domain_checks.arithmetic_trace.obligation_evidence.{obligation}",
                        "no registered exact arithmetic-trace replay exists; declared bindings, matching hashes, and caller-constructed judgments are non-admissive",
                        witness=ids,
                    )
                )
    return findings


def recovery_findings(raw: dict[str, Any]) -> list[Finding]:
    domain_checks = raw.get("domain_checks", {})
    if not isinstance(domain_checks, dict):
        return [
            Finding(
                Severity.ERROR,
                "DOMAIN_CHECKS_TYPE",
                "domain_checks",
                "domain_checks must be an object when present",
            )
        ]
    config = domain_checks.get("global_recovery")
    if config is None:
        return []
    if not isinstance(config, dict):
        return [Finding(Severity.ERROR, "GLOBAL_RECOVERY_TYPE", "domain_checks.global_recovery", "global-recovery checks must be an object")]
    findings: list[Finding] = []
    for field in sorted(DOMAIN_CHECK_FIELDS["global_recovery"]):
        if field in config and type(config[field]) is not bool:
            findings.append(
                Finding(
                    Severity.ERROR,
                    "GLOBAL_RECOVERY_FLAG_TYPE",
                    f"domain_checks.global_recovery.{field}",
                    "global-recovery control flags must be boolean",
                )
            )
    if findings:
        return findings
    if config.get("claims_global_recovery"):
        missing = [name for name in ("fiber_unique", "boundary_complete") if not config.get(name)]
        if missing:
            findings.append(Finding(Severity.BLOCKED, "LOCAL_GLOBAL_PROMOTION_FAILURE", "domain_checks.global_recovery", "a global-recovery claim requires global fiber and boundary/properness certificates", witness=missing, repair="supply global fiber and boundary/properness certificates"))
    return findings


def run_plugins(raw: dict[str, Any]) -> list[Finding]:
    return arithmetic_trace_findings(raw) + recovery_findings(raw)
