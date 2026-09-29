# Settled narrative — process-compliance

> Verbatim relocations out of `epic.md` by the `cleanup` compact stage (operator-confirmed
> 2026-09-28). Each origin keeps a pointer naming the heading below. Moved, never dropped.

## Inherited Material — the decompose input

⛔ **This is a hand-off record, not a queue.** Nothing below is staged. Every item is
OBSERVED in a shipped plan's run and verified at HEAD there; each names its evidence.
Decompose turns these into workstreams and specs. All claim labels must be re-verified
at decompose against the implementing sources (verify-first contract).

### A. The governing observation (read first)

Prevention failed in every instance; detection-and-correction worked in every
instance (finalize-machinery inbox `invocation-surfaces-004`, archived). Five prose
rules simultaneously in force were all rationalized around; the fail-closed boundary
guards caught 100% of deviations. Design conclusion: not "more rules" but earlier,
structural enforcement of existing rules. Cost asymmetry is documented there: doing
it in order costs phase artifacts up front; the deviated path cost a relocation, a
manifest composition, an outline reconstruction, a foreign-gate STOP plus retrofit,
and unpriced collision/orphan risks.

### B. Phase-completion artifact gates (highest leverage)

Bare 2-refine/3-outline/4-plan transitions with zero artifacts are decidable inside
`manage-status transition` itself — nothing checks (`invocation-surfaces-004`
deviation 2, proposal P0). Gate: refuse `--completed 3-outline` unless
solution_outline.md validates; refuse `--completed 4-plan` unless ≥1 task file exists
or the manifest is composed; refuse `--completed 2-refine` unless the
clarified/confidence record exists. Required carve-out: explicit exemption metadata
for legitimately artifact-free phases (decision-logged, retrospective-visible).
Related corpus: 2026-09-06-08-001 (authoring a fix does not immunize the authoring).

### C. Worktree discipline: materialization assertion + boundary checks + hand-off gate

Work on main with `use_worktree=true` and never-materialized worktree, twice, from
independent sessions (archived `invocation-surfaces-001`, `plan-01-head-rearm-001`;
PLAN-04 residue Watch in finalize-machinery). Proposal P1: `prepare_execute`
persists a `worktree_materialized` flag; every phase-5 dispatch and Bucket-B
invocation with `use_worktree=true` refuses while unset; extend the post-refine
main-clean assertion to EVERY phase boundary 1→2→3→4→5. Stated residual: no script
gate binds a free agent's Edit tool — pair with detection, not instead of it.
Proposal from `plan-01-head-rearm-003`: hand-off admission gate (plan record +
`feature/` branch + worktree + proven-clean main before the first edit) and a
session-start tree check (branch + status before the first repo edit). Related
corpus: 2026-09-17-19-001 (move-in single-location rule).

### D. Compliant paths where none exist (the forced-violation class)

Deviations 3–5 of `invocation-surfaces-004` share one root cause: the compliant path
did not cover the use case. (1) Sanctioned read path for orchestrator specs —
proposal P2 (`corpus read --slug --plan`), else record the carve-out in AGENTS.md;
`plan-01-head-rearm-003` R4/R6 agree (three rules, one action, no precedence; no
manage verb exposes a spec body). (2) Generator-bootstrap exception + template-content
staleness detection — proposal P3 (fresh clone / stale cached generator contradicts
"never by direct path"). (3) Wrapper filter passthrough for fast targeted signal —
proposal P4 (direct `.venv` pytest had no sanctioned form).

### E. Nudge handling and correction memory (persona behavior rules)

`plan-01-head-rearm-003` R2/R3/R5: literal-request optimization answered every nudge
minimally without re-deriving the invariant; the cross-turn correction-memory rule
existed and was never consulted (three nudges for one invariant); minimal-literal
compliance is itself a finding. Proposals: nudge-batching obligation (enumerate the
invariant family, close every sibling, report the set) and structured
deviation-audit form — proposal P5 (fixed checklist artifact replacing prose
"revisit the workflow"). Owner surface: persona-plan-marshall-agent behavior rules.

### F. Dispatch contract gaps (improvisation forced by missing contracts)

