#!/usr/bin/env python3
"""Tests for scripts/locus_diagnostics.py.

The fixtures are a synthetic chromosome with six loci whose expected
diagnostics are known by construction: a clean single-exon model, a clean
three-exon minus-strand model, a model with an internal stop codon, a model
below the 300 nt fragmentation threshold, a model with no stop codon, and a
model whose exons overlap an assembly gap. Every expected value below is
fixed by the fixture design, not by running the implementation, so the
tests fail if the implementation drifts.

Run them with:

    python3 -m unittest discover -s tests
"""

import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), os.pardir, "scripts"))

import locus_diagnostics as ld


def revcomp(sequence):
    """Return the reverse complement of an upper-case ACGT sequence.

    Args:
        sequence: the sequence.

    Returns:
        The reverse complement. Duplicated here, five lines, so the tests
        do not import the very function they are checking.
    """
    return sequence.translate(str.maketrans("ACGT", "TGCA"))[::-1]


# The six fixture loci on one synthetic chromosome, scaffold1.
#
# geneA  plus strand, one exon, CDS 101..700: ATG + 198*GCT + TAA (600 nt,
#        200 codons). Clean.
# geneB  minus strand, three exons, CDS segments 1001..1200, 2001..2200,
#        3001..3122 (522 nt, 174 codons: ATG + 172*GCT + TAA). Clean.
# geneC  plus strand, one exon, CDS 4001..4300 (300 nt, 100 codons: ATG +
#        GCT + TAA + 96*GCT + TAA). Internal stop at codon 3.
# geneD  plus strand, one exon, CDS 5001..5150 (150 nt, 50 codons: ATG +
#        48*GCT + TAA). Below the 300 nt threshold.
# geneE  plus strand, one exon, CDS 6001..6300 (300 nt, 100 codons: ATG +
#        99*GCT, no terminal stop, no stop_codon feature). No stop.
# geneF  plus strand, two exons, CDS 6901..6950 and 7005..7104 (150 nt).
#        An assembly gap (20 Ns) sits at 7001..7020, overlapping the
#        second exon.
GENE_A_CDS = "ATG" + "GCT" * 198 + "TAA"
GENE_B_MRNA = "ATG" + "GCT" * 172 + "TAA"
GENE_C_CDS = "ATG" + "GCT" + "TAA" + "GCT" * 96 + "TAA"
GENE_D_CDS = "ATG" + "GCT" * 48 + "TAA"
GENE_E_CDS = "ATG" + "GCT" * 99
GENE_F_MRNA = "ATG" + "GCT" * 48 + "TAA"


def build_scaffold():
    """Build the synthetic chromosome with the six fixture loci.

    Returns:
        The scaffold sequence as a string, 7200 bases, 1-based features
        as documented at module level.
    """
    scaffold = ["A"] * 7200

    def place(start, sequence):
        scaffold[start - 1 : start - 1 + len(sequence)] = sequence

    place(101, GENE_A_CDS)
    # Minus-strand geneB: transcription order is high to low, so the
    # mRNA's first chunk sits at the highest coordinates, reverse
    # complemented.
    place(3001, revcomp(GENE_B_MRNA[0:122]))
    place(2001, revcomp(GENE_B_MRNA[122:322]))
    place(1001, revcomp(GENE_B_MRNA[322:522]))
    place(4001, GENE_C_CDS)
    place(5001, GENE_D_CDS)
    place(6001, GENE_E_CDS)
    place(6901, GENE_F_MRNA[0:50])
    place(7005, GENE_F_MRNA[50:150])
    # The assembly gap overwrites whatever the gene model carried; that is
    # what a gap is. It overlaps geneF's second exon (7005..7104).
    place(7001, "N" * 20)
    return "".join(scaffold)


