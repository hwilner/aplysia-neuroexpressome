#!/usr/bin/env python3
"""Record which transcriptome build the project runs on, and check it.

There are two sequence sets for the Orvis 2022 CNS transcriptome, and P01-03.3
through P01-03.4 established that they are not interchangeable:

- the **deposited** set, GenBank TSA ``GJYY00000000``, 68,308 transcripts,
  which is the set the paper deposits and the set with a BioProject, a
  BioSample and an SRA run attached to it;
- the **analysis** set, ``annotation_1A-2C.fasta`` on AplysiaTools, 39,486
  transcripts, which is the set the paper's own final unigene count is 39,486.

A third file, ``new_unigenes.fasta``, 26,849 transcripts, is a 2020 build that
matches no published count and is not part of the Orvis 2022 assembly at all.

Which of them the project lifts, and which one it cites, are two different
questions with two different answers, and this file records both. That is
the point of ``data/authoritative-build.tsv``: it is the decision, in a form
that can be checked against the bytes.

**The decision is declared here and derived nowhere.** The roles, the
accessions and the relations are the choice; the record counts, the SHA-256
digests and the dates are re-derived from the files themselves every time
``write`` runs. A decision that is re-derived from the data it is about is
not a decision, it is a summary, and it would change under the analyst.

**The check works without the raw files.** CI has no raw files, because they
are gitignored and re-fetchable. So ``check`` verifies everything that can be
verified from the committed tree -- the structure, the roles, the agreement
with ``data/manifest.tsv`` -- and verifies the digests and the record counts
against the bytes only when the bytes are there. A check that needs the
network would be a check that nobody runs.

Usage:

    python3 scripts/authoritative_build.py write [--output PATH]
    python3 scripts/authoritative_build.py check [--table PATH]

Exit status: 0 if the record is sound, 1 if it is not, 2 for usage errors and
unreadable or malformed inputs.
"""

import argparse
import csv
import datetime
import email.utils
import gzip
import hashlib
import os
import re
import sys
import urllib.request
from typing import Dict, List, NamedTuple, Optional, Tuple

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# The columns of the record, in order. Every consumer reads them by name.
COLUMNS = (
    "role",
    "file",
    "accession",
    "records",
    "sha256",
    "last_modified",
    "relation",
)

# The roles the record must carry, exactly one row each. There is no
# "other": a build that is neither the analysis input, nor the accession to
# cite, nor explicitly excluded has not been classified, and an
# unclassified build is how the wrong file gets analysed by accident.
ROLES = ("analysis-input", "citable-deposition", "excluded")

# The GenBank master record, whose LOCUS line carries the deposition date.
MASTER_RECORD = "tsa.GJYY.mstr.gbff.gz"

# A LOCUS line of a GenBank master record, e.g.
#   LOCUS       GJYY01000000           68308 rc    RNA     linear   TSA 10-JUN-2022
LOCUS_DATE = re.compile(
    r"^LOCUS\s+\S+\s+\d+\s+\S+\s+\S+\s+\S+\s+TSA\s+(\d{2}-[A-Z]{3}-\d{4})\s*$"
)

MONTHS = {
    "JAN": 1, "FEB": 2, "MAR": 3, "APR": 4, "MAY": 5, "JUN": 6,
    "JUL": 7, "AUG": 8, "SEP": 9, "OCT": 10, "NOV": 11, "DEC": 12,
}

SHA256 = re.compile(r"^[0-9a-f]{64}$")
DATE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


class Build(NamedTuple):
    """One build, as decided.

    Attributes:
        role: what the build is for in this project. One of ``ROLES``.
        file: the file name, as it appears in ``data/manifest.tsv``.
        accession: the accession the file belongs to, or ``none``.
        relation: how this build stands to the analysis input, in one
            sentence, with the numbers that say so.
        date_source: where the build's date comes from: ``http`` for the
            publisher's own ``Last-Modified`` header, or ``genbank`` for the
            LOCUS line of the deposition's master record.
    """

    role: str
    file: str
    accession: str
    relation: str
    date_source: str


