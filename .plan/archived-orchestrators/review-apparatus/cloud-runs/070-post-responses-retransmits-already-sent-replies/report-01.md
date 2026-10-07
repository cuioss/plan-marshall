# Run report — 070-post-responses-retransmits-already-sent-replies (run 01)

**Date (UTC):** 2026-08-12    **Branch:** `claude/post-responses-retransmits-qflwby` (harness-assigned)    **PR:** [#1187](https://github.com/cuioss/plan-marshall/pull/1187)    **Outcome:** completed (auto-merge armed; landing via the merge queue)

**Commits:** `4b4fb58` (fix) · `b0ac64d` (pre-PR verification-finding fixes) · report commits

## Skills loaded

Loaded by reading the bundle source path (the `plan-marshall` plugin route was not attempted; the path route always works in a fresh clone):

- `plan-marshall:ref-code-quality` (always)
- `pm-plugin-development:plugin-script-architecture` (always)
- `pm-dev-python:python-core` (Python production code)
- `pm-dev-python:pytest-testing` (Python tests)
- `plan-marshall:persona-implementer` (production-code work identity)
- `plan-marshall:ref-workflow-architecture` (workflow docs — `verification-feedback.md`)

## Deliverables

### D0 — GATE: consumer derivation of the returned count (mutates nothing)

**Absence confirmed once (settled, not re-litigated):** `cmd_post_responses`
(`github_pr.py:1485–1596`) selects a finding on `resolution in _RESPONDABLE_RESOLUTIONS`
AND `pr_number == this PR` AND non-empty `resolution_detail`. There is **no
prior-transmission term** in the predicate; `responded` at `github_pr.py:1593` is a
local output accumulator built fresh each call, not a persisted per-finding marker. A
round-1 reply therefore re-qualifies in round 2. Confirmed by reading the predicate, not
the docstring.

**Consumer derivation — method:** grep the whole repository tree (excluding `doc/plans/`)
for the literal field name `count_responded`; then trace (a) the sole production invoker
of `github_pr post_responses` and what it reads from the return, and (b) the plan-named
suspect (the review-retrospective) against its actual data source. Not a hand-list — every
hit enumerated and classified.

**Derived consumer set of the returned `count_responded` — size 0 in production:**

| Reader | What it reads | Consumes `count_responded`? |
|---|---|---|
| `verification-feedback.md` Step 8 (sole production invoker) | the return's `status` + `count_untransmitted` (line 252) | **No** |
| `finalize-step-review-retrospective` `review_retrospective.py` | each finding's `resolution` field via `manage-findings` (`review_retrospective.py:276`); `pct_resolved_as_fixed` numerator/denominator are `resolution`-bucket counts | **No** — different data path (the finding `resolution` family, not the post_responses return) |
| test assertions (github/gitlab/sonar test files) | `result['count_responded']` | Yes — tests only |

**Producers (3):** `github_pr.py:1590`, `gitlab_pr.py:410`, `sonar.py:774`.
**Production readers of the field: none.** The field is read only by test assertions and
surfaced in the operator-facing TOON.

**GATE verdict: PASSES (does not halt).** The consumer set is *derivable* and is *known*
(empty in production) — not "unknown," which is the only halt condition. The plan's
premise that the review-retrospective's %-resolved is "computed from this family of counts"
is **refuted by derivation**: it is computed from the finding `resolution` field, which
`post_responses` does not alter, so narrowing/renaming `count_responded` cannot move the
retrospective's numbers. This resolves the "consumer set of the count" HYPOTHESIS and the
"retrospective is not the only reader" caution: the retrospective is *not a reader of the
count at all*.

**Cross-provider sweep (the out-of-scope population, named):** the same
local-accumulator-without-marker shape exists in `gitlab_pr.py` (`responded` accumulator at
line 413, no `mark_finding_responded` import, no `finding.get('responded')` skip). Sonar
(`sonar.py`) is the reference that gets it right. **Population = {github (fixed here),
gitlab (same defect, NOT fixed — out of scope), sonar (reference)}.** The GitLab fix is a
separate change on a different provider surface and was deliberately not made in this run.

### D1 — idempotent transmission per (thread, disposition)

Design (copy the Sonar reference; predicate stays `terminal AND NOT responded`):

- `github_pr.cmd_post_responses`: import `mark_finding_responded`; skip a finding carrying
  `finding.get('responded')` (recorded in `skipped` with reason `already responded`, exactly
  as Sonar); call `mark_finding_responded(plan_id, hash_id)` in the **same unit of work** that
  transmits — right after a successful thread-reply+resolve, and for the batch after the batch
  post succeeds.
- **The "key, not suppression" half lives in `_findings_core.resolve_finding`:** the plain
  boolean marker suppresses forever unless something invalidates it. A disposition changes via
  `resolve_finding`; so `resolve_finding` clears `responded`/`responded_at` **when (and only
  when) the resolution or a supplied detail differs from what is stored**. An unchanged
  re-resolve (idempotent no-op) leaves the marker — and its already-sent reply — intact. This
  keeps ONE cross-provider vocabulary (the boolean marker), makes the key `(finding,
  disposition)`, and gives Sonar the same changed-disposition correctness for free without
  touching `sonar.py` (which the plan holds read-only).

**Surface note (beyond the plan's "Expected surface"):** D1 requires editing
`manage-findings/_findings_core.py::resolve_finding`. This is the minimal, necessary
consequence of combining the plan-specified plain-boolean predicate with D1's
"changed-disposition-still-transmits" requirement; the alternative (a github-local compound
marker) would ship a second vocabulary, which the plan forbids. Flagged here for the
verification sub-agent and reviewers.

### D2 — the count reports what it names

After D1, `count_responded` counts only dispositions transmitted **this round** (already-sent
ones are skipped), so its name now matches its content. Already-satisfied findings are
distinguished from newly-transmitted ones by living in `skipped[]` with reason
`already responded` (identical to Sonar's vocabulary) — no new count field is added, keeping a
single vocabulary across providers. D0 shows **no production consumer** to migrate, so this is
a correctness restoration, not a silent redefinition of a field with live readers; the test
assertions are updated to the corrected semantics.

### D3 — tests (each verified to FAIL pre-fix, proven discriminating)

Three tests added to `test/plan-marshall/workflow-integration-github/test_github_pr.py` (commit
`4b4fb58`), each verified RED against the unfixed code, then GREEN after the fix:

| Test | Pre-fix (RED) | Post-fix (GREEN) | Discriminates |
|---|---|---|---|
| `test_post_responses_second_round_transmits_only_newly_resolved_dispositions` (a) | `count_responded == 7` | `== 3` | the missing skip |
| `test_post_responses_retransmits_a_changed_disposition` (b) | unchanged re-run `== 1` | `== 0`, changed `== 1` | both the marker AND the `resolve_finding` clear |
| `test_post_responses_count_responded_names_this_rounds_transmits` (c) | `count_responded == 6` | `== 1` | the count naming its content |

All use the real persisted store (`plan_context`), so the `responded` marker round-trips through
disk exactly as production would. Pre-fix failure values (7, 1, 6) are the literal defect. D3(c)
adapts `_dispatch_roster.py`'s "derive → assert non-empty → cover each" discipline to the return's
count-field family, because D0 proved the *external* consumer roster empty (a source-scan guard would
be brittle against legitimate documentation mentions of the field name).

Commit `b0ac64d` (verification-finding fixes) added four more tests:
`test_post_responses_thread_reply_path_is_idempotent_across_rounds` (the thread-reply marker path,
by round-trip rather than inspection), and three `_findings_core` marker-lifecycle unit tests in
`test_findings_store.py` — clear-on-change, preserve-on-noop-reresolve, and the bulk-resolve clear.

## Build gate

`git diff --name-only origin/main...HEAD -- '*.py'` → non-empty (`github_pr.py`, `_findings_core.py`,
`test_github_pr.py`), so the full build ran.

- Per-commit quality gate (`./pw quality-gate`): `ruff … All checks passed!`, `mypy … Success: no
  issues found in 395 source files`, `SPDX-header check passed`, `status: pass`, `total_issues: 0`.
- Full verify (`./pw verify`): **`=== verify: SUCCESS ===`** — 19234 passed then 19238 passed (after
  the GAP-fix tests), 14 skipped, ~6–7 min each. The marketplace-wide plugin-doctor rule
  (`test_real_marketplace_quality_gate_has_zero_findings`) passed, which lints the edited `SKILL.md`
  frontmatter, workflow-doc prose, and relative links.

## Findings

| # | Source | Description | Disposition |
|---|---|---|---|
| 1 | Pre-PR sub-agent (D0) | Independently re-derived: `count_responded` has zero production readers; retrospective refuted as a reader. | Confirmed the run's D0. No action. |
| 2 | Pre-PR sub-agent (D1) | Marker pattern + change-detection truthiness (`bool(detail)` guard) correct; matches Sonar. | No action. |
| 3 | Pre-PR sub-agent (GAP-1) | `verification-feedback.md` Step 8 idempotency claim over-reached to GitLab (whose verb has no marker). | **Fixed** in `b0ac64d` — claim scoped to GitHub/Sonar; GitLab's current behaviour stated. |
| 4 | Pre-PR sub-agent (GAP-2) | `resolve_findings_by_type` (bulk) did not clear the marker on change, unlike `resolve_finding` — latent, not reachable by any current caller. | **Fixed** in `b0ac64d` — bulk path mirrors the clear; covered by a new unit test. |
| 5 | Pre-PR sub-agent (GAP-3) | All D3 tests used the batched path; the thread-reply marker was proven by inspection only. | **Fixed** in `b0ac64d` — added a thread-reply idempotency round-trip test. |
| 6 | Pre-PR sub-agent (cold read) | Cold read of the corrected prose answers "twice ⇒ nothing re-sent, count 0; changed ⇒ re-sent" correctly. | Pass. No action. |
| 7 | CI | `verify` (required), `verify / gate`, `review / review`, `dependency-review`, `generate-check` all green on head; local `./pw verify` green. | No action. |
| 8 | PR review — `cuioss-review-bot` | "PR contains tests / No security concerns identified / No major issues detected." | Clean review, no actionable findings. No action. |
| 9 | PR review — `coderabbitai` | Posted only "Review limit reached" (window reopens ~36 min). | Rate-limited; not a review finding. No reply owed. |
| 10 | PR review — `sourcery-ai` | Posted only "weekly rate limit of 500000 diff characters". | Rate-limited; not a review finding. No reply owed. |

No actionable review comment was left unaddressed on any of the three PR comment surfaces
(`get_comments`, `get_reviews`, `get_review_comments` — the last empty).

## Reviewer participation

Population derived from the registry — the `author_login` of each
`marketplace/bundles/plan-marshall/skills/automatic-review/standards/{bot_kind}.md`
(`coderabbit.md`, `pr-agent.md`, `sourcery.md`), cross-named by `.github/workflows/pr-agent.yml`.

| Reviewer (`author_login`) | Verdict | Body evidence |
|---|---|---|
| `cuioss-review-bot` | `reviewed` | Posted the "PR Reviewer Guide" review body over the diff: tests present, no security concerns, no major issues — an explicit clean verdict. |
| `coderabbitai` | `rate-limited` | Posted only "Review limit reached … Next review available in: 36 minutes" — engaged, did not review this diff. |
| `sourcery-ai` | `rate-limited` | Posted only "you have reached your weekly rate limit of 500000 diff characters" — engaged, did not review. |

**Coverage: 1 of 3.** The § Step 8 shortfall disclosure fired: "Review coverage 1 of 3 —
`cuioss-review-bot` reviewed (clean); `coderabbitai` rate-limited (window reopens ~36 min);
`sourcery-ai` rate-limited (weekly quota)." Per the contract this is a disclosure, not a merge block:
rate limits are routine and outside our control, so the run proceeds on the disclosed partial
coverage.

## Cost

- **Tokens:** not available to the agent in this session (the Claude Code cloud harness does not
  surface a per-session token count to the model). One pre-PR verification sub-agent was dispatched
  (its own transcript reported ~95k subagent tokens, 32 tool uses, ~318s).
- **Wall-clock:** roughly one interactive session; two full `./pw verify` runs (~6–7 min each) plus
  the sub-agent (~5 min) dominate.
- **Population:** these figures count this single Claude Code cloud session's activity as the harness
  reports it. ⛔ NOT comparable to a plan-marshall `metrics.toon` total, which counts an
  orchestrator-plus-agent dispatch tree under plan-marshall's own per-task billing boundary — a
  boundary a single interactive cloud session does not share. No parity is implied or computable here.

## Contract check (Step 9)

| Step | Verdict | Evidence |
|---|---|---|
| 1 Skills loaded | done | Six skills named in § Skills loaded, read by bundle path. |
| 2 Branch | done | Harness-assigned `claude/post-responses-retransmits-qflwby`, pushed to `origin` before any edit. |
| 3 Plan directory | done | `doc/plans/review-apparatus/070-…/plan.md` exists and opens with the first-instruction block. |
| 4 Implement | done | Deliverables addressed; commits carry the `Co-Authored-By: Claude` trailer, no "Generated with" footer. |
| 4 Per-commit gate | done | Both `*.py`-touching commits preceded by a clean `./pw quality-gate` (ruff/mypy/SPDX all reported clean). |
| 4 Pushed | done | No unpushed commit — every commit pushed immediately. |
| 5 Build gate | done | Python changed → full `./pw verify`, `=== verify: SUCCESS ===` (both runs). |
| 6 Verification sub-agent | done | Dispatched; findings + dispositions in § Findings (rows 1–6); three gaps fixed and re-verified. |
| 7 PR cycle | done | PR [#1187](https://github.com/cuioss/plan-marshall/pull/1187); all three comment surfaces read; every comment dispositioned. |
| 8 Merge gate | done at finalize | Conditions 1–3 met; 1-of-3 coverage disclosed (condition 4); auto-merge armed (recorded to operator, below). |
| 8 Bridge | done | No status/bookkeeping write outside this plan's own directory; report carries PR number + per-deliverable outcome. |
| 9 This check | done | This table. |
| 9 What have we learned | done | Below. |

GitHub access path used: **GitHub MCP server** (cloud path). Branch form: **harness-assigned**
(`claude/*`). A cloud run owes **no** `/sync-plugin-cache` (machine-local build step).

## What have we learned (Step 9)

**No contract change proposed.** The `cloud-plan-lane` contract fit this run end to end with no
ambiguity that produced a wrong or unproducible artifact: skill loading by bundle path worked, the
build gate and per-commit gate behaved as written, the three comment surfaces each returned distinct
content (the review-summary surface held `sourcery-ai`'s rate-limit review — exactly the surface the
contract warns is easy to miss), and the 1-of-3 disclosure path applied cleanly. The one deviation
this run made — expanding the edit surface into `_findings_core.py`, which the plan's "Expected
surface" did not list — was forced by the plan's own D1/D3(b) requirements, not by a gap in the
contract, and the contract already prescribes exactly how to handle it (record the surface expansion,
have the sub-agent judge it). Nothing this run encountered is evidence for a contract edit.

## Residue

- GitLab (`gitlab_pr.py`) carries the identical re-transmission defect and was left unfixed
  (out of scope; population named in D0). A follow-up plan should apply the same Sonar-pattern
  fix there.
