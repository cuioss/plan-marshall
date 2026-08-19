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
| **D1 — filter mechanism** | New `marketplace/targets/component_targets.py` parses the `targets:` declaration and answers `emits_to(path, target_name)`. Both component-tree-emitting targets consult it: the Claude verbatim emitter (`excluded_emission_roots` + `is_under_any`, skipping a scoped-out file or a whole scoped-out skill directory) and its manifest generator (`plugin_json_gen` drops the same entries), and the OpenCode emitter (per-skill / per-agent / per-command skip). The governed set is derived from `TARGET_REGISTRY` filtered by each target's `emits_bundle_tree` capability — never enumerated. Absent field still means every target. | `fab9611` | `test_component_targets.py`, `test_target_scoped_emission.py` — **76 and 14 collected at HEAD**. Counts are stated at HEAD only, never against the implementing commit: `test_component_targets.py` has grown in most rounds and had 24 cases at `fab9611`, so attributing its current count there would name a number that commit never had. (`test_target_scoped_emission.py` has been 14 since `a9c90ef`; the HEAD-only rule is uniform, not a claim that every file moved.) |
| **D2 — fail-closed validation** | `_validate` rejects an unknown target name, an empty list, and a list naming only non-component-tree targets. Every message names the component path and the offending value. Validation fires wherever the emission predicate is CALLED: both component-tree targets' emit paths, and the Claude target's validate-only mode (which re-walks each bundle's components for this check alone). Reading a component is not the same as validating it — a `pr-agent`-only run opens skill manifests to harvest rule text, yet never asks whether a component is in scope, because it emits no component. The doctor rule is the authoring-time net there. | `fab9611` | `test_component_targets.py` + `test_target_scoped_emission.py::test_generation_fails_*` |
| **D3 — first consumer** | `marketplace/bundles/plan-marshall/commands/tools-fix-intellij-diagnostics.md` declares `targets: [claude]`. | `fab9611` | Asserted by generation-output listing (below) |
| **D4 — authoring surface** | New `targets-scope-invalid` plugin-doctor rule (`_analyze_target_scope.py`), registered in `_rule_registry.py` and wired into both the quality gate and analyze mode, with rows in `rule-provenance.md` and `rule-catalog.md` and a firing positive fixture in `_fixtures.py`. The field, its semantics, its validation table, and the three-condition admission test are documented in `plugin-architecture/references/frontmatter-standards.md` § "Target Scoping". | `fab9611` | `test_analyze_target_scope.py` — **117 collected at HEAD** (same HEAD-only rule); the doctor runs clean over the real tree with D3's declaration in place |

### D3 generation-output listing (the plan's own "Done when" evidence)

`uv run python marketplace/targets/generate.py --target all --output {dir}` exits **0**:

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

`git diff --name-only origin/main...HEAD -- '*.py'` reports **22 changed Python files**, so the gate
applies. This figure has gone stale inside the very commit that re-derived it, twice running: round
13 corrected 17 to 18 and `b160c69` immediately made it 22. Eighth and ninth recurrences of a class
this report has tracked since round 2. It is stated once, here, and re-derived at the close of every
round rather than carried forward: **22** at HEAD.

`./pw verify` — **SUCCESS**, all three sub-steps clean. It was re-run after every commit that changed
a Python file; the figures below are from the last such run, and every earlier run is superseded
rather than reported here:

- quality-gate: `ruff … All checks passed!`, `mypy … Success: no issues found in 415 source files`,
  `SPDX-header check passed`, plugin-doctor `total_issues: 0`
- test-compile: mypy over 775 test files, clean
- module-tests: **21167 passed, 14 skipped** — 0 failed, 0 errors

One `./pw verify` run in round 10 reported 3 failures in `test_component_targets.py`; they were an
artefact of a mutation sweep editing the parser while the build was reading it, and the run is
discarded rather than reported. The lesson is recorded because the failure mode is silent in the
other direction too: a mutation sweep run alongside a build can also make a mutant look KILLED for
the wrong reason. Mutation sweeps and builds do not overlap on this branch, and the figures above are
from a run that had the tree to itself.

No lockfile churn: `git status --porcelain` was empty after the build, and every commit staged
deliverable paths explicitly — by name, or with `git add -A --` bounded by an explicit pathspec, which
sweeps nothing outside the named paths. No commit staged the whole worktree.

## Findings

Source key: **V1**–**V15** = pre-PR verification sub-agent, rounds 1 to 15. **S** = self-found
(mutation sweep or my own re-read).

One row per finding. A row states its own instance count where it spans more than one site — `F14–F17`
covers four, and a row saying "both copies" or "both suites" covers two.

**Every per-round number in this report is a ROW COUNT of the round's table below.** Rows, labels and
instances all differ — a row may cover several sites, and a round's verifier may label its findings
differently from how this report tabulates them. Earlier drafts conflated the three and were wrong
every time, so exactly one unit is used here: rows, countable by looking. They are 13, 17, 12, 17, 16,
13, 12, 13, 16, 16, 19, 17, 24, 16, 12 for rounds 1 to 15. **This unit governs the ROW-COUNT
series and nothing else** — the shipped-change split in § Stop record is stated in each verifier's own
units, which is why the two do not reconcile and are not meant to.

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
| Mutation sweep, 4 further mutations after round 2 (`_strip_comment` guard and the flow join, each parser separately) | The round-2 additions | **4/4 reddened**. Kill counts grow as fixtures are added, so they are re-measured after each round's own additions rather than before them — round 6 measured before its and mislabelled the result "at HEAD". At the commit this report is finalised on, measured per suite (generator / doctor): `_strip_comment` **3 / 3**, flow-join **8 / 8**. Round 10 found the single figure here wrong and self-contradicting — it said "7 per suite" where the suites were 8 and 7, while the R2-07 disposition said no single figure covered both |
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
| 7-08 | V7 | The R6-08 counting convention was wrong on every figure it stated — it called label counts row counts, and its two instance totals contradicted each other and the Stop record. | **Fixed, then fixed again in round 8** — the unit it named was still wrong. The report now counts ROWS, which are countable by looking, and states no instance total anywhere. The series is maintained in the § Findings lead-in and cross-referenced elsewhere, never restated. Round 10 found it restated in the Stop record, which is now a cross-reference. |
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
| R8-04 | V8 | The counting convention round 7 introduced was itself wrong: the totals do not count labels either (round 7 has 12 labels, stated as 11; round 1 has 13, stated as 12). | **Fixed** — every per-round number is now a ROW count of the table below it, mechanically re-derived. The series itself lives in the § Findings lead-in and is not restated here, because a second copy is a second thing to keep in step. |
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
re-derivable from its description; the others are not. **This applies to every round, including
the ones below it** — rounds 9, 10 and 11 each state corpus figures whose scripts live in a
session scratch directory, not on the branch, and round 11 found them still being stated as fact
here. Read every corpus figure in this report as that verifier's testimony, attributed to the
round that produced it, not as a reproducible branch artifact.

### Round 9 — BLOCKED, and what was checked without it

**The round did not run.** Two dispatches failed: the first to a mid-response API error, the second to
a **session limit** (resets 23:40 UTC). Neither produced verification. A failed dispatch is not a
round, and is not counted as one — counting it would be the "silence read as a pass" defect this loop
exists to prevent. **Round 9 was re-dispatched and ran** — see the § Round 9 table below. At the time this paragraph was written both rounds were unspent; it is kept as the record of the blockage.

What was done instead is narrower and is labelled as such: the **executable** probes round 9 was
assigned were run directly. These are mechanical — each returns a verdict that could have come back
differently — so they are evidence, not self-assessment. What they cannot replace is an independent
reader, which is the part of the round that is missing.

| Probe | Result |
|---|---|
| **Over-rejection matrix** — a hand-built shape set through the new continued-scalar guard, against PyYAML | ⚠️ **This verdict was WRONG, and round 9 refuted it.** It reported no genuine over-rejection; round 9's own matrix found four — `>-`, `\|-` and quoted multi-line values, which PyYAML reads as sound single values naming a real target. The matrix was hand-built by the author of the guard and is not persisted, so it is testimony of the weakest kind: a sample chosen by the party with an interest in it passing. Round 9 fixed the diagnosis for two of the four (`>-`, `|-`); round 10 found the other two still misdiagnosed — every block-scalar header carrying an indentation indicator, and both quoted multi-line spellings — and fixed them. This row is kept as the record of a self-check that missed. |
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
| R9-03 | V9 | The docstring calls the space join "the load-bearing half"; replacing `' '.join` with `''.join` left the suite **fully green**, including the very test round 9's predecessor added to check the property. | **Fixed in round 10, not round 9.** Round 9's fixture was `targets: [open,` / `code]` — the COMMA splits that value, so it passed under `''.join` too. The test's name asserted the property and its body did not exercise it: the same defect, inside the fix for it. Round 10's fixture drops the comma, and the mutant now dies in both suites (the doctor suite had no such test at all). |
| R9-04 | V9 | "No registered target name contains a space" is the premise that argument rests on, asserted in one docstring and enforced nowhere: `register_target('my target', T)` succeeded. | **Fixed** — `register_target` now rejects a name with whitespace, so the premise is true by construction. |
| R9-05 | V9 | **The guard over-rejects, and my own probe said it did not.** `targets: >-` / `  claude` and `targets: \|-` / `  claude` are valid YAML whose value is `claude`, a registered target; they were refused under a message calling them plain scalars. | **Fixed** — block scalars are detected and rejected under their own name, in both parsers. The probe row above is corrected and kept as the record of a self-check that missed. |
| R9-06 | V9 | Two shipped messages say the build "reads only its first line" — true before the guard, false after. | **Fixed** |
| R9-07 | V9 | Two collection counts stale again — the fourth recurrence of this class. | **Fixed** — re-derived at HEAD. |
| R9-08 | V9 | "seven per suite at HEAD" states no unit, and under any unit the two suites are no longer symmetric. | **Fixed** — the figure is withdrawn rather than restated. |
| R9-09 | V9 | The docstring-rewrite enumeration stops at round 8 and presents its reason as current, in a commit that had just falsified it. | **Fixed** |
| R9-10 | V9 | The row-count restatement lists seven numbers for a convention covering eight rounds. | **Fixed** — the series lives in one place now. |
| R9-11 | V9 | The Round-9 probe row cites "13 shapes" while characterising nine, unpersisted — the standard the report's own ⚠️ note imposes on other rounds. | **Fixed** — the row no longer cites a corpus size, and says plainly what kind of evidence it was. |
| R9-12 | V9 | The block-form "pin" is vacuous: `_has_continuation → True` leaves both block-form checks green, because the guard is structurally unreachable for that form. The commit message claimed the named over-correction was pinned against. | **Fixed** — the claim is withdrawn; the tests remain as coverage of the surrounding behaviour, which is what they actually are. |
| R9-13 | V9 | The sentinel's identity contract ("cannot collide") had no check: `is` → `==` left the suite green. | **Fixed in round 10, not round 9.** Round 9 pinned ONE of the two sentinels; the block-scalar sentinel's `is` → `==` mutant still left the doctor suite green. Round 10 collapsed the duplicated per-shape branches into one identity comparison over a table and parametrised the test across every sentinel, so one mutation now covers all of them. |
| R9-14 | V9 | **Survivor B3's bound was measured against the parser's own answer** — the same vacuous-guard shape round 8 found in F8, one survivor over — and its second half was vacuous. | **Fixed** — restated against the YAML-authoritative last declaration, with both directions named. |
| R9-15 | V9 | Rounds 3 and 5 both use labels `F1`–`F12`, so `F8`/`F9` each name two findings and the survivors table refers to them unqualified. | **Fixed** — survivor references now say which round's F8/F9 they mean. |
| R9-16 | V9 | The field-list sentence, fourth rewrite, classified 13 of 14 fields — the unclassified one being `targets`, this plan's own addition, whose block is in a sibling section. | **Fixed** — all fourteen are placed. |

**Round 9's verdict on convergence, which supersedes rounds 7 and 8's.** Shipped-change findings by
round: 9, 10, 9, 7, 5, 3, **9**. The fall through rounds 4–8 was an artefact of what those rounds were
looking at — rounds 7 and 8 examined the report, and round 8 was the first commit since `fab9611` to
change what the module *does*. **A behaviour change resets the shipped-defect rate**; the loop had not
converged, it had been re-seeded. Any reading of the earlier trend as evidence the mechanism was
settling was wrong, and this report stated that reading twice.

### Round 10

The last round of the operator's five-round extension. Dispatched against `6c33a79` with the round-9
fix commit named as the highest-risk unread surface, because rounds 8 and 9 had each changed module
behaviour and each change re-seeds the defect rate. It was told the four prior behavioural defects
were all OVER-corrections and asked to hunt a fifth.

**A methodology correction that reaches backwards.** The round's first mutation sweep reported four
survivors; one was false, caused by a stale `__pycache__`. `is` → `==` is a **same-length** edit, so
the `.pyc` — validated on mtime-seconds plus size — stayed valid and the subprocess re-ran the
UNMUTATED bytecode. Re-running with `PYTHONDONTWRITEBYTECODE=1` and the caches cleared flipped it to
killed. **Any mutation verdict in rounds 1–9 that came from a same-length edit is suspect**, because
caching was not disabled in those rounds. Every sweep from round 10 on disables it, and the harness
is described here rather than left implicit.

| # | Source | Finding | Disposition |
|---|---|---|---|
| R10-01 | V10 | **The space join was still unpinned, and the R9-03 disposition said otherwise.** Round 9's fixture `targets: [open,` / `code]` splits on the COMMA, so `' '.join` → `''.join` left the suite green — a test whose name asserted the property and whose body did not exercise it. | **Fixed** — comma dropped from the fixture; mutant now dies. The R9-03 disposition is corrected in place. |
| R10-02 | V10 | Same mutant survived in the doctor mirror, which had no space-join test at all. | **Fixed** — the fixture added to the doctor suite too. |
| R10-03 | V10 | **The block-scalar sentinel's identity contract was unpinned, and the R9-13 disposition said otherwise.** Round 9 duplicated the `is` check per shape and covered one copy; `is` → `==` at the other left the doctor suite green. | **Fixed** — the per-shape branches collapse into ONE identity comparison over a table, and the test is parametrised across every sentinel. |
| R10-04 | V10 | **The round-9 fix under-covered by 90%.** The block-scalar set held only the six chomping spellings, so **54 of the 60** legal headers — every one carrying an indentation indicator (`\|2`, `>3-`, `\|-2`) — were still refused under the plain-scalar message the fix existed to remove. Five registers asserted it was fixed. | **Fixed** — a header REGEX replaces the fixed set in both parsers; the indentation spellings are pinned in both suites; all five registers corrected. |
| R10-05 | V10 | **Both quoted multi-line spellings were still misdiagnosed**, and the report said round 9 fixed all four over-rejections it found. `targets: "claude,` / `  opencode"` is `claude, opencode` to PyYAML and is not a PLAIN scalar by definition. | **Fixed** — a third shape with its own noun and its own reason code (`targets_quoted_scalar`). The probe row that missed it is corrected. |
| R10-06 | V10 | **A new fail-OPEN of the same class as the fixed R6-03a.** A frontmatter block whose every line is indented has top-level keys to YAML; the column-zero scan read "no declaration" and shipped the component to every target with its scope unread. 42 of 9,100 combinatorial shapes; the only fail-open family the sweep found. Both parsers. | **Fixed** — the block is dedented by its common prefix first. A key indented BEYOND its siblings still reads as nested, pinned from that side too so the fix is not itself an over-correction. |
| R10-07 | V10 | **Second fail-OPEN: a fence carrying trailing whitespace.** `--- ` and `---\t` read as "no frontmatter" — while `_dep_detection.extract_frontmatter`, this tree's own canonical frontmatter reader, accepts them. Two parsers in one repository disagreed about whether such a file has frontmatter at all. | **Fixed** — both fences match `^---[ \t]*$`, matching the canonical reader. |
| R10-08 | V10 | Three collection counts wrong — **fifth recurrence** of this class. | **Fixed twice.** Round 10 re-derived them and then went stale again inside its own commit, because it measured before adding its last fixtures — the SIXTH recurrence, in the row recording the fifth. No figure is stated here any more: the D1 and D4 rows carry the counts, and one site cannot disagree with itself. |
| R10-09 | V10 | The flow-join kill count was stated as one figure ("7 per suite") where the suites were 8 and 7; it contradicted the R2-07 disposition twenty lines away, which says no single figure covers both; and the R9-08 disposition called the figure withdrawn while it was still stated. Three instances. | **Fixed** — re-measured per suite after this round's fixtures: `_strip_comment` 3 / 3, flow-join 8 / 8, stated as a pair. |
| R10-10 | V10 | "The series is maintained in the § Findings lead-in **and nowhere else**" — it was stated at two sites. (Both agreed, and both were correct; the claim about uniqueness was the false part.) | **Fixed** — the Stop record now cross-references the lead-in instead of restating it. |
| R10-11 | V10 | The authoring standards' validation table reinstated the misdiagnosis round 9 removed from the code: it merged the two rejections into one row and gave the plain-scalar reason for the block-scalar half. Code and register disagreed. | **Fixed** — the row now states the ONE condition and names all three constructs under it. |
| R10-12 | V10 | `register_target`'s new `ValueError` was undocumented, and its stated rationale named a split its guard does not cover ("split on commas" — `register_target('a,b', T)` succeeds). | **Fixed** — a `Raises:` block, and the rationale now names the space JOIN, which is the property the guard actually protects. |
| R10-13 | V10 | "Rounds 9 and 10 of the operator's extension are unspent" was false at HEAD — round 9's table sits directly below it. | **Fixed** — kept as the record of the blockage, with its scope stated. |
| R10-14 | V10 | The round-9 provenance edit left a subject/verb mismatch ("One generator rejection is not mirrored here — … — **asks** each target class …"). Content true, sentence broken. | **Fixed** |
| R10-16 | S | **F9, a five-round survivor, closed rather than re-characterised.** Its proof was sound — the build rejects either way — but R10-04 and R10-05 fixed exactly this misdiagnosis in two other shapes, and `targets:` / `  claude` is the value `claude` to YAML, not an empty list. Keeping it would have left the same defect described three different ways in one module. | **Fixed** — an indented line yielding no `- ` item is reported as a continued plain scalar, in both parsers. Pinned from both sides: a NON-indented next line still reports an empty declaration, so the fix is not an over-correction. |
| R10-15 | V10 | The module docstring's Degradation paragraph argued one direction only: "failing open is correct **because** this module only ever REMOVES output". A fail-open also ships a Claude-only component into OpenCode's tree — which is what R6-03a, R10-06 and R10-07 were all treated as defects for. A one-sided argument presented as a proof. | **Fixed** — both directions stated, with the reason the vanish direction is judged worse. |

**Round 10's evidence.** 114 hand-built adversarial shapes plus 9,100 combinatorial shapes (7 key
spellings × 25 values × 13 continuations × 4 tails), each run through both parsers and PyYAML:
**0 divergences** generator-vs-doctor across the whole corpus, and **0** cases of either parser
inventing a scope YAML does not declare, outside the known duplicate-key survivor B3. Every shape in that
list — anchors, tags, `{}`, `~`, unclosed brackets, tabs, 5,000-character names, 200-element lists,
unicode — lands fail-closed. That is a result about the shapes enumerated, not about malformed YAML
in general, and round 10 stated the narrow one as the general one: round 12 found 47,088 cases in its
own corpus that this parser accepts as a scope while PyYAML raises, `targets:[claude]` (no space
after the colon, which is a plain scalar to YAML rather than a mapping) among them. Deliverables re-verified end to end rather than read: `--target
all` exits 0 at 1166 / 1090 / 1 entries, 160 components walked with exactly 1 scoped,
`tools-fix-intellij-diagnostics.md` present in the Claude tree and its `plugin.json` and absent from
OpenCode's. Mutation sweep 37 mutants, 34 killed, 3 survivors — R10-01/02/03.

