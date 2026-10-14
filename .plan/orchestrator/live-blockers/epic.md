# Epic: Live Blockers

slug: live-blockers

> Hand-written narrative for one epic under `.plan/orchestrator/live-blockers/`. The layout and
> authority contract live in the central standard — see
> `persona-plan-orchestrator/standards/orchestration-model.md`. The ledger JSON files
> (`status.json`, the `queue/{PLAN-ID}.json` rows) and `resume_anchor.md` are the machine
> authority; any statement here that conflicts with them is stale prose.
>
> START HERE and the Ordered Queue are not in this file. They live in the generated,
> git-tracked `queue-view.md` next to it (see the Persist / Stop-Resume Contract in that
> standard). `queue-view.md` is never hand-edited. A merge conflict in it is never merged by
> hand: merge the source files, run
> `python3 .plan/execute-script.py plan-marshall:plan-orchestrator:orchestrator regenerate-view --slug live-blockers`
> on the merged tree, and `git add` the result.

## Vision

plan-marshall's workflow machinery is being rewritten as plan-marshall-mcp, and until that ships
plan-marshall stays in daily production use. This epic holds the work that cannot wait for the
rewrite: defects that make a normal plan run fail, mislead or need an operator override today,
and high-priority work on things the rewrite does not replace — harness sync, organisation CI,
the review bots and their rollout. It is too large for one plan because the 21 fixes sit on
different surfaces and most are independently shippable. The epic is done when a plan can run
from init to merge in this repository and in a consumer repository without a manual override,
and the review gate can be trusted to mean what it says.

The epic was cut on 2026-10-07 from a sweep of the nine epics active at the time and the lessons
store. Eight of those epics were closed and archived in the same act; `lessons-routing` stays
active. Design input for the rewrite is not carried here: it lives in plan-marshall-mcp's
requirements, specification and implementation-watch documents.

## Queue annotations

The queue was regrouped on 2026-10-08 (see Decisions); PLAN-LB-01 to PLAN-LB-13 and PLAN-LB-15
to PLAN-LB-21 are `superseded` and their spec files stay as the record of the first cut. The
live rows and their state are in `queue-view.md`; this zone keeps only notes the view cannot
derive, for rows still live.

> ↪ Relocated to `settled.md` § "Queue annotations for shipped, superseded and drained work" — their plans shipped or were superseded and their drains were consumed; moved on 2026-10-14 by operator override of the annotation-zone rule.

- **Where each earlier plan went.**
  - PLAN-LB-22 finalize-loop-control — PLAN-LB-10, PLAN-LB-02, PLAN-LB-05 D5.
  - PLAN-LB-23 verify-builds — PLAN-LB-12, PLAN-LB-01.
  - PLAN-LB-24 review-step — PLAN-LB-05 D3, PLAN-LB-18, PLAN-LB-19.
  - PLAN-LB-25 phase-and-merge-gates — PLAN-LB-09, PLAN-LB-05 D1 and D2, PLAN-LB-04.
  - PLAN-LB-26 execute-loop-triage — PLAN-LB-06, PLAN-LB-05 D4, PLAN-LB-08.
  - PLAN-LB-27 plan-footprint — PLAN-LB-07, PLAN-LB-11.
  - PLAN-LB-28 java-consumer-repos — PLAN-LB-13, PLAN-LB-03 (labelled a weak merge in its header).
  - PLAN-LB-29 harness-sync — PLAN-LB-15, PLAN-LB-17.
  - PLAN-LB-30 org-ci-release — PLAN-LB-16, PLAN-LB-20 D1 to D3.
  - PLAN-LB-31 in-house-reviewer — PLAN-LB-21, PLAN-LB-20 D4 and D5.
  - PLAN-LB-14 launch-gate-scope — unchanged.

- **PLAN-LB-39** (running; staged 2026-10-13) — sequenced after PLAN-LB-37 by operator decision (shares
  `functional-review.md` and two test directories). Its D6 builds on 37's functional review;
  rebase onto 37's final landing. Also overlaps the staged PLAN-LB-26 and PLAN-LB-27 on
  `phase-5-execute/SKILL.md`, `execution.md` and `triage.md` — the gate will ask when either is
  emitted alongside it.

- **PLAN-LB-31** (running) — its roster decision is in (inbox `-001`, 2026-10-14): the operator
  kept `cuioss-review-bot` required as is and CodeRabbit required; the measurement does not
  meet the reopen condition, so the plan proceeds to its enrolment deliverables (PLAN-LB-20 D4
  and D5 in the carried numbering).

- **PLAN-LB-40 and PLAN-LB-41** (staged 2026-10-14) — 40 shares no declared file with any
  running plan. 41 shares `automatic-review/standards/cuioss-review-bot.md` with the running
  PLAN-LB-31 (different sections); its D5 waits for a live code-review comment on a PR merged
  after `187f7314a`.

- **Foreign checkout paths.** The specs carried into 28, 30 and 31 name sibling repositories
  as `/Users/oliver/git/...`. Each of those specs carries a clause to resolve the names under
  the checkout root of the machine the plan runs on.

- **Operator decisions the specs leave open** (each is a verify-first clause in its spec):
  - PLAN-LB-26 — sticky resolutions with an opt-in reopen of `fixed`, or always reopen `fixed`.
  - PLAN-LB-27 — how legitimate out-of-footprint edits by finalize steps get in.
  - PLAN-LB-31 — running `gh`-based corpus scripts, posting `/review` on merged PRs, the
    roster decision itself, and whether to enrol after it.

## Decisions

