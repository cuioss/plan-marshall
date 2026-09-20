envelope_version=1
sender_type=plan
sender_id=manifest-composer-honours-declared-contract
epic=truthful-signals
kind=landing
created=2026-07-27T19:23:07Z

## What landed

**PLAN-75 — Manifest composer honours the declared step contract** — PR #1025
(`fix(manage-execution-manifest): honour declared step contract on compose`),
branch `feature/manifest-composer-honours-declared-contract`, `change_type: bug_fix`,
`compatibility: breaking`, `simplicity: lean`.

Two independently-observed composer defects closed in one change:

- **Defect A (silent omission)** — a step that was configured, enabled, and rendered in
  the auto-posture preview (`plan-marshall:plan-retrospective`, `lane: minimal`) was
  dropped from the composed manifest with no signal. The preview and the composed
  manifest were two renderings of one decision that were permitted to disagree. The
  composer now either honours a declared, resolvable step contract or refuses loudly.
- **Defect B (ordering inversion)** — `finalize-step-preference-emitter` (`order: 61`,
  `mutates_source: true`) sequenced after `branch-cleanup` (`order: 70`) in a real
  composed `execution.toon`, placing a source-mutating step after the merge gate and
  making PLAN-44's (#990) `order: 80 -> 61` fix inert at runtime.

Footprint: 19 files, +1407/-182. Production surface is
`manage-execution-manifest` (`_manifest_rules.py`, `_manifest_validation.py`,
`manage-execution-manifest.py`, `decision-rules.md`, `manifest-schema.md`, SKILL.md)
plus a `manage-config` defaults/data-model correction. Five test modules touched,
including a new `test_declared_step_contract_regression.py` (386 lines) and a new
`test_validate_loadable.py` (185 lines).

## Evidence discipline notes for the epic ledger

- The Defect-B mechanism was confirmed **empirically** before the fix was designed, per
  the plan's own D0/D1 gate. Two earlier hypotheses (`default:`-prefix unsortable;
  stale plugin-cache pin) were retracted with orchestrator-verified evidence, and the
  spec's remaining `path-resolution` hypothesis was carried as *open and unconfirmed*
  rather than as a premise. The epic's stale-cache-as-evidence archetype was applied
  here to invalidate an artifact, not to acquit the defect.
- D5's regression fixtures were confirmed to FAIL against the pre-fix composer before
  the fix landed, so the new tests are not vacuous.

## Residue the epic should track

1. **The plan shipped with ZERO substantive automated review.** All three enabled bots
   failed on PR #1025 — CodeRabbit rate-limited, Sourcery refused the diff as exceeding
   its 150000-character ceiling, PR-Agent silent. The `automatic-review` step recorded
   `0 comment(s) found` and `outcome: done`; `finalize-step-review-retrospective`
   independently recorded `Review surface absent: rate-limit, diff-size, silent
   (3 modes)`. The refusal detectors worked correctly and filtered both notices as
   noise — which is precisely how the finalize signal became indistinguishable from a
   clean review. Filed separately as a candidate lesson; this is the epic's own theme
   (confident signal hides a caveat) landing on the epic's own PR. Adjacent to
   PLAN-80 (stale refusal detectors) and PLAN-72 (PR-Agent erratic participation),
   and it raises PR-Agent's silent-run count again.
2. **Corroboration, not a new lesson**: this run's change ledger again carried a
   `status: timeout` entry with `exit_code: 0`. Already covered by lesson
   `2026-07-27-00-002` ("kind=build rows record exit_code 0 for timed-out builds")
   and by the standing freshness-reconciliation rule to filter on `status: success`
   rather than exit code. Recorded here as an additional live sighting only — no
   duplicate lesson was filed.
3. Two candidate lessons filed alongside this landing: a plugin-doctor rule-precision
   defect (which cost the extra commit `9caa8c54e` on this branch), and a build-wrapper
   `--timeout` default that is a scope-broadening recurrence of an existing lesson.