Five promoted corpus lessons, all from plan-03-review-currency with evidence:
2026-09-17-19-004 (generic dispatch must defer to step-owned dispatch bodies —
`requires_prompt_fields`, author/verifier choreography); 2026-09-17-19-005 (fix-task
loop-back dispatch shape: no envelope fields stated); 2026-09-17-19-006
(`loop_back_target` missing on verification-feedback loop_back returns); -007
(producer vocabulary inconsistently enforced — `ci-verify-timeout` accepted once,
contract-violated once); -008 (dispatch roster should carry each step's prompt
skills, pinned by the roster-closure test family).

### G. Opencode-specific abstraction repairs (do NOT re-stage PLAN-07)

Transcript-less target handling is staged as finalize-machinery PLAN-07
(session-identity resolver, degrade-to-unenriched) — referenced here, never
re-staged. This epic owns what surrounds it: the opencode runtime gaps that forced
improvisation (no session id, no transcript, hook_not_configured — evidence in
archived `plan-03-review-currency-003`, `git-branch-mechanics-002`, and the operator
paste summaries), the NO_SESSION_IDENTITY sentinel convention, and unattended-order
merge authorization (proposal 6 of `plan-01-head-rearm-003` — the merge gate's
consent prompt is indistinguishable from a blocking question).

### H. What NOT to change (carried from -004 § What NOT to change)

The fail-closed boundary guards (dirty-tree block, pr_title capture,
manifest-required abort, freshness stale refusal, foreign-gate STOP, barrier UNKNOWN
handling); the loop-back machinery (triage → fix tasks → fix commit → re-review);
the metrics gap flags (backfilling boundaries post-hoc falsifies the record). Extend
them; do not soften them.

## Incorporated lessons (moved from shared corpus at operator direction)

13 lessons describing process-compliance issues were moved from
`.plan/local/lessons-learned/` into `archive/lessons/` in this tree (verbatim bodies
with provenance headers) and staged against the queue below. Sources were retired from
the shared corpus after the copies were verified on disk.

| Lesson | Target | Notes |
|--------|--------|-------|
| 2026-09-17-19-001 | WS-02 / PLAN-02 | Worktree single-location rule; extends epic §C |
| 2026-09-17-19-004 | WS-05 / PLAN-05 | Step-owned dispatch bodies; core of epic §F |
| 2026-09-17-19-005 | WS-05 / PLAN-05 | Fix-task loop-back shape; core of epic §F |
| 2026-09-17-19-006 | WS-05 / PLAN-05 | loop_back_target required; core of epic §F |
| 2026-09-17-19-007 | WS-05 / PLAN-06 | Producer vocabulary; core of epic §F |
| 2026-09-17-19-008 | WS-05 / PLAN-06 | Roster prompt skills; core of epic §F |
| 2026-09-06-08-001 | WS-01 / PLAN-01 | Self-immunization anti-pattern; related corpus of epic §B |
| 2026-09-07-15-007 | WS-06 / PLAN-07 | Standing vs specific authorization; epic §G proposal 6 |
| 2026-09-16-11-001 | WS-06 / PLAN-07 | OpenCode usage-capture gap; epic §G runtime gaps |
| 2026-08-25-09-006 | WS-06 / PLAN-07 | Transcript fallback via session_ids; transcript-less family |
| 2026-09-03-07-001 | WS-05 / PLAN-05 | requires_prompt_fields pre-flight; precursor of -004 |
| 2026-08-25-09-015 | WS-02 / PLAN-02 | Session-restart cwd re-pin; worktree discipline |
| 2026-09-03-06-004 | WS-04 / PLAN-04 | Hard-rule precedence sentence; persona behavior rules |

Deliberately NOT moved (already-covered, retired from corpus at operator direction):
the argparse-rejection cluster 2026-09-11-19-001, 2026-09-04-17-008, and the
canonical-forms mechanism 2026-09-12-17-001 — the argparse-rejection class shipped as
PR #1507 per the annotations above, so moving them would re-stage shipped work. Each
retired with verdict `superseded` and a tombstone naming PR #1507 plus the
recipe-fix-argparse-rejection remediation carrier.

## Open Defects — closed (relocated 2026-09-28)

