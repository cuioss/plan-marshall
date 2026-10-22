# PLAN-LB-83: The OpenCode 2 permission writer keeps its promises, the bridge reports what it did, and no OpenCode surface names the OpenCode 1 shape

epic: live-blockers
workstream: WS-04

> Staged plan spec — one shippable unit of work, ready for `/plan-marshall-runbook-lane` hand-off.
> Lives at `plans/PLAN-LB-83-lb-48-completion.md` and is queued as one row file, `queue/PLAN-LB-83.json`,
> in the epic ledger. The orchestrator EMITS the command below; it never launches the plan inline.
> This spec is SELF-SUFFICIENT: the emitted command is a one-line pointer and carries no
> brief, so every per-plan carry is authored here and nowhere else.
> See `persona-plan-orchestrator/standards/orchestration-model.md` for the tier and
> hand-off contract.

> Staged from the adversarial landing analysis of PLAN-LB-48 (#1830, `148558aa1`),
> `landings/PLAN-LB-48.md` § Code defects. Priority is **medium**: PLAN-LB-48 met every written Done-when and the
> OpenCode 2 shape now ships, but the permission writer it moved to a list can still produce the wrong effect for
> a rule it reports as added, the bridge it rewrote can report "no drift" for a file it just replaced, and the
> sweep that was to remove the OpenCode 1 tool names left five lines behind. **Each deliverable is its own
> outline deliverable, and each Done-when is its own success criterion. Do not merge them.** A Done-when says
> "fails at `148558aa1`" only where the behaviour is new at that sha; a clause that already holds says "holds at
> `148558aa1`". A Done-when is never labelled "holds at" while a claim it rests on is still a HYPOTHESIS below.

## Objective

PLAN-LB-48 moved the OpenCode target and the permission tooling to OpenCode 2's ordered `permissions` list.
The list is evaluated last-match-wins, so the tool that writes it must keep the effect it reports: it can
still move a rule past a more specific later rule, it does not recognise OpenCode 2's own tool name `shell`,
and every failed write or unreadable input is not reported. The standing-rules bridge reports no drift for a
bridge it just rewrote and crashes on a baseline that is not UTF-8. Five lines of the OpenCode target rules
still name the OpenCode 1 tools or the mtime drift check, and the guard test that was to find them looks at
the wrong glob. This plan closes those, and settles whether the emitted catch-alls can override a global deny.

## Deliverables

1. **The rule writer keeps the effect it reports and knows OpenCode 2's tool name.**
   - Skills: pm-plugin-development:plugin-architecture, pm-plugin-development:plugin-script-architecture, pm-dev-python:python-core, plan-marshall:ref-code-quality, pm-dev-python:pytest-testing, plan-marshall:persona-module-tester
   - Persona: plan-marshall:persona-implementer
   - `_upsert_permission_rule` / `_move_rule_to_end` (`opencode_runtime.py`) never make a requested rule win by
     overriding a later, more specific rule that the caller did not ask to change: when the requested effect
     cannot be made effective without changing a more specific outcome, the write reports that conflict
     (a named reason, nothing silently moved past it) instead of reporting success.
   - `to_opencode_grant` treats `shell` as the bare tool key it is, so `deny(shell)` is a deny of the shell
     catch-all and not a deny of the literal command `shell`.
   - Decide at outline, and record, whether a rule with a wildcard `action` (`*`) is honoured by the
     effective-effect check (`_effective_rule_effect`, `_rule_exists`); if OpenCode 2 evaluates it, the check
     must too.
   - A `task` or `subagent` grant written to an OpenCode 1 map file is not written as a `subagent` key the map
     shape does not know.

   *Done when:* each of these fails at `148558aa1`:
   - the list `[{shell,*,allow},{shell,"git push --force *",deny},{shell,"git *",ask}]` given `ensure
     deny(git push *)` ends with `git push --force x` still denied, and the write reports the conflict;
   - `to_opencode_grant("deny(shell)")` returns the shell catch-all with effect deny;
   - a list rule `{action:"*",resource:"*",effect:"deny"}` after an allow makes `_rule_exists` for the allow
     false (only if the outline settles that OpenCode 2 evaluates it);
   - an OpenCode 1 map file given a `subagent` grant ends with no `subagent` key.

2. **Every failed write and unreadable input is reported, never swallowed or written over.**
   - Skills: pm-plugin-development:plugin-architecture, pm-plugin-development:plugin-script-architecture, pm-dev-python:python-core, plan-marshall:ref-code-quality, pm-dev-python:pytest-testing, plan-marshall:persona-module-tester
   - Persona: plan-marshall:persona-implementer
   - A project `opencode.json` that does not parse is never loaded as `{"error": …}` and saved back with a
     `permissions` list beside it: `permission fix` / `ensure` returns the error and writes nothing
     (`opencode_runtime.py` L1401-1403, `permission_fix.py` L378-395).
   - `ensure-defaults` reports a failed list write as an error, and `project_initial_setup` surfaces it
     instead of ignoring the result.
   - `permission_fix.py` `cmd_add` and `cmd_remove` have an OpenCode branch (or refuse with a named reason):
     an OpenCode 2 file no longer raises `TypeError`.
   - `installed_opencode_version` ignores output of a non-zero exit, so a failing `opencode --version` whose
     stderr carries a `N.M` is not read as the OpenCode major.
   - `analyze`'s deny parser and the one `permission` health uses agree on a hybrid file (list and map), and
     both read `agents.*.permissions`.

   *Done when:* each of these fails at `148558aa1`:
   - `permission fix ensure` over a malformed `opencode.json` returns an error and the file's bytes are unchanged;
   - an `ensure-defaults` whose list write fails returns an error and `project_initial_setup` reports it;
   - `cmd_add` over an OpenCode 2 `permissions` list returns a result, not a `TypeError`;
   - a stubbed `opencode --version` exiting non-zero with `Node 20.11` on stderr reports "not checkable";
   - `analyze` over a hybrid file reports the map's deny rules.

3. **The bridge reports what it did and survives any baseline bytes.**
   - Skills: pm-plugin-development:plugin-architecture, pm-plugin-development:plugin-script-architecture, pm-dev-python:python-core, plan-marshall:ref-code-quality, pm-dev-python:pytest-testing, plan-marshall:persona-module-tester
   - Persona: plan-marshall:persona-implementer
   - `_baseline_text` catches `UnicodeDecodeError` as well as `OSError`, so a `CLAUDE.md` with a non-UTF-8 byte
     is an unreadable baseline (the bridge is kept) and no longer crashes `project_initial_setup`.
   - Setup reports `bridge_drift` from what the write did: a bridge that setup replaces with the stub (the
     baseline was deleted) or rewrites because its body no longer equals the generated one (a hand edit with
     the marker and hash intact) is reported as drift, never `in_sync` / `False`
     (`standing_rules_drift_status` L199-200, `_write_rules_bridge` L174-184, the verdict at L975-976).
   - The unreadable-baseline test uses a real unreadable file (a non-UTF-8 `CLAUDE.md`), not a monkeypatch of
     the unit's own `_baseline_text`.

   *Done when:* each of these fails at `148558aa1`:
   - setup over a `CLAUDE.md` containing a latin-1 byte completes and leaves an existing bridge unchanged;
   - setup after `CLAUDE.md` is deleted reports `bridge_drift: true` and the stub is written;
   - setup over a bridge whose body was hand-edited (marker and hash intact) reports `bridge_drift: true`;
   - the unreadable-baseline test passes only when a real non-UTF-8 file is used (the monkeypatched version is removed).

4. **No OpenCode-side surface names the OpenCode 1 shape, and the guard test finds the ones it missed.**
   - Skills: pm-plugin-development:plugin-architecture, pm-documents:ref-asciidoc, pm-dev-python:pytest-testing, plan-marshall:persona-module-tester
   - Persona: plan-marshall:persona-documenter
   - `plan-marshall-opencode/skills/target-rules/SKILL.md` names the OpenCode 2 tools (`shell`, `subagent`)
     where it says `bash` and `task` (L15, L19, L28, L35), and its drift sentence describes the content hash,
     not "a baseline newer than the bridge" (L34).
   - `doc/developer/opencode.adoc` role matrix row "Git write" describes the `*` fallback as a list rule, not
     as `agents.build.permissions` map notation.
   - `test_no_bundle_standard_names_the_opencode_subagent_tool_as_task` covers the OpenCode target-rules
     skill and `plan-marshall/workflow/execution.md` as well as `*/skills/*/standards/*.md`.
   - `test_target_context.py` gains a precedence test (antigravity before opencode before claude) that does
     not read `TARGET_ENV_SIGNALS`, so reordering or dropping a signal fails it; the matrices that now derive
     from that registry are not edited here.

   *Done when:* each of these fails at `148558aa1`:
   - the widened guard test fails on `target-rules/SKILL.md` at `148558aa1`;
   - a doc test asserts `target-rules/SKILL.md` carries `shell` and `subagent` and no OpenCode `bash` / `task`
     instruction and describes the hash drift;
   - the precedence test fails when `TARGET_ENV_SIGNALS` is reordered.

5. **The emitted catch-alls cannot override a global deny — or the plan records that they cannot.**
   - Skills: pm-plugin-development:plugin-architecture, pm-plugin-development:plugin-script-architecture, pm-dev-python:python-core, plan-marshall:ref-code-quality, pm-dev-python:pytest-testing, plan-marshall:persona-module-tester
   - Persona: plan-marshall:persona-implementer
   - Verify first (see the Claim Labels): in which order OpenCode 2 evaluates the global `permissions`, the
     project `permissions` and an agent's `permissions`. If an agent's or project's rules are evaluated AFTER
     the global ones, then (a) `frontmatter.py` must not emit `{shell,*,allow}` for an agent, and (b)
     `_opencode2_skeleton` must not put `{shell,*,ask}` first in a new project config, because either one
     overrides a global `rm *` / `gh *` deny. If they are evaluated before, record the evidence and change
     nothing.

   *Done when:* the verify-first clause is settled with a recorded source, and, if confirmed, each of these
   fails at `148558aa1`: an emitted agent carries no shell catch-all allow, and a new project skeleton carries
   no shell catch-all that sorts after a global deny.

Split guard: five deliverables, all OpenCode-only, all in one file family (`opencode_runtime.py`, its tests and
the OpenCode target rules). Proceeding unsplit: D5 may resolve to "no change", which is a recorded outcome, and
D4 is a documentation sweep with no new logic.

## Claim Labels

- OBSERVED: `_move_rule_to_end` moves a rule to the END of the list whenever `_effective_rule_effect` differs from the requested effect, with no regard for later more specific rules — `marketplace/bundles/plan-marshall/skills/platform-runtime/scripts/opencode_runtime.py` L503-546 (read by the orchestrator).
  - verdict: corroborated | checked_at: d60b36f8d | by: live-blockers/analyze | rescoped: n/a | evidence: Unchanged by #1835 (+1 shift): _move_rule_to_end at opencode_runtime.py L518-522, called from _upsert_permission_rule L525-561 (L544-545, L559-560) when the effective effect differs (cited L503-546).
- OBSERVED: `to_opencode_grant`'s bare-key tuple lists `bash` and `task` and `subagent` but not `shell`, so `deny(shell)` falls through to `('bash', 'shell', 'deny')` — `opencode_runtime.py` L317-332 (read by the orchestrator).
  - verdict: corroborated | checked_at: d60b36f8d | by: live-blockers/analyze | rescoped: n/a | evidence: Bare-key tuple at opencode_runtime.py L332-345 (no shell), ('bash', perm, action) fall-through at L347 (cited L317-332).
- OBSERVED: `_baseline_text` catches `OSError` only, and `standing_rules_drift_status` returns `{'drift': False, 'reason': 'baseline_missing'}` while `_write_rules_bridge` replaces an existing bridge with the stub when the baseline is missing — `opencode_runtime.py` L121-126, L174-184, L199-200 (read by the orchestrator).
  - verdict: corroborated | checked_at: d60b36f8d | by: live-blockers/analyze | rescoped: n/a | evidence: _baseline_text L136-141 catches OSError only; _write_rules_bridge L186-199 keeps a bridge only when the baseline is_file (L189) else overwrites with the stub; drift returns baseline_missing at L214-215 (cited L121-126/L174-184/L199-200).
- OBSERVED: `plan-marshall-opencode/skills/target-rules/SKILL.md` still says `bash` (L15, L28), `task` (L19, L35) and "a baseline newer than the bridge" (L34) (read by the orchestrator).
- OBSERVED: `test_no_bundle_standard_names_the_opencode_subagent_tool_as_task` globs `*/skills/*/standards/*.md` for the literal ``OpenCode `task` `` (`test/marketplace/targets/opencode/test_opencode2_dispatch_shape.py`; reported by the corroboration, not re-read).
- OBSERVED: the unreadable-baseline test monkeypatches `_baseline_text` to `None` — `test/plan-marshall/platform-runtime/test_opencode_runtime.py::test_an_unreadable_baseline_never_overwrites_the_bridge` (reported by the corroboration, not re-read).
- HYPOTHESIS: a malformed `opencode.json` is loaded as `{'error': …}` and `create=True` saves `{error, permissions}` over it — confirm at `opencode_runtime.py` L1401-1403 and `permission_fix.py` L378-395 (verify-at-outline).
  - verdict: corroborated | checked_at: d60b36f8d | by: live-blockers/analyze | rescoped: n/a | evidence: opencode_runtime.py side holds: permission_load_settings returns {error: ...} at L2142-2143; permission fix runs load then _permission_rules(create=True) at L1571-1573 with no error guard (cited L1401-1403). The permission_fix.py half is outside #1835.
- HYPOTHESIS: `ensure-defaults` returns `applied: False` with no error when the list write fails, and `project_initial_setup` ignores the result — confirm at `opencode_runtime.py` L969, L2018-2027 (verify-at-outline).
  - verdict: corroborated | checked_at: d60b36f8d | by: live-blockers/analyze | rescoped: n/a | evidence: project_initial_setup discards the result at L1081 (cited L969); permission_ensure_defaults list branch L2188-2199 returns applied=False with no error key when save fails (cited L2018-2027).
- HYPOTHESIS: `cmd_add` / `cmd_remove` have no OpenCode branch and raise `TypeError` on a list — confirm at `permission_fix.py` L314, L347 (verify-at-outline).
- HYPOTHESIS: `installed_opencode_version` ignores `returncode` — confirm at `opencode_runtime.py` L571-578 (verify-at-outline).
  - verdict: corroborated | checked_at: d60b36f8d | by: live-blockers/analyze | rescoped: n/a | evidence: installed_opencode_version at L573-593 never reads completed.returncode and parses stdout/stderr regardless (cited L571-578).
- HYPOTHESIS: the two deny parsers disagree on a hybrid file — confirm at `opencode_runtime.py` `_deny_rules` (L596-608) against `_deny_rules_from_config` (L688-731) (verify-at-outline).
  - verdict: corroborated | checked_at: d60b36f8d | by: live-blockers/analyze | rescoped: n/a | evidence: _deny_rules L611-636 returns only the list's denies when a permissions list exists and skips the map; _deny_rules_from_config L703+ consumes the list, the map and agent scopes, so a hybrid file diverges (cited L596-608/L688-731).
- HYPOTHESIS: a rule with a wildcard `action` is invisible to the effective-effect check — confirm at `opencode_runtime.py` L461-476, and settle whether OpenCode 2 evaluates such a rule (verify-at-outline).
  - verdict: corroborated | checked_at: d60b36f8d | by: live-blockers/analyze | rescoped: n/a | evidence: Code half: _matching_rules L487-492 requires rule.get(action) == action exactly, so an action * rule never reaches _effective_rule_effect at L495-498 (cited L461-476); whether OpenCode 2 evaluates such a rule is a binary question and stays verify-at-outline.
- HYPOTHESIS: a map-shaped file given a `subagent` grant gets a `subagent` map key — confirm at `opencode_runtime.py` L1464-1487 (verify-at-outline).
  - verdict: corroborated | checked_at: d60b36f8d | by: live-blockers/analyze | rescoped: n/a | evidence: Permission fix map branch L1634-1657 writes perm[cat]=act with cat=subagent from to_opencode_grant (L1654-1656; cited L1464-1487); permission configure's map branch L1444-1458 does the same.
- HYPOTHESIS (deliverable 5): OpenCode 2 evaluates global rules before the agent's and the project's, so an agent `{shell,*,allow}` (`frontmatter.py` L339-344) and a skeleton `{shell,*,ask}` (`opencode_runtime.py` L591) override a global deny — confirm in the OpenCode 2 binary's rule evaluation (the order `opencode.adoc` models for the root config) before changing either (verify-at-outline).
  - verdict: corroborated | checked_at: d60b36f8d | by: live-blockers/analyze | rescoped: n/a | evidence: Only the code reference depends on #1835: the {shell,*,ask} skeleton is now at opencode_runtime.py L606 (cited L591; _opencode2_skeleton L596-608); the binary evaluation order and frontmatter.py are outside #1835 and stay verify-at-outline.
- Verify-first clause (deliverable 5): read the evaluation order in the installed OpenCode 2 binary and record the source and version; a refutation closes deliverable 5 as "no change" and loops back to nothing else.

## Expected Surface

- OBSERVED: `marketplace/bundles/plan-marshall/skills/platform-runtime/scripts/opencode_runtime.py` — rule writer, `to_opencode_grant`, bridge, setup, ensure-defaults, version probe, deny parsers (D1, D2, D3, D5)
- OBSERVED: `marketplace/bundles/plan-marshall/skills/tools-permission-fix/scripts/permission_fix.py` — `cmd_add`, `cmd_remove`, ensure over a malformed file (D2)
- OBSERVED: `marketplace/bundles/plan-marshall-opencode/skills/target-rules/SKILL.md` (D4)
- OBSERVED: `doc/developer/opencode.adoc` — the "Git write" role matrix row (D4)
- OBSERVED: `test/plan-marshall/platform-runtime/test_opencode_runtime.py` (D1, D2, D3)
- OBSERVED: `test/plan-marshall/platform-runtime/test_opencode_permission_shape.py` (D1, D2)
- OBSERVED: `test/marketplace/targets/opencode/test_opencode2_dispatch_shape.py` — the guard glob (D4)
- OBSERVED: `test/plan-marshall/script-shared/test_target_context.py` — the precedence test (D4)
- HYPOTHESIS: `marketplace/targets/opencode/frontmatter.py` — only if deliverable 5 confirms the order (verify-at-outline) (D5)
- HYPOTHESIS: `test/marketplace/targets/opencode/test_opencode2_shape.py` — only if deliverable 5 confirms the order (verify-at-outline) (D5)
- HYPOTHESIS: `test/plan-marshall/tools-permission-fix/test_runtime_dsl.py` — only if `cmd_add` / `cmd_remove` gain a branch (verify-at-outline) (D2)

## Dependencies and Sequencing

- Depends on: PLAN-LB-48 (shipped, `148558aa1`).
- Overlaps with: PLAN-LB-86 (staged from the PLAN-LB-49 landing) on `opencode_runtime.py` and `test_opencode_runtime.py` (different functions: that plan owns the session and metrics paths; this one owns the permission, bridge and setup paths), PLAN-LB-84 on `opencode_runtime.py` only if that plan moves the session id read (both HYPOTHESIS entries), and PLAN-LB-79 on `test/plan-marshall/platform-runtime/`. The gate will ask. PLAN-LB-49 shipped (#1833, `3baf825e4`) and added about 222 net lines to `opencode_runtime.py` (session capture, `_per_phase_buckets`, a shared database-path resolver that now honours `OPENCODE_DB` first, which also changes which database the persisted-permission scan reads), so every line reference in this spec after about L60 has moved by roughly 12 to 180 lines: re-read each against `main` at outline.
- Adjacent to: the root `opencode.json`, which still carries an OpenCode 1 `permission.bash` map beside its `permissions` list (landed by the steward through the pre-image `ensure-defaults`, #1812) and `.opencode/plugin/guard.js`; neither is edited here, and the root file is an operator decision (guarded configuration).

## Hand-Off Command

```text
/plan-marshall-runbook-lane plan=.plan/orchestrator/live-blockers/plans/PLAN-LB-83-lb-48-completion.md
```

## Write-Boundary

The plan implementing this spec touches only its own repository source and tests. It creates
and edits NO file under `.plan/orchestrator/` other than its own
`inbox/{sender}-{seq}` message — the orchestrator owns every other ledger write — and reports
its outcome through its PR and its inbox message. The inbox exception's qualifiers and the
sole sanctioned write mechanism are stated in
`persona-plan-orchestrator/standards/orchestration-model.md` § Ledger Write-Boundary.
