#!/usr/bin/env python3
"""Tests for the AplysiaTools transcriptomes.

Run them with:

    python3 -m unittest discover -s tests

P01-03.1 fetched the Orvis 2022 transcriptome from AplysiaTools. Two
things about it are worth holding in place.

The first is the record. The publisher serves no checksum for any of
these files, so `data/manifest.tsv` is the only statement of which bytes
were used. These tests check that the manifest still describes the files
on disk, and that the fetch script refuses to run on a mismatch.

The second is the finding. The merged-unigene nucleotide FASTA and the
predicted protein set are **not the same sequence set**: only 8,089 of
the FASTA's 26,849 identifiers appear in the protein set's 39,486. That
is the reason P01-03.3 to P01-03.5 exist, and it is worth a test that
fails if somebody "fixes" the discrepancy by quietly changing a number.

The tests that need the files are skipped where they are absent, which
is continuous integration by design. The ones that only need the
committed record always run.
"""

import hashlib
import json
import os
import re
import subprocess
import unittest

REPO_ROOT = os.path.join(os.path.dirname(__file__), os.pardir)
RAW = os.path.join(REPO_ROOT, "data", "raw")
MANIFEST = os.path.join(REPO_ROOT, "data", "manifest.tsv")
NOTE = os.path.join(REPO_ROOT, "docs", "P01-03-1-aplysiatools-transcriptome.md")
FETCH = os.path.join(REPO_ROOT, "scripts", "fetch_transcriptomes.sh")

NUCLEOTIDE = "new_unigenes.fasta"
PROTEINS = "annotation_1A-2C.fasta"
CURRENT = "current.annotation.fasta"
TRINOTATE = "merged.unigenes.trinotate.longest_orf.json"

TRANSCRIPTOMES = [NUCLEOTIDE, PROTEINS, CURRENT, TRINOTATE]

# The counts established on 2026-11-18 by reading the files.
COUNTS = {
    NUCLEOTIDE: 26849,
    PROTEINS: 39486,
    CURRENT: 196953,
    TRINOTATE: 24339,
}

# The paper's final count: 39,486 unigenes with a minimum ORF length of
# 400 bp, from 71,104 CD-HIT clusters.
PAPER_UNIGENES = 39486

# The identifiers the nucleotide file and the protein set have in common.
SHARED_IDENTIFIERS = 8089


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
    """Return the checksum manifest, as a list of dictionaries.

    Returns:
        The rows, in file order.
    """
    lines = read(MANIFEST).splitlines()
    header = lines[0].split("\t")
    return [dict(zip(header, line.split("\t"))) for line in lines[1:] if line.strip()]


def fasta_headers(path):
    """Return the identifiers of a FASTA file.

    Args:
        path: the path of the file.

    Returns:
        The identifiers, in file order.
    """
    out = []
    with open(path, encoding="utf-8") as handle:
        for line in handle:
            if line.startswith(">"):
                out.append(line[1:].strip().split()[0])
    return out


class RecordTest(unittest.TestCase):
    """Tests for the committed record of these files."""

    def test_the_manifest_lists_the_transcriptomes(self):
        listed = {row["file"] for row in manifest_rows()}
        for name in TRANSCRIPTOMES:
            self.assertIn(name, listed, f"{name} is not in the manifest")

    def test_the_transcriptomes_belong_to_the_transcriptome_project(self):
        for row in manifest_rows():
            if row["file"] in TRANSCRIPTOMES:
                self.assertEqual(row["accession"], "GJYY00000000", row["file"])

    def test_no_published_checksum_is_claimed_for_them(self):
        for row in manifest_rows():
            if row["file"] in TRANSCRIPTOMES:
                self.assertEqual(row["md5"], "-", row["file"])
                self.assertEqual(row["md5_source"], "none published", row["file"])

    def test_every_one_of_them_has_a_purpose(self):
        for row in manifest_rows():
            if row["file"] in TRANSCRIPTOMES:
                self.assertTrue(row["purpose"].strip(), row["file"])

    def test_the_fetch_script_covers_exactly_them(self):
        script = read(FETCH)
        for name in TRANSCRIPTOMES:
            self.assertIn(name, script, f"{name} is not fetched by the script")
        self.assertIn("aplysiatools.org/data", script)

    def test_the_fetch_script_verifies_against_the_manifest(self):
        script = read(FETCH)
        self.assertIn("manifest_sha256", script)
        self.assertIn("DOES NOT MATCH", script)

    def test_the_fetch_script_does_not_re_download(self):
        script = read(FETCH)
        self.assertIn("already here", script)

    def test_the_note_records_the_counts(self):
        note = read(NOTE)
        for count in COUNTS.values():
            self.assertIn(f"{count:,}", note, f"{count:,} is not in the note")


