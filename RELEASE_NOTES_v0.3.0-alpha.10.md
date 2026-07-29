# BSC Audit Engine v0.3.0-alpha.10

Released 2026-07-28 as a public research prerelease.

## Exact starter-routing correction

Alpha.10 fixes the single failed post-save alpha.9 starter smoke without moving or rewriting the alpha.9 tag, release, assets, or history.

Exact literal matching now runs before generic intent inference:

1. `Start a 60-second claim audit` requests only a one-sentence claim in English, then stops.
2. `60秒で主張を点検する` requests only a one-sentence claim in Japanese, then stops.
3. `Show a simple example first` returns one concise Quick example in English.
4. `まず簡単な例を見る` returns one concise Quick example in Japanese.

Permanent generator and unit tests reject changed order, missing or duplicate starters, and behavior remapping. The bounded Quick contract remains verdict first, no more than 250 words and four short visible blocks, normally no table.

Live Instructions operate below a hard 6,000-character cap, 75% of the 8,000-character Builder maximum. Every reviewed fatal and required rule text remains in the live field; only machine-oriented rule IDs move out of that field and remain exact in the canonical profile.

Checker 1.4 validates the four ordered Quick sections semantically. It accepts harmless short heading qualifiers and display-math line wrapping while still rejecting missing, duplicate, reordered, empty, or fifth sections. The first alpha.10 freeze exposed this controller-format defect and was preserved as invalid controller evidence; the counted suite restarted from Case 1 in ChatGPT Preview's normal/default model mode. That model setting is separate from the BSC audit-depth default of Quick.

## Preserved evidence and scope

The exact alpha.9 candidate passed its predetermined 12-case compact Preview gate before release and live Update. Its later fresh post-save smoke then preserved one real failure: the Japanese claim-audit starter returned an example before requesting the claim. That negative result remains alpha.9 evidence and is not reused as an alpha.10 pass.

Alpha.10 does not change the five-Knowledge roster, capability settings, Apps or Actions, engine schemas, research repository, historical 39-case campaign, or the authority of any checker result.

## Verification boundary

Release assets are built reproducibly from the exact clean tagged commit and bind their commit, tree, tag, toolchain, sizes, and SHA-256 values in `RELEASE_MANIFEST.json` and `SHA256SUMS`. No artifact signature or release container is asserted.

Repository hashes verify Knowledge files before upload. ChatGPT does not expose independently hashable indexed Knowledge bytes, so byte-identical live Knowledge binding cannot be claimed. Saved-editor fields, visible public starters, capabilities, filenames, and fresh behavior checks are reported separately.

This release does not publish to PyPI or Zenodo.