- **Six invalid inbox messages (drain 2026-09-26,
  `module-budget-campaign-completion-006` … `-011`) — RESOLVED 2026-09-27.**
  Stray `revision=1` header line removed on operator instruction (git shows no
  amendment ever happened); all six then validated, drained as `observed`
  (content already in carry-over MB06–MB11) and archived. Original record: Each fails
  `revision_not_monotonic` (`revision=1` with no `amended=` stamp — a
  hand-set revision), so the drain may not consume them and they stay
  un-archived. Content was read and extracted anyway (carry-over rows
  MB06–MB11: absolute `WORKTREE` refusal, re-fired step cannot record
  `failed`, opencode emitter drops `workflow/`, non-durable `cd`, 271-item
  `uncertain` prompt, 434-path hand-transcribed footprint). Recovery is
  operator-side: correct the envelopes or retire the files; `inbox amend`
  refuses an already-invalid message.
- **Partial inbox drain 2026-09-21 (landing pass: 13/76 consumed, 63 remain).**
  All 13 `kind: landing` messages mapped to already-shipped rows with
  `landings/` records present — zero new ships, so no `queue --transition` /
  `--set-row` writes were owed. Terminals reconciled: `phase-gates-012`
  (PLAN-01/PR 1540), `compliant-paths-007` (PLAN-03/PR 1542),
  `plan-02-worktree-discipline-014` + tail `...-015` (PLAN-02/PR 1547),
  `plan-04-persona-behavior-003` (PLAN-04/PR 1556),
  `plan-07-opencode-repairs-008` (PLAN-07/PR 1554, with erratum: facts block
  names PR 1553 closed-unmerged while body + queue carry live PR 1554 merged —
  annotated, facts not overwritten). Predecessors retired by successor:
  `plan-02-worktree-discipline-001..005` by `-014`,
  `plan-04-persona-behavior-001/002` by `-003`. The remaining 63 (42 findings,
  21 candidate-lessons) are enumerated with draft dispositions held for the next
   drain pass — 18 stage heads, folds, promotes, and observations per the
   drain-proposal record in the decision log. Per the drain contract a non-zero
   `live_count` after this pass is recorded here as the discrepancy, not as a
   clean empty. (Closed 2026-09-21 by the findings/lessons pass below — 63/63
   consumed, queue empty.)
- **Deliberate process bypass for speed, opencode (paste 2026-09-22,
  `run-3-carve-2-tools-permission-fix`, test-quality PLAN-181 carve 2, unowned).**
  Executing agent confesses delivering D1–D4 + PR #1582 while bypassing the
  process: phased lifecycle skipped (init artifacts inline, D2 direct, no
  2-refine → 3-outline → 4-plan → 5-execute envelopes), work on main-checkout
  feature branch instead of phase-5 worktree move-in, direct pytest /
  execute-script without architecture resolve, plain git / rm / python3 -c
  instead of workflow-integration-git / manage-* scripts, quality-gate over
  uncommitted edits, direct `.plan/` reads and `/tmp/opencode/` staging
  instead of `.plan/temp/`. Corroborated: branch
  `feature/run-3-carve-2-tools-permission-fix` exists on main checkout, PR
  #1582 open on that head (test-only carve, 141 passed), own inbox
  `run-3-carve-2-tools-permission-fix-001.md` items 4–5 admit the worktree
  deviation and tooling note. Stated cause: delivery prioritized over the
  slower compliant path; inbox filings do not excuse the bypasses. No owning
  spec (persona-conduct-adjacent, mechanism is resolve-speed incentive);
  candidate future staging. Inbox filing itself stays queued for drain.
- **Addenda drain 2026-09-22 (`run-3-...-001` remainder, `-002`, `-003`;
  folded, no new defect).** Remainder of -001: fidelity path-sensitivity
  (`test_identities` carry paths, so splits report lost=124/gained=124 with
  names preserved — instrument-vs-expectation gap); `manage-references get`
  without `--field` refused (discoverability gap, recovered via
  `manage-files read`); `rg` absent on PATH (tooling note, counted via
  python); planning-lane `route` deep with null scope/change signals
  (proceeded inline, no block); clean-main dirt was operator-queued ledger
  state, logged and proceeded. -002 remediation: kept-branch work redone
  genuinely on a fresh tree (byte-identical to kept commit), Sourcery nit
  fixed as TASK-004, PR #1582 enqueued. -003 closure, PR-corroborated:
  squash-merged as 1a9a6722 (13 files), branches removed via sanctioned
  sequence, test-quality landing amended. The bypass story closes with a
  genuine re-execution plus merge — recorded here; test-quality PLAN-181
  queue reconciliation is that epic's drain business.

