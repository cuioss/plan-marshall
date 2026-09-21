envelope_version=1
sender_type=plan
sender_id=domain-over-provision
epic=operator-ux
kind=candidate-lesson
created=2026-09-02T14:18:06Z

# Candidate lessons from PLAN-01 (domain-over-provision)

Routing correction: these lesson dispositions were made during PLAN-01's finalize while
the retrospective steps were dispatched with `orchestrated: false`. The plan IS
epic-bound (`orchestrator inbox detect` → `orchestrated: true`, `epic: operator-ux`),
so the dispositions are mirrored here. The lesson files themselves live in the global
store; this message is the epic-visible record of what PLAN-01 learned.

## Recorded — new

**`2026-09-02-14-001`** — a delete-everywhere fix must verify completeness by SEARCHING
the corpus, not by enumerating the sites the round already knows.

Round 6 of PLAN-01's pre-submission self-review deleted a contract restatement from six
sites and its commit message claimed the contract "now lives there and nowhere else".
That claim was false: a seventh site survived, and round 7 found it in one command —
`architecture search --content --pattern "unconditional union"` (0 hits after the fix,
5314 files, clean coverage). Round 6 had verified its own completeness against its own
working set, which is complete for the previous round's proposition and complete for
nothing else. Cost of not running the search: one full level-5 dispatch inside a phase
that consumed 55% of the plan's 4.18M tokens.

This is one layer past the already-filed `2026-09-02-13-001` (apply the convergent
resolution, do not narrowly reword): obeying that rule terminates the *seeding* but not
the *class*.

**`2026-09-02-08-001`** — Sourcery's weekly-quota refusal is a third wording that
matches neither registered `refusal_pattern`, so a declination is credited as
participation. Sourcery declares no `review_body_summary_patterns`, whose fail-closed
effect means nothing downstream can demote it; the miscredit then propagates into
`actionable_count`, `pct_resolved_as_fixed` and `escapes_total`. Cause is `quota`, not
`size` — waiting is productive and splitting the PR would be the wrong remedy.

## Merged as recurrences — no new files

- **`2026-09-02-13-001`** — eight of PLAN-01's self-review findings are instances of
  correction-breeds-the-next-instance. Rounds 2, 3 and 4 each found defects introduced
  by the previous round's own fix prose; the class closed only when fixes became
  deletions.
- **`2026-09-02-13-002`** — PLAN-01 reproduces the source plan's dispatch/ledger pairing
  rate almost exactly: 8 of 20 paired in 6-finalize, `channel_completeness.ratio 0.409`
  to three decimals, with `pre-submission-self-review` again the worst-covered step
  (2 of 4 firings unpaired). Two independent plans landing on the same ratio points at a
  structural call-site partition rather than sporadic dropped writes.
- **`2026-08-25-09-009`** — third sighting of `build_count: 0`. PLAN-01 confirms the
  daemon-routing hypothesis: 72 `pyproject_build` calls, 7,231,000 ms (74.3% of all
  script time), every one carrying `mechanism=daemon_longpoll`, none executed inline.

## Held at medium, reported not recorded

Proposition-axis blindness. Rounds 1-5 asked *what set does the detector return*, round 6
*how is it composed*, round 7 *what does `ambiguous: true` oblige the caller to do*. Each
round's search was shaped by its own proposition and could not see the next one. The
re-search remedy above fixes site coverage within a proposition; it does not fix this.
