# Run report — inert-thinking-directives-in-dispatched-docs (run 01)

**Date (UTC):** 2026-08-10    **Branch:** `claude/inert-thinking-directives-smd2a3` (harness-assigned)    **PR:** [#1138](https://github.com/cuioss/plan-marshall/pull/1138)    **Outcome:** completed

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

⛔ **STOP CONDITION fired.** `test/_shared/_dispatch_roster.py` does **not** expose the execution-context workflow roster. It is a generic Markdown-section parser (`section_lines` / `parse_roster`) imported by nine test modules — six under `test/plan-marshall/phase-6-finalize/` (`test_architecture_refresh.py`, `test_dispatch_roster_closure.py`, `test_merge_authorization_roster.py`, `test_pre_submission_self_review_verdict.py`, `test_step_completion_emission.py`, `test_step_termination_contract.py`) and three outside it (`test/plan-marshall/manage-lessons/test_lesson_store_resolution_population.py`, `test/plan-marshall/phase-5-execute/test_execute_phase_markers.py`, `test/plan-marshall/ref-workflow-architecture/test_citations_only_conformance.py`) — and whose own docstring scopes it to `dispatch-inline-split.md`'s `## Dispatched steps` / `## Inline steps` sections — the finalize dispatched-vs-inline **step** roster, an unrelated concept. No existing enumerator (`find_implementors` included — it scans SKILL.md + phase-6/phase-5 docs, not the `workflow/*.md` surface this ext-point lives at) covers the true population.

Per the contract (§ "Rules that outrank convenience" — a claim is not an outcome) and the plan's own "may re-scope the plan" clause, the divergence was escalated to the operator via `AskUserQuestion`. **This run executed in an interactive Claude Code cloud session with the operator reachable** — the escalation was a real main-context `AskUserQuestion` (the main session is not a dispatched leaf, so the leaf "cannot reach the operator" caveat does not apply). The escalation and its answer are a conversation event, not a committed artifact, so they are not independently verifiable from the diff; they are recorded here. The operator chose to **re-scope to a frontmatter-derived population** rather than halt D2/D3 (the autonomous fallback the plan's STOP CONDITION names, which a headless run with no reachable operator would have taken). This is a legitimate *derived* population, not a hand-rolled roster or a grep: the roster is derived from each doc's own `implements: …ext-point-execution-context-workflow` frontmatter (the same declaration the dispatcher resolves against — see `ext-point-execution-context-workflow.md` § Addressing), read via the analyzer's frontmatter parser. Nothing is hand-listed.

- **Roster size: 33** docs (derived population — reported separately).
- **Hit count: 5** pre-fix (3 in `research-best-practices.md`, 2 in `content-review.md`), **0** post-fix.
- The sweep over all 33 population docs confirmed the two D1 files were the **only** offenders — every hit is fixed; none was left with a recorded reason (there were none beyond D1).

### D3 — plugin-doctor rule preventing reintroduction — DONE (commit `917ce75`)

- New analyzer `marketplace/bundles/pm-plugin-development/skills/plugin-doctor/scripts/_analyze_thinking_directive_in_workflow_docs.py` — rule id `thinking-directive-in-workflow-doc`.
- **Population-derived, never hardcoded:** `enumerate_execution_context_workflow_docs()` scans `*/skills/*/{SKILL.md,workflow/*.md}` and keeps docs declaring the ext-point in frontmatter (scalar + block-sequence).
- **Publishes the population size:** every finding carries `details.population_size`; an **empty population** (when the ext-point IS defined in the tree) emits its own finding — so a clean result cannot read as a vacuous pass over an unread population.
- **False-positive boundary:** six high-precision families; procedural sequencing ("step-by-step workflow"), the "careful analysis" review label, and "step-by-step analysis" are deliberately NOT flagged. Verified by a boundary harness (10 positive / 10 negative) and by the negative parametrized tests.
- **Both-direction tests:** `test/pm-plugin-development/plugin-doctor/test_analyze_thinking_directive_in_workflow_docs.py` (46 collected cases across 21 test functions) — positive families, the five removed D1 directives, negatives, population derivation, structural exemptions, population-size publication, the empty-population guard (fires only when the ext-point is defined), finding shape, and real-tree anchors (population ≥ 20, zero findings).
- Wired into the runner (`_runner.py` quality-gate + analyze paths), the descriptor registry (`_rule_registry.py`), the zero-match firing-fixture corpus (`_fixtures.py`), the provenance table (`rule-provenance.md`), and the rule catalog (`rule-catalog.md`).

