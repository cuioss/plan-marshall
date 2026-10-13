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
- **PLAN-LB-37 is landing in parts.** Four part-PRs are on `main`: #1754 (`fc0090a24`, rubric,
  `review_support` helper, harvestable rules), #1755 (`730f37a2f`, the functional-review and
  code-review steps and the code-review packs), #1757 (`77ef084ad`, every reader moved off the old
  step) and #1758 (`47d21e1bf`, the old step and the surfacer apparatus retired, configurations
  migrated). The row stays `running` until its landing message arrives; the post-landing
  consumer rollout (D9/D10) and the bot settings change (D15) are still to come.
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
- 2026-10-09 — **parallelization_scope raised from 2 to 4 by operator instruction** ("set
  the parallelism to 4"). Four plans were already running on per-launch overrides
  (PLAN-LB-24, 32, 33 and 34); the knob now matches what the operator runs. The limit on
  real parallelism is unchanged: plans that share `phase-6-finalize/SKILL.md`,
  `execution.md` or the self-review workflow still run in sequence.

## Open Defects

- **Antigravity: critical, by operator ruling of 2026-10-12 (the epic's highest priority).**
  All from pm-mcp-core PLAN-41 (pm-mcp-core PR #34), the first plan of that epic run under
  Antigravity; the ingest verified against the archived plan, not at HEAD here unless noted.
  None is owned by any staged plan. Full bodies at
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
    — `lessons-routing-028.md` (148).
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
    standing finalize triage source. Check at PLAN-LB-37's landing whether its functional review
    catches (1), (2) and (4). Evidence rests on the sender's audit, not re-checked here.
    — `lessons-routing-026.md`.
  - **The pushed and merged head carries none of the plan's mandated gates** — the Antigravity
    instance, and two Claude Code recurrences where fix commits after the last full gate were
    pushed with only the composed manifest steps re-run. Graded high for Claude Code.
    — `lessons-routing-016.md`.
- **A deliverable in a sibling repository has no lifecycle** (high; critical in its Antigravity
  instance): no plan-owned worktree, no finalize step pushes it or opens its PR, the footprint
  ignores it, and the foreign-PR gate assumes `feature/{plan_id}`
  (`phase-6-finalize/scripts/foreign_pr_gate.py:170-171`), so it both blocks a merged foreign PR
  and misses a missing one. Recurs on every pm-mcp-core plan that changes a specification. Not
  owned by any staged plan. — `lessons-routing-018.md`. Two more plans (PLAN-13, PLAN-18): the
  retrospective footprint reports every sibling path as declared-but-unrealised, so M6 fails by
  construction; relative sibling paths break under `use_worktree`; a sibling deliverable has no
  module name in the architecture. — `lessons-routing-028.md` (168, 175, 176, 181).
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
- **Red CI has no triage route.** `verification-feedback.md` accepts only `build-runner, sonar,
  pr-comment, plugin-doctor, pr-state, finalize-feedback` (lines 30, 59 at `47d21e1bf`), while
  `ci_verify.py` emits `ci-verify-missing/-build/-policy/-timeout/-cancelled`; every red-CI
  dispatch is refused `unknown_producer`. Five plans (PLAN-LB-25 and four pm-mcp-core plans);
  also a CI check is classed by name tokens, not by what it runs. Lesson `2026-10-11-16-001`.
  Not owned by any staged plan. — `lessons-routing-019.md`, `lb-25-phase-and-merge-gates-001`.
  Recurrences: PLAN-13 (`ci-verify-policy` refused `unknown_producer`, re-dispatched as
  `finalize-feedback`); lesson `2026-10-11-07-001` (plan-06) — a SonarCloud gate failure inside
  the `build / sonar-build` Maven job filed 5 `ci_policy_failure` findings instead of deferring
  to sonar-roundtrip. — `lessons-routing-028.md` (153, 189).
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
- **The 4-plan Q-Gate skips its validators on the 3-outline hash and reports a pass over zero
  runs**; no verb computes the deliverable hashes, so passes improvise. Graded high by the
  operator. Not owned by any staged plan. — `lessons-routing-023.md`. Recurred on PLAN-18: both
  Q-Gate runs skipped `deliverable-hashes.toon` (16 hashes over 2 runs); the 4-plan leaf had no
  shell. Asks for a `manage-solution-outline deliverable-hashes` verb.
  — `lessons-routing-028.md` (185).
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
  `verification-feedback.md` and the remaining `phase-6-finalize` documents are left. Lesson
  `2026-10-13-07-002`. Not owned by any staged plan. — `lb-37-functional-review-004.md`.
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
  - **Closed by PLAN-LB-33 (#1745):** a generation from another checkout is refused and
    leaves main's executor byte-identical (`cross_checkout_refusal`), and an orphaned
    executor recovers from the cache or the checkout's sources. Remove this entry at the next
    cleanup. The template format went from 4 to 5, so every existing executor reads stale
    until it is regenerated.
- **The root `opencode.json` is in a shape nothing in this repository reads.** PLAN-LB-29's
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
- **An empty `--changed-paths ""` runs no tests.** PLAN-LB-33 D9 made the executor keep an
  empty option value; `pyproject_build.py:295-296` reads it as an empty footprint and returns
  `divergence_possible: false`. Before D9 the value was stripped and argparse failed loudly.
  So a Step 5(b) whose `{changed_paths}` resolves empty skips pytest and reports success.
  Related, advisory: `architecture resolve --narrow-unit ""` falls back to the module-wide
  resolve without `bound_source`. **Closed by PLAN-LB-38 (#1752):** both empty values are
  refused (`empty_changed_paths`, `empty_narrow_unit`), and a task with no changed file
  resolves by `--plan-id`. Remove this entry at the next cleanup. — source: read-only review
  of `370f42379`, 2026-10-10; advisory list of the PR #1745 body.
- **The self-review's author leaf is briefed to record a step it must not record.** On
  PLAN-LB-33, every author leaf of seven firings returned without `mark-step-done`, as the
  workflow requires (the verifier runs from the orchestrator), and later briefs still said
  "record before return"; one dispatch named the workflow under `standards/` and failed with
  `workflow_not_found`. Lesson `2026-10-10-20-007`. PLAN-LB-34 (running) edits
  `pre-submission-self-review.md` but not the finalize dispatcher. — source: inbox message
  `lb-33-leaf-test-scope-and-executor-006.md`.
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
- **The `migrate-review-steps` steward migration is meant to go.** PLAN-LB-37 D8 added it on
  operator instruction, to be removed by a later plan once every configured repository has been
  migrated by PLAN-LB-37's post-landing rollout (scope: `marshall-steward/scripts/upgrade.py`
  `migrate-review-steps` and `_merged_review_params` with its SHIM(A) block, the steward
  `SKILL.md` and `references/upgrade-flow.md`, `test_review_step_migration.py` and cases in
  `test_upgrade.py` / `test_upgrade_flow_stage2.py`, the plugin-doctor shim-marker figures).
  — trigger: PLAN-LB-37's landing reports the rollout complete for every repository, or the
  operator confirms none still needs it. — source: `lb-37-functional-review-001.md`.
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
- **Three plans outside this epic had no captured footprint** when last read
  (`harness-bundles-target-rules`, `selective-bundle-installer`, `steward-harness-config`).
  The gate PLAN-LB-14 shipped still refuses while a live plan has neither a footprint nor an
  orchestrated source spec. — trigger: the first `next` run on the new gate; retire when it
  reports the comparison determinate.

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
