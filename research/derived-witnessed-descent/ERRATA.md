# Packet errata and clarifications

These corrections do not rewrite the preserved source notes or reports.

1. In `Formal_Verification_and_Prime_Block_Obstruction.md`, the display text `f=1,quad g=0` should read `f=1,\quad g=0`.
2. "Formal verification" in the source title means a constructive mathematical proof plus exact finite certificate replay. No Lean, Coq, Isabelle, or other proof-assistant kernel checked the notes.
3. The bounded-jet orthogonal-prime-block theorem in the later formal supplement supersedes the earlier note's conditional or unresolved orthogonal-prime status under its explicitly frozen hypotheses.
4. At alpha.3 intake, the supplied checksum record listed three generators that were not supplied, so reproduction claims depending on them were blocked. Exact originals were recovered later and are recorded in `RECOVERY.json`; this does not retroactively change the published alpha.3 evidence state.
5. The source verification README's relative paths describe its original staging layout. The repository-level commands and paths in this directory's `README.md` are authoritative here.
6. The finite atomic-modulus route checks a declared finite record. It does not establish uniform integrability, local `L^p` control, a compact exhaustion, or absolute-continuity closure.
7. The prime obstruction requires its stated orthogonality, exact trace law, uniform jet-order, domain, and trace-class convergence hypotheses. Local nonconcentration alone does not rule out transform-domain cancellation.
