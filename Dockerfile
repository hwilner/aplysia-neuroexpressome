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
#   micromamba run -n r    <cmd>    limma, edgeR, clusterProfiler, metafor
#   micromamba run -n ips  <cmd>    InterProScan
#   scripts/environment.sh          prints the pinned manifest for all four
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
# The Bioconductor packages live on bioconda, not conda-forge, and their
# versions track the R release. limma 3.60 does not exist; the channel goes
# 3.58.1 -> 3.62.0. r-metafor carries a _0 suffix: 4.4_0.
RUN micromamba create -y -n r \
        -c conda-forge -c bioconda \
        r-base=4.4 \
        bioconductor-limma=3.62.0 \
        bioconductor-edger=4.0 \
        bioconductor-clusterprofiler=4.10 \
        r-metafor=4.4_0 \
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
# Liftoff installs from a pinned commit: no tag matches 1.3.0.
# ---------------------------------------------------------------------
ARG LIFTOFF_COMMIT="b8a41b0"
RUN micromamba run -n bio pip install --no-cache-dir --no-deps \
        "git+https://github.com/AdrienLegat/liftoff.git@${LIFTOFF_COMMIT}" \
    && micromamba run -n bio pip install --no-cache-dir --no-deps \
        "git+https://github.com/Embl-EBI/OrthoFinder@2.5.4"

COPY scripts/ /opt/aplysia/bin/
RUN chmod +x /opt/aplysia/bin/*.sh 2>/dev/null || true

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

# ---- tool manifest: printed on every run and captured in the log ---------
RUN { \
      echo "# environment manifest - generated at image build time"; \
      echo "built: $(date -u +%Y-%m-%dT%H:%M:%SZ)"; \
      echo; \
      echo "## env: bio"; \
      for t in python diamond liftoff busco hisat2 samtools hmmer-hsearch \
               eggnog-mapper.pl gffread orthofinder TransDecoder.R; do \
        v=$(micromamba run -n bio bash -c "command -v $t >/dev/null 2>&1 && ($t --version 2>&1 | head -1 || echo present) || echo 'NOT FOUND'"); \
        printf '%-22s %s\n' "$t" "$v"; \
      done; \
      echo; \
      echo "## env: tree"; \
      for t in mafft trimal iqtree2; do \
        v=$(micromamba run -n tree bash -c "command -v $t >/dev/null 2>&1 && ($t --version 2>&1 | head -1 || echo present) || echo 'NOT FOUND'"); \
        printf '%-22s %s\n' "$t" "$v"; \
      done; \
      echo; \
      echo "## env: r"; \
      micromamba run -n r Rscript -e 'cat("R ", R.version.string, "\n", sep=""); \
        for (p in c("limma","edgeR","clusterProfiler","metafor","ggplot2","patchwork","rstatix","testthat")) \
          cat(sprintf("%-22s %s\n", p, tryCatch(as.character(packageVersion(p)), error=function(e) "NOT FOUND")))' \
        2>/dev/null || echo "R NOT FOUND"; \
      echo; \
      echo "## env: ips"; \
      micromamba run -n ips bash -c 'java -version 2>&1 | head -1; \
        printf "%-22s %s\n" InterProScan "$(InterProScan.sh -h 2>&1 | grep -i version | head -1 || echo present)"' \
        2>/dev/null || echo "InterProScan NOT FOUND"; \
    } > /opt/aplysia/ENVIRONMENT.txt 2>&1 || true

CMD ["/bin/bash"]
