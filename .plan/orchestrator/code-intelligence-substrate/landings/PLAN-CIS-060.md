# Landing Analysis: PLAN-CIS-060 — The verdict field's read and write integrity

epic: code-intelligence-substrate
workstream: WS-07
pr: 1355
merge_commit: `91a07aaa4`
plan_marshall_plan_id: verdict-field-read-and-write-integrity
archived: `.plan/local/archived-plans/2026-08-26-verdict-field-...`

## Outcome

**completed** — 3 of 3 deliverables, 23 of 23 finalize steps. PR state corroborated first-party via
`ci pr view --pr-number 1355` → `state: merged`; `landing_commit` `91a07aaa4ffe5007a39963aee4031e83d497155c`
matches `origin/main` HEAD exactly.

⭐ **This is the FIRST landing in this epic to arrive `complete: true`** — `inbox landing-check`
reports every required fact key supplied, `missing_keys[0]`. Every prior landing in this ledger was a
prose paste with no machine-readable block, so the drain could not establish that the required facts
had drained. It can now.

⚠ One inconsistency, benign: the landing message's `steps` fact records `archive-plan:pending` while
the operator report shows it `[OK]`. The message was emitted by `emit-landing`, which runs BEFORE
`archive-plan` — so the block is a truthful snapshot of a step order, not a stale claim. Parsed with a
LAST-colon split, per the payload spec: `project:finalize-step-plugin-doctor` → `done`, not
`project` → `finalize-step-plugin-doctor:done`.

## The fix works, and this ledger is the proof — 7 specs now BLOCK that previously passed vacuously

⭐⭐ **Re-derived first-party at HEAD `91a07aaa4`, not carried from the landing narrative:**
`corpus verdicts --slug code-intelligence-substrate` now reports `unreadable_claim_section_count: 7`
and **`blocking_count: 7`**, against `blocking_count: 0` on the same corpus one day earlier. The seven
are exactly the specs D13 named, each carrying `section_verdict: absent`:

| Spec | Authoring form of its claim section |
|---|---|
| `PLAN-CIS-049-architecture-store-query-truthfulness.md` | prose-only |
| `PLAN-CIS-050-measurement-and-cost-integrity.md` | prose-only |
| `PLAN-CIS-051-detector-and-auditor-integrity.md` | prose-only |
| `PLAN-CIS-052-finalize-dispatch-and-blocking-boundary-observability.md` | prose-only |
| `PLAN-CIS-053-test-suite-anti-vacuity.md` | prose-only |
| `PLAN-CIS-054-documentation-surface-truthfulness.md` | prose-only |
| `PLAN-CIS-055-cloud-plan-lane-contract-proposals.md` | table-form |

