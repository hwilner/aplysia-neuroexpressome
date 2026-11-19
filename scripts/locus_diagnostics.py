#!/usr/bin/env python3
"""Compute per-locus gene-model diagnostics from an annotation and an assembly.

This is the stage-1 diagnostic step pre-registered in
`materials-and-methods.md` section 3.1, step 3: parse the GFF and compute,
per locus, the number of exons, the total CDS length, whether the model has
a start and a stop codon, whether the model overlaps a gap in the assembly,
and a fragmentation flag for models shorter than 300 nt of CDS or containing
internal stops. The output is the per-locus table that the paired
before/after comparison (tests T2 and T3 in section 5.2) is built from once
the repaired annotation exists; the pairing itself is a later step, because
there is no repaired set to pair against yet.

Design decisions, made here rather than at analysis time:

- One row per locus. Where a locus has several transcripts, the
  representative is the transcript with the greatest total CDS length, with
  ties broken by the lexicographically smallest transcript ID, so the choice
  is deterministic and cannot be tuned after the fact.
- Only coding models are reported. Exon count, CDS length, start/stop and
  internal-stop are properties of a coding model, so loci with no CDS
  feature are skipped rather than emitted with empty columns.
- Start and stop are taken from explicit `start_codon`/`stop_codon`
  features when the GFF carries them (RefSeq GFF3 does), and inferred from
  the assembly sequence when it does not: a model has a start if its
  spliced CDS begins with ATG, and a stop if its last complete codon is one
  of TAA, TAG, TGA. A trailing partial codon is ignored.
- An internal stop is any stop codon among the complete codons of the
  spliced CDS, excluding a terminal stop. Translation uses the standard
  genetic code; the mitochondrion (NC_005827.1) uses code 5 and must be
  excluded or re-evaluated before any statement about mitochondrial loci.
  Nothing in P01's channel catalogue is mitochondrial.
- An assembly gap is a run of at least `--min-gap` N bases (default 10).
  A model overlaps a gap if any of its exon intervals does (CDS intervals
  if the GFF carries no exon features).
- `--fasta` is optional. Without it the sequence-based diagnostics
  (inferred start/stop, internal stop, gap overlap) are reported as `NA`
  rather than guessed, and the fragmentation flag rests on CDS length
  alone. A number that cannot be computed is marked, not estimated.

Usage:
    scripts/locus_diagnostics.py --gff3 annotation.gff3 --fasta genome.fna --out diagnostics.tsv
    scripts/locus_diagnostics.py --gff3 annotation.gff3 --out diagnostics.tsv
"""

import argparse
import sys
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple
from urllib.parse import unquote

TRANSCRIPT_TYPES = frozenset({"mRNA", "transcript"})
CHILD_TYPES = frozenset({"exon", "CDS", "start_codon", "stop_codon"})
STOP_CODONS = frozenset({"TAA", "TAG", "TGA"})

DEFAULT_MIN_GAP = 10
DEFAULT_MIN_CDS = 300

HEADER = (
    "locus_id",
    "transcript_id",
    "seqid",
    "start",
    "end",
    "strand",
    "exon_count",
    "cds_length",
    "has_start",
    "has_stop",
    "internal_stop",
    "overlaps_gap",
    "fragmented",
)


@dataclass
class Feature:
    """One line of a GFF3 file.

    Attributes:
        seqid: the sequence the feature sits on.
        type: the feature type (column 3).
        start: the 1-based inclusive start coordinate.
        end: the 1-based inclusive end coordinate.
        strand: "+", "-" or ".".
        attributes: the parsed column-9 attributes.
    """

    seqid: str
    type: str
    start: int
    end: int
    strand: str
    attributes: Dict[str, str]


@dataclass
class TranscriptModel:
    """A transcript and its child features.

    Attributes:
        feature: the transcript feature itself.
        exons: its exon features.
        cds: its CDS features.
        start_codons: its start_codon features.
        stop_codons: its stop_codon features.
    """

    feature: Feature
    exons: List[Feature] = field(default_factory=list)
    cds: List[Feature] = field(default_factory=list)
    start_codons: List[Feature] = field(default_factory=list)
    stop_codons: List[Feature] = field(default_factory=list)


