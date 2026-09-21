# Epic: Operator UX — reduce interaction friction across the plan-marshall lifecycle

slug: operator-ux

> Ledger document for one epic under `.plan/orchestrator/operator-ux/`. The layout and
> authority contract live in the central standard — see
> `persona-plan-orchestrator/standards/orchestration-model.md`. `status.json` is the
> machine authority; any statement here that conflicts with it is stale prose.

## Vision

plan-marshall is powerful but expensive to *operate*: it asks the user too often, asks at the
wrong moments, asks without giving enough context to answer well, speaks its own internal
vocabulary (ledger, workstream, q-gate, disjointness) at people who never learned it, emits far
more output than a user needs to make the next decision, and does not consistently honour the
language the user is writing in. The result is a system whose correctness is high and whose
felt cost is also high.

This epic drives the operator-facing surface toward one shape: **plan-marshall decides by
default and asks rarely, and when it does ask, the question is answerable without reading the
codebase.** The concrete moves are — collapse the autonomy gates toward "proceed" and leave
`plan_without_asking` as the single deliberate human checkpoint; make skill-domain selection
automatic and deliberately over-provisioned rather than a wizard interrogation; give every
surviving `AskUserQuestion` real decision context; replace internal vocabulary with user
vocabulary at every user-facing surface; honour the user's language end to end; and cut output
volume to what the next decision needs. An experience-level preference, chosen once at
`/marshall-steward` and changeable later, is the candidate carrier for how aggressively those
defaults apply.

It is too large for one plan because it spans four independent surfaces that do not share a
footprint: config defaults (`manage-config`), the setup wizard (`marshall-steward`), the
per-phase interaction points (`phase-1`…`phase-6`, `plan-marshall` workflow docs), and the
cross-cutting authoring standards (`persona-plan-marshall-agent`, `plugin-architecture`) that
govern how every future component talks to the user. Done, at the epic level, means: a routine
plan runs start-to-finish with exactly one deliberate user checkpoint; every remaining prompt
carries the context needed to answer it; no user-facing string uses an unexplained internal
term; and the user's language is honoured throughout.

## START HERE

<!-- GENERATED BLOCK — never hand-write or hand-edit this section.
     Regenerate after every queue-touching state change via:
     python3 .plan/execute-script.py plan-marshall:plan-orchestrator:orchestrator resume-summary --slug operator-ux
     Paste the returned `summary` block verbatim between the markers (the same
     invocation also emits `ordered_queue` for the Ordered Queue section below).
     Anything a reader wants to add BY HAND goes in the annotation zone below,
     outside the markers — never inside them. -->

<!-- BEGIN GENERATED: resume-summary -->
**Resume anchor**: DRAIN DONE 2026-09-16: 14/14 PLAN-09 messages consumed (4 promoted 2026-09-16-17-001..004, 9 discarded, landing reconciled-duplicate). Queue 10/10 shipped, zero staged. Next: WS-07 decompose vs close decision.
**Phase**: orchestrating
**Inbox (derived)**: 0 queued, 96 archived
**Queue** (staged, in order):
- (empty)
- PLAN-02 (WS-01-domain-resolution) — plan=domain-glob-seeding — PR #1406 — landing=landings/PLAN-02.md — status: shipped
- PLAN-03 (WS-01-domain-resolution) — plan=domain-post-plan-narrow — PR #1422 — landing=landings/PLAN-03.md — status: shipped
- PLAN-04 (WS-02-autonomy-defaults) — plan=plan-04-autonomy-gate-defaults — PR #1437 — landing=landings/PLAN-04.md — status: shipped
- PLAN-06 (WS-04-how-plan-marshall-talks) — plan=user-language-and-vocabulary — PR #1382 — landing=landings/PLAN-06.md — status: shipped
- PLAN-07 (WS-04-how-plan-marshall-talks) — plan=output-volume-standard — PR #1387 — landing=landings/PLAN-07.md — status: shipped
- PLAN-08 (WS-05-surface-remediation) — plan=remediate-user-facing-sites — PR #1447 — landing=landings/PLAN-08.md — status: shipped
- PLAN-09 (WS-06-interaction-mode) — plan=implement-plan-09-interaction-mode — PR #1502 — landing=landings/PLAN-09.md — status: shipped
- PLAN-10 (WS-01-domain-resolution) — plan=always-on-is-not-a-resolve — PR #1391 — landing=landings/PLAN-10.md — status: shipped
- PLAN-01 (WS-01-domain-resolution) — plan=domain-over-provision — PR #1380 — landing=landings/PLAN-01.md — status: shipped
- PLAN-05 (WS-03-prompt-quality) — plan=prompt-standard-and-doctor-rule — PR #1378 — landing=landings/PLAN-05.md — status: shipped
<!-- END GENERATED: resume-summary -->

### Annotations

<!-- ANNOTATION ZONE — hand-written, and deliberately OUTSIDE the generated markers.
     A regeneration replaces only what sits BETWEEN the markers, so everything written
     here survives it. This is what makes the block above genuinely regenerable: the
     per-row notes the generator cannot produce (why a row is parked, what a running
     plan is waiting on, an operator caveat on a queue entry) have a home that a
     verbatim paste does not destroy. -->

