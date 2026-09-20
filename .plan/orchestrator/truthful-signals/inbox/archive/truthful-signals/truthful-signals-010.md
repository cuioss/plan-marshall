envelope_version=1
sender_type=orchestrator
sender_id=truthful-signals
epic=truthful-signals
kind=finding
created=2026-09-14T08:10:48Z
revision=3
amended=2026-09-14T09:12:40Z

# Three places where the plan record presents as authoritative while nothing checks it against reality

Filed 2026-09-14 from an operator-directed analysis. Revision 1 added source URLs. Revision 2
inspected the upstream framework itself, added a fifth finding and retracted one claim revisions 0–1
had carried from the article without checking it.

⭐⭐ **Revision 3 is a SPLIT, not a correction.** Operator-chosen on 2026-09-14. This message carried
five findings across two different subjects; findings 4 and 5 were about *measuring the instruction
substrate*, which is the `next-level` epic's subject and not this one's. They have been **absorbed by
`next-level` in full** and are relocated, not deleted — see the pointers below. Findings 1, 2 and 3
are unchanged from revision 2 and are what this message now carries.

⛔ **Nothing was lost in the split and nothing needs re-deriving.** Each relocated finding names the
staged spec that now owns it, and the receiving epic's specs carry the measurements, the corrections
and the prohibitions rather than summarising them.

## Sources

| # | Source | Status |
|---|--------|--------|
| 1 | Peng Qian, *"From OpenSpec to AIDLC: How I Improved My Team's AI Code Quality"*, 2026-09-01 — `https://www.dataleadsfuture.com/from-openspec-to-aidlc-how-i-improved-my-teams-ai-code-quality/` | Fetched. ⛔ **Demoted in revision 2 to framing-only and treated as unreliable about its own subject**: no before/after measurement, benchmark or numeric data anywhere; it misreports the framework it describes and omits the most valuable thing in it. Nothing below rests on it |
| 2 | `https://github.com/awslabs/aidlc-workflows` @ `v1` — MIT-0 | Fetched and inspected in revision 2. ⭐ **Relevant only to the relocated findings** — see the pointers section |

Most of what source #1 complains about, plan-marshall already solves, frequently better — the
orchestrator epic ledger is a stronger version of AIDLC's requirement-parking state file. What
follows is only the residue that did *not* already have an answer here.

## The shape

Three findings, related but separable. ⚠ **The unifying frame is offered, not asserted**: in each one
an artifact — a doc, an approval, a spec — **presents as current and binding while no mechanism checks
that it still is**. Finding 2 is squarely this epic's confident-signal-hides-a-caveat theme. Findings
1 and 3 are the record-diverges-from-reality variant. ⛔ **Do not treat the three as one deliverable
because this section grouped them.**

---

## 1. Doc-consistency is enforced at finalize, and nothing obliges a task to carry its own docs

**Measured.** A case-insensitive sweep for doc-drift language (`doc-contract`, `documentation
drift`, `documentation consistency`, `docs stay in sync`) across
`marketplace/bundles/plan-marshall/skills` matches **four** files:
`phase-6-finalize/workflow/create-pr.md`, `phase-6-finalize/scripts/pr_intent_section.py`,
`persona-plan-orchestrator/standards/orchestration-model.md`, `manage-lessons/SKILL.md`. ⛔ **None
is in `phase-5-execute`.** Every `documentation` occurrence in `phase-5-execute/SKILL.md` and
`standards/operations.md` is about *documentation-only build skips* or a JS jsdoc trigger — not one
is an obligation to update the docs a task's own code change invalidated.

**Why it is a finding and not a preference.** Two recorded costs meet at this placement:

- `doc-contract-divergence` is a **recurring** defect archetype in the WS-10 list — it keeps
  recurring, which is what a late-placed gate produces.
- PLAN-TRUTH-089's finalize gate consumed **81% of a 13.9M-token run**, fired self-review **19×**,
  exhausted **all 17** loop-back iterations, and **27%** of its findings were self-seeded.

⚠ **These two facts are each independently recorded; the claim that the first is *caused by* the
placement is a hypothesis this message does not establish.** What is established is that the only
enforcement point for a per-task property sits inside the most expensive gate in the system.

**Lead, not instruction.** Move the invariant to where the change happens: a per-task obligation at
execute time to update the documentation the task's own footprint invalidated, leaving finalize to
verify rather than to discover. ⚠ The `affected_files` under-recording defect carried out of
PLAN-CIS-001 bears directly on this — a per-task doc obligation derived from `affected_files` would
inherit that under-scoping. Reconcile before scoping.

---

## 2. Approval inferred from absence of objection

