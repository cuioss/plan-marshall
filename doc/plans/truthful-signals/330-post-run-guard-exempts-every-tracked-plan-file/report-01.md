# Run report — 330-post-run-guard-exempts-every-tracked-plan-file (run 01)

**Date (UTC):** 2026-08-13    **Branch:** `claude/post-run-guard-exempts-plans-q4if33` (harness-assigned, kept as-is)    **PR:** [#1217](https://github.com/cuioss/plan-marshall/pull/1217)    **Outcome:** completed (auto-merge armed; landing delegated to the merge queue)

## Skills loaded

- `plan-marshall:ref-code-quality` (via bundle path)
- `pm-plugin-development:plugin-script-architecture` (via bundle path)
- `plan-marshall:persona-implementer` (via bundle path — production-code work identity)
- `pm-dev-python:python-core` (via bundle path — Python production code)
- `pm-dev-python:pytest-testing` (via bundle path — Python tests)
- `pm-plugin-development:plugin-architecture` — to be loaded before SKILL.md prose edits

## Deliverables

_Filled in as the run proceeds._

### D0 — GATE: classify exemption population + re-derive tracked-file set under `.plan/`

**Verify-first clause (the plan's re-scope gate).** `git ls-files .plan/` at HEAD returned **13 tracked
files** — `.plan/marshal.json` (the project config) plus `.plan/project-architecture/_project.json`
and eleven `.plan/project-architecture/{module}/enriched.json` architecture descriptors. The set is
**non-empty**, so the premise is **CONFIRMED, not refuted** — the plan proceeds unchanged. (Claim-label
row "Files under `.plan/` are git-tracked, including the config and the architecture descriptors":
HYPOTHESIS → **confirmed**.)

**Exemption-population classification** (published with the population it was derived from: a
`.plan`-literal sweep of `marketplace/bundles/**/*.py`, then reading each hit). The classification
criterion: a site is **same-defect** iff it (a) observes **working-tree dirtiness** to decide whether a
step left **unpushable tracked source** behind, and (b) a `.plan/`-prefix drop excludes a git-**tracked**
`.plan/` file from that verdict — a false-clean signal about an unpushable tracked edit.

| # | Site (by symbol) | Classification | Evidence |
|---|---|---|---|
| 1 | `post_run_source_guard.py` — `_PLAN_STATE_PREFIX` const (L91), `filter_tracked_source` (L138) | **same-defect (CONFIRMED)** | porcelain runs `--untracked-files=no` (L179) → input tracked-only; `filter_tracked_source` then drops `.plan/` (L148), so every dropped path is known-tracked. A dirty tracked `.plan/marshal.json` post-gate → reported `clean:true`. |
| 2 | `_invariants.py` — `_filter_main_dirty_paths` (L458–474) | **same-defect (CONFIRMED)** | `return [p for p in paths if not p.startswith('.plan/')]` — per-site copy of the same prefix drop, on the "normal bookkeeping" rationale (docstring L466–469). Input = `git_dirty_files` = `git status --porcelain` **including untracked** (`_git_helpers.py` L71–78), so here the drop hides *tracked* `.plan/` drift. |
| 3 | `_path_attribution_merge.py` (extension-api) | **different-purpose (not a defect)** | The `.plan` strings at L92 / L359 are **illustrative docstring examples** of the generic path normalizer (`_normalize_spelling`/`lookup_claim`). There is **no `.plan/` prefix exemption in executable code**; the module maps path→module ownership, not dirty-source detection. |
| 4 | `check-manifest-consistency.py` — `_BOOKKEEPING_PREFIXES` (L49), `filter_bookkeeping` (L194) | **different-purpose (not a defect)** | Operates on a **committed diff** (`git diff {base}...HEAD --name-only`, L172) — every path already committed and pushable. Dropping tracked `.plan/`+`.claude/` bookkeeping from *footprint classification* (docs-only/tests-only) is correct; a trackedness predicate would *introduce* false positives (committed `.plan/marshal.json` is tracked → would wrongly count as implementation footprint). |
| 5 | `check-routing-decisions.py` — `_BOOKKEEPING_PREFIXES` (L66), `_is_bookkeeping`→`footprint_has_production` (L276–294) | **different-purpose (not a defect)** | Same as #4: operates on the **realized/committed footprint** (`resolve_footprint`/`--diff-file`); the `.plan/`+`.claude/` drop correctly excludes bookkeeping from a *production-code* check. Trackedness predicate would wrongly count committed `.plan/marshal.json` as production code. |
| 6 | `gitignore_setup.py` — `.plan/` constants (L66–93) | **negative-control (EXPECTED)** | Its job *is* `.plan/` gitignoring — the matched negative control. Not touched (plan Out-of-scope). |

**D0 verdict: exactly TWO confirmed same-defect sites** (#1, #2). These are the sites D1 fixes with one
shared predicate and D5 tests against. The three previously-unclassified rows (#3–#5) are **different-purpose**
— the "floor of six" was a literal-string-sweep floor; on reading, four of the six are not the defect
(three different-purpose + one negative control). D0 mutates nothing.

_Verification state: complete. Committed as the D0 GATE checkpoint._

### D1 — Shared trackedness predicate

Done. New shared module
`marketplace/bundles/plan-marshall/skills/script-shared/scripts/_plan_state_exemption.py`
(`partition_plan_state_exemption` / `tracked_plan_paths` / `is_plan_state_path`). A `.plan/` path
is exempt **only when it is NOT git-tracked**; a tracked `.plan/` file is retained like any other
tracked source; non-`.plan/` paths are never exempted by this predicate; on an unusable trackedness
observation the predicate **fails closed (retains)**. **Both** confirmed sites import and call the
single predicate: `post_run_source_guard.py` (`_observe_dirty_source`) and `_invariants.py`
(`_filter_main_dirty_paths`, threaded the tree, called from `_capture_main_dirty_files`). It is one
predicate, not a per-site copy — the plan's central D1 requirement. Commit `4d882c5`.

### D2 — Publish examined population

Done. The post-run guard's TOON output now carries `considered_paths` (every dirty tracked path
observed, the population the verdict is drawn from), `exempted_paths` (the untracked `.plan/` subset
dropped — always empty at this site because its porcelain is `--untracked-files=no`, so honest and
correct), and `offending_paths` (retained). A `clean: true` naming a non-empty `considered_paths` is
distinguishable from a looked-at-nothing pass. Verified non-empty in the CLI output by
`test_cli_publishes_examined_population`. Contract prose updated in `phase-6-finalize/SKILL.md`.
Commit `4d882c5`.

### D3 — Fix declared footprint at freeze point

Done — **choice recorded: option B (teach consumers it is a declaration, never a record).** The
freeze point is `manage-solution-outline/scripts/_plan_parsing.py::_extract_affected_files`, which
parses the outline `**Affected files:**` blocks at phase-3 and is never re-derived during execution
(claim "frozen at outline time" → confirmed by symbol). Rather than update the frozen list at
execution time (option A) or re-derive scope inside each consumer gate (explicitly rejected — it
multiplies the source of truth), the declaration-vs-record distinction is made explicit in the
contract: a new subsection in `manage-execution-manifest/standards/decision-rules.md` states that
`affected_files` / `outline_affected_files` / `affected_files_count` are a frozen declared lower-bound
surface (a pre-filter hint) and the single authoritative touched-file record is `live_footprint` —
the source `security_class_inactive` and the retrospective footprint checks already consult. The
wording is correct for both sanctioned and unsanctioned widenings ("approval is not recording"), and
does not implement the refuted absent-key remedy. The freeze-point docstring names its role. Commit
`3e415f8`.

### D4 — Disposition for legitimately-dirty tracked `.plan/` file

Done — **the run cannot autonomously make the finalize-lifecycle decision, so a proposal is recorded
(the plan's sanctioned fallback).** Evidence gathered this run: `default:architecture-refresh` is
`order: 10` (before the merge gate `default:branch-cleanup`, order 70), so it writes AND commits the
architecture descriptors on the feature branch (`chore(architecture)`) pre-merge — those writes are
pushable and the main checkout is clean by the time the post-run band runs. `finalize-step-preference-emitter`
(order 992, post-merge) deliberately NAMES owed enrich calls rather than writing them. So **the fixed
guard does NOT create a recurring block in the current flow** — no post-run step writes a tracked
`.plan/` file today. A tracked `.plan/` path reported by the guard therefore means an owed enrich
write ESCAPED the pre-merge commit — a genuine gap, surfaced non-blocking (item 5f is advisory). The
disposition is documented in `phase-6-finalize/SKILL.md` item 5f. The **durable remedy is an open
proposal** — see the "Contract / lifecycle proposal (D4)" section below.

### D5 — Tests (each seen RED pre-fix)

Done. Red-first evidence captured against the unfixed code (3 controls RED, matched negative control
GREEN by construction), then GREEN after the fix:

- **(a) positive control, site 1** — `test_dirty_tracked_plan_state_is_reported`: a dirty TRACKED
  `.plan/` file IS reported. Seen RED pre-fix (asserted `clean False`, got `True`).
- **(c) positive control, site 2** — `test_capture_main_dirty_files_reports_tracked_plan_state`: a
  dirty TRACKED `.plan/` file is retained in the capture. Seen RED pre-fix (captured `[]`).
- **(d) population non-empty** — `test_cli_publishes_examined_population`: the `considered_paths`
  field is non-empty. Seen RED pre-fix (field absent).
- **(b) matched negative controls** — site 1 `test_dirty_untracked_plan_state_is_not_reported`, site 2
  `test_capture_main_dirty_files_exempts_untracked_plan_state`, plus the shared-module
  `test_partition_exempts_untracked_plan_file`: an UNTRACKED `.plan/` file stays exempt. GREEN both
  before and after by construction (they assert the preserved behavior — the plan's own D5(b) frames
  the negative control as guarding the over-broad fix, i.e. it must stay green; it cannot be red-first
  because that would require the current code to already report untracked `.plan/`, which it does not).

Both confirmed sites carry the positive+negative pair (D5c). The shared-predicate logic (prefix
precision, tracked/untracked split, fail-closed, sort/dedupe) is covered by the new
`test/plan-marshall/script-shared/test_plan_state_exemption.py`. Commits `4d882c5`, `ad40b0f`.

## Build gate

`git diff --name-only origin/main...HEAD -- '*.py'` is non-empty (guard predicate, both sites, the
outline parser, and tests), so the build gate takes its full path (as the plan's Verification section
requires). `./pw quality-gate` clean at each `.py` commit (ruff / mypy / SPDX / plugin-doctor, coverage
COMPLETE, `issues[0]`). Final `./pw verify`: **SUCCESS — 19515 passed, 14 skipped, 0 failed** in
7:20, coverage COMPLETE across quality-gate + mypy(production, 397 files) + mypy(test, 728 files) +
whole-tree module-tests. `UV_HTTP_TIMEOUT=600` and a 600000 ms Bash timeout were used on every `./pw`
call.

One note on the gate revealing a real defect: the first `./pw verify` failed on two of the new
shared-module non-repo tests. Under `./pw`, `build.py` roots `tmp_path` INSIDE the repo (`--basetemp`
under `.plan/temp/`), so `git -C <tmp_path subdir>` resolves the enclosing plan-marshall repo instead
of failing — a `tmp_path`-based "not a repository" test does not exercise the fail-closed path.
Switched those two tests to the `outside_repo_dir` fixture (system-temp, genuinely outside any repo);
re-verify is green. This is exactly the class of ambient-vs-pinned divergence `./pw verify` exists to
catch — the ambient-pytest run had hidden it (its tmp is `/tmp`, outside the repo). Commit `ad40b0f`.

## Contract / lifecycle proposal (D4)

**Problem (recorded, not decided this run).** With the guard fixed, a legitimately-owed
architecture-enrich write to a tracked `.plan/` file that lands AFTER the merge gate has no push path
onto the already-merged feature branch, and the guard now (correctly) reports it. In the current flow
this does not occur (architecture-refresh commits pre-merge at order 10; no post-run step writes
tracked `.plan/`), so no recurring block exists today — but the durable question "a finalize step
legitimately produces a tracked write and there is no push path for it" needs an owner's decision.

**Options and consequences** (a finalize-lifecycle change that alters when/where architecture-enrich
writes — out of scope for the guard fix, which is why this is a proposal):

- **A. Flush all owed enrich hints in the pre-merge `architecture-refresh` band (order 10).** Owed
  descriptor writes ride the current PR and are pushable. Consequence: couples enrich-flushing to
  every plan's pre-merge band; a hint discovered post-merge (by the preference-emitter at order 992)
  still cannot ride this PR — it lands next plan.
- **B. Give the post-run band a follow-up push path.** After the post-run band, commit an owed tracked
  `.plan/` enrich write and open a small follow-up PR. Consequence: extra PR churn per enriching plan.
- **C. Classify the tracked-`.plan/`-descriptor finding as informational (non-blocking at the
  completion boundary), distinct from a tracked-source `mutates_source` violation.** Consequence: the
  enrich lag persists across plans, but no plan is ever blocked; requires the guard to categorize
  offenders (tracked source vs tracked plan-config).

**Recommendation for the operator:** A (flush owed hints pre-merge) is the cleanest — it keeps one
push path and no extra PRs — but it does not close the post-merge-discovery case, for which C is the
safety net. This run implements neither; it surfaces the reported path non-blocking and records this
proposal.

## Findings

**Verification sub-agent (Step 6, `general-purpose`, read-only).** Verdict: all six deliverables
D0–D5 satisfied as specified; D0 classification independently confirmed (the two retrospective checks
observe a *committed* diff so a trackedness predicate would there introduce false positives; the
path-attribution helper is docstring-only; an independent sweep for a 7th `startswith('.plan/')`
prefix-drop found none); D1 is a genuine single shared predicate; no undeclared collateral. It
surfaced four stale-restatement findings — each a doc/comment that still asserted the old drop-all
behavior and is now false. All four **accepted and fixed** (a false restatement is exactly the defect
this truthful-signals epic targets):

| # | Source | Finding | Disposition |
|---|---|---|---|
| 1 | `workflow-integration-git/standards/worktree-handling.md:220` § "Filter Rule: `.plan/` Paths Are Excluded" | HIGH — a dedicated section (header + body) asserting the old unconditional drop-all; the same file's § "What Layer D Detects" was updated but this section was missed, leaving the standard self-contradictory | **fixed** — header → "Excluded Only When Untracked"; body rewritten to the trackedness rule (commit `<pending>`) |
| 2 | `test/plan-marshall/phase-6-finalize/test_post_run_review_ordering.py:557` | LOW — a per-test docstring stating the predicate is "dirty AND tracked AND outside .plan/" | **fixed** — corrected to "dirty AND tracked; `.plan/` exempt only when untracked" |
| 3 | `plan-marshall/scripts/_handshake_store.py:25`, `_handshake_commands.py:17` | LOW — bare "sorted, `.plan/`-filtered" shorthand, not updated in lock-step with the parallel `phase-handshake.md:127` table | **fixed** — both now describe the trackedness-keyed exemption |
| 4 | `test/plan-marshall/plan-marshall/test_phase_handshake_worktree_assertion.py:502`, `test_worktree_contract_e2e.py:16` | LOW — one-line scenario summaries implying drop-all | **fixed** — both now say "untracked `.plan/` filtered; a tracked `.plan/` file retained as a leak" |

No finding was rejected.

**Re-verification round (same sub-agent, resumed).** After fixing 1–4 the agent re-verified and ran a
SECOND independent beyond-diff sweep — warranted because finding #1 showed a whole section can slip a
first sweep. It confirmed all four fixes truthful and surfaced **two more** stale restatements I had
missed; both accepted and fixed:

| # | Source | Finding | Disposition |
|---|---|---|---|
| 5 | `phase-6-finalize/workflow/lessons-capture.md:24` | "reports any dirty TRACKED path **outside `.plan/`**" — the same stale pattern already fixed in the sibling `finalize-step-preference-emitter.md`, missed here | **fixed** — mirrored the preference-emitter wording ("source, or a tracked `.plan/` config/descriptor, keyed on trackedness"); also clarified the step writes only UNTRACKED plan state |
| 6 | `test/plan-marshall/plan-marshall/test_invariants.py` `test_capture_main_dirty_files_only_dot_plan_paths_returns_empty_list` | LOW — docstring "Only `.plan/` paths dirty → empty" generalizes the old drop-all; the test also relied implicitly on the ambient checkout's tracked-`.plan/` set | **fixed** — renamed to `..._only_untracked_dot_plan_paths_...`, docstring corrected, and made robust by stubbing `_repo_root` to a controlled repo |

**Convergence round (round 3, same sub-agent).** After the round-2 fixes the agent ran one more
EXHAUSTIVE beyond-diff sweep (96 marketplace hits + 72 test hits reviewed in full, plus `doc/**` and
the guard output-field enumeration). Verdict: **CLEAN** — both round-2 fixes truthful, and no remaining
stale statement of the old guard/layer-D "all `.plan/` dropped / always exempt / dirty tracked source
outside `.plan/` / only `.plan/` → empty" behavior in any current-state prose, docstring, comment,
section header, worked example, or test scaffold. Every surviving "outside `.plan/`" occurrence is a
correct description of the non-`.plan/` tracked-source control or an explicit contrast against tracked
`.plan/`.

The round-3 sweep flagged one BORDERLINE pre-existing statement (not a guard-scope restatement):
`workflow-integration-git/standards/worktree-handling.md:27` restated the blanket premise D0 refuted
("`.plan/` is … excluded from version control"). Its operative claim (worktree placement under
`.plan/local/worktrees/` inherits gitignore coverage) is true, but the lead clause is the epic's exact
false premise, so — being already in this file — it was **tightened** to "its runtime `.plan/local/**`
subtree is git-ignored … (a handful of files under `.plan/` are tracked — `marshal.json`, the
`project-architecture/**` descriptors — but `.plan/local/**` is not)."

Total: **six stale-restatement findings across two rounds, plus one borderline premise — all seven
fixed; round-3 verdict clean.** Quality gate green after every fix round; `./pw verify` green (19515
passed) and all fixes since are prose/comment/test-scaffold only (no runtime behavior change).

**CI (PR #1217).** All required and non-required contexts green: `verify / conclusion` **success**,
`verify / verify` success, `verify / gate` success, `generate-check` success, `dependency-review`
success, `review / review` success; `auto-merge` and `Sourcery review` checks skipped (expected).
`mergeable_state: clean`. No CI finding.

**PR review.** No actionable review comment on any surface (issue comments, review summaries, inline
threads all read). Dispositions: `cuioss-review-bot` posted "No major issues detected / No security
concerns / PR contains tests" — nothing to address; `coderabbitai` and `sourcery-ai` posted only
rate-limit notices — no review content to act on. Inline review threads: none.

## Reviewer participation

Expected reviewer population **derived from configuration** — the `author_login` of each
`marketplace/bundles/plan-marshall/skills/automatic-review/standards/{bot_kind}.md` registry doc
(cross-named by `.github/workflows/pr-agent.yml`): `coderabbitai` (coderabbit.md), `sourcery-ai`
(sourcery.md), `cuioss-review-bot` (pr-agent.md).

| Reviewer (`author_login`) | Verdict | Body evidence / reason |
|---|---|---|
| `cuioss-review-bot` | `reviewed` | Published a "PR Reviewer Guide 🔍" review artifact over the diff: "🧪 PR contains tests · 🔒 No security concerns identified · ⚡ No major issues detected" — an explicit nothing-to-report over this diff (issue-comment #5284248810; `review / review` check success). |
| `coderabbitai` | `rate-limited` | Published only a refusal notice ("Review limit reached … Next review available in: 74 minutes"), not a review (issue-comment #5284240965). |
| `sourcery-ai` | `rate-limited` | Published only a refusal notice ("you have reached your weekly rate limit of 500000 diff characters"), not a review (review #4929898432; `Sourcery review` check skipped). |

**Coverage: 1 of 3 reviewed.** The § Step 8 condition-4 shortfall disclosure fired: coverage is 1-of-3
— `cuioss-review-bot` reviewed (no issues); `coderabbitai` rate-limited (window reopens ~74 min);
`sourcery-ai` rate-limited (weekly quota). Per the lane this is a disclosure, not a merge block — rate
limits are routine and outside our control — so the run discloses the shortfall and arms auto-merge on
the same conditions full coverage would.

## Cost

- **Tokens:** verification sub-agent (3 rounds) ≈ 531k output tokens (144,942 + 177,185 + 209,348, from
  the sub-agent usage records). The **main Claude Code cloud session's** own token total is **not
  available to the agent in this session** (the harness does not surface it here) — stated plainly
  rather than estimated.
- **Wall-clock:** ≈ from the first plan-directory commit to auto-merge arm on 2026-08-13, roughly
  1.5–2 h of session wall-clock (source: git commit timestamps and the PR event times 17:38–17:52 UTC).
- **Population:** this single Claude Code cloud session's usage as the harness/sub-agent records count
  it. ⛔ **NOT comparable** to a plan-marshall `metrics.toon` total — that counts the orchestrator +
  per-task dispatch tree under plan-marshall's own per-task billing boundary, which a single
  interactive cloud session does not share. No parity figure is presented.

## Contract check (Step 9)

Re-read the `cloud-plan-lane` skill; per-step verdict against what actually happened:

| Step | Verdict | Artifact |
|---|---|---|
| 1 Skills loaded | done | named in "Skills loaded" (all obtained via bundle path — the `plan-marshall` plugin was not assumed present) |
| 2 Branch | done | `claude/post-run-guard-exempts-plans-q4if33` exists on `origin` — **harness-assigned** form, kept as-is; pushed before any work |
| 3 Plan directory | done | `doc/plans/truthful-signals/330-…/plan.md` exists and opens with the first-instruction block (present in the handed plan; not repaired) |
| 4 Implement | done | commits carry the `Co-Authored-By: Claude` trailer; all deliverables addressed |
| 4 Per-commit gate | done | every `*.py`-touching commit preceded by a clean `./pw quality-gate` (`issues[0]`, coverage COMPLETE) |
| 4 Pushed | done | every commit pushed; no `ahead` remains |
| 5 Build gate | done | Python changed → full path; `./pw verify` SUCCESS (19515 passed, 0 failed) |
| 6 Verification sub-agent | done | findings + dispositions recorded (§ Findings); iterated to a clean verdict over 3 rounds |
| 7 PR cycle | done | PR #1217 open; every comment dispositioned; all three comment surfaces read |
| 8 Merge gate | done | conditions 1–3 met, coverage shortfall disclosed (cond. 4), auto-merge armed; landing delegated to the merge queue |
| 8 Bridge | done | no status/bookkeeping write landed under `doc/plans/` outside this plan's own directory; report carries PR # and per-deliverable outcome |
| 9 This check | done | this table |
| 9 What have we learned | done | below |

**GitHub access path used:** the **GitHub MCP server** (cloud path; `gh` CLI not used). **Branch form:**
harness-assigned `claude/*`. A `/sync-plugin-cache` is **not owed** by this cloud run (machine-local
build step). One local sync IS owed on a developer machine that wants the edited `marketplace/bundles/`
reflected in its plugin cache — recorded here as a note, not a debt of this run.

## What have we learned (Step 9)

**No contract change proposed.** Every `cloud-plan-lane` step was executable as written and produced its
named artifact; nothing was ambiguous in practice, no command failed in the actual environment, and no
step proved unnecessary. The one multi-round event — the verification sub-agent needing three sweeps to
converge on all seven stale restatements of the changed value — is the contract's Step 6 rule
("a verification pass that found a defect has not finished") operating **correctly**, not a gap in it;
the run followed that mandate to a clean pass. (A minor operational note, not a contract change: ambient
`pytest` installed for fast iteration gave both a false failure and a hidden pass that `./pw verify`
corrected — reinforcing the contract's existing insistence that `./pw verify` is the authoritative gate;
no wording change is warranted.) This run examined the contract and found nothing to change.

## Residue

- **D4 durable remedy is an open proposal** (§ "Contract / lifecycle proposal (D4)"): the push-path /
  classification for a legitimately-owed post-merge tracked `.plan/` enrich write is a finalize-lifecycle
  decision for the operator. Not blocking (the fixed guard creates no recurring block in the current
  flow); it belongs to the architecture-enrich surface, out of scope for the guard fix.
- **Two external reviewers were rate-limited** (`coderabbitai` ~74 min, `sourcery-ai` weekly quota). If a
  fuller external review is wanted, re-request once the windows reopen (`@coderabbitai review`) — the
  code already carries `cuioss-review-bot`'s clean review.
- **Local plugin-cache sync owed on a developer machine** that edits `marketplace/bundles/` (not a debt
  of this cloud run).
