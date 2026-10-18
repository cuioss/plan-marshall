# Landing Analysis: PLAN-LB-66 — the runbook lane as a plan-marshall skill (runbook lane)

epic: live-blockers
workstream: WS-04
pr: #1808 (https://github.com/cuioss/plan-marshall/pull/1808), merged via the merge queue as `f54acb7a5` (squash)
harness: **OpenCode runbook lane**, `deepseek-v4.1-flash` / `high` throughout. Root
`ses_eb4c5386effe2ieUSq6FcQNHSm` plus nine child sessions. No compaction, no restart.

> Landing record for one shipped plan. Lives at `landings/PLAN-LB-66.md`. Written by the
> `analyze` verb after verifying claims against ground truth (actual code, artifacts,
> PR state) — a pasted claim is a lead, never a fact. See
> `persona-plan-orchestrator/standards/orchestration-model.md` for the analysis and
> reconciliation contract.

Source: inbox `oc-lb-66-runbook-lane-skill-001.md`. Checked against:

- `git show f54acb7a5`;
- the progress file `.plan/temp/oc-lb-66-runbook-lane-skill/progress.md`;
- `opencode.db`;
- `.plan/temp/guard.log`;
- PR #1808's reviews, comments and checks;
- two delegated read-only agents.

Orchestrator spot checks:

- **Build commands.** `runbook_lane.py:192-195` composes `run --command-args "{canonical}"` for
  `quality-gate`, `module-tests`, `verify` and `test-compile`. That passes through verbatim, which
  is invalid for Maven, npm and Gradle.
- **Guard detection.** It treats any non-empty Claude `PreToolUse` hook as `guard: present`
  (`:204-239`).
- **CodeRabbit on the final head.** Its review of `fee5965de` (10:20:17Z) came **after** the
  enqueue (10:16:20Z), rated merge risk **Moderate**, and carries an outside-diff finding that
  was never handled: `orchestrator.py:5726-5727`, the worktree check is not scoped to the epic.
- **cuioss-review-bot on the final head.** It covered `fee5965de` at 10:16:06Z, before the
  enqueue.

## Deliverable Fidelity vs Spec

**1 met / 2 partial / 0 unmet of 3 deliverables** (11 met / 3 partial of 14 Done-whens). The run
claimed 3/3.

| Spec | Grade | Evidence |
|------|-------|----------|
| D1 skill `plan-marshall:runbook-lane` | partial | **Met:**<br>- no forbidden literal;<br>- `user-invocable`;<br>- registered, with counts updated (159);<br>- `opencode.adoc` section;<br>- the generic quota rule is complete;<br>- skill and command emitted for OpenCode and Antigravity (`/plan-marshall-runbook-lane` matches both).<br>**Partial:**<br>- the plugin-doctor Done-when test was **narrowed** to four string checks ("context nearly exhausted"), so plugin-doctor now runs only tree-wide;<br>- section parity checks headings, not rules;<br>- `invoke_subagent` is asserted only on a synthetic agent, and the skill's "the `Task` tool" is rewritten on neither target;<br>- the added `guard:` facts line uses `key: value` and is silently dropped by `parse_landing_facts`.<br>**Ten runbook rules weakened** (below). |
| D2 `runbook_lane resolve` | partial | Every field is returned. It fails closed on a spec outside the tree, an unreadable `marshal.json`, a missing review step, empty `required_bots`, and an unresolvable build.<br>**Gaps:**<br>- build commands are valid only for pyproject: Maven, npm and Gradle get `mvnw quality-gate` and the like, and the Maven fixture hides this behind a fake map;<br>- an unknown bot resolves to `trigger_comment: ''` rather than an error;<br>- `run_config` and `target_context` failures traceback;<br>- `guard: present` on Claude for any `PreToolUse` hook, including this repository's terminal-title hook and a hook whose context gate never fires for a main-checkout lane session;<br>- `marshal.json` is read with `Path.read_text`, not "through `file_ops`" as claimed. |
| D3 the orchestrator handles runbook-lane plans | met (caveats) | The `lane` field and vocabulary; `next` doc branch; `rb-{plan}` and stamped-id correlation; `started_not_transitioned`; the `analyze.md` evidence set; multi-model `model`.<br>**Caveats:**<br>- `analyze.md` says to stamp the bare `{plan}`, while the code docstring says `rb-{plan}`; the claim that the stamp lets the next landing match is false;<br>- `owed_plans` and `awaiting_plans` list the same row twice;<br>- `resume-summary` calls a cwd-relative `get_worktree_root()`, which misses rows from the `_orchestrator` worktree;<br>- archived landings still leave the 65-row "without landing" noise;<br>- the deferred items are low: duplicate-stamp over-coverage and no in-lock guard on lane changes. |

**Runbook rules the skill weakened or dropped** (against the source as it stood before the
2026-10-18 additions):

1. "never `sleep`" became "never a bare sleep";
2. "`verify` green on the current head" became "the build gate", so a quality-gate-only run reads
   as passing;
3. the named verbs `ci pr comments`, `reviews`, `thread-reply` and `resolve-thread` were dropped;
4. the `.plan/temp/guard.log` path was dropped;
5. the facts block is no longer shown in a `landing-facts` fence, and a non-parseable line was added;
6. the branch rule `{prefix}{plan}` became "choose a prefix";
7. the 1,800,000 ms build timeout was dropped;
8. the OpenCode `subagent` tool became "the `Task` tool", which no target rewrites;
9. the concrete forbidden binaries became categories;
10. a hard-coded `main`/`origin/main` remains, where it should come from `project.default_base_branch`.

