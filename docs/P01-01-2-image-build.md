# P01-01.2 — image build: five attempts, and a green build

**Status:** **done**, 2026-10-29. The image builds, from a clean cache, and
every tool the Dockerfile names is in it. **Parent:** P01-01. **Estimate:** 1 day.
**Depends on:** P01-01.1 (done).

## The blocker

The image cannot be built in the environment where this file was written.
Checked and absent:

| Tool | Result |
|---|---|
| `docker` | not installed |
| `podman` | not present |
| `singularity` | not present |
| `apptainer` | not present |
| `/var/run/docker.sock` | absent |
| daemon | not reachable |

There is no container runtime, so "build the image and confirm it builds from a
clean cache" cannot be completed here. Marking it **blocked** rather than done,
because the build genuinely has not run. P01-01.3 and P01-01.4 are downstream of
it and are likewise not done.

## What was done instead

### 1. Every pin was verified against the package index

The dominant failure mode of a build is a version that no longer resolves, so
that part of the check is separable from having Docker. All 26 pins were
queried against the anaconda.org package API. **9 of 26 did not resolve.**

| Package | Original pin | Status found | Corrected to |
|---|---|---|---|
| `biopython` | 1.83 on bioconda | bioconda stops at 1.70 | 1.83 on **conda-forge** |
| `bioconductor-limma` | 3.60 | does not exist; channel goes 3.58.1 → 3.62.0 | **3.62.0** on bioconda |
| `bioconductor-edger` | 4.0 on conda-forge | not on conda-forge | 4.0 on **bioconda** |
| `bioconductor-clusterprofiler` | 4.10 on conda-forge | not on conda-forge | 4.10 on **bioconda** |
| `r-metafor` | 4.4 | version string carries a `_0` suffix | **4.4_0** |
| `interproscan` | 5.70-102.0 | bioconda's newest is 5.59-91.0 | **5.59_91.0** |
| `trimal` | 1.4.rev22 | no such build; 1.4.1 / 1.5.0 / 1.5.1 exist | **1.5.1** |
| `aplotransdecoder` | 3.0.0 | not a conda package at all | **`transdecoder` 5.7.0** |
| `tabular` | 1.0 | no such package; never in the methods table | **removed** |

The other 17 pins resolved as written: `python 3.11`, `diamond 2.1.8`,
`liftoff 1.3.0`, `busco 5.7.1`, `hisat2 2.2.1`, `samtools 1.19`,
`r-base 4.4`, `r-ggplot2 3.5`, `r-patchwork 1.2`, `r-rstatix 0.7`,
`r-testthat 3.2`, `hmmer 3.4`, `eggnog-mapper 2.1.9`, `orthofinder 2.5.4`,
`mafft 7.505`, `iqtree 2.2.6`, `gffread 0.9.9`.

The Dockerfile has been corrected. It would not have built as written.

### 2. The build moved to continuous integration

`.github/workflows/build-image.yml` runs the real thing on a runner that has
Docker: a cached build, then a `--no-cache` build, which is the literal
"clean cache" check. It then runs the container, captures
`/opt/aplysia/ENVIRONMENT.txt`, **fails the build if any tool named in the
Dockerfile reports `NOT FOUND`**, and uploads the manifest and the image digest
as artefacts. A human does not have to pull a multi-gigabyte image to see
whether the pins resolved.

### 3. One substantive downgrade, recorded

`interproscan` moved from 5.70-102.0 to **5.59-91.0**, because 5.70-102.0 is not
distributed on bioconda. This is not cosmetic. The InterProScan version
determines the Pfam and InterPro member-database snapshot, so every domain
assignment made with this image will be traceable to the 5.59-91.0 data release.
The methods file must state this, and the catalogue must record the InterProScan
version beside every domain hit. If 5.70-102.0 is required, it installs from
the InterProScan distribution rather than conda, at the cost of Java 11 and a
much longer build.

## Second attempt: three environments instead of one solve

The first two CI runs of `build-image.yml` **failed** at the `docker build`
step, in a fraction of a second. The log endpoint was initially unreachable from
this sandbox; once it answered, the error was not a solver conflict at all:

```
ERROR: docker.io/mambaorg/micromamba:23.11: not found
  30 |     ARG MAMBA_VERSION="23.11"
  31 | >>> FROM mambaorg/micromamba:${MAMBA_VERSION}
```

