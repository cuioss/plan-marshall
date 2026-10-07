envelope_version=1
sender_type=plan
sender_id=verdict-field-read-and-write-integrity
epic=code-intelligence-substrate
kind=candidate-lesson
created=2026-08-26T19:36:18Z

component=plan-marshall:phase-6-finalize
category=anti-pattern
confidence=high
source_plan=verdict-field-read-and-write-integrity
source_pr=1355

# Clause-deletion fixes at one line re-flag that same line round after round

## Context

Of the 9 self-review findings this plan filed at `6-finalize`, **6 are in one file** and **5 are at two lines of it**:

| Line | Rounds it produced a finding | Findings |
|---|---|---|
| `orchestrate.md:77` | 12:35, 12:56, 13:13 (three) | `3b7ab8`, `3a8bba`, `cb3d67` |
| `orchestrate.md:71` | 12:56, 13:22 (two) | `34fdd0`, `a544e6` |

Five of the seven rounds the loop ran (round count per sibling message -001, corroborated from the session transcript) were spent re-flagging two lines. Each round's fix was recorded as convergent and complete; each was followed by a round that found a new defect at the line just fixed.

The recorded resolutions show the mechanism. They are clause deletions:

- `3b7ab8` → *"Deleted the over-claiming clause 'and names --section-scope as its remedy' from line 77 ... Convergent-by-deletion per the self-seeding rule"*
- `a544e6` → *"Resolved by deleting the trailing clause; the sentence then reads exactly as orchestration-model.md states it."*

And the round-5 finding names the coupling outright: the `:71` defect was *"six lines above the two that 839d106b3 fixed and missed by that commit's sweep"* **and** *"It also contradicted line 77 of the same document as rewritten in 839d106b3."* The previous round's fix is both what the sweep missed and what turned the surviving clause into a contradiction.

## Root cause

Deleting the offending clause makes the sentence stop asserting the specific false thing the round found. It does not re-derive the sentence against the contract it describes, so whatever else that sentence still over-claims survives — and it survives *next to a neighbourhood the fix just rewrote*, which is what makes the next round surface it again. Three successive clause deletions at `:77` each left a sentence that the following round read and refuted on a different clause.

The workflow's class-closure obligation has a stated answer to this, and it did not hold here:

> The class is still closed as a class, because the closing **full-surface confirmation pass** ... runs this same sweep over the whole plan diff before the step may record `done`.

Round 4 filed two members of the unreadable-equals-blocking class and swept for the rest; round 5 found a third, six lines away, in a file round 4 had open. The sweep is bounded to *"every OTHER surfaced candidate of the same candidate list"* — so a sibling line the surfacer did not surface as a candidate is outside the sweep no matter how close it sits or how thoroughly the file was read. The bound is documented and deliberate; what is not documented is that it leaves same-file, same-paragraph siblings unreachable, which is where this class of defect actually clusters.

## Proposed action

Two changes, both cheap, neither of which widens the surface:

1. **Flag a repeat site.** When a round files a finding whose `file` and `line` (within a small window) match a finding a PRIOR round already filed, mark it — `repeat_site: true` on the finding, and surface the count in the step's return. A line on its third finding is not converging, and today nothing says so. This composes with the cumulative-cohort fix in sibling message -007 and reads from the same already-loaded prior-round records.
2. **Make a clause deletion re-derive its sentence.** When a fix's remedy is deletion of a clause from a normative sentence, require the fixer to re-read the whole sentence against the contract source it describes and state that the remaining clauses were checked — not merely that the flagged one is gone. The convergent-by-deletion rule is right about *what to remove*; it is silent about *what is left*, and what is left is what the next round finds.

A third, weaker option worth measuring before adopting: let the class sweep re-read the enclosing paragraph of a filed finding, even where those lines were not surfaced as candidates. This is a genuine widening of the surface-only rule and should not be taken on this plan's evidence alone — but the evidence here is that the surface-only bound and the same-file clustering of this defect class are in direct tension.

## Corroborating instance on a different surface

The same shape appeared in this run's PR-bot triage. Finding `f5704b` (CodeRabbit, MD038 spaces-in-code-span) was fixed at the one flagged site, with the resolution recording: *"the same spaced-span form appears in ~8 other docs this PR does not touch; sweeping those is out of scope for this PR."* Declaring that out of scope was a defensible call for a PR boundary — it is included here only because it is the same one-site-fix-known-cohort pattern reaching the tree through a second, independent channel.

## Evidence

- `qgate-6-finalize.jsonl` — 9 findings; `file_path` tallies: `orchestrate.md` 6, `cleanup.md` 1, `analyze.md` 1 (+1 at `orchestrate.md` under `ambiguous_wording`); line tallies `:77` x3, `:71` x2
- `a544e6` detail, verbatim: *"Third instance of the unreadable-equals-blocking class, six lines above the two that 839d106b3 fixed and missed by that commit's sweep"*
- `3b7ab8` and `a544e6` resolution_detail — both explicitly "deleted the ... clause"
- Landed fix commits, one per round: `2ed10f650`, `544444d93`, `839d106b3`, `851544e12`
- Source: `marketplace/bundles/plan-marshall/skills/phase-6-finalize/workflow/pre-submission-self-review.md` — § "Class-closure obligation", **The bound** and **Consequence of the bound** paragraphs (the surfaced-set restriction and the full-surface-confirmation claim this run refutes)
- `f5704b` resolution_detail — the ~8 unswept sibling docs
