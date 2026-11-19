#!/usr/bin/env python3
"""Guard the pre-registered Results skeleton in results.md.

results.md is a pre-registration: every table and figure the manuscript
must contain is reserved there, with its caption, before any data exist,
and the file's own header says the structure is not edited after the
fact. A pre-registration that can drift silently is not one, so these
tests check the properties that make it binding:

- the pre-registered success criteria (C1-C7) are all present, with
  their thresholds and their named tests;
- the negative-result clause is still there;
- every reserved table (Tables 1-7) and Figure 1 still has its caption;
- every reserved block is either still *Pending* with its producing
  task named, or it has been filled in - in which case it must declare
  its provenance (a backtick-quoted script, artifact or record) in the
  block, because a result that does not say where it came from cannot
  be checked;
- no table cell carries a hedged number: "estimated" and "simulated"
  have no place in a results file, because only measured values may be
  written there;
- the gate record still names both gates, G1 and G2.

Run them with:

    python3 -m unittest discover -s tests
"""

import os
import re
import unittest

REPO_ROOT = os.path.join(os.path.dirname(__file__), os.pardir)
RESULTS_MD = os.path.join(REPO_ROOT, "results.md")

# The pre-registered success criteria: the row identifier and fragments
# that its threshold and test columns must contain.
CRITERIA = (
    ("C1", ("60%", "G2")),
    ("C2", ("McNemar",)),
    ("C3", ("Wilcoxon",)),
    ("C4", ("Wilcoxon",)),
    ("C5", ("90%", "descriptive")),
    ("C6", ("0.80",)),
    ("C7", ("reproduce.sh",)),
)

# Words that must never appear in a results-table data cell. The file
# records measured values or stays pending; a hedge is neither.
HEDGED_WORDS = ("estimated", "simulated")


def read_results():
    """Read results.md.

    Returns:
        The file's text.
    """
    with open(RESULTS_MD, encoding="utf-8") as handle:
        return handle.read()


def caption_blocks(text):
    """Split results.md into its reserved blocks.

    Args:
        text: the file's text.

    Returns:
        A mapping from a block label ("Table 1", "Figure 1", ...) to the
        text from that caption to the next caption or section heading.
    """
    markers = list(
        re.finditer(r"\*\*(Table \d+|Figure \d+)\.", text)
    )
    blocks = {}
    for index, marker in enumerate(markers):
        end = markers[index + 1].start() if index + 1 < len(markers) else len(text)
        section = re.search(r"\n## ", text[marker.start() : end])
        if section:
            end = marker.start() + section.start()
        blocks[marker.group(1)] = text[marker.start() : end]
    return blocks


class StructureTest(unittest.TestCase):
    """Tests that the pre-registered structure is intact."""

    @classmethod
    def setUpClass(cls):
        cls.text = read_results()
        cls.blocks = caption_blocks(cls.text)

    def test_the_success_criteria_table_is_complete(self):
        for criterion, fragments in CRITERIA:
            row = re.search(rf"^\| {criterion} \|.*$", self.text, re.MULTILINE)
            self.assertIsNotNone(row, f"criterion {criterion} is missing")
            for fragment in fragments:
                self.assertIn(
                    fragment,
                    row.group(0),
                    f"criterion {criterion} no longer states {fragment!r}",
                )

    def test_the_negative_result_clause_is_present(self):
        self.assertIn("Negative-result clause", self.text)
        self.assertIn("the negative result is published", self.text)

    def test_every_reserved_table_and_figure_has_its_caption(self):
        for label in (
            "Table 1",
            "Table 2",
            "Table 3",
            "Table 4",
            "Table 5",
            "Table 6",
            "Table 7",
            "Figure 1",
        ):
            self.assertIn(label, self.blocks, f"{label}'s caption is missing")

    def test_the_gate_record_names_both_gates(self):
        section = self.text.split("## Gate record")[-1]
        self.assertIn("G1", section)
        self.assertIn("G2", section)


class ProvenanceTest(unittest.TestCase):
    """Tests that filled-in results declare where they came from."""

    @classmethod
    def setUpClass(cls):
        cls.blocks = caption_blocks(read_results())

    def test_every_block_is_pending_with_attribution_or_filled_with_provenance(self):
        for label, block in self.blocks.items():
            if "*Pending*" in block:
                # A pending block must still say what will produce it: a
                # P01 task reference or a backtick-quoted source.
                self.assertRegex(
                    block,
                    r"P01-\d+|`[^`]+`",
                    f"{label} is pending but no longer names its producer",
                )
            else:
                # A filled block must declare its provenance: a
                # backtick-quoted script, artifact or record in the
                # block. A result that does not say where it came from
                # cannot be checked, and an unchecked number in a
                # results file is how retraction histories start.
                self.assertRegex(
                    block,
                    r"`[^`]+`",
                    f"{label} is filled in but declares no producing "
                    f"script or artifact",
                )

    def test_no_table_cell_carries_a_hedged_number(self):
        for label, block in self.blocks.items():
            for line in block.splitlines():
                if not line.startswith("|") or set(line) <= set("|- "):
                    continue
                for word in HEDGED_WORDS:
                    self.assertNotRegex(
                        line.lower(),
                        rf"\b{word}\b",
                        f"{label} contains {word!r}: results are measured "
                        f"or pending, never hedged",
                    )


if __name__ == "__main__":
    unittest.main()
