envelope_version=1
sender_type=plan
sender_id=spec-corpus-review-and-cleanup-entry-point
epic=truthful-signals
kind=candidate-lesson
created=2026-08-22T16:28:17Z

# Owed architecture hint — orchestrator module treats improvement findings as a standing consideration

An owed `architecture enrich` hint from `default:finalize-step-preference-emitter` (order 992). The
step is `post_run_review: true` and runs after the merge gate, so it MUST NOT call `architecture
enrich` itself — a post-merge enrich write would land tracked source on `main` as an uncommitted diff
(the `#990` defect). The hint is named here so the enrichment is scheduled and visible rather than lost.

## The owed call

| Field | Value |
|---|---|
| `--module` | `plan-marshall:marshall-orchestrator` — ⛔ **see the rename caveat below** |
| enrich verb | `insight` |
| hint text | *the project treats improvement findings as a standing consideration in the orchestrator module* |

Reconstructed call shape:

```
architecture enrich insight --module {resolved-module} \
  --insight "the project treats improvement findings as a standing consideration in the orchestrator module"
```

## Why it cleared the gate

Within-plan recurrence of the `(module, finding-class, disposition)` tuple
`(plan-marshall:marshall-orchestrator, improvement, taken_into_account)` is **2**, against a
`preference_min_recurrence` of **2**. Generalized rather than logged raw, per the
disposition-to-hint-routing privacy invariant: the two underlying records are retained in the plan's
findings store and are not restated here.

`taken_into_account` maps to `insight` per the shared contract's disposition table.

## Populations, so the count is checkable

- 7 dispositioned findings total: 2 `accepted`, 5 `taken_into_account`, 0 `suppressed`.
- Both `accepted` findings are `pr-comment` with `bot_kind: coderabbit` (authorship-admissible) but
  carry an **empty `component`**, so they resolve to the `default` bucket and were **dropped by the
  attribution gate** — an unattributed recurrence is never promoted, even when it clears the threshold.
- The other four `taken_into_account` tuples recur once each and did not clear.

## ⛔ Rename caveat — the module name in this hint is stale by construction

This plan settled its dispositions while the module was still named `marshall-orchestrator`. That
module has since been renamed to **`plan-orchestrator`** (PLAN-TRUTH-015 / PLAN-120, PR #1162, a
verified pure token rename). An `architecture enrich --module plan-marshall:marshall-orchestrator`
call would therefore target a module that no longer exists and the hint would be dead on arrival.

**Resolve the module against the live architecture before enriching**, and record which name was used.
This is the same stale-pointer shape the epic files against: a value that was true when captured and
is false when consumed, with nothing in between to notice.

## Provenance

- Emitted by `default:finalize-step-preference-emitter`, order 992, during the cross-session finalize
  resume of `spec-corpus-review-and-cleanup-entry-point` (PR #1134, merged as `c0bbd2d8b`).
- `orchestrated: true`, `epic: truthful-signals` — resolved once by the dispatcher, not re-derived here.
- Zero `manage-lessons add` calls and zero `architecture enrich` calls were made by this step.
