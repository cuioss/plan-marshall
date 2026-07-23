# Lesson Source-Premise Check

Authoritative supplement to `phase-1-init/SKILL.md` Step 4b. Defines the extraction heuristics, verification helpers, the `obsolescence_prompt` return-block shape, and the per-branch resolution contract used to detect stale lesson prescriptions before plan scope is locked.

phase-1-init runs as a dispatched `execution-context` leaf and **cannot** fire `AskUserQuestion` (see [`../../ref-workflow-architecture/standards/agents.md`](../../ref-workflow-architecture/standards/agents.md) § "Leaf cannot fire AskUserQuestion — return a prompt-required envelope"). The leaf only *detects* obsolescence and carries an `obsolescence_prompt` block back on its return TOON; the main-context orchestrator (`plan-marshall/workflow/planning.md` § Action: init) fires the prompt and applies the chosen branch post-init. This document describes both sides.

## Scope

Runs only when the init source is a lesson (`lesson_id` provided). Skipped for `description`, `issue`, and `recipe` sources. The check operates on the lesson body resolved in Step 4 ("From Lesson") and runs before Step 5 writes `request.md`.

## Extraction Heuristics

Apply the following passes to the lesson body in order. Each pass yields zero or more `(reference, kind)` tuples appended to the obsolescence-report working set.

### File paths

Match relative or absolute paths anywhere in the body:

```text
(?:(?<=\s)|(?<=`)|^)((?:[a-zA-Z0-9_.-]+/)*[a-zA-Z0-9_.-]+\.(?:py|md|json|toon|java|js|ts|sh|adoc))\b
```

The directory-segment group uses `*` (zero-or-more) so root-level files match alongside nested paths. Examples that the regex captures: `README.md`, `pom.xml`, `opencode.json`, `package.json` (root-level) as well as `marketplace/bundles/plan-marshall/skills/phase-1-init/SKILL.md` (nested).

Both backtick-fenced (`` `marketplace/bundles/.../SKILL.md` ``) and bare paths qualify. Strip surrounding backticks before recording.

### Function / method / subcommand names

Match identifiers rendered in single backticks:

```text
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

## Obsolescence Prompt Contract

Triggered only when at least one reference is stale. The **leaf does NOT fire `AskUserQuestion`** — it carries an `obsolescence_prompt` block on its Step 12 return TOON listing each stale reference and its evidence plus the three option ids, then continues to Step 5 writing `request.md` with the full lesson body intact:

```toon
obsolescence_prompt:
  stale[N]{reference,evidence}:
    {reference_1},{evidence_1}
    {reference_2},{evidence_2}
  options[3]: [refine, close, residual]
```

The **orchestrator** fires the `AskUserQuestion` from the main context, showing the obsolescence report (`{stale_count} stale / {total_count} total`) and offering exactly three options:

- **refine** — "Refine the lesson into the current code surface": continue plan creation with the obsolescence report attached to `request.md` as a clarifying note.
- **close** — "Close the lesson as already-resolved": delete the lesson and the plan, aborting.
- **residual** — "Proceed with the residual scope only": drop the stale references and continue with the remainder.

Option ids (`refine`, `close`, `residual`) are the contract surface other code may key off. Do not reword them.

## Per-Branch Resolution Contract

The **leaf** emits exactly one decision-log entry with the prefix `(plan-marshall:phase-1-init:source-premise)`, recording only what it *detected* (it does not know the operator's choice — the orchestrator owns the prompt). Use the canonical messages below verbatim — downstream audit tooling pattern-matches on them.

| Leaf outcome | Decision-log message |
|--------------|----------------------|
| All clean | `All N references verified — no obsolescence detected.` |
| Obsolescence detected | `Obsolescence detected (N stale of M total) — surfaced to the orchestrator via obsolescence_prompt.` |

The **orchestrator** applies the operator's chosen branch post-init (the leaf continued init with the full lesson body intact):

### Refine branch (orchestrator)

Compose a markdown section and append it to `request.md` (via the `manage-plan-documents request` append flow) under a `## Pre-flight Reference Verification` heading:

```text
## Pre-flight Reference Verification

The following references cited in the source lesson no longer match the current tree. Treat the lesson as a starting pointer and re-derive scope from observed behavior.

- `{reference_1}` — {evidence_1}
- `{reference_2}` — {evidence_2}
```

### Close-as-resolved branch (orchestrator)

Delete the lesson and the just-created plan, then abort — do not proceed to phase-2-refine:

```bash
python3 .plan/execute-script.py plan-marshall:manage-lessons:manage-lessons remove \
  --lesson-id {lesson_id} --reason "Closed as resolved during phase-1-init premise check"
```

```bash
python3 .plan/execute-script.py plan-marshall:manage-status:manage-status delete-plan \
  --plan-id {plan_id}
```

### Residual-scope branch (orchestrator)

Emit one work-log entry per dropped reference so the audit trail captures the scope reduction:

```bash
python3 .plan/execute-script.py plan-marshall:manage-logging:manage-logging \
  work --plan-id {plan_id} --level INFO \
  --message "[ARTIFACT] (plan-marshall:phase-1-init:source-premise) Dropped stale reference: {reference} ({evidence})"
```

Continue with the residual reference set. The kept references are not logged individually — only drops are recorded, since drops shrink scope and require audit visibility.