# The decision. This is the whole of it.
#
# The analysis input is the AplysiaTools CNS set and not the GenBank copy
# because it is the set the paper's own final count describes: the paper
# reports 39,486 unigenes at a minimum ORF length of 400 bp, and this file
# has exactly 39,486 records. The GenBank copy is the citable deposition,
# the paper's 68,308 unigenes before that filter, and it is the accession a
# reader can fetch and the independent check on the sequences. The two are
# the same build: 38,129 identifiers in common, 38,117 of them identical
# character for character and 12 the same transcript with 35 to 71 extra
# bases at one end.
#
# The 2020 merged-unigene build is excluded. It shares only 8,089
# identifiers with the analysis input and 12,551 with the deposition, it
# matches no count the paper publishes, and the pre-registration named it
# only because the pre-registration was written before the counts were
# compared.
DECISION = (
    Build(
        role="analysis-input",
        file="annotation_1A-2C.fasta",
        accession="GJYY00000000",
        relation=(
            "the paper's final combined unigene set at the 400 bp ORF filter, "
            "the set Fig. 1C's BUSCO and the paper's downstream analysis used; "
            "38,129 of its identifiers are in the deposited set and 1,357 are "
            "not, and none of the 1,357 is a renamed copy of a deposited "
            "transcript"
        ),
        date_source="http",
    ),
    Build(
        role="citable-deposition",
        file="tsa.GJYY.1.fsa_nt.gz",
        accession="GJYY00000000",
        relation=(
            "the paper's deposited unigene set before the 400 bp ORF filter, of "
            "which the paper counts 38,125 as surviving; the accession to cite, "
            "under BioProject PRJNA792581, and the independent check on the "
            "sequences"
        ),
        date_source="genbank",
    ),
    Build(
        role="excluded",
        file="new_unigenes.fasta",
        accession="none",
        relation=(
            "the 2020 merged-unigene build, an earlier selection from the same "
            "assembly that matches no count the paper publishes; superseded by "
            "the analysis input and not used by any stage"
        ),
        date_source="http",
    ),
)


class RecordError(ValueError):
    """The record cannot be read, or the files it names cannot be used."""


def read_manifest(path: str) -> Dict[str, Dict[str, str]]:
    """Read the manifest into a mapping from file name to its row.

    Args:
        path: the path of ``data/manifest.tsv``.

    Returns:
        A mapping from file name to the manifest row, with the row's columns
        as keys.

    Raises:
        RecordError: if the manifest cannot be read or has no header.
    """
    try:
        with open(path, encoding="utf-8") as handle:
            rows = list(csv.DictReader(handle, delimiter="\t"))
    except OSError as error:
        raise RecordError(f"manifest error: {error}") from error
    if not rows:
        raise RecordError(f"manifest error: {path} is empty")
    return {row["file"]: row for row in rows}


def sha256_file(path: str) -> str:
    """Return the SHA-256 digest of a file.

    Args:
        path: the path of the file.

    Returns:
        The digest, as 64 lowercase hex characters.
    """
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def count_records(path: str) -> int:
    """Count the sequences in a FASTA file, compressed or not.

    A record is a header line. The count is of records, not of distinct
    identifiers, because a file that carries the same sequence twice is a
    different file from one that does not and the checksum will say so.

    Args:
        path: the path of the FASTA file.

    Returns:
        The number of records.
    """
    opener = gzip.open if path.endswith(".gz") else open
    count = 0
    with opener(path, "rt", encoding="utf-8", errors="replace") as handle:
        for line in handle:
            if line.startswith(">"):
                count += 1
    return count


def http_last_modified(url: str) -> str:
    """Return the publisher's own modification date for a file.

    The date is the one the server reports, not the one the file looks like
    it has locally, because the local copy is whatever the day of the
    download was.

    Args:
        url: the URL of the file.

    Returns:
        The date, as ``YYYY-MM-DD``.

    Raises:
        RecordError: if the server does not report a usable date.
    """
    request = urllib.request.Request(url, method="HEAD")
    request.add_header("User-Agent", "aplysia-neuroexpressome/1.0")
    try:
        with urllib.request.urlopen(request, timeout=60) as response:
            header = response.headers.get("Last-Modified")
    except OSError as error:
        raise RecordError(f"cannot read the date of {url}: {error}") from error
    if not header:
        raise RecordError(f"{url} reports no Last-Modified header")
    parsed = email.utils.parsedate_to_datetime(header)
    return parsed.date().isoformat()


def genbank_date(path: str) -> str:
    """Return the deposition date from a GenBank master record.

    The LOCUS line of a master record carries the date the sequence was
    deposited, which is the date the accession means.

    Args:
        path: the path of the master record, compressed or not.

    Returns:
        The date, as ``YYYY-MM-DD``.

    Raises:
        RecordError: if the record has no usable LOCUS line.
    """
    opener = gzip.open if path.endswith(".gz") else open
    with opener(path, "rt", encoding="utf-8", errors="replace") as handle:
        for line in handle:
            found = LOCUS_DATE.match(line.rstrip("\n"))
            if found:
                day, month, year = found.group(1).split("-")
                return datetime.date(
                    int(year), MONTHS[month], int(day)
                ).isoformat()
    raise RecordError(f"no LOCUS line with a date in {path}")


