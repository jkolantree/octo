# BSC Audit Engine v0.3.0-alpha.18

Alpha.18 is a bounded GitHub math-renderer compatibility recovery. It
preserves the alpha.17 engine algorithms and accepted schemas while correcting
the canonical and generated documentation under a new release identity.

## What failed in alpha.17

The exact tagged `docs/MATHEMATICS.md` page displayed 12 GitHub error banners.
Every banner identified `\operatorname` as a rejected macro. The prior local
documentation gate had checked delimiters, fences, headings, links, and source
bytes, but it did not inspect commands inside active math. The prior browser
check counted `math-renderer` elements without distinguishing successful
renderers from error renderers.

This is evidence of a documentation transport and verification-harness
failure. It is not evidence that the mathematical propositions are false.
The alpha.17 tag, release, assets, and negative observation remain unchanged.

## What changed

- Observation descent now uses explicit maps $\mathcal K$ and $\mathcal D$,
  explicit composition, and the empty-intersection convention.
- Exact observed quotients state injectivity and surjectivity directly and use
  $i_n(N_n)$ for the set image.
- The generated `BSC_SUPPORTED_CHECKS.md` projection, package, manifests, and
  checksums are regenerated from the corrected canonical source.
- Documentation lint now extracts active inline and fenced mathematics,
  ignores inline code and non-math fences, and rejects commands outside a
  reviewed renderer-safe set.
- Permanent regressions reject `\operatorname` and an unknown future command
  while preserving the literal positive escape cases `\forall`, `\frac`,
  `\begin`, and `\theta`.

## Typed verification boundary

- **Product mathematics:** manual review found the stated Galois connection and
  short-exact-sequence argument correct under their explicit hypotheses.
- **Source compatibility:** local lint checks exact active commands against the
  repository's reviewed set; it does not control GitHub's future behavior.
- **Hosted transport:** commit- and tag-pinned GitHub pages must separately show
  zero renderer error signatures and the expected renderer counts.
- **Artifact identity:** release assets are bound to the exact clean tagged
  commit and tree by manifests, hashes, and keyless attestations.
- **External truth and deployment:** no scientific-truth, live-GPT binding, or
  deployment-authority conclusion follows from documentation or release
  checks.

## Preserved state

- `v0.3.0-alpha.17` and every earlier tag, release, asset, and negative result
  remain unchanged.
- The public protocol component remains byte-identical to
  `0.3.0-alpha.13`.
- The official Custom GPT remains the separately observed alpha.10 live state;
  no editor, Instructions, Knowledge, starter, capability, App, Action, or
  Preview change is part of this release.
- Indexed live Knowledge remains `NON_ADMISSIBLE_UNHASHABLE`.
- Exact-hash imported research notes retain their original bytes. A separate
  renderer-safe presentation companion is deferred rather than silently
  rewriting those sources.
- `jkolantree/BSC` remains a separate research repository and is not mutated.
