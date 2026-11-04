# P01-01.4 — push the image and record the digest in the README

**Parent:** P01-01. **Status:** in progress. **Started:** 2026-11-04.

## What the subtask asks

Push the analysis image to a registry and record its digest in the README of
`hwilner/aplysia-neuroexpressome`.

## The distinction that matters

The digest of the **released** image is not the digest of a test image built
on a runner. The first is what somebody else would actually pull; the second
is what happened to exist at one moment on one machine. P01-01.2 and
P01-01.3 both produced the second kind, and recording one of them as if it
were the first would be a false claim of reproducibility.

So the release has to be a separate act from the verification, and the
digest that gets written down has to be the digest of what was pushed.

## How it is done

**`.github/workflows/release-image.yml`** builds the image, logs in to GHCR,
pushes it, and then:

1. reads the digest **from the push itself** — the `digest: sha256:…` line
   the registry prints — rather than from the local image, which is the
   digest of the local image;
2. pulls the pushed image back **by its digest** and runs the manifest
   generator inside it;
3. diffs that manifest against `docs/manifest-build-1.txt`, the manifest
   verified in P01-01.3. If the pins no longer resolve to the same tool
   versions, the release fails rather than publishing a digest for an
   environment nobody checked;
4. writes the digest into the README, from the same run, and commits it.

The digest is never transcribed by hand. A digest typed by a person is a
digest that can be typed wrongly, and a wrong digest in a README is worse
than no digest at all: it is a claim of reproducibility that is false.

**`scripts/record_release.py`** writes the README's released-image region.
It is idempotent, because the workflow runs on every push that touches the
Dockerfile and a workflow that fails because the README already mentions the
digest is a workflow that gets switched off. It refuses to write into a
README that has no region, rather than appending one somewhere unexpected.

**`scripts/diff_manifests.py`**, from P01-01.3, does the verification.

## What is recorded

| Field | Where it comes from |
|---|---|
| Image | `ghcr.io/hwilner/aplysia-neuroexpressome` |
| Digest | the registry's own answer to the push |
| Tag | `sha-<short commit>` — mutable, for humans; the digest is for machines |
| Built from commit | the commit that was built |
| Released | UTC timestamp of the push |
| Tool manifest | `docs/released-manifest.txt`, the manifest of the image that was pushed |

## What is verified and what is not

Verified locally, without a container: 51 unit tests, including that the
recorder is idempotent, that it refuses a README without the region, that
the pull command is a pull **by digest** rather than by a mutable tag, and
that the README in the repository has the region.

Not verified until the workflow runs: that the push succeeds, that the
digest read from the push matches the digest of the image that was pulled
back, and that the released manifest matches the verified one.

## Note for the next person

The release workflow needs `packages: write` and `contents: write`. The
`contents: write` is for the commit that records the digest, and it is
safe: a push made with `GITHUB_TOKEN` does not trigger further workflow
runs, so the commit that writes the README cannot start the release again.

A package pushed to GHCR is private by default even when the repository is
public. The workflow tries to make it public, but the `GITHUB_TOKEN` may not
be permitted to change visibility; if it is not, the visibility has to be
set from the account that owns the package. A private image is still a
valid release — the digest is still the digest — but it is not a public one,
and the README should not imply otherwise.

## What the release runs found

**The first run failed on an unbound variable.** `echo "IMAGE=…" >>
"$GITHUB_ENV"` makes the variable available to the *later* steps of a job,
not to the rest of the block that wrote it, and under `set -u` reading it back
is a failed build. `scripts/check_workflow.py` now looks for that, so the
next run of the same mistake is caught before it costs a run.

**The second run pushed the image and then failed the verification.** The
image was built, pushed, and pulled back by its digest — and the manifest of
the pulled image did not match the verified one:

```
-  certifi       2026.10.23  pyhd8ed1ab_0   conda-forge
+  certifi       2026.10.23  pyhd8ed1ab_3   conda-forge
-  pip           26.2.2      pyh8b19718_0   conda-forge
+  pip           26.2.2      pyh8b19718_2   conda-forge
-  libnghttp2    1.70.0      hc5e5977_0     conda-forge
+  libnghttp2    1.71.0      hc5e5977_0     conda-forge
-  r-future      1.80.0      r44hacb3a79_0  conda-forge
+  r-future      1.82.0      r44hacb3a79_0  conda-forge
-  r-openssl     2.4.2       r44h68c19f5_0  conda-forge
+  r-openssl     2.5.0       r44haecc533_0  conda-forge
```

**Not one of the 25 pinned tools differs.** Every difference is in a
transitive dependency, and every one of them is conda-forge moving between
2026-11-02 and 2026-11-04: two rebuilds and three version bumps.

This is the important finding of the subtask, and it is two findings.

**The gate was wrong.** It compared the whole manifest, so a moving
transitive closure failed the release. But a moving closure does not make a
release wrong — a digest fixes an image exactly, and the released image *is*
exactly what was verified. What the drift breaks is the ability to
*rebuild* from the Dockerfile, which is a different claim. The gate is now
`diff_manifests.py --tools-only`: the pinned tools have to be the ones that
were verified, and the closure drift is recorded rather than fatal.

**The build is not reproducible across time.** Pinning the direct tools does
not pin the environment. `libnghttp2` is not a pin in this project and it
still changed under the build, and `r-future` is three minor versions ahead
of what the verified build had. A rebuild from the same Dockerfile tomorrow
would produce a different closure. That is now **P01-01.5**, which pins the
resolved closure in an explicit lock file.

## What the release therefore establishes

That the released image, pulled by its digest, runs the same 25 pinned tools
as the image verified in P01-01.3. And it records the drift in the
transitive closure, so that the difference between "reproducible" and
"reproducible if the lock file is used" is written down rather than
assumed.

## The release as it stands

| | |
|---|---|
| Image | `ghcr.io/hwilner/aplysia-neuroexpressome` |
| Digest | `sha256:a18d6914ecdd9ce12d906adf2976a2f773fad14af536fe8dfd4362e6fade125b` |
| Tag | `sha-14370da` |
| Visibility | public |
| Pull | `docker pull ghcr.io/hwilner/aplysia-neuroexpressome@sha256:a18d6914e…` |
| Tool versions | identical to the manifest verified in P01-01.3 — all 26 |
| Package closure | moved; recorded in `docs/closure-drift.txt` |

Verified from outside the workflow: the registry serves that digest to an
**anonymous** pull, and its own `docker-content-digest` header is the digest
the README records. The digest was written by the run that pushed the image,
so it cannot have been transcribed wrongly.

Three images are in the registry: `sha-36527be` from the first attempt,
which failed on the unbound variable; `sha-e0e0d02` from the second, which
pushed successfully and then failed the over-strict verification; and
`sha-14370da`, the release.

## One wart worth naming

The release workflow triggers on a push that touches the Dockerfile or the
scripts that write the record. It does **not** trigger on a change to the
release workflow's own file, and that is deliberate.

Every release rebuilds the image, and a rebuild produces a new digest even
when the content is identical, because the image config carries a creation
timestamp. So a workflow that re-released on every edit to itself would
republish the image and move the digest recorded in the README, in
`results.md` and in the programme's `STATUS.md` — three places to keep in
step, for no change to the software. Re-running it by hand is
`workflow_dispatch`.

This is a real limitation, not a workaround: the image is not bit-for-bit
reproducible, so "rebuild and compare digests" is not a reproducibility
test. What P01-01.3 established — that the *tool versions* agree across
independent builds — is the meaningful claim, and P01-01.5 will make the
byte-level claim true as well by pinning the closure.
