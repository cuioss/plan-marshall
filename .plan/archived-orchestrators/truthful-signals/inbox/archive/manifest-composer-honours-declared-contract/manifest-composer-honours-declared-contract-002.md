envelope_version=1
sender_type=plan
sender_id=manifest-composer-honours-declared-contract
epic=truthful-signals
kind=candidate-lesson
created=2026-07-27T19:23:51Z

component=plan-marshall:automatic-review
category=bug
bundle=plan-marshall
suggested_disposition=merge_into 2026-07-27-07-001 (or file as its successor recurrence)

# A fully-filtered set of bot refusals produces the same finalize signal as a clean review

## Context

Observed first-hand during phase-6-finalize of PLAN-75
(`manifest-composer-honours-declared-contract`, PR #1025, epic `truthful-signals`).
All three enabled review bots failed to review the diff, each for a different reason:

- **CodeRabbit** — rate-limited.
- **Sourcery** — refused the diff as exceeding its 150000 diff-character ceiling
  (the PR is 19 files, +1407/-182).
- **PR-Agent** — silent; published nothing.

`fetch_findings` did exactly what it was fixed to do: both refusal notices were
recognised and filtered as noise, so neither reached the findings ledger. The
consequence is the defect:

```text
automatic-review:
  outcome: done
  display_detail: 0 comment(s) found (unified triage pending)
```

`0 comment(s) found` + `outcome: done` is **byte-identical** to the signal produced by
"three bots reviewed the diff and found nothing worth commenting on". The finalize
pipeline then proceeded to the merge gate carrying a green, confident, and
substantively empty review signal.

An independent surface in the SAME run did hold the truth:
`project:finalize-step-review-retrospective` recorded
`Review surface absent: rate-limit, diff-size, silent (3 modes)`. The information
existed; it simply was not the signal the gate consumed.

## Why this is not already covered

Lesson `2026-07-27-07-001` catalogues two adjacent false-participation mechanisms:
(a) a green CI check with zero published comments, and (b) a refusal notice **stored
as a finding**, over-counting participation. This run is the **inverse of (b)**, and it
was introduced by the fix for (b): now that registered-bot refusals are correctly
pre-filtered via `ignore_patterns` / `_is_rate_limit_notice`, a run in which *every*
bot refuses yields an empty filtered set — and an empty filtered set is the encoding
already reserved for "reviewed, nothing found". The prior lesson's corrective read
("cross-reference the actual published comment count") does not catch this case,
because the published comment count here is genuinely zero.

This is also a second sighting of the archetype where a fix for a defect class
introduces an adjacent instance of the same class.

## The rule

Filtering a refusal out of the findings ledger is correct, but it must not be
**silent**. A review step must distinguish three outcomes it currently collapses into
one:

1. `reviewed, 0 findings` — bots participated, published nothing actionable.
2. `refused / degraded` — one or more bots produced a recognised non-review notice.
3. `absent` — one or more bots produced nothing at all.

Concretely:

- Count filtered refusals as a **first-class per-bot outcome** and carry that count on
  the step's return contract, not only as discarded noise. A run with
  `comments_found == 0 AND refusals_filtered > 0` is a *degraded* review, not a clean
  one, and its `display_detail` must say so.
- Never derive "review coverage" from `comments_found == 0` alone.
- Bot **check state carried no information in either direction** on this PR —
  participation was establishable only from retrieved comment bodies. Do not
  reintroduce check conclusion as a participation oracle.
- When every enabled bot degrades in the same run, that is the compounding case: the
  PR ships with zero substantive automated review while every surface reads green. It
  warrants an explicit escalation, not a silently-green step.

## Related

- `2026-07-27-07-001` — the two prior degrade shapes (CI-green-but-silent,
  refusal-stored-as-finding). This is the post-fix inverse.
- `2026-06-23-19-001` — large mechanical-sweep PRs auto-skip CodeRabbit entirely.
- Epic queue: PLAN-80 (refusal detectors stale, neither detector a superset),
  PLAN-72 (PR-Agent erratic per-PR participation) — this run adds another
  PR-Agent-silent sighting.
