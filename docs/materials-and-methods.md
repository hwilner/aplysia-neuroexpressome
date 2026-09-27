# AplysiaNeuroExpress — planned materials and methods

> Status: **pre-registration draft.** Written before any analysis is run. Every test named here is fixed in advance; any deviation gets logged in `docs/analysis-deviations.md` with a dated reason. This file is the methods section of the manuscript and doubles as the analysis specification.

## 1. Study design

A genome-annotation and curation study. No new biological material is generated. The unit of analysis is the **gene locus**; the unit of curation is the **channel-family assignment**. The design is paired (before/after) for the annotation-repair comparison and unpaired for the cross-species comparison.

**Primary hypothesis.** Lifting the 2022 CNS transcriptome onto AplCal3.0 and repairing the resulting models yields a neuron-focused gene set with measurably higher structural integrity than RefSeq Annotation Release 102, measured by BUSCO metazoan completeness and by coding-sequence length, for a pre-specified channel/plasticity gene set.

**Pre-specified secondary hypotheses.**
- H2: the repair recovers loci that are fragmented or partial in Release 102, concentrated in large, multi-exon genes.
- H3: ion channel family representation in *Aplysia* neuronal models is systematically lower than in vertebrate and *Drosophila* reference sets — a statement about **annotation depth**, not about biology, and framed as such.
- H4: isoform structure for a pre-specified set of channel loci is recoverable at higher resolution from the transcriptome than from the genome annotation alone.

**Explicit non-hypotheses.** This study does not claim to produce a new assembly, does not claim completeness for any gene family, and does not draw functional conclusions about channel activity. It makes no statement about cell-type-specific expression.

## 2. Materials

### 2.1 Primary inputs (all open access; no registration required)

| Input | Accession / location | Version pin | Used for |
|---|---|---|---|
| Genome assembly | `GCF_000002075.2` (AplCal3.0) | Assembly release 2013, checksum recorded at download | Lift-over target, coordinate frame |
| Current reference annotation | RefSeq Annotation Release **102** | Release 102 (2020) | Baseline / "before" arm |
| CNS transcriptome assembly | GenBank TSA `GJYY00000000` (Orvis et al. 2022); also via AplysiaTools `aplysiatools.org` | Deposited 2022-06-10; FASTA checksummed | Lift-off source, gene-model repair source |
| Comparison annotation: *Elysia timida* | BRAKER3 annotation, 19,904 protein-coding genes | 2025 | Cross-annotation BUSCO comparison |
| Comparison annotation: *Euprymna scolopes* | BRAKER2 annotation, 18,663 gene models | 2025 | Cross-annotation BUSCO comparison |
| Pfam / InterPro | Pfam-A via HMMER 3.1b2; InterProScan 5 | Current at run date, recorded | Domain and family assignment |
| Ortholog reference | eggNOG-mapper 2.1.9; OrthoFinder 2.5 | Current at run date, recorded | Orthology, functional annotation |
| BUSCO lineage | `metazoa_odb10` | odb10 | Completeness metric |

### 2.2 Software environment

Pinned via a multi-stage `Dockerfile` committed to the repository and the image pushed to a public container registry with a digest recorded in the README. No step may be run outside the container.

| Stage | Tool | Version | Purpose |
|---|---|---|---|
| base | `mambaforge` | 23.11 | environment manager |
| lift | `liftoff` | 1.3.0 (git-pinned) | lift transcriptome models to genome |
| decode | `TransDecoder` / `aplotransDecoder` | 5.7.0 | ORF prediction on transcriptome |
| align | `HISAT2` + `SAMTOOLS` | 2.2.1 / 1.19 | only if the fallback BRAKER route is taken |
| anno | `InterProScan` | 5.70-102.0 | domain annotation |
| ortho | `OrthoFinder`, `eggNOG-mapper` | 2.5.4 / 2.1.9 | orthology and functional annotation |
| metric | `BUSCO` | 5.7.1 | completeness |
| tree | `MAFFT` L-INS-i, `trimAl`, `IQ-TREE` 2 | 7.505 / 1.4.rev22 / 2.2.6 | family phylogenies |
| stats | `R` with `tidyverse`, `rstatix`, `metafor`, `lme4` | 4.4.x | statistical analysis |
| interp | `Jupyter` | 1.x | notebooks, figure provenance |

