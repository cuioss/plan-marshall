envelope_version=1
sender_type=plan
sender_id=token-total-is-a-partition-labelled-a-whole
epic=truthful-signals
kind=candidate-lesson
created=2026-08-03T12:55:25Z

component=plan-marshall:plan-retrospective
category=bug
bundle=plan-marshall

# The retrospective overwrites the plan's session binding before the step that consumes it runs — on a cross-session resume this silently mis-attributes the whole plan's metrics

## What was observed — live, in this run

`plan-retrospective` Step 1 unconditionally calls:

```bash
python3 .plan/execute-script.py plan-marshall:platform-runtime:platform_runtime \
  session capture --plan-id {plan_id}
```

`session capture` stores the **currently running** session id into `status.metadata.session_id`. Observed in this plan:

| when | `status.metadata.session_id` |
|------|------------------------------|
| before Step 1 | `39786697-0046-49fe-bee0-34bf2ea450a8` (the session that ran phases 1-5 and most of finalize) |
| after Step 1 | `43c13d58-b277-4de6-81cc-440309b571ca` (this retrospective dispatch's own session) |

The overwrite is logged: `[MANAGE-STATUS] Metadata: session_id=43c13d58-...` at `12:41:55Z`.

## Why it is harmful rather than merely untidy

`manage-metrics enrich --session-id {id}` is the only producer of `subagent_samples`, the four-field usage view, and `billing_weighted_total`. It is invoked by `record-metrics`, which sits at **manifest position 20** — three positions **after** `plan-retrospective` at 17.

So the ordering is: the retrospective rebinds the plan to its own session, and then the step that enriches the plan's metrics resolves the session from that rebound value. On this plan, `record-metrics` has not yet run at the time of writing and is armed to enrich against session `43c13d58`, which contains none of the plan's phases 1-5 and only the retrospective's own turns.

The failure is **conditional on cross-session resume**, which is why it has not been universally visible: when the retrospective runs in the same session that ran the plan, `session capture` rewrites the field with the value it already held and nothing is lost. The archived plan cited in this plan's own request (`2026-08-02-barrier-override-not-head-bound`) has a fully-populated `billing_weighted_total` of 66,476,321 — a single-session run. This plan re-entered `5-execute` three times across an overnight gap and finalized in a second session, and every `enrich`-produced field is absent from every one of its phase rows.

That is the shape of the bug: it is invisible on the happy path and total on the resumed path, and the resumed path is the one that produces the largest, most expensive plans — exactly the ones whose cost data matters most.

## The generalisable rule

**A measurement step must not mutate the binding that a later step uses to resolve what to measure.** The retrospective is an observer; `session capture` is a write, and it writes the observer's own identity over the subject's.

Three checks worth making standing practice:

1. **Observers write nothing that a producer reads.** If `plan-retrospective` needs a session id for its own chat-history aspect, it should use the **forwarded** `--session-id` parameter — which the dispatcher already supplies and which correctly carried the plan's working session here — and never call `session capture`.
2. **A binding captured once at plan start should be write-once.** `status.metadata.session_id` identifies *the session that executed the plan*. If a resumed session needs recording, it belongs in an append-only list (`sessions[]`), not as a replacement of the original.
3. **When a field is written by one step and read by a later one, the ordering dependency should be explicit.** Nothing in the manifest expresses that step 20 depends on a field step 17 can clobber.

## Impact

Every cross-session-resumed plan loses its entire cost/enrichment dataset, silently, with no error and no log line saying `enrich` found nothing. Combined with the sibling finding that the retrospective also *reads* metrics three steps before `record-metrics` writes them, the two defects compound: the retrospective corrupts the input to the enrichment it has already failed to wait for.

**Immediately actionable for this plan:** `record-metrics` has not yet run. Restoring `status.metadata.session_id` to `39786697-0046-49fe-bee0-34bf2ea450a8` before it does would let this plan's enrichment attribute correctly, and would give the epic a first plan with a populated `billing_weighted_total` to calibrate against.
