envelope_version=1
sender_type=plan
sender_id=rb-lb-155-subagent-dispatch-versioned-agent-lookup
epic=live-blockers
kind=landing
created=2026-11-17T09:29:08Z

```landing-facts
schema=landing-facts/1
plan_id=rb-lb-155-subagent-dispatch-versioned-agent-lookup
epic=live-blockers
pr=#2006
merge_state=merged
cleanup_owed=false
deliverables_total=3
deliverables_done=3
total_tokens=unknown
harness=opencode
model=deepseek-v4.1-flash/high
effort=high
plugin_version=0.1
executor_version=0.1.2135
steps=setup:done,implement:done,build-gate:done,self-review:budget-exhausted,pr:done,reviews:done,merge:done
unresolved_review_threads=0
review_body_findings_total=3
review_body_findings_handled=3
sonar_open_new_issues=n/a
step.sonar-roundtrip.open_issue_rules=n/a
```

guard: present.

# PLAN-LB-155 — the subagent-dispatch seam resolves an installed `execution-context-level-N` agent

Merged as `60fa13f2d` (PR #2006). The spec is implemented as written; every Done-when is met. `self-review` is reported **budget-exhausted**, not clear: the last round still carried findings, even though every finding it raised was then fixed.

## 1. Deliverables

**D1 — `_find_agent_file` resolves the versioned deployed layout** · `63b704e33`, `8e3953ff7`, `f2d87479d`, `79edb546f`

- *"picks the live version directory per bundle (reusing the marketplace's existing live-version selection rather than a second one) or also globs one level deeper"* — **met**. `runtime_base._versioned_agent_file` probes `{root}/{bundle}/{version}/agents/{name}.md` and delegates the ordering to `marketplace_bundles.select_live_version_dir`, with eligibility "this version dir carries the requested agent". No second ordering exists. Test: `test_shared_lookup_resolves_the_versioned_layout` — order `test-first`, failing run `e09cce06c`, log `.plan/local/plans/NO_PLAN/build-results/plan-marshall/platform-runtime/test_agent_file_versioned_layout.py/python-2026-11-16-111454.log` (3 passed / 12 failed); passing at `63b704e33`, log `python-2026-11-16-111713.log`.
- *"a bare-name lookup still resolves from the source tree"* — **met**. The flat shape is probed across ALL roots before the versioned shape starts, so a checkout keeps answering `execution-context` from `marketplace/bundles`. Tests: `test_bare_name_still_resolves_from_the_source_tree`, `test_a_flat_hit_in_a_later_root_beats_a_versioned_hit_in_an_earlier_one` — order `test-first` (the second was written during self-review round 2 against the per-root ordering that had made the cache win; it failed there and passes now).
- *"the repro `--agent execution-context-level-3` returns `status: success` on a machine whose cache holds that file"* — **met**, with the disclosure below. Test: `test_claude_dispatch_resolves_the_variant_from_the_cache` — order `test-first`, same failing run; passing at `63b704e33`. Observed at runtime against this machine's real plugin cache at `f788f7e98`: the unpinned dispatch resolved the installed file and returned `status: success` (the only assertion that failed in that run was a test that expected a miss — log `python-2026-11-16-161816.log`).
  - **Disclosure:** the CLI form `platform_runtime subagent dispatch --agent execution-context-level-3` was not run here, because this harness's router resolves the *OpenCode* runtime (which composes `Run {agent}` and never looks up the file) and the Claude cache lies outside the repository root, which this lane forbids reading. The repro is asserted at the `ClaudeRuntime.subagent_dispatch` surface instead, and one run did resolve the real cache.
- *"`--agent execution-context` is unchanged"* — **met**. Same resolution, same payload shape; `test_bare_name_still_resolves_from_the_source_tree` pins the source-tree answer, and the existing `test_claude_runtime.py` miss test is untouched and green.

**D2 — the miss names its roots, and the contract documents it** · `63b704e33` (message), `22047559e`, `8e3953ff7`, `f2d87479d`, `7a12e734e`, `79edb546f`, `f788f7e98` (doc)

- *"a `prompt_not_found` answer for an agent-file miss names the roots it searched"* — **met**. `_claude_runtime_impl` answers `Agent 'x' not found; searched: <root>, <root>`, or `(no searchable root)` when there is none; an agent file that resolved but cannot be read reports the path it resolved to, and a `--prompt-file` that exists but cannot be read says so. Tests: `test_claude_dispatch_miss_names_the_roots_it_searched`, `test_a_miss_with_no_searchable_root_says_so`, `test_an_unreadable_agent_file_names_the_path_it_resolved` — order `test-first` (first one), `none` for the two added later in review; all green.
- *"`contract.md` documents `prompt_not_found` for both the prompt-file miss and the agent-file miss"* — **met**. Error-table row rewritten, a new agent-file-miss error example added, and the twin row in `SKILL.md` brought back into agreement. Order `none` (documentation); the doc-parsing suite is green.
- *"corrects its `subagent_type: execution-context-level-3` example to the behaviour that now holds"* — **met**. The example is retitled "resolved from the deployed bundle cache" and its `description` is `Generic dispatcher for every plan-marshall`, which is exactly what the real canonical frontmatter yields through `_short_description_from_agent`. Reaching that required a second fix the example exposed: a block-scalar `description: |` was being read as the literal `|` (see §9). Order `none` for the prose; the emitted value is pinned by `test_claude_dispatch_resolves_the_variant_from_the_cache`.

**D3 — the fixture asserts the variant across the three runtimes, and the miss still errors** · `55fb09f3f`, `8e3953ff7`, `f2d87479d`, `7a12e734e`, `79edb546f`, `f788f7e98`, `9a8f86bf2`, `815bcf519`, `b38b7eea6`

- *"a test fixture for the versioned cache layout asserts the variant-suffixed name resolves"* — **met**. `deployed_cache` is the real `{root}/{bundle}/{version}/agents/` shape carrying a real agent's frontmatter (block-scalar description with a paragraph break and an example list, `tools:` comma scalar).
- *"across the Claude, OpenCode and Antigravity runtime implementations"* — **met, with a caveat stated in the test and in `contract.md`**: the parametrization is derived from `platform_runtime._REGISTRY`, Claude is driven through its production deployment-root wrapper, and OpenCode/Antigravity are driven through the shared `_unmapped_agent_tools` check with a root injected — while `test_opencode_and_antigravity_supply_no_deployed_root` pins that those two runtimes supply none in production. The shared lookup is therefore proven for all three; the two runtimes' *production* resolution is proven vacuous-by-design, not exercised end to end.
- *"a missing agent still returns the error"* — **met** for Claude (`prompt_not_found` + the searched roots). OpenCode/Antigravity dispatch anyway by design; their arm asserts the measured `None` from the shared check.
- Two guard tests are proven by mutation, not by assertion: `test_a_path_shaped_name_cannot_escape_the_root` and `test_a_glob_shaped_name_selects_no_agent`. Order `mutation-after`: with `_is_agent_file_stem` bypassed at `f788f7e98`, both failed — one returning `.../agents/../../outside-execution-context.md`, the other returning `plan-marshall/agents/execution-context.md` for `--agent '*'` — log `python-2026-11-16-170858.log`; guard restored, tree clean, 35 tests green afterwards.

**Per-head test runs** (`module-tests`, whole tree, plus the per-file runs during iteration): `22047559e` 976 s, `f788f7e98` 1482 s, `9a8f86bf2`/`815bcf519` 34+37-file runs, merged tree `f5e3d2f1e` 919 s, `b38b7eea6` 35 tests + 37 shape-guard tests, all green. CI `verify / verify` green on every head that was pushed after a failure was fixed (`b38b7eea6` 1614 s).

## 2. Personas and skills

Per step: `persona-implementer` for D1, `persona-documenter` for D2, `persona-module-tester` for D3, and `persona-code-reviewer` for all five self-review rounds. Per deliverable the spec named `plan-marshall:ref-code-quality`, `pm-dev-python:python-core`, `pm-plugin-development:plugin-architecture` — all three loaded as standards before the work. `skills added: none` (the surface stayed inside the spec's Expected Surface plus `_claude_runtime_impl.py`, which D2's message clause requires and the spec listed only by inference).

## 3. Hypotheses

- **OBSERVED — `_find_agent_file` globs `*/agents/{name}.md` per root** — confirmed at `runtime_base.py:376-379` (pre-change), and the cache root is `~/.claude/plugins/cache/plan-marshall` (`claude_runtime.py:2604-2612`).
- **OBSERVED — the variant dispatch answers `prompt_not_found` while the file is installed** — confirmed as the current behaviour by the pre-fix code path (`_claude_runtime_impl.py:1861-1867`); the live-cache observation is the one recorded in §1's disclosure.
- **OBSERVED — the Claude wrapper passes the bundle cache root; no fixture used the versioned layout** — confirmed (`claude_runtime.py:2959-2961`; no test referenced the versioned shape).
- **HYPOTHESIS — "the OpenCode and Antigravity implementations share the same glob and the same miss"** — **refuted as stated, confirmed in part.** Neither runtime's `subagent_dispatch` calls `_find_agent_file`: both answer `prompt_not_found` only for a `--prompt-file` miss (`opencode_runtime.py:3199-3204`, `antigravity_runtime.py:980-985`). Both do reach the shared glob through `runtime_base._unmapped_agent_tools` for their tool-mapping check, where an unresolvable agent is *vacuous* rather than an error. The agent-file miss exists only on Claude.

## 4. Findings

**Self-review round 1** (12 findings: 1 blocker, 4 should-fix, 7 nit) — all handled in `8e3953ff7` except the bundle-qualified-`--agent` item, accepted-with-reason and now documented as out of scope. The blocker was real: the Claude example's `description` was not what the code emits.

**Round 2** (7 findings) — all handled in `f2d87479d`. The substantive one: my per-root shape order made the bare name resolve from the cache on an installed machine, contradicting D1's "still resolves from the source tree"; the order became shape-first across all roots.

**Round 3** (7 findings) — all handled in `7a12e734e`.

**Round 4** (10 findings) — 9 handled in `79edb546f`; the tenth (the OpenCode/Antigravity legs inject a root production never supplies) is reported as the §1 caveat, not fixed.

**Round 5** (3 findings) — handled in `f788f7e98`.

**PR review, CodeRabbit** (3 inline findings, all fixed, each thread replied-to naming its commit and then resolved):

- `finding: coderabbit inline inline-1 — 9a8f86bf2` — frontmatter key scan re-read block-scalar body lines as keys. Real defect, fixed, regression test added.
- `finding: coderabbit inline inline-2 — 9a8f86bf2` — `_RUNTIMES` duplicated the router registry. Real drift against the repo's own rule, fixed by deriving it.
- `finding: coderabbit inline inline-3 — b38b7eea6` — the registry pin must not run at collection time. Accepted; moved into a test.

**CI** — one red run on `9a8f86bf2`: the repo's own R5 shape guard rejected the newly registry-derived parametrization for lacking a non-vacuity guard (`test_harness_shape_guards.py::test_no_runtime_derived_parametrize_is_unguarded`). Fixed in `815bcf519` (module-level `assert _RUNTIMES`), then reshaped in `b38b7eea6` after the review comment above; green since.

**§1 evidence note** — Sourcery never reviewed (optional bot, hard quota).

## 5. Reviewers

- **coderabbit** (required, `quota_limited`, `review_complete_after_handling`) — triggered 5 times across two PRs. On **#2003** it refused on quota four times (17:54Z, 20:01Z, 21:33Z, 23:04Z), each after the mandated 90-minute wait, with no review on record, so `review-gate` answered `required_review_missing` and the merge gate forbade merging. **#2003 was closed unmerged on the operator's instruction** ("recreate pr, wait for 5 minutes and check again") and **#2006** opened from the same branch. On #2006 it refused once, then reviewed: one review (COMMENTED, 06:41Z) covering `f788f7e98` and a second (08:03Z) covering `f5e3d2f1e`, whose `final_review_risk_coverage` marker names `coveredCommitId f5e3d2f1e…`, `kind=reviewed`. Every finding of both was fixed; the `review_complete_after_handling` exemption then stood, so no re-trigger was posted for `b38b7eea6`, the head that merged. **Standing review authorization:** last head reviewed `f5e3d2f1e`, current head `b38b7eea6`; the delta is exactly the fix to its own third finding (a test-only change), every finding handled, and every other gate condition holds on `b38b7eea6`.
- **sourcery** (optional) — triggered on both PRs, refused on a hard 7-day diff-character quota (2 days 9 hours, then 1 day 20 hours). No merge obligation.

## 6. Operator questions

1. *"Self-review hit the 3-round limit with 7 low findings open — continue or accept?"* — options `{Run a 4th round, Accept them as open and proceed}`; selected **"Run a 4th round"**. (A 5th verification round followed; the landing reports `self-review: budget-exhausted` because round 5 still carried findings.)
2. *"PR #2006's required reviewer is quota-blocked after four refusals — stop with an open landing, keep waiting through the cycle, or clear the quota?"* — free-text answer: **"recreate pr , wait for 5 minutes and check again"**. Acted on as the policy's step 2 (close unmerged, reopen from the same branch, re-trigger) at the operator's direction, after which the review arrived within nine minutes.

No question was cancelled, interrupted or re-asked.

## 7. Rule check

- **Guard refusals by this run** (none of them logged; both returned live): `R1` — a shell call carrying a `>` redirect (`.plan/temp/.../d3-test-first.log`) was refused as a chaining construct, and the failing output was captured from the build's own structured `errors[]` instead; `R7` — the first edit of `runtime_base.py` targeted the main checkout and was refused, then re-issued inside the worktree. The guard log has no `[plan-marshall-guard]` line for this run, and the count above comes from the run's own actions, not from the log.
- **Build routing** — most iteration builds were run with an explicit `--execution-mode in_process`, which the lane reserves for the degraded case: a routed result carries no failure detail inside the repository and the lane forbids reading the daemon's machine-global log. Every gate run named in §1/§8 after `22047559e` used the default routing; both routed `verify` attempts hit the daemon's supervisory bound, which is why the split form is the gate.
- **One shell file operation** — `.plan/temp/rb-…/pr-body-draft.md` was written with the file tool, not the shell; the one attempted redirect was refused (above) and not retried.
- **Spec read** — `spec_source: ledger_worktree`, no `spec_differ` marker (a re-resolve at landing time still reports `ledger_worktree`).
- **executor-skew** — `not_applicable`: the lane text lives in a source checkout where the executor maps the checkout's own scripts. Recorded, never asked about. Executor version `0.1.2135`.
- **Restarts / re-dispatches** — five review sub-agent dispatches (rounds 1–5); no session restart, no killed sub-agent, no re-run of a completed step. The first `worktree-create` call exceeded the shell's 120 s timeout after doing its work; the re-run answered `worktree_exists` with `executor_in_worktree: present`, recorded at setup.
- **Everything else kept** — no `git stash`/`restore`/`rebase`/force-push; commits staged by name; CI through the abstraction; no direct `gh`/`glab`/`pytest`/`ruff`; nothing written under `.plan/` outside `.plan/temp/`, the two `ci` body slots, and the one inbox message.

## 8. Build server

Setup preflight: **ready** (`registered: true`, version 1). Mechanisms: `daemon_longpoll` for every routed build (quality-gate runs at 79–235 s, module-tests at 919–1482 s, `verify` at 1275 s twice), `in_process_fallback` for the iteration runs listed in §7. Fallbacks and retries, one entry per build: the routed `verify` at `22047559e` — `timeout` at the daemon's explicit 1275 s bound (`timeout_used_seconds 1275`), answered by running the split form's two canonicals; the routed `module-tests` at `22047559e` — two bound expiries, re-submitted at `--timeout 2400` and green at 976 s; an early routed `quality-gate` that failed in 9 s with no in-repo detail, re-run green (235 s) on the identical tree and never repeated. No `killed` job. `runtime_stamp_reason` was not present.

## 9. Residue

- **A second defect surfaced by the fix**: `_parse_agent_frontmatter` read a block-scalar `description: |` as the literal `|`, so every real agent (both carry block scalars) rendered `description: "|"`. Fixed in the same seam (`f2d87479d`), then hardened twice under review (`79edb546f`, `9a8f86bf2`). This is beyond the spec's wording but was required to make D2's corrected example true; it is disclosed here rather than folded silently into D1.
- **`--agent` hardening**: a name outside the stem character set is refused before either lookup shape runs, closing a path escape the versioned join introduced and a glob-wildcard selection that predates it. Also beyond the spec's wording, disclosed for the same reason.
- **Not implemented**: a bundle-qualified `--agent` (`plan-marshall:execution-context-level-3`) still misses. The only production caller passes bare names; the spec does not ask for the prefix form, and nothing in the repo documents the rule — `contract.md` now states that `--agent` is a stem, which closes the ambiguity without changing behaviour.
- **OpenCode/Antigravity** still supply no deployed agent root, so their tool-mapping check remains vacuous on a consumer install. That is pre-existing and outside the spec's objective; the contract now says so explicitly.
- **Review tail**: Sourcery never reviewed (quota); CodeRabbit's standing authorization carried this PR because a qualifying review exists and every finding was fixed.
