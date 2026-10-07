envelope_version=1
sender_type=plan
sender_id=plan-13-finalize-mechanism-defects
epic=process-compliance
kind=finding
created=2026-09-28T18:29:41Z

# Residual stale runtime-state paths after PLAN-13's sweep (supersedes issue 12 of message 004)

PLAN-13 (PR #1651, merge c56710b) swept stale pre-ADR-002 runtime-state paths out of ~40 marketplace
docs, but only within the files the self-review loop reached. Issue 12 in message 004 described the
pre-sweep `.plan/plans/` population and is now outdated. This message records the residue as it stands
on main at c56710b, from a fresh `architecture search --content --literal` sweep (3523 inventoried files;
`.claude/**` and `.github/**` are inventory-allowlisted and were covered; git-ignored trees were not).

## Residue

`.plan/logs/` (13 hits, 7 files). Runtime logs resolve to `get_base_dir() / DIR_LOGS` =
`<plan-root>/.plan/local/logs`:

- `marketplace/bundles/plan-marshall/skills/manage-logging/scripts/manage-logging.py` (3; the review
  named lines 22 and 35)
- `marketplace/bundles/plan-marshall/skills/manage-locks/scripts/_locks_core.py` (1)
- `marketplace/bundles/plan-marshall/skills/extension-api/standards/ext-point-build.md` (2)
- `marketplace/bundles/plan-marshall/skills/marshall-steward/references/wizard-flow.md` (2)
- `doc/user/efforts.adoc` (1)
- `test/plan-marshall/manage-logging/test_manage_logging.py` (2)
- `test/plan-marshall/audit-archived-plan-retrospectives/test_audit_check_merge_window_accounting.py` (1)

`status.toon` (2 files). The live status file is `status.json`:

- `marketplace/bundles/plan-marshall/skills/plan-retrospective/scripts/collect-plan-artifacts.py`
- `test/plan-marshall/manage-files/test_manage_files_content_lifecycle.py`

`.plan/plans/` (30 hits, 15 files). Most are likely intentional and need triage, not a blind rewrite:
the plugin-doctor rule `_analyze_plan_path_in_scripts.py` detects this legacy path by design (its
rule-catalog/rule-provenance docs and tests name it), and several tests assert the canonical-path
migration. Candidates that look like genuine drift and need a per-hit check:

- `marketplace/bundles/plan-marshall/skills/phase-6-finalize/scripts/ci_complete_precondition.py` (1)
- `test/plan-marshall/manage-logging/test_logging.py`, `manage-metrics/test_manage_metrics.py`,
  `manage-references/test_manage_references.py`, `manage-status/test_manage_status_read_cmd_set_phase.py`,
  `manage-ci-artifacts/test_manage_ci_artifacts_cli.py`, `tools-file-ops/test_file_ops.py`,
  `plan-retrospective/test_footprint_oracle_classification_*.py`

Leftovers the PLAN-13 self-review named but never filed, to re-check by hand (not literal-path hits):

- `manage-run-config/scripts/_cmd_cleanup.py:46-48` (comment)
- `plan-retrospective/references/artifact-consistency.md` (path fragment)
- `phase-6-finalize/standards/emit-landing.md` lines 45, 64, 338 (internal inconsistencies)

Clean on main: `.plan/archived/` and `.plan/archived-plans` (without `local/`) have zero hits.

## Proposed follow-up plan

One plan that completes the runtime-state path migration repo-wide and makes it self-enforcing:

1. Correct the residue above (code, docs, tests), triaging each `.plan/plans/` hit as intentional
   (detector/migration test) or drift.
2. Add a doc-vs-resolver parity test for the live-plan, log, and status-file paths, extending
   PLAN-13's `test_archive_path_doc_resolver_parity.py` pattern (archive path) to `get_base_dir()`,
   `DIR_LOGS`, and the status filename, over the full inventory with an explicit allowlist for the
   plugin-doctor detector and migration tests.
3. Scope it as a full-repo migration up front: PLAN-13 showed that discovering a partial path
   migration inside pre-submission-self-review cannot converge (message 004 issues 14 and 19).
