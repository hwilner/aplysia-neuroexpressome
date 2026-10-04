# P01-01.2 — image build: blocked locally, pins corrected, build moved to CI

**Status:** **blocked**, 2026-10-03. **Parent:** P01-01. **Estimate:** 1 day.
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

**P01-01.2 is still Blocked.** Three of four environments are proven; the image
is not built. Nothing in this project is reproducible until it is.

## What a reviewer should take from this

The image has never been built. The pins are verified to exist; the build is
wired to run on every push to `main`; and the first CI run is the real
verification. Until that run is green, no result in this project should be
treated as reproducible, and the Dockerfile should be treated as unverified
however carefully it has been written.

## Next

- **P01-01.3** — the second build and the version diff. Unblocked once the
  first CI run is green.
- **P01-01.4** — push the image and record the digest. Unblocked once P01-01.3
  is done.
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
  solved in its own step on a bare runner, with no Docker, so a conflict names
  the ecosystem and prints the solver's message. The image build waits on it.
