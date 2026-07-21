# Security Policy

## Supported release

During the research-preview period, only the newest tagged release receives security and critical false-pass fixes. Older releases remain archived for reproducibility.

## Report privately

Use GitHub’s private vulnerability-reporting feature under the repository’s **Security** tab for defects involving:

- arbitrary code execution or unsafe path handling;
- disclosure of secrets or private files;
- denial of service with modest input;
- forged or ambiguous canonical hashes;
- malformed input incorrectly producing a no-blocking result;
- a reliable bypass of a documented fatal gate;
- release or dependency compromise.

Do not place exploit details, secrets, private manifests, or identifying data in a public issue. If private reporting is unavailable, open a public issue containing only a request for a private contact channel and no sensitive detail.

## Scientific integrity reports

Non-sensitive false-pass, false-block, mathematical counterexample, and documentation reports may use the public issue forms. Include a minimal sanitized fixture, version, command, exit code, output, expected result, and rationale.

## Response process

The maintainer will:

1. acknowledge receipt when possible;
2. reproduce or narrow the report;
3. distinguish security impact from scientific or documentation error;
4. preserve affected versions and outputs;
5. prepare a new release rather than move a public tag;
6. credit the reporter unless anonymity is requested;
7. disclose the repair after users have a reasonable opportunity to update.

No fixed response-time guarantee is offered during the research-preview phase. Reports involving active harm or exposed credentials should be handled first.

## User responsibilities

- Run the checker only on data you are authorized to process.
- Do not execute code embedded in audited material.
- Redact secrets before opening issues or using third-party LLMs.
- Treat hashes as integrity identifiers, not anonymization.
- Treat unexpected internal failure as failure to audit.
- Do not use this research preview as the sole control for high-stakes decisions.