**Round 10's own fixes were mutation-tested, cache-disabled: 24 mutants, 24 killed** — the two
fail-open fixes, the dedent's nested-key side, the block-scalar header regex, the quoted shape, the
collapsed sentinel comparison, and the F9 guard in both directions. **The sweep was not exhaustive,
and round 10 said it was:** "every guard added or changed this round is pinned in both parsers" was
false of five more guards round 10 introduced and never mutated — the close fence's line anchor, the
fence search's offset, the block-header pattern's end anchor and its comment stripping, and the
quoted test's threshold. Round 11 found all five unpinned and round 11's own sweep covers them. A
mutation sweep proves what it mutates and nothing else; the count is not the claim.

The tree was byte-restored from an in-memory snapshot after every mutant and `git status
--porcelain` re-checked at the end; no `git checkout`, `restore`, `stash` or `clean` was used at any
point, because the working tree held uncommitted work throughout.

**Convergence, restated for the third time.** The shipped-change series is maintained in the § Stop
record and is not restated here, because a second copy is a second thing to keep in step — the R10-10
remedy, applied to this series too after round 10 stated two different figures for its own round.

What the series shows, stated ONCE here because two sites of it went out of step: rounds **7, 9,
10, 11, 12 and 13** each found a behavioural defect inside the PREVIOUS round's fix — 7-04 in round
6's, R9-01 and R9-05 in round 8's, R10-04 and R10-05 in round 9's, R11-01 in round 10's, R12-01 and
R12-02 in round 11's, and R13-01/02/03 in the `yaml.safe_load` commit. Rounds 9 through 13 are five
consecutive. Three of them — R10-06, R11-01, R12-01 — are the same fail-open in the same function,
answered by three different indentation rules, each wrong about YAML in a new way. (Round 8 is not
in the list: it was the first commit since `fab9611` to change module behaviour at all, so it had
no predecessor's fix to find a defect in. **Round 14 is not either** — its finding predates the last
two commits, so the loop stopped finding defects it had just introduced and started finding one the
rewrite shipped and three rounds missed. That is a different signal, and § Residue reads it.) This
does not describe a loop that is converging; it describes one where each behaviour change re-seeds
the next round. That is
the argument for the design decision recorded in § Residue, not for another round.

