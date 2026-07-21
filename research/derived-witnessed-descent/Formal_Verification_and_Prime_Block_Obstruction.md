# Formal Verification of Derived Holonomy, a Mechanical Shifted-Ladder Witness, and an Orthogonal Prime-Block No-Go

**Date:** 21 July 2026  
**Research status:** three proved theorem packages, one mechanically reproduced counterexample, and explicit remaining escape routes  
**Scope:** mathematical supplement; no repository or audit-engine source code was changed

## Executive result

Three questions were separated and resolved.

1. **Derived holonomy.** For bounded finite-dimensional chain complexes over an exact field, two chain maps induce the same homology map if and only if their difference is null-homotopic. A constructive formula and an exact rational pass/fail certificate are given below. The supplied checker replays four exact fixtures and exhausts 153 small two-term map pairs.

2. **Shifted ladder.** The bilateral shifted spectral ladder has a trace-class relative resolvent but a symmetric-cutoff relative unitary trace converging to an infinite off-origin Dirac comb. The coefficient identity is replayed exactly over \(\mathbb Q(i)\) on 1,001 integer modes; independent 80-digit calculations reproduce both trace-norm summability and distributional convergence against a Gaussian.

3. **Orthogonal prime blocks.** The earlier conditional obstruction becomes a theorem once the allowed origin counterterms have uniformly bounded distributional order. A single derivative annihilates every such counterterm. The surviving prime-power terms have one sign and force a divergent trace-norm derivative sum whenever \(0<\operatorname{Im}z\le \tfrac12\). Thus a locally uniform \(\mathcal S_1\)-Cauchy orthogonal prime-block fold cannot cross that region under the declared trace law. This does not rule out nonorthogonal gluing, construction first in \(\operatorname{Im}z>\tfrac12\), or separately controlled absolutely continuous remainders.

The third result is the principal new bridge. It converts an unspecified “noncancellation estimate” into the checkable hypothesis “uniformly bounded origin-jet order,” which is exactly the kind of declared counterterm class required by the framework.

---

## 1. Derived holonomy: exact theorem and constructive proof

### 1.1 Typed setting

Let \(F\) be a field and let \(C=(C_n,d_n^C)\), \(D=(D_n,d_n^D)\) be bounded chain complexes of finite-dimensional \(F\)-vector spaces. Thus

\[
d_{n-1}^C d_n^C=0,
\qquad
d_{n-1}^D d_n^D=0.
\]

Let \(f,g:C\to D\) be chain maps and set \(\Omega=f-g\). A degree \(+1\) homotopy is a family \(h_n:C_n\to D_{n+1}\). Its mapping-complex boundary is

\[
(\delta h)_n=d_{n+1}^D h_n+h_{n-1}d_n^C.
\]

The derived holonomy class is

\[
[\Omega]\in H_0\!\left(\underline{\operatorname{Hom}}(C,D)\right).
\]

### Theorem 1 — derived-holonomy criterion

The following are equivalent:

1. \(H_n(f)=H_n(g)\) for every \(n\);
2. \([f-g]=0\) in \(H_0(\underline{\operatorname{Hom}}(C,D))\);
3. there is a degree \(+1\) map \(h\) with

   \[
   f-g=d_Dh+hd_C.
   \]

### 1.2 Constructive contraction data

Because \(F\) is a field, choose in every degree a splitting

\[
C_n=B_n^C\oplus H_n^C\oplus L_n^C,
\]

where \(B_n^C=\operatorname{im}d_{n+1}^C\), the summand \(H_n^C\) represents homology, and

\[
d_n^C:L_n^C\xrightarrow{\sim}B_{n-1}^C.
\]

This produces chain maps

\[
i_C:H(C)\to C,
\qquad
p_C:C\to H(C),
\]

and a degree \(+1\) contraction \(s_C\) satisfying

\[
1_C-i_Cp_C=d_Cs_C+s_Cd_C.
\tag{1}
\]

Choose analogous data \((i_D,p_D,s_D)\) for \(D\).

### 1.3 Proof of Theorem 1

The implication \(3\Rightarrow1\) is immediate: if \(x\) is a cycle, then

\[
(f-g)x=d_D(hx),
\]

so \(f\) and \(g\) give the same homology class. Conditions 2 and 3 are identical by the definition of mapping-complex homology.

