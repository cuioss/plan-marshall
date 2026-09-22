# PLAN-102: Post-merge review findings are untriaged and live in main

epic: truthful-signals
workstream: WS-01

> Staged plan spec — one shippable unit of work, ready for `/plan-marshall` hand-off.
> **Deliberately small: gather, verify, fix what survives.** See
> `persona-marshall-orchestrator/standards/orchestration-model.md` for the tier and hand-off contract.

## Objective

CodeRabbit reviews have landed **after** their PRs merged, so real findings were never triaged and are
live in `main`. Gather every such finding, verify each against the current tree, and fix the ones that
still hold. **This is debt cleanup, not a mechanism fix.**

⛔ **OUT OF SCOPE — the race itself.** *Why* a merge outruns its review belongs to **PLAN-92** (D4's
wait strategy), which is in flight. **Do not fix the timing, the wait, the gate, or the merge
sequencing here.** If this plan finds itself editing `automatic-review` or the merge path, it has
left its scope — stop and report instead.

## What is OBSERVED

Cross-epic handover from `test-suite-quality`, 2026-07-28:

- **#1036** — merged `16:42:47` (`a8cc8acef`); CodeRabbit posted **"Actionable comments posted: 5"** at
  `16:45:29`, **2m42s after the merge**, having reviewed the **final** tree
  (`741a1c99d..530e5face`, including the second commit). **All 12 PR comments remain unresolved.**
- **#1026** — same shape, review at **58 s post-merge**.
- Two consecutive occurrences ⇒ the mechanism is **causal, not coincidental**. Filed as lesson
  `2026-07-28-19-002`.

## ⛔ The two named PRs are a SAMPLE, not the population

**Do not scope this to #1026 and #1036.** This epic's most-recurring failure is exactly that — a named
list read as an enumeration, confirmed four separate times, most recently when #1038's sweep found 10
persist sites where the request named 5.

**D1 must derive the population**: enumerate recently-merged PRs and find every one carrying
review comments that arrived at or after merge time, or that carry unresolved review threads. The
comparison is **comment timestamp vs merge timestamp**, which is mechanical and cheap.

## Deliverables

1. **D1 — GATE: derive the population and gather (mutates no source).** Enumerate merged PRs in the
   affected window; for each, pull comments through `plan-marshall:tools-integration-ci:ci pr comments`
   (⚠ **never raw `gh`** — CI-abstraction rule) and select those whose review arrived at/after merge or
   whose threads are unresolved. **Report the PR count examined and the finding count separately —
   a count of PRs examined is a VOLUME, not coverage.** Produce a per-finding record: PR, file,
   symbol, the claim, and its current status.
2. **D2 — verify each finding against the CURRENT tree.** `main` has moved several merges since these
   reviews; a finding may already be fixed, may no longer apply, or may never have been valid. **Each
   finding is a LEAD, not a defect** — resolve by symbol, not by line number, since line numbers have
   drifted. Classify each: **still-valid / already-fixed / not-valid / needs-its-own-plan.**
   ⚠ **Bot suggestions have been wrong before** in this epic (#1009 shipped a bot-suggested wording
   that was itself incorrect and had to be re-corrected). Verify the claim, not the suggestion.
3. **D3 — fix what survives, and only that.** Apply fixes for `still-valid` findings whose remedy is
   small and local. ⛔ **Anything that is not small and local is reported, not implemented** — it
   becomes its own staged item. **A finding classified `needs-its-own-plan` is a successful outcome
   of this plan, not a failure.** Record the disposition of every gathered finding, including the ones
   deliberately not fixed.

Three deliverables. Small by construction — D3's size is bounded by D2's verdicts, not by D1's haul.

## ⭐ Added 2026-07-28 (cross-repo, API-Sheriff PLAN-25) — the stale-diff-range check D2 needs

