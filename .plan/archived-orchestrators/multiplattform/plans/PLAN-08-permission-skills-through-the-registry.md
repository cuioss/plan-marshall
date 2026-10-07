# PLAN-08: The permission skills state intent and route through the registry

epic: multiplattform
workstream: WS-01

> Staged plan spec — one shippable unit of work, ready for `/plan-marshall` hand-off.
> This spec is SELF-SUFFICIENT: the emitted command is a one-line pointer and carries no
> brief, so every per-plan carry is authored here and nowhere else.
> Ingested from `archive/original-staged-specs/080-permission-skills-through-the-registry.md` and
> re-grounded against HEAD `2cd1a19c`. **Its premises re-derived exactly — this is the most tightly
> pre-verified spec in the epic.**

## Epic Constraints (bind every deliverable)

- **The principles bind:** no target enumeration in contracts, no wire format across the runtime boundary, no universal templating, honest no-ops. Read `../reference/principles.md`.
- **Counts and enumerations here are LEADS.** Re-derive at the moment of the claim.
- **Never edit another plan's surface**, even for an obvious adjacent fix.
- **Confirm the Expected Surface against the tree as the first action** and report any file the work needs beyond it.

## Objective

`tools-permission-doctor` and `tools-permission-fix` are **general skills that only work on Claude**,
and nothing prevents an OpenCode project from reaching them. Two defects produce that, and the second
is why the first cannot simply be fixed by rerouting.

**The direct binding.** `permission_common.py` imports `_claude_global_settings_path`,
`_claude_project_settings_path`, `_claude_project_settings_read_path`, `_load_settings`,
`_save_settings` and `ensure_default_permissions` from `claude_runtime` by name, after walking parents
to put `platform-runtime/scripts` on `sys.path`. `permission_doctor.py` imports from `claude_runtime`
the same way. So settings load/save, both path selectors, and the default-permission renderer resolve
to the Claude implementation whatever `runtime.target` says — and because the skills carry no
`targets:` filter, an unscoped component is emitted everywhere, so on an OpenCode project these write
`.claude/settings*.json`. This also fails the §6 cost bar: adding a target means editing these general
skill scripts.

**The grammar crossing, which blocks the reroute.** Routing the direct-binding calls through
`platform_runtime._REGISTRY` does not by itself make the skills target-neutral, because **the arguments
are already Claude grammar**. `permission configure` takes a raw permission list; `permission fix
--operation add|remove|ensure` takes patterns like `Bash(docker:*)`. §1 names that exact shape as a
violation — its own worked example is *"Also bad: `permission configure --permissions "Bash(…)"`"*.
Rerouting an op whose argument is Claude's DSL would require every other runtime to **parse Claude's
permission grammar** — the coupling inverted rather than removed. Alongside it, `permission_fix.py`
renders and parses that grammar directly, and `ensure_default_permissions` receives the Claude settings
**mapping** as a parameter — a return-value and argument crossing §1 forbids in both directions.

The repository already contains the shape that resolves this: `permission_web_apply` takes **domain
names**; `permission fix --operation protect-path` takes **directory paths**. Both express intent and
carry normalized data, and both were reachable without teaching any runtime a foreign grammar.

## Deliverables

1. **D1 — The crossing inventory, and the stop condition.** Enumerate, from the tree, every place the three scripts (`permission_common.py`, `permission_doctor.py`, `permission_fix.py`) either import `claude_runtime` directly or render/parse a permission-DSL string, and for each DSL site record the **intent** it expresses in one phrase. Write the result into the PR body and the inbox message **before changing any code**.
   *Done when:* the PR body and the inbox message carry the enumeration, each row naming file, symbol, and intent phrase. ⛔ **HALT the plan and report if the intents cannot be stated from the code** — if a rendered string's purpose is not recoverable by reading, the vocabulary in D2 would be invented rather than derived, and this plan's premise has failed. Do **not** fall back to inventing intents from the string shapes: that reproduces the grammar coupling inside the fix.
2. **D2 — A semantic vocabulary for the crossings D1 found.** For each intent, provide a target-neutral way to express it, following the two in-tree precedents. The naming rule, so this needs no mid-run decision: **name what the caller wants, never what Claude writes** — an argument is a domain, a path, a skill name, an executor identity, never a `Tool(pattern)` string. Where an intent is genuinely Claude-only, that is a legitimate finding: record it as a candidate for a `no-op` on other targets, and do not invent a neutral spelling for it.
   *Done when:* no argument to, and no return value from, a `platform-runtime` permission operation is a permission-DSL string, verified by re-reading the operation signatures and the router; and `contract.md` documents each operation by its intent.
