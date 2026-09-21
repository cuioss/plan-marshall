# Epic: Finalize machinery — retire the recurring phase-6 defects

slug: finalize-machinery

> Ledger document for one epic under `.plan/orchestrator/finalize-machinery/`. The layout
> and authority contract live in the central standard — see
> `persona-plan-orchestrator/standards/orchestration-model.md`. `status.json` is the
> machine authority; any statement here that conflicts with it is stale prose.

## Vision

This epic exists because `operator-ux` was becoming the finalize lane's defect inbox. Across
five landings that epic observed, recorded, and could not fix a growing population of
`phase-6-finalize` and lessons-pipeline defects: none of them were operator-UX work, no plan
anywhere owned them, and the lessons corpus grew monotonically while its retirement rate stayed
at zero. The operator decided on 2026-09-03 to split them out rather than fold maintenance into
a UX epic.

The goal is **retirement, not observation**. A lesson in the corpus with no owning plan is a
defect the system has learned to live with; this epic's output is landed fixes that let those
lessons be retired, plus the confirmation runs that justify retiring them.

Two themes dominate the inherited material and are the likely workstream split:

1. **Cost** — finalize consistently costs 3–5× execute, and PLAN-10 identified the mechanism: a
   HEAD move inside finalize re-arms every head-bound step. One run fired the quality gate four
   times for three tasks. This is the highest-value single target in the inherited set.
2. **Invocation surfaces that do not teach their own fix** — nine argparse rejections in one
   run across four signatures, several recurring from independent callers, and one trap hit by
   the orchestrator session that had the documenting standard open at the time. Documentation
   has demonstrably failed to hold this class; the remedy has to live in the rejection message.

## START HERE

<!-- GENERATED BLOCK — never hand-write or hand-edit this section.
     Regenerate after every queue-touching state change via:
     python3 .plan/execute-script.py plan-marshall:plan-orchestrator:orchestrator resume-summary --slug finalize-machinery
     Paste the returned `summary` block verbatim between the markers (the same
     invocation also emits `ordered_queue` for the Ordered Queue section below).
     Anything a reader wants to add BY HAND goes in the annotation zone below,
     outside the markers — never inside them. -->

