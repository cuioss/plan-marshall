# Consumer Sweep for Delete/Rename Deliverables

Outline-time procedure that ensures every cross-bundle consumer of a deleted or renamed public symbol is enumerated in the deliverable's `Affected files` list before phase-3-outline finalizes. This standard exists to close a recurring failure mode in which a plan deletes or renames a public symbol in shared core code, the deliverable lists only the owning module's files, and downstream tasks discover the breakage opportunistically — silently expanding scope or shipping a half-converted codebase.

> **Why this matters**: Consumer sweeps are the difference between a plan that ships clean and a plan whose verification phase (or worse, the next adjacent sweep) discovers a half-rewritten public surface. The sweep adds seconds at outline time and saves a fix-loop iteration during execute.

---

## 1. Trigger Heuristic

The consumer sweep is **mandatory** when a deliverable's `Change per file` field, `Refactoring` field, or title text contains any of the following patterns applied to a public/exported symbol (a function, class, constant, module-level name, or skill notation that is visible across module boundaries):

| Pattern | Examples |
|---------|----------|
| **Delete language** | `delete`, `remove`, `drop`, `git rm`, `eliminate`, `purge` |
| **Rename language** | `rename`, `replaced by`, `migrate from X to Y`, `renamed to` |
| **Replacement language** | `replace X with Y`, `swap X for Y` (when X is a public symbol) |

**Scope qualifier**: The trigger applies only to **module-level public symbols** — symbols declared at the top of a Python module (function, class, constant), public method on an exported class, exported skill notation (`bundle:skill:script`), or skill loader directive (`Skill: bundle:skill`). It does NOT apply to:

- Local variables, helper functions inside a function body, or private symbols (those starting with `_`).
- File-level renames that do not change a public symbol (e.g., a markdown standard renamed for clarity with no notation impact).
- Documentation-only changes (typo fixes, comment edits) that do not alter a public surface.

When the trigger heuristic matches, you MUST run the Sweep Procedure (§2) before finalizing the deliverable. When the trigger does not match, the sweep is optional and may be skipped without log entry.

---

## 2. Sweep Procedure

### 2a. Extract symbol names

From the deliverable's `Change per file`, `Refactoring`, or title, extract every public symbol that the delete/rename pattern applies to. For function-level renames like `replace load_derived_data with iter_modules`, extract both the old and new symbol names — the old name drives the consumer sweep, the new name is informational.

For skill notations, extract the full three-part (`bundle:skill:script`) or two-part (`bundle:skill`) form.

### 2b. Run structured discovery first

For every extracted symbol, run the structured architecture inventory:

```bash
python3 .plan/execute-script.py plan-marshall:manage-architecture:architecture \
  find --pattern "{symbol}" --audit-plan-id {plan_id}
```

The architecture verb returns module-level matches and is the canonical first pass. Record every consumer file from the `results` list.

### 2c. Run grep fallback for sub-module references

The architecture inventory deliberately elides sub-module path components (e.g., script files inside `skills/{name}/scripts/`, agent loader directives inside skill markdown). To catch references the structured query misses, run a grep fallback against the worktree root:

```bash
grep -rn "{symbol}" marketplace/bundles/
```

For skill notations specifically, also sweep `marshal.json` and `.plan/`:

```bash
grep -rn "{bundle}:{skill}:" marshal.json .plan/
```

For `Skill:` loader directives in markdown:

```bash
grep -rn "^Skill:[[:space:]]*{bundle}:{skill}" marketplace/ .claude/
```

Each grep call is a separate Bash invocation (one command per call — never combined with `&&`, `;`, or pipes). Use `architecture find` first; the grep calls exist to narrow into sub-module components and content searches the architecture verb cannot resolve.

### 2d. Collect every consuming file

Merge results from §2b and §2c into a single deduplicated list. Discard `__pycache__` paths, vendored dependencies, and the deliverable's own `affected_files` entries (which are already in scope by definition).

### 2e. Distinguish consumers from the owning module

For each consumer, determine whether it sits in the **same bundle** as the symbol's owning module, or in a **different bundle** (cross-bundle consumer). Cross-bundle consumers are the high-risk class — they are the consumers most likely to be missed by a deliverable that scopes itself to the owning module.

---

## 3. Output Format

Every consumer (same-bundle or cross-bundle) discovered in §2 becomes an explicit entry under the deliverable's `**Affected files:**` list. The list is **flat** in the deliverable markdown — do NOT introduce nested headings or sub-lists per bundle. To preserve readability, you MAY add an HTML comment that groups entries by bundle, but the markdown bullet list itself stays flat:

```markdown
**Affected files:**
<!-- plan-marshall (owning module) -->
- `marketplace/bundles/plan-marshall/skills/manage-architecture/scripts/_architecture_core.py`
<!-- pm-dev-java (cross-bundle consumer) -->
- `marketplace/bundles/pm-dev-java/skills/manage-maven-profiles/scripts/profiles.py`
- `test/pm-dev-java/manage-maven-profiles/test_profiles.py`
```

The HTML comment is for human reviewers; phase-4-plan and downstream tooling parse only the bullet list. The flat structure preserves compatibility with the `**Affected files:**` parsing convention used throughout the outline standards.

For each consumer, the `**Change per file:**` field MUST describe the migration explicitly — not "update consumer", but "rewrite `list_profiles` to use `iter_modules` + `load_module_derived` per the new per-module helper contract; remove the `load_derived_data` import".

---

## 4. Worked Example: `load_derived_data` (lesson 2026-04-30-23-001)

The driving failure case for this standard came from plan `phase-a-arch-split`, which split monolithic `derived-data.json` into a per-module layout. TASK-2's deliverable removed `load_derived_data` and `save_derived_data` from `_architecture_core` and added `load_module_derived` / `save_module_derived` / `load_project_meta` / `save_project_meta`. The deliverable's `Affected files` enumerated only the manage-architecture core files — the pm-dev-java consumer (`profiles.py::list_profiles`) was not listed.

Consequence: TASK-9 ran `module-tests pm-dev-java` and pytest collection failed with `ImportError: cannot import name 'save_derived_data' from '_architecture_core'`. The TASK-9 dispatch then silently expanded scope to include the production rewrite of `profiles.py` — violating the "task description = task scope" contract and burning an extra fix-loop iteration.

### Trigger evaluation

The deliverable's `Change per file` contained "remove `load_derived_data`" and "replaced by `load_module_derived` / `load_project_meta`". Both **delete** and **rename** language applied to a module-level public function — trigger fires.

### Sweep procedure

`architecture find --pattern "load_derived_data"` would have returned the manage-architecture core file (already in scope) and elided the pm-dev-java sub-module reference. The grep fallback `grep -rn "load_derived_data" marketplace/bundles/` would have surfaced:

```
marketplace/bundles/pm-dev-java/skills/manage-maven-profiles/scripts/profiles.py:14:from _architecture_core import load_derived_data
test/pm-dev-java/manage-maven-profiles/test_profiles.py:8:from _architecture_core import load_derived_data, save_derived_data
```

### Output

The deliverable's `Affected files` would gain (using the flat-with-comment format from §3):

```markdown
**Affected files:**
<!-- plan-marshall (owning module) -->
- `marketplace/bundles/plan-marshall/skills/manage-architecture/scripts/_architecture_core.py`
<!-- pm-dev-java (cross-bundle consumer) -->
- `marketplace/bundles/pm-dev-java/skills/manage-maven-profiles/scripts/profiles.py`
- `test/pm-dev-java/manage-maven-profiles/test_profiles.py`
```

And the `Change per file` would gain explicit migration text for the cross-bundle consumer:

```markdown
- `profiles.py`: rewrite `list_profiles` to use `iter_modules(project_dir)` + `load_module_derived(name, project_dir)` per the per-module helper contract; remove `load_derived_data` import; add `DataNotFoundError` skip for half-written entries.
- `test_profiles.py`: rewrite `create_test_derived_data` to seed via `save_project_meta` + `save_module_derived`; remove `save_derived_data` import; update module docstring to reference per-module layout.
```

With the consumer sweep applied at outline time, TASK-9 would never have hit the `ImportError`, and scope would have stayed pinned to the deliverable's stated text. The consumer-sweep step would add roughly two seconds of outline-time grep work and save a fix-loop iteration during execute.

---

## 5. Cross-References

- `outline-workflow-detail.md` — Step 7 (Simple Track) and Step 10 (Complex Track) call this standard before deliverable finalization.
- `change-feature.md` and `change-tech_debt.md` — discovery sub-sections cross-reference this standard.
- `plan-marshall:phase-3-outline/SKILL.md` — Complex Track table row for Step 10 has a one-line callout pointing here.
- `plan-marshall:q-gate-validation-agent` — `consumer_sweep_completeness` check enforces the trigger and output requirements at Q-Gate time.
- Driving lesson: `2026-04-30-23-001` (TASK-9 scope expanded silently — pm-dev-java profiles.py needed migration to per-module layout).
