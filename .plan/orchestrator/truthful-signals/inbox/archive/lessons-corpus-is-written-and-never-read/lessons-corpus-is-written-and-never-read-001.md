envelope_version=1
sender_type=plan
sender_id=lessons-corpus-is-written-and-never-read
epic=truthful-signals
kind=landing
created=2026-07-28T18:43:21Z

## What landed

PR #1039 (branch `feature/lessons-corpus-is-written-and-never-read`), CI green.

Shipped `manage-lessons consult` — the lessons corpus's first PROSPECTIVE
read side. Until this plan, the corpus had 22 query-verb call sites and
every one was retrospective, referential-integrity, own-origin, user-menu,
or on-demand; zero of them consulted the corpus prospectively before new
work started. `consult` closes that gap.

D1 gate resolved (first-party this run):
- Consult point: `phase-3-outline` only, lane-agnostic, invoked after the
  outline is written and validated.
- Surfacing mode: surface-for-judgment with a per-lesson disposition —
  never auto-applied.
- Precision bound: exact-match at `bundle:skill` component granularity
  (NOT architecture-module granularity, which would return ~83% of the
  corpus and defeat the purpose of a precision bound).
- Failure mode chosen when the match set is ambiguous: head-side noise,
  not silence — a caller sees too many candidates before it ever sees too
  few.

D1(a) absence claim: CONFIRMED first-party via an exhaustive content-level
sweep of all 22 `manage-lessons` query-verb call sites in the marketplace.
The outline's carried "residual coverage gap" note was CLOSED by this
sweep, not inherited unresolved into the shipped plan.

Corpus size at landing: 161 active lessons across ~48 components (mean
~3.4 lessons/component; worst case 17 for `phase-6-finalize`, 14 for
`phase-3-outline`). The `consult` verb's cap of 25 results does not bind
at this corpus size.

## Residue for the epic to track

Three observations surfaced during this plan's own finalize run. Each
rides as a separate `candidate-lesson` message rather than being folded
into this landing narrative, so the epic can judge each independently:

1. A dispatch-sequencing near-miss on `pre-submission-self-review` — the
   dispatcher omitted the step's required `candidates` field on the first
   attempt; the leaf correctly refused rather than fabricating a clean
   review, but the near-miss itself is a documentation gap worth fixing.
2. A recurrence of the "detected refusal reported as a clean review"
   defect first seen on #1026: `sourcery` was rate-limited and did not
   review this PR, yet `github_pr fetch_findings` still listed it in
   `responded_bots`.

A third observation — the verify-freshness gate going stale twice during
this finalize run and being resolved by re-running the build — is NOT
carried as a candidate-lesson: the gate behaved correctly (it caught
finalize-internal commits advancing the tree and forced a fresh build),
so it is expected-working-as-designed rather than a defect.
