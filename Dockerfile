# AplyNeuroExpress — analysis container
#
# Every tool version is pinned. The image is the unit of reproducibility:
# a result produced outside this container is not a result we can reproduce.
#
# Build:  docker build -t aplysia-neuroexpressome .
# Digest: recorded in the repository README (subtask P01-01.4)
#
# Two stages: the builder carries compilers, the runtime does not, so the
# shipped image carries no build toolchain.
#
# Pins were verified against the anaconda.org package API on 2026-10-03 and
# corrected: 9 of the 26 original pins did not resolve. See
# docs/P01-01-2-image-build.md for the verification table and what changed.

ARG MAMBA_VERSION="23.11"

# ---------------------------------------------------------------- stage 1
FROM mambaorg/micromamba:${MAMBA_VERSION} AS builder

USER root
SHELL ["/usr/local/bin/_entrypoint.sh", "/bin/bash", "-euo", "pipefail", "-c"]

ENV MAMBA_ROOT_PREFIX=/opt/conda
ENV MAMBA_DOCKERFILE_ACTIVATE=1

# biopython 1.83 exists on conda-forge only; bioconda stops at 1.70
RUN micromamba install -y -n base \
        -c conda-forge -c bioconda \
        python=3.11 \
        biopython=1.83 \
        diamond=2.1.8 \
        liftoff=1.3.0 \
        busco=5.7.1 \
        hisat2=2.2.1 \
        samtools=1.19 \
    && micromamba clean --all --yes

# ---------------------------------------------------------------- stage 2
FROM mambaorg/micromamba:${MAMBA_VERSION}

USER root
SHELL ["/usr/local/bin/_entrypoint.sh", "/bin/bash", "-euo", "pipefail", "-c"]

ENV MAMBA_ROOT_PREFIX=/opt/conda
ENV MAMBA_DOCKERFILE_ACTIVATE=1
ENV PATH=/opt/conda/envs/base/bin:$PATH

# Java 11 is required by InterProScan. Pinned, because an unpinned JRE has
# broken InterProScan before.
RUN micromamba install -y -n base -c conda-forge \
        openjdk=11 \
    && micromamba clean --all --yes

# analysis tooling, pinned (P01 methods 2.2, corrected 2026-10-03)
#
# channel notes, all verified 2026-10-03:
#   bioconductor-*      live on bioconda, not on conda-forge
#   limma 3.60          does not exist; the channel goes 3.58.1 -> 3.62.0
#   r-metafor           version string carries a _0 suffix: 4.4_0
#   interproscan        bioconda's newest build is 5.59-91.0, not 5.70-102.0
#   trimal              no .rev22 build; 1.5.1 is current
#   aplotransdecoder    not a conda package; the tool ships as 'transdecoder'
#   tabular             no such package; removed (it was never in the methods)
RUN micromamba install -y -n base \
        -c conda-forge -c bioconda \
        python=3.11 \
        r-base=4.4 \
        bioconductor-limma=3.62.0 \
        bioconductor-edger=4.0 \
        bioconductor-clusterprofiler=4.10 \
        r-metafor=4.4_0 \
        r-ggplot2=3.5 \
        r-patchwork=1.2 \
        r-rstatix=0.7 \
        r-testthat=3.2 \
        interproscan=5.59_91.0 \
        hmmer=3.4 \
        eggnog-mapper=2.1.9 \
        orthofinder=2.5.4 \
        mafft=7.505 \
        trimal=1.5.1 \
        iqtree=2.2.6 \
        transdecoder=5.7.0 \
        gffread=0.9.9 \
    && micromamba clean --all --yes

# Liftoff has no tagged release matching 1.3.0, so it installs from a pinned
# commit. OrthoFinder is available as a tagged release.
ARG LIFTOFF_COMMIT="b8a41b0"
RUN pip install --no-cache-dir --no-deps \
        "git+https://github.com/AdrienLegat/liftoff.git@${LIFTOFF_COMMIT}"
RUN pip install --no-cache-dir --no-deps \
        "git+https://github.com/Embl-EBI/OrthoFinder@2.5.4"

COPY scripts/ /opt/aplysia/bin/
RUN chmod +x /opt/aplysia/bin/*.sh 2>/dev/null || true
ENV PATH=/opt/aplysia/bin:$PATH

# data layout. data/raw is gitignored: inputs are large and are re-fetchable
# from the accessions recorded in data/manifest.tsv.
RUN mkdir -p /workspace/data/raw /workspace/data/derived /workspace/results \
             /workspace/docs /workspace/figures \
    && chown -R $MAMBA_USER:$MAMBA_USER /workspace
USER $MAMBA_USER
WORKDIR /workspace

ENV PIP_DISABLE_PIP_VERSION_CHECK=1
ENV PYTHONHASHSEED=0

# ---- tool manifest: printed on every run and captured in the log ---------
RUN { \
      echo "# environment manifest - generated at image build time"; \
      echo "built: $(date -u +%Y-%m-%dT%H:%M:%SZ)"; \
      for t in python diamond liftoff busco hisat2 samtools InterProScan.pl \
               eggnog-mapper.pl mafft trimal iqtree2 gffread \
               orthofinder TransDecoder.R R java; do \
        v=$(command -v "$t" >/dev/null 2>&1 \
            && ("$t" --version 2>&1 | head -1 || echo present) \
            || echo "NOT FOUND"); \
        printf '%-22s %s\n' "$t" "$v"; \
      done; \
      echo "r-base: $(R --version 2>&1 | head -1)"; \
    } > /opt/aplysia/ENVIRONMENT.txt 2>&1 || true

CMD ["/bin/bash"]
