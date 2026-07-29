"use strict";

const assert = require("node:assert/strict");
const crypto = require("node:crypto");
const fs = require("node:fs");
const path = require("node:path");
const test = require("node:test");

const ROOT = path.resolve(__dirname, "..");
const desk = require(path.join(ROOT, "pages", "return-desk-core.js"));
const schema = JSON.parse(fs.readFileSync(path.join(ROOT, "schemas", "audit-return-v0.1.schema.json"), "utf8"));
const schemaHash = crypto.createHash("sha256").update(fs.readFileSync(path.join(ROOT, "schemas", "audit-return-v0.1.schema.json"))).digest("hex");
const HASHES = {
  request: `sha256:${"1".repeat(64)}`,
  report: `sha256:${"2".repeat(64)}`,
  source: `sha256:${"3".repeat(64)}`,
  evidence: `sha256:${"4".repeat(64)}`,
  protocol: `sha256:${"a".repeat(64)}`,
};
const SESSION_RUNTIME = "3.12.13 (session-reported test runtime)";

function execution(activity, status) {
  const ran = status === "ran";
  return {
    activity,
    status,
    tool: ran ? "BSC Custom GPT" : null,
    version: ran ? "0.3.0-alpha.11" : null,
    input_artifact_ids: ran ? ["artifact.request", "artifact.source"] : [],
    output_artifact_ids: ran ? ["artifact.report", "artifact.evidence"] : [],
    receipt_ids: [],
    notes: status === "ran" ? "Model reasoning only; no mechanical execution is inferred." : "This activity was not run or relied upon.",
  };
}

function validRecord() {
  return {
    return_version: "0.1.0",
    authority: "non_admissive_return_inspection",
    draft: true,
    protocol: { version: "0.3.0-alpha.11", sha256: HASHES.protocol },
    bindings: { request_artifact_id: "artifact.request", report_artifact_id: "artifact.report" },
    audit_depth: "standard",
    primary_claim_id: "claim.main",
    claims: [{
      id: "claim.main",
      statement: "The supplied finite record is internally consistent under the stated scope.",
      research_verdict: "plausible_but_unresolved",
      depends_on: [],
      source_ids: ["source.target"],
      evidence_ids: ["evidence.analysis"],
      fatal_gate_ids: ["gate.structure"],
    }],
    summary_projection: {
      primary_claim_id: "claim.main",
      research_verdict: "plausible_but_unresolved",
      admission: "pass",
      deployment_status: "research_only",
      fatal_gate_ids: ["gate.structure"],
      unresolved_obligation_ids: [],
    },
    sources: [{
      id: "source.target",
      label: "Target source",
      kind: "document",
      coverage_state: "fully_inspected",
      access_mode: "attachment",
      inspected_scope: ["entire supplied UTF-8 document"],
      omissions: [],
      artifact_id: "artifact.source",
    }],
    artifacts: [
      { id: "artifact.request", filename: "request.txt", role: "request", media_type: "text/plain", sha256: HASHES.request },
      { id: "artifact.report", filename: "report.txt", role: "report", media_type: "text/plain", sha256: HASHES.report },
      { id: "artifact.source", filename: "source.txt", role: "source", media_type: "text/plain", sha256: HASHES.source },
      { id: "artifact.evidence", filename: "evidence.json", role: "evidence", media_type: "application/json", sha256: HASHES.evidence },
    ],
    evidence: [{
      id: "evidence.analysis",
      kind: "argument",
      status: "verified",
      result: "pass",
      claim_ids: ["claim.main"],
      gate_ids: ["gate.structure"],
      artifact_ids: ["artifact.evidence"],
      execution_activities: ["model_reasoning"],
      receipt_ids: [],
    }],
    fatal_gates: [{ id: "gate.structure", state: "pass", evidence_ids: ["evidence.analysis"], obligation_ids: [] }],
    execution: desk.CANONICAL_ACTIVITIES.map((activity) => execution(activity, activity === "model_reasoning" ? "ran" : "not_run")),
    receipts: [],
    unresolved_obligations: [],
  };
}

function artifactBytes(record, artifact) {
  if (artifact.id === record.bindings.report_artifact_id) {
    const outputReferences = record.execution
      .filter((item) => item.status === "ran" && item.activity !== "model_reasoning")
      .flatMap((item) => item.output_artifact_ids)
      .map((artifactId) => record.artifacts.find((item) => item.id === artifactId))
      .filter((item) => item)
      .map((item) => item.filename);
    return Buffer.from(`Audit report.\nExecution details: ${outputReferences.join(", ")}\n`, "utf8");
  }
  if (artifact.id === "artifact.bsc-output") {
    return Buffer.from("tool=bsc-audit\nversion=0.3.0a11\n", "utf8");
  }
  if (artifact.id === "artifact.da-output") {
    const run = record.execution.find((item) => item.activity === "chatgpt_data_analysis");
    const rows = run.output_artifact_ids
      .filter((artifactId) => artifactId !== "artifact.da-output")
      .map((artifactId) => record.artifacts.find((item) => item.id === artifactId))
      .filter((item) => item && !["request", "source"].includes(item.role))
      .map((item) => {
        const bytes = artifactBytes(record, item);
        return {
          filename: item.filename,
          bytes: bytes.byteLength,
          sha256: item.sha256.slice("sha256:".length),
        };
      })
      .sort((left, right) => (
        left.filename < right.filename ? -1 : (left.filename > right.filename ? 1 : 0)
      ));
    return Buffer.from(
      "bsc_chatgpt_data_analysis_output_version: 2\n"
      + `session_reported_runtime=${SESSION_RUNTIME}\n`
      + "runtime_provenance=session_reported\n"
      + "finalized_artifacts:\n"
      + rows.map((row) => `${row.sha256}  ${row.bytes}  ${row.filename}\n`).join(""),
      "utf8",
    );
  }
  if (artifact.filename.toLowerCase().endsWith(".json")) return Buffer.from(`{"artifact_id":${JSON.stringify(artifact.id)}}\n`, "utf8");
  return Buffer.from(`${artifact.id}\tverified\r\n`, "utf8");
}

function options(record, omittedFilename = null) {
  return {
    contract: {
      authority: "non_admissive_return_inspection",
      execution_activities: Array.from(desk.CANONICAL_ACTIVITIES),
      integrity_verified: true,
      schema,
      schema_sha256: schemaHash,
      version: "0.1.0",
    },
    protocol: { version: record.protocol.version, sha256: record.protocol.sha256.slice(7) },
    artifacts: record.artifacts
      .filter((item) => item.filename !== omittedFilename)
      .map((item) => {
        const bytes = artifactBytes(record, item);
        return { name: item.filename, sha256: item.sha256, size: bytes.byteLength, bytes };
      }),
  };
}

function inspect(record, supplied = options(record)) {
  return desk.inspectReturn(`${JSON.stringify(record)}\n`, supplied);
}

function codes(result) {
  return new Set(result.findings.map((item) => item.code));
}

