# PLAN-TRUTH-047: a lesson was retired against a worked example that demonstrates the anti-pattern its own clause forbids

epic: truthful-signals
workstream: WS-01

## Objective

The evidence standard for retiring a lesson is currently **"the rule is codified somewhere"**. It has to
be **"the codification is correct"**, because `PLAN-TRUTH-010`'s run produced a `completely-covered`
retirement justified by a demonstration that **mishandles the very ambiguity cited as its coverage.**

⭐⭐ **A wrong worked example is the highest-leverage defect in the corpus**: it does not merely fail
once, it **propagates into every future retirement decision that cites it.**

## OBSERVED — the sequence, from the plan's own decision log

**13:43:31Z, decision `71fe82`** — housekeeping classifies lesson `2026-07-11-15-001` (*detect-and-warn
inferred a clean pass from absence-of-change, not an affirmative success signal*) as
**`completely-covered`**:

> the rule … is now codified as `error-handling.md` Fail-Closed Classification (d), **whose worked
> contrast covers the succeeded-idempotently vs never-ran ambiguity the lesson names**. No residue
> outside that clause. Disposition **remove**.

**20:04:48Z, decision `ce09fb`**, acting on CodeRabbit comment `c9176b` on PR #1081:

> Clause (d) states absence-of-change is not evidence of success — and then **its GOOD example branches
> on `outcome.applied`, a change flag**, so a successful idempotent no-op routes to `markUnresolved`.
> **The GOOD example demonstrates the anti-pattern its own clause forbids.**

A **second defect of the same class** in the same pass: **clause (f)'s** GOOD-example comment claims a
short readback while the code only compares **list sizes** — the term misnames the mechanism.

## ⛔⛔ Three independent controls sat between the lesson and its retirement. None fired.

1. The **housekeeping classifier** read clause (d) and pronounced it covering.
2. **`pre-submission-self-review` ran five passes** over text this plan authored, at a recorded
   **709,472 tokens**, and did not flag it.
3. **`plugin-doctor quality-gate`** ran clean over the same file.

It was caught by a **free external reviewer, in one pass, after the PR was open.**

⭐ **And the lesson survived only by accident.** `restore-from-plan` was independently broken (see
`PLAN-TRUTH-044`), so the `remove` disposition **could not be applied**. Had the restore worked, a
load-bearing lesson would have been deleted on the strength of a self-contradicting example.

> ⛔⛔ **Safety by unrelated bug is not a control.**

⇒ **This is why `PLAN-TRUTH-044` must not land alone**: repairing the restore path without this plan's
evidence standard converts a latent corpus loss into an actual one.

## ⭐ The class the controls could not reach

Self-review's yield on this run was concentrated in **structural/mechanical** classes. The class it
demonstrably did not reach is **semantic self-contradiction inside prose the same run had just
authored** — precisely the class an independent reader is good at and an author re-reading their own
text is bad at, **however many times they re-read it**. ⚠ **Five passes is not five perspectives.**

## Deliverables

1. **D0 — GATE: sweep every codified worked example against the clause it illustrates.** For each GOOD /
   BAD pair in the promoted standards, state the concrete input on which the example produces the
   clause's correct verdict. ⛔ **Population-derived over the standards tree, not sampled** — two of the
   handful of clauses shipped in one PR were already wrong, so the base rate is **not** low.
   ⭐ **Report the count of contradicting examples found — that number is the evidence the check was
   needed.**
2. **D1 — a `completely-covered` verdict must cite the clause AND name the input.** The verdict must
   state, in one sentence, the concrete input on which the clause's own worked example produces the
   correct result. **If that sentence cannot be written, the verdict is `partially-covered` at best.**
   ⭐ **Load-bearing** — it is the only deliverable that makes the classifier read the example rather
   than the clause's title.
3. **D2 — retirement becomes a two-key operation.** Classification and deletion must not both derive
   from the same read of the same text by the same pass.
4. **D3 — a dedicated worked-example check**, standing: *does the GOOD example actually satisfy the
   clause it illustrates?* ⛔ **A control assertion is required** — the check must be shown to FIRE on
   the live clause-(d) fixture (recoverable from git at the pre-fix commit), or it is a vacuous guard in
   a new place. **Both defects here (clauses (d) and (f)) are this check, absent.**