def build_gff3():
    """Build the GFF3 annotation for the six fixture loci.

    Returns:
        The GFF3 text. geneE deliberately has no stop_codon feature, so
        its stop status must come from the sequence.
    """

    def gene(identifier, start, end, strand):
        return (
            f"scaffold1\tfixture\tgene\t{start}\t{end}\t.\t{strand}\t.\t"
            f"ID={identifier};Name={identifier}"
        )

    def mrna(identifier, parent, start, end, strand):
        return (
            f"scaffold1\tfixture\tmRNA\t{start}\t{end}\t.\t{strand}\t.\t"
            f"ID={identifier};Parent={parent}"
        )

    def child(kind, identifier, parent, start, end, strand, phase="."):
        return (
            f"scaffold1\tfixture\t{kind}\t{start}\t{end}\t.\t{strand}\t"
            f"{phase}\tID={identifier};Parent={parent}"
        )

    lines = ["##gff-version 3"]
    lines.append(gene("geneA", 101, 700, "+"))
    lines.append(mrna("rnaA1", "geneA", 101, 700, "+"))
    lines.append(child("exon", "exonA1", "rnaA1", 101, 700, "+"))
    lines.append(child("CDS", "cdsA1", "rnaA1", 101, 700, "+", "0"))
    lines.append(child("start_codon", "scA1", "rnaA1", 101, 103, "+"))
    lines.append(child("stop_codon", "tcA1", "rnaA1", 698, 700, "+"))

    lines.append(gene("geneB", 1001, 3150, "-"))
    lines.append(mrna("rnaB1", "geneB", 1001, 3150, "-"))
    lines.append(child("exon", "exonB1", "rnaB1", 1001, 1200, "-"))
    lines.append(child("exon", "exonB2", "rnaB1", 2001, 2200, "-"))
    lines.append(child("exon", "exonB3", "rnaB1", 3001, 3150, "-"))
    lines.append(child("CDS", "cdsB1", "rnaB1", 1001, 1200, "-", "0"))
    lines.append(child("CDS", "cdsB2", "rnaB1", 2001, 2200, "-", "0"))
    lines.append(child("CDS", "cdsB3", "rnaB1", 3001, 3122, "-", "0"))
    lines.append(child("start_codon", "scB1", "rnaB1", 3120, 3122, "-"))
    lines.append(child("stop_codon", "tcB1", "rnaB1", 1001, 1003, "-"))

    lines.append(gene("geneC", 4001, 4300, "+"))
    lines.append(mrna("rnaC1", "geneC", 4001, 4300, "+"))
    lines.append(child("exon", "exonC1", "rnaC1", 4001, 4300, "+"))
    lines.append(child("CDS", "cdsC1", "rnaC1", 4001, 4300, "+", "0"))
    lines.append(child("start_codon", "scC1", "rnaC1", 4001, 4003, "+"))
    lines.append(child("stop_codon", "tcC1", "rnaC1", 4298, 4300, "+"))

    lines.append(gene("geneD", 5001, 5150, "+"))
    lines.append(mrna("rnaD1", "geneD", 5001, 5150, "+"))
    lines.append(child("exon", "exonD1", "rnaD1", 5001, 5150, "+"))
    lines.append(child("CDS", "cdsD1", "rnaD1", 5001, 5150, "+", "0"))
    lines.append(child("start_codon", "scD1", "rnaD1", 5001, 5003, "+"))
    lines.append(child("stop_codon", "tcD1", "rnaD1", 5148, 5150, "+"))

    lines.append(gene("geneE", 6001, 6300, "+"))
    lines.append(mrna("rnaE1", "geneE", 6001, 6300, "+"))
    lines.append(child("exon", "exonE1", "rnaE1", 6001, 6300, "+"))
    lines.append(child("CDS", "cdsE1", "rnaE1", 6001, 6300, "+", "0"))
    lines.append(child("start_codon", "scE1", "rnaE1", 6001, 6003, "+"))

    lines.append(gene("geneF", 6901, 7104, "+"))
    lines.append(mrna("rnaF1", "geneF", 6901, 7104, "+"))
    lines.append(child("exon", "exonF1", "rnaF1", 6901, 6950, "+"))
    lines.append(child("exon", "exonF2", "rnaF1", 7005, 7104, "+"))
    lines.append(child("CDS", "cdsF1", "rnaF1", 6901, 6950, "+", "0"))
    lines.append(child("CDS", "cdsF2", "rnaF1", 7005, 7104, "+", "0"))
    lines.append(child("start_codon", "scF1", "rnaF1", 6901, 6903, "+"))
    lines.append(child("stop_codon", "tcF1", "rnaF1", 7102, 7104, "+"))
    return "\n".join(lines) + "\n"


def build_fasta():
    """Build the FASTA for the synthetic chromosome.

    Returns:
        The FASTA text.
    """
    scaffold = build_scaffold()
    wrapped = "\n".join(
        scaffold[index : index + 70] for index in range(0, len(scaffold), 70)
    )
    return f">scaffold1 synthetic fixture chromosome\n{wrapped}\n"