function bindEffectiveBscRun(record) {
  record.artifacts.push(
    { id: "artifact.bsc-output", filename: "bsc-output.txt", role: "execution_output", media_type: "text/plain", sha256: `sha256:${"5".repeat(64)}` },
    { id: "artifact.bsc-receipt", filename: "bsc-receipt.json", role: "receipt", media_type: "application/json", sha256: `sha256:${"6".repeat(64)}` },
  );
  record.receipts.push({
    id: "receipt.bsc",
    authority: "execution_record",
    kind: "bsc_cli_output",
    artifact_id: "artifact.bsc-receipt",
    claim_ids: ["claim.main"],
    gate_ids: ["gate.structure"],
    status: "verified",
  });
  const run = record.execution.find((item) => item.activity === "bsc_python_checker");
  Object.assign(run, {
    status: "ran",
    tool: "bsc-audit",
    version: "0.3.0a11",
    input_artifact_ids: ["artifact.request", "artifact.source"],
    output_artifact_ids: ["artifact.bsc-output"],
    receipt_ids: ["receipt.bsc"],
    notes: "Bound positive control for execution-to-evidence linkage.",
  });
}

function bindDataAnalysisRun(record) {
  record.artifacts.push({
    id: "artifact.da-output",
    filename: "chatgpt_data_analysis_output.txt",
    role: "execution_output",
    media_type: "text/plain",
    sha256: `sha256:${"7".repeat(64)}`,
  });
  const run = record.execution.find((item) => item.activity === "chatgpt_data_analysis");
  Object.assign(run, {
    status: "ran",
    tool: "Python",
    version: SESSION_RUNTIME,
    input_artifact_ids: ["artifact.request", "artifact.source"],
    output_artifact_ids: ["artifact.da-output"],
    receipt_ids: [],
    notes: "The runtime is session-reported, not independently authenticated.",
  });
}

test("strict parser rejects duplicate keys and non-object input", () => {
  assert.throws(() => desk.parseStrictJson('{"a":1,"a":2}'), /duplicate JSON object key/);
  assert.throws(() => desk.parseStrictJson("[]"), /top-level JSON value must be an object/);
  assert.throws(() => desk.parseStrictJson('{"x":"\\ud800"}'), /unpaired JSON unicode surrogate/);
  assert.throws(() => desk.parseStrictJson('{"\\udc00":1}'), /unpaired JSON unicode surrogate/);
});

test("non-JSON BOM and Unicode padding cannot be trimmed into validity", () => {
  const source = JSON.stringify(validRecord());
  for (const padded of [`\ufeff${source}`, `${source}\u00a0`]) {
    const result = desk.inspectReturn(padded, options(validRecord()));
    assert.equal(result.outcome, "blocked");
    assert.ok(codes(result).has("RETURN_JSON_MALFORMED"));
  }
  for (const padded of [`\ufeff${source}`, `\u00a0${source}`]) {
    const result = desk.inspectReturn(`\`\`\`json\n${padded}\n\`\`\``, options(validRecord()));
    assert.equal(result.outcome, "blocked");
    assert.ok(codes(result).has("RETURN_JSON_MALFORMED"));
  }
});

test("prose without one versioned envelope remains needs_review", () => {
  const result = desk.inspectReturn("This fluent report has no structured return.", options(validRecord()));
  assert.equal(result.outcome, "needs_review");
  assert.ok(codes(result).has("RETURN_ENVELOPE_MISSING"));
});

test("multiple fenced objects remain ambiguous when a key uses a JSON escape", () => {
  const record = validRecord();
  const literal = JSON.stringify(record);
  const escaped = literal.replace('"return_version"', '"\\u0072eturn_version"');
  const result = desk.inspectReturn(`first\n\`\`\`json\n${literal}\n\`\`\`\nsecond\n\`\`\`json\n${escaped}\n\`\`\``, options(record));
  assert.equal(result.outcome, "blocked");
  assert.ok(codes(result).has("RETURN_ENVELOPE_AMBIGUOUS"));
});

test("oversized UTF-8 return source is blocked before parsing", () => {
  const source = "é".repeat(Math.floor(desk.MAX_RETURN_JSON_BYTES / 2) + 1);
  const result = desk.inspectReturn(source, options(validRecord()));
  assert.equal(result.outcome, "blocked");
  assert.ok(codes(result).has("RETURN_JSON_TOO_LARGE"));
  assert.ok(!result.checks.run.includes("strict_json_parse"));
  assert.throws(() => desk.parseStrictJson(source), desk.StrictJsonError);
});

test("unverified or malformed embedded contracts fail closed", () => {
  const record = validRecord();
  const unverified = options(record);
  unverified.contract.integrity_verified = false;
  assert.equal(inspect(record, unverified).outcome, "blocked");
  assert.ok(codes(inspect(record, unverified)).has("RETURN_CONTRACT_UNAVAILABLE"));

  const permissive = options(record);
  permissive.contract.schema = true;
  assert.equal(inspect(record, permissive).outcome, "blocked");
  assert.ok(codes(inspect(record, permissive)).has("RETURN_CONTRACT_UNAVAILABLE"));

  const wrongHash = options(record);
  wrongHash.contract.schema_sha256 = "0".repeat(64);
  assert.equal(inspect(record, wrongHash).outcome, "blocked");
  assert.ok(codes(inspect(record, wrongHash)).has("RETURN_CONTRACT_UNAVAILABLE"));

  const wrongIdentity = options(record);
  wrongIdentity.contract.schema = { ...schema, $id: "urn:wrong" };
  assert.equal(inspect(record, wrongIdentity).outcome, "blocked");
  assert.ok(codes(inspect(record, wrongIdentity)).has("RETURN_CONTRACT_UNAVAILABLE"));
});

test("schema equality keeps booleans distinct from numbers", () => {
  const record = validRecord();
  record.draft = 1;
  const result = inspect(record);
  assert.equal(result.outcome, "blocked");
  assert.ok(codes(result).has("RETURN_SCHEMA_INVALID"));
});

test("schema identifiers require the absolute end of the string", () => {
  const record = validRecord();
  record.claims[0].id = "claim.main\n";
  record.primary_claim_id = "claim.main\n";
  record.summary_projection.primary_claim_id = "claim.main\n";
  record.evidence[0].claim_ids = ["claim.main\n"];
  const result = inspect(record);
  assert.equal(result.outcome, "blocked");
  assert.ok(codes(result).has("RETURN_SCHEMA_INVALID"));
});

test("schema string lengths count Unicode code points", () => {
  const atLimit = validRecord();
  atLimit.claims[0].statement = "\u{1f600}".repeat(16384);
  assert.equal(inspect(atLimit).outcome, "consistent");

  const overLimit = validRecord();
  overLimit.claims[0].statement = "\u{1f600}".repeat(16385);
  const result = inspect(overLimit);
  assert.equal(result.outcome, "blocked");
  assert.ok(codes(result).has("RETURN_SCHEMA_INVALID"));
});

