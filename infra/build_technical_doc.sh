#!/usr/bin/env bash
# Builds the technical document: regenerates the QA figures and captions
# phylo.qa scripts produce, then builds them into docs/draft.pdf. Build
# tooling, not science -- it orchestrates phylo.qa and latexmk, and knows
# nothing about topologies or models itself (see this directory's CLAUDE.md).
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$repo_root"

# docs/draft.pdf is committed, so identical inputs must produce identical
# bytes. Both matplotlib (the QA figures below) and pdftex (the LaTeX build)
# honor SOURCE_DATE_EPOCH, embedding it as their PDF /CreationDate instead of
# the current wall-clock time; a fixed constant keeps every rebuild
# byte-identical regardless of when it runs, which is what CI's staleness
# check relies on.
export SOURCE_DATE_EPOCH=1735689600
# SOURCE_DATE_EPOCH alone fixes the PDF's /CreationDate but not \today, which
# reads pdftex's \year/\month/\day primitives -- those follow the wall clock
# unless FORCE_SOURCE_DATE is set. The title page prints \today, so without
# this the rendered first page changes date every day and the staleness check
# below fails on a PR that touched nothing.
export FORCE_SOURCE_DATE=1

uv run python -m phylo.qa.sim_tree \
  --params tests/regression/fixtures/simulation_params_8taxa.yaml \
  --output-dir docs/tex/figures

uv run python -m phylo.qa.sim_example \
  --params tests/regression/fixtures/simulation_params.yaml \
  --output-dir docs/tex/figures

uv run python -m phylo.qa.jc_transition \
  --params tests/regression/fixtures/simulation_params.yaml \
  --output-dir docs/tex/figures

# Brute-force marginalization costs k**m for m internal nodes, so this runs on
# the 4-taxon fixture and nowhere larger.
uv run python -m phylo.qa.backend_agreement \
  --params tests/regression/fixtures/simulation_params.yaml \
  --output-dir docs/tex/figures

uv run python -m phylo.qa.sim_problem_sizes \
  --params tests/regression/fixtures/simulation_params.yaml \
  --params tests/regression/fixtures/simulation_params_small_sites.yaml \
  --params tests/regression/fixtures/simulation_params_8taxa.yaml \
  --output-dir docs/tex/figures

# The optimization figures refit both reference instances many times over,
# which is why they are here and not in the per-PR test suite: the coverage
# sweep alone is ~40 s. See python/phylo/qa/opt_coverage.py for the sizes.
uv run python -m phylo.qa.opt_recovery \
  --potts-params tests/regression/fixtures/potts_params.yaml \
  --hmm-params tests/regression/fixtures/hmm_params.yaml \
  --output-dir docs/tex/figures

uv run python -m phylo.qa.opt_coverage \
  --potts-params tests/regression/fixtures/potts_params.yaml \
  --hmm-params tests/regression/fixtures/hmm_params.yaml \
  --output-dir docs/tex/figures

uv run python -m phylo.qa.opt_branch_recovery \
  --unrooted-params tests/regression/fixtures/simulation_params_small_sites.yaml \
  --rooted-params tests/regression/fixtures/simulation_params_8taxa.yaml \
  --output-dir docs/tex/figures

uv run python -m phylo.qa.opt_model_recovery \
  --params tests/regression/fixtures/simulation_params_8taxa.yaml \
  --output-dir docs/tex/figures

# The search figures each sweep all 105 unrooted topologies on the 6-taxon
# fixture, which is why they are here and not in the per-PR suite.
uv run python -m phylo.qa.search_trajectory \
  --params tests/regression/fixtures/simulation_params_6taxa.yaml \
  --output-dir docs/tex/figures

uv run python -m phylo.qa.search_topologies \
  --params tests/regression/fixtures/simulation_params_6taxa.yaml \
  --output-dir docs/tex/figures

# The reward-surface comparison scores all 105 topologies twice, once of them
# at one optimization per topology. Same reason as above.
uv run python -m phylo.qa.rl_reward_surface \
  --params tests/regression/fixtures/simulation_params_6taxa.yaml \
  --output-dir docs/tex/figures

# A site-count sweep with replicates at each size: the slowest figure in the
# build, and the only measurement of the accuracy requirement.
uv run python -m phylo.qa.topology_accuracy \
  --params tests/regression/fixtures/simulation_params_6taxa.yaml \
  --output-dir docs/tex/figures

(
  cd docs/tex
  latexmk -pdf -interaction=nonstopmode -halt-on-error \
    -outdir=.. -jobname=draft main.tex
)

echo "Built docs/draft.pdf"