**Fallback route.** BRAKER is documented as not supporting training on assembled-transcriptome alignments, only on RNA-seq reads. If the Liftoff-first route underperforms the success threshold in §4, the fallback is to map SRA reads from BioProject `PRJNA77701` / SRA `SRP009481` to AplCal3.0 and run BRAKER3. This is recorded in advance because it changes the compute budget materially and should not be a mid-project surprise.

### 2.3 Compute

Liftoff, OrthoFinder and BUSCO run on 16 vCPU / 64 GB RAM. The SRA-remap-plus-BRAKER3 fallback needs 32 vCPU / 128 GB and roughly 40 GB of scratch. Costs are estimated in `docs/compute-budget.md` and kept under a self-imposed ceiling stated in the README.

## 3. Methods

### 3.1 Stage 1 — Baseline integrity assessment (before)

1. Download AplCal3.0 and RefSeq Release 102. Record SHA-256 checksums in `data/manifest.tsv`. Record assembly and annotation release strings verbatim.
2. Run BUSCO (`metazoa_odb10`, `--mode genome` on the assembly with `--proteins` against the annotation's protein set) to obtain the "before" completeness profile.
3. Parse the GFF and compute per-locus diagnostics: number of exons, total CDS length, whether the model has a start and stop codon, whether the model overlaps a gap in the assembly, and a fragmentation flag for models shorter than 300 nt or containing internal stops.
4. Run the same pipeline on the *Elysia* and *Euprymna* annotation protein sets to give a contemporary peer baseline.

**Gate G1.** If baseline metazoan BUSCO completeness is below 90%, the baseline annotation is too degraded for the paired comparison to be meaningful, and the project re-scopes to the channel subset only. Record and report.

### 3.2 Stage 2 — Transcriptome lift-off

1. Obtain the merged-unigene FASTA and predicted protein set from AplysiaTools; obtain the Orvis 2022 assembly from GenBank. Confirm the two are the same underlying build by comparing sequence counts and a random sample of 50 sequences.
2. Align the transcriptome protein set to the assembly with DIAMOND; run Liftoff with `--flanks 10` and the Release 102 annotation as the `--gff` guide.
3. Extract per-transcript lift statistics: lifted / not lifted / partial, and for partial lifts the percent aligned.

**Gate G2.** If the lifted fraction is below 60%, fall back to mapping SRA reads and running BRAKER3 rather than reporting a lift that does not cover the transcriptome.

### 3.3 Stage 3 — Gene-model repair

Follow the published repair logic rather than inventing one: build a candidate family sequence set (genome-derived plus transcriptome-derived), align with MAFFT L-INS-i, trim with `trimAl`, infer a tree with IQ-TREE 2, then inspect branches with multiple homologs and replace partial, expanded, or broken models with better-supported transcriptome-derived sequences [Hsiao et al. 2024]. Specifically:

1. Run ORF prediction on the transcriptome to generate candidate coding models not present in the genome annotation.
2. For each locus, reconcile the genome-derived and transcriptome-derived models into a single preferred model, recording the evidence for the choice.
3. Never delete a Release 102 model outright. Retain it in a `superseded` track with the reason recorded, so the resource is auditable and reversible.

### 3.4 Stage 4 — Channel-family curation

1. Sweep the recovered protein set against Pfam-A for the channel-associated families (Kv, K2P, KCNQ, Slo/BK, SK, HCN, CaV, Nav, ENaC, Na/K-ATPase, ligand-gated ion channels, inositol trisphosphate receptor, SERCA, and the two-pore and Slack families), and against InterPro for entry signatures.
2. Assign each hit to a family, with membrane topology predicted by DeepTMHMM.
3. Produce a manual review queue for every candidate and every Release 102 locus that matches a channel keyword but has no domain evidence. Two independent annotators review the queue; disagreements go to a third. Report agreement (§5.3).
4. Release the catalogue as GFF/GTF, protein FASTA, and a flat table.

### 3.5 Stage 5 — Statistical analysis

See §5.

### 3.6 Stage 6 — Reporting and release

Figures generated only from scripts in `src/`. Every figure has a corresponding `figures/figureN.py`. Release via Zenodo with a concept DOI, and archive the container image digest in the same record.

## 4. Success criteria

Declared in advance so the project cannot be retrofitted to its outcome.

| Criterion | Threshold |
|---|---|
| Lift coverage of transcriptome proteins | >= 60% (Gate G2) |
| BUSCO completeness, repaired set | higher than Release 102, p < 0.05 by McNemar's test |
| Median CDS length, paired loci | higher in repaired set, p < 0.05 by Wilcoxon signed-rank |
| Channel loci with domain-level evidence | >= 90% of catalogue entries |
| Manual curation inter-annotator agreement | Cohen's kappa >= 0.80 |
| Independent code execution | repository README reproduces all figures from a clean clone |

If the BUSCO and CDS-length criteria both fail, the negative result is published. A measured, documented failure to improve on Release 102 is itself a useful community result and is within scope.

## 5. Statistical analysis plan

### 5.1 Test-selection procedure

The rule applied throughout: **identify the data type, then the number of independent sampling units, then the distributional assumption, then choose the narrowest test whose assumption is satisfied — and if the assumption cannot be checked with the available n, use a permutation or bootstrap alternative rather than assuming normality.**

| Step | Question | If YES | If NO |
|---|---|---|---|
| 1 | Are the observations independent sampling units? | Proceed | Use a mixed-effects model with the non-independent factor as a random effect; if the nesting is not modelled, do not report a p-value |
| 2 | Is the outcome binary or categorical? | Propagate to step 3 | Go to step 4 |
| 3 | Is the design paired (same entities measured twice)? | McNemar's exact test | Fisher's exact test (small cell counts) or chi-square (all expected counts >= 5) |
| 4 | Is the outcome a count or rate? | Negative binomial GLM with offset, or Poisson if variance ~= mean | Go to step 5 |
| 5 | Is the outcome continuous, and is n >= 30 per group? | Welch's t-test (unequal variances assumed by default) | Go to step 6 |
| 6 | Is the outcome continuous, paired, and n < 30? | Wilcoxon signed-rank test (exact p when n <= 25) | Go to step 7 |
| 7 | Is the outcome continuous and unpaired with n < 30, or is the distribution strongly non-normal? | Permutation test (10000 resamples) or bootstrap BCa confidence interval | Welch's t-test with a permutation-based p-value as the reported value |
| 8 | Are there more than two groups or a factorial design? | Linear model with the factors as fixed effects and interaction terms tested first | Two-group test as above |
| 9 | Is the analysis drawing on multiple independent studies or datasets? | Random-effects meta-analysis (§5.5) | Single-dataset analysis |

Two rules override the table:

- **Report the effect size, not only the p-value.** For rank tests report the matched-pairs rank-biserial correlation; for mean differences report Hedges' *g*; for proportions report the risk difference with a Wilson interval; for the two-stage ordering results report the proportion of concordant pairs.
- **Never test a null that the design cannot detect.** Before running, compute the minimum detectable effect at 80% power for the actual n and state it. If the MDE exceeds the effect being claimed, report "no detectable difference above X" rather than a non-significant p-value.

### 5.2 Specific tests for this project

| # | Analysis | Data type / n | Test | Why this test and not the obvious alternative | Assumption check | Fallback |
|---|---|---|---|---|---|---|
| T1 | BUSCO completeness, repaired vs Release 102 | Paired binary per ortholog group, thousands of loci | **McNemar's exact test** | Paired proportions; chi-square on a 2x2 of paired data is invalid because the two arms are not independent | Discordant-pair count; if < 25 use the exact binomial form | Report the difference in proportion with a Wilson interval and skip the test if discordant pairs < 10 |
| T2 | Median CDS length, paired loci | Paired continuous, n = number of loci with both models | **Wilcoxon signed-rank (exact)** | Locus lengths are heavily right-skewed and n is large but the tails are long; the signed-rank test is robust to that and the exact distribution is available | Check for >20% non-zero differences; if violated, use a permutation test on the mean difference | Bootstrap BCa median difference |
| T3 | Exon count change, paired | Paired discrete | **Wilcoxon signed-rank** | Same reasoning as T2; ordinal counts, non-normal | As T2 | As T2 |
| T4 | Cross-annotation BUSCO (Aplysia vs *Elysia* vs *Euprymna*) | Unpaired proportions, 3 groups | **Chi-square on 3x2 contingency**, with Fisher's exact if any expected count < 5 | Three groups compared simultaneously; pairwise Fisher as a post-hoc with Holm adjustment | Expected counts | Report proportions with Wilson intervals only, and state that the comparison is descriptive |
| T5 | Ion channel family counts across four taxa (Aplysia, *Drosophila*, *C. elegans*, human) | Counts per family per taxon | **Poisson GLM** with taxon as a fixed factor and family as an offset or factor | Counts with small integer values; a chi-square on counts assumes fixed denominators, which is wrong here because the genome sizes differ by orders of magnitude | Check overdispersion with a dispersion statistic; if phi > 2, switch to negative binomial | Descriptive counts with the caveat, and state that this is annotation depth, not gene-family evolution |
| T6 | GO / KEGG enrichment on recovered loci | Over-representation against a background of all tested genes | **Hypergeometric (Fisher's exact) test per term**, Benjamini-Hochberg FDR across terms | Standard over-representation; the background must be the tested universe, not the whole genome, and stating this is the difference between a valid and an invalid enrichment analysis | Report enrichment ratio, adjusted p, and the number of background genes | Pre-ranked GSEA on a ranked statistic, which does not depend on an arbitrary threshold |
| T7 | Ortholog retention, Aplysia vs each gastropod reference | 2x2 per orthogroup | **Fisher's exact** | Sparse retention tables with cells well under 5 | Expected counts | Report counts descriptively |
| T8 | Isoform number per channel locus | Discrete counts, small n (<20 loci) | **Descriptive only, no test** | n is far too small for inference; a test here would be performative | — | Report per-locus counts and the detection method used |
| T9 | Manual curation agreement | Categorical, two raters, ~100+ items | **Cohen's kappa** with a bootstrap CI | Beyond raw percent agreement, which overstates agreement under imbalanced marginals | Report the prevalence-marginal index alongside kappa; if prevalence is extreme, supplement with positive-agreement and negative-agreement rates | Gwet's AC1 as a prevalence-robust alternative |
| T10 | Protein identity of recovered models vs Release 102 | Unpaired continuous, n in thousands | **Welch's t-test** on sequence identity, with Welch-Satterthwaite df | Large n makes the t-test robust even with modest non-normality; do not use the pooled-variance variant | Check via Q-Q plot on a random subsample of 500 | Mann-Whitney U |

### 5.3 Manual curation protocol and reliability

Two annotators independently classify the full review queue without seeing each other's labels. Disagreements are adjudicated by a third annotator. Report Cohen's kappa with a 1000-iteration bootstrap CI, plus the raw confusion matrix, plus the per-family breakdown — a single global kappa can hide that one family (typically K2P or ENaC) is where all the difficulty sits, and that family-level detail is what makes the resource usable.

### 5.4 Multiple testing

- Within-family test families (all enrichment terms; all pairwise taxon comparisons) use Benjamini-Hochberg at *q* = 0.05.
- Pre-specified primary hypotheses (H1, H2) are tested at *alpha* = 0.05 without correction, because they are two tests fixed in advance, not a search.
- All other analyses are exploratory and are labelled as such in both the table above and the manuscript.
- The number of tests actually run is reported, not only the number that were significant.

### 5.5 Why there is no meta-analysis here

The meta-analysis machinery in this document (see Project 03, `../03-tempq10/materials-and-methods.md`) is not applicable to P01. P01 compares one annotation against one baseline on one genome; there are no independent studies to pool. Applying random-effects pooling to a set of BUSCO completeness figures from a single annotation would be a category error, and the paper will not do it.

## 6. Data and code availability

- Repository: public GitHub repository, MIT licence, `main` branch archived at submission via Zenodo concept DOI.
- Derived data (repaired GFF, protein FASTA, channel catalogue TSV) deposited in a public repository with a citable DOI, released under CC0.
- Container image digest recorded in the README and in the Zenodo record.
- A `reproduce.sh` script regenerates every figure from a clean clone on a machine with only Docker installed.

## 7. Limitations to be stated in the manuscript

1. The genome is a 2013 scaffold-level assembly. Lift-off quality is bounded by assembly contiguity, and no amount of annotation work fixes that. Any locus spanning a scaffold boundary is flagged as such.
2. The CNS transcriptome is single-ganglion in origin and single-individual in the strict sense; it represents one transcriptome, not a population. Absence of a transcript from it is weak evidence of absence from the genome.
3. Central neurons are highly polyploid, so gene dosage cannot be inferred from this work.
4. The catalogue is a curated subset by design. It is not a complete channel census, and it will not recover channels whose protein products were not captured by the sequencing effort.
5. The comparison to *Elysia* and *Euprymna* is between annotations built by different pipelines on different sequencing technologies. BUSCO comparison is a completeness proxy, not a quality ranking of the underlying groups.
6. Everything in H3 concerns annotation depth. It is not evidence about channel repertoire evolution in molluscs, and must not be phrased as though it were.
