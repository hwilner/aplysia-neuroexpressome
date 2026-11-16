# P01-02.5 — the release strings, verbatim

**Subtask:** P01-02.5 — capture the assembly and annotation release strings verbatim.
**Status:** complete.
**Date:** 2026-11-16.

## Why this exists

The pre-registration asks for the assembly and annotation release strings to be
recorded. The point of recording them is that a reader, a reviewer, or a
re-runner six months from now can say exactly which assembly and which
annotation release the analysis was run against — without trusting that nobody
changed the accession in the meantime, and without a 240 MB download to hand.

"Verbatim" is the operative word, and it is stricter than it looks. NCBI writes
the same date in two different formats in two different files. It gives the
assembly *units* accessions of their own, which are not the assembly accession
and look like it. It gives a release a numeric id in one file and a full name in
another. A capture that paraphrased any of that would be wrong in a way that
looks right.

So the capture is not written by hand. `scripts/capture_versions.py` carries a
table of **where to look** — file, line, and how to take the value out of that
line — and the value is whatever is there. Nothing in the record is a retyping,
so nothing in it can drift from the source by a capital letter or a hyphen.

| | |
|---|---|
| Record | `data/versions.tsv` — 38 strings, 26 concepts |
| Source lines | `data/versions-verbatim.txt` — the lines, with their numbers |
| Generator | `scripts/capture_versions.py` |
| Tests | `tests/test_release_strings.py` |
| Sources | `README_Aplysia_californica_annotation_release_102`, `Aplysia_californica_AR102_annotation_report.xml` |

The generator refuses to run unless each source file is listed in
`data/manifest.tsv` **and** its SHA-256 still matches. A capture cannot
silently be taken from different bytes than the ones the programme has already
recorded.

## The sources, verbatim

The blocks below are written by the generator, not by hand. The prose around
them is not.

<!-- BEGIN VERBATIM -->
### `README_Aplysia_californica_annotation_release_102`

```
     1: ORGANISM NAME:	Aplysia californica
     2: ORGANISM COMMON NAME:	California sea hare
     3: TAXID:	6500
     4: ANNOTATION RELEASE NAME:	NCBI Aplysia californica Annotation Release 102
     5: ANNOTATION EVIDENCE FREEZE DATE:	18-August-2020
     6: ANNOTATION RELEASE DATE:	31-August-2020
     7: ANNOTATION REPORT:	https://www.ncbi.nlm.nih.gov/genome/annotation_euk/Aplysia_californica/102
    10: ASSEMBLY NAME:	AplCal3.0
    11: ASSEMBLY ACCESSION:	GCF_000002075.1
    12: ASSEMBLY SUBMITTER:	Broad Institute
    13: ASSEMBLY DATE:	15 May 2013
    14: ASSEMBLY TYPE:	Haploid
    15: NUMBER OF ASSEMBLY-UNITS:	2
    18: GCF_000001455.1	Primary Assembly
    19: GCF_000045755.1	non-nuclear
```

### `Aplysia_californica_AR102_annotation_report.xml`

```
     3:   <AssembliesReport target_set_accession="GCF_000422015.1">
     5:     <Name>AplCal3.0</Name>
     6:     <Accession>GCF_000002075.1</Accession>
     7:     <IsReference>Yes</IsReference>
     8:     <SubmitterOrganization>Broad Institute</SubmitterOrganization>
     9:     <SubmitterDate>05-15-2013</SubmitterDate>
    16:         <Name>Primary Assembly</Name>
    17:         <Accession>GCF_000001455.1</Accession>
    18:         <IsPrimary>Yes</IsPrimary>
    19:         <Type>HaploidUnit</Type>
    22:         <Name>non-nuclear</Name>
    23:         <Accession>GCF_000045755.1</Accession>
    24:         <IsPrimary>No</IsPrimary>
    25:         <Type>HaploidUnit</Type>
    31:   <Taxid>6500</Taxid>
    32:   <ScientificName>Aplysia californica</ScientificName>
    33:   <AnnotationReleaseId>102</AnnotationReleaseId>
    34:   <FreezeDate>Aug 18 2020</FreezeDate>
    35:   <FreezeDateId>20200818</FreezeDateId>
    36:   <IdLoadDate>Aug 31 2020</IdLoadDate>
    40:   <FtpSite>ftp://ftp.ncbi.nlm.nih.gov/genomes/all/annotation_releases/6500/102</FtpSite>
```
<!-- END VERBATIM -->

## What the two sources agree on

Twelve concepts are recorded by both files. Nine are byte-identical; three are
the same date in two formats.

