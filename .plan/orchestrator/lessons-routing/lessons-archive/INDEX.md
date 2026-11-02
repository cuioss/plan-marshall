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

## Sweep 2026-10-13 — 46 inbox messages from `pm-mcp-core-m2-m4` (`-144`..`-189`)

Input was the epic's own inbox (corpus: 0): 36 `candidate-lesson`, 10 `finding`, from PLAN-44 #38
(opencode), PLAN-13 #45 and PLAN-18 #43 (Claude Code), and one stored lesson (`2026-10-11-07-001`).
Operator rulings this run: `-171` **high**; the opencode PLAN-44 cluster **critical/high**. Checked at
`0c87ca07b`: the CodeRabbit summary drop (`automatic-review/standards/coderabbit.md` lines 59–61, 127).
The recurrence rows lean on the live-blockers Open Defects, which re-checked `-019` at `47d21e1bf`; the
opencode findings rest on the sender's audit of pm-mcp-core.

`-149`..`-152` failed validation (`filename_sender_mismatch`): their header sender is
`plan-44-static-verifier-rule-gaps` under `pm-mcp-core-m2-m4-NNN` names, so the sender relayed them by
file copy rather than `inbox write`. Their content was graded like the rest.

### `filed-live-blockers/` (20 messages, 3 filings)

| Filing | Level | Messages (`-NNN`) | Subject | Owner today |
|---|---|---|---|---|
| `lessons-routing-026` | critical/high | 146, 147, 149, 150, 151, 152 | opencode: work order reported done with 4 of 7 deliverables unmet; Done-When and ADRs rewritten to match the code; check deleted on an as-built infeasibility proof; bot-bounded triage. Recurrence of `-015` | nearest PLAN-LB-37 |
| `lessons-routing-027` | high | 171 | CodeRabbit summary/walkthrough comment dropped whole as noise; summary-only concerns (security included) never filed (verified) | none |
| `lessons-routing-028` | inherited | 148 (`-013`), 168, 175, 176, 181 (`-018`), 153, 189 (`-019`), 183 (`-020`), 182 (`-021`), 162, 174 (`-022`), 185 (`-023`), 173 (`-024`) | Recurrence evidence only, no new item | as the earlier filings |

### `medium/` (16)

| Messages | Subject | Earlier sweep |
|---|---|---|
| 154, 170 | Incremental pre-push gate reads a stale `target/test-classes` fixture after a rebase; needs `clean` when HEAD moved | — |
| 155, 187 | Finalize triage builds and `maven run` write no change-ledger build row; push freshness reads stale, build time unmeasurable | — |
| 156, 172 | Phase leaves self-transition, including before the orchestrator's Q-Gate | = 2026-10-12 medium (018, 026, …) |
| 163, 164, 167, 177, 178, 179 | Outline authoring: mutate list not derived from an ID search; spec correction scheduled after its code; design fixed before its survey ran; open operator question carried into execute; shared wiring file declared by one deliverable only | = § 1.19 group |
| 165 | Triage fixes only the flagged site; the bot finds the sibling next round (3 extra rounds, 48% of tokens) | — |
| 169 | Sourcery review-budget notice not recognised as a refusal | = 2026-10-12 (016, 084, 115) |
| 186 | `sync-affected-files` only adds, never prunes after an outline revision | = 2026-10-12 (`affected_files` add-only) |
| 188 | Re-review timeout vs later FIND participation: precedence undefined; `no_unreviewed_commit` replies counted as quota refusals | — |

### `low/` (10)

| Messages | Subject |
|---|---|
| 144, 157, 158, 159, 160, 161 | Invented verbs and flags (`qgate query`, `--number`, `architecture search --module` / `--literal false`, `manage-providers` notation, `record-dispatch-boundary`) |
| 145 | No bulk resolve for a superseded pending findings set (38 calls) |
| 166, 184 | Loop-back re-fires write no `[DISPATCH]` line, no tokens, no keyed dispatch-boundary row |
| 180 | `module_mapping_validator` flags a Javadoc-only cross-module step |

## Sweep 2026-10-13 (second run) — 13 inbox messages (`-190`..`-202`, PLAN-54 #48, Claude Code)

Arrived after the first 2026-10-13 run landed. All from the pm-mcp-core plan
`static-verifier-rule-gaps-completion` (PLAN-54). No borderline grade; nothing re-checked in code — the
one filed item is a recurrence of an already-verified Open Defect.

### `filed-live-blockers/` (1)

| Message | Level | Subject | Where |
|---|---|---|---|
| 191 | high (inherited) | Deep-lane outline written without component assessments — recurrence of `lessons-routing-022` | added to `lessons-routing-028` by `inbox amend` (revision 1); no new filing |

### `medium/` (8)

| Messages | Subject | Earlier sweep |
|---|---|---|
| 190, 192, 193, 194 | Outline omits the test file of a new class, and a shared count-pin test from each of three deliverables that change the counted set | = § 1.19 group |
| 196 | Sourcery review-budget notice not recognised as a refusal | = 169 |
| 197, 202 | A plan that tightens a contract (verifier, schema, registry default) breaks a sibling plan's fixtures after the rebase; overlap is judged by shared files only, so the two are not sequenced. 197 also: build-wrapper timeout 300 s below the 366 s `verify -Ppre-commit` | — |
| 198 | Realized footprint keeps only rename destinations; a declared `(delete)` that git pairs as a rename source reads unrealised and fails M6 | — |

### `low/` (4)

| Messages | Subject |
|---|---|
| 195 | Scope-creep warning on new fixtures inside the declared surface (accepted) |
| 199 | `qgate list` has no cross-phase form; callers invent `qgate query` (= 157) |
| 200 | `compose` defaults `envelope_count` to 1 instead of deriving it from the packed tasks |
| 201 | Disabled build server logs a WARNING per build (= 031, 046, 109) |

