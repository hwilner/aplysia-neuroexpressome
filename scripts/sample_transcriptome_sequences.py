#!/usr/bin/env python3
"""Sample sequences from the two AplysiaTools transcriptomes and compare
them with the GenBank TSA.

Run it with:

    python3 scripts/sample_transcriptome_sequences.py

P01-03.4. The pre-registration (§3.2, step 1) asks for a random sample of
50 sequences to be compared between the two transcriptome sources, to
confirm that they are the same underlying build.

**All three files are nucleotide.** That was not known when the
pre-registration was written, and it is the reason the comparison can be a
byte comparison at all: `new_unigenes.fasta`, `annotation_1A-2C.fasta` and
`current.annotation.fasta` hold A/C/G/T only, with no amino-acid letters
anywhere in 590 megabases of sequence. There is no protein FASTA at
AplysiaTools.

Three comparisons are made, because they answer three different questions:

**A - the literal one.** Fifty sequences are drawn from the merged-unigene
FASTA and compared, character for character, with the TSA's sequence for the
same transcript. This is the comparison §3.2 step 1 names.

**B - the one the lift-off depends on.** Fifty sequences are drawn from the
CNS set and compared with the TSA's sequence for the same transcript.

**C - the one that separates the two builds.** Fifty sequences are drawn
from the transcripts the CNS set and the merged unigenes have in common,
and the two files are compared with each other. The overlap is small, so
the draw is from the intersection rather than from either file.

The TSA's own FASTA header carries the original assembly name, so the two
identifier namespaces can be joined without the GenBank flatfile. The
flatfile's mapping is read as well and checked against the headers; the two
are independent records of the same thing, and the script stops if they
disagree.

Sampling is deterministic: the identifiers are sorted before the draw, so
the sample does not depend on the order the file happens to be in, and the
seed is the programme-wide one, 20261005. The seed, the sample size and the
identifiers are all written out, so the sample can be reproduced and
audited.

It writes:

    data/derived/sequence_sample.tsv             one row per sampled item
    data/derived/sequence_sample_merged.fasta     the 50 sampled merged-unigene sequences
    data/derived/sequence_sample_cns.fasta        the 50 sampled CNS sequences

The derived files are not committed; the script that makes them is.
"""

import argparse
import gzip
import os
import random
import re
import sys

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RAW = os.path.join(REPO_ROOT, "data", "raw")
DERIVED = os.path.join(REPO_ROOT, "data", "derived")

TSA_FASTA = "tsa.GJYY.1.fsa_nt.gz"
TSA_NAMES = "tsa_transcript_names.tsv"
MERGED_FASTA = "new_unigenes.fasta"
CNS_FASTA = "annotation_1A-2C.fasta"

SAMPLE_OUT = os.path.join(DERIVED, "sequence_sample.tsv")
MERGED_OUT = os.path.join(DERIVED, "sequence_sample_merged.fasta")
CNS_OUT = os.path.join(DERIVED, "sequence_sample_cns.fasta")
EXHAUSTIVE_OUT = os.path.join(DERIVED, "sequence_exhaustive.tsv")
DIFFERENCES_OUT = os.path.join(DERIVED, "sequence_differences.tsv")

# The programme-wide seed. The same value the statistical tests use.
P01_DEFAULT_SEED = 20261005
DEFAULT_SIZE = 50

# The original assembly names, in either of the two forms AplysiaTools uses.
NAME_PATTERN = re.compile(r"(asmbl_\d+|TRINITY_DN\d+_c\d+_g\d+_i\d+)")


def tsa_sequences(fasta_path):
    """Return the TSA's sequence for each original name.

    The FASTA's own header carries the original assembly name:

        >GJYY01000001.1 TSA: Aplysia californica isolate field caught,
        aquaculture reared TRINITY_DN69521_c0_g1_i1, transcribed RNA sequence

    so the mapping between the two identifier namespaces does not need the
    GenBank flatfile.

    Args:
        fasta_path: the path of the TSA FASTA.

    Returns:
        A tuple of (mapping of name to sequence, mapping of name to
        accession).
    """
    sequences = {}
    accessions = {}
    opener = gzip.open if fasta_path.endswith(".gz") else open
    name = None
    chunks = []
    with opener(fasta_path, "rt", encoding="utf-8", errors="replace") as handle:
        for line in handle:
            if line.startswith(">"):
                if name is not None:
                    sequences[name] = "".join(chunks)
                fields = line[1:].split()
                match = NAME_PATTERN.search(line)
                name = match.group(1) if match else None
                if name is not None and fields:
                    accessions[name] = fields[0].split(".")[0]
                chunks = []
            elif name is not None:
                chunks.append(line.strip())
    if name is not None:
        sequences[name] = "".join(chunks)
    return sequences, accessions


