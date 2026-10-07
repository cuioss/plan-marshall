# PLAN-TRUTH-100: The inbox has no delivery path to a running plan

epic: truthful-signals
workstream: WS-01

> Staged plan spec — one shippable unit of work, ready for `/plan-marshall` hand-off.
> Lives at `plans/PLAN-TRUTH-100-the-inbox-has-no-delivery-path-to-a-running-plan.md` and is
> queued in the epic `status.json` `plans[]` field. The orchestrator EMITS the command below;
> it never launches the plan inline.
> This spec is SELF-SUFFICIENT: the emitted command is a one-line pointer and carries no
> brief, so every per-plan carry is authored here and nowhere else.
> See `persona-plan-orchestrator/standards/orchestration-model.md` for the tier and
> hand-off contract.

## Objective

Build the mid-run delivery channel the orchestrator↔plan inbox deliberately left unbuilt, so an
orchestrator can reach a plan that is already running. Today the channel is one-way by construction: a
plan writes, the orchestrator drains between plans, and **no plan-side reader exists anywhere in the
tree**. The `--target-plan` field exists but is a *visibility* device — a message aimed at a `running`
plan is REFUSED at write time (`undeliverable_to_running_plan`) precisely because nothing would ever
read it. This plan replaces that refusal with an actual delivery path, and gives the running plan two
places to notice a message: **at every phase transition, and on return from every dispatched sub-agent.**

⚠ **This plan amends a standing invariant, and that is the substance of the work, not a side effect.**
`orchestration-model.md` § Ledger Write-Boundary currently states the channel is *"One-way — the plan
writes, the orchestrator drains"* and that *"The plan never reads the ledger to make a decision."* D0
settles the amended wording BEFORE any code changes. A plan that quietly builds a reader while leaving
that sentence standing produces exactly the doc-contract divergence this epic exists to remove.

## Deliverables

SEVEN deliverables, under the epic's split guard of 12. D0 is a gate: nothing downstream starts until the
contract and the amended invariant are settled and recorded. **D6 is the API model** — added after the
first staging, when the operator observed that the spec named a mailbox and two check-points but modelled
no callable surface and no path-resolution contract. Read D6 BEFORE D1–D3: it is the shape those three
implement against, and its (c)/(d) clauses forbid the hand-rolled resolution they would otherwise invite.

**D0 — GATE: settle the delivery contract, the mailbox residency, and the amended invariant.**
Three decisions, each recorded with its rationale before any code moves.
1. **Residency.** The orchestrator MUST NOT write into `.plan/local/plans/` — its direct-file-write
   carve-out is bounded to `.plan/local/orchestrator/{slug}/**`. ⇒ **The plan-directed mailbox lives
   inside the epic tree and the PLAN reads it.** Propose `outbox-to-plan/{plan_id}-{NNN}.md` as the
   sibling of `inbox/`, keeping the two directions in separate directories so a drain of one never
   enumerates the other. ⛔ Do NOT solve this by relaxing the orchestrator's write carve-out — that
   inverts a boundary two standards depend on.
2. **Effect vocabulary — bounded, and small.** Decide what a delivered message may DO. An unbounded
   actionable channel makes a plan's behaviour depend on out-of-band state, which breaks the
   resumability the whole lifecycle rests on. Start with `advisory` (record and surface, no control
   flow) and justify any second kind explicitly. ⛔ A message MUST NOT be able to silently re-scope a
   running plan's deliverables.
3. **The amended invariant.** Rewrite § Ledger Write-Boundary's one-way sentence to state the bounded
   two-way contract, and state the bound: the plan reads a mailbox addressed to it, and still never
   reads the epic's queue, `epic.md`, or another plan's messages.

**D1 — the writer: replace the refusal with delivery.** `undeliverable_to_running_plan` today refuses
exactly the messages this channel is for. Re-scope it: a message to a **running** plan now queues for
delivery; a message to a plan that does not exist, or to an unsafe identifier, still refuses with its
existing code. **Matched control required**: one test proving a running-plan message now queues, and one
proving a nonexistent-plan message still refuses — the pair is what proves a *re-scope* rather than a
removed guard. Update `inbox-envelope.md` § Write-side deliverability in the same change; its
deliverability table is the contract and currently states the opposite outcome.

**D2 — the reader: a plan-side read verb, fail-open by construction.** Add the ONE sanctioned read
seam. It MUST be read-only, MUST NOT fault, and MUST distinguish its zeros the way `inbox list` already
does: *mailbox absent* (could not look) and *mailbox present but empty* (looked, found nothing) are
different answers and are separately representable. An absent mailbox, an unreadable message, or a
missing epic resolves to a normal empty read — **never to an error that could fail the plan.** A plan
whose orchestrator never wrote anything must behave byte-identically to today.