For \(1\Rightarrow3\), the chain map \(\Omega=f-g\) induces zero on homology, so

\[
p_D\Omega i_C=0.
\tag{2}
\]

Define

\[
h=s_D\Omega+i_Dp_D\Omega s_C.
\tag{3}
\]

Using (1) for \(D\), the chain-map identity \(d_D\Omega=\Omega d_C\), and \(d_Di_D=0\),

\[
d_D(s_D\Omega)+(s_D\Omega)d_C
=(1_D-i_Dp_D)\Omega.
\tag{4}
\]

Equation (2) and the source contraction give

\[
\begin{aligned}
p_D\Omega
&=p_D\Omega(1_C-i_Cp_C)\\
&=p_D\Omega(d_Cs_C+s_Cd_C)\\
&=p_D\Omega s_Cd_C,
\end{aligned}
\tag{5}
\]

because \(p_D\Omega d_C=0\). Hence

\[
d_D(i_Dp_D\Omega s_C)+(i_Dp_D\Omega s_C)d_C=i_Dp_D\Omega.
\tag{6}
\]

Adding (4) and (6) gives \(d_Dh+hd_C=\Omega\). This proves the theorem. \(\square\)

### 1.4 Exact finite certificate

After bases are fixed, vectorize all entries of \(h\) and \(\Omega\). The homotopy identity becomes

\[
A\mathbf h=\boldsymbol\omega
\]

over \(F\), and over \(\mathbb Q\) it is decidable by exact Gaussian elimination.

- A **pass certificate** is \(\mathbf h\in\mathbb Q^r\) with exact equality \(A\mathbf h=\boldsymbol\omega\).
- A **fail certificate** is \(y\in\mathbb Q^m\) with

  \[
  y^TA=0,
  \qquad
  y^T\boldsymbol\omega\ne0.
  \]

The fail witness is complete: if \(A\mathbf h=\boldsymbol\omega\) is inconsistent, exact row reduction produces such a row of the accumulated row-operation matrix.

### 1.5 Mechanical verification record

The dependency-free checker `verification/derived_holonomy_exact.py` performs all arithmetic with `fractions.Fraction`. It:

- checks \(d^2=0\) and the chain-map equations;
- constructs \(A\) directly from the typed matrix entries;
- produces either \(\mathbf h\) or \(y\);
- independently constructs exact homology bases and induced homology maps;
- asserts that the certificate verdict equals equality of induced homology maps;
- checks the contractible false-block fixture;
- checks a genuine homology-visible failure;
- checks a discrepancy killed only after an observation quotient;
- exhausts all 153 valid pairs arising from two-term \(1\times1\) differentials and scalar maps with entries in \(\{-1,0,1\}\).

The central false-block fixture is

\[
0\longrightarrow\mathbb Q\xrightarrow{1}\mathbb Q\longrightarrow0,
\qquad
f=1,quad g=0.
\]

The raw discrepancy is nonzero in both degrees, but the generated certificate is

\[
A=\begin{bmatrix}1\\1\end{bmatrix},
\qquad
\boldsymbol\omega=\begin{bmatrix}1\\1\end{bmatrix},
\qquad
\mathbf h=[1].
\]

Thus a strict holonomy gate fails while the derived gate passes.

### 1.6 Formal-verification boundary

The proof above is a complete algebraic proof, and each finite fixture has a replayable exact certificate. It has **not** been certified by a Lean, Coq, or Isabelle kernel in this environment because no such kernel is installed and toolchain installation was unavailable. It would be incorrect to relabel this as ITP-kernel verification. A future kernel formalization should define the contraction data explicitly and verify equations (3)–(6); the exact checker already fixes the sign and grading conventions that the formalization must reproduce.

The field hypothesis matters. For example, the exact complex

\[
0\to\mathbb Z\xrightarrow{\,2\,}\mathbb Z\to\mathbb Z/2\mathbb Z\to0
\]

is acyclic but not contractible: contracting it would split the nonsplit quotient map \(\mathbb Z\to\mathbb Z/2\mathbb Z\). Thus equality on homology need not imply chain homotopy over an arbitrary ring.

---

## 2. Shifted spectral ladder: proof and mechanical reproduction

### 2.1 Operators