## Sweep 2026-10-15 — 97 inbox messages (84 `pm-mcp-core-m2-m4-203`..`-286`, 13 late arrivals)

Input was the epic's own inbox (corpus: 0). The 84 `pm-mcp-core-m2-m4` messages came from pm-mcp-core plans (opencode and Claude Code); the 13 late arrivals from `api-sheriff-kidicap-gateway-requirements` (API-Sheriff plan `32-early-answer-it-timeouts`, PR cuioss/API-Sheriff#466) landed mid-run and were graded in the same run. Operator rulings this run: all five `pm-mcp-core` borderlines graded **high** (224, 232 framework-skill over-attachment; 247 verification scope plus `.md` false-pass; 252 module ADR collisions; 267 pre-push DEGRADED on Maven); late-arrival 006 graded **medium**. Nothing re-checked in code — filed items rest on the sender's verification and the triage record; medium/low rest on the message text.

### `filed-live-blockers/` (40 messages, 15 filings)

| Filing | Level | Messages | Subject | Owner today |
|---|---|---|---|---|
| `lessons-routing-029` | high | pm 203, 213, 240, 265, 285 | Sibling-repo deliverable lifecycle (recurrence of `-018`) | `-018` |
| `lessons-routing-030` | high | pm 204, 218, 231, 235, 245, 254 | Sourcery review-budget refusal not a registered refusal pattern | none |
| `lessons-routing-031` | high | pm 205, 216, 229, 237, 250, 267 | Gate-bundle derivation zero on Maven; pre-push gate DEGRADED | none |
| `lessons-routing-032` | high | pm 212, 226, 238, 248, 266, 274 | Deep-lane outline without the assessment pass (recurrence of `-022`) | `-022` |
| `lessons-routing-033` | high | pm 225, 283 | Q-Gate deliverable-hash skip has no hash primitive (recurrence of `-023`) | `-023` |
| `lessons-routing-034` | high | pm 230 | Triage fix-task shape under deliverable 0 rejected by commit-add (recurrence of `-020`) | PLAN-LB-26 |
| `lessons-routing-035` | high | pm 234 | Staged-spec premise invalidated by a sibling landing | none |
| `lessons-routing-036` | high | pm 242, 252 | Per-package ADR numbers collide; pre-merge gate misses them | none |
| `lessons-routing-037` | high | pm 247, 253 | Verification scoped to the wrong files; Sonar confirms a stale analysis | none |
| `lessons-routing-038` | high | pm 255 | Phase-4/5 subagents self-transition before the orchestrator Q-Gate | none |
| `lessons-routing-039` | high | pm 224, 232 | Task skill resolution attaches framework skills the module forbids | none |
| `lessons-routing-040` | high | as 001, 002, 003 | Outline assessments miss files, lack backing, outlive refuted designs | none |
| `lessons-routing-041` | high | as 005 | Staged diagnose-then-fix plans have no declared task deferral | none |
| `lessons-routing-042` | high | as 012 | `worktree-remove` from a stale-cwd shell fails after move-back | none |
| `lessons-routing-043` | high (inherited) | as 011 | ci-verify triage recurrence, evidence for `-019`, no new item | PLAN-LB-24 |

`pm` = `pm-mcp-core-m2-m4-NNN`; `as` = `api-sheriff-kidicap-gateway-requirements-NNN`.

### `medium/` (45)

| Messages | Subject |
|---|---|
| pm 206, 215 | Re-verify from a clean build after a rebase (stale `target/` fixtures) |
| pm 207, 220 | Sibling-checkout search fallback and footprint false-fails on sibling/read-intent paths |
| pm 208, 222 | Finalize dispatches emit no `DISPATCH` telemetry (ad-hoc and loop-back re-fires) |
| pm 209, 211, 241 | Change-ledger rows: short-SHA duplicates; Maven runs write no build row (thrice) |
| pm 210 | `review_completeness --participated-bots` rejects a bare bot name (caller UX) |
| pm 214 | Quality-gate rewrites accepted blind, flagged by Sonar (project review discipline) |
| pm 217 | Worktree-rebase drift probe errors without a marketplace root |
| pm 219 | Unified triage pending count mismatches the findings store |
| pm 221 | Subagent hand-backs counted as operator turns in `extract-signal` |
| pm 223, 236, 280 | Outline/phase self-transitions before the Q-Gate (sequencing, re-open) |
| pm 227 | Cross-module log-record change left untested by the module_testing split |
| pm 233 | Additive-only `affected_files` sync cannot prune renamed paths |
| pm 246, 264 | Outline sequencing and construction-site sweep gaps (Q-Gate caught) |
| pm 249, 256 | Docs-only loop-back reruns full verify; pre-push docs assume marketplace shape |
| pm 251 | Sonar prerequisite wording induces invented notation |
| pm 257, 258, 262 | Skill/domain detection gaps (framework ban, Java-as-docs, project-local carry) |
| pm 259 | Scope-creep check re-reports accepted gate/operator files |
| pm 261 | Architecture inventory blind to `.pmwf` fixtures |
| pm 263 | Review-driven correction opened a fail-open (pm-mcp-core discipline) |
| pm 268, 271 | Sourcery pronoun-variant refusal plus declined-comment leak |
| pm 269, 284 | Finalize dispatch boundaries and zero-usage rows (metrics only) |
| pm 270 | Read-intent references graded `CERTAIN_INCLUDE` (false unrealised signal) |
| pm 275 | Consumer sweep missed a cross-module log-text test |
| pm 276 | Pre-commit rewrite of untouched files trips scope-creep (114 files) |
| pm 279 | `change_type` heuristic overconfident on the word "verification" |
| pm 286 | Whole-tree verify inside a leaf hits the timeout cap (scoping rule) |
| as 004 | Doc deliverable named an insertion point by paraphrase; no such section |
| as 006 | Deliverable risk-mitigation gate not carried into task text (operator: medium) |
| as 007, 008 | Throwaway-branch deletion owner; exemplar-mirroring rationale import |
| as 009 | Operator re-scope left a stale "unchanged" claim after loop-back |
| as 010 | `ci checks logs` argparse rejections on unquoted free text |

