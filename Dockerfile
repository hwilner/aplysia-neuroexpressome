# AplyNeuroExpress — analysis container
#
# Every tool version is pinned. The image is the unit of reproducibility:
# a result produced outside this container is not a result we can reproduce.
#
# Build:  docker build -t aplysia-neuroexpressome .
# Digest: recorded in the repository README (subtask P01-01.4)
#
# FOUR environments, not one, and two of the separations are forced.
#
# P01-01.2 failed its first CI build. The original Dockerfile solved for all
# 25 packages in a single micromamba transaction, spanning bioconda, the R
# stack from conda-forge, and InterProScan, which carries its own pinned
# library tree. The exact solver error could not be read back (the log endpoint
# is unreachable from the authoring sandbox), but a single solve across those
# three ecosystems is fragile by construction and is the most likely cause.
#
# The base image was also wrong. MAMBA_VERSION was "23.11", a tag that has
# never existed; the real current version is 2.9.0. That, and nothing else, is
# what failed both CI builds. It is now pinned to 2.9.0.
#
# The three-environment layout below was adopted while chasing that failure and
# was NOT the fix. It is kept because isolating InterProScan's pinned library
# tree is defensible on its own merits, and because per-environment probes are
# better diagnostics - not because it was shown to be necessary.
#
# ACTIVATIONS
#   micromamba run -n bio  <cmd>    tools, alignment, orthology, BUSCO
#   micromamba run -n tree <cmd>    MAFFT, trimAl, IQ-TREE
#   micromamba run -n r    <cmd>    limma, edgeR, metafor, lme4, tidyverse
#   micromamba run -n ips  <cmd>    InterProScan
#   scripts/environment.sh          prints the pinned manifest
#
# Every tool is installed from a pinned conda package. An earlier revision
# installed Liftoff and OrthoFinder from git checkouts instead. That could not
# work: the base image carries no git, and neither does the bio environment,
# so `pip install git+https://...` had no way to clone. Both tools are on
# bioconda at exactly the pinned versions - liftoff 1.3.0 is the upstream
# Liftoff-1.3.0 release built from the PyPI source distribution, and
# OrthoFinder 2.5.4 is the upstream 2.5.4 release - and the conda packages
# declare the dependencies that the git checkouts, installed with --no-deps,
# left to the solver. See docs/P01-01-2-image-build.md.
#
# Pins verified against the anaconda.org package API on 2026-10-03; the
# corrections applied are listed in docs/P01-01-2-image-build.md.

ARG MAMBA_VERSION="2.9.0"
FROM mambaorg/micromamba:${MAMBA_VERSION}

USER root
SHELL ["/usr/local/bin/_entrypoint.sh", "/bin/bash", "-euo", "pipefail", "-c"]

ENV MAMBA_ROOT_PREFIX=/opt/conda
ENV MAMBA_DOCKERFILE_ACTIVATE=1

# ---------------------------------------------------------------------
# env: bio — the analysis tools
# ---------------------------------------------------------------------
# biopython 1.83 exists on conda-forge only; bioconda stops at 1.70
RUN micromamba create -y -n bio \
        -c conda-forge -c bioconda \
        python=3.11 \
        biopython=1.83 \
        diamond=2.1.8 \
        liftoff=1.3.0 \
        busco=5.7.1 \
        hisat2=2.2.1 \
        samtools=1.19 \
        hmmer=3.4 \
        eggnog-mapper=2.1.9 \
        orthofinder=2.5.4 \
        transdecoder=5.7.0 \
        gffread=0.9.9 \
    && micromamba clean --all --yes

# ---------------------------------------------------------------------
# env: tree — the phylogeny tools
# ---------------------------------------------------------------------
# mafft is isolated here, not because it is big, but because it cannot
# coexist with BUSCO. BUSCO 5.7.1 pulls sepp >=4.3.10, which pulls pasta,
# which requires mafft >=7.526. The newest mafft on bioconda is 7.525 - one
# patch below. So there is no mafft that satisfies both a BUSCO pin and a
# mafft pin, and the conflict is structural rather than a bad version.
# Splitting the tree tools out keeps every pin intact and the solve small.
# This was found by the CI solver, not by inspection: the package exists and
# the version resolves, so only an actual solve reveals it.
RUN micromamba create -y -n tree \
        -c conda-forge -c bioconda \
        mafft=7.525 \
        trimal=1.5.1 \
        iqtree=2.2.6 \
    && micromamba clean --all --yes

