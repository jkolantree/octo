## Exact change

State the behavior, documentation, schema, or mathematical claim changed.

## Scope and non-claims

- In scope:
- Not established by this change:

## Reproduction

```text
commands, versions, and expected exit codes
```

## Evidence

- [ ] Positive known-answer fixture
- [ ] Negative fixture with minimal witness
- [ ] Boundary or malformed-input fixture where relevant
- [ ] Ordinary baseline or simpler alternative considered

## Public contract

- [ ] Documentation updated
- [ ] Schema and migration updated if needed
- [ ] Changelog updated
- [ ] No fatal gate was weakened into a score
- [ ] Prior negative results remain preserved
- [ ] No secrets, identifying data, or incompatible third-party material included

## Gate review, if applicable

- Activation scope:
- Mathematical or methodological basis:
- False-pass cost:
- False-block cost:
- Independent reviewer:
- Retirement condition:

## Verification

- [ ] `python -m unittest discover -s tests -v`
- [ ] `git diff --check`
- [ ] Relevant example decisions and exit codes checked
