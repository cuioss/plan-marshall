---
name: ref-ascii-diagrams
description: Authoring standards for ASCII box diagrams in skill and doc source — box-drawing conventions, right-border alignment, and a deterministic check/fix validator over fenced/literal code blocks in .md and .adoc files
user-invocable: false
mode: knowledge
---

# ASCII Diagrams Skill

Reference standards for authoring ASCII / monospace box diagrams inside fenced
(` ``` `) code blocks of Markdown (`.md`) skill source and literal (`----`) /
fenced blocks of AsciiDoc (`.adoc`) documentation. Covers the box-drawing
character conventions, the right-border column-alignment rule, and the
deterministic `check` / `fix` validator that detects and repairs misaligned
boxes. ASCII box diagrams are the diff-able counterpart to the visual SVGs in
`ref-svg-diagrams`: they live in source that must stay reviewable in a unified
diff, where a rendered image cannot.

## Enforcement

**Execution mode**: Read [`standards/box-conventions.md`](standards/box-conventions.md)
before authoring or editing an ASCII box diagram, hand-author the diagram inside
a code/literal block, then run the validator's `check` mode (Workflow Step 3) to
confirm alignment.

**Prohibited actions:**

- Do not mix box-drawing styles within a single diagram. Use the canonical
  set `┌ ─ ┐ │ └ ┘` only; do not substitute ASCII `+`, `-`, `|` for the
  rounded/heavy variants, and do not mix single- and double-line glyphs.
- Do not hand-pad interior lines by counting columns. Author the content, then
  let `fix` re-pad to a consistent width — manual column counting is the most
  common source of the ragged right borders this skill exists to prevent.
- Do not place a box diagram outside a fenced (` ``` `) or literal (`----`)
  block. The validator only scans inside code/literal blocks; a box in running
  prose is neither validated nor repaired.

**Constraints:**

- Right borders of every line in a box MUST sit in the same column; the top
  (`┌──┐`) and bottom (`└──┘`) rules MUST span the same inner width as the
  widest interior line. The validator's `fix` mode is the canonical way to
  achieve this — see [`standards/box-conventions.md`](standards/box-conventions.md).
- `check` is non-mutating: it reports offending file + line numbers and exits
  with data only. `fix` is mutating and idempotent: a second `fix` pass over an
  already-aligned file changes nothing.
- Legends, flow-lines (a bare `│` connector that is not `│`-bounded on both
  sides), and nested boxes are NOT separately re-ruled — they are interior
  content of the enclosing box. Author them per
  [`standards/box-conventions.md`](standards/box-conventions.md) so the
  heuristic validator does not mistake them for misaligned boxes.

## Exit-code convention for every script call

Every `python3 .plan/execute-script.py` call in this document — of EVERY notation, **not only `manage-*`** — carries the following exit-code contract unless a step explicitly states otherwise. The scope is widened past `manage-*` because this document invokes `ascii_diagrams` — a `manage-*`-scoped convention leaves exactly those calls with no rule at all, which is the swallowed-rejection gap.

- **`exit_code == 0` AND `status: success`**: parse the returned TOON and use the value as the step describes.
- **`exit_code == 0` with a `status` other than `success`, or with no parseable `status` at all**: NOT a usable value — STOP exactly as the `exit_code != 0` disposition below requires, with one difference in what the error TOON carries: on this path the diagnostic is on STDOUT, not stderr. Preserve the stdout **error envelope** as emitted — every field it carries, verbatim — into the returned error TOON; it is the only account of the cause that exists. Copy the whole envelope rather than a fixed field list, because the diagnostic fields vary by verb and `error` is sometimes a generic string whose real cause sits in one of the others. A zero exit is not evidence the operation succeeded; a script MAY print `status: error` and still exit 0. Read `status` FIRST, and never read a **success-payload** field off a non-`success` return. A malformed or truncated stdout carrying **no parseable `status` at all** takes this same path: an unreadable read is not evidence of success, so it fails closed onto STOP rather than falling through to the first clause.
- **`exit_code != 0`**: STOP and return an error TOON to the orchestrator carrying the script's stderr verbatim. Non-zero exits include `argparse_rejection` (exit 2) — silent swallowing of `wrong_parameters` rejections is the prohibited anti-pattern; "log and continue" is equally forbidden.

