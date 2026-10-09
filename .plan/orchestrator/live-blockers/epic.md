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

The queue was regrouped on 2026-10-08 (see Decisions). Eleven plans are live: PLAN-LB-14 and
PLAN-LB-22 to PLAN-LB-31. PLAN-LB-01 to PLAN-LB-13 and PLAN-LB-15 to PLAN-LB-21 are
`superseded`; their spec files stay as the record of the first cut.

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
- **Foreign checkout paths.** The specs carried into 28, 30 and 31 name sibling repositories
  as `/Users/oliver/git/...`. Each of those specs carries a clause to resolve the names under
  the checkout root of the machine the plan runs on.
- **Operator decisions the specs leave open** (each is a verify-first clause in its spec):
  - PLAN-LB-14 — whether a sibling spec that is only `staged` or `parked` can block a launch.
  - PLAN-LB-22 — how a plan already in finalize is read once the loop counter is per source.
  - PLAN-LB-24 — whether Sourcery may lose its credit when its review is not of the merge commit.
  - PLAN-LB-25 — write the PR title before the refine boundary, or defer the check to outline.
  - PLAN-LB-26 — sticky resolutions with an opt-in reopen of `fixed`, or always reopen `fixed`.
  - PLAN-LB-27 — how legitimate out-of-footprint edits by finalize steps get in.
  - PLAN-LB-28 — what replaces `test -pl X -am` for modules using a sibling test-jar; and
    "done, not covered" with a warning, or halt and ask.
  - PLAN-LB-29 — whether the sync may write Claude Code's plugin registry.
  - PLAN-LB-30 — what to do if the organisation workflow release is not available; the two
    `project.yml` schema decisions; cutting the organisation release.
  - PLAN-LB-31 — running `gh`-based corpus scripts, posting `/review` on merged PRs, the
    roster decision itself, and whether to enrol after it.

## Decisions

- 2026-10-07 — **Epic created by operator instruction** ("create an orchestrator for the
  critical / high; remove them from the current orchestrator; archive / dormant the other
  orchestrators beside lessons-routing"). Scope is the 21 high-priority clusters of the
  cross-epic sweep; the roughly 50 medium and low clusters are recorded in `backlog.md` and are
  not staged. Alternative considered: stage all 70 — not chosen, the operator asked for
  critical and high only.
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

## Open Defects

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

## Watches

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

- **A landing from the Antigravity harness reported `total_tokens=0`** (PLAN-LB-30) and still
  passed the completeness check, which accepts any value that is not `n/a` or `unknown`.
  — trigger: stage it if a second landing from that harness reports zero.
- **PLAN-LB-24 must rebase onto PLAN-LB-22's landing** (`6b00815e0`). It changed
  `phase-6-finalize/SKILL.md`, `automatic-review/SKILL.md`, `triage.md` and
  `verification-feedback.md`, which PLAN-LB-24 declares. PLAN-LB-23 has landed. — trigger:
  PLAN-LB-24's pre-merge rebase; retire when it has landed.
- **Head-dependent finalize steps re-fire in full on every fix commit.** PLAN-LB-22 recorded
  a refusal to declare `verdict_inputs` for the two steps it examined; lessons-housekeeping
  and plugin-doctor fired seven times each with identical results. Lesson
  `2026-10-08-21-003` carries the proposal. — trigger: stage it as a plan if the next two
  landings report the same cost.
  - **Staged on 2026-10-09 as PLAN-LB-32, at high priority, by operator instruction.**
    Retire this Watch when PLAN-LB-32 lands and one later landing reports the two steps'
    re-fires as carried over or skipped.
  - **Trigger met on 2026-10-09.** Of the two landings
    since, PLAN-LB-30 had no fix commit and so no re-fire; PLAN-LB-23 had both steps fire
    eight times with identical verdicts ("0 rm, 0 promo, 0 adapt, 64 keep"; plugin-doctor
    clean), at a floor of 1,680,033 tokens, and its decision log reached 710 entries
    because each firing logs one line per retained lesson. That is three landings with the
    cost (PLAN-LB-14 five firings, PLAN-LB-22 seven, PLAN-LB-23 eight). The message adds
    two proposals to the lesson's: a delta prefilter for housekeeping, and one aggregate
    log line per firing. — source: inbox message `lb-23-verify-builds-003.md`.
- **PLAN-LB-29 must rebase onto PLAN-LB-14's landing** in `orchestrator.py` and
  `plan-orchestrator/SKILL.md`. — trigger: when PLAN-LB-29 reaches its pre-merge rebase or
  reports a conflict; retire when it lands.
- **The archived-epic tree left `main`** (#1717, `1e556f15d`: archived plans and orchestrator
  records moved to plan-marshall-telemetry). Claims in the live specs that cite a file under
  `.plan/archived-orchestrators/` were corroborated before that move and can no longer be read
  in this repository. — trigger: when a launched plan's outline reports such a claim as
  unreadable, point it at the telemetry repository.
- **Three plans outside this epic had no captured footprint** when last read
  (`harness-bundles-target-rules`, `selective-bundle-installer`, `steward-harness-config`).
  The gate PLAN-LB-14 shipped still refuses while a live plan has neither a footprint nor an
  orchestrated source spec. — trigger: the first `next` run on the new gate; retire when it
  reports the comparison determinate.

- **Harness installs lag the source after every landing** until PLAN-LB-15 ships: the plugin
  registry pin is behind the executor. A session may run stale skill text. — trigger: before
  trusting a skill's behaviour right after a landing, compare the registry pin with
  `MARSHALL_VERSION`; retire when PLAN-LB-15 lands.
- **`plan-pr-078-review-bot-fleet-opt-in` is still listed as in progress at finalize** with a
  dead worktree pointer and its archive step never run; four consumer checkouts are still on
  its merged branch. — trigger: clean up by hand or when the worktree-pointer fix
  (`backlog.md` § 1.14) is promoted.
