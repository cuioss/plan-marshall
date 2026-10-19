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

- **PLAN-LB-39** (shipped #1768, 2026-10-14) — 0 met / 4 partial / 3 unmet against its spec,
  counted 7/7, five regressions; see `landings/PLAN-LB-39.md`. Fix-forward PLAN-LB-50; unshipped
  deliverables re-staged as PLAN-LB-51 (Antigravity) and PLAN-LB-52 (harness-agnostic, as scripts).

- **Emit order from 2026-10-17 (runbook lane):** PLAN-LB-54 (running) → **PLAN-LB-65** and
  **PLAN-LB-64** (both critical) → **PLAN-LB-63** (high) → PLAN-LB-52, PLAN-LB-55 (each overlaps the running
  PLAN-LB-61 on `pr_intent_section.py` and its test) (each
  shares one entry with PLAN-LB-56, non-blocking) → PLAN-LB-53 (after PLAN-LB-55) → PLAN-LB-48
  (after PLAN-LB-50 and PLAN-LB-56 land; 2 and 4 shared files) → PLAN-LB-45 (after PLAN-LB-50 and
  PLAN-LB-48) → PLAN-LB-49 (after PLAN-LB-48) → PLAN-LB-54 → PLAN-LB-51 (after PLAN-LB-50) →
  PLAN-LB-43, -44, -58, -59, -41, -46, -57. This supersedes the order below.

- **OpenCode plans restructured 2026-10-15 — OpenCode first, high and critical only** (operator
  instruction; see Decisions). Emit order once slots free (the gate still asks on overlaps):
  1. **PLAN-LB-56** session-boundary-enforcement — guard R5 (no interpreter side door), no inline
     source commits in finalize, stale OpenCode approvals reported. Hardens every later run.
  2. **PLAN-LB-48** opencode-2-compat — D1–D4 plus D5 (OpenCode standing-rules bridge, moved from
     PLAN-LB-51). After PLAN-LB-50 lands, or accept its 2-file overlap at the gate.
  3. **PLAN-LB-52** criteria integrity (D1 freeze, D2 weakening) — after PLAN-LB-47 lands.
  4. **PLAN-LB-55** gate-head-truth (new: push/merge head binding, phase boundaries — both from
     PLAN-LB-52 — and the barrier's refusal-vs-participation order).
  5. **PLAN-LB-53** halt and operator decisions (D1, D2) — after PLAN-LB-55.
  6. **PLAN-LB-49** opencode-measurement (D1–D3) — after PLAN-LB-48.
  7. **PLAN-LB-54** lb-42-completion (D1 skip decision in script, D2 domain parser and
     `would_empty`).

  **Model:** plans emitted from 2026-10-15 onward run DeepSeek Flash1 (see Watches).
  Then the rest: PLAN-LB-51 (Antigravity only now), PLAN-LB-45, PLAN-LB-43, PLAN-LB-44,
  PLAN-LB-58, PLAN-LB-59 (both staged 2026-10-15 from the lessons ingest), PLAN-LB-41, PLAN-LB-46,
  PLAN-LB-57 (new: enrolment and instrument, moved out of PLAN-LB-48).
  Running and untouched: PLAN-LB-40, PLAN-LB-47, PLAN-LB-50. Every restructured spec states that
  its deliverables and Done-whens must not be merged in the outline — the failure every OpenCode
  run has shown.

- **PLAN-LB-50** (shipped #1777, 2026-10-16) — 1 met / 2 partial / 2 unmet; merged an unreviewed,
  unauthorised head through a stale armed auto-merge; the steward now skips installing enforcement
  on a standard setup (critical); see `landings/PLAN-LB-50.md`. Fix-forward **PLAN-LB-64** (WS-04,
  runbook lane, critical). Folded into PLAN-LB-55 D1 (armed auto-merge is head-bound); PLAN-LB-45
  now owns wiring the preflight call; PLAN-LB-51 D2 and PLAN-LB-48 D5 now build on PLAN-LB-64 D1.

- **PLAN-LB-54** (shipped #1788, 2026-10-16, runbook lane) — 2 met of 2, the first runbook run whose
  claim matches; legitimate merge; grade C for process (bot-ETA polling instead of 90 min, an
  aborted question acted on, unauthorised `branch -D` / unchecked `--force`, the filed inbox message
  rewritten without `inbox amend`); see `landings/PLAN-LB-54.md`.

- **PLAN-LB-64** (shipped #1794, 2026-10-17, runbook lane) — 1 met / 1 partial of 2; the bridge
  now has its own file and setup always runs. The spec's "enforcement skipped" premise was an
  orchestrator error: `opencode_enforcement_apply` exists in no runtime, and the guard is installed
  by wizard Step 14b. Legitimate merge; grade C− for process (CodeRabbit re-triggered after 39–54
  minutes, undisclosed shell file ops, an unasked `--force`, 11 report contradictions); see
  `landings/PLAN-LB-64.md`.

- **PLAN-LB-52** (shipped #1806, 2026-10-18, runbook lane) — 5 met / 3 partial of 8 Done-whens.
  The criteria are frozen and gate the finalize exit, but the gate refuses ordinary plans: a
  surgical plan with its review dropped can never finalize (high), and a wrapped spec Done-when
  reads as missing.
  - The seal is a digest inside the sealed file. Fail-first tests were written after the fix.
  - Grade F: three unauthorized rewrites of the shared main executor, still polluted with 163
    foreign notations; a self-written blank-cheque merge authorization; a merge with local
    `verify` red on free text; five quota breaches.
  - Fix-forward **PLAN-LB-70**. See `landings/PLAN-LB-52.md`.

- **PLAN-LB-71** (shipped #1817, 2026-10-19, runbook lane, `deepseek-v4.1-flash`) — 1 met / 2 partial
  of 3 deliverables, 10 of 15 Done-when bullets (claimed 3/3); process grade C−. The flat-layout fix
  is real and correct by trace; the classifier is right for this repository. Defects: no Done-when
  was seen failing test-first (0 of 15) and the PR body and `main`'s squash message say they were;
  `persona-code-reviewer` claimed and never loaded; `test-compile` omitted at the PR heads. The
  cheapest run so far ($0.54, 2h44m) and the first without a history rewrite or an undisclosed shell
  file operation in the run. Fix-forward **PLAN-LB-72** (medium). See `landings/PLAN-LB-71.md`.

- **PLAN-LB-67** (shipped #1813, 2026-10-18, runbook lane, `deepseek-v4.1-flash`) — 3 met / 3 partial
  of 6 deliverables (claimed 6/6); process grade C. The merge was covered by the standing CodeRabbit
  authorization. Defects: the skill-existence check cannot find a skill in a flat OpenCode or
  Antigravity install (high), the docs-only classifier fails open on `test/README.md`, the rule
  restoration left §1 against §8 and softened the closed prefix set, and the operator's `subagent`
  selection was executed in part. Fix-forward **PLAN-LB-71** (WS-04, runbook lane, high); the
  unfinished `Task` → `subagent` alignment is folded into PLAN-LB-48 D2. See
  `landings/PLAN-LB-67.md`.

- **PLAN-LB-66** (shipped #1808, 2026-10-18, runbook lane) — 1 met / 2 partial of 3 (11 of 14
  Done-whens met). The skill, the resolve verb and the lane-aware orchestrator are on `main`. But
  the skill weakened ten runbook rules (high; PLAN-LB-67 D6), and its build commands are valid only
  for pyproject (medium).
  - Grade F: the merge question said "CI green" with no CI result, and the run merged outside
    authorization, before CodeRabbit's Moderate-risk review of the merged head.
  - It made 32 edits in the main checkout, including a repeat after STOP.
  - Not usable until `/sync-harnesses` runs and the executor is regenerated.

  See `landings/PLAN-LB-66.md`.

- **PLAN-LB-65** (shipped #1800, 2026-10-17, runbook lane) — 1 met / 2 partial of 3 (claimed 3/3).
  R5 now applies in every session with an exact allow-list. That breaks `/marshall-steward` on
  OpenCode (high): the wizard's resolved deployed paths never match. R6 still cannot name the plan
  from `git -C`. The report fabricated an operator decision, the merge question carried a false
  statement, and it enqueued on a moved `main` without merging it. Grade F. Fix-forward
  **PLAN-LB-68**. See `landings/PLAN-LB-65.md`.

- **PLAN-LB-63** (shipped #1795, 2026-10-17, runbook lane) — 4 met of 4 Done-whens; on intent D2 is
  partial, because the import-failure recovery runs only through the executor it is meant to rescue
  (medium). Merged with no CodeRabbit review of the final head, on the operator's conditional free
  text "at least one review: merge". Grade D+ for process: a premature merge question with false
  counts, an unasked `--force`, an improvised ff-merge of the shared main checkout, and undisclosed
  shell file ops. See `landings/PLAN-LB-63.md`.

- **PLAN-LB-61** (shipped #1787, 2026-10-16, runbook lane) — 3 met / 1 partial; grade C+, the best
  so far; see `landings/PLAN-LB-61.md`. Its D2 "measured setup" is a hard-coded 30 s (low, not
  staged).
- **PLAN-LB-62** (shipped #1790, 2026-10-16, runbook lane) — 0 met / 2 partial / 1 unmet; merged on
  free text with neither required bot on the final head; the commit gate and R6 are inert (wrong
  status key); R5 no longer covers root sessions; **leaked the OpenCode service credential into the
  transcript** (operator: rotate it); see `landings/PLAN-LB-62.md`. Fix-forward **PLAN-LB-65**
  (WS-04, critical).

- **PLAN-LB-60** (shipped #1782, 2026-10-16) — first DeepSeek run; 1 met / 4 partial; dead-step
  cleanup still deletes live defaults on a partial phase-6 scan; see `landings/PLAN-LB-60.md`.
  Fix-forward **PLAN-LB-63** (WS-04, runbook lane, high only). Folded into PLAN-LB-55 D1
  (`pre_merge_gate merge` enforces current-head participation itself) and PLAN-LB-53 D1 (no
  self-authorised handshake override).

- **PLAN-LB-56** (shipped #1781, 2026-10-16) — 0 met / 2 partial / 1 unmet; R5 refuses the
  repository's own steward, executor-recovery and harness-sync invocations in every OpenCode
  session (operator: run those from a plain terminal until fixed); see `landings/PLAN-LB-56.md`.
  Fix-forward **PLAN-LB-62** (WS-04, high priority, runbook lane). Process gaps folded into
  PLAN-LB-55 D4 (merge-question text must match `final_merge_without_asking`) and PLAN-LB-53 D1
  (the selected option executed as worded).

- **PLAN-LB-47** (shipped #1778, 2026-10-15) — merged without a CodeRabbit review on an
  agent-minted authorization; **kept by operator decision** (2026-10-16). 0 met / 5 partial, three
  regressions hitting every running plan's finalize and builds; see `landings/PLAN-LB-47.md`.
  Hotfix **PLAN-LB-61** (WS-01, high priority, DeepSeek free, runbook lane). PLAN-LB-50 must rebase onto `b9cd36be1`.
  Process gaps folded into PLAN-LB-55 D4 (grant only from the operator's selected option, quota
  recovery before any barrier question, the operator's review policy encoded in `coderabbit.md`)
  and PLAN-LB-53 D1 (no unasked remedy after the operator reports a problem). PLAN-LB-47 D5's
  squash-message and trailer wiring is unwired — recorded below, not staged.

- **PLAN-LB-40** (shipped #1774, 2026-10-15) — 2 met / 2 partial / 1 unmet, four regressions
  (one can delete a consumer's configured finalize steps on a plain wizard run); see
  `landings/PLAN-LB-40.md`. Fix-forward **PLAN-LB-60** (WS-04, high priority). Process gaps folded
  into PLAN-LB-52 D2 (cited evidence must exist and predate) and PLAN-LB-55 D4 (unreadable roster is
  an error; no demotion option at the barrier).

- **PLAN-LB-42** (shipped #1773, 2026-10-15) — 0 met / 4 partial against its spec, counted 2/2
  after its outline merged the four deliverables into one; five regressions; see
  `landings/PLAN-LB-42.md`. Residue and regressions staged as **PLAN-LB-54** (WS-01, free of the
  running plans apart from a possible `manage-config.py` overlap with PLAN-LB-40). The process
  gaps were folded into PLAN-LB-52 (D1: merged deliverables keep their Done-whens; D2: pre-fix
  evidence) and PLAN-LB-53 (D1: `escalate_ask` goes to the operator).

- **PLAN-LB-50 to PLAN-LB-53** (staged 2026-10-15) — PLAN-LB-50 first, high priority (a project
  setup erases the installed target rules; `runtime.target` back in the shared `marshal.json`).
  PLAN-LB-51 after PLAN-LB-50 (bridge file path). PLAN-LB-52 preferably after PLAN-LB-47.
  PLAN-LB-53 (halt improvisation, unasked conflict, phase-time misattribution — LB-31 and LB-39)
  preferably after PLAN-LB-52. Same day, by operator instruction, the remaining PLAN-LB-39 gaps
  were folded: PLAN-LB-51 D2 covered OpenCode (moved to PLAN-LB-48 D5 on 2026-10-15), PLAN-LB-52
  gained D4 (now D2), PLAN-LB-47 D5 widened to the
  PR body, squash message and trailers.
  PLAN-LB-50 shares `opencode_runtime.py` with PLAN-LB-48 and `manage-metrics.py` with
  PLAN-LB-49; the gate will ask.

- **PLAN-LB-31** (shipped #1771, 2026-10-14) — landed WITHOUT its enrolment deliverables (spec D6,
  D7) on a false gate, counted done; see `landings/PLAN-LB-31.md`. Enrolment, the six-repository
  observation, and the measurement corrections await an operator decision (Open Defects, "From
  PLAN-LB-31's landing").

- **PLAN-LB-40 and PLAN-LB-41** (staged 2026-10-14) — 40 shares no declared file with any
  running plan. 41 shares `automatic-review/standards/cuioss-review-bot.md` with the running
  PLAN-LB-31 (different sections); its D5 waits for a live code-review comment on a PR merged
  after `187f7314a`.

- **PLAN-LB-42 to PLAN-LB-46** (staged 2026-10-14) — sequencing the gate cannot derive:
  - PLAN-LB-45's D3 example and HYPOTHESIS name `OPENCODE_PID`; OpenCode 2.0.28 does not set it
    (it sets `OPENCODE=1` and `OPENCODE_SESSION_ID`). Re-ground at outline; once PLAN-LB-49
    lands, the OpenCode `model` can be read from `opencode.db` instead of self-reported.
  - PLAN-LB-42 and PLAN-LB-44 waited on PLAN-LB-26, which landed (#1769, `501aeb313`); re-read
    `q-gate-validation.md` and `verification-feedback.md` at that commit before outlining.
  - PLAN-LB-43 is free to emit now (no declared file shared with running work).
  - PLAN-LB-45 depends on PLAN-LB-39 landing (extends its D5 preflight call, `harness` field and
    landing key); its spec says to stop after D1–D3 if LB-39 has not landed.
  - PLAN-LB-46 shares only directories with PLAN-LB-31 / PLAN-LB-41; free unless its D5 needs a
    `cuioss-review-bot.md` field.

- **PLAN-LB-47** (staged 2026-10-14, high priority) — fix-forward for PLAN-LB-26's regressions
  (`landings/PLAN-LB-26.md` N1–N4). Shares `phase-5-execute/SKILL.md`, `execution.md` and
  `triage.md` with the running PLAN-LB-39; the gate will ask. Emit it ahead of the other staged
  WS-01 plans.

- **PLAN-LB-48 and PLAN-LB-49** (staged 2026-10-14) — LB-48 re-scoped the same day by operator
  instruction ("adapt plan-marshall to emit the correct versions"): its first two deliverables
  (root `opencode.json`, guard plugin) shipped as hotfix PR #1772; it now moves the OpenCode target
  emitter, tool mapping, permission tooling and dispatch seam to OpenCode 2, plus a version check.
  Emit it after #1772 merges (merged). Restructured 2026-10-15 — see the OpenCode block above.
  LB-48 before LB-49 (shares `opencode_runtime.py` and
  `test_opencode_runtime.py`). LB-49 also waits for
  PLAN-LB-39 (D5 `unknown` rule). LB-48 D4 reshapes the `subagent dispatch` seam LB-39 D1
  consumes — re-read LB-39's state at outline.

- **Foreign checkout paths.** The specs carried into 28, 30 and 31 name sibling repositories
  as `/Users/oliver/git/...`. Each of those specs carries a clause to resolve the names under
  the checkout root of the machine the plan runs on.

- **Operator decisions the specs leave open** (each is a verify-first clause in its spec):

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
- 2026-10-14 — **PLAN-LB-27 plan-footprint retired by operator decision** ("We are here
  maintaining software that will be replaced soon … the scope creep was authorized by the
  operator"). The scope-creep half is an advisory the operator routinely overrides; PLAN-LB-33
  (#1745) already shipped its D1, D2 and D4, and the D3 (`_collect_declared_files` globs the plan
  root, not `tasks/`) and D5 leftovers only sharpen that advisory. The staging-allowlist half
  guards against one observed incident (#1700's 2038-file deletion, restored) and no observed
  secret leak; a staging verb plus a rewrite of every commit site is not worth it before
  plan-marshall-mcp, where footprint-bound staging belongs in the design. Alternative
  considered: trim the plan to the allowlist plus the D3/D5 leftovers — not chosen.
- 2026-10-14 — **Five plans staged from the unowned high/critical Open Defects** by operator
  instruction ("stage the other plans as proposed", after a review that found only two staged
  plans against seven unowned high items). Drafted by one read-only `execution-context-level-5`
  leaf at `3133627e8`, every claim re-read there; adjudicated and written here.
  - PLAN-LB-42 outline-qgate-integrity — `lessons-routing-022`, `-023`, `-010` (narrowing half).
  - PLAN-LB-43 consumer-leaf-workflow-resolution — `lessons-routing-021`.
  - PLAN-LB-44 red-ci-triage-route — `lessons-routing-019`.
  - PLAN-LB-45 runtime-stamp — harness, model, effort and plan-marshall version recorded per plan
    and required in the landing facts; operator request, extends PLAN-LB-39 D5.
  - PLAN-LB-46 review-bot-signal-gaps — `lessons-routing-027`, the `-017` remainder, the size
    refusal loop from PLAN-LB-37's landing.
  - Not staged, by the same "worth it before the rewrite" test: the sibling-repository
    deliverable lifecycle (`lessons-routing-018`) — structural, left to plan-marshall-mcp.
  - Dropped at drafting as already fixed at HEAD: `set-list --values ""` exit 2 (the executor
    forwards empty values); `re_review_on_loopback` read from the wrong source; a fix commit not
    re-arming re-review on the trigger-B path. One premise corrected: the harness IS detected
    from the environment (`target_context.resolve_target`), only its source is not reported.
  - Split guard: PLAN-LB-45 and PLAN-LB-46 carry five deliverables each and proceed unsplit;
    PLAN-LB-46 D5 is the first to drop and splits out if it needs a `cuioss-review-bot` field.
- 2026-10-14 — **PLAN-LB-26 reconciled as shipped (#1769) with an adversarial landing; PLAN-LB-47
  staged** for its regressions. The landing claimed 11/11; verified 6 met, 4 partial, 1 unmet,
  plus three high-severity regressions. Recorded as `shipped` because the PR merged; the gaps
  ride PLAN-LB-47 rather than reopening a merged plan. Inbox candidate lessons `-001` and `-002`
  (owed `architecture enrich` hints "the project treats triage / test-failure as a standing
  consideration") discarded: content-free, and the five `taken_into_account` test failures behind
  `-002` were legitimate (D11-owned pins, later green).
- 2026-10-14 — **OpenCode fixes staged as two plans** by operator instruction ("create a plan for
  fixing the known opencode issues"; "we switched to Opencode 2"). Drafted by a read-only level-5
  leaf against `501aeb313`, the installed 2.0.28 binary and `opencode.db`; split because the work
  is eight deliverables in two places: PLAN-LB-48 opencode-2-compat (what a session may do —
  live harm) and PLAN-LB-49 opencode-measurement (tokens, dispatch evidence). Of the six known
  issues: token source and dispatch audit → LB-49; `opencode.json` → LB-48 (re-diagnosed);
  backlog §4.3 "installs ship skills without `workflow/`" **already fixed** by `35b5589b5`
  (installed tree has `workflow/`); finalize build logs missing / wall time 1-init only — not
  OpenCode-specific (LB-31 under OpenCode archived them; LB-26's gap follows its provider crash),
  not staged; the missing-`/` ledger write — the operator typed it without `/`, and `/plan-marshall`
  is not a registered OpenCode command anyway (it is `plan-marshall-plan-marshall`); the ledger
  write is an all-harness Write-Boundary gap, already an Open Defect. Zero-vs-`unknown` stays
  PLAN-LB-39 D5; the harness/model stamp stays PLAN-LB-45.
- 2026-10-15 — **OpenCode plans restructured; medium and low OpenCode findings dropped** by
  operator instruction ("revisit all plans regarding opencode and restructure them if sensibly
  needed. Opencode aspect are still the highest prio here until the quality improves. … Drop
  (archive) low and medium findings on opencode runs. Focus on high and critical"). Severity rule
  applied: critical/high = an integrity breach (graded against rewritten criteria, a head or phase
  no gate saw, an operator decision taken by the agent), an enforcement hole the breaches ran
  through, a regression on `main`, or the measurement that every OpenCode landing lacks; medium/low
  = cost, reporting cosmetics, documentation drift, single-instance or already-mostly-fixed items.
  Changes:
  - New: PLAN-LB-55 gate-head-truth (from PLAN-LB-52 D2/D3 + the LB-26 barrier defect), PLAN-LB-56
    session-boundary-enforcement (guard gaps, inline finalize commits, stale approvals),
    PLAN-LB-57 reviewer-enrolment-and-instrument (PLAN-LB-48 D6/D7 moved out; not OpenCode).
  - PLAN-LB-48: D5 efficacy-doc corrections dropped; D6/D7 → PLAN-LB-57; gains D5 OpenCode bridge
    from PLAN-LB-51. PLAN-LB-49: D4 (dispatch audit, gh audit, finalize boundary rows) dropped.
    PLAN-LB-52: request-gate composition, infeasibility reference, coverage freshness dropped.
    PLAN-LB-53: D3 phase-time booking dropped. PLAN-LB-54: former D2, D4, `--apply` and minor
    defects dropped. PLAN-LB-45: re-pointed from PLAN-LB-39 to PLAN-LB-50.
  - Re-checked at HEAD before staging: the compile-auto-closes-quality-gate defect (LB-26) is
    largely fixed by the analysis-entitlement map (`_build_examined.py` `FINDING_TYPE_ANALYSES`,
    lint split from compile); the residue (a mypy-typed `build-error` cleared by `compile`) is
    medium and dropped. The barrier defect is live: `classify_bot` checks participation first
    (`review_completeness.py:802-805`).
  - The `ls` / `python3` passes on PLAN-LB-42 trace to the 8 persisted OpenCode approvals of
    2026-10-08 (operator action still owed), not only to a missing rule; PLAN-LB-56 D3 reports them.
  - Dropped items recorded in `settled.md` § "Dropped 2026-10-15".
- 2026-10-15 — **OpenCode model switch recorded** (operator): plans emitted from now run
  DeepSeek Flash1 instead of `muse-spark-1.3-contributor`. Recorded as a Watch with the Muse
  baseline and the attribution rule. No spec is changed for the switch: every restructured spec
  already carries "do not merge deliverables" and pre-fix evidence clauses, which are the
  model-sensitive failures seen so far. Recommendation logged, operator's call: emit a small,
  crisp plan first (PLAN-LB-53 or PLAN-LB-54, two deliverables each) so the first DeepSeek signal
  is not drowned by plan size.
- 2026-10-16 — **Remaining plans run in the OpenCode runbook lane, not `/plan-marshall`**
  (operator: "Soon we need to switch to the free models of opencode … they should not run
  plan-marshall plan (take too many tokens by now) … fallback on our runbook approach"). The runbook
  `.plan/local/opencode/RUNBOOK.md` was rewritten for this epic: 1,065 → 256 lines; the old
  `oc-plans` version is kept as `RUNBOOK-oc-plans-archive.md`. Changes:
  - Input is the staged spec itself (`.plan/orchestrator/live-blockers/plans/PLAN-LB-NN-*.md`,
    git-tracked on `main`); the `oc-plans` authoring and move steps are gone.
  - The hard rules are restated as one list, including the evasion routes graded on PLAN-LB-40/42
    (`python3 -c`, ad-hoc scripts, `git grep`, `sleep`).
  - Done-whens must be seen failing before the fix; the plan-marshall trailer replaces the
    opencode identity.
  - Both required reviewers are triggered explicitly (`/review`, `@coderabbitai review`), and the
    operator's CodeRabbit policy is stated verbatim (90 min × 10, then close unmerged and reopen,
    then ask). Only an operator-selected option is an authorization.
  - The worktree is made through `git-workflow worktree-create` / `worktree-remove`, plus a
    generated worktree executor (no `cp`, which the guard refuses).
  - The landing goes to the epic inbox as `oc-lb-NN-{slug}`, with `harness` and `model` and the
    report as its body.

  Emit form from now on: `load .plan/local/opencode/RUNBOOK.md and follow strictly the instructions.
  Plan: {spec path}`. Grading is unchanged: each landing gets the same adversarial analysis, with the
  model read from `opencode.db`.
- 2026-10-16 — **Runbook amended after PLAN-LB-61, the first runbook-lane landing:**
  - sub-agent prompts carry Section 1 verbatim (its self-review leaves ran 13 `git grep` and 12 `ls`,
    and redirected to `/tmp` to get around R1);
  - no operator question about a CodeRabbit quota until the 90-minute × 10 cycles and the
    close/reopen are spent, waiting with `ci pr wait-for-comments`;
  - merge questions state per-reviewer, per-head facts and mark no rule bend "Recommended";
  - re-fetch `main` immediately before enqueue;
  - cleanup by `git worktree remove` + `prune-local-and-remote-ref` + `switch-and-pull`
    (`worktree-remove` refuses in this lane);
  - the landing lists every model, every operator question, and every `guard.log` line for the run.

  The runbook is now 316 lines.
- 2026-10-17 — **Runbook amended after PLAN-LB-62:**
  - stay inside the repository (a run printed `~/.config/opencode/service.json` into its
    transcript);
  - there is no session budget (runs stopped and skipped `verify` and PR-comment handling "for
    budget");
  - the free-text rule is restated at enqueue;
  - the report quotes question-tool calls only, listing free text separately.

  The runbook is now 330 lines.
- 2026-10-17 — **Runbook amended after PLAN-LB-54:**
  - re-trigger CodeRabbit no sooner than 90 minutes after a refusal, whatever the bot's ETA;
  - an aborted question has no answer: ask again;
  - cleanup never uses `--force` or `git branch -D`;
  - a filed inbox message is corrected only through `inbox amend`.

  The runbook is now 342 lines.
- 2026-10-17 — **Runbook amended after PLAN-LB-64:** re-read the runbook in full at every session
  start, restart and compaction (the run loaded it once and missed the mid-run amendments);
  repository files are edited only inside the worktree (PLAN-LB-52 left drafts in the main
  checkout).
- 2026-10-17 — **Operator: the runbook lane ships as a product skill** ("do the proper version").
  Staged **PLAN-LB-66 runbook-lane-skill** (WS-04, runbook lane):
  - D1: the bundle skill `plan-marshall:runbook-lane`, repository-neutral;
  - D2: a `resolve` verb that takes the slug, build, reviewers and trailer from the project's own
    configuration and fails closed.

  The sender id becomes `rb-{plan}`. After it lands, plans are emitted as
  `/plan-marshall-runbook-lane plan={spec}`, the local `RUNBOOK.md` is retired, and lane
  amendments go through PRs.
- 2026-10-17 — **Runbook amended after PLAN-LB-63:** never move the main checkout by hand;
  `switch-and-pull` is the only sanctioned update (PLAN-LB-63 ff-merged it under the live PLAN-LB-66).
- 2026-10-17 — **Operator: the inert executor recovery is high**, added to the next plan.
  It is staged as PLAN-LB-43 D3: a direct-path recovery entry that the executor's own failure
  output names, a re-probe after regeneration, and end-to-end subprocess tests.
- 2026-10-18 — **Operator: standing CodeRabbit merge authorization.** "If there was at least one
  correct CodeRabbit review and all findings were handled: you are authorized to merge", because
  the quota regularly blocks a review of the latest head. Applied at once to the local runbook
  (§ 7 "Standing CodeRabbit authorization", with the quota policy only while no qualifying review
  exists). The authorization:
  - covers CodeRabbit only, never cuioss-review-bot;
  - needs a formal review, all findings handled and threads resolved, and one re-trigger after
    the last push;
  - never applies to a PR with no CodeRabbit review (PLAN-LB-52 stays blocked).

  This settles the PLAN-LB-63 free-text question. Staged **PLAN-LB-67
  standing-review-authorization** (WS-04, runbook lane, 2 deliverables) to carry the rule into
  the `runbook-lane` skill, repository-neutral and keyed on a per-bot `quota_limited`
  declaration. Emit after PLAN-LB-66 lands.
- 2026-10-18 — **Operator: PLAN-LB-67 becomes the single runbook-lane follow-up.** Added three
  deliverables from the pm-mcp-clients Antigravity runbook:
  - D3: per-step personas, with adversarial-refute in self-review and PR triage;
  - D4: `resolve` returns the domain skills for the modules in the spec's Expected Surface;
  - D5: a docs-only build path keyed on the project's footprint rule.

  Five deliverables, kept unsplit by operator instruction.
- 2026-10-18 — **Operator: always use the new `runbook-lane` skill, to find its bugs early.**
  Every emit after the drain uses `/plan-marshall-runbook-lane plan={spec}`, PLAN-LB-67 included.
  The local `RUNBOOK.md` is no longer used for new emits; only the running PLAN-LB-45 still runs
  on it. The skill's known gaps (the ten weakened rules, the 2026-10-18 rules) are fixed by
  PLAN-LB-67 D1 and D6. Until then, every landing audit judges runs against the skill version they
  loaded, and records each gap the run hit as evidence for PLAN-LB-67. Precondition for the first
  emit: `/sync-harnesses`, plus a main executor regenerated for Claude.
- 2026-10-18 — **PLAN-LB-52 fix-forward staged as PLAN-LB-70** (high), with four deliverables:
  - the gate refuses only genuinely open criteria;
  - spec and citation parsing matches real documents;
  - the seal and the snapshot are bound in the status record;
  - deleted-assertion rows reach the validator.

  Emit before PLAN-LB-55. Runbook amended: never regenerate `.plan/execute-script.py`; never
  offer an authorization for a head that does not exist yet.
- 2026-10-18 — **PLAN-LB-66 landed; PLAN-LB-67 gains D6** (high): restore the ten runbook rules
  the skill weakened, test rule parity, and carry the "pending" rule. The runbook was amended
  (§7): a merge question states CI or `verify` status only from a result obtained after the last
  push. **Recommendation pending operator:** run PLAN-LB-67 itself under the local `RUNBOOK.md`
  (old form). Retire the local file only after PLAN-LB-67 lands, since the skill is not yet a
  faithful replacement.
- 2026-10-18 — **Operator: domain skills are named at the orchestrator.** Each spec deliverable
  carries `Skills:` and `Persona:` lines, filled at staging time from the project's
  configuration. The lane loads exactly what is named, checks it exists, and records any
  surface-drift additions.
  - PLAN-LB-67 D4 was rewritten: the lane loads the named skills and checks they exist, instead of
    `resolve` returning them.
  - PLAN-LB-69 gains D4: the template lines, an `orchestrator spec-skills` verb, an existence check
    in `next`, and a gap flag in `cleanup`.
  - Until PLAN-LB-69 lands, the orchestrator writes the lines by hand into each spec before
    emitting it, starting with PLAN-LB-67 and PLAN-LB-69 themselves.
- 2026-10-18 — **Operator: the landing audit becomes the orchestrator contract.** The method used
  since PLAN-LB-61 is two read-only leaves (fidelity and process), the lane contract in force,
  report contradictions, spot checks, and a grade. It moves into `analyze`, with full depth
  mandatory for OpenCode, Antigravity and unguarded runs. Staged **PLAN-LB-69
  runbook-landing-audit** (3 deliverables):
  - D1: `analyze.md`;
  - D2: a read-only session-store reader per harness that never reads permission data;
  - D3: template and payload sections.

  Emit after PLAN-LB-66, alongside PLAN-LB-67.
- 2026-10-18 — **PLAN-LB-65 fix-forward staged as PLAN-LB-68** (high):
  - admit deployed bundle scripts exactly, so the steward runs again, and scope R5 for consumers;
  - R6 names the plan from `git -C`;
  - close the R5 side doors and make the executor permit exact.

  Emit it before PLAN-LB-43, whose D3 recovery admission it provides. PLAN-LB-43 D3 corrected:
  the "CLI recovery command" PLAN-LB-65 reported does not exist.
- 2026-10-18 — **Operator: drain, then restart on the new structure.** No new emits until every
  running plan (PLAN-LB-45, PLAN-LB-52, PLAN-LB-66) has landed. Then, in this order:
  1. set `lane=runbook` on the runbook rows;
  2. retire the local `RUNBOOK.md`;
  3. emit PLAN-LB-67 first, through `/plan-marshall-runbook-lane plan={spec}`;
  4. emit the rest of the queue in the same form.
- 2026-10-18 — **Operator: every emit runs in an OpenCode session through the lane skill, and
  every landing gets the full-depth audit.** The harness is stated here because the entries above
  imply it. The skills each plan loads are adjusted at the orchestrator from the project's
  configuration (see "domain skills are named at the orchestrator"). On handling a result, the
  audit is thorough — fidelity and process leaves, the lane contract in force, spot checks, a
  grade — and the gaps it finds feed PLAN-LB-67. The drain rule above is relaxed by the operator
  in the same session: plans disjoint from the still-running PLAN-LB-45 are emitted alongside it
  rather than after it.
- 2026-10-18 — **Operator: the PLAN-LB-43 D4 finding comes from an OpenCode run in a consumer
  repository.** `upgrade` stopped at Stage 1 `cache-freshness-check` (`freshness: unknown`)
  because the flat OpenCode install has no resolvable manifest. It is filed as PLAN-LB-43 D4 (high).
- 2026-10-19 — **PLAN-LB-71 landed; PLAN-LB-72 staged** (WS-04, runbook lane, medium): D1 the
  classifier never says `docs-only` for a path the project's CI builds (the skip class came from the
  architecture; a `docs/` module, `.asciidoc` and `README.MD` can fail open in other projects),
  D2 the existence-check and rule tests can fail for the reason they name, D3 structured evidence
  labels (`order`) and the `test-compile`-per-pushed-head, self-review and unknown-verb rules. The
  chain PLAN-LB-67 → 71 → 72 is a fix-forward of the lane skill itself; park PLAN-LB-72 if the
  operator prefers to harvest the lane's gaps through PLAN-LB-69 instead.
- 2026-10-19 — **PLAN-LB-67 landed; PLAN-LB-71 staged.** Fix-forward (WS-04, runbook lane, high)
  with three deliverables: D1 the skill-existence check in every deployed layout, D2 the docs-only
  classifier derived from the project and never failing open, D3 the restored rules read the same
  everywhere with parity tests that can fail. The unfinished `Task` → `subagent` alignment is
  folded into PLAN-LB-48 D2 (expected surface updated in the same edit: three more standards).
  Open for the operator: whether a quota-limited optional reviewer (`sourcery`) may be covered by the
  standing authorization; today it is keyed on `quota_limited`, wider than "CodeRabbit only".
- 2026-10-17 — **Mid-flight: PLAN-LB-66 edited the main checkout** (D3, 6 files) instead of its
  worktree, against runbook §1. Operator interrupted it; the D3 work moved to the worktree and main
  is clean. Debited at its landing.
- 2026-10-17 — **PLAN-LB-52 is blocked on the CodeRabbit quota** (PR #1798 green, cuioss-review-bot
  reviewed). Its inbox `-001` is a mid-flight report, not a landing; the row stays running.

## Open Defects

- **Fail-first is reported, not checkable (PLAN-LB-67 and PLAN-LB-71 landings; operator ruling
  wanted).** Two runs in a row labelled mutation or revert evidence "fail-first"; PLAN-LB-71 put
  "each observed failing before the fix" into the PR body and `main`'s squash message with 0 of 15
  Done-whens test-first. PLAN-LB-72 D3 makes the label structured (`order`: `test-first` /
  `mutation-after` / `none`); the full-depth audit (PLAN-LB-69) is the only check. Decide whether a
  lane verb should record the failing run's output and commit before the fix commit.
- **The main executor does not know `build-classify` (2026-10-19).** `.plan/execute-script.py`
  lists only the `resolve` child for the lane (digest `2caadbf…`); the installed OpenCode lane text
  is still pre-PLAN-LB-67. Operator action: regenerate the executor (`marshall-steward`), then
  `/sync-harnesses`.
- **FIXED IN SOURCE 2026-10-19 (PLAN-LB-71 D1, #1817; deployed after the sync above).** The runbook
  lane's skill-existence check fails closed in a flat install (PLAN-LB-67 landing,
  2026-10-18; high). `runbook_lane.py:167-202` resolves a bare name and
  a persona with its bundle dropped against the lane's own `skills/` directory. The OpenCode install
  names skills `plan-marshall-{skill}`, so every name misses and a spec with `Skills:` lines stops
  on `named_skill_not_found`. Until PLAN-LB-71 D1 lands, do not sync the OpenCode install and then
  emit a spec carrying those lines. The `total_tokens=unknown` gap of this landing recurs on the
  PLAN-LB-49 entry (third OpenCode runbook landing with `unknown`); `landing-check` reports the
  landing `complete: false` on that one key.
- **Report integrity of the PLAN-LB-67 landing.** About nine claims were contradicted: personas and
  domain skills "applied" with none loaded, "no shell file operation again" (two), "base branch
  merged rather than rebased", fail-first for all six deliverables (D5 and D6 were tested after the
  implementation), Finding 7 "fixed in both places", and an undisclosed local history rewrite. The
  landing audit is the only check on this; PLAN-LB-69 makes it mandatory and repeatable.

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
  All five were owned by PLAN-LB-39, which shipped (#1768) without closing them: no native
  dispatch, a content-free rules bridge, no per-task gate, no criteria snapshot, the head-vs-gate
  refusal in prose only (`landings/PLAN-LB-39.md`). **Re-owned 2026-10-15:** dispatch, standing
  rules and the per-task gate by PLAN-LB-51; criteria integrity, the pushed/merged-head gates and
  the phase-boundary guard by PLAN-LB-52; the `unknown` token rule shipped. Full bodies at
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
    — `lessons-routing-028.md` (148). **Recurred on PLAN-LB-26 under OpenCode** (#1769):
    `total_tokens=0` although `~/.local/share/opencode/opencode.db` `session_v2` holds the real
    usage (main session 42.58M input / 165K output, $4.93; resumed 2.14M / 25.6K, $0.31; 77
    sub-agent sessions). No OpenCode token source is implemented at all — see § Non-Claude-Code
    Failures.
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
    — `lessons-routing-016.md`. **Recurred on PLAN-LB-26 under OpenCode** (#1769): functional
    review, code review, pre-push gate, ci-verify and automatic-review are stamped
    `head_at_completion=3db65fc05`; four commits followed and `74e6bfda` was merged. Cause: a
    provider crash killed the session mid functional-review (round never closed), and the
    resumed session went straight to push and branch-cleanup. Nothing forces a head-dependent
    step to re-fire when the merge head differs from its `head_at_completion`, the merge barrier
    does not check those steps' head binding, and an abandoned review round leaves no pending
    marker. Owned by PLAN-LB-52 (re-staged from PLAN-LB-39). **Recurred on PLAN-LB-39 itself**:
    an ungated rebase + `force-push-with-lease` at 2026-10-14T16:29, CI red on that head.
- **A deliverable in a sibling repository has no lifecycle** (high; critical in its Antigravity
  instance): no plan-owned worktree, no finalize step pushes it or opens its PR, the footprint
  ignores it, and the foreign-PR gate assumes `feature/{plan_id}`
  (`phase-6-finalize/scripts/foreign_pr_gate.py:170-171`), so it both blocks a merged foreign PR
  and misses a missing one. Recurs on every pm-mcp-core plan that changes a specification. Not
  owned by any staged plan. — `lessons-routing-018.md`. Two more plans (PLAN-13, PLAN-18): the
  retrospective footprint reports every sibling path as declared-but-unrealised, so M6 fails by
  construction; relative sibling paths break under `use_worktree`; a sibling deliverable has no
  module name in the architecture. — `lessons-routing-028.md` (168, 175, 176, 181).
  Recurred 2026-10-13..15 on pm-mcp-core (-203, -213, -240, -265, -285; `lessons-routing-029`);
  live at `d17ac5bef` (no cross-repo field in the deliverable template, no per-path cross-repo
  footprint bucket; PLAN-LB-27 retired). Still unowned by the earlier "structural" ruling.
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
  Owned by PLAN-LB-44 (staged; the label "not owned" was stale, corrected 2026-10-15).
  Recurred on API-Sheriff #466 (`lessons-routing-043`, which names the landed PLAN-LB-24); accept-set
  unchanged at `d17ac5bef` (`verification-feedback.md` L30, L63-72).
  — `lessons-routing-019.md`, `lb-25-phase-and-merge-gates-001`.
  Recurrences: PLAN-13 (`ci-verify-policy` refused `unknown_producer`, re-dispatched as
  `finalize-feedback`); lesson `2026-10-11-07-001` (plan-06) — a SonarCloud gate failure inside
  the `build / sonar-build` Maven job filed 5 `ci_policy_failure` findings instead of deferring
  to sonar-roundtrip. — `lessons-routing-028.md` (153, 189). Recurred on PLAN-LB-42 (2026-10-14
  18:31): a CI-wait lapse was dispatched as `ci-verify-timeout` and refused `unknown producer`; all
  four `ci_timeout` findings were titled "verify failed" while verify was still running
  (`plan-lb-42-outline-qgate-integrity-001`).
- **The guard has no rule for shell file operations or ad-hoc scripts** (2026-10-15, PLAN-LB-42
  landing). Under OpenCode with the deny rules active, R1 (compound shell) and R4 (raw pytest)
  refused all 8 attempts. `ls` (2), `python3 -m py_compile` (3) and a `.plan/temp/*.py` ad-hoc
  script passed. CLAUDE.md forbids shell file operations, but no R-rule enforces the ban.
  HYPOTHESIS: the same gap exists under Claude Code's PreToolUse hook. Owned by PLAN-LB-56
  (2026-10-15). Correction: `ls`, `grep`, `head` and `python3` passed the global deny because of
  the 8 persisted OpenCode "always allow" approvals of 2026-10-08 (still owed by the operator);
  read-side probes are governed by the permission map, not the guard (`guard.js:28-32`).
  PLAN-LB-56 adds R5 for interpreter calls and reports stale approvals. **Shipped partly (#1781):** R5 refuses `-c` / `-m` / script paths, but has
  no plan-context gate on OpenCode, misses wrapper prefixes, and blocks documented workflows;
  `git grep` and `ls` are still uncovered. Remainder owned by PLAN-LB-62.
  PLAN-LB-40 (second guarded run): 92 `python3 -c`, 18 `git grep` (not in PLAN-LB-56's scope),
  17 ad-hoc script runs, three harness-written-after-R4-refusal evasions.
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
  Twelfth: PLAN-LB-26 (finding 037a63 pending across the 3-outline and 4-plan exits, waved
  through in phase 5). **Partly fixed by PLAN-LB-42 (#1773):** an empty store now reports "not
  run" instead of failing. Six more recurrences (pm-mcp-core -212..-274, `lessons-routing-032`) all
  predate #1773. Residue at `d17ac5bef`: the only component-analysis implementor is
  `pm-plugin-development:ext-outline-workflow`, so a Java or generic deep-lane plan never establishes
  coverage — it is reported "not run", no longer a false failure. Residue owned by PLAN-LB-54 D2: the outline skill is missing from the
  return, and the hash cache is switched off for an empty store.
- **The 4-plan Q-Gate skips its validators on the 3-outline hash and reports a pass over zero
  runs**; no verb computes the deliverable hashes, so passes improvise. Graded high by the
  operator. Not owned by any staged plan. — `lessons-routing-023.md`. Recurred on PLAN-18: both
  Q-Gate runs skipped `deliverable-hashes.toon` (16 hashes over 2 runs); the 4-plan leaf had no
  shell. Asks for a `manage-solution-outline deliverable-hashes` verb.
  — `lessons-routing-028.md` (185). **Partly fixed by PLAN-LB-42 (#1773):**
  - the skip is phase-keyed in prose;
  - a cached skip reads "not run";
  - the verb exists but persists nothing, and no test executes the skip rule.

  Residue owned by PLAN-LB-54 D1. Recurred on pm-mcp-core (-225, -283; `lessons-routing-033`),
  both before #1773; "no hash verb" is stale at `d17ac5bef`, the hand-written artifact is not.
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
- **From PLAN-LB-26's landing** (`landings/PLAN-LB-26.md`, 2026-10-14):
  - **Regressions N1–N4 shipped in #1769** — owned by PLAN-LB-47 (running).
  - **The review barrier counts a current-head quota refusal as participation** — owned by
    PLAN-LB-55 D3 (re-checked live at `8442a5e33`: `classify_bot` checks participation first).
  - Dropped 2026-10-15 as medium/low (`settled.md` § "Dropped 2026-10-15"): compile auto-close
    residue, metrics re-entry accounting, landing-fact ordering, the plan-session ledger write, the
    `build-server wait` log repetition, tier-1 `--request-text`.

- **From PLAN-LB-31's landing** (`landings/PLAN-LB-31.md`, 2026-10-14):
  - **Enrolment (D6, D7) and a durable measurement instrument** — owned by PLAN-LB-57 (moved out of
    PLAN-LB-48 on 2026-10-15). The efficacy-doc and registry corrections were dropped as medium.
    The CodeRabbit Learning stays by operator decision.
  - **The functional review never checks "Done when" outcome counts** — owned by PLAN-LB-52 (D1
    snapshot, D2 Done-when as a triage source).
  - Dropped 2026-10-15 as medium/low: no route from task content into the PR body, drift recovery
    manufacturing its own loop cap, the OpenCode-blind direct-`gh` audit, the in-house review job
    skipping PRs (cause unverified), `ci pr reply --repo` as a standalone item (it rides PLAN-LB-57
    D1).

- **From the lessons ingest of 2026-10-15** (`lessons-routing-029`..`-043`; pm-mcp-core
  `-203`..`-286`, API-Sheriff #466). Re-checked read-only at `d17ac5bef`; the operator's gradings at
  that ingest stand over the re-check's.
  - **High — staged 2026-10-15 by operator instruction:** PLAN-LB-58 verification-truth (Sonar
    staleness D1, link check D2, Maven gate population D3) and PLAN-LB-59 skill-and-adr-resolution
    (module-aware skills D1, ADR scan D2); both queue after the OpenCode plans.
    - **Sonar confirms a stale analysis** (`-037`, pm-mcp-core `-253`): `count_status` is decided by
      CE readiness alone (`workflow-integration-sonar/scripts/sonar.py` L26-33); no script compares
      the analysis revision with the PR head, so a clean stale analysis reads as a confirmed 0.
      Fail-open. → PLAN-LB-58 D1.
    - **Task skill resolution attaches framework skills the module forbids** (`-039`, operator-graded
      high): `manage_personas.py` `_resolve_profile_domain_skills` merges `defaults` AND `optionals`
      (L150) with no module context, so every Java task gets `java-quarkus`, `java-cdi`,
      `junit-weld-testing`; the module-level demotion in `pm-dev-java/.../extension.py` L178-185 is
      bypassed. → PLAN-LB-59 D1.
    - **The Markdown link check passes on zero links** (`-037`, operator graded pm-mcp-core `-247`
      high): `pm-documents` `_cmd_verify_links.py` file mode accepts a `.md` and parses it with
      AsciiDoc regexes (L70-106, L185-186) — `total_links: 0, status: success`; directory mode
      already refuses. The verification-scope half of `-247` was caught by the Q-Gate as designed.
      → PLAN-LB-58 D2.
    - **Pre-push gate has no per-module population on Maven** (`-031`, operator graded `-267` high):
      `derive_gate_bundles.py` is marketplace-shaped (L127-139) and only `build-pyproject` exposes
      `resolve-test-scope`, so module-tests runs DEGRADED on every Maven plan. Disclosed, not silent:
      rule 4 reports the unresolved paths and the whole-tree arms run. → PLAN-LB-58 D3.
    - **Per-package ADR numbers collide** (`-036`, operator graded `-252` high): `manage-adr.py`
      `ADR_DIR = Path('doc/adr')` (L29) with non-recursive globs (L129, L139, L163); `doc/adr/{package}/`
      is invisible to numbering and the scan. → PLAN-LB-59 D2.
  - **Graded high by the ingest, medium on re-check** (no false pass, caught by an existing gate, or
    one plan shape):
    - Sourcery's "used its review budget" notice is not a registered refusal (`-030`; `sourcery.md`
      L46 registers "used your own review budget of", case-sensitive substring at `_github_pr.py`
      L308). Data-only fix; Sourcery is optional.
    - Staged premises are not re-checked against sibling landings when no file overlaps (`-035`;
      `finalize-step-sync-baseline.md` L107-128).
    - Leaf phase skills self-transition before the orchestrator's Q-Gate (`-038`;
      `phase-3-outline/SKILL.md` L694-700 vs `planning-outline.md` L217, L264-267); the gate still
      runs. Nearest PLAN-LB-55 D2.
    - Outline assessments miss files and outlive a refuted design (`-040`); § 2.2 catches each, at
      the cost of rounds.
    - No declared task deferral for diagnose-then-fix plans (`-041`).
  - **Fixed or low:** triage fix tasks under `deliverable: 0` (`-034`) fixed by #1769
    (`_tasks_core.py` L89-94, L892), error-text residue in PLAN-LB-47 D4; `worktree-remove` from a
    stale cwd (`-042`) — the in-worktree case refuses `cwd_inside_removal_target`, the observed
    failure was a redundant second call; low.

- **PLAN-LB-47 D5 is unwired (medium, not staged):** the "squash message composed explicitly" rule
  (`branch-cleanup.md:1615-1635`) has no command — `ci pr safe-merge` / `ci repo` take no message —
  and `ensure_project_trailer` (`git-workflow.py:283-299`) is called only from a test. Every
  merge-queue squash still takes the PR page body (footer, duplicate `## Intent`, CodeRabbit block,
  extra `Co-authored-by`). — `landings/PLAN-LB-47.md`.
- **Build-finding dedup can fold distinct failures** (PLAN-LB-61 D4, `c1f68bd68`, re-check before
  staging). The identity `(type, title, file)`, with the title carrying `message[:80]`
  (`_build_shared.py:343-358`), folds two distinct failures in the same file, line and category,
  even within one build. The second is `deduplicated` and counted as stored. If it lands on a
  record owned by a pending fix task, the short-circuit guard reads all-owned and the new failure is
  not triaged. A recurrence also keeps the first detection's `detail`. Frequency unverified.
  Medium-high; not staged. — `landings/PLAN-LB-61.md`.
- **The shared outline metadata parser was widened unsafely** (PLAN-LB-54, `6953df489`,
  `_plan_parsing.py:325`). The pattern `-\s*\*{0,2}(\w+)\*{0,2}:\*{0,2}\s*(.+)` leaks bold
  markers into values (`- **domain: java**` → `java**`), produces case-kept keys from bold labels,
  and no longer reads a `domain:` line after a blank line or indented. This affects every
  `extract_deliverables` caller (outline validator, qgate mechanical, review attribution,
  `foreign_pr_gate`); a dropped domain is silent when another survives. No `test_plan_parsing.py`
  case. Medium; not staged. — `landings/PLAN-LB-54.md`.
- **The clobber report misleads** (PLAN-LB-64, `24475924b`). Every project set up before the fix
  had the bridge stub written into `plan-marshall-target-rules.md` by setup itself, so it is now
  reported "clobbered" and told to "restore" rules it never had. The restore command
  `./install.sh --emit-rules` (`configure_harness.py:65`) does not exist under that name in a
  consumer project (the retained installer is `plan-marshall-install.sh`, emit lands in the cwd,
  and without `-U` it reinstalls). A stub bridge is healed silently, never reported, and
  `configure_harness` returns `status: success` when `setup_failed` is true. Medium; not staged.
  — `landings/PLAN-LB-64.md`.
- **A dead enforcement call** (`configure_harness.py:197`): `opencode_enforcement_apply` exists in
  no runtime and is skipped by `hasattr`; `doc/developer/opencode.adoc:272` says it runs. OpenCode
  enforcement (`guard.js`, the two-tier map) is installed only by wizard Step 14b, an LLM-driven
  step. Either implement the method or drop the call and the doc claim. Medium; not staged.
  — `landings/PLAN-LB-64.md`.
- **The executor import recovery is inert** (PLAN-LB-63, `b90e8a25f`). `upgrade.py`'s probe and
  `needs_recovery` only run when `upgrade plan` runs, and it runs only through the executor
  (`upgrade-flow.md:87-89`). A broken executor never reaches it, and a working one passes the
  probe. Low items alongside:
  - no re-probe after regeneration;
  - `dead_sweep: resolved` on an empty step map;
  - one unreadable doc disables the whole sweep, unnamed;
  - `dead_removed_steps` is never read;
  - the sync-defaults output contract is stale.
  **High** (operator elevated it); staged as **PLAN-LB-43 D3**, together with the re-probe and the
  overwritten warning. The other low items are not staged. — `landings/PLAN-LB-63.md`.
- **The steward is refused on OpenCode** (PLAN-LB-65, `d3e9c2544`). R5 runs in every session,
  and the wizard's resolved deployed script paths never match the repository-relative allow-list.
  There is no consumer executor recovery, and consumers lose ordinary `python3`. **High**; staged
  as PLAN-LB-68 D1. Carried high gaps: R6 misses `git -C {WORKTREE} commit`; R5 side doors
  (here-string, `exec`/`stdbuf`/`setsid`, `bash -c` and `uv run` on Claude, a suffix-matched
  executor permit). Staged as PLAN-LB-68 D2 and D3. — `landings/PLAN-LB-65.md`.
- **The runbook-lane build commands are valid only for pyproject** (PLAN-LB-66, `f54acb7a5`).
  `runbook_lane.py:192-195` passes the canonical names through as `--command-args`, which is
  invalid for Maven, npm and Gradle. **The Claude guard false positive:** any `PreToolUse` hook
  reads as `guard: present`. Low items alongside:
  - the stamp doc and docstring disagree;
  - double listing in `owed_landing`;
  - cwd-relative `resume-summary`;
  - an unknown bot gives an empty trigger;
  - CodeRabbit's unhandled worktree-epic-scoping finding (`orchestrator.py:5726`).

  Medium; not staged. — `landings/PLAN-LB-66.md`.
- **The criteria gate refuses ordinary finalizes** (PLAN-LB-52, `6286484d8`). With a snapshot and
  no verdict (functional review dropped for surgical scope, commit-push disabled, or review off),
  `open_done_when_criteria` refuses `6-finalize` completion and archive. A wrapped spec Done-when
  is captured as its first line, giving a false `spec_criterion_missing`. Also: "prefix" is read
  as "pre-fix"; authorized changes, superseded deliverables and paraphrased verdict rows are
  ignored; the seal is in-file. **High**; staged as PLAN-LB-70. — `landings/PLAN-LB-52.md`.
- **The main executor is polluted** (PLAN-LB-52 run). `.plan/execute-script.py` was generated for
  the OpenCode target, with 163 foreign `default-bundle:*` notations. Operator action: regenerate
  it for Claude.
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

- **Superseded 2026-10-14 — see § Non-Claude-Code Failures "OpenCode 2: no deny rule applies".**
  The new keys are OpenCode 2's own schema; the live defect is rule order and the guard's tool
  name. Owned by PLAN-LB-48. Original entry kept below as the record.
  **The root `opencode.json` is in a shape nothing in this repository reads.** PLAN-LB-29's
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
  - **Eighth landing: PLAN-LB-26 (OpenCode)** — phase-5 re-dispatches skipped `effort
    resolve-target` (1 resolve against 29 dispatches), so no `[DISPATCH]` rows; the
    retrospective's dispatch audit reported "0 dispatched" against 77 real sub-agent sessions
    it cannot see. — source: `landings/PLAN-LB-26.md`.
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

## Non-Claude-Code Failures

Failures that occur only, or only measurably, when a plan runs under a harness other than
Claude Code (OpenCode, Antigravity). The Antigravity incidents of 2026-10-12 stay under Open
Defects ("Antigravity: critical …"), owned by PLAN-LB-39.

OpenCode on this machine is **2.x** (2.0.25 from 2026-10-08, 2.0.28 from 2026-10-13). Several
entries below are OpenCode 1 assumptions in plan-marshall that OpenCode 2 broke.

- **Retired 2026-10-15 — "OpenCode 2: no deny rule applies and the guard plugin blocks nothing".**
  Hot-fixed in PR #1772 (`9011a19bf`); the last plan running on the unfixed files, PLAN-LB-39,
  landed (#1768). Remaining: the persisted "always allow" approvals in `opencode.db` (operator);
  the producers that would re-introduce the OpenCode 1 shape are PLAN-LB-48. Whether the deny
  rules now refuse in practice is graded at the PLAN-LB-40 / PLAN-LB-42 landings (Watches).

- **OpenCode harness is not detected under OpenCode 2** (2026-10-15, PLAN-LB-39 landing):
  `script-shared/scripts/target_context.py:167` checks `OPENCODE` / `OPENCODE_PID`; with neither
  resolvable the worktree falls back to `claude`, so the new harness stamp would record a wrong
  `claude` with `transcripts=full` rather than `unknown`. PLAN-LB-39's own landing reads
  `harness=unknown` although its decision log names "target opencode". Owned by PLAN-LB-48 D4.

- **OpenCode: no token measurement exists at all, so every OpenCode landing reports
  `total_tokens=0`.** Verified at `501aeb313`: `platform-runtime/scripts/opencode_runtime.py`
  implements every token path as a deliberate no-op — `session_capture` (`:399-411`, "OpenCode
  does not expose a platform-provided session id to the shell; tracked upstream at issue
  #9292"), `metrics_capture` (`:1109`, no-op "on EVERY input", so even an explicit
  `--total-tokens` is not stored), `metrics_normalized_tokens` (`:1153`, `transcript_not_found`).
  The design premise — "OpenCode exposes no session transcript" — is wrong: OpenCode persists
  every session, with per-session token and cost totals, in `~/.local/share/opencode/opencode.db`
  (`session_v2`). PLAN-LB-26's analysis read it read-only: main session 42.58M input / 165K
  output / 310M cache-read ($4.93), resumed session 2.14M / 25.6K ($0.31), 77 sub-agent sessions.
  The missing piece is only the session id in the shell; the plan's worktree path and its time
  window (or `OPENCODE_PID`, which `target_context` already reads) are candidate keys for finding
  the session in the database — not verified. Two separate defects meet here: no source is read
  (this entry), and an unmeasured total is written as `0` rather than `unknown` (the zero-token
  Open Defect, PLAN-LB-39 D5). Seen on PLAN-LB-26 and pm-mcp-core PLAN-44. **Resolved premise
  (2026-10-14):** OpenCode 2.0.28 sets `OPENCODE_SESSION_ID` in every shell subprocess (and no
  `OPENCODE_PID`); the DB links sub-agents through `session_v2.parent_id`. PLAN-LB-26 corrected:
  main tree 75 sessions, 52.53M input, $7.16; resumed tree 4 sessions, 2.50M input, $0.37 (74 + 3
  sub-agents, not 77 under one session). Owned by PLAN-LB-49, which also makes the dispatch audit
  count OpenCode sub-agent sessions. Recurred on PLAN-LB-31: `total_tokens=0` against 28.7M input /
  $4.09 over 55 sessions; the root passed `record-dispatch-boundary --total-tokens 0` literally.

## Watches

- **DeepSeek Flash runs, third grade.** PLAN-LB-71 (`deepseek-v4.1-flash`/high, 3 sessions, $0.54,
  2h44m): C−. Execution hygiene improved (no history rewrite, no undisclosed shell file operation in
  the run, no operator question, every commit trailered); evidence integrity did not (0 of 15
  test-first, labelled fail-first). Retire with the second grade when three consecutive landings
  grade B or better.
- **DeepSeek Flash runs, second grade.** PLAN-LB-67 (`deepseek-v4.1-flash`/high, 2 sessions, $1.18):
  grade C, the best execution of the OpenCode runbook-lane runs since PLAN-LB-61 — a clean main
  checkout, a genuine operator question and all commits trailered — but about nine contradicted
  report claims, D5 and D6 tested after the implementation, and a partly executed operator
  selection. Retire when three consecutive landings grade B or better.
- **The merge was enqueued a few minutes after CodeRabbit's announced quota reset without a further
  re-trigger (PLAN-LB-67).** Allowed by the standing authorization as written; watch whether runs
  routinely skip a review that was minutes away.

- **Model switch on OpenCode: Muse → DeepSeek Flash1** (operator, 2026-10-15: "Starting with the
  next new plan we will change to DeepSeek Flash1 … analyze whether this has an impact on the
  plan-delivery quality"). Every OpenCode run so far — root and every sub-agent — ran
  `muse-spark-1.3-contributor` (`opencode.db` `session_v2.model`). No agent pins a model in the
  OpenCode config, so the root model is the whole run's model. PLAN-LB-40, -47, -50 and -56 finish
  on Muse and join the baseline as each lands (eight Muse plans in all); the next emitted plan is
  the first DeepSeek run.
  - **PLAN-LB-60 graded D+** (2026-10-16, `landings/PLAN-LB-60.md`) — **first DeepSeek grade**
    (`deepseek-v4.1-flash`/high, 45/45 sessions). 1 met / 4 partial vs claimed 5/5 — best spec
    fidelity of any OpenCode run, and the first with no fabricated evidence (27/27 cited tests
    exist). Mechanics clearly better than Muse: 6 argparse rejections (Muse 21–24), 2 `python3 -c`
    (LB-40: 92), root 25% of cost (Muse 50–69%), trailers 9/9, no root guard evasion, roster passed
    correctly. Integrity failures unchanged from Muse: Done-whens dropped from the outline, no
    pre-fix runs, the participation barrier skipped at the merged head (cuioss-review-bot never
    reviewed `e4dc79f8e`), a self-authorised handshake override, voluntary stops. One run — no
    conclusion yet (rule: compare after three).
  - **Correction (operator, 2026-10-16): no Gemini runs.** Every plan not run with Muse runs
    DeepSeek. Recorded per run from `opencode.db`:
    - PLAN-LB-60 — `deepseek-v4.1-flash`, provider `opencode-go`, variant `high` (plan-marshall
      lane).
    - PLAN-LB-61 — `deepseek-v4.1-flash-free`, provider `opencode` (free tier), variant `max`, root
      `ses_ebc18e9baffeE9SllcYgkzZubr`, started 2026-10-16 08:49 — the first **runbook-lane** run.

    Two variables change at once on PLAN-LB-61 (free tier/variant and lane), so its grade is
    compared with PLAN-LB-60 for the model and with later runbook runs for the lane; it is not
    attributed to either alone.
  - **First DeepSeek run: PLAN-LB-60** (started 2026-10-15 16:34, root
    `ses_ebf95b304ffeduimJZ6Cr5frL1`). `opencode.db` records the model as
    `{"id":"deepseek-v4.1-flash","providerID":"opencode-go","variant":"high"}` — the same provider
    as Muse, with an explicit `high` variant where Muse ran `default`. Check at its landing that the
    sub-agents carry the same model and variant.
  - **Muse baseline** (adversarial landings, spec deliverables met / partial / unmet vs claimed):

    | Plan | Spec met/partial/unmet | Claimed | Regressions | Sessions | Cost | Grade |
    |------|------------------------|---------|-------------|----------|------|-------|
    | PLAN-LB-26 | 6 / 4 / 1 of 11 | 11/11 | 3 | 79 | $7.54 | C |
    | PLAN-LB-31 | 1 / 4 / 2 of 7 | 5/5 | — | 55 | $4.09 | D |
    | PLAN-LB-39 | 0 / 4 / 3 of 7 | 7/7 | 5 | 99 | $12.01 | C− |
    | PLAN-LB-42 | 0 / 4 / 0 of 4 | 2/2 | 5 | 69 | $5.79 | C |
    | PLAN-LB-40 | 2 / 2 / 1 of 5 | 5/5 | 4 | 77 | $5.66 | D |
    | PLAN-LB-47 | 0 / 5 / 0 of 5 | 5/5 | 3 | 30 | $2.32 | F |
    | PLAN-LB-56 | 0 / 2 / 1 of 3 | 3/3 | 1 (R5 breadth) | 65 | $4.85 | D |
    | PLAN-LB-50 | 1 / 2 / 2 of 5 | 5/5 | 2 (1 critical) | 68 | $5.21 | F |

    Muse pooled (8 plans): 10 of 47 spec deliverables met (21%).

    **DeepSeek** (`deepseek-v4.1-flash`):

    | Plan | Spec met/partial/unmet | Claimed | Regressions | Sessions | Cost | Grade |
    |------|------------------------|---------|-------------|----------|------|-------|
    | PLAN-LB-60 | 1 / 4 / 0 of 5 | 5/5 | 1 high | 45 | $3.75 | D+ |

    **Runbook lane** (DeepSeek; first run mixed — implementation on `deepseek-v4.1-flash-free`/max,
    review and merge on paid `deepseek-v4.1-flash`/high after a free-tier 429):

    | Plan | Spec met/partial/unmet | Claimed | Regressions | Sessions | Cost | Grade |
    |------|------------------------|---------|-------------|----------|------|-------|
    | PLAN-LB-61 | 3 / 1 / 0 of 4 | 4/4 | 0 confirmed | 5 | $0.40 | C+ |
    | PLAN-LB-62 | 0 / 2 / 1 of 3 | 3/3 | 2 high (R5 root gap, allow-list bypass) | 2 | $0.58 | F |
    | PLAN-LB-54 | 2 / 0 / 0 of 2 | 2/2 | 1 medium (shared metadata regex) | 5 | $0.51 | C |
    | PLAN-LB-64 | 1 / 1 / 0 of 2 | 2/2 | 1 medium (clobber report) | 5 | $0.36 | C− |
    | PLAN-LB-63 | 4 / 0 / 0 of 4 Done-whens (D2 intent partial) | 2/2 | 1 medium (inert recovery) | 5 | $0.44 | D+ |
    | PLAN-LB-65 | 1 / 2 / 0 of 3 | 3/3 | 1 high (steward refused on OpenCode) | 4 | $1.87 | F |
    | PLAN-LB-66 | 1 / 2 / 0 of 3 | 3/3 | 1 high (ten runbook rules weakened) | 10 | $1.85 | F |
    | PLAN-LB-52 | 5 / 3 / 0 of 8 Done-whens | 2/2 | 2 high (finalize gate refuses, spec parse) | 4 | $1.77 | F |

    PLAN-LB-61 is the first run to keep every Done-when verbatim with genuine fail-first evidence.
    It still bent the CodeRabbit policy (the merged head has no CodeRabbit review; Q4's premise was
    partly false), its sub-agents broke rules undisclosed, and its report had about 10 omissions.

    Pooled: see the Muse total below the table; every run claimed 100%. The over-claim is the
    constant; mechanics (gh, rebase, trailers) improved run over run as enforcement arrived.
  - **What is model-attributable and what is not.** Measure each DeepSeek landing on the same
    dimensions, split into:
    - *model-sensitive* — spec deliverables kept separate in the outline; met rate and claim gap;
      verdict self-editing; rule-violation ATTEMPTS (guard refusals count as attempts — the guard
      hides outcomes, not intent); argparse rejections (invented verbs/flags); root share of
      cost and inline commits; `escalate_ask` answered by the root; PR-body truthfulness;
      regressions shipped;
    - *mechanism-sensitive* — gh calls executed, ungated pushes, phase bypasses, token reporting:
      these change as PLAN-LB-56, -52, -55, -53, -49 land, whatever the model.
  - **Confounders to state at every grading:** plan difficulty and size (normalise per spec
    deliverable); enforcement landed in between (name which of LB-56/52/55/53/48 were on `main` at
    the plan's branch point); the cached plugin version the run used. The cleanest comparison is
    the overlap window — Muse plans LB-40/47/50/56 and the first DeepSeek plans run against the
    same `main` and the same guard.
  - **Switch-specific risks to check at the first DeepSeek landing** (HYPOTHESES, unverified):
    tool-call compatibility with OpenCode 2's `skill {id}` and `subagent` tools (failed or
    malformed tool calls in `opencode.db`); context-window pressure on the large workflow docs
    (more compactions or mid-phase restarts); the `execution-context-level-N` variants carry no
    model or effort on OpenCode, so the level ladder is flat under either model.
  - **Grading rule:** record the model per landing from `opencode.db` (`session_v2.model`, root
    and children — a mixed tree is reported, not averaged). Draw no conclusion from one plan:
    compare after three DeepSeek landings, and report the claim gap and the attempt rates first.
    — trigger: each OpenCode landing; retire when three DeepSeek plans are graded and the result is
    recorded as a decision.

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
  - **PLAN-LB-26 graded C** (2026-10-14, `landings/PLAN-LB-26.md`). Mechanics strong: 77 real
    sub-agent sessions, ~92% executor discipline, no `gh`, operator questions through the
    OpenCode `question` tool. Failed the end-of-run integrity: claimed 11/11 against 6 met,
    4 partial, 1 unmet; merged `74e6bfda` which no in-house gate had seen (gates stamped
    `3db65fc05`) after a provider crash and a resume that skipped the head-dependent re-fires;
    improvised the merge-override question and omitted CodeRabbit's quota refusal; reported
    `total_tokens=0` against ~45M real input tokens; wrote the orchestrator ledger from the plan
    session. Three regressions shipped (PLAN-LB-47). Remaining: PLAN-LB-31, PLAN-LB-39.
  - **PLAN-LB-31 graded D** (2026-10-14, `landings/PLAN-LB-31.md`). 7 spec deliverables: 1 met,
    4 partial, 2 unmet (enrolment and observation) counted done on a gate the ledger refutes. 120
    direct `gh` calls including 8 `gh pr comment … /review`; the operator's counter-question "why
    not fixing the script?" went unanswered and was logged as the operator resolution "no new
    corpus runs"; the landing, the functional review and a CodeRabbit-triage reply all claim PR
    tables that do not exist; tokens 0 against $4.09 real. Good: four genuine operator questions,
    the drift-cap escalation, the merge path, the write-boundary. Remaining: PLAN-LB-39.
  - **PLAN-LB-39 graded C−** (2026-10-15, `landings/PLAN-LB-39.md`). 0 met / 4 partial / 3 unmet
    against its spec, counted 7/7; five regressions (PLAN-LB-50). Improved: **0 direct `gh`**
    (LB-31: 120), 97 sub-agents with the finalize roster honoured, required-bot gate handled, final
    gate head = merged head, `total_tokens=unknown` instead of `0`. Failed: the root rewrote the
    functional-review verdict to "met" three times with `python3 -c`; rebased and force-pushed an
    ungated head after telling the operator no rebase or force-push would happen; 37 raw test
    commands, 11 `/tmp` scripts; `harness=unknown`; $12.01 real cost, roots 73%. Trend across the
    three: C, D, C− — mechanics improve, end-of-run integrity does not.
  - **PLAN-LB-42 graded C** (2026-10-15, `landings/PLAN-LB-42.md`), the first run with the guard.
    - Guard: refused all 8 covered attempts (4 raw pytest, 2 of them via a venv's Python after a
      refusal; 4 compound shell). It does not cover `ls` or `py_compile`.
    - Good: 0 `gh`, no rebase or force-push, 100% trailers, a genuine barrier question, $5.79.
    - Failed: 4 spec deliverables cut to 2 and graded 2/2 against 0 met / 4 partial; an
      unevidenced "fails pre-fix" criterion graded met; a leaf's `escalate_ask` answered by the
      root; 8 of 16 commits written inline by the root; about 4.5 h of finalize booked to execute.

    Remaining: PLAN-LB-40.
  - **Extended 2026-10-15 to PLAN-LB-56** (operator instruction, "do the grading"), emitted for
    OpenCode. Same adversarial analysis and per-plan grade. Additionally grade whether the run
    kept to its own subject:
    - Did it attempt the routes it is closing (`python3 -c`, ad-hoc or `/tmp` scripts,
      inline source commits in finalize)?
    - Did each spec deliverable stay a separate outline deliverable with its Done-when intact?
    - Does each Done-when test fail at `8442a5e33`, evidenced by a run against that tree?

    Retire the Watch once PLAN-LB-40 and PLAN-LB-56 are graded.
  - **PLAN-LB-40 graded D** (2026-10-15, `landings/PLAN-LB-40.md`). 2 met / 2 partial / 1 unmet
    vs claimed 5/5; four regressions (PLAN-LB-60). Guard refused 15/15 covered attempts, but the run
    routed around it: 92 `python3 -c` (one wrote the functional verdict via `/tmp`), 18 `git grep`,
    17 ad-hoc script runs, three harness-after-refusal evasions. Faked the verify-first gate; the
    verdict cited test names that do not exist; the CRITICAL merge override was obtained on a false
    "bot untriggerable" premise with a "Make cuioss optional (Recommended)" option. Good: 0 `gh`, no
    force-push, every push gated, 11/11 trailers, five deliverables kept. Remaining: PLAN-LB-47,
    -50, -56.
  - **PLAN-LB-47 graded F** (2026-10-16, `landings/PLAN-LB-47.md`). 0 met / 5 partial vs claimed
    5/5; three regressions (PLAN-LB-61). Merged #1778 with no CodeRabbit review on a
    `barrier-ask-override` the agent minted from the operator's "try now", with a false reason ("CI
    green" while red); never re-triggered CodeRabbit (raw `sleep` waits, empty-roster leaf as on
    PLAN-LB-40); re-ran a red check unasked; hid the bypass in the step record. Kept on `main` by
    operator decision. Remaining: PLAN-LB-50, -56.
  - **PLAN-LB-56 graded D** (2026-10-16, `landings/PLAN-LB-56.md`). 0 met / 2 partial / 1 unmet
    vs claimed 3/3. D2's finalize commit gate is dead code (no caller) yet graded met. R5 has no
    plan-context gate on OpenCode and refuses the repository's own steward, executor-recovery and
    harness-sync invocations (PLAN-LB-62). Good: every refusal respected, both required bots
    reviewed the merged head, merged head gated. Failed: root 50% of cost and 11 of 14 commits,
    12 of 14 without trailer, a `uv run` evasion attempt after R5, an operator selection executed
    as something else, the empty-roster leaf a third time. Remaining: PLAN-LB-50.
  - **PLAN-LB-50 graded F** (2026-10-16, `landings/PLAN-LB-50.md`). 1 met / 2 partial / 2 unmet vs
    claimed 5/5; D1 implemented backwards; the conflict resolution made the steward skip installing
    enforcement (PLAN-LB-64). Merged `779b035ab`, which no required bot reviewed and no grant
    covered, through an auto-merge armed for the earlier head `f4ca42ab`, after an unconsented
    force-push; then left the operator's "was there a CodeRabbit review?" unanswered. Five
    review verdicts written by ad-hoc `/tmp` scripts.
  - **Retired 2026-10-16: all eight Muse plans graded.** Final: PLAN-LB-26 C, -31 D, -39 C−, -42 C,
    -40 D, -47 F, -56 D, -50 F. 10 of 47 spec deliverables met (21%); every run claimed 100%.
    Mechanics improved where enforcement arrived (`gh` 120 → 0); end-of-run integrity never did —
    rewritten or dropped Done-whens, no pre-fix evidence, fabricated or mis-cited evidence, merges
    past required reviewers (PLAN-LB-47, -50), regressions in every run. The comparison continues
    under the model Watch.
  - **Corrected 2026-10-15: PLAN-LB-47 and PLAN-LB-50 are OpenCode runs too** (emitted in the OpenCode
    form, Muse, `opencode.db` roots `ses_ec19f02e1ffeJrkGjQ3D6znWUt` and
    `ses_ec19f318affeLhDQuk6jhH6ZGa`), and were missing from this Watch. All four running plans —
    PLAN-LB-40, -47, -50, -56 — get the same adversarial grading; the Watch retires when all four are
    graded. With PLAN-LB-26, -31, -39 and -42 that makes eight Muse plans in the baseline.
  - **Extended 2026-10-14 to PLAN-LB-40 and PLAN-LB-42**, emitted for OpenCode by operator
    instruction ("emit the next two plans for opencode"). They are the first OpenCode plans to run
    with the deny rules and guard in effect (branched after `9011a19bf`), so grade separately
    whether a denied command was attempted and refused (`.plan/temp/guard.log`, `opencode.db`).
    Same adversarial analysis at each landing; retire after all five are graded.

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
