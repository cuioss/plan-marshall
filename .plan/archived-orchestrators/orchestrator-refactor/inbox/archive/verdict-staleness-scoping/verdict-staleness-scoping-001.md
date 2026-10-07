envelope_version=1
sender_type=plan
sender_id=verdict-staleness-scoping
epic=orchestrator-refactor
kind=candidate-lesson
created=2026-09-22T21:28:17Z

# Emit reduced_transcript as BlockScalar in chat extract-signal runtime op

## Metadata

- component: `plan-marshall:platform-runtime`
- category: bug
- confidence: high
- observed_in_plan: verdict-staleness-scoping

## Context

The `plan-retrospective` chat-history aspect (aspect 14) obtains its input by running
`extract-chat-signal.py run --session-id {id}`, which invokes the platform-runtime
`chat extract-signal` operation in a subprocess and parses its stdout with `parse_toon`.
On this plan the runtime reported `reduced_bytes: 273005` while the consumer measured
`reduced_transcript_delivered_bytes: 69` — exactly the byte length of the transcript's
first line. The remaining transcript lines appeared in the output as sibling top-level
keys (`<command-name>/plan-marshall: plan-marshall</command-name>`, `operator-decision: ...`,
`user: ...`), all flush at column 0.

## Root cause

The runtime op serializes `reduced_transcript` as a plain multi-line `str`. `serialize_toon`
quotes but does not escape such a value, so every line after the first lands at column 0 and
`parse_toon` reads it as a new top-level key. `BlockScalar` appears in **no** script under
`platform-runtime/scripts/` — the marking that makes the body round-trip is applied only on
the consumer's own emission (`extract-chat-signal._delivered_transcript`), never on the
producer whose stdout the consumer parses. `chat-history-analysis.md` § "Multi-line
serialization" states the rule "binds PRODUCERS and fragment authors alike" and records that
the consumer half was already fixed once; the producer half was not.

## Proposed action

Mark `reduced_transcript` as `BlockScalar` before handing it to `serialize_toon` in the
platform-runtime `chat extract-signal` emission path (candidate sites:
`platform-runtime/scripts/runtime_base.py`, `platform-runtime/scripts/_chat_signal_reducer.py`,
and the per-target runtimes). Add a round-trip test that asserts
`reduced_bytes == reduced_transcript_delivered_bytes` for a multi-line transcript.

## Evidence

- aspect: chat_history_analysis — `reduced_bytes=273005` vs `reduced_transcript_delivered_bytes=69`; 69 is the exact UTF-8 length of the first transcript line
- aspect: permission_prompt_analysis — the transcript channel delivered no examinable prompt population, so the aspect reported `not_evaluated` rather than a clean zero
- source: `extract-chat-signal.py:128` parses the runtime's stdout with `parse_toon`; `:186` measures the post-parse value
- source: `architecture search --content --pattern BlockScalar --category script` returns 6 files, none under `platform-runtime`
