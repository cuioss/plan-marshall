envelope_version=1
sender_type=plan
sender_id=preference-admissibility-prose-vs-auditor-code
epic=truthful-signals
kind=candidate-lesson
created=2026-09-05T14:10:48Z

component=pm-plugin-development:ext-self-review-plan-marshall
category=improvement
bundle=pm-plugin-development

# The two review instruments split one defect family by WHICH SIDE is wrong, so a clean self-review is not evidence the code is sound

## Rule

The pre-submission self-review and the external review bots do not differ in thoroughness over one
population — they cover **complementary halves of a single defect family**, partitioned by which
side of a prose/code mismatch is the wrong one:

| Instrument | The half it finds | Its convergent remedy |
|---|---|---|
| pre-submission self-review | **the prose over-claims** what the code does | DELETE the prose |
| external review bots | **the code cannot do** what the prose says | FIX the code |

A clean self-review therefore licenses exactly one statement — *no surviving prose over-claim was
surfaced* — and specifically does NOT license *the code behind that prose works*.

## Observation

From this run's `review-retrospective` (PLAN `preference-admissibility-prose-vs-auditor-code`):

- All **12** self-review findings were of the form "the prose over-claims".
- CodeRabbit's **two strongest** findings were of the opposite form — "the code cannot do what the
  prose says":
  - a **documented fallback that is unreachable**;
  - an **empty registry set published as `basis: recognized`** — a verdict over a vacuous
    population.
- Both sat **inside modules the self-review had just swept clean**. This is not a scope gap; the
  files were searched and returned clean.

## The remedy asymmetry is the dangerous half

The self-review's only convergent remedy is **deletion**. So when it is handed a code-side defect,
its available move is to delete the prose that describes the broken code — which makes the mismatch
disappear while leaving the defect in place, and removes the documentation that would have exposed
it later.

That happened here: the self-review converted **one of CodeRabbit's code defects into a prose
deletion, citing its own precedent** from the twelve prose findings before it. The instrument's
prior findings became the justification for mis-dispositioning the one finding of the other kind.

## Why this is stronger than the published `structural_limit`

`ext-point-self-review-surfacing.md` requires an unconditional `structural_limit`, whose scope is
"a defect class the analysis cannot reach however wide the sweep — **the behaviour of the code under
inputs the diff does not contain**".

Both CodeRabbit findings were **statically visible in the diff**: an unreachable fallback and an
empty set published as a recognized basis need no runtime input to see. They are inside the diff and
inside the swept files, and still outside what this instrument finds. The published limit is about
*inputs*; this one is about *direction*, and the two do not overlap.

## How to apply

- **Verdict wording**: `"self-review clean: {N} candidates examined, no check matched"` should not
  be readable as diff assurance. State the direction: no surviving *prose over-claim* was surfaced.
- **`structural_limit`**: add the directional limit alongside the input-based one — this analysis
  finds prose that over-claims, not code that under-delivers.
- **Disposition rule (the load-bearing one)**: a finding of the form "the code cannot do what the
  prose says" MUST NOT be dispositioned by deleting the prose. Deleting the claim resolves the
  mismatch and preserves the defect. Route it to a code fix or escalate it.
- **Precedent guard**: prior findings of the *prose-wrong* kind are not precedent for dispositioning
  a *code-wrong* finding. Check which side is wrong before reaching for the precedent.
- **Sequencing**: do not treat a clean self-review as a reason to weight external review findings
  down. The clean round is evidence about the half the bots do not cover.
