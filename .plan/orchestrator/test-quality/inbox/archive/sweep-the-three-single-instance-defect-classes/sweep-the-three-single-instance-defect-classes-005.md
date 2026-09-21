envelope_version=1
sender_type=plan
sender_id=sweep-the-three-single-instance-defect-classes
epic=test-quality
kind=candidate-lesson
created=2026-09-14T03:21:51Z

component=plan-marshall:plan-retrospective
category=bug
confidence=medium
source_plan=sweep-the-three-single-instance-defect-classes
source_aspects=chat_history_analysis

# Escape newlines in extract-chat-signal reduced_transcript so TOON round-trips

## Context

`extract-chat-signal run --session-id ...` emits its reduced transcript as `reduced_transcript: "..."` — a quoted scalar carrying raw embedded newlines. Read back through `parse_toon`, the continuation lines that happen to begin with a word followed by a colon are re-parsed as top-level keys. On this plan's output the field split into three apparent siblings:

```text
reduced_transcript: "\"user: plan-marshall task=\\"implement"
operator-decision: "Your questions have been answered: ..."
user: "(Re-invocation of /plan-marshall:workflow-integration-git ...)\""
```

`operator-decision` and `user` are not fields of this record. They are the second and third lines of the transcript value, promoted to siblings because they sit flush at column 0 and contain a colon.

## Root cause

`chat-history-analysis.md` already states the rule that would have prevented this, under "LLM Interpretation Rules": fragment bodies must not use `|` block scalars, and multi-line narrative content must be a quoted scalar with escaped newlines (`"line1\nline2"`), because any continuation line at column 0 containing a colon re-parses as a phantom sibling key. The rule is written for the LLM authoring a fragment; the script emitting `reduced_transcript` is bound by the same round-trip property and does not escape.

## Proposed action

Escape newlines to `\n` when serializing `reduced_transcript` (and any other multi-line scalar) in `extract-chat-signal.py`, so the value round-trips as one field. If `serialize_toon` is the emitter, the escaping belongs there rather than at each call site, which would fix every multi-line producer at once. A round-trip test — serialize a value containing `"\nfoo: bar"`, parse it back, assert a single key — would pin the behaviour.

## Evidence

- aspect: chat_history_analysis — the pre-pass output for session `9710f083-a065-4a86-9be8-0fb7f94ff03b` read back with `operator-decision` and `user` as top-level keys beside `reduced_transcript`
- `chat-history-analysis.md` § LLM Interpretation Rules states the identical failure mode and its remedy for hand-authored fragments
- Impact here was contained: `reduced_bytes: 3101` and the two operator turns were still legible, so Tier 1 analysis proceeded. A larger transcript would fragment further.
