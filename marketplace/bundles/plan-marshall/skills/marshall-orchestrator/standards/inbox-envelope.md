# Inbox Envelope Schema

The message format of the epic's plan-writable OUTBOX. An executing plan appends structured messages to its governing epic through this channel and through nothing else; the orchestrator drains them. The write-boundary contract that sanctions the channel lives in [`persona-marshall-orchestrator/standards/orchestration-model.md`](../../persona-marshall-orchestrator/standards/orchestration-model.md) § Ledger Write-Boundary — this document owns only the message format and its validation.

## Storage location

```text
.plan/local/orchestrator/{epic}/inbox/{sender_id}-{NNN}.md
```

`inbox/` is created by `orchestrator scaffold` alongside `workstreams/`, `plans/`, `landings/`, and `logs/`. Messages are written ONLY by the `orchestrator inbox write` verb (see [`../SKILL.md`](../SKILL.md) § Canonical invocations), which derives the path from the validated epic slug and `--sender-id` and accepts no caller-supplied output path. There is no argument value that reaches any other path in the epic tree.

## File naming and sequence semantics

| Segment | Rule |
|---------|------|
| `{sender_id}` | The sender's identifier — a plan id for a `plan` sender, an epic slug for an `orchestrator` sender. Kebab-case; validated as a path-safe identifier before use. |
| `{NNN}` | Zero-padded, three-digit-minimum sequence, allocated per sender, starting at `001` and growing past three digits when a sender exceeds 999 messages. |

Sequence allocation is a **claim, not a scan-then-write**: the next free number is proposed by scanning `inbox/`, but the exclusive create (`O_CREAT | O_EXCL`) is the atomic step — a collision advances to the next sequence and retries. A concurrent or re-entered finalize therefore cannot clobber an existing message.

## Message shape

A `key=value` metadata header (the repo's existing `file_ops.parse_markdown_metadata` format), exactly one blank line, then the markdown payload body:

```text
envelope_version=1
sender_type=plan
sender_id=orchestration-inbox-channel
epic=truthful-signals
kind=landing
created=2026-07-26T21:04:11Z

## What landed

...markdown payload...
```

The blank line is the header terminator. A message with no blank line has no payload and is rejected as `empty_payload`.

## Header fields

Every field is required. A message missing any one is rejected as `missing_header_field`.

| Field | Required | Type | Description |
|-------|:--------:|------|-------------|
| `envelope_version` | Yes | integer | Schema version. Currently `1`. Any other value is rejected — never silently accepted. |
| `sender_type` | Yes | enum | `plan` (an executing plan's OUTBOX message) or `orchestrator` (reserved for orchestrator-to-orchestrator messages). |
| `sender_id` | Yes | identifier | The sender's id. MUST match the `{sender_id}` segment of the filename. |
| `epic` | Yes | slug | The epic the message is addressed to. MUST match the tree the message sits in. |
| `kind` | Yes | enum | `landing`, `finding`, or `candidate-lesson` — see the payload contract below. |
| `created` | Yes | ISO-8601 | UTC compose timestamp (`YYYY-MM-DDTHH:MM:SSZ`). |

## Payload contract per kind

The payload is free markdown; the kind tells the orchestrator-side pickup how to consume it. Granularity is **one message per emitted item** — that is what the sequence exists to allocate.

| `kind` | Payload contract |
|--------|------------------|
| `landing` | The plan's landing narrative: what shipped, the PR reference, and any residue the epic should track. Exactly one per orchestrated finalize run, emitted unconditionally — including when the plan produced no lesson-bearing signals. |
| `finding` | One observation the plan surfaced that the epic should know about but that is not itself a lesson. |
| `candidate-lesson` | One proposed lesson body, in the same `key=value` + markdown-body shape the lessons corpus uses, so the orchestrator-side pickup can lift it into `manage-lessons` with zero transcoding. The plan performs no global-vs-epic classification — only the orchestrator holds the cross-plan context that judgement needs. |

## Invariants

- **Append-only.** A sender creates new message files and never edits or deletes an existing one, including its own.
- **One file per message.** A message is never appended to an existing file; each emitted item gets its own sequence.
- **Own-file-only.** A sender writes only files whose `{sender_id}` segment is its own id.
- **One-way.** The plan writes; the orchestrator drains. A plan never reads the ledger to make a decision.

## Validator error codes

The named validation seam is `validate_envelope(text, expected_epic, filename)` in `scripts/_orchestrator_inbox.py`, surfaced as `orchestrator inbox validate`. Checks run in the fixed order below, so a given malformed message always yields the same code.

| Order | `error` | Rejection condition |
|:-----:|---------|---------------------|
| 1 | `missing_header_field` | One or more header fields is absent or empty. |
| 2 | `unknown_envelope_version` | `envelope_version` is not the supported version. |
| 3 | `invalid_sender_type` | `sender_type` is outside the declared enum. |
| 4 | `invalid_kind` | `kind` is outside the declared enum. |
| 5 | `empty_payload` | No payload body follows the header's blank line. |
| 6 | `epic_mismatch` | The `epic` header disagrees with the epic tree the message sits in. Checked only when an expected epic is supplied. |
| 7 | `filename_sender_mismatch` | The filename's `{sender}` segment disagrees with the `sender_id` header. Checked only when a filename is supplied. |

## Forward compatibility

`envelope_version` is **fail-closed**: a message whose version is not the supported one is rejected with `unknown_envelope_version`, never accepted on a best-effort basis. The `sender_type` discriminator carries the extension point for future sender classes, so a new sender needs no version bump. Nothing beyond those two extension points is added speculatively.

## Related

- [`persona-marshall-orchestrator/standards/orchestration-model.md`](../../persona-marshall-orchestrator/standards/orchestration-model.md) — § Ledger Write-Boundary, the contract that sanctions this channel
- [`../SKILL.md`](../SKILL.md) § Canonical invocations — the `inbox write` / `inbox validate` / `inbox detect` argument surfaces
- [`manage-lessons/standards/file-format.md`](../../manage-lessons/standards/file-format.md) — the lesson body shape a `candidate-lesson` payload carries
