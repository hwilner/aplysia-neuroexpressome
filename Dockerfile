# AplyNeuroExpress — analysis container
#
# Every tool version is pinned. The image is the unit of reproducibility:
# a result produced outside this container is not a result we can reproduce.
#
# Build:  docker build -t aplysia-neuroexpressome .
# Record: the image digest goes in the repository README (subtask P01-01.4)
#
# Subtask P01-01.1. Multi-stage: the builder carries compilers, the runtime
# does not, so the shipped image carries no build toolchain.

ARG MAMBA_VERSION="23.11"

# ---------------------------------------------------------------- stage 1
FROM mambaorg/micromamba:${MAMBA_VERSION} AS builder

USER root
SHELL ["/usr/local/bin/_entrypoint.sh", "/bin/bash", "-euo", "pipefail", "-c"]

ENV MAMBA_ROOT_PREFIX=/opt/conda
ENV MAMBA_DOCKERFILE_ACTIVATE=1

RUN micromamba install -y -n base -c conda-forge -c bioconda \
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

# analysis tooling, pinned (P01 methods 2.2)
RUN micromamba install -y -n base -c conda-forge -c bioconda \
        python=3.11 \
        r-base=4.4 \
        bioconductor-limma=3.60 \
        bioconductor-edger=4.0 \
        bioconductor-clusterProfiler=4.10 \
        r-metafor=4.4 \
        r-ggplot2=3.5 \
        r-patchwork=1.2 \
        r-rstatix=0.7 \
        r-testthat=3.2 \
        interproscan=5.70-102.0 \
        hmmer=3.4 \
        eggnog-mapper=2.1.9 \
        orthofinder=2.5.4 \
        mafft=7.505 \
        trimal=1.4.rev22 \
        iqtree=2.2.6 \
        applotransdecoder=3.0.0 \
        gffread=0.9.9 \
        tabular=1.0 \
    && micromamba clean --all --yes

# Liftoff and the annotation tools ship as git installs; pin the commit.
ARG LIFTOFF_COMMIT="b8a41b0"
ARG ORTHOFINDER_COMMIT=""
RUN pip install --no-cache-dir --no-deps "git+https://github.com/AdrienLegat/liftoff.git@${LIFTOFF_COMMIT}" \
    && pip install --no-cache-dir --no-deps "git+https://github.com/Embl-EBI/OrthoFinder@2.5.4"

# scripts the pipeline writes into $PATH at runtime
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
      echo "# environment manifest — generated at image build time"; \
      echo "built: $(date -u +%Y-%m-%dT%H:%M:%SZ)"; \
      echo "base:  $(cat /opt/conda/conda-meta/history 2>/dev/null | head -1)"; \
      for t in python diamond liftoff busco hisat2 samtools InterProScan.pl \
               eggnog-mapper.pl diamond mafft trimal iqtree2 gffread \
               orthofinder applotransdecoder R; do \
        v=$(command -v "$t" >/dev/null 2>&1 && ("$t" --version 2>&1 | head -1 || echo present)); \
        printf '%-22s %s\n' "$t" "$v"; \
      done; \
      echo "r-base: $(R --version 2>&1 | head -1)"; \
    } > /opt/aplysia/ENVIRONMENT.txt 2>&1 || true

CMD ["/bin/bash"]
