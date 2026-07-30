# Audit Descent Mathematics

This is the canonical mathematical reference for the finite checks implemented
by the BSC Audit Engine and for the nearby mathematical objects that motivate
them. Displayed formulas use GitHub's fenced `math` syntax. A renderer without
math support will therefore show a stable, readable code block instead of
reinterpreting formula lines as Markdown headings.

## Reading and authority boundary

Every conclusion in this document has a subject, scope, method, evidence
identity, and authority. The same word—such as *pass*, *verified*, or
*proved*—does not transfer authority between mathematical reasoning, exact
engine replay, actual execution, harness validity, artifact identity,
transport, external scientific truth, release state, or deployment.

| Subject | Scope | Method | Evidence identity / status | Authority |
| --- | --- | --- | --- | --- |
| Certificate complexes, transport, and strict path equality (§§1–3) | Mathematical statements over one exact field; executable route over finite rational complexes | Exact matrix method through `complex` | No execution evidence asserted; contract/example: [`complex-v0.3` schema](../schemas/complex-v0.3.schema.json), [positive fixture](../examples/complex_valid_transport.json), and [negative fixture](../examples/complex_broken_transport.json) | Supplied finite algebra only |
| Observation descent (§4) | Finite declared states, relation pairs, and total queries | Exact pairwise constancy check through `observe` | No execution evidence asserted; contract/example: [`observation-v0.3` schema](../schemas/observation-v0.3.schema.json) and [distinguishing fixture](../examples/observation_failure.json) | Supplied finite observation model only |
| Curved bicomplex (§5) | Declared bicomplex data under stated sign conventions | Manual derivation | Manual argument identity: §5 formula and derivation in this document; no engine receipt | Proposed mathematics; no public engine route |
| Atomic nonconcentration (§6) | Locally finite signed Radon measures away from the origin | Manual measure-theoretic proof; limited record replay through `atomic` | Manual argument identity: Theorem 4 and its proof; no execution evidence asserted for the [`atomic-modulus-v0.3` schema](../schemas/atomic-modulus-v0.3.schema.json) or [finite positive fixture](../examples/atomic_modulus_valid.json) | The theorem and the finite record check are separate; neither validates an external proof identifier |
| Quantitative defect composition (§7) | Declared nonnegative rational bounds | Exact arithmetic through `defect` | No execution evidence asserted; contract/example: [`defect-v0.3` schema](../schemas/defect-v0.3.schema.json) and [positive fixture](../examples/defect_composition_valid.json) | Propagation of supplied upper bounds only |
| Product gates (§8) | One finite claim-dependency graph | Exact gate evaluation through `audit` | No execution evidence asserted; contract/example: [`claim-manifest-v0.4` schema](../schemas/claim-manifest-v0.4.schema.json) and [polynomial fixture](../examples/claim_polynomial_identity.json) | Registered predicates and dependencies only |
| Derived and observed path comparison (§§9–10) | Bounded finite-dimensional rational complexes within resource limits | Exact row reduction and rank replay through `holonomy` | No execution evidence asserted; contract/example: [`derived-holonomy-v0.2` schema](../schemas/derived-holonomy-v0.2.schema.json), [derived fixture](../examples/holonomy_contractible_derived_pass.json), and [exact-kernel fixture](../examples/holonomy_observed_exact_kernel_pass.json) | Supplied rational complexes, maps, and meaning-string bytes only |
| Polynomial identity kernel (§11) | Syntactically admitted terms in the closed rational-polynomial language and resource envelope | Canonical sparse-polynomial normalization through `theorem` | No execution evidence asserted; contract/example: [`theorem-certificate-v0.1` schema](../schemas/theorem-certificate-v0.1.schema.json) and [binomial fixture](../examples/theorem_binomial_identity.json) | Formal identity of the authoritative AST only |
| Checked judgments (§12) | Registered replay results consumed by matching obligations | Exact tuple validation inside the engine | No execution evidence asserted; contract/test source: [`test_judgment.py`](../tests/test_judgment.py) | Authority-typing firewall; not external truth or deployment authority |

The links identify versioned contracts and example inputs; this table does not
assert that a command ran. Actual execution requires a separately identified
receipt or fresh test record bound to the exact release candidate.

For operational interpretation, see the [Status Model](STATUS_MODEL.md). For
the exact executable homotopy contract, see
[Exact Derived Holonomy](DERIVED_HOLONOMY.md).

