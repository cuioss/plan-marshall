envelope_version=1
sender_type=plan
sender_id=pr-065-settings-repo-accumulates-never-lands
epic=review-apparatus
kind=candidate-lesson
created=2026-09-14T19:22:32Z

component=plan-marshall:phase-3-outline
category=anti-pattern
source_signal=qgate_finding
source_plan=pr-065-settings-repo-accumulates-never-lands
evidence=qgate finding 330014 (3-outline, fixed via TASK-012)

# A deliverable claimed its file list came from a content sweep; re-running the sweep refuted it

Deliverable 1's "Change per file" asserted that the four documentation sites
"were enumerated by a content sweep for `pr list` over the inventory rather than
by recall". Re-deriving that sweep independently found a fifth site —
`persona-plan-marshall-agent/standards/argument-naming.md:159`, carrying the
Canonical Forms row for `ci pr list` — which was NOT in `affected_files`.

The sweep's coverage was clean (`files_scanned 5460`, `unreadable 0`,
`truncated false`, `elided 0`), so the omission was real rather than an
unsearched-population artifact.

## Why it matters

The claim "enumerated by a sweep, not by recall" is itself a completeness
assertion, and it was asserted rather than derived — the stated provenance was
not the provenance. This is the archetype the corpus already carries as
"DERIVE completeness, never assert it", recurring in the one place that
explicitly invokes a derivation to license the claim.

## Candidate rule

A deliverable that cites a sweep as its authority should carry the sweep's
coverage fields and its hit list, so the Q-Gate re-derivation compares against a
recorded result rather than against a prose claim about one. As filed, the only
way to check the claim was to re-run the whole sweep.

## Second-order note

One correction the triage established: the row is NOT under enforcement in this
direction — `scan_canonical_forms` checks documented-flag-to-argparse only, never
the reverse, and it skips bracketed tokens. So no gate would have caught it. The
finding's own stated enforcement rationale was wrong while its conclusion was
right.