@dataclass
class Diagnostics:
    """The pre-registered per-locus diagnostics, as one output row.

    Attributes:
        locus_id: the gene identifier.
        transcript_id: the representative transcript's identifier.
        seqid: the sequence the locus sits on.
        start: the 1-based inclusive start of the representative transcript.
        end: the 1-based inclusive end of the representative transcript.
        strand: "+", "-" or ".".
        exon_count: the number of exons (CDS segments if the GFF has no
            exon features).
        cds_length: the summed length of the CDS segments, in nucleotides.
        has_start: whether the model has a start codon; None if not
            assessable (no feature and no sequence).
        has_stop: whether the model has a stop codon; None if not
            assessable.
        internal_stop: whether the spliced CDS contains a stop codon
            before its terminus; None if no sequence was given.
        overlaps_gap: whether the model overlaps an assembly gap; None if
            no sequence was given.
        fragmented: the pre-registered fragmentation flag: CDS shorter
            than the threshold, or an internal stop.
    """

    locus_id: str
    transcript_id: str
    seqid: str
    start: int
    end: int
    strand: str
    exon_count: int
    cds_length: int
    has_start: Optional[bool]
    has_stop: Optional[bool]
    internal_stop: Optional[bool]
    overlaps_gap: Optional[bool]
    fragmented: bool


def parse_gff3(path: str) -> List[Feature]:
    """Parse a GFF3 file into features.

    Args:
        path: the GFF3 file.

    Returns:
        The features, in file order. Directives (lines starting with #)
        are skipped.

    Raises:
        ValueError: if a data line does not have nine tab-separated
            columns, or its coordinates are not valid 1-based inclusive
            positions.
    """
    features = []
    with open(path, encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, start=1):
            line = line.rstrip("\n")
            if not line or line.startswith("#"):
                continue
            columns = line.split("\t")
            if len(columns) != 9:
                raise ValueError(
                    f"{path} line {line_number}: expected 9 tab-separated "
                    f"columns, found {len(columns)}"
                )
            try:
                start = int(columns[3])
                end = int(columns[4])
            except ValueError:
                raise ValueError(
                    f"{path} line {line_number}: start and end must be "
                    f"integers, found {columns[3]!r} and {columns[4]!r}"
                ) from None
            if start < 1 or end < start:
                raise ValueError(
                    f"{path} line {line_number}: invalid coordinates "
                    f"{start}..{end}"
                )
            attributes = {}
            if columns[8] != ".":
                for item in columns[8].split(";"):
                    if not item:
                        continue
                    if "=" not in item:
                        raise ValueError(
                            f"{path} line {line_number}: attribute {item!r} "
                            f"is not a key=value pair"
                        )
                    key, _, value = item.partition("=")
                    attributes[key] = unquote(value)
            features.append(
                Feature(
                    seqid=columns[0],
                    type=columns[2],
                    start=start,
                    end=end,
                    strand=columns[6],
                    attributes=attributes,
                )
            )
    return features


def read_fasta(path: str) -> Dict[str, str]:
    """Read a FASTA file into a dictionary of upper-case sequences.

    Args:
        path: the FASTA file. The record identifier is the first
            whitespace-delimited token of the header.

    Returns:
        A mapping from record identifier to sequence.

    Raises:
        ValueError: if sequence appears before any header.
    """
    sequences: Dict[str, List[str]] = {}
    current: Optional[str] = None
    with open(path, encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, start=1):
            line = line.strip()
            if not line:
                continue
            if line.startswith(">"):
                current = line[1:].split()[0]
                sequences[current] = []
            else:
                if current is None:
                    raise ValueError(
                        f"{path} line {line_number}: sequence before any header"
                    )
                sequences[current].append(line.upper())
    return {name: "".join(parts) for name, parts in sequences.items()}


def reverse_complement(sequence: str) -> str:
    """Return the reverse complement of a nucleotide sequence.

    Args:
        sequence: the sequence, upper case. Bases other than ACGT (gaps,
            ambiguity codes) complement to themselves.

    Returns:
        The reverse complement.
    """
    table = str.maketrans("ACGT", "TGCA")
    return sequence.translate(table)[::-1]


