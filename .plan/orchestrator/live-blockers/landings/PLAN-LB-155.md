# Landing Analysis: PLAN-LB-155 — The subagent-dispatch seam resolves an installed `execution-context-level-N` agent

epic: live-blockers
workstream: WS-04
pr: #2006 (https://github.com/cuioss/plan-marshall/pull/2006)

> Landing record for one shipped plan. Lives at `landings/PLAN-LB-155.md`. Written by the
> `analyze` verb after verifying claims against ground truth (actual code, artifacts,
> PR state) — a pasted claim is a lead, never a fact. See
> `persona-plan-orchestrator/standards/orchestration-model.md` for the analysis and
> reconciliation contract.

Runbook lane, sender `rb-lb-155-subagent-dispatch-versioned-agent-lookup`, harness `opencode`, model `deepseek-v4.1-flash/high`.
Squash merge `60fa13f2d20abf908471668cfb23d1218cf6059e` through the merge queue. Message
`rb-lb-155-subagent-dispatch-versioned-agent-lookup-001.md` carries `total_tokens=unknown` (out of scope under the standing ruling) and
`self-review:budget-exhausted` after five rounds (see Follow-Ups). The first PR, #2003, was closed unmerged on the operator's instruction after four
CodeRabbit quota refusals; #2006 was opened from the same branch.

## Deliverable Fidelity vs Spec

Corroborated against `origin/main` at the merge commit: the diff stat (7 files, 673 insertions, 34 deletions), a read of the merged
`runtime_base.py`, `claude_runtime.py`, `_claude_runtime_impl.py` and `marketplace_bundles.py` diffs and of the `contract.md` and `SKILL.md` diffs, and
the PR state (`merged`, merge commit equal to the one above).

| Deliverable (spec) | Verdict | Evidence |
|--------------------|---------|----------|
| D1 `_find_agent_file` resolves the versioned deployed layout, a bare name still resolves from the source tree, `--agent execution-context-level-3` succeeds where the cache holds the file | shipped-as-specified | `runtime_base._versioned_agent_file` probes `{root}/{bundle}/{version}/agents/{name}.md` and takes the version directory from `marketplace_bundles.select_live_version_dir` with the eligibility "this version dir carries the requested agent" (re-read), so no second ordering exists. `_find_agent_file` runs the FLAT shape across every root before the VERSIONED shape starts, which keeps a bare name on the source tree in a checkout. The CLI form was not run (see L3-6) |
| D1 `--agent execution-context` unchanged | shipped-as-specified | the flat pass is untouched in shape (`root.glob('*/agents/{name}.md')`), run first across all roots; the only added pre-condition is the stem guard (see the scope additions below) |
| D2 a miss names the roots, `contract.md` documents both `prompt_not_found` misses and corrects the example | shipped-as-specified (code and docs re-read) | `_claude_runtime_impl.py` answers `Agent {agent!r} not found; searched: {roots or "(no searchable root)"}`, names the resolved path when an agent file cannot be read, and says so when a `--prompt-file` exists but cannot be read; `claude_runtime._agent_search_roots` publishes the probed roots; the `contract.md` error-table row, the arguments paragraph, a new "Agent-file resolution" paragraph, the retitled Claude example and a new agent-file-miss example are in the diff; the twin row in `SKILL.md` agrees |
| D3 a fixture for the versioned layout asserts the variant resolves across the three runtimes and a missing agent errors | shipped-as-specified (lane-reported, with a stated caveat) | `test_agent_file_versioned_layout.py` (463 lines) is in the stat and was not read here. The lane states that OpenCode and Antigravity are driven through the shared `_unmapped_agent_tools` check with an injected root while a pin test records that production supplies none for those two |

The spec's HYPOTHESIS (OpenCode and Antigravity share the glob and the miss) was refuted in part by the lane: neither runtime's `subagent_dispatch` calls
`_find_agent_file`; both reach it only through `_unmapped_agent_tools`, where an unresolvable agent is vacuous. The merged `_unmapped_agent_tools` docstring
states the same ("the callers ... supply no deployed bundle cache"), which is consistent with the lane's reading.

**Scope additions beyond the spec's wording**, all disclosed by the lane and all re-read in the diff:

- `_claude_runtime_impl.py` (11 lines): the miss message and the two read-error messages. The spec listed `claude_runtime.py` only by inference.
- `runtime_base._parse_agent_frontmatter` now reads a block-scalar `description: |` as its text (new `_is_block_scalar_marker`, `_block_scalar_value`) and skips indented lines when scanning keys. Required to make the corrected example true: every real agent file carries a block-scalar description, and the old parser rendered it as `|`.
- `runtime_base._is_agent_file_stem` / `_AGENT_STEM_CHARS`: `--agent` outside the stem character set resolves to nothing. It closes a path escape the versioned join would have introduced and a glob-wildcard selection that predates it.
- `script-shared/scripts/marketplace_bundles.py` (8 lines): a docstring-only change, stating that two call sites with different eligibility predicates can pick different version directories.