- PLAN-10 is `shipped` (#1391, merged `87782159`). Historical note: it escalated a genuine fork
  mid-flight — `finalize-step-simplify` had reversed a decision its own outline recorded on
  purpose — and the orchestrator ruled: accept the collapse, pin the invariant with a test
  rather than restore dead code. It escalated a SECOND fork later (sourcery's unregistered
  refusal wording) and the operator chose fix-here-anyway, so it shipped 8 files against 5
  declared. **It is the first plan in this epic to report its own landing complete on arrival.**
  The reasoning is in `logs/decision.log`.
- PLAN-07 is `shipped` (#1387, merged `9fd095718`). Historical note: it was the first round in
  the epic where both slots filled. It merged while its ledger row still read `staged` and
  filed no `kind: landing` message — the ledger learned of the merge by reconciliation, not by
  report. That failure mode is the first Open Defect above.
- PLAN-06 is `shipped`. Historical note: it was `launched` and `launched` is not `running`: nothing
  observes whether a launched plan is alive, so this note records what the operator said and no
  liveness claim beyond it should be read into the queue.
- The three-round shortfall streak broke only because PLAN-07's surface (persona standards) is
  disjoint from the `manage-config` cluster. Within that cluster the bottleneck still binds:
  PLAN-02, PLAN-03 and PLAN-04 all collide with PLAN-10 on `manage-config/SKILL.md`.
- **The bottleneck cleared 2026-09-03 when PLAN-10 shipped**, after five consecutive
  under-filled rounds. What the streak actually measured: with `parallelization_scope: 2`, this
  epic supports exactly ONE legal concurrent pair across its whole staged corpus — PLAN-02 ×
  PLAN-08, and that one is ruled out by PLAN-08's own sequencing. Nine of the ten pairings among
  the five staged plans collide. ⛔ **The scope knob has been buying nothing for five rounds and
  will keep buying nothing**: the constraint is the shared `manage-config/SKILL.md` and
  `marshall-steward/references/` surfaces, not the slot count. Worth deciding whether to drop
  the knob to `1` and stop reporting a shortfall against capacity the surfaces cannot supply.
- **⚠ Follow-up traffic is EXPECTED and this ledger is not settled.** The operator instructed
  PLAN-10's agent to revisit the CodeRabbit reviews and act on them, so further messages,
  and possibly a follow-up PR, are anticipated for work already recorded as shipped. Do not
  read the current `shipped` rows as terminal until that traffic has drained.

## Ordered Queue

<!-- GENERATED BLOCK — never hand-write or hand-edit the table between the markers.
     Regenerated from status.json and the staged specs: emitted as `ordered_queue` by
     orchestrator.py resume-summary --slug operator-ux (paste it verbatim after a queue change),
     and rewritten in place by the compact stage (orchestrator.py compact --slug operator-ux) at
     cleanup. Only the LIVE queue is rendered here — a shipped/landed row belongs in its
     landing record, not in the live queue. Per-row notes a reader wants to ADD go in the
     annotation zone below, outside the markers — never inside them. -->

<!-- BEGIN GENERATED: ordered-queue -->
| # | Plan | Workstream | Status | Surface (expected) |
|---|------|------------|--------|--------------------|
| 1 | PLAN-09-interaction-mode | WS-06-interaction-mode | staged | marketplace/bundles/plan-marshall/skills/extension-api/standards/marshal-json-reference.md; marketplace/bundles/plan-marshall/skills/manage-config/SKILL.md; marketplace/bundles/plan-marshall/skills/manage-config/scripts/_cmd_skill_domains.py; marketplace/bundles/plan-marshall/skills/manage-config/scripts/_config_defaults.py; marketplace/bundles/plan-marshall/skills/manage-config/standards/data-model.md; marketplace/bundles/plan-marshall/skills/marshall-steward/references/menu-configuration.md; marketplace/bundles/plan-marshall/skills/marshall-steward/references/skill-domains-setup.md; marketplace/bundles/plan-marshall/skills/marshall-steward/references/wizard-flow.md; test/plan-marshall/manage-config/ |
<!-- END GENERATED: ordered-queue -->

### Queue annotations

<!-- ANNOTATION ZONE — hand-written, and deliberately OUTSIDE the generated table markers.
     A regeneration replaces only the table BETWEEN the markers, so everything written here
     survives it. This is where the per-row narrative the generator cannot derive lives — a
     sequencing caveat, a disjointness note, why a row is parked — keyed by plan id. -->

- Surfaces in this epic cluster tightly around `manage-config` and `marshall-steward`.
  With `parallelization_scope: 2`, expect the second slot to be fillable only by PLAN-05
  (`pm-plugin-development`) or PLAN-06/07 (persona standards) — the two footprints that share
  no file with the `manage-config` cluster.
- PLAN-01 — the epic's entry plan and highest-value single change. No dependencies. Its
  acceptance test is the operator's pasted api-sheriff prompt: it must not fire.
- PLAN-02 — sequenced after PLAN-01 for a doc collision only (`skill-domains.md`,
  `manage-config/SKILL.md`), not a logical dependency. Could be reordered if PLAN-01 stalls.
- PLAN-03 — hard sequence after PLAN-01 (same detector file) AND after PLAN-02 (glob knowledge
  is what makes a narrowed set accurate). Carries the epic's sharpest safety constraint:
  narrowing may only drop a domain no resolved task depends on.
- PLAN-04 — independent, but overrides a documented deliberate default
  (`loop_back_without_asking: false`). Its PR must say so rather than presenting the flip as a
  correction. The `max_iterations` guard is the load-bearing justification and is re-verified
  against the dispatcher, not against the prose that asserts it.
- PLAN-05 — the most parallelizable plan in the epic; its entire surface is
  `pm-plugin-development`. Best candidate for the second slot alongside PLAN-01.
- PLAN-06 → PLAN-07 — hard sequence, same file (`agent-behavior-rules.md`).
- PLAN-08 — terminal by construction: depends on PLAN-05, PLAN-06 and PLAN-07, and should also
  follow PLAN-01 and PLAN-04 because those DELETE prompts it would otherwise rewrite. Broadest
  surface in the epic; **expect it to run alone with the second slot deliberately unfilled**.
  Split along bundle boundaries if the PLAN-05 doctor rule flags materially more than the eight
  named sites.
- PLAN-09 — last. Depends on PLAN-04 (census), PLAN-06 and PLAN-07 (the rules `basic` dials
  up). Constraint carried in the spec: `expert` must not re-enable the domain prompt PLAN-01
  removes.
- PLAN-09 — **shipped 2026-09-16 (#1502, merge `ef5959dc`, merge queue).** Last staged plan; queue now 10/10 shipped, zero staged. Realized 15 files vs 9 declared (operator-added scope + review hardening, all gated green). Constraint held (`expert` does not re-enable the PLAN-01-removed prompt). Residue: `references.json`/`create-pr` record still names #1496 (superseded, retained as history); inbox holds 14 live messages (13 candidate-lesson + landing-014) for a follow-up drain — consumer wiring for interaction_mode plus one architecture hint.
- PLAN-03 — **priority raised 2026-09-02.** Its PLAN-02 dependency is downgraded from hard to
  preference; it now depends on PLAN-01 alone, which has shipped. It is the only staged plan
  that addresses a cost being paid on EVERY plan right now (unbounded over-provisioning that
  the executing agent knows is wrong and cannot correct). Still surface-sequenced behind
  PLAN-10 on `_cmd_domain_detect.py`.
- PLAN-10 — staged 2026-09-02 from a live operator observation, not from decompose. Corrects
  PLAN-01's own branch: an `always_on`-only union suppresses over-provisioning. Dependency-free
  and prep-ready. Hard-sequences BEFORE PLAN-03: narrowing a set that is still wrongly narrow is
  meaningless. **Surface corrected 2026-09-03** — its realized footprint is 5 files, not the 4 it
  declared; `phase-1-init/SKILL.md` was added to its Expected Surface from
  `git diff --name-only main...feature/always-on-is-not-a-resolve`. That file is exactly what
  PLAN-08 collides on, so the omission was load-bearing: the gate held only because
  `corpus cross-check` compares a LAUNCHED plan by its realized footprint rather than by its
  declaration. (The prior note here said it shared one file with "live PLAN-06"; PLAN-06 shipped
  as #1382 and the live collision is with PLAN-10's own running plan.)
- **PLAN-02 — `shipped` 2026-09-04 (#1406, merge commit `ef4bf54b5`, merge queue).** 4/4
  deliverables against 5 specified — a re-cut, not a shortfall, plus one genuinely unstaged
  deliverable (the accessor across all nine domain extensions) and one operator-approved
  out-of-footprint fix (`build.py`, a pre-existing quality-gate hard-fail for bundles with no
  test directory, verified reproducible on clean `main` first). Most expensive plan in the epic:
  **12.0M tokens, 18h29m** — 3.0× PLAN-10. `marshalld` was unreachable for the whole run so
  every build degraded to in-process. It shipped **unreviewed** (see the awaitable-refusal Open
  Defect) and its lessons bypassed this epic's inbox (see the orchestration-context Open Defect).
- ⚠ **PLAN-04 and PLAN-09 must be re-grounded before emission — their premises moved under
  them.** PLAN-02 modified `extension-api/standards/marshal-json-reference.md` (declared by
  both) and `manage-config/standards/data-model.md` (declared by PLAN-09) without declaring
  either. This is now a THIRD re-grounding debt alongside PLAN-03's, and unlike PLAN-03's it was
  invisible to the ledger until the landing diff was read.
  **PLAN-03 is unaffected by this landing**: `_cmd_domain_detect.py` is absent from PLAN-02's
  realized 37, so PLAN-03's debt remains exactly the PLAN-10 rewrite already recorded.
- **⛔ The epic is now fully serialized behind PLAN-10, and the 2026-09-03 round is the fourth
  consecutive shortfall.** With `parallelization_scope: 2` and PLAN-10 launched, one slot is
  open and NO staged plan can fill it — every one of the five collides with PLAN-10's realized
  footprint: PLAN-02 (`manage-config/SKILL.md`, `skill-domains.md`), PLAN-03 (all five files),
  PLAN-04 and PLAN-09 (`manage-config/SKILL.md`), PLAN-08 (`phase-1-init/SKILL.md`). The second
  slot is not merely hard to fill, it is unfillable until PLAN-10 lands. `parallelization_scope:
  2` is buying nothing in this state and the epic is effectively sequential.
- **PLAN-08 is `running` — the operator confirmed it STARTED on 2026-09-07, and this note is the
  only record of that.** Nothing in the system observes whether a `running` plan is alive, so
  read this row as *what the operator said*, not as a liveness signal. The row went
  `staged → running` directly: the emit was accepted and the plan started in one operator act,
  so no separate `launched` state was ever recorded for it.
- **⛔ The R-accounting defect is now LIVE in this epic — do not fill a slot on a clean machine
  read.** `orchestrate.md` Step 4 derives `R` from the `launched` count alone, so PLAN-08 at
  `running` reports `R = 0` and `next` will offer `N − R = 2` slots. That is wrong: PLAN-08 holds
  one. This is the first time the epic has actually exercised the defect rather than avoiding
  it — every prior plan went `launched → shipped` and skipped `running` precisely to keep the
  count honest. The truthful state was recorded anyway, because misrecording a row to work
  around a known bug is how the workaround stayed unnamed for six plans.
  **It is harmless right now, and only for a reason unrelated to the defect:** the sole other
  staged plan, PLAN-09, is refused on two independent grounds — its `corpus_spec` collision with
  PLAN-08 on `menu-configuration.md` and `wizard-flow.md`, and `test-quality` PLAN-130 being live
  with `test/` and `test/plan-marshall/` claimed at root, which CONTAINS PLAN-09's
  `test/plan-marshall/manage-config/`. The matcher cannot see that containment — it compares
  normalized paths for equality — so a machine read reports PLAN-09 clean against it. A
  miscounted second slot therefore offers capacity no candidate can legally take.

## Decisions

{One entry per recorded decision — append-only, newest last. This section is a curated
human-facing VIEW; the authoritative append-only record is `logs/decision.log`, written via
`manage-logging --store orchestrator` (decision verb). Because entries carry rationale and
alternatives the log summary need not, this section is NARRATIVE — the compact stage preserves
it verbatim and never regenerates it.}

- Epic opened at operator request. `parallelization_scope` set to **2** (project default is
  `1`): the operator accepted one config-surface plan running alongside one disjoint
  persona/language-surface plan. Alternatives offered were `1` (strictly sequential, matching
  the project default) and `3` (rejected — this epic's surfaces collide too much for a third
  slot to fill).
- The three user-communication rules — language, vocabulary, and output volume — live in ONE
  new dedicated standards file, `persona-plan-marshall-agent/standards/user-communication.md`,
  loaded UNCONDITIONALLY beside `agent-behavior-rules.md`. The operator offered two options (a
  standalone skill, or folding into `agent-behavior-rules.md`); a third was proposed and chosen
  because it dominates both. A standalone skill was rejected as **opt-in by construction** — it
  binds only when something remembers to load it, and "German is not honoured *throughout*" is
  precisely the failure a load-when-remembered rule produces; adopting it would also require
  every phase skill to declare the dependency, a permanent conformance burden. Folding into
  `agent-behavior-rules.md` binds correctly but gives no isolation, scattering the rules through
  a 368-line general-purpose file. The new-standards-file option binds unconditionally AND keeps
  the three rules in one document. It is available only because the persona already uses
  progressive disclosure (Step 1 unconditional, Steps 2–5 "as needed") — the new file joins the
  unconditional tier, and placing it in the "as needed" tier would reproduce the exact opt-in
  failure the standalone skill was rejected for. Consequence: PLAN-06 creates the file and its
  load step; PLAN-07's surface NARROWED to appending to it, no longer touching
  `agent-behavior-rules.md` or the persona `SKILL.md`; PLAN-06 → PLAN-07 sequencing became
  structural rather than stylistic.
- **The persona-loading restructure lands as WS-07 IN THIS EPIC, not as a separate epic**
  (operator decision 2026-09-04, `AskUserQuestion`). Options offered: a new epic — which the
  orchestrator **recommended** — a new workstream here, or record-only-and-defer. The operator
  chose the workstream. ⛔ **This is a deliberate exception to this epic's own earlier ruling,
  not a reversal of it.** On 2026-09-03 the operator ruled that finalize-machinery debt gets a
  separate epic so operator-ux would not become a maintenance backlog; WS-07 is machinery-shaped
  and would fall under that ruling on surface alone. The distinguishing fact accepted here is
  **authorship**: PLAN-06 and PLAN-07 put `user-communication.md` into the unconditional tier,
  so this epic is restructuring a surface it created, whereas the finalize defects were
  inherited from a lane this epic does not own. The accepted cost is that operator-ux now
  carries one workstream whose surface is the persona resolver and the dispatch site.
  **This does NOT reverse the user-communication decision above**, which remains correct on its
  own terms: unconditional binding was the right call, and WS-07 changes neither the rules nor
  their strength. What WS-07 revisits is narrower and was not in front of the operator then —
  the *register* Steps 2–5 select in (prose judgement rather than `composes:`), and the
  *audience* the standard is shipped to (a leaf that can reach only `display_detail` receives
  the full three-rule document). The prior entry's own reasoning is in fact the seed of this
  one: it treated "Step 1 unconditional, Steps 2–5 as needed" as settled background, and WS-07
  is the first time that background was examined rather than used.

- **A value standard for `project.user_language` (BCP-47 or otherwise) was raised and DECLINED
  on 2026-09-05 — do not re-raise it without new evidence.** The operator observed that the knob
  accepts free prose and asked for enforcement; on reading the code the permissiveness turned out
  to be a decision PLAN-06 shipped deliberately, argued in the validator's own docstring
  (*"no BCP-47 grammar is enforced — `auto`, `de`, `German` and `pt-BR` are all legitimate, and
  over-validating would reject valid input for no reader's benefit"*) and again in
  `user-communication.md` Rule 1 (*"prose an agent reads, not a tag code a parser consumes"*).
  The sole consumer is that prose rule and **no code parses the value**, so a grammar buys no
  reader anything while rejecting natural inputs, requiring an `auto` carve-out (`auto` is not a
  valid BCP-47 tag), and forcing a migration of every existing pin. The operator agreed and
  dropped it. ⚠ **The residual cost is accepted, not absent:** Rule 1 pins on *"anything other
  than `auto`"*, so a typo such as `Englsih` still becomes a silent pin, and `de` / `German` /
  `Deutsch` remain three spellings of one configuration. Reopen only if that silent-pin case is
  actually observed to bite. The Open Defect and the WS-04 follow-up section written for this
   were removed on the same decision; `logs/decision.log` holds the full analysis.

- **Inbox drain 2026-09-16 — 14 messages from `implement-plan-09-interaction-mode`, all consumed.** 13 candidate-lesson + 1 landing (-014, `complete: true`, already reconciled via paste as PLAN-09 #1502 — recorded as reconciled-duplicate, no re-stamp). Dispositions: **promoted** 4 (corpus `2026-09-16-17-001` ← -002 non-object config roots; `-002` ← -003 plugin-doctor stale-scope flag loop; `-003` ← -004 derive-from-authoritative-tuple, with -007 recorded as recurrence of it; `-004` ← -012 fragment single-root resolver); **discarded** 9 (-001 single-instance doc wording, fix shipped; -005/-006/-008 plan-local implementation details, fixes shipped; -007 duplicate of promoted -004 theme; -009/-010/-011 argparse invented-flag variants already covered by canonical-invocation guards per the plan's own retrospective; -013 architecture hint already `taken_into_account` by enrich insight). No fold (no staged spec remains), no stage (consumer-wiring follow-up needs operator scoping — see Open Defects). Expected surface unchanged by every fold-less disposition: adds no file surface.

## Open Defects

{Known defects surfaced by landings or observations that are not yet owned by a staged
plan. When a defect is folded into a plan spec, move it out of this list and note the
owning PLAN-NN.}

Every item below is labelled `OBSERVED` (read at HEAD in this session) or `HYPOTHESIS`
(inferred, carrying a named confirm/refute artifact), per the verify-first contract.

- **OBSERVED — the `archive-plan` completion record is lost on 17 of 20 archived plans, so the
  standard's own MUST is violated at scale and nothing catches it.** Surfaced 2026-09-08 by
  PLAN-08's landing, which reported the miss as a one-off ordering slip by its own agent. A scan
  of every directory under `.plan/local/archived-plans/` refutes that scoping: **17 of 20 archived
  plans carry no `archive-plan` row at all**, while carrying the rest of the step map — and in 17
  cases the immediately-preceding `emit-landing` row. Only three recorded it
  (`2026-09-03-always-on-is-not-a-resolve`, `2026-09-03-output-volume-standard`,
  `2026-09-07-plan-130-sweep-the-prose-the-widened-rules`). The instances span 2026-08-22 to
  2026-09-08 and many different plan agents.
  ⛔ **The prose is not ambiguous and is violated anyway.**
  `phase-6-finalize/standards/archive-plan.md:52` states the `mark-step-done` call MUST precede
  the archive and explains the exact failure mode inline. An 85% violation rate against an
  unambiguous, self-explaining MUST is the argument for moving the constraint into
  `manage-status archive` itself — refuse to archive while the terminal step's row is absent —
  which is what lesson `2026-09-08-13-001` proposes. **The retrospective scan that lesson listed
  as an optional extra is the step that converted a self-blamed one-off into a measured systemic
  defect**; without it the lesson would have shipped with the wrong cause attached.
  *Not staged.* Source: full scan of `.plan/local/archived-plans/` + `archive-plan.md` read at HEAD.

- **OBSERVED — PLAN-08 shipped 10 AsciiDoc files that its own self-review instrument structurally
  could not see, and the emit-time instruction to say so was not discharged.** The emit required
  PLAN-08's outline to "either confirm the gap is fixed or state it in its own report". Its report
  does neither. The gap is confirmed **still open at HEAD**: no `.adoc` detector exists anywhere
  under `pm-plugin-development/skills/ext-self-review-plan-marshall/`. So the reported
  `pre-submission-self-review clean: 147 candidates examined, no check matched` covers the
  marketplace half only — all 10 shipped `doc/user/*.adoc` files, deliverable 2 in its entirety,
  were invisible to it. ⚠ **What actually reviewed them was CodeRabbit**, which filed findings on
  `commands.adoc`, `configuration.adoc` and `getting-started.adoc`. The AsciiDoc half of a
  documentation plan was covered by an external reviewer rather than by the instrument the plan
  reported clean, and only luck put a reviewer there. Tracked by existing corpus lesson
  `2026-09-07-13-002`; recorded here because a second plan has now shipped through the gap.
  *Not staged.* Source: `grep` for `.adoc` across the surfacer at HEAD + PR #1447 comment set.

- **OBSERVED — `corpus cross-check`'s `corpus_spec` class does not filter by ledger status, so a
  SHIPPED spec collides forever.** Surfaced 2026-09-08 while testing PLAN-09 for emission. Its
  `file_overlap_matches[]` carries seven rows, and six name shipped specs (PLAN-01, 02, 03, 04, 06,
  08, 10) whose plans have all merged. A shipped spec stays in `plans/` as the audit record, so the
  matcher keeps comparing against it and the literal gate reading in `orchestrate.md` Step 4 — *no
  `file_overlap_matches[]` row naming that candidate's spec* — can never again be satisfied by any
  plan sharing a file with a shipped sibling. ⛔ **Read literally, this blocks PLAN-09 permanently
  and would block every future spec in a maturing corpus**, because the collision set only ever
  grows. This is the exact mirror of the already-recorded containment defect: there the matcher saw
  too little, here it sees too much, and in both cases the machine verdict needs a human to say
  which rows are live. *Remedy shape (not decided here):* the overlap matcher restricts the
  `corpus_spec` class to specs whose ledger row is not terminal. *Not staged.*
  Source: `corpus cross-check --slug operator-ux` at HEAD, read against the queue.

- **OBSERVED — the orchestrator's status vocabulary and its concurrency accounting disagree, so
  a plan the operator confirmed as STARTED becomes invisible to the slot count.** Surfaced
  2026-09-05 by actually performing the transition rather than avoiding it.
  `orchestrate.md` Step 4 says: *"Count `R`, the plans currently in `launched` status, and select
  up to `N − R` candidates"* — R counts `launched` and nothing else. But `running` is a valid
  status (`queue --transition PLAN-03 --status running` succeeds, and accepts the jump straight
  from `staged`), and `resume-summary` renders it correctly under its own `**Running**` group. So
  the render side knows about `running` and the accounting side does not: the moment a plan moves
  `launched → running` — the one transition the emit≠running invariant explicitly reserves to the
  operator — it stops occupying a slot as far as `next` is concerned. The next `next` computes
  `R = 0`, `N − R = 2`, and offers a slot the running plan already holds.
  ⛔ **The invariant is self-defeating as written**: it insists the operator owns the
  `launched → running` transition, and the accounting punishes them for exercising it. Staying at
  `launched` forever is the only way to keep the slot count correct, which makes `running`
  unreachable in practice.
  *Corroborating history, and it explains a pattern the ledger already carried:* PLAN-01, 02, 05,
  06, 07 and 10 ALL went `launched → shipped` and none passed through `running`. The 2026-09-04
  status read even recorded the avoidance explicitly for PLAN-02 — *"row stays launched
  deliberately: next derives R from the launched count, so a running transition would falsely
  free a slot"*. That was a workaround being applied without the defect being named. It is named
  now.
  *Remedy shape (for the plan that owns it, not decided here):* R is the count of plans in ANY
  slot-occupying status — `launched` **or** `running` — and the doc should say so rather than
  naming one of the two. A `plan-orchestrator` defect: the **first machinery defect in this epic
  that is not `phase-6-finalize`**, so it does not route to finalize-machinery. Recorded here and
  NOT staged. Source: performed transition + `orchestrate.md` Step 4 read at HEAD.

- ↪ **The awaitable-reviewer-refusal hole** — relocated to `settled.md` § "The awaitable-reviewer-refusal hole": closed 2026-09-07 on PLAN-04 and re-confirmed by PLAN-08 (#1447), whose CodeRabbit review filed 89 substantive comments.
- ↪ **The orchestration-context bypass** — relocated to `settled.md` § "The orchestration-context bypass": closed 2026-09-07 on PLAN-04 and re-confirmed by PLAN-08 (#1447), whose full 12-message drain reached this inbox.
- **OBSERVED — a landing narrative counts candidate lessons EMITTED and reports them as corpus
  entries CREATED, and the two differ by the whole dedup rate.** Two instances, both measured, in
  consecutive plans. PLAN-02 claimed 14 where 12 carried the date and 7 were attributable.
  PLAN-03 (#1422) claimed nine went to the global store; the corpus went from **113 to 116**
  entries and exactly **three** carry a `2026-09-06` id (`07-001`, `07-002`, `07-003`) — six of
  the nine were folded or deduped by `finalize-step-lessons-housekeeping`, which ran `done`.
  ⛔ **Opened as its own defect rather than folded into the bypass entry above, because the two are
  independent**: the bypass is about WHERE lessons land, this is about the number reported landing
  anywhere, and a fix to either leaves the other intact. The reporting step has the true figure —
  housekeeping returns its `rm / promo / adapt / keep` tally — so the remedy is to report the
  post-housekeeping count, or to report both and label them. Until then, **no lesson count in any
  landing narrative may be entered in a ledger without re-measuring the corpus.** Source: PLAN-02
  and PLAN-03 landings, corroborated against `manage-lessons list --status all` totals before and
  after. Routed to finalize-machinery.

- **OBSERVED — PLAN-03's deliverable 4 shipped as a record, not as a user-visible report, so the
  narrowing is still silent to the operator.** The spec asked that *"the system reports the
  narrowing to the user in one line rather than silently — a domain set changing under a plan is
  exactly the kind of thing that must be visible"*. At HEAD `domain_narrow_report` is emitted by
  `phase-3-outline/SKILL.md` and `workflow/light-lane.md` and **read by nothing**: an
  inventory-wide sweep returns 4 hits across those 2 files, both producers, and
  `plan-marshall/workflow/planning-outline.md` does not enumerate the field. The shipped code says
  so itself — *"the decision log is the report's only CONSUMED sink today"*, *"wiring a consumer
  there is owed follow-up, not present behaviour"*.
  ⭐ **The plan behaved correctly and this is not a process failure**: three of its own self-review
  findings were prose claiming that sink existed, and it removed the false claim rather than
  faking the sink — its subject rule applied to itself. ⛔ But the decision log is a developer
  artifact, so in an operator-UX epic the deliverable's actual purpose is unmet. **Follow-up:
  wire a consumer in `plan-marshall/workflow/planning-outline.md`** — a file no spec in this epic
  declares. Small, well-specified, and the natural companion to any WS-04/WS-05 surface work.
  Source: PLAN-03 landing, corroborated by `architecture search --content` and by reading the
  three self-describing sites.

- **OBSERVED — nothing in the repository detects a false "only X and Y" coverage claim except
  self-review, and self-review only sees the change's own delta.** PLAN-02's
  `pre-submission-self-review` filed 4 `contract_drift` findings; **three of the four were
  already false at HEAD before the plan touched those files**. Its `lessons-capture` step
  established that no test, no plugin-doctor rule and no quality gate detects the class. The
  consequence is structural: a false coverage claim in a file no current plan touches is
  undetectable and stays false indefinitely, and it is found only by the accident of a later plan
  editing that file. ⛔ **This is the same shape as the enforcement-matrix fork already recorded
  below** (a hand-maintained mirror derived from nothing) — that entry is one instance, this is
  the general class, and the derive-vs-collapse decision the operator still owes applies to both.
  Recorded here and NOT staged. Source: PLAN-02 landing, `pre-submission-self-review` +
  `lessons-capture` findings.

- **OBSERVED — persona content is selected in three registers, and the only non-declarative
  one lives inside the base persona that every context loads unconditionally.** Raised by the
  operator 2026-09-04 as a token-waste observation about `execution-context`; corroborated at
  HEAD and sharpened — the waste is a symptom, the register split is the defect. **OWNED BY
  WS-07.**

  *Measured, not inferred.* The unconditional tier every `execution-context` leaf loads is
  `SKILL.md` (15,874 B) + `standards/agent-behavior-rules.md` (37,324 B) +
  `standards/user-communication.md` (9,550 B) = **62,748 B / ~8,645 words**, before the caller's
  `skills[]`, before the workflow doc, before the task. `agents/execution-context.md:71` issues
  the `Skill:` load and `:75` requires strict compliance; `SKILL.md` Step 1 declares two of the
  three standards "not optional and not loaded on demand — the unconditional tier".

  *The three registers, read at HEAD:* (1) **declarative** — `composes:` / `profiles:`
  frontmatter, flattened by `manage-personas resolve`, called from `phase-4-plan/SKILL.md:369`,
  auditable and zero-cost when unselected; (2) **hardcoded** — the base, which
  `manage-personas/SKILL.md` states is "always included, unconditionally — it is never read from
  `composes:`"; (3) **prose** — `SKILL.md` Steps 2–5 ("As Needed") for `tool-usage-patterns.md`,
  `argument-naming.md`, `thoroughness.md` and `coverage-gathering-contract.md`, resolved by the
  agent's runtime judgement. ⛔ Register 3 is precisely what the resolver's own prohibited-actions
  list forbids everywhere else: *"Do not hardcode a persona↔profile table — the persona's
  `profiles:` frontmatter is the binding source of truth."* The base persona hardcodes a
  standard↔context table in English.

  *Why the leaf is the sharpest instance.* `user-communication.md` Rule 3 **self-declares** it
  does not apply to the context loading it — *"It does not reach the sub-agent return path: what
  a dispatched envelope returns to its caller is governed by `citations-only-return.md`."* Rule
  1's in-scope list is `AskUserQuestion` prompts (a leaf structurally cannot fire one), phase
  summaries, the finalize output template, and user-facing error text — all main-context. The
  only leaf-reachable item is Rule 1a. So a leaf loads 9,550 B to govern one ≤80-character ASCII
  string.

  *What is NOT the remedy, and the file says so itself.* "Make it opt-in" is refuted in advance:
  *"All three load unconditionally … because an opt-in placement reproduces the failure mode they
  exist to fix"*, and Rule 1a spends a paragraph killing the exemption reading. The remedy is a
  split by **audience** and by **context**, both fixed — not a conditional. The hard rules (one
  Bash command per call, `.plan/` through scripts only, no direct `gh`/`glab`, leaves cannot
  dispatch) stay genuinely universal, because they must reach contexts that never call the
  resolver; only the advisory tiers move.

  *This epic authored the surface.* PLAN-06 (#1382) and PLAN-07 (#1387) added
  `user-communication.md` — 156 lines, 3 files, `git diff --stat 219da7b1d~1 HEAD` — to the
  unconditional tier. That is why the restructure is admitted here rather than routed to a
  machinery epic; see the Decisions entry for the recorded exception.

  ⚠ **NOT measured: the per-plan multiplier.** No `[DISPATCH]` records are present in
  `.plan/local/logs/`, so the number of leaf dispatches per plan — and therefore the total token
  cost — could not be derived. The per-dispatch figure above is measured; any per-plan figure
  would be invented. This is the same instrumentation gap the "phase-6 cost figures are floors"
  watch already records (lesson `2026-09-02-13-002`).

  Source: operator observation 2026-09-04, corroborated at
  `persona-plan-marshall-agent/SKILL.md`, `standards/user-communication.md`,
  `manage-personas/SKILL.md`, `agents/execution-context.md`, `phase-4-plan/SKILL.md`, and the
  `composes:` / `profiles:` frontmatter of all nine `persona-*` skills.

- **OBSERVED — the pre-push quality gate certifies a tree that review never sees.**
  `pre-push-quality-gate` is `order: 5`; `finalize-step-simplify` is `order: 8`. On PLAN-10 the
  gate certified `43ed295b`, simplify then advanced HEAD to `8827a7f2`, so **the tree reviewers
  reviewed was never locally gated**. The review-retrospective did not paper over it: it
  recorded its review-vs-gate delta as `excluded` / `gates_did_not_cover_reviewed_tree` with
  `structural_share: null` — withheld, not zero, which is the honest reporting this defect
  needs to stay visible. Corpus lesson `2026-09-03-11-002` already tracks the ordering hole.
  A `phase-6-finalize` defect. Routed to the finalize-machinery epic. Source: PLAN-10 landing.

- **OBSERVED — `prune-local-and-remote-ref` aborts on an already-deleted local branch and
  leaves the remote-tracking ref stale.** `worktree-remove` deletes the local branch ref as part
  of its own cleanup; the later `prune-local-and-remote-ref` then fails `branch_delete_failed`
  on the absent branch and returns **before** its remote-tracking step, stranding
  `refs/remotes/origin/{branch}`. PLAN-10's run issued the single targeted `update-ref -d` the
  standard permits and verified both refs gone, so the blast radius was contained by the
  operator's manual step — not by the verb. ⛔ The two steps are individually correct and
  jointly wrong, which is why neither one's own tests would catch it. A `phase-6-finalize` /
  `workflow-integration-git` defect. Routed to the finalize-machinery epic. Source: PLAN-10
  landing Residue, 2026-09-03.

- ↪ **The sourcery false-participation defect** — relocated to `settled.md` § "The sourcery false-participation defect": resolved 2026-09-03; the refusal pattern is registered and the defect has not recurred since.
- **OBSERVED — a merged plan is invisible to the epic until its landing arrives, and nothing
  bounds how long that takes.** ⚠ **AMENDED 2026-09-03 after the landing arrived — the original
  absolute claim is REFUTED and is kept here so the correction is legible.**

  *What the defect originally said (and got wrong):* that PLAN-07 "filed no `kind: landing`
  message", that it was "absent from `archived-plans/`", and that "`emit-landing` and
  `archive-plan` did not complete". All three are false. The landing was filed as
  `output-volume-standard-017.md`, the plan IS at
  `.plan/local/archived-plans/2026-09-03-output-volume-standard`, and all 21 finalize steps
  completed. The run had been **interrupted after the merge and resumed in a second session**;
  what the original observation read as a terminal state was a mid-interruption snapshot.
  ⛔ The methodological lesson is the sharper one: *absence observed once is not absence*, and
  this defect inferred a completed failure from a single point-in-time read of a lane that was
  merely paused.

  *What survives, and it is still a real defect:* the landing arrived at 16:12 UTC against a
  10:24 merge — a **5h48m window** in which the ledger row read `staged` for merged work. For
  that whole window `next` would have re-emitted PLAN-07's command, and it had in fact already
  been emitted once. **Nothing detects the window**: `inbox list` reports what WAS filed and has
  no notion of a landing that is OWED, so an epic awaiting a slow landing looks identical to one
  with no news. The gap was closed here by `cleanup`'s re-grounding pass, which is a manual
  sweep, not a detector.

  *Now corroborated:* `inbox landing-check` on the arrived message returns `complete: true`,
  so once a landing does arrive the completeness guarantee holds. The defect is purely the
  unbounded and undetected latency, not the content.
  A `phase-6-finalize` defect, not operator-UX work, so it is recorded here and NOT staged.
  Source: `cleanup` A1 re-grounding 2026-09-03; amended by the `analyze` drain the same day.

- **OBSERVED — the lessons pipeline re-files what the corpus already holds, and nothing
  deduplicates before transmission.** The `analyze` drain of PLAN-07's 11 `candidate-lesson`
  messages found **6 already present in the corpus** — `2026-09-03-10-001` (verify-freshness
  double verdict), `2026-08-25-09-012` + `2026-09-02-08-001` (sourcery false participation),
  `2026-08-25-09-014` (twice over, as the doc-side and script-side halves of one defect), and
  `2026-09-03-11-004` / `2026-09-03-11-005` (two argparse-rejection lessons filed by the
  *immediately preceding plan in this same epic*). Only 5 of 11 were new. ⛔ **The dedup burden
  sits entirely on the orchestrator's drain**, which is a per-message manual corpus comparison
  that scales with corpus size — now 68 lessons. One message (`-015`) even names its own
  duplicate and asks the orchestrator to merge the pair, which is the producer knowing the
  defect exists and transmitting anyway. **Consequence:** the corpus grows monotonically with
  re-observations of known defects, and its signal — which lessons are NEW — is only recoverable
  by the manual pass done here. A `plan-retrospective` / `lessons-capture` defect, not
  operator-UX work. Recorded here and NOT staged. Source: `analyze` drain, 2026-09-03.

- **OBSERVED — `branch-sync-state` cannot reach its own `remote_absent_landed` verdict once
  branch-cleanup has removed the worktree, so the one state that answers correctly is
  unreachable exactly when it is needed.** On PLAN-07's resumed session the call returned
  `status: error / head_unresolvable`. The push re-entry contract's documented default for an
  error payload is RE-FIRE ("fail toward pushing") — which after a successful merge would have
  tried to resurrect a merged-and-deleted branch. ⛔ **The default is written for an *ambiguous*
  parity state; post-merge it is not ambiguous**, and the contract does not distinguish the two.
  The run skipped on independent evidence (`ci pr view` → `state: merged`, `9fd0957`), so the
  blast radius was contained by the executing agent's judgement rather than by the contract.
  **Consequence if unnoticed:** a re-push attempt against a deleted branch at the end of an
  otherwise-successful finalize. A `phase-6-finalize` / `workflow-integration-git` defect, not
  operator-UX work. Recorded here and NOT staged. Source: PLAN-07 landing Residue, corroborated
  against the landing message 2026-09-03.

- **OBSERVED — `finalize-step-simplify`'s edits are never self-reviewed, and its own
  reconciliation cannot see commitments recorded in outline prose.** Two structural gaps, both
  surfaced live by PLAN-10 at its simplify step and both confirmed by the executor's own
  report. (a) Self-review runs at **order 7**, simplify at **order 9**, so every simplify edit
  ships unreviewed by construction — demonstrated by this very run, where simplify made a
  production-Python edit that REVERSED a decision the outline had recorded on purpose, and the
  only thing that caught it was the executor reading the diff. (b) Simplify's reconciliation
  returned `verdict: clear, commitments_considered: 0` — not a miss but a wrong search
  location: it reads the findings store only, so a commitment living in the solution outline's
  Approach prose is invisible to it. ⛔ The two compound: the step most likely to reverse a
  decision is also the step nothing reviews. A `phase-6-finalize` ordering-and-scope defect,
  not operator-UX work, so it is recorded here and NOT staged in this epic — it belongs to the
  separate finalize-machinery epic the watch below proposes.
  Source: PLAN-10 mid-flight report, pre-push, 2026-09-03.

- **OBSERVED — over-provisioning is unbounded, and the executing agent knowingly persists a set
  it has already judged wrong.** A live plan resolved `reason=over_provisioned_resolve` with
  zero narrative matches and was given EVERY offerable domain including `javascript`, which it
  does not touch. The agent recorded that the set was wrong, noted the remedy ("narrowing
  references.json domains to java,java-cui,documentation is a one-call fix"), and persisted the
  wrong set anyway — because the workflow treats a non-ambiguous resolve as final and offers no
  correction path. ⛔ **This is the cost side of the operator's own over-provision policy, and
  it is the exact condition PLAN-03 exists to close.** Two distinct facts, kept apart: (a) the
  detector genuinely has no signal on a zero narrative match, so unbounded is the only honest
  thing it can do alone; (b) the AGENT does have signal, and nothing consumes it. (a) is
  PLAN-02's territory (give the glob leg something to match); (b) is PLAN-03's.
  Source: operator paste, corroborated at `_cmd_domain_detect.py` §§ `_offerable_domains`,
  the zero-match `prompt_candidates` construction.

- **OBSERVED — PLAN-01's over-provisioning is suppressed by a single `always_on` domain, and
  the epic's own acceptance test was too narrow to catch it.** At HEAD after #1380 the
  zero-narrative-match path guards on `if inclusion_union:` and returns
  `inclusion_only_resolve` with `ambiguous: False` BEFORE the over-provision branch is
  reachable. So a project with any blanket `always_on` domain never over-provisions. Observed
  live on a Python-heavy plan that resolved to `plan-marshall-plugin-dev` alone and omitted
  `python`. The underlying error is a conflation: **`always_on` is evidence about the PROJECT;
  `glob_matched` is evidence about THIS PLAN.** A union made only of the former has found
  nothing about the work at hand — the same state as an empty union, wearing a result. This is
  the epic's recurring "which zero is this" theme (ADR-019) inside its own first landing.
  ⛔ **Lesson for the epic's own method:** the acceptance test was stated as "the api-sheriff
  prompt must not fire". It doesn't. A test phrased as "no domain prompt fires on a plan whose
  domain is inferable" would have caught this. Owned by **PLAN-10**.
  Source: operator paste, corroborated at `_cmd_domain_detect.py` and by
  `manage-config skill-domains get` on both domains.

- **OBSERVED — CONFIRMED CLASS (2 instances): any post-`branch-cleanup` operation gated on the
  phase-entry worktree assertion is unrunnable by construction.** Upgraded 2026-09-03 from a
  single-instance defect. Two independent symptoms, one root cause — `branch-cleanup` removes
  the worktree while `metadata.worktree_path` still names it, and the phase-entry assertion
  fires before any later verdict can be reached:
  - **PLAN-01 (#1380)** — the pre-archive findings-check could not run. The executor answered
    the blocking question directly (0 pending, both stores) and logged it.
  - **PLAN-06 (#1382)** — `status.json` still records `5-execute` as `in_progress` though it
    completed, and the correction was unreachable for the same reason. ⛔ The executor
    **declined to clear the metadata to get past the safety guard**, which is the right call:
    the guard is not the defect, the ordering is. The metrics ledger is correct
    (`close_count: 2`, `end_time` present); only the status row disagrees.
  A `phase-6-finalize` step-ordering defect, not operator-UX work, so it is recorded here and
  NOT staged in this epic.
  Source: inbox `domain-over-provision-005.md` (#1380) and `user-language-and-vocabulary-009.md`
  (#1382).

- **OBSERVED — `_DEF_OR_CLASS` omits `async def`, so coroutine and module docstrings are
  invisible to the `user_facing_strings` detector.** Three sibling detectors use the variant
  that includes it; this one does not. Six live sites in `marshalld.py` are currently unseen.
  Recorded here — unlike the other machinery findings, which went only to the corpus —
  **because that detector is one of the instruments PLAN-08 depends on**: a conformance sweep
  measured by a detector with a known blind spot reports a clean result it did not earn.
  PLAN-08's outline must confirm this is fixed, or state the gap in its own report.
  Also corpus lesson `2026-09-02-14-003`.
  Source: inbox `domain-over-provision-003.md`.

- **OBSERVED — PLAN-01 under-declared its surface by 12 of 17 files (71%), and two of them
  belonged to PLAN-03.** Declared 5 entries; realized 17. `phase-2-refine/SKILL.md` and
  `phase-3-outline/SKILL.md` are in PLAN-03's Expected Surface, and PLAN-01 also widened
  `resolve-outline-skill` into an N-to-1 domain selector — scope absent from its spec
  entirely. ⛔ **No collision occurred only because PLAN-03 was dependency-sequenced for
  independent reasons.** Had it been dependency-free, the gate would have offered it for the
  second slot on a comparison missing two of its files. This is a measured instance of the
  under-declaration bound the standard documents as the dominant residual class, inside this
  epic, on its first parallel pair. Corrected in the same act: PLAN-02 and PLAN-03 carry
  re-verify warnings naming the moved files.
  Source: `git show --stat bf012b2cd` against the staged spec.

- **OBSERVED (from PLAN-05's landing, PR #1378) — the enforcement matrix for
  `askuserquestion-prompt-quality` is a hand-maintained mirror in four places, derived from
  nothing.** Which obligations the rule mechanically checks (1, 2, 5) and which it declares
  blind (3, 4) is stated independently in `askuserquestion-patterns.md`,
  `plugin-architecture/SKILL.md`, `plugin-doctor/references/rule-catalog.md`, and the rule's
  test file — none derived from `_analyze_askuserquestion_prompt_quality.py`. A change to the
  analyzer can leave all of them asserting coverage the code no longer provides, with nothing
  failing. Credible rather than speculative: PLAN-05's own self-review filed **11 findings,
  every one `contract_drift`** in exactly these files, each fixed by deleting an over-claim —
  converging the prose while leaving the structure that produced it. ⛔ **This is a fork
  reserved to the operator, not a defect to fold.** *Derive* (analyzer-owned coverage
  constant plus a rule or test asserting agreement) closes the class but adds a generation
  seam and another mirror-checking rule; *collapse* (one authoritative site, the rest
  cross-referencing) is cheaper, needs no new mechanism, and matches the
  deletion-over-correction convergence PLAN-05 established — but prevents nothing
  mechanically. The generalisable question is whether the marketplace wants a standing
  derived-doc mechanism for rule coverage, since this rule is not the only one publishing an
  enforcement boundary in prose.
  Source: inbox `prompt-standard-and-doctor-rule-001.md`; CodeRabbit thread
  `PRRT_kwDOQ3xasM6eYroJ`.

- **OBSERVED — the lessons corpus knew about two defects, the housekeeping step read and
  retained both, and the run committed them anyway.** Lessons `2026-08-25-09-002` and
  `2026-08-25-09-007` were both `active` and unapplied; PLAN-05's own
  `lessons-housekeeping` step reviewed and RETAINED both on 2026-09-01 as "surface untouched
  by this plan"; the run then produced a second independent instance of each. The gap is not
  in either lesson — it is that a retain verdict is made against the plan's *declared* surface
  while the recurrence happens in the *executor's* behaviour, which no surface predicate sees.
  Recorded as its own defect because it is about the housekeeping step, not about either
  lesson; the recurrences themselves are folded onto the corpus entries.
  Source: inbox `prompt-standard-and-doctor-rule-003.md` / `-004.md`, corroborated against the
  live corpus (`manage-lessons list` confirms both `active`).

- **OBSERVED — the autonomy-gate premise is already three-quarters true, and the real gap is
  one knob, not five.** `init_without_asking`, `execute_without_asking` and
  `finalize_without_asking` already default to `true`
  (`manage-config/scripts/_config_defaults.py`; `marshall-steward/references/wizard-flow.md`
  § "The defaults are a partition, not 'all pause'"). Only `plan_without_asking` (`false`, and
  the operator wants it to stay `false`) and `loop_back_without_asking` (`false`) pause. So the
  actionable change from the operator's first bullet is **`loop_back_without_asking` → `true`**
  plus the step-owned `final_merge_without_asking` under `default:branch-cleanup` (also
  `false`) — not a sweep of five knobs. The current `false` on `loop_back_without_asking` is
  documented as deliberate ("so unattended runs cannot silently re-enter execute"), so
  flipping it is a stated trade-off to decide, not an oversight to correct.
  Source: operator paste, corroborated against `_config_defaults.py` and `manage-config/SKILL.md`.

- **OBSERVED — "profile" is already a taken word in this codebase, and reusing it for
  Basic/Advanced/Expert would collide.** `skill_domains.active_profiles` and
  `skills_by_profile` already denote *work-activity* profiles (`implementation`,
  `module_testing`, `integration_testing`, `quality`, `documentation`), read by the persona
  resolver and the domain wizard. The operator's proposed experience-level knob needs a
  different noun. Deciding that noun is a genuine fork and is surfaced at `decompose`.
  Source: `manage-config/scripts/_cmd_skill_domains.py`, `skill-domains-setup.md`.

- **OBSERVED — no user-language / locale concept exists anywhere in the marketplace.** A
  marketplace-wide search over `*.md` and `*.py` for `user_language`, `output_language`,
  `locale`, "respond in the user's language" and equivalents returns only unrelated Java
  `Locale` examples in `pm-dev-java` standards. The German-not-honoured complaint therefore has
  no partially-built surface to extend — this workstream builds the concept from zero, and its
  natural home is `persona-plan-marshall-agent` (the unconditional base every persona inherits).
  An asserted absence is the higher-risk half of the verify-first contract, so this one was
  verified by exhaustive search rather than assumed.
  Source: operator paste, corroborated by marketplace-wide grep.

- **OBSERVED — the `AskUserQuestion` surface is large and has an existing authoring standard
  that is not being met.** 126 marketplace files reference `AskUserQuestion`;
  `pm-plugin-development/skills/plugin-architecture/references/askuserquestion-patterns.md`
  already exists as the authoring reference. The heaviest prompt sites are
  `marshall-steward/references/menu-configuration.md` (29),
  `phase-6-finalize/standards/branch-cleanup.md` (24), `phase-1-init/SKILL.md` (20) and
  `plan-marshall/workflow/planning.md` (18). So the "more context in prompts" work is a
  *conformance* problem against an existing standard plus a strengthening of that standard —
  not a greenfield one.
  Source: operator paste, corroborated by grep counts at HEAD.

- **OBSERVED (was HYPOTHESIS; CONFIRMED and sharpened by an operator paste of a live
  ambiguous-domain prompt) — the mechanism that would suppress the domain prompt already
  exists, is absent by default, and is never seeded by the setup wizard.** Read at HEAD in
  `manage-config/scripts/_cmd_domain_detect.py`: the detector composes
  `{narrative matches} ∪ always_on_set ∪ glob_matched_set`, and `ambiguous` is `true` on a
  detector multi-match **or** on a zero-match whose `always_on`/`file_globs` union is empty.
  Both inclusion keys are documented as *"absent by default — no seed into
  `DEFAULT_SYSTEM_DOMAIN` / `get_default_config()`"* (`standards/skill-domains.md`
  § Domain Inclusion), and a grep over the whole `marshall-steward/` tree finds **no writer
  for either key** — the only writer anywhere is the manual
  `skill-domains set-inclusion` verb. So every project ships with both legs empty. The
  consequence is structural, not incidental: **narrative matching is a literal token match**
  (`_tokenize` splits on non-alphanumerics and lowercases), so a request that says "fix the
  flaky Vert.x test in api-sheriff" contains no token `java` and no token `java-cui`, scores
  zero, finds both inclusion legs empty, and prompts. That is why the operator sees this in
  *nearly every plan* — it is the default configuration's steady state, not an edge case.
  Three independent remedies exist and the epic must choose deliberately among them (a fork
  for `decompose`): (a) have `skill-domains configure` seed `file_globs` from each domain
  extension's own file-type knowledge at wizard time; (b) flip the zero-match branch from
  *ask* to *over-provision* — union `candidates` when the detector already ranked them; (c)
  both. The operator's stated policy ("if in doubt, over-provision") points at (b) as the
  behavioural default with (a) as the accuracy improvement.
  Source: operator paste of a live prompt, corroborated against `_cmd_domain_detect.py`,
  `standards/skill-domains.md`, and a marshall-steward-wide grep.

- **OBSERVED (CORRECTED 2026-09-02) — the ambiguous-domain prompt is a category error, but the
  ranking came from the AGENT, not the detector.** ⛔ This entry originally claimed the
  detector produced the four ranked candidates with their reasons. That was wrong, and the
  correction relocates the fix. Read at `_cmd_domain_detect.py` § the zero-match branch: on a
  zero narrative match the detector emits `[{'domain': d, 'matched_aliases': []} for d in
  offerable]` — every offerable domain, **no ranking and no reasons**. The per-option prose in
  the pasted prompt ("JUnit 5 / Vert.x test-support code under api-sheriff/src/test/** plus
  Maven build invocation") was authored by the executing AGENT. The category error therefore
  stands, but its subject moves: it is not that a well-informed detector asked anyway — it is
  that **the agent's own judgement about domain relevance is real, and the pipeline has
  nowhere to put it.** Confirmed twice over: in the api-sheriff instance that judgement was
  converted into a prompt to the user; in the 2026-09-02 over-provision instance it was
  converted into a log line ("javascript … which this plan does not touch") and discarded. A
  system that can rank candidates that precisely does not need to ask which ones apply — it
  needs a path to act on what it already knows. Worse, the prompt is **unanswerable in the terms it
  offers**: option 4 (`general-dev`) is described as "pick this only if you want the plan to
  avoid loading the Java/CUI standard sets", which asks the user to reason about skill-loading
  mechanics to answer a question about their own code. And the prompt's own preamble leaks
  internal vocabulary at the user — *"Domain detection returned ambiguous (no narrative
  match). Per Step 7 this requires an operator multiSelect"* names a workflow step number and
  a tool-API type to someone who wants a test fixed. This one paste therefore instantiates
  **four** of the epic's six themes at once — an unnecessary gate, a low-context prompt,
  internal vocabulary, and a missing over-provision default — which makes it the epic's
  reference example and a natural acceptance test: *this prompt must not fire.*
  Source: operator paste (first-party plan-marshall output).

- **HYPOTHESIS — output volume is governed by convention rather than by an enforced bound
  outside the dispatch-return path.** `citations-only-return.md` and `agents.md` bound a
  *subagent return* (`display_detail` ≤80 chars, one TOON block), but no equivalent bound
  appears to govern what the main orchestrator context prints to the user between phases. If
  confirmed, "too much output" is an unowned surface needing a new standard rather than
  tightening of an existing one.
  Confirm/refute at `marketplace/bundles/plan-marshall/skills/persona-plan-marshall-agent/standards/agent-behavior-rules.md`
  § the user-interaction / reporting rules — verify-at-outline.

- **OBSERVED — the count-divergence detector's scope guard is one-sided, so it reports a false
  divergence on every `N of M` phrasing.** `resume-summary --slug operator-ux` has now returned
  `count_divergences: [{claim: "10 shipped", narrated: 10, derived: 5}]` on two consecutive
  reads, against an anchor sentence that says **"5 of 10 shipped"** and is correct.
  *Mechanism, read at HEAD, not inferred:* `_COUNT_CLAIM_RE`
  (`marketplace/bundles/plan-marshall/skills/plan-orchestrator/scripts/orchestrator.py:316`)
  captures a 12-character **tail** after the noun, and `_SCOPED_CLAIM_RE` (`:331`) tests only
  that tail for a scoping word (`in|of|for|under|within|across|from`). The guard therefore
  catches a qualifier that FOLLOWS the count — "12 rows `in` WS-01" — and is structurally
  blind to one that PRECEDES it. In "5 `of` 10 shipped" the `of` is to the left of the number,
  so the match survives the guard with tail `": PLAN-01 #13"`, and 10 is compared against the
  epic-wide derivation of 5. `_RATIO_CLAIM_RE` (`:337`) does not cover it either — it matches
  only the literal `R = N of M` form, not the prose form an anchor sentence naturally uses.
  ⛔ **The narrated and derived values are the denominator and numerator of one correct
  sentence being compared to each other**, which is why the report is not merely noisy but
  actively misleading: the two numbers always look like a plausible drift.
  ⛔ **This is the exact failure the guard was written to prevent, and its own docstring names
  it**: *"reporting that as a divergence is the false positive that would teach every reader
  to ignore the detector."* It fires in the one surface whose whole job is telling an operator
  whether the ledger is truthful, and it fires on the most natural way to write progress — so
  the cost is paid on every status read, by the reader least able to dismiss it safely.
  ⚠ I dismissed this as a parsing artifact on the previous read without opening the source.
  That was wrong twice over: it is a real bug, and "artifact" was a conclusion drawn from the
  output shape alone. Recorded on recurrence rather than as a second item.
  *Remedy shape (for the plan that owns it, not decided here):* the guard needs a preceding-
   context test symmetric with its tail test — a count immediately preceded by `of` is a
   denominator, not a claim about the whole population.

- **OBSERVED — `interaction_mode` is persisted but largely unconsumed: the mode-to-behaviour
  mapping exists as documentation, and only the phase-1 ambiguous-domain branch reads the
  knob.** PLAN-09 shipped the scalar, the manage-config surface, the steward menu, and
  `standards/interaction-mode.md`; in-run (TASK-10/11) it wired phase-1-init Step 7
  (basic silent-union / expert fail-closed) because CodeRabbit caught the gap live. No other
  phase or steward workflow consumes the persisted mode — the prompt-volume (PLAN-05) and
  output-volume (PLAN-07) behaviours the mapping names are still unmodulated. *Not staged:*
  the scope (which consumers, in what order) needs operator scoping — the natural companion
  to the WS-07 decompose-vs-close decision. Source: PLAN-09 landing Residue + inbox
  `implement-plan-09-interaction-mode-014.md`.

## Watches

{Mid-flight observations that need monitoring but no immediate action — signals to
re-check at the next landing or session. Retire a watch when it resolves or graduates
into a defect/plan.}

- ~~**PLAN-09 inbox drain pending (2026-09-16).**~~ **RETIRED 2026-09-16 — drained.** 14/14 consumed: 4 promoted (`2026-09-16-17-001`…`-004`), 9 discarded (reasons in Decisions), landing -014 reconciled-duplicate. Consumer-wiring follow-up recorded as Open Defect above.
- **Epic end-of-queue (2026-09-16).** All 10 plans shipped, zero staged; WS-07-persona-loading-structure still undecomposed. Next decision: decompose WS-07 vs close the epic. Retire when decided.
- The orchestrator's own surface has the same disease this epic treats — the
  `parallelization_scope` prompt fired at `init` is exactly the kind of gate the operator is
  complaining about, and the word "epic"/"ledger"/"disjointness" is internal vocabulary.
  Re-check at decompose whether orchestrator-facing UX belongs in scope or is deliberately
  deferred; deciding it is a fork for the operator.

- The domain-prompt defect was observed in **api-sheriff**, a different repository from
  plan-marshall. The fix lands in the marketplace (shared by both), but the *verification*
  needs a project whose config actually reproduces it — plan-marshall's own `skill_domains`
  may or may not. Re-check at decompose which repo the acceptance test runs in.

- ~~Two epics are already active (`multiplattform`, `test-quality`); surfaces not yet
  cross-checked.~~ **RETIRED at decompose.** `corpus cross-check` ran over 2 sibling epics,
  3 live plans and 45 candidates: `source_origin_match_count: 0` (the stronger duplication
  signal — no shared origin pointer anywhere), and the only three sibling-epic file overlaps
  are broad TEST-DIRECTORY entries against `test-quality` (`test/plan-marshall/manage-config/`
  on PLAN-04 and PLAN-06, `test/marketplace/` on PLAN-05). Those are over-declarations on this
  epic's side, not duplicate work — `test-quality` is reducing those suites while this epic
  adds cases to them. No spec is duplicated; nothing is superseded. Re-check at `cleanup`.
- **This epic is accruing finalize-machinery debt faster than it retires it, and none of it is
  operator-UX work.** PLAN-06's run alone reproduced FIVE active lessons with no landed remedy
  (`2026-08-25-09-001`, `-008`, `-009`, `-014`, `2026-09-02-13-005`), each retained by
  lessons-housekeeping the day before as "untouched by this plan. No coverage." — correct at
  the time, and all five reproduced during that same run. Across three landings this epic has
  promoted **19 machinery lessons** while shipping 3 of 10 plans. The plan's own message asked
  whether five simultaneous recurrences is "a scheduling signal for the epic". It is — but the
  right response is a SEPARATE epic for finalize machinery, not folding it here, which would
  turn an operator-UX epic into a maintenance backlog. Trigger to decide: the next landing that
  reproduces a lesson already recurring.

  ⛔ **THE TRIGGER HAS FIRED — twice over, and the decision is now overdue.** PLAN-07's drain
  (2026-09-03) delivered 11 candidate-lessons of which **6 were already in the corpus**, two of
  them filed by the immediately preceding plan in this same epic (`2026-09-03-11-004`,
  `2026-09-03-11-005`) and one — the sourcery false-participation defect — on its **third
  recorded acceptance** across three separate runs. That is precisely "a landing that reproduces
  a lesson already recurring", and it arrived alongside a second instance of `2026-08-25-09-014`.

  Updated figures across FOUR landings: the corpus is now **68 lessons** (up from 63 before this
  drain), this epic has promoted **24 machinery lessons** while shipping 4 of 10 plans, and the
  retirement rate remains **zero** — no plan in this epic, or any other, owns a single one of
  them. Three of this epic's Open Defects are now `phase-6-finalize` defects it will never fix.
  The epic is functioning as the finalize lane's defect inbox, which is the exact outcome this
  watch was opened to prevent.

  ✅ **RESOLVED 2026-09-03 — the operator chose a SEPARATE finalize-machinery epic.** This watch
  is now discharged as far as `operator-ux` is concerned: no finalize-machinery work is folded
  into this epic, and its scope stays operator UX. What transfers to the new epic as decompose
  input: the three `phase-6-finalize` Open Defects recorded above (the merge-to-landing
  detection window, the lessons-pipeline re-filing defect, and `branch-sync-state`'s unreachable
  `remote_absent_landed`), plus the recurring corpus lessons with no owning plan — at minimum
  `2026-08-25-09-012` / `2026-09-02-08-001` (sourcery, three acceptances), `2026-08-25-09-014`
  (`--measured-diff-size`, two instances), `2026-09-03-10-001`, `2026-09-03-11-004` and
  `2026-09-03-11-005`. The new epic is NOT scaffolded yet; that is the next orchestrator action
  after PLAN-10 lands. Recorded as an operator interaction in `logs/decision.log`.
- **Declared-surface honesty is now a measured risk in this epic, not a theoretical one.**
  PLAN-01 realized 3.4x the files it declared. Every remaining spec was authored by the same
  process, so assume comparable under-declaration until a landing disproves it. Practical
  consequence: a `disjoint` verdict here is weaker evidence than it reads. Trigger to
  re-check: each landing's realized-vs-declared ratio, recorded in its landing report.

  **Second data point, and it is WORSE — PLAN-02 under-declared by 78%.** Declared 6 entries
  covering 8 realized files; realized **37** (`git diff --name-only c3a1aacbc ef4bf54b5`). The
  29 undeclared files are dominated by one unstaged deliverable — implementing the accessor in
  all nine domain extensions, 18 files — plus `build.py`, `doc/user/configuration.adoc`,
  `script-shared/.../extension_base.py`, three further `extension-api/` standards, two
  `manage-config/standards/` docs, and three test files. Three landings now measured: PLAN-01
  71%, PLAN-10 declared 4 of 5, PLAN-02 78%. ⛔ **The trend is not improving, and the ratio is
  no longer a warning — it is the epic's normal.** Treat every remaining `disjoint` verdict as
  approximately a coin-flip on files nobody declared.
  ⚠ **This instance had teeth the others did not.** PLAN-02 silently modified
  `extension-api/standards/marshal-json-reference.md` (declared by PLAN-04 **and** PLAN-09) and
  `manage-config/standards/data-model.md` (declared by PLAN-09). The gate never saw either,
  because neither was in PLAN-02's declaration. No collision occurred **only** because PLAN-02
  ran alone with slot 2 deliberately unfilled — had the epic been at its nominal
  `parallelization_scope: 2`, this is the pairing that would have broken. Trigger to re-check:
  the next landing that runs concurrently with anything.

  ⛔ **Fourth data point — PLAN-03 at 67%, and it changes what this Watch is about.** Declared 8
  entries, of which **5 were touched**; realized 15 files, of which **10 were undeclared**
  (`git show --stat 80f0b5a79`). The ratio finally moved down — 71%, 78%, 67% — and that is the
  least interesting thing about it. **The plan's PRIMARY artifact was undeclared while three
  declared files were never opened.** The declaration named `_cmd_domain_detect.py` and its test;
  the plan wrote `_cmd_domain_narrow.py` (347 new lines) and two new test modules.
  `phase-1-init/SKILL.md` was declared and never touched.
  ⛔ **So the failure is no longer only under-coverage; it is MIS-IDENTIFICATION.** A declaration
  that is merely incomplete still points at the right neighbourhood, and a reviewer reading it
  gets a true-but-partial picture. A declaration that names the wrong primary file points
  somewhere the plan never went, and the disjointness gate then compares against a fiction — it
  can produce a false COLLISION as readily as a false clearance. Every remedy discussed so far
  (measure the ratio, widen declarations at fold time) addresses coverage and none addresses this.
  ⚠ Third consecutive hit on the same victim: PLAN-03 modified `manage-config/standards/
  data-model.md`, declared by **PLAN-09**, undeclared by PLAN-03 — after PLAN-02 did the same to
  that file and to `marshal-json-reference.md`. Trigger to re-check: whether any spec's
  declaration names a file the plan's own objective does not require.

  ⭐ **Fifth data point — PLAN-04 at 44%, the FIRST improvement, and the cause is identifiable.**
  Declared 9 entries, **all nine touched**; realized 27, of which 15 are covered. The series is
  71% → 78% → 67% → **44%**. What changed is not the plan's diligence: the 2026-09-06 `cleanup`
  applied an understated-surface correction to this spec before it launched, adding
  `manage-config/standards/data-model.md` and `doc/user/configuration.adoc` — and **both were
  realized**, `configuration.adoc` at +76 lines carrying the whole of deliverable 3. Without the
  correction the plan's largest documentation deliverable would have shipped undeclared. That is
  one measured instance of the cleanup pass paying for itself, and the first evidence in this epic
  that the ratio is movable by an act the orchestrator controls.
  ⛔ **But the same pass got one exclusion WRONG, and it is recorded because the judgement was
  explicit.** `manage-config/standards/api-reference.md` was inspected and deliberately excluded
  with a stated reason — *"its only mention is an analogy for `orchestrator.auto_emit` and states no
  default"*. The plan touched it: `:284` carries `final_merge_without_asking: false` inside a worked
  `step get` example, a defaults-stating site in exactly deliverable 4's sense. The evidence was
  already in hand — an `architecture search --content` for `final_merge_without_asking` had listed
  that file with 2 matches — and a later, narrower grep for the *other* knob returned nothing for
  it, which was allowed to override the broader result. This is `2026-09-02-14-001`'s warning
  (verify by re-searching the literal, not by enumeration) landing on the orchestrator's own act.
  Trigger to re-check: at every future surface correction, query for **each** knob or symbol the
  deliverable names, never one as a proxy for the family.
- **The epic serializes on one file.** 6 of 9 specs declare
  `marketplace/bundles/plan-marshall/skills/manage-config/SKILL.md` (PLAN-01, 02, 03, 04, 06,
  09). With PLAN-01 in flight that single file blocks every dependency-free candidate, so the
  second concurrency slot cannot be filled at all. This is what makes `parallelization_scope: 2`
  mostly inert in practice, and it is a property of how the surfaces were declared rather than
  of the work. Worth re-examining at `cleanup`: several of those six touch that file only to
  update a reference table, which may be separable from the behavioural change. Trigger to
  re-check: the next shortfall where the only blocker is this file.
- **Phase-6 cost figures for this epic are floors, not measurements.** PLAN-05's ledger
  integrity check found only **8 of 20** finalize rows pair with a boundary row, so the
  headline figures it reported (finalize ~52% of 3.9M tokens; self-review loop ~43% of the
  phase-6 dispatch total) are lower bounds over a partially-paired ledger. ⛔ Do not quote
  them as measured shares, and do not size any future plan against them. Re-check when
  `2026-09-02-13-002` (the ledger-pairing lesson) is applied.
- **PLAN-05's deliverable 4 shipped partial and the queue no longer shows it.** The blind-spot
  scope statement covers obligations 3 and 4 but not the structural mirror above. The row is
  `shipped` because the plan shipped; the residue is carried by the Open Defect, not by the
  queue. Trigger to re-check: whichever way the derive/collapse fork resolves.
- ~~The three test-directory overlaps are a merge-ordering hazard against `test-quality`
  PLAN-030.~~ **DOWNGRADED at first `next`.** PLAN-030 is already **landed** (PRs #1261,
  #1270), so its reduction of `test/plan-marshall/manage-config/` is merged rather than
  pending — there is no concurrent writer to race. The residual risk is only that PLAN-04,
  PLAN-06 and PLAN-09 add tests to a directory a landed plan deliberately shrank; the outline
  of each should read PLAN-030's landing record before adding cases there, so the reduction is
  not silently undone. `test-quality` PLAN-110 (`test/marketplace/`, overlapping PLAN-05) is
  still only **staged**, so it is not in flight either — re-check if it launches while PLAN-05
  is running.
