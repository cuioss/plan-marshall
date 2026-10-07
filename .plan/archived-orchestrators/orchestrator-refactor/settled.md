# Settled: Orchestrator Substrate Refactor

Relocated closed narrative from `epic.md` — the audit record of resolved defects and
retired watches, moved here verbatim by the `cleanup` verb's ledger-compaction stage so
`epic.md` stays focused on live state. A pointer at each origin names the heading here.
See `persona-plan-orchestrator/standards/orchestration-model.md` § Ledger-Compaction Stage.

## PLAN-01 stuck mid-finalize on an unreviewable diff

- ~~PLAN-01 is stuck mid-finalize on an unreviewable diff~~ **RESOLVED 2026-09-21**: the
  split executed — #1557 (code, ~48 files, merged `8c8c7bbf`), #1558 (ledger content, 3,977
  files, `skip-bot-review`, merged `6728b738`), #1555 closed unmerged with a pointer to the
  replacements. A follow-up, #1561, landed a fix for a hardcoded-path finding the split
  missed. See `landings/PLAN-01.md`.

## Epic ledger tree split across two locations

- ~~the epic's own ledger tree split across two locations~~ **RESOLVED 2026-09-21, root
  cause corrected.** PLAN-01's #1558 seeded `.plan/orchestrator/orchestrator-refactor/` as a
  ONE-TIME snapshot at merge time (`updated: 2026-09-20T10:23:39Z`), predating this epic's
  own `cleanup` pass. The two trees then diverged for TWO DIFFERENT reasons, not one: (a)
  during `cleanup` (2026-09-21, before PLAN-01 had landed), this orchestrator's script calls
  correctly resolved to the OLD `.plan/local/orchestrator/` tree, since the new resolver code
  did not exist on disk yet; (b) AFTER PLAN-01 merged into local `main` (confirmed:
  `git log HEAD` matches `origin/main` at `441cc46c8`, so the resolver code WAS current, not
  stale as first suspected), this orchestrator's OWN direct `Write`/`Edit` calls kept
  hardcoding the OLD path out of habit for several turns (the PLAN-01 landing report, the
  PLAN-03 fold, this epic.md's own Open-Defects/Watches edits) — while its SCRIPT calls
  (`queue --transition`, `--set-row`) correctly began resolving to the NEW tree the moment
  local `main` advanced, silently splitting `status.json` from everything else. **Both halves
  reconciled**: `epic.md`, `plans/PLAN-02-*.md`, `plans/PLAN-03-*.md`, `plans/PLAN-06-*.md`,
  and `landings/PLAN-01.md` copied forward into `.plan/orchestrator/orchestrator-refactor/`;
  `status.json`'s PLAN-06 transition (`parked`→`staged`) re-applied via script now that it
  resolves correctly. `logs/decision.log` deliberately stays local-only (by #1557's own
  design: `*/logs/` is re-ignored after the tracking negation, to avoid line-churn conflicts)
  — its absence from the tracked tree is expected, not a gap. **The tracked-tree write is an
  UNCOMMITTED change in the actual git working tree** — this orchestrator does not commit or
  push without being asked; flagging for the operator. Going forward, this orchestrator
  writes directly to `.plan/orchestrator/orchestrator-refactor/` only.

## Restart-check worktree signal reported not_ready

- ~~STILL OPEN — restart-check's worktree signal reports not_ready~~ **RESOLVED
  2026-09-21**: operator approved the commit/push/PR/merge sequence. Landed as PR #1566
  (`3d88b24cf`, `skip-bot-review`, merge queue) — see `landings/PLAN-01.md`. `main`
  pulled locally; `restart-check` now reports `ready` on all 5 scored signals. The old
  `.plan/local/orchestrator/orchestrator-refactor/` tree (21 decision-log entries it
  alone held, since `logs/` is git-ignored) was merged into this tree's log before the
  operator deleted it.

## truthful-signals PLAN-TRUTH-143 running, blocking dependents

- ~~`truthful-signals` PLAN-TRUTH-143 is `running`...~~ **RESOLVED 2026-09-20/21**: shipped as
  PR #1539 (merge `1c56734ce`, 2026-09-20T07:11:51Z). Both dependents unblocked: PLAN-01's
  live-plan collision cleared (it was subsequently launched — see the new Open Defect on its
  own stuck finalize, unrelated to this collision); PLAN-06 re-grounded and re-staged this
  cleanup pass (D2/D3 found moot, D5 narrowed).

## Two orchestrator entities share one word

- ~~Two "orchestrator" entities share one word in this codebase...~~ **RESOLVED by PLAN-04 /
  ADR-023 §(d) "Telling the two tiers apart at the caller surface"** — the epic is `--epic`,
  the plan is `--plan-id`; the two are different tokens on the same parser by construction.
  Retired 2026-09-20.

## 2026-09-28 — #1641 reverted this epic's ledger; RESTORED from `88fcfc9ef`

`process-compliance-001` reported, and a direct diff confirmed, that #1641 (`945e59287`, a cross-epic ledger sync
squash-merged from a branch cut before #1643) reverted 13 paths here: the PM-MCP park (spec banners, 43 lines of
`epic.md`, `PLAN-03/05/06` back to `staged`), the PLAN-09/10 re-scope, the PLAN-11 re-stage note, and it deleted
the archived `review-apparatus-001.md`. `git diff 88fcfc9ef origin/main` over this tree equalled the #1641 diff
exactly (plus the new inbox message), so no legitimate later change existed and all 13 paths were restored
whole from `88fcfc9ef`. **Archetype:** a stale-branch squash silently reverts every file it carries at an older
version; a ledger landing from a branch not cut from current `origin/main` is a revert. Every ledger landing
from this session branches from `origin/main` explicitly.

