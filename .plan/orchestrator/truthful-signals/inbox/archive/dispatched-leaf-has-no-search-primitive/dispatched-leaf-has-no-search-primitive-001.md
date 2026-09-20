envelope_version=1
sender_type=plan
sender_id=dispatched-leaf-has-no-search-primitive
epic=truthful-signals
kind=landing
created=2026-07-29T09:18:10Z

## What landed

**PR #1046** — `fix(execution-context): close the leaf broad-sweep primitive contract gap` (merge-pending at finalize time).

`git grep` is now sanctioned as an explicit, bounded carve-out to the project's bare-`grep` prohibition, for the one case a dispatched `execution-context` leaf cannot otherwise serve: a broad content sweep when the harness has revoked the `Grep` tool. The carve-out and its bounds landed across 6 documentation surfaces plus 2 tests that pin them.

## Root-cause reframe (operator, mid-run)

The original outline blamed `architecture find` for not doing content matching. That framing was **wrong** — `architecture find` is a path glob working exactly as designed.

The real defect is a **permission asymmetry**:

- The hard rule ("never use Bash `grep`") prescribes *the `Grep` tool* as its own remedy.
- A dispatched leaf has `Grep` revoked at harness runtime.
- The bare-`grep` prohibition stays enforced regardless.

So the remedy the rule names is unreachable precisely for the executor class the rule still binds. It is not an empty intersection of constraints — it is one constraint whose escape hatch is permission-gated away from a subset of executors.

"Grant `Grep` to leaves" was investigated and is **not an available repair**: the agent frontmatter already declares `Grep`, and `permissions.deny` is `[]`. The revocation happens below the surfaces this project controls.

`arch-constraint` lesson `2026-07-29-08-001` already records the constraint itself.

## Strength of evidence

The defect reproduced **six times live inside its own plan run** — in 2-refine, 3-outline, the Q-Gate, 5-execute, the reframe dispatch, and the self-review gate. First-party, not inferred.

## Signals

Six Q-Gate findings were raised **and resolved in-run** (1 in 2-refine, 3 in 3-outline, 2 in 4-plan) — the slipped-then-caught class.

## Residue the epic should track

1. **HEADLINE (epic theme, direct hit).** `coderabbit` (a *required* reviewer) reported a green `completed: true` check-run while posting **zero comments and zero reviews** across ~32 minutes and 24 polls of *both* endpoints. `sourcery` hard-refused on a weekly rate limit. Only `pr-agent` participated, with boilerplate. The operator merged unreviewed. This is "check states lie in both directions" recurring — a confident green signal hiding the caveat that nobody actually looked.
2. **Tool defect, unfixed** — `manage-solution-outline get-module-context` is structurally unusable in phase-3.
3. **Tool defect, unfixed** — `phase-3-outline` prescribes a `Task:` dispatch that a dispatched leaf cannot perform.
4. **Doc-duplication finding, unfixed** — `finalize-step-simplify` flagged the new "Broad content sweep" section in `tool-usage-patterns.md` as near-verbatim duplication of the SKILL.md carve-out prose.

Each of items 1-4 rides as its own `candidate-lesson` message alongside this landing.
