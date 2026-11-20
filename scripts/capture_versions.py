#!/usr/bin/env python3
"""Capture the assembly and annotation release strings, verbatim.

Run it with:

    python3 scripts/capture_versions.py

P01-02.5. The pre-registration asks for the release strings to be
recorded verbatim. Verbatim means byte-for-byte what the publisher wrote,
which is why this script *extracts* them rather than carrying a copy of
them: the table below says where to look, and the value is whatever is
there. Nothing here is retyped, so nothing here can drift from the
source by a capital letter or a hyphen.

It writes two files:

    data/versions.tsv             the record: one row per captured string
    data/versions-verbatim.txt    the source lines, with their line numbers

Both are committed. The sources they are taken from are not: they are
re-fetched from NCBI.

The record is anchored to the checksum manifest. Every source file has
to be listed in data/manifest.tsv, and its SHA-256 has to match, so a
capture cannot silently be taken from different bytes than the ones the
programme has already recorded.
"""

import argparse
import gzip
import hashlib
import os
import re
import sys

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RAW = os.path.join(REPO_ROOT, "data", "raw")
MANIFEST = os.path.join(REPO_ROOT, "data", "manifest.tsv")
OUT_TSV = os.path.join(REPO_ROOT, "data", "versions.tsv")
OUT_VERBATIM = os.path.join(REPO_ROOT, "data", "versions-verbatim.txt")
NOTE = os.path.join(REPO_ROOT, "docs", "P01-02-5-release-strings.md")

# The note's prose is written by hand; this region is written by the
# script, and holds the source lines themselves.
BEGIN_MARKER = "<!-- BEGIN VERBATIM -->"
END_MARKER = "<!-- END VERBATIM -->"

README = "README_Aplysia_californica_annotation_release_102"
REPORT = "Aplysia_californica_AR102_annotation_report.xml"
TSA_MASTER = "tsa.GJYY.mstr.gbff.gz"

COLUMNS = ["key", "value", "concept", "source_file", "source_line", "selector"]


class Capture:
    """One string to capture, and where to find it.

    Attributes:
        key: the unique name of this row.
        concept: what the string is about, shared across sources. Two
            sources that record the same concept are compared against
            each other by the tests.
        source_file: the file under data/raw/ to read.
        line: the 1-indexed line to read.
        selector: how to take the value out of that line.
    """

    def __init__(self, key, concept, source_file, line, selector):
        self.key = key
        self.concept = concept
        self.source_file = source_file
        self.line = line
        self.selector = selector


