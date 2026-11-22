#!/usr/bin/env python3
"""Compare the record counts of the two transcriptome sources.

Run it with:

    python3 scripts/compare_transcriptome_counts.py

P01-03.3. The pre-registration (§3.2, step 1) asks for the merged-unigene
FASTA and the predicted protein set from AplysiaTools, the Orvis 2022
assembly from GenBank, and then for the two to be confirmed as "the same
underlying build" by comparing sequence counts and a random sample of 50
sequences.

This script does the counting half. It does not assume that the counts
agree: it computes each count from the file it belongs to, says what each
count is a count OF, and puts the counts side by side so that the
agreement, or the absence of it, is visible.

The two identifier namespaces are the first trap. AplysiaTools writes
tissue-prefixed identifiers in `current.annotation.fasta` and in the
per-tissue files -- `salivary.asmbl_100`, `CNS.asmbl_340921` -- while the
merged-unigene FASTA and the GenBank TSA use the bare ones: `asmbl_100`,
`TRINITY_DN69529_c0_g1_i1`. Compared without removing the prefix, the
per-tissue sets look disjoint from each other. They are not: 15,926
unigenes occur in more than one tissue.

It writes:

    data/derived/transcriptome_counts.tsv     one row per source
    data/derived/transcriptome_overlaps.tsv   one row per pair of sources

The derived files are not committed; the script that makes them is.
"""

import argparse
import gzip
import json
import os
import sys

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RAW = os.path.join(REPO_ROOT, "data", "raw")
DERIVED = os.path.join(REPO_ROOT, "data", "derived")

TSA_FASTA = "tsa.GJYY.1.fsa_nt.gz"
TSA_NAMES = "tsa_transcript_names.tsv"
MERGED_FASTA = "new_unigenes.fasta"
PROTEIN_FASTA = "annotation_1A-2C.fasta"
CURRENT_FASTA = "current.annotation.fasta"
TRINOTATE_JSON = "merged.unigenes.trinotate.longest_orf.json"
TISSUE_IDS = "tissue_unigene_ids.tsv"

# The per-tissue files, and the tissue each one holds.
FILE_TEMPLATE = "{code}.transrate.good.longestorfs.p1.cdhitest.unigenes.fasta"

COUNTS_OUT = os.path.join(DERIVED, "transcriptome_counts.tsv")
OVERLAPS_OUT = os.path.join(DERIVED, "transcriptome_overlaps.tsv")

# The counts the Orvis 2022 paper publishes, so that the comparison is
# against the source's own numbers rather than against ours.
PAPER_COUNTS = {
    "clusters": 71104,
    "unigenes": 68308,
    "unigenes_ge_400bp_orf": 39486,
    "transcripts_ge_400bp_orf": 38125,
}


def fasta_ids(path):
    """Return the identifiers of a FASTA file, in file order.

    Args:
        path: the path of the FASTA file. A `.gz` path is read through
            gzip.

    Returns:
        The identifiers, without their descriptions.
    """
    ids = []
    opener = gzip.open if path.endswith(".gz") else open
    with opener(path, "rt", encoding="utf-8", errors="replace") as handle:
        for line in handle:
            if line.startswith(">"):
                fields = line[1:].split()
                ids.append(fields[0] if fields else "")
    return ids


def bare(identifier):
    """Return an identifier without its tissue prefix.

    `salivary.asmbl_100` becomes `asmbl_100`; an identifier that carries
    no prefix is returned unchanged.

    Args:
        identifier: the identifier.

    Returns:
        The unprefixed identifier.
    """
    return identifier.split(".", 1)[1] if "." in identifier else identifier


def tissue_of(identifier):
    """Return the tissue prefix of an identifier, or the empty string.

    Args:
        identifier: the identifier.

    Returns:
        The prefix.
    """
    return identifier.split(".", 1)[0] if "." in identifier else ""


def tsa_names(path):
    """Return the original names of the TSA records.

    Args:
        path: the path of the accession-to-name mapping.

    Returns:
        The set of original names.
    """
    names = set()
    with open(path, encoding="utf-8") as handle:
        next(handle, None)
        for line in handle:
            parts = line.rstrip("\n").split("\t")
            if len(parts) >= 2:
                names.add(parts[1])
    return names


def trinotate_ids(path):
    """Return the identifiers the Trinotate JSON annotates.

    Args:
        path: the path of the JSON.

    Returns:
        The set of identifiers.
    """
    with open(path, encoding="utf-8") as handle:
        entries = json.load(handle)
    return {entry["id"] for entry in entries}