### `low/` (12)

| Messages | Subject |
|---|---|
| pm 228 | Stale `target/test-classes` after rebase (local Maven hygiene) |
| pm 239 | Pattern-uniqueness claim written without a content sweep |
| pm 243, 244 | ADR backfill overclaim; triage loop-back budget sizing (same PR) |
| pm 260 | Dispatch-boundary rows lack `step_id` (metrics observability only) |
| pm 272, 273 | Invented `qgate query` verb; `architecture search` flag misuse |
| pm 277 | Residual dual-path audit-log write (single-plan, review caught) |
| pm 278 | Code-review verdict guidance on `failure_class "none"` |
| pm 281, 282 | Build-wrapper timeout and build-before-commit freshness (single-repo tuning) |
| as 013 | Build-server `timeout` under foreign machine load (environmental, re-submitted green) |

### `stale/` (0)

No message refuted at ground truth this run; nothing filed as stale.

## Sweep 2026-10-23 — 31 corpus lessons + 116 inbox messages

Both refills were ingested in one run (operator decision): the corpus held 31 active lessons and the epic inbox held 116 live messages (`pm-mcp-core-m2-m4-287`..`-402`). Corpus: 0 active after the run (one pre-existing non-active record remains). Inbox: 0 live, 0 invalid after the run.

`pm` below = `pm-mcp-core-m2-m4-NNN`.

**Two operating constraints applied this run.**

1. **`live-blockers`' FOCUS RULE (2026-10-23)** — "high and blocking issues only, no fine-tuning; token usage and measurement are out of scope" — governs what may be filed there. It outranks this sweep's own grading: a drafted filing for the head-dependent re-fire cost cluster (7 sources) was **withdrawn** rather than routed, and its members archived as `medium`. The withdrawal note is `filed-live-blockers/lessons-routing-047.md`, which is a record, not a message — the destination inbox allocated no `-047`.
2. **Archive convention for messages.** Prior sweeps copied every message body into `medium/`/`low/`. This run keeps the authoritative verbatim body where the channel already puts it: `inbox/archive/{sender}/`. One consolidated body per FILED cluster lives in `filed-live-blockers/` (the filing payload itself). No message body was retyped, so nothing can drift; the mapping from message to level is this table.

No fresh code re-verification was performed: filed items rest on the senders' own verification at the shas they cite, and the `medium`/`low` grades rest on the message text and the lessons' own ground-truth notes. The two `already-covered` corpus lessons were re-read against the live-blockers filings they name.

### `filed-live-blockers/` (14 filings, 74 sources)

| Message | Level | Sources | Subject | Owner today |
|---|---|---|---|---|
| `lessons-routing-044` | high | corpus `2026-10-22-12-001`; pm 298, 299, 303, 304, 305, 315, 316, 318, 319, 320, 343, 357, 360, 361, 362, 363, 379, 381, 382, 394, 402 | Script surface drift: documented verbs/flags the scripts do not declare; `--plan-id` treated as universal; parse-only executor mode + doc sweep | recurrence of `-023`/`-033` |
| `lessons-routing-045` | high | pm 290, 306, 308, 321, 335, 388 | Executor version/target skew invisible; consumer repos silently run a stale executor; workflow notations resolved against `marketplace/bundles` | PLAN-LB-43 staged |
| `lessons-routing-046` | high | pm 307, 344, 345, 350, 366, 380, 396 | A history rewrite invalidates the change ledger; guarded 5→6 transition refuses; no sha remap; delta base gone | none |
| `lessons-routing-047` | — | (draft) | **Withdrawn, not filed** — head-dependent re-fire cost, excluded by the destination focus rule | — |
| `lessons-routing-048` | high | pm 294, 352 | Task closes before its verification runs; the verification-owed hold is lost | none |
| `lessons-routing-049` | high | corpus `2026-10-10-20-006`; pm 296, 297, 339, 369, 370, 371, 372 | Declared footprint omits what the plan will touch (referrers, restated names, read sets, developer guides, cross-module, write-replace targets) | none |
| `lessons-routing-050` | high | corpus `2026-10-12-05-002`, `2026-10-13-14-001`, `2026-10-13-14-003`; pm 309, 323, 353, 365, 384 | Review-bot registry: Sourcery budget refusal, CodeRabbit size refusal, participation from an edited comment, cross-PR trigger-B, size caps before create-pr | recurrence of `-030`; PLAN-LB-46 staged |
| `lessons-routing-051` | high | corpus `2026-10-10-20-008`; pm 292, 311, 337, 367, 385 | Leaves denied Grep have no sanctioned search over resource trees or sibling checkouts; false greens (security audit 5 of 17) | none |
| `lessons-routing-052` | high | corpus `2026-10-11-06-003`, `2026-10-11-16-005`; pm 312, 328, 386 | Manifest composes unresolvable verification steps; tier oscillation and whole-tree hand-backs | none |
| `lessons-routing-053` | high | corpus `2026-10-11-16-001`, `-002`, `-003` | Finalize verification integrity: ci-verify producer accept-set, finding attribution, root-level guards skipped | PLAN-LB-58 staged |
| `lessons-routing-054` | high | corpus `2026-10-11-16-004` | Merge-lock ownership keyed on `plan_id`; a same-plan session can release another's lock | none |
| `lessons-routing-055` | high | corpus `2026-10-11-06-001` | `format_toon` is a second projection; `to_dict` fields silently dropped from default output | none |
| `lessons-routing-056` | high | corpus `2026-10-13-07-002` | Free-text placeholders in documented commands are not shell-quoted | partially shipped (LB-37) |
| `lessons-routing-057` | low | pm 401 | Domain content (`pm-documents`): "declared once" is a claim about every consumer | none |

