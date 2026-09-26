# PLAN-TRUTH-171: State writers that fabricate, collide, or fail silently

> ⛔⛔ **SUPERSEDED BY PM-MCP (2026-09-26, operator decision; row status `parked`).** `plan-marshall-mcp` replaces both the
> process prose and the Python scripts this plan edits, so implementing it here is legacy work. Its
> implementation-independent content (rules, invariants, classifications, data, fixtures) was extracted to
> `plan-marshall-mcp/doc/known-defects/truthful-signals-carry-over.md` as PM-MCP input.
> **Do NOT emit; un-park only by explicit operator decision.** The spec body below stays intact as the evidence chain.

epic: truthful-signals
workstream: WS-01

> Staged plan spec — one shippable unit of work, ready for `/plan-marshall` hand-off.
> The orchestrator EMITS the command below; it never launches the plan inline.
> This spec is SELF-SUFFICIENT: the emitted command is a one-line pointer and carries no brief.

## Provenance

Staged 2026-09-18 from the corpus-wide lessons sweep. Five lessons, five plans, none previously owned;
all preserved verbatim at `.plan/local/orchestrator/truthful-signals/lessons/{id}.md`.

## Objective

**Five writers and readers of plan state each produce something a consumer cannot tell apart from the
truth** — a fabricated identifier, a collided path, a parsed artefact of prose, a crash dressed as a
guard, and an exit code with nothing behind it:

- An append-only ledger **accepts a fabricated full SHA** reconstructed from an abbreviated one; prefix
  matching then hides it, and consumers must take last-row-wins to survive.
- `phase-2-refine` stages `module_mapping.toon` to a **fixed, non-plan-namespaced** temp path, so
  concurrent refine dispatches silently clobber one another's payload.
- `baseline-reconcile` parses `git merge-tree` **prose lines into synthetic file paths**, inflating the
  conflict count roughly threefold, with no proximity-versus-semantic classification.
- `.get('metadata', {})` is a missing-key guard, not a wrong-type guard: an explicit `metadata: null` —
  which an operator can write by hand — crashes the read.
- `phase_handshake verify` **exits 1 with no stderr**, twice, so the only classification available is
  "residual internal error".

⭐ Each is cheap to fix and expensive to diagnose, which is why all five survived in the corpus rather
than in a plan.

## Deliverables

Eight deliverables (D0–D6 plus the two absorbed at D5a/D5b), re-derived after the 2026-09-18 cleanup merge
rather than summed: `-164`'s D0 collapses into this spec's D0, which already derives the writer population.
D0 is a gate.

**D0 — GATE: derive the fabricated-identity and shared-path populations.** Enumerate (a) every site that
constructs an identifier it did not read from its source of truth (SHAs, ids, paths), and (b) every
`.plan/temp` staging path that is not plan-namespaced. ⛔ Publish both with sizes before fixing any
single member.

**D1 — An identifier is read, never reconstructed.** A full commit SHA comes from `git rev-parse HEAD`,
not from expanding an abbreviation; the ledger refuses a value it cannot verify, and the consumer
contract stops relying on last-row-wins to paper over it.

**D2 — Every temp staging path is plan-namespaced.** No fixed shared filename for a per-plan payload;
concurrent dispatches cannot collide by construction rather than by luck.

**D3 — `baseline-reconcile` parses structure, not prose.** Only real path lines become file paths, and a
conflict carries whether it is proximity or semantic. The inflated count is the visible symptom; the
classification absence is the one that changes an operator's decision.

**D4 — A type guard defends against the wrong type, not only the missing key.** `.get(k, {})` is replaced
where an explicit `null` is reachable, especially in operator-editable documents.

**D5a — ABSORBED from PLAN-TRUTH-164: `worktree-remove` clears the worktree metadata it invalidates.**
`cmd_worktree_remove` contains no clear of `use_worktree` / `worktree_path` / `worktree_branch`, so every
later reader sees a worktree that no longer exists — **five independent sightings across five plans**,
including three dispatched post-merge steps resolving through a removed tree. D0's population derivation
absorbs `-164`'s: the readers that consult those three fields.

**D5b — ABSORBED from PLAN-TRUTH-164 D2: `prune-local-and-remote-ref` is idempotent per ref.**
`worktree-remove` deletes the local branch; the prune verb then errors on its absence and **stops before
pruning the remote-tracking ref** — the exact stale ref it exists to remove. An already-absent local branch
reports `skipped / already_absent`, the verb still prunes the tracking ref, and each ref's outcome is
reported separately. ⭐ This is the same sibling pair as D3: `workflow-integration-git` verbs that assume a
state a sibling verb routinely destroys.

**D6 — A non-zero exit carries a reason, plus controls.** `phase_handshake verify` reports why it failed;
a silent exit 1 is itself a defect. Controls: a fabricated SHA is refused, two concurrent refines keep
their own payloads, a prose-only merge-tree output yields zero file paths, an explicit `metadata: null`
is handled, and a failing verify prints a cause.

## Claim Labels

Each is OBSERVED by the plan that filed the cited lesson; all five are preserved in this epic. ⛔ Re-ground
each at HEAD before scoping (verify-at-outline for all).

- OBSERVED (lesson `2026-08-27-12-001`): a full commit SHA was reconstructed from an abbreviated one and
  accepted into the append-only change ledger; prefix matching hid it.
  - verdict: corroborated | checked_at: 74153664d | by: truthful-signals/cleanup | rescoped: n/a | evidence: manage-change-ledger.py accepts --commit-sha as a caller-supplied value with a PRESENCE check only (lines 161-163, passed through at 169); no format check, no resolvability check, no git rev-parse corroboration. The mechanism is live.
