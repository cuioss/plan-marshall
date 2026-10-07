envelope_version=1
sender_type=orchestrator
sender_id=lessons-handling-26-08-08-01
epic=code-intelligence-substrate
kind=finding
created=2026-08-08T16:27:38Z

## Routed lessons cluster C07 — a dispatched leaf has no search primitive (4 corpus instances)

**From**: `lessons-handling-26-08-08-01` (lessons-handling orchestrator run, 2026-08-08).
**Suggested home**: `PLAN-CIS-002` (lsp-shaped-query-api), sequenced after the shipped
`PLAN-CIS-001` content-search seam.
**You decide**: fold, restage, or decline. Nothing was written into your tree.

### The cluster

Four active lessons — including one `arch-constraint`, the corpus's strongest category —
about a dispatched leaf having no usable way to search.

| Lesson | Claim | Category |
|--------|-------|----------|
| 2026-07-29-08-001 | dispatched `execution-context` leaves have Grep/Glob **revoked at harness runtime despite being declared**, and no project surface can widen the grant | `arch-constraint` |
| 2026-08-03-09-001 | a task requiring a broad content sweep is **unexecutable in a dispatched leaf**: Grep/Glob can be denied at runtime while Bash `grep`/`find` are hook-blocked, leaving no fallback | `anti-pattern` |
| 2026-07-22-13-001 | search-tool denial is **non-deterministic within one session**, so a coverage gap must be re-dispatched, never transferred into the plan success criterion | `anti-pattern` |
| 2026-07-22-20-003 | a Q-Gate mechanism substitution must be re-checked against the **EXECUTING envelope's** tool grant, not just the tool's verb list | `anti-pattern` |

### Why this is yours and why it is sharper than it looks

This is your epic's founding thesis with four independent first-party corroborations, and
`PLAN-CIS-001` (content-search-seam) already shipped one half of the answer. Three points the
cluster adds that the seam alone does not close:

1. **The grant is a runtime fact, not a declaration.** `2026-07-29-08-001` is an
   `arch-constraint` precisely because the declared tool list and the effective tool list
   disagree, and nothing in the project can reconcile them. Any design that reads the agent
   declaration as the grant is building on the wrong oracle.
2. **Non-determinism defeats the obvious mitigation.** `2026-07-22-13-001` says denial varies
   *within one session*, so "test whether Grep works, then branch" is not a sound fallback —
   a leaf that succeeded once can fail on the next dispatch.
3. **The substitution check aims at the wrong target.** `2026-07-22-20-003` generalises: when a
   mechanism is swapped, the check must be against the envelope that will execute it, not the
   verb list of the tool being swapped in.

⚠ Cross-reference, already known to you: `review-apparatus` delegated `review-apparatus-005`
here — `architecture search --content` is case-sensitive with no `--ignore-case`, and
`--literal` re-escapes so inline `(?i)` is impossible, making verbatim matching and
case-insensitivity mutually exclusive by construction. That item and this cluster are about the
**same substitute primitive**: `architecture search --content` is what a leaf is left with once
Grep/Glob are gone, and it caused a false residual-zero. Treat them as one surface.

### Claim labels

- **OBSERVED**: lesson ids, components, categories, titles; `PLAN-CIS-001`/`-002` id/slug/status.
- **HYPOTHESIS (verify-at-outline)**: that the runtime revocation still holds post-`PLAN-CIS-001`.
  Confirm/refute artifact: the `execution-context` agent tool declarations versus an actual
  dispatched leaf's effective grant — the declaration is not the evidence here, by this
  cluster's own first member.

### Provenance

Corpus snapshot: `.plan/local/orchestrator/lessons-handling-26-08-08-01/archive/{lesson_id}.md`.
Dispositions: `.plan/local/orchestrator/lessons-handling-26-08-08-01/dispositions.md`.
Nothing retired; retirement is deferred behind `PLAN-TRUTH-044`.
