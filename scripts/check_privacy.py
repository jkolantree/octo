#!/usr/bin/env python3
"""Fail closed on pseudonymous-publication privacy invariants."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
import tarfile
import tomllib
import zipfile
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Iterable
from xml.etree import ElementTree as ET


ROOT = Path(__file__).resolve().parents[1]
POLICY_PATH = ROOT / "privacy-policy.json"

EMAIL_RE = re.compile(r"(?<![A-Za-z0-9._%+-])[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}(?![A-Za-z0-9.-])")
PHONE_RES = (
    re.compile(r"(?<!\w)\+\d{1,3}[ .-](?:\(?\d{2,4}\)?[ .-]){1,3}\d{3,4}(?!\w)"),
    re.compile(r"(?<!\d)\(?\d{3}\)?[ .-]\d{3}[ .-]\d{4}(?!\d)"),
)
LOCAL_PATH_RES = (
    re.compile(r"(?:^|[\s\"'=(])/(?:Users|home|workspace|root)/[^\s\"'<>]+"),
    re.compile(r"(?:^|[\s\"'=(])[A-Za-z]:\\Users\\[^\s\"'<>]+", re.IGNORECASE),
    re.compile(r"file:" + r"///[^\s\"'<>]+", re.IGNORECASE),
)
SECRET_RES = (
    ("GITHUB_TOKEN", re.compile(r"(?:github_pat_|gh[pousr]_)[A-Za-z0-9_]{20,}")),
    ("AWS_ACCESS_KEY", re.compile(r"(?:AKIA|ASIA)[0-9A-Z]{16}")),
    ("OPENAI_KEY", re.compile(r"sk-[A-Za-z0-9_-]{20,}")),
    ("SLACK_TOKEN", re.compile(r"xox[baprs]-[A-Za-z0-9-]{10,}")),
    ("GOOGLE_API_KEY", re.compile(r"AIza[0-9A-Za-z_-]{30,}")),
    ("PRIVATE_KEY", re.compile(r"-----BEGIN (?:[A-Z ]+ )?PRIVATE KEY-----")),
)

TEXT_SUFFIXES = {
    "",
    ".cff",
    ".css",
    ".html",
    ".in",
    ".js",
    ".json",
    ".jsonl",
    ".lock",
    ".md",
    ".py",
    ".sha256",
    ".toml",
    ".txt",
    ".yaml",
    ".yml",
}
ARCHIVE_SUFFIXES = {".docx", ".whl", ".zip"}

DC = "http://purl.org/dc/elements/1.1/"
DCTERMS = "http://purl.org/dc/terms/"
CP = "http://schemas.openxmlformats.org/package/2006/metadata/core-properties"
EP = "http://schemas.openxmlformats.org/officeDocument/2006/extended-properties"
W = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"


@dataclass(frozen=True)
class Finding:
    code: str
    path: str
    message: str

    def as_dict(self) -> dict[str, str]:
        return {"code": self.code, "path": self.path, "message": self.message}


@dataclass(frozen=True)
class Policy:
    version: str
    project_identities: frozenset[str]
    bot_identities: frozenset[str]
    bot_emails: frozenset[str]
    enforcement_base_commit: str
    pipeline_identity: str

    @property
    def identities(self) -> frozenset[str]:
        return self.project_identities | self.bot_identities


def load_policy(path: Path = POLICY_PATH) -> Policy:
    raw = json.loads(path.read_text(encoding="utf-8"))
    expected_keys = {
        "policy_version",
        "allowed_project_identities",
        "allowed_bot_identities",
        "allowed_bot_emails",
        "enforcement_base_commit",
        "publication_pipeline_identity",
    }
    if set(raw) != expected_keys:
        raise ValueError("privacy policy fields differ from the registered contract")
    project = frozenset(raw["allowed_project_identities"])
    bots = frozenset(raw["allowed_bot_identities"])
    bot_emails = frozenset(raw["allowed_bot_emails"])
    if project != frozenset({"J. Tree", "Tree, J.", "jtree", "jkolantree"}):
        raise ValueError("project identity allowlist has drifted")
    if bots != frozenset({"GitHub", "github-actions[bot]", "web-flow"}):
        raise ValueError("GitHub bot identity allowlist has drifted")
    if any(not email.endswith(("@users.noreply.github.com", "@github.com")) for email in bot_emails):
        raise ValueError("bot email allowlist contains a non-GitHub address")
    enforcement_base = raw["enforcement_base_commit"]
    if enforcement_base != "2c611ab693f09bc2f3b5304f972d9a3b8a8f1969":
        raise ValueError("privacy enforcement base commit has drifted")
    return Policy(
        version=raw["policy_version"],
        project_identities=project,
        bot_identities=bots,
        bot_emails=bot_emails,
        enforcement_base_commit=enforcement_base,
        pipeline_identity=raw["publication_pipeline_identity"],
    )


def _redacted(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8", errors="replace")).hexdigest()[:12]


def _allowed_email(value: str, policy: Policy) -> bool:
    if value in policy.bot_emails:
        return True
    if not value.endswith("@users.noreply.github.com"):
        return False
    local = value.split("@", 1)[0].lower()
    return re.fullmatch(r"(?:\d+\+)?(?:jtree|jkolantree)", local) is not None


def scan_text(label: str, text: str, policy: Policy) -> list[Finding]:
    findings: list[Finding] = []
    for match in EMAIL_RE.finditer(text):
        value = match.group(0)
        if not _allowed_email(value, policy):
            findings.append(Finding("EMAIL_NOT_ALLOWLISTED", label, f"unapproved email fingerprint {_redacted(value)}"))
    for pattern in PHONE_RES:
        for match in pattern.finditer(text):
            findings.append(Finding("PHONE_NUMBER_PRESENT", label, f"telephone-like value fingerprint {_redacted(match.group(0))}"))
    for pattern in LOCAL_PATH_RES:
        for match in pattern.finditer(text):
            findings.append(Finding("LOCAL_PATH_PRESENT", label, f"local path fingerprint {_redacted(match.group(0))}"))
    for code, pattern in SECRET_RES:
        for match in pattern.finditer(text):
            findings.append(Finding(code, label, f"secret-like value fingerprint {_redacted(match.group(0))}"))
    return findings


def _safe_member(name: str) -> bool:
    path = PurePosixPath(name.replace("\\", "/"))
    return not path.is_absolute() and ".." not in path.parts


def _decode_text(data: bytes) -> str:
    if b"\x00" in data[:4096]:
        raise UnicodeError("binary data")
    return data.decode("utf-8")


def _scan_payload(label: str, data: bytes, suffix: str, policy: Policy) -> list[Finding]:
    if suffix in TEXT_SUFFIXES:
        try:
            return scan_text(label, _decode_text(data), policy)
        except (UnicodeDecodeError, UnicodeError):
            return [Finding("UNSUPPORTED_BINARY", label, "tracked payload declared as text is not UTF-8 text")]
    if suffix == ".pdf":
        return scan_pdf_bytes(label, data, policy)
    return [Finding("UNSUPPORTED_BINARY", label, f"binary suffix {suffix or '<none>'} has no registered privacy scanner")]


def _xml_text(root: ET.Element, tag: str) -> str | None:
    element = root.find(tag)
    if element is None or element.text is None:
        return None
    value = element.text.strip()
    return value or None


def scan_docx(path: Path, policy: Policy, label: str | None = None) -> list[Finding]:
    shown = label or path.as_posix()
    findings: list[Finding] = []
    try:
        with zipfile.ZipFile(path) as archive:
            names = archive.namelist()
            if len(names) != len(set(names)):
                findings.append(Finding("ARCHIVE_DUPLICATE_MEMBER", shown, "DOCX contains duplicate member names"))
            for name in names:
                member_label = f"{shown}!{name}"
                if not _safe_member(name):
                    findings.append(Finding("ARCHIVE_UNSAFE_MEMBER", member_label, "archive member escapes its root"))
                    continue
                data = archive.read(name)
                if name.endswith((".xml", ".rels")):
                    try:
                        text = data.decode("utf-8")
                    except UnicodeDecodeError:
                        findings.append(Finding("DOCX_XML_NOT_UTF8", member_label, "DOCX XML is not UTF-8"))
                        continue
                    findings.extend(scan_text(member_label, text, policy))
                    if name.endswith(".rels") and re.search(r"TargetMode=[\"']External[\"']", text, re.IGNORECASE):
                        findings.append(Finding("DOCX_EXTERNAL_RELATIONSHIP", member_label, "external document relationship is not permitted"))

            core = ET.fromstring(archive.read("docProps/core.xml"))
            creator = _xml_text(core, f"{{{DC}}}creator")
            if creator not in policy.project_identities:
                findings.append(Finding("DOCX_CREATOR_NOT_ALLOWLISTED", f"{shown}!docProps/core.xml", "creator is missing or unapproved"))
            if _xml_text(core, f"{{{CP}}}lastModifiedBy") is not None:
                findings.append(Finding("DOCX_LAST_MODIFIER_PRESENT", f"{shown}!docProps/core.xml", "lastModifiedBy must be absent"))
            for tag in ("created", "modified"):
                if _xml_text(core, f"{{{DCTERMS}}}{tag}") is not None:
                    findings.append(Finding("DOCX_TIMESTAMP_PRESENT", f"{shown}!docProps/core.xml", f"{tag} timestamp must be absent"))

            app = ET.fromstring(archive.read("docProps/app.xml"))
            application = _xml_text(app, f"{{{EP}}}Application")
            if application != policy.pipeline_identity:
                findings.append(Finding("DOCX_APPLICATION_FINGERPRINT", f"{shown}!docProps/app.xml", "application identity is not the generic publication pipeline"))
            for tag in ("AppVersion", "Company", "Manager", "Template", "TotalTime"):
                if _xml_text(app, f"{{{EP}}}{tag}") is not None:
                    findings.append(Finding("DOCX_EXTENDED_METADATA_PRESENT", f"{shown}!docProps/app.xml", f"{tag} must be absent"))

            if "word/comments.xml" in names:
                comments = ET.fromstring(archive.read("word/comments.xml"))
                for comment in comments.findall(f".//{{{W}}}comment"):
                    author = comment.get(f"{{{W}}}author")
                    if author and author not in policy.identities:
                        findings.append(Finding("DOCX_COMMENT_AUTHOR_NOT_ALLOWLISTED", f"{shown}!word/comments.xml", "comment author is unapproved"))
    except (KeyError, ET.ParseError, OSError, zipfile.BadZipFile) as exc:
        findings.append(Finding("DOCX_UNREADABLE", shown, f"DOCX privacy inspection failed: {type(exc).__name__}"))
    return findings


PDF_FIELD_RE = re.compile(rb"/(Author|Creator|Producer|CreationDate|ModDate)\s*(<[^>]*>|\((?:\\.|[^)])*\))")


def _decode_pdf_value(raw: bytes) -> str:
    if raw.startswith(b"<"):
        payload = bytes.fromhex(re.sub(rb"\s+", b"", raw[1:-1]).decode("ascii"))
        if payload.startswith(b"\xfe\xff"):
            return payload[2:].decode("utf-16-be", errors="replace")
        return payload.decode("latin-1", errors="replace")
    payload = raw[1:-1]
    payload = re.sub(
        rb"\\([0-7]{1,3})",
        lambda match: bytes([int(match.group(1), 8)]),
        payload,
    )
    payload = re.sub(rb"\\([()\\])", rb"\1", payload)
    return payload.decode("latin-1", errors="replace")


def scan_pdf_bytes(label: str, data: bytes, policy: Policy) -> list[Finding]:
    findings: list[Finding] = []
    printable = data.decode("latin-1", errors="ignore")
    null_stripped = data.replace(b"\x00", b"").decode("latin-1", errors="ignore")
    # Binary PDF streams generate telephone-shaped byte sequences by chance.
    # Retain every high-confidence text check while leaving telephone detection
    # to actual text/XML members and structured PDF metadata fields.
    findings.extend(
        finding
        for finding in scan_text(label, printable + "\n" + null_stripped, policy)
        if finding.code != "PHONE_NUMBER_PRESENT"
    )

    fields: dict[str, list[str]] = {}
    for match in PDF_FIELD_RE.finditer(data):
        fields.setdefault(match.group(1).decode("ascii"), []).append(_decode_pdf_value(match.group(2)))
    authors = fields.get("Author", [])
    if not authors or any(author not in policy.project_identities for author in authors):
        findings.append(Finding("PDF_AUTHOR_NOT_ALLOWLISTED", label, "PDF author is missing or unapproved"))
    for field in ("Creator", "Producer"):
        values = fields.get(field, [])
        if not values or any(value != policy.pipeline_identity for value in values):
            findings.append(Finding("PDF_TOOL_FINGERPRINT", label, f"PDF {field.lower()} is not the generic publication pipeline"))
    for field in ("CreationDate", "ModDate"):
        if fields.get(field):
            findings.append(Finding("PDF_TIMESTAMP_PRESENT", label, f"PDF {field} must be absent"))
    if b"<x:xmpmeta" in data or b"/Metadata" in data:
        findings.append(Finding("PDF_XMP_PRESENT", label, "XMP metadata must be removed from the public PDF"))
    for token in (b"LibreOffice", b"Microsoft Word", b"X86_64", b" KST"):
        if token in data:
            findings.append(Finding("PDF_TOOL_FINGERPRINT", label, "detailed PDF producer or environment fingerprint remains"))
    return findings


def scan_zip(path: Path, policy: Policy) -> list[Finding]:
    findings: list[Finding] = []
    try:
        with zipfile.ZipFile(path) as archive:
            names = archive.namelist()
            if len(names) != len(set(names)):
                findings.append(Finding("ARCHIVE_DUPLICATE_MEMBER", path.as_posix(), "archive contains duplicate member names"))
            for name in names:
                label = f"{path.as_posix()}!{name}"
                if name.endswith("/"):
                    continue
                if not _safe_member(name):
                    findings.append(Finding("ARCHIVE_UNSAFE_MEMBER", label, "archive member escapes its root"))
                    continue
                data = archive.read(name)
                suffix = Path(name).suffix.lower()
                if suffix in TEXT_SUFFIXES or suffix == ".pdf":
                    findings.extend(_scan_payload(label, data, suffix, policy))
                elif suffix in ARCHIVE_SUFFIXES or name.endswith(".tar.gz"):
                    findings.append(Finding("NESTED_ARCHIVE_UNSCANNED", label, "nested archive requires an explicit scanner"))
    except (OSError, zipfile.BadZipFile) as exc:
        findings.append(Finding("ARCHIVE_UNREADABLE", path.as_posix(), f"ZIP privacy inspection failed: {type(exc).__name__}"))
    return findings


def scan_tar(path: Path, policy: Policy) -> list[Finding]:
    findings: list[Finding] = []
    try:
        with tarfile.open(path, "r:gz") as archive:
            names: set[str] = set()
            for member in archive.getmembers():
                label = f"{path.as_posix()}!{member.name}"
                if member.name in names:
                    findings.append(Finding("ARCHIVE_DUPLICATE_MEMBER", label, "archive contains a duplicate member name"))
                names.add(member.name)
                if not _safe_member(member.name) or member.issym() or member.islnk():
                    findings.append(Finding("ARCHIVE_UNSAFE_MEMBER", label, "archive member is unsafe or link-valued"))
                    continue
                if not member.isfile():
                    continue
                stream = archive.extractfile(member)
                if stream is None:
                    findings.append(Finding("ARCHIVE_MEMBER_UNREADABLE", label, "regular archive member could not be read"))
                    continue
                data = stream.read()
                suffix = Path(member.name).suffix.lower()
                if suffix in TEXT_SUFFIXES or suffix == ".pdf":
                    findings.extend(_scan_payload(label, data, suffix, policy))
                elif suffix in ARCHIVE_SUFFIXES or member.name.endswith(".tar.gz"):
                    findings.append(Finding("NESTED_ARCHIVE_UNSCANNED", label, "nested archive requires an explicit scanner"))
    except (OSError, tarfile.TarError) as exc:
        findings.append(Finding("ARCHIVE_UNREADABLE", path.as_posix(), f"tar privacy inspection failed: {type(exc).__name__}"))
    return findings


def scan_path(path: Path, policy: Policy) -> list[Finding]:
    suffix = path.suffix.lower()
    if suffix == ".docx":
        return scan_docx(path, policy)
    if suffix in {".zip", ".whl"}:
        return scan_zip(path, policy)
    if path.name.endswith(".tar.gz"):
        return scan_tar(path, policy)
    try:
        data = path.read_bytes()
    except OSError as exc:
        return [Finding("FILE_UNREADABLE", path.as_posix(), f"file could not be read: {type(exc).__name__}")]
    return _scan_payload(path.as_posix(), data, suffix, policy)


def tracked_paths() -> list[Path]:
    result = subprocess.run(["git", "ls-files", "-z"], cwd=ROOT, capture_output=True, check=False)
    if result.returncode != 0:
        raise RuntimeError("git ls-files failed")
    return [ROOT / item.decode("utf-8") for item in result.stdout.split(b"\0") if item]


def validate_project_metadata(policy: Policy) -> list[Finding]:
    findings: list[Finding] = []
    project = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))["project"]
    authors = {item.get("name") for item in project.get("authors", [])}
    if not authors or not authors <= policy.project_identities:
        findings.append(Finding("PROJECT_AUTHOR_NOT_ALLOWLISTED", "pyproject.toml", "package author is missing or unapproved"))

    citation = (ROOT / "CITATION.cff").read_text(encoding="utf-8")
    if 'family-names: "Tree"' not in citation or 'given-names: "J."' not in citation:
        findings.append(Finding("CITATION_AUTHOR_NOT_ALLOWLISTED", "CITATION.cff", "citation author differs from Tree, J."))
    if re.search(r"(?mi)^\s*(email|orcid|affiliation):", citation):
        findings.append(Finding("CITATION_PERSONAL_FIELD", "CITATION.cff", "citation contains a forbidden personal identifier field"))

    for relative in (".zenodo.json", "research/zenodo.json"):
        raw = json.loads((ROOT / relative).read_text(encoding="utf-8"))
        creators = {item.get("name") for item in raw.get("creators", [])}
        if not creators or not creators <= policy.project_identities:
            findings.append(Finding("ZENODO_AUTHOR_NOT_ALLOWLISTED", relative, "archive creator is missing or unapproved"))
        for item in raw.get("creators", []):
            if set(item) != {"name"}:
                findings.append(Finding("ZENODO_PERSONAL_FIELD", relative, "archive creator contains a field beyond the pseudonym"))
    return findings


def _noreply_email(identity: str, email: str, policy: Policy) -> bool:
    if email in policy.bot_emails:
        return identity in policy.bot_identities
    if identity not in policy.project_identities:
        return False
    return _allowed_email(email, policy)


def scan_commit(ref: str, policy: Policy) -> list[Finding]:
    format_string = "%H%x00%an%x00%ae%x00%cn%x00%ce"
    result = subprocess.run(
        ["git", "show", "-s", f"--format={format_string}", ref],
        cwd=ROOT,
        capture_output=True,
        check=False,
    )
    if result.returncode != 0:
        return [Finding("COMMIT_UNREADABLE", ref, "commit metadata could not be read")]
    fields = result.stdout.rstrip(b"\n").decode("utf-8", errors="replace").split("\0")
    if len(fields) != 5:
        return [Finding("COMMIT_UNREADABLE", ref, "commit metadata has an unexpected shape")]
    commit, author, author_email, committer, committer_email = fields
    findings: list[Finding] = []
    for role, identity, email in (
        ("author", author, author_email),
        ("committer", committer, committer_email),
    ):
        if identity not in policy.identities:
            findings.append(Finding("COMMIT_IDENTITY_NOT_ALLOWLISTED", commit, f"{role} identity is unapproved"))
        if not _noreply_email(identity, email, policy):
            findings.append(Finding("COMMIT_EMAIL_NOT_NOREPLY", commit, f"{role} email is not an approved GitHub noreply address"))
    return findings


def scan_history(ref: str, policy: Policy) -> tuple[list[Finding], int]:
    result = subprocess.run(
        ["git", "rev-list", "--reverse", ref],
        cwd=ROOT,
        capture_output=True,
        check=False,
    )
    if result.returncode != 0:
        return [Finding("COMMIT_HISTORY_UNREADABLE", ref, "reachable commit history could not be enumerated")], 0
    commits = [item for item in result.stdout.decode("ascii", errors="replace").splitlines() if item]
    findings: list[Finding] = []
    for commit in commits:
        findings.extend(scan_commit(commit, policy))
    return findings, len(commits)


def scan_protected_history(ref: str, policy: Policy) -> tuple[list[Finding], int]:
    base = policy.enforcement_base_commit
    ancestry = subprocess.run(
        ["git", "merge-base", "--is-ancestor", base, ref],
        cwd=ROOT,
        capture_output=True,
        check=False,
    )
    if ancestry.returncode != 0:
        return [Finding("PRIVACY_BASE_NOT_ANCESTOR", ref, "registered enforcement base is not reachable from the requested ref")], 0
    result = subprocess.run(
        ["git", "rev-list", "--reverse", f"{base}..{ref}"],
        cwd=ROOT,
        capture_output=True,
        check=False,
    )
    if result.returncode != 0:
        return [Finding("COMMIT_HISTORY_UNREADABLE", ref, "protected commit history could not be enumerated")], 0
    commits = [item for item in result.stdout.decode("ascii", errors="replace").splitlines() if item]
    findings: list[Finding] = []
    for commit in commits:
        findings.extend(scan_commit(commit, policy))
    return findings, len(commits)


def iter_artifacts(directory: Path) -> Iterable[Path]:
    for path in sorted(directory.rglob("*")):
        if path.is_file():
            yield path


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--commit", action="append", default=[], help="Git commit/ref whose author and committer metadata must be checked")
    parser.add_argument("--history", action="append", default=[], help="Git ref whose complete reachable authorship history must be checked")
    parser.add_argument("--protected-history", action="append", default=[], help="Git ref whose post-policy ancestry must satisfy the registered identity contract")
    parser.add_argument("--artifacts", action="append", type=Path, default=[], help="additional release-artifact directory to scan")
    args = parser.parse_args()

    try:
        policy = load_policy()
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(json.dumps({"decision": "blocked", "findings": [{"code": "PRIVACY_POLICY_INVALID", "path": "privacy-policy.json", "message": str(exc)}]}, sort_keys=True))
        return 1

    findings: list[Finding] = []
    try:
        paths = tracked_paths()
    except RuntimeError as exc:
        findings.append(Finding("TRACKED_FILE_ENUMERATION_FAILED", ".", str(exc)))
        paths = []
    for path in paths:
        if not path.is_file():
            findings.append(Finding("TRACKED_FILE_MISSING", path.relative_to(ROOT).as_posix(), "tracked file is missing"))
            continue
        findings.extend(scan_path(path, policy))
    findings.extend(validate_project_metadata(policy))
    for ref in args.commit:
        findings.extend(scan_commit(ref, policy))
    commits_scanned = len(args.commit)
    for ref in args.history:
        history_findings, count = scan_history(ref, policy)
        findings.extend(history_findings)
        commits_scanned += count
    for ref in args.protected_history:
        history_findings, count = scan_protected_history(ref, policy)
        findings.extend(history_findings)
        commits_scanned += count
    for directory in args.artifacts:
        if not directory.is_dir():
            findings.append(Finding("ARTIFACT_DIRECTORY_MISSING", directory.as_posix(), "artifact directory is missing"))
            continue
        for path in iter_artifacts(directory):
            findings.extend(scan_path(path, policy))

    unique = sorted({(item.code, item.path, item.message) for item in findings})
    payload = {
        "decision": "pass" if not unique else "blocked",
        "policy_version": policy.version,
        "files_scanned": len(paths),
        "commits_scanned": commits_scanned,
        "findings": [Finding(*item).as_dict() for item in unique],
    }
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0 if not unique else 1


if __name__ == "__main__":
    raise SystemExit(main())
