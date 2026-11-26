#!/usr/bin/env python3
"""Tests for the authoritative-build record.

Run them with:

    python3 -m unittest discover -s tests

P01-03.5 records which transcriptome build the project runs on and which one
it cites. Two things make that record worth a test.

The first is that it is a decision, and a decision can be got wrong. The
record says the analysis input is the AplysiaTools CNS set and not the
GenBank copy, and it says the accession to cite is the GenBank copy and not
the AplysiaTools one. Both are checked here against the evidence: the record
counts, the paper's published counts, and the byte-level agreement between
the two sets wherever they overlap.

The second is that a decision that is not checked against the bytes is a
wish. The record carries SHA-256 digests, and the digests are verified
against the files themselves wherever the files are present. They are not
present in continuous integration, because the raw files are gitignored and
re-fetchable, so those tests skip there; the tests that need only the
committed tree always run.

The rule-based test runs over every row of the record, rather than naming
the rows one by one. A test that names a row breaks every time that row
changes, which trains the reader to ignore the failures.
"""

import csv
import os
import subprocess
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), os.pardir, "scripts"))

from authoritative_build import (  # noqa: E402  pylint: disable=wrong-import-position
    COLUMNS,
    DECISION,
    ROLES,
    RecordError,
    check_table,
    count_records,
    genbank_date,
    parse_table,
    render,
    sha256_file,
)

REPO_ROOT = os.path.join(os.path.dirname(__file__), os.pardir)
RAW = os.path.join(REPO_ROOT, "data", "raw")
TABLE = os.path.join(REPO_ROOT, "data", "authoritative-build.tsv")
MANIFEST = os.path.join(REPO_ROOT, "data", "manifest.tsv")
NOTE = os.path.join(REPO_ROOT, "docs", "P01-03-5-authoritative-build.md")
SCRIPT = os.path.join(REPO_ROOT, "scripts", "authoritative_build.py")
DEVIATIONS = os.path.join(REPO_ROOT, "docs", "deviations.md")

# The digests and counts the record carries, and the counts the paper and
# the publisher publish. If any of these moves, the decision moves with it.
EXPECTED = {
    "analysis-input": {
        "file": "annotation_1A-2C.fasta",
        "accession": "GJYY00000000",
        "records": 39486,
        "sha256": "a35b3cbc1f4e361c5a4e83227c135fa5cd792bdbe52ffa72953eb168c5b9dc6a",
        "last_modified": "2021-04-28",
    },
    "citable-deposition": {
        "file": "tsa.GJYY.1.fsa_nt.gz",
        "accession": "GJYY00000000",
        "records": 68308,
        "sha256": "a1d6bd89baf1c2212a754a93ce3cb8eef927c988c05384d7fce68445d084a892",
        "last_modified": "2022-06-10",
    },
    "excluded": {
        "file": "new_unigenes.fasta",
        "accession": "none",
        "records": 26849,
        "sha256": "f12aab4374de954f255d9ba4e1d8aa2bc733b56c30790a3828fd55dff8a7c3bb",
        "last_modified": "2020-11-11",
    },
}

# The counts the sources themselves publish, which the record has to agree
# with. The TSA's come from stats.tsa.GJYY, the publisher's own aggregates;
# the other two are the paper's.
PUBLISHED = {
    "analysis-input": 39486,   # the paper's final unigene count, Fig. 1A
    "citable-deposition": 68308,  # the paper's "unigenes", and stats.tsa.GJYY
}


def read_table():
    """Return the committed record, as a list of dictionaries."""
    with open(TABLE, encoding="utf-8") as handle:
        return parse_table(handle.read())


def read_manifest():
    """Return the committed manifest, as a mapping from file name to row."""
    with open(MANIFEST, encoding="utf-8") as handle:
        return {
            row["file"]: row
            for row in csv.DictReader(handle, delimiter="\t")
        }


