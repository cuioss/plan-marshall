# Landing Analysis: PLAN-LB-136 — Antigravity standing rules and the per-task gate

epic: live-blockers
workstream: WS-04
pr: #1984

> Landing record for one shipped plan. Lives at `landings/PLAN-LB-136.md`. Written by the
> `analyze` verb after verifying claims against ground truth (actual code, artifacts,
> PR state) — a pasted claim is a lead, never a fact. See
> `persona-plan-orchestrator/standards/orchestration-model.md` for the analysis and
> reconciliation contract.

Merge commit `ff6de5f0606fba6e016d694f0aa5e1274e08118b`, a squash commit with one parent `21c9a205d` (the PLAN-LB-148 landing, read with git).
Runbook lane, harness `opencode`, model `deepseek-v4.1-flash/high`, effort `high`, executor `0.1.2123`. The message
`rb-lb-136-antigravity-standing-rules-and-task-gate-001.md` is `complete: false` on `total_tokens` alone (`unknown`; out of scope under the
ruling of 2026-10-23, so no Open Defect). The squash carries 16 files, +1209 -359.

## Deliverable Fidelity vs Spec

Read against `plans/PLAN-LB-136-antigravity-standing-rules-and-task-gate.md` and the merge's file list (`git show --stat ff6de5f06`).

| Deliverable (spec) | Verdict | Evidence |
|--------------------|---------|----------|
| D1 — the Antigravity rules carry the shared build-command rules | shipped-as-specified | `antigravity-rules.md:28-29` (the `architecture resolve` and `No plugin found for prefix` bullets), mirrored in `target-rules/SKILL.md:28`; test `test_antigravity_rules_carry_the_shared_build_command_rules` (leaf read the hunk; not re-read) |
| D2 — the bridge carries the baseline and a content hash; drift is content, not mtime | shipped-as-specified | `standing_rules_bridge.py:144-167` (`bridge_body`), `:240-299` (`drift_status`), `:302-327` (`setup`, drift read before the heal), `:197-198` (unreadable baseline keeps the bridge) — all re-read by the orchestrator; both runtimes use the shared module |
| D3 — a per-task gate stamp reaches every task's `verification.commands` | shipped-as-specified, one caveat (L1-3) | `manage-execution-manifest.py:1732-1779` (resolve), `:1782-1867` (append and withdraw), call site `:2856` — re-read; the Done-when's executable is a stubbed `_invoke_architecture_resolve`, so no live resolve is exercised |

Surface: the squash touches 16 files. The declared surface was met except `runtime_base.py` (a hypothesis; the lane chose a sibling
`standing_rules_bridge.py`, which the spec permits as "or a shared module"), `_manifest_rules.py`, the compose-fixtures file and
`test_opencode_runtime.py`. **Eight files are outside the declared list** and not the permitted shared module: `plan-marshall-antigravity`
`target-rules/SKILL.md`, `plan-marshall-opencode` `target-rules/standards/opencode-rules.md`, `manage-execution-manifest/SKILL.md`,
`manage-execution-manifest/standards/decision-rules.md`, `phase-5-execute/SKILL.md`, `marshall-steward/scripts/configure_harness.py`,
`test_domain_seeded_step_resolvability.py` and `test_harness_config.py`. The spec says the OpenCode target rules are "Adjacent to … (not
edited)"; the lane edited `opencode-rules.md` (to name `bridge_write_failed`). The lane's landing report states "two adjacent files were
changed beyond" the surface; that is not borne out (L1-4). The edits are explained (documentation that mirrors the code, a steward that must
not certify a refused write) and none is unrelated.

## Three-Layer Analysis

- **Dispatch:** one read-only leaf (`execution-context-level-5`) — reason: a full-ship landing is read by one leaf; it read the merged diff, wrote nothing and returned 3 conformance rows and 12 numbered findings. Its content sweeps used `git diff --name-only -G…`, a read-only content search, disclosed by the leaf.
- **Re-read by the orchestrator** (a point not in this list is an unverified lead): `standing_rules_bridge.py:100-330`; `manage-execution-manifest.py:1725-1875` and the call sites of the routing pass (`:2734`) and the append (`:2856`); the spec's Expected Surface; the merge's file list; the live `ci pr comments` body of #1984; the `review-gate` verdict on #1984 (with the lane's dispositions); the lane's progress file.
- **Verdict:** no blocker and no major. Layer 3: 3 minors re-read and confirmed (L3-1, L3-2, L3-5 by call order), 4 nits re-read and confirmed (L3-4, L3-7, L3-8, and the by-value withdrawal the lane named); the rest are leaf leads.

### Layer 1 — Specified

| Finding | Claim | Verdict | Polarity | Evidence (file:line) |
|---------|-------|---------|----------|----------------------|
| L1-1 | D1 met | checked | confirms | leaf: `antigravity-rules.md:28-29`, `target-rules/SKILL.md:28` (not re-read) |
| L1-2 | D2 met | checked | confirms | `standing_rules_bridge.py:144-167, 197-198, 240-327` (re-read) |
| L1-3 | D3 met, the executable in its test is a stub | checked | confirms with a caveat | `manage-execution-manifest.py:1761` (re-read) |
| L1-4 | the lane's "two adjacent files" beyond the surface | checked | contradicts | eight files, listed above (spec re-read; stat re-read) |

### Layer 2 — Spec and surface drift

