# Documentation Contract

Public documentation is part of the BSC Audit Engine's correctness boundary.
It must render predictably, identify the authority of its conclusions, avoid
leaking private machine state, and remain reproducible from canonical sources.

## Mathematical notation

Use GitHub-native MathJax syntax:

- inline mathematics: `$T_\alpha$`;
- displayed mathematics: a fenced `math` block;
- executable identifiers and literal syntax: backticks.

Example:

```math
\forall x,\qquad
\frac{a}{b},\qquad
\begin{aligned}
f(\theta)&=\theta^2.
\end{aligned}
```

Do not use the unsupported display delimiters `\[` and `\]` or inline
delimiters `\(` and `\)` outside code. A fenced `math` block renders on GitHub
and remains a readable code block in CommonMark viewers without MathJax.
Introduce every important formula in prose so the surrounding argument does
not depend on visual rendering alone.

## Conclusion typing

For every consequential conclusion, make these coordinates recoverable:

1. **subject** — the exact claim, artifact, execution, or deployment;
2. **scope** — the admitted language, hypotheses, inputs, and limits;
3. **method** — the reasoning, checker, measurement, or observation;
4. **evidence identity** — the concrete file, fixture, receipt, digest, or
   public observation;
5. **authority** — what the result may and may not establish.

Keep mathematical correctness, product behavior, exact artifact identity,
actual execution, harness validity, transport behavior, external truth,
release state, and deployment authority separate. A shared label such as
`pass`, `verified`, or `proven` never transfers authority between them.

## Thresholds and limits

Treat an external ceiling as a failure cliff. Unless exact saturation is
intrinsic to the result, specify and test safety headroom proportionate to
uncertainty, drift, and blast radius. A boundary pass is evidence of nominal
acceptance, not of robustness.

State resource rejections as rejections. Do not turn an unexecuted,
out-of-envelope, unavailable, or invalid-harness result into a product pass or
failure.

## Canonical and generated files

Edit canonical sources only. Regenerate projections with their owning script:

- `gpt/` public package files come from `gpt/_source/`, canonical repository
  documents, and `scripts/build_gpt_package.py`;
- `pages/protocol/`, `pages/profile.js`, and `pages/protocol/meta.js` come from
  `scripts/build_publication_assets.py`;
- Japanese freshness metadata is verified by
  `scripts/check_localization.py`; its exact hashes are updated as a reviewed
  manifest edit after both source and translation bytes are final;
- frozen candidate hashes come from
  `scripts/check_gpt_frozen_candidate.py`.

Generated files must have one top-level heading and must not strengthen,
truncate, or silently reinterpret their canonical source.

## Privacy and publication safety

Public prose must not contain:

- local absolute paths, `file:` URLs, account data, private evidence, or raw
  browser captures;
- control, bidirectional-override, or invisible format characters;
- active HTML such as `script`, `iframe`, `object`, `embed`, or `form`;
- a release-acceptance rule based only on a magic asset count.

Use HTTPS for external references. Local Markdown links must resolve inside the
tracked publication tree. Keep security examples inside code fences so they
remain inert.

## Preservation boundary

Current normative documentation is linted. Immutable historical evidence,
frozen evaluation derivatives, and separately governed research artifacts are
not silently rewritten for presentation. If one needs a new renderer-friendly
edition, create a newly identified derivative and preserve the original bytes
and digest.

## Author check

Run:

```bash
python scripts/check_documentation.py
python scripts/verify.py candidate
```

The focused checker establishes repository documentation structure, safe
source syntax, and local-link integrity. It does not establish the truth of a
mathematical proposition, the validity of an external source, public
deployment, or live Custom GPT binding.
