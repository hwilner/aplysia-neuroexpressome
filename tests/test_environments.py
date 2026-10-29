#!/usr/bin/env python3
"""Tests for the Dockerfile environment parser.

Run them with:

  python3 -m unittest discover -s tests

The point of these tests is drift. The Dockerfile defines four micromamba
environments and prints a manifest section for each. Every list in the
repository that has to name those environments -- the manifest block, the
continuous-integration probe loop -- has to stay in step with the Dockerfile
itself, and a list that falls behind is the kind of defect that is only
noticed when a build has already failed.
"""

import os
import re
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), os.pardir, "scripts"))

from environments import (  # noqa: E402  pylint: disable=wrong-import-position
    Environment,
    logical_lines,
    parse_environments,
    to_json,
    to_tsv,
)

REPO_ROOT = os.path.join(os.path.dirname(__file__), os.pardir)
DOCKERFILE = os.path.join(REPO_ROOT, "Dockerfile")
ENVIRONMENT_SCRIPT = os.path.join(REPO_ROOT, "scripts", "environment.sh")

# A minimal Dockerfile that exercises the parser, including the shapes that
# have to be ignored and the shapes that have to be rejected.
FIXTURE = """
FROM mambaorg/micromamba:2.9.0
RUN micromamba clean --all --yes
RUN micromamba create -y -n bio \\
        -c conda-forge -c bioconda \\
        python=3.11 \\
        diamond=2.1.8 \\
    && micromamba clean --all --yes
RUN micromamba create -y -n tree -c conda-forge mafft=7.525
RUN echo "not a solve"
"""


class ParseEnvironmentsTest(unittest.TestCase):
    """Tests for parse_environments."""

    def test_parses_name_and_pins(self):
        environments = parse_environments(FIXTURE)
        self.assertEqual(
            environments,
            [
                Environment("bio", ["python=3.11", "diamond=2.1.8"]),
                Environment("tree", ["mafft=7.525"]),
            ],
        )

    def test_ignores_instructions_that_do_not_solve(self):
        names = [env.name for env in parse_environments(FIXTURE)]
        self.assertNotIn("clean", names)

    def test_rejects_a_solve_without_a_name(self):
        with self.assertRaises(ValueError):
            parse_environments("RUN micromamba create -y -c conda-forge python=3.11")

    def test_rejects_a_solve_without_pins(self):
        with self.assertRaises(ValueError):
            parse_environments("RUN micromamba create -y -n bio -c conda-forge")


class DockerFileTest(unittest.TestCase):
    """Tests against the Dockerfile this repository actually ships."""

    def setUp(self):
        with open(DOCKERFILE, encoding="utf-8") as handle:
            self.text = handle.read()
        self.environments = parse_environments(self.text)

    def test_defines_the_expected_environments(self):
        self.assertEqual(
            [env.name for env in self.environments],
            ["bio", "tree", "r", "ips"],
        )

    def test_every_environment_has_pins(self):
        for env in self.environments:
            with self.subTest(environment=env.name):
                self.assertTrue(env.pins)

    def test_manifest_covers_every_environment(self):
        """Every environment the Dockerfile solves has a manifest section.

        A manifest section that is missing leaves the tool it describes
        unchecked: the build reports a tool as present when nobody ever
        looked for it.
        """
        sections = {
            match.group(1)
            for match in re.finditer(r'echo "## env: ([^"]+)"', self.text)
        }
        self.assertEqual(sections, {env.name for env in self.environments})

    def test_manifest_lists_a_tool_for_every_environment(self):
        """Each manifest section checks at least one named tool.

        A section that names no tool checks nothing, and the build then
        reports the environment as present when nobody ever looked inside it.
        """
        sections = _manifest_sections(self.text)
        self.assertEqual(set(sections), {env.name for env in self.environments})
        for name, body in sections.items():
            with self.subTest(environment=name):
                self.assertNotEqual(body.strip(), "")


def _manifest_sections(text):
    """Return the manifest block of the Dockerfile, keyed by environment.

    Args:
        text: the contents of a Dockerfile.

    Returns:
        The text of each "## env: <name>" section of the manifest block.
    """
    parts = re.split(r'echo "## env: ([^"]+)"', text)
    sections = {}
    for index in range(1, len(parts), 2):
        sections[parts[index]] = parts[index + 1]
    return sections


class HelperScriptTest(unittest.TestCase):
    """Tests for the helper that prints the image's tool manifest."""

    def test_helper_does_not_hardcode_an_environment_count(self):
        """The helper must not state how many environments the image has.

        A hardcoded count goes stale the moment an environment is added or
        removed, and the stale count is exactly what misleads a reader about
        what the image contains.
        """
        with open(ENVIRONMENT_SCRIPT, encoding="utf-8") as handle:
            text = handle.read()
        for word in ("two", "three", "four", "five", "six"):
            with self.subTest(word=word):
                self.assertNotRegex(text, rf"\b{word}\b")


class SerialisationTest(unittest.TestCase):
    """Tests for the two output formats."""

    def setUp(self):
        self.environments = [
            Environment("bio", ["python=3.11", "diamond=2.1.8"]),
            Environment("tree", ["mafft=7.525"]),
        ]

    def test_tsv_has_one_line_per_environment(self):
        lines = to_tsv(self.environments).splitlines()
        self.assertEqual(len(lines), 2)
        self.assertEqual(lines[0], "bio\tpython=3.11 diamond=2.1.8")

    def test_json_round_trips(self):
        import json

        payload = json.loads(to_json(self.environments))
        self.assertEqual(
            payload,
            [
                {"name": "bio", "pins": "python=3.11 diamond=2.1.8"},
                {"name": "tree", "pins": "mafft=7.525"},
            ],
        )


if __name__ == "__main__":
    unittest.main()
