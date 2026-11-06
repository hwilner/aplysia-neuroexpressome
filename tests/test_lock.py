#!/usr/bin/env python3
"""Tests for the lock files that pin the resolved package closure.

Run them with:

    python3 -m unittest discover -s tests

The point of these tests is that a lock file is only worth having if it is
kept in step with the thing it locks. A lock that drifts away from the pins
in the Dockerfile is worse than no lock at all, because the build would
install a closure that no longer matches the declaration of intent, and the
build would still be green.

So these tests check three things: that the lock files parse, that every
environment in the Dockerfile has a lock, and that each lock satisfies the
pins that Dockerfile declares for it.
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), os.pardir, "scripts"))

from environments import parse_environments  # noqa: E402  pylint: disable=wrong-import-position
from lock import (  # noqa: E402  pylint: disable=wrong-import-position
    EXPLICIT,
    compare,
    parse_spec,
    render,
    resolved_from,
    split_filename,
)

REPO_ROOT = os.path.join(os.path.dirname(__file__), os.pardir)
DOCKERFILE = os.path.join(REPO_ROOT, "Dockerfile")
LOCK_DIR = os.path.join(REPO_ROOT, "lock")

# Two packages whose names contain hyphens, which is where a naive split of
# the file name goes wrong: `kernel-headers_linux-64` is one package, not
# three, and its version is 5.14.0 rather than 64.
SPEC = """List of packages in environment: "/somewhere/envs/bio"

