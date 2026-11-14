#!/usr/bin/env python3
"""Tests for the checksum manifest of the downloaded inputs.

Run them with:

    python3 -m unittest discover -s tests

This is not the tool manifest of P01-01.x, which lives in
tests/test_manifest.py and describes the packages inside the image. This
one describes the data files: the inputs are gitignored and are
re-fetched, so the manifest is the only committed record of the bytes the
analysis ran on.

It has three things to agree with, and this test holds all three
together:

  * the files on disk, when they are there;
  * the two download notes, which record the same checksums in prose;
  * NCBI's published checksums, for the files that have them.

The checks that do not need the raw data always run, because the manifest
is committed and the notes are committed, and a disagreement between them
is a disagreement nobody would otherwise see. The checks that need the raw
data are skipped where it is absent, which is continuous integration by
design.
"""

import hashlib
import os
import re
import subprocess
import unittest

REPO_ROOT = os.path.join(os.path.dirname(__file__), os.pardir)
MANIFEST = os.path.join(REPO_ROOT, "data", "manifest.tsv")
RAW = os.path.join(REPO_ROOT, "data", "raw")
ASSEMBLY_NOTE = os.path.join(REPO_ROOT, "docs", "P01-02-2-assembly-download.md")
ANNOTATION_NOTE = os.path.join(REPO_ROOT, "docs", "P01-02-3-annotation-download.md")

COLUMNS = [
    "file",
    "assembly",
    "annotation_release",
    "url",
    "bytes",
    "md5",
    "md5_source",
    "sha256",
    "purpose",
]

