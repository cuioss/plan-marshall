# Lessons archive — index

Written by the `ingest` command of the `lessons-routing` epic (RULING 2026-10-09 in `epic.md`). Each
lesson file is a verbatim copy of the corpus file, placed under the directory of its level. Clusters of
duplicates and near-duplicates are recorded here; the lesson files themselves are kept one per id.

Grades follow the `live-blockers` epic's `backlog.md` where that list already graded the subject (the
section is cited); the rest are the orchestrator's own grade. Only the lessons filed to `live-blockers`
and the two stale ones were checked against the code or the ledger at ingest time — the `medium/` and
`low/` grades rest on the lesson text and the backlog's earlier verification.

## Sweep 2026-10-09 — 34 lessons, 6 carry-over rows

### `filed-live-blockers/` — high, filed to the `live-blockers` inbox (9 lessons)

| Message | Lessons | Subject | Owner today |
|---|---|---|---|
| `lessons-routing-001` | `2026-09-29-17-001`, `2026-10-02-10-005`, `2026-10-07-07-001` | Self-review does not converge and re-fires settled finalize steps (backlog § 1.2) | PLAN-LB-22 shipped, #1726 shipped, PLAN-LB-32 staged |
| `lessons-routing-002` | `2026-10-02-10-003`, `2026-10-02-10-004` | Scope-creep guard cannot persist its finding and diffs the wrong base (backlog § 1.7) | PLAN-LB-27 staged |
| `lessons-routing-003` | `2026-10-03-18-001`, `2026-10-07-07-007`, `2026-10-07-07-008` | Review step: stale required bot, unrunnable poll wait, "fixed" posted before the commit (backlog §§ 4.4, 1.5) | PLAN-LB-24 running, PLAN-LB-25 staged |
| `lessons-routing-004` | `2026-10-06-15-001` | Review-bot fleet enrolment of the schema-failing repositories (backlog § 4.5) | PLAN-LB-31 staged |

### `medium/` (16 lessons)

| Lessons | Subject | Backlog |
|---|---|---|
| `2026-09-27-07-003`, `2026-10-02-21-003` | Plan advances past the outline with Q-Gate findings pending (two routes to one state) | § 1.17 |
| `2026-09-27-07-004` | Strict handshake fails on other sessions' writes to the main checkout; eased by the shared ledger worktree | § 1.15 |
| `2026-09-27-08-001` | Lessons-housekeeping Step 1 reads the retired `modified_files` field | § 1.12 |
| `2026-09-28-17-001` | `ci checks status` omits a reusable workflow's nested checks | § 2.7 |
| `2026-09-29-17-002` | `affected_files` is never re-synced, so finalize gates under-scope | § 1.13 |
| `2026-10-02-10-002` | Landing gate cannot tell an ejected PR from a queued one | § 1.23 |
| `2026-10-02-10-009`, `2026-10-03-18-003` | Orchestrator-tier test runs: filed under no plan, and each one ends an execute envelope | § 2.9 |
| `2026-10-07-07-002` | A script a plan changed cannot be called by the same plan (stale executor) | § 2.3 |
| `2026-10-07-07-009` | `WORKTREE` dispatch contract says repo-relative, dispatcher sends absolute | § 1.20 |
| `2026-10-02-10-008`, `2026-10-07-07-004` | Dispatch-boundary rows are keyless and record an omitted figure as `0` | not listed (metrics) |
| `2026-10-07-07-003` | `post_run_source_guard` called with an undeclared `--plan-id`, so the guard did not run | not listed |
| `2026-10-07-07-005` | Foreign-repository paths need their own class in the declared footprint | not listed |
| `2026-10-02-21-005` | A re-fire overwrites the earlier firing's step record | not listed |

### `low/` (7 lessons)

| Lessons | Subject | Backlog |
|---|---|---|
| `2026-09-27-19-001` | `Module_testing scope` is not named in the phase-4 task-split algorithm (file has no metadata header) | § 5 |
| `2026-10-02-10-007`, `2026-10-02-21-001` | Retrospective counts read-intent paths and rename sources as unrealised | not listed |
| `2026-10-02-21-002` | Execute workflow does not name the `get-deliverable` call | not listed |
| `2026-10-02-21-004` | `display_detail` contract is not enforced | not listed |
| `2026-10-03-18-002` | No script computes the Q-Gate deliverable hashes | § 1.18 |
| `2026-10-07-07-006` | Release and deploy steps planned as leaf steps | § 4.11 |

