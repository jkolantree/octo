# Verification packet

This directory contains three dependency-free reproductions for the companion note [Formal Verification and Prime-Block Obstruction](../Formal_Verification_and_Prime_Block_Obstruction.md).

Run from `output/research`:

```bash
python3 verification/derived_holonomy_exact.py
python3 verification/shifted_ladder_reproduce.py
python3 verification/prime_block_obstruction.py
python3 -m py_compile verification/*.py
```

## Epistemic scope

| Route | Arithmetic | What the script establishes | What establishes the universal statement |
|---|---|---|---|
| Derived holonomy | Exact `fractions.Fraction` | Exact pass/fail certificates, four fixtures, 153 exhaustive small cases | Constructive contraction proof in the note |
| Shifted ladder | Exact \(\mathbb Q(i)\) identity plus 80-digit Decimal evaluation | Resolvent coefficient replay, trace-norm tails, Gaussian and phase-sensitive distribution pairings | \(k^{-2}\) majorant and Poisson summation in the note |
| Prime blocks | Exact rational polynomial differentiation plus finite prime enumeration | Uniform jet annihilation and prime-cutoff growth | Trace-norm additivity, the resolvent power identity, and Euler's prime-reciprocal divergence |

No theorem-prover kernel is installed in this environment. The derived theorem is formally proved on paper and its finite certificates are checked exactly; it is not represented as Lean/Coq/Isabelle-kernel verified.

The generated JSON reports use stable key ordering and end with a newline. Each script prints the SHA-256 of its report after a successful run.
