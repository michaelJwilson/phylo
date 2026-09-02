#!/usr/bin/env bash
# Builds the technical document: regenerates the QA figures and captions
# phylo.qa scripts produce, then builds them into docs/draft.pdf. Build
# tooling, not science -- it orchestrates phylo.qa and latexmk, and knows
# nothing about topologies or models itself (see this directory's CLAUDE.md).
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$repo_root"

uv run python -m phylo.qa.sim_tree \
  --params tests/regression/fixtures/simulation_params_8taxa.yaml \
  --output-dir docs/tex/figures

uv run python -m phylo.qa.sim_example \
  --params tests/regression/fixtures/simulation_params.yaml \
  --output-dir docs/tex/figures

uv run python -m phylo.qa.sim_problem_sizes \
  --params tests/regression/fixtures/simulation_params.yaml \
  --params tests/regression/fixtures/simulation_params_small_sites.yaml \
  --params tests/regression/fixtures/simulation_params_8taxa.yaml \
  --output-dir docs/tex/figures

(
  cd docs/tex
  latexmk -pdf -interaction=nonstopmode -halt-on-error \
    -outdir=.. -jobname=draft main.tex
)

echo "Built docs/draft.pdf"
