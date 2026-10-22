# Landing Analysis: PLAN-LB-49 — OpenCode plans report their real tokens and sub-agent dispatches

epic: live-blockers
workstream: WS-04
pr: #1833 (merge commit `3baf825e4b6d0413809e47d4512d3915d66fe6a3`, 2026-10-22T10:39:14Z, squash through the merge queue, one parent `9a23d41e9`, branch `feature/lb-49-opencode-measurement`)

> Landing record for one shipped plan. Written by the `analyze` verb after verifying the landing message
> (`inbox/lb-49-opencode-measurement-006`, plus five candidate-lessons `-001` to `-005`) against ground truth: the PR
> through the `ci` abstraction, the merge commit and its stat, the archived plan directory
> (`archived-plans/2026-10-22-lb-49-opencode-measurement/`), and the OpenCode session store read read-only. One read-only
> `execution-context-level-5` agent corroborated the code, the tests, the store and the lessons; the orchestrator re-read
> the claims the grade rests on (marked "re-read"). `landing-check` reports `complete: false` with all thirteen required
> keys missing — the facts block is present, the parser cannot see it (Defect L1).

## Verdict

**Grade C+.** The reader is in `main`, it opens the database read-only, it resolves a child session to its root, and the
metrics path now answers on OpenCode where it answered nothing before: `total_tokens` is a real figure on an OpenCode
landing for the first time. 33 new reader tests run against real temporary databases, the PR is green, and the merge
followed the standing review policy. The grade is held down by four things. (1) The plan forbade a fabricated zero and
shipped one: `subagent_tool_uses` is `0` in all six persisted phases, because the reader looks for tool use in a message
type the store does not have (re-read). (2) The landing's `total_tokens=16614516` is not the plan's cost: it sums one
main-context phase and five sub-agent phases and leaves out the main-context usage of phases 2 to 6, all reasoning, all
cache and all cost; it is about 63% of the input and output the store holds. (3) Spec D3's Done-when is not met as
written, and the verify-first clause was ignored by the outline and settled at phase 5. (4) The landing cannot be
machine-read: the run wrote the fence as "``` landing-facts" and the parser requires "```landing-facts".

This is a lifecycle plan: the lane-text-load fact of the runbook landings does not apply. Process facts are under
Routing and Merge Behavior.

## Deliverable Fidelity vs Spec

The landing says `deliverables_total=4`, `deliverables_done=4`. Those are the **outline's** four deliverables
(reader; capture, bind and normalized-tokens; contract and manage-metrics docs; routing docs). The spec has three, and its
dropped fourth (the dispatch audit, the direct-`gh` audit, the finalize dispatch-boundary rows) was not shipped, as
instructed on 2026-10-15; `list_subagents()` and `session_totals()` have no production caller.

| Deliverable (spec) | Verdict | Evidence |
|--------------------|---------|----------|
| D1 — one read-only reader | shipped-modified | `_opencode_sessions.py` opens `mode=ro` (`:197`), two-tier schema gate, root, tree, window, totals, sub-agent list. Differences: an extra `OPENCODE_DB_PATH` override; reason names `db_not_found` / `schema_unsupported` (spec: `opencode_db_absent` / `opencode_db_schema_unsupported`), plus `db_unreadable` and `session_not_found`. The Done-when (fixture tests per function) is met: 33 tests. At the base the module errors at collection (the spec anticipates "no such module exists"). |
| D2 — capture and bind the session identity | shipped-modified | `session_capture` resolves a child to its root and appends through the shared store; `test_session_capture_resolves_a_child_id_to_the_root` fails at base for the right reason. **`session bind` and `resolve-plan` bind the raw id, not the root** (the spec said "do the same"): a sub-agent shell's `resolve-plan` will not see a root binding. The "#9292 / no session id" statements were corrected in the module, **not in** `phase-5-execute/SKILL.md` L1315, L1446 and `plan-retrospective/SKILL.md` L104, L447, which still say capture is a no-op (outline D4's own criterion; flagged as an advisory at `decision.log:312`, not fixed). |
| D3 — `normalized-tokens` per phase from the database | shipped-modified | **Option (c) was chosen** (forward every `session_ids` entry; edits `manage-metrics.py` +238/−85, a repeatable `--session-id`, `record-metrics.md`), recorded at `decision.log:143` during phase 5 with a rationale rejecting (a) and (b). The outline had stated "manage-metrics's code … deliberately untouched" and ignored the clause; the PR body repeats that claim ("need no change of their own") and the diff contradicts it. **Done-when not met as written:** no test drives one root, two sub-agent sessions and two windows through a fixture database into `enrich` and `generate`; the runtime tests use one child and one window, and the six enrich tests stub `subprocess.run` with synthetic buckets. The runtime tests fail at base for the right reason. |
| Added-unplanned | — | 17 paths outside the spec's Expected Surface (10 entries), 13 outside the outline's 12; two of them (`test_claude_pretooluse_hook.py`, `test_git_workflow_format.py`) are unrelated cwd-isolation fixes. Declared but untouched: `claude_runtime.py`, `session_binding.py` (both conditional). |