def find_gaps(sequence: str, min_length: int) -> List[Tuple[int, int]]:
    """Find assembly gaps: runs of N of at least a given length.

    Args:
        sequence: the sequence, upper case.
        min_length: the shortest run of N that counts as a gap.

    Returns:
        The gap intervals as 1-based inclusive (start, end) pairs, in
        coordinate order.
    """
    gaps = []
    run_start: Optional[int] = None
    for index, base in enumerate(sequence):
        if base == "N":
            if run_start is None:
                run_start = index
        elif run_start is not None:
            if index - run_start >= min_length:
                gaps.append((run_start + 1, index))
            run_start = None
    if run_start is not None and len(sequence) - run_start >= min_length:
        gaps.append((run_start + 1, len(sequence)))
    return gaps


def build_loci(features: List[Feature]) -> List[Tuple[str, List[TranscriptModel]]]:
    """Group gene-model features into loci of transcript models.

    Args:
        features: the parsed GFF3 features.

    Returns:
        A list of (locus_id, transcript models) pairs in file order of
        first appearance. Child features parented directly to a gene are
        grouped under a pseudo-transcript named after the gene; exon,
        CDS and codon features attach to their parent transcript.

    Raises:
        ValueError: if a child feature's parent is neither a transcript
            nor a gene in the same file, or a transcript's parent gene is
            missing.
    """
    genes: Dict[str, Feature] = {}
    transcripts: Dict[str, Feature] = {}
    children: Dict[str, List[Feature]] = {}
    order: List[str] = []
    for feature in features:
        if feature.type == "gene":
            identifier = feature.attributes.get("ID")
            if identifier:
                genes[identifier] = feature
                if identifier not in order:
                    order.append(identifier)
        elif feature.type in TRANSCRIPT_TYPES:
            identifier = feature.attributes.get("ID")
            if identifier:
                transcripts[identifier] = feature
        elif feature.type in CHILD_TYPES:
            for parent in feature.attributes.get("Parent", "").split(","):
                parent = parent.strip()
                if parent:
                    children.setdefault(parent, []).append(feature)

    loci: Dict[str, Dict[str, TranscriptModel]] = {}
    for identifier, feature in transcripts.items():
        parents = [
            parent.strip()
            for parent in feature.attributes.get("Parent", "").split(",")
            if parent.strip()
        ]
        if not parents or parents[0] not in genes:
            raise ValueError(
                f"transcript {identifier!r} has no parent gene in the file"
            )
        locus = parents[0]
        loci.setdefault(locus, {})[identifier] = TranscriptModel(feature=feature)
        if locus not in order:
            order.append(locus)

    for parent, child_features in children.items():
        if parent in transcripts:
            target = None
            for locus_models in loci.values():
                if parent in locus_models:
                    target = locus_models[parent]
                    break
        elif parent in genes:
            models = loci.setdefault(parent, {})
            if parent not in models:
                models[parent] = TranscriptModel(feature=genes[parent])
            target = models[parent]
        else:
            raise ValueError(
                f"{child_features[0].type} feature has parent {parent!r}, "
                f"which is neither a transcript nor a gene in the file"
            )
        for child in child_features:
            if child.type == "exon":
                target.exons.append(child)
            elif child.type == "CDS":
                target.cds.append(child)
            elif child.type == "start_codon":
                target.start_codons.append(child)
            elif child.type == "stop_codon":
                target.stop_codons.append(child)
    return [(locus, list(models.values())) for locus, models in
            ((name, loci[name]) for name in order if name in loci)]


def spliced_cds_sequence(model: TranscriptModel, sequence: str) -> str:
    """Extract the spliced CDS sequence of a transcript, 5' to 3'.

    Args:
        model: the transcript model.
        sequence: the sequence of the seqid the model sits on.

    Returns:
        The concatenated CDS sequence in transcription order, reverse
        complemented for minus-strand models. RefSeq phase conventions
        make the concatenation start in frame.
    """
    segments = sorted(model.cds, key=lambda cds: cds.start)
    if model.feature.strand == "-":
        segments = list(reversed(segments))
    joined = "".join(sequence[cds.start - 1 : cds.end] for cds in segments)
    if model.feature.strand == "-":
        return reverse_complement(joined)
    return joined


