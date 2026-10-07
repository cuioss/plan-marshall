envelope_version=1
sender_type=plan
sender_id=marketplace-dependency-resolver
epic=code-intelligence-substrate
kind=candidate-lesson
created=2026-08-01T23:18:31Z

component=project:finalize-step-review-retrospective
category=bug
title=Declare head_dependent on review-retrospective so its verdict cannot outlive its HEAD

# Declare head_dependent on review-retrospective so its verdict cannot outlive its HEAD

## Context

`review-retrospective.md` is on disk in the merged plan directory asserting three
things about PR #1074:

- "CodeRabbit (`coderabbitai`) — absent. No assessment possible. The bot refused
  with an awaitable rate limit and produced no record."
- "Inline coverage on PR #1074 was zero: `by_author_kind` contains no `inline` row."
- "This is a thin-review landing, not a clean-review landing."

All three are false. CodeRabbit completed a review of the rebased head `1decffb9`
at 19:52:34Z and posted **6 actionable comments across 16 files with
`evidence_kind=inline`**. Four were genuine defects — including a `TypeError`
crash path in `build.py`'s `_mypy_exclude_patterns` that contradicted its own
documented fail-open contract. They became TASK-011 and TASK-012 and landed in
the merge commit.

The artifact's closing recommendation is now actively misleading: it tells a
future reader to "treat PR #1074 as having received no meaningful automated
review coverage" and "do not treat 'the bots passed it' as counter-evidence —
the bots did not read it." CodeRabbit did read it, and found four real defects.

## Root cause

The step ran once at 19:06:24Z (`order: 50`) and was never re-fired. Its verdict
is computed from the `pr-comment` findings store — i.e. from the **remote state
of the source** — which changed materially when the branch was rebased and the
bot re-reviewed.

PR #1073 landed one commit before this plan's merge and made exactly this
declaration mandatory. Its discriminator is stated verbatim in
`ext-point-finalize-step.md`:

> **"would this verdict change if HEAD changed?"** Declaring this field is
> **mandatory** for a step matching either of two shapes — (1) it records a
> pass/fail verdict over tracked source **or over the remote state of that
> source** …

`finalize-step-review-retrospective` matches shape (1) exactly. Its frontmatter
carries `lane`, `order: 50`, `default_on`, `presets`, `implements` — and no
`head_dependent` field. #1073 updated the built-in steps plus two project steps
(`era-stamp-fill`, `plugin-doctor`); this project-local step was not swept.

The loop-back re-fire gate at 20:36:27Z enumerates its decisions explicitly —
`pre-push-quality-gate` re-fired, `pre-submission-self-review` and
`finalize-step-simplify` declined with reasons, `push`/`ci-verify`/
`automatic-review` re-fired. `review-retrospective` appears in neither list. It
was not declined; it was never considered.

## Proposed action

1. Add `head_dependent: true` to the frontmatter of
   `.claude/skills/finalize-step-review-retrospective/SKILL.md`.
2. Have the step persist `--head-at-completion {sha}` on its terminal
   `mark-step-done` call, as the contract requires of head-dependent steps.
3. Sweep the remaining **project-local** finalize steps against #1073's
   discriminator — #1073 swept the built-ins and two project steps, so the
   project tier is where the next instance of this gap will be.
4. Consider a structural guard: a step that reads the `pr-comment` findings store
   is head-dependent by construction, and that is mechanically checkable.

## Evidence

- aspect: request_result_alignment — the landed footprint contains `build.py` and
  `test/default/test_build_verify.py`, neither declared by any deliverable, both
  produced by the CodeRabbit-driven TASK-011.
- aspect: log_analysis — `review-retrospective` recorded at 19:09:00Z; the
  barrier-vindication decision entry is timestamped 19:52:34Z; the loop-back
  transition is at 20:06:35Z.
- decision.log `d97f6f` — "Barrier VINDICATED … 6 actionable comments across 16
  files, with participated_bots showing evidence_kind=inline."
- decision.log `5f9671` — the re-fire gate decision list, which does not mention
  this step.
- `ext-point-finalize-step.md` (landed in #1073) — the mandatory-declaration rule
  and the "remote state of that source" clause.
