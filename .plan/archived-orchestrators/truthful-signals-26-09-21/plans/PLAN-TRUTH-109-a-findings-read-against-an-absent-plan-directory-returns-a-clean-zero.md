# PLAN-TRUTH-109: A findings read against an absent plan directory returns a clean zero

epic: truthful-signals
workstream: WS-01

> Staged plan spec — one shippable unit of work, ready for `/plan-marshall` hand-off.
> The orchestrator EMITS the command below; it never launches the plan inline.
> This spec is SELF-SUFFICIENT: the emitted command is a one-line pointer and carries no brief.
> See `persona-plan-orchestrator/standards/orchestration-model.md` for the tier and hand-off contract.

## Provenance

Staged 2026-08-24 on operator direction, after the operator asked why three defects visible in a run
transcript had not reached the orchestrator. **The plans had filed all three.** The orchestrator's own
check had returned a clean zero from a store nobody was writing to.

## Objective

**`manage-findings list --plan-id X` returns `status: success` / `total_count: 0` when the plan
directory it resolved does not exist.** Measured first-party, 2026-08-24, from the main checkout:

| Plan | `manage-findings list` | Actual, on disk |
|---|---|---|
| `plugin-doctor-detector-coverage-residue` | **`total_count: 0`** | **49** findings, 10 files |
| `orchestrator-inbox-and-landing-residue` | **`total_count: 0`** | **36** findings, 6 files |
| `metrics-ledger-readers-and-timestamp-provenance` | **`total_count: 0`** | **31** findings, 7 files |
| `build-gates-test-suite-confidence-ci-workflow-lint` | **`total_count: 0`** | **62** findings, 9 files |

**178 findings, 26 of them pending, reported as four clean zeros.**

The mechanism: those plans run in worktrees and write
`.plan/local/worktrees/{id}/.plan/local/plans/{id}/artifacts/findings/`. The verb resolved the
main-anchored `.plan/local/plans/{id}/`, **which does not exist**, and reported an empty result rather
than an unresolved one.

⛔ **The defect is NOT that the verb chose the wrong root.** Which root is correct depends on caller
context and is a separate design question. **The defect is that an absent store is indistinguishable
from an empty one** — the archetype this epic exists to close, in the orchestrator's own instrument.

⭐⭐ **A SIBLING SKILL ALREADY SOLVES THIS AND IS THE MODEL TO COPY.** `manage-lessons` resolves its
main-anchored stores and states: *"**Both are required**, so either one failing is a structured
`store_unresolved` error — never a zero. The error names the store that actually failed:
`store_resolution: unresolved`, `plans_root_state: unknown`, and `unresolved_store: plans | lessons`."*
It further distinguishes the non-faulting `plans_root_state: missing` (*"the scan could not look"*)
from a resolved store that simply holds nothing. ⇒ **Three states, already shipped, one skill over.**

## Deliverables

Six deliverables. D0 is a gate. D5 was folded in 2026-08-26 from a foreign-machine report.

**D0 — GATE: derive which read verbs share the defect, and what each SHOULD resolve.** ⛔ **Do not fix
`list` alone.** Sweep every read-side verb across `manage-findings` (`list`, `get`, `qgate`,
`assessment`) and its siblings for the same shape: a store path that may not exist, and a zero-valued
success on that path. **Publish the swept population and its size.**

⚠ **Answer the root question explicitly and separately from the zero question**: when an orchestrator in
the main checkout asks for a worktree plan's findings, should the verb (a) resolve the worktree store,
(b) refuse and name the worktree, or (c) require an explicit root? ⭐ **(b) is likely right and is the
cheapest** — a refusal that names where the store actually is costs nothing and cannot mislead — but D0
decides, and **the zero fix is correct under all three**, so D1 does not wait on it.

**D1 — an absent or unresolved store is never a zero.** Adopt `manage-lessons`' vocabulary rather than
inventing one: a structured `store_unresolved` (or equivalent) naming which store failed, and a
non-faulting *resolved-but-empty* state distinct from it. ⛔ **Three states — `unresolved` / `resolved
but absent` / `resolved and empty` — must be separately representable**, exactly as the sibling already
does. ⚠ Reuse its field names where they fit; a second vocabulary for one concept is the
producer-consumer drift this epic tracks.

