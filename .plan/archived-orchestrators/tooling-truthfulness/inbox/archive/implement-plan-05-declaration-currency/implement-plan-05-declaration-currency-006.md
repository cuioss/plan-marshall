envelope_version=1
sender_type=plan
sender_id=implement-plan-05-declaration-currency
epic=tooling-truthfulness
kind=candidate-lesson
created=2026-09-13T12:34:30Z

# Candidate lesson: review_completeness flag-shape friction on the barrier path

## Context

Driving the pre-merge review-completeness barrier by hand produced four
argparse rejections: `--measured-diff-size` with an empty value is
rejected (it takes a value, unlike the `nargs='?'` list flags), and
`--participated-bots` requires `bot_kind:evidence_kind` pairs while the
producer's similarly-named fields use different shapes.

## Observation

Flags that share a call but differ in empty-value and shape contracts
invite exactly the misinvocation observed; per-flag contract notes at
the barrier call site would have prevented all four rejections.
