# Run report — 150-configurable-display-timezone-for-rendered-timestamps (run 01)

**Date (UTC):** 2026-08-11    **Branch:** claude/configurable-display-timezone-6t3zs0 (harness-assigned)    **PR:** [#1172](https://github.com/cuioss/plan-marshall/pull/1172)    **Outcome:** completed (all D1–D5 delivered; CI green; auto-merge armed into the merge queue)

## Skills loaded

- `plan-marshall:ref-code-quality` (bundle path)
- `pm-plugin-development:plugin-script-architecture` (bundle path)
- `plan-marshall:persona-implementer` (bundle path — production-code work identity)
- `pm-dev-python:python-core` (bundle path — Python production code)
- `pm-dev-python:pytest-testing` (bundle path — Python tests)

All obtained by reading the bundle path (the `plan-marshall` plugin was not assumed present).

## Deliverables

### D1 — GATE: derive & classify the rendering surfaces
Population re-derived from the live tree via grep for
`datetime.now|utcnow|strftime|fromisoformat|astimezone|ZoneInfo|zoneinfo|.timestamp()|fromtimestamp`
over `marketplace/bundles/**/*.py`: **55 real call sites** (plus 2 docstring/comment mentions that
are not call sites). An independent Explore sub-agent enumerated the same surface and **confirmed
exactly two RENDER sites**; every other site is STORE or COMPARE, and it found no beyond-grep verbatim
ISO echoes into human text (inbox, status, logging, terminal title, resume summary, metrics.toon
serializer all checked). The lead figure ("~32 sites, zero naive calls") was re-derived; every
`datetime.now()` in the tree uses `datetime.now(UTC)` — the tree is fully converged onto UTC.

The classification is persisted as
`test/plan-marshall/manage-run-config/timestamp_render_classification.json` (the D4 guard is derived
over it). RENDER = 2 sites; STORE/COMPARE = the derived remainder. The lesson-identifier prefix
(doubles as a sort key) is correctly classified STORE and left untouched.

Commit: `68ede53`. Verified by `test_display_timezone_guard.py` (coverage + census).

### D2 — The knob
`display_timezone` top-level run-config field (IANA name, default `UTC`) with
`display-timezone get` / `set` subcommands in `run_config.py`. `set` validates the IANA name via
`zoneinfo.ZoneInfo` and returns an `invalid_value` error on an unknown zone. The default/unset path
resolves `UTC` without constructing a `ZoneInfo`, so the unset behaviour has **no tzdata dependency**
and is byte-identical to today. Commit `68ede53`. Verified by `test_display_timezone_knob.py` (9 tests,
including the slash-bearing IANA name driven through the CLI — the mandatory first boundary test for a
new input shape).

### D3 — Every rendered timestamp carries its zone label
`_display_time.render_timestamp(moment, body_fmt, utc_suffix, *, tz=None)` is the single conversion
surface. The UTC path returns `body + utc_suffix` (byte-identical to each caller's historical label);
the conversion path **always** appends `ABBREV (UTC±HH:MM)` — a structurally unavoidable, non-empty,
cold-read-recoverable label. The two RENDER sites (metrics.md `Generated:`, retrospective
`- generated:`) are routed through it. Commit `68ede53`. Verified by `test_display_time_render.py`.

### D4 — Guard that the knob cannot reach the write path
`test_display_timezone_guard.py` is **derived over D1's classification**: it re-scans the live tree,
treats STORE/COMPARE as the derived remainder (so a new site is STORE/COMPARE by default), publishes
the population it examined, and asserts every knob-consumer symbol
(`render_timestamp`, `resolve_display_timezone`, `read_display_timezone`, `display_timezone`) lives
only in a knob-owner or declared-RENDER file — never a STORE/COMPARE site. **Published population:**
33 time-bearing files — 2 RENDER, 2 owner, 29 STORE/COMPARE. Commit `68ede53`.

### D5 — Tests, each verified to FAIL pre-fix
All four hold and each was **seen red first** (implementation stashed via
`git stash push -u`, tests run → red, restored → green):
- (a) unset/UTC byte-identical for both routed formats — `test_utc_render_is_byte_identical_*`.
- (b) positive-offset zone (`Asia/Kolkata`, +05:30, no DST) converts `14:30:45`→`20:00:45` and carries
  `IST (UTC+05:30)` — `test_positive_offset_zone_converts_and_labels`.
- (c) stored timestamp is UTC under a non-UTC knob value — `test_stored_timestamp_is_utc_under_any_knob_value`.
- (d) render-site population derived and asserted non-empty — the guard's coverage/census test.

Red-first evidence: under the stash, `test_display_time_render.py` errored on the missing
`_display_time` module, the 8 display-timezone CLI tests failed (subcommand absent), and all 3 guard
tests failed. The one green pre-fix — `test_validate_accepts_config_with_display_timezone` — is a
forward-compatibility check (validate ignores unknown top-level keys), green by design and not a D5
safety test. After restore: **25 passed**.

## Build gate

`git diff --name-only origin/main...HEAD -- '*.py'` is non-empty (Python changed), so the build gate
took its full path. `./pw quality-gate` → `status: pass, total_issues: 0`, mypy clean (393 files),
ruff clean, SPDX clean, all 36 plugin-doctor rules 0 findings. `./pw verify plan-marshall` →
**15997 passed, 1 skipped** (~5 min), `verify: SUCCESS`. (All changed `*.py` are in the `plan-marshall`
bundle; the merge queue runs the full cross-bundle verify.)

## Findings

- **Self (pre-commit):** `test-compile` mypy flagged `test_display_timezone_guard.py:41`
  (`Returning Any` from `json.loads`) — **fixed** by annotating the local (`data: dict = ...`), commit
  `c442db1`. Re-verified green.
- **Verification sub-agent — F1 (stale prose): FIXED.**
  `plan-retrospective/references/report-structure.md:45` claimed the retrospective header `generated`
  value "is an ISO-8601 UTC timestamp". That value is now routed through `render_timestamp`, so under a
  non-UTC `display_timezone` it is the converted zone-labelled form — the claim was conditionally false
  (this epic's namesake misleading-signal defect). Corrected to describe the conditional label, with an
  xref to the run-config standard. Commit `cdcff5e`. The agent confirmed every OTHER "ISO-8601 UTC"
  doc claim it swept describes STORE fields (`now_utc_iso()`/`.isoformat()`) that are NOT routed through
  the helper, so those remain accurate.
- **Verification sub-agent — F2 (observation): rejected-with-reason (accepted as STORE).**
  `pm-documents/.../ref-asciidoc/scripts/_cmd_stats.py:102` (`generated`) and `_cmd_validate.py:161`
  (`timestamp`) emit `datetime.now(UTC)` as structured command-output fields. Left STORE/UTC: they are
  structured TOON fields in a different bundle's doc-tooling, not a plan-marshall report-body prose
  line, and under-inclusion is safe per the plan (leaving a timestamp in UTC is never a regression).
- **Verification sub-agent — F3 (observation): accepted design choice.** The guard is file-granular
  (whitelists whole RENDER/owner files). A future STORE write *inside* a render file that routed through
  the knob would not be caught. Accepted: both render files legitimately render, neither currently
  leaks, and the granularity is documented in the classification artifact.
- **Verification sub-agent — F4 (observation): accepted design choice.** `render_timestamp(*, tz=None)`
  accepts a per-call zone override, used only by tests for determinism; both live call sites pass no
  `tz` and resolve the single global zone, so the out-of-scope "per-surface timezone" is not violated.
- **Verification sub-agent — cannot-verify notes (addressed):**
  - D5 red-first: evidenced in this report (stash run → red; restore → 25 passed).
  - D2 steward configuration-flow surfacing: D2's Done-when is met via the ordinary run-config CLI
    path (`display-timezone get/set`) and `read_display_timezone`. Broader knob-catalogue surfacing is
    **deferred** to the sibling knob-cataloguing plan per this plan's Notes; the agent confirmed
    `marshall-steward` carries no knob catalogue that now omits `display_timezone`, so nothing is stale.
  - Build/test green: confirmed locally — `./pw verify plan-marshall` → 15997 passed, 1 skipped.
- **CI (PR #1172):** all required checks green — `verify / conclusion`, `verify / verify`, `verify / gate`, `dependency-review`, `review / review`, `generate-check` all **success**; `mergeable_state: clean`. No failures.
- **PR review:** `cuioss-review-bot` posted a PR Reviewer Guide — "PR contains tests / No security concerns identified / No major issues detected" — **no findings, no inline review threads**. Nothing to fix or answer. The other two expected reviewers were rate-limited (see Reviewer participation).

## Reviewer participation

Expected reviewer population derived from the registry — the `author_login` of each
`marketplace/bundles/plan-marshall/skills/automatic-review/standards/{bot_kind}.md`
(`coderabbit.md`, `pr-agent.md`, `sourcery.md`), cross-named by `.github/workflows/pr-agent.yml`:

| Reviewer (`author_login`) | Verdict | Body evidence / reason |
|---|---|---|
| `cuioss-review-bot` | `reviewed` | Posted a "PR Reviewer Guide" review over the diff — "PR contains tests / No security concerns identified / No major issues detected"; no findings, no inline threads. |
| `coderabbitai` | `rate-limited` | Posted only "Review limit reached … Next review available in: 58 minutes" — engaged, did not review this diff. |
| `sourcery-ai` | `rate-limited` | Posted only "you have reached your weekly rate limit of 500000 diff characters" — engaged, did not review this diff. |

**Coverage: 1 of 3.** The § Step 8 condition-4 shortfall disclosure fired: "Review coverage: 1 of 3 —
`cuioss-review-bot` reviewed (no findings); `coderabbitai` rate-limited (window reopens ~58 min);
`sourcery-ai` rate-limited (weekly quota)." Per the lane this is a disclosure, not a merge block: rate
limits are routine and outside our control, and conditions 1–3 are the only gates on the merge.

## Cost

- **Tokens:** not available to the agent in this session.
- **Wall-clock:** single interactive cloud session on 2026-08-11 (UTC); PR opened 21:32Z, CI green 21:46Z.
- **Population:** this single Claude Code cloud session's usage; **not comparable** to a plan-marshall
  `metrics.toon` dispatch-tree total (that counts an orchestrator+agent dispatch tree under a different
  per-task billing boundary this session does not share).

## Contract check (Step 9)

| Step | Verdict | Evidence |
|---|---|---|
| 1 Skills loaded | done | Named under Skills loaded; all via bundle path. |
| 2 Branch | done | `claude/configurable-display-timezone-6t3zs0` (harness-assigned, kept as-is) pushed to origin as the first action. |
| 3 Plan directory | done | `doc/plans/truthful-signals/150-.../plan.md` exists and opens with the first-instruction block. |
| 4 Implement | done | Deliverables addressed; every commit carries the `Co-Authored-By: Claude` trailer. |
| 4 Per-commit gate | done | The `*.py`-touching commit was preceded by a `total_issues: 0`, empty-`errors[]` quality-gate log. |
| 4 Pushed | done | No unpushed commit remains at each step. |
| 5 Build gate | done | `git diff --name-only origin/main...HEAD -- '*.py'` non-empty → `./pw verify plan-marshall` = SUCCESS (15997 passed, 1 skipped). |
| 6 Verification sub-agent | done | Independent agent: GO, all D1–D5 satisfied; F1 found and fixed, re-verified; F2–F4 recorded as accepted. |
| 7 PR cycle | done | PR #1172; both comment surfaces read; no actionable comments; reviewer participation recorded. |
| 8 Merge gate | conditions 1–3 met | All required checks green + `clean`; no open comments; report finalized as the last pre-merge commit. Coverage shortfall (1-of-3) disclosed. Auto-merge arming = the closing action. |
| 8 Bridge | done | No status/bookkeeping write under `doc/plans/` outside this plan's own directory; report carries the PR number and per-deliverable outcome. |
| 9 This check | done | This table. |

GitHub access path: **GitHub MCP server** (cloud). Branch form: **harness-assigned** `claude/*`, kept as-is.
No `/sync-plugin-cache` is owed (machine-local build step; a cloud run never performs or owes it).

## What have we learned (Step 9)

**None proposed.** Every step of the cloud-plan-lane contract executed as written and produced its named
artifact: the branch published before work, the conditional build gate keyed on `*.py`, the independent
pre-PR verification (and a focused re-dispatch after the F1 fix, done by continuing the same agent —
which worked and preserved context), the two-surface comment read, the registry-derived reviewer
population, and the disclose-not-block treatment of the 1-of-3 coverage shortfall. No step was
ambiguous in practice, no artifact was unproducible as written, and no command failed in the
environment. With no run-produced evidence of a gap, there is nothing to propose — a speculative
improvement is explicitly not a proposal.

## Residue

- `coderabbitai` and `sourcery-ai` were rate-limited and did not review this diff. Their windows reopen
  (coderabbit ~58 min; sourcery weekly). Re-review is optional and not a merge blocker; if desired, a
  maintainer can comment `@coderabbitai review` once the window resets.
- Broader knob-catalogue / steward-flow surfacing of `display_timezone` is deferred to the sibling
  knob-cataloguing plan in this epic, per this plan's Notes.
