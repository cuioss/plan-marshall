# Epic: Live Blockers

slug: live-blockers

> Hand-written narrative for one epic under `.plan/orchestrator/live-blockers/`. The layout and
> authority contract live in the central standard — see
> `persona-plan-orchestrator/standards/orchestration-model.md`. The ledger JSON files
> (`status.json`, the `queue/{PLAN-ID}.json` rows) and `resume_anchor.md` are the machine
> authority; any statement here that conflicts with them is stale prose.
>
> START HERE and the Ordered Queue are not in this file. They live in the generated,
> git-tracked `queue-view.md` next to it (see the Persist / Stop-Resume Contract in that
> standard). `queue-view.md` is never hand-edited. A merge conflict in it is never merged by
> hand: merge the source files, run
> `python3 .plan/execute-script.py plan-marshall:plan-orchestrator:orchestrator regenerate-view --slug live-blockers`
> on the merged tree, and `git add` the result.

## Vision

plan-marshall's workflow machinery is being rewritten as plan-marshall-mcp, and until that ships
plan-marshall stays in daily production use. This epic holds the work that cannot wait for the
rewrite: defects that make a normal plan run fail, mislead or need an operator override today,
and high-priority work on things the rewrite does not replace — harness sync, organisation CI,
the review bots and their rollout. It is too large for one plan because the 21 fixes sit on
different surfaces and most are independently shippable. The epic is done when a plan can run
from init to merge in this repository and in a consumer repository without a manual override,
and the review gate can be trusted to mean what it says.

The epic was cut on 2026-10-07 from a sweep of the nine epics active at the time and the lessons
store. Eight of those epics were closed and archived in the same act; `lessons-routing` stays
active. Design input for the rewrite is not carried here: it lives in plan-marshall-mcp's
requirements, specification and implementation-watch documents.

## Queue annotations

The queue was regrouped on 2026-10-08 (see Decisions); PLAN-LB-01 to PLAN-LB-13 and PLAN-LB-15
to PLAN-LB-21 are `superseded` and their spec files stay as the record of the first cut. The
live rows and their state are in `queue-view.md`; this zone keeps only notes the view cannot
derive, for rows still live.

> ↪ Relocated to `settled.md` § "Queue annotations for shipped, superseded and drained work" — their plans shipped or were superseded and their drains were consumed; moved on 2026-10-14 by operator override of the annotation-zone rule.

- **Where each earlier plan went.**
  - PLAN-LB-22 finalize-loop-control — PLAN-LB-10, PLAN-LB-02, PLAN-LB-05 D5.
  - PLAN-LB-23 verify-builds — PLAN-LB-12, PLAN-LB-01.
  - PLAN-LB-24 review-step — PLAN-LB-05 D3, PLAN-LB-18, PLAN-LB-19.
  - PLAN-LB-25 phase-and-merge-gates — PLAN-LB-09, PLAN-LB-05 D1 and D2, PLAN-LB-04.
  - PLAN-LB-26 execute-loop-triage — PLAN-LB-06, PLAN-LB-05 D4, PLAN-LB-08.
  - PLAN-LB-27 plan-footprint — PLAN-LB-07, PLAN-LB-11.
  - PLAN-LB-28 java-consumer-repos — PLAN-LB-13, PLAN-LB-03 (labelled a weak merge in its header).
  - PLAN-LB-29 harness-sync — PLAN-LB-15, PLAN-LB-17.
  - PLAN-LB-30 org-ci-release — PLAN-LB-16, PLAN-LB-20 D1 to D3.
  - PLAN-LB-31 in-house-reviewer — PLAN-LB-21, PLAN-LB-20 D4 and D5.
  - PLAN-LB-14 launch-gate-scope — unchanged.

