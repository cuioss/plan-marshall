# Run report — 250-inbox-has-no-amend-or-supersede-verb (run 01)

**Date (UTC):** 2026-08-12    **Branch:** `claude/inbox-amend-supersede-verb-sidmu7` (harness-assigned)    **PR:** [#1198](https://github.com/cuioss/plan-marshall/pull/1198)    **Outcome:** completed (all six deliverables shipped; auto-merge armed after the report landed)

## Skills loaded

- `plan-marshall:ref-code-quality` (always)
- `pm-plugin-development:plugin-script-architecture` (always)
- `plan-marshall:persona-implementer` (production code work identity)
- `pm-dev-python:python-core` (Python production code)
- `pm-dev-python:pytest-testing` (Python tests)

All loaded by `Read` on the bundle path (the `plan-marshall` plugin notation was not attempted; the bundle-path route always works in a fresh clone).

Note: the plan's "Expected surface" names `marshall-orchestrator`, but the skill has since been **renamed to `plan-orchestrator`** (the plan's own Notes warned a skill-rename plan would move every path). Re-grounded on the actual paths under `plan-orchestrator/`.

## Deliverables

### D0 — GATE: the message-state vocabulary, designed once

**Chosen model — a single `lifecycle` header field, derived from the lessons skill's `status` model.**

The lessons skill (`manage-lessons`) carries `VALID_STATUSES = ('active', 'superseded', 'removed')` — a single `status` metadata field on a record, defaulting to `active` when absent (`metadata.get('status', 'active')`), plus a `superseded_by` pointer and a `.tombstones/{id}.json` record; a superseded lesson stays on disk (resolvable) but stops presenting as live in `list`. The inbox already has the *consumed* half (the `archive/` relocation) but not the *replaced* half. D0 imports the lessons model, not a new one.

The envelope gains **one** vocabulary — the `lifecycle` header field — closed over three values:

| `lifecycle` | Meaning | Carried extra fields |
|---|---|---|
| `live` (default; absent ⇒ `live`) | A filed message that is current. Every message written today. | `revision` / `amended` when amended |
| `superseded` | Replaced by a named successor; stays on disk and validates green, but stops presenting as live. | `superseded_by={successor bare filename}` |
| `stream-end` | A terminal control marker: the sender that filed it will send no more. | — |

**Amendment rides on attributes, not a second enum.** `amend` replaces the body in place, **preserves `created`**, stamps `amended={UTC ts}`, and bumps a monotonic `revision` (0 on a virgin message, +1 per amend). The message stays `lifecycle=live`. `revision` is a counter and `amended` a timestamp — neither is an enum, so the "no second enum" rule holds: there is exactly ONE state vocabulary (`lifecycle`).

**Stream termination fits as one more value in that one vocabulary** — `lifecycle=stream-end` — rather than a parallel `stream_status` enum. This is the merge that made two plans one: the stream-termination concept is a *sender-stream* state, expressed as a message the sender files (`inbox close-stream`) carrying `lifecycle=stream-end`. The marker is a normal, fully-valid message (it carries a real `kind` — `finding`, the "the epic should know" kind — and a body: the closing note), so **no validator message-class branch is needed**; `lifecycle` is orthogonal to `kind`. The drain keys the terminal signal off `lifecycle`, never off `kind`.

**Rejected alternative (recorded):** putting `stream-end` into the existing `kind` enum (`kind ∈ {landing, finding, candidate-lesson, stream-end}`) while `superseded` lived in `lifecycle`. Rejected because it splits message-state across **two** fields (`kind` for stream-end, `lifecycle` for supersede) — precisely the "second enum in one schema" the plan forbids ("Design both into one vocabulary"). Keeping `kind` purely the payload-type vocabulary and `lifecycle` the sole state vocabulary is what satisfies the one-vocabulary constraint.

