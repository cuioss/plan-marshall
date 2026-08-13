> ⛔ **FIRST INSTRUCTION — do not skip, do not delete, do not move below the title.**
>
> Before reading the rest of this plan and before any other action, load the working contract that
> governs this run:
>
> ```text
> Skill: cloud-plan-lane
> ```
>
> It owns the branch/PR/review-comment cycle, the build gate, the pre-PR verification sub-agent, the
> run report, and the closing self-check. **Nothing in this plan overrides it** — where this plan and
> the contract disagree, the contract wins, and the disagreement is reported.
>
> If the skill cannot be loaded, **stop and report the run blocked**. Do not reconstruct the workflow
> from this file: the parts that matter most — the merge gate, the verification dispatch, the report
> — are not in here.
>
> This block is part of the plan, not part of the template. It survives into every copy.

# The terminal report is one machine-readable emission the inbox drains

**Epic:** truthful-signals
**Branch prefix:** feature

> **Split from plan `300`.** Plan 300 owns **the space** — the banded allocation contract with reserved
> gaps, the resolved same-phase collision, and the compose-time collision check. It reserves the
> terminal slot this plan fills. **This plan owns the emission and the payload:** a dedicated terminal
> step that occupies 300's slot, exists only under an orchestrator, and carries the run's facts as
> machine-readable data the epic inbox can drain. ⛔ **Serialize after 300** — this plan's D1 needs the
> slot 300 created, and its D0 gate confirms that slot exists before anything is built.

## Problem

> **A plan reports its outcome to two audiences over two channels, and the operator channel carries
> truths the inbox channel never sees — because the emission is prose, emitted at the wrong time.**

Plan 300 fixes *where* a terminal step may sit (the ordering space) and *whether* two steps may collide
(the check). It does not fix *what* the terminal step emits or *when* the emission happens. Those are
this plan's:

| End | Symptom |
|---|---|
| **What** | The inbox gets narrative; the operator report gets per-step outcomes, totals, repository state. **They are not the same facts.** |
| **When** | The landing is emitted at `order: 991` — before the run's own token totals (998) and the archive path (1000) exist. **The emission cannot carry facts produced after it.** |

### A. The channel gap is systematic, and it is cross-repository

**Seven findings across two runs existed ONLY in the operator report**: a fourth token total 3.4% from
the others (*the magnitude that gets quoted rather than investigated*); a housekeeping step reporting
`0 removed, 0 promoted, 0 adapted, 180 retained` on a run whose own log declared its input unavailable;
the **runtime** step order rather than the order the merged tree shows; a merge call returning
`merged: true` on an unmerged branch; a total that exposed a three-way disagreement; a split guard never
evaluated; a review-bot withdrawal.

⭐ **Operator, first-party:** *"After the last plans I started again pasting the result and **always** the
result has additional infos."* ⇒ **Not an incident. Every run.**

⭐⭐ **Cross-repository corroboration:** another repository's orchestrator **drained and reconciled
correctly from its inbox** — shipped, landing written, rows stamped, spec archived — **and the paste
still carried three things the inbox lacked**, including a version-cut deadline on two standing public
elements. ⇒ ⛔ **The gap is a property of the CHANNEL, not of drain discipline.**

### B. The emission is not terminal, and prose is not facts

The landing emission sits inside a finalize step at `order: 991`. The run's token totals are produced at
`998` (`record-metrics`), the archive path at `1000` (`archive-plan`). ⭐ **The source says why
`archive-plan` runs last: it moves the plan directory out from under every later reader** — so it must
stay last, and the terminal emission must sit in the slot *before* it that plan 300 reserves.

⭐⭐ **The report renders from prose, not from facts.** The operator report (`output-template.md`)
assembles each finalize step's one-line `display_detail` string; the typed per-step `facts` map that
`manage-status --fact` already records is **discarded at the render boundary.** ⇒ **The emission is a
ROUTING gap, not a modelling problem** — the typed facts already exist; nothing routes them to a
drainable channel.