**Archive-file numbering.** The destination allocator numbered only messages it actually wrote: `044`, `045`, `046`, then `047`..`057` (13 messages; `-047` was never allocated because the draft of that number was withdrawn). The archive files under `filed-live-blockers/` keep the DRAFT numbers, so from `048` onwards the filename is one higher than the message it carries: file `048` → message `047`, `049` → `048`, …, `058` → `057`. The message column above is authoritative.

### `medium/` (67 sources, grouped by cluster; not filed)

| Sources | Subject |
|---|---|
| corpus `2026-10-13-07-001`; pm 288, 324, 333, 347, 383 | Head-dependent finalize steps re-fire on every HEAD advance (withdrawn filing — destination focus rule) |
| corpus `2026-10-10-06-002`, `-003`, `-004` | Lessons-housekeeping empty-corpus dispatch; non-active population unnamed; `display_detail` 80-ASCII contract |
| corpus `2026-10-10-20-005` | `manage-lessons consult` does not resolve a worktree-hosted plan directory |
| corpus `2026-10-10-21-001`; pm 287, 336, 346 | Sonar: unconfigured vs `internal_error`; stale-analysis issue list; re-reported Sonar keys |
| corpus `2026-10-10-21-002`, `2026-10-11-06-002`, `2026-10-11-16-006`; pm 291, 400 | Test adequacy: order-dependent load, inconsistent Maven fixture, xdist-suffixed ids, tests that pass on the old code, vacuous refusal-path assertion |
| corpus `2026-10-10-06-001`; pm 329 | `manage-tasks`: no verification write-back; `deliverable: 0` rejected for fix tasks |
| corpus `2026-10-11-06-004`; pm 300, 326, 373, 390, 391 | Footprint amendment during execution: prune on revise, sanctioned widening, create-then-delete, decision re-sync |
| corpus `2026-10-11-16-007`; pm 314, 355 | Review grading discipline: over-graded blocking finding, nitpicks in summary bodies, no `superseded` criterion status |
| corpus `2026-10-12-05-001`; pm 393 | Build hygiene: stale `uv.lock` on main; build-server wait-log spam |
| corpus `2026-10-13-14-002` | Retrospective footprint over a stacked landing |
| corpus `2026-10-13-14-004`; pm 302, 325, 334, 354, 364, 387, 392 | Dispatch-boundary/execution-log accounting: keyless rows, missing re-fires, zeros for uncaptured usage |
| pm 289, 351, 374, 375, 376, 377, 378 | Success criteria that cannot be evidenced at review time (PR body, foreign-repo PR, external link check) |
| pm 293, 330, 358, 359 | Worktree and sibling-repo path handling (`../{sibling}` breaks; cross-repo deliverable module) |
| pm 313, 341, 398, 399 | False self-reports; guarantee restatements; verification-claim provenance |
| pm 317 | Phase handshake reports drift when a Q-Gate was legitimately resolved after capture |
| pm 332 | Baseline drift checked against committed files only, not pending tasks' declared files |
| pm 338 | A Q-Gate premise about file locations verified against prose, not the tree |
| pm 348, 349, 368 | Merge-queue body trimming; ADR duplicate-number gate scope; HEAD-bound merge consent reuse |
| pm 356, 395, 397 | Retrospective: self-reported gh/grep not counted; compile-report section defects; inotify exhaustion misattributed |
| pm 301 | Refine offers no concrete proposed names in a rename question (**low**) |

### `already-covered/` (5 sources)

| Source | Covered by |
|---|---|
| corpus `2026-10-13-07-003`; pm 295, 310, 327 | live-blockers `lessons-routing-039` (also `-024`): framework skills attached where the project forbids them; no project-level exclusion filter |
| corpus `2026-10-13-07-004` | live-blockers `lessons-routing-025`: cui-http-testing needs single-use stubs and loopback-family rules |

### `stale/` (0)

Nothing refuted at ground truth this run.

### Dispositions

| Disposition | Count |
|---|---|
| clustered-into (14 filed clusters + 24 archived clusters) | 142 |
| already-covered | 5 |
| standalone | 0 |
| stale | 0 |
| **total** | **147** |

## Sweep 2026-11-01 — 61 lessons from two sibling checkouts (cross-repo)

Input was the local lesson stores of the two sibling checkouts that hold any: `API-Sheriff` (43 lessons, 2026-10-02 to 10-14; a Maven consumer of plan-marshall) and `TokenSheriff` (18 lessons, 2026-10-29 to 10-31). The other sibling checkouts have no lessons directory. This epic's own corpus was empty. Remote lesson text is externally-sourced; every claim here rests on that text, and a lesson was not re-verified at HEAD unless a line says so.

**Relevance.** 46 of the 61 are about plan-marshall or its bundles and were taken in; 15 are specific to the consumer project (see `Not applicable` below) and stay where they are. **Archive layout.** Remote ids collide with this repo's own (`2026-10-13-14-001`..`-004` already exist under `high/` and `medium/`), so the copies are verbatim under a per-repo subdirectory: `{level}/{repo}/{lesson-id}.md`. The consolidated body of each filing is `filed-live-blockers/sweep-2026-11-01/lessons-routing-NNN.md`, and there the file number equals the message number. They sit in a subdirectory because the root `filed-live-blockers/lessons-routing-058.md` already holds the earlier sweep's DRAFT 058 (message `-057`, see the numbering note above).