### Round 11

The operator granted up to five further rounds after round 10 ("if needed"). Round 10 changed module
behaviour in five places, and this branch's own established finding is that a behaviour change
re-seeds the defect rate, so round 11 was dispatched against round 10's fix commit. It found a
fail-open **inside round 10's fix for a fail-open**.

| # | Source | Finding | Disposition |
|---|---|---|---|
| R11-01 | V11 | **The dedent fix was defeated by a single comment line, in both parsers.** `textwrap.dedent` ignores blank lines but NOT comment lines, so one `#` at column 0 above an indented block pinned the common indent at zero and left every key unscanned — R10-06 re-opened by the shape one over. The severe half is not the widening: `# note` / `  targets: [typo]` and `…[]` **passed the build with nothing reported**, by generator and doctor alike. The fail-closed contract, defeated by a comment. | **Fixed** — a `_dedent_block` helper computes the indent over lines that CARRY STRUCTURE, excluding blanks and whole-line comments, which is what YAML does. Pinned in both parsers from both sides, including the invalid-declaration-under-a-comment case. |
| R11-02 | V11 | `targets: # note` followed by a `- ` block was rejected as "declares an empty list" — a valid declaration naming a real target, refused under a description of a file the author did not write. The comment was being read as the value. | **Fixed** — the inline value is tested AFTER its comment is stripped, so a comment-only value is no value, and the list beneath it is read. |
| R11-03 | V11 | A flow sequence opening on the line BELOW the key (`targets:` / `  [claude, opencode]`) was rejected — first as "empty list", then, after round 10's shape work, as "a plain scalar continued across lines". Round 10 changed the noun on it and never noticed it was rejecting valid YAML. | **Fixed** — `_continued_value` recognises a `[`-initial continuation and folds it, so a flow sequence is one value wherever it opens. |
| R11-04 | V11 | **Five guards round 10 added were pinned by nothing**, and round 10's report said every guard it added was pinned: the close fence's line anchor, the fence search's `start - 1` offset, the block-header pattern's end anchor, its comment stripping, and the quoted test's `< 2` threshold. Each could be loosened with both suites green. | **Fixed** — all five pinned in both parsers, and the false claim corrected at its site. |
| R11-05 | S | **Three of round 11's OWN first pins were vacuous**, caught by mutating them rather than by re-reading. The `---`-prefix fixture used `description: ---x`, where the hyphens sit mid-line and the pattern never reaches them; and the column-zero-comment case was pinned in neither parser. Green either way is not a pin. | **Fixed** — the fixture now uses a `----` line at column 0, and a column-zero comment between a key and its continuation is pinned in both suites. Re-run: 22 mutants, 22 killed, no survivors. |
| R11-06 | V11 | "54 of the 60 legal spellings" — the block-header grammar admits **96**, so the fixed set it replaced misdiagnosed **90**. Four instances (both parsers, both suites) plus the report. | **Fixed** — re-derived mechanically (2 indicators × {bare, indent 1-9, chomp, both orders} = 96) and corrected at every site. The regex covers all 96 and over-matches only the ten `0`-bearing spellings, which YAML rejects as headers anyway. |
| R11-07 | V11 | `_dep_detection` was placed "in the plugin-doctor" / "in this same skill". It is owned by `tools-marketplace-inventory` and imported across skills. Two instances. | **Fixed** — the owning skill is named in both. |
| R11-08 | V11 | **The fence-parity claim was broader than the fix.** That reader matches `\n---` as a PREFIX and so also closes on `----`, where this one does not; parity was restored for trailing whitespace only. | **Fixed** — the divergence is stated at both constants, with the reason it is not closed: adopting the prefix match would re-open the truncation defect the whole-line match exists to prevent. Pinned by the R11-05 fixture. |
| R11-09 | V11 | `_multiline_shape`'s stated limit called its escaped-quote blind spot "a wrong noun **on invalid input**". `"cla\"ude,` / `  opencode"` and the `'it''s,` doubling are valid YAML. | **Fixed** — the limit is stated as what it is: a wrong noun on valid YAML, rejected either way. |
| R11-10 | V11 | The module docstring's ONE-condition parenthetical — "a value that is not a flow sequence, followed by an indented line" — describes `targets:` / `  - claude` exactly, which is ACCEPTED. | **Fixed** — the condition is stated as coded, at both of its sites, with the block form named as the case the loose wording swallowed. |
| R11-11 | V11 | The `start - 1` comment justified the offset by "an empty frontmatter block", where the offset has no observable effect at all. Its only observable effect is on `---` / `---` / more text. Two instances. | **Fixed** — the comment names the case that actually changes, which is also now pinned (it was not). |
| R11-12 | V11 | The authoring standards said a flow sequence "spans lines **freely**" — falsified by R11-03 at the moment it was written. | **Fixed** — restated over the shapes that do span lines, all of which now work. |
| R11-13 | V11 | The standards' coverage sentence named ONE gap in the doctor rule ("except the ships-nowhere case"). In a consumer install the unknown-name check is skipped too — and this document ships to consumers. `rule-catalog.md` already carried the caveat; the authoring surface did not. | **Fixed** — both gaps named, with what still runs. |
| R11-14 | V11 | Round 10 stated **two different** shipped-change figures for itself, in two places. | **Fixed** — one site, and the § Stop record is it. |
| R11-15 | V11 | "the **fourth consecutive** round to find a defect inside the previous round's fix" named three rounds, and a second site called the same set "rounds 7, 9 and 10", which are not consecutive. | **Fixed** — each round named, the ordinal dropped, and round 8's exclusion explained rather than left as an off-by-one. |
| R11-16 | V11 | Three collection counts stale again — the **sixth** recurrence, inside the row recording the fifth. | **Fixed** — the figure is deleted rather than re-derived; the D-rows carry the counts and one site cannot disagree with itself. |
| R11-17 | V11 | "24 mutants, 24 killed … **every** guard added or changed this round is pinned in both parsers" — false of the five guards in R11-04. | **Fixed** — the sweep is described by what it mutated, and the gap is stated. A mutation count is not a coverage claim. |
| R11-18 | V11 | "**Eight** defects, one root cause" in § Residue omits round 1's empty-list misfire and round 4's R4-4 regression, both parser-vs-YAML divergences. | **Fixed** — restated as at least eleven with round 11's three added, which strengthens the row's own argument rather than weakening it. |
| R11-19 | V11 | The corpus-attribution rule ("read them as testimony") is applied to rounds 6 and 7 only, while an R8-12 disposition claims it now applies to every round including its own. Rounds 8, 9 and 10's figures are stated as fact. | **Fixed** — the note is scoped to every round's unpersisted corpus figures, this one included. |

**Round 11's evidence.** A 38,716-case structured corpus and a 25,000-case randomized corpus, each run
four ways: this parser at HEAD, the same parser at the parent commit (extracted with `git show` to a
temp path — never checked out), the doctor mirror, and PyYAML as oracle.

- **HEAD vs the parent commit:** 10,281 verdict changes, **all** attributable to round 10's five
  intended fixes — 10,244 to the dedent, 36 to the fence regexes, 1 to the search offset — and none
  of them a narrowing. No unintended behaviour change.
- **HEAD vs the doctor mirror:** **0 divergences** over 63,716 cases, other than the `emits_bundle_tree`
  check the doctor deliberately omits.
- **HEAD vs PyYAML:** 0 invented scopes and 0 wrong scopes outside the known duplicate-key survivor.
  The only fail-open families were R11-01 and the `----` fence.

**Round 11's fixes were mutation-tested, cache-disabled, with no build running: 22 mutants, 22
killed** — the dedent rule and its structural filter, the comment-as-value fix, the flow-below-key
branch, the continued-value indent check, and the five guards R11-04 named, in both parsers. Three of
the round's first-draft pins were vacuous and were caught by that sweep rather than by re-reading
them (R11-05).

**The sweep was again described as more than it was.** "Every guard this round added or changed, in
both parsers, in both directions where a guard has two halves" was false of `_dedent_block`'s
short-line branch — a round-11 guard with two halves that round 11 never mutated and round 12 found
unpinned. That is R11-17's own finding, recommitted in the sentence closing it. A mutation count is
not a coverage claim, and this is the second consecutive round to write one as though it were.

### Round 12

Dispatched against round 11's fix commit, for the same reason round 11 was dispatched against round
10's. It found the **same fail-open family for the third consecutive round**.

| # | Source | Finding | Disposition |
|---|---|---|---|
| R12-01 | V12 | **FAIL-OPEN, both parsers, third time in this family.** A `min()` over structural lines counts the CONTINUATION of a multi-line value, so `  description: "one` / `two"` / `  targets: […]` pinned the base indent at zero and left the whole block unscanned — R10-06 and R11-01 re-opened one shape over. As with R11-01, the severe half is that an invalid declaration then passes the build unreported by generator AND doctor. 16/16 across four constructs × four declaration kinds, plus 18 hits in a 60,000-case random corpus; the only fail-open family found. | **Fixed, and the rule changed kind.** The base indent is now the FIRST structural line's, which is what sets a YAML block mapping's indentation. And where a structural line sits SHALLOWER than that base, the parser no longer guesses: it raises, because that line is either a multi-line value's continuation or malformed YAML and a line scan cannot tell which. This is a deliberate move from failing open to failing closed — the previous three rules all answered this shape by shipping the component with its declaration unread. A block at indent zero, which is every component in this marketplace, cannot reach the guard. |
| R12-02 | V12 | `_continued_value` hard-coded `_SHAPE_PLAIN_SCALAR`, so a block scalar and a quoted scalar opening BELOW the key were both reported as plain scalars — reinstating R9-05, R10-04 and R10-05 at a site round 11 created to fix something else. | **Fixed** — the shape is diagnosed from the line, exactly as the inline path does. Pinned across all three shapes in both parsers. |
| R12-03 | V12 | The rejection message asserted "That is one YAML value **spanning several lines**" of `targets:` / `  claude`, whose value occupies exactly one line. All 5,184 over-rejections in a 248,400-case corpus are that one shape — so the false clause is on the most common failure this rule produces, and a test asserted it. | **Fixed** — the message now says the value is not on the key's own line alone, which is true of every shape that reaches it. The verdict is unchanged: round 10 chose the rejection deliberately (R10-16) and changing it is a design decision, not a wording fix. |
| R12-04 | V12 | **`_dedent_block`'s short-line branch was pinned by nothing, in both parsers** — a guard round 11 added, in the round whose own headline was five unpinned guards round 10 added. Slicing a comment line by the base indent instead turns `#targets: [opencode]` into a `targets:` key and ships a scope no author wrote. | **Fixed** — pinned in both, with that exact input. |
| R12-05 | V12 | The fold's closing-bracket exit (`if ']' in segment: break`) was unpinned. Deleting it folds the FOLLOWING FIELD into the value and rejects a well-formed declaration. | **Fixed** — pinned in both suites. |
| R12-06 | V12 | The fold's entry guard was unpinned, both halves — a bare value and a closed bracketed value were each folded with nothing red. | **Fixed** — both halves pinned. |
| R12-07 | V12 | Which text the shape test reads (`value.strip()` vs `head`) is observable and was unpinned. | **Fixed** — pinned in both, with the input that distinguishes them. |
| R12-08 | V12 | **The doctor's `_has_continuation` was unpinned where the generator's is killed:** every doctor fixture used a bracketed value, where the `and` short-circuits before the check runs. Forcing it to `True` left the doctor suite green while flagging every bare declaration as a continued scalar. The same structural blind spot as R12-04 — a guard pinned on one side of a mirror and not the other. | **Fixed** — bare-value fixtures added to the doctor suite. |
| R12-09 | V12 | `_dedent_block`'s residue paragraph was false in both halves: a column-zero structural line does NOT imply "YAML has a node there", and the residue is not "exotic spellings" — it is the ordinary multi-line values of R12-01. | **Fixed** — the paragraph is rewritten over the family that actually reaches it, and names the two rules that were wrong before it. |
| R12-10 | V12 | "stripping it first would **hide the quote** this looks for" — an exhaustive probe over every string of length 1-5 in the relevant alphabet found **0** such inputs; the 54 that differ go the other way. | **Fixed** — the true reason is stated, and it is the opposite of the one written down. |
| R12-11 | V12 | "the build reports it under whichever of three constructs you wrote" was false at the `_continued_value` site. Six sites. | **Resolved by R12-02** — the claim is true again now that the site diagnoses. |
| R12-12 | V12 | **R11-11's disposition said its fix landed at "two instances"; one landed.** The doctor still carried the exact false comment round 11 removed from the generator. | **Fixed** — and this is the mirror-parity blind spot again, in a disposition rather than in code. |
| R12-13 | V12 | `_strip_comment`: "what keeps a hypothetical name containing `#` intact" — false of a quoted `#`. `["a #b"]` is one name to YAML and this splits it. | **Fixed** — bounded to unquoted values, with what the split costs (the wording, not the tree). |
| R12-14 | V12 | "Parity is restored for trailing whitespace and for nothing else … [only] `----`" — a second, unnamed disagreement exists: that reader does not strip a UTF-8 BOM. Two sites. | **Fixed** — both disagreements named. (Round 12 also checked CRLF end-to-end and confirmed it is NOT a divergence: `read_text` applies universal newlines before either parser sees the bytes.) |
| R12-15 | V12 | The replacement `start - 1` comment over-generalised: "would skip that fence and read them as fields" holds only when a THIRD fence exists; with none, the file reads as having no frontmatter. Two sites. | **Fixed** — the condition is stated at both. |
| R12-16 | V12 | **"22 mutants, 22 killed … every guard this round added or changed, in both directions"** — false of R12-04, a round-11 guard with two halves. R11-17's own finding, recommitted in the sentence closing it. Second consecutive round of writing a mutation count as a coverage claim. | **Fixed** — the sweep is described by what it mutated, and the recurrence is named as a recurrence. |
| R12-17 | V12 | Round 10's "everything malformed lands fail-closed" is a claim about the shapes it enumerated, stated as a general one. 47,088 cases in round 12's corpus are accepted as a scope while PyYAML raises — `targets:[claude]` with no space among them. | **Fixed** — scoped to the enumerated shapes, with the counter-example. |

