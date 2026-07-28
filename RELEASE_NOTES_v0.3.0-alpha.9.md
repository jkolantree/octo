# BSC Audit Engine v0.3.0-alpha.9

Released 2026-07-28 as a public research prerelease.

## Bounded maintenance release

Alpha.9 promotes the reviewed post-alpha.8 maintenance line under a new immutable version. It does not move, replace, or relabel `v0.3.0-alpha.8`.

The Custom GPT package now has one coherent Quick default: verdict first, no more than 250 words and four short visible blocks, normally no table, with Japanese routes primarily in Japanese. The canonical conversation starters are exactly:

1. Start a 60-second claim audit
2. 60秒で主張を点検する
3. Show a simple example first
4. まず簡単な例を見る

The no-claim starters ask only for a one-sentence claim in the selected language. The example starters give one concise example.

## Integrity and maintenance improvements

- removed requester-perspective narration and corrected stale current-status wording;
- reconciled generated Knowledge with the Quick contract;
- added positive literal-escape coverage for `\forall`, `\frac`, `\begin`, and `\theta` while retaining control-byte rejection and historical negative fixtures;
- added privacy/documentation lint for current Markdown and HTML;
- fixed mixed prose-plus-Markdown Quick block counting;
- reduced duplicate CI noise and compacted test output without removing release checks;
- regenerated package, frozen-candidate, localization, Pages, manifest, and checksum projections;
- documented the separate Boundary-State Calculus research repository without implying certification, upstream status, or shared release authority.

## Preserved boundaries

The public GPT remains a bounded interpretive research-preview interface with five Knowledge files, Web Search and Data Analysis enabled for source inspection or bounded calculations, and no Apps or Actions. It does not emit downloadable machine records, compiler output, hashes, Base64, shards, transport containers, or section 10.

The retired 39-case artifact campaign and D01/D02 preflights remain preserved historical evidence; they are not restarted or counted toward alpha.9. Alpha.9 instead uses the exact 12-case compact Preview gate, followed by fresh smoke checks for the four starters and one Quick follow-up.

## Verification boundary

Release assets are built reproducibly from the exact clean tagged commit and bind their commit, tree, tag, toolchain, sizes, and SHA-256 values in `RELEASE_MANIFEST.json` and `SHA256SUMS`. No artifact signature or release container is asserted.

Repository hashes verify Knowledge files before upload. ChatGPT does not expose independently hashable indexed Knowledge bytes, so byte-identical live Knowledge binding cannot be claimed. Saved-editor fields, the visible public starters, capabilities, filenames, and fresh behavior checks are reported separately.

This release does not publish to PyPI or Zenodo.