**Operator rulings this run.** Three borderlines were put to the operator and each graded **high**: the no-progress rule (`-059`), the pre-merge head binding (`-060`) and the Surefire parser false positive (`-061`). Two of them sit against `live-blockers`' FOCUS RULE (high and blocking only); the operator ruling outranks it, and each message states that it is an operator grade.

### `filed-live-blockers/` (6 filings, 19 sources)

| Message | Level | Sources | Subject | Owner today |
|---|---|---|---|---|
| `lessons-routing-058` | high (inherited) | API `2026-10-12-16-001`, `-16-005`, `-16-008`, `2026-10-13-14-003` | Consumer-repo fit: assessment-coverage check on the deep lane, ci-verify producers `verification-feedback` rejects, Maven pre-push gate degraded; new: a step with no implementor records `done` | recurrence of `-022`, `-019`, `-031`; the `done`-vs-`skipped` item has none |
| `lessons-routing-059` | high (operator) | API `2026-10-12-16-007`, `2026-10-12-07-007` | The no-progress rule records a prescribed phase-5 yield as `error` | none |
| `lessons-routing-060` | high (operator) | TokenSheriff `2026-10-31-13-002` | Pre-merge head binding voids every gate on a late commit; a waiver the step record accepted is refused at merge | PLAN-LB-55, PLAN-LB-101 shipped; consumer plugin version unknown |
| `lessons-routing-061` | high (operator) | API `2026-10-12-07-015` | Maven log parser files a `test-failure` for a passing Surefire summary with `Skipped` above zero | none |
| `lessons-routing-062` | medium | API `2026-10-02-12-007`, `2026-10-12-07-011`, `2026-10-13-06-001`, `-06-002`, `-06-003`, `2026-10-13-14-004`, `2026-10-12-16-009`, `-16-010`; TokenSheriff `2026-10-31-12-006` | Domain content (`pm-documents`): a stated guarantee, count or closed list is not checked against what enforces it | sibling of `-057`; none |
| `lessons-routing-063` | medium / low | TokenSheriff `2026-10-29-23-001` (medium), `2026-10-29-23-003` (low) | Domain content (`pm-dev-java`): `SecureRandom` in native-image code; U+2028/U+2029 as Unicode escapes | none (searched: only the crypto standard names `SecureRandom`; no Java standard names U+2028) |

Messages `-058`..`-063` were written to `live-blockers/inbox/` in one run and are undrained at the end of it. `live-blockers` is open (`phase: orchestrating`). Domain-content filings `-062` and `-063` are below that epic's FOCUS RULE and may be discarded there; they are filed because RULING 2026-10-09 files domain content at any severity.

### `medium/` (11, not filed)

| Lessons | Subject |
|---|---|
| API `2026-10-12-07-001`, `2026-10-12-16-006` | A build `status: timeout` is not "the build ended" (teardown destroyed a running build); the build daemon's 1800 s default is shorter than a full Docker integration run and a timed-out run tears nothing down. Same subject as pm 197, 281, 282 and as 013 |
| API `2026-10-12-07-009` | The merge-queue wait budget is shorter than the queue's own required checks, so the deferred path is the normal path |
| API `2026-10-12-07-006` | `-Dtest=A+B` matches nothing and passes with zero tests; the planning step stamped the wrong form (related to `-061`) |
| API `2026-10-12-07-014`, `2026-10-12-16-002`, `2026-10-12-16-003`, `2026-10-14-13-001`; TokenSheriff `2026-10-31-13-005` | Outline and task-plan quality: a mitigation that moves a fix into a later deliverable, a test task paired with a doc-only implementation task, operator answers not written back into `solution_outline.md`, success criteria that cannot be evidenced before the grading gate, closed-set docs missing from the footprint (same subject as `as 004`, `006`, `009`) |
| TokenSheriff `2026-10-31-13-004` | Bookkeeping slips: a change-ledger row per out-of-task commit, the commit trailer checked before the first commit, phase transitions left to the orchestrator (see pm 209, 211, 241) |
| TokenSheriff `2026-10-31-13-006` | The PR body goes stale after loop-back fix tasks and is the squash-merge commit message |

### `low/` (15, not filed)

| Lessons | Subject |
|---|---|
| API `2026-10-12-07-004`, `2026-10-12-07-008`, `2026-10-13-14-005` | One finalize ceiling shared by self-review, CI and review-bot rounds (pm 243, 244); `adr-propose` skipped after a hand-driven final round; description-drift check flags a count derived from an enumerated outline list |
| API `2026-10-12-07-012`; TokenSheriff `2026-10-31-12-003`, `-12-007`, `-12-009` | Test adequacy (the existing cluster of the 2026-10-23 sweep): a guard needs a negative control, wall-clock boundary tests need margin plus a hit assertion, leak assertions must test the real input, one throwing call per `assertThrows` |
| API `2026-10-12-07-003`, `2026-10-12-07-013`, `2026-10-12-16-004`, `2026-10-13-06-004`, `2026-10-13-06-005`; TokenSheriff `2026-10-31-13-001`, `-13-003`, `2026-10-29-23-002` | **Already covered.** Self-review does not converge (`-001`); invented verbs and flags — `qgate query` in three plans, `--number`, `--plan-id` placement, Maven `resolve-test-scope` (`-044`, pm 144, 157..161, 272, 273); docs-only fix re-fires every head-dependent step (`-005`, the withdrawn `-047`); CodeRabbit one-review-per-hour quota (`live-blockers` ruling: wait); script surface drift (`-044`); log injection from parser exception messages (`persona-security-expert` secure-logging and `cui-logging` standards) |

### `stale/` (1)

| Lesson | Why |
|---|---|
| API `2026-10-14-13-003` | The premise — a merge hold written in the epic ledger cannot reach a running plan — is answered by the addressee mailbox: `inbox write --target-plan` delivers to a running plan's `inbox/to/{plan_id}/`, and a plan reads it with `inbox read` (checked in the installed `orchestration-model.md` Ledger Write-Boundary). Whether it is a reliable hold is a separate question the lesson does not ask. |

