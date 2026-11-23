#!/usr/bin/env python3
"""Validate that a channel catalogue carries the InterProScan data release.

This implements the acceptance gate for issue P01-23, which the deviation
register (docs/deviations.md D002) made mandatory: because the released
image carries InterProScan 5.59-91.0 rather than the pre-registered
5.70-102.0, the data release is part of what every domain hit means, so
every row of the P01-13 channel catalogue must carry it, and it must be
the release of the image that actually ran -- never a string typed by
hand.

The rules, fixed here before the catalogue exists:

- The catalogue is a TSV with a header row. One column is dedicated to
  the release and is named exactly ``interproscan_release``.
- Every data row carries a non-empty value in that column, and the value
  equals the release string of the released image exactly.
- The expected string is read from the environment manifest
  (``docs/released-manifest.txt``), from the line on which the
  ``interproscan.sh`` tool reports ``InterProScan version X``. The
  manifest must contain exactly one such line; zero or several is a
  manifest error, not something to guess around.

A catalogue row without the release fails validation; a row whose release
does not match the manifest fails validation; both failure modes are
pinned by tests with fixture catalogues.

Usage:

    python3 scripts/validate_catalogue.py CATALOGUE [--manifest MANIFEST]

Exit status: 0 if the catalogue is valid, 1 if any row fails, 2 for
usage errors and unreadable or malformed inputs.
"""

import argparse
import csv
import os
import re
import sys
from typing import List, Optional

# The dedicated column, named once here so producers and this validator
# cannot drift apart.
RELEASE_COLUMN = "interproscan_release"

# The manifest line on which the tool reports its own version, e.g.
# "interproscan.sh        InterProScan version 5.59-91.0".
RELEASE_LINE = re.compile(r"^interproscan\.sh\s+InterProScan version (\S+)\s*$")

DEFAULT_MANIFEST = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), os.pardir,
    "docs", "released-manifest.txt",
)


class ManifestError(ValueError):
    """The environment manifest does not pin exactly one release."""


def parse_interproscan_release(manifest_text: str) -> str:
    """Read the InterProScan release string from an environment manifest.

    Args:
        manifest_text: the full text of an environment manifest such as
            ``docs/released-manifest.txt``.

    Returns:
        The release string, e.g. ``5.59-91.0``.

    Raises:
        ManifestError: if the manifest does not contain exactly one
            ``interproscan.sh`` version line.
    """
    matches = []
    for line in manifest_text.splitlines():
        found = RELEASE_LINE.match(line.strip())
        if found:
            matches.append(found.group(1))
    if not matches:
        raise ManifestError(
            "manifest carries no interproscan.sh version line; the expected "
            "release cannot be established"
        )
    if len(set(matches)) > 1 or len(matches) > 1:
        raise ManifestError(
            f"manifest carries {len(matches)} interproscan.sh version lines "
            f"({sorted(set(matches))}); exactly one is required"
        )
    return matches[0]


def validate_catalogue_text(
    catalogue_text: str, expected_release: str
) -> List[str]:
    """Validate catalogue TSV text against the expected release string.

    Args:
        catalogue_text: the full text of the catalogue TSV.
        expected_release: the release string every row must carry.

    Returns:
        A list of problems; empty means the catalogue is valid. Problems
        are phrased for the producer of the catalogue, one per defect.
    """
    problems: List[str] = []
    reader = csv.reader(catalogue_text.splitlines(), delimiter="\t")
    rows = [row for row in reader if row]
    if not rows:
        return ["catalogue is empty; even a header row is missing"]
    header = rows[0]
    if RELEASE_COLUMN not in header:
        return [
            f"catalogue header has no '{RELEASE_COLUMN}' column; every "
            f"catalogue row must carry the InterProScan data release"
        ]
    column = header.index(RELEASE_COLUMN)
    for number, row in enumerate(rows[1:], start=2):  # Line 1 is the header.
        value: Optional[str] = row[column] if column < len(row) else None
        if value is None or value == "":
            problems.append(
                f"line {number}: empty {RELEASE_COLUMN}; a catalogue row "
                f"without the data release fails validation"
            )
        elif value != expected_release:
            problems.append(
                f"line {number}: {RELEASE_COLUMN} is {value!r} but the "
                f"released image carries {expected_release!r}"
            )
    return problems


def main(argv: Optional[List[str]] = None) -> int:
    """Validate a catalogue file.

    Args:
        argv: command-line arguments, defaults to sys.argv[1:].

    Returns:
        0 if the catalogue is valid, 1 if any row fails validation, 2 for
        usage errors and unreadable or malformed inputs.
    """
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("catalogue", help="the channel catalogue TSV")
    parser.add_argument(
        "--manifest",
        default=DEFAULT_MANIFEST,
        help="environment manifest to read the expected release from "
        "(default: docs/released-manifest.txt next to this script)",
    )
    args = parser.parse_args(argv)
    try:
        with open(args.manifest, encoding="utf-8") as handle:
            expected = parse_interproscan_release(handle.read())
    except (OSError, ManifestError) as error:
        print(f"manifest error: {error}", file=sys.stderr)
        return 2
    try:
        with open(args.catalogue, encoding="utf-8") as handle:
            catalogue_text = handle.read()
    except OSError as error:
        print(f"catalogue error: {error}", file=sys.stderr)
        return 2
    problems = validate_catalogue_text(catalogue_text, expected)
    if problems:
        print(f"{args.catalogue}: INVALID", file=sys.stderr)
        for problem in problems:
            print(f"  {problem}", file=sys.stderr)
        return 1
    print(f"{args.catalogue}: valid (InterProScan {expected})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
