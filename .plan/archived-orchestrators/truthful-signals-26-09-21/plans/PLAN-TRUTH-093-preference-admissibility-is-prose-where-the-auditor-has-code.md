> ⛔⛔ **READ BEFORE EMITTING — two standing preconditions applied at the 2026-08-22 ingestion.**
>
> **1. Every gap id in this plan is a SNAPSHOT, not live state.** The `gaps.md` files this plan was
> authored from were written by the epic audit at PR #1298 (2026-08-18). Plans 500 (#1320), 510
> (#1309) and 520 (#1317) landed afterwards and closed **90 of the corpus's 283 gaps**, and #1326
> closed one more incidentally. **Re-ground every gap this plan claims to close, at HEAD, before
> implementing it** — and treat a "closed" gap as a lead too: four closures are PARTIAL (`190/G6`
> is closed for its documentation and OPEN for its code path).
>
> **2. No archived-run-report deliverables.** This plan's Expected surface names no
> `doc/plans/**/report-01.md`, so RULING 1 leaves its scope unchanged.

# The preference-admissibility gate is prose on the surface that needs it most

**Epic:** truthful-signals
**Branch prefix:** fix

## Problem

Preference learning treats a recurring operator disposition as evidence about what the operator
wants. For that to mean anything, the findings it counts must come from someone whose opinion is
evidence — a recognized external reviewer — and not from the pipeline's own posted comments. A
`pr-comment` finding the pipeline authored, counted as a preference, is the pipeline learning from its
own echo: a self-reinforcing artifact that grows with chattiness rather than with judgement.

The rule that prevents this is the **authorship-admissibility gate**, stated in
`marketplace/bundles/plan-marshall/skills/phase-6-finalize/standards/disposition-to-hint-routing.md`
§ "(e) Authorship admissibility". Two surfaces must apply it before counting a recurrence, and they
apply it in two different ways:

- The **cross-plan auditor** applies it structurally, in code: `_preference_admissible` in
  `.claude/skills/audit-archived-plan-retrospectives/scripts/audit.py`, validating each archived
  `bot_kind` against a registry-derived set resolved once per corpus walk.
- The **per-plan emitter** applies it as **prose an LLM is asked to follow**. Its standard,
  `phase-6-finalize/standards/finalize-step-preference-emitter.md`, instructs the dispatched agent to
  exclude findings whose `bot_kind` is missing or unrecognized. There is no backing script, and no
  test binds the instruction to a result.

The routing standard is explicit that the prose *is* the implementation: *"the emitter is an
LLM-executed prose contract, and this paragraph IS its implementation."* That is the defect this
epic exists to close — a gate that reports a clean signal because nothing examined the population,
rather than because the population was examined and found clean.

**The write-time check does not cover the gap, and must not be changed to.**
`add_finding` in `marketplace/bundles/plan-marshall/skills/manage-findings/scripts/_findings_core.py`
guards with `if bot_kind and bot_kind not in BOT_KINDS`, so a finding whose `bot_kind` is **absent**
is accepted. That is deliberate and correct: an absent `bot_kind` is the honest recorded state for an
unattributed human comment *and* for the pipeline's own posted comments, both of which must remain
ingestible as findings. Rejecting them at write time would discard legitimate records. The gate
therefore has to hold at aggregation, which is precisely where one of the two surfaces has no code.

**Provenance.** Raised by CodeRabbit against PR #1309 (the run of plan `510`), verified there against
the two implementations, and dispositioned as out of scope for that plan — its touch on the routing
standard was a single stale statement, and closing this properly means creating a component that does
not exist. The finding is recorded in that PR's review thread on
`disposition-to-hint-routing.md` and in `510`'s run report. It belongs to no other staged plan in this
epic; **re-derive that** (see D1).

## Goal

The authorship-admissibility rule is enforced by one implementation that both consuming surfaces
reach, and a test demonstrates that a `pr-comment` finding with no `bot_kind` and one with an
unrecognized `bot_kind` are both excluded from a preference recurrence — with the exclusion having
been **seen to fail** against an implementation that omits it.

## Deliverables

### D1 — Derive the current state of both surfaces, or HALT

The plan's scope rests on three premises. Derive each and **report the result before implementing
anything**; if any fails, stop and report rather than proceeding on the assumption.

1. **The emitter has no backing script.** Asserted absence — the highest-risk claim shape, so verify
   it as you would a presence. Artifact, git-reachable:
   `ls marketplace/bundles/plan-marshall/skills/phase-6-finalize/standards/` and the emitter
   standard's own text. If a script now exists, this plan's premise is gone: report and HALT.
2. **The auditor's predicate is where this plan says it is.** `_preference_admissible` and the
   registry resolver it calls, in the audit script named above. If either has moved or been
   generalized already, report what is there now and HALT rather than duplicating it.
3. **`add_finding`'s guard still admits a missing `bot_kind`.** Read the predicate. If it has been
   narrowed to reject absent values, the ingestion of human and pipeline comments has already changed
   and this plan's problem statement is stale: report and HALT.

**Done when:** all three are derived, each with the command that derived it, and the report states
whether the plan proceeds. A count or a file list stated here is a **lead** — re-derive it at the
moment you use it; the clone may not match the tree this plan was authored against.

### D2 — One implementation of the rule, reachable by both surfaces

Move the admissibility predicate to a surface both consumers can reach, and have the auditor call it
rather than carry its own copy. The auditor is project-local (`.claude/skills/`) while the emitter is
a bundle standard, so the shared home must be in the bundle — a consumer project of plan-marshall
gets the emitter without the auditor.

Keep the auditor's current behaviour exactly, including its degraded branch when the registry cannot
be loaded. This deliverable moves the rule; it does not re-decide it.

**Done when:** one function is the rule, the auditor delegates to it, and the auditor's existing tests
pass unchanged. A behavioural difference discovered while moving it is **reported, not resolved** —
see § Out of scope.

### D3 — Make the emitter's gate executable

Give the emitter a way to apply the rule that does not depend on an agent following prose. The shape
is a judgement call the run must make from what it finds — a filter verb on the findings surface, or a
predicate the emitter's dispatch invokes — and the plan does not prescribe it, because the right
answer depends on what D1 finds.

What the plan does prescribe: **the emitter's standard must stop being the implementation.** After
this deliverable, the paragraph that currently says the prose "IS its implementation" names the
executable path instead and describes the rule rather than enacting it.

**Done when:** a test demonstrates that a `pr-comment` finding with (a) no `bot_kind` and (b) an
unrecognized `bot_kind` are both excluded from a preference recurrence by executable means, and the
test has been **seen RED** against an implementation with the filter removed. Record the mutation, the
failing test id, and the emitted failure message — quoted from the run, not from the test source.

### D4 — State what the write-time check does and does not guarantee

`add_finding`'s guard is easy to mistake for the admissibility gate; the routing standard already
carries a corrected statement of this from PR #1309. Verify that statement still matches the code, and
make sure the emitter standard and `manage-findings`' own documentation do not contradict it.

**Done when:** no document claims write-time validation enforces admissibility, and the one place that
describes the guard states both what it rejects (a non-empty unrecognized value) and what it admits (an
absent one), with the reason absence is legitimate.

## Out of scope

Each exclusion carries its reason, because with no operator watching the written boundary is the only
thing that stops mid-run drift.

- **Changing `add_finding` to reject a missing `bot_kind`.** It would discard legitimate
  `pr-comment` findings — unattributed human comments and the pipeline's own — that must stay
  ingestible. This is a contract change to a shared write path, and a cloud run may not self-approve
  one. If the run concludes it is nonetheless right, it **records a proposal** and ships nothing.
- **Re-deciding the admissibility rule itself** — which identities count as recognized, whether an
  unattributed human comment should be evidence. The rule is settled in the routing standard; this
  plan changes where it is enforced, not what it says. A disagreement is recorded as a proposal.
- **Converting the preference emitter from a prose-dispatched step into a fully scripted one.** D3
  needs its *gate* to be executable, not its whole body. Rewriting the step is a much larger change
  whose verification would couple to the dispatch machinery.
- **The cross-plan auditor's other detectors.** They share a file with `_preference_admissible` and
  nothing else; touching them would widen the diff for no gain and collide with plans that own them.

**DA — add a durability admissibility gate; count recurrence over DISTINCT findings.** *(folded 2026-08-23 from PR #1330 / L10 — CORROBORATED first-party)*
`finalize-step-preference-emitter` found `(python, test_failure, accepted)` at recurrence **18**. It
cleared `preference_min_recurrence=2` AND the `(d)` attribution gate (`python` is a concrete module,
not the `default` bucket), so **by the letter it was promotable** — and the hint it would have written
into `enriched.json` reads *"the project favours / tolerates ... `test_failure` is accepted in
`python`"*, surfacing through `get-module-context` into every future outline's `## Architecture Hints`.
Promoting it would have taught the repository to tolerate red tests.
Two independent reasons the recurrence was not preference evidence:
- **Environmental, then remedied.** The 18 acceptances were `build-npm` tests shelling out to a real
  `npm` binary absent from the machine (`npm --version` -> exit 127). The operator installed npm mid-run
  and the suite went green at 21,675. The disposition described a transient machine state.
- **One decision, re-filed.** The 18 are **9 distinct tests observed twice** (once by `module-tests`,
  once by `coverage`). Recurrence counted re-observations of ONE triage judgement as 18 independent ones,
  so the count that cleared the threshold was itself inflated.
**Why the existing gates miss it, confirmed at HEAD:** `disposition-to-hint-routing.md` carries exactly
two admissibility gates — `(d) Attribution` (line 79) and `(e) Authorship admissibility` (line 110).
**Both ask WHO AUTHORED the finding; neither asks whether the disposition still describes a standing
preference at promotion time.**
**Remedy:** add a third gate — provisionally *"(f) Durability admissibility"* — on two signals already
available without new plumbing: (1) **remediation within the run** (a finding whose class was later
resolved green by the same plan; the change ledger and build results both record the transition), and
(2) **re-observation collapse** — count recurrence over DISTINCT findings using the existing
`content_discriminator` dedup key.
⭐ **Signal 2 is the cheaper and more general fix and is worth doing regardless: an inflated recurrence
count corrupts the threshold for EVERY tuple, not just this one.**
⚠ The step was recorded `done` with `no patterns promoted` and the withholding reasoned in the decision
log — so the emitter's governing sentence ("Generalize, do not transcribe: the hint names the durable
preference the recurrence implies") did the work. **That is prose, and it depends on the running agent
reading it and choosing to withhold against a threshold that said promote.** This spec's whole premise.

## Expected Surface

A file changed that is not here is collateral and must be explained in the run report.

- `marketplace/bundles/plan-marshall/skills/manage-findings/` — the shared predicate's likely home
  (D2), and possibly the executable path for D3.
- `.claude/skills/audit-archived-plan-retrospectives/scripts/audit.py` — the auditor delegating to
  the shared predicate (D2).
- `marketplace/bundles/plan-marshall/skills/phase-6-finalize/standards/finalize-step-preference-emitter.md`
  — the emitter's gate stops being prose (D3).
- `marketplace/bundles/plan-marshall/skills/phase-6-finalize/standards/disposition-to-hint-routing.md`
  — the paragraph that currently declares itself the implementation (D3), and the write-time statement
  (D4).
- A test module for the D3 demonstration, under `test/plan-marshall/`.

## Claim Labels

- **OBSERVED** — the emitter's admissibility instruction is prose with no backing script.
  *Artifact:* `finalize-step-preference-emitter.md` and a listing of its directory. Asserted absence:
  verify as a presence (D1.1).
  - verdict: corroborated | checked_at: 31bed3e76 | by: truthful-signals/cleanup | rescoped: n/a | evidence: Confirmed: finalize-step-preference-emitter.md exists as a standard, and phase-6-finalize/scripts/ contains NO preference-emitter script. The asserted absence was verified as a presence check over the directory, as the claim itself required
- **OBSERVED** — `_preference_admissible` exists in the auditor and validates against a
  registry-derived set. *Artifact:* the audit script.
  - verdict: corroborated | checked_at: 31bed3e76 | by: truthful-signals/cleanup | rescoped: n/a | evidence: _preference_admissible is defined at .claude/skills/audit-archived-plan-retrospectives/scripts/audit.py:2291 and used at :2358
- **OBSERVED** — `add_finding` admits a missing `bot_kind`. *Artifact:* the predicate in
  `_findings_core.py`.
  - verdict: corroborated | checked_at: 31bed3e76 | by: truthful-signals/cleanup | rescoped: n/a | evidence: Confirmed and it is a vacuous guard in the strict sense: _findings_core.py:238 declares bot_kind: str | None = None, and the only validation is :258 'if bot_kind and bot_kind not in BOT_KINDS'. A MISSING bot_kind short-circuits the guard entirely, so add_finding admits it
- **OBSERVED** — the routing standard declares its own prose to be the emitter's implementation.
  *Artifact:* `disposition-to-hint-routing.md` § (e).
  - verdict: corroborated | checked_at: 31bed3e76 | by: truthful-signals/cleanup | rescoped: n/a | evidence: disposition-to-hint-routing.md:154-155 states verbatim: 'the emitter is an LLM-executed prose contract, and this paragraph IS its implementation'
- **HYPOTHESIS** — no other staged plan in this epic covers this gap. *Confirm/refute:*
  `grep -rln "preference-emitter\|add_finding\|bot_kind" doc/plans/truthful-signals/*.md` over the
  un-executed plan files, reading each hit to see whether it covers *enforcement* or only mentions the
  step. This plan was authored on that grep returning only order-comment and documentation mentions;
  **re-derive it** — a plan added since would make this one a duplicate, and the right action then is
  to report and HALT.
  - verdict: unverifiable | checked_at: 31bed3e76 | by: truthful-signals/cleanup | rescoped: n/a | evidence: The claim's own confirm/refute recipe greps doc/plans/truthful-signals/*.md, but that tree is the cloud-lane plan directory and is not the staged spec corpus. The correct population is .plan/local/orchestrator/truthful-signals/plans/, and corpus cross-check reports no source-origin duplicate for -093. The claim as written names the wrong population, so it cannot be settled on its own terms

## Verification

Beyond each deliverable's own *done when*:

1. **The red-first demonstration (D3).** The report carries the mutation applied, the test id that
   failed, the failure message **as emitted**, and confirmation that the target was restored byte-for-
   byte. A guard whose red was not observed is reported as not done. Snapshot the target's bytes to a
   path outside the repository and restore in a `finally`; never `git checkout`/`restore`/`stash`,
   which would discard unstaged work.
2. **Cold read (D3, D4).** These deliverables are text whose value is what a later reader does with
   them. Dispatch the verification sub-agent with an *interpretation* brief, not a conformance one:
   give it the rewritten routing paragraph with no other context and ask — *"A `pr-comment` finding
   has no `bot_kind`. Was it rejected when it was written, and may it seed a preference recurrence?"*
   A correct reading says it was accepted at write time and is excluded at aggregation. Record the
   answer verbatim; a wrong reading is a wording failure however complete the text looks.
3. **The auditor is unchanged in behaviour (D2).** Its existing tests pass without modification. If a
   test had to change, that is a behavioural difference — report it rather than absorbing it.
4. **Population re-derivation at the point of claim.** Every count the report states is re-derived at
   the moment it is written, with the command shown. No number is carried across from this plan file.

## Notes

- **`.plan/` is git-ignored and absent from the clone.** Nothing in this plan asks the run to open a
  `.plan/` path. The findings store lives there at runtime, but every claim above is settled from
  tracked source; if a source document names a `.plan/` path, that is context for a local run and not
  an instruction here.
- **Why this is not a documentation fix.** The routing standard is already accurate about the rule
  after PR #1309 corrected its write-time claim. The remaining defect is that one of the two surfaces
  enforces the rule with prose. Rewording the prose again would leave the gate exactly as unenforced.
- **The two surfaces are asymmetric on purpose, and that is the finding.** The auditor reads archived
  JSONL directly, so it re-validates against the live registry; the emitter runs inside a plan and was
  assumed to be able to follow instructions. The asymmetry is not that one is stricter — it is that
  only one of them can be shown to work.

## Folded from PLAN-TRUTH-074's drain (2026-08-22)

### F1 — a live emitter run produced a hint naming a module that no longer exists (from inbox `-009`)

**First-party evidence for this plan's subject, from a real run.**
`default:finalize-step-preference-emitter` (order 992) filed one owed `architecture enrich` hint on
PLAN-TRUTH-074:

| Field | Value |
|---|---|
| `--module` | `plan-marshall:marshall-orchestrator` — ⛔ **stale, see below** |
| enrich verb | `insight` |
| hint text | *the project treats improvement findings as a standing consideration in the orchestrator module* |

⛔ **CORROBORATED STALE by the orchestrator at HEAD `31211a99b`.** `architecture find --pattern
"*orchestrator*"` returns **82** paths and **not one** under `marshall-orchestrator`; the live skill
is `plan-orchestrator`, and the rename shipped as PLAN-TRUTH-015 / PR #1162 (a verified pure token
rename). An `architecture enrich --module plan-marshall:marshall-orchestrator` call would target a
module that does not exist and the hint would be **dead on arrival** — silently, since a
non-resolving module is not distinguishable from a hint nobody acted on.

⇒ **The emitter must resolve `--module` against the live architecture at emission time**, and record
which name it used. This is the same stale-pointer shape the epic files against: a value true when
captured, false when consumed, with nothing in between to notice. It is a second, independent
admissibility axis alongside the authorship gate this plan already owns — *is the module real?* —
and it is exactly as unenforced.

**Two further facts from that run, both worth keeping as controls for D3's executable gate:**

- The gate **worked** where it was implemented. Within-plan recurrence of
  `(plan-marshall:marshall-orchestrator, improvement, taken_into_account)` was **2** against
  `preference_min_recurrence: 2`, and the hint was generalized rather than logged raw, per the
  disposition-to-hint-routing privacy invariant. `taken_into_account` → `insight` per the shared
  contract's disposition table.
- The **attribution gate correctly dropped an unattributed recurrence.** Of 7 dispositioned findings
  (2 `accepted`, 5 `taken_into_account`, 0 `suppressed`), both `accepted` ones were `pr-comment` with
  `bot_kind: coderabbit` — authorship-admissible — but carried an **empty `component`**, so they
  resolved to the `default` bucket and were dropped. ⭐ **That is the correct behaviour and makes a
  good negative control**: an unattributed recurrence is never promoted even when it clears the
  threshold.

**Discharge note.** The owed enrich cannot be discharged by the orchestrator: `architecture enrich`
writes tracked `.plan/project-architecture/**` descriptors, which sit outside the epic's write
boundary. It is carried here so a plan performs it. The emitter made **zero** `manage-lessons add`
and **zero** `architecture enrich` calls on that run, which is correct for a `post_run_review: true`
step — a post-merge enrich write would land tracked source on `main` as an unpushable diff.

## Folded from the PLAN-TRUTH-096 drain (2026-08-24) — finding `5ed45d`

A concrete instance of this spec's subject, and it is the **vacuous-guard archetype** in the
preference path.

Build findings stamp `module` with the **language tag** (`python`) rather than an architecture module.
`finalize-step-preference-emitter`'s attribution gate **only drops the `default` sentinel**, so a
bogus-but-concrete value passes it and would route `architecture enrich --module python` at a module
that does not exist.

⛔ **The gate tests for the sentinel rather than for MEMBERSHIP in the real module set.** That is the
whole defect, and it is exactly why this spec exists: the admissibility rule lives in prose ("drop
unattributed patterns") while the code implements a single-value denylist. A denylist of one cannot
express "attributed to something real."

⭐ The run dropped the tuple **by hand** and reported `0 patterns promoted, 2 skipped` — so the healthy
outcome here was produced by an operator-side correction, not by the gate. A gate whose correct
behaviour depends on someone noticing is not a gate.

⇒ Fold into the deliverable that replaces the prose rule with a set-membership check against the
resolved module set; the sentinel test becomes redundant once membership is the criterion.
⚠ The finding was **`pending` at plan end** and the plan directory has since been archived.