def derive(build: Build, manifest_row: Dict[str, str], raw_dir: str) -> Dict[str, str]:
    """Derive the measured fields of one build's record.

    Args:
        build: the declared build.
        manifest_row: the build's row in the manifest.
        raw_dir: the directory holding the raw files.

    Returns:
        The measured fields: the record count, the digest and the date.

    Raises:
        RecordError: if a file the build names is not present, or the date
            cannot be established.
    """
    path = os.path.join(raw_dir, build.file)
    if not os.path.exists(path):
        raise RecordError(
            f"{build.file} is not in {raw_dir}; fetch the raw files before "
            f"writing the record"
        )
    if build.date_source == "http":
        date = http_last_modified(manifest_row["url"])
    elif build.date_source == "genbank":
        date = genbank_date(os.path.join(raw_dir, MASTER_RECORD))
    else:
        raise RecordError(f"{build.file}: unknown date source {build.date_source!r}")
    return {
        "records": str(count_records(path)),
        "sha256": sha256_file(path),
        "last_modified": date,
    }


def render(rows: List[Dict[str, str]]) -> str:
    """Render the record as TSV text.

    Args:
        rows: the rows, in the order they should appear.

    Returns:
        The table, as text, with a header row and a trailing newline.
    """
    lines = ["\t".join(COLUMNS)]
    for row in rows:
        lines.append("\t".join(row[column] for column in COLUMNS))
    return "\n".join(lines) + "\n"


def parse_table(text: str) -> List[Dict[str, str]]:
    """Parse a record table.

    Args:
        text: the full text of the table.

    Returns:
        The rows, as a list of dictionaries keyed by column name.

    Raises:
        RecordError: if the header is not the expected one, or a row has
            the wrong number of columns.
    """
    reader = csv.reader(text.splitlines(), delimiter="\t")
    rows = [row for row in reader if row]
    if not rows:
        raise RecordError("the record is empty")
    if tuple(rows[0]) != COLUMNS:
        raise RecordError(
            f"the record's header is {rows[0]}, expected {list(COLUMNS)}"
        )
    parsed = []
    for number, row in enumerate(rows[1:], start=2):
        if len(row) != len(COLUMNS):
            raise RecordError(
                f"line {number}: {len(row)} fields, expected {len(COLUMNS)}"
            )
        parsed.append(dict(zip(COLUMNS, row)))
    return parsed


def check_table(
    rows: List[Dict[str, str]],
    manifest: Dict[str, Dict[str, str]],
    raw_dir: str,
) -> List[str]:
    """Check a record against the manifest and, where possible, the bytes.

    Args:
        rows: the parsed record.
        manifest: the manifest, keyed by file name.
        raw_dir: the directory holding the raw files, if they are there.

    Returns:
        A list of problems; empty means the record is sound. Each problem
        is phrased for whoever has to fix it.
    """
    problems: List[str] = []

    by_role: Dict[str, List[Dict[str, str]]] = {}
    seen_files: Dict[str, int] = {}
    for row in rows:
        role = row["role"]
        by_role.setdefault(role, []).append(row)
        seen_files[row["file"]] = seen_files.get(row["file"], 0) + 1
        for column in COLUMNS:
            if row[column] == "":
                problems.append(
                    f"{row['file']}: the '{column}' column is empty"
                )
        if not SHA256.match(row["sha256"]):
            problems.append(
                f"{row['file']}: {row['sha256']!r} is not a SHA-256 digest"
            )
        if not DATE.match(row["last_modified"]):
            problems.append(
                f"{row['file']}: {row['last_modified']!r} is not a date"
            )
        if not row["records"].isdigit() or int(row["records"]) <= 0:
            problems.append(
                f"{row['file']}: {row['records']!r} is not a record count"
            )

    for role in ROLES:
        count = len(by_role.get(role, []))
        if count != 1:
            problems.append(
                f"there are {count} rows with the role {role!r}; exactly one "
                f"is required"
            )
    for role in sorted(set(by_role) - set(ROLES)):
        problems.append(f"{role!r} is not one of the roles {list(ROLES)}")
    for file_name, count in sorted(seen_files.items()):
        if count > 1:
            problems.append(f"{file_name} appears {count} times in the record")

    for row in rows:
        file_name = row["file"]
        manifest_row = manifest.get(file_name)
        if manifest_row is None:
            problems.append(
                f"{file_name} is not in data/manifest.tsv; the record must name "
                f"files the manifest knows"
            )
            continue
        if manifest_row["sha256"] != row["sha256"]:
            problems.append(
                f"{file_name}: the record's SHA-256 is {row['sha256']} but the "
                f"manifest's is {manifest_row['sha256']}"
            )
        if manifest_row["accession"] != row["accession"]:
            problems.append(
                f"{file_name}: the record's accession is {row['accession']!r} but "
                f"the manifest's is {manifest_row['accession']!r}"
            )
        path = os.path.join(raw_dir, file_name)
        if not os.path.exists(path):
            continue
        digest = sha256_file(path)
        if digest != row["sha256"]:
            problems.append(
                f"{file_name}: the file on disk has the SHA-256 {digest} but the "
                f"record says {row['sha256']}"
            )
        records = count_records(path)
        if str(records) != row["records"]:
            problems.append(
                f"{file_name}: the file on disk has {records} records but the "
                f"record says {row['records']}"
            )

    return problems


