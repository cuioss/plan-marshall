> ⛔ **FIRST INSTRUCTION — do not skip, do not delete, do not move below the title.**
>
> Before reading the rest of this plan and before any other action, load the working contract that
> governs this run:
>
> ```text
> Skill: cloud-plan-lane
> ```
>
> It owns the branch/PR/review-comment cycle, the build gate, the pre-PR verification sub-agent, the
> run report, and the closing self-check. **Nothing in this plan overrides it** — where this plan and
> the contract disagree, the contract wins, and the disagreement is reported.
>
> If the skill cannot be loaded, **stop and report the run blocked**. Do not reconstruct the workflow
> from this file: the parts that matter most — the merge gate, the verification dispatch, the report
> — are not in here.
>
> This block is part of the plan, not part of the template. It survives into every copy.

# The permission skills state intent and route through the registry

**Epic:** multiplattform (standalone — see [`README.md`](README.md) for the shared constraints)
**Branch prefix:** `chore`

## Problem

`tools-permission-doctor` and `tools-permission-fix` are **general skills that only work on Claude**,
and nothing prevents an OpenCode project from reaching them. Two distinct defects produce that, and
the second is why the first cannot simply be fixed by rerouting.

**The direct binding.** `permission_common.py` imports `_claude_global_settings_path`,
`_claude_project_settings_path`, `_claude_project_settings_read_path`, `_load_settings`,
`_save_settings` and `ensure_default_permissions` from `claude_runtime` by name, after walking
parents to put `platform-runtime/scripts` on `sys.path`. `permission_doctor.py` imports from
`claude_runtime` the same way. So settings load/save, both path selectors, and the default-permission
renderer resolve to the Claude implementation whatever `runtime.target` says — the skills are emitted
to every target (no `targets:` filter; an unscoped component is emitted everywhere, per
`component_targets.py::emits_to`), so on an OpenCode project these write `.claude/settings*.json`.
This also fails the [§6](reference/principles.md#6-open-to-further-targets) cost bar: adding a target
means editing these general skill scripts.

**The grammar crossing, which blocks the reroute.** Routing the direct-binding calls through
`platform_runtime._REGISTRY` does not by itself make the skills target-neutral, because **the
arguments are already Claude grammar**. `permission configure` takes a raw permission list;
`permission fix --operation add|remove|ensure` takes patterns like `Bash(docker:*)`.
[§1](reference/principles.md#1-goal-based-api--semantic-in-normalized-out) names that exact shape as
a violation — its own worked example is *"Also bad: `permission configure --permissions "Bash(…)"`"*.
Rerouting an op whose argument is Claude's DSL would require every other runtime to **parse Claude's
permission grammar**, which is the coupling inverted rather than removed. Alongside it,
`permission_fix.py` renders and parses that grammar directly (`EXECUTOR_PERMISSION`,
`OVERLY_BROAD_PYTHON`, `TIMESTAMP_PATTERN`, `normalize_path_perm`,
`is_individual_script_permission`, the `Skill(…)`/`SlashCommand(…)` wildcard generators), and
`ensure_default_permissions` receives the Claude settings **mapping** as a parameter — a return-value
and argument crossing §1 forbids in both directions.

The repository already contains the shape that resolves this. `permission_web_apply` takes **domain
names**; `permission fix --operation protect-path` takes **directory paths**. Both express intent and
carry normalized data, and both were reachable without teaching any runtime a foreign grammar.

## Goal

The permission skills express **intent** and consume **normalized values**, and resolve their
platform through the runtime registry rather than through a direct `claude_runtime` import. A
non-Claude target either implements the operation on its own model or declines it with an honest
`no-op` — never silently writes a Claude-shaped file. Both coupling-inventory rows covering these
files are retired by re-derivation, and adding a fourth target requires editing none of these
scripts.

## Deliverables

1. **D1 — The crossing inventory, and the stop condition** — enumerate, from the tree, every place
   these three scripts (`permission_common.py`, `permission_doctor.py`, `permission_fix.py`) either
   import `claude_runtime` directly or render/parse a permission-DSL string, and for each DSL site
   record the **intent** it expresses in one phrase. Write the result into the run report before
   changing any code.
   *Done when:* the report carries the enumeration, each row naming file, symbol, and intent phrase.
   **HALT the plan and report if the intents cannot be stated from the code** — if a rendered string's
   purpose is not recoverable by reading, the vocabulary in D2 would be invented rather than derived,
   and this plan's premise has failed. Do **not** fall back to inventing intents from the string
   shapes: that reproduces the grammar coupling inside the fix.
2. **D2 — A semantic vocabulary for the crossings D1 found** — for each intent, provide a
   target-neutral way to express it, following the two in-tree precedents (`permission_web_apply`
   takes domains; `protect-path` takes paths). The naming rule, so this needs no mid-run decision:
   **name what the caller wants, never what Claude writes** — an argument is a domain, a path, a
   skill name, an executor identity, never a `Tool(pattern)` string. Where an intent is genuinely
   Claude-only, that is a legitimate finding: record it in the report as a candidate for a `no-op`
   on other targets, and do not invent a neutral spelling for it.
   *Done when:* no argument to, and no return value from, a `platform-runtime` permission operation
   is a permission-DSL string, verified by re-reading the operation signatures and the router; and
   `contract.md` documents each operation by its intent.
3. **D3 — The skills route through the registry** — `permission_common.py` and `permission_doctor.py`
   resolve their runtime through `platform_runtime`'s registry instead of importing `claude_runtime`,
   and the `sys.path` parent-walk that exists to reach `claude_runtime` goes with it. The Claude
   settings **mapping** stops crossing into `ensure_default_permissions` as a parameter.
   *Done when:* `grep -n "claude_runtime" ` over all three scripts returns nothing, re-derived at the
   moment of the claim; and an OpenCode-target project driving each subcommand gets either a real
   result or an honest `no-op`, never a written `.claude/settings*.json`. Pin the latter with a test
   that sets `runtime.target` to a non-Claude value and asserts no `.claude/` file is created.
4. **D4 — Retire the inventory rows by re-derivation** — the two
   [`coupling-inventory.md`](reference/coupling-inventory.md) rows covering these files (the
   `permission_common.py` / `permission_fix.py` binding row in §B, and the `permission_fix.py`
   DSL-rendering row beneath it) are re-derived against the tree and closed per the inventory's own
   [§ Closing a row](reference/coupling-inventory.md#closing-a-row).
   *Done when:* each row's own detection is re-run and reported. A row whose detection still finds
   something **stays, narrowed to the residue** — deleting a row because this plan merged is exactly
   what that section forbids.

## Out of scope

- **`workflow-permission-web/scripts/permission_web.py`.** It renders `WebFetch(domain)` strings and
  performs Claude settings I/O itself — the same class — but it is a different skill with its own
  inventory row, and folding it in roughly doubles the surface and the review burden. Excluded so
  this plan stays reviewable; the row stays open and un-drawn.
- **A `targets: [claude]` filter on either skill.** Considered and rejected on evidence, not
  overlooked: these skills are **mixed**. The operations in each SKILL.md's platform-routed table
  already go through the registry and work correctly on a non-Claude target; only the
  executor-pattern and marketplace-wildcard operations bind Claude directly. Scoping the whole
  component would remove the half that works in order to contain the half that does not, and would
  make the skills unavailable on OpenCode permanently rather than fixing them. This was raised in
  review on PR #1319 and declined there for this reason.
- **The plugin-doctor analyzers and other resolvers that keep inline `.claude` anchors** (inventory
  §B). Different files, different owners, no dependency on this work — including them would make the
  surface collide with plans `060` and `070`.
- **Changing what the permission model *means* on OpenCode.** This plan gives OpenCode an honest
  answer (implement or decline); deciding which permission semantics OpenCode *should* have needs a
  live install, which is the [validation protocol](reference/opencode-validation-protocol.md)'s
  territory and explicitly not plannable in this epic.

## Expected surface

Re-derive before acting — this list is hand-written, per the epic README's standing warning.

- `marketplace/bundles/plan-marshall/skills/tools-permission-doctor/scripts/permission_common.py` — the direct-binding site (D3)
- `marketplace/bundles/plan-marshall/skills/tools-permission-doctor/scripts/permission_doctor.py` — imports `claude_runtime` the same way (D3)
- `marketplace/bundles/plan-marshall/skills/tools-permission-fix/scripts/permission_fix.py` — the DSL rendering/parsing symbols and the 12 `cmd_*` subcommands that consume them (D1–D3)
- `marketplace/bundles/plan-marshall/skills/platform-runtime/scripts/runtime_base.py` — the permission operations whose signatures carry DSL strings (D2)
- `marketplace/bundles/plan-marshall/skills/platform-runtime/scripts/claude_runtime.py`, `_claude_runtime_impl.py` — the Claude side of any changed operation (D2)
- `marketplace/bundles/plan-marshall/skills/platform-runtime/scripts/opencode_runtime.py` — the declining side (D2)
- `marketplace/bundles/plan-marshall/skills/platform-runtime/scripts/platform_runtime.py` — the router's argument surface (D2)
- `marketplace/bundles/plan-marshall/skills/platform-runtime/standards/contract.md` — operation documentation (D2)
- `marketplace/bundles/plan-marshall/skills/tools-permission-fix/SKILL.md`, `tools-permission-doctor/SKILL.md` — the command tables and the ⚠️ warning that currently discloses the gap this plan closes (D3)
- `doc/plans/multiplattform/reference/coupling-inventory.md` — row retirement (D4)
- `test/plan-marshall/platform-runtime/**`, `test/plan-marshall/tools-permission-fix/**`, `test/plan-marshall/tools-permission-doctor/**` — the pins

## Claim labels

| Claim | Label | Confirm/refute artifact |
|---|---|---|
| `permission_common.py` imports six symbols from `claude_runtime` by name, after a `sys.path` parent-walk | OBSERVED | `permission_common.py`, the two `from claude_runtime import` blocks |
| `permission_doctor.py` imports from `claude_runtime` the same way | OBSERVED | `permission_doctor.py`, its `from claude_runtime import` block |
| `permission configure` and `permission fix --operation add\|remove\|ensure` take permission-DSL strings as arguments | OBSERVED | `runtime_base.py::permission_configure` signature; `tools-permission-fix/SKILL.md` platform-routed table |
| §1 names `permission configure --permissions "Bash(…)"` as a violation | OBSERVED | `reference/principles.md` § 1, the "Also bad" bullet |
| `permission_web_apply` (domains) and `protect-path` (paths) are in-tree precedents for a semantic argument | OBSERVED | `runtime_base.py::permission_web_apply` signature; `contract.md` § `permission fix` |
| An unscoped component is emitted to every target | OBSERVED | `marketplace/targets/component_targets.py::emits_to` |
| Every intent behind a rendered DSL string in `permission_fix.py` is recoverable by reading the code | **HYPOTHESIS** | D1 settles it against the named symbols; **if it refutes, the plan halts** rather than inventing a vocabulary |
| No general skill script outside the three named here binds `claude_runtime` **for permission work** | **HYPOTHESIS** | a re-derived `grep -rl claude_runtime marketplace/bundles/*/skills/*/scripts/` excluding `platform-runtime/scripts` and `__pycache__`, run before D3. An **asserted absence**, so verify it as a presence. **The grep is not self-interpreting** — at authoring time it returned six non-`__pycache__` files outside the three named here, and every one was out of scope for a different reason: `manage-metrics.py`, `manage_terminal_title.py`, `marketplace_paths.py` and `file_ops.py` bind the runtime for metrics, title, layout and file work (not permissions), and plugin-doctor's `_analyze_sys_path_bootstrap.py` / `_analyze_plan_path_in_scripts.py` / `_doctor_shared.py` *mention* the name as analyzer subject matter rather than binding it. Re-derive and classify each hit by that test — a hit is a refutation only if it performs permission work. Note `permission_fix.py` does **not** appear: it reaches the runtime through `permission_common`, which is why D3 names the other two as the binding sites |

`permission_fix.py` has **12 `cmd_*` subcommands** and the `Runtime` ABC carries **24 operations** and
**7 permission operations**. All three are **leads** — re-derive from the tree; a number baked in here
is invalidated by any change between authoring and execution.

## Verification

Beyond each deliverable's *done when*:

- **The no-Claude-write pin (D3).** A test that drives each affected subcommand with `runtime.target`
  set to a non-Claude value and asserts no `.claude/settings*.json` is created. This is the check that
  the whole plan exists for; without it the routing is asserted rather than shown.
- **A cold read of the changed `contract.md` operation docs (D2).** Dispatch the lane's pre-PR
  verification sub-agent to read the new operation documentation **cold** — no plan, no diff — and
  report, for each changed operation, *what argument it believes the caller passes*. If any answer
  names a permission-DSL string, the wording failed however complete it looks: D2's whole value is
  what a later caller does with the text. Aim the sub-agent at interpretation, not at
  "matches requirements".
- **Both runtimes, every permission operation.** Assert Claude implements and OpenCode either
  implements or returns an honest `no-op` with `reason` + `alternative` — never fabricated success,
  per [§3](reference/principles.md#3-no-op-policy). Derive the operation population from the ABC
  rather than restating it, with a non-vacuity guard so an empty population cannot pass.
- **Full `./pw verify`**, read from its **exit status** and its result `status`/`errors[]` — the
  wrapper exits 0 even on failure for the architecture-resolved envelope, so neither alone is
  sufficient.

## Notes

**Sequencing.** Runs after `030` (PR #1319), which moved the default-permission renderer and the
credential deny rules behind the runtime and added `protect-path`. This plan starts from that shape:
`030` established the goal-based pattern in two places and left the rest, registering the residue in
the inventory rows D4 retires.

**Concurrency.** Shares `platform-runtime/scripts/**` with `010` and `030`, and
`platform-runtime/standards/contract.md` conditionally with `060` and `070`. Not concurrent with any
of them. Independent of `040`.

**Why the reroute is second, not first.** D2 precedes D3 deliberately. Routing an operation whose
argument is Claude's DSL would oblige every other runtime to parse that DSL — the coupling inverted
rather than removed. The vocabulary has to exist before routing through it means anything.

**Op-count references.** `contract.md` and this epic's `README.md` both state the `Runtime` operation
count. If D2 changes it, update both — and treat the stated figure as a lead in each.

**Prior review.** The `targets:` remedy in the Out of scope was raised by CodeRabbit on PR #1319 and
declined there with the mixed-skill reasoning; the reviewer agreed the correct fix is registry
routing and belongs to a separate plan. This is that plan.

**No `.plan/` reading.** This epic is standalone: it has no orchestrator ledger, and nothing here
expects one. `.plan/` is git-ignored and invisible from a cloud clone — do not go looking for a spec,
a landing record, or a status file. Everything this plan needs is in git and named above.
