# Epic: Orchestrator Substrate Refactor

slug: orchestrator-refactor

> Ledger document for one epic under `.plan/orchestrator/{slug}/`. The layout and
> authority contract live in the central standard — see
> `persona-plan-orchestrator/standards/orchestration-model.md`. `status.json` is the
> machine authority; any statement here that conflicts with it is stale prose.

## Vision

The orchestrator refactors its own substrate. Four bound changes: (1) relocate the
persisted ledger from the machine-local `.plan/local/orchestrator/{slug}/` tree to a
SHARED `.plan/orchestrator/{slug}/` tree (git-tracked, cross-machine), decomposing the
current large monolithic files (`status.json`, `epic.md`) into smaller self-contained
per-concern files so two machines can work the same epic in parallel without file-level
collisions; (2) design and land a self-terminating migration mechanism — old-path reads
auto-migrate to the new layout, and a dated/versioned removal task retires the
compatibility shim after a bounded window, generalized so future layout migrations reuse
the same mechanism rather than each inventing its own; (3) rename the `slug` vocabulary
to `name` across the orchestrator's call surface (CLI flags, `status.json` fields, doc
prose), and unify plan-marshall's own top-level `--plan` / `plan_id` naming onto the same
`name` vocabulary, surveying other top-level commands for the same drift; (4) survey
every sibling orchestrator epic (active and archived) for deliverables that are actually
orchestrator-tooling work (not domain work routed through an epic) and fold those into
this epic's workstreams rather than leaving orchestrator-improvement work scattered
across unrelated epics; (5, added 2026-09-23, operator-proposed) confine an epic's own
`.plan/orchestrator/{slug}/` reads/writes to a FIXED-NAME, long-lived, never-removed
per-epic git worktree instead of the primary checkout, and replace today's ad hoc
`git commit`/`git push` with explicit, monitored `land` (this epic) and `land-all` (every
active epic) verbs — landing via branch/PR/CI-wait/merge/pull-both — because frequent
unrelated orchestrator ledger commits landing directly on `main` interfere with
plan-marshall runs that inspect `main`'s state at various lifecycle phases. Done = the
ledger lives at the shared path with no monolithic file, a proven and time-boxed
migration/removal path exists as a reusable pattern, the call surface says `name`
everywhere `slug` used to, no sibling epic still carries an orchestrator-substrate
deliverable this epic did not absorb or explicitly decline, and an epic opted into
`orchestrator.use_worktree` lands its ledger changes through `land`/`land-all` rather than
ad hoc commits directly against `main`.

