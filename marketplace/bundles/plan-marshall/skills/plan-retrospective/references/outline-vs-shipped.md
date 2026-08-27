# Aspect: Outline vs Shipped

The outline-vs-shipped aspect compares what `phase-3-outline` said it would touch — the per-file component assessments recorded in the plan's assessments store — against what the landing actually touched, the realized footprint resolved through the shared footprint resolver.

Nothing checked that correspondence before. Outline records a per-file judgement, the work proceeds, and the two are never placed side by side. This aspect is that comparison and nothing more.

## Deterministic facts vs LLM judgment

The split the whole skill follows: `check-outline-vs-shipped` produces deterministic, counted facts; this reference is the contract the LLM synthesizes a judgment from. The script computes three set differences and publishes each beside the population it was taken over. It decides nothing about whether a divergence mattered.

## Reports, never gates

⛔ **This aspect emits informational severity only and returns no failing status.** An outline assessment is a planning-time judgement recorded *before* the work happened. Grading a landing against it would convert an honest forecast into a gate, and no failure has been demonstrated for this comparison — only an absence of visibility. The script publishes `gating: report_only` so the report states the rule rather than leaving a reader to infer it from the absence of a failing status.

A finding here is never a criticism of outline's judgement. It is the observation that the judgement and the outcome differ, which has several innocent causes and one bad one — see the three outcomes below.

## Assessments carry no resolution lifecycle

⛔ **Assessments are scope INPUTS, consumed by the decision they informed — not defects awaiting closure.** They carry no `resolution` field, and this aspect neither writes one nor requires one. The store is opened read-only.

This is stated rather than assumed because reading assessments as findings has already produced a false public claim: a consumer counted a missing `resolution` as `pending` across 29 assessment records and reported *"29 findings never resolved"*, which was wrong and had to be retracted. The script publishes `assessment_lifecycle: none` so the absence is legible in the report instead of being re-inferred by the next reader.

## Three distinguishable outcomes — never one divergence count

The three mean different things and only one of them is unambiguously bad. Each is derived from its own set expression, is counted separately, and publishes its own denominator.

| Class | Set expression | What it means |
|-------|----------------|---------------|
| `include_unrealised` | assessed `CERTAIN_INCLUDE`, absent from the footprint | **May** be a silent descope — or a forecast that a later, better-informed decision correctly abandoned. Not a defect on its own. |
| `touched_but_unassessed` | in the footprint, carrying no assessment of any certainty | **Ordinary discovery — the system working.** Execution finds work outline could not foresee; that is expected, not a failure. |
| `exclude_violated` | assessed `CERTAIN_EXCLUDE`, in the footprint anyway | **The one unambiguously bad outcome.** Outline ruled the file out and the work touched it regardless. |

⛔ **Do not collapse them into a single "divergence" figure.** Two of the three are routinely benign; summing them buries the only one that warrants attention under the noise of the two that do not.

`UNCERTAIN` counts as **assessed**. A path outline explicitly judged uncertain was looked at, so touching it is not undeclared discovery and it never appears under `touched_but_unassessed`.

A path carrying both `CERTAIN_INCLUDE` and `CERTAIN_EXCLUDE` — a contradictory outline — is reported under both classes. That is the honest report of the contradiction; silently picking one certainty would hide it.

## Every count carries the population it was taken over

A bare count is inadmissible: `3` means nothing without the set it is `3` of. Each class block publishes `count`, `denominator`, the `population` label naming what the denominator counts, and the `members` themselves.

| Class | `population` | Denominator counts |
|-------|--------------|--------------------|
| `include_unrealised` | `certain_include_assessed_paths` | distinct paths carrying a `CERTAIN_INCLUDE` assessment |
| `touched_but_unassessed` | `realized_footprint_paths` | distinct paths in the realized footprint |
| `exclude_violated` | `certain_exclude_assessed_paths` | distinct paths carrying a `CERTAIN_EXCLUDE` assessment |

Denominators count **paths, not records**: two assessments of one file are one assessed path. `assessments_read` (records parsed) and `assessed_path_count` (distinct paths) are both published, so the difference is visible rather than hidden inside a denominator.

`assessments_store_present` separates *"outline recorded no assessments"* from *"the store could not be opened"*. A plan whose store is absent reports `false` with `assessments_read: 0`; both denominators that depend on assessments are then `0`, and a zero count beside a zero denominator says exactly what happened.

