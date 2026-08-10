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

# Apply the corpus the same admission control the codebase already gets

**Epic:** code-intelligence-substrate
**Branch prefix:** feature

## Problem

This project enforces strict admission control on what it reads from the **codebase**: structured
queries before search, a content search that returns location and strength but never line bodies, no
unscoped exploration. The **document corpus** — the skills, standards and workflow docs the system
reads to execute at all — has none of it. `Skill:` loads a whole `SKILL.md`; a referenced standard is
read whole; nothing ranks, slices, or bounds any of it.

The mechanism is that no reading path over the corpus was ever built. The discipline itself is
already written down and argued: `doc/concepts/code-intelligence.adoc` § "Location and strength,
never the lines" states that returning line bodies makes response size a function of match density
while returning files makes it a function of file count. **That argument was applied to the codebase
and never to the documents.**

The scale is what makes it worth a plan rather than a cleanup. One component —
`marketplace/bundles/plan-marshall/skills/persona-plan-marshall-agent/` — is a `SKILL.md` on the
order of fifteen kilobytes with roughly a hundred kilobytes of `standards/` behind it, and it is
loaded **unconditionally by every dispatch**. That is one of well over a hundred registered
components. ⛔ **Both of those figures are leads: re-derive them in the clone** (`wc -c` over the
skill directory, and a re-count of registered components) — the tree the run sees is not guaranteed
to be the tree these numbers were taken from.

## Goal

A dispatched leaf can obtain the *section* of a corpus document it actually needs without loading
the whole file, with a coverage contract that distinguishes "the section does not exist" from "the
file could not be read" from "the section is empty" — and the epic's own value case is restated
against what the corpus measurement actually says.

## Deliverables

1. **D0 — GATE: can the residency population be derived in this clone at all?**
   The measurement this plan rests on was taken from archived plan records under a **machine-local,
   git-ignored** path. ⛔ **That path is not present in this clone and must not be searched for** —
   see Claim labels.
   *Done when:* the run has established, from git-reachable evidence alone, either (a) a population
   of instrumented records it can measure, or (b) that no such population is reachable here.
   ⛔ **On (b): HALT. Report the plan blocked on corpus availability and stop.** Do **not** proceed
   to D2 on a single observation, and do **not** substitute a hand-assembled stand-in for the
   measurement — a hand-maintained list is the defect class this epic exists to close, so the
   fallback would reproduce it inside the fix.
2. **D1 — derive the corpus-residency population. Mutates nothing.**
   Establish which documents are read, how often, how many times *within one envelope*, and how much
   of each read document a step actually consumes.
   ⛔ **Report per phase with the population size — do not pool.** The whole finding is that phases
   differ sharply.
   ⛔ **Implement a three-state archived-record read** (`current` / `old-schema` / `pre-migration`):
   the partiality keys were renamed with no compatibility shim, and silently defaulting an
   old-schema record is exactly how a bare rename manufactures a clean verdict.
   *Done when:* per-phase residency and consumption figures exist, each carrying its own population
   size, and old-schema records are reported as old-schema rather than defaulted.
3. **D2 — a section-granular read verb for the corpus.** A dispatched leaf obtains a named section
   of a `SKILL.md` or a `standards/*.md` without loading the file.
   ⛔ **It carries the same coverage contract the existing content reader ships.**
   *Done when:* a leaf retrieves one section without the file, and the three states above are
   separately representable — verified by a negative control for each, not by a positive case alone.
4. **D3 — re-read elimination within an envelope.** A document already resident in a dispatch's
   context is not read again. D1 supplies the magnitude.
   *Done when:* either the elimination ships, **or** D1 shows intra-envelope re-reads are rare and
   the run **records the refutation and drops the deliverable**. Dropping it on evidence is a
   success, not a shortfall.
5. **D4 — restate the epic's value case against the corpus measurement.** If the addressable share
   on the phases that matter is codebase-small versus corpus-large, **say so** in the epic's own
   vision document and re-scope.
   *Done when:* the written value case matches what D1 measured, and an independent cold reader
   (see Verification) reports it read the epic as aimed where D1 says the cost actually is.

Five deliverables with D0 a gate — at the split guard's edge. **Evaluate the split before
implementing**; the natural cut is measurement (D0+D1) then mechanism (D2+D3+D4).

## Out of scope

- **Loading fewer skills, or dropping standards from a profile.** Excluded on principle, not on
  balance: reducing what is examined improves the token number while degrading detection, and this
  project rejects that class of lever outright. In scope is a smaller *slice* of a document that is
  read anyway; out of scope is reading fewer documents.
- **Shortening standards documents to make them cheaper.** Excluded because document quality is not
  the variable — how much of a document enters a context is.