test("complete valid return is internally consistent and deterministic", () => {
  const record = validRecord();
  const first = inspect(record);
  const second = inspect(record);
  assert.deepEqual(first, second);
  assert.equal(first.outcome, "consistent");
  assert.ok(codes(first).has("RETURN_INTERNALLY_CONSISTENT"));
  assert.match(first.caveat, /not truth, proof, admissibility/);
  assert.equal(Object.prototype.hasOwnProperty.call(first, "timestamp"), false);
});

test("summary strengthening and omitted bound evidence block", () => {
  const strengthened = validRecord();
  strengthened.summary_projection.research_verdict = "proven";
  const summaryResult = inspect(strengthened);
  assert.equal(summaryResult.outcome, "blocked");
  assert.ok(codes(summaryResult).has("RETURN_SUMMARY_VERDICT_MISMATCH"));

  const omitted = validRecord();
  omitted.fatal_gates[0].evidence_ids = [];
  const omittedResult = inspect(omitted);
  assert.equal(omittedResult.outcome, "blocked");
  assert.ok(codes(omittedResult).has("RETURN_GATE_EVIDENCE_ASYMMETRIC"));
});

test("missing request bytes need review while a hash mismatch blocks", () => {
  const missing = validRecord();
  const missingResult = inspect(missing, options(missing, "request.txt"));
  assert.equal(missingResult.outcome, "needs_review");
  assert.ok(codes(missingResult).has("RETURN_ARTIFACT_UNAVAILABLE"));

  const mismatch = validRecord();
  const supplied = options(mismatch);
  supplied.artifacts.find((item) => item.name === "request.txt").sha256 = `sha256:${"f".repeat(64)}`;
  const mismatchResult = inspect(mismatch, supplied);
  assert.equal(mismatchResult.outcome, "blocked");
  assert.ok(codes(mismatchResult).has("RETURN_ARTIFACT_HASH_MISMATCH"));
});

test("hash-verified text artifacts require strict UTF-8 and portable controls", () => {
  const invalidUtf8 = validRecord();
  const invalidUtf8Options = options(invalidUtf8);
  invalidUtf8Options.artifacts.find((item) => item.name === "report.txt").bytes = Buffer.from([0xc3, 0x28]);
  const encodingResult = inspect(invalidUtf8, invalidUtf8Options);
  assert.equal(encodingResult.outcome, "blocked");
  assert.ok(codes(encodingResult).has("RETURN_ARTIFACT_TEXT_ENCODING_INVALID"));

  const invalidControl = validRecord();
  const invalidControlOptions = options(invalidControl);
  invalidControlOptions.artifacts.find((item) => item.name === "evidence.json").bytes = Buffer.from('{"value":"before"}\f{"value":"after"}\n', "utf8");
  const controlResult = inspect(invalidControl, invalidControlOptions);
  assert.equal(controlResult.outcome, "blocked");
  assert.ok(codes(controlResult).has("RETURN_ARTIFACT_TEXT_CONTROL_INVALID"));

  const allowedControls = validRecord();
  const allowedOptions = options(allowedControls);
  allowedOptions.artifacts.find((item) => item.name === "report.txt").bytes = Buffer.from("heading\tvalue\r\nnext line\n", "utf8");
  assert.equal(inspect(allowedControls, allowedOptions).outcome, "consistent");
});

test("file-only access cannot support verified evidence", () => {
  const record = validRecord();
  record.evidence[0].execution_activities = ["chatgpt_data_analysis"];
  record.execution.find((item) => item.activity === "chatgpt_data_analysis").status = "file_read_only";
  const result = inspect(record);
  assert.equal(result.outcome, "blocked");
  assert.ok(codes(result).has("RETURN_FILE_READ_PROMOTION"));
});

test("receipt-only evidence cannot promote a claim to proven", () => {
  const record = validRecord();
  record.claims[0].research_verdict = "proven";
  record.summary_projection.research_verdict = "proven";
  record.artifacts.find((item) => item.id === "artifact.evidence").role = "receipt";
  const result = inspect(record);
  assert.equal(result.outcome, "blocked");
  assert.ok(codes(result).has("RETURN_RECEIPT_ONLY_PROOF"));
});

test("verified evidence needs a bound checking activity", () => {
  const record = validRecord();
  record.evidence[0].execution_activities = [];
  const result = inspect(record);
  assert.equal(result.outcome, "blocked");
  assert.ok(codes(result).has("RETURN_GATE_STATE_MISMATCH"));
  assert.ok(codes(result).has("RETURN_EVIDENCE_UNVERIFIED_LOCALLY"));
});

test("ineffective receipt-only nonpassing evidence remains review-needed", () => {
  for (const evidenceResult of ["fail", "inconclusive"]) {
    const record = validRecord();
    record.artifacts.find((item) => item.id === "artifact.evidence").role = "receipt";
    record.evidence[0].result = evidenceResult;
    record.fatal_gates[0].state = "unrun";
    record.fatal_gates[0].obligation_ids = ["obligation.review"];
    record.summary_projection.admission = "unrun";
    record.summary_projection.unresolved_obligation_ids = ["obligation.review"];
    record.unresolved_obligations = [{
      id: "obligation.review",
      statement: "Verify the evidence with a substantive, locally bound artifact.",
      claim_ids: ["claim.main"],
      gate_ids: ["gate.structure"],
      evidence_ids: ["evidence.analysis"],
    }];
    const result = inspect(record);
    assert.equal(result.outcome, "needs_review", evidenceResult);
    assert.ok(codes(result).has("RETURN_EVIDENCE_UNVERIFIED_LOCALLY"), evidenceResult);
  }
});

test("globally valid but unrelated execution cannot support evidence", () => {
  const record = validRecord();
  bindEffectiveBscRun(record);
  record.evidence[0].execution_activities = ["bsc_python_checker"];
  const result = inspect(record);
  assert.equal(result.outcome, "blocked");
  assert.ok(codes(result).has("RETURN_EVIDENCE_EXECUTION_BINDING_MISMATCH"));
});

test("every evidence-role artifact must be an output of a cited execution", () => {
  const record = validRecord();
  record.artifacts.push({
    id: "artifact.additional-evidence",
    filename: "additional-evidence.json",
    role: "evidence",
    media_type: "application/json",
    sha256: `sha256:${"7".repeat(64)}`,
  });
  record.evidence[0].artifact_ids.push("artifact.additional-evidence");
  const result = inspect(record);
  assert.equal(result.outcome, "blocked");
  assert.ok(codes(result).has("RETURN_EVIDENCE_SUPPORT_OUTPUT_MISMATCH"));

  const unverified = structuredClone(record);
  Object.assign(unverified.evidence[0], { status: "unverified", result: "inconclusive" });
  Object.assign(unverified.fatal_gates[0], {
    state: "unrun",
    obligation_ids: ["obligation.verify-output"],
  });
  unverified.unresolved_obligations = [{
    id: "obligation.verify-output",
    statement: "Verify that every support artifact came from the cited execution.",
    claim_ids: ["claim.main"],
    gate_ids: ["gate.structure"],
    evidence_ids: ["evidence.analysis"],
  }];
  Object.assign(unverified.summary_projection, {
    admission: "unrun",
    unresolved_obligation_ids: ["obligation.verify-output"],
  });
  const unverifiedResult = inspect(unverified);
  assert.equal(unverifiedResult.outcome, "needs_review");
  assert.ok(!codes(unverifiedResult).has("RETURN_EVIDENCE_SUPPORT_OUTPUT_MISMATCH"));
});

