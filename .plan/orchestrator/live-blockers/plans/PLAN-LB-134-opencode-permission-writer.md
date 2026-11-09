# PLAN-LB-134: The OpenCode 2 permission writer keeps the effect it reports, reports every failed write, and its readers agree

epic: live-blockers
workstream: WS-04

> Staged plan spec — one shippable unit of work, ready for `/plan-marshall-runbook-lane` hand-off.
> Lives at `plans/PLAN-LB-134-opencode-permission-writer.md` and is queued as one row file, `queue/PLAN-LB-134.json`,
> in the epic ledger. The orchestrator EMITS the command below; it never launches the plan inline.
> This spec is SELF-SUFFICIENT: the emitted command is a one-line pointer and carries no
> brief, so every per-plan carry is authored here and nowhere else.
> See `persona-plan-orchestrator/standards/orchestration-model.md` for the tier and
> hand-off contract.

> Regrouped on the operator's word of 2026-11-09 from the permission-writer half of PLAN-LB-83 (D1 to D3 and D5 there), which the
> adversarial analysis of PLAN-LB-48 (#1830, `148558aa1`) staged. Every claim was re-grounded against `main` at `9cd644892` by a
> read-only leaf on 2026-11-09; only PLAN-LB-86 (`d420ba879`, session and metrics paths) touched the file since the old spec, and
> nothing in these areas shipped. **Each deliverable is its own outline deliverable, and each Done-when is its own success
> criterion. Do not merge them.** Every Done-when below fails at `9cd644892` unless it says "holds at". No Sonar. No token or
> measurement work.

## Objective

OpenCode 2 evaluates an ordered `permissions` list, last match wins. The tool that writes it can still make a requested rule win by
moving it past a more specific later rule and reporting success; it does not know OpenCode 2's own tool name `shell`; it writes a
`subagent` key an OpenCode 1 map does not know; and an unparsable `opencode.json` is overwritten with `{error, permissions}`. A failed
list write is reported as success by setup, `permission fix` crashes on an OpenCode 2 file, and the two deny parsers disagree on a
hybrid file. This plan makes the writer keep its promise and every failure visible, and settles whether the emitted catch-all rules
can override a global deny.

## Deliverables

1. **The rule writer keeps the effect it reports and knows OpenCode 2's tool name.**
   - `_upsert_permission_rule` / `_move_rule_to_end` (`opencode_runtime.py`) never make a requested rule win by moving past a later,
     more specific rule with a different effect that the caller did not ask to change: when the requested effect cannot be made
     effective without changing that more specific outcome, the write returns a named conflict and moves nothing.
   - `to_opencode_grant` maps the bare tool `shell` to the shell catch-all (category `bash`, resource `*`), so `deny(shell)` is a deny
     of every shell command and not of the literal command `shell`.
   - An OpenCode 1 map write (`permission configure`, `permission fix` ensure and remove, `tools-permission-fix` `cmd_ensure`) maps a
     `subagent` grant to the map's `task` key and never writes a `subagent` key; a bare `task` grant is already correct and stays so.
   - Verify first: whether OpenCode 2 evaluates a rule whose `action` is the wildcard `*`. `_matching_rules` and `_rule_exists`
     require an exact action; the repository's own evaluator (`test_opencode_root_config.py`) does too, and `doc/developer/opencode.adoc`
     is silent. Only the installed binary settles it. If it evaluates the wildcard, the effective-effect check must; if it does not,
     record the evidence and the version and change nothing.

   *Done when:* each of these fails at `9cd644892`:
   - rules `[{shell,*,allow},{shell,"git push --force *",deny},{shell,"git *",ask}]` given `permission_fix('project','ensure',['ask(git push *)'],False)`
     (and again with `allow(git push *)`) end with `git push --force x` still `deny`, or the write returns a conflict and the file is
     unchanged; at `9cd644892` the rule is moved to the end and the result is `ask` or `allow` with `added: 1`;
   - `to_opencode_grant('deny(shell)') == ('bash','*','deny')`;
   - a file `{"permission":{"bash":{}}}` given `ensure ['subagent']` ends with a `task` key and no `subagent` key (the same through `tools-permission-fix` `cmd_ensure`);
   - the wildcard-action question carries a recorded source and version.

   And these hold at `9cd644892` and must keep holding: `test_a_requested_deny_outranks_a_broader_earlier_allow`
   (`test_opencode_permission_shape.py`); a bare `task` grant on a map file writes `task`.

2. **A failed write and an unreadable input are reported, never swallowed or written over.**
   - A project `opencode.json` that does not parse is never loaded as `{"error": …}` and saved back with a `permissions` list beside
     it. `permission fix` ensure (`opencode_runtime.py`), `tools-permission-fix` `cmd_ensure` and `cmd_ensure_executor` return the
     error and write nothing. `permission_load_settings` returns an error for a non-UTF-8 file as well (it catches only `OSError` and
     `JSONDecodeError` today).
   - `permission_ensure_defaults` reports a failed list or map save as an error (`applied: False` with no error key today);
     `project_initial_setup` surfaces the result instead of discarding it, including the error for an unparsable file;
     `permission_ensure_wildcards` does not wrap a failed result in a success envelope; `tools-permission-fix` `cmd_apply_fixes` reads
     `defaults['applied']`.
   - `tools-permission-fix` `cmd_add` and `cmd_remove` have an OpenCode 2 and an OpenCode 1 branch (delegating to the upsert and remove
     helpers the writer already has) or refuse with a named reason: an OpenCode 2 list no longer raises `TypeError` and an OpenCode 1
     map no longer raises `KeyError`; a missing project file is not turned into a skeleton and then a crash.
   - `installed_opencode_version` ignores the output of a non-zero exit, so a failing `opencode --version` whose stderr carries
     `Node 20.11` is "not checkable" and never read as OpenCode major 20.

   *Done when:* each of these fails at `9cd644892`:
   - `not json` in `opencode.json` followed by `permission_fix('project','ensure',['deny(git push *)'],False)` returns an error and the file's bytes are unchanged (the same for `cmd_ensure` and `cmd_ensure_executor` with `force_opencode`);
   - a non-UTF-8 `opencode.json` returns the loader's error instead of raising `UnicodeDecodeError`;
   - `permission_ensure_defaults` over a list file whose save is stubbed to fail returns an `error` key, and `project_initial_setup` reports it;
   - `cmd_add` over an OpenCode 2 list file with `force_opencode` returns a result (and `cmd_remove`), and over a map file does not raise;
   - a stubbed `opencode --version` exiting 1 with empty stdout and `Node 20.11 required` on stderr yields major `None` and the health consumer says "not checkable" (the stub helper in `test_opencode_runtime.py` gains `stderr` and `returncode` parameters).

3. **The two deny readers agree.**
   - `_deny_rules` reads only the list when a `permissions` list exists, ignores the map of a hybrid file and never reads
     `agent` / `agents`; `_deny_rules_from_config` reads the list, the map and the agent scopes. One reader is the source for both, with
     one rule for a missing action, so the permission `analyze` and the permission `health` check cannot disagree.

   *Done when:* each of these fails at `9cd644892`:
   - `{'permissions':[{shell,*,allow}],'permission':{'bash':{'rm *':'deny'}}}` yields the same deny set from both entry points, including `rm *`;
   - `{'permissions':[],'agents':{'b':{'permissions':[{shell,'gh *',deny}]}}}` yields `gh *` from both.

4. **The emitted catch-alls cannot override a global deny — or the plan records that they cannot.**
   - Verify first: in which order OpenCode 2 evaluates the global `permissions`, the project `permissions` and an agent's. The repository's
     own model (`opencode.adoc` L130-134, `test_opencode_root_config.py` L46) is global, then project, then agent, last match wins, and
     `opencode.adoc` L206 and L221 say an agent's `"*": "ask"` overrides a global deny. Under that model `transform_agent_frontmatter`
     (`marketplace/targets/opencode/frontmatter.py`) emits `{shell,*,allow}` for every agent that declares Bash, which overrides a global
     `gh *` or `rm *` deny (guard rule R2 still blocks `rm` at host level; no rule covers `gh`), and `_opencode2_skeleton` puts
     `{shell,*,ask}` first, downgrading a global deny to ask. The docstring of `transform_agent_frontmatter` says it "emits no
     catch-all of its own", which its code contradicts.
   - If the order is confirmed against the binary: an emitted agent carries no shell catch-all allow, the skeleton carries no shell
     catch-all that sorts after a global deny, and the docstring is true. If the binary evaluates agent and project rules BEFORE the
     global ones, record the source and version, correct the docs that say otherwise, and change nothing in the emitters. Whether the
     binary also merges agent-markdown frontmatter permissions with `opencode.json` `agents.*` is part of the same record.

   *Done when:* the evaluation order has a recorded source and version; and, if confirmed, each of these fails at `9cd644892`: an
   emitted Bash-declaring agent's permissions contain no `{shell,*,allow}`, and a new project skeleton contains no `{shell,*,*}` rule
   that sorts after a global deny.

Split guard: four deliverables, all in the OpenCode permission family (`opencode_runtime.py`, `permission_fix.py`, the OpenCode
emitter and their tests). D4 may resolve to "no change", which is a recorded outcome. If the outline finds D2 growing past the
`tools-permission-fix` surface, D2 splits off first.

## Standing Constraints

- Settle each HYPOTHESIS and each verify-first clause first. A refuted claim is dropped from its deliverable, not worked around, and
  the PR says so.
- A write that cannot be made safely returns a named reason and writes nothing; it never reports success for an effect it did not
  produce.
- Rules are evaluated last-match-wins; no change may reorder rules the caller did not ask to change.
- Documentation states the current behaviour; no comment or document describes a change or the old behaviour.
- Tests state their purpose, use the `PLAN_MARSHALL_HOME` fixture, are shown red at `9cd644892` where a Done-when says so, and a test
  that fails only by a monkeypatched internal is not a proof. Counts come from an enumeration, not a hand list.
- Executor regeneration only if a verb or a flag is added; if one is, the landing says so.
- No token or measurement work. No Sonar.

## Claim Labels

- OBSERVED: `_move_rule_to_end` (L522-526) and `_upsert_permission_rule` (L529-565) move a requested rule to the end of the list whenever
  its effective effect differs from the requested one, without regard to a later more specific rule. The leaf's counter-example:
  `ensure deny(git push *)` is safe because a `git *` ask sits after it; `ensure ask(git push *)` or `allow(git push *)` turns a
  `deny` of `git push --force x` into `ask` or `allow` — `marketplace/bundles/plan-marshall/skills/platform-runtime/scripts/opencode_runtime.py`
- OBSERVED: `to_opencode_grant` (L296-351) has no `shell` in its bare-key tuple (L336-349); `deny(shell)` falls through to `('bash','shell','deny')` — same file
- OBSERVED: the OpenCode 1 map branches write the category from `to_opencode_grant` without `_permission_action`: `permission_configure` (L1560-1576), `permission_fix` ensure (L1770-1774) and remove (L1800), and `permission_fix.py` `cmd_ensure` (L454-474); a bare `task` is correct, a bare `subagent` is not
- OBSERVED: `permission_load_settings` returns `{'error':…}` for unparsable JSON and catches only `OSError` and `JSONDecodeError` (L2251-2260); `permission_fix` (L1688-1690) has no error check; `permission_fix.py` `cmd_ensure` (L378-425) and `cmd_ensure_executor` (L1393-1429) pass the error through `load_settings_path` (`permission_common.py` L166-177)
- OBSERVED: `permission_ensure_defaults` returns `applied: bool(… and saved)` with no error key (list branch L2295-2316, map branch L2343-2353); `project_initial_setup` discards the result (L1171); `permission_ensure_wildcards` wraps a failed result in `toon_success` (L1975-1976); `permission_fix.py` `cmd_apply_fixes` ignores `defaults['applied']` (L229-245)
- OBSERVED: `permission_fix.py` `cmd_add` (L311-336) and `cmd_remove` (L344-368) index `settings['permissions']['allow']` with no target branch; an OpenCode 2 list raises `TypeError`, an OpenCode 1 map raises `KeyError`
- OBSERVED: `installed_opencode_version` (L577-597) never reads `returncode` and takes `stdout or stderr`; the health consumer (L2755-2767) reports a version mismatch
- OBSERVED: `_deny_rules` (L615-640) and `_deny_rules_from_config` (L724-767) differ on a hybrid file, on `agent` / `agents` scopes and on the missing-action default (`''` against `'bash'`)
- OBSERVED: `transform_agent_frontmatter` emits `{action, resource:"*", effect:allow}` for every mapped tool (L348-353), `Bash` maps to `shell` in `marketplace/targets/opencode/mapping.json`; `_opencode2_skeleton` emits `{shell,*,ask}` first (L600-612)
- HYPOTHESIS: OpenCode 2 evaluates global rules before project and agent rules, so the emitted catch-alls override a global deny — confirm in the installed binary and record the version (verify-at-outline, D4)
- HYPOTHESIS: OpenCode 2 evaluates a rule with a wildcard `action` — confirm in the installed binary (verify-at-outline, D1)
- Verify-first clause (D1): reproduce the counter-example at `9cd644892` as a fixture before editing, and decide conflict-versus-keep-in-place as the writer's rule; record why.
- Verify-first clause (D4): record the binary version and the evaluation order before touching either emitter.

## Expected Surface

- OBSERVED: `marketplace/bundles/plan-marshall/skills/platform-runtime/scripts/opencode_runtime.py` — rule writer, `to_opencode_grant`, map branches, loader, ensure-defaults, ensure-wildcards, setup, version probe, deny parsers (D1, D2, D3)
- OBSERVED: `marketplace/bundles/plan-marshall/skills/tools-permission-fix/scripts/permission_fix.py` — `cmd_add`, `cmd_remove`, `cmd_ensure`, `cmd_ensure_executor`, `cmd_apply_fixes` (D1, D2)
- HYPOTHESIS: `marketplace/bundles/plan-marshall/skills/tools-permission-doctor/scripts/permission_common.py` — `load_settings_path`, only if the loader error is fixed there (verify-at-outline) (D2)
- HYPOTHESIS: `marketplace/targets/opencode/frontmatter.py` — only if D4 confirms the order (verify-at-outline) (D4)
- HYPOTHESIS: `doc/developer/opencode.adoc` — the evaluation-order statements at L130-134, L206 and L221, only if D4 records a different order (verify-at-outline) (D4)
- OBSERVED: `test/plan-marshall/platform-runtime/test_opencode_permission_shape.py` (D1, D2, D3)
- OBSERVED: `test/plan-marshall/platform-runtime/test_opencode_runtime.py` — setup, the version stub (D2)
- OBSERVED: `test/plan-marshall/tools-permission-fix/test_runtime_dsl.py` (D1, D2)
- OBSERVED: `test/plan-marshall/tools-permission-fix/_permission_fix_fixtures.py` — `force_opencode` (D1, D2)
- HYPOTHESIS: `test/marketplace/targets/opencode/test_frontmatter.py` and `test/plan-marshall/platform-runtime/test_opencode_root_config.py` — only if D4 confirms the order (verify-at-outline) (D4)

## Dependencies and Sequencing

- Depends on: PLAN-LB-48 (shipped, `148558aa1`); PLAN-LB-86 (shipped, `d420ba879`) is already in the base.
- Overlaps with: PLAN-LB-135 on `opencode_runtime.py` and `test_opencode_runtime.py` (different functions: this plan owns the permission writer, the loader, the version probe and the deny parsers; PLAN-LB-135 owns the bridge and setup's bridge verdict) — both edit `project_initial_setup`'s neighbourhood, so sequence them or accept the overlap prompt. PLAN-LB-136 (Antigravity) shares `platform-runtime/scripts/` but no file.
- Adjacent to: the root `opencode.json` (a guarded operator file; its OpenCode 1 `permission.bash` map beside the list is not edited here) and `.opencode/plugin/guard.js` (not edited).

## Hand-Off Command

```text
/plan-marshall-runbook-lane plan=.plan/orchestrator/live-blockers/plans/PLAN-LB-134-opencode-permission-writer.md
```

## Write-Boundary

The plan implementing this spec touches only its own repository source and tests. It creates
and edits NO file under `.plan/orchestrator/` other than its own
`inbox/{sender}-{seq}` message — the orchestrator owns every other ledger write — and reports
its outcome through its PR and its inbox message. The inbox exception's qualifiers and the
sole sanctioned write mechanism are stated in
`persona-plan-orchestrator/standards/orchestration-model.md` § Ledger Write-Boundary.
