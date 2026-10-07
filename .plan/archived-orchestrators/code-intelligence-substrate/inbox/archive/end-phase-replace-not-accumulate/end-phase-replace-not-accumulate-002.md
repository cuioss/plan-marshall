envelope_version=1
sender_type=plan
sender_id=end-phase-replace-not-accumulate
epic=code-intelligence-substrate
kind=landing
created=2026-07-29T16:36:01Z

## What landed

PR #1059 — `fix(manage-metrics): accumulate phase attribution on loop-back`. Fixed the class of defect where a phase boundary's end-timestamp write REPLACED the prior stamp instead of accumulating onto it, corrupting the per-phase token-attribution measurement corpus whenever a phase looped back and re-entered (e.g. a 3-outline re-entry via the operator-directed feedback cycle).

Finalize signals: pre-push quality-gate green (1 bundle + whole-tree, test-compile + module-tests), plugin-doctor clean, self-review clean (75 candidates examined, no check matched), CI green, 1 reviewer compared with 0 actionable comments (CodeRabbit was rate-limited on this pass — proceeded unreviewed per policy).

## Residue for the epic

Two tooling defects were found and filed as findings during this plan's own finalize, then triaged `accepted` (out of scope for this plan's diff) rather than fixed in-run. Both are genuine open defects, filed to the epic as separate `candidate-lesson` messages in this same drain:

- `detect-artifacts` (workflow-integration-git) returning safe-to-delete entries that include live, gitignored in-flight state (plan work.log, `.mypy_cache/`), contradicting its own documented exclusion contract.
- `architecture-refresh` dual-classified (SKILL.md's inline list AND its own standard both claim the inline/dispatch split), where SKILL.md names `dispatch-inline-split.md` as the single source of truth but the inline classification duplicates it instead of deferring.

Also notable: this plan's own execution reproduced the exact defect shape it was created to fix — see the third `candidate-lesson` message for the self-referential recurrence during the 3-outline re-entry.

No pending Q-Gate findings remain open at finalize time (the 3-outline phase's four q-gate findings were all resolved in-run as `taken_into_account`); this landing message is emitted unconditionally per the orchestrated-finalize contract regardless of that fact.