test("critical execution needs exact evidence, receipt, and scope bindings", () => {
  const record = validRecord();
  bindEffectiveBscRun(record);
  Object.assign(record.evidence[0], {
    artifact_ids: ["artifact.bsc-output", "artifact.bsc-receipt"],
    execution_activities: ["bsc_python_checker"],
    receipt_ids: ["receipt.bsc"],
  });
  const positive = inspect(record);
  assert.equal(positive.outcome, "consistent", JSON.stringify(positive.findings));

  const wrongInput = structuredClone(record);
  wrongInput.execution.find((item) => item.activity === "bsc_python_checker").input_artifact_ids = ["artifact.request"];
  const inputResult = inspect(wrongInput);
  assert.equal(inputResult.outcome, "blocked");
  assert.ok(codes(inputResult).has("RETURN_EVIDENCE_EXECUTION_INPUT_UNBOUND"));

  record.receipts[0].claim_ids = [];
  const mismatched = inspect(record);
  assert.equal(mismatched.outcome, "blocked");
  assert.ok(codes(mismatched).has("RETURN_RECEIPT_SCOPE_MISMATCH"));
});

test("critical canonical activities cannot hide behind not_applicable", () => {
  for (const activity of ["bsc_python_checker", "external_proof_tool", "empirical_test"]) {
    const record = validRecord();
    record.execution.find((item) => item.activity === activity).status = "not_applicable";
    const result = inspect(record);
    assert.equal(result.outcome, "blocked", activity);
    assert.ok(codes(result).has("RETURN_EXECUTION_NOT_APPLICABLE_MISUSED"), activity);
  }

  const proposed = validRecord();
  proposed.execution.find((item) => item.activity === "proposed_computation").status = "not_applicable";
  assert.equal(inspect(proposed).outcome, "consistent");
});

test("ran non-model execution versions bind once in an output that the report references", () => {
  const record = validRecord();
  bindEffectiveBscRun(record);
  const positive = options(record);
  const reportBytes = positive.artifacts.find((item) => item.name === "report.txt").bytes;
  assert.equal(reportBytes.includes(Buffer.from("0.3.0a11", "utf8")), false);
  assert.equal(inspect(record, positive).outcome, "consistent");

  const unboundVersion = options(record);
  unboundVersion.artifacts.find((item) => item.name === "bsc-output.txt").bytes = Buffer.from("tool=bsc-audit\nversion=0.3.0a7\n", "utf8");
  const unboundVersionResult = inspect(record, unboundVersion);
  assert.equal(unboundVersionResult.outcome, "blocked");
  assert.ok(codes(unboundVersionResult).has("RETURN_EXECUTION_VERSION_UNBOUND"));

  const unreferencedOutput = options(record);
  unreferencedOutput.artifacts.find((item) => item.name === "report.txt").bytes = Buffer.from("Audit report without an execution-output reference.\n", "utf8");
  const unreferencedOutputResult = inspect(record, unreferencedOutput);
  assert.equal(unreferencedOutputResult.outcome, "blocked");
  assert.ok(codes(unreferencedOutputResult).has("RETURN_EXECUTION_OUTPUT_NOT_REFERENCED"));
});

test("Data Analysis runtime uses one session-reported output binding", () => {
  const record = validRecord();
  bindDataAnalysisRun(record);
  const positive = options(record);
  const reportBytes = positive.artifacts.find((item) => item.name === "report.txt").bytes;
  assert.equal(reportBytes.includes(Buffer.from(SESSION_RUNTIME, "utf8")), false);
  assert.equal(inspect(record, positive).outcome, "consistent");

  const rowBound = structuredClone(record);
  rowBound.execution.find(
    (item) => item.activity === "chatgpt_data_analysis",
  ).output_artifact_ids = ["artifact.report", "artifact.da-output"];
  const rowBoundOptions = options(rowBound);
  assert.equal(inspect(rowBound, rowBoundOptions).outcome, "consistent");
  for (const [pattern, replacement] of [
    [/  \d+  report\.txt\n/, "  999999  report.txt\n"],
    ["  report.txt\n", "  forged-name.md\n"],
  ]) {
    const malformed = options(rowBound);
    const output = malformed.artifacts.find(
      (item) => item.name === "chatgpt_data_analysis_output.txt",
    );
    output.bytes = Buffer.from(
      output.bytes.toString("utf8").replace(pattern, replacement),
      "utf8",
    );
    const result = inspect(rowBound, malformed);
    assert.equal(result.outcome, "blocked");
    assert.ok(codes(result).has("RETURN_DATA_ANALYSIS_RUNTIME_BINDING_INVALID"));
  }

  const badProvenance = options(record);
  badProvenance.artifacts.find(
    (item) => item.name === "chatgpt_data_analysis_output.txt",
  ).bytes = Buffer.from(
    "bsc_chatgpt_data_analysis_output_version: 2\n"
    + `session_reported_runtime=${SESSION_RUNTIME}\n`
    + "runtime_provenance=independently_authenticated\n"
    + "finalized_artifacts:\n",
    "utf8",
  );
  const badProvenanceResult = inspect(record, badProvenance);
  assert.equal(badProvenanceResult.outcome, "blocked");
  assert.ok(
    codes(badProvenanceResult).has(
      "RETURN_DATA_ANALYSIS_RUNTIME_BINDING_INVALID",
    ),
  );

  for (const badBytes of [
    Buffer.from(
      "bsc_chatgpt_data_analysis_output_version: 2\n"
      + `session_reported_runtime=${SESSION_RUNTIME}\n`
      + "runtime_provenance=session_reported\n"
      + "finalized_artifacts:\n"
      + `session_reported_runtime=${SESSION_RUNTIME}\n`,
      "utf8",
    ),
    Buffer.from(
      "bsc_chatgpt_data_analysis_output_version: 2\n"
      + `session_reported_runtime=${SESSION_RUNTIME} suffix\n`
      + "runtime_provenance=session_reported\n"
      + "finalized_artifacts:\n",
      "utf8",
    ),
    Buffer.from(
      "bsc_chatgpt_data_analysis_output_version: 2\n"
      + `session_reported_runtime=${SESSION_RUNTIME}\n`
      + "runtime_provenance=session_reported\n"
      + "finalized_artifacts:\n"
      + "runtime_provenance=independently_authenticated\n",
      "utf8",
    ),
    Buffer.from(
      "bsc_chatgpt_data_analysis_output_version: 2\n"
      + `session_reported_runtime=${SESSION_RUNTIME}\n`
      + "runtime_provenance=session_reported\n"
      + "finalized_artifacts:\n"
      + "0f4b6688f8f47f050bad1a1205a3adf1eb19f99841981a03f1f0bfe1ad1f3831  999999  forged-name.md\n",
      "utf8",
    ),
  ]) {
    const malformed = options(record);
    malformed.artifacts.find(
      (item) => item.name === "chatgpt_data_analysis_output.txt",
    ).bytes = badBytes;
    const result = inspect(record, malformed);
    assert.equal(result.outcome, "blocked");
    assert.ok(codes(result).has("RETURN_DATA_ANALYSIS_RUNTIME_BINDING_INVALID"));
  }
});

