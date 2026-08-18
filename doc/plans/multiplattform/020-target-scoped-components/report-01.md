# Run report — 020-target-scoped-components (run 01)

**Date (UTC):** 2026-08-18    **Branch:** `claude/target-scoped-components-k3qt57`    **PR:** _pending_    **Outcome:** _in progress_

## Skills loaded

Loaded by reading the bundle source path (the `plan-marshall` plugin is not installed in this
cloud session, so `Skill: {bundle}:{skill}` notation was not attempted).

| Skill | Why |
|---|---|
| `plan-marshall:ref-code-quality` | Always |
| `pm-plugin-development:plugin-script-architecture` | Always |
| `pm-dev-python:python-core` | Python production code |
| `pm-dev-python:pytest-testing` | Python tests |
| `pm-plugin-development:plugin-architecture` | `SKILL.md` / bundle structure (D4) |
| `plan-marshall:persona-implementer` | Production-code work identity |

Every skill resolved at its bundle path; none was unobtainable.

## Claim labels — re-derived before building

The plan's claim table required re-derivation. All were re-checked against the tree at HEAD of
`origin/main`:

| Claim | Verdict |
|---|---|
| No `targets:` frontmatter filter exists anywhere under `marketplace/targets/` | **CONFIRMED.** No `targets` handling in any `marketplace/targets/**/*.py` or `*.json`, and no bundle component declared the field. The premise held; the plan was not halted. |
| The Claude target is a verbatim mirror gated by `run_equality_check` | **CONFIRMED.** `claude/target.py::generate` mirrors via `emit_bundle_verbatim` and gates on `equality_check.run_equality_check`. |
| `TARGET_REGISTRY` holds `claude`, `opencode`, `pr-agent` | **CONFIRMED** as a lead only. D1/D2 iterate the registry; no enumeration was written. |
| `tools-fix-intellij-diagnostics.md` has YAML frontmatter incl. `mcp__ide__getDiagnostics` | **CONFIRMED.** |
| `pr-agent` emits no per-component bundle tree | **CONFIRMED.** `pr_agent/target.py` overrides `emits_bundle_tree` to `False` and emits one `.pr_agent.toml`. |
| `plugin-doctor` frontmatter validation would flag an unknown `targets:` key today | **REFUTED.** The doctor carries no closed-frontmatter-key rule at all — no allowlist of permitted keys exists in any analyzer — so an unknown key was neither flagged nor validated. D4 therefore had to ADD validation rather than extend an existing allowlist. |

## Deliverables

