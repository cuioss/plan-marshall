envelope_version=1
sender_type=plan
sender_id=path-attribution-seam
epic=code-intelligence-substrate
kind=candidate-lesson
created=2026-08-01T20:48:33Z

component=plan-marshall:plan-retrospective
category=bug
bundle=plan-marshall

# Four defects in the retrospective's own machinery — and all four fail in the confident direction rather than the absent one

## What happened

Running the retrospective over PLAN-CIS-023 surfaced four independent defects **in the retrospective itself**. They live in four different code paths and need four different fixes, but they share one property worth naming: every one produces a *confident wrong value* rather than an honest absence.

### 1. The declared-affected-files parser counts prose as paths

`check-artifact-consistency` reported `declared: 27`. The structured extractor over the same document — `manage-solution-outline list-deliverables` — yields a **23-file** union across the 7 deliverables. The 4 extras are not paths:

- `"A review-bot finding whose claim is already satisfied in the current tree is dispositioned"`
- `"When adding a new resolvable extension surface, extend the corresponding curated test set —"`
- `"Whole-tree coverage is an orchestrator-tier build (~37min instrumented) that the harness kills, and"`
- `build-maven` (a bare module name)

Three prose sentences and a module name are being counted as file paths, inflating the recall **denominator** by 17%. Two parsers read one document and disagree; the structured one already exists and should be the single source.

### 2. `mis_prune` attributes a posture-cutoff removal to a prune predicate

`check-routing-decisions` reported:

```text
"mis_prune:sonar-roundtrip",fail,no_code_delta,predicate_evaluated,
  sonar-roundtrip skipped as no_code_delta but the realized footprint touched production code
```

`decision.log` says otherwise, verbatim and twice:

```text
[STATUS] lane_resolution — dropped sonar-roundtrip from phase_6.steps
  (execution_profile=standard): effective tier full exceeds the standard posture cutoff
```

`sonar-roundtrip` was never evaluated against `no_code_delta` at all. It was removed by the posture cutoff before any prune predicate ran. The checker re-evaluates a predicate that did not cause the removal, then reports the mismatch as a **mis-prune FAIL** — an accusation of a routing error that did not occur, on a step whose removal was correct and logged.

### 3. `no_signal: false` on a corpus with one human turn

`extract-chat-signal` reduced 982 transcript turns to 5 and reported `no_signal: false`, gating Tier-1 analysis on. Of the 5 retained turns, **4 are machine `<task-notification>` envelopes** for background builds. The only human-authored turn is the launch command.

Worse, a *real* operator turn was dropped. `decision.log` records at 12:41:54Z:

> `Operator answer applied — SVG nine to twelve reconciliation absorbed into deliverable 7`

That answer exists, it mattered (it reshaped deliverable 7), and the reducer discarded it while keeping four build-completion notices. The retention predicate is not selecting for operator authorship, so `no_signal: false` can be satisfied entirely by harness-generated turns.

### 4. The Executive Summary section has no reachable producer

`references/report-structure.md` § 1 specifies the Executive Summary as "a 3-5 sentence narrative that synthesizes all aspects", and `compile-report.build_document` reads it from `fragments['_executive-summary']`. But that key is unreachable through the only producer path a workflow run has:

```text
$ collect-fragments add --aspect _executive-summary --fragment-file ...
status: error
error: internal_error
message: "Reserved aspect key: keys starting with \"_\" are internal metadata"
```

`retro_sections.valid_aspect_keys()` excludes underscore-prefixed keys, and the comment says they "are injected directly by the orchestrator" — but the SKILL workflow documents no injection mechanism, and direct writes into the bundle are prohibited by the `.plan/`-scripts-only rule. Section 1 therefore renders `_No executive summary provided._` on **every** run.

## The unifying rule

**Do X — when a measurement cannot be taken, report the absence with a reason token; never substitute a computed value over missing evidence.** Every one of the four above had a truthful alternative available: `skipped: parser_disagreement`, `skipped: removal_cause_not_predicate`, `no_signal: true`, and a loud "no executive-summary producer registered". Each instead emitted a number or a verdict that reads as measured.

**Do X — when two components parse the same artifact, one of them must be the source and the other must call it.** Defect 1 is a producer/consumer divergence that a single call to `list-deliverables` removes.

**Do X — check the *recorded cause* before re-evaluating a predicate against it.** Defect 2's fix is one field: `removal_cause` is already in the fragment schema and was set to `predicate_evaluated` on a removal whose logged cause was the posture cutoff. Read the cause, and skip the predicate re-evaluation when it does not match.

**Not Y — do not let a reserved-key guard block the only writer of a key the consumer requires.** Defect 4 is a guard that is individually correct (underscore keys are internal) and jointly fatal (nothing else can write it). A reserved key with a consumer and no producer is dead structure.

## Why these belong together

Individually each is small. Together they say something about the retrospective as an instrument: it is the component whose entire job is to report truthfully on a run, and in four separate places it prefers a confident answer to an honest gap. That is the epic's own theme applied to the auditor.
