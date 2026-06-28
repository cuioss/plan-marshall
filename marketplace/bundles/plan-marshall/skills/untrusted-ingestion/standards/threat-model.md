# Threat Model — Prompt Injection via Untrusted External Content

The plan-marshall workflow routinely ingests bytes the project does not author and cannot trust: web pages fetched during research, GitHub issue/PR/comment bodies fetched during CI/review surfaces, and Sonar issue messages fetched during issue triage. Any of these can carry attacker-controlled text crafted to subvert a write-capable LLM context — a prompt-injection payload embedded in a comment body, an issue description, or a fetched page.

## What "untrusted" means

A byte stream is **untrusted** when its content is authored outside the project's trust boundary and reaches an LLM context that can write, edit, execute, or load skills. The danger is not the bytes themselves but the path from raw external text to a write-capable context: an injection payload that reads as instructions ("ignore previous instructions and …") can hijack a context that has `Write`, `Edit`, `Bash`, or `Skill` in its tool surface.

## Surfaces in scope

| Surface | Untrusted source | Fetcher |
|---------|------------------|---------|
| Web research | Web pages returned by `WebFetch`/`WebSearch` | `research-best-practices.md` workflow |
| GitHub CI/review | Issue/PR/comment bodies (the finding `detail` field) | `workflow-integration-github` (`github_ops.py`) |
| Sonar CI/review | Issue `message`/description text | `workflow-integration-sonar` (`sonar.py`) |
| Plan source ingestion | External GitHub issue body used as request narrative | `phase-2-refine` (`source-premise-verification.md`) |

The script-deterministic fetchers (`github_ops.py`, `sonar.py`) are **not** the containment boundary — they fetch raw bytes and are single-responsibility by design. Containment is applied at the LLM-orchestration layer, after fetch, before any write-capable consumption.

## The reader/orchestrator/writer isolation boundary

```
   UNTRUSTED EXTERNAL BYTES
        │
        ▼
 ┌─────────────────────────────────────────────────────┐
 │  READER   execution-context-reader-{level}           │
 │  tools: WebSearch, WebFetch, Read, Grep              │
 │  semantic extraction ONLY → CANDIDATE struct         │
 │  (NO write/edit/execute/skill — cannot act on bytes) │
 └─────────────────────────────────────────────────────┘
        │  candidate STRUCT (untrusted until validated)
        ▼
 ┌─────────────────────────────────────────────────────┐
 │  VALIDATOR SCRIPT   untrusted-ingestion:validate_struct │
 │  THE containment boundary (deterministic)            │
 │  schema enforce + length-cap/truncate + domain check │
 └─────────────────────────────────────────────────────┘
        │  ONLY a script-validated, clamped STRUCT
        ▼
 ┌─────────────────────────────────────────────────────┐
 │  ORCHESTRATOR / WRITER   execution-context-{level}   │
 │  write-capable; consumes ONLY the validated struct   │
 └─────────────────────────────────────────────────────┘
```

Three properties make this an actual containment boundary rather than a hopeful convention:

1. **The reader cannot act on the project.** Its tool surface (`WebSearch, WebFetch, Read, Grep`) has no write, edit, execute, or skill-loading capability — so an injection payload that successfully hijacks the reader cannot mutate the project, run commands, or load skills. It is NOT tool-free, however: it retains `WebFetch` (domain-allowlisted) and `WebSearch`, so a hijacked reader could still issue outbound fetches within the allowlist or shape a (malformed) candidate struct. The containment property is therefore the absence of *write/edit/execute/skill* capability, not the absence of all tools — the residual fetch surface is bounded by the WebFetch domain allowlist, not eliminated.
2. **The candidate struct is untrusted until the script validates it.** Even a faithful reader is not the security guarantee. The deterministic `untrusted-ingestion:validate_struct` script — not reader prose, not reader good-behaviour — enforces the output schema, length-caps/truncates, and performs the domain-allowlist check. See `reader-contract.md` and `output-schema-rules.md`.
3. **The writer consumes only the validated struct.** The write-capable orchestrator/writer never sees the raw bytes and never consumes an unvalidated candidate. It branches on the script's `status: success|error` and aborts on `error`.

## Why the script, not the reader, is the boundary

Restricting the reader's tool surface bounds the blast radius of a hijack, but it does not by itself guarantee the struct the writer consumes is well-formed and in-policy. A reader that has been injection-hijacked could emit a candidate struct with oversized fields, extra keys, or URLs pointing at attacker-controlled hosts. The deterministic validator script is what rejects or clamps such a struct — it reads the declared schema (`additionalProperties:false` + `maxLength` + `maxItems` + `pattern`), truncates over-long strings and over-large arrays, and checks every URL host against the WebFetch allowlist by reusing `workflow-permission-web` domain logic. The security property is: **the write-capable context consumes only a struct that a deterministic script certified, so safety does not depend on the reader behaving.**
