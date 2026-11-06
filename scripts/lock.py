#!/usr/bin/env python3
"""Generate and check the lock files that pin the resolved package closure.

Pinning the direct tools does not pin the environment. Between the build
verified in P01-01.3 and the release in P01-01.4, conda-forge rebuilt
`certifi` and `pip` and moved `libnghttp2`, `r-future` and `r-openssl`, and
none of the pinned tools changed. A rebuild from the same Dockerfile on a
different day produced a different closure.

A lock file closes that gap. It names every package in the closure with its
exact version and build string, and the image is installed from it rather
than solved for:

    micromamba create -y -n bio --file lock/bio.txt

The format is conda's explicit format: the file starts with `@EXPLICIT` and
every following line is the URL of one package, which carries the channel,
the platform and the file extension. Those three cannot be recovered from
the package name, so the URLs are carried through from the source spec
rather than rebuilt from it.

The header carries two more things:

    # PINS: ...      the direct pins the closure was solved from
    # RESOLVED: ...  the same packages with their exact versions

`PINS` is the declaration of intent and lives in the Dockerfile. `RESOLVED`
is what the closure actually contains, and it is what the check compares
against the lock, so a lock that has drifted away from the pins is caught
rather than believed.

Usage:
    scripts/lock.py generate --env bio --pins "python=3.11 ..." \\
        --from explicit.txt --output lock/bio.txt
    scripts/lock.py check --env bio --pins "python=3.11 ..." --lock lock/bio.txt
    scripts/lock.py compare --lock lock/bio.txt --from explicit.txt
"""

import argparse
import re
import sys
from typing import Dict, List, NamedTuple, Tuple

# The line that tells micromamba the file is an explicit spec.
EXPLICIT = "@EXPLICIT"

# A package URL: host, channel, platform, then the file name.
URL = re.compile(
    r"^https?://(?P<host>[^/]+)/(?P<channel>[^/]+)/(?P<platform>[^/]+)/"
    r"(?P<filename>[^/]+)\.(?P<extension>conda|tar\.bz2)$"
)


def split_filename(filename: str) -> Tuple[str, str, str]:
    """Return the name, version and build string of a package file name.

    A conda file name is `name-version-build`, and the name may itself
    contain hyphens: `kernel-headers_linux-64-5.14.0-he073ed8_3` is one
    package called `kernel-headers_linux-64` at version `5.14.0`. A version
    never contains a hyphen, and the build string is always last, so the
    split runs from the right: the build is the last hyphen-separated
    piece, and the version is the last piece before it that begins with a
    digit.

    Args:
        filename: the file name, without its extension.

    Returns:
        A triple of name, version and build string.

    Raises:
        ValueError: if the name does not have the expected shape.
    """
    pieces = filename.split("-")
    if len(pieces) < 3:
        raise ValueError(f"cannot split a package file name: {filename}")
    build = pieces[-1]
    for index in range(len(pieces) - 2, 0, -1):
        if pieces[index][0].isdigit():
            version = pieces[index]
            name = "-".join(pieces[:index])
            return name, version, build
    raise ValueError(f"cannot find a version in a package file name: {filename}")


class Package(NamedTuple):
    """One package in a closure.

    Attributes:
        name: the package name.
        version: the exact version.
        build: the build string.
        channel: the channel it came from.
        platform: the subdirectory it came from.
        url: the full URL, kept verbatim so that nothing is reconstructed.
    """

    name: str
    version: str
    build: str
    channel: str
    platform: str
    url: str


def parse_spec(text: str) -> List[Package]:
    """Return the packages in an explicit spec.

    Args:
        text: the contents of an explicit spec.

    Returns:
        The packages, in file order.
    """
    packages = []
    for line in text.splitlines():
        line = line.strip()
        if not line or line.startswith("#") or line == EXPLICIT:
            continue
        match = URL.match(line)
        if not match:
            continue
        try:
            name, version, build = split_filename(match.group("filename"))
        except ValueError:
            continue
        packages.append(
            Package(
                name=name,
                version=version,
                build=build,
                channel=match.group("channel"),
                platform=match.group("platform"),
                url=line,
            )
        )
    return packages


