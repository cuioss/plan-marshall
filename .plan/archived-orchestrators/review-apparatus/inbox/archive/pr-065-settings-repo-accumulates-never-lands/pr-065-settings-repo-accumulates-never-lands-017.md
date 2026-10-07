envelope_version=1
sender_type=plan
sender_id=pr-065-settings-repo-accumulates-never-lands
epic=review-apparatus
kind=candidate-lesson
created=2026-09-14T19:22:37Z

component=plan-marshall:phase-3-outline
category=anti-pattern
source_signal=qgate_finding
source_plan=pr-065-settings-repo-accumulates-never-lands
evidence=qgate finding 9407ee (3-outline, fixed via TASK-013)

# The producer was fixed and the one consumer whose decision gates a destructive delete was left reading a page

Deliverable 1 made `ci pr list` derive a complete population instead of reporting
a page. `phase-6-finalize/standards/branch-cleanup.md:177` calls `pr list --head
{branch} --state open` with no `--limit`, extracts a bare count at :180, and that
count drives the Safety Check at :318-327, which ABORTS branch cleanup when other
open PRs use the branch.

So the fix's single most consequential consumer — the one gating a branch
deletion — was not in the deliverable's affected files. After the producer
landed, that call site would receive a `truncated` field it does not read and a
default `--limit` it does not set: a page still read as a population, in the exact
code path the deliverable existed to correct.

## Why it matters to this epic

Fixing a producer's contract without migrating its consumers leaves the defect
alive at the point where it matters most, while the plan reports the defect
fixed. The scope-criterion validator caught it here; nothing in the outline's own
success criterion would have.

## Candidate rule

When a deliverable changes the SEMANTICS of a returned value (page to
population, adding a `truncated` discriminator), the consumer enumeration is part
of the deliverable, not an optional follow-up — and consumers whose decision is
destructive or irreversible are the ones to enumerate first. Record a deliberate
exclusion under declared residue rather than leaving the set implicit.
