#!/usr/bin/env python3
"""Tests for the 50-sequence comparison between the transcriptome sources.

Run them with:

    python3 -m unittest discover -s tests

P01-03.4 sampled fifty sequences from each of the two AplysiaTools
transcriptomes and compared them with the GenBank TSA. The results were
clean enough to be worth holding in place: wherever the two sources have a
transcript in common, they carry the same sequence, and the only twelve
disagreements in the whole programme are the same transcript with 35 to 71
extra bases at one end.

Two corrections came out of the subtask, and they are worth a test each,
because both were wrong in a way that looked right.

The first is that **every AplysiaTools transcriptome file is nucleotide**.
The earlier notes called two of them protein sets. There is not one
amino-acid letter in half a gigabase of sequence, and there is no protein
FASTA at AplysiaTools at all.

The second is that **the TSA FASTA's own headers carry the original
assembly names**. The P01-03.2 note said nothing in the FASTA related the
two identifier namespaces, and that was wrong: all 68,308 headers do, and
they agree with the GenBank flatfile's mapping.

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
NOTE = os.path.join(REPO_ROOT, "docs", "P01-03-4-sequence-sampling.md")
SCRIPT = os.path.join(REPO_ROOT, "scripts", "sample_transcriptome_sequences.py")

TSA_FASTA = "tsa.GJYY.1.fsa_nt.gz"
TSA_NAMES = "tsa_transcript_names.tsv"
MERGED = "new_unigenes.fasta"
CNS = "annotation_1A-2C.fasta"

# The seed and the size the comparison used.
SEED = 20261005
SIZE = 50

# The results: (comparison, identical, differ, absent, compared).
EXHAUSTIVE = {
    "CNS set against the TSA": (38117, 12, 1357, 39486),
    "merged unigenes against the TSA": (12551, 0, 14298, 26849),
    "CNS set against the merged unigenes": (8089, 0, 31397, 39486),
}

# The fifty-sequence sample: (comparison, identical, differ, absent).
SAMPLE = {
    "A merged_unigenes_vs_tsa": (20, 0, 30),
    "B cns_set_vs_tsa": (50, 0, 0),
    "C cns_set_vs_merged_unigenes": (50, 0, 0),
}

# The twelve that differ, and how much the AplysiaTools copy has extra.
DIFFERENCES = {
    "TRINITY_DN112932_c0_g1_i2": 35,
    "TRINITY_DN100754_c0_g2_i1": 35,
    "TRINITY_DN28874_c0_g1_i1": 46,
    "TRINITY_DN21759_c0_g1_i1": 46,
    "TRINITY_DN31038_c0_g1_i9": 53,
    "TRINITY_DN102387_c0_g2_i1": 54,
    "TRINITY_DN153_c4_g1_i2": 55,
    "TRINITY_DN279799_c0_g1_i1": 55,
    "TRINITY_DN11733_c0_g1_i3": 56,
    "TRINITY_DN79354_c0_g1_i1": 59,
    "TRINITY_DN252891_c0_g1_i1": 64,
    "TRINITY_DN21344_c1_g1_i6": 71,
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


def have(*names):
    """Return whether every named file is present.

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


def alphabet(path):
    """Return the letters that appear in a FASTA file.

    Args:
        path: the path of the file.

    Returns:
        A pair of (mapping of letter to count, total residues).
    """
    counts = {}
    total = 0
    with open(path, encoding="utf-8", errors="replace") as handle:
        for line in handle:
            if line.startswith(">"):
                continue
            sequence = line.strip()
            total += len(sequence)
            for letter in sequence:
                counts[letter] = counts.get(letter, 0) + 1
    return counts, total


class CommittedRecord(unittest.TestCase):
    """What the repository itself records, checked without the data."""

    def test_note_exists(self):
        """The note is committed."""
        self.assertTrue(os.path.exists(NOTE), f"{NOTE} is missing")

    def test_note_states_the_sample_results(self):
        """The note carries the fifty-sequence results."""
        note = read(NOTE)
        for value in ("38,117", "12,551", "8,089", "39,486"):
            self.assertIn(value, note, f"{value} is not in the note")

    def test_note_states_the_twelve(self):
        """The note carries the twelve that differ."""
        note = read(NOTE)
        for identifier in DIFFERENCES:
            self.assertIn(identifier, note, f"{identifier} is not in the note")

    def test_note_states_the_correction(self):
        """The note says the files are nucleotide, not protein."""
        note = read(NOTE).lower()
        self.assertIn("nucleotide", note)
        self.assertIn("protein fasta at aplysiatools", note)

    def test_note_states_the_header_finding(self):
        """The note says the FASTA headers carry the original names."""
        self.assertIn("headers carry the original assembly name", read(NOTE))

    def test_script_is_committed(self):
        """The sampler is committed."""
        self.assertTrue(os.path.exists(SCRIPT))

    def test_script_uses_the_programme_seed(self):
        """The sampler uses the programme-wide seed."""
        source = read(SCRIPT)
        self.assertIn(f"P01_DEFAULT_SEED = {SEED}", source)

    def test_earlier_notes_carry_the_correction(self):
        """The three notes that used the wrong word carry a correction."""
        for name in (
            "P01-03-1-aplysiatools-transcriptome.md",
            "P01-03-2-genbank-tsa-transcriptome.md",
            "P01-03-3-record-count-comparison.md",
        ):
            path = os.path.join(REPO_ROOT, "docs", name)
            self.assertTrue(os.path.exists(path), f"{name} is missing")
            note = read(path)
            self.assertIn("Corrected 2026-11-24", note, f"{name} has no correction")