# The files that make up the inputs. md5checksums.txt is the publisher's
# own list, and it is in the manifest because the manifest's md5 column is
# taken from it.
INPUTS = [
    "GCF_000002075.1_AplCal3.0_genomic.fna.gz",
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


def manifest_rows():
    """Return the manifest, as a list of dictionaries.

    Returns:
        The rows, in file order.
    """
    lines = read(MANIFEST).splitlines()
    header = lines[0].split("\t")
    rows = []
    for line in lines[1:]:
        if not line.strip():
            continue
        values = line.split("\t")
        rows.append(dict(zip(header, values)))
    return rows


def note_checksums(path):
    """Return the checksums a download note records.

    The annotation note records one row per file; the assembly note records
    a single file as a vertical table. Both shapes are read here.

    Args:
        path: the path of the note.

    Returns:
        A mapping of file name to SHA-256.
    """
    recorded = {}
    for line in read(path).splitlines():
        match = re.match(r"\|\s*`([^`]+)`\s*\|\s*`([0-9a-f]{64})`\s*\|", line)
        if match:
            recorded[match.group(1)] = match.group(2)
    return recorded


def assembly_note_checksum():
    """Return the SHA-256 the assembly note records.

    Returns:
        The checksum, as text.
    """
    match = re.search(r"\|\s*SHA-256\s*\|\s*`([0-9a-f]{64})`\s*\|", read(ASSEMBLY_NOTE))
    return match.group(1) if match else ""


class ManifestTest(unittest.TestCase):
    """Tests for the manifest's own shape."""

    def test_the_manifest_exists(self):
        self.assertTrue(os.path.exists(MANIFEST))

    def test_the_manifest_is_not_ignored(self):
        # The manifest is the committed record of the inputs. If it were
        # ignored it would exist only on the machine that made it, and the
        # inputs would have no committed record at all.
        result = subprocess.run(
            ["git", "check-ignore", "-q", "data/manifest.tsv"],
            cwd=REPO_ROOT,
            capture_output=True,
            check=False,
        )
        self.assertNotEqual(result.returncode, 0, "data/manifest.tsv is gitignored")

    def test_the_header_is_the_expected_one(self):
        header = read(MANIFEST).splitlines()[0].split("\t")
        self.assertEqual(header, COLUMNS)

    def test_every_input_is_in_the_manifest(self):
        names = {row["file"] for row in manifest_rows()}
        for name in INPUTS:
            self.assertIn(name, names, f"{name} is not in the manifest")

    def test_the_manifest_has_no_duplicate_files(self):
        names = [row["file"] for row in manifest_rows()]
        self.assertEqual(len(names), len(set(names)))

    def test_every_row_has_a_well_formed_checksum(self):
        for row in manifest_rows():
            self.assertRegex(row["sha256"], r"^[0-9a-f]{64}$", row["file"])

    def test_every_row_has_a_size_and_a_purpose(self):
        for row in manifest_rows():
            self.assertGreater(int(row["bytes"]), 0, row["file"])
            self.assertTrue(row["purpose"].strip(), row["file"])

    def test_every_row_names_the_assembly_and_a_release(self):
        for row in manifest_rows():
            self.assertEqual(row["assembly"], "GCF_000002075.1", row["file"])
            self.assertTrue(row["annotation_release"].strip(), row["file"])

    def test_the_urls_point_at_the_assembly_directory(self):
        for row in manifest_rows():
            self.assertIn("GCF/000/002/075/GCF_000002075.1_AplCal3.0", row["url"], row["file"])


class AgreementTest(unittest.TestCase):
    """Tests that the manifest and the download notes agree.

    These always run. The notes are committed, the manifest is committed,
    and a disagreement between them means one of them is wrong about the
    bytes the analysis ran on.
    """

    def test_the_annotation_note_checksums_are_in_the_manifest(self):
        recorded = note_checksums(ANNOTATION_NOTE)
        self.assertTrue(recorded, "the annotation note records no checksums")
        in_manifest = {row["file"]: row["sha256"] for row in manifest_rows()}
        for name, checksum in recorded.items():
            self.assertIn(name, in_manifest, f"{name} is in the note and not in the manifest")
            self.assertEqual(in_manifest[name], checksum, f"the manifest and the note differ on {name}")

    def test_the_assembly_note_checksum_is_in_the_manifest(self):
        checksum = assembly_note_checksum()
        self.assertTrue(checksum, "the assembly note records no sha256")
        in_manifest = {row["file"]: row["sha256"] for row in manifest_rows()}
        self.assertIn(
            "GCF_000002075.1_AplCal3.0_genomic.fna.gz",
            in_manifest,
            "the assembly is not in the manifest",
        )
        self.assertEqual(
            in_manifest["GCF_000002075.1_AplCal3.0_genomic.fna.gz"], checksum
        )


@unittest.skipUnless(
    os.path.exists(os.path.join(RAW, INPUTS[0])),
    "the inputs are not downloaded here; the raw data is not committed",
)
class AgainstDiskTest(unittest.TestCase):
    """Tests that the manifest matches the files on disk.

    These run where the inputs have been fetched, and are skipped
    elsewhere.
    """

    def test_every_file_in_the_manifest_is_present(self):
        for row in manifest_rows():
            self.assertTrue(
                os.path.exists(os.path.join(RAW, row["file"])),
                f"{row['file']} is in the manifest and not on disk",
            )

    def test_no_file_on_disk_is_missing_from_the_manifest(self):
        listed = {row["file"] for row in manifest_rows()}
        for name in os.listdir(RAW):
            if name.startswith("."):
                continue
            self.assertIn(name, listed, f"{name} is on disk and not in the manifest")

    def test_the_sizes_and_checksums_match(self):
        for row in manifest_rows():
            path = os.path.join(RAW, row["file"])
            self.assertEqual(os.path.getsize(path), int(row["bytes"]), row["file"])
            digest = hashlib.sha256()
            with open(path, "rb") as handle:
                for block in iter(lambda: handle.read(1 << 20), b""):
                    digest.update(block)
            self.assertEqual(digest.hexdigest(), row["sha256"], row["file"])

    def test_the_published_md5s_match(self):
        for row in manifest_rows():
            if row["md5_source"] != "published by NCBI":
                continue
            digest = hashlib.md5()
            with open(os.path.join(RAW, row["file"]), "rb") as handle:
                for block in iter(lambda: handle.read(1 << 20), b""):
                    digest.update(block)
            self.assertEqual(digest.hexdigest(), row["md5"], row["file"])


if __name__ == "__main__":
    unittest.main()
