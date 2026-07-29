# Audit Descent Mathematics

## 1. Certificate complexes

At each scientific context `c` place a finite chain complex over a computable exact field:

\[
\cdots\longrightarrow K_2(c)\xrightarrow{\partial^c_2}K_1(c)
\xrightarrow{\partial^c_1}K_0(c),
\qquad \partial^c_{n-1}\partial^c_n=0.
\]

The degree convention is application-specific, but must be fixed in the manifest. A typical encoding places primitive evidence at high degree, derived obligations below it, and the promoted claim at degree zero. If the basis and differentials have been given a valid obligation semantics, homology records obligations that are closed under the declared rules but not discharged by available certificates. The chain complex alone does not validate that external semantics.

## 2. Certificate-interchange curvature

A context change `alpha: c -> d` supplies graded linear maps

\[
T_{\alpha,n}:K_n(c)\to K_n(d).
\]

### Definition

The certificate-interchange defect is

\[
\Theta_{\alpha,n}
=\partial^d_nT_{\alpha,n}-T_{\alpha,n-1}\partial^c_n.
\]

It is zero exactly when `T_alpha` is a chain map.

### Theorem 1 — lawful promotion transport

If every `Theta_alpha,n` vanishes, then transport sends cycles to cycles and boundaries to boundaries, and therefore induces maps

\[
H_n(T_\alpha):H_n(K(c))\to H_n(K(d)).
\]

If `Theta` is nonzero, a nonzero column is a finite exact basis-vector witness to failure of the declared matrix chain-map equation. It represents a scientific obligation only when the chosen basis and differentials have independently validated obligation semantics.

**Proof.** For a cycle `z`, `partial z=0`, so `partial Tz=T partial z=0`. For a boundary `z=partial w`, `Tz=T partial w=partial Tw`. The witness statement follows by evaluating the defect on a standard basis vector corresponding to a nonzero column. QED.

### Theorem 2 — derivation law

For composable context transports `T_alpha` and `T_beta`,

\[
\Theta_{\beta\alpha}
=\Theta_\beta T_\alpha+T_\beta\Theta_\alpha.
\]

**Proof.** Expand `partial T_beta T_alpha - T_beta T_alpha partial` and add/subtract `T_beta partial T_alpha`. QED.

This law localizes composite failure: a broken long transport must inherit defect from at least one stage unless defects cancel, and any such cancellation is itself a certificate obligation rather than an excuse to average.

## 3. Path holonomy

For a square with two composite transports from `c` to `d`, define

\[
\Omega=T_{q|p}T_p-T_{p|q}T_q.
\]

`Omega = 0` is exact equality of the two declared composite paths in this square. It is not, by itself, global path independence: that requires a presentation whose checked squares generate every relevant path relation. The square test specializes to:

- scale-transfer curvature;
- order dependence when adjoining primes;
- change of instrument followed by quotient versus quotient followed by instrument change;
- boundary completion followed by inference versus inference followed by completion.

No norm is silently chosen. Approximate mode must declare a norm, domain, and tolerance separately.

## 4. Observation-descent Galois connection

Let `Rel(X)` be relations on a state set `X` ordered by inclusion. Fix a set `Q_0` of total queries, where each `q in Q_0` has a declared codomain. For a family of queries `Q subseteq Q_0`, define

\[
\operatorname{Ker}(Q)=\bigcap_{q\in Q}\ker q.
\]

For a relation `R`, define

\[
\operatorname{Desc}(R)=\{q\in Q_0:R\subseteq\ker q\}.
\]

### Theorem 3 — observation audit lattice

\[
Q\subseteq\operatorname{Desc}(R)
\quad\Longleftrightarrow\quad
R\subseteq\operatorname{Ker}(Q).
\]

Thus `Ker` and `Desc` form an antitone Galois connection. The composites `Ker Desc` and `Desc Ker` are closure operators on relations and query families, respectively.

**Proof.** Both sides say exactly that every query in `Q` is constant on every pair in `R`. Extensivity, monotonicity, and idempotence of the induced closures are standard consequences of a Galois connection. QED.

