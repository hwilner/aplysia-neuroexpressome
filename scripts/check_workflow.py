#!/usr/bin/env python3
"""Check that a workflow file's block scalars are structurally sound.

There is no YAML parser in the authoring sandbox and no way to install one,
so this checks the one thing a hand-written workflow edit can get wrong: the
content of a block scalar has to be indented further than the key that opens
it. A comment or a command line placed at the wrong indentation inside a
`run: |` block ends the block silently in a YAML parser's view and turns the
rest of the file into a different structure.

Usage:
    scripts/check_workflow.py .github/workflows/build-image.yml
"""

import sys
from typing import List


def indent_of(line: str) -> int:
    """Return the number of leading spaces on a line."""
    return len(line) - len(line.lstrip(" "))


def check(path: str) -> List[str]:
    """Return the problems found in a workflow file.

    Args:
        path: the file to check.

    Returns:
        A list of human-readable problems; empty if the file is sound.
    """
    with open(path, encoding="utf-8") as handle:
        lines = handle.read().split("\n")

    problems: List[str] = []
    open_key_indent = None
    open_line = 0

    for number, line in enumerate(lines, start=1):
        stripped = line.strip()

        if not stripped or stripped.startswith("#"):
            # A comment does not end a block scalar, but a blank line does not
            # either. Neither carries content, so neither is checked.
            continue

        if open_key_indent is not None:
            if indent_of(line) > open_key_indent:
                continue
            open_key_indent = None

        # A key that opens a block scalar.
        if stripped.endswith("|") or stripped.endswith(">"):
            open_key_indent = indent_of(line)
            open_line = number
            continue

        # A sequence item is a line of its own, not a key.
        if stripped.startswith("- "):
            continue

        # A plain "key: value" line at the same level as the block we were in
        # is fine; the block has ended and we have already closed it above.
        if ":" not in stripped:
            problems.append(
                f"line {number}: {stripped[:60]!r} is neither a comment, a key, "
                f"nor content inside the block scalar opened on line {open_line}"
            )

    return problems


def main(argv: List[str]) -> int:
    """Check each file given on the command line.

    Args:
        argv: the command-line arguments.

    Returns:
        0 if every file is sound, 1 otherwise.
    """
    if not argv:
        print("usage: check_workflow.py FILE...", file=sys.stderr)
        return 2
    failed = False
    for path in argv:
        problems = check(path)
        if problems:
            failed = True
            print(f"{path}:")
            for problem in problems:
                print(f"  {problem}")
        else:
            print(f"{path}: sound")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
