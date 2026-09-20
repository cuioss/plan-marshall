envelope_version=1
sender_type=plan
sender_id=plan-truth-103
epic=truthful-signals
kind=candidate-lesson
created=2026-09-13T12:00:46Z

# A declared-unmeasured aspect drops loud while a bare empty one omits benign

component: plan-marshall:plan-retrospective
category: bug
confidence: medium
source_plan: plan-truth-103
source_aspects: permission_prompt_analysis, compile_report

## Context

`compile-report` partitions non-emitted sections into two states with opposite
meanings:

- `sections_omitted` — BENIGN. The trigger fragment was absent or carried
  nothing renderable, so nothing was lost.
- `sections_dropped` — LOUD. A registered fragment was present and carried
  payload but still did not render. A non-empty `sections_dropped` returns
  `status: warning`, and `plan-retrospective/SKILL.md` forbids treating it as a
  clean pass because "a dropped fragment may have carried a live finding".

On this run the Permission Prompt Analysis fragment was emitted honestly: zero
`prompts[]` rows (none were observable), `status: skipped`,
`declared_unmeasured: true`, and a `findings[]` entry explaining that the
session reduction kept 4 of 1347 turns and that no permission-prompt channel is
instrumented at all — so the zero is a zero over a reduced substrate, not a
whole-session clean negative.

The renderer keys the section **body** on `prompts[]`, which was legitimately
empty, so nothing rendered. But the drop-vs-omit classifier keys on whether the
fragment **carried payload**, and the disclosure counts as payload. Result:
`sections_dropped[1]: Permission Prompt Analysis`, `status: warning`.

## The inverted incentive

Had the same aspect emitted a bare `findings: []` and said nothing about its
coverage, it would have carried no payload and been classified
`sections_omitted` — benign, `status: success`, no warning.

So the run is penalised for disclosing a coverage gap and rewarded for staying
silent about it. That is precisely backwards for a report whose companion probe
(`sections_unattributed_zero`) exists to catch sections that "report
`findings: []` without naming what they checked".

Note the two mechanisms currently disagree with each other:
`sections_unattributed_zero` punishes an unattributed zero, and the
drop-classifier punishes an attributed one.

## Proposed action

Make the classifier read the fragment's own declared state before classifying.
A fragment carrying `status: skipped` with a recognised skip-reason token, or
`declared_unmeasured: true`, has said what it did and did not do — that is a
complete answer, not a lost one. Route it to `sections_omitted`, or better, to a
third reported state (`sections_declared_unmeasured`) that is rendered in the
report so the disclosure survives, and that does not flip the run to `warning`.

The vocabulary already exists: `ZERO_DECLARED_UNMEASURED_STATUSES` in
`scripts/retro_sections.py` is the registry the `sections_unattributed_zero`
probe consults for exactly this distinction. The drop-classifier should consult
the same one.

## Evidence

- `compile-report run` return (twice, on two independent compiles): `status: warning`, `sections_dropped[1]: Permission Prompt Analysis`, `sections_unattributed_zero[0]`
- `work/fragment-permission-prompt-analysis.toon`: `status: skipped`, `declared_unmeasured: true`, `prompts` key absent, one `info` finding naming the reduced substrate (4 of 1347 turns)
- `references/permission-prompt-analysis.md` § TOON Fragment Shape — the section body is specified as `prompts[*]{...}`
- `plan-retrospective/SKILL.md` § Prohibited actions — "Never treat a `compile-report` warning as a clean pass"
- `scripts/retro_sections.py` — `ZERO_DECLARED_UNMEASURED_STATUSES` already encodes the declared-unmeasured vocabulary for the sibling probe