3. **D3 — The skills route through the registry.** `permission_common.py` and `permission_doctor.py` resolve their runtime through `platform_runtime`'s registry instead of importing `claude_runtime`, and the `sys.path` parent-walk that exists to reach `claude_runtime` goes with it. The Claude settings **mapping** stops crossing into `ensure_default_permissions` as a parameter.
   *Done when:* a `claude_runtime` search over all three scripts returns nothing, re-derived at the moment of the claim; and an OpenCode-target project driving each subcommand gets either a real result or an honest `no-op`, never a written `.claude/settings*.json`. Pin the latter with a test that sets `runtime.target` to a non-Claude value and asserts no `.claude/` file is created.
4. **D4 — Report the inventory rows for retirement.** The two `../reference/coupling-inventory.md` rows covering these files (the `permission_common.py` / `permission_fix.py` binding row in §B, and the `permission_fix.py` DSL-rendering row beneath it) are re-derived against the tree, and **each row's own detection is re-run and the result reported in the PR body and the inbox message**. A row whose detection still finds something **stays, narrowed to the residue** — a row is retired because the coupling is gone from the tree, never because a plan claiming it merged.
   ⛔ **Changed from the original spec at ingestion:** the plan does **not** edit the inventory. It lives in the orchestrator ledger now, which the ledger write-boundary puts off-limits to an executing plan. The plan **reports** each re-derivation; the orchestrator retires the row from the landing. The re-derivation test still gates every closure — only the actor changed.
   *Done when:* the PR body and the inbox message carry each row's re-run detection and its verdict.

## Out of Scope

- **`workflow-permission-web/scripts/permission_web.py`.** It renders `WebFetch(domain)` strings and performs Claude settings I/O itself — the same class — but folding it in roughly doubles the surface and the review burden. **PLAN-14 owns it**, and runs after this plan so it can consume D2's vocabulary rather than build a second one.
- **A `targets: [claude]` filter on either skill.** Considered and **rejected on evidence**: these skills are **mixed**. The operations in each SKILL.md's platform-routed table already go through the registry and work correctly on a non-Claude target; only the executor-pattern and marketplace-wildcard operations bind Claude directly. Scoping the whole component would remove the half that works in order to contain the half that does not, and would make the skills unavailable on OpenCode permanently rather than fixing them. Raised in review on PR #1319 and declined there for this reason; the reviewer agreed registry routing is the correct fix and belongs to a separate plan. **This is that plan.**
- **The plugin-doctor analyzers and other resolvers with inline `.claude` anchors** (inventory §B) — PLAN-06's and PLAN-10's surfaces.
- **Changing what the permission model *means* on OpenCode.** This plan gives OpenCode an honest answer (implement or decline); deciding which permission semantics OpenCode *should* have needs a live install — WS-05's territory.
- **`permission_doctor.py`'s analysis rules and the three permission standards docs** as rule-pack-class subject matter — a different class (analyzed content, not render/import residue). **PLAN-14 owns it.**

## Claim Labels

- OBSERVED: `permission_common.py` imports six symbols from `claude_runtime` by name after a `sys.path` parent-walk — re-derived at HEAD `2cd1a19c`: **5** `claude_runtime` hits across its two `from claude_runtime import` blocks.
  - verdict: corroborated | checked_at: 2cd1a19c | by: multiplattform/analyze | rescoped: n/a | evidence: permission_common.py carries 5 claude_runtime hits across its two from claude_runtime import blocks, after the sys.path parent-walk
- OBSERVED: `permission_doctor.py` imports from `claude_runtime` the same way — read at `permission_doctor.py:27`, a direct `from claude_runtime import`. **1** hit.
  - verdict: corroborated | checked_at: 2cd1a19c | by: multiplattform/analyze | rescoped: n/a | evidence: permission_doctor.py:27 carries a direct from claude_runtime import - 1 hit
- OBSERVED: `permission_fix.py` does **not** import `claude_runtime` directly — it reaches the runtime through `permission_common`. This is why D3 names the other two as the binding sites.
  - verdict: corroborated | checked_at: 2cd1a19c | by: multiplattform/analyze | rescoped: n/a | evidence: permission_fix.py carries no direct claude_runtime import; it reaches the runtime through permission_common. Confirmed - this is why D3 names the other two as the binding sites.
- OBSERVED: `permission configure` and `permission fix --operation add|remove|ensure` take permission-DSL strings as arguments — read at `runtime_base.py::permission_configure` and the `tools-permission-fix/SKILL.md` platform-routed table.
  - verdict: corroborated | checked_at: 2cd1a19c | by: multiplattform/analyze | rescoped: n/a | evidence: runtime_base.py permission_configure signature and the tools-permission-fix SKILL.md platform-routed table both carry permission-DSL string arguments
