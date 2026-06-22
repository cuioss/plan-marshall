# Cross-Cutting Principles

These rules apply to all workstreams in this directory. They are constraints, not
suggestions, and they encode the unifying thesis: extend the existing machinery,
do not add parallel subsystems.

---

## 1. Reuse over reinvention

Every workstream names the existing plan-marshall surface it builds on and changes
that surface rather than introducing a parallel one. The router extends
`planning-lane`; audits are recipes; the security gate is a finalize step;
preference learning reuses the `enriched.json` hints store. If a workstream finds
itself proposing a new store, a new dispatcher, or a new finding sink, that is a
signal to stop and map it back onto an existing mechanism.

---

## 2. Findings pipeline is the universal sink

Anything that discovers a problem — a review, a security audit, an acceptance
check — emits into `manage-findings`, not into ad-hoc prose reports. This is what
buys triage, suppression, loop-back, and re-review for free, and it is the
structural difference from external tools that print a report and stop.

A finding carries `type`, `severity`, `title`, `detail`, `file`, `line`, and is
triaged via the domain `ext-triage-*` extension. New discovery surfaces add a
producer; they do not add a new resolution model.

---

## 3. Cheap paths are single-envelope

The token/wall-time win comes from running known-shape work inside one execution
envelope (the recipe model) instead of fragmenting across the refine → outline →
plan loop. Any "make it cheaper" workstream resolves to *routing onto a
single-envelope path*, not to micro-optimizing the heavy path.

---

## 4. Heuristic-first, LLM-as-fallback

Routing and classification default to deterministic heuristics (field reads,
keyword/intent overlap, the existing auto-suggest scoring). An LLM pass is admitted
only as a bounded fallback when the heuristic is ambiguous, and never as an
always-on gate. This preserves the zero-token property the current `planning-lane`
router already has.

---

## 5. Integrate, do not rebuild

Where a mature external tool exists (browser automation, acceptance testing), wrap
it behind a thin plan-marshall surface (recipe or finalize step) rather than
building an in-house equivalent. plan-marshall owns the orchestration and the
findings contract; the external tool owns its domain.

---

## 6. Generalize, do not log raw events

Preference learning stores a *generalized* preference ("module X: prefer Y over Z")
as a best-practice, never a raw event log of individual dispositions. Signal is
threshold-gated so one-off decisions do not pollute the hints store, mirroring the
existing lessons-capture signal thresholds.

---

## 7. Document hygiene

- No version numbers or changelogs in any document
- No "Status", "Created", "Last updated" metadata
- No duplication — cross-reference instead
- Current state only — do not describe transitional information
- Markdown for these planning documents (`.md`); AsciiDoc (`.adoc`) for canonical
  long-form docs under `doc/developer/` and `doc/concepts/`
