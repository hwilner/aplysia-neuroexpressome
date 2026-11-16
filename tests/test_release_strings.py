#!/usr/bin/env python3
"""Tests for the captured release strings.

Run them with:

    python3 -m unittest discover -s tests

The pre-registration asks for the assembly and annotation release strings
to be recorded verbatim. "Verbatim" is the whole requirement: the value
has to be what NCBI wrote, not what we remembered of it, and not what we
retyped into a table.

So the record is generated, and these tests hold it against four things:

  * the sources themselves, where they are present;
  * the checksum manifest, which says which bytes the capture came from;
  * the note, whose verbatim blocks and agreement table have to agree
    with the record;
  * the other source, concept by concept - the two files are NCBI's
    independent statements of the same release, and where they record
    the same thing they have to say the same thing.

The first three do not need the raw data, because the record and the
note are both committed. A disagreement between them would otherwise go
unseen.
"""

import datetime
import os
import re
import subprocess
import unittest

REPO_ROOT = os.path.join(os.path.dirname(__file__), os.pardir)
VERSIONS = os.path.join(REPO_ROOT, "data", "versions.tsv")
VERBATIM = os.path.join(REPO_ROOT, "data", "versions-verbatim.txt")
MANIFEST = os.path.join(REPO_ROOT, "data", "manifest.tsv")
NOTE = os.path.join(REPO_ROOT, "docs", "P01-02-5-release-strings.md")
RAW = os.path.join(REPO_ROOT, "data", "raw")

COLUMNS = ["key", "value", "concept", "source_file", "source_line", "selector"]

README = "README_Aplysia_californica_annotation_release_102"
REPORT = "Aplysia_californica_AR102_annotation_report.xml"

# The concepts whose two sources record a date, and whose values are
# therefore expected to differ in format while describing one date.
DATE_CONCEPTS = {
    "assembly.date",
    "annotation.evidence_freeze_date",
    "annotation.release_date",
}

DATE_FORMATS = [
    "%d-%B-%Y",
    "%d %B %Y",
    "%b %d %Y",
    "%B %d %Y",
    "%m-%d-%Y",
    "%Y%m%d",
]


def read(path):
    """Return the contents of a file.

    Args:
        path: the path of the file.

    Returns:
        The contents, as text.
    """
    with open(path, encoding="utf-8") as handle:
        return handle.read()


def version_rows():
    """Return the captured strings, as a list of dictionaries.

    Returns:
        The rows, in file order.
    """
    lines = read(VERSIONS).splitlines()
    header = lines[0].split("\t")
    rows = []
    for line in lines[1:]:
        if not line.strip():
            continue
        rows.append(dict(zip(header, line.split("\t"))))
    return rows


def manifest_rows():
    """Return the checksum manifest, as a list of dictionaries.

    Returns:
        The rows, in file order.
    """
    lines = read(MANIFEST).splitlines()
    header = lines[0].split("\t")
    rows = []
    for line in lines[1:]:
        if not line.strip():
            continue
        rows.append(dict(zip(header, line.split("\t"))))
    return rows


def verbatim_sections():
    """Return the generated source lines, by file name.

    Returns:
        A mapping of file name to the list of printed lines.
    """
    sections = {}
    current = None
    for line in read(VERBATIM).splitlines():
        if line.startswith("=== "):
            current = line[4:].strip()
            sections[current] = []
            continue
        if current is not None and line.strip():
            sections[current].append(line)
    return sections


def note_verbatim_sections():
    """Return the note's verbatim blocks, by file name.

    Only the marked region is read. The note has other code fences
    further down, and a parser that walked the whole file would collect
    those too.

    Returns:
        A mapping of file name to the list of lines in its block.
    """
    text = read(NOTE)
    start = text.index("<!-- BEGIN VERBATIM -->")
    end = text.index("<!-- END VERBATIM -->")
    sections = {}
    current = None
    inside = False
    for line in text[start:end].splitlines():
        heading = re.match(r"^### `([^`]+)`\s*$", line)
        if heading:
            current = heading.group(1)
            sections[current] = []
            continue
        if line.strip() == "```":
            inside = not inside
            continue
        if inside and current is not None:
            sections[current].append(line)
    return sections


