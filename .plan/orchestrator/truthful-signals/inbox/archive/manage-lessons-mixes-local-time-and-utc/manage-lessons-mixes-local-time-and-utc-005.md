envelope_version=1
sender_type=plan
sender_id=manage-lessons-mixes-local-time-and-utc
epic=truthful-signals
kind=candidate-lesson
created=2026-07-29T16:39:11Z

component=plan-marshall:manage-change-ledger
category=bug
created=2026-07-29

# Freshness check reported `fresh` while attributing the match to a notation absent from the project

`pre-commit-verify-freshness` returned `status: fresh` with `matched_notation: plan-marshall:build-npm:js_coverage` while gating a finalize step on a Python-only project tree that has no JS build system present at all. The check was green, but the notation it credited the freshness to could not possibly have produced the ledger entry it matched against for this project.

## Solution

The freshness matcher should validate that a matched notation's owning build system is actually present/applicable to the current project (or at minimum flag a low-confidence match) before reporting `fresh` on its strength — a `fresh` verdict attributed to an inapplicable notation is not evidence of anything for the notation that actually mattered.

## Impact

Same "confident signal hides a caveat" pattern as the epic theme: a green freshness gate is not proof the RIGHT build was verified fresh. Any project with multiple build-system notations registered in its ledger (even ones it doesn't actually use) is at risk of this mis-attribution.
