# P01 AplyNeuroExpress — project Gantt (repo: aplysia-neuroexpressome)

Machine-readable versions of this plan live alongside it: `tasks.csv` (GitHub Projects import, with a `Depends on` column) and `gantt.mmd` (Mermaid Gantt). Dates are identical to the programme schedule — this file is a view of the programme plan, not a re-plan.

**Cross-project relationship.** P01 is the head of the programme's critical path (**P01 → P02**). Its repaired gene models and channel catalogue feed P02's expression quantification as a *soft* dependency: P02 is designed to run against either Release 102 or the P01 models, but if P01 delivers, its models become P02's primary analysis and the Release 102 run becomes a robustness check. The three-week winter gap after P01 exists to absorb a P01 overrun before P02 starts.

## The one-paragraph version

Eleven weeks, 2026-10-05 → 2026-12-18, to turn RefSeq Release 102 plus the Orvis 2022 transcriptome into a repaired gene-model set and a curated ion-channel catalogue, with the before/after comparison as primary hypothesis H1. Two gates protect the project: G1 checks the baseline is adequate for a paired comparison at all, and G2 checks the Liftoff route before the compute budget is committed to it. The tail of the project is deliberately uncompressible — dual-annotator blind curation with adjudication, the full T1–T10 test battery, script-generated figures, manuscript, and a Zenodo release in the final week. If both primary criteria fail, the negative result is published; that outcome is in scope.

## Task table

| ID | Task | Start | End | Depends on |
|---|---|---|---|---|
| P01-01 | Pin container environment and toolchain | 2026-10-05 | 2026-10-09 | — |
| P01-02 | Acquire AplCal3.0 and RefSeq Release 102 | 2026-10-05 | 2026-10-07 | — |
| P01-03 | Acquire AplysiaTools and Orvis 2022 transcriptome | 2026-10-05 | 2026-10-08 | — |
| P01-04 | BUSCO baseline on Release 102 | 2026-10-12 | 2026-10-14 | P01-02 |
| P01-05 | Per-locus fragmentation diagnostics | 2026-10-12 | 2026-10-16 | P01-02 |
| P01-06 | Cross-annotation BUSCO for Elysia and Euprymna | 2026-10-19 | 2026-10-21 | P01-02 |
| P01-07 | GATE G1 — baseline adequacy review | 2026-10-21 | 2026-10-22 | P01-04 |
| P01-08 | Liftoff lift-off of transcriptome onto AplCal3.0 | 2026-10-19 | 2026-10-23 | P01-02, P01-03 |
| P01-09 | GATE G2 — lift coverage review | 2026-10-26 | 2026-10-27 | P01-08 |
| P01-10 | Transcriptome ORF prediction | 2026-10-26 | 2026-10-30 | P01-03 |
| P01-11 | Gene-model repair and reconciliation | 2026-11-02 | 2026-11-13 | P01-05, P01-09, P01-10 |
| P01-12 | OrthoFinder and eggNOG-mapper | 2026-11-09 | 2026-11-20 | P01-11 |
| P01-13 | Pfam and InterProScan channel-family sweep | 2026-11-16 | 2026-11-20 | P01-11 |
| P01-14 | Membrane topology prediction | 2026-11-23 | 2026-11-25 | P01-13 |
| P01-15 | Dual-annotator manual curation queue | 2026-11-23 | 2026-12-04 | P01-13 |
| P01-16 | Kappa analysis and third-annotator adjudication | 2026-12-07 | 2026-12-09 | P01-15 |
| P01-17 | Isoform analysis for key channel loci | 2026-12-01 | 2026-12-04 | P01-13 |
| P01-18 | Enrichment and cross-species statistics | 2026-12-07 | 2026-12-10 | P01-12, P01-16 |
| P01-19 | Statistical tests T1-T4 and T10 | 2026-12-07 | 2026-12-10 | P01-05, P01-06, P01-11 |
| P01-20 | Figure generation from scripts | 2026-12-14 | 2026-12-16 | P01-16, P01-17, P01-18, P01-19 |
| P01-21 | Manuscript draft | 2026-12-14 | 2026-12-18 | P01-18, P01-19, P01-20 |
| P01-22 | Zenodo release and repository archive | 2026-12-18 | 2026-12-18 | P01-21 |

## Text Gantt (weekly resolution)

