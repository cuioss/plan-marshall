# Lesson Source-Premise Check

Authoritative supplement to `phase-1-init/SKILL.md` Step 4b. Defines the extraction heuristics, verification helpers, the `AskUserQuestion` shape, and the per-branch persistence contract used to detect stale lesson prescriptions before plan scope is locked.

## Scope

Runs only when the init source is a lesson (`lesson_id` provided). Skipped for `description`, `issue`, and `recipe` sources. The check operates on the lesson body resolved in Step 4 ("From Lesson") and runs before Step 5 writes `request.md`.

## Extraction Heuristics

Apply the following passes to the lesson body in order. Each pass yields zero or more `(reference, kind)` tuples appended to the obsolescence-report working set.

### File paths

Match relative or absolute paths anywhere in the body:

```
(?:(?<=\s)|(?<=`)|^)((?:[a-zA-Z0-9_.-]+/)*[a-zA-Z0-9_.-]+\.(?:py|md|json|toon|java|js|ts|sh|adoc))\b
```

The directory-segment group uses `*` (zero-or-more) so root-level files match alongside nested paths. Examples that the regex captures: `README.md`, `pom.xml`, `opencode.json`, `package.json` (root-level) as well as `marketplace/bundles/plan-marshall/skills/phase-1-init/SKILL.md` (nested).

Both backtick-fenced (`` `marketplace/bundles/.../SKILL.md` ``) and bare paths qualify. Strip surrounding backticks before recording.

### Function / method / subcommand names

Match identifiers rendered in single backticks:

```
`([a-zA-Z_][a-zA-Z0-9_:.-]{2,})`
```

Filter out matches that look like prose (length < 3, contain spaces). Common shapes the heuristic catches: `manage_status transition`, `phase-2-refine`, `summarize-invariants`, `Step 3b`.

### CLI invocation shapes

Match `python3 .plan/execute-script.py {notation} {subcommand}` lines (with or without surrounding backticks or fenced blocks). Capture the `notation` (3-segment colon form) and the immediate `subcommand`. Both segments are independently verified by the [Verification Helpers](#verification-helpers) table below (specifically the "CLI shape (notation + subcommand)" row).

### Anti-pattern signatures

The lesson body sometimes calls out a substring as the wrong shape (e.g., "do not use `cd && git`"). Treat any backtick-quoted span introduced by phrases like "anti-pattern", "do not", "never", "wrong shape" as a literal anti-pattern signature. These are verified by Grep — a match means the anti-pattern still exists in the tree (which is itself stale evidence: the lesson said it should be gone).

## Verification Helpers

For each extracted reference, verify against the live tree:

| Kind | Tool | Stale when |
|------|------|------------|
| File path | `Read` | Path missing OR file is empty |
| Function / pattern name | `Grep` (literal first, regex fallback) | Zero matches in repo |
| CLI shape (notation + subcommand) | Invoke `python3 .plan/execute-script.py {notation} --help` | Subcommand absent from help output |
| Anti-pattern signature | `Grep` (literal) | Zero matches (the lesson's claim that it exists is stale) |

Record each verification as a `(reference, kind, status, evidence)` tuple. `status` is one of `valid` or `stale`. `evidence` is a short string suitable for inclusion in a markdown bullet (e.g., `Read returned ENOENT`, `Grep matched 0 lines`, `--help omits subcommand 'foo'`).

## AskUserQuestion Contract

Triggered only when at least one reference is stale. Show the obsolescence report inline as the question's `details` field, then offer exactly three options:

```
question: "The lesson cites references that no longer match the current tree. How should we proceed?"
details: |
  Obsolescence report:
  - {reference_1} — {evidence_1}
  - {reference_2} — {evidence_2}
  ...
  ({stale_count} stale / {total_count} total)
options:
  - id: refine
    label: "Refine the lesson into the current code surface"
    detail: "Continue plan creation; obsolescence report is attached to request.md as a clarifying note."
  - id: close-as-resolved
    label: "Close the lesson as already-resolved"
    detail: "Delete the lesson via manage-lessons and abort plan creation."
  - id: residual-scope
    label: "Proceed with the residual scope only"
    detail: "Drop the stale references and continue with the remainder."
```

Option ids (`refine`, `close-as-resolved`, `residual-scope`) are the contract surface other code may key off. Do not reword them.

## Per-Branch Persistence Contract

All branches (including the all-clean fast path) MUST emit exactly one decision-log entry with the prefix `(plan-marshall:phase-1-init:source-premise)`. Use the canonical messages below verbatim — downstream audit tooling pattern-matches on them.

| Branch | Decision-log message |
|--------|---------------------|
| All clean | `All N references verified — no obsolescence detected.` |
| Refine | `User chose refine — attaching obsolescence report (N stale of M total) as clarifying note.` |
| Close as resolved | `User chose close-as-resolved — lesson {lesson_id} deleted, aborting plan creation.` |
| Residual scope | `User chose residual-scope — dropping N stale references, continuing with M-N valid references.` |

### Refine branch

Compose a markdown section and append it to the body content Step 5.2 writes into `request.md`:

```
## Pre-flight Reference Verification

The following references cited in the source lesson no longer match the current tree. Treat the lesson as a starting pointer and re-derive scope from observed behavior.

- `{reference_1}` — {evidence_1}
- `{reference_2}` — {evidence_2}
```

No additional script call is needed — the appended section travels into `request.md` via the existing Step 5.2 `Write` flow.

### Close-as-resolved branch

Delete the lesson and abort:

```bash
python3 .plan/execute-script.py plan-marshall:manage-lessons:manage-lessons delete \
  --lesson-id {lesson_id}
```

Return the abort TOON documented in SKILL.md Step 4b.5 — do not proceed to Step 5, do not transition phase, do not create references.

### Residual-scope branch

Emit one work-log entry per dropped reference so the audit trail captures the scope reduction:

```bash
python3 .plan/execute-script.py plan-marshall:manage-logging:manage-logging \
  work --plan-id {plan_id} --level INFO \
  --message "[ARTIFACT] (plan-marshall:phase-1-init:source-premise) Dropped stale reference: {reference} ({evidence})"
```

Continue to Step 5 with the residual reference set. The kept references are not logged individually — only drops are recorded, since drops shrink scope and require audit visibility.
