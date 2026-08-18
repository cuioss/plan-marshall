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
| **D1 — filter mechanism** | New `marketplace/targets/component_targets.py` parses the `targets:` declaration and answers `emits_to(path, target_name)`. Both component-tree-emitting targets consult it: the Claude verbatim emitter (`excluded_emission_roots` + `is_under_any`, skipping a scoped-out file or a whole scoped-out skill directory) and its manifest generator (`plugin_json_gen` drops the same entries), and the OpenCode emitter (per-skill / per-agent / per-command skip). The governed set is derived from `TARGET_REGISTRY` filtered by each target's `emits_bundle_tree` capability — never enumerated. Absent field still means every target. | `fab9611` | `test_component_targets.py` (41 collected), `test_target_scoped_emission.py` (14 collected) |
| **D2 — fail-closed validation** | `_validate` rejects an unknown target name, an empty list, and a list naming only non-component-tree targets. Every message names the component path and the offending value. Validation fires wherever the emission predicate is CALLED: both component-tree targets' emit paths, and the Claude target's validate-only mode (which re-walks each bundle's components for this check alone). Reading a component is not the same as validating it — a `pr-agent`-only run opens skill manifests to harvest rule text, yet never asks whether a component is in scope, because it emits no component. The doctor rule is the authoring-time net there. | `fab9611` | `test_component_targets.py` + `test_target_scoped_emission.py::test_generation_fails_*` |
| **D3 — first consumer** | `marketplace/bundles/plan-marshall/commands/tools-fix-intellij-diagnostics.md` declares `targets: [claude]`. | `fab9611` | Asserted by generation-output listing (below) |
| **D4 — authoring surface** | New `targets-scope-invalid` plugin-doctor rule (`_analyze_target_scope.py`), registered in `_rule_registry.py` and wired into both the quality gate and analyze mode, with rows in `rule-provenance.md` and `rule-catalog.md` and a firing positive fixture in `_fixtures.py`. The field, its semantics, its validation table, and the three-condition admission test are documented in `plugin-architecture/references/frontmatter-standards.md` § "Target Scoping". | `fab9611` | `test_analyze_target_scope.py` (27 collected); the doctor runs clean over the real tree with D3's declaration in place |

### D3 generation-output listing (the plan's own "Done when" evidence)

`python3 marketplace/targets/generate.py --target all --output {dir}` exits **0**:

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

`git diff --name-only origin/main...HEAD -- '*.py'` reports **17 changed Python files**, so the gate
applies.

`./pw verify` — **SUCCESS**, all three sub-steps clean. It was re-run after every commit that changed
a Python file; the figures below are from the last such run, and every earlier run is superseded
rather than reported here:

- quality-gate: `ruff … All checks passed!`, `mypy … Success: no issues found in 415 source files`,
  `SPDX-header check passed`, plugin-doctor `total_issues: 0`
- test-compile: mypy over 775 test files, clean
- module-tests: **21055 passed, 14 skipped** — 0 failed, 0 errors

No lockfile churn: `git status --porcelain` was empty after the build, and every commit staged
deliverable paths explicitly — by name, or with `git add -A --` bounded by an explicit pathspec, which
sweeps nothing outside the named paths. No commit staged the whole worktree.

## Findings

Source key: **V1**–**V6** = pre-PR verification sub-agent, rounds 1 to 6. **S** = self-found
(mutation sweep or my own re-read).

One row per finding, and a row states its own instance count where it covers more than one site (`F14–F17`
is four; a row saying "both copies" or "both suites" is two). Round totals below count ROWS, so they
understate instances — round 5's 19 rows are 18 condition-A instances plus survivors; round 6's 11 rows
are 13 instances.

### Round 1

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

### Round 2

| # | Source | Finding | Disposition |
|---|---|---|---|
| R2-01 | V2 | Round 1's replacement `emits_to` text said `pr-agent` "reads no component at all". False — `pr_agent/target.py` opens every `*-security` skill's `SKILL.md` to harvest rule text. One falsity replaced by another in the same sentence. | **Fixed** — it reads manifests but never asks whether a component is in scope. |
| R2-02 | V2 | Same falsity, second site: the report's D2 row. | **Fixed** |
| R2-03 | V2 | "15 changed Python files" — 16 at that HEAD, because the round-1 fix commit itself touched `base.py`. A figure round 1 had just re-derived went stale in the same commit. | **Fixed** — re-derived (17) and now stated against a named commit. |
| R2-04 | V2 | "the gate saw the whole branch" was false of HEAD: the recorded `./pw verify` predated the round-1 fix commit. | **Fixed** — the claim now names the commit its figures come from, and `./pw verify` was re-run after the round-2 commit. |
| R2-05 | V2 | Round 1 corrected "one exception" to "two"; still short — variant emission and the excluded cache directories are also exceptions, and `claude/emitter.py`'s docstring already listed them, so the two disagreed. | **Fixed** — the list defers to the emitter rather than restating it. |
| R2-06 | V2 | The new sentence "That list is the **closed** set of supported top-level skill fields" made a pre-existing omission load-bearing: `implements` is a supported skill field, documented fifteen lines below the list it is missing from. | **Fixed** — `implements` added to both copies of the list. |
| R2-07 | V2 | A flow sequence spanning lines (`targets: [claude,` continued next line) was truncated to its first physical line, yielding the token `[claude`. Same class as B1; the round-1 fix reached block sequences and inline comments but not flow sequences. | **Fixed** — both parsers fold continuation lines in; pinned by three tests per suite at the time (five per suite at HEAD, after rounds 3–5 each added a fold fixture). |
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

### Round 3

| # | Source | Finding | Disposition |
|---|---|---|---|
| F1 | V3 | The "closed set of supported top-level skill fields" claim — introduced by round 1, "fixed" by round 2 adding one field — is false by **eleven** more. The verifier derived the real set by scanning every `SKILL.md`'s top-level keys: `scope` (20 skills, and MANDATORY for `manage-*` under `manage-contract.md`), `lane` (11, declared by `ext-point-lane-element`), `allowed-tools`, `order`, `mutates_source`, `default_on`, `presets`, `requires`, `head_dependent`, `configurable`, `post_run_review`. | **Fixed by withdrawal, not enumeration.** The document cannot hold a true list of fields it does not declare, so it now states what it names, points at the owning contracts, and says plainly it is not the register. |
| F2 | V3 | The Issue-4 restatement carried the same exhaustiveness. | **Fixed** — defers to the section above it. |
| F3 | V3 | A **third** copy in `doc/developer/marketplace-build.adoc`, which no earlier round had touched, despite this branch editing that file. | **Fixed** |
| F4 | V3 | `core-principles.md` lists `allowed-tools` and `model` as optional skill fields, contradicting `frontmatter-standards.md`. Pre-existing; the branch's closedness assertion is what made it a contradiction. | **Resolved by F1** — with the assertion withdrawn it reverts to a pre-existing inconsistency this plan does not own. Recorded in Residue. |
| F5 | V3 | `_join_flow_sequence`'s docstring said an unclosed sequence "is left as-is". Running it showed the fold consuming every remaining line of the block, so the diagnostic named the following FIELDS as targets. | **Fixed** — the fold is bounded, and the docstring describes what it does. (The first bound was itself wrong; see R4-3/R4-4.) |
| F6 | V3 | `emitter.py`'s docstring named two of the four `EXCLUDED_DIR_NAMES` members — and round 2 had just made that docstring the authoritative list. | **Fixed** — it defers to the constant rather than copying it. |
| F7 | V3 | The report's D2 row asserted validation fires on every path that READS components, one sentence before observing that `pr-agent` reads components and does not validate. | **Fixed** |
| F8 | V3 | Round 2 promoted the rule out of the reference-resolution pack in `rule-catalog.md` but left the row inside the matching section of `rule-provenance.md`, whose lead-in says those rules are NOT quality-gate-wired while the row says build-failing. | **Fixed** — the row has its own section. |
| F9 | V3 | That row's Emitter cell named only `cmd_quality_gate`; the rule is wired into `cmd_analyze` too. | **Fixed** |
| F10 | V3 | `principles.md` §6 carries a **third** "adding a target" checklist with no filter obligation. | **Not fixed — judged not-false by the verifier**: the `emits_to` call lands inside its item 2, and its "Nothing else" scopes to other files needing edits. Recorded in Residue. |
| F11 | V3 | The doctor's operator-facing `_DESCRIPTION_UNKNOWN` said an unknown target means the component "ships to fewer targets"; the build rejects it and ships nothing. | **Fixed**, and now pinned by an assertion on the text. |
| F12 | V3 | A findings heading counted 12 over a 13-row table. | **Fixed** — the headings name what they cover instead of counting. |

### Round 4

| # | Source | Finding | Disposition |
|---|---|---|---|
| R4-1 | V4 | A **fourth** copy of the withdrawn closed-schema claim, in the `metadata` paragraph of the very file round 3 edited — and named in round 1's own A5 row, which left it. | **Fixed.** A tree-wide grep for the claim now returns nothing. |
| R4-2 | V4 | `ext-point-verify.md` cites "the skill frontmatter schema is closed", naming as its authority the document that now says it is not the register — a contradiction round 3's edit CREATED. | **Fixed** — it states the true reason (`verification_profile` has no owning contract). |
| R4-3 | V4 | The docstrings round 3 wrote to explain its own guard were false of the code: `^[^\s#][^:]*:` matches any non-indented line containing a colon anywhere, not "a top-level key". | **Fixed, then found false again in round 5 (F1/F2) and fixed there.** Round 4's replacement claimed the pattern tests a YAML key; it is only an approximation of one, wrong in both directions. The docstrings now say so. |
| R4-4 | V4 | **A behavioural regression round 3 introduced.** That loose boundary broke two VALID declarations: a continuation line with a URL in a trailing comment, and one whose value is a quoted string containing a colon. Both are ordinary YAML; both were rejected naming `[claude` — the very defect the fold exists to prevent. | **Fixed** — the boundary is now a key test (`^[A-Za-z_][A-Za-z0-9_.-]*\s*:`), both shapes are restored. Round 5 found the second fixture pinned nothing — it quoted no colon and was green against the pre-fix parser — so it was replaced by one replayed against that parser and confirmed red (F5). |
| R4-5 | V4 | The provenance lead-in round 3 wrote asserts the reference-resolution rules are "analyze-only" — false for three of that section's eight rows, which are quality-gate-ONLY. | **Fixed** — it states only what is true of this rule. |
| R4-6 | V4 | "The skill fields **this document specifies**" — four of the fourteen appear exactly once, inside the list, and are not specified anywhere. | **Fixed** — "names" rather than "specifies", at both sites. |
| R4-7 | V4 | The adoc's "**Further** optional fields (`implements`, …, `targets`)" listed two fields that are the bullets immediately above it. | **Fixed** |
| R4-8 | V4 | The `#optional-fields-2` anchor ordinal is unguarded — `broken-relative-link` does not check pure-anchor links. | **Not fixed.** Correct today (headings at 80/149/198). Recorded in Residue; guarding it means changing a doctor rule's scope, which is out of this plan. |
| R4-9 | V4 | The doctor's finding strings had no test, so round 3's correction could regress silently. | **Fixed** — the unknown-target test now asserts the corrected clause is present and the retired one absent. |
| R4-10 | V4 | The new provenance lead-in is unguarded prose — the provenance test checks only that a row exists. | **Not fixed.** Same class as R4-8; recorded in Residue. |
| R4-11 | V4 | `test_component_targets.py` count stale (37 → 39 at that HEAD). | **Fixed** — re-derived (41) at the commit named in the Contract check. |
| R4-12 | V4 | `test_analyze_target_scope.py` count stale (24 → 25). | **Fixed** — re-derived (27). |
| R4-13 | V4 | "the figures below are from the run at `dcd7a2e`, **the last such commit**" — false once a later commit changed Python files. **Verbatim recurrence of R2-04**, whose disposition read "Fixed". | **Fixed differently**, because naming a commit inline is what keeps going stale: the figures now name no commit of their own and defer to the Contract check, which is written last. |
| R4-14 | V4 | The module-test count was stale by exactly the tests the previous fix commit added. **Third occurrence of this class** (A3, R2-03). | **Fixed** — re-derived (21042), same deferral as R4-13. |
| R4-15 | V4 | The report carried no Round 3 section at all, while its headings claimed "all fixed" — a completed-state claim the branch's own HEAD commit contradicted. | **Fixed** — this section and the Round 4 section below it. |
| R4-16 | V4 | The plan's cold-read semantics check had no recorded result. | **Fixed** — performed and recorded under "Cold read" below. |
| R4-17 | V4 | PR / Outcome fields still `pending`. | **Fixed at close** — filled in before the merge gate. |

### Round 5

| # | Source | Finding | Disposition |
|---|---|---|---|
| F1 | V5 | The `_join_flow_sequence` docstring is false in BOTH directions. `^[A-Za-z_][A-Za-z0-9_.-]*\s*:` is not a YAML key test: a digit-initial (`2fa: no`) or quoted (`"q": v`) key is a real key it does NOT match and folds in, while a bare `https://…` at column 0 is not a key and DOES break the fold. Rounds 3 and 4 both rewrote this docstring and both got it wrong. | **Fixed** — it now states the pattern is a heuristic, names both misreads, and gives the reason they are safe: in the bracketed form every misread leaves a token no registry name matches, so the value is rejected, never mis-accepted. |
| F2 | V5 | The doctor's mirror of the same docstring, same falsity. | **Fixed** |
| F3 | V5 | The `#:` constant comment says the old pattern matched "any non-indented line containing a colon anywhere" — it excluded comment lines. Overstated in both copies. | **Fixed** in both |
| F4 | V5 | A test-fixture comment claimed "Both continuation lines below … contain a colon"; the second contained none. | **Fixed** |
| F5 | V5 | **The `quoting-a-colon` fixture quotes no colon**, was green against the pre-fix parser, and pins nothing — so the second of R4-4's two restored shapes was pinned in NEITHER suite. Two instances (both suites). | **Fixed** — replaced with `"a: b"`, and replayed against a reconstruction of the pre-fix boundary to confirm it goes red (`['[claude']` before, `['claude', 'a: b']` after). The url-comment fixture was replayed too and is a genuine regression test. |
| F6 | V5 | Round 4's "the skill fields **this document names**" is false: the very next paragraph names six more (`scope`, `lane`, `order`, `default_on`, `presets`, `mutates_source`). Round 4 fixed an overstatement about four fields by making the sentence false about six others. | **Fixed** — the sentence no longer characterises the document's scope at all. |
| F7 | V5 | The same phrasing at the Issue-4 site. | **Fixed** |
| F8 | V5 | **Behavioural, previously uncharacterised:** the plain-scalar form (`targets: claude` continued on an indented line) is a multi-line YAML scalar the fold does not engage on, so both parsers read the first line only and ACCEPT a scope PyYAML would reject. Fail-OPEN. | **Survivor (B), characterised below.** No statement claims otherwise, so nothing false ships. |
| F9 | V5 | `targets:` followed by an indented scalar reports "declares an empty list" — the build outcome is right, the message names a defect the file does not have. | **Survivor (B), characterised below.** |
| F10 | V5 | The R4-3 disposition read "Fixed — the docstrings describe the real test". They did not. | **Fixed** |
| F11 | V5 | The R4-4 disposition claimed both shapes "pinned in both suites" (F5 refutes). | **Fixed** |
| F12 | V5 | "Round 3 — all fixed" over a table containing a "Not fixed" row. | **Fixed** — the headings no longer assert a state. |
| F13 | V5 | "Round 4 — all fixed" over two "Not fixed" rows and a "Fixed at close" whose header still read pending. This re-committed R4-15's own defect while closing it. | **Fixed** |
| F14–F17 | V5 | Four dispositions said "Recorded in Residue" while `## Residue` read `_(filled in at close)_`. Four instances. | **Fixed** — § Residue is written and carries all four. |
| F18 | V5 | The build-gate figures pointed at "the commit named in the Contract check below", which was unwritten — R4-13's fix replaced a stale value with a pointer to nothing. | **Fixed** — the figures stand on their own; § Contract check names the commit. |
| F19 | V5 | The plan's red-first Verification bullet had no recorded result. | **Fixed** — recorded below. |

### Red-first (the plan's § Verification requirement)

**Stated honestly: there is no red-first git history.** D1's and D2's tests landed in the same commit
as the implementation (`fab9611`), so no commit in this branch shows them failing. That is a real
shortfall against the plan's wording and is not narrated away.

What was done instead, and what it establishes:

| Evidence | Scope | Result |
|---|---|---|
| Mutation sweep, 18 mutations across both parsers, both emitters, the manifest generator and the doctor rule | Every guard the plan's D1/D2 introduced | **18/18 reddened**, no survivors, tree byte-restored and re-checked clean |
| Mutation sweep, 4 further mutations after round 2 (`_strip_comment` guard and the flow join, each parser separately) | The round-2 additions | **4/4 reddened**. Re-derived at HEAD by round 6: the `_strip_comment` pair reddens 3 tests per suite, the flow-join pair 5, because rounds 3–5 each added a fold fixture |
| Round 4's mutation of `_TOP_LEVEL_KEY_RE` → `False` | The round-3 boundary | Reddens in both suites |
| Round 5's mutation of `_DESCRIPTION_UNKNOWN` | The doctor's operator-facing text | Reddens |
| **Replay against the pre-fix parser** (round 5's method, repeated here for the corrected fixture) | The two shapes R4-4 restored | Both **red before, green after** — a true red-first demonstration, obtained after the fact |

A mutation that reddens a test proves the same property red-first proves — that the test discriminates
the defect — and it proves it for guards whose defect no longer exists to be reintroduced. It does not
substitute for the plan's literal instruction, which is why the shortfall is stated first.

### Round 6

Rounds 6–10 were granted by the operator after the default budget was spent (§ Budget escalation).

| # | Source | Finding | Disposition |
|---|---|---|---|
| R6-01 | V6 | Round 5's own fix introduced a new falsity: "**This list** is: `name`, `description`, …" has no antecedent (the only preceding list is the *prohibited* fields, so the first reading is backwards) and, taken against its heading, asserts that `name`/`description`/`user-invocable`/`mode` are OPTIONAL — refuted twice in the same file. Fifth consecutive round in which prose written to close a finding was itself false. | **Fixed** — the sentence now names what it covers ("the required ones above and the optional ones below"). |
| R6-02 | V6 | The F8 survivor bound claimed the 4761-case differential "proves the family is the **only** one producing accept/reject divergence" — refuted by B3, two rows below in the same table, and by the quoted-key defect below. | **Fixed** — the bound now states what the differentials actually establish: that the *fold* introduces no divergence in the bracketed form. |
| R6-03a | V6 | **Behavioural, fail-OPEN, undisclosed.** A quoted top-level key — `"targets": [claude]` — was not recognised as a declaration, so the component shipped to **every** target with nothing reported. Valid YAML; PyYAML reads it as a real `targets` key. Five rounds missed it. | **Fixed, not merely disclosed** — the key is unquoted before comparison, and both quoted spellings are pinned. |
| R6-03b | V6 | The same miss in the doctor's mirror, so the authoring-time net missed it too. | **Fixed** |
| R6-04a | V6 | Round 5's answer to "the docstring is false" was a longer, more precise docstring with **no test behind any of it**. Proven by mutation: widening the boundary regex to match digit-initial keys, and adding `(?!//)` so a bare URL no longer ends the fold, each falsify a documented clause in code and leave the suite at **41 passed, 0 failed**. | **Fixed** — both misreads and the safety property (every misread is rejected) are now pinned. |
| R6-04b | V6 | Same, in the doctor suite (27 passed, 0 failed under both mutations). | **Fixed** |
| R6-05 | V6 | The Red-first table said the flow-join mutation reddens "3 tests each"; it reddens 5 per suite at HEAD, because rounds 3–5 each added a fold fixture. | **Fixed** — re-derived, and the figure now says which pair reddens which count. |
| R6-06 | V6 | The same stale count at the R2-07 disposition. | **Fixed** |
| R6-07 | V6 | The fold docstring's "no accept/reject divergence from PyYAML **anywhere in this bracketed form**" is unbounded as written, and a duplicate top-level key is a well-formed, entirely bracketed counter-example. | **Fixed** — scoped to divergence *arising from this fold*, with the duplicate-key exception named. |
| R6-08 | V6 | The Findings lead-in states "One row per instance"; the round-5 table breaks it three times, so the round totals count rows rather than instances. | **Fixed** — the convention now matches what the tables do, and says so. |
| R6-09 | V6 | F8's bound leans on "the standards section documents inline and block form only" (true) while `_split_inline`'s docstring and the `inline-bare` fixtures advertise the bare spelling the bound relies on nobody using. | **Fixed** — the bound names the tension rather than resting on the narrower reading. |
| R6-10 | V6 | The doctor's cross-reference imported a guarantee its own module does not carry: "why **every** misread is rejected" is true of the build, but the analyzer returns `[]` with no `marketplace/targets/` tree, so a misread is silently ignored there. | **Fixed** |
| R6-11 | V6 | The Residue's "(156 skills)" measures on-disk `SKILL.md` files while the sentence it corrects says *registered* — a `plugin.json` count. | **Fixed** — the row states the drift without substituting a figure from a different population. |

**Round 6's evidence, and why it is the strongest on this branch.** It did not merely re-read: it built
its own corpora and one of its results proves a GAP rather than confirming a claim.

- **Two mutations that positively demonstrate missing coverage** — each falsifies a documented clause
  in code while both suites stay fully green. No amount of reading establishes an absence of coverage;
  this does. It is what produced R6-04.
- **Directed falsification of the safety claim**: 20,580 bracketed shapes constructed specifically to
  smuggle a valid scope through a misread → **0 accepts**. The claim survived an attack built to break
  it.
- **Two independent PyYAML differentials** (6,768 and 16,806 well-formed shapes) → 0 accept/reject and
  0 scope divergence in the bracketed form, and a **24,046-shape parser-vs-parser differential** → 0
  disagreements, generalising round 5's 4761/0 at five times the corpus.
- **A family-level oracle comparison across 21 declaration families** — which is what surfaced R6-02
  and the R6-03 fail-open, both invisible to any amount of reading.

### Cold read (the plan's § Verification requirement)

A sub-agent that had seen no implementation, no test and no git history read **only** the
`## Target Scoping` section and answered the plan's two questions:

- *What does an absent `targets:` field mean?* → **"the component ships to every build target"**
- *What happens on an unknown value?* → **"fails the build, with an error naming both the component
  and the unknown value"**

Both are the required answers, and the reader reported guessing at neither. The plan's check
therefore **passes**.

It surfaced two wording gaps, both fixed rather than waved through:

1. "The plugin-doctor rule reports **the first two**" forced the reader to count table rows to learn
   which defects the linter catches. The cases are now named, not counted.
2. The section refused to enumerate valid target names (correctly — a prose list rots) but gave the
   reader no other route, so the only reason they could write `claude` was that the worked example
   happened to use it. *"If the question had been 'ship only to OpenCode', the section would have
   left me unable to answer."* The section now names the command that prints the live set. Writing
   that sentence introduced a falsity of its own — the command also prints `all`, which is not a
   target name — caught by running it before the claim shipped.

### Stop record

**The loop has not ended. The first budget was spent and the operator extended it.**

The budget was the contract's default of **five rounds**; the plan set none. No round returned
"nothing remains" — round 5 answered the stop question **"Yes, condition A is violated at 13 sites"**,
and those 13 were fixed, as condition A requires regardless of budget. What a spent budget ends is the
*verifying*, never the *fixing*.

### Budget escalation

An operator was reachable in this session, so the contract's boundary ask was an obligation rather
than an option, and it was put to them with: the rounds run and their counts, the non-convergence
evidence below, every survivor with its bound, and the four options (stop and open the PR; another
five rounds; stop and hand the branch over; or narrow the loop to one named surface).

| | |
|---|---|
| **Asked at** | End of round 5, after all 13 of its condition-A findings were fixed and pushed |
| **Answer** | **"Another five rounds"** — granted on identical terms |
| **Terms** | Rounds 6–10; the same boundary question when they run out; the same autonomous fallback if the operator has become unreachable by then |

This record exists because a conversation event is not a committed artifact — the report is its only
durable trace.

**Rounds and what they found:** 12, 17, 12, 17, 19. Two further round-5 dispatches died to server-side
API errors (one mid-response, one a 529) before doing any work; neither is counted as a round, because
a failed dispatch produced no verification and counting it would be the "silence read as a pass"
defect this loop exists to catch.

**Convergence: no.** Each round was asked for the shipped-change vs report split, and the answer never
narrowed — round 3: 9/12 in the shipped change; round 4: 10/17; round 5: 9/19. Round 5's verdict:
*"merely fewer, and barely … the share has fallen only because the report grew a Round 3 and a Round 4
section this round — the denominator moved, not the numerator."* Two of its findings sat in the same
docstring pair rounds 3 and 4 had each rewritten and each got wrong.

**Evidence stronger than another read** — all obtained in round 5, none of which the branch previously
carried:

- an **exhaustive combinatorial differential** over 4761 frontmatter shapes between the two parsers:
  **0 disagreements**. The "mirrors the generator's parser so the two agree" claim, flagged in round 2
  as having nothing behind it, is now established by enumeration rather than by three examples;
- a **three-way oracle comparison against PyYAML** over the same 4761 shapes, classified by
  accept/reject verdict: 42 divergences, **all confined to the plain-scalar family and zero in the
  bracketed flow form** the fold governs. That is what bounds F8/F9 rather than leaving them open;
- **mutation kills** (18 + 4 + 2) and a **pre-fix parser replay** that exposed F5 — evidence no amount
  of reading would have produced.

This evidence covers the parsers. It does not cover the report or the bundle prose, where the verdict
still rests on reading — which is precisely where round 5 found most of what it found.

**Survivors left open, each characterised:**

| Survivor | Kind | (a) proof / (b) bound |
|---|---|---|
| **F8** — plain-scalar `targets: claude` continued on an indented line is read as its first line only, accepting a scope PyYAML would reject | Behavioural, fail-**open** | **(b)** Reach: one component, scoped to a set YAML never declared. It cannot reach a component with no `targets:` field. It is **not** the only family diverging from PyYAML — B3 below is another, and a quoted top-level key was a third until round 6 fixed it; what the differentials establish is narrower, that the *fold* introduces no divergence in the bracketed form. No component in the tree uses the plain-scalar multi-line form. The standards section documents inline and block form only — but note `_split_inline`'s docstring and the `inline-bare` test fixtures do advertise the single-line bare spelling, so an author could reach the multi-line form by extending a spelling the code invites. |
| **F9** — `targets:` plus an indented scalar reports "declares an empty list" | Diagnostic text | **(a)** The build outcome is unchanged (rejection); only the message misnames the defect. It cannot change what the deliverable does. |
| **B3** — a duplicate top-level `targets:` resolves to the first declaration, silently | Behavioural | **(b)** Verified again at HEAD: cannot narrow below the first declaration and cannot widen past "every target"; the result is then fully validated. |
| **B5** — OpenCode's `_prune_stale_outputs` runs only on a full regeneration, so a `--bundles` subset emit can leave a scoped-out component behind | Behavioural, pre-existing | **(b)** Bounded to scoped emits. The normal build and both drift checks run full regenerations; the constraint is documented at the function with its reason. Unchanged by this plan — reachable through a new cause, not newly created. |
| **B6** — `check_bundle`'s orphan sweep covers `agents/` and `commands/`, not skill directories | Behavioural, pre-existing | **(b)** Bounded to validate-only mode over a stale tree. Any emit wipes each bundle's destination first, and `content_drift`'s `orphan_in_target` catches a stale `.md` because it regenerates through `ClaudeTarget`. A deleted skill was equally invisible before this plan. |

Every one was re-put to the verifier in the stopping round and re-characterised there, not carried
forward unread.

**Residue to assume remains:** see § Residue. In short — the parsers are well evidenced; the prose
about them is where five rounds kept finding defects, and the last round still did.

## Reviewer participation

_(filled in after the PR is opened)_

## Cost

_(filled in at close)_

## Contract check (Step 9)

_(filled in at close)_

## What have we learned (Step 9)

_(filled in at close)_

## Residue

Four dispositions above defer here; this is that record.

**Open, and deliberately not fixed by this plan:**

| Item | Why it is left | Where it should go |
|---|---|---|
| `core-principles.md` lines 48-52 list `allowed-tools` and `model` as optional skill fields, contradicting `frontmatter-standards.md`'s "Skills do not use `model`, `color`, or `tools`/`allowed-tools`" — and two real skills (`automatic-review`, `plan-retrospective`) do declare `allowed-tools` (round 3, F4) | Pre-existing. It became visible only because this branch briefly asserted the field list was closed; that assertion is withdrawn, so the inconsistency reverts to what it was on `main`. Resolving it means deciding which document is right about a field this plan does not touch | A frontmatter-documentation reconciliation, not a target-scoping plan |
| `principles.md` §6 carries a third "adding a target" checklist ("adding target X is **exactly**: 1…3 … **Nothing else**") with no filter obligation (round 3, F10) | The verifier judged it **not false**: the `emits_to` call lands inside its item 2, and "Nothing else" scopes to *other files needing edits*, which stays true | The epic's own reference set, if a later plan widens that checklist |
| The `#optional-fields-2` anchor ordinal in `frontmatter-standards.md` is unguarded — `broken-relative-link` explicitly skips pure-anchor links, so inserting an earlier `### Optional Fields` heading would silently retarget it (round 4, R4-8) | Correct today (headings at 80/149/198). Guarding it means widening a plugin-doctor rule's scope, which is outside this plan | A plugin-doctor rule-scope change |
| The `rule-provenance.md` § "Target-scope rule" lead-in is unguarded prose — the provenance test checks only that a *row* exists (round 4, R4-10) | Same class as the anchor: the guard would be a new doctor capability, not a fix to this change | With R4-8 |
| `rule-provenance.md` line 247's "**Five rules** … NOT in `quality-gate`" stands over an 8-row table whose last three rows are `cmd_quality_gate` (round 5) | **Pre-existing and not branch-introduced** — round 5 confirmed the section is byte-identical to `origin/main` after this plan's row was moved out of it | A provenance-table audit |
| `CLAUDE.md`'s "157 registered components (153 skills…)" has drifted | Pre-existing, already tracked as deferred in another plan's report. The drift is real; this report deliberately states no replacement figure, because `CLAUDE.md` says *registered* — a `plugin.json` count — and the obvious substitute (156 on-disk `SKILL.md` files) measures a different population | Already owned elsewhere |

**Behavioural survivors** — see § Findings → "Stop record" for each one's bound.

**What a reader should assume still remains.** Round 5's own answer, quoted because it is the most
useful sentence in this report: *"The code is in much better shape than the prose about the code …
the residue is documentary, and it is concentrated in exactly the sentences written to close a prior
round."* Five rounds rewrote `_join_flow_sequence`'s docstring and the first four were false of their
own regex. Treat any self-descriptive comment in the two parsers, and any "X is pinned in both
suites" claim, as needing its own check rather than trusting the sentence.