5. **D4 — apply the three OWED trims.** Each is `partially-covered`: cut the covered half, **keep the
   uncovered half.** ⛔ **The keep-list is normative, not advisory:**

   | Lesson | CUT (covered) | ⛔ KEEP (uncovered) |
   |---|---|---|
   | `2026-07-16-14-001` | axes 2–3 → clauses (b)/(c)/(e) | **axis 1** (a scoping input must be required) and **axis 4** (an exactly-once guard must be evaluated before the classification it suppresses). ⚠ **Clause (a) governs match-table ROW ORDER — a different thing. Do NOT treat it as covering axis 4.** |
   | `2026-06-21-21-001` | the fail-open `None`-wildcard bullet | naive-vs-aware datetime normalization; `gh api --paginate` requires `--slurp` |
   | `2026-07-22-12-003` | rule 1 → clause (e) | rules 2–3: corroborate a routed build's outer envelope against the daemon job log; **an implausible duration is a first-class failure signal** |

   ⚠ **A trim rewrites a body to drop only the covered portion — the operation most likely to lose the
   uncovered half if done carelessly.** The filer deferred these **on cost at the end of a 13-hour run,
   not on judgement**, and explicitly asked for a fresh context. **Honour that: D4 runs first in its
   phase, not last.**
6. **D5 — tests.** (a) The worked-example check fires on the pre-fix clause (d). (b) A verdict lacking
   the D1 sentence cannot be `completely-covered`. (c) Each trimmed lesson still contains its keep-list
   items **verbatim** after the trim.

⚠ Six deliverables, at the bloat threshold. **Split evaluated and declined**: D4 is the concrete instance
D0–D3 generalise, and separating them re-creates exactly the classify-without-apply gap this run hit.
⭐ Rationale recorded per the standing correction that the split decision is made at staging.

## Retirements already APPLIED this run — record as done, do not re-do

| Lesson | Disposition |
|---|---|
| `2026-07-22-16-003` | retired — failure mode eliminated; the stamp is now a conjunction with a build-executing-subcommand allow-list. No residue. |
| `2026-07-11-15-001` | retired — rule promoted to clause (d). ⚠ **First justification was FALSE**; example corrected in-PR before re-applying. |
| `2026-07-07-17-001` | retired — rules 1–2 → clauses (a)/(b); rule 3 residue promoted to `persona-module-tester/standards/testing-coverage.md`. |
| `2026-07-24-13-002` | retired — corrective rule → clause (c); test residue promoted to the same standards file. |
| `2026-07-23-01-002` | ✅ **RETAINED deliberately** (bias-to-retain) — it governs a **gate** whose scope filter excludes items lacking the key it enforces, not a classifier verdict, and the vacuous-guard archetype is an **open recurrence**. ⛔ Do not re-classify. |

## Claim Labels

- **OBSERVED (plan-reported, first-party, quoting its own decision log ids `71fe82` / `ce09fb` and
  CodeRabbit comment `c9176b`)**: both verdicts, the clause-(d) and clause-(f) defects, the three
  non-firing controls, the 709,472-token self-review figure, and the applied/retained dispositions.
- ⚠ **NOT independently re-derived by this orchestrator.** ⭐ Clause (d)'s **corrected** text is on main
  in `ref-code-quality`; the **pre-fix** text is recoverable from the PR #1082 range. **Read both at D0**
  — D3's control assertion needs the pre-fix version as its fixture.
- **HYPOTHESIS**: the two found defects are the complete set of contradicting examples. ⛔ **Assembled
  from one external reviewer's single pass — that is a SAMPLE, not an enumeration.** D0 exists to
  replace it.

## Expected Surface

- **HYPOTHESIS**: `ref-code-quality` — `error-handling.md` Fail-Closed Classification clauses
- **HYPOTHESIS**: `project:finalize-step-lessons-housekeeping` — the classifier and its evidence standard
- **HYPOTHESIS**: `.plan/local/lessons-learned/` — the three trims (D4)

## Dependencies and Sequencing

- ⛔ **PAIRED WITH `PLAN-TRUTH-044` — sequencing is load-bearing, not tidiness.** 044 repairs the restore
  path; this plan supplies the evidence standard that makes a working restore safe. **044 must not land
  first.**
- ⚠ Adjacent to `PLAN-90` (the corpus is written and never read) and `PLAN-TRUTH-014` (landed-residue
  promotion sweep) — **same store. SERIALIZE.**

## Hand-Off Command

```text
/plan-marshall task="implement .plan/local/orchestrator/truthful-signals/plans/PLAN-TRUTH-047-a-retirement-verdict-cited-a-worked-example-that-contradicts-its-own-clause.md"
```

## Write-Boundary

The plan implementing this spec touches only its own repository source and tests, **plus the lessons
corpus under `.plan/local/lessons-learned/` for D4** — which is the plan's declared subject matter, not
an incidental write. It creates and edits NO file under `.plan/local/orchestrator/` other than its own
`inbox/{sender}-{seq}` message. Qualifiers are in
`persona-marshall-orchestrator/standards/orchestration-model.md` § Ledger Write-Boundary.
