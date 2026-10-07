# Landing Analysis: PLAN-03 — Domain post-plan narrowing

epic: operator-ux
workstream: WS-01-domain-resolution
pr: #1422 — https://github.com/cuioss/plan-marshall/pull/1422

> Landing record for one shipped plan. Lives at `landings/PLAN-03.md`. Written by the
> `analyze` verb after verifying claims against ground truth (actual code, artifacts,
> PR state) — a pasted claim is a lead, never a fact. See
> `persona-plan-orchestrator/standards/orchestration-model.md` for the analysis and
> reconciliation contract.

Input mode: inbox scan (5 messages from sender `domain-post-plan-narrow`), corroborated against
the operator's paste, git, and the read-side CI abstraction. `inbox landing-check` on
`domain-post-plan-narrow-005.md` returned `complete: true`, `missing_keys: []`. Where a claim and
the measured ground truth disagree, the measurement is recorded and the claim is labelled.

## Deliverable Fidelity vs Spec

⛔ The spec declared **five** deliverables; the landing reports **2/2**. The two are a re-cut of
the same work, not a reduction — but the re-cut hides one genuine shortfall, recorded below.

| Deliverable (spec) | Verdict | Evidence |
|--------------------|---------|----------|
| 1. Narrowing re-resolution once the file set is known; **outline must choose between shape (i) end-of-outline and shape (ii) narrow-at-init** | shipped-as-specified, fork resolved | Landing D2. Outline adopted **(i) only** and declined (ii) outright — *"shape (ii) narrows at the point of maximum ignorance, which is the same information deficit that causes the over-provisioning"*. No successor plan implied; the scope-bloat split guard was never triggered |
| 2. A **safety-bounded** narrowing rule — drop only when no resolved task depends on it and the glob/`always_on` legs do not claim it | shipped-as-specified | Landing D1. `manage-config/scripts/_cmd_domain_narrow.py` (347 new lines) + `manage-config.py` wiring; `test_cmd_domain_narrow.py` (686 lines) |
| 3. Recorded provenance on the `references.domains` write | shipped-as-specified | Written on **both** exits, so its presence proves the pass ran — a stronger property than the spec asked for |
| 4. **The system reports the narrowing to the user in one line rather than silently** | ⛔ **PARTIAL — recorded, not surfaced** | See the shortfall below |
| 5. Tests: over-provisioned set narrows; `always_on` survives; a task-claimed domain survives; empty/unreadable footprint narrows nothing | shipped-as-specified | `test_cmd_domain_narrow.py` + `test_domain_narrow_reason_codes_documented.py` (163 lines), plus `test_manage_references.py` amendments |

### ⛔ Deliverable 4 is the one that did not land, and this epic is the reason it matters

Spec D4 asked for the narrowing to be reported **to the user**, on the argument that *"a domain
set changing under a plan is exactly the kind of thing that must be visible"*. At HEAD the shipped
code states three times, in its own words, that no user-facing sink exists:

- `phase-3-outline/SKILL.md:656` — *"⛔ **The decision log is the report's only CONSUMED sink
  today.** `domain_narrow_report` is a declared return field with no reader … Stating that the
  orchestrator surfaces it would be a promise this repository does not keep."*
- `:718` — *"It has no reader today … Wiring a consumer there is owed follow-up, not present
  behaviour."*
- `:738` — *"`display_detail` is NOT a sink for the domain-narrow report."*

Corroborated independently: an inventory-wide sweep for `domain_narrow_report` returns **4 hits
across 2 files, both producers** (`phase-3-outline/SKILL.md`, `workflow/light-lane.md`).
`plan-marshall/workflow/planning-outline.md` — the consumer that would surface it — does not
enumerate the field.

⭐ **The plan handled this exactly right and should be read as a success on process:** three of its
own self-review findings (`cd0783`, `399e28`, `7f14d3`) were prose claiming this very sink
existed, and the plan **removed the false claim rather than pretending the sink was there**. That
is the plan's own subject rule applied to itself.

