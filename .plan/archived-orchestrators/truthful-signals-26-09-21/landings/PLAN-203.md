# Landing Analysis: PLAN-203 — The inbox and the resume anchor cannot distinguish consumed from missing

epic: truthful-signals
workstream: WS-01
pr: 1064 — merged as `e82b466ee`

## Ground-truth corroboration

The landing message (`plan-203-inbox-consumed-vs-missing-001.md`) is a lead, not a fact. Checked:

- ✅ **PR #1064 merged** — `git log origin/main` shows `e82b466ee fix(marshall-orchestrator): distinguish
  consumed from missing in inbox reads and derive resume-summary counts (#1064)`. Independent of the
  message's own claim.
- ✅ **branch-cleanup completed** — plan `status.json` `phase_steps` records *"PR #1064 merged via queue,
  main pulled, worktree removed, branch gone"*, and `git worktree list` confirms no
  `plan-203-*` worktree survives.
- ✅ **Reviewer claim** — `automatic-review` recorded `0 comment(s)` at head `aa76c57a`, while
  `finalize-step-review-retrospective` recorded *"2 reviewers compared, 2 actionable comments"*. The
  message's "1 actionable review comment remediated in-run" is consistent with the retrospective, not
  with the `automatic-review` step. ⚠ Not reconciled here — recorded as an open question below.

## Deliverable Fidelity

D1–D5 as claimed (archive-resolving `inbox validate` with a distinct `location: archived`; `inbox list`
reporting `inbox_dir` + an `inbox_state` discriminator; `resume-summary` deriving inbox counts at read
time; D4 a mutates-nothing gate; tests verified red pre-fix). ⚠ Per-deliverable fidelity is **asserted by
the plan, not independently verified here** — recorded as verification debt, consistent with how PLAN-103
was handled.

## ⭐ The fix lands exactly on the defect that bit THIS orchestrator, in this session

D3 — *"queued/archived counts are rendered from the inbox at read time, separately from the operator's
narrative anchor, so a stale sentence can no longer outrank a live count"* — is the direct remedy for the
failure this session committed twice:

1. The prior anchor asserted `INBOX: 0 queued` while `inbox list` returned **2**.
2. This orchestrator then reported `0 queued` after its own drain and asserted `origin/main` unchanged
   **for the rest of the session** — by which time 11 messages had queued and two PRs had merged.

⛔ **And the fix cannot help this session**, because the skill docs loaded here come from plugin cache
`0.1.1240` while the executor resolves `0.1.1269`. A fix that shipped 6 minutes ago is not in the prose
this session is following. That is the doc-vs-script version-skew axis folded into **PLAN-TRUTH-008** —
now with a second, concrete instance.

## Residue accepted from the message

1. ⛔ **D4 REFUTED the request's own hypothesis** — "the inbox count is the only drifted hand-written
   count" is false. Population swept across 7 files: **13 derivable assertion classes, 8 genuinely
   narrative**, with **at least three derivable surfaces beyond the inbox still unprotected** — one of
   them the `epic.md` **Ordered Queue table**, which is *strictly larger* than the count this plan fixed.
   ⭐ This is the population-derived-detector rule paying out: the plan enumerated instead of fixing the
   named site, and found the named site was the small half.
2. ⭐ **The epic's theme reproduced inside the plan's own fix** — CodeRabbit caught `inbox_state` being
   observed AFTER the enumeration it describes, so the payload could report `count: 3` alongside
   `inbox_state: missing`: "could not look" asserted about a scan that did look. Fixed in-run.
   **Vacuous/incoherent-signal archetype, introduced by a fix for that archetype — the family is now at
   n=6.**
3. A Q-Gate `keyword_drift` false positive and a decision-log fragmentation artifact ride as
   candidate-lessons.

## Open questions this landing does NOT settle

- ⚠ **`archive-plan` has not happened.** At 10:19:09Z the plan directory is still live at
  `.plan/local/plans/plan-203-inbox-consumed-vs-missing/`, `current_phase` reads `6-finalize` /
  `in_progress`, and there is no `2026-07-30-plan-203-*` entry under `archived-plans/`. Its last step
  update was **10:12:49Z, ~6 minutes earlier**, so this is **NOT yet declared a defect** — finalize may
  still be running. ⇒ **WATCH: re-check the store. If the directory is still live and unarchived on the
  next resume, this is a confirmed instance of API-Sheriff round-4 item 2** (shipped plan left live in
  the store, silently), and it pollutes the exact surface start-detection reads. For contrast, #1063's
  plan DID archive (`2026-07-30-audit-report-path-ignores-plan-dir`), so the step is not globally broken.
- ⚠ **`2-refine` is `in_progress` while 3/4/5 are `done` and 6 is running.** A phase left open that later
  phases overtook — a second honest-state gap in the same `status.json`.
- ⚠ **Reviewer-count divergence** between `automatic-review` (`0 comments`) and the review-retrospective
  (`2 actionable`). Per the standing rule, only `ci pr comments --pr-number 1064` is evidence. Not run
  here.

## ✅ Finalize COMPLETED — the open questions above are now settled

Operator report + verification at 22/22 finalize steps:

- ✅ **`archive-plan` DID complete** → `.plan/local/archived-plans/2026-07-30-plan-203-inbox-consumed-vs-missing`,
  and `.plan/local/plans/` is now **empty**. ⇒ **The round-4 item 2 watch closes as NOT an instance.**
  The 6-minute-old step update was indeed mid-flight, and declining to declare a defect on that evidence
  was correct. ⭐ Recorded because the restraint is the reusable part: **a 6-minute-stale in-progress
  record is not evidence of a stalled step.**
- ✅ `record-metrics`: 3 h 37 m worked / **3.2 M tokens**, 6 phases.
- ⭐ **#1064's own D2 fix is now visible in the executor's output** — `inbox list` returns `inbox_dir` and
  `inbox_state: present`, fields absent from the same call earlier in this session. The script layer
  advanced mid-session; the doc layer this session read did not.

## ⚖ ADJUDICATION — the self-review dispute splits three ways

The operator asked for confirmation. Neither side is wholly right, and the record itself is the finding.

- ✅ **The operator's correction is CONFIRMED on the causal claim.** The persisted step reads
  `display_detail: "self-review clean: 26 candidates, no check matched"` — a **non-empty 26-candidate
  set**, which cannot be the output of the run that refused for *missing* candidates. The recorded
  verdict is the re-dispatch. So *"reported clean over checks that could not run"* is **wrong as
  stated**.
- ✅ **Corroborating logic, independent of the record:** the same retrospective says the defect
  self-review missed (the self-contradicting `inbox_state` payload) was caught by CodeRabbit instead. A
  step that never ran cannot *miss* a specific check class — the miss presupposes a run.
- ✅ **But the retrospective's underlying observation STANDS, and it named it itself:** *"Nothing in
  `status.metadata.phase_steps` preserves the error."* It saw an ERROR at 07:27:40 and a later
  `outcome=done`, and inferred causation from log adjacency because the record offered nothing better.
- ⛔ **THE REAL DEFECT IS THE ONE NEITHER SIDE NAMED: the step record has no ATTEMPT IDENTITY.** A
  retried dispatch collapses into one `phase_steps` entry, so a reader cannot distinguish *"refused,
  then succeeded on re-dispatch"* from *"refused, and was reported green anyway."* The retrospective
  took the pessimistic reading; the operator knows the optimistic one is true; **the persisted record
  cannot adjudicate between them.** That is this epic's theme one level up — filed as an Open Defect.

⚠ **Per-instance split, not a whole-finding verdict.** The retrospective bundled TWO instances into one
*"two finalize gates rendered a confident green"* finding. Instance 1 (self-review) is **refuted as
stated**; instance 2 (`review_completeness` argparse rejection) the operator **confirms as a genuine
defect**. ⇒ A bundled finding must be dispositioned **per instance** — refuting one half does not retire
the other, and accepting one half does not validate the other.

## ⛔ Residue MUCH larger than the fix — five further surfaces, not three

The quality-verification report records: *"THEME RECURRENCE: the plan's own defect archetype — a zero
that cannot state which kind of zero it is — was found live in **five further surfaces** of the same
finalize pipeline (self-review, review barrier, retrospective footprint check, review-retrospective
reviewer accounting, manifest prune predicate). PLAN-203 fixed one instance of a pipeline-wide pattern."*

Combined with D4's enumeration (13 derivable assertion classes vs 8 narrative across 7 files; three
unprotected surfaces — the `epic.md` Ordered Queue with 4 derivable columns and **no BEGIN/END GENERATED
guard**, the Decisions list, and the anchor's PR/CI clause), the shipped fix is **one instance of a
pattern with at least eight known live siblings.** ⇒ Filed as an Open Defect; this is the population,
and it is what the next plan in this family must be scoped against — not the named site.

⭐ **The `running`-has-no-machine-field claim, corrected.** The report frames it as *"running has no
machine field anywhere."* ⚠ **Not quite** — this epic's `plans[]` rows carry `status: running` for
PLAN-57 and PLAN-202, so the field exists. The accurate statement is that **nothing can falsify its
value**: it is hand-set on operator confirmation and no liveness signal exists to check it against —
which is exactly API-Sheriff round-4 item 5. ⇒ Folded there rather than filed as a separate finding.

## Operator's three flagged items — dispositions

1. **Self-review** — adjudicated above. Correction accepted; attempt-identity filed as the real defect.
2. **`review_completeness` doc/script drift** — the doc's `--enabled-bots` form was rejected (argparse
   exit 2) against the live `--required-bots`/`--optional-bots` surface, ~60 s before the gate flipped
   green. ⇒ **FOLDED into PLAN-TRUTH-012** (`canonical-block-diverges-from-argparse-choices`) — its exact
   subject. ⭐ **Two subagents hit it independently**, which makes it a population signal, not an
   incident. ⚠ The green verdict is real (re-run with the correct surface), so this is a doc defect, not
   a false green — stated so the fold does not overclaim.
