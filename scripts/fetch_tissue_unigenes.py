#!/usr/bin/env python3
"""Fetch the per-tissue unigene identifier lists from AplysiaTools.

Run it with:

    python3 scripts/fetch_tissue_unigenes.py

P01-03.3. The AplysiaTools web server keeps a second directory,
http://aplysiatools.org/unigenes/, with one unigene FASTA per tissue:

    A2.transrate.good.longestorfs.p1.cdhitest.unigenes.fasta   salivary
    A3.transrate.good.longestorfs.p1.cdhitest.unigenes.fasta   digestive
    A5.transrate.good.longestorfs.p1.cdhitest.unigenes.fasta   hepatopancreas
    A7.transrate.good.longestorfs.p1.cdhitest.unigenes.fasta   heart
    A8.transrate.good.longestorfs.p1.cdhitest.unigenes.fasta   muscle
    A10.transrate.good.longestorfs.p1.cdhitest.unigenes.fasta  hermaphroditic

These are what the six non-CNS tissue sets of `current.annotation.fasta`
are made of, and counting them is what explains that file's 196,953
records. P01-03.3 compares record counts, so it needs their counts.

The six files are 321 MB together and they are inputs, not results, so
they are not kept. Their SHA-256 is recorded and checked on every run,
and their identifiers are written out, which is all the comparison needs.

It writes:

    data/derived/tissue_unigene_ids.tsv      tissue <TAB> file <TAB> id
    data/derived/tissue_unigenes_sha256.tsv   file <TAB> bytes <TAB> sha256 <TAB> last_modified

The publisher serves no checksum for any of these files, so the SHA-256
recorded here is this repository's own record of the bytes that were
counted, and a mismatch on a later run is reported rather than
accepted. Pass --skip-download to reuse the identifiers already on disk
without touching the network.
"""

import argparse
import hashlib
import os
import subprocess
import sys
import tempfile
import time
import urllib.parse

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DERIVED = os.path.join(REPO_ROOT, "data", "derived")

BASE = "http://aplysiatools.org/unigenes"
USER_AGENT = (
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/120 Safari/537.36"
)

# The tissue each file holds. The names are AplysiaTools' own; the tissue
# code A2, A3, ... is theirs too and is what the file names carry.
TISSUES = [
    ("A2", "salivary"),
    ("A3", "digestive"),
    ("A5", "hepatopancreas"),
    ("A7", "heart"),
    ("A8", "muscle"),
    ("A10", "hermaphroditic"),
]

FILE_TEMPLATE = "{code}.transrate.good.longestorfs.p1.cdhitest.unigenes.fasta"

IDS_OUT = os.path.join(DERIVED, "tissue_unigene_ids.tsv")
SHA_OUT = os.path.join(DERIVED, "tissue_unigenes_sha256.tsv")

RETRIES = 3


def download(url):
    """Fetch a URL to a temporary file, returning its digest and metadata.

    curl is used rather than urllib because the server truncates long
    transfers: an interrupted read surfaces as IncompleteRead to urllib,
    while curl's own retry handling recovers from it.

    Args:
        url: the URL to fetch.

    Returns:
        A tuple of (path of the temporary file, sha256 hex digest,
        last-modified header). The caller removes the file.

    Raises:
        RuntimeError: if the file could not be fetched.
    """
    handle, path = tempfile.mkstemp(prefix="aplysia-tissue-", suffix=".fasta")
    os.close(handle)
    command = [
        "curl",
        "-fsSL",
        "--retry",
        "6",
        "--retry-delay",
        "5",
        "--retry-all-errors",
        "--max-time",
        "1800",
        "-A",
        USER_AGENT,
        "-H",
        "Accept-Encoding: identity",
        "-D",
        path + ".headers",
        url,
        "-o",
        path,
    ]
    result = subprocess.run(command, capture_output=True, text=True)
    if result.returncode != 0 or not os.path.exists(path) or os.path.getsize(path) == 0:
        detail = (result.stderr or "").strip().splitlines()
        message = detail[-1] if detail else f"curl exited {result.returncode}"
        if os.path.exists(path):
            os.unlink(path)
        raise RuntimeError(f"could not fetch {url}: {message}")

    digest = hashlib.sha256()
    with open(path, "rb") as stream:
        for block in iter(lambda: stream.read(1 << 20), b""):
            digest.update(block)

    modified = ""
    headers = path + ".headers"
    if os.path.exists(headers):
        with open(headers, encoding="utf-8", errors="replace") as stream:
            for line in stream:
                if line.lower().startswith("last-modified:"):
                    modified = line.split(":", 1)[1].strip()
        os.unlink(headers)
    return path, digest.hexdigest(), modified