**Sibling-plan overlap noted (not blocking):** the sibling plan `truthful-signals/050-migration-shims-have-no-expiry` also wants a population-derived plugin-doctor detector and points at the same (mis-identified) `_dispatch_roster.py` "pattern". This run did not co-design with it (050 is not in flight in this session); the overlap is recorded here per the plan's Out-of-scope note. The pattern this run established — derive the population from the ext-point `implements:` frontmatter, publish the size, guard the empty case — is the reusable shape a co-design would adopt.

## Build gate

`git diff --name-only origin/main...HEAD` includes `*.py` (the analyzer + tests + runner/registry/fixtures), so the build gate took its **full path**.

- `./pw quality-gate` — `status: pass`, `total_issues: 0` (32 rules, including the new `analyze_thinking_directive_in_workflow_docs,0`).
- `./pw verify` — `=== verify: SUCCESS ===`, **18711 passed, 14 skipped** (0:06:05), including `test_real_marketplace_quality_gate_has_zero_findings`.

## Findings

**Verification sub-agent (Step 6)** — independent `general-purpose` reviewer, read-only. Verdicts: D1 PASS, D2 PASS (STOP CONDITION correctly handled), D3 PASS. Cold read: **8/8 agreement** between the agent's independent classification and the detector — no false positive on any of the three procedural-prose samples (samples 1 "step-by-step implementation guide", 3 "careful analysis decision framework", 5 "Read phrase in isolation"), all five directives flagged. The false-positive boundary is confirmed correct. Findings raised, each with disposition:

1. **content-review.md:177 rewrite is non-verbatim** (real, low severity, judgment call) — *disposition: accepted, no change.* The plan's "preserve every **surrounding** criteria sentence verbatim" governs sentences around the directive; line 177 had none (heading → single directive sentence → next heading). That sentence fused the reasoning-level directive with a purpose clause; the rewrite ("This framework distinguishes factual descriptions from promotional language.") salvages the criterion while removing the directive. A pure deletion would strand an empty "Decision Framework" subsection, and removing the heading+criterion would drop guidance the plan asks to preserve. The reviewer concluded the rewrite "honors the plan's spirit." No re-dispatch: no fix was applied.
2. **D2 operator-approval unverifiable from committed artifacts** (cannot-verify) — *disposition: accepted, clarified in the D2 section above.* Correct observation from a sub-agent that cannot see the conversation. The re-scope approval was a real interactive `AskUserQuestion` in this main cloud session (operator reachable; main session ≠ dispatched leaf). Recorded as a conversation event.
3. **Run report incomplete** (expected) — *disposition: by design.* Findings / Reviewer participation / Contract check / What-have-we-learned are finalized at the merge gate (Step 8 condition 3), the last pre-merge commit.

No undeclared collateral changes: the reviewer confirmed all 12 changed files are within the plan's expected surface, and `test/_shared/_dispatch_roster.py` was correctly left unmodified.

**CI findings:** None. `./pw verify` was green locally (18718 passed) on the code commit; the PR's `verify / verify` check was confirmed green before arming auto-merge. The one-off `verify / conclusion` cancellations from the per-commit push cadence are superseded runs, not failures.

**PR review findings** (each with disposition):

