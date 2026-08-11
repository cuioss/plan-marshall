# Run report — 030-a-workflow-doc-prescribes-a-flag-no-script-declares (run 01)

**Date (UTC):** 2026-08-11    **Branch:** claude/workflow-flag-script-mismatch-q42lik (harness-assigned, kept as-is)    **PR:** _pending_    **Outcome:** completed (pending PR + merge gate)

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

_Pending the pre-PR verification sub-agent (Step 6, dispatched), CI, and PR review — recorded per instance below as each returns._

## Reviewer participation

_Pending PR._

## Cost

- **Tokens:** not available to the agent in this session (the harness does not surface a per-run token total to the model).
- **Wall-clock:** run start ~08:13Z; PR/merge pending.
- **Population:** this single Claude Code cloud session's usage as the harness counts it. ⛔ NOT comparable to a plan-marshall `metrics.toon` total (which counts an orchestrator-plus-agent dispatch tree under plan-marshall's per-task billing boundary a single interactive session does not share).

## Contract check (Step 9)

_Filled at Step 8 condition 3, as the last pre-merge commit._

## What have we learned (Step 9)

_Filled at Step 8 condition 3._

## Residue

_Pending._