⚠ But the ledger must not inherit the plan's re-cut as if D4 shipped. The narrowing is recorded
in the **decision log**, which is a developer artifact, not an operator surface. In an epic whose
entire subject is operator UX, "the domain set changed silently and only the decision log knows"
is the failure D4 was written to prevent. **Follow-up owed: wire a consumer in
`plan-marshall/workflow/planning-outline.md`.** That file is declared by no spec in this epic.

## Metrics and Anomalies

- **Tokens**: 7,103,472 — against a 2.5M calibrated error anchor, so **~3× over**. Second most
  expensive plan in the epic after PLAN-02's 12.0M.
- **Duration**: `total_wall_seconds: 68668` = 19 h 04 m wall; the operator reports 4 h 13 m worked.
- **Finalize outspent execute 3.74×.** ⚠ The retrospective's judgement, recorded here because it
  cuts against the obvious remedy: the re-firing was **productive** — five review rounds carrying
  real findings, zero error-attributed tokens — so this does **not** support cutting the round
  count. Recurrence of corpus lesson `2026-09-03-11-007`.
- **Steps**: 23/23 `done`, none skipped, none failed — parsed by last-colon split, which the six
  `project:` and `plan-marshall:` namespaced ids require.
- **Merge**: squash, merge commit `80f0b5a79`, `review_decision: none`, verified via
  `ci pr view --pr-number 1422`.
- **Realized surface**: 15 files, +1623/−36 (`git show --stat 80f0b5a79`). `uv.lock` is among them
  — the standalone `c3d69f52a` uv.lock refresh that sat on main is no longer in the first-parent
  history, so this plan's rebase absorbed it.
- ⚠ **CONTRADICTED — "nine lessons went to the global store" is not what the corpus holds.** The
  landing message and the paste both state nine. Measured: the corpus went from **113 to 116**
  entries, and exactly **three** carry a `2026-09-06` id (`07-001` reviewer-yield, `07-002` the
  self-reported orchestration error, `07-003` trigger-B single-bot selection). Six of the nine
  candidates were folded or deduped by `finalize-step-lessons-housekeeping`, which ran `done`.
  ⛔ **This is the SECOND consecutive landing to make this exact overcount** — PLAN-02 claimed 14
  where 12 existed and 7 were attributable. The narrative counts *candidates emitted*; the corpus
  holds *entries created after dedup*. Recorded as a new Open Defect, not folded, because two
  independent instances make it a reporting defect rather than one plan's slip.
  ⛔ **What is NOT in doubt, and is the part that matters:** those lessons went to the GLOBAL
  store rather than this inbox. The count is a lead; the bypass is the fact.

## Routing and Merge Behavior

- ⛔ **The orchestration-context bypass recurred, and this instance is diagnostically better than
  the first.** The finalize dispatcher forwarded `orchestrated=false` / `epic=""` to
  `plan-marshall:plan-retrospective` **without ever running the Step 4b.a0 resolution**, although
  the plan's `request.md` carries
  `source_id: .plan/orchestrator/operator-ux/plans/PLAN-03-domain-post-plan-narrow.md` and
  the canonical seam answers correctly — `inbox detect --source-id …` → `orchestrated: true,
  epic: operator-ux`. `plan-retrospective`'s Input Contract forbids it from recomputing the
  forwarded values, so it correctly honoured a wrong `false`. `lessons-capture` ran afterwards
  with corrected values, which is why messages 001–004 reached this inbox and the retrospective's
  did not. ⭐ The run **caught its own error and filed `2026-09-06-07-002`**, which names the
  detection seam and the remedy. That closes the diagnosis this epic's existing Open Defect could
  not supply.
- **Review: a required reviewer contributed nothing, and the quorum still passed.**
  `cuioss-review-bot` participated at every head asked and reported "no major issues detected"
  each time, filing **zero** findings. CodeRabbit filed **12** (all triaged FIX) and the plan's own
  self-review found **7** more. `sourcery` was quota-refused from first contact and never reviewed.
  ⭐ CodeRabbit was **required** for this run — the first plan in the epic to land under the
  `required_bots` change from #1407 — completed five rounds, ended at zero findings against the
  final state, and was **never moved to `optional_bots`**; one ten-cycle wait was needed.
  ⛔ The quorum proves participation, not review quality: on this PR the required bot found nothing
  and the optional-by-history bot found twelve.
