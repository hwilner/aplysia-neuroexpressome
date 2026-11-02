#!/usr/bin/env python3
"""Tests for the manifest generator and the manifest diff.

Run them with:

    python3 -m unittest discover -s tests

These are the tests that can be run without a container, which is the point:
the manifest machinery is the part that decides whether P01-01.3's comparison
means anything, and it should be checkable on a laptop rather than only in CI.

Three things are under test.

**The tool-to-package map cannot drift.** Every package the manifest falls
back on has to be pinned in that environment, or the fallback would report a
version the image does not contain.

**The five failures are caught.** The first manifest recorded error text where
a version belonged. The validator has to reject each of those, and the
fallback has to produce a real version when a tool refuses to report one.

**The diff excludes the build timestamp and nothing else.** A comparison that
excluded too much would pass on manifests that genuinely disagree.
"""

import os
import subprocess
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), os.pardir, "scripts"))

import diff_manifests  # noqa: E402  pylint: disable=wrong-import-position
import manifest  # noqa: E402  pylint: disable=wrong-import-position
from environments import parse_environments  # noqa: E402  pylint: disable=wrong-import-position

REPO_ROOT = os.path.join(os.path.dirname(__file__), os.pardir)
DOCKERFILE = os.path.join(REPO_ROOT, "Dockerfile")


class VersionValidatorTest(unittest.TestCase):
    """The validator has to reject what the first manifest actually recorded."""

    def test_rejects_the_five_recorded_failures(self):
        """The failures from the green build must not pass as versions."""
        failures = [
            'Failed to parse command line: No such option "--version".',
            'There was an error retrieving eggnog-mapper DB data: not a valid file',
            "",
            "   ",
            "NOT FOUND",
            "Traceback (most recent call last):",
            "No such file or directory",
        ]
        for failure in failures:
            with self.subTest(value=failure):
                self.assertFalse(manifest.is_usable_version(failure))

    def test_accepts_real_versions(self):
        """Real version strings must pass."""
        versions = [
            "Python 3.11.9",
            "v7.525 (2024/Mar/13)",
            "BUSCO 5.7.1",
            "5.59_91.0",
            "3.62.0",
        ]
        for version in versions:
            with self.subTest(version=version):
                self.assertTrue(manifest.is_usable_version(version))


class ToolPackageMapTest(unittest.TestCase):
    """The fallback package has to be a package the image actually installs."""

    def setUp(self):
        with open(DOCKERFILE, encoding="utf-8") as handle:
            self.environments = parse_environments(handle.read())

    def test_every_mapped_package_is_pinned(self):
        """Each tool's fallback package must be a pin in that environment."""
        for environment in self.environments:
            tools = manifest.TOOLS.get(environment.name, [])
            if not tools:
                continue
            pinned = {pin.split("=")[0] for pin in environment.pins}
            for tool in tools:
                with self.subTest(env=environment.name, tool=tool.command):
                    self.assertIn(
                        tool.package,
                        pinned,
                        f"{environment.name}/{tool.command} falls back on "
                        f"{tool.package}, which is not pinned in that environment",
                    )

    def test_every_pinned_package_has_a_tool(self):
        """A pinned package with no tool means the manifest never checks it."""
        for environment in self.environments:
            tools = manifest.TOOLS.get(environment.name, [])
            if not tools:
                continue
            covered = {tool.package for tool in tools}
            for pin in environment.pins:
                package = pin.split("=")[0]
                with self.subTest(env=environment.name, package=package):
                    self.assertIn(
                        package,
                        covered,
                        f"{package} is pinned in {environment.name} but no tool "
                        f"reports its version",
                    )

    def test_r_packages_are_all_declared(self):
        """Every R package the manifest reports must be in the R list."""
        self.assertEqual(len(manifest.R_PACKAGES), len(set(manifest.R_PACKAGES)))
        for name in manifest.R_PACKAGES:
            with self.subTest(package=name):
                self.assertTrue(name)


class FallbackTest(unittest.TestCase):
    """When a tool will not report a version, the package version is used."""

    def test_falls_back_to_the_package_version(self):
        """A tool whose candidates all fail takes the package version."""
        tool = manifest.Tool("trimal", "trimal", ("false", "also-false"))
        version, source = manifest.tool_version(tool, {"trimal": "1.5.1"})
        self.assertEqual(version, "1.5.1")
        self.assertEqual(source, "package")

    def test_prefers_the_tool_own_version(self):
        """A tool that does report a version is taken at its word."""
        tool = manifest.Tool("mafft", "mafft", ("echo v7.525",))
        version, source = manifest.tool_version(tool, {"mafft": "7.525"})
        self.assertEqual(version, "v7.525")
        self.assertEqual(source, "tool")

    def test_missing_package_gives_no_version(self):
        """With no package version either, there is no version to report."""
        tool = manifest.Tool("x", "x", ("false",))
        version, source = manifest.tool_version(tool, {})
        self.assertEqual(version, "")
        self.assertEqual(source, "none")


