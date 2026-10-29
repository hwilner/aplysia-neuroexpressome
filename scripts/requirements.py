#!/usr/bin/env python3
"""Print the requirements of the packages a conda pin resolves to.

`micromamba repoquery depends --json` reports the builds that a pin resolves
to and the constraints each of those builds carries. The plain text output of
the same command is the solver's progress log, which buries the requirement
under lines about cached shards - and that is why the reason a pin was
rejected was missing from the build logs this repository kept.

Usage:

  micromamba repoquery depends <pin> -c conda-forge -c bioconda --json \
    | scripts/requirements.py
"""

import json
import sys
from typing import List


def format_requirements(payload: str) -> List[str]:
    """Return one line per resolved build, with the constraints it carries.

    Args:
        payload: the JSON that `micromamba repoquery depends --json` prints.

    Returns:
        A line for each build the pin resolves to. A pin that the index does
        not know produces no lines.
    """
    try:
        data = json.loads(payload)
    except ValueError:
        return []
    roots = data.get("result", {}).get("graph_roots", [])
    lines = []
    for root in roots:
        lines.append(
            "  {name} {version} [{build}]".format(
                name=root.get("name", "?"),
                version=root.get("version", "?"),
                build=root.get("build_string", "?"),
            )
        )
        for dependency in root.get("depends", []):
            lines.append(f"      requires {dependency}")
    return lines


def main() -> int:
    """Print the requirements of the pins described on standard input."""
    lines = format_requirements(sys.stdin.read())
    for line in lines:
        print(line)
    return 0


if __name__ == "__main__":
    sys.exit(main())