- **L2-1 (minor, leaf):** `manage-execution-manifest/standards/manifest-schema.md` still says the stamp "serves planning and observability" and does not list the per-task append or `verification.per_task_gate_commands`; `SKILL.md` and `decision-rules.md` say "one durable write", so the three documents disagree. Not re-read.
- **L2-2 (nit, leaf and lane):** the steward's bridge verdict stays marker-only (`configure_harness.py:134-145`); the lane answered CodeRabbit's outside-diff finding as out of scope and closed only the concrete hole (a refused setup write is never certified).
- **L2-3 (nit, leaf):** a comment near `manage-execution-manifest.py:1714-1720` and a test docstring still describe the old behaviour. Not re-read.
- **L2-4 (nit):** a trailing blank line in `antigravity-rules.md`. **L2-5 (verified negative by a content sweep, leaf):** no non-test file still carries the retired drift reasons or private helper names; three documents were not read line by line.
- **L2-6 (leaf):** the OpenCode refactor onto the shared module keeps strict decode, the staged replace and the drift read from the write; two changes are improvements.

### Layer 3 — Defects

| Finding | Severity | Claim | Evidence |
|---------|----------|-------|----------|
| L3-1 | minor, re-read | `_is_within(bridge, project_dir)` resolves the leaf, so a bridge that is a symlink to a path outside the project answers `bridge_write_failed` on every setup, and the steward then reports `damaged` with a re-emit command that cannot fix it; the prior OpenCode writer replaced the symlink, and the comment at `:221-224` still says so | `standing_rules_bridge.py:103, 204, 221-225`; the OpenCode symlink tests point inside the project (leaf, not re-read) |
| L3-2 | minor, re-read | `baseline_mode or 0o600` falls back only when every bit is zero, so a baseline at `0o200` gives a `0o200` bridge, against the docstring; the mode is applied only on a write, so an existing `0o644` bridge over a now-private baseline is never re-moded (`:217-218`) | `standing_rules_bridge.py:114-128, 217-218, 230` |
| L3-3 | nit, leaf | a time-of-check gap between the containment check and `mkdir`/`mkstemp` | `:204` against `:220-225` |
| L3-4 | nit, re-read | `drift_status` follows a symlinked bridge and can answer `in_sync`, while `write_bridge` never accepts one as current | `:286-289` against `:214` |
| L3-5 | minor, re-read by call order | the per-task append runs after the routing pass, so the compose that appends a gate does not fold it into `bash_timeout_seconds`, and a task with `commands: []` gets none until the next compose; reasoned from the code, not executed | call sites `:2734`, `:2856` |
| L3-6 | nit, leaf | the `[STATUS]` lines are logged before the compose-time resolution gate, so a compose that then fails logs an append that was never persisted | not re-read |
| L3-7 | nit, re-read | a recorded command removed from `commands` by hand is both recorded and missing, so `owned` holds it twice | `manage-execution-manifest.py:1844, 1852` |
| L3-8 | nit, re-read | the resolve subprocess runs before the `tasks_dir.is_dir()` check | `:1813-1816` |
| L3-9 | nit, lane-named | withdrawal is by value, so a plan-authored copy of the same string goes too; the lane states why no reachable path produces it | `:1838, 1847` |
| L3-10 | minor, leaf | `test_dispatch_damaged_stub_returns_damaged_verdict` now stubs `failed=True`, so its `damaged` verdict comes from the new short-circuit and the marker-check path is no longer exercised by it | `test_harness_config.py` near 419-433, `configure_harness.py:236-237` (not re-read) |
| L3-11 | nit, leaf | `BRIDGE_VERSION` stays `1` though the file layout changed from a stub to a content-carrying bridge; old stubs match the marker and are caught as `source_hash_missing` | not re-read |
| L3-12 | not checked | whether `manage-tasks` keeps `verification.per_task_gate_commands` on its own updates (if it drops the key, withdrawal can never happen), and whether the two resolve passes (top-level `--plan-id` or not) return the same executable | nobody read it |

No defect found, by reading: the steward does not certify a bridge whose setup write was refused; an orchestrator-tier gate is not appended; an unresolved lookup withdraws nothing; the version-marker regex has no off-by-one.

## The review gate on this PR

`review-gate --pr-number 1984` with the lane's seven dispositions and `--required-reviewer coderabbit` answers `all_handled`, 0 unresolved threads, 7/7. Without the dispositions it answers 0/7, which is the gate working. The live review body also holds a CodeRabbit `Outside diff range comments (1)` block, which the gate does not count: the total is the seven inline findings, and the lane's own progress file records the outside-diff finding as handled (`f8fa95cb4`). This is the same parser gap as the Open Defect opened from PLAN-LB-148, seen on a second PR; the lane's record, not the gate, is what covered it.

## Residue the lane named

The lane's three residue items (the `[STATUS]` line with no direct test, the inert `write_bridge` patch in `test_outdated_bridge_version_is_damaged`, the by-value withdrawal) are confirmed as stated.

## Reconciliation

Row stamped `shipped`, `pr` 1984, `landing`, and `plan_marshall_plan_id` `rb-lb-136-antigravity-standing-rules-and-task-gate` (from the sender). No `corpus set-verdict`: the spec's row is shipped and nothing reads a shipped spec's verdicts. A harness sync is owed (bundle sources under `marketplace/bundles/` changed, among them `manage-execution-manifest`, which the executor loads); no verb or flag was added, so no executor regeneration is owed. PLAN-LB-135's L1-1 and L1-6 (the Antigravity copy's defects) are closed by the shared writer; the symlink-leaf regression above is new.
