envelope_version=1
sender_type=plan
sender_id=two-producers-one-marker-field-two-encodings
epic=truthful-signals
kind=candidate-lesson
created=2026-08-09T04:57:07Z

component=plan-marshall:manage-findings
category=bug
confidence=high
source_plan=two-producers-one-marker-field-two-encodings
source_pr=1125
suggested_epic=truthful-signals

# manage-findings list renders quarantined raw_input verbatim, including before ingest has run

## Context

`manage-findings` quarantines untrusted external free-text under a `raw_input.{field}`
sub-object so that the top-level record fields stay clean-by-construction. The `ingest`
verb is the containment boundary: it validates each `raw_input` mapping through the
`validate_struct` `finding` schema (additionalProperties:false, per-field `maxLength`
clamping, domain allowlist) and only then promotes clamped values to the top-level
fields. The stated invariant is: *no top-level field is ever populated from an
un-validated `raw_input` value, so the top-level surface the triage pass reads is
clean-by-construction.*

`list` defeats the purpose of that quarantine at the read surface. Its tabular header
for this plan is:

```
findings[11]{hash_id,timestamp,type,title,detail,resolution,resolution_detail,
             promoted,promoted_to,file_path,line,author,kind,
             reviewed_commit_sha,bot_kind,raw_input,body}
```

`raw_input` is emitted as an inline column, verbatim and unclamped, in the same
payload a consumer reads for triage. The quarantine is preserved in the *storage*
model and dropped in the *output* model.

Critically, this happens irrespective of ingest state. Three records in this plan
(`cefd79`, `c8180d`, `7255b6`) render with `body: ""` — the top-level field ingest
would have populated is empty, so ingest did not promote them — while their full
`raw_input` bodies are emitted in the same rows. The un-ingested, un-validated
content reaches the reader anyway, through a different column.

## Root cause

The containment boundary is enforced on the promotion path (`raw_input` → top-level)
but not on the serialization path (`record` → TOON output). `list` serialises whatever
fields the record carries, and `raw_input` is one of them. Nothing in the read verb
distinguishes "field that survived validation" from "field that is quarantined
precisely because it has not."

The consequence is that the LLM triage pass — the reader this quarantine exists to
protect — sees the raw bot/comment body regardless. For this plan the bodies were
benign CodeRabbit markdown, but they are attacker-influenceable content by
construction: PR comment bodies are the canonical untrusted-ingestion surface named
in `plan-marshall:untrusted-ingestion`.

A secondary effect: the payload is large. This plan's `list --type pr-comment` output
was 32.6 KB and had to be spilled to a file, most of it duplicated `raw_input` and
`body` prose.

## Proposed action

- Omit `raw_input` from the default `list` projection. It is an audit field, not a
  read field — the SKILL already describes it as retained "for audit".
- Where the raw value is genuinely needed, put it behind an explicit opt-in
  (`--include-raw-input`) so a caller has to ask for un-validated content, and the
  ask is visible in the invocation.
- If a record's `raw_input` is still un-promoted, say so with a marker
  (`ingest_pending: true`) rather than by silently shipping the raw body. That gives
  the triage pass the one fact it actually needs — *this record has not cleared the
  boundary yet* — without handing it the content.

## Evidence

- first-party: `manage-findings list --plan-id two-producers-one-marker-field-two-encodings
  --type pr-comment` emits `raw_input` and `body` as inline tabular columns
- first-party: records `cefd79`, `c8180d` and `7255b6` render `body: ""` alongside a
  fully-populated `raw_input`, i.e. the value is emitted while still quarantined
- `manage-findings` SKILL.md § "Batched raw_input ingestion (ingest)" — states the
  containment invariant that the read surface does not uphold
- `plan-marshall:untrusted-ingestion` — names GitHub PR/issue comment bodies as an
  untrusted-external-content ingestion surface
- payload size: 32.6 KB for 11 findings, spilled to a tool-results file
