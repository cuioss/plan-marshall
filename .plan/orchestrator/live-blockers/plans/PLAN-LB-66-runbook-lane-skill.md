# PLAN-LB-66: The runbook lane ships as a plan-marshall skill, usable from any project, and the orchestrator drives it

epic: live-blockers
workstream: WS-04

> Staged plan spec — one shippable unit of work, ready for hand-off.
> Lives at `plans/PLAN-LB-66-runbook-lane-skill.md` and is queued as one row file,
> `queue/PLAN-LB-66.json`, in the epic ledger. This spec is SELF-SUFFICIENT.
> See `persona-plan-orchestrator/standards/orchestration-model.md` for the hand-off contract.

> Staged 2026-10-17 on the operator's decision: the OpenCode runbook lane becomes the standard way
> to run a staged plan on a cheap model, in this repository and in consumer projects. Today it is a
> machine-local file (`.plan/local/opencode/RUNBOOK.md`, not git-tracked) hard-wired to this
> repository. Runs in the runbook lane.
>
> **Each Done-when below is a test you write, see fail at `c3abf8c38` (the skill and verb do not
> exist there), then see pass.**

## Objective

The runbook lane implements one orchestrator plan spec without the `/plan-marshall` lifecycle:
progress file and resume, hard rules, fail-first evidence, build gate, self-review rounds, PR and
review cycle, merge gate, cleanup, and a landing message to the epic inbox. Its contract lives
only in a local file that names this repository's epic, build system, reviewers and commit
trailer. Ship it as a bundle skill whose project-specific values come from the project's own
configuration through one deterministic script verb, so any project with plan-marshall installed
can run it. The orchestrator then emits, correlates and stamps runbook-lane plans itself instead
of relying on hand work.

## Deliverables

1. **A user-invocable bundle skill `plan-marshall:runbook-lane` carries the lane contract.**
   - **Source text:** `.plan/local/opencode/RUNBOOK.md` in the **main checkout**. Read it at the
     start (read only; it is inside the repository). Keep every section and every rule; change only
     what is repository-specific. Do not restate it from memory, and do not drop a rule because it
     looks redundant.
   - **Invocation:** the skill takes `plan={spec path}` (any `.plan/orchestrator/{slug}/plans/PLAN-*.md`).
     The first step is the D2 `resolve` verb; every repository-specific value in the text is
     replaced by a field of its result:
     - epic slug;
     - `{plan}` and the derived names;
     - build commands;
     - required and optional reviewers, with their trigger and escalated-trigger comments;
     - commit trailer;
     - inbox sender id and landing command.
   - **Generic sender id:** `rb-{plan}` (the `oc-` prefix named a harness; the lane is
     harness-neutral).
   - **Repository-neutral text:** none of these literals appears anywhere in the skill:
     `live-blockers`, `PLAN-LB`, `build-pyproject`, `pyproject_build`, `cuioss-review-bot`,
     `coderabbit`, `sourcery`, `noreply@cuioss.de`.
   - **Quota rule stays generic:** the CodeRabbit quota rule becomes a rule for any required
     reviewer that refuses on quota: wait 90 minutes, re-trigger, up to 10 times; then close the PR
     unmerged, reopen it and trigger; then ask the operator. Keep it in the skill;
     `automatic-review/standards/{bot}.md` stays the source of each bot's trigger phrases.
   - **Generated harnesses:** the OpenCode and Antigravity targets export the skill like every
     other user-invocable plan-marshall skill. On OpenCode that gives skill
     `plan-marshall-runbook-lane` and command `/plan-marshall-runbook-lane`.
   - **Registration:** the skill is registered wherever a new plan-marshall skill must be
     (`plugin.json` and any count or registry test). The component count in `CLAUDE.md` is
     updated.
   - **Harness without a guard:** where no tool-call guard is installed (Antigravity has no
     pre-tool-use hooks; an OpenCode project without `.opencode/plugin/guard.js`), the skill makes
     the landing say `guard: none on this harness (unenforced)` in the facts block and in the rule
     check. It never reports "all kept" or "no guard-log line" when nothing was enforced. How the
     run detects the guard is part of the D2 `resolve` result (`guard: present|none`).
   - **Docs:** a short section in `doc/developer/opencode.adoc` names the lane, its invocation and
     its prerequisites:
     - the steward-installed executor;
     - the OpenCode guard (wizard Step 14b);
     - an orchestrator epic holding the spec.

   *Done when:* tests, each failing at `c3abf8c38`:
   - the skill exists, is user-invocable, and passes plugin-doctor with no finding;
   - a content test asserts that none of the eight literals above occurs (case-insensitive) under
    `skills/runbook-lane/`;
   - a content test asserts that every top-level section of the source runbook (0, 0a, 1–8) has a
     matching section in the skill. Quote the source headings in the test as fixed strings; do
     not read `.plan/local` from the test;
   - generating the OpenCode target emits the skill and the `/plan-marshall-runbook-lane` command,
     and generating the Antigravity target emits the skill and its command with the tool names
     rewritten (`ask_question`, `invoke_subagent`), both asserted in the existing
     target-generation tests;
   - a content test asserts the skill's landing section contains the unenforced-guard wording.

