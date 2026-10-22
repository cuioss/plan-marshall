# Landing Analysis: PLAN-LB-48 — plan-marshall emits and edits OpenCode 2 configuration

epic: live-blockers
workstream: WS-04
pr: #1830 (merge commit `148558aa168572c54b2dc7dc9892c4acf5f3fe4f`, 2026-10-21T10:10:21Z, branch `fix/lb-48-opencode-2-compat`)

> Landing record for one shipped plan. Written by the `analyze` verb after verifying the landing message
> against ground truth: the merged diff and tree at `148558aa1`, the PR through the `ci` abstraction (state,
> reviews, 54 comments), the run's progress file, the guard log, the commit trailers, and the OpenCode session
> store read-only (572 messages in the main session, 53 in the self-review sub-agent). One read-only
> `execution-context-level-5` agent corroborated the code and the tests; the orchestrator re-read DF1-DF4
> and the five straggler lines itself (the other defects are the corroboration's account, not re-read). The landing says the run is
> **runbook lane on OpenCode**; the emitted command was the `/plan-marshall` form, because the row's lane was
> empty — see Process findings.

## Verdict

**Grade B−.** Every written Done-when is met and is backed by a test that fails against the pre-image (27 tests
audited: none vacuous, most sound, eight weak or half tautological), the run is genuinely test-first, the
three-round self-review caught a real high-severity regression (F1), all eight CodeRabbit threads were fixed
or answered and are resolved, the sub-agent used no daemon build, and the guard-log and trailer claims are
true. The grade is held down by what the spec asked for and the Done-whens did not pin: D5's "never reports
`bridge_drift: False` for a bridge it just rewrote" is false in two arms, D2's "no bundle standard calls the
tool `task`" left five lines in the OpenCode target-rules skill, the permission writer can still reverse a
more specific rule it reports as added (DF1, introduced by a commit the self-review never saw). Process
debits: the merge went out two heads after the operator's selection, the shell
file-operation count is 42 rather than "early in the run", `total_tokens` is `unknown` for a run that cost
$1.30, and the `test-compile` record is a list of shas rather than a record of runs.

Lane text loaded: the PLAN-LB-72 text (`cf28a05db`, the newest on `main`), read once at 2026-10-20T19:05:59Z from
the installed OpenCode copy (content equal to `cf28a05db` apart from `AskUserQuestion` -> `question`,
`Task` -> `subagent` and the harness footer). It was **not** re-read after the 5 h 38 m idle gap that ended with
the operator's `retry` at 2026-10-21T05:04:54Z. No lane change had landed since, so the missed re-read cost
nothing here.

## Deliverable Fidelity vs Spec

| Deliverable (spec) | Verdict | Evidence |
|--------------------|---------|----------|
| D1 — the target emits OpenCode 2 configuration | shipped-as-specified | `emitter.py:527-532` writes `{$schema, skills: ['./skills'], agents}` only; `frontmatter.py:339-344` writes a `permissions` list; `variant_emitter.py:142` delegates to the same transform, so variants get the new shape although the file is untouched. The emitter sets no `subtask`, so the command-frontmatter bullet was vacuous. The "same effect per tool" test is half tautological (below). |
| D2 — tool names and directives match OpenCode 2 | shipped-modified | `mapping.json` `Bash` -> `shell`, `Task` -> `subagent`, directive `{ id: … }`; `subagent_dispatch` returns `tool: subagent`, `agent`, `description`, `prompt`; the parser accepts `subagent`. **Miss:** `plan-marshall-opencode/skills/target-rules/SKILL.md` L15, L19, L28, L35 still say `bash` / `task` (read by the orchestrator); the spec's guard test globs `*/skills/*/standards/*.md` and cannot see it. `to_opencode_grant` does not recognise `shell` (DF4). |
| D3 — the permission tooling reads and writes the shape the file has | shipped-as-specified | List-aware read/write in every operation the spec names; a map-shaped file keeps the map path; `permission fix` returns `io_error` on a failed list or map write; `analyze` reports `permission_shape` and `deny_rules`. Three defects remain (DF1, DF5, DF7). |
| D4 — the installed version is checked | shipped-as-specified | Health `version` check (`opencode_runtime.py:2403-2419`): absent or unparseable -> not checkable, major != 2 -> mismatch; `TARGET_ENV_SIGNALS` has no `OPENCODE_PID`. Gaps: a non-zero exit is not checked (DF9), no test for unparseable output. |
| D5 — the standing rules reach an OpenCode agent | shipped-modified | Bridge carries `CLAUDE.md` and `source-sha256`; drift is by hash; the verdict is taken before the heal; an unreadable baseline keeps the bridge; rules (a) and (b) are in the persona and the OpenCode rules. **Not met:** "never reports `bridge_drift: False` for a bridge it just rewrote" fails in two arms (DF3), and a non-UTF-8 `CLAUDE.md` crashes setup (DF2). |
| Added-unplanned | — | 32 files beyond the declared surface (20 declared, 49 realized, 3 declared and untouched: `variant_emitter.py`, `test_emitter.py`, `test_permission_ops.py`). Eight groups are necessary consequences of D1-D5 (doc and noun sweeps, the `OPENCODE_PID` removal, downstream suites that pinned the old shape, `frontmatter.py` where the agent frontmatter is actually rendered, `install.sh`). One is beyond the spec: the marshall-steward, tools-script-executor, manage-metrics and marketplace_paths matrices were rewritten to derive their rows from the unit's own `TARGET_ENV_SIGNALS`, which weakens them (below). The surface was under-declared, as in every earlier landing in this lane. |

### Tests

27 audited; none vacuous. Sound: the shape, install, directive, ensure-defaults, configure, analyze, fix, io_error,
protect-path, web, health and version tests, `test_subagent_dispatch_echoes_requested_agent`, the sentinel and
drift tests, `test_opencode_pid_alone_does_not_resolve`. Weak points the run did not disclose:

- `test_emitted_agent_permissions_evaluate_like_the_source_tool_grants`: the ungranted half cannot fail, because the emitter writes no rule for an ungranted tool and the evaluator defaults to `ask`; it evaluates the agent list in isolation, never merged with project rules.
- `test_no_bundle_standard_names_the_opencode_subagent_tool_as_task` globs the wrong tree (it misses `target-rules/SKILL.md` and `workflow/execution.md`, which the spec named).
- `test_an_unreadable_baseline_never_overwrites_the_bridge` monkeypatches the unit's own `_baseline_text` to `None`; no real unreadable file is ever read, so DF2 passed.
- `test_a_deleted_baseline_replaces_the_bridge_with_the_stub` asserts `bridge_reason` and not `bridge_drift`, which tolerates DF3.
- `test_mapping_uses_opencode2_tool_names`, `test_mapping_skill_directive_passes_an_id`, `test_mapping_task_note_agrees_with_its_tool_mapping`, `test_default_permissions_constant_is_not_empty` and `test_opencode_pid_is_not_a_declared_signal` pin constants, and `test_ensure_defaults_is_idempotent_in_the_list_shape` passes at the pre-image.
- `test_to_opencode_grant_accepts_the_opencode2_subagent_key` does not check that a list write produces action `subagent` (the spec's "maps it to the OpenCode 2 rule"); no health-version test covers unparseable output or a non-zero exit.
- The `TARGET_ENV_SIGNALS` matrices in `test_manage_metrics_enrich`, `test_cache_freshness`, `test_cache_retention`, `test_executor_target_resolution` now derive precedence and parametrization from the unit's own registry: reordering it or dropping a signal passes silently (previously pinned antigravity > opencode > claude).

### Order labels

The audit read the tests against the pre-image from the code (the corroboration), not the order from build
logs: it confirms every `test-first` row would fail at the pre-image except `test_ensure_defaults_is_idempotent_in_the_list_shape`
(passes there) and the deliberate regression guard `test_permission_fix_ensure_still_writes_the_legacy_map`. The
failing-run log names (`python-2026-10-20-…log`) were not opened one by one, so the order labels are the landing's
account; the one structural check made is that the transcript shows a red `quality-gate` or `verify` before most
commits. The two `mutation-after` rows cite logs of the fix reverted in place.

## Code defects (PLAN-LB-83)

Confirmed by the corroboration; DF1-DF4 and DF6 re-read by the orchestrator.

- **DF1** (medium, introduced in `7ba1fe838`, after the last self-review): `_move_rule_to_end` (`opencode_runtime.py:503-546`) moves a requested rule to the END of the list whenever a later rule beats it, which then overrides later, MORE specific rules. `[{shell,*,allow},{shell,"git push --force *",deny},{shell,"git *",ask}]` + `ensure deny(git push *)` turns `git push --force x` into an allow.
- **DF2** (medium): `_baseline_text` catches `OSError` only (`:121-126`); a non-UTF-8 `CLAUDE.md` raises `UnicodeDecodeError` out of `standing_rules_drift_status` and crashes `project_initial_setup`.
- **DF3** (medium): setup reports `bridge_drift: False` for a bridge it rewrote. (a) `CLAUDE.md` deleted: `standing_rules_drift_status` returns `{'drift': False, 'reason': 'baseline_missing'}` (`:199-200`) while `_write_rules_bridge` replaces the carried rules with the stub (`:176-184`). (b) A hand-edited bridge body with marker and hash intact reads `in_sync` and is then rewritten because the body no longer equals the generated one. Contradicts `opencode-rules.md:60`.
- **DF4** (medium): `to_opencode_grant` has no `shell` in its bare-key tuple (`:317-332`), so `deny(shell)` becomes `('bash', 'shell', 'deny')`, a deny of the literal command `shell`.
- **DF5** (medium, pre-existing on the map path): no `error` check on a loaded `opencode.json`; invalid JSON loads as `{"error": …}` and `create=True` saves `{error, permissions}` over the operator's file (`opencode_runtime.py:1401-1403`, `permission_fix.py:378-395`). Not re-read.
- **DF6** (minor): `ensure-defaults` returns `applied: False` with no error when the list write fails (`:2018-2027`) and `project_initial_setup` ignores the result (`:969`), so setup reports success with no executor rule written.
- **DF7** (minor): two deny parsers disagree on a hybrid file (`_deny_rules` `:596-608` reads the list only and ignores `agents.*.permissions`; `_deny_rules_from_config` `:688-731` unions both).
- **DF8** (minor): `cmd_add` / `cmd_remove` have no OpenCode branch (`permission_fix.py:314`, `:347`): an OpenCode 2 file raises `TypeError`; OpenCode 1 raises `KeyError` (pre-existing).
- **DF9** (minor, plausible): `installed_opencode_version` ignores `returncode` (`:571-578`); a failing `opencode --version` whose stderr carries `N.M` is read as the major.
- **DF10** (minor): an OpenCode 1 map file given a `subagent` / `task` grant gets a `subagent` map key OpenCode 1 does not know (`:1464-1487`).
- **DF11** (minor, plausible): a rule with a wildcard `action` later in the list is invisible to the effective-effect check (`:461-476`).
- **DF12** (high if confirmed, plausible): emitted agents carry `{shell,*,allow}` (`frontmatter.py:339-344`); if OpenCode 2 evaluates agent rules after global ones, that overrides a global `rm *` / `gh *` deny. Pre-existing as `bash: allow`.
- **DF13** (medium, plausible): a new project config gets `{shell,*,ask}` first (`_opencode2_skeleton` `:591`); under global-then-project order it overrides every global shell deny.
- Stragglers (read): `plan-marshall-opencode/skills/target-rules/SKILL.md` L15 (`bash`), L19 and L35 (`task`), L28 (`bash`), L34 (mtime drift); `doc/developer/opencode.adoc` role matrix "Git write" cites map notation for a list rule; the root `opencode.json` L2731-2737 still carries an OpenCode 1 `permission.bash` map beside its `permissions` list (landed by the steward, #1812, through the pre-image `ensure-defaults`; a guarded configuration file and an operator decision, not PLAN-LB-83's).

## Metrics and Anomalies

- Tokens (from `session_v2`, the landing says `unknown`): main session (`build`) input 2,606,536 / output 148,881 / reasoning 67,915 / cache-read 215,786,624, cost $1.168; self-review sub-agent (`general`) input 267,446 / output 24,641 / reasoning 55,319 / cache-read 15,912,832, cost $0.136. Total input 2,873,982, output 173,522, reasoning 123,234, cache-read 231,699,456; **$1.304**. Every assistant message is `deepseek-v4.1-flash` variant `high`, provider opencode-go; OpenCode 2.1.1 at both sessions.
- Duration: 15 h 27 m (2026-10-20T19:04:35Z to 2026-10-21T10:32:15Z). Idle gap 5 h 38 m before the operator's `retry` (the session had stopped); operator question 48 m (07:47:26Z to 08:35:39Z); the rest is builds, CI and the CodeRabbit windows. One idle cycle; compactions were not checked.
- Tool use in the main session: 296 shell, 225 edits, 138 reads, 40 greps, 31 writes, 3 sub-agent dispatches, 1 question; 91 in-process builds, none through the daemon; the sub-agent ran 33 shell calls and 1 in-process build.
- $1.30 against LB-77's $0.81 and LB-45's $3.78: about 1.6x LB-77 for 5 deliverables over 49 files against 3 over about 15.
- Merge time: the squash was stamped 10:10:21Z; the landing was written 10:32:06Z.

## Routing and Merge Behavior

- **Reviewers**: cuioss-review-bot (`quota_limited=false`) never posted a comment, review or check on #1830; `/review` was posted six times (22:10:16, 05:08:30, 05:52:01, 07:11:42, 08:48:26, 09:39:59, all verified) and the landing lists the same six times. The cause the run gives (no caller workflow for the org's reusable workflow in this repository) is its own account; #1829 (`ee06267b8`) removed the bot's block from `.github/project.yml` while the run was in flight.
- coderabbit: formal reviews 22:15:59 (`adde127af`, 7 actionable), 05:17:43 (`7a45e5d06`), 06:44:57 (`94e044ce1`), 08:53:34 (`092bc1a38`, 1 actionable) — all four match the landing — and a thread reply at 09:36:56 confirming the `bc0f6b9c8` guard ("separates the two cases correctly"), which the landing does not mention: CodeRabbit did read the final semantic fix, in-thread, 8 minutes before the refused re-trigger. Triggers 22:12:02, 05:52:15, 07:11:57 (replied 07:12:03), 08:48:45 (review 08:53), 09:44:34 (refused 09:44:46). All eight threads are `resolved: true`.
- sourcery: the automatic refusal on open (22:08:38) and one manual trigger (22:12:33, refused 22:12:39). The landing's "`@sourcery-ai review` at 22:12 and again later" is wrong: there was no later trigger. Optional; no gate.
- **90-minute floor**: held between 07:11:57 and 08:48:45 (96 m 48 s); the 05:52:15 and 07:11:57 triggers fall after a qualifying review (06:44:57 for the second) and so under the standing authorization, not the floor.
- **Standing authorization**: conditions 1-3 are met for `092bc1a38`/`bc0f6b9c8` (qualifying review at 08:53:34; its one finding fixed in `bc0f6b9c8`; one re-trigger after the push, refused). Condition 4 (every other gate green on the current head): cuioss-review-bot is covered only by the operator's selection, made at head `e994da000` (07:47:26Z, answered 08:35:39Z). The merge went out at `bc0f6b9c8`, **two heads later** (`092bc1a38` merged `main`; `bc0f6b9c8` changed the bridge's missing-versus-unreadable semantics). The lane (§ immediately before enqueue) says to repeat step 6 when the base moved. This is the second datapoint (after LB-77) for the open ruling on whether a selection covers later heads. Mitigation the run could not know: the merge of `main` removed the bot from the project's required list, so a fresh `runbook_lane resolve` lists only CodeRabbit.
- CI: not re-read per head. The merge-group run `39582646491` completed `success`; `queue-state` reads `merged` with the merge SHA on `origin/main`.
- Commit trailers: all 14 non-merge commits carry exactly `Co-Authored-By: plan-marshall <noreply@cuioss.de>`; the merge commit `092bc1a38` carries **none** (the lane tells the run to `git merge origin/{base_branch}` with no message; PLAN-LB-77's `06610bd71` is the first instance).

## Operator questions (rebuilt from the transcript)

Exactly one, completed; no aborted question; one free-text message (`retry`, 05:04:54Z, after the idle gap).

1. 07:47:26Z, header "Merge gate: reviewer gap", options Merge now accepting the cuioss-review-bot gap / Do not merge; leave the PR open / Merge only after enrolling the bot. **Selected: "Merge now, accepting the cuioss-review-bot gap"** at 08:35:39Z. The facts in the question are accurate (head `e994da000`, four `/review` triggers at 22:10, 05:07 [05:08:30 in the PR], 05:52, 07:11, the 07:11:57 CodeRabbit re-trigger refused 07:12:03, Sourcery refused). The question named a head and the merge went out two heads later; no second question was asked.

## Process findings

- **Lane**: PLAN-LB-72 text (`cf28a05db`), loaded once; not re-read after the idle gap. The user message that started the run was the pasted `emitted[]` row (`PLAN-LB-48,/plan-marshall task="implement …"`); the model loaded `plan-marshall-plan-marshall`, found no registered `/plan-marshall` command, and switched to the runbook lane at 19:05:59Z after about a minute of exploration (15 `ls` calls). The row's `lane` was empty, so the emitted command was the plan-lifecycle form for a plan that only runs in the lane on OpenCode.
- **Rule breaks the landing under-reports**: the landing says shell `ls`, `grep`, `sed -n` and `tail` were used "early in the run". The transcript has 42 shell file-operation calls (15 `ls`, 15 `grep`, 8 `tail`, 3 `sed`, 1 `wc`) between 19:04Z and 10:31Z, the last two minutes before the landing was written; one `sed -i` at 19:22Z and two `git add -A` at 19:37Z and 20:02Z (all three disclosed). Guard log: the four lines it lists are the whole log for both sessions (3 main, 1 sub-agent) and match the transcript's three guard-blocked main calls and one sub-agent call.
- **Skills and personas**: the spec named none (`skills: none named` is true); the lane loaded `persona-plan-marshall-agent` only; the landing's persona list (implementer, module-tester, documenter, code-reviewer) is a description of roles, and only the sub-agent loaded the reviewer persona per its own prompt (the transcript shows 2 `skill` calls in the main session — the lifecycle skill and the lane — and 1 in the sub-agent).
- **Self-review**: three dispatches to one sub-agent session, 21:01Z to 22:07Z. Round 1: 10 findings, round 2: 4, round 3: none open. It covered the tree up to `adde127af` (21:40Z). **The seven commits after it were never self-reviewed**: `7ba1fe838`, `7a45e5d06`, `83afb5e33`, `94e044ce1`, `e994da000`, `092bc1a38`, `bc0f6b9c8`. DF1 originates in `7ba1fe838` and DF3(a), the replace-with-stub arm for a deleted baseline, in `bc0f6b9c8`. The landing's `self-review:clear` is true only for one head of fifteen.
- **Sub-agent builds**: one in-process build, no daemon build and no `git grep` (LB-77's 17 daemon builds do not recur).
- **Main-session builds**: 91 in-process; local `verify` (which includes `test-compile`) succeeded against the content of `11a75cb59`, `adde127af`, `94e044ce1`, `e994da000`, `092bc1a38` (after the merge of `main`) and `bc0f6b9c8`; the other nine heads had `quality-gate` locally and nothing else.
- **Residue claim**: "cuioss-review-bot remains unenrolled in this repository, so every future plan will hit the same required-reviewer gap" is stale: `#1829` removed the bot from `.github/project.yml` and a fresh `runbook_lane resolve` lists only CodeRabbit as required. `.plan/marshal.json` was not read; the standing bot-list rule says it still names both, so the two now disagree (Watch).

### `test-compile` at every pushed head

The landing lists fourteen heads and says `test-compile` ran at each "inside the CI `verify` job"; `83afb5e33` is missing from the list although the landing's own CI note says it ran red there. The lane requires the sha of each run to be recorded, and the run recorded no run of its own.

| Head | Local evidence |
|------|----------------|
| `dab0afe6e`, `0459a4278`, `4eabac1ec`, `12ee9ce5f`, `38dfdba36`, `5d2fe95f2`, `7ba1fe838`, `7a45e5d06`, `83afb5e33` | `quality-gate` only; CI per head not read |
| `11a75cb59` | local `verify` success at 20:47Z (content of the commit) |
| `adde127af` | local `verify` success at 21:40Z, 31,559 tests |
| `94e044ce1` | local `verify` success at 06:30Z |
| `e994da000` | local `verify` success at 07:02Z |
| `092bc1a38` | local `verify` success at 08:37Z (after the merge of `main`) |
| `bc0f6b9c8` | local `verify` success at 09:27Z |

## Landing-message accuracy

Correct: the PR number and merge sha; the base `18020aad0` and the mid-run merge of `main`; the five deliverable verdicts as far as their Done-whens go; the CodeRabbit finding set and fixes (eight threads, two withdrawn on reasons); the six `/review` times; the four CodeRabbit review heads; the guard-log lines and the `sed -i` and `git add -A` disclosures; the operator question and its option; the two review-found D3 and D5 regressions; the three self-review round counts; the residue list; trailers on the 14 non-merge commits.

False or misleading:

1. §7 "…early in the run": 42 shell file operations across the whole run, to 10:31Z.
2. §1 "`test-compile` ran at every pushed head … inside the CI `verify` job": no local `test-compile` or per-head CI record; `83afb5e33` omitted from the list.
3. Facts block: `total_tokens=unknown` (2.87M input, $1.30 measured); `effort` and `plugin_version` absent; `model=deepseek-v4.1-flash` without the variant `high`; `self-review: clear` for one head of fifteen.
4. §5 "Operator authorized the merge naming this exact gap": the selection named `e994da000`; the merge was at `bc0f6b9c8`.
5. §5 sourcery "`@sourcery-ai review` at 22:12 and again later": one manual trigger.
6. §5 coderabbit omits the 09:36:56 in-thread confirmation of the final fix (in the run's favour).
7. §4 "every thread is resolved" is true; "D5 … met" and "D2 … met" are true of their Done-whens and false of the spec's bullets (DF3, the target-rules lines).
8. §8 "every future plan will hit the same required-reviewer gap": stale since #1829.
9. §7 does not mention the trailerless merge commit `092bc1a38`.
10. `landing-check`: `complete: false`, `missing_keys` = `total_tokens`, `effort`, `plugin_version` — **recurrence 2** of the PLAN-LB-78 D3 defect (LB-77 was recurrence 1), not a new one.

## Reconciliation Actions

- [x] row `status` -> `shipped` — `orchestrator queue --transition PLAN-LB-48 --status shipped`
- [x] row `pr` stamped — `1830`
- [x] row `landing` stamped — `landings/PLAN-LB-48.md`
- [x] row `plan_marshall_plan_id` stamped — `lb-48-opencode-2-compat` (from the sender `rb-lb-48-opencode-2-compat`)
- [x] row `lane` stamped — `runbook` (the row was empty; the run executed in the runbook lane)
- [x] `epic.md`: grade and watch entries, the incomplete-landing defect recurrence, the PLAN-LB-48 defects and the retired OpenCode detection entry, the Queue annotations
- [x] PLAN-LB-83 staged (`lb-48-completion`, medium, WS-04, runbook lane) and its Expected Surface verified with `corpus surfaces`
- [x] PLAN-LB-73 D1 gains the trailerless-merge bullet and Done-when (no surface change); PLAN-LB-49 and PLAN-LB-81 re-ground notes (no surface change)
- [x] resume anchor rewritten; `queue-view.md` regenerated

## Follow-Ups

- PLAN-LB-83 owns DF1-DF13 and the stragglers, except the root `opencode.json` map (operator decision).
- PLAN-LB-69 (landing audit): a `test-compile` claim that rests on CI the run never read per head; an "early in the run" count set against the transcript's shell-call times; a selection that names a head and a merge on a later head.
- PLAN-LB-73: the lane's own merge instruction produces a trailerless commit.
- Rulings for the operator: whether a selection made at one head covers later heads (LB-77 and LB-48 both merged on a later head); whether the lane's required-reviewer set may differ from the standing bot list now that `project.yml` no longer names the bot.