| Deliverable | What was done | Commit | Verification state |
|---|---|---|---|
| **D1 — filter mechanism** | New `marketplace/targets/component_targets.py` parses the `targets:` declaration and answers `emits_to(path, target_name)`. Both component-tree-emitting targets consult it: the Claude verbatim emitter (`excluded_emission_roots` + `is_under_any`, skipping a scoped-out file or a whole scoped-out skill directory) and its manifest generator (`plugin_json_gen` drops the same entries), and the OpenCode emitter (per-skill / per-agent / per-command skip). The governed set is derived from `TARGET_REGISTRY` filtered by each target's `emits_bundle_tree` capability — never enumerated. Absent field still means every target. | `fab9611` | `test_component_targets.py` (37 collected), `test_target_scoped_emission.py` (14 collected) |
| **D2 — fail-closed validation** | `_validate` rejects an unknown target name, an empty list, and a list naming only non-component-tree targets. Every message names the component path and the offending value. Validation fires on every path that READS components: both component-tree targets' emit paths and the Claude target's validate-only mode (which re-walks each bundle's components for this check alone). A `pr-agent`-only run does NOT validate: it opens skill manifests to harvest rule text, but never asks whether a component is in scope, because it emits no component. The doctor rule is the authoring-time net there. | `fab9611` | `test_component_targets.py` + `test_target_scoped_emission.py::test_generation_fails_*` |
| **D3 — first consumer** | `marketplace/bundles/plan-marshall/commands/tools-fix-intellij-diagnostics.md` declares `targets: [claude]`. | `fab9611` | Asserted by generation-output listing (below) |
| **D4 — authoring surface** | New `targets-scope-invalid` plugin-doctor rule (`_analyze_target_scope.py`), registered in `_rule_registry.py` and wired into both the quality gate and analyze mode, with rows in `rule-provenance.md` and `rule-catalog.md` and a firing positive fixture in `_fixtures.py`. The field, its semantics, its validation table, and the three-condition admission test are documented in `plugin-architecture/references/frontmatter-standards.md` § "Target Scoping". | `fab9611` | `test_analyze_target_scope.py` (24 collected); the doctor runs clean over the real tree with D3's declaration in place |

### D3 generation-output listing (the plan's own "Done when" evidence)

`python3 marketplace/targets/generate.py --target all --output {dir}` exits **0** (re-derived at `dcd7a2e`):

```text
claude: produced 1166 entries
opencode: produced 1090 entries
pr-agent: produced 1 entries
```

- `{dir}/claude/plan-marshall/commands/` — contains `tools-fix-intellij-diagnostics.md`.
- `{dir}/claude/plan-marshall/.claude-plugin/plugin.json` — `commands` declares
  `./commands/tools-fix-intellij-diagnostics.md`.
- `{dir}/opencode/command/` — the command is **absent**.
- `pr-agent` emits `.pr_agent.toml` only, unaffected by construction.

## Build gate

`git diff --name-only origin/main...HEAD -- '*.py'` reports **17 changed Python files** at the commit
recorded below, so the gate applies.

`./pw verify` — **SUCCESS**, all three sub-steps clean. Re-run after every commit that changed a
Python file; the figures below are from the run at `dcd7a2e`, the last such commit, with the working
tree clean at the time (`git status --porcelain` empty):

- quality-gate: `ruff … All checks passed!`, `mypy … Success: no issues found in 415 source files`,
  `SPDX-header check passed`, plugin-doctor `total_issues: 0`
- test-compile: mypy over 775 test files, clean
- module-tests: **21035 passed, 14 skipped** — 0 failed, 0 errors

No lockfile churn: `git status --porcelain` was empty after the build, and every commit staged
explicit deliverable paths (never `git add -A`).

## Findings

Source key: **V1** / **V2** = pre-PR verification sub-agent, rounds 1 and 2. **S** = self-found
(mutation sweep or my own re-read). One row per instance.

### Round 1 — 12 findings, all fixed

| # | Source | Finding | Disposition |
|---|---|---|---|
| A1 | V1 | `component_targets.emits_to` docstring claimed validation runs "whichever target happens to be generating". False on two paths the verifier RAN: a `pr-agent`-only generation, and Claude validate-only mode (which regenerates only the manifest, and the manifest never lists skills, so a skill's bad declaration passed). | **Fixed** — validate-only mode now walks each bundle's components before the equality check, closing the gap rather than only narrowing the sentence; the docstring states what is actually covered. Pinned by `test_validate_only_mode_rejects_an_invalid_skill_declaration`. |
| A2 | V1 | The report's D2 row repeated A1's falsity. | **Fixed** |
| A3 | V1 | Four report figures did not reproduce (emission counts, a test count, the changed-Python-file count, the module-test count). | **Fixed** — re-derived. Went stale AGAIN in the same commit; see R2-03. |
| A4 | V1 | `claude/target.py` emit-mode docstring listed `plugin.json` as the only exception to the byte-for-byte mirror; scoped-out components are another. | **Fixed** — and still under-counted; see R2-05. |
| A5 | V1 | `frontmatter-standards.md` contradicted itself: the new top-level-vs-`metadata:` rule at line 202 vs the unchanged `metadata:` escape-hatch rule below it, with `ext-point-verify.md`'s `verification_profile` as a live counter-example. | **Fixed** — `targets` simply joins the supported-field list, as `profiles` / `priming_preamble` / `composes` did before it; the invented rule is gone. |
| A6 | V1 | Same file called that list "the **runtime** schema — the fields the host platform reads", which is false of `profiles`, `priming_preamble`, and `composes`. That mischaracterisation was the load-bearing premise for A5's rule. | **Fixed** |
| A7 | V1 | `test_every_component_tree_target_honours_the_filter` asserted `component_tree_target_names()` against its own body — the expectation derived from the function under test. The verifier mutation-proved it: replacing the function with a hard-coded enumeration left it green, and it made no emission assertion at all. Its name and docstring claimed a property it did not establish. | **Fixed** — replaced by a sweep that generates through EVERY registered component-tree target and asserts from each target's own emitted-path list, with an anti-vacuity guard. Re-mutated in round 2: deleting a filter call reddens, emitting nothing reddens. |
| A8 | V1 | `coupling-inventory.md` §D said "Until the `targets:` frontmatter mechanism exists, they ship to every target" and listed the now-scoped command as a candidate. | **Fixed** — lead rewritten, `Scoped` column added per candidate with its reason. |
| A9 | V1 | The "declares an empty list" error fired for a file declaring `[claude]` (see B1). | **Fixed** with B1. |
| M1 | V1 | `registered_target_names`'s rationale — a module-level registry import "would close a cycle" — is false; the verifier ran the counterfactual and it imports fine. | **Fixed** — reworded to the true reason (early binding predates every registration and works only because the registry is mutated in place). Re-verified true in round 2. |
| M2 | V1 | "`emits_bundle_tree` … a runtime property no static scan can read" is overstated — it is a literal `return False`. | **Fixed** in the analyzer docstring; survived in two other files, see R2-10/R2-11. |
| C | V1 | Registry derivation governs which target NAMES are legal; it does not make a new target honour the filter, which is per-target wiring. So "a target registered later is covered … never silently bypassed" was a guarantee the code did not provide. | **Fixed** — the obligation is stated on `TargetBase.generate` and as step 6 of the targets README, and A7's replacement sweep fails an unwired target. Round 2 constructed a rogue `emits_bundle_tree=True` target that never calls `emits_to` and confirmed it fails the suite. |
| S1 | S | Every scoping fixture named `claude`, so the CLAUDE emitter's own exclusion path was never taken — it could be deleted with the suite green. | **Fixed** before the round-1 dispatch: mirror-image fixtures scoped to the other target, in commit `7114c24`. |

### Round 2 — 17 findings, all fixed

| # | Source | Finding | Disposition |
|---|---|---|---|
| R2-01 | V2 | Round 1's replacement `emits_to` text said `pr-agent` "reads no component at all". False — `pr_agent/target.py` opens every `*-security` skill's `SKILL.md` to harvest rule text. One falsity replaced by another in the same sentence. | **Fixed** — it reads manifests but never asks whether a component is in scope. |
| R2-02 | V2 | Same falsity, second site: the report's D2 row. | **Fixed** |
| R2-03 | V2 | "15 changed Python files" — 16 at that HEAD, because the round-1 fix commit itself touched `base.py`. A figure round 1 had just re-derived went stale in the same commit. | **Fixed** — re-derived (17) and now stated against a named commit. |
| R2-04 | V2 | "the gate saw the whole branch" was false of HEAD: the recorded `./pw verify` predated the round-1 fix commit. | **Fixed** — the claim now names the commit its figures come from, and `./pw verify` was re-run after the round-2 commit. |
| R2-05 | V2 | Round 1 corrected "one exception" to "two"; still short — variant emission and the excluded cache directories are also exceptions, and `claude/emitter.py`'s docstring already listed them, so the two disagreed. | **Fixed** — the list defers to the emitter rather than restating it. |
| R2-06 | V2 | The new sentence "That list is the **closed** set of supported top-level skill fields" made a pre-existing omission load-bearing: `implements` is a supported skill field, documented fifteen lines below the list it is missing from. | **Fixed** — `implements` added to both copies of the list. |
| R2-07 | V2 | A flow sequence spanning lines (`targets: [claude,` continued next line) was truncated to its first physical line, yielding the token `[claude`. Same class as B1; the round-1 fix reached block sequences and inline comments but not flow sequences. | **Fixed** — both parsers fold continuation lines in; pinned by three tests per suite. |
| R2-08 | V2 | `component_targets._strip_comment`'s comment-vs-value guard had NO test — deleting it left the suite green, so the documented behaviour could regress silently. | **Fixed** — three parametrised cases; deleting the guard now reddens three tests. |
| R2-09 | V2 | Same guard, same gap, in the doctor's copy — whose docstring claims it "mirrors the generator's parser so the two agree", with nothing pinning the agreement. | **Fixed** — same three cases in the doctor suite. |
| R2-10 | V2 | M2's falsity survived verbatim in `rule-catalog.md` § Coverage boundary. | **Fixed** |
| R2-11 | V2 | And again in `rule-provenance.md`'s row. | **Fixed** |
| R2-12 | V2 | Inserting the new rule into the reference-resolution pack falsified its "**Five rules**" lead-in — the pack had six `###` members. | **Fixed** — the rule is promoted out of the pack to its own section; the pack is five again (re-counted: `declared-component-vs-disk`, `plugin-json-orphan-component`, `skill-notation-unresolved`, `notation-bundle-skill-drift`, `recipe-missing-implements`). |
| R2-13 | V2 | The same lead-in says the pack is "NOT included in `quality-gate`"; the new member IS quality-gate-wired, and carried no activation line of its own. | **Fixed** — promoted out, and it now states its own activation. |
| R2-14 | V2 | The lead-in's five-item "each gap resolves to a dead reference at runtime" enumeration did not cover the sixth member — and an invalid declaration is a build-time authoring error, not a dead reference. The rule was mis-filed. | **Fixed** — promoted out, with the reason recorded in its own section. |
| R2-15 | V2 | "**the other four** are marketplace-wide passes wired into `cmd_analyze`" — five, after the insertion. | **Fixed** — promoted out. |
| R2-16 | V2 | `claude/emitter.py`'s new paragraph claimed the manifest entry is dropped in lock-step for every scoped-out component; a skill has none to drop, which `plugin_json_gen.py`'s docstring states correctly. The two contradicted each other. | **Fixed** |
| R2-17 | V2 | `marketplace/targets/__init__.py` carries a second "adding a new target" checklist that round 1 did not update, so an author reading only the package docstring got four steps and no filter obligation. | **Fixed** |

## Reviewer participation

_(filled in after the PR is opened)_

## Cost

_(filled in at close)_

## Contract check (Step 9)

_(filled in at close)_

## What have we learned (Step 9)

_(filled in at close)_

## Residue

_(filled in at close)_