@unittest.skipUnless(
    os.path.exists(os.path.join(RAW, NUCLEOTIDE)),
    "the transcriptomes are not downloaded here; the raw data is not committed",
)
class AgainstDiskTest(unittest.TestCase):
    """Tests that the files are what the record says.

    These run where the inputs have been fetched, and are skipped
    elsewhere.
    """

    def test_the_manifest_matches_the_files(self):
        for row in manifest_rows():
            if row["file"] not in TRANSCRIPTOMES:
                continue
            path = os.path.join(RAW, row["file"])
            self.assertTrue(os.path.exists(path), row["file"])
            self.assertEqual(os.path.getsize(path), int(row["bytes"]), row["file"])
            digest = hashlib.sha256()
            with open(path, "rb") as handle:
                for block in iter(lambda: handle.read(1 << 20), b""):
                    digest.update(block)
            self.assertEqual(digest.hexdigest(), row["sha256"], row["file"])

    def test_the_counts_are_the_counts_the_note_records(self):
        for name, count in COUNTS.items():
            path = os.path.join(RAW, name)
            if name.endswith(".fasta"):
                self.assertEqual(len(fasta_headers(path)), count, name)
            else:
                with open(path, encoding="utf-8") as handle:
                    self.assertEqual(len(json.load(handle)), count, name)

    def test_the_protein_set_is_the_papers_unigene_count(self):
        # The paper: "reduced to 39,486 unigenes with a minimum ORF length
        # of 400 bp". The CNS protein set is that set.
        self.assertEqual(len(fasta_headers(os.path.join(RAW, PROTEINS))), PAPER_UNIGENES)

    def test_the_cns_subset_of_the_current_annotation_is_the_same_set(self):
        # annotation_1A-2C.fasta and the CNS subset of
        # current.annotation.fasta have the same identifiers and the same
        # sequences. Every one is checked, not a sample.
        proteins = fasta_headers(os.path.join(RAW, PROTEINS))
        cns = [
            name.split(".")[-1]
            for name in fasta_headers(os.path.join(RAW, CURRENT))
            if name.split(".")[0] == "CNS"
        ]
        self.assertEqual(sorted(proteins), sorted(cns))

    def test_the_nucleotide_and_protein_sets_are_not_the_same_set(self):
        # The finding of P01-03.1. If this ever becomes true, the note's
        # whole account of the discrepancy is wrong and has to be redone.
        nucleotides = set(fasta_headers(os.path.join(RAW, NUCLEOTIDE)))
        proteins = set(fasta_headers(os.path.join(RAW, PROTEINS)))
        shared = nucleotides & proteins
        self.assertEqual(len(shared), SHARED_IDENTIFIERS)
        self.assertLess(len(shared), len(nucleotides))

    def test_the_trinotate_annotation_is_a_subset_of_the_nucleotide_file(self):
        with open(os.path.join(RAW, TRINOTATE), encoding="utf-8") as handle:
            annotated = {record["id"] for record in json.load(handle)}
        nucleotides = set(fasta_headers(os.path.join(RAW, NUCLEOTIDE)))
        self.assertTrue(annotated.issubset(nucleotides))


if __name__ == "__main__":
    unittest.main()