A descent failure is certified by a pair `(x,x') in R` for which `q(x) != q(x')`. This is the finite observation analogue of a nontrivial arrow in a kernel-pair groupoid.

## 5. Curved audit bicomplex

Suppose an audit has actually been equipped with horizontal and vertical differentials satisfying `delta^2 = 0` and `partial^2 = 0`. A generic dependency DAG does not supply such a differential automatically; a cellular, simplicial, or other chain construction and its signs must be declared. Let `delta` lower horizontal degree `p` and `partial` lower vertical degree. With the explicit convention

\[
D=\delta+(-1)^p\partial,
\qquad
D^2=(-1)^p(\delta\partial-\partial\delta).
\]

The right-hand side is the audit curvature. When it vanishes, the displayed total differential squares to zero and has ordinary total homology. When it does not vanish, ordinary total homology is undefined; requiring an explicit curved-complex replacement or restricting the claim is an audit policy, not a new impossibility theorem. This is the next foundational object proposed for the BSC program.

## 6. Atomic rigidity under limits

Finite-stage counterterm admissibility is not closed under distributional limits. Smooth densities may concentrate into off-origin atoms. For a compact set `K` disjoint from the origin, define

\[
\kappa_K(\varepsilon)=
\sup_{\lambda}\sup_{t\in K}
\int_{t-\varepsilon}^{t+\varepsilon}|a_\lambda(u)|\,du,
\]

where `lambda` ranges over a declared tail of place/cutoff stages.

### Theorem 4 — no-hidden-atom criterion

Suppose `a_lambda(u) du` converges weakly as finite signed measures on compact sets away from the origin, the total variations are locally uniformly bounded, and `kappa_K(epsilon) -> 0` for every compact `K` away from zero. Then the limiting measure has no atoms away from the origin.

**Proof.** Let `mu` be a weak limit and `t in K`. For the open interval `U_epsilon(t) = (t-epsilon,t+epsilon)`, lower semicontinuity of total variation under weak convergence on open sets gives

\[
|\mu|(\{t\})\le |\mu|(U_\varepsilon(t))
\le \liminf_\lambda |\mu_\lambda|(U_\varepsilon(t))
\le \kappa_K(\varepsilon).
\]

Letting `epsilon` decrease to zero gives `|mu|({t})=0`. QED.

Without this gate, normalized smooth bumps narrowing around `m log p` can converge to the prime-power delta comb even though every finite stage is smooth. A sufficient analytic certificate is a computable power bound `kappa_K(epsilon) <= C_K epsilon^alpha` with `alpha > 0`; uniform local `W^{1,1}` or stronger regularity bounds can supply such control under the appropriate hypotheses.

The v0.2 `atomic` command does not prove this analytic certificate. It checks internal consistency of finitely many declared rational upper bounds against an integer-power modulus and requires an external `proof_id`. It does not dereference that identifier, establish tail uniformity, or verify that the listed compacts form an exhaustion. A passing finite record is therefore not a proof of Theorem 4.

## 7. Composable quantitative defects

Suppose a transport stage has a declared amplification bound `L`, a newly introduced discrepancy bound `epsilon`, and a certificate failure probability `alpha`. Encode it by `(L, epsilon, alpha)`. Sequential composition is

\[
(L_2,\varepsilon_2,\alpha_2)\star(L_1,\varepsilon_1,\alpha_1)
=
(L_2L_1,\varepsilon_2+L_2\varepsilon_1,
\min(1,\alpha_1+\alpha_2)).
\]

This operation is associative with identity `(1,0,0)`. The second coordinate is the elementary upper-bound propagation rule for a Lipschitz stage: incoming discrepancy is amplified before the new declared bound is added. The probability coordinate uses only the union bound and therefore does not assume independence. The engine exactly composes the declared rational bounds; it does not measure the underlying physical defects or validate the probability model. It demotes a path certificate that understates a propagated coordinate.

## 8. Product gates and dependency filters

