envelope_version=1
sender_type=plan
sender_id=a-rule-that-is-green-because-it-examined-nothing
epic=truthful-signals
kind=candidate-lesson
created=2026-08-08T18:40:52Z

component=plan-marshall:plan-retrospective
category=bug
title=Order-995 placement makes the coverage check structurally unmeasurable
confidence=high
source_plan=a-rule-that-is-green-because-it-examined-nothing

# Order-995 placement makes the coverage check structurally unmeasurable

## Context

`check-artifact-consistency` owns the declared-vs-achieved coverage comparison — the deterministic half of the thoroughness dial. On this plan it returned:

```
affected_files_recall,inconclusive,"Plan footprint could not be resolved (no live worktree diff and no modified_files key) — recall is unmeasurable, not 0%"
affected_files_exact_match,inconclusive,"...the comparison substantiates no verdict"
```

The real answer was a perfect score. `references.affected_files` declares 5 paths; `git diff aa606b617^..aa606b617` (the squash-merge of PR #1115) contains exactly those same 5 paths. Recall 100%, precision 100%, zero scope creep, zero shortfall. That result went unmeasured.

The footprint is resolvable only inside the window between worktree materialisation and `branch-cleanup`. Outside it, both ends fail:

- **Before** — `manage-execution-manifest compose` at 13:29:06 logged `pre_push_quality_gate_inactive — kept pre-push-quality-gate on an unknown build verdict: plan footprint unresolvable — worktree not yet materialised`.
- **After** — `plan-marshall:plan-retrospective` is ordered 995 and `default:branch-cleanup` is ordered 70, so the retrospective ALWAYS runs after the worktree has been removed. This is not a scheduling accident on one plan; it is the normal finalize order for every plan.

`project:finalize-step-lessons-housekeeping` hit the same wall at 17:20:48 and logged it explicitly: *"quality-verification-report.md unavailable at settle-band order 4 because plan-retrospective runs at order 995. references field modified_files also absent."*

## Root cause

The footprint resolver knows two sources — the live worktree diff and the retired `references.modified_files` key — and both are unavailable post-`branch-cleanup`. It does not know the third source that IS available and IS already persisted: the landing SHA in `status.metadata.phase_steps["6-finalize"]["branch-cleanup"].head_at_completion` (here `aa606b617`), from which `git diff {sha}^..{sha}` reconstructs the footprint exactly.

`metrics.md` has the mirror-image version of the same ordering problem: the retrospective reads it at order 995, but `default:record-metrics` regenerates it at order 998. The copy the retrospective consumed was generated at 13:56:36Z while `work/metrics.toon` had been updated at 15:44:39Z — so the report under-reported 5-execute by 83,170 tokens and showed 2 closes where the live data has 3.

## Proposed action

- Teach the shared footprint resolver a git-derived third source keyed on the recorded landing/completion SHA, so a post-`branch-cleanup` consumer resolves the footprint instead of reporting inconclusive.
- Either re-run `manage-metrics generate` at the head of the retrospective, or move `record-metrics` ahead of `plan-retrospective`, so the retrospective's efficiency aspect reads a current `metrics.md` rather than a snapshot from before the last phase-5 re-entry.
- Keep the `inconclusive` verdict itself — it is honest and correct. The defect is that it is reachable on every plan, not that it is worded wrongly.

## Evidence

- aspect: artifact_consistency — 2 of 6 checks inconclusive, `footprint_resolved: false`, `declared: 5`
- aspect: request_result_alignment — declared 5, realized 5, exact set equality confirmed from the landing commit
- aspect: plan_efficiency — `metrics.md` generated 13:56:36Z vs `work/metrics.toon` updated 15:44:39Z; 5-execute 344,873/2 closes vs 428,043/3 closes
- source: `decision.log` c11f4a (compose-time), `work.log` 51ffb6 (lessons-housekeeping naming the order-995 problem directly)
