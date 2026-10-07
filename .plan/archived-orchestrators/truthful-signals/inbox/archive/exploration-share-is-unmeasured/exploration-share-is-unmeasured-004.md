envelope_version=1
sender_type=plan
sender_id=exploration-share-is-unmeasured
epic=truthful-signals
kind=candidate-lesson
created=2026-07-29T04:50:55Z

component=plan-marshall:manage-status
category=bug
title=scope_estimate derived from backticked spec paths under-counts the footprint and mis-routes the plan to the light lane / minimal posture

# Backticked paths in a spec are invisible to path detection, so scope_estimate under-counts

## Observation

Plan `exploration-share-is-unmeasured` was a five-deliverable change touching the transcript engine, `cmd_enrich`, `metrics.toon`, `generate`, a new auditor check, and a new standard with a conformance detector. The router initially routed it to the **`light` lane / `minimal` posture**, off a `scope_estimate` derived from **ONE** detected path — because the spec wrote its paths inside backticks and the path-detection regex did not see them.

The operator escalated to `deep` / `auto`.

This is a direct instance of this epic's theme: a routing decision reported with full confidence, whose confidence was manufactured by a silent detection gap. The router did not say "I found 1 path, which may be an undercount" — it said `light`.

## Rule

- A scope/footprint estimate derived from path detection MUST treat a **low** detected-path count over a **long/multi-deliverable** narrative as a *low-confidence* read, not as a small scope. Under-detection and genuine smallness are indistinguishable from the count alone; the two must not collapse to the same routing verdict.
- Path detection over a markdown spec MUST see paths inside inline code spans. Backticked paths are the *conventional* way to write a path in this repository's specs — they are the common case, not an edge case.
- **A count is not a coverage number.** One detected path is a volume reading; the coverage question ("did I see all the paths?") was never asked.

## Suggested direction

Either (a) strip inline-code fencing before path extraction, or (b) surface a `scope_confidence` alongside `scope_estimate` so a thin detection result routes to `auto`/`deep` rather than `minimal`/`light`.