test("receipt bytes and receipt IDs cannot be relabeled across records or activities", () => {
  const duplicateArtifact = validRecord();
  bindEffectiveBscRun(duplicateArtifact);
  duplicateArtifact.receipts.push({ ...duplicateArtifact.receipts[0], id: "receipt.copy" });
  const duplicateResult = inspect(duplicateArtifact);
  assert.equal(duplicateResult.outcome, "blocked");
  assert.ok(codes(duplicateResult).has("RETURN_RECEIPT_ARTIFACT_REUSED"));

  const reusedReceipt = validRecord();
  bindEffectiveBscRun(reusedReceipt);
  const external = reusedReceipt.execution.find((item) => item.activity === "external_proof_tool");
  Object.assign(external, {
    status: "ran",
    tool: "external-tool",
    version: "1",
    input_artifact_ids: ["artifact.request"],
    output_artifact_ids: ["artifact.bsc-output"],
    receipt_ids: ["receipt.bsc"],
  });
  const reuseResult = inspect(reusedReceipt);
  assert.equal(reuseResult.outcome, "blocked");
  assert.ok(codes(reuseResult).has("RETURN_EXECUTION_RECEIPT_REUSED"));
});

test("request, report, and other artifacts cannot be relabeled as evidence", () => {
  for (const [artifactId, replacementRole] of [["artifact.request", null], ["artifact.report", null], ["artifact.evidence", "other"]]) {
    const record = validRecord();
    if (replacementRole) record.artifacts.find((item) => item.id === artifactId).role = replacementRole;
    record.evidence[0].artifact_ids = [artifactId];
    const result = inspect(record);
    assert.equal(result.outcome, "blocked");
    assert.ok(codes(result).has("RETURN_EVIDENCE_ARTIFACT_ROLE_INVALID"));
  }
});

test("artifact bytes cannot be redeclared to launder roles", () => {
  const record = validRecord();
  record.claims[0].research_verdict = "proven";
  record.summary_projection.research_verdict = "proven";
  const request = record.artifacts.find((item) => item.role === "request");
  const evidence = record.artifacts.find((item) => item.role === "evidence");
  evidence.sha256 = request.sha256;
  const result = inspect(record);
  assert.equal(result.outcome, "blocked");
  assert.ok(codes(result).has("RETURN_ARTIFACT_HASH_ALIAS"));
});

test("high research verdicts require local source bytes and direct support", () => {
  const proven = validRecord();
  proven.claims[0].research_verdict = "proven";
  proven.summary_projection.research_verdict = "proven";
  const missingSource = inspect(proven, options(proven, "source.txt"));
  assert.equal(missingSource.outcome, "blocked");
  assert.ok(codes(missingSource).has("RETURN_PROVEN_SOURCE_BYTES_UNVERIFIED"));

  const strong = validRecord();
  strong.claims[0].research_verdict = "strongly_supported";
  strong.claims[0].source_ids = [];
  strong.claims[0].evidence_ids = [];
  strong.evidence[0].claim_ids = [];
  strong.summary_projection.research_verdict = "strongly_supported";
  const unsupported = inspect(strong);
  assert.equal(unsupported.outcome, "blocked");
  assert.ok(codes(unsupported).has("RETURN_STRONGLY_SUPPORTED_WITH_SOURCE_GAP"));
  assert.ok(codes(unsupported).has("RETURN_STRONGLY_SUPPORTED_WITHOUT_EVIDENCE"));

  const dependency = validRecord();
  Object.assign(dependency.claims[0], {
    research_verdict: "strongly_supported",
    depends_on: ["claim.unsupported-dependency"],
  });
  dependency.claims.push({
    id: "claim.unsupported-dependency",
    statement: "A required dependency remains unresolved.",
    research_verdict: "plausible_but_unresolved",
    depends_on: [],
    source_ids: [],
    evidence_ids: [],
    fatal_gate_ids: [],
  });
  dependency.summary_projection.research_verdict = "strongly_supported";
  const dependencyResult = inspect(dependency);
  assert.equal(dependencyResult.outcome, "blocked");
  assert.ok(codes(dependencyResult).has("RETURN_STRONGLY_SUPPORTED_DEPENDENCY_UNCLOSED"));
});

test("high verdicts cannot ignore direct effective nonpassing evidence", () => {
  for (const verdict of ["proven", "strongly_supported"]) {
    for (const evidenceResult of ["fail", "inconclusive"]) {
      const record = validRecord();
      record.claims[0].research_verdict = verdict;
      record.summary_projection.research_verdict = verdict;
      const contrary = structuredClone(record.evidence[0]);
      Object.assign(contrary, { id: `evidence.${evidenceResult}`, result: evidenceResult, gate_ids: [] });
      record.evidence.push(contrary);
      record.claims[0].evidence_ids.push(contrary.id);
      const result = inspect(record);
      assert.equal(result.outcome, "blocked");
      assert.ok(codes(result).has("RETURN_HIGH_VERDICT_EVIDENCE_CONFLICT"));
    }
  }
});

test("gate evidence cannot float free of the claims that own the gate", () => {
  const record = validRecord();
  record.claims[0].evidence_ids = [];
  record.evidence[0].claim_ids = [];
  const result = inspect(record);
  assert.equal(result.outcome, "blocked");
  assert.ok(codes(result).has("RETURN_GATE_CLAIM_SCOPE_MISMATCH"));
});

test("primary claim and every gate require explicit ownership", () => {
  const record = validRecord();
  record.claims[0].fatal_gate_ids = [];
  record.evidence[0].claim_ids = [];
  const result = inspect(record);
  assert.equal(result.outcome, "blocked");
  assert.ok(codes(result).has("RETURN_PRIMARY_CLAIM_GATE_MISSING"));
  assert.ok(codes(result).has("RETURN_GATE_OWNER_MISSING"));
});