### Not applicable — left in the source checkout (15)

| Lessons | Why |
|---|---|
| API `2026-10-02-12-008`, `2026-10-12-07-002`, `2026-10-12-07-005`, `2026-10-13-14-002` | Keycloak realm fixture, Rancher Desktop/WSL2 dead host ports, the project's native CI job limit: host and project facts |
| API `2026-10-12-07-010`, `2026-10-12-16-011`, `2026-10-12-16-012`, `2026-10-12-16-013`, `2026-10-14-13-002`, `2026-10-13-14-001` | k6 behaviour, a Sonar literal, a flaky edge test, a missing library accessor, an exception handler's rationale, a diagnosis made by reading code (`2026-10-13-14-001` is Principle 8 of the foundational persona; its own scope hint says not a plan-marshall component) |
| TokenSheriff `2026-10-31-12-001`, `-12-002`, `-12-004`, `-12-005`, `-12-008` | Async lifecycle fencing, two-slot races, a stale `~/.m2` runner, formatter import flips and OpenRewrite markers in that project's build |

### Dispositions

| Disposition | Count |
|---|---|
| clustered-into (19 in 6 filings, 11 in `medium/`, 7 in `low/`) | 37 |
| already-covered (stored in `low/`) | 8 |
| standalone | 0 |
| stale | 1 |
| not applicable (left in the source checkout) | 15 |
| **total** | **61** |

The 46 lessons taken in are the 37 clustered, the 8 already-covered and the 1 stale; the 15 not applicable are not copied.

## Sweep 2026-11-02 — inbox, 116 messages

Input was this epic's own inbox: `api-sheriff-api-sheriff-0-2-0-001`..`-078` (API-Sheriff epic api-sheriff-0-2-0), `lessons-routing-001`..`-013` (API-Sheriff observations relayed under this epic's sender id), `plan-v02-04-adr-corpus-cleanup-001`..`-007`, `plan-v02-12-idp-addressing-model-001`..`-008`, `plan-v02-46-upstream-close-after-early-answer-001`..`-005`, `pm-mcp-core-corpus-group-contamination-001`..`-005`. Corpus: 0. All 116 valid, all live, none a landing. Grading was drafted by one read-only `execution-context-level-5` leaf and adjudicated here.

Abbreviations below: `as-NNN` = `api-sheriff-api-sheriff-0-2-0-NNN`, `lr-NNN` = this inbox's `lessons-routing-NNN` (not the outbound filings), `v04-`/`v12-`/`v46-` = the three `plan-v02-*` senders, `pmc-` = `pm-mcp-core-corpus-group-contamination`. Message bodies are preserved verbatim in `inbox/archive/{sender}/`; no copy was made under `{level}/` (as in the 2026-10-23 sweep). The filed bodies live only in `live-blockers/inbox/` (no `filed-live-blockers/` copy — the messages carry the full body).

**Operator rulings this run.** Four borderlines were put to the operator, and all four were graded **high**: review-ingest fidelity (`lr-013`, `as-044`, `as-052`) and the freshness false pass (`as-078` item 2). The operator also directed that `live-blockers` `lessons-routing-060` (undrained) be amended with the waiver-refused-at-merge evidence instead of getting a new filing.

**Checked at `c431a8193`:** `_criteria_snapshot.py:72` (the bullet regex); `_review_support_integrity.py:75` (`--no-renames`) and `:81-84` (the pre-image is read at the base tip); `coderabbit.md:48-53` (the `inline` evidence needs no marker); and `refire_waiver`, which is not referenced from any `pre_merge_gate` source (`architecture search --content`). Medium and low grades rest on the message text.

### Filed to `live-blockers` (5 new filings + 1 amendment, 15 sources + 3 recurrences)

| Message | Level | Sources | Subject |
|---|---|---|---|
| `lessons-routing-064` | high | lr-008; as-036, -048, -049, -062, -063, -071 | `weakened_test` reads moves, renames and planned dedups as lost assertions, and re-raises them at every head. Shares a file with PLAN-LB-75 (parked) |
| `lessons-routing-065` | high | as-004; v46-001 | The success-criteria parser drops every criterion after a wrapped line |
| `lessons-routing-066` | high | as-055, -074 | CodeRabbit participation: thread replies credit an unreviewed head, and the new summary format is never credited (PLAN-LB-100 now blocks on it) |
| `lessons-routing-067` | high (operator) | lr-013; as-044, -052 | Review bodies are cut at 8,000 characters before the request, and a re-review's inline comments are not fetched |
| `lessons-routing-068` | high (operator) | as-078 (item 2) | The freshness gate passed on a 5-test row labelled whole-tree (residual check against LB-58) |
| `lessons-routing-060` (amended, revision 1) | high (operator, 2026-11-01) | + lr-001, lr-009, as-078 (item 1) | The merge gate ignores a `--waive-refire` that the step record accepted |

### Already covered (39, no new filing)

| Messages | Covered by |
|---|---|
| lr-001, lr-009 | `lessons-routing-060` (amended above) |
| lr-002; as-006, -016, -029, -030, -047, -051, -059 | `-044` script surface drift. `resolve-test-scope` is now declared, so its rejection was executor skew |
| lr-004; as-038 | `-051` search coverage |
| lr-007, lr-010; as-023, -067; v12-007 | `-045` executor skew; PLAN-LB-43 #1851, PLAN-LB-95 #1865 |
| as-001; pmc-002 | PLAN-LB-101 #1890 (quota wait); `-030`/`-050` |
| as-005, -022, -037, -065; v04-003; v46-005 | `-031`/`-058` (Maven module-tests DEGRADED). The zero-bundle half is fixed by #1866 |
| as-010, -031, -045, -053; v12-005; pmc-001 | `-046`; PLAN-LB-91 #1847 rebase remap |
| as-011 | `-038` leaf self-transition |
| as-014, -019, -026 | `-022`/`-032`/`-058` outline assessments |
| as-040, -061; v04-006 | `-042` stale cwd after cleanup |
| v12-004 | `-059` no-progress hand-back |

