#!/usr/bin/env python3
"""Tests for the data layout and the rules that keep raw data out of git.

Run them with:

    python3 -m unittest discover -s tests

The point of these tests is that "raw/ is gitignored" is a claim that
decays. The rule was written as `data/raw/`, which ignores the directory
itself rather than its contents, and git does not descend into an excluded
directory - so a .gitkeep placed inside one was ignored too, and a fresh
clone had no `data/raw/` at all. The directory would have been missing from
every clean clone, and the scripts that write into it would have had to
create it.

So these tests check the behaviour rather than the text of the rule: that a
file placed in the raw directory does not show up in git's view of the
working tree, that the .gitkeep files are not ignored, and that the
manifest of checksums - which is tracked - is not ignored either.
"""

import os
import subprocess
import unittest

REPO_ROOT = os.path.join(os.path.dirname(__file__), os.pardir)


def git(*arguments):
    """Run a git command in the repository and return its output.

    Args:
        arguments: the arguments to git.

    Returns:
        The command's standard output, stripped.
    """
    result = subprocess.run(
        ["git"] + list(arguments),
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    return result.stdout.strip()


def is_ignored(path):
    """Return whether git ignores a path.

    Args:
        path: the path, relative to the repository root.

    Returns:
        True if git ignores the path.
    """
    result = subprocess.run(
        ["git", "check-ignore", "-q", path],
        cwd=REPO_ROOT,
        capture_output=True,
        check=False,
    )
    return result.returncode == 0


class LayoutTest(unittest.TestCase):
    """Tests for the directories the pipeline writes into."""

    def test_the_data_directory_exists(self):
        self.assertTrue(os.path.isdir(os.path.join(REPO_ROOT, "data")))

    def test_the_raw_directory_exists(self):
        self.assertTrue(os.path.isdir(os.path.join(REPO_ROOT, "data", "raw")))

    def test_the_derived_directory_exists(self):
        self.assertTrue(os.path.isdir(os.path.join(REPO_ROOT, "data", "derived")))


class IgnoreRulesTest(unittest.TestCase):
    """Tests for what the ignore rules do and do not exclude."""

    def test_a_raw_file_is_ignored(self):
        self.assertTrue(is_ignored("data/raw/AplCal3.0_genomic.fna"))

    def test_a_derived_file_is_ignored(self):
        self.assertTrue(is_ignored("data/derived/gene_models.gff3"))

    def test_the_raw_keep_file_is_not_ignored(self):
        # If this fails, the rule has gone back to excluding the directory
        # itself, and a clean clone will have no raw directory.
        self.assertFalse(is_ignored("data/raw/.gitkeep"))

    def test_the_derived_keep_file_is_not_ignored(self):
        self.assertFalse(is_ignored("data/derived/.gitkeep"))

    def test_the_checksum_manifest_is_not_ignored(self):
        # data/manifest.tsv is how a raw input is versioned: by the SHA-256
        # of its bytes rather than by committing the bytes.
        self.assertFalse(is_ignored("data/manifest.tsv"))

    def test_a_file_in_the_raw_directory_does_not_reach_git(self):
        probe = os.path.join(REPO_ROOT, "data", "raw", "ignore-probe.tmp")
        try:
            with open(probe, "w", encoding="utf-8") as handle:
                handle.write("probe\n")
            status = git("status", "--porcelain")
            self.assertNotIn("ignore-probe.tmp", status)
        finally:
            if os.path.exists(probe):
                os.remove(probe)


class TrackedTest(unittest.TestCase):
    """Tests for what the repository actually carries.

    A .gitkeep that is never committed leaves the directory missing from a
    clone, which is the defect this whole exercise is about.
    """

    def test_the_keep_files_are_tracked(self):
        tracked = git("ls-files", "data/").splitlines()
        for path in (
            "data/.gitkeep",
            "data/raw/.gitkeep",
            "data/derived/.gitkeep",
        ):
            self.assertIn(path, tracked, f"{path} is not tracked")

    def test_no_raw_data_is_tracked(self):
        tracked = git("ls-files", "data/raw/")
        for path in tracked.splitlines():
            self.assertTrue(
                path.endswith(".gitkeep"),
                f"{path} is tracked, and raw data is released via Zenodo, not committed",
            )


if __name__ == "__main__":
    unittest.main()
