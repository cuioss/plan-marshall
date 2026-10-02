# Epic: Process compliance — make rule-following structural, especially on opencode

slug: process-compliance

> Ledger document for one epic under `.plan/local/orchestrator/process-compliance/`. The layout
> and authority contract live in the central standard — see
> `persona-plan-orchestrator/standards/orchestration-model.md`. `status.json` is the
> machine authority; any statement here that conflicts with it is stale prose.

## Vision

Across three shipped finalize-machinery plans, every run observed the same governing
pattern: prevention failed everywhere, detection-and-correction worked everywhere.
Agents rationalized around prose rules (five simultaneously in force), fell back to
improvisation wherever the compliant path did not cover the use case, and needed
repeated nudges for invariants already recorded as active corrections — worst on the
opencode target, where Claude affordances (session identity, transcripts, hooks) do
not exist and the abstraction leaks them as hard blocks. This epic moves each guard
from the boundary where the damage is already done to the earliest point where the
deviation is decidable, so rule-following is structural rather than disciplinary.
Too large for one plan: it spans transition gates, worktree machinery, generator and
wrapper contracts, dispatch registries, persona behavior rules, and opencode-specific
abstraction repairs. Done looks like a run that cannot skip phases, cannot dirty
main, cannot invent invocations, and cannot strand on missing Claude concepts —
with every remaining gap a logged, visible exemption rather than a silent slip.

## START HERE

### Annotations

<!-- ANNOTATION ZONE — hand-written, and deliberately OUTSIDE the generated markers. -->

- **Scaffolded 2026-09-17, NOT yet decomposed.** Next action is
  `/plan-orchestrator decompose slug=process-compliance`, working from the inherited
  material below. `parallelization_scope` is 1 (sequential) per operator answer.
