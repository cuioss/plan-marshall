---
lane:
  class: adversarial
  cost_size: S
name: finalize-step-plugin-doctor
description: Finalize-phase wrapper that runs the plugin-doctor quality-gate — scoped to the skills the plan touched, or whole-tree when a plugin-doctor/plan-doctor rule or a non-skill file the verdict reads changes, or the scope read is indeterminate — gating structural lint before push
user-invocable: false
mode: script-executor
allowed-tools: Bash
order: 6
head_dependent: true
reads:
  - worktree
default_on: false
presets: []
implements: plan-marshall:extension-api/standards/ext-point-finalize-step
---

# Finalize Step: plugin-doctor

## Purpose

Run the plugin-doctor `quality-gate` invariant rule set — argparse safety, argument-naming, manage-invocation, extension contracts, shell-substitution, lesson-id / historical prose, role-field, the markdown-mirror rules (`broken-relative-link`, `fenced-code-no-language`), and the repo-root agentfile analyzers; the roster is defined by `cmd_quality_gate` and this list is illustrative, not closed — scoped to the marketplace source of any skill the plan modifies — gating structural lint **before push**. Catches structural breakage that the Python `quality-gate` (ruff/mypy/pytest) cannot detect. The gate's scope is the **union** of two reads (Step 1): the plan's realized footprint — what the branch actually changed, fix tasks and fix commits included — and the `affected_files` list declared at outline time. The union and the skill-dir extraction over it (Step 2) SUPPLY the `--paths` targets the gate scopes to; the skip-clean exit (Step 3) skips the gate when both reads succeed, no union entry matches a whole-tree trigger pattern (Step 2.5), and the union names no skill.