1. `coderabbitai` — **Continue after an inline-code match** (Minor): `pattern.search` stops at the first match; a later live directive on a line whose first match is an in-code mention was missed. *Fixed* in `de61276` (`finditer` + first-match-outside-inline-code) + mixed-content regression test. Auto-resolved by the bot.
2. `coderabbitai` / `cuioss-review-bot` — **Require directive context for bare-term families** (Major): `ultrathink` / `extended thinking` matched descriptive prose ("Extended thinking is configured by the dispatcher"), not only directives. *Fixed* in `de61276` (directive-cue requirement, clause-bounded window) + descriptive negatives. Auto-resolved. The same defect was raised by `cuioss-review-bot`'s PR Reviewer Guide (inline-code filter framing) — one fix covers both.
3. `coderabbitai` — **Support all Markdown fenced-code delimiters** (Minor): only exactly-three backticks were recognized; `~~~` and 4+ backtick fences were not exempt. *Fixed* in `de61276` (CommonMark fence tracking) + tilde / four-backtick regression tests. Auto-resolved.
4. `coderabbitai` — **Commit the D2 population rescope** (Major, failed to post inline): the plan names `_dispatch_roster.py` and the report used frontmatter derivation. *Rejected with reason (replied on the PR):* the plan's D2 header explicitly permits re-scoping ("this deliverable may re-scope the plan"); the STOP CONDITION's instruction is "halt and report", so the report is the sanctioned deviation record and the plan is the original brief; the frontmatter derivation is a *derived* population (the dispatcher's own addressing mechanism), not the hand-rolled roster / grep the plan forbids; the re-scope IS committed (the enumerator ships). Rewriting the plan's brief would erase the record that a re-scope occurred.

## Reviewer participation

Expected reviewer population **derived from configuration** — the `author_login` of each `marketplace/bundles/plan-marshall/skills/automatic-review/standards/{bot_kind}.md` registry doc:

| Reviewer (`author_login`) | Verdict | Body evidence / reason |
|---|---|---|
| `cuioss-review-bot` | `reviewed` | Posted the "PR Reviewer Guide" issue-comment carrying a finding (the inline-code filter) against the diff. |
| `coderabbitai` | `reviewed` | Posted a full review with three actionable inline findings + walkthrough on the first commit; the findings were addressed and the bot auto-resolved all three threads ("✅ Addressed in commit de61276"). Its re-review of the fix commit was subsequently rate-limited (33-min window), but the substantive review of the diff was complete. |
| `sourcery-ai` | `rate-limited` | Published only a quota notice — "you have reached your weekly rate limit of 500000 diff characters" — in place of a review. |

**Coverage: 2 of 3.** Step 8 shortfall disclosure fired: `sourcery-ai` is rate-limited (weekly diff-char quota, outside our control) and did not review this diff; `coderabbitai`'s re-review of the fix commit is rate-limited but its original review of the diff completed and its findings were resolved. Per the contract this is a disclosure, not a block — rate limits do not hold the merge.

## Cost

- **Tokens:** not available to the agent in this session.
- **Wall-clock:** single interactive session; the two `./pw verify` runs were 6m05s and 4m48s. No precise session start/end timestamp is available to the agent.
- **Population:** this single Claude Code cloud session's usage. ⛔ NOT comparable to a plan-marshall `metrics.toon` total (that counts the orchestrator-plus-agent dispatch tree under plan-marshall's per-task billing boundary, which a single interactive cloud session does not share).

## Contract check (Step 9)

| Step | Verdict | Evidence |
|---|---|---|
| 1 Skills loaded | done | Named in § Skills loaded (read from bundle paths). |
| 2 Branch | done | Harness-assigned `claude/inert-thinking-directives-smd2a3`, kept as-is, on `origin`. |
| 3 Plan directory | done | `doc/plans/truthful-signals/040-inert-thinking-directives-in-dispatched-docs/plan.md` exists and opens with the first-instruction block (present, not repaired). |
| 4 Implement | done | Commits `917ce75` (D1+D3), `de61276` (review fixes) carry the `Co-Authored-By: Claude` trailer; deliverables addressed. |
| 4 Per-commit gate | done | `917ce75` preceded by a `total_issues: 0` quality-gate log; `de61276` preceded by a green `./pw verify` (quality-gate + tests). |
| 4 Pushed | done | No unpushed commit remains (the report commit is the final push). |
| 5 Build gate | done | Python changed → full path. `./pw verify` green twice (18711, then 18718 passed). |
| 6 Verification sub-agent | done | Findings + dispositions in § Findings; cold read 8/8. |
| 7 PR cycle | done | PR #1138; every comment fixed-or-answered (§ Findings). |
| 8 Merge gate | confirmed at merge | Checks read green via the PR check API before arming auto-merge; merge state read back (`state: MERGED`), merge commit reported to the operator. |
| 8 Bridge | done | Nothing under `doc/plans/` outside this plan's own directory changed; report carries PR number + per-deliverable outcome. |
| 9 This check | done | This table. |
| 9 What have we learned | done | Below. |

GitHub access path used: **GitHub MCP server** (the cloud path). Branch form: **harness-assigned** `claude/*`. The plan edited `marketplace/bundles/` (D1 docs + D3 detector), but **no `/sync-plugin-cache` is owed by this run — it is neither necessary nor possible in the cloud lane.** *Not possible:* the lane cannot touch `target/` (git-ignored build output) or `~/.claude/` (the plugin cache). *Not necessary:* the merged `marketplace/bundles/` source is authoritative; any plugin-cache refresh is a local-developer-machine concern, not a debt this cloud run creates.