**Back-compat:** `envelope_version` stays `1`. The new fields are all optional-with-default: `compose_envelope` (the `write` path) emits the unchanged six base fields and NO `lifecycle`/`revision` line, so a virgin message is byte-identical to today and an absent `lifecycle` reads as `live` (mirroring the lessons `status` default). The new fields appear only once a state-changing verb (`amend`/`supersede`/`close-stream`) writes them — which is exactly what makes an amended or superseded message distinguishable from a virgin one from the envelope alone (D1).

### D1 — envelope field makes post-filing mutation visible ✅

`cmd_inbox_amend` is the sanctioned in-place body correction. It replaces the body with the staged `--payload-file`, preserves `created`, stamps `amended=now`, bumps `revision`, and leaves `lifecycle=live`. `cmd_inbox_supersede` sets `lifecycle=superseded` + `superseded_by`. Both are visible **from the envelope alone**: a virgin message carries none of these header lines. Commit `58814bc`. Verified by `test_amended_message_is_distinguishable_from_a_virgin_one_from_the_envelope` (checks the header block, not the body).

### D2 — validate enforces, list surfaces ✅

`_validate_state_fields` (run after the seven base checks so existing codes are unchanged) adds `invalid_lifecycle`, `invalid_revision`, `revision_not_monotonic` (an `amended` stamp and `revision>=1` move together), and `invalid_supersede_state` (`superseded_by` present iff `lifecycle=superseded`). `cmd_inbox_list` carries per-row `lifecycle`/`revision`/`superseded_by` plus payload-level `live_count`. Commit `58814bc`.

### D3 — stream termination + drain ✅

`cmd_inbox_close_stream` files a `lifecycle=stream-end` marker (kind `finding`, a real body). `inbox list` reports `live_count` (valid live messages only — excludes superseded and stream-end) and `closed_senders`. The drain distinguishes EMPTY (`live_count 0`, empty `closed_senders`) from FINISHED (`live_count 0`, sender in `closed_senders`). The marker persists in the live queue as the durable closed-stream record; it claims a sequence like any message. Commit `58814bc`.

### D4 — foldered archive, atomic with the four functions ✅

Archive is per-sender: `inbox/archive/{sender}/{sender_id}-{NNN}.md`, keyed on the SOURCE sender (so a message and its `--as-name` recovery twin fold together). Updated ATOMICALLY in the single commit `58814bc`: `next_sequence` (scans queue + `archive/{sender}/` + flat shim), `resolve_message_path` (probes foldered then flat), `inbox_counts`/`_count_archived` (counts both layouts), and `cmd_inbox_archive` (writes foldered). New `cmd_inbox_migrate_archive` folds a flat archive and reports `moved_by_sender` (per-sender counts) + `moved_total`. **Directory-name safety:** `_foldered_archive_dir` re-validates the sender with `validate_plan_id` (`^[a-z][a-z0-9-]*$`) before using it as a path component — a `..`-shaped sender (valid as a filename component, traversing as a directory) is refused `invalid_message_name`, never folded into `archive/../`. This is the D4 hazard the plan flagged ("verified exactly like an asserted presence").

