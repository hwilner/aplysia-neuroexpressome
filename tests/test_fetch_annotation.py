#!/usr/bin/env python3
"""Tests for the annotation fetch script and the record of what it fetched.

Run them with:

    python3 -m unittest discover -s tests

The point of these tests is that the record and the files have to agree. The
annotation is not committed, so `docs/P01-02-3-annotation-download.md` and the
files on disk are the only two things that say what was used, and they can
drift apart without either being wrong on its own.

The table in the note is the reference, and it is read rather than
retyped: a checksum that is transcribed by hand into a test is a checksum
that can be transcribed wrongly.

The test also pins the accession. `GCF_000002075.2` is what the
pre-registration says, and it does not resolve; `GCF_000002075.1` is what
NCBI publishes for the RefSeq assembly, and it does.
"""

import hashlib
import os
import re
import subprocess
import unittest

REPO_ROOT = os.path.join(os.path.dirname(__file__), os.pardir)
SCRIPT = os.path.join(REPO_ROOT, "scripts", "fetch_annotation.sh")
NOTE = os.path.join(REPO_ROOT, "docs", "P01-02-3-annotation-download.md")
RAW = os.path.join(REPO_ROOT, "data", "raw")
ASSEMBLY = "GCF_000002075.1"
# The accession the pre-registration names, which does not resolve.
UNRESOLVABLE = "GCF_000002075.2"

# The files the note records, and the ones the script has to fetch.
EXPECTED = [
    "GCF_000002075.1_AplCal3.0_genomic.gff.gz",
    "GCF_000002075.1_AplCal3.0_protein.faa.gz",
    "GCF_000002075.1_AplCal3.0_cds_from_genomic.fna.gz",
    "GCF_000002075.1_AplCal3.0_feature_table.txt.gz",
    "GCF_000002075.1_AplCal3.0_genomic_gaps.txt.gz",
    "GCF_000002075.1_AplCal3.0_gene_ontology.gaf.gz",
    "GCF_000002075.1_AplCal3.0_assembly_report.txt",
    "GCF_000002075.1_AplCal3.0_feature_count.txt.gz",
    "Aplysia_californica_AR102_annotation_report.xml",
    "README_Aplysia_californica_annotation_release_102",
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


def recorded_checksums():
    """Return the checksums the note records, keyed by file name.

    Returns:
        A mapping of file name to SHA-256.
    """
    recorded = {}
    for line in read(NOTE).splitlines():
        match = re.match(r"\|\s*`([^`]+)`\s*\|\s*`([0-9a-f]{64})`\s*\|", line)
        if match:
            recorded[match.group(1)] = match.group(2)
    return recorded


class ScriptTest(unittest.TestCase):
    """Tests for the fetch script."""

    def test_the_script_exists_and_is_executable(self):
        self.assertTrue(os.path.exists(SCRIPT))
        self.assertTrue(os.access(SCRIPT, os.X_OK), "the fetch script is not executable")

    def test_the_script_is_valid_bash(self):
        result = subprocess.run(
            ["bash", "-n", SCRIPT], capture_output=True, text=True, check=False
        )
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_the_script_pins_the_accession_that_resolves(self):
        self.assertIn(ASSEMBLY, read(SCRIPT))

    def test_the_script_does_not_use_the_accession_that_does_not_resolve(self):
        self.assertNotIn(UNRESOLVABLE, read(SCRIPT))

    def test_the_script_fetches_every_file_the_note_records(self):
        script = read(SCRIPT)
        # The eight assembly files are listed by their tail, because the
        # script builds them from the accession and the assembly name; the
        # two release files are named outright.
        prefix = f"{ASSEMBLY}_AplCal3.0_"
        for name in EXPECTED:
            tail = name[len(prefix):] if name.startswith(prefix) else name
            self.assertIn(tail, script, f"the script does not fetch {name}")

    def test_the_script_builds_the_prefixed_files_from_one_prefix(self):
        script = read(SCRIPT)
        self.assertEqual(script.count('PREFIX="${ASSEMBLY}_"'), 1)

    def test_the_script_says_when_there_is_no_published_checksum(self):
        # A file with no published checksum must not read as one that was
        # checked against the publisher.
        script = read(SCRIPT)
        self.assertIn("no published checksum", script)


class NoteTest(unittest.TestCase):
    """Tests for the record of what was fetched."""

    def test_the_note_exists(self):
        self.assertTrue(os.path.exists(NOTE))

    def test_the_note_records_the_accession(self):
        self.assertIn(ASSEMBLY, read(NOTE))

    def test_the_note_records_a_checksum_for_every_file(self):
        recorded = recorded_checksums()
        for name in EXPECTED:
            self.assertIn(name, recorded, f"the note records no checksum for {name}")

    def test_the_note_records_the_verification_method_per_file(self):
        note = read(NOTE)
        self.assertIn("NCBI's published MD5", note)
        self.assertIn("no published checksum", note)

    def test_the_note_records_the_protein_count(self):
        self.assertIn("26,656", read(NOTE))

    def test_the_note_records_how_many_models_are_predicted(self):
        # The composition of the annotation is the fact the methods will
        # have to state, so it is checked for being present.
        self.assertIn("19,142", read(NOTE))


@unittest.skipUnless(
    os.path.exists(os.path.join(RAW, EXPECTED[0])),
    "the annotation is not downloaded here; the raw data is not committed",
)
class DownloadTest(unittest.TestCase):
    """Tests that the downloaded files are the ones the note describes.

    These run where the annotation has been fetched, and are skipped
    elsewhere - in continuous integration, where the raw data is absent by
    design.
    """

    def test_every_file_matches_its_recorded_checksum(self):
        recorded = recorded_checksums()
        for name in EXPECTED:
            path = os.path.join(RAW, name)
            self.assertTrue(os.path.exists(path), f"{name} is not in data/raw/")
            digest = hashlib.sha256()
            with open(path, "rb") as handle:
                for block in iter(lambda: handle.read(1 << 20), b""):
                    digest.update(block)
            self.assertEqual(digest.hexdigest(), recorded[name], f"{name} differs")

    def test_the_sizes_match_the_note(self):
        note = read(NOTE)
        for name in EXPECTED:
            size = os.path.getsize(os.path.join(RAW, name))
            self.assertIn(f"{size:,}", note, f"the note records no size for {name}")


if __name__ == "__main__":
    unittest.main()