2. **One script verb resolves every project-specific value.**
   - `runbook_lane resolve --spec PATH` (notation `plan-marshall:runbook-lane:runbook_lane`)
     returns TOON with:
     - `slug`, `plan`, `worktree`, `progress_file`, `sender_id`, and the exact `inbox write`
       command line;
     - `build`: the canonical commands the lane uses (`quality-gate`, `module-tests`, `verify`,
       and the split form), resolved through `architecture resolve` for the project's build
       system — never a hard-coded build skill;
     - `required_bots` and `optional_bots` from the project's `.plan/marshal.json`
       automatic-review step, each with `trigger_comment` and `escalated_trigger_comment` from
       its `automatic-review/standards/{bot}.md`;
     - `commit_trailer` from `run_config commit-trailer get`;
     - `harness` (from `platform_runtime runtime-info`) and `guard`: `present` when the harness
       has a tool-call guard installed for this project, `none` otherwise (always `none` on
       Antigravity).
   - **Fail closed:** a spec path outside `.plan/orchestrator/{slug}/plans/`, a missing or empty
     `required_bots`, or an unresolvable build command returns `status: error` with a specific
     code. It never falls back to a default reviewer list or a default build.

   *Done when:* tests, each failing at `c3abf8c38`:
   - a fixture project with a pyproject build, `required_bots: [a, b]` and a trailer override
     resolves all fields, including that override;
   - a fixture with a Maven build resolves Maven commands (no pyproject literal in the output);
   - an empty `required_bots` is an error;
   - a spec outside `.plan/orchestrator/` is an error;
   - an Antigravity harness resolves `guard: none`, and an OpenCode fixture without
     `.opencode/plugin/guard.js` resolves `guard: none`.

3. **The orchestrator handles runbook-lane plans end to end.**
   - **Lane per row:** a queue row carries `lane` (`plan-marshall`, the default, or `runbook`). It is
     set with `queue --add-row … --lane` and `queue --set-row --field lane`, and is shown in
     `queue-view.md`.
   - **Emit:** `next` emits by lane. A `runbook` row gets
     `/plan-marshall-runbook-lane plan=.plan/orchestrator/{slug}/plans/{spec}`; a `plan-marshall`
     row keeps today's `/plan-marshall task="implement …"`. The spec template's *Hand-Off Command*
     section shows the lane's form.
   - **Landing correlation:** a landing message is matched to its row. The sender `rb-{plan}`
     matches the row whose spec basename gives `{plan}`, and any sender equal to a row's stamped
     `plan_marshall_plan_id` matches that row. `owed_landing`, `queue_reconciliation` and
     `landing-check` count the match. Today every one of the 65 rows reads "without landing" and
     each landing reads "without queue".
   - **Stamping:** `analyze` stamps `plan_marshall_plan_id` from a matched runbook sender, so the
     orchestrator no longer types it by hand.
   - **Start detection:** `status` reports a `staged` runbook row whose worktree
     `.plan/local/worktrees/{plan}` exists as "started, not transitioned". It reports only and
     writes nothing.
   - **Analysis inputs:** `workflow/analyze.md` names the runbook-lane evidence set in place of the
     plan directory:
     - the progress file;
     - `.plan/temp/guard.log`;
     - the PR;
     - the harness session store, read only.

     It also states that `landing-facts` `model` may list several comma-separated models.

   *Done when:* tests, each failing at `c3abf8c38`:
   - a `runbook` row makes `next` emit the runbook form, and a `plan-marshall` row is unchanged;
   - an inbox holding an `rb-lb-66-runbook-lane-skill` landing, with a running PLAN-LB-66 row
     (`lane: runbook`), reconciles: the row is not in `queue_without_landing`, the landing is not
     in `landing_without_queue`, and `owed_landing` counts it as queued;
   - a landing whose sender equals a row's stamped `plan_marshall_plan_id` reconciles to that row;
   - `status` flags a `staged` runbook row whose worktree exists.

Split guard: three deliverables.

## Claim Labels