**Round 12's evidence.** A 248,400-case structured differential, a 60,000-case randomised
differential, a 90,000-string exhaustive shape probe, and ~60 hand-built shapes — each run four ways
(HEAD, the parent commit extracted via `git show` to a temp path, the doctor mirror, PyYAML).

- **Verdict-diff vs the parent:** 18,747 changes, **0 unexplained** — each attributable to one of round
  11's three intended fixes, classified by re-deriving those predicates independently.
- **Generator vs doctor:** **0 divergences over 308,400 cases**, excluding the deliberately-omitted
  `emits_bundle_tree` check.
- **Vacuity audit of every pin added in the last two commits:** none vacuous. This round's gaps were
  guards with NO test (R12-04 to R12-08), not tests that fail to discriminate — a different failure
  mode from round 10's and round 11's, and one a coverage claim hides just as well.
- Round 12's own sweep: 65 mutants, 57 killed, 6 real survivors and 2 equivalent mutants it identified
  as equivalent and argued for.

**Round 12's fixes were then mutation-tested, cache-disabled, with no build running: 43 mutants, 43
killed, no survivors.** The sweep covers both parsers' full guard set, not only this round's
additions — including every guard round 12 found unpinned, in both directions where a guard has two
halves, and `register_target`. Two doctor-side survivors appeared on the first pass, both guards
pinned on the generator side only; the mirror-parity gap R12-08 and R12-12 name is what that sweep
was widened to catch, and it caught two more instances of it immediately.