The wrapper runs in one of three mutually-exclusive modes, selected deterministically (see Step 2.5 for the precedence and for the trigger patterns): it runs **whole-tree** (no `--paths`) when a union entry matches a whole-tree trigger pattern — either a plugin-doctor / plan-doctor analyzer or rule script, because a rule change re-classifies skills the diff never touched (the **F1 trigger**), or a file outside every skill directory whose content the gate's verdict reads, because its finding lands where a scoped run filters it out and where a skip never looks (the **verdict-input trigger**: a target package's `__init__.py`, a bundle's `plugin.json`, a repository agent file); it runs **whole-tree** when either scope read is indeterminate (broken, not empty); and otherwise it **scopes** the gate to the skill directories the union names (the common case). In scoped mode the wrapper additionally emits a loud **cross-skill divergence WARNING**, because a scoped `--paths` run structurally cannot evaluate plugin-doctor's cross-skill rules — those whose verdict spans more than the touched skill and whose finding anchors to a counterpart file OUTSIDE the touched paths (the PR #915 scoped-green / whole-tree-red class). The warning keeps the common-case scoped run for skill-local rules unchanged while surfacing, at finalize, that the cross-skill rule class was not gated — rather than silently passing as if it had been.

Ordered at `order: 6` so it slots between `default:finalize-step-simplify` (order 5) and `default:finalize-step-security-audit` (order 7) — structural lint gates before the commit is pushed, not after CI.

When the plan runs in an isolated worktree, the gate first regenerates a worktree-bound executor so the `manage-invocation-invalid` rule probes each script's `--help` against the worktree's TRUE argparse surface. Without this step, the worktree's `.plan/execute-script.py` is a symlink to the main checkout's executor, whose embedded mappings resolve every `manage-*` notation to the main-checkout (pre-plan) script — making a newly added subcommand read as a false-positive "unregistered" and a newly required flag read as a false-negative that masks the real CI finding.

## Interface Contract

Invoked by `plan-marshall:phase-6-finalize` for projects that include `project:finalize-step-plugin-doctor` in their `phase-6-finalize.steps` list.

Accepts the standard finalize-step arguments:

- `--plan-id` — plan identifier (required, used to derive the plan's realized footprint and to read the declared `affected_files`, whose union is the gate scope)
- `--iteration` — finalize iteration counter (accepted for contract compliance, no effect)

MUST be ordered **before** `default:commit-push` in the steps list so structural lint gates before push.

In a worktree-backed plan, the gate step is preceded by a worktree-fresh-executor regeneration (Step 4 below) that rebinds notation→path resolution to the worktree's scripts. Regeneration failure is non-fatal (logged WARN) — a gate run against the still-stale executor is no worse than not regenerating, so finalize must not hard-block on a mapping refresh.

## HEAD-dependency

This step declares `head_dependent: true` in its frontmatter — that fact IS the membership declaration the dispatcher's re-entry check reads (see [ext-point-finalize-step.md](../../../marketplace/bundles/plan-marshall/skills/extension-api/standards/ext-point-finalize-step.md) § "Implementor Frontmatter"). Its verdict is a structural-lint **pass/fail gate over the tree's marketplace source**, so a HEAD advance changes both the derived `--paths` scope (Step 2) and the gate's verdict. Both `--outcome done` records below assert something about the tree that a loop-back commit can falsify — the Step 5 pass asserts "the gated source is lint-clean", and the Step 3 Case (a) skip-clean asserts "the plan touched no skill and no whole-tree trigger file" — so BOTH MUST capture the worktree HEAD immediately before their `mark-step-done` call and forward it via `--head-at-completion {sha}`. The `--outcome failed` record does NOT take the flag: the dispatcher retries `failed` records on re-entry regardless of HEAD, so the SHA carries no decision value there.

### Verdict-input surface — deliberately undeclared

This step declares **no** `verdict_inputs`, so the dispatcher's verdict-currency classifier never narrows its re-fire: every HEAD advance re-runs it. The absence is a **recorded refusal on evidence**, not an obligation left unwritten, and it is recorded because this step looks like the obvious candidate for a declaration — its `--paths` scope is derived from two skill roots, so `marketplace/*` plus `.claude/*` reads like the whole story. It is not.

The admissibility bar is that the globs be a **superset** of everything the gate's verdict reads (see [ext-point-finalize-step.md](../../../marketplace/bundles/plan-marshall/skills/extension-api/standards/ext-point-finalize-step.md) § "Implementor Frontmatter"). Two rules in the roster this step runs read outside those roots:

- **`broken-relative-link`** resolves each relative link target **against the linking file's own directory**, then stats it on disk whenever it falls inside the **repository root** — the containment boundary the whole-tree call site passes precisely so that in-repo cross-tree links are existence-checked. A missing in-boundary target is an `error`. Marketplace docs link out of `marketplace/` in bulk — into `doc/**`, into `test/**`, and to root files — so a commit that renames or deletes any link *target* turns this gate red without touching either skill root. The target set cannot be captured by a static glob at all: any file can become a link target, so the input set is derivable at run time and underivable ahead of time.
- **`analyze_agentfile_line_budget` / `analyze_agentfile_directory_tree`** walk the repository root and lint every `CLAUDE.md` / `AGENTS.md` at any depth — a whole-repo walk, which [verdict-currency.md](../../../marketplace/bundles/plan-marshall/skills/phase-6-finalize/standards/verdict-currency.md) § "The classification" names as a disqualifying shape in its own right.

So no proper subset of the tree is sound here, and a whole-tree declaration would be an inert lever wearing the shape of a real one. Declaring nothing keeps the fail-closed default and says so. `default:pre-push-quality-gate` refuses for a parallel reason — see its own [§ "Verdict-input surface — deliberately undeclared"](../../../marketplace/bundles/plan-marshall/skills/phase-6-finalize/standards/pre-push-quality-gate.md) — and the two together are why the mechanism's admissibility bar is stated as a superset obligation rather than a naming exercise. See [verdict-currency.md](../../../marketplace/bundles/plan-marshall/skills/phase-6-finalize/standards/verdict-currency.md).

#### The narrower rule that was examined, and why it is refused

Both rules above fail on a path that *appears or disappears*: a link target renamed or deleted, an agent file added. That suggests a narrower rule, built on the kind of change rather than on a glob. It was examined and is refused.

**The rule examined.** Skip a re-fire when the HEAD advance:

- adds, deletes and renames no tracked path, and
- modifies no path inside a gated skill directory, and
- modifies no agent file the two whole-repository analyzers read, and
- modifies no file of the plugin-doctor or plan-doctor skills.

The reasoning behind it: a modify-only commit cannot break a link target's existence, and the three exclusions cover the content the gate reads — the gated skills themselves, the agent files, and the rules.

**The counter-example.** The exclusions do not cover the content the gate reads. The `targets-scope-invalid` rule (`analyze_target_scope`, in the `quality-gate` roster) reads the **content** of two kinds of file:

- `marketplace/targets/*/__init__.py` — the registered target names, and
- each bundle's `.claude-plugin/plugin.json` — the bundle's `targets` scope.

Both lie outside every skill directory. Neither is an agent file, and neither belongs to the plugin-doctor or plan-doctor skills. Yet the rule anchors its findings at a `SKILL.md` or a skill-internal document **inside** a gated skill directory, so a scoped gate reports them. A commit that only modifies one of these files — a target renamed in a target package's `__init__.py`, a `targets` entry edited in a `plugin.json` — adds, deletes and renames nothing and touches no listed path. The examined rule would skip the re-fire, and the gate that was skipped would have turned red.

**The consequence.** No skip predicate is admitted. The step keeps the unconditional re-fire: every HEAD advance re-runs the gate. A rule of this shape is only as sound as its list of exclusions is complete, and the roster is open — each rule added to `cmd_quality_gate` may read content from somewhere new, and nothing would force the list to follow. What bounds the cost of a re-fire is the gate's scope (Step 1's union of realized footprint and declared files), not a skip.

This recorded reason is the whole of the refusal. The step ships no script and no skip test, and its workflow, its script calls and its re-fire behaviour are exactly as the sections below state.

## Workflow

### Step 1: Read the gate scope — realized footprint ∪ declared files

The gate covers what the plan **changed**, not only what it **declared**. `affected_files` is the footprint declared at outline time; files changed by fix tasks and fix commits never enter it, so a gate scoped to it alone covers fewer skill directories than the branch touched. Step 1 therefore makes two reads and forms their union.

Resolve the worktree path first — the footprint read needs it, and Step 3 and Step 4 reuse the value:

```bash
python3 .plan/execute-script.py plan-marshall:manage-status:manage-status get-worktree-path \
  --plan-id {plan_id}
```

Capture `worktree_path` from the returned TOON as `{worktree_path}` (substitute `.` when it is empty — the main-checkout flow).

**Read 1 — the realized footprint** (what the branch changed, derived live from the worktree's git state):

```bash
python3 .plan/execute-script.py plan-marshall:manage-references:manage-references compute-footprint \
  --plan-id {plan_id} --worktree-path {worktree_path}
```

On `status: success`, `files` is the realized footprint (it MAY be empty). `status: error` means the read is broken, not empty — the named errors are `worktree_not_found`, `references_not_found`, `not_a_git_worktree`, `git_error`, `files_out_refused` and `files_out_unwritable`, and an error payload carries no `files` key at all.

**Read 2 — the declared files**:

```bash
python3 .plan/execute-script.py plan-marshall:manage-references:manage-references get \
  --plan-id {plan_id} --field affected_files
```

`status: success` means the read resolved (the list MAY be empty); `status: error` with `error: field_not_found` means the read is broken, not empty.

**Form the union.** When BOTH reads return `status: success`, the gate scope is the set union of the two lists, deduplicated. Keeping the declared list in the union is deliberate: a declared-but-untouched skill directory is still gated. Steps 2, 2.5 and 3 all operate on this union — never on either list alone.

**When EITHER read fails** — `field_not_found` for the declared list, or any named `compute-footprint` error — the scope is **indeterminate**: a union with a missing operand is not a smaller scope, it is an unknown one. Do not form a union from the surviving list; Step 3's indeterminate branch applies and the gate runs whole-tree.

### Step 2: Extract skill directory paths (the `--paths` supplier)

Filter the Step 1 union to entries matching either pattern:
- `marketplace/bundles/{bundle}/skills/{skill}/` (marketplace skills)
- `.claude/skills/{skill}/` (project-local skills)

For each matching file, extract the skill directory path (everything up to and including the skill name directory). Deduplicate the result. These extracted skill directories are the `--paths` targets supplied to the `quality-gate` invocation in Step 5.

Example: `marketplace/bundles/plan-marshall/skills/phase-5-execute/SKILL.md` → `marketplace/bundles/plan-marshall/skills/phase-5-execute`

### Step 2.5: Select gate mode (whole-tree triggers → whole-tree)

The gate runs in exactly one of three modes. Evaluate them in this fixed precedence order and pick the first that applies:

1. **Trigger whole-tree mode** — at least one entry in the Step 1 union matches a pattern in the whole-tree trigger table below. Step 5 runs `quality-gate` with **no `--paths`** against the resolved `--marketplace-root`. This precedes BOTH the skip-clean exit and scoped mode: a trigger hit forces a whole-tree run when no skill directory survived Step 2 filtering (rather than a skip), and equally when one or more did (rather than a scoped run).
2. **Indeterminate-read whole-tree fallback** — either Step 1 read returned `status: error`: `error: field_not_found` for the declared list, or any named `compute-footprint` error for the realized footprint (a scope-deriving read is broken, not empty). Step 5 runs `quality-gate` with **no `--paths`** (see Step 3 Case (b)).
3. **Scoped mode** (the common case) — neither whole-tree condition holds; Step 5 scopes the gate to the skill directories extracted from the union in Step 2 **and emits the loud cross-skill divergence WARNING** described below.

**Whole-tree trigger patterns.** The table is the complete trigger set. Each pattern is matched against a whole repository-relative union entry: `*` matches within one path segment, and `**` matches any run of segments, including none.

| Trigger pattern | Family | Why a union entry matching it forces whole-tree |
|-----------------|--------|--------------------------------------------------|
| `marketplace/bundles/pm-plugin-development/skills/plugin-doctor/**` | F1 | A plugin-doctor analyzer or rule script changed; a rule change re-classifies skills the diff never touched |
| `marketplace/bundles/plan-marshall/skills/plan-doctor/**` | F1 | A plan-doctor analyzer or rule script changed; same re-classification |
| `marketplace/targets/*/__init__.py` | verdict-input | `targets-scope-invalid` reads the registered target names from it; renaming one invalidates a `targets:` declaration in a skill the diff never touched |
| `marketplace/bundles/*/.claude-plugin/plugin.json` | verdict-input | `targets-scope-invalid` reads the bundle's `targets` scope from it and anchors findings at the manifest itself and at any component of the bundle that widens the scope |
| `**/CLAUDE.md` | verdict-input | The two agentfile analyzers lint it and anchor the finding at the agent file, outside every skill directory |
| `**/AGENTS.md` | verdict-input | Same as `CLAUDE.md` |

The two families fail the scoped and skipped paths the same way. A **verdict-input** file lies outside every skill directory, so Step 2 extracts nothing from it: alone in the union it would reach the skip-clean exit, and beside an unrelated skill it would reach scoped mode, where `--paths` filters out a finding anchored at the file itself or in a skill the union does not name. The agent-file patterns match by basename at any depth, which is wider than the analyzers' own walk (it prunes `.plan`, `.git`, `node_modules` and `target`); a match in a pruned directory costs one unneeded whole-tree run and misses nothing.

**What no trigger covers: link targets outside skill directories.** `broken-relative-link` stats every in-repository link target, and marketplace docs link into `doc/**`, `test/**` and root files. A union that renames or deletes such a target and names no skill takes the skip-clean exit, and one that names an unrelated skill runs scoped — the broken link is anchored in the linking file, which is in neither scope. No pattern can close this: any file can be a link target, so the set of paths whose removal breaks a link is known only by resolving every link, which is the whole-tree run itself. The gap is bounded, not closed — the whole-tree gate in CI reports the broken link.

When a whole-tree trigger fires, skip the Step 3 skip-clean exit entirely and proceed to Step 4, then run the whole-tree invocation in Step 5. The two whole-tree modes (trigger, indeterminate read) share the same no-`--paths` invocation — they differ only in what selects them.

**Cross-skill divergence gap (why scoped mode warns).** `doctor-marketplace.py quality-gate --paths` filters every file-anchored finding to those whose `file` resolves under a supplied path (`_finding_in_scope`). A **cross-skill rule** — one whose verdict spans more than the touched skill and whose finding anchors to a counterpart file OUTSIDE `--paths` — is therefore structurally invisible to a scoped run: the scoped run sees only the touched side and passes, while a whole-tree run sees both sides and fails. This is the PR #915 divergence class: a non-rule skill edit changed one side of a cross-skill invariant whose counterpart lived in an untouched skill. Concrete quality-gate rules in this class include `manage-invocation-invalid` / `missing-canonical-block` (a referenced script or its canonical block in an untouched skill), `provides-method-table-drift`, `literal-count-drift`, `resolver-matrix-coverage`, and the source-of-truth-duplication / count-prose cross-reference rules. `validate_extension_contracts` is the SOLE exception — it always runs whole-tree unfiltered even under `--paths`, so it is NOT part of the gap.

The bounded correction (per the request's caught-or-loudly-warned latitude, adding no new whole-tree mechanism and NOT making the step unconditionally whole-tree): **scoped mode MUST emit a loud finalize WARNING** in Step 5 recording that scoped mode did not evaluate the cross-skill rule class. The warning fires in scoped mode regardless of whether the scoped gate passes or fails — it documents the rules that were NOT run, not the scoped result. A scoped run therefore never silently passes as if plugin-doctor's cross-skill rules had been gated; the #915 class is surfaced at finalize rather than first at whole-tree CI.

### Step 3: Skip-clean exit (only when both reads succeed, no trigger fired and the union names no skill)

The skip-clean exit is taken ONLY when no Step 2.5 whole-tree trigger fired AND BOTH Step 1 reads succeeded (`status: success`) AND zero skill paths remain after Step 2 filtering of the union — the plan touched and declared no skill and no file the trigger table names. A trigger hit of either family (Step 2.5 mode 1) forces a whole-tree run and MUST NOT take this exit. An errored read — `field_not_found` for the declared list, or any named `compute-footprint` error — is **indeterminate** (the input is broken, not empty) and MUST NOT take this exit either; it falls through to the whole-tree fallback below.

**Case (a) — both reads successful, no whole-tree trigger fired, zero skill paths in the union after filtering** (the plan touched and declared no skill and no trigger file): log, record the step as done, and return success:

```bash
python3 .plan/execute-script.py plan-marshall:manage-logging:manage-logging \
  work --plan-id {plan_id} --level INFO \
  --message "[STATUS] (project:finalize-step-plugin-doctor) No skill changes detected. Skipping plugin-doctor quality-gate"
```

`{worktree_path}` is the value Step 1 resolved. Resolve the HEAD SHA immediately before marking done, per § HEAD-dependency:

```bash
git -C {worktree_path} rev-parse HEAD
```

Capture stdout as `{sha}` and forward it via `--head-at-completion`:

```bash
python3 .plan/execute-script.py plan-marshall:manage-status:manage-status mark-step-done \
  --plan-id {plan_id} --phase 6-finalize --step project:finalize-step-plugin-doctor --outcome done \
  --display-detail "no skill changes detected" \
  --head-at-completion {sha}
```

**Case (b) — either read returns `status: error`** (`error: field_not_found` for the declared list, or any named `compute-footprint` error — indeterminate scope, not empty): do NOT take the skip-clean exit and do NOT record `--outcome done --display-detail "no skill changes detected"` off a broken read. Instead, fall back to gating the whole tree so structural lint still runs: log the indeterminate-read fallback naming which read failed and its error, proceed to Step 4, then in Step 5 run the `quality-gate` with **no `--paths` scoping** (whole-tree gate) against the resolved `--marketplace-root`. `{read}` is `realized footprint` or `affected_files`:

```bash
python3 .plan/execute-script.py plan-marshall:manage-logging:manage-logging \
  work --plan-id {plan_id} --level WARNING \
  --message "[STATUS] (project:finalize-step-plugin-doctor) Gate scope indeterminate: the {read} read failed ({error}), so the union of realized footprint and affected_files cannot be formed. Falling back to whole-tree plugin-doctor quality-gate"
```

### Step 4: Regenerate a worktree-fresh executor

Reuse the `worktree_path` Step 1 resolved — the raw returned value, before the `.` substitution. It also determines the `--marketplace-root` passed to Step 5:

- **Non-empty `worktree_path`** (worktree-backed plan) — Step 5 uses `--marketplace-root {worktree_path}/marketplace` (the parent of `bundles/` inside the worktree, NOT `bundles/`), so the gate runs against the in-progress edits.
- **Empty `worktree_path`** (main-checkout flow) — Step 5 uses `--marketplace-root marketplace`. Skip the executor regeneration below and proceed to Step 5.

When `worktree_path` is non-empty, replace the worktree's `.plan/execute-script.py` symlink (which points at the main-checkout executor) with a worktree-bound executor so the `manage-invocation-invalid` rule probes `--help` against the worktree's argparse:

```bash
python3 .plan/execute-script.py plan-marshall:tools-script-executor:generate_executor generate \
  --marketplace-root {worktree_path}
```

This mirrors `test/conftest.py::_ensure_executor_present` on CI. Regeneration failure is **non-fatal**: log a WARN line and proceed to Step 5 with the existing executor.

```bash
python3 .plan/execute-script.py plan-marshall:manage-logging:manage-logging \
  work --plan-id {plan_id} --level WARNING \
  --message "[STATUS] (project:finalize-step-plugin-doctor) Worktree executor regeneration failed. Gating against existing executor"
```

### Step 5: Run the quality-gate

**Scoped invocation** (the common case — no Step 2.5 whole-tree trigger fired, both Step 1 reads succeeded and Step 2 yielded one or more skill directories from their union): run the plugin-doctor `quality-gate` scoped to the skill directories extracted in Step 2, against the marketplace root resolved in Step 4 (`{worktree_path}/marketplace` for a worktree, `marketplace` for the main checkout).

**Cross-skill divergence WARNING (scoped mode only) — emit BEFORE the scoped gate.** Because the scoped run cannot evaluate plugin-doctor's cross-skill rules (Step 2.5, "Cross-skill divergence gap"), emit a loud finalize WARNING recording that scoped mode did not gate the cross-skill rule class. Emit it in scoped mode ONLY (never for either whole-tree mode, which already covers cross-skill rules), and emit it **before** running the scoped gate below so it fires regardless of the scoped gate's pass/fail outcome — a failing scoped gate records `failed` and aborts finalize (see below), so a warning placed after the invocation would never fire on a red gate. It names the rules that were NOT run, so a #915-class scoped-green / whole-tree-red divergence is surfaced at finalize rather than first at CI. `{N}` is the count of scoped skill directories:

```bash
python3 .plan/execute-script.py plan-marshall:manage-logging:manage-logging \
  work --plan-id {plan_id} --level WARNING \
  --message "[STATUS] (project:finalize-step-plugin-doctor) scoped plugin-doctor cannot detect cross-skill divergence — scoped mode gated skill-local rules over {N} skill dir(s) only. Cross-skill rules whose counterpart lives outside --paths were NOT evaluated. A cross-skill invariant broken by this change would surface first at whole-tree CI (PR #915 class)."
```

After the WARNING is emitted, run the scoped gate:

```bash
python3 .plan/execute-script.py pm-plugin-development:plugin-doctor:doctor-marketplace \
  quality-gate --paths {space-separated skill directory paths} --marketplace-root {marketplace root}
```

**Whole-tree invocation** (either whole-tree mode from Step 2.5 — a whole-tree trigger of either family fired, OR the indeterminate case of Step 3 Case (b) where either scope read errored — `field_not_found` for the declared list, or a named `compute-footprint` error): run the `quality-gate` with **no `--paths` scoping** against the same resolved marketplace root, so the structural lint runs over the whole tree — catching a doctor / plan-doctor rule change that breaks an otherwise-untouched skill (F1), catching a finding raised by a changed target registration, bundle manifest or agent file wherever it is anchored (verdict-input), and not false-skipping off a broken scope-deriving read (indeterminate):

```bash
python3 .plan/execute-script.py pm-plugin-development:plugin-doctor:doctor-marketplace \
  quality-gate --marketplace-root {marketplace root}
```

Parse the TOON output. The violation signal is `status: fail` (the script also exits 1) OR `total_issues > 0`. On a violation, log the failure, record the step outcome `failed`, and exit with `status: error` so phase-6-finalize aborts **before** `default:commit-push`:

```bash
python3 .plan/execute-script.py plan-marshall:manage-status:manage-status mark-step-done \
  --plan-id {plan_id} --phase 6-finalize --step project:finalize-step-plugin-doctor --outcome failed \
  --display-detail "plugin-doctor: {total_issues} violations"
```

On `status: pass` / `total_issues: 0`, log, record the step as done, and exit success. Resolve the HEAD SHA immediately before marking done, per § HEAD-dependency (`{worktree_path}` is the value resolved in Step 1; substitute `.` when it is empty):

```bash
git -C {worktree_path} rev-parse HEAD
```

Capture stdout as `{sha}` and forward it via `--head-at-completion`:

```bash
python3 .plan/execute-script.py plan-marshall:manage-status:manage-status mark-step-done \
  --plan-id {plan_id} --phase 6-finalize --step project:finalize-step-plugin-doctor --outcome done \
  --display-detail "plugin-doctor clean: {N} skills gated" \
  --head-at-completion {sha}
```

## Error Handling

| Scenario | Action |
|----------|--------|
| Missing `pm-plugin-development` bundle | Fatal config error — the project opted into the wrapper without the dependency |
| Empty `worktree_path` (main-checkout flow) | Skip Step 4 regeneration — the executor already reflects the current checkout; proceed to the scan |
| Worktree executor regeneration fails | Non-fatal — log WARN and gate against the existing executor; finalize does not hard-block on a mapping refresh |
| A Step 1 union entry matches an F1 pattern of the Step 2.5 trigger table — a plugin-doctor / plan-doctor analyzer or rule script (Step 2.5 mode 1) | Whole-tree mode: do NOT skip-clean even when no skill dir survived Step 2, and do NOT scope when one did; run the whole-tree `quality-gate` (Step 5, no `--paths`) so a rule change that breaks an untouched skill is caught, then record the outcome from that gate run |
| A Step 1 union entry matches a verdict-input pattern of the Step 2.5 trigger table — a target package's `__init__.py`, a bundle's `plugin.json`, or a `CLAUDE.md` / `AGENTS.md` (Step 2.5 mode 1) | Whole-tree mode: do NOT skip-clean even when no skill dir survived Step 2, and do NOT scope when one did; run the whole-tree `quality-gate` (Step 5, no `--paths`) so a finding anchored outside the union's skill directories is caught, then record the outcome from that gate run |
| The union renames or deletes a link target outside every skill directory and matches no trigger pattern | Not covered by any trigger (Step 2.5, "What no trigger covers"): the run skips clean or runs scoped, and a link broken by the change is reported by the whole-tree gate in CI |
| Scoped mode selected (Step 2.5 mode 3 — the common case) | Emit the loud cross-skill divergence WARNING (`[STATUS] ... scoped plugin-doctor cannot detect cross-skill divergence`) recording that cross-skill rules whose counterpart lives outside `--paths` were NOT evaluated — fired regardless of the scoped gate's pass/fail — then run the scoped `quality-gate` and record its outcome. Scoped mode never silently passes as if cross-skill rules were gated; this surfaces the PR #915 divergence class at finalize instead of first at CI |
| Both Step 1 reads succeed, the union of realized footprint and `affected_files` holds zero skill paths after filtering, no whole-tree trigger of either family fired | Skip-clean exit (plan touched and declared no skill and no trigger file) — record `mark-step-done --outcome done --display-detail "no skill changes detected" --head-at-completion {sha}` so the `phase_steps_complete` handshake invariant counts the step as done and a later HEAD advance re-fires it |
| Either Step 1 read returns `status: error` — `field_not_found` for `affected_files`, or `worktree_not_found` / `references_not_found` / `not_a_git_worktree` / `git_error` / `files_out_refused` / `files_out_unwritable` for the realized footprint | Indeterminate: the union cannot be formed, so do NOT skip-clean and do NOT gate on the surviving list alone; fall back to the whole-tree `quality-gate` (Step 5, no `--paths`) so structural lint still runs, then record the outcome from that gate run |
| plugin-doctor `status: fail` / `total_issues > 0` | Fatal — record `mark-step-done --outcome failed --display-detail "plugin-doctor: {total_issues} violations"`, then abort finalize before `default:commit-push` |
| plugin-doctor `status: pass` / `total_issues: 0` | Record `mark-step-done --outcome done --display-detail "plugin-doctor clean: {N} skills gated" --head-at-completion {sha}` |

## Related

- [.claude/skills/finalize-step-sync-plugin-cache/SKILL.md](../finalize-step-sync-plugin-cache/SKILL.md) — sibling pattern for cache sync
- `pm-plugin-development:plugin-doctor` — underlying tool; this wrapper invokes its scopeable `quality-gate --paths` verb (see that skill's `## Canonical invocations`)
- [marketplace/bundles/plan-marshall/skills/phase-6-finalize/SKILL.md](../../../marketplace/bundles/plan-marshall/skills/phase-6-finalize/SKILL.md) — finalize phase that invokes this wrapper
