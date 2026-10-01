# How to contribute to AplyNeuroExpress

AplyNeuroExpress reconstructs neuron gene models for *Aplysia californica* and
curates a searchable, confidence-scored catalogue of ion channel and plasticity
loci. The repository is open to contributions.

## What this project is

The reference *Aplysia* annotation is a 2013 scaffold assembly with a 2020
automated annotation on top. Research groups working on *Aplysia* neuropeptides
have reported having to search the genome annotation and a separate transcriptome
assembly, because the genome records are incomplete. This project measures how
incomplete the annotation is, repairs it using the published gene-model repair
method, and curates the channel genes by hand.

## Before you contribute

Read these in order. They are short.

1. [Introduction](introduction.md) — the argument, with sources
2. [Extended introduction](extended-introduction.md) — the same, from first
   principles
3. [Materials and methods](materials-and-methods.md) — the pre-registered plan

The pre-registration is a commitment, not a suggestion. Its commit timestamp
predates every analysis artefact, and continuous integration fails the build if
that stops being true.

## What you can contribute

| Contribution | Where it goes | Who reviews |
|---|---|---|
| A channel-family assignment you can justify | `curation_queue` in the review queue | Maintainer, plus a second annotator |
| A better gene model for a locus you have evidence for | The repair stage | Maintainer |
| A bug in the pipeline | Any script under `src/` | Maintainer |
| A documentation fix | Any `.md` | Maintainer |
| A pre-registration deviation | An issue, not a commit | Maintainer |

## What we will not accept

- **New analysis not in the pre-registration.** Raise it as an issue first. The
  point of pre-registration is that the analysis does not change to suit the
  result.
- **A dependency bump with no behavioural justification.** The container is
  pinned. If a tool needs updating, say what changed and why it matters.
- **A figure not produced by a script.** Every figure comes from `src/figures/`.
- **A deletion of a RefSeq model.** Displaced models move to a superseded track
  with the reason recorded. The repair is auditable and reversible, and that
  property depends on nothing being destroyed.

## How to set up

```bash
git clone https://github.com/hwilner/aplysia-neuroexpressome
cd aplysia-neuroexpressome
docker build -t aplysia-neuroexpressome .
```

Run everything inside the container. A result produced outside it is not a
result we can reproduce.

## How to submit

1. Open a branch. Do not commit to `main`.
2. Make the change, and add a test if the change is in a script.
3. Open a pull request. Continuous integration checks that no large files, no
   credentials, and no analysis artefact pre-dating the pre-registration.
4. Wait for review. Curation changes need a second annotator, not just approval.

## House style

Documentation follows the
[Google developer documentation style guide](https://developers.google.com/style):
sentence case headings, second person, active voice, and the present tense.
Scientific documents follow academic convention instead, because that is what
the target journals expect. If you are unsure which applies, it depends on the
file: operational documentation uses Google style, scientific documents do not.

## Code of conduct

Be direct, be accurate, and disagree with the evidence rather than the person.
Report a negative result rather than leaving it out; a measured failure to beat
the baseline is a publishable finding here, not a disappointment.
