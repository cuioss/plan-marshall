# PLAN-TRUTH-004: Invented `--plan-id` Flags Are A Correct Generalisation With One Carve-Out — Prose Cannot Fix That

> Renamed from **PLAN-85** on 2026-07-30 (see `plan-id-rename-map.md`).

epic: truthful-signals
workstream: WS-01

> Staged 2026-07-27 from **inbox message `orchestration-inbox-channel-002`** — the first plan spec in
> this epic sourced through the channel PLAN-55 shipped, rather than through a PR narrative.
> `component: plan-marshall:tools-integration-ci`, `category: anti-pattern`.

## Objective

`argparse_rejection` (exit 2) from invented plan-scoping flags accounted for **2 of the 4
script-failure clusters in a single plan's run**, in a workflow whose agents load the prohibiting rule
unconditionally. Make the failure structurally impossible or self-correcting, rather than prohibited
in prose that demonstrably does not hold.

## ⚠ Mechanism — the diagnosis is the valuable part, not the failure count

- OBSERVED (inbox `-002`, first-party plan report) — two rejections, same shape, not two typos:
  `plan-marshall:tools-integration-ci:ci checks status` invoked with an invented `--plan-id`
  (that verb is **repo/PR-scoped, not plan-scoped**), and a `manage-change-ledger` rejection on the
  same class of caller-model-vs-argument-surface mismatch.
- OBSERVED — the standing rule already names verb-scoped `--plan-id` as **recurrence signature #2**
  (`persona-plan-marshall-agent`), and **every agent in that workflow loads it unconditionally**.
- **⇒ The load-bearing insight: the caller is NOT guessing wildly — it is over-generalising a real and
  near-universal convention.** Nearly every `manage-*` verb IS plan-scoped and DOES take `--plan-id`,
  so the flag reads as **ambient boilerplate** rather than a per-verb declaration.
- **⇒ Therefore prose cannot fix this.** *"Don't invent flags"* asks the reader to suppress a
  correct pattern-match on the basis of a carve-out they cannot see from the call site. **A rule that
  every agent has loaded and that still fires twice inside one plan is not doing the work it claims
  to do** — which makes this a *vacuous-guard* instance in the documentation layer, the same family as
  the code-layer instances this epic tracks.

## ⚠ Third instance — cross-repo, and a SECOND sub-shape (folded 2026-07-27 from API-Sheriff PR #114)