### Operator decision — the generator reads YAML

**Put to the operator after round 12; answered "switch the generator to `yaml.safe_load`".**

The § Residue decision this report had been deferring for two rounds. The evidence for putting it
rather than a thirteenth round: every behavioural defect across twelve rounds was the hand-rolled
parser disagreeing with YAML, and three of them — R10-06, R11-01, R12-01 — were the SAME fail-open in
the same function, answered by three successive indentation rules, each wrong about YAML in a new
way. Two verifiers reached the same conclusion independently.

**What changed**

| | |
|---|---|
| **Reading** | `marketplace/targets/component_targets.py` calls `yaml.safe_load` on the fenced block. What it still owns is finding the fence — markdown frontmatter is not a YAML document stream, and the body beneath the closing fence would parse as a second document — and the SHAPE rules, which are policy rather than syntax. |
| **Dependency** | `PyYAML>=6.0.2` declared in `[project].dependencies`, `types-PyYAML` in the dev group, `uv.lock` regenerated. The generator now runs inside the project environment, so every documented `python3 marketplace/targets/generate.py` invocation became `uv run python …` — 16 sites across the developer docs, two project-local skills, `CLAUDE.md` and two READMEs. |
| **Doctor rule** | Narrowed from a mirror to an **approximation**, and says so. A plugin-doctor script is stdlib-only because a consumer project installs the bundles without this repository's dependencies, so it cannot follow. It now reads the shapes it is certain of and stays SILENT on the rest, reporting only `targets_unknown` and `targets_empty`. Four reason codes and ~180 lines of parser were deleted. |
| **The promise it makes** | Soundness, not completeness: anything it reports is a real build failure. That is now a TEST — a shared corpus run through both the rule and the build, failing if the rule ever flags something the build accepts — rather than a sentence. |

**What the decision deletes.** Sixteen behavioural defects' worth of surface: the shape/noun
machinery (three constructs × two parsers), the indentation rules, the fold and its boundary
heuristic, the comment-vs-value guard, the quote-matching key reader, the ambiguous-indent refusal,
and every "is this claim about the parser true?" finding those generated. Survivor **B3** goes with
them — a duplicate `targets:` key now resolves the way YAML resolves it, last-one-wins, so the
eight-round-old open behavioural survivor is closed without a policy decision. **Seven** shapes the line
scanner refused are now simply read; `test_shapes_a_line_scanner_refused_are_now_read` carries nine,
because two of them — the indented-block rows — had already been fixed by rounds 10 and 11 and are
kept as the shapes three successive indentation rules were written for. It is the record that
accepting them is deliberate, so a future edit that re-refuses one has to argue for it there.

**What it costs, stated rather than glossed:**

- A build dependency where there was none. `marketplace/targets/` was pure stdlib.
- The two parsers stop being mirrors. The "0 divergences over 308,400 cases" property rounds 11 and
  12 relied on no longer means anything, because they are no longer trying to agree. The soundness
  test replaces it and is a weaker guarantee — deliberately, since the stronger one was only
  available while both sides were equally wrong.
- Two shapes now fail closed that previously passed: a bare `----` line inside frontmatter (invalid
  YAML; the old scanner skipped it), and unparseable frontmatter that mentions `targets:`. The
  second is scoped ON PURPOSE — unparseable frontmatter that never mentions the field is refused by
  nothing here, because turning target scoping into the repository's YAML linter is a job the plan
  did not give it and a failure surface it should not widen.
- One test fixture in the OpenCode variant suite was itself invalid YAML (`description:` with an
  unquoted `: ` in it) and had to be repaired. The real agent it imitates uses a `|` block scalar.
- **Any unquoted TAB in frontmatter now fails the build** for a component mentioning
  `targets:`, where the line scanner tolerated it — not only a trailing one, which is how this cost
  was first written. A tab is invalid YAML there and every reader
  rejects it; normalising it would mean pre-processing the text, which is the hand-rolling this
  decision removed. No component in the tree carries one. Found by round 13, recorded not fixed.
- **Both CI workflows that invoke the generator had to be repaired** (`c99a84b`). They ran a bare
  `python3` after `actions/setup-python` with no install step, so `opencode-generate-check.yml` —
  which triggers on `marketplace/**` — would have failed on the very commit that added the
  dependency, and `claude-distribute.yml` would have broken the release path.

**Reach check before landing.** All 160 components' frontmatter parses under `yaml.safe_load` — zero
unparseable — and generation is unchanged: `--target all` exits 0 at 1166 / 1090 / 1 entries, 160
components walked, exactly 1 scoped, `tools-fix-intellij-diagnostics.md` present in the Claude tree
and absent from OpenCode's.

**Size, as a proxy for what was carrying the defects.** The generator parser fell from 775 lines to
**520**, and the two suites went from 122 + 86 collected tests to **76 + 117**. The doctor rule ends
at **542** against its old 635 — near where it started, which is the honest shape of the result: the
parser it lost was replaced by guards that keep it from reporting on what it cannot read, and by a
suite that pins every one of them. Roughly half of each suite existed to pin a hand-rolled rule against YAML, and those
tests went with the rule they pinned; what replaced them is one soundness test over a shared corpus
and one list of shapes that used to be refused and are now read.

### Round 13

Dispatched against the `yaml.safe_load` commit. It found that the refactor **shipped a new instance
of the defect class it was authorised to remove**: the rewritten doctor rule reports build-failing
errors on valid components. That is worse in kind than what it replaced, because the old parser at
least agreed with itself.