**D2 — the orchestrator gets a sanctioned way to read a live plan's findings.** ⛔ **This is the
deliverable that closes the operator's actual question**, and without it D1 only converts a silent
wrong answer into a loud one. Per D0's root decision, provide a supported path — an explicit
`--worktree` / root argument, or a resolver that finds the live plan's real store. ⚠ **Read-only.** The
orchestrator has no authority to resolve another plan's findings and must not acquire one here.

**D3 — tests, with the matched control that is the whole point.** Assert: an absent store yields the
unresolved state, **a resolved-but-empty store yields a genuine zero**, and a live worktree plan's
findings are readable through the supported path. ⛔ **The resolved-and-empty control is
load-bearing** — a fix that makes every zero an error is as wrong as one that makes every error a zero,
and this epic has recorded the vacuous-guard archetype being re-introduced by its own fix at least
twice.

**D5 — FOLDED 2026-08-26: the same false negative WITHOUT an absent store — the Q-Gate split.**
⛔ **D0's sweep as written would MISS this one**, because it looks for "a store path that may not
exist". Here the store exists, is written, and is readable — and the read verb still reports absence,
because the enumeration it uses deliberately excludes it. `get_finding` / `resolve_finding` enumerate
through `_list_finding_files`, whose own docstring says *"(excluding qgate-\*, assessments)"*, so a
Q-Gate finding resolves as `Finding not found: {hash_id}`. The **same** skill's `query_findings` merges
the Q-Gate store and reports it with `qgate_included: True`. ⇒ **One skill, two populations, and only
the list side knows there are two.** ⭐ **Widen D0's sweep predicate accordingly**: the shape is *a read
verb whose enumeration is narrower than the store set its own sibling verbs write and read*, of which
"the path may not exist" is only one instance. ⚠ The remedy is NOT simply "make `get` scan qgate too" —
the Q-Gate records are phase-scoped and a resolution written against one may not be meaningful; D0
decides, and the **naming** half is unconditional: a hash that exists in a store this verb declines to
scan must not be reported as not-found.

**D4 — record the interim workaround and its expiry.** Until this lands, the orchestrator reads
`.plan/local/worktrees/*/.plan/local/plans/*/artifacts/findings/*.jsonl` directly. ⛔ **That bypasses
the script funnel and is a workaround, not a practice** — document it as such in the epic ledger with
this plan named as what retires it, so it does not silently become the way findings are read.

## Expected Surface

- `marketplace/bundles/plan-marshall/skills/manage-findings/scripts/**` — including `_findings_core.py`:304 `_list_finding_files`, :431 `get_finding`, :439 `resolve_finding`, :~400 `query_findings` (the Q-Gate merge path), and `manage-findings.py`:160 `cmd_resolve` *(D5)*
- `marketplace/bundles/plan-marshall/skills/manage-findings/SKILL.md`
- `marketplace/bundles/plan-marshall/skills/manage-lessons/**` *(expected READ-ONLY — the model being copied)*
- `test/plan-marshall/manage-findings/**`

## Dependencies and Sequencing

⛔ **Re-derive with `corpus cross-check` at emit time.**

- ⚠ **`PLAN-TRUTH-100`** owns the mid-run inbox channel and has been extended with the plan→orchestrator
  direction. **That is the eventual replacement for the sweep D2 enables**; this plan makes the pull
  path correct, `-100` makes the push path exist. **Complementary; neither blocks the other.**
- **Depends on:** nothing.

## Claim Labels

- OBSERVED: `manage-findings list --plan-id X` returned `status: success` / `total_count: 0` for four live plans whose worktree stores hold 49, 36, 31 and 62 findings — measured 2026-08-24 from the main checkout.
  - verdict: corroborated | checked_at: 31bed3e76 | by: truthful-signals/cleanup | rescoped: n/a | evidence: REPRODUCED LIVE AT THIS SHA on a plan that did not exist when the claim was written. manage-findings list --plan-id a-failing-ci-call-reports-success returns status: success and total_count: 0 while that plan runs in a worktree and .plan/local/plans/a-failing-ci-call-reports-success/ is absent from main. The defect is not historical
