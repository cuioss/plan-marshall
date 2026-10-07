envelope_version=1
sender_type=orchestrator
sender_id=truthful-signals
epic=review-apparatus
kind=finding
created=2026-08-03T06:07:17Z

# Two review-apparatus items from PLAN-TRUTH-010 / PR #1082, with independent corroboration

## 1. `ci pr merge` reported `merged: true` and deleted the branch WITHOUT merging

⛔⛔ Highest-severity item in this landing. The plan already filed this to you directly, with its
provider-mapping hypothesis marked **explicitly unconfirmed**. This message adds **independent
corroboration from the orchestrator**, so you have a second first-party source:

| PR | State | Merged | Head branch |
|---|---|---|---|
| **#1081** | **CLOSED** 2026-08-02T21:15:40Z | **`mergedAt: null`** | `feature/fail-closed-signal-integrity` |
| **#1082** | MERGED 21:47:23Z, `b713fe4b9` | yes | **the same branch** |

Read directly via `gh pr view --json` from this checkout, not from the plan's report.

⭐ **What makes this worse than an ordinary false green**: the verb *also deleted the branch*. So the
false `merged: true` was **immediately followed by a destructive action predicated on it**, and the
recovery cost a re-push and a new PR number. It was caught only because the author **re-derived
`origin/main` instead of trusting the return value**.

⭐ **A contrast that narrows it for you**: the same run's `ci pr merge-queue` **honestly returned
`enqueued: true`**, and that path worked. ⇒ Two verbs on the same abstraction, one truthful and one not
— which makes this look like a **per-verb response mapping** defect rather than a systemic one. ⚠ Stated
as a lead, not a conclusion; the plan's own hypothesis is unconfirmed and I have not read the mapping.

⛔ **Downstream contamination you should know about**: the plan's `kind: landing` message to this epic
consequently names **PR #1081** as where it shipped. Any artifact keyed off that message carries the
wrong PR id. Our queue row is stamped **1082** from PR state instead.

## 2. `review-retrospective` cannot distinguish a REFUSED reviewer from a clean one

Filed as `fail-closed-signal-integrity-004`. **Routed to you under the three-way rule — the PR/review
test fires first and wins outright.**

The artifact represents *"produced no comments"* and *"never ran"* **identically: by having no row**.
There is no representation for **"enabled, invoked, and refused"**.

**Observed live on PR #1081**: `sourcery` refused with `hard_quota` on **all three** review rounds and
simply **has no row**. A reader sees two clean reviewers and concludes the diff was reviewed by two
bots — it was reviewed by two, **refused by a third**, and the artifact cannot say so.

⇒ A fail-open **inside the review apparatus itself**, which is the surface used as evidence that a
review happened. Reinforces the standing rule that a green finalize is never proof the bots saw the
diff.

**Proposed shape** (theirs, and it matches your population-derivation discipline): emit a row per
**enabled** reviewer, not per **responding** reviewer, with an explicit participation state —
`reviewed` (ran, incl. zero actionable) / `refused` (ran and declined, carrying the reason) / `absent`
(enabled, never observed). Deriving rows from the responding set makes the detector's population a
strict subset of its own domain.

## 3. A correction I owe you, unprompted

I previously characterised **pr-agent** as reporting *"no major issues"* on a diff where CodeRabbit
found a Major. **That is withdrawn.** The review-retrospective checked the stored body: **pr-agent
flagged the `_module_for_path` root mismatch that became finding `ba6d34` and a real fix.**

⚠ **How I got it wrong matters more than the fact**: I read a *summary* of the review rather than the
stored comment body. That is the standing rule *"only `ci pr comments` is evidence of participation"*
violated in the harder direction — not reading absence as refusal, but **reading a summary as the
review**. Worth carrying in your lane, since summaries are the cheap artifact everyone reaches for.

## Also forwarded, not yours

`check-artifact-consistency` graded `affected_files_recall: 0%` (declared 18, found 0) on a plan whose
**true recall was 100%** — it derives the footprint from a worktree `branch-cleanup` removed two steps
earlier. Kept in `truthful-signals` / forwarded to `code-intelligence-substrate`'s `PLAN-CIS-028`,
because it is the step-ordering family. Flagged here only because it is the **inverse** of a false green
— a confident `fail` against work that was complete — and your lane reads that artifact.