# The readme is tab-separated: LABEL<TAB>VALUE. The report is XML:
# <Tag>VALUE</Tag>, with the target set as an attribute.
CAPTURES = [
    # --- the readme: organism and release -----------------------------------
    # NCBI calls the organism's name "ORGANISM NAME" in the readme and
    # "ScientificName" in the report. It is the same string, and the
    # concept is shared so that the two are compared against each other.
    Capture("organism.name.readme", "organism.scientific_name", README, 1, "tab:2"),
    Capture("organism.common_name.readme", "organism.common_name", README, 2, "tab:2"),
    Capture("organism.taxid.readme", "organism.taxid", README, 3, "tab:2"),
    Capture("annotation.release_name.readme", "annotation.release_name", README, 4, "tab:2"),
    Capture(
        "annotation.evidence_freeze_date.readme",
        "annotation.evidence_freeze_date",
        README,
        5,
        "tab:2",
    ),
    Capture("annotation.release_date.readme", "annotation.release_date", README, 6, "tab:2"),
    Capture("annotation.report_url.readme", "annotation.report_url", README, 7, "tab:2"),
    # --- the readme: the assembly ------------------------------------------
    Capture("assembly.name.readme", "assembly.name", README, 10, "tab:2"),
    Capture("assembly.accession.readme", "assembly.accession", README, 11, "tab:2"),
    Capture("assembly.submitter.readme", "assembly.submitter", README, 12, "tab:2"),
    Capture("assembly.date.readme", "assembly.date", README, 13, "tab:2"),
    Capture("assembly.type.readme", "assembly.type", README, 14, "tab:2"),
    Capture("assembly.unit_count.readme", "assembly.unit_count", README, 15, "tab:2"),
    # --- the readme: the assembly units -------------------------------------
    Capture(
        "assembly.unit.primary.accession.readme",
        "assembly.unit.primary.accession",
        README,
        18,
        "tab:1",
    ),
    Capture(
        "assembly.unit.primary.name.readme",
        "assembly.unit.primary.name",
        README,
        18,
        "tab:2",
    ),
    Capture(
        "assembly.unit.non_nuclear.accession.readme",
        "assembly.unit.non_nuclear.accession",
        README,
        19,
        "tab:1",
    ),
    Capture(
        "assembly.unit.non_nuclear.name.readme",
        "assembly.unit.non_nuclear.name",
        README,
        19,
        "tab:2",
    ),
    # --- the report: the assembly -------------------------------------------
    Capture(
        "annotation.target_set_accession.report",
        "annotation.target_set_accession",
        REPORT,
        3,
        "xml-attribute:target_set_accession",
    ),
    Capture("assembly.name.report", "assembly.name", REPORT, 5, "xml-element"),
    Capture("assembly.accession.report", "assembly.accession", REPORT, 6, "xml-element"),
    Capture("assembly.is_reference.report", "assembly.is_reference", REPORT, 7, "xml-element"),
    Capture("assembly.submitter.report", "assembly.submitter", REPORT, 8, "xml-element"),
    Capture("assembly.date.report", "assembly.date", REPORT, 9, "xml-element"),
    Capture(
        "assembly.unit.primary.name.report",
        "assembly.unit.primary.name",
        REPORT,
        16,
        "xml-element",
    ),
    Capture(
        "assembly.unit.primary.accession.report",
        "assembly.unit.primary.accession",
        REPORT,
        17,
        "xml-element",
    ),
    Capture(
        "assembly.unit.primary.is_primary.report",
        "assembly.unit.primary.is_primary",
        REPORT,
        18,
        "xml-element",
    ),
    Capture(
        "assembly.unit.primary.type.report",
        "assembly.unit.primary.type",
        REPORT,
        19,
        "xml-element",
    ),
    Capture(
        "assembly.unit.non_nuclear.name.report",
        "assembly.unit.non_nuclear.name",
        REPORT,
        22,
        "xml-element",
    ),
    Capture(
        "assembly.unit.non_nuclear.accession.report",
        "assembly.unit.non_nuclear.accession",
        REPORT,
        23,
        "xml-element",
    ),
    Capture(
        "assembly.unit.non_nuclear.is_primary.report",
        "assembly.unit.non_nuclear.is_primary",
        REPORT,
        24,
        "xml-element",
    ),
    Capture(
        "assembly.unit.non_nuclear.type.report",
        "assembly.unit.non_nuclear.type",
        REPORT,
        25,
        "xml-element",
    ),
    # --- the report: the build -----------------------------------------------
    Capture("organism.taxid.report", "organism.taxid", REPORT, 31, "xml-element"),
    Capture(
        "organism.scientific_name.report",
        "organism.scientific_name",
        REPORT,
        32,
        "xml-element",
    ),
    Capture(
        "annotation.release_id.report",
        "annotation.release_id",
        REPORT,
        33,
        "xml-element",
    ),
    Capture(
        "annotation.evidence_freeze_date.report",
        "annotation.evidence_freeze_date",
        REPORT,
        34,
        "xml-element",
    ),
    Capture(
        "annotation.evidence_freeze_date_id.report",
        "annotation.evidence_freeze_date_id",
        REPORT,
        35,
        "xml-element",
    ),
    Capture(
        "annotation.id_load_date.report",
        "annotation.release_date",
        REPORT,
        36,
        "xml-element",
    ),
    Capture("annotation.ftp_site.report", "annotation.ftp_site", REPORT, 40, "xml-element"),
    # --- the TSA master record: the Orvis 2022 deposition --------------------
    Capture("tsa.project_version_accession.report", "tsa.project_version_accession", TSA_MASTER, 1, "locus:1"),
    Capture("tsa.sequence_count.report", "tsa.sequence_count", TSA_MASTER, 1, "locus:2"),
    Capture("tsa.division.report", "tsa.division", TSA_MASTER, 1, "locus:3"),
    Capture("tsa.molecule.report", "tsa.molecule", TSA_MASTER, 1, "locus:4"),
    Capture("tsa.topology.report", "tsa.topology", TSA_MASTER, 1, "locus:5"),
    Capture("tsa.locus_date.report", "tsa.locus_date", TSA_MASTER, 1, "locus:7"),
    Capture("tsa.accession.report", "tsa.accession", TSA_MASTER, 4, "label-value:ACCESSION"),
    Capture("tsa.version.report", "tsa.version", TSA_MASTER, 5, "label-token:VERSION"),
    Capture("tsa.bioproject.report", "tsa.bioproject", TSA_MASTER, 6, "regex:BioProject: (PRJNA\\d+)"),
    Capture("tsa.biosample.report", "tsa.biosample", TSA_MASTER, 7, "regex:BioSample: (SAMN\\d+)"),
    Capture("tsa.sra.report", "tsa.sra", TSA_MASTER, 8, "regex:Sequence Read Archive: (SRR\\d+)"),
    Capture("tsa.organism.report", "tsa.organism", TSA_MASTER, 11, "label-value:ORGANISM"),
    Capture("tsa.journal.report", "tsa.journal", TSA_MASTER, 21, "label-value:JOURNAL"),
    Capture("tsa.submitted_date.report", "tsa.submitted_date", TSA_MASTER, 27, "regex:Submitted \\((\\d{2}-[A-Z]{3}-\\d{4})\\)"),
    Capture("tsa.reads.report", "tsa.reads", TSA_MASTER, 34, "regex:([\\d.]+ billion Illumina HiSeq reads)"),
    Capture("tsa.assembly_method.report", "tsa.assembly_method", TSA_MASTER, 46, "assembly-data:Assembly Method"),
    Capture("tsa.assembly_name.report", "tsa.assembly_name", TSA_MASTER, 47, "assembly-data:Assembly Name"),
    Capture("tsa.sequencing_technology.report", "tsa.sequencing_technology", TSA_MASTER, 48, "assembly-data:Sequencing Technology"),
    Capture("tsa.organism_qualifier.report", "tsa.organism", TSA_MASTER, 52, "qualifier:organism"),
    Capture("tsa.mol_type.report", "tsa.mol_type", TSA_MASTER, 53, "qualifier:mol_type"),
    Capture("tsa.isolate.report", "tsa.isolate", TSA_MASTER, 54, "qualifier:isolate"),
    Capture("tsa.taxon.report", "tsa.taxon", TSA_MASTER, 55, "regex:taxon:(\\d+)"),
    Capture("tsa.sex.report", "tsa.sex", TSA_MASTER, 56, "qualifier:sex"),
    Capture("tsa.tissue_type.report", "tsa.tissue_type", TSA_MASTER, 57, "qualifier:tissue_type"),
    Capture("tsa.sequence_range.report", "tsa.sequence_range", TSA_MASTER, 58, "label-value:TSA"),
]



