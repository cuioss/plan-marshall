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

<!-- GENERATED BLOCK — never hand-write or hand-edit this section.
     Regenerate after every queue-touching state change via:
     python3 .plan/execute-script.py plan-marshall:plan-orchestrator:orchestrator resume-summary --slug process-compliance
     Paste the returned `summary` block verbatim between the markers (the same
     invocation also emits `ordered_queue` for the Ordered Queue section below).
     Anything a reader wants to add BY HAND goes in the annotation zone below,
     outside the markers — never inside them. -->

<!-- BEGIN GENERATED: resume-summary -->
**Resume anchor**: Landing 3 done (PR1604 merged 5689afcd, main pulled); 2 fresh filings queued. Next: drain inbox.
**Phase**: orchestrating
**Inbox (derived)**: 1 queued, 115 archived
**Queue** (staged, in order):
1. PLAN-08 (WS-03)
2. PLAN-09 (WS-03)
3. PLAN-10 (WS-01)
4. PLAN-11 (WS-06)
5. PLAN-12 (WS-05)
6. PLAN-13 (WS-07)
7. PLAN-14 (WS-04)
- PLAN-01 (WS-01) — plan=phase-gates — PR 1540 — landing=landings/PLAN-01.md — status: shipped
- PLAN-02 (WS-02) — plan=plan-02-worktree-discipline — PR 1547 — landing=landings/PLAN-02.md — status: shipped
- PLAN-03 (WS-03) — plan=compliant-paths — PR 1542 — landing=landings/PLAN-03.md — status: shipped
- PLAN-04 (WS-04) — plan=plan-04-persona-behavior — PR 1556 — landing=landings/PLAN-04.md — status: shipped
- PLAN-05 (WS-05) — plan=implement-dispatch-envelopes-process-compliance — PR 1583 — landing=landings/PLAN-05.md — status: shipped
- PLAN-06 (WS-05) — status: launched
- PLAN-07 (WS-06) — plan=plan-07-opencode-repairs — PR 1554 — landing=landings/PLAN-07.md — status: shipped
- PLAN-15 (WS-06) — status: launched
<!-- END GENERATED: resume-summary -->

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

<!-- GENERATED BLOCK — never hand-write or hand-edit the table between the markers.
     Regenerated from status.json and the staged specs: emitted as `ordered_queue` by
     orchestrator.py resume-summary --slug process-compliance, and rewritten in place by the
     compact stage at cleanup. Only the LIVE queue is rendered here. Per-row notes a reader
     wants to ADD go in the annotation zone below, outside the markers. -->

<!-- BEGIN GENERATED: ordered-queue -->
| # | Plan | Workstream | Status | Surface (expected) |
|---|------|------------|--------|--------------------|
| 1 | PLAN-06 | WS-05 | launched | marketplace/bundles/plan-marshall/skills/execute-task/scripts/inject_project_dir.py; marketplace/bundles/plan-marshall/skills/phase-5-execute/standards/operations.md; marketplace/bundles/plan-marshall/skills/phase-6-finalize/standards/dispatch-inline-split.md; test/plan-marshall/phase-5-execute/ |
| 2 | PLAN-08 | WS-03 | staged | marketplace/bundles/plan-marshall/skills/tools-integration-ci/; marketplace/bundles/plan-marshall/skills/workflow-integration-github/ |
| 3 | PLAN-09 | WS-03 | staged | AGENTS.md; marketplace/bundles/plan-marshall/skills/plan-orchestrator/SKILL.md; marketplace/bundles/plan-marshall/skills/plan-orchestrator/scripts/orchestrator.py; test/plan-marshall/plan-orchestrator/ |
| 4 | PLAN-10 | WS-01 | staged | marketplace/bundles/plan-marshall/skills/phase-1-init/; marketplace/bundles/plan-marshall/skills/plan-marshall/; marketplace/bundles/plan-marshall/skills/plan-marshall/workflow/planning.md; marketplace/bundles/plan-marshall/skills/plan-orchestrator/scripts/_orchestrator_inbox.py; test/plan-marshall/plan-marshall/; test/plan-marshall/plan-orchestrator/ |
| 5 | PLAN-11 | WS-06 | staged | marketplace/bundles/plan-marshall/skills/phase-6-finalize/; marketplace/bundles/plan-marshall/skills/plan-orchestrator/scripts/orchestrator.py; test/plan-marshall/phase-5-execute/; test/plan-marshall/plan-orchestrator/ |
| 6 | PLAN-12 | WS-05 | staged | marketplace/bundles/plan-marshall/skills/manage-locks/scripts/merge_lock.py; marketplace/bundles/plan-marshall/skills/manage-status/scripts/manage-status.py; marketplace/bundles/plan-marshall/skills/phase-6-finalize/standards/branch-cleanup.md; marketplace/bundles/plan-marshall/skills/plan-retrospective/; marketplace/bundles/plan-marshall/skills/tools-integration-ci/scripts/ci.py; marketplace/bundles/plan-marshall/skills/tools-integration-ci/standards/pr-review-operations.md; test/plan-marshall/manage-status/ |
| 7 | PLAN-13 | WS-07 | staged | marketplace/bundles/plan-marshall/skills/phase-6-finalize/SKILL.md; marketplace/bundles/plan-marshall/skills/phase-6-finalize/standards/archive-plan.md; marketplace/bundles/plan-marshall/skills/phase-6-finalize/standards/dispatch-inline-split.md; marketplace/bundles/plan-marshall/skills/phase-6-finalize/standards/emit-landing.md; marketplace/bundles/plan-marshall/skills/phase-6-finalize/workflow/create-pr.md; marketplace/bundles/plan-marshall/skills/platform-runtime/scripts/session_binding.py; test/plan-marshall/phase-6-finalize/ |
| 8 | PLAN-14 | WS-04 | staged | marketplace/bundles/plan-marshall/skills/persona-plan-marshall-agent/; test/plan-marshall/persona-plan-marshall-agent/ |
| 9 | PLAN-15 | WS-06 | launched | .opencode/commands/; marketplace/bundles/plan-marshall/skills/platform-runtime/scripts/opencode_runtime.py; opencode.json; test/plan-marshall/platform-runtime/ |
<!-- END GENERATED: ordered-queue -->

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

## Open Defects

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

## Watches

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
