# Human Audit Worksheet

Complete this before asking whether a claim is true. Ordinary language is enough. A blank field is useful evidence that an obligation remains unresolved.

## 1. Exact claim

Write one sentence that could be false. Avoid “may,” “suggests,” “connected to,” and “explains” unless those terms have an explicit test.

**Claim:**

## 2. Scope

Where, when, and for whom is the claim supposed to hold? List exclusions and domain boundaries.

**Scope:**

## 3. Objects and types

List the inputs, states, parameters, maps, operators, datasets, or physical systems. Give each a domain, codomain, unit, or data type where applicable.

**Objects:**

## 4. Observation

What is actually observed? Which instrument, measurement rule, data filter, human report, or software process produces it? What was available at decision time?

**Observation process:**

## 5. Lost information

Which distinct underlying states can look identical after observation, averaging, anonymization, phase loss, projection, or coarse-graining?

**Known identifications:**

## 6. Baseline and nulls

What ordinary explanation or simpler method must the proposal beat? Which nuisance processes could imitate the result? Did candidate and null receive comparable search exposure?

**Baseline and null family:**

## 7. Evidence and source coverage

List the actual proof, data, code, calibration, certificate, and source location. Separate direct evidence from inference, analogy, and intuition. Record material not inspected.

**Evidence:**

**Not inspected or unavailable:**

## 8. Independent hard gates

What must pass before promotion? Use separate yes/no gates rather than one blended score. Mark each `unrun`, `pass`, `fail`, or `conflict`.

**Hard gates:**

## 9. Kill and demotion conditions

What specific result would refute, narrow, sandbox, demote, or retire the claim? Who owns that decision?

**Conditions and owner:**

## 10. Boundary and adversarial cases

Check zero, empty, singular, infinite, missing-data, path-order, coordinate, alternate-instrument, out-of-distribution, malicious, and resource-exhaustion cases.

**Cases and outcomes:**

## 11. Reproduction and privacy

What files, hashes, versions, seeds, instructions, and negative results would a stranger need? Which material must remain private, and what lawful audit substitute is available?

**Preservation plan:**

## 12. Current status

Choose each coordinate independently.

**Research verdict:** Proven / Strongly supported / Plausible but unresolved / Refuted / Ill-posed / Outside current knowledge

**Evidence maturity:** Declared / Structurally checked / Empirically passed / Externally replicated

**Deployment:** Research-only / Sandboxed / Candidate / Admitted / Retired

**Checks not run:**

## Final two sentences

**Strongest surviving statement:**

**Highest-leverage next test:**

No worksheet, model, or checker grants deployment authority. Preserve the reviewer’s name or accountable role beside the completed audit.
