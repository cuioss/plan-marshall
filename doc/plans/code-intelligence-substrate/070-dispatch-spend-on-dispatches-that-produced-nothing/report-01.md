# Run report — 070-dispatch-spend-on-dispatches-that-produced-nothing (run 01)

**Date (UTC):** 2026-08-12    **Branch:** `claude/dispatch-spend-empty-ds4y39` (harness-assigned)    **PR:** [#1180](https://github.com/cuioss/plan-marshall/pull/1180)    **Outcome:** completed

## Skills loaded

- `cloud-plan-lane` — the working contract (first action, before reading the plan).
- `plan-marshall:ref-code-quality` — always-load (read from bundle path).
- `pm-plugin-development:plugin-script-architecture` — always-load (read from bundle path).
- `plan-marshall:persona-implementer` — production-code work identity.
- `pm-dev-python:python-core` — Python production code.
- `pm-dev-python:pytest-testing` — Python tests.

All obtained by reading the bundle-path `SKILL.md` files (the `plan-marshall` plugin is not installed in this cloud session, so `Skill:` notation loads were not used). No skill was unreachable.

## Deliverables

The plan's founding proxy (`error` == "produced nothing") is REFUTED by the plan itself. The work fixes the proxy first (D1), settles the token-column gate (D2), and reports the terminal-error dispatch spend distinctly from the retryable spend (D4/D5). The terminal-error figure is the strongest *proxy* for genuinely-wasted spend once productive loop-backs are stamped separately — but the finding-yield proof that those `error` rows produced nothing is D3's corpus-gated measurement, which is blocked in a fresh clone (as are D4's class shares).

### D1 — GATE: taxonomy member for a productive non-completion + widen the audit rule — **DONE**

Confirmed in the clone before changing anything: `DISPATCH_TERMINATION_CAUSES` had no member for a findings-bearing return (settling the refutation claim without the machine-local record — the mis-stamping is structural), and the step-completion surface already carries a `loop_back` outcome + `loop_back_target` classifier while the dispatch ledger had no counterpart.

- Added `returned_with_findings` to `DISPATCH_TERMINATION_CAUSES` (`manage-metrics.py`), the dispatch-ledger counterpart of the step-completion `loop_back` outcome.
- Routed the finalize 5c classification (`phase-6-finalize/SKILL.md`) so a dispatched step whose `mark-step-done` recorded `outcome: loop_back` is stamped `returned_with_findings`, **never** `error`. The classification is now five causes, not four.
- Widened the `DISPATCH_TERMINATION_CAUSE` audit rule (`logging-gap-analysis.md`): its Inputs and precondition covered only `metrics-dispatch-boundaries-5-execute.toon`; they now cover every dispatching phase incl. `6-finalize`. (The programmatic reader `read_dispatch_boundaries_per_phase` in `analyze-logs.py` already globbed all phases — lesson `2026-05-20-12-002`; the *rule doc* was the stale half, and is what the plan's "read by no rule at all" was pointing at.)
- All enum-mirror sites moved in lock-step: `manage-metrics/SKILL.md` (2 brace-forms + bullet), `data-format.md` enum line, `logging-gap-analysis.md` `the accepted causes:` set, and the argparse `description=` string. The existing contract tests (`test_every_documented_termination_cause_site_matches_the_enum`, `test_logging_gap_analysis_termination_cause_set_matches_the_enum`, `test_data_format_termination_cause_enum_matches_the_enum`) and the plugin-doctor `canonical-enum-choices-drift` rule enforce the sync.

Tests that fail before the change: `test_enum_contains_returned_with_findings_cause`, `test_returned_with_findings_recorded_on_the_finalize_boundary` (stamps the new member on the finalize boundary file), `test_analyze_logs_surfaces_the_finalize_boundary_file` (the audit reader reads the finalize file and counts the new cause), `test_logging_gap_analysis_rule_scope_names_the_finalize_boundary_file` (the rule doc widening). Commit `0499cc7`.

### D2 — GATE: the four per-dispatch token columns — **SETTLED (already satisfied by prior work)**

The plan frames D2 as binary (populate or drop) on the belief that the columns "persist as though measured" (write `0` for an omitted flag). **That premise is REFUTED in the current clone.** A prior change (the `unmeasured`-token infrastructure, `UNMEASURED_COLUMN_TOKEN`) already ships a superior third path: an omitted flag writes the literal `unmeasured`, never `0`; a *measured* `0` stays `0`; and readers implement a three-way (measured / unmeasured / unrecognised) read. The measured-vs-unproduced distinction is therefore representable on disk **and comprehensively tested** — `test_record_model_representability.py` pins it in the writer and in BOTH readers (the retrospective reader and the `.claude` audit ledger reader), including the exact negative control the plan's Verification section demands (a measured `0` and an unproduced column are distinguishable).

Producer-absence established first-party (the plan flags this as the higher-burden asserted absence): a repository sweep for `--input-tokens`/`--output-tokens`/`--cache-read-input-tokens`/`--cache-creation-input-tokens` finds them only in the writer's argparse definition, the schema doc, and the SKILL.md — **no** workflow doc or caller (`execution.md`, `planning-outline.md`, `phase-6-finalize/SKILL.md`) forwards them. So the columns are honestly `unmeasured` at every call site, which is the correct representation, not a manufactured zero. D2's gate is met: nothing reads a manufactured zero, and D5 reads `total_tokens` (column 3, produced), not these columns. **No code change was warranted; re-implementing would have shipped a second writer for one taxonomy, which the plan forbids.**

### D3 — re-derive the non-productive population, first-party — **BLOCKED on corpus availability**

D3 mutates nothing; it is a measurement over a corpus of archived run records. That corpus lives under the machine-local, git-ignored `.plan/` tree and is **not present in a fresh cloud clone** (per `CLAUDE.md` and the `cloud-plan-lane` skill). The plan explicitly instructs: "If no population of archived records is reachable here, HALT D3/D4's measurement and report them blocked on corpus availability" and "⛔ Do not search for it." No corpus was reachable; **the measurement is halted and reported blocked.** No share figure was computed or fabricated, and the retired "a third of finalize dispatch spend" figure is not quoted anywhere. Per the plan, a halt with a clear statement of what was unreachable is the D3 deliverable met, not a failure.

### D4 — separate RETRYABLE from TERMINAL — **code DONE; class shares BLOCKED on corpus**

Code half: the reader (`_parse_dispatch_boundary_file`) now reports `retryable_total_tokens` (`blocked_session_restart` + `harness_cancellation` — infrastructure a re-run recovers) **distinctly** from `error_total_tokens` (genuine terminal failure that may be deterministic). They are never summed into one "failure" figure; a test (`test_retryable_total_tokens_reported_distinctly_from_error`) asserts they stay distinct. The named cause-classes are module constants (`_RETRYABLE_CAUSES`, `_TERMINAL_WASTE_CAUSES`). Measurement half (the class shares over archived records): blocked on the same corpus gate as D3.

### D5 — make the waste a reported figure — **DONE**

The terminal-error dispatch spend is emitted as its own field, `error_total_tokens` — the sum of `total_tokens` over `error` rows. After D1, findings-bearing loop-backs are stamped `returned_with_findings`, so what remains under `error` is the terminal-error population, which is the strongest **proxy** for genuinely-wasted spend now that the productive loop-backs are pulled out. It is a proxy, not a proof: whether an `error` dispatch produced nothing is a finding-yield question, and confirming it against archived records is D3's corpus-gated measurement — the field asserts only "terminal-error spend", not "proven waste". The field is surfaced in the `dispatch_boundaries` fragment and rendered in the compile-report "Phase Dispatch Boundaries" table (`error_total_tokens (terminal-error)` column), so a reader sees it without reconstructing it. Covered by `test_error_total_tokens_sums_only_terminal_error_rows` and the compile-report render tests. The productive population it must be told apart from is counted as `returned_with_findings_count`. (This precision — proxy vs proof — was tightened in response to a CodeRabbit review comment; see Findings.)

**Owning-module resolution (Expected surface was a HYPOTHESIS).** The plan hypothesised D5's field in `manage-metrics`. It is placed instead in `plan-retrospective`'s dispatch-boundary reader + compile-report, because (a) that reader is where termination causes are already interpreted per-cause (`unknown_count`, `clean_exit_queue_empty_count`), (b) the compile-report "Phase Dispatch Boundaries" section is where a human reader actually sees per-phase dispatch data, and (c) it avoids the `manage-metrics` per-phase token-field **lattice** contract, which would force a lattice row and reconciliation coupling for a figure that is a per-cause interpretation, not a dispatched-population measure. The taxonomy member itself (D1) is in `manage-metrics` as hypothesised.

## Build gate

`git diff --name-only origin/main...HEAD -- '*.py'` is non-empty (`manage-metrics.py`, `analyze-logs.py`, `compile-report.py`, and four test files), so the Python gate ran. `./pw verify plan-marshall` → **SUCCESS**: 16077 passed, 1 skipped; quality-gate (ruff / mypy(production 277) / mypy(test 571) / SPDX / plugin-doctor marketplace-wide) all clean; module-tests(plan-marshall) green. Scoped to the `plan-marshall` bundle because the entire diff is within it (sanctioned by the lane contract's "append a bundle name" note); the merge queue runs the full cross-bundle verify.

## Findings

**Pre-PR verification sub-agent (Step 6)** — independent `general-purpose` agent, verified against the plan's requirements with a beyond-the-diff sweep of the owning bundles.

- Verdicts: **D1 VERIFIED** (member added; finalize 5c routes `loop_back → returned_with_findings`, `failed` stays `error`; audit-rule doc widened; all enum-mirror sites in sync; RED-before tests present). **D2 VERIFIED** — both claims independently confirmed: the measured-`0`-vs-`unmeasured` distinction is implemented and tested in the writer and both readers, and **no producer** forwards the context-load flags (only the writer's argparse, the schema doc, and the SKILL.md mention them). **D3 VERIFIED as correctly ships-nothing** — no measurement/sweep code, no fabricated share, the retired figure appears only inside `plan.md` labelled RETIRED. **D4 VERIFIED** — `error_total_tokens` and `retryable_total_tokens` are separate sums, never folded. **D5 VERIFIED** — `error_total_tokens` emitted, tested (RED-before), and rendered in the compile-report table.
- Finding 1 (source: sub-agent beyond-the-diff sweep; low severity): `analyze-logs.py` `read_dispatch_boundaries_per_phase` docstring enumerated the per-file shape with only the old four keys — stale after three keys were added. **Disposition: fixed** (commit `d55d3c6`) — replaced the enumeration with a reference to `_parse_dispatch_boundary_file`'s authoritative shape.
- Finding 2 (source: same; low severity): `compile-report.py` `_dispatch_boundaries_has_present_phase` docstring had the same incomplete enumeration. **Disposition: fixed** (commit `d55d3c6`) — same reference-based fix.
- Re-dispatch after the fix: **RESOLVED** — both fixed, no new staleness, bundle sweep clean (every remaining per-file-shape enumeration is either the authoritative full seven-key list or the complete seven-column table).

**CI findings:** none. On head `dc8e352` the required `verify / conclusion` check concluded **success**; `verify / verify`, `verify / gate`, `review / review`, `dependency-review`, and `generate-check` all success; `Sourcery review` and `auto-merge` skipped. `mergeStateStatus` reported `clean`.

**PR review findings (CodeRabbit — 6 actionable + 1 inline).** Each dispositioned:

| # | Finding | Disposition |
|---|---|---|
| CR-1 | Run report has placeholder sections while `Outcome: completed` (inline, `report-01.md`) | **Fixed** — all sections finalized in this commit before the merge gate. |
| CR-2 | Guard every full termination-cause mirror; the argparse `description` is unguarded | **Fixed** — made the argparse `description` **derived** from `DISPATCH_TERMINATION_CAUSES` (eliminates the mirror, matching `choices=`); the SKILL.md mirror-note updated. The `data-format.md` enum and `logging-gap-analysis.md` accepted-causes set were already guarded by structural-equality tests (`test_data_format_termination_cause_enum_matches_the_enum`, `test_logging_gap_analysis_termination_cause_set_matches_the_enum`) — noted in the reply. |
| CR-3 | Add an executable "unavailable-skill" guard for the cloud-plan-lane | **Rejected** — misreads the lane architecture: the lane is executed by the agent, not a runner/loader; the skill-load-failure handling is the agent stopping and reporting blocked (the plan's first-instruction block). There is no entrypoint code to add a guard to, and this PR does not redesign the lane. |
| CR-4 | Plan D1 wording "read by no rule at all" is imprecise (the reader already globs all phases) | **Acknowledged, no plan-text edit** — the plan's own claim-labels mark that clause a **HYPOTHESIS** ("Read the rule's scope in the clone before widening it"); the implementation and this report already state the precise mechanism (the reader globbed all phases; the rule **doc** was the stale half). Editing the historical plan text would rewrite what was planned; the report carries the correction. |
| CR-5 | Add an integration test that drives `mark-step-done --outcome loop_back` through the finalize classification, not only the writer | **Rejected (architectural)** — the `loop_back → returned_with_findings` classification lives entirely in `phase-6-finalize/SKILL.md` prose executed by the dispatcher LLM (as does every finalize cause); there is no code seam to drive end-to-end. The test asserts the strongest available proxy (writer-acceptance on the finalize file + the doc classification table). The independent verification sub-agent reached the same conclusion. |
| CR-6 | Plan D2's binary (populate/drop) omits the shipped `unmeasured` third state | **Acknowledged, no plan-text edit** — same reasoning as CR-4: the report documents D2 settled via the third (`unmeasured`) path, which the plan's own "resolve the owning module at outline" guidance sanctions. The plan's binary was a lead, correctly superseded at implementation. |
| CR-7 | Keep structural taxonomy evidence separate from corpus-derived waste; qualify `error_total_tokens` as terminal-error spend until finding-yield proves waste | **Fixed** — softened the field's docstring/comment, the rendered column label (`error_total_tokens (terminal-error)`), and the report so the figure asserts "terminal-error spend" (the strongest proxy for genuinely-wasted post-D1), with the finding-yield proof explicitly deferred to the corpus-gated D3. |

Two findings rejected, with reasons above (CR-3, CR-5). Nothing deferred.

## Reviewer participation

Expected population derived from the registry docs (`marketplace/bundles/plan-marshall/skills/automatic-review/standards/{bot_kind}.md` `author_login`): `cuioss-review-bot` (pr-agent.md), `coderabbitai` (coderabbit.md), `sourcery-ai` (sourcery.md). Verdicts read from the stored comment/review bodies, not from check states:

| Reviewer (`author_login`) | Verdict | Body evidence / reason |
|---|---|---|
| `coderabbitai` | `reviewed` | Full review over the diff: a walkthrough issue-comment + a review with 6 actionable findings and an inline review thread on `report-01.md`. |
| `cuioss-review-bot` | `reviewed` | Posted a "PR Reviewer Guide 🔍" issue-comment over the diff: "PR contains tests / No security concerns identified / No major issues detected." An explicit nothing-major verdict on this diff. |
| `sourcery-ai` | `rate-limited` | Published only a refusal notice in place of a review: "you have reached your weekly rate limit of 500000 diff characters." Its check-run concluded `skipped`. It engaged but did not review this diff. |

**Coverage: 2 of 3 reviewed.** The Step-8 shortfall disclosure fired: `sourcery-ai` is rate-limited (weekly quota) — a routine, out-of-our-control shortfall, disclosed and NOT blocked on. The two reviews that landed were fully dispositioned (see Findings).

## Cost

- **Tokens:** not available to the agent in this session (a Claude Code cloud session does not expose its own token accounting to the running agent).
- **Wall-clock:** single interactive cloud session; `./pw verify plan-marshall` alone was ~6m36s.
- **Population:** this single Claude Code cloud session's usage. ⛔ NOT comparable to a plan-marshall `metrics.toon` total — that counts the orchestrator-plus-agent dispatch tree under plan-marshall's own per-task billing boundary, which a single interactive cloud session does not share. The figures cannot be made comparable, so none is presented as if it were.

## Contract check (Step 9)

| Step | Verdict | Artifact |
|---|---|---|
| 1 Skills loaded | done | Named in § Skills loaded; all via bundle path. |
| 2 Branch | done | `claude/dispatch-spend-empty-ds4y39` (harness-assigned, kept as-is) exists on `origin`; pushed before the first edit. |
| 3 Plan directory | done | `…/070-…/plan.md` exists and opens with the first-instruction block (present on arrival; not repaired). |
| 4 Implement | done | Commits carry the `Co-Authored-By: Claude` trailer; all deliverables addressed. |
| 4 Per-commit gate | done | Every `*.py`-touching commit was preceded by a clean `./pw quality-gate` (ruff/mypy/SPDX/plugin-doctor). |
| 4 Pushed | done | No unpushed commit remains at each stage. |
| 5 Build gate | done | `git diff --name-only origin/main...HEAD -- '*.py'` non-empty → `./pw verify plan-marshall` SUCCESS (16077 passed, 1 skipped). |
| 6 Verification sub-agent | done | Findings + dispositions in § Findings; two docstring findings fixed, re-dispatch RESOLVED. |
| 7 PR cycle | done | PR #1180; both comment surfaces read (issue comments, review summary bodies, inline threads); every comment dispositioned in § Findings. |
| 8 Merge gate | done | Conditions 1–3 met (required check green on head; all comments handled; report finalized + pushed as the last pre-merge commit); shortfall disclosed (2-of-3, sourcery rate-limited); auto-merge armed. |
| 8 Bridge | done | No status/bookkeeping write landed under `doc/plans/` outside this plan's own directory. The report carries the PR number and per-deliverable outcome. |
| 9 This check | done | This table. |
| 9 What have we learned | done | Proposal below. |

GitHub access path: the **GitHub MCP server** (cloud path). Branch form: **harness-assigned** `claude/…`. A cloud run owes no `/sync-plugin-cache` (machine-local build step). Self-wake note: the `claude-code-remote` `subscribe_pr_activity` tool was **not available** in this session; the review cycle was driven by the non-gated read surface (`pull_request_read`) per the lane's manual-read-polling path, and CI/reviews had already concluded by first poll.

## What have we learned (Step 9)

**Proposed contract change (evidence from this run): name the review-summary-bodies MCP call in the gh↔MCP mapping.** The lane's § Cloud-session-affordances mapping table maps the *conversation* surface to `gh pr view {N} --comments` and the *inline review-thread* surface to the paginated review-comments call — but it does **not** name an MCP call for **review summary bodies**, even though the prose surface table lists "review summary bodies" under Conversation. In this run, the principal automated-reviewer findings (CodeRabbit's 6 actionable comments) arrived in the **review summary body**, reachable only via `pull_request_read method: get_reviews` — *not* as issue comments (`get_comments`) and *not* as inline threads (`get_review_comments`, which returned only one thread). A run that read only the two surfaces the mapping names by MCP call would have silently missed six findings — the exact false-clean-signal the lane exists to prevent. **Proposed edit:** add a mapping row `gh pr view {N} --json reviews` (review summary bodies) → `pull_request_read` `method: get_reviews`, and state that all three read methods (`get_comments`, `get_reviews`, `get_review_comments`) must be called before the merge gate. Per Step 9 this is **presented to the operator for approval and, if approved, shipped as a separate `chore/` PR** touching only the skill — it is not self-approved and not included in this plan's PR.

No other contract change is proposed. Every other step's artifact was producible as written, and the one deviation encountered (the self-wake tool being unavailable rather than merely approval-gated) was already fully covered by the lane's read-polling / arm-and-hand-off fallbacks — no gap.

## Residue

- **D3 measurement** and **D4's class shares** remain unmeasured, blocked on the archived-records corpus that a fresh clone does not carry. When run where the corpus is present (a local machine with `.plan/local/archived-plans/`), the sweep should: derive the terminal-state vocabulary from the schema (not the two observed names), re-derive against finding-yield (a `returned_with_findings` dispatch is the opposite of the target), report the count + token cost + population size, and compute any share only against a settled denominator (the sibling coverage-ratio plan is the blocker for share figures).