- OBSERVED (lesson `2026-09-02-15-001`): `phase-2-refine` stages `module_mapping.toon` to a fixed,
  non-plan-namespaced `.plan/temp` path — concurrent refine dispatches race.
  - verdict: corroborated | checked_at: 74153664d | by: truthful-signals/cleanup | rescoped: n/a | evidence: phase-2-refine/standards/refine-workflow-detail.md:750 instructs staging the rendered TOON payload to the FIXED, non-plan-namespaced path .plan/temp/module_mapping.toon, consumed at line 764. Concurrent refine dispatches collide.
- OBSERVED (lesson `2026-09-15-08-010`, KEEP of its cluster): `baseline-reconcile` parses merge-tree prose
  into synthetic `file_path` entries. Members `2026-09-15-08-009` (proximity vs semantic), `-011` (a second
  synthetic path per conflict) and `-012` (name the symbols to prove disjointness) retired as redundant —
  ⚠ `-009`'s classification gap is carried into D3 and is NOT covered by the count fix alone.
  - verdict: corroborated | checked_at: 74153664d | by: truthful-signals/cleanup | rescoped: n/a | evidence: _cmd_baseline_reconcile.py:411-414 takes stdout.splitlines()[1:] on rc==1 and returns EVERY non-blank line as a conflicted path, with no filter separating git's conflicted-name block from its trailing informational-message block.
- OBSERVED (lesson `2026-09-15-08-044`): `.get('metadata', {})` does not defend against an explicit
  `metadata: null`.
  - verdict: unverifiable | checked_at: 74153664d | by: truthful-signals/cleanup | rescoped: n/a | evidence: Lesson 2026-09-15-08-044 present; the reachable-explicit-metadata:null call sites were not enumerated (that is D0's .get(k,{}) population sweep).
- OBSERVED (lesson `2026-09-15-08-006`): `phase_handshake verify` exits 1 twice with no stderr captured.
  - verdict: unverifiable | checked_at: 74153664d | by: truthful-signals/cleanup | rescoped: n/a | evidence: Partly overtaken: _handshake_commands.py cmd_verify (line 547) now has named handlers returning structured TOON for each refusal class incl. pr_title_missing at 608-614. Which code path produced the observed silent exit 1 is not identified.
- ⚠ HYPOTHESIS: `2026-09-15-08-017` (the module-mapping validator has no shape for a cross-bundle
  drift-rule test) belongs with D0's population rather than as its own deliverable — ⛔ unsettled; D0
  decides whether it is a sixth member or a separate spec (verify-at-outline).
  - verdict: unverifiable | checked_at: 74153664d | by: truthful-signals/cleanup | rescoped: n/a | evidence: Lesson 2026-09-15-08-017 present; whether it is a sixth member or its own spec is a decision the claim assigns to D0.

## Expected Surface

- OBSERVED: `marketplace/bundles/plan-marshall/skills/manage-change-ledger/` — the ledger writer and its SHA acceptance (D1)
- OBSERVED: `marketplace/bundles/plan-marshall/skills/phase-2-refine/` — the temp staging path (D2)
- OBSERVED: `marketplace/bundles/plan-marshall/skills/workflow-integration-git/scripts/` — `baseline-reconcile`'s merge-tree parse (D3)
- OBSERVED: `marketplace/bundles/plan-marshall/skills/manage-status/scripts/` — the metadata read (D4)
- OBSERVED: `marketplace/bundles/plan-marshall/skills/plan-marshall/scripts/` — `phase_handshake verify` (D5)
- HYPOTHESIS: `marketplace/bundles/plan-marshall/skills/phase-4-plan/` — the module-mapping validator, if D0 admits it (verify-at-outline)
- OBSERVED: `test/plan-marshall/manage-change-ledger/`, `test/plan-marshall/workflow-integration-git/`, `test/plan-marshall/manage-status/` — D6's controls
- OBSERVED: `marketplace/bundles/plan-marshall/skills/workflow-integration-git/scripts/git-workflow.py` — `cmd_worktree_remove` and its `worktree-create` counterpart (D5a; absorbed from PLAN-TRUTH-164)
- OBSERVED: `marketplace/bundles/plan-marshall/skills/workflow-integration-git/scripts/_cmd_prune_ref.py` — the prune verb (D5b; absorbed from PLAN-TRUTH-164)
- HYPOTHESIS: `marketplace/bundles/plan-marshall/skills/manage-status/**` — the metadata read/write surface for the three worktree fields (D5a) (verify-at-outline)

## Dependencies and Sequencing

- Depends on: none.
- ⚠ D3 shares `workflow-integration-git/scripts/` with `PLAN-TRUTH-164` (worktree-remove leaves state
  stale) and `PLAN-TRUTH-170` D4 (the staging boundary). Sequence; `-170` and this plan are the closer
  pair and must not run together.
- ⚠ D4 shares `manage-status/scripts/` with `PLAN-TRUTH-156` and `-170` D3.

## Hand-Off Command

```text
/plan-marshall task="implement .plan/local/orchestrator/truthful-signals/plans/PLAN-TRUTH-171-state-writers-that-fabricate-collide-or-fail-silently.md"
```

## Write-Boundary

The plan implementing this spec touches only its own repository source and tests. It creates and edits
NO file under `.plan/local/orchestrator/` other than its own `inbox/{sender}-{seq}` message — the
orchestrator owns every other ledger write — and reports its outcome through its PR and its inbox
message. The inbox exception's qualifiers and the sole sanctioned write mechanism are stated in
`persona-plan-orchestrator/standards/orchestration-model.md` § Ledger Write-Boundary.
