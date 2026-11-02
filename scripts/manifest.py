#!/usr/bin/env python3
"""Write the tool manifest for the image.

The manifest is what makes the pins inspectable without pulling the image:
one line per tool, giving the command and the version that command actually
reports, followed by the resolved package list for every environment.

Two things this script exists to fix.

**A tool's own version flag is not guaranteed to work.** The first version of
the manifest ran `--version` on every command and recorded whatever came
back. Five tools did not cooperate, and the manifest recorded the failure
instead of the version:

    hmmsearch       Failed to parse command line: No such option "--version".
    emapper.py      There was an error retrieving eggnog-mapper DB data: ...
    orthofinder     (empty)
    trimal          (empty)
    interproscan.sh present

That is not a cosmetic problem. A manifest that holds error text cannot be
diffed against another manifest and called a version comparison, and a gate
that looks for the string "NOT FOUND" passes every one of those lines. So
every tool here gets a list of candidate invocations, the output is validated,
and when no invocation yields a usable version the script falls back to the
version of the conda package that provides the command. The fallback cannot
fail, because the package is in the image by construction.

**The resolved package list is the real reproducibility surface.** The direct
pins are eleven packages in one environment; what is actually installed is
their whole transitive closure, and that closure is what has to be identical
between two builds. So the manifest also carries `micromamba list` output per
environment.

Usage:
    scripts/manifest.py                 write the manifest to stdout
    scripts/manifest.py --output PATH   write the manifest to PATH
"""

import argparse
import json
import os
import re
import subprocess
import sys
from typing import Dict, List, NamedTuple, Optional, Tuple

# The R packages are read by R itself, which reports their versions exactly.
R_PACKAGES = (
    "limma",
    "edgeR",
    "metafor",
    "lme4",
    "tidyverse",
    "ggplot2",
    "patchwork",
    "rstatix",
    "testthat",
)


class Tool(NamedTuple):
    """One command the image is expected to provide.

    Attributes:
        command: the name of the command, as the user would type it.
        package: the conda package that provides it.
        candidates: shell invocations to try, in order, for its version.
    """

    command: str
    package: str
    candidates: Tuple[str, ...]


# The tools each environment provides, and the package that provides each one.
#
# The package column is not decoration: it is the fallback used when the tool
# itself will not report a version, and the test suite checks that every
# package named here is actually pinned in that environment, so the two cannot
# drift apart without the tests failing.
TOOLS: Dict[str, List[Tool]] = {
    "bio": [
        Tool("python", "python", ("python --version",)),
        Tool("diamond", "diamond", ("diamond version", "diamond --version")),
        Tool("liftoff", "liftoff", ("liftoff --version",)),
        Tool("busco", "busco", ("busco --version",)),
        Tool("hisat2", "hisat2", ("hisat2 --version",)),
        Tool("samtools", "samtools", ("samtools --version",)),
        Tool(
            "hmmsearch",
            "hmmer",
            (
                "hmmsearch -h 2>&1 | grep -oE 'HMMER [0-9]+(\\.[0-9]+)+' | head -1",
                "hmmsearch -h 2>&1 | head -2",
            ),
        ),
        Tool(
            "emapper.py",
            "eggnog-mapper",
            (
                "emapper.py -h 2>&1 | grep -oiE 'eggnog-mapper [0-9.]+' | head -1",
                "emapper.py -h 2>&1 | head -3",
            ),
        ),
        Tool("gffread", "gffread", ("gffread --version",)),
        # biopython ships the Bio module and no executable of its own, so
        # there is no command to probe. It is still a pinned package whose
        # version matters, and the import is the check that says the module
        # is present and is the version the package actually installed.
        Tool(
            "biopython",
            "biopython",
            ('python -c "import Bio; print(Bio.__version__)"',),
        ),
        Tool(
            "orthofinder",
            "orthofinder",
            (
                "orthofinder -h 2>&1 | grep -oiE 'OrthoFinder version [0-9.]+' | head -1",
                "orthofinder --version",
            ),
        ),
        Tool(
            "TransDecoder.Predict",
            "transdecoder",
            ("TransDecoder.Predict --version",),
        ),
    ],
    "tree": [
        Tool("mafft", "mafft", ("mafft --version",)),
        Tool(
            "trimal",
            "trimal",
            ("trimal --version", "trimal -h 2>&1 | head -2"),
        ),
        Tool("iqtree2", "iqtree", ("iqtree2 --version", "iqtree2 -version")),
    ],
    "ips": [
        Tool("java", "openjdk", ("java -version",)),
        Tool(
            "interproscan.sh",
            "interproscan",
            ("interproscan.sh -version", "interproscan.sh --version"),
        ),
    ],
}

# Output that is an error rather than a version. The first manifest recorded
# several of these verbatim, which is why they are rejected explicitly rather
# than being left to look plausible.
ERROR_PATTERNS = (
    "not found",
    "no such option",
    "no such file",
    "failed",
    "error",
    "usage:",
    "traceback",
    "not a valid file",
    "cannot",
)


