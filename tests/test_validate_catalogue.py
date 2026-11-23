#!/usr/bin/env python3
"""Tests for scripts/validate_catalogue.py.

The fixtures are a minimal environment manifest and small catalogue TSVs
whose validity is known by construction: a valid catalogue, a catalogue
missing the release column, one with an empty release cell, one carrying
the wrong release, and manifests that pin zero, one, or two releases.
Both failure modes named in the P01-23 acceptance criteria -- a row
without the release, and a row whose release does not match the manifest
-- are asserted to fail. The real released manifest is checked to parse
to the string the released image actually carries.

Run them with:

    python3 -m unittest discover -s tests
"""

import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), os.pardir, "scripts"))

import validate_catalogue as vc

REPO_ROOT = os.path.join(os.path.dirname(__file__), os.pardir)
REAL_MANIFEST = os.path.join(REPO_ROOT, "docs", "released-manifest.txt")

MANIFEST = """# environment manifest - generated at image build time
built: 2026-11-06T14:33:59Z

## env: ips
java                   openjdk version "11.0.30-internal" 2026-01-20
interproscan.sh        InterProScan version 5.59-91.0
"""

MANIFEST_TWO_RELEASES = MANIFEST + "interproscan.sh        InterProScan version 5.70-102.0\n"

HEADER = "locus_id\tfamily\tpfam_hit\tinterproscan_release\n"
VALID_ROW = "apcal_0001\tKv\tPF00520\t5.59-91.0\n"


class ManifestParsingTest(unittest.TestCase):
    """The expected release is read from the manifest, never typed."""

    def test_parses_the_tool_version_line(self):
        self.assertEqual(vc.parse_interproscan_release(MANIFEST), "5.59-91.0")

    def test_missing_line_is_an_error_not_a_guess(self):
        with self.assertRaises(vc.ManifestError):
            vc.parse_interproscan_release("# empty manifest\n")

    def test_two_releases_is_an_error_not_a_choice(self):
        with self.assertRaises(vc.ManifestError):
            vc.parse_interproscan_release(MANIFEST_TWO_RELEASES)

    def test_the_real_manifest_pins_the_released_image(self):
        # D002 in docs/deviations.md: the released image carries
        # 5.59-91.0, not the pre-registered 5.70-102.0.
        with open(REAL_MANIFEST, encoding="utf-8") as handle:
            self.assertEqual(vc.parse_interproscan_release(handle.read()),
                             "5.59-91.0")


class CatalogueValidationTest(unittest.TestCase):
    """Both P01-23 failure modes are caught; the valid case passes."""

    def test_valid_catalogue_passes(self):
        problems = vc.validate_catalogue_text(HEADER + VALID_ROW, "5.59-91.0")
        self.assertEqual(problems, [])

    def test_row_without_release_fails(self):
        catalogue = HEADER + "apcal_0001\tKv\tPF00520\t\n"
        problems = vc.validate_catalogue_text(catalogue, "5.59-91.0")
        self.assertEqual(len(problems), 1)
        self.assertIn("empty", problems[0])

    def test_row_with_wrong_release_fails(self):
        # The pre-registered string on a catalogue row is exactly the
        # defect D002 warns about: the image carries 5.59-91.0.
        catalogue = HEADER + "apcal_0001\tKv\tPF00520\t5.70-102.0\n"
        problems = vc.validate_catalogue_text(catalogue, "5.59-91.0")
        self.assertEqual(len(problems), 1)
        self.assertIn("5.70-102.0", problems[0])
        self.assertIn("5.59-91.0", problems[0])

    def test_missing_column_fails(self):
        catalogue = "locus_id\tfamily\tpfam_hit\napcal_0001\tKv\tPF00520\n"
        problems = vc.validate_catalogue_text(catalogue, "5.59-91.0")
        self.assertEqual(len(problems), 1)
        self.assertIn(vc.RELEASE_COLUMN, problems[0])

    def test_short_row_counts_as_missing(self):
        catalogue = HEADER + "apcal_0001\tKv\tPF00520\n"
        problems = vc.validate_catalogue_text(catalogue, "5.59-91.0")
        self.assertEqual(len(problems), 1)

    def test_every_bad_row_is_reported(self):
        catalogue = (HEADER
                     + "apcal_0001\tKv\tPF00520\t5.70-102.0\n"
                     + "apcal_0002\tHCN\tPF00000\t5.59-91.0\n"
                     + "apcal_0003\tCaV\tPF00001\t\n")
        problems = vc.validate_catalogue_text(catalogue, "5.59-91.0")
        self.assertEqual(len(problems), 2)
        self.assertIn("line 2", problems[0])
        self.assertIn("line 4", problems[1])

    def test_empty_catalogue_fails(self):
        self.assertTrue(vc.validate_catalogue_text("", "5.59-91.0"))


class CliTest(unittest.TestCase):
    """The command line distinguishes valid, invalid, and broken inputs."""

    def _write(self, directory, name, text):
        path = os.path.join(directory, name)
        with open(path, "w", encoding="utf-8") as handle:
            handle.write(text)
        return path

    def test_exit_codes(self):
        with tempfile.TemporaryDirectory() as tmp:
            manifest = self._write(tmp, "manifest.txt", MANIFEST)
            good = self._write(tmp, "good.tsv", HEADER + VALID_ROW)
            bad = self._write(tmp, "bad.tsv",
                              HEADER + "apcal_0001\tKv\tPF00520\t5.70-102.0\n")
            self.assertEqual(vc.main([good, "--manifest", manifest]), 0)
            self.assertEqual(vc.main([bad, "--manifest", manifest]), 1)
            self.assertEqual(vc.main([os.path.join(tmp, "absent.tsv"),
                                      "--manifest", manifest]), 2)
            broken = self._write(tmp, "broken.txt", "# no tool lines\n")
            self.assertEqual(vc.main([good, "--manifest", broken]), 2)


if __name__ == "__main__":
    unittest.main()
