#!/usr/bin/env python3
"""Tests for the workflow checker.

Run them with:

    python3 -m unittest discover -s tests

The checker exists because there is no YAML parser in the authoring sandbox,
so a hand-edited workflow has to be checked by reading it. It caught two
things that a build would otherwise have caught by failing: content at the
wrong indentation inside a block scalar, and a variable that is exported to
`$GITHUB_ENV` and then read back in the same block.

The second one cost a release run. It is worth a test.
"""

import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), os.pardir, "scripts"))

import check_workflow  # noqa: E402  pylint: disable=wrong-import-position

REPO_ROOT = os.path.join(os.path.dirname(__file__), os.pardir)
WORKFLOWS = os.path.join(REPO_ROOT, ".github", "workflows")

BROKEN = """\
name: broken
on:
  push:
    branches: [main]
jobs:
  broken:
    runs-on: ubuntu-latest
    steps:
      - name: Build
        run: |
          set -euo pipefail
          echo "IMAGE=ghcr.io/example" >> "$GITHUB_ENV"
          docker build -t "$IMAGE:latest" .
"""

FIXED = """\
name: fixed
on:
  push:
    branches: [main]
jobs:
  ok:
    runs-on: ubuntu-latest
    steps:
      - name: Build
        run: |
          set -euo pipefail
          image="ghcr.io/example"
          echo "IMAGE=$image" >> "$GITHUB_ENV"
          docker build -t "$image:latest" .
"""

COMMENTED = """\
name: commented
on:
  push:
    branches: [main]
jobs:
  ok:
    runs-on: ubuntu-latest
    steps:
      - name: Build
        run: |
          set -euo pipefail
          # the old step exported IMAGE and then read "$IMAGE" here
          image="ghcr.io/example"
          echo "IMAGE=$image" >> "$GITHUB_ENV"
          docker build -t "$image:latest" .
"""


class ExportTest(unittest.TestCase):
    """A variable exported to $GITHUB_ENV is not readable in the same block."""

    def write(self, text):
        """Write a workflow to a temporary file and return its path."""
        handle = tempfile.NamedTemporaryFile(
            "w", suffix=".yml", delete=False, encoding="utf-8"
        )
        handle.write(text)
        handle.close()
        self.addCleanup(os.unlink, handle.name)
        return handle.name

    def test_flags_an_export_read_in_the_same_block(self):
        """The bug that cost a release run is caught."""
        problems = check_workflow.check(self.write(BROKEN))
        self.assertTrue(problems)
        self.assertIn("GITHUB_ENV", problems[0])

    def test_accepts_the_fixed_form(self):
        """A block that sets a local variable first is fine."""
        self.assertEqual(check_workflow.check(self.write(FIXED)), [])

    def test_a_comment_is_not_a_read(self):
        """A block that explains the mistake is not flagged for it."""
        self.assertEqual(check_workflow.check(self.write(COMMENTED)), [])

    def test_finds_the_exported_names(self):
        """The names are read out of the export lines."""
        names = check_workflow.exported_names(
            ['echo "IMAGE=$image" >> "$GITHUB_ENV"', "docker build ."]
        )
        self.assertEqual(names, ["IMAGE"])


class RealWorkflowTest(unittest.TestCase):
    """The workflows in the repository have to pass the check."""

    def test_every_workflow_is_sound(self):
        """No workflow in the repository trips the checker."""
        for name in sorted(os.listdir(WORKFLOWS)):
            if not name.endswith(".yml"):
                continue
            with self.subTest(workflow=name):
                problems = check_workflow.check(os.path.join(WORKFLOWS, name))
                self.assertEqual(problems, [], f"{name}: {problems}")


if __name__ == "__main__":
    unittest.main()