def note_agreement_table():
    """Return the note's agreement table, as concept to both values.

    Returns:
        A mapping of concept to the two values, or None for a concept
        that only one source records.
    """
    text = read(NOTE)
    start = text.index("## What the two sources agree on")
    table = {}
    for line in text[start:].splitlines():
        match = re.match(r"^\|\s*`([^`]+)`\s*\|\s*`([^`]*)`\s*\|\s*`([^`]*)`\s*\|\s*$", line)
        if match:
            table[match.group(1)] = (match.group(2), match.group(3))
    return table


def normalise_date(value):
    """Return a date as an ISO string, whichever format it is written in.

    Args:
        value: the date, as written.

    Returns:
        The date as YYYY-MM-DD, or None if it is not a date.
    """
    for fmt in DATE_FORMATS:
        try:
            return datetime.datetime.strptime(value, fmt).date().isoformat()
        except ValueError:
            continue
    return None


class CaptureTest(unittest.TestCase):
    """Tests for the record's own shape."""

    def test_the_files_exist(self):
        self.assertTrue(os.path.exists(VERSIONS))
        self.assertTrue(os.path.exists(VERBATIM))
        self.assertTrue(os.path.exists(NOTE))

    def test_the_record_is_not_ignored(self):
        for name in ("data/versions.tsv", "data/versions-verbatim.txt"):
            result = subprocess.run(
                ["git", "check-ignore", "-q", name],
                cwd=REPO_ROOT,
                capture_output=True,
                check=False,
            )
            self.assertNotEqual(result.returncode, 0, f"{name} is gitignored")

    def test_the_header_is_the_expected_one(self):
        header = read(VERSIONS).splitlines()[0].split("\t")
        self.assertEqual(header, COLUMNS)

    def test_the_keys_are_unique(self):
        keys = [row["key"] for row in version_rows()]
        self.assertEqual(len(keys), len(set(keys)))

    def test_every_row_has_a_value_and_a_location(self):
        for row in version_rows():
            self.assertTrue(row["value"].strip(), row["key"])
            self.assertTrue(row["concept"].strip(), row["key"])
            self.assertTrue(row["source_file"].strip(), row["key"])
            self.assertGreater(int(row["source_line"]), 0, row["key"])
            self.assertTrue(row["selector"].strip(), row["key"])

    def test_every_source_file_is_in_the_checksum_manifest(self):
        recorded = {row["file"] for row in manifest_rows()}
        for row in version_rows():
            self.assertIn(row["source_file"], recorded, row["source_file"])

    def test_the_sources_are_the_two_the_capture_names(self):
        used = {row["source_file"] for row in version_rows()}
        self.assertEqual(used, {README, REPORT})


class AgreementTest(unittest.TestCase):
    """Tests that the two sources agree where they overlap."""

    def test_the_concepts_recorded_by_both_sources(self):
        by_concept = {}
        for row in version_rows():
            by_concept.setdefault(row["concept"], []).append(row)
        both = {
            concept: rows
            for concept, rows in by_concept.items()
            if len({row["source_file"] for row in rows}) == 2
        }
        self.assertGreaterEqual(len(both), 10, "the two sources barely overlap")
        for concept, rows in both.items():
            readme = [r for r in rows if r["source_file"] == README][0]
            report = [r for r in rows if r["source_file"] == REPORT][0]
            if concept in DATE_CONCEPTS:
                # The same date, written two ways.
                self.assertIsNotNone(
                    normalise_date(readme["value"]), f"{concept}: {readme['value']}"
                )
                self.assertEqual(
                    normalise_date(readme["value"]),
                    normalise_date(report["value"]),
                    f"{concept} differs between the two sources",
                )
            else:
                self.assertEqual(
                    readme["value"],
                    report["value"],
                    f"{concept} differs between the two sources",
                )

    def test_the_assembly_accession_is_not_a_unit_or_the_target_set(self):
        by_key = {row["key"]: row["value"] for row in version_rows()}
        self.assertEqual(by_key["assembly.accession.readme"], "GCF_000002075.1")
        self.assertEqual(by_key["assembly.accession.report"], "GCF_000002075.1")
        # The units and the target set are different accessions, and
        # confusing one for the assembly would be fatal and quiet.
        for key in (
            "assembly.unit.primary.accession.readme",
            "assembly.unit.non_nuclear.accession.readme",
            "annotation.target_set_accession.report",
        ):
            self.assertNotEqual(by_key[key], "GCF_000002075.1", key)
            self.assertTrue(by_key[key].startswith("GCF_"), key)

    def test_the_accession_the_pre_registration_names_is_not_the_one_used(self):
        # The pre-registration names GCF_000002075.2, which does not
        # resolve. The capture must not quietly adopt it.
        by_key = {row["key"]: row["value"] for row in version_rows()}
        for value in by_key.values():
            self.assertNotEqual(value, "GCF_000002075.2")


