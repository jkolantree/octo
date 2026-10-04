# History migration and historical evidence

The privacy migration changes one owner's personal email in commit author and
committer fields to the existing GitHub noreply identity. It preserves historical
names, timestamps, commit messages, and every source tree. Parent references and
annotated-tag targets follow the rewritten graph. Commit IDs and tag object IDs
therefore change. Commit signatures over replaced objects cannot authenticate
the replacements and are removed; no replacement signatures are claimed.

The current main successor updates only active privacy policy ancestry pins,
their checker and tests, and this privacy documentation. The exact retained merge
exception remains bound to its migrated commit ID, ordered parents, subject,
author pair, and GitHub committer pair. The identity allowlists and prospective
enforcement boundary do not expand.

## Historical evidence remains historical

Research records, status files, frozen-candidate registrations, release records,
and their recorded hashes are preserved as attestations of the original history.
Their old commit IDs are historical references, not assertions that the rewritten
objects have the same identities or signatures. Matching source trees does not
reissue scientific claims or provenance attestations.

Existing uploaded release assets are historical bytes. This migration neither
rebuilds them nor verifies their payloads or removes any metadata inside them.
Their existing provenance does not attest the new commit IDs. GitHub-generated
source archives may change when their tag targets move.

Historical branches and tags retain their original source trees, including any
old policy and test pins. They are not covered by the current-main runnable test
claim and may fail ancestry-dependent checks in a repository containing only the
rewritten history. This does not justify restoring original commit objects or
relaxing exact-object checks.

## GitHub and distributed-history limits

Updating branch and tag refs does not remove original objects from pull-request
refs, review context, cached views, forks, or external clones. Pull requests may
lose their earlier diff or review context. GitHub-side retention requires separate
cleanup, and copies held elsewhere cannot be certified absent by this repository.
The migration is targeted email removal, not a claim of anonymity or complete
removal from every historical artifact.