## 1. Certificate complexes

Fix one computable exact field $F$. To each scientific context $c$, assign a
bounded finite-dimensional chain complex of $F$-vector spaces:

```math
\cdots\longrightarrow K_2(c)\xrightarrow{\partial^c_2}K_1(c)
\xrightarrow{\partial^c_1}K_0(c),
\qquad \partial^c_{n-1}\partial^c_n=0.
```

Using one field makes every declared linear transport well-typed. The current
`complex` and `holonomy` routes use $F=\mathbb Q$.

The degree convention is application-specific and must be fixed in the
manifest. A typical encoding places primitive evidence at high degree, derived
obligations below it, and the promoted claim at degree zero. If the basis and
differentials have independently validated obligation semantics, homology
records obligations closed under the declared rules but not discharged by
available certificates. The chain complex alone does not validate those
external semantics.

## 2. Certificate-interchange curvature

A context change $\alpha:c\to d$ supplies graded $F$-linear maps

```math
T_{\alpha,n}:K_n(c)\longrightarrow K_n(d).
```

### Definition

The certificate-interchange defect is

```math
\Theta_{\alpha,n}
=\partial^d_nT_{\alpha,n}-T_{\alpha,n-1}\partial^c_n.
```

It is zero in every degree exactly when $T_\alpha$ is a chain map.

### Theorem 1 — lawful promotion transport

If every $\Theta_{\alpha,n}$ vanishes, transport sends cycles to cycles and
boundaries to boundaries and therefore induces maps

```math
H_n(T_\alpha):H_n(K(c))\longrightarrow H_n(K(d)).
```

If $\Theta_{\alpha,n}$ is nonzero, a nonzero column is a finite exact
basis-vector witness to failure of the declared matrix chain-map equation. It
represents a scientific obligation only when the chosen basis and
differentials have independently validated obligation semantics.

**Proof.** If $\partial z=0$, then
$\partial(T_\alpha z)=T_\alpha(\partial z)=0$. If $z=\partial w$, then
$T_\alpha z=T_\alpha(\partial w)=\partial(T_\alpha w)$. Evaluating a nonzero
defect column on its standard basis vector gives the stated witness. QED.

### Theorem 2 — derivation law

For $\alpha:c\to d$ and $\beta:d\to e$,

```math
\Theta_{\beta\alpha,n}
=\Theta_{\beta,n}T_{\alpha,n}
+T_{\beta,n-1}\Theta_{\alpha,n}.
```

**Proof.** Expand
$\partial T_\beta T_\alpha-T_\beta T_\alpha\partial$ and add and subtract
$T_\beta\partial T_\alpha$. QED.

A nonzero composite defect implies that at least one stage defect is nonzero.
Conversely, nonzero stage defects can cancel in the composite; establishing
such cancellation is a separate exact obligation.

## 3. Path holonomy

For a square with two composite transports from $c$ to $d$, define

```math
\Omega=T_{q\mid p}T_p-T_{p\mid q}T_q.
```

$\Omega=0$ is exact equality of the two declared composite paths in this
square. It is not, by itself, global path independence: that requires a
presentation whose checked squares generate every relevant path relation. The
square test specializes to:

- scale-transfer curvature;
- order dependence when adjoining primes;
- change of instrument followed by quotient versus quotient followed by
  instrument change;
- boundary completion followed by inference versus inference followed by
  completion.

No norm is silently chosen. Approximate mode must declare a norm, domain, and
tolerance separately.

## 4. Observation-descent Galois connection

Let $\operatorname{Rel}(X)$ be relations on a state set $X$, ordered by
inclusion. Fix a set $Q_0$ of total queries, each with a declared codomain, and
define

```math
\ker(q)=\{(x,x')\in X\times X:q(x)=q(x')\}.
```

For $Q\subseteq Q_0$, define

```math
\operatorname{Ker}(Q)=\bigcap_{q\in Q}\ker(q).
```

For a relation $R$, define

```math
\operatorname{Desc}(R)
=\{q\in Q_0:R\subseteq\ker(q)\}.
```

### Theorem 3 — observation audit lattice

```math
Q\subseteq\operatorname{Desc}(R)
\quad\Longleftrightarrow\quad
R\subseteq\operatorname{Ker}(Q).
```