A re-review can grade a **stale diff range** and produce a **Major** finding against
already-fixed code. Observed on API-Sheriff PR #123: a second bot pass graded a range that no
longer matched the PR head, and its Major finding described code that had already been fixed.

**This is the precise mechanism D2 needs, and it is stronger than "resolve by symbol":**

1. Read the bot's **reported reviewed range / reviewed commit** from its comment body.
2. Compare against the PR's **current head SHA**.
3. If the reviewed range does not include the current head, treat every finding from that pass as
   **PROVISIONAL** — it was graded against code that no longer exists.
4. Ground-truth each provisional finding against actual current file contents before triage. If it
   does not hold, dispose as `not_applicable` with the rationale *"bot reviewed stale range X..Y,
   current head is Z"*, and **do not fix**.

⛔ **Never let bot severity substitute for ground truth. A Major finding on stale code is worth
nothing — and the severity label is the part most likely to short-circuit the check.** That is
directly load-bearing here: this plan's whole population is findings graded against trees that have
since moved, so *every* finding it gathers is provisional by construction.

## Claim Labels

- OBSERVED (cross-epic handover, timestamps quoted): #1036's merge at `16:42:47` / review at
  `16:45:29`; #1026's review at 58 s post-merge; "Actionable comments posted: 5"; 12 unresolved
  comments on #1036.
- HYPOTHESIS: findings can still be dispositioned on a **closed/merged** PR — the triage path may
  assume an open PR, and `post_responses` behaviour against a merged PR is unverified.
  Confirm/refute at the `workflow-integration-github` `post_responses` seam (verify-at-outline).
  **If refuted, D3 records dispositions in the plan's own artifacts instead — do not leave them
  unrecorded.**
- HYPOTHESIS: the affected set is larger than the two named PRs — confirm/refute by D1's derivation
  (verify-at-outline). **An asserted absence would need proving; do not assume two.**
- Verify-first clause: re-read each finding against HEAD before fixing. A finding already closed by a
  later landing is `already-fixed` and MUST NOT be re-implemented.

## Expected Surface

- OBSERVED: read-side `plan-marshall:tools-integration-ci:ci pr comments` (D1, no mutation).
- HYPOTHESIS: **unknown at spec time — the fix surface is wherever the surviving findings point**
  (verify-at-outline). This is the defining risk below.
- OBSERVED: tests for whatever D3 changes.

**Disjointness: ⚠ UNKNOWABLE UNTIL D1 COMPLETES.** The fix surface is defined by the findings, so this
plan can land anywhere in the tree.

⛔ **Therefore treat it as LOW-COMPATIBILITY for pairing.** Prefer running it when few plans are in
flight, or **gate D3 on a disjointness re-check against the then-current in-flight set** — D1 and D2
mutate nothing and are always safe to run. If D2's verdicts point into an in-flight plan's surface,
**hand those findings to that plan rather than editing behind it.**

## Dependencies and Sequencing

- Depends on: none. D1/D2 are read-only and can run at any time.
- ⚠ Coordinate with: **PLAN-92** (in flight) — it owns the race that created this debt. This plan
  cleans up; that one stops the bleeding. Neither blocks the other, but **do not let this plan drift
  into fixing the cause.**
- Adjacent to: PLAN-85 (`tools-integration-ci`) — if D1 finds the `ci` read surface inadequate for
  timestamp comparison, that is a finding for PLAN-85, not a fix to make here.

## Hand-Off Command

```text
/plan-marshall task="implement .plan/local/orchestrator/truthful-signals/plans/PLAN-102-post-merge-review-findings-are-untriaged-in-main.md"
```

## Write-Boundary

The plan implementing this spec touches only its own repository source and tests. It creates and
edits NO file under `.plan/local/orchestrator/` other than its own `inbox/{sender}-{seq}` message —
the orchestrator owns every other ledger write — and reports its outcome through its PR and its inbox
message. See `persona-marshall-orchestrator/standards/orchestration-model.md`
§ Ledger Write-Boundary.