def sha256_of(path):
    """Return the SHA-256 of a file.

    Args:
        path: the path of the file.

    Returns:
        The checksum, as text.
    """
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def read_manifest(path):
    """Return the checksum manifest, as a mapping of file name to checksum.

    Args:
        path: the path of the manifest.

    Returns:
        A mapping of file name to SHA-256.
    """
    recorded = {}
    with open(path, encoding="utf-8") as handle:
        header = handle.readline().rstrip("\n").split("\t")
        for line in handle:
            if not line.strip():
                continue
            row = dict(zip(header, line.rstrip("\n").split("\t")))
            recorded[row["file"]] = row["sha256"]
    return recorded


def extract(line, selector, text=None):
    """Take the value out of one source line, or out of the whole record.

    Args:
        line: the source line, without its terminator.
        selector: how to take the value. "tab:N" is the Nth tab-separated
            field, 1-indexed. "xml-element" is the text between the tags.
            "xml-attribute:NAME" is the value of that attribute. "locus:N"
            is the Nth field of the LOCUS line. "label-value:NAME" and
            "label-token:NAME" read a flatfile label. "qualifier:NAME"
            reads a feature qualifier. "assembly-data:KEY" reads the
            Assembly-Data block. "regex:PATTERN" takes the first match.
        text: the whole record, for the selectors that read across it.

    Returns:
        The value, as text.

    Raises:
        ValueError: If the line does not yield a value.
    """
    if text is None:
        text = line
    if selector.startswith("tab:"):
        fields = line.split("\t")
        index = int(selector.split(":", 1)[1])
        if index > len(fields):
            raise ValueError(f"line has {len(fields)} tab-separated fields, wanted field {index}")
        return fields[index - 1]
    if selector == "xml-element":
        start = line.find(">")
        end = line.rfind("<")
        if start < 0 or end < 0 or end < start:
            raise ValueError(f"line is not an element with a value: {line!r}")
        return line[start + 1 : end]
    if selector.startswith("locus:"):
        index = int(selector.split(":", 1)[1])
        for candidate in text.split("\n"):
            if candidate.strip().split(" ")[0] == "LOCUS":
                # The LOCUS keyword is not a field of the record; the
                # fields are what follows it.
                fields = candidate.split()[1:]
                if index > len(fields):
                    raise ValueError(f"the LOCUS line has {len(fields)} fields, wanted field {index}")
                return fields[index - 1]
        raise ValueError("the line holds no LOCUS record")
    if selector.startswith("label-value:") or selector.startswith("label-token:"):
        name = selector.split(":", 1)[1]
        token = selector.startswith("label-token:")
        for candidate in text.split("\n"):
            stripped = candidate.strip()
            if stripped.startswith(name + " ") or stripped == name:
                rest = stripped[len(name) :].strip()
                if not rest:
                    raise ValueError(f"the {name} label carries no value")
                return rest.split()[0] if token else rest
        raise ValueError(f"there is no {name} label in the record")
    if selector.startswith("qualifier:"):
        name = selector.split(":", 1)[1]
        marker = f'/{name}="'
        start = text.find(marker)
        if start < 0:
            raise ValueError(f"the record has no /{name} qualifier")
        start += len(marker)
        end = text.find('"', start)
        if end < 0:
            raise ValueError(f"the /{name} qualifier is not closed")
        return text[start:end]
    if selector.startswith("assembly-data:"):
        key = selector.split(":", 1)[1]
        pattern = re.compile(r"^\s*" + re.escape(key) + r"\s+::\s*(.*)$", re.MULTILINE)
        match = pattern.search(text)
        if not match:
            raise ValueError(f"the record has no {key} in its Assembly-Data block")
        return match.group(1).strip()
    if selector.startswith("regex:"):
        pattern = selector.split(":", 1)[1]
        match = re.search(pattern, text)
        if not match:
            raise ValueError(f"the pattern {pattern!r} does not match the record")
        return match.group(1) if match.groups() else match.group(0)
    if selector.startswith("xml-attribute:"):
        name = selector.split(":", 1)[1]
        marker = f'{name}="'
        start = line.find(marker)
        if start < 0:
            raise ValueError(f"line has no attribute {name}: {line!r}")
        start += len(marker)
        end = line.find('"', start)
        if end < 0:
            raise ValueError(f"attribute {name} is not closed: {line!r}")
        return line[start:end]
    raise ValueError(f"unknown selector {selector!r}")


