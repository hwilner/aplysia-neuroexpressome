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
import datetime
import json
import os
import re
import subprocess
import sys
import tempfile
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


def environment_command(environment: str, command: str) -> str:
    """Return the command that runs `command` inside a micromamba environment.

    The probes have to run in the environment they describe. Run in the
    base environment they report whatever the base environment happens to
    have, which is how an `openjdk=11` pin was reported as Java 22: the
    `java` on the path was not the one the pin installed.

    The command is written to a file and that file is run, rather than
    being quoted into a command line. Several probes contain single quotes
    of their own, and quoting them into a command line is where the first
    version of the R probe went wrong.

    Args:
        environment: the name of the micromamba environment.
        command: the command to run inside it.

    Returns:
        The command that runs the other command in the environment.
    """
    handle = tempfile.NamedTemporaryFile(
        "w", suffix=".sh", delete=False, encoding="utf-8"
    )
    handle.write(command)
    handle.close()
    return f"micromamba run -n {environment} bash {handle.name}"


def run(command: str, environment: str = "") -> Tuple[int, str]:
    """Run a shell command and return its exit status and first output line.

    Both output streams are searched for the line. Several tools report
    their version on standard error: `java -version` always does, and
    `gffread --version` and `mafft --version` do as well. A version probe
    that reads only standard output sees an empty string for those three
    and records them as absent, which is how an `openjdk=11` pin was
    reported as absent from the image.

    Args:
        command: the shell command to run.
        environment: the micromamba environment to run it in, if any.

    Returns:
        A pair of the exit status and the first line of output.
    """
    status, stdout, stderr = run_full(command, environment)
    lines = [
        line.strip()
        for line in (stdout + stderr).splitlines()
        if line.strip()
    ]
    return status, lines[0] if lines else ""


def run_full(command: str, environment: str = "") -> Tuple[int, str, str]:
    """Run a shell command and return its status and both output streams.

    The streams have to be kept apart. `micromamba list` writes a header
    line before the package list, and the header is on standard output, so
    a helper that took the first line of the combined output returned the
    header and never the list. A helper that joined the streams would
    return a header on standard error instead of the JSON on standard
    output. Neither is what the caller asked for.

    Args:
        command: the shell command to run.
        environment: the micromamba environment to run it in, if any.

    Returns:
        A triple of the exit status, standard output and standard error.
    """
    script = ""
    if environment:
        command = environment_command(environment, command)
        script = command.split(" bash ", 1)[1]
    try:
        completed = subprocess.run(
            command,
            shell=True,
            capture_output=True,
            text=True,
            timeout=600,
            check=False,
        )
    except (subprocess.TimeoutExpired, OSError):
        return 1, "", ""
    finally:
        if script:
            try:
                os.unlink(script)
            except OSError:
                pass
    return completed.returncode, completed.stdout or "", completed.stderr or ""


def package_versions(environment: str) -> Dict[str, str]:
    """Return the resolved version of every package in an environment.

    Args:
        environment: the name of the micromamba environment.

    Returns:
        A mapping of package name to resolved version.
    """
    # Not run inside the environment: `micromamba list` is the environment
    # manager's own command and reads the prefix directly.
    status, stdout, _ = run_full(f"micromamba list -n {environment} --json")
    if status == 0 and stdout.strip():
        versions = _versions_from_json(stdout)
        if versions:
            return versions
    # The JSON is the convenient form, not a guaranteed one. The text
    # listing is always there, and it is what the manifest prints, so it is
    # also the fallback.
    return _versions_from_text(package_listing(environment))


def _versions_from_json(text: str) -> Dict[str, str]:
    """Return the package versions in a JSON listing.

    The shape is not fixed: some versions of micromamba print a bare array
    of package objects and some print an object with the array under a key.
    Both are handled, and a banner printed before the JSON is ignored.

    Args:
        text: the JSON output, possibly preceded by a banner.

    Returns:
        A mapping of package name to version; empty if nothing parsed.
    """
    payloads: List = []
    try:
        payloads.append(json.loads(text))
    except json.JSONDecodeError:
        start = text.find("[")
        end = text.rfind("]")
        if start != -1 and end > start:
            try:
                payloads.append(json.loads(text[start : end + 1]))
            except json.JSONDecodeError:
                pass
        start = text.find("{")
        end = text.rfind("}")
        if start != -1 and end > start:
            try:
                payloads.append(json.loads(text[start : end + 1]))
            except json.JSONDecodeError:
                pass

    versions: Dict[str, str] = {}
    for payload in payloads:
        entries = payload
        if isinstance(payload, dict):
            for key in ("packages", "installed_packages", "pkgs"):
                if isinstance(payload.get(key), list):
                    entries = payload[key]
                    break
            else:
                entries = []
        if not isinstance(entries, list):
            continue
        for entry in entries:
            if not isinstance(entry, dict):
                continue
            name = entry.get("name")
            version = entry.get("version")
            if name and version:
                versions[name] = version
        if versions:
            break
    return versions