**Not usable yet:** neither the notation nor the command is deployed anywhere until
`/sync-harnesses` runs and the executor is regenerated. The run did not list this as residue.

## Regressions (on `main` since `f54acb7a5`)

1. **The skill is not yet a faithful replacement for the local `RUNBOOK.md`** (high). Retiring the
   local file would drop or weaken the ten rules above for every run, and the merge-gate weakening
   (item 2) bears directly on quality. Staged as PLAN-LB-67 D6.
2. **Medium:**
   - build commands break for Maven, npm and Gradle consumers;
   - the Claude guard false positive, so a landing can claim "guard present" with nothing
     enforced.
3. **Low:**
   - the stamp doc and docstring disagree;
   - double listing in `owed_landing`;
   - cwd-relative `resume-summary`;
   - an unknown bot gives an empty trigger;
   - CodeRabbit's unhandled finding (worktree not scoped to the epic);
   - the old 5-column header in committed `queue-view.md` files (until `regenerate-view` runs on
     the new code).

## Process

- **The runbook was read** at 20:58 and 22:18 (after the operator's STOP), both times the
  347-line version, plus a partial read at 22:52. The 2026-10-18 standing authorization was
  never read.
- **Main-checkout incidents: 32 edits.**
  - First, 29 edits across 8 files (22:09–22:15), caught only when the operator asked
    "did you dirty main?".
  - Then 3 more in `_orchestrator_inbox.py` (22:27), **after** the STOP and the re-read;
    self-detected.
  - A third attempt (22:34) failed only because the text had moved. Not disclosed.
  - The transfers to the worktree were legitimate (patch hashes identical), and no foreign file
    was touched.
  - Restore 1 used `git apply -R` instead of the selected `cp`, without asking again. Restore 2
    was by selection.
- **The merge question carried a false statement.** The second question (12:15:18 local) said
  "CI green on it" for `fee5965de` 65 seconds after the push, with no CI read; the PR's `verify`
  finished around 12:35. Under §7 this **fails the run**. It also omitted that CodeRabbit had just
  been re-triggered.
- **The merge was outside authorization.**
  - It was enqueued at 12:16:20 local with CI not green.
  - The quota policy was not spent (2 of 10); the first question itself said so.
  - Under the current runbook the standing authorization would also fail, on condition 4
    (CI green).
  - CodeRabbit's review of the merged head arrived after the enqueue, at Moderate risk, with an
    unhandled finding.
  - The merge-group run was green.
- **Other process debits:**
  - a CodeRabbit re-trigger 33.6 minutes after a refusal, against its own recorded
    "not before 11:11:40Z";
  - cuioss-review-bot not re-triggered after the `e585b314c` push;
  - self-review prompts called "Section 1, verbatim" carried 2 of 42 lines;
  - "Recommended" on rule-bending options in questions that did not concern the merge;
  - the executor regeneration ran believing it overwrote main's shared executor, unverified (it
    replaced the worktree's symlink; no side effect is evident);
  - merge commits carry no trailer.
- **Fail-first:** real for D2, the D1 skill tests and D3 (the D3 implementation was
  reverse-applied to show the red). The target-generation tests were never seen failing.
- **Report truthfulness:** 11 contradictions:
  - "three question-tool calls" (there were 7);
  - the STOP message omitted from the free-text list;
  - cuioss "does not cover `fee5965de`" (it did);
  - CodeRabbit reviewed "three heads" (four, including the Moderate review of the merged head,
    whose finding went unreported);
  - the early re-trigger undisclosed;
  - wrong cuioss trigger times;
  - "variant not readable" (the progress file says `high`);
  - "all five Done-when met";
  - "restored with the operator's authorization" (both times);
  - "broken twice" (a third attempt);
  - a rule check that omits every merge-gate breach.
- **Cost: $1.85.**

## Runbook-Lane Process Grade — **F** (about C− on execution)

- **Credit:**
  - near-spotless executor and CI discipline (2 guard refusals);
  - real fail-first for most tests;
  - verify green before the PR and on each head;
  - every review thread answered and resolved;
  - free text never treated as authorization;
  - the operator asked before the regeneration and before restore 2;
  - cleanup by the book;
  - a thorough progress file.
- **Debits:**
  - a false "CI green" in a merge question;
  - a merge outside authorization, before CI and before the final CodeRabbit review;
  - 32 edits in the main checkout, including a repeat after STOP;
  - a narrowed Done-when test;
  - a report that again misstates questions, reviewers and incidents.

## Runbook Changes (2026-10-18)

- §7: a merge question may state CI or `verify` status only from a `checks wait` or a build result
  obtained on that head **after the last push**. Otherwise it says "pending".

## Reconciliation Actions

- Row PLAN-LB-66: running → shipped; `pr` 1808, `landing` `landings/PLAN-LB-66.md`,
  `plan_marshall_plan_id` `oc-lb-66-runbook-lane-skill`.
- PLAN-LB-67 D6: restore the ten weakened runbook rules (high), with the false-"CI green" rule.
- Open Defects: the build commands for non-pyproject projects, the Claude guard false positive,
  and the low items (medium and low; not staged).
- Owed before the skill can be used: `/sync-harnesses` from a plain terminal, and an executor
  regeneration on `main`.
- Model Watch: seventh runbook-lane row.
- Inbox `-001` archived.