## Three-Layer Analysis

Depth: **orchestrator re-read only, no leaf dispatched** — the change is one lookup function with its helpers, a parser fix and a contract section, read in the
merged diff. By reading: no build, no test run, no run of the dispatch verb.

### Layer 1 — Specified

| Finding | Claim | Verdict | Polarity | Evidence |
|---------|-------|---------|----------|----------|
| L1-1 | OBSERVED: `_find_agent_file` globs `*/agents/{name}.md` per root | checked | confirms | the pre-change shape is visible as the unchanged first loop of the merged function |
| L1-2 | OBSERVED: the variant dispatch answered `prompt_not_found` while the file is installed | checked | confirms | the new versioned pass is exactly the missing probe; the lane records one run against this machine's real cache that resolved |
| L1-3 | OBSERVED: the only documented caller is `execution.md` | checked | confirms | `plan-marshall/workflow/execution.md` lines 178-184 pass `--agent {target}`, a bare stem |
| L1-4 | HYPOTHESIS: OpenCode and Antigravity share the same miss | checked | refutes (in part) | see above; the agent-file miss exists on Claude only |

**Layer 1 verdict:** no refuting finding against a claim the plan relied on; the one refuted hypothesis was reported and handled by scoping the miss message to Claude.

### Layer 2 — Implemented

| Deliverable | Code trace | Test that can fail | Unexplained file | Verdict |
|-------------|------------|--------------------|------------------|---------|
| D1 | `runtime_base.py` `_agent_search_roots`, `_versioned_agent_file`, `_find_agent_file` | `test-first` run named by the lane: 12 of 15 failed at the base commit (`e09cce06c`) | none | checked |
| D2 | `_claude_runtime_impl.py` miss paths, `claude_runtime._agent_search_roots`, `contract.md`, `SKILL.md` | the platform-runtime doc-parsing suite (green per the lane) | none | checked |
| D3 | `test_agent_file_versioned_layout.py` | two guard tests proven by `mutation-after` (guard bypassed, both failed, log named) | none | lane-reported |
| scope addition | `_parse_agent_frontmatter`, `_is_agent_file_stem` | parser section over every block-scalar header form; the two guard tests | `marketplace_bundles.py` docstring | checked |

### Layer 3 — Correct

| Defect | File:line | Triggering input | Effect | Severity |
|--------|-----------|------------------|--------|----------|
| L3-1 | `runtime_base._versioned_agent_file`; `marketplace_bundles.select_live_version_dir` | an agent shipped by an older version directory but not by the newest one | the agent resolves from the older directory while the running scripts come from the newer one. Stated in `contract.md` ("the agent can come from an older directory than the one serving the running scripts") and in the `marketplace_bundles.py` docstring | minor, documented |
| L3-2 | `runtime_base._is_agent_file_stem`; `_claude_runtime_impl.py` miss | `--agent plan-marshall:execution-context-level-3`, the `{bundle}:{name}` notation of a `Task:` call | the colon is outside the stem character set, the lookup returns `None`, and the answer reads `Agent '...' not found; searched: <roots>` — it reads as a wrong name or an unsearched root, while the cause is the notation. `contract.md` states that `--agent` is a stem, so the behaviour is documented, the message is not. The only production caller passes a bare stem | minor; staged as PLAN-LB-159 D3 |
| L3-3 | `runtime_base._find_agent_file`, `_versioned_agent_file` | one agent name carried by two bundles under one root | the flat pass answers in glob order, the versioned pass in sorted bundle order. The versioned docstring names the difference ("a deterministic tie-break, unlike the flat pass's glob order"). No two bundles carry the same agent stem today | info |
| L3-4 | `runtime_base._unmapped_agent_tools`; `opencode_runtime.py`, `antigravity_runtime.py` | an OpenCode or Antigravity dispatch on an install that has no source tree | both supply no deployed agent root, so the tool-mapping check (verify-first clause 2) is vacuous and the dispatch proceeds. Pre-existing, stated by the plan and now in `contract.md`; the lane's tests prove the shared lookup for those two runtimes, not their production resolution | minor, pre-existing, not staged |
| L3-5 | `runtime_base._unmapped_agent_tools` | an agent file that resolves but cannot be read, on OpenCode or Antigravity | it parses as an agent declaring no tools, so the check answers a measured empty `[]` and the dispatch proceeds. Stated in the docstring and the contract | info |
| L3-6 | the harness install, not the repository | the merged source is not the installed cache | the dispatch verb the executor maps on this machine still runs the installed copy until `/apply-changes` (or `/sync-harnesses`) refreshes it. The lane did not run the CLI form (its harness resolves the OpenCode runtime and the Claude cache is outside its read boundary) and asserted the repro at `ClaudeRuntime.subagent_dispatch`; one run did resolve this machine's real cache. The end-to-end repro on this machine is therefore the operator's first check after the sync | owed to the operator |
| L3-7 | the last commits | `b38b7eea6` merged after the last CodeRabbit review (`f5e3d2f1e`) | the standing review authorization carried the merge. Re-read: the delta `f5e3d2f1e..b38b7eea6` is one test file, 10 insertions and 7 deletions, and the lane states it is the fix to CodeRabbit's own third finding. Holds | info, correct |

