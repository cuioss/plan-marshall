# Run report — 060-runtime-and-script-substrate-test-reduction (run 03)

**Date (UTC):** 2026-08-16    **Branch:** `chore/060-residue-order-dependence`    **PR:** [#1272](https://github.com/cuioss/plan-marshall/pull/1272)    **Outcome:** partial

A residue run against the open items left by runs 01 ([#1263](https://github.com/cuioss/plan-marshall/pull/1263))
and 02 ([#1265](https://github.com/cuioss/plan-marshall/pull/1265)). It closes the two highest-priority
items — including the only **live** defect in the residue — and leaves the two bulk items open, with a
sharper account of what each actually requires.

**Branch.** Cut fresh from `main` at `02ced6f` on operator instruction, with a `chore/` prefix from the
closed set (this is maintenance/refactoring). It is a **run-created** branch, not the harness-assigned
one, so the closed prefix set governs it. Pushed before the first edit; every commit pushed after.

## What this run closed

| Residue item (run 01/02 numbering) | State |
|---|---|
| **F10** — order-dependent failure in the slice | **FIXED** — the one live defect |
| **F11** — six new `sys.modules` registrations from the D3 sweep | **FIXED**, and two further pre-existing collisions with it |
| Run 01's third D1 group (`sys.stdin` ×3) | **FIXED** |
| D3's remaining preamble findings | **17 → 2**; the 2 that remain are a structural limit, named below |
| **D2** — 53 modules over budget | **still open** — with a new finding on what it costs |
| **D4** parametrization beyond one family | **still open** |

## F10 — the order-dependent failure, fixed

Run 01 recorded this as the highest-priority residue item and did not fix it. It is now fixed, and it
was a **live** failure rather than a latent one:

```text
pytest <the slice's 15 directories, reverse order>
FAILED platform-runtime/test_layout_resolution.py::test_resolve_module_reimport_clean
E   ImportError: module marketplace_paths not in sys.modules
```

**Mechanism.** `conftest.load_script_module` registers the module it builds under its stem
(`test/conftest.py`). `extension-api/test_extension_discovery.py` loaded `marketplace_paths` **by
file**, which replaced the object that other directories import **by name**. A test holding the
displaced object then failed `importlib.reload`, depending on collection order.

**Fix.** Where a module is already importable by name, a plain `import` binds *the* registered object
and cannot displace anything. `marketplace_paths` is imported rather than loaded.

**Verified both ways, and the negative control matters:** the same reverse-order run reproduced the
failure identically at the branch point (`8872700`), which is what establishes it as pre-existing
rather than introduced by the reduction work. After the fix, reverse order passes.

## F11 — module loads displacing shared registrations

The same mechanism, at six sites the D3 preamble sweep introduced: `_load_module` helpers that used a
bare `spec_from_file_location` (which does **not** register) were converted to `load_script_module`
(which does), so those modules began displacing objects that six other directories — owned by
**concurrently-running sibling plans** — import by name.

All six are now plain imports. That also removes the per-module `_load_module` re-implementation B7
forbids, so it is a house-style improvement rather than a revert.

**An audit generalised the finding rather than fixing only the named six.** For every
`load_script_module` call in the slice, it resolves the registered name and asks whether that name is
also plainly importable:

| | collisions |
|---|---:|
| before | 5 |
| after | **3** |

The two removed are the ones with real blast radius: `extension_discovery` (plain-imported by **15**
other test modules) and `_providers_core` (by 3). The 3 that remain register names **no test imports
plainly**, so no object is displaced — recorded rather than churned.

## D3 preambles — 17 → 2

Repo-root constants built by counting directory hops now use `conftest`'s own `TEST_ROOT` /
`PROJECT_ROOT` / `MARKETPLACE_ROOT`. Each chain's depth was **resolved per file** and compared against
the three constants rather than assumed, so a file at a different depth could not be rewritten to the
wrong root.

**The two that remain are a structural limit, not an oversight.** Both load a bundle's `extension.py`,
which lives **directly under the skill directory, not under `scripts/`**. `get_scripts_dir` raises when
a skill has no `scripts/` tree — and `pm-code-intelligence/plan-marshall-plugin` has none — so
`load_script_module`, the remedy the rule's own message names, **cannot address those files at all**.

That also resolves run 01's F7 residue item (`test/pm-code-intelligence/`'s own D3 finding): it is not
fixable by the remedy the rule names. **Proposal for the epic:** either `load_script_module` grows a
way to address a skill file outside `scripts/`, or the rule exempts bundle `extension.py`. Recorded,
not acted on — both are production/standards changes outside a test-refactoring plan.

## A scope violation, caught and reverted

The root-constant rewrite was first run over a glob that reached **beyond this plan's surface** — 45
modules including `phase-6-finalize/`, `plan-marshall/`, and root-level `test/plan-marshall/*.py` files
owned by other plans in the epic.

It was caught by checking the changed set against the plan's Expected surface before committing, and
**all 37 out-of-scope files were reverted**; 9 in-scope files were kept. The scope check was then run
after every subsequent edit and reports **0** out-of-scope files.

Recorded because it is exactly the failure the epic's concurrency contract exists to prevent, and it
came within one commit of happening. The lesson is narrow and mechanical: a sweep's file glob must be
derived from the plan's Expected surface, not from a convenient tree walk.

## D2 — still open, with a new finding

**53 modules remain over the 400-line budget. Nothing was split.**

What this run adds is a measurement that changes what D2 means. The plan says to split by behaviour
cluster and to use the existing test classes as the boundaries. Over the whole slice:

* `platform-runtime/test_claude_runtime.py` — 4,668 lines, **39 classes**, 222 tests in classes, a
  62-line preamble and **23 module-level helpers** that any split must re-home into a
  `_{domain}_fixtures.py` (B10);
* **exactly one class in the entire slice exceeds the budget on its own** —
  `test_claude_runtime.py::TestInstallTerminalTitleHooks` at **663 lines**.

So class-boundary splitting can bring **52 of 53** modules under budget, and the 53rd cannot get there
without splitting a class, which the plan explicitly does not sanction ("use [the classes] rather than
inventing new ones"). That is a bounded, stated exception rather than an open-ended one — and it is the
kind of fact a later run should have before it starts, which is why it is recorded here rather than
discovered again.

## D4 parametrization — still open

223 families at ≥80% skeleton similarity, ~4,554 lines. Unchanged from run 01, including its caveat:
the similarity set includes `script-shared`'s matched positive/negative control pairs, which the plan
forbids collapsing and which scan as duplicates. Each family needs reading.

## Build gate

`git diff --name-only origin/main...HEAD -- '*.py'` non-empty → the gate applies. `./pw quality-gate`
ran clean before every commit (`ruff … All checks passed!`, `mypy … Success: no issues found in 408
source files`, `SPDX-header check passed`).

Full `./pw verify`: **`=== verify: SUCCESS ===`**, whole-tree **20,329 passed, 14 skipped, 0 failed**
in 359s, all three sub-steps including `test-compile` (mypy over the whole test tree).

## Verification

| Arm | Result |
|---|---|
| Forward order, serial | **3,827 passed** |
| **`-n auto`** | **3,827 passed** |
| **Reverse directory order** | **3,827 passed** — was `1 failed, 3826 passed` before F10 |
| Collected count | **3,827**, unchanged throughout |

`plugin-doctor test-conventions` over the slice: **73 → 58** findings
(`test-module-preamble-boilerplate` 17 → 2; `test-module-line-budget` 53, unchanged because nothing was
split; `test-docstring-historical-prose` 0; `subprocess-pythonpath` 3).

The **randomised** arm remains unavailable — `pytest-randomly` is genuinely not installed here, checked
rather than assumed. Reverse-order collection is a sufficient reordering to have caught F10, and did.

## Findings

| # | Source | Finding | Disposition |
|---|---|---|---|
| H1 | Reverse-order run | `test_extension_discovery.py` loaded `marketplace_paths` by file, displacing the shared registration and breaking `importlib.reload` in another directory | **Fixed** — plain import. Confirmed pre-existing by reproducing at `8872700` |
| H2 | Collision audit | The D3 sweep newly registered six names that sibling plans' directories import plainly | **Fixed** — plain imports; also removes the `_load_module` re-implementation B7 forbids |
| H3 | Collision audit | Two further pre-existing collisions with real blast radius (`extension_discovery` ×15 importers, `_providers_core` ×3) | **Fixed** |
| H4 | Collision audit | 3 collisions remain | **Recorded, not churned** — each registers a name no test imports plainly, so nothing is displaced |
| H5 | This run's own sweep | The root-constant rewrite initially touched 37 files outside the plan's Expected surface | **Reverted before commit**; scope check now run after every edit, reporting 0 |
| H6 | Preamble conversion | Two findings are unfixable by the remedy their own rule names: a bundle `extension.py` is not under `scripts/`, and `get_scripts_dir` raises for a skill with no `scripts/` tree | **Recorded with a proposal** (widen the helper, or exempt the shape). Closes run 01's F7 as *not fixable as specified* |
| H7 | D2 analysis | Exactly one class in the slice (663L) exceeds the module budget alone, so class-boundary splitting reaches 52 of 53 modules, not 53 | **Recorded** — a bounded exception a later run should know before starting |
| H8 | Rewrite tooling | The chain rewrite produced `TEST_ROOT = TEST_ROOT` self-assignments in 3 modules, and its "locally defined" guard then suppressed the needed import | **Fixed** — caught by collection errors, not by review |

## Reviewer participation

_(completed at the merge gate)_

## Cost

* **Tokens:** not available to the agent in this session.
* **Wall-clock:** ~1h.
* **Population:** one Claude Code cloud session continuing after #1265 merged. ⛔ Not comparable to a
  plan-marshall `metrics.toon` total.

## Contract check (Step 9)

_(completed as the final pre-merge commit)_

## Residue

1. **D2 — 53 modules over budget**, with H7's bound: 52 reachable by class-boundary splitting, 1 not.
2. **D4 parametrization** — 223 families, ~4,554 lines.
3. **The two structurally-unfixable preamble findings** (H6) — need a helper or standards change.
4. **3 remaining `sys.modules` registrations** (H4) — latent; no plain importer today.
5. **The randomised hermeticity arm** — `pytest-randomly` absent in this environment.
6. **D4's cold read** — still not performed.
7. **The partition defect** — `test/pm-code-intelligence/` still needs assigning to a plan by the epic
   owner; this run did not re-claim it.
8. **Per-slice line floors** (run 01 F5) and the **cloud-plan-lane amendment** (run 01 § What have we
   learned) — both with the operator.