class FixtureTestCase(unittest.TestCase):
    """Base class that writes the fixtures to a temporary directory."""

    @classmethod
    def setUpClass(cls):
        cls._tmp = tempfile.TemporaryDirectory()
        cls.addClassCleanup(cls._tmp.cleanup)
        cls.gff3 = os.path.join(cls._tmp.name, "fixture.gff3")
        cls.fasta = os.path.join(cls._tmp.name, "fixture.fna")
        with open(cls.gff3, "w", encoding="utf-8") as handle:
            handle.write(build_gff3())
        with open(cls.fasta, "w", encoding="utf-8") as handle:
            handle.write(build_fasta())

    def rows(self, fasta=True, min_cds=ld.DEFAULT_MIN_CDS):
        """Run the pipeline on the fixtures and index rows by locus.

        Args:
            fasta: whether to pass the FASTA.
            min_cds: the fragmentation threshold.

        Returns:
            A mapping from locus ID to a dict of column values.
        """
        table = ld.run(
            self.gff3, self.fasta if fasta else None, 10, min_cds
        )
        lines = table.strip().split("\n")
        header = lines[0].split("\t")
        self.assertEqual(header, list(ld.HEADER))
        return {
            dict(zip(header, line.split("\t")))["locus_id"]: dict(
                zip(header, line.split("\t"))
            )
            for line in lines[1:]
        }


class ParseTest(unittest.TestCase):
    """Tests for the GFF3 and FASTA readers."""

    def test_a_line_with_eight_columns_is_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "bad.gff3")
            with open(path, "w", encoding="utf-8") as handle:
                handle.write("seq\tsrc\tgene\t1\t9\t.\t+\t.\n")
            with self.assertRaises(ValueError):
                ld.parse_gff3(path)

    def test_reversed_coordinates_are_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "bad.gff3")
            with open(path, "w", encoding="utf-8") as handle:
                handle.write("seq\tsrc\tgene\t9\t1\t.\t+\t.\tID=g1\n")
            with self.assertRaises(ValueError):
                ld.parse_gff3(path)

    def test_gap_runs_are_found_with_inclusive_coordinates(self):
        self.assertEqual(
            ld.find_gaps("AAC" + "N" * 12 + "GT" + "N" * 12 + "AC", 10),
            [(4, 15), (18, 29)],
        )

    def test_short_n_runs_are_not_gaps(self):
        self.assertEqual(ld.find_gaps("NNNNAACNNNN", 10), [])


