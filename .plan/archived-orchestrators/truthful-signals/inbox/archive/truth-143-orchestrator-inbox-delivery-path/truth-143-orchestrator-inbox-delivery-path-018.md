envelope_version=1
sender_type=plan
sender_id=truth-143-orchestrator-inbox-delivery-path
epic=truthful-signals
kind=candidate-lesson
created=2026-09-20T08:28:21Z

# Candidate lesson: a guard claimed to detect within-set duplicates that its mechanism had already discarded

## Signal source

PR #1539 CodeRabbit inline comment `165549` at `test/plan-marshall/plan-orchestrator/test_orchestrator.py:654`.

## Observation

A test asserted that it detected duplicate statuses, both **within** a declaring set and **across** declaring sets. Each declaring set is a `frozenset`, so it has already discarded its own duplicates before the expansion the assertion measures. Repeating a status inside one `frozenset` literal leaves `len(declared)` unchanged and the test passes.

The cross-set overlap half of the claim was real and load-bearing. The within-set half was **vacuous** — not wrong in outcome, but unachievable by the mechanism, so the documentation promised a protection that did not exist.

The bot cited the repo's own path instruction verbatim: *"When a change states that something is skipped, disabled, guarded, validated, enforced or removed, verify that the mechanism exists."*

## Resolution

The claim was narrowed to cross-set overlap only, leaving the check itself intact. Rejecting duplicate source literals would require inspecting the literal sequence **before** `frozenset` construction, and was recorded as out of scope rather than silently dropped.

## Corrective rule

1. **A guard's stated scope must be derivable from its mechanism.** When a data structure normalises its input (a set deduplicates, a dict collapses keys, a `strip()` removes the whitespace a test claims to catch), any claim about the normalised-away property is vacuous by construction.
2. **The fix is usually to narrow the claim, not to widen the mechanism** — but the dropped half must be recorded as out of scope, not deleted silently, or the next reader re-derives the same gap.
3. This is the vacuous-guard archetype the corpus already tracks (n>=6, and repeatedly reintroduced *by a fix* for it). Its distinguishing marker here is that the test **passes**, so only reading the mechanism against the claim finds it — no red build will.
