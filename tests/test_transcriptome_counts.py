#!/usr/bin/env python3
"""Tests for the record-count comparison between the transcriptome sources.

Run them with:

    python3 -m unittest discover -s tests

P01-03.3 compared the record counts of the two transcriptome sources, as
§3.2 step 1 of the pre-registration asks. The comparison found that the
counts do not agree, and why: AplysiaTools is not one build but a directory
of files from four different years, and the merged-unigene FASTA (2020) and
the Orvis 2022 assembly are two different builds.

Two things about that are worth holding in place.

The first is the numbers. The counts and the overlaps in the note are the
result of a real comparison, and a test that fails if somebody "fixes" a
discrepancy by quietly changing a number is worth more than the number.

The second is the trap. AplysiaTools writes tissue-prefixed identifiers
(`salivary.asmbl_100`) in the current annotation and the per-tissue files,
and bare identifiers (`asmbl_100`) in the merged-unigene FASTA and the
protein set. Compared without removing the prefix, the six per-tissue sets
look disjoint from each other -- which is an artefact, because 15,926
unigenes occur in more than one tissue. There is a test for that too.

The tests that need the downloaded files are skipped where they are absent,
which is continuous integration by design. The ones that only need the
committed record always run.
"""

import os
import subprocess
import sys
import unittest

REPO_ROOT = os.path.join(os.path.dirname(__file__), os.pardir)
RAW = os.path.join(REPO_ROOT, "data", "raw")
DERIVED = os.path.join(REPO_ROOT, "data", "derived")
NOTE = os.path.join(REPO_ROOT, "docs", "P01-03-3-record-count-comparison.md")
SCRIPT = os.path.join(REPO_ROOT, "scripts", "compare_transcriptome_counts.py")
FETCH_TISSUES = os.path.join(REPO_ROOT, "scripts", "fetch_tissue_unigenes.py")

TSA_FASTA = "tsa.GJYY.1.fsa_nt.gz"
TSA_NAMES = "tsa_transcript_names.tsv"
MERGED = "new_unigenes.fasta"
PROTEINS = "annotation_1A-2C.fasta"
CURRENT = "current.annotation.fasta"
TRINOTATE = "merged.unigenes.trinotate.longest_orf.json"
TISSUE_IDS = "tissue_unigene_ids.tsv"

# The record counts, as established on 2026-11-22 by counting the files.
COUNTS = {
    "tsa": 68308,
    "proteins": 39486,
    "merged": 26849,
    "trinotate": 24339,
    "current_records": 196953,
    "current_distinct": 174400,
    "tissue_records": 157467,
    "tissue_distinct": 139303,
}

# The per-tissue files, and how many records each holds.
TISSUES = {
    "salivary": 19329,
    "digestive": 26153,
    "hepatopancreas": 25819,
    "heart": 25467,
    "muscle": 32933,
    "hermaphroditic": 27766,
}

# The overlaps, in both directions.
OVERLAPS = {
    ("proteins", "tsa"): 38129,
    ("merged", "tsa"): 12551,
    ("merged", "proteins"): 8089,
    ("merged", "current"): 9826,
    ("per_tissue", "current_non_cns"): 139303,
    ("per_tissue", "proteins"): 4389,
}

# The unigenes of the current annotation that occur under CNS and under
# another tissue both: 39,486 + 139,303 - 4,389 = 174,400.
CNS_AND_OTHER = 4389

# The `asmbl_` identifiers in each set: how many, and how many are in the
# TSA. The protein set's are all in it; the merged unigenes' are not.
ASMBL = {
    "merged": 24099,
    "proteins": 13314,
    "tsa": 23003,
}
ASMBL_IN_TSA = {
    "merged": 10458,
    "proteins": 13314,
}

# The counts the Orvis 2022 paper publishes.
PAPER_COUNTS = {
    "clusters": 71104,
    "unigenes": 68308,
    "unigenes_ge_400bp_orf": 39486,
    "transcripts_ge_400bp_orf": 38125,
}

# Unigenes occurring in more than one of the six per-tissue files.
MULTI_TISSUE = 15926

# The last-modified dates of the AplysiaTools files, as the server reports
# them. They are what shows that the directory holds four builds.
LAST_MODIFIED = {
    MERGED: "11 Nov 2020",
    TRINOTATE: "11 Nov 2020",
    PROTEINS: "28 Apr 2021",
    CURRENT: "15 Jul 2025",
}