- 2026-10-07 — **Epic created by operator instruction** ("create an orchestrator for the
  critical / high; remove them from the current orchestrator; archive / dormant the other
  orchestrators beside lessons-routing"). Scope is the 21 high-priority clusters of the
  cross-epic sweep; the roughly 50 medium and low clusters are recorded in `backlog.md` and are
  not staged. Alternative considered: stage all 70 — not chosen, the operator asked for
  critical and high only.

> ↪ Relocated to `settled.md` § "Decisions settled by the regrouping and the shipped plans" — the subjects are closed — the first cut was regrouped, the staged plans shipped or were superseded, the cleanups landed.

- 2026-10-08 — **Queue regrouped from 21 plans to 11 by operator instruction** ("make a full
  review of all plans. Rearrange that: adjacent plans (same component / topics) are bundled
  together; the plans aggregate a larger amount of deliverables (up to 12 are authorized); the
  plans are structured in a way to provide high parallelism"). Twenty specs were absorbed into
  ten new ones, PLAN-LB-22 to PLAN-LB-31, of 7 to 11 deliverables each; PLAN-LB-14 is
  unchanged. All 90 deliverables of the absorbed specs were carried, each exactly once, with
  their claim labels and surface entries copied unchanged; the move list is in Queue
  annotations. Scope-bloat guard: every new spec is above six deliverables and proceeds
  unsplit on the operator's authorization of up to twelve.
  - Two specs were cut at the deliverable level, because each spanned components that belong
    to different plans: PLAN-LB-05 (five waits in five components) and PLAN-LB-20 (schema work
    in the organisation repository, then enrolment gated on PLAN-LB-21's decision).
  - Alternatives considered and not chosen: cutting PLAN-LB-02 and PLAN-LB-09 by deliverable
    (it freed no additional pair); keeping PLAN-LB-12 with PLAN-LB-13 and PLAN-LB-05 D4 as one
    build plan (it made the build plan collide with the review plan through
    `await-long-running.md` and with the execute plan through `execution.md`).
  - No spec file was deleted. The twenty absorbed rows are `superseded`; each old spec carries
    a banner naming its successor, and its `## Expected Surface` was replaced by a `DERIVED`
    marker with the original entries kept under "Superseded Surface (record only)", so a
    retired spec no longer collides with the plan that carries its work.
  - What limits parallelism: `phase-6-finalize/SKILL.md` is edited by four of the new plans
    and `plan-marshall/workflow/execution.md` by three. Those two files, not the bundling,
    are why the finalize plans still run in sequence.
- 2026-10-09 — **parallelization_scope raised from 2 to 4 by operator instruction** ("set
  the parallelism to 4"). Four plans were already running on per-launch overrides
  (PLAN-LB-24, 32, 33 and 34); the knob now matches what the operator runs. The limit on
  real parallelism is unchanged: plans that share `phase-6-finalize/SKILL.md`,
  `execution.md` or the self-review workflow still run in sequence.
- 2026-10-13 — **PLAN-LB-39 antigravity-execution-fidelity staged** (WS-04) by operator
  instruction ("emit the antigravity plan"). Scope by operator decision: ONE plan, seven
  deliverables, above the ~6 split guard — the recommended split (dispatch + phase integrity vs
  context + measurement) was declined; and the two harness-agnostic critical items `-015`/`-026`
  (criteria rewritten, weakened tests) and `-016` (pushed head past its gates) are INCLUDED, over
  the recommendation to exclude them. Staging-time re-grounding at `71971784f`: the Antigravity
  `Task` tool maps to `invoke_subagent` and `platform-runtime subagent dispatch` already exists,
  but the `Task:` dispatch line is preserved verbatim in the generated output and nothing in phase
  5 calls the seam; `project_initial_setup` bridges no `CLAUDE.md`; nothing on the start path calls
  `orchestrator preflight`. **Held back** at the first `next`: it shares
  `functional-review.md` and two test directories with the running PLAN-LB-37; the operator
  declined to run them together. Emit once PLAN-LB-37 lands. **Hold released 2026-10-13**:
  PLAN-LB-37 landed (#1759, `d5c1e869f`); start from that commit or later. Still overlaps the
  staged PLAN-LB-26 and PLAN-LB-27 on `phase-5-execute/SKILL.md`, `execution.md`, `triage.md`.
- 2026-10-14 — **Inbox drain: two specs staged, one Watch retired.** PLAN-LB-40
  steward-upgrade-integrity takes `-011`'s defects and the `migrate-review-steps` removal in one
  plan because both edit `marshall-steward/scripts/upgrade.py`, `upgrade-flow.md` and the same
  steward tests; five deliverables after folding `-011` item 6 into D4 and dropping item 4's
  "add both review steps" half, which the removal makes moot because every configured
  repository already carries both. PLAN-LB-41 lb-37-review-leftovers takes `-012` items 1, 3 to
  7. `-012` item 2 (PLAN-LB-37's D12 outline wording drifted from what shipped) is not a file
  to fix — the outline is archived with the plan; recorded here as an instance of outline drift
  after in-flight re-scoping. Alternative considered: fold `-011` into a staged plan — no
  staged plan touches the steward upgrade.

## Open Defects

- **The two-pass cuioss-review-bot has unverified and unprevented gaps (inbox
  `lb-37-functional-review-012` items 8 to 10, 2026-10-14; foreign repositories, not owned).**
  (8) The 65,000-character comment cap is documented in cuioss-review-bot
  `doc/consumer-guide.adoc` as PR-Agent's truncation, but not verified in the pinned image and
  not mentioned in cuioss-organization #326 — verify or remove the claim. (9) `/improve` has no
  fail-closed oracle, and both `/review` passes are still last-write-wins on overlapping
  comment-triggered runs (detected by the content-match gate, not prevented). (10)
  `/review -i` now fails the `review / code-review` job by design; operator decision whether
  maintainers need specific harmless options allowed. Next step: a plan in
  `cuioss/cuioss-review-bot` / `cuioss/cuioss-organization`, or an operator ruling per item.

- **Antigravity: critical, by operator ruling of 2026-10-12 (the epic's highest priority).**
  All from pm-mcp-core PLAN-41 (pm-mcp-core PR #34), the first plan of that epic run under
  Antigravity; the ingest verified against the archived plan, not at HEAD here unless noted.
  All five are owned by PLAN-LB-39 (staged 2026-10-13, held behind PLAN-LB-37). Full bodies at
  `lessons-routing/lessons-archive/filed-live-blockers/`.
  - **Phase 5 dispatches no sub-agent.** `Task: plan-marshall:execution-context-{level}` has no
    meaning on Antigravity and `phase-5-execute` has no wiring to its `invoke_subagent` (nor to
    OpenCode's sub-agents); all 8 tasks ran inline in one session, phase boundaries were left
    open, no dispatch-boundary row was written. — `lessons-routing-011.md`.
  - **The repository's `CLAUDE.md` is never loaded**, because Antigravity reads only `GEMINI.md`,
    `AGENTS.md` and `.agents/rules/*.md`; with it the build rules and prohibitions vanished.
    Task verification also carried no quality gate although the manifest stamped it per task.
    One symptom: with `CLAUDE.md` unread the agent guessed a formatter, retried
    `spotless:apply` fully qualified after `No plugin found for prefix 'spotless'`, and Maven
    fetched the plugin from Central. Asked for, besides the `CLAUDE.md` bridge and the
    quality-gate synthesis: one agent rule in the base persona and the Antigravity target
    rules — an unresolvable plugin prefix means the project does not use that plugin; stop,
    never retry it fully qualified. — `lessons-routing-012.md` (revision 1).
  - **Zero tokens is recorded as a real number and no plan records its harness**: every
    `record-step` reads `unmeasured`, the landing carries `total_tokens=0` and passes
    `landing-check`; no archived plan has a `client.toon`, because nothing on the start path
    calls `orchestrator preflight`. — `lessons-routing-013.md`. Meets the Watch below.
    Recurred under **opencode** (PLAN-44): `total_tokens=0`, wall time covers 1-init only, no
    `client.toon`; the five finalize builds' logs are missing from the archived
    `build-results/`, so the gates on the pushed head cannot be shown (bears on `-016`).
    — `lessons-routing-028.md` (148).
  - **Not a defect: `build-maven maven run` accepting any plugin goal** (operator ruling
    2026-10-12). The wrapper is a deliberate pass-through; a goal guard would cost a POM
    evaluation per call and refuse ordinary undeclared goals (`dependency:tree`,
    `help:effective-pom`, `versions:*`), and restricting plugin repositories is the project's
    own `.mvn` configuration. The incident is a symptom of the unread `CLAUDE.md` above.
    `lessons-routing-014.md` is superseded by `-012`.
  - **A materially incomplete package was reported complete, with existing tests weakened to stay
    green** (`deliverables_done=7/7`; an independent audit found rules partial, dead or missing,
    a coverage test counting enum constants, an assertion filtered and a fixture changed to
    dodge a rule). Nothing in the pipeline caught it on any harness. PLAN-LB-37's functional
    review, which verifies each success criterion against evidence, is the nearest remedy;
    whether it catches a weakened existing test is not established. — `lessons-routing-015.md`.
    **Recurred under opencode** (pm-mcp-core PLAN-44, PR #38, `6caa663`; operator grade
    critical as the recurrence, high for the new mechanisms): `deliverables_done=6/6` against a
    7-deliverable spec, with D2, D4, D6 and D7 unmet and one new test weakening. New mechanisms,
    none owned: (1) the plan rewrote its own package What/Done-When and ADRs 002–005 to describe
    the shipped code; (2) an ADR contradicts the specification (Workflow DSL Rule 6) with no spec
    PR, and a test-catalog entry was reshaped to stay green; (3) an infeasibility verdict was
    checked against the as-built code and the specified check was then deleted under the
    verify-first "drop a refuted gap" clause — an infeasibility verdict must name the work-order
    sentence and deleting a specified check needs an operator decision; (4) task statuses and
    green builds stood in for the Done-When (no coverage table, a "done" fix task changed no
    code); (5) pre-push review read shape only and finalize triage was bot-bounded, so the loop
    exited on an empty bot queue with Done-When criteria open — asked: the Done-When as a
    standing finalize triage source. Checked at PLAN-LB-37's landing: its functional review
    catches neither a rewritten criterion nor a weakened test — it grades the outline's current
    criteria (`functional-review.md:210-215, 298`) without comparing them to the request, and a
    test identifier counts as evidence (`review-rubric.md:66`). Owned by PLAN-LB-39 D6. Evidence
    of the incident rests on the sender's audit, not re-checked here. — `lessons-routing-026.md`.
  - **The pushed and merged head carries none of the plan's mandated gates** — the Antigravity
    instance, and two Claude Code recurrences where fix commits after the last full gate were
    pushed with only the composed manifest steps re-run. Graded high for Claude Code.
    — `lessons-routing-016.md`.
- **A deliverable in a sibling repository has no lifecycle** (high; critical in its Antigravity
  instance): no plan-owned worktree, no finalize step pushes it or opens its PR, the footprint
  ignores it, and the foreign-PR gate assumes `feature/{plan_id}`
  (`phase-6-finalize/scripts/foreign_pr_gate.py:170-171`), so it both blocks a merged foreign PR
  and misses a missing one. Recurs on every pm-mcp-core plan that changes a specification. Not
  owned by any staged plan. — `lessons-routing-018.md`. Two more plans (PLAN-13, PLAN-18): the
  retrospective footprint reports every sibling path as declared-but-unrealised, so M6 fails by
  construction; relative sibling paths break under `use_worktree`; a sibling deliverable has no
  module name in the architecture. — `lessons-routing-028.md` (168, 175, 176, 181).
- **A required review bot goes stale after a fix commit** (remainder after #1742 and #1752):
  a commit pushed after the last review by any path (inline finalize fix, merge-queue flow
  without a local rebase) does not re-arm the re-review; a leaf read `re_review_on_loopback`
  from the wrong source; a bot whose path filter excludes the whole diff is not counted as
  expected-absent. The "fixed before the fix exists" item is closed by #1742/#1752. Not owned by
  any staged plan. — `lessons-routing-017.md`.
- **CodeRabbit concerns raised only in its summary/walkthrough comment are never filed** —
  security concerns included (high, operator ruling 2026-10-13). Verified at HEAD:
  `automatic-review/standards/coderabbit.md:60-61` list the summary marker and `## Walkthrough`
  as `ignore_patterns`, line 127 calls them whole-comment drops "that carry no per-line
  finding", and `github_pr.py` (`_is_obvious_noise`, line 407) counts them into
  `count_skipped_noise` only; nothing reads the summary body for actionable, "Outside diff
  range" or security items. Seen on pm-mcp-core PLAN-18, PR #43. Asked: parse the summary for
  actionable and security items, or at least report a dropped summary that carried them; a
  summary-only security fixture pins it. Not owned by any staged plan; nearest PLAN-LB-31 or
  the `-017` remainder. — `lessons-routing-027.md`.
- **Red CI has no triage route.** `verification-feedback.md` accepts only `build-runner, sonar,
  pr-comment, plugin-doctor, pr-state, finalize-feedback` (lines 30, 59 at `47d21e1bf`), while
  `ci_verify.py` emits `ci-verify-missing/-build/-policy/-timeout/-cancelled`; every red-CI
  dispatch is refused `unknown_producer`. Five plans (PLAN-LB-25 and four pm-mcp-core plans);
  also a CI check is classed by name tokens, not by what it runs. Lesson `2026-10-11-16-001`.
  Not owned by any staged plan. — `lessons-routing-019.md`, `lb-25-phase-and-merge-gates-001`.
  Recurrences: PLAN-13 (`ci-verify-policy` refused `unknown_producer`, re-dispatched as
  `finalize-feedback`); lesson `2026-10-11-07-001` (plan-06) — a SonarCloud gate failure inside
  the `build / sonar-build` Maven job filed 5 `ci_policy_failure` findings instead of deferring
  to sonar-roundtrip. — `lessons-routing-028.md` (153, 189).
- **In a consumer repository a dispatched leaf cannot resolve its workflow document**:
  `agents/execution-context.md:111-112` maps a notation only to `marketplace/bundles/…`
  (`workflow_not_found` otherwise, line 119), so every consumer-repository dispatch improvises,
  some reading a stale built copy. Graded high. Not owned by any staged plan.
  — `lessons-routing-021.md`. Recurred on PLAN-18: the 4-plan leaf and two sonar-roundtrip
  leaves read the doc from the plan-marshall checkout's `target/claude/` instead.
  — `lessons-routing-028.md` (182).
- **The deep-lane outline writes no assessments**, so Q-Gate check 2.2 fails every deliverable
  — one guaranteed operator interruption per deep-lane plan (eight pm-mcp-core plans). Graded
  high by the operator. Not owned by any staged plan. — `lessons-routing-022.md`. Ninth to
  eleventh plans: PLAN-13 (Q-Gate 447991), PLAN-18 (0feabd, accepted by the operator), PLAN-54
  (affb5d, assessments added after the gate asked). — `lessons-routing-028.md` (162, 174, 191).
- **The 4-plan Q-Gate skips its validators on the 3-outline hash and reports a pass over zero
  runs**; no verb computes the deliverable hashes, so passes improvise. Graded high by the
  operator. Not owned by any staged plan. — `lessons-routing-023.md`. Recurred on PLAN-18: both
  Q-Gate runs skipped `deliverable-hashes.toon` (16 hashes over 2 runs); the 4-plan leaf had no
  shell. Asks for a `manage-solution-outline deliverable-hashes` verb.
  — `lessons-routing-028.md` (185).
- **A local-only run can still schedule push-related steps.** With
  `phase-5-execute.commit_and_push` false the commit-push filter drops `pre-push-quality-gate`,
  `functional-review` and `code-review`, and the ceremony selection adds them back for a
  `lane: minimal` gate without consulting `commit_and_push` (`_manifest_rules.py`,
  `_apply_ceremony_finalize_selection`). Predates PLAN-LB-37. **Operator decision needed:**
  whether a `minimal` lane overrides "no push", possibly per step class (a review step may keep
  value in a local-only run, a pre-push gate does not). — `lb-37-functional-review-003.md`.
- **Free-text placeholders in workflow command templates are not shell-quoted**: finding titles,
  reasons and refs interpolated into double-quoted arguments break the command or run
  `$(...)`. PLAN-LB-37 fixed `functional-review.md` and `code-review.md`; `triage.md`,
  `verification-feedback.md` and the remaining `phase-6-finalize` documents are left — confirmed
  at `7f35dca9a`, e.g. `workflow/create-pr.md:182, 292`, `workflow/adr-propose.md:115`,
  `workflow/lessons-capture.md:170`, `standards/push.md:168`. Lesson `2026-10-13-07-002`. Not
  owned by any staged plan. — `lb-37-functional-review-004.md`.
- **From PLAN-LB-37's landing** (`landings/PLAN-LB-37.md`), none owned by a staged plan:
  - **A required bot's size refusal loops instead of escalating**, and trigger-B reads
    staleness from another PR's findings: the structural-refusal branch is keyed on the
    rate-limit list, CodeRabbit's `refusal_patterns` miss "files exceed the limit", and the
    selector has no `pr_number` filter. Lesson `2026-10-13-14-003`. Pairs with lesson `-14-001`
    (check size caps before `create-pr`). Nearest owner PLAN-LB-31.
  - **The footprint of a stacked landing is the last PR only**, so the retrospective reports
    confident low recall. Lesson `2026-10-13-14-002`.
  - **Finalize re-fires leave no execution-log or dispatch-boundary rows.** Lesson
    `2026-10-13-14-004`.
  - **`manage-logging` `work`/`decision` now exit 1 on a write failure** (`manage-logging.py:197-220`,
    since #1759), against the plugin rule of exit 0 with `status: error`
    (`plugin-architecture/SKILL.md:159`); a caller that treats a non-zero exit as fatal halts on
    a log-write failure. Low.
  - **D13 partial**: neither review step's own tests read `review-rubric.md`. Low.
  - **The plugin-cache sync does not prune**: the installed cache still lists the retired
    `pm-plugin-development:ext-self-review-plan-marshall`. Low.
- **Medium and low items are not owned by any staged plan.** They are listed with evidence
  in `backlog.md` (sections 1.12 onward, 2.3 onward, 3.2 onward, 4.7 onward and 5). Promote an
  item into a plan spec when it starts to hurt; re-verify it at HEAD first.
- **35 active lessons have no router of their own beyond `lessons-routing`**, which was
  dormant at the cut. The lessons that describe live defects are folded into the specs here
  and into `backlog.md`; two lessons describe defects already fixed and should be retired
  (`2026-09-27-07-001`, `2026-10-02-21-006`), and `2026-09-27-19-001` has no metadata header.
  — source: sweep of the lessons store, 2026-10-07.
- **The outline leaf has no signal for an ambiguous change type, and two documents disagree on
  the skills the detection dispatch carries.** When `change-type-heuristic` ties,
  `phase-3-outline` Step 4b prescribes a dispatch the outline leaf cannot issue; the leaf
  returns `blocked` with a free-form field and `planning-outline.md` Step 2 has no handler for
  it. PLAN-LB-22 hit this, lost one outline dispatch (about 198K tokens) and got past it with
  three moves no document prescribes. Separately, `outline-workflow-detail.md` lists one skill
  for the `detect-change-type` dispatch where the workflow's own Inputs require three. Reach:
  every deep-lane, non-recipe plan whose heuristic ties. Not owned by any staged plan; stage it
  if it recurs. — source: inbox message `lb-22-finalize-loop-control-001.md`, 2026-10-08, read
  at bundle version 0.1.1867; not verified against the source here.
- **A routed build leaves no change-ledger row for its plan, and it is not the missing plan
  id.** PLAN-LB-23 examined the hypothesis folded into its spec on 2026-10-08 and reports it
  as a separate defect it does not fix: the 84 routed builds of the PLAN-LB-14 run carried a
  real plan id (the work-log line is only written when one is present), yet the ledger held no
  `kind=build` row for the plan. Its candidate cause, reasoned from the code and not
  reproduced: the ledger path is resolved per working tree, so a row appended by a build
  running under the daemon may land in a different working tree's ledger than the one a
  reader opens. If that is right it also bears on which ledger the freshness check reads.
  Not owned by any staged plan. Next step it suggests: run one routed build for a plan in a
  worktree, then compare the ledger file that received the row with the one
  `pre-commit-verify-freshness` opens. — source: inbox message `lb-23-verify-builds-001.md`,
  2026-10-08; pointers `_build_execute_factory._append_gate_build_row`,
  `_ledger_core.resolve_ledger_path`; not verified here.
  - **Read in the code on 2026-10-09 at `c9738952a`; the cause holds and PLAN-LB-23 left
    it open.** `resolve_ledger_path` resolves from the working directory, up to the nearest
    ancestor holding `.plan/local`; each plan worktree has its own
    `.plan/work/change-ledger.jsonl`. The freshness check takes the SHA from the plan's
    worktree but the ledger from its own working directory. `_append_gate_build_row` writes
    its row without a worktree SHA, so that row can never satisfy the freshness check. What
    PLAN-LB-23 changed is the other half: resolved build commands now carry `--plan-id`.
    Its routed-build test replaces the ledger path with a temp file and cannot see the
    split. Seen again on PLAN-LB-23 itself: its retrospective scanned 1272 ledger rows and
    matched none against 148 logged build calls, because the worktree holding the ledger
    had been removed. Still not reproduced by a run. — source: read-only review of
    `c9738952a`; inbox message `lb-23-verify-builds-013.md`.
- **The direct build path's signal handling has three gaps**, all in
  `script-shared/scripts/build/_build_execute.py` as shipped by PLAN-LB-23.
  `_signal_build_group` suppresses `ProcessLookupError` only, so a permission error from
  the group kill surfaces as `error`, a red build, where the daemon path reports `timeout`.
  The grace period waits on the group leader alone, so when the leader exits promptly the
  rest of the group is killed without grace. The signal handlers are installed a few
  statements after the child starts; a signal in that window kills the wrapper and leaves
  the build running with no bound. Each is narrow; none gives a wrong green. Not owned by
  any staged plan. — source: read-only review of `c9738952a`, 2026-10-09, by line; the
  third is also named in the plan's landing message.

> ↪ Relocated to `settled.md` § "Open Defects closed by PLAN-LB-33 and PLAN-LB-38" — closed by #1745 and #1752; the entries themselves said to remove them at the next cleanup, and their two open follow-ups stay as their own Open Defects.

- **The root `opencode.json` is in a shape nothing in this repository reads.** PLAN-LB-29's
  merge commit rewrote it: `permission.bash`, a map of command pattern to
  `allow`/`ask`/`deny`, became a `permissions` array of `{action, resource, effect}`
  objects, `agent` became `agents`, `skills.paths` became a bare list, and the file grew
  from about 650 to about 2730 lines. `opencode_runtime.py` still reads `permission` and
  the OpenCode emitter still writes `agent`. No deliverable asked for it and the diff holds
  no producer for it. If OpenCode ignores the new keys, the deny rules for `gh`, `rm`,
  `git restore`, `git stash` and the rest do not apply in an OpenCode session of this
  repository. OpenCode's own schema was not checked here. Not owned by any staged plan.
  Next step: compare the file with the OpenCode configuration schema, and regenerate it
  from the emitter if the old shape is the valid one. — source: `git show 35b5589b5 --
  opencode.json`, read 2026-10-09; read-only review of the commit.
- **`sync.py --repin` can repin bundles the run did not sync.** It passes the one synced
  version as the target for every registry bundle, so `--bundles X --repin` also moves any
  other bundle that has a directory of that version. — source: read-only review of
  `35b5589b5`, `marketplace/targets/sync.py:855-861`; not reproduced.
- **Symbolic-link handling in the sync has three known gaps**, named by PLAN-LB-29 and
  confirmed in the code: a window between the link check and the write in
  `registry_pin.py`, `sync.py` and `cache_sync.py` (no no-follow open); the two
  `variant_emitter.py` files write with a bare `write_text` when called directly; a version
  string containing a slash is checked for containment but not for an intermediate link.
  Not owned by any staged plan. — source: inbox message `plan-lb-29-harness-sync-014.md`;
  read-only review of `35b5589b5`.
- **Participation credit ignores an in-progress review.** The credit path
  (`workflow-integration-github/scripts/github_pr.py:1938-2033`, untouched by #1752) applies the
  refusal exclusion, the marker gate and currency, but never `read_bot_in_progress` or a
  completion check, so an edited, marker-bearing, pre-existing bot comment is credited while
  the review is running. Observed on #1752: CodeRabbit credited `participated_but_empty` from an
  edited earlier comment, no new review object; the review-retrospective graded the PR
  indeterminate. Lesson `2026-10-12-05-002`. Not owned by any staged plan. — source: inbox
  message `plan-lb-38-review-gate-and-empty-scope-004.md`; read-only review of `4a985a1bf`.
- **A "fixed" reply is held forever on a repository without CI.** PLAN-LB-38's hold
  (`_pr_head_ci_hold_reason`, `github_pr.py` ~3135) requires the overall conclusion over the
  non-bot check rows to be `success`; with no such row it reads `none` → `pr_head_ci_pending`
  (or `pr_head_ci_unreadable` if the provider errors), and `--send-unstamped-fixed` does not
  release a stamped finding. Every repository this machine runs has CI, so it is latent. Also
  left: the wake margin is a fixed 60 seconds with no jitter, and the over-budget escalation
  is an instruction in item 7a only. Not owned by any staged plan. — source: read-only review
  of `4a985a1bf`, 2026-10-12; advisory list of PR #1752.
- **A dependency-floor bump can land with a stale `uv.lock`.** Dependabot #1743/#1744 bumped
  ruff and mypy floors without a lock update; every later plan build re-locked 353 lines, and
  PLAN-LB-38 shipped the re-lock under its own subject. Fixed for now by that commit; the cause
  (no stale-lock check on the bump path, a build that re-locks silently) is lesson
  `2026-10-12-05-001`. Not owned by any staged plan. — source: inbox message
  `plan-lb-38-review-gate-and-empty-scope-001.md`. PLAN-LB-25 is running and does not
    declare the review step. — source: read-only review of `7dd1d3433`, 2026-10-10; inbox
    messages `lb-24-review-step-001` to `-003`, `lb-33-leaf-test-scope-and-executor-001`.
- **The outline's domain narrowing can leave a plan with no domain, and the documented
  recovery fails.** On a consumer-repository plan every deliverable declared
  `domain: documentation`, the phase-3 narrowing dropped all detected domains, and
  `references.domains` was `[]`, so no domain skill resolved in any later phase until the
  list was restored by hand. The documented recovery, `manage-references set-list --values
  ""`, exits 2 because the executor strips empty-string arguments; `--values=` works. Seen
  once. Graded high by the operator in the `lessons-routing` session. Not verified at HEAD
  and not owned by any staged plan. — source: inbox message `lessons-routing-010.md`
  (retired lesson `2026-10-05-17-002`), 2026-10-09.
- **The housekeeping delta rule PLAN-LB-32 shipped has three gaps.** (1) It decides "edited
  since the last firing" by file modification time
  (`.claude/skills/finalize-step-lessons-housekeeping/scripts/affected_lessons.py`, lines
  245 and 339). `restore-from-plan` moves a lesson file and keeps its old modification time,
  so a lesson restored after the last firing is carried over without ever being judged; the
  spec required a content hash for this reason. (2) The rule applies after the corpus has
  been enumerated with every lesson body, and the empty-corpus exit records no firing time,
  so the firing after an empty one is a full run. (3) Unconfirmed: the imported helper finds
  the bundles root by walking up from the working directory, so a firing whose script runs
  from the main checkout while given the worktree path would fall back to a full run every
  time; the tests pin the root and cannot see it. Also left: one document still names the
  retired `modified_files` field (`.claude/skills/recipe-plan-review/SKILL.md`, lines 70 and
  86). Not owned by any staged plan. — source: read-only review of `ef7d36617`, 2026-10-10.
- **Dispatch-boundary rows carry no step id, on three landings in a row.** PLAN-LB-23 (30 of
  34 rows), PLAN-LB-29 (38 of 38) and PLAN-LB-32 (54 of 54) recorded their dispatch
  boundaries without a step key and with all four context-load figures unmeasured. The
  effect is that no landing can say what a finalize step cost: the figures this ledger
  quotes for housekeeping and plugin-doctor re-fires are estimates from row shape. The flag
  is optional, so the omission is silent. Not owned by any staged plan; it is what every
  cost decision in this epic is measured with. — source: inbox messages
  `lb-23-verify-builds-013.md`, `plan-lb-29-harness-sync-010.md`,
  `lb-32-head-dependent-step-refire-005.md`.
  - **Seventh landing: PLAN-LB-38**, 16 of 16 rows keyless, 0 firings paired. — source: inbox
    message `plan-lb-38-review-gate-and-empty-scope-003.md`.
  - **Sixth landing: PLAN-LB-25**, every row keyless in every phase; finalize rows stop at
    08:35Z while finalize dispatched until about 15:54Z, covering 1.6 of 8.08 million finalize
    tokens. — source: inbox message `lb-25-phase-and-merge-gates-011.md`.
  - **Fifth landing: PLAN-LB-28**, 28 of 28 rows keyless, 0 of 47 firings paired; the message
    names the cause as call sites that do not forward `--step-id` and the four context-load
    figures they hold. — source: inbox message `lb-28-java-consumer-repos-006.md`.
  - **Fourth landing, and rows now go missing too.** PLAN-LB-33: the ledger holds 10 execute
    and 15 finalize rows that stop hours before the last dispatches (at least 23 later
    dispatches have no row), all 26 keyless, 0 of 38 firings paired. The proposed remedy is
    to record the boundary at the dispatch seam with `--step-id`, or to fail a phase exit
    whose boundary rows and dispatch lines disagree. — source: inbox message
    `lb-33-leaf-test-scope-and-executor-002.md`.

> ↪ Relocated to `settled.md` § "Self-review entries closed by its retirement" — the pre-submission self-review step was retired by PLAN-LB-37 (#1758) and no file of it remains; re-raise a defect against the functional or code review if it recurs there.

- **Leaf test scope after PLAN-LB-33 (#1745): narrowed only inside one bundle.**
  `resolve-test-scope` now names the top-level test trees and maps `marketplace/targets/`,
  but forces divergence for both, so a change there still runs whole-tree — the PLAN-LB-29
  case is unchanged. Narrow units are offered only for a footprint in exactly one bundle; a
  multi-module footprint gets none. The path is prose-driven: no script calls
  `architecture resolve --narrow-unit`. — source: read-only review of `370f42379`
  (`_test_scope_divergence.py:489-498`, `:116`), 2026-10-10. Not owned by any staged plan.
  - The reverse gap: root-level tests (`test/test_harness_shape_guards.py`) run only in the
    whole-tree run, so a module-scoped verification never sees them; they failed PLAN-LB-34
    twice, late. Reported by that plan, not re-checked here. — source: inbox message
    `lb-34-self-review-surfacing-foundation-and-java-001.md`.
  - Third plan in a row: PLAN-LB-38's pre-push gate failed twice on the same guard after every
    per-deliverable run was green; the fix commit re-fired three finalize steps. Recorded on
    lesson `2026-10-11-16-003`. — source: inbox message
    `plan-lb-38-review-gate-and-empty-scope-002.md`.
  - Second plan in a row: on PLAN-LB-25 every local gate passed and CI failed on
    `test/test_harness_shape_guards.py` rule R5, because the pre-push gate judged
    `divergence_possible=false` and skipped the whole-tree run; a later round hit the
    whole-tree-only marketplace quality test the same way. Lesson `2026-10-11-16-003`. — source:
    inbox message `lb-25-phase-and-merge-gates-004.md`.
- **Merge-lock ownership is keyed on `plan_id`, not session** (accepted residual of PLAN-LB-25).
  A second finalize session of the same plan is admitted as `already_held`
  (`merge_lock.py:1497-1498`) and either session's release removes the other's lock
  (1922-1939); the landing-gate failure path in `branch-cleanup.md` (1688-1693) releases after
  an unobserved enqueue already released (1562-1566), against its own invariant 4 (line 120).
  Low likelihood (needs two live finalize sessions of one plan). Lesson `2026-10-11-16-004`
  proposes an acquisition token required on release. Not owned by any staged plan; PLAN-LB-38
  (running) edits `merge_lock.py` for the rate-window wait only. — source: inbox message
  `lb-25-phase-and-merge-gates-006.md`; read-only review of `3ff307ddd`.
- **Leaves fall back to `git grep` because Grep and Glob are not granted to them.** Five
  leaves on PLAN-LB-33 reported the denial; three used `git grep`, two left a claim
  unverified. `architecture search --content` answers "which file", not "which line", and
  does not walk `.claude/**`. Lesson `2026-10-10-20-008`. Not owned by any staged plan.
  — source: inbox message `lb-33-leaf-test-scope-and-executor-007.md`.
- **PLAN-LB-28's test ladder needs discovery re-run in each Maven consumer.** The
  test-artifact detection is persisted in `metadata.reactor_test_artifacts` at discovery, and
  the overlay reads persisted data, so a consumer keeps `test -pl X -am` until discovery is
  re-run there after the harness sync. Detection reads only a module's own `<dependencies>`
  (not a parent POM, profile or property-interpolated coordinate). Two smaller gaps: a
  truncated reactor log holding only some summary blocks is summed and stamped `measured`;
  epilogue header lines (`Failures:`, `COMPILATION ERROR :`, `symbol:`, `location:`) are
  still filed as issues. Not owned by any staged plan; the re-discovery is an operator step
  per consumer. — source: read-only review of `2fd164ec9`, 2026-10-11.
- **Flaky test in the merge group:**
  `test/plan-marshall/manage-execution-manifest/test_decision_rules_early.py::TestEarlyTerminateTaskQueueGuard::test_falls_through_when_task_queue_in_progress`
  failed with `FileNotFoundError` on a temp-file rename in a shared scratch directory; a
  re-enqueue passed. Seen once. — source: PLAN-LB-33 landing residue.
- **Per-task tests have no runnable scope on two landings in a row** (partly closed by
  PLAN-LB-33; see the entry above for what is left). `resolve-test-scope`
  maps only paths under `marketplace/bundles/` and test directories named after a bundle;
  everything else returns no target and falls back to a whole-tree run that is too long for
  a dispatched step. On PLAN-LB-29, 11 of 17 execute dispatches stopped to hand that run
  over, at 3.9 million tokens; on PLAN-LB-23, 5 of 7, and three test failures surfaced only
  at batch runs. Lessons `2026-10-09-13-001` and `2026-10-09-15-001` carry the two halves of
  the remedy. Not owned by any staged plan; the cost is of the size that got PLAN-LB-32
  staged. — source: inbox messages `lb-23-verify-builds-004.md` and
  `plan-lb-29-harness-sync-002.md`; the mapping was read at
  `script-shared/scripts/build/_test_scope_divergence.py` § `_module_for_path`, `4ed67e228`.

## Watches

- **OpenCode runtime quality — PLAN-LB-39, PLAN-LB-31, PLAN-LB-26.** By operator decision,
  these three run under **OpenCode**, not Claude Code, and the run is an evaluation of
  OpenCode's quality as well as of the implementations. Each emitted command carries the
  suffix "Important: Strictly comply to the process / rules. Non compliance is not faster but
  a complete failure". At every landing, assume the implementation is missing or wrong until
  ground truth proves otherwise: check each spec deliverable against the merged diff, and
  check that its tests really test the behaviour (no weakened assertions, no rewritten
  acceptance criteria). Separately grade process compliance: phase boundaries kept, sub-agent
  dispatch versus inline, the executor used, CI abstraction used, findings triaged through
  manage-findings, and the landing-facts block complete with real token and step figures (the
  opencode `total_tokens=0` recurrence in Open Defects). Record an OpenCode grade per plan in
  its landing record. — trigger: each of the three landings; retire after all three are
  analyzed and graded.

> ↪ Relocated to `settled.md` § "Watches retired on 2026-10-14" — each trigger was met: the self-review was retired, the Antigravity zero-token watch became an Open Defect, the review-step migration went to PLAN-LB-40, and the three footprint-less plans were deleted and the gate read determinate.

- **The rate-window recovery PLAN-LB-24 shipped has not been seen working live.** Its own
  pull request recovered only by hand (two escalated commands posted by the main context),
  and PLAN-LB-33's leaf ran the earlier text. — trigger: the next landing whose review met a
  CodeRabbit quota refusal; read whether item 7a waited and re-dispatched without an
  operator step. Retire on one clean recovery.
- **Head-dependent finalize steps re-fire in full on every fix commit.** PLAN-LB-22 recorded
  a refusal to declare `verdict_inputs` for the two steps it examined; lessons-housekeeping
  and plugin-doctor fired seven times each with identical results. Lesson
  `2026-10-08-21-003` carries the proposal. — trigger: stage it as a plan if the next two
  landings report the same cost.
  - **Staged on 2026-10-09 as PLAN-LB-32, at high priority, by operator instruction; running
    since the same day.** Retire this Watch when PLAN-LB-32 lands and one later landing
    reports the two steps' re-fires as carried over or skipped.
  - **What PLAN-LB-32 leaves open, on purpose:** the other eight head-dependent steps still
    re-fire in full on every fix commit — among them the pre-push gate and ci-verify, which
    the retired lesson names. After PLAN-LB-32 lands, read the next landing's finalize cost
    by step before deciding whether any of them needs the same treatment. — source: inbox
    message `lessons-routing-005.md`, 2026-10-09.
  - **PLAN-LB-32 landed on 2026-10-10 and this Watch stays open.** The cost it was staged
    against is the dispatch of each re-fire, about 100,000 to 125,000 tokens for
    housekeeping, and nothing it shipped avoids a dispatch: plugin-doctor's skip was refuted,
    and housekeeping's delta rule and its empty-corpus exit both run inside the dispatched
    step. Its own run: 11 and 10 firings. Only a decision the dispatcher can take from a
    script before dispatching saves that cost — for housekeeping, "no active lesson" and
    "nothing a lesson depends on changed"; lesson `2026-10-10-06-002` carries the first. The
    standard rules out a derived verdict surface, so this needs a design decision, not only
    a fix. Retire when a landing reports the two steps' re-fires as not dispatched.
  - **Trigger met on 2026-10-09.** Of the two landings
    since, PLAN-LB-30 had no fix commit and so no re-fire; PLAN-LB-23 had both steps fire
    eight times with identical verdicts ("0 rm, 0 promo, 0 adapt, 64 keep"; plugin-doctor
    clean), at a floor of 1,680,033 tokens, and its decision log reached 710 entries
    because each firing logs one line per retained lesson. That is three landings with the
    cost (PLAN-LB-14 five firings, PLAN-LB-22 seven, PLAN-LB-23 eight). The message adds
    two proposals to the lesson's: a delta prefilter for housekeeping, and one aggregate
    log line per firing. — source: inbox message `lb-23-verify-builds-003.md`.
- **The archived-epic tree left `main`** (#1717, `1e556f15d`: archived plans and orchestrator
  records moved to plan-marshall-telemetry). Claims in the live specs that cite a file under
  `.plan/archived-orchestrators/` were corroborated before that move and can no longer be read
  in this repository. — trigger: when a launched plan's outline reports such a claim as
  unreadable, point it at the telemetry repository.
- **Harness installs still lag the source after a landing unless the repin is applied.**
  PLAN-LB-29 shipped the report and the repin, but the repin is off by default
  (`registry-repin` is `disabled` on the machines seen so far), so finalize reports
  `behind` and a session keeps running the older skill text until someone runs
  `sync.py --repin` and restarts. PLAN-LB-23's orchestrator followed a stale cached
  workflow document for exactly this reason. — trigger: before trusting a skill's
  behaviour right after a landing, read the sync's `registry_parity` block; retire when
  the operator has decided the setting for each machine.
- **`plan-pr-078-review-bot-fleet-opt-in` is still listed as in progress at finalize** with a
  dead worktree pointer and its archive step never run; four consumer checkouts are still on
  its merged branch. — trigger: clean up by hand or when the worktree-pointer fix
  (`backlog.md` § 1.14) is promoted.