Let \(\mathcal H=\ell^2(\mathbb Z)\), fix \(\alpha\in\mathbb R\setminus\mathbb Z\), and define on the common domain

\[
Ae_k=ke_k,
\qquad
A^{(0)}e_k=(k+\alpha)e_k.
\]

Both operators are self-adjoint, and \(A^{(0)}=A+\alpha I\).

### Theorem 2 — resolvent/trace separation

For every \(z\notin\mathbb R\),

\[
(A-z)^{-1}-(A^{(0)}-z)^{-1}\in\mathcal S_1.
\]

If \(P_N\) projects onto \(\operatorname{span}\{e_k:|k|\le N\}\), then

\[
T_N(t)=\operatorname{Tr}\!\left(P_N(e^{itA}-e^{itA^{(0)}})P_N\right)
\]

converges in \(\mathcal S'(\mathbb R)\) to

\[
2\pi\sum_{m\in\mathbb Z}
\left(1-e^{2\pi i\alpha m}\right)\delta(t-2\pi m).
\tag{7}
\]

This limit has no atom at zero and has infinitely many nonzero off-origin atoms.

### 2.2 Resolvent proof

The resolvent difference is diagonal with coefficient

\[
r_k(z)=
\frac1{k-z}-\frac1{k+\alpha-z}
=\frac{\alpha}{(k-z)(k+\alpha-z)}.
\tag{8}
\]

On every compact \(K\subset\mathbb C\setminus\mathbb R\), there are constants \(M_K\) and \(k_0\) such that

\[
\sup_{z\in K}|r_k(z)|\le \frac{M_K}{k^2}
\qquad(|k|\ge k_0).
\]

Therefore \(\sum_k|r_k(z)|\) converges, and its tails converge uniformly on \(K\). This proves both trace-class membership and compact-uniform trace-norm convergence of the diagonal cutoffs.

### 2.3 Distributional proof and phase check

The finite trace is exactly

\[
T_N(t)=(1-e^{i\alpha t})\sum_{k=-N}^Ne^{ikt}.
\tag{9}
\]

For \(\varphi\in\mathcal S(\mathbb R)\) and

\[
\widehat\varphi(\xi)=\int_{\mathbb R}\varphi(t)e^{-it\xi}\,dt,
\]

the pairing is

\[
\langle T_N,\varphi\rangle
=\sum_{k=-N}^N
\left(\widehat\varphi(-k)-\widehat\varphi(-(k+\alpha))\right).
\tag{10}
\]

Both bilateral series converge absolutely. Poisson summation gives

\[
\sum_{k\in\mathbb Z}e^{ikt}
=2\pi\sum_{m\in\mathbb Z}\delta(t-2\pi m).
\]

Multiplication by \(1-e^{i\alpha t}\) yields (7), including the positive phase \(e^{2\pi i\alpha m}\). Since \(\alpha\notin\mathbb Z\), infinitely many of these coefficients are nonzero. \(\square\)

### 2.4 Mechanical witness

The script `verification/shifted_ladder_reproduce.py` fixes

\[
\alpha=\tfrac12,
\qquad z=i,
\qquad
\varphi(t)=e^{-t^2/8}.
\]

It checks (8) exactly over \(\mathbb Q(i)\) for every \(-500\le k\le500\). It then evaluates the trace-norm partial sums and the analytic two-sided tail bound

\[
\sum_{|k|>N}|r_k(i)|
\le
\log\frac{N+1/2}{N-1/2}.
\tag{11}
\]

For the Gaussian, (10) becomes

\[
2\sqrt{2\pi}
\sum_{k=-N}^N
\left(e^{-2k^2}-e^{-2(k+1/2)^2}\right).
\]

The comb pairing is

\[
2\pi\sum_{m\in\mathbb Z}(1-(-1)^m)e^{-(2\pi m)^2/8}.
\]

The 80-digit calculation gives

\[
\langle T_8,\varphi\rangle
=0.1807517433291105541915827439229378114617476337303535351851285\ldots
\]

and the independently evaluated comb agrees to about \(62\) decimal places. The omitted comb tail after \(|m|\le20\) is bounded analytically by less than \(7\times10^{-859}\). These decimals corroborate the theorem; the proof is the summability and Poisson argument above.

Because an even Gaussian with \(\alpha=1/2\) could hide a Fourier-sign error, the script also runs a phase-sensitive fixture with

\[
\alpha=\tfrac13,
\qquad
\varphi(t)=e^{-t^2/8}e^{it/4}.
\]

It evaluates the negative Fourier arguments in (10) literally and compares them with the positive comb phase in (7). The two formulas agree to more than \(70\) decimal places. This second fixture locks the sign convention rather than merely checking a symmetric special case.

### 2.5 What the counterexample proves

It proves that locally uniform \(\mathcal S_1\) convergence of relative resolvents is compatible with an infinite atomic distributional unitary trace. It refutes any gate that treats resolvent control alone as determining atomic support, arithmetic weights, provenance, cutoff independence, or determinant normalization. It does not produce the prime-power comb.

---

## 3. Orthogonal prime blocks: removing the noncancellation hypothesis

### 3.1 Frozen assumptions

Let \(\mathbb P\) be the rational primes and let

\[
\mathcal H=\bigoplus_{p\in\mathbb P}\mathcal H_p
\]

be an orthogonal Hilbert direct sum. Let \(U\subset\mathbb C\) be open. For every prime \(p\), let

\[
B_p:U\to\mathcal S_1(\mathcal H_p)
\]

be holomorphic, and for finite \(S\subset\mathbb P\) put

\[
B_S(z)=\bigoplus_{p\in S}B_p(z).
\]

Assume there are:

- an integer \(d\ge0\);
- a constant \(c\in\mathbb C\) with \(|c|=1\);
- for each \(p\), a polynomial \(P_p\) of degree at most \(d\);
- a nonempty open interval \(I\subset(0,\infty)\) with \(iI\subset U\);

such that for every \(\eta\in I\),

\[
c^{-1}\operatorname{Tr}B_p(i\eta)
=P_p(\eta)
-\sum_{m\ge1}(\log p)p^{-m/2}e^{-\eta m\log p}.
\tag{12}
\]

For fixed \(p\), the series and all its \(\eta\)-derivatives converge locally uniformly for \(\eta>-1/2\). Formula (12) is the exact transform obligation. An origin-supported counterterm of order at most \(d\) has a Laplace/Fourier transform of the polynomial form \(P_p\); the convention-dependent constant is absorbed into \(c\).

### Theorem 3 — bounded-jet orthogonal-prime-block obstruction

If \(I\cap(0,\tfrac12]\ne\varnothing\), the net \((B_S)_S\), ordered by inclusion of finite prime sets, cannot be locally uniformly Cauchy in \(\mathcal S_1\) on \(U\).

More generally, the open-interval assumption may be replaced by requiring (12) on a set with an accumulation point \(\eta_0\in(0,\tfrac12]\), with \(i\eta_0\in U\). A singleton is insufficient: one could take \(B_p=0\) and choose a constant \(P_p\) matching the prime series at that one point.

### 3.2 Proof

Set \(r=d+1\). Differentiating (12) \(r\) times annihilates \(P_p\) and gives

\[
\left|
\frac{d^r}{d\eta^r}\operatorname{Tr}B_p(i\eta)
\right|
=
\sum_{m\ge1}
m^r(\log p)^{r+1}p^{-m(1/2+\eta)}.
\tag{13}
\]

All terms have the same phase; this is the missing noncancellation estimate, now obtained rather than assumed. Keeping only \(m=1\),

\[
\left|
\frac{d^r}{d\eta^r}\operatorname{Tr}B_p(i\eta)
\right|
\ge
(\log p)^{d+2}p^{-(1/2+\eta)}.
\tag{14}
\]

Suppose, toward contradiction, that \((B_S)_S\) is locally uniformly \(\mathcal S_1\)-Cauchy. Holomorphic functions with values in the Banach space \(\mathcal S_1\) then have locally uniformly Cauchy derivatives by the vector-valued Cauchy integral formula. Therefore, at every \(\eta\in I\), the derivative net is \(\mathcal S_1\)-Cauchy.

Orthogonality of the blocks gives

\[
\left\|
\frac{d^r}{d\eta^r}(B_T-B_S)(i\eta)
\right\|_1
=
\sum_{p\in T\setminus S}
\left\|
\frac{d^r}{d\eta^r}B_p(i\eta)
\right\|_1.
\tag{15}
\]

Since \(|\operatorname{Tr}X|\le\|X\|_1\), equations (14) and (15) imply the necessary condition

\[
\sum_p(\log p)^{d+2}p^{-(1/2+\eta)}<\infty.
\tag{16}
\]

If \(0<\eta\le\tfrac12\), then \(s=\tfrac12+\eta\le1\). For every sufficiently large prime,

\[
(\log p)^{d+2}p^{-s}\ge\frac1p.
\]

Euler's divergence of \(\sum_p1/p\) contradicts (16). \(\square\)

### Corollary 3.1 — pointwise obstruction for genuine relative resolvents

Assume additionally that

\[
B_p(z)=(A_p-z)^{-1}-(A_p^{(0)}-z)^{-1}
\]

for self-adjoint \(A_p,A_p^{(0)}\). Then failure is already pointwise at every \(i\eta\) covered by the theorem; local uniform convergence need not be assumed.

Indeed, writing \(R_p=(A_p-z)^{-1}\), \(R_p^{(0)}=(A_p^{(0)}-z)^{-1}\), the noncommutative telescoping identity gives

\[
\begin{aligned}
\left\|\frac{d^r}{dz^r}B_p(i\eta)\right\|_1
&=r!\left\|R_p(i\eta)^{r+1}-R_p^{(0)}(i\eta)^{r+1}\right\|_1\\
&\le (r+1)!\eta^{-r}\|B_p(i\eta)\|_1.
\end{aligned}
\tag{17}
\]

Combining (14) with (17), and noting that \(d/d\eta=i\,d/dz\), yields

\[
\|B_p(i\eta)\|_1
\ge
\frac{\eta^r}{(r+1)!}
(\log p)^{d+2}p^{-(1/2+\eta)}.
\tag{18}
\]

The prime sum diverges. Orthogonal additivity therefore prevents even pointwise \(\mathcal S_1\)-Cauchy convergence at \(i\eta\).

### 3.3 Why the bounded-order hypothesis is natural

Every distribution supported at the single point \(0\) is a finite sum of delta derivatives, but its order may depend on \(p\). The theorem requires one common order \(d\). This is not merely cosmetic: without it, no single derivative is guaranteed to remove all local counterterms.

A bounded family of distributions supported in a fixed compact set has a uniform finite-order estimate on that compact. Consequently, any counterterm class that is bounded in the usual distribution topology and supported at \(0\) supplies precisely the uniform-order hypothesis used above. If the proposal permits arbitrarily increasing derivative order with no common bound, that escape must be declared and analytically controlled; it cannot be hidden inside the word “local.”

### 3.4 Absolutely continuous remainders

Suppose (12) contains an additional remainder \(R_p(\eta)\). The same contradiction holds if

\[
\sum_p\left|R_p^{(d+1)}(\eta)\right|<\infty
\tag{19}
\]

at one \(\eta\in I\cap(0,\tfrac12]\), or under a uniform domination

\[
|R_p^{(d+1)}(\eta)|
\le\theta(\log p)^{d+2}p^{-(1/2+\eta)},
\qquad \theta<1.
\tag{20}
\]

Indeed, the reverse triangle inequality leaves a divergent positive lower bound. Thus “explicitly controlled absolutely continuous spectral component” can be made auditable by (19), (20), or a stronger transform-domain certificate implying one of them.

Neither local nonconcentration nor uniform integrability alone implies this certificate. To see the obstruction, put

\[
L_p=\log p,
\qquad
w_p=\frac{\log p}{\sqrt p},
\]

and replace the first prime atom by a smooth bump

\[
a_p(t)=w_p\varepsilon_p^{-1}
\rho\!\left(\frac{t-L_p}{\varepsilon_p}\right),
\qquad \int\rho=1,
\]

with the cancellation sign. By taking \(\varepsilon_p\) super-summably small, its Laplace transform and any fixed finite family of transform derivatives approximate those of \(w_p\delta_{L_p}\) with summable total error on a fixed upper-half-plane compact. The bumps remain smooth and absolutely continuous, their centers escape to infinity, and \(w_p\to0\). Thus standard local atomic-rigidity and ordinary uniform-integrability checks do not prevent transform-domain cancellation. The extension of Theorem 3 to an absolutely continuous channel genuinely requires a weighted Laplace-moment or noncancellation obligation.

### 3.5 Mechanical support

The script `verification/prime_block_obstruction.py`:

- differentiates arbitrary rational polynomials of degrees \(0\) through \(8\) exactly and verifies annihilation by derivative order \(d+1\);
- enumerates all 78,498 primes up to \(10^6\);
- records partial sums of the lower bound in (14) for several \(d\) and \(\eta\).

At the boundary \(\eta=1/2\), the partial lower sum for \(d=0\) grows from approximately \(8.74\) at prime cutoff \(100\) to \(92.89\) at cutoff \(10^6\). For \(\eta=1/4\), it reaches approximately \(1248.77\). These finite computations are illustrations; Euler's theorem supplies the proof of divergence.

### 3.6 Exact scope and escape routes

The theorem **rules out** a naive architecture having all of the following at once:

1. mutually orthogonal prime blocks;
2. the exact local prime-power trace transform (12);
3. origin counterterms of uniformly bounded order;
4. locally uniform trace-norm resolvent convergence on a domain meeting \(0<\operatorname{Im}z\le1/2\).

It does **not** rule out:

- nonorthogonal prime interactions, where block norms need not add;
- construction in the absolute-convergence half-plane \(\operatorname{Im}z>1/2\), followed by a separately proved continuation or renormalization;
- counterterms with unbounded order, provided their growth is declared and controlled;
- an absolutely continuous remainder whose derivative is large enough to cancel the prime part, unless a condition such as (19) or (20) is certified;
- convergence in a topology weaker than \(\mathcal S_1\);
- a global operator that has no primewise orthogonal direct-sum decomposition.

The first two are the mathematically cleanest research directions. The theorem says that prime locality cannot simultaneously mean orthogonal independence, bounded local subtraction, and trace-norm convergence through the critical boundary.

---

## 4. Verification ledger

| Item | Classification | Evidence |
|---|---|---|
| Derived-holonomy equivalence over finite-dimensional fields | **Proven** | Constructive contraction proof |
| Exact rational pass/fail certificate completeness | **Proven** | Gaussian elimination with accumulated row operations |
| Four finite derived-holonomy fixtures | **Mechanically verified** | Exact `Fraction` report |
| 153 small two-term instances | **Mechanically verified** | Exhaustive exact enumeration |
| Shifted-ladder trace-class resolvent | **Proven** | Uniform \(k^{-2}\) majorant |
| Shifted-ladder Dirac-comb trace limit | **Proven** | Schwartz pairing plus Poisson summation |
| Gaussian reproduction of the comb | **Strongly supported numerically** | 80-digit independent formulas |
| Orthogonal prime-block no-go with bounded origin jets | **Proven under explicit assumptions** | Derivative annihilation, block additivity, Euler divergence |
| Same no-go with an absolutely continuous remainder | **Proven under (19) or (20)** | Reverse triangle inequality |
| Full prime-local operator construction | **Outside current knowledge** | The theorem narrows but does not solve the construction |
| Historical novelty of Theorem 3 | **Unresolved** | Requires a dedicated literature comparison before priority claims |

## 5. Reproduction

From the `output/research` directory:

```bash
python3 verification/derived_holonomy_exact.py
python3 verification/shifted_ladder_reproduce.py
python3 verification/prime_block_obstruction.py
python3 -m py_compile verification/*.py
```

Each script writes a canonical JSON report next to itself and prints its SHA-256 digest. No network, random seed, floating package, or project installation is required. The derived-holonomy route is exact. Decimal and double-precision results are explicitly labeled as numerical corroboration rather than proof.

## 6. Highest-leverage next step

The next operator program should begin in the half-plane

\[
\operatorname{Im}z>\tfrac12,
\]

where the first-prime-power lower bound is summable, and test one of two architectures:

1. **interacting prime gluing:** construct nonorthogonal intertwiners and quantify the exact naturality defect; or
2. **renormalized continuation:** prove an operator-valued continuation across \(\operatorname{Im}z=\tfrac12\) with a declared subtraction class and a determinant identity.

Any construction retaining orthogonal blocks must explicitly give up at least one of bounded local counterterms, local uniform \(\mathcal S_1\) convergence through the boundary, or the exact prime trace law. That is now a theorem-level design boundary rather than a heuristic warning.
