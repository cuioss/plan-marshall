# Landing: PLAN-PR-008 — Review barrier deadlocks on a refusing bot

epic: review-apparatus · workstream: WS-04 · shipped 2026-08-15
cloud run: `cloud-runs/120-review-barrier-deadlocks-on-a-refusing-bot/`
PR #1241 (`9e9e98800`) — *"a size-capped reviewer is no longer offered a non-option"*

> Landing analysis over the cloud-wave corpus. `report-01.md` is the run's claim; `verification.md`
> is ground truth. Where they disagree, verification wins.

**Verification verdict: `verified-with-gaps`.**

## The pre-run refutation was honoured

Two of the epic spec's three deliverables were confirmed already shipped before the run — "distinguish
refused from unproven" (shipped via `rate_limit_class`) and "a sanctioned recorded coverage-gap
acceptance" (shipped, HEAD-bound, gap-class-bound, fail-closed). **The run re-implemented neither**,
and restated the real subject — *the refusal taxonomy had no STRUCTURAL member* — in the report's
second line. The misleading slug was kept, correctly (never rename a launched plan).

## What landed

`refused_structural` is a first-class taxonomy member decided by an observed `cause` that dominates the
per-bot `rate_limit_class`; the cap is read from the notice (never declared) and paired with a
`measured_diff_size`; the pre-merge barrier renders split / accept / disable with no wait and no
re-triage, behind an 81-test suite.

**Deliverables: 3 numbered + 1 starred sub-clause — 2 done (D0, D2), 2 partial (D1, D1⭐), 2 refuted
pre-run.**

## ⛔ The defect D1 exists to remove is live for a bot in the tree today

The leaf's opt-in recovery **Branch 0 branches on a `cause` that neither producer feeding it emits**.
`_detect_rate_limited_bots` emits `{bot_kind, rate_limit_class, eta}`; `_refusal_record` emits
`{source, bot_kind, layer, eta, body}`. Neither carries `cause`. A Sourcery size refusal therefore
falls to Branch 1 and is offered *"Wait another {review_rate_window_timeout_seconds}s"* — non-option
pairing #1, the exact defect D1 was written to remove. Gated only by `review_rate_window_await`
defaulting to `false`.

**Standing rule: "not reachable on the default configuration" is a disclosure, never a closure.** An
operator may flip it, and Sourcery already declares both the size pattern and `hard_quota`.

## Report claims the verification found false

- D1 conjunct 3 "Now closed at both layers" — the leaf layer is **prose-only**; the fix cannot fire
  from the data the section names.
- The SKILL sentence the run relies on — "Both carry the same discriminators … the refusal's `cause`
  … plus … the stated `cap`" — is **false** (the two producer return literals above).
- F29's deferral bound "no registered bot declares `rate_limit_eta_patterns`" — **refuted**;
  `coderabbit.md:57-60` declares three.
- Mutation table row A "7 failures, all in case (a)" — a re-run yields **9**, one of them in case (c).
- "One row per INSTANCE, never bundled" — broken four times in the section that states it. `F8–F20` is
  labelled "Thirteen" against **fifteen**; `F30–F36` "Seven" against **eight**.

## Gaps: 11 — 10 full, 1 partial, 0 uncovered

- **partial**: G2 — the crash fix and its tests are covered by PLAN-PR-025 D1, but correcting F29's
  *false stated reason* in the report is out of scope there and is listed by **no** 5NN plan. A routing
  hole, not a judgement call: it belongs as a ninth item in PLAN-PR-031 D2.

## Standing facts

- ⭐ **Never trust a count written beside a table.** This report went through four consecutive fixes of
  the same defect (F64→F72→F78→F79), each restating a literal the next row invalidated, and *still*
  landed with two miscounted bundles. F78 named the durable repair — do not state a count beside a
  table at all — and correctly declined to make it.
- ⭐ **`ten` and `eleven` are both correct for this taxonomy, over different populations.** Eleven
  `STATE_` constants; ten non-participation members (the contract's closure sentence); nine in
  `_UNPROVEN_STATES`; nine display buckets over eleven states. Every count claim must name its
  population or it reads as drift.
- ⛔ **A defaulted-off knob hid a live defect through six review rounds.**
