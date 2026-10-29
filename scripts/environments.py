#!/usr/bin/env python3
"""Report the micromamba environments that the Dockerfile defines.

The Dockerfile is the single source of truth for the tool pins. Continuous
integration reads the environments from here rather than repeating them, so
that the environment it solves is the environment the image actually builds,
and so that an environment added to the image cannot then be quietly skipped
by CI.

Usage:
  scripts/environments.py                 print one "<name><TAB><pins>" line per environment
  scripts/environments.py --format=json   print the same environments as a JSON array
"""

import argparse
import json
import shlex
import sys
from typing import Dict, List, NamedTuple


class Environment(NamedTuple):
    """One micromamba environment, with the pins that define it."""

    name: str
    pins: List[str]

    @property
    def pin_string(self) -> str:
        """Return the pins as a single space-separated string."""
        return " ".join(self.pins)


def logical_lines(text: str) -> List[str]:
    """Return the Dockerfile instructions, joining backslash continuations."""
    lines: List[str] = []
    pending = ""
    for raw in text.splitlines():
        stripped = raw.strip()
        if not stripped or stripped.startswith("#"):
            continue
        if pending:
            stripped = f"{pending} {stripped}"
        if stripped.endswith("\\"):
            pending = stripped[:-1].strip()
            continue
        pending = ""
        lines.append(stripped)
    return lines


def parse_environments(text: str) -> List[Environment]:
    """Return the environments defined by the `micromamba create` instructions.

    Only the environment name and the package pins are kept. The channel list
    and the clean-up step that follows each solve are not part of the
    definition of an environment.

    Args:
        text: the contents of a Dockerfile.

    Returns:
        The environments, in the order the Dockerfile defines them.
    """
    environments: List[Environment] = []
    for line in logical_lines(text):
        tokens = shlex.split(line)
        if not tokens or tokens[0] != "RUN":
            continue
        try:
            start = tokens.index("micromamba")
        except ValueError:
            continue
        if start + 1 >= len(tokens) or tokens[start + 1] != "create":
            continue
        environments.append(_environment_from_tokens(tokens[start + 2:]))
    return environments


def _environment_from_tokens(tokens: List[str]) -> Environment:
    """Return the environment described by the tokens of one `create` call."""
    name = ""
    pins: List[str] = []
    index = 0
    while index < len(tokens):
        token = tokens[index]
        if token == "&&":
            break
        if token == "-n":
            index += 1
            name = tokens[index] if index < len(tokens) else ""
        elif token == "-c":
            index += 1  # A channel, not a pin.
        elif token in ("-y", "--yes"):
            pass
        else:
            pins.append(token)
        index += 1
    if not name:
        raise ValueError(f"a micromamba create has no environment name: {' '.join(tokens)}")
    if not pins:
        raise ValueError(f"environment {name} has no package pins")
    return Environment(name=name, pins=pins)


def to_tsv(environments: List[Environment]) -> str:
    """Return the environments as tab-separated lines."""
    return "\n".join(f"{env.name}\t{env.pin_string}" for env in environments)


def to_json(environments: List[Environment]) -> str:
    """Return the environments as a JSON array of name and pins objects."""
    payload: List[Dict[str, str]] = [
        {"name": env.name, "pins": env.pin_string} for env in environments
    ]
    return json.dumps(payload)


def main(argv: List[str]) -> int:
    """Print the environments defined by the Dockerfile."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--format",
        choices=("tsv", "json"),
        default="tsv",
        help="output format (default: tsv)",
    )
    parser.add_argument(
        "--dockerfile",
        default="Dockerfile",
        help="the Dockerfile to read (default: Dockerfile)",
    )
    args = parser.parse_args(argv)

    with open(args.dockerfile, encoding="utf-8") as handle:
        environments = parse_environments(handle.read())

    if args.format == "json":
        print(to_json(environments))
    else:
        print(to_tsv(environments))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
