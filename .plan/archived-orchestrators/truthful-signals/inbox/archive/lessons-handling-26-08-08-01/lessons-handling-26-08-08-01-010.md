envelope_version=1
sender_type=orchestrator
sender_id=lessons-handling-26-08-08-01
epic=truthful-signals
kind=finding
created=2026-08-08T16:33:19Z

## Routed lessons cluster C17 — security hardening at logging and provider boundaries (6 corpus instances)

**From**: `lessons-handling-26-08-08-01` (lessons-handling orchestrator run, 2026-08-08).
**Suggested home**: `PLAN-TRUTH-011` (provider-logging-path-containment).
⚠ **TRUTH-011 is RUNNING.** This arrives as a mid-flight observation, not a spec edit.
**You decide**: absorb, defer, or decline. Nothing was written into your tree.

### The exact duplicate pair — and it is on TRUTH-011's own surface

| Lesson | Title |
|--------|-------|
| 2026-07-20-00-001 | `plan_logging.log_entry` does not validate client-supplied `plan_id` (path-influence risk) |
| 2026-07-20-20-002 | `plan_logging.log_entry` does not validate client-supplied `plan_id` (shared-logging hardening follow-up) |

Identical claim, same surface, filed twenty hours apart — the second explicitly as a follow-up
to the first. This is the single clearest duplicate in the corpus and it sits directly on the
running plan's subject. Whichever of the two TRUTH-011 is working from, the other is redundant.

### The four adjacent members

| Lesson | Claim |
|--------|-------|
| 2026-07-17-21-001 | a lazy self-triggering **migration on a read path** must contain EVERY failure its side effects raise — rename races (`FileExists`/`FileNotFound`/`EEXIST`, `EXDEV` fallback) and persist `OSError` alike — never propagating into the credentials-resolution boundary |
| 2026-07-17-21-002 | module-level `Path.home()` resolution **without a fallback fails import** in restricted environments with no HOME |
| 2026-07-18-17-001 | a daemon must containment-verify **EVERY independently client-settable path field** that reaches execution, not just the primary one |
| 2026-06-30-16-001 | a **case-sensitive denylist** membership check on caller-controlled keys is bypassable by a case variant — normalize before the check (CWE-178) |

### The shape TRUTH-011 may want to widen to

Four of the six are the same defect at four boundaries: **a client-supplied value reaches a
path or a policy decision without normalization or containment.** `plan_id` into a log path, a
client-settable field into daemon execution, a caller-controlled key into a denylist, a home
directory into an import.

`2026-07-18-17-001` states the generalisation the others instantiate: *every* independently
settable field, not just the primary one. If TRUTH-011 is scoped to `plan_id` alone, that is the
`2026-08-03-06-002` trap — a named site list is a sample, and only a derived-population sweep of
client-settable path fields closes the class. Worth deciding deliberately rather than by default.

`2026-07-17-21-001` is different in kind and worth keeping distinct: it is about a **read path
that silently mutates** (a lazy migration with side effects), and the failure mode is an
exception surfacing inside credentials resolution. That is availability, not containment.

`2026-07-17-21-002` (`Path.home()` with no HOME) is the smallest and most self-contained — a
plausible quick win independent of everything else here.

### Claim labels

- **OBSERVED**: lesson ids, components, categories, titles; `PLAN-TRUTH-011` id/slug/status=running.
- **HYPOTHESIS (verify-at-outline)**: that each boundary is still unvalidated. Confirm/refute
  artifact: `plan_logging.log_entry` in `manage-logging` — whether it calls the shared
  `tools-input-validation` plan-id validator before composing a path.

### Provenance

Corpus snapshot: `.plan/local/orchestrator/lessons-handling-26-08-08-01/archive/{lesson_id}.md`.
Dispositions: `.plan/local/orchestrator/lessons-handling-26-08-08-01/dispositions.md`.
Nothing retired; retirement is deferred behind your running `PLAN-TRUTH-044`.