| # | Source | Finding | Disposition |
|---|---|---|---|
| R13-01 | V13 | **The doctor's soundness promise was false.** `targets:` followed by a **column-zero** `- ` block — idiomatic YAML, and what an author writes first — was reported `targets_empty` at `error` severity, build-failing under `quality-gate`, while the build read a valid scope. | **Fixed** — a sequence item may sit at column zero; only a column-zero NON-item is the next field. |
| R13-02 | V13 | Second soundness break: a **duplicate `targets:` key**. The doctor read the first occurrence, YAML and the build take the last, so it reported on a declaration the build does not use. Three variants. | **Fixed** — every column-zero occurrence is examined and the LAST readable one wins; if any is unreadable the whole file is, because the scanner cannot then know which declaration the build will use. |
| R13-03 | V13 | Third: `targets:#c` was read as an empty declaration. YAML needs whitespace after the colon for a mapping key, so that line is a plain scalar and there is no key at all. | **Fixed** — a key now requires whitespace (or nothing) after its colon, which is YAML's own rule. It also aligns `targets:[claude]`, where the two readers previously disagreed. |
| R13-04 | V13 | **The soundness test did not contain either failure mode.** Its only duplicate-key row was the ordering under which both readers stay silent; there was no column-zero block sequence at all. The test that exists to prevent R13-01/02 would not have caught them. | **Fixed** — the corpus went from 33 rows to 53, covering every shape both suites exercise, both duplicate-key orderings, the no-space-after-colon family, and every declined shape. |
| R13-05 | V13 | **`_mentions_the_field` failed OPEN, and its docstring said it could not.** The `^\s*` anchor missed a key that is not at a line start, so `{targets: [typo], name: x` — unparseable frontmatter DECLARING the field — shipped the component everywhere with the declaration unread. | **Fixed** — the anchor is gone, which is what "deliberately over-inclusive" was supposed to mean. The docstring now names the defect instead of denying it. |
| R13-06 | V13 | `read_target_scope` caught only `yaml.YAMLError`; a deeply nested flow collection raises `RecursionError` inside the parser, which escaped and aborted the generator with a raw traceback. | **Fixed** — caught alongside `YAMLError`, so the failure names the file. |
| R13-07 | V13 | **"every documented invocation became `uv run python …`" was false — 17 remained**, each naming a command that now dies with `ModuleNotFoundError`. Among them `AGENTS.md` (whose `CLAUDE.md` twin WAS updated), the generator's own `--help` epilog, and seven **remediation messages the build itself prints when a gate fails**. | **Fixed** — all 17 converted, plus the emitted `.pr_agent.toml` header regenerated. |
| R13-08 | S | **Both CI workflows that invoke the generator ran a bare `python3` with no install step.** `opencode-generate-check.yml` triggers on `marketplace/**`, so this PR would have failed its own check on the commit that added the dependency; `claude-distribute.yml` would have broken the release path. Found while preparing the PR, not by the round. | **Fixed** in `c99a84b` — both install the declared dependencies first, deriving the constraint from `pyproject.toml` so CI cannot carry a second copy that drifts. |
| R13-09 | V13 | **Four properties lost their pins in the rewrite**, each confirmed by a surviving mutant: the close fence's trailing TAB, the close fence at EOF with no trailing newline, the doctor's BOM stripping, and the doctor's immediately-closed-block offset. The last is soundness-load-bearing. | **Fixed** — all four re-pinned. |
| R13-10 | V13 | **Three rows of `test_shapes_the_scanner_declines_to_read` did not exercise the guard they name** — a continuation check or the bracket test declined them first, so dropping `>`, `\|` or `&` from the opener set left the suite green. `&` is independently soundness-load-bearing. | **Fixed** — rows added that reach the opener check. |
| R13-11 | S | **And the first draft of round 13's own fix for R13-10 was vacuous**, in the same way: the comment-continuation fixture indented its comment, which is already "indented" to the guard. Caught by mutating it, not by reading it. | **Fixed** — the comment sits at column zero; the mutant now dies. Third consecutive round in which a fix for vacuous pins was itself vacuously pinned. |
| R13-12 | V13 | Five further guards were unpinned — two blank-token filters and three `_is_readable` clauses. None broke soundness alone, which is exactly why nothing caught them: a guard that only stops the rule being *wrong-but-still-failing* is invisible to a test that checks the verdict. | **Fixed** — all five pinned. |
| R13-13 | V13 | **Trailing-tab regression, undocumented.** One stray TAB anywhere in frontmatter now hard-fails the build for any component mentioning `targets:`; it built fine before. | **Recorded, not fixed** — see the cost list in § Operator decision. A trailing tab is invalid YAML and every reader rejects it; normalising it would mean pre-processing the text, which is the hand-rolling the decision removed. No component in the tree carries one. |
| R13-14 | V13 | Line counts wrong: "785 and 664" — no commit on the branch ever had those. | **Fixed** — 775 and 635. |
| R13-15 | V13 | **A stale count inside the clause asserting the count was not stale**: "17 changed Python files … unchanged by the switch because it added none". It is 18; `24140ec` added the test file whose fixture repair the same report lists as a cost. **Seventh recurrence** of this class. | **Fixed** — 18, and the "added none" clause deleted. |
| R13-16 | V13 | Survivor B3 was recorded as OPEN in two places after the same report said it was closed. | **Fixed** — struck from both, with the observation that the "policy the plan does not specify" never needed specifying, because YAML specifies it. |
| R13-17 | V13 | § Residue was stale: three of its five rows had been answered by the operator decision recorded 170 lines above. | **Fixed** — resolved rows struck through rather than deleted, since the evidence that put them there is the argument for the decision. A new open row is added: does the doctor rule earn its place at all? |
| R13-18 | V13 | "15 sites" converted (16); "three reason codes deleted" (four); "nine shapes now read" — two of the nine were ACCEPTED by the parser being replaced, having been fixed by rounds 10 and 11. | **Fixed** — 16, four, and seven-of-nine with the two explained. |
| R13-19 | V13 | `rule-catalog.md`'s recommended fix named "the two value-shape reasons", which no longer exist (and "two" was wrong when there were three). | **Fixed** |
| R13-20 | V13 | "**Write it however YAML lets you** … any spelling YAML accepts is a spelling this field accepts" — falsified by the validation row three lines above it: `targets: {claude: yes}`, `targets: 3`, `targets: true`. | **Fixed** — scoped to what YAML must RESOLVE to, with the table named as the value rule rather than a syntax rule. |
| R13-21 | V13 | A test docstring listed a `----` line among the shapes it pins as not hiding a declaration; no such param exists, and `----` deliberately fails closed in the sibling test. | **Fixed** |
| R13-22 | V13 | The soundness promise was asserted as fact at **seven sites** while the code did not have it. | **Resolved by R13-01/02/03** — the prose is true now. |
| R13-23 | V13 | `excluded_emission_roots`' "validates every component of the bundle" holds for the Claude path only; OpenCode validates what its `plugin.json` declares. | **Fixed** — the docstring scopes the claim and names what covers the gap. |
| R13-24 | V13 | Commit `c99a84b` was recorded nowhere in the report. | **Fixed** — R13-08 above, and a cost row. |

**Round 13's evidence.** A 338-case adversarial differential against PyYAML; a verdict-diff against
`51f6abc` (20 widenings, 23 narrowings, 0 scope changes, every widening intended); a 44-mutant sweep
finding 13 survivors; and — the measurement that mattered — **the doctor's soundness quantified
rather than asserted**: over a 334-case corpus, 249 real build failures, 159 caught (**64%
complete**), and **10 false positives across 4 root causes**. The documented trade was "incomplete
but sound"; what shipped was neither.

**After the fixes: 41 mutants, 41 killed, no survivors**, cache-disabled with no build concurrent.
The soundness corpus is now 53 rows and contains every shape that broke it.

### Round 14

Dispatched against round 13's fix commit. It found a **fifth** way the doctor rule fails the build on
a valid component — the same class as round 13's headline, in the same function, found by the same
method, and live since the rewrite rather than introduced by the last fix.

| # | Source | Finding | Disposition |
|---|---|---|---|
| R14-01 | V14 | **The soundness promise was false again.** `_is_readable` inspected only the value's FIRST character, so a quoted, tagged or anchored item INSIDE a flow sequence read as a bare name — and since nothing here unquotes, the rule reported `"claude"`, quotes included, as an unknown target at `error` severity while the build shipped the component fine. **757 unsound cases in a 157,951-shape corpus**, 753 of them present since the rewrite. The branch's own generator fixtures pin that exact spelling (`targets: ['claude']`) as one an author may write, and the standards page shipped alongside says "write it however YAML lets you". | **Fixed** — every item is checked, not the opener alone. This is also the narrowing round 14 recommended: the rule now reads a flow sequence of BARE names and nothing else. |
| R14-02 | V14 | **The corpus written to prevent exactly this omitted the shape that breaks it** — 10 of the 18 `_ACCEPTED_FORMS` rows were missing, `quoted-item` among them. R13-04 recurring verbatim: a hand-copied corpus has now missed the live defect twice. | **Fixed** — the corpus is DERIVED from the fixtures both suites already maintain, so a shape cannot be added to either suite and left out of the soundness check. Verified discriminating: mutating the new guard reddens it. |
| R14-03 | V14 | The soundness promise was asserted at **seven shipped sites and two report sites**, including R13-22's disposition reading "the prose is true now". | **Resolved by R14-01** — and the two coverage-boundary enumerations now name the flow-item case explicitly rather than describing a rule that is sound. |
| R14-04 | V14 | **Round 13's own headline generator fix was pinned by nothing.** Re-anchoring `_MENTIONS_FIELD_RE` to the pre-fix code left all three suites green. | **Fixed** |
| R14-05 | V14 | Round 13's `RecursionError` fix was pinned by nothing either. | **Fixed** |
| R14-06 | V14 | Nine further guards unpinned, **four of them soundness-load-bearing**: the null branch of the duplicate-key loop, the unreadable-duplicate rule for the block path, the per-item check in a block sequence, and `"` in the opener set — which R13-10 had fixed for `>`, `\|` and `&` and left. | **Fixed** — all pinned, in both suites where the mirror-parity gap applied. |
| R14-07 | V14 | **All three fence properties were pinned in the generator suite and in neither for the doctor.** The R12-08 / R12-12 mirror-parity class, third occurrence. | **Fixed** |
| R14-08 | V14 | The soundness test's own oracle was inconsistent: the fake registry omitted `pr-agent` while the build had it, so a false positive on a `pr-agent`-bearing declaration would be created or masked by the mismatch rather than measured. | **Fixed** — both sides register the same set. |
| R14-09 | V14 | `_mentions_the_field`'s docstring asserted an impossibility. A double-quoted key can spell the field with an escape and so carry no literal `targets` text. | **Fixed** — the residue is stated rather than denied, with its bound: such a file must ALSO be unparseable YAML for the function to be consulted, so it is already broken for every other frontmatter consumer in the tree. |
| R14-10 | V14 | `_strip_comment`'s docstring claimed "a quoted value is one this scanner declines to read at all, so it never reaches a case where that would matter" — falsified by R14-01's input. | **Fixed** — scoped to a value whose FIRST character is a quote, and it now names what actually keeps the function safe. |
| R14-11 | V14 | R13-18 fixed the "nine shapes" count and got the identity wrong: the two rows that were ACCEPTED at `51f6abc` are the indented-block pair, not the last two. | **Fixed** — both named. |
| R14-12 | V14 | **"41 mutants over both files' full guard set, 41 killed, no survivors"** — a 64-mutant sweep over the same two files found 17 survivors, 11 real. **Fourth consecutive round** of a mutation count written as a coverage claim. | **Recorded.** The commit message is pushed and cannot be corrected; this row is its correction. The rule this report keeps failing to apply: a sweep proves what it mutated, and the honest sentence names the guards, not the number. |
| R14-13 | V14 | "18 changed Python files" — 22 at HEAD. `b160c69` made it stale, which is the commit whose own row corrected 17 to 18. **Eighth and ninth recurrences.** | **Fixed** — and the figure now says outright that it is re-derived every round rather than carried. |
| R14-14 | V14 | § Stop record said two of five extension rounds were spent, with a 24-row § Round 13 table 30 lines above it. Verbatim R10-13. | **Fixed** |
| R14-15 | V14 | The "rounds that found a defect in the previous round's fix" list existed at two sites, both incomplete and disagreeing. R11-15 was this exact finding. | **Fixed** — stated once, in § Round 10's convergence note, and cross-referenced from the Stop record. |
| R14-16 | V14 | The report's own D3 reproduction command was one of the 17 invocations R13-07 converted — unconverted, in the report. | **Fixed** |

