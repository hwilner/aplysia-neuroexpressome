#!/usr/bin/env python3
"""Tests for the release recorder.

Run them with:

    python3 -m unittest discover -s tests

The recorder writes the released-image digest into the README. Two things
have to hold. It has to be idempotent, because the release workflow runs on
every push that touches the Dockerfile and a workflow that fails because the
README already mentions the digest is a workflow that gets switched off. And
it has to fail loudly when the region is missing, because a README with no
digest in it and a README with a digest in the wrong place look the same to
a reader.

The marker check also has to survive the README being edited by hand, which
is why the region is delimited by comments rather than by line numbers.
"""

import json
import os
import subprocess
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), os.pardir, "scripts"))

import record_release  # noqa: E402  pylint: disable=wrong-import-position

REPO_ROOT = os.path.join(os.path.dirname(__file__), os.pardir)
README = os.path.join(REPO_ROOT, "README.md")

RECORD = {
    "image": "ghcr.io/hwilner/aplysia-neuroexpressome",
    "digest": "sha256:" + "a" * 64,
    "tag": "sha-abc1234",
    "commit": "abc1234",
    "released_utc": "2026-11-04T09:00:00Z",
    "manifest": "docs/manifest-build-1.txt",
}


class RenderTest(unittest.TestCase):
    """The block has to say the things a reader needs."""

    def test_carries_every_field(self):
        """Each field of the record appears in the block."""
        block = record_release.render(RECORD)
        for value in RECORD.values():
            self.assertIn(value, block)

    def test_the_digest_is_in_code_font(self):
        """A digest is a hash and should not read as prose."""
        block = record_release.render(RECORD)
        self.assertIn(f"`{RECORD['digest']}`", block)

    def test_the_pull_command_is_the_digest_pull(self):
        """The command pulls by digest, not by a mutable tag."""
        block = record_release.render(RECORD)
        self.assertIn(
            f"docker pull {RECORD['image']}@{RECORD['digest']}", block
        )

    def test_the_markers_are_present(self):
        """The region has to be findable again on the next run."""
        block = record_release.render(RECORD)
        self.assertIn(record_release.BEGIN_MARKER, block)
        self.assertIn(record_release.END_MARKER, block)


class ReplaceTest(unittest.TestCase):
    """The block has to be replaceable, and only the block."""

    def test_replaces_the_region(self):
        """The old block goes and the new one arrives."""
        readme = (
            "# Title\n\nbefore\n\n"
            + record_release.render(RECORD)
            + "\n\nafter\n"
        )
        new_record = dict(RECORD, digest="sha256:" + "b" * 64)
        updated = record_release.replace_block(readme, record_release.render(new_record))
        self.assertNotIn("a" * 64, updated)
        self.assertIn("b" * 64, updated)
        self.assertIn("before", updated)
        self.assertIn("after", updated)

    def test_is_idempotent(self):
        """Writing the same record twice changes nothing."""
        readme = (
            "# Title\n\n"
            + record_release.render(RECORD)
            + "\n\nafter\n"
        )
        once = record_release.replace_block(readme, record_release.render(RECORD))
        twice = record_release.replace_block(once, record_release.render(RECORD))
        self.assertEqual(once, twice)

    def test_refuses_a_readme_without_the_region(self):
        """A missing region is an error, not a silent append."""
        with self.assertRaises(ValueError):
            record_release.replace_block("# Title\n\nno markers here\n",
                                         record_release.render(RECORD))


class RealReadmeTest(unittest.TestCase):
    """The README in the repository has to have the region."""

    def test_the_readme_has_the_region(self):
        """The markers are in the committed README."""
        with open(README, encoding="utf-8") as handle:
            readme = handle.read()
        self.assertIn(record_release.BEGIN_MARKER, readme)
        self.assertIn(record_release.END_MARKER, readme)

    def test_a_recorded_digest_is_in_code_font(self):
        """If the README records a digest, it is in code font.

        Before the first release the cell holds a placeholder and there is
        nothing to check. After it, a digest that is not in code font is a
        digest that reads as prose and can be transcribed wrongly.
        """
        with open(README, encoding="utf-8") as handle:
            readme = handle.read()
        block = readme[
            readme.index(record_release.BEGIN_MARKER) : readme.index(
                record_release.END_MARKER
            )
        ]
        row = [
            line
            for line in block.splitlines()
            if line.startswith("| Digest |")
        ]
        self.assertEqual(len(row), 1)
        value = row[0].split("|")[2].strip()
        if value != "*not released yet*":
            self.assertTrue(value.startswith("`sha256:"), value)
            self.assertTrue(value.endswith("`"), value)


class ScriptTest(unittest.TestCase):
    """The script has to run from the command line."""

    def test_writes_and_then_reports_no_change(self):
        """The second run says there is nothing to do."""
        with tempfile.TemporaryDirectory() as tmp:
            record_path = os.path.join(tmp, "release.json")
            readme_path = os.path.join(tmp, "README.md")
            with open(record_path, "w", encoding="utf-8") as handle:
                json.dump(RECORD, handle)
            with open(readme_path, "w", encoding="utf-8") as handle:
                handle.write(
                    "# Title\n\n"
                    + record_release.render(RECORD)
                    + "\n\nafter\n"
                )
            script = os.path.join(REPO_ROOT, "scripts", "record_release.py")
            first = subprocess.run(
                [sys.executable, script, "--record", record_path, "--readme", readme_path],
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(first.returncode, 0, first.stdout + first.stderr)
            self.assertIn("nothing to write", first.stdout)


if __name__ == "__main__":
    unittest.main()
