# P01-01.5 — the lock files

**Subtask:** P01-01.5 — pin the resolved package closure with an explicit lock file.
**Status:** complete.
**Date:** 2026-11-06.

## What this subtask does

The image installs from a lock file instead of being solved for at build time.

Until now the Dockerfile declared the direct tools it wanted — `python=3.11`,
`diamond=2.1.8`, `mafft=7.525` and so on — and the solver worked out the rest
each time the image was built. That pins the tools. It does not pin the
environment around them, and the difference is not academic.

Between the build verified in P01-01.3 and the release in P01-01.4, five
packages in the closure moved while none of the pinned tools did. The diff is
recorded in `docs/closure-drift.txt`:

| package | in the P01-01.3 build | in the released image |
| --- | --- | --- |
| `certifi` | `pyhd8ed1ab_0` | `pyhd8ed1ab_3` |
| `pip` | `pyh8b19718_0` | `pyh8b19718_2` |
| `libnghttp2` | `1.70.0` | `1.71.0` |
| `r-future` | `1.80.0` | `1.82.0` |
| `r-openssl` | `2.4.2` | `2.5.0` |

Rebuilding the same Dockerfile today moves seven more. The `bio` environment
still resolves to exactly 285 packages, the same 285, and seven of them come
back at a different version or build string:

| package | in the released image | resolved locally on 2026-11-06 |
| --- | --- | --- |
| `kernel-headers_linux-64` | `6.12.0/he073ed8_6` | `5.14.0/he073ed8_3` |
| `libblas` | `11_h4a7cf45_openblas` | `12_h4a7cf45_openblas` |
| `libcblas` | `11_h0358290_openblas` | `12_h0358290_openblas` |
| `liblapack` | `11_h47877c9_openblas` | `12_h47877c9_openblas` |
| `libuuid` | `hcfc3c73_0` | `hcfc3c73_1` |
| `pandas` | `3.1.0` | `3.1.1` |
| `sysroot_linux-64` | `2.39/hc4b9eeb_6` | `2.34/h087de78_3` |

`kernel-headers_linux-64` and `sysroot_linux-64` move together: the two
solvers picked different consistent pairs of the same two constraints. Both
are valid solves. That is exactly the problem. A valid solve is not the same
thing as the same solve, and a rebuild that lands on the other one produces
an image whose closure nobody has checked.

## The format

Each environment has a lock file under `lock/`, in conda's explicit format.
The file starts with `@EXPLICIT` and every following line is the URL of one
package, which carries the channel, the platform and the file extension:

```
@EXPLICIT
https://conda.anaconda.org/conda-forge/linux-64/_openmp_mutex-4.5-20_gnu.conda
https://conda.anaconda.org/bioconda/noarch/busco-5.7.1-pyhdfd78af_1.tar.bz2
```

A URL names the package, its exact version and its build string, so the
closure cannot move under the image.

The header carries the pins the closure was solved from, and the exact
versions those pins resolved to:

```
# PINS: python=3.11 biopython=1.83 diamond=2.1.8 ...
# RESOLVED: biopython=1.83 busco=5.7.1 diamond=2.1.8 ...
```

`PINS` is the declaration of intent and lives in the Dockerfile, as a comment
above the install. `RESOLVED` is what the closure actually contains, and it
is what the check compares against, so a lock that has drifted away from the
pins is caught rather than believed.

The four locks are:

| file | environment | packages |
| --- | --- | --- |
| `lock/bio.txt` | the analysis tools | 285 |
| `lock/tree.txt` | the phylogeny tools | 18 |
| `lock/r.txt` | the statistics | 300 |
| `lock/ips.txt` | InterProScan | 125 |

## How the Dockerfile uses it

The pins stay in the Dockerfile, as a comment above each install:

```dockerfile
# PINS: python=3.11 biopython=1.83 diamond=2.1.8 liftoff=1.3.0 busco=5.7.1 ...
RUN micromamba create -y -n bio --file /opt/aplysia/lock/bio.txt \
    && micromamba clean --all --yes
```