⛔⛔ **CONSEQUENCE FOR THE QUEUE, and it is large: these seven are the first SEVEN rows in staged
order.** The prep-ready gate now correctly refuses all of them, so the emittable head of the queue
jumps to `PLAN-CIS-056`. **This is the fix behaving exactly as designed — a spec whose premises were
never checked is now visibly unemittable instead of invisibly admitted — and it is not a regression.**
D13's remedy is discharged in both directions: the read side blocks, and `corpus set-verdict
--section-scope` is the write address that repairs a blocked spec **in one call without re-authoring
its claim prose**.

⛔ **None of the seven was repaired, deliberately** — the plan states this, and this ledger confirms it
(`section_verdict: absent` on all seven). Repair is re-grounding work and belongs to a `cleanup` pass
or an operator decision, not to a landing analysis.

## The measurement REFUTED a sibling epic's stated denominator

⭐ First-party from the run's TASK-4 sweep over all 9 epic slugs: **331 specs scanned, 26 unreadable,
26 blocking**, partition `absent 104 / empty 0 / unreadable 26 / parsed 201` **summing exactly to 331**
— a stated partition that closes over its own population, which is the discipline this epic demands.

- **This epic's expectation of 7 is CONFIRMED** — 7 of 64, and independently re-derived here.
- **`truthful-signals`' numerator of 19 is CONFIRMED and now twice-observed.**
- ⛔ **Its DENOMINATOR is REFUTED: 161 heading-carrying specs, not the 124 its spec states.**
- Authoring forms of the 26: table-form 7, prose-only 19, template-placeholder **0**, fenced-only-body
  **0** — ⭐ both zeros **derived from a content sweep over 5 246 files**, not merely unobserved. A
  population-derived zero, which is the standard this epic holds everything else to.

⇒ **Cross-epic obligation, OWED**: `truthful-signals` must be told its denominator is wrong. Their
`19/124` becomes `19/161`; the numerator survives, the ratio does not.

## Cost

**5 132 687 tokens · 50 448 s wall (14h00m) / 4h20m worked · 6 tasks · 10 commits · 12 files.**
`any_phase_missing_end_time: false`. ⚠ Unlike PLAN-CIS-059, this run reports **no loop-back**, so the
`-003` clamp defect that invalidated 059's worked-time figure does not obviously apply here — but the
clamp is still unreported when it fires (CIS-050 D2.i), so the worked figure is **not independently
trustworthy** and is recorded rather than relied on.

## Findings carried out — all routed, none dropped

Eight `candidate-lesson` messages accompanied this landing and are dispositioned in the
§ 2026-08-26 Inbox drain record in `epic.md`. The three the plan itself flagged as most consequential:

1. ⛔ **The finalize dispatch ledger under-counts by ~36%, and its own auditor grades that `nominal`.**
   Seven `pre-submission-self-review` rounds produced **2** `[DISPATCH]` lines, **2** `effort
   resolve-target` records and **2** boundary rows — all three channels key on step ENTRY, so they
   share one blind spot. `6-finalize` records 2 883 328 accumulated tokens against a dispatch-boundary
   total of 1 555 736. ⭐⭐ `check-dispatch-audit.py::cmd_run` returns `ratio: 1.0` **by comparing two
   unrelated populations** — the correctly-scoped finalize count against the UNSCOPED phases-2-6 count;
   the finalize-scoped ratio is **12/22 = 0.545**. **A vacuous green in the instrument that measures
   the instruments** — squarely this epic's subject.
2. ⛔ **Two live review-pipeline defects, the false-green and false-red halves of one gap**, both fired
   in this single run. Sourcery's rate-limit refusal is credited as PARTICIPATION (a third,
   undocumented budget phrasing matches neither the declared `refusal_pattern` nor the structural
   fallback, so `refused_bots[]`, `unrecognised_refusal[]` and `count_skipped_refusal` all came back
   empty and the summary read "2 reviewed" when one bot reviewed) — visible in **three** instruments.
   And pr-agent reads ABSENT because its ~22-minute response outruns `review_bot_buffer_seconds: 180`
   and it publishes no check-run, so `bot_completion` returns `no_check_name` and the buffer IS the
   whole wait; two consecutive FINDs recorded it absent, **each consuming a loop-back iteration**.
3. ⭐ **The in-house gate found the substance; the bots found lint.** Seven full-surface self-review
   rounds found **10 real defects pre-push** — every one a doc claiming something the code does not
   provide, *the same class this plan was written to fix*, including a recovery path unreachable from
   BOTH write-side callers. The three review bots contributed **one markdownlint MD038 nit**.
   ⛔ **The comparison carries a confound the plan itself names and this record keeps**: self-review
   runs at orders 5-7, so the bots reviewed a tree those 10 defects had already been removed from.
   This run does **not** measure whether they would have caught them.

## Reconciliation actions

- [x] row `status` → `shipped`; `pr` `1355`; `landing` `landings/PLAN-CIS-060.md`;
      `plan_marshall_plan_id` `verdict-field-read-and-write-integrity`
- [x] 9 inbox messages drained (8 candidate-lesson + 1 landing)
- [x] D13 discharged — see `epic.md`

## Follow-ups

⛔ **Plugin registry pin widened again**: `bootstrap_plugin resolve` → **`0.1.1556`** against a served
skill base dir of **`0.1.1544`** — now **12 versions** behind, widened by this landing's
`sync-plugin-cache` exactly as the per-landing leak predicts. Repair remains operator-only.

⚠ **Two tooling defects located in source by the run**, carried as leads: `git_provider.py`'s
`_DEFAULT_TIMEOUT_SECONDS = 60` with `cmd_worktree_remove` branching on `rc != 0` once — attaching the
same "verify the worktree is clean" hint to rc 124 (timeout), rc 127 and a genuine dirty-tree refusal,
where **a timeout leaves the worktree partially removed so the retry then reads dirty for a reason the
first attempt caused** (fired twice on this plan); and `pre-submission-self-review`'s round-scoped
`cohort_size` (`contract_drift` fired across four rounds for a cumulative 7 findings while the largest
published figure is 2 — the closed-cohort illusion the field exists to prevent).

⚠ **One open QUESTION, deliberately not asserted as a defect**: the cross-plan merge mutex was acquired
at the widened-hold point and released at the terminal site as `action: noop, lock not held (already
free)` with no intervening explicit release; the title token spans 51m10s, inside the 3600 s budget,
and no release payload appears in either log. A mutex self-releasing mid-hold would not be serializing
what it claims to — but the artifacts do not evidence the mechanism, so it stays a question.
