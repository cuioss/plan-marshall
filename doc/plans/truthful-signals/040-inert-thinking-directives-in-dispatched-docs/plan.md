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

# Inert in-prose thinking directives in dispatched workflow docs

**Epic:** truthful-signals
**Branch prefix:** fix

## Problem

Several dispatched workflow docs contain prose asking the model to adopt a reasoning level — "use
**ultrathink mode** for deep analysis", "use careful step-by-step reasoning". That prose cannot do
what it says. `marketplace/bundles/plan-marshall/agents/execution-context.md` states the contract
outright: **model and effort are NOT prompt-body fields; they are pinned by the variant filename
(`execution-context-{level}.md`) the caller dispatched against.** A doc reached only through such a
dispatch therefore runs at a level already fixed before its first line is read.

So the directive is at best inert, and at worst in tension with the pin — a document instructing a
change it has no power to make, two files away from the contract that says so. This is the **vacuous
guard** archetype: a predicate that can never fire. It is also **doc-contract-divergence**: the doc
and the contract disagree, and nothing detects it.

The sharper half is the second instance. `content-review.md` carries a chain-of-thought scaffold on a
**checklist-following** review task — the case where CoT prompting is argued to pull attention off
the stated constraints. That argument is worth acting on but it is *an argument*, not a measurement;
it is labelled a HYPOTHESIS below and must not be shipped downstream as established.

## Goal

No dispatched workflow doc instructs the model about its own reasoning level, the corpus has been
swept from a **derived population** rather than from a grep someone happened to write, and a
plugin-doctor rule prevents reintroduction without firing on ordinary procedural prose.

## Deliverables

1. **D1 — Fix the confirmed instances.** Remove the reasoning-level and process-narration prose from
   `marketplace/bundles/plan-marshall/skills/plan-marshall/workflow/research-best-practices.md` and
   from `marketplace/bundles/pm-documents/skills/ref-documentation/workflow/content-review.md`.
   **Preserve every surrounding criteria sentence verbatim** — the directive is the target, not the
   guidance around it.
   *Done when:* the reasoning-level directives are gone from both files and a diff review shows no
   criteria prose altered. ⛔ **MUST NOT be gated on D3** — D1 stands alone and ships even if the
   detector work is dropped.
2. **D2 — GATE: derive the dispatch roster, then sweep it.** The candidate file set is **every
   markdown reachable as an `execution-context*` `workflow:` target**, enumerated from
   `test/_shared/_dispatch_roster.py`. Enumerate the roster first, then scan it for the defect class,
   then fix what it finds.
   *Done when:* the roster size and the hit count are reported **as two separate numbers**, and every
   hit is either fixed or recorded with the reason it was left.
   ⛔ **STOP CONDITION — this deliverable may re-scope the plan.** First confirm
   `test/_shared/_dispatch_roster.py` still exposes the roster in a usable shape. **If it does not,
   halt D2 and report that** — do **not** hand-roll a second roster and do **not** substitute a grep.
   A hand-built population is the very thing this deliverable exists to replace.
   ⛔ **The originating grep was a SAMPLE, not an enumeration.** It covered `ultrathink`, "think step
   by step", careful/deeply + reason|think|consider|analyze, "take your time", "before answering".
   **That list is not the population.** D2's output size is unknown at authoring time; this is a
   discovery deliverable.
3. **D3 — A plugin-doctor rule preventing reintroduction.** A **population-derived** detector over
   the same roster — never a hard-coded path list.
   *Done when:* the rule ships with tests **in both directions**, and the detector publishes the
   population size it examined so a zero can never read as coverage.
   ⛔ **THE FALSE-POSITIVE BOUNDARY IS THE HARD PART.** Descriptive prose about workflow
   *sequencing* ("Step-by-step workflow for creating a solution outline") is **not** a violation.
   Only a directive asking the model to adopt a reasoning level, or to narrate a reasoning process,
   is. A detector that fires on procedural prose is a regression, not a win — the negative test cases
   are as load-bearing as the positive ones.

Three deliverables, well under the split presumption.

## Out of scope

- **Any sweep of `CRITICAL` / `NEVER` / `MUST NOT` / `MANDATORY` / `ALWAYS` / `FORBIDDEN` emphasis
  markers.** These guard true invariants — `.plan/` script-only access, one-command-per-Bash,
  executor notation, TOON schema shape — and their corpus distribution is flat rather than
  concentrated, so there is no hotspot to fix. Sweeping them would strip real guards to satisfy a
  pattern match. **Leave them alone.** (The corpus counts that supported this judgement are leads,
  not facts — see Claim labels.)
