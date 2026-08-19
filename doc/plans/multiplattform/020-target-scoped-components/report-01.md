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
| **D1 — filter mechanism** | New `marketplace/targets/component_targets.py` parses the `targets:` declaration and answers `emits_to(path, target_name)`. Both component-tree-emitting targets consult it: the Claude verbatim emitter (`excluded_emission_roots` + `is_under_any`, skipping a scoped-out file or a whole scoped-out skill directory) and its manifest generator (`plugin_json_gen` drops the same entries), and the OpenCode emitter (per-skill / per-agent / per-command skip). The governed set is derived from `TARGET_REGISTRY` filtered by each target's `emits_bundle_tree` capability — never enumerated. Absent field still means every target. | `fab9611` | `test_component_targets.py`, `test_target_scoped_emission.py` — **73 and 14 collected at HEAD**. Counts are stated at HEAD only, never against the implementing commit: `test_component_targets.py` has grown in most rounds and had 24 cases at `fab9611`, so attributing its current count there would name a number that commit never had. (`test_target_scoped_emission.py` has been 14 since `a9c90ef`; the HEAD-only rule is uniform, not a claim that every file moved.) |
| **D2 — fail-closed validation** | `_validate` rejects an unknown target name, an empty list, and a list naming only non-component-tree targets. Every message names the component path and the offending value. Validation fires wherever the emission predicate is CALLED: both component-tree targets' emit paths, and the Claude target's validate-only mode (which re-walks each bundle's components for this check alone). Reading a component is not the same as validating it — a `pr-agent`-only run opens skill manifests to harvest rule text, yet never asks whether a component is in scope, because it emits no component. The doctor rule is the authoring-time net there. | `fab9611` | `test_component_targets.py` + `test_target_scoped_emission.py::test_generation_fails_*` |
| **D3 — first consumer** | `marketplace/bundles/plan-marshall/commands/tools-fix-intellij-diagnostics.md` declares `targets: [claude]`. | `fab9611` | Asserted by generation-output listing (below) |
| **D4 — authoring surface** | New `targets-scope-invalid` plugin-doctor rule (`_analyze_target_scope.py`), registered in `_rule_registry.py` and wired into both the quality gate and analyze mode, with rows in `rule-provenance.md` and `rule-catalog.md` and a firing positive fixture in `_fixtures.py`. The field, its semantics, its validation table, and the three-condition admission test are documented in `plugin-architecture/references/frontmatter-standards.md` § "Target Scoping". | `fab9611` | `test_analyze_target_scope.py` — **50 collected at HEAD** (same HEAD-only rule); the doctor runs clean over the real tree with D3's declaration in place |

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
- module-tests: **21088 passed, 14 skipped** — 0 failed, 0 errors

No lockfile churn: `git status --porcelain` was empty after the build, and every commit staged
deliverable paths explicitly — by name, or with `git add -A --` bounded by an explicit pathspec, which
sweeps nothing outside the named paths. No commit staged the whole worktree.

## Findings

Source key: **V1**–**V8** = pre-PR verification sub-agent, rounds 1 to 8. **S** = self-found
(mutation sweep or my own re-read).

One row per finding. A row states its own instance count where it spans more than one site — `F14–F17`
covers four, and a row saying "both copies" or "both suites" covers two.

**Every per-round number in this report is a ROW COUNT of the round's table below.** Rows, labels and
instances all differ — a row may cover several sites, and a round's verifier may label its findings
differently from how this report tabulates them. Earlier drafts conflated the three and were wrong
every time, so exactly one unit is used here: rows, countable by looking. They are 13, 17, 12, 17, 16,
13, 12, 13, 16 for rounds 1 to 9.

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
| R2-07 | V2 | A flow sequence spanning lines (`targets: [claude,` continued next line) was truncated to its first physical line, yielding the token `[claude`. Same class as B1; the round-1 fix reached block sequences and inline comments but not flow sequences. | **Fixed** — both parsers fold continuation lines in; pinned by three tests per suite at the time. At HEAD the two suites are no longer symmetric — rounds 3–9 added fold fixtures unevenly — so no single figure covers both; count them from the suites if you need one. |
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
| F8 | V5 | **Behavioural:** the plain-scalar form (`targets: claude,` continued on an indented line) is one multi-line YAML value the fold did not engage on, so both parsers read the first line only. **Rounds 5–7 labelled this fail-OPEN; round 8 executed it and the label was backwards** — the same value written on one line yields `{claude, opencode}`, so the multi-line form silently DROPPED a declared target. That is silent narrowing, the one direction this mechanism must never fail in. | **Fixed in round 8, INCOMPLETELY — closed in round 9.** Round 8's guard exempted continuation lines beginning with `-`, meaning to protect the block form; the guard only runs when the key has a value and a block form's key has none, so the exemption protected nothing and left the hole open for `targets: claude,` / `  - opencode`. Nothing tested it — deleting the exemption reddened no test. Round 9 removed it and pinned both shapes. |
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
| Mutation sweep, 4 further mutations after round 2 (`_strip_comment` guard and the flow join, each parser separately) | The round-2 additions | **4/4 reddened**. Kill counts grow as fixtures are added, so they are re-measured after each round's own additions rather than before them — round 6 measured before its and mislabelled the result "at HEAD". At the commit this report is finalised on: `_strip_comment` **3 per suite**, flow-join **7 per suite** |
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

### Round 7

| # | Source | Finding | Disposition |
|---|---|---|---|
| 7-01 | V7 | Round 6's replacement sentence claims the fourteen fields are "**documented in this file**"; four of them (`argument-hint`, `compatibility`, `disable-model-invocation`, `license`) occur exactly once in the whole file — in that list. **Sixth consecutive round of false fix-prose on this sentence.** Four instances. | **Fixed** — the sentence now claims only that the fields are *named* here, and says outright that some are named and nothing more. |
| 7-02 | V7 | The same sentence partitions by position ("required above, optional below") and so still calls `mode` optional; `mode` is documented below and is required, enforced by the `skill-missing-mode` rule. Fixed for three required fields, left for the fourth. | **Fixed** — the partition is gone. |
| 7-03 | V7 | The R6-10 fix overshot: "with no `marketplace/targets/` tree … this analyzer **reports nothing at all**" is refuted by its own cited module docstring, by `_scan_component` (the empty-declaration branch returns a Finding first), by `rule-catalog.md`, and by a passing test. | **Fixed** — scoped to the unknown-name check, with the empty-declaration check named as unaffected. |
| 7-04 | V7 | **Behavioural regression introduced by round 6, in the mirror direction.** `key.strip().strip('"').strip("'")` strips a character SET, so `targets": [claude]`, `targets': [claude]` and `"'targets'": [claude]` — all different keys to YAML — were read as declarations. A component that declared **no** scope was silently narrowed to someone else's list: silent exclusion, which the module docstring calls prohibited. Two instances (both parsers). | **Fixed** — `_unquote_key` removes only a MATCHED pair. All eighteen probed spellings now agree with PyYAML, and the boundary is pinned from **both** sides in both suites — six mismatched spellings in the generator suite, two in the doctor's. |
| 7-05 | V7 | The R6-05 figure went stale in the commit that stated it: round 6 measured the flow-join kill count *before* adding its own fold fixtures and labelled the result "re-derived at HEAD". 5 at `b0d454e`, 7 at `913965b`. | **Fixed** — re-measured after this round's additions (3 and 7 per suite), and the figure now states the rule that keeps it honest: measure after the round's own fixtures, not before. |
| 7-06 | V7 | The same wrong figure at the R2-07 disposition. | **Fixed** |
| 7-07 | V7 | Three collection counts were the values from *before* round 6's test additions, and were attributed to `fab9611`, where the real values are 24/11/16. All three were wrong. | **Fixed** — stated at HEAD only (55 / 14 / 36), with the reason a commit attribution cannot work for a number that grows every round. |
| 7-08 | V7 | The R6-08 counting convention was wrong on every figure it stated — it called label counts row counts, and its two instance totals contradicted each other and the Stop record. | **Fixed, then fixed again in round 8** — the unit it named was still wrong. The report now counts ROWS, which are countable by looking, and states no instance total anywhere. The series is maintained in the § Findings lead-in and nowhere else, so it cannot fall out of step with itself. |
| 7-09 | V7 | The Stop record still described a five-round run: round counts, the convergence series and the evidence paragraph all omitted round 6. Three instances. | **Fixed** |
| 7-10 | V7 | The Residue said "the first four [docstring rewrites] were false of their own regex"; round 5's was accurate-but-unguarded, which is round 6's own finding. | **Fixed** |
| 7-11 | V7 | The doctor's quoted-key pin exercised the parser only, while its docstring claimed "the authoring-time net missed it too" — an entry point no test reached. | **Fixed** — the rule's own entry point is now exercised, from both sides. |
| 7-12 | V7 | Round 6's corpus figures (20,580 smuggle attempts; 6,768 and 16,806 PyYAML differentials; 24,046 parser-vs-parser; "21 declaration families") are **not re-derivable** — no corpus or script is persisted on the branch. | **Recorded, not fixed.** Round 7 ran its own 288-shape bracketed differential and found 0 cases of the failure mode the claim denies, consistent at ~1% of the corpus. The figures are attributed to the round that produced them and should be read as that verifier's measurement, not as a reproducible branch artifact. |

**Round 7's evidence.** Four mutations re-run at HEAD in both suites; both round-6 mutations replayed
at `b0d454e` in a throwaway worktree, independently confirming round 6's coverage-gap claim rather
than taking it on trust; the fold-disable kill count measured at two commits; collection counts
measured at three; an eighteen-spelling adversarial key probe across generator, doctor and PyYAML —
which is what produced 7-04 — and a 288-shape bracketed PyYAML differential.

### Round 8

| # | Source | Finding | Disposition |
|---|---|---|---|
| R8-01 | V8 | The field-list sentence, third rewrite, still inexact: "some have a field-specification block **below** and some are **only named here**" leaves three fields (`name`, `description`, `user-invocable`) in neither class — their blocks are *above* the list. | **Fixed** — all three classes are named explicitly. |
| R8-02 | V8 | The doctor's mismatched-quote test docstring says a mismatched quote "is a different key"; for `"targets` it is not a key at all (PyYAML raises). Its generator twin, written in the same commit, hedges correctly — the fix landed at one of the two sites. | **Fixed** |
| R8-03 | V8 | `_join_flow_sequence`'s docstring appeals to "tens of thousands of bracketed shapes" — the same unpersisted-corpus claim round 7 ruled must be attributed rather than asserted, applied to the report and not to the shipped docstring making it. | **Fixed** — the corpus appeal is replaced by the structural reason, which a reader can check against the code: a fold that overruns absorbs a colon-bearing fragment, and one that stops early keeps its opening bracket; both land outside the registry. |
| R8-04 | V8 | The counting convention round 7 introduced was itself wrong: the totals do not count labels either (round 7 has 12 labels, stated as 11; round 1 has 13, stated as 12). | **Fixed** — every per-round number is now a ROW count of the table below it, mechanically re-derived: 13, 17, 12, 17, 16, 13, 12. |
| R8-05 | V8 | "No instance total is stated here" is contradicted twice in the same document by "13 sites" / "all 13". Two instances. | **Fixed** — both restated without a total. |
| R8-06 | V8 | The source key read "V1–V6 … rounds 1 to 6" in the commit that added twelve V7 rows. | **Fixed** |
| R8-07 | V8 | "round 7 independently reproduced that result at two commits" — the replay was at one commit; "two commits" belongs to a different measurement in the same list. | **Fixed** |
| R8-08 | V8 | "**Six rounds** rewrote the docstring" over an enumeration naming four, and round 7 raised the count without naming its own rewrite. | **Fixed** — the sentence names each rewrite instead of counting them. |
| R8-09 | V8 | Row 7-07 says "two of the three were wrong" while its own figures show all three differ. | **Fixed** |
| R8-10 | V8 | Row 7-04 attaches a generator-only count ("six mismatched spellings") to a both-suites claim; the doctor pins two. | **Fixed** |
| R8-11 | V8 | The new HEAD-only rule generalises "they have grown every round" — false for `test_target_scoped_emission.py`, which the same row governs and which has been 14 since `a9c90ef`. | **Fixed** — the rule is stated as uniform policy rather than as a claim about every file. |
| R8-12 | V8 | Round 7's own evidence paragraph introduces unreproducible figures (an 18-spelling probe, a 288-shape differential) with no caveat, in the commit whose 7-12 disposition requires exactly that caveat. | **Fixed** — see the evidence note below, which now applies the rule to every round including this one. |
| R8-13 | V8 | **The F8 survivor was mislabelled in direction at two sites.** Called "fail-OPEN / accepts a scope PyYAML would reject" through rounds 5–7; executing it shows the opposite — the multi-line plain scalar silently DROPS a declared target. Its bound was re-checked every round and held; its kind was never checked. | **Fixed in the code, not the label** — see below. |

**R8-13 is why round 8 changed behaviour.** Once the direction was right, F8 stopped qualifying as a
survivor: condition B admits a bounded behavioural finding, but this one was silent *narrowing*, which
`component_targets`'s own contract calls prohibited. So a plain scalar continued across lines is now
**rejected** with a message naming the supported spellings, in the build and in the doctor rule alike,
and the rejection is pinned together with five supported forms it must not disturb — because the
obvious over-correction here is a guard that also refuses the block form.

**Evidence.** Round 8 ran an **exhaustive** differential over the key-spelling space — all 441 shapes
of `prefix + whitespace + targets + whitespace + suffix` for every quote string of length 0–2 —
three-way against PyYAML: 0 narrowing disagreements, 0 missed declarations, 0 generator/doctor splits.
That closes the quoted-key class by enumeration rather than by example, and unlike the corpus figures
of rounds 6 and 7 it is reproducible from a short script. It also ran five directional mutations across
both parsers (both `_unquote_key` reverts, a rule-entry-point isolation, and round 6's two boundary
mutations) and a full `--target all` regeneration reproducing the D3 listing end-to-end.

⚠️ **On corpus figures generally:** the sizes quoted for rounds 6 and 7 (20,580 / 6,768 / 16,806 /
24,046 / 18 spellings / 288 shapes) are each one verifier's measurement, not a branch artifact — no
script or corpus is persisted. Round 8's 441-shape sweep is exhaustive over a defined space and so is
re-derivable from its description; the others are not. Read them as testimony.

### Round 9 — BLOCKED, and what was checked without it

**The round did not run.** Two dispatches failed: the first to a mid-response API error, the second to
a **session limit** (resets 23:40 UTC). Neither produced verification. A failed dispatch is not a
round, and is not counted as one — counting it would be the "silence read as a pass" defect this loop
exists to prevent. **Rounds 9 and 10 of the operator's extension are unspent.**

What was done instead is narrower and is labelled as such: the **executable** probes round 9 was
assigned were run directly. These are mechanical — each returns a verdict that could have come back
differently — so they are evidence, not self-assessment. What they cannot replace is an independent
reader, which is the part of the round that is missing.

| Probe | Result |
|---|---|
| **Over-rejection matrix** — a hand-built shape set through the new continued-scalar guard, against PyYAML | ⚠️ **This verdict was WRONG, and round 9 refuted it.** It reported no genuine over-rejection; round 9's own matrix found four — `>-`, `\|-` and quoted multi-line values, which PyYAML reads as sound single values naming a real target. The matrix was hand-built by the author of the guard and is not persisted, so it is testimony of the weakest kind: a sample chosen by the party with an interest in it passing. Round 9 fixed the diagnosis; this row is kept as the record of a self-check that missed. |
| **Falsification of the fold's safety claim** — 81 two-line continuations, both failure directions | **0 accepted without a closing bracket.** No misread smuggles a scope past `_validate`. |
| **Falsification of the fold docstring's stated REASON** | **Falsified, and corrected.** See below. |

**The docstring's reason was wrong again — the sixth time this sentence has been.** Round 8 replaced
an unpersisted corpus appeal with a structural argument: an overrun "absorbs a fragment containing a
colon". Enumeration refutes it — `targets: [claude,` continued by two plain lines yields the token
`opencode opencode`, which contains no colon and no bracket. The safety property still holds, but for
a different reason than the one written down: the fold joins with a **space**, and no registered
target name contains a space. That is now what the docstring says, and the 81-shape search that found
it is pinned as a test, so the property is checked rather than asserted.

That correction is the whole point of the exercise: **the code was right and the explanation was
wrong**, which is this branch's most persistent defect class, and it took execution rather than
reading to catch — the same method that produced rounds 6, 7 and 8's headline findings.

### Round 9

The round that ran after the blocked dispatch. **It is the most consequential of the nine**, because
it refuted a fix, a self-check and a convergence trend all at once.

| # | Source | Finding | Disposition |
|---|---|---|---|
| R9-01 | V9 | **F8 was not fixed.** Round 8's guard exempted continuation lines starting with `-`, meaning to protect the block form — but the guard runs only when the key HAS a value, and a block form's key has none, so the exemption protected nothing and left the silent-narrowing hole open for `targets: claude,` / `  - opencode`. Deleting the exemption reddened **no test**. Three report claims said it was fixed. | **Fixed** — exemption removed, both shapes pinned in both suites. |
| R9-02 | V9 | Round 8's behaviour change landed in two code sites and **none of the ten registers documenting them** — two module docstrings, an explicit "two defects" count, three `rule-catalog.md` clauses, two `rule-provenance.md` clauses, the standards validation table, and a test module docstring. | **Fixed at all ten**, and `component_targets`' own docstring now names the registers a new rejection must be added to, so the next one is not a hunt. |
| R9-03 | V9 | The docstring calls the space join "the load-bearing half"; replacing `' '.join` with `''.join` left the suite **fully green**, including the very test round 9's predecessor added to check the property. | **Fixed** — pinned by a case where only the space rejects (`targets: [open,` / `code]`). |
| R9-04 | V9 | "No registered target name contains a space" is the premise that argument rests on, asserted in one docstring and enforced nowhere: `register_target('my target', T)` succeeded. | **Fixed** — `register_target` now rejects a name with whitespace, so the premise is true by construction. |
| R9-05 | V9 | **The guard over-rejects, and my own probe said it did not.** `targets: >-` / `  claude` and `targets: \|-` / `  claude` are valid YAML whose value is `claude`, a registered target; they were refused under a message calling them plain scalars. | **Fixed** — block scalars are detected and rejected under their own name, in both parsers. The probe row above is corrected and kept as the record of a self-check that missed. |
| R9-06 | V9 | Two shipped messages say the build "reads only its first line" — true before the guard, false after. | **Fixed** |
| R9-07 | V9 | Two collection counts stale again — the fourth recurrence of this class. | **Fixed** — re-derived at HEAD. |
| R9-08 | V9 | "seven per suite at HEAD" states no unit, and under any unit the two suites are no longer symmetric. | **Fixed** — the figure is withdrawn rather than restated. |
| R9-09 | V9 | The docstring-rewrite enumeration stops at round 8 and presents its reason as current, in a commit that had just falsified it. | **Fixed** |
| R9-10 | V9 | The row-count restatement lists seven numbers for a convention covering eight rounds. | **Fixed** — the series lives in one place now. |
| R9-11 | V9 | The Round-9 probe row cites "13 shapes" while characterising nine, unpersisted — the standard the report's own ⚠️ note imposes on other rounds. | **Fixed** — the row no longer cites a corpus size, and says plainly what kind of evidence it was. |
| R9-12 | V9 | The block-form "pin" is vacuous: `_has_continuation → True` leaves both block-form checks green, because the guard is structurally unreachable for that form. The commit message claimed the named over-correction was pinned against. | **Fixed** — the claim is withdrawn; the tests remain as coverage of the surrounding behaviour, which is what they actually are. |
| R9-13 | V9 | The sentinel's identity contract ("cannot collide") had no check: `is` → `==` left the suite green. | **Fixed** — pinned by a component declaring the sentinel's literal text, which must be reported as an unknown NAME. |
| R9-14 | V9 | **Survivor B3's bound was measured against the parser's own answer** — the same vacuous-guard shape round 8 found in F8, one survivor over — and its second half was vacuous. | **Fixed** — restated against the YAML-authoritative last declaration, with both directions named. |
| R9-15 | V9 | Rounds 3 and 5 both use labels `F1`–`F12`, so `F8`/`F9` each name two findings and the survivors table refers to them unqualified. | **Fixed** — survivor references now say which round's F8/F9 they mean. |
| R9-16 | V9 | The field-list sentence, fourth rewrite, classified 13 of 14 fields — the unclassified one being `targets`, this plan's own addition, whose block is in a sibling section. | **Fixed** — all fourteen are placed. |

**Round 9's verdict on convergence, which supersedes rounds 7 and 8's.** Shipped-change findings by
round: 9, 10, 9, 7, 5, 3, **9**. The fall through rounds 4–8 was an artefact of what those rounds were
looking at — rounds 7 and 8 examined the report, and round 8 was the first commit since `fab9611` to
change what the module *does*. **A behaviour change resets the shipped-defect rate**; the loop had not
converged, it had been re-seeded. Any reading of the earlier trend as evidence the mechanism was
settling was wrong, and this report stated that reading twice.

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
"nothing remains" — round 5 answered the stop question **"Yes, condition A is violated"**,
and those 13 were fixed, as condition A requires regardless of budget. What a spent budget ends is the
*verifying*, never the *fixing*.

### Budget escalation

An operator was reachable in this session, so the contract's boundary ask was an obligation rather
than an option, and it was put to them with: the rounds run and their counts, the non-convergence
evidence below, every survivor with its bound, and the four options (stop and open the PR; another
five rounds; stop and hand the branch over; or narrow the loop to one named surface).

| | |
|---|---|
| **Asked at** | End of round 5, after every one of its condition-A findings was fixed and pushed |
| **Answer** | **"Another five rounds"** — granted on identical terms |
| **Terms** | Rounds 6–10; the same boundary question when they run out; the same autonomous fallback if the operator has become unreachable by then |

This record exists because a conversation event is not a committed artifact — the report is its only
durable trace.

**Rounds and what they found:** 13, 17, 12, 17, 16, 13, 12, 13, 16 — rows, per the counting note in
§ Findings. Two further round-5 dispatches died to server-side API errors (one mid-response, one a
529) before doing any work; neither is counted as a round, because a failed dispatch produced no
verification and counting it would be the "silence read as a pass" defect this loop exists to catch.

**Convergence: partial, and only on volume.** Each round was asked for the shipped-change vs report
split: round 3 9/12, round 4 10/17, round 5 9/19, round 6 7/13, round 7 5/11, round 8 3/13, round 9 **9/16**
(each as its verifier reported it, in that verifier's own units). Rounds 7 and 8 read the fall as narrowing; **round 9 refuted that**
and this report's earlier statement of it. Its finding: the fall was an artefact of what those rounds
examined — the report, not the code — and round 8 was the first commit since `fab9611` to change what
the module does. Round 9's count returned to round-1 levels. *A behaviour change re-seeds the
shipped-defect rate*, and four of the nine rounds have now found a behavioural defect introduced by a
previous round's fix.

**Evidence stronger than another read.** Rounds 5, 6 and 7 each produced some; the branch carried none
before round 5. Round 6's is the strongest in kind, because it proved a GAP rather than confirming a
claim — two mutations that each falsify a documented clause in code while both suites stay green — and
round 7 independently reproduced that result by replaying both mutations at the preceding commit. Round 5's contribution:

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
| **F8** (round 5's) — a plain scalar continued across lines was read as its first line only | ~~Survivor~~ **fixed in round 8, incompletely; closed in round 9** | Carried as a survivor through rounds 5–7 under a **backwards direction label** ("fail-open"). Round 8 executed it: the multi-line form silently dropped a declared target, i.e. narrowed. Once the direction was right the survivor argument collapsed — silent narrowing is what this mechanism exists to prevent — so it was fixed rather than re-characterised. The lesson worth keeping: a survivor's *bound* was checked every round and held; its *kind* was not, and that is what was wrong. |
| **F9** (round 5's) — `targets:` plus an indented scalar reports "declares an empty list" | Diagnostic text | **(a)** The build outcome is unchanged (rejection); only the message misnames the defect. It cannot change what the deliverable does. |
| **B3** — a duplicate top-level `targets:` resolves to the FIRST declaration; YAML takes the LAST | Behavioural — **both directions**: against the YAML-authoritative last declaration it both adds a target and drops one | **(b)** The bound stated through round 8 — "cannot narrow below the first declaration" — measured the parser against its own answer, which is the vacuous-guard defect one survivor over from where round 8 found it. Stated against the right baseline: for a component with two `targets:` keys, the shipped scope is the first list rather than the last, so it may both add and remove targets relative to YAML. Reach: a component would have to declare the key twice, which no component does and which a YAML-aware editor flags. Left open because closing it means choosing a duplicate-key policy the plan does not specify. |
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
round."* Every round from 3 onward has rewritten `_join_flow_sequence`'s docstring, and most rewrites were
themselves defective: rounds 3 and 4 wrote versions false of their own regex, round 5's was accurate
but had no test behind any of it, round 6 scoped an overstated sweep claim and pinned the clauses,
round 7 corrected the boundary description again, round 8 replaced its corpus appeal with a
structural reason, and round 9 falsified THAT reason by enumeration and replaced it with the
space-join argument now in the file. It is the single most-revised sentence on this branch, and every
rewrite before the last was wrong about its own code. Treat any self-descriptive comment in the two parsers, and any "X is pinned in both
suites" claim, as needing its own check rather than trusting the sentence.
