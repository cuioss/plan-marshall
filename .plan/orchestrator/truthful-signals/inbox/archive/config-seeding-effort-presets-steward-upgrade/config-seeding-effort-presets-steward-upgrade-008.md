envelope_version=1
sender_type=plan
sender_id=config-seeding-effort-presets-steward-upgrade
epic=truthful-signals
kind=candidate-lesson
created=2026-08-26T14:42:36Z

component=plan-marshall:plan-retrospective
category=bug
source_plan=config-seeding-effort-presets-steward-upgrade
confidence=high

# The retrospective graded this run against a plugin-cache reference contract 314 versions stale

## Context

The `plan-retrospective` finalize step is served from the plugin cache. This envelope loaded its SKILL body and every aspect reference from `.../plan-marshall/0.1.1240/skills/plan-retrospective/`, while the run's own `project:finalize-step-sync-plugin-cache` had, minutes earlier, deployed **0.1.1554**. The scripts the same envelope invoked resolved against the newer set. So the retrospective ran with a **split version**: current scripts, 314-version-old contract.

That is not an abstract risk. It produced three concrete consequences inside this one dispatch:

**1. It nearly filed a false defect.** The cached `manage-metrics` SKILL declares the `--termination-cause` enum as `voluntary_checkpoint | task_complete_returned_verbatim | budget_yield | harness_cancellation | error | clean_exit_queue_empty`. Four of the five recorded 6-finalize dispatch-boundary rows carry `step_complete`, which is absent from that list — a textbook out-of-enum-value-persisted finding, an archetype this repository has filed before. Checking the live source first showed `step_complete` appearing three times in the current `manage-metrics/SKILL.md`: it is a valid, documented cause. The cached contract was simply older than the value.

**2. It graded against a superseded calibration table.** The cached `plan-efficiency.md` carries a 12-row anchor table keyed on `surgical / single_module / cross_cutting / complex`. This plan's `scope_estimate` is **`multi_module`**, which appears in that table nowhere, so the primary calibration path would have been unreachable and scoring would have fallen through to ratio thresholds. The live source carries a 35-row exact cross-product with `multi_module + bug_fix` **anchored** at ≥1.2M/90min warning and ≥2.0M/150min error — and the run crossed the error column 4.4× on tokens and 2.9× on time. The cached doc would have downgraded a hard error to a set of ratio warnings. It also specifies a different ratio set (`worked_seconds_per_task`, not `seconds_per_task`) and a `denominator_provenance` block and a `build_time` contract that the cached version does not mention at all.

**3. It executed a retired notation.** Step 5b in the cached body instructs `plan-marshall:marshall-orchestrator:orchestrator inbox write`. That skill has been renamed; the executor rejected it three times with `Unknown notation`. The live body correctly says `plan-marshall:plan-orchestrator:orchestrator inbox write`. This message is being delivered only because the envelope went and read the current source.

## Root cause

The known registry-pin gap: `/sync-plugin-cache` mints a new cache version and does not re-point the registry, so each landing widens the gap by one version. The new consequence documented here is the *ordering*: the sync step runs inside finalize, immediately before the retrospective step, so the retrospective is systematically the step most exposed to the pin it just widened — and it is the step whose entire job is grading, against contracts, with evidence.

## Proposed action

1. Where a retrospective aspect's contract is normative for a verdict (the calibration table, the enum sets, the script notations), read it from **repository source**, not from the served copy, and record which it used. This retrospective added a `reference_version_caveat` field to its plan-efficiency fragment for exactly this reason; make that structural rather than ad hoc.
2. Have the retrospective assert `executor_version == installPath` at entry and surface the delta in the report when they disagree — a report is the right place for its own instrument's provenance.
3. Consider ordering `finalize-step-sync-plugin-cache` after the post-run-review steps, or re-pinning the registry as part of it, so the step that grades is not served by the copy the step before it superseded.

## Evidence

- Served base directory of this envelope's skill loads: `/Users/oliver/.claude/plugins/cache/plan-marshall/plan-marshall/0.1.1240/skills/...`.
- `status.metadata.phase_steps["6-finalize"]["project:finalize-step-sync-plugin-cache"].display_detail`: "10 bundles synced 0.1.1554; executor regenerated 159 scripts".
- Cached `manage-metrics/SKILL.md` enum vs `architecture search --content --pattern step_complete` → 3 occurrences in the live `manage-metrics/SKILL.md`.
- Cached `plan-efficiency.md` 12-row table vs live 35-row cross-product (live lines 143-189), including the `multi_module + bug_fix` anchored row.
- Three `Unknown notation: plan-marshall:marshall-orchestrator:orchestrator` executor rejections, resolved by `architecture search --content --pattern "plan-orchestrator:orchestrator inbox write"`.
