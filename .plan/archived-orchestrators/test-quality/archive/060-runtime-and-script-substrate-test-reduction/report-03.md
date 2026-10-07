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
| H9 | PR review (`sourcery-ai`) | `untrusted-ingestion/test_validate_struct.py` mutated `sys.path` at import time | **Fixed by removal.** The insert bought nothing — the module imports only `conftest` (importable because pytest makes it so) and `toon_parser` (resolved through the marketplace path `conftest` assembles). Deleting it leaves no mutation to scope or revert, which suits this PR's theme better than a fixture would |
| H10 | PR review (`coderabbitai`) | The quote-path executor test stubbed `get_shared_module_dirs` with a hardcoded five-entry list **mirroring the production function's own `shared_skills`**. A mirror goes stale the moment a shared skill is added, and the test would then validate with incomplete import coverage **while still passing** | **Fixed** — the stub now derives from `_gen.get_shared_module_dirs(MARKETPLACE_ROOT)` with a non-vacuity assertion. Verified the derivation returns the same five directories. **Pre-existing**: the list was present at `02ced6f`; this PR only converted its `Path(__file__)` chain, which is what put it in the diff. The reviewer proposed `conftest._MARKETPLACE_SCRIPT_DIRS` as the source — that is *every* scripts dir in the marketplace, not the five-entry subset the stub represents, so the function being stubbed is the right authority |

## Reviewer participation

Population derived from the `author_login` of each
`marketplace/bundles/plan-marshall/skills/automatic-review/standards/{bot_kind}.md` registry doc.
**M = 3.** Verdicts read from the authors' own comment bodies.

| Reviewer (`author_login`) | Verdict | Reopens? | Body evidence |
|---|---|---|---|
| `sourcery-ai` | **`reviewed`** | — | Two high-level suggestions on path centralisation and `sys.path` scoping |
| `cuioss-review-bot` | **`reviewed`** | — | "PR Reviewer Guide 🔍 — PR contains tests / No security concerns / No major issues detected" |
| `coderabbitai` | **`reviewed`** | — | Rate-limited on first pass, then **re-requested and reviewed**: two findings, both fixed |

**Coverage: 3 of 3 — no shortfall to disclose.**

**The re-request is why, and it is worth recording as method rather than luck.** CodeRabbit's first
response was a refusal whose notice read *"Next review available in: 46 seconds"* — a `Reopens? yes`
refusal. Rather than bank a 2-of-3 and disclose it, the run posted the registry's declared
`trigger_comment` (`@coderabbitai review`) once the window had passed. That converted the shortfall
into full coverage **and** produced the single most substantive finding of the round (H10 below), which
a disclosed 2-of-3 would have shipped without.

**Comment disposition — 2 review threads plus a top-level review, all handled:**

| Source | Finding | Disposition |
|---|---|---|
| `sourcery-ai` | Wrap the remaining `sys.path.insert` so mutations are scoped/reverted | **Fixed by deletion** (H9) — the insert was not needed at all, which is strictly better than scoping it |
| `sourcery-ai` | Centralise deep marketplace paths into `conftest` helpers | **Replied, not actioned** — `test/conftest.py` is plan `020`'s surface and the epic forbids editing it here. Converges on this report's own H6 proposal, and the reply sharpens it: the gap is files *outside* `scripts/`, not the `scripts/` case `get_scripts_dir` already covers |
| `coderabbitai` | `shared_dirs` mirrors the production shared-module set and can drift | **Fixed** (H10), with a different source than proposed |
| `coderabbitai` | MD040 — fenced block without a language | **Fixed** |

## Cost

* **Tokens:** not available to the agent in this session.
* **Wall-clock:** ~1h.
* **Population:** one Claude Code cloud session continuing after #1265 merged. ⛔ Not comparable to a
  plan-marshall `metrics.toon` total.

## Contract check (Step 9)

| Step | Verdict | Artifact |
|---|---|---|
| 1 Skills loaded | **done** | `cloud-plan-lane` governs; domain skills carried from runs 01–02 |
| 2 Branch | **done** | `chore/060-residue-order-dependence`, **run-created** from `main` at `02ced6f` per operator instruction, prefix from the closed set. Pushed before the first edit |
| 3 Plan directory | **done** | Established by run 01; this run adds `report-03.md` |
| 4 Implement | **done** | 8 commits, each carrying the trailer |
| 4 Per-commit gate | **done** | `./pw quality-gate` clean before every `*.py` commit |
| 4 Pushed | **done** | No unpushed commits |
| 5 Build gate | **done** | `=== verify: SUCCESS ===`, 20,329 passed / 0 failed |
| 6 Verification sub-agent | **NOT DISPATCHED** | Reported as not done. The PR review substituted in practice and found two real defects, but it is not the same gate and this row does not pretend otherwise |
| 7 PR cycle | **done** | PR #1272; all three surfaces read; every comment fixed or answered; participation 3-of-3 |
| 7 Bot-review label | **correctly omitted** | Diff contains `*.py` |
| 8 Merge gate | **done** | Required check green on head; no open comment; report committed last |
| 8 Bridge | **done** | Nothing written under `doc/plans/` outside this plan's directory |
| 9 This check | **done** | This table |

