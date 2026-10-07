envelope_version=1
sender_type=plan
sender_id=provider-logging-path-containment
epic=truthful-signals
kind=candidate-lesson
created=2026-08-08T23:38:43Z

# Candidate lesson L5 — The Phase Dispatch Boundaries section is unreachable and its loss reports as a benign omission

- component: `plan-marshall:plan-retrospective`
- category: bug
- source plan: `provider-logging-path-containment` (PLAN-TRUTH-011, PR #1123)
- theme: confident-signal-hides-a-caveat

## Observation

`retro_sections.SECTION_SPEC` declares the section `('Phase Dispatch Boundaries', 'dispatch_boundaries', 'dispatch_boundaries')` — a **top-level bundle key**. But the producer, `analyze-logs`, emits `dispatch_boundaries` as a **nested block inside the `log-analysis` fragment**, and the SKILL's Step 3 aspect table has no row that registers `dispatch_boundaries` separately.

Following the documented workflow verbatim therefore leaves `fragments.get('dispatch_boundaries')` as `None`. `should_emit` returns `False`, and — this is the sharp part — the non-emit path calls `_fragment_has_payload(None)`, which is `False`, so the section is classified as a **benign omission** rather than a drop. The report emits `sections_dropped[0]` and `status: success`.

The data was fully present the whole time: 20 rows across 3 phases, all with `present: true`. The `sections_dropped` mechanism exists precisely to make lost content loud, and it is defeated by the payload living under a different key than the one the gate probes.

This retrospective recovered the section by extracting the nested block into its own fragment and registering it as `dispatch_boundaries`, which rendered correctly — confirming the consumer works and only the wiring is missing.

## Why the guard misses it

`retro_sections.py`'s own docstring claims the shared registry makes "producer/consumer key drift structurally impossible — a typo'd or renamed aspect key now fails loudly at `collect-fragments add` time". That guarantee only covers keys a producer *does* register. It cannot see a key nobody registers at all, which is this case.

## Proposed remedy

1. Add an explicit registration step for `dispatch_boundaries` to the SKILL's Step 3 aspect table (extract the nested block from the `log-analysis` fragment, or have `analyze-logs` also emit a standalone `fragment-dispatch-boundaries.toon`).
2. Strengthen the completeness probe: for a section whose `conditional_trigger` names a key that **no registered fragment provides**, distinguish "trigger key absent from the bundle entirely" from "trigger fragment present but empty". Only the latter is a benign omission; the former is an unwired section and should be loud.
