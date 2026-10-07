# Run report — 030-a-workflow-doc-prescribes-a-flag-no-script-declares (run 01)

**Date (UTC):** 2026-08-11    **Branch:** claude/workflow-flag-script-mismatch-q42lik (harness-assigned, kept as-is)    **PR:** [#1157](https://github.com/cuioss/plan-marshall/pull/1157)    **Outcome:** completed — merge armed / landing delegated (cloud arm-and-hand-off)

## Skills loaded

- `cloud-plan-lane` (first action)
- `plan-marshall:ref-code-quality` + `standards/error-handling.md` (the § "Fail-Closed Classification" rules (b)/(c)/(e) this plan's D0/D1 implement) — read from bundle path
- `pm-plugin-development:plugin-script-architecture` + `standards/output-contract.md` (exit-code convention: exit 2 = argparse rejection) — read from bundle path

GitHub access path: **GitHub MCP server** (cloud). Branch form: **harness-assigned** `claude/…`, kept as-is. A cloud run owes no `/sync-plugin-cache`.

## Re-grounding against merged main (the plan is a repair of a shipped fix)

Every line reference was re-read against merged `main`. The current tree is already past the symptom-era version — the exact symptom strings (`"Pre-merge comment barrier: clean …"`, `participated_bots=none`) do not exist; the tree IS the "prior shipped remedy" the plan hypothesises about. Consequences:

- **The barrier is PROSE** in `phase-6-finalize/standards/branch-cleanup.md` § "Pre-Merge Review-Completeness Barrier", executed by the **inline** orchestrator. No code fails the step on a non-zero exit. Its UNKNOWN-verdict guards for the three participation calls (`fetch_findings`, `ci checks pull-request-runs`, `review_completeness check`) are present-but-ineffective (prose the agent must obey).
- The plan's HYPOTHESIS "guard wired to review_completeness but not its siblings": at the **barrier** the guard covers all three (present-but-ineffective → this is a *repair of a shipped fix*, per the plan's discriminating question). At the **automatic-review FIND step**, the `github_pr fetch_findings` producer had **no** exit-code guard (the `manage-*`-scoped convention excluded it) — the genuine gap D0 closes.

### NULL results (re-derived; reported rather than padded, per the Claim-labels guidance)

| Plan target | Finding | Action |
|---|---|---|
| `--enabled-bots` prescribed in a doc | **Absent from the whole tree** (grep: 0 hits in `marketplace/bundles/`). Producer declares `--required-bots`/`--optional-bots` only. | Already reconciled — no doc edit; D3 test guards against reintroduction. |
| Surviving `enabled_bots` frontmatter key | **Gone.** Only retirement/migration-shim references survive (`marshall-steward/scripts/upgrade.py`, `manage-config/standards/data-model.md`). | Null — no change. |
| Old return fields `complete` / `unfetched_bots` | **Absent from the whole tree.** Live names are `participation_complete` / `unproven_bots` / `bot_states`, already in use at both consumers. | Null — no change (D2's field-rename was already landed by an earlier PR). |

## Deliverables

**D1 — malformed bot-flag value REJECTED, not silently reinterpreted.** `review_completeness.py`.
- `parse_participation` now raises `MalformedBotFlag` on a shape violation (a bare/colonless token, or an empty-sided pair) instead of silently dropping it (which resolved the bot to `absent`, a *blocking* member → a confident false merge block). The SHAPE check is separate from the diff-derived-evidence SEMANTIC filter: a well-formed pair with inadmissible evidence stays a silent drop.
- `_split_bots` (bare-form flags) rejects a colon-bearing pair token.
- `--stale-participation-bots` changed from bare-form to **pair-form** (`parse_participation`), matching the producer's `stale_participation_bots[]` output and the sibling `--participated-bots` — the root fix for "the producer emits pairs for both while the flags disagree by construction".
- `cmd_check` renders `MalformedBotFlag` as `status: error` + exit 1 + no `participation_complete` (read as UNKNOWN by the barrier/FIND step).
- Commit `ff5af02`. Tests: `TestMalformedBotFlagRejection` (both directions), `TestStaleParticipationIsPairForm`, and the two pre-fix `coderabbit,absent` assertions replaced. **Mutation-proof by construction** (they assert behaviour that only exists post-fix; the pre-fix code returned `{}`/`absent`).

**D2 — reconcile prescribed invocations to live surfaces.** Docs.
- `execution-context.md` `plan_id` row: the false universal "Every script call inside this envelope forwards `--plan-id`" replaced with a per-script, per-position statement (before-the-verb for a router like `ci`; after the verb where declared there; append nothing where undeclared). **Primary fix site for the position cause class.**
- `automatic-review/SKILL.md` item 4: `{stale_participation_bots}` now rendered as `bot_kind:evidence_kind` pairs (matching the now pair-form consumer flag and the producer output). No barrier invocation change needed — it already forwarded the producer's pairs verbatim; D1 made the flag accept them.
- Plus the three NULL results above.
- Commit `d24e7fc`.

**D0 — enforce the exit-code convention across the merge-and-review population.** Prose + test.
- Widened the exit-code convention from "Every `manage-*` script call" to **every** `execute-script.py` call in `branch-cleanup.md`, `automatic-review/SKILL.md`, and `phase-6-finalize/SKILL.md` — a real SCOPE change (not a restatement), covering the non-`manage-*` github_pr/review_completeness/ci calls the old scope excluded. This closes the automatic-review FIND `fetch_findings` gap. The barrier's richer UNKNOWN branches remain as the "unless a step explicitly states otherwise" carve-out.
- Widening scoped to the finalize merge-and-review docs (D0's population); the ~35 other docs carrying the boilerplate convention are other phases/steps, out of scope. Intentional, documented inconsistency.
- Population-derived enforcement test `TestExitCodeConventionCoversEveryScript` (commit `ec02ee1`): derives the invoked-notation population from the docs, asserts it reaches the three non-`manage-*` families (derived, not hand-listed), and fails unless each doc's convention is widened. **Mutation-proven**: reverting a heading to the `manage-*` form fails exactly that doc's case (verified).

**D3 — population-derived parse test.** Test.
- `TestDocumentedReviewMergeInvocationsParse` (commit `ec02ee1`): derives the documented review-and-merge surface invocations (fetch_findings / review_completeness check / ci checks pull-request-runs) from the docs at run time, asserts non-emptiness first, publishes size (6 invocations, floor ≥ 4), substitutes placeholders, and runs each against its REAL parser, failing on any argparse rejection (exit 2). Copies the fenced-block/derivation discipline of `test/_shared/_dispatch_roster.py`.
- **Mutation-proven**: a reintroduced `--enabled-bots "{enabled_bots}"` in the FIND `fetch_findings` invocation made exactly the `skill-md-github-pr` case fail (exit 2), where pre-fix it would have failed only a dispatched agent at merge time (verified, then reverted).

## Build gate

`git diff --name-only origin/main...HEAD -- '*.py'` is non-empty (review_completeness.py + two test files). Ran `./pw verify plan-marshall`: **`=== verify: SUCCESS ===`, 15896 passed, 1 skipped (7m35s)**. Per-commit `./pw quality-gate plan-marshall` was clean (mypy 274 files no issues, ruff all passed, SPDX ok) before each `*.py` commit.

## Findings

| # | Source | Description | Disposition |
|---|---|---|---|
| 1 | pre-PR sub-agent | D1 SHAPE-vs-SEMANTIC separation correct; both directions tested; mutation-proof. | Confirmed — no change. |
| 2 | pre-PR sub-agent | D2 cold-read of the new `--plan-id` cell produces a correct **pre-verb** placement for the `ci` router; universal removed. | Confirmed — no change. |
| 3 | pre-PR sub-agent | D2 null results (`--enabled-bots`, `enabled_bots` frontmatter, `complete`/`unfetched_bots`) all hold. | Confirmed — no change. |
| 4 | pre-PR sub-agent | D3 docstring claimed it "copies the walk used by `_dispatch_roster`", but that module walks list-rosters, not fenced blocks. | **Fixed** (`6cf9ea8`): docstring corrected to "follows the discipline; reimplements a fenced-block walk". |
| 5 | pre-PR sub-agent | D0/D3 curation critique: `_CONVENTION_DOCS` and the D3 three-verb surface are hand-scoped, brushing the anti-curation mandate. | **Partially addressed** (`6cf9ea8`): the D0 widening *obligation* is now DERIVED from each doc's own non-manage-* invocations. **Accepted-with-reason** for the doc SET and D3 surface: "the merge-and-review path" is a semantic scope with no machine-readable manifest, and the run-based parse cannot cover choice/value-required verbs whose valid values are not doc-derivable. Documented in the test docstring + the PR's "For the reviewer to weigh". |
| 6 | pre-PR sub-agent | HYPOTHESIS "guard wired to review_completeness but not siblings": at the barrier all three are covered (present-but-ineffective prose); the FIND-step `fetch_findings` producer was the genuine uncovered sibling. | Confirmed — this PR is the *extension* that covers the FIND producer via the widened convention. |
| 7 | pre-PR sub-agent | HYPOTHESIS "a consumer tolerates the old field names": no reader of `complete`/`unfetched_bots` exists; `_cmd_merge_authorization.py` reads `unproven_bots` (new name). | **NULL result** — publishable; no change. |
| 8 | CI (`verify / gate`, `dependency-review`, `generate-check`) | success on head `6cf9ea8`. `verify / verify` in_progress at hand-off. | See Build gate; delegated. |
| 9 | PR review (`cuioss-review-bot` / pr-agent) | "PR Reviewer Guide — PR contains tests, No security concerns, No major issues detected." | No findings — nothing to fix or reply. |
| 10 | PR review (`coderabbitai`) | "Review limit reached — we couldn't start this review" (window reopens ~32 min). | Rate-limit refusal, not a finding — no action (routine, outside our control). |
| 11 | PR conversation (`cla-assistant`) | CLA status pending for `cuioss-oliver`. | Administrative/operator gate, not a code request — disclosed to the operator, not fixable here. |

Inline review-thread surface (`get_review_comments`): **0 threads** — read explicitly, not assumed.

## Reviewer participation

Population derived from configuration — the `author_login` of each `automatic-review/standards/{bot_kind}.md` registry doc (cross-named by `.github/workflows/pr-agent.yml`), never transcribed:

| Reviewer (`author_login`) | Verdict | Body evidence / reason |
|---|---|---|
| `cuioss-review-bot` (pr-agent) | `reviewed` | Published its "PR Reviewer Guide" issue_comment against the diff — "No major issues detected" (its declared publish shape; a review artifact over the diff). |
| `coderabbitai` (coderabbit) | `rate-limited` | Published ONLY the "Review limit reached — we couldn't start this review" refusal notice; no review of the diff. Window reopens ~32 min. |
| `sourcery-ai` (sourcery) | `silent` | The `Sourcery review` check concluded `skipped`; Sourcery published nothing. |

**Coverage: 1 of 3.** The § Step 8 shortfall disclosure fired: `cuioss-review-bot` reviewed; `coderabbitai` rate-limited (window reopens); `sourcery-ai` skipped/silent. Per the lane this is a DISCLOSURE, not a block — rate limits and skips are routine and outside our control, so the merge is armed on partial coverage with the shortfall stated, not held.

## Cost

- **Tokens:** not available to the agent in this session (the harness does not surface a per-run token total to the model), plus two sub-agent dispatches (~164k + ~119k tokens as the Task tool reported them).
- **Wall-clock:** run start ~08:13Z → PR opened ~09:09Z → merge armed / delegated.
- **Population:** this single Claude Code cloud session's usage as the harness counts it, plus the two sub-agents. ⛔ NOT comparable to a plan-marshall `metrics.toon` total (which counts an orchestrator-plus-agent dispatch tree under plan-marshall's per-task billing boundary a single interactive session does not share). The figures are not made comparable and are not presented as such.

## Contract check (Step 9)

| Step | Verdict | Artifact |
|---|---|---|
| 1 Skills loaded | done | Named above (Skills loaded). |
| 2 Branch | done | `claude/workflow-flag-script-mismatch-q42lik` on `origin` (harness-assigned, kept). |
| 3 Plan directory | done | `doc/plans/review-apparatus/030-…/plan.md` exists and opens with the first-instruction block. |
| 4 Implement | done | 4 deliverables; commits carry the `Co-Authored-By: Claude` trailer, no "Generated with Claude Code" footer. |
| 4 Per-commit gate | done | Each `*.py` commit preceded by a `./pw quality-gate plan-marshall` with mypy "no issues", ruff "all passed", SPDX ok. |
| 4 Pushed | done | No unpushed commit (this report is the final pre-arm push). |
| 5 Build gate | done | `*.py` changed → `./pw verify plan-marshall` = SUCCESS, 15896 passed / 1 skipped. |
| 6 Verification sub-agent | done | Findings 1-7 above, with dispositions. |
| 7 PR cycle | done | PR #1157; all comments dispositioned (Findings 9-11); both surfaces read (0 inline threads). |
| 8 Merge gate | conditions 1-3 met; auto-merge armed; landing delegated to collect (cloud session cannot self-confirm the queue landing). |
| 8 Bridge | done | No status/bookkeeping write under `doc/plans/` outside this plan's own directory. |
| 9 This check | done | This table. |
| 9 What have we learned | done | Below. |

GitHub access path: **GitHub MCP server**. Branch form: **harness-assigned**. No `/sync-plugin-cache` owed (cloud run).

## What have we learned (Step 9)

**One observation, recorded rather than proposed as a change.** In a cloud session the merge gate has a mild circularity: condition 3 makes the finalized report the *last* pre-merge commit, but pushing it re-triggers the required `verify` run — and condition 1 wants that required context *green* before arming, which a cloud session cannot poll for. I resolved it within the existing contract: finalize + push the report FIRST, then let auto-merge (which § Step 8 says "defers required-ness to the queue" on this merge-queue repo) hold the PR until the re-triggered `verify` passes. The contract already contains the resolution (the merge-queue note), so the friction is a documentation-clarity nit, not a gap — **no contract change proposed.** If the operator wants, the two clauses (condition 1 "pending = not met" vs the merge-queue "arming defers required-ness") could be cross-referenced explicitly for the cloud arm-and-hand-off case; that would be a separate `chore(cloud-plan-lane)` PR, not folded here.

## Residue

- **`verify / verify`** was `in_progress` at hand-off (passed locally; `verify / gate` already green in CI). The merge queue admits the PR only when it concludes green.
- **CLA status** shows pending for `cuioss-oliver` (`cla-assistant`); if the CLA is a required context it is an operator gate the queue enforces — not fixable in-session.
- **Review coverage 1-of-3** (disclosed): `coderabbitai` rate-limited (window reopens ~32 min), `sourcery-ai` skipped. Both routine; the merge is armed on partial coverage per the lane.
- Landing confirmation is delegated to the orchestrator's collect (read from the PR merge event), per § Step 8 arm-and-hand-off.