## An unresolvable footprint is `inconclusive`, and the counts are ABSENT

⛔ When no resolver tier answers, `comparison` is `inconclusive` and the `counts` block **is not emitted at all**. Three zeros are not published.

The reason is the one this whole plan turns on: a zero published by a run that compared nothing reads exactly like a zero it measured, and `exclude_violated: 0` is the most reassuring line in the report. Absence of the key forces a consumer to branch on `comparison` rather than to find a false zero. A single informational finding names the reason in the counts' place.

Read `comparison` first. `measured` is the only state in which `counts` exists.

## Cross-plan sizing rule

⛔ **One plan is not a population.** Any threshold, rate, or magnitude stated *about* these facts — "an `exclude_violated` rate above N warrants attention", "typical plans see M unassessed paths" — MUST be derived from a distribution across the reachable archived-plan corpus, never from a single plan's numbers.

The obligation on any such statement:

- **Publish the denominator.** State how many archived plans the distribution was computed from.
- **Name the plans actually reached.** The archived stores are git-ignored, so the reachable corpus is a property of the machine the derivation ran on, not of the repository. A denominator without the named population cannot be checked or reproduced.
- **Declare a floor, and report `unmeasured` below it.** When the reachable population falls below the floor the derivation declares, report the distribution as `unmeasured`. Do **not** state a threshold the corpus cannot substantiate — an under-powered figure is worse than no figure, because it is quoted as though it were one.

The script itself states no threshold and no magnitude; it publishes counts beside their populations and stops. This rule governs everything downstream of it.

## The LLM judgment (the only cognition)

Read the three classes separately and report what each says about **this** plan:

1. **`exclude_violated` first.** Each member is a file outline ruled out that the work touched. Establish which decision overrode the exclusion and whether it was recorded anywhere. A member here is worth a finding on its own; the other two classes usually are not.
2. **`include_unrealised` is a question, not a verdict.** For each member, ask whether the deliverable it belonged to shipped by another route, was consciously descoped, or was quietly dropped. Only the last is a finding, and the fragment cannot tell you which it was.
3. **`touched_but_unassessed` is the expected state.** Report it as scale, not as fault: an unusually large class relative to the footprint suggests outline's survey missed a region, which is an input to the *next* plan's outline, not a defect in this one.
4. **On `comparison: inconclusive`, report the inconclusive outcome itself.** Do not reason about class sizes — none were computed. Never reconstruct a count the script withheld.

## Output fragment

The judgment fragment carries the LLM's reading alongside the script's supporting facts, **using the field names the script emits** — the LLM augments the facts, it does not rename them.

```toon
status: success
aspect: outline-vs-shipped
gating: report_only
assessment_lifecycle: none
assessments_store_present: true | false
assessments_read: N
assessed_path_count: N
footprint_source: diff_file | resolved | unresolved
comparison: measured | inconclusive
footprint_path_count: N          # present ONLY on comparison: measured
counts:                          # present ONLY on comparison: measured
  include_unrealised: { count, denominator, population, members[] }
  touched_but_unassessed: { count, denominator, population, members[] }
  exclude_violated: { count, denominator, population, members[] }
findings[N]{severity,message}    # informational severity only; one per non-empty class
llm_judgement_required: true
```

## Persistence

Run the script and register its fragment under the canonical aspect key:

```bash
python3 .plan/execute-script.py plan-marshall:plan-retrospective:check-outline-vs-shipped \
  run --plan-id {plan_id} --mode {live|archived} --diff-file work/footprint.txt > work/fragment-outline-vs-shipped.toon
python3 .plan/execute-script.py plan-marshall:plan-retrospective:collect-fragments \
  add --plan-id {plan_id} --aspect outline-vs-shipped --fragment-file work/fragment-outline-vs-shipped.toon
```

`--diff-file` is optional and carries the realized footprint one path per line, the same capture the routing-decisions aspect consumes. A relative path resolves against the plan directory first and the cwd second; a supplied path that resolves to nothing **raises** rather than reporting an empty footprint — a could-not-look must not carry a nothing-to-look-at's token. When the flag is absent the footprint is recovered through the shared resolver, and only a still-unresolvable footprint yields `comparison: inconclusive`.