**Migration of the real `.plan/` archive is NOT done in this cloud clone** — `.plan/` is git-ignored and absent, so there is no archive to migrate here (the plan's "~652 files" live under `.plan/`, unreachable). The migration CAPABILITY (`inbox migrate-archive`) ships; executing it against a real archive is a local-run action. The dual-layout reads (foldered + flat) mean a stale pinned executor running flat-writing code against a foldered archive still allocates safely — the standing plugin-pin hazard the plan's Notes call out, bounded and noted here.

### D5 — five tests, each verified RED pre-fix ✅

New file `test/plan-marshall/plan-orchestrator/test_inbox_message_state.py`. Each control was run against a targeted revert of its own fix and confirmed red, then the fix restored:

| D5 | Test | Red-first evidence (naive impl) |
|----|------|---------------------------------|
| (a) amended distinguishable | `test_amended_message_is_distinguishable_from_a_virgin_one_from_the_envelope` + `test_should_stamp_amended_and_bump_revision` | naive body-only amend (no stamps) → `assert 'amended=' in amended_header` fails; `assert result['amended']` fails on `''` |
| (b) created survives amend | `test_should_preserve_created_across_an_amend` | naive amend restamping `created` → `assert '2026-...' == '2020-01-01T00:00:00Z'` fails (test plants a distinctive PAST timestamp so a same-second restamp cannot slip past) |
| (c) superseded not live, stays resolvable | `test_superseded_message_stops_appearing_as_live_but_stays_resolvable` | list counting superseded as live → `assert 2 == 1` fails |
| (d) monotonicity rejected | `test_should_reject_amended_without_a_revision_bump` (+ the reverse) | monotonicity check disabled → `assert (True,None) == (False,'revision_not_monotonic')` fails |
| (e) **the control** — no sequence reuse from a foldered archive | `test_next_sequence_advances_past_a_foldered_archived_message` | naive flat-only `next_sequence` → `assert 1 == 2` fails (the silent reuse the control guards against) |

All 41 tests in the new file pass with the fix; all 223 inbox tests and 549 plan-orchestrator tests pass.

## Build gate

`git diff --name-only origin/main...HEAD -- '*.py'` — Python changed (the two scripts + three test files), so the gate takes its full path.

- **Quality gate** (`./pw quality-gate`): CLEAN — `issues[0]`, coverage COMPLETE (mypy production [395 files], ruff [marketplace/bundles, test, .claude], SPDX headers, plugin-doctor marketplace-wide).
- **Module tests** (`./pw module-tests plan-marshall`): **16287 passed, 1 skipped**; 2 failed + 1 error, ALL in unrelated subsystems (`phase-2-refine/test_phase_2_refine_manage_config_readonly.py`, `phase-5-execute/test_phase5_change_ledger.py` — git change-ledger / marshal.json). Each **passes in isolation** — they are pre-existing xdist test-ordering flakiness in areas my diff does not touch (my change is confined to the plan-orchestrator inbox surface). Recorded as pre-existing, not caused by this change.
- Direct `uv run pytest` over the four inbox test files: **223 passed**.

## Findings

### Verification sub-agent (Step 6) — independent `general-purpose` reviewer, read-only

Verdict: **all six deliverables met, no correctness gaps.** D5(e) confirmed meaningful (would fail against a naive flat-only `next_sequence`). D4 atomicity confirmed (all code in one commit; the physical `.plan/` archive is absent from the clone, so no intermediate foldered-with-flat-allocator state is checkoutable). Three findings, each recorded per instance:

| # | Source | Finding | Disposition |
|---|--------|---------|-------------|
| 1 | sub-agent | `cmd_inbox_archive` docstring: "`os.link` creates `inbox/archive/{name}`" — stale flat path post-foldering | **fixed** (fc8ecb4) → `inbox/archive/{sender}/{name}` |
| 2 | sub-agent | `resolve_message_path` docstring: "Probing … `inbox/archive/{name}` second" — omits the now-primary foldered probe | **fixed** (fc8ecb4) → foldered-then-flat probe order documented |
| 3 | sub-agent | `_resolve_live_message` says "LIVE" but filters only queued+valid; `supersede` had no lifecycle guard, so superseding a `stream-end` marker would flip it to superseded and silently drop the sender from `closed_senders` (re-opening the stream) | **fixed** (fc8ecb4) → docstring corrected; `supersede` now refuses a stream-end marker with `not_supersedable`, fired before the successor check; new test `test_should_refuse_to_supersede_a_stream_end_marker` |

Observations the sub-agent raised that are **NOT** plan gaps (recorded, not fixed):

- **`analyze.md` drain not updated to consume the new state.** The Step 3 drain loop still routes every `messages[]` row by `kind` and archives it; it does not consult `live_count` / `closed_senders` / `lifecycle`, so a `superseded` message would be processed as ordinary work and a `stream-end` marker routes through the `finding` branch. Nothing in `analyze.md` is *false* (kind-routing stays exhaustive since stream-end rides `finding`), and `analyze.md` is not in the plan's Expected surface. This is the **CONSUMER-side follow-up** — the script surface (D2/D3 done-when: list carries the state; the drain *can* tell empty from finished) is complete; teaching the `analyze` workflow to *act* on it belongs to the epic-compaction work the plan explicitly scopes out. See § Residue.

Also fixed proactively during my own beyond-diff sweep (before the sub-agent ran):

- **`orchestration-model.md` § Ledger Write-Boundary** — the "Append-only — never edits" qualifier was stale once `amend`/`supersede` became sanctioned in-place edits of a sender's own message. Reconciled (a9b52f4) to name the one sanctioned correction path while keeping all three bolded qualifiers (`Append-only`, `Own-file-only`, `One-way`) intact for the doc-contract test, and pointing at the message-state vocabulary. A re-verification of the delta was dispatched to confirm the fixes.

## Reviewer participation

Expected reviewer population **derived from configuration** — the `author_login` of each `marketplace/bundles/plan-marshall/skills/automatic-review/standards/{bot_kind}.md` registry doc (`pr-agent.md`, `coderabbit.md`, `sourcery.md`), cross-named by `.github/workflows/pr-agent.yml`. Verdicts read from the stored comment bodies on PR #1198 head `7b503ca`:

| Reviewer (`author_login`) | Verdict | Body evidence / reason |
|---|---|---|
| `cuioss-review-bot` | `reviewed` | Posted a "PR Reviewer Guide" review artifact against the diff: "PR contains tests", "No security concerns identified", "No major issues detected". No actionable findings. |
| `coderabbitai` | `rate-limited` | Posted only a "Review limit reached … Next review available in: 11 minutes" notice in place of a review. Engaged but did not review this diff. |
| `sourcery-ai` | `rate-limited` | Posted only "you have reached your weekly rate limit of 500000 diff characters" in place of a review. |

**Coverage: 1 of 3.** No inline review-thread comments; no actionable comment on any surface, so every comment is handled (nothing to fix). The § Step 8 shortfall disclosure fired: *"Review coverage 1 of 3 — cuioss-review-bot reviewed (no issues); coderabbitai rate-limited (window reopens ~11 min); sourcery-ai rate-limited (weekly quota)."* Rate limits are routine and outside our control; the shortfall is DISCLOSED, not blocked (per § Step 8 condition 4). The final report commit re-triggers the reviewers on a new head — any review that then arrives is a bonus, not a gate.

## Cost

- **Tokens:** not available to the agent in this session — no per-session token meter is exposed to the run. The verification sub-agent self-reported ~305k subagent tokens across its two passes (146.8k + 158.2k) as harness-counted usage.
- **Wall-clock:** ~1h from run start (branch push, plan-dir establishment) to PR #1198 open and the merge gate; the `verify` CI run itself took ~15 min (22:31→22:46 UTC).
- **Population:** this single Claude Code cloud session's usage as the harness counts it. ⛔ NOT comparable to a plan-marshall `metrics.toon` total, which counts the orchestrator-plus-agent dispatch tree under plan-marshall's own per-task billing boundary — a boundary a single interactive cloud session does not share. The figures above are wall-clock and sub-agent self-report only; a comparable per-task token total is not derivable here.

## Contract check (Step 9)

Re-read `cloud-plan-lane` and checked each step against what happened:

| Step | Verdict |
|---|---|
| 1 Skills loaded | Done — 5 skills via bundle-path `Read` (named in § Skills loaded). |
| 2 Branch | Done — kept the harness-assigned `claude/inbox-amend-supersede-verb-sidmu7`; pushed to `origin` before any work (branch was absent from the remote at start). |
| 3 Plan directory | Done — `git mv` to `.../250-…/plan.md`; the first-instruction block was present and survives. |
| 4 Implement / per-commit gate / pushed | Done — commits carry the `Co-Authored-By: Claude` trailer and no "Generated with" footer; each `*.py`-touching commit was preceded by a clean `./pw quality-gate`; every commit pushed (no unpushed commit remains). Staged explicit paths (never `git add -A`); no `uv.lock` churn. |
| 5 Build gate | Done — Python changed → full path. `./pw quality-gate` clean; `./pw module-tests plan-marshall` 16287 passed (2 unrelated xdist-flaky, pass in isolation). |
| 6 Verification sub-agent | Done — one `general-purpose` pass (clean verdict, 3 findings), all findings fixed, re-verified clean via a focused re-dispatch. Findings + dispositions in § Findings. |
| 7 PR cycle | Done — PR #1198 (no `skip-bot-review`: the diff touches `marketplace/bundles/**` and `*.py`, so it is reviewed as code). All three comment surfaces read; every comment dispositioned; per-reviewer participation recorded. |
| 8 Merge gate | Conditions 1–3 met (required contexts green on head `7b503ca` → `mergeable_state: clean`; every comment handled; report finalized as the last pre-merge commit). Coverage shortfall (1-of-3) disclosed. Auto-merge armed (SQUASH). |
| 8 Bridge | No status/bookkeeping write landed outside this plan's own directory; the report carries the PR number and per-deliverable outcome the orchestrator will collect. |
| 9 This check | Recorded here. |

**GitHub access path:** the GitHub MCP server (cloud path). **Branch form:** harness-assigned `claude/*`. A cloud run **owes no** `/sync-plugin-cache` — it is a machine-local build step, not a debt this run records.

## What have we learned (Step 9)

**None proposed.** The run exercised the contract end to end without hitting a step that was ambiguous in practice, an artifact that could not be produced as written, or a command that failed in the environment. The one friction — the full `./pw module-tests plan-marshall` run surfacing two flaky failures in unrelated subsystems (git change-ledger, marshal.json) under xdist — is already covered by the contract's "read the output, not the exit code" rule plus the in-isolation re-check I performed, so it is not a contract defect. This is a **headless/autonomous** run with no reachable operator, so a proposal could not be presented for approval regardless; recording "none, with reason" is the honest outcome (per § "A run that examined the contract and found nothing is a different fact from a run that never looked").

## Residue

- **`analyze` drain workflow does not yet consume the new state.** The Step 3 drain loop routes by `kind` and does not skip `superseded` messages or recognize `stream-end` closure via `closed_senders`. The SCRIPT surface D2/D3 require is complete (list carries the state; the drain *can* tell empty from finished); teaching the workflow to *act* on it is CONSUMER-side follow-up, belonging to the epic-compaction work the plan explicitly scopes out. → a follow-up plan on `plan-orchestrator/workflow/analyze.md`.
- **Real `.plan/` archive migration is owed on a local run.** `inbox migrate-archive` ships, but the physical fold of the repository's actual archive (git-ignored, absent from this clone) must be run where `.plan/` exists. The dual-layout reads keep allocation safe until then.
- **Plan "Expected surface" named the pre-rename skill** (`marshall-orchestrator`); re-grounded on `plan-orchestrator`. A plan-authoring staleness for the orchestrator to note, not a lane-contract issue.
- **Stale plugin-pin hazard** (plan Notes): a stale pinned executor running flat-writing code against a foldered archive is bounded (only this repo, only post-migration) and mitigated by the dual-layout reads; it is the standing plugin-pin issue, noted because it recurs.

## Cost

_pending_

## Contract check (Step 9)

_pending_

## What have we learned (Step 9)

_pending_

## Residue

_pending_
