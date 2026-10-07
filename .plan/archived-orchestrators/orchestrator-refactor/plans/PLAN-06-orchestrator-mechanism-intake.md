# PLAN-06: Take ownership of the orchestrator mechanism scattered across sibling epics

> ⛔⛔ **SUPERSEDED BY PM-MCP (2026-09-26, operator decision relayed by `review-apparatus` inbox message; row status `parked`).**
> `plan-marshall-mcp` replaces both the process prose and the Python scripts this plan edits, so implementing it
> here is legacy work. Its implementation-independent content (rules, invariants, classifications, data,
> fixtures) was extracted to `plan-marshall-mcp/doc/known-defects/orchestrator-refactor-carry-over.md` as PM-MCP
> input. **Do NOT emit; un-park only by explicit operator decision.** The body below is kept intact as the
> evidence chain.

epic: orchestrator-refactor
workstream: WS-04

> Staged plan spec — one shippable unit of work, ready for `/plan-marshall` hand-off.
> Lives at `plans/PLAN-06-orchestrator-mechanism-intake.md` and is queued in the epic
> `status.json` `plans[]` field. The orchestrator EMITS the command below; it never launches
> the plan inline. This spec is SELF-SUFFICIENT: the emitted command is a one-line pointer
> and carries no brief, so every per-plan carry is authored here and nowhere else.
> See `persona-plan-orchestrator/standards/orchestration-model.md` for the tier and
> hand-off contract.

## Objective

Consolidate under one owner the orchestrator-mechanism items currently carried by epics whose
domain is something else. The mechanism is not the problem; the ownership is. One schema file
(`landing-payload-spec.md`) has three would-be owners in three ledgers that cannot see each
other, and one schema defect (the row-status vocabulary) was routed to the catch-all epic
explicitly because its finder judged it "not this epic's to fix".