def flatfile_names(names_path):
    """Return the accession-to-name mapping of the GenBank flatfile.

    Args:
        names_path: the path of the mapping.

    Returns:
        The mapping of accession to name.
    """
    mapping = {}
    with open(names_path, encoding="utf-8") as handle:
        next(handle, None)
        for line in handle:
            parts = line.rstrip("\n").split("\t")
            if len(parts) >= 2:
                mapping[parts[0]] = parts[1]
    return mapping


def check_names(accessions, bridge):
    """Check the FASTA's headers against the flatfile's mapping.

    Args:
        accessions: the mapping of name to accession, from the FASTA.
        bridge: the mapping of accession to name, from the flatfile.

    Returns:
        The number of names the two sources agree about.

    Raises:
        RuntimeError: if they disagree about any name.
    """
    disagreements = [
        (accession, name, bridge.get(accession))
        for name, accession in accessions.items()
        if bridge.get(accession) != name
    ]
    if disagreements:
        raise RuntimeError(
            f"the FASTA header and the flatfile mapping disagree about "
            f"{len(disagreements)} names, the first is {disagreements[0]}"
        )
    return len(accessions)


def fasta_ids(path):
    """Return the identifiers of a FASTA file, in file order.

    Args:
        path: the path of the FASTA file.

    Returns:
        The identifiers.
    """
    ids = []
    opener = gzip.open if path.endswith(".gz") else open
    with opener(path, "rt", encoding="utf-8", errors="replace") as handle:
        for line in handle:
            if line.startswith(">"):
                fields = line[1:].split()
                if fields:
                    ids.append(fields[0])
    return ids


def fasta_sequences(path, wanted):
    """Return the sequences of a FASTA file for a set of identifiers.

    Args:
        path: the path of the FASTA file.
        wanted: the identifiers to keep.

    Returns:
        The mapping of identifier to sequence, for those that are present.
    """
    found = {}
    opener = gzip.open if path.endswith(".gz") else open
    current = None
    chunks = []
    with opener(path, "rt", encoding="utf-8", errors="replace") as handle:
        for line in handle:
            if line.startswith(">"):
                if current is not None and current in wanted:
                    found[current] = "".join(chunks)
                fields = line[1:].split()
                current = fields[0] if fields else None
                chunks = []
            elif current is not None and current in wanted:
                chunks.append(line.strip())
    if current is not None and current in wanted:
        found[current] = "".join(chunks)
    return found


def stream_fasta(path):
    """Yield the identifier and the sequence of every record of a FASTA file.

    Args:
        path: the path of the FASTA file.

    Yields:
        Pairs of identifier and sequence.
    """
    opener = gzip.open if path.endswith(".gz") else open
    current = None
    chunks = []
    with opener(path, "rt", encoding="utf-8", errors="replace") as handle:
        for line in handle:
            if line.startswith(">"):
                if current is not None:
                    yield current, "".join(chunks)
                fields = line[1:].split()
                current = fields[0] if fields else None
                chunks = []
            elif current is not None:
                chunks.append(line.strip())
    if current is not None:
        yield current, "".join(chunks)


def exhaustive_count(label, path, other):
    """Compare every record of a FASTA file with a mapping of sequences.

    Args:
        label: what the comparison is.
        path: the path of the FASTA file.
        other: the mapping of identifier to sequence to compare against.

    Returns:
        A row of counts.
    """
    identical = 0
    differ = 0
    absent = 0
    for identifier, sequence in stream_fasta(path):
        if identifier not in other:
            absent += 1
        elif other[identifier] == sequence:
            identical += 1
        else:
            differ += 1
    return [label, identical, differ, absent, identical + differ + absent]