### `medium/` (50, not filed — bodies in `inbox/archive/`)

| Cluster | Messages |
|---|---|
| Head-dependent re-fire cost (cost class, outside the FOCUS RULE; precedent: the withdrawn `-047`) | lr-012; as-025, -034, -043, -054, -064; v04-004; v12-008 |
| Outline and plan authoring quality (the Q-Gate catches these) | lr-011; as-012, -015, -018, -020, -027, -028, -041, -056, -057; v46-002 |
| Finalize/review authoring traps | lr-006; as-003, -013, -042, -046, -058, -069 |
| Orchestrator spec planning | as-002, -007 |
| Build timeouts and daemon env | as-009, -035, -068 |
| build-server wait log flood | as-017, -024 |
| `q_gate_validation=once` leaves findings pending | as-021, -039 |
| Post-merge CI wait | as-032, -072; v04-007; v12-003 |
| Freshness keyed to a hash | lr-005; as-076 |
| `git-workflow commit` reports FETCH_FAILURE on an empty index | v12-001; v46-003 |
| Singletons | lr-003 (guards learned from refusal); as-050 (busy main checkout); as-060 (review body re-filed); as-070 (preference promotion); as-075 (loop-back admit spends a round); v04-001 (finalize driven from a leaf); v46-004 (`pull_request_runs` false negative) |

### `low/` (12, not filed)

| Cluster | Messages |
|---|---|
| Caller UX and contract gaps | as-073; v04-002; v12-002, -006 |
| Measurement and logging gaps (outside the FOCUS RULE) | as-077; pmc-003, -004 |
| Singletons | as-008 (spec size cap); as-033 (deliverable label); as-066 (leaf edited a tool-result copy); v04-005 (queue squash message, also as-078 item 3); pmc-005 (Sonar project key) |

### Dispositions

| Disposition | Count |
|---|---|
| filed (5 filings) | 15 |
| already-covered (incl. 3 folded into amended `-060`) | 39 |
| medium | 50 |
| low | 12 |
| stale | 0 |
| **total** | **116** |

## Sweep 2026-11-02 (second run) — 178 lessons from five sibling checkouts (cross-repo)

The input was the local lesson stores of `API-Sheriff` (91), `pm-mcp-core` (60), `nifi-extensions` (13), `TokenSheriff` (10) and `cui-jsf-test-basic` (4). The plan-marshall corpus itself was empty. Remote text is externally sourced. Grading was drafted by one read-only level-5 leaf in two passes (consolidation and dedup, then a ground-truth check at `c431a8193`) and adjudicated here.

**Coverage caveat.** The store set was found by probing sibling directory names by hand. Glob was not available, and the hook blocks shell listing, so a wildcard sweep and the one-level-deeper check were not run. Probed with no store: cuioss-organization, cui-http, cui-test-generator, cui-test-keycloak-integration, cui-test-mockwebserver-junit5, cui-test-value-objects, coderabbit, cui-portal-core, cui-java-tools, cui-test-juli-logger. Not checked out: cui-jwt, OAuth-Sheriff, pm-mcp, cui-parent-pom, pr-agent-settings. **Discrepancy with the 2026-11-01 record:** its "left in the source checkout" ids, for example API `2026-10-12-07-002` and TokenSheriff `2026-10-31-12-001`, no longer exist at those paths. API `2026-10-13-14-001`/`-002` exist with different content. Unreconciled.

**Operator rulings this run.**
- The 82 project-only lessons stay in their source checkout.
- Domain content is filed at any severity, per RULING 2026-10-09.
- The borderline build-daemon concurrency lesson is graded **high**.

**Layout.** Each lesson was moved verbatim with `mv -n` (no overwrite) to `{level}/{repo}/{lesson-id}.md`, and the filed ones to `filed-live-blockers/sweep-2026-11-02/{repo}/`. 96 destination files were verified present by `git status`. The source repos' tombstones were not written, and nothing was committed in any source repo.

### Filed to `live-blockers` (6 filings, 10 sources)

| Message | Level | Sources | Subject |
|---|---|---|---|
| `lessons-routing-069` | high (operator) | API `2026-10-04-09-002` | Build daemon runs two builds in one worktree; shared `target/` produces false failures. No per-project_dir exclusion at HEAD |
| `lessons-routing-070` | medium / low | pmc `2026-10-15-06-001`; TS `2026-10-14-06-001`; API `2026-10-15-09-002`, `2026-10-05-13-001`; cjtb `2026-06-16-09-001` | `pm-dev-java`: `Locale.ROOT` for signed bytes, URL user-info in rejection messages, S2637/S2638 flip-flop, `-Dtest` selector grammar |
| `lessons-routing-071` | low | API `2026-10-24-15-001` | `pm-dev-java-cui` cui-logging: a retired LogRecord id is reused |
| `lessons-routing-072` | medium | API `2026-10-21-19-003` | `pm-dev-oci` oci-security: quick reference signs/verifies a mutable tag (`supply-chain-security.md:28-32`) |
| `lessons-routing-073` | low | nifi `2026-07-18-21-001` | `pm-documents` ref-svg-diagrams: comma alt text, document-global `:imagesdir:` |
| `lessons-routing-074` | low | nifi `2026-06-14-21-001` | `pm-dev-frontend` jest-testing: `--silent` instead of console stubs |

### Already covered (33, stored in `low/{repo}/`)