def read_source(name):
    """Return the lines of a source file.

    Args:
        name: the name of the file under data/raw/.

    Returns:
        The lines, without their terminators.

    Raises:
        FileNotFoundError: If the file has not been fetched.
    """
    path = os.path.join(RAW, name)
    if not os.path.exists(path):
        raise FileNotFoundError(
            f"{path} is not here. Run scripts/fetch_assembly.sh and scripts/fetch_annotation.sh first."
        )
    if name.endswith(".gz"):
        with gzip.open(path, "rt", encoding="utf-8") as handle:
            return handle.read().split("\n")
    with open(path, encoding="utf-8") as handle:
        return handle.read().split("\n")


def capture(captures):
    """Capture every string.

    Args:
        captures: the list of Capture entries.

    Returns:
        The captured rows, and the source lines they came from.

    Raises:
        ValueError: If a capture cannot be taken.
    """
    rows = []
    lines = {}
    for entry in captures:
        if entry.source_file not in lines:
            lines[entry.source_file] = read_source(entry.source_file)
        source = lines[entry.source_file]
        if entry.line > len(source):
            raise ValueError(
                f"{entry.key}: {entry.source_file} has {len(source)} lines, wanted line {entry.line}"
            )
        line = source[entry.line - 1]
        value = extract(line, entry.selector, "\n".join(source))
        if not value:
            raise ValueError(f"{entry.key}: {entry.source_file} line {entry.line} yields an empty value")
        rows.append(
            {
                "key": entry.key,
                "value": value,
                "concept": entry.concept,
                "source_file": entry.source_file,
                "source_line": str(entry.line),
                "selector": entry.selector,
            }
        )
    return rows, lines


def write_tsv(path, rows):
    """Write the record.

    Args:
        path: where to write it.
        rows: the rows to write.
    """
    lines = ["\t".join(COLUMNS)]
    for row in rows:
        lines.append("\t".join(row[column] for column in COLUMNS))
    with open(path, "w", encoding="utf-8", newline="") as handle:
        handle.write("\n".join(lines) + "\n")