def characterise_difference(first, second):
    """Describe how two versions of one transcript differ.

    Args:
        first: the first sequence.
        second: the second sequence.

    Returns:
        A tuple of (common prefix length, common suffix length, verdict).
    """
    prefix = 0
    for a, b in zip(first, second):
        if a != b:
            break
        prefix += 1
    suffix = 0
    for a, b in zip(reversed(first), reversed(second)):
        if a != b:
            break
        suffix += 1
    if second.startswith(first):
        verdict = f"the TSA copy is the CNS copy minus {len(first) - len(second)} nt at the 3' end"
    elif first.startswith(second):
        verdict = f"the CNS copy is the TSA copy plus {len(first) - len(second)} nt at the 3' end"
    elif second.endswith(first):
        verdict = f"the CNS copy is the TSA copy plus {len(first) - len(second)} nt at the 5' end"
    elif first.endswith(second):
        verdict = f"the TSA copy is the CNS copy minus {len(first) - len(second)} nt at the 5' end"
    else:
        verdict = "neither sequence contains the other"
    return prefix, suffix, verdict


def write_fasta(path, records):
    """Write a FASTA file.

    Args:
        path: where to write it.
        records: the pairs of identifier and sequence, in order.
    """
    with open(path, "w", encoding="utf-8", newline="") as handle:
        for identifier, sequence in records:
            handle.write(f">{identifier}\n")
            for start in range(0, len(sequence), 60):
                handle.write(sequence[start : start + 60] + "\n")


def compare(first, second):
    """Compare two nucleotide sequences.

    Args:
        first: the first sequence.
        second: the second sequence.

    Returns:
        A tuple of (verdict, detail).
    """
    if second is None:
        return "absent", "the other file has no record with this name"
    if first == second:
        return "identical", f"{len(first)} nt, character for character"
    if len(first) == len(second):
        return "differs", f"both {len(first)} nt, but not the same sequence"
    return "differs", (
        f"{len(first)} nt against {len(second)} nt, "
        f"{'the other is shorter' if len(second) < len(first) else 'the other is longer'}"
    )