class TheCommittedRecord(unittest.TestCase):
    """The record exists, and it says what it is supposed to say."""

    def test_the_record_exists(self):
        self.assertTrue(os.path.exists(TABLE), f"{TABLE} is missing")

    def test_the_header_is_the_expected_one(self):
        with open(TABLE, encoding="utf-8") as handle:
            header = handle.readline().rstrip("\n").split("\t")
        self.assertEqual(header, list(COLUMNS))

    def test_every_role_is_present_exactly_once(self):
        roles = [row["role"] for row in read_table()]
        for role in ROLES:
            self.assertEqual(
                roles.count(role), 1, f"there must be exactly one {role} row"
            )
        self.assertEqual(len(roles), len(ROLES))

    def test_every_row_names_a_file_the_manifest_knows(self):
        manifest = read_manifest()
        for row in read_table():
            self.assertIn(
                row["file"], manifest, f"{row['file']} is not in the manifest"
            )

    def test_every_digest_agrees_with_the_manifest(self):
        manifest = read_manifest()
        for row in read_table():
            self.assertEqual(
                row["sha256"],
                manifest[row["file"]]["sha256"],
                f"{row['file']}: the record and the manifest disagree",
            )

    def test_every_digest_is_a_sha256(self):
        for row in read_table():
            self.assertRegex(row["sha256"], r"^[0-9a-f]{64}$")

    def test_every_date_is_a_date(self):
        for row in read_table():
            self.assertRegex(row["last_modified"], r"^\d{4}-\d{2}-\d{2}$")

    def test_every_record_count_is_a_positive_integer(self):
        for row in read_table():
            self.assertTrue(row["records"].isdigit())
            self.assertGreater(int(row["records"]), 0)

    def test_every_relation_says_something(self):
        for row in read_table():
            self.assertGreater(
                len(row["relation"]), 40, f"{row['file']}: the relation is a stub"
            )

    def test_the_counts_are_the_ones_the_sources_publish(self):
        for row in read_table():
            expected = PUBLISHED.get(row["role"])
            if expected is None:
                continue
            self.assertEqual(
                int(row["records"]),
                expected,
                f"{row['file']}: the record count must match the published one",
            )

    def test_the_decision_is_the_one_that_was_reached(self):
        """The analysis input and the cited accession are different files.

        This is the heart of the subtask, and it is a single assertion:
        the project does not analyse the file it cites, and it does not cite
        the file it analyses. Both are right, and a reader who assumes
        otherwise will be misled.
        """
        rows = {row["role"]: row for row in read_table()}
        self.assertNotEqual(
            rows["analysis-input"]["file"],
            rows["citable-deposition"]["file"],
        )

    def test_the_analysis_input_is_the_set_the_papers_count_describes(self):
        rows = {row["role"]: row for row in read_table()}
        self.assertEqual(rows["analysis-input"]["records"], "39486")

    def test_the_cited_accession_is_the_genbank_deposition(self):
        rows = {row["role"]: row for row in read_table()}
        self.assertEqual(rows["citable-deposition"]["accession"], "GJYY00000000")

    def test_the_excluded_build_belongs_to_no_accession(self):
        rows = {row["role"]: row for row in read_table()}
        self.assertEqual(rows["excluded"]["accession"], "none")

    def test_the_recorded_digests_and_counts_are_the_measured_ones(self):
        for row in read_table():
            expected = EXPECTED[row["role"]]
            self.assertEqual(row["file"], expected["file"])
            self.assertEqual(row["records"], str(expected["records"]))
            self.assertEqual(row["sha256"], expected["sha256"])
            self.assertEqual(row["last_modified"], expected["last_modified"])


class TheNote(unittest.TestCase):
    """The note records the decision and the evidence for it."""

    def test_the_note_exists(self):
        self.assertTrue(os.path.exists(NOTE), f"{NOTE} is missing")

    def test_the_note_states_the_decision(self):
        with open(NOTE, encoding="utf-8") as handle:
            text = handle.read()
        for phrase in (
            "annotation_1A-2C.fasta",
            "tsa.GJYY.1.fsa_nt.gz",
            "new_unigenes.fasta",
            "39,486",
            "68,308",
            "26,849",
        ):
            self.assertIn(phrase, text, f"the note does not mention {phrase}")

    def test_the_note_states_the_digests(self):
        with open(NOTE, encoding="utf-8") as handle:
            text = handle.read()
        for row in read_table():
            self.assertIn(row["sha256"], text, f"the note omits {row['file']}'s digest")

    def test_the_note_says_the_two_sets_are_the_same_build(self):
        with open(NOTE, encoding="utf-8") as handle:
            text = handle.read()
        self.assertIn("38,129", text)
        self.assertIn("38,117", text)

    def test_the_note_records_the_four_transcript_residual(self):
        """The residual is stated rather than smoothed away."""
        with open(NOTE, encoding="utf-8") as handle:
            text = handle.read()
        self.assertIn("38,125", text)
        self.assertIn("1,361", text)

    def test_the_deviation_is_filed(self):
        with open(DEVIATIONS, encoding="utf-8") as handle:
            text = handle.read()
        self.assertIn("D006", text)


