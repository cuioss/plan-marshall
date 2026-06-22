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

The `type` comes from the **closed `manage-findings` taxonomy** (the 12-type
`FINDING_TYPES` set: `bug`, `improvement`, `anti-pattern`, `triage`, `tip`,
`insight`, `best-practice`, `build-error`, `test-failure`, `lint-issue`,
`sonar-issue`, `pr-comment`). A new discovery surface **maps onto an existing
type** — quality/review findings → `lint-issue`; security findings →
`bug` / `anti-pattern` (there is no `security-issue` type) — it never adds a new
one.

---

## 3. Cheap paths run inline, not per-phase dispatched

The token/wall-time win comes from running known-shape work inside one execution
envelope (the recipe model) instead of fragmenting across the refine → outline →
plan loop. Any "make it cheaper" workstream resolves to *routing onto a
single-envelope path*, not to micro-optimizing the heavy path.

The dominant cost being removed is **per-phase execution-context dispatch**. On the
heavy path the orchestrator dispatches a separate `Task: execution-context-{level}`
envelope for each phase (phase-2-refine, phase-3-outline, phase-4-plan,
phase-5-execute) plus sibling q-gate-validation dispatches — each is a fresh agent
with a full context reload (the per-dispatch envelope overhead behind the measured
re-dispatch waste). A shortcut path must therefore **run the early phases inline in
the orchestrator's own context** rather than spinning an execution-context per
phase — especially the first phases (init / refine / outline), which on a
known-shape request carry little cognition worth a dedicated envelope. Dispatch a
separate execution-context only where a phase genuinely needs a different
model/effort level or heavy isolated cognition (typically only phase-5-execute).

This is the existing in-context rule (`extension-api/standards/dispatch-granularity.md`
§ 4 — per-X loops iterate in one envelope) applied to the *phase* axis, and it
follows the light-lane precedent that already folds Simple-outline +
deliverable-derivation into a single envelope.

**Cheap is not stateless.** Running phases inline (a *compute* decision) is separate
from plan *state*: every plan — including a shortcut or recipe — still creates its
own plan-directory (`.plan/local/plans/{plan_id}/`). State isolation keeps each run
apart and means the plan-bound tooling (`manage-status`, `manage-findings`, the
`ci` abstraction) works uniformly with no plan-less special case. Shortcuts shed
the per-phase *envelopes*, never the plan-directory.

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
