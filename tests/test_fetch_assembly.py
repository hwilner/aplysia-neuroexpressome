#!/usr/bin/env python3
"""Tests for the assembly fetch script and the record of what it fetched.

Run them with:

    python3 -m unittest discover -s tests

The point of these tests is that the record and the file have to agree. The
assembly is not committed, so `docs/P01-02-2-assembly-download.md` and the
file on disk are the only two things that say what was used, and they can
drift apart without either being wrong on its own.

The test also pins the accession. `GCF_000002075.2` is what the
pre-registration says, and it does not resolve; `GCF_000002075.1` is what
NCBI publishes for the RefSeq assembly, and it does. A script that went
back to the unresolvable string would fetch nothing, and would fail late
and obscurely, so it is checked early and here.
"""

import hashlib
import os
import re
import subprocess
import unittest

REPO_ROOT = os.path.join(os.path.dirname(__file__), os.pardir)
SCRIPT = os.path.join(REPO_ROOT, "scripts", "fetch_assembly.sh")
NOTE = os.path.join(REPO_ROOT, "docs", "P01-02-2-assembly-download.md")
RAW = os.path.join(REPO_ROOT, "data", "raw")
ASSEMBLY = "GCF_000002075.1"
FILE_NAME = f"{ASSEMBLY}_AplCal3.0_genomic.fna.gz"
# The accession the pre-registration names, which does not resolve.
UNRESOLVABLE = "GCF_000002075.2"
# The checksum NCBI publishes for the file, in md5checksums.txt.
PUBLISHED_MD5 = "fd012bb43298223de48b4ba0bccf54f3"


def read(path):
    """Return the contents of a file.

    Args:
        path: the path of the file.

    Returns:
        The contents, as text.
    """
    with open(path, encoding="utf-8") as handle:
        return handle.read()


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

    def test_the_script_fetches_the_genomic_fasta(self):
        # The file name is built from the accession and the assembly name,
        # so the two halves are what the script carries.
        script = read(SCRIPT)
        self.assertIn(f"{ASSEMBLY}_AplCal3.0", script)
        self.assertIn("_genomic.fna.gz", script)
        self.assertIn("md5checksums.txt", script)
        self.assertIn("gzip -t", script)


class NoteTest(unittest.TestCase):
    """Tests for the record of what was fetched."""

    def test_the_note_exists(self):
        self.assertTrue(os.path.exists(NOTE))

    def test_the_note_records_the_accession(self):
        self.assertIn(ASSEMBLY, read(NOTE))

    def test_the_note_records_the_published_md5(self):
        self.assertIn(PUBLISHED_MD5, read(NOTE))

    def test_the_note_records_a_well_formed_sha256(self):
        found = re.findall(r"\b[0-9a-f]{64}\b", read(NOTE))
        self.assertTrue(found, "the note records no sha256")

    def test_the_note_records_the_sequence_count(self):
        self.assertIn("4,332", read(NOTE))


@unittest.skipUnless(
    os.path.exists(os.path.join(RAW, FILE_NAME)),
    "the assembly is not downloaded here; the raw data is not committed",
)
class DownloadTest(unittest.TestCase):
    """Tests that the downloaded file is the one the note describes.

    These run where the assembly has been fetched, and are skipped
    elsewhere - in continuous integration, where the raw data is absent by
    design.
    """

    def setUp(self):
        self.path = os.path.join(RAW, FILE_NAME)

    def test_the_md5_matches_the_published_checksum(self):
        with open(self.path, "rb") as handle:
            digest = hashlib.md5(handle.read()).hexdigest()
        self.assertEqual(digest, PUBLISHED_MD5)

    def test_the_sha256_matches_the_note(self):
        with open(self.path, "rb") as handle:
            digest = hashlib.sha256(handle.read()).hexdigest()
        self.assertIn(digest, read(NOTE))

    def test_the_size_matches_the_note(self):
        size = os.path.getsize(self.path)
        self.assertIn(f"{size:,} bytes", read(NOTE))


if __name__ == "__main__":
    unittest.main()