def read(path):
    """Return the contents of a file.

    Args:
        path: the path of the file.

    Returns:
        The contents, as text.
    """
    with open(path, encoding="utf-8") as handle:
        return handle.read()


def fasta_ids(path):
    """Return the identifiers of a FASTA file.

    Args:
        path: the path of the file.

    Returns:
        The identifiers, in file order.
    """
    out = []
    with open(path, encoding="utf-8", errors="replace") as handle:
        for line in handle:
            if line.startswith(">"):
                out.append(line[1:].strip().split()[0])
    return out


def bare(identifier):
    """Return an identifier without its tissue prefix.

    Args:
        identifier: the identifier.

    Returns:
        The unprefixed identifier.
    """
    return identifier.split(".", 1)[1] if "." in identifier else identifier


def have(*names):
    """Return whether every named derived or raw file is present.

    Args:
        names: the file names, relative to data/raw or data/derived.

    Returns:
        True when they are all there.
    """
    for name in names:
        if not (
            os.path.exists(os.path.join(RAW, name))
            or os.path.exists(os.path.join(DERIVED, name))
        ):
            return False
    return True


class CommittedRecord(unittest.TestCase):
    """What the repository itself records, checked without the data."""

    def test_note_exists(self):
        """The note is committed."""
        self.assertTrue(os.path.exists(NOTE), f"{NOTE} is missing")

    def test_note_states_the_counts(self):
        """The note carries the counts it is about."""
        note = read(NOTE)
        for value in ("68,308", "39,486", "26,849", "196,953", "157,467"):
            self.assertIn(value, note, f"{value} is not in the note")

    def test_note_states_the_overlaps(self):
        """The note carries the overlaps it is about."""
        note = read(NOTE)
        for value in ("38,129", "12,551", "8,089", "9,826", "139,303"):
            self.assertIn(value, note, f"{value} is not in the note")

    def test_note_states_the_multi_tissue_count(self):
        """The note carries the number of unigenes shared across tissues."""
        self.assertIn("15,926", read(NOTE))

    def test_note_records_the_paper_counts(self):
        """The paper's own counts are in the note, not only in the script."""
        note = read(NOTE)
        for value in ("71,104", "38,125"):
            self.assertIn(value, note, f"{value} is not in the note")

    def test_note_records_the_build_dates(self):
        """The note says which build is which, by date."""
        note = read(NOTE)
        for value in ("2020-11-11", "2021-04-28", "2022-06-10", "2023-02-10", "2025-07-15"):
            self.assertIn(value, note, f"{value} is not in the note")

    def test_note_points_at_the_deviation(self):
        """The note files the deviation rather than editing the methods."""
        self.assertIn("#30", read(NOTE))

    def test_note_does_not_claim_agreement(self):
        """The note does not claim the two sources are the same build."""
        note = read(NOTE).lower()
        self.assertIn("do not agree", note)

    def test_script_carries_the_paper_counts(self):
        """The comparison script holds the paper's counts as data."""
        source = read(SCRIPT)
        for name, count in PAPER_COUNTS.items():
            self.assertIn(f'"{name}": {count}', source, f"{name} is not in the script")

    def test_script_is_runnable(self):
        """The comparison script runs and reports what it finds."""
        if not have(TSA_FASTA, TSA_NAMES, MERGED, PROTEINS, CURRENT, TRINOTATE):
            self.skipTest("the downloaded files are not here")
        result = subprocess.run(
            [sys.executable, SCRIPT], capture_output=True, text=True
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("record counts", result.stdout)

    def test_fetch_script_is_committed(self):
        """The per-tissue fetch script is committed."""
        self.assertTrue(os.path.exists(FETCH_TISSUES))


class TheCounts(unittest.TestCase):
    """The record counts, checked against the downloaded files."""

    def setUp(self):
        """Skip when the data is not here."""
        if not have(TSA_FASTA, MERGED, PROTEINS, CURRENT, TRINOTATE):
            self.skipTest("the downloaded files are not here")

    def test_tsa_record_count(self):
        """The TSA holds 68,308 sequences."""
        import gzip

        path = os.path.join(RAW, TSA_FASTA)
        count = 0
        with gzip.open(path, "rt", encoding="utf-8", errors="replace") as handle:
            for line in handle:
                if line.startswith(">"):
                    count += 1
        self.assertEqual(count, COUNTS["tsa"])

    def test_protein_count(self):
        """The CNS protein set holds 39,486 proteins."""
        self.assertEqual(len(fasta_ids(os.path.join(RAW, PROTEINS))), COUNTS["proteins"])

    def test_merged_count(self):
        """The merged-unigene FASTA holds 26,849 sequences."""
        self.assertEqual(len(fasta_ids(os.path.join(RAW, MERGED))), COUNTS["merged"])

    def test_trinotate_count(self):
        """The Trinotate JSON annotates 24,339 unigenes."""
        import json

        path = os.path.join(RAW, TRINOTATE)
        with open(path, encoding="utf-8") as handle:
            entries = json.load(handle)
        self.assertEqual(len(entries), COUNTS["trinotate"])

    def test_current_annotation_counts(self):
        """The current annotation holds 196,953 records and 174,400 unigenes."""
        ids = fasta_ids(os.path.join(RAW, CURRENT))
        self.assertEqual(len(ids), COUNTS["current_records"])
        self.assertEqual(len({bare(i) for i in ids}), COUNTS["current_distinct"])

    def test_protein_set_is_the_cns_set(self):
        """The CNS protein set is the current annotation's CNS set."""
        cns = {
            bare(i)
            for i in fasta_ids(os.path.join(RAW, CURRENT))
            if i.split(".", 1)[0] == "CNS"
        }
        proteins = set(fasta_ids(os.path.join(RAW, PROTEINS)))
        self.assertEqual(proteins, cns)

    def test_asmbl_split(self):
        """Each set's identifiers split the way the note says."""
        for name, path, expected in (
            ("merged", MERGED, ASMBL["merged"]),
            ("proteins", PROTEINS, ASMBL["proteins"]),
        ):
            ids = [i for i in fasta_ids(os.path.join(RAW, path)) if i.startswith("asmbl_")]
            self.assertEqual(len(ids), expected, f"{name} has the wrong asmbl_ count")


class TheOverlaps(unittest.TestCase):
    """The overlaps, checked against the downloaded files."""

    def setUp(self):
        """Skip when the data is not here."""
        if not have(TSA_FASTA, TSA_NAMES, MERGED, PROTEINS, CURRENT):
            self.skipTest("the downloaded files are not here")

    def tsa_name_set(self):
        """Return the original names of the TSA records.

        Returns:
            The set of names.
        """
        names = set()
        with open(os.path.join(DERIVED, TSA_NAMES), encoding="utf-8") as handle:
            next(handle, None)
            for line in handle:
                parts = line.rstrip("\n").split("\t")
                if len(parts) >= 2:
                    names.add(parts[1])
        return names

    def test_proteins_in_tsa(self):
        """38,129 of the protein set's identifiers are in the TSA."""
        proteins = set(fasta_ids(os.path.join(RAW, PROTEINS)))
        self.assertEqual(len(proteins & self.tsa_name_set()), OVERLAPS[("proteins", "tsa")])

    def test_merged_in_tsa(self):
        """12,551 of the merged unigenes' identifiers are in the TSA."""
        merged = set(fasta_ids(os.path.join(RAW, MERGED)))
        self.assertEqual(len(merged & self.tsa_name_set()), OVERLAPS[("merged", "tsa")])

    def test_merged_and_proteins(self):
        """8,089 identifiers are in both AplysiaTools files."""
        merged = set(fasta_ids(os.path.join(RAW, MERGED)))
        proteins = set(fasta_ids(os.path.join(RAW, PROTEINS)))
        self.assertEqual(len(merged & proteins), OVERLAPS[("merged", "proteins")])

    def test_merged_in_current_annotation(self):
        """9,826 of the merged unigenes are in the current annotation."""
        merged = set(fasta_ids(os.path.join(RAW, MERGED)))
        current = {bare(i) for i in fasta_ids(os.path.join(RAW, CURRENT))}
        self.assertEqual(len(merged & current), OVERLAPS[("merged", "current")])

    def test_every_asmbl_protein_is_in_the_tsa(self):
        """All 13,314 `asmbl_` identifiers of the protein set are in the TSA."""
        proteins = {i for i in fasta_ids(os.path.join(RAW, PROTEINS)) if i.startswith("asmbl_")}
        self.assertEqual(len(proteins), ASMBL["proteins"])
        self.assertTrue(proteins <= self.tsa_name_set())

    def test_not_every_asmbl_merged_is_in_the_tsa(self):
        """The merged unigenes' `asmbl_` identifiers are only partly in the TSA."""
        merged = {i for i in fasta_ids(os.path.join(RAW, MERGED)) if i.startswith("asmbl_")}
        shared = merged & self.tsa_name_set()
        self.assertEqual(len(shared), ASMBL_IN_TSA["merged"])
        self.assertLess(len(shared), len(merged))


class ThePerTissueFiles(unittest.TestCase):
    """The six per-tissue files, checked against the fetched identifiers."""

    def setUp(self):
        """Skip when the identifiers are not here."""
        if not os.path.exists(os.path.join(DERIVED, TISSUE_IDS)):
            self.skipTest("the per-tissue identifiers have not been fetched")

    def tissue_ids(self):
        """Return the identifiers of each tissue.

        Returns:
            The mapping of tissue to identifier set.
        """
        per = {}
        with open(os.path.join(DERIVED, TISSUE_IDS), encoding="utf-8") as handle:
            next(handle, None)
            for line in handle:
                parts = line.rstrip("\n").split("\t")
                if len(parts) >= 3:
                    per.setdefault(parts[0], []).append(bare(parts[2]))
        return per

    def test_per_tissue_counts(self):
        """Each per-tissue file holds the count the note gives."""
        per = self.tissue_ids()
        for tissue, count in TISSUES.items():
            self.assertEqual(len(per[tissue]), count, f"{tissue} has the wrong count")

    def test_total_and_distinct(self):
        """The six files hold 157,467 records and 139,303 distinct unigenes."""
        per = self.tissue_ids()
        every = [i for ids in per.values() for i in ids]
        self.assertEqual(len(every), COUNTS["tissue_records"])
        self.assertEqual(len(set(every)), COUNTS["tissue_distinct"])

    def test_multi_tissue_count(self):
        """15,926 unigenes occur in more than one tissue."""
        per = self.tissue_ids()
        seen = {}
        for tissue, ids in per.items():
            for identifier in ids:
                seen.setdefault(identifier, set()).add(tissue)
        shared = sum(1 for tissues in seen.values() if len(tissues) > 1)
        self.assertEqual(shared, MULTI_TISSUE)

    def test_the_prefix_trap_is_real(self):
        """The prefix makes the sets look disjoint when they are not."""
        per = self.tissue_ids()
        prefixed = {f"{tissue}.{identifier}" for tissue, ids in per.items() for identifier in ids}
        bare_ids = {identifier for ids in per.values() for identifier in ids}
        # As prefixed identifiers the six files share nothing at all.
        self.assertEqual(len(prefixed), COUNTS["tissue_records"])
        self.assertEqual(len(bare_ids), COUNTS["tissue_distinct"])
        self.assertLess(len(bare_ids), len(prefixed))

    def test_the_current_annotation_decomposes(self):
        """The current annotation is its CNS set plus the six per-tissue files."""
        if not os.path.exists(os.path.join(RAW, CURRENT)):
            self.skipTest("the current annotation is not here")
        ids = fasta_ids(os.path.join(RAW, CURRENT))
        cns = sum(1 for i in ids if i.split(".", 1)[0] == "CNS")
        per = self.tissue_ids()
        tissue_records = sum(len(v) for v in per.values())
        self.assertEqual(cns, COUNTS["proteins"])
        self.assertEqual(cns + tissue_records, COUNTS["current_records"])

    def test_the_per_tissue_files_are_in_the_current_annotation(self):
        """The six per-tissue files are the current annotation's non-CNS part."""
        if not os.path.exists(os.path.join(RAW, CURRENT)):
            self.skipTest("the current annotation is not here")
        per = self.tissue_ids()
        union = {i for ids in per.values() for i in ids}
        ids = fasta_ids(os.path.join(RAW, CURRENT))
        cns = {bare(i) for i in ids if i.split(".", 1)[0] == "CNS"}
        non_cns = {bare(i) for i in ids if i.split(".", 1)[0] != "CNS"}
        self.assertEqual(len(non_cns), OVERLAPS[("per_tissue", "current_non_cns")])
        # The same set, not merely the same size.
        self.assertEqual(non_cns, union)
        # And the distinct count of the whole file follows from the two.
        self.assertEqual(len(cns) + len(non_cns) - CNS_AND_OTHER, COUNTS["current_distinct"])


if __name__ == "__main__":
    unittest.main()
