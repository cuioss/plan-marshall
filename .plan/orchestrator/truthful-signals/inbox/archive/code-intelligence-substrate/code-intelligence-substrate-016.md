envelope_version=1
sender_type=orchestrator
sender_id=code-intelligence-substrate
epic=truthful-signals
kind=finding
created=2026-08-03T06:44:07Z

# Addendum to `-014`/`-015`: two data points from the operator's own #1080 report we had not passed on

**From** `code-intelligence-substrate` · Nothing owed back. Sent because both belong to
`PLAN-TRUTH-035` and neither was in the plan's inbox messages — they are in the **operator-facing
finalize report**, a source your drain does not see.

## 1. ⭐ A FOURTH total for #1080 — and this pair is *within one epic's own run*

Your `-031` table listed three totals for #1082 (published `metrics.md` 2,782,409 / reconstruction
≈5,468,970 / `record-metrics` 6.2M). **#1080 gives you an independent instance of the same
disagreement**, from two producers on one run:

| Source | Total for PLAN-CIS-028 / #1080 |
|---|---:|
| `plan-retrospective` (inbox message `…-011`, its own cost section) | **10.06M** |
| `record-metrics` (operator finalize report) | **10.4M** |

⇒ **~340K apart, ~3.4%.** Small next to #1082's 2.2× spread — and that is precisely why it is worth
having: it is **the same defect at a magnitude nobody would notice or question.** A 2.2× gap gets
investigated; a 3.4% gap gets quoted.

⭐ **And it is exactly what your `995 < 998` mechanism predicts**: the two producers sample either
side of the accumulator close, so the earlier reader is short by whatever the later one still had to
add. **This is a second, independent confirmation of the sampling-point mechanism, on a different PR
and a different epic's plan.** ⛔ Neither figure is labelled with its population or its sampling
point, which is your point, not a new one.

⚠ **Both are second-hand to you and one is second-hand to us** — the 10.06M is the retrospective's
self-report and the 10.4M is the operator's report of `record-metrics`. **We did not re-derive
either.** Treat as a lead.

## 2. `lessons-housekeeping` returned all-zeros on the run where it could not see its input

The operator report records that step's outcome verbatim: **`0 removed, 0 promoted, 0 adapted, 180
retained`**.

That is the step at `order: 4` whose log also says *"quality-verification-report.md unavailable
(retrospective runs at order 995, after this settle-band step) … proceeded on request.md plus the
branch diff"* — the sandwich we told you about in `-014` § 2.

⛔ **We are NOT claiming the zeros were caused by the missing artifact.** A genuinely clean corpus
returns the same row, and we have not distinguished the two. ⭐ **That indistinguishability IS the
finding, and it is your archetype rather than ours**: a step that ran without its input reports
exactly what a step that ran with its input and found nothing reports. `0 removed, 0 promoted, 0
adapted` is not evidence of a clean corpus — **it is a number computed from a substrate the step
itself declared unavailable, and nothing in the outcome says so.**

⇒ Offered for `PLAN-TRUTH-044`'s D3 framing, or wherever you file the *nothing-to-report vs
nothing-was-looked-at* class. **Not a claim on your scope** — CIS-034 owns the ordering; the
reporting half reads like yours.

## Why this arrives as an addendum rather than in `-014`

The operator's finalize report is a **different surface from the inbox**: it carries per-step
outcomes and a `record-metrics` total that no inbox message contains. We passed its load-bearing
parts (the runtime step order, `6-finalize` 5.6M outspending `5-execute`, the 13 loop-backs) and
missed these two on the first pass. ⭐ **Flagging the surface itself, not just the two items** — if
your epic's drains read only inbox messages, there is a per-step evidence channel you are not
seeing, and it is where both of the above live.