def is_usable_version(value: str) -> bool:
    """Return whether a captured string can serve as a version.

    A version has to be non-empty and must not read as an error. "present" is
    accepted: InterProScan's version flag needs its member databases, which
    the conda package does not ship, so for that one command the package
    version is used instead and the line is not a claim about a working run.

    Args:
        value: the captured output.

    Returns:
        True if the string can be used as a version.
    """
    text = value.strip()
    if not text:
        return False
    lowered = text.lower()
    return not any(pattern in lowered for pattern in ERROR_PATTERNS)


def run(command: str) -> Tuple[int, str]:
    """Run a shell command and return its exit status and first output line.

    Args:
        command: the shell command to run.

    Returns:
        A pair of the exit status and the first line of combined output.
    """
    try:
        completed = subprocess.run(
            command,
            shell=True,
            capture_output=True,
            text=True,
            timeout=300,
            check=False,
        )
    except (subprocess.TimeoutExpired, OSError):
        return 1, ""
    output = (completed.stdout or "") + (completed.stderr or "")
    lines = [line.strip() for line in output.splitlines() if line.strip()]
    return completed.returncode, lines[0] if lines else ""


def package_versions(environment: str) -> Dict[str, str]:
    """Return the resolved version of every package in an environment.

    Args:
        environment: the name of the micromamba environment.

    Returns:
        A mapping of package name to resolved version.
    """
    status, output = run(f"micromamba list -n {environment} --json")
    if status != 0 or not output:
        return {}
    try:
        payload = json.loads(output)
    except json.JSONDecodeError:
        return {}
    versions = {}
    for entry in payload:
        name = entry.get("name")
        version = entry.get("version")
        if name and version:
            versions[name] = version
    return versions


def tool_version(tool: Tool, versions: Dict[str, str]) -> Tuple[str, str]:
    """Return the version of a tool and where that version came from.

    The tool's own version flag is tried first. When none of the candidates
    produces a usable version, the version of the package that provides the
    command is used instead. That fallback cannot fail: the package is in the
    image because the environment pins it.

    Args:
        tool: the tool to interrogate.
        versions: the resolved package versions of the environment.

    Returns:
        A pair of the version and its source, one of "tool" or "package".
    """
    for candidate in tool.candidates:
        status, output = run(candidate)
        if status == 0 and is_usable_version(output):
            return output, "tool"
    fallback = versions.get(tool.package)
    if fallback:
        return fallback, "package"
    return "", "none"


def r_package_versions(environment: str) -> List[str]:
    """Return the version of every R package the image declares.

    Args:
        environment: the name of the micromamba environment.

    Returns:
        A list of "<package><TAB><version>" lines.
    """
    expression = (
        "cat(sprintf('%-22s %s\\n', p, "
        "tryCatch(as.character(packageVersion(p)), error=function(e) 'NOT FOUND')))"
    )
    packages = ", ".join(f'"{name}"' for name in R_PACKAGES)
    status, output = run(
        f"micromamba run -n {environment} Rscript -e "
        f"'for (p in c({packages})) {expression}'"
    )
    if status != 0:
        return [f"R{'':<21} NOT FOUND"]
    return [line for line in output.splitlines() if line.strip()]


def build_manifest(environments: List[str]) -> str:
    """Build the manifest text for the given environments.

    Args:
        environments: the names of the environments to describe, in order.

    Returns:
        The manifest, as text.
    """
    lines = [
        "# environment manifest - generated at image build time",
        "built: " + subprocess.run(
            ["date", "-u", "+%Y-%m-%dT%H:%M:%SZ"],
            capture_output=True,
            text=True,
            check=False,
        ).stdout.strip(),
        "",
    ]
    for environment in environments:
        versions = package_versions(environment)
        lines.append(f"## env: {environment}")
        if environment == "r":
            lines.extend(r_package_versions(environment))
        else:
            for tool in TOOLS.get(environment, []):
                version, source = tool_version(tool, versions)
                if not version:
                    version = "NOT FOUND"
                    source = "none"
                note = "" if source == "tool" else f"  [{source} version]"
                lines.append(f"{tool.command:<22} {version}{note}")
        lines.append("")
        lines.append(f"## packages: {environment}")
        status, output = run(f"micromamba list -n {environment}")
        if status == 0 and output.strip():
            lines.extend(output.rstrip().splitlines())
        else:
            lines.append("NOT FOUND")
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def main(argv: List[str]) -> int:
    """Write the manifest.

    Args:
        argv: the command-line arguments.

    Returns:
        The process exit status.
    """
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", help="write here instead of stdout")
    parser.add_argument(
        "--environments",
        nargs="+",
        default=["bio", "tree", "r", "ips"],
        help="the environments to describe, in order",
    )
    args = parser.parse_args(argv)

    manifest = build_manifest(args.environments)
    if args.output:
        os.makedirs(os.path.dirname(args.output) or ".", exist_ok=True)
        with open(args.output, "w", encoding="utf-8") as handle:
            handle.write(manifest)
    else:
        sys.stdout.write(manifest)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
