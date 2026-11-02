#!/usr/bin/env python3
"""Compare two tool manifests and report whether they agree.

P01-01.3 asks whether the image builds the same way twice. That question is
answered by building it twice and diffing the manifests, and this script is
the diff.

Two properties matter for the comparison to mean anything.

**The build timestamp is not a difference.** Every manifest carries the moment
it was written. Two manifests that agree on every tool version still differ
on that one line, so comparing them raw reports a difference on every run and
the check becomes noise that people learn to ignore. Lines beginning with
`built:` are excluded, and the number excluded is reported, so the exclusion
is visible rather than silent.

**A difference has to be a difference in a version.** The first manifest
recorded error text where a version should have been, so a comparison of two
identical failures would have passed. `--check` reports any line whose value
is empty, reads as an error, or is `NOT FOUND`, which is the failure mode
this script exists to catch.

Usage:
    scripts/diff_manifests.py OLD NEW      compare two manifests
    scripts/diff_manifests.py --check FILE  report unusable version lines
"""

import argparse
import difflib
import re
import sys
from typing import List, Tuple

# The lines that are expected to differ between two builds of the same image.
VOLATILE_PREFIXES = ("built:",)

# A tool line is "<command><whitespace><value>". The value is allowed to be
# empty here, because an empty value is a defect worth reporting: the first
# manifest recorded two of them, and a pattern that required a non-empty
# value would have skipped those lines rather than flagged them.
TOOL_LINE = re.compile(r"^(\S+)\s{2,}(.*)$")

# Values that are a failure rather than a version.
ERROR_MARKERS = (
    "not found",
    "no such option",
    "no such file",
    "failed",
    "error",
    "not a valid file",
    "traceback",
)


def is_volatile(line: str) -> bool:
    """Return whether a line is expected to differ between two builds.

    Args:
        line: the line to classify.

    Returns:
        True if the line should be excluded from the comparison.
    """
    return line.startswith(VOLATILE_PREFIXES)


def read_manifest(path: str) -> List[str]:
    """Read a manifest and drop the lines that are expected to differ.

    Args:
        path: the file to read.

    Returns:
        The comparable lines.
    """
    with open(path, encoding="utf-8") as handle:
        return [line.rstrip("\n") for line in handle if not is_volatile(line)]


def tool_lines(lines: List[str]) -> List[Tuple[str, str, str]]:
    """Return the tool lines of a manifest.

    Only lines inside an `## env:` section are tool lines. The `## packages:`
    sections are package listings and are compared verbatim, as whole blocks.

    Args:
        lines: the manifest lines.

    Returns:
        A list of (section, command, value) triples.
    """
    found = []
    section = ""
    for line in lines:
        if line.startswith("## env:"):
            section = line[len("## env:") :].strip()
            continue
        if line.startswith("## packages:"):
            section = ""
            continue
        if not section or not line.strip() or line.startswith("#"):
            continue
        match = TOOL_LINE.match(line)
        if match:
            found.append((section, match.group(1), match.group(2)))
    return found


def unusable_values(lines: List[str]) -> List[Tuple[str, str, str]]:
    """Return the tool lines whose value is not a usable version.

    Args:
        lines: the manifest lines.

    Returns:
        A list of (section, command, value) triples, one per unusable line.
    """
    bad = []
    for section, command, value in tool_lines(lines):
        text = value.strip()
        if not text:
            bad.append((section, command, "<empty>"))
            continue
        lowered = text.lower()
        if "not found" in lowered or any(m in lowered for m in ERROR_MARKERS):
            bad.append((section, command, text))
    return bad


def compare(old_path: str, new_path: str) -> int:
    """Compare two manifests and report the differences.

    Args:
        old_path: the earlier manifest.
        new_path: the later manifest.

    Returns:
        0 if the manifests agree, 1 if they differ, 2 on an I/O error.
    """
    try:
        old_lines = read_manifest(old_path)
        new_lines = read_manifest(new_path)
    except OSError as error:
        print(f"error: {error}", file=sys.stderr)
        return 2

    excluded = 0
    with open(old_path, encoding="utf-8") as handle:
        excluded += sum(1 for line in handle if is_volatile(line))
    with open(new_path, encoding="utf-8") as handle:
        excluded += sum(1 for line in handle if is_volatile(line))

    differences = list(
        difflib.unified_diff(
            old_lines,
            new_lines,
            fromfile=old_path,
            tofile=new_path,
            lineterm="",
        )
    )

    print(f"compared {old_path} with {new_path}")
    print(f"excluded {excluded // 2} build-timestamp line(s) from each manifest")

    bad_old = unusable_values(old_lines)
    bad_new = unusable_values(new_lines)
    for label, bad in (("old", bad_old), ("new", bad_new)):
        for section, command, value in bad:
            print(f"::error::the {label} manifest has an unusable version for "
                  f"{section}/{command}: {value}")

    if differences:
        print("")
        print("".join(line + "\n" for line in differences))
        print("the two builds do not agree")
        return 1

    if bad_old or bad_new:
        print("the two builds agree, but on values that are not versions")
        return 1

    print("the two builds agree on every tool version")
    return 0


def check(path: str) -> int:
    """Report the tool lines in a manifest that do not carry a version.

    Args:
        path: the manifest to check.

    Returns:
        0 if every tool line carries a usable version, 1 otherwise.
    """
    try:
        with open(path, encoding="utf-8") as handle:
            lines = [line.rstrip("\n") for line in handle]
    except OSError as error:
        print(f"error: {error}", file=sys.stderr)
        return 2

    tools = tool_lines(lines)
    bad = unusable_values(lines)
    print(f"{path}: {len(tools)} tool lines, {len(bad)} unusable")
    for section, command, value in bad:
        print(f"::error::{section}/{command}: {value}")
    return 1 if bad else 0


def main(argv: List[str]) -> int:
    """Compare manifests, or check one of them.

    Args:
        argv: the command-line arguments.

    Returns:
        The process exit status.
    """
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", metavar="FILE", help="check one manifest")
    parser.add_argument("files", nargs="*", help="the manifests to compare")
    args = parser.parse_args(argv)

    if args.check:
        return check(args.check)
    if len(args.files) != 2:
        parser.error("give two manifests to compare, or --check FILE")
    return compare(args.files[0], args.files[1])


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
