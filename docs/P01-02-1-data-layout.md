# P01-02.1 — the data layout

**Subtask:** P01-02.1 — create `data/` and `data/raw/`, and confirm `raw/` is gitignored.
**Status:** complete.
**Date:** 2026-11-08.

## The layout

The repository now carries the three directories the pipeline writes into.

```
data/
├── .gitkeep          the directory itself
├── manifest.tsv      SHA-256 of every downloaded input   (P01-02.4)
├── raw/              the downloaded inputs, never committed
│   └── .gitkeep
└── derived/          generated intermediates, never committed
    └── .gitkeep
```

`data/raw/` holds the inputs: the AplCal3.0 assembly FASTA (P01-02.2), the
RefSeq Release 102 annotation and its supporting files (P01-02.3). They are
large, and they are re-fetchable from the accessions recorded in
`data/manifest.tsv`, so committing them would bloat the repository without
adding provenance.

`data/derived/` holds what the pipeline generates from them.

`data/manifest.tsv` is the part that is tracked, and it is the whole
provenance mechanism. A raw input is versioned by the SHA-256 of its bytes
rather than by committing the bytes, so the manifest is what says which
release of which file was used. It is created in P01-02.4.

The same three directories — `data/raw`, `data/derived` and `results` — are
created inside the image by the Dockerfile, at `/workspace/`, and
`.dockerignore` keeps the raw data out of the build context. Before this
change the image had them and the repository did not.

## The ignore rules, and why they changed

The rules read like this:

```gitignore
/data/raw/*
!/data/raw/.gitkeep
/data/derived/*
!/data/derived/.gitkeep
```

They used to read:

```gitignore
data/raw/
data/derived/
```

The difference is not cosmetic. The old form excludes the **directory
itself**, and git does not descend into an excluded directory — so a
`.gitkeep` placed inside one was ignored along with everything else. The
directory would have been missing from every fresh clone, and the scripts
that write into it would have had to create it first.

The `/*` form excludes the contents and leaves the directory in place, and
the negation puts the `.gitkeep` back. The leading slash anchors the
pattern to the repository root, so the rules cannot be made to match a
`raw/` directory somewhere else by accident.

## How it was verified

Not by reading the file. By doing the thing it claims.

A clean clone of the repository was made, and the layout checked in it:

```
present  data/
present  data/raw/
present  data/derived/
tracked under data/ in the clone:
    data/.gitkeep
    data/derived/.gitkeep
    data/raw/.gitkeep
```

A raw file and a reads file were then dropped into the clone's
`data/raw/`, and `git status --porcelain` reported nothing. Neither file
reached git.

The same checks run as unit tests, in `tests/test_data_layout.py`, so they
keep running:

| check | what it catches |
|---|---|
| the directories exist | a layout that was never created |
| a raw file is ignored | the rule going back to excluding the directory |
| a derived file is ignored | the same |
| the `.gitkeep` files are not ignored | the rule going back to excluding the directory |
| `data/manifest.tsv` is not ignored | the checksum manifest being ignored by accident |
| a file written into `data/raw/` never reaches `git status` | the end-to-end claim, tested rather than asserted |
| the `.gitkeep` files are tracked | a `.gitkeep` that was never committed, which leaves the directory missing from a clone |
| no raw data is tracked | raw data committed by accident |

The tracked-file check is the one that matters most. A `.gitkeep` that
exists in the working tree but was never committed produces a repository
that looks right to the person who made it and is missing a directory in
every clone.

The test suite is 93 tests, up from 82.

## What comes next

| subtask | what it does |
|---|---|
| P01-02.2 | downloads the AplCal3.0 assembly FASTA into `data/raw/` |
| P01-02.3 | downloads the RefSeq Release 102 annotation into `data/raw/` |
| P01-02.4 | records the SHA-256 of every file in `data/manifest.tsv` |
| P01-02.5 | captures the assembly and annotation release strings verbatim |

None of them needs the layout changed. The next one writes into
`data/raw/`, and the manifest that versions what it wrote arrives two
subtasks later.

## Files

| file | what it is |
|---|---|
| `.gitignore` | the ignore rules, corrected |
| `data/.gitkeep`, `data/raw/.gitkeep`, `data/derived/.gitkeep` | the tracked directories |
| `tests/test_data_layout.py` | the checks above, as tests |
| `.dockerignore` | unchanged; it already excluded the raw data from the build context |
| `Dockerfile` | unchanged; it already created the directories inside the image |
