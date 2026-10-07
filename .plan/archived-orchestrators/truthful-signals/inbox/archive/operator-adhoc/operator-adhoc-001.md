envelope_version=1
sender_type=orchestrator
sender_id=operator-adhoc
epic=truthful-signals
kind=finding
created=2026-07-28T13:17:24Z

# Finding: inert in-prose thinking directives in dispatched workflow docs

Out-of-plan finding, main checkout. Unverified beyond the greps noted under D2.

**Theme fit**: a directive that reads as if it steers the model, but is
structurally incapable of firing. Confident signal, hidden caveat.

## Root cause

Model/effort is pinned by the dispatched `execution-context-{level}` /
`execution-context-reader-{level}` variant filename, per
`extension-api/standards/ext-point-dynamic-level-executor` (ADR-003).
`agents/execution-context.md:30` states outright: "Model and effort are NOT
prompt-body fields." Any prose INSIDE a dispatched workflow doc that asks the
model to adopt a thinking level is therefore inert or in tension with the pin —
and it diverges from the contract stated two files away.

Archetype: **vacuous guard** (predicate can never fire). This is now n=5.
Secondary archetype: doc-contract-divergence.

## Confirmed instances

1. `plan-marshall/skills/plan-marshall/workflow/research-best-practices.md`
   - `:9` — "Use **ultrathink mode** for deep analysis and synthesis"
   - `:46` — "consider using ultrathink to formulate the most effective search query strategy"
   - `:112` — "use ultrathink at the start of this step"

   Reachable ONLY via dispatch to `execution-context-reader-{level}`
   (`agent-behavior-rules.md:98-110`). Effort already pinned by the variant.

2. `pm-documents/skills/ref-documentation/workflow/content-review.md`
   - `:7` — descriptive restatement of the same scaffold
   - `:177` — "**CRITICAL:** Use careful step-by-step reasoning for comprehensive tone assessment"

   This one is worse than inert: a CoT scaffold on a checklist-following review
   task, the exact case where published results show CoT prompting pulls
   attention off the stated constraints.

## Scope — three deliverables, ordered

**D1 — Fix the confirmed instances.** Must NOT be gated on D3. Remove the
reasoning-level / process narration only; preserve surrounding criteria prose
verbatim. Modules: `plan-marshall`, `pm-documents`.

**D2 — Corpus-wide sweep for the same defect class, then fix what it finds.**
THIS IS A DISCOVERY DELIVERABLE — its output size is unknown at spec time.

> The originating grep was a SAMPLE, not an enumeration. It covered:
> `ultrathink`, "think step by step", careful/deeply + reason|think|consider|analyze,
> "take your time", "before answering". Do not treat that list as the population.

The candidate file set MUST be population-derived from the dispatch roster —
every markdown reachable as an `execution-context*` `workflow:` target; see
`test/_shared/_dispatch_roster.py`. Enumerate the roster, then scan it. Report
roster size and hit count separately: a count of files examined is a VOLUME, not
a coverage number.

**D3 — plugin-doctor rule preventing reintroduction.** Population-derived
detector over the same roster, not a hard-coded path list.

FALSE-POSITIVE BOUNDARY IS THE HARD PART: 24 of 25 corpus hits for
"step-by-step" are legitimate procedural prose ("Step-by-step workflow for
creating a solution outline"). Descriptive prose about workflow SEQUENCING is
not a violation. Only directives asking the model to adopt a reasoning level or
narrate a reasoning process are. Needs test cases in both directions — a
detector that fires on procedural prose is a regression, not a win.

## Out of scope (deliberate)

Any sweep of CRITICAL / NEVER / MUST NOT / MANDATORY emphasis markers. Corpus
counts: `MUST NOT` 220, `CRITICAL` 170, `NEVER` 164, `MANDATORY` 47, `ALWAYS` 43,
`FORBIDDEN` 20. Distribution is flat (max 18 in one file, and that file is
`plugin-architecture/references/execution-directive.md` — a document ABOUT
directives). These guard true invariants: `.plan/` script-only access,
one-command-per-Bash, executor notation, TOON schema shape. Leave them alone.

## Why not recipe-surgical-fix

Checked against its Step 1 fit gate before proposing this. It aborts:

| File | Module (via `architecture which-module`) |
|------|------------------------------------------|
| `research-best-practices.md` | `plan-marshall` |
| `content-review.md` | `pm-documents` |
| plugin-doctor rule + tests | `pm-plugin-development` |

Three modules fails `cross_module`; D2's unbounded discovery pass fails
`too_broad`. Findings-only also fails — those two files are already in different
modules.