test("effective decisive and inconclusive evidence preserve conflict", () => {
  const record = validRecord();
  const mixed = structuredClone(record.evidence[0]);
  mixed.id = "evidence.inconclusive";
  mixed.result = "inconclusive";
  record.evidence.push(mixed);
  record.claims[0].evidence_ids.push(mixed.id);
  Object.assign(record.fatal_gates[0], {
    state: "conflict",
    evidence_ids: ["evidence.analysis", mixed.id],
    obligation_ids: ["obligation.resolve-conflict"],
  });
  record.unresolved_obligations = [{
    id: "obligation.resolve-conflict",
    statement: "Resolve the incompatible decisive and inconclusive bound records.",
    claim_ids: ["claim.main"],
    gate_ids: ["gate.structure"],
    evidence_ids: ["evidence.analysis", mixed.id],
  }];
  Object.assign(record.summary_projection, {
    admission: "conflict",
    unresolved_obligation_ids: ["obligation.resolve-conflict"],
  });
  const result = inspect(record);
  assert.equal(result.outcome, "consistent", JSON.stringify(result.findings));
  assert.ok(!codes(result).has("RETURN_GATE_STATE_MISMATCH"));
  assert.ok(codes(result).has("RETURN_INTERNALLY_CONSISTENT"));
});

test("honest unverified evidence remains review-needed", () => {
  const record = validRecord();
  Object.assign(record.evidence[0], { status: "unverified", result: "inconclusive" });
  Object.assign(record.fatal_gates[0], {
    state: "unrun",
    obligation_ids: ["obligation.replay"],
  });
  record.unresolved_obligations = [{
    id: "obligation.replay",
    statement: "Independently replay the structural check against the bound source.",
    claim_ids: ["claim.main"],
    gate_ids: ["gate.structure"],
    evidence_ids: ["evidence.analysis"],
  }];
  Object.assign(record.summary_projection, {
    admission: "unrun",
    unresolved_obligation_ids: ["obligation.replay"],
  });
  const result = inspect(record);
  assert.equal(result.outcome, "needs_review", JSON.stringify(result.findings));
  assert.ok(codes(result).has("RETURN_EVIDENCE_UNVERIFIED"));
  assert.ok(codes(result).has("RETURN_INTERNALLY_CONSISTENT"));
});

test("unresolved obligations keep coherent claim, gate, and optional evidence scope", () => {
  function obligationRecord(evidenceIds = []) {
    const record = validRecord();
    Object.assign(record.evidence[0], { status: "unverified", result: "inconclusive" });
    Object.assign(record.fatal_gates[0], {
      state: "unrun",
      obligation_ids: ["obligation.replay"],
    });
    record.unresolved_obligations = [{
      id: "obligation.replay",
      statement: "Replay the unresolved structural check.",
      claim_ids: ["claim.main"],
      gate_ids: ["gate.structure"],
      evidence_ids: evidenceIds,
    }];
    Object.assign(record.summary_projection, {
      admission: "unrun",
      unresolved_obligation_ids: ["obligation.replay"],
    });
    return record;
  }

  const missingEvidence = obligationRecord();
  const missingEvidenceResult = inspect(missingEvidence);
  assert.equal(missingEvidenceResult.outcome, "needs_review");
  assert.ok(!codes(missingEvidenceResult).has("RETURN_OBLIGATION_SCOPE_MISMATCH"));

  const emptyScope = obligationRecord();
  Object.assign(emptyScope.unresolved_obligations[0], { claim_ids: [], gate_ids: [] });
  const emptyScopeResult = inspect(emptyScope);
  assert.equal(emptyScopeResult.outcome, "blocked");
  assert.ok(codes(emptyScopeResult).has("RETURN_OBLIGATION_SCOPE_MISMATCH"));

  const unownedGate = obligationRecord();
  unownedGate.claims[0].fatal_gate_ids = [];
  const unownedResult = inspect(unownedGate);
  assert.equal(unownedResult.outcome, "blocked");
  assert.ok(codes(unownedResult).has("RETURN_OBLIGATION_SCOPE_MISMATCH"));

  const disjointEvidence = obligationRecord(["evidence.analysis"]);
  disjointEvidence.evidence[0].claim_ids = [];
  disjointEvidence.evidence[0].gate_ids = [];
  const disjointResult = inspect(disjointEvidence);
  assert.equal(disjointResult.outcome, "blocked");
  assert.ok(codes(disjointResult).has("RETURN_OBLIGATION_SCOPE_MISMATCH"));
});

test("gate obligation cardinality is fail closed", () => {
  const nonpassing = validRecord();
  nonpassing.claims[0].research_verdict = "refuted";
  nonpassing.evidence[0].result = "fail";
  nonpassing.fatal_gates[0].state = "fail";
  Object.assign(nonpassing.summary_projection, {
    research_verdict: "refuted",
    admission: "fail",
  });
  const nonpassingResult = inspect(nonpassing);
  assert.equal(nonpassingResult.outcome, "blocked");
  assert.ok(
    codes(nonpassingResult).has("RETURN_UNRESOLVED_GATE_OBLIGATION_OMITTED"),
  );

  const passing = validRecord();
  passing.fatal_gates[0].obligation_ids = ["obligation.unnecessarily-open"];
  passing.unresolved_obligations = [{
    id: "obligation.unnecessarily-open",
    statement: "This obligation cannot remain behind a passing gate.",
    claim_ids: ["claim.main"],
    gate_ids: ["gate.structure"],
    evidence_ids: ["evidence.analysis"],
  }];
  passing.summary_projection.unresolved_obligation_ids = [
    "obligation.unnecessarily-open",
  ];
  const passingResult = inspect(passing);
  assert.equal(passingResult.outcome, "blocked");
  assert.ok(
    codes(passingResult).has("RETURN_PASSED_GATE_HAS_OPEN_OBLIGATION"),
  );
});

test("required human-semantic strings cannot be blank", () => {
  const cases = [];
  const claim = validRecord();
  claim.claims[0].statement = " \t";
  cases.push(["claim statement", claim]);
  const label = validRecord();
  label.sources[0].label = " \t";
  cases.push(["source label", label]);
  const scope = validRecord();
  scope.sources[0].inspected_scope = [" \t"];
  cases.push(["inspected scope", scope]);
  const omissions = validRecord();
  Object.assign(omissions.sources[0], { coverage_state: "partially_inspected", omissions: [" \t"] });
  cases.push(["omission", omissions]);
  const mediaType = validRecord();
  mediaType.artifacts[0].media_type = " \t";
  cases.push(["media type", mediaType]);
  const notes = validRecord();
  notes.execution[0].notes = " \t";
  cases.push(["execution notes", notes]);
  for (const [field, record] of cases) {
    const result = inspect(record);
    assert.equal(result.outcome, "blocked", field);
    assert.ok(codes(result).has("RETURN_SCHEMA_INVALID"), field);
  }

  for (const invisible of ["\u200b", "\ufeff"]) {
    const record = validRecord();
    record.claims[0].statement = invisible;
    const result = inspect(record);
    assert.equal(result.outcome, "blocked");
    assert.ok(codes(result).has("RETURN_SEMANTIC_TEXT_INVISIBLE"));
  }
});

