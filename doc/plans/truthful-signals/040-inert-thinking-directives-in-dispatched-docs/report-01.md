# Run report — inert-thinking-directives-in-dispatched-docs (run 01)

**Date (UTC):** 2026-08-10    **Branch:** `claude/inert-thinking-directives-smd2a3` (harness-assigned)    **PR:** _pending_    **Outcome:** _in progress_

## Skills loaded

- `cloud-plan-lane` (first action, via `Skill:`) — the working contract.
- `plan-marshall:ref-code-quality` — read from bundle path.
- `pm-plugin-development:plugin-script-architecture` — read from bundle path.
- `plan-marshall:ref-workflow-architecture` — workflow-docs / dispatch-topology surface.
- `pm-dev-python:python-core` — Python production code (D3).
- `pm-dev-python:pytest-testing` — Python tests (D3).

All loaded by `Read`-ing the bundle `SKILL.md` path (the plugin was not assumed installed). No skill was unobtainable.

## Deliverables

### D1 — Fix the confirmed instances — DONE (commit `917ce75`)

- `marketplace/bundles/plan-marshall/skills/plan-marshall/workflow/research-best-practices.md` — removed the three `ultrathink` directives (former `:9`, `:46`, `:112`), each a standalone paragraph. All surrounding criteria (search strategy, dedup rules, workflow steps) preserved verbatim.
- `marketplace/bundles/pm-documents/skills/ref-documentation/workflow/content-review.md` — removed the restatement (former `:7`, second sentence only — the framework-purpose sentence before it is preserved) and rewrote the CoT scaffold (former `:177`, `**CRITICAL:** Use careful step-by-step reasoning…`) to `This framework distinguishes factual descriptions from promotional language.`, preserving the section's stated purpose while dropping the reasoning-level directive.
- All five claim-label strings were confirmed by string before editing (the `content-review.md` HYPOTHESIS at `:7`/`:177` was verified present, not assumed).

*Verification state:* covered by the D3 detector's positive mutation-guard tests (`test_removed_d1_directives_fire`), which fire on the exact removed prose; and by the whole-tree sweep (0 residual hits).

### D2 — GATE: derive the dispatch roster, then sweep it — DONE, WITH A REPORTED RE-SCOPE

⛔ **STOP CONDITION fired.** `test/_shared/_dispatch_roster.py` does **not** expose the execution-context workflow roster. It is a generic Markdown-section parser (`section_lines` / `parse_roster`) whose sole consumers are the phase-6-finalize tests, and whose own docstring scopes it to `dispatch-inline-split.md`'s `## Dispatched steps` / `## Inline steps` sections — the finalize dispatched-vs-inline **step** roster, an unrelated concept. No existing enumerator (`find_implementors` included — it scans SKILL.md + phase-6/phase-5 docs, not the `workflow/*.md` surface this ext-point lives at) covers the true population.

Per the contract (§ "Rules that outrank convenience" — a claim is not an outcome) and the plan's own "may re-scope the plan" clause, the divergence was escalated to the operator via `AskUserQuestion`. The operator chose to **re-scope to a frontmatter-derived population** rather than halt D2/D3. This is a legitimate *derived* population, not a hand-rolled roster or a grep: the roster is derived from each doc's own `implements: …ext-point-execution-context-workflow` frontmatter (the same declaration the dispatcher resolves against — see `ext-point-execution-context-workflow.md` § Addressing), read via the analyzer's frontmatter parser. Nothing is hand-listed.

- **Roster size: 33** docs (derived population — reported separately).
- **Hit count: 5** pre-fix (3 in `research-best-practices.md`, 2 in `content-review.md`), **0** post-fix.
- The sweep over all 33 population docs confirmed the two D1 files were the **only** offenders — every hit is fixed; none was left with a recorded reason (there were none beyond D1).

### D3 — plugin-doctor rule preventing reintroduction — DONE (commit `917ce75`)

- New analyzer `marketplace/bundles/pm-plugin-development/skills/plugin-doctor/scripts/_analyze_thinking_directive_in_workflow_docs.py` — rule id `thinking-directive-in-workflow-doc`.
- **Population-derived, never hardcoded:** `enumerate_execution_context_workflow_docs()` scans `*/skills/*/{SKILL.md,workflow/*.md}` and keeps docs declaring the ext-point in frontmatter (scalar + block-sequence).
- **Publishes the population size:** every finding carries `details.population_size`; an **empty population** (when the ext-point IS defined in the tree) emits its own finding — so a clean result cannot read as a vacuous pass over an unread population.
- **False-positive boundary:** six high-precision families; procedural sequencing ("step-by-step workflow"), the "careful analysis" review label, and "step-by-step analysis" are deliberately NOT flagged. Verified by a boundary harness (10 positive / 10 negative) and by the negative parametrized tests.
- **Both-direction tests:** `test/pm-plugin-development/plugin-doctor/test_analyze_thinking_directive_in_workflow_docs.py` (39 tests) — positive families, the five removed D1 directives, negatives, population derivation, structural exemptions, population-size publication, the empty-population guard (fires only when the ext-point is defined), finding shape, and real-tree anchors (population ≥ 20, zero findings).
- Wired into the runner (`_runner.py` quality-gate + analyze paths), the descriptor registry (`_rule_registry.py`), the zero-match firing-fixture corpus (`_fixtures.py`), the provenance table (`rule-provenance.md`), and the rule catalog (`rule-catalog.md`).

**Sibling-plan overlap noted (not blocking):** the sibling plan `truthful-signals/050-migration-shims-have-no-expiry` also wants a population-derived plugin-doctor detector and points at the same (mis-identified) `_dispatch_roster.py` "pattern". This run did not co-design with it (050 is not in flight in this session); the overlap is recorded here per the plan's Out-of-scope note. The pattern this run established — derive the population from the ext-point `implements:` frontmatter, publish the size, guard the empty case — is the reusable shape a co-design would adopt.

## Build gate

`git diff --name-only origin/main...HEAD` includes `*.py` (the analyzer + tests + runner/registry/fixtures), so the build gate took its **full path**.

- `./pw quality-gate` — `status: pass`, `total_issues: 0` (32 rules, including the new `analyze_thinking_directive_in_workflow_docs,0`).
- `./pw verify` — `=== verify: SUCCESS ===`, **18711 passed, 14 skipped** (0:06:05), including `test_real_marketplace_quality_gate_has_zero_findings`.

## Findings

_Verification sub-agent (Step 6) findings and dispositions — pending finalization at the merge gate._

## Reviewer participation

_Pending — filled after the PR review cycle._

## Cost

- **Tokens:** not available to the agent in this session.
- **Wall-clock:** run start ~ session open; `./pw verify` alone was 6m05s. Full run wall-clock recorded at finalization.
- **Population:** this single Claude Code cloud session's usage. ⛔ NOT comparable to a plan-marshall `metrics.toon` total (that counts the orchestrator-plus-agent dispatch tree under plan-marshall's per-task billing boundary, which a single interactive cloud session does not share).

## Contract check (Step 9)

_Pending — filled at the merge gate as the last pre-merge commit._

## What have we learned (Step 9)

_Pending — filled at the merge gate._

## Residue

- The plan (and its sibling 050) name `test/_shared/_dispatch_roster.py` as the population source for a population-derived detector; that file is the wrong mechanism. A contract/plan-authoring note may be worth proposing (see Step 9). The bundle edits under `marketplace/bundles/` mean a local `/sync-plugin-cache` is owed by whoever picks the work up on a developer machine (this lane cannot sync — `target/` and `~/.claude/` are out of reach).
