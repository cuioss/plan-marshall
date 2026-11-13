# Settled narrative — live-blockers

Relocated verbatim from `epic.md` by `cleanup`; each origin keeps a pointer naming its heading here.

## Decisions settled by the regrouping and the shipped plans

- 2026-10-07 — **parallelization_scope set to 2** (operator choice over the project default
  of 1). Most plans share finalize files, so truly disjoint pairs will be limited; two lets a
  CI or review-bot plan run beside a finalize plan.

- 2026-10-07 — **Specs re-drafted, not copied.** Where an earlier epic already had a spec for
  the same fix, its analysis was reused but every claim was re-read against HEAD and the scope
  cut to what removes the blocker, because the source specs were up to three weeks stale and
  bundled unrelated deliverables. Each spec names the source plan ids it carries forward.

- 2026-10-07 — **Decomposed into 5 workstreams and 21 staged plans.** Spec bodies were drafted
  by five read-only agents against HEAD `6edefac32` and adjudicated here: all 21 resolve a
  declarative surface with no unresolved entry, none exceeds five deliverables, and none was
  found already fixed. Scope-bloat guard: no split needed. Two specs were amended after
  drafting — PLAN-LB-14's store figures (measured while the archived root was missing) and
  PLAN-LB-11 (the #1700 deletion as evidence).

- 2026-10-07 — **`.plan/archived-orchestrators/` restored.** PR #1700 had deleted all 2038 files
  of the archived-epic tree from `main` as a side effect of a five-file fix. Restored
  byte-identical from `78ba60f41^` in the ledger worktree before the eight closed epics were
  archived into it. Not confirmed with the operator as accidental at the time of writing.

- 2026-10-07 — **Integrated two parallel ledger landings (#1706, #1707)** that touched
  `post-run-quality` and `process-compliance` after this epic's base. The local commits were
  rebased onto them; the changed files were verified byte-identical in the archived trees, the
  two generated views were restored from the closed-state render, and both history files gained
  a "Landed in parallel with the close" section. Consequences here: `PLAN-LB-04` carries two new
  recurrences as evidence; issue #1697 is fixed (struck in `backlog.md` § 3.3).

- 2026-10-07 — **process-compliance `PLAN-17` not adopted, flagged.** That epic's session had
  emitted `PLAN-17` and `PLAN-19` under an operator "land now" override; neither was launched.
  `PLAN-19` is `PLAN-LB-06`. `PLAN-17` (clean-checkout assertions against concurrent ledger
  writes) was ranked medium in the sweep and sits in `backlog.md` § 1.15. Whether to stage it
  here is the operator's call, given the earlier land-now intent.

- 2026-10-08 — **Ledger worktree fast-forwarded to `main`** (`6c676de29` to `64b573110`) by
  operator instruction, after it was found three commits behind with nothing pending. Three
  leftover directories under the active root holding only an ignored `logs/decision.log`
  (`post-run-quality`, `process-compliance`, `truthful-signals`) were removed on the same
  instruction; their tracked trees are in the archived root.

- 2026-10-08 — **Cleanup run by operator instruction, then landed.** Re-grounding covered the
  eleven live specs at `726ca857a`; the twenty superseded specs were not re-grounded, because
  every claim they hold is carried, and now verdict-stamped, in a successor. Nine contradicted
  claims were re-scoped in place: the original text is kept and a dated note states what is
  true and what it changes for the plan. No spec was found already fixed, none lacks an
  objective, a surface or claim labels, and no relocation to `settled.md` was proposed (no
  subject of this epic is closed yet). The inbox drain was refused as the workflow requires.
  Restart verdict `indeterminate`, for one reason: the epic has no `inbox/` directory yet.
  - Deviation, recorded: the eleven verification agents were each allowed to write one result
    file under `.plan/temp/`, and the verdicts were stamped from those files by a driver that
    calls `corpus set-verdict` once per claim. No agent wrote to the ledger.

- 2026-10-09 — **PLAN-LB-32 staged as its own plan, at high priority, by operator
  instruction** ("Stage it as a high prio plan. Consider adding it to another one as well if
  sensible"). It makes a re-fire of the two project steps cheap: a re-fired step reads what
  changed since its last firing, re-examines only that, carries the rest over and logs one
  line. Seven deliverables.
  - Not built as a `verdict_inputs` declaration, which is what the lesson and the Watch
    proposed. Read at `97f341b6c`: the mechanism admits static path globs only, no step
    declares one, and both steps carry a reasoned refusal — housekeeping reads a git-ignored
    corpus and plan records, plugin-doctor's rules read link targets and agent files across
    the repository. PLAN-LB-22 was asked for the declaration and shipped the refusal. A plan
    asking for it a second time would end the same way.
  - Adding it to an existing plan was considered and not chosen. PLAN-LB-25 and PLAN-LB-27,
    the two plans on neighbouring ground, hold ten deliverables each, so seven more would
    pass the authorized twelve; and both wait behind PLAN-LB-24 on shared files, which would
    hold a high-priority fix back. The fold went the other way: two items PLAN-LB-27 named
    as "not fixed here" — the plugin-doctor gate reading the declared footprint, and the
    housekeeping step reading a retired field — are deliverables of PLAN-LB-32, because they
    sit in the two documents it rewrites. PLAN-LB-27's spec says so.
  - Scope-bloat guard: seven deliverables, above six, proceeding unsplit on the operator's
    authorization of up to twelve.

- 2026-10-09 — **Cleanup run by operator instruction, after the second drain; not landed, on
  the same instruction.** Re-grounding covered the six staged specs (PLAN-LB-25, 26, 27,
  28, 31, 32) at `4ed67e228`; PLAN-LB-24 is running and was excluded, and shipped and
  superseded specs were not re-grounded. 159 verdicts were stamped: 145 corroborated, 5
  unverifiable, 9 contradicted and re-scoped in place.
  - PLAN-LB-25 and PLAN-LB-26: nothing contradicted and no deliverable already done.
    PLAN-LB-23 did not do PLAN-LB-26's bounded-wait deliverable: the daemon route still
    loops without a bound and the five documents still disagree.
  - PLAN-LB-27: two hypotheses refuted. A finding of a new type does not reach the Step 11
    triage, whose read sweeps `test-failure` and `lint-issue` only, so the type choice in
    its first deliverable must also settle how the finding is read; and the residual is
    already kept in the result when persisting fails. Its surface gained two conditional
    entries (`verification-feedback.md`, `_task_artifacts.py`); the first now overlaps
    PLAN-LB-24.
  - PLAN-LB-28: its Maven half holds unchanged. In its self-review half three observed
    claims are no longer true after #1726 and #1718: the verifier no longer refuses a clean
    full-surface round on structural grounds, an operator close exists, and the verdict set
    has six members. Its third self-review deliverable shrinks to reporting the files no
    check covered. One hypothesis was refuted: a Maven parser fix does reach routed builds.
  - PLAN-LB-31: two claims re-scoped (two pull requests are named in the old ledger after
    all; the enrolled repositories' pins have moved to v0.40.0 and v0.37.0), and a stale
    deliverable number corrected. The schema failures that held thirteen repositories back
    reportedly no longer fail under the released schema.
  - PLAN-LB-32: all sixteen observed claims hold. One hypothesis refuted — a lesson has no
    reliable last-changed time, so its second deliverable uses a content hash — and two
    verify-first clauses now carry what was read: the existing `classify` subcommand
    returns before the diff for both steps, and the helper it wants to reuse sits in a
    file a plain import cannot name.
  - No spec was found already fixed; none lacks an objective, a surface or claim labels.
    No duplication finding: the cross-check shows no new overlap except the one above.
    No relocation to `settled.md` was made: the judgement was deferred, because the
    operator was not asked in this run.
  - Ledger compaction: both invariants hold; the view was regenerated. The inbox was
    drained by the analyze verb before this pass; the cleanup's own archive phase refuses
    by design. Restart verdict `not_ready`: PLAN-LB-24 is running. Registry parity reads
    `indeterminate` on this machine (the registry pins 0.1.1890, the executor states
    0.1.1888).
  - Deviation, recorded, as on 2026-10-08: the six verification agents each wrote one
    result file under `.plan/temp/`, and the verdicts were stamped from those files by a
    driver that calls `corpus set-verdict` once per claim. No agent wrote to the ledger.

- 2026-10-09 — **PLAN-LB-33 staged at high priority by operator instruction** ("stage both.
  consider into which plan"): the two Open Defects on per-task test scope and on the main
  executor, as one plan of ten deliverables in WS-02, labelled a weak merge and licensed to
  split at outline between deliverables 6 and 7.
  - Folding into an existing plan was considered for each half and not chosen. The test
    scope is closest to PLAN-LB-26, which works on the same execute loop, but that plan
    holds eleven deliverables and five more would pass the authorized twelve. PLAN-LB-28
    was the other candidate; it is already a weak merge of two subjects and shares no file
    with the resolver. The executor half belongs with the plugin-doctor step document, which
    PLAN-LB-32 is rewriting and which is running, so nothing can be folded into it; no
    staged plan declares the executor generator or its template.
  - The two halves are one plan and not two because of the fixed cost of a landing in this
    epic: 13 to 17 million tokens each, more than half in finalize.
  - Read at `fcd54e6ef` before drafting. The resolver's registered targets are bundle
    names only, while the build wrapper accepts any directory under `test/`; a narrow
    target has its own duration key, starts unmeasured and is classed orchestrator-tier on
    first use. For the executor: the generator writes wherever the working directory
    resolves, two callers pin it and the plugin-doctor step does not; the bootstrap's cache
    recovery walks one directory level short of the installed layout; and the executor
    drops empty-string arguments, which is the executor half of the domain-narrowing defect.
  - Scope-bloat guard: ten deliverables, above six, proceeding unsplit on the operator's
    authorization of up to twelve.

- 2026-10-09 — **Self-review surfacers for every domain staged as three plans, by operator
  instruction** ("I meant the self-review surfacer. This is the most important one. For all
  domains"). PLAN-LB-34 builds the foundation and the Java surfacer; PLAN-LB-35 adds
  JavaScript and Python; PLAN-LB-36 adds documents, containers and requirements, settles
  what happens to a file no domain claims, and ends with a table accounting for every
  domain key. PLAN-LB-34 is the top priority of the epic; 35 and 36 wait for it and may then
  run together.
  - This revives work the retired `truthful-signals` epic had specified and never ran:
    PLAN-TRUTH-181 (foundation) and PLAN-TRUTH-182 to -185 (Java, Python, JavaScript,
    documents), requested by the operator on 2026-09-26 and dropped at this epic's cut on
    2026-10-07, when PLAN-LB-03 kept only the first third of the foundation as a stopgap.
    The five specs were read from git history at `1e556f15d^`; their designs are carried,
    re-read against `fcd54e6ef`. Containers and requirements had no earlier spec.
  - **PLAN-LB-28 was split.** It was a weak merge licensed to split; its self-review half
    (deliverables 5 to 8, from PLAN-LB-03) moved to PLAN-LB-34 with its ten surface entries.
    PLAN-LB-28 is the Maven plan only and now shares no file with any live plan.
  - Why three plans and not one per domain or one for all: six surfacers plus the
    foundation is far above twelve deliverables; one plan per domain would pay the fixed cost
    of a landing seven times. The foundation carries Java because Java is where the gap was
    reported and a real second surfacer is the test that the foundation works. The other
    five split by kind — programming languages, and document-like domains — and sit in
    separate bundles, so the two later plans share only the class table of the standard.
  - What changed since the earlier specs, read at `fcd54e6ef`: since #1726 a round over a
    diff the one surfacer classes entirely as `other` closes as clean instead of looping, so
    an unreviewed Java change now passes quietly — read from the verifier rule, not observed
    on a consumer run. The workflow is wired to the one surfacer by name in five places, and
    several of its checks are worded for Python. The behavioural check over changed code
    that #1726 added exists for Python only.
  - **Three design decisions, taken by the operator on 2026-10-09** and written into the
    specs: (1) surfacers are routed per domain, through the resolver triage uses, so a
    repository runs only the surfacers of the domains it enabled; (2) the `-cui` bundles
    contribute no detectors and are covered by their base domain's surfacer; (3) no
    last-resort surfacer for files no domain claims — "not for now, we start with the
    others" — so such files stay reported as not covered, PLAN-LB-36 lists the deliberately
    uncovered types and counts them, and the last-resort surfacer is deferred, not rejected.
  - Scope-bloat guard: 11, 8 and 9 deliverables, each above six, proceeding unsplit on the
    operator's authorization of up to twelve.

## Open Defects closed by PLAN-LB-33 and PLAN-LB-38

- **The main checkout's executor can be left pointing into a worktree that no longer
  exists.** After PLAN-LB-23 moved back to the main checkout, `.plan/execute-script.py`
  failed with `ModuleNotFoundError: plan_logging`: its bootstrap paths pointed into the
  removed worktree of the standalone self-review run, and the plugin-cache self-heal did not
  recover it. The plan's orchestrator regenerated it from its own worktree's executor. What
  wrote the main copy from another worktree is not established; the self-review run had
  reported that a test run regenerated it. Until fixed, removing any worktree can break the
  main checkout's executor, and the recovery is a regeneration. Adjacent to PLAN-LB-29
  (running), which reads the executor version but does not own this. Lesson
  `2026-10-09-13-004` carries the proposal. — source: inbox messages
  `lb-23-verify-builds-009.md` and `-014.md`, 2026-10-09; reported by the plan's
  orchestrator, not reproduced here.
  - **Closed by PLAN-LB-33 (#1745):** a generation from another checkout is refused and
    leaves main's executor byte-identical (`cross_checkout_refusal`), and an orphaned
    executor recovers from the cache or the checkout's sources. Remove this entry at the next
    cleanup. The template format went from 4 to 5, so every existing executor reads stale
    until it is regenerated.

- **Four review-gate defects have no owner.** Handed over from retired lessons, seen in
  consumer repositories, none re-checked in code: (1) `github_re_review re-review
  --bot-kind cuioss-review-bot` reported a match on a CodeRabbit review, so a re-review
  awaited for one bot is satisfied by another's (`2026-10-05-17-001`); (2) a bot that edits
  its summary comment in place gets a second pending finding on every pre-merge re-fetch,
  which blocks the merge until resolved by hand (`2026-10-05-14-006`); (3) the `CodeRabbit`
  commit status is in the CI-complete check set, so a slow or rate-limited bot is reported
  as a CI timeout (`2026-10-05-14-007`); (4) nothing compares the planned footprint with a
  required bot's size cap before the pull request is created (`2026-10-04-09-001`).
  PLAN-LB-24 (running) owns the review step; read against its objective and first four
  deliverables only, none of the four was found there. Decide at its landing whether they
  go to PLAN-LB-25, a follow-up plan or the backlog. — source: inbox message
  `lessons-routing-007.md`, 2026-10-09.
  - **PLAN-LB-24 landed (#1742) and owns none of the four.** Its review row for the
    in-place edit (2) is related but different: it drops an acknowledgment, not an edited
    summary. The four stay unowned, joined by five from the landing itself, all in the same
    review step: (5) a stale quota notice settles a required bot that never reviewed — the
    stale check runs before every window and trigger branch and reads the notice alone, so
    the next pass settles it again until the loop-back ceiling (lesson `2026-10-10-20-001`,
    observed on #1742); (6) CodeRabbit's "review in progress" summary that names the head is
    credited as a head-verified review — the matcher applies no participation marker
    (`2026-10-10-20-002`, observed twice on #1742); (7) "Full review triggered/finished" is
    stored as a finding and is an eligible answer, case-sensitive match at
    `github_re_review.py:1734` (`2026-10-10-20-003`, observed on #1742 and #1745); (8) a
    "fixed" reply is released when the fix commit is on the branch, before verify is green;
    (9) the rate-window wait gives up exactly when the claim expires (3600 s each, no grace)
    and the jittered wake the spec asked for was dropped. **Owned by PLAN-LB-38 since
    2026-10-11** (deliverables 2–10); remove this entry when it lands.
  - **Defect (1) seen live on #1751:** the `cuioss-review-bot` re-review returned `matched: true,
    head_sha_verified: true` on a review written by `coderabbitai[bot]` (empty body, head
    320a1b7); the verdict held only because a later read credited the bot's own comment.
    PLAN-LB-38 deliverable 3 is no longer a hypothesis. — source: inbox message
    `lb-25-phase-and-merge-gates-005.md`.
  - **Closed by PLAN-LB-38 (#1752), except as follows; remove this entry at the next cleanup.**
    Defects 1, 2, 3, 5, 7 fixed; 9 got a fixed 60-second margin; 4 dropped (no bot declares a
    cap); 6 and 8 are fixed on the re-review path and leave the two follow-ups below.

- **An empty `--changed-paths ""` runs no tests.** PLAN-LB-33 D9 made the executor keep an
  empty option value; `pyproject_build.py:295-296` reads it as an empty footprint and returns
  `divergence_possible: false`. Before D9 the value was stripped and argparse failed loudly.
  So a Step 5(b) whose `{changed_paths}` resolves empty skips pytest and reports success.
  Related, advisory: `architecture resolve --narrow-unit ""` falls back to the module-wide
  resolve without `bound_source`. **Closed by PLAN-LB-38 (#1752):** both empty values are
  refused (`empty_changed_paths`, `empty_narrow_unit`), and a task with no changed file
  resolves by `--plan-id`. Remove this entry at the next cleanup. — source: read-only review
  of `370f42379`, 2026-10-10; advisory list of the PR #1745 body.

## Self-review entries closed by its retirement

- **The self-review has no outcome for "could not establish coverage".** A round that cannot
  read everything it is asked to judge still returns an ordinary verdict: the figures
  `contract_sources_read` and `contract_sources_listed` are reported and nothing branches on
  them, a missing verifier records a loop-back, and no outcome is exempt from the round
  ceiling. So a round that fails for lack of a tool spends a round, and one that reads only
  part of its surface can close. Reported fixture: seven firings, five of five loop-backs,
  263 candidates, closed by operator override. Not owned by any staged plan; PLAN-LB-28
  edits the same workflow and is the place to fold it if it recurs after #1726. — source:
  inbox message `lessons-routing-001.md` (the PLAN-09 row), 2026-10-09; the absence was read
  in `pre-submission-self-review.md` at `4ed67e228`.

- **The self-review's author leaf is briefed to record a step it must not record.** On
  PLAN-LB-33, every author leaf of seven firings returned without `mark-step-done`, as the
  workflow requires (the verifier runs from the orchestrator), and later briefs still said
  "record before return"; one dispatch named the workflow under `standards/` and failed with
  `workflow_not_found`. Lesson `2026-10-10-20-007`. PLAN-LB-34 (running) edits
  `pre-submission-self-review.md` but not the finalize dispatcher. — source: inbox message
  `lb-33-leaf-test-scope-and-executor-006.md`.

## Watches retired on 2026-10-14

- **Does the regraded self-review converge?** The first plans to finalize on `d8b0284ef` or
  later are the test: read their landing facts for the self-review's firing count, its
  `blocking_count` and `advisory_count`, and whether it closed by verifier or by operator.
  — trigger: the landings of PLAN-LB-24 and 29, if they rebased onto it; retire after
  two landings that closed by verifier.
  - Baseline, from PLAN-LB-23, which ran the self-review from before that change: five
    rounds returning 6, 7, 4, 5 and 10 findings (32, all fixed), 25 of them doc-claim
    findings, no clean round, closed by operator decision and not re-run on the two later
    review-fix commits. The five reviewer dispatches cost 2,159,266 tokens. Two of the 32
    were shipped-code defects, found in rounds 4 and 5 (the supervisor waited on the job
    leader and left a build that ignores SIGTERM alive; a `PermissionError` recorded a
    timed-out job as `failure`). A regraded review that stops earlier must still reach
    defects of that kind. — source: inbox message `lb-23-verify-builds-002.md`.
  - Second baseline, from PLAN-LB-29: six rounds, 29 findings, nearly all over-wide prose
    claims, closed by the operator at the round limit; 3,220,593 tokens in author and
    verifier dispatches. In its last round the reviewer saw a real defect outside its
    candidates (the install sync writing through a destination symlink) and did not file
    it; CodeRabbit filed it one round later as Major. The review shipped as #1726 returns
    such an observation as advisory and lets the verifier promote it. Check on the next
    landings whether a real code defect seen that way was promoted, or again left as text.
    — source: inbox message `plan-lb-29-harness-sync-004.md`.
  - Third baseline, from a consumer repository before #1726 (cui-http PLAN-13, PR #262, a
    documentation-claims plan): about seven rounds, each reworded claim producing new
    findings, the ceiling exceeded twice on operator authorisation. — source: inbox message
    `lessons-routing-005.md` (retired lesson `2026-10-05-17-003`).
  - **First landing on the regraded review: PLAN-LB-32 closed by verifier**
    (`acceptance=accepted`, `may_close=yes`, 0 blocking, 12 advisory notes left open; no
    operator close). One of the two landings this Watch asks for. Its round count and the
    review's token cost are not in the landing facts, and whether any of the 12 advisory
    notes was a real defect was not checked; three of them named the same out-of-scope
    observation in three rounds. — source: inbox message
    `lb-32-head-dependent-step-refire-007.md`.
  - **PLAN-LB-24: not converged.** All five fix rounds used, each fix right on its target
    but adding one or two new blocking gaps in the finalize text it rewrote; closed by
    operator decision, then by override at two later heads, so the CodeRabbit review-fix
    commits shipped without self-review, and CodeRabbit found a real defect in one of them.
    About 4.9 million tokens in the five rounds. The override carries forward to every later
    head; lesson `2026-10-10-20-004` proposes a delta-only review after it. — source: inbox
    messages `lb-24-review-step-008.md`, `-009.md`.
  - **PLAN-LB-33: seven firings**, closed (`pre-submission-self-review:done`); whether by
    verifier is not in its landing facts. — source: inbox message
    `lb-33-leaf-test-scope-and-executor-008.md`.

- **A landing from the Antigravity harness reported `total_tokens=0`** (PLAN-LB-30) and still
  passed the completeness check, which accepts any value that is not `n/a` or `unknown`.
  — trigger: stage it if a second landing from that harness reports zero.
  - **Trigger met on 2026-10-13**: pm-mcp-core PLAN-41, run under Antigravity, landed with
    `total_tokens=0` and every `record-step` `unmeasured` (`lessons-routing-013.md`). Now part
    of the critical Antigravity Open Defect; staging is the operator's decision.

- **RETIRED 2026-10-14 — trigger met, now owned by PLAN-LB-40 D5.** The rollout reached every
  configured repository (see the PLAN-LB-37 annotation).
  **The `migrate-review-steps` steward migration is meant to go.** PLAN-LB-37 D8 added it on
  operator instruction, to be removed by a later plan once every configured repository has been
  migrated by PLAN-LB-37's post-landing rollout (scope: `marshall-steward/scripts/upgrade.py`
  `migrate-review-steps` and `_merged_review_params` with its SHIM(A) block, the steward
  `SKILL.md` and `references/upgrade-flow.md`, `test_review_step_migration.py` and cases in
  `test_upgrade.py` / `test_upgrade_flow_stage2.py`, the plugin-doctor shim-marker figures).
  — trigger: PLAN-LB-37's landing reports the rollout complete for every repository, or the
  operator confirms none still needs it. — source: `lb-37-functional-review-001.md`. PLAN-LB-37
  landed 2026-10-13 with the rollout (D9) OWED and `blocked` by operator decision; the trigger
  is not met yet.

- **Three plans outside this epic had no captured footprint** when last read
  (`harness-bundles-target-rules`, `selective-bundle-installer`, `steward-harness-config`).
  The gate PLAN-LB-14 shipped still refuses while a live plan has neither a footprint nor an
  orchestrated source spec. — trigger: the first `next` run on the new gate; retire when it
  reports the comparison determinate.

## Queue annotations for shipped, superseded and drained work

- **Which plans may run together.** Measured with `corpus cross-check` after the regrouping:
  40 of the 55 pairs of live plans share no declared file. The fifteen pairs that do:
  - PLAN-LB-22 with each of 23, 24, 25, 26, 27 and 28. It is the hub of the finalize work
    (`phase-6-finalize/SKILL.md`, `manage-status`, `execution.md`,
    `pre-submission-self-review.md`, and directory-level entries under `phase-6-finalize/`).
  - PLAN-LB-24 with 25, 26 and 27 (`phase-6-finalize/SKILL.md`, `merge_lock.py`, `triage.md`).
  - PLAN-LB-26 with 23, 27 and 28 (`manage-tasks/SKILL.md`, `phase-5-execute/SKILL.md`,
    `execution.md`, `pre-submission-self-review.md`).
  - PLAN-LB-25 with 27 (`phase-6-finalize/SKILL.md`).
  - PLAN-LB-23 with 28 (`_build_shared.py`, which 28 touches only conditionally).
  - PLAN-LB-14 with 29 (`orchestrator.py`, `plan-orchestrator/SKILL.md`).

- **Queue order** is built for pairs: PLAN-LB-14 with 22; then 23 with 24; then 25 with 26;
  then 27 with 28. PLAN-LB-29, 30 and 31 share no file with any of 22 to 28 and fill a slot
  whenever one is free; 29 waits for PLAN-LB-14. At a parallelization scope above 2, up to five
  plans are mutually disjoint at once (for example 23, 24, 29, 30 and 31).

- **Emitted on 2026-10-08, two blocks.** PLAN-LB-14 and PLAN-LB-22 were emitted first, under
  operator override of the launch gate. For a second machine, PLAN-LB-30 and PLAN-LB-31 were
  identified as the two further plans that can run beside them: each shares no declared file
  with PLAN-LB-14, with PLAN-LB-22, or with the other (measured with `corpus cross-check`),
  and they are the only two live plans for which that holds — PLAN-LB-23 to 28 each overlap
  PLAN-LB-22, and PLAN-LB-29 overlaps PLAN-LB-14. Four plans in flight is above the
  parallelization scope of 2; that is the operator's instruction, and the knob was left as it
  is. One order remains between the two: PLAN-LB-31 starts with its measurement and stops
  after the recorded roster decision until PLAN-LB-30 has released the schema. All four rows
  stay `staged` until the operator confirms each launch.

- **Order swapped on 2026-10-08: PLAN-LB-29 before PLAN-LB-14.** PLAN-LB-30 was started on a
  second machine on the Antigravity harness, whose installs are missing every skill
  `workflow/` file until PLAN-LB-29 lands. The operator had PLAN-LB-29 emitted at once for
  that reason. The two plans share `plan-orchestrator/scripts/orchestrator.py` and
  `plan-orchestrator/SKILL.md`, so PLAN-LB-14, emitted earlier but not launched, now waits for
  PLAN-LB-29 and is not launched beside it. `next` keeps refusing for that much longer.

- **PLAN-LB-14 shipped on 2026-10-08 (#1715, `3fe828c84`)** — record at `landings/PLAN-LB-14.md`.
  It ran and landed while PLAN-LB-29 was running, although the ledger held it until 29 had
  landed. Nothing collided at its merge; PLAN-LB-29 now rebases onto it in
  `plan-orchestrator/scripts/orchestrator.py` and `plan-orchestrator/SKILL.md`. The gate it
  ships judges each candidate against in-flight work only, and puts an overlap of more than
  one shared entry to the operator instead of refusing.

- **PLAN-LB-30 shipped on 2026-10-08 (#1722, `2cb0f8c3f`)** — record at `landings/PLAN-LB-30.md`.
  Reconciled on 2026-10-09 from inbox message `plan-lb-30-org-ci-release-001.md` (landing,
  complete), the only message of that drain. The organisation release it owed exists:
  `cuioss-organization` `v0.39.0` carries the extra-buildable input, the whole-file validator
  and the settled schema keys, so PLAN-LB-31 no longer has to stop after its roster decision.
  Nothing collided with PLAN-LB-23, 24 or 29. All seven deliverables were checked against
  the code on 2026-10-09: the released validator passes API-Sheriff, TokenSheriff and
  cui-http unchanged, and the gate was seen skipping a ledger-only PR (#1728) and building a
  Markdown-only one (#1727). Three small gaps in its tests were
  closed by a follow-up outside the queue: #1733 (`baa7238fa`) adds a drive-letter path
  pattern with two negative controls, corrects the docstring to the key forms the pattern
  matches, and checks the two Markdown globs by exact token with an `.mdx` negative control;
  `cuioss-organization` #320 (`e8d085e`) makes the cross-file test assert that the schema
  marks the timeout key deprecated and that the three other files say so on the line naming
  it, and adds the same kind of test for the two-part version decision. Both diffs were read
  on 2026-10-09; the mutation runs the follow-up reports were not repeated here. One side
  effect: #1733 removed the `/Users/alice/git` negative control, so no control now pins the
  `home`/`Users`, `/tmp/`, `.sock` and `.pid` path alternatives on their own (the remaining
  cases that carry such values assert the prohibited-key message instead).

- **Inbox drain of 2026-10-08, six messages** (five from PLAN-LB-14, one from PLAN-LB-22):
  - `lb-14-launch-gate-scope-005.md` (landing) — reconciled; complete.
  - `lb-14-launch-gate-scope-001.md` — folded into PLAN-LB-22 as a recurrence, recorded here
    and not in the spec because that plan is in flight: on this epic's first landing
    `finalize-step-lessons-housekeeping` and `finalize-step-plugin-doctor` each fired five
    times with identical verdicts. PLAN-LB-22 already carries the `verdict_inputs` declaration
    for lessons-housekeeping (PLAN-LB-02 D5). It leaves plugin-doctor's recorded refusal to
    declare standing; the message proposes declaring the scoped skill directories for it,
    which that plan's outline should weigh against the refusal's evidence. No surface added.
  - `lb-14-launch-gate-scope-002.md` — promoted to the lessons corpus as `2026-10-08-15-001`:
    a rule corrected at many sites needs one canonical statement and pointers elsewhere. It
    applies to every plan here that makes several documents state one rule (22, 24, 25, 26).
  - `lb-14-launch-gate-scope-003.md` — promoted as `2026-10-08-15-002`: the retrospective's
    outline-vs-shipped aspect counts a superseded exclusion as violated. No owner in this epic.
  - `lb-14-launch-gate-scope-004.md` — folded into PLAN-LB-23 as a hypothesis and a
    verify-first clause on PLAN-LB-12 D5: routed builds left no change-ledger row for the
    plan. Expected surface unchanged; `_build_shared.py` was already declared.
  - `lb-22-finalize-loop-control-001.md` (finding) — absorbed as an Open Defect, below.

- **PLAN-LB-22 shipped on 2026-10-08 (#1718, `6b00815e0`)** — record at `landings/PLAN-LB-22.md`.
  All ten deliverables landed; the `verdict_inputs` deliverable landed as the recorded refusal
  the spec allowed, so head-dependent finalize steps still re-fire on every fix commit. Its
  own self-review never converged and was closed with the operator-close verb it built.

- **Inbox drain of 2026-10-08 (second), fifteen messages from PLAN-LB-22:**
  - `-016` (landing) — reconciled; complete.
  - `-002` (scope-creep guard cannot persist, measures upstream history) and `-004`
    (`affected_files` does not grow with fix tasks) — folded into PLAN-LB-27. No surface added.
  - `-005` (triage `deliverable: 0` rejected; three runs chose three rules) — folded into
    PLAN-LB-26. No surface added.
  - `-014` (the merge lock is released early during branch cleanup) — folded into PLAN-LB-25
    as its tenth deliverable; `integrate_into_main.py` and the reentrant-acquire test added to
    its Expected Surface.
  - `-007` (the pre-push gate's builds are not accepted by the freshness check) — a recurrence
    of what PLAN-LB-23 fixes. That plan is running, so it is recorded here and not in the
    spec: with green rows for a bundle compile, the whole-tree quality gate and two bundle
    verifies, the check still answered `build_scope_narrow`, and each fix commit owed a
    whole-tree `verify` of 17 to 23 minutes.
  - `-009` (the re-review procedure triggers one stale bot of two) and `-010` (CodeRabbit's
    reply to our own trigger is stored as a blocking finding) — recurrences of what PLAN-LB-24
    fixes (PLAN-LB-19 D1; PLAN-LB-18 D3 and D4). That plan is running, so they are recorded
    here and not in the spec. `-009` cost one loop-back round with nothing wrong.
  - `-012` (the self-review has no stopping rule on prose-heavy plans; Step 2a's read-all
    instruction is not achievable) — folded into the standalone self-review plan's brief.
  - Promoted to the lessons corpus, none with an owning plan here: `-003` as
    `2026-10-08-21-001` (lessons-housekeeping still reads the retired `modified_files` field),
    `-006` as `-21-002` (pass self-review candidates by file path), `-008` as `-21-003`
    (declare `verdict_inputs` on head-dependent steps), `-011` as `-21-004` (a wrong bot
    comment needs a `rejected` disposition), `-013` as `-21-005` (six `manage-status`
    documentation and behaviour gaps left by PLAN-LB-22), `-015` as `-21-006` (the PR Intent
    section drops the non-goals when over budget).

- **PLAN-LB-23 shipped on 2026-10-09 (#1729, `c9738952a`)** — record at `landings/PLAN-LB-23.md`.
  A timed-out build now stops its whole process tree on both the daemon and the direct
  path, a timeout names the bound applied and its source, and the push freshness gate
  credits a set of narrower green builds when every required analysis has one row at an
  adequate scope. Scope is not pooled across rows: several bundle verifies still do not
  cover a whole-tree change, so a fix commit touching more than one module still owes a
  whole-tree `verify`. Seven of nine deliverables landed as specified or with a small
  deviation; the plan-attribution deliverable landed in part (see Open Defects). It cost
  13.1 million tokens and about 14 hours, 58 percent of the tokens in finalize.
  - The commit touched 31 files its spec did not declare, among them `execution.md`,
    `phase-5-execute/SKILL.md`, `canonical_verify.md` and `build-server-client/SKILL.md`,
    which PLAN-LB-26 cites by line, and it changed `_build_execute_factory.py` and
    `_build_shared.py`. PLAN-LB-26 and PLAN-LB-28 need their claims re-grounded against it
    before launch, in addition to the self-review claims named below.

- **PLAN-LB-32 head-dependent-step-refire, staged on 2026-10-09 at high priority.** It is to
  be launched ahead of PLAN-LB-25 to PLAN-LB-28, as soon as a slot is free or the operator
  exceeds the scope for it. Measured with `corpus cross-check`: it shares one declared entry
  with PLAN-LB-24 (running) — `phase-6-finalize/SKILL.md`, which it edits only for a script
  table row or if its change-list verb has to be handed over by the dispatcher — and none
  with PLAN-LB-29 (running), 26, 28, 30 or 31. With PLAN-LB-25 it shares that same file, with
  PLAN-LB-27 that file and `ext-point-finalize-step.md`. Its remaining overlap is with
  PLAN-LB-22, which has shipped. It does not touch `manage-lessons.py`, which five staged
  specs of the `lessons-routing` epic declare.

- **Inbox drain of 2026-10-09, thirteen messages from PLAN-LB-23:**
  - `-014` (landing) — reconciled; complete.
  - `-005` (scope-creep guard: six failed calls, 76 to 108 residual files of upstream
    history) and `-011` (`affected_files` held 46 entries against 56 touched files; the
    scoped plugin-doctor gate read it and left four skill directories ungated) — folded into
    PLAN-LB-27 as second recurrences. No surface added.
  - `-006` (triage `deliverable: 0` rejected in four dispatches; fix tasks created without
    an envelope were handed out after queued plan tasks three times) — folded into
    PLAN-LB-26 as a second recurrence. No surface added.
  - Promoted to the lessons corpus, none with an owning plan here: `-004` as
    `2026-10-09-13-001` (run per-task tests at directory scope when the module-wide run is
    too long for a leaf), `-007` as `-13-002` (`WORKTREE` arrives absolute, or as a flag
    fragment after the merge), `-008` as `-13-003` (the orchestrator followed a stale cached
    workflow document and told the operator the wrong loop limit), `-009` as `-13-004` (the
    main executor pointing into a removed worktree; also an Open Defect), `-013` as
    `-13-005` (30 of 34 dispatch-boundary rows carry no step id, so finalize cost cannot be
    attributed to steps).
  - Discarded as duplicates of lessons already in the corpus, each a second sighting:
    `-003` (`2026-10-08-21-003`; its cost figures are on the Watch), `-010`
    (`2026-10-08-21-006`), `-012` (`2026-10-08-21-004`).
  - `-002` (the self-review never converged) — not lifted: the run used the self-review
    from before #1726. Kept as the baseline of the Watch on the regraded review.

- **PLAN-LB-29 shipped on 2026-10-09 (#1724, `35b5589b5`)** — record at `landings/PLAN-LB-29.md`.
  The sync now reports whether Claude Code's plugin registry matches the version it just
  installed (`behind` is a partial result, `ahead` is not an error), one reader serves the
  sync, the pin trap and the restart check, and the OpenCode and Antigravity installs
  receive every file of a skill directory, `workflow/` included. Eight of the nine spec
  deliverables landed as specified or with a small deviation; the repin landed in part.
  The registry is written only on request: `sync.py --repin`, `registry_pin.py --apply`, or
  at finalize when the machine-local `registry-repin` setting is `enabled` (default
  `disabled`). The plan grew to fifteen deliverables — two accepted quality-check findings
  and a symbolic-link hardening class from review — and cost 16.8 million tokens over
  about 26 hours. It changed the root `opencode.json` into a shape the repository's own
  code does not read (see Open Defects).

- **Inbox drain of 2026-10-09 (second), eighteen messages** — fourteen from PLAN-LB-29, four
  findings from the `lessons-routing` epic, which retired nine lessons from the corpus and
  handed their subjects to this epic (bodies at
  `lessons-routing/lessons-archive/filed-live-blockers/`):
  - `plan-lb-29-harness-sync-014` (landing) — reconciled; complete.
  - Folded into staged specs, no surface added: `-001` (scope-creep guard, third recurrence)
    and `lessons-routing-002` (task artifact lines list a sibling task's uncommitted files)
    into PLAN-LB-27; `-012` (housekeeping's retired-field read, second recurrence) and the
    generated-commit item of `lessons-routing-001` into PLAN-LB-32; the merge-commit item
    of `-013` and the bot-in-progress item of `lessons-routing-003` into PLAN-LB-25.
  - Promoted to the lessons corpus, none with an owning plan here: `-002` as
    `2026-10-09-15-001` (the test-scope resolver has no target for `marketplace/targets/`
    and `test/sync-harnesses/`), `-008` as `-15-002` (task planning cannot append tasks for
    a deliverable added later), `-009` as `-15-003` (a loop-back books finalize time on the
    execute phase), `-011` as `-15-004` (the transcript reduction counts subagent
    hand-backs as operator turns), `-013` as `-15-005` (seven finalize steps the dispatcher
    improvised), `-005` as `-15-006` (triage fixes a reviewer finding at the commented site
    only; four sites of one class took two extra rounds), `-007` as `-15-007`
    (`@coderabbitai full review` and the bot's replies to it are stored as findings).
  - Already shipped, discarded: `-003` (the freshness gate refused the builds the manifest
    prescribes — the union rule of PLAN-LB-23, #1729, accepts them now) and `-004` (a
    defect seen outside the review's candidates was dropped — the review shipped as #1726
    returns it as an advisory observation the verifier may promote).
  - Covered by PLAN-LB-24, which is running, so recorded here and not in its spec: `-006`
    (the rate-window wait cannot run in a dispatched step; its deliverable 2 returns the
    wait to the dispatcher). Read against that spec on 2026-10-09, three things from this
    drain are NOT in it and are to be checked at its landing: the claim window equals the
    wait budget (`-006`); `@coderabbitai full review` is not excluded as an own trigger, and
    "Already reviewed the last commit" is treated as a refusal, not noise (`-007`); a
    `fixed` reply is held back until the fixing commit is on the branch, but not until
    verify is green (`lessons-routing-003`).
  - Duplicate of lesson `2026-10-09-13-005`, discarded: `-010` (all 38 dispatch-boundary
    rows without a step id).
  - `lessons-routing-004` (enrol the repositories left unwritten for schema failure) —
    covered by PLAN-LB-31 deliverable 6; discarded.
  - `lessons-routing-001` — two of its four items shipped with #1726 (the verifier is
    dispatched by the dispatcher; a class sweep exists, limited to the surfaced
    candidates), one went to PLAN-LB-32, one is open (see Open Defects).

- **PLAN-LB-32 shipped on 2026-10-10 (#1741, `ef7d36617`)** — record at `landings/PLAN-LB-32.md`.
  All seven deliverables are accounted for, and the objective is not met yet: a re-fire of
  the two project steps is not cheaper in practice. Plugin-doctor keeps its full re-fire —
  the narrower skip rule was examined and refuted with a named counter-example, as the spec
  allowed. Housekeeping gained the delta rule, but it narrows the judging and not the
  dispatch, runs after every lesson body has been loaded, and never met a real lesson on
  this run, because the corpus was empty. On its own run the plan fired the two steps 11 and
  10 times and spent 70 percent of 13.7 million tokens in finalize. What it did deliver for
  good: both steps read the realized footprint (the retired-field read is gone from
  housekeeping), one log line per firing, and a verb any step can call to ask what changed
  since its last firing. See Open Defects and the Watch.
  - Its self-review closed by the verifier, with no operator close: the first such landing.
  - Its `sync-plugin-cache` step is recorded failed: the registry pins 0.1.1892, the cache
    was synced to 0.1.1894, and repinning is disabled on this machine. The remedy is the
    operator's: `python3 marketplace/targets/claude/registry_pin.py --apply`, then a restart.
  - PLAN-LB-33 may now do its last deliverable: the plugin-doctor passage it targets is
    unchanged by this landing (the symlink sentence at lines 29 and 203, the generation call
    at 206-207). PLAN-LB-25 and PLAN-LB-27 no longer share a file with a running PLAN-LB-32.

- **Inbox drain of 2026-10-10, seven messages from PLAN-LB-32:**
  - `-007` (landing) — reconciled; complete.
  - `-001` (scope-creep guard, fifth plan in a row without a signal) — folded into
    PLAN-LB-27. No surface added.
  - Promoted to the lessons corpus: `-002` as `2026-10-10-06-001` (no verb edits a task's
    verification commands, so moving a test re-creates every task), `-003` as `-06-002`
    (check for an empty corpus before dispatching housekeeping), `-004` as `-06-003` (an
    empty-corpus exit should name the non-active records), `-006` as `-06-004` (the
    automatic-review `display_detail` template is 87 characters with an em dash against an
    80-character ASCII rule).
  - `-005` (every dispatch-boundary row without a step id) — third landing in a row;
    absorbed as an Open Defect.
  - The question `-004` leaves open — where 18 lessons went between two outline passes — is
    answered here: the `lessons-routing` ingest runs of 2026-10-09 retired the corpus into
    `lessons-routing/lessons-archive/`. `manage-lessons list` read `total: 1, filtered: 0`
    on 2026-10-10 before this drain's promotions.

- **PLAN-LB-37 functional review + code review shipped on 2026-10-13 as a five-PR stack**:
  #1754 (`fc0090a24`, rubric, `review_support` helper, harvestable rules), #1755 (`730f37a2f`,
  the two steps and the code-review packs), #1757 (`77ef084ad`, every reader moved off the old
  step), #1758 (`47d21e1bf`, the old step and the surfacer apparatus retired, configurations
  migrated), #1759 (`d5c1e869f`, review-step and migration hardening). Record:
  `landings/PLAN-LB-37.md`. 14 of 16 spec deliverables shipped (D13 partial); D9 (consumer
  rollout) and D15 (bot settings) OWED by operator decision. Reviews and merge closed by
  operator override. The stack exists because CodeRabbit's 100-file cap refused the single PR
  #1753. Its functional review does not catch rewritten criteria or weakened tests — PLAN-LB-39
  D6 owns that. Inbox `-005` to `-008` promoted as lessons `2026-10-13-14-001` to `-004`;
  `-009` is the landing.

- **PLAN-LB-37's owed post-landing work is done (inbox `-010`, verified 2026-10-14).** D9: all
  nine configured consumer repositories carry the review-step migration on their default branch
  with `functional-review`, `code-review` and the standard roster (API-Sheriff #441,
  TokenSheriff #802, cui-http #284, cui-jsf-test-basic #215, cui-open-rewrite #197,
  cuioss-parent-pom #1515, nifi-extensions #650, plan-marshall-mcp #74, pm-mcp-core #57; read
  with `git -C` on each clone). D15: cuioss-organization #326 (`d16ff2e`, released v0.42.0, tag
  commit `711571432`), cuioss-review-bot #69 (`73db31d`) and plan-marshall #1767 (`187f7314a`)
  are merged. One residue: the phase-3 `qgate` key in cui-jsf-test-basic (read by nothing).

- **Inbox drain of 2026-10-14, four messages, no landing:**
  - `lb-37-functional-review-010` (D9 and D15 done) — observed; the entry above.
  - `lb-37-functional-review-011` (six steward-upgrade defects from the rollout) — staged as
    PLAN-LB-40 steward-upgrade-integrity, together with the `migrate-review-steps` removal whose
    Watch trigger the rollout met.
  - `lb-37-functional-review-012` (ten leftovers) — items 1, 3 to 7 staged as PLAN-LB-41
    lb-37-review-leftovers; item 2 recorded as a decision; items 8 to 10 an Open Defect
    (foreign repositories).
  - `plan-lb-31-in-house-reviewer-001` (running PLAN-LB-31's roster decision) — observed; see
    the PLAN-LB-31 annotation.

- **Inbox drain of 2026-10-13, nineteen messages:**
  - From PLAN-LB-37 (four follow-ups it handed off, none a landing):
    - `-001` (remove the one-shot `migrate-review-steps` steward migration once every consumer is
      migrated) — kept as a Watch; operator instruction recorded by the plan.
    - `-002` (capture `head_at_completion` at step start for every head-dependent step) —
      promoted as `2026-10-13-07-001`.
    - `-003` (ceremony selection re-adds steps the no-push filter dropped) — an Open Defect
      with a decision for the operator.
    - `-004` (shell-quote free-text placeholders in every workflow command template) —
      promoted as `2026-10-13-07-002`; an Open Defect.
  - From the `lessons-routing` epic (fifteen findings ingested from the pm-mcp-core epic on
    2026-10-12; its "owner today" lines predate the landings of PLAN-LB-24, 25, 28, 33 and 38
    and are re-read here):
    - `-011`, `-012`, `-013`, `-014`, `-015`, `-016`, `-018` — Open Defects, below; six are graded
      **critical** by the operator's ruling of 2026-10-12 that Antigravity issues are the
      epic's highest priority. `-013` meets the trigger of the Antigravity zero-token Watch.
    - `-017` (a required bot goes stale after a fix commit) — partly closed by #1742 and
      #1752; the remainder is an Open Defect.
    - `-019` (red CI has no triage route) — same defect as lesson `2026-10-11-16-001`, now with
      four more plans; confirmed still present at `47d21e1bf` (`verification-feedback.md:30, 59`).
      An Open Defect.
    - `-020` (`commit-add` rejects deliverable 0) — folded into PLAN-LB-26 as OBSERVED. No
      surface added.
    - `-021`, `-022`, `-023` — Open Defects.
    - `-024` (Java skill profiles) and `-025` (cui-http-testing guidance) — domain content,
      promoted as `2026-10-13-07-003` and `-07-004`.
  - Recurrences of the above, from `lessons-routing-028.md` (2026-10-13, 14 pm-mcp-core
    messages, no new work asked): appended to the Open Defects for `-013`, `-018`, `-019`,
    `-021`, `-022`, `-023`. `-020` recurred on PLAN-18 (both triage runs; fix tasks left under
    deliverables 3 and 4) — appended to PLAN-LB-26's OBSERVED line, no surface added. `-024`
    recurred on PLAN-18 (`java-quarkus` / `java-cdi` attached in a module whose `CLAUDE.md`
    bans them) — evidence for lesson `2026-10-13-07-003`, not re-filed.
  - `lessons-routing-026.md` — recurrence of `-015` under opencode with five new mechanisms;
    appended to the `-015` Open Defect. `lessons-routing-027.md` — new Open Defect (CodeRabbit
    summary-only concerns dropped as noise), verified at HEAD.

- **PLAN-LB-38 review-gate-and-empty-scope shipped on 2026-10-11 as #1752 (`4a985a1bf`).**
  Record: `landings/PLAN-LB-38.md`. Nine of ten deliverables shipped (four with deviations);
  D10 dropped under its own clause (no bot declares a size cap). An empty change list is now
  refused, and a task with none resolves by plan. On the re-review path the gate credits only a
  finished review by the awaited bot; acknowledgments are noise; review-bot statuses are no
  longer CI; a stale notice re-triggers a required bot; an edited comment updates its finding
  (reopen-on-change, by operator decision). Left open: the participation-credit path does not
  apply the in-progress check (observed on its own PR); the new "fixed"-reply CI hold never
  releases on a repository with no non-bot check; the wake margin has no jitter. It committed
  the stale `uv.lock` re-lock by operator choice. PLAN-LB-37 must rebase onto it: three of its
  declared files changed.

- **Inbox drain of 2026-10-12, five messages from PLAN-LB-38:**
  - `-005` (landing) — reconciled; complete.
  - Promoted to the lessons corpus: `-001` as `2026-10-12-05-001` (detect a stale base `uv.lock`
    instead of re-locking it in every plan build), `-004` as `-05-002` (participation credited
    from an edited pre-existing comment).
  - `-002` (root-level guards skipped before push) — third plan in a row; added to lesson
    `2026-10-11-16-003` as a recurrence instead of a parallel lesson.
  - `-003` (every dispatch-boundary row keyless) — seventh landing; absorbed into the Open
    Defect.

- **PLAN-LB-25 phase-and-merge-gates shipped on 2026-10-11 as #1751 (`3ff307ddd`).** Record:
  `landings/PLAN-LB-25.md`. All ten deliverables shipped, three with deviations. Merge is now
  gated by a script (`pre_merge_gate.py`, fails closed); archive is refused by `manage-status`
  (recording the step `failed` stays an instruction); both merge waits are bounded inside scripts
  without `sleep`; the light-lane `pr_title` producer is documented and the refusal names its
  remedy. Two residuals accepted by the operator at the self-review round cap: merge-lock
  ownership keyed on `plan_id`, not session, and a landing-gate failure path that releases a lock
  it no longer holds. For the running plans: PLAN-LB-38's rate-window code and items 7a/7c(0)
  are unchanged, only moved; PLAN-LB-37 meets a new `pre_merge_gate` block in
  `phase-6-finalize/SKILL.md` and seven changed tests under `phase-6-finalize/`. PLAN-LB-27
  no longer shares a file with a running plan except `phase-6-finalize/SKILL.md` with
  PLAN-LB-37 and PLAN-LB-38.

- **Inbox drain of 2026-10-11 (second), twelve messages from PLAN-LB-25:**
  - `-012` (landing) — reconciled; complete.
  - Promoted to the lessons corpus: `-001` as `2026-10-11-16-001` (verification-feedback refuses
    ci-verify's producers), `-002` as `-16-002` (ci-verify findings keyed on the wrong run),
    `-004` as `-16-003` (root-level test guards skipped before push), `-006` as `-16-004`
    (session-scoped merge-lock ownership), `-009` as `-16-005` (module-tests tier oscillates),
    `-010` as `-16-006` (xdist_group-suffixed test ids), `-007` as `-16-007` (nitpicks inside an
    "Actionable comments" body under-counted; filed under the bare component
    `finalize-step-review-retrospective`, because the store refuses the `project:` prefix).
  - `-003` (`commit-add` rejects deliverable 0, fourth recurrence) and `-008` (a module-testing
    task closed before its tests ran) — folded into PLAN-LB-26. No surface added.
  - `-005` (a re-review awaited for cuioss-review-bot matched a CodeRabbit review) — the live
    confirmation of PLAN-LB-38 deliverable 3, which treats it as verify-first. PLAN-LB-38 is
    running, so nothing is folded into its spec; recorded on the Open Defect.
  - `-011` (finalize boundary rows stop hours early, all keyless) — sixth landing; absorbed into
    the Open Defect.

- **PLAN-LB-38 review-gate-and-empty-scope, staged and emitted on 2026-10-11 by operator
  instruction** ("create a plan for fixing both and emit it now"). It owns two former Open
  Defects: the empty `--changed-paths` fail-open (part A, deliverable 1, to be done first) and
  the nine unowned review-gate defects (part B, deliverables 2–10; four of them from retired
  consumer-repository lessons, verify-first). A weak merge the outline may split between
  deliverables 1 and 2. Measured with `corpus cross-check`: it shares
  `manage-locks/scripts/merge_lock.py`, `phase-6-finalize/SKILL.md` and
  `test_merge_lock_rate_window.py` with running PLAN-LB-25 (deliverables 4 and 6 only); PLAN-LB-37
  (running, no footprint yet) names `automatic-review/SKILL.md` and `phase-6-finalize/SKILL.md`
  among the files it edits. Both collisions are accepted by the operator's "now"; the spec tells
  the plan to rebase onto whichever lands first.

- **PLAN-LB-28 java-consumer-repos shipped on 2026-10-10 as #1750 (`2fd164ec9`).** Record:
  `landings/PLAN-LB-28.md`. Deliverables 1–4 shipped (5–8 had moved to PLAN-LB-34, now
  superseded by PLAN-LB-37). A consumer of a reactor test artifact gets a `package` ladder;
  Maven test counts are summed across summary blocks with `unmeasured` where they cannot be
  attributed; javac tags are literal; the failure epilogue is no longer filed. Half the
  premise of deliverable 1 was refuted and recorded: Maven 3.9.16 resolves a plain
  `test-jar` dependency at `test`; only a custom classifier breaks. **It does not reach the
  consumer repositories until architecture discovery is re-run there** after the harness
  sync, because detection is persisted at discovery. The evidence is fixture-only. It crossed
  the request's `extension-api` exclusion with one consistent table in `build-execution.md`,
  without a recorded operator decision; PLAN-LB-37 declares the `extension-api` tree.

- **Inbox drain of 2026-10-11, seven messages from PLAN-LB-28:**
  - `-007` (landing) — reconciled; complete.
  - Promoted to the lessons corpus: `-001` as `2026-10-11-06-001` (a field added to `to_dict`
    and not to `format_toon`; carries `-002`, its round-state companion), `-003` as `-06-002`
    (a Maven fixture whose test-jar classifier the producer never attached), `-004` as
    `-06-003` (re-resolve the live timeout before a leaf starts a long build), `-005` as
    `-06-004` (`sync-affected-files` never prunes a path dropped from the outline).
  - `-002` — folded into `-06-001`; its surfacer proposal is moot under PLAN-LB-37.
  - `-006` (every dispatch-boundary row keyless) — fifth landing; absorbed into the Open
    Defect.
  - The plan filed two lessons itself at `lessons-capture`: `2026-10-10-21-001` (sonar returns
    `internal_error` where it should say `unconfigured`) and `-21-002` (an order-dependent
    build-server test).

- **PLAN-LB-34 stopped unmerged on 2026-10-10; PLAN-LB-37 staged in its place, at the head
  of the epic.** Source: inbox messages `lb-34-self-review-surfacing-foundation-and-java-001`
  and `-002` (stream end). Checked: branch
  `feature/lb-34-self-review-surfacing-foundation-and-java` is local only (`a35410713`, 24
  commits on `66c6e4cd0`), not on the remote, and `ci pr list` finds no pull request for it;
  `main` is untouched. Four self-review rounds over its own change found real defects, nearly
  all in the per-language diff parsing it built, every one by reading changed code whole while
  the reviewer reached about 40 percent of the surfaced candidates. The operator concluded the
  review has drifted from its question ("did the plan implement the requirements?") and
  directed a split: a domain-free functional review, and a code review against general
  practice and the project's conventions built on the cuioss-review-bot pack generator,
  without security. PLAN-LB-37 carries both, in one plan of two documents
  (`plans/PLAN-LB-37-functional-review.md`, D1–D9 with the hand-off command;
  `plans/companion-PLAN-LB-37-code-review.md`, D10–D16 — named so the spec probe resolves only
  the main document), drafted in the PLAN-LB-34 session and staged here unchanged apart from
  the number. It is a breaking change with a migration (`marshall-steward upgrade`) and two
  post-landing writes outside this repository: the consumer `marshal.json` rollout (D9) and the
  `cuioss/cuioss-review-bot` settings repository (D15). Operator decisions: "stage, but review
  first" — a read-only re-grounding of its claims and surface precedes the emit — and PLAN-LB-35
  and 36 superseded (their surfacer foundation is removed), PLAN-LB-26 re-scoped (it loses its
  edits to the deleted self-review workflow and waits for PLAN-LB-37). PLAN-LB-28 holds no
  self-review deliverable since the split of 2026-10-09. Salvage on the kept branch:
  `script-shared/scripts/git_lines.py`, the refusal of an unreadable footprint or diff, the
  `skill-domains set-extensions` input validation, a `CLAUDE.md` component-count correction.

- **PLAN-LB-24 review-step shipped on 2026-10-10 as #1742 (`7dd1d3433`).** Record:
  `landings/PLAN-LB-24.md`. Ten of the review's ten rows shipped, four with a deviation (the
  jittered wake after the rate window dropped; three extra outcomes for the no-new-commit
  reply; the CI-status half of the currency helpers deleted; the "fixed" reply held until the
  fix commit, GitHub only, with an escape). Of the anchor's checks: the claim window equals
  the wait budget (3600 s each, no grace); the full-review command is now a registered
  trigger but its "Full review triggered/finished" replies are still stored as findings
  (case-sensitive match); a "fixed" reply is not held until verify is green. Two defects in
  the code it shipped were observed on its own pull request: a stale quota notice settles a
  required bot that never reviewed, and CodeRabbit's "review in progress" summary is
  credited as a head-verified review. Its self-review used all five rounds and was closed by
  operator override at three heads, so the review-fix commits shipped without it. See Open
  Defects.

- **PLAN-LB-33 leaf-test-scope-and-executor shipped on 2026-10-10 as #1745 (`370f42379`).**
  Record: `landings/PLAN-LB-33.md`. Executor half met: a worktree run cannot overwrite main's
  executor, and an orphaned executor recovers. Test-scope half partly met: narrow units are
  offered only for a footprint inside one bundle, and the targets and harness trees that
  motivated the plan (PLAN-LB-29) still run whole-tree. It also introduced a fail-open:
  `--changed-paths ""` now reads as an empty footprint, so no test runs. The operator added
  two deliverables at execute that rebuilt the scope-creep guard (accepted finding type,
  merge-base baseline, configured threshold) — three of PLAN-LB-27's five scope-creep
  deliverables. PLAN-LB-27 is re-scoped in place; PLAN-LB-26, which declares the same guard,
  must re-ground against it. The executor template's format changed, so every existing
  executor reads stale until regenerated.

- **Inbox drain of 2026-10-10 (second), seventeen messages from PLAN-LB-24 and PLAN-LB-33:**
  - `lb-24-review-step-009` and `lb-33-leaf-test-scope-and-executor-008` (landings) —
    reconciled; both complete.
  - Promoted to the lessons corpus: `lb-24-…-001` as `2026-10-10-20-001` (re-trigger a
    required bot whose notice window elapsed), `-002` as `-20-002` (in-progress summary
    credited), `-003` as `-20-003` (full-review acknowledgment stored; carries the second
    sighting from `lb-33-…-001`), `-008` as `-20-004` (self-review after an operator
    override); `lb-33-…-003` as `-20-005` (consult misses a worktree-hosted outline), `-004`
    as `-20-006` (write-replace targets must exist), `-006` as `-20-007` (the self-review
    author is told to record mark-step-done), `-007` as `-20-008` (no sanctioned in-file
    search for a leaf).
  - `lb-33-…-001` — folded into `-20-003`; its own-trigger half was fixed by #1742, which its
    branch predated.
  - `lb-24-…-004` (scope-creep finding type) — fixed by #1745. `lb-24-…-005` (housekeeping
    reads the retired field) — fixed by #1741, which merged while PLAN-LB-24 was in finalize.
  - `lb-24-…-006` (`commit-add` rejects deliverable 0) — folded into PLAN-LB-26, which owns
    the triage fix-task path (PLAN-LB-06 D1). No surface added.
  - `lb-24-…-007` (lessons corpus emptied mid-finalize) — discarded: the `lessons-routing`
    ingest runs of 2026-10-09 retired the corpus, as recorded above.
  - `lb-33-…-002` (dispatch-boundary rows stop and carry no step id) — fourth landing;
    absorbed into the Open Defect.
  - `lb-33-…-005` (rate-window wait inside a leaf) — what PLAN-LB-24 D2 shipped. The leaf
    followed the old Branch 3 (a paced `sleep 60`), so it most likely ran the step text from
    before #1742 (not verified). Discarded; the Watch on live evidence for D2 covers it.

- **PLAN-LB-34, 35 and 36, staged on 2026-10-09: self-review surfacers for every domain.**
  PLAN-LB-34 is the operator's top priority. Measured with `corpus cross-check`: it shares
  no declared file with PLAN-LB-24 or PLAN-LB-32 (both running), and one with PLAN-LB-26
  (`pre-submission-self-review.md`) — sequence those two. PLAN-LB-35 and PLAN-LB-36 each
  share three entries with PLAN-LB-34 (the extension-point standard, the shared module, the
  plan-marshall surfacer's detector module), which is the dependency: neither starts before
  PLAN-LB-34 has landed. PLAN-LB-28 lost its self-review half to PLAN-LB-34 and overlaps no
  live plan.

- **PLAN-LB-33 leaf-test-scope-and-executor, staged on 2026-10-09 at high priority.** It
  owns two former Open Defects (per-task test scope; the main executor pointing into a
  removed worktree) and the executor half of a third (empty-string arguments dropped).
  Measured with `corpus cross-check`: it shares one conditional entry with PLAN-LB-32
  (running) — the plugin-doctor step document, touched only by its last deliverable, which
  waits for that landing — and nothing with PLAN-LB-24 (running), 25, 28 or 31. With
  PLAN-LB-26 it shares `phase-5-execute/SKILL.md` and `canonical_verify.md`, with
  PLAN-LB-27 `phase-5-execute/SKILL.md`. It is to be launched ahead of PLAN-LB-25 to 28.

- **Inbox drain of 2026-10-09 (third), six findings from the `lessons-routing` epic.** Its
  second ingest retired thirteen more lessons from the corpus, among them lessons this
  ledger cites by id (`2026-10-08-21-003`, `2026-10-09-13-001`, `-13-004`, `-15-001`,
  `-15-007`). **A lesson id cited here that the corpus no longer returns is to be read at
  `lessons-routing/lessons-archive/filed-live-blockers/{id}.md`.**
  - `-005` — its first item is PLAN-LB-32, which is running; its residual question is
    answered from that spec: the pre-push gate and ci-verify re-fires are left out there on
    purpose, with the other six head-dependent steps (see Watches). Its second item is a
    third baseline for the self-review Watch.
  - `-006` (scope-creep guard, fourth recurrence: exit 1 with an empty stderr) — folded
    into PLAN-LB-27. No surface added.
  - `-007` (five review-step and review-gate defects) — PLAN-LB-24 is running, so nothing
    is folded into its spec. Added to the checks at its landing; the four it does not
    appear to own are an Open Defect.
  - `-008` (per-task tests have no runnable scope) and `-009` (the main executor pointing
    into a removed worktree) — both already Open Defects here; each asks whether to stage.
    That is the operator's decision and is put to them.
  - `-010` (the outline's domain narrowing can empty `references.domains`, and the
    documented recovery call fails) — absorbed as an Open Defect; not verified at HEAD.

- **Standalone plan outside the queue, commissioned by the operator on 2026-10-08:** "the
  pre-submission self-review blocks on real defects, not on wording". It has no queue row and
  is not run through plan-marshall; the operator hands it to OpenCode. Brief:
  `doc/plans/live-blockers/self-review-materiality/plan.md` in the worktree
  `.plan/local/worktrees/self-review-materiality` (branch `fix/self-review-materiality`, cut
  from `3fe828c84`; the brief is untracked and is not to be committed). It adds a severity
  rubric, lets only `medium` and above loop, rewrites the verifier's stop question, adds a
  behavioural check over changed functions, and screens prose candidates. Basis, read from
  the archived plans: about 205 self-review findings in 40 plans, roughly a quarter real
  defects and more than half wording, every one filed at one constant severity.
  - **Shipped on 2026-10-09 as #1726, merge commit `d8b0284ef`** ("grade findings by severity
    and loop only on blocking ones"). Reconciled from the run's own final report, pasted by
    the operator, and checked against `ci pr queue-state --pr-number 1726` (merged, merge-group
    run `success`) and `git show --stat d8b0284ef` (18 files, 1486 insertions, 233 deletions:
    the workflow document, the extension-point standard, the surfacer skill and its four
    scripts, eleven test modules). The code was not read here.
    - What it reports as shipped, all six parts of the brief: the severity rubric in the
      surfacer skill only; `severity` and `failure_scenario` on findings, with only `medium`
      and above looping and filed; the verifier checking the grading and closing when nothing
      blocks; a `changed_code_units` list with a behavioural check 19; a screening question
      before prose checks and on-demand contract reads; the self-seeding rule removed. Its two
      cold reads matched (8 of 8 rubric grades; the verifier prompt answered as expected).
    - Deviations it reports: `changed_code_units` reads the syntax tree instead of the shared
      touched-function helper, which mis-reads docstring lines starting with `class`; the
      candidate gate and the verdict counts include the changed units; a store record later
      regraded to advisory is resolved with existing `manage-findings` verbs; the state
      finding keeps `--severity warning`.
    - **It merged, although the brief said to stop at an open pull request.** The run's first
      PR, #1725, was closed unmerged after CodeRabbit was rate-limited; #1726 replaced it and
      went through the merge queue. Whether the operator approved the merge in that session
      is not recorded here.
    - A review comment found a real gap, fixed before merge: a diff that only removes lines
      from a function was not listed for the behavioural check.
    - The run's worktree `.plan/local/worktrees/self-review-materiality` is gone
      (`git worktree list` on 2026-10-09 shows no entry for it), and the untracked brief
      went with it. Its removal left the main checkout's executor pointing into it; see
      Open Defects.
    - The three stale texts its report named were corrected by the same session as #1727
      (`2d9fc981f`, merged through the queue): `capability-gaps.adoc`,
      `dispatch-granularity.md` and `unreachable-guard-detection.md`.
    - Consequences for the queue: PLAN-LB-28 may now run (nothing else is editing the
      self-review workflow), but the PLAN-LB-03 claims it carries were verified before this
      change and name sections this change rewrote; the same holds for the PLAN-LB-08 claims
      in PLAN-LB-26 about the evidence-resolution paragraph. Both specs need their self-review
      claims re-grounded before launch. Running plans pick the new self-review up only after
      they rebase onto `d8b0284ef`.
  - It ran in Claude Code, not OpenCode, as a standalone `doc/plans/` session in its
    worktree, without plan-marshall (operator-confirmed on 2026-10-08).
  - **Released to the operator on 2026-10-08, after PLAN-LB-22 landed.** It had been held
    until then by operator decision. The brief was reconciled with commit `6b00815e0`: it now
    describes the loop-budget, grant, operator-close and rule-keyed state findings as existing
    and to be left alone; it gained a bounded Step 2a and an advisory channel for observations
    outside a round's candidates (from inbox message `-012` and the note in `-013`); the branch
    was moved onto `964d0bb4d`.
  - It edits `pre-submission-self-review.md`, which PLAN-LB-22 (running) is editing, and the
    surfacer skill that PLAN-LB-28 will edit. The brief names the sections each owns and
    tells the run to rebase; whichever of it and PLAN-LB-22 merges second resolves the
    overlap. PLAN-LB-28's outline must read what this plan shipped before scoping its
    PLAN-LB-03 deliverables, and PLAN-LB-26's PLAN-LB-08 deliverables keep their one-call
    edit in that file.

- **Sequencing inside the bundles** that the earlier notes asked for is now internal:
  PLAN-LB-05 D3 before PLAN-LB-18 before PLAN-LB-19 (all in 24); PLAN-LB-21 before the
  enrolment of PLAN-LB-20 (both in 31). Two cross-plan orders remain: 31's enrolment
  deliverables need the schema 30 releases, and 29 follows PLAN-LB-14.

- PLAN-LB-14 — the launch gate this plan fixes also gates this epic's own `next`. Until it
  lands, expect `next` to refuse and each launch to need an operator override. Two things
  were added to its spec on 2026-10-08: Step 4's overlap conjunct is refused by rows against
  archived sibling specs as well, so the plan must narrow that conjunct too; and the twenty
  superseded specs of this epic now count as indeterminate own specs until terminal rows are
  excluded.

- PLAN-LB-29 — three harness plans outside this epic were in flight on 2026-10-08 with no
  captured footprint (`harness-bundles-target-rules`, `selective-bundle-installer`,
  `steward-harness-config`). Check them before launching 29.

- **Drift since the specs were drafted** (HEAD `6edefac32` to `64b573110`): `planning.md` and
  `light-lane.md` changed, which affects the PLAN-LB-04 claims carried in 25; and
  `python-verify.yml` moved to the organisation's v0.37.0, which makes the pin claim carried
  in 30 stale. Both specs carry a verify-first clause saying so.

- **Re-grounded on 2026-10-08 at `726ca857a`** (`cleanup`). The eleven live specs carry a
  verdict on 281 claims: 259 corroborated, 13 unverifiable from this machine, 9 contradicted
  and re-scoped in place. No verdict blocks. The 151 remaining bullets are hypotheses that
  need a run or a decision, and verify-first clauses; they stay open for the launched plan.
  - The PLAN-LB-04 claims carried in 25 hold at HEAD: the light lane still has no `pr_title`
    producer.
  - The nine re-scoped claims: 22 (the simplify step reads the whole footprint, so "code
    files only" is not an admissible `verdict_inputs` declaration); 27 (a sixth staging site,
    the `land` script's path-bound `git add`); 30 (two claims: the pin is now v0.37.0, which
    still has no extra-buildable input); 31 (all seven repositories were enrolled on
    2026-10-06, six were never observed); 29 (four claims, see next bullet).
  - PLAN-LB-29 — the live state its evidence described has changed: the registry was
    repinned by hand to `0.1.1865` and is ahead of the executor (`0.1.1864`), and the cache
    manifest reads `0.1.1859`. The defect itself is confirmed in source (the sync never
    touches the registry), but it is not observable live today, and the executor now embeds
    source-tree paths. The plan must prove its parity verdicts on fixtures, cover a registry
    that is ahead, and read the executor version from `MARSHALL_VERSION`.
  - Unverifiable here: the dated store measurements in PLAN-LB-14, lessons
    `2026-10-07-07-007` and `-008` (absent from the lessons store), the `cuioss-review-bot`
    checkout (not on this machine), and three machine-local files.

- **Operator decisions the specs left open, for plans since shipped** (split from the live entry on 2026-10-14):
  - PLAN-LB-14 — whether a sibling spec that is only `staged` or `parked` can block a launch.
  - PLAN-LB-22 — how a plan already in finalize is read once the loop counter is per source.
  - PLAN-LB-24 — whether Sourcery may lose its credit when its review is not of the merge commit.
  - PLAN-LB-25 — write the PR title before the refine boundary, or defer the check to outline.
  - PLAN-LB-28 — what replaces `test -pl X -am` for modules using a sibling test-jar; and
    "done, not covered" with a warning, or halt and ask.
  - PLAN-LB-29 — whether the sync may write Claude Code's plugin registry.
  - PLAN-LB-30 — what to do if the organisation workflow release is not available; the two
    `project.yml` schema decisions; cutting the organisation release.

## Open Defects closed by PLAN-LB-143 (PR #1964, 2026-11-12)

Three Open Defects from the PLAN-LB-134 landing analysis, staged as deliverables 1 to 3 of PLAN-LB-143 on the operator's word of 2026-11-11 and
relocated here when that plan shipped. Detail of what the landing closed and what it left is in `landings/PLAN-LB-143.md`.

- **The OpenCode emitter expressed no tool restriction for any agent (D1, closed in code, not yet evidenced on an install).** The base policy was
  read at `opencode v2.2.7` (`GET /api/agent/execution-context-reader` returned `{*,*,allow}` first and denied only `browser` and `skill:browser`),
  so the reader could edit, write and run shell on the OpenCode target. The emitter now writes one `deny` row per mapped action an agent's source
  does not grant, never an allow or an ask, and the reader blocks of `opencode.json` lost their shell allows. What stays open and is carried in the
  landing report: the reader's restriction is not evidenced on an install until the OpenCode harness is synced and the same GET is read again, the
  deny set is a closed blocklist over the mapping's non-null values, and the lane's account of which agent gets which denies is wrong while the code is right.
- **`permission fix protect-path` and `ensure` refused a request a later broader row of the same effect already satisfied (D2, closed).** A satisfied
  request is a success with nothing added; a crossing of a partially overlapping rule is a conflict. One false conflict remains in the satisfied branch
  (a fully shadowed different-effect row before the satisfying row still counts as a crossing hazard; fail-closed).
- **A scalar `permission.bash` value was replaced by an empty map in six writers (D3, closed).** The writers keep a scalar as the map's own `*` row or
  leave `bash` alone; the map removal matches the effect; `web-apply` keeps a `webfetch` pattern map. `web-apply` still turns a `*` deny into `allow`
  on a map, which the spec itself orders; carried in the landing report.

## Dropped 2026-10-15

By operator instruction ("Drop (archive) low and medium findings on opencode runs. Focus on high
and critical"), with the severity rule recorded in `epic.md` § Decisions (2026-10-15). Dropped,
not fixed: an item that recurs at higher severity is re-staged from here after a re-check at HEAD.

### Deliverables removed from staged specs

- **PLAN-LB-48 former D5** — efficacy-doc and registry corrections
  (`doc/analysis/in-house-reviewer-efficacy.md` pointers to PR-description content that does not
  exist; `cuioss-review-bot.md` "moved nothing" claim and post-charter rows #1722, #1742, #1745,
  #1750). Medium: documentation truthfulness, no runtime effect.
- **PLAN-LB-49 former D4** — dispatch audit counting OpenCode sub-agent sessions; direct-`gh`
  audit reading `opencode.db` (the guard now refuses raw `gh`; PLAN-LB-42 made 0 calls); finalize
  dispatch-boundary rows and seam-written `[DISPATCH]` lines (PLAN-LB-39 lessons `-002`/`-005`).
  Medium: retrospective reporting.
- **PLAN-LB-52 parts** — request-named gate composition (`compose_request_project_gates`,
  `_manifest_core.py:608`, a dead path); infeasibility verdicts naming their spec sentence;
  `required_coverage_unknown` not fresh. Medium.
- **PLAN-LB-53 former D3** — phase time booked per interval across loop-backs (PLAN-LB-31
  2-refine 13h12m; PLAN-LB-39 5-execute 21h45m vs ≈9.6 h; PLAN-LB-42 ≈4.5 h of finalize booked
  to execute). Medium: metrics accuracy.
- **PLAN-LB-54 parts** — empty-store hash-cache regression and not-run reporting completeness
  (former D2: `q-gate-validation.md` L229, L283-295, L910-933, L1044, L1053; the vacuous Steps 6/8
  test); `domain-narrow --apply` and its `domains_unreadable` overload; stale outline docs
  (`phase-3-outline/SKILL.md` L604, L633; `light-lane.md` L244; would_empty routed as "could not
  evaluate"); the verb's minor defects. Medium/low: cost, unused surface, documentation.

### Open Defect items removed from `epic.md`

- **Compile run auto-closes quality-gate failures (PLAN-LB-26)** — re-checked at `8442a5e33`:
  largely fixed by `_build_examined.py` `FINDING_TYPE_ANALYSES` (lint split from compile;
  `test-failure` needs measured tests). Residue: a mypy-typed `build-error` from `quality-gate`
  can be cleared by a `compile` run that does not run mypy. Medium.

The PLAN-LB-26 and PLAN-LB-31 landing entries as they stood before the drop (owned items now point
at PLAN-LB-47, -52, -55, -57):

- **From PLAN-LB-26's landing** (`landings/PLAN-LB-26.md`, 2026-10-14):
  - **Regressions N1–N4 shipped in #1769** — owned by PLAN-LB-47 (staged): a red
    orchestrator-tier build can skip triage; triage never records the owning fix task on a
    Q-Gate finding; `module_testing` tasks never close under the per-task tier; a per-task leaf
    can receive `running`.
  - **The review barrier counts a current-head quota refusal as participation.** At `74e6bfda`
    `fetch_findings` listed CodeRabbit in both `participated_bots` (inline comments on the older
    head) and `refused_bots` (quota); `review_completeness check` resolved `participated`. Inline
    comments carry `commit_id ""`, so their staleness is undetectable. Nearest owner PLAN-LB-46.
  - **A compile run auto-closes quality-gate failures** ("auto-resolved by green build") because
    both are typed `build-error` — `script-shared/scripts/build/_build_shared.py`. Unowned.
  - **Metrics re-entry accounting is wrong**: a re-entered phase is reported as first-entry to
    last-exit (5-execute 12h28m absorbing four finalize passes), finalize counts its last pass
    only, and the quality report disagrees with the total (50,696 s vs 62,058 s). Unowned.
  - **Landing facts**: `emit-landing` runs before `archive-plan`, so `archive-plan:pending` is
    permanent; step facts carry no head binding; the residue mislabelled the optional sourcery as
    required. Nearest owner PLAN-LB-45.
  - **A plan session wrote the orchestrator ledger** (transition, anchor, view, raw commit in the
    ledger worktree) when the operator's command reached it without the leading `/`. Nothing
    stops a plan session from doing it. Unowned.
  - **`build-server wait result` log lines repeat hundreds of times** with identical hash and
    timestamp (work.log 426-599, 13813-14441). Low.
  - **Tier-1 routing verbs accept only `--request-text`**, which forced a hand transcription of a
    59 KB spec. Low.

- **From PLAN-LB-31's landing** (`landings/PLAN-LB-31.md`, 2026-10-14):
  - **Folded into PLAN-LB-48 (D5–D7) by operator instruction, 2026-10-14**: the doc/registry
    corrections, the enrolment and observation (asking once before the foreign writes), `ci pr
    reply --repo`, and a durable instrument with persisted tables (answering the operator's "why
    not fixing the script?"). The CodeRabbit Learning stored from the false triage reply is left
    in place by operator decision (2026-10-14: "just ignore / remove it from the list"). The text
    below is the record of what was found.
  - **Operator decisions owed.** (1) Enrolment of the thirteen deferred repositories and the
    first-PR observation (spec D6, D7) were not done: re-stage, asking once before writing to 13
    foreign repositories (schema released `v0.39.0`; the roster decision does not block).
    (2) The measurement: `doc/analysis/in-house-reviewer-efficacy.md` and the registry section of
    `cuioss-review-bot.md` point at PR tables that do not exist, name an instrument that was
    deleted, and overclaim the fixed-diff result (four rows were post-charter merged heads); the
    operator's "why not fixing the script?" is unanswered.
  - **A task's content for the PR description has no route into the PR body**; `create-pr` offers
    no channel, and the functional review accepted temp files as evidence that the PR description
    carries it. Unowned.
  - **The functional review never checks "Done when" outcome counts**: a verification-profile task
    with one read step and 0 of 13 enrolled was graded met. Nearest owner PLAN-LB-39 D6 (criteria
    integrity). Recurrence class of `lessons-routing-015`/`-026`.
  - **`ci pr reply` has no `--repo`**, so a comment on a foreign repository's PR can only be made
    with raw `gh`. Low. Owned by PLAN-LB-48 D6.
  - **Drift recovery can manufacture its own loop cap**: a refine Q-Gate that defers the rebase to
    finalize guarantees the next drift. Unowned.
  - **The retrospective's direct-`gh` audit is blind on OpenCode** — folded into PLAN-LB-49.
  - **The in-house review job is skipped or fails on a large share of PRs**: per the efficacy doc,
    skipped on more than a hundred candidate PRs and failed on twenty, against about two hundred
    posted reviews, across eight repositories (skip-label and Dependabot PRs already excluded).
    Required-bot coverage is silently absent there. The doc records it only as a yield caveat.
    Nearest owner PLAN-LB-46 (D5, a bot with nothing to review), but skips are broader than path
    filters — needs its cause established first. Unverified beyond the doc's own claim.

## DeepSeek Flash grades, second to fifth (measurement, out of scope)

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

## DeepSeek Flash grades, ninth to thirteenth (measurement, out of scope)

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

## Model comparison round and the eighth grade (measurement, out of scope)

- **Model comparison round (operator, 2026-10-19).** The next four runs after the four in flight
  stay on `deepseek-v4.1-flash`; the round after that runs on Muse, through the same runbook lane,
  so the two can be compared. DeepSeek so far under the runbook lane: LB-61 C+, LB-66 F, LB-67 C,
  LB-71 C−, LB-72 B−, LB-70 F, LB-59 C, LB-74 C, LB-68 C−, LB-76 C+, LB-45 C−, LB-77 B−, LB-48 B−, LB-81 C+, LB-78 B−, LB-79 C+ ($1.76, 5 sessions, 19 h 40 min, `deepseek-v4.1-flash/high` throughout, no switch; code
  graded on its work, report graded down for the undisclosed shell and clone conduct), LB-55 C+ (3 sessions, 14 h 17 min, `deepseek-v4.1-flash/high`; half the spec delivered and
reported as such, lane text re-read after both restarts, four restarts claimed against two in the store, two tracked-file edits in the main checkout and one sub-agent guard refusal unreported,
merged head unreviewed at merge), LB-53 B (4 sessions, 16 h 56 min, `deepseek-v4.1-flash/high`; both deliverables on their Done-when clauses, clean main checkout, exact guard, question and self-review
attribution, lane text re-read after all three restarts, two restarts reported against three, shell read-class calls not disclosed, last head unreviewed with changed logic), LB-90 B (2 sessions, 17 h 32 min, `deepseek-v4.1-flash/high`; all three deliverables test-first, exact question, sub-agent and guard counts, clean main checkout, 37 executor calls under a spoofed harness identity beyond the operator's answer, last head unreviewed), LB-95 B+ (5 sessions, 11 h 14 min, `deepseek-v4.1-flash/high`; all four deliverables delivered, all six tests then present failing at the base and the seventh mutation-checked, exact question (3), sub-agent (4) and guard (1) counts, clean main checkout, no spoofed identity, required reviewer reviewed the merged head, read-class shell calls 32 against about two dozen, one label contradicting its own failing log), LB-98 B+ (5 sessions, 5 h 37 min, `deepseek-v4.1-flash/high`; all three deliverables delivered with ten red tests in the cited job log, the fail-open case caught by the lane, exact question (3), sub-agent (4), guard (3 of 3) and read-class shell (8 of 8) counts, no restart, no main-checkout edit, CodeRabbit reviewed the merged head, a revert-after run labelled test-first, Sonar merged on the operator's override), LB-93 C+ (1 session and no self-review sub-agent, 5 h 25 min, `deepseek-v4.1-flash/high`; four of six deliverables delivered and verified, D5 half, D6 not started, the self-review skipped and reported as a rule break, exact question (3) and guard (1 of 1) counts, read-class shell calls understated, no restart, no main-checkout edit, honest account of its own state), LB-97 B (4 sessions, 15 h 41 min, `deepseek-v4.1-flash/high`; all four deliverables delivered with honest `mutation-after` evidence and cited job logs that exist and show what is claimed, exact question (5), sub-agent (3) and guard (3) counts, no spoofed identity, six real CodeRabbit findings fixed, 18 main-checkout operations at the start, the shared main executor regenerated from a scratch worktree and broken for a concurrent lane, one unreported restart, Sonar never decidable and merged on the operator's override), LB-58 B (5 sessions, 26 h 16 min including an operator pause, `deepseek-v4.1-flash/high`; all four deliverables delivered, evidence logs for D1, D2 and D4 matching exactly, D3's named population tests absent from the cited failing run, one clause unmet where my spec named a SHA the lane does not share, exact question (3) and sub-agent (4) counts, guard refusals 4 against 1 reported, read-class shell calls 3 against 1, clean main checkout, no spoofed identity, two real self-inflicted defects found by CodeRabbit and fixed, the "rebase" instruction handled honestly), LB-96 B+ (4 sessions, 8 h 02 min, `deepseek-v4.1-flash/high`; three of four deliverables as written and the fourth reported as unmet where my spec was wrong, all seven cited logs matching, exact guard (5), question (2) and sub-agent (3) counts, clean main checkout after one disclosed and reverted main-checkout edit, no spoofed identity, CodeRabbit reviewed the second-to-last head and re-triggered after the last push, read-class shell calls understated, residue honestly listed), LB-82 B (6 sessions, 14 h 39 min, `deepseek-v4.1-flash/high`; all four deliverables delivered, `mutation-after` for D1 to D3 and test-first for D4 with the four failing logs matching the PR body, exact question (4), sub-agent (5), read-class shell (4) and guard (0) counts, clean main checkout, no spoofed identity, honest self-report of its shell deviations, reviewer state at the final head misreported and one Minor thread merged open), LB-94 B (4 sessions, 8 h 02 min, `deepseek-v4.1-flash/high`; all five deliverables delivered `mutation-after`, exact question and sub-agent counts, clean main checkout, honest D5 and self-review state, no spoofed identity, guard refusals 3 against 1 reported, read-class shell calls 7 against 2, last head unreviewed), LB-43 B− (2 sessions in the store, 25 h, `deepseek-v4.1-flash/high`; lane text re-read after
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

## R5 and R6 enforcement bypass Watch, retired with PLAN-LB-88

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

## DeepSeek Flash grades, sixth and seventh (measurement, out of scope)

- **DeepSeek Flash runs, sixth and seventh grade (2026-10-20).** PLAN-LB-59 (`landings/PLAN-LB-59.md`,
  3 sessions, $0.62, 3h12m): **C**; 1 met / 1 partial of 2 deliverables, claimed 2/2. PLAN-LB-74
  (`landings/PLAN-LB-74.md`, 3 sessions, $0.80, 8h31m): **C**; 3 met / 1 partial of 4, claimed 3/4.
  Both: genuinely test-first on the core Done-whens, real self-review with the persona loaded, a merge
  covered by the standing authorization, clean trailers; both over-claimed (`self-review: clear` over
  nine open items on LB-59; "no operator question" and "all tests seen failing" on LB-74), and neither
  loaded the domain skills the spec names beyond one block at the start. The lane text they loaded
  lacks PLAN-LB-72's rules, so their evidence labels and `test-compile` shas are not comparable with
  LB-72's. Grades so far: LB-61 C+, LB-66 F, LB-67 C, LB-71 C−, LB-72 B−, LB-70 F, LB-59 C, LB-74 C.

## A spec edited in the ledger worktree reaches a run only through a ledger land (fixed by PLAN-LB-102)

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

## The lane's Sonar question in PLAN-LB-100: stale configuration, fixed by PR 1884

- **The lane's Sonar question recurred in PLAN-LB-100 (2026-10-29), now with its cause found: stale configuration, not the lane
  (recorded, not staged).** The LB-100 run asked the same question and was told to merge. `runbook_lane resolve` decides `configured`
  from `credentials_config.workflow-integration-sonar` in the tracked `.plan/marshal.json` (organization `cuioss`, project key
  `cuioss_plan-marshall`), and `default:sonar-roundtrip` was `lane: full` there. The operator confirmed the config is stale. The
  `sonar-roundtrip` lane is now `off`, the provider block is removed from `credentials_config` (left as an empty object), and the
  global token is removed. **FIXED (PR 1884, merge `9e731121c`, 2026-10-29):** `runbook_lane resolve` now reports
  `sonar: not_configured` and no longer carries a project key, so LB-101's lane has no Sonar question to ask. The block was removed by
  a direct edit of `.plan/marshal.json`, the operator's approval, because no script verb removes a provider block (`credentials
  remove` deletes the secret and leaves the block; a small plan could add that verb). CodeRabbit could not review that PR at all:
  its path filter excludes `.plan/**`, so it posted a skipped notice, and the merge went ahead on green CI plus Sourcery's approval.
  The PR ran two full verify builds, one on the PR and one in the merge group (about 30 minutes each), because
  `.plan/marshal.json` is on the workflow's forced-build list. A lane change (treat `sonar-roundtrip: off` as not configured) stays
  optional and rides the lane refactor decision.

## Routed-build failures from a worktree: the relative project directory (fixed by PLAN-LB-104, closed 2026-11-07)

- **A second routed-build failure from a worktree, with a trigger the lane did not name (PLAN-LB-100, 2026-10-29).** The first routed
  `quality-gate` with `--project-dir {worktree}` failed `execution_failed` (the worktree's `pwx` exited -1 with an empty log) and
  every later build ran in-process. The landing does not say whether the path was absolute. Unconfirmed as the known relative-path
  trigger; treat it as a recurrence of the routed-build Watch below until shown otherwise.
- **STAGED as PLAN-LB-104 on 2026-10-29 (operator: the build server is the lane's default; trigger CONFIRMED first-hand).** The daemon
  journal holds a matched pair of jobs, same worktree, executor and daemon: relative `--project-dir` died `execution_failed` (`pwx`,
  exit -1, 0 s), absolute ran `./pw module-tests` green. Cause: `_route_to_daemon` submits `*sys.argv[1:]` unchanged and the daemon
  runs it with the worktree as cwd, so the relative path is re-resolved against the worktree; `detect_wrapper` then finds no `pw` and
  the bare fallback (`pwx`, or `mvn` for Maven) is spawned. The lane text and `resolve` both emit the relative form. LB-100 then ran
  every later build in-process on its own initiative. **SHIPPED 2026-10-30 (#1893, B, `landings/PLAN-LB-104.md`): the fix is in
  source, and installed since the sync of 2026-10-30, so the two Watches below ("known trigger" and "still fall back after LB-92") stay open
  until one routed build with the relative form from the main checkout confirms it (D1's live-record clause, which could not be
  produced before the merge and can be now: the main executor runs the source tree).** The Maven report from another project is unconfirmed (spec's Verify-first
  clause; the lane did not read that journal).
- **Routed-build failure from a worktree has a known trigger (PLAN-LB-97, 2026-10-27).** The lane ran 72 routed builds with no
  degradation once `--project-dir` was ABSOLUTE; a relative path resolved against the daemon's cwd and fell back to a system
  `pwx` that is not installed. PLAN-LB-53 said the same. The five lanes that fell back (LB-55, LB-53, LB-82, LB-96, LB-58)
  most likely passed a relative path or hit this; the runbook-lane text could say "absolute" once. Recorded, not staged.

- **Routed builds from a lane worktree still fall back to in-process after PLAN-LB-92 (2026-10-25).** Both landings that ran
  after #1850 (PLAN-LB-55, PLAN-LB-53) report routed builds failing at setup: LB-55 "`pwx` unresolvable from the worktree
  (exit -1)", then every build `in_process_fallback`; LB-53 that a RELATIVE `--project-dir` resolves against the daemon's cwd
  and falls back to `pwx` (absolute values work), plus two whole-tree builds hitting the daemon's supervisory bound. Landing
  statements, not re-run here. Also both report `test_harness_shape_guards.py` whole-tree scanners passing in CI and standalone
  but exceeding 300 s under 32 k-test local load. None blocks a run (the fallback works); recorded to see whether a third
  run repeats it before anything is staged. **A fifth run repeats it (PLAN-LB-58, 2026-10-26; routed builds answered `exit_code -1` with an empty inner log).**
  **A fourth run repeats it (PLAN-LB-96, 2026-10-26; the daemon's inner `pwx` call from a cwd with no `pyproject.toml`).**
  **A third run repeats it (PLAN-LB-82, 2026-10-26):** the routed leg could not
  resolve the worktree's `./pw` (`pwx`, `exit_code -1`) and every build ran `--execution-mode in_process`; the same
  command from the main checkout succeeded. Operator decides whether it earns a plan.

## Standing authorization and a last head that changed logic (retired 2026-10-25)

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

## Non-Claude-Code Failures: retired and out-of-scope entries

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

## Open Defects of 2026-11-02 closed by PLAN-LB-105 to 110 and 119

- **HIGH — the success-criteria parser keeps only an unbroken run of `- ` lines, so every
  criterion after a wrapped or nested line drops out of the frozen snapshot unreported (2026-11-02;
  not staged).** Cited ground truth: `_criteria_snapshot.py:72` `_SUCCESS_CRITERIA_RE`, the single
  parser `outline_deliverables` uses. Because `criteria_drift` and `open_criteria` compare against
  the snapshot, a dropped criterion is never graded and never reported. API-Sheriff #467 and #513
  (`unknown_criterion_id`). The parked PLAN-LB-75 surface includes this file. — source: inbox
  `lessons-routing-065.md`.
- **HIGH — CodeRabbit participation is read from the wrong signals (2026-11-02; not staged).**
  Per-line thread replies at the new HEAD count as a review of that head; `coderabbit.md:50`
  requires no marker for `inline`. A finished review in the new summary format
  (`coveredCommitId == head`, `kind: reviewed`) is never credited, because only `runbook-lane`
  reads `coveredCommitId`. Since PLAN-LB-100, every such clean review needs `barrier-ask-override`.
  API-Sheriff #515 and #537. This is related to, but not covered by, the "Participation credit
  ignores an in-progress review" entry and parked PLAN-LB-46. — source: inbox
  `lessons-routing-066.md`.
- **HIGH (operator ruling) — the build daemon runs two builds in one worktree at once (2026-11-02;
  not staged).** The machine-global `max_slots` does not serialise jobs that share a
  `project_dir`, so a shared `target/` produces false ClassNotFound and Quarkus start failures
  (API-Sheriff PLAN-V02-10 and V02-14). Cited content search: no script keys any exclusion on
  the worktree. Exposure is wider since PLAN-LB-104 made routing the lane default. This relates
  to the Watch on the build server coalescing results (folded into PLAN-LB-78 D2 as a prose
  rule). — source: inbox `lessons-routing-069.md`.
- **HIGH (operator ruling) — a waiver accepted by a step record is refused by the merge gate
  (2026-11-02; not staged; recurs after PLAN-LB-55 and PLAN-LB-101).** `loop-back close
  --waive-refire` records `refire_waiver`, then `pre_merge_gate merge` refuses with
  `merge_candidate_not_gated` naming the same steps. Cited content search at `c431a8193`: no
  `pre_merge_gate` source reads `refire_waiver`. Further asks: derive the skip rule and the
  head-dependence from one source, and build the operator prompt from the barrier's own labels.
  Sightings: TokenSheriff PLAN-01/02/06, and API-Sheriff `-078` and #527. — source: inbox
  `lessons-routing-060.md` (revision 1).
- **HIGH (operator ruling) — the Maven log parser files a `test-failure` for a passing Surefire
  summary with `Skipped` above zero (2026-11-02; not staged).** API-Sheriff plan-25 #408, twice.
  The accepted-false-positive tuple reached `preference_min_recurrence`. A related medium item:
  `-Dtest=A+B` matches nothing. This sits next to the "PLAN-LB-28's test ladder" entry (epilogue
  lines still filed). — source: inbox `lessons-routing-061.md`.

## Open Defects retired or fixed in source in October (PLAN-LB-44, 71, 73 and the superseded OpenCode config entry)

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
- **FIXED IN SOURCE 2026-10-19 (PLAN-LB-71 D1, #1817; deployed after the sync above).** The runbook
  lane's skill-existence check fails closed in a flat install (PLAN-LB-67 landing,
  2026-10-18; high). `runbook_lane.py:167-202` resolves a bare name and
  a persona with its bundle dropped against the lane's own `skills/` directory. The OpenCode install
  names skills `plan-marshall-{skill}`, so every name misses and a spec with `Skills:` lines stops
  on `named_skill_not_found`. Until PLAN-LB-71 D1 lands, do not sync the OpenCode install and then
  emit a spec carrying those lines. The `total_tokens=unknown` gap of this landing recurs on the
  PLAN-LB-49 entry (third OpenCode runbook landing with `unknown`); `landing-check` reports the
  landing `complete: false` on that one key.
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

## Open Defects fixed, retired or out of scope in October (merge path, recovery command, Sonar read, measurement, R5 walk)

- **The merge-path part of this item was fixed in source by PLAN-LB-100 (#1883, 2026-10-29); the rest is PLAN-LB-101.** The
  `pre_merge_gate merge` participation check and the merged-under-authorization record exist now; the roster, trigger, option and
  loop items below are unchanged and are LB-101's. **The gate-truth half of PLAN-LB-55 is unshipped, and it sits in the lifecycle lane only (PLAN-LB-55 landing, 2026-10-25;
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

## Executor and flat-install Open Defects fixed in source (PLAN-LB-94, 95, 96, 97, 110)

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
- **MEDIUM — a Maven consumer's task-time gate cannot reach the new Maven scope verb (recorded 2026-10-27 from the PLAN-LB-58
  landing residue; not staged).** `execute-task` hardcodes the `build-pyproject` notation for its per-task gate, so the Maven
  `resolve-test-scope` verb PLAN-LB-58 added is reached by the finalize gate (which resolves it dynamically) but not at task
  time. No false pass: the finalize gate still runs it.
- **HIGH — a flat install cannot complete the `marshall-steward` upgrade on this machine (found 2026-10-26 on the `pm-mcp-core`
  project; FIXED IN SOURCE by PLAN-LB-97, #1872, merged 2026-10-27; not live on any install until the next sync, executor
  regeneration and repin here, and the new plugin version on the second machine; the `OPENCODE`-unset workaround stands
  until then).** `manage-config sync-defaults --backfill-bot-roster` stops with `step body doc
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

## Executor-skew, ledger-first spec read and incomplete-landing notes (fixed in source, PLAN-LB-98, 99, 102)

- **INCOMPLETE LANDING — `rb-lb-99-source-checkout-executor-skew-001.md` (2026-10-28; `inbox landing-check` reported
  `complete: false`, `missing_keys`: `total_tokens`).** The lane wrote `total_tokens=unknown` while the OpenCode session store
  holds the figures for the root and the child session. The landing was drained and reconciled as far as its facts go; the
  tokens are recorded in `landings/PLAN-LB-99.md` from the store. Token and measurement work is out of scope under the focus
  rule, so nothing is staged.
- **FIXED IN SOURCE (PLAN-LB-99, #1878, 2026-10-28; LIVE after the next sync, since a harness loads the installed lane text) — `executor-skew` STILL cannot answer in this repository's own lanes (found 2026-10-27 right after the sync of
  `0.1.2025`; owner PLAN-LB-99, STAGED 2026-10-28 with ONE outline decision rather than a prescribed mechanism: the operator
  challenged my first idea (derive a version from tree evidence) and the check showed `generate_executor preflight` already
  answers staleness but regenerates the executor in place when it is stale, so it is not a read-only witness; the candidates are
  an explicit `not_applicable` verdict for a source checkout, a read-only variant of preflight, or leaving the question).** PLAN-LB-98 is live and correct on a flat install: the installed
  OpenCode copy reads the stamp (`0.1.2025`), returns `skew` for a `0.1.2021` executor and `match` after regeneration (run here
  with the installed lane copy called directly). But this checkout's executor maps `runbook_lane` (and every script) to the
  SOURCE tree (`marketplace/bundles/plan-marshall/skills/runbook-lane/scripts/runbook_lane.py`), so a lane in this repository
  runs the source copy, whose layout is "nested, no version directory": `could_not_check`, now with the reason `lane text
  version unknown: no version directory under …/marketplace/bundles/plan-marshall`. The operator will therefore still get the
  question in every lane of this repository. In a source checkout the executor is generated from the tree, so the real risk is
  an executor older than the tree's scripts; the tree carries the evidence for that (the `target/{harness}/dist-manifest.json`
  fingerprints, or a comparison of the executor's script fingerprint with the tree), and nothing reads it. LB-98's own landing
  records the source-checkout limit ("the reading checkout is a source tree"); my LB-98 spec did not name it and its
  reproduction (`env OPENCODE=1 …`) ran the source copy, not the flat one, which I presented as the flat copy. Mine to correct.
- **FIXED IN SOURCE (PLAN-LB-98, #1876, 2026-10-27; LIVE since the sync of `0.1.2025` on flat installs) — `executor-skew` answered
  `could_not_check` on every flat OpenCode install; high by operator ruling "it is high"; found in the PLAN-LB-95 landing,
  2026-10-26; asked again by the PLAN-LB-93 lane, 2026-10-27).** Beyond the avoidable question, on the second machine the same verdict sat on a stale executor (`0.1.2010`)
  and hid it. A flat install carries a version witness the check does not read: the sync's `dist-manifest.json` at the install
  root. Earlier text of this entry, written at medium: A flat install has no `{bundle}/{version}` directory, so the lane text version cannot be derived and each
  OpenCode lane asks the operator two questions that cannot change the outcome (LB-95 asked both; regenerating the executor
  did not change the verdict). Related to PLAN-LB-96, which makes the flat install resolve its bundles root, but not part of
  it. Under the high-and-blocking focus rule this waits.
- **FIXED IN SOURCE (PLAN-LB-102, #1882, 2026-10-28; LIVE after the next sync, since a harness loads the installed lane text) — the
  emitted lane command could not read a spec from the ledger worktree (PLAN-LB-90 landing, 2026-10-25; high).** The lane now reads the
  ledger worktree's copy first and falls back to the main checkout by default (operator ruling 2026-10-28), so an emitted command needs no
  flag and no ledger land after a spec edit; `--spec-from-ledger` stays accepted as a documented no-op. Verified live on the merged
  tree: `resolve` on LB-101 with no flag answers `spec_source: ledger_worktree`. Until the sync, an installed lane text still says the
  main checkout is the default, so land the ledger before an emit that follows a spec edit.
- **INCOMPLETE LANDING — `rb-lb-102-ledger-first-spec-read-001.md` (2026-10-28; `inbox landing-check` reported `complete: false`,
  `missing_keys`: `total_tokens`).** The lane wrote `total_tokens=unknown`. The landing was drained and reconciled as far as its facts
  go. Token and measurement work is out of scope under the focus rule, so the figure was not recovered and nothing is staged.

## Sonar closed by ruling, the PLAN-LB-100 merge-path half, and its incomplete-landing note

- **CLOSED BY OPERATOR RULING (2026-10-28): Sonar is not enabled for this project and is ignored for all plans; nothing is
  staged and the text below is the historical record.** ~~HIGH — the Sonar merge gate is unattainable on this repository, so
  every merge needs an operator override (found in
  the PLAN-LB-97 landing, 2026-10-27; confirmed by PLAN-LB-93 and PLAN-LB-98; NOT STAGED, needs an operator decision).~~
  PRs #1872, #1874 and #1876 all ended with `read_open_issues` answering `undecidable` / `analysis_revision_unavailable` and
  merged on the operator's explicit "merge anyway". Cause, verified: `.github/project.yml` has had `sonar: enabled: false` since
  the first commit (2026-02-21), so CI submits no pull-request analysis, while the project's provider block resolves
  `sonar: configured` for `cuioss_plan-marshall`. The provider holds three PR analyses (PRs 766, 801 and 802), the newest from
  2026-06-29. The gate PLAN-LB-58 added correctly fails closed. Options: enable Sonar analysis in CI, or make the provider
  block resolve `unconfigured` when `sonar.enabled` is false so the gate does not demand an analysis nobody submits. **Correction
  that follows:** every "Sonar 0" I recorded for this repository's PRs since 2026-06-29 (the LB-95, LB-82 and LB-96 landing
  records and their epic lines) came from the pre-LB-58 behaviour, which counted issues on whatever the provider returned; as the
  provider holds no analysis for those PRs, those confirmed zeros can only have read an absent analysis as zero (my inference,
  from the list above and the confirmed `0` reads I made). Those figures are not evidence of a clean analysis. LB-58's own landing reports confirmed
  live reads at two heads of PR 1866; I cannot reconcile that with the provider's current list and have not tried to.
- **MERGE-PATH HALF FIXED IN SOURCE (PLAN-LB-100, #1883, 2026-10-29; LIVE after the next sync); the review-policy half is staged as
  PLAN-LB-101.** `pre_merge_gate merge` now refuses an unproven required-bot participation (`merge_participation_unproven`), a merge
  under an authorization is recorded by `record-merge`, and the merge question's consequence sentence is generated from the knob.
  The roster-read error, stale-bot trigger-before-ask, no-demotion options and the quota loop below are LB-101's. Original entry:
  **HIGH — the gate-truth half of PLAN-LB-55 is still not shipped (PLAN-LB-93 landing, 2026-10-27).** LB-93 shipped
  the push-vs-armed-merge refusal and left D5's second bullet (the participation check inside `pre_merge_gate merge`) and all
  of D6 (the `step-params` empty-roster error, the stale-bot re-trigger, generated barrier options with no "make the required
  bot optional", the rate-window loop, the merged-under-authorization record, the merge-anyway mutex re-acquisition, and the two
  remedies in `branch-cleanup.md` L1041 and L1222). Second deferral (LB-55 first). Needs a plan.
- **INCOMPLETE LANDING — `rb-lb-100-merge-path-truth-001.md` (2026-10-29; `inbox landing-check` reported `complete: false`,
  `missing_keys`: `total_tokens`).** The lane wrote `total_tokens=unknown` (OpenCode measured none). The landing was drained and
  reconciled as far as its facts go. Token and measurement work is out of scope under the focus rule; nothing is staged and no
  figure was recovered.