> **Aspect 1 (address) landed 2026-09-21** via PLAN-01 — the epic's own ledger now lives
> here, at `.plan/orchestrator/orchestrator-refactor/`. **Aspect 3's literal framing was
> corrected by PLAN-04/ADR-023**: the settled spelling is `--epic`, not `--name` — see
> Decisions below. **Aspect 5 staged 2026-09-23** as WS-05 (PLAN-09/PLAN-10) — not yet
> half shipped: PLAN-09 landed the shared ledger worktree, and **`orchestrator.use_worktree` was turned ON
> 2026-10-01** (repository-wide, #1666). Every epic's ledger writes now go to the shared worktree
> (`.plan/local/worktrees/_orchestrator`, branch `chore/orchestrator-ledger`), not to `main`. **Aspect 5 shipped
> 2026-10-03**: PLAN-10 landed the `land` verb (#1690), so that branch is landed by `orchestrator land` rather
> than by hand once the harness installs are synced.

## Queue annotations

{Per-row narrative the generated `queue-view.md` cannot derive — keyed by plan id. The row's
status, workstream, and surface are in `queue-view.md`; this zone carries only what it
cannot express.}

- PLAN-10 — **SHIPPED 2026-10-03** (#1690, squash `7a0af07c5`; landing `landings/PLAN-10.md`). All six spec
  deliverables plus one operator-accepted unplanned one (`worktree_setup_commands`). Realized surface 43 against
  14 declared (21 undeclared, 1 declared-untouched). WS-05 is complete; no staged row remains in this epic.
- PLAN-09 / PLAN-10 / PLAN-11 (2026-09-26, historical: PLAN-09 and PLAN-11 have since SHIPPED, so
  PLAN-10 is the only staged row) — the rows re-staged after the PM-MCP park. All three share
  `orchestrator.py` and `test/plan-marshall/plan-orchestrator/**`, so they run one at a time, never paired.
  PLAN-10 strictly follows PLAN-09. Queue order puts PLAN-09 first; PLAN-11 is the smallest and may go first by
  operator choice.
- PLAN-09 — **SHIPPED 2026-09-28** (#1652, squash `438a0a71f`; landing `landings/PLAN-09.md`). The shared
  `_orchestrator` worktree and `orchestrator.use_worktree` it delivered were switched ON by the operator on
  2026-10-01 — see Decisions.
- PLAN-10 — now emittable (PLAN-09 landed). 6 deliverables after the D6 fold from the PLAN-09 landing (ledger-branch
  check before commit; dedicated reserved-key refusal on `worktree-remove`). Kept unsplit at the ~6 threshold:
  D6 is two small guards on `land`'s own code path, and splitting them off would ship `land` without them.
  Shares `orchestrator.py` with PLAN-11 — one at a time.
- PLAN-01 — **SHIPPED 2026-09-21** (#1557/#1558/#1561; #1555 closed unmerged, split
  executed). See `landings/PLAN-01.md`. Landed WITHOUT a redirect — see the new Open Defect
  on `_orchestrator_inbox.py`'s path-prefix gap, folded into PLAN-03.
- PLAN-02 — **SHIPPED 2026-09-24** (#1609, merge `21578e447`, verified as an ancestor of
  `origin/main`). See `landings/PLAN-02.md`. All 9 deliverables done — the per-concern
  ledger layout, `migrate-layout`, `regenerate-view`, and the row-vocabulary prose
  reconciliation. Emitted 2026-09-23 on direct operator override ahead of `next`-slot rigor
  (the marketplace-wide disjointness gate was, and remains, indeterminate) — that caveat is
  now moot, the plan shipped clean. Self-review did not converge (4 rounds, last 6 fixes
  never self-reviewed) but full verify/CI/CodeRabbit covered them. Surfaced a major
  follow-up: 24 sibling epics still carry the legacy ledger layout and are now unreadable
  by every orchestrator verb — new Open Defect below, operator decision needed on the
  cross-epic sweep.
- PLAN-03 — **PARKED 2026-09-26** (PM-MCP park, see Open Defects — do NOT emit; un-park only by operator
  decision). Dependency satisfied (PLAN-01 shipped); before the park it was emittable subject to
  disjointness/prep-ready checks. ⚠ **Landed without a redirect** — D6 is now a retrofit; its
  most urgent sub-target (`_orchestrator_inbox.py`'s `_SOURCE_ID_RE` path-prefix gap) is
  ACTIVELY breaking orchestration routing right now, not merely a theorised risk — see Claim
  Labels. Overlaps PLAN-04 on `plugin-doctor/references/rule-catalog.md` — not caught by the
  automated matcher; sequence, do not parallelize. Disjoint from PLAN-02 and PLAN-06 — the
  one clean pair in this corpus.
- PLAN-04 — no hard dependency; decision-only. Overlaps PLAN-05 (`argument-naming.md`, PLAN-05
  depends on PLAN-04's decision) and PLAN-03 (`rule-catalog.md`, see above).
- PLAN-05 — **PARKED 2026-09-26** (PM-MCP park, see Open Defects — do NOT emit). PLAN-04 dependency
  satisfied (shipped #1543, folded with its execution brief 2026-09-20); PLAN-02 dependency satisfied
  too (shipped #1609). Also overlaps PLAN-06 and PLAN-07. **New at `next`-time
  2026-09-20**: collides with a DIFFERENT currently-running live plan
  (`retrospective-aspects-publish-verdict`) on `platform-runtime/standards/contract.md` —
  re-check this plan's own state before PLAN-05 is ever emitted.
- PLAN-06 — **PARKED again 2026-09-26** (PM-MCP park, see Open Defects — do NOT emit). Earlier:
  unblocked and re-staged 2026-09-21 (`cleanup`): PLAN-TRUTH-143 landed as
  PR #1539. Re-grounding found D2/D3 already closed at HEAD (PR #1366, with a corrected
  attribution — the spec's own guess of PR #1370 for the second gate was wrong) and dropped
  them; D5 confirmed still live today (PLAN-04's own row still carries no delivered `kind:
  landing` message) but narrowed to enforcing an existing, already-documented contract rather
  than building new machinery. D1's ownership statement now routes around `truthful-signals`
  PLAN-TRUTH-144, which is `running` as of this pass. No hard dependency; independent of
  PLAN-01's finalize block.
- PLAN-07 — **parked by design**, lowest confidence in the corpus, no external forcing
  function. Depends on PLAN-01/02/05/06/08/09/10 all landing first (all touch
  `orchestrator.py`; PLAN-08 was a behavior FIX to `stale` derivation, PLAN-09/PLAN-10 add
  real new verbs — all three must land before PLAN-07's behavior-PRESERVING split, or the
  split freezes pre-fix/pre-feature state). Operator discretion at `next`-time to keep,
  defer indefinitely, or drop — re-stage to `staged` only once every other plan in this
  epic has shipped, and re-derive its line attribution against the then-current HEAD
  before staging its command.
- PLAN-08 — **SHIPPED 2026-09-22** (#1585, merge `b5d0ef7e6`, verified as `main`'s current
  HEAD). See `landings/PLAN-08.md`. Deliverables D1-D4 shipped-as-specified or better (D2
  exceeds the spec: a full closed 6-member `staleness_basis` vocabulary, not just a named
  fallback). Both of the spec's own re-grounding claims (HYPOTHESIS + Verify-first clause)
  re-grounded and stamped `corroborated` against the merge commit. Landed via merge queue
  under an operator `barrier-ask-override` after CodeRabbit's quota timeout on the final
  loop-back HEAD — see landing record for the review-participation reasoning. Surfaced two
  follow-ups now recorded separately (git-config-injection production hardening — new Open
  Defect below; a mis-triaged review finding — new Watch below) plus 8 promoted lessons.
  Emitted originally on direct operator request ahead of `next`-slot rigor, per its own
  staging note above — that caveat is now moot; the plan shipped clean.
- PLAN-09 — (staging note, historical — SHIPPED 2026-09-28, see above) staged 2026-09-23, WS-05
  foundation. No dependency of its own (net-new
  capability). Overlaps PLAN-02/06 (`orchestrator.py`). PLAN-10 strictly depends on this.
  Carries three verify-at-outline HYPOTHESES: the worktree-verb extension shape, the
  `use_worktree` default, and the terminal-title/session-binding audit — none dictated by
  this staging, all left for outline.
- PLAN-10 — **staged 2026-09-23**, WS-05. Strictly depends on PLAN-09. Overlaps PLAN-07
  (adds real verbs to `orchestrator.py` before PLAN-07's split — PLAN-07 spec updated).
  Carries an open sequencing question for `land-all` (sequential vs bounded-parallel
  against the merge queue) and a HYPOTHESIS on whether `ci pr merge`'s existing sub-verbs
  suffice for D3 — both verify-at-outline, not decided here.
- PLAN-11 — **SHIPPED 2026-10-02** (#1676, squash `8665ddacf`; landing `landings/PLAN-11.md`). Both false
  candidate populations are excluded and named in the payload; the sentinel exclusion was observed live on this
  store after landing. The gate verdict is still `false` — see the Open Defect of 2026-09-22. Ran 2026-10-01 to
  2026-10-02 as plan `cross-check-dated-archive-self-collision`, emitted on operator override.
- PLAN-10 — **sequencing block lifted 2026-10-02**: PLAN-11 has landed, so nothing else in this epic holds
  `orchestrator.py`. **Re-grounded at `8665ddacf` by `cleanup` 2026-10-02** (7 claims: 5 corroborated, 2
  contradicted and already re-scoped; none blocking). D5 was sharpened with the merge-queue ejection case seen
  on PLAN-11 — a dequeued PR stays `open`, so the settle poll alone cannot report it. Still 6 deliverables,
  surface unchanged at 14 entries. The gate still refuses it, so it goes out only on an operator override.
- PLAN-11 — **2026-10-01: folded D4 (exclude the `NO_PLAN` sentinel from the `live_plan` candidates), now 5
  deliverables.** Surface +2 entries (`manage-status/scripts/_cmd_sibling_collision.py`,
  `test/plan-marshall/manage-status/**`), so it now also overlaps parked PLAN-05. Claim 3's verdict corrected
  to `rescoped: yes` — it was the corpus's one blocking row. ⚠ **Cannot be emitted through `next`**: the gate it
  repairs refuses it (comparison indeterminate), so it needs an operator override, as PLAN-02 and PLAN-08 did.
- PLAN-11 — **appeared 2026-09-23 from a concurrent process, not authored this session.**
  Title (`cross-check-dated-archive-self-collision`, WS-04) matches a previously-recorded
  defect: `corpus cross-check` self-colliding against this epic's own archived snapshot as
  a sibling-epic candidate. Plausible on that basis; content not independently reviewed by
  this session — see the spec itself before relying on its Claim Labels.

## Decisions

- 2026-10-05 — **Pre-archive cleanup (operator-directed).** PLAN-03/05/06/07 transitioned `parked` →
  `superseded` (the 2026-09-26 PM-MCP supersession; carry-over already filed in plan-marshall-mcp). Open items routed
  per item by the operator: gate scope, session UX, git-config-injection, PLAN-09 residue (1)(2)(4) and the
  `drain-dedup` defect → `truthful-signals`; `ci checks pull-request-runs` `run_count=0` → `review-apparatus`;
  lesson `2026-09-27-07-001` retirement and the PLAN-09 lesson carry-over → `lessons-routing` (one
  `orchestrator-refactor-001.md` message each). Resolved in place: legacy-layout sweep (all 8 other active epics
  read cleanly), PLAN-11 residue (1)(2), cross-ledger watches (moot). Settled narrative relocated verbatim to
  `settled.md`; a header-less PLAN-05 scope-bloat bullet spliced onto the PLAN-08 drain entry was split back out
  with a reconstructed header. Remaining before `close`: operator runs `/sync-harnesses` (Watches).

- 2026-10-03 — **`cleanup` pass after the PLAN-10 landing.** Corpus: 11 rows and 11 specs, reconciled both
  ways, none running; all 11 surfaces `declarative`; 0 source-origin duplicates. **Applied: nothing** — no spec
  is staged. **Declined, by name:** re-grounding of the 7 shipped specs (terminal) and of parked PLAN-03/05/06/07
  (PM-MCP do-not-emit park; verdicts stay stale on purpose and must be refreshed before any un-park).
  Settled-narrative relocation deferred again, pending operator confirmation; candidates are the shipped-plan
  residue for PLAN-01/02/04/08/09/10/11 in Decisions and Queue annotations. Compaction: view unchanged, both
  invariants ok, 6 relocation pointers reachable. Inbox archive drain refused (no epic-wide quiescence signal).
  Restart verdict `ready` (5 of 6 signals scored; `registry_parity` not available).

> ↪ Relocated to `settled.md` § "Shipped-plan landings, drains and folds (PLAN-01/02/04/05/06/08/10/11, #1685)" — subjects closed: those plans shipped or were superseded

- 2026-10-02 — **`cleanup` pass after the PLAN-11 landing.** Corpus: 11 rows and 11 specs, reconciled both
  ways, none running. Applied: PLAN-10 re-grounded at `8665ddacf` (all 7 verdicts re-stamped, outcomes
  unchanged) and its D5 corrected for the merge-queue ejection case; its PLAN-11 overlap note marked
  discharged. **Declined, by name:** re-grounding of parked PLAN-03/05/06/07 — they are under the PM-MCP
  do-not-emit park, so their verdicts stay stale on purpose and must be refreshed before any un-park — and of
  the six shipped specs, which are terminal. Settled-narrative relocation out of this file was deferred:
  candidates are the 2026-09-20 to 2026-09-24 drain and landing decisions for shipped PLAN-01/02/04/08, and
  they move only on operator confirmation. No duplication (0 source-origin matches). Compaction: view
  unchanged, both invariants ok, 6 relocation pointers reachable. Inbox archive drain refused, as always (no
  epic-wide quiescence signal).

- 2026-10-01 — **`orchestrator.use_worktree` turned ON, on operator instruction; this epic now works in the
  shared ledger worktree.** Order of events: the session's ledger changes landed on `main` first (#1665,
  `0f94c0d8f`), so the cutover check found no uncommitted or unlanded ledger path; `manage-config orchestrator
  set --field use_worktree --value true` then succeeded from the main checkout and its one-line `marshal.json`
  change went out as #1666. First use created the worktree at `.plan/local/worktrees/_orchestrator` on
  `chore/orchestrator-ledger`, branched from `0f94c0d8f`. The knob is repository-wide: every other epic's
  session resolves into the same worktree from its next script call. Consequence to remember: nothing lands
  ledger commits on `main` automatically — until PLAN-10's `land` ships, the ledger branch is landed by hand.
  The running PLAN-11 plan's inbox writes resolve into the worktree as well.

- 2026-09-23 — **New workstream WS-05 (Worktree-Isolated Ledger Landing) staged, PLAN-09 +
  PLAN-10, on operator request.** Operator observed that frequent orchestrator ledger
  commits landing directly on `main` interfere with plan-marshall runs checking `main`'s
  state. Proposed and staged: fixed-name, long-lived, never-removed per-epic worktree
  (PLAN-09) plus `land`/`land-all` verbs replacing ad hoc commit/push with a monitored
  branch/PR/CI-wait/merge/pull-both cycle (PLAN-10). Grounded against a research pass
  confirming: (a) no commit/push mechanism exists today (fully ad hoc); (b) the existing
  plan-worktree lifecycle (`git-workflow.py`) is reusable as a pattern but hard-coupled to
  `--plan-id`; (c) the orchestrator config block is a closed schema needing a real
  extension for `use_worktree`; (d) `phase-6-finalize`'s PR workflow is plan-bound and NOT
  reusable, but the underlying `ci` primitives (`--project-dir` addressing) are generic and
  ARE reusable directly; (e) a bounded, non-foreground CI-wait primitive already exists
  (`ci checks wait`); (f) `corpus epics` is the correct substrate for `land-all`'s sweep.
  Sequenced: PLAN-10 strictly depends on PLAN-09; both must land before PLAN-07 (behavior
  additions before a behavior-preserving split) — PLAN-07's spec updated accordingly.
  Several implementation choices deliberately left as verify-at-outline HYPOTHESES rather
  than dictated here (worktree-verb extension shape, `use_worktree` default,
  `land-all` sequential-vs-parallel) — orchestrating stages the work, not the mechanism.

- 2026-09-19 — parallelization_scope set to 2 (operator choice over the project default
  of 1). Rationale: most staged plans in this epic touch the same shared surface
  (orchestrator.py, the store-path resolver, naming across docs) so true disjoint pairs
  will be rare, but a doc-only or purely-additive plan may run alongside a code plan.
- 2026-09-21 — **`cleanup` re-grounding pass (dispatched, 108 claims across PLAN-02/03/04/
  05/06/07 against HEAD `e8a716501`; PLAN-01 manually excluded — see Open Defects) applied
  material corrections.** PLAN-02's D2 (row-status vocabulary) is largely already delivered
  by PLAN-TRUTH-143 (#1539) — shrinks to doc reconciliation; verdicts stamped on claim-index
  10 (corroborated) and 11 (contradicted, rescoped: yes — population corrected to 509
  rows/13 ledgers). PLAN-06's blocking condition discharged (PLAN-TRUTH-143 shipped); its
  D2/D3 dropped as already-closed at HEAD (PR #1366), with an attribution correction — the
  claim-parsing-gate closure was mis-attributed to PLAN-CIS-051/#1370, actually closed by
  #1366 and #1355; D5 confirmed still live TODAY (not merely historical) but narrowed to
  enforcing an existing, already-documented `source_id` contract rather than building new
  detection machinery; verdicts stamped on claim-index 8 (corroborated), 9 (contradicted,
  rescoped: yes — attribution fix), 10 (contradicted, rescoped: yes — blocker discharged).
  PLAN-06 transitioned `parked` → `staged`. No duplication found beyond an expected
  self-match (PLAN-01's spec ↔ its own launched plan). No ambiguity findings (all 7 specs
  carry Objective/Expected Surface/Claim Labels). No Understated/Unresolvable surface
  corrections needed. Full per-claim corroboration table is the dispatched agent's own
  report, not persisted verbatim here — this entry and the two specs' own edits are the
  durable record.

## Open Defects

> ↪ Relocated to `settled.md` § "2026-09-28 — #1641 reverted this epic's ledger; RESTORED from `88fcfc9ef`" — resolved: all 13 reverted paths restored from `88fcfc9ef` and landed in #1656

### ⛔⛔⛔ 2026-09-26 — THE WHOLE STAGED QUEUE IS PARKED: `plan-marshall-mcp` supersedes it

**Operator decision** (relayed by the `review-apparatus` inbox message `review-apparatus-001.md`, amended rev 1;
drained 2026-09-26 on operator instruction "drain and restructure according to the review-apparatus
message"). `plan-marshall-mcp` (PM-MCP, `/Users/oliver/git/plan-marshall-mcp`) replaces BOTH the process prose
AND the Python scripts of plan-marshall. **Nothing Python- or prose-bound carries**; only
implementation-independent content does. PM-MCP's PM-TEST-1 Ported/Redesigned reading was explicitly withdrawn
by the operator — do not re-derive it.

- **All six staged rows `PLAN-03`, `-05`, `-06`, `-09`, `-10`, `-11` → `parked`**; `PLAN-07` was already
  parked. All seven specs carry a `SUPERSEDED BY PM-MCP` banner; bodies intact as the evidence chain. **Do NOT
  emit; un-park only by explicit operator decision.** No emitted-but-unlaunched command existed to void.
- **Emission exceptions: none.** No spec is foreign-repo config, none is a PM-MIG-2/3 enabler, none fixes a
  defect blocking delivery today. `PLAN-11`'s self-collision is live at `a88626306`, but landing it alone cannot
  flip `candidate_comparison_determinate` (only ~half of the 94 indeterminate sibling candidates are
  self-collisions).
- **Extraction filed in PM-MCP** (the one operator-authorized write, uncommitted there — the operator commits):
  `plan-marshall-mcp/doc/known-defects/orchestrator-refactor-carry-over.md`. Population: 7 specs / 41
  deliverables, 26 carry / 15 none; 78 carry rows (58 spec + 20 `epic.md`): 25 gap, 38 partial, 15 covered;
  mapped at PM-MCP `4e9cca1`, headline contradictions re-read at `7e13ea1`. Eight contradictions, first three
  verified by direct read: (1) PM-MCP commits the epic ledger on the primary checkout
  (`workflow-dsl.adoc:714-718`) against its own PM-ARCH-5 b3 worktree rule; (2) `queue/<PLAN-ID>` vs
  lowercase `plan_id` — the two-vocabulary defect PLAN-05 D6 reproduced; (3) the 10-state queue vocabulary has
  no `parked` / `retired`. Extractors could not content-search PM-MCP, so `gap` = "not found in the files read".
- **Consequence for this epic:** the live queue is empty of emittable work. The epic's remaining purpose is
  historical; closing it (`close` → `archive`) is an operator decision.
- **Same day, operator override: `PLAN-11` re-staged** (`parked` → `staged`) as an explicit operator-confirmed
  exception. Its banner now records the re-staging; its carry-over rows stay in the PM-MCP file.
- **Same day, operator override: `PLAN-09` and `PLAN-10` re-staged AND RE-SCOPED — one fixed worktree for ALL
  epic changes** (operator: "the idea is to create a fixed worktree for all epic changes"), replacing the
  per-epic worktree design. PLAN-09 → 5 deliverables: repository-wide knob, one worktree with a key outside the
  plan-id grammar on a fixed `chore/` branch, never-removed lifecycle, one resolver seam for both store roots
  incl. the plan-side consumers (`inbox write/read/detect`, `phase-1-init`'s spec read — an unlanded spec is
  invisible on `main`), and a cutover guard against stranding dirty ledger files on `main`. PLAN-10 → 5
  deliverables: one `land` for everything pending in the worktree (ledger paths only) under a repository-wide
  lock, epic-native PR title/body, post-enqueue settle loop, a resync that never discards writes made after
  the land snapshot, recoverable failure. The per-epic `land-all` sweep and its merge-queue collision are gone.
  Remaining parked: `PLAN-03`, `-05`, `-06`, `-07`.

> ↪ Relocated to `settled.md` § "Legacy-layout migration sweep across sibling epics" — resolved: all 8 other active epics read cleanly under the per-concern layout (verified 2026-10-05)

- **NEW, discovered 2026-09-22 at `next`-time — the disjointness gate is currently
  MARKETPLACE-WIDE INDETERMINATE, blocking emission for every candidate in this epic
  (and presumptively every epic).** `corpus cross-check` reports
  `candidate_comparison_determinate: false`: 95 of 581 sibling-epic-spec candidates
  across 25 sibling epics, plus 1 `live_plan` entry (`NO_PLAN`), are indeterminate.
  Per the fail-closed rule in `orchestrate.md` Step 4, an indeterminate comparison
  refuses EVERY candidate rather than admitting any on an unexamined population — so
  PLAN-02/03/05/06 all pass prep-readiness (`corpus verdicts blocking_count: 0`) but
  none is emittable. Not this epic's defect to fix (the 95 indeterminate specs belong
  to 25 OTHER epics), but it fully blocks this epic's own `next` progress until either
  those specs gain declarative surfaces or the gate's global-vs-per-candidate scope is
  reconsidered. Not sized or staged — flag for the operator; possibly a
  `truthful-signals` or ecosystem-health item, not orchestrator-refactor's to own.
  **Re-measured 2026-10-01 at `391efbbd6`:** still `false` — `sibling_epic_spec indeterminate: 95` of 611,
  `live_plan indeterminate: 2` of 2 (`NO_PLAN`, `antigravity`). PLAN-11 now removes two of the contributors
  (dated-archive self-collisions, the sentinel). What remains after it lands is honest indeterminacy — sibling
  specs with non-declarative surfaces, and any real live plan with no captured footprint (`antigravity`:
  `1-init`, untouched since 2026-09-17, looks abandoned) — so this repo's gate stays closed until the scope
  question above is decided. A project whose only indeterminate candidate is the sentinel is fully unblocked
  by PLAN-11.
  **Re-measured 2026-10-02 at `8665ddacf`, after PLAN-11 landed:** still `false` — `sibling_epic_spec
  indeterminate: 95` of 611, `live_plan indeterminate: 1` of 2 (`antigravity`; the sentinel is excluded).
  This is now the ONLY thing between this epic and a working `next`, and no staged plan addresses it:
  either the gate's scope changes (an indeterminate candidate blocks only what it could collide with), or 95
  sibling specs in other epics gain declarative surfaces. **Operator decision needed** — if the scope change
  is wanted, it is a new WS-04 spec on `orchestrator.py` and `orchestrate.md`.
  ↪ **TRANSFERRED 2026-10-05** to `truthful-signals` inbox `orchestrator-refactor-001.md` § 1 (operator routing; re-measured at `b3aba30aa`: 95 of 611 sibling, 1 of 1 live indeterminate).
- **NEW, operator-reported 2026-09-22 — no owner: orchestrator-session UX/mechanism gap.**
  Three related asks surfaced during a live `status` interaction, none cleanly covered by
  an existing staged spec: (a) when already inside a `/plan-marshall:plan-orchestrator
  epic={slug}` session, suggestions should name the bare verb (e.g. "analyze" to drain the
  inbox) rather than restate the full slash-command form — the epic is already bound to the
  session; (b) after a major state change, surface the core next-verb options by name (not
  full syntax), plus any previously-emitted `/plan-marshall` command still `launched` and
  not yet operator-confirmed `running`; (c) candidate mechanism for (b): a single script call
  cross-checking `launched`-status queue rows against live plan-lifecycle state (the same
  `manage-status list`-cross-read pattern already used elsewhere to catch a queue claiming
  `staged` while the live plan has run for a day) to positively detect whether an emitted
  command was actually started, rather than relying on the operator to say so. Not sized or
  staged — none of PLAN-02/03/05/06/07 owns this cleanly (PLAN-06 is ownership consolidation
  of scattered SCHEMA/detection items, not session-presentation UX). Flag for the next
  `decompose`/`cleanup` pass to size and place (new workstream, or fold into WS-04 if the
  running-check script turns out to share surface with `orchestrator.py`'s existing verbs).
  ↪ **TRANSFERRED 2026-10-05** to `truthful-signals` inbox `orchestrator-refactor-001.md` § 2.
- CONFIRMED NOT a new item — operator also flagged residual `slug=` example forms (e.g. the
  `plan-orchestrator` SKILL.md Usage table's `analyze slug={slug}` line). Already inside
  PLAN-05's sized rename surface (D1 CLI-flag rename `--slug`→`--epic`, D4's ~43-file prose
  sweep including `plan-orchestrator/**`) — no separate item created.
> ↪ Relocated to `settled.md` § "PLAN-01 stuck mid-finalize on an unreviewable diff" —
> resolved 2026-09-21 via the #1557/#1558 split.
> ↪ Relocated to `settled.md` § "Pre-PLAN-01 source_id prefix rejected by inbox detect" — closed: folded into PLAN-03, superseded by PM-MCP; carry-over filed in plan-marshall-mcp
> ↪ Relocated to `settled.md` § "Epic ledger tree split across two locations" — resolved
> 2026-09-21, both halves reconciled into the tracked tree.
> ↪ Relocated to `settled.md` § "Restart-check worktree signal reported not_ready" —
> resolved 2026-09-21, PR #1566 landed, `restart-check` now reports `ready`.
> ↪ Relocated to `settled.md` § "PLAN-01 branch skipped the plugin-cache sync" — superseded by later finalize syncs and the unified /sync-harnesses (#1684)
- (all other defects surfaced by decompose research were folded into a staged plan's Claim
  Labels; see PLAN-01 through PLAN-07)
- **NEW, from PLAN-08's landing (2026-09-23) — unrouted: git-config-injection production
  hardening, ~20 scripts repo-wide.** CodeRabbit finding `5ed953` on PR #1585: the test
  fixture's env scrub was hardened in-plan (TASK-010), but the broader hardening of
  production git seams (`orchestrator.py`'s `_git_read`, `_git_tree_diff`,
  `_resolve_anchor_sha`, and their counterparts across ~20 other scripts repo-wide) was
  deliberately held out of PLAN-08's `bug_fix` scope as a cross-cutting policy change. The
  landing's own residue note names this epic OR `truthful-signals` as candidate homes
  without picking one — `orchestrator.py` is only ONE instance of a repo-wide pattern, so
  staging it here would under-scope it, and dropping it would lose a real security finding.
  Not sized or staged — **operator routing decision needed**: stage a dedicated plan under
  this epic (WS-04, narrowly for `orchestrator.py`'s own three call sites) plus a
  `truthful-signals` item for the other ~17 sites, or route the whole thing to
  `truthful-signals` as one cross-cutting hardening plan.
  ↪ **TRANSFERRED 2026-10-05** to `truthful-signals` inbox `orchestrator-refactor-001.md` § 3 (as one cross-cutting plan).

## Watches

- **Harness sync owed (2026-10-03, updated at the PLAN-10 landing).** The harness installs predate #1685 (the
  mailbox-probe fix) and #1690 (the `land` verb and its `workflow/land.md`). PLAN-10's own finalize reports
  `finalize-step-sync-plugin-cache: done`, but whether that sync included #1685 was not checked. Until
  `/sync-harnesses` is confirmed: a running plan may still misreport `not_orchestrated` at transitions, and
  orchestrator sessions may not see the `land` verb. No plan is running now. — trigger: before the first
  `orchestrator land`, and before delivering any mailbox message to a running plan; retire when a sync is
  confirmed after `7a0af07c5`.

> ↪ Relocated to `settled.md` § "PLAN-11 landing residue" — (1) fixed by #1684, (2) owned by lesson 2026-10-02-10-001, (3) transferred to truthful-signals

- **PLAN-09 landing residue (2026-09-28, not folded):** (1) an unreadable main-checkout config silently falls
  back to the primary checkout (CodeRabbit, noise-filtered) — a silent fallback on the resolver seam; (2)
  `_cutover_refusal` duplicates `_default_base_branch()` (simplify, advisory); (3) `ci checks pull-request-runs`
  read `run_count=0` on #1652 although pull_request checks exist (review-apparatus territory); (4) branch-cleanup
  records `rev-parse HEAD` as the merge sha, wrong whenever another PR lands before switch-and-pull (landing
  recorded `438a0a71f`, main was at `c9c67839c`). Retire each when fixed or routed.
  ↪ **TRANSFERRED 2026-10-05**: (1)(2)(4) to `truthful-signals` inbox `orchestrator-refactor-001.md` § 4; (3) to `review-apparatus` inbox `orchestrator-refactor-001.md`.

> ↪ Relocated to `settled.md` § "truthful-signals PLAN-TRUTH-143 running, blocking dependents" — resolved 2026-09-20/21, shipped as PR #1539.
> ↪ Relocated to `settled.md` § "Cross-ledger watches keyed on PLAN-02 and PLAN-06 emission" — moot: PLAN-02 shipped, PLAN-06 superseded
- **NEW, from PLAN-08's landing (2026-09-23), low urgency.** PLAN-08's own round-2
  verification-feedback triage mis-dispositioned finding `e79ee5` as `accepted` though its
  own `resolution_detail` shows it was a false positive — self-flagged by
  `project:finalize-step-review-retrospective`, not independently re-verified by this
  analysis. — trigger: worth a spot-check if `plan-orchestrator:verification-feedback`
  triage quality is ever audited; no action owed otherwise.
> ↪ Relocated to `settled.md` § "Two orchestrator entities share one word" — resolved by
> PLAN-04/ADR-023, retired 2026-09-20.
- **Cross-plan `2-refine` suspicious-perfect-confidence tracking** (from
  `identifier-vocabulary-decision-008`, promoted to global lessons as `2026-09-20-08-011`).
  PLAN-04 scored 100% on all six weighted refine dimensions and the Q-Gate's
  suspicious-perfect-score flag was resolved `taken_into_account` — the reviewer's own
  rationale is that an orchestrator-authored, claim-labeled staged spec is EXPECTED to score
  100%, not suspiciously so. Whether this holds is a cross-plan question this epic's own
  corpus can answer as more plans land. — trigger: as each subsequent plan in this epic lands,
  record its `2-refine` aggregate score and Q-Gate resolution here; once 3+ data points exist,
  report the rate back to the promoted global lesson.
- **Per-plan argparse-rejection rate** (from `identifier-vocabulary-decision-010`/`-011`/`-012`,
  the latter two promoted individually, `-012` discarded standalone by its own instruction).
  PLAN-04's run produced 3 independent argparse rejections across 3 unrelated notations (`ci`
  router-flag-after-verb, `merge_lock --hold-start` type mismatch, `manage-status metadata`
  missing `--field`) in one plan — denominator unknown (n=1 epic-plan by construction).
  — trigger: as each subsequent plan lands, count its `script_failure`/`argparse_rejection`
  work-log markers here; 3+ data points settle whether PLAN-04's count was high, normal, or low.
