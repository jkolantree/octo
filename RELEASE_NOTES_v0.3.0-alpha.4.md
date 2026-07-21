# BSC Audit Engine v0.3.0-alpha.4

This research-preview release restores the three exact original generators that were unavailable at the alpha.3 intake boundary and adds an accessible, local-only route for preparing versioned LLM audit packets.

## Exact generator recovery

- Recovered `derived_holonomy_exact.py`, `shifted_ladder_reproduce.py`, and `prime_block_obstruction.py` without reconstruction.
- Verified their bytes against the checksum record preserved before recovery.
- Bound the supplied archive, each recovered script, the three reports, and the replay result in `RECOVERY.json`.
- Regenerate reports only after fail-closed hash checks and inside an isolated temporary directory.
- Preserve alpha.3's original missing-generator statement as historical provenance rather than rewriting it.

## Accessible local packet builder

- Open <https://jkolantree.github.io/octo/>, paste or attach target material, choose quick, standard, adversarial, or formal depth, then copy or download the packet.
- The static page reads target material only in the browser. It has no login, analytics, cookies, storage, service worker, form submission, or cross-origin request capability.
- The page verifies the canonical protocol bytes against committed SHA-256 metadata before enabling output.
- Text files up to 1 MiB are embedded. Other files remain companion attachments; files up to 25 MiB receive a local SHA-256.
- Keyboard navigation, visible focus, semantic labels, reduced-motion handling, forced-color support, narrow layouts, and a pauseable demonstration are part of the checked interface.

The builder does not call an LLM, upload target material, or run the Python checker. Generated LLM output remains a draft. Users must separately assess a model provider's privacy terms before sending material.

## Publication assets

The deterministic release build now emits:

- `START_HERE.txt`;
- `BSC_AUDIT_COPY_PASTE.txt`;
- `BSC_AUDIT_UPLOAD_TO_LLM.txt`;
- `BSC_AUDIT_SYSTEM_PROMPT.txt`;
- `BSC_AUDIT_LLM_PACKET.md` and `BSC_AUDIT_SCHEMA.json`;
- `BSC_AUDIT_EXAMPLES.zip` and `BSC_AUDIT_PUBLICATION.json`;
- `bsc-audit-complete.zip` plus the existing source, package, conformance, SBOM, manifest, and checksum artifacts.

The release deliberately does not add a shortened protocol capsule. Until normative sections are mechanically classified, shortening the protocol could silently weaken fatal gates.

## Verification boundary

The unchanged recovered scripts calculate their printed report hashes over LF bytes while Windows text mode writes CRLF. The recovery checker permits only that CRLF-to-LF canonicalization, then requires exact report bytes and preserved digests. It does not authenticate the archive's external origin, establish historical novelty, or perform proof-assistant kernel verification.

As with earlier previews, `no_blocking_findings` means only that no implemented blocking condition fired on the declared finite input. It is not a theorem, empirical replication, safety certification, or deployment authorization.
