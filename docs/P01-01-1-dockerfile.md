# P01-01.1 — analysis container

**Status:** complete, 2026-10-02. **Parent:** P01-01. **Estimate:** 2 days.

## What was built

`Dockerfile`, a two-stage build:

| Stage | Contains |
|---|---|
| `builder` | compilers and header libraries, not shipped |
| runtime | the analysis environment, no build toolchain |

Every version in the pre-registered methods table is pinned: `diamond 2.1.8`,
`liftoff 1.3.0` (pinned to commit `b8a41b0`, because Liftoff has no tagged
release that matches), `BUSCO 5.7.1`, `HISAT2 2.2.1`, `InterProScan
5.70-102.0`, `OrthoFinder 2.5.4`, `MAFFT 7.505`, `trimAl 1.4.rev22`,
`IQ-TREE 2.2.6`, `R 4.4`, `limma 3.60`, `edgeR 4.0`, `metafor 4.4`.

## Why the manifest matters

The image writes `/opt/aplysia/ENVIRONMENT.txt` at build time, listing every
tool and its resolved version. `scripts/environment.sh` prints it. Every analysis
run in this project starts by emitting that manifest, so a result can be tied
to exact tool versions without reconstructing the image by hand.

## Data layout

```
/workspace/data/raw        gitignored; inputs re-fetchable from the accessions in data/manifest.tsv
/workspace/data/derived    generated; not committed
/workspace/results         generated result files, committed
/workspace/figures         generated figures, committed
```

## Verification not yet performed

The image has not been built in this environment. Subtasks **P01-01.2** and
**P01-01.3** are the build and the build-twice-and-diff, and they are the
subtasks that will fail if a pinned version does not resolve on conda-forge or
bioconda. Treat those two as the real test of this file.

## Known risk

`liftoff` and `OrthoFinder` install from git with `--no-deps`, so a dependency
that moved between the conda package and the git checkout will surface at
runtime rather than at build time. P01-01.2 is where that shows up.
