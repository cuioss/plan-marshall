# Landing Analysis: PLAN-LB-134 — the OpenCode permission writer keeps the effect it reports and reports every failed write

epic: live-blockers
workstream: WS-04
pr: #1954 (merge commit `b09bf3197118f7fc5efcfa2c49338a1b089d01ee`, one parent `27f4e4b96`)

> Landing record for one shipped plan. Written by the `analyze` verb after verifying claims against ground truth (actual code, artifacts, PR state) — a pasted claim is a lead, never a fact.

## Deliverable Fidelity vs Spec

Corroborated against git: the merge is a merge-queue squash with one parent (`27f4e4b96`, the PLAN-LB-138 squash, read with git before the leaf prompt named it); twelve changed paths, read with `git diff --name-only`. The facts block (`pr=#1954`, `merge_state=merged`, `deliverables 4/4`) agrees with git. **Two messages exist for this plan:** message 001 was read on 2026-11-10 as a mid-flight report (`merge_state=open`, PR open, CodeRabbit refused on quota) and archived; the lane then could not amend it (`inbox amend` refuses an archived message), so message 002 was filed as a fresh landing that says "everything else in the archived landing still stands". `total_tokens=unknown` is an unobserved fact, not a defect. `self-review:budget-exhausted` is a lane state, with one operator-authorised fourth round.

| Deliverable (spec) | Verdict | Evidence |
|--------------------|---------|----------|
| D1 — the rule writer keeps the effect it reports and knows OpenCode 2's tool name | shipped; two edges the lane's "same defect class" claim did not close | `_upsert_permission_rule` returns `PermissionRuleWrite` and refuses before any save (`opencode_runtime.py:671-733`, re-read); the scan covers only rules a move crosses (leaf `:696, :715`); `to_opencode_grant('deny(shell)')` is `('bash','*','deny')` (leaf `:336-339`); `subagent` maps to `task` through `_permission_map_key` (leaf `:461-470`); the map `*` row goes first through `_set_map_catch_all` in the four writers (leaf `:473-484`). **The claim "a removal matches the effect" is false for the runtime `permission fix remove` OpenCode 1 map branch** (re-read at `:2064-2086`: `cat, pat, _ = to_opencode_grant(...)` discards the effect and deletes by pattern alone; the new map-removal test goes through `cmd_remove` only, leaf). |
| D2 — a failed write and an unreadable input are reported | shipped-as-specified | the loader catches `UnicodeDecodeError` (leaf `:2574`); writers report load errors and failed saves; `installed_opencode_version` returns `None` on a non-zero exit (leaf `:775-780`); `cmd_add` and `cmd_remove` have list and map branches (leaf). Test gaps: no unparsable-file test for `cmd_add`, `cmd_remove` or `cmd_apply_fixes`; no setup test for a failed save. |
| D3 — the two deny readers agree | shipped-as-specified | `_deny_rules` delegates to `_deny_rules_from_config` (leaf `:808-820, :904-952`); the lane's answered finding about the audit and health source-set difference is sound (the unification covers shapes, not files; `contract.md` discloses it; leaf). |
| D4 — the emitted catch-alls cannot override a global deny | shipped, and **broader than the spec** | the spec required no `{shell,*,allow}`; the emitter now emits NO permission rule for any tool (diff re-read: `transform_agent_frontmatter` only validates `tools:` against `mapping['tool_permissions']`, the `permissions:` block is gone). See Layer 3 L3-1. |

**Surface drift, and the lane understates it.** Message 001 named `test_opencode2_shape.py` as the only path outside the Expected Surface. The re-read path list shows four: `platform-runtime/SKILL.md`, `platform-runtime/standards/contract.md`, `test_opencode2_shape.py` and `test_variant_emitter.py`. Three Expected Surface paths were not changed (`permission_common.py`, `_permission_fix_fixtures.py`, `test_opencode_root_config.py`); the leaf explains the first two (the loader already delegates; the fixture sufficed) and the third is a D4 hypothesis. The three D4 test names in message 001's evidence row (`test_known_tools_map_to_permissions`, `test_emitted_agent_permissions_evaluate_like_the_source_tool_grants`, `test_target_absent_tool_alongside_mapped_tools_emits_only_mapped`) no longer exist in the merged tree (leaf), and the `mutation-after` run cited (`7adc28b93`) predates the emitter rewrite and the later scan changes, so message 002's "everything else still stands" does not hold for D4.