def complete_codons(sequence: str) -> List[str]:
    """Split a coding sequence into its complete codons.

    Args:
        sequence: the coding sequence. A trailing partial codon is
            dropped.

    Returns:
        The complete codons, in order.
    """
    return [
        sequence[index : index + 3]
        for index in range(0, len(sequence) - len(sequence) % 3, 3)
    ]


def has_internal_stop(coding: str) -> bool:
    """Return whether a spliced CDS contains a stop before its terminus.

    Args:
        coding: the spliced CDS sequence, 5' to 3'. Codons containing
            ambiguity codes are not stops by definition.

    Returns:
        True if any complete codon other than a terminal one is a stop
        codon.
    """
    codons = complete_codons(coding)
    if codons and codons[-1] in STOP_CODONS:
        codons = codons[:-1]
    return any(codon in STOP_CODONS for codon in codons)


def overlaps(
    intervals: List[Tuple[int, int]], others: List[Tuple[int, int]]
) -> bool:
    """Return whether any interval overlaps any of the others.

    Args:
        intervals: 1-based inclusive (start, end) pairs.
        others: 1-based inclusive (start, end) pairs.

    Returns:
        True if any pair shares at least one position.
    """
    return any(
        start <= other_end and other_start <= end
        for start, end in intervals
        for other_start, other_end in others
    )


def diagnose_transcript(
    locus_id: str,
    transcript_id: str,
    model: TranscriptModel,
    sequences: Optional[Dict[str, str]],
    gaps: Dict[str, List[Tuple[int, int]]],
    min_cds: int,
) -> Diagnostics:
    """Compute the pre-registered diagnostics for one transcript.

    Args:
        locus_id: the gene the transcript belongs to.
        transcript_id: the transcript identifier.
        model: the transcript model.
        sequences: the assembly sequences, or None if no FASTA was given.
        gaps: the assembly gaps per seqid, from `find_gaps`.
        min_cds: the CDS length below which a model is fragmented.

    Returns:
        The diagnostics row.

    Raises:
        ValueError: if the transcript has no CDS, or its seqid is missing
            from the FASTA.
    """
    if not model.cds:
        raise ValueError(f"transcript {transcript_id!r} has no CDS features")
    feature = model.feature
    cds_length = sum(cds.end - cds.start + 1 for cds in model.cds)
    exon_count = len(model.exons) if model.exons else len(model.cds)

    has_start: Optional[bool] = None
    has_stop: Optional[bool] = None
    internal_stop: Optional[bool] = None
    overlaps_gap: Optional[bool] = None

    if model.start_codons:
        has_start = True
    if model.stop_codons:
        has_stop = True

    if sequences is not None:
        if feature.seqid not in sequences:
            raise ValueError(
                f"seqid {feature.seqid!r} of transcript {transcript_id!r} "
                f"is not in the FASTA"
            )
        coding = spliced_cds_sequence(model, sequences[feature.seqid])
        codons = complete_codons(coding)
        if has_start is None:
            has_start = coding[:3] == "ATG"
        if has_stop is None:
            has_stop = bool(codons) and codons[-1] in STOP_CODONS
        internal_stop = has_internal_stop(coding)
        intervals = [
            (exon.start, exon.end) for exon in (model.exons or model.cds)
        ]
        overlaps_gap = overlaps(intervals, gaps.get(feature.seqid, []))

    return Diagnostics(
        locus_id=locus_id,
        transcript_id=transcript_id,
        seqid=feature.seqid,
        start=feature.start,
        end=feature.end,
        strand=feature.strand,
        exon_count=exon_count,
        cds_length=cds_length,
        has_start=has_start,
        has_stop=has_stop,
        internal_stop=internal_stop,
        overlaps_gap=overlaps_gap,
        fragmented=cds_length < min_cds or internal_stop is True,
    )


