# Landing Analysis: PLAN-CIS-048 — LSP and derivation-resolver correctness

epic: code-intelligence-substrate
workstream: WS-07
pr: 1321
merge_commit: `cdf8062`, `7f36c76`, `3331bfa`, `8f468a4`, `a230637`, `9d375df`, `573580c` (squashed)
lane: cloud-plan-lane (the `doc/plans/` export wave; NOT the plan-marshall lifecycle, so no `plan_marshall_plan_id` exists)
artifacts: `cloud-runs/500-lsp-and-derivation-resolver-correctness/` — `plan.md`, `report-01.md`, `proposals.md`, plus `verification.md`, `gaps.md` and `adversarial-review.md` **produced during the 2026-08-22 ingest**

## Outcome

**completed** — 6 of 6 deliverables shipped, every core mechanism confirmed at `file:line` against
HEAD. Post-run audit verdict: **CONFIRMED WITH GAPS, INCLUDING TWO HIGH-SEVERITY ONES**.

This is the first of the eight `5xx` remediation plans and the only plan in the whole epic that ran
without a post-run audit. **That audit was performed during this ingest**, in the same two stages the
other 36 received: an independent verification, then an adversarial pass by a reviewer that had not
produced it.

⛔ **The first-pass audit returned `6 of 6 confirmed, zero high-severity gaps, no false report claims,
no vacuous guards`. The adversarial pass overturned it.** That outcome is not an anomaly — it is the
epic's base rate holding: **all 37 audited plans returned *sound after correction*; none returned
sound as written.**

## Premise verdict

The plan's premises held, and its deliverables landed as claimed. The report's own header records the
verification loop exiting **`budget-exhausted, non-converging`** — the state in which a run's
self-assessment is least reliable — and the audit was weighted accordingly. The deliverables survived
that scrutiny; **the run's summary judgement about its own residue did not.**

Two specific claims were independently confirmed:

- **D5's frame fix is real.** The report honestly discloses that D5's title clause was **FALSE until
  round 8** — `9d375df` guarded the handler, not the frame, so every malformed frame still ended the
  session silently. Verified by reading the pre-fix blob directly: `read_message` returned `None`
  uniformly for every malformed shape. At HEAD the `FrameError` boundary exists and its
  seven-shape subprocess-driven test **would fail against pre-round-8 code for exactly the claimed
  reason**, not incidentally.
- **Round 11's `setup.cfg` remedy is correct at HEAD** — interpolation on, every `parser.get()` inside
  the `try`, metadata committed only after full success. ⚠ It still carries **no execution-based
  verification** — three independent passes have now checked it by code reading only, and all three
  disclose that honestly.

## Gaps carried out of this landing

**7 total — 2 high, 2 medium, 3 low.** High: G1 (re-rated), G6 (re-rated).

⛔ **Both high-severity gaps were created by the adversarial pass, one by re-rating and one by
measurement the first audit deferred.**

- **G1 — a surviving false-clean path the run itself named, and the audit erased.** The report states
  verbatim: *"None of these can produce a false clean success — the class this plan exists to
  eliminate — **except S1**, which is bounded to line endings."* S1 is a CRLF line-ending rewrite in
  which rollback reports `rolled_back: true` while the restored bytes provably differ from the
  pre-edit bytes. The first audit **confirmed S1 present and then asserted that none of the twelve
  survivors can produce a false-clean success** — contradicting the source three lines away.
  Re-rated **low → high**: a false `rolled_back: true` in a live return payload outranks a
  documentation inconsistency.
- **G6 — the npm whole-tree abort, now measured.** The first audit named this the biggest risk and
  left its blast radius unmeasured; the adversarial pass measured it. A malformed (array- or
  string-shaped) `package.json` at the project root **or at any single workspace member** raises an
  uncaught `AttributeError` inside `discover_npm_modules`, **losing every npm module's discovery in
  the project, not just the malformed one** — the same blast radius as the Python `setup.cfg` defect
  this same run rated high and fixed as its worst finding. The gap entry's own stated escalation
  trigger is therefore met. Re-rated **medium → high**.
- **New medium — S8, a second false-clean-capable survivor.** A malformed `documentChanges` entry is
  silently dropped by `normalize_changes` with no note appended, so the whole-refusal gate (which
  fires only on a non-empty `notes[]`) never trips and the verb reports `status: success` over an
  edit that silently omitted part of the `WorkspaceEdit`. **S8 was absent from the first audit's
  sample entirely.**

## Inconsistencies found, and what was verified

- First audit's *"none of the twelve survivors can produce a false-clean success"* | verified against
  the run report's own `except S1` carve-out and by direct code read | **verdict: false on the
  audit's own cited source.** The report disclosed one false-clean survivor explicitly and a second
  (S8) implicitly; the audit's summary erased the first while citing it as confirmed-present.
- G6's blast radius, deferred as unmeasured | verified by reading `_npm_cmd_discover.py`
  (`_load_package_json` returns any parsed JSON value, not just dicts; `_resolve_workspaces` calls
  `.get()` on it unguarded; the per-member loop has no `try`/`except`) | **verdict: whole-project
  abort confirmed.**
- ✅ **No fabricated findings, and no wrong counts.** The validator-figure drift between `plan.md`
  (61/5081) and `report-01.md` (61/5083) is expected re-derivation, correctly handled.

## Residue

**The first audit's sample was narrower than its verdict implied**: of the 12 disclosed behavioural
survivors it cited as evidence for zero false-clean risk, it independently code-checked **only 2**
(S1 and B2) and took the other ten on the report's word. The adversarial pass checked two more (S8,
S9). **Eight survivors (S2–S7, S10–S12 less those checked) remain un-re-verified by anyone.**

The CI-portability figures remain unreproduced by **three** independent passes — the run's own round
5, the audit, and the adversarial review — a three-deep coverage hole. All three disclose it.

## Reconciliation actions

- [x] row `status` -> `shipped` — seeded with the row (this plan had no prior ledger row)
- [x] row `pr` stamped `1321`
- [x] row `landing` stamped `landings/PLAN-CIS-048.md`
- [x] the missing post-run audit **performed and archived** alongside the plan's own artifacts
- [ ] `plan_marshall_plan_id` — deliberately empty; cloud-lane plan

## Follow-Ups

- **G1 and G6 are both high and both live.** They route to **PLAN-CIS-053** (`550`, test-suite
  anti-vacuity) for the false-clean survivors and to **PLAN-CIS-049** (`510`) for the npm discoverer
  abort — the latter is the same *discoverer misreports a missing capability* class as
  PLAN-CIS-004's G1/G10, and belongs in one window with them.
- **The eight unchecked survivors are recorded as a known coverage hole**, not as a clean result.
- ⭐ **The method result is worth more than the findings**: a first-pass audit that reports *no false
  claims found* is, in this corpus, the least likely outcome — and here the disproof was sitting in
  the audited document's own text. **Never accept a clean first-pass audit in this epic without the
  adversarial pass.**
