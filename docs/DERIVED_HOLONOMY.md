# Exact derived holonomy

The `holonomy` route audits whether two declared transport paths agree at the level the claim actually requires. It supplements the `complex` route; it does not change that route's strict square-holonomy behavior.

## Why there are three levels

For two chain-map paths `f,g: C -> D`, define `Omega = f - g`.

- **Strict:** require `Omega = 0` degree by degree.
- **Derived:** require degree-`+1` maps `h_n` satisfying `Omega_n = dD_(n+1) h_n + h_(n-1) dC_n`. The paths may differ on representatives while inducing the same homology map.
- **Observed-derived:** require the same equation after an explicit observation projection `pi: D -> O`. This permits only discrepancies killed by a declared lawful quotient.

The derived equivalence is implemented only for bounded finite-dimensional complexes over the exact rational field `Q`. The field hypothesis is essential; the engine rejects other coefficient declarations rather than extending the theorem to arbitrary rings.

## Fail-closed execution order

For each document the checker:

1. validates matrix shapes and `d^2 = 0`;
2. replays each semantic-basis digest;
3. verifies every referenced edge satisfies `dT = Td`;
4. composes arbitrary-length paths and checks common endpoints;
5. composes and records raw strict defects, including for illegal edges when the matrices remain composable;
6. constructs the exact homotopy system only when all path edges are lawful;
7. for observed-derived relations, verifies that the projection is a chain map and degreewise surjective;
8. solves and replays the required rational systems.

A non-chain-map edge produces `HOLONOMY_EDGE_ILLEGAL` and, for a derived relation, `HOLONOMY_DERIVED_NOT_CONSTRUCTED`. Its raw presentation-level strict defect is still reported when the matrices compose. No derived class is fabricated from an illegal edge.

## Certificates

The homotopy equation is flattened in deterministic degree, target-basis, source-basis order as `A h = omega`.

A pass finding includes:

- `kind: exact_solution`;
- the rational solution vector;
- equation and variable coordinate ledgers;
- degreewise homotopy matrices;
- an exact zero residual.

A failure includes a rational vector `y` with `y^T A = 0` and `y^T omega != 0`. It also includes the exact least-squares vector `h_*`, residual `r = omega - A h_*`, the replayed condition `A^T r = 0`, and `eta_squared = r^T r > 0`.

The solver uses rational row operations only and bounds equations, variables, coefficient cells, input rational sizes, and intermediate bit growth. Path composition has a separate document-wide budget of 1,000,000 scalar products, checks every intermediate numerator and denominator against the 8,192-bit ceiling, and memoizes repeated path tuples.

`eta_squared` uses the ordinary Euclidean norm in the declared coordinate bases. It is exact for those registered bases, but it is not a canonical basis-free magnitude and can change under basis rescaling.

## Lawful observation projection

An observed-derived relation names a transport `D -> O`. The engine requires it to be:

- shape-correct;
- a chain map;
- surjective in every declared degree.

These checks certify that its kernel is a subcomplex and that `O` is the represented finite quotient. They do not prove that the projection is a complete or scientifically justified observation model. The route does not yet accept a separately declared inclusion `N -> D` and prove `ker(pi) = image(N)`.

## Semantic basis binding

Each basis vector carries a label, a meaning string, and the SHA-256 digest of the UTF-8 meaning bytes. The checker requires exact degree and dimension coverage and replays every digest.

This prevents an unrecorded direct-sum component from entering silently. It does not establish that the meaning string faithfully represents an external scientific obligation; that remains a review obligation.

## Run the known-answer cases

From the repository root:

```bash
python run_audit.py holonomy examples/holonomy_contractible_derived_pass.json
python run_audit.py holonomy examples/holonomy_homology_obstruction.json
python run_audit.py holonomy examples/holonomy_observed_quotient_pass.json
python run_audit.py holonomy examples/holonomy_non_chain_map.json
```

The first case fails strict equality but passes with an explicit contraction. The second emits a dual homology obstruction. The third preserves the pre-observation failure as a warning and passes only after the declared quotient. The fourth blocks before derived evaluation.

The public contract is [`derived-holonomy-v0.1.schema.json`](../schemas/derived-holonomy-v0.1.schema.json). The preserved research packet and its epistemic limits are under [`research/derived-witnessed-descent/`](../research/derived-witnessed-descent/README.md).

## Current boundary

The route does not yet implement invariant naturality, higher coherent homotopies, a query-holonomy Galois search, physical truth validation, or proof-assistant certification. A clear result establishes only the finite equations and bindings actually checked.