### C. And the emission is armed on every plan, orchestrated or not

The one place a terminal, machine-readable emission belongs is a run the orchestrator will drain — an
orchestrated plan. A non-orchestrated plan has no epic inbox to write to. ⇒ **The terminal step must be
composed OUT of a non-orchestrated plan, as an observable compose-time decision — never a silent runtime
no-op that leaves a dead step in the manifest.**

⚠ **A second, same-seam defect is recorded, not owned here.** The retrospective unconditionally rebinds
the session it measures, and a later enrichment resolves the session from that rebound value. It is *at*
this seam but is neither this plan's deliverable nor 300's — **record it if a change here touches it,
and leave its fix to a dedicated plan.**

## Goal

The orchestrated terminal report is **one emission, at the end, in the slot plan 300 reserved**, carrying
the run's facts as **machine-readable data** the epic inbox can drain; the step **exists only under an
orchestrator**, decided observably at compose time; and after a drain reports zero, the orchestrator can
**establish that nothing material is outstanding** — so the manual paste stops yielding anything new.

## Deliverables

⚠ **Six deliverables, under the split from plan 300.** ⭐ The emission and its payload are kept in ONE
plan deliberately: **a terminal step emitting prose at the right time, or facts at the wrong time, is the
half-fix this epic keeps shipping.** The space (300) is separable; the emission and the facts it carries
are not.

### D0 — GATE: re-derive the seam against HEAD, and confirm 300's slot exists

**Mutates nothing.** ⛔ **Re-derive every claim — any path or count below is a lead, not an inheritance.**

*Done when:* all of the following are read **by symbol** and recorded in the report:

- **300's slot exists.** The banded allocation contract has landed and reserves an integer slot for a
  terminal step **after the last reporting step and before `archive-plan`**. ⛔ **If 300 has not landed,
  STOP and report blocked — this plan cannot occupy a slot that does not exist.**
- **The typed facts map**, and whether it carries both-direction guards. ⭐ **If it does, D4 is routing,
  not modelling.**
- **What the report renders from.** ⛔ **Verify the report renders from the facts map. If it renders from
  something else (per-step `display_detail` prose is the suspected source), D4's source changes** — the
  routing target is the render site, wherever it actually reads.
- **Whether the plan's source identifier is available at COMPOSE time.** D2 depends on it: if `source_id`
  is available only at runtime, D2's shape changes and observability gets *harder*. ⛔ **Read the composer
  and the detection verb — do not infer from output.**

### Phase 1 — the emission

1. **D1 — A dedicated terminal step, in the slot D0 confirmed.**
   *Done when:* the emission is the **last thing that happens before the archive step**.
   ⛔ **The archive step stays last.** ⚠ **Do NOT relocate the currently-emitting step wholesale** — its
   other work is legitimately mid-band; **only the emission moves.** ⭐ **Separating the two is the
   point**: relocating a whole step past what it needed is how the read-direction defect was created.
2. **D2 — The step exists ONLY under an orchestrator.**
   *Done when:* a non-orchestrated plan composes the step **out**, as an **observable compose-time
   decision** — ⛔ **never a silent runtime no-op.**
   ⭐ **The existing detection verb is the single sanctioned seam.** ⛔ **No second detector, no new
   persisted field** — that skill's contract says so, and a second producer over one field is a defect
   this epic has already shipped a plan for.

### Phase 2 — the payload

3. **D3 — Derive the report↔inbox DELTA, in both directions.**
   *Done when:* the set difference is derived — **and every item is classified MECHANISABLE or
   NARRATIVE-ONLY.**
   ⛔ **The set difference IS the payload specification.**
   ⭐ **The seven known report-only findings are the non-empty control: if the derived delta lacks them,
   D3 is wrong.**
   ⛔ **At least one known item may not be mechanisable at all** — the false-merge report arrived as
   operator narrative, not as a step fact. **Say so rather than forcing it.**
   ⚠ **The archived plans, run reports, and drained messages live under `.plan/` and are absent from this
   clone.** The delta is therefore derived from the report render schema and the inbox envelope schema,
   with the seven findings as the control; ⛔ **the "over three archived plans" empirical sample is not
   reachable here — say so rather than claiming a sample that was not taken.**