def verbatim_sections(rows, lines):
    """Return the source lines of each file, with their line numbers.

    Two captures can sit on the same source line - the readme's
    assembly-unit rows carry both an accession and a name - so a line is
    printed once.

    Args:
        rows: the captured rows.
        lines: the source lines, by file name.

    Returns:
        A mapping of file name to the list of printed lines.
    """
    sections = {}
    current = None
    emitted = set()
    for row in rows:
        if row["source_file"] != current:
            current = row["source_file"]
            emitted = set()
            sections[current] = []
        if row["source_line"] in emitted:
            continue
        emitted.add(row["source_line"])
        source = lines[current]
        sections[current].append(f"{row['source_line']:>6}: {source[int(row['source_line']) - 1]}")
    return sections


def write_verbatim(path, rows, lines):
    """Write the source lines, with the line numbers they sit at.

    Args:
        path: where to write it.
        rows: the captured rows.
        lines: the source lines, by file name.
    """
    sections = verbatim_sections(rows, lines)
    out = []
    for name, section in sections.items():
        out.append(f"=== {name}")
        out.append("")
        out.extend(section)
    with open(path, "w", encoding="utf-8", newline="") as handle:
        handle.write("\n".join(out) + "\n")


def write_note_block(path, rows, lines):
    """Rewrite the verbatim section of the note.

    The note's prose is written by hand and is never touched. Only the
    region between the markers is replaced, and it is replaced with the
    source lines themselves - which is the point: nothing in the note is
    a retyping of anything.

    Args:
        path: the path of the note.
        rows: the captured rows.
        lines: the source lines, by file name.

    Raises:
        FileNotFoundError: If the note is not there.
        ValueError: If the note does not carry the markers.
    """
    if not os.path.exists(path):
        raise FileNotFoundError(f"{path} is not here. It is committed; restore it from git.")
    with open(path, encoding="utf-8") as handle:
        note = handle.read()
    if BEGIN_MARKER not in note or END_MARKER not in note:
        raise ValueError(f"{path} does not carry the {BEGIN_MARKER} markers.")

    sections = verbatim_sections(rows, lines)
    block = []
    for name, section in sections.items():
        block.append(f"### `{name}`")
        block.append("")
        block.append("```")
        block.extend(section)
        block.append("```")
        block.append("")
    rendered = BEGIN_MARKER + "\n" + "\n".join(block).rstrip("\n") + "\n" + END_MARKER

    start = note.index(BEGIN_MARKER)
    end = note.index(END_MARKER) + len(END_MARKER)
    updated = note[:start] + rendered + note[end:]
    with open(path, "w", encoding="utf-8", newline="") as handle:
        handle.write(updated)


def main(argv=None):
    """Capture the release strings.

    Args:
        argv: the command-line arguments.

    Returns:
        The exit code.
    """
    parser = argparse.ArgumentParser(description=__doc__)
    parser.parse_args(argv)

    if not os.path.exists(MANIFEST):
        print(f"error: {MANIFEST} is not here. It is committed; restore it from git.", file=sys.stderr)
        return 1

    recorded = read_manifest(MANIFEST)
    for name in {entry.source_file for entry in CAPTURES}:
        path = os.path.join(RAW, name)
        if name not in recorded:
            print(f"error: {name} is not in the checksum manifest.", file=sys.stderr)
            return 1
        if not os.path.exists(path):
            print(f"error: {path} is not here. Fetch it first.", file=sys.stderr)
            return 1
        if sha256_of(path) != recorded[name]:
            print(f"error: {name} does not match the checksum in the manifest.", file=sys.stderr)
            return 1

    try:
        rows, lines = capture(CAPTURES)
    except (ValueError, FileNotFoundError) as error:
        print(f"error: {error}", file=sys.stderr)
        return 1

    keys = [row["key"] for row in rows]
    if len(keys) != len(set(keys)):
        print("error: two captures have the same key.", file=sys.stderr)
        return 1

    write_tsv(OUT_TSV, rows)
    write_verbatim(OUT_VERBATIM, rows, lines)
    try:
        write_note_block(NOTE, rows, lines)
    except (FileNotFoundError, ValueError) as error:
        print(f"error: {error}", file=sys.stderr)
        return 1
    print(f"wrote {OUT_TSV} with {len(rows)} captured strings")
    print(f"wrote {OUT_VERBATIM}")
    print(f"updated the verbatim section of {NOTE}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
