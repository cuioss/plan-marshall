> ⛔⛔ **SUPERSEDED BY PM-MCP (2026-09-26, operator decision; row status `parked`).** `plan-marshall-mcp` replaces both the
> process prose and the Python scripts this plan edits, so implementing it here is legacy work. Its
> implementation-independent content (rules, invariants, classifications, data, fixtures) was extracted to
> `plan-marshall-mcp/doc/known-defects/truthful-signals-carry-over.md` as PM-MCP input.
> **Do NOT emit; un-park only by explicit operator decision.** The spec body below stays intact as the evidence chain.

> ⛔ **MERGED OUT 2026-09-18 (cleanup A5) — this spec is RETIRED and must not be launched.**
> Its substance now lives in **PLAN-TRUTH-170** as D4a: the finalize seam records less than it does — its D0 already derives the step-record population this spec would have derived separately.
> The deliverables were carried, not summarised, and this spec's own gate collapsed into the
> receiving spec's D0 rather than being duplicated. This file stays on disk unchanged below the
> line — a superseded spec is never deleted. Its queue row is `parked`, because
> `queue --transition` cannot write `superseded` (see PLAN-TRUTH-143 D9).

# PLAN-TRUTH-156: `mark-step-done` must derive `head_at_completion`, never accept it from the caller

epic: truthful-signals
workstream: WS-01

> Staged plan spec — one shippable unit of work, ready for `/plan-marshall` hand-off.
> The orchestrator EMITS the command below; it never launches the plan inline.
> This spec is SELF-SUFFICIENT: the emitted command is a one-line pointer and carries no brief.
> See `persona-plan-orchestrator/standards/orchestration-model.md` for the tier and hand-off contract.

## Provenance