| Concept | Readme | Report |
|---|---|---|
| `organism.scientific_name` | `Aplysia californica` | `Aplysia californica` |
| `organism.taxid` | `6500` | `6500` |
| `annotation.evidence_freeze_date` | `18-August-2020` | `Aug 18 2020` |
| `annotation.release_date` | `31-August-2020` | `Aug 31 2020` |
| `assembly.name` | `AplCal3.0` | `AplCal3.0` |
| `assembly.accession` | `GCF_000002075.1` | `GCF_000002075.1` |
| `assembly.submitter` | `Broad Institute` | `Broad Institute` |
| `assembly.date` | `15 May 2013` | `05-15-2013` |
| `assembly.unit.primary.accession` | `GCF_000001455.1` | `GCF_000001455.1` |
| `assembly.unit.primary.name` | `Primary Assembly` | `Primary Assembly` |
| `assembly.unit.non_nuclear.accession` | `GCF_000045755.1` | `GCF_000045755.1` |
| `assembly.unit.non_nuclear.name` | `non-nuclear` | `non-nuclear` |

The two files are NCBI's own statement of the same release, written for two
different audiences — a readme for a human and an XML report for a program.
That they agree on all twelve is a check, not a hope: the tests compare them
concept by concept, and the three dates are compared after being parsed, so a
date that drifted in one file would fail.

## Three things worth knowing before citing this

**The same date, in two formats.** The readme writes `15 May 2013`; the report
writes `05-15-2013`. The evidence freeze is `18-August-2020` in one and
`Aug 18 2020` in the other. Both are captured as written. A manuscript that
quotes the release date has to pick one, and the note has to say which — the
readme's `ANNOTATION RELEASE DATE` is the natural choice for prose, because it
is the label NCBI uses for a human reader.

**The report has no element called "release date".** It has `<IdLoadDate>`. The
date is the same one — 31 August 2020 — but NCBI's internal term for it is
different, and a capture that renamed it to "release date" would be
interpreting. Both the value and the name are recorded: the key is
`annotation.id_load_date.report` and the concept it is filed under is
`annotation.release_date`.

**The assembly has two units, and they have their own accessions.**

| | Accession | Name |
|---|---|---|
| The assembly | `GCF_000002075.1` | `AplCal3.0` |
| Its primary unit | `GCF_000001455.1` | `Primary Assembly` |
| Its non-nuclear unit | `GCF_000045755.1` | `non-nuclear` |

Only the first is the assembly accession. The other two are RefSeq accessions
for the *sequence sets* within the assembly — the nuclear assembly and the
mitochondrial one, which is `NC_005827.1`. Writing `GCF_000001455.1` where
`GCF_000002075.1` was meant is an easy mistake and a fatal one: it resolves to
something real, so nothing complains. The keys in `data/versions.tsv` keep them
apart — `assembly.accession` against `assembly.unit.primary.accession` — and
`data/manifest.tsv` records the assembly accession against the file the
analysis actually uses.

There is a third accession here, `GCF_000422015.1`, which is the
`target_set_accession`: the set of genomes this release annotated, of which
AplCal3.0 is one. It is not the assembly either.

## The accession, now pinned byte-for-byte

`GCF_000002075.1` was already confirmed by five independent sources. This
subtask does not add a sixth — two of those five are the files captured here.
What it adds is the **exact bytes**: the accession as NCBI writes it, in the
readme's `ASSEMBLY ACCESSION:` field and in the report's `<Accession>` element,
quoted rather than asserted, with the SHA-256 of the files they came from
recorded in `data/manifest.tsv`.

The pre-registration's `GCF_000002075.2` still does not resolve. That remains
deviation D003 and issue #28, and the pre-registrations are still unedited.

## The release is mostly prediction

One thing about Release 102 does not come from the release strings, and it
matters more than any of them. The annotation is about **98.6%
machine-predicted**: of its 19,425 protein-coding gene placements, 19,142 are
Gnomon predictions, and 26,391 of its 26,656 proteins carry `XP_` accessions.
Only 283 placements are RefSeq-supported.

This is not a deviation — the pre-registration names Release 102 and Release
102 is what was fetched. But Gate G1 measures baseline BUSCO completeness, and
that measurement is taken against a mostly predicted annotation. The methods
must say so, and the Gate G1 record must carry it.

## How to check

```bash
python3 scripts/capture_versions.py     # regenerates both files and the note's blocks
python3 -m unittest discover -s tests   # 15 tests
```

The generator is idempotent: run it twice and both files are byte-identical.

The tests hold the capture against four things — the sources themselves, the
checksum manifest, the note's verbatim blocks, and the agreement table — and
the first three do not need the raw data, because the record and the note are
both committed.