test("broken references return structured blocking findings instead of throwing", () => {
  const missingActivity = validRecord();
  missingActivity.execution.find((item) => item.activity === "chatgpt_data_analysis").activity = "web_research";
  missingActivity.evidence[0].execution_activities = ["chatgpt_data_analysis"];
  const activityResult = inspect(missingActivity);
  assert.equal(activityResult.outcome, "blocked");

  const missingSource = validRecord();
  missingSource.claims[0].research_verdict = "proven";
  missingSource.summary_projection.research_verdict = "proven";
  missingSource.claims[0].source_ids = ["source.missing"];
  const sourceResult = inspect(missingSource);
  assert.equal(sourceResult.outcome, "blocked");
  assert.ok(codes(sourceResult).has("RETURN_REFERENCE_MISSING"));
});

test("portable filenames, nonblank tools, and undeclared attachments are fail closed", () => {
  const collision = validRecord();
  collision.artifacts[0].filename = "A.txt";
  collision.artifacts[1].filename = "a.txt";
  const collisionResult = inspect(collision);
  assert.equal(collisionResult.outcome, "blocked");
  assert.ok(codes(collisionResult).has("RETURN_DECLARED_FILENAME_COLLISION"));

  const unsafe = validRecord();
  unsafe.artifacts[0].filename = "CON .txt";
  const unsafeResult = inspect(unsafe);
  assert.equal(unsafeResult.outcome, "blocked");
  assert.ok(codes(unsafeResult).has("RETURN_ARTIFACT_FILENAME_UNSAFE"));

  const superscriptDevice = validRecord();
  superscriptDevice.artifacts[0].filename = "COM¹.txt";
  const superscriptResult = inspect(superscriptDevice);
  assert.equal(superscriptResult.outcome, "blocked");
  assert.ok(codes(superscriptResult).has("RETURN_ARTIFACT_FILENAME_UNSAFE"));

  for (const formatControl of ["\u0085", "\u009f", "\u061c", "\u200e", "\u200f", "\u2028", "\u2029", "\u202a", "\u202e", "\u2066", "\u2069", "\ufeff"]) {
    const bidi = validRecord();
    bidi.artifacts[0].filename = `report${formatControl}fdp.exe`;
    const bidiResult = inspect(bidi);
    assert.equal(bidiResult.outcome, "blocked");
    assert.ok(codes(bidiResult).has("RETURN_ARTIFACT_FILENAME_UNSAFE"));
  }

  const unpairedSurrogate = validRecord();
  unpairedSurrogate.artifacts[0].filename = "report\ud800fdp.exe";
  const surrogateResult = inspect(unpairedSurrogate);
  assert.equal(surrogateResult.outcome, "blocked");
  assert.ok(codes(surrogateResult).has("RETURN_JSON_MALFORMED"));

  for (const nonAsciiCased of ["Å.txt", "å.txt", "Δ.txt", "δ.txt"]) {
    const cased = validRecord();
    cased.artifacts[0].filename = nonAsciiCased;
    const casedResult = inspect(cased);
    assert.equal(casedResult.outcome, "blocked");
    assert.ok(codes(casedResult).has("RETURN_ARTIFACT_FILENAME_UNSAFE"));
  }

  const unicodeExact = validRecord();
  unicodeExact.artifacts[0].filename = "資料.txt";
  unicodeExact.artifacts[1].filename = "data.txt";
  assert.equal(inspect(unicodeExact).outcome, "consistent");

  const unicodeCollision = validRecord();
  unicodeCollision.artifacts[0].filename = "が.txt";
  unicodeCollision.artifacts[1].filename = "か\u3099.txt";
  const unicodeResult = inspect(unicodeCollision);
  assert.equal(unicodeResult.outcome, "blocked");
  assert.ok(codes(unicodeResult).has("RETURN_DECLARED_FILENAME_COLLISION"));

  const whitespace = validRecord();
  whitespace.execution[0].tool = " ";
  whitespace.execution[0].version = "\t";
  const whitespaceResult = inspect(whitespace);
  assert.equal(whitespaceResult.outcome, "blocked");
  assert.ok(codes(whitespaceResult).has("RETURN_SCHEMA_INVALID"));

  const extra = validRecord();
  const supplied = options(extra);
  supplied.artifacts.push({ name: "important-omitted-source.pdf", sha256: `sha256:${"9".repeat(64)}`, size: 1 });
  const extraResult = inspect(extra, supplied);
  assert.equal(extraResult.outcome, "needs_review");
  assert.ok(codes(extraResult).has("RETURN_ATTACHED_ARTIFACT_UNDECLARED"));
});

test("maximum claim chain and tail cycle return structured results", () => {
  const record = validRecord();
  const identifiers = Array.from({ length: 4095 }, (_, index) => `claim.chain.${index}`);
  record.claims[0].depends_on = [identifiers[0]];
  identifiers.forEach((id, index) => record.claims.push({
    id,
    statement: `Acyclic dependency ${index}.`,
    research_verdict: "plausible_but_unresolved",
    depends_on: index + 1 < identifiers.length ? [identifiers[index + 1]] : [],
    source_ids: [],
    evidence_ids: [],
    fatal_gate_ids: [],
  }));
  const acyclic = inspect(record);
  assert.equal(acyclic.outcome, "consistent");
  assert.ok(codes(acyclic).has("RETURN_INTERNALLY_CONSISTENT"));

  record.claims[record.claims.length - 1].depends_on = [identifiers[identifiers.length - 100]];
  const cyclic = inspect(record);
  assert.equal(cyclic.outcome, "blocked");
  assert.ok(codes(cyclic).has("RETURN_CLAIM_DEPENDENCY_CYCLE"));
});

test("receipt bytes cannot be redeclared as substantive evidence", () => {
  const record = validRecord();
  record.artifacts.push({
    id: "artifact.receipt-alias",
    filename: "receipt-alias.json",
    role: "receipt",
    media_type: "application/json",
    sha256: HASHES.evidence,
  });
  const supplied = options(record);
  supplied.artifacts.push({ name: "receipt-alias.json", sha256: HASHES.evidence, size: 1 });
  const result = inspect(record, supplied);
  assert.equal(result.outcome, "blocked");
  assert.ok(codes(result).has("RETURN_ARTIFACT_HASH_ALIAS"));
});

test("a return declaring more than the browser attachment limit stays review-needed", () => {
  const record = validRecord();
  for (let index = 0; index < 29; index += 1) {
    record.artifacts.push({
      id: `artifact.extra.${index}`,
      filename: `extra-${index}.bin`,
      role: "other",
      media_type: "application/octet-stream",
      sha256: `sha256:${(index + 10).toString(16).padStart(64, "0")}`,
    });
  }
  const supplied = options(record, "extra-28.bin");
  assert.equal(supplied.artifacts.length, 32);
  const result = inspect(record, supplied);
  assert.equal(result.outcome, "needs_review");
  assert.ok(codes(result).has("RETURN_ARTIFACT_UNAVAILABLE"));
});

