envelope_version=1
sender_type=plan
sender_id=arm-the-refusal-recovery-that-has-never-run
epic=review-apparatus
kind=candidate-lesson
created=2026-09-07T14:29:13Z

# extract-chat-signal emits a raw multi-line body that forges its own envelope

component: plan-marshall:plan-retrospective
category: bug
confidence: high

## Context

`extract-chat-signal.py run` returns the reduced transcript as `reduced_transcript`, serialized as a **quoted scalar containing raw newlines**. `serialize_toon` quotes but does not escape, so the value's continuation lines land at column zero and `parse_toon` reads them as sibling top-level keys.

Observed verbatim in this run's output — the emitted TOON contains, at column zero:

```
operator-decision: "Your questions have been answered: ..."
user: "status?\""
```

Both parse as phantom top-level keys of the pre-pass envelope.

## Root cause

Identical defect class to findings `ed9ef2` and `4394cf`, which this same plan fixed for `ci pr view` and `ci issue view`. The remedy already exists in-tree: the `BlockScalar` marker this plan added to `ref-toon-format/scripts/toon_parser.py`. This sibling producer was never swept.

The exposure is **higher** here than in the two fixed cases, not lower. The payload is operator-authored free text rather than a PR or issue body, and it is emitted by a script the retrospective consumes automatically. An operator turn containing a line reading `status: blocked` overwrites the pre-pass envelope's own `status` field — a control value forged by content the envelope is merely reporting.

## Proposed action

Emit `reduced_transcript` through the `BlockScalar` marker, exactly as `pr view` and `issue view` now emit `body`. Then sweep for the remaining unmarked producers of multi-line payloads rather than fixing this one site: the two already-fixed sites plus this one make three instances of the same class, which is a population worth enumerating once. A test asserting round-trip *fidelity* (not merely presence) with a matched unmarked negative control is the pattern the `ed9ef2` fix already established in `test_pr_view_body_fidelity.py`.

## Evidence

- aspect: chat_history_analysis — the finding was observed by reading this retrospective's own pre-pass output.
- prior art: qgate finding `ed9ef2` (pr view body absent) and `4394cf` (issue view raw body, same envelope-forgery hazard), both `fixed` in this plan.
- the fix vehicle already exists: `BlockScalar` in `marketplace/bundles/plan-marshall/skills/ref-toon-format/scripts/toon_parser.py`.
- measured in the `4394cf` fix: an unmarked payload yielded `naive status: blocked` and `naive body intact: False`.