- OBSERVED: §1 names `permission configure --permissions "Bash(…)"` as a violation — read at `../reference/principles.md` § 1, the "Also bad" bullet.
  - verdict: corroborated | checked_at: 2cd1a19c | by: multiplattform/analyze | rescoped: n/a | evidence: principles.md section 1 Also bad bullet names permission configure --permissions Bash(...) as the violation shape
- OBSERVED: `permission_web_apply` (domains) and `protect-path` (paths) are in-tree precedents for a semantic argument — read at `runtime_base.py::permission_web_apply` and `contract.md` § `permission fix`.
  - verdict: corroborated | checked_at: 2cd1a19c | by: multiplattform/analyze | rescoped: n/a | evidence: runtime_base.py permission_web_apply takes domain names and contract.md permission fix protect-path takes directory paths - both semantic, both in-tree, neither teaching any runtime a foreign grammar
- OBSERVED: an unscoped component is emitted to every target — read at `marketplace/targets/component_targets.py::emits_to`.
  - verdict: corroborated | checked_at: 2cd1a19c | by: multiplattform/analyze | rescoped: n/a | evidence: marketplace/targets/component_targets.py emits_to - an unscoped component is emitted to every registered component-tree target
- OBSERVED, **all three counts re-derived exactly at ingestion and they match**: `permission_fix.py` has exactly **12** `cmd_*` subcommands; the `Runtime` ABC carries exactly **25** `@abstractmethod` operations and exactly **7** `permission_*` operations, mirrored in both `_claude_runtime_impl.py` and `opencode_runtime.py`. ⚠️ **The op count was RE-SCOPED from 24 to 25 at the PLAN-13 landing** (PR #1376), which added the chat-signal operation to the ABC — re-derived at `bccca692c`: 25 `@abstractmethod`, 7 `permission_*`, and `permission_fix.py` still exactly 12 `cmd_*`, so only the op count moved. Note the spec had anticipated the change but named the wrong plan: it expected **PLAN-09** to move the count; **PLAN-13** did. All three remain **leads** — re-derive from the tree; a number baked in here is invalidated by any change between authoring and execution, and PLAN-09 may yet move it again.
  - verdict: contradicted | checked_at: bccca692c | by: multiplattform/analyze | rescoped: yes | evidence: Op count moved 24 -> 25 at the PLAN-13 landing (PR #1376), which added the chat-signal operation to the Runtime ABC. Re-derived at bccca692c: 25 @abstractmethod, 7 permission_*, permission_fix.py still 12 cmd_* - only the op count moved. Spec text updated to 25 in the same act, so the refutation is absorbed. The spec anticipated the change but attributed it to PLAN-09; PLAN-13 made it.
- OBSERVED: `permission_fix.py` still carries the DSL rendering/parsing symbols — **7** `claude_runtime`-class hits at HEAD covering `EXECUTOR_PERMISSION`, `OVERLY_BROAD_PYTHON`, `TIMESTAMP_PATTERN`, `normalize_path_perm`, `is_individual_script_permission`, and the `Skill(…)`/`SlashCommand(…)` wildcard generators.
  - verdict: corroborated | checked_at: 2cd1a19c | by: multiplattform/analyze | rescoped: n/a | evidence: permission_fix.py carries 7 hits covering EXECUTOR_PERMISSION, OVERLY_BROAD_PYTHON, TIMESTAMP_PATTERN, normalize_path_perm, is_individual_script_permission and the Skill(...)/SlashCommand(...) wildcard generators
- HYPOTHESIS: every intent behind a rendered DSL string in `permission_fix.py` is recoverable by reading the code — D1 settles it against the named symbols (verify-at-outline). ⛔ **If it refutes, the plan HALTS** rather than inventing a vocabulary.
  - verdict: unverifiable | checked_at: 2cd1a19c | by: multiplattform/analyze | rescoped: n/a | evidence: Intent recoverability was not tested at ingestion - that is D1's own job and its stop condition. Recorded as open so no reader mistakes the tight corroboration of the surrounding claims for a settlement of this one.
- HYPOTHESIS: no general skill script outside the three named here binds `claude_runtime` **for permission work** — an asserted absence, so verify it as a presence (verify-at-outline). ⛔ **The search is not self-interpreting.** At authoring time it returned six non-cache files outside the three named here, and every one was out of scope for a different reason: `manage-metrics.py`, `manage_terminal_title.py`, `marketplace_paths.py` and `file_ops.py` bind the runtime for metrics, title, layout and file work (**not** permissions); plugin-doctor's `_analyze_sys_path_bootstrap.py`, `_analyze_plan_path_in_scripts.py` and `_doctor_shared.py` *mention* the name as analyzer subject matter rather than binding it. Re-derive and classify each hit by that test — a hit is a refutation **only if it performs permission work**.
  - verdict: unverifiable | checked_at: 2cd1a19c | by: multiplattform/analyze | rescoped: n/a | evidence: The asserted absence was not re-derived and classified at ingestion. The claim carries its own classification test (a hit refutes only if it performs permission work); running and classifying it is the plan's first action.

## Expected Surface

Re-derive before acting — this list is hand-written, per the standing epic warning.

- OBSERVED: `marketplace/bundles/plan-marshall/skills/tools-permission-doctor/scripts/permission_common.py` — the direct-binding site (D3)
- OBSERVED: `marketplace/bundles/plan-marshall/skills/tools-permission-doctor/scripts/permission_doctor.py` — imports `claude_runtime` the same way (D3)
- OBSERVED: `marketplace/bundles/plan-marshall/skills/tools-permission-fix/scripts/permission_fix.py` — the DSL symbols and the 12 `cmd_*` subcommands that consume them (D1–D3)
- OBSERVED: `marketplace/bundles/plan-marshall/skills/platform-runtime/scripts/runtime_base.py` — the permission operations whose signatures carry DSL strings (D2)
- OBSERVED: `marketplace/bundles/plan-marshall/skills/platform-runtime/scripts/claude_runtime.py`, `_claude_runtime_impl.py` — the Claude side of any changed operation (D2)
- OBSERVED: `marketplace/bundles/plan-marshall/skills/platform-runtime/scripts/opencode_runtime.py` — the declining side (D2)
- OBSERVED: `marketplace/bundles/plan-marshall/skills/platform-runtime/scripts/platform_runtime.py` — the router's argument surface (D2)
- OBSERVED: `marketplace/bundles/plan-marshall/skills/platform-runtime/standards/contract.md` — operation documentation (D2)
- OBSERVED: `marketplace/bundles/plan-marshall/skills/tools-permission-fix/SKILL.md`, `marketplace/bundles/plan-marshall/skills/tools-permission-doctor/SKILL.md` — the command tables and the ⚠️ warning that currently discloses the gap this plan closes (D3)
- OBSERVED: `test/plan-marshall/platform-runtime/**`, `test/plan-marshall/tools-permission-fix/**`, `test/plan-marshall/tools-permission-doctor/**` — the pins
- ⛔ **Removed from the surface at ingestion:** the coupling inventory. It is now ledger-resident and off-limits; D4 reports instead of editing.

## Dependencies and Sequencing

- Depends on: **PLAN-03** (landed, PR #1319), which moved the default-permission renderer and the credential deny rules behind the runtime and added `protect-path`. This plan starts from that shape.
- Overlaps with: **PLAN-01** (landed) and **PLAN-09** on `platform-runtime/scripts/**`; **PLAN-06** and **PLAN-07** conditionally on `contract.md`. ⛔ **Not concurrent with any of them.**
- Blocks: **PLAN-14**, which consumes D2's vocabulary.
- Concurrent with: PLAN-04 (fully disjoint), PLAN-13 (fully disjoint).
- **Why the reroute is second, not first.** D2 precedes D3 deliberately. Routing an operation whose argument is Claude's DSL would oblige every other runtime to parse that DSL — the coupling inverted rather than removed. The vocabulary has to exist before routing through it means anything.
- **Op-count references.** `contract.md` states the `Runtime` operation count. If D2 changes it, update it there and report the new figure in the inbox message so the orchestrator can correct every other carrier.

## Verification

- **The no-Claude-write pin (D3).** A test that drives each affected subcommand with `runtime.target` set to a non-Claude value and asserts no `.claude/settings*.json` is created. This is the check the whole plan exists for; without it the routing is asserted rather than shown.
- **A cold read of the changed `contract.md` operation docs (D2).** A reviewer reads the new operation documentation **cold** — no plan, no diff — and reports, for each changed operation, *what argument it believes the caller passes*. If any answer names a permission-DSL string, the wording failed however complete it looks. Aim at interpretation, not at "matches requirements".
- **Both runtimes, every permission operation.** Assert Claude implements and OpenCode either implements or returns an honest `no-op` with `reason` + `alternative` — never fabricated success, per §3. Derive the operation population from the ABC rather than restating it, with a non-vacuity guard so an empty population cannot pass.
- **The full verify gate**, read from its **exit status** and its result `status`/`errors[]` — the wrapper exits 0 even on failure, so neither alone is sufficient.

## Hand-Off Command

```text
/plan-marshall task="implement .plan/orchestrator/multiplattform/plans/PLAN-08-permission-skills-through-the-registry.md"
```

## Write-Boundary

The plan implementing this spec touches only its own repository source and tests. It creates and
edits NO file under `.plan/orchestrator/` other than its own `inbox/{sender}-{seq}` message —
the orchestrator owns every other ledger write. D4 in particular **reports** its row re-derivations
through that message and the PR; it never edits `../reference/coupling-inventory.md`.