class TheChecker(unittest.TestCase):
    """The checker catches what it is supposed to catch."""

    def test_a_good_table_has_no_problems(self):
        rows = read_table()
        problems = check_table(rows, read_manifest(), RAW)
        self.assertEqual(problems, [], "\n".join(problems))

    def test_a_missing_role_is_caught(self):
        rows = [row for row in read_table() if row["role"] != "excluded"]
        problems = check_table(rows, read_manifest(), RAW)
        self.assertTrue(
            any("excluded" in problem for problem in problems),
            "a table with no excluded row must be rejected",
        )

    def test_a_duplicated_role_is_caught(self):
        rows = read_table()
        rows.append(dict(rows[0]))
        problems = check_table(rows, read_manifest(), RAW)
        self.assertTrue(any("appears 2 times" in problem for problem in problems))

    def test_an_unknown_role_is_caught(self):
        rows = read_table()
        rows[0]["role"] = "the-best-one"
        problems = check_table(rows, read_manifest(), RAW)
        self.assertTrue(any("not one of the roles" in problem for problem in problems))

    def test_a_digest_that_disagrees_with_the_manifest_is_caught(self):
        rows = read_table()
        rows[0]["sha256"] = "0" * 64
        problems = check_table(rows, read_manifest(), RAW)
        self.assertTrue(any("manifest" in problem for problem in problems))

    def test_a_file_the_manifest_does_not_know_is_caught(self):
        rows = read_table()
        rows[0]["file"] = "not_a_file.fasta"
        problems = check_table(rows, read_manifest(), RAW)
        self.assertTrue(any("not in data/manifest.tsv" in problem for problem in problems))

    def test_an_empty_cell_is_caught(self):
        rows = read_table()
        rows[0]["relation"] = ""
        problems = check_table(rows, read_manifest(), RAW)
        self.assertTrue(any("empty" in problem for problem in problems))

    def test_a_bad_digest_is_caught(self):
        rows = read_table()
        rows[0]["sha256"] = "not-a-digest"
        problems = check_table(rows, read_manifest(), RAW)
        self.assertTrue(any("not a SHA-256 digest" in problem for problem in problems))

    def test_a_bad_date_is_caught(self):
        rows = read_table()
        rows[0]["last_modified"] = "28 April 2021"
        problems = check_table(rows, read_manifest(), RAW)
        self.assertTrue(any("is not a date" in problem for problem in problems))

    def test_a_bad_count_is_caught(self):
        rows = read_table()
        rows[0]["records"] = "many"
        problems = check_table(rows, read_manifest(), RAW)
        self.assertTrue(any("not a record count" in problem for problem in problems))

    def test_a_wrong_header_is_caught(self):
        with self.assertRaises(RecordError):
            parse_table("role\tfile\nanalysis-input\tx\n")

    def test_a_short_row_is_caught(self):
        broken = "\t".join(COLUMNS) + "\nonly\ttwo\n"
        with self.assertRaises(RecordError):
            parse_table(broken)

    def test_the_render_round_trips(self):
        rows = read_table()
        self.assertEqual(parse_table(render(rows)), rows)

    def test_the_rendered_table_is_tab_separated(self):
        text = render(read_table())
        for line in text.rstrip("\n").split("\n"):
            self.assertEqual(len(line.split("\t")), len(COLUMNS))

    def test_the_declared_decision_matches_the_committed_record(self):
        """The script declares the decision; the record is what it wrote.

        If these drift apart, the script would rewrite the record and change
        the project's source of truth without anyone deciding anything.
        """
        rows = {row["role"]: row for row in read_table()}
        for build in DECISION:
            row = rows.get(build.role)
            self.assertIsNotNone(row, f"the record has no {build.role} row")
            self.assertEqual(row["file"], build.file)
            self.assertEqual(row["accession"], build.accession)
            self.assertEqual(row["relation"], build.relation)


class TheTools(unittest.TestCase):
    """The small helpers do what they say."""

    def test_the_genbank_date_is_read_from_the_locus_line(self):
        with tempfile.NamedTemporaryFile("w", suffix=".txt", delete=False) as handle:
            handle.write(
                "LOCUS       GJYY01000000           68308 rc    RNA     "
                "linear   TSA 10-JUN-2022\n"
            )
            path = handle.name
        try:
            self.assertEqual(genbank_date(path), "2022-06-10")
        finally:
            os.unlink(path)

    def test_a_record_without_a_locus_line_is_an_error(self):
        with tempfile.NamedTemporaryFile("w", suffix=".txt", delete=False) as handle:
            handle.write("ACCESSION   GJYY00000000\n")
            path = handle.name
        try:
            with self.assertRaises(RecordError):
                genbank_date(path)
        finally:
            os.unlink(path)

    def test_records_are_counted_and_digests_computed(self):
        with tempfile.NamedTemporaryFile("w", suffix=".fasta", delete=False) as handle:
            handle.write(">one\nACGT\n>two\nACGT\n")
            path = handle.name
        try:
            self.assertEqual(count_records(path), 2)
            self.assertRegex(sha256_file(path), r"^[0-9a-f]{64}$")
        finally:
            os.unlink(path)


class TheBytes(unittest.TestCase):
    """The record is verified against the files themselves.

    These are skipped where the raw files are absent, which is continuous
    integration by design.
    """

    @classmethod
    def setUpClass(cls):
        missing = [
            row["file"]
            for row in read_table()
            if not os.path.exists(os.path.join(RAW, row["file"]))
        ]
        if missing:
            raise unittest.SkipTest(
                f"the raw files are not present: {', '.join(missing)}"
            )

    def test_the_digests_match_the_bytes(self):
        for row in read_table():
            path = os.path.join(RAW, row["file"])
            self.assertEqual(
                sha256_file(path),
                row["sha256"],
                f"{row['file']}: the bytes on disk do not match the record",
            )

    def test_the_record_counts_match_the_bytes(self):
        for row in read_table():
            path = os.path.join(RAW, row["file"])
            self.assertEqual(
                str(count_records(path)),
                row["records"],
                f"{row['file']}: the bytes on disk do not match the record",
            )

    def test_the_check_passes_against_the_bytes(self):
        result = subprocess.run(
            [sys.executable, SCRIPT, "check"],
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
        )
        self.assertEqual(
            result.returncode, 0, result.stdout + result.stderr
        )


if __name__ == "__main__":
    unittest.main()
