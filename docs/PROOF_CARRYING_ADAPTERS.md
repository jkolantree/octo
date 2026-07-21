# Proof-carrying adapter boundary

This document defines the first post-`v0.3.0-alpha.2` bridge toward Lean 4,
SMT-LIB, and rigorous interval verification. The bridge is deliberately
non-admissive: it can bind a receipt to local bytes and reject inconsistent
claims about an execution, but it cannot yet promote a mathematical claim.

## The object being checked

An adapter receipt is a finite record

\[
R=(J,S,E,A,C,V,o),
\]

where `J` is the hashed adapter job, `S` the hashed source subject, `E` the
hashed execution environment, `A` the adapter/tool identity and transcript,
`C` the certificate, `V` the replay/checker declaration, and `o` the adapter
outcome. Every referenced file must be below the receipt directory and must
match its non-placeholder SHA-256 digest.

The command

```bash
python run_audit.py adapter path/to/receipt.json
```

checks the released schema, safe paths, artifact hashes, kind/format pairing,
exit/result consistency, checker replay declaration, and the declared
assumption allow-list. A clean receipt returns a warning rather than theorem
authority.

## Trust boundary

The receipt is supplied by the submitter. Consequently, fields such as
`replay_verified` are assertions, not independently established facts. The
current command therefore always emits `ADAPTER_RECEIPT_NON_ADMISSIVE`.
Neither `outcome: pass` nor a zero process exit can satisfy a proof gate.

Admission requires a later supervised runner to:

1. resolve an adapter from a versioned allow-list;
2. verify its executable and environment hashes;
3. invoke it without a shell, using a fixed argument vector;
4. enforce time, memory, file, process, and output limits;
5. capture immutable stdout, stderr, source, job, and environment artifacts;
6. replay the certificate with the declared checker;
7. construct the receipt from observed events rather than submitted fields;
8. bind the checked obligation to the exact claim and hypotheses.

Until all eight steps execute inside the engine, the receipt is provenance,
not proof.

## Adapter-specific gates

### Lean 4

A passing receipt uses `result_token: accepted` and certificate format
`lean4-kernel-check`. The replay must report every axiom used by the target
declaration. Observed axioms outside the explicit allow-list block the receipt.
The same pinned Lean kernel may elaborate and replay the declaration, although
an independently built kernel is a stronger future profile. `sorry`, generated
axioms, and an unreported target declaration must become fatal supervised-run
conditions.

### SMT-LIB 2

A passing receipt means that the registered negated obligation produced
`result_token: unsat`. Solver output alone is insufficient. The certificate
must be Alethe, LFSC, or DRAT and must replay under an independent checker.
A `sat` model is only a candidate counterexample until both the model and the
claim-to-formula translation are checked.

### Interval arithmetic

A passing receipt uses `result_token: enclosed` and format
`exact-interval-replay`. A future runner must record the directed-rounding
backend, precision schedule, subdivision tree, and exact rational endpoint
serialization. An independent replay checker must verify every containment
step. Decimal display values and ordinary floating-point tolerances are not
certificates.

## Failure and attack cases

The initial regression suite covers:

- certificate or transcript hash substitution;
- passing outcome paired with a nonzero exit;
- result tokens inconsistent with the adapter kind;
- SMT or interval passes without an independent checker;
- assumptions observed outside the declared policy;
- path traversal and symlink escape;
- attempts to assign admission authority to a preview receipt.

## Next implementation increments

1. Add a no-shell supervised process runner and an allow-listed adapter
   registry.
2. Implement a Lean target/axiom reporter and preserve its generated source.
3. Implement cvc5 Alethe production plus a separately pinned proof checker.
4. Define an exact interval-certificate grammar and independent rational replay.
5. Bind successful supervised receipts into the theorem-support transition,
   with Null-Discrimination fixtures for forged, truncated, and cross-claim
   certificates.