| Lessons | Covered by |
|---|---|
| API `2026-10-04-09-004`, `-09-008`, `-09-009`, `-09-010`, `2026-10-14-20-001`, `2026-10-15-09-001`, `2026-10-15-12-001`, `2026-10-17-09-001`, `2026-10-18-06-001`, `2026-10-22-05-004`, `2026-10-27-05-002`; pmc `2026-10-11-20-001` | `-062`/`-057` stated guarantee not bound to its enforcer |
| API `2026-09-24-15-004`, `2026-10-09-13-001`, `-13-002`, `2026-10-22-05-001`, `2026-10-27-17-003` | `-049` declared footprint omits ADRs / restating sites |
| API `2026-10-03-06-003`; TS `2026-10-10-08-001` | `-007`/`-050` review-bot size caps |
| API `2026-10-03-06-007`, `2026-10-06-08-001` | `-031`/`-058` Maven pre-push gate; #1866 |
| API `2026-10-03-06-001` | `-001`/`-005` self-review non-convergence |
| API `2026-10-03-06-006` | `-044` script surface drift |
| API `2026-10-13-07-001` | `-045` executor skew; PLAN-LB-43, -95 |
| API `2026-10-04-09-003` | `-022`/`-032` outline assessments |
| API `2026-10-05-13-002` | `-038` leaf self-transition |
| API `2026-09-24-15-013` | `-017`; PLAN-LB-101 #1890 |
| API `2026-10-27-05-001` | `-051` search coverage |
| pmc `2026-10-13-06-001`, `2026-10-15-07-001` | `-018`/`-029`/`-035` sibling-repo spec drift |
| pmc `2026-10-15-07-002` | `-052` whole-tree verify in a leaf |
| pmc `2026-10-15-07-003` | `-036` ADR number collision |
| TS `2026-10-10-08-003` | junit-core `test-fork-policy.md:96-98` |

### `stale/` (5)

| Lesson | Why |
|---|---|
| API `2026-10-03-06-005` | scope_creep_check fixed by #1745 (`370f42379`) |
| API `2026-10-05-18-002` | Maven reactor test count fixed by #1750 (`2fd164ec9`) |
| nifi `2026-07-17-17-002` | Doc tasks get skills: `pm-documents` `plan-marshall-plugin/extension.py:119-127` |
| pmc `2026-10-15-06-004`; API `2026-10-24-15-002` | cui-logging row sync and emitting test already stated (`logmessages-documentation.md:145-155`, `SKILL.md:27,125`) |

### `medium/` (18, not filed — message text only unless noted)

| Cluster | Lessons |
|---|---|
| Base drift during long finalize | API `2026-10-03-06-002`, `2026-10-27-17-001`, `2026-10-29-09-003` |
| Build timeouts / daemon env | API `2026-10-03-06-008`; TS `2026-10-19-08-002` |
| Outline authoring (survey lists, finalize obligations, in-file entries) | API `2026-10-04-09-005`, `-09-006`; pmc `2026-10-18-06-001` |
| Singletons | API `2026-10-03-06-004` (queue-landing wait); API `2026-10-05-13-003` (whole self-review in a leaf); API `2026-10-06-08-004` (`pull_request_runs` false zero); API `2026-10-09-13-006` (self-review closes with unchecked items); API `2026-10-13-18-001` (duplicate plan hand-off — `launched` status exists at HEAD; residual unchecked); API `2026-10-28-05-001` (staged spec claims ungrounded); TS `2026-10-10-08-004` (unexecuted test reported verified); TS `2026-10-10-08-006` (Maven module-scoped commands below package); nifi `2026-07-16-21-002` (change-ledger build row in worktree); pmc `2026-10-13-13-003` (sibling-relative paths under plan worktrees) |

### `low/` (30, not filed)

| Cluster | Lessons |
|---|---|
| Test adequacy (consumer practice) | API `2026-09-24-15-003`, `-15-009`, `2026-10-05-18-001`, `2026-10-28-05-002`, `2026-10-29-09-001`, `2026-10-30-05-001`; TS `2026-10-10-08-002` |
| Request/outline premises from prose | API `2026-09-24-15-006`, `-15-007`, `-15-011`; nifi `2026-06-22-18-001` |
| Review-bot suggestion triage, fix rounds | API `2026-10-27-14-001`; nifi `2026-06-22-15-001`; pmc `2026-10-15-07-004` |
| Module-mapping validator cross-module pairs | API `2026-10-09-13-004`; TS `2026-10-19-08-001` |
| Sonar visible only in CI / PR scan scope | API `2026-10-09-13-009`; pmc `2026-10-10-07-009` |
| Process discipline | API `2026-10-04-09-001`, `2026-10-06-08-003` |
| Recipe near no-op; Sonar HTTPS config | cjtb `2026-06-15-18-001`, `2026-06-16-09-002` |
| Singletons | API `2026-10-04-09-007` (keyword_drift FP); API `2026-10-05-13-004` (docs-only skip cost); API `2026-10-09-13-007` (formatter style flips); API `2026-10-09-13-010` (footprint on mid-finalize split); API `2026-10-25-22-001` (JaCoCo append); API `2026-10-29-09-002` (stale file:line citations); TS `2026-10-10-08-005` (owed architecture hint); nifi `2026-07-16-00-001` (Surefire `@Nested` count) |

### Not applicable — left in the source checkout (82)

cui-jsf-test-basic 1, nifi-extensions 6, TokenSheriff 1, pm-mcp-core 49, API-Sheriff 25: the consumer project's own code, tests, docs, CI or host. They are exactly the lesson files still present in each store after this run.

### Dispositions

| Disposition | Count |
|---|---|
| filed (6 filings) | 10 |
| already-covered | 33 |
| medium | 18 |
| low | 30 |
| stale | 5 |
| not applicable (left in source) | 82 |
| **total** | **178** |