@EXPLICIT
https://conda.anaconda.org/conda-forge/linux-64/python-3.11.9-hb806964_0_cpython.conda
https://conda.anaconda.org/conda-forge/linux-64/kernel-headers_linux-64-5.14.0-he073ed8_3.conda
https://conda.anaconda.org/bioconda/noarch/busco-5.7.1-pyhdfd78af_1.tar.bz2
"""


class SplitFilenameTest(unittest.TestCase):
    """Tests for splitting a package file name."""

    def test_splits_a_plain_name(self):
        self.assertEqual(
            split_filename("python-3.11.9-hb806964_0_cpython"),
            ("python", "3.11.9", "hb806964_0_cpython"),
        )

    def test_keeps_the_hyphens_in_the_name(self):
        name, version, build = split_filename("kernel-headers_linux-64-5.14.0-he073ed8_3")
        self.assertEqual(name, "kernel-headers_linux-64")
        self.assertEqual(version, "5.14.0")
        self.assertEqual(build, "he073ed8_3")

    def test_keeps_the_hyphens_in_the_name_and_the_build(self):
        name, version, build = split_filename("r-digest-0.6.39-r44h3697838_0")
        self.assertEqual(name, "r-digest")
        self.assertEqual(version, "0.6.39")
        self.assertEqual(build, "r44h3697838_0")

    def test_rejects_a_name_that_is_too_short(self):
        with self.assertRaises(ValueError):
            split_filename("python-3.11")


class ParseSpecTest(unittest.TestCase):
    """Tests for reading an explicit spec."""

    def test_skips_the_banner_and_the_explicit_line(self):
        packages = parse_spec(SPEC)
        self.assertEqual(len(packages), 3)

    def test_keeps_the_url_verbatim(self):
        packages = parse_spec(SPEC)
        self.assertEqual(packages[1].url.split("/")[-1],
                         "kernel-headers_linux-64-5.14.0-he073ed8_3.conda")

    def test_records_the_channel_and_the_platform(self):
        packages = parse_spec(SPEC)
        self.assertEqual(packages[0].channel, "conda-forge")
        self.assertEqual(packages[0].platform, "linux-64")
        self.assertEqual(packages[2].channel, "bioconda")
        self.assertEqual(packages[2].platform, "noarch")

    def test_ignores_a_line_that_is_not_a_package(self):
        packages = parse_spec(SPEC + "this is not a url\n")
        self.assertEqual(len(packages), 3)


class ResolvedFromTest(unittest.TestCase):
    """Tests for matching the pins against the closure."""

    def test_records_the_exact_version(self):
        packages = parse_spec(SPEC)
        self.assertEqual(resolved_from(packages, ["python=3.11"]), ["python=3.11.9"])

    def test_matches_a_pin_on_an_exact_version(self):
        packages = parse_spec(SPEC)
        self.assertEqual(resolved_from(packages, ["busco=5.7.1"]), ["busco=5.7.1"])

    def test_skips_a_pin_that_is_not_in_the_closure(self):
        packages = parse_spec(SPEC)
        self.assertEqual(resolved_from(packages, ["mafft=7.525"]), [])

    def test_returns_the_pins_sorted(self):
        packages = parse_spec(SPEC)
        resolved = resolved_from(packages, ["busco=5.7.1", "python=3.11"])
        self.assertEqual(resolved, ["busco=5.7.1", "python=3.11.9"])


class RenderTest(unittest.TestCase):
    """Tests for writing a lock file."""

    def test_starts_with_the_explicit_line(self):
        text = render(parse_spec(SPEC), ["python=3.11"], "bio")
        lines = [line for line in text.splitlines() if line and not line.startswith("#")]
        self.assertEqual(lines[0], EXPLICIT)

    def test_keeps_every_url(self):
        text = render(parse_spec(SPEC), ["python=3.11"], "bio")
        self.assertEqual(len(parse_spec(text)), 3)

    def test_states_the_pins_and_the_resolved_versions(self):
        text = render(parse_spec(SPEC), ["python=3.11"], "bio")
        self.assertIn("# PINS: python=3.11", text)
        self.assertIn("# RESOLVED: python=3.11.9", text)


class CompareTest(unittest.TestCase):
    """Tests for comparing two closures."""

    def test_agrees_with_itself(self):
        packages = parse_spec(SPEC)
        self.assertEqual(compare(packages, packages), [])

    def test_reports_a_version_difference(self):
        locked = parse_spec(SPEC)
        other = parse_spec(SPEC.replace("python-3.11.9", "python-3.11.10"))
        problems = compare(locked, other)
        self.assertEqual(len(problems), 1)
        self.assertIn("python", problems[0])

    def test_reports_a_missing_package(self):
        locked = parse_spec(SPEC)
        other = parse_spec("\n".join(SPEC.splitlines()[:3]))
        problems = compare(locked, other)
        self.assertEqual(len(problems), 3)


class RepositoryLocksTest(unittest.TestCase):
    """Tests for the lock files that are committed."""

    def test_every_environment_has_a_lock(self):
        for environment in parse_environments(open(DOCKERFILE, encoding="utf-8").read()):
            path = os.path.join(LOCK_DIR, f"{environment.name}.txt")
            self.assertTrue(os.path.exists(path), f"{environment.name} has no lock file")

    def test_every_lock_satisfies_the_pins_of_its_environment(self):
        for environment in parse_environments(open(DOCKERFILE, encoding="utf-8").read()):
            path = os.path.join(LOCK_DIR, f"{environment.name}.txt")
            with open(path, encoding="utf-8") as handle:
                locked = parse_spec(handle.read())
            resolved = resolved_from(locked, environment.pins)
            have = {item.split("=", 1)[0] for item in resolved}
            for pin in environment.pins:
                name = pin.split("=", 1)[0]
                self.assertIn(name, have, f"the {environment.name} lock has no {pin}")

    def test_every_lock_states_the_pins_it_was_solved_from(self):
        for environment in parse_environments(open(DOCKERFILE, encoding="utf-8").read()):
            path = os.path.join(LOCK_DIR, f"{environment.name}.txt")
            with open(path, encoding="utf-8") as handle:
                text = handle.read()
            stated = [line for line in text.splitlines() if line.startswith("# PINS:")]
            self.assertEqual(len(stated), 1, f"{environment.name} does not state its pins")
            self.assertEqual(
                stated[0].split(":", 1)[1].split(),
                environment.pins,
                f"the pins in lock/{environment.name}.txt are not the pins in the Dockerfile",
            )

    def test_every_lock_has_the_explicit_line(self):
        for name in ("bio", "tree", "r", "ips"):
            path = os.path.join(LOCK_DIR, f"{name}.txt")
            with open(path, encoding="utf-8") as handle:
                lines = handle.read().splitlines()
            body = [line for line in lines if line and not line.startswith("#")]
            self.assertEqual(body[0], EXPLICIT, f"lock/{name}.txt is not an explicit spec")

    def test_no_lock_names_the_same_package_twice(self):
        for name in ("bio", "tree", "r", "ips"):
            path = os.path.join(LOCK_DIR, f"{name}.txt")
            with open(path, encoding="utf-8") as handle:
                packages = parse_spec(handle.read())
            names = [package.name for package in packages]
            self.assertEqual(len(names), len(set(names)), f"lock/{name}.txt has a duplicate")


if __name__ == "__main__":
    unittest.main()