def identifiers(path):
    """Return the identifiers of a FASTA file, in file order.

    Args:
        path: the path of the FASTA file.

    Returns:
        The identifiers, without their descriptions.
    """
    ids = []
    with open(path, encoding="utf-8", errors="replace") as handle:
        for line in handle:
            if line.startswith(">"):
                fields = line[1:].split()
                ids.append(fields[0] if fields else "")
    return ids


def read_sha256(path):
    """Return the recorded SHA-256 of each file, as a dict.

    Args:
        path: the path of the SHA-256 record.

    Returns:
        The mapping of file name to digest.
    """
    recorded = {}
    if not os.path.exists(path):
        return recorded
    with open(path, encoding="utf-8") as handle:
        next(handle, None)
        for line in handle:
            parts = line.rstrip("\n").split("\t")
            if len(parts) >= 3:
                recorded[parts[0]] = parts[2]
    return recorded


def main(argv=None):
    """Fetch the six per-tissue unigene files and record their identifiers.

    Args:
        argv: the command-line arguments.

    Returns:
        The exit code.
    """
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--skip-download",
        action="store_true",
        help="reuse the identifiers on disk without touching the network",
    )
    args = parser.parse_args(argv)

    os.makedirs(DERIVED, exist_ok=True)

    if args.skip_download:
        if not os.path.exists(IDS_OUT):
            print(
                f"error: {IDS_OUT} is not here, so there is nothing to reuse.",
                file=sys.stderr,
            )
            return 1
        print(f"reusing {IDS_OUT}")
        return 0

    recorded = read_sha256(SHA_OUT)
    rows = []
    sha_rows = []

    for code, tissue in TISSUES:
        name = FILE_TEMPLATE.format(code=code)
        url = f"{BASE}/{urllib.parse.quote(name)}"
        print(f"==> {name}  ({tissue})")
        path, digest, modified = download(url)
        try:
            size = os.path.getsize(path)
            ids = identifiers(path)
        finally:
            if os.path.exists(path):
                os.unlink(path)
        print(f"    {size:,} bytes, sha256 {digest}")
        print(f"    {len(ids):,} identifiers, last modified {modified or 'unknown'}")

        if name in recorded and recorded[name] != digest:
            print(
                f"    DOES NOT MATCH the checksum recorded earlier "
                f"({recorded[name]}); the file changed on the server",
                file=sys.stderr,
            )
            return 1

        for identifier in ids:
            rows.append((tissue, name, identifier))
        sha_rows.append((name, size, digest, modified))

    with open(IDS_OUT, "w", encoding="utf-8", newline="") as handle:
        handle.write("tissue\tfile\tid\n")
        for tissue, name, identifier in rows:
            handle.write(f"{tissue}\t{name}\t{identifier}\n")
    with open(SHA_OUT, "w", encoding="utf-8", newline="") as handle:
        handle.write("file\tbytes\tsha256\tlast_modified\n")
        for row in sha_rows:
            handle.write("\t".join(str(field) for field in row) + "\n")

    print()
    print(f"wrote {IDS_OUT} with {len(rows):,} identifiers")
    print(f"wrote {SHA_OUT} with {len(sha_rows)} files")
    return 0


if __name__ == "__main__":
    sys.exit(main())