def main(argv=None):
    """Run the sampling and the comparisons.

    Args:
        argv: the command-line arguments.

    Returns:
        The exit code.
    """
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--size", type=int, default=DEFAULT_SIZE, help="sample size")
    parser.add_argument("--seed", type=int, default=P01_DEFAULT_SEED, help="the seed")
    args = parser.parse_args(argv)

    paths = {
        "TSA FASTA": os.path.join(RAW, TSA_FASTA),
        "TSA names": os.path.join(DERIVED, TSA_NAMES),
        "merged unigenes": os.path.join(RAW, MERGED_FASTA),
        "CNS set": os.path.join(RAW, CNS_FASTA),
    }
    missing = [name for name, path in paths.items() if not os.path.exists(path)]
    if missing:
        for name in missing:
            print(f"error: {name} is missing.", file=sys.stderr)
        print(
            "    run scripts/fetch_transcriptomes.sh and "
            "scripts/extract_tsa_names.py first.",
            file=sys.stderr,
        )
        return 1

    os.makedirs(DERIVED, exist_ok=True)

    tsa, tsa_accessions = tsa_sequences(paths["TSA FASTA"])
    bridge = flatfile_names(paths["TSA names"])
    agreed = check_names(tsa_accessions, bridge)
    print(
        f"the TSA's own headers and the flatfile mapping agree about all "
        f"{agreed:,} names"
    )

    merged_ids = sorted(fasta_ids(paths["merged unigenes"]))
    cns_ids = sorted(fasta_ids(paths["CNS set"]))
    shared = sorted(set(merged_ids) & set(cns_ids))

    generator = random.Random(args.seed)
    size = min(args.size, len(merged_ids), len(cns_ids), len(shared))
    merged_sample = generator.sample(merged_ids, size)
    cns_sample = generator.sample(cns_ids, size)
    shared_sample = generator.sample(shared, size)

    merged_sequences = fasta_sequences(paths["merged unigenes"], set(merged_sample))
    cns_sequences = fasta_sequences(paths["CNS set"], set(cns_sample))
    shared_merged = fasta_sequences(paths["merged unigenes"], set(shared_sample))
    shared_cns = fasta_sequences(paths["CNS set"], set(shared_sample))

    rows = []
    tally = {}

    def record(comparison, identifier, verdict, detail):
        """Add one row and count it.

        Args:
            comparison: which comparison the row belongs to.
            identifier: the transcript.
            verdict: the outcome.
            detail: the detail.
        """
        rows.append([comparison, identifier, verdict, detail])
        key = (comparison, verdict)
        tally[key] = tally.get(key, 0) + 1

    # --- A: the merged unigenes against the TSA
    for identifier in merged_sample:
        verdict, detail = compare(
            merged_sequences.get(identifier, ""), tsa.get(identifier)
        )
        record("A merged_unigenes_vs_tsa", identifier, verdict, detail)

    # --- B: the CNS set against the TSA
    for identifier in cns_sample:
        verdict, detail = compare(cns_sequences.get(identifier, ""), tsa.get(identifier))
        record("B cns_set_vs_tsa", identifier, verdict, detail)

    # --- C: the CNS set against the merged unigenes, over their intersection
    for identifier in shared_sample:
        verdict, detail = compare(
            shared_cns.get(identifier, ""), shared_merged.get(identifier)
        )
        record("C cns_set_vs_merged_unigenes", identifier, verdict, detail)

    with open(SAMPLE_OUT, "w", encoding="utf-8", newline="") as handle:
        handle.write("comparison\tidentifier\tverdict\tdetail\n")
        for row in rows:
            handle.write("\t".join(row) + "\n")

    write_fasta(
        MERGED_OUT,
        [(i, merged_sequences.get(i, "")) for i in merged_sample],
    )
    write_fasta(CNS_OUT, [(i, cns_sequences.get(i, "")) for i in cns_sample])

    # --- the exhaustive check, over every shared transcript
    #
    # The sample answers the pre-registered question. The same comparison
    # over every shared transcript is cheap, because the sequences are
    # already in hand, and it turns "50 of 50 agreed" into a statement
    # about the whole set rather than about a sample of it.
    exhaustive = [
        exhaustive_count("CNS set against the TSA", paths["CNS set"], tsa),
        exhaustive_count(
            "merged unigenes against the TSA", paths["merged unigenes"], tsa
        ),
    ]
    # the transcripts that differ, and how
    differences = []
    for identifier, sequence in stream_fasta(paths["CNS set"]):
        other = tsa.get(identifier)
        if other is not None and other != sequence:
            prefix, suffix, verdict = characterise_difference(sequence, other)
            differences.append(
                [
                    identifier,
                    len(sequence),
                    len(other),
                    len(sequence) - len(other),
                    prefix,
                    suffix,
                    verdict,
                ]
            )
    with open(DIFFERENCES_OUT, "w", encoding="utf-8", newline="") as handle:
        handle.write(
            "identifier\tcns_nt\ttsa_nt\tdifference_nt\tcommon_prefix\t"
            "common_suffix\tverdict\n"
        )
        for row in differences:
            handle.write("\t".join(str(field) for field in row) + "\n")

    merged_all = dict(stream_fasta(paths["merged unigenes"]))
    exhaustive.append(
        exhaustive_count(
            "CNS set against the merged unigenes", paths["CNS set"], merged_all
        )
    )
    del merged_all

    with open(EXHAUSTIVE_OUT, "w", encoding="utf-8", newline="") as handle:
        handle.write("comparison\tidentical\tdiffer\tnot_in_the_other\tcompared\n")
        for row in exhaustive:
            handle.write("\t".join(str(field) for field in row) + "\n")

    print(f"seed {args.seed}, sample size {size}")
    print()
    for comparison, title in (
        ("A merged_unigenes_vs_tsa", "A - the merged unigenes against the TSA"),
        ("B cns_set_vs_tsa", "B - the CNS set against the TSA"),
        ("C cns_set_vs_merged_unigenes", "C - the CNS set against the merged unigenes"),
    ):
        print(title)
        verdicts = [
            (verdict, count)
            for (name, verdict), count in sorted(tally.items())
            if name == comparison
        ]
        for verdict, count in verdicts:
            print(f"  {verdict:<20} {count:>4} of {size}")
    print()
    print("every shared transcript, compared exhaustively")
    for row in exhaustive:
        print(
            f"  {row[0]:<36} identical {row[1]:>7,}   differ {row[2]:>6,}   "
            f"not in the other {row[3]:>7,}"
        )
    print()
    print(f"the {len(differences)} shared transcripts that differ, and how")
    for row in differences:
        print(f"  {row[0]:<26} {row[3]:>+5} nt   {row[6]}")
    print()
    print(f"wrote {SAMPLE_OUT}")
    print(f"wrote {EXHAUSTIVE_OUT}")
    print(f"wrote {DIFFERENCES_OUT}")
    print(f"wrote {MERGED_OUT}")
    print(f"wrote {CNS_OUT}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
