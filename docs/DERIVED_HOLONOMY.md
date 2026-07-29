# Exact derived holonomy

The `holonomy` route audits whether two declared transport paths agree at the level the claim actually requires. It supplements the `complex` route; it does not change that route's strict square-holonomy behavior.

## Why there are four levels

For two chain-map paths `f,g: C -> D`, define `Omega = f - g`.

- **Strict:** require `Omega = 0` degree by degree.
- **Derived:** require degree-`+1` maps `h_n` satisfying `Omega_n = dD_(n+1) h_n + h_(n-1) dC_n`. The paths may differ on representatives while inducing the same homology map.
- **Observed-derived:** require the same equation after an explicit observation projection `pi: D -> O`. This permits only discrepancies killed by a declared lawful quotient.
- **Observed-derived with exact kernel:** additionally declare an inclusion `i: N -> D` and prove that `0 -> N -> D -> O -> 0` is degreewise exact. This certifies that the projection kills exactly the declared null subcomplex, not an unnamed larger space.

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
8. for v0.2 exact-kernel relations, verifies that the declared inclusion and projection form a short exact sequence of complexes;
9. solves and replays the required rational systems.

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

These checks certify that its kernel is a subcomplex and that `O` is the represented finite quotient. They do not prove that the projection is a complete or scientifically justified observation model.

The v0.2 `observed_derived_exact_kernel` route additionally names a chain-map inclusion `i: N -> D` and checks, in every degree:

```text
rank(i_n) = dim(N_n)
rank(pi_n) = dim(O_n)
pi_n i_n = 0
dim(N_n) + dim(O_n) = dim(D_n)
```

Over `Q`, these equations imply `image(i_n) = ker(pi_n)`. Together with the two chain-map checks, they certify a short exact sequence of the supplied complexes. A zero projection can therefore no longer erase an undeclared extra direction while satisfying this stronger route.

Legacy v0.1 `observed_derived` records retain their narrower meaning: they certify the projection's actual kernel but do not bind that kernel to a separately declared null complex.

## Semantic basis binding

Each basis vector carries a label, a meaning string, and the SHA-256 digest of the UTF-8 meaning bytes. The checker requires exact degree and dimension coverage and replays every digest.

This prevents an unrecorded direct-sum component from entering silently. It does not establish that the meaning string faithfully represents an external scientific obligation; that remains a review obligation.

## Run the known-answer cases

From the repository root:

```bash
python run_audit.py holonomy examples/holonomy_contractible_derived_pass.json
python run_audit.py holonomy examples/holonomy_homology_obstruction.json
python run_audit.py holonomy examples/holonomy_observed_quotient_pass.json
python run_audit.py holonomy examples/holonomy_observed_exact_kernel_pass.json
python run_audit.py holonomy examples/holonomy_observed_exact_kernel_overquotient.json
python run_audit.py holonomy examples/holonomy_non_chain_map.json
```

The first case fails strict equality but passes with an explicit contraction. The second emits a dual homology obstruction. The legacy quotient case preserves the pre-observation failure as a warning and passes only after its declared projection. The positive v0.2 case also emits `OBSERVATION_KERNEL_SEQUENCE_EXACT`; the over-quotient case blocks because the declared null image is smaller than the projection kernel. The final case blocks before derived evaluation. Every otherwise successful case also emits `HOLONOMY_EXTERNAL_INTERPRETATION_NON_ADMISSIBLE` with `scientific_truth` and `source_authenticity` fixed at `not_established`.

The current public contract is [`derived-holonomy-v0.2.schema.json`](../schemas/derived-holonomy-v0.2.schema.json). Runtime validation dispatches legacy `holonomy_version: 0.1.0` records to the immutable [`derived-holonomy-v0.1.schema.json`](../schemas/derived-holonomy-v0.1.schema.json), so new v0.2 fields cannot be smuggled into the older closed contract and silently ignored. The v0.2 relation is discriminated by mode: `observation_projection` and `kernel_inclusion` are forbidden on `strict` and `derived`, preventing stronger-looking but unchecked declarations. The preserved research packet and its epistemic limits are under [`research/derived-witnessed-descent/`](../research/derived-witnessed-descent/README.md).

## Current boundary

The route does not implement invariant naturality, higher coherent homotopies, a query-holonomy Galois search, physical truth validation, or proof-assistant certification. A clear result establishes only the finite equations and bindings actually checked. The explicit non-admissive warning is permanent output semantics, not an invitation to infer that an external declaration is true or false.
