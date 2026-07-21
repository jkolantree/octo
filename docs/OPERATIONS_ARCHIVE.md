# Preserved release-operation branch tips

The following merged one-shot publication branch tips were recorded before ref
cleanup. These commit identifiers preserve the audit trail after the temporary
operational refs are deleted.

| Branch | Preserved tip | Pull request | Purpose |
| --- | --- | --- | --- |
| `ops/publish-v0.3.0-alpha.2` | `3ce5764f76699be5004940d167836789f6b0d9a9` | [#2](https://github.com/jkolantree/octo/pull/2) | Install the authorized one-shot publisher. |
| `ops/retry-v0.3.0-alpha.2-publication` | `c75c8109fd2d4e0e517c54ef5a096660da23b697` | [#3](https://github.com/jkolantree/octo/pull/3) | Correct the workflow-dispatch target without moving the tag. |
| `ops/finalize-v0.3.0-alpha.2-publication` | `15a8460b7c95fe93fad574ac8fcf186760287144` | [#4](https://github.com/jkolantree/octo/pull/4) | Correct checksum verification before publication. |
| `ops/remove-alpha2-publisher` | `559f4a03ad79cf86f7cf12e825a2fac09b9ac278` | [#5](https://github.com/jkolantree/octo/pull/5) | Remove the temporary privileged workflow. |

The immutable release tag remains `v0.3.0-alpha.2` at
`fa61f02d555a1c1a4db0b07ccb23c794ca4e8e84`.
