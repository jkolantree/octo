# BSC v1.2 Simulation-Evidence Crosswalk

This document records one deliberately narrow bridge from the separately
published Boundary-State Calculus v1.2.0 simulation profile into the existing
BSC Audit Engine `defect` route. It adds no general simulation validator, new
schema, or deployment authority.

## Immutable upstream evidence

| Subject | Scope | Method | Evidence identity | Authority |
|---|---|---|---|---|
| BSC v1.2.0 source | Published upstream release | Git tag and Git-tree identity | [release `v1.2.0`](https://github.com/jkolantree/BSC/releases/tag/v1.2.0), commit `5fdcb3e1de15b04ed037da135717d316e45f28b1`, tree `7328eee577c7595c5381e129c62d5c0b1fe78e30` | Identifies the upstream source; does not transfer its claims into octo |
| Version record | BSC v1.2.0 deposit | Public Zenodo record | [version DOI `10.5281/zenodo.21711341`](https://doi.org/10.5281/zenodo.21711341) | Identifies the deposited release |
| Published paper | [`paper/On_Boundaries_of_Evidence.pdf`](https://github.com/jkolantree/BSC/blob/5fdcb3e1de15b04ed037da135717d316e45f28b1/paper/On_Boundaries_of_Evidence.pdf) | SHA-256 over exact file bytes | `106631826fc417549d68927418759b856e5610c7c0c27ab53c33665994a60b8c` | Release context; not a separate executable dependency |
| Simulation profile | [`framework/Simulation_Evidence_Profile.md`](https://github.com/jkolantree/BSC/blob/5fdcb3e1de15b04ed037da135717d316e45f28b1/framework/Simulation_Evidence_Profile.md) | SHA-256 over exact file bytes | `2f6ebf949995cf4e3b955cea2d4e52612d08b27668a46d9177767e9b9b5ed7ac` | Mathematical source for BSC-SIM-03 and F10 |
| F10 input | [`fixtures/F10_coupled_surrogate/input.json`](https://github.com/jkolantree/BSC/blob/5fdcb3e1de15b04ed037da135717d316e45f28b1/fixtures/F10_coupled_surrogate/input.json) | SHA-256 over exact file bytes | `cb8ffa494ace2cc204d02f3060eaf04783abb89b0c66c161c42415b8538f9497` | Identifies the exact fixture contract |
| F10 retained receipt | [`fixtures/F10_coupled_surrogate/verification_receipt.json`](https://github.com/jkolantree/BSC/blob/5fdcb3e1de15b04ed037da135717d316e45f28b1/fixtures/F10_coupled_surrogate/verification_receipt.json) | SHA-256 over exact file bytes | `7296f8aa486c52669eee34b83889cae177d51c059696a52646f3135e86d630b8` | Records the upstream exact rational replay and state paths |

Source attribution: J. Tree, *On Boundaries of Evidence / Boundary-State
Calculus* v1.2.0. Upstream paper and documentation are
[CC BY 4.0](https://github.com/jkolantree/BSC/blob/5fdcb3e1de15b04ed037da135717d316e45f28b1/LICENSES/paper-and-documentation.txt);
machine-readable fixture tooling is
[MIT licensed](https://github.com/jkolantree/BSC/blob/5fdcb3e1de15b04ed037da135717d316e45f28b1/LICENSES/code.txt).
This is an independently written octo crosswalk; it copies no upstream source
file and grants no authority across repositories.

The dependency slice is the simulation profile plus the identified F10 input
and receipt. `Normalized_Scale_Profiles.md` is not a mathematical dependency
of this recurrence.

## Three meanings that do not collapse

BSC v1.2 distinguishes statistical simulation, computational simulation, and
surrogate deployment. The shared word “simulation” transfers no evidence
authority between them. This octo bridge concerns only a finite exact
coupled-surrogate recurrence.

For one declared stage, octo stores a nonnegative amplification bound $L$, a
new discrepancy bound $\varepsilon$, and a failure-probability upper bound
$\alpha$. If stage 1 precedes stage 2, `AffineDefect.then` computes

```math
(L_1,\varepsilon_1,\alpha_1)
\mathrm{then}
(L_2,\varepsilon_2,\alpha_2)
=
\left(
L_2L_1,\,
\varepsilon_2+L_2\varepsilon_1,\,
\min(1,\alpha_1+\alpha_2)
\right).
```

For the F10 projection, every stage has
$(L,\varepsilon,\alpha)=(a_h,1/100,0)$. Folding ten stages from the identity
gives the BSC-SIM-03 prefix expression

```math
E_n
=
\frac{1}{100}\sum_{r=0}^{n-1}a_h^r.
```

The octo kernel establishes exact composition of the supplied rational upper
bounds. It does not establish that a supplied bound equals actual simulator
error. The sidecar names this authority
`exact_propagation_of_supplied_affine_upper_bounds_only`.

## Why the F10 violation is stronger than an octo bound

The upstream F10 fixture separately binds the exact reference and surrogate
recurrences, both initial states, every exact state-path value, and the
equality between their actual error and the recurrence above. That equality
witness is why Host B is a proved fixture violation. An upper bound above a
tolerance would be inconclusive without it.

| Host | Exact evidence | Exact tolerance comparison | Disposition basis |
|---|---|---|---|
| A | $E_{10}=1023/51200$ | $1/20-E_{10}=1537/51200$ | `violation_basis = none` |
| B before crossing | $E_6=468559/10000000$ | $E_6<1/20$ | no violation through step 6 |
| B first crossing | exact state-path error at step 7 | $E_7-1/20=217031/100000000$ | `violation_basis = exact_actual_error_above_tolerance` |
| B endpoint | exact state-path error at step 10 | $E_{10}-1/20=1513215599/100000000000$ | same exact-actual-error basis |

The repository examples
[`defect_f10_host_a.json`](../examples/defect_f10_host_a.json) and
[`defect_f10_host_b.json`](../examples/defect_f10_host_b.json) are valid
`defect-v0.3` inputs. The companion
[`f10_coupled_surrogate_crosswalk.json`](../examples/f10_coupled_surrogate_crosswalk.json)
preserves the external receipt identity and the `violation_basis` distinction.
It is a crosswalk record, not a new CLI input schema.

## Admission and additional headroom

BSC v1.2 Theorem 4.2 admits a numeric deployment coordinate under its stated
hypotheses when

```math
U^0_{c,j}+\rho_{c,j}\le\tau_{c,j}.
```

Equality is admissible under that theorem but has zero certified slack. A
stricter octo release or deployment policy may instead require

```math
U^0_{c,j}+\rho_{c,j}+\gamma_{c,j}\le\tau_{c,j},
\qquad
\gamma_{c,j}>0.
```

Here $\gamma_{c,j}$ is explicit safety headroom chosen by octo policy; it is
not part of the BSC theorem and is not the BSC Boolean hard-gate symbol
$g_{c,k}$. Alpha.20 documents this policy distinction but adds no general
deployment-admission route.

## Typed conclusion boundary

| Coordinate | Alpha.20 conclusion |
|---|---|
| Product correctness | By definition and exact-arithmetic regression design, the existing octo kernel composes the supplied ten-stage rational records; an execution result requires a separately identified test or CI receipt. |
| Artifact identity | The crosswalk binds the upstream release, simulation profile, F10 input, and retained receipt identities listed above. |
| Actual execution | This static document asserts no fresh octo execution receipt. The separately identified BSC receipt records the upstream exact state-path execution. |
| Verification-harness validity | When run, `tests/test_defect.py` recomputes every prefix and comparison. That regression does not replace the upstream checker, schema, or negative mutants, and its validity must be established independently of any product result. |
| Transport behavior | Source and release gates can bind these public files. No live Custom GPT or indexed-Knowledge identity follows. |
| External truth | The fixture falsifies one universal same-error/same-disposition claim. It establishes no accuracy for an untested simulator or physical system. |
| Deployment authority | Not granted. Every applicable intended-use coordinate, gate, readiness condition, and evidence identity remains independently required. |

The BSC and octo repositories retain separate histories, licenses, versions,
claims, and release gates. Octo does not certify the paper or become its proof
engine, and BSC v1.2 does not certify an octo release.