- **⚠ The reviewer-yield instrument undercounts by 35% on this PR.** All five CodeRabbit
  `review_body` records were bucketed `meta` because each opens with an
  `Actionable comments posted: N` line; four carried real findings behind it. True actionable yield
  17, measured 11. `review-retrospective` recorded the caveat rather than silently recomputing.
  Corpus lesson `2026-09-06-07-001`.
- **No surface collision occurred** — PLAN-03 ran alone with slot 2 deliberately unfilled. That is
  the reason, not disjointness holding.

## Reconciliation Actions

- [x] row `status` → `shipped` — `orchestrator queue --transition PLAN-03 --status shipped`
- [x] row `pr` stamped `#1422`; row `landing` stamped `landings/PLAN-03.md`; row
      `plan_marshall_plan_id` stamped `domain-post-plan-narrow`
- [x] 5 inbox messages drained and archived (4 candidate-lesson + 1 landing), each with a logged
      disposition
- [x] corpus lessons promoted: `2026-09-06-08-001`, `-08-002`, `-08-003`; message 003 discarded as
      a tracked recurrence
- [x] Open Defect opened — the candidate-vs-created lesson-count overcount (second instance)
- [x] Open Defect opened — deliverable 4's unwired user-facing sink
- [x] Open Defect folded — the orchestration-context bypass, now with its diagnosis and remedy
- [x] Watch updated — declared-surface honesty, third data point, sharpened
- [x] epic.md queue reconciled from status.json; both generated blocks regenerated

## Follow-Ups

- **Under-declaration measured at 67%, and the shape is worse than the ratio.** Declared 8 entries;
  5 were touched. Realized 15 files, of which 10 are undeclared: `_cmd_domain_narrow.py`,
  `manage-config.py`, `api-reference.md`, `data-model.md`, `workflow-overview.md`,
  `light-lane.md`, two new `manage-config` test modules, `test_manage_references.py`, `uv.lock`.
  ⛔ **The plan's PRIMARY artifact was undeclared while three declared files were never touched.**
  The declaration named `_cmd_domain_detect.py` and its test; the plan wrote
  `_cmd_domain_narrow.py` (347 lines) and two new test modules. `phase-1-init/SKILL.md` was
  declared and never opened. So this is not merely under-coverage — the declaration **named the
  wrong file for the main deliverable**. The ratio (71% → 78% → 67%) understates that.
- ⚠ **PLAN-09's re-grounding debt grows for the third time.** PLAN-03 modified
  `manage-config/standards/data-model.md`, declared by **PLAN-09** and undeclared by PLAN-03 —
  after PLAN-02 did the same to that file and to `marshal-json-reference.md`. Re-ground before
  PLAN-09 is emitted.
- ⚠ **PLAN-04, PLAN-06 and PLAN-09 all declare `test/plan-marshall/manage-config/`**, into which
  PLAN-03 added two new modules. `test/plan-marshall/manage-references/` was also touched and is
  declared by `test-quality` PLAN-030 (landed).
- **Two adjacent defects in machinery this plan does not own**, recorded not fixed:
  `automatic-review/SKILL.md` documents `--measured-diff-size "{value}"` as safe-when-empty
  although the flag takes a required argument (two agents hit the rejection independently — this
  is corpus lesson `2026-08-25-09-014` recurring, already finalize-machinery decompose input); and
  trigger-B selects ONE bot by newest bot-authored finding, so it structurally cannot reach a
  DIFFERENT stale bot while the prose names it as that bot's remedy (`2026-09-06-07-003`).
- **`github_pr.py` rejected `--plan-id`** — the third recorded site of the misplaced-`--plan-id`
  argparse class. Routed to `finalize-machinery`, which already owns `2026-09-03-19-003` and
  `-19-004`; deliberately NOT filed as a fourth corpus lesson.