**Layer 3 not shown by reading:** `quality-gate`, `module-tests` and `verify` green at the merged head (CI `verify / verify` 1614 s green on `b38b7eea6` per the lane), the
mutation runs, the 463-line test file, and the dispatch verb against this machine's installed cache after a sync. No run was made here.

**Layer 3 verdict:** no blocker, no major. L3-1, L3-4 and L3-5 are documented decisions; L3-2 is staged; L3-6 is the operator's check.

### Conformance to the Project's Own Rules

| Rule source | Rule | Verdict | Evidence |
|-------------|------|---------|----------|
| CLAUDE.md Documentation Standards | Current state only | conforms | the new `contract.md` paragraphs state the present resolution; no history clause |
| `pm-dev-python:python-core` | explicit exception handling | conforms | `_versioned_agent_file` catches `OSError` on the directory read and returns a miss; the read errors in `_claude_runtime_impl.py` bind the exception and put it in the message |
| CLAUDE.md Workflow Discipline | shell constructs | deviates (self-reported) | one `>` redirect was refused by the guard (R1) and not retried; one edit targeted the main checkout and was refused (R7). Neither was logged by the guard |
| Runbook-lane build routing | `--execution-mode in_process` is reserved for the degraded case | deviates (self-reported) | most iteration builds ran `in_process` because a routed result carries no failure detail inside the repository; every gate run after `22047559e` used default routing |
| CLAUDE.md Build Commands | gates green | not_shown_by_reading | only a run shows it |

## Metrics and Anomalies

- Tokens: `unknown` (out of scope under the standing ruling).
- Anomalies: CodeRabbit refused on quota four times on #2003, each after the mandated 90-minute wait, with no review on record; the merge gate answered
  `required_review_missing`; #2003 was closed unmerged on the operator's instruction and #2006 opened from the same branch, where one refusal was followed by a review within
  nine minutes. Sourcery refused on its 7-day quota twice. Two routed `verify` runs hit the daemon's 1275 s bound (split form used); one routed `module-tests` run needed
  `--timeout 2400`; an early routed `quality-gate` failed in 9 s with no in-repo detail and passed on the identical tree. 5 self-review rounds.

## Routing and Merge Behavior

- Review: CodeRabbit (required, quota-limited, `review_complete_after_handling`) reviewed `f788f7e98` and `f5e3d2f1e`: 3 body findings, all fixed with replies. The merge ran on the standing authorization (L3-7).
  Sourcery (optional) never reviewed. Not independently re-run here.
- CI/merge: `verify / verify` green on every pushed head after the one red run on `9a8f86bf2` (the R5 shape guard, fixed in `815bcf519`); queue merge.
- Sonar: `n/a` (not configured).
- Parallelization: ran beside PLAN-LB-154 and -157 on disjoint surfaces; no collision reported.

## Reconciliation Actions

- [x] row `status` → `shipped` — `orchestrator queue --transition PLAN-LB-155 --status shipped`
- [x] row `pr` stamped — `2006`
- [x] row `landing` stamped — `landings/PLAN-LB-155.md`
- [x] row `plan_marshall_plan_id` stamped — `rb-lb-155-subagent-dispatch-versioned-agent-lookup` (from the sender)
- [x] `epic.md` narrative: one Decision bullet
- [x] inbox message archived; decision logged
- [x] resume anchor updated; `queue-view.md` regenerated
- Owed to the operator: `/apply-changes` so the installed dispatch verb carries the fix (L3-6); the end-to-end repro (`platform_runtime subagent dispatch --agent execution-context-level-3`) is the check.

## Follow-Ups

- **L3-2 (bundle-qualified `--agent` miss)** — staged as PLAN-LB-159 D3 (diagnosis only, no second lookup form).
- **L3-4 (OpenCode and Antigravity supply no deployed agent root)** — recorded here, no plan. Pre-existing and documented. Trigger: an OpenCode or Antigravity consumer install whose dispatch proceeds with a tool the target cannot map.
- **L3-1, L3-3, L3-5** — documented decisions; no plan.
- **Self-review `budget-exhausted`** — round 5's three findings were fixed in `f788f7e98` and CodeRabbit then reviewed the head that followed; nothing further owed.
- **Closed PR #2003** — closed by the operator, not by the lane; nothing to reconcile.