- OBSERVED: the current contract is `.plan/local/opencode/RUNBOOK.md` (about 350 lines, machine-local), and its repository-specific references are §0 (spec path), §1 and §4 (`build-pyproject` commands, `--execution-mode in_process`), §1, §6 and §8 (reviewers and trigger phrases), §1 (trailer) and §8 (`--slug live-blockers`, `epic=`) — orchestrator-read.
- OBSERVED: `automatic-review/standards/coderabbit.md:37-38` declares `trigger_comment` and `escalated_trigger_comment`; `cuioss-review-bot.md` and `sourcery.md` sit beside it — orchestrator-read.
- OBSERVED: user-invocable plan-marshall skills are exported to OpenCode as `~/.config/opencode/skills/plan-marshall-{skill}` and `commands/plan-marshall-{skill}.md` (e.g. `plan-marshall-plan-orchestrator.md`) — orchestrator-read.
- OBSERVED: the live ledger's `inbox list` reports `queue_without_landing_count: 65` and `landing_without_queue_count: 1` while a landing for a running row is queued: reconciliation compares row ids (`PLAN-LB-64`) with sender ids (`oc-lb-64-lb-50-completion`) — orchestrator-observed 2026-10-17.
- OBSERVED: `orchestrate.md` `next` emits only `/plan-marshall task="implement …"` — orchestrator-read.
- OBSERVED: `CLAUDE.md:7` states "158 registered components (154 skills, 2 agents, 2 commands)" — orchestrator-read.
- HYPOTHESIS: only `build-pyproject` accepts `--execution-mode in_process`. Other build skills may need the worktree executor for the daemon. Confirm how a Maven build runs in a worktree without a generated worktree executor, and make `resolve` return the form that works. If none works without the daemon, report it as not met for Maven rather than inventing one.
- HYPOTHESIS: a new script needs the executor mapping regenerated before `python3 .plan/execute-script.py plan-marshall:runbook-lane:runbook_lane` resolves. Confirm which tests check script registration, and run the regeneration through the executor in process (as PLAN-LB-54 did with `generate-claude`).
- OBSERVED: Antigravity runs without pre-tool-use hooks (`doc/developer/antigravity.adoc:343`), so no guard and no `guard.log` exist there; the target supports skills and commands (`marketplace/targets/antigravity/target.py:38-39`) — orchestrator-read.
- HYPOTHESIS: `.plan/marshal.json` is read through an existing manage-config verb rather than by path. Confirm, and use the verb.

## Expected Surface

- NEW: `marketplace/bundles/plan-marshall/skills/runbook-lane/SKILL.md` (D1)
- NEW: `marketplace/bundles/plan-marshall/skills/runbook-lane/scripts/runbook_lane.py` (D2)
- NEW: `test/plan-marshall/runbook-lane/test_runbook_lane.py` (D1, D2)
- OBSERVED: `marketplace/bundles/plan-marshall/.claude-plugin/plugin.json` (D1)
- OBSERVED: `CLAUDE.md` (D1, component count)
- OBSERVED: `doc/developer/opencode.adoc` (D1)
- HYPOTHESIS: the target-generation tests under `test/` that assert exported skills and commands, for OpenCode and Antigravity (D1)
- OBSERVED: `marketplace/bundles/plan-marshall/skills/plan-orchestrator/scripts/orchestrator.py` — `PLAN_ROW_FIELDS`, `queue`, `status`/`next` (D3)
- OBSERVED: `marketplace/bundles/plan-marshall/skills/plan-orchestrator/scripts/_orchestrator_inbox.py` — `reconcile_queue_vs_landings`, owed-landing (D3)
- OBSERVED: `marketplace/bundles/plan-marshall/skills/plan-orchestrator/workflow/orchestrate.md`, `workflow/analyze.md` (D3)
- OBSERVED: `marketplace/bundles/plan-marshall/skills/plan-orchestrator/templates/plan-spec.md` (D3)
- HYPOTHESIS: `marketplace/bundles/plan-marshall/skills/plan-orchestrator/standards/landing-payload-spec.md` (D3, multi-model `model`)
- HYPOTHESIS: the ledger layout module in `manage-status` that owns the row schema (D3)
- OBSERVED: `test/plan-marshall/plan-orchestrator/test_orchestrator.py`, `test_inbox_drain_contract.py`, `test_orchestrator_queue_view.py` (D3)

## Dependencies and Sequencing

- Depends on: none.
- Overlaps with: PLAN-LB-45 (running) on `orchestrator.py` (its `preflight` forwarding),
  `_orchestrator_inbox.py` (its `LANDING_REQUIRED_KEYS`) and `landing-payload-spec.md`, in
  different functions; whichever lands second merges `main`. No file is shared with PLAN-LB-52,
  PLAN-LB-63 or PLAN-LB-65.
- After it lands, the orchestrator sets `lane: runbook` on the runbook rows and retires the local
  `RUNBOOK.md`. Later amendments to the lane go through PRs.

## Write-Boundary

The plan implementing this spec touches only its own repository source and tests. It creates
and edits NO file under `.plan/orchestrator/` other than its own
`inbox/{sender}-{seq}` message — the orchestrator owns every other ledger write — and reports
its outcome through its PR and its inbox message.