class DiagnosticsTest(FixtureTestCase):
    """Tests for the per-locus diagnostics on the fixture chromosome."""

    def test_every_coding_locus_is_reported_once(self):
        self.assertEqual(
            sorted(self.rows()), ["geneA", "geneB", "geneC", "geneD", "geneE", "geneF"]
        )

    def test_a_clean_single_exon_model(self):
        row = self.rows()["geneA"]
        self.assertEqual(row["exon_count"], "1")
        self.assertEqual(row["cds_length"], "600")
        self.assertEqual(row["has_start"], "true")
        self.assertEqual(row["has_stop"], "true")
        self.assertEqual(row["internal_stop"], "false")
        self.assertEqual(row["overlaps_gap"], "false")
        self.assertEqual(row["fragmented"], "false")

    def test_a_clean_minus_strand_multi_exon_model(self):
        # This is the case that breaks when the spliced CDS is not reverse
        # complemented: the first codon of the mRNA sits at the highest
        # genomic coordinates.
        row = self.rows()["geneB"]
        self.assertEqual(row["strand"], "-")
        self.assertEqual(row["exon_count"], "3")
        self.assertEqual(row["cds_length"], "522")
        self.assertEqual(row["has_start"], "true")
        self.assertEqual(row["has_stop"], "true")
        self.assertEqual(row["internal_stop"], "false")
        self.assertEqual(row["fragmented"], "false")

    def test_an_internal_stop_flags_the_model_fragmented(self):
        row = self.rows()["geneC"]
        self.assertEqual(row["cds_length"], "300")
        self.assertEqual(row["internal_stop"], "true")
        self.assertEqual(row["has_stop"], "true")
        self.assertEqual(row["fragmented"], "true")

    def test_a_short_cds_flags_the_model_fragmented(self):
        row = self.rows()["geneD"]
        self.assertEqual(row["cds_length"], "150")
        self.assertEqual(row["internal_stop"], "false")
        self.assertEqual(row["fragmented"], "true")

    def test_a_model_without_a_stop_codon(self):
        row = self.rows()["geneE"]
        self.assertEqual(row["cds_length"], "300")
        self.assertEqual(row["has_start"], "true")
        self.assertEqual(row["has_stop"], "false")
        self.assertEqual(row["internal_stop"], "false")
        # Exactly at the threshold is not below it.
        self.assertEqual(row["fragmented"], "false")

    def test_a_model_overlapping_an_assembly_gap(self):
        row = self.rows()["geneF"]
        self.assertEqual(row["overlaps_gap"], "true")
        for locus in ("geneA", "geneB", "geneC", "geneD", "geneE"):
            self.assertEqual(self.rows()[locus]["overlaps_gap"], "false")

    def test_the_fragmentation_threshold_is_adjustable(self):
        row = self.rows(min_cds=100)["geneD"]
        self.assertEqual(row["fragmented"], "false")

    def test_without_a_fasta_sequence_diagnostics_are_na_not_guessed(self):
        rows = self.rows(fasta=False)
        self.assertEqual(rows["geneC"]["internal_stop"], "NA")
        self.assertEqual(rows["geneC"]["overlaps_gap"], "NA")
        # Explicit codon features still answer start and stop.
        self.assertEqual(rows["geneC"]["has_start"], "true")
        self.assertEqual(rows["geneC"]["has_stop"], "true")
        # Fragmentation rests on length alone in the degraded mode.
        self.assertEqual(rows["geneC"]["fragmented"], "false")
        self.assertEqual(rows["geneD"]["fragmented"], "true")
        # And a stop status that needs the sequence is NA, not a guess.
        self.assertEqual(rows["geneE"]["has_stop"], "NA")

    def test_a_seqid_missing_from_the_fasta_is_an_error(self):
        with tempfile.TemporaryDirectory() as tmp:
            fasta = os.path.join(tmp, "empty.fna")
            with open(fasta, "w", encoding="utf-8") as handle:
                handle.write(">elsewhere\nACGT\n")
            with self.assertRaises(ValueError):
                ld.run(self.gff3, fasta, 10, 300)

    def test_a_child_feature_with_an_unknown_parent_is_an_error(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "orphan.gff3")
            with open(path, "w", encoding="utf-8") as handle:
                handle.write(
                    "scaffold1\tfixture\tCDS\t1\t9\t.\t+\t0\t"
                    "ID=cdsX;Parent=ghost\n"
                )
            with self.assertRaises(ValueError):
                ld.build_loci(ld.parse_gff3(path))

    def test_the_output_is_byte_for_byte_reproducible(self):
        first = ld.run(self.gff3, self.fasta, 10, 300)
        second = ld.run(self.gff3, self.fasta, 10, 300)
        self.assertEqual(first, second)

    def test_the_command_line_entry_point_writes_the_table(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = os.path.join(tmp, "diagnostics.tsv")
            status = ld.main(
                [
                    "--gff3",
                    self.gff3,
                    "--fasta",
                    self.fasta,
                    "--out",
                    out,
                ]
            )
            self.assertEqual(status, 0)
            with open(out, encoding="utf-8") as handle:
                written = handle.read()
            self.assertEqual(written, ld.run(self.gff3, self.fasta, 10, 300))

    def test_the_command_line_entry_point_reports_errors(self):
        status = ld.main(
            ["--gff3", "/nonexistent.gff3", "--out", "-"]
        )
        self.assertEqual(status, 1)


class RepresentativeTest(unittest.TestCase):
    """Tests for the deterministic representative-transcript choice."""

    def test_the_longest_cds_wins_and_ties_break_by_identifier(self):
        base = dict(
            locus_id="g",
            seqid="s",
            start=1,
            end=9,
            strand="+",
            exon_count=1,
            has_start=True,
            has_stop=True,
            internal_stop=False,
            overlaps_gap=False,
            fragmented=False,
        )
        short = ld.Diagnostics(
            transcript_id="rna1", cds_length=300, **base
        )
        long = ld.Diagnostics(
            transcript_id="rna2", cds_length=600, **base
        )
        tied = ld.Diagnostics(
            transcript_id="rna0", cds_length=600, **base
        )
        self.assertEqual(
            ld.choose_representative([("rna1", short), ("rna2", long)])[0], "rna2"
        )
        self.assertEqual(
            ld.choose_representative([("rna2", long), ("rna0", tied)])[0], "rna0"
        )


if __name__ == "__main__":
    unittest.main()