**Already partly settled here, which is why it is worth generalising.** PLAN-PR-025B **reported a
CodeRabbit review that never ran** — `count_stored: 0` was read as "reviewed and clean" — and it was
caught only post-merge. PLAN-PR-046 (#1477, `77cb2e251`) fixed that one instance by gating
CodeRabbit clean-review credit behind a **marker**.

Source #1 independently arrives at the same shape from the opposite direction, and states it more
generally than the fix does: an **advance** token is a separate artifact from a **review** token,
produced by a different actor, and the workflow proceeds only on the *presence* of the advance
token — never on the absence of an objection.

**The open question, which is the actual deliverable.** #1477 fixed one gate. ⛔ **Whether any other
gate in the finalize chain still infers advance from absence-of-objection has NOT been enumerated,
and this message does not claim it has.** `phase-6-finalize/standards/` holds 23 standards and
`workflow/` holds 5; the population was not swept. Per this epic's own derive-completeness rule,
that enumeration — not a spot-check — is the work.

---

## 3. Operator decisions made during execute do not reach the spec

**Recorded.** PLAN-TRUTH-035 carried "3 operator decisions SUPERSEDED the spec". The plan's opening
intent *is* captured — `phase-1-init/templates/request.md` exists, and
`plan-retrospective/references/request-result-alignment.md` checks result against request. ⛔ **But
the mid-flight `AskUserQuestion` answers that redefine the intent have no documented durable
destination.**

The consequence here is sharper than in source #1, because plan-marshall *does* run a
request-result alignment check — and a check that compares the result against a request the operator
already superseded reports a divergence that is not one, or misses one that is.

⭐ **Upstream has a mechanism for exactly this, and it is cheap.** AIDLC writes every clarifying
question and answer to `{phase}-questions.md`, and appends each stage's operator input, the model's
response and the stage summary to a single **append-only, never-edited** `audit.md`. The
append-only-never-edited property is the load-bearing part: it is what makes the superseding
decision recoverable rather than overwritten. A `golden-aidlc-docs/audit.md` is part of that repo's
evaluation fixture set, so the format is concrete and inspectable.

**Lead.** An append-only decision log per plan, written at the moment an operator answer changes the
contract, and read by request-result alignment as an amendment to the request. ⚠ Cheap and
non-destructive, but ⛔ **the claim that no such destination exists today is from a targeted search,
not an exhaustive one** — verify against `manage-plan-documents` before scoping.

---

## Relocated to `next-level` — pointers, not summaries

⛔ **Read these at their destination.** They are reproduced nowhere, deliberately: a restatement here
would be a second copy that drifts from the specs that now own them.

| Was | Subject | Now owned by |
|-----|---------|--------------|
| Finding 4 | A prescriptive testing standard whose own stated precondition has never been satisfied — property-based testing documented in two skills while the library it names appears in no source file, no test file and no dependency declaration. The **vacuous-authority** archetype inside the testing standards. Carries the revision-2 correction: an independent team converged on our scoping discriminator, so **deletion is refuted** | `.plan/local/orchestrator/next-level/plans/PLAN-07-pbt-standard-liveness.md` |
| Finding 5 | A working multi-model evaluation harness for a markdown instruction corpus, as prior art for the gating deliverable `truthful-signals-009` said it could not design — the three-role executor/simulator/scorer separation, the capability-tier model spread, cross-model consistency and token consumption as named metrics, and the infra-failure gate partition this repository arrived at independently | `.plan/local/orchestrator/next-level/plans/PLAN-04-cross-model-eval-signal.md` |

⭐ Finding 4's source-tree half was **re-derived** at absorption rather than carried on trust:
`architecture search --content` for `from hypothesis|import hypothesis|@given` returns 6 hits across
3 files, **all markdown docs**, zero source and zero test, over `files_scanned: 5462` with clean
coverage.

⛔ Finding 5's four named flaws-not-to-copy — self-grading at the default configuration, a trend gate
that is not a bar, corpus-under-test drift, and unsized cost — are carried into PLAN-04 as a **named
section**, not as a footnote. So is its most important limitation: **not one result from that harness
was read**, so it establishes that the mechanism is buildable and nothing at all about whether any
instruction change helps or harms any model.

⛔ The revision-2 tension between an upstream team *adding* scaffolding after an overconfidence
failure and Anthropic's guidance to *dial it back* is also absorbed, as an epic-level Non-Goal in
`next-level`: convergence is corroboration, never authority, and an outside document with no data is
not cited as evidence for a direction — in either direction. It was never evidence here and it is not
evidence there.

Companion message `truthful-signals-009` — the corpus-calibration finding this epic also carried — was
**superseded whole** by `next-level-001.md` in the same operation. It remains resolvable through
`inbox validate` with its body preserved byte-for-byte.

## What this message does NOT establish

- **No causal claim.** Finding 1 pairs two recorded costs; it does not prove the placement causes
  the recurrence. Finding 2 names one confirmed instance and an un-enumerated population.
- **No population was derived for finding 2.** The finalize gate surface was not swept. Any plan
  must derive it rather than sample it.
- **Nothing from source #1 is carried as fact**, and revision 2 demonstrated why: the one claim
  revisions 0–1 did carry from it was false.
- **AIDLC's workflow design is still not endorsed.** Its dynamic-workflow and requirement-parking
  mechanisms remain **weaker** than the orchestrator ledger already in place. Only the `audit.md`
  append-only property (finding 3) is recommended as prior art on this side of the split.
- **Finding 3's gap is from a targeted search**, not an exhaustive enumeration of plan-document
  destinations.
- **The split is not a judgement that findings 4 and 5 were wrong to file here.** They were filed
  before `next-level` existed. The split is a routing correction made possible by a destination that
  did not previously exist.