4. **D4 — The terminal emission carries the facts, machine-readable.** Consume the existing typed facts
   map.
   *Done when:* the emission carries typed facts, not prose.
   ⭐ **The schema already exists with both-direction guards — this is a ROUTING gap, not a modelling
   problem.** ⛔ **Do not re-narrate facts into prose**; the plan that built that map found precisely
   that prose step records are not facts. ⚠ **Verify the report actually renders from that map**; if it
   renders from something else, D4's source changes.
5. **D5 — A drain-completeness check, and retire the workaround.** After a drain reports zero, the
   orchestrator must be able to establish nothing material is outstanding.
   *Done when:* the check exists, is **verified to FAIL on a pre-fix archived plan** where the delta is
   known non-empty, and the report **states explicitly whether the manual paste is retired — naming any
   residue that is irreducibly narrative and therefore correctly keeps it.**
   ⛔ **A completeness check that passes on a known-incomplete input is the vacuous guard this project
   counts at n≥5.**
   ⭐⭐ **The operator is the oracle: this is done when a paste stops yielding anything new.**

## Out of scope

- **The ordering space, the banded contract, the collision, and the collision check.** ⛔ **Plan 300 owns
  them.** This plan **consumes** 300's reserved terminal slot; it does **not** renumber steps, define
  bands, or add ordering guards. If D0 finds the slot missing, this plan is **blocked on 300**, not
  re-scoped to build the space itself.
- **Fixing the totals' sampling point itself.** A sibling plan owns it. ⭐ **This plan removes the
  *reason* for partiality at the landing**; it does not fix the sampling defect. **Serialize against it.**
- **The retrospective's unconditional session rebind (Problem C).** A same-seam defect owned by neither
  this plan nor 300. ⛔ **Record it if a change here touches the retrospective; do not fix it silently.**
- **Renumbering consumer repositories' declarations** and any change to the merge-gate order — those are
  the space's concern (plan 300), not the emission's.

## Expected surface

- A **new finalize step document** (the terminal emission step) plus the phase-6-finalize SKILL.md
  **Built-in Step Dispatch Table**, and the default-step list
  (`manage-execution-manifest/scripts/_manifest_core.py::DEFAULT_PHASE_6_STEPS`).
- `marketplace/bundles/plan-marshall/skills/manage-execution-manifest/scripts/**` — the compose path that
  composes the terminal step **out** for a non-orchestrated plan (D2), and the extension-api doc where
  `order` / step frontmatter is described for third-party authors.
- `marketplace/bundles/plan-marshall/skills/plan-orchestrator/scripts/orchestrator.py` +
  `scripts/_orchestrator_inbox.py` — the detection verb (`classify_source_id`) and the inbox-write verb
  (D2, D4), and the **analyze workflow** where the drain-completeness check lands (D5).
- `marketplace/bundles/plan-marshall/skills/manage-status/**` — the typed facts map the emission consumes
  (D4).
- `marketplace/bundles/plan-marshall/skills/phase-6-finalize/standards/output-template.md` — the report
  render site (D0/D4: the source the report actually reads).
- `marketplace/bundles/plan-marshall/skills/plan-orchestrator/standards/inbox-envelope.md` — the envelope
  schema a facts-carrying `landing` rides (D4).
- `marketplace/bundles/plan-marshall/skills/extension-api/standards/ext-point-finalize-step.md` — the
  `records_facts` contract and the terminal step's frontmatter (D1/D4).
- `test/plan-marshall/phase-6-finalize/**` and the orchestrator tests (D2, D5).

## Claim labels