Thus $\operatorname{Ker}$ and $\operatorname{Desc}$ form an antitone Galois
connection. The composites
$\operatorname{Ker}\operatorname{Desc}$ and
$\operatorname{Desc}\operatorname{Ker}$ are closure operators on relations
and query families, respectively.

**Proof.** Both sides say exactly that every query in $Q$ is constant on every
pair in $R$. Extensivity, monotonicity, and idempotence of the induced
closures follow from the displayed equivalence. QED.

A descent failure is a pair
$(x,x')\in R\setminus\ker(q)$; equivalently, it witnesses
$R\nsubseteq\ker(q)$. It is not an arrow in the kernel-pair groupoid of $q$,
because its two query values differ.

## 5. Curved audit bicomplex

Suppose an audit has actually been equipped with horizontal and vertical
differentials satisfying $\delta^2=0$ and $\partial^2=0$. A generic dependency
DAG does not supply such differentials automatically; a cellular, simplicial,
or other chain construction and its signs must be declared. Let $\delta$
lower horizontal degree $p$ and let $\partial$ lower vertical degree. With the
explicit convention

```math
D=\delta+(-1)^p\partial,
\qquad
D^2=(-1)^p(\delta\partial-\partial\delta).
```

The right-hand side is the audit curvature. When it vanishes, this total
differential squares to zero and has ordinary total homology. When it does not
vanish, ordinary total homology is undefined. Requiring an explicit
curved-complex replacement or restricting the claim is an audit policy, not a
new impossibility theorem. This is a proposed research direction, not a
current public engine route.

## 6. Atomic rigidity under limits

Finite-stage smoothness alone does not exclude atomic weak limits. Let
$\mu_\lambda=a_\lambda(u)\,du$ be locally finite signed Radon measures on
$\mathbb R\setminus\{0\}$. For a compact
$K\subset\mathbb R\setminus\{0\}$ and sufficiently small $\varepsilon>0$,
define on a declared tail $\Lambda_0$:

```math
\kappa_K(\varepsilon)
=\sup_{\lambda\in\Lambda_0}\sup_{t\in K}
\int_{t-\varepsilon}^{t+\varepsilon}|a_\lambda(u)|\,du.
```

### Theorem 4 — no-hidden-atom criterion

Suppose $\mu_\lambda$ converges locally weak-* to a signed Radon measure $\mu$
on $\mathbb R\setminus\{0\}$, the total variations are locally uniformly
bounded, and $\kappa_K(\varepsilon)\to0$ as $\varepsilon\downarrow0$ for every
compact $K$ away from zero. Then $\mu$ has no atoms away from the origin.

**Proof.** Fix $t\in K$ and choose $\varepsilon$ small enough that
$U_\varepsilon(t)=(t-\varepsilon,t+\varepsilon)$ remains away from zero.
Lower semicontinuity of total variation under local weak-* convergence on
open sets gives

```math
|\mu|(\{t\})
\le |\mu|(U_\varepsilon(t))
\le \liminf_\lambda|\mu_\lambda|(U_\varepsilon(t))
\le \kappa_K(\varepsilon).
```

Letting $\varepsilon\downarrow0$ gives $|\mu|(\{t\})=0$. QED.

Without this gate, normalized smooth bumps narrowing around $m\log p$ can
converge to a prime-power delta comb although every finite stage is smooth. A
sufficient analytic certificate is a computable bound
$\kappa_K(\varepsilon)\le C_K\varepsilon^\alpha$ with $\alpha>0$.
Appropriate uniform local $W^{1,1}$ or stronger regularity bounds can supply
such control under additional hypotheses.

The current `atomic` route (schema `atomic-modulus-v0.3`) does not prove that
analytic certificate. It checks internal consistency of finitely many
declared rational upper bounds against an integer-power modulus and requires
an external `proof_id`. It does not dereference that identifier, establish
tail uniformity, or verify that the listed compacts form an exhaustion. A
passing finite record is therefore not a proof of Theorem 4.

## 7. Composable quantitative defects

Suppose stage 1 runs before stage 2. Each stage has a declared amplification
bound $L_i\ge0$, a newly introduced discrepancy bound
$\varepsilon_i\ge0$, and a certificate-failure upper bound
$\alpha_i\in[0,1]$. Encode it by $(L_i,\varepsilon_i,\alpha_i)$. Sequential
composition is

```math
(L_2,\varepsilon_2,\alpha_2)\star
(L_1,\varepsilon_1,\alpha_1)
=
\left(
L_2L_1,\,
\varepsilon_2+L_2\varepsilon_1,\,
\min(1,\alpha_1+\alpha_2)
\right).
```

The operation is associative with identity $(1,0,0)$. Both bracketings of
three stages give

```math
\left(
L_3L_2L_1,\,
\varepsilon_3+L_3\varepsilon_2+L_3L_2\varepsilon_1,\,
\min(1,\alpha_1+\alpha_2+\alpha_3)
\right).
```

The discrepancy coordinate is the elementary upper-bound propagation rule
for a Lipschitz stage: incoming discrepancy is amplified before the new bound
is added. The probability coordinate uses only the union bound and does not
assume independence. It is a declared upper bound, not an observed
probability. The engine exactly composes the supplied rational bounds; it
does not measure physical defects or validate the probability model. It
demotes a path certificate that understates a propagated coordinate.

## 8. Product gates and dependency filters

Fatal failure is not generally an algebraic operator ideal: two operators can
separately fail a drift gate while their sum passes it. Fatality therefore
lives in an acyclic claim-dependency graph. Each gate has one state in

```math
G=\{\mathrm{unrun},\mathrm{pass},\mathrm{fail},\mathrm{conflict}\}.
```

A multi-gate ledger indexed by $I$ lies in the Cartesian product $G^I$.
Epistemic status, execution, artifact identity, transport, and deployment
remain independent coordinates. A failed or conflicting fatal gate blocks
every dependent promoted claim. Soft scores may rank only the surviving
product fiber.

## 9. Exact derived path comparison

For bounded finite-dimensional chain complexes over $\mathbb Q$, two chain
maps induce the same map on homology exactly when their difference is
chain-null-homotopic. With the engine's homological grading convention:

```math
f_n-g_n=d^D_{n+1}h_n+h_{n-1}d^C_n.
```

**Proof sketch.** Every finite-dimensional complex over a field admits a
deformation retract onto its homology with zero differential. For a chain map
$u:C\to D$, chosen retract data give
$u\simeq i_D\,H(u)\,p_C$. Therefore $H(u)=0$ exactly when $u$ is
null-homotopic. The converse also follows directly by applying the homotopy
identity to cycles. This equivalence can fail over general rings because the
required splittings need not exist.

After deterministic vectorization, the equation becomes
$A\mathbf h=\boldsymbol\omega$. Exact row reduction over $\mathbb Q$ yields
one of two disjoint certificate variants:

- a solution $\mathbf h$ with exact equality
  $A\mathbf h=\boldsymbol\omega$;
- an annihilator $\mathbf y$ with
  $\mathbf y^{\mathsf T}A=0$ and
  $\mathbf y^{\mathsf T}\boldsymbol\omega\ne0$.

The dual obstruction is decisive because a hypothetical solution would force

```math
\mathbf y^{\mathsf T}\boldsymbol\omega
=\mathbf y^{\mathsf T}A\mathbf h
=0.
```

A primal result contains the exact solution, deterministically recomputed
zero residual, and

```math
\eta^2
=\sum_i\left(A\mathbf h-\boldsymbol\omega\right)_i^2
=0.
```

A dual result contains only the annihilator and deterministically recomputed
nonzero pairing. Wrong-variant fields are rejected at construction and
replay. Earlier coordinate-dependent least-squares diagnostics were
non-authoritative and are no longer accepted on a failure certificate.

The row-reduction method decides every syntactically accepted bounded system.
Inputs beyond declared resource ceilings fail closed without a mathematical
verdict. An observation-reduced comparison applies the same theorem after an
explicitly supplied surjective chain map. Chain-map legality is checked before
either derived class is constructed.

Semantic basis hashes bind each basis slot to the exact UTF-8 bytes of a
declared meaning string. They do not validate that meaning or make it
intrinsic. See [Exact Derived Holonomy](DERIVED_HOLONOMY.md) for the executable
contract.

## 10. Exact observed quotients

Let $i:N\to D$ and $\pi:D\to O$ be chain maps between finite-dimensional
complexes over $\mathbb Q$. Suppose degreewise that

```math
\operatorname{rank}(i_n)=\dim N_n,\qquad
\operatorname{rank}(\pi_n)=\dim O_n,\qquad
\pi_n i_n=0,
```

and

```math
\dim N_n+\dim O_n=\dim D_n.
```

Injectivity gives $\dim\operatorname{image}(i_n)=\dim N_n$. Surjectivity gives
$\dim\ker(\pi_n)=\dim D_n-\dim O_n=\dim N_n$. The zero composite gives
$\operatorname{image}(i_n)\subseteq\ker(\pi_n)$. Equal finite dimensions
therefore force

```math
\operatorname{image}(i_n)=\ker(\pi_n).
```

Thus $0\to N\to D\to O\to0$ is a short exact sequence of chain complexes. The
`holonomy_version: 0.2.0` exact-kernel route replays these rational rank and
composition conditions before constructing an observed-derived class. This
certifies the supplied finite quotient algebra; it does not establish that
$N$ is the scientifically correct nuisance or null subcomplex.

## 11. Exact polynomial-identity kernel

Let $\mathbb Q[x_1,\ldots,x_n]$ be the polynomial ring in the certificate's
sorted declared variables. The closed term language contains rational
constants, variables, negation, finite addition and multiplication, and
nonnegative integer powers. Define $N(t)$ recursively as the canonical sparse
polynomial represented by term $t$.

For a formal equality $L=R$, the engine computes

```math
\rho=N(L)-N(R).
```

Because coefficients are exact rationals and like monomials are combined
canonically, $\rho=0$ exactly when $L$ and $R$ denote the same element of the
declared polynomial ring. For every syntactically admitted input within the
declared limits on variables, AST depth and size, arity, exponent, monomial
count, operations, and bit growth, this is a complete decision procedure—not
a probabilistic identity test. Inputs beyond that resource envelope are
rejected rather than labeled pass or fail. A nonzero coefficient and power
vector is an exact countercertificate.

The theorem is deliberately narrow. It does not interpret free prose, import
axioms, divide by a symbolic expression, handle inequalities or
transcendental functions, validate an external proof assistant, or establish a
scientific declaration. Manifest `0.4.0` makes the formal AST authoritative
and requires `claim.statement` to be its deterministic ASCII projection. The
emitted replay witness includes that projection, identifies its authority as
internal exact replay over the canonical formal statement only, and states
that scientific truth and deployment authority are not established. The
certificate claim ID, formal statement, residual, evidence result, local
artifact hash, and gate bindings must agree.

This is also a semantic-laundering firewall: a matching hash binds bytes but
does not turn a declared `pass`, `fail`, empirical result, or replication
label into a mathematical or scientific result. Only a result recomputed by a
registered exact replay can change a gate or evidence maturity.

## 12. Authority-typed checked judgments

A replay conclusion is a tuple, not a transferable word:

```math
J=(S,P,\Sigma,M,E,A,R),
```

where $S$ is the subject identity and digest, $P$ the predicate, $\Sigma$ the
scope, $M$ the method, $E$ the evidence identity and digest, $A$ the authority
domain, and $R$ the result. A gate may consume $J$ only when every coordinate
matches its declared obligation. In particular, the string `pass` from a
polynomial replay cannot satisfy an arithmetic-trace obligation, and a
matching artifact hash cannot supply a missing method or authority.

This envelope makes the authority boundary machine-checkable. It does not
claim that a syntactically well-typed judgment is externally true; it only
prevents one registered result from being reused outside its declared
coordinates. `CheckedJudgment` types a registered replay conclusion only.
Actual execution, harness validity, artifact transport, external truth,
release state, and deployment authority remain separate records; see the
[Status Model](STATUS_MODEL.md).

## 13. Status

- **Mathematical propositions:** Theorems 1–4 and the finite-dimensional
  splitting, quotient, and polynomial statements are supported here by manual
  proofs or proof sketches under their explicit hypotheses. They have not
  received proof-assistant replay or independent peer review in this release.
- **Executable finite checks:** When run, the linked engine routes and tests
  replay only admitted finite objects and fail closed outside their registered
  language or resource envelope. Schemas and fixtures identify contracts and
  examples; they do not execute themselves.
- **External semantics and truth:** Basis meanings, scientific declarations,
  proof identifiers, probability models, and the completeness of supplied
  evidence remain external obligations.
- **Operational authority:** Test success, hashes, release identity,
  transport, live-GPT state, and deployment permission are separate
  conclusions recorded outside this mathematical reference.
- **Historical priority:** The proposed audit assembly, certificate semantics,
  and witness formats require independent scholarly review before any priority
  claim.