def choose_representative(
    rows: List[Tuple[str, Diagnostics]]
) -> Tuple[str, Diagnostics]:
    """Choose the representative transcript of a locus.

    The representative is the transcript with the greatest total CDS
    length, ties broken by the smallest transcript ID, so the choice is
    deterministic and fixed before any result exists.

    Args:
        rows: (transcript_id, diagnostics) pairs for one locus.

    Returns:
        The representative pair.
    """
    return sorted(rows, key=lambda row: (-row[1].cds_length, row[0]))[0]


def render_cell(value: Optional[bool]) -> str:
    """Render an optional boolean as a TSV cell.

    Args:
        value: the value.

    Returns:
        "true", "false", or "NA" when the value could not be assessed.
    """
    if value is None:
        return "NA"
    return "true" if value else "false"


def render_table(rows: List[Diagnostics]) -> str:
    """Render diagnostics rows as a TSV table.

    Args:
        rows: the rows.

    Returns:
        The table, one header line then one line per row, ordered by
        seqid, start, end and transcript ID so the output is byte-for-byte
        reproducible.
    """
    lines = ["\t".join(HEADER)]
    for row in sorted(
        rows, key=lambda row: (row.seqid, row.start, row.end, row.transcript_id)
    ):
        lines.append(
            "\t".join(
                [
                    row.locus_id,
                    row.transcript_id,
                    row.seqid,
                    str(row.start),
                    str(row.end),
                    row.strand,
                    str(row.exon_count),
                    str(row.cds_length),
                    render_cell(row.has_start),
                    render_cell(row.has_stop),
                    render_cell(row.internal_stop),
                    render_cell(row.overlaps_gap),
                    "true" if row.fragmented else "false",
                ]
            )
        )
    return "\n".join(lines) + "\n"


def run(
    gff3_path: str,
    fasta_path: Optional[str],
    min_gap: int,
    min_cds: int,
) -> str:
    """Compute the per-locus diagnostics table.

    Args:
        gff3_path: the annotation GFF3.
        fasta_path: the assembly FASTA, or None for structure-only
            diagnostics.
        min_gap: the shortest N-run that counts as an assembly gap.
        min_cds: the CDS length below which a model is fragmented.

    Returns:
        The TSV table.
    """
    sequences = read_fasta(fasta_path) if fasta_path else None
    gaps = (
        {name: find_gaps(sequence, min_gap) for name, sequence in sequences.items()}
        if sequences is not None
        else {}
    )
    features = parse_gff3(gff3_path)
    rows = []
    for locus_id, models in build_loci(features):
        coding = []
        for model in models:
            if not model.cds:
                continue
            transcript_id = model.feature.attributes.get(
                "ID", model.feature.attributes.get("Name", locus_id)
            )
            coding.append(
                (
                    transcript_id,
                    diagnose_transcript(
                        locus_id, transcript_id, model, sequences, gaps, min_cds
                    ),
                )
            )
        if coding:
            rows.append(choose_representative(coding)[1])
    return render_table(rows)


def main(argv: List[str]) -> int:
    """Compute per-locus diagnostics and write the TSV table.

    Args:
        argv: the command-line arguments.

    Returns:
        The process exit status.
    """
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--gff3", required=True, help="the annotation GFF3")
    parser.add_argument(
        "--fasta",
        default=None,
        help="the assembly FASTA; without it, sequence-based diagnostics "
        "are reported as NA",
    )
    parser.add_argument(
        "--out",
        required=True,
        help="the output TSV, or - for standard output",
    )
    parser.add_argument(
        "--min-gap",
        type=int,
        default=DEFAULT_MIN_GAP,
        help=f"the shortest N-run that counts as a gap "
        f"(default {DEFAULT_MIN_GAP})",
    )
    parser.add_argument(
        "--min-cds",
        type=int,
        default=DEFAULT_MIN_CDS,
        help=f"the CDS length below which a model is fragmented "
        f"(default {DEFAULT_MIN_CDS})",
    )
    args = parser.parse_args(argv)

    try:
        table = run(args.gff3, args.fasta, args.min_gap, args.min_cds)
    except (ValueError, OSError) as error:
        print(f"error: {error}", file=sys.stderr)
        return 1

    if args.out == "-":
        sys.stdout.write(table)
    else:
        with open(args.out, "w", encoding="utf-8") as handle:
            handle.write(table)
        print(f"wrote {args.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