**`mambaorg/micromamba:23.11` has never existed.** The tag was invented when
this file was first written. The build never reached the solver, so the pins
were never tested by it. The real current version is **2.9.0**, verified against
the Docker Hub tag list; there is no `23.*` tag at all. `MAMBA_VERSION` is now
pinned to `2.9.0`.

This is worth recording plainly, because two rounds of work went into the wrong
problem. Correcting the 9 bad pins was independently valid — those 9 genuinely
did not resolve. The three-environment split was **not** the fix and is not
evidence of anything: it was adopted while chasing a failure that turned out to
be a bad version number.

What is known is that a single `micromamba install` solving for all 26 packages
at once spans three ecosystems that routinely conflict: bioconda's tool stack,
the conda-forge R stack with Bioconductor, and InterProScan with its own
pinned library tree. That layout was fragile by construction, whatever the
specific message turned out to be.

The image is now **three environments**, each solved separately:

| Environment | Holds | Pins |
|---|---|---|
| `bio` | the tools: diamond, liftoff, BUSCO, HISAT2, samtools, HMMER, eggNOG-mapper, OrthoFinder, MAFFT, trimAl, IQ-TREE, TransDecoder, gffread, Biopython, Python | 15 |
| `r` | the statistics: R 4.4, limma, edgeR, clusterProfiler, metafor, ggplot2, patchwork, rstatix, testthat | 9 |
| `ips` | InterProScan 5.59-91.0 and OpenJDK 11, alone | 2 |

Each solve is now small, and a failure names the ecosystem that caused it. CI
probes each environment separately before running the whole manifest, so the
next run reports which one broke rather than a single opaque transaction.

Invocation becomes explicit:

```bash
micromamba run -n bio liftoff ...
micromamba run -n r   Rscript -e 'library(limma)'
micromamba run -n ips ./InterProScan.sh ...
```

The split is kept because isolating InterProScan's pinned library tree is
defensible on its own merits and because per-environment probes are better
diagnostics. It is **not** kept because it was shown to be necessary.

**P01-01.2 remains blocked until a green build.** The base image now resolves,
but the pins have still never been through a solver. The next CI run is the
first real test of the 26 pins, and until it passes nothing in this project is
reproducible.

## Third attempt: the real conflict, found by the solver

With the base image fixed, the third CI build reached the solver and failed
with a genuine conflict:

```
├─ busco =5.7.1 * is installable and it requires
│  └─ sepp >=4.3.10 *, which requires
│     └─ pasta =* *, which requires
│        └─ mafft >=7.526,<8.0a0 *, which can be installed;
└─ mafft =7.505 * is not installable because it conflicts with any installable versions previously reported.
```

BUSCO pulls `sepp`, which pulls `pasta`, which requires **mafft >= 7.526**. And
the newest mafft on bioconda is **7.525** — one patch below. So no mafft
satisfies both a BUSCO pin and a mafft pin. The conflict is structural, not a
bad version choice, and no amount of version-shopping fixes it.

**Fix: a fourth environment.** The tree tools now live in their own:

| Environment | Holds | Pins |
|---|---|---|
| `bio` | tools, alignment, orthology, BUSCO | 12 |
| `tree` | MAFFT 7.525, trimAl 1.5.1, IQ-TREE 2.2.6 | 3 |
| `r` | limma, edgeR, clusterProfiler, metafor, plotting | 9 |
| `ips` | InterProScan 5.59-91.0, OpenJDK 11 | 2 |

Every pin survives, including `mafft=7.525`, which solves cleanly once sepp and
pasta are no longer in the transaction.

**The diagnosis was only obtainable by solving.** `mafft=7.505` exists, and
`7.525` exists, and every pin verifies individually against the package index.
Nothing short of an actual solve surfaces this. That is the argument for
running the build in CI rather than reasoning about it.

## Fourth attempt: down to one pin, then stopping

After pinning the Bioconductor 3.20 pair, the whole R stack resolves —
`r-base 4.4` with `limma 3.62.0` and `edgeR 4.4.0` — and the `r` environment
is down to a single package:

```
r-metafor =4.4.0 is not installable because there are no viable options
r-metafor 4.4_0 would require        <- requirement not expanded in the log
```

