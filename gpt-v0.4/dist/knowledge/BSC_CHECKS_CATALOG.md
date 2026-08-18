# BSC Implemented Checks Catalog

**Engine dependency:** `v0.3.0-alpha.20` (unchanged)

This is a generated projection of `checks_catalog.json`, the authority for implemented check scope. It describes available routes; it does not assert that any route ran for the current user.

## `lint` — claim-manifest-lint

- **Accepted input:** A UTF-8 JSON claim manifest accepted by the registered v0.3, v0.4, or v0.5 manifest schema.
- **Establishes:** Schema conformance and the implemented structural consistency checks for the submitted manifest.
- **Does not establish:** Truth of the research claim, authenticity of cited evidence, or deployment authority.
- **Required executor:** BSC Python CLI v0.3.0-alpha.20
- **Execution evidence required:** The exact input identity plus retained structured CLI output, engine version, command, and exit code.
- **Known limitations:** Only registered fields and predicates are checked; unknown scientific semantics are outside the route.

## `audit` — claim-manifest-audit

- **Accepted input:** A UTF-8 JSON claim manifest accepted by the registered manifest schemas, including its declared dependencies and evidence records.
- **Establishes:** The results of registered manifest, gate-product, and domain checks that actually ran.
- **Does not establish:** A human research verdict, external evidence authenticity, complete coverage of unregistered domains, or permission to deploy.
- **Required executor:** BSC Python CLI v0.3.0-alpha.20
- **Execution evidence required:** The exact input identity and complete structured output listing checks run and not run, findings, decision, version, and exit code.
- **Known limitations:** A zero exit code means no blocking implemented finding; it is not a scientific truth badge.

## `complex` — exact-certificate-complex

- **Accepted input:** A complex-v0.3 finite rational chain-complex and transport record.
- **Establishes:** The implemented exact finite matrix equations, including declared differential and transport obligations.
- **Does not establish:** External meaning of the bases, source authenticity, or global path independence beyond the submitted relations.
- **Required executor:** BSC Python CLI v0.3.0-alpha.20
- **Execution evidence required:** A fresh structured result bound to the exact complex record and engine version.
- **Known limitations:** Finite rational algebra only; semantic interpretation remains an external premise.

## `observe` — finite-observation-descent

- **Accepted input:** An observation-v0.3 record of finite states, declared relation pairs, and total queries.
- **Establishes:** Whether each submitted query is constant on the submitted relation classes.
- **Does not establish:** Measurement validity, completeness of the state space, causation, or population generalization.
- **Required executor:** BSC Python CLI v0.3.0-alpha.20
- **Execution evidence required:** Structured output bound to the exact observation record, command, version, and exit code.
- **Known limitations:** The result is only as complete as the finite states, relations, and queries supplied.

## `atomic` — finite-atomic-modulus

- **Accepted input:** An atomic-modulus-v0.3 finite certificate record.
- **Establishes:** The implemented finite arithmetic conditions in the submitted concentration-modulus record.
- **Does not establish:** The full measure-theoretic theorem, authenticity of an external proof, or facts outside the finite record.
- **Required executor:** BSC Python CLI v0.3.0-alpha.20
- **Execution evidence required:** Structured output bound to the exact certificate bytes and engine version.
- **Known limitations:** The finite replay and the nearby manual theorem are separate authority lanes.

## `defect` — affine-defect-propagation

- **Accepted input:** A defect-v0.3 record of declared nonnegative rational affine upper bounds.
- **Establishes:** Exact propagation and comparison of the submitted upper bounds.
- **Does not establish:** Actual error, equality with a bound, source-state authenticity, or a physical tolerance violation.
- **Required executor:** BSC Python CLI v0.3.0-alpha.20
- **Execution evidence required:** Structured output bound to the exact defect record and engine version.
- **Known limitations:** An upper enclosure is not an observed or exact value; missing ports are not zero.

## `adapter` — adapter-receipt-inspection

- **Accepted input:** An adapter-receipt-v0.1 provenance record and any locally available referenced bytes.
- **Establishes:** Implemented receipt structure and available local binding consistency.
- **Does not establish:** That an external prover ran, that its result is valid, or that the research claim is proved.
- **Required executor:** BSC Python CLI v0.3.0-alpha.20
- **Execution evidence required:** The exact receipt, available referenced bytes, and retained structured inspection output.
- **Known limitations:** This route is non-admissive provenance inspection; unavailable external execution stays unverified.

## `holonomy` — exact-derived-holonomy

- **Accepted input:** A derived-holonomy-v0.1 or v0.2 bounded finite-dimensional rational record.
- **Establishes:** The implemented strict, derived, observed-derived, or exact-kernel finite path comparison selected by the record.
- **Does not establish:** External scientific interpretation, source authenticity, or claims outside the declared finite complexes and maps.
- **Required executor:** BSC Python CLI v0.3.0-alpha.20
- **Execution evidence required:** A fresh structured result bound to the exact record, mode, command, and engine version.
- **Known limitations:** Resource-bounded exact rational linear algebra; mode-specific fields are closed and nontransferable.

## `theorem` — exact-polynomial-identity

- **Accepted input:** A theorem-certificate-v0.1 expression in the closed rational-polynomial AST and resource envelope.
- **Establishes:** Canonical normalization equality of the submitted formal polynomial expressions.
- **Does not establish:** Nearby prose, an unencoded theorem, external proof identity, empirical truth, or deployment authority.
- **Required executor:** BSC Python CLI v0.3.0-alpha.20
- **Execution evidence required:** The exact certificate and retained structured replay output with engine version and exit code.
- **Known limitations:** Authority is confined to the encoded closed language and exact statement.

## `census` — finite-census-affine-bound

- **Accepted input:** A finite-census-certificate-v0.1 complete-frame record with rational enclosures, affine bound, and guard band.
- **Establishes:** The exact conditional affine-bound proposition over the declared finite frame and enclosures.
- **Does not establish:** The four external premise identities, causation, population generalization, independent replication, or deployment authority.
- **Required executor:** BSC Python CLI v0.3.0-alpha.20
- **Execution evidence required:** The exact certificate plus retained structured replay output, command, version, and exit code.
- **Known limitations:** A conditional observational bridge only; every external premise remains separately typed.

## `return-desk` — audit-return-inspection

- **Accepted input:** An audit-return-v0.1 envelope and the locally available artifacts it identifies.
- **Establishes:** Implemented internal consistency and available local byte-binding checks for the returned envelope.
- **Does not establish:** Research truth, proof validity, citation authenticity, external execution, transport completeness, or deployment authority.
- **Required executor:** BSC Python CLI v0.3.0-alpha.20
- **Execution evidence required:** The exact envelope, available artifacts, and retained structured inspection output.
- **Known limitations:** Non-admissive review only; missing artifacts produce review limits rather than invented verification.
