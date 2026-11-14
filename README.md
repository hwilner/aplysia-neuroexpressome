# aplysia-neuroexpressome

**P01 · AplyNeuroExpress**

which *Aplysia* ion channel genes are hard to read, and can the public record be corrected?

## The three documents

| File | What it is | Read it if |
|---|---|---|
| [`introduction.md`](introduction.md) | Full academic introduction, with references to every relevant primary work | You work in the field and want the argument and the citations |
| [`extended-introduction.md`](extended-introduction.md) | Ground-up primer for a reader with **no** background, with every resource directly linked | You are starting from zero, or you want to check that a claim is properly sourced |
| [`materials-and-methods.md`](materials-and-methods.md) | **Pre-registered** analysis plan, including the decision procedure for choosing each statistical test, the gates, and the fallbacks | You want to know exactly what will be run, and what will happen if a result is negative |

Copies of the first and third also live in [`docs/`](docs/) for tools that expect manuscript sources there.

## Status

The pre-registration is committed and no analysis has run yet — that commit is
the evidence. The environment, the released image and the primary inputs are
in place; the subtask register lives in the programme repository.

## The released image

<!-- BEGIN RELEASED IMAGE -->

<!-- Written by scripts/record_release.py from the release record. Do not edit by hand. -->

| | |
|---|---|
| Image | `ghcr.io/hwilner/aplysia-neuroexpressome` |
| Digest | `sha256:3bf4416d3dc36a5feb99d988f566498881650d5cb985723c6cd744bef3c0344d` |
| Tag | sha-6fe3061 |
| Built from commit | 6fe3061978c8d9b76728a2c29be3626c5c33514d |
| Released | 2026-11-06T14:38:13Z |
| Tool manifest | `docs/released-manifest.txt` |
| Package closure | moved since the verified build — see `docs/closure-drift.txt` |

Pull it with:

```bash
docker pull ghcr.io/hwilner/aplysia-neuroexpressome@sha256:3bf4416d3dc36a5feb99d988f566498881650d5cb985723c6cd744bef3c0344d
```

<!-- END RELEASED IMAGE -->

The image is released and publicly pullable. The digest is written here by the
release workflow, from the same run that pushes the image, so that it cannot
be transcribed wrongly. A digest typed by hand is a claim of reproducibility
that can be false.

## Ground rules

1. The pre-registration is not amended. Later changes are logged as `deviation-log` issues, and stated in the manuscript.
2. Gate decisions are `gate-decision` issues, not commit messages. A gate with no recorded decision did not happen.
3. Every figure comes from a script in `src/figures/`.
4. Negative results get published. Gates with a fallback that produces a paper rather than a stop are in scope.
5. Released data get a Zenodo DOI, a container image digest, and a `reproduce.sh`.

## Where the rest of the programme lives

- **Charter and continuation protocol:** [aplysia-research-programme](https://github.com/hwilner/aplysia-research-programme)
  - [`PROGRAMME.md`](https://github.com/hwilner/aplysia-research-programme/blob/main/PROGRAMME.md) — which projects are standalone and which form a series
  - [`HANDOFF.md`](https://github.com/hwilner/aplysia-research-programme/blob/main/HANDOFF.md) — what to do when a project finishes
  - [`project-contracts/`](https://github.com/hwilner/aplysia-research-programme/tree/main/project-contracts) — gates, criteria, delivery contract
- **Schedule:** 74 tasks, importable into GitHub Projects, in the programme repository

## Licence

MIT. See [LICENSE](LICENSE).

## Contributing

This repository is open. Read [CONTRIBUTING.md](CONTRIBUTING.md) first, and
read [materials-and-methods.md](materials-and-methods.md) before changing any
script. The pre-registration is a commitment, and continuous integration fails
the build if an analysis artefact appears with an earlier commit date than the
pre-registration.

## Note on the other repositories

The sibling repositories hold the specifications for the other three projects.
They are not yet public, so those links resolve only for collaborators. Nothing
in this repository depends on them.