## Three-Layer Analysis

One read-only leaf (`execution-context-level-3`) read the landing with the lane's seven claims passed one by one and an explicit hunt on the emitter claim; the orchestrator re-read the points marked re-read. **By reading, no build, no test run, no write. No repro was executed; one input was traced by hand (L3-2).**

- **Dispatch:** one read-only leaf per landing — reason: reading merged code is the depth the dispatch rule exists for.
- **Verdict:** no blocker. The leaf graded five majors; the orchestrator regraded them below (three stay major, two are minor).
- **Leaf process note:** the leaf used one read-only `git grep` against the instruction and disclosed it; it read nothing the findings rest on. It also confirmed that the runtime, `permission_fix.py` and emitter files are byte-identical between the merge commit and the checkout HEAD.

Re-read: `frontmatter.py` (the full diff `27f4e4b96..b09bf3197`), `opencode_runtime.py` `:517-556, :615-645, :671-733, :1736-1750, :2064-2090, :2170-2200, :2362-2384`. **Not re-read** (unverified leads): the writer call sites the leaf lists by line, `_deny_rules_from_config`, `installed_opencode_version`, the contract and adoc tables, the OpenCode 2 base-policy fact (it needs the installed binary), every build log, the mutation runs, the PR body and the review history, and the spec's counter-example (L3-2).

### Layer 1 — Specified

| Finding | Claim | Verdict | Polarity | Evidence (file:line) |
|---------|-------|---------|----------|----------------------|
| L1-1 | D1's "a removal matches the effect as part of the rule identity" holds on the list branch and in `cmd_remove`, not in the runtime OpenCode 1 map removal. | checked (re-read) | refutes (partly) | `opencode_runtime.py:2064-2086` |
| L1-2 | D4 asked for no shell catch-all; the lane removed every agent grant, which is a larger change than the spec named and removes the only trace of a tool list from the emitted agent. | checked (re-read) | exceeds the spec | `marketplace/targets/opencode/frontmatter.py` diff |
| L1-3 | The lane's refusal to take a CodeRabbit finding ("`ensure` returning a conflict for a rule a broader later row already shadows") rests on the spec's D1 Done-when requiring that branch. The leaf reads the Done-when as requiring a conflict only when a move would CROSS a more specific later rule, and says the spec's `ask` counter-example is already `ask` at the base (the later `git *` ask wins), so the spec fixture can only pass through the shadow branch. | checked (leaf), the spec fixture NOT re-read | refutes the lane's reading | `opencode_runtime.py:721-732` (re-read), spec D1 (not re-read) |

**Layer 1 verdict:** findings — 3 (1 major, 1 minor, 1 watch)

### Layer 2 — Implemented

| Deliverable | Code trace | Test that can fail | Unexplained file / unborne claim | Verdict |
|-------------|------------|--------------------|---------------------------------|---------|
| D1 | `opencode_runtime.py:671-733` | crossing test through `runtime.permission_fix` asserts status, error code and unchanged bytes (leaf); the `ask` parameter passes through the SHADOW branch, not the crossing branch (leaf) | none | checked |
| D2 | writers and loader (leaf) | real functions; failed-save tests monkeypatch `permission_save_settings`, which the spec prescribes | none | checked, gaps named |
| D3 | `_deny_rules` (leaf) | real functions | none | checked |
| D4 | `frontmatter.py` | **none**: the old assertion that a tool the source did not grant must not evaluate to allow was deleted; the rewritten tests assert only the absence of rules | named D4 tests gone | not shown |

- **L2-1 (minor):** the surface drift is understated (above), and the evidence rows cite tests that no longer exist and a mutation run that predates the final code.
- **L2-2 (minor):** "review-gate 8/8 handled" agrees with the verb's total (see Routing); the findings list in message 002 adds up to nine (six on one head, three on the next), one more than the eight dispositions it states; not shown by reading (review history).

**Layer 2 verdict:** findings — 2 (minor)

### Layer 3 — Correct