class NoteTest(unittest.TestCase):
    """Tests that the note agrees with the record."""

    def test_the_note_verbatim_blocks_match_the_generated_lines(self):
        generated = verbatim_sections()
        in_note = note_verbatim_sections()
        self.assertEqual(set(generated), set(in_note))
        for name, section in generated.items():
            self.assertEqual(section, in_note[name], f"the note's block for {name} differs")

    def test_every_captured_value_appears_in_the_verbatim_lines(self):
        for row in version_rows():
            section = "\n".join(verbatim_sections()[row["source_file"]])
            self.assertIn(row["value"], section, row["key"])

    def test_every_captured_value_appears_in_the_note(self):
        note = read(NOTE)
        for row in version_rows():
            self.assertIn(row["value"], note, row["key"])

    def test_the_agreement_table_lists_exactly_the_shared_concepts(self):
        by_concept = {}
        for row in version_rows():
            by_concept.setdefault(row["concept"], []).append(row)
        shared = {
            concept
            for concept, rows in by_concept.items()
            if len({row["source_file"] for row in rows}) == 2
        }
        table = note_agreement_table()
        self.assertEqual(set(table), shared)

    def test_the_agreement_table_carries_the_right_values(self):
        by_concept = {}
        for row in version_rows():
            by_concept.setdefault(row["concept"], []).append(row)
        table = note_agreement_table()
        for concept, (readme_value, report_value) in table.items():
            rows = by_concept[concept]
            self.assertEqual(
                readme_value, [r for r in rows if r["source_file"] == README][0]["value"], concept
            )
            self.assertEqual(
                report_value, [r for r in rows if r["source_file"] == REPORT][0]["value"], concept
            )


@unittest.skipUnless(
    os.path.exists(os.path.join(RAW, README)),
    "the inputs are not downloaded here; the raw data is not committed",
)
class AgainstSourcesTest(unittest.TestCase):
    """Tests that the capture still matches the sources.

    These run where the inputs have been fetched, and are skipped
    elsewhere.
    """

    def test_each_value_is_where_it_says_it_is(self):
        sys_path = os.path.join(REPO_ROOT, "scripts")
        import sys

        if sys_path not in sys.path:
            sys.path.insert(0, sys_path)
        import capture_versions

        for row in version_rows():
            path = os.path.join(RAW, row["source_file"])
            with open(path, encoding="utf-8") as handle:
                lines = handle.read().split("\n")
            line = lines[int(row["source_line"]) - 1]
            value = capture_versions.extract(line, row["selector"])
            self.assertEqual(value, row["value"], f"{row['key']} at {row['source_file']}")

    def test_the_generated_lines_match_the_sources(self):
        for row in version_rows():
            path = os.path.join(RAW, row["source_file"])
            with open(path, encoding="utf-8") as handle:
                lines = handle.read().split("\n")
            source = lines[int(row["source_line"]) - 1]
            printed = f"{row['source_line']:>6}: {source}"
            self.assertIn(printed, read(VERBATIM), row["key"])


if __name__ == "__main__":
    unittest.main()
