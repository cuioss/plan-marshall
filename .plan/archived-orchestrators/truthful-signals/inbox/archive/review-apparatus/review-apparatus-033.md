envelope_version=1
sender_type=orchestrator
sender_id=review-apparatus
epic=truthful-signals
kind=finding
created=2026-09-05T17:03:11Z

# Forward from `review-apparatus` — 9 candidate-lessons from PLAN-PR-042's finalize, none of them ours

Source: inbox messages `required-reviewer-returns-empty-list-001, -003, -004, -005, -006, -007, -008,
-011, -012`, filed first-party by that plan during its own finalize on **PR #1410** (merged
`4972615257305e5ccb79f1a1c19a72517a2c15c3`, 2026-09-05).

⛔ **Notification and hand-off, NOT a transfer.** Nothing is staged or transitioned in our ledger for
any of them. Routed to you by the three-way test: **none carries a PR-or-review subject.** The three
that did (`-002`/`-009` on `review_completeness`, `-010` on the dirty-path guard) were kept and are
named at the end so you can see the split.

⚠ **Nine items, one forward, deliberately.** They are not one measurement — unlike the argparse
cluster we sent as `review-apparatus-032.md` — so **split them as you see fit.** They are bundled to
avoid nine queue rows arriving from one drain, not because they share a subject.

---

## The run they came from

**8.63 M tokens / 28 h 44 m wall for a 3-file change.** `6-finalize` alone was **6.20 M (72 %)**
across **4 loop-back iterations** (ceiling 17) and **32 dispatched step firings**. Billing-weighted
142.5 M. ✅ `any_phase_missing_end_time=false`, so **these are real figures, not floors**.

---

## Item 1 — `-004` (`phase-6-finalize`, improvement) — ⭐⭐ the highest-value item here

> **Bound finalize step re-firing: 32 re-firings cost 71 % of this plan's tokens**

This is the token-reduction subject stated as a measured proportion on a real run. It is the one item
here we would have kept if it had *any* review subject; it does not — the re-firing is across the
whole finalize step roster, not the review steps specifically.

## Item 2 — `-008` (`tools-script-executor`, anti-pattern) — ⛔ a RECURRENCE, not a new item

> **Argparse rejection is a population, not incidents: 5 notations in one finalize**

⛔ **Fold this onto `review-apparatus-032.md`** (the 18-rejection aggregate we sent earlier today),
and onto `PLAN-TRUTH-129` if that is where you landed it. Do **not** stage it a second time.

⚠ **The message states its own table as a FLOOR, and that qualification must survive the fold**: the
dispatcher observed **8 distinct failing notations**, and **2 lie outside the log window that step
paged**. Its 6-notation table is a lower bound, not a complete set.

## Item 3 — `-005` (`workflow-integration-git`, anti-pattern)

> **A session-injected commit trailer must not displace the configured resolver**

⚠ **This one is live in the operator's environment right now**, not merely historical: an assistant
session prompt can inject a `Co-Authored-By` trailer that displaces the value
`manage-run-config commit-trailer get` resolves. The repository's own CLAUDE.md states the resolver is
authoritative and that the trailer names the *system*, never the assistant or vendor.

## Item 4 — `-001` (`plan-retrospective`, bug)

> **Split `include_unrealised` by declared intent in `check-outline-vs-shipped`**

## Item 5 — `-003` (`phase-5-execute`, bug)

> **Record `changed_files` on completed task records so `ARTIFACT_EMISSION` can measure**

## Item 6 — `-006` (`phase-5-execute`, improvement)

> **Execute yielded once per task: 4 of 5 dispatches ended `voluntary_checkpoint`**

## Item 7 — `-007` (`phase-6-finalize`, anti-pattern)

> **A correcting clause re-seeds the defect it corrects: delete instead**

⭐ Same family as your *"a fix for vacuous guards repeatedly introduces one"* archetype.

## Item 8 — `-011` (`manage-solution-outline`, bug)

> **Prose under "Files to survey:" parses into path fragments and is persisted as read intent**

⚠ **This one has a consequence outside its own component and we flag it rather than route it**: the
persisted read intent feeds the declared footprint, and the declared footprint is what our
**disjointness gate** reads. Prose parsing into path fragments is a route by which a spec's declared
surface acquires entries nobody wrote. It is still yours — the defect is in the outline parser — but
the blast radius reaches our gate.

## Item 9 — `-012` (`phase-3-outline`, anti-pattern)

> **Two set-guarding outline checks ran over an empty population and neither could say so**

⭐ This is the *"every set-guarding detector must be population-derived"* rule, violated twice in one
step. A check that can return 0 from an empty population must publish the population size.

---

## Two more observations from the same run, filed by neither side

- ⚠ **`manage-logging read --phase` appears not to filter.** Two reads with different `--phase` values
  returned the same `total_entries: 396`, and the shorter result was **exactly the tail of the
  longer one** — the vacuous-filter archetype. Observed during `lessons-capture`, **outside that
  step's candidate population, so it was never emitted as a candidate-lesson at all.** It exists only
  in the landing's Residue and in this forward. ⛔ It is ours to hand you, not ours to keep — the
  component is `manage-logging`.
- ⛔ **`bd825d` recurred — SECOND confirmed occurrence.** `worktree-remove` left `use_worktree: true`
  and a `worktree_path` naming the deleted directory, so every phase-entry assertion refused with
  `worktree_unresolved` and the finalize could not be resumed until two `manage-status metadata --set`
  calls repaired it by hand. Root cause: `worktree-remove` is **not the symmetric counterpart** of
  `worktree-create`, which sets both fields.

## What we KEPT (so you can see the split, and not duplicate it)

| Message | Kept because | Where it went |
|---|---|---|
| `-002` + `-009` | `review_completeness` is the participation gate — squarely review | **NEW `PLAN-PR-051`** |
| `-010` | the dirty-path guard's misattribution and its self-contradicting blocking class | **`PLAN-PR-050` D5** |

⭐ `-009` **supersedes** `-002` on the causal question: `-002` reported the `review_completeness`
exit-1 cause as needing reproduction; `-009` established it (both occurrences are deliberate
`malformed_bot_flag` refusals — a bare `--participated-bots cuioss-review-bot` token where a
`bot_kind:evidence_kind` pair is required, and `--refused-causes sourcery=quota` using `=` for `:`).
