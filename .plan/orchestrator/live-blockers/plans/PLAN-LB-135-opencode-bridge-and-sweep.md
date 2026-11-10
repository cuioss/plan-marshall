# PLAN-LB-135: The OpenCode 2 bridge reports what it did and survives any baseline bytes, and no OpenCode surface names the OpenCode 1 shape

epic: live-blockers
workstream: WS-04

> Staged plan spec — one shippable unit of work, ready for `/plan-marshall-runbook-lane` hand-off.
> Lives at `plans/PLAN-LB-135-opencode-bridge-and-sweep.md` and is queued as one row file, `queue/PLAN-LB-135.json`,
> in the epic ledger. The orchestrator EMITS the command below; it never launches the plan inline.
> This spec is SELF-SUFFICIENT: the emitted command is a one-line pointer and carries no
> brief, so every per-plan carry is authored here and nowhere else.
> See `persona-plan-orchestrator/standards/orchestration-model.md` for the tier and
> hand-off contract.

> Regrouped on the operator's word of 2026-11-09 from the bridge, setup and documentation half of PLAN-LB-83 (D3 and D4 there), staged
> from the adversarial analysis of PLAN-LB-48 (#1830, `148558aa1`). Every claim was re-grounded against `main` at `9cd644892` by a
> read-only leaf on 2026-11-09; nothing in these areas shipped since. **Each deliverable is its own outline deliverable, and each
> Done-when is its own success criterion. Do not merge them.** Every Done-when below fails at `9cd644892` unless it says "holds at".
> No Sonar. No token or measurement work.

## Objective

The OpenCode standing-rules bridge is generated from `CLAUDE.md` and drift is detected by content hash. Setup still crashes on a
`CLAUDE.md` or a bridge that is not UTF-8, reports `bridge_drift: false` for a bridge it just replaced, and a rule file claims the
opposite. The OpenCode target rules and the developer document still name the OpenCode 1 tools and the mtime drift check, and the
guard test that was meant to find them looks at the wrong files. This plan closes those.

## Deliverables

1. **Setup survives any baseline or bridge bytes.**
   - `_baseline_text` catches `UnicodeDecodeError` as well as `OSError`, so a `CLAUDE.md` with a non-UTF-8 byte is an unreadable
     baseline (the existing bridge is kept) and no longer crashes `project_initial_setup` or `standing_rules_drift_status`.
   - A bridge file that is not UTF-8 is read the way `installed_rules_clobbered` already reads it (`errors='replace'`), or reported
     unreadable; it never raises out of `_write_rules_bridge` or the drift status.
   - The unreadable-baseline test uses a real unreadable file (a non-UTF-8 `CLAUDE.md`), not a monkeypatch of the unit's own
     `_baseline_text`.

   *Done when:* each of these fails at `9cd644892`:
   - after one setup, `CLAUDE.md` rewritten with the bytes `\xff\xfe` plus text and setup run again completes with `bridge_written: false`, `bridge_reason: baseline_unreadable` and the bridge file unchanged (it raises at `9cd644892`);
   - a bridge file holding non-UTF-8 bytes does not raise from setup or from the drift status;
   - `test_an_unreadable_baseline_never_overwrites_the_bridge` passes with a real non-UTF-8 `CLAUDE.md` and no monkeypatch of `_baseline_text`.

2. **Setup reports the drift it healed, from what the write did.**
   - `standing_rules_drift_status` returns `drift: false` / `baseline_missing` even when a non-stub bridge exists, while
     `_write_rules_bridge` replaces that bridge with the stub when the baseline is missing; and a bridge whose body was hand-edited with
     its marker and hash intact reads `in_sync` (it compares the recorded hash to the baseline only) while the writer rewrites it. Setup
     then reports `bridge_written: true` beside `bridge_drift: false`.
   - The verdict is derived from what the write did: a replaced or rewritten bridge is reported as drift (`bridge_drift` is true
     whenever the writer replaced a bridge that differed from what it wrote), and the drift status distinguishes a missing baseline
     with a stub bridge (in sync) from a missing baseline with a non-stub bridge (drift).
   - `test_standing_rules_drift_baseline_missing_with_bridge` (`test_opencode_runtime.py` L1953-1963) pins the old
     `{'drift': False, …, 'baseline_missing'}` answer for a non-stub bridge and is amended with the change; the rule file
     `marketplace/bundles/plan-marshall-opencode/skills/target-rules/standards/opencode-rules.md` (L60: "a setup that rewrote the
     bridge never reports a clean bridge") then states what the code does.
   - Before changing the drift status, read every caller of `standing_rules_drift_status` and record them.

   *Done when:* each of these fails at `9cd644892`:
   - setup after `CLAUDE.md` is deleted (a non-stub bridge exists) reports `bridge_drift: true` and writes the stub;
   - setup over a bridge whose body was hand-edited with marker and hash intact reports `bridge_drift: true`;
   - `test_a_deleted_baseline_replaces_the_bridge_with_the_stub` (L2073-2086) asserts `bridge_drift`;
   - the drift status for a missing baseline plus a non-stub bridge is `drift: true`.

3. **No OpenCode-side surface names the OpenCode 1 shape.**
   - `marketplace/bundles/plan-marshall-opencode/skills/target-rules/SKILL.md` names the OpenCode 2 tools (`shell`, `subagent`) where
     it says `bash` (L15, L28) and `task` (L19, L35), and its drift sentence (L34) describes the content hash, not "a baseline newer
     than the bridge".
   - `doc/developer/opencode.adoc`: the role-matrix row "Git write" (L183) and the passages at L201, L206, L216, L221 and L224 describe
     the `"*": "ask"` fallback as a list rule and not as `agents.build.permissions` map notation; L247 no longer says setup writes
     `runtime.target: opencode` to `.plan/marshal.json` (setup reports `marshal_written: false`); L399 no longer cites
     `test_permission_fix_opencode.py`, which does not exist.
   - Read each passage against the code before editing; a passage the code still bears out stays.

   *Done when:* each of these fails at `9cd644892`: a doc test asserts `target-rules/SKILL.md` carries `shell` and `subagent`, carries
   no OpenCode `bash` / `task` instruction, and describes the hash drift; a doc test asserts `opencode.adoc` describes the fallback as a
   list rule and cites only tests that exist.

4. **The guard tests find what they were meant to find.**
   - `test_no_bundle_standard_names_the_opencode_subagent_tool_as_task` (`test_opencode2_dispatch_shape.py` L57-65) globs
     `*/skills/*/standards/*.md` and matches the literal ``OpenCode `task` ``. Widening the glob alone still passes at `9cd644892`
     (`target-rules/SKILL.md` never contains that literal), so the needle widens too: a backticked `task` or `bash` used as the tool
     name inside the `plan-marshall-opencode` bundle, and `SKILL.md` and `workflow/*.md` are in the glob. The widened test lands before
     D3's edit so it is shown red.
   - `test_target_context.py` gains a precedence test with literal environment names (all three signals set resolves to
     `antigravity`; dropping the antigravity signal resolves to `opencode`; dropping that resolves to `claude`) that does not read
     `TARGET_ENV_SIGNALS`. It passes at `9cd644892` by design: it is a regression pin, and it is shown not vacuous by reordering the tuple
     in a mutation run, recorded as `order=mutation-after`.

   *Done when:* the widened guard test fails at `9cd644892` on `target-rules/SKILL.md` L15, L19, L28 and L35; the precedence test passes
   at `9cd644892` and fails when `TARGET_ENV_SIGNALS` is reordered (recorded).

Split guard: four deliverables, all OpenCode-only in one file family (`opencode_runtime.py`, the OpenCode target rules, one developer
document and their tests). D3 is a documentation sweep with no new logic and D4 is tests only.

## Standing Constraints

- Settle each HYPOTHESIS first. A refuted claim is dropped from its deliverable and the PR says so.
- The bridge is kept whenever its baseline cannot be read; a bridge is replaced only from a readable baseline or by an explicit stub
  rule, and setup reports what it did.
- Documentation states the current behaviour; no comment or document describes a change or the old behaviour.
- Tests state their purpose, use the `PLAN_MARSHALL_HOME` fixture, are shown red where a Done-when says so, and use real bytes, not
  a monkeypatch of the unit under test.
- Executor regeneration only if a verb or a flag is added.
- No token or measurement work. No Sonar.

## Claim Labels

- OBSERVED: `_baseline_text` (L140-145) catches `OSError` only; a non-UTF-8 `CLAUDE.md` raises from `_write_rules_bridge` (L192, reached at setup L1178) and from `standing_rules_drift_status` (L228); a non-UTF-8 bridge raises at L197 and L223, while `installed_rules_clobbered` (L264) uses `errors='replace'` — `marketplace/bundles/plan-marshall/skills/platform-runtime/scripts/opencode_runtime.py`
- OBSERVED: `standing_rules_drift_status` returns `drift False / baseline_missing` for a non-stub bridge (L218-219); `_write_rules_bridge` replaces it with the stub (L193-201); setup reports `bridge_written True`, `bridge_drift False` (L1177-1178); the hash comparison (L231-236) cannot see a hand-edited body — same file
- OBSERVED: `opencode-rules.md` L60 claims "a setup that rewrote the bridge never reports a clean bridge" — `marketplace/bundles/plan-marshall-opencode/skills/target-rules/standards/opencode-rules.md`
- OBSERVED: `target-rules/SKILL.md` says `bash` (L15, L28), `task` (L19, L35) and the mtime drift sentence (L34); `opencode.adoc` carries map notation at L183, L201, L206, L216, L221, L224, a stale `marshal.json` write claim at L247 and a missing test at L399 — read by the leaf on 2026-11-09
- OBSERVED: `plan-marshall/workflow/execution.md` L178 already says `subagent` and is clean
- OBSERVED: `test_no_bundle_standard_names_the_opencode_subagent_tool_as_task` globs `*/skills/*/standards/*.md` (L61) with the needle ``OpenCode `task` `` (L63) — `test/marketplace/targets/opencode/test_opencode2_dispatch_shape.py`
- OBSERVED: `target_context.py` orders antigravity, opencode, claude (L150-154) and `detect_target_from_env` returns the first hit (L179-181); `test_target_context.py` sets one signal at a time (L99-112) and derives the cleared set from `TARGET_ENV_SIGNALS` (L49)
- HYPOTHESIS: no other caller of `standing_rules_drift_status` depends on the `baseline_missing` answer for a non-stub bridge — enumerate the callers before changing it (verify-at-outline, D2)
- Verify-first clause (D2): read the callers of `standing_rules_drift_status` and decide whether setup computes the verdict from the write or the drift status changes; record why.

## Expected Surface

- OBSERVED: `marketplace/bundles/plan-marshall/skills/platform-runtime/scripts/opencode_runtime.py` — `_baseline_text`, `_write_rules_bridge`, `standing_rules_drift_status`, setup's bridge verdict (D1, D2)
- OBSERVED: `marketplace/bundles/plan-marshall-opencode/skills/target-rules/SKILL.md` (D3)
- OBSERVED: `marketplace/bundles/plan-marshall-opencode/skills/target-rules/standards/opencode-rules.md` — L60 (D2)
- OBSERVED: `doc/developer/opencode.adoc` — L183, L201, L206, L216, L221, L224, L247, L399 (D3)
- OBSERVED: `test/plan-marshall/platform-runtime/test_opencode_runtime.py` — next to L1953-1963 and L2052-2086 (D1, D2)
- OBSERVED: `test/marketplace/targets/opencode/test_opencode2_dispatch_shape.py` (D4)
- OBSERVED: `test/plan-marshall/script-shared/test_target_context.py` — `TestCascadeTiers` (D4)
- HYPOTHESIS: `marketplace/bundles/plan-marshall/skills/script-shared/scripts/target_context.py` — read only (verify-at-outline) (D4)

## Dependencies and Sequencing

- Depends on: PLAN-LB-48 (shipped, `148558aa1`); PLAN-LB-64 (shipped) gave the bridge its separate file.
- Overlaps with: PLAN-LB-134 on `opencode_runtime.py` and `test_opencode_runtime.py` (different functions; see that spec). Sequence or accept the overlap prompt.
- Adjacent to: the Antigravity bridge (PLAN-LB-136 D2), whose helper reuse is decided there; `.opencode/plugin/guard.js` (not edited).

## Hand-Off Command

```text
/plan-marshall-runbook-lane plan=.plan/orchestrator/live-blockers/plans/PLAN-LB-135-opencode-bridge-and-sweep.md
```

## Write-Boundary

The plan implementing this spec touches only its own repository source and tests. It creates
and edits NO file under `.plan/orchestrator/` other than its own
`inbox/{sender}-{seq}` message — the orchestrator owns every other ledger write — and reports
its outcome through its PR and its inbox message. The inbox exception's qualifiers and the
sole sanctioned write mechanism are stated in
`persona-plan-orchestrator/standards/orchestration-model.md` § Ledger Write-Boundary.