The middle clause is what the `ci` family makes load-bearing: a `ci` verb reports failure as `status: error` at exit 0 **by design**, so a caller must branch on the payload `status` and never on the exit code. That rule is stated authoritatively in `plan-marshall:tools-integration-ci`; it is not restated here.

Step-level exceptions — calls whose non-zero exit is itself the signal — are documented inline in the step that issues them.

## When to use this skill

Load this skill when:

- Adding an ASCII box diagram to a skill / standards doc under
  `marketplace/bundles/**` (the diff-able diagram surface).
- Adding an ASCII box diagram to an AsciiDoc page under `doc/` inside a literal
  or fenced block.
- Touching an existing ASCII box diagram in any `.md` or `.adoc` source.

Do not load this skill for:

- User-facing visual diagrams in `doc/` — those are hand-authored SVGs governed
  by `pm-documents:ref-svg-diagrams`.
- Tables or aligned non-box monospace content (the validator only normalizes
  `┌…┐` box runs).

## Standards

| Document | Scope |
|----------|-------|
| [`standards/box-conventions.md`](standards/box-conventions.md) | Box-drawing character set, the right-border column-alignment rule, matching top/bottom rule widths, and how to author legends, flow-lines, and nested boxes so they are not mistaken for misaligned boxes. |

## Workflow

### Step 1 — Read the authoring conventions

Read [`standards/box-conventions.md`](standards/box-conventions.md). It defines
the canonical box-drawing character set, the alignment rule the validator
enforces, and the legend / flow-line / nested-box patterns the heuristic
validator deliberately leaves alone.

### Step 2 — Author the box inside a code/literal block

Place the diagram inside a fenced (` ``` `) block (`.md`) or a literal (`----`)
/ fenced block (`.adoc`). Use the canonical character set and author the content
without manually counting columns — the next step re-pads to a consistent width.

### Step 3 — Verify alignment with the validator (advisory)

After creating or editing any ASCII box diagram, run the validator's `check`
mode against the file:

```bash
python3 .plan/execute-script.py pm-documents:ref-ascii-diagrams:ascii_diagrams check --path {file}
```

`check` reports any misaligned box borders as `file` / `line` findings without
mutating the file. When it reports misalignment, repair it with `fix`:

```bash
python3 .plan/execute-script.py pm-documents:ref-ascii-diagrams:ascii_diagrams fix --path {file}
```

`fix` re-pads interior lines and rebuilds the top/bottom rules to a consistent
width; it is idempotent, so a second pass over an aligned file changes nothing.

This step is **advisory, not a hard commit-gate**. ASCII-box detection is
heuristic (legends, flow-lines, and nested boxes can resemble misaligned boxes),
so it is surfaced as an authoring aid and a repo-wide sweep recipe rather than a
blocking lint rule. The repo-wide sweep is
`pm-documents:recipe-verify-ascii-diagrams`.

## Canonical invocations

The canonical argparse surface for the entry-point script this skill registers:
`ascii_diagrams.py`. The plugin-doctor `missing-canonical-block` rule checks that this section is PRESENT,
matching its heading only — the body is never read; `manage-invocation-invalid` derives
its accept-set from a live `--help` walk rather than from this section. Consuming docs xref this section by name instead
of restating the command inline. See
[`pm-plugin-development:plugin-script-architecture` cross-skill-integration.md](../../../pm-plugin-development/skills/plugin-script-architecture/standards/cross-skill-integration.md)
§ "Script invocation in documentation".

### check

```bash
python3 .plan/execute-script.py pm-documents:ref-ascii-diagrams:ascii_diagrams check \
  [--path PATH]
```

### fix

```bash
python3 .plan/execute-script.py pm-documents:ref-ascii-diagrams:ascii_diagrams fix \
  [--path PATH]
```

## Related

- `pm-documents:ref-svg-diagrams` — visual SVG diagrams for the user-facing
  `doc/` tree (defers in-source skill/standards diagrams to ASCII for
  diff-ability; this skill governs those ASCII diagrams).
- `pm-documents:recipe-verify-ascii-diagrams` — repo-wide sweep that validates
  and fixes ASCII box-diagram alignment across `.md` and `.adoc` files.
- `pm-documents:ref-asciidoc` — AsciiDoc syntax and formatting standards
  (sibling skill; the validator scans `.adoc` literal/fenced blocks).
