# R01 forensic addendum

**Date:** 2026-07-23
**Scope:** historical interpretation only; this addendum does not alter the preserved R01 bytes, score, or stop record.

## Corrected disposition

R01 was not a candidate pass. The supplied induction argument was mathematically complete, but the frozen candidate failed execution honesty and representation consistency. The original local Return Desk replay was also controller-incomplete because it supplied only five generated outputs and omitted the exact target plus the six canonical Knowledge files. That omission invalidates that replay as a complete controller trial; it does not rescue the independent runtime and exported-payload contradictions already present in the candidate output.

The three relevant byte representations are:

| Representation | Bytes | SHA-256 | Distinguishing content |
| --- | ---: | --- | --- |
| A: preserved visible machine record | 10,129 | `07ef36ef6d469e76e710935f75fa8d7f664e1aad80700133a955aa78df5868e5` | `independently`; session reported Python `3.11.8 ... [GCC 12.2.0]`; no terminal LF |
| B: transport wrapper declaration | 10,130 | `8f4482904132b36c61d846ae43c3169a79ec1c9f12a4d3a5601e3f85f3b5e45e` | declared `independently`; Python `3.13.5 ... [GCC 14.2.0]`; terminal LF |
| C: strictly decoded exported payload | 10,127 | `3759d6d97d5d12e7cc651efc49af843cc235f0b89e8c8ab7940219ee563fc26d` | `indepently`; Python `3.13.5 ... [GCC 14.2.0]`; terminal LF |

The B-to-C difference includes deletion of the aligned Base64 quartet `ZW5k`, which decodes to `end` and changes `independently` to `indepently`. Strict downstream Base64 decoding and file writing reproduced C exactly. Therefore the downstream decoder/write path was exact for the exported payload actually received.

## What the evidence establishes

- **Mathematics:** passed. The elementary induction proof itself was complete.
- **Candidate execution/representation consistency:** failed. A and C disagree on the runtime, and B's declared size and digest do not match C.
- **Original Return Desk replay:** `trial_invalid_controller`. Its missing target and six-file Knowledge roster prevent complete replay scoring.
- **Exported-payload identity:** C is established exactly by strict decoding.
- **Download-button identity:** `transport_identity_unresolved`. No automation download event was available and authenticated external fetch was denied, so the original download bytes were unavailable.
- **Browser/download corruption:** not established. Unavailable original bytes must not be relabeled “corrupt,” and C must not be claimed byte-identical to an unavailable download.

The architectural repair follows from these separate facts: capture one session-reported runtime; generate all byte-derived projections deterministically; validate the complete controller roster before replay; and preserve candidate failure, invalid-controller, and unresolved-transport outcomes as distinct coordinates.
