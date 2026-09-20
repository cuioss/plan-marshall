# PLAN-86: An Unchecked Finding-Persist Loses The Finding, And The Referral Still Reports Success

epic: truthful-signals
workstream: WS-01

> Staged plan spec — one shippable unit of work, ready for `/plan-marshall` hand-off.
> Split out 2026-07-27 from **PLAN-59 D2b** on operator decision: the defect is a live data-loss
> path, PLAN-59 is large by design and deep in the queue, and this fix is small and independently
> shippable. PLAN-59 retains the *promotion* of the durable rule into the governing standard
> (its D3 write-direction clause); this plan closes the *instance*.
> This spec is SELF-SUFFICIENT: the emitted command is a one-line pointer and carries no brief.

## Objective

A phase-5 executor persists each failing finding to the Q-Gate store and then returns
`triage_required`, which tells the orchestrator to read those findings **by reference**. The persist
call's exit status is never checked. When the persist fails, the executor proceeds as though the
record landed: the referral points at a store that never received it, and nothing anywhere reports a
failure. Make a failed finding-persist **loud and fail-closed** at every persist site in the family,
so an unstorable finding can never be silently dropped behind a confident referral.

This is the epic's flagship archetype in its least visible form — the *write* direction. It is not
hypothetical: it fired in a real cross-repo run (API-Sheriff PR #114), silently lost an escalation
finding, cost an extra orchestrator round-trip, and surfaced only because a human noticed an absence.

## Deliverables

### D1 — GATE: establish which persist sites are actually unchecked, and settle the fail-loud shape (mutates nothing)

(a) **Verify each of the five call sites first-party** against the implementing source, and record a
per-site verdict (`unchecked` / `already-checked` / `not-a-persist`). Do not assume the Step 11c shape
generalizes — the sibling sites are OBSERVED as call sites but their unchecked-ness is HYPOTHESIS.
(b) **Settle where the check belongs.** Two candidate layers, and the choice matters:
a *doc-contract* fix (the workflow step tells the executor to check and fail loudly) versus a
*structural* fix (the persist seam itself cannot be called in a fire-and-forget way, or the referral
signal cannot be composed without evidence the store received the records). ⚠ **Bias toward the
structural layer**: a doc-contract fix asks an LLM executor to remember a check, which is the
documentation-layer vacuous-guard shape this epic tracks (see PLAN-85) — the same failure mode, one
level up. Record the rationale either way.
(c) **Decide the failure semantics.** A finding that cannot be stored must not degrade into a clean
pass NOR into a referral with no content. State explicitly what the executor returns instead, and
confirm the orchestrator's consuming branch handles it — a new terminal state nothing consumes would
relocate the silence rather than remove it.

### D2 — implement the D1 remedy across every site D1 marked `unchecked`

Scoped to D1's verdicts. **Hard constraint: no site may be "fixed" by suppressing or downgrading the
finding** — the failure must become louder, never quieter. If D1 chose the structural layer, the
fire-and-forget call shape must become unavailable, not merely discouraged.

### D3 — tests

(a) A persist that fails (rejected invocation / unwritable store) produces D1's chosen loud behaviour
and **never** a clean pass or a content-free referral. (b) **The test must be verified to FAIL against
pre-fix code** — this epic has a recorded `test-pins-the-defect` archetype, and a test written against
post-fix behaviour only proves the code matches itself. (c) A successful persist path is unaffected.

Three deliverables (D1 a gate) — well under the split guard. Deliberately small: the value is closing
a live loss path quickly, not breadth.

## Claim Labels

- OBSERVED: an argparse rejection on `manage-findings qgate add` was survived and an escalation
  finding was lost — operator-relayed, first-party narrative from the merged API-Sheriff PR #114.
- OBSERVED: the Step 11c persist contract specifies **no exit-code check and no on-failure
  behaviour** — read at `phase-5-execute/SKILL.md` § Step 11c (`:870-879`), which says only
  "Persist each failing finding to the Q-Gate findings store" and "One `qgate add` call per finding".
- OBSERVED: the referral is by-reference, so a lost record cannot be recovered downstream — read at
  `phase-5-execute/SKILL.md` § 11d (`:881`), "return a structured terminal payload … the orchestrator
  owns the triage dispatch".
- OBSERVED (asserted absence, verified): no `escalation` member exists in `FINDING_TYPES` — read at
  `tools-file-ops/scripts/constants.py:96-121`. Recorded here only as context for *why* a persist may
  be rejected; **the rejection cause is PLAN-85's scope, not this plan's.**
- OBSERVED (asserted absence): the invocation surface is NOT stale — `qgate add` is a real subcommand
  (`manage-findings/SKILL.md` § Canonical invocations → `qgate add`) and `--phase 5-execute` is a valid
  member of `QGATE_PHASES` (`tools-file-ops/scripts/constants.py:30`). Do not re-scope this plan as a
  doc-drift fix.
- HYPOTHESIS: the four sibling persist sites are unchecked in the same way as Step 11c —
  confirm/refute at `phase-6-finalize`-adjacent phase-5 sites `phase-5-execute/SKILL.md:769`, `:940`,
  `:976` and at `phase-5-execute/scripts/scope_creep_check.py` § `_emit_finding` (`:102`)
  (verify-at-outline).
- Verify-first clause: **D1(a) must settle every site verdict against the implementing source before
  D2 scopes.** A site that turns out to be already-checked is dropped from D2, not "hardened" anyway.
  If ALL sites prove already-checked, the premise is refuted — loop back and re-scope against the real
  mechanism rather than implementing a redundant guard.

## Expected Surface

- OBSERVED: `phase-5-execute/SKILL.md` — Step 11c persist contract `:870-879`, referral contract
  `:881`; sibling persist sites `:769`, `:940`, `:976`.
- OBSERVED: `phase-5-execute/scripts/scope_creep_check.py:102` — the `qgate add` emit helper.
- HYPOTHESIS: the `manage-findings` `qgate add` output contract, IF D1(b) picks the structural layer
  and the seam needs an affirmative stored-receipt in its return (verify-at-outline; a plain exit-code
  check needs no change here).
- HYPOTHESIS: `plan-marshall/workflow/execution.md` § "Verification-feedback triage (leaf returned
  triage_required)" — only if D1(c)'s failure semantics add a state the orchestrator must consume
  (verify-at-outline).
