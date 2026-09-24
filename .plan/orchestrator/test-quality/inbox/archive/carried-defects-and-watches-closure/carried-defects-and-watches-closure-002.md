envelope_version=1
sender_type=plan
sender_id=carried-defects-and-watches-closure
epic=test-quality
kind=landing
created=2026-09-23T20:59:36Z

# PLAN-183 review triage + fix commit (carried-defects-and-watches-closure)

## landing-facts
- pr: #1602
- fix_commit: 5f4f73cb6
- files: 4 (all inside PLAN-183 Expected Surface + D1 kwarg-test, see scope note)
- threads_replied: 5
- threads_resolved: 5
- tier_m_skip_bot_review: n
- coderabbit_skipped: n (reviewed, 5 actionable)
- sourcery_present: y (rate-limit notice only, no findings)

## Triage (FIX / ACCEPT core)
- FIX A1 (CI): `test_env_var_named_env_treated_as_pythonpath` asserted the exact name-only trust D1 orders removed. Replaced with flagged-when-unbound + passes-when-bound pair. Scope note: D1's Done clause explicitly demands "the kwarg test proves the PYTHONPATH behavior" — this file IS that test, so the edit is read as D1 scope, recorded here for operator overrule.
- FIX A2 (CI): R5 armed guard flagged the registry-derived parametrize. Added binding-site `assert _TWO_PART_GROUPS` (the exact guard R5 credits). In-scope D2 test file.
- FIX B1 (Major): registry/dispatch drift risk → `test_operation_registry_matches_dispatch_literals` derives both populations at test time (registry import + AST walk of `_dispatch`) and asserts set equality. Full 28-handler `_dispatch` refactor declined as beyond D2's Done; rationale posted on-thread.
- FIX B2 (Minor): header state reset on path change in `_detect_user_facing_strings`.
- FIX B3 (Major): multiline module-docstring span collection; behavior probes pass (multiline/single-line/async).
- FIX B4 (Minor): rule-catalog `subprocess-pythonpath` intent now names the exemption set.
- FIX B5 (Minor): same edit as A2.
- ACCEPT C (PR-Agent review job FAILURE): GitHub App token failure (`cuioss/pr-agent-settings` inaccessible) — deterministic infra, out of scope, will fail identically on rerun.
- HANDLED D (Sourcery): rate-limit notice, zero findings.

## Verification on fix HEAD (worktree, pre-commit)
- compile (mypy): green. ruff format --check + ruff check: clean on all touched files.
- Scoped suites green: router 130, rule2 21, harness-guards 37 (incl. armed R5 over 1351 modules), self-review 355, test_detection 3, test_cmd_skill_domains 109.
- Detector behavior probes: cross-file leak → module_docstring (was: misclassified docstring); async-def docstring detected.

## Next
- CI re-runs verify on 5f4f73c; merge only when green with no new actionable comments. Plan stays in 5-execute until merge-time finalize.