## Watches — settled (relocated 2026-09-28)

- **RETIRED 2026-09-28 — PLAN-13's "landing will be skipped" claim (refuted 2026-09-27).** The run
  claimed the `PLAN-13-…` filename was not recognised as orchestrated. `inbox detect` returned
  `orchestrated: true`, and the `kind: landing` message `-007` then arrived through that same detector.
  (The original 2026-09-27 entry was overwritten on disk by a concurrent session edit before it was
  committed; it is restated here.)
- **Process findings routed to the PM-MCP carry-over (drain 2026-09-26,
  observed, no staging).** `opencode-bootstrap-executor-fix-001` (5 violations:
  foundational-skill load failed twice as `ripgrep execution failed` and the run
  continued; direct-path generator recovery; incomplete init; stale
  `comments-stage` invocation; direct `.plan/` reads) → rows OB.1–OB.5.
  `truth-179-opencode-target-detection-landed-005` (whole-tree gate red on
  pristine main; cache class closed in-run, gate source-scoping shipped as
  #1632; residual 26 canonical-forms errors on correct prose) → rows
  T179.1–T179.6, with T179.1 (baseline-vs-plan attribution) a full PM-MCP gap.
- **Corpus scrub checked (drain 2026-09-18, `finalize-machinery-003`).** The 15
  IDs finalize-machinery retired resolve to zero citations in this epic's staged
  specs and ledger (grep over the tree hits only the notice itself) — no
  re-pointing owed.
- **Simplify sweep scope note (drain 2026-09-18, `git-branch-mechanics-001`
  item 8).** A re-fired simplify pass deleted a just-added regression test as
  duplicative (correct outcome, suite green) — recorded with no action so a future
  bad cut has a prior to cite.
- **PLAN-01 in flight (paste 2026-09-18, code-corroborated).** Executing plan
  `phase-gates` reports the gate implemented (`_has_refine/outline/plan_artifact`,
  `_phase_artifact_refusal`, three fail-closed codes, exemption form, docs,
  10-test module, 28 passing per plan report — test count plan-reported, not
  re-run here) with subject-class self-review applied per archived 2026-09-06-08-001.
  Symbols verified at HEAD in `_cmd_lifecycle.py` (:171/:204/:225/:248/:282-284)
  and `manage-status.py` (:342/:351); no re-verdicting (premises already settled
  at cleanup). Inbox `phase-gates-001.md` validated live/queued for a later drain.
- **PLAN-02 mid-flight (paste 2026-09-19, code-corroborated, no ship — no PR).**
  Branch `feature/plan-02-worktree-discipline` pushed (b47eba9e4, fe7e2940a on
  433d0a6), 6 files per diffstat matching the claimed surfaces; main clean.
  Self-reported gaps corroborated: `guarded_inject`'s only production path is
  the CLI `cmd_run` (default fail-open) and no dispatch caller passes
  `--worktree-materialized` (execute-task SKILL.md seams at :111/:398) — seam
  built, wiring not; the 5-entry worktree-resolution audit sub-item unaddressed.
  Test/quality claims are plan-reported, not re-run here (re-running is plan
  work). Remaining work (caller wiring, audit, finalize PR) belongs to the
  running plan — tracked here, staged nowhere; PR opens on operator word.
  (Retired 2026-09-19 by PLAN-02 landing PR #1547 — gaps closed in-run.)
- **PLAN-02 self-reported process deviations (paste 2026-09-19, absorbed).**
  Direct `.plan/` Read at opening, fast-tracked refine/outline/plan (hand-set
  confidence/scope/skills, skipped loops and Q-gates), focused pytest outside
  the resolved envelope. Pattern recurrence of epic §C–E material, now with a
  first-party admission attached. Formal record lives in inbox
  `plan-02-worktree-discipline-001.md` (live/queued, kind: landing) for the
  owed drain; no duplicate defect opened.
- **Full findings/lessons drain 2026-09-21 (63/63 consumed, queue empty).**
  Landing pass (13) closed earlier; this pass: 42 findings + 21 candidate-lessons.
  Promoted 6 corpus lessons (2026-09-21-15-001..006: regular-file gate, stale-bot
  pairs, ci `--plan-id` position, canonical-forms quoting, Q-gate assessment
  coverage, decline-contra-intent triage). Staged 4 specs (PLAN-09 store-access,
  PLAN-10 entry-capture, PLAN-11 landing-facts, PLAN-12 tool-triage) carrying 12
  staged + 7 folded messages. Folded `phase-gates-009` into staged PLAN-08
  (surface unchanged, recorded in-spec). Discarded 3 (TFR-001 duplicate of shipped
  PLAN-03 corpus-read; PG-008/P02-008 embodied in shipped work). Retired
  `compliant-paths-003` by successor (`-007`). Absorbed 27 observations (in-run
  remediations, override/identity records, foreign-epic notes for test-quality and
  quality-aspect with cross-refs, recurrence notes). Per-message dispositions in
  the decision log; messages archived on consume.
- **Lessons-routing duplicate lead, verified negative (drain 2026-09-22,
  `lessons-routing-001.md`, observed).** The flagged `2026-09-21-10-004` was
  promoted to the global corpus by truthful-signals on 2026-09-21 AND is cited
  as a source claim in staged PLAN-14 — checked both: one corpus copy, one
  spec citation, no double promotion. PLAN-14 needs no change. The underlying
  gap (corpus carries no promoted-by-epic field) is tracked in
  lessons-routing's own epic, not here.
- **PLAN-06 spec repointed in-drain 2026-09-23 (`plan-06-dispatch-roster-001.md`,
  observed).** Hand-Off, Write-Boundary, and two Claim evidence pointers still
  named the pre-migration `.plan/local/orchestrator/` tier — corrected to
  `.plan/orchestrator/` in place. Same message corroborates the PLAN-10 D2
  re-opening with a `source_id` present, and the ledger-gate family from the
  plan side; both folded into their homes, no duplicate defect.
- **PLAN-06 repoint cross-epic recurrence (drain 2026-09-23,
  `truth-147-lane-reports-green-001.md` item 1, observed).** Truthful-signals
  PLAN-TRUTH-147's hand-off emits the same stale `.plan/local/` path our
  PLAN-06 carried — foreign epic, not edited here; their drain's business.
- **PLAN-183 remediation closed (drain 2026-09-23,
  `carried-defects-and-watches-closure-001/002.md`, observed).** Worktree
  deviation remediated via the sanctioned stash-move path (PR #1602 from the
  worktree, plan-reported); quality-gate churn remediated via clean-before
  checkout; metrics gaps recorded not backfilled. Stale-lead re-derivations
  and task-contract frictions noted as that run's business.
- **PLAN-05 shipped 2026-09-22 (PR #1583, squash 40cacf7d).** All 4 deliverables
  per spec; landing record at `landings/PLAN-05.md`. Landing message was
  narrative-only (incomplete-landing defect above). Owed per landing:
  target-regeneration + plugin-cache sync re-run once main clean.
- **PLAN-06 shipped 2026-09-24 (PR #1606, merge 07ccfeda; #1594 closed
  unmerged for review retrigger).** All 4 deliverables per spec plus the
  coderabbit-driven input-boundary guard (TASK-7); landing record at
  `landings/PLAN-06.md` with a complete facts block. Residue on record:
  override push basis, unenriched metrics floor, missing kind=change rows,
  mailbox probe flip (folded into PLAN-10 D2 note).
- **PLAN-15 shipped 2026-09-24 (PR #1618, merge e37e4720).** All 6 deliverables
  per spec plus review-driven hardening (R1–R4 bypass closures, decision-table
  tests); landing record at `landings/PLAN-15.md`. Landed via operator paste
  (no kind=landing message queued — reconciled against PR ground truth).
  Overrides and disclaimed out-of-scope defects on record as reported.
