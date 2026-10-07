# Run report — 110-participation-derived-from-a-lossy-view (run 01)

**Date (UTC):** 2026-08-13    **Branch:** `claude/participation-lossy-view-sqtb8u` (harness-assigned, kept as-is)    **PR:** [#1219](https://github.com/cuioss/plan-marshall/pull/1219)    **Outcome:** completed — landing delegated (auto-merge armed SQUASH; `verify` finishing on the final head)

## Skills loaded

- `cloud-plan-lane` (the working contract; loaded first)
- `plan-marshall:ref-code-quality` (read from bundle path)
- `pm-plugin-development:plugin-script-architecture` (read from bundle path)
- `pm-dev-python:python-core` (Python production code / tests)
- `pm-dev-python:pytest-testing` (Python tests — the surface this run touches)

All obtained by the bundle-path route; none unreachable. `persona-implementer` not loaded — this run
writes no production code (see D0/D1/D2 below), only a test.

## Headline

**Both defects this plan was written to fix are REFUTED at HEAD — they were already fixed by the merged
sibling plan `010-participation-credited-from-a-superseded-commit` (PR #1141, MERGED, squash
`50f67ed`).** That plan is the "currency plan" the cross-plan collision section anticipated. The
SHA-anchored, idempotent participation predicate this plan's D1 was to build already exists as
`github_pr.py` § `_reviewed_at_merge_candidate`, and the storage-dedup decoupling this plan's D2 was to
make already holds (participation is derived from the raw comment scan + the currency ledger, *before*
and *independent of* the storage dedup). The plan therefore does **not** HALT (the consumer population
is derivable), and it produces the one genuinely-missing regression guard (D3(a)) plus an honest
accounting of what is already covered.

## Deliverables

### D0 — GATE: re-establish both defects at HEAD + derive the consumer population

**Re-grounded every symbol at HEAD (line numbers navigational only). Verdict: both defects REFUTED.**

**Defect 1 — "a storage dedup empties the set the barrier is fed" — REFUTED.**
In `github_pr.cmd_fetch_findings`, participation is derived in a dedicated loop (the `participated` /
`stale_participation` dicts) over `raw_comments` *before any noise / duplicate / resolved filtering*
(the in-source comment says exactly this). The storage dedup (`existing_comment_keys`, keyed
`(bot_kind, comment_id)`) is consulted **only** in the separate finding-storage loop
(`if (bot_kind or '', comment_id) in existing_comment_keys: skipped_duplicate += 1; continue`). The two
never share an input: participation reads the scan + the currency ledger; the dedup gates only whether a
`pr-comment` finding is *filed*. A storage-hygiene change to the dedup cannot empty `participated_bots`.

**Defect 2 — "proven participation is not re-credited across FIND calls" — REFUTED.**
For a `participation_requires_update` bot the credit is `_reviewed_at_merge_candidate`, a **pure SHA
comparison** against the current PR HEAD read from the plan-scoped currency ledger
(`_recorded_currency_records`). Its own docstring: *"the verdict is a PURE COMPARISON that consumes no
observation state — so it is identical however many times it is evaluated."* Re-running the fetch at the
same HEAD returns the same answer (SHA-currency arm); advancing HEAD with no fresh edit resets the credit
to `participated_stale`. This is verbatim the D1 mechanism this plan specified.

**The consumer population, classified (D0's required table).**

`participated_bots` / participation-verdict chain:

| # | Site | Reads | Class |
|---|------|-------|-------|
| C1 | `github_pr.cmd_fetch_findings` | the raw comment **scan** ∪ the currency **ledger** | **PRODUCER** — not a deduped projection |
| C2 | `automatic-review/SKILL.md` FIND step → `review_completeness check --participated-bots` | the producer's `participated_bots` set | consumer of the producer set |
| C3 | `branch-cleanup.md` Pre-Merge Review-Completeness Barrier → `review_completeness check` | the producer's `participated_bots` (retained from the barrier's own `fetch_findings` re-run) | consumer of the producer set |
| C4 | `review_completeness.check_completeness` (`review_completeness.py:312`) | the `--participated-bots` input, tested for membership in `participation_evidence(bot)` (the **LIST**) | quorum consumer |

**None of C2–C4 reads a deduped projection.** Every consumer downstream of the producer reads the
currency-anchored `participated_bots` the producer emits. `branch-cleanup.md` line 784 retains
`participated_bots` / `stale_participation_bots` / `refused_bots` from its own `fetch_findings` re-run
and feeds them to `review_completeness check` — it does **not** feed a stored/deduped set.

`participation_evidence(bot)` consumers, classified LIST vs FIRST-ELEMENT (`[0]`) — the ordering
dependency D0 requires be classified:

| Site | Reads | Kind |
|------|-------|------|
| `github_pr.py:929` | `_kind not in participation_evidence(_bot_kind)` | **LIST** (membership) — production |
| `review_completeness.py:312` | `evidence_kind in participation_evidence(bot_kind)` | **LIST** (membership) — production |
| `_github_pr.py:400` | `all(not participation_evidence(bot_kind) …)` | **LIST** (emptiness) — production |
| `test_github_pr.py:2370` (`_publish_comment` helper) | `participation_evidence(bot_kind)[0]` | FIRST-ELEMENT — **test fixture** |
| `test_pre_merge_barrier.py:739` | `participation_evidence('pr-agent')[0]` | FIRST-ELEMENT — **test fixture** |
| `test_bot_participation_contract.py:650` | `participation_evidence(bot)[0]` | FIRST-ELEMENT — **test fixture** |
| `test_legacy_bot_list_migration.py:137` | `participation_evidence(other)[0]` | FIRST-ELEMENT — **test fixture** |
| `test_bot_participation_contract.py:700` | `shapes = participation_evidence(bot)` | LIST (vocabulary/emptiness) — test |

**Ordering finding, stated honestly:** every FIRST-ELEMENT (`[0]`) reader is a **test fixture** that
synthesizes "a comment in a shape this bot really publishes"; **no production participation decision
reads `[0]`** — all three production consumers test LIST membership/emptiness, which is
order-independent. So reordering `participation_evidence` would re-point the test fixtures (silently,
as the plan warned) but would **not** silently re-point any production verdict. The D2 "cover the
ordering dependency too" concern therefore has **no production coupling to decouple** — the ordering
dependency lives entirely in test-fixture convention, and the appropriate response is the append-only
convention already in force, not a production change. Recorded rather than acted on.

**Cross-plan collision — resolved.** The plan warned not to blind-port `_has_update_movement`, and to
take the SHA-anchored predicate "the currency plan is building … If that plan has not landed, say so and
record which predicate was adopted." **The currency plan (010) HAS landed (PR #1141).** `_has_update_movement`
no longer exists — it was replaced by `_reviewed_at_merge_candidate` (the SHA-anchored, idempotent
predicate). There is nothing to port: the correct predicate is already the one in place. Adopted
predicate: `_reviewed_at_merge_candidate` (SHA-currency arm + guarded first-observation arm + edit-movement
arm against the recorded `updated_at`).

**Gate verdict: consumer population derived from the tree (grep + producer→consumer call graph + registry);
both defects refuted; the plan PROCEEDS (does not halt).**

### D1 — participation monotonic within a finalize run for a fixed head SHA

**Already satisfied at HEAD by #1141; no production change.** `_reviewed_at_merge_candidate` credits a
proven bot on call 2 at an unchanged HEAD (SHA-currency arm) and resets the credit when the SHA advances.
Derived from the ledger ∪ the current scan; no new persisted field. Per-bot trigger semantics are already
registry data (`participation_requires_update`, `trigger_comment`, `rate_limit_class`). *Done-when*
verified by existing tests: `test_second_fetch_at_the_same_head_stays_participated` (call-2 credit at
unchanged HEAD) and `test_review_predating_the_merge_candidate_is_stale` (SHA-advance reset).

### D2 — storage dedup decoupled from the participation predicate

**Already satisfied at HEAD by #1141; no production change.** The participation predicate's input is the
scan + the durable currency ledger, not the storage dedup (which keys `(bot_kind, comment_id)` for
*finding-filing* only). The identity used for "seen this review" is stated explicitly in-source: the
currency ledger records `(reviewed_commit_sha, updated_at)` per credited comment, and the dedup's
`(bot_kind, comment_id)` answers the *different* question "was this already STAGED as a finding?" The one
uncovered property — that a comment **deduped on storage is still credited** — is closed by D3(a) below.

### D3 — tests

- **(a) deduped-but-still-credited — ADDED (the one genuine gap).** New test in `test_github_pr.py`
  asserting that on a re-fetch where every comment is dropped by the storage dedup
  (`count_skipped_duplicate == len(_COMMENTS)`), `participated_bots` is unchanged and non-empty — the
  storage dedup does not empty the participation set. Asserts against the **existing** `skipped_duplicate`
  counter (per Verification), no new instrumentation. Mutation-proven (below).
- **(b) call-1→call-2 credit at unchanged HEAD — ALREADY COVERED** by
  `test_second_fetch_at_the_same_head_stays_participated` (#1141).
- **(c) SHA-advance resets credit — ALREADY COVERED** by `test_review_predating_the_merge_candidate_is_stale`
  and `test_edit_at_one_commit_does_not_credit_a_later_commit` (#1141).
- **(d) consumer population + refusal fixture — ALREADY COVERED.** Consumer/currency population:
  `test_at_least_one_registered_bot_requires_update_movement`, `test_currency_anchor_is_recorded_in_the_ledger_on_credit`,
  and the `_registered_bots()`-derived taxonomy sweep in `test_bot_participation_contract.py`. Population-derived
  refusal fixture: `test_refusal_recovery_arming.py` § `test_every_registered_bots_refusal_is_detected`
  and `test_a_bots_declared_refusal_is_recognized_as_DATA` — both swept over `_registered_bots()` with a
  non-empty guard (`_registered_bots` asserts the population is non-empty; parametrization publishes it).

## Population sizes (Verification requires publishing these)

- **Consumer population of `participated_bots` / participation verdict:** 4 sites (1 producer + 3 consumers);
  0 read a deduped projection. `participation_evidence` consumers: 3 production (all LIST) + 5 test (4 FIRST-ELEMENT
  fixtures + 1 LIST). Derivation: `Grep participated_bots|participation_evidence` over `*.py` + producer→consumer
  call-graph from `fetch_findings`' return keys + `branch-cleanup.md`/`SKILL.md` barrier call sites.
- **Refusal-pattern population:** 3 registered bots (`coderabbit`, `pr-agent`, `sourcery`); declared
  `refusal_patterns` total = 3 (coderabbit 1, sourcery 2, pr-agent 0 — fail-closed). Population is
  derived from `bot_registry.bot_kinds()`, non-empty-guarded in `_registered_bots()`. `count: 3` verified
  by reading the three `automatic-review/standards/{bot_kind}.md` registry docs.

## Build gate

`git diff --name-only origin/main...HEAD -- '*.py'` is **non-empty** (one test file:
`test/plan-marshall/workflow-integration-github/test_github_pr.py`), so the full `./pw verify` ran.
Result: **`=== verify: SUCCESS ===`, 19606 passed, 14 skipped, 0 failed** — mypy(production) [398 files],
ruff [marketplace/bundles, test, .claude], SPDX headers, plugin-doctor [marketplace-wide], mypy(test)
[733 files], whole-tree pytest. `UV_HTTP_TIMEOUT=600` and `UV_PYTHON=3.12` set on the call (session
interpreter is 3.12, at the project floor, so no `uv.lock` churn — verified by `git status`).

**Mutation proof for the D3(a) test (Verification requires discrimination by mutation).** Temporarily
re-coupled participation to the storage dedup (added `if (bot_kind, id) in existing_comment_keys:
continue` to the participation loop in `github_pr.py`). The new test then FAILED exactly at the
decoupling assertion — the second fetch's `participated_bots` collapsed to `[]` (the original defect,
reproduced) against the first fetch's 3 bots. Mutation reverted; `git diff --stat` confirms only the
test file changed.

## Findings

### Verification sub-agent (Step 6)

An independent `general-purpose` sub-agent verified the diff against the plan (read-only). It read the
production code **cold** before consulting the report's conclusions and **independently confirmed the
entire D0 refutation** — no gaps, no live defect:

1. **Both defects genuinely refuted at HEAD.** Participation (`participated`/`stale_participation` loop,
   `github_pr.py:917–951`) never touches `existing_comment_keys`; the dedup is consulted only at the
   finding-storage site (`:1062`). `_reviewed_at_merge_candidate` is a pure, idempotent SHA comparison.
   `branch-cleanup.md` feeds the producer's currency-anchored set. `_has_update_movement` is absent from
   the tree (grep-clean) — replaced, nothing to port.
2. **The mandated cold read.** Its verbatim answer: participation is decided **in CODE, not in a reader's
   interpretation of a standards document** — evidence shapes are registry *data* consumed by code, the
   currency test is a code predicate, the quorum re-tests membership in code. "The enforcement HAS moved
   to code (it moved with #1141)." This is the plan's central success criterion, met.
3. **The D3(a) test is correct and discriminating** — asserts both observables on one fetch, uses the
   existing `skipped_duplicate` counter, and would fail if participation were re-coupled to the dedup.
4. **D3(b),(c),(d) genuinely covered** by the named pre-existing tests (each confirmed to exist and
   assert what the report claims). One path clarification (not a gap): the taxonomy sweep lives at
   `test/plan-marshall/automatic-review/test_bot_participation_contract.py`; the report cited it by
   basename.
5. **No production change, no stale claims** — `git diff --name-status` is exactly the rename + report +
   test; the report's factual claims (pr-agent sole `requires_update`, 3 registered bots, 3 refusal
   patterns, no production `[0]` reader) all match the tree.
6. **The report does not overstate** — it credits the production fix to #1141 and frames this run as
   adding a test.

**Disposition: no findings to fix.** The two items the agent flagged as un-verifiable from code alone —
the empirical `./pw verify` result and #1141's specific squash SHA / MERGED status — were verified
directly by this run (build: `=== verify: SUCCESS ===`; #1141 MERGED squash `50f67ed`, read from plan
010's `report-01.md`). No re-dispatch needed.

### CI / PR review

- **pr-agent (`cuioss-review-bot`, the required bot) — reviewed, no findings.** Posted its "PR Reviewer
  Guide 🔍": *🧪 PR contains tests · 🔒 No security concerns identified · ⚡ No major issues detected.* A
  review artifact against the diff with nothing actionable. **Disposition: nothing to fix.**
- **coderabbit / sourcery — refusals, not code feedback.** coderabbit posted "Review limit reached"
  (awaitable window, ~43 min); sourcery posted "reached your weekly rate limit of 500000 diff characters"
  (weekly quota). These are rate-limit notices, not comments about the code, so there is nothing to
  handle or reply to; recorded as `rate-limited` participation below.
- **Inline review threads:** none (`get_review_comments` → 0).
- **CI:** `verify / gate` success, `dependency-review` success, `review / review` (pr-agent) success.
  `verify / verify` — the required check — was `in_progress` at the merge gate (see Merge gate below).

No CI or PR-review finding required a code change.

## Merge gate

- **Condition 1 (required contexts green on the head):** the sole required check is `verify / verify`
  (per #1141's landing: `license/cla` and the bot reviews are NOT required). At the gate it was
  `in_progress` on the head. `verify / gate`, `dependency-review`, and `review / review` had all
  concluded `success`; `verify / verify` is the one still running.
- **Condition 2 (every comment handled):** met — two refusals (not code feedback) + one clean required-bot
  review, none actionable; no inline threads.
- **Condition 3 (report finalized + pushed as last pre-merge commit):** this report is committed as the
  final pre-merge commit before arming.
- **Condition 4 (coverage-shortfall disclosure):** fired — 1-of-3, both shortfalls optional rate-limited
  bots (see Reviewer participation). A disclosure, not a block.

**Disposition — arm-and-hand-off (no self-wake available).** `send_later` / `subscribe_pr_activity` are
absent in this session (the `claude-code-remote` MCP server is not connected) and Bash cannot poll
GitHub, so the session cannot reliably block-until-green. Per the lane's Step 8 carve-out — *"when there
is no self-wake AND a required check is still `in_progress` at the gate, arm anyway; the merge queue is
the enforcer"* — auto-merge is armed `SQUASH` after this commit. GitHub auto-merge holds the merge until
`verify / verify` concludes green on the final head, then lands it. **This is a completed run with the
landing delegated, not partial.** The squash merge commit is read from the PR merge event and reported to
the operator, not embedded here (it does not exist at commit time). Note: committing this report advances
the head, so it supersedes the in-flight `verify` and a fresh `verify` runs on the final head — that is
the run auto-merge waits on.

## Reviewer participation

Population derived from the registry `author_login` of each `automatic-review/standards/{bot_kind}.md`
(cross-named by `.github/workflows/pr-agent.yml`): `coderabbit`→`coderabbitai`,
`pr-agent`→`cuioss-review-bot`, `sourcery`→`sourcery-ai`. This repo's settled config makes **`pr-agent`
the sole REQUIRED bot** (`coderabbit`, `sourcery` optional). Verdicts from the stored comment bodies on
PR #1219:

| Reviewer (`author_login`) | Verdict | Body evidence / reason |
|---|---|---|
| `cuioss-review-bot` (pr-agent, **required**) | `reviewed` | Posted "PR Reviewer Guide 🔍" — "No major issues detected", "No security concerns identified", "PR contains tests": a review artifact against the diff, nothing actionable. |
| `coderabbitai` (coderabbit, optional) | `rate-limited` | Posted only "Review limit reached … Next review available in 43 minutes" (awaitable window). |
| `sourcery-ai` (sourcery, optional) | `rate-limited` | Posted only "you have reached your weekly rate limit of 500000 diff characters" (weekly quota). |

**Coverage: 1 of 3 reviewed; the REQUIRED bot (`pr-agent`) reviewed, so the required quorum is
satisfied.** The two optional bots are rate-limited (routine, outside our control; optional silence does
not block). **Step 8 shortfall disclosure fired:** "Review coverage 1 of 3 — `cuioss-review-bot`
(pr-agent, required) reviewed clean; `coderabbitai` rate-limited (awaitable window reopens ~43 min);
`sourcery-ai` rate-limited (weekly quota). Both shortfalls are OPTIONAL bots — the merge proceeds; the
disclosure changes what the run says, not whether it merges."

## Cost

- **Tokens:** not available to the agent in this session (the Claude Code cloud harness does not expose a
  per-run token total to the model).
- **Wall-clock:** ~1h from branch publish to PR open + review cycle (branch pushed ~20:0x UTC, PR opened
  20:19 UTC).
- **Population:** this single Claude Code cloud session's usage. ⛔ NOT comparable to a plan-marshall
  `metrics.toon` total, which counts the orchestrator-plus-agent dispatch tree under plan-marshall's
  per-task billing boundary — a boundary this interactive session does not share. No comparable figure is
  available, so none is presented.

## Contract check (Step 9)

| Step | Verdict |
|---|---|
| 1 Skills loaded | Done — five skills named above, all via the bundle-path route. |
| 2 Branch | Done — harness-assigned `claude/participation-lossy-view-sqtb8u`, kept as-is, on `origin` (pushed before any work). **Branch form: harness-assigned.** |
| 3 Plan directory | Done — `doc/plans/review-apparatus/110-…/plan.md` exists and opens with the first-instruction block (present on arrival; no repair needed). |
| 4 Implement | Done — one test deliverable; every commit carries the `Co-Authored-By: Claude` trailer, no "Generated with" footer. |
| 4 Per-commit gate | Done — the source-touching commit was covered by a clean full `./pw verify` (subsumes quality-gate). |
| 4 Pushed | Done — every commit pushed immediately; no unpushed commit remains. |
| 5 Build gate | Done — `*.py` changed (one test file) → full `./pw verify` → SUCCESS, 19606 passed / 14 skipped. |
| 6 Verification sub-agent | Done — independent agent confirmed the refutation cold; no findings to fix (§ Findings). |
| 7 PR cycle | Done — PR #1219; all three comment surfaces read; two refusals + one clean required-bot review, none actionable. |
| 8 Merge gate | See Merge gate below. |
| 8 Bridge | Nothing under `doc/plans/` outside this plan's own directory was changed; this report carries the PR number and per-deliverable outcome. |
| 9 This check | Appended here. |
| 9 What have we learned | Below. |

**GitHub access path:** the GitHub MCP server (the cloud path). **Branch form:** harness-assigned. A
cloud run **never owes** a `/sync-plugin-cache` — and this run touched no `marketplace/bundles/**` source
anyway (only a test and docs), so there is no cache debt of any kind.

## What have we learned (Step 9)

**One observation worth surfacing, recorded not shipped.** This run's substantive finding is that the
plan's target defects were already fixed by a sibling plan that landed first (#1141) — the "cross-plan
collision" the plan itself anticipated, resolved in the opposite direction. The cloud-plan-lane contract
handled this cleanly: D0 is a gate that re-establishes-or-refutes at HEAD, so "already fixed" is a
first-class outcome, not an error. **No contract change is proposed** — the lane's D0-gate framing, its
"a claim is not an outcome / re-derive at HEAD" rule, and the pre-PR cold-read all worked exactly as
written and are what caught that the production work was already done rather than re-doing it. The one
latent risk the run exposed (a plan whose production deliverable a sibling already landed) is already
covered by the plan template's own cross-plan-collision section and the D0 HALT/refute mechanics; nothing
in the *contract* needed to change to handle it. Recorded here as the run-produced evidence that the
existing contract was sufficient.

## Residue

- **None blocking.** The plan's production goal (participation read from artifacts + durable ledger,
  SHA-anchored, code-enforced) is met at HEAD by #1141; this run added the one uncovered regression guard
  and verified the rest. No follow-up owed.
- **Optional-bot re-review** (coderabbit/sourcery rate-limited) — routine, outside our control; both are
  optional so they do not block, and no re-trigger is warranted for a docs+test PR.