- **Quantifying a token saving.** Excluded because sizing needs the measurement instrument other
  plans in this epic own. The success test here is **binary and structural**: can a dispatched leaf
  obtain the one section it needs without the whole file, yes or no?
- **A second content-search verb.** Excluded because one already shipped and another staged plan
  already carries this prohibition. Extend the existing surface or justify a new home explicitly.

## Expected surface

- **HYPOTHESIS**: `marketplace/bundles/plan-marshall/skills/ref-workflow-architecture/standards/skill-loading.md`
  — the loading contract. Verify at outline.
- **HYPOTHESIS**: the corpus read verb's home — `marketplace/bundles/plan-marshall/skills/manage-architecture/`
  (it already owns content search over the inventory) or a new surface. Decide at outline.
- **HYPOTHESIS**: `doc/concepts/token-management.adoc` § 4 — the skill-driven-guidance claim, which
  today asserts pre-loaded skills *prevent* the exploration loop. They prevent the **codebase** loop
  and are themselves the larger cost. Verify at outline.
- `doc/concepts/code-intelligence.adoc` — the discipline being extended.

## Claim labels

| Claim | Label | Confirm/refute artifact |
|---|---|---|
| The doc-residency share generalises beyond a single observed plan | **HYPOTHESIS — the load-bearing one** | D1. ⚠ This project has already twice recorded a phase-specific figure being read as a whole-corpus one. **Do not build D2 on n=1.** |
| A step's *needed* fraction of a document is materially smaller than the document | **HYPOTHESIS** | D1 must measure **consumption**, not just residency. ⚠ If a step genuinely needs most of what it loads, D2's ceiling is low and the plan re-scopes. This is the honest way this plan returns an unwelcome answer. |
| The corpus admission-control discipline is already argued in writing and was applied only to the codebase | **OBSERVED** | `doc/concepts/code-intelligence.adoc` § "Location and strength, never the lines" — git-reachable, read it. |
| The foundational persona is loaded unconditionally by every dispatch and cannot be named in `skills[]` | **OBSERVED** | The execution-context agent contract under `marketplace/bundles/plan-marshall/skills/` — git-reachable, re-read it rather than trusting this line. |
| The size figures (skill body, standards total, component count) | **LEAD, not a fact** | Re-derive in the clone. A count taken at authoring time is invalidated by any document added or removed since. |
| The originating per-phase measurement | **NOT REACHABLE FROM THIS CLONE** | It lives in a machine-local archived-plan record under the git-ignored `.plan/` tree. ⛔ **Do not go looking for it.** D0 exists precisely because this evidence is absent here. |
| `Skill:` loading is a **platform** mechanism, not this project's | **HYPOTHESIS** | Establish at outline what the harness actually admits when a skill loads — whether progressive disclosure already bounds it to `SKILL.md`, and whether a section-granular read is reachable from inside a dispatched envelope. **If the harness forecloses D2, re-scope to the `standards/*.md` reads that go through `Read`, which this project does own.** |

An asserted **absence** ("no admission control exists over the corpus") is verified exactly as an
asserted presence and is the higher-risk half — confirm it against the loading contract before
building, because an unverified absence produces duplicate work against something that already
exists.

## Verification

- **D0's halt is a real outcome and must be reported as one.** A run that halts at D0 with a clear
  statement of what was unreachable has succeeded at D0; a run that proceeds past it on a
  hand-assembled substitute has failed, whatever else it ships.
- **D2's coverage contract is verified by three negative controls** — a missing section, an
  unreadable file, an empty section — each asserted to produce a *distinct* result. A positive-only
  fixture passes against a broken implementation.
- **D4 carries a cold read.** Its value is entirely what a later reader concludes about where the
  epic is aimed. Dispatch the pre-PR verification sub-agent to read the revised value case **cold**
  and report which reading it took. If it does not land where D1's evidence points, the wording
  failed however complete it looks.
- Full `./pw verify` per the lane contract's build gate.

## Notes

- **This plan can honestly return an unwelcome answer, and that is a feature.** If D1 shows steps
  consume most of what they load, D2's ceiling is low and the plan re-scopes rather than shipping a
  mechanism with nothing behind it. Record that outcome plainly; an understated result is collected
  and picked up again, an overstated one is collected as done.
- **Coordination.** A sibling plan in this epic builds a live protocol client for a dispatched
  envelope aimed at *code*. The same protocol shape is what D2 needs aimed at the **corpus**.
  **Coordinate; do not fork a second client.** A separate editor-facing plan overlaps in subject but
  not in consumer — re-verify at outline that the two are not building one index twice.
- **Ordering.** A WS-04 measurement plan settles the two `unattributed` populations D1's split
  inherits; where a figure is load-bearing, that plan landing first makes this one cheaper. It is
  not a hard dependency.
