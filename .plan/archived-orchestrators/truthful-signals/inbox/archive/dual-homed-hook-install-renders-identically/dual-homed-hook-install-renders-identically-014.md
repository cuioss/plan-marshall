envelope_version=1
sender_type=plan
sender_id=dual-homed-hook-install-renders-identically
epic=truthful-signals
kind=candidate-lesson
created=2026-09-03T10:19:35Z

# Candidate lesson: no read surface names WHAT a queued inbox message is about, so a candidate-lesson emitter structurally cannot dedup against the queue

**Component**: `plan-marshall:plan-orchestrator` (inbox read surface) / `plan-marshall:phase-6-finalize` lessons-capture Branch B4
**Source signal**: observed first-hand while executing this step's own dedup obligation
**Suggested category**: improvement

## Claim

Branch B4 of `lessons-capture` requires the emitting plan to route only genuinely uncovered material into the epic inbox. Nothing in the read surface makes that checkable. The two read verbs return **envelope metadata only**:

- `inbox list` → `name, sender_id, kind, created, lifecycle, revision, superseded_by, valid, error`
- `inbox validate` → the same header fields plus `location` / `archive_path`

Neither carries a title, subject, or any summary of the message body, and there is no body-read verb at all (`inbox --help`: `write, amend, supersede, close-stream, validate, list, archive, migrate-archive, detect, landing-check` — `landing-check` reads a payload but only for `kind: landing`, and returns fact keys, not content).

## Evidence (first-hand, this step)

The queue held 24 live messages when this step ran, 8 of them written by **this same sender** minutes earlier by `plan-retrospective`. Enumerating them yields 24 rows that differ only in filename and timestamp:

```text
dual-homed-hook-install-renders-identically-001.md,...,candidate-lesson,"2026-09-03T09:46:54Z",live,...
dual-homed-hook-install-renders-identically-002.md,...,candidate-lesson,"2026-09-03T09:47:30Z",live,...
```

There is no way, from any script surface, to learn what 001..008 were **about**. A dispatched leaf is additionally bound by the project's scripts-only rule for `.plan/` access, so it cannot fall back to opening the files.

## How the gap was worked around, and why that is the tell

The dispatching orchestrator had to **hand-enumerate the already-covered material into the prompt body** — seven lesson ids with one-line summaries each, plus a prose list of what remained uncovered. That works, and it is exactly the shape of a missing surface: the information existed, but only in the caller's head, transmitted as narrative. Had the orchestrator's summary been incomplete or stale, the duplicate would have been written with every verb returning `status: success`.

This is one level below the known rule *"a ledger cannot see a duplicate in another ledger"*: here the duplicate is in **the same ledger**, in the same sender's own stream, and it is still invisible.

## Why it matters

- Duplicate candidate-lessons cost the drain a full per-message disposition each, and the drain is the expensive end.
- The dedup obligation is stated as a requirement with no mechanism, so compliance depends entirely on caller diligence — the class of guard the project elsewhere insists must be population-derived rather than asserted.
- It scales the wrong way: the fuller the queue, the more the emitter needs the surface and the more prose the orchestrator must hand-carry.

## Suggested directive (for the orchestrator to judge)

1. **Give `inbox list` a subject column.** Cheapest sufficient fix: have `inbox write` capture the payload's first `#` heading into an envelope `subject` header, and surface it in `inbox list` rows. Titles are what dedup actually needs; full bodies are not.
2. **Consider a `inbox read --message NAME` verb** returning the body, so the drain and any leaf share one sanctioned read path. Today the orchestrator's own drain reads payloads with no documented script surface — the direct read is implied by `analyze.md`'s inbox-scan mode rather than provided.
3. **Then make the obligation checkable at the emitter.** Once subjects are readable, Branch B4 can state a real dedup step instead of relying on the dispatcher's prose. Until then, the prompt-body hand-off should be documented as the required mechanism rather than left implicit — an unstated requirement with no surface is met by luck.

Scope honestly: this was found by one leaf executing one dedup obligation. Before staging, check whether other queue consumers (the `analyze` drain's own Open-Defect dedup at items 3 / 4a / 5b, which the doc says must "fold into that entry") face the same blindness — those sites also require recognising an already-tracked item across messages.