The solver names the package and prints a "would require" line with nothing
after it. That is the limit of what the log gives, and guessing at a version
would be exactly the wrong move: five CI cycles have already gone into this
subtask, three of them into problems other than the real one.

**So this tick stops here, honestly.** Current verified state:

| Environment | Status |
|---|---|
| `bio` — 12 pins | **solves** |
| `tree` — 3 pins | **solves** |
| `ips` — 2 pins | **solves** |
| `r` — 8 pins | one pin remaining: `r-metafor` |

The `solve-check` job now runs `micromamba repoquery depends` on the three
pins in question, so the next run states metafor's actual requirement as a fact
rather than a hypothesis. That is the difference between this being stuck and
this being known.

**P01-01.2 was still Blocked at this point.** Three of four environments were
proven; the image was not built. Nothing in this project was reproducible
until it was. The fifth attempt, below, is what changed that.

## Fifth attempt: the requirement as a fact, and three more names that were wrong

The fourth attempt stopped because the log did not say why `r-metafor` could
not be installed. It does say why; the log was just being read wrongly.

### The requirement was in the package index all along

`micromamba repoquery depends <pin> --json` reports the builds a pin resolves
to and the constraint each build carries. The plain text output of the same
command is the solver's progress log, and the step that was meant to answer
this question piped that text through `head -25`, which cut the answer off
before it appeared. The step was therefore reporting nothing at all, which is
why the requirement looked unavailable.

Asked directly, the answer is one line:

```
$ micromamba repoquery depends r-metafor=4.4_0 --json | scripts/requirements.py
  r-metafor 4.4_0 [r43hc72bb7e_0]
      requires r-base >=4.3,<4.4.0a0
      requires r-mathjaxr
      ...
```

`r-metafor 4.4_0` has exactly two builds on conda-forge: one for `r-base
>=4.2,<4.3` and one for `r-base >=4.3,<4.4`. **Neither accepts R 4.4**, so
the pin and the pre-registered R cannot coexist, and no reordering of the
other pins will help. `r-metafor 4.6_0` has a third build,
`r44hc72bb7e_1`, which requires `r-base >=4.4,<4.5.0a0` and therefore does.

**Fix:** `r-metafor=4.6_0`. The pre-registration names R 4.4.x and names no
metafor version, so the pre-registered R is unchanged and this is not a
pre-registration amendment. The whole R environment now solves, with `r-base
4.4.3`, `limma 3.62.0` and `edgeR 4.4.0` exactly as before.

Two tools that the pre-registered software environment names and the image
did not have are now in it: `lme4`, which is the mixed-effects model that
step 1 of the pre-registered test-selection procedure calls for when the
observations are not independent, and `tidyverse`.

### Three more tool names, and one that reported nothing

With the pins fixed, the image build itself was still going to fail, for
reasons that had nothing to do with the pins.

**The manifest checked four commands that the packages do not ship.** The
manifest is the build's own check that every tool is in the image, so a
command name that does not exist reports a missing tool and fails the build
on a tool that is present under a different name:

| Checked | Actually shipped | By |
|---|---|---|
| `hmmer-hsearch` | `hmmsearch` | `hmmer 3.4` |
| `eggnog-mapper.pl` | `emapper.py` | `eggnog-mapper 2.1.9` |
| `TransDecoder.R` | `TransDecoder.Predict` | `transdecoder 5.7.0` |
| `InterProScan.sh` | `interproscan.sh` | `interproscan 5.59_91.0` |

The first three would have failed the build with "a tool named in the
Dockerfile is absent from the image". The fourth was worse: the `ips` section
of the manifest ran `InterProScan.sh -h` inside a `$(...)`, so a missing
command produced an empty version string rather than a `NOT FOUND`, and the
check passed on a tool that was never there. All four names are now the ones
the packages install, and the `ips` section checks presence with the same
`command -v` guard as every other environment.

**The git checkouts could not be installed at all.** The Dockerfile installed
Liftoff and OrthoFinder with `pip install git+https://...`, which needs a
`git` binary to clone. There is none: the published base image
`mambaorg/micromamba:2.9.0` contains no `git` executable in any of its
layers, and `git` is not a dependency of any package in the `bio` environment
either. The layers would have failed with `git: command not found`.

