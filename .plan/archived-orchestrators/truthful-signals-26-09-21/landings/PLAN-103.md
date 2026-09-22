# Landing Analysis: PLAN-103 — Wrong-store guard refuses project-local lessons

epic: truthful-signals
workstream: WS-01
pr: 1050 — merged as `a7a657b00`, 2026-07-29 12:36:16 +0000

## Deliverable Fidelity

Merged as *"fix(manage-lessons): scope the store-ownership guard to prefixed components"* — the
refusal-message defect the spec named is addressed. ⚠ Per-deliverable fidelity is **not** established
(no plan report supplied); recorded as **verification debt**.

⭐ **Two CodeRabbit findings were caught and fixed in-run** (`28a1e041d`), both real:

1. **`match()` → `fullmatch()`** — `$` matches before a trailing newline, so `'integration-tests '`
   passed the shape check. Fixed with a regression test.
2. **Non-string coercion** — `from-error` now **rejects** an explicitly-supplied non-string
   `component` instead of defaulting it to `unknown`. ⚠ **A deliberate contract change** that rewrote
   two tests which had pinned the old behaviour — i.e. **test-pins-the-defect, correctly identified
   and correctly unwound** rather than preserved.

## Post-merge PR revisit — an ACK arrived post-merge, and a real re-review is now IN FLIGHT

| Event | Time |
|---|---|
| **PR merged** `a7a657b00` | **12:36:16Z** |
| Operator posts `@coderabbitai review` (explicit re-review request) | ~12:38Z |
| CodeRabbit posts *"Re-reviewing #1050, with particular attention to the `28a1e041d` contract change"* | **12:38:26Z** |

⚠ **The post-merge arrival is an ACK, not a finding — so this does NOT advance the late-arrival
counter, which stays at n=4.** Applying the epic's own standing rule (*an ack is not a review*)
consistently, including where counting it would have looked more dramatic.

⛔ **But the exposure is live and worse than a plain late review**: a re-review was requested
**after** the merge, so CodeRabbit is now reviewing **already-merged code**, with explicit attention
to a **deliberate contract change**. **Any finding it returns lands untriaged in `main` by
construction.** ⇒ **WATCH: re-check #1050's comments; route anything actionable to the untriaged-in-main
sweep.**

## Reconciliation Actions

- [x] row `status` → `shipped`; `pr` = 1050; `landing`; `plan_marshall_plan_id` — all four stamped
- [x] post-merge revisit performed; ack-vs-finding distinction applied; counter held at n=4
- [x] in-flight re-review recorded as an open watch
- [x] verification debt recorded

## Follow-Ups

Six candidate-lessons drained with this landing. Two are notable:

- **`-003` — a vacuous guard introduced BY a fix, plus a test that pinned the old defect.** ⭐ Both
  recurring archetypes, in one change, in a plan whose subject was a wrongly-scoped guard.
- **`-005` — the change-type / scope-estimate heuristics read only `request.md`'s `original_input`
  section.** ⚠ Directly adjacent to PLAN-101 (shipped) and PLAN-57 (staged): another instance of the
  router scoring a **narrower body than the real request**.