def tissue_ids(path):
    """Return the per-tissue identifiers and the counts per tissue.

    Args:
        path: the path of the per-tissue identifier list.

    Returns:
        A tuple of (mapping of tissue to identifier set, mapping of tissue
        to record count, number of unigenes occurring in more than one
        tissue).
    """
    per_tissue = {}
    counts = {}
    tissues_of = {}
    with open(path, encoding="utf-8") as handle:
        next(handle, None)
        for line in handle:
            parts = line.rstrip("\n").split("\t")
            if len(parts) < 3:
                continue
            tissue, _, identifier = parts[0], parts[1], parts[2]
            per_tissue.setdefault(tissue, set()).add(bare(identifier))
            counts[tissue] = counts.get(tissue, 0) + 1
            tissues_of.setdefault(bare(identifier), set()).add(tissue)
    shared = sum(1 for tissues in tissues_of.values() if len(tissues) > 1)
    return per_tissue, counts, shared


def write_table(path, header, rows):
    """Write a tab-separated table.

    Args:
        path: where to write it.
        header: the column names.
        rows: the rows, as lists of strings.
    """
    with open(path, "w", encoding="utf-8", newline="") as handle:
        handle.write("\t".join(header) + "\n")
        for row in rows:
            handle.write("\t".join(str(field) for field in row) + "\n")