### `stale/` (2 lessons)

| Lesson | Why |
|---|---|
| `2026-10-02-10-001` | All three proposed actions are marked completed in PLAN-LB-30, shipped as #1722 (`2cb0f8c3f` on `main`). |
| `2026-10-02-21-006` | `live-blockers` `backlog.md` § 5 lists it as already fixed (the R4 worktree block, #1688). Not re-checked here. |

### PLAN-09 (#1652) carry-over rows

Six rows from `inbox/archive/orchestrator-refactor/orchestrator-refactor-001.md`; they were never corpus
lessons, so there is no file per row. Full text and fixtures are in that message.

| Row | Subject | Level | Note |
|---|---|---|---|
| 1 | A payload delivered far below its produced size is truncated, never "small" | medium | retrospective tier selection |
| 2 | Dispatch-boundary records carry the step key and usage; unmeasured is never `0` | medium | same subject as `2026-10-02-10-008` / `2026-10-07-07-004` |
| 3 | A coverage-class step without its tool returns a coverage gap and spends no loop-back | high | filed in `lessons-routing-001` |
| 4 | Excluded-versus-declared outline paths; declared lists reconciled after execute | medium | same subject as `2026-09-29-17-002` |
| 5 | A landing's merge-commit fact comes from the PR merge record, not local HEAD | low | backlog § 1.24 |
| 6 | A reserved never-removed resource has a dedicated refusal on every destructive path | low | backlog § 3.3 |

## Sweep 2026-10-09 (second run) — 76 lessons

None of the 76 ids was in the first sweep. Checked against the code or `main` at this run: the stale
lessons (their fixing PR is on `origin/main`), and the three "still live" notes marked below. Every
other grade rests on the lesson text, the `live-blockers` backlog and that epic's ledger.

### `filed-live-blockers/` — high, filed to the `live-blockers` inbox (12 lessons)

| Message | Lessons | Subject | Owner today |
|---|---|---|---|
| `lessons-routing-005` | `2026-10-08-21-003`, `2026-10-05-17-003` | Head-dependent finalize steps re-fire in full; the self-review self-seeds on doc-claim plans (backlog § 1.2) | PLAN-LB-32 staged; #1726 shipped |
| `lessons-routing-006` | `2026-10-07-12-002` | `scope_creep_check` exits 1 with empty stderr (backlog § 1.7) | PLAN-LB-27 staged |
| `lessons-routing-007` | `2026-10-04-09-001`, `2026-10-05-14-006`, `2026-10-05-14-007`, `2026-10-05-17-001`, `2026-10-09-15-007` | Review step and gate: size caps found after the PR exists, an edited bot summary double-filed, a bot status in the CI set, the re-review matcher ignoring the bot's author, `full review` stored as a finding (backlog § 4.4). `coderabbitai full review` is in no inventoried file — still unregistered | PLAN-LB-24 running (covers the last in part); the rest unowned |
| `lessons-routing-008` | `2026-10-09-13-001`, `2026-10-09-15-001` | Per-task tests have no runnable scope (Open Defect in `live-blockers`) | none |
| `lessons-routing-009` | `2026-10-09-13-004` | The main executor can point into a removed worktree (Open Defect in `live-blockers`) | none |
| `lessons-routing-010` | `2026-10-05-17-002` | domain-narrow empties `references.domains`; the documented recovery call exits 2. Graded high by the operator (asked as borderline) | none |

### `medium/` (29 lessons)

| Lessons | Subject | Backlog |
|---|---|---|
| `2026-09-19-09-003`, `2026-09-20-18-001`, `2026-09-20-18-002`, `2026-09-21-11-007`, `2026-09-21-15-003`, `2026-09-21-15-004`, `2026-10-02-16-003` | Invented verbs and flags: retried after an argparse rejection, `--plan-id` placed by rote, flag names taken from prose (`-11-007` and `-15-003` are one incident) | § 2.9 in part |
| `2026-09-21-09-001`, `2026-09-21-09-002` | `files_exist` gate: a declared path no task targets is never examined; a file the plan itself created is flagged | § 2.9 |
| `2026-09-21-11-012` | Retrospective fragment pipeline: undeclared flag, doubled plan path, missing fragments file, still `done` | § 2.9 |
| `2026-09-19-09-002`, `2026-10-07-12-003`, `2026-10-09-13-005`, `2026-10-09-15-003` | Dispatch and phase metrics: no finalize boundary rows, keyless rows, uncorroborated dispatch lines, finalize time booked on execute | not listed (metrics) |
| `2026-09-24-05-001` | Six review fix tasks of #1599 deferred at the loop-back ceiling by operator decision (file has no metadata header) | not listed |
| `2026-10-05-14-001` | `verification-feedback` rejects `producer=ci-verify-policy`. Still live: the token is in no `verification-feedback` file | § 1.24 |
| `2026-10-05-14-003` | A verify on a dirty tree does not count for the committed tree | not listed |
| `2026-10-05-14-004` | Pre-push gate scope is derived from marketplace bundles, so it is empty in a Maven repository | not listed |
| `2026-10-05-14-005`, `2026-10-08-15-001`, `2026-10-09-15-006` | A fix closes one site and leaves its siblings: same-file restatements, ten-site rule rewrites, one defect class at four sites | not listed |
| `2026-10-05-14-008` | Refine scratch file at a fixed shared path. Still live: `module_mapping.toon` is named in three skill documents | § 2.9 |
| `2026-10-08-21-001` | Lessons-housekeeping Step 1 reads the retired `modified_files` field | § 1.12; folded into PLAN-LB-32 |
| `2026-10-08-21-004` | A wrong bot comment is stored `accepted`, so review statistics count no false positive | not listed |
| `2026-10-08-21-005` | Six `manage-status` documentation and behaviour gaps left by PLAN-LB-22 | not listed |
| `2026-10-09-13-002` | `WORKTREE` arrives absolute, or as a flag fragment after the merge | § 1.20 |
| `2026-10-09-13-003` | The orchestrator followed a stale plugin-cache workflow document mid-plan. Asked as borderline; the operator left it at medium | § 4.1; Watch in `live-blockers` |
| `2026-10-09-15-002` | Task planning cannot append tasks for a deliverable added later | not listed |
| `2026-10-09-15-005` | Seven finalize steps the dispatcher improvised | § 1.23, § 1.24 in part |

### `low/` (27 lessons)

| Lessons | Subject | Backlog |
|---|---|---|
| `2026-09-19-09-001` | OUTCOME lines missing for tasks done before the guard landed (one-off) | not listed |
| `2026-09-21-09-004`, `2026-09-21-11-001`, `2026-09-21-20-001`, `2026-09-23-18-001` | A CI wait that lapses on running checks is accepted, not a red build (three are owed `architecture enrich` hints) | § 1.5 |
| `2026-09-21-11-003`, `2026-09-21-15-002` | `review_completeness` rejects a bare bot name by design (one incident, filed twice) | not listed |
| `2026-09-21-11-004` | Preserve-then-move recovery for work authored on `main` before the plan | not listed |
| `2026-09-21-11-005`, `2026-09-21-11-006` | Precedents: operator override for a spend-capped required bot; suppressing a check failure with vendor evidence | not listed |
| `2026-09-21-11-009` | A failed `manage-status transition` was passed over (no stderr captured) | not listed |
| `2026-09-21-11-010`, `2026-09-21-15-005` | File outline assessments at outline time (one incident, filed twice) | not listed |
| `2026-09-21-11-011`, `2026-09-21-15-006` | Decline review-bot suggestions that contradict the tasked intent (one incident, filed twice) | not listed |
| `2026-09-23-18-002` | Executor tree-first ordering: fixed and tested; the skill document does not state it | not listed |
| `2026-09-24-10-001`, `2026-09-25-08-001` | Test-module carve campaign: template globs make the reconciliation check ambiguous; whole-tree globs as task write sets (`-24-10-001` has no metadata header) | § 4.11 |
| `2026-10-05-14-002` | `mark-step-done` rejects an ambiguous short SHA | not listed |
| `2026-10-05-17-004` | Decide test-scope guards up front on docs-reconciliation specs | not listed |
| `2026-10-07-12-001` | Retrospective footprint tiers counted untracked archived-epic paths | not listed |
| `2026-10-07-12-004` | A batch `mark-steps-done` verb | not listed |
| `2026-10-07-12-005` | A failures-only build-log summarizer | not listed |
| `2026-10-08-15-002` | outline-vs-shipped counts a superseded exclusion as violated | not listed |
| `2026-10-08-21-002` | Pass self-review candidates by file path, not inline | not listed |
| `2026-10-08-21-006` | The PR Intent section drops the non-goals when over budget | not listed |
| `2026-10-09-15-004` | `chat extract-signal` counts subagent hand-backs as operator turns | not listed |

### `stale/` (8 lessons)

Each records a defect fixed inside the plan that reported it; that plan's PR is on `origin/main`.

| Lessons | Fixed by |
|---|---|
| `2026-09-19-09-004`, `2026-09-19-09-005` | #1534 (`a5977d953`) — the only two lessons about a domain bundle (`pm-plugin-development`); `doctor-test-conventions.md` names `py_compile` |
| `2026-09-21-11-002`, `2026-09-21-15-001` | #1540 (`433d0a67b`) — one finding, filed twice |
| `2026-09-21-11-008` | #1547 (`895694e32`) |
| `2026-09-21-09-003` | #1556 (`ed9032805`) |
| `2026-10-02-16-001`, `2026-10-02-16-002` | #1674 (`4d92fb749`) |

## Sweep 2026-10-12 — 133 inbox messages from `pm-mcp-core-m2-m4`

Input was the epic's own inbox, not the lessons corpus (corpus: 0). All 133 were sent by the
pm-mcp-core epic orchestrator (123 `candidate-lesson`, 10 `finding` from PLAN-41, the first plan run
under Antigravity). Files are named by inbox message, `pm-mcp-core-m2-m4-NNN.md`; the source lesson id,
where one exists, is in each body's `Origin` line. Operator rulings this run: Antigravity findings are
**critical** (they prevent Antigravity from working); cross-repo deliverables, assessment-coverage Q-Gate
and the 4-plan Q-Gate hash skip are **high**. Every filed and stale item was checked at `fc0090a24`
where the message names a code location; medium and low grades rest on the message text and `backlog.md`.

### `filed-live-blockers/` (65 messages, 15 filings)

| Filing | Level | Messages (`-NNN`) | Subject | Owner today |
|---|---|---|---|---|
| `lessons-routing-011` | critical | 133, 125 | Antigravity: no sub-agent dispatch, inline execution, no execute trail | none |
| `lessons-routing-012` | critical | 131 | Antigravity: `CLAUDE.md` never loaded; quality gate dropped from tasks | partly PLAN-LB-29 |
| `lessons-routing-013` | critical | 124, 132 | Antigravity: tokens recorded as `0`; harness never recorded (`client.toon`) | none |
| `lessons-routing-014` | superseded by `-012` | 126 | `maven run` executes any plugin goal (Spotless from Central). Operator ruling 2026-10-12: not a defect of its own — the wrapper is a deliberate pass-through; the cause is `CLAUDE.md` unread under Antigravity. Folded into `-012` as a symptom, with an "unresolvable plugin prefix means stop" rule | PLAN-LB-29 (via `-012`) |
| `lessons-routing-015` | critical | 130 | Incomplete package reported complete; existing tests weakened | none |
| `lessons-routing-016` | critical/high | 127, 012, 056 | Pushed/merged head lacks the plan's mandated gates | near PLAN-LB-32 |
| `lessons-routing-017` | critical/high | 128, 005, 041, 053, 034, 061 | Required review bot stale after fix; re-review not re-armed (backlog § 4.4) | PLAN-LB-24 |
| `lessons-routing-018` | critical/high | 129, 082, 009, 015, 045, 048, 052, 055, 073, 078, 090, 093, 096, 100, 112, 122 | Sibling-repo deliverable lifecycle; foreign-PR gate assumes `feature/{plan_id}` (verified) | none |
| `lessons-routing-019` | high | 003, 024, 042, 103 | Red-CI triage unreachable: ci-verify producers outside the accept-set (verified) | PLAN-LB-24 |
| `lessons-routing-020` | high | 025, 054, 062, 087, 113, 117, 006 | Fix tasks under deliverable 0 rejected by commit-add (verified; backlog § 1.6) | PLAN-LB-26 |
| `lessons-routing-021` | high | 081, 094, 120 | Workflow notation resolves only `marketplace/bundles/` in consumer repos (verified) | none |
| `lessons-routing-022` | high | 001, 040, 050, 057, 074, 091, 097, 123 | Deep-lane outline writes no assessments; Q-Gate 2.2 fails every deliverable | none |
| `lessons-routing-023` | high | 067, 080, 110, 121 | 4-plan Q-Gate skips validators on the 3-outline hash, reports a pass | none |
| `lessons-routing-024` | medium, domain | 010, 076, 088, 114, 118 | `pm-dev-java` profiles attach Quarkus/Weld/IT skills ungated; `cui-testing` missing (verified) | none |
| `lessons-routing-025` | low, domain | 058, 059 | `cui-http-testing`: single-use responses, loopback address family (verified gap) | none |

### `stale/` (6)

| Messages | Reason |
|---|---|
| 028, 060, 065, 083, 101 | `scope_creep_check` finding type and diff base fixed by #1745 (`370f42379`, 2026-10-10T18:39Z): type `triage`, merge-base baseline. Later reports came from consumers on an unsynced plugin. |
| 085 | Reactor test count summed by #1750 (`2fd164ec9`). |

### `medium/` (39)

| Messages | Subject | Backlog |
|---|---|---|
| 008, 037, 043, 044, 068, 104, 119 | Pre-push gate is marketplace-shaped in Maven repos (zero bundles, module-tests DEGRADED, drift probe no verdict); compose keeps it on an unknown verdict | — |
| 018, 026, 051, 066, 089, 106 | Phase leaves self-transition before the orchestrator's gate; half-stamped metrics boundary; handshake drift on re-entry | §§ 1.16, 1.17 |
| 007, 019, 063 | Unmeasured build commands resolve to orchestrator tier and cost one execute yield per module | § 1.20 |
| 077, 107 | Orchestrator ends its turn after a non-terminal hand-back / `budget_yield` | — |
| 038, 070 | Manifest step-param snapshot goes stale against `marshal.json` | — |
| 033 | Executor drops an empty-string `--value ""` argument | — |
| 002, 027, 039, 049, 071, 098, 099, 035, 111 | Outline authoring checks (dependency edges, grounding, closed write-sets, cross-spec contradictions); init scope counts every path; `affected_files` add-only | § 1.19 |
| 030, 105 | Sonar identity includes the line number; fetch without `--pr` fills the plan store | — |
| 016, 084, 115 | Approval-only and gate-status comments filed as findings; Sourcery budget refusal unrecognised | § 4.4 |
| 029, 069, 036, 086 | Commit predicate on the chain tail; automatic-review doc vs `trigger-bot` flags; shared `module_mapping` temp file; fix-round builds filed under `NO_PLAN` | § 2.9 |

### `low/` (23)

| Messages | Subject |
|---|---|
| 031, 046, 109 | Disabled build server logs a WARNING on every build |
| 011, 013, 021, 032, 047, 064, 075 | Dispatch-boundary and metrics recording gaps (double count, keyless rows, re-fires unrecorded, checkpoint reclassified as error) |
| 014, 079, 092, 108 | Retrospective measurement (ledger gone with the worktree, read-intent files graded unrealised, hand-backs counted as operator turns) |
| 004, 017, 020, 022, 023, 072, 116, 102, 095 | Sonar only in CI; triage decline reversed; review-round cost; phase-complete count line; project-specific recipe premise; verb and flag paraphrases; re-review timeout clamp |

### Late arrivals 2026-10-12 — 10 messages (`-134`..`-143`, PLAN-11 #30, Claude Code)

Arrived at 13:52Z while the sweep ran; graded in the same run. None filed.

| Messages | Level | Subject |
|---|---|---|
| 141 | stale | `scope_creep_check` — fixed by #1745; the consumer ran an unsynced plugin |
| 135, 136, 138, 139, 140, 143 | medium | `trigger-bot --required-bots` (= 069); `resolve --task-number`; executor stale mid-session (`pre_merge_gate` unknown at merge); transient GraphQL read in `wait-for-queue-settle`; leaf self-transition; phase-4-plan Step 8 `qgate add --type warning` |
| 134, 137, 142 | low | Nine review rounds (widened fix rounds); `--wait-seconds` paraphrase; dispatch-boundary rows |