- OBSERVED: those plans write `.plan/local/worktrees/{id}/.plan/local/plans/{id}/artifacts/findings/`, and `.plan/local/plans/{id}/` does not exist for any of them.
  - verdict: corroborated | checked_at: 31bed3e76 | by: truthful-signals/cleanup | rescoped: n/a | evidence: Confirmed for the CURRENT population, which has fully turned over: all three live worktree plans (a-failing-ci-call-reports-success, metrics-ledger-readers-and-timestamp-provenance, verdict-field-read-and-write-integrity) have NO .plan/local/plans/{id}/ directory in main
- OBSERVED: `manage-lessons` already returns a structured `store_unresolved` naming the failed store, and separately distinguishes `plans_root_state: missing` from a resolved store holding nothing — read at `manage-lessons/SKILL.md` § list-stalled / restore-from-plan error tables.
  - verdict: unverifiable | checked_at: 31bed3e76 | by: truthful-signals/cleanup | rescoped: n/a | evidence: manage-lessons' store_unresolved and plans_root_state surfaces were not read at this sha; the comparison the claim draws is to another skill's payload shape and was not re-derived
- OBSERVED *(D5, folded 2026-08-26)*: `resolve_finding` asserts parent existence via `get_finding`, which enumerates only `_list_finding_files(plan_id)` — read at `marketplace/bundles/plan-marshall/skills/manage-findings/scripts/_findings_core.py`:431 § `get_finding` and :439 § `resolve_finding`
- OBSERVED *(D5)*: `_list_finding_files` builds its file list from `FINDING_TYPES` only, and its docstring states the exclusion explicitly — *"List all per-type finding JSONL files (excluding qgate-\*, assessments)"* — read at `_findings_core.py`:304 § `_list_finding_files`
- OBSERVED *(D5)*: the same module's list path merges the Q-Gate store and advertises the merge in its payload (`qgate_included: True`, with separate `plan_count` / `qgate_count`), so the two populations are known to the skill and invisible to `get`/`resolve` — read at `_findings_core.py`:~420 § `query_findings` return
- HYPOTHESIS *(D5)*: `promote` and `mark_finding_responded` share the same `get_finding` precondition and therefore the same blind spot, making the false-not-found class wider than `resolve` alone — confirm/refute at `_findings_core.py` § the callers of `get_finding` (verify-at-outline). ⛔ Enumerate the caller set; do not sample it.
- Verify-first clause *(D5)*: before scoping the remedy, settle against the implementing source whether a Q-Gate record carries the fields `resolve_finding` writes (`resolution`, `resolution_detail`, `responded`). If it does not, the remedy is a *distinguishing error message* naming the store the hash was found in, NOT an enumeration widening — and D5 re-scopes to that.
- OBSERVED: 26 pending findings sit in those four stores, including one titled *"OPERATOR DECISION OWED: the zero-skip gate is inert — arm it or delete it"* — **a finding addressed to the operator that the operator cannot see.**
  - verdict: unverifiable | checked_at: 31bed3e76 | by: truthful-signals/cleanup | rescoped: n/a | evidence: The 26 pending findings were counted on 2026-08-24 across four plans that have since landed. The population no longer exists to recount, so the figure is unrepeatable rather than refuted. The operator-addressed finding it names may be lost with those stores - worth D0's attention
- HYPOTHESIS: other read verbs in the same skill share the shape — confirm/refute at D0's sweep (verify-at-outline).
  - verdict: unverifiable | checked_at: 31bed3e76 | by: truthful-signals/cleanup | rescoped: n/a | evidence: Deferred to D0's sweep of other read verbs in the skill; population unenumerated
- HYPOTHESIS: refusing-and-naming (option b) is cheaper and safer than cross-root resolution — confirm/refute at D0 (verify-at-outline).
  - verdict: unverifiable | checked_at: 31bed3e76 | by: truthful-signals/cleanup | rescoped: n/a | evidence: A cost/safety design comparison between two remedies, settled at D0 by judgement rather than against implementing source
- Verify-first clause: the resolved-but-empty control must be red before the fix and green after — a fix that turns every zero into an error is the inverse defect and this epic has shipped that inversion before.
  - verdict: unverifiable | checked_at: 31bed3e76 | by: truthful-signals/cleanup | rescoped: n/a | evidence: A forward verify-first CLAUSE requiring a matched control (resolved-but-empty must be red before the fix, green after)