## Shipped-plan landings, drains and folds (PLAN-01/02/04/05/06/08/10/11, #1685)

- 2026-10-03 — **PLAN-10 landed (#1690, `7a0af07c5`); reconciled via `analyze` (inbox scan, 9 messages).** The
  landing message was complete (`landing-check`: no missing key) and corroborated against `ci pr view` (merged),
  ancestry on fetched `origin/main`, and the merge commit's file list. Row `running` → `shipped`, `pr` and
  `landing` stamped. The spec's D5 HYPOTHESIS (no `ci` verb exposes queue membership) held — the plan added
  `ci pr queue-state` and `ci pr wait-for-queue-settle`. The emit-time overlap with `unified-sync-all-harnesses`
  did not materialize (PLAN-10 never touched the file). No spec's declaration needs correcting — the landed spec
  is terminal and no staged spec remains.
  **Lessons drain (messages -001 … -008):** 3 PROMOTED — `2026-10-03-18-001` (automatic-review: re-trigger a
  `participated_stale` required bot, -002), `-002` (manage-solution-outline: q-gate deliverable-hash verb, -003),
  `-003` (execute-task: orchestrator-tier module-tests block per-task verification, -004; cross-referenced to
  `2026-10-02-10-009`). 5 FOLDED as recurrence sections on active lessons, each verified active and matching
  before writing: `2026-10-02-10-003` and `-004` (-001), `2026-10-02-10-008` (-005), `2026-10-02-10-009` (-006),
  `2026-09-29-17-002` (-007, new trigger: operator-added work mid-execute), `2026-10-02-21-002` (-008). None
  concerns this epic's substrate. Noticed, not acted on: active lesson `2026-09-27-07-001` describes the
  mailbox-probe defect #1685 fixed — a retirement candidate for lessons housekeeping.

- 2026-10-03 — **Phase-transition mailbox probe fixed outside the queue: #1685 (`8aa33cfe1`), an ad-hoc
  operator-run fix, not a plan of this epic.** Found while PLAN-10 ran: its transition probe reported
  `not_orchestrated` although `inbox detect` classified the same pointer `orchestrated`. Cause:
  `_resolve_mailbox_checkpoint` (`manage-status/scripts/_cmd_lifecycle.py`) read `source_id` with
  `file_ops.parse_markdown_metadata`, which reads only leading `key=value` lines and stops at the first blank
  line or heading — a real `request.md` opens with an HTML comment and a `# Request:` heading and writes
  `source_id: …`. So every orchestrated plan was misreported at every phase transition. The test fixture
  pinned the defect by writing `request.md` in `key=value` form. Fix: read through `parse_document_sections`
  (`_plan_parsing`), the reader behind `request read`; the fixture now renders the production template.
  Corroborated: `ci pr view` (merged, `8aa33cfe1`), the commit is an ancestor of `origin/main`, its file list
  is `_cmd_lifecycle.py` plus two `manage-status` test files, and the checked-out probe imports
  `parse_document_sections`. Same defect as the "transition-mailbox misreports `not_orchestrated`" lesson
  from PLAN-02's drain (`2026-09-23-15-001`, no longer in the lessons store). Also: #1684
  (`unified-sync-all-harnesses`) merged as `4962d398b`, so PLAN-10's checked live-plan overlap at emit time is
  gone.

- 2026-10-02 — **PLAN-10 emitted on operator override ("emit the plan"); not yet confirmed launched.** `next`
  refused it on two counts, read from `corpus cross-check` at emit time: (1) `candidate comparison
  indeterminate — sibling_epic_spec indeterminate: 95` (of 611), the standing repository-wide gate; (2) a
  CHECKED overlap with the live plan `unified-sync-all-harnesses` (`6-finalize`, PR #1684) on
  `manage-locks/standards/machine-global-config-scope-audit.md`, which PLAN-10's `manage-locks/**` claim
  contains. The second is new — the previous live-plan candidate (`antigravity`, indeterminate) is no longer
  in the live plan set. Prep-readiness passed on its own terms: 7 verdict rows, all admit, none stale. One of
  two slots filled (`parallelization_scope` 2, nothing launched). `auto_emit` is `false`, so the row stays
  `staged` until the operator confirms the launch. Same override precedent as PLAN-02, PLAN-08 and PLAN-11.
  **Same day: operator confirmed the start.** Cross-read of the live plan store showed
  `orchestrator-land-verbs` in `2-refine`; row transitioned `staged` → `running`, `plan_marshall_plan_id`
  stamped.

- 2026-10-02 — **PLAN-11 landed (#1676, `8665ddacf`); reconciled via `analyze` (inbox scan, 10 messages).**
  The landing message was complete (`landing-check`: no missing key) and corroborated against `ci pr view`
  (merged), the merge commit's file list, and two live `corpus cross-check` runs. Row transitioned `running` →
  `shipped`, `pr` and `landing` stamped. Two readings the landing changes: (1) the spec's estimate that the
  self-snapshot accounted for "roughly half" of `review-apparatus`'s sibling indeterminacy is refuted — it
  was 2 of 94; (2) the sentinel exclusion, which the plan could only cover by test, is now observed on a real
  store (`excluded_sentinel_plan_count: 1`). Surface delta: 3 undeclared architecture descriptors (finalize
  catch-up for #1670, not plan work) and 2 declared-but-untouched `manage-status` entries (D4 chose the
  consumer site). No spec's declaration needs correcting — the landed spec is terminal.

- 2026-10-02 — **Inbox drain: 9 `candidate-lesson` messages from `cross-check-dated-archive-self-collision`
  (PLAN-11's own #1676 retrospective) — all 9 PROMOTED, `2026-10-02-10-001` through `-009`, in message order.**
  None concerns this epic's substrate; each is about another component: `python-verify-ci` (config-only
  `marshal.json` PRs redden main, -001), `phase-6-finalize` (a dequeued PR is indistinguishable from a queued
  one, -002; settle-band verdicts re-bought on every loop-back, -005; dispatch-boundary rows without a step id,
  -008), `phase-5-execute` (`scope_creep_warning` rejected by `manage-findings`, -003; scope-creep and artifact
  diffs run from a pre-rebase commit, -004), `finalize-step-sync-plugin-cache` (staleness guard expects bundles
  the claude target never emits, -006), `plan-retrospective` (read-intent files counted as unrealised, -007),
  `plan-marshall` (orchestrator-tier verify builds filed under `NO_PLAN`, -009). Bodies were lifted verbatim.
  Three restate signals this epic already promoted and `lessons-routing` has since drained from the corpus:
  -003 (PLAN-02's drain, 2026-09-24), -005 (the post-loop-back re-fire set, same drain) and -008 (the
  dispatch-audit channel, PLAN-08's drain, 2026-09-23) — promoted again because no active lesson carries them.
  ⚠ `manage-lessons drain-dedup` was NOT followed: it groups by component only and reported 5 of the 9 as
  recurrences of two unrelated lessons (`2026-09-29-17-001`, `2026-09-27-07-004`) and of each other. Checked
  by reading both lessons and listing each component — no real duplicate exists. See Watches.

- 2026-10-01 — **PLAN-11 emitted on operator override and confirmed started.** `next` refused it
  (`candidate comparison indeterminate — sibling_epic_spec indeterminate: 95, live_plan indeterminate: 2`);
  the operator launched it anyway because it repairs that gate. Row transitioned `staged` → `running`,
  `plan_marshall_plan_id` stamped `cross-check-dated-archive-self-collision` after cross-reading the live plan
  store. Same override precedent as PLAN-02 and PLAN-08.

- 2026-10-01 — **Operator observation (paste from a consumer project's `next`): the `NO_PLAN` sentinel blocks
  every emission — CORROBORATED and FOLDED into PLAN-11 as D4.** Verified at `391efbbd6`:
  `_live_plan_records` (`orchestrator.py:3860`) takes every entry of `_iter_active_plan_dirs`
  (`_cmd_sibling_collision.py:130`), which admits any directory with a `status.json`; the sentinel directory
  has one (`metadata.sentinel: true`), never has `affected_files`, and neither function references
  `NO_PLAN_SENTINEL`. Reproduced on this repo (`live_indeterminate_plans: [NO_PLAN, antigravity]`). The consumer
  project's own run was not re-executed — recorded in the spec as an operator-paste claim. Folded rather than
  staged separately: same verdict, same function, same defect shape as PLAN-11's self-collision, and a second
  plan would only queue behind it on `orchestrator.py`. Operator instruction honoured: the exclusion is
  explicit, keyed on the single sentinel definition. NOT folded: the gate's whole-population fail-closed scope
  (Open Defect 2026-09-22) — a design decision, kept as a named Non-Goal.

- 2026-10-01 — **PLAN-11 claim 3 verdict corrected `rescoped: no` → `yes`.** The refutation (no comparable
  identity field) was re-verified at `391efbbd6` and was already absorbed by D1's re-scope on 2026-09-24; the
  cleanup stamp of 2026-09-29 misreported it as open, which made PLAN-11 the corpus's only prep-ready blocker.

- 2026-09-24 — **Inbox drain: 9 `candidate-lesson` messages from `ledger-decomposition-and-row-vocabulary`
  (PLAN-02's own PR #1609 retrospective) — 7 PROMOTED, 2 recorded as RECURRENCES on existing
  lessons.** None concern this epic's own substrate; all are findings about OTHER marketplace
  components surfaced during PLAN-02's execution. Promoted (`2026-09-24-09-001,003,004,005,006,007,008`):
  `phase-5-execute` (scope_creep_check finding-type mismatch), `phase-6-finalize` ×3 (local-main
  staleness blocking self_review, no derived post-loop-back re-fire set, missing STEP/DISPATCH
  lines on loop-back re-fires), `ext-self-review-plan-marshall` (no closed-set-claim candidate,
  4-round non-convergence), `phase-4-plan` (declared verification command dropped between
  deliverable and task), `execute-task` (xdist_group nodeid suffix not stripped). Recurrences:
  the `-003` message (extract-chat-signal `BlockScalar` defect) is the SAME defect as
  `2026-09-23-05-001` (filed from PLAN-08's own retrospective the day before) — recorded as a
  Recurrence section there rather than a second lesson, after retiring the accidentally-allocated
  duplicate stub. The `-007` message (transition-mailbox misreports `not_orchestrated`) recurs
  `2026-09-23-15-001`, filed from an EARLIER phase transition of this SAME plan's own run —
  recorded as a second Recurrence section there.

- 2026-09-24 — **Inbox drain: `ledger-decomposition-and-row-vocabulary-001.md` (finding) —
  absorbed, partially actioned.** PLAN-02 shipped (#1609): every orchestrator ledger now
  refuses reads/writes in the old monolithic layout (`legacy_layout`, no read-fallback) and
  needs `orchestrator migrate-layout --slug {slug}`. This epic's own ledger migrated
  immediately (11 rows, anchor migrated, `queue-view.md` written, GENERATED blocks stripped
  from `epic.md`). **NOT actioned**: the finding also asks to run `migrate-layout` across
  the WHOLE population (`corpus epics`: 25 distinct — 9 active, 16 archived). That write
  touches every OTHER epic's own ledger tree, outside this session's write-boundary
  (`.plan/orchestrator/orchestrator-refactor/` only), and several sibling epics have their
  own live sessions actively using their ledgers right now. Flagged to the operator rather
  than actioned unilaterally — see the new Open Defect below.

- 2026-09-20 — **PLAN-04 landed (PR #1543) with a result that CORRECTS this epic's own
  Vision.** This epic's Vision (written at `init`) framed aspect 3 as "rename the `slug`
  vocabulary to `name`". PLAN-04's actual, independently-reasoned outcome, landed as
  ADR-023, is different: `--name` is explicitly REJECTED — it names the value's *shape*
  (a form-noun spelling), the exact defect `--slug` already has — and the epic
  identifier is instead spelled `--epic` (entity-noun-first, closed suffix set
  `none`/`-id`/`-number`/`-slug`). The plan identifier is NOT collapsed into the epic's:
  `--plan-id` stays at all its sites, since epic and plan are distinct entities at
  distinct tiers. Alternatives considered and rejected by ADR-023: `--name` (form-noun,
  rejected on the rule), `--slug` (form-noun, incumbent, rejected on the same rule —
  volume favored it 23-to-4 by site count but the rule overrides volume). This
  supersedes the literal "rename to `name`" framing everywhere it appears in this
  epic's own Vision and in PLAN-05's original title; PLAN-05 is corrected to execute
  the ACTUAL decision (`--epic`), not the epic's original guess at what the decision
  would be.

- 2026-09-20 — PLAN-05 folded with PLAN-04's D4 execution brief (message
  `identifier-vocabulary-decision-001.md`): sized rename surface (31 source files / 43
  prose files — NOT the originally-cited 38/215, which the brief shows measures the
  UNCHANGED `--plan-id` incumbent surface, not the rename surface), the same-commit
  ordering constraint from `ARGUMENT_NAMING_CANONICAL_FORMS_DRIFT` (binds only 30 of 71
  canonical-forms rows; the other 41 need a manual sweep), a git-native survivor-sweep
  method, the `orchestrator queue` mode-selector redesign (not a substitution), and the
  "two plan-identifier vocabularies" finding (epic-local `PLAN-NN` ordinal vs
  plan-marshall kebab id, spelled inconsistently across orchestrator verbs — PLAN-05
  must decide per-verb before renaming). Expected Surface updated in the same act:
  added `manage-architecture/**`, `script-shared/scripts/query/query-architecture.py`,
  and `pm-plugin-development/skills/plugin-doctor/scripts/doctor-marketplace.py` (+
  its test) — new `--name`-occupant sites the brief's population derivation surfaced
  that PLAN-04's own (narrower) Expected Surface never declared. Excluded by the same
  same-act rule: `workflow-integration-sonar`'s `sonar_rest --transition` — a false
  member the brief explicitly flags, not a rename target.

- 2026-09-20 — PLAN-06 (parked) folded with `identifier-vocabulary-decision-003`: the
  orchestration-detection reconciliation defect between `phase-1-init` (does not always
  record `source_id`) and `phase-6-finalize`'s terminal-emission gate (drops
  `emit-landing` when the pointer is absent, even when the finalize dispatcher itself
  later resolves `orchestrated: true`). Measured consequence, independently confirmed:
  this epic's `queue_without_landing_count` was `7` of `7` until this reconciliation.
  Expected Surface updated in the same act: added `phase-1-init/**` and
  `phase-6-finalize/**` (the terminal-emission-orchestration-gate surface specifically).

- 2026-09-21 — **PLAN-01 landed** (#1557/#1558/#1561) via a split from the stuck #1555.
  Reconciled via `analyze` (paste, corroborated against `ci pr view` for all four PR numbers
  plus `git log origin/main`). Two consequential discoveries made and acted on in the same
  pass: (1) `_orchestrator_inbox.py`'s `_SOURCE_ID_RE` now hardcodes the `.plan/orchestrator/`
  prefix, reproduced directly to fail on PLAN-01's own pre-migration `source_id` — folded into
  PLAN-03 as first-party evidence, not theorised risk; (2) this epic's own ledger tree had
  split across the old and new resolver paths (see Open Defects for the corrected root-cause
  account) — reconciled, with `status.json`'s PLAN-06 transition re-applied via script once
  resolution was confirmed correct.

- 2026-09-22 — **Inbox drain: 1 message, `lessons-handling-26-09-22-01-001.md`
  (candidate-lesson, 3 items) dispositioned.** Item `2026-09-19-13-001` (channel
  address grammar mismatch — `--target-plan` mailbox routing keys off the epic-local
  `PLAN-NN` ordinal while a plan's own mailbox read keys off its kebab
  `plan_marshall_plan_id`, so delivery cannot fire in any real epic) **corroborated
  against HEAD and FOLDED into PLAN-05's D6** as first-party evidence, not theorised
  risk — see PLAN-05 Claim Labels. Items `2026-09-21-10-010` and `2026-09-21-10-012`
  **DISCARDED as already-covered**, contradicting the source epic's own
  none-already-covered disposition: -010's cited bug is fixed at
  `_cmd_lifecycle.py:183` (post PLAN-TRUTH-143/#1539); -012's principle is already
  enforced by this epic's own `candidate_comparison_determinate` fail-closed verdict
  (`orchestrate.md` Step 4), landed by the same PR.

- 2026-09-23 — **Inbox drain: `lessons-routing-001.md` (finding) — CONFIRMED, no new action.**
  `lessons-routing` flagged `2026-09-21-10-010`/`-012` as possible duplicates of content
  `truthful-signals` already promoted on 2026-09-21, asking this epic to check before staging
  or acting further. Re-verified: `manage-lessons get` returns `not_found` for both ids in the
  global corpus, and this epic's own 2026-09-22 drain (see entry above) already independently
  discarded both as already-covered — the exact outcome `lessons-routing`'s correction points
  toward. Nothing to retract or re-disposition.

- 2026-09-23 — **Inbox drain: 8 `candidate-lesson` messages from `verdict-staleness-scoping`
  (PLAN-08's own PR #1585 retrospective) — all 8 PROMOTED to the global lessons corpus,
  `2026-09-23-05-001` through `-008`.** None concern this epic's own substrate (`orchestrator.py`,
  the ledger, WS-01..WS-04); all are findings about OTHER marketplace components surfaced
  during PLAN-08's execution — `platform-runtime` (BlockScalar serialization bug in
  `chat extract-signal`, -001), `plan-retrospective` (Tier-1 gating blind to the
  delivered-vs-reduced byte gap, -002; `top_tags[5]` vs the fixed logging-gap vocabulary, -005;
  `Phase Dispatch Boundaries` structurally unrenderable, -008), `phase-6-finalize` (finalize
  cost matched execute's on a 6-file fix, -003; dispatch-audit evidence channel only 27.3%
  populated, -007), `manage-change-ledger` (37 build calls, zero ledger rows, -004), and
  `pm-plugin-development:ext-self-review-plan-marshall` (`self_review surface` exits 1 with
  empty stderr, -006). Promoted rather than folded/staged because no plan in this epic owns
  any of these components — this is the lessons-routing sweep's job to route onward from here.

- **[header lost in an earlier edit, reconstructed at relocation] PLAN-05 scope-bloat split guard (9 deliverables, D0–D8) —
  no prior rationale was on record.** Verdict: proceed unsplit. D0–D4/D6–D8 are one
  coherent rename (`--slug`→`--epic`) bound by a hard same-commit ordering constraint
  (`ARGUMENT_NAMING_CANONICAL_FORMS_DRIFT`) that a split would not relax — they cannot
  land independently without breaking the gate. D5 (the `orchestrator queue`
  mode-selector collapse) is a genuinely SEPARATE decision, staged here only because it
  sits on the same subparser D1 touches, not because it shares the rename's ordering
  constraint — it is the one candidate for splitting out. Not split now: D5 also depends
  on D6 (settle first, same as D1), so a split plan would still have to sequence tightly
  behind this one, and the corpus's own disjointness gate is currently marketplace-wide
  blocked regardless (see Open Defects) — a split has no throughput benefit while that
  holds. Reconsider at outline time if the executing plan finds D5 adds unwanted coupling.

## Legacy-layout migration sweep across sibling epics

- **NEW, from PLAN-02's landing (2026-09-24) — 24 other epic ledgers are now unreadable by
  every orchestrator verb (`legacy_layout`, no read-fallback), and migrating them is
  outside this epic's write-boundary.** `corpus epics` reports 25 distinct epics (9
  active, 16 archived); only `orchestrator-refactor` has been migrated (by this session).
  Any orchestrator verb touching a sibling epic's queue or resume anchor now refuses until
  `orchestrator migrate-layout --slug {slug}` runs for it. Letter-suffixed plan ids (e.g.
  `PLAN-PR-025B`) are refused by the migration itself (`unmigratable_rows`) and need a
  per-row operator decision before that epic can migrate. **Operator decision needed**:
  authorize a cross-epic sweep (by this session, or left to each epic's own session), and
  decide the letter-suffixed row ids case by case as they surface.

## Pre-PLAN-01 source_id prefix rejected by inbox detect

- **NEW, CRITICAL — the orchestration-detection seam hardcodes the NEW tracked path only,
  so every plan whose `source_id` was captured before PLAN-01 landed now silently fails
  `inbox detect`.** Reproduced directly, 2026-09-21:
  `orchestrator inbox detect --source-id ".plan/local/orchestrator/orchestrator-refactor/plans/PLAN-01-tracked-orchestrator-store-resolver.md"`
  (PLAN-01's OWN actual, correctly-written source_id) returns `orchestrated: false`,
  `detection: unrecognised_id`. The SAME id with the path prefix changed to
  `.plan/orchestrator/...` (the new tracked address) correctly returns `orchestrated: true`
  — isolating the cause precisely to `_orchestrator_inbox.py`'s `_SOURCE_ID_RE`, which now
  requires the `.plan/orchestrator/` prefix literally, with no acceptance of the pre-PLAN-01
  `.plan/local/orchestrator/` form. This is NOT a naming-grammar defect (the digit-suffix
  grammar itself accepts a trailing descriptive slug — `PLAN-01-tracked-orchestrator-store-resolver.md`
  parses fine once the prefix matches) and NOT unique to this epic: `truthful-signals`
  PLAN-TRUTH-144, confirmed `running` as of this epic's own `cleanup` pass, almost certainly
  carries an old-form `source_id` too and will hit the identical failure at its own finalize.
  Folded into PLAN-03 (the migration-mechanism workstream) as first-party reproduced
  evidence, not merely theorised risk — see PLAN-03's Claim Labels.

## PLAN-01 branch skipped the plugin-cache sync

- **Operator-reported, not yet independently investigated**: `finalize-step-deploy-target` /
  `finalize-step-sync-plugin-cache` were skipped for PLAN-01's own branch, so the local
  `~/.claude/plugins/cache/plan-marshall/` may be stale relative to what just landed
  (including the resolver change itself). Run `/sync-plugin-cache` to refresh — outside this
  orchestrator's carve-out to perform itself.

## PLAN-11 landing residue

- **PLAN-11 landing residue (2026-10-02):** (1) the plugin cache is stale relative to `8665ddacf` —
  `finalize-step-sync-plugin-cache` failed on its staleness guard (lesson `2026-10-02-10-006`); `corpus
  cross-check` already runs the landed code here, so the orchestrator scripts are not affected, but the synced
  skill bodies are. Retire when a sync succeeds. (2) This epic's own #1666 (`use_worktree` on) reddened `main`
  for about two hours because a `marshal.json`-only PR skips the test build (lesson `2026-10-02-10-001`) —
  until that is fixed, run the config-contract tests locally before landing any knob change from this epic.
  (3) `manage-lessons drain-dedup` groups candidates by component alone and reports distinct defects as
  recurrences; a drain that trusted it would have dropped 5 of 9 lessons. Not filed as a lesson yet — route
  to `truthful-signals` (a confident "recurrence" count hiding a loss) on the next sweep. It also reported
  lesson `2026-09-27-19-001` as present but carrying no parseable metadata header.

## Cross-ledger watches keyed on PLAN-02 and PLAN-06 emission

- `truthful-signals` PLAN-TRUTH-151 (still `staged` as of 2026-09-21) declares
  `orchestration-model.md`, overlapping PLAN-02 — the disjointness gate cannot see this
  cross-ledger collision. No actual risk yet (nothing running there). — trigger: check before
  staging PLAN-02's emitted command.
- `truthful-signals` PLAN-TRUTH-144 is `running` (as of 2026-09-21 cleanup pass) and declares
  `landing-payload-spec.md` — the same file PLAN-06's D1 takes ownership of. PLAN-06's
  ownership statement must route around it per the running-row exclusion. — trigger: check its
  status before PLAN-06 is ever emitted; once it lands, fold its own claim on the file into
  D1's ownership record.
- `lessons-routing` PLAN-LR-04 (staged) states the same git-ignored-store durability thesis as
  this epic's WS-01 in its own Vision, but its Expected Surface is `prose` (undetectable by
  the gate). — trigger: if PLAN-LR-04 reaches for a durability substrate before WS-01 lands,
  read its spec body by hand rather than trusting the gate.