A third `argparse_rejection` on the same surface family, this time from **another repo** (API-Sheriff
PR #114, merged) — which matters because D1(a) forbids scoping from one plan's run.

- OBSERVED (operator narrative, first-party): the phase-5 executor hit an argparse rejection on
  `manage-findings qgate add`, **continued past it**, and silently lost an escalation finding, costing
  an extra orchestrator round-trip. The reporting agent routed it to architecture hints because a leaf
  cannot file upstream.
- OBSERVED (this repo, first-party): the invocation surface is **sound** — `qgate add` is a real
  subcommand (`manage-findings/SKILL.md` § Canonical invocations → `qgate add`), `--phase 5-execute`
  is a valid `QGATE_PHASES` member (`tools-file-ops/scripts/constants.py:30`), and the documented
  phase-5 call at `phase-5-execute/SKILL.md:872-877` is conformant. **So this was NOT a stale doc.**
- **HYPOTHESIS — a SECOND sub-shape, distinct from the invented-flag shape above: a closed enum with
  no member expressing the caller's intent.** `--type` is `required=True, choices=FINDING_TYPES`
  (`manage-findings.py:380`) and `FINDING_TYPES` (`constants.py:96-121`) has **no `escalation` member**
  — the lost finding was described as an *escalation*. A caller needing to escalate has no admissible
  `--type`, so any value it picks is an exit-2. Confirm/refute artifact: the API-Sheriff plan's
  `.plan/archived-plans/2026-07-27-benchmark-health-target/` script log — the recorded **argv and
  stderr** of the failing call. **Verify-at-outline; do NOT implement against this hypothesis unless
  that argv confirms it.** If refuted, the instance still counts toward D1(a)'s corpus as an
  unclassified exit-2.
- ⇒ **Consequence for D1.** If the enum-gap shape is confirmed, "don't invent flags" is not merely
  unpersuasive here — it is *unfollowable*: the caller's intent has no admissible encoding, so the
  remedy is a surface question (does the escalation concept need a type, or a different channel?), not
  a discipline question. That strengthens the spec's existing bias away from another prose rule.
- ⚠ **The silent-loss half of this instance is NOT in this plan's scope** — it is folded into PLAN-TRUTH-010
  as a new open fail-open instance. This plan owns why the call was *rejected*; PLAN-TRUTH-010 owns why the
  rejection was *survivable*.

## ⭐ FOURTH INSTANCE — the orchestrator caught itself, 2026-07-27

Recorded because it is first-party and unusually clean evidence for two of D1(c)'s candidate remedies.

- OBSERVED: while verifying the PLAN-80 landing, the **orchestrator itself** invented
  `ci pr status --pr-number 1021`. The real verb is `pr view`; argparse rejected it with a bare
  `invalid choice` listing 19 alternatives. Same mechanism as the founding instances — a correct
  pattern-match (`status` is a verb elsewhere in the surface) over-generalised to a verb that lacks it.
- OBSERVED, and **directly on point for D1(c)**: `ci pr view --help` documents
  `--head HEAD  Source branch — alternative to --pr-number for branch-identified lookups`, but
  **`pr view` does not declare `--pr-number`** — invoking it fails at the top-level parser with
  `unrecognized arguments: --pr-number 1021`. **The verb's own help text advertises a flag the verb
  does not accept.** This is exactly the "a doc advertising a flag a verb does not declare" case D1(c)
  lists as a candidate plugin-doctor check — no longer hypothetical, and found without looking for it.
- **⇒ Two consequences for D1.** First, the corpus mined in D1(a) should include **help-text-vs-declared-flag
  divergence**, not only rejected invocations: a caller misled by accurate-looking help is not making a
  guess, and no amount of caller discipline fixes it. Second, this instance argues the actionable-error
  remedy and the doctor-check remedy are **complements, not alternatives** — the error catches the
  caller, the doctor check catches the document that misled them.

## Deliverables

### D1 — GATE: measure the real shape, then choose a structural remedy over a stronger rule (mutates nothing)

(a) **Quantify.** Mine the script-failure corpus for `argparse_rejection` exit-2 events and classify:
how many are invented `--plan-id` on a non-plan-scoped verb, how many are other invented flags, how
many are **closed-enum values with no member matching caller intent** (the API-Sheriff sub-shape
above), how many are genuine typos. **Do not scope from n=2**; the inbox message is one plan's run —
the corpus is now n≥3 across two repos, which is still too small to scope from.
(b) **Determine which verbs are the carve-out** — enumerate the non-plan-scoped verbs across the
`manage-*` / `ci` surface. If that set is small and stable, the convention is nearly-total and the
remedy differs from the case where it is large and arbitrary.
(c) **Choose the remedy, with an explicit bias AWAY from another prose rule.** Candidates, cheapest
first: an **actionable argparse error** that names the correct invocation for that verb (turning a
dead exit-2 into a self-correcting one); **accepting-and-ignoring** `--plan-id` where it is harmless;
making the plan-scoping property **visible at the call site** (notation or doc convention); or a
plugin-doctor check that flags docs advertising a flag a verb does not declare. ⚠ **Adding emphasis to
the existing rule is an explicitly REJECTED option** unless D1 argues why this instance differs — it
has already failed at n≥3.

### D2 — implement the D1 remedy

Scoped to whatever D1 selects. **Hard constraint: no verb's real argument surface may be widened
merely to absorb the mistake** unless D1 decides accept-and-ignore *is* the remedy and records the
trade — silently accepting a meaningless flag trades a loud failure for a quiet one, which is this
epic's own anti-pattern.

### D3 — tests

(a) The exact failing invocation from the inbox message (`ci checks status --plan-id …`) produces
D1's chosen behaviour — **verified to produce a bare exit-2 against current code**. (b) A correct
invocation is unaffected. (c) If D1 adds a doctor check, a doc advertising a non-existent flag is
flagged and a correct doc is not.

Three deliverables (D1 a gate) — well under the split guard. **Deliberately small**; the value is in
D1's diagnosis, not in volume.

## Expected Surface

- HYPOTHESIS: `tools-integration-ci` `ci` argparse surface — the `checks status` verb
  (verify-at-outline).
- HYPOTHESIS: `manage-change-ledger` argparse surface (verify-at-outline).
- HYPOTHESIS: shared argparse/error-emission helper, if one exists — the natural home for an
  actionable rejection message; **confirm a shared seam exists before assuming it**.
- HYPOTHESIS: `pm-plugin-development:plugin-doctor` — only if D1 picks the doc-check remedy. Note
  `recipe-fix-argparse-rejection` already exists as a **remediation** recipe; this plan is
  **prevention**, so confirm no overlap rather than duplicating it.
- OBSERVED: inbox message `.plan/local/orchestrator/truthful-signals/inbox/orchestration-inbox-channel-002.md`
  — read-only; the orchestrator drains it, the plan does not edit it.

**Disjointness:** `tools-integration-ci` + possibly `plugin-doctor`. Disjoint from PLAN-79
(`platform-runtime`), PLAN-80 (`workflow-integration-github`), PLAN-81 (`pm-plugin-development`
self-review — ⚠ **overlaps if D1 picks the doctor remedy**; re-check then), PLAN-82/83, PLAN-84.

## Dependencies and Sequencing

- Independent; no gate.
- ⚠ **Re-check against PLAN-81 at outline** — both may land in `pm-plugin-development` if D1 chooses a
  doctor check. Different rule, same bundle.

## Notes

- **Provenance is itself notable**: this is the first spec in the epic sourced from the inbox channel
  rather than a PR narrative — evidence the channel carries content worth acting on, and an argument
  for PLAN-56 (the drain) landing soon so this stops being manual.
- Theme fit: a *documentation-layer* vacuous guard. The rule exists, is loaded, is correct, and does
  not fire in the reader's head at the moment it is needed — which is indistinguishable, in outcome,
  from a predicate that cannot fire.

## Two `tools-integration-ci` / argparse findings

Message-supplied, HYPOTHESIS until re-verified at outline. Both are in this plan's own surface.

**(a) `check_auth_cli` reports "Not authenticated" for EVERY non-zero exit — including a missing
binary.** Observed live on #1037: the real cause was a `gh` **PATH** problem, and the diagnostic named
authentication. **A misattributed diagnostic is this epic's archetype inside an error message** — the
verdict is confident, the caveat (we do not actually know why the call failed) is suppressed, and it
sends the operator to the wrong fix. Distinguish *binary absent* from *present but unauthenticated*,
and **fail with an unknown-cause state rather than guessing** when neither can be established.

**(b) Four argparse rejections in one run, all matching already-documented recurrence signatures.**
The argparse/notation-drift archetype is already tracked and `recipe-fix-argparse-rejection` already
exists — so four rejections in a single run means the documented signatures are **not reaching the
point of use**. ⚠ The deliverable is not another signature list: ask why documented recurrences keep
recurring, and treat a fix that only adds documentation as insufficient.

⭐ **THE CAUSE OF (a), from #1038 — dispatched leaves get a TRUNCATED PATH.** `gh`/`ci` failures in a
dispatched leaf are therefore not auth failures at all; the binary is unreachable. **This supplies the
mechanism (a) was missing:** `check_auth_cli` reports "Not authenticated" because the call fails, and
the call fails because `gh` is not on the leaf's PATH. **Fix both ends** — the diagnostic must
distinguish unreachable-binary from unauthenticated, *and* the leaf PATH truncation is a real defect
in its own right. ⚠ Do not fix only the message: a correct diagnostic for a broken environment still
leaves dispatched CI calls failing.

⚠ **Orchestrator-observed, same family (2026-07-28):** `ci pr view` rejected `--pr-number 1038` while
accepting `--head` in the same session. Whether that is a real surface gap or an invocation error on
my part is **unsettled** — verify before acting on it.

## Write-Boundary

Repository source + tests only. NO writes to `.plan/local/orchestrator/` **ledger state**
(`status.json`, `epic.md`, `plans/`, `landings/`); the `inbox/` channel is the sanctioned exception
for orchestrated plans. See `persona-marshall-orchestrator/standards/orchestration-model.md`
§ Ledger Write-Boundary.


---

## ⚠⚠ NO CLAIM LABELS — EVERY CLAIM IN THIS SPEC IS UNLABELLED (recorded 2026-08-09, full-corpus review)

This spec predates the verify-first contract and carries **no `## Claim Labels` section**. The contract
requires every serialized premise to be marked `OBSERVED` or `HYPOTHESIS`, with a `HYPOTHESIS` naming
the file **plus the symbol** that settles it.

⛔ **Labels were NOT retrofitted here, deliberately.** Assigning `OBSERVED` to a claim this orchestrator
did not observe would manufacture provenance — the precise defect the contract exists to prevent, and
worse than the missing section, because a wrong label reads as a checked one.

⇒ **Until outline labels them, treat EVERY claim in this spec as `HYPOTHESIS`**, including its counts,
its file lists, and any asserted *absence*. ⭐ **Asserted absences are the higher-risk half**: an
unverified "X does not exist, build it" produces duplicate work against a surface that already exists,
and nothing downstream trips over it. **Outline owns the labelling before any deliverable is sized.**