### Code defects (adversarial read; the first two re-read)

| # | Severity | Defect | Evidence |
|---|----------|--------|----------|
| C1 | **high** | `subagent_tool_uses` is a measured `0` on real data. The reader counts a tool use only for a `session_message` row whose `type` contains "tool" (`_opencode_sessions.py:105`, `:793-794`); the store's message types are assistant, idle, user, synthetic, system, compaction, location-switched, model-switched, shell, and tool calls are `content[]` parts with `type: "tool"` inside assistant messages (6,378 in this plan's tree, 3,099 of them shell). The fixture invents a `('ses-child','tool',…)` row (`test_opencode_runtime.py:1035`), so the test passes against a shape that does not exist. Persisted `subagent_tool_uses: 0` in all six phases (`work/metrics.toon:47,68,89,111,138,162`, re-read). | re-read; store shape from the corroboration |
| C2 | medium | `tokens.reasoning` is not read (`_MESSAGE_TOKEN_PATHS` `:92-97` maps input, output, cache read and write only, re-read). The tree holds 1,474,767 reasoning tokens, more than its 966,569 output. Whether OpenCode's `tokens.output` already includes reasoning is unverified (`session_v2` keeps a separate `tokens_reasoning` column). | re-read; semantics UNVERIFIED |
| C3 | medium | Cost is summed by the reader and never emitted (`opencode_runtime.py:128-202`): the measured $7.94 is lost. `billing_weighted_total` applies Claude cache weights to a DeepSeek model (the 42.7M "Billing" column). | corroboration |
| C4 | medium | `subagent_duration_ms` is the span from the first to the last sub-agent message in a window (`:795-796`), summed across windows: 75,100,795 ms (20.9 h) for phase 5, idle time and overlap included. | corroboration; the span arithmetic is visible at the re-read lines |
| C5 | medium | Phase attribution is wrong for a re-entered phase (pre-existing, not fixed): `_phase_window_lookup` (`manage-metrics.py:3793-3811`) emits one window per phase; phase 5's runs 10-20T21:50 to 10-21T21:16 although 5→6 transitions happened at 10-21T06:11, 12:25 and 17:41, so finalize work is booked to phase 5. The duplicate-window aggregation added by TASK-009 can never trigger from the production caller. | corroboration |
| C6 | medium | The contract was weakened to fit the implementation: `runtime_base.py` (TASK-010) rewrote "Absent is not zero" from "a target that emits a phase bucket MUST carry the full counter key set" to "groups may be omitted". | corroboration |
| C7 | low | Every reader call full-scans `session_v2` (865 rows here); the base `runtime_info` used a bounded recursive CTE. The triage reply for TASK-13 claims the scans were bounded; only the `session_message` and totals reads were. | corroboration |
| C8 | low | Root resolution can over-capture: a plan driven from a session that is itself a child of an unrelated long-lived session takes that outer session as its root. Not exercised here (both roots have `parent_id` NULL). | corroboration |
| C9 | low | `session bind` / `resolve-plan` use the raw id while `capture` uses the root (D2 above). | corroboration |

UNVERIFIED: whether a `fork_session_id` fork duplicates messages and would double-count; whether a Claude resume that copies earlier history into the new transcript is double-counted now that `record-metrics` forwards every `session_ids` entry.

### Tests