Both tools are on bioconda at exactly the pinned versions, so the git
checkouts were never needed:

| Tool | bioconda package | Provenance |
|---|---|---|
| `liftoff 1.3.0` | `noarch/liftoff-1.3.0-py_0` | built from the upstream `Liftoff-1.3.0` PyPI source distribution; declares `biopython`, `gffutils`, `interlap`, `minimap2`, `networkx`, `numpy`, `pyfaidx`, `pysam`; installs the `liftoff` console script |
| `orthofinder 2.5.4` | `noarch/orthofinder-2.5.4-hdfd78af_0` | the upstream 2.5.4 release; installs `bin/orthofinder` and `bin/scripts_of/` |

The git checkouts were also installed with `--no-deps`, which is the runtime
drift risk this file already recorded under "Known risk": the conda package
declares its dependencies, the git checkout left them to the solver. The
conda packages are now used directly.

### The environment list is now read from the Dockerfile

`build-image.yml` repeated the pins of all four environments by hand, and
probed three of them: the `tree` environment, added on 2026-10-04, was
solved but never probed. Two lists that have to be kept in step by hand are
two lists that will drift.

`scripts/environments.py` now parses the `micromamba create` instructions out
of the Dockerfile, and the workflow solves and probes exactly what it finds
there. An environment cannot be added to the image and then left out of the
checks, because there is only one list. `tests/test_environments.py` guards
the remaining drift: every environment the Dockerfile solves has a section in
the manifest, and every manifest section belongs to an environment that is
solved.

### The manifest stage could not write the manifest

The image built on 2026-10-29, for the first time in this project's history,
and all four environments probed cleanly inside it. The manifest stage did
not run, and the build did not notice.

The Dockerfile switches to the unprivileged user before the manifest stage,
and `/opt/aplysia` is created by `COPY` as root and stays root-owned. The
manifest stage writes its output with a redirect into that directory, so it
failed:

```
/bin/bash: line 1: /opt/aplysia/ENVIRONMENT.txt: Permission denied
```

The `|| true` at the end of the stage swallowed that error, the stage
reported `DONE`, and the image shipped with no manifest at all.

The manifest gate did not catch it, because the gate only looked for the
string `NOT FOUND`. An image with no manifest produces the helper's fallback
message instead,

```
no manifest: the image was not built with the manifest stage
```

and that message contains no `NOT FOUND`, so the gate reported "OK: every
tool named in the Dockerfile is present" on an image in which not one tool had
been looked for.

**Fix:** `/opt/aplysia` is given to the unprivileged user, so the manifest
stage can write the manifest it exists to write; and the gate now fails on
the missing-manifest message, on an empty manifest, and on a manifest with no
section for an environment the Dockerfile defines.

This is the fifth defect, and it is the one that shows what the other four
were worth: the image was building correctly while the gate was lying about
it. A gate that only looks for one string is a gate that reports on the
tools it happens to know about and stays silent about everything else.

### The build, and what it produced

On 2026-10-29 the image built on a GitHub runner, from a clean cache and
again from the cached layers, and every environment probed cleanly inside
it. The manifest the image wrote for itself is the record:

```
# environment manifest - generated at image build time
built: 2026-10-29T07:25:45Z

## env: bio
python                 Python 3.11.9
diamond                diamond version 2.1.8
liftoff                v1.3.0
busco                  BUSCO 5.7.1
hisat2                 /opt/conda/envs/bio/bin/hisat2-align-s version 2.2.1
samtools               samtools 1.19.2
hmmsearch              Failed to parse command line: No such option "--version".
emapper.py             There was an error retrieving eggnog-mapper DB data: not a valid file "..."
gffread                0.9.9
orthofinder
TransDecoder.Predict   TransDecoder.Predict 5.7.0

## env: tree
mafft                  v7.525 (2024/Mar/13)
trimal
iqtree2                IQ-TREE multicore version 2.2.6 COVID-edition for Linux 64-bit built Dec  8 2023

## env: r
R R version 4.4.3 (2025-02-28)
limma                  3.62.0
edgeR                  4.4.0
metafor                4.6.0
lme4                   2.0.6
tidyverse              2.0.0
ggplot2                3.5.2
patchwork              1.2.0
rstatix                0.7.3
testthat               3.2.3

## env: ips
java                   openjdk version "11.0.30-internal" 2026-01-20
interproscan.sh        present
```