def main(argv: Optional[List[str]] = None) -> int:
    """Run the authoritative-build tool.

    Args:
        argv: command-line arguments, defaults to sys.argv[1:].

    Returns:
        0 if the record is sound, 1 if it is not, 2 for usage errors and
        unreadable or malformed inputs.
    """
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = parser.add_subparsers(dest="command", required=True)

    write = sub.add_parser("write", help="write the record")
    write.add_argument(
        "--output",
        default=os.path.join(ROOT, "data", "authoritative-build.tsv"),
        help="where to write the record (default: data/authoritative-build.tsv)",
    )
    write.add_argument(
        "--manifest",
        default=os.path.join(ROOT, "data", "manifest.tsv"),
        help="the manifest to read the URLs from (default: data/manifest.tsv)",
    )
    write.add_argument(
        "--raw",
        default=os.path.join(ROOT, "data", "raw"),
        help="the directory holding the raw files (default: data/raw)",
    )

    check = sub.add_parser("check", help="check the record")
    check.add_argument(
        "--table",
        default=os.path.join(ROOT, "data", "authoritative-build.tsv"),
        help="the record to check (default: data/authoritative-build.tsv)",
    )
    check.add_argument(
        "--manifest",
        default=os.path.join(ROOT, "data", "manifest.tsv"),
        help="the manifest to check against (default: data/manifest.tsv)",
    )
    check.add_argument(
        "--raw",
        default=os.path.join(ROOT, "data", "raw"),
        help="the directory holding the raw files (default: data/raw)",
    )

    args = parser.parse_args(argv)

    try:
        manifest = read_manifest(args.manifest)
    except RecordError as error:
        print(f"::error::{error}", file=sys.stderr)
        return 2

    if args.command == "write":
        rows = []
        for build in DECISION:
            manifest_row = manifest.get(build.file)
            if manifest_row is None:
                print(
                    f"::error::{build.file} is not in the manifest",
                    file=sys.stderr,
                )
                return 2
            try:
                measured = derive(build, manifest_row, args.raw)
            except RecordError as error:
                print(f"::error::{error}", file=sys.stderr)
                return 2
            row = {
                "role": build.role,
                "file": build.file,
                "accession": build.accession,
                "relation": build.relation,
            }
            row.update(measured)
            rows.append(row)
        with open(args.output, "w", encoding="utf-8") as handle:
            handle.write(render(rows))
        print(f"wrote {args.output}: {len(rows)} builds")
        return 0

    try:
        with open(args.table, encoding="utf-8") as handle:
            rows = parse_table(handle.read())
    except (OSError, RecordError) as error:
        print(f"::error::the record cannot be read: {error}", file=sys.stderr)
        return 2

    problems = check_table(rows, manifest, args.raw)
    for problem in problems:
        print(f"::error::{problem}", file=sys.stderr)
    if problems:
        print(f"{args.table}: INVALID", file=sys.stderr)
        return 1
    for row in rows:
        print(
            f"{row['role']}: {row['file']} ({row['records']} records, "
            f"sha256 {row['sha256'][:12]}..., {row['last_modified']})"
        )
    print(f"{args.table}: valid")
    return 0


if __name__ == "__main__":
    sys.exit(main())
