#!/usr/bin/env python3
"""Write the released-image record into the repository README.

The digest of the released image is written by the process that pushed the
image, not by hand. A digest transcribed by a person is a digest that can be
transcribed wrongly, and a wrong digest in a README is worse than no digest:
it is a claim of reproducibility that is false.

This script takes a release record and writes it into a marked region of the
README. It is idempotent: running it twice with the same record leaves the
README unchanged, and running it with a different record replaces the old
one. That matters because the release workflow runs on every push that
touches the Dockerfile, and a workflow that fails because the README already
mentions the digest is a workflow that gets disabled.

The region is delimited by HTML comments, so the rendered README shows a
table and the source shows where the machine-written part begins.

Usage:
    scripts/record_release.py --record release.json --readme README.md
    scripts/record_release.py --record release.json --readme README.md --print
"""

import argparse
import json
import sys
from typing import List

BEGIN_MARKER = "<!-- BEGIN RELEASED IMAGE -->"
END_MARKER = "<!-- END RELEASED IMAGE -->"

# The fields of the record, in the order they are written. Each is a label
# and the key it comes from in the record.
FIELDS = (
    ("Image", "image"),
    ("Digest", "digest"),
    ("Tag", "tag"),
    ("Built from commit", "commit"),
    ("Released", "released_utc"),
    ("Tool manifest", "manifest"),
    ("Package closure", "closure_drift"),
)


def render(record: dict) -> str:
    """Render the released-image block from a release record.

    Args:
        record: the release record.

    Returns:
        The block, as markdown, including the markers.
    """
    lines = [
        BEGIN_MARKER,
        "",
        "<!-- Written by scripts/record_release.py from the release record. "
        "Do not edit by hand. -->",
        "",
        "| | |",
        "|---|---|",
    ]
    for label, key in FIELDS:
        value = record.get(key, "")
        if key == "closure_drift":
            if value == "true":
                value = ("moved since the verified build — see "
                         "`docs/closure-drift.txt`")
            elif value == "false":
                value = "unchanged since the verified build"
            else:
                value = "not recorded"
        if key == "digest" and value:
            value = f"`{value}`"
        elif key in ("image", "manifest") and value:
            value = f"`{value}`"
        lines.append(f"| {label} | {value} |")
    lines.extend(
        [
            "",
            "Pull it with:",
            "",
            "```bash",
            f"docker pull {record.get('image', '')}@{record.get('digest', '')}",
            "```",
            "",
            END_MARKER,
        ]
    )
    return "\n".join(lines)


def replace_block(readme: str, block: str) -> str:
    """Return the README with the released-image block replaced.

    Args:
        readme: the current README.
        block: the block to write.

    Returns:
        The new README.

    Raises:
        ValueError: if the markers are not present.
    """
    start = readme.find(BEGIN_MARKER)
    end = readme.find(END_MARKER)
    if start == -1 or end == -1 or end < start:
        raise ValueError(
            f"the README has no released-image region: expected {BEGIN_MARKER} "
            f"and {END_MARKER}"
        )
    return readme[:start] + block + readme[end + len(END_MARKER) :]


def main(argv: List[str]) -> int:
    """Write the release record into the README.

    Args:
        argv: the command-line arguments.

    Returns:
        The process exit status.
    """
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--record", required=True, help="the release record")
    parser.add_argument("--readme", required=True, help="the README to update")
    parser.add_argument(
        "--print", dest="print_only", action="store_true", help="print, do not write"
    )
    args = parser.parse_args(argv)

    with open(args.record, encoding="utf-8") as handle:
        record = json.load(handle)
    with open(args.readme, encoding="utf-8") as handle:
        readme = handle.read()

    block = render(record)
    try:
        updated = replace_block(readme, block)
    except ValueError as error:
        print(f"error: {error}", file=sys.stderr)
        return 1

    if args.print_only:
        print(block)
        return 0

    if updated == readme:
        print("the README already records this release; nothing to write")
        return 0

    with open(args.readme, "w", encoding="utf-8") as handle:
        handle.write(updated)
    print(f"wrote the release record into {args.readme}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
