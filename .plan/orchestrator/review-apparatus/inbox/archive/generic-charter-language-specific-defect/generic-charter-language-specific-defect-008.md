envelope_version=1
sender_type=plan
sender_id=generic-charter-language-specific-defect
epic=review-apparatus
kind=candidate-lesson
created=2026-08-09T17:06:31Z

# The instrument that measures review quality reports "nothing to compare" on exactly the run where nothing was reviewed

component: plan-marshall:automatic-review
category: bug
confidence: high
source_signal: signal_automated_review_count

## Context

PR #1130 is a 27-file diff. Every configured reviewer failed to produce content, each for a different reason:

- **pr-agent** (the only REQUIRED bot) — participated, **0 actionable comments**: `participated_but_empty`.
- **coderabbit** — `refused_awaitable`: a recoverable rate window, with `review_rate_window_await` **off for this plan**, so the recoverable refusal was discarded rather than waited out.
- **sourcery** — `refused_hard`: quota.

The barrier's quorum passed on the required bot's empty participation. `unproven_bots=[coderabbit, sourcery]`. The operator was then shown the gap explicitly — including that zero comments means no reviewer produced content rather than that the diff is clean, and including the option to await coderabbit's recoverable window — and granted `barrier-ask-override` at HEAD `c30d5a656`, gap class `participated_but_empty`, on in-house evidence. The merge is not the defect; the operator was correctly informed and made a judgement call.

**The defect is what every downstream instrument said about it.**

1. The `automatic-review` step recorded `outcome: done`, `display_detail: "0 comment(s) found (unified triage pending)"`. That sentence is what a later reader, a PR body, or a status render actually sees. It is **textually identical** to what a clean 27-file review produces.
2. `project:finalize-step-review-retrospective` — the step whose entire purpose is to compare automated and human reviewers and judge review quality — recorded `outcome: done`, `display_detail: "0 pr-comment findings - nothing to compare"`. The reviewer-quality instrument reported a benign no-op **on precisely the run where reviewer coverage collapsed to zero**. It is blind in exactly the condition it exists to detect.
3. The only artefact that states the truth is a `WARNING` in the work log at 13:56:11Z: *"Zero actionable comments here means NO REVIEWER PRODUCED CONTENT, not that the diff is clean. This 27-file diff must not be rendered as a reviewed diff in any PR-body or log claim."* That sentence reaches no step field, no PR body, and no status render. It was written by the run's own judgement, not produced by any gate.

## Root cause

Both instruments key on the **finding count**, and a finding count cannot distinguish *no defects found* from *no reviewer looked*. `participation_complete` is a liveness predicate; it is being consumed as a coverage predicate. The two coincide on every normal run, which is why the gap only becomes visible when a bot refuses — and when it does, the counts move to zero in the same direction a clean review moves them.

`review-retrospective` inherits the same blindness one level up: its population is `pr-comment` findings, so an empty population reads as *nothing to compare* rather than as *the comparison was impossible because coverage was zero*. It is a set-guarding check reporting a zero whose population size it never publishes.

## Proposed action

1. **`automatic-review`'s `display_detail` must carry the reviewer-state distribution, not just the comment count.** `"0 comment(s) found"` and `"0 comment(s) found — 1 empty, 2 refused, 0 proven"` are different facts and must not share a rendering. The taxonomy already exists (`STATE_REFUSED_AWAITABLE` / `STATE_REFUSED_HARD`, split by registry `rate_limit_class`); it simply does not reach the field a reader sees.
2. **`review-retrospective` must publish its population state.** When zero `pr-comment` findings exist, it must distinguish *reviewers ran and found nothing* from *no reviewer produced content*, and grade the latter `indeterminate` — never `done` with a benign summary. It must not mark itself complete on a comparison it could not perform.
3. **A recoverable refusal that is not awaited should be recorded as a discarded opportunity.** `coderabbit` was `refused_awaitable`; `review_rate_window_await` was off; the one refusal convertible into actual review content was dropped silently by configuration. That the option existed appears only in the override's `granted_over` prose.

## Relation to the epic

This is **fresh first-party evidence, not a new plan.** It reinforces three staged rows and sharpens each differently:

- **PLAN-PR-008** (*review barrier deadlocks on a refusing bot*) — the empty-quorum case is now on a **third** PR (#1118, #1122, #1130). Confirms again that `participation_complete` is liveness, never coverage.
- **PLAN-PR-021** (*coverage shortfall disclosed against the roster, not the required set*) — the false-clean polarity, again. Here the required set had exactly one member and it participated emptily, so a required-set-only denominator reports full coverage over zero content.
- **PLAN-PR-011** (*review bots catch what in-house gates cannot*) — the **complement** of that plan's natural experiment. PR-011's evidence is a run where self-review and CodeRabbit found essentially disjoint defect sets. This run is the case PR-011 warns about, realised: with no bot content available, the merge proceeded on in-house evidence alone (CI green, quality-gate, 18,135 tests, plugin-doctor clean, self-review clean after 4 findings fixed) — a proxy that is weakest exactly when it is being leaned on hardest.

## Evidence

- `status.metadata.merge_authorizations.barrier-ask-override` — `gap_class: participated_but_empty`, `granted_over` naming all three reviewer states, `granted_at: 2026-08-09T16:02:34Z`
- `status.metadata.phase_steps.6-finalize.automatic-review` — `outcome: done`, `display_detail: "0 comment(s) found (unified triage pending)"`
- `status.metadata.phase_steps.6-finalize.project:finalize-step-review-retrospective` — `outcome: done`, `display_detail: "0 pr-comment findings - nothing to compare"`
- `manage-findings list --type pr-comment` — `total_count: 7`, `filtered_count: 0`
- `logs/work.log` 2026-08-09T13:56:11Z — the `[VERIFY]` WARNING, the only artefact stating the truth
