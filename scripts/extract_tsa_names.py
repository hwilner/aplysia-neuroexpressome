#!/usr/bin/env python3
"""Extract the TSA's original transcript names.

Run it with:

    python3 scripts/extract_tsa_names.py

P01-03.2. The Orvis 2022 transcriptome exists in two places with two
different identifier namespaces: GenBank TSA GJYY00000000 numbers its
sequences GJYY01000001-GJYY01068308, while AplysiaTools calls them
`asmbl_N` or `TRINITY_DN...`.

Both the GenBank flatfile and the TSA FASTA carry the original name.
Every flatfile record's DEFINITION line holds it:

    DEFINITION  TSA: Aplysia californica isolate field caught, aquaculture reared
                  TRINITY_DN69521_c0_g1_i1, transcribed RNA sequence.

and every FASTA header holds it too, in the same place:

    >GJYY01000001.1 TSA: Aplysia californica isolate field caught, aquaculture
    reared TRINITY_DN69521_c0_g1_i1, transcribed RNA sequence.

P01-03.2 established the flatfile route. P01-03.4 checked the FASTA route
and found it agrees with the flatfile for all 68,308 names, so this script
is the second, independent record of the mapping rather than the only one.
Its docstring previously said that nothing in the FASTA related the two,
which was wrong.

    DEFINITION  TSA: Aplysia californica isolate field caught, aquaculture reared
                  TRINITY_DN69521_c0_g1_i1, transcribed RNA sequence.

That mapping is what lets the two copies of the transcriptome be compared
by name, and it is also what P01-03.4 does by sequence content. This
script writes it out so that the comparison can be done both ways.

It writes:

    data/derived/tsa_transcript_names.tsv    accession <TAB> original name

The derived file is not committed; the script that makes it is.
"""

import argparse
import gzip
import os
import re
import sys

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RAW = os.path.join(REPO_ROOT, "data", "raw")
DERIVED = os.path.join(REPO_ROOT, "data", "derived")

GBFF = "tsa.GJYY.1.gbff.gz"
OUT = os.path.join(DERIVED, "tsa_transcript_names.tsv")

# A DEFINITION continuation line carrying the original name.
NAME_LINE = re.compile(r"^\s{10,}([A-Za-z0-9_]+), transcribed RNA")


def extract(path):
    """Return the accession-to-name mapping of a TSA flatfile.

    Args:
        path: the path of the flatfile.

    Returns:
        The pairs, in file order.
    """
    pairs = []
    accession = None
    name = None
    with gzip.open(path, "rt", encoding="utf-8") as handle:
        for line in handle:
            if line.startswith("ACCESSION   "):
                accession = line.split()[1]
            elif line.startswith("DEFINITION"):
                name = None
            elif name is None:
                match = NAME_LINE.match(line)
                if match:
                    name = match.group(1)
            if accession and name:
                pairs.append((accession, name))
                accession = None
                name = None
    return pairs


def main(argv=None):
    """Extract the mapping.

    Args:
        argv: the command-line arguments.

    Returns:
        The exit code.
    """
    parser = argparse.ArgumentParser(description=__doc__)
    parser.parse_args(argv)

    path = os.path.join(RAW, GBFF)
    if not os.path.exists(path):
        print(
            f"error: {path} is not here. Run scripts/fetch_transcriptomes.sh first.",
            file=sys.stderr,
        )
        return 1

    pairs = extract(path)
    if not pairs:
        print(f"error: no names were found in {GBFF}.", file=sys.stderr)
        return 1

    seen = set()
    for accession, _ in pairs:
        if accession in seen:
            print(f"error: {accession} appears twice.", file=sys.stderr)
            return 1
        seen.add(accession)

    os.makedirs(DERIVED, exist_ok=True)
    with open(OUT, "w", encoding="utf-8", newline="") as handle:
        handle.write("accession\tname\n")
        for accession, name in pairs:
            handle.write(f"{accession}\t{name}\n")

    kinds = {}
    for _, name in pairs:
        kind = "asmbl_" if name.startswith("asmbl_") else "TRINITY_DN"
        kinds[kind] = kinds.get(kind, 0) + 1
    print(f"wrote {OUT} with {len(pairs)} mappings")
    for kind, count in sorted(kinds.items()):
        print(f"  {kind}: {count}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