MANIFEST_A = """\
# environment manifest - generated at image build time
built: 2026-10-29T07:25:45Z

## env: bio
python                 Python 3.11.9
mafft                  v7.525 (2024/Mar/13)

## packages: bio
python 3.11.9
"""

MANIFEST_B = """\
# environment manifest - generated at image build time
built: 2026-11-02T09:00:00Z

## env: bio
python                 Python 3.11.9
mafft                  v7.525 (2024/Mar/13)

## packages: bio
python 3.11.9
"""

MANIFEST_DIFFERENT = """\
# environment manifest - generated at image build time
built: 2026-11-02T09:00:00Z

## env: bio
python                 Python 3.11.9
mafft                  v7.525 (2024/Mar/13)

## packages: bio
python 3.11.10
"""

MANIFEST_BROKEN = """\
# environment manifest - generated at image build time
built: 2026-11-02T09:00:00Z

## env: bio
python                 Python 3.11.9
hmmsearch              Failed to parse command line: No such option "--version".

## packages: bio
python 3.11.9
"""


class DiffTest(unittest.TestCase):
    """The diff has to exclude the timestamp and nothing else."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)

    def write(self, name, text):
        """Write a manifest to a temporary file and return its path."""
        path = os.path.join(self.tmp.name, name)
        with open(path, "w", encoding="utf-8") as handle:
            handle.write(text)
        return path

    def test_ignores_the_build_timestamp(self):
        """Two builds at different times still agree."""
        old = self.write("a.txt", MANIFEST_A)
        new = self.write("b.txt", MANIFEST_B)
        self.assertEqual(diff_manifests.compare(old, new), 0)

    def test_reports_a_real_difference(self):
        """A changed package version is a difference."""
        old = self.write("a.txt", MANIFEST_A)
        new = self.write("c.txt", MANIFEST_DIFFERENT)
        self.assertEqual(diff_manifests.compare(old, new), 1)

    def test_reports_a_changed_tool_version(self):
        """A changed tool version is a difference."""
        changed = MANIFEST_B.replace("v7.525", "v7.520")
        old = self.write("a.txt", MANIFEST_A)
        new = self.write("d.txt", changed)
        self.assertEqual(diff_manifests.compare(old, new), 1)

    def test_catches_an_unusable_version(self):
        """Two manifests that agree on an error are not two agreeing versions."""
        old = self.write("a.txt", MANIFEST_A)
        broken = self.write("e.txt", MANIFEST_BROKEN)
        self.assertEqual(diff_manifests.compare(old, broken), 1)

    def test_check_reports_unusable_lines(self):
        """--check finds the unusable version lines in one manifest."""
        broken = self.write("e.txt", MANIFEST_BROKEN)
        self.assertEqual(diff_manifests.check(broken), 1)
        good = self.write("b.txt", MANIFEST_B)
        self.assertEqual(diff_manifests.check(good), 0)

    def test_check_ignores_the_timestamp(self):
        """The timestamp is not a tool line."""
        good = self.write("b.txt", MANIFEST_B)
        self.assertEqual(diff_manifests.check(good), 0)

    def test_the_real_green_manifest_has_unusable_lines(self):
        """The manifest from the green build must fail --check.

        This is the regression that motivated the whole exercise: the build
        was green, and the manifest it produced recorded error text for two
        tools and empty strings for two more.
        """
        path = os.path.join(REPO_ROOT, "docs", "environment-manifest-2026-10-29.txt")
        if not os.path.exists(path):
            self.skipTest("the recorded manifest is not in the repository")
        self.assertEqual(diff_manifests.check(path), 1)

        with open(path, encoding="utf-8") as handle:
            lines = [line.rstrip("\n") for line in handle]
        bad = {
            (section, command)
            for section, command, _ in diff_manifests.unusable_values(lines)
        }
        expected = {
            ("bio", "hmmsearch"),
            ("bio", "emapper.py"),
            ("bio", "orthofinder"),
            ("tree", "trimal"),
        }
        self.assertEqual(
            bad,
            expected,
            "the green manifest's defects are exactly these four tools, and "
            "the set must not change silently",
        )

    def test_an_empty_version_is_unusable(self):
        """An empty version field is a defect, not an absent one."""
        manifest_text = (
            "# environment manifest\n"
            "built: 2026-10-29T07:25:45Z\n"
            "\n"
            "## env: bio\n"
            "orthofinder          \n"
            "\n"
            "## packages: bio\n"
            "python 3.11.9\n"
        )
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "m.txt")
            with open(path, "w", encoding="utf-8") as handle:
                handle.write(manifest_text)
            self.assertEqual(diff_manifests.check(path), 1)
            bad = diff_manifests.unusable_values(
                [line.rstrip("\n") for line in open(path, encoding="utf-8")]
            )
            self.assertEqual(len(bad), 1)
            self.assertEqual(bad[0][1], "orthofinder")


class StreamTest(unittest.TestCase):
    """A version probe has to look at both output streams.

    `java -version` writes to standard error, and so do `gffread --version`
    and `mafft --version`. A probe that reads only standard output sees
    nothing for those three and records them as absent.
    """

    def test_a_version_on_stderr_is_found(self):
        """A tool that reports on standard error is still found."""
        original = manifest.run_full
        manifest.run_full = lambda command, environment="": (
            0,
            "",
            "openjdk version \"11.0.30-internal\" 2026-01-20\n",
        )
        try:
            version, source = manifest.tool_version(
                manifest.Tool("java", "openjdk", ("java -version",)),
                {"openjdk": "11.0.30"},
                "ips",
            )
        finally:
            manifest.run_full = original
        self.assertEqual(version, 'openjdk version "11.0.30-internal" 2026-01-20')
        self.assertEqual(source, "tool")


class RListingTest(unittest.TestCase):
    """The R section has to list every package, not the first one.

    The R code prints one line per package. A helper that returned only the
    first line of the output would have reported one package and silently
    lost the other eight.
    """

    def test_every_r_package_is_listed(self):
        """All nine packages come back."""
        output = "\n".join(
            f"{name:<22} 1.0.0" for name in manifest.R_PACKAGES
        )
        original = manifest.run_full
        manifest.run_full = lambda command, environment="": (0, output, "")
        try:
            lines = manifest.r_package_versions("r")
        finally:
            manifest.run_full = original
        self.assertEqual(len(lines), len(manifest.R_PACKAGES))
        for name in manifest.R_PACKAGES:
            self.assertTrue(
                any(line.startswith(name) for line in lines),
                f"{name} is missing from the R section",
            )


class EnvironmentTest(unittest.TestCase):
    """A probe has to run in the environment it describes.

    Run in the base environment, a probe reports whatever the base
    environment happens to have. That is how an `openjdk=11` pin was
    reported as Java 22: the java on the path was not the one the pin
    installed, and the manifest said so without noticing.
    """

    def test_probes_run_inside_the_environment(self):
        """The generated command must enter the environment."""
        command = manifest.environment_command("ips", "java -version")
        self.assertIn("micromamba run -n ips", command)
        self.assertIn("java -version", open(command.split("bash ", 1)[1]).read())

    def test_a_probe_with_quotes_survives(self):
        """A command containing single quotes has to arrive intact."""
        probe = "python -c \"import Bio; print(Bio.__version__)\""
        command = manifest.environment_command("bio", probe)
        path = command.split("bash ", 1)[1]
        with open(path, encoding="utf-8") as handle:
            self.assertEqual(handle.read(), probe)


class ShellQuotingTest(unittest.TestCase):
    """The R code has to survive the shell on its way to R.

    The first version put the R expression in shell single quotes while the
    R code itself used single quotes, so the shell ended the quoting early
    and R received code with its quotes stripped. R reported a syntax error,
    the manifest recorded "R NOT FOUND", and the gate passed it.
    """

    def test_r_expression_reaches_the_shell_intact(self):
        """The argument R receives must still have its quotes."""
        expression = (
            "cat(sprintf('%-22s %s\\n', p, "
            "tryCatch(as.character(packageVersion(p)), error=function(e) 'NOT FOUND')))"
        )
        packages = ", ".join(f"'{name}'" for name in manifest.R_PACKAGES)
        command = (
            f"micromamba run -n r Rscript -e "
            f'"for (p in c({packages})) {expression}"'
        )
        delivered = subprocess.run(
            ["sh", "-c", f"printf '%s' {command.split('Rscript -e ', 1)[1]}"],
            capture_output=True,
            text=True,
            check=False,
        ).stdout
        self.assertIn("'limma'", delivered)
        self.assertIn("sprintf(", delivered)
        self.assertIn("NOT FOUND'", delivered)
        self.assertNotIn("Rscript", delivered)


class ScriptTest(unittest.TestCase):
    """Both scripts have to be runnable from the command line."""

    def test_diff_script_runs(self):
        """The diff script runs on two manifests and exits 0 when they agree."""
        with tempfile.TemporaryDirectory() as tmp:
            old = os.path.join(tmp, "a.txt")
            new = os.path.join(tmp, "b.txt")
            for path, text in ((old, MANIFEST_A), (new, MANIFEST_B)):
                with open(path, "w", encoding="utf-8") as handle:
                    handle.write(text)
            result = subprocess.run(
                [
                    sys.executable,
                    os.path.join(REPO_ROOT, "scripts", "diff_manifests.py"),
                    old,
                    new,
                ],
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertIn("agree on every tool version", result.stdout)


if __name__ == "__main__":
    unittest.main()
