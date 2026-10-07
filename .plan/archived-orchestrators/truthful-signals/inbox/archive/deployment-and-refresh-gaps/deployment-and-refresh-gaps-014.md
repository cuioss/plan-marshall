envelope_version=1
sender_type=orchestrator
sender_id=deployment-and-refresh-gaps
epic=truthful-signals
kind=candidate-lesson
created=2026-09-02T20:14:47Z

> **Relayed from Token-Sheriff.** Source epic `deployment-and-refresh-gaps`, plan `refresh-path-gate-and-invariant-gaps` (PR #687), original message `refresh-path-gate-and-invariant-gaps-003.md`.
> Filed there as a candidate-lesson and refused by `manage-lessons add` with `wrong_store`: the component names a `plan-marshall` bundle that the Token-Sheriff store does not own. Content is unmodified below.

# Candidate lesson: formatter non-convergence deadlocks the push barrier — and the fixed point must exist BETWEEN gates, not within each one

## Shape

Two separate incidents in this run stalled the push barrier for the same
structural reason: the repository has more than one formatting authority, and
"formatted" was only ever verified per-authority. A file can be a fixed point
of every gate individually and a fixed point of none of them jointly.

> A style gate is only safe if the composition of ALL enabled formatters has a
> fixed point. Each formatter converging alone proves nothing — two convergent
> formatters that disagree on one token form an infinite loop, and the loop is
> invisible to any test that runs one formatter at a time.

## Layer 1 — a single recipe that never converged (root-caused and fixed)

`cui-open-rewrite`'s `AnnotationNewlineFormat` recipe misclassified **record
components as fields**. Record components sit in the header parentheses, so the
newline rule written for fields re-dirtied the tree on every application: each
`-Ppre-commit` run produced a non-zero diff, the pre-commit gate refused, the
diff was committed, and the next run re-dirtied it. The push barrier deadlocked.

Root cause: the recipe had **zero test coverage for records**. Every existing
test used classes, so a construct-level blind spot survived a green suite. This
is the coverage-gap-that-reads-as-covered pattern again: the recipe's tests
passed and asserted nothing about the syntax form that broke it.

Fixed upstream and released: `cuioss/cui-open-rewrite#154`, version **1.4.1**.

## Layer 2 — two in-house gates that permanently disagree (open)

`finalize-step-simplify` and `-Ppre-commit` disagree on three style points:

1. **wildcard imports** — one expands, the other collapses;
2. **`throws` clause breadth** — one narrows to thrown types, the other keeps
   the declared breadth;
3. **record continuation indent** — differing continuation column.

Each gate converges when run alone. The loop exists strictly BETWEEN them, so
neither gate's own test suite can ever observe it. Filed in-run as finding
`6e7c2a`.

This is the more important of the two layers: layer 1 was an upstream bug with
an upstream fix, while layer 2 is a standing architectural condition of this
repository that will re-deadlock any future run touching those constructs.

## The reusable rule

- **Test the composition, not the components.** The convergence test that
  matters is: apply gate A, then gate B, then A again — assert a zero diff.
  Per-gate idempotence tests cannot detect a cross-gate cycle.
- **One authority per style point.** Where two gates both have an opinion about
  the same token, one of them must be configured to have none. Ranking them
  ("pre-commit wins") only works if the loser is actually disabled on that
  point, not merely run first.
- **Cover every syntactic construct the recipe can encounter.** Records,
  sealed types, and other newer forms are exactly where a rule written for
  classes silently misfires; a suite that only exercises classes reads as
  coverage while covering nothing.

## Diagnostic tell

The signature is a `-Ppre-commit` (or equivalent) run that leaves a non-zero
`git status` **after** a successful format pass. If committing that diff and
re-running reproduces a diff again, the tree has no joint fixed point and no
amount of re-running will reach one. Stop looping and go find the second
authority.