Staged 2026-09-13 from a candidate-lesson filed by `plan-truth-139` (`inbox/plan-truth-139-003.md`) at
its own landing (PR #1479). The plan self-caught and self-corrected the defect this spec exists to close
— logged at WARNING (decision `858d9c`) rather than silently amended, which is what surfaced it.

## Objective

**`mark-step-done` accepts `head_at_completion` as a caller-supplied `--head-at-completion` argument
instead of deriving it itself, so a well-formed-but-fabricated 40-character sha is indistinguishable from
a resolved one to every downstream reader.**

Nine of PLAN-TRUTH-139's 20 terminal finalize steps carried a `head_at_completion` field. One of the nine
was stamped with a FABRICATED value: the short hash `1e2fddb7b` padded out to
`1e2fddb7b1b3b1d7eb6b8c2c9c8b0f8e3e1a0b5c` rather than resolved — the real sha was
`1e2fddb7b814755abd0b765e0bc519099a86b14d`. It was self-caught and re-stamped from `git rev-parse HEAD`
before it shipped. The run's own note states the consequence had it stood: the dispatcher's re-entry
check compares `head_at_completion` against live HEAD, so an invented sha never matches and the gate
re-fires forever — and, worse, a reader takes the record as evidence about a tree that never existed.

Resolving HEAD in the worktree the step just certified involves no judgement and has exactly one correct
answer, so there is no reason for the value to travel through an LLM-authored argument at all. Every
occurrence is an opportunity for the SHAPE of a sha (40 hex characters) to be satisfied without its
CONTENT being resolved.

## Deliverables

Two deliverables.

**D0 — GATE: derive the population of `mark-step-done` call sites that currently supply
`--head-at-completion`, and confirm the verb has no legitimate reason to accept a caller value that
diverges from the worktree it just certified.** Publish the population and its size — this spec's
Provenance names one instance found by one self-correction, never the population.

**D1 — `mark-step-done` derives `head_at_completion` itself and stops accepting it as an input.** The verb
already knows the plan and can resolve the worktree; a caller-supplied value has no legitimate divergence
from the tree the step just ran against. If a transitional period is needed, reject any supplied value
that does not equal the derived one, and name both in the rejection — a mismatch is either a fabricated
identifier or a step reporting on a tree it did not test, and both are defects rather than inputs to
honour.

## Claim Labels

- OBSERVED: `mark-step-done` accepts `--head-at-completion HEAD_AT_COMPLETION` as a caller-supplied
  argument (`manage-status.py mark-step-done --help`). First-party at this spec's staging.
  - verdict: corroborated | checked_at: 77cb2e251 | by: truthful-signals/cleanup | rescoped: n/a | evidence: manage-status.py mark-step-done --help still shows --head-at-completion HEAD_AT_COMPLETION as a caller-supplied argument at this HEAD
- OBSERVED: the implementation lives in `marketplace/bundles/plan-marshall/skills/manage-status/scripts/_cmd_mark_step.py`
  (28 `head_at_completion` references — the primary carrier of this field in the codebase, per
  `architecture search --content --pattern head_at_completion`).
  - verdict: corroborated | checked_at: 77cb2e251 | by: truthful-signals/cleanup | rescoped: n/a | evidence: architecture search --content --pattern head_at_completion still shows _cmd_mark_step.py as the dominant carrier (28 references) at this HEAD
- ⚠ HYPOTHESIS: no `mark-step-done` call site has a legitimate reason for its supplied
  `head_at_completion` to diverge from the worktree's own resolved HEAD at call time. ⛔ Reasoned from the
  verb's own contract, NOT exhaustively checked against every caller. D0 owns the population derivation
  and may find a caller with a genuine reason to supply a different value — that is a result, and it must
  be published as one (verify-at-outline).
  - verdict: unverifiable | checked_at: 77cb2e251 | by: truthful-signals/cleanup | rescoped: n/a | evidence: Population question (every mark-step-done call site) is D0's own job; no exhaustive caller sweep run at cleanup time
- ⚠ HYPOTHESIS: this is the same shape as the `reviewed_commit_sha` re-stamping defect already noted
  against the participation ledger, and this PR's own `create-pr` `pr_number` fact going stale — "an
  identifier in a verdict record should be derived at the moment of the verdict." ⛔ Named as a RELATED
  pattern, not folded — those two are separately-tracked, unowned defects at time of staging and are NOT
  in this spec's Expected Surface; D0 states explicitly whether they turn out to share a remedy or stay
  separate (verify-at-outline).
  - verdict: unverifiable | checked_at: 77cb2e251 | by: truthful-signals/cleanup | rescoped: n/a | evidence: reviewed_commit_sha re-stamping and pr_number staleness are separately-tracked, unowned defects elsewhere in this ledger; not cross-checked against this spec's D0 at cleanup time

## Expected Surface

- OBSERVED: `marketplace/bundles/plan-marshall/skills/manage-status/scripts/_cmd_mark_step.py` — the
  `mark-step-done` implementation and its `--head-at-completion` handling (D1)
- OBSERVED: `marketplace/bundles/plan-marshall/skills/manage-status/scripts/manage-status.py` — the CLI
  argument declaration (D1)
- HYPOTHESIS: `test/plan-marshall/manage-status/test_mark_step_done_completion_head_and_keys.py`,
  `test/plan-marshall/manage-status/test_mark_step_head_anchor.py`,
  `test/plan-marshall/manage-status/_mark_step_done_fixtures.py`,
  `test/plan-marshall/manage-status/_manage_status_transition_fixtures.py` — existing coverage that
  exercises `head_at_completion`, likely touched by removing/restricting the caller-supplied argument
  (verify-at-outline)
- HYPOTHESIS: `marketplace/bundles/plan-marshall/skills/manage-status/SKILL.md` — the documented
  invocation surface for `mark-step-done` (verify-at-outline)

## Dependencies and Sequencing

- Depends on: none.
- ⚠ **Related but NOT merged**: the `reviewed_commit_sha` re-stamping defect (participation ledger) and
  `create-pr`'s `pr_number` staleness are the same archetype — an identifier in a verdict record accepted
  or re-stamped rather than derived at the moment of the verdict — but are separately-tracked, unowned
  defects. D0 decides whether a shared remedy is worth pursuing; this spec's own surface stays scoped to
  `mark-step-done` unless D0 finds otherwise.
- ⛔ Re-derive `corpus cross-check` before emitting — this spec's surface has never been machine-checked
  against the corpus.

## Hand-Off Command

```text
/plan-marshall task="implement .plan/local/orchestrator/truthful-signals/plans/PLAN-TRUTH-156-mark-step-done-must-derive-head-at-completion-never-accept-it.md"
```

## Write-Boundary

The plan implementing this spec touches only its own repository source and tests. It creates and edits
NO file under `.plan/local/orchestrator/` other than its own `inbox/{sender}-{seq}` message — the
orchestrator owns every other ledger write — and reports its outcome through its PR and its inbox
message. The inbox exception's qualifiers and the sole sanctioned write mechanism are stated in
`persona-plan-orchestrator/standards/orchestration-model.md` § Ledger Write-Boundary.