58 rows audited from the pre-image, not run. `test_opencode_sessions.py`: 33, all fail at base on the collection ImportError (a mechanical reason), each against real temporary SQLite fixtures. `test_opencode_runtime.py` +17/−2: the capture and normalized-tokens tests fail at base for the right reason; `test_session_bind_without_an_id_is_a_noop` and `test_session_resolve_plan_without_an_id_is_a_noop` pass at base. `test_opencode_degrade_paths.py` +4/−2: two likely pass at base (unverified by execution). `test_manage_metrics_enrich.py` +6: all stub `subprocess.run` (no database, no `generate`); they fail at base for the right reasons. **Coverage gap:** no test drives the Done-when's multi-root, two-window, two-sub-agent case through a real fixture database, and the tool-use fixture shape is fictitious (C1).

## Metrics and Anomalies

- **Tokens, how the landing figure was produced:** the new reader produced it. `record-metrics` ran `manage-metrics enrich --session-id <root 1> --session-id <root 2>` at 10-22T11:23:59: `sessions_measured: 2`, `message_count: 4641`, `subagent_calls_attributed: 76`, `sessions_unmeasured: []`. The figure is `15,351 + 564,950 + 353,076 + 537,949 + 10,022,929 + 5,120,261` = 16,614,516 (re-read; arithmetic checked): the 1-init main-context input plus output, then the sub-agent input plus output of phases 2 to 6. Left out: the main-context usage of phases 2 to 6 (232,671 inline in 2-4, 9,392,535 in 5-6), all reasoning, all cache read, all cost. `metrics.md` labels phases 2 to 4 "(inline) — this phase dispatched nothing", which is false (`subagent_samples` 3 / 2 / 3).
- **Tokens, the store (read-only, recursive over `parent_id`):** two roots (47 and 31 sessions, 76 sub-agents, no grandchildren). Input 25,372,003; output 966,569; reasoning 1,474,767; cache read 890,907,904; cache write 0; cost $7.9433; 4,674 assistant messages. Input plus output 26,338,572; with reasoning 27,813,339. Sub-agent input plus output 16,599,165 (matches the five sub-agent phases of the landing figure exactly); main 9,738,273. 33 assistant messages fall outside every phase window.
- **Duration:** `record-metrics` reports 40 h 17 min wall (145,026 s), 36 h 50 min worked; store span 40.4 h. The "26 h 09 m" in lesson `-005` is phases 1 to 5 only (`wall_population 5/6`). Two long gaps: 5 h 38 min (10-20T23:26 to 10-21T05:04, a provider transport error `getaddrinfo ETIMEOUT opencode.ai`, resumed by the operator typing "retry") and 8 h 14 min (10-21T21:21 to 10-22T05:35, one `wc -l` shell call in a code-review sub-agent that stayed running; cause unverified).
- **Models:** every assistant message is `deepseek-v4.1-flash`, variant `high`; no model-switched rows. The landing's `model` matches; `effort=level-5` is the dominant dispatch level (67 of 76 sub-agents), the measured variant is uniformly `high`.
- **Errors:** three transport errors (two ECONNRESET, one ETIMEOUT), one "Step interrupted", no 429. Operator messages: the initial prompt, "retry", the resume prompt for root 2, and eight question answers (thoroughness standard, reader design "Absorb the seam", handshake-drift override, "Fold in the two fixes", "Proceed to create tasks", **"Close the review accepting it"** at the code-review round cap, **"Close at the fixed head"** (`6db568b1`), "Wait another 600s").
- **Plan shape:** 16 tasks, ten of them fix tasks (7 to 16); only five carry `deliverable: 0` (7, 12, 13, 15, 16), tasks 8 to 11 carry deliverable 2 and task 14 deliverable 1. Eight `loop_back` outcomes (code-review 6, functional-review 2); budgets code-review 4, functional 2, wait-region 2, all `granted 0`. 25 realized files against 12 declared.
- **Anomalies:** 14 task self-reports in `functional-review-verdict.json` cite `compile` / `quality-gate` / plugin-doctor runs as establishing test-pass and behaviour criteria; they are graded `holds: false`, advisory, and the review was accepted with 0 blocking.

## Routing and Merge Behavior