**Scope discipline, checked mechanically rather than asserted:** after every edit, the changed set was
diffed against the plan's Expected surface. It reported 37 out-of-scope files once (§ "A scope
violation"), which were reverted, and **0** on every check since.

**Reported as NOT done:** the Step 6 verification sub-agent; D2; D4 parametrization; the randomised
hermeticity arm; D4's cold read.

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

## Disposition update (2026-08-17) — appended by the epic re-scoping run

Appended after these runs closed, by the run that read every landed report in this epic and re-scoped
the remaining plans. It covers the residue of **all three** runs of plan `060` and does not revise
anything above.

| Item from run 01, 02 or 03 | Disposition |
|---|---|
| Run 01 § F5 — the 25% floor is unreachable for this slice; set per-slice floors from each slice's own composition | **Acted on, epic-wide, and further than proposed.** Every percentage floor is retired rather than re-derived: the epic README § "Why there is no line floor" carries the arithmetic for all six slices, and this slice is one of the three whose floor exceeded its entire comment-and-docstring volume. This report's measurement — mean test 11.7 lines, already inside **B2**, with every remaining lever summing to ~10.7% — is part of what settled it |
| Run 01 § F7 and run 03 § Residue 7 — `test/pm-code-intelligence/` is claimed by no plan; run 01's claim was "a decision about *this run*, not a durable partition fix" | **Closed, durably.** It is assigned to plan `080`'s slice and named in `080`'s Expected surface, with the reason recorded in the epic README's partition section, which states explicitly that it is **not** an exclusion but an assignment to `080`'s slice. Four consecutive runs each halted on it and were told to proceed, because each disposition was about that run; this one is about the partition |
| Run 03 § H4 — three `sys.modules` registrations remain, latent because no test imports those names plainly, and no guard exists | **Owner assigned: plan `090` § D3**, which must demonstrate the guard **failing** by giving one of those three a plain importer and watching it go red — a detector that has never been observed detecting is not a guard |
| Run 03 § H6 — two preamble findings are unfixable by the remedy their own rule names, because a bundle `extension.py` is not under `scripts/` | **Owner assigned: plan `090` § D2**, on exactly the fork this report proposed: widen the helper, or exempt the shape — and state which was taken and why the other was rejected |
| Run 02 § Residue — 27 of the 29 `parse_ns` exceptions are blocked on production modules with no parser seam; "a published `build_parser()` would unblock all 14" — a subtotal run 02's own G8 row records as corrected to **15** in `f4bf557`, which is the figure plan `090` carries | **Owner assigned: plan `090` § D1**, which publishes a seam on every module a re-derived `ParserSeamNotFound` collection names. It is why `090` should land before `070` and `080` start: those two slices carry roughly 502 and 222 hand-built namespaces and would hit the same wall |
| Run 03 § "D2 — still open, with a new finding" — 53 modules over budget, of which class-boundary splitting reaches 52; exactly one class (663 lines) exceeds the budget alone | **Owner assigned: plan `100`.** The bound is carried into that plan verbatim as the kind of fact a later run should have before it starts. Re-derived for this slice today: **53** over budget, matching this report's own statements of that figure |
| Run 01 § F6 and run 03 § Residue 6 — D4's required cold read, never performed; and D4 parametrization, ~223 families at ≥80% similarity | **Still open in this plan's slice, and indexed** in the epic README § "What the executed half left open", including the caveat that the similarity set contains matched control pairs which must **not** be collapsed |
| Run 03 § Residue 5 — the randomised hermeticity arm, unrun because `pytest-randomly` is absent | **Routed to plan `110` § D5**, which owns the genuinely-absent-dependency shape: it records the dependency proposal (a third-party dependency is a user-approval step no run may take) and covers the contract another way meanwhile |
| Run 01 § "What have we learned" — generalise the positive-control rule to every "unavailable" claim | **Landed in the lane contract**, which now carries the unreadable-versus-empty distinction and the positive-control discipline. This run's false "`pytest-xdist` unavailable" is what bought it |
| Run 03 § "A scope violation, caught and reverted" — a sweep's file glob reached 37 modules outside the plan's surface | **Carried forward as a stated hazard**: plan `100` § D2 and both re-scoped reduction plans require a sweep's glob to be derived from the plan's Expected surface, and `100` takes one slice per run partly so the surface stays small enough to check |