- OBSERVED: tests under `test/plan-marshall/phase-5-execute/**`.

**Disjointness:** `phase-5-execute` (+ possibly `manage-findings`). Disjoint from the five plans
currently in flight — PLAN-79 (`platform-runtime`/`manage-status`/`manage-locks`), PLAN-56
(`marshall-orchestrator`), PLAN-80 (`workflow-integration-github`/`automatic-review`), PLAN-75
(`manage-execution-manifest`), PLAN-62 (`manage-run-config`/build engines/`ci_base`). ⚠ **Adjacent to
PLAN-85** — same originating incident, different half (PLAN-85 owns why the call was *rejected*, this
owns why the rejection was *survivable*); they touch different files, so they are file-disjoint, but
see sequencing.

## Dependencies and Sequencing

- Depends on: none. Independently shippable — that is the point of the split.
- Overlaps with: **PLAN-59** — no file overlap, but a **contract** relationship: PLAN-59's D3 promotes
  the durable write-direction rule into the governing standard, and this plan is its worked instance.
  Whichever lands second re-grounds against the other. ⚠ **PLAN-59's D2b MUST NOT be implemented
  twice** — its D2b now points here.
- Adjacent to: **PLAN-85** (the rejection cause). Deliberately NOT sequenced behind it: this fix is
  correct regardless of *why* any given persist call fails, and gating it on PLAN-85's enum question
  would keep a live loss path open for a diagnosis it does not need. If PLAN-85 lands first, D1 gains
  a confirmed rejection mechanism as a test fixture — useful, not required.
- Adjacent to: `manage-findings` store internals — untouched; this plan changes how callers treat a
  failed persist, never the store's own write path.

## Hand-Off Command

```text
/plan-marshall task="implement .plan/local/orchestrator/truthful-signals/plans/PLAN-86-unchecked-finding-persist-loses-the-finding.md"
```

## Write-Boundary

Repository source + tests only. NO writes to `.plan/local/orchestrator/` **ledger state**
(`status.json`, `epic.md`, `plans/`, `landings/`); the `inbox/` channel is the sanctioned exception
for orchestrated plans. See `persona-marshall-orchestrator/standards/orchestration-model.md`
§ Ledger Write-Boundary.
