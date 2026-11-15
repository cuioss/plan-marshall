# Landing Analysis: PLAN-LB-135 — the OpenCode 2 bridge reports what it did and survives any baseline bytes, and no OpenCode surface names the OpenCode 1 shape

epic: live-blockers
workstream: WS-04
pr: #1972 (squash commit `57f8e70babf64bc6affd06a2721372683f8e4a49`, one parent `afaeb0d2f90d3f0f8ece7465b5a37e19397aa153`)

> Landing record for one shipped plan. Written by the `analyze` verb after verifying claims against ground truth (actual code, artifacts, PR state) — a pasted claim is a lead, never a fact.

## Deliverable Fidelity vs Spec

One message from the runbook lane (sender `rb-lb-135-opencode-bridge-and-sweep`, revision 0, `merge_state=merged`, deliverables 4/4, harness `opencode`, model `deepseek-v4.1-flash/high`). It is `complete: false` on `total_tokens` alone (out of scope under the operator's focus rule, as for every runbook landing in this epic). The row was `running` and carried no `pr` or plan id; both are stamped now from the sender and the provider. The squash commit has one parent, read with git (`git rev-parse 57f8e70ba^`) before the leaf prompt named it, and touches 12 paths (read with `git diff --name-only 57f8e70ba^ 57f8e70ba`): 5 under `marketplace/bundles/`, 1 under `doc/`, 6 under `test/`.

The facts block agrees with ground truth on the thread count: `unresolved_review_threads=0` and `review_body_findings_total=10` equal the provider's numbers from `runbook_lane review-gate --pr-number 1972` (ids `inline-1` to `inline-10`, all CodeRabbit). The `handled` figure is **not** cleanly reproducible and one lane statement is not borne out (see "Review record" below): the run's progress file holds dispositions for 4 of the 10 CodeRabbit findings, and the gate given exactly those 4 answers `handled: 4`, `body_findings_undisposed` for `inline-5` to `inline-10`. The PR threads corroborate the lane's 10 of 10: every one of the ten CodeRabbit threads is resolved and carries a CodeRabbit reply (the fix thanked, or the request withdrawn), read through `ci pr comments`. `sonar_open_new_issues=n/a`. The PR reads merged.

| Deliverable (spec) | Verdict | Evidence |
|--------------------|---------|----------|
| D1 — setup survives any baseline or bridge bytes | shipped-as-specified | `_baseline_text` catches `(OSError, UnicodeDecodeError)` (`opencode_runtime.py:148-151`, re-read); an unreadable baseline with a bridge present returns before any write (`:217-218`, re-read); the status answers `baseline_unreadable` / `bridge_unreadable` without raising (`:267-272,290-298`, re-read); the writer compares bridge BYTES (`:224`, re-read). Tests (leaf read, not re-read): `test_an_unreadable_baseline_never_overwrites_the_bridge` with real `\xff\xfe` bytes and no `_baseline_text` reference left under `test/` |
| D2 — setup reports the drift it healed, from what the write did | shipped-as-specified; one gap against the spec's own constraint (L1-1) | `_BridgeWrite(written, replaced)` (`:180-191`); `bridge_drift = drift['drift'] or bridge_write.replaced`, reason `bridge_body_replaced` when the status read `in_sync` (`:1653-1658`, re-read); a missing baseline plus a non-stub bridge is drift, plus the byte-identical stub is not (`:273-287`, re-read). The single production caller is `opencode_runtime.py:1648` (leaf sweep, coverage below); the lane's caller claim and its `antigravity_runtime.py` independent-copy claim agree with the leaf |
| D3 — no OpenCode-side surface names the OpenCode 1 shape | shipped-as-specified for the named passages; one document still names it (L3-2) | `target-rules/SKILL.md`, `README.md`, the `_config_core.py` comment and the new `opencode.adoc` matrix wording read consistent (leaf, not re-read); `opencode.adoc:164-169` still labels guard rules "(bash)" (leaf, not re-read) |
| D4 — the guard tests find what they were meant to find | shipped-as-specified | the widened guard hits the parent `target-rules/SKILL.md` and `README.md` on `git show afaeb0d2f:` (leaf read), and each glob has a non-empty guard (leaf); `skills/*/workflow/*.md` matches no file today, so that arm is vacuous (leaf, not re-read). The precedence test's mutation run is a lane claim not re-run |

Spec sub-points: both HYPOTHESES are settled by the lane in the message and the leaf agrees — the caller enumeration (C4 below) and `target_context.py` read-only (`git diff --name-only` read above: it is not among the 12 paths). The verify-first clause for D2 is answered in the PR body (the verdict is derived from the write).

## Three-Layer Analysis

The landing was read on three layers by one read-only leaf (`execution-context-level-5`, `orchestrator.analyze` surface), and the orchestrator re-read the points marked as re-read. The reading is **by reading, no build, no test run, no write**.

- **Dispatch:** one read-only leaf per landing — reason: reading merged code and ten claims one by one is the depth the dispatch rule exists for; this was the only landing in the firing.
- **Verdict:** no blocker. **One major with a narrow trigger (L1-1)**, graded by the leaf and confirmed by the orchestrator re-read; layer 1: 1 major, 3 minor, 3 info; layer 2: 2 minor and 1 info; layer 3: 3 minor. The layer-3 defects are reported to the operator in the same turn; none is fixed inline.
- **Leaf rule breaks:** none beyond what it declared: it logged nothing (it was told not to touch `.plan/`), and ran read-only `grep` through Bash because its envelope has no Grep tool. No refused command is reported.

Re-read: `opencode_runtime.py:140-299,1636-1665`; `configure_harness.py:100-234`; the squash commit body; the progress file's `finding:` lines (14 lines) and its CodeRabbit lines; the provider through `review-gate` (bare, and with the four recorded dispositions) and `ci pr comments`; the changed path list through git; the surface delta through `inbox landing-check`; the PLAN-LB-135 and PLAN-LB-136 specs; the tracked bridge `.opencode/rules/plan-marshall-standing-rules.md` for the "Merge Authorization" heading (absent). **Not re-read** (unverified leads): every test file's content (the leaf read them); `opencode.adoc` and `opencode-rules.md` lines (L3-1 to L3-3); `antigravity_runtime.py:126,163,169,311-312`; the C4 sweep (the leaf's `grep -rn` over `*.py`, `*.md`, `*.adoc` in `marketplace/`, `test/`, `doc/`, and a second sweep over `.claude/` and `.opencode/`); `opencode_runtime.py` outside the two ranges above; `configure_harness.py` outside `:100-234`; `guard.js`; the claim that the repository's bridge is git-tracked.

### Layer 1 — Specified

| Finding | Claim | Verdict | Polarity | Evidence (file:line) |
|---------|-------|---------|----------|----------------------|
| L1-C1 | A non-UTF-8 baseline or bridge raises nowhere in setup or the drift status; the existing bridge is kept (`bridge_written` false, reason `baseline_unreadable`) | checked (re-read) | confirms | `opencode_runtime.py:148-151,217-218,267-272,290-298`. Scope: the bridge is kept only when it is a regular file or a link to one (`:217` uses `is_file()`); an absent bridge, a directory or a dangling link takes the stub |
| L1-C2 | `bridge_drift` is derived from the write; a missing baseline with a rule-carrying bridge is drift | checked (re-read) | confirms | `:1653-1658,273-287` |
| L1-C3 | The writer stages through `mkstemp` in the bridge's own directory and replaces the path atomically; a symlink at the bridge path is never written through; a failed write leaves no staging file and does not truncate the old bridge | checked in code (re-read) and not tested on the failure path (leaf) | confirms, caveats L1-3 / L1-4 | `:232-241` |
| L1-C4 | `standing_rules_drift_status` has one production caller; `configure_harness` reads the bridge itself; `antigravity_runtime.py` is an independent copy | checked (leaf; sweep limited to the file types above) | confirms | `opencode_runtime.py:1648`; `configure_harness.py:134-144` (re-read: it reads the bridge file directly) |
| L1-C5 | `configure_harness` refuses to certify an unreadable baseline | **partly**: the baseline arm is closed (`:114-123`, re-read); the verdict arm still certifies any bridge that carries the marker | partly refutes | `configure_harness.py:134-144` (re-read). A non-UTF-8 bridge (decoded with `errors='replace'`), a stale-hash bridge and a rule-less stub when a baseline exists all read `current`; it matters when setup's write did not land (L1-1) |
| L1-C6 / C7 | `target_context.py` is not in the diff; no verb or flag is added, so executor regeneration is not owed | checked (git for the first; leaf for the second) | confirms | `git diff --name-only`; leaf: no `add_parser` / `add_argument` in the three scripts' diff. A changed script still changes the hash the executor template compares (the PLAN-LB-144 L2-2 reading, not re-read here), and regeneration is already owed for other plans, so no new owed item |
| **L1-1 (major, narrow trigger)** | A write failure is reported as "nothing to do", so setup reports `bridge_written` false and (for a hand-edited body) `bridge_drift` false, `in_sync` | **new, re-read** | refutes the spec's "setup reports what it did" | `opencode_runtime.py:243-244` turns any `OSError` into `_BridgeWrite(False, False)`, the same value as "already current", with no error field; setup uses only `drift` and `replaced` (`:1653`). Trigger: `.opencode/rules/` not writable (a read-only mount or another owner), or `chmod` refused by the filesystem (`:237`), with a changed baseline or a hand-edited body. For a changed baseline setup still says drift true from the pre-heal status; for a body-only edit it says clean. `dispatch_platform_runtime_setup` reads only `status` and the warnings from the setup payload (`configure_harness.py:192-207`, re-read), so its verdict goes through `:134-144` (marker only) and reads the stale bridge `current`, and `rules_emitted: true` is persisted (leaf, `:279,:301`, not re-read) |
| L1-2 (minor) | The re-emit advice cannot converge for an unreadable baseline: reconcile returns False (`:114-123`), the verdict is `damaged`, `bridge_reemit_command` is surfaced, and re-running setup keeps the bridge (`opencode_runtime.py:217-218`) | checked (re-read of the two arms; the surfacing line `:317-318` is the leaf's) | refutes | `configure_harness.py:114-123,228-231` |
| L1-3 (minor) | The replaced bridge is always mode 0644 (`:237`), ignoring the old file's mode and the umask; the old `write_text` honoured the umask. Under umask 077 a copy of a 0600 `CLAUDE.md` becomes world-readable | checked (re-read of the line; the old behaviour is the leaf's) | refutes | `opencode_runtime.py:237` |
| L1-4 (minor) | A symlinked bridge is kept as is when the baseline is unreadable (`:217`, `is_file()` follows links), which contradicts "never owned" (`:221-223`) | checked (re-read) | refutes | `opencode_runtime.py:217,221-223` |
| L1-5 (info) | The TOCTOU between the symlink check and the replace is harmless (rename never follows the destination); a directory at the bridge path fails the replace and the staging file is removed; a killed process leaves a `.<name>.XXXX.tmp` that is not `*.md`; no fsync, so power loss is not covered | checked (leaf; the code is re-read, the edge cases are leaf reasoning) | none | `:224-241` |
| L1-6 (minor, sibling outside the diff) | `antigravity_runtime.py` keeps the defects this landing fixed for OpenCode: it catches only `OSError` at `:126,163` (a non-UTF-8 bridge raises out of setup), reads the drift status after the heal at `:311-312`, and its drift is mtime-based (`baseline_newer`, `:169`) | leaf, not re-read | refutes | the PLAN-LB-136 spec (re-read by grep) names none of `UnicodeDecodeError`, `errors='replace'`, a write failure or `mkstemp`, so the spec does not carry it |
| L1-7 (info) | The repository's own tracked bridge is stale: it has no "Merge Authorization" heading while `CLAUDE.md` does, so a setup run here reports `baseline_changed` | checked (re-read by grep: 0 matches) | none | `.opencode/rules/plan-marshall-standing-rules.md`; the heading came with PR #1974 |

No finding settles a staged-spec corpus claim cleanly, so no re-grounding verdict is persisted.

**Layer 1 verdict:** findings — 11 (1 major with a narrow trigger, 4 minor, 6 info or confirming); no blocker

### Layer 2 — Implemented

| Deliverable | Code trace | Test that can fail | Unexplained file / unborne claim | Verdict |
|-------------|------------|--------------------|---------------------------------|---------|
| D1 | `opencode_runtime.py:148-151,217-224,290-298` (re-read) | real `\xff\xfe` bytes in `test_an_unreadable_baseline_never_overwrites_the_bridge` (`test_opencode_runtime.py:2134`) and `test_a_non_utf8_bridge_never_raises_from_setup_or_drift` (`:2159`); no `_baseline_text` reference left under `test/` (leaf) | none | checked (partly re-read) |
| D2 | `:273-287,1648-1658` (re-read) | `test_setup_reports_drift_for_a_hand_edited_bridge` (`:2300`) and the two symlink tests (`:2253`); a write-through regression would turn the first symlink test red (leaf) | see L2-1 | checked (partly re-read) |
| D3 | docs (leaf) | `test_target_rules_skill_body_names_the_opencode2_tools_and_the_hash_drift`, `test_the_role_matrix_describes_the_agent_fallback_as_a_list_rule`, `test_every_cited_test_module_exists` (leaf) | see L2-2 | checked (leaf) |
| D4 | the widened guard would have gone red on the parent `SKILL.md` and `README.md` (leaf, `git show afaeb0d2f:`) | the precedence test passes at base by design; the mutation run is the lane's claim, not re-run | see L2-3 | checked (leaf) |

- **L2-1 (minor):** nothing covers the writer's failure path. The leaf's searches for `mkstemp`, `staging`, `.tmp`, `chmod`, `PermissionError` and `st_mode` in `test_opencode_runtime.py` find nothing relevant, so staging cleanup, non-truncation, the file mode and the swallowed write error (L1-1) are untested.
- **L2-2 (minor):** `test_every_cited_test_module_exists` matches cited basenames across `test/**/*.py`, so a basename that exists elsewhere passes: `test_emitter.py` exists in three directories (antigravity, claude, opencode), so deleting the OpenCode one, or filing a citation under the wrong directory, still passes. It caught the real defect and the lane says so; path-aware matching is the lane's own follow-up (message §9).
- **L2-3 (minor):** weak assertions. `test_harness_config.py:624` asserts `bridge_verdict != 'current'`, which a failed setup also satisfies (the `_reconcile_standing_rules_bridge(...) is False` assertion is the one with teeth); `test_opencode_runtime.py:2159` does not assert setup's `bridge_drift` or `bridge_reason`. `test_harness_config.py:421-449` monkeypatches `_write_rules_bridge`, a collaborator of the unit under test and not the unit itself (info).
- **Surface delta:** declared 7 written entries (the 8th, `target_context.py`, is read-only), realized 12, **added 5, missing 0** (`expansion_detected`, read with `inbox landing-check --declared-paths … --realized-paths …`): `marketplace/bundles/plan-marshall-opencode/README.md`, `_config_core.py`, `configure_harness.py`, `test_harness_config.py`, `test_opencode_permission_docs.py`. The lane names the same five and why (the last OpenCode 1 tool name, a comment contradicting the corrected adoc, a steward verdict that certified an unreadable baseline, and the two doc-test homes). Of the five, `configure_harness.py` is production code with a behaviour change (the unreadable-baseline refusal) outside the spec's declared surface; the others are text and tests. No row running in parallel declares any of these paths, so no collision is recorded.
- **Claim not borne out (review counts):** the lane says "19 comments/threads" and "14 threads were replied to and resolved". The provider shows 26 review threads (10 CodeRabbit, 16 Sourcery) and the gate shows 0 unresolved; the lane's 19 and 14 do not match, and the provider's numbers are the ones that hold.
- **Claim not borne out (PR body versus code):** the squash body says the bridge reader "in the writer and in the drift status decodes with `errors='replace'`". The shipped code compares bytes in the writer (`:224`) and decodes strictly in the status (`:291-293`), answering `bridge_unreadable`; the body describes an earlier head, not the merged one. (`opencode.adoc` and `opencode-rules.md` wording is L3-1.)
- **Claim C9 (lane residue, borne out):** the lane's note on basename matching is accurate, and it records the marshal.json prose sites at `marketplace_paths.py:260` and `test_config_defaults.py:1095` as a leftover for a documentation sweep (leaf did not read them; lead).
- **Claim not re-checked (executor regeneration "not owed"):** no verb or flag was added (leaf), but the changed scripts change the hash the executor template compares; on a stale executor they dispatch without pre-spawn validation (PLAN-LB-144 L2-2, `execute-script.py.template:1387-1416`, not re-read here). Regeneration is already owed, so no new item; **not shown by reading** for these three scripts.

**Layer 2 verdict:** findings — 3 (all minor); the surface delta and the two unborne claims recorded above

### Layer 3 — Correct

| Defect | File:line | Triggering input | Effect | Severity |
|--------|-----------|------------------|--------|----------|
| L3-1 | `opencode-rules.md:59-60` | an operator reads that re-setup "heals a drifted … bridge" and "leaves a current bridge untouched" | a `baseline_unreadable` drift (line 59 lists it as drift) is not healed (`opencode_runtime.py:217-218`, re-read); a symlinked bridge with matching bytes is replaced (`:224`, re-read); line 59 says a non-UTF-8 bridge reports `bridge_unreadable`, which holds only when the baseline exists (with none the reason is `baseline_missing`, `:273-287`, re-read). Document lines are the leaf's, not re-read | minor |
| L3-2 | `opencode.adoc:164-169` | any reader of the guard rules | R1, R2, R4, R5 and R6 are labelled "(bash)", which names the OpenCode 1 tool as the OpenCode tool; on OpenCode 2 it is `shell` (the guard accepts both, leaf `guard.js:1883`). The file is outside the C8 sweep, so the guard cannot find it (leaf; `opencode.adoc:243` "bash timeout ceiling" is info) | minor |
| L3-3 | `opencode.adoc:253` | an operator reads that setup "reports the drift verdict it healed" | setup does not heal an unreadable baseline, and a swallowed write failure heals nothing (L1-1) (leaf, not re-read) | minor |

**Layer 3 not shown by reading:** the document lines above (leaf only); the suite's pass/fail (nothing was run); whether consumer projects git-ignore the bridge; whether the loop in L1-2 is visible to an operator.

**Layer 3 verdict:** findings — 3 (all minor); the layer-1 major (L1-1) is the one defect with an effect on an operator

### Conformance to the Project's Own Rules

| Rule source | Rule | Verdict | Evidence |
|-------------|------|---------|----------|
| Spec standing constraint | setup reports what it did | **deviates** | L1-1: a failed write reads as "already current" (`opencode_runtime.py:243-244`, re-read) |
| Spec standing constraint | the bridge is kept whenever its baseline cannot be read | conforms, with the symlink and non-regular-file qualifiers | `:217-218` (re-read) |
| Spec standing constraint | tests use real bytes, not a monkeypatch of the unit under test | conforms for the unit; one collaborator is patched | no `_baseline_text` reference left; `_write_rules_bridge` patched at `test_harness_config.py:421-449` (leaf) |
| Spec standing constraint | documentation states current behaviour, no change description | deviates in the PR body only; the documents read as current state (leaf, not re-read) | the squash body's `errors='replace'` line |
| Spec standing constraint | executor regeneration only if a verb or flag is added | conforms | leaf: no new `add_parser` / `add_argument` |
| CLAUDE.md § Commit Trailer | exactly the plan-marshall trailer and nothing else | deviates, outside the lane's control | the squash commit ends with GitHub's `Co-authored-by` line for the human author, then the `plan-marshall` trailer (re-read) |
| CLAUDE.md § Merge Authorization (Standing) | the lane merges its own PR once the gate passes, without asking | conforms | message §6: no operator question asked; the PR reads merged |
| CLAUDE.md § Documentation Standards | no duplication | not shown by reading | the document lines are the leaf's |

## Metrics and Anomalies

- Tokens: `unknown` (the harness measured none; out of scope under the operator's focus rule).
- Duration: not reported.
- Anomalies: 38 routed builds, all through the build-server long-poll; one whole-tree `module-tests` at `55bfbf06c` hit the daemon bound (750 s) and was re-run with 1800 s (1212 s), and queue waits reached 1828 s behind other sessions (all lane-reported, not re-read). Two guard refusals (R1 on a pipeline, R5 on a mistyped interpreter call), none worked around (lane-reported, not re-read from `.plan/temp/guard.log`).

## Routing and Merge Behavior

- Review: CodeRabbit (required) reviewed `5943fa1ea` and the merge head `da2f86e81`; its quota notice at `ce942e683` arrived while a qualifying review was on record, so no trigger was owed (CodeRabbit stall recovery policy). Sourcery (optional) reviewed twice and was skipped later; it gated nothing. `review-gate` on the merged head: 0 unresolved threads, 10 body findings, `handled` 4 from the four dispositions the progress file holds, and all ten threads resolved with a CodeRabbit reply on the provider. The bare run answers `handled: 0` and `merge_allowed: false` only because it holds no dispositions input; given the four recorded lines it answers `handled: 4` and names `inline-5` to `inline-10`. **The lane's own record does not carry its "10 of 10"**: six findings of the second review were handled on the PR but not written to the progress file as `finding:` lines. The merge went through under the standing authorization once the provider's gate conditions held, which the PR threads support; the gap is in the record, not on the PR.
- CI/merge: `verify` green on the head per the lane (gates at `5943fa1ea`, `quality-gate` 74 s, `module-tests` 971 s, `verify` 1033 s); the PR reads merged as a squash with one parent. No rebase conflict reported.
- Sonar: `sonar_open_new_issues=n/a`; the project does not enable Sonar and this epic ignores it. No figure measured.

## Reconciliation Actions

- [x] row `status` → `shipped` — `orchestrator queue --transition PLAN-LB-135 --status shipped`
- [x] row `pr` stamped — `1972`
- [x] row `landing` stamped — `landings/PLAN-LB-135.md`
- [x] row `plan_marshall_plan_id` stamped — `rb-lb-135-opencode-bridge-and-sweep` (the sender's `{plan}` carried as data)
- [x] epic.md narrative reconciled against the queue rows (queue annotation and Decisions entry; no Open Defect opened for the incomplete landing, because `complete: false` on `total_tokens` alone is out of scope under the operator's focus rule)
- [x] resume anchor updated and `queue-view.md` regenerated
- [x] message `rb-lb-135-opencode-bridge-and-sweep-001.md` archived after the persist

## Follow-Ups

- **Residue of this plan, one surface** (the OpenCode bridge writer, the steward's bridge verdict and the OpenCode documents): L1-1 (the swallowed write failure and the steward ignoring setup's `bridge_written`/`bridge_drift`, the one major, narrow trigger), L1-2 and L1-4 (the unreadable-baseline loop and the symlinked bridge kept), L1-3 (mode 0644), L2-1 to L2-3, L3-1 to L3-3. No fix plan is staged without the operator word; it joins the consolidated-plan decision (4).
- **PLAN-LB-136 carries the sibling.** L1-6 is the Antigravity copy of every defect this plan fixed for OpenCode, and the PLAN-LB-136 spec names none of them. Its outline should read this landing and `antigravity_runtime.py:108-184,300-327` and decide there, as the spec says of its D2 helper reuse; the spec is not edited here. L1-1 should be settled once for both runtimes, not copied.
- **The repository's own bridge is stale (L1-7):** a setup run in this checkout rewrites `.opencode/rules/plan-marshall-standing-rules.md` from the new `CLAUDE.md`; whether that tracked file is committed is the operator's decision, not an owed ledger item.
- **Lane residue (message §9), recorded as leads on the same surface:** two prose sites still say `runtime.target` is read from `.plan/marshal.json` (`marketplace_paths.py:260`, `test_config_defaults.py:1095`) and path-aware matching for `test_every_cited_test_module_exists`; not staged.
- **Harness sync owed:** this plan changes `marketplace/bundles/` (the bridge writer, the steward and the OpenCode target rules). The sync the operator ran earlier in this session pinned 0.1.2114 and its registry backup is stamped 17:03Z, while the lane's message is stamped 18:13Z, so that sync predates this merge and does not carry it. A new `/sync-harnesses` run is owed (Claude, OpenCode and Antigravity).