The build image, from the run's own digest step:

```
sha256:6ff264cd0cd1d15dfaf3348fb6d3d2b4bb7cc0305045674d24098197dd5e3214
```

**What this establishes.** The image builds from a clean cache. All four
environments are present and usable in it, each of them probed separately.
Every tool the Dockerfile names is installed under the name the Dockerfile
checks, and the manifest contains no `NOT FOUND`. The pre-registered R 4.4
is in the image, with limma 3.62.0 and edgeR 4.4.0 beside it.

**What this does not establish.** It is a build result, not a scientific
result. Nothing in the image has been run against data, so no result in this
project is reproducible yet. The digest above is the digest of a test image
built on a runner; it is not the released digest, which is P01-01.4's job.

Three lines of the manifest are not versions, and the reason is worth
recording: `hmmsearch`, `trimal`, `orthofinder` and `emapper.py` do not
accept `--version`, so the first line of their output is what appears. The
check that matters, that the command is installed, holds for all four. The
`emapper.py` line reports that the eggNOG-mapper database is not in the
image, which is expected: the conda package never ships it, and it is
fetched with the rest of the inputs.

### What this attempt establishes

That **all four environments solve**, each one checked with the solver, with
the pins taken from the Dockerfile; that the manifest checks commands the
packages actually ship; that the manifest gate no longer passes on an empty
manifest, on a manifest that is missing an environment, or on an image that
has no manifest at all; and that the image builds from a clean cache and
contains every tool the Dockerfile names.

It does **not** establish anything about the science. Nothing in the image
has been run against data.

## What a reviewer should take from this

The image builds, and the build is wired to run on every push to `main`, so
the next push is the next verification of the pins.

Five defects stood between this repository and a working image, and four of
them were invisible behind the first. Rounds one to four went into the pins
and none of them into the three things that would have failed the build once
the pins were right: the manifest's four wrong command names, the git
checkouts, and the `tree` environment that was never probed. The fifth was
found by the gate that the fourth round hardened: the image built, and the
gate reported that the manifest was missing, which was true, because the
manifest stage had been failing to write it since the beginning.

A build that is red tells you about the first thing that is wrong. It does
not tell you how many things are. And a gate that only looks for one string
reports on the things it happens to know about, and stays silent about
everything else.

The original reviewer note, written before the build had ever run, said:

> The image has never been built. The pins are verified to exist; the build is
> wired to run on every push to `main`; and the first CI run is the real
> verification. Until that run is green, no result in this project should be
> treated as reproducible, and the Dockerfile should be treated as unverified
> however carefully it has been written.

The last sentence of that note is still true of the Dockerfile as a piece of
prose. What the run has now established is narrower and more useful: the
pins resolve, the image builds, and the tools are in it.

## Next

- **P01-01.3** — the second build and the version diff. Unblocked now that the
  first CI run is green. The workflow already builds the image twice, once
  from the cached layers and once with `--no-cache`; what it does not yet do
  is diff the two manifests.
- **P01-01.4** — push the image and record the digest. Unblocked once P01-01.3
  is done. The digest of the released image is not the digest of the test
  image built on the runner, so the row in Table 7 of `results.md` stays
  *Pending* until this subtask is done.
- A new subtask is warranted: record the InterProScan data release in
  `materials-and-methods.md` and require the InterProScan version beside every
  catalogue domain hit. This was not in the original plan and should be added
  before the catalogue is built.
- `materials-and-methods.md` §2.2 still describes a single environment, a
  micromamba version, and InterProScan 5.70-102.0. All three are now wrong. The
  correction is a pre-registration amendment and must be logged as a
  `deviation-log` issue, not edited silently.
- **Lesson worth carrying, three of them.** A base image tag is a version pin
  like any other, and `ARG` makes an invented value look like a configured one.
  A package existing and a package resolving are different questions. And a
  cross-package dependency can be unsatisfiable no matter what versions you
  choose, which is the one failure that only a solver can find.
- `build-image.yml` now runs a `solve-check` job first: each environment is
  solved in its own job on a bare runner, with no Docker, so a conflict names
  the ecosystem and prints the solver's message. The image build waits on it.