- **Deliberately excluded from decompose input:** the session-identity fix itself
  (staged as PLAN-07 in finalize-machinery — this epic references it, never re-stages
  it); the argparse-rejection class (shipped as PR #1507); review-currency (shipped
  as PR #1510); the merge-gate holes (shipped). Decompose must not re-stage shipped
  work — it stages the structural guards below.
- **Standing emit convention (operator direction 2026-09-18, strengthened
  2026-09-22).** Every emitted `/plan-marshall` command appends: "Comply strictly
  to the process rules. All issues with the process rules, file into
  `.plan/orchestrator/process-compliance/inbox`. Non compliance is not faster
  but a complete failure." Evidence: ~6 runs, much better with the base lines
  than without; with the third line (operator report 2026-09-22, PLAN-06/15
  running) no ignored-process issues in general — not perfect yet (see Watches).

## Ordered Queue

### Queue annotations

<!-- ANNOTATION ZONE — hand-written, and deliberately OUTSIDE the generated table markers. -->

- **Transfer-in 2026-09-19 (operator direction): PLAN-08-process-contracts (WS-03,
  staged).** Eight plan-lane contract lessons from the quality-aspect full-corpus
  ingestion (the nine 2026-09-03-02-0xx process lessons minus basetemp, which went
  with test-quality PLAN-180 as single owner). Documented-lane vs built-lane gaps
  are compliant-path coverage, owned by WS-03. No overlap with staged WS-01–WS-06
  surfaces. Lesson evidence at
  `.plan/local/orchestrator/quality-aspect/lessons-archive/`; per-lesson homes in
  quality-aspect's `lessons-disposition.md`.
- (Also reconciled by this regen: PLAN-01 row now renders launched, matching
  status.json; the prior table still read staged.)
- **PLAN-01 shipped 2026-09-19 (PR #1540, squash 433d0a6).** Gate + exemption + tests + docs per spec; landing record at `landings/PLAN-01.md`. Light-lane 2-refine adoption follow-up (Open Defects) is now unblocked — candidate docs-adoption pass or staged follow-up, not a PLAN-01 re-scope.
- **PLAN-02 shipped 2026-09-19 (PR #1547, squash 895694e3).** All 4 deliverables per spec incl. in-run wiring closure (dispatch seams pass the flag — verified at HEAD) and review-driven hardenings; landing record at `landings/PLAN-02.md`. Mid-flight watches below retired by this landing.
- **PLAN-03 shipped 2026-09-20 (PR #1542, merge 1e2aa916).** All 4 deliverables per spec incl. 4 review loop-back hardenings; both hypotheses re-corroborated at merge HEAD via set-verdict; landing record at `landings/PLAN-03.md`. Residues recorded in the landing (review-gap 3-file delta, token floor, uv.lock churn).
- **PLAN-07 shipped 2026-09-20 (PR #1554, merge e8a7165).** Surrounds only (resolver untouched): degrade paths, sentinel, distinct consent prompt; claims 0–3 re-corroborated at merge HEAD; landing record at `landings/PLAN-07.md`. Residues recorded in the landing (duplicate-PR account, session override, sonar closure, body embellishment).
- **PLAN-04 shipped 2026-09-21 (PR #1556, squash ed90328).** All 4 deliverables per spec incl. review-driven correction-memory mechanism; claims 0–2 re-corroborated at merge HEAD; landing record at `landings/PLAN-04.md`. Reconciled post store-tier migration (tree relocated to the tracked tier per operator direction).
- **PLAN-12 shipped 2026-09-29 (PR #1654, merge 26f864b; #1653 closed by the CodeRabbit close-and-reopen
  recovery).** All defect deliverables per spec, each with a regression test. Landing record at
  `landings/PLAN-12.md`. The landing message was complete, but its `pr=#1653` is a stale create-pr fact,
  so the row carries 1654 (the root cause is staged as PLAN-24 D4). Main was merged into the branch to
  resolve a `plan-retrospective/SKILL.md` conflict with #1651: an undeclared overlap between PLAN-12 and
  PLAN-13, recorded, with no spec correction owed. Self-review ran 12 iterations and closed by
  operator override.
- **PLAN-24…27 staged 2026-09-29** from PLAN-12's 22 further messages:
  - PLAN-24 review and PR record integrity;
  - PLAN-25 build-routing integrity;
  - PLAN-26 git and worktree contracts;
  - PLAN-27 execute guards and dispatch header.

  PLAN-16/19/20/21/23 took recurrence folds. The staged corpus is now 12 specs: PLAN-10 and PLAN-16 to 27.
- **PLAN-13 shipped 2026-09-28 (PR #1651, merge c56710b).** All 5 deliverables per spec, each with a
  regression test, plus an operator-approved ~40-file stale-path sweep outside the declared surface.
  Landing record at `landings/PLAN-13.md`; the landing message was complete (`landing-check`). Residue:
  self-review ran into the 5/5 loop-back ceiling, the closing round was waived, the head-dependent
  re-fires were skipped, and the merge ran under `barrier-ask-override` — all now staged as PLAN-20 /
  PLAN-21.
- **PLAN-19 / PLAN-20 / PLAN-21 staged 2026-09-28** from the PLAN-13 run's 22-item report. PLAN-20 and
  PLAN-21 share `phase-6-finalize/SKILL.md` and `standards/`, so run them in sequence: PLAN-20 after
  PLAN-12 lands, then PLAN-21.
- **Store-tier migration 2026-09-21 (operator direction).** Tree moved `.plan/local/orchestrator/process-compliance/` → `.plan/orchestrator/process-compliance/` completing the #1558 intent for this epic. Standing emit-convention inbox path is now `.plan/orchestrator/process-compliance/inbox`.

## Decisions

- **Epic opened 2026-09-17 at operator direction** ("drain the messages, gather all
  related to improper following of rules — in general, but especially opencode — and
  create a new orchestrator of it"). Split out of finalize-machinery rather than folded
  into it: finalize-machinery retires finalize-lane defects, while this material is
  about the process machinery itself (guards, contracts, registries, persona rules)
  across all lanes. The 6-message drain that fed this epic promoted 5 corpus lessons
  (2026-09-17-19-004..008) and folded 1 recurrence into finalize-machinery PLAN-07.
- **parallelization_scope=1** (operator answer, 2026-09-17; project default suggested
  1): process-machinery specs touch shared guards and registries — strictly sequential
  until decompose proves disjoint surfaces.
- **parallelization_scope raised 1 → 2** (operator direction 2026-09-18, after
  PLAN-01 launch, to open a parallel slot). The gate still admits per candidate:
  an indeterminate live surface sequences rather than emits.
- **Cross-epic routing agreement noted (drain 2026-09-18, `finalize-machinery-001`).**
  finalize-machinery routes every rule-following finding matching this epic's
  relevance test here instead of absorbing locally; source messages stay archived
  there. Backfill owed nothing (Inherited Material A–H already holds it).
- **Scope ruling (drain 2026-09-18, `git-branch-mechanics-001` item 2).** The
  session-identity hard-block (telemetry-only input gating the shipping pipeline)
  is owned by finalize-machinery PLAN-07 (the resolver itself); this epic
  references that plan and never re-stages it. No spec here takes it.
- **2026-09-26 — PM-MCP supersedes Python- and prose-bound plan work (operator
  decision, relayed by review-apparatus inbox `review-apparatus-001`, amended).**
  `plan-marshall-mcp` replaces both the process prose and the Python scripts; only
  implementation-independent content (rules, invariants, classifications, data,
  fixtures) carries. All 7 staged rows (PLAN-08 … PLAN-14) were re-triaged per
  deliverable and **parked**, each with a `SUPERSEDED BY PM-MCP` banner; bodies kept
  as the evidence chain. The extraction is filed (operator-authorized single write,
  uncommitted — the operator commits it) at
  `/Users/oliver/git/plan-marshall-mcp/doc/known-defects/process-compliance-carry-over.md`
  against PM-MCP HEAD `7e13ea1`: 104 spec rows → 50 carried (10 gap / 30 partial /
  10 covered), plus 25 inbox-routed rows → 20 carried. Contradictions: 10.C-dirt
  (Clean Main Checkout Guard is absolute and its recovery reverts foreign dirt),
  08.D5 (PM-EXT-7 re-composes an in-flight manifest), 13.D4 (`pr_title` fixed at
  refine); plus 14.D5 as a cross-epic duplicate of review-apparatus's zero-findings
  contradiction. Quotes re-verified at `7e13ea1`; rows are sub-agent derivation, not
  re-verified line by line. **No emission exception confirmed.** Candidates held for
  operator decision only: PLAN-12 D3 (merge-lock `--hold-start` float vs instant —
  would block merges if a real reclaim fails) and PLAN-13 D3 (forked-finalize cwd,
  unverifiable, finalize runs inline today). No emitted-but-not-launched command
  existed, so nothing was voided. ⛔ Consequence for this ledger: every "candidate
  future staging" Open Defect below is no longer stageable as Python/prose work —
  its knowledge routes to the carry-over, not to a new spec.
- **2026-09-26 — PLAN-12 and PLAN-13 un-parked (operator: "stage 12 and 13").**
  Both re-staged in full as operator-confirmed exceptions under the
  delivery-breaking class (candidates PLAN-12 D3 merge-lock `--hold-start`,
  PLAN-13 D3 forked-finalize cwd); banners rewritten to UN-PARKED, the carry-over's
  emission-exception section updated. Staged whole, not narrowed to D3 — the
  operator's instruction named the plans. PLAN-08/-09/-10/-11/-14 stay parked.

- **2026-09-27 — operator directive: current problems are FIXED, not relayed to
  PM-MCP.** Supersedes the 2026-09-26 practice of routing process findings to the
  carry-over only. Drain of 6 messages (plan-12-tool-triage-001..005,
  plan-13-finalize-mechanism-defects-001): PLAN-10 UN-PARKED (parked→staged) and
  folded the mailbox-probe mis-parse (root cause confirmed at HEAD) and the
  file-pointer `--request-text` gap; PLAN-16 `init-lane-fidelity` STAGED for posture
  prose / lane_report, session_ids at init, scope-estimate provenance, domain-detect
  provenance, and the absent Grep/Glob fallback. Late arrival
  plan-13-finalize-mechanism-defects-002: item 1 folded into PLAN-10; items 2-3
  STAGED as PLAN-17 `concurrent-plan-isolation` (clean-main assertions trip on
  sibling/orchestrator writes; shared `.plan/temp/module_mapping.toon`). PLAN-10,
  PLAN-16, PLAN-17 pairwise overlap — sequence, do not parallelize.

## Inherited Material — the decompose input

> ↪ Relocated to `settled.md` § "Inherited Material — the decompose input" — the decompose hand-off; every item became PLAN-01…07, all shipped.

## Incorporated lessons (moved from shared corpus at operator direction)

> ↪ Relocated to `settled.md` § "Incorporated lessons (moved from shared corpus at operator direction)" — all 13 lessons landed with their shipped target plans.

## Open Defects

- **#1641 (`945e59287`, "cross-epic ledger sync") reverted ledger state across 9
  epics (found 2026-09-28, this epic RESTORED).** Its body claims it held back 20
  deletions with no verifiable successor; the squash deleted exactly those 20
  files, and stripped every PM-MCP-supersession banner, `epic.md` decision entry
  and anchor block that #1643 (`88fcfc9ef`) had landed. Here: both 2026-09-26
  decision entries, 7 spec banners, PLAN-08/-09/-11/-14 `parked` → `staged`, two
  consumed inbox messages un-archived, archived `review-apparatus-001` deleted.
  Restored from `88fcfc9ef` by the landing PR for the 2026-09-28 drain (operator
  choice: restore this epic only). The other 8 epics (code-intelligence-substrate,
  instrumentation-substrate, lessons-routing, orchestrator-refactor,
  post-run-quality, review-apparatus, test-quality, truthful-signals) were each
  sent an inbox finding naming their reverted files and the restore source.
  Mechanism class: a stale-base ledger sync overwrote a newer landing — worth a
  guard (a ledger sync must refuse to delete or revert a path changed on main
  since its base).
- **2026-09-26 — THE STAGED QUEUE IS PARKED (PM-MCP supersession, see
  Decisions).** PLAN-08/-09/-10/-11/-14 parked; PLAN-12 and PLAN-13 re-staged by
  operator decision the same day. Un-park the rest only by explicit operator
  decision. Owed follow-up: the unowned "candidate future
  staging" defects in this section were NOT part of the extracted population
  (the procedure covered staged/parked rows); route their invariants into the
  carry-over file as an addendum, or record them as `none`, before this epic
  closes.
> ↪ Relocated to `settled.md` § "Open Defects — closed (relocated 2026-09-28)" — 5 entries whose subject is closed (six invalid messages resolved, 2026-09-21 partial drain closed, 2026-09-22 bypass story closed by PR #1582, `opencode-bootstrap-executor-fix-003` recovered and staged as PLAN-23 on 2026-09-29).

- **Self-review verifier close-out has no contract exit (drain 2026-09-18,
  `git-branch-mechanics-001` items 4+5, unowned).** Two identical accepted-clean
  rounds on an unchanged HEAD still answer `may_close: no` on incurable grounds;
  closing required overwriting the measured `no` with `yes`, so the override reads
  as the verdict. Proposed: same-surface detector (identical candidate digest +
  unchanged HEAD seals prior acceptance) or a distinct `may_close=waived` marker
  with reason reference. No owning spec (verifier contract is neither dispatch
  envelope nor roster); candidate future staging.
- **Condensed-inline lane undocumented (drain 2026-09-18,
  `plan-06-anchors-and-mutex-001` item 2, unowned).** Phases 2–4 ran inline in the
  orchestrator context with no per-phase dispatch envelope and `AskUserQuestion`
  resolved to projected `standard` without prompting — lifecycle artifacts still
  produced, but no topology rule admits or forbids it. Proposed: document the
  condensed-inline lane as allowed for single-session orchestrated executions, or
  fail transitions with no dispatch envelope observed. No owning spec; candidate
  future staging.
- **Executor verb registration is a silent second gate (drain 2026-09-18,
  `plan-06-anchors-and-mutex-001` item 3, unowned).** A new verb existed in code
  and passed unit tests yet the executor refused `unknown_verb` until mapping
  regeneration — invisible producer-side. Proposed: contract test asserting every
  argparse subcommand of every executor-mapped script resolves through the
  generated executor, or document regeneration as a required verb-adding step. No
  owning spec; candidate future staging.
- **Light-lane 2-refine adoption follow-up (paste 2026-09-18,
  `phase-gates-001` item 2, unowned while PLAN-01 flies).** Light-lane
  `planning.md` closes 2-refine via transition with no refine artifact, which the
  new gate refuses as `refine_bare_transition` — the caller must adopt
  `--allow-bare-transition --bare-reason` or produce a clarified record, and no
  change was made (outside PLAN-01's surface). Blocked on PLAN-01 landing; then
  either a docs-adoption pass or a staged follow-up. PLAN-01's spec is not
  re-scoped mid-flight.
- **Emit-path hand-off non-idempotent (drain 2026-09-21,
  `phase-gates-004.md` item 1, unowned).** A re-issued hand-off command carries no
  plan pointer and re-enters init derivation (duplicate plan) unless the
  exists-collision prompt saves it — bypassed on non-interactive runs. Proposed:
  emit with the `plan=` pointer once launched, or an init guard that auto-resumes
  on `source_id` match. Items 2–3 of the same message (queue back-pointer, stale
  anchor) were fixed in-run. No owning spec; candidate future staging.
- **phase-1-init doc invents `--request-text` (drain 2026-09-21,
  `compliant-paths-002.md`, unowned).** Live `--help` rejects the flag the doc
  prescribes for `domain-detect`. Doc fix; candidate future staging.
- **Sanctioned move-in cannot take a pre-existing branch (drain 2026-09-21,
  `test-fidelity-rules-004.md`, unowned).** Move-to-worktree gap plus its move-back
  sequel (`-005`) and uv.lock restore note (`-006`, absorbed). Candidate future staging.
- **Installed skill copy carries no workflow documents (drain 2026-09-21,
  `test-fidelity-rules-follow-up-002.md`, unowned).** Skill-packaging gap; candidate
  future staging.
- **Incomplete landing message (drain 2026-09-22,
  `implement-dispatch-envelopes-process-compliance-003.md`, open).** Narrative-only
  landing, no `landing-facts` block (`missing_keys`: schema, plan_id, pr,
  merge_state, cleanup_owed, deliverables_total, deliverables_done,
  total_tokens, steps). Reconciled as far as it goes against PR #1583 ground
  truth; a manual paste from that plan could still surface a required fact the
  inbox did not carry.
- **q-gate §2.2 unsatisfiable on the light lane (drain 2026-09-23,
  `implement-opencode-enforcement-parity-004.md`, unowned).** Two facets:
  the 4-plan leaf ran §§2.1–2.7 over a dispatched subset of §§2.11/2.12
  (subset scope not enforced as hard scope), and §2.2 assessments are
  produced only by deep-lane analysis, so ANY light-lane plan flags every
  file permanently. Candidate future staging (subset-scope enforcement +
  light-lane carve-out or assessment-producing envelope step).
- **Ledger-gate absolute-cleanliness vs concurrent ledger churn (drain
  2026-09-23, `module-budget-campaign-completion-001.md` issue 2, `-002.md`,
  `-003.md`, open — parked awaiting operator disposition).** Post-init,
  post-refine, and handshake-verify gates refuse on any porcelain dirt, but
  the dirt is operator-ledger state (drain/archive/status) the phase leaf
  cannot author and, for mid-run drift, cannot prevent. Suggested shape:
  scope assertions and the `main_dirty` invariant to non-ledger paths, or
  compare before/after per dispatch; alternatively a quiesce rule pausing
  ledger reconciliation at phase boundaries. Plan parked at 2-refine, no
  transition taken — compliantly.
- **Recurrences drain 2026-09-23 (folded here, still open).** `plan-06-003`
  (PLAN-06 stopped at the post-refine gate on concurrent ledger churn,
  asking); `truth-147-002` (post-init gate fired on the run's own sanctioned
  inbox filing — compliance self-incriminates); `truth-179-003` (post-init
  gate on concurrent dirt + own filings + the untracked staged spec itself,
  disposition requested before 2-refine). Same ask in all three: attribute or
  scope the gate, or grant an explicit advance-with-dirt-named disposition.
- **Footprint helpers read stale local base (drain 2026-09-21,
  `test-fidelity-rules-follow-up-009.md`, unowned).** Should resolve the merge base;
  candidate future staging.
- **Opencode cache shadowing poisons executor and imports (drain 2026-09-24,
  `plan-06-dispatch-roster-006.md`, `truth-147-lane-reports-green-004.md`,
  `module-budget-campaign-completion-005.md`,
  `truth-179-opencode-target-detection-landed-004.md` half 2, open).** One
  family, three surfaces: target-blind regen writes claude-target executor
  mappings from opencode roots (breaks the next call); flat-layout cache dirs
  precede tree dirs on the executor sys.path so `resolve_bundles_root` raises
  for cache-resolved modules (all `manage-config` verbs down, machine-global);
  the step-15 regen call carries no repo-anchoring. Operators recovered
  in-run (direct regen with root + target; generated-file sort-key patch).
  Candidate future staging (target-aware regen + layout-aware resolver).
- **Executor-regen poisoning: worktree-blind enumeration + cache slurp (drain
  2026-09-24, `implement-opencode-enforcement-parity-006/007.md`, open).**
  `diff-modules` reports bundle-backed modules as removed under worktree
  `--project-dir` (same call clean on main); the regression gate attests
  `regressive: false` over 2 examined of 10 deleted. Separately, fresh
  regeneration registers ~160 plugin-cache shadows, making shorthand
  resolution ambiguous and the whole-tree gate false-red. Candidate future
  staging (single reader + fail-closed partial coverage + no-shadow
  registration).
- **Recurrence drain 2026-09-24 (`implement-opencode-enforcement-parity-008.md`,
  folded here).** On-main regen via sync-plugin-cache wrote an executor that
  crashes every call (`plan_logging` unresolvable in cache context) — total
  lockout recovered via direct-path bootstrap. New facet beyond the defect
  above: no fail-safe caught it (py_compile guards syntax, not runtime
  imports). Fails the defect's premise upward: smoke-import before atomic
  replace, or pin `--marketplace` context.
- **Scope-creep guard unsatisfiable on worktree plans (drain 2026-09-23,
  `implement-opencode-enforcement-parity-005.md`, unowned).** Two independent
  defects: the diff base (`plan_creation_sha` at init) predates worktree
  materialization, so upstream merges count as residual (49 files, zero
  plan-authored); and the emission type `scope_creep_warning` is not a member
  of `FINDING_TYPES`, so a genuine hit can never be persisted — the guard can
  only fail. Candidate future staging (merge-base basis + registered emission
  type); documented knobs (re-anchor sha, threshold) are the interim unblocks.
- **q-gate §2.2 unsatisfiable on the light lane (drain 2026-09-23,
  `implement-opencode-enforcement-parity-004.md`, unowned).** The 4-plan leaf
  ran §§2.1–2.7 over a dispatched subset of §§2.11/2.12 (subset not enforced
  as hard scope), and §2.2 assessments exist only on the deep lane — any
  light-lane plan flags every file permanently. Candidate future staging
  (subset-scope enforcement + light-lane carve-out).
- **PLAN-05 run filings (drain 2026-09-22,
  `implement-dispatch-envelopes-process-compliance-001/002.md`, unowned).**
  Six actionable items, all candidate future staging: `request.md` Step 5.2
  full-file Write clobbers the allocator stub frontmatter (reported twice —
  recurrence folded here — `clarified_request`/`original_input` lost, fix is
  append-body-only wording); description-source plans carry no `source_id`,
  so the mailbox probe reads `not_orchestrated` (two-way routing needs a
  defined linkage path); freshness `build_scope_narrow` refuses
  module-scoped builds (whole-tree verify per push doubles cost — document
  the demanded canonical+scope per footprint class); loop-back envelope
  `blocked` over an empty queue is ambiguous (distinguish
  blocked-with-work from blocked-empty); triage stamps no
  `predicted_cost_tokens`, so loop-back `pack-envelopes` refuses (stamp at
  allocation or default it); light-lane pre-dispatch needs two undocumented
  exemptions (`--allow-bare-transition`, seeded `pr_title`). Observed-only
  (no defect): pre-init direct `.plan` reads (reads-only, self-contained);
  dirty-main override and merge-anyway grant (operator decisions on record).
- **Recurrence drain 2026-09-23 (`plan-06-dispatch-roster-002.md`, folded
  here).** Pre-init direct `.plan` reads again, self-reported, reads-only —
  third instance of the pattern. No new defect; the pattern's home remains
  the persona-conduct surface (PLAN-14) and the opencode guard (PLAN-15).
- **Recurrence drain 2026-09-23 (`carried-defects-and-watches-closure-002.md`
  item 1, folded here).** Structured-queries-first bypass (straight to
  Grep/Glob, minor, no impact observed) — fourth instance class of the
  read-path discipline pattern.
- **verification-feedback producer accept-set rejects `ci-verify-build` (drain
  2026-10-02, `truth-168-003` item 8, unowned).** `ci_verify run` returns
  `producers: [ci-verify-build]` with a one-invocation-per-producer contract,
  but the verification-feedback guard accepts only build-runner, sonar,
  pr-comment, plugin-doctor, pr-state, finalize-feedback. Red-CI triage
  dead-ends; workaround `producer=pr-state`. Candidate: widen accept-set or
  document taxonomy-to-producer mapping at the call site. No owning spec
  (closest PLAN-19 verification-loop, not yet widened); candidate future work.
- **No sanctioned file-scoped pytest on opencode target (drain 2026-10-02,
  `truth-168-003` item 9, unowned).** R4 guard refuses bare pytest, wrapper
  offers only whole-bundle module-tests (~20 min vs ~330s daemon cap). No
  sanctioned re-run of touched test files after settle-band edits; CI is the
  authoritative runner. Candidate: file-scoped suite surface or documented
  exemption. No owning spec; candidate future work.
- **Footprint gate treats `.plan/marshal.json` as docs-only (drain 2026-10-02,
  `truth-168-003` item 10, unowned).** Steward landing #1677 skipped verify,
  left main red on the canonical-order test. Candidate: treat
  `.plan/marshal.json` as buildable or gate steward artifact landings on
  verify. No owning spec; candidate future work.
- **Re-filed `opencode-bootstrap-executor-fix-003.md` cannot archive (drain
  2026-10-02, `archive_conflict`, open).** The live `inbox/` file carries the
  same name as the already-archived staging source of PLAN-23, and the archive
  verb refuses to clobber the audit record. Disposition stands (folded into
  PLAN-23 at staging; recurrence noted in this drain's Watch entry) and is NOT
  re-applied. Recovery is operator-side: retire the live file via `inbox archive
  --as-name` under a non-colliding sender-preserving name. Left un-archived by
  design so it stays visible to the next drain.

## Watches

- **Drain 2026-09-29 (PLAN-12 landing plus 23 messages).**
  - Reconciled: `-013` (the landing).
  - Staged into new specs: `-012`, `-014`, `-015`, `-019`, `-021`, `-028`, `-029`, `-030`, `-031`,
    `-032`, and parts of `-017`, `-025` and `-027` (PLAN-24…27).
  - Folded as recurrences: `-010`, `-011`, `-016`, `-018`, `-020`, `-022`, `-023`, `-024`, `-026`,
    and the remaining parts (into PLAN-16/19/20/21/23).
  - Routed: `-009` to post-run-quality (`process-compliance-003`, the second PRQ-12 recurrence), because
    PRQ-12 is the one live sibling owner. review-apparatus and truthful-signals are fully parked, so
    PR/review material was kept here.
  - Reclaimed from the PM-MCP carry-over under the 2026-09-27 directive: MB06 (→ PLAN-27), MB07
    (→ PLAN-21), MB10 (→ PLAN-26).

- **⛔ Dead-end routing corrected (2026-09-29).** The 2026-09-28 routing of PLAN-13 report items 5, 21
  and 22 and the `-006` step-id lesson to truthful-signals (`process-compliance-002`) targeted
  PLAN-TRUTH-169 / 150 / 205 / 175. All four are **parked** under the PM-MCP supersession: the
  `staged` status seen at routing time was #1641's reverted state, which #1656 undid. No plan would
  have acted on them. They are reclaimed here: items 5, 21 and 22 → PLAN-23 push-boundary-evidence;
  step-id → PLAN-21 D5c. truthful-signals was notified (`process-compliance-003`). The PRQ-12 routing
  (`post-run-quality`, staged) is unaffected. **Rule for future routing:** re-read the target row's
  status at routing time. A parked or superseded target is not an owner.

- **Drain 2026-09-28, second pass (PLAN-13 landing + 3 messages).** `-007` landing reconciled
  (shipped). `-004`'s 22 items: 17 staged as PLAN-19/20/21; items 5, 21 and 22 routed to
  truthful-signals (`process-compliance-002`: TRUTH-169, TRUTH-150/205); item 12 discarded as shipped
  (#1651's sweep) — ⛔ **that verdict was WRONG, corrected the same day.** The verifying grep covered
  `marketplace/bundles` and the `.plan/plans/` form only. `-008` then reported residue in `test/`,
  `doc/` and the `.plan/logs/` / `status.toon` classes, and the item is now **staged as PLAN-22
  runtime-state-path-migration**. The two sweeps disagree on the population (sender 7/2/15 files,
  orchestrator grep 84/23/201), so PLAN-22 derives it itself. Run PLAN-22 alone: its surface is
  repo-wide. Candidate lessons: `-005` routed to post-run-quality as a PRQ-12 recurrence, `-006`
  routed to truthful-signals as a TRUTH-175 recurrence (`--step-id` facet). Inbox empty.
> ↪ Relocated to `settled.md` § "Watches — settled (relocated 2026-09-28)" — 15 entries about shipped plans (PLAN-01/02/05/06/13/15) and closed drains 2026-09-18…26; refutations stay reachable there.

- **Drain 2026-09-28 (4 findings, standing directive "fix, not relay").**
  `plan-12-tool-triage-006` + `plan-13-…-003` §3 → folded into PLAN-17 D1
  (porcelain assertion vs handshake exemption set; +`planning-outline.md`,
  +`phase-handshake.md` surface) and new PLAN-17 D3 (blocking count unreconciled
  with buckets). `plan-12-…-007` (leaf self-transition), `-008` (no hash verb;
  Step 9c rule vs example), `plan-13-…-003` §1/§2/§4a/§4b → **staged PLAN-18
  outline-lane-contracts**. Recurrences with no surface change: Grep/Glob
  unavailable (PLAN-16 D5), `not_orchestrated` probe (PLAN-10). Queue order for
  the planning-lane cluster: PLAN-17 → PLAN-18; PLAN-10 / PLAN-16 also share
  `planning.md` / `phase-1-init/`.

- **PLAN-13 run's "not orchestrated" report — cause REFUTED, symptom CONFIRMED
  (drain 2026-09-27).** The run blamed the `PLAN-13-…` filename lacking a code
  segment; `inbox detect` returns `orchestrated: true` for PLAN-12 and PLAN-13
  (`PLAN-{DIGITS}` is an accepted form), so no rename is owed and `emit-landing`
  (which uses the detector directly) should still file a landing. But the
  phase-transition mailbox probe IS a false negative for every orchestrated plan:
  `_cmd_lifecycle.py` parses request.md with the `key=value` metadata parser,
  which returns `{}` for it. Fix staged in PLAN-10 deliverable 2. Verify at
  PLAN-12/PLAN-13 landing that a `kind: landing` message actually arrives.

- **The inherited set will grow.** finalize-machinery still has PLAN-04 running and
  PLAN-05/06/07 staged; their landings may surface further rule-following material.
  Re-gather at decompose if new landings have arrived — do not treat the set above
  as closed.
- **Operator-reported compliance preamble (absorbed observation, no ship).** The
  operator reports that adding an `## Execution Contract` section to a plan spec
  (binding brief, phased lifecycle via managing skills, verify-first before scoping,
  Write-Boundary, PR + inbox reporting, "process compliance is mandatory, not
  advisory" standing instruction for opencode) plus a plan-call line ("Comply
  strictly to the process rules. All issues with the process rules, file into
  `.plan/local/orchestrator/process-compliance/inbox`") yields "much better"
  compliance than without them. Corroborated as novel: no staged spec in this
  corpus carries either element (grep over `plans/` returns zero hits). Effect size
  is operator-reported, replicated across ~6 runs per operator correction
  (2026-09-18) — repeated observation, not a measured controlled comparison. Implication
  (not yet staged): standardizing the preamble in the plan-spec template and the
  emitted hand-off line is candidate follow-up work — no owning spec exists
  (closest is WS-04 persona behavior, which owns rules, not the template/emit
   format). Revisit at cleanup or on operator direction.
- **Drain 2026-10-02 (9 findings, no landings, no invalid).**
  - `implement-plan-211-baseline-reconcile-001` (finding): direct `.plan` reads before
    sanctioned `corpus read`/`resolve-path`, self-corrected, no ledger mutation.
    Recurrence of the read-path discipline pattern (home: PLAN-14/PLAN-15 surfaces).
    Absorbed as observed; no spec change.
  - `implement-plan-211-baseline-reconcile-002` (finding): PLAN-211 first pass bypassed
    phases 2-4/5/6 with partial verification. Historical record only; superseded by
    the by-the-book redo in `-003`. Absorbed as observed; no spec change.
  - `implement-plan-211-baseline-reconcile-003` (finding): redo by the book (init via
    finalize, PR 1675 merged green, zero actionable review). Noted gap: finalize leaf
    could not issue Task dispatches so 12 orchestrator-owned dispatched sub-steps did
    not run. Recorded as Watch for PLAN-21 consideration; message absorbed as
    observed, no spec change in this drain.
  - `opencode-bootstrap-executor-fix-002` (finding): finalize session-identity resolver
    misclassifies OpenCode-without-session as transcript-capable Claude
    (`hook_not_configured` + `runtime-info harness: claude`). Owned by
    finalize-machinery PLAN-07 (resolver itself) with here PLAN-13 shipped covering
    `session_binding.py`; no re-stage. Absorbed as observed.
  - `opencode-bootstrap-executor-fix-003` (finding): local green `verify` contaminated
    by untracked generated `target/` tree; CI fix already landed on the plan branch
    (pre-verify generate `--target all`). Already staged as PLAN-23 on 2026-09-29;
    this message is the staging source. Folded into PLAN-23 as the source record;
    expected surface unchanged by this drain fold (no new file surface in this message
    beyond PLAN-23 scope — recorded explicitly).
  - `truth-168-sync-defaults-reverting-remove-001` items 1-4 (finding): (1) direct
    `.plan` read recurrence; (2) recipe-match/aspect-classify `--request-text`
    verbatim vs Bash newline rule, workaround single-line title, zero-match
    no-routing-impact; (3) manage-logging parentheses vs R1 guard, dash-only
    workaround; (4) logical-vs-physical store path note, no action. Items 1-2 are
    PLAN-10 deliverable 2/3 recurrences; folded into PLAN-10 as recurrence notes.
    Expected surface unchanged by this fold (phase-1-init/ and probe paths already
    declared — recorded explicitly). Item 3 is an opencode-guard facet with no
    owning staged spec; carried in this Watch entry.
  - `truth-168-sync-defaults-reverting-remove-002` items 5-7 (finding): (5) commit
    trailer angle-brackets vs R1 redirect guard, Python helper workaround; (6)
    `inbox detect orchestrated:true` vs transition mailbox probe `not_orchestrated`
    on the same pointer, PLAN-10 D2 recurrence with confirmed root cause; (7)
    whole-tree module-tests timeout on build server (capacity, not code failure).
    Item 6 folded into PLAN-10 D2 as recurrence; expected surface unchanged
    (`_cmd_lifecycle.py` already declared — recorded explicitly). Items 5/7 carried
    in this Watch entry.
  - `truth-168-sync-defaults-reverting-remove-003` items 8-10 (finding): (8)
    `ci_verify` producer `ci-verify-build` rejected by verification-feedback guard
    accept-set, workaround `producer=pr-state`; (9) targeted pytest guard-blocked,
    no file-scoped suite surface, CI as authoritative runner; (10) pre-existing red
    baseline from verify-skipped steward landing (#1677 `.plan/marshal.json` top-level
    key, canonical-order table stale), repair riding as drive-by. Item 8 belongs to
    PLAN-19 verification-loop scope, items 9-10 to PLAN-25 build-routing scope;
    recorded here as Open-Defect-class observations (see Open Defects) rather than
    spec edits in this drain — absorbed as observed with ownership pointers, no
    surface change.
  - `truth-168-sync-defaults-reverting-remove-004` items 11-13 (finding): owned
    deviations — (11) direct `.plan` reads for diagnosis (no manage-* read verb for
    build logs/config bytes/CI payloads); (12) one-word `runtime.target` restore
    (`antigravity` to `claude`) via direct edit, diff-verified, flagged in PR body;
    (13) two out-of-spec drive-by commits as landing blockers, named in commit
    messages. Auditable deviations, operator review flagged upstream. Absorbed as
    observed; no spec change.