| Claim | Label | Confirm/refute artifact |
|---|---|---|
| Plan 300 landed and reserves a terminal slot before `archive-plan` | HYPOTHESIS | ⛔ **D0, and the whole plan turns on it** — the banded contract 300 lands, read at HEAD. If absent, this plan is BLOCKED on 300 |
| The typed facts map exists with both-direction guards | HYPOTHESIS | `manage-status` `--fact` + `ext-point-finalize-step.md` § `records_facts` (∃/∀ directions) — ⭐ **if true, D4 is routing, not modelling** |
| The report renders from per-step prose (`display_detail`), not from the facts map | HYPOTHESIS | `phase-6-finalize/standards/output-template.md` snapshot/emission procedure — ⛔ **if it renders from something else, D4's source changes** |
| The plan's source identifier is available at COMPOSE time | HYPOTHESIS | the composer entry (`manage-execution-manifest` compose) and the detection verb (`_orchestrator_inbox.classify_source_id`) — **D2's shape depends on it** |
| The single sanctioned orchestration detector is the shipped `source_id` classifier | HYPOTHESIS | `_orchestrator_inbox.classify_source_id`, by symbol — ⛔ **no second detector, no new persisted field** |
| Seven findings existed only in the operator report | HYPOTHESIS | ⛔ **run reports under `.plan/`, not reachable here.** ⭐ **But the fact this plan needs — that a paste carried what the inbox did not — is established by the act of pasting**, independently of any technical claim in it |
| The cross-repository corroboration | HYPOTHESIS | ⛔ **second-hand and unverifiable from this checkout.** Same note as above applies |
| At least one control item (the false-merge report) is not mechanisable | HYPOTHESIS | it arrived as operator narrative, not a step fact — ⛔ **say so rather than forcing it into a fact** |

An asserted **absence** is verified exactly as an asserted presence, and is the higher-risk half.
Every count above is a **lead** — re-derive it at the moment of the claim.

## Verification

- ⛔ **D2 must be an OBSERVABLE compose-time decision.** A non-orchestrated compose emits the terminal
  step **out**, visible in the compose result — never a runtime no-op that leaves a dead step in the
  manifest. Verify by composing a non-orchestrated plan and reading that the step is absent *and why*.
- ⛔ **D5 must be SEEN to fail on a known-incomplete input.** A completeness check that only ever passes
  is the vacuous guard this plan exists to stop shipping.
- **D3's delta must include the known control items.** A derived delta that misses the seven report-only
  findings is measuring the wrong thing, however clean it looks.
- **D4's source must be verified by reading the render site**, not assumed: if the report renders from
  `display_detail` prose today, routing facts into the emission changes what the render reads.
- Python, documentation, and test changes are expected, so the build gate takes its full path.

## Notes

- ⛔ **Depends on plan 300.** 300 lands the banded allocation contract (with the reserved terminal slot),
  resolves the same-phase collision, and adds the compose-time collision check. **This plan serializes
  after 300** and consumes its slot. D0 confirms the slot before Phase 1 builds anything.
- ⚠ **A terminal emission IS a termination signal by construction**, which substantially overlaps the
  sibling inbox-protocol work (plan 250 landed the inbox amend/supersede verbs) and reduces the need for
  an amend verb. **Re-evaluate both after this lands.**
- ⚠ **The post-run band contract is owned by another epic** (`code-intelligence-substrate` plan 050): a
  `post_run_review: true` step must sit after the merge gate and declare `mutates_source: false`. The
  terminal emission step is backward-looking and reads post-merge evidence, so it **inherits that band's
  rules** — declare `post_run_review: true` / `mutates_source: false` and cite the band contract; ⛔ **do
  not restate or alter it.**
- ⛔ **Do not go looking for the orchestrator spec, the archived plans, the run reports, the drained
  messages, or the other repository's report.** They live under `.plan/` or outside this repository, and
  are absent from this clone. Everything this plan needs is stated above; where the evidence is
  second-hand, this file says so.
