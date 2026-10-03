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