> **Re-grounded 2026-09-21 against HEAD `e8a716501`.** Three material changes since staging:
> (1) the blocking condition below is DISCHARGED — `truthful-signals` PLAN-TRUTH-143 shipped
> as PR #1539 (merge `1c56734ce`, 2026-09-20T07:11:51Z); (2) D2 and D3 are MOOT — both were
> already closed at HEAD, by PR **#1366**, not by the #1370 this spec's own HYPOTHESIS guessed
> for the second one (see the Claim Labels correction); (3) D5 is real and CURRENTLY LIVE
> (confirmed against today's own `orchestrator inbox list`), but narrower than staged — the
> single-detector mechanism already exists and `phase-1-init` already documents the
> `--source-id` requirement (since PR #991); D5 narrows to enforcing that existing contract,
> not building new machinery.

## Deliverables

1. **D0 — GATE: re-ground every carried item against HEAD before scoping.** DONE as part of
   this cleanup pass, 2026-09-21 (`e8a716501`) — see the re-grounding note above and the
   corrected Claim Labels below. D2 and D3 dropped as closed; D1's ownership statement
   adjusted for a since-changed row status; D5 confirmed live and narrowed.
2. **D1 — one owner for `landing-payload-spec.md`.** State the ownership, and state how the
   sibling specs that declare it (see Claim Labels) are sequenced against it. ⚠ One of the
   five sibling specs, `truthful-signals` PLAN-TRUTH-144, is now `running` (was `staged` at
   research time) — the running-row exclusion applies: this plan's ownership statement notes
   its existence and defers touching anything that would affect its scope until it lands.
3. **D2 — DROPPED, already closed at HEAD.** ~~the two-parser split~~ `orchestrator.py:785-794`
   already declares in-source that `## Expected Surface`'s grammar and reader both live in
   `script-shared`'s `epic_spec_parser` alone, and a population-derived guard test
   (`test_expected_surface_single_reader.py`) already pins the single-reader property. Closed
   by PR #1366 (`b758d5c02`). No remaining work.
4. **D3 — DROPPED, already closed at HEAD.** ~~the plan-id detection seam~~
   `_epic_partition.py:109-115` already imports the same `epic_spec_parser` reader;
   `epic_spec_parser.plan_id_of` (`:710`, using `PLAN_ID_PREFIXED_SEGMENT` at `:116`) already
   recognises `PLAN-{CODE}-{NNN}` and explicitly refuses a letter-suffixed id rather than
   silently collapsing it. Also closed by PR #1366. No remaining work.
5. **D4 — the transfer record.** Each intake item names its source epic, its source location,
   and whether the source row is retired, re-scoped, or left alone. An offer is not a transfer;
   the sibling ledger must be updated by its own orchestrator session, and this plan records
   what it asks for rather than performing it. Since D2/D3 dropped, D4 now covers only the
   `landing-payload-spec.md` ownership item (D1) and the row-status-vocabulary assignment
   (already recorded as belonging to PLAN-02, see Claim Labels).
6. **D5 (folded 2026-09-20, from `identifier-vocabulary-decision-003`; narrowed 2026-09-21) —
   enforce the existing `source_id` contract phase-1-init already documents but does not
   validate.** The mechanism this deliverable originally proposed to BUILD already exists:
   `manage-execution-manifest.py:900-907` states the compose-time gate reads "the SAME
   `source_id` pointer `phase-1-init` persisted and `orchestrator inbox detect` classifies —
   no second detector", and `phase-1-init/SKILL.md:303` has mandated
   `--source-id "{spec_path}"` on the file-pointer branch since PR #991. What is missing is
   ENFORCEMENT: nothing fails loudly when a file-pointer request lands with `source_id`
   absent, so the documented contract is silently violable — exactly as it was violated for
   PLAN-04 (see the D5 evidence below, re-confirmed live TODAY, not merely historically). The
   fix is a validation at `phase-1-init`'s file-pointer branch (or a loud failure at the
   terminal-emission gate when the signal is absent on a plan the finalize dispatcher later
   resolves as orchestrated), not a new detection mechanism.

## Non-Goals

- No `status.json` schema change (PLAN-02's job), except where an intake item IS the schema
  change (the row-status vocabulary) and is explicitly assigned there instead of duplicated
  here.
- No sibling ledger is edited by this plan.

## Claim Labels

- OBSERVED — three-way concurrent ownership of ONE orchestrator schema file,
  `plan-orchestrator/standards/landing-payload-spec.md`, declared as Expected Surface by:
  `post-run-quality` PLAN-PRQ-04 (staged, "the owed-item fact keys", D1/D2);
  `truthful-signals` PLAN-TRUTH-149 (staged), -146 (staged), -167 (staged, HYPOTHESIS);
  `review-apparatus` PLAN-PR-073 (staged, "⚠ D2 edits the orchestrator inbox"), plus parked
  -055 and -064.
- OBSERVED (added 2026-09-21) — `truthful-signals` PLAN-TRUTH-144 (running as of this
  cleanup pass) also declares `landing-payload-spec.md`. Per the running-row exclusion in
  `orchestration-model.md` § Cleanup Contract, this spec does not re-scope around it — D1's
  ownership statement notes its existence and waits for it to land before touching anything
  that would affect PLAN-TRUTH-144's own scope.
- OBSERVED — `review-apparatus/epic.md:2533-2542`: the queue cannot express `retired`;
  `VALID_STATUS_VOCABULARY` is `{staged, launched, running, parked, shipped, landed}` and
  `--transition` refuses `retired` "while four rows in this very ledger already carry it"; the
  item was "Filed to `truthful-signals` as `review-apparatus-036.md`… it is not this epic's to
  fix". Generalised first-party (see PLAN-02): 95 of 500 rows across 12 ledgers, 6 epics. This
  item is ASSIGNED to PLAN-02 (WS-01) — it is the schema — and this deliverable records that
  assignment rather than re-implementing it.
- OBSERVED — `review-apparatus/epic.md:2008-2013` records that specs declare
  `../cloud-runs/*` as Expected Surface while their own Write-Boundary forbids editing anything
  under `.plan/local/orchestrator/` and that tree is git-ignored, "so such an edit can never
  appear in a PR". This is this epic's own aspect-1 thesis (PLAN-01/PLAN-02), found
  independently from another ledger — cite it there, do not re-derive it here.
- OBSERVED (citation corrected 2026-09-23, cleanup A1 — the range shifted after `#1578`'s
  epic restructuring, was `:2146-2158`) — `truthful-signals/epic.md:2088-2100` (D-SWEEP-a):
  two parsers read one `## Expected Surface` and disagree — `orchestrator.py`'s queue
  renderer returns "(no expected surface)" and governs the disjointness gate, while
  `epic-surface-partition classify` returns "declarative, 6 resolved paths" and governs only
  the report. Recorded as a live ADR-019 violation inside our own machinery. Already CLOSED
  at this epic's own HEAD per claim 9's verdict — historical evidence, not open work.
- OBSERVED (citation corrected 2026-09-23, cleanup A1 — was `:2160-2166`) —
  `truthful-signals/epic.md:2102-2108` (D-SWEEP-b): `epic-surface-partition classify` carries
  a THIRD plan-id detector that does not recognise `PLAN-{CODE}-{NNN}`, so attribution
  "cannot group by plan for this epic at all"; `orchestrator inbox detect` already declares
  itself the single detection seam. Already CLOSED — historical evidence, not open work.
- OBSERVED — `epic-surface-partition.py:132` calls `get_store_dir('orchestrator', epic,
  allow_archived=True)`: the orchestrator mechanism has a second implementation home in the
  `pm-plugin-development` bundle.
- OBSERVED — `code-intelligence-substrate` PLAN-CIS-052 (staged) declares `inbox-envelope.md`
  (D6d) and `_orchestrator_inbox.py` (D6e), with a recorded cross-epic ordering constraint
  against the now-superseded `truthful-signals` PLAN-TRUTH-100 (successor PLAN-TRUTH-143,
  which as of this cleanup pass has SHIPPED as PR #1539 — the ordering constraint on
  PLAN-CIS-052 is therefore discharged, removing one sequencing input from D1's transfer
  record; PLAN-CIS-052 itself is not touched by this plan).
- HYPOTHESIS — the two-parser disagreement and the third plan-id detector were closed by
  `truthful-signals` PLAN-TRUTH-113 (shipped, PR #1366); confirm/refute at `orchestrator.py`
  § the queue renderer and the partition script's `classify` path before staging any remedy.
  - verdict: corroborated | checked_at: 9588b30b317d0312ede90f1982122aa3145ea871 | by: orchestrator-refactor/cleanup | rescoped: n/a | evidence: Every citation resolves despite orchestrator.py growing to 6243 lines. Single-reader property declared in-source at :909-912 (was :883-886): both grammar and reader live in script-shared's epic_spec_parser, this module CONSUMES it. _epic_partition.py:6/:115 imports the same reader; epic-surface-partition.py:71 likewise. plan_id_of at :710, PLAN_ID_PREFIXED_SEGMENT at :116, refusal of letter-suffixed ids documented :138/:212. Attribution re-verified: b758d5c02 = PR #1366.
- HYPOTHESIS — the claim-parsing gates recorded at
  `code-intelligence-substrate/epic.md:1267-1292` (`orchestrator.py:389`
  `CLAIM_LABELS_HEADING_RE` case-exact, and `_parse_claims` accepting only top-level bullets,
  jointly producing a vacuous prep-ready admission) were closed by PLAN-CIS-051 (shipped, PR
  #1370); confirm/refute at those two symbols.
  - verdict: contradicted | checked_at: 9588b30b317d0312ede90f1982122aa3145ea871 | by: orchestrator-refactor/cleanup | rescoped: yes | evidence: Attribution re-refuted at source; outcome moot; already absorbed in D3. git log --grep=#1370 -> 7845a4b9a; git show --stat on orchestrator.py is empty -- PR #1370 touched no orchestrator.py. Gate 1 closed by #1366: CLAIM_LABELS_HEADING_RE now carries re.IGNORECASE at :930. Gate 2 closed by #1355 (91a07aaa4). Correction stands: claim-section parse is a FOUR-state vocabulary (:433-444), assigned in _parse_claim_section :2797-2904, tallied over the whole vocabulary at :3554/:3594. No further spec change owed.
- Verify-first clause: `truthful-signals` PLAN-TRUTH-143 is RUNNING and declares the widest
  orchestrator surface of any live spec (`orchestrator.py`, `_orchestrator_inbox.py`,
  `SKILL.md`, `inbox-envelope.md`, `orchestration-model.md`, `workflow/analyze.md`,
  `workflow/orchestrate.md`). Do NOT re-scope it — the running-row exclusion in
  `orchestration-model.md` § Cleanup Contract forbids changing the brief under a running plan.
  This plan's command is BLOCKED until PLAN-TRUTH-143 lands and this spec is re-grounded
  against the new HEAD.
  - verdict: contradicted | checked_at: 9588b30b317d0312ede90f1982122aa3145ea871 | by: orchestrator-refactor/cleanup | rescoped: yes | evidence: Blocker discharged, already absorbed. PLAN-TRUTH-143 shipped as 1c56734ce (PR #1539), absent from the 45-spec truthful-signals corpus. PLAN-06's own row reads staged at HEAD (corpus enumerate: shipped 4/staged 6/parked 1 -- PLAN-08 shipped since last pass), not parked. New adjacency persists and is git-tracked: PLAN-TRUTH-177-orchestration-detection-fails-open-without-source-id targets the same gap as PLAN-06's narrowed D5 -- already recorded in the spec's own OBSERVED bullet idx15. No further spec change owed.
- ⛔ CLOSED, do not re-stage: `code-intelligence-substrate/epic.md:1348-1362` ("the orchestrator
  has NO add-a-row verb") — `queue --add-row` shipped via `truthful-signals` PLAN-TRUTH-099
  (PR #1434) and is live at `orchestrator.py:896-992` and `:1090-1192`.
- ⛔ `lessons-handling-26-08-26-01` PLAN-LH2-14 "orchestrator-stops-short" is NOT an item for
  this plan. Its two clustered lessons concern the plan-LIFECYCLE orchestrator yielding to the
  operator (`*_without_asking` knobs), not the epic-tier orchestrator this epic owns. Two
  different entities share the word "orchestrator" in this codebase — see PLAN-04.
- OBSERVED (D5, from `identifier-vocabulary-decision-003`, filed against PLAN-04's own
  landing) — compose-time decision log entry `7f9799`:
  `terminal_emission_orchestration_gate — dropped emit-landing from phase_6.steps: plan is
  not orchestrated (detection=not_orchestrator_pointer); no epic inbox to write a landing
  to`, on a plan whose `request.md` carried `source: description` with no `source_id`
  section (`request read --section source_id` → `section_not_found`), while the SAME plan's
  finalize retrospective was dispatched with `orchestrated: true, epic: orchestrator-refactor`.
  Measured consequence, independently confirmed by this epic's own `analyze`:
  `orchestrator inbox list --slug orchestrator-refactor` reported
  `queue_reconciliation.queue_count: 7`, `landing_count: 0`, `queue_without_landing_count: 7`.
  ⚠ CORRECTED 2026-09-21: this is not historical. Re-running `inbox list` TODAY returns the
  SAME figures, with `queue_without_landing[7]` naming all seven plans INCLUDING PLAN-04
  (whose row is `shipped` / `pr: #1543` / `landing: landings/PLAN-04.md`). The queue row was
  stamped by this orchestrator's own `analyze` reconciliation; no `kind: landing` inbox
  message ever arrived from the plan itself, because the gate never fired. The gap is LIVE,
  not something PLAN-04's own landing already closed.
- OBSERVED (added 2026-09-21) — the D5 mechanism is NOT missing, only unenforced. The
  compose-time gate already reads the single seam:
  `manage-execution-manifest.py:900-907` states it reads "the SAME `source_id` pointer
  `phase-1-init` persisted and `orchestrator inbox detect` classifies — no second detector",
  called at `:976`. And `phase-1-init/SKILL.md:303` has mandated `--source-id "{spec_path}"`
  on the file-pointer branch since PR #991 (`f7c4130cb`). D5 therefore narrows to: make the
  existing, already-documented contract FAIL LOUDLY when violated, rather than building any
  new detection or reconciliation mechanism.
- OBSERVED (added 2026-09-22, re-grounding pass) — `truthful-signals` has since staged
  `PLAN-TRUTH-177-orchestration-detection-fails-open-without-source-id`, targeting the SAME
  gap D5 narrows to (the compose-time gate failing loudly when `source_id` is absent). Check
  its state before D1/D5 land — if it ships first, D5 narrows further to confirming the fix
  rather than building it; if this plan lands first, PLAN-TRUTH-177 should be re-grounded
  against this plan's landing rather than duplicating the work.

## Expected Surface

- OBSERVED: `marketplace/bundles/plan-marshall/skills/plan-orchestrator/standards/landing-payload-spec.md`
- OBSERVED: `marketplace/bundles/plan-marshall/skills/plan-orchestrator/standards/inbox-envelope.md`
- OBSERVED: `marketplace/bundles/plan-marshall/skills/plan-orchestrator/scripts/_orchestrator_inbox.py`
- OBSERVED: `marketplace/bundles/plan-marshall/skills/plan-orchestrator/scripts/orchestrator.py`
- OBSERVED: `marketplace/bundles/pm-plugin-development/skills/tools-epic-surface-partition/scripts/_epic_partition.py`
- OBSERVED: `marketplace/bundles/pm-plugin-development/skills/tools-epic-surface-partition/scripts/epic-surface-partition.py`
- OBSERVED (added by the D5 fold, 2026-09-20): `marketplace/bundles/plan-marshall/skills/phase-1-init/**`
- OBSERVED (added by the D5 fold, 2026-09-20): `marketplace/bundles/plan-marshall/skills/phase-6-finalize/**`
- OBSERVED: `test/plan-marshall/plan-orchestrator/**`
- OBSERVED: `test/pm-plugin-development/tools-epic-surface-partition/**`
- OBSERVED (added by the D5 fold, 2026-09-20): `test/plan-marshall/phase-1-init/**`
- OBSERVED (added by the D5 fold, 2026-09-20): `test/plan-marshall/phase-6-finalize/**`

## Dependencies and Sequencing

- Depends on: none, as of 2026-09-21 — ~~`truthful-signals` PLAN-TRUTH-143 landing first~~
  DISCHARGED (shipped PR #1539). Within this epic, no hard dependency; unblocked and
  re-staged.
- Overlaps with: PLAN-05 (`_orchestrator_inbox.py`, `tools-epic-surface-partition/**`,
  and — after this plan's own D5 fold — `phase-1-init/**`/`phase-6-finalize/**`); PLAN-07
  (`orchestrator.py`, `_orchestrator_inbox.py`).
- Adjacent to: `truthful-signals` PLAN-TRUTH-149/-146/-167 (staged), -144 (**running** as of
  2026-09-21 — do not touch anything affecting its scope until it lands), `review-apparatus`
  PLAN-PR-073/-055/-064, `post-run-quality` PLAN-PRQ-04, `code-intelligence-substrate`
  PLAN-CIS-052 (its own cross-epic ordering constraint against PLAN-TRUTH-100→-143 is
  discharged) — all declare `landing-payload-spec.md` and/or `_orchestrator_inbox.py`. None of
  these overlaps are visible to the automated disjointness gate (it does not cross sibling
  ledgers); this plan's D4 records the transfer request into each rather than editing them.

## Hand-Off Command

```text
/plan-marshall task="implement .plan/orchestrator/orchestrator-refactor/plans/PLAN-06-orchestrator-mechanism-intake.md"
```

## Write-Boundary

The plan implementing this spec touches only repository source, standards and tests across two
bundles. It creates and edits NO file under ANY orchestrator store — including sibling
epics' — other than its own `inbox/{sender}-{seq}` message in this epic's own tree. The
orchestrator owns every other ledger write, and reports its outcome through its PR and its
inbox message. The inbox exception's qualifiers and the sole sanctioned write mechanism are
stated in `persona-plan-orchestrator/standards/orchestration-model.md` § Ledger
Write-Boundary.