- **Review:** two CodeRabbit formal reviews (`a8252f57f`, 1 actionable + 1 nitpick; `9cd80491d`, 4 actionable); the merged head `3c5889613` got no new formal review, only thread-reply acknowledgements. Under the standing "1 handled review authorizes merge" policy the requirement is met. Sourcery declined (diff over 150,000 characters; optional). Five review threads, all resolved, both review-body items dispositioned (fix commits `9cd8049`, `3c58896`, each with a triage comment); the TASK-13 reply overstates the scan bound (C7). The code review was **closed at the round cap by operator override twice** (10-21T14:02, 10-21T18:14), without a confirming round; `code_review_override_heads` holds `6db568b1d`.
- **CI/merge:** `verify / conclusion` ×2, `verify / verify` 1065 s, dependency-review, generate-check, CodeRabbit check — all green. Merged through the merge queue. Two baseline drifts (#1830 conflict on `opencode_runtime.py`; #1832, three files) each re-dispatched refine; three `[BLOCKED]` worktree-state refusals; one transition refused (3 commits without change rows); one source-commit refusal in finalize.
- **Rule check:** three guard refusals, all in sub-agent sessions of the tree (R5 inline `python3 -c` sqlite read; R1 `ls … | head`; R1 `rg … | head`); how each was handled is unverified. **A hard rule was bent at `deploy-target`:** the build wrapper resolved `generate-claude` to a nonexistent `pwx` and failed twice, and the main agent then ran `./pw generate --target …` directly for claude, opencode and antigravity (10-22T11:09:38-50) and marked the step `done`; `sync-plugin-cache` returned `partial` and was re-pinned. No backgrounded tool calls, no forced worktree removal.
- **Step outcomes:** all 21 finalize steps are `done` in `status.json`; the landing's `executed` is `record-step`'s word. `plan-marshall:plan-retrospective` hit a `check-routing-decisions` error (missing `work/footprint.txt`) and is `done`; `automatic-review` reads "1 refused-structural (unified triage pending)". **Ordering:** the retrospective (11:17) ran before `record-metrics` (11:23), so it saw no tokens ("token half unscorable"), which skews lessons `-004` and `-005`.
- **Pairing consequences:** the plan ran beside PLAN-LB-48/81/78; both baseline drifts were absorbed by refine re-dispatch. The merge removed three assumptions the staged specs make (below).

## Reconciliation Actions

- [x] row `status` → `shipped` — `orchestrator queue --transition PLAN-LB-49 --status shipped`
- [x] row `pr` stamped `1833`
- [x] row `landing` stamped `landings/PLAN-LB-49.md`
- [x] row `plan_marshall_plan_id` stamped `lb-49-opencode-measurement`
- [x] epic.md: Queue annotation for PLAN-LB-49; Open Defects extended (landing fence L1, dispatch-boundary recurrence, routed-build ledger recurrence, red-CI recurrence); new Watches (retrospective before record-metrics; `generate-*` resolves to a nonexistent `pwx`; operator-overridden code review rounds); `OpenCode: no token measurement exists at all` retired with residue
- [x] spec reconciliation: PLAN-LB-84 (fence fix as D6, stale `runtime_info.py` references, recursive-CTE hypothesis obsolete, LB-49 shipped), PLAN-LB-83 and PLAN-LB-73 (line references moved), PLAN-LB-85 D4 (consumer-visible field set line)
- [x] new specs: PLAN-LB-86 (measurement truth), PLAN-LB-87 (recording call sites)
- [x] resume anchor and `queue-view.md` regenerated

## Follow-Ups

- **C1 to C6, C9, the stale docs, the missing fixture-database enrich-to-generate test, the `(inline)` mislabel and the `total_tokens` population** → **PLAN-LB-86** (high).
- **Lessons `-003` (gate-route build rows have no duration), `-004` (callers do not forward `--step-id` and hard-code zero spend), the retrospective-before-record-metrics ordering and the `pwx` resolution** → **PLAN-LB-87** (medium).
- **Defect L1, the facts fence** → PLAN-LB-84 D6 (parser accepts the CommonMark spacing; `emit-landing.md` stops describing the fence with padded backticks).
- **Lesson `-005`** → PLAN-LB-85 D4 (the plan-spec template asks a spec that serves an unchanged consumer to enumerate its consumer-visible field set). The lesson's figures are partly wrong (see Metrics); the pattern holds, and this plan's own spec is an instance: D3 was prose against an existing consumer.
- **Lesson `-001`** → folded into the red-CI Open Defect (owned by PLAN-LB-44; no surface added). **Lesson `-002`** → promoted to the lessons corpus.
