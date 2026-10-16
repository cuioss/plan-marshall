# PLAN-LB-61: Hotfix for PLAN-LB-47 — triage resolves in the right store, builds hand back below the ceiling, PR bodies survive a backslash

epic: live-blockers
workstream: WS-01

> Staged plan spec — one shippable unit of work, ready for `/plan-marshall` hand-off.
> Lives at `plans/PLAN-LB-61-lb-47-hotfix.md` and is queued as one row file,
> `queue/PLAN-LB-61.json`, in the epic ledger. The orchestrator EMITS the command below; it never
> launches the plan inline. This spec is SELF-SUFFICIENT: the emitted command is a one-line pointer
> and carries no brief, so every per-plan carry is authored here and nowhere else.
> See `persona-plan-orchestrator/standards/orchestration-model.md` for the tier and
> hand-off contract.

> Staged 2026-10-16 by operator instruction ("keep the current state: create a plan for fixing")
> from the landing analysis of PLAN-LB-47 (#1778, `b9cd36be1`), `landings/PLAN-LB-47.md`. #1778 is
> kept on `main` without a CodeRabbit review; this plan fixes what it broke. To be run with a
> Gemini model (operator); graded under the model Watch.
>
> **Rules for this run** — every PLAN-LB plan so far failed on these:
> - Each deliverable below is its own outline deliverable, and each Done-when is copied verbatim as
>   its success criterion. Do not merge, narrow or rewrite them.
> - "Fails at `b9cd36be1`" is evidenced only by a run against that tree; a green run at HEAD is not
>   evidence. Every test cited as evidence must exist at the graded head.
> - A required review bot (CodeRabbit) is never skipped, demoted to optional, or bypassed. A merge
>   authorization exists only if the operator selected that option; free text is not a grant. If
>   CodeRabbit refuses on quota, wait the window, re-trigger, and repeat; ask the operator only
>   after that, stating these facts.

## Objective

PLAN-LB-47 shipped three regressions that hit every running plan's finalize or builds:

- triage records every task-fix in the Q-Gate store, so fixes for PR-comment, Sonar and build
  findings are never recorded and the findings are re-triaged;
- the build wrapper waits up to 600 s, the same as the Bash ceiling, so a long routed build
  overruns the tool call;
- the PR Intent renderer passes LLM-written text as a regex replacement and crashes on a backslash.

The duplicate-fix-task loop LB-26 meant to close also stays open, because the all-owned
short-circuit can no longer be reached.

## Deliverables

1. **A triage task-fix is recorded in the store the finding lives in.**
   - FIX Shape 1 (`plan-marshall/workflow/triage.md:212-222`) resolves a Q-Gate finding with
     `qgate resolve --phase {its phase} --task-number {N}`, and a plan-scoped finding (PR comment,
     Sonar, auto-stored build finding) with the plan-scoped `resolve --task-number {N}`. The
     record's store decides which; the triage list (`list --include-qgate`) carries it.
   - The plan-scoped `resolve` accepts `--task-number` if it does not already, so ownership is
     recorded in both stores.

   *Done when:* tests: a plan-scoped PR-comment finding triaged into a fix task is `fixed` with
   `fix_task_number` and is found by `stamp-fix-commit`; a Q-Gate finding is resolved in the Q-Gate
   store with `fix_task_number`. The first fails at `b9cd36be1`.

2. **The build wrapper hands back below the per-call ceiling.**
   - `_DAEMON_WAIT_BOUND_SECONDS` (`script-shared/scripts/build/_build_execute_factory.py:833`) is
     derived as the ceiling minus a margin that covers preflight, submit and start (or restored to
     300), never equal to the ceiling. The comment at `:828-829` describes what the code does.
   - `test_build_execute_factory.py::test_the_wait_bound_stays_foreground_safe` asserts the bound
     plus the measured setup stays below 600 s again.

   *Done when:* the foreground-safe test fails at `b9cd36be1` (where the bound is `== 600`) and
   passes after; a routed build that outlives the bound returns `status: running` inside a
   600 000 ms call.

3. **The Intent renderer cannot be broken by the text it renders.**
   - `pr_intent_section.py:414` passes the rendered section through a function replacement (or
     escapes it), so backslashes, `\1` and `\g<0>` in the text are inserted literally.
   - The filled section keeps a blank line before the next heading. `create-pr.md:200` ("appended
     to, not replaced") describes the fill-in-place behaviour.

   *Done when:* tests: an Intent text containing `\d`, `\1` and `\n` renders verbatim; the next
   section heading is preceded by a blank line. The first fails at `b9cd36be1` with
   `PatternError: bad escape`.

4. **The all-owned short-circuit is reachable again.**
   - The short-circuit guard (`plan-marshall/workflow/execution.md` § "Short-circuit guard") treats
     a plan-scoped build finding as owned when an equivalent pending finding (same type, file and
     message) is already owned by a pending fix task, instead of always counting it as new — or the
     build path dedups its auto-stored copies (`_build_shared.py:381`). Choose at outline and record
     the choice.

   *Done when:* a test computes the guard verdict for a repeated failing build whose finding is
   owned by a pending fix task and gets the all-owned verdict (no new fix task); a genuinely new
   failure still yields `new-findings`. The first fails at `b9cd36be1`.

Split guard: four deliverables, all regressions or gaps of one commit.

## Claim Labels

- OBSERVED: `triage.md:212-222` at `b9cd36be1` always runs `manage-findings qgate resolve … --phase {qgate_phase} --task-number {N}`; triage lists with `--include-qgate` (`:42-47`); `resolve_qgate_finding` returns "Q-Gate finding not found" for a plan-scoped hash (`_findings_core.py:1559-1621`); `stamp-fix-commit` reads only the plan-scoped store (`:1027-1034`) — orchestrator-read and delegated agent.
- OBSERVED: `_DAEMON_WAIT_BOUND_SECONDS = 600` at `b9cd36be1`, `= 300` at `b9cd36be1^` — orchestrator-read; a routed `module-tests plan-marshall` returned `running` only after the 600 000 ms call (delegated agent).
- OBSERVED: `re.compile(...).sub('…\\d…', …)` raises `PatternError: bad escape \d` — orchestrator-reproduced against the pattern at `pr_intent_section.py:414`.
- OBSERVED: every failing build with a plan id auto-stores plan-scoped copies without dedup (`_build_shared.py:381`); the guard counts them as new (delegated agent).
- HYPOTHESIS: the plan-scoped `resolve` verb already takes `--task-number` — confirm with `--help` (verify-at-outline).
- Out of scope (recorded as an Open Defect, not staged): PLAN-LB-47 D5's unwired squash-message rule and trailer function; the unreachable `--verification-owed` ordering (pre-LB-26 behaviour, not worse).

## Expected Surface

- OBSERVED: `marketplace/bundles/plan-marshall/skills/plan-marshall/workflow/triage.md` (D1)
- OBSERVED: `marketplace/bundles/plan-marshall/skills/manage-findings/scripts/_findings_core.py` (D1)
- HYPOTHESIS: `marketplace/bundles/plan-marshall/skills/manage-findings/SKILL.md` — `resolve --task-number` (verify-at-outline) (D1)
- OBSERVED: `test/plan-marshall/manage-findings/test_manage_findings_qgate.py` (D1, D4)
- OBSERVED: `marketplace/bundles/plan-marshall/skills/script-shared/scripts/build/_build_execute_factory.py` (D2)
- OBSERVED: `test/plan-marshall/script-shared/test_build_execute_factory.py` (D2)
- OBSERVED: `marketplace/bundles/plan-marshall/skills/phase-6-finalize/scripts/pr_intent_section.py` (D3)
- OBSERVED: `marketplace/bundles/plan-marshall/skills/phase-6-finalize/workflow/create-pr.md` (D3)
- HYPOTHESIS: `test/plan-marshall/phase-6-finalize/test_pr_intent_section.py` (verify-at-outline) (D3)
- OBSERVED: `marketplace/bundles/plan-marshall/skills/plan-marshall/workflow/execution.md` (D4)
- HYPOTHESIS: `marketplace/bundles/plan-marshall/skills/script-shared/scripts/build/_build_shared.py` — only if dedup is chosen (verify-at-outline) (D4)

## Dependencies and Sequencing

- Depends on: none. High priority: regressions 1 and 2 hit PLAN-LB-50, -56 and -60.
- Overlaps with: PLAN-LB-52 (staged) on `triage.md`; PLAN-LB-55 (staged) on the
  `phase-6-finalize/scripts/` directory. The gate will ask about running plans.

## Hand-Off Command

```text
/plan-marshall task="implement .plan/orchestrator/live-blockers/plans/PLAN-LB-61-lb-47-hotfix.md"
```

## Write-Boundary

The plan implementing this spec touches only its own repository source and tests. It creates
and edits NO file under `.plan/orchestrator/` other than its own
`inbox/{sender}-{seq}` message — the orchestrator owns every other ledger write — and reports
its outcome through its PR and its inbox message. The inbox exception's qualifiers and the
sole sanctioned write mechanism are stated in
`persona-plan-orchestrator/standards/orchestration-model.md` § Ledger Write-Boundary.