**Round 14's evidence.** 79,356 randomised shapes through the generator against PyYAML: **0
fail-opens, 0 over-rejections, 0 scope divergences**. A 157,951-case verdict-diff against `24140ec`:
62,466 changes, **0 unexplained**. Doctor soundness over the same corpus: 49,966 reports, **757
unsound, all one root cause**. Completeness re-measured at **31%** on a 147,545-shape corpus — round
13's "64%" was its own smaller corpus and the two are not comparable, which is itself worth stating,
because a completeness figure without its population is not a figure. CI wiring verified end to end:
the `tomllib` one-liner runs verbatim, `python-version: '3.x'` guarantees ≥3.11, the quoting survives
YAML→bash, and the install step precedes the generator step in both workflows.

**After the fixes: 40 mutants, 40 killed, no survivors** — four of round 13's mutants no longer apply
because the code they targeted is gone. D1–D4 re-derived from generated output and all hold.

### Round 15

The last round. It found a **sixth** doctor soundness root cause — one that predates the fixes for
the fourth and fifth rather than being introduced by them, and that both of those rounds missed.

| # | Source | Finding | Disposition |
|---|---|---|---|
| R15-01 | V15 | **A `targets:` line that is the CONTINUATION of a construct opened above it was read as a top-level key.** An unterminated `[`/`{`, or a quoted scalar spanning lines, leaves the next line inside it — YAML knows that; a line-local scan does not. The rule reported at `error` severity while the build saw no key at all. **430 counterexamples across ~339,000 shapes, exactly one root cause**, live since the `yaml.safe_load` rewrite. | **Fixed** — a bracket/quote balance over the lines above each candidate key. A quote counts as opening a scalar only in VALUE position, so an apostrophe in `description: it's fine` is not mistaken for one; and where the check is wrong anyway it reports MORE lines as open, which only makes the rule decline. Declining costs completeness; reading a fragment costs soundness, which is the only thing this rule promises. **Zero of the 160 real components are affected.** |
| R15-02 | V15 | **The "derived" corpus did not derive from what it claimed.** It dropped the rows whose payload lives in `_ONCE_REFUSED_WHOLE_FILE` — one of them the indented sibling of R15-01's family — derived from one suite only, missing 27 shapes the doctor's own fixtures exercise, and 54 of its 78 rows were still hand-written. R14-02 recurring. | **Fixed** — this suite's shape rows are hoisted into five module-level tuples that both the parametrize lists and the corpus read, and the corpus pulls from all of them plus all three generator fixtures. A row cannot now be added to either suite and missed by the check. |
| R15-03 | V15 | Three more guards unpinned and **soundness-load-bearing**: `_unquote_key`'s matched-pair test (600 unsound cases when loosened), the `not separator` guard (884), and `_REGISTER_TARGET_RE`'s character class — which drops `pr-agent` from the derived registry, the R14-08 class again, and which the corpus alone cannot catch because `targets: [pr-agent]` fails the build anyway. | **Fixed** — a mixed declaration discriminates the registry case; the other two are fixture rows. |
| R15-04 | V15 | **The rule's `severity='error'` was pinned by nothing.** Downgrading it to `warning` left every test green while the rule stopped failing the build — the thing two register documents describe it as doing. | **Fixed** |
| R15-05 | V15 | `_is_readable`'s emptiness check was unpinned, and dropping it raises `IndexError` **inside a quality-gate rule**. | **Fixed** — an empty block item pins it. |
| R15-06 | V15 | `_strip_comment`'s docstring named the wrong decliner, falsified by its own example: `["a #b"]` is declined by the closing-bracket test, not by `_is_bare_name`. R14-10 rewrote this sentence and got the mechanism wrong. | **Fixed** — both cases named, and which one each example exercises. |
| R15-07 | V15 | A **branch-introduced `ruff I001`** in `marketplace/targets/claude/target.py` that no gate lints: the quality gate's ruff scope is `marketplace/bundles/`, `test/` and `.claude/` — the generator tree is outside it entirely. | **Fixed.** The scope gap is recorded in § Residue rather than closed here: widening it surfaces pre-existing violations across a tree this plan does not own. |
| R15-08 | V15 | `TARGET_SCOPE_FIELD` was exported in `__all__` with zero consumers. | **Fixed** — removed. |
| R15-09 | V15 | `excluded_emission_roots(...)` was called for its exception alone, its return discarded, with the intent only in a comment above it. | **Fixed** — a named `validate_component_scopes(bundle_dir)`, so the intent is in the name rather than in prose beside it. |
| R15-10 | V15 | The report contradicted itself about the unit of its per-round numbers: "every per-round number is a ROW COUNT" against a split series stated "in that verifier's own units". | **Fixed** — the lead-in is scoped to the row-count series, and says outright that the two series do not reconcile and are not meant to. |
| R15-11 | V15 | § Residue was off by one after round 14, and its live decision row still cited round 13's "64% complete, unsound in four ways" after round 14 had found a fifth. | **Fixed** |
| R15-12 | V15 | The trailing-TAB cost was understated: **any** unquoted tab fails, not only a trailing one. R13-13's own wording was the accurate one and the cost list weakened it. | **Fixed** |

**Round 15's evidence.** ~339,000 shapes for doctor soundness across four corpora — **430
counterexamples, exactly one root cause** — with the sub-population having no multi-line opener above
the key returning **0**, which is what identified the cause. 250,000 randomised shapes for the
generator against an independent extractor plus PyYAML: **0 fail-opens, 0 scope divergences, 0
over-rejections**. A 33,048-shape verdict-diff against `b160c69`: 1,152 changes, **0 widenings**,
every one explained. 82 mutants, 67 killed, 15 survivors of which 6 were proved equivalent.

**Completeness, with its population** — a figure this report has quoted three different values for,
each on a different corpus, which is why it now always carries one: **34.5%** at HEAD over a
22,032-shape safe-prefix population. Round 14's narrowing cost 3.2 points, intended and tolerable.

**After the fixes: 49 mutants, 49 killed, no survivors** — including R15-01's new guard, the severity
descriptor, and every guard round 15 found bare.

### Post-PR — the merge conflict, and why no CI ran

PR **#1313** was opened at 22:36Z. Thirty minutes later it had **no `verify` check run at all** — only
`Sourcery review / skipped`. Two things were wrong, and they were the same thing:

- **`mergeable_state: dirty`.** `main` had moved while the fifteen rounds ran (PRs #1307, #1310,
  #1311 and others landed the same afternoon). GitHub could not build the PR's merge ref, and a
  `pull_request` workflow runs against that ref — so `python-verify.yml` never fired. The absent
  check was a symptom of the conflict, not a second fault.
- The negative was **verified before it was believed**, per this contract's own rule: a branch-filtered
  `list_workflow_runs` returned `total_count: 0`, and a positive control on the same workflow returned
  rows including a `pull_request` run on another `claude/*` head. Only then was the zero treated as
  real.

`origin/main` was merged into the branch. Git resolved every path itself — including main's rename of
`test/pm-plugin-development/plugin-doctor/_fixtures.py` to `_plugin_doctor_fixtures.py`, which this
branch had modified.

**One test then failed, and it was this branch's to fix.** A loader-contract guard that landed on main
during the run bounds how many loader call sites it cannot resolve statically, at 90. This branch adds
a plugin-doctor test file, and every file in that directory uses a `_load_module(name, filename)`
helper whose forwarded parameters are invisible to the guard — so the count became 91.

The bound was **not raised**. Raising it is what the guard's own docstring calls widening the blind
spot, and the remedy it asks for is to pass literals. The call site now does, which puts this file
*inside* what the guard can see and returns the count to 90 — a fix that shrinks the gap rather than
documenting a larger one. Measured both ways to be sure the delta was this branch's: `origin/main`'s
test tree scans at 90, this branch's at 91, and the one added entry named this file.

`./pw verify` on the merged tree: **SUCCESS — 21277 passed, 14 skipped**.

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

**A third budget is open, and four of its five rounds are spent** — 11, 12, 13 and 14. The contract's
default five and the operator's first extension are gone; after round 10 the operator granted up to
five more "if needed", and after round 12 asked for the remainder to be run if sensible. Each was:
rounds 11 and 12 each found a fail-open inside the previous round's fix, round 13 found the doctor
rewrite failing the build on valid components, and round 14 found a fifth way it did the same thing.
**Round 15 remains.** No round ever returned "nothing remains": round 10 answered the
stop question **"Yes, condition A is violated"** and named fifteen items, all of which were fixed,
as condition A requires regardless of budget. What a spent budget ends is the *verifying*, never the
*fixing*.

At the second boundary the report does not ask for a third extension. Round 10's own standing-back
section is the reason: four consecutive rounds have found a defect inside the previous round's fix,
and every behavioural defect on this branch has one root cause that no verification round can
remove. What is owed at this boundary is a **decision**, and the decisions are in § Residue.

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

**Rounds and what they found:** the per-round row counts are in the § Findings lead-in, which is
the single site that maintains them. Two further round-5 dispatches died to server-side API errors (one mid-response, one a
529) before doing any work; neither is counted as a round, because a failed dispatch produced no
verification and counting it would be the "silence read as a pass" defect this loop exists to catch.

**Convergence: none.** Each round was asked for the shipped-change vs report split: round 3 9/12,
round 4 10/17, round 5 9/19, round 6 7/13, round 7 5/11, round 8 3/13, round 9 **9/16**, round 10
**8/16**, round 11 **12/19**, round 12 **15/17**, round 13 **13/24**, round 14 **11/16**, round 15 **9/12** (each as its verifier reported it, in that verifier's own units). Rounds 7 and 8 read the
fall through rounds 4–8 as narrowing; **round 9 refuted that** and this report's earlier statement of
it, and round 10 confirmed the refutation. The fall was an artefact of what those rounds examined —
the report, not the code — and round 8 was the first commit since `fab9611` to change what the module
does. *A behaviour change re-seeds the shipped-defect rate*; which rounds found a defect inside the previous
round's fix is listed once, in § Round 10's convergence note, and is not restated here.

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
| **F9** (round 5's) — `targets:` plus an indented scalar reports "declares an empty list" | ~~Survivor~~ **closed in round 10** | Carried through rounds 5–9 on a sound proof — the build outcome is unchanged, only the message misnames the defect. Round 10 fixed the same misdiagnosis in two other shapes (R10-04, R10-05), which left no principled reason to keep this one: `targets:` / `  claude` is the value `claude` to YAML, and it now says so. Pinned from both sides, so a genuinely empty declaration keeps its own message. |
| **B3** — a duplicate top-level `targets:` resolved to the FIRST declaration; YAML takes the LAST | ~~Survivor~~ **closed by the operator decision** — the build delegates to YAML, so last-one-wins. Round 13 found the doctor still reading the first, which was a soundness break in the rule rather than a live survivor here, and fixed it. | **No bound needed.** It was open for eight rounds under a bound that measured the parser against its own answer, then a corrected one. Delegating the read closed it without a policy decision — the "duplicate-key policy the plan does not specify" turned out not to need specifying, because YAML already specifies it. |
| **B5** — OpenCode's `_prune_stale_outputs` runs only on a full regeneration, so a `--bundles` subset emit can leave a scoped-out component behind | Behavioural, pre-existing | **(b)** Bounded to scoped emits. The normal build and both drift checks run full regenerations; the constraint is documented at the function with its reason. Unchanged by this plan — reachable through a new cause, not newly created. |
| **B6** — `check_bundle`'s orphan sweep covers `agents/` and `commands/`, not skill directories | Behavioural, pre-existing | **(b)** Bounded to validate-only mode over a stale tree. Any emit wipes each bundle's destination first, and `content_drift`'s `orphan_in_target` catches a stale `.md` because it regenerates through `ClaudeTarget`. A deleted skill was equally invisible before this plan. |

Every one was re-put to the verifier in the stopping round and re-characterised there, not carried
forward unread.

**Residue to assume remains:** see § Residue. In short — the parsers are well evidenced by
enumeration and by mutation; the prose about them is where every round kept finding defects, and
the last round still did. The open items there are decisions, not defects.

## Reviewer participation

_(filled in after the PR is opened)_

## Cost

_(filled in at close)_

## Contract check (Step 9)

_(filled in at close)_

## What have we learned (Step 9)

_(filled in at close)_

## Residue

Six dispositions above defer here (F4, F10, R4-8, R4-10, and the two survivor bounds); this is
that record. Round 10 adds the decisions below, which are not defects and cannot be settled by
another verification round.

**Open, and deliberately not fixed by this plan:**

| Item | Why it is left | Where it should go |
|---|---|---|
| `core-principles.md` lines 48-52 list `allowed-tools` and `model` as optional skill fields, contradicting `frontmatter-standards.md`'s "Skills do not use `model`, `color`, or `tools`/`allowed-tools`" — and two real skills (`automatic-review`, `plan-retrospective`) do declare `allowed-tools` (round 3, F4) | Pre-existing. It became visible only because this branch briefly asserted the field list was closed; that assertion is withdrawn, so the inconsistency reverts to what it was on `main`. Resolving it means deciding which document is right about a field this plan does not touch | A frontmatter-documentation reconciliation, not a target-scoping plan |
| `principles.md` §6 carries a third "adding a target" checklist ("adding target X is **exactly**: 1…3 … **Nothing else**") with no filter obligation (round 3, F10) | The verifier judged it **not false**: the `emits_to` call lands inside its item 2, and "Nothing else" scopes to *other files needing edits*, which stays true | The epic's own reference set, if a later plan widens that checklist |
| The `#optional-fields-2` anchor ordinal in `frontmatter-standards.md` is unguarded — `broken-relative-link` explicitly skips pure-anchor links, so inserting an earlier `### Optional Fields` heading would silently retarget it (round 4, R4-8) | Correct today (headings at 80/149/198). Guarding it means widening a plugin-doctor rule's scope, which is outside this plan | A plugin-doctor rule-scope change |
| The `rule-provenance.md` § "Target-scope rule" lead-in is unguarded prose — the provenance test checks only that a *row* exists (round 4, R4-10) | Same class as the anchor: the guard would be a new doctor capability, not a fix to this change | With R4-8 |
| `rule-provenance.md` line 247's "**Five rules** … NOT in `quality-gate`" stands over an 8-row table whose last three rows are `cmd_quality_gate` (round 5) | **Pre-existing and not branch-introduced** — round 5 confirmed the section is byte-identical to `origin/main` after this plan's row was moved out of it | A provenance-table audit |
| `CLAUDE.md`'s "157 registered components (153 skills…)" has drifted | Pre-existing, already tracked as deferred in another plan's report. The drift is real; this report deliberately states no replacement figure, because `CLAUDE.md` says *registered* — a `plugin.json` count — and the obvious substitute (156 on-disk `SKILL.md` files) measures a different population | Already owned elsewhere |

**Decisions this loop cannot make.** Fifteen rounds can establish whether a claim is true. None of
them has standing to answer these. Three of the five rows here were **resolved by the operator's
decision after round 12** and are kept struck through rather than deleted, because the evidence that
put them on the table is the argument for why the decision was the right one.

| Decision | Status, and the evidence |
|---|---|
| ~~**Should `marketplace/targets/` keep a hand-rolled line parser at all?**~~ | **RESOLVED — it does not.** The evidence that carried it: every behavioural defect across twelve rounds was a divergence between that parser and YAML — round 1's empty-list misfire on `[claude]`, R4-4, R6-03a, 7-04, F8, R9-05, R10-04, R10-05, R10-06, R10-07, R11-01, R11-02, R11-03, R12-01, R12-02, R12-03. Sixteen defects, one root cause, and three successive rules for a single line of YAML indentation semantics |
| ~~**Duplicate `targets:` keys**~~ | **RESOLVED.** YAML specifies it; the build now follows. The "policy the plan does not specify" turned out not to need specifying |
| ~~**Is the loop worth its marginal cost?**~~ | **Answered by use.** Rounds 13, 14 and 15 each found a build-failing false positive on a valid component, in a rule whose whole purpose is to avoid one. The answer for those three rounds was yes |
| **Is `targets:` the right mechanism, versus a per-target ignore manifest?** | **OPEN, and untouched by fifteen rounds.** A manifest puts the policy in one reviewable place instead of distributing it across 160 frontmatter blocks. An architecture question the plan settled by assumption; the delivered mechanism works, which is not the same as its being the better of the two |
| **Should `marketplace/targets/` be inside the quality gate's lint scope?** | **OPEN, and found at round 15.** The gate lints `marketplace/bundles/`, `test/` and `.claude/`; the generator tree is outside it, so a branch-introduced `ruff I001` there passed every check. Widening the scope surfaces pre-existing violations across a tree this plan does not own, which is why it is recorded rather than done |
| **Is failing OPEN the right degradation direction on a read fault?** | **OPEN.** The module argues both sides and picks one (see its Degradation docstring). R6-03a, R10-06, R10-07 and R11-01 were all treated as defects *because* they failed open, and round 13's V13-05 is a fresh instance. The module's own history argues against its own default |
| **Does the `targets-scope-invalid` doctor rule earn its place at all?** | **OPEN, and sharper each round.** The rule is an approximation of a build that reads YAML properly. **Six** distinct soundness root causes have been found in it since the rewrite — four by round 13, a fifth by round 14, a sixth by round 15 that predated both fixes — and each was found by running a corpus through both sides, never by reading. Completeness measures **34.5%** (population: a 22,032-shape safe-prefix corpus) against a build that catches everything. Every one is now fixed and pinned, and the soundness test is derived rather than transcribed so the next one cannot hide the same way. The question is still whether an authoring-time convenience that needed six corrections earns its place beside a build that needs none — and only a human can weigh that |

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