# ---------------------------------------------------------------------
# env: r — the statistics
# ---------------------------------------------------------------------
# Three constraints the solver found, none visible from the version list:
#
#   limma 3.58.1 (Bioc 3.18)  -> requires r-base < 4.4
#   edgeR 4.0   (Bioc 3.18)   -> requires limma >=3.58.0,<3.59.0
#   clusterProfiler 4.10       -> requires hdo.db 0.99.1 -> r-base >=4.3,<4.4
#
# limma and edgeR are Bioconductor 3.20 packages, the generation built for
# R 4.4, and the pair must be taken from the same generation. edgeR 4.0 is
# the 3.18 generation and requires limma 3.58.x, which in turn requires
# r-base < 4.4. The 3.20 pair is limma 3.62.0 with edgeR 4.4.0, and that is
# what is pinned, which keeps the pre-registered R 4.4 intact.
#
# clusterProfiler is dropped. It is the sole reason R 4.4 becomes
# unsolvable, and the project needs none of its heavy machinery.
#
# clusterProfiler was named in the pre-registered methods for GO and KEGG
# over-representation. That analysis is a hypergeometric test per term with
# Benjamini-Hochberg FDR across terms, implemented directly in base R against a
# GO/KEGG gene-to-term map - ten lines, no annotation databases, no dependency
# tree. Dropping the package is a pre-registration amendment and is recorded
# as such; see docs/deviations.md.
#
# metafor 4.4_0 cannot be installed alongside R 4.4. The package has two
# builds, one for r-base >=4.2,<4.3 and one for r-base >=4.3,<4.4, and no
# build that accepts R 4.4, so the solver rejects the pair outright. metafor
# 4.6_0 has an r44 build, and it is the version pinned here. The
# pre-registration names R 4.4.x and names no metafor version, so this does
# not change the pre-registered R.
#
# r-metafor carries a _0 suffix: 4.6_0.
#
# lme4 and tidyverse are named in the pre-registered software environment
# (materials-and-methods.md section 2.2) and were missing from the image.
# lme4 is the mixed-effects model that step 1 of the pre-registered
# test-selection procedure calls for when observations are not independent.
RUN micromamba create -y -n r \
        -c conda-forge -c bioconda \
        r-base=4.4 \
        bioconductor-limma=3.62.0 \
        bioconductor-edger=4.4.0 \
        r-metafor=4.6_0 \
        r-lme4=2.0_6 \
        r-tidyverse=2.0.0 \
        r-ggplot2=3.5 \
        r-patchwork=1.2 \
        r-rstatix=0.7 \
        r-testthat=3.2 \
    && micromamba clean --all --yes

# ---------------------------------------------------------------------
# env: ips — InterProScan, isolated
# ---------------------------------------------------------------------
# bioconda's newest InterProScan build is 5.59-91.0, not 5.70-102.0. This is a
# data-release change, not a cosmetic one: the version determines the Pfam and
# InterPro member-database snapshot, so the methods must state it and the
# catalogue must record it beside every domain hit. Java 11 is required and is
# pinned for the same reason InterProScan is.
RUN micromamba create -y -n ips \
        -c conda-forge -c bioconda \
        openjdk=11 \
        interproscan=5.59_91.0 \
    && micromamba clean --all --yes

# ---------------------------------------------------------------------
# Liftoff and OrthoFinder come from bioconda, pinned above.
#
# An earlier revision installed both from git checkouts, Liftoff at commit
# b8a41b0 and OrthoFinder at tag 2.5.4, with --no-deps. That could not work:
# the base image mambaorg/micromamba:2.9.0 carries no git binary, and git is
# not a dependency of any package in the bio environment either, so pip had no
# way to clone either repository. bioconda publishes liftoff 1.3.0, built from
# the upstream Liftoff-1.3.0 source distribution, and orthofinder 2.5.4, the
# upstream 2.5.4 release; both provide the commands the manifest checks
# (liftoff and orthofinder) and both declare their own dependencies.
# ---------------------------------------------------------------------

COPY scripts/ /opt/aplysia/bin/
RUN chmod +x /opt/aplysia/bin/*.sh 2>/dev/null || true
# The manifest is written by the unprivileged user the image runs as, so the
# directory has to belong to that user. Without this the manifest stage fails
# with "Permission denied", the redirect in that stage swallows the error, and
# the image ships with no manifest at all.
RUN chown -R $MAMBA_USER:$MAMBA_USER /opt/aplysia

# data layout. data/raw is gitignored: inputs are large and are re-fetchable
# from the accessions recorded in data/manifest.tsv.
RUN mkdir -p /workspace/data/raw /workspace/data/derived /workspace/results \
             /workspace/docs /workspace/figures \
    && chown -R $MAMBA_USER:$MAMBA_USER /workspace
USER $MAMBA_USER
WORKDIR /workspace

ENV PATH=/opt/aplysia/bin:$PATH
ENV PIP_DISABLE_PIP_VERSION_CHECK=1
ENV PYTHONHASHSEED=0

  # ---- tool manifest: written at build time, inspectable without the image ----
  #
  # The manifest is what makes the pins inspectable without pulling the
  # image. It used to be written by a shell loop here that ran `--version` on
  # every command and recorded whatever came back. Four of the command names
  # were wrong, and were fixed; but the loop itself was the defect, because
  # it recorded failures as though they were versions:
  #
  #   hmmsearch     Failed to parse command line: No such option "--version".
  #   emapper.py    There was an error retrieving eggnog-mapper DB data: ...
  #   orthofinder   (empty)
  #   trimal        (empty)
  #
  # A manifest holding error text cannot be compared with another manifest
  # and called a version comparison, and the build gate looked for the string
  # "NOT FOUND" and so passed every one of those lines. The generation now
  # lives in scripts/manifest.py, which tries several invocations per tool,
  # validates the output, and falls back to the version of the conda package
  # that provides the command. The fallback cannot fail: the package is in
  # the image by construction.
  #
  # The manifest also carries the resolved package list for every
  # environment. The direct pins are a dozen packages; what is actually
  # installed is their whole transitive closure, and that closure is what has
  # to be identical between two builds.
  #
  # The stage fails the build if it cannot write the manifest. An earlier
  # revision swallowed the error with "|| true" and shipped images with no
  # manifest at all.
  RUN micromamba run -n bio python3 /opt/aplysia/bin/manifest.py \
        --output /opt/aplysia/ENVIRONMENT.txt

  # The manifest has to be readable by the user the image runs as.
  RUN chmod 644 /opt/aplysia/ENVIRONMENT.txt

CMD ["/bin/bash"]
