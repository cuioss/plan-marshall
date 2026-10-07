envelope_version=1
sender_type=plan
sender_id=executor-rejects-invalid-invocations-before-spawn
epic=code-intelligence-substrate
kind=candidate-lesson
created=2026-08-09T14:48:20Z

# Hand-built surface fixtures cannot see a strip-the-attribute defect — probe the guard live

component: plan-marshall:tools-script-executor
category: bug
confidence: high
source_plan: executor-rejects-invalid-invocations-before-spawn
source_pr: 1127

## Context

This plan shipped a pre-spawn invocation validator — a guard that refuses an invalid
`execute-script.py` call before spawning the child. Its own execute and finalize phases then
found **four** defects in that guard, every one of them a valid call refused or an operator
misdirected into a refusal, and **every one caught by running the guard live rather than by
the test suite**:

1. **`--help` refused on EVERY script** (decision.log `438350`, 01:46Z, phase-5). The first
   validating executor rejected `--help` everywhere with `reason=unknown_flag, accepted=[]`,
   because `parse_help_node` deliberately strips `help` from each derived flag set, so the
   validator saw it as undeclared. 17 real tests failed. Self-referential: the derivation
   probes each script with `--help` *through* this executor, so the guard starved the
   mechanism that feeds it.
2. **A leading top-level flag desynchronised the walk** (qgate `dc73da`, severity `error`).
   `architecture --project-dir . find --pattern '*.template'` was refused
   `reason=unknown_flag rejected=--pattern accepted=[content, pre]` while the identical call
   without `--project-dir` succeeded. The tell was that the same two accepted tokens came
   back for *different* verbs — the walk never left the ROOT node.
3. **Short `-h` still refused after the `--help` fix** (qgate `6d981f`). `_mentions_help`
   matched only `--help` and `--help=`, so `manage-tasks read -h` returned
   `missing_required_flag`, exit 2, no usage text, where the pre-change executor printed
   help. The finding records the reason it survived: *"No test covers `-h` (zero hits for the
   token across the test tree)."*
4. **The `unknown_flag` corrective advertised a set that contradicted its sibling corrective**
   (qgate `cdbb40`). `declared` was computed as `inherited_flags - _ALWAYS_ACCEPTED_FLAGS`
   unconditionally, dropping any genuinely-declared flag colliding with the universal
   allowlist — `--plan-id` and `--project-dir`, the two most common flags in the system. On
   one resolved node `unknown_flag` said the declared set was `task-number` alone while
   `missing_required_flag` on that same node named `--plan-id` as required. An operator
   following the first corrective is refused on the next attempt.

## Root cause

One shape produced all four, and the first finding states it exactly:

> "This was the exact hazard the design named and it still shipped past a green synthetic
> suite, **because every fixture surface happened to declare at least one flag**."

The suite builds its surfaces by hand. A hand-built fixture is written to be *representative*,
so it is populated — it declares flags, it has verbs, its walk starts at a verb. That makes an
entire defect class structurally invisible: any bug of the form *"the derivation strips /
omits / mis-attributes attribute X"* only manifests on a surface where X is absent, empty, or
collides, and no one hand-writes that fixture because it does not look like a real script.

The four defects are the same blind spot seen four times: `help` stripped from every derived
set (nothing in the corpus had an empty flag set), a leading optional flag before the verb
(no fixture invocation started with one), the `-h` spelling (zero occurrences of the token in
the whole test tree), and an allowlist-vs-declared name collision (no fixture declared a flag
that was also universal). Each was found the same way — by dispatching a real notation through
a regenerated executor — and each fix's own resolution record says so ("CONFIRMED LIVE",
"Verified live against the regenerated worktree executor", "Reproducer verified passing
first-party").

This is the plan reproducing its own subject matter. The plan exists because a plausible-
looking invocation that the real surface does not accept should be refused at the boundary;
its own guard shipped four times over a suite whose fixtures were plausible-looking surfaces
that the real script set does not resemble.

## Proposed action

Two changes, both aimed at the fixture population rather than at adding more cases:

- **Derive the fixture corpus from the real surface index rather than hand-writing it.** The
  generator already produces a 148-script / 106-surface index. A test that walks that index
  and asserts every registered notation's `--help`, `-h`, and declared-flag invocation is
  accepted is population-derived, so it fails the moment the derivation drops an attribute —
  exactly what four hand-built rounds could not do. This is the standing
  *"every set-guarding detector must be population-derived"* rule applied to the guard's own
  fixtures.
- **Make a live probe a required part of shipping a change to the validator.** All four were
  caught by regenerating the worktree executor and dispatching a real notation; none by the
  suite. That is not an argument for more unit tests, it is evidence that the synthetic and
  live surfaces differ in a way the suite cannot self-detect. A regenerate-and-dispatch smoke
  over a handful of real notations (including a help spelling and a leading top-level flag)
  belongs in the deliverable, not in the reviewer's judgement.

Worth recording alongside this: the *repair* half worked well every time. Each of the four
fixes shipped with fail-first proof and matched negative controls (`6d981f` added three
positive controls plus three matched negatives so the fix could not read as disabling
validation; `cdbb40` added an omission control and a required-subset-of-declared
non-contradiction invariant). The gap is detection, not remediation.

## Evidence

- decision.log `[2026-08-09T01:46:00Z] [WARNING] [438350] (plan-marshall:phase-5-execute)` — the
  `--help` false rejection, the 17 failing tests, and the verbatim "every fixture surface
  happened to declare at least one flag" diagnosis.
- qgate-6-finalize findings `dc73da` (severity `error`), `6d981f`, `cdbb40` — the three later
  recurrences, each with its live reproducer in the finding detail and its live verification
  in the resolution detail.
- `6d981f` detail — "No test covers `-h` (zero hits for the token across the test tree)", the
  clearest single statement of the coverage hole.
- decision.log `[2026-08-09T01:36:23Z] [e4341f]` — the related premise correction: the guard IS
  self-exercisable against a worktree-bound executor, which is what made live probing possible
  at all and is the mechanism the proposed smoke would formalise.
