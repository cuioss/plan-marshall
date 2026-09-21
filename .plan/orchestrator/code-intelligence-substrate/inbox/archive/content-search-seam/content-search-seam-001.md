envelope_version=1
sender_type=plan
sender_id=content-search-seam
epic=code-intelligence-substrate
kind=landing
created=2026-08-03T14:28:54Z

# PLAN-CIS-001 content-search-seam — landed

**PR**: #1084 — squash-merged via merge queue as `714130bdb` on `main`.
**Verified**: landing confirmed against the commit graph and by reading merged file
content back, not from the merge response's `merged` field (the #1081 false-green
archetype).

## Outcome

All 5 deliverables fulfilled, 7 tasks, 7 paired `[OUTCOME]` lines. Declared-vs-realized
footprint was an exact 37/37 set match against the merge commit — recall 1.00,
precision 1.00, no scope creep. `references.affected_files` stayed accurate through a
scope that moved during execute, which is that store's usual failure mode.

`architecture search --content` ships: dispatched leaves that are denied `Grep` now have
a first-class content-search verb, and the four-field complete-coverage rule is contracted
once in `client-api.md` rather than restated across the tree.

## Residue owed to this epic

1. **`search --content` ReDoS observation (accepted, not fixed).** A caller-supplied regex
   has no timeout — Python `re` offers none. Both mitigations were judged worse than the
   gap. The carry-forward is that any future bound MUST be a **reported coverage field**,
   never a silent body-size cap: a silent cap manufactures exactly the confident-false-negative
   defect this plan removed.

2. **Reviewer-list-as-sample.** A CodeRabbit finding named 8 duplication sites; the true
   population was 14 files. The triage derived the population instead of trusting the list.
   Generalizes: a reviewer's enumeration of call sites is a SAMPLE, never a population.

3. **Bot review coverage is not what a green check reports.** At merge, all three review
   bots were stale or rate-limited and the final commit `94206f88f` carried no automated
   review from any of them — while CodeRabbit's CI check read SUCCESS. The two measured
   bots found *non-overlapping* bypasses in the same function, so neither is redundant.

## Cross-epic routing note

7 lessons from this plan's retrospective were written to the GLOBAL lessons store
(`2026-08-03-14-001` … `-007`) rather than arriving here as `candidate-lesson` messages:
the retrospective was dispatched with `orchestrated: false` because the dispatcher did not
resolve orchestration context before the dispatch. The lessons exist and are not lost —
they are in the wrong store. Re-routing them into this inbox is owed follow-up.
