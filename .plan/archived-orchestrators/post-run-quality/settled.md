# post-run-quality — settled narrative

Relocated from `epic.md` by `cleanup` Phase B. Bodies are verbatim.

## Cross-epic collision: PLAN-TRUTH-175/174 vs PLAN-PRQ-08/01

- **Two NEW staged `truthful-signals` specs materially overlap PLAN-PRQ-08 and PLAN-PRQ-01, invisible to
  either ledger.** Found 2026-09-22 during A1 re-grounding corroboration. `PLAN-TRUTH-175-dispatch-and-
  phase-boundary-measurement-integrity` (staged) declares D2/D3 = the same dispatch-boundary token
  recording and four component token columns PLAN-PRQ-08 claims 5/7 own, with the OPPOSITE stated root
  cause (-175: "the recorder does not capture them, fix the recorder" vs PLAN-PRQ-08/`truthful-signals`
  PLAN-TRUTH-160: "the recorder declares all four flags, the call sites pass nothing, fix the call
  sites"), and D5 = the identical `manage-change-ledger`/build-time-oracle investigation PLAN-PRQ-08 claim
  6 owns. `PLAN-TRUTH-175` itself records "Overlaps with: none known against the current live queue" —
  that statement is made against its own ledger only, so the sole-ownership reading on either side is not
  safe. `PLAN-TRUTH-174-plan-retrospective-measurement-integrity` (staged, same-source sibling) is an
  adjacent candidate collision with PLAN-PRQ-01's `plan-retrospective/**` surface, not yet corroborated in
  detail. — resolve before either PLAN-PRQ-01 or PLAN-PRQ-08 is emitted: read `truthful-signals`'
  PLAN-TRUTH-174/-175 spec bodies in full and either fold/cross-reference or explicitly partition the
  overlapping deliverables between the two epics.

## Resolved defects

Relocated from `epic.md` by `cleanup` Phase B, 2026-10-07, on operator
confirmation. Bodies are verbatim.

- ✅ **RESOLVED 2026-10-07 — both inbox defects fixed and merged as PR #1700 (`78ba60f41`); issue
  [#1697](https://github.com/cuioss/plan-marshall/issues/1697) is closed.** ⚠ **Verified behaviourally on
  this epic's own queue, not from the landing report** — which is the right test, because this epic's
  inbox is the exact state both defects were found in.
  - **Closure now survives the drain.** `inbox list` reports `count: 0`, `live_count: 0` and
    `closed_senders: [cross-repo-telemetry-archive-and-analyze]` — the sender is named **with its marker
    archived**, where before the fix this read `closed_senders: []`. The FINISHED zero is reachable after a
    complete drain, which is precisely what the issue said was impossible. ⭐ **The fix also added a
    coverage discriminator nobody asked for**: `archive_readable: true`, so an archive that could not be
    scanned can never masquerade as *"no closed senders"* — the honest-zero discipline applied to the fix
    itself.
  - **`restart-check` now names the zero, not just the count.** Its inbox row reads
    `ready, "FINISHED: 1 sender(s) closed (cross-repo-telemetry-archive-and-analyze) with no live
    message", "inbox/: 0 live of 0 total and 1 closed and 0 invalid"`. ⭐ **That exceeds the remedy the
    issue proposed** — it was asked to score on `live_count` and report the neighbours; it reports the
    state by its vocabulary word with the whole population spelled out.
  ⚠ **One observation from the fixing run, recorded as an instance rather than a complaint**: its own
  `record-metrics` step reported **`40h31m / 0 tokens`** with every phase blank in the Phase Breakdown. A
  measured `0` over an unread population — the founding defect of this epic — in the run that fixed two
  instances of it. Exactly what `PLAN-PRQ-13`'s reports would classify `not_measured` rather than zero.
  ⚠ The run also filed 4 `process-compliance` findings (`issue-1697-001`..`-004`), **including one against
  itself** for holding the merge lock across operator waits. Found by draining this epic's last message. Before the
  drain the queue read `live_count: 0` with `closed_senders: [cross-repo-telemetry-archive-and-analyze]` —
  the **FINISHED** zero, meaning *that sender will send no more*. Archiving the marker, which is exactly
  what the drain contract prescribes for a `stream-end` row, moved it to `count: 0` with
  `closed_senders: []` — the **EMPTY** zero, which asserts *a later message is still possible*. ⛔ **So a
  closure declaration is either queued-and-undrained or archived-and-no-longer-declaring; there is no
  state in which it is both recorded and consumed.** The envelope doc states the mechanism ("a marker the
  drain has already archived no longer closes the stream") without naming the consequence: a drained queue
  **cannot** report FINISHED, so the three-zero vocabulary's middle value is unreachable after any complete
  drain. ⚠ Harmless for this instance — the sender is a landed, archived plan that can never write — but it
  means `inbox write` would no longer refuse that sender with `stream_closed`. ⇒ **Not owned here**;
  `plan-orchestrator` inbox mechanics, same family as the two defects below.
- ✅ **RESOLVED 2026-10-07 by PR #1700 — see the entry above for the verified behaviour.** The account
  below is retained as the evidence trail: it is how the defect was found, and it carries the warning that
  the green verdict after the 2026-10-05 drain was **not** resolution — which remained true for two days,
  until the signal itself was fixed. ⛔ **The original entry read:** `cleanup restart-check`'s inbox signal
  reads `count`, not `live_count`, so a stream-end marker holds an epic at `not_ready` forever. ⚠ **STILL
  REAL after the 2026-10-05 drain, and the drain did not fix it.** Archiving the marker cleared the *instance* — the verdict is now `ready` with
  `inbox: 0 queued and 51 archived` — but the defect is in the signal, not in the queue: any `stream-end`
  marker filed and not yet drained will hold its epic at `not_ready` again, and a FINISHED queue is by
  definition one that still holds its marker. ⛔ **Do not read the green verdict as this defect being
  resolved.** Found by this epic's own cleanup pass:
  `restart-check` returns `verdict: not_ready` on a single signal — *"1 message(s) still queued"* — and that
  message is the `lifecycle=stream-end` marker filed on the landed `cross-repo-telemetry-archive-and-analyze`
  plan's behalf. `inbox list` reports the same queue as `count: 1, live_count: 0, closed_senders: [that
  sender]` — the **FINISHED** zero. ⭐ **So the readiness instrument cannot tell which zero it is looking
  at**, which is this epic's founding subject reproduced in the instrument that grades restart-readiness.
  ⛔ **The marker was NOT archived to clear the signal.** Archiving it would delete the closure record —
  the inbox contract is explicit that a marker the drain has archived no longer closes the stream — and
  gaming a readiness signal by removing the thing it misreads is precisely the move this epic exists to
  catch. The `not_ready` verdict therefore stands, honestly, on a defect in the signal rather than on
  unfinished work. ⇒ **Not owned here** — `plan-orchestrator` mechanics, in the same family as the
  `registry_parity` row that already reports `not_available` and names another spec as its owner. Small and
  concrete: read `live_count` and `closed_senders` instead of `count`.
- ✅ **RESOLVED 2026-10-04 — `PLAN-PRQ-13` emitted, gate overridden on a stated basis, and my own
  characterisation of it corrected.** ⛔ **The correction first, because it is the substantive part:** I
  told the operator this was a *weaker* override case than PRQ-07's, on the strength of the ~45 overlap-row
  count. Separating the rows by class shows it is **comparable, and arguably safer**. PRQ-07 also carried a
  large sibling-epic-spec volume (186 rows) with zero live-plan overlaps and in-corpus overlaps only against
  parked or shipped siblings; PRQ-13 has **zero** live-plan rows, **one** in-corpus row (`PLAN-PRQ-01`,
  parked), and ~40 sibling-ledger rows. ⭐ **The real difference runs the other way**: every PRQ-13 overlap
  is driven by ONE declared path, `manage-findings`, which the spec declares a HYPOTHESIS — so if it
  resolves false the in-repo surface is **empty** and the collisions do not exist. PRQ-07's surface was
  unconditional. A row count compared across two candidates without separating its classes is exactly the
  under-derived figure this epic exists to catch, and I published one. ⇒ The emitted spec carries the
  override, its basis, and a concrete obligation: settle the `manage-findings` hypothesis at D0/outline
  before touching that file, and re-check the live plan set if it resolves true.
- ⚠ **SUPERSEDED by the entry above — the original gate-refusal record for `PLAN-PRQ-13`.** `candidate_comparison_determinate: false` again (96 sibling-epic specs and 3 live plans
  declare no comparable surface), so the test fails closed. ⛔ **But unlike PRQ-07, PRQ-13 DOES have overlap
  rows** — roughly 45 of them, including `PLAN-PRQ-01` in this corpus and ~40 sibling-epic specs across
  `review-apparatus`, `truthful-signals` and others. ⭐ **Every one of them is driven by a single path**,
  `manage-findings`, which PRQ-13 declares as a **HYPOTHESIS** — it is only in scope if D4's three new
  mechanisms need a producer-side vocabulary change rather than reading-side classification. The other four
  declared entries are `plan-marshall-telemetry/` paths the parser reports as **unresolved** (4 unresolved
  spans, 1 resolved path), because they are outside this repository. So the honest statement is: *if the
  hypothesis resolves false, this plan has no in-repo surface and collides with nothing; if it resolves
  true, it joins a crowded file.* The gate cannot express a conditional surface. ⇒ Emit decision is the
  operator's; D0 and outline settle the hypothesis either way.
- ✅ **RESOLVED 2026-10-02 — #1641 reverted this epic's ledger state.** Filed as
  `process-compliance-001.md` (2026-09-28), corroborated first-party and repaired the same session; the
  full account is the 2026-10-02 Decisions entry. Retained as the record of why `settled.md`,
  `inbox/archive/review-apparatus/review-apparatus-001.md` and the ten SUPERSEDED banners have a
  restore commit (`13e3d2426`) in their history rather than a continuous one. ⇒ **The mechanism remains
  unowned by this epic**: a stale-branch squash merge silently reverting a newer landing, unflagged at the
  merge gate, is orchestrator/merge-queue mechanics. Second observed instance (`process-compliance`
  restored its own tree the same way), so it is a recurring class, not an accident.
- ✅ **RESOLVED-AS-REFUTED 2026-09-17, and re-staged on its true mechanism as `PLAN-PRQ-06`** (operator
  reported the same observation independently; analyzed the same day). The entry as filed read: *"either
  the lane resolution does not drop a non-ceremony step at `off`, or the landing's step list is not
  derived from the composed manifest."* ⛔ **BOTH readings are refuted**, and the refuting evidence is
  retained here per the standing convention:
  - `_manifest_lanes.py:171-172` + `:37` — an `off` on a `core` / `derived-state` element is **immune by
    contract**, documented in `ext-point-lane-element.md:50-51, 70, 90`. `lessons-capture` declares
    `lane.class: core`, the same class as `push` / `create-pr` / `branch-cleanup`.
  - The archived plan's `execution.toon` composed the step (lines 33, 84, 118) and recorded it `executed`
    (line 158); its `logs/decision.log` entry `4a5900` carries the neutralization warning verbatim. **The
    landing told the truth.**
  ⇒ The real defect is that the neutralization is invisible to the operator — both config writers validate
  the lane value space and never read the element's class, and the one honest record is a compose-time log
  line inside a plan directory that is then archived. Owned by **PLAN-PRQ-06**.
  ✅ **SHIPPED 2026-09-19, PR #1541 (`a1dd4901f`).** All 7 deliverables (D0-D4, D3a, D2a) landed —
  write-side refusal, read-side surfacing, `lessons-capture` reclassified `core → prunable` (the
  2026-09-17 operator ruling), and the manifest now carries the effective lane with the requested value
  preserved separately. See `landings/PLAN-PRQ-06.md` for the full reconciliation.

## Retired watches

Relocated from `epic.md` by `cleanup` Phase B, 2026-10-07, on operator
confirmation. Bodies are verbatim.

- ✅ **RESOLVED 2026-10-05 — the reports have now run in anger, on two projects, and the run vindicated the
  Watch.** Verified first-party in the telemetry repo: `bcd0da5` transferred **70 archived plans and 16
  orchestrator records**, `83d1e93` committed the first fully-adjudicated reports, and `reports/` now holds
  both `plan-marshall` and `cui-http`, each with a `project-report.adoc` plus monthly variants. ⛔⛔ **The
  first real run found false measured zeros that 924 green tests did not**: `eab509f` records that a
  recorder placeholder `total_tokens: 0` is no figure — **11 plans carried a measured 0** — and that
  `main_context_tokens` must be `not_measured` with no phase figure and a floor when a phase is
  unclassified — **45 plans carried a measured 0**. ⭐ **This is the strongest single argument this epic has
  produced**: the reports shipped with the exact defect class the epic exists to eliminate, their own test
  suite could not see it, and only real data exposed it. A fixture corpus cannot contain the shapes a real
  corpus has.
- ✅ **RESOLVED 2026-10-05 (operator) — the `.adoc` has been read.** ⚠ **Closed on the operator's word, and
  that is the right evidence here**: the question was never whether the file exists (it does, 8 of them)
  but whether a human had seen it rendered, and only the operator can answer that. No renderer is recorded
  in the repo, so this is operator-confirmed rather than first-party-verified, and the ledger says so.
- ✅ **RESOLVED 2026-10-05 — the tokens zero-floor is fixed**, by `eab509f` above, with the affected
  populations named (11 and 45 plans) rather than merely asserted. It was the third rediscovery of this
  shape; it did not need a third plan.
- ✅ **RESOLVED 2026-10-04 (operator) — and this Watch named the WRONG REPOSITORY, which is the part worth
  keeping.** The durable finding stands: `plan-marshall:automatic-review` `lane: off` only stops *reading*
  results and is **not a bot off-switch**, so opting out of the lane and disabling a bot are different acts.
  ⛔ **What this Watch got wrong**: it proposed disabling CodeRabbit, Sourcery and cuioss-review-bot for
  `cuioss/plan-marshall`. The operator's ruling is the opposite — *"do not change anything related in this
  repo (plan-marshall). There the bots are correct."* Disabling was only ever wanted in
  **`cuioss/plan-marshall-telemetry`**, and it is **done**: CodeRabbit via that repo's `.coderabbit.yaml`
  (`reviews.auto_review.enabled: false`, commit `b403805`), Sourcery via the operator's dashboard, and
  `cuioss-review-bot` never ran there for want of a `.github/` tree. ⚠ **Recorded as operator-confirmed,
  not independently verified** — a GitHub App's installation state is not readable through the CI
  abstraction from here; the `.coderabbit.yaml` is. ⛔ **The standing rule is untouched and still binds:
  CodeRabbit is a required reviewer in `plan-marshall` and must never be moved to `optional_bots` to clear
  a blocked merge gate.** ⇒ The lesson for this epic is about its own practice, not the bots: an owed item
  carried a target repository it had never checked, and it was restated twice — including in a resume
  anchor as "overdue" — before anyone corrected it. **Name the repository a change targets before
  proposing it.**