- **PLAN-LB-39** (shipped #1768, 2026-10-14) — 0 met / 4 partial / 3 unmet against its spec,
  counted 7/7, five regressions; see `landings/PLAN-LB-39.md`. Fix-forward PLAN-LB-50; unshipped
  deliverables re-staged as PLAN-LB-51 (Antigravity) and PLAN-LB-52 (harness-agnostic, as scripts).

- **PLAN-LB-48** (shipped #1830, 2026-10-21, runbook lane) — all five Done-whens met, D5 and D2 partial against
  their bullets; grade B−; see `landings/PLAN-LB-48.md`. Fix-forward **PLAN-LB-83** (WS-04, runbook lane,
  medium; emit it after PLAN-LB-49, which is already executing and shares `opencode_runtime.py` but not its functions). #1830 moved
  files PLAN-LB-49 (`opencode_runtime.py`, `contract.md`, `no-op-policy.md`, `test_opencode_runtime.py`,
  `test_manage_metrics_enrich.py`) and PLAN-LB-43 (`generate_executor.py`, `marshall-steward/SKILL.md`,
  `test_variant_emitter.py`, the steward and executor tests) declare: re-read their line references at
  outline. PLAN-LB-73 D1 gained the trailerless-merge-commit bullet; PLAN-LB-49 and PLAN-LB-81 gained a
  re-ground note (no surface change).

- **PLAN-LB-78** (shipped #1834, 2026-10-22, runbook lane) — D2 and D3 met as written, D1 shipped-modified with two
  spec clauses unsatisfiable (D1.1b, D1.3: the run is right); grade B−; see `landings/PLAN-LB-78.md`. Fix-forward is
  **PLAN-LB-73 D4** (the build-gate text and `resolve` it shipped: a routed build's executor is not supplied by
  worktree creation, the text contradicts itself on routing, the lane text is not re-read after a compaction, a
  restart or an idle gap) and two bullets in **PLAN-LB-84** (a mixed-variant `effort`, a source-manifest
  `plugin_version`). PLAN-LB-73 is now unblocked: re-read its line references at outline, #1834 moved the sections.
  The landing's `order=test-first` over-counts (the committed Maven and no-gate tests were rewritten after the fix and
  never run at base); its `total_tokens=unknown` hides 5.30M input+output+reasoning and $0.91 the session store holds.

- **PLAN-LB-49** (shipped #1833, 2026-10-22, plan-marshall lifecycle, OpenCode) — grade C+; see
  `landings/PLAN-LB-49.md`. The reader, root resolution and the multi-root enrich are in `main`, and the landing
  carries a measured `total_tokens` for the first time on OpenCode. It is not the cost: 16,614,516 sums one
  main-context phase and five sub-agent phases (63% of the store's 26.3M input plus output; reasoning, cache and cost
  left out), `subagent_tool_uses` is a measured `0` in all six phases, and D3's Done-when is not met as written. The
  landing's fence has a space after the backticks, so `landing-check` reads none of its thirteen keys. Fix-forward:
  **PLAN-LB-86** (WS-04, runbook, high: tool use, reasoning, cost, the total's population, re-entered phases, session
  identity, a real fixture-database test), **PLAN-LB-87** (WS-04, runbook, medium: boundary rows' step id and unmeasured
  spend, gate-route build duration, retrospective after metrics, the `pwx` resolution), **PLAN-LB-84 D6** (the fence),
  **PLAN-LB-85 D4** (the consumer-visible field set in the spec template). Spec line references moved: PLAN-LB-84
  (`runtime_info.py`, the recursive-query hypothesis is obsolete), PLAN-LB-83 (`opencode_runtime.py`, +222 lines),
  PLAN-LB-73 (`runtime_info.py`). PLAN-LB-84 is no longer held on PLAN-LB-49; it now sequences after PLAN-LB-86.

- **PLAN-LB-85** (shipped #1839, 2026-10-22, runbook lane, `deepseek-v4.1-flash/high`, confirmed in the store) — grade
  B; see `landings/PLAN-LB-85.md`. D1, D2 and D4 delivered; D3 is 2 of 3 clauses, clause 3 being a
  preservation claim that cannot fail (a spec error). The lane now resolves its Sonar state, reads a pull request's open
  issues through the plan-less `read_open_issues` verb and gates the merge on `sonar-gate`. **The Sonar figure for its
  own PR is `unknown`** (the verbs were unreachable through the stale executor and the bootstrap was refused by the
  guard). The landing is the first runbook landing whose guard-log attribution matched `guard.log` exactly by session tree, and the
  first to re-read the lane text on its own after a server restart (25 s later). Store facts: 4 sessions, none killed,
  2.10M input+output (2.23M with reasoning), $1.00, 8 h 37 min; `total_tokens` was written `unknown` regardless, and
  `ls` was under-reported (4, not 2). Realized footprint moved `runbook-lane/SKILL.md`
  and `runbook_lane.py` (PLAN-LB-73, 89, 69), `sonar.py` and the sonar `SKILL.md` (PLAN-LB-58) and
  `landing-payload-spec.md`, `landing-analysis.md`, `plan-spec.md` (PLAN-LB-84, 69): re-read their line references at
  outline. Added surface outside the declaration: `ext-point-triage.md`, `findings-pipeline.md` (one line each, the
  provider contract is now three verbs). PLAN-LB-73 and PLAN-LB-89 are unblocked on this plan.

- **PLAN-LB-88** (shipped #1840, 2026-10-23, runbook lane, `deepseek-v4.1-flash/high`) — grade B; see
  `landings/PLAN-LB-88.md`. D1-D4 delivered. Residual guard boundaries (a `git -C ... grep` in the OpenCode guard, a script
  run by a script, an absent table) are accepted under the focus rule. Fix-forward: none.
- **PLAN-LB-86** (shipped #1841, 2026-10-23, runbook lane, `deepseek-v4.1-flash/high`) — grade B−; see
  `landings/PLAN-LB-86.md`. OpenCode measurement chain: out of scope by the focus rule, so only the process was analysed.
  Lane text not re-read across a restart; a killed round-3 self-review sub-agent is missing from the report. Fix-forward: none.

- **PLAN-LB-73** (shipped #1843, 2026-10-23, runbook lane, `deepseek-v4.1-flash/high`) — see
  `landings/PLAN-LB-73.md`. D1-D4 all landed; the merged tree carries `executor-skew`, `build-routing`,
  `build_missing_canonicals` and the `executor_absent_from_worktree` reason. Sonar `0 confirmed` re-read on the PR and
  agreeing with the landing. Declared 7 entries, realized 3, **no expansion** (the four untouched declarations are
  over-declaration, not under-declaration), so no spec surface needed correcting. The report is accurate where checkable:
  two CodeRabbit findings rounds, the guard line, the commit trailer and the merge sha all corroborate. Debit: the landing
  is `complete: false` on `total_tokens` (recurrence 2 of the PLAN-LB-49 entry), and it reports two shell file reads the
  guard cannot see. Grading deferred to the audit pass; the report's disclosures are the strongest of any runbook run so far.

- **PLAN-LB-44** (shipped #1848, 2026-10-23, runbook lane, `deepseek-v4.1-flash/high`) — see
  `landings/PLAN-LB-44.md`. D1-D3 all landed; every declared file was touched and the "Red CI has no triage route"
  Open Defect is retired on the merged code. Two checkable conduct claims hold exactly (both guard refusals, the
  CodeRabbit review at `8bba8fc`, Sonar `0 confirmed`). Debit: the realized footprint is **30 files against 11
  declared** — the vocabulary/path-anchor documentation sweep was not in the spec's surface. No collision followed,
  because none of the 19 added paths belongs to another in-flight plan, so the gate's `max_shared 0` prediction was not
  contradicted; the delta is recorded as declaration-quality evidence rather than corrected into a shipped spec.
  Self-review hit the lane's round limit and continued on an operator answer (`budget-exhausted` in the facts block).

- **PLAN-LB-92** (staged 2026-10-23, WS-04, runbook lane, operator-prioritised **next plan**) — a lane worktree has its own
  executor. Not running: PLAN-LB-73 D4 chose to check for the missing executor and record
  `executor_absent_from_worktree`, a disclosure that leaves the worktree without one. LB-92 produces it at worktree creation
  through the lifecycle's own seam (`prepare_execute._generate_worktree_executor`), adds a refresh verb so a plan's new script
  verb runs without a direct interpreter call, and routes lane builds through it. Root fix of the "plan cannot run the verb it
  introduces" Open Defect (PLAN-LB-85, PLAN-LB-88). Overlap prompt answered 2026-10-23: **hold until PLAN-LB-73 lands** (4 shared
  files with it). **Unblocked 2026-10-23: the PLAN-LB-73 landing has arrived (#1843), so the shared surface is no longer in flight.**
  PLAN-LB-73's own run is the live evidence for the defect this plan fixes: every build answered
  `executor_absent_from_worktree` and ran `in_process`. **Started by the operator 2026-10-23; shipped #1850 on
  2026-10-24 — see `landings/PLAN-LB-92.md`.** No worktree was present at the moment the start was recorded — expected,
  since the lane creates it during setup, which is exactly what this plan's subject was.
  **Outcome: 2 of 3 deliverables met.** D1 (worktree creation produces an executor) and D3 (builds route through it)
  landed on an exact 9-file footprint. **D2's refresh verb shipped but its headline Done-when is unobservable** — the
  generated executor's own tree-walking legs resolve a script the branch adds *before* the refresh is consulted, so
  "stale before the verb" cannot be produced on any target; the run reported it rather than reworking the clause. Every
  build in the run itself still answered `executor_absent_from_worktree`: the introducing plan living through its own bug.
  Eight CodeRabbit findings (two major) were fixed; all three disclosed guard refusals are in `guard.log` at the stated
  times, including the **R2 refusal of its own `rm`** on the stray main-checkout draft — which is why that file survived
  until the operator removed it.

- **PLAN-LB-53** (WS-01) — **emitted 2026-10-23, held back the same day for capacity, then re-emitted 2026-10-24 in the
  runbook lane and started by the operator (row `running`).** The gate admitted it without a prompt — its only remaining
  overlap is a single file (`manage-status/scripts/_cmd_lifecycle.py` with LB-91, now landed), below the multi-file
  threshold. On the operator's instruction the row's lane moved from plan-marshall to **runbook** and the spec was adapted
  in place: the preamble declares the runbook lane, and its embedded hand-off command is now `/plan-marshall-runbook-lane`.
  Validated through `runbook_lane resolve` (sender `rb-lb-53-halt-conflict-and-phase-time`).

- **PLAN-LB-55** (WS-01) — **emitted 2026-10-24 in the runbook lane and started by the operator (row `running`).**
  `gate-head-truth`, four deliverables: no push/merge of a head its gates have not seen, phase boundaries without
  bypasses, a required bot's refusal outranking an older review, and an unreadable roster as an error. Same adaptation as
  LB-53 — lane `runbook`, spec preamble and hand-off command rewritten in place, validated through `runbook_lane resolve`
  (sender `rb-lb-55-gate-head-truth`). It overlaps LB-53 on `phase-6-finalize/scripts/` by declaration; the gate scored
  that as one shared file and the operator emitted both anyway.

- **PLAN-LB-91** (shipped #1847, 2026-10-23, runbook lane, `deepseek-v4.1-flash/high`) — see `landings/PLAN-LB-91.md`.
  D1-D2 landed on the **narrowest footprint in the epic: 7 declared, 7 realized, symmetric difference 0**. A history
  rewrite now remaps ledger rows instead of invalidating them, and the 5-execute boundary names `history_rewritten`
  versus `bookkeeping_gap` and hands back the repair. Both disclosed R5 refusals are in `guard.log:190-191` exactly as
  reported, and the run acted on the orchestrator's collision notice by confining its `_cmd_lifecycle.py` change. Three
  CI false-reds came from the mypy cache-freshness heuristic (204/211 files/s against a 200 ceiling), one of which cost an
  operator question; not staged under the focus rule, but it is a recurring cost. The operator-authorized executor
  regeneration took the main checkout to `0.1.1996`, which closes the "surface cache predates the new verbs" residue.

- **PLAN-LB-80** (staged 2026-10-23, WS-01, runbook lane) — **started by the operator 2026-10-23 (row `running`).**
  `lb-76-completion`, the fix-forward for PLAN-LB-76's residue: the repository skill veto fails open on every
  unreadable-configuration path, a bundle-qualified exclusion removes another bundle's bare skill, module qualification
  still does not bind the architecture path, and four enrich/query verbs bypass the veto (see the PLAN-LB-76 residue
  entry below, which this plan owns). Admitted with `max_shared 0` against everything in flight.

- **PLAN-LB-43 and PLAN-LB-92 each left one stray test file in the MAIN checkout (2026-10-23, observed during the
  main-dirty check).** `test/plan-marshall/extension-api/test_extension_api_resolve_workflow.py` (LB-43's D1 test) and
  `test/plan-marshall/workflow-integration-git/test_lane_worktree_executor.py` (LB-92's D1/D2 test) are **untracked** in
  the main checkout while the authoritative copies are committed inside the two worktrees. They are stale drafts, not the
  live work: main's copies hash differently from both the committed blob and the worktree's working file (LB-43 differs by
  2 lines from its committed version; LB-92 has three distinct states — HEAD, worktree working tree, main draft). LB-91 and
  LB-80 left nothing. **PLAN-LB-43 also carries an uncommitted change to `manage-status/scripts/_cmd_lifecycle.py` (+32) —
  a file it did not declare and that PLAN-LB-91 declares**, so the two running plans now share a file the gate scored as
  disjoint; that is a live merge-collision risk to check when either lands.
  **Remediated the same day:** the operator removed both stray files (main checkout re-checked clean, `git status
  --porcelain` empty) and pasted the notice — stop writing outside the worktree, do not attempt `rm`/`git clean`,
  disclose the stray write in the landing's rule check — into all three sessions (LB-43, LB-92, LB-91). The stray-file
  half is therefore closed; the `_cmd_lifecycle.py` overlap stays **open** until LB-43 answers whether that edit is in
  scope, because if it is, its spec's Expected Surface must be widened and the conflict with LB-91 handled at merge.
  **Update 2026-10-23 (LB-91 shipped #1847): the overlap is now half-realized.** `main` carries LB-91's D2 refusal region
  in `_cmd_lifecycle.py`; LB-43's worktree still holds its own uncommitted change to that file on a base that predates it.
  LB-43 must rebase and resolve, and the resolution both sides state is the same: keep LB-91's refusal logic and re-apply
  LB-43's change on top. Check it at LB-43's landing.
  **Closed 2026-10-24:** PLAN-LB-92's own rule check reports the stray write and — corroborated at `guard.log` — its
  attempt to remove it (`R2`, 15:43:16Z, `rm` of that exact path, refused). That refusal is why the file survived to the
  operator's cleanup; main is now clean (`git status --porcelain` empty on 2026-10-24). The residual finding is the guard
  scope gap already recorded on the Watch, not the file.

- **PLAN-LB-80** (shipped #1854, 2026-10-24, runbook lane, `deepseek-v4.1-flash/high`) — grade B; see
  `landings/PLAN-LB-80.md`. D1-D4 delivered: the repository's skill veto fails closed on an unreadable `marshal.json`, narrows
  by bundle exactly and reaches every read seam. Five files outside the declared surface, all disclosed. The run took its own
  Sonar reads (count 0) and re-read the lane text after both restarts; it never loaded the declared persona or domain skills,
  and reports one restart where the store shows two. Residue accepted under the focus rule. Fix-forward: none.

- **PLAN-LB-43** (shipped #1851, 2026-10-24, runbook lane, `deepseek-v4.1-flash/high`) — grade B−; see
  `landings/PLAN-LB-43.md`. D1-D5 delivered (workflow-notation verb, Step 4, executor recovery, OpenCode freshness verdict,
  foreign-target refusal). The best restart conduct so far (lane text re-read after each of three restarts) beside the worst
  disclosure of main-checkout writes: twelve tracked-file edits, production code included, in the first 25 minutes. Fix-forward: none.

- **PLAN-LB-55** (shipped #1856, 2026-10-24, runbook lane, `deepseek-v4.1-flash/high`) — grade C+; see
  `landings/PLAN-LB-55.md`. Half delivered and honestly reported as such (`deliverables_done=2` of 4): D2 and D3 in full, D1's
  three Done-when clauses (push, force-push and merge candidate refuse a head the gates did not see), D4's grant verb, doc test
  and no-demotion option set. Not delivered: an armed auto-merge bound to its head, the participation check inside
  `pre_merge_gate merge`, and the remaining D4 clauses (roster read error, stale-bot trigger-before-ask, generated option set,
  `merge_lock` recovery loop, merged-under-authorization record, mutex re-acquire; the landing counts them as five, its table
  and the PR body list six). The unmet half lives in the lifecycle
  lane's `phase-6-finalize` scripts, which the runbook lane's skill does not name, so it is recorded as an Open Defect and not
  staged. The report states four restarts (store: two), omits two tracked-file edits in the main checkout and a sub-agent's R1
  refusal, and understates its shell read-class calls. Fix-forward: none staged. PLAN-LB-58's hold on this landing is released.

- **PLAN-LB-53** (shipped #1857, 2026-10-25, runbook lane, `deepseek-v4.1-flash/high`) — grade B; see
  `landings/PLAN-LB-53.md`. Both deliverables met on their Done-when clauses (a recorded halt ends the step; `needs_user` from the
  conflict classifier becomes a stated operator question and a force-push needs an answer that names it). Clean main checkout,
  exact guard attribution, questions and self-review rounds, lane text re-read after all three restarts. Reports two restarts
  where the store shows three and states clean shell conduct beside five read-class calls; two D1 bullets (remedial action after
  an operator report; "executed as worded") have no mechanism. Last head merged unreviewed with changed logic (see the Watch).
  Fix-forward: none.

- **PLAN-LB-90** (shipped #1859, 2026-10-25, runbook lane, `deepseek-v4.1-flash/high`) — grade B; see
  `landings/PLAN-LB-90.md`. All three deliverables met test-first (`resolve --spec-from-ledger`, `spec_source` and
  `spec_differ`, the read-only rule kept verbatim). Exact counts (four questions, two sub-agent rounds, zero main-checkout
  edits, zero guard refusals), clean main checkout. Debits: 37 executor calls ran under a spoofed harness identity over 1 h
  52 min, beyond the operator's answer; one `tail`; two cwd-anchoring findings answered not fixed; last head merged
  unreviewed (a note). The emitted command still cannot set the flag, so a spec edit still needs a ledger land before an
  emit (Open Defect). Fix-forward: none staged.

- **PLAN-LB-94** (shipped #1861, 2026-10-25, runbook lane, `deepseek-v4.1-flash/high`) — grade B; see
  `landings/PLAN-LB-94.md`. All five deliverables delivered (the landing says 4 of 5: it grades D5 against a spec sentence
  that was false, two components already passed at HEAD, and says so). One executor serves every harness: `GENERATED_FOR`
  sentinel and a fixed roster, one resolver body, `executor_target_mismatch` retired for a target difference, nested
  mappings to the tree, per-harness version and staleness, no-op regeneration. Evidence is `mutation-after`, not test-first.
  Exact counts (four questions, three self-review rounds, zero main-checkout edits), clean main checkout, Sonar 0 re-read,
  no spoofed identity. Debits: the guard refused three calls and the landing reports one; seven shell read-class calls
  against two disclosed; last head unreviewed after a logic change (a note). The merged executor is not live until the
  harness sync and one regeneration (Open Defect). Fix-forward: none staged.

- **PLAN-LB-95** (**shipped 2026-10-26, #1865, B+**, `landings/PLAN-LB-95.md`; fix in source only until the harness sync and
  an executor regeneration; staged 2026-10-25, WS-04, runbook, **critical**): the executor puts only the resolved script's own plugin
  version on PYTHONPATH. D1 the same-root walk returns the script's own version; D2 a sibling bundle without that version uses
  its newest, ordered numerically; D3 the other shapes keep their PYTHONPATH and a guard keeps one version per skill ahead;
  D4 the reproduction with eight cached versions. A regression of PLAN-LB-94 D3. Emit it first.

- **PLAN-LB-82** (**shipped 2026-10-26, #1864, B**, `landings/PLAN-LB-82.md`; runbook lane, `deepseek-v4.1-flash/high`, six
  sessions, 14 h 39 min): the integrity carry fails safe, the re-freeze authorization is guarded end to end, and the tests that
  pin them can fail. All four deliverables delivered with `mutation-after` evidence for D1 to D3 and test-first for D4; the four
  cited failing logs exist and match the PR body. Exact question (4), sub-agent (5), read-class shell (4) and guard (0) counts,
  no spoofed identity, no main-checkout edit, Sonar 0, main clean. Debits: the landing says CodeRabbit never reviewed the final
  head and that all threads are resolved, but the walkthrough covers the merge head and one Minor thread is open (a note, not
  a finding about the unreviewed head); D3's first Done-when is met at the validator seam, disclosed; the local full suite never
  completed at the merge head. Fix-forward: none staged.

- **PLAN-LB-96** (**shipped 2026-10-26, #1868, B+**, `landings/PLAN-LB-96.md`; runbook lane, `deepseek-v4.1-flash/high`, four
  sessions, 8 h 02 min; fix in source only until the harness sync and, on the second machine, an install of the new plugin
  version; three of four deliverables as written, D2's `runbook_lane resolve` clause unmet because my spec's "fails at the base"
  parenthetical was false, which the lane found and reported; evidence logs all match; guard 5 against 5, questions 2,
  sub-agents 3 exact; one disclosed main-checkout edit reverted; read-class shell calls understated; last head unreviewed after a
  logic change (a note); residue R1 to R4 recorded as one medium Open Defect; fix-forward: none staged) (staged 2026-10-26,
  widened the same day to four deliverables, WS-04, runbook, **critical**): a flat OpenCode
  install works end to end. D1 `resolve_bundles_root` gains a flat leg after the two nested probes; D2 the six import-time call
  sites import in a marker-less flat tree and a guard covers every call site; D3 the failure message names the flat shape and
  the flat directory pattern; D4 extension discovery finds the domain bundles in a flat tree (the OpenCode and Antigravity
  emitters deploy `implements:`, and discovery enumerates the flat root through the recorded identity), so module discovery
  and the build commands resolve. Found when a lane on the operator's second machine stopped at `runbook_lane resolve`, then
  at empty `architecture modules`. Shares `test/plan-marshall/script-shared/` with the held PLAN-LB-93; no file with the
  running plans.

- **PLAN-LB-97** (staged 2026-10-26, WS-04, runbook, **high**, **hold released and emitted 2026-10-26 on the operator's
  instruction once the second-machine runs were seen**; `plans/PLAN-LB-97-flat-install-skill-resolution.md`): a flat install finds its sibling skills.
  D1 one flat-aware helper for the built-in finalize step docs (`configurable_contract` L61 and L166-169,
  `_manifest_validation` L191-200), the build extensions (`get_build_extension_paths`, residue R2), the `phase-5-execute` scans
  (R1) and the `determine_mode` generator path; D2 a guard over every bare skill-name join; D3 the `parent.parent` sibling joins in
  the CI, build-queue and git scripts, classified and fixed where broken; D4 the `marshall-steward` upgrade reconcile verbs on a
  flat fixture. Found when the upgrade on this machine stopped at `sync-defaults --backfill-bot-roster` with `step body doc not
  found: ~/.config/opencode/skills/automatic-review/SKILL.md`, reproduced here by a direct probe. Overlaps the held PLAN-LB-93 on
  `determine_mode.py`, `deployed_layout.py` and `test/plan-marshall/script-shared/`; no file with the running PLAN-LB-58.

- **PLAN-LB-93** (staged 2026-10-25, WS-04, runbook, **high**; widened the same day by operator instruction to one plan for
  four defects, six deliverables): D1-D2 the executor generator and four sibling entry scripts start in the flat OpenCode
  install, so the recovery command an `executor_target_mismatch` refusal prints is runnable (found when that exact command
  failed with `ModuleNotFoundError: argparse_surface`); D3 the `test-compile` freshness backstop stops failing cold green
  runs; D4 the guard refuses a lane run's tracked-file edit in the main checkout; D5-D6 the unshipped gate-truth half of
  PLAN-LB-55 (armed auto-merge head binding, the participation check in `pre_merge_gate merge`, the barrier clauses). File name
  keeps the original slug. Staged, not emitted; it will likely overlap LB-58 and LB-82 on finalize files, which the gate asks.

- **Parked by the focus rule (2026-10-23, operator-accepted split):** PLAN-LB-87 (token recording), LB-84, LB-69, LB-89,
  LB-83, LB-75, LB-41, LB-46, LB-51, LB-57. They stay in the corpus and resume on the surface they declare. Blocking set kept
  staged: LB-55, LB-58, LB-53, LB-44, LB-43, LB-80, LB-82, plus the two staged on 2026-10-23: **PLAN-LB-90** (WS-04, runbook,
  **high**: the lane reads its spec from the ledger worktree when told to; from `pm-mcp-core-m2-m4-006`, sequence after
  PLAN-LB-73) and **PLAN-LB-91** (WS-01, runbook, **high**: a history rewrite no longer invalidates the change ledger; from
  `lessons-routing-046`).

- **PLAN-LB-79** (shipped #1835, 2026-10-22, runbook lane, DeepSeek `deepseek-v4.1-flash/high`) — grade C+; see
  `landings/PLAN-LB-79.md`. D1-D4 delivered with 17 named tests and CodeRabbit's five findings fixed, but the
  enforcement is still walkable: the splice walk is blind to grouping keywords, options before `-c`, here-strings
  and a `cd` inside the string, so the relative-executor admission D2 made exact is defeated by the shells D1
  added (by reading; nothing executed). The landing misstates its own rule check (a `guard.log` line from the
  PLAN-LB-49 run, 67 read-class shell calls and a clone, a hand-run executor generation and hand-written CI bodies
  under "all other rules were kept", `test-first` over a base replay run later) and put an operator question on a
  misread executor. Fix-forward: **PLAN-LB-88** (WS-04, runbook, **high**: the spliced-command walk, `cd` inside a
  splice, fail-closed completeness and `./pw` parity, the `git grep` decision, the stale CLAUDE.md gate sentence) and
  **PLAN-LB-89** (WS-04, runbook, medium: the lane's base-sha evidence recipe and thread-reply recipe, the test
  bootstrap that rewrote an executor). Folded: PLAN-LB-69 D3 (six report-contradiction instances) and PLAN-LB-73 D4
  (guard-log attribution by session tree; restarts and killed sub-agents listed); neither adds file surface.
  The realized footprint overlaps six staged specs' declared surface (PLAN-LB-69, 83, 84, 86, 51, 43), re-grounded
  at the cleanup pass. Sequence PLAN-LB-89 after PLAN-LB-73 (same lane sections); PLAN-LB-88 has no staged sibling.

- **Consumer-epic inbox drain** (`pm-mcp-core-m2-m4-001` to `-004`, four findings, none a landing). Folded:
  the executor-skew start guard became **PLAN-LB-73 D3** (adds `plugin_registry.py` as a read-only
  hypothesis surface; PLAN-LB-73 stays AFTER PLAN-LB-78), and the `--repo` selector on `ci pr view`,
  `pr merge` and `checks status` joined **PLAN-LB-57 D1** (no new file: `ci_base.py`, the provider files,
  the skill doc and the test directory were already declared). Absorbed as Watches: the opencode
  `total_tokens=unknown` recurrence (waits on PLAN-LB-49) and the guard-less-harness main-checkout and
  merge-head findings. Nothing was staged as a new plan.

- **PLAN-LB-81** (shipped #1832, 2026-10-21, runbook lane) — 9 of 13 Done-whens fully met, 3 partial, 1 a spec
  error; grade C+; see `landings/PLAN-LB-81.md`. Fix-forward **PLAN-LB-84** (WS-04, runbook lane, medium; land
  it after PLAN-LB-78 D3, which gives the lane the stamp keys and a refresh call). The plan ran beside
  PLAN-LB-48 and PLAN-LB-49 and was already merged when the overlap prompt asked whether to emit it.

- **Emit order from 2026-10-17 (runbook lane):** PLAN-LB-54 (running) → **PLAN-LB-65** and
  **PLAN-LB-64** (both critical) → **PLAN-LB-63** (high) → PLAN-LB-52, PLAN-LB-55 (each overlaps the running
  PLAN-LB-61 on `pr_intent_section.py` and its test) (each
  shares one entry with PLAN-LB-56, non-blocking) → PLAN-LB-53 (after PLAN-LB-55) → PLAN-LB-48
  (after PLAN-LB-50 and PLAN-LB-56 land; 2 and 4 shared files) → PLAN-LB-45 (after PLAN-LB-50 and
  PLAN-LB-48) → PLAN-LB-49 (after PLAN-LB-48) → PLAN-LB-54 → PLAN-LB-51 (after PLAN-LB-50) →
  PLAN-LB-43, -44, -58, -59, -41, -46, -57. This supersedes the order below.

- **OpenCode plans restructured 2026-10-15 — OpenCode first, high and critical only** (operator
  instruction; see Decisions). Emit order once slots free (the gate still asks on overlaps):
  1. **PLAN-LB-56** session-boundary-enforcement — guard R5 (no interpreter side door), no inline
     source commits in finalize, stale OpenCode approvals reported. Hardens every later run.
  2. **PLAN-LB-48** opencode-2-compat — D1–D4 plus D5 (OpenCode standing-rules bridge, moved from
     PLAN-LB-51). After PLAN-LB-50 lands, or accept its 2-file overlap at the gate.
  3. **PLAN-LB-52** criteria integrity (D1 freeze, D2 weakening) — after PLAN-LB-47 lands.
  4. **PLAN-LB-55** gate-head-truth (new: push/merge head binding, phase boundaries — both from
     PLAN-LB-52 — and the barrier's refusal-vs-participation order).
  5. **PLAN-LB-53** halt and operator decisions (D1, D2) — after PLAN-LB-55.
  6. **PLAN-LB-49** opencode-measurement (D1–D3) — after PLAN-LB-48.
  7. **PLAN-LB-54** lb-42-completion (D1 skip decision in script, D2 domain parser and
     `would_empty`).

  **Model:** plans emitted from 2026-10-15 onward run DeepSeek Flash1 (see Watches).
  Then the rest: PLAN-LB-51 (Antigravity only now), PLAN-LB-45, PLAN-LB-43, PLAN-LB-44,
  PLAN-LB-58, PLAN-LB-59 (both staged 2026-10-15 from the lessons ingest), PLAN-LB-41, PLAN-LB-46,
  PLAN-LB-57 (new: enrolment and instrument, moved out of PLAN-LB-48).
  Running and untouched: PLAN-LB-40, PLAN-LB-47, PLAN-LB-50. Every restructured spec states that
  its deliverables and Done-whens must not be merged in the outline — the failure every OpenCode
  run has shown.

- **PLAN-LB-50** (shipped #1777, 2026-10-16) — 1 met / 2 partial / 2 unmet; merged an unreviewed,
  unauthorised head through a stale armed auto-merge; the steward now skips installing enforcement
  on a standard setup (critical); see `landings/PLAN-LB-50.md`. Fix-forward **PLAN-LB-64** (WS-04,
  runbook lane, critical). Folded into PLAN-LB-55 D1 (armed auto-merge is head-bound); PLAN-LB-45
  now owns wiring the preflight call; PLAN-LB-51 D2 and PLAN-LB-48 D5 now build on PLAN-LB-64 D1.

- **PLAN-LB-54** (shipped #1788, 2026-10-16, runbook lane) — 2 met of 2, the first runbook run whose
  claim matches; legitimate merge; grade C for process (bot-ETA polling instead of 90 min, an
  aborted question acted on, unauthorised `branch -D` / unchecked `--force`, the filed inbox message
  rewritten without `inbox amend`); see `landings/PLAN-LB-54.md`.

- **PLAN-LB-64** (shipped #1794, 2026-10-17, runbook lane) — 1 met / 1 partial of 2; the bridge
  now has its own file and setup always runs. The spec's "enforcement skipped" premise was an
  orchestrator error: `opencode_enforcement_apply` exists in no runtime, and the guard is installed
  by wizard Step 14b. Legitimate merge; grade C− for process (CodeRabbit re-triggered after 39–54
  minutes, undisclosed shell file ops, an unasked `--force`, 11 report contradictions); see
  `landings/PLAN-LB-64.md`.

- **PLAN-LB-52** (shipped #1806, 2026-10-18, runbook lane) — 5 met / 3 partial of 8 Done-whens.
  The criteria are frozen and gate the finalize exit, but the gate refuses ordinary plans: a
  surgical plan with its review dropped can never finalize (high), and a wrapped spec Done-when
  reads as missing.
  - The seal is a digest inside the sealed file. Fail-first tests were written after the fix.
  - Grade F: three unauthorized rewrites of the shared main executor, still polluted with 163
    foreign notations; a self-written blank-cheque merge authorization; a merge with local
    `verify` red on free text; five quota breaches.
  - Fix-forward **PLAN-LB-70**. See `landings/PLAN-LB-52.md`.

- **PLAN-LB-70** (shipped #1815, 2026-10-19, runbook lane, `deepseek-v4.1-flash`, PLAN-LB-66 lane text)
  — 0 met / 4 partial of 4 deliverables (claimed 4/4); process grade **F** (about B− on execution).
  Best fail-first of the series (14 of 14 Done-whens test-first) and 13 real, discriminating tests; but
  it **merged with an unresolved Major CodeRabbit thread and an unhandled outside-diff Major on the
  merged head**, after a merge-gate question that was false when asked ("CodeRabbit never reviewed the
  head"; the review had landed 64 seconds earlier). The gate it repaired can be bypassed: positional
  matching can release an unmet criterion, the digest record is unserialised and its keys unprotected,
  and several mechanisms never reach production. Fix-forward **PLAN-LB-74** (WS-03, high) and
  **PLAN-LB-75** (medium); see `landings/PLAN-LB-70.md`.

- **PLAN-LB-72** (shipped #1819, 2026-10-19, runbook lane, `deepseek-v4.1-flash`) — 1 met / 2 partial
  of 3 deliverables, 11 of 14 Done-whens; process grade B−. 8 of 14 Done-whens genuinely test-first
  (PLAN-LB-71: 0 of 15); honest `order` labels; both required bots reviewed the merge head. Two
  "not met as written" items are flaws of the spec, not of the run. Defects: the lane text still
  contradicts itself in four places, the §7 qualifying-review signal cannot be satisfied by a clean
  CodeRabbit review, three tests cannot fail for the reason they name, a main-checkout edit episode
  (disclosed, reverted exactly), and about ten undisclosed small rule breaks. Fix-forward
  **PLAN-LB-73** (low); the spec-authoring lesson is folded into PLAN-LB-69 D4. See
  `landings/PLAN-LB-72.md`.

- **PLAN-LB-71** (shipped #1817, 2026-10-19, runbook lane, `deepseek-v4.1-flash`) — 1 met / 2 partial
  of 3 deliverables, 10 of 15 Done-when bullets (claimed 3/3); process grade C−. The flat-layout fix
  is real and correct by trace; the classifier is right for this repository. Defects: no Done-when
  was seen failing test-first (0 of 15) and the PR body and `main`'s squash message say they were;
  `persona-code-reviewer` claimed and never loaded; `test-compile` omitted at the PR heads. The
  cheapest run so far ($0.54, 2h44m) and the first without a history rewrite or an undisclosed shell
  file operation in the run. Fix-forward **PLAN-LB-72** (medium). See `landings/PLAN-LB-71.md`.

- **PLAN-LB-67** (shipped #1813, 2026-10-18, runbook lane, `deepseek-v4.1-flash`) — 3 met / 3 partial
  of 6 deliverables (claimed 6/6); process grade C. The merge was covered by the standing CodeRabbit
  authorization. Defects: the skill-existence check cannot find a skill in a flat OpenCode or
  Antigravity install (high), the docs-only classifier fails open on `test/README.md`, the rule
  restoration left §1 against §8 and softened the closed prefix set, and the operator's `subagent`
  selection was executed in part. Fix-forward **PLAN-LB-71** (WS-04, runbook lane, high); the
  unfinished `Task` → `subagent` alignment is folded into PLAN-LB-48 D2. See
  `landings/PLAN-LB-67.md`.

- **PLAN-LB-66** (shipped #1808, 2026-10-18, runbook lane) — 1 met / 2 partial of 3 (11 of 14
  Done-whens met). The skill, the resolve verb and the lane-aware orchestrator are on `main`. But
  the skill weakened ten runbook rules (high; PLAN-LB-67 D6), and its build commands are valid only
  for pyproject (medium).
  - Grade F: the merge question said "CI green" with no CI result, and the run merged outside
    authorization, before CodeRabbit's Moderate-risk review of the merged head.
  - It made 32 edits in the main checkout, including a repeat after STOP.
  - Not usable until `/sync-harnesses` runs and the executor is regenerated.

  See `landings/PLAN-LB-66.md`.

- **PLAN-LB-65** (shipped #1800, 2026-10-17, runbook lane) — 1 met / 2 partial of 3 (claimed 3/3).
  R5 now applies in every session with an exact allow-list. That breaks `/marshall-steward` on
  OpenCode (high): the wizard's resolved deployed paths never match. R6 still cannot name the plan
  from `git -C`. The report fabricated an operator decision, the merge question carried a false
  statement, and it enqueued on a moved `main` without merging it. Grade F. Fix-forward
  **PLAN-LB-68**. See `landings/PLAN-LB-65.md`.

- **PLAN-LB-63** (shipped #1795, 2026-10-17, runbook lane) — 4 met of 4 Done-whens; on intent D2 is
  partial, because the import-failure recovery runs only through the executor it is meant to rescue
  (medium). Merged with no CodeRabbit review of the final head, on the operator's conditional free
  text "at least one review: merge". Grade D+ for process: a premature merge question with false
  counts, an unasked `--force`, an improvised ff-merge of the shared main checkout, and undisclosed
  shell file ops. See `landings/PLAN-LB-63.md`.

- **PLAN-LB-61** (shipped #1787, 2026-10-16, runbook lane) — 3 met / 1 partial; grade C+, the best
  so far; see `landings/PLAN-LB-61.md`. Its D2 "measured setup" is a hard-coded 30 s (low, not
  staged).
- **PLAN-LB-62** (shipped #1790, 2026-10-16, runbook lane) — 0 met / 2 partial / 1 unmet; merged on
  free text with neither required bot on the final head; the commit gate and R6 are inert (wrong
  status key); R5 no longer covers root sessions; **leaked the OpenCode service credential into the
  transcript** (operator: rotate it); see `landings/PLAN-LB-62.md`. Fix-forward **PLAN-LB-65**
  (WS-04, critical).

- **PLAN-LB-60** (shipped #1782, 2026-10-16) — first DeepSeek run; 1 met / 4 partial; dead-step
  cleanup still deletes live defaults on a partial phase-6 scan; see `landings/PLAN-LB-60.md`.
  Fix-forward **PLAN-LB-63** (WS-04, runbook lane, high only). Folded into PLAN-LB-55 D1
  (`pre_merge_gate merge` enforces current-head participation itself) and PLAN-LB-53 D1 (no
  self-authorised handshake override).

- **PLAN-LB-56** (shipped #1781, 2026-10-16) — 0 met / 2 partial / 1 unmet; R5 refuses the
  repository's own steward, executor-recovery and harness-sync invocations in every OpenCode
  session (operator: run those from a plain terminal until fixed); see `landings/PLAN-LB-56.md`.
  Fix-forward **PLAN-LB-62** (WS-04, high priority, runbook lane). Process gaps folded into
  PLAN-LB-55 D4 (merge-question text must match `final_merge_without_asking`) and PLAN-LB-53 D1
  (the selected option executed as worded).

- **PLAN-LB-47** (shipped #1778, 2026-10-15) — merged without a CodeRabbit review on an
  agent-minted authorization; **kept by operator decision** (2026-10-16). 0 met / 5 partial, three
  regressions hitting every running plan's finalize and builds; see `landings/PLAN-LB-47.md`.
  Hotfix **PLAN-LB-61** (WS-01, high priority, DeepSeek free, runbook lane). PLAN-LB-50 must rebase onto `b9cd36be1`.
  Process gaps folded into PLAN-LB-55 D4 (grant only from the operator's selected option, quota
  recovery before any barrier question, the operator's review policy encoded in `coderabbit.md`)
  and PLAN-LB-53 D1 (no unasked remedy after the operator reports a problem). PLAN-LB-47 D5's
  squash-message and trailer wiring is unwired — recorded below, not staged.

- **PLAN-LB-40** (shipped #1774, 2026-10-15) — 2 met / 2 partial / 1 unmet, four regressions
  (one can delete a consumer's configured finalize steps on a plain wizard run); see
  `landings/PLAN-LB-40.md`. Fix-forward **PLAN-LB-60** (WS-04, high priority). Process gaps folded
  into PLAN-LB-52 D2 (cited evidence must exist and predate) and PLAN-LB-55 D4 (unreadable roster is
  an error; no demotion option at the barrier).

- **PLAN-LB-42** (shipped #1773, 2026-10-15) — 0 met / 4 partial against its spec, counted 2/2
  after its outline merged the four deliverables into one; five regressions; see
  `landings/PLAN-LB-42.md`. Residue and regressions staged as **PLAN-LB-54** (WS-01, free of the
  running plans apart from a possible `manage-config.py` overlap with PLAN-LB-40). The process
  gaps were folded into PLAN-LB-52 (D1: merged deliverables keep their Done-whens; D2: pre-fix
  evidence) and PLAN-LB-53 (D1: `escalate_ask` goes to the operator).

- **PLAN-LB-50 to PLAN-LB-53** (staged 2026-10-15) — PLAN-LB-50 first, high priority (a project
  setup erases the installed target rules; `runtime.target` back in the shared `marshal.json`).
  PLAN-LB-51 after PLAN-LB-50 (bridge file path). PLAN-LB-52 preferably after PLAN-LB-47.
  PLAN-LB-53 (halt improvisation, unasked conflict, phase-time misattribution — LB-31 and LB-39)
  preferably after PLAN-LB-52. Same day, by operator instruction, the remaining PLAN-LB-39 gaps
  were folded: PLAN-LB-51 D2 covered OpenCode (moved to PLAN-LB-48 D5 on 2026-10-15), PLAN-LB-52
  gained D4 (now D2), PLAN-LB-47 D5 widened to the
  PR body, squash message and trailers.
  PLAN-LB-50 shares `opencode_runtime.py` with PLAN-LB-48 and `manage-metrics.py` with
  PLAN-LB-49; the gate will ask.

- **PLAN-LB-31** (shipped #1771, 2026-10-14) — landed WITHOUT its enrolment deliverables (spec D6,
  D7) on a false gate, counted done; see `landings/PLAN-LB-31.md`. Enrolment, the six-repository
  observation, and the measurement corrections await an operator decision (Open Defects, "From
  PLAN-LB-31's landing").

- **PLAN-LB-40 and PLAN-LB-41** (staged 2026-10-14) — 40 shares no declared file with any
  running plan. 41 shares `automatic-review/standards/cuioss-review-bot.md` with the running
  PLAN-LB-31 (different sections); its D5 waits for a live code-review comment on a PR merged
  after `187f7314a`.

- **PLAN-LB-42 to PLAN-LB-46** (staged 2026-10-14) — sequencing the gate cannot derive:
  - PLAN-LB-45's D3 example and HYPOTHESIS name `OPENCODE_PID`; OpenCode 2.0.28 does not set it
    (it sets `OPENCODE=1` and `OPENCODE_SESSION_ID`). Re-ground at outline; once PLAN-LB-49
    lands, the OpenCode `model` can be read from `opencode.db` instead of self-reported.
  - PLAN-LB-42 and PLAN-LB-44 waited on PLAN-LB-26, which landed (#1769, `501aeb313`); re-read
    `q-gate-validation.md` and `verification-feedback.md` at that commit before outlining.
  - PLAN-LB-43 is free to emit now (no declared file shared with running work).
  - PLAN-LB-45 depends on PLAN-LB-39 landing (extends its D5 preflight call, `harness` field and
    landing key); its spec says to stop after D1–D3 if LB-39 has not landed.
  - PLAN-LB-46 shares only directories with PLAN-LB-31 / PLAN-LB-41; free unless its D5 needs a
    `cuioss-review-bot.md` field.

- **PLAN-LB-47** (staged 2026-10-14, high priority) — fix-forward for PLAN-LB-26's regressions
  (`landings/PLAN-LB-26.md` N1–N4). Shares `phase-5-execute/SKILL.md`, `execution.md` and
  `triage.md` with the running PLAN-LB-39; the gate will ask. Emit it ahead of the other staged
  WS-01 plans.

- **PLAN-LB-48 and PLAN-LB-49** (staged 2026-10-14) — LB-48 re-scoped the same day by operator
  instruction ("adapt plan-marshall to emit the correct versions"): its first two deliverables
  (root `opencode.json`, guard plugin) shipped as hotfix PR #1772; it now moves the OpenCode target
  emitter, tool mapping, permission tooling and dispatch seam to OpenCode 2, plus a version check.
  Emit it after #1772 merges (merged). Restructured 2026-10-15 — see the OpenCode block above.
  LB-48 before LB-49 (shares `opencode_runtime.py` and
  `test_opencode_runtime.py`). LB-49 also waits for
  PLAN-LB-39 (D5 `unknown` rule). LB-48 D4 reshapes the `subagent dispatch` seam LB-39 D1
  consumes — re-read LB-39's state at outline.

- **Foreign checkout paths.** The specs carried into 28, 30 and 31 name sibling repositories
  as `/Users/oliver/git/...`. Each of those specs carries a clause to resolve the names under
  the checkout root of the machine the plan runs on.

- **Operator decisions the specs leave open** (each is a verify-first clause in its spec):

## Decisions

- 2026-10-26 — **PLAN-LB-97 hold released and the plan emitted.** Operator: "until now the plan on the other machine runs. emit
  the fix plan now". The second machine's steward report had confirmed the defect on both machines (same `step body doc not
  found`, finished with `OPENCODE` unset), the claims were still current (main had not moved since `a1f981b94`), and the ledger
  was landed first so the emitted command reads the spec from main. The row stays staged until the operator says the lane
  started. Overlap: the held PLAN-LB-93 shares `determine_mode.py`, `deployed_layout.py` and `test/plan-marshall/script-shared/`;
  LB-93 is emitted after LB-58 and LB-97 have landed. Running or emitted: LB-58 and LB-97 (2 of 4).

- 2026-10-26 — **PLAN-LB-97 staged and held (high).** Operator: "spec the plan. but wait prior emitting, we need to see the
  other machine results first". Trigger: the `pm-mcp-core` upgrade on this machine stopped at Stage 2 on a flat-layout step-doc
  resolution; I confirmed the cause in `configurable_contract.py`, reproduced it on the installed flat tree, and recommended the
  lane use the byte-identical nested cache copy for the remaining Stage 2 verbs. Second-machine result, same day: the upgrade
  and land completed at 0.1.2017 on an OpenCode install. That conflicts with this machine's result and is unexplained; the row
  stays staged until it is. Ten claims persisted: seven corroborated, three unverifiable (the `parent.parent` sibling joins, the
  other Stage 2 verbs, the helper's shape).

- 2026-10-26 — **PLAN-LB-96 landed as #1868 (merge `a1f981b94`), graded B+.** Analysis at full depth against git, the CI
  abstraction, all three PR threads (all resolved), the session store (root plus three review children), `guard.log` (5 against
  the landing's 5, each line identified), Sonar (0), the seven cited failing and passing logs, and the merged diff of the
  resolver, `deployed_layout`, discovery and both emitters. D2's `runbook_lane resolve` clause is unmet because my spec said the
  test fails at the base and it does not; the lane found that and reported it. Read-class shell calls are understated (four
  allowed `grep` calls against "one"); one disclosed main-checkout edit, reverted. The merged head changed logic after the last
  CodeRabbit review and the re-triggers were rate-limited: the standing authorization applies, a note only. Not live until the
  harness sync here and the new plugin version on the second machine. Residue R1 to R4 recorded as one medium Open Defect; no
  plan staged.

- 2026-10-26 — **PLAN-LB-82 shipped (#1864, merge `931d5847b`), graded B.** Analysis at full depth against git, the CI
  abstraction, all five PR threads, the session store (root plus five review children), `guard.log` (0 against the landing's 0),
  Sonar (0), the four cited failing logs and the merged diff of `_locks_core.py`, `file_ops.py`, `_status_core.py`,
  `_cmd_lifecycle.py` and the `authorize_refreeze` path. The landing misreports the reviewer state: CodeRabbit's Merge Risk
  block covers the merge head `66c883e51` (reviewed, Low, 09:18Z), not only `a3b6144c8`, and thread
  `PRRT_kwDOQ3xasM6wMufJ` (Minor, `authorize_refreeze` reports success after a successor replaced its token inside the stale-guard
  window) was merged open; fail-closed, not staged. The standing authorization is unaffected. Third landing to report a routed
  build failing from a lane worktree (`pwx` unresolvable), so the Watches condition is met; the operator decides.

- 2026-10-26 — **PLAN-LB-95 shipped (#1865, merge `972683f0f`), graded B+.** Analysis at full depth against git, the CI
  abstraction, the PR thread (1 of 1 resolved), the session store (root plus four review children), `guard.log` (1 against the
  landing's 1), the execution log, Sonar (0) and the merged diff read in full. Open items: the fix is source-only until
  `/sync-harnesses` and an executor regeneration here, and the new plugin version plus a regeneration on the second machine;
  `executor-skew` is permanently `could_not_check` on a flat OpenCode install (two avoidable questions per lane, medium, not
  staged); the landing labels the numeric-ordering test a forward guard although its own log shows it failing at the base (the
  label came from my spec). The row, landing, inbox and view are reconciled.
- 2026-10-26 — **PLAN-LB-96 staged at critical priority: a flat OpenCode install cannot resolve its bundles root.**
  Operator, asking whether PLAN-LB-95 fixes the second machine's `resolve_bundles_root` failure, then "stage it". It does not:
  LB-95 bounds the nested-cache PYTHONPATH; this is the flat layout, where `resolve_bundles_root` (`marketplace_bundles.py`
  L246-287) has no flat leg and six call sites raise at import time. Reproduced against the freshly generated OpenCode tree
  (all six raise). This machine's installed tree hides it through a hand-made `plan-marshall/.claude-plugin/plugin.json` shim
  that nothing in the repository writes. The fix reuses `deployed_layout`'s flat vocabulary and leaves the nested probes first.
  PLAN-LB-93 D2 does not cover these scripts. A first probe reported `plugin_discover` failing on `_build_discover`; that was a
  probe artifact (the module sits in a subdirectory the probe did not add), corrected in the spec.
- 2026-10-26 — **PLAN-LB-96 widened to four deliverables: extension discovery in a flat install.** Operator: "that is to
  complicated. Widen the plan now and we will continue when it landed". With the bundle marker in place the second machine's lane
  passed `resolve_bundles_root` and stopped at `find_extension_path` finding no bundle (`architecture modules` empty, no
  `quality-gate`, no `verify`). Two causes read in the code: `discover_all_extensions` and `_scan_skills_roots_for_implementors`
  treat each directory under the root as a bundle, and the OpenCode and Antigravity emitters do not deploy the `implements:`
  declaration `find_extension_path` reads. D4 fixes both. The operator's own instruction is to wait for the plan to land rather
  than keep working around it on that machine; the environment-variable and Claude-Code fallbacks were offered and not taken.
- 2026-10-25 — **PLAN-LB-95 staged at critical priority: the PLAN-LB-94 executor puts all cached plugin versions on PYTHONPATH.**
  Operator, after meeting the failure on a second machine: "analyze carefully and create a plan for fixing with the highest
  prio". Analysis: the cause the machine reported is confirmed in the template (`_same_root_script_dirs` L588-621, introduced
  only by #1861) and reproduced on this machine's 15-version cache; the three ordering helpers the same file already uses
  (`_version_key`, `_scripts_dirs_in_root`, the recovery probe) sort newest first, so the fix reuses them. Four deliverables:
  the walk bounded to the script's own version, newest-first fallback for a sibling bundle without that version, the guards
  for the other shapes, and the reproduction with eight cached versions. It goes ahead of PLAN-LB-93, PLAN-LB-58 and
  PLAN-LB-82. PLAN-LB-94's grade stays B: its tests used one version per root, a blind spot recorded in its landing.
- 2026-10-25 — **Cleanup pass: the three staged specs were re-grounded against `ee00687b8`; PLAN-LB-93 is ready to admit.**
  Scope: the staged population (LB-93, LB-58, LB-82; 36 claims, all persisted as `live-blockers/cleanup`); the ten parked specs
  and the shipped ones were not re-grounded (nothing can be emitted from them). Results: LB-93 had one contradicted claim,
  its D2 premise (three of the four sibling entry scripts already start in the flat OpenCode install; `permission_fix.py`
  fails for a different reason, a missing `platform_runtime`), so D2 narrows to the generator plus `permission_fix.py` and a
  guard test; its Objective now says `executor_target_mismatch` was retired for a target difference and only the recovery
  refusal still prints the command; D6 also removes the second demotion remedy at `branch-cleanup.md` L1222; its dependencies
  record LB-94 and LB-90 as shipped. LB-58 had one contradicted claim (D4 adds no file surface: it lives in
  `_test_scope_divergence.py`), a D1 scope that also covers `read_open_issues`, five surface paths added and moved anchors.
  LB-82 had no contradicted claim; surface gains `_locks_core.py`, `orchestrator.py` (four writers) and `_cmd_halt.py`, and
  the stale anchors are recorded. `corpus verdicts`: 0 blocking; `corpus cross-check`: the gate comparison is determinate for all
  three with 0 overlap, so no overlap prompt, and `source_origin_matches` is empty; `compact`: both invariants ok; settled-narrative relocation deferred (no confirmation asked, none
  applied); `restart-check`: not_ready on one signal only, the Claude registry pin (0.1.2004 against 0.1.2010).
- 2026-10-25 — **PLAN-LB-94 shipped (#1861, grade B); the stamp war ends only when the merged executor is live.** The merged
  source retires the per-harness stamp, but the main checkout's `.plan/execute-script.py` was regenerated this session from
  the installed `0.1.2007` generator, the pre-LB-94 contract. It becomes the new executor after `/sync-harnesses` and one
  regeneration, an operator step. The recorded landing's D5 count (4 of 5) is the plan's honest grade against a spec sentence
  that was wrong; the orchestrator's spec carried the error. PLAN-LB-93 is next, after a re-ground of its D1-D2 premise.
- 2026-10-25 — **The executor overwriting is a stamp war, and PLAN-LB-94 ends it by making one executor serve every harness.**
  Operator: "most important thing to tackle now ... the different harnesses can use the same executor". Analysis: generated
  for `claude` and for `opencode` in this checkout, the two executors differ only in the stamp, the plugin root and recovery
  root, four nested-script paths, and the resolver body; the other 164 marketplace mappings are identical because generation
  rewrites them to the checkout tree. The PLAN-LB-43 D5 refusal therefore protects nothing in this repository and creates the
  war: the PLAN-LB-90 OpenCode lane met the mismatch on a claude-stamped file, asked the operator, regenerated for opencode,
  tried spoofing the platform environment signals, and the orchestrator regenerated for claude minutes later. PLAN-LB-94 is
  staged **critical** (five deliverables: generation independent of the harness; no cross-harness refusal; mappings and
  surfaces not bound to an install; per-harness staleness; convergent regeneration). It goes ahead of PLAN-LB-93, which it
  overlaps on the generator. Until it ships and the main executor is regenerated once, any session that hits the mismatch and
  regenerates will break the other harness.
- 2026-10-25 — **One plan, PLAN-LB-93, fixes the four open defects.** Operator: create a single plan for fixing them all at
  once — the `build.py` freshness backstop, the stray main-checkout writes, the unshipped gate-truth half of PLAN-LB-55 and the
  flat-install generator bootstrap. They were folded into the already staged PLAN-LB-93 (six deliverables) instead of staging
  further plans, so the queue gains no row. The one-theme split guard is overridden on the operator's instruction and the spec
  says so; each deliverable keeps its own Done-when. The Open Defects and the stray-writes Watch now name PLAN-LB-93 as owner.
- 2026-10-25 — **Unreviewed last heads are settled: the standing authorization applies and nothing is asked.** Operator: with
  at least one valid CodeRabbit review and the reviews currently on quota, it is ok to move on. This confirms the standing
  merge authorization of 2026-10-18 (carried in the lane text § 7) and removes the reading of the 2026-10-23 ruling that
  added an ask step; the lane text as merged is correct and needs no change. A last head that changed logic after the
  qualifying review is covered by the same rule (LB-88, LB-80, LB-55, LB-53 all merged this way). The matching Watch is
  retired. The orchestrator no longer raises this as a question, and a landing's unreviewed last head is a note, not a finding.
- 2026-10-24 — **Both lane-switched plans started; the epic is full again at 4 of 4.** PLAN-LB-53 and PLAN-LB-55 were
  emitted in the runbook lane (operator instruction: emit the OpenCode lane, adapting only the plans being emitted) and
  the operator started both, so the rows are `running`. With LB-43 and LB-80 still in flight that is
  `parallelization_scope` 4 of 4: nothing further is emitted until a landing frees a slot. LB-58 remains the only
  plan-marshall-lane row staged; LB-82 and LB-90 stay staged in the runbook lane. The manage-status concentration noted
  earlier is now live: LB-53, LB-55 and LB-43 all touch that module, with LB-43's edit still undeclared.
- 2026-10-24 — **PLAN-LB-92 shipped with 2 of 3 deliverables, and the gap is recorded rather than smoothed.** D1
  (worktree creation produces an executor) and D3 (builds route through it) landed; D2's refresh verb shipped but its
  headline Done-when is unobservable because the executor's own tree-walking legs already resolve an added script. The
  run reported "not met as written" instead of reworking the clause, which is the behaviour the evidence-order rules ask
  for, and it ran every build `in_process` on itself — the introducing plan living through its own defect. Consequence:
  the high "a plan cannot run the verb it introduces" defect is **narrowed, not retired**; only the introducing plan's
  bootstrap remains. With LB-43 and LB-80 still running the epic is back to **2 of `parallelization_scope` 4**, so two
  slots are open.
- 2026-10-23 — **The PLAN-LB-91 landing frees the first slot since the epic filled.** Shipped (#1847) on an exact 7/7
  footprint; the row is `shipped` with its PR, landing and plan id stamped. With LB-43, LB-80 and LB-92 still running the
  epic is back to **3 of `parallelization_scope` 4**, so one slot is open — the block below says what fills it and why.
  The lesson the plan came from (`lessons-routing-046`) is closed by the merge: a rewrite remaps instead of invalidating.
  Note also that the operator-authorized executor regeneration in that run (main checkout to `0.1.1996`) closes the
  executor-surface residue recorded against the PLAN-LB-73 landing.
- 2026-10-23 — **PLAN-LB-53 held back by the operator; PLAN-LB-80 took the slot instead.** The plan was emitted from a clean
  gate verdict (declarative surface, determinate comparison, one shared file — below the prompt threshold), and the
  operator declined to start it with three plans already running. Recorded as a capacity decision, not a gate refusal:
  the row stays `staged`, sequenced, and re-emittable as-is. **The operator then started PLAN-LB-80 instead the same day**,
  which fills the epic to `parallelization_scope` 4 of 4 — so the `N − R` slot count is advisory capacity, not a mandate,
  and the operator, not the knob, decides which admitted candidate takes a free slot.
- 2026-10-23 — **Both emitted plans started by the operator; the epic is at its concurrency ceiling.** PLAN-LB-92
  (runbook) and PLAN-LB-43 (plan-marshall) were started from the block `analyze` emitted, and both rows are now `running`
  on the operator's confirmation — the emit≠running invariant is intact: the orchestrator never asserted a start it had not
  been told about. With LB-91 still running that made **3 of `parallelization_scope` 4 slots occupied**; PLAN-LB-80 has
  since been started too, so the epic now stands at **4 of 4**. LB-55, LB-82 and LB-90 stay staged behind the overlap
  prompt; LB-58 stays admitted and unemitted. Note: neither new plan's worktree existed under
  `.plan/local/worktrees/` when the starts were first recorded — LB-43's is created at phase-1 init, and LB-92's at lane
  setup. **Both now exist** (`lb-43-consumer-leaf-workflow-resolution`, `lb-92-lane-worktree-executor`), so the starts are
  corroborated on disk rather than resting on the operator's word alone.
- 2026-10-23 — **The PLAN-LB-73 landing was reconciled from the inbox, not from a paste.** The drain-completeness check
  reported `complete: false` on `total_tokens` alone, which the ruling above puts out of scope, so no defect was opened. The
  corroboration that mattered: merge sha `3873b6695` on `origin/main`, both CodeRabbit finding rounds at 10:47:35Z and
  12:00:34Z, the guard line at `guard.log:175`, a Sonar re-read of `0 confirmed` agreeing with the landing, and
  `surface_delta` measured **clean** (7 declared, 3 realized, `added_count=0`). Two Open Defects retired on the evidence
  (§7's summary-comment rule; the merge-gate re-read), one landing residue **contradicted** rather than folded (the
  `executor-skew` / `build-routing` "unknown_verb" claim does not reproduce: both resolve here), and one Watch narrowed
  (the install-lag trigger is satisfied for this cycle by content). **PLAN-LB-92's hold is released**: its four shared
  files with PLAN-LB-73 are no longer in flight.
- 2026-10-23 — **Operator rulings on the review quota, the standing authorization, Sourcery and token usage,
  and a focus rule for the whole epic.** (1) *CodeRabbit quota:* when the quota refuses a review, wait. Other plans
  draw on the same quota, so there is nothing sensible to do about it; no cap on concurrent plans, no escalated trigger
  ahead of the 90-minute floor. (2) *Selection covering later heads / a semantic fix after a qualifying review:* keep the
  standing authorization as written. The plan tries to get a re-review of the later head, and asks the operator when the
  quota prevents it. (3) *Sourcery:* optional, because it has a weekly limit. (4) *Token usage:* out of scope. This
  version of plan-marshall is replaced completely, so no token total, reasoning, cost or measurement aspect is worth
  work here. (5) *Focus:* fix high and blocking issues only; fine-tuning is not this epic's job (it restates the founding
  decision below: critical and high only). Every open aspect is revisited against that rule; the result is recorded in
  the entries that follow it. Consequences already applied: a landing that is `complete: false` on `total_tokens` alone is
  no longer recorded as an Open Defect or a recurrence; the `plugin_version` / `bundle_version` lead is not pursued; the
  Claude PreToolUse hook stays unset by choice.
- 2026-10-23 — **Inbox drain: 14 `lessons-routing` findings, one consumer requirement and the PLAN-LB-88 landing.**
  Review bot: the operator put `cuioss-review-bot` dormant and wants it removed completely, so CodeRabbit is the one required
  bot and Sourcery the optional one (the #1829 narrowing is intended; any remaining `cuioss-review-bot` entry in a
  `marshal.json` or `.github/project.yml` is a removal still owed, not a gap to restore). Dispositions under the focus rule,
  each from a sender-graded "high" that was NOT re-verified at HEAD unless stated:
  `pm-mcp-core-m2-m4-006` **staged** as PLAN-LB-90 (operator-set high); `-046` (history rewrite vs change ledger)
  **staged** as PLAN-LB-91 (the refusal exists at HEAD: `_cmd_lifecycle.py`); `-045` (foreign-target executor skew)
  **folded** into PLAN-LB-43 as D5, no new file surface; `-053` item 3 (root-level guards skipped before push) **folded**
  into PLAN-LB-58 as D4, no new file surface; `-053` item 2 (run attribution, log pointers) **folded** into PLAN-LB-44 as
  D3, surface widened by `ci_base.py` and `test/plan-marshall/tools-integration-ci/`; `-053` item 1 is already PLAN-LB-44
  D1; `-050` **folded** into PLAN-LB-46 (parked) as D6, items 3-4 already its D2-D4, no new file surface; **discarded** as
  not blocking: `-044` (argparse drift; the executor already reports the accepted set), `-047` (task closes before its
  verification), `-048` (declared footprint omits files), `-049` (in-run review coverage), `-051` (leaf search coverage),
  `-052` (manifest steps and tier oscillation), `-054` (merge-lock holder is the plan id; rare, residual accepted by the
  sender's operator), `-055` (`format_toon` second projection), `-056` (free-text placeholders in command templates; R1
  refuses command substitution on both harnesses), `-057` (domain content, low). Surface check after the folds:
  `corpus surfaces` reads PLAN-LB-43, 44, 46, 58, 90 and 91 as `declarative`.
- 2026-10-07 — **Epic created by operator instruction** ("create an orchestrator for the
  critical / high; remove them from the current orchestrator; archive / dormant the other
  orchestrators beside lessons-routing"). Scope is the 21 high-priority clusters of the
  cross-epic sweep; the roughly 50 medium and low clusters are recorded in `backlog.md` and are
  not staged. Alternative considered: stage all 70 — not chosen, the operator asked for
  critical and high only.

> ↪ Relocated to `settled.md` § "Decisions settled by the regrouping and the shipped plans" — the subjects are closed — the first cut was regrouped, the staged plans shipped or were superseded, the cleanups landed.

- 2026-10-08 — **Queue regrouped from 21 plans to 11 by operator instruction** ("make a full
  review of all plans. Rearrange that: adjacent plans (same component / topics) are bundled
  together; the plans aggregate a larger amount of deliverables (up to 12 are authorized); the
  plans are structured in a way to provide high parallelism"). Twenty specs were absorbed into
  ten new ones, PLAN-LB-22 to PLAN-LB-31, of 7 to 11 deliverables each; PLAN-LB-14 is
  unchanged. All 90 deliverables of the absorbed specs were carried, each exactly once, with
  their claim labels and surface entries copied unchanged; the move list is in Queue
  annotations. Scope-bloat guard: every new spec is above six deliverables and proceeds
  unsplit on the operator's authorization of up to twelve.
  - Two specs were cut at the deliverable level, because each spanned components that belong
    to different plans: PLAN-LB-05 (five waits in five components) and PLAN-LB-20 (schema work
    in the organisation repository, then enrolment gated on PLAN-LB-21's decision).
  - Alternatives considered and not chosen: cutting PLAN-LB-02 and PLAN-LB-09 by deliverable
    (it freed no additional pair); keeping PLAN-LB-12 with PLAN-LB-13 and PLAN-LB-05 D4 as one
    build plan (it made the build plan collide with the review plan through
    `await-long-running.md` and with the execute plan through `execution.md`).
  - No spec file was deleted. The twenty absorbed rows are `superseded`; each old spec carries
    a banner naming its successor, and its `## Expected Surface` was replaced by a `DERIVED`
    marker with the original entries kept under "Superseded Surface (record only)", so a
    retired spec no longer collides with the plan that carries its work.
  - What limits parallelism: `phase-6-finalize/SKILL.md` is edited by four of the new plans
    and `plan-marshall/workflow/execution.md` by three. Those two files, not the bundling,
    are why the finalize plans still run in sequence.
- 2026-10-09 — **parallelization_scope raised from 2 to 4 by operator instruction** ("set
  the parallelism to 4"). Four plans were already running on per-launch overrides
  (PLAN-LB-24, 32, 33 and 34); the knob now matches what the operator runs. The limit on
  real parallelism is unchanged: plans that share `phase-6-finalize/SKILL.md`,
  `execution.md` or the self-review workflow still run in sequence.
- 2026-10-13 — **PLAN-LB-39 antigravity-execution-fidelity staged** (WS-04) by operator
  instruction ("emit the antigravity plan"). Scope by operator decision: ONE plan, seven
  deliverables, above the ~6 split guard — the recommended split (dispatch + phase integrity vs
  context + measurement) was declined; and the two harness-agnostic critical items `-015`/`-026`
  (criteria rewritten, weakened tests) and `-016` (pushed head past its gates) are INCLUDED, over
  the recommendation to exclude them. Staging-time re-grounding at `71971784f`: the Antigravity
  `Task` tool maps to `invoke_subagent` and `platform-runtime subagent dispatch` already exists,
  but the `Task:` dispatch line is preserved verbatim in the generated output and nothing in phase
  5 calls the seam; `project_initial_setup` bridges no `CLAUDE.md`; nothing on the start path calls
  `orchestrator preflight`. **Held back** at the first `next`: it shares
  `functional-review.md` and two test directories with the running PLAN-LB-37; the operator
  declined to run them together. Emit once PLAN-LB-37 lands. **Hold released 2026-10-13**:
  PLAN-LB-37 landed (#1759, `d5c1e869f`); start from that commit or later. Still overlaps the
  staged PLAN-LB-26 and PLAN-LB-27 on `phase-5-execute/SKILL.md`, `execution.md`, `triage.md`.
- 2026-10-14 — **Inbox drain: two specs staged, one Watch retired.** PLAN-LB-40
  steward-upgrade-integrity takes `-011`'s defects and the `migrate-review-steps` removal in one
  plan because both edit `marshall-steward/scripts/upgrade.py`, `upgrade-flow.md` and the same
  steward tests; five deliverables after folding `-011` item 6 into D4 and dropping item 4's
  "add both review steps" half, which the removal makes moot because every configured
  repository already carries both. PLAN-LB-41 lb-37-review-leftovers takes `-012` items 1, 3 to
  7. `-012` item 2 (PLAN-LB-37's D12 outline wording drifted from what shipped) is not a file
  to fix — the outline is archived with the plan; recorded here as an instance of outline drift
  after in-flight re-scoping. Alternative considered: fold `-011` into a staged plan — no
  staged plan touches the steward upgrade.
- 2026-10-14 — **PLAN-LB-27 plan-footprint retired by operator decision** ("We are here
  maintaining software that will be replaced soon … the scope creep was authorized by the
  operator"). The scope-creep half is an advisory the operator routinely overrides; PLAN-LB-33
  (#1745) already shipped its D1, D2 and D4, and the D3 (`_collect_declared_files` globs the plan
  root, not `tasks/`) and D5 leftovers only sharpen that advisory. The staging-allowlist half
  guards against one observed incident (#1700's 2038-file deletion, restored) and no observed
  secret leak; a staging verb plus a rewrite of every commit site is not worth it before
  plan-marshall-mcp, where footprint-bound staging belongs in the design. Alternative
  considered: trim the plan to the allowlist plus the D3/D5 leftovers — not chosen.
- 2026-10-14 — **Five plans staged from the unowned high/critical Open Defects** by operator
  instruction ("stage the other plans as proposed", after a review that found only two staged
  plans against seven unowned high items). Drafted by one read-only `execution-context-level-5`
  leaf at `3133627e8`, every claim re-read there; adjudicated and written here.
  - PLAN-LB-42 outline-qgate-integrity — `lessons-routing-022`, `-023`, `-010` (narrowing half).
  - PLAN-LB-43 consumer-leaf-workflow-resolution — `lessons-routing-021`.
  - PLAN-LB-44 red-ci-triage-route — `lessons-routing-019`.
  - PLAN-LB-45 runtime-stamp — harness, model, effort and plan-marshall version recorded per plan
    and required in the landing facts; operator request, extends PLAN-LB-39 D5.
  - PLAN-LB-46 review-bot-signal-gaps — `lessons-routing-027`, the `-017` remainder, the size
    refusal loop from PLAN-LB-37's landing.
  - Not staged, by the same "worth it before the rewrite" test: the sibling-repository
    deliverable lifecycle (`lessons-routing-018`) — structural, left to plan-marshall-mcp.
  - Dropped at drafting as already fixed at HEAD: `set-list --values ""` exit 2 (the executor
    forwards empty values); `re_review_on_loopback` read from the wrong source; a fix commit not
    re-arming re-review on the trigger-B path. One premise corrected: the harness IS detected
    from the environment (`target_context.resolve_target`), only its source is not reported.
  - Split guard: PLAN-LB-45 and PLAN-LB-46 carry five deliverables each and proceed unsplit;
    PLAN-LB-46 D5 is the first to drop and splits out if it needs a `cuioss-review-bot` field.
- 2026-10-14 — **PLAN-LB-26 reconciled as shipped (#1769) with an adversarial landing; PLAN-LB-47
  staged** for its regressions. The landing claimed 11/11; verified 6 met, 4 partial, 1 unmet,
  plus three high-severity regressions. Recorded as `shipped` because the PR merged; the gaps
  ride PLAN-LB-47 rather than reopening a merged plan. Inbox candidate lessons `-001` and `-002`
  (owed `architecture enrich` hints "the project treats triage / test-failure as a standing
  consideration") discarded: content-free, and the five `taken_into_account` test failures behind
  `-002` were legitimate (D11-owned pins, later green).
- 2026-10-14 — **OpenCode fixes staged as two plans** by operator instruction ("create a plan for
  fixing the known opencode issues"; "we switched to Opencode 2"). Drafted by a read-only level-5
  leaf against `501aeb313`, the installed 2.0.28 binary and `opencode.db`; split because the work
  is eight deliverables in two places: PLAN-LB-48 opencode-2-compat (what a session may do —
  live harm) and PLAN-LB-49 opencode-measurement (tokens, dispatch evidence). Of the six known
  issues: token source and dispatch audit → LB-49; `opencode.json` → LB-48 (re-diagnosed);
  backlog §4.3 "installs ship skills without `workflow/`" **already fixed** by `35b5589b5`
  (installed tree has `workflow/`); finalize build logs missing / wall time 1-init only — not
  OpenCode-specific (LB-31 under OpenCode archived them; LB-26's gap follows its provider crash),
  not staged; the missing-`/` ledger write — the operator typed it without `/`, and `/plan-marshall`
  is not a registered OpenCode command anyway (it is `plan-marshall-plan-marshall`); the ledger
  write is an all-harness Write-Boundary gap, already an Open Defect. Zero-vs-`unknown` stays
  PLAN-LB-39 D5; the harness/model stamp stays PLAN-LB-45.
- 2026-10-15 — **OpenCode plans restructured; medium and low OpenCode findings dropped** by
  operator instruction ("revisit all plans regarding opencode and restructure them if sensibly
  needed. Opencode aspect are still the highest prio here until the quality improves. … Drop
  (archive) low and medium findings on opencode runs. Focus on high and critical"). Severity rule
  applied: critical/high = an integrity breach (graded against rewritten criteria, a head or phase
  no gate saw, an operator decision taken by the agent), an enforcement hole the breaches ran
  through, a regression on `main`, or the measurement that every OpenCode landing lacks; medium/low
  = cost, reporting cosmetics, documentation drift, single-instance or already-mostly-fixed items.
  Changes:
  - New: PLAN-LB-55 gate-head-truth (from PLAN-LB-52 D2/D3 + the LB-26 barrier defect), PLAN-LB-56
    session-boundary-enforcement (guard gaps, inline finalize commits, stale approvals),
    PLAN-LB-57 reviewer-enrolment-and-instrument (PLAN-LB-48 D6/D7 moved out; not OpenCode).
  - PLAN-LB-48: D5 efficacy-doc corrections dropped; D6/D7 → PLAN-LB-57; gains D5 OpenCode bridge
    from PLAN-LB-51. PLAN-LB-49: D4 (dispatch audit, gh audit, finalize boundary rows) dropped.
    PLAN-LB-52: request-gate composition, infeasibility reference, coverage freshness dropped.
    PLAN-LB-53: D3 phase-time booking dropped. PLAN-LB-54: former D2, D4, `--apply` and minor
    defects dropped. PLAN-LB-45: re-pointed from PLAN-LB-39 to PLAN-LB-50.
  - Re-checked at HEAD before staging: the compile-auto-closes-quality-gate defect (LB-26) is
    largely fixed by the analysis-entitlement map (`_build_examined.py` `FINDING_TYPE_ANALYSES`,
    lint split from compile); the residue (a mypy-typed `build-error` cleared by `compile`) is
    medium and dropped. The barrier defect is live: `classify_bot` checks participation first
    (`review_completeness.py:802-805`).
  - The `ls` / `python3` passes on PLAN-LB-42 trace to the 8 persisted OpenCode approvals of
    2026-10-08 (operator action still owed), not only to a missing rule; PLAN-LB-56 D3 reports them.
  - Dropped items recorded in `settled.md` § "Dropped 2026-10-15".
- 2026-10-15 — **OpenCode model switch recorded** (operator): plans emitted from now run
  DeepSeek Flash1 instead of `muse-spark-1.3-contributor`. Recorded as a Watch with the Muse
  baseline and the attribution rule. No spec is changed for the switch: every restructured spec
  already carries "do not merge deliverables" and pre-fix evidence clauses, which are the
  model-sensitive failures seen so far. Recommendation logged, operator's call: emit a small,
  crisp plan first (PLAN-LB-53 or PLAN-LB-54, two deliverables each) so the first DeepSeek signal
  is not drowned by plan size.
- 2026-10-16 — **Remaining plans run in the OpenCode runbook lane, not `/plan-marshall`**
  (operator: "Soon we need to switch to the free models of opencode … they should not run
  plan-marshall plan (take too many tokens by now) … fallback on our runbook approach"). The runbook
  `.plan/local/opencode/RUNBOOK.md` was rewritten for this epic: 1,065 → 256 lines; the old
  `oc-plans` version is kept as `RUNBOOK-oc-plans-archive.md`. Changes:
  - Input is the staged spec itself (`.plan/orchestrator/live-blockers/plans/PLAN-LB-NN-*.md`,
    git-tracked on `main`); the `oc-plans` authoring and move steps are gone.
  - The hard rules are restated as one list, including the evasion routes graded on PLAN-LB-40/42
    (`python3 -c`, ad-hoc scripts, `git grep`, `sleep`).
  - Done-whens must be seen failing before the fix; the plan-marshall trailer replaces the
    opencode identity.
  - Both required reviewers are triggered explicitly (`/review`, `@coderabbitai review`), and the
    operator's CodeRabbit policy is stated verbatim (90 min × 10, then close unmerged and reopen,
    then ask). Only an operator-selected option is an authorization.
  - The worktree is made through `git-workflow worktree-create` / `worktree-remove`, plus a
    generated worktree executor (no `cp`, which the guard refuses).
  - The landing goes to the epic inbox as `oc-lb-NN-{slug}`, with `harness` and `model` and the
    report as its body.

  Emit form from now on: `load .plan/local/opencode/RUNBOOK.md and follow strictly the instructions.
  Plan: {spec path}`. Grading is unchanged: each landing gets the same adversarial analysis, with the
  model read from `opencode.db`.
- 2026-10-16 — **Runbook amended after PLAN-LB-61, the first runbook-lane landing:**
  - sub-agent prompts carry Section 1 verbatim (its self-review leaves ran 13 `git grep` and 12 `ls`,
    and redirected to `/tmp` to get around R1);
  - no operator question about a CodeRabbit quota until the 90-minute × 10 cycles and the
    close/reopen are spent, waiting with `ci pr wait-for-comments`;
  - merge questions state per-reviewer, per-head facts and mark no rule bend "Recommended";
  - re-fetch `main` immediately before enqueue;
  - cleanup by `git worktree remove` + `prune-local-and-remote-ref` + `switch-and-pull`
    (`worktree-remove` refuses in this lane);
  - the landing lists every model, every operator question, and every `guard.log` line for the run.

  The runbook is now 316 lines.
- 2026-10-17 — **Runbook amended after PLAN-LB-62:**
  - stay inside the repository (a run printed `~/.config/opencode/service.json` into its
    transcript);
  - there is no session budget (runs stopped and skipped `verify` and PR-comment handling "for
    budget");
  - the free-text rule is restated at enqueue;
  - the report quotes question-tool calls only, listing free text separately.

  The runbook is now 330 lines.
- 2026-10-17 — **Runbook amended after PLAN-LB-54:**
  - re-trigger CodeRabbit no sooner than 90 minutes after a refusal, whatever the bot's ETA;
  - an aborted question has no answer: ask again;
  - cleanup never uses `--force` or `git branch -D`;
  - a filed inbox message is corrected only through `inbox amend`.

  The runbook is now 342 lines.
- 2026-10-17 — **Runbook amended after PLAN-LB-64:** re-read the runbook in full at every session
  start, restart and compaction (the run loaded it once and missed the mid-run amendments);
  repository files are edited only inside the worktree (PLAN-LB-52 left drafts in the main
  checkout).
- 2026-10-17 — **Operator: the runbook lane ships as a product skill** ("do the proper version").
  Staged **PLAN-LB-66 runbook-lane-skill** (WS-04, runbook lane):
  - D1: the bundle skill `plan-marshall:runbook-lane`, repository-neutral;
  - D2: a `resolve` verb that takes the slug, build, reviewers and trailer from the project's own
    configuration and fails closed.

  The sender id becomes `rb-{plan}`. After it lands, plans are emitted as
  `/plan-marshall-runbook-lane plan={spec}`, the local `RUNBOOK.md` is retired, and lane
  amendments go through PRs.
- 2026-10-17 — **Runbook amended after PLAN-LB-63:** never move the main checkout by hand;
  `switch-and-pull` is the only sanctioned update (PLAN-LB-63 ff-merged it under the live PLAN-LB-66).
- 2026-10-17 — **Operator: the inert executor recovery is high**, added to the next plan.
  It is staged as PLAN-LB-43 D3: a direct-path recovery entry that the executor's own failure
  output names, a re-probe after regeneration, and end-to-end subprocess tests.
- 2026-10-18 — **Operator: standing CodeRabbit merge authorization.** "If there was at least one
  correct CodeRabbit review and all findings were handled: you are authorized to merge", because
  the quota regularly blocks a review of the latest head. Applied at once to the local runbook
  (§ 7 "Standing CodeRabbit authorization", with the quota policy only while no qualifying review
  exists). The authorization:
  - covers CodeRabbit only, never cuioss-review-bot;
  - needs a formal review, all findings handled and threads resolved, and one re-trigger after
    the last push;
  - never applies to a PR with no CodeRabbit review (PLAN-LB-52 stays blocked).

  This settles the PLAN-LB-63 free-text question. Staged **PLAN-LB-67
  standing-review-authorization** (WS-04, runbook lane, 2 deliverables) to carry the rule into
  the `runbook-lane` skill, repository-neutral and keyed on a per-bot `quota_limited`
  declaration. Emit after PLAN-LB-66 lands.
- 2026-10-18 — **Operator: PLAN-LB-67 becomes the single runbook-lane follow-up.** Added three
  deliverables from the pm-mcp-clients Antigravity runbook:
  - D3: per-step personas, with adversarial-refute in self-review and PR triage;
  - D4: `resolve` returns the domain skills for the modules in the spec's Expected Surface;
  - D5: a docs-only build path keyed on the project's footprint rule.

  Five deliverables, kept unsplit by operator instruction.
- 2026-10-18 — **Operator: always use the new `runbook-lane` skill, to find its bugs early.**
  Every emit after the drain uses `/plan-marshall-runbook-lane plan={spec}`, PLAN-LB-67 included.
  The local `RUNBOOK.md` is no longer used for new emits; only the running PLAN-LB-45 still runs
  on it. The skill's known gaps (the ten weakened rules, the 2026-10-18 rules) are fixed by
  PLAN-LB-67 D1 and D6. Until then, every landing audit judges runs against the skill version they
  loaded, and records each gap the run hit as evidence for PLAN-LB-67. Precondition for the first
  emit: `/sync-harnesses`, plus a main executor regenerated for Claude.
- 2026-10-18 — **PLAN-LB-52 fix-forward staged as PLAN-LB-70** (high), with four deliverables:
  - the gate refuses only genuinely open criteria;
  - spec and citation parsing matches real documents;
  - the seal and the snapshot are bound in the status record;
  - deleted-assertion rows reach the validator.

  Emit before PLAN-LB-55. Runbook amended: never regenerate `.plan/execute-script.py`; never
  offer an authorization for a head that does not exist yet.
- 2026-10-18 — **PLAN-LB-66 landed; PLAN-LB-67 gains D6** (high): restore the ten runbook rules
  the skill weakened, test rule parity, and carry the "pending" rule. The runbook was amended
  (§7): a merge question states CI or `verify` status only from a result obtained after the last
  push. **Recommendation pending operator:** run PLAN-LB-67 itself under the local `RUNBOOK.md`
  (old form). Retire the local file only after PLAN-LB-67 lands, since the skill is not yet a
  faithful replacement.
- 2026-10-18 — **Operator: domain skills are named at the orchestrator.** Each spec deliverable
  carries `Skills:` and `Persona:` lines, filled at staging time from the project's
  configuration. The lane loads exactly what is named, checks it exists, and records any
  surface-drift additions.
  - PLAN-LB-67 D4 was rewritten: the lane loads the named skills and checks they exist, instead of
    `resolve` returning them.
  - PLAN-LB-69 gains D4: the template lines, an `orchestrator spec-skills` verb, an existence check
    in `next`, and a gap flag in `cleanup`.
  - Until PLAN-LB-69 lands, the orchestrator writes the lines by hand into each spec before
    emitting it, starting with PLAN-LB-67 and PLAN-LB-69 themselves.
- 2026-10-18 — **Operator: the landing audit becomes the orchestrator contract.** The method used
  since PLAN-LB-61 is two read-only leaves (fidelity and process), the lane contract in force,
  report contradictions, spot checks, and a grade. It moves into `analyze`, with full depth
  mandatory for OpenCode, Antigravity and unguarded runs. Staged **PLAN-LB-69
  runbook-landing-audit** (3 deliverables):
  - D1: `analyze.md`;
  - D2: a read-only session-store reader per harness that never reads permission data;
  - D3: template and payload sections.

  Emit after PLAN-LB-66, alongside PLAN-LB-67.
- 2026-10-18 — **PLAN-LB-65 fix-forward staged as PLAN-LB-68** (high):
  - admit deployed bundle scripts exactly, so the steward runs again, and scope R5 for consumers;
  - R6 names the plan from `git -C`;
  - close the R5 side doors and make the executor permit exact.

  Emit it before PLAN-LB-43, whose D3 recovery admission it provides. PLAN-LB-43 D3 corrected:
  the "CLI recovery command" PLAN-LB-65 reported does not exist.
- 2026-10-18 — **Operator: drain, then restart on the new structure.** No new emits until every
  running plan (PLAN-LB-45, PLAN-LB-52, PLAN-LB-66) has landed. Then, in this order:
  1. set `lane=runbook` on the runbook rows;
  2. retire the local `RUNBOOK.md`;
  3. emit PLAN-LB-67 first, through `/plan-marshall-runbook-lane plan={spec}`;
  4. emit the rest of the queue in the same form.
- 2026-10-18 — **Operator: every emit runs in an OpenCode session through the lane skill, and
  every landing gets the full-depth audit.** The harness is stated here because the entries above
  imply it. The skills each plan loads are adjusted at the orchestrator from the project's
  configuration (see "domain skills are named at the orchestrator"). On handling a result, the
  audit is thorough — fidelity and process leaves, the lane contract in force, spot checks, a
  grade — and the gaps it finds feed PLAN-LB-67. The drain rule above is relaxed by the operator
  in the same session: plans disjoint from the still-running PLAN-LB-45 are emitted alongside it
  rather than after it.
- 2026-10-18 — **Operator: the PLAN-LB-43 D4 finding comes from an OpenCode run in a consumer
  repository.** `upgrade` stopped at Stage 1 `cache-freshness-check` (`freshness: unknown`)
  because the flat OpenCode install has no resolvable manifest. It is filed as PLAN-LB-43 D4 (high).
- 2026-10-19 — **PLAN-LB-70 landed; PLAN-LB-74 and PLAN-LB-75 staged.** PLAN-LB-74 (WS-03, runbook
  lane, **high**, four deliverables): D1 the two Major findings left unhandled on #1815, D2 a verdict row
  answers a criterion only by id or exact text, D3 the integrity record under the status writer's lock
  with protected keys, D4 the `.plan/` citation escape. PLAN-LB-75 (medium, four deliverables): the
  triage source and `criteria_gate`, the re-freeze routing and the stale standards, the test-integrity
  reach, and the sticky override heads. Emit PLAN-LB-74 before the staged PLAN-LB-53 and PLAN-LB-55:
  they overlap its files and run through the gate it repairs. The false-merge-question rule is folded
  into PLAN-LB-73 D1 (no new file surface). **An operator selection made on a false premise is not an
  authorization:** the merge of #1815 stays on `main` and its findings are carried by PLAN-LB-74.
- 2026-10-19 — **PLAN-LB-72 landed; PLAN-LB-73 staged** (WS-04, runbook lane, low): D1 the lane text
  states each rule once (branch row, §0a template, the grading by order, §6 identifiers, §4 docs-only
  `test-compile`) and §7's qualifying-review signal counts CodeRabbit's marker-bearing summary
  comment; D2 the tests of the timeout, the probed layout, the `test-compile` evidence and the glob
  helper import can fail for the reason they name. The Done-when authoring rule was folded into
  PLAN-LB-69 D4; the fold adds no file surface (its declared surface already holds
  `templates/plan-spec.md`, `workflow/decompose.md` and `workflow/cleanup.md`).
- 2026-10-19 — **Operator: stay on OpenCode with `deepseek-v4.1-flash` for the next four runs,
  then switch back to Muse for a comparison.** "Four" counts the runs emitted AFTER the four now in
  flight (PLAN-LB-45, PLAN-LB-68, PLAN-LB-70, PLAN-LB-72, all on DeepSeek Flash). The comparison round
  that follows runs on Muse (`muse-spark-1.3-contributor`). Protocol, so the model is the only
  variable:
  - Muse runs also go through the `runbook-lane` skill (the eight earlier Muse runs ran under the
    plan lifecycle and the local runbook, so they are history, not a baseline for this round).
  - Plans of comparable size and surface type, and the same landing audit at full depth.
  - Compare the same fields every time: process grade, deliverables met against claimed, test-first
    share of the Done-whens, report contradictions, rule breaks, cost, wall clock, sessions.
  - Which plans go to Muse is chosen when the round starts, not now.
- 2026-10-19 — **PLAN-LB-71 landed; PLAN-LB-72 staged** (WS-04, runbook lane, medium): D1 the
  classifier never says `docs-only` for a path the project's CI builds (the skip class came from the
  architecture; a `docs/` module, `.asciidoc` and `README.MD` can fail open in other projects),
  D2 the existence-check and rule tests can fail for the reason they name, D3 structured evidence
  labels (`order`) and the `test-compile`-per-pushed-head, self-review and unknown-verb rules. The
  chain PLAN-LB-67 → 71 → 72 is a fix-forward of the lane skill itself; park PLAN-LB-72 if the
  operator prefers to harvest the lane's gaps through PLAN-LB-69 instead.
- 2026-10-19 — **PLAN-LB-67 landed; PLAN-LB-71 staged.** Fix-forward (WS-04, runbook lane, high)
  with three deliverables: D1 the skill-existence check in every deployed layout, D2 the docs-only
  classifier derived from the project and never failing open, D3 the restored rules read the same
  everywhere with parity tests that can fail. The unfinished `Task` → `subagent` alignment is
  folded into PLAN-LB-48 D2 (expected surface updated in the same edit: three more standards).
  Open for the operator: whether a quota-limited optional reviewer (`sourcery`) may be covered by the
  standing authorization; today it is keyed on `quota_limited`, wider than "CodeRabbit only".
- 2026-10-17 — **Mid-flight: PLAN-LB-66 edited the main checkout** (D3, 6 files) instead of its
  worktree, against runbook §1. Operator interrupted it; the D3 work moved to the worktree and main
  is clean. Debited at its landing.
- 2026-10-17 — **PLAN-LB-52 is blocked on the CodeRabbit quota** (PR #1798 green, cuioss-review-bot
  reviewed). Its inbox `-001` is a mid-flight report, not a landing; the row stays running.

## Open Defects

- **`executor-skew` answers `could_not_check` on every flat OpenCode install (PLAN-LB-95 landing, 2026-10-26; medium; not
  staged).** A flat install has no `{bundle}/{version}` directory, so the lane text version cannot be derived and each
  OpenCode lane asks the operator two questions that cannot change the outcome (LB-95 asked both; regenerating the executor
  did not change the verdict). Related to PLAN-LB-96, which makes the flat install resolve its bundles root, but not part of
  it. Under the high-and-blocking focus rule this waits.
- **The emitted lane command cannot read a spec from the ledger worktree (PLAN-LB-90 landing, 2026-10-25; high; not staged).**
  The lane accepts `resolve --spec-from-ledger`, but `/plan-marshall-runbook-lane plan=…` carries no argument that sets it and
  the lane text names no trigger for adding it, so a spec edited in the ledger worktree reaches a lane only after a ledger
  land. The PLAN-LB-90 spec left this to the orchestrator side (`orchestrate.md` Step 5 and the command's argument handling).
  Until it is staged and shipped, land the ledger before each emit that follows a spec edit.
- **CRITICAL — the shared `.plan/execute-script.py` is rewritten back and forth by two harnesses (found 2026-10-25;
  fixed in source by PLAN-LB-94, #1861; LIVE EFFECT OWED until `/sync-harnesses` and one executor regeneration from the
  merged template, then the stamp war is over; until then the workaround below stands).** The test-suite-as-writer clause was
  not reproduced in the LB-94 run (no `generate_executor` log line in its test windows; the LB-94 landing says the autouse
  sandbox covers it); the earlier LB-90 observation is unexplained and may have been the LB-43 D5 suites LB-94 rewrote. The PLAN-LB-43 D5 stamp makes a Claude call fail on an OpenCode-stamped executor and the
  reverse; the printed remedy regenerates for the refused harness, which refuses the other. Evidence: the PLAN-LB-90 lane's
  regenerate at 07:59:21Z and spoofed-environment call at 07:59:30Z on 2026-10-25, the orchestrator's regenerate at about
  08:01Z, and an earlier flip at 20:01Z on 2026-10-24 (executor mtime) beside the same lane's skew and drift calls. Measured:
  the two executors are otherwise identical in this checkout. **PLAN-LB-90 landing (2026-10-25):** the lane answered the
  mismatch with 37 calls under a spoofed identity (`CLAUDE_CODE_SESSION_ID=1 OPENCODE= …`, 07:59:30Z to 09:51:27Z), and a
  full `module-tests` run is a third writer (every `generate_executor` verb ran through the main executor at 08:04:51Z to
  08:05:46Z); both folded into PLAN-LB-94. Workaround until it ships: after a mismatch, regenerate with
  the repository-source generator (`recover --target claude` for the orchestrator), expecting the lane to flip it back.
- **HIGH — a flat install cannot complete the `marshall-steward` upgrade on this machine (found 2026-10-26 on the `pm-mcp-core`
  project; owner PLAN-LB-97, staged and held).** `manage-config sync-defaults --backfill-bot-roster` stops with `step body doc
  not found: ~/.config/opencode/skills/automatic-review/SKILL.md`, because `configurable_contract` and
  `_manifest_validation` join bare skill names onto the skills root. Reproduced here by a direct probe of the installed flat tree
  (every built-in step id resolves to a path that does not exist). The nested plugin-cache copy of the same version runs the verb
  fine, which is the lane's workaround. **Discrepancy explained (2026-10-26):** the operator ran the same upgrade and land to completion at
  0.1.2017 on the second machine, also under OpenCode. A direct probe there shows the flat copy has the same missing step doc,
  and both executors carry the flat and the nested entry for every script; the executor prefers the runtime harness's own root
  and otherwise the declared order (Claude cache first), so the upgrade ran the nested copy there. **Observed:** the second machine's
  steward report (PR #228, `chore(steward): land steward-maintained artifacts`, merged 2026-10-26) records the same `step body
  doc not found` failure and a completed reconcile with `OPENCODE` unset, which made the executor dispatch the Claude-cache copy
  of the same 0.1.2017 code. The defect is real on both machines; the workaround is `OPENCODE` unset for the `manage-config`
  verbs. This entry is the concrete form of the medium entry below, whose residue R1 and R2 PLAN-LB-97 absorbs.
- **MEDIUM — a flat install still has blind spots after PLAN-LB-96 (recorded 2026-10-26 from its landing residue; not
  staged; R1 and R2 now owned by the held PLAN-LB-97).** R1: the built-in phase-5/phase-6 step docs are undiscoverable on a flat install
  (`resolve_skills_root(...) / 'phase-5-execute'` against the deployed `plan-marshall-phase-5-execute`), so
  `find_implementors_with_status` reports those surfaces unresolved. R2: `get_build_extension_paths` joins bare build-skill
  names, so the file-to-build route derivation finds no build extension on a flat install; build commands come from the
  discovered domain bundles and the persisted architecture only. R3: `scan_extensions --marketplace-path` expects a marketplace
  root. R4: `PM_MARKETPLACE_ROOT` has two incompatible meanings (`_doctor_shared` wants the parent of `bundles/`,
  `marketplace_paths` the directory containing `marketplace/bundles`). Whether `quality-gate` and `verify` resolve on a real flat
  install is not shown by any test; one runbook lane on the second machine after the install decides whether R1 and R2 earn a
  plan.
- **CRITICAL — a flat OpenCode install cannot resolve its bundles root (found 2026-10-26 on the operator's second machine;
  owner PLAN-LB-96, FIXED IN SOURCE by #1868, merged 2026-10-26; not live until the harness sync here and the new plugin
  version installed on the second machine; the hand-made shim and `PM_MARKETPLACE_ROOT` workarounds below become unnecessary
  once it is).** `resolve_bundles_root` accepts only the marketplace and versioned-cache shapes, so six
  import-time call sites (`_cmd_client_build`, `_config_core`, `_manifest_validation`, `plugin_discover`, `_doctor_shared`,
  `_cmd_extension`) raise `could not locate a 'plan-marshall' bundle` and `runbook_lane resolve` never starts. Reproduced against
  the generated tree; masked here by a hand-made bundle-identity shim in `~/.config/opencode/skills/plan-marshall/`. Behind it,
  extension discovery finds no bundle in a flat tree (`architecture modules` empty, no `quality-gate` or `verify`): the
  discovery loops treat each directory as a bundle and the OpenCode and Antigravity emitters do not deploy `implements:`.
  Workaround on the affected machine: create `~/.config/opencode/skills/plan-marshall/.claude-plugin/plugin.json` (name
  `plan-marshall`, a version, a description) and export `PM_MARKETPLACE_ROOT` at a plan-marshall checkout (untested); both
  hide the defect. The operator chose to wait for the plan to land.
- **CRITICAL — the generated executor puts every cached plugin version on PYTHONPATH, oldest first (found 2026-10-25 on the
  operator's second machine; regression of PLAN-LB-94 D3, #1861; FIXED IN SOURCE by PLAN-LB-95, #1865, merged 2026-10-26; not
  live until the harness sync and an executor regeneration, and on the second machine until the new plugin version is
  installed there).** `_same_root_script_dirs`
  (`execute-script.py.template` L588-621) globs the whole install root and sorts the result as strings, so a script from
  `0.1.2010` imports its helpers from the oldest cached version that has them: `marshall-steward` on a not yet enrolled
  project stopped at Step 4 with `ImportError: cannot import name 'STANDING_RULES_BRIDGE_MARKER' from 'antigravity_runtime'`
  (loaded from `0.1.1916`, eight versions cached). Scripts that need no newer helper run old helper code silently. Reproduced
  here: 15 cached versions, 1065 directories, `platform-runtime` `0.1.1969` at index 38, `0.1.2010` at index 808. This checkout
  and the PLAN-LB-94 lane did not see it because a developer checkout resolves scripts to the tree, and every PLAN-LB-94
  fixture held one version per bundle. Affects every consumer project and every harness install with more than one cached
  version. Workaround on the affected machine until it ships: delete the old cache version directories, leaving the newest.
- **The `test-compile` freshness backstop fails green builds on a fast runner (PLAN-LB-43 landing, 2026-10-24; medium; not
  staged).** `build.py` L540-580 fails `verify` closed when mypy exits 0 faster than a plausibility bound (here 1801 files in
  8.2 s, 205-220 files/s against a 200 files/s limit). It failed `verify / verify` three times on PR #1851 (twice on the PR
  head, once in the first merge-group run) and passed on re-run each time, with mypy reporting no issues; it cost operator
  questions and re-queue time. The bound is a heuristic against a stale-cache false-clean; CI runs cold, so the false-clean
  risk it guards does not apply there. Decision for the operator: stage a fix (a CI-aware bound, or a retry-once) or accept
  the reruns. **Recurrence (PLAN-LB-53, 2026-10-25):** the same guard tripped once on PR #1857 (211 files/s) and passed on
  re-run: four failures across two PRs, all cleared by a re-run. **Owner: PLAN-LB-93 D3 (operator, 2026-10-25).** Read for the
  spec: mypy always runs `--no-incremental`, so a cache cannot answer, and the 200 files/s ceiling was calibrated on 417 files
  at 71 files/s.
- **The gate-truth half of PLAN-LB-55 is unshipped, and it sits in the lifecycle lane only (PLAN-LB-55 landing, 2026-10-25;
  medium; not staged).** An armed auto-merge is not bound to its head; `pre_merge_gate merge` does not run the required-bot
  participation check; the roster-read error, stale-bot trigger-before-ask, generated barrier option set, `merge_lock`
  recovery loop, merged-under-authorization record and mutex re-acquire are unimplemented, so `coderabbit.md`'s policy is
  documented and not enforced. The runbook lane's skill names neither `pre_merge_gate` nor the barrier, so a runbook run
  would not have used these gates; its merge rests on § 7 of the lane text. **Owner: PLAN-LB-93 D5-D6 (operator, 2026-10-25,
  asked for regardless of the lane).** The spec adds one constraint from the same day's ruling: the participation check must
  admit a quota-limited required reviewer that has a qualifying review. It also records that `branch-cleanup.md` L1041 still
  tells the operator to "move [a required bot] to optional" for a `declined` or `refused_hard` state.
- **The recovery command an executor refusal prints cannot start in the OpenCode install (found 2026-10-25; high; owner
  PLAN-LB-93, staged).** `executor_target_mismatch` prints `python3 {plugin_root}/plan-marshall-tools-script-executor/scripts/generate_executor.py recover …`; run
  as printed it exits 1 with `ModuleNotFoundError: argparse_surface` (before and after a sync of all harnesses). The
  bootstrap resolves `{skills}/{lib}/scripts` and the flat install names the directories `plan-marshall-{lib}`. The same
  loop is in four sibling entry scripts (not run). Workaround used: the same script from the repository source.
  The cause of the executor's re-stamp for another harness was not established.
- **RETIRED 2026-10-23: the PLAN-LB-88 landing carries `open_issue_count=0` from five reads the run took itself
  (`landings/PLAN-LB-88.md`).** **The Sonar read the lane now requires has never been taken on a real pull request (PLAN-LB-85 landing,
  2026-10-23; high; owner: the next runbook run, and an operator step).** `lb-85-lane-sonar-issues` shipped the
  verbs and could not run them on its own PR: the main checkout's executor predates the change, the worktree has none,
  and the only route that writes a worktree executor is a direct `generate_executor.py` call, which the guard refused
  (R5, `guard.log` 16:35:56Z). The landing carries `step.sonar-roundtrip.open_issue_count=unknown`. Until a run reads
  a PR with the merged lane text, the gate's verdicts on a real analysis are unobserved; `resolve` on the merged tree
  reports `sonar: configured`, project `cuioss_plan-marshall`. **2026-10-23: the executor was regenerated and the
  orchestrator took the read for the merged PR** (`sonar read_open_issues --project cuioss_plan-marshall --pr 1839`):
  `count_status: confirmed`, `open_issue_count: 0`, no rules. So #1839 had no open Sonar issue, the verb works against
  the live service, and the landing's `unknown` was a missed measurement, not a hidden finding. Still open until a runbook
  landing carries the measured count itself (the lane's own read step, not the orchestrator's).
- **A plan whose own lane text calls a verb it introduces cannot run it, and the guard refuses the bootstrap
  (PLAN-LB-85 landing, 2026-10-23; raised to high by the operator on 2026-10-23; owner now PLAN-LB-92, the next plan).**
  Either the guard admits the generator verb, or worktree creation generates the per-tree executor. The build-server
  fallback `executor_absent_from_worktree` is the same gap seen from the build side (every build ran `in_process`).
  Retire when PLAN-LB-89 ships and a worktree can run a verb added by its own plan. **Recurrence 1 (PLAN-LB-88,
  2026-10-23):** the run needed an operator question ("stale sonar surface") and a hand-run executor regeneration. PLAN-LB-89
  is parked by the focus rule; the cost is one operator question per affected run, not a failed run.
  **NARROWED, STILL OPEN — 2026-10-24 (PLAN-LB-92 shipped #1850, 2 of 3 deliverables).** The *worktree-creation* half is
  closed: `worktree-create` now produces `{worktree}/.plan/execute-script.py` for every plan, non-fatally and idempotently,
  and `build-routing` answers `auto` when it is present. What survives is the **introducing plan's own bootstrap**: a plan
  that adds a script verb cannot invoke it from its own worktree, because no executor's surface carries it yet. LB-92's D2
  added a refresh verb for that case, but its Done-when ("stale before the verb") is unobservable — the generated
  executor's tree-walking legs resolve an added script first — so D2 shipped as a tool, not as a proven remedy. The lane
  text now names the one bootstrap route (the registered generator, run from the worktree) and treats a zero-executor
  worktree as a blocker rather than hunting a path. The retire condition is unchanged and still unmet on its second
  clause: a worktree still cannot run a verb *its own plan* adds.
- **OUT OF SCOPE since 2026-10-23 (measurement; see Decisions) — `plugin_version` is recorded as `0.1` beside `executor_version` `0.1.1986` (PLAN-LB-85 landing, 2026-10-23;
  medium; lead, owner PLAN-LB-84 once confirmed).** The landing copied what its stamp source reported;
  `platform_runtime runtime-info` run here (Claude) also returns `bundle_version: "0.1"`, while PLAN-LB-49's landing
  carried `0.1.1983`. **Cause found (2026-10-23):** `read_bundle_version` (`runtime_info.py:455`) returns the `version` of the bundle manifest
  it runs from, and the source manifest says `"0.1"`; only installed copies are stamped by the sync (the Claude cache holds
  `0.1.1986` to `0.1.1989`). So the value is `0.1` whenever the executor resolves the script to the main checkout, not a
  truncation bug. Open: which copy a runbook run executes. Original note: confirm under OpenCode first: if `runtime-info` truncates the bundle version, PLAN-LB-84's
  `plugin_version` bullet (source-manifest version) must cover it and its test must pin a three-part value. Retire when
  a runbook landing's `plugin_version` equals the installed bundle version.
- **OUT OF SCOPE since 2026-10-23 (token usage; see Decisions) — the runbook landing's `complete: false` on `total_tokens` is now the only missing key (PLAN-LB-85 landing,
  2026-10-23; recurrence of the PLAN-LB-86 D2 contract collision, not a new defect).** `effort` and `plugin_version`
  are supplied under the post-sync lane text, so PLAN-LB-78 D3's fix reached the run. `surface_delta` measured:
  `expansion_detected` (2 added, 3 missing). The store holds the total the lane wrote as `unknown` (2,099,576 input+output,
  $1.0042): the fourth runbook landing to hide a measurable figure.
- **RETIRED 2026-10-23 (PLAN-LB-88 shipped #1840; the cross-product rows are in the PR's tests and CI is green; residual
  boundaries accepted, see `landings/PLAN-LB-88.md`).** **The R5 enforcement merged by PLAN-LB-79 is still walkable, and the hook it made binding refuses a command
  the repository prescribes (PLAN-LB-79 landing, 2026-10-22; high; fix-forward PLAN-LB-88).** By code reading,
  not executed: the spliced-string walk splits on `; & | newline` only, so a grouping keyword, `-o pipefail` before
  `-c`, a here-string, a script file or `fish`/`csh`/`tcsh` hide the interpreter, and a `cd` inside the string is
  never applied, so `zsh -c "cd /tmp/x; python3 .plan/execute-script.py …"` is admitted on both harnesses; the
  missing-table fail-closed branch checks raw tokens and misses a spliced interpreter; the hook's R4 refuses
  every `./pw`, `./pw generate` included (CLAUDE.md prescribes it); the `git grep` decision the spec asked for was
  never made. The merged hook is also not installed on Claude here (no cached hook references the new table,
  `.claude/settings.local.json` has no `claude_pretooluse` entry); `.opencode/plugin/guard.js` is live for OpenCode
  sessions in this checkout. The self-review found one of these and rated it MEDIUM. Third completion in a chain
  (LB-65, LB-68, LB-79): PLAN-LB-88 D1 asks for a generated cross-product so the next wrapper is covered by
  construction. Retire when PLAN-LB-88 ships and its cross-product rows are green on both harnesses.
- **A second runbook landing's rule-check self-report is contradicted by its transcript (PLAN-LB-79 landing,
  2026-10-22; medium; owners PLAN-LB-73 D4, PLAN-LB-69 D3, PLAN-LB-89).** The Watch on the PLAN-LB-78 instance named
  this trigger. PLAN-LB-79 reported three refusals "for this run's sessions" (one belongs to the PLAN-LB-49 run) and
  "all other rules kept" over 67 read-class shell calls, a clone, a hand-run executor generation, hand-written CI
  bodies and a killed-and-retried self-review round, and its operator question rested on a misread executor. The
  deliverable the Watch asked for is a rule-check count taken from the transcript and attributed by session tree:
  PLAN-LB-73 D4 §8 (extended in this drain), PLAN-LB-69 D3 (six instances added), PLAN-LB-89 (the improvised
  recipes). Retire when two consecutive runbook landings' self-reports match their transcripts.
- **A lifecycle landing whose facts fence has a space after the backticks is read as carrying no facts
  (PLAN-LB-49 landing, 2026-10-22; medium; fix-forward PLAN-LB-84 D6).** `lb-49-opencode-measurement-006` wrote
  "``` landing-facts"; `_LANDING_FENCE_RE` (`_orchestrator_inbox.py` L1494-1497) requires "```landing-facts", and
  `landing-check` returned `complete: false` with all thirteen required keys missing for a block that carries them.
  Cause: `emit-landing.md` L275 describes the opening as "a ` landing-facts ` info-string fence" (padded backticks),
  and the model took the spaces literally; CommonMark permits them, so the parser is also stricter than the format.
  The facts were read by eye for this drain (`total_tokens` 16,614,516, `plugin_version` 0.1.1983, `harness` opencode,
  `model` deepseek-v4.1-flash, `effort` level-5, all 21 steps `executed`); the machine check saw none. One instance.
  Retire when PLAN-LB-84 D6 ships and a landing with a padded fence reads `complete: true`.
- **Every runbook-lane landing is now `complete: false` on `effort` and `plugin_version` (PLAN-LB-45 landing,
  2026-10-20; high; fix-forward PLAN-LB-78 D3).** #1802 made `harness`, `model`, `effort` and `plugin_version`
  required, sentinel-rejecting landing keys and changed nothing in the runbook lane: the section 8 fence
  (`runbook-lane/SKILL.md` L490-503) writes no `effort` or `plugin_version`, `resolve` returns `harness` only,
  and `landing-payload-spec.md` L128-130 says the opposite. PLAN-LB-77's landing will arrive incomplete for
  this reason; record it as this defect's recurrence, not a new one. **Recurrence 1 (PLAN-LB-77, 2026-10-20):**
  `inbox landing-check` reports `complete: false`, `missing_keys` = `total_tokens`, `effort`,
  `plugin_version`; the model fact also lacks the variant (the database says `high`). **Recurrence 2
  (PLAN-LB-48, 2026-10-21):** `inbox landing-check` reports the same three `missing_keys`; the model fact
  again lacks the variant and `total_tokens` is `unknown` for a run that measured 2.87M input and $1.30.
  **Recurrence 3 (PLAN-LB-81, 2026-10-21):** the same three `missing_keys`; `total_tokens` unknown against 3.09M
  input and $1.06. Irony: the plan that made the stamp complete cannot stamp its own landing, because the
  runbook lane has no `status.json` and never calls `refresh-runtime-stamp`. Retire with PLAN-LB-78.
  **Retired 2026-10-22 by PLAN-LB-78 D3 (#1834, `9a23d41e9`); residue open.** `plugin_version` now lands
  (as the unstamped `0.1`, PLAN-LB-84 D3), and `effort` now lands when the tree ran one variant. Recurrence 4
  (PLAN-LB-78): `missing_keys` = `total_tokens`, `effort`, because the tree ran two variants and `unknown` is
  rejected at every key, so a mixed-variant landing can never be complete (PLAN-LB-84 D2); on Claude and
  Antigravity model and effort stay `unknown` (PLAN-LB-73 D4, an operator ruling on self-report); the lane's
  landing-time re-read bypasses `refresh-runtime-stamp` (PLAN-LB-84 Dependencies). `total_tokens` is PLAN-LB-49's.
  **Recurrence 5 (PLAN-LB-79, 2026-10-22):** `missing_keys` = `total_tokens`, `effort`, `plugin_version`. Not a
  regression of #1834: the run loaded the pre-#1834 lane text once at 17:34Z on 10-21 and never re-read it in 19 h
  40 min (#1834 merged 06:44Z on 10-22), so its `resolve` could not return the keys. `total_tokens` is `unknown`
  against 4.41M input, 0.24M output, 0.25M reasoning, 269M cache read and $1.76 in the store; the runbook lane has no
  measured source at all, so PLAN-LB-86 D2's population rule must also say what a plan-less run sums. Reload of
  the lane text after a restart or idle gap is PLAN-LB-73 D4.
- **PLAN-LB-48 is on `main` with a permission writer that can reverse a more specific rule, a bridge that
  reports no drift for a file it rewrote, and OpenCode 1 tool names left in the OpenCode target rules
  (PLAN-LB-48 landing, 2026-10-21; medium; PLAN-LB-83).** `_move_rule_to_end` moves a requested rule past
  later, more specific rules (DF1); `to_opencode_grant` has no `shell` key (DF4); `bridge_drift` is `False`
  for a deleted-baseline stub write and for a hand-edited body, and a non-UTF-8 `CLAUDE.md` crashes setup
  (DF3, DF2); `target-rules/SKILL.md` L15, L19, L28, L34, L35 still name `bash`, `task` and the mtime check;
  and whether the emitted agent and skeleton `shell` catch-alls override a global deny is open (DF12, DF13,
  verify first in PLAN-LB-83 D5). The root `opencode.json` still carries an OpenCode 1 `permission.bash` map
  beside its list (steward, #1812): an operator decision, not a plan's. Retire each with PLAN-LB-83.
- **Retired 2026-10-21 by PLAN-LB-81 (#1832), residue owned by PLAN-LB-84 (medium):** the variant is stamped,
  effort is measured on OpenCode, the stamp refreshes at landing, a failed preflight clears the old stamp,
  `metadata_stamped: false` is reported and the reader honours `XDG_DATA_HOME` and percent-encodes its URI.
  Left open, each with its own deliverable in PLAN-LB-84: the provenance the refresh records never reaches
  the landing (DF1), the refresh measures the landing process's session and replaces the stamp wholesale (DF2),
  an environment model overwrites the reported one on a non-measuring harness (DF3), an Antigravity install
  now stamps `0.1.0` as the bundle version (DF4), and about half of the new tests cannot fail for the reason
  they name. Original entry kept below as the record.
- **The stamp PLAN-LB-45 shipped drops the measured variant, is taken once at plan start, and survives a
  failed preflight from an earlier run (PLAN-LB-45 landing; medium; PLAN-LB-81).** `_PREFLIGHT_METADATA_FIELDS`
  omits `variant`; `effort` on OpenCode is the model's self-report; `cmd_preflight` returns before the stamp
  clearing on a collector failure; `phase-1-init` is silent on `metadata_stamped: false`; the database read
  is unencoded, unbounded and ignores `XDG_DATA_HOME`. The OpenCode 2 detection signal shipped with PLAN-LB-48
  D4 (#1830: `OPENCODE` is the only ambient signal; the run's own `resolve` reported `harness: opencode`).
  Retire with PLAN-LB-81.
- **PLAN-LB-70 is on `main` with two unhandled Major CodeRabbit findings (2026-10-19; high;
  fix-forward PLAN-LB-74 D1).** (1) `review_support.py` ignores `worktree_unresolved` even when the plan
  declares a worktree, so a code review can report `may_close: true` without grading the branch's
  test changes (thread `PRRT_kwDOQ3xasM6uAyYk`, unresolved at merge); (2) a failed snapshot-digest
  record leaves a frozen snapshot with no outside-the-file binding (`_criteria_snapshot.py:588-595`,
  outside-diff, never handled).
- **The criteria gate can release an unmet criterion and can be bypassed (PLAN-LB-70 landing; high;
  PLAN-LB-74 D2, D3, D4).** The positional fallback in `_graded_status` answers a criterion with
  the wrong verdict row; `record_integrity` writes `status.json` without the status writer's lock;
  `manage-status metadata --set` can wipe `criteria_integrity` or append an override head; a
  `.plan/../` citation escapes the graded-head rule.
- **PLAN-LB-70 mechanisms that never reach production (medium; PLAN-LB-75).** The triage source is
  not drop-aware, `criteria_gate` is not persisted, `criteria-refreeze-authorize` is wired into no
  workflow, `worktree_unresolved` hides every plan without a worktree, per-function matching misses
  class methods and delete-and-compensate moves, and `triage.md` and `review-rubric.md` contradict the
  code.
- **RETIRED 2026-10-23 (the PLAN-LB-73 landing, #1843: §7's question step now re-reads `ci pr comments`,
  `ci pr reviews` and the marker-bearing summary comment in the same step and again before the enqueue, and a
  late review of the current head invalidates the answer).** **A merge-gate question stated that a head had not
  been reviewed 64 seconds after its review landed (PLAN-LB-70 run; operator authorization obtained on a false
  premise).** Folded into PLAN-LB-73 D1. The operator's selection is treated as no authorization for that merge.
- **RETIRED 2026-10-23 (the PLAN-LB-73 landing, #1843: §7 now counts a reviewer's marker-bearing summary comment
  — `final_review_risk_coverage` with `sourceCommitId` / `coveredCommitId` / `kind=reviewed` — as a qualifying
  review for a quota-limited reviewer, and keeps the current-head rule for the others). The retirement is
  demonstrated on this very landing: PLAN-LB-73's standing authorization rests on exactly such a summary
  marker on `39701dea8`.** **The runbook lane's §7 "qualifying review" cannot be satisfied by a clean CodeRabbit
  review (PLAN-LB-72 landing, 2026-10-19; low; fix-forward PLAN-LB-73 D1).** §7 excluded a summary comment,
  while CodeRabbit publishes a clean review only as a marker-bearing summary comment. The standing
  authorization therefore keyed on reviews that had findings, and `ci pr reviews` was empty on #1819
  although both bots reviewed the merge head. The run asked the operator a question the contract does
  not define (91 minutes). The main condition ("reviewed the current head") held.
- **Done-whens unmeetable by construction (PLAN-LB-72 landing; orchestrator-side).** A preservation or
  coverage clause carried "fails at {sha}", so the run reported two Done-whens "not met as written".
  Folded into PLAN-LB-69 D4 as an authoring rule ("fails at" for new behaviour, "holds at" otherwise).
  The spec also named the wrong path for the glob helper (`manage-architecture`, not `script-shared`).
  **Second instance (PLAN-LB-92 landing, 2026-10-24):** D2's "a script the branch adds is stale before the verb, and
  resolves after it" names a state the product's own resolution path makes unreachable — the executor's tree-walking legs
  resolve an added script before the refresh is consulted, on every target. The run reported it as not met instead of
  reworking the clause, which is the correct conduct; the authoring lesson is that a Done-when may not assume a defect
  is still observable once an earlier leg of the same pipeline can satisfy the call. Feeds PLAN-LB-69 D4, no new entry.
- **The classifier's architecture fallback can still say `docs-only` for a path a reusable CI workflow
  would build (`docs/x.asciidoc`; PLAN-LB-72 landing).** Only the local build is skipped and the PR's
  CI backstops it. Operator ruling wanted: accept, or fail closed (which defeats the docs-only path in
  this repository, whose rule lives in a reusable workflow).
- **Undisclosed rule breaks of the PLAN-LB-72 run:** `git config --get-regexp .` (dumps user and global
  git config), the unknown verb `ci bot completion` neither asked about nor recorded (§4), a third
  `tail`, three argparse rejections, two rejected sub-agent shell attempts, a sub-agent read outside
  the repo, and no base re-fetch before the enqueue. The guard does not cover read-side probes by
  design, so none was logged.
- **Fail-first is reported, not checkable (PLAN-LB-67 and PLAN-LB-71 landings; operator ruling
  wanted).** Two runs in a row labelled mutation or revert evidence "fail-first"; PLAN-LB-71 put
  "each observed failing before the fix" into the PR body and `main`'s squash message with 0 of 15
  Done-whens test-first. PLAN-LB-72 D3 makes the label structured (`order`: `test-first` /
  `mutation-after` / `none`); the full-depth audit (PLAN-LB-69) is the only check. Decide whether a
  lane verb should record the failing run's output and commit before the fix commit.
- **The main executor does not know `build-classify` (2026-10-19).** `.plan/execute-script.py`
  lists only the `resolve` child for the lane (digest `2caadbf…`); the installed OpenCode lane text
  is still pre-PLAN-LB-67. Operator action: regenerate the executor (`marshall-steward`), then
  `/sync-harnesses`. **Recurrence 2 (PLAN-LB-73 landing, 2026-10-23) — REPORTED, THEN CONTRADICTED:**
  the landing's Residue says `executor-skew` and `build-routing` "are not in any deployed executor's
  surface cache yet" and that invoking either "still answers `unknown_verb`". Re-checked at analysis on
  this machine, both resolve: `runbook_lane executor-skew --help` and `runbook_lane build-routing --help`
  return their real argument surfaces. So the claim was already stale when the landing was drained — the
  executor was regenerated or recovered the subcommand in between — and it is **not** an open defect.
  The genuine half of the observation stands and is what PLAN-LB-92 owns: a runbook worktree carries no
  executor at all, which is why every one of this run's builds answered `executor_absent_from_worktree`.
- **FIXED IN SOURCE 2026-10-19 (PLAN-LB-71 D1, #1817; deployed after the sync above).** The runbook
  lane's skill-existence check fails closed in a flat install (PLAN-LB-67 landing,
  2026-10-18; high). `runbook_lane.py:167-202` resolves a bare name and
  a persona with its bundle dropped against the lane's own `skills/` directory. The OpenCode install
  names skills `plan-marshall-{skill}`, so every name misses and a spec with `Skills:` lines stops
  on `named_skill_not_found`. Until PLAN-LB-71 D1 lands, do not sync the OpenCode install and then
  emit a spec carrying those lines. The `total_tokens=unknown` gap of this landing recurs on the
  PLAN-LB-49 entry (third OpenCode runbook landing with `unknown`); `landing-check` reports the
  landing `complete: false` on that one key.
- **Report integrity of the PLAN-LB-67 landing.** About nine claims were contradicted: personas and
  domain skills "applied" with none loaded, "no shell file operation again" (two), "base branch
  merged rather than rebased", fail-first for all six deliverables (D5 and D6 were tested after the
  implementation), Finding 7 "fixed in both places", and an undisclosed local history rewrite. The
  landing audit is the only check on this; PLAN-LB-69 makes it mandatory and repeatable.

- **The two-pass cuioss-review-bot has unverified and unprevented gaps (inbox
  `lb-37-functional-review-012` items 8 to 10, 2026-10-14; foreign repositories, not owned).**
  (8) The 65,000-character comment cap is documented in cuioss-review-bot
  `doc/consumer-guide.adoc` as PR-Agent's truncation, but not verified in the pinned image and
  not mentioned in cuioss-organization #326 — verify or remove the claim. (9) `/improve` has no
  fail-closed oracle, and both `/review` passes are still last-write-wins on overlapping
  comment-triggered runs (detected by the content-match gate, not prevented). (10)
  `/review -i` now fails the `review / code-review` job by design; operator decision whether
  maintainers need specific harmless options allowed. Next step: a plan in
  `cuioss/cuioss-review-bot` / `cuioss/cuioss-organization`, or an operator ruling per item.

- **Antigravity: critical, by operator ruling of 2026-10-12 (the epic's highest priority).**
  All from pm-mcp-core PLAN-41 (pm-mcp-core PR #34), the first plan of that epic run under
  Antigravity; the ingest verified against the archived plan, not at HEAD here unless noted.
  All five were owned by PLAN-LB-39, which shipped (#1768) without closing them: no native
  dispatch, a content-free rules bridge, no per-task gate, no criteria snapshot, the head-vs-gate
  refusal in prose only (`landings/PLAN-LB-39.md`). **Re-owned 2026-10-15:** dispatch, standing
  rules and the per-task gate by PLAN-LB-51; criteria integrity, the pushed/merged-head gates and
  the phase-boundary guard by PLAN-LB-52; the `unknown` token rule shipped. Full bodies at
  `lessons-routing/lessons-archive/filed-live-blockers/`.
  - **Phase 5 dispatches no sub-agent.** `Task: plan-marshall:execution-context-{level}` has no
    meaning on Antigravity and `phase-5-execute` has no wiring to its `invoke_subagent` (nor to
    OpenCode's sub-agents); all 8 tasks ran inline in one session, phase boundaries were left
    open, no dispatch-boundary row was written. — `lessons-routing-011.md`.
  - **The repository's `CLAUDE.md` is never loaded**, because Antigravity reads only `GEMINI.md`,
    `AGENTS.md` and `.agents/rules/*.md`; with it the build rules and prohibitions vanished.
    Task verification also carried no quality gate although the manifest stamped it per task.
    One symptom: with `CLAUDE.md` unread the agent guessed a formatter, retried
    `spotless:apply` fully qualified after `No plugin found for prefix 'spotless'`, and Maven
    fetched the plugin from Central. Asked for, besides the `CLAUDE.md` bridge and the
    quality-gate synthesis: one agent rule in the base persona and the Antigravity target
    rules — an unresolvable plugin prefix means the project does not use that plugin; stop,
    never retry it fully qualified. — `lessons-routing-012.md` (revision 1).
  - **Zero tokens is recorded as a real number and no plan records its harness**: every
    `record-step` reads `unmeasured`, the landing carries `total_tokens=0` and passes
    `landing-check`; no archived plan has a `client.toon`, because nothing on the start path
    calls `orchestrator preflight`. — `lessons-routing-013.md`. Meets the Watch below.
    Recurred under **opencode** (PLAN-44): `total_tokens=0`, wall time covers 1-init only, no
    `client.toon`; the five finalize builds' logs are missing from the archived
    `build-results/`, so the gates on the pushed head cannot be shown (bears on `-016`).
    — `lessons-routing-028.md` (148). **Recurred on PLAN-LB-26 under OpenCode** (#1769):
    `total_tokens=0` although `~/.local/share/opencode/opencode.db` `session_v2` holds the real
    usage (main session 42.58M input / 165K output, $4.93; resumed 2.14M / 25.6K, $0.31; 77
    sub-agent sessions). No OpenCode token source is implemented at all — see § Non-Claude-Code
    Failures.
  - **Not a defect: `build-maven maven run` accepting any plugin goal** (operator ruling
    2026-10-12). The wrapper is a deliberate pass-through; a goal guard would cost a POM
    evaluation per call and refuse ordinary undeclared goals (`dependency:tree`,
    `help:effective-pom`, `versions:*`), and restricting plugin repositories is the project's
    own `.mvn` configuration. The incident is a symptom of the unread `CLAUDE.md` above.
    `lessons-routing-014.md` is superseded by `-012`.
  - **A materially incomplete package was reported complete, with existing tests weakened to stay
    green** (`deliverables_done=7/7`; an independent audit found rules partial, dead or missing,
    a coverage test counting enum constants, an assertion filtered and a fixture changed to
    dodge a rule). Nothing in the pipeline caught it on any harness. PLAN-LB-37's functional
    review, which verifies each success criterion against evidence, is the nearest remedy;
    whether it catches a weakened existing test is not established. — `lessons-routing-015.md`.
    **Recurred under opencode** (pm-mcp-core PLAN-44, PR #38, `6caa663`; operator grade
    critical as the recurrence, high for the new mechanisms): `deliverables_done=6/6` against a
    7-deliverable spec, with D2, D4, D6 and D7 unmet and one new test weakening. New mechanisms,
    none owned: (1) the plan rewrote its own package What/Done-When and ADRs 002–005 to describe
    the shipped code; (2) an ADR contradicts the specification (Workflow DSL Rule 6) with no spec
    PR, and a test-catalog entry was reshaped to stay green; (3) an infeasibility verdict was
    checked against the as-built code and the specified check was then deleted under the
    verify-first "drop a refuted gap" clause — an infeasibility verdict must name the work-order
    sentence and deleting a specified check needs an operator decision; (4) task statuses and
    green builds stood in for the Done-When (no coverage table, a "done" fix task changed no
    code); (5) pre-push review read shape only and finalize triage was bot-bounded, so the loop
    exited on an empty bot queue with Done-When criteria open — asked: the Done-When as a
    standing finalize triage source. Checked at PLAN-LB-37's landing: its functional review
    catches neither a rewritten criterion nor a weakened test — it grades the outline's current
    criteria (`functional-review.md:210-215, 298`) without comparing them to the request, and a
    test identifier counts as evidence (`review-rubric.md:66`). Owned by PLAN-LB-39 D6. Evidence
    of the incident rests on the sender's audit, not re-checked here. — `lessons-routing-026.md`.
  - **The pushed and merged head carries none of the plan's mandated gates** — the Antigravity
    instance, and two Claude Code recurrences where fix commits after the last full gate were
    pushed with only the composed manifest steps re-run. Graded high for Claude Code.
    — `lessons-routing-016.md`. **Recurred on PLAN-LB-26 under OpenCode** (#1769): functional
    review, code review, pre-push gate, ci-verify and automatic-review are stamped
    `head_at_completion=3db65fc05`; four commits followed and `74e6bfda` was merged. Cause: a
    provider crash killed the session mid functional-review (round never closed), and the
    resumed session went straight to push and branch-cleanup. Nothing forces a head-dependent
    step to re-fire when the merge head differs from its `head_at_completion`, the merge barrier
    does not check those steps' head binding, and an abandoned review round leaves no pending
    marker. Owned by PLAN-LB-52 (re-staged from PLAN-LB-39). **Recurred on PLAN-LB-39 itself**:
    an ungated rebase + `force-push-with-lease` at 2026-10-14T16:29, CI red on that head.
- **A deliverable in a sibling repository has no lifecycle** (high; critical in its Antigravity
  instance): no plan-owned worktree, no finalize step pushes it or opens its PR, the footprint
  ignores it, and the foreign-PR gate assumes `feature/{plan_id}`
  (`phase-6-finalize/scripts/foreign_pr_gate.py:170-171`), so it both blocks a merged foreign PR
  and misses a missing one. Recurs on every pm-mcp-core plan that changes a specification. Not
  owned by any staged plan. — `lessons-routing-018.md`. Two more plans (PLAN-13, PLAN-18): the
  retrospective footprint reports every sibling path as declared-but-unrealised, so M6 fails by
  construction; relative sibling paths break under `use_worktree`; a sibling deliverable has no
  module name in the architecture. — `lessons-routing-028.md` (168, 175, 176, 181).
  Recurred 2026-10-13..15 on pm-mcp-core (-203, -213, -240, -265, -285; `lessons-routing-029`);
  live at `d17ac5bef` (no cross-repo field in the deliverable template, no per-path cross-repo
  footprint bucket; PLAN-LB-27 retired). Still unowned by the earlier "structural" ruling.
- **A required review bot goes stale after a fix commit** (remainder after #1742 and #1752):
  a commit pushed after the last review by any path (inline finalize fix, merge-queue flow
  without a local rebase) does not re-arm the re-review; a leaf read `re_review_on_loopback`
  from the wrong source; a bot whose path filter excludes the whole diff is not counted as
  expected-absent. The "fixed before the fix exists" item is closed by #1742/#1752. Not owned by
  any staged plan. — `lessons-routing-017.md`.
- **CodeRabbit concerns raised only in its summary/walkthrough comment are never filed** —
  security concerns included (high, operator ruling 2026-10-13). Verified at HEAD:
  `automatic-review/standards/coderabbit.md:60-61` list the summary marker and `## Walkthrough`
  as `ignore_patterns`, line 127 calls them whole-comment drops "that carry no per-line
  finding", and `github_pr.py` (`_is_obvious_noise`, line 407) counts them into
  `count_skipped_noise` only; nothing reads the summary body for actionable, "Outside diff
  range" or security items. Seen on pm-mcp-core PLAN-18, PR #43. Asked: parse the summary for
  actionable and security items, or at least report a dropped summary that carried them; a
  summary-only security fixture pins it. Not owned by any staged plan; nearest PLAN-LB-31 or
  the `-017` remainder. — `lessons-routing-027.md`.
- **RETIRED 2026-10-23 (the PLAN-LB-44 landing, #1848: `verification-feedback` accepts the single `ci-verify`
  producer from one shared constant, the taxonomy row travels as a finding subtype, a failing check is classed by
  what it ran — closed policy list, build default, Sonar-marker deferral — and each finding is keyed on its own
  check's run with a log pointer or a named `log_unavailable_reason`).** **Red CI has no triage route.** `verification-feedback.md` accepts only `build-runner, sonar,
  pr-comment, plugin-doctor, pr-state, finalize-feedback` (lines 30, 59 at `47d21e1bf`), while
  `ci_verify.py` emits `ci-verify-missing/-build/-policy/-timeout/-cancelled`; every red-CI
  dispatch is refused `unknown_producer`. Five plans (PLAN-LB-25 and four pm-mcp-core plans);
  also a CI check is classed by name tokens, not by what it runs. Lesson `2026-10-11-16-001`.
  Owned by PLAN-LB-44 (staged; the label "not owned" was stale, corrected 2026-10-15).
  Recurred on API-Sheriff #466 (`lessons-routing-043`, which names the landed PLAN-LB-24); accept-set
  unchanged at `d17ac5bef` (`verification-feedback.md` L30, L63-72).
  — `lessons-routing-019.md`, `lb-25-phase-and-merge-gates-001`.
  Recurrences: PLAN-13 (`ci-verify-policy` refused `unknown_producer`, re-dispatched as
  `finalize-feedback`); lesson `2026-10-11-07-001` (plan-06) — a SonarCloud gate failure inside
  the `build / sonar-build` Maven job filed 5 `ci_policy_failure` findings instead of deferring
  to sonar-roundtrip. — `lessons-routing-028.md` (153, 189). Recurred on PLAN-LB-42 (2026-10-14
  18:31): a CI-wait lapse was dispatched as `ci-verify-timeout` and refused `unknown producer`; all
  four `ci_timeout` findings were titled "verify failed" while verify was still running
  (`plan-lb-42-outline-qgate-integrity-001`). Recurred on PLAN-LB-49 (2026-10-22): the bounded CI wait lapsed at
  head `a8252f57` and two duplicate "[ci_timeout] verify / verify failed" findings were filed, both resolved
  "Superseded: CI completed green" (`artifacts/findings/triage.jsonl:1-2`). The duplicate filing is itself a smell.
  Folded under PLAN-LB-44 (staged) with no surface added. — `lb-49-opencode-measurement-001.md`.
- **The guard has no rule for shell file operations or ad-hoc scripts** (2026-10-15, PLAN-LB-42
  landing). Under OpenCode with the deny rules active, R1 (compound shell) and R4 (raw pytest)
  refused all 8 attempts. `ls` (2), `python3 -m py_compile` (3) and a `.plan/temp/*.py` ad-hoc
  script passed. CLAUDE.md forbids shell file operations, but no R-rule enforces the ban.
  HYPOTHESIS: the same gap exists under Claude Code's PreToolUse hook. Owned by PLAN-LB-56
  (2026-10-15). Correction: `ls`, `grep`, `head` and `python3` passed the global deny because of
  the 8 persisted OpenCode "always allow" approvals of 2026-10-08 (still owed by the operator);
  read-side probes are governed by the permission map, not the guard (`guard.js:28-32`).
  PLAN-LB-56 adds R5 for interpreter calls and reports stale approvals. **Shipped partly (#1781):** R5 refuses `-c` / `-m` / script paths, but has
  no plan-context gate on OpenCode, misses wrapper prefixes, and blocks documented workflows;
  `git grep` and `ls` are still uncovered. Remainder owned by PLAN-LB-62.
  PLAN-LB-40 (second guarded run): 92 `python3 -c`, 18 `git grep` (not in PLAN-LB-56's scope),
  17 ad-hoc script runs, three harness-written-after-R4-refusal evasions.
- **In a consumer repository a dispatched leaf cannot resolve its workflow document**:
  `agents/execution-context.md:111-112` maps a notation only to `marketplace/bundles/…`
  (`workflow_not_found` otherwise, line 119), so every consumer-repository dispatch improvises,
  some reading a stale built copy. Graded high. Not owned by any staged plan.
  — `lessons-routing-021.md`. Recurred on PLAN-18: the 4-plan leaf and two sonar-roundtrip
  leaves read the doc from the plan-marshall checkout's `target/claude/` instead.
  — `lessons-routing-028.md` (182).
- **The deep-lane outline writes no assessments**, so Q-Gate check 2.2 fails every deliverable
  — one guaranteed operator interruption per deep-lane plan (eight pm-mcp-core plans). Graded
  high by the operator. Not owned by any staged plan. — `lessons-routing-022.md`. Ninth to
  eleventh plans: PLAN-13 (Q-Gate 447991), PLAN-18 (0feabd, accepted by the operator), PLAN-54
  (affb5d, assessments added after the gate asked). — `lessons-routing-028.md` (162, 174, 191).
  Twelfth: PLAN-LB-26 (finding 037a63 pending across the 3-outline and 4-plan exits, waved
  through in phase 5). **Partly fixed by PLAN-LB-42 (#1773):** an empty store now reports "not
  run" instead of failing. Six more recurrences (pm-mcp-core -212..-274, `lessons-routing-032`) all
  predate #1773. Residue at `d17ac5bef`: the only component-analysis implementor is
  `pm-plugin-development:ext-outline-workflow`, so a Java or generic deep-lane plan never establishes
  coverage — it is reported "not run", no longer a false failure. Residue owned by PLAN-LB-54 D2: the outline skill is missing from the
  return, and the hash cache is switched off for an empty store.
- **The 4-plan Q-Gate skips its validators on the 3-outline hash and reports a pass over zero
  runs**; no verb computes the deliverable hashes, so passes improvise. Graded high by the
  operator. Not owned by any staged plan. — `lessons-routing-023.md`. Recurred on PLAN-18: both
  Q-Gate runs skipped `deliverable-hashes.toon` (16 hashes over 2 runs); the 4-plan leaf had no
  shell. Asks for a `manage-solution-outline deliverable-hashes` verb.
  — `lessons-routing-028.md` (185). **Partly fixed by PLAN-LB-42 (#1773):**
  - the skip is phase-keyed in prose;
  - a cached skip reads "not run";
  - the verb exists but persists nothing, and no test executes the skip rule.

  Residue owned by PLAN-LB-54 D1. Recurred on pm-mcp-core (-225, -283; `lessons-routing-033`),
  both before #1773; "no hash verb" is stale at `d17ac5bef`, the hand-written artifact is not.
- **A local-only run can still schedule push-related steps.** With
  `phase-5-execute.commit_and_push` false the commit-push filter drops `pre-push-quality-gate`,
  `functional-review` and `code-review`, and the ceremony selection adds them back for a
  `lane: minimal` gate without consulting `commit_and_push` (`_manifest_rules.py`,
  `_apply_ceremony_finalize_selection`). Predates PLAN-LB-37. **Operator decision needed:**
  whether a `minimal` lane overrides "no push", possibly per step class (a review step may keep
  value in a local-only run, a pre-push gate does not). — `lb-37-functional-review-003.md`.
- **Free-text placeholders in workflow command templates are not shell-quoted**: finding titles,
  reasons and refs interpolated into double-quoted arguments break the command or run
  `$(...)`. PLAN-LB-37 fixed `functional-review.md` and `code-review.md`; `triage.md`,
  `verification-feedback.md` and the remaining `phase-6-finalize` documents are left — confirmed
  at `7f35dca9a`, e.g. `workflow/create-pr.md:182, 292`, `workflow/adr-propose.md:115`,
  `workflow/lessons-capture.md:170`, `standards/push.md:168`. Lesson `2026-10-13-07-002`. Not
  owned by any staged plan. — `lb-37-functional-review-004.md`.
- **From PLAN-LB-37's landing** (`landings/PLAN-LB-37.md`), none owned by a staged plan:
  - **A required bot's size refusal loops instead of escalating**, and trigger-B reads
    staleness from another PR's findings: the structural-refusal branch is keyed on the
    rate-limit list, CodeRabbit's `refusal_patterns` miss "files exceed the limit", and the
    selector has no `pr_number` filter. Lesson `2026-10-13-14-003`. Pairs with lesson `-14-001`
    (check size caps before `create-pr`). Nearest owner PLAN-LB-31.
  - **The footprint of a stacked landing is the last PR only**, so the retrospective reports
    confident low recall. Lesson `2026-10-13-14-002`.
  - **Finalize re-fires leave no execution-log or dispatch-boundary rows.** Lesson
    `2026-10-13-14-004`.
  - **`manage-logging` `work`/`decision` now exit 1 on a write failure** (`manage-logging.py:197-220`,
    since #1759), against the plugin rule of exit 0 with `status: error`
    (`plugin-architecture/SKILL.md:159`); a caller that treats a non-zero exit as fatal halts on
    a log-write failure. Low.
  - **D13 partial**: neither review step's own tests read `review-rubric.md`. Low.
  - **The plugin-cache sync does not prune**: the installed cache still lists the retired
    `pm-plugin-development:ext-self-review-plan-marshall`. Low.
- **From PLAN-LB-26's landing** (`landings/PLAN-LB-26.md`, 2026-10-14):
  - **Regressions N1–N4 shipped in #1769** — owned by PLAN-LB-47 (running).
  - **The review barrier counts a current-head quota refusal as participation** — owned by
    PLAN-LB-55 D3 (re-checked live at `8442a5e33`: `classify_bot` checks participation first).
  - Dropped 2026-10-15 as medium/low (`settled.md` § "Dropped 2026-10-15"): compile auto-close
    residue, metrics re-entry accounting, landing-fact ordering, the plan-session ledger write, the
    `build-server wait` log repetition, tier-1 `--request-text`.

- **From PLAN-LB-31's landing** (`landings/PLAN-LB-31.md`, 2026-10-14):
  - **Enrolment (D6, D7) and a durable measurement instrument** — owned by PLAN-LB-57 (moved out of
    PLAN-LB-48 on 2026-10-15). The efficacy-doc and registry corrections were dropped as medium.
    The CodeRabbit Learning stays by operator decision.
  - **The functional review never checks "Done when" outcome counts** — owned by PLAN-LB-52 (D1
    snapshot, D2 Done-when as a triage source).
  - Dropped 2026-10-15 as medium/low: no route from task content into the PR body, drift recovery
    manufacturing its own loop cap, the OpenCode-blind direct-`gh` audit, the in-house review job
    skipping PRs (cause unverified), `ci pr reply --repo` as a standalone item (it rides PLAN-LB-57
    D1).

- **From the lessons ingest of 2026-10-15** (`lessons-routing-029`..`-043`; pm-mcp-core
  `-203`..`-286`, API-Sheriff #466). Re-checked read-only at `d17ac5bef`; the operator's gradings at
  that ingest stand over the re-check's.
  - **High — staged 2026-10-15 by operator instruction:** PLAN-LB-58 verification-truth (Sonar
    staleness D1, link check D2, Maven gate population D3) and PLAN-LB-59 skill-and-adr-resolution
    (module-aware skills D1, ADR scan D2); both queue after the OpenCode plans.
    - **Sonar confirms a stale analysis** (`-037`, pm-mcp-core `-253`): `count_status` is decided by
      CE readiness alone (`workflow-integration-sonar/scripts/sonar.py` L26-33); no script compares
      the analysis revision with the PR head, so a clean stale analysis reads as a confirmed 0.
      Fail-open. → PLAN-LB-58 D1.
    - **Task skill resolution attaches framework skills the module forbids** (`-039`, operator-graded
      high): `manage_personas.py` `_resolve_profile_domain_skills` merges `defaults` AND `optionals`
      (L150) with no module context, so every Java task gets `java-quarkus`, `java-cdi`,
      `junit-weld-testing`; the module-level demotion in `pm-dev-java/.../extension.py` L178-185 is
      bypassed. → PLAN-LB-59 D1.
    - **The Markdown link check passes on zero links** (`-037`, operator graded pm-mcp-core `-247`
      high): `pm-documents` `_cmd_verify_links.py` file mode accepts a `.md` and parses it with
      AsciiDoc regexes (L70-106, L185-186) — `total_links: 0, status: success`; directory mode
      already refuses. The verification-scope half of `-247` was caught by the Q-Gate as designed.
      → PLAN-LB-58 D2.
    - **Pre-push gate has no per-module population on Maven** (`-031`, operator graded `-267` high):
      `derive_gate_bundles.py` is marketplace-shaped (L127-139) and only `build-pyproject` exposes
      `resolve-test-scope`, so module-tests runs DEGRADED on every Maven plan. Disclosed, not silent:
      rule 4 reports the unresolved paths and the whole-tree arms run. → PLAN-LB-58 D3.
    - **Per-package ADR numbers collide** (`-036`, operator graded `-252` high): `manage-adr.py`
      `ADR_DIR = Path('doc/adr')` (L29) with non-recursive globs (L129, L139, L163); `doc/adr/{package}/`
      is invisible to numbering and the scan. → PLAN-LB-59 D2.
  - **Graded high by the ingest, medium on re-check** (no false pass, caught by an existing gate, or
    one plan shape):
    - Sourcery's "used its review budget" notice is not a registered refusal (`-030`; `sourcery.md`
      L46 registers "used your own review budget of", case-sensitive substring at `_github_pr.py`
      L308). Data-only fix; Sourcery is optional.
    - Staged premises are not re-checked against sibling landings when no file overlaps (`-035`;
      `finalize-step-sync-baseline.md` L107-128).
    - Leaf phase skills self-transition before the orchestrator's Q-Gate (`-038`;
      `phase-3-outline/SKILL.md` L694-700 vs `planning-outline.md` L217, L264-267); the gate still
      runs. Nearest PLAN-LB-55 D2.
    - Outline assessments miss files and outlive a refuted design (`-040`); § 2.2 catches each, at
      the cost of rounds.
    - No declared task deferral for diagnose-then-fix plans (`-041`).
  - **Fixed or low:** triage fix tasks under `deliverable: 0` (`-034`) fixed by #1769
    (`_tasks_core.py` L89-94, L892), error-text residue in PLAN-LB-47 D4; `worktree-remove` from a
    stale cwd (`-042`) — the in-worktree case refuses `cwd_inside_removal_target`, the observed
    failure was a redundant second call; low.

- **PLAN-LB-47 D5 is unwired (medium, not staged):** the "squash message composed explicitly" rule
  (`branch-cleanup.md:1615-1635`) has no command — `ci pr safe-merge` / `ci repo` take no message —
  and `ensure_project_trailer` (`git-workflow.py:283-299`) is called only from a test. Every
  merge-queue squash still takes the PR page body (footer, duplicate `## Intent`, CodeRabbit block,
  extra `Co-authored-by`). — `landings/PLAN-LB-47.md`.
- **Build-finding dedup can fold distinct failures** (PLAN-LB-61 D4, `c1f68bd68`, re-check before
  staging). The identity `(type, title, file)`, with the title carrying `message[:80]`
  (`_build_shared.py:343-358`), folds two distinct failures in the same file, line and category,
  even within one build. The second is `deduplicated` and counted as stored. If it lands on a
  record owned by a pending fix task, the short-circuit guard reads all-owned and the new failure is
  not triaged. A recurrence also keeps the first detection's `detail`. Frequency unverified.
  Medium-high; not staged. — `landings/PLAN-LB-61.md`.
- **The shared outline metadata parser was widened unsafely** (PLAN-LB-54, `6953df489`,
  `_plan_parsing.py:325`). The pattern `-\s*\*{0,2}(\w+)\*{0,2}:\*{0,2}\s*(.+)` leaks bold
  markers into values (`- **domain: java**` → `java**`), produces case-kept keys from bold labels,
  and no longer reads a `domain:` line after a blank line or indented. This affects every
  `extract_deliverables` caller (outline validator, qgate mechanical, review attribution,
  `foreign_pr_gate`); a dropped domain is silent when another survives. No `test_plan_parsing.py`
  case. Medium; not staged. — `landings/PLAN-LB-54.md`.
- **The clobber report misleads** (PLAN-LB-64, `24475924b`). Every project set up before the fix
  had the bridge stub written into `plan-marshall-target-rules.md` by setup itself, so it is now
  reported "clobbered" and told to "restore" rules it never had. The restore command
  `./install.sh --emit-rules` (`configure_harness.py:65`) does not exist under that name in a
  consumer project (the retained installer is `plan-marshall-install.sh`, emit lands in the cwd,
  and without `-U` it reinstalls). A stub bridge is healed silently, never reported, and
  `configure_harness` returns `status: success` when `setup_failed` is true. Medium; not staged.
  — `landings/PLAN-LB-64.md`.
- **A dead enforcement call** (`configure_harness.py:197`): `opencode_enforcement_apply` exists in
  no runtime and is skipped by `hasattr`; `doc/developer/opencode.adoc:272` says it runs. OpenCode
  enforcement (`guard.js`, the two-tier map) is installed only by wizard Step 14b, an LLM-driven
  step. Either implement the method or drop the call and the doc claim. Medium; not staged.
  — `landings/PLAN-LB-64.md`.
- **The executor import recovery is inert** (PLAN-LB-63, `b90e8a25f`). `upgrade.py`'s probe and
  `needs_recovery` only run when `upgrade plan` runs, and it runs only through the executor
  (`upgrade-flow.md:87-89`). A broken executor never reaches it, and a working one passes the
  probe. Low items alongside:
  - no re-probe after regeneration;
  - `dead_sweep: resolved` on an empty step map;
  - one unreadable doc disables the whole sweep, unnamed;
  - `dead_removed_steps` is never read;
  - the sync-defaults output contract is stale.
  **High** (operator elevated it); staged as **PLAN-LB-43 D3**, together with the re-probe and the
  overwritten warning. The other low items are not staged. — `landings/PLAN-LB-63.md`.
- **The steward is refused on OpenCode** (PLAN-LB-65, `d3e9c2544`). R5 runs in every session,
  and the wizard's resolved deployed script paths never match the repository-relative allow-list.
  There is no consumer executor recovery, and consumers lose ordinary `python3`. **High**; staged
  as PLAN-LB-68 D1. Carried high gaps: R6 misses `git -C {WORKTREE} commit`; R5 side doors
  (here-string, `exec`/`stdbuf`/`setsid`, `bash -c` and `uv run` on Claude, a suffix-matched
  executor permit). Staged as PLAN-LB-68 D2 and D3. — `landings/PLAN-LB-65.md`.
- **The runbook-lane build commands are valid only for pyproject** (PLAN-LB-66, `f54acb7a5`).
  `runbook_lane.py:192-195` passes the canonical names through as `--command-args`, which is
  invalid for Maven, npm and Gradle. **The Claude guard false positive:** any `PreToolUse` hook
  reads as `guard: present`. Low items alongside:
  - the stamp doc and docstring disagree;
  - double listing in `owed_landing`;
  - cwd-relative `resume-summary`;
  - an unknown bot gives an empty trigger;
  - CodeRabbit's unhandled worktree-epic-scoping finding (`orchestrator.py:5726`).

  Medium; not staged. — `landings/PLAN-LB-66.md`.
- **The criteria gate refuses ordinary finalizes** (PLAN-LB-52, `6286484d8`). With a snapshot and
  no verdict (functional review dropped for surgical scope, commit-push disabled, or review off),
  `open_done_when_criteria` refuses `6-finalize` completion and archive. A wrapped spec Done-when
  is captured as its first line, giving a false `spec_criterion_missing`. Also: "prefix" is read
  as "pre-fix"; authorized changes, superseded deliverables and paraphrased verdict rows are
  ignored; the seal is in-file. **High**; staged as PLAN-LB-70. — `landings/PLAN-LB-52.md`.
- **The main executor is polluted** (PLAN-LB-52 run). `.plan/execute-script.py` was generated for
  the OpenCode target, with 163 foreign `default-bundle:*` notations. Operator action: regenerate
  it for Claude.
- **Medium and low items are not owned by any staged plan.** They are listed with evidence
  in `backlog.md` (sections 1.12 onward, 2.3 onward, 3.2 onward, 4.7 onward and 5). Promote an
  item into a plan spec when it starts to hurt; re-verify it at HEAD first.
- **35 active lessons have no router of their own beyond `lessons-routing`**, which was
  dormant at the cut. The lessons that describe live defects are folded into the specs here
  and into `backlog.md`; two lessons describe defects already fixed and should be retired
  (`2026-09-27-07-001`, `2026-10-02-21-006`), and `2026-09-27-19-001` has no metadata header.
  — source: sweep of the lessons store, 2026-10-07.
- **The outline leaf has no signal for an ambiguous change type, and two documents disagree on
  the skills the detection dispatch carries.** When `change-type-heuristic` ties,
  `phase-3-outline` Step 4b prescribes a dispatch the outline leaf cannot issue; the leaf
  returns `blocked` with a free-form field and `planning-outline.md` Step 2 has no handler for
  it. PLAN-LB-22 hit this, lost one outline dispatch (about 198K tokens) and got past it with
  three moves no document prescribes. Separately, `outline-workflow-detail.md` lists one skill
  for the `detect-change-type` dispatch where the workflow's own Inputs require three. Reach:
  every deep-lane, non-recipe plan whose heuristic ties. Not owned by any staged plan; stage it
  if it recurs. — source: inbox message `lb-22-finalize-loop-control-001.md`, 2026-10-08, read
  at bundle version 0.1.1867; not verified against the source here.
- **A routed build leaves no change-ledger row for its plan, and it is not the missing plan
  id.** PLAN-LB-23 examined the hypothesis folded into its spec on 2026-10-08 and reports it
  as a separate defect it does not fix: the 84 routed builds of the PLAN-LB-14 run carried a
  real plan id (the work-log line is only written when one is present), yet the ledger held no
  `kind=build` row for the plan. Its candidate cause, reasoned from the code and not
  reproduced: the ledger path is resolved per working tree, so a row appended by a build
  running under the daemon may land in a different working tree's ledger than the one a
  reader opens. If that is right it also bears on which ledger the freshness check reads.
  Not owned by any staged plan. Next step it suggests: run one routed build for a plan in a
  worktree, then compare the ledger file that received the row with the one
  `pre-commit-verify-freshness` opens. — source: inbox message `lb-23-verify-builds-001.md`,
  2026-10-08; pointers `_build_execute_factory._append_gate_build_row`,
  `_ledger_core.resolve_ledger_path`; not verified here.
  Recurrence (PLAN-LB-49, 2026-10-22): the plan's 211 logged build calls left 4 `kind=build` rows against
  3,990 rows scanned, all four without a duration, so `total_build_seconds` read `unavailable` while
  `pyproject_build` took 62.6% of the plan's script time. Read in source: the gate route appends its row with
  `duration_seconds=None` (`_build_execute_factory.py` L536-541), the daemon route stamps one; whether the in-process
  route appends any row is a hypothesis. The duration half is owned by PLAN-LB-87 D2; the daemon-working-tree half
  above stays unowned. — `lb-49-opencode-measurement-003.md`.
  - **Read in the code on 2026-10-09 at `c9738952a`; the cause holds and PLAN-LB-23 left
    it open.** `resolve_ledger_path` resolves from the working directory, up to the nearest
    ancestor holding `.plan/local`; each plan worktree has its own
    `.plan/work/change-ledger.jsonl`. The freshness check takes the SHA from the plan's
    worktree but the ledger from its own working directory. `_append_gate_build_row` writes
    its row without a worktree SHA, so that row can never satisfy the freshness check. What
    PLAN-LB-23 changed is the other half: resolved build commands now carry `--plan-id`.
    Its routed-build test replaces the ledger path with a temp file and cannot see the
    split. Seen again on PLAN-LB-23 itself: its retrospective scanned 1272 ledger rows and
    matched none against 148 logged build calls, because the worktree holding the ledger
    had been removed. Still not reproduced by a run. — source: read-only review of
    `c9738952a`; inbox message `lb-23-verify-builds-013.md`.
- **The direct build path's signal handling has three gaps**, all in
  `script-shared/scripts/build/_build_execute.py` as shipped by PLAN-LB-23.
  `_signal_build_group` suppresses `ProcessLookupError` only, so a permission error from
  the group kill surfaces as `error`, a red build, where the daemon path reports `timeout`.
  The grace period waits on the group leader alone, so when the leader exits promptly the
  rest of the group is killed without grace. The signal handlers are installed a few
  statements after the child starts; a signal in that window kills the wrapper and leaves
  the build running with no bound. Each is narrow; none gives a wrong green. Not owned by
  any staged plan. — source: read-only review of `c9738952a`, 2026-10-09, by line; the
  third is also named in the plan's landing message.

> ↪ Relocated to `settled.md` § "Open Defects closed by PLAN-LB-33 and PLAN-LB-38" — closed by #1745 and #1752; the entries themselves said to remove them at the next cleanup, and their two open follow-ups stay as their own Open Defects.

- **Superseded 2026-10-14 — see § Non-Claude-Code Failures "OpenCode 2: no deny rule applies".**
  The new keys are OpenCode 2's own schema; the live defect is rule order and the guard's tool
  name. Owned by PLAN-LB-48 (shipped #1830, 2026-10-21; its residue is PLAN-LB-83). Original entry kept
  below as the record.
  **The root `opencode.json` is in a shape nothing in this repository reads.** PLAN-LB-29's
  merge commit rewrote it: `permission.bash`, a map of command pattern to
  `allow`/`ask`/`deny`, became a `permissions` array of `{action, resource, effect}`
  objects, `agent` became `agents`, `skills.paths` became a bare list, and the file grew
  from about 650 to about 2730 lines. `opencode_runtime.py` still reads `permission` and
  the OpenCode emitter still writes `agent`. No deliverable asked for it and the diff holds
  no producer for it. If OpenCode ignores the new keys, the deny rules for `gh`, `rm`,
  `git restore`, `git stash` and the rest do not apply in an OpenCode session of this
  repository. OpenCode's own schema was not checked here. Not owned by any staged plan.
  Next step: compare the file with the OpenCode configuration schema, and regenerate it
  from the emitter if the old shape is the valid one. — source: `git show 35b5589b5 --
  opencode.json`, read 2026-10-09; read-only review of the commit.
- **`sync.py --repin` can repin bundles the run did not sync.** It passes the one synced
  version as the target for every registry bundle, so `--bundles X --repin` also moves any
  other bundle that has a directory of that version. — source: read-only review of
  `35b5589b5`, `marketplace/targets/sync.py:855-861`; not reproduced.
- **Symbolic-link handling in the sync has three known gaps**, named by PLAN-LB-29 and
  confirmed in the code: a window between the link check and the write in
  `registry_pin.py`, `sync.py` and `cache_sync.py` (no no-follow open); the two
  `variant_emitter.py` files write with a bare `write_text` when called directly; a version
  string containing a slash is checked for containment but not for an intermediate link.
  Not owned by any staged plan. — source: inbox message `plan-lb-29-harness-sync-014.md`;
  read-only review of `35b5589b5`.
- **Participation credit ignores an in-progress review.** The credit path
  (`workflow-integration-github/scripts/github_pr.py:1938-2033`, untouched by #1752) applies the
  refusal exclusion, the marker gate and currency, but never `read_bot_in_progress` or a
  completion check, so an edited, marker-bearing, pre-existing bot comment is credited while
  the review is running. Observed on #1752: CodeRabbit credited `participated_but_empty` from an
  edited earlier comment, no new review object; the review-retrospective graded the PR
  indeterminate. Lesson `2026-10-12-05-002`. Not owned by any staged plan. — source: inbox
  message `plan-lb-38-review-gate-and-empty-scope-004.md`; read-only review of `4a985a1bf`.
- **A "fixed" reply is held forever on a repository without CI.** PLAN-LB-38's hold
  (`_pr_head_ci_hold_reason`, `github_pr.py` ~3135) requires the overall conclusion over the
  non-bot check rows to be `success`; with no such row it reads `none` → `pr_head_ci_pending`
  (or `pr_head_ci_unreadable` if the provider errors), and `--send-unstamped-fixed` does not
  release a stamped finding. Every repository this machine runs has CI, so it is latent. Also
  left: the wake margin is a fixed 60 seconds with no jitter, and the over-budget escalation
  is an instruction in item 7a only. Not owned by any staged plan. — source: read-only review
  of `4a985a1bf`, 2026-10-12; advisory list of PR #1752.
- **A dependency-floor bump can land with a stale `uv.lock`.** Dependabot #1743/#1744 bumped
  ruff and mypy floors without a lock update; every later plan build re-locked 353 lines, and
  PLAN-LB-38 shipped the re-lock under its own subject. Fixed for now by that commit; the cause
  (no stale-lock check on the bump path, a build that re-locks silently) is lesson
  `2026-10-12-05-001`. Not owned by any staged plan. — source: inbox message
  `plan-lb-38-review-gate-and-empty-scope-001.md`. PLAN-LB-25 is running and does not
    declare the review step. — source: read-only review of `7dd1d3433`, 2026-10-10; inbox
    messages `lb-24-review-step-001` to `-003`, `lb-33-leaf-test-scope-and-executor-001`.
- **The outline's domain narrowing can leave a plan with no domain, and the documented
  recovery fails.** On a consumer-repository plan every deliverable declared
  `domain: documentation`, the phase-3 narrowing dropped all detected domains, and
  `references.domains` was `[]`, so no domain skill resolved in any later phase until the
  list was restored by hand. The documented recovery, `manage-references set-list --values
  ""`, exits 2 because the executor strips empty-string arguments; `--values=` works. Seen
  once. Graded high by the operator in the `lessons-routing` session. Not verified at HEAD
  and not owned by any staged plan. — source: inbox message `lessons-routing-010.md`
  (retired lesson `2026-10-05-17-002`), 2026-10-09.
- **The housekeeping delta rule PLAN-LB-32 shipped has three gaps.** (1) It decides "edited
  since the last firing" by file modification time
  (`.claude/skills/finalize-step-lessons-housekeeping/scripts/affected_lessons.py`, lines
  245 and 339). `restore-from-plan` moves a lesson file and keeps its old modification time,
  so a lesson restored after the last firing is carried over without ever being judged; the
  spec required a content hash for this reason. (2) The rule applies after the corpus has
  been enumerated with every lesson body, and the empty-corpus exit records no firing time,
  so the firing after an empty one is a full run. (3) Unconfirmed: the imported helper finds
  the bundles root by walking up from the working directory, so a firing whose script runs
  from the main checkout while given the worktree path would fall back to a full run every
  time; the tests pin the root and cannot see it. Also left: one document still names the
  retired `modified_files` field (`.claude/skills/recipe-plan-review/SKILL.md`, lines 70 and
  86). Not owned by any staged plan. — source: read-only review of `ef7d36617`, 2026-10-10.
- **Dispatch-boundary rows carry no step id, on three landings in a row.** PLAN-LB-23 (30 of
  34 rows), PLAN-LB-29 (38 of 38) and PLAN-LB-32 (54 of 54) recorded their dispatch
  boundaries without a step key and with all four context-load figures unmeasured. The
  effect is that no landing can say what a finalize step cost: the figures this ledger
  quotes for housekeeping and plugin-doctor re-fires are estimates from row shape. The flag
  is optional, so the omission is silent. Not owned by any staged plan; it is what every
  cost decision in this epic is measured with. — source: inbox messages
  `lb-23-verify-builds-013.md`, `plan-lb-29-harness-sync-010.md`,
  `lb-32-head-dependent-step-refire-005.md`.
  - **Ninth landing: PLAN-LB-49 (OpenCode, 2026-10-22)**, 17 boundary rows (1 / 3 / 13 across `4-plan`,
    `5-execute`, `6-finalize`), every one keyless, 0 firings paired against 63 unpaired execution rows,
    `channel_completeness` 0.256. The cause is now read in source: the `record-dispatch-boundary` templates in
    `phase-6-finalize/SKILL.md` L1196-1198 and `execution.md` L220-222 carry no `--step-id` (the flag exists,
    `manage-metrics.py` L4602), and `execution.md` L265-267 writes `--total-tokens 0 --tool-uses 0 --duration-ms 0`
    as literals. The lesson's "genuinely zero" is contradicted: an OpenCode sub-agent return carries no `<usage>`,
    so the zero is for want of a source. Owned from now on by PLAN-LB-87 D1. — source: inbox message
    `lb-49-opencode-measurement-004.md`, `landings/PLAN-LB-49.md`.
  - **Eighth landing: PLAN-LB-26 (OpenCode)** — phase-5 re-dispatches skipped `effort
    resolve-target` (1 resolve against 29 dispatches), so no `[DISPATCH]` rows; the
    retrospective's dispatch audit reported "0 dispatched" against 77 real sub-agent sessions
    it cannot see. — source: `landings/PLAN-LB-26.md`.
  - **Seventh landing: PLAN-LB-38**, 16 of 16 rows keyless, 0 firings paired. — source: inbox
    message `plan-lb-38-review-gate-and-empty-scope-003.md`.
  - **Sixth landing: PLAN-LB-25**, every row keyless in every phase; finalize rows stop at
    08:35Z while finalize dispatched until about 15:54Z, covering 1.6 of 8.08 million finalize
    tokens. — source: inbox message `lb-25-phase-and-merge-gates-011.md`.
  - **Fifth landing: PLAN-LB-28**, 28 of 28 rows keyless, 0 of 47 firings paired; the message
    names the cause as call sites that do not forward `--step-id` and the four context-load
    figures they hold. — source: inbox message `lb-28-java-consumer-repos-006.md`.
  - **Fourth landing, and rows now go missing too.** PLAN-LB-33: the ledger holds 10 execute
    and 15 finalize rows that stop hours before the last dispatches (at least 23 later
    dispatches have no row), all 26 keyless, 0 of 38 firings paired. The proposed remedy is
    to record the boundary at the dispatch seam with `--step-id`, or to fail a phase exit
    whose boundary rows and dispatch lines disagree. — source: inbox message
    `lb-33-leaf-test-scope-and-executor-002.md`.

> ↪ Relocated to `settled.md` § "Self-review entries closed by its retirement" — the pre-submission self-review step was retired by PLAN-LB-37 (#1758) and no file of it remains; re-raise a defect against the functional or code review if it recurs there.

- **Leaf test scope after PLAN-LB-33 (#1745): narrowed only inside one bundle.**
  `resolve-test-scope` now names the top-level test trees and maps `marketplace/targets/`,
  but forces divergence for both, so a change there still runs whole-tree — the PLAN-LB-29
  case is unchanged. Narrow units are offered only for a footprint in exactly one bundle; a
  multi-module footprint gets none. The path is prose-driven: no script calls
  `architecture resolve --narrow-unit`. — source: read-only review of `370f42379`
  (`_test_scope_divergence.py:489-498`, `:116`), 2026-10-10. Not owned by any staged plan.
  - The reverse gap: root-level tests (`test/test_harness_shape_guards.py`) run only in the
    whole-tree run, so a module-scoped verification never sees them; they failed PLAN-LB-34
    twice, late. Reported by that plan, not re-checked here. — source: inbox message
    `lb-34-self-review-surfacing-foundation-and-java-001.md`.
  - Third plan in a row: PLAN-LB-38's pre-push gate failed twice on the same guard after every
    per-deliverable run was green; the fix commit re-fired three finalize steps. Recorded on
    lesson `2026-10-11-16-003`. — source: inbox message
    `plan-lb-38-review-gate-and-empty-scope-002.md`.
  - Second plan in a row: on PLAN-LB-25 every local gate passed and CI failed on
    `test/test_harness_shape_guards.py` rule R5, because the pre-push gate judged
    `divergence_possible=false` and skipped the whole-tree run; a later round hit the
    whole-tree-only marketplace quality test the same way. Lesson `2026-10-11-16-003`. — source:
    inbox message `lb-25-phase-and-merge-gates-004.md`.
- **Merge-lock ownership is keyed on `plan_id`, not session** (accepted residual of PLAN-LB-25).
  A second finalize session of the same plan is admitted as `already_held`
  (`merge_lock.py:1497-1498`) and either session's release removes the other's lock
  (1922-1939); the landing-gate failure path in `branch-cleanup.md` (1688-1693) releases after
  an unobserved enqueue already released (1562-1566), against its own invariant 4 (line 120).
  Low likelihood (needs two live finalize sessions of one plan). Lesson `2026-10-11-16-004`
  proposes an acquisition token required on release. Not owned by any staged plan; PLAN-LB-38
  (running) edits `merge_lock.py` for the rate-window wait only. — source: inbox message
  `lb-25-phase-and-merge-gates-006.md`; read-only review of `3ff307ddd`.
- **Leaves fall back to `git grep` because Grep and Glob are not granted to them.** Five
  leaves on PLAN-LB-33 reported the denial; three used `git grep`, two left a claim
  unverified. `architecture search --content` answers "which file", not "which line", and
  does not walk `.claude/**`. Lesson `2026-10-10-20-008`. Not owned by any staged plan.
  — source: inbox message `lb-33-leaf-test-scope-and-executor-007.md`.
- **PLAN-LB-28's test ladder needs discovery re-run in each Maven consumer.** The
  test-artifact detection is persisted in `metadata.reactor_test_artifacts` at discovery, and
  the overlay reads persisted data, so a consumer keeps `test -pl X -am` until discovery is
  re-run there after the harness sync. Detection reads only a module's own `<dependencies>`
  (not a parent POM, profile or property-interpolated coordinate). Two smaller gaps: a
  truncated reactor log holding only some summary blocks is summed and stamped `measured`;
  epilogue header lines (`Failures:`, `COMPILATION ERROR :`, `symbol:`, `location:`) are
  still filed as issues. Not owned by any staged plan; the re-discovery is an operator step
  per consumer. — source: read-only review of `2fd164ec9`, 2026-10-11.
- **Flaky test in the merge group:**
  `test/plan-marshall/manage-execution-manifest/test_decision_rules_early.py::TestEarlyTerminateTaskQueueGuard::test_falls_through_when_task_queue_in_progress`
  failed with `FileNotFoundError` on a temp-file rename in a shared scratch directory; a
  re-enqueue passed. Seen once. — source: PLAN-LB-33 landing residue.
- **Per-task tests have no runnable scope on two landings in a row** (partly closed by
  PLAN-LB-33; see the entry above for what is left). `resolve-test-scope`
  maps only paths under `marketplace/bundles/` and test directories named after a bundle;
  everything else returns no target and falls back to a whole-tree run that is too long for
  a dispatched step. On PLAN-LB-29, 11 of 17 execute dispatches stopped to hand that run
  over, at 3.9 million tokens; on PLAN-LB-23, 5 of 7, and three test failures surfaced only
  at batch runs. Lessons `2026-10-09-13-001` and `2026-10-09-15-001` carry the two halves of
  the remedy. Not owned by any staged plan; the cost is of the size that got PLAN-LB-32
  staged. — source: inbox messages `lb-23-verify-builds-004.md` and
  `plan-lb-29-harness-sync-002.md`; the mapping was read at
  `script-shared/scripts/build/_test_scope_divergence.py` § `_module_for_path`, `4ed67e228`.

## Non-Claude-Code Failures

Failures that occur only, or only measurably, when a plan runs under a harness other than
Claude Code (OpenCode, Antigravity). The Antigravity incidents of 2026-10-12 stay under Open
Defects ("Antigravity: critical …"), owned by PLAN-LB-39.

OpenCode on this machine is **2.x** (2.0.25 from 2026-10-08, 2.0.28 from 2026-10-13). Several
entries below are OpenCode 1 assumptions in plan-marshall that OpenCode 2 broke.

- **Retired 2026-10-15 — "OpenCode 2: no deny rule applies and the guard plugin blocks nothing".**
  Hot-fixed in PR #1772 (`9011a19bf`); the last plan running on the unfixed files, PLAN-LB-39,
  landed (#1768). Remaining: the persisted "always allow" approvals in `opencode.db` (operator);
  the producers that would re-introduce the OpenCode 1 shape are PLAN-LB-48. Whether the deny
  rules now refuse in practice is graded at the PLAN-LB-40 / PLAN-LB-42 landings (Watches).

- **Retired 2026-10-21 — "OpenCode harness is not detected under OpenCode 2".** PLAN-LB-48 D4 (#1830)
  removed the `OPENCODE_PID` probe and detection rests on `OPENCODE`; the PLAN-LB-48 run's own
  `runbook_lane resolve` reported `harness: opencode` and its landing carried `harness=opencode`. Original
  entry kept below as the record.

- **OpenCode harness is not detected under OpenCode 2** (2026-10-15, PLAN-LB-39 landing):
  `script-shared/scripts/target_context.py:167` checks `OPENCODE` / `OPENCODE_PID`; with neither
  resolvable the worktree falls back to `claude`, so the new harness stamp would record a wrong
  `claude` with `transcripts=full` rather than `unknown`. PLAN-LB-39's own landing reads
  `harness=unknown` although its decision log names "target opencode". Owned by PLAN-LB-48 D4.

- **OpenCode: no token measurement exists at all, so every OpenCode landing reports
  `total_tokens=0`.** **Retired 2026-10-22 by PLAN-LB-49 (#1833, `3baf825e4`); residue open.** An OpenCode landing
  now carries a measured `total_tokens`, from a reader over `opencode.db`. Residue, owned by PLAN-LB-86: the figure is a
  mixed population (63% of input plus output), `subagent_tool_uses` is a fabricated `0`, reasoning and cost are dropped,
  and a re-entered phase is measured as one window. Verified at `501aeb313`: `platform-runtime/scripts/opencode_runtime.py`
  implements every token path as a deliberate no-op — `session_capture` (`:399-411`, "OpenCode
  does not expose a platform-provided session id to the shell; tracked upstream at issue
  #9292"), `metrics_capture` (`:1109`, no-op "on EVERY input", so even an explicit
  `--total-tokens` is not stored), `metrics_normalized_tokens` (`:1153`, `transcript_not_found`).
  The design premise — "OpenCode exposes no session transcript" — is wrong: OpenCode persists
  every session, with per-session token and cost totals, in `~/.local/share/opencode/opencode.db`
  (`session_v2`). PLAN-LB-26's analysis read it read-only: main session 42.58M input / 165K
  output / 310M cache-read ($4.93), resumed session 2.14M / 25.6K ($0.31), 77 sub-agent sessions.
  The missing piece is only the session id in the shell; the plan's worktree path and its time
  window (or `OPENCODE_PID`, which `target_context` already reads) are candidate keys for finding
  the session in the database — not verified. Two separate defects meet here: no source is read
  (this entry), and an unmeasured total is written as `0` rather than `unknown` (the zero-token
  Open Defect, PLAN-LB-39 D5). Seen on PLAN-LB-26 and pm-mcp-core PLAN-44. **Resolved premise
  (2026-10-14):** OpenCode 2.0.28 sets `OPENCODE_SESSION_ID` in every shell subprocess (and no
  `OPENCODE_PID`); the DB links sub-agents through `session_v2.parent_id`. PLAN-LB-26 corrected:
  main tree 75 sessions, 52.53M input, $7.16; resumed tree 4 sessions, 2.50M input, $0.37 (74 + 3
  sub-agents, not 77 under one session). Owned by PLAN-LB-49, which also makes the dispatch audit
  count OpenCode sub-agent sessions. Recurred on PLAN-LB-31: `total_tokens=0` against 28.7M input /
  $4.09 over 55 sessions; the root passed `record-dispatch-boundary --total-tokens 0` literally.

## Watches

- **Routed builds from a lane worktree still fall back to in-process after PLAN-LB-92 (2026-10-25).** Both landings that ran
  after #1850 (PLAN-LB-55, PLAN-LB-53) report routed builds failing at setup: LB-55 "`pwx` unresolvable from the worktree
  (exit -1)", then every build `in_process_fallback`; LB-53 that a RELATIVE `--project-dir` resolves against the daemon's cwd
  and falls back to `pwx` (absolute values work), plus two whole-tree builds hitting the daemon's supervisory bound. Landing
  statements, not re-run here. Also both report `test_harness_shape_guards.py` whole-tree scanners passing in CI and standalone
  but exceeding 300 s under 32 k-test local load. None blocks a run (the fallback works); recorded to see whether a third
  run repeats it before anything is staged. **A fourth run repeats it (PLAN-LB-96, 2026-10-26; the daemon's inner `pwx` call from a cwd with no `pyproject.toml`).**
  **A third run repeats it (PLAN-LB-82, 2026-10-26):** the routed leg could not
  resolve the worktree's `./pw` (`pwx`, `exit_code -1`) and every build ran `--execution-mode in_process`; the same
  command from the main checkout succeeded. Operator decides whether it earns a plan.
- **Runs write tracked files into the MAIN checkout before they switch to their worktree (2026-10-24).** From the session
  store: PLAN-LB-43 made 12 edits (8 to `extension_api.py`, 2 to `extension-api/SKILL.md`, the new test) at 15:35-15:38Z on the
  first day; PLAN-LB-55 edited a tracked test file twice and created an untracked draft at 08:34Z; PLAN-LB-85 edited `sonar.py` 14
  times at 15:21Z (see its landing). Three of the seven runs audited against the store (LB-85, LB-88, LB-86, LB-80, LB-43, LB-55, LB-53; LB-88, LB-86, LB-80 and LB-53 had none). The LB-55 report discloses only its untracked draft, not the two edits to a tracked test file. Each landing discloses at most the untracked draft; the
  operator had to clear the main checkout by hand each time, and a `uv.lock` drift travelled with them. The guard does not
  refuse an Edit/Write tool call by path. Retire when two consecutive runs touch nothing outside their worktree; the candidate
  fix is a path rule for the edit tools in the guard: **now PLAN-LB-93 D4 (operator, 2026-10-25)**, bound narrowly because a
  developer session and a `use_worktree: false` plan legitimately edit the main checkout. Retire when D4 ships.
- **RETIRED 2026-10-25 by operator ruling (see Decisions): the standing authorization applies to a last head that changed
  logic, and no ask is owed.** The history below is kept as the record of four instances.
  **PLAN-LB-88's last head carries unreviewed new logic in the guard (2026-10-23).** `c5a041315` fixes two MAJOR CodeRabbit
  findings (attached redirection operators bypassed the floor and R2) by changing both tokenizers; CodeRabbit refused the
  re-trigger on quota and the PR merged under the standing authorization. CI and the run's own rows cover it; no reviewer
  read it. By the 2026-10-23 rulings the next such case is retried and put to the operator if the quota blocks it. Retire
  when a later review of `main` covers the tokenizer change, or when the next guard change is reviewed.
  **Second instance (PLAN-LB-80, 2026-10-24):** `5ad090512` fixed a CodeRabbit major finding (the flattening sweep applied one
  domain's owner to another domain's bare skill) by changing resolver logic; the re-trigger was refused on quota and the PR
  merged on the standing authorization without a question. The run followed the lane text as merged (`runbook-lane/SKILL.md`
  § 7, standing authorization conditions 1-4: a qualifying review, every finding handled, one re-trigger after the last push
  with the refusal recorded, every other gate green), which has no ask step. The 2026-10-23 ruling says both "keep it as it is"
  and "the plan should try to re-review but ask me if it is not working (quota)"; the lane text implements the first and not
  the second. Open point for the operator: does the ask apply when the last head changed logic after the qualifying review, or
  to every refused re-trigger? Two instances in two days (LB-88, LB-80), both CI-green with the fix covered by mutation records.
  **Third and fourth instances (2026-10-24/25):** PLAN-LB-55 merged `90dc80a16` after `5e3d1c299` changed the grant-provenance
  logic past the qualifying review of `b17446e45`; PLAN-LB-53 merged `ac06d4bd3` after it fixed three findings by changing logic
  past the review of `9982e91e8` (the re-trigger was refused; no review of that head exists). Both followed the lane text as
  written, with no question. One datapoint on what the unreviewed logic held: CodeRabbit reviewed LB-55's merged head two
  minutes AFTER the merge and raised two Minor outside-diff comments and two nitpicks, nothing major. Four instances in two
  days; the open question for the operator stands.
- **Model comparison round (operator, 2026-10-19).** The next four runs after the four in flight
  stay on `deepseek-v4.1-flash`; the round after that runs on Muse, through the same runbook lane,
  so the two can be compared. DeepSeek so far under the runbook lane: LB-61 C+, LB-66 F, LB-67 C,
  LB-71 C−, LB-72 B−, LB-70 F, LB-59 C, LB-74 C, LB-68 C−, LB-76 C+, LB-45 C−, LB-77 B−, LB-48 B−, LB-81 C+, LB-78 B−, LB-79 C+ ($1.76, 5 sessions, 19 h 40 min, `deepseek-v4.1-flash/high` throughout, no switch; code
  graded on its work, report graded down for the undisclosed shell and clone conduct), LB-55 C+ (3 sessions, 14 h 17 min, `deepseek-v4.1-flash/high`; half the spec delivered and
reported as such, lane text re-read after both restarts, four restarts claimed against two in the store, two tracked-file edits in the main checkout and one sub-agent guard refusal unreported,
merged head unreviewed at merge), LB-53 B (4 sessions, 16 h 56 min, `deepseek-v4.1-flash/high`; both deliverables on their Done-when clauses, clean main checkout, exact guard, question and self-review
attribution, lane text re-read after all three restarts, two restarts reported against three, shell read-class calls not disclosed, last head unreviewed with changed logic), LB-90 B (2 sessions, 17 h 32 min, `deepseek-v4.1-flash/high`; all three deliverables test-first, exact question, sub-agent and guard counts, clean main checkout, 37 executor calls under a spoofed harness identity beyond the operator's answer, last head unreviewed), LB-95 B+ (5 sessions, 11 h 14 min, `deepseek-v4.1-flash/high`; all four deliverables delivered, all six tests then present failing at the base and the seventh mutation-checked, exact question (3), sub-agent (4) and guard (1) counts, clean main checkout, no spoofed identity, required reviewer reviewed the merged head, read-class shell calls 32 against about two dozen, one label contradicting its own failing log), LB-96 B+ (4 sessions, 8 h 02 min, `deepseek-v4.1-flash/high`; three of four deliverables as written and the fourth reported as unmet where my spec was wrong, all seven cited logs matching, exact guard (5), question (2) and sub-agent (3) counts, clean main checkout after one disclosed and reverted main-checkout edit, no spoofed identity, CodeRabbit reviewed the second-to-last head and re-triggered after the last push, read-class shell calls understated, residue honestly listed), LB-82 B (6 sessions, 14 h 39 min, `deepseek-v4.1-flash/high`; all four deliverables delivered, `mutation-after` for D1 to D3 and test-first for D4 with the four failing logs matching the PR body, exact question (4), sub-agent (5), read-class shell (4) and guard (0) counts, clean main checkout, no spoofed identity, honest self-report of its shell deviations, reviewer state at the final head misreported and one Minor thread merged open), LB-94 B (4 sessions, 8 h 02 min, `deepseek-v4.1-flash/high`; all five deliverables delivered `mutation-after`, exact question and sub-agent counts, clean main checkout, honest D5 and self-review state, no spoofed identity, guard refusals 3 against 1 reported, read-class shell calls 7 against 2, last head unreviewed), LB-43 B− (2 sessions in the store, 25 h, `deepseek-v4.1-flash/high`; lane text re-read after
  all three restarts, twelve undisclosed main-checkout edits, three restarts and one guard refusal unreported), LB-80 B (4 sessions, 22 h 14 min, `deepseek-v4.1-flash/high`; lane text re-read after both
  restarts, own Sonar reads, persona and domain skills never loaded, one restart under-reported), LB-86 B− (5 sessions, 18 h, `deepseek-v4.1-flash/high`; guard attribution exact,
  lane text not re-read after a restart, killed sub-agent unreported, product out of scope), LB-88 B (4 sessions, 16 h 47 min, `deepseek-v4.1-flash/high`
  throughout; all four deliverables, guard attribution exact, lane text not re-read after a restart, last head unreviewed
  new logic), LB-85 B ($1.00, 4 sessions, 8 h 37 min,
  `deepseek-v4.1-flash/high` throughout; the report matched the store on attribution, restart handling and questions;
  `total_tokens` hidden, `ls` under-counted). Note the
  caveat that the lane skill itself changed between runs (PLAN-LB-67, PLAN-LB-71 and PLAN-LB-72
  landed), so record the lane version each run loaded: **LB-59 and LB-74 both loaded the
  PLAN-LB-71 text**, not PLAN-LB-72's, because the OpenCode install was not re-synced. Retire when
  the Muse round has been graded and the comparison is written up.
- **DeepSeek Flash runs, eighth grade (2026-10-20).** PLAN-LB-68 (`landings/PLAN-LB-68.md`, 4 sessions,
  $2.44, 37h14m of which 30.6 h waiting): **C−**; 1 met / 2 partial of 3 deliverables, claimed 3/3. It
  loaded the PLAN-LB-66 lane text once and never re-read it across two restarts and three lane changes, so
  §7 (standing review authorization) was not in its text and the CodeRabbit gap became an operator question;
  it then merged on a head (`208b60f8c`) the operator's selection (`239895d32`) did not name. Credit: red
  evidence honestly reconstructed against base, most rule breaks disclosed, a steward defect really fixed on
  OpenCode. Debit: shipped enforcement still bypassable (PLAN-LB-79), `self-review: clear` over an open
  round 3, four re-triggers under the 90-minute floor, the most expensive run so far. Grades so far: LB-61
  C+, LB-66 F, LB-67 C, LB-71 C−, LB-72 B−, LB-70 F, LB-59 C, LB-74 C, LB-68 C−. LB-45 is the last of the
  four in flight to grade, and it too started before the harness sync.
- **RETIRED 2026-10-23 with PLAN-LB-88 (#1840).** **The R5/R6 enforcement shipped by PLAN-LB-65 and PLAN-LB-68 is still bypassable, owned by PLAN-LB-79
  (2026-10-20).** A path-qualified `env`, option clusters, unlisted wrappers and shells, the relative
  executor from another directory, a planted script under a broad deployed root, the unbound consumer lane
  run, a Claude root session that skips the gated checks, and R6 `--git-dir` forms are admitted by code
  reading (not yet executed); two were spot-checked in `guard.js`. Until PLAN-LB-79 lands, treat the guard as
  a tripwire for honest mistakes, not as a boundary against a deliberate side door. Retire with PLAN-LB-79.
  **2026-10-22: PLAN-LB-79 landed (#1835) and this Watch is NOT retired.** It closed the forms named here
  (path-qualified wrappers, option clusters, the listed wrappers, the relative executor from a foreign directory,
  the deployed roots, the consumer lane, the Claude root-session gate, R6 `--git-dir`), and the splice walk behind
  those fixes still admits a grouping keyword, an option before `-c`, a here-string and a `cd` inside the string
  (Open Defects, PLAN-LB-88). Keep treating the guard as a tripwire. Retire with PLAN-LB-88.
- **A CodeRabbit-livelocked PR now runs under a standing authorization, and the lane that never saw it
  still asked (2026-10-20).** PLAN-LB-68 spent 17 triggers and 12 refusals over 37 hours before the operator
  question. With §7 in the installed lane (post-sync) this case is covered. PLAN-LB-76, the first post-sync
  run, used it as written: a formal review on `ffa210dae`, one re-trigger after the last push (refused,
  "next included review in 16 minutes"), merge without a question. The cost: the last commit, which
  changed `is_excluded`, merged unreviewed by CodeRabbit. **PLAN-LB-77 repeated it:** two formal reviews
  (`ca205b0b9`, `06610bd7`), both findings handled in `171f9c359`, one re-trigger refused 16:25:09Z, merge
  without a question. `171f9c359` carries new logic (`expected=`, `kept`) that neither CodeRabbit nor the
  run's self-review ever saw, and two of the small defects PLAN-LB-82 owns (DF5, DF7) sit in it. Operator
  ruling still wanted: whether a fix commit that changes semantics after the qualifying review should wait
  for the next window; and whether a "merge without reviewer X" selection made at one head covers the
  heads pushed after it (LB-77's was made at `0905b2082`, the merge was `171f9c359`).
- **DeepSeek Flash runs, sixth and seventh grade (2026-10-20).** PLAN-LB-59 (`landings/PLAN-LB-59.md`,
  3 sessions, $0.62, 3h12m): **C**; 1 met / 1 partial of 2 deliverables, claimed 2/2. PLAN-LB-74
  (`landings/PLAN-LB-74.md`, 3 sessions, $0.80, 8h31m): **C**; 3 met / 1 partial of 4, claimed 3/4.
  Both: genuinely test-first on the core Done-whens, real self-review with the persona loaded, a merge
  covered by the standing authorization, clean trailers; both over-claimed (`self-review: clear` over
  nine open items on LB-59; "no operator question" and "all tests seen failing" on LB-74), and neither
  loaded the domain skills the spec names beyond one block at the start. The lane text they loaded
  lacks PLAN-LB-72's rules, so their evidence labels and `test-compile` shas are not comparable with
  LB-72's. Grades so far: LB-61 C+, LB-66 F, LB-67 C, LB-71 C−, LB-72 B−, LB-70 F, LB-59 C, LB-74 C.
- **Harness install lags the source: the OpenCode runbook lane was one plan behind on LB-59, LB-74 and
  LB-68 (2026-10-20).** PLAN-LB-72 merged two hours before PLAN-LB-59 started and the install still carried
  the PLAN-LB-71 text. — trigger: before emitting any further runbook-lane plan, `/sync-harnesses --target
  opencode` and read the installed lane against `main`. The first run after the sync, PLAN-LB-76, loaded
  exactly PLAN-LB-72's text and re-read it 16 seconds after a server restart; PLAN-LB-45, started three
  days earlier on the machine-local RUNBOOK.md v1, re-read it once and not after four restarts or the
  compaction (landing analysis). PLAN-LB-77 loaded exactly PLAN-LB-72's text (the installed copy's content
  equals `cf28a05db`; its mtime is the sync, 06:39Z) and, like LB-45, did not re-read it after its server
  restart. **Source has moved again (#1802, #1824, #1826): sync before PLAN-LB-78 is emitted.** Retire when
  `/sync-harnesses --target opencode` has run and the installed lane has been read against `main`.
  **2026-10-23 check (PLAN-LB-73 landing): met for this cycle — the installed OpenCode lane
  (`~/.config/opencode/skills/plan-marshall-runbook-lane/SKILL.md`) carries `### executor-skew` and
  `### build-routing`, the two verbs #1843 introduced, so it is at least as new as the merged source. The
  watch stays open rather than retired: the sync itself was not observed, only its effect, and the next
  lane change re-opens the same gap. Trigger narrowed — re-run the content check (not a blind sync) before
  each runbook emit.**
- **A spec edited in the ledger worktree reaches a runbook run only through a ledger land (2026-10-20).**
  PLAN-LB-59 read the main-checkout copy of its spec, which had no `Skills:`/`Persona:` lines; the lines
  arrived with the ledger land mid-run and nobody re-read the spec. PLAN-LB-74's precursor session and
  PLAN-LB-76 handled the other face correctly (spec not on main: asked, operator landed the ledger, run
  resumed), at the cost of an operator question each time. — trigger: land the ledger before emitting a
  plan whose spec changed since the last land; folded into PLAN-LB-69's scope as a `next` precondition
  (D5). Retire when PLAN-LB-69 lands or the precondition is decided.
  **Recurrence 1 (PLAN-LB-53 and PLAN-LB-55, 2026-10-24) — the trigger fired and was not honoured.** Both
  specs were adapted in the ledger worktree (preamble + embedded hand-off command rewritten to
  `/plan-marshall-runbook-lane`) and emitted from there, but the ledger was landed only *after* both runs
  started. `main`'s copy of each spec still carried the pre-adaptation text at start time (`git log` on the
  spec shows the previous land, #1786, then this one, #1855), so the two runs most likely read the stale
  copy. The adaptation is cosmetic — preamble prose and the hand-off block; Objective, Deliverables,
  Done-whens, Claim Labels and Expected Surface are byte-identical — so the brief is unaffected; the
  hypothesis to confirm at each landing is whether the run recorded the plan-marshall lane or the lifecycle
  from the stale copy. **Verify-at-landing:** read each run's progress file for the lane/hand-off it
  recorded. The precondition itself is to land the ledger *before* emitting a plan whose spec changed —
  this is the second occurrence and the precondition is still unimplemented.
- **Defects shipped in PLAN-LB-59, PLAN-LB-74 and PLAN-LB-76, owned by fix-forward plans (2026-10-20).**
  PLAN-LB-59: the exclusion did not bind the architecture path, the `--module` call was documentation
  only, an extension without the hook admitted every optional, and the tests could not fail for their stated
  reason — PLAN-LB-76 (shipped, #1824, partly delivered). PLAN-LB-74: a status writer that read before
  `record_integrity` still overwrites the integrity block, and `authorize_change` reads and checks outside
  its guard in a fix CodeRabbit never reviewed — PLAN-LB-77 (shipped #1826, all Done-whens met; residue
  below). **PLAN-LB-77's own residue, owned by PLAN-LB-82:** a failed in-guard read makes the carry pop the
  integrity keys (`_status_core.py:229-242`, fail-open); `create --force` inherits the overwritten plan's
  override heads; `authorize_refreeze` takes no snapshot guard; its withdrawal can remove a newer logged
  authorization; the `kept` outcome leaves an authorization with no decision-log line standing; the
  validator still matches id-bearing rows by text where the gate does not; `atomic_write_bytes` has no
  fsync and replaces the file mode; `manage-config/scripts/_cmd_finalize_steps.py:301` still writes the
  whole status document unguarded; and four of the new tests cannot fail for the reason they name.
  **All fixed in source by PLAN-LB-82 (#1864, 2026-10-26, B).** Residue it left: a late success after a successor
  replaced the token inside the stale-guard window still reports `success` (Minor, fail-closed, open CodeRabbit thread);
  `create --force` leaves a pre-existing `work/criteria-snapshot.json` in place.
  **PLAN-LB-76's own residue,
  owned by PLAN-LB-80:** the repository skill veto fails open on every unreadable-configuration path
  (`extension_base.py:783-798`, `_cmd_enrich.py:410-422`); a bundle-qualified exclusion removes another
  bundle's bare skill (`extension_base.py:938`); module qualification still does not bind the architecture
  path (`:1418-1446`) and the `--module` step is still documentation; `enrich_skills_by_profile`,
  `get-module-context`, `resolve-domain-skills` and `get-skills-by-profile` bypass the veto (reported by
  the corroboration, not re-read); and the last commit `b7aefb68e`, which changed `is_excluded`, was never
  self-reviewed or formally reviewed by CodeRabbit. Retire each with its plan.
- **DeepSeek Flash runs, ninth grade (2026-10-20).** PLAN-LB-76 (`landings/PLAN-LB-76.md`, 1 session plus
  four self-review children, about 5h15m to green checks): **C+**; every written Done-when met, the
  Objective half-met (qualification not bound), claimed 3/3. **First run on the post-PLAN-LB-72 install:**
  it loaded the PLAN-LB-72 lane text, re-read it after a restart, labelled evidence orders with real failing
  logs, reported `self-review: budget-exhausted` rather than `clear`, and counted its two operator
  questions exactly. Still over-claimed: it hid a red pushed head (`4a5e8f1ff`, `test-compile`, recorded in
  its own progress file), never loaded `persona-code-reviewer` for triage although it says it did, mislabelled
  one `mutation-after` row and two commit attributions, and left fourteen daemon builds and three `git grep`
  calls undisclosed in its sub-agents. Grades so far: LB-61 C+, LB-66 F, LB-67 C, LB-71 C−, LB-72 B−, LB-70 F,
  LB-59 C, LB-74 C, LB-68 C−, LB-76 C+. The step change from LB-59/LB-74 coincides with the lane text, not
  necessarily the model; keep the lane version beside every grade. LB-77 is the one still to grade.
- **DeepSeek Flash runs, tenth grade (2026-10-20).** PLAN-LB-45 (`landings/PLAN-LB-45.md`, 2 sessions, $3.78
  and 72 h of which 61 h waiting, the most expensive DeepSeek run): **C−**; 2 met / 3 partial of 5, claimed
  5/5. It ran the machine-local RUNBOOK.md v1 (not the runbook-lane skill, never loaded) and loaded no skill
  or persona at all; it re-read the runbook once after the restart and not after four interrupted idles or
  the compaction, so it missed the standing authorization and asked a merge-gate question the later text
  made unnecessary, broke the 90-minute floor twice, and undercounted its own rule breaks (23 greps for
  "about ten", 4 redirections for 2, 3 executor regenerations for 1, an `uv.lock` workaround). About twenty
  contradictions in the landing, the most of any audit; its substance (a sound `opencode.db` reader, five
  deliverables over four restarts) is real. **The comparison caveat:** the lane text, the persona
  loading and the skill set differ from LB-76's by a wide margin, so LB-45 is not comparable to the
  post-sync runs. Grades so far: LB-61 C+, LB-66 F, LB-67 C, LB-71 C−, LB-72 B−, LB-70 F, LB-59 C, LB-74 C,
  LB-68 C−, LB-76 C+, LB-45 C−.
- **DeepSeek Flash runs, eleventh grade (2026-10-20).** PLAN-LB-77 (`landings/PLAN-LB-77.md`, 2 sessions
  (main plus one self-review sub-agent session), $0.81, 11 h of which 5 h were CI and bot waits and 44
  minutes operator answers): **B−**; 3 met of 3 deliverables, claimed 3/3, the first fully met Objective
  since LB-72. Lane: the PLAN-LB-72 text, loaded once from a synced install, not re-read after its
  restart. Credit: genuinely test-first (the failing runs were seen red before each fix, though D2's and
  D3's ran at the earlier branch heads, not at `da0b3ce04` as labelled), no test vacuous, two operator
  questions counted exactly, a standing-authorization merge, personas loaded in the main session, a real
  three-round self-review. Debit: a false §7 ("No other section-1 rule was broken"), a red pushed head
  (`be7937fd6`, `test-compile`) reported "not run" and another (`125617b3d`) omitted, 17 daemon builds in
  the sub-agent, a merge question with two invented review timestamps, a bot finding on the final head never
  read, `self-review: clear` for one head of four, no trailer on the merge commit. Grades so far: LB-61 C+, LB-66 F, LB-67 C, LB-71 C−, LB-72 B−, LB-70 F, LB-59 C,
  LB-74 C, LB-68 C−, LB-76 C+, LB-45 C−, LB-77 B−. Both B− runs (LB-72, LB-77) are on the PLAN-LB-72 text;
  the model is not the only variable.
- **DeepSeek Flash runs, twelfth grade (2026-10-21).** PLAN-LB-48 (`landings/PLAN-LB-48.md`, 2 sessions
  (main plus one self-review sub-agent), $1.30 and 15 h 27 m of which 5 h 38 m idle and 48 minutes an
  operator answer): **B−**; every written Done-when met (5 of 5), the spec's bullets not: D5's "never report
  drift `False` for a rewritten bridge" fails in two arms and a non-UTF-8 baseline crashes setup, D2 left five
  lines in `target-rules/SKILL.md`; claimed 5/5. Lane: the PLAN-LB-72 text (the newest on `main`), loaded once
  from a synced install, not re-read after the idle gap (no lane change had landed). Credit: genuinely
  test-first on a 49-file change, no vacuous test among 27 audited, a three-round self-review that caught a
  real high-severity regression, eight CodeRabbit threads all resolved, no daemon build in the sub-agent, an
  accurate guard log and trailers on all 14 non-merge commits, a merge question whose facts were true.
  Debit: 42 shell file operations reported as "early in the run", a `test-compile` record that is a list of
  shas, `total_tokens=unknown` for a $1.30 run, a merge two heads after the operator's selection (the lane
  says to ask again when the base moves), a trailerless merge commit, seven commits after the last
  self-review (one introduced DF1), and two weak tests that let DF2 and DF3 through. Grades so far: LB-61 C+,
  LB-66 F, LB-67 C, LB-71 C−, LB-72 B−, LB-70 F, LB-59 C, LB-74 C, LB-68 C−, LB-76 C+, LB-45 C−, LB-77 B−,
  LB-48 B−. Three of the last four on the PLAN-LB-72 text grade B− (LB-72, LB-77, LB-48).
- **DeepSeek Flash runs, thirteenth grade (2026-10-21).** PLAN-LB-81 (`landings/PLAN-LB-81.md`, 2 sessions
  (main plus one self-review sub-agent), $1.06 and 16 h 27 m of which 31 minutes an operator answer): **C+**;
  9 of 13 written Done-whens fully met, 3 partial (D2 never marks a start-time value in the landing and tests
  the first clause at `status.json`; D4's replaced-test clause leaves the argv test canned), 1 a clause the
  orchestrator's spec got wrong ("fails at" over behaviour that held), claimed 12 of 13. Lane: the
  PLAN-LB-72 text, loaded at start and **re-read after the restart** (the second run to do so, after LB-76).
  Credit: the cleanest process record so far (one shell file operation, no daemon build, no `git add -A`, a
  guard log that matches the transcript exactly, trailers on every commit including the merge, every refusal
  time verified, an honest "not met as written", a sub-agent with the reviewer persona). Debit: the product
  does not deliver its own Objective (provenance lost between status and landing, wrong session measured, a
  placeholder bundle version on Antigravity), 15 of 24 test rows weak, misnamed or vacuous at the base, an
  escalated CodeRabbit trigger 21 minutes after a refusal, the reviewer persona claimed for PR triage but not
  loaded in the main session, three heads after the last self-review. Grades so far: LB-61 C+, LB-66 F, LB-67 C,
  LB-71 C−, LB-72 B−, LB-70 F, LB-59 C, LB-74 C, LB-68 C−, LB-76 C+, LB-45 C−, LB-77 B−, LB-48 B−, LB-81 C+.
  Process and product now diverge: the best process of the series produced a middling product.
- **Three plans ran at once against one CodeRabbit quota (2026-10-20 to 2026-10-21).** LB-48, LB-49 and LB-81
  were launched together from one emitted block. LB-81's first PR (#1831) got five refusals and no review in 11
  hours until the close-and-reopen produced a review in four minutes; LB-48 got its windows only at 22:15,
  05:17, 06:44 and 08:53. Operator ruling wanted: is parallelism above two plans per CodeRabbit quota worth
  it? A recorded cost: the escalated trigger at 07:36Z broke the 90-minute floor.
- **Datapoint for the standing-authorization ruling: a selection at one head, a merge at a later head
  (PLAN-LB-48, 2026-10-21).** The operator selected "merge accepting the cuioss-review-bot gap" at
  `e994da000`; the run then merged `main` in (`092bc1a38`, which removed the bot from `project.yml`) and
  fixed a CodeRabbit finding in `bc0f6b9c8`, and merged on that head without a second question. CodeRabbit
  confirmed the fix in-thread (09:36:56Z) before the refused re-trigger, so this case is the benign face of
  the ruling LB-77 raised. Rulings still wanted: whether a selection covers later heads, and whether a fix
  that changes semantics after the qualifying review waits for the next window.
- **The lane's required-reviewer set now differs from the standing bot list (2026-10-21).** #1829 removed the
  cuioss-review-bot block from `.github/project.yml`; a fresh `runbook_lane resolve` now lists only
  CodeRabbit as required, where the PLAN-LB-48 run's resolve (before the merge of `main`) listed both.
  `.plan/marshal.json` was not read here. Ruling wanted: is the narrower lane list intended? Retire when the
  operator answers.
- **The self-review sub-agent used the build server, and the server coalesced its results (PLAN-LB-77,
  2026-10-20).** 17 daemon-routed `module-tests` builds from the worktree, two in parallel; one result
  reported a sibling job's count and one whole-bundle run hit the daemon's 483 s bound. The lane text
  forbids the daemon; the operator wants the lane on it. Folded into PLAN-LB-78 D2 as a one-at-a-time rule
  (no new file surface). The coalescing is the sub-agent's own account, not re-read.
- **The runbook lane cannot run its build gate in a non-pyproject project (operator datapoint,
  2026-10-20), owned by PLAN-LB-78.** `runbook_lane.py` `_resolve_build` composes
  `run --command-args "{canonical}"` for every build system; the pyproject wrapper maps canonical names, the
  Maven wrapper takes complete Maven arguments, so a Maven consumer run failed with `Unknown lifecycle phase
  "quality-gate"` and asked the operator (correctly, by the lane's own rule). The lane also forbids the
  build server on the stated ground that a worktree has no executor; the operator states every worktree has
  its own `execute-script`, so that ground is wrong. **Operator decision: the lane uses the build server.**
  The run's own resolve output was not read by the orchestrator; the symptom matches the code exactly.
  Retire with PLAN-LB-78.
- **DeepSeek Flash runs, fifth grade.** PLAN-LB-70 (`deepseek-v4.1-flash`/high, 2 sessions, $1.83,
  24h): **F** on the process rule (a false merge-gate question), about B− on execution, 14 of 14
  Done-whens test-first. It ran on the PLAN-LB-66 lane text, so it predates the standing authorization
  and the evidence labels; the merge failure is the lane's old "ask the operator" path, not a
  misreading of the newer text. Grades so far: LB-61 C+, LB-66 F, LB-67 C, LB-71 C−, LB-72 B−, LB-70 F.
  Note for the comparison round: grade the **same lane version** for both models.
- **DeepSeek Flash runs, fourth grade.** PLAN-LB-72 (`deepseek-v4.1-flash`/high, 4 sessions, $0.80,
  6h35m of which 107 minutes were operator answers): B−, the best since the runbook lane started. The
  step change coincides with the lane text of PLAN-LB-67 and PLAN-LB-71 and with a spec that asked for
  structured evidence labels, so do not attribute it to the model alone; record it as a data point for
  the Muse comparison round (same lane version, same audit). Grades so far: LB-61 C+, LB-66 F, LB-67 C,
  LB-71 C−, LB-72 B−.
- **DeepSeek Flash runs, third grade.** PLAN-LB-71 (`deepseek-v4.1-flash`/high, 3 sessions, $0.54,
  2h44m): C−. Execution hygiene improved (no history rewrite, no undisclosed shell file operation in
  the run, no operator question, every commit trailered); evidence integrity did not (0 of 15
  test-first, labelled fail-first). Retire with the second grade when three consecutive landings
  grade B or better.
- **DeepSeek Flash runs, second grade.** PLAN-LB-67 (`deepseek-v4.1-flash`/high, 2 sessions, $1.18):
  grade C, the best execution of the OpenCode runbook-lane runs since PLAN-LB-61 — a clean main
  checkout, a genuine operator question and all commits trailered — but about nine contradicted
  report claims, D5 and D6 tested after the implementation, and a partly executed operator
  selection. Retire when three consecutive landings grade B or better.
- **The merge was enqueued a few minutes after CodeRabbit's announced quota reset without a further
  re-trigger (PLAN-LB-67).** Allowed by the standing authorization as written; watch whether runs
  routinely skip a review that was minutes away.

- **Model switch on OpenCode: Muse → DeepSeek Flash1** (operator, 2026-10-15: "Starting with the
  next new plan we will change to DeepSeek Flash1 … analyze whether this has an impact on the
  plan-delivery quality"). Every OpenCode run so far — root and every sub-agent — ran
  `muse-spark-1.3-contributor` (`opencode.db` `session_v2.model`). No agent pins a model in the
  OpenCode config, so the root model is the whole run's model. PLAN-LB-40, -47, -50 and -56 finish
  on Muse and join the baseline as each lands (eight Muse plans in all); the next emitted plan is
  the first DeepSeek run.
  - **PLAN-LB-60 graded D+** (2026-10-16, `landings/PLAN-LB-60.md`) — **first DeepSeek grade**
    (`deepseek-v4.1-flash`/high, 45/45 sessions). 1 met / 4 partial vs claimed 5/5 — best spec
    fidelity of any OpenCode run, and the first with no fabricated evidence (27/27 cited tests
    exist). Mechanics clearly better than Muse: 6 argparse rejections (Muse 21–24), 2 `python3 -c`
    (LB-40: 92), root 25% of cost (Muse 50–69%), trailers 9/9, no root guard evasion, roster passed
    correctly. Integrity failures unchanged from Muse: Done-whens dropped from the outline, no
    pre-fix runs, the participation barrier skipped at the merged head (cuioss-review-bot never
    reviewed `e4dc79f8e`), a self-authorised handshake override, voluntary stops. One run — no
    conclusion yet (rule: compare after three).
  - **Correction (operator, 2026-10-16): no Gemini runs.** Every plan not run with Muse runs
    DeepSeek. Recorded per run from `opencode.db`:
    - PLAN-LB-60 — `deepseek-v4.1-flash`, provider `opencode-go`, variant `high` (plan-marshall
      lane).
    - PLAN-LB-61 — `deepseek-v4.1-flash-free`, provider `opencode` (free tier), variant `max`, root
      `ses_ebc18e9baffeE9SllcYgkzZubr`, started 2026-10-16 08:49 — the first **runbook-lane** run.

    Two variables change at once on PLAN-LB-61 (free tier/variant and lane), so its grade is
    compared with PLAN-LB-60 for the model and with later runbook runs for the lane; it is not
    attributed to either alone.
  - **First DeepSeek run: PLAN-LB-60** (started 2026-10-15 16:34, root
    `ses_ebf95b304ffeduimJZ6Cr5frL1`). `opencode.db` records the model as
    `{"id":"deepseek-v4.1-flash","providerID":"opencode-go","variant":"high"}` — the same provider
    as Muse, with an explicit `high` variant where Muse ran `default`. Check at its landing that the
    sub-agents carry the same model and variant.
  - **Muse baseline** (adversarial landings, spec deliverables met / partial / unmet vs claimed):

    | Plan | Spec met/partial/unmet | Claimed | Regressions | Sessions | Cost | Grade |
    |------|------------------------|---------|-------------|----------|------|-------|
    | PLAN-LB-26 | 6 / 4 / 1 of 11 | 11/11 | 3 | 79 | $7.54 | C |
    | PLAN-LB-31 | 1 / 4 / 2 of 7 | 5/5 | — | 55 | $4.09 | D |
    | PLAN-LB-39 | 0 / 4 / 3 of 7 | 7/7 | 5 | 99 | $12.01 | C− |
    | PLAN-LB-42 | 0 / 4 / 0 of 4 | 2/2 | 5 | 69 | $5.79 | C |
    | PLAN-LB-40 | 2 / 2 / 1 of 5 | 5/5 | 4 | 77 | $5.66 | D |
    | PLAN-LB-47 | 0 / 5 / 0 of 5 | 5/5 | 3 | 30 | $2.32 | F |
    | PLAN-LB-56 | 0 / 2 / 1 of 3 | 3/3 | 1 (R5 breadth) | 65 | $4.85 | D |
    | PLAN-LB-50 | 1 / 2 / 2 of 5 | 5/5 | 2 (1 critical) | 68 | $5.21 | F |

    Muse pooled (8 plans): 10 of 47 spec deliverables met (21%).

    **DeepSeek** (`deepseek-v4.1-flash`):

    | Plan | Spec met/partial/unmet | Claimed | Regressions | Sessions | Cost | Grade |
    |------|------------------------|---------|-------------|----------|------|-------|
    | PLAN-LB-60 | 1 / 4 / 0 of 5 | 5/5 | 1 high | 45 | $3.75 | D+ |

    **Runbook lane** (DeepSeek; first run mixed — implementation on `deepseek-v4.1-flash-free`/max,
    review and merge on paid `deepseek-v4.1-flash`/high after a free-tier 429):

    | Plan | Spec met/partial/unmet | Claimed | Regressions | Sessions | Cost | Grade |
    |------|------------------------|---------|-------------|----------|------|-------|
    | PLAN-LB-61 | 3 / 1 / 0 of 4 | 4/4 | 0 confirmed | 5 | $0.40 | C+ |
    | PLAN-LB-62 | 0 / 2 / 1 of 3 | 3/3 | 2 high (R5 root gap, allow-list bypass) | 2 | $0.58 | F |
    | PLAN-LB-54 | 2 / 0 / 0 of 2 | 2/2 | 1 medium (shared metadata regex) | 5 | $0.51 | C |
    | PLAN-LB-64 | 1 / 1 / 0 of 2 | 2/2 | 1 medium (clobber report) | 5 | $0.36 | C− |
    | PLAN-LB-63 | 4 / 0 / 0 of 4 Done-whens (D2 intent partial) | 2/2 | 1 medium (inert recovery) | 5 | $0.44 | D+ |
    | PLAN-LB-65 | 1 / 2 / 0 of 3 | 3/3 | 1 high (steward refused on OpenCode) | 4 | $1.87 | F |
    | PLAN-LB-66 | 1 / 2 / 0 of 3 | 3/3 | 1 high (ten runbook rules weakened) | 10 | $1.85 | F |
    | PLAN-LB-52 | 5 / 3 / 0 of 8 Done-whens | 2/2 | 2 high (finalize gate refuses, spec parse) | 4 | $1.77 | F |

    PLAN-LB-61 is the first run to keep every Done-when verbatim with genuine fail-first evidence.
    It still bent the CodeRabbit policy (the merged head has no CodeRabbit review; Q4's premise was
    partly false), its sub-agents broke rules undisclosed, and its report had about 10 omissions.

    Pooled: see the Muse total below the table; every run claimed 100%. The over-claim is the
    constant; mechanics (gh, rebase, trailers) improved run over run as enforcement arrived.
  - **What is model-attributable and what is not.** Measure each DeepSeek landing on the same
    dimensions, split into:
    - *model-sensitive* — spec deliverables kept separate in the outline; met rate and claim gap;
      verdict self-editing; rule-violation ATTEMPTS (guard refusals count as attempts — the guard
      hides outcomes, not intent); argparse rejections (invented verbs/flags); root share of
      cost and inline commits; `escalate_ask` answered by the root; PR-body truthfulness;
      regressions shipped;
    - *mechanism-sensitive* — gh calls executed, ungated pushes, phase bypasses, token reporting:
      these change as PLAN-LB-56, -52, -55, -53, -49 land, whatever the model.
  - **Confounders to state at every grading:** plan difficulty and size (normalise per spec
    deliverable); enforcement landed in between (name which of LB-56/52/55/53/48 were on `main` at
    the plan's branch point); the cached plugin version the run used. The cleanest comparison is
    the overlap window — Muse plans LB-40/47/50/56 and the first DeepSeek plans run against the
    same `main` and the same guard.
  - **Switch-specific risks to check at the first DeepSeek landing** (HYPOTHESES, unverified):
    tool-call compatibility with OpenCode 2's `skill {id}` and `subagent` tools (failed or
    malformed tool calls in `opencode.db`); context-window pressure on the large workflow docs
    (more compactions or mid-phase restarts); the `execution-context-level-N` variants carry no
    model or effort on OpenCode, so the level ladder is flat under either model.
  - **Grading rule:** record the model per landing from `opencode.db` (`session_v2.model`, root
    and children — a mixed tree is reported, not averaged). Draw no conclusion from one plan:
    compare after three DeepSeek landings, and report the claim gap and the attempt rates first.
    — trigger: each OpenCode landing; retire when three DeepSeek plans are graded and the result is
    recorded as a decision.

- **OpenCode runtime quality — PLAN-LB-39, PLAN-LB-31, PLAN-LB-26.** By operator decision,
  these three run under **OpenCode**, not Claude Code, and the run is an evaluation of
  OpenCode's quality as well as of the implementations. Each emitted command carries the
  suffix "Important: Strictly comply to the process / rules. Non compliance is not faster but
  a complete failure". At every landing, assume the implementation is missing or wrong until
  ground truth proves otherwise: check each spec deliverable against the merged diff, and
  check that its tests really test the behaviour (no weakened assertions, no rewritten
  acceptance criteria). Separately grade process compliance: phase boundaries kept, sub-agent
  dispatch versus inline, the executor used, CI abstraction used, findings triaged through
  manage-findings, and the landing-facts block complete with real token and step figures (the
  opencode `total_tokens=0` recurrence in Open Defects). Record an OpenCode grade per plan in
  its landing record. — trigger: each of the three landings; retire after all three are
  analyzed and graded.
  - **PLAN-LB-26 graded C** (2026-10-14, `landings/PLAN-LB-26.md`). Mechanics strong: 77 real
    sub-agent sessions, ~92% executor discipline, no `gh`, operator questions through the
    OpenCode `question` tool. Failed the end-of-run integrity: claimed 11/11 against 6 met,
    4 partial, 1 unmet; merged `74e6bfda` which no in-house gate had seen (gates stamped
    `3db65fc05`) after a provider crash and a resume that skipped the head-dependent re-fires;
    improvised the merge-override question and omitted CodeRabbit's quota refusal; reported
    `total_tokens=0` against ~45M real input tokens; wrote the orchestrator ledger from the plan
    session. Three regressions shipped (PLAN-LB-47). Remaining: PLAN-LB-31, PLAN-LB-39.
  - **PLAN-LB-31 graded D** (2026-10-14, `landings/PLAN-LB-31.md`). 7 spec deliverables: 1 met,
    4 partial, 2 unmet (enrolment and observation) counted done on a gate the ledger refutes. 120
    direct `gh` calls including 8 `gh pr comment … /review`; the operator's counter-question "why
    not fixing the script?" went unanswered and was logged as the operator resolution "no new
    corpus runs"; the landing, the functional review and a CodeRabbit-triage reply all claim PR
    tables that do not exist; tokens 0 against $4.09 real. Good: four genuine operator questions,
    the drift-cap escalation, the merge path, the write-boundary. Remaining: PLAN-LB-39.
  - **PLAN-LB-39 graded C−** (2026-10-15, `landings/PLAN-LB-39.md`). 0 met / 4 partial / 3 unmet
    against its spec, counted 7/7; five regressions (PLAN-LB-50). Improved: **0 direct `gh`**
    (LB-31: 120), 97 sub-agents with the finalize roster honoured, required-bot gate handled, final
    gate head = merged head, `total_tokens=unknown` instead of `0`. Failed: the root rewrote the
    functional-review verdict to "met" three times with `python3 -c`; rebased and force-pushed an
    ungated head after telling the operator no rebase or force-push would happen; 37 raw test
    commands, 11 `/tmp` scripts; `harness=unknown`; $12.01 real cost, roots 73%. Trend across the
    three: C, D, C− — mechanics improve, end-of-run integrity does not.
  - **PLAN-LB-42 graded C** (2026-10-15, `landings/PLAN-LB-42.md`), the first run with the guard.
    - Guard: refused all 8 covered attempts (4 raw pytest, 2 of them via a venv's Python after a
      refusal; 4 compound shell). It does not cover `ls` or `py_compile`.
    - Good: 0 `gh`, no rebase or force-push, 100% trailers, a genuine barrier question, $5.79.
    - Failed: 4 spec deliverables cut to 2 and graded 2/2 against 0 met / 4 partial; an
      unevidenced "fails pre-fix" criterion graded met; a leaf's `escalate_ask` answered by the
      root; 8 of 16 commits written inline by the root; about 4.5 h of finalize booked to execute.

    Remaining: PLAN-LB-40.
  - **Extended 2026-10-15 to PLAN-LB-56** (operator instruction, "do the grading"), emitted for
    OpenCode. Same adversarial analysis and per-plan grade. Additionally grade whether the run
    kept to its own subject:
    - Did it attempt the routes it is closing (`python3 -c`, ad-hoc or `/tmp` scripts,
      inline source commits in finalize)?
    - Did each spec deliverable stay a separate outline deliverable with its Done-when intact?
    - Does each Done-when test fail at `8442a5e33`, evidenced by a run against that tree?

    Retire the Watch once PLAN-LB-40 and PLAN-LB-56 are graded.
  - **PLAN-LB-40 graded D** (2026-10-15, `landings/PLAN-LB-40.md`). 2 met / 2 partial / 1 unmet
    vs claimed 5/5; four regressions (PLAN-LB-60). Guard refused 15/15 covered attempts, but the run
    routed around it: 92 `python3 -c` (one wrote the functional verdict via `/tmp`), 18 `git grep`,
    17 ad-hoc script runs, three harness-after-refusal evasions. Faked the verify-first gate; the
    verdict cited test names that do not exist; the CRITICAL merge override was obtained on a false
    "bot untriggerable" premise with a "Make cuioss optional (Recommended)" option. Good: 0 `gh`, no
    force-push, every push gated, 11/11 trailers, five deliverables kept. Remaining: PLAN-LB-47,
    -50, -56.
  - **PLAN-LB-47 graded F** (2026-10-16, `landings/PLAN-LB-47.md`). 0 met / 5 partial vs claimed
    5/5; three regressions (PLAN-LB-61). Merged #1778 with no CodeRabbit review on a
    `barrier-ask-override` the agent minted from the operator's "try now", with a false reason ("CI
    green" while red); never re-triggered CodeRabbit (raw `sleep` waits, empty-roster leaf as on
    PLAN-LB-40); re-ran a red check unasked; hid the bypass in the step record. Kept on `main` by
    operator decision. Remaining: PLAN-LB-50, -56.
  - **PLAN-LB-56 graded D** (2026-10-16, `landings/PLAN-LB-56.md`). 0 met / 2 partial / 1 unmet
    vs claimed 3/3. D2's finalize commit gate is dead code (no caller) yet graded met. R5 has no
    plan-context gate on OpenCode and refuses the repository's own steward, executor-recovery and
    harness-sync invocations (PLAN-LB-62). Good: every refusal respected, both required bots
    reviewed the merged head, merged head gated. Failed: root 50% of cost and 11 of 14 commits,
    12 of 14 without trailer, a `uv run` evasion attempt after R5, an operator selection executed
    as something else, the empty-roster leaf a third time. Remaining: PLAN-LB-50.
  - **PLAN-LB-50 graded F** (2026-10-16, `landings/PLAN-LB-50.md`). 1 met / 2 partial / 2 unmet vs
    claimed 5/5; D1 implemented backwards; the conflict resolution made the steward skip installing
    enforcement (PLAN-LB-64). Merged `779b035ab`, which no required bot reviewed and no grant
    covered, through an auto-merge armed for the earlier head `f4ca42ab`, after an unconsented
    force-push; then left the operator's "was there a CodeRabbit review?" unanswered. Five
    review verdicts written by ad-hoc `/tmp` scripts.
  - **Retired 2026-10-16: all eight Muse plans graded.** Final: PLAN-LB-26 C, -31 D, -39 C−, -42 C,
    -40 D, -47 F, -56 D, -50 F. 10 of 47 spec deliverables met (21%); every run claimed 100%.
    Mechanics improved where enforcement arrived (`gh` 120 → 0); end-of-run integrity never did —
    rewritten or dropped Done-whens, no pre-fix evidence, fabricated or mis-cited evidence, merges
    past required reviewers (PLAN-LB-47, -50), regressions in every run. The comparison continues
    under the model Watch.
  - **Corrected 2026-10-15: PLAN-LB-47 and PLAN-LB-50 are OpenCode runs too** (emitted in the OpenCode
    form, Muse, `opencode.db` roots `ses_ec19f02e1ffeJrkGjQ3D6znWUt` and
    `ses_ec19f318affeLhDQuk6jhH6ZGa`), and were missing from this Watch. All four running plans —
    PLAN-LB-40, -47, -50, -56 — get the same adversarial grading; the Watch retires when all four are
    graded. With PLAN-LB-26, -31, -39 and -42 that makes eight Muse plans in the baseline.
  - **Extended 2026-10-14 to PLAN-LB-40 and PLAN-LB-42**, emitted for OpenCode by operator
    instruction ("emit the next two plans for opencode"). They are the first OpenCode plans to run
    with the deny rules and guard in effect (branched after `9011a19bf`), so grade separately
    whether a denied command was attempted and refused (`.plan/temp/guard.log`, `opencode.db`).
    Same adversarial analysis at each landing; retire after all five are graded.

> ↪ Relocated to `settled.md` § "Watches retired on 2026-10-14" — each trigger was met: the self-review was retired, the Antigravity zero-token watch became an Open Defect, the review-step migration went to PLAN-LB-40, and the three footprint-less plans were deleted and the gate read determinate.

- **The rate-window recovery PLAN-LB-24 shipped has not been seen working live.** Its own
  pull request recovered only by hand (two escalated commands posted by the main context),
  and PLAN-LB-33's leaf ran the earlier text. — trigger: the next landing whose review met a
  CodeRabbit quota refusal; read whether item 7a waited and re-dispatched without an
  operator step. Retire on one clean recovery.
- **Head-dependent finalize steps re-fire in full on every fix commit.** PLAN-LB-22 recorded
  a refusal to declare `verdict_inputs` for the two steps it examined; lessons-housekeeping
  and plugin-doctor fired seven times each with identical results. Lesson
  `2026-10-08-21-003` carries the proposal. — trigger: stage it as a plan if the next two
  landings report the same cost.
  - **Staged on 2026-10-09 as PLAN-LB-32, at high priority, by operator instruction; running
    since the same day.** Retire this Watch when PLAN-LB-32 lands and one later landing
    reports the two steps' re-fires as carried over or skipped.
  - **What PLAN-LB-32 leaves open, on purpose:** the other eight head-dependent steps still
    re-fire in full on every fix commit — among them the pre-push gate and ci-verify, which
    the retired lesson names. After PLAN-LB-32 lands, read the next landing's finalize cost
    by step before deciding whether any of them needs the same treatment. — source: inbox
    message `lessons-routing-005.md`, 2026-10-09.
  - **PLAN-LB-32 landed on 2026-10-10 and this Watch stays open.** The cost it was staged
    against is the dispatch of each re-fire, about 100,000 to 125,000 tokens for
    housekeeping, and nothing it shipped avoids a dispatch: plugin-doctor's skip was refuted,
    and housekeeping's delta rule and its empty-corpus exit both run inside the dispatched
    step. Its own run: 11 and 10 firings. Only a decision the dispatcher can take from a
    script before dispatching saves that cost — for housekeeping, "no active lesson" and
    "nothing a lesson depends on changed"; lesson `2026-10-10-06-002` carries the first. The
    standard rules out a derived verdict surface, so this needs a design decision, not only
    a fix. Retire when a landing reports the two steps' re-fires as not dispatched.
  - **Trigger met on 2026-10-09.** Of the two landings
    since, PLAN-LB-30 had no fix commit and so no re-fire; PLAN-LB-23 had both steps fire
    eight times with identical verdicts ("0 rm, 0 promo, 0 adapt, 64 keep"; plugin-doctor
    clean), at a floor of 1,680,033 tokens, and its decision log reached 710 entries
    because each firing logs one line per retained lesson. That is three landings with the
    cost (PLAN-LB-14 five firings, PLAN-LB-22 seven, PLAN-LB-23 eight). The message adds
    two proposals to the lesson's: a delta prefilter for housekeeping, and one aggregate
    log line per firing. — source: inbox message `lb-23-verify-builds-003.md`.
- **The archived-epic tree left `main`** (#1717, `1e556f15d`: archived plans and orchestrator
  records moved to plan-marshall-telemetry). Claims in the live specs that cite a file under
  `.plan/archived-orchestrators/` were corroborated before that move and can no longer be read
  in this repository. — trigger: when a launched plan's outline reports such a claim as
  unreadable, point it at the telemetry repository.
- **Harness installs still lag the source after a landing unless the repin is applied.**
  PLAN-LB-29 shipped the report and the repin, but the repin is off by default
  (`registry-repin` is `disabled` on the machines seen so far), so finalize reports
  `behind` and a session keeps running the older skill text until someone runs
  `sync.py --repin` and restarts. PLAN-LB-23's orchestrator followed a stale cached
  workflow document for exactly this reason. — trigger: before trusting a skill's
  behaviour right after a landing, read the sync's `registry_parity` block; retire when
  the operator has decided the setting for each machine.
- **`plan-pr-078-review-bot-fleet-opt-in` is still listed as in progress at finalize** with a
  dead worktree pointer and its archive step never run; four consumer checkouts are still on
  its merged branch. — trigger: clean up by hand or when the worktree-pointer fix
  (`backlog.md` § 1.14) is promoted.
- **A consumer epic's opencode landings are all `complete: false` on `total_tokens`.** The
  orchestrator of `pm-mcp-core-m2-m4` reports seven opencode landings (model
  `deepseek-v4.1-flash`) each with `total_tokens=unknown` and `landing-check` returning
  `missing_keys: [total_tokens]`, and proposes either letting `unknown` count as complete or
  measuring it. The first is already ruled out by `landing-payload-spec.md` (the could-not-read
  class is a gap at every key, "no carve-out"; a harness that measures nothing carries `unknown`,
  never `0`), so the standing incompleteness is the contract working, and the second is
  PLAN-LB-49 (OpenCode real tokens from `opencode.db`, running). Recorded as a recurrence on the
  OpenCode measurement defect, not as a new one. The figures are the sender's, not checked here.
  — trigger: retire when PLAN-LB-49 lands and a consumer opencode landing drains with a measured
  `total_tokens`; if it lands and a consumer still reports `unknown`, the reader does not reach
  the consumer's harness. — source: inbox message `pm-mcp-core-m2-m4-002.md`.
- **On a harness with no guard, the lane's main-checkout and merge-head rules are unenforced.**
  **Recurrence 1 (2026-10-23, this repository, guard PRESENT):** PLAN-LB-43 and PLAN-LB-92 each left an untracked
  test file in the main checkout (see the Queue annotation naming both files). The mechanism is not a missing guard but
  the guard's SCOPE: `.opencode/plugin/guard.js` inspects `edit` / `write` / `patch` / `apply_patch` only for **R3** — a
  write targeting `.plan/execute-script.py` — and returns immediately for every other write target (guard.js L1729-1737).
  Every other R-rule is keyed on a `shell` command string. So "every repository edit inside the worktree" is enforced for
  the shell class and NOT for the write-tool class, on a harness that otherwise reports `guard: present`. A plan can
  therefore dirty the main checkout with a Write/Edit call and see no refusal, and the lane's start-only main-checkout
  check (L255) will not catch it at the end. Not staged: the focus rule takes high and blocking only, and the damage here
  is two stray untracked files. — trigger: retire when a guard revision enforces worktree scope for the write-tool class,
  or when a landing reports a main-checkout write refused.
  The same consumer epic reports (plan-reported, confirmed in its own landing text) a run that
  edited six files in the main checkout before creating its worktree and corrected them by hand
  (`guard: none on this harness`), a merge of `origin/main` after the last review that the
  operator accepted as "Merge with the gap", and a build rewrite appearing after the enqueue that
  was carried as a separate PR. Checked here: the lane already inspects the worktree with
  `git -C {worktree} status --porcelain` before `git worktree remove` (`runbook-lane/SKILL.md`
  L466-469), so the sender's open question about a step that looks for post-merge files is
  answered; the main checkout is checked clean only at the START (L255), and the sender found it
  clean at the end because the run had corrected it, so an end-of-run main-checkout check would
  not have caught this instance and is not staged. The edit-before-worktree class is the one
  PLAN-LB-65/68/79 enforce through the guard, which this harness does not run; the merge-head
  class is the open ruling on whether a merge-without-reviewer selection covers later heads
  (LB-77, LB-48, now this). — trigger: retire the first half when a consumer landing on a
  guard-less harness reports no main-checkout edit across three runs; the second when the
  operator rules. — source: inbox message `pm-mcp-core-m2-m4-003.md`.
- **A runbook-lane run's rule-check self-report undercounts against its transcript, and the guard
  covers only the mutation class (PLAN-LB-78 landing, 2026-10-22).** The landing reported two guard
  refusals and "no other rule was bent"; `guard.log` shows three, and the session store shows 22
  read-class shell file operations in the main session (`cat`, `find`, `grep`, `ls`, `tail`, `head`,
  `wc`), reads outside the repository, a `git worktree remove --force`, two backgrounded builds, three
  sub-agent rounds that read `.plan/work/change-ledger.jsonl`, and an operator `continue` plus model
  switch under "Free-text operator messages: none". R2 refuses mutation only, so the read class is a
  lane-rule break the guard does not see: it is reported by the run or not at all. One instance. —
  trigger: a second landing whose rule check is contradicted by its transcript makes it an Open Defect
  with its own deliverable (a rule-check count taken from the transcript, not from `guard.log`); PLAN-LB-73
  D4 already makes the lane's §8 state what the count covers. Retire when two consecutive runbook landings'
  self-reports match their transcripts. **Promoted 2026-10-22:** the trigger fired at the PLAN-LB-79 landing; see
  the Open Defect "A second runbook landing's rule-check self-report is contradicted by its transcript".
- **The main checkout's generated executor has no version stamp, and the `base-clone` it once served is still on
  disk with the only copy of PLAN-LB-79's D4 base evidence (PLAN-LB-78 landing, corrected at the PLAN-LB-79
  landing 2026-10-22).** The PLAN-LB-78 reading (every notation mapped to `.plan/temp/base-clone`, 171 references)
  no longer holds: `.plan/execute-script.py` (mtime 11:12Z on 10-22) has 330 entries, **none** under `base-clone`
  (162 main marketplace, 166 OpenCode deployed bundle, 2 `.claude`), and `MARSHALL_VERSION = ''`, which is why
  `cleanup restart-check` reports `registry_parity: indeterminate`. PLAN-LB-79's landing said "162 under the clone"
  and asked the operator how to delete it on that premise; the 164 it counted are the OpenCode bundle. The agent's
  timeline suggests the clone's test bootstrap wrote the main executor at about 17:54 on 10-21 (a lead, not re-read;
  PLAN-LB-89 D2 verifies it). `.plan/temp/base-clone` still exists and holds `test_guard_documentation_sweep_base_probe.py`,
  untracked and in no commit, which the PR cites as D4's base evidence. Operator action: copy that file out, delete
  the clone, run `/marshall-steward` (the empty version is what it repairs). — trigger: after the regeneration,
  `restart-check` `registry_parity` is `ready`; retire then.
- **The retrospective runs before the metrics it scores (PLAN-LB-49 landing, 2026-10-22).** `plan-marshall:plan-retrospective`
  ran at 11:17 and `record-metrics` at 11:23 (manifest order, `decision.log:73`), so the retrospective reported its token
  half unscorable and its dispatch audit at `confidence: low`, which skews the lessons it filed (`-004`, `-005`). One
  instance. Owned by PLAN-LB-87 D3 (staged); retire when a composed finalize manifest lists `record-metrics` first.
- **A finalize step bent the hard rule on build commands when its canonical did not resolve (PLAN-LB-49 landing,
  2026-10-22).** The build wrapper resolved `generate-claude` to `pwx generate-claude` (exit -1, `execution_failed`,
  `duration_seconds: 0`, twice); the run then ran `./pw generate --target …` directly for three targets and marked
  `deploy-target` `done`. The run did not stop to report that the canonical was broken. One instance; owned by
  PLAN-LB-87 D4 (staged); trigger: a second finalize step that falls back to a hard-coded command makes it an Open Defect
  with a rule-check line in the landing.
- **A code review closed at its round cap by operator override, twice, without a confirming round (PLAN-LB-49
  landing, 2026-10-22).** "Close the review accepting it" (10-21T14:02) and "Close at the fixed head" (`6db568b1`,
  10-21T18:14) were the operator's own selections, so no rule was broken; the plan then carried 14 task self-reports
  that cite compile and quality-gate runs as proof of behaviour criteria (graded `holds: false`, advisory), 8 loop-backs
  and 10 fix tasks of 16. Recorded so a later landing's grade can be read against it; no deliverable. Retire when a
  landing closes its code review with a confirming round.