Fatal failure is not generally an algebraic operator ideal: two operators can separately fail a drift gate while their sum passes it. Fatality therefore lives in an acyclic claim-dependency graph. Gate state is product-valued (`unrun`, `pass`, `fail`, `conflict`), while epistemic and deployment status remain independent coordinates. A failed or conflicting fatal gate blocks every dependent promoted claim. Soft scores may rank only the surviving product fiber.

## 9. Exact derived path comparison

For bounded finite-dimensional chain complexes over `Q`, two chain maps induce the same map on homology exactly when their difference is chain-null-homotopic. With the homological grading convention used by the engine, the degreewise equation is:

```text
f_n - g_n = dD_(n+1) h_n + h_(n-1) dC_n.
```

After deterministic vectorization this becomes `A h = omega`. Exact row reduction is complete over `Q`:

- a solution `h` is a pass certificate;
- an annihilator `y` with `y^T A = 0` and `y^T omega != 0` is a failure certificate;
- the normal equations give an exact residual with `A^T r = 0` and `eta_squared = r^T r`.

This squared residual is coordinate-dependent: the current engine uses the Euclidean norm in the declared bases and does not claim invariance under arbitrary basis rescaling.

An observation-reduced comparison applies the same theorem after an explicitly supplied surjective chain map. Chain-map legality is checked before either derived class is constructed. Semantic basis hashes bind the finite algebra to declared meanings but do not make those meanings intrinsic or externally true.

This theorem depends on the field and finite-dimensional splitting hypotheses. The implementation does not claim the same equivalence over arbitrary rings. See [Exact Derived Holonomy](DERIVED_HOLONOMY.md) for the executable contract.

## 10. Exact observed quotients

Let `i: N -> D` and `pi: D -> O` be chain maps between finite-dimensional complexes over `Q`. Suppose degreewise that:

\[
\operatorname{rank}(i_n)=\dim N_n,\qquad
\operatorname{rank}(\pi_n)=\dim O_n,\qquad
\pi_n i_n=0,
\]

and

\[
\dim N_n+\dim O_n=\dim D_n.
\]

Injectivity gives `dim image(i_n) = dim N_n`. Surjectivity gives `dim ker(pi_n) = dim D_n - dim O_n = dim N_n`. The zero composite gives \(\operatorname{image}(i_n)\subseteq\ker(\pi_n)\). Equal finite dimensions therefore force:

\[
\operatorname{image}(i_n)=\ker(\pi_n).
\]

Thus `0 -> N -> D -> O -> 0` is a short exact sequence of chain complexes. The v0.2 exact-kernel holonomy route replays these rational rank and composition conditions before constructing an observed-derived class. This certifies the supplied finite quotient algebra; it does not establish that `N` is the scientifically correct nuisance or null subcomplex.

## 11. Exact polynomial-identity kernel

Let `Q[x_1,...,x_n]` be the polynomial ring in the certificate's sorted,
declared variables. The closed term language contains rational constants,
variables, negation, finite addition and multiplication, and nonnegative
integer powers. Define `N(t)` recursively as the canonical sparse polynomial
represented by term `t`.

For a formal equality `L = R`, the engine computes

\[
\rho = N(L)-N(R).
\]

Because sparse coefficients are exact rational numbers and like monomials are
combined canonically, `rho` is zero if and only if `L` and `R` denote the same
element of `Q[x_1,...,x_n]`. This is a complete decision procedure for the
closed language, not a probabilistic identity test. A nonzero coefficient and
power vector is an exact countercertificate.

The theorem is deliberately narrow. It does not interpret the human gloss,
import axioms, divide by a symbolic expression, handle inequalities or
transcendental functions, validate an external proof assistant, or establish a
scientific declaration. Manifest `0.4.0` makes the formal AST authoritative and
requires the certificate claim ID, statement, residual, evidence result, local
artifact hash, and gate bindings to agree.

## 12. Status

The algebraic identities above are proved. Their use as a universal scientific ontology is not claimed. The proposed originality lies in the audit assembly, certificate semantics, and executable witness formats; historical priority requires independent review.
