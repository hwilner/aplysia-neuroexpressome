#!/usr/bin/env python3
"""Check that a workflow file's block scalars are structurally sound.

There is no YAML parser in the authoring sandbox and no way to install one,
so this checks the things a hand-written workflow edit can get wrong.

**Content at the wrong indentation.** The content of a block scalar has to
be indented further than the key that opens it. A comment or a command line
placed at the wrong indentation inside a `run: |` block ends the block
silently in a YAML parser's view and turns the rest of the file into a
different structure.

**A variable exported and read in the same step.** Writing a variable to
`$GITHUB_ENV` makes it available to the *later* steps of a job, not to the
rest of the block that wrote it. Reading it back in the same block is an
unbound variable, and under `set -u` it is a failed build. It cost a
release run to find out.

Usage:
    scripts/check_workflow.py .github/workflows/build-image.yml
"""

import re
import sys
from typing import List, Tuple

# A line that exports a variable to the next step.
EXPORT = re.compile(
    r'([A-Za-z_][A-Za-z0-9_]*)=([^\'"]*)[\'"]?\s*>>\s*[\'"]?\$GITHUB_ENV[\'"]?'
)


def indent_of(line: str) -> int:
    """Return the number of leading spaces on a line."""
    return len(line) - len(line.lstrip(" "))


def blocks(lines: List[str]) -> List[Tuple[int, List[str]]]:
    """Return the body of every block scalar in a file.

    Args:
        lines: the file's lines.

    Returns:
        A list of (line number of the opening key, body lines).
    """
    found: List[Tuple[int, List[str]]] = []
    open_key_indent = None
    open_line = 0
    body: List[str] = []

    for number, line in enumerate(lines, start=1):
        stripped = line.strip()
        if open_key_indent is not None:
            if not stripped or indent_of(line) > open_key_indent:
                body.append(line)
                continue
            found.append((open_line, body))
            open_key_indent = None
            body = []

        if not stripped or stripped.startswith("#"):
            continue
        if stripped.endswith("|") or stripped.endswith(">"):
            open_key_indent = indent_of(line)
            open_line = number
            body = []

    if open_key_indent is not None:
        found.append((open_line, body))
    return found


def exported_names(body: List[str]) -> List[str]:
    """Return the variables a block exports to the next step.

    Args:
        body: the lines of the block.

    Returns:
        The exported names.
    """
    names = []
    for line in body:
        match = EXPORT.search(line)
        if match:
            names.append(match.group(1))
    return names


def reads_names(body: List[str], names: List[str]) -> List[str]:
    """Return the exported names that the block also reads.

    The export lines themselves are excluded: writing a name is not reading
    it.

    Args:
        body: the lines of the block.
        names: the exported names.

    Returns:
        The names that are read as well as written.
    """
    offending = []
    for line in body:
        # A comment does not run. A block that explains the very mistake this
        # check looks for will otherwise be flagged for explaining it.
        if line.strip().startswith("#"):
            continue
        if EXPORT.search(line):
            continue
        for name in names:
            if re.search(r"\$" + re.escape(name) + r"\b", line) or (
                "${" + re.escape(name) + r"}" in line
            ):
                offending.append(name)
                break
    return offending


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
            continue

        if open_key_indent is not None:
            if indent_of(line) > open_key_indent:
                continue
            open_key_indent = None

        if stripped.endswith("|") or stripped.endswith(">"):
            open_key_indent = indent_of(line)
            open_line = number
            continue

        if stripped.startswith("- "):
            continue

        if ":" not in stripped:
            problems.append(
                f"line {number}: {stripped[:60]!r} is neither a comment, a key, "
                f"nor content inside the block scalar opened on line {open_line}"
            )

    for line_number, body in blocks(lines):
        names = exported_names(body)
        if not names:
            continue
        offending = reads_names(body, names)
        for name in offending:
            problems.append(
                f"line {line_number}: the block exports {name} to $GITHUB_ENV "
                f"and then reads ${name} in the same block. A variable written "
                f"to $GITHUB_ENV is available to the later steps, not to the "
                f"rest of this one."
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
