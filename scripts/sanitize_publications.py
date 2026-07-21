#!/usr/bin/env python3
"""Remove non-pseudonymous and environment metadata from the public DOCX/PDF."""

from __future__ import annotations

import argparse
import os
import tempfile
import zipfile
from pathlib import Path
from xml.etree import ElementTree as ET


DC = "http://purl.org/dc/elements/1.1/"
DCTERMS = "http://purl.org/dc/terms/"
CP = "http://schemas.openxmlformats.org/package/2006/metadata/core-properties"
EP = "http://schemas.openxmlformats.org/officeDocument/2006/extended-properties"
W = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
PIPELINE = "BSC publication pipeline"
AUTHOR = "J. Tree"


def _remove(root: ET.Element, tag: str) -> None:
    for element in list(root.findall(tag)):
        root.remove(element)


def _sanitize_core(data: bytes) -> bytes:
    root = ET.fromstring(data)
    creator = root.find(f"{{{DC}}}creator")
    if creator is None:
        creator = ET.SubElement(root, f"{{{DC}}}creator")
    creator.text = AUTHOR
    for tag in (f"{{{CP}}}lastModifiedBy", f"{{{DCTERMS}}}created", f"{{{DCTERMS}}}modified"):
        _remove(root, tag)
    return ET.tostring(root, encoding="utf-8", xml_declaration=True)


def _sanitize_app(data: bytes) -> bytes:
    root = ET.fromstring(data)
    for child in list(root):
        root.remove(child)
    application = ET.SubElement(root, f"{{{EP}}}Application")
    application.text = PIPELINE
    return ET.tostring(root, encoding="utf-8", xml_declaration=True)


def _sanitize_word_xml(data: bytes) -> bytes:
    root = ET.fromstring(data)
    for element in root.iter():
        for attribute in list(element.attrib):
            if attribute.startswith(f"{{{W}}}rsid"):
                del element.attrib[attribute]
    return ET.tostring(root, encoding="utf-8", xml_declaration=True)


def sanitize_docx(path: Path) -> None:
    with tempfile.NamedTemporaryFile(prefix=path.stem + "-", suffix=".docx", dir=path.parent, delete=False) as stream:
        temporary = Path(stream.name)
    try:
        with zipfile.ZipFile(path, "r") as source, zipfile.ZipFile(temporary, "w") as destination:
            for info in source.infolist():
                data = source.read(info.filename)
                if info.filename == "docProps/core.xml":
                    data = _sanitize_core(data)
                elif info.filename == "docProps/app.xml":
                    data = _sanitize_app(data)
                elif info.filename.startswith("word/") and info.filename.endswith(".xml"):
                    data = _sanitize_word_xml(data)
                destination.writestr(info, data)
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


def sanitize_pdf(path: Path) -> None:
    try:
        from pypdf import PdfReader, PdfWriter
        from pypdf.generic import NameObject
    except ImportError as exc:
        raise SystemExit("pypdf is required to sanitize the PDF metadata") from exc

    reader = PdfReader(path)
    writer = PdfWriter()
    writer.clone_document_from_reader(reader)
    writer.root_object.pop(NameObject("/Metadata"), None)
    writer.metadata = None
    writer.add_metadata(
        {
            "/Title": "Audit Descent Calculus",
            "/Author": AUTHOR,
            "/Subject": "Certificate naturality, observation descent, atomic rigidity, and executable scientific audit",
            "/Keywords": "certificate, transport, chain, complex, audit, observation, quotient, atomic, rigidity, arithmetic, trace",
            "/Creator": PIPELINE,
            "/Producer": PIPELINE,
        }
    )
    # clone_document_from_reader preserves outlines and tagged-PDF structure,
    # but it initially imports every source object. Remove objects no longer
    # reachable after detaching the XMP metadata stream so its bytes cannot
    # survive as an orphaned producer/timestamp fingerprint.
    writer.compress_identical_objects(remove_duplicates=True, remove_unreferenced=True)
    with tempfile.NamedTemporaryFile(prefix=path.stem + "-", suffix=".pdf", dir=path.parent, delete=False) as stream:
        temporary = Path(stream.name)
        writer.write(stream)
    try:
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--docx", type=Path, default=Path("research/Audit_Descent_Calculus.docx"))
    parser.add_argument("--pdf", type=Path, default=Path("research/Audit_Descent_Calculus.pdf"))
    args = parser.parse_args()
    sanitize_docx(args.docx)
    sanitize_pdf(args.pdf)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