| Defect | File:line | Triggering input | Effect | Severity |
|--------|-----------|------------------|--------|----------|
| L3-1 | `frontmatter.py` `transform_agent_frontmatter`; `variant_emitter.py` (leaf) | any `tools:`-restricted agent emitted for OpenCode, for example `execution-context-reader` (WebSearch, WebFetch, Read, Grep only) | the emitted agent carries description, mode and model and no tool information. **Before the change it carried only `allow` rows, never a deny or a `tools:` map, so the restriction was already never expressed in the OpenCode artifact.** What changes depends on OpenCode 2's base policy, which the leaf could not read: if every agent starts `{*,*,allow}` (the lane's own recorded evidence), the reader could edit, write and run shell before and after, and the untrusted-content containment of that agent does not exist on the OpenCode target; if no match means `ask` (the repository's documented model, `opencode.adoc` L140), every previously granted read, grep, web and edit becomes `ask`, which stalls headless dispatched subagents. The adoc and SKILL still say "no match means ask" beside the lane's "base policy already decides". No test asserts that a restricted agent stays restricted. The leaf also notes that a deny for an UNGRANTED action cannot override a global deny, so the override hazard that justified dropping the allows does not apply to denies, and the lane did not consider emitting them | **major, unproven by reading** (a pre-existing gap if the base is allow-all; a regression if it is ask) |
| L3-2 | `opencode_runtime.py:721-733` (re-read), protect-path `:2170-2194` (re-read), `_rule_exists` `:623-639` (re-read) | `permission fix protect-path` on a list holding a later broader deny with the same effect as a protected-path vector, for example a `cat *` deny after the shell catch-all; `ensure ask(git push *)` with a later `git *` ask | `_rule_exists` needs the exact resource, so the vector falls through to the upsert; the effect already holds through the later row, no move happens, `hits[-1]` is that later row, and the new refusal returns `permission_conflict` with nothing saved. The remaining vectors (`less`, `more`, `cp`, `base64`) are not installed either; `--dry-run` reported a proposed count before the refusal. Before the change the same input succeeded. The mechanism is read in code; whether the repository's own recommended list contains such a row is the leaf's reading and was not re-read. `ensure` is also non-idempotent: one already-satisfied grant aborts the whole batch | **major** (loud failure of a hardening command, not a silent fail-open) |
| L3-3 | `opencode_runtime.py:541-545` (leaf) | `[*, git * ask, *--force* deny]` then `ensure allow(git push *)` | `_patterns_overlap` tests one pattern as a literal resource of the other, so partially overlapping globs are missed: the result is `[..., git push * allow]` and `git push --force x` changes from deny to allow while the write reports `added: 1` — the D1 defect class with a different glob shape. Traced by the leaf, not executed, not re-read | watch (leaf graded major) |
| L3-4 | `opencode_runtime.py:1742-1749` (re-read) and five more writers (leaf: fix `:1999-2002`, ensure-defaults `:2657-2668`, `permission_fix.py` `cmd_ensure_wildcards` `:1051-1058`, `cmd_ensure_executor` `:1674-1680`, `cmd_ensure`) | `{"permission":{"bash":"deny"}}` (or `"ask"`) and any ordinary write | at the re-read site only a scalar `"allow"` survives; any other scalar becomes `{}` before the grant is even typed, so a conservative scalar deny or ask is lost, and the leaf says OpenCode 1's default is allow (not re-read). The same reset exists for a scalar `permission`. **This is the lane's own residue item 1, pre-existing at the base**; the lane fixed the preservation in `_opencode_add` and protect-path and left these six | **major** (pre-existing; OpenCode 1 map shape) |
| L3-5 | `opencode_runtime.py:2064-2086` (re-read) | `{"permission":{"bash":{"git push *":"deny"}}}` and `permission fix remove ['allow(git push *)']` | the deny is deleted by naming an allow | minor (OpenCode 1 map shape, explicit operator action) |
| L3-6 | `opencode_runtime.py:2372-2375` (re-read) | an OpenCode 1 settings file with `"webfetch": {"evil.com": "deny"}` and `web-apply add` | `perm['webfetch'] = 'allow'` replaces the pattern map and deletes its denies; the lane fixed this class in three sibling writers and missed this fourth | minor (OpenCode 1 shape) |
| L3-7 | `opencode_runtime.py:2573`; `contract.md` (leaf) | a non-object root `[1,2,3]` or `null` | loads as `{}`, so a writer saves a skeleton over it, while `contract.md` documents a non-object root as fail-closed; `permission configure` and `web-apply` return `save_error` where the contract lists `io_error`, and the protect-path load failure returns `invalid_settings` where the contract lists `load_error` | minor (the lane's residue item 3) |
| L3-8 | conflict envelopes (leaf `:1896, :2264, :2340`) | a conflict after `get_settings_path(write=True)` created a skeleton | "no rule was written" is accurate, but the file can exist afterward; `--dry-run` cannot predict a conflict | minor (the lane's residue item 2) |
| L3-9 | `opencode.adoc` L210 and L225; root `opencode.json` (leaf) | — | the adoc matrix still cites per-agent `"*": "ask"` rules overriding global denies, which the same PR's prose calls the hazard, and the repository's root `opencode.json` still carries those per-agent shell catch-alls; `frontmatter.py`'s module docstring still describes per-tool permission entries | watch |

**Layer 3 verdict:** findings — 3 (major), 3 (minor), 3 (watch)

### Conformance to the Project's Own Rules

| Rule source | Rule | Verdict | Evidence |
|-------------|------|---------|----------|
| spec Expected Surface | touched paths within the surface | deviates | four paths outside it, three more than message 001 names |
| spec standing | evidence names tests that exist at the merge | deviates | the D4 tests named in message 001 are gone from the merged tree |
| spec standing | a fixture answer is one the real verb can give | conforms for D1 to D3, not shown for D4 | no test pins a restricted agent |
| CLAUDE.md § Documentation Standards | current state only | deviates | L3-7 and L3-9 (contract and adoc contradictions) |

## Metrics and Anomalies

- Tokens: `unknown`; out of scope. `landing-check` on message 002 is incomplete on `total_tokens` alone.
- Anomalies: message 001 was archived by this orchestrator as a mid-flight report; that is what stopped the lane from amending it. A merged-state correction is a second message, so the plan has two messages in the archive. The lesson is recorded in the anchor's working rules.

## Routing and Merge Behavior

- Review: CodeRabbit (required, quota-limited) reviewed `03a35cf11` and `3769c5d12` after its quota reset; eight findings, seven fixed (`3769c5d12`, `686146186`) and one answered with a reason (the audit and health source-set difference, which the leaf finds sound). Review numbers re-read with `runbook_lane review-gate --pr-number 1954`: `unresolved_review_threads` 0 (agrees) and `review_body_findings_total` 8 (agrees: `inline-1` to `inline-8`; the lane's list adds an outside-diff finding the verb does not count); `review_body_findings_handled` is **not re-verified** (no progress file was passed, so the verb reports 0).
- CI/merge: merge queue, squash with one parent (git); the lane's CI and verify claims were not re-read.
- Sonar: `n/a`.

## Reconciliation Actions

- [x] row `status` → `shipped` — `orchestrator queue --transition PLAN-LB-134 --status shipped`
- [x] row `landing` stamped — `orchestrator queue --set-row PLAN-LB-134 --field landing --value landings/PLAN-LB-134.md`
- [x] row `pr` and `plan_marshall_plan_id` already stamped at the mid-flight read (1954 and `rb-lb-134-opencode-permission-writer`)
- [x] epic.md narrative reconciled against the queue rows
- [x] defect/watch opened or retired
- [x] resume anchor updated in `resume_anchor.md`
- [x] `queue-view.md` regenerated

(Each box is ticked only after the call it names has returned.)

## Follow-Ups

- No blocker. **Three majors, reported to the operator and NOT staged:** L3-1 (the emitter expresses no tool restriction; its effect depends on one unread fact, the base policy of an OpenCode 2 agent, which `opencode api GET /api/agent` for `execution-context-reader` answers), L3-2 (the shadow refusal aborts `protect-path` and breaks `ensure` idempotence), and L3-4 (a scalar bash or permission value is replaced by an empty map in six writers, the lane's own residue).
- **Sequencing:** PLAN-LB-135, 136 and 140 were held behind this plan on `opencode_runtime.py`; PLAN-LB-135 is now admissible and the other two follow it one at a time. Their specs should be re-read against L3-1 and L3-2 first, because both change what they build on.
- **Watch:** L3-3, L3-5 to L3-9 and the spec's counter-example.