<!-- BEGIN GENERATED: resume-summary -->
**Resume anchor**: COMPLETE 2026-09-18: all 7 plans shipped (#1505, #1507, #1510, #1509, #1527, #1525, #1530); inbox drained (0 queued); no staged or running rows. Next: operator decides close/archive; open items: stray lesson file deletion, defect 2 (PLAN-06 narrative landing), cuioss-demotion + pco-overlap watches.
**Phase**: orchestrating
**Inbox (derived)**: 0 queued, 35 archived
**Queue** (staged, in order):
- (empty)
- PLAN-01 (WS-01) — PR 1505 — landing=landings/PLAN-01.md — status: shipped
- PLAN-02 (WS-02) — plan=invocation-surfaces — PR 1507 — landing=landings/PLAN-02.md — status: shipped
- PLAN-03 (WS-03) — plan=plan-03-review-currency — PR 1510 — landing=landings/PLAN-03.md — status: shipped
- PLAN-04 (WS-03) — plan=git-branch-mechanics — PR 1509 — landing=landings/PLAN-04.md — status: shipped
- PLAN-05 (WS-04) — plan=lessons-pipeline — PR 1527 — landing=landings/PLAN-05.md — status: shipped
- PLAN-06 (WS-04) — plan=plan-06-anchors-and-mutex — PR 1525 — landing=landings/PLAN-06.md — status: shipped
- PLAN-07 (WS-04) — plan=plan-07-session-identity — PR 1530 — landing=landings/PLAN-07.md — status: shipped
<!-- END GENERATED: resume-summary -->

### Annotations

<!-- ANNOTATION ZONE — hand-written, and deliberately OUTSIDE the generated markers. -->

- **Scaffolded 2026-09-03, NOT yet decomposed.** The next action is
  `/plan-orchestrator decompose slug=finalize-machinery`, working from the inherited material
  below. `parallelization_scope` is unset and must be chosen at decompose.
- **2026-09-05 — the inherited set grew by a source the epic did not anticipate.** An
  unorchestrated plan (`unreviewed-merge-gate-holes`, PR #1409) worked this epic's exact surface
  without a ledger row anywhere. Two open gate holes and four new lessons were transferred; see
  the new subsection under Inherited Material. ⚠️ The general point outranks the items: **work on
  this epic's surface is already happening outside every epic's gate**, so decompose must expect
  its staged specs to be moved under by plans no cross-check can see.

## Ordered Queue

<!-- GENERATED BLOCK — never hand-write or hand-edit the table between the markers.
     Regenerated from status.json and the staged specs: emitted as `ordered_queue` by
     orchestrator.py resume-summary --slug finalize-machinery, and rewritten in place by the
     compact stage at cleanup. Only the LIVE queue is rendered here. Per-row notes a reader
     wants to ADD go in the annotation zone below, outside the markers. -->

<!-- BEGIN GENERATED: ordered-queue -->
| # | Plan | Workstream | Status | Surface (expected) |
|---|------|------------|--------|--------------------|
| — | (empty) | — | — | — |
<!-- END GENERATED: ordered-queue -->

### Queue annotations

<!-- ANNOTATION ZONE — hand-written, and deliberately OUTSIDE the generated table markers. -->

- DECOMPOSED 2026-09-16: 4 workstreams, 6 staged plans, scope N=2.
- PLAN-01 (WS-01) runs first in effect: highest value, and its ordering decision
  constrains the gate work. PLAN-04 sequences behind PLAN-01 (shared
  phase-6-finalize standards directory, different files).
- PLAN-02 and PLAN-03 are file-disjoint inside automatic-review (SKILL.md wording vs
  gate scripts) and may parallelize; either widening its surface forces sequencing.
- PLAN-05 and PLAN-06 are file-disjoint (ledger/retrospective vs locks/build/handshake)
  and may parallelize.
- STANDING OPERATOR RULE (2026-09-16, opencode + Muse Spark 1.3): every staged spec
  carries a ## Execution Contract section mandating strict plan-marshall process
  compliance, and every future spec staged in this epic gets one. The emitted
  /plan-marshall command stays a bare one-line file pointer — the compliance clause
  MUST NOT be appended to the task string, because phase-1-init classifies a pointer
  by syntax (bare `implement` + single path token, nothing else) and extra prose
  would route the plan to the plain-text branch with the spec body never ingested.

## Decisions

- **Epic opened 2026-09-03 at operator decision**, taken via `AskUserQuestion` during an
  `operator-ux` analyze drain. The alternatives offered were to keep parking these lessons in
  the corpus (rejected: the dedup burden already costs a manual per-message comparison against
  a 68-lesson corpus on every drain, and it scales with corpus size) and to fold the worst
  offenders into `operator-ux` (rejected: it would convert a UX epic into a maintenance
  backlog, the exact outcome that epic's standing Watch was opened to prevent). The full
  reasoning is in `operator-ux`'s `logs/decision.log`.
- **Inbox invocation-surfaces-002 discarded** (2026-09-17 drain): the candidate lesson
  ("name flag + sibling verb in argparse rejections") restates the remedy PLAN-02 just
  shipped (PR #1507) and corpus lesson 2026-09-03-19-004 already holds. No duplicate
  corpus entry; dedup discipline applied.
- **Inbox plan-03-review-currency-006 discarded** (2026-09-17 drain): the argparse
  never-invent-verbs candidate duplicates the most-lessoned class in the corpus
  (2026-09-03-19-004, 2026-09-04-17-008, 2026-09-11-19-001, 2026-09-13-12-005). No
  duplicate corpus entry; dedup discipline applied.
- **Inbox plan-01-head-rearm-003 discarded** (2026-09-17 drain): the retrospective's
  six proposals overlap invocation-surfaces-004's P0–P5 and are tracked in the
  structural process-fix Watch above; epic-process-specific content, not global-corpus
  material. The standing R3 self-finding is preserved in the archived message.
- **PLAN-07 staged from inbox session-identity findings** (2026-09-17 drain):
  plan-03-review-currency-003 escalated (abstraction bug with remedy direction),
  git-branch-mechanics-002 folded as recurrence of the same defect. Spec
  `plans/PLAN-07-session-identity.md`, row appended via `queue --add-row`, WS-04.
- **Corpus move + purge executed** (2026-09-17, operator direction): 68 epic-relevant
  lessons copied into `lessons/` (new directory — layout variance recorded here;
  each file carries its source id, corpus status, and epic coverage note) with
  `lessons/index.md` as the coverage map. 12 removed as completely_covered by
  shipped PRs #1505/#1507/#1509-adjacent/#1510 (tombstoned with clause+input each);
  3 removed as redundant (09-02-08-001→08-25-09-012, 09-14-12-001→09-12-08-001,
  09-04-17-010→09-03-18-001; representatives retained open). Open/staged lessons
  copied with corpus originals RETAINED (no honest removal verdict exists pre-ship).
  Corpus count 186→171 reconciles exactly. Two operator cleanups owed: delete stray
  `lessons/2026-09-08-25-09-012.md` (typo duplicate of `lessons/2026-08-25-09-012.md`;
  no delete tool in the orchestrator envelope), and note the `finalize-maternity/`
  typo directory was created and immediately removed with no residue.
- **PLAN-07 drain dispositions** (2026-09-18): -002/-003/-004/-008 promoted to
  2026-09-18-20-001..004; -005 discarded (never-invent-verbs family, corpus-held);
  -006 folded into epic lesson 19-003 (router-placement recurrence + validator
  proposal; surface unchanged); -007 discarded (absent-vs-zero discipline
  corpus-held).
- **STANDING ROUTING RULE (2026-09-17, operator direction):** rule-following findings
  — improper process adherence in general, especially on opencode — drain to the
  `process-compliance` epic's inbox, not absorbed here. Relevance test: proposes,
  evidences, or corroborates a structural guard/contract/registry/persona-rule/
  target-abstraction repair. Filed as `sender-type=orchestrator`,
  `sender-id=finalize-machinery`, each naming its source message. Agreement filed as
  `process-compliance/inbox/finalize-machinery-001.md`; backfill already gathered in
  that epic's Inherited Material A–H, so nothing prior is re-filed.
- **Inbox git-branch-mechanics-003 discarded** (2026-09-17 drain): the
  review_completeness flag-shape candidate duplicates the corpus-held argparse family
  (2026-09-03-19-004, 2026-09-04-17-008, 2026-09-11-19-001, 2026-09-13-12-005). Not a
  structural process guard, so not forwarded under the routing rule; dedup discipline
  applied.
- **Eight candidate-lessons promoted to the corpus across two drains** (two-sided
  record for Step 5b): 2026-09-17-19-001 (move-in single-location rule, from -002),
  -002 (participation-site registry, from -004), -003 (wire helpers to production,
  from -005), -004 (step-owned dispatch bodies, from -008), -005 (loop-back dispatch
  shape, from -009), -006 (loop_back_target, from -010), -007 (producer vocabulary,
  from -011), -008 (roster skills column, from -013). All eight are cited as related
  material in the process-compliance epic's Inherited Material.

## Inherited Material — the decompose input

⛔ **This is a hand-off record, not a queue.** Nothing below is staged. Every item is carried
from `operator-ux`, where it was OBSERVED and verified at HEAD, and each names its evidence
there. Decompose turns these into workstreams and specs.

### Open Defects transferred from operator-ux

1. **A merged plan is invisible to its epic until the landing arrives, and nothing bounds the
   latency.** Observed at 5h48m on PLAN-07. `inbox list` reports what WAS filed and has no
   notion of a landing that is OWED, so an epic awaiting a slow landing is indistinguishable
   from one with no news. During the window the orchestrator would re-emit shipped work.
2. **The lessons pipeline re-files what the corpus already holds.** Two consecutive drains found
   6-of-11 and 4-of-10 candidate-lessons already present, twice including lessons filed by the
   immediately preceding plan in the same epic. One message even names its own duplicate and
   asks the orchestrator to merge the pair. The dedup burden sits entirely on the drain.
3. **`branch-sync-state` cannot reach its own `remote_absent_landed` verdict once branch-cleanup
   has removed the worktree** — the one state that answers correctly is unreachable exactly when
   it is needed, and the push re-entry contract's error default ("fail toward pushing") would
   re-push a merged-and-deleted branch.
4. **The pre-push quality gate certifies a tree that review never sees.** `pre-push-quality-gate`
   is `order: 5`, `finalize-step-simplify` is `order: 8`; the gate certified `43ed295b` and
   simplify advanced HEAD to `8827a7f2`. Tracked by corpus lesson `2026-09-03-11-002`.
5. **`prune-local-and-remote-ref` aborts on an already-deleted local branch**, stranding
   `refs/remotes/origin/{branch}`, because `worktree-remove` deleted that ref first. The two
   steps are individually correct and jointly wrong.

### Corpus lessons with no owning plan

The retirement targets. Ordered by observed recurrence:

| Lesson | Subject | Status |
|--------|---------|--------|
| `2026-09-03-19-005` | HEAD move inside finalize re-arms every head-bound step | **Highest value** — the cost mechanism |
| `2026-09-03-19-004` | Argparse rejections do not name the offending flag or the sibling verb | Structural remedy for the whole class |
| `2026-09-03-19-003` | `ci pr prepare-body` router-vs-verb `--plan-id` split | 2 verbs, hit by the orchestrator itself |
| `2026-08-25-09-014` | `--measured-diff-size` is the one flag the empty-is-safe guarantee misses | 2 observed instances |
| `2026-09-03-11-004` | `manage-status read` declares only `--plan-id` / `--store` | 3 observations, 2 from independent envelopes |
| `2026-09-03-11-005` | `manage-plan-documents` has no `read` verb | 2 observations |
| `2026-09-03-10-001` | `pre-commit-verify-freshness` returns two verdicts for one tree | 2 observations |
| `2026-09-03-16-005` | `phase_handshake` drifts on `pending_findings_blocking_count` | 2 observations, **bidirectional** — see the amendment |
| `2026-09-03-19-006` | `phase_handshake verify` exits non-zero with empty stderr | Blocks triage of the above |
| `2026-09-03-11-002` | Self-review at order 7 runs before simplify at order 9 | Related to defect 4 |
| `2026-09-03-11-007` | Finalize cost 3.7× execute on a three-file docs change | Symptom of `19-005` |
| `2026-09-03-19-007` | Retrospective registers 17 fragments in 17 calls | Cost, low complexity |

### Transferred from `unreviewed-merge-gate-holes` (PR #1409) — not an orchestrated plan

⛔ **This plan belongs to no epic.** It was run directly by the operator, so it has no ledger row
anywhere, no landing record was owed, and its lessons correctly went to the global store rather
than to any inbox. It is recorded here because its entire surface is this epic's — the
merge gate, the review-currency guard, and the merge mutex — and because it closed one hole while
its own gates found two more. Verified at HEAD: PR merged as squash commit `66320e70d`,
`review_decision: none` (`ci pr view --pr-number 1409`), 19 files realized, +506/−88
(`git show --stat 66320e70d`).

**Two gate holes are open, with remedies already specified in the corpus:**

6. **The review-currency guard orders timestamps instead of comparing the SHA the bot says it
   reviewed**, so a force-push lets a stale review credit as current. Corpus lesson
   `2026-09-04-17-016` (`plan-marshall:workflow-integration-github`, active). ⚠️ #1409 changed
   `test/plan-marshall/workflow-integration-github/test_github_pr.py` but **no production file
   under `workflow-integration-github/scripts/`** — the hole is untouched, as the run itself said.
7. **`head_sha_verified` is unreachable on the `issue_comment` publish path**, so a bot that
   reviewed the merge candidate reads as declined. Corpus lesson `2026-09-05-14-001`
   (`plan-marshall:workflow-integration-github`, active). ⛔ On this very PR the mechanism, acting
   on the false flag, advised **weakening the gate** for two bots that had in fact reviewed. The
   merge went through on the operator reading the bots' own SHA claims and overriding the
   mechanism — which means the PR that made CodeRabbit subject to the currency test could not
   itself be cleared by that test.

**⛔ A new interaction, OBSERVED at HEAD and not present when the inherited set was written.**
`#1407` (`bf1b7ed67`) moved `coderabbit` from `optional_bots` into `required_bots` — verified by
diff of `.plan/marshal.json`, so deliverable 2 of #1409 really was delivered upstream and its
DROPPED verdict is sound. But at HEAD the same step block still reads
`review_rate_window_await: false`. CodeRabbit's refusals are the **awaitable** kind (measured on
`operator-ux` PLAN-02, where CodeRabbit refused on quota and nothing waited). So the epic now has
a **required** bot whose most common failure is a refusal the gate is configured never to wait
out. The pressure that creates is to move CodeRabbit back to `optional_bots` to clear a blocked
merge — which is the wrong remedy; turning the await on is the right one. A plan touching the
required-bot set MUST decide this pair together.

### New corpus lessons from that run — all four confirmed to name the plan

| Lesson | Subject | Note |
|--------|---------|------|
| `2026-09-05-16-004` | Merge mutex survived a session boundary 18 min past a 3600 s budget with a waiter queued | Body names `unreviewed-merge-gate-holes` and quotes `decision.log`. `merge_hold_budget_seconds` is a **declared** budget with no reclaim path: only the holder can release, so a dead holder releases nothing. `manage-locks` already carries plan liveness; nothing consults it against the budget |
| `2026-09-05-16-003` | `mark-step-done` accepts a `--head-at-completion` resolving to no commit, persisting a fabricated anchor | The operator's self-reported fabricated SHA, caught by a fail-closed refusal — the *acceptance* is the defect |
| `2026-09-05-16-002` | A down daemon silently removes cross-plan build serialization, so concurrent suites exhaust memory and the harness kills them | ⭐ Explains the `marshalld unreachable` anomaly recorded in `operator-ux` `landings/PLAN-02.md`, which noted the degradation but not this consequence |
| `2026-09-05-16-001` | `reduced_transcript` is truncated and reordered by the consumer TOON round-trip while its counts still describe the intact text | Pairs with `2026-09-04-14-002` (chat-signal starvation) — the retrospective's input path is lossy at two independent points |

### Transferred from `operator-ux` PLAN-03 (`domain-post-plan-narrow`, PR #1422)

An orchestrated plan this time, drained through the inbox — so unlike the #1409 transfer above,
these arrived by the sanctioned channel.

8. ⛔ **The orchestration-context bypass RECURRED, and the second instance carries its own
   diagnosis.** Defect 2's sibling: on PLAN-02 the context was resolved late; on PLAN-03 the
   dispatcher forwarded `orchestrated=false` / `epic=""` to `plan-marshall:plan-retrospective`
   **without ever running the Step 4b.a0 resolution**. The plan's `request.md` carried
   `source_id: …/operator-ux/plans/PLAN-03-domain-post-plan-narrow.md` and the canonical seam
   answers correctly (`inbox detect --source-id …` → `orchestrated: true, epic: operator-ux`).
   `plan-retrospective`'s Input Contract forbids it from recomputing, so it correctly honoured a
   wrong `false`. ⭐ **Corpus lesson `2026-09-06-07-002` names the seam and the remedy**, so this
   is now a specified fix rather than a wanted one. ⭐ `lessons-capture` re-ran with corrected
   values in the same run, so one run demonstrates both the broken and the working path — the
   cheapest possible reproduction.
9. **A landing narrative counts candidate lessons EMITTED and reports them as corpus entries
   CREATED.** Two measured instances in consecutive plans: PLAN-02 claimed 14 (12 carried the
   date, 7 attributable); PLAN-03 claimed nine went to the global store while the corpus grew
   **113 → 116** and exactly three carry a `2026-09-06` id. The difference is the dedup rate, and
   `finalize-step-lessons-housekeeping` already computes it — it returns an `rm / promo / adapt /
   keep` tally. Remedy shape: report the post-housekeeping count, or report both and label them.
   Until then no landing's lesson count may enter a ledger un-remeasured.
10. **⚠ THIRD recorded site of the misplaced/undeclared `--plan-id` argparse class** —
    `plan-marshall:workflow-integration-github:github_pr` rejected `--plan-id` (exit 2). Folded
    here as a recurrence on the existing cluster (`2026-09-03-19-003`, `2026-09-03-19-004`,
    `2026-09-04-17-008`) rather than filed as a fourth corpus lesson, which is exactly what
    Open Defect 2 above exists to prevent. Three sites now: `ci pr prepare-body`,
    `review_completeness --measured-diff-size`, and `github_pr --plan-id`.
11. **`automatic-review/SKILL.md` documents `--measured-diff-size "{value}"` as safe-when-empty
    although the flag takes a required argument** — two agents hit the rejection independently in
    one run. This is corpus lesson `2026-08-25-09-014` (already in the table below) recurring, and
    the recurrence is what promotes it from "2 observed instances" to a documented-vs-actual
    contract mismatch with a named doc site.
12. **Trigger-B selects ONE bot — the newest bot-authored finding's kind — so it structurally
    cannot reach a DIFFERENT bot that is the stale one**, while the prose names the trigger as
    that bot's remedy. Corpus lesson `2026-09-06-07-003`.

| New lesson | Subject | Note |
|------------|---------|------|
| `2026-09-06-08-001` | Authoring a fix for a defect class does not immunize the authoring against that class | Promoted from the inbox at the PLAN-03 drain. Nine instances of the plan's own subject class in its own output; self-review caught 3 of 9. Pairs with `2026-09-02-14-002` (a round is clean only on the proposition it asked) by naming one proposition derivable from the plan's own subject |
| `2026-09-06-08-002` | Publish the population a signal-gate count was computed over | `signal_script_failure_clusters_count` reported 1 against two distinct failing notations. The count is a GATE — at the boundary an undercount silently converts a signal into a skip, indistinguishable from a clean run |
| `2026-09-06-08-003` | Compare a symmetric pair written in the same edit against each other | The symmetric-pair detector fires on structural divergence, not on guard STRENGTH (`.strip()` vs bare truthiness in two guards from one commit). No completeness sweep reaches it |
| `2026-09-06-07-001` | Classify `review_body` actionable content by residual text, not the status line | Reviewer yield undercounted 17 as 11 (35%) because every CodeRabbit body opens with `Actionable comments posted: N` and was bucketed `meta` |

⚠ **The cost finding cuts against its own obvious remedy, and the epic should not act on the
headline.** PLAN-03 ran 3× the calibrated ceiling (7.1M tokens against a 2.5M anchor) with
6-finalize outspending 5-execute 3.74×. The retrospective's judgement, recorded because it is the
part that would be lost: the re-firing was **productive** — five review rounds carrying real
findings, zero error-attributed tokens. **This does not support cutting the round count.** It is a
counter-example to the cost theme in § Vision, not another instance of it.

### Already fixed — do NOT re-stage

- ✅ **Sourcery false participation** (`2026-08-25-09-012`, `2026-09-02-08-001`). Fixed by
  PLAN-10 of `operator-ux` as an operator-approved scope deviation and demonstrated working in
  the same run. ⛔ Those two lessons are retirement CANDIDATES, not retirements: one
  demonstration inside the fixing run is not independent confirmation. Retire them after a
  later run classifies sourcery into `refused_bots` unaided.

## Open Defects

1. ~~Incomplete landing-facts on invocation-surfaces-003~~ RETIRED 2026-09-17: the
   required deliverable facts arrived via the complete plan-03 landing (-007,
   deliverables 2/2). Nothing further owed.
2. **Narrative-only landing on plan-06-anchors-and-mutex-001** (2026-09-18): no
   `landing-facts` block, so `landing-check` reports `complete: false` (all 9 keys
   missing). Reconciled as far as the narrative goes (PR #1525 merged at 1605831c,
   verified); a manual paste from that plan may still surface machine facts (tokens,
   wall time, steps). Retire when they arrive or the operator confirms nothing is owed.

## Watches

- **cuioss-review-bot demoted to optional** (2026-09-18, PLAN-05 landing residue,
  operator-ordered after 5 unanswered re-review triggers; required_bots=coderabbit).
  Silence pattern preserved in the archived plan; process-compliance may want it.
  Re-promote when the bot answers again.
- **PLAN-07 finalize blocked on missing SessionStart hook** (2026-09-18, absorbed
  from plan-07-session-identity-001): abort at the session gate on a
  transcript-capable target is the designed outcome (broken hook, not a defect).
  Work preserved — 3 tasks done, 3 commits in the plan worktree, nothing pushed.
  Operator remedy: marshall-steward hook install, then re-run finalize unchanged.
  Pre-existing main-checkout stash@{0} (plan07-session-identity-wip-on-main,
  unowned) left for operator disposition. ~~Retire when finalize re-runs green.~~
  RETIRED 2026-09-18: hook installed, finalize re-ran, PR #1530 merged as ba0317c.

- **process-compliance decomposed onto overlapping surfaces** (2026-09-17,
  observed in cross-check): that epic's staged PLAN-01-phase-gates touches
  manage-status.py (our shipped PLAN-02's surface — terminal, no conflict),
  PLAN-03-compliant-paths touches plan-orchestrator orchestrator.py (our staged
  PLAN-05), PLAN-02-worktree-discipline touches phase_handshake.py (our staged
  PLAN-06), PLAN-07-opencode-repairs touches opencode_runtime.py (our staged
  PLAN-07). Staged-vs-staged is adjacency, not collision — but if both epics
  launch the same pair concurrently, the gate cannot see across the ledger.
  Coordinate launch timing with the process-compliance session; re-check at each
  landing on either side.

- **The inherited set is a floor, not a census.** It is what two epics happened to observe
  while doing unrelated work. No systematic sweep of the finalize lane has been done, so
  decompose should expect to find more and should not treat the twelve lessons above as the
  full population.
- **PLAN-02 mid-run worktree failure, remediated** (2026-09-16, absorbed from inbox
  invocation-surfaces-001): implementation began on the main checkout with the worktree
  unmaterialized; remediated via snapshot relocation + Step 2.5 materialization before
  any commit. Landed clean as PR #1507. Kept as process evidence for launch discipline.
- ~~PLAN-01 implemented outside the lifecycle; PR #1505 open~~ RETIRED 2026-09-17:
  PR #1505 merged as 66733bef; row shipped with pr/landing stamped (no lifecycle plan
  id exists — direct implementation, plan_marshall_plan_id deliberately unstamped).
  The main-checkout process failure stands as filed in archived -001 as evidence.
- **PLAN-03 move-in duplication report, refuted** (2026-09-17, absorbed from inbox
  plan-03-review-currency-001): single location verified (worktree holds the tree,
  main holds no copy); the doubled `.plan/local` segments are per-tree nesting by
  design, not a copy. Kept so the next identical report folds here instead of
  re-verifying.
- ~~PLAN-04 worktree residue, mid-flight~~ RETIRED 2026-09-17: clean move-back
  confirmed at landing (branch cleaned, plan archived to
  .plan/local/archived-plans/2026-09-17-git-branch-mechanics, main clean).
  The corrective path stated in -001 stands as launch discipline evidence.
- **Structural process-fix backlog** (2026-09-17, absorbed from inbox
  invocation-surfaces-004): prevention-failed-everywhere vs detection-worked
  analysis with prioritized proposals P0 (transition artifact gates) through P5
  (structured deviation-audit form), plus the do-not-change list (fail-closed
  guards, loop-back, metrics gap flags) and the cost asymmetry. Future epic-planning
  material; overlapping proposals from plan-01-head-rearm-003 fold here.