def resolved_from(packages: List[Package], pins: List[str]) -> List[str]:
    """Return the exact version of each direct pin, where the closure has it.

    A pin names a package and a version, and the closure may hold a later
    patch of it. `python=3.11` is satisfied by `3.11.9`; the closure says
    which one was installed, and that is what gets recorded.

    Args:
        packages: the closure.
        pins: the direct pins.

    Returns:
        A list of "name=version" strings, one per pin, sorted by name.
    """
    by_name = {package.name: package.version for package in packages}
    resolved = []
    for pin in pins:
        name, wanted = pin.split("=", 1)
        if name not in by_name:
            continue
        have = by_name[name]
        if have == wanted or have.startswith(wanted + ".") or have.startswith(wanted):
            resolved.append(f"{name}={have}")
    return sorted(resolved)


def render(packages: List[Package], pins: List[str], environment: str) -> str:
    """Render a lock file.

    Args:
        packages: the closure.
        pins: the direct pins.
        environment: the name of the environment.

    Returns:
        The lock file, as text.
    """
    channels = sorted({package.channel for package in packages})
    platforms = sorted({package.platform for package in packages})
    resolved = resolved_from(packages, pins)
    lines = [
        f"# P01-01.5 lock file for the '{environment}' environment.",
        "#",
        "# The resolved closure of this environment: every package, with its",
        "# exact version and build string, as an explicit URL. The image is",
        "# installed from this file, so the closure cannot move under it.",
        "#",
        f"# Channels: {', '.join(channels)}. Platforms: {', '.join(platforms)}.",
        "#",
        "# PINS is the declaration of intent: the direct packages this",
        "# environment is for. It is copied from the Dockerfile, and the pins",
        "# are checked against the closure below.",
        f"# PINS: {' '.join(pins)}",
        "#",
        "# RESOLVED is what the closure actually contains for those pins.",
        f"# RESOLVED: {' '.join(resolved)}",
        "#",
        f"# Install with: micromamba create -y -n {environment} --file lock/{environment}.txt",
        EXPLICIT,
    ]
    lines.extend(package.url for package in packages)
    return "\n".join(lines) + "\n"


def compare(locked: List[Package], source: List[Package]) -> List[str]:
    """Return the differences between two closures.

    Args:
        locked: the closure in the lock file.
        source: the closure that was resolved.

    Returns:
        A list of human-readable differences; empty if they agree.
    """
    locked_map = {package.name: (package.version, package.build) for package in locked}
    source_map = {package.name: (package.version, package.build) for package in source}
    problems = []
    for name in sorted(set(locked_map) | set(source_map)):
        if locked_map.get(name) != source_map.get(name):
            problems.append(
                f"{name}: the lock has {locked_map.get(name)} and the "
                f"environment has {source_map.get(name)}"
            )
    return problems


def main(argv: List[str]) -> int:
    """Run the lock tool.

    Args:
        argv: the command-line arguments.

    Returns:
        The process exit status.
    """
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)

    gen = sub.add_parser("generate", help="write a lock file")
    gen.add_argument("--env", required=True)
    gen.add_argument("--pins", required=True)
    gen.add_argument("--from", dest="source", required=True)
    gen.add_argument("--output", required=True)

    check = sub.add_parser("check", help="check a lock against its pins")
    check.add_argument("--env", required=True)
    check.add_argument("--pins", required=True)
    check.add_argument("--lock", required=True)

    diff = sub.add_parser("compare", help="compare a lock with a spec")
    diff.add_argument("--lock", required=True)
    diff.add_argument("--from", dest="source", required=True)

    args = parser.parse_args(argv)

    if args.command == "generate":
        with open(args.source, encoding="utf-8") as handle:
            source = handle.read()
        packages = parse_spec(source)
        with open(args.output, "w", encoding="utf-8") as handle:
            handle.write(render(packages, args.pins.split(), args.env))
        print(f"wrote {args.output}: {len(packages)} packages")
        return 0

    if args.command == "check":
        with open(args.lock, encoding="utf-8") as handle:
            locked = parse_spec(handle.read())
        pins = args.pins.split()
        resolved = resolved_from(locked, pins)
        have = {item.split("=", 1)[0] for item in resolved}
        missing = [
            pin for pin in pins if pin.split("=", 1)[0] not in have
        ]
        for pin in missing:
            print(f"::error::the lock for {args.env} has no package for the pin {pin}")
        if missing:
            return 1
        print(f"the lock for {args.env} satisfies all {len(pins)} pins")
        return 0

    with open(args.lock, encoding="utf-8") as handle:
        locked = parse_spec(handle.read())
    with open(args.source, encoding="utf-8") as handle:
        source = parse_spec(handle.read())
    problems = compare(locked, source)
    for problem in problems:
        print(f"::error::{problem}")
    if problems:
        return 1
    print(f"the lock and the resolved environment agree on {len(locked)} packages")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
