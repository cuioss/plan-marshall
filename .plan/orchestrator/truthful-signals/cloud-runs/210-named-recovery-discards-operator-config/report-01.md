# Run report — 210-named-recovery-discards-operator-config (run 01)

**Date (UTC):** 2026-08-12    **Branch:** `claude/named-recovery-operator-config-d9v43a` (harness-assigned; kept as-is)    **PR:** [#1186](https://github.com/cuioss/plan-marshall/pull/1186)    **Outcome:** completed

## Skills loaded

Loaded by reading bundle-source paths (the `plan-marshall` plugin was not relied on):

- `cloud-plan-lane` (the governing contract, loaded first)
- `plan-marshall:ref-code-quality` (always)
- `pm-plugin-development:plugin-script-architecture` (always)
- `plan-marshall:ref-workflow-architecture` (workflow docs — the change's surface)
- `pm-dev-python:pytest-testing` (the new Python tests)

Conditional skills not loaded because unused: `plan-marshall:persona-implementer` (no production code — the change is workflow prose + a doc-content test), `pm-dev-python:python-core` (the test uses only `re` + stdlib and the conftest helpers), `pm-plugin-development:plugin-architecture` (no SKILL frontmatter/structure change), `pm-documents:ref-asciidoc` (no `.adoc` change), `plan-marshall:persona-security-expert` (not a security-domain change).

## Deliverables

### D0 — GATE: derive the population by assertion shape (mutates nothing)

Derived by **assertion shape** — "a document asserting that an artifact is safe to discard, restore, or delete on the strength of a guard that establishes only that one actor didn't write it" — not by command string. The sweep ran multiple phrasings across the full documentation surface (`marketplace/bundles/**`, `.claude/**`, `doc/**`, whole-repo `*.md`) and the script surface (`*.py`):

- `safe to (revert|delete|discard|remove|restore|drop|throw away|wipe|clean)`
- `(safely|freely|always) (delete|discard|revert|remove|restore|drop)`
- `git checkout --` / `git restore` / `reset --hard` / `git clean` / `rm -rf`
- `spurious write` / `without losing any` / `never a … output artifact` / `MUST NOT have touched`
- `restore … from HEAD` / `loses no` / `nothing is lost` / `no work is lost` / `no data loss`
- `Named recovery` / `Recovery: git` / `recovery case`

**Hit count vs population size (reported separately, per the plan and Verification):**

- **Hit count (raw volume examined):** several dozen matched lines across all phrasings and surfaces — a *volume*, not coverage. The bulk are unrelated uses of the same words: idempotency of an operation ("re-running `upgrade` is always safe", "Stop is always safe"), configuration semantics ("an unconfigured project loses nothing"), lock-guard cleanup ("the guard file is always removed in a `finally`"), and node_modules/apt/temp cleanup commands.
- **Population size (derived by shape): 3.** Exactly the three named-recovery `.plan/marshal.json` sites — planning.md (2-refine boundary), planning-outline.md (3-outline boundary), planning-outline.md (4-plan boundary). No fourth site of this assertion shape exists in the documentation or script surface.

**The three known sites were treated as a sample, not assumed to be the population** — the derivation is a shape sweep, and D3(b) encodes it (sweep by heading across every workflow doc, so a future fourth boundary is covered automatically). The sample-as-population error the plan warns against is avoided: the count of 3 is a *derived* result, not the seed.

**Two counter-postures already in the repo (NOT in the destructive population — they are the correct model):**
- `execute-task/SKILL.md` §"Anti-pattern: never batch a destructive checkout to re-baseline" — states plainly that `git checkout -- <files>` / `git restore <files>` are "destructive of uncommitted working-tree content with no undo" and mandates inspection + per-path proof before any revert. This is the exact correct treatment the three named-recovery sites contradicted; D1's replacement aligns with it.
- `plugin-script-architecture/standards/shim-marker-convention.md` and `plugin-doctor/references/rule-catalog.md` — "nobody can **prove** it is safe to delete" (evidence required), and `risky-fixes-guide.md` — a shim "can be safely removed" only after the live-caller count "must be verified to be ≤1".

**Sibling-plan hand-off (Out-of-scope item):** the sibling plan `truthful-signals/140-detect-artifacts-offers-a-live-audit-trail-as-safe-to-delete` covers the same archetype on a **different surface** — a *tool* (`detect-artifacts`/`scan_artifacts` in `git-workflow.py`) that offered a running plan's live audit trail as safe-to-delete. That plan is already landed (PR #1171). **The two surfaces do NOT share a code root** — one is workflow prose emitting a human-facing recovery line, the other is a Python traversal classifier — so there is nothing to re-scope and nothing fixed "twice in two shapes". D0's population (the 3 doc sites) is disjoint from 140's surface.

### D1 — Replace the false inference at every site

Done at all three sites. The valid inference — *"phase N must not have touched it" → "something other than phase N wrote it (most likely the operator)"* → **inspection, not restoration** — now drives each block. The recovery surfaces the diff (`git diff -- .plan/marshal.json`) and requires an **explicit operator disposition** (Keep / Discard) before any discard; a discard is permitted only on an explicit operator "Discard" and only against that one file. Commit `6308698`.

⛔ **The word "always" does not survive in any justification** at any of the three sites — verified: `always safe` / `always a spurious` / `MUST NOT have touched` / `Recovery: git checkout --` all return zero matches across both workflow files (incl. the cross-reference bullets, one of which — planning.md — had carried "makes marshal.json restoration always safe").

### D2 — Collapse the triplet into ONE authority

Done. The full contract (premise, danger, inspection steps, disposition options) now exists **once**, in `planning.md` at the 2-refine boundary, marked "the single authority for this recovery — the outline and plan phase boundaries reference this block". The two `planning-outline.md` boundaries (3-outline, 4-plan) are now **references** to it — a one-line imperative plus a cross-reference bullet pointing at the authority — not restatements of the justification. Per the standing rule, the copies were deleted (replaced by references), not synchronised. The drift evidence the plan cited — the 2-refine copy's grammatical corruption *"a spurious write that safe to revert"* (missing "is") — is gone with the copy.

### D3 — Tests, each verified RED pre-fix

New file `test/plan-marshall/plan-marshall/test_named_recovery_marshal_config.py`, three tests, **each seen red against the unfixed docs before the fix, green after** (see § Findings for the red evidence):

- `test_named_recovery_never_instructs_unconditional_discard` — D3(a): no derived named-recovery region carries an unconditional-discard directive or an "always safe" justification.
- `test_named_recovery_inspection_first_population_nonempty_and_covers_known_members` — D3(b): the derived population of inspection-first sites is asserted **non-empty** and covers the known members, with a non-vacuous control (the plain by-heading sweep) proving the derivation examined a populated surface — so the non-empty assertion cannot pass on an empty sweep. **The derivation is asserted, not the enumeration** (the known members are checked as a subset, and the sweep globs every workflow doc).
- `test_named_recovery_contract_is_a_single_authority` — D2 collapse guard: exactly one authority (the block carrying the concrete `git diff` inspection command); every other named-recovery site references it. This is red pre-fix (three copies, zero authorities) and pins the collapse against future re-drift.

## Build gate

`git diff --name-only origin/main...HEAD -- '*.py'` verdict: **Python changed** (the new test file) → build gate takes its full path.

`./pw verify plan-marshall` (scoped — the entire diff is within the plan-marshall bundle and its test dir): **`16157 passed, 1 skipped in 318.99s`**; coverage line: `mypy(production) [277 files], ruff [marketplace/bundles/plan-marshall, test/plan-marshall], SPDX headers, mypy(test) [574 files], module-tests [plan-marshall]`; `=== verify: SUCCESS ===`. No `errors[]`. The single skip is the pre-existing environment-guarded test (the reference-platform `skipped == 0` gate is CI-opt-in; a local scoped run does not set it), not introduced by this change.

## Findings

Every finding with source and disposition. Recorded per instance.

### D3 pre-fix RED evidence (each test seen red first, against unfixed docs)

Run with the session's `pytest` (uv-tool 9.0.2, `-o addopts="" -o filterwarnings=ignore`) directly against the workflow docs at HEAD before the fix:

| Test | Pre-fix | Evidence |
|---|---|---|
| `test_named_recovery_never_instructs_unconditional_discard` (D3a) | RED | Offender list named all three sites — `planning.md:390`, `planning-outline.md:257`, `planning-outline.md:581` — each carrying BOTH an unconditional `git checkout --` recovery directive AND an "always safe"/"always a spurious" justification. |
| `test_named_recovery_inspection_first_population_nonempty_and_covers_known_members` (D3b) | RED | `assert []` — zero inspection-first sites. The non-vacuous control passed first (the by-heading sweep found 3 regions incl. both planning-outline.md boundaries), so the failure is specifically the empty inspection-first population, not a vacuous sweep. |
| `test_named_recovery_contract_is_a_single_authority` (D2) | RED | `assert 0 == 1` — zero authorities (no block carried the `git diff -- .plan/marshal.json` inspection command); three copies existed. |

Post-fix: all three PASS (`3 passed`), and the full scoped suite is green (§ Build gate).

### Verification sub-agents (pre-PR)

Two independent `general-purpose` sub-agents, read-only (report, never fix).

**1. Isolated recovery-text semantic check** (the plan's flagged "check that matters most" — give the agent ONLY the new recovery text, no other context, and ask what it would do about a dirty `marshal.json`). **PASS.** With no context beyond the authority's recovery text, the agent's first action was `git diff -- .plan/marshal.json` (a read-only inspection); it answered **No** to running an immediate/unconditional discard; it would discard only after reporting the diff AND receiving an explicit operator "Discard" disposition, scoped to that one file; and it summarized the behavior as "inspect → report to operator → no destructive action until the operator explicitly decides." It did **not** reach for `git checkout --`. The wording succeeds by the plan's own test.

**2. Deliverable verification (D0–D3 + beyond-diff stale-claim sweep).** **PASS (clean).** The agent verified against the plan's own requirements, read the post-fix files (not just the diff), ran its **own independent** repo-wide assertion-shape sweep, and reasoned each test against the pre-fix text:

- D0 — shape-based derivation encoded (globs every workflow doc, keys on the heading not the command string); population size (3) vs hit count (several dozen) separated correctly. Its independent missed-site sweep found **no fourth site**; the other `always safe` hits are genuinely unrelated (operation idempotency, "Stop is always safe", log interpolation). It confirmed the two counter-postures (`execute-task` anti-pattern; shim-marker "prove it is safe to delete") are the correct model, not defects.
- D1 — all three sites inspect-first with operator disposition; **"always" survives in no justification** (the only remaining `always` occurrences in either file are unrelated dispatch-mechanics prose); the old "…makes marshal.json restoration always safe" cross-reference is gone.
- D2 — the full contract exists exactly once (planning.md, self-labelled "the single authority"); the `git diff -- .plan/marshal.json` inspection command appears in no other **named-recovery region** across the workflow docs (which is what the `_is_authority` uniqueness test asserts — the string also occurs, as expected, as the predicate literal in the regression test and in this report's prose, neither of which is a recovery block); the two planning-outline.md boundaries are references, not restatements; the drift-corruption is gone.
- D3 — both tests assert the derivation (subset membership on the swept set), not an enumeration; each would fail against the pre-fix text (RED), matching the recorded evidence. The agent noted it cannot itself witness the "seen red first" process (it was not present pre-fix) but confirmed the verifiable substance — the tests *would* fail pre-fix.
- Collateral/scope: clean — only the declared surface plus the plan-lane records. Beyond-diff stale-claim sweep across the whole bundle and repo: **none survives** (the only residual quotes of the old wording are in plan.md and this report, which cite it as the defect being fixed).

Two non-blocking observations, both accepted with reason (no fix warranted):
- The D3 shape derivation is scoped to the named-recovery heading within `skills/plan-marshall/workflow/`. This is the deliberate scope — D3 regression-tests the named-recovery population (the realistic recurrence: a new phase boundary adding such a block, "covered automatically"), while the broader assertion class is D0's one-time human sweep. Consistent with the plan.
- The RED-evidence table cites the plan-boundary offender at `planning-outline.md:581` — the correct line **in the pre-fix docs** where the RED run executed; the post-fix heading sits at :576 after the shorter reference replaced the longer block. The pre-fix line is the accurate record of the red run.

## Reviewer participation

Expected reviewer population **derived from configuration** — the `author_login` of each `marketplace/bundles/plan-marshall/skills/automatic-review/standards/{bot_kind}.md` registry doc (cross-named by `.github/workflows/pr-agent.yml`): `cuioss-review-bot` (pr-agent.md), `coderabbitai` (coderabbit.md), `sourcery-ai` (sourcery.md). M = 3.

| Reviewer (`author_login`) | Verdict | Body evidence / reason |
|---|---|---|
| `cuioss-review-bot` | `reviewed` | Published a "PR Reviewer Guide 🔍" issue-comment against the diff: "PR contains tests / No security concerns identified / No major issues detected" — an explicit nothing-to-report over the diff. |
| `coderabbitai` | `reviewed` | Published a full walkthrough and a review with "Actionable comments posted: 1" — one inline review-thread comment on `report-01.md:93` (scope the command-uniqueness claim). Handled: fixed + replied on the thread. A later incremental re-review of the report-only push hit its rolling PR limit, but the substantive review over the code diff completed and produced the finding. |
| `sourcery-ai` | `rate-limited` | Published **only** a refusal (review body, COMMENTED state): "you have reached your weekly rate limit of 500000 diff characters." Its `Sourcery review` check concluded `skipped`. It engaged but did not review this diff. |

**Coverage: 2 of 3.** Inline review-thread surface: 1 thread (CodeRabbit), read explicitly and handled — not inferred from the conversation view. All three comment surfaces (`get_comments`, `get_reviews`, `get_review_comments`) were read before the merge gate.

**§ Step 8 condition-4 shortfall disclosure (fired):** "Review coverage: 2 of 3 — `cuioss-review-bot` reviewed (no findings); `coderabbitai` reviewed (1 actionable comment, fixed); `sourcery-ai` rate-limited (weekly 500k-diff-char quota)." Per the contract this is a **disclosure, not a block** — the rate limit is routine and outside our control, and the merge is gated only on conditions 1–3.

## Cost

- **Tokens:** not available to the agent in this session (a single interactive Claude Code cloud session; the harness does not surface a per-run token count here).
- **Wall-clock:** dominated by one `./pw verify plan-marshall` (~5m19s build + suite) plus the shape sweep and two verification sub-agents.
- **Population:** this single Claude Code cloud session's usage. ⛔ NOT comparable to a plan-marshall `metrics.toon` total, which counts the orchestrator-plus-agent dispatch tree under plan-marshall's per-task billing boundary — a boundary a single interactive cloud session does not share. No comparable number is presented.

## Contract check (Step 9)

| Step | Verdict |
|---|---|
| 1 Skills loaded | ✅ Named in § Skills loaded (read by bundle path; `plan-marshall` plugin not relied on). |
| 2 Branch on `origin` | ✅ `claude/named-recovery-operator-config-d9v43a` (harness-assigned, kept as-is) — absent from the remote at start (`git ls-remote` empty), pushed to `origin` before any edit. |
| 3 Plan directory | ✅ `doc/plans/truthful-signals/210-…/plan.md` exists and opens with the first-instruction block (present in the handed file — no repair needed). |
| 4 Implement | ✅ D0–D3 addressed; every commit carries the `Co-Authored-By: Claude` trailer and no "Generated with Claude Code" footer. |
| 4 Per-commit gate | ✅ The one `*.py`-touching commit (`6308698`, the test) was preceded by a clean `./pw verify plan-marshall` (16157 passed, quality-gate + mypy(test) clean, SPDX passed). The plan-dir move and report commits touch no `*.py` → no gate owed. |
| 4 Pushed | ✅ Branch pushed after every commit; no unpushed commit remained at any stage. |
| 5 Build gate | ✅ Python changed (the new test) → full path; `./pw verify plan-marshall` clean. |
| 6 Verification sub-agent | ✅ Two dispatched (isolated-recovery-text + deliverable verification); findings + dispositions in § Findings; both PASS. |
| 7 PR cycle | ✅ PR [#1186](https://github.com/cuioss/plan-marshall/pull/1186); all three comment surfaces read; the one actionable comment (CodeRabbit) fixed and replied on-thread. |
| 8 Merge gate | Conditions 2 (comments handled) and 3 (report finalized) met at this report-commit; condition 1 (required `verify` check) confirmed success on the final head immediately before arming; auto-merge (SQUASH) then armed. Condition-4 shortfall (2-of-3 coverage) disclosed. The merge commit is recorded to the operator, not embedded here. |
| 8 Bridge | ✅ No status/bookkeeping write landed under `doc/plans/` outside this plan's own directory; the report carries the PR number and per-deliverable outcome for the collect step. |
| 9 This check | ✅ This table. |
| 9 What have we learned | ✅ Below. |

**GitHub access path used:** the GitHub MCP server (the cloud path). **Branch form:** harness-assigned `claude/*`, kept as-is. **`/sync-plugin-cache`:** not owed — a cloud run never performs or owes it (machine-local build step); the merged bundle source is authoritative.

## What have we learned (Step 9)

**No NEW contract change proposed — but this run independently reproduced the evidence for the sibling plan 140's pending proposal, and that corroboration is worth recording.**

The lane's build-gate wording (§ Step 4 per-commit gate and § Step 5) instructs a run to "open the `log_file` it names and confirm `total_issues: 0` and an empty `errors[]`" — vocabulary from the plan-marshall executor's TOON output. But this lane runs `./pw verify` **directly**, which emits no such `log_file`/`total_issues`/`errors[]` structure; it streams the tools' own output (`ruff … All checks passed!`, `mypy … Success: no issues found`, `SPDX-header check passed`, and the `N passed, M skipped` pytest summary and the `=== verify: SUCCESS ===` line). I read cleanliness from those streamed lines, which is the lane-appropriate signal — the same friction plan 140's report already documented and proposed a wording fix for. Because 140 has already presented that concrete edit to the operator (pending), filing a duplicate here would be noise; this run records the corroboration instead. Presented to the operator in this run's closing message.

One smaller observation, **not** rising to a proposal: the lane's fast red-check has no single-file path — the system `python3` has no `pytest`, and `./pw module-tests` runs the whole bundle suite. I used the session's uv-tool `pytest` (`-o addopts="" -o filterwarnings=ignore`) to see each D3 test red against the unfixed docs quickly, then used the contract's `./pw verify` for the authoritative gate. This worked and needed no contract change; noting it only so a future run knows the fast-red option exists.

## Residue

- **Nothing left open in scope.** All four deliverables (D0–D3) are complete and verified; the one review comment is fixed.
- **Merge landing** is delegated to the merge queue (auto-merge armed) — see the closing operator note for the confirmed `state: MERGED` / merge commit, which cannot appear in this pre-merge report (the branch locks on arming).
- **`/sync-plugin-cache`:** not owed — a cloud run never performs or owes it (machine-local build step).
- **Sibling sequencing (plan Notes):** this plan and the sibling that declares exclusivity against dispatched-workflow-doc edits must not run concurrently; this run touched `planning.md` and `planning-outline.md`, so a concurrent sibling run must be sequenced after this lands.
