envelope_version=1
sender_type=plan
sender_id=token-total-is-a-partition-labelled-a-whole
epic=truthful-signals
kind=candidate-lesson
created=2026-08-03T12:35:47Z

component=plan-marshall:marshall-steward
category=bug
bundle=plan-marshall

# The skill loader served two different plugin versions inside one finalize run — observed first-hand from inside a dispatched envelope

## What was observed

During PLAN-TRUTH-035's finalize, the plugin registry-pin inversion fired again. The evidence is first-hand rather than reconstructed: **this observation was made from inside the `lessons-capture` dispatch envelope itself.**

- The orchestrator directed this dispatch to read its workflow doc from `…/cache/plan-marshall/plan-marshall/**0.1.1289**/skills/phase-6-finalize/workflow/lessons-capture.md`, because it had already detected the loader was serving stale bodies.
- Inside the envelope, `Skill: plan-marshall:persona-plan-marshall-agent` resolved and announced `Base directory: …/cache/plan-marshall/plan-marshall/**0.1.1240**/skills/persona-plan-marshall-agent`.

Two versions, one session, one dispatch. The `Skill:` notation loader and the filesystem disagreed by **49 versions**, and the loader gave no indication that it was serving anything other than the current pin.

This matches the recorded incident shape: the executor path resolves cleanly while the **skill loader** is stale, so counting executor path-versions does not detect it. It also matches the standing observation that the version gap contains the launching plan's own target surface — PLAN-TRUTH-035 modified `phase-6-finalize/standards/record-metrics.md`, and `phase-6-finalize` is exactly the skill tree the finalize was executing out of.

## Why this one is worth recording separately

The mitigation currently in play is *check the pin before every plan launch*. This incident fired **mid-finalize**, hours after any such preflight would have passed. A pre-launch check cannot cover it, because the failure is not in the pin — it is in what the session's loaded registry serves when asked.

The orchestrator caught it here only because it happened to notice a sibling dispatch loading `0.1.1240`, and then hand-routed every subsequent dispatch to absolute `0.1.1289` paths. That is a detection by coincidence, not by mechanism. Nothing in the dispatch path asserts that a loaded skill body came from the pinned version.

## The generalisable rule

**A skill that announces its base directory is emitting a verifiable fact — assert on it.** The loader already tells you which version it served; nothing currently reads that. The cheapest available guard:

1. On every `Skill:` load inside a dispatch, compare the announced `Base directory` version segment against the pin.
2. On mismatch, fail the dispatch loudly rather than proceeding on a stale body.

This turns a silent wrong-version execution into an explicit error, and it needs no change to the plugin cache machinery — only a read of a string the loader already prints.

Corollary for the operator-facing guidance: **a clean pre-launch pin check is necessary but not sufficient.** The pin can be correct at launch and the session's registry stale throughout. For this variant a session restart does resolve it (the pin is fine; the session's loaded registry is not) — which is the opposite of the older, pin-corruption variant where a restart never helps. The two variants share a symptom and need different responses, so any runbook must first establish **which** one is live: read the pin, then read what the loader actually served.

## Impact

Every dispatched envelope in every plan. When the stale body is a workflow doc, the dispatch executes a superseded contract while reporting success against the current one — the run is green and the work is wrong. This is at least the sixth recorded incident, and the second in which two distinct versions were served inside a single session.