`scripts/environments.py` reads the pins from the comment, so the manifest,
the continuous-integration matrix and the lock check all still know what the
environment is for.

## How it is checked

`.github/workflows/build-image.yml` checks the lock at three levels, and the
third one is the definition of done.

1. **The lock satisfies the pins.** `scripts/lock.py check` fails when a
   pinned package is absent from the lock. A lock that has stopped matching
   the Dockerfile is a broken lock.

2. **The lock installs.** Each environment is installed from its lock file in
   its own job, so a lock that will not install fails here, with the
   installer's own message, rather than inside a buildkit layer.

3. **The built image matches the lock.** After the image is built, the
   closure inside each environment is extracted and compared with the lock
   file. This is the check that says what P01-01.5 asks for: *the image is
   built from it*.

The pins are also still solved from, but that step is advisory. The image is
built from the lock, so a pin the channels have dropped does not break the
image; it only narrows what can be done the next time the closure has to
move. It is reported as a warning rather than swallowed, because a pin that
quietly stopped solving is the same class of drift this subtask exists to
stop.

## Regenerating a lock

A lock is regenerated when a pin changes, or when the closure has to move for
a reason the pins do not explain.

```bash
# 1. Solve the environment with the pins from the Dockerfile.
micromamba create -y -n bio -c conda-forge -c bioconda \
    python=3.11 biopython=1.83 diamond=2.1.8 ...

# 2. Write the lock.
python3 scripts/lock.py generate \
    --env bio \
    --pins "python=3.11 biopython=1.83 diamond=2.1.8 ..." \
    --from <explicit spec> \
    --output lock/bio.txt

# 3. Check it.
python3 scripts/lock.py check --env bio --pins "..." --lock lock/bio.txt
```

`scripts/lock.py compare --lock lock/bio.txt --from <explicit spec>` reports
how a resolved environment differs from a lock, which is the tool for the
question "what moved, and when".

## What this does not claim

**The image is still not bit-for-bit reproducible.** Its configuration carries
a creation timestamp, so every rebuild produces a new digest regardless of
whether the closure moved. The lock fixes the *environment*; the digest is
still a property of the build, not of the content. Comparing digests across
builds remains the wrong test, and the release workflow keeps recording the
digest of the run that actually pushed the image.

## What the build proved

The build that carried these locks ran on 2026-11-06, and every check in it
passed:

| check | result |
|---|---|
| the lock satisfies the pins | all four environments |
| the lock installs | all four environments |
| the closure inside the built image equals the lock | 285, 18, 300 and 125 packages, identical |
| the two independent builds agree on the tool versions | all 26 |
| the pinned tool versions match the P01-01.3 manifest | all 26 |

The image was then released as
`sha256:3bf4416d3dc36a5feb99d988f566498881650d5cb985723c6cd744bef3c0344d`,
tag `sha-6fe3061`, and the closure in the pushed image was compared against
the lock file again, from the release run, with the same result.

The locks were resolved with micromamba 2.10.0, while the image pins
micromamba 2.9.0. The explicit format is stable across both, and the build
is what proved the image accepts these locks.

**What the build did not prove:** that the image is reproducible. It proved
that the environment is. The digest still moves, because the image's
configuration carries a creation timestamp, so the image built from this lock
on 2026-11-06 and the image built from the same lock on any other day have
the same closure and different digests.

## Files

| file | what it is |
| --- | --- |
| `lock/bio.txt`, `lock/tree.txt`, `lock/r.txt`, `lock/ips.txt` | the four locks |
| `scripts/lock.py` | generates, checks and compares the locks |
| `tests/test_lock.py` | tests for the locks and the tool |
| `Dockerfile` | installs from the locks; the pins are in the comments |
| `scripts/environments.py` | reads the pins from the comments |
| `.github/workflows/build-image.yml` | checks the locks and the built image |