**D3 — the two check-points (the operator's explicit requirement).** Poll the mailbox at BOTH:
- **(a) Every phase transition** — at the `manage-status` phase-transition seam (`set-phase` /
  `update-phase` / `transition`), fired BEFORE the new phase's first work so a message can be seen
  before the work it concerns begins.
- **(b) Every return from a dispatched sub-agent** — ⭐ **use the call-site discipline the codebase has
  already shipped**: `manage-status assert-step-recorded` is documented as being *"called after every
  dispatched (Task-agent) step returns"* and performs **zero writes** to `status.json`
  (`manage-status/SKILL.md:516`). That is the same shape and the same site class this poll needs; adopt
  it rather than inventing a second return-side convention.
Both check-points are fail-open: a poll that cannot read proceeds silently. ⛔ Neither check-point may
introduce a blocking wait — a plan must never stall on an empty mailbox.

**D4 — consumption AND non-consumption are both visible.** A delivered message records an
acknowledgement (which plan read it, at which check-point). A message NEVER read before the plan ends
**must not die silently**: it returns to the orchestrator's ordinary drain marked undelivered, carrying
the reason. ⛔ *"The plan finished and the mailbox was empty"* and *"the plan finished without ever
looking"* are different outcomes and must be separately representable — the same *which-zero-is-this*
discipline `inbox list`'s `inbox_state` and `closed_senders` already enforce on the other direction.

**D5 — tests: matched controls plus a POPULATION-DERIVED check-point roster.**
- **Positive**: a message written to a running plan is delivered at the next check-point of each kind.
- **Negative control**: with no message, behaviour, call count, and persisted state are unchanged —
  this is what proves the channel is inert when idle rather than merely working when used.
- ⛔ **The check-point roster MUST be population-derived**, following `test/_shared/_dispatch_roster.py`:
  enumerate every phase-transition site and every dispatch-return site from the source, then assert each
  one polls. A hand-listed roster passes forever while a newly-added site silently never polls. **The
  detector MUST publish the population size it derived**, so a roster that degenerates to zero sites
  cannot report green — the vacuous-guard archetype this epic has now recorded six or more times, twice
  introduced by a fix for it.

**D6 — ONE symmetric channel API over the (epic_slug, plan_id) address, resolving BOTH plan faces
through the resolver that already owns them.** *(added 2026-08-23 on operator instruction — the spec as
first staged named a directory and two check-points but modelled NO callable surface, which would have
left every caller to hand-roll addressing and path resolution.)*

**(a) One surface, direction as a parameter — not two parallel APIs.** A plan→orchestrator surface
already ships (`inbox write` / `list` / `validate` / `archive` / `supersede` / `close-stream`). If this
plan adds a second, differently-shaped surface for orchestrator→plan, the channel has two idioms for one
concept and every future author must learn which half they are on. **Model ONE API whose direction is an
argument**, and state explicitly what happens to the existing verbs: either they are re-expressed on it,
or they are retained as the named compatibility face. ⛔ *"A new module that happens to sit next to the
old one"* is not a decision — record which of the two it is.

**(b) The address is the abstraction — and it MUST name which identifier namespace it takes.** A caller
names `(epic_slug, plan_id)` and nothing else. It never passes a path, never joins one, and never learns
whether the target plan is worktree-bound. Both identifiers are validated path-safe by the EXISTING
validator (`_validate_identifier`) before any resolution — the same guard `inbox write` already applies to
`--slug`, `--sender-id` and `--target-plan`.
⛔ **There are TWO plan-identifier namespaces in this system and they are not interchangeable — observed
first-party 2026-08-23 while filing a cross-epic notification.** `--target-plan PLAN-CIS-052` is REFUSED:
`invalid_target_plan — Must match ^[a-z][a-z0-9-]*$`. The uppercase `PLAN-{CODE}-{NNN}` form is an
**orchestrator QUEUE-ROW id**; `--target-plan` takes the **lowercase live plan-marshall plan id**, which is
the `plan_marshall_plan_id` column of that row. ⇒ Two consequences the API must state rather than leave a
caller to discover: **(i)** a `staged` queue row has NO live plan id (the column is empty until launch), so
it is **structurally unaddressable** — a message cannot be aimed at a plan that has not started, and the
API must answer that with a distinct named outcome rather than a validation error that reads like a typo;
**(ii)** the two namespaces must never be silently coerced — no lowercasing a queue-row id to manufacture
a plan id. ⭐ This also bounds D4: a message addressed to a plan that never launches is undeliverable for a
DIFFERENT reason than one the plan never read, and D4's non-consumption record must distinguish them.

**(c) ⛔ Resolution MUST delegate to `file_ops.resolve_plan_context` — do NOT write a third resolver.**
This is the operator's "smart enough to find both locations" requirement, and the repository has already
solved it and already paid for solving it twice:
- `PlanContext` (`file_ops.py:983`) is documented as *"The single struct every plan-id consumer resolves
  against."* It carries `plan_dir` (eager — a pure path join) and the worktree faces `worktree_state`,
  `worktree_path`, `has_worktree`, `worktree_branch` (**lazy**, because resolving them shells out to
  `manage-status get-worktree-path`; the laziness is load-bearing and must not be defeated by an eager
  read in this channel).
- `resolve_live_worktree` (`_references_core.py:177`) exists precisely because footprint consumers
  *"previously reconstructed it by reading `status.metadata.worktree_path` out of the plan's own
  `status.json` — a hand-rolled re-derivation of the worktree face that `file_ops.resolve_plan_context`
  now owns."* **A hand-rolled resolution in this channel would be the third instance of that archetype.**
- Gate on **`has_worktree`**, never on the truthiness of `worktree_path`: the resolver falls back to the
  **main checkout** for a plan that is not worktree-bound, so a path test silently answers "main
  checkout" where the caller asked "is a worktree materialized". All four states must be handled and
  named: `materialized`, `pending` (worktree not yet created by phase-5-execute), `disabled`, and the
  `NO_PLAN` sentinel (whose worktree face is ALWAYS the main checkout).

**(d) ⛔ The EPIC side resolves MAIN-ANCHORED, explicitly — never by cwd walk-up luck.** A plan runs in
`.plan/local/worktrees/{plan_id}`, which carries no `.plan/local` of its own, so
`_find_plan_root_from_cwd()` walks up and lands on the main checkout *by accident of nesting*. That
accident makes the mailbox reachable today and **is not a contract**: a worktree placed anywhere outside
the main repo's `.plan/local/` resolves elsewhere and the plan silently reads an empty mailbox. Resolve
the epic store through the main-anchored family (`get_store_dir('orchestrator', slug)` /
`resolve_main_anchored_path`) so reachability is guaranteed by construction rather than by layout.
⭐ This is the same resolver-residency trap that produced the L8 / D-074-b misdiagnosis in this epic —
the mechanism is understood, so reproducing it here would be unforced.

**(e) ⛔ THE TEST THAT ACTUALLY BITES: resolve from BOTH cwds.** A resolution suite written from the main
checkout passes completely while being wrong exactly where it matters, because the failing caller is a
plan running **inside its worktree**. Required matched pair: the same `(epic_slug, plan_id)` address
resolves to the same epic mailbox and the same plan faces (i) with cwd at the main checkout and (ii) with
cwd inside a materialized worktree. **Publish which cwds the suite actually exercised** — a suite that
silently ran both cases from one directory is the vacuous-guard archetype wearing a second coat.

**(f) Errors are envelope-shaped and non-fatal.** Unknown plan, unknown epic, unsafe identifier, and
absent mailbox each return a distinct, named outcome — never an exception that could fail a running plan
(D2's fail-open rule governs the read path, and this API is how it is expressed).

## Claim Labels

Every claim this spec serializes, labelled per the epic's verify-first contract. The OBSERVED claims were
checked first-party at HEAD `e8324d241` on 2026-08-23; re-ground them at the plan's own HEAD before
relying on any one of them.

- **OBSERVED** — `inbox write --target-plan` refuses a message aimed at a `running` plan with
  `undeliverable_to_running_plan` (`_orchestrator_inbox.py:1098-1101`).
  - verdict: corroborated | checked_at: 66320e70d | by: truthful-signals/cleanup | rescoped: n/a | evidence: _orchestrator_inbox.py still refuses a running-plan target with undeliverable_to_running_plan, now at L1150-1159 (line drift from 1098-1101); mechanism unchanged
- **OBSERVED** — `inbox-envelope.md:62` states the refusal *"deliberately does NOT build a mid-run
  delivery channel — routing a message into a running plan is a larger design question this channel does
  not answer."* ⇒ this plan answers that deferred question; it is not fixing an oversight.
  - verdict: corroborated | checked_at: 66320e70d | by: truthful-signals/cleanup | rescoped: n/a | evidence: inbox-envelope.md still states the guard deliberately does NOT build a mid-run delivery channel, verbatim
- **OBSERVED** — **no plan-side reader exists.** Every non-orchestrator skill referencing the inbox
  (`phase-6-finalize` ×5, `manage-execution-manifest`, `plan-retrospective`, `manage-lessons` ×3,
  `extension-api`) is on the WRITE side. Enumerated across `marketplace/bundles/plan-marshall/skills/`,
  so this is a complete population, not a sample.
  - verdict: unverifiable | checked_at: 66320e70d | by: truthful-signals/cleanup | rescoped: n/a | evidence: Population claim (no plan-side reader tree-wide) not independently re-swept this pass
- **OBSERVED** — `orchestration-model.md` § Ledger Write-Boundary states the one-way rule and *"The plan
  never reads the ledger to make a decision."* D0(3) amends exactly this sentence.
  - verdict: corroborated | checked_at: 66320e70d | by: truthful-signals/cleanup | rescoped: n/a | evidence: orchestration-model.md still states the One-way bullet and never-reads-the-ledger clause, unchanged at HEAD
- **OBSERVED** — the orchestrator's write carve-out is bounded to `.plan/local/orchestrator/{slug}/**`
  and names `.plan/local/plans/` as out of bounds ⇒ the mailbox cannot live in the plan directory.
  - verdict: corroborated | checked_at: 66320e70d | by: truthful-signals/cleanup | rescoped: n/a | evidence: orchestration-model.md still states a Write outside the epic own slug tree including .plan/local/plans/ is out of bounds
- **OBSERVED** — `assert-step-recorded` is documented as called after every dispatched step returns and
  performs zero writes (`manage-status/SKILL.md:516`) ⇒ D3(b)'s call-site precedent exists and is shipped.
  - verdict: corroborated | checked_at: 66320e70d | by: truthful-signals/cleanup | rescoped: n/a | evidence: manage-status/SKILL.md:516 still documents assert-step-recorded as read-only zero writes called after every dispatched step
- **OBSERVED** — `file_ops.PlanContext` (`file_ops.py:983`) is documented as *"The single struct every
  plan-id consumer resolves against"*, carrying `plan_dir` eagerly and `worktree_state` /
  `worktree_path` / `has_worktree` / `worktree_branch` LAZILY, the laziness deliberate because the
  worktree face shells out to `manage-status get-worktree-path`. ⇒ D6(c) reuses it; it does not rebuild it.
  - verdict: corroborated | checked_at: 66320e70d | by: truthful-signals/cleanup | rescoped: n/a | evidence: file_ops.py PlanContext docstring confirmed at L986 (spec cites 983, a 3-line drift it already noted); text matches
- **OBSERVED** — `resolve_live_worktree` (`_references_core.py:177`) records that consumers *"previously
  reconstructed [the worktree face] by reading `status.metadata.worktree_path` out of the plan's own
  `status.json` — a hand-rolled re-derivation … that `file_ops.resolve_plan_context` now owns."* ⇒ the
  hand-rolled-resolver archetype is real, already cost this repository once, and D6(c) forbids a third.
  - verdict: corroborated | checked_at: 66320e70d | by: truthful-signals/cleanup | rescoped: n/a | evidence: _references_core.py resolve_live_worktree at L179 (spec cites 177, 2-line drift already noted); hand-rolled re-derivation text confirmed
- **OBSERVED** — the resolver's `worktree_path` **falls back to the main checkout** for a non-worktree-bound
  plan, which is why `has_worktree` is the documented gate rather than a truthiness test on the path.
  - verdict: corroborated | checked_at: 66320e70d | by: truthful-signals/cleanup | rescoped: n/a | evidence: file_ops.py has_worktree docstring confirms worktree_path always falls back to the main checkout and has_worktree is the gate
- **OBSERVED** — `_find_plan_root_from_cwd()` returns the FIRST ancestor containing `.plan/local`, and a
  worktree under `.plan/local/worktrees/{id}` carries none of its own ⇒ cwd walk-up from a worktree lands
  on the main checkout **by accident of nesting**. Established first-party during this epic's L8 / D-074-b
  adjudication. ⇒ D6(d) requires explicit main-anchored resolution instead of relying on it.
  - verdict: corroborated | checked_at: 66320e70d | by: truthful-signals/cleanup | rescoped: n/a | evidence: marketplace_paths.py _find_plan_root_from_cwd returns the FIRST ancestor whose .plan/local exists, exact match
- **HYPOTHESIS** — that ONE symmetric API with direction as a parameter is better than retaining two
  surfaces. D6(a) requires the choice to be RECORDED either way; it does not presuppose the outcome.
  - verdict: unverifiable | checked_at: 66320e70d | by: truthful-signals/cleanup | rescoped: n/a | evidence: HYPOTHESIS on one symmetric API vs two surfaces; a design choice D6(a) leaves open
- **HYPOTHESIS** — that `outbox-to-plan/` as a sibling directory is the right residency. D0(1) may settle
  otherwise; the constraint that binds is the write carve-out, not this directory name.
  - verdict: unverifiable | checked_at: 66320e70d | by: truthful-signals/cleanup | rescoped: n/a | evidence: HYPOTHESIS on outbox-to-plan/ residency; D0(1) may settle otherwise per the spec own text
- **HYPOTHESIS** — that `advisory` alone is a sufficient first effect vocabulary. D0(2) may justify a
  second kind; it may not assume one.
  - verdict: unverifiable | checked_at: 66320e70d | by: truthful-signals/cleanup | rescoped: n/a | evidence: HYPOTHESIS that advisory alone suffices; D0(2) leaves it open
- **HYPOTHESIS** — that phase transition and sub-agent return are together sufficient coverage. They are
  the operator's stated floor (*"at least"*), not a proven-complete set. If D5's population-derived roster
  surfaces a third site class where a plan runs unattended for long stretches, report it rather than
  silently widening or silently ignoring it.
  - verdict: unverifiable | checked_at: 66320e70d | by: truthful-signals/cleanup | rescoped: n/a | evidence: HYPOTHESIS that phase-transition plus sub-agent-return are sufficient coverage; the spec calls this an unproven floor

## Expected Surface

- `marketplace/bundles/plan-marshall/skills/persona-plan-orchestrator/standards/orchestration-model.md`
- `marketplace/bundles/plan-marshall/skills/plan-orchestrator/standards/inbox-envelope.md`
- `marketplace/bundles/plan-marshall/skills/plan-orchestrator/scripts/_orchestrator_inbox.py`
- `marketplace/bundles/plan-marshall/skills/plan-orchestrator/scripts/orchestrator.py`
- `marketplace/bundles/plan-marshall/skills/plan-orchestrator/SKILL.md`
- `marketplace/bundles/plan-marshall/skills/manage-status/scripts/manage-status.py`
- `marketplace/bundles/plan-marshall/skills/manage-status/SKILL.md`
- `marketplace/bundles/plan-marshall/skills/plan-marshall/workflow/planning.md`
- `test/plan-marshall/plan-orchestrator/test_inbox_delivery.py`
- `test/_shared/_dispatch_roster.py`

- `marketplace/bundles/plan-marshall/skills/plan-orchestrator/workflow/analyze.md` *(added 2026-09-03, drain fold of `dual-homed-hook-install-renders-identically-014` — the drain’s own undocumented payload read)*

## Dependencies and Sequencing

⛔⛔ **THIS SECTION IS MACHINE-DERIVED (`corpus cross-check`, 2026-08-23, over 148 specs / 7 sibling epics
/ 7 live plans). An earlier hand-written version of it was WRONG in both directions and was replaced.**
The epic has recorded this exact failure before: a hand-derived collision map missed five pairs and
asserted two that path-overlap did not confirm. Do not re-derive this list by reading specs.

**⛔ NOT EMITTABLE — collides with THREE currently-LAUNCHED plans:**

| Launched plan | Files | Overlapping surface |
|---|---|---|
| `-096` orchestrator-inbox-and-landing-residue | **4** | `orchestration-model.md`; `_orchestrator_inbox.py`; `orchestrator.py`; `inbox-envelope.md` |
| `-095` finalize-step-contract-guard-residue | **2** | `manage-status/SKILL.md`; `manage-status/scripts/manage-status.py` |
| `-094` plugin-doctor-detector-coverage-residue | **1** | `test/_shared/_dispatch_roster.py` |

⇒ **This plan waits on all three.** `-096` is the deep one — it is actively editing the four inbox files
this plan must extend, so starting before it lands would put two plans in the same channel code at once.
⚠ The `-095` collision was NOT predicted by hand and was found only by the machine check: the live plan's
`references.json` shows it already touching `manage-status.py`, which is exactly where D3(a)'s
phase-transition poll goes.

**Staged-spec collisions — sequence, do not pair:**

| Spec | Files | Overlapping surface |
|---|---|---|
| `-099` the-ledger-has-no-safe-single-row-append | **3** | `orchestration-model.md`; `plan-orchestrator/SKILL.md`; `orchestrator.py` |
| `-089` planning-lane-change-type-scope-and-execution-manifest | **2** | `manage-status/SKILL.md`; `manage-status.py` |
| `-090`, `-097`, `-025` | 1 each | `plan-marshall/workflow/planning.md` |
| `-002` | 1 | `test/_shared/_dispatch_roster.py` |

**⛔⛔ CROSS-EPIC — CHECKED 2026-08-23, AND IT IS A CONTRACT CONFLICT, NOT A FILE COLLISION.**

`code-intelligence-substrate/PLAN-CIS-052-finalize-dispatch-and-blocking-boundary-observability`
(**`staged`**; CIS is under a standing 2026-08-09 operator hold, R=0/N=2, and CIS-052 is their
*recommended first pair* — so it may be emitted the moment that hold lifts).

**Subject is NOT duplicated.** CIS-052's six deliverables are finalize dispatch observability and
blocking-boundary audibility (one emitter per dispatch, `manage-status` write-path records, audible
completion refusal, rebase-seam executor refresh, `pre-submission-self-review` document order, and
six can-not-fire guards). None of them is a delivery channel. ⇒ **Neither plan should be retired in
favour of the other, and neither should absorb the other's deliverable.**

**But two of its D6 sub-items act on THE EXACT GUARD THIS PLAN RE-SCOPES, in the OPPOSITE DIRECTION:**

| | CIS-052 | This plan (`-100`) |
|---|---|---|
| `_orchestrator_inbox.py` | **D6e** — keep the running-plan refusal; make its FAIL-OPEN visible by emitting `target_plan_check: indeterminate` when `--target-plan` was supplied and the status document was unreadable | **D1** — RE-SCOPE the refusal so a running-plan target is DELIVERED rather than refused |
| `inbox-envelope.md` | **D6d** — add a sentence to **§ Write-side deliverability** naming `lessons-capture` as the site that owes `--target-plan`, on the premise that *"the inbox deliverability guard refuses a write aimed at a running plan"* | **D1** — REWRITE **that same section**, because its deliverability table "currently states the opposite outcome" |
| `manage-status/SKILL.md` | D2a/D2b (`mark-step-done` recording) | D3(a)/D6 (phase-transition poll) — ordinary file collision, different subject |

⭐ **CIS-052's premise is that the guard is UNDER-reached** — `--target-plan` is `required=False,
default=None` with no caller, so the refusal never fires and D6d makes callers supply it. **This plan's
premise is that the refusal is the BLOCKER.** Both readings of the code are correct today; they simply
want opposite futures for it.

**⇒ ORDERING CONSTRAINT — `-100` lands AFTER CIS-052, and D0 owes it a re-grounding.**
1. CIS-052's edit on this surface is SMALL (one obligation sentence, one advisory TOON field) while
   `-100` rewrites the section and the guard's semantics. Landing the small one first is cheaper than
   rebasing it onto changed semantics.
2. `-100` is blocked behind three LAUNCHED plans anyway, so this costs no wall-clock.
3. ⛔ **D0 MUST re-ground CIS-052's D6d/D6e at HEAD before D1 touches the guard.** If CIS-052 has landed,
   D1 supersedes its envelope sentence and MUST say so in the same edit rather than silently deleting a
   sibling's shipped contract line. If it has NOT landed, `-100` must not pre-empt it — **notify, do not
   absorb: an offer is not a transfer, and D6d stays CIS's deliverable.**
4. ⚠ D6e's *concern* survives this plan's change and its *expression* does not: "I could not tell whether
   the target is running" still matters when the answer selects DELIVERY versus drain-queueing. Preserve
   the indeterminate signal; do not discard it as obsolete.

✅ **CIS has been notified** — finding filed to their inbox 2026-08-23 (`truthful-signals-044.md`), naming
the conflict and the ordering. Their ledger cannot see this collision on its own.

**Lower-severity sibling overlaps (1 file each, no contract interaction):**
`code-intelligence-substrate/PLAN-CIS-045`, `PLAN-CIS-058`, `review-apparatus/PLAN-PR-024`
(`test/_shared/_dispatch_roster.py`, the shared roster helper D5 reuses);
`review-apparatus/PLAN-PR-028` (`_orchestrator_inbox.py`).

**Adjacent to:** `-088` (measurement / ledger family) — this plan shares its *theme* (absence must be
representable, D4) but touches none of its files.
⛔ **`tools-file-ops/scripts/file_ops.py` is REUSED, NOT EDITED, and that is a sequencing constraint, not
a style preference.** D6(c) consumes `resolve_plan_context` as it stands; the file is deliberately ABSENT
from the Expected Surface above so this plan stays disjoint from it. **`-088` holds `file_ops.py` in its
own surface.** If implementation shows the resolver genuinely must change to serve this channel, that is a
NEW `-100 ↔ -088` collision: **report it and serialize — do not absorb `-088`'s file silently.** The same
applies to `_references_core.py`, which is read for precedent only.

⚠ **Re-derive every row above at emit time against `-094`/`-095`/`-096`'s LANDED diffs, not against their
specs.** This epic has `affected_files` under-recording recorded as a live defect (19-vs-37), so a
launched plan's real surface can be wider than either its spec or its `references.json` shows.

⚠ **Provenance of this spec's own queue row.** It was added by the whole-array
`manage-status update-field --field plans` rewrite, because **D-074-d** — no safe single-row append —
is still open. `PLAN-TRUTH-099` is the fix. The array was rebuilt programmatically from the live
`status.json` rather than retyped; the row count was asserted before and after (145 → 146), key order was
asserted against an existing row, and `corpus enumerate` confirmed `rows_without_spec: 0` afterwards.

## Hand-Off Command

```text
/plan-marshall task="implement .plan/local/orchestrator/truthful-signals/plans/PLAN-TRUTH-100-the-inbox-has-no-delivery-path-to-a-running-plan.md"
```

## ⭐⭐ FOLDED 2026-08-27 — a THIRD undeliverable state, and it arrived by demonstrating itself

This plan's subject is the missing **orchestrator → running plan** direction. Two further instances
landed on 2026-08-26/27, and both are the same shape: **a channel whose lifecycle is shorter than the
lifetime of the findings it must carry.**

**(a) Post-closure sender — self-demonstrating.** `lessons-handling-26-08-26-01` filed a valid
`lifecycle=stream-end` marker for itself at drain completion
(`truthful-signals/inbox/lessons-handling-26-08-26-01-014.md`, verified present and `valid: true`).
A LATER `cleanup` pass over the same epic then produced new findings — and `inbox write` correctly
refuses that sender with `stream_closed`. ⇒ **The findings had no route to their owning epic and
arrived as an operator paste.** ⭐ The reporter explicitly DECLINED the available workaround — minting a
fresh sender id, which `stream_closed`'s per-sender scope would have accepted — on the grounds that it
launders past a closure they filed truthfully. **That judgement is correct and is the reason this is a
design gap rather than an operator-error story.**

**Directive candidate (theirs, endorsed):** scope `close-stream` to a **drain** rather than to a sender
**for all time**, or add an explicit post-closure channel. ⛔ Do NOT fix it by making `stream_closed`
advisory — the refusal is what gives the marker meaning; the defect is the marker's unbounded scope.

**(b) Running-plan finding with no ledger route (D-114-g).** A `worktree-remove` defect was found
minutes AFTER `PLAN-TRUTH-114` was transitioned to `running`. The running-row exclusion forbade
re-scoping the spec, and `inbox write --target-plan` is refused by the running-plan guard ⇒ operator
paste again. ⭐⭐ **The generalisation the epic kept: a CONFIRMED start and an OBSERVED start are not the
same instant, and the gap between them is exactly where a finding becomes undeliverable.** The paste in
fact landed at `1-init`, on main, before the worktree existed — so the brief was still open and the
ledger was the only thing that had closed.

⇒ **Three undeliverable states now, not one:** to a running plan (this plan's original subject), from a
closed sender, and in the confirmed-but-not-yet-observed start window. **D0 should enumerate the
channel's lifecycle boundaries rather than fix the three instances**; a per-instance fix will leave the
fourth.

## Write-Boundary

The plan implementing this spec touches only its own repository source and tests. It creates and edits
NO file under `.plan/local/orchestrator/` other than its own `inbox/{sender}-{seq}` message — the
orchestrator owns every other ledger write — and reports its outcome through its PR and its inbox
message. The inbox exception's qualifiers and the sole sanctioned write mechanism are stated in
`persona-plan-orchestrator/standards/orchestration-model.md` § Ledger Write-Boundary.

⚠ **A pointed note for this plan in particular:** it is building the very channel it must not abuse.
Implementing a plan-side reader does NOT license this plan to read the epic ledger during its own run,
and the mailbox it creates is written by the ORCHESTRATOR, never by the plan. Keep the two directions
and the two write-boundaries distinct in the code as well as in the prose.

---

## ⭐ THE INVERSE DIRECTION IS ALSO MISSING, AND IT IS THE ONE COSTING VISIBILITY TODAY (2026-08-24)

This plan builds **orchestrator → running plan**. The operator's 2026-08-24 question exposed that
**plan → orchestrator, mid-run, is equally absent** — and it is the direction currently doing damage.

**Measured:** a plan's findings ledger flushes nothing until `emit-landing` at **order 1000**, the last
step. Across four running plans there are **178 findings, 26 pending**, none of which has reached this
epic — including one titled *"OPERATOR DECISION OWED: the zero-skip gate is inert — arm it or delete
it"*. ⛔ **A finding addressed to the operator, invisible to the operator, for the life of the plan.**

⇒ **Fold the inverse direction into this plan's D0 scope question**, or record explicitly that it is
out of scope and name its owner. ⭐ **The mailbox residency argument already made here applies
unchanged**: the orchestrator may not write into `.plan/local/plans/`, so the channel lives in the epic
tree — and a plan writing *outbound* mid-run is the direction that residency already permits, since
`inbox write` is exactly that call made at order 1000. **The mechanism exists; only its timing is
fixed.**

⚠ **Related, not duplicate:** `PLAN-TRUTH-109` fixes the orchestrator's *pull* (a findings read against
an absent store returns a clean zero) and `PLAN-TRUTH-110` owns transport-and-audit at landing. **This
is the mid-run push.** All three are needed; none subsumes another.

## ⛔⛔ OBSERVED FIRST-PARTY 2026-08-27 — the drain DESTROYS the closure signal it consumes

Found by performing the drain this plan is about, not by reasoning about it.

Before the drain, `inbox list` reported:

```text
count: 14   live_count: 13   invalid_count: 0
closed_senders[1]:
  - lessons-handling-26-08-26-01
```

After archiving all 14 (including the `stream-end` marker, which archives on consume like any other
message):

```text
count: 0   live_count: 0   invalid_count: 0
closed_senders[0]:
```

⛔ **Two consequences, both undesigned.**

**(1) The three-zeros table now reports the WRONG zero.** `live_count: 0` + empty `closed_senders` +
`invalid_count: 0` is defined as **EMPTY** — *"no sender has declared closure, so a later message is
still possible"*. But a sender **did** declare closure; its declaration was simply consumed. ⇒ **The
FINISHED state is not durable — it survives only until the drain that reads it.** The one state the
table exists to distinguish is the one that erases itself.

**(2) The closure stops binding the sender.** `inbox write`'s `stream_closed` refusal **scans `inbox/`
only** — documented behaviour — so an archived marker no longer closes the stream. ⇒ **Every drain
silently re-opens every sender it closed.** ⭐ **Ironically this resolves the very dilemma that produced
the operator paste**: `lessons-handling-26-08-26-01` may now write again without laundering past its own
closure. **That is an artifact of archival, not an affordance anyone designed**, and it must not be
relied on.

⇒ **D0 should treat closure as ledger state rather than as a queued message.** A declaration whose
lifetime is the lifetime of the message carrying it cannot outlive its own consumption — which is the
same lifecycle-mismatch this plan already carries three instances of, now with a fourth that is
structural rather than situational.

⚠ **Do not "fix" this by leaving `stream-end` markers un-archived.** That trades a vanishing signal for
a queue that never drains clean, and `inbox list`'s `count` would then never reach zero — breaking the
completed-drain check instead.

## ⭐ FOLDED 2026-09-03 — inbox drain (1 message(s))

- **`dual-homed-hook-install-renders-identically-014.md`** — *no read surface names WHAT a queued inbox message is about, so a candidate-lesson emitter structurally cannot dedup against the queue.*

  ⭐⭐ **Observed first-hand by a leaf executing its OWN dedup obligation, which is what makes it evidence rather than a suggestion.** Branch B4 of `lessons-capture` requires the emitting plan to route only genuinely uncovered material into the epic inbox. **Nothing in the read surface makes that checkable.** Both read verbs return envelope metadata only — `inbox list` → `name, sender_id, kind, created, lifecycle, revision, superseded_by, valid, error`; `inbox validate` → the same header fields plus `location` / `archive_path` — and **there is no body-read verb at all** (`landing-check` reads a payload but only for `kind: landing`, and returns fact keys, not content).

  The queue held **24 live messages** when that step ran, **8 of them written by the same sender minutes earlier**. Enumerating them yields 24 rows differing only in filename and timestamp. ⛔ **A dispatched leaf is additionally bound by the scripts-only rule for `.plan/` access, so it cannot fall back to opening the files.**

  ⭐ **How the gap was worked around is the tell:** the dispatching orchestrator **hand-enumerated the already-covered material into the prompt body** — seven lesson ids with one-line summaries plus a prose list of what remained uncovered. *“That works, and it is exactly the shape of a missing surface: the information existed, but only in the caller’s head, transmitted as narrative. Had the orchestrator’s summary been incomplete or stale, the duplicate would have been written with every verb returning `status: success`.”*

  ⭐⭐ **One level below the known rule.** *“A ledger cannot see a duplicate in another ledger”* — here the duplicate is in **the same ledger, in the same sender’s own stream**, and it is still invisible.

  **Three asks, ordered by cost:** (1) **give `inbox list` a `subject` column** — have `inbox write` capture the payload’s first `#` heading into an envelope header and surface it; *“titles are what dedup actually needs; full bodies are not”*. (2) **consider `inbox read --message NAME`** returning the body, so the drain and any leaf share one sanctioned read path — ⛔ **today the orchestrator’s own drain reads payloads with NO documented script surface**; the direct read is implied by `analyze.md`’s inbox-scan mode rather than provided, which is why this fold widens the Expected Surface to include `analyze.md`. (3) **then make the obligation checkable at the emitter**; until then the prompt-body hand-off should be documented as the required mechanism rather than left implicit — *“an unstated requirement with no surface is met by luck”*.

  ⚠ **Scope honestly, in the sender’s own words:** *“this was found by one leaf executing one dedup obligation. Before staging, check whether other queue consumers — the `analyze` drain’s own Open-Defect dedup at items 3 / 4a / 5b, which the doc says must ‘fold into that entry’ — face the same blindness.”* ⭐ **This drain confirms they do**: its own recurrence checks were performed by reading payload files directly, exactly the unsanctioned path ask (2) would replace.

---

## Superseded By

⛔ **This spec is SUPERSEDED by `PLAN-TRUTH-143-the-orchestrator-inbox-has-no-delivery-path-and-its-corpus-instruments-publish-an-unmeasured-zero.md` (PLAN-TRUTH-143)**, recorded 2026-09-12 under the operator directive to group plans by shared target at a ceiling of 12 deliverables. It is retained in full as the audit record of why it was retired and as the authority its successor's `## Claim Labels` section POINTS at — the successor deliberately does not restate these claims, so **this document is where they are re-derived from**. Do not implement from this spec; implement from its successor.
