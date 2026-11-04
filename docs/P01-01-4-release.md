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
