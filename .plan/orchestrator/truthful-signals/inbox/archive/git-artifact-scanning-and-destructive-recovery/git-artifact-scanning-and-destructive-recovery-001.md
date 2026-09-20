envelope_version=1
sender_type=plan
sender_id=git-artifact-scanning-and-destructive-recovery
epic=truthful-signals
kind=candidate-lesson
created=2026-08-31T08:03:09Z

component=pm-plugin-development:ext-self-review-plan-marshall
category=improvement
created=2026-08-31
bundle=pm-plugin-development
confidence=high
source_plan=git-artifact-scanning-and-destructive-recovery

# Surface a guard whose predicate is satisfiable without the evidence its docstring names

## Context

This plan's whole subject was assertions that outrun their evidence — git artifact scanning claiming a `.gitignore` exclusion it did not have, and recovery prose routing readers to a destructive command without inspection. It reproduced that same defect three times in its own work.

The deepest instance is TASK-018. TASK-018 existed to *tighten* a guard so that a destructive disposal instruction had to be preceded by content inspection. The tightened guard was itself satisfiable without inspection:

- `_CONTENT_INSPECTION` matched `git diff --name-only` — a path listing, not content — because `--no-patch` was omitted from the exclusion set although `-s` was listed.
- `_is_destructive_instruction_qualified` ANDed five clauses with no ordering constraint, so a `git restore` appearing *before* the diff still satisfied an inspection-*first* requirement. Match position was first-vs-first with no path matching.

No in-house gate caught it. Not the whole-tree quality gate. Not plugin-doctor at 37 rules. Not the pre-submission self-review at 61 candidates across 22 lists. Not whole-tree verify. Not CI. CodeRabbit caught it, and the fix shipped as TASK-019.

The two other instances of the same archetype in this run were each caught by a *different* mechanism, and no mechanism caught more than one:

- A stale cardinal — "The three `main_*` captures" — shipped in `phase-handshake.md` in the same diff that added a **fourth** `main_*` capture whose new invariant-table row cross-references that very sentence. Caught by the pre-submission self-review (stale count prose is already a surfaced candidate class). Fixed by DELETING the cardinal rather than re-numbering it, because a count restated beside a growing registry re-stales on the next addition.
- The orchestrator published commit sha `6b929f4d3` in a PR body; it was a dangling pre-rebase object on no branch. Caught incidentally by the `create-pr` step, which re-derived it. The live sha was `42dc92362`.

## Root cause

Every structural gate in the suite checks that a thing EXISTS or PARSES. None can check that a predicate is FALSIFIABLE against the prose requirement it implements. The self-review caught instance 2 because a stale cardinal is a *structural* pattern; it could not catch instance 1 because "this regex admits a name-only diff" requires reading a docstring's stated intent against the pattern's actual extension.

## Proposed action

Add two deterministic candidate classes to the plan-marshall self-review surfacer. Neither judges — each surfaces a pair for the reviewer to judge:

1. **Prose-requirement vs implementing predicate.** When a function's docstring states a requirement in prose and the function body is a regex or a boolean conjunction implementing it, surface the docstring sentence beside the predicate. The reviewer then asks the one question no structural rule can: is there an input that satisfies the predicate and violates the sentence?
2. **Ordering word over an order-free conjunction.** When a docstring carries an ordering word (`first`, `before`, `then`, `precedes`, `prior to`) and the implementing predicate is a pure `and` of independent clauses with no positional comparison, surface the pair. This is exactly instance 1, and it is mechanically detectable.

## Evidence

- aspect: chat_history_analysis — "TASK-018 fixes it with matched controls, using the shipped `worktree-handling.md` § Recovery Loop as the negative control"
- aspect: request_result_alignment — three instances, three different catchers, no mechanism catching more than one
- aspect: invariant_summary — qgate finding `2a56cd`, the stale-cardinal instance, with the reviewer's explicit "delete the cardinal, do NOT re-number it" fix direction
- Run facts: 2 loop-back iterations of a permitted 5, both `returned_with_findings` (productive), both triggered by external review rather than by an in-house gate