## What have we learned (Step 9)

> **Mitigated by plan `450-cloud-lane-assumes-local-runtime-affordances`.** Both cloud-plan-lane items
> raised in this run are closed by that plan: the operator-escalation-vs-autonomous-fallback question
> (immediately below) by **D4** (a reachable operator MAY escalate via `AskUserQuestion`; a headless run
> takes the plan's autonomous fallback), and the build-gate misframing (§ "Build-gate error — I treated a
> markdown-only change as build-gated" below) by **D5a** (the build gate now triggers on `*.py` only,
> with the merge queue's `merge_group` run named as the docs-only net). The `_dispatch_roster.py`
> plan-authoring note is not a cloud-plan-lane change and is unaffected.

**Proposed contract clarification (presented to the operator; not self-approved, not shipped in this PR):** the cloud-plan-lane is written for autonomous execution, but this run executed in an interactive main session with a reachable operator, and a D2 STOP CONDITION offered a re-scope. The contract is silent on whether the main session may escalate to the operator (via `AskUserQuestion`) versus always taking the plan's autonomous fallback. This run escalated; a headless run of the same plan would have halted D2 and shipped D1 only — so the identical plan yields different outcomes depending on operator reachability. **Evidence:** the D2 escalation in this run. **Proposed edit:** a sentence in `cloud-plan-lane` § "Rules that outrank convenience" (or § Step-with-STOP-CONDITION guidance) stating that when the main session has a reachable operator and a plan offers a re-scope, the run MAY escalate via `AskUserQuestion`; a headless run takes the plan's stated autonomous fallback. If the operator accepts, ship as a separate `chore/` PR touching only the skill. If declined, the current behavior (judgment call by the run) stands.

A second, non-contract observation for the orchestrator/plan-author (not a cloud-plan-lane change): both this plan and the sibling `050-migration-shims-have-no-expiry` name `test/_shared/_dispatch_roster.py` as the population source / pattern for a population-derived detector, but that file is a finalize dispatched-vs-inline **step** parser — the wrong mechanism. Plan-authoring for population-derived detectors should point at the ext-point `implements:` frontmatter derivation (or `extension_discovery.find_implementors` where the surface matches), not `_dispatch_roster.py`.

### Build-gate error — I treated a markdown-only change as build-gated (operator-flagged)

**What went wrong.** During the follow-up contract PR (#1145, a `.claude/skills/**` markdown-only change) I ran `./pw quality-gate` and described it as "the per-commit gate," treating the markdown change as build-gated. That is wrong: **the build triggers only on buildable source (`*.py`).** `.github/workflows/python-verify.yml` opts into `skip-on-docs-only: true`, and its reusable workflow skips the build+tests whenever every changed path is non-building (docs/config); markdown under `.claude/skills/**` and `marketplace/bundles/**` is docs, so a markdown-only change does not build. The quality-gate run passed and did no harm, but the framing mis-stated the gating rule.

**Root cause.** I applied the cloud-plan-lane build-gate predicate verbatim — Step 4's per-commit gate and Step 5's table both list `.claude/skills/**` and `marketplace/bundles/**` as `./pw quality-gate` triggers — without reconciling it against `python-verify.yml`'s py-only `skip-on-docs-only` behaviour. The contract's markdown-triggering rows are broader than the actual CI gate; the accurate rule is that the build runs only for `*.py` changes. The plan-040 commits themselves were unaffected — every gated commit there carried `*.py`, so its quality-gate/verify runs were correct — the error was confined to the markdown-only follow-up.

**Durable fix.** The contract's build-gate predicate should be narrowed to `*.py` (dropping the `.claude/skills/**` / `marketplace/bundles/**` rows, or demoting them to an explicitly-optional local lint that is not called a build gate). That is a `cloud-plan-lane` change and is offered to the operator separately, not made here.

## Residue

- The plan (and its sibling 050) name `test/_shared/_dispatch_roster.py` as the population source for a population-derived detector; that file is the wrong mechanism. A contract/plan-authoring note may be worth proposing (see Step 9). No `/sync-plugin-cache` is owed by this run: it is neither necessary nor possible in the cloud lane (see the Contract-check note above).