def _versions_from_text(lines: List[str]) -> Dict[str, str]:
    """Return the package versions in a text listing.

    The listing is four columns: name, version, build string and channel.
    None of them contains a space, so the columns can be split on
    whitespace.

    Args:
        lines: the listing lines.

    Returns:
        A mapping of package name to version.
    """
    versions: Dict[str, str] = {}
    for line in lines:
        fields = line.split()
        if len(fields) < 2:
            continue
        name, version = fields[0], fields[1]
        if name.lower() == "name" or version.startswith("---"):
            continue
        versions[name] = version
    return versions


def package_listing(environment: str) -> List[str]:
    """Return the resolved package list of an environment, one package per line.

    Args:
        environment: the name of the micromamba environment.

    Returns:
        The listing lines, without the banner `micromamba list` prints.
    """
    status, stdout, _ = run_full(f"micromamba list -n {environment}")
    if status != 0:
        return []
    lines = [line.rstrip() for line in stdout.splitlines() if line.strip()]
    if lines and lines[0].lower().startswith("list of packages"):
        lines = lines[1:]
    return lines


def tool_version(
    tool: Tool, versions: Dict[str, str], environment: str = ""
) -> Tuple[str, str]:
    """Return the version of a tool and where that version came from.

    The tool's own version flag is tried first. When none of the candidates
    produces a usable version, the version of the package that provides the
    command is used instead. That fallback cannot fail: the package is in the
    image because the environment pins it.

    Args:
        tool: the tool to interrogate.
        versions: the resolved package versions of the environment.
        environment: the micromamba environment to probe in.

    Returns:
        A pair of the version and its source, one of "tool" or "package".
    """
    for candidate in tool.candidates:
        status, output = run(candidate, environment)
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
    # The R code goes inside shell double quotes and the R strings inside
    # shell single quotes. The other way round, the R string quotes end the
    # shell's quoting and the code arrives at R with its quotes stripped.
    expression = (
        "cat(sprintf('%-22s %s\\n', p, "
        "tryCatch(as.character(packageVersion(p)), error=function(e) 'NOT FOUND')))"
    )
    packages = ", ".join(f"'{name}'" for name in R_PACKAGES)
    status, stdout, _ = run_full(
        f"Rscript -e \"for (p in c({packages})) {expression}\"", environment
    )
    if status != 0:
        return ["R NOT FOUND"]
    # Every package prints its own line, so the whole output is needed here.
    # Taking the first line would report one package and lose the other eight.
    return [line.rstrip() for line in stdout.splitlines() if line.strip()]


def build_manifest(environments: List[str]) -> str:
    """Build the manifest text for the given environments.

    Args:
        environments: the names of the environments to describe, in order.

    Returns:
        The manifest, as text.
    """
    lines = [
        "# environment manifest - generated at image build time",
        "built: " + datetime.datetime.now(datetime.timezone.utc).strftime(
            "%Y-%m-%dT%H:%M:%SZ"
        ),
        "",
    ]
    for environment in environments:
        versions = package_versions(environment)
        lines.append(f"## env: {environment}")
        if environment == "r":
            lines.extend(r_package_versions(environment))
        else:
            for tool in TOOLS.get(environment, []):
                version, source = tool_version(tool, versions, environment)
                if not version:
                    version = "NOT FOUND"
                    source = "none"
                note = "" if source == "tool" else f"  [{source} version]"
                lines.append(f"{tool.command:<22} {version}{note}")
        lines.append("")
        lines.append(f"## packages: {environment}")
        listing = package_listing(environment)
        lines.extend(listing if listing else ["NOT FOUND"])
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
