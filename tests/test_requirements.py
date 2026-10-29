#!/usr/bin/env python3
"""Tests for the pin-requirement formatter.

Run them with:

  python3 -m unittest discover -s tests
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), os.pardir, "scripts"))

from requirements import format_requirements  # noqa: E402  pylint: disable=wrong-import-position

# The shape that `micromamba repoquery depends --json` prints. The build it
# describes is the r-metafor 4.4_0 build for R 4.3, which is the constraint
# that made the R environment unsolvable alongside R 4.4.
PAYLOAD = """
{
  "query": {"query": "r-metafor=4.4_0", "type": "depends"},
  "result": {
    "graph_roots": [
      {
        "build_number": 0,
        "build_string": "r43hc72bb7e_0",
        "channel": "conda-forge",
        "depends": [
          "r-base >=4.3,<4.4.0a0",
          "r-mathjaxr",
          "r-matrix"
        ],
        "name": "r-metafor",
        "version": "4.4_0"
      }
    ]
  }
}
"""


class FormatRequirementsTest(unittest.TestCase):
    """Tests for format_requirements."""

    def test_names_the_build_and_its_constraints(self):
        lines = format_requirements(PAYLOAD)
        self.assertIn("  r-metafor 4.4_0 [r43hc72bb7e_0]", lines)
        self.assertIn("      requires r-base >=4.3,<4.4.0a0", lines)

    def test_lists_every_constraint(self):
        lines = format_requirements(PAYLOAD)
        self.assertEqual(len([line for line in lines if "requires" in line]), 3)

    def test_reports_nothing_for_an_unknown_pin(self):
        self.assertEqual(format_requirements('{"result": {"graph_roots": []}}'), [])

    def test_reports_nothing_for_output_that_is_not_json(self):
        self.assertEqual(format_requirements("Getting repodata from channels..."), [])


if __name__ == "__main__":
    unittest.main()