3. **Budget 3.2 M against a ~1.3 M threshold** — three `automatic-review` dispatches across two
   loop-backs dominate, and **one loop-back was caused by a content-identical rebase invalidating
   required-bot participation, which will recur on every plan.** ⇒ **FORWARDED to `review-apparatus`** —
   a recurrence of the Shape F mechanism their PLAN-116 split already owns. Not ours: participation
   invalidation is review apparatus.

## Reconciliation Actions

- [x] row `status` → `shipped`
- [x] `pr` = 1064
- [x] `landing` = `landings/PLAN-203.md`
- [x] `plan_marshall_plan_id` = `plan-203-inbox-consumed-vs-missing`
- [x] landing message archived
- [ ] **9 candidate-lesson messages (002–010) NOT yet dispositioned** — they need a dedicated drain pass
      with a per-item disposition each; deliberately not rushed as part of this reconciliation
- [ ] post-merge PR revisit for #1064 — owed; note the standing rule no longer binds us for PR-related
      PRs, but #1064 is a `marshall-orchestrator` plan, so it is OURS

## Parallelization Consequence

PLAN-203 held the `marshall-orchestrator` surface. Its landing **unblocks PLAN-TRUTH-002**
(inert-thinking-directives, blocked on same-bundle collision) — re-derive that verdict at emit rather
than trusting this sentence.