- **Re-litigating the recipe choice.** `recipe-surgical-fix` was checked against its own fit gate and
  aborts: the change spans three bundles (`plan-marshall`, `pm-documents`,
  `pm-plugin-development`), which fails `cross_module`, and D2's unbounded discovery pass fails
  `too_broad`. Re-deciding this mid-run would spend the run's budget on a settled question.
- **Building a second detector framework.** A sibling plan in this epic (`migration-shims-have-no-
  expiry`) also wants a population-derived plugin-doctor detector over a roster. If both are in
  flight, **co-design one pattern rather than shipping two** — but do not wait on it: note the
  overlap in the report and proceed.

## Expected surface

- `marketplace/bundles/plan-marshall/skills/plan-marshall/workflow/research-best-practices.md` — three
  `ultrathink` directives (D1).
- `marketplace/bundles/pm-documents/skills/ref-documentation/workflow/content-review.md` — the
  restatement and the CoT scaffold (D1).
- `test/_shared/_dispatch_roster.py` — the population source. **Read-only unless D2 must extend it.**
- `marketplace/bundles/pm-plugin-development/**` — the plugin-doctor rule's home and its tests (D3).
- **Open-ended:** whatever additional roster files D2 surfaces. Because the sweep's surface cannot be
  enumerated in advance, treat this plan as **exclusive against anything else editing dispatched
  workflow docs**.

## Claim labels

| Claim | Label | Confirm/refute artifact |
|---|---|---|
| Model and effort are pinned by the dispatched variant filename, not by prompt-body or in-doc prose | OBSERVED | `marketplace/bundles/plan-marshall/agents/execution-context.md` — find the pin sentence **by string, not by line number** |
| `research-best-practices.md` carries three reasoning-level directives ("ultrathink") | OBSERVED | that file — locate by string; the reported line numbers `:9`, `:46`, `:112` are leads only |
| `content-review.md` carries a restatement and a "careful step-by-step reasoning" directive | HYPOTHESIS | that file — **confirm by string before editing**; reported at `:7` and `:177`, not independently verified |
| A CoT scaffold on a checklist-following task actively degrades constraint-following | HYPOTHESIS | none available in-repo — this is an **argument**, not a measurement. Act on it if the string is confirmed, but ⛔ **do not serialize it downstream as established** |
| "24 of 25 corpus hits for step-by-step are legitimate procedural prose" | HYPOTHESIS | re-derive over the roster D2 builds. ⛔ This figure came from a message and was never re-derived; D3's false-positive boundary must be tuned against a **freshly computed** ratio |
| The six emphasis-marker corpus counts under Out of scope | HYPOTHESIS | re-derive if any of them is used to justify a decision; they are quoted to explain a boundary, not to be relied on |
| `test/_shared/_dispatch_roster.py` still exposes the roster in the shape D2 needs | HYPOTHESIS | **D2 itself, which HALTS if it does not** |

An asserted **absence** is verified exactly as an asserted presence, and is the higher-risk half.
Every count above is a **lead** — re-derive it at the moment of the claim.

## Verification

- ⛔ **D3's rule text and D1's edited prose are both text-whose-value-is-what-a-reader-does.** Give
  the Step 6 verification sub-agent a **cold read**: show it (a) three real procedural-prose samples
  from the corpus and (b) the removed directives, with no other context, and have it state which are
  violations. The correct answer is that **none** of the procedural samples is and **all** of the
  directives are. If it flags procedural prose, D3's boundary is wrong however complete the rule
  looks.
- D3's detector must **publish the population size it examined** in its own output. Verify by running
  it and reading that number — a rule that can return "clean" from an empty population is the defect
  archetype this epic is named for.
- Report the roster size and the hit count as **separate** figures. A count of files examined is a
  volume, not a coverage number.
- Python changes are expected (D3 + tests), so the build gate takes its full path. Confirm from git
  evidence rather than assuming.

## Notes

- **Both other plans that touch detector surfaces are worth checking before this one edits
  plugin-doctor**: the migration-shim plan and the self-review-guard plan both work near
  population-derived detectors. If either has landed since this plan was authored, read what it built
  before adding a parallel mechanism.
- The **vacuous guard** archetype this plan closes has recurred at least five times in this project,
  and has more than once been **reintroduced by a fix for it**. D3 is the guard against that; its own
  tests are the guard against D3 becoming another instance.
- ⛔ **Do not go looking for the orchestrator spec, the inbox message, or any landing record.** They
  live under `.plan/`, which is git-ignored and absent from this clone. Everything needed is in this
  file.
