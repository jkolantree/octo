"use strict";

(function publishReturnDesk(root, factory) {
  const api = Object.freeze(factory());
  if (typeof module !== "undefined" && module.exports) module.exports = api;
  if (root) root.BSC_RETURN_DESK = api;
})(typeof window !== "undefined" ? window : null, function buildReturnDesk() {
  const MAX_DEPTH = 64;
  const MAX_ITEMS = 100000;
  const MAX_RETURN_JSON_BYTES = 8 * 1024 * 1024;
  const EXPECTED_SCHEMA_SHA256 = "25714690651ca078c69f7e920c18d5087ec93b245a8cfed1f17633b2ea572799";
  const DATA_ANALYSIS_LEDGER_HEADER = "bsc_chatgpt_data_analysis_output_version: 2";
  const DATA_ANALYSIS_LEDGER_SECTION = "finalized_artifacts:";
  const EVIDENCE_ARTIFACT_ROLES = new Set(["evidence", "source", "execution_output"]);
  const NOT_APPLICABLE_REQUIRED_ACTIVITIES = new Set(["bsc_python_checker", "external_proof_tool", "empirical_test"]);
  const WINDOWS_RESERVED_BASENAMES = new Set(["CON", "PRN", "AUX", "NUL", "COM1", "COM2", "COM3", "COM4", "COM5", "COM6", "COM7", "COM8", "COM9", "LPT1", "LPT2", "LPT3", "LPT4", "LPT5", "LPT6", "LPT7", "LPT8", "LPT9", "COM¹", "COM²", "COM³", "LPT¹", "LPT²", "LPT³"]);
  const CANONICAL_ACTIVITIES = Object.freeze([
    "model_reasoning",
    "web_research",
    "independent_source_check",
    "chatgpt_data_analysis",
    "bsc_python_checker",
    "external_proof_tool",
    "empirical_test",
    "proposed_computation",
  ]);

  class StrictJsonError extends Error {}

  function utf8ByteLengthBounded(source, limit = MAX_RETURN_JSON_BYTES) {
    let bytes = 0;
    for (let index = 0; index < source.length; index += 1) {
      const first = source.charCodeAt(index);
      if (first <= 0x7f) bytes += 1;
      else if (first <= 0x7ff) bytes += 2;
      else if (first >= 0xd800 && first <= 0xdbff && index + 1 < source.length
        && source.charCodeAt(index + 1) >= 0xdc00 && source.charCodeAt(index + 1) <= 0xdfff) {
        bytes += 4;
        index += 1;
      } else bytes += 3;
      if (bytes > limit) return limit + 1;
    }
    return bytes;
  }

  function exceedsJsonByteLimit(source) {
    return source.length > MAX_RETURN_JSON_BYTES
      || utf8ByteLengthBounded(source) > MAX_RETURN_JSON_BYTES;
  }

  function hasVisibleText(value) {
    return Array.from(value).some((character) => !/[\p{C}\p{M}\p{Z}]/u.test(character));
  }

  function hasExactRuntimeBinding(text, version, expectedRows) {
    const rows = Array.from(expectedRows)
      .sort((left, right) => (
        left.filename < right.filename ? -1 : (left.filename > right.filename ? 1 : 0)
      ))
      .map((row) => `${row.sha256}  ${row.bytes}  ${row.filename}`);
    const expected = [
      DATA_ANALYSIS_LEDGER_HEADER,
      `session_reported_runtime=${version}`,
      "runtime_provenance=session_reported",
      DATA_ANALYSIS_LEDGER_SECTION,
      ...rows,
    ].join("\n") + "\n";
    return text === expected;
  }

  function hasUnpairedSurrogate(value) {
    for (let index = 0; index < value.length; index += 1) {
      const code = value.charCodeAt(index);
      if (code >= 0xd800 && code <= 0xdbff) {
        const next = value.charCodeAt(index + 1);
        if (!(next >= 0xdc00 && next <= 0xdfff)) return true;
        index += 1;
      } else if (code >= 0xdc00 && code <= 0xdfff) return true;
    }
    return false;
  }

  function portableFilename(name) {
    const normalized = name.normalize("NFC");
    const base = normalized.split(".", 1)[0].replace(/[ .]+$/g, "").toUpperCase();
    const unsafe = normalized === "." || normalized === ".." || /[ .]$/.test(normalized)
      || /[<>:"/\\|?*]/.test(normalized) || /[\p{Cc}\p{Cf}\p{Cs}\p{Zl}\p{Zp}]/u.test(normalized)
      || Array.from(normalized).some((character) => character.codePointAt(0) > 127 && character.toLowerCase() !== character.toUpperCase())
      || WINDOWS_RESERVED_BASENAMES.has(base);
    return { key: normalized.replace(/[A-Z]/g, (character) => character.toLowerCase()), unsafe };
  }

  function parseStrictJson(source, sizeChecked = false) {
    if (typeof source !== "string") throw new StrictJsonError("input must be text");
    if (!sizeChecked && exceedsJsonByteLimit(source)) throw new StrictJsonError(`input exceeds the ${MAX_RETURN_JSON_BYTES}-byte limit`);
    let position = 0;
    let itemCount = 0;

    function fail(message) {
      throw new StrictJsonError(`${message} at character ${position}`);
    }

    function whitespace() {
      while (position < source.length && /[\u0009\u000a\u000d\u0020]/.test(source[position])) position += 1;
    }

    function stringValue() {
      if (source[position] !== '"') fail("expected a JSON string");
      const start = position;
      position += 1;
      while (position < source.length) {
        const code = source.charCodeAt(position);
        if (code < 0x20) fail("unescaped control character in JSON string");
        if (source[position] === '"') {
          position += 1;
          try {
            const decoded = JSON.parse(source.slice(start, position));
            if (hasUnpairedSurrogate(decoded)) fail("unpaired JSON unicode surrogate");
            return decoded;
          } catch (_error) {
            if (_error instanceof StrictJsonError) throw _error;
            fail("invalid JSON string escape");
          }
        }
        if (source[position] === "\\") {
          position += 1;
          if (position >= source.length || !/["\\/bfnrtu]/.test(source[position])) fail("invalid JSON string escape");
          if (source[position] === "u") {
            const digits = source.slice(position + 1, position + 5);
            if (!/^[0-9a-fA-F]{4}$/.test(digits)) fail("invalid JSON unicode escape");
            position += 4;
          }
        }
        position += 1;
      }
      fail("unterminated JSON string");
    }

    function value(depth) {
      if (depth > MAX_DEPTH) fail(`JSON nesting exceeds ${MAX_DEPTH}`);
      whitespace();
      const token = source[position];
      if (token === '"') return stringValue();
      if (token === "{") {
        position += 1;
        whitespace();
        const output = Object.create(null);
        const names = new Set();
        if (source[position] === "}") {
          position += 1;
          return output;
        }
        while (position < source.length) {
          const name = stringValue();
          if (names.has(name)) fail(`duplicate JSON object key ${JSON.stringify(name)}`);
          names.add(name);
          itemCount += 1;
          if (itemCount > MAX_ITEMS) fail(`JSON container entries exceed ${MAX_ITEMS}`);
          whitespace();
          if (source[position] !== ":") fail("expected ':' after JSON object key");
          position += 1;
          output[name] = value(depth + 1);
          whitespace();
          if (source[position] === "}") {
            position += 1;
            return output;
          }
          if (source[position] !== ",") fail("expected ',' or '}' in JSON object");
          position += 1;
          whitespace();
        }
        fail("unterminated JSON object");
      }
      if (token === "[") {
        position += 1;
        whitespace();
        const output = [];
        if (source[position] === "]") {
          position += 1;
          return output;
        }
        while (position < source.length) {
          itemCount += 1;
          if (itemCount > MAX_ITEMS) fail(`JSON container entries exceed ${MAX_ITEMS}`);
          output.push(value(depth + 1));
          whitespace();
          if (source[position] === "]") {
            position += 1;
            return output;
          }
          if (source[position] !== ",") fail("expected ',' or ']' in JSON array");
          position += 1;
        }
        fail("unterminated JSON array");
      }
      for (const [literal, decoded] of [["true", true], ["false", false], ["null", null]]) {
        if (source.startsWith(literal, position)) {
          position += literal.length;
          return decoded;
        }
      }
      const number = source.slice(position).match(/^-?(?:0|[1-9][0-9]*)(?:\.[0-9]+)?(?:[eE][+-]?[0-9]+)?/);
      if (number) {
        position += number[0].length;
        const decoded = Number(number[0]);
        if (!Number.isFinite(decoded)) fail("non-finite JSON number is forbidden");
        return decoded;
      }
      fail("unexpected JSON token");
    }

    whitespace();
    const decoded = value(0);
    whitespace();
    if (position !== source.length) fail("trailing content after JSON value");
    if (!decoded || typeof decoded !== "object" || Array.isArray(decoded)) {
      throw new StrictJsonError("top-level JSON value must be an object");
    }
    return decoded;
  }

  function jsonKey(value) {
    if (value === null || typeof value !== "object") return JSON.stringify(value);
    if (Array.isArray(value)) return `[${value.map(jsonKey).join(",")}]`;
    return `{${Object.keys(value).sort().map((key) => `${JSON.stringify(key)}:${jsonKey(value[key])}`).join(",")}}`;
  }

  function schemaType(value, expected) {
    if (expected === "object") return value !== null && typeof value === "object" && !Array.isArray(value);
    if (expected === "array") return Array.isArray(value);
    if (expected === "string") return typeof value === "string";
    if (expected === "integer") return Number.isInteger(value);
    if (expected === "number") return typeof value === "number" && Number.isFinite(value);
    if (expected === "boolean") return typeof value === "boolean";
    if (expected === "null") return value === null;
    return false;
  }

  function resolveSchemaRef(rootSchema, reference) {
    if (typeof reference !== "string" || !reference.startsWith("#/")) throw new Error("only local schema references are supported");
    let value = rootSchema;
    for (const raw of reference.slice(2).split("/")) {
      const token = raw.replace(/~1/g, "/").replace(/~0/g, "~");
      value = value[token];
    }
    return value;
  }

  function validateSchema(value, schema, rootSchema = schema, path = "$") {
    if (schema === true || (schema && typeof schema === "object" && Object.keys(schema).length === 0)) return [];
    if (schema === false) return [{ path, message: "value is forbidden by the schema" }];
    if (!schema || typeof schema !== "object" || Array.isArray(schema)) return [{ path, message: "invalid internal schema node" }];
    if (schema.$ref) return validateSchema(value, resolveSchemaRef(rootSchema, schema.$ref), rootSchema, path);
    let violations = [];
    if (Array.isArray(schema.allOf)) {
      for (const member of schema.allOf) violations = violations.concat(validateSchema(value, member, rootSchema, path));
    }
    if (Array.isArray(schema.oneOf)) {
      const matches = schema.oneOf.filter((member) => validateSchema(value, member, rootSchema, path).length === 0).length;
      if (matches !== 1) return violations.concat([{ path, message: "value must satisfy exactly one allowed schema" }]);
    }
    if (schema.if && validateSchema(value, schema.if, rootSchema, path).length === 0 && schema.then) {
      violations = violations.concat(validateSchema(value, schema.then, rootSchema, path));
    }
    if (schema.type !== undefined) {
      const expected = Array.isArray(schema.type) ? schema.type : [schema.type];
      if (!expected.some((item) => schemaType(value, item))) return violations.concat([{ path, message: `expected type ${expected.join("|")}` }]);
    }
    if (Object.prototype.hasOwnProperty.call(schema, "const") && jsonKey(value) !== jsonKey(schema.const)) {
      violations.push({ path, message: "value differs from the required constant" });
    }
    if (Array.isArray(schema.enum) && !schema.enum.some((item) => jsonKey(value) === jsonKey(item))) {
      violations.push({ path, message: "value is outside the allowed enumeration" });
    }
    if (typeof value === "string") {
      const codePointLength = Array.from(value).length;
      if (schema.minLength !== undefined && codePointLength < schema.minLength) violations.push({ path, message: `string is shorter than ${schema.minLength} characters` });
      if (schema.maxLength !== undefined && codePointLength > schema.maxLength) violations.push({ path, message: `string is longer than ${schema.maxLength} characters` });
      if (schema.pattern && !(new RegExp(schema.pattern).test(value))) violations.push({ path, message: "string does not match the required pattern" });
    }
    if (typeof value === "number" && Number.isFinite(value)) {
      if (schema.minimum !== undefined && value < schema.minimum) violations.push({ path, message: `number is below minimum ${schema.minimum}` });
      if (schema.maximum !== undefined && value > schema.maximum) violations.push({ path, message: `number exceeds maximum ${schema.maximum}` });
    }
    if (Array.isArray(value)) {
      if (schema.minItems !== undefined && value.length < schema.minItems) violations.push({ path, message: `array has fewer than ${schema.minItems} items` });
      if (schema.maxItems !== undefined && value.length > schema.maxItems) violations.push({ path, message: `array has more than ${schema.maxItems} items` });
      if (schema.uniqueItems && new Set(value.map(jsonKey)).size !== value.length) violations.push({ path, message: "array items must be unique" });
      if (Array.isArray(schema.prefixItems)) {
        schema.prefixItems.forEach((member, index) => {
          if (index < value.length) violations = violations.concat(validateSchema(value[index], member, rootSchema, `${path}.${index}`));
        });
      }
      if (schema.items !== undefined) {
        const start = Array.isArray(schema.prefixItems) ? schema.prefixItems.length : 0;
        for (let index = start; index < value.length; index += 1) {
          violations = violations.concat(validateSchema(value[index], schema.items, rootSchema, `${path}.${index}`));
        }
      }
    }
    if (value !== null && typeof value === "object" && !Array.isArray(value)) {
      for (const name of schema.required || []) {
        if (!Object.prototype.hasOwnProperty.call(value, name)) violations.push({ path: `${path}.${name}`, message: "required property is missing" });
      }
      const properties = schema.properties || {};
      for (const [name, nested] of Object.entries(value)) {
        if (Object.prototype.hasOwnProperty.call(properties, name)) {
          violations = violations.concat(validateSchema(nested, properties[name], rootSchema, `${path}.${name}`));
        } else if (schema.additionalProperties !== undefined) {
          violations = violations.concat(validateSchema(nested, schema.additionalProperties, rootSchema, `${path}.${name}`));
        }
      }
    }
    return violations;
  }

  function finding(severity, code, path, message, witness, repair) {
    const item = { severity, code, path, message };
    if (witness !== undefined) item.witness = witness;
    if (repair !== undefined) item.repair = repair;
    return item;
  }

  function sortedUnique(values) {
    return Array.from(new Set(values)).sort();
  }

  function sameSet(left, right) {
    const a = sortedUnique(left);
    const b = sortedUnique(right);
    return a.length === b.length && a.every((value, index) => value === b[index]);
  }

  function suppliedByteView(value) {
    if (typeof ArrayBuffer === "undefined") return null;
    if (value instanceof ArrayBuffer) return new Uint8Array(value);
    if (ArrayBuffer.isView(value)) return new Uint8Array(value.buffer, value.byteOffset, value.byteLength);
    return null;
  }

  function isUtf8TextArtifact(artifact) {
    const mediaType = artifact.media_type.toLowerCase().split(";", 1)[0].trim();
    const filename = artifact.filename.toLowerCase();
    return mediaType.startsWith("text/")
      || filename.endsWith(".md")
      || filename.endsWith(".txt")
      || filename.endsWith(".json");
  }

  function indexRecords(records, label, findings, globalIds) {
    const output = new Map();
    records.forEach((record, index) => {
      if (output.has(record.id)) findings.push(finding("blocked", "RETURN_DUPLICATE_ID", `$.${label}.${index}.id`, `${label} identifiers must be unique`, record.id));
      else output.set(record.id, record);
      if (globalIds.has(record.id)) findings.push(finding("blocked", "RETURN_GLOBAL_ID_COLLISION", `$.${label}.${index}.id`, "record identifiers must be globally unambiguous", record.id));
      else globalIds.add(record.id);
    });
    return output;
  }

  function requireReferences(records, fields, indexes, collection, findings) {
    records.forEach((record, index) => {
      fields.forEach(([field, target, nullable = false]) => {
        const raw = record[field];
        const values = Array.isArray(raw) ? raw : (nullable && raw === null ? [] : [raw]);
        values.forEach((id) => {
          if (!indexes[target].has(id)) findings.push(finding("blocked", "RETURN_REFERENCE_MISSING", `$.${collection}.${index}.${field}`, `reference does not identify a declared ${target} record`, id));
        });
      });
    });
  }

  function extractReturnJson(text) {
    const trimJsonWhitespace = (value) => value.replace(/^[\u0009\u000a\u000d\u0020]+|[\u0009\u000a\u000d\u0020]+$/g, "");
    const trimmed = trimJsonWhitespace(text);
    if (!trimmed) return { kind: "missing" };
    if (trimmed.startsWith("{") || trimmed.trimStart().startsWith("{")) return { kind: "json", text: trimmed };
    const blocks = [];
    const pattern = /```(?:json|audit_return\.json)?([\s\S]*?)```/gi;
    let match;
    while ((match = pattern.exec(trimmed)) !== null) {
      const candidate = trimJsonWhitespace(match[1]);
      if (candidate.startsWith("{") || candidate.trimStart().startsWith("{")) blocks.push(candidate);
    }
    if (blocks.length === 1) return { kind: "json", text: blocks[0] };
    if (blocks.length > 1) return { kind: "ambiguous" };
    return { kind: "prose" };
  }

  function inspectReturn(text, options) {
    const contract = options && options.contract;
    const protocol = options && options.protocol;
    const suppliedArtifacts = (options && options.artifacts) || [];
    const checksRun = [];
    const checksNotRun = [];
    const findings = [];
    if (typeof text !== "string") {
      return {
        inspection_version: "0.1.0",
        authority: "non_admissive_return_inspection",
        outcome: "blocked",
        checks: { run: [], not_run: ["strict_json_parse", "schema_validation", "semantic_projection", "local_artifact_hashes"] },
        findings: [finding("blocked", "RETURN_JSON_MALFORMED", "$", "input must be text")],
        caveat: "Internal consistency is not truth, proof, admissibility, checker execution, citation verification, or deployment approval.",
      };
    }
    if (exceedsJsonByteLimit(text)) {
      return {
        inspection_version: "0.1.0",
        authority: "non_admissive_return_inspection",
        outcome: "blocked",
        checks: { run: [], not_run: ["strict_json_parse", "schema_validation", "semantic_projection", "local_artifact_hashes"] },
        findings: [finding("blocked", "RETURN_JSON_TOO_LARGE", "$", `The audit return exceeds the ${MAX_RETURN_JSON_BYTES}-byte UTF-8 limit.`)],
        caveat: "Internal consistency is not truth, proof, admissibility, checker execution, citation verification, or deployment approval.",
      };
    }
    const extracted = extractReturnJson(text);
    if (extracted.kind === "missing" || extracted.kind === "prose") {
      return {
        inspection_version: "0.1.0",
        authority: "non_admissive_return_inspection",
        outcome: "needs_review",
        checks: { run: [], not_run: ["strict_json_parse", "schema_validation", "semantic_projection", "local_artifact_hashes"] },
        findings: [finding("review", "RETURN_ENVELOPE_MISSING", "$", "No single audit_return-v0.1 JSON envelope was found. Prose alone cannot receive a consistent result.")],
        caveat: "Internal consistency is not truth, proof, admissibility, checker execution, citation verification, or deployment approval.",
      };
    }
    if (extracted.kind === "ambiguous") {
      return {
        inspection_version: "0.1.0",
        authority: "non_admissive_return_inspection",
        outcome: "blocked",
        checks: { run: [], not_run: ["schema_validation", "semantic_projection", "local_artifact_hashes"] },
        findings: [finding("blocked", "RETURN_ENVELOPE_AMBIGUOUS", "$", "More than one candidate audit-return envelope was found.")],
        caveat: "Internal consistency is not truth, proof, admissibility, checker execution, citation verification, or deployment approval.",
      };
    }

    let record;
    try {
      checksRun.push("strict_json_parse");
      record = parseStrictJson(extracted.text, true);
    } catch (error) {
      return {
        inspection_version: "0.1.0",
        authority: "non_admissive_return_inspection",
        outcome: "blocked",
        checks: { run: ["strict_json_parse"], not_run: ["schema_validation", "semantic_projection", "local_artifact_hashes"] },
        findings: [finding("blocked", "RETURN_JSON_MALFORMED", "$", error instanceof Error ? error.message : "strict JSON parsing failed")],
        caveat: "Internal consistency is not truth, proof, admissibility, checker execution, citation verification, or deployment approval.",
      };
    }

    if (!contract || contract.integrity_verified !== true || contract.schema_sha256 !== EXPECTED_SCHEMA_SHA256
      || !contract.schema || Array.isArray(contract.schema) || typeof contract.schema !== "object"
      || contract.schema.$id !== "urn:bsc-audit:schema:audit-return:v0.1"
      || contract.version !== "0.1.0" || contract.authority !== "non_admissive_return_inspection"
      || !Array.isArray(contract.execution_activities)
      || contract.execution_activities.length !== CANONICAL_ACTIVITIES.length
      || !sameSet(contract.execution_activities, CANONICAL_ACTIVITIES)) {
      return {
        inspection_version: "0.1.0",
        authority: "non_admissive_return_inspection",
        outcome: "blocked",
        checks: { run: checksRun, not_run: ["schema_validation", "semantic_projection", "local_artifact_hashes"] },
        findings: [finding("blocked", "RETURN_CONTRACT_UNAVAILABLE", "$", "The locally generated return contract is missing or malformed.")],
        caveat: "Internal consistency is not truth, proof, admissibility, checker execution, citation verification, or deployment approval.",
      };
    }

    const schemaViolations = validateSchema(record, contract.schema).slice(0, 100);
    checksRun.push("schema_validation");
    if (schemaViolations.length) {
      schemaViolations.forEach((item) => findings.push(finding("blocked", "RETURN_SCHEMA_INVALID", item.path, item.message)));
      return {
        inspection_version: contract.version,
        authority: contract.authority,
        outcome: "blocked",
        checks: { run: checksRun, not_run: ["semantic_projection", "local_artifact_hashes"] },
        findings,
        caveat: "Internal consistency is not truth, proof, admissibility, checker execution, citation verification, or deployment approval.",
      };
    }

    checksRun.push("semantic_projection", "local_artifact_hashes");
    if (!protocol || record.protocol.version !== protocol.version) {
      findings.push(finding("blocked", "RETURN_PROTOCOL_VERSION_MISMATCH", "$.protocol.version", "return protocol version differs from the locally verified protocol", { expected: protocol && protocol.version, observed: record.protocol.version }));
    }
    const expectedProtocolHash = protocol && protocol.sha256 ? `sha256:${protocol.sha256}` : null;
    if (!expectedProtocolHash || record.protocol.sha256 !== expectedProtocolHash) {
      findings.push(finding("blocked", "RETURN_PROTOCOL_HASH_MISMATCH", "$.protocol.sha256", "return protocol hash differs from the locally verified protocol", { expected: expectedProtocolHash, observed: record.protocol.sha256 }));
    }

    const globalIds = new Set();
    const indexes = {
      claims: indexRecords(record.claims, "claims", findings, globalIds),
      sources: indexRecords(record.sources, "sources", findings, globalIds),
      artifacts: indexRecords(record.artifacts, "artifacts", findings, globalIds),
      evidence: indexRecords(record.evidence, "evidence", findings, globalIds),
      fatal_gates: indexRecords(record.fatal_gates, "fatal_gates", findings, globalIds),
      receipts: indexRecords(record.receipts, "receipts", findings, globalIds),
      unresolved_obligations: indexRecords(record.unresolved_obligations, "unresolved_obligations", findings, globalIds),
    };

    const semanticText = [];
    record.claims.forEach((item, index) => semanticText.push([`$.claims.${index}.statement`, item.statement]));
    record.sources.forEach((item, index) => {
      semanticText.push([`$.sources.${index}.label`, item.label]);
      item.inspected_scope.forEach((value, textIndex) => semanticText.push([`$.sources.${index}.inspected_scope.${textIndex}`, value]));
      item.omissions.forEach((value, textIndex) => semanticText.push([`$.sources.${index}.omissions.${textIndex}`, value]));
    });
    record.artifacts.forEach((item, index) => semanticText.push([`$.artifacts.${index}.media_type`, item.media_type]));
    record.execution.forEach((item, index) => {
      semanticText.push([`$.execution.${index}.tool`, item.tool]);
      semanticText.push([`$.execution.${index}.version`, item.version]);
      semanticText.push([`$.execution.${index}.notes`, item.notes]);
    });
    record.unresolved_obligations.forEach((item, index) => semanticText.push([`$.unresolved_obligations.${index}.statement`, item.statement]));
    semanticText.forEach(([path, value]) => {
      if (value !== null && !hasVisibleText(value)) findings.push(finding(
        "blocked",
        "RETURN_SEMANTIC_TEXT_INVISIBLE",
        path,
        "human-semantic text must contain a visible letter, number, punctuation mark, or symbol",
        Array.from(value).map((character) => `U+${character.codePointAt(0).toString(16).toUpperCase().padStart(4, "0")}`),
      ));
    });

    requireReferences(record.claims, [["depends_on", "claims"], ["source_ids", "sources"], ["evidence_ids", "evidence"], ["fatal_gate_ids", "fatal_gates"]], indexes, "claims", findings);
    requireReferences(record.sources, [["artifact_id", "artifacts", true]], indexes, "sources", findings);
    requireReferences(record.evidence, [["claim_ids", "claims"], ["gate_ids", "fatal_gates"], ["artifact_ids", "artifacts"], ["receipt_ids", "receipts"]], indexes, "evidence", findings);
    requireReferences(record.fatal_gates, [["evidence_ids", "evidence"], ["obligation_ids", "unresolved_obligations"]], indexes, "fatal_gates", findings);
    requireReferences(record.receipts, [["artifact_id", "artifacts"], ["claim_ids", "claims"], ["gate_ids", "fatal_gates"]], indexes, "receipts", findings);
    requireReferences(record.unresolved_obligations, [["claim_ids", "claims"], ["gate_ids", "fatal_gates"], ["evidence_ids", "evidence"]], indexes, "unresolved_obligations", findings);
    requireReferences(record.execution, [["input_artifact_ids", "artifacts"], ["output_artifact_ids", "artifacts"], ["receipt_ids", "receipts"]], indexes, "execution", findings);
    const claimStates = new Map();
    const cyclicClaims = new Set();
    record.claims.forEach((claim) => {
      if ((claimStates.get(claim.id) || 0) !== 0) return;
      const stack = [{ id: claim.id, dependencyIndex: 0 }];
      const path = [];
      const positions = new Map();
      while (stack.length > 0) {
        const frame = stack[stack.length - 1];
        if ((claimStates.get(frame.id) || 0) === 0) {
          claimStates.set(frame.id, 1);
          positions.set(frame.id, path.length);
          path.push(frame.id);
        }
        const dependencies = indexes.claims.get(frame.id).depends_on;
        if (frame.dependencyIndex < dependencies.length) {
          const dependency = dependencies[frame.dependencyIndex];
          frame.dependencyIndex += 1;
          if (!indexes.claims.has(dependency)) continue;
          const dependencyState = claimStates.get(dependency) || 0;
          if (dependencyState === 0) stack.push({ id: dependency, dependencyIndex: 0 });
          else if (dependencyState === 1) path.slice(positions.get(dependency)).forEach((item) => cyclicClaims.add(item));
          continue;
        }
        stack.pop();
        claimStates.set(frame.id, 2);
        positions.delete(frame.id);
        path.pop();
      }
    });
    if (cyclicClaims.size > 0) findings.push(finding("blocked", "RETURN_CLAIM_DEPENDENCY_CYCLE", "$.claims", "claim dependencies contain a cycle", Array.from(cyclicClaims).sort()));
    for (const [field, role] of [["request_artifact_id", "request"], ["report_artifact_id", "report"]]) {
      const artifact = indexes.artifacts.get(record.bindings[field]);
      if (!artifact) findings.push(finding("blocked", "RETURN_BINDING_MISSING", `$.bindings.${field}`, "binding does not reference a declared artifact", record.bindings[field]));
      else if (artifact.role !== role) findings.push(finding("blocked", "RETURN_BINDING_ROLE_MISMATCH", `$.bindings.${field}`, `binding must reference an artifact with role ${role}`, artifact.role));
    }
    if (record.bindings.request_artifact_id === record.bindings.report_artifact_id) findings.push(finding("blocked", "RETURN_REQUEST_REPORT_ALIAS", "$.bindings", "request and report must be independently identified artifacts"));

    const primary = indexes.claims.get(record.primary_claim_id);
    if (!primary) findings.push(finding("blocked", "RETURN_PRIMARY_CLAIM_MISSING", "$.primary_claim_id", "primary claim does not identify a declared claim", record.primary_claim_id));
    if (primary && primary.fatal_gate_ids.length === 0) findings.push(finding("blocked", "RETURN_PRIMARY_CLAIM_GATE_MISSING", "$.primary_claim_id", "the primary claim must declare at least one independently evaluated fatal gate"));
    if (record.summary_projection.primary_claim_id !== record.primary_claim_id) findings.push(finding("blocked", "RETURN_SUMMARY_PRIMARY_MISMATCH", "$.summary_projection.primary_claim_id", "summary primary claim differs from the detailed return"));
    if (primary && record.summary_projection.research_verdict !== primary.research_verdict) findings.push(finding("blocked", "RETURN_SUMMARY_VERDICT_MISMATCH", "$.summary_projection.research_verdict", "summary verdict differs from the primary claim verdict"));
    if (!sameSet(record.summary_projection.fatal_gate_ids, record.fatal_gates.map((item) => item.id))) findings.push(finding("blocked", "RETURN_SUMMARY_GATE_OMISSION", "$.summary_projection.fatal_gate_ids", "summary must project every fatal gate exactly"));
    if (!sameSet(record.summary_projection.unresolved_obligation_ids, record.unresolved_obligations.map((item) => item.id))) findings.push(finding("blocked", "RETURN_SUMMARY_OBLIGATION_OMISSION", "$.summary_projection.unresolved_obligation_ids", "summary must project every unresolved obligation exactly"));

    record.claims.forEach((claim, index) => {
      const boundEvidence = record.evidence.filter((item) => item.claim_ids.includes(claim.id)).map((item) => item.id);
      if (!sameSet(claim.evidence_ids, boundEvidence)) findings.push(finding("blocked", "RETURN_CLAIM_EVIDENCE_ASYMMETRIC", `$.claims.${index}.evidence_ids`, "claim/evidence bindings must agree in both directions"));
    });
    record.fatal_gates.forEach((gate, index) => {
      const boundEvidence = record.evidence.filter((item) => item.gate_ids.includes(gate.id)).map((item) => item.id);
      if (!sameSet(gate.evidence_ids, boundEvidence)) findings.push(finding("blocked", "RETURN_GATE_EVIDENCE_ASYMMETRIC", `$.fatal_gates.${index}.evidence_ids`, "gate/evidence bindings must include every bound record in both directions"));
      const owningClaims = record.claims.filter((claim) => claim.fatal_gate_ids.includes(gate.id)).map((claim) => claim.id);
      if (owningClaims.length === 0) findings.push(finding("blocked", "RETURN_GATE_OWNER_MISSING", `$.fatal_gates.${index}`, "every fatal gate must be owned by at least one declared claim"));
      const scopeMismatches = Array.from(new Set(gate.evidence_ids.concat(boundEvidence))).filter((id) => indexes.evidence.has(id) && !owningClaims.every((claimId) => indexes.evidence.get(id).claim_ids.includes(claimId)));
      if (scopeMismatches.length > 0) findings.push(finding("blocked", "RETURN_GATE_CLAIM_SCOPE_MISMATCH", `$.fatal_gates.${index}.evidence_ids`, "every evidence record used to derive a gate must bind every claim that declares that gate", { claim_ids: owningClaims, evidence_ids: scopeMismatches }));
      const boundObligations = record.unresolved_obligations.filter((item) => item.gate_ids.includes(gate.id)).map((item) => item.id);
      if (!sameSet(gate.obligation_ids, boundObligations)) findings.push(finding("blocked", "RETURN_GATE_OBLIGATION_ASYMMETRIC", `$.fatal_gates.${index}.obligation_ids`, "gate/obligation bindings must include every unresolved obligation in both directions"));
    });

    const suppliedByName = new Map();
    const suppliedPortableNames = new Map();
    suppliedArtifacts.forEach((artifact, index) => {
      const portable = portableFilename(artifact.name);
      if (portable.unsafe) findings.push(finding("blocked", "RETURN_ATTACHED_FILENAME_UNSAFE", `$.attachments.${index}`, "attached artifact filename is not a portable safe basename", artifact.name));
      if (suppliedPortableNames.has(portable.key)) findings.push(finding("blocked", "RETURN_ATTACHED_FILENAME_COLLISION", `$.attachments.${index}`, "attached artifact filenames collide after portable Unicode and case normalization", [suppliedPortableNames.get(portable.key), artifact.name]));
      else suppliedPortableNames.set(portable.key, artifact.name);
      if (suppliedByName.has(artifact.name)) findings.push(finding("blocked", "RETURN_ATTACHED_FILENAME_DUPLICATE", `$.attachments.${index}`, "attached artifact filenames must be unique", artifact.name));
      else suppliedByName.set(artifact.name, artifact);
    });
    const verifiedArtifacts = new Set();
    const verifiedArtifactText = new Map();
    const declaredFilenames = new Set();
    const declaredPortableNames = new Map();
    record.artifacts.forEach((artifact, index) => {
      const portable = portableFilename(artifact.filename);
      if (portable.unsafe) {
        findings.push(finding("blocked", "RETURN_ARTIFACT_FILENAME_UNSAFE", `$.artifacts.${index}.filename`, "artifact filenames must be portable basenames without controls, reserved device names, or trailing dot/space", artifact.filename));
        return;
      }
      if (declaredPortableNames.has(portable.key)) findings.push(finding("blocked", "RETURN_DECLARED_FILENAME_COLLISION", `$.artifacts.${index}.filename`, "declared artifact filenames collide after portable Unicode and case normalization", [declaredPortableNames.get(portable.key), artifact.filename]));
      else declaredPortableNames.set(portable.key, artifact.filename);
      if (declaredFilenames.has(artifact.filename)) findings.push(finding("blocked", "RETURN_DECLARED_FILENAME_DUPLICATE", `$.artifacts.${index}.filename`, "declared artifact filenames must be unique for browser-local binding", artifact.filename));
      declaredFilenames.add(artifact.filename);
      if (artifact.sha256 === `sha256:${"0".repeat(64)}`) findings.push(finding("blocked", "RETURN_HASH_PLACEHOLDER", `$.artifacts.${index}.sha256`, "an all-zero SHA-256 is a placeholder, not a byte binding"));
      const supplied = suppliedByName.get(artifact.filename);
      if (!supplied || !supplied.sha256) {
        findings.push(finding("review", "RETURN_ARTIFACT_UNAVAILABLE", `$.artifacts.${index}`, "declared artifact bytes were not locally available and hashed", artifact.filename));
        return;
      }
      if (supplied.sha256 !== artifact.sha256) {
        findings.push(finding("blocked", "RETURN_ARTIFACT_HASH_MISMATCH", `$.artifacts.${index}.sha256`, "attached artifact bytes do not match the declared SHA-256", { filename: artifact.filename, expected: artifact.sha256, observed: supplied.sha256 }));
        return;
      }
      const suppliedBytes = suppliedByteView(supplied.bytes);
      if (suppliedBytes !== null && isUtf8TextArtifact(artifact)) {
        let decoded;
        try {
          decoded = new TextDecoder("utf-8", { fatal: true }).decode(suppliedBytes);
        } catch (_error) {
          findings.push(finding("blocked", "RETURN_ARTIFACT_TEXT_ENCODING_INVALID", `$.artifacts.${index}`, "a hash-verified text artifact must be valid UTF-8", artifact.filename));
          return;
        }
        const invalidControlOffsets = [];
        suppliedBytes.forEach((byte, byteOffset) => {
          if (byte <= 0x08 || byte === 0x0b || byte === 0x0c || (byte >= 0x0e && byte <= 0x1f) || byte === 0x7f) invalidControlOffsets.push(byteOffset);
        });
        if (invalidControlOffsets.length > 0) {
          findings.push(finding(
            "blocked",
            "RETURN_ARTIFACT_TEXT_CONTROL_INVALID",
            `$.artifacts.${index}`,
            "a hash-verified text artifact may contain only TAB, LF, or CR control bytes",
            { filename: artifact.filename, byte_offsets: invalidControlOffsets.slice(0, 100) },
          ));
          return;
        }
        verifiedArtifactText.set(artifact.id, decoded);
      }
      verifiedArtifacts.add(artifact.id);
    });
    const artifactsByHash = new Map();
    record.artifacts.forEach((artifact) => {
      if (!artifactsByHash.has(artifact.sha256)) artifactsByHash.set(artifact.sha256, []);
      artifactsByHash.get(artifact.sha256).push(artifact);
    });
    const hashAliases = {};
    artifactsByHash.forEach((artifactsForHash, digest) => {
      if (artifactsForHash.length > 1) hashAliases[digest] = artifactsForHash.map((artifact) => artifact.id).sort();
    });
    if (Object.keys(hashAliases).length > 0) findings.push(finding("blocked", "RETURN_ARTIFACT_HASH_ALIAS", "$.artifacts", "identical bytes cannot be redeclared under multiple artifact identifiers or roles", hashAliases, "use one artifact identifier for each exact byte sequence and reference it without role laundering"));
    suppliedArtifacts.forEach((artifact, index) => {
      if (!declaredFilenames.has(artifact.name)) findings.push(finding("review", "RETURN_ATTACHED_ARTIFACT_UNDECLARED", `$.attachments.${index}`, "an attached file is not declared by the return envelope and was not used as evidence", artifact.name));
    });
    record.sources.forEach((source, index) => {
      if (source.coverage_state !== "fully_inspected") findings.push(finding("review", "RETURN_SOURCE_COVERAGE_INCOMPLETE", `$.sources.${index}.coverage_state`, "source coverage is incomplete; absence or truncation is not a scientific verdict", source.coverage_state));
      if (source.artifact_id === null) findings.push(finding("review", "RETURN_SOURCE_BYTES_UNBOUND", `$.sources.${index}.artifact_id`, "source bytes are not bound to a declared local artifact", source.id));
      const sourceArtifact = source.artifact_id === null ? null : indexes.artifacts.get(source.artifact_id);
      if (sourceArtifact && sourceArtifact.role !== "source") findings.push(finding("blocked", "RETURN_SOURCE_ARTIFACT_ROLE_MISMATCH", `$.sources.${index}.artifact_id`, "a source must bind an artifact with role source"));
      const coverageContradiction = (
        (source.coverage_state === "fully_inspected" && (source.artifact_id === null || source.inspected_scope.length === 0 || source.omissions.length > 0 || ["citation_only", "unavailable"].includes(source.access_mode)))
        || (["partially_inspected", "possibly_truncated"].includes(source.coverage_state) && source.omissions.length === 0)
        || (source.coverage_state === "missing" && (source.artifact_id !== null || source.access_mode !== "unavailable" || source.inspected_scope.length > 0 || source.omissions.length === 0))
        || (source.coverage_state === "unreadable" && (source.inspected_scope.length > 0 || source.omissions.length === 0))
      );
      if (coverageContradiction) findings.push(finding("blocked", "RETURN_SOURCE_COVERAGE_CONTRADICTION", `$.sources.${index}`, "source coverage, access, inspected scope, omissions, and artifact binding contradict one another"));
    });

    const receiptArtifactCounts = new Map();
    record.receipts.forEach((receipt) => receiptArtifactCounts.set(receipt.artifact_id, (receiptArtifactCounts.get(receipt.artifact_id) || 0) + 1));
    const reusedReceiptArtifacts = new Set(Array.from(receiptArtifactCounts.entries()).filter(([, count]) => count > 1).map(([id]) => id));
    if (reusedReceiptArtifacts.size > 0) findings.push(finding("blocked", "RETURN_RECEIPT_ARTIFACT_REUSED", "$.receipts", "one receipt artifact cannot be relabeled as multiple receipt records", Array.from(reusedReceiptArtifacts).sort()));

    const receiptExecutionActivities = new Map(record.receipts.map((receipt) => [receipt.id, record.execution.filter((item) => item.receipt_ids.includes(receipt.id)).map((item) => item.activity).sort()]));
    const receiptExecutionBindingOk = new Map();
    record.receipts.forEach((receipt, index) => {
      const activitiesForReceipt = receiptExecutionActivities.get(receipt.id);
      if (activitiesForReceipt.length > 1) findings.push(finding("blocked", "RETURN_EXECUTION_RECEIPT_REUSED", `$.receipts.${index}`, "one receipt cannot serve as the execution record for multiple activities", activitiesForReceipt));
      const boundExecution = activitiesForReceipt.length === 1 ? record.execution.find((item) => item.activity === activitiesForReceipt[0]) : null;
      const boundToOneRanExecution = Boolean(boundExecution && boundExecution.status === "ran");
      receiptExecutionBindingOk.set(receipt.id, boundToOneRanExecution);
      if (receipt.status === "verified" && receipt.authority === "execution_record" && receipt.kind !== "adapter_receipt" && !boundToOneRanExecution) findings.push(finding("blocked", "RETURN_RECEIPT_EXECUTION_BINDING_INVALID", `$.receipts.${index}`, "a verified execution record must bind exactly one execution activity recorded as ran", activitiesForReceipt));
    });

    function receiptEffective(receiptId) {
      const receipt = indexes.receipts.get(receiptId);
      return Boolean(receipt
        && receipt.status === "verified"
        && receipt.authority === "execution_record"
        && receipt.kind !== "adapter_receipt"
        && !reusedReceiptArtifacts.has(receipt.artifact_id)
        && receiptExecutionBindingOk.get(receipt.id) === true
        && verifiedArtifacts.has(receipt.artifact_id)
        && indexes.artifacts.get(receipt.artifact_id).role === "receipt");
    }

    record.receipts.forEach((receipt, index) => {
      const receiptArtifact = indexes.artifacts.get(receipt.artifact_id);
      if (receiptArtifact && receiptArtifact.role !== "receipt") findings.push(finding("blocked", "RETURN_RECEIPT_ARTIFACT_ROLE_MISMATCH", `$.receipts.${index}.artifact_id`, "a receipt must bind an artifact with role receipt"));
      if (receipt.kind === "adapter_receipt" && receipt.authority === "execution_record") findings.push(finding("blocked", "RETURN_ADAPTER_AUTHORITY_OVERREACH", `$.receipts.${index}.authority`, "a submitted adapter receipt is non-admissive provenance, not independently established execution"));
      if (receipt.status !== "verified") findings.push(finding("review", "RETURN_RECEIPT_NOT_VERIFIED", `$.receipts.${index}.status`, "unverified or missing receipt metadata cannot support an execution claim", receipt.id));
      else if (receipt.authority === "execution_record" && !receiptEffective(receipt.id)) findings.push(finding("review", "RETURN_RECEIPT_UNVERIFIED_LOCALLY", `$.receipts.${index}`, "execution record is not backed by its locally hash-matched artifact", receipt.id));
    });

    const activities = record.execution.map((item) => item.activity);
    if (!sameSet(activities, CANONICAL_ACTIVITIES) || activities.length !== CANONICAL_ACTIVITIES.length) findings.push(finding("blocked", "RETURN_EXECUTION_ROSTER", "$.execution", "execution ledger must contain each canonical activity exactly once"));
    const executionByActivity = new Map(record.execution.map((item) => [item.activity, item]));
    const executionEffective = new Map();
    const receiptKinds = {
      web_research: "citation_access",
      independent_source_check: "citation_access",
      chatgpt_data_analysis: "chatgpt_tool_output",
      bsc_python_checker: "bsc_cli_output",
      external_proof_tool: "external_tool_transcript",
      empirical_test: "empirical_record",
    };
    record.execution.forEach((item, index) => {
      if (item.status === "file_read_only" && item.activity !== "chatgpt_data_analysis") findings.push(finding("blocked", "RETURN_FILE_READ_ACTIVITY_MISMATCH", `$.execution.${index}.status`, "file_read_only is valid only for ChatGPT attachment tooling"));
      if (item.activity === "proposed_computation" && ["ran", "file_read_only"].includes(item.status)) findings.push(finding("blocked", "RETURN_PROPOSAL_EXECUTION_MISMATCH", `$.execution.${index}.status`, "a proposed computation cannot simultaneously be recorded as executed"));
      if (["not_run", "not_applicable", "file_read_only"].includes(item.status) && (item.output_artifact_ids.length > 0 || item.receipt_ids.length > 0)) findings.push(finding("blocked", "RETURN_EXECUTION_STATUS_CONTRADICTION", `$.execution.${index}`, "an unexecuted or read-only activity cannot declare execution outputs or receipts"));
      if (item.status === "not_applicable" && NOT_APPLICABLE_REQUIRED_ACTIVITIES.has(item.activity)) findings.push(finding(
        "blocked",
        "RETURN_EXECUTION_NOT_APPLICABLE_MISUSED",
        `$.execution.${index}.status`,
        "canonical checker, proof-tool, and empirical activities must remain explicitly not_run when they were not executed",
        item.activity,
        "record not_run unless the activity was actually executed and can satisfy the execution-record requirements",
      ));
      if (item.status === "reported_but_unverified") findings.push(finding("review", "RETURN_EXECUTION_UNVERIFIED", `$.execution.${index}.status`, "reported execution lacks an adequate verified record", item.activity));
      if (item.status === "ran" && item.activity !== "model_reasoning") {
        const reportText = verifiedArtifactText.get(record.bindings.report_artifact_id);
        const supportArtifactIds = new Set(item.output_artifact_ids);
        item.receipt_ids.forEach((receiptId) => {
          const receipt = indexes.receipts.get(receiptId);
          if (receipt) supportArtifactIds.add(receipt.artifact_id);
        });
        const versionArtifactIds = Array.from(supportArtifactIds)
          .filter((artifactId) => (
            typeof item.version === "string"
            && (verifiedArtifactText.get(artifactId) || "").includes(item.version)
          ))
          .sort();
        if (versionArtifactIds.length === 0) findings.push(finding(
          "blocked",
          "RETURN_EXECUTION_VERSION_UNBOUND",
          `$.execution.${index}.version`,
          "a ran non-model execution version must appear in a verified bound execution output or receipt",
          {
            activity: item.activity,
            version: item.version,
            support_artifact_ids: Array.from(supportArtifactIds).sort(),
          },
        ));
        const supportReferences = Array.from(new Set(versionArtifactIds.flatMap((artifactId) => {
          const artifact = indexes.artifacts.get(artifactId);
          return artifact ? [artifactId, artifact.filename] : [];
        }))).sort();
        if (
          typeof reportText !== "string"
          || !supportReferences.some((reference) => reportText.includes(reference))
        ) findings.push(finding(
          "blocked",
          "RETURN_EXECUTION_OUTPUT_NOT_REFERENCED",
          `$.execution.${index}`,
          "the verified report must reference a bound version-bearing execution output or receipt instead of independently reproducing its version",
          {
            activity: item.activity,
            report_artifact_id: record.bindings.report_artifact_id,
            accepted_references: supportReferences,
          },
        ));
        if (item.activity === "chatgpt_data_analysis") {
          const runtimeArtifactIds = item.output_artifact_ids.filter((artifactId) => {
            const artifact = indexes.artifacts.get(artifactId);
            return artifact
              && artifact.role === "execution_output"
              && artifact.filename === "chatgpt_data_analysis_output.txt";
          }).sort();
          const runtimeText = runtimeArtifactIds.length === 1
            ? verifiedArtifactText.get(runtimeArtifactIds[0])
            : null;
          const runtimeArtifactId = runtimeArtifactIds.length === 1
            ? runtimeArtifactIds[0]
            : null;
          const runtimeLedgerRows = [];
          let runtimeLedgerMembersVerified = true;
          item.output_artifact_ids.forEach((artifactId) => {
            if (artifactId === runtimeArtifactId) return;
            const artifact = indexes.artifacts.get(artifactId);
            if (!artifact || ["request", "source"].includes(artifact.role)) return;
            const supplied = suppliedByName.get(artifact.filename);
            const bytes = supplied ? suppliedByteView(supplied.bytes) : null;
            if (!verifiedArtifacts.has(artifactId) || bytes === null) {
              runtimeLedgerMembersVerified = false;
              return;
            }
            runtimeLedgerRows.push({
              filename: artifact.filename,
              bytes: bytes.byteLength,
              sha256: artifact.sha256.slice("sha256:".length),
            });
          });
          const runtimeBindingOk = (
            typeof runtimeText === "string"
            && typeof item.version === "string"
            && runtimeLedgerMembersVerified
            && hasExactRuntimeBinding(runtimeText, item.version, runtimeLedgerRows)
          );
          if (!runtimeBindingOk) findings.push(finding(
            "blocked",
            "RETURN_DATA_ANALYSIS_RUNTIME_BINDING_INVALID",
            `$.execution.${index}`,
            "ChatGPT Data Analysis must bind one verified chatgpt_data_analysis_output.txt that projects the structured version as a session-reported, not independently authenticated runtime",
            {
              runtime_artifact_ids: runtimeArtifactIds,
              structured_version: item.version,
            },
          ));
        }
      }

      let effective = false;
      if (item.activity === "model_reasoning") effective = item.status === "ran";
      else if (item.status === "ran" && item.activity !== "proposed_computation") {
        const inputsOk = item.input_artifact_ids.length > 0 && item.input_artifact_ids.every((id) => verifiedArtifacts.has(id));
        const outputsOk = item.output_artifact_ids.length > 0 && item.output_artifact_ids.every((id) => verifiedArtifacts.has(id));
        const receiptsOk = item.receipt_ids.length > 0 && item.receipt_ids.every((id) => {
          const receipt = indexes.receipts.get(id);
          return receiptEffective(id) && receipt.kind === receiptKinds[item.activity];
        });
        const critical = ["bsc_python_checker", "external_proof_tool", "empirical_test"].includes(item.activity);
        const toolOk = typeof item.tool === "string" && item.tool.trim().length > 0 && typeof item.version === "string" && item.version.trim().length > 0;
        effective = inputsOk && toolOk && (critical ? (outputsOk && receiptsOk) : (outputsOk || receiptsOk));
        if (!effective) findings.push(finding("blocked", "RETURN_EXECUTION_RECORD_INADEQUATE", `$.execution.${index}`, "status ran requires bound inputs, a named versioned tool, and a verified output or admissible execution record", item.activity));
      }
      executionEffective.set(item.activity, effective);
    });

    const receiptScopeOk = new Map();
    record.receipts.forEach((receipt, index) => {
      const citingEvidence = record.evidence.filter((item) => item.receipt_ids.includes(receipt.id));
      if (citingEvidence.length === 0) {
        receiptScopeOk.set(receipt.id, true);
        return;
      }
      const evidenceClaims = Array.from(new Set(citingEvidence.flatMap((item) => item.claim_ids))).sort();
      const evidenceGates = Array.from(new Set(citingEvidence.flatMap((item) => item.gate_ids))).sort();
      const scopeOk = sameSet(receipt.claim_ids, evidenceClaims) && sameSet(receipt.gate_ids, evidenceGates);
      receiptScopeOk.set(receipt.id, scopeOk);
      if (!scopeOk) findings.push(finding("blocked", "RETURN_RECEIPT_SCOPE_MISMATCH", `$.receipts.${index}`, "receipt claim and gate scope must equal the union of evidence records that cite it", { declared_claim_ids: receipt.claim_ids, evidence_claim_ids: evidenceClaims, declared_gate_ids: receipt.gate_ids, evidence_gate_ids: evidenceGates }));
    });

    function evidenceBindings(item) {
      const artifactIds = new Set(item.artifact_ids);
      const receiptIds = new Set(item.receipt_ids);
      const requiredInputs = new Set([record.bindings.request_artifact_id]);
      item.claim_ids.forEach((claimId) => {
        const claim = indexes.claims.get(claimId);
        if (!claim) return;
        claim.source_ids.forEach((sourceId) => {
          const source = indexes.sources.get(sourceId);
          if (source && source.artifact_id !== null && verifiedArtifacts.has(source.artifact_id)) requiredInputs.add(source.artifact_id);
        });
      });
      const unboundActivities = item.execution_activities.filter((activity) => {
        const executionRecord = executionByActivity.get(activity);
        if (!executionRecord) return true;
        const outputBound = executionRecord.output_artifact_ids.some((id) => artifactIds.has(id));
        const receiptBound = executionRecord.receipt_ids.some((id) => receiptIds.has(id));
        if (["bsc_python_checker", "external_proof_tool", "empirical_test"].includes(activity)) return !(outputBound && receiptBound);
        if (activity === "model_reasoning") return !outputBound;
        return !(outputBound || receiptBound);
      });
      const inputUnboundActivities = item.execution_activities.filter((activity) => {
        const executionRecord = executionByActivity.get(activity);
        return !executionRecord || !Array.from(requiredInputs).every((id) => executionRecord.input_artifact_ids.includes(id));
      });
      const receiptFailures = {};
      item.receipt_ids.forEach((receiptId) => {
        const receipt = indexes.receipts.get(receiptId);
        if (!receipt) return;
        const failures = [];
        if (!artifactIds.has(receipt.artifact_id)) failures.push("receipt_artifact_not_bound_to_evidence");
        if (!item.claim_ids.every((id) => receipt.claim_ids.includes(id))) failures.push("claim_binding_missing");
        if (!item.gate_ids.every((id) => receipt.gate_ids.includes(id))) failures.push("gate_binding_missing");
        if (!item.execution_activities.some((activity) => executionByActivity.has(activity) && executionByActivity.get(activity).receipt_ids.includes(receiptId))) failures.push("execution_binding_missing");
        if (receiptScopeOk.get(receiptId) !== true) failures.push("receipt_scope_mismatch");
        if (failures.length > 0) receiptFailures[receiptId] = failures;
      });
      const supportOutputFailures = item.artifact_ids.filter((id) => (
        indexes.artifacts.has(id)
        && indexes.artifacts.get(id).role === "evidence"
        && !item.execution_activities.some((activity) => (
          executionByActivity.has(activity)
          && executionByActivity.get(activity).output_artifact_ids.includes(id)
        ))
      ));
      return {
        executionOk: unboundActivities.length === 0,
        inputOk: inputUnboundActivities.length === 0,
        receiptOk: Object.keys(receiptFailures).length === 0,
        supportOutputOk: supportOutputFailures.length === 0,
        receiptFailures,
        requiredInputs: Array.from(requiredInputs).sort(),
        supportOutputFailures,
        unboundActivities,
        inputUnboundActivities,
      };
    }

    function evidenceEffective(item) {
      const hasSupportArtifact = item.artifact_ids.some((id) => indexes.artifacts.has(id) && EVIDENCE_ARTIFACT_ROLES.has(indexes.artifacts.get(id).role));
      const artifactRolesOk = item.artifact_ids.every((id) => indexes.artifacts.has(id) && (EVIDENCE_ARTIFACT_ROLES.has(indexes.artifacts.get(id).role) || indexes.artifacts.get(id).role === "receipt"));
      const sourceScopeOk = item.artifact_ids.filter((id) => indexes.artifacts.has(id) && indexes.artifacts.get(id).role === "source").every((id) => {
        const matchingSources = new Set(record.sources.filter((source) => source.artifact_id === id).map((source) => source.id));
        return item.claim_ids.every((claimId) => indexes.claims.has(claimId) && indexes.claims.get(claimId).source_ids.some((sourceId) => matchingSources.has(sourceId)));
      });
      const outputScopeOk = item.artifact_ids.filter((id) => indexes.artifacts.has(id) && indexes.artifacts.get(id).role === "execution_output").every((id) => item.execution_activities.some((activity) => executionByActivity.has(activity) && executionByActivity.get(activity).output_artifact_ids.includes(id)));
      const bindings = evidenceBindings(item);
      return item.status === "verified"
        && item.artifact_ids.length > 0
        && item.execution_activities.length > 0
        && item.artifact_ids.every((id) => verifiedArtifacts.has(id))
        && item.receipt_ids.every(receiptEffective)
        && item.execution_activities.every((activity) => executionEffective.get(activity) === true)
        && bindings.executionOk
        && bindings.inputOk
        && bindings.receiptOk
        && bindings.supportOutputOk
        && artifactRolesOk
        && sourceScopeOk
        && outputScopeOk
        && hasSupportArtifact;
    }

    record.evidence.forEach((item, index) => {
      const invalidRoleArtifacts = item.artifact_ids.filter((id) => indexes.artifacts.has(id) && !EVIDENCE_ARTIFACT_ROLES.has(indexes.artifacts.get(id).role) && indexes.artifacts.get(id).role !== "receipt");
      const sourceScopeFailures = item.artifact_ids.filter((id) => indexes.artifacts.has(id) && indexes.artifacts.get(id).role === "source").filter((id) => {
        const matchingSources = new Set(record.sources.filter((source) => source.artifact_id === id).map((source) => source.id));
        return item.claim_ids.some((claimId) => !indexes.claims.has(claimId) || !indexes.claims.get(claimId).source_ids.some((sourceId) => matchingSources.has(sourceId)));
      });
      const outputScopeFailures = item.artifact_ids.filter((id) => indexes.artifacts.has(id) && indexes.artifacts.get(id).role === "execution_output").filter((id) => !item.execution_activities.some((activity) => executionByActivity.has(activity) && executionByActivity.get(activity).output_artifact_ids.includes(id)));
      const receiptOnly = item.artifact_ids.length > 0 && item.artifact_ids.every((id) => indexes.artifacts.has(id) && indexes.artifacts.get(id).role === "receipt");
      const bindings = evidenceBindings(item);
      if (item.status === "missing" && item.result === "pass") findings.push(finding("blocked", "RETURN_MISSING_EVIDENCE_PASS", `$.evidence.${index}`, "missing evidence cannot carry a passing result"));
      if (item.status !== "verified") findings.push(finding("review", "RETURN_EVIDENCE_UNVERIFIED", `$.evidence.${index}.status`, "unverified or missing evidence remains review-needed and cannot pass a fatal gate", item.status));
      if (item.status === "verified" && item.artifact_ids.length === 0) findings.push(finding("blocked", "RETURN_VERIFIED_EVIDENCE_UNBOUND", `$.evidence.${index}.artifact_ids`, "verified evidence requires at least one locally bound artifact"));
      if (invalidRoleArtifacts.length > 0) findings.push(finding("blocked", "RETURN_EVIDENCE_ARTIFACT_ROLE_INVALID", `$.evidence.${index}.artifact_ids`, "evidence artifacts may use only evidence, source, execution_output, or receipt roles", invalidRoleArtifacts));
      if (sourceScopeFailures.length > 0) findings.push(finding("blocked", "RETURN_EVIDENCE_SOURCE_SCOPE_MISMATCH", `$.evidence.${index}.artifact_ids`, "a source artifact used as evidence must be declared by every claim it supports", sourceScopeFailures));
      if (outputScopeFailures.length > 0) findings.push(finding("blocked", "RETURN_EVIDENCE_OUTPUT_SCOPE_MISMATCH", `$.evidence.${index}.artifact_ids`, "an execution-output artifact must be an output of an execution activity cited by the evidence", outputScopeFailures));
      if (item.status === "verified" && !bindings.supportOutputOk) findings.push(finding("blocked", "RETURN_EVIDENCE_SUPPORT_OUTPUT_MISMATCH", `$.evidence.${index}.artifact_ids`, "every artifact with role evidence must be an output of an execution activity cited by the evidence record", bindings.supportOutputFailures));
      if (item.status === "verified" && item.result === "pass" && receiptOnly) findings.push(finding("blocked", "RETURN_RECEIPT_ONLY_PROMOTION", `$.evidence.${index}`, "a receipt alone cannot promote a passing evidence record"));
      if (!bindings.executionOk) findings.push(finding("blocked", "RETURN_EVIDENCE_EXECUTION_BINDING_MISMATCH", `$.evidence.${index}.execution_activities`, "evidence cannot reuse an unrelated execution; each cited activity must bind this evidence's output or receipt", bindings.unboundActivities));
      if (!bindings.inputOk) findings.push(finding("blocked", "RETURN_EVIDENCE_EXECUTION_INPUT_UNBOUND", `$.evidence.${index}.execution_activities`, "each cited execution must bind the request and every locally available source for the evidence's claims", { activities: bindings.inputUnboundActivities, required_artifact_ids: bindings.requiredInputs }));
      if (!bindings.receiptOk) findings.push(finding("blocked", "RETURN_EVIDENCE_RECEIPT_BINDING_MISMATCH", `$.evidence.${index}.receipt_ids`, "a receipt used as evidence must bind its own bytes, the same claims and gates, and a cited execution", bindings.receiptFailures));
      const unsupportedActivities = item.execution_activities.filter((activity) => executionEffective.get(activity) !== true);
      if (unsupportedActivities.length > 0 && (item.result === "pass" || item.gate_ids.length > 0)) findings.push(finding("blocked", "RETURN_UNSUPPORTED_EXECUTION_EVIDENCE", `$.evidence.${index}.execution_activities`, "evidence relied on an activity that was not adequately executed and bound", unsupportedActivities));
      const dataAnalysis = executionByActivity.get("chatgpt_data_analysis");
      if (item.execution_activities.includes("chatgpt_data_analysis") && dataAnalysis && dataAnalysis.status === "file_read_only") findings.push(finding("blocked", "RETURN_FILE_READ_PROMOTION", `$.evidence.${index}.execution_activities`, "read-only file access cannot support evidence or a fatal gate"));
      if (item.status === "verified" && !evidenceEffective(item) && !findings.some((entry) => entry.path === `$.evidence.${index}` && entry.severity === "blocked")) findings.push(finding("review", "RETURN_EVIDENCE_UNVERIFIED_LOCALLY", `$.evidence.${index}`, "evidence marked verified is not fully supported by locally hash-matched artifacts and adequate execution records", item.id));
    });

    const derivedGateStates = new Map();
    record.fatal_gates.forEach((gate, index) => {
      const boundIds = new Set(gate.evidence_ids);
      record.evidence.filter((item) => item.gate_ids.includes(gate.id)).forEach((item) => boundIds.add(item.id));
      const bound = Array.from(boundIds).filter((id) => indexes.evidence.has(id)).map((id) => indexes.evidence.get(id));
      const verified = bound.filter(evidenceEffective);
      const hasPass = verified.some((item) => item.result === "pass");
      const hasFail = verified.some((item) => item.result === "fail");
      const hasInconclusive = verified.some((item) => item.result === "inconclusive");
      let derived = "unrun";
      if ((hasPass && hasFail) || (hasInconclusive && (hasPass || hasFail))) derived = "conflict";
      else if (hasFail) derived = "fail";
      else if (bound.length > 0 && verified.length === bound.length && verified.every((item) => item.result === "pass")) derived = "pass";
      derivedGateStates.set(gate.id, derived);
      if (gate.state !== derived) findings.push(finding("blocked", "RETURN_GATE_STATE_MISMATCH", `$.fatal_gates.${index}.state`, "declared gate state differs from all bound, locally effective evidence", { gate: gate.id, declared: gate.state, derived }));
      if (gate.state === "pass" && gate.obligation_ids.length > 0) findings.push(finding("blocked", "RETURN_PASSED_GATE_HAS_OPEN_OBLIGATION", `$.fatal_gates.${index}.obligation_ids`, "a passing fatal gate cannot retain an implicitly open obligation"));
      if (gate.state !== "pass" && gate.obligation_ids.length === 0) findings.push(finding("blocked", "RETURN_UNRESOLVED_GATE_OBLIGATION_OMITTED", `$.fatal_gates.${index}.obligation_ids`, "a nonpassing fatal gate must preserve at least one open obligation"));
    });
    const states = Array.from(derivedGateStates.values());
    let admission = "pass";
    if (states.includes("conflict")) admission = "conflict";
    else if (states.includes("fail")) admission = "fail";
    else if (states.length === 0 || states.includes("unrun")) admission = "unrun";
    if (record.summary_projection.admission !== admission) findings.push(finding("blocked", "RETURN_SUMMARY_ADMISSION_MISMATCH", "$.summary_projection.admission", "summary admission differs from the recomputed fatal-gate product", { declared: record.summary_projection.admission, derived: admission }));

    if (record.summary_projection.deployment_status === "admitted") findings.push(finding("blocked", "RETURN_DEPLOYMENT_AUTHORITY_MISSING", "$.summary_projection.deployment_status", "this non-admissive return format cannot grant deployment admission, even when its internal gate projection passes"));
    record.unresolved_obligations.forEach((obligation, index) => {
      const unownedGateIds = obligation.gate_ids.filter((gateId) => !obligation.claim_ids.some((claimId) => (
        indexes.claims.has(claimId) && indexes.claims.get(claimId).fatal_gate_ids.includes(gateId)
      )));
      const evidenceClaimScopeFailures = obligation.evidence_ids.filter((evidenceId) => (
        !indexes.evidence.has(evidenceId)
        || !indexes.evidence.get(evidenceId).claim_ids.some((claimId) => obligation.claim_ids.includes(claimId))
      ));
      const evidenceGateScopeFailures = obligation.evidence_ids.filter((evidenceId) => (
        !indexes.evidence.has(evidenceId)
        || !indexes.evidence.get(evidenceId).gate_ids.some((gateId) => obligation.gate_ids.includes(gateId))
      ));
      if (obligation.claim_ids.length === 0 || obligation.gate_ids.length === 0 || unownedGateIds.length > 0 || evidenceClaimScopeFailures.length > 0 || evidenceGateScopeFailures.length > 0) findings.push(finding(
        "blocked",
        "RETURN_OBLIGATION_SCOPE_MISMATCH",
        `$.unresolved_obligations.${index}`,
        "an unresolved obligation needs nonempty claim and gate scope, each gate owned by a listed claim, and each listed evidence record intersecting both scopes",
        {
          empty_claim_scope: obligation.claim_ids.length === 0,
          empty_gate_scope: obligation.gate_ids.length === 0,
          unowned_gate_ids: unownedGateIds,
          evidence_claim_scope_failures: evidenceClaimScopeFailures,
          evidence_gate_scope_failures: evidenceGateScopeFailures,
        },
      ));
      if (obligation.gate_ids.some((id) => derivedGateStates.get(id) === "pass")) findings.push(finding("blocked", "RETURN_OPEN_OBLIGATION_BEHIND_PASS", `$.unresolved_obligations.${index}`, "a fatal gate cannot pass while a bound obligation remains unresolved", obligation.id));
    });

    record.claims.forEach((claim, index) => {
      const claimEvidence = record.evidence.filter((item) => item.claim_ids.includes(claim.id));
      const effectivePass = claimEvidence.filter((item) => item.result === "pass" && evidenceEffective(item));
      const effectiveFail = claimEvidence.filter((item) => item.result === "fail" && evidenceEffective(item));
      const claimSources = claim.source_ids.filter((id) => indexes.sources.has(id)).map((id) => indexes.sources.get(id));
      const sourcesComplete = claim.source_ids.length > 0 && claimSources.length === claim.source_ids.length && claimSources.every((source) => source.coverage_state === "fully_inspected");
      const sourceBytesVerified = sourcesComplete && claimSources.every((source) => source.artifact_id !== null && verifiedArtifacts.has(source.artifact_id));
      const effectiveNonpass = claimEvidence
        .filter((item) => ["fail", "inconclusive"].includes(item.result) && evidenceEffective(item))
        .map((item) => ({ id: item.id, result: item.result }));
      if (["proven", "strongly_supported"].includes(claim.research_verdict) && effectiveNonpass.length > 0) findings.push(finding(
        "blocked",
        "RETURN_HIGH_VERDICT_EVIDENCE_CONFLICT",
        `$.claims.${index}.research_verdict`,
        "a high verdict cannot coexist with direct locally effective failing or inconclusive evidence",
        { claim_id: claim.id, evidence: effectiveNonpass },
        "resolve the contradictory or inconclusive evidence or demote the verdict; do not remove a valid negative result",
      ));
      if (claim.research_verdict === "proven") {
        const gatesPass = claim.fatal_gate_ids.length > 0 && claim.fatal_gate_ids.every((id) => derivedGateStates.get(id) === "pass");
        const nonReceiptEvidence = effectivePass.some((item) => item.artifact_ids.some((id) => indexes.artifacts.has(id) && indexes.artifacts.get(id).role === "evidence"));
        const openObligations = record.unresolved_obligations.filter((item) => item.claim_ids.includes(claim.id) || item.gate_ids.some((id) => claim.fatal_gate_ids.includes(id)));
        const unsupportedDependencies = claim.depends_on.filter((id) => indexes.claims.has(id) && indexes.claims.get(id).research_verdict !== "proven");
        if (!sourcesComplete) findings.push(finding("blocked", "RETURN_PROVEN_WITH_SOURCE_GAP", `$.claims.${index}.research_verdict`, "proven requires complete coverage of every source bound to the claim"));
        if (!sourceBytesVerified) findings.push(finding("blocked", "RETURN_PROVEN_SOURCE_BYTES_UNVERIFIED", `$.claims.${index}.research_verdict`, "proven requires locally hash-matched bytes for every bound source"));
        if (!gatesPass) findings.push(finding("blocked", "RETURN_PROVEN_WITH_BLOCKED_GATE", `$.claims.${index}.research_verdict`, "proven requires every bound fatal gate to recompute as pass"));
        if (!nonReceiptEvidence) findings.push(finding("blocked", "RETURN_RECEIPT_ONLY_PROOF", `$.claims.${index}.research_verdict`, "a receipt alone cannot support proven; locally bound non-receipt proof evidence is required"));
        if (openObligations.length > 0) findings.push(finding("blocked", "RETURN_PROVEN_WITH_OPEN_OBLIGATION", `$.claims.${index}.research_verdict`, "proven cannot retain an unresolved obligation", openObligations.map((item) => item.id)));
        if (unsupportedDependencies.length > 0) findings.push(finding("blocked", "RETURN_PROVEN_DEPENDENCY_UNCLOSED", `$.claims.${index}.depends_on`, "proven cannot depend on a claim not itself recorded as proven", unsupportedDependencies));
      }
      if (claim.research_verdict === "strongly_supported") {
        const gatesPass = claim.fatal_gate_ids.length > 0 && claim.fatal_gate_ids.every((id) => derivedGateStates.get(id) === "pass");
        const unsupportedDependencies = claim.depends_on.filter((id) => indexes.claims.has(id) && !["proven", "strongly_supported"].includes(indexes.claims.get(id).research_verdict));
        if (!sourcesComplete) findings.push(finding("blocked", "RETURN_STRONGLY_SUPPORTED_WITH_SOURCE_GAP", `$.claims.${index}.research_verdict`, "strongly_supported requires complete coverage of every bound source"));
        if (!sourceBytesVerified) findings.push(finding("blocked", "RETURN_STRONGLY_SUPPORTED_SOURCE_BYTES_UNVERIFIED", `$.claims.${index}.research_verdict`, "strongly_supported requires locally hash-matched bytes for every bound source"));
        if (effectivePass.length === 0) findings.push(finding("blocked", "RETURN_STRONGLY_SUPPORTED_WITHOUT_EVIDENCE", `$.claims.${index}.research_verdict`, "strongly_supported requires direct, locally effective passing evidence"));
        if (!gatesPass) findings.push(finding("blocked", "RETURN_STRONGLY_SUPPORTED_WITH_BLOCKED_GATE", `$.claims.${index}.research_verdict`, "strongly_supported requires every bound fatal gate to recompute as pass"));
        if (unsupportedDependencies.length > 0) findings.push(finding("blocked", "RETURN_STRONGLY_SUPPORTED_DEPENDENCY_UNCLOSED", `$.claims.${index}.depends_on`, "strongly_supported cannot depend on a claim below strongly_supported", unsupportedDependencies));
      }
      if (claim.research_verdict === "refuted") {
        if (!sourcesComplete) findings.push(finding("blocked", "RETURN_REFUTED_WITH_SOURCE_GAP", `$.claims.${index}.research_verdict`, "refuted requires complete coverage of every source that defines the claim and counterexample scope"));
        if (!sourceBytesVerified) findings.push(finding("blocked", "RETURN_REFUTED_SOURCE_BYTES_UNVERIFIED", `$.claims.${index}.research_verdict`, "refuted requires locally hash-matched bytes for every bound source"));
        if (effectiveFail.length === 0) findings.push(finding("blocked", "RETURN_REFUTED_WITHOUT_COUNTEREVIDENCE", `$.claims.${index}.research_verdict`, "refuted requires direct, locally effective failing evidence; missing material alone is not refutation"));
      }
    });

    findings.push(finding("info", "RETURN_DESK_NON_ADMISSIVE", "$.authority", "The Return Desk checks envelope consistency and local byte bindings only; it does not establish truth, proof, execution beyond bound records, citation validity, or deployment permission."));
    if (!findings.some((item) => item.severity === "blocked")) findings.push(finding("info", "RETURN_INTERNALLY_CONSISTENT", "$", "The submitted projections, ledgers, references, and inspected local byte bindings are internally consistent within the implemented checks."));
    const outcome = findings.some((item) => item.severity === "blocked")
      ? "blocked"
      : (findings.some((item) => item.severity === "review") ? "needs_review" : "consistent");
    return {
      inspection_version: contract.version,
      authority: contract.authority,
      outcome,
      checks: { run: checksRun, not_run: checksNotRun },
      findings,
      caveat: "Internal consistency is not truth, proof, admissibility, checker execution, citation verification, or deployment approval.",
    };
  }

  return {
    CANONICAL_ACTIVITIES,
    MAX_RETURN_JSON_BYTES,
    StrictJsonError,
    inspectReturn,
    parseStrictJson,
    utf8ByteLengthBounded,
    validateSchema,
  };
});
