# P01-05.1 · the per-locus diagnostics script

**Date:** 2026-11-19. **Subtask:** P01-05. **Affects:** nothing measured;
this note records an implementation, not a result.

## What was built

`scripts/locus_diagnostics.py` implements the diagnostic step
pre-registered in `materials-and-methods.md` §3.1 step 3: per locus, the
number of exons, the total CDS length, whether the model has a start and a
stop codon, whether the model overlaps an assembly gap, and the
fragmentation flag (CDS under 300 nt, or an internal stop). Its output is
the per-locus table that the paired before/after comparison — tests T2 and
T3, results.md Table 2 — is built from once the repaired annotation exists.

## Design decisions, fixed before any data are seen

- **One row per locus.** The representative transcript is the one with the
  greatest total CDS length, ties broken by the smallest transcript ID.
  The choice is deterministic and cannot be tuned after results exist.
- **Coding models only.** Loci with no CDS feature are skipped: the
  diagnostics are properties of a coding model.
- **Start/stop** come from explicit `start_codon`/`stop_codon` features
  where the GFF carries them (RefSeq GFF3 does) and from the assembly
  sequence where it does not.
- **Internal stop** is any stop codon among the complete codons of the
  spliced CDS, excluding a terminal one, under the standard genetic code.
  The mitochondrion (`NC_005827.1`) uses code 5 and is out of scope for
  the channel catalogue; if mitochondrial loci are ever diagnosed, the
  code must be selectable first.
- **Assembly gap** is a run of at least 10 N bases (`--min-gap`).
- **`--fasta` is optional.** Without it, the sequence-based diagnostics
  are reported as `NA` — marked, not guessed — and fragmentation rests on
  CDS length alone.

## Validation

`tests/test_locus_diagnostics.py` builds a synthetic chromosome with six
loci whose expected diagnostics are known by construction — clean
single-exon, clean three-exon minus-strand, internal stop, sub-threshold
CDS, missing stop codon, gap overlap — plus parser rejection cases, the
degraded no-FASTA mode, the representative-transcript tie-break, and a
byte-for-byte reproducibility check. Every expected value is fixed by the
fixture design rather than by running the implementation. 19 tests, all
passing under `python3 -m unittest discover -s tests`.

`tests/test_results_skeleton.py` was added in the same run: it guards the
pre-registered Results skeleton in results.md against silent drift and
requires any filled *Pending* block to declare its producing script or
artifact.

## What is deliberately not done

The script has not been run on Release 102. That run happens in the
released container against the real GFF3, under P01-05 proper, and its
output lands in `data/derived/` (gitignored, checksummed into
`data/manifest.tsv`). No number in this note or anywhere in the repository
is a measured result; results.md Table 2 stays *Pending* until then.