test("browser runtime discriminates every canonical Return Desk fixture", () => {
  const expected = {
    "audit_return_valid.json": "consistent",
    "audit_return_missing_artifact.json": "needs_review",
    "audit_return_poisoned_summary.json": "blocked",
    "audit_return_omitted_bound_failure.json": "blocked",
    "audit_return_unreceipted_execution.json": "blocked",
    "audit_return_missing_source_promotion.json": "blocked",
    "audit_return_deployment_overreach.json": "blocked",
    "audit_return_receipt_only_promotion.json": "blocked",
  };
  for (const [filename, outcome] of Object.entries(expected)) {
    const record = JSON.parse(fs.readFileSync(path.join(ROOT, "examples", filename), "utf8"));
    const artifacts = record.artifacts.flatMap((item) => {
      const local = path.join(ROOT, "examples", item.filename);
      if (!fs.existsSync(local)) return [];
      const bytes = fs.readFileSync(local);
      return [{
        name: item.filename,
        sha256: `sha256:${crypto.createHash("sha256").update(bytes).digest("hex")}`,
        size: bytes.byteLength,
        bytes,
      }];
    });
    const result = desk.inspectReturn(JSON.stringify(record), {
      artifacts,
      contract: {
        authority: "non_admissive_return_inspection",
        execution_activities: Array.from(desk.CANONICAL_ACTIVITIES),
        integrity_verified: true,
        schema,
        schema_sha256: schemaHash,
        version: "0.1.0",
      },
      protocol: { version: record.protocol.version, sha256: record.protocol.sha256.slice(7) },
    });
    assert.equal(result.outcome, outcome, `${filename}: ${JSON.stringify(result.findings)}`);
  }
});

function packetBuilderHarness() {
  const vm = require("node:vm");
  const source = fs.readFileSync(path.join(ROOT, "pages", "app.js"), "utf8");
  const boundary = source.indexOf("async function copyText");
  assert.ok(boundary > 0, "packet-builder test boundary is missing");
  const sandbox = {
    TextDecoder,
    TextEncoder,
    crypto: crypto.webcrypto,
    document: { querySelector: () => ({ value: "standard" }) },
    window: {
      BSC_AUDIT_PROFILE: {
        audit_depths: [{ id: "standard", instruction: "Inspect the supplied target.", label: "Standard", machine_record_required: false }],
        output_sections: [{ order: 1, title: "Scope and source coverage" }],
      },
      BSC_PAGE_LOCALE: {
        code: "en",
        report_language: "en",
        strings: {
          target_file_read_error: "The selected target filename is unsafe, overlong, or ambiguous.",
          target_filename_collision: "The target filename {name} collides with another selected filename under portable Unicode and case comparison.",
          target_filename_unsafe: "The target filename {name} is unsafe or exceeds 240 Unicode code points.",
          target_required: "Paste material or attach at least one target file first.",
        },
      },
      BSC_PROTOCOL: { sha256: "0".repeat(64), version: "test-protocol" },
    },
  };
  vm.createContext(sandbox);
  vm.runInContext(`${source.slice(0, boundary)}
    Object.assign(elements, { material: { value: "" } });
    Object.assign(state, { files: [], protocol: "", protocolReady: true });
    this.packetBuilderTestApi = Object.freeze({
      buildPacket,
      targetFilenameRecord,
      validateTargetFilenames,
      configure(material, protocol, files = []) {
        elements.material.value = material;
        state.protocol = protocol;
        state.files = files;
      },
    });`, sandbox);
  return sandbox.packetBuilderTestApi;
}

test("packet builder hashes and embeds exact pasted text and verified protocol text", async () => {
  const api = packetBuilderHarness();
  const material = "\n \u3000Claim: whitespace is part of this target.\n\t";
  const protocol = "EXACT PROTOCOL BYTES\n\n";
  api.configure(material, protocol);
  const packet = await api.buildPacket();
  const digest = crypto.createHash("sha256").update(Buffer.from(material, "utf8")).digest("hex");
  assert.ok(packet.includes(`UTF-8 text SHA-256: ${digest}`));
  assert.ok(packet.includes(`Characters (Unicode code points): ${Array.from(material).length}\n\n${material}\n`));
  const delimiter = "===== VERSIONED AUDIT PROTOCOL AND TARGET DELIMITER =====\n";
  const protocolOffset = packet.indexOf(delimiter);
  assert.ok(protocolOffset >= 0);
  assert.ok(packet.slice(protocolOffset + delimiter.length).startsWith(`${protocol}\n`));

  api.configure(" \u3000\n\t", protocol);
  await assert.rejects(api.buildPacket(), /Paste material or attach at least one target file first/);

  const whitespaceOnly = " \u3000\n\t";
  api.configure(whitespaceOnly, protocol, [{ embedded: false, name: "companion.bin", sha256: null, size: 1, type: "application/octet-stream" }]);
  const packetWithCompanion = await api.buildPacket();
  const whitespaceDigest = crypto.createHash("sha256").update(Buffer.from(whitespaceOnly, "utf8")).digest("hex");
  assert.ok(packetWithCompanion.includes(`UTF-8 text SHA-256: ${whitespaceDigest}`));
  assert.ok(packetWithCompanion.includes(`Characters (Unicode code points): ${Array.from(whitespaceOnly).length}\n\n${whitespaceOnly}\n`));
});

test("packet builder preserves safe filenames and rejects unsafe, overlong, or colliding names", () => {
  const api = packetBuilderHarness();
  const safeName = "資料-😀.txt";
  const safe = api.targetFilenameRecord(safeName);
  assert.equal(safe.error, null);
  assert.equal(safe.name, safeName);

  const decomposedHangul = api.targetFilenameRecord("가.txt");
  const composedHangul = api.targetFilenameRecord("가.txt");
  assert.equal(decomposedHangul.error, null);
  assert.equal(composedHangul.error, null);
  assert.equal(decomposedHangul.key, composedHangul.key);
  assert.notEqual(decomposedHangul.name, composedHangul.name);
  assert.equal(api.targetFilenameRecord("A.txt").key, api.targetFilenameRecord("a.txt").key);

  for (const name of ["", ".", "..", "CON.txt", "bad/name.txt", "trailing. ", "bidi\u202E.txt", "Ä.txt", `${"x".repeat(241)}.txt`]) {
    assert.notEqual(api.targetFilenameRecord(name).error, null, name);
  }

  api.configure("target", "protocol\n", [{ name: "A.txt" }]);
  assert.throws(() => api.validateTargetFilenames([{ name: "a.txt" }]), /"a\.txt" collides/);
  api.configure("target", "protocol\n", [{ name: "가.txt" }]);
  assert.throws(() => api.validateTargetFilenames([{ name: "가.txt" }]), /"가\.txt" collides/);
  api.configure("target", "protocol\n", []);
  assert.throws(() => api.validateTargetFilenames([{ name: "bad\u202E.txt" }]), /"bad\\u\{202e\}\.txt" is unsafe/);
  assert.doesNotThrow(() => api.validateTargetFilenames([{ name: safeName }]));
});
