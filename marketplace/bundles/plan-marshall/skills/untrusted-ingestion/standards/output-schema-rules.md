# Output-Schema Rules — The Discipline the Validator Script Enforces

Every candidate struct a reader emits is constrained by a declared output schema. The schema is not advisory and is not self-enforced by reader prose — it is **enforced deterministically by `untrusted-ingestion:validate_struct`** (schema check + length-capping/truncation + domain-allowlist check). This document declares the design rules the schema follows and the field shape per `--schema` selector that the script reads; the script is the single enforcement point.

## Design rules (every schema obeys all four)

1. **`additionalProperties: false`** — the struct may carry only the keys the schema declares. Any extra key is a structural violation; the script returns `status: error` naming the violating field. (Extra keys are a common injection vector — a hijacked reader smuggling instructions into an undeclared field.)
2. **`maxLength` on every string** — every string field has an explicit maximum length. The script clamps (truncates) over-long strings rather than rejecting, and records what it clamped.
3. **`maxItems` on every array** — every array field has an explicit maximum item count. The script clamps over-large arrays to the cap, and records what it clamped.
4. **`pattern` on enum-like / identifier fields** — fields with a fixed vocabulary (confidence tiers, finding severities) or an identifier shape carry a regex `pattern`. A value that does not match the pattern is a structural violation; the script returns `status: error`.

On any structural violation (extra key, wrong type, failed `pattern`) the script returns `status: error` with the violating field. On length/array over-runs the script **clamps** and returns `status: success` with the clamped struct and a record of what was truncated.

## WebFetch domain-allowlist requirement

Beyond the schema, every URL/domain-bearing field is subject to a **deterministic domain-allowlist check** the script performs by reusing `workflow-permission-web` logic — it imports and calls `permission_web.categorize_domain` and `permission_web.check_red_flags` against `domain-lists.json`. A URL is allowlisted iff its host categorizes to `major`, `high_reach`, or `universal` AND trips no red flag. When any URL field's host categorizes to `unknown` or trips a red flag, the script returns `status: error` and the write-capable context must abort. This is a deterministic in-script check — **never reader prose**. The reader does not decide domain trust; the script does.

## Schema selectors and field shapes

The validator script takes a `--schema` selector. Four schemas are declared:

### `--schema research`

Candidate findings from web research (consumed by `research-best-practices.md`).

| Field | Type | Constraint |
|-------|------|------------|
| `findings` | array of objects | `maxItems` |
| `findings[].practice` | string | `maxLength` |
| `findings[].justification` | string | `maxLength` |
| `findings[].confidence` | string | `pattern` (enum: confidence tier) |
| `findings[].references` | array of string (URLs) | `maxItems`; each host domain-allowlist-checked |

### `--schema ci-finding`

A candidate summary of a CI/review finding body (consumed by `workflow-integration-github` and `workflow-integration-sonar`).

| Field | Type | Constraint |
|-------|------|------------|
| `summary` | string | `maxLength` |
| `severity` | string | `pattern` (enum: severity) |
| `file` | string | `maxLength` |
| `line` | integer | type-checked |
| `references` | array of string (URLs) | `maxItems`; each host domain-allowlist-checked |

### `--schema issue-body`

A candidate narrative parsed from an external GitHub issue body (consumed by `phase-2-refine` `source-premise-verification.md`).

| Field | Type | Constraint |
|-------|------|------------|
| `narrative` | string | `maxLength` |
| `references` | array of string (URLs) | `maxItems`; each host domain-allowlist-checked |

### `--schema finding`

The **ledger free-text ingestion** schema, consumed in-process by the batched `manage-findings ingest` pass (`validate_candidate('finding', raw_input)`) — one call per pending finding over its quarantined `raw_input.{field}` sub-object. It declares exactly the untrusted free-text fields a producer may quarantine; `additionalProperties: false` means a `raw_input` field not declared here rejects the whole struct (a fidelity failure the ingestion pass routes to `rejected`), never silently dropping it.

| Field | Type | Constraint |
|-------|------|------------|
| `title` | string | `maxLength` |
| `detail` | string | `maxLength` |
| `body` | string | `maxLength` |
| `message` | string | `maxLength` |
| `summary` | string | `maxLength` |

**Ledger containment invariant.** The `finding` schema IS the ingestion boundary for the findings ledger. A producer files untrusted text under `raw_input.{field}`; the ingestion pass validates it under this schema and promotes only the `status: success` clamped output to the finding's clean top-level field of the same name. `raw_input.*` = un-ingested untrusted quarantine (audit-only); top-level = clean-by-construction. Downstream triage reads the promoted top-level fields ONLY, never `raw_input.*` — statically enforced by the plugin-doctor `triage-reads-top-level-only` rule. See [`../../manage-findings/standards/jsonl-format.md`](../../manage-findings/standards/jsonl-format.md) § "`raw_input` quarantine namespace".

## The single enforcement point

These rules are enforced by `untrusted-ingestion:validate_struct` — the deterministic containment boundary documented in `../SKILL.md` § "Canonical invocations". Surface prose (the research workflow, the CI/review SKILLs, the refine source-premise standard) references this script; it does not re-enforce the schema, the length caps, or the domain check in prose. The exact per-field cap values and enum vocabularies are declared in the script alongside the schema it reads.
