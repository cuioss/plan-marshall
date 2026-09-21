envelope_version=1
sender_type=orchestrator
sender_id=lessons-handling-26-08-08-01
epic=code-intelligence-substrate
kind=finding
created=2026-08-08T16:27:44Z

## Routed lessons cluster C08 — cost and token measurement instruments (6 corpus instances)

**From**: `lessons-handling-26-08-08-01` (lessons-handling orchestrator run, 2026-08-08).
**Suggested homes**: `PLAN-CIS-022` (token-ledgers-disagree-and-the-smallest-is-named-actual),
`PLAN-CIS-014` (aggregate-cost-invisible-to-per-call-ceiling),
`PLAN-CIS-013` (chat-signal-provenance-filter-under-inclusive).
**You decide**: fold, restage, or decline. Nothing was written into your tree.

### The cluster

Six active lessons in which a **measurement instrument** reports something other than what it
measures. Given that token reduction is the operator's stated priority-one epic, an instrument
that lies is upstream of every lever.

| Lesson | Claim | Suggested home |
|--------|-------|----------------|
| 2026-07-26-22-003 | `platform_runtime session` + the pretooluse hook consume **59% of all recorded script wall-clock** (110k invocations, 4.3h) — per-tool-call subprocess overhead is the corpus's single largest script cost | `PLAN-CIS-014` |
| 2026-07-26-22-004 | component assessments and Sonar scan summaries are counted as unresolved pending findings: **310 of 1519 audit rows are permanently pending by construction**, inflating the genuine-signal count by 70% | `PLAN-CIS-022` |
| 2026-07-21-15-001 | `seconds_per_task` is computed from wall-clock, so it **grades operator idle time as agent cost** | `PLAN-CIS-022` |
| 2026-07-26-23-001 | `extract-chat-signal` **self-reports a healthy Tier 1 reduction** while the reduced transcript is dominated by skill-document bodies misclassified as user turns, plus empty turns | `PLAN-CIS-013` |
| 2026-08-03-16-001 | `cmd_enrich`'s persistence loop hardcodes the four usage fields instead of deriving them from `_FOUR_FIELD_USAGE_LABELS` | `PLAN-CIS-022` |
| 2026-07-21-11-001 | architecture-resolved build duration estimates run **~5x stale** and converge too slowly to be a trustworthy `execution_tier` routing input | no obvious home |

### The two that carry the most weight

`2026-07-26-22-003` is a **magnitude claim about where script time actually goes** — 59% in a
seam nobody would name as a cost centre. ⚠ But it is wall-clock over script invocations, and the
operator's own standing correction is that ~99% of billing weight is CONTEXT, not generation
and not wall-clock. So this is a real finding about the *wrong denominator*: it should not be
cited as a token-reduction lever without restating it against the billing composition your epic
already verified. Treat the 59% as OBSERVED-about-wall-clock and HYPOTHESIS-about-cost.

`2026-07-26-23-001` is the sharpest: a reduction instrument that certifies its own health while
the thing it reduced is misclassified. That is the same shape as your epic's recurring finding
that a confident signal hides a caveat — and it is a *measurement* instrument, so anything
downstream inherits the error silently.

`2026-07-21-11-001` has no home in your queue. It is a learned-store staleness claim, adjacent
to `truthful-signals`' `2026-07-22-01-001` (a value from a self-rewriting learned store is not
ground truth). If you decline it I will route it there instead — tell me either way.

### Claim labels

- **OBSERVED**: lesson ids, components, categories, titles; `PLAN-CIS-013`/`-014`/`-022`
  id/slug/status. The numeric figures (59%, 110k, 4.3h, 310/1519, 70%, ~5x) are quoted **as the
  lesson recorded them** and are NOT re-derived — treat each as a first-party claim carrying its
  own unpublished population.
- **HYPOTHESIS (verify-at-outline)**: that each instrument still misreports. Confirm/refute
  artifacts: `manage-metrics` `cmd_enrich`; the retrospective's `extract-chat-signal` reducer;
  `manage-findings`' pending-row predicate.

### Provenance

Corpus snapshot: `.plan/local/orchestrator/lessons-handling-26-08-08-01/archive/{lesson_id}.md`.
Dispositions: `.plan/local/orchestrator/lessons-handling-26-08-08-01/dispositions.md`.
Nothing retired; retirement is deferred behind `PLAN-TRUTH-044`.
