# Run report — 070-post-responses-retransmits-already-sent-replies (run 01)

**Date (UTC):** 2026-08-12    **Branch:** `claude/post-responses-retransmits-qflwby` (harness-assigned)    **PR:** TBD    **Outcome:** in progress

**Fix commit:** `4b4fb58` (`fix(review-apparatus): make post_responses idempotent per (finding, disposition)`)

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

## Build gate

`git diff --name-only origin/main...HEAD -- '*.py'` → non-empty (`github_pr.py`, `_findings_core.py`,
`test_github_pr.py`), so the full build ran.

- Per-commit quality gate (`./pw quality-gate`): `ruff … All checks passed!`, `mypy … Success: no
  issues found in 395 source files`, `SPDX-header check passed`, `status: pass`, `total_issues: 0`.
- Full verify (`./pw verify`): **`=== verify: SUCCESS ===`** — 19234 passed, 14 skipped in 423s. The
  marketplace-wide plugin-doctor rule (`test_real_marketplace_quality_gate_has_zero_findings`) passed,
  which lints the edited `SKILL.md` frontmatter, workflow-doc prose, and relative links.

## Findings

Pending — verification sub-agent, CI, PR review.

## Reviewer participation

Pending.

## Cost

Recorded at close.

## Contract check (Step 9)

Pending.

## What have we learned (Step 9)

Pending.

## Residue

- GitLab (`gitlab_pr.py`) carries the identical re-transmission defect and was left unfixed
  (out of scope; population named in D0). A follow-up plan should apply the same Sonar-pattern
  fix there.