def main(argv=None):
    """Compute the comparison.

    Args:
        argv: the command-line arguments.

    Returns:
        The exit code.
    """
    parser = argparse.ArgumentParser(description=__doc__)
    parser.parse_args(argv)

    needed = {
        "TSA FASTA": os.path.join(RAW, TSA_FASTA),
        "TSA name mapping": os.path.join(DERIVED, TSA_NAMES),
        "merged unigenes": os.path.join(RAW, MERGED_FASTA),
        "protein set": os.path.join(RAW, PROTEIN_FASTA),
        "current annotation": os.path.join(RAW, CURRENT_FASTA),
        "Trinotate JSON": os.path.join(RAW, TRINOTATE_JSON),
    }
    missing = [name for name, path in needed.items() if not os.path.exists(path)]
    if missing:
        for name, path in needed.items():
            if name in missing:
                print(f"error: {name} is missing ({path}).", file=sys.stderr)
        print(
            "    run scripts/fetch_transcriptomes.sh and "
            "scripts/extract_tsa_names.py first.",
            file=sys.stderr,
        )
        return 1

    tsa_ids = fasta_ids(needed["TSA FASTA"])
    tsa_name_set = tsa_names(needed["TSA name mapping"])
    merged = fasta_ids(needed["merged unigenes"])
    protein = fasta_ids(needed["protein set"])
    current = fasta_ids(needed["current annotation"])
    annotated = trinotate_ids(needed["Trinotate JSON"])

    merged_set = set(merged)
    protein_set = set(protein)
    current_bare = {bare(i) for i in current}
    annotated_set = set(annotated)

    current_by_tissue = {}
    for identifier in current:
        current_by_tissue.setdefault(tissue_of(identifier), set()).add(bare(identifier))

    tissue_path = os.path.join(DERIVED, TISSUE_IDS)
    have_tissues = os.path.exists(tissue_path)
    if have_tissues:
        per_tissue, tissue_counts, multi_tissue = tissue_ids(tissue_path)
    else:
        per_tissue, tissue_counts, multi_tissue = {}, {}, 0

    cns = current_by_tissue.get("CNS", set())
    # The unigenes of the current annotation's non-CNS records. This is
    # not the same set as "everything that is not under CNS": 4,389
    # unigenes occur under CNS and under another tissue both.
    non_cns = {
        bare(i) for i in current if tissue_of(i) != "CNS"
    }

    # --- the counts ---------------------------------------------------
    rows = [
        [
            "GenBank TSA GJYY00000000",
            TSA_FASTA,
            len(tsa_ids),
            len(tsa_name_set),
            "one record per unigene: the Orvis 2022 CNS transcriptome",
        ],
        [
            "AplysiaTools CNS protein set",
            PROTEIN_FASTA,
            len(protein),
            len(protein_set),
            "one predicted protein per unigene of the CNS transcriptome",
        ],
        [
            "AplysiaTools merged unigenes",
            MERGED_FASTA,
            len(merged),
            len(merged_set),
            "the merged-unigene nucleotide FASTA: one sequence per unigene",
        ],
        [
            "AplysiaTools merged unigenes, annotated",
            TRINOTATE_JSON,
            len(annotated),
            len(annotated_set),
            "the Trinotate annotation of the merged unigenes",
        ],
        [
            "AplysiaTools current annotation",
            CURRENT_FASTA,
            len(current),
            len(current_bare),
            "every tissue's proteins in one file: seven tissues",
        ],
    ]
    if have_tissues:
        for tissue in sorted(tissue_counts):
            identifiers_in = per_tissue[tissue]
            rows.append(
                [
                    f"AplysiaTools per-tissue unigenes, {tissue}",
                    FILE_TEMPLATE.format(code=tissue),
                    tissue_counts[tissue],
                    len(identifiers_in),
                    "one file per tissue, six tissues: the non-CNS part of the current annotation",
                ]
            )
        union_all = set().union(*per_tissue.values()) if per_tissue else set()
        rows.append(
            [
                "AplysiaTools per-tissue unigenes, all six",
                "http://aplysiatools.org/unigenes/ (6 files)",
                sum(tissue_counts.values()),
                len(union_all),
                "the six per-tissue files together, deduplicated across tissues",
            ]
        )

    write_table(
        COUNTS_OUT,
        ["source", "file", "records", "distinct_unigenes", "what_it_counts"],
        rows,
    )

    # --- the overlaps -------------------------------------------------
    def pair(left_name, left, right_name, right, note):
        shared = left & right
        return [
            left_name,
            right_name,
            len(left),
            len(right),
            len(shared),
            f"{100.0 * len(shared) / len(left):.1f}" if left else "-",
            f"{100.0 * len(shared) / len(right):.1f}" if right else "-",
            note,
        ]

    overlaps = [
        pair(
            "CNS protein set",
            protein_set,
            "TSA original names",
            tsa_name_set,
            "the protein set against the Orvis 2022 transcriptome",
        ),
        pair(
            "merged unigenes",
            merged_set,
            "TSA original names",
            tsa_name_set,
            "the merged-unigene FASTA against the Orvis 2022 transcriptome",
        ),
        pair(
            "merged unigenes",
            merged_set,
            "CNS protein set",
            protein_set,
            "the two AplysiaTools files against each other",
        ),
        pair(
            "merged unigenes",
            merged_set,
            "current annotation",
            current_bare,
            "the merged-unigene FASTA against every AplysiaTools protein",
        ),
        pair(
            "CNS protein set",
            protein_set,
            "current annotation CNS set",
            cns,
            "the protein set against the CNS set of the current annotation",
        ),
    ]
    if have_tissues:
        union = set().union(*per_tissue.values())
        overlaps.append(
            pair(
                "per-tissue unigenes",
                union,
                "current annotation, non-CNS records",
                non_cns,
                "the six per-tissue files against the non-CNS records of the current annotation",
            )
        )
        overlaps.append(
            pair(
                "per-tissue unigenes",
                union,
                "CNS protein set",
                protein_set,
                "the six per-tissue files against the CNS set",
            )
        )

    write_table(
        OVERLAPS_OUT,
        [
            "left",
            "right",
            "left_unigenes",
            "right_unigenes",
            "shared",
            "share_of_left_pct",
            "share_of_right_pct",
            "note",
        ],
        overlaps,
    )

    # --- the report ---------------------------------------------------
    print("record counts")
    for row in rows:
        print(f"  {row[0]:<36} {row[2]:>8,} records  {row[3]:>8,} distinct")
    print()
    print("overlaps")
    for row in overlaps:
        print(
            f"  {row[0]:<32} vs {row[1]:<32} "
            f"{row[4]:>7,} shared  ({row[5]}% of left, {row[6]}% of right)"
        )
    print()
    print("the counts the paper publishes, for comparison")
    for name, count in PAPER_COUNTS.items():
        print(f"  {name:<28} {count:>8,}")
    print()
    if have_tissues:
        cns_records = sum(1 for i in current if tissue_of(i) == "CNS")
        tissue_records = sum(tissue_counts.values())
        print("how current.annotation.fasta decomposes")
        print(f"  its CNS set                     {cns_records:>8,} records")
        print(f"  the six per-tissue files        {tissue_records:>8,} records")
        print(f"  sum                             {cns_records + tissue_records:>8,} records")
        print(f"  the file holds                  {len(current):>8,} records")
        print(f"  distinct unigenes, CNS          {len(cns):>8,}")
        print(f"  distinct unigenes, non-CNS      {len(non_cns):>8,}")
        print(f"  distinct unigenes, whole file   {len(current_bare):>8,}")
        print(f"  under CNS and another tissue    {len(cns & non_cns):>8,}")
        print(f"  unigenes in more than one tissue {multi_tissue:>7,}")
        print()
    print(f"wrote {COUNTS_OUT}")
    print(f"wrote {OVERLAPS_OUT}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