```
                                                    Oct05 Oct12 Oct19 Oct26 Nov02 Nov09 Nov16 Nov23 Nov30 Dec07 Dec14
P01-01 Pin container environment and toolchain       ███                                                   
P01-02 Acquire AplCal3.0 and RefSeq Release 102      ███                                                   
P01-03 Acquire AplysiaTools and Orvis 2022 transcr…  ███                                                   
P01-04 BUSCO baseline on Release 102                      ███                                              
P01-05 Per-locus fragmentation diagnostics                ███                                              
P01-06 Cross-annotation BUSCO for Elysia and Eupry…            ███                                         
P01-07 GATE G1 — baseline adequacy review                       ◆                                          
P01-08 Liftoff lift-off of transcriptome onto AplC…            ███                                         
P01-09 GATE G2 — lift coverage review                                ◆                                     
P01-10 Transcriptome ORF prediction                                 ███                                    
P01-11 Gene-model repair and reconciliation                              ███  ███                          
P01-12 OrthoFinder and eggNOG-mapper                                          ███  ███                     
P01-13 Pfam and InterProScan channel-family sweep                                  ███                     
P01-14 Membrane topology prediction                                                     ███                
P01-15 Dual-annotator manual curation queue                                             ███  ███           
P01-16 Kappa analysis and third-annotator adjudica…                                               ███      
P01-17 Isoform analysis for key channel loci                                                 ███           
P01-18 Enrichment and cross-species statistics                                                    ███      
P01-19 Statistical tests T1-T4 and T10                                                            ███      
P01-20 Figure generation from scripts                                                                  ███ 
P01-21 Manuscript draft                                                                                ███ 
P01-22 Zenodo release and repository archive                                                            ■  

██ active week   ◆ gate (decision point)   ■ release day   weeks start Mondays; span 2026-10-05 -> 2026-12-18
```

## Critical path within P01

Each link is a genuine dependency, not a sequencing preference.

1. **P01-02 → P01-04 → P01-07 (GATE G1).** The BUSCO baseline on Release 102 is the "before" arm of H1. If it is below 90% metazoan completeness, the paired comparison is void and scope drops to the channel subset — decided at G1 on 2026-10-22, not discovered at analysis time.
2. **P01-02 + P01-03 → P01-08 → P01-09 (GATE G2).** The lift-off of the transcriptome onto AplCal3.0 is the cheapest route to better models, but only if it covers ≥ 60% of transcriptome proteins. G2 on 2026-10-27 is the last cheap exit onto the SRA remap + BRAKER3 fallback, which costs ~3 weeks of compute and schedule.
3. **P01-09 → P01-11 → P01-13 → P01-15 → P01-16.** Gene-model repair (Hsiao 2024 logic) produces the models; the Pfam/InterProScan sweep turns them into a channel catalogue; dual-annotator curation validates the catalogue; kappa with adjudication makes the curation defensible. None of these can start before the previous one produces its output.
4. **P01-05/P01-06/P01-11 → P01-19 → P01-20 → P01-21 → P01-22.** The primary tests T1–T4 and T10 need the fragmentation diagnostics, the cross-annotation baseline, and the repaired models; figures are generated from the stats; the manuscript is written against stats and figures; the release archives the manuscript state. Release is same-day with manuscript completion — zero slack by design.

## Gate register (P01 only)

| Gate | Condition | If failed |
|---|---|---|
| **G1** (P01-07, 2026-10-22) | Baseline metazoan BUSCO >= 90% | Paired comparison is void; scope drops to the channel subset only |
| **G2** (P01-09, 2026-10-27) | Lift-off covers >= 60% of transcriptome proteins | Abandon the lift route; fall back to SRA remap + BRAKER3 (raises compute budget materially) |

## Longest-lead items

- **P01-11 Gene-model repair** — 10 working days, on the critical path, and the input to OrthoFinder, the channel sweep, the isoform analysis, and the primary tests. The single most load-bearing task in the project.
- **P01-15 Dual-annotator manual curation** — 10 working days and deliberately uncompressible: it cannot be halved and still report a kappa. Book the second annotator before the sweep finishes.
- **P01-12 OrthoFinder and eggNOG-mapper** — 10 working days of wall-clock compute; starts 2026-11-09, four days before repair (P01-11) completes on 2026-11-13. The overlap assumes the first repaired families are available in batches; if repair delivers nothing until the end, OrthoFinder slips day-for-day.

## What breaks this project

| Failure | Likelihood | Effect | Response |
|---|---|---|---|
| G2 fails, SRA+BRAKER3 fallback needed | Moderate | P01 grows by ~3 weeks | Absorb the winter gap; P02 slips to 2027-01-25 |
| Reviewer requests a wet-lab validation | High | Cannot be satisfied solo | Decline and reframe the claim as a resource. Do not invent validation |
| Gaps in references/bibliography.bib during pre-registration | Low | Blocks the timestamp claim | Fix before the first analysis run; the pre-registration must be verifiable from history |
| Illness, teaching load, life | Realistic | Slips everything downstream | The winter gap is the only buffer before P02 |

## First actions

1. Create the `aplysia-neuroexpressome` repository with an MIT licence and a `docs/` directory.
2. Start P01-01 on 2026-10-05: pin the container, record the image digest in the README. No step runs outside the container.
3. Start P01-02 the same day: acquire AplCal3.0 and RefSeq Release 102, record SHA-256 for all inputs in `data/manifest.tsv`.
4. Fill `references/bibliography.bib` to the level needed for the pre-registration, and commit it with a timestamp before the first analysis run.
