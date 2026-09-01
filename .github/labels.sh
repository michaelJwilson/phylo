#!/usr/bin/env bash
# Create (or update) the triage labels. Idempotent: --force overwrites an
# existing label's colour and description rather than failing.
#
#   ./.github/labels.sh
#
# Keep in step with the label table in README.md's "Raising a ticket".
set -euo pipefail

create() { gh label create "$1" --color "$2" --description "$3" --force; }

# State. Each label has exactly one owner; see README.
create "approved"        0e8a16 "Maintainer gate: eligible to be worked"
create "in-progress"     1d76db "Dispatched; a PR is expected"
create "rejected:unsafe" b60205 "Failed the safety screen; never queued"
create "external"        ededed "Author is not a collaborator; automation skipped"

# Topic. Decides which batch the work lands in, and drives the roadmap filters.
create "topic:science"   0052cc "Numerical or phylogenetics behaviour"
create "topic:infra"     0052cc "Build, packaging, dependencies"
create "topic:ci"        0052cc "Workflows and required checks"
create "topic:tests"     0052cc "Regression, property, or benchmark coverage"
create "topic:docs"      0052cc "README, docstrings, Sphinx"
create "topic:claude-md" 0052cc "Conventions and agent guidance"

# Priority. New tickets start low; a maintainer promotes.
create "priority:high"   d93f0b "Runs on approval, unbatched"
create "priority:medium" fbca04 "Runs at the next refresh boundary"
create "priority:low"    c2e0c6 "Next boundary outside working hours; the default"

# Escape hatch.
create "skip-changelog"  ededed "Exempt this PR from the changelog fragment check"
