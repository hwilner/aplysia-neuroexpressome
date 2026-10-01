# Results

**Status: no results yet.** P01 kicks off 2026-10-05. This file is the pre-registered Results skeleton: every table and figure that the finished manuscript must contain is reserved here, with its caption, before any data exist. When a result lands it replaces the *Pending* marker in place — the structure below is not edited after the fact. Deviations from the plan are logged as `deviation-log` issues and stated here.

## Pre-registered success criteria

**Table 1. Pre-registered success criteria for P01 (AplyNeuroExpress), committed before analysis.** Thresholds are the acceptance values from `materials-and-methods.md`; the Result column is filled at analysis time and nowhere else.

| # | Criterion | Threshold | Statistical test | Result |
|---|---|---|---|---|
| C1 | Lift-off coverage of transcriptome proteins | ≥ 60% | descriptive, gate G2 | *Pending* |
| C2 | BUSCO completeness vs Release 102 | higher, McNemar *p* < 0.05 | T1 · McNemar exact | *Pending* |
| C3 | Median CDS length, paired loci | higher, Wilcoxon *p* < 0.05 | T2 · Wilcoxon signed-rank (exact) | *Pending* |
| C4 | Median exon count, paired loci | higher, Wilcoxon *p* < 0.05 | T3 · Wilcoxon signed-rank (exact) | *Pending* |
| C5 | Channel loci with domain-level evidence | ≥ 90% | descriptive | *Pending* |
| C6 | Manual curation agreement | Cohen's κ ≥ 0.80 | T9 · κ with bootstrap CI | *Pending* |
| C7 | Clean-clone reproduction | README reproduces all figures | `reproduce.sh` | *Pending* |

**Negative-result clause (pre-committed):** if C1 and C2 both fail, the negative result is published. This outcome is in scope and does not alter the tables below.

## Primary results

### R1 · Gene-model fragmentation, before and after repair

**Table 2. Per-locus fragmentation diagnostics on paired loci (Release 102 vs repaired).** Exon count, CDS length, start/stop presence, gap overlap, internal-stop flag; paired tests T2/T3 with matched-pairs rank-biserial *r* as effect size. *Pending — produced by task P01-05/P01-19.*

| Metric | Release 102 median | Repaired median | Test | p | Effect size |
|---|---|---|---|---|---|
| CDS length | *Pending* | *Pending* | Wilcoxon signed-rank | *Pending* | *Pending* |
| Exon count | *Pending* | *Pending* | Wilcoxon signed-rank | *Pending* | *Pending* |
| Complete start/stop (%) | *Pending* | *Pending* | McNemar exact | *Pending* | *Pending* |
| Internal-stop loci (%) | *Pending* | *Pending* | McNemar exact | *Pending* | *Pending* |

**Figure 1. Gene models are fragments; the transcriptome is how you find the rest.** The same genomic region before (RefSeq Release 102) and after (AplCal3.0 + 2022 CNS transcriptome) repair, with the five-step repair pipeline. Schematic, drawn by `src/make_figures.py` (fig01) in the programme repository. *Exists — schematic only; data panels to be added by P01-20.*

### R2 · BUSCO completeness, repaired vs Release 102 and contemporary peers

**Table 3. BUSCO (metazoa_odb10) completeness across annotations.** McNemar exact test for the paired Release 102 comparison (T1); chi-square/Fisher for the cross-annotation comparison against *Elysia* and *Euprymna* (T4). *Pending — tasks P01-04, P01-06, P01-19.*

| Annotation | Complete (%) | Fragmented (%) | Missing (%) | Comparison | p |
|---|---|---|---|---|---|
| Release 102 (baseline) | *Pending* | *Pending* | *Pending* | — | — |
| Repaired | *Pending* | *Pending* | *Pending* | vs baseline (T1) | *Pending* |
| *Elysia* peer annotation | *Pending* | *Pending* | *Pending* | vs repaired (T4) | *Pending* |
| *Euprymna* peer annotation | *Pending* | *Pending* | *Pending* | vs repaired (T4) | *Pending* |

### R3 · Ion-channel and plasticity-gene catalogue

**Table 4. Channel-family sweep results.** Loci recovered per family with Pfam/InterProScan domain-level evidence, DeepTMHMM topology, and curation confidence tier. Families: Kv, K2P, KCNQ, Slo/BK, SK, HCN, CaV, Nav, ENaC, Na/K-ATPase, ligand-gated, IP3R, SERCA, Slack, TREK. *Pending — tasks P01-13/P01-14.*

| Family | Loci | Domain-level evidence (%) | Topology predicted | Confidence tier |
|---|---|---|---|---|
| *16 rows, one per family* | *Pending* | *Pending* | *Pending* | *Pending* |

**Table 5. Dual-annotator curation agreement.** Cohen's κ with bootstrap CI, reported globally and per family, with the raw confusion matrix; third-annotator adjudication outcomes. *Pending — tasks P01-15/P01-16.*

| Scope | κ | 95% CI | N adjudicated |
|---|---|---|---|
| Global | *Pending* | *Pending* | *Pending* |
| Per family | *Pending* | *Pending* | *Pending* |

## Secondary results

**Table 6. Enrichment and cross-species statistics.** T5 Poisson GLM on family counts; T6 hypergeometric enrichment against the tested universe; T7 Fisher exact on ortholog retention; T10 Welch *t* on sequence identity. All reported with effect sizes (Hedges' *g*, Wilson intervals) per the statistical decision procedure. *Pending — tasks P01-18/P01-19.*

| Test | Question | Statistic | p | Effect size |
|---|---|---|---|---|
| T5 | Family count enrichment | Poisson GLM | *Pending* | *Pending* |
| T6 | Functional enrichment | hypergeometric | *Pending* | *Pending* |
| T7 | Ortholog retention | Fisher exact | *Pending* | *Pending* |
| T10 | Sequence identity | Welch *t* | *Pending* | *Pending* |

**Isoform analysis (T8):** descriptive only — *n* too small for inference at this locus count. Reported as a table of key channel loci and their isoforms, no test. *Pending — task P01-17.*

## Reproducibility

**Table 7. Release checklist.** Completed at Zenodo release (task P01-22).

| Item | Value |
|---|---|
| Concept DOI | *Pending* |
| Container image digest | *Pending* |
| `reproduce.sh` clean-clone run | *Pending* |
| Catalogue licence | CC0 |

## Gate record

Gate decisions are `gate-decision` issues, not prose. G1 (baseline BUSCO ≥ 90%) and G2 (lift coverage ≥ 60%) are *not reached*; their outcomes and any fallback taken will be recorded here with links to the decision issues.