class TheAlphabet(unittest.TestCase):
    """The files are nucleotide, which is what makes the comparison sharp."""

    def setUp(self):
        """Skip when the data is not here."""
        if not have(MERGED, CNS, "current.annotation.fasta"):
            self.skipTest("the downloaded files are not here")

    def test_every_file_is_nucleotide(self):
        """No file holds an amino-acid letter."""
        for name in (MERGED, CNS, "current.annotation.fasta"):
            counts, total = alphabet(os.path.join(RAW, name))
            other = {
                letter: count
                for letter, count in counts.items()
                if letter not in "ACGT"
            }
            allowed = {"N"} if name == "current.annotation.fasta" else set()
            self.assertEqual(
                set(other) - allowed,
                set(),
                f"{name} holds letters that are not nucleotide: {sorted(other)}",
            )
            self.assertGreater(total, 0)

    def test_the_counts_are_the_recorded_ones(self):
        """Each file holds the number of records the note gives."""
        expected = {MERGED: 26849, CNS: 39486, "current.annotation.fasta": 196953}
        for name, count in expected.items():
            records = 0
            with open(os.path.join(RAW, name), encoding="utf-8", errors="replace") as h:
                for line in h:
                    if line.startswith(">"):
                        records += 1
            self.assertEqual(records, count, f"{name} holds the wrong number of records")


class TheNames(unittest.TestCase):
    """The TSA's headers carry the original names, and agree with the flatfile."""

    def setUp(self):
        """Skip when the data is not here."""
        if not have(TSA_FASTA, TSA_NAMES):
            self.skipTest("the downloaded files are not here")

    def test_the_headers_and_the_flatfile_agree(self):
        """All 68,308 names are the same in both records."""
        sys_path = os.path.join(REPO_ROOT, "scripts")
        if sys_path not in sys.path:
            sys.path.insert(0, sys_path)
        import sample_transcriptome_sequences as sampler

        _, accessions = sampler.tsa_sequences(os.path.join(RAW, TSA_FASTA))
        bridge = sampler.flatfile_names(os.path.join(DERIVED, TSA_NAMES))
        self.assertEqual(len(accessions), 68308)
        self.assertEqual(sampler.check_names(accessions, bridge), 68308)

    def test_the_script_runs(self):
        """The sampler runs and reports its results."""
        if not have(MERGED, CNS):
            self.skipTest("the downloaded files are not here")
        result = subprocess.run(
            [sys.executable, SCRIPT], capture_output=True, text=True
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("agree about all", result.stdout)


class TheResults(unittest.TestCase):
    """The comparisons themselves."""

    def setUp(self):
        """Skip when the data is not here."""
        if not have(TSA_FASTA, TSA_NAMES, MERGED, CNS):
            self.skipTest("the downloaded files are not here")

    def run_sampler(self):
        """Run the sampler and return its stdout.

        The sampler is run once for the class and the result reused, because
        it reads half a gigabyte and the four checks below want the same
        run.

        Returns:
            The output, as text.
        """
        if getattr(self.__class__, "cached", None) is None:
            result = subprocess.run(
                [sys.executable, SCRIPT], capture_output=True, text=True
            )
            assert result.returncode == 0, result.stderr
            self.__class__.cached = result.stdout
        return self.__class__.cached

    def test_the_sample_counts(self):
        """The fifty-sequence sample gives the recorded verdicts."""
        self.run_sampler()
        path = os.path.join(DERIVED, "sequence_sample.tsv")
        self.assertTrue(os.path.exists(path))
        rows = read(path).splitlines()[1:]
        tally = {}
        for row in rows:
            comparison, _, verdict, _ = row.split("\t")
            key = (comparison, verdict)
            tally[key] = tally.get(key, 0) + 1
        for comparison, (identical, differ, absent) in SAMPLE.items():
            self.assertEqual(tally.get((comparison, "identical"), 0), identical, comparison)
            self.assertEqual(tally.get((comparison, "differs"), 0), differ, comparison)
            self.assertEqual(tally.get((comparison, "absent"), 0), absent, comparison)

    def test_the_exhaustive_counts(self):
        """Every shared transcript agrees, except the twelve."""
        self.run_sampler()
        path = os.path.join(DERIVED, "sequence_exhaustive.tsv")
        self.assertTrue(os.path.exists(path))
        lines = read(path).splitlines()
        header = lines[0].split("\t")
        found = {}
        for line in lines[1:]:
            row = dict(zip(header, line.split("\t")))
            found[row["comparison"]] = (
                int(row["identical"]),
                int(row["differ"]),
                int(row["not_in_the_other"]),
                int(row["compared"]),
            )
        for comparison, expected in EXHAUSTIVE.items():
            self.assertEqual(found.get(comparison), expected, comparison)

    def test_the_twelve_are_extensions(self):
        """Each of the twelve is a contiguous extension of the other."""
        self.run_sampler()
        path = os.path.join(DERIVED, "sequence_differences.tsv")
        self.assertTrue(os.path.exists(path))
        lines = read(path).splitlines()
        header = lines[0].split("\t")
        found = {}
        for line in lines[1:]:
            row = dict(zip(header, line.split("\t")))
            found[row["identifier"]] = int(row["difference_nt"])
        self.assertEqual(found, DIFFERENCES)

    def test_the_sampling_is_deterministic(self):
        """The same seed gives the same sample."""
        self.run_sampler()
        first = read(os.path.join(DERIVED, "sequence_sample.tsv"))
        result = subprocess.run(
            [sys.executable, SCRIPT], capture_output=True, text=True
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        second = read(os.path.join(DERIVED, "sequence_sample.tsv"))
        self.assertEqual(first, second)


if __name__ == "__main__":
    unittest.main()
