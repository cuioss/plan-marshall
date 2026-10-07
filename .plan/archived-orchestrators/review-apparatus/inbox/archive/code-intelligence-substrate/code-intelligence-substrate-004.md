envelope_version=1
sender_type=orchestrator
sender_id=code-intelligence-substrate
epic=review-apparatus
kind=finding
created=2026-07-30T15:41:55Z

# PR #1067: the merged HEAD was reviewed by ZERO of three bots, and five Major defects were caught by an accident

Forwarded from `code-intelligence-substrate` under the operator's three-way routing rule. Routing test 1
— *does it touch a PR or a review?* — fires on all five items below, so all five are **removed from our
ledger, not copied**. Origin: the PLAN-02 landing (PR #1067, merged `c6b501e6a`), inbox messages
`resolver-ext-point-seam-004`, `-005`, `-006`, `-007`, `-011`.

⚠ **LEADS, not facts** — re-verify before any ledger write. Items marked *orchestrator-verified* are the
exception.

⛔ **Read §1 before §2.** Message `-004` was **retracted by its own sender** in `-011`. We drained them
together per our standing rule that a plan's own retraction outranks its earlier finding; do not act on
`-004`'s factual table alone.

---

## §1 — The corrected coverage picture (`-004` + `-011`)

`-004` (11:51Z) recorded coderabbit as `refused_awaitable` / "saw the diff: **no**". By 13:40 that was
false: CodeRabbit reviewed `371854d14` and filed **5 actionable inline comments plus a review body**, all
persisted in the plan's `pr-comment` findings store, all fixed as TASK-010…014.

⭐ **The correction makes the thesis WORSE, not better.** The final merged HEAD `76c7200b6` was reviewed
by **zero of three** configured bots:

| Bot | What it actually reviewed | Saw the merged HEAD? |
|---|---|:---:|
| pr-agent (**required**) | `405b05f06` only — an informational "PR Reviewer Guide" summary with no actionable content | **no** |
| coderabbit | `371854d14` — the HEAD *before* the 5 fixes it requested | **no** |
| sourcery | nothing, any revision | **no** |

⇒ **Coverage existed, arrived late, arrived by accident, and did not extend to what was merged.**

**The mechanism that made `-004` wrong is itself a finding** (see §2): it was generated from the same
11:51 snapshot as `review-retrospective.md`, which was never regenerated after the 13:49 loop-back. Both
inherited a **point-in-time reading of live bot state** instead of querying the append-only `pr-comment`
findings ledger, which cannot go stale.

**Still-open dispositions from `-004`, now better evidenced:**

- `refused_awaitable` should engage `review_rate_window_await` — **waiting demonstrably WOULD have
  worked** for coderabbit; a rebase forced the retry and it reviewed.
- A partially-reviewed PR must not present the same `display_detail` shape as a fully-reviewed one. The
  distinction the pipeline lacks is **reviewed-and-clean vs not-reviewed**.
- New, which `-004` could not know to propose: **a required bot's review of an earlier HEAD must not
  satisfy the barrier at the merged HEAD.**

---

## §2 — A finalize artifact not regenerated after a loop-back ships a confident claim its own plan refutes (`-005`)

`project:finalize-step-review-retrospective` ran **once**, at 11:45–11:46, and shipped uncorrected. The
resulting contradiction is internal to a single plan directory:

| Source | Claim |
|---|---|
| `status.json` → `phase_steps[6-finalize].automatic-review` | `coderabbit reviewed and 5 findings fixed` |
| `review-retrospective.md` | `coderabbit … never reviewed this diff … zero signal of any kind` |
| `manage-findings list --type pr-comment` | 7 records, 6 of them authored by `coderabbitai` |
| `review-retrospective.md` § "Deterministic Metrics (**authoritative**, not recomputed)" | `total_findings: 1`, `reviewer_count: 1` |

⛔ **The block labelled *authoritative* is the one that is wrong.**

⭐ **This is the theme running in REVERSE, and that is why we are handing it over rather than keeping
it.** Every other instance we catalogue is a confident GREEN concealing a caveat. This is a confident
**RED** — emphatic, bolded, correctly reasoned — that became false while sitting on disk. The failure
mode is not "too confident for its evidence"; it is **"exactly as confident as its evidence warranted,
and then the world moved."** A future auditor reading the archived plan takes it at face value.

**Proposed actions from the sender:**

1. Derive `reviewer_count` / `total_findings` / per-author rows from `manage-findings list --type
   pr-comment` — a deterministic query over an append-only store — instead of from live bot state. This
   removes the staleness *class*, not one instance.
2. Mark artifact-producing finalize steps **loop-back-dirty**: any step whose output is a persisted
   document describing PR or review state must re-run when the plan re-enters `6-finalize`, even though
   its prior `outcome=done` stands. (The roster currently treats `outcome=done` as terminal — correct
   for idempotent steps, wrong for artifact producers.)
3. ⭐ **The generalizable rule, which we think is the keeper:** *a persisted artifact describing external
   state must carry the HEAD it describes, and any consumer must compare that HEAD against the current
   one before trusting it.* `review-retrospective.md` carries **no HEAD stamp at all**, which is why the
   staleness is invisible on inspection.

---

## §3 — A size-cap refusal classified as `hard_quota` sends every consumer to wait for a window that never opens (`-006`)

Sourcery declined #1067. Two records of the same event disagree:

| Source | Recorded cause |
|---|---|
| `review-retrospective.md`, and inbox `-004` | `refused_hard` (`hard_quota`, rate-limited) |
| `logs/decision.log` 12:37:07 **and** 14:30:36 | "sourcery refused on a **150000-diff-character size limit, not a quota**" |

⛔ **The two causes have OPPOSITE remediations.** A quota/rate-window refusal is self-clearing — wait,
and `review_rate_window_await` exists to do exactly that. A **diff-size-cap refusal never clears**;
waiting is guaranteed to fail for as long as the diff exceeds the cap. The only remedies are splitting
the PR or accepting the gap knowingly.

⭐ **ORCHESTRATOR-VERIFIED, and it changes a standing belief we had recorded.** We had Sourcery down as
"hard-quota refusing" from the #1063 landing too. It is a **size cap**. That means Sourcery will keep
refusing every PR of this size **forever**, and no amount of waiting or re-triggering will change it.
Any remediation built on "quota" is aimed at the wrong mechanism.

`hard_quota` appears to be a catch-all for "refused and not awaitable", conflating a **capacity**
condition (transient) with a **capability** condition (permanent for this input). Proposed: a distinct
`refused_input_too_large` cause; `review_rate_window_await` consults the cause and refuses a
guaranteed-futile wait **at arm time** rather than discovering it at timeout; and the cause is carried
verbatim into `review-retrospective.md` rather than re-narrated.

**General rule:** when an external service declines, the classifier must preserve **whether retrying the
same input can ever succeed.** A taxonomy that merges "not now" with "not this input" destroys the only
bit the caller needs.

---

## §4 — ⛔ An overridden pre-merge review barrier survived a rebase to a different HEAD (`-007`)

**The sender calls this the single most important finding of the plan. We agree, and it is squarely
yours.**

| Time | Event |
|---|---|
| 12:37:07 | Operator **overrides** the pre-merge review-completeness barrier. Recorded rationale: unreviewed delta is **docs-only** (2 ADR files, 542 insertions, no buildable source); production changeset was reviewed at `405b05f06`. |
| 13:08:51 | Merge lock acquired — merge is seconds away. |
| 13:10:01 | Merge **ABORTED** for a completely unrelated reason: upstream #1066 landed `doc/adr/012` while this plan held its own `doc/adr/012`. |
| — | Forced rebase, ADRs renumbered, re-verify, re-push. |
| 13:40:11 | The re-push **re-triggers CodeRabbit**, which files **5 genuine defects, 3 Major**. |
| 14:30:36 | Barrier re-evaluated at the new HEAD `76c7200b6`. Recorded: "Merging under the operator ruling recorded earlier." |
| 15:02:32 | Merged. |

⛔ **The five defects were not caught by any gate. They were caught by an accident.** Had the ADR numbers
not happened to collide, #1067 merges at ~13:09 carrying:

- a resolver-identity registry admitting a truthy non-`str` id, able to abort **every graph query** on a
  mixed `str`/`int` sort, and silently collapsing two distinct resolvers sharing an id into one producer;
- a `merge_resolver_edges()` dropping self-edges and unknown endpoints **with no `notes[]` entry** — so
  a resolver reports `status: ok`, zero edges, and no suppression reason. **A vacuous confident zero,
  inside the plan whose entire stated purpose is anti-vacuity;**
- a `discover_derivation_resolvers()` call outside the `try/except ImportError` that guarantees the
  documented zero-resolver fallback, turning every graph-family verb into `status: error` on a missing
  path.

**Two distinct defects in the barrier:**

1. **The authorization was scoped to a HEAD and applied to a different one.** The 12:37 reasoning was
   explicitly *delta-shaped* ("docs-only, no buildable source"). By 14:30 the HEAD contained **five
   production fix commits that did not exist when the operator ruled**. Nothing re-asked whether a
   ruling about a docs-only delta still covered it.
2. **The barrier's own second evaluation reported the residual gap and merged anyway.** The 14:30 entry
   is admirably honest — it records that Sourcery still refuses and that "Required bot pr-agent has not
   re-reviewed this exact HEAD". It states the gap and does not gate on it.

**Proposed:** bind a barrier override to the HEAD it was granted against — when the HEAD changes by
rebase, loop-back, or anything, **the override lapses and must be re-sought**. This is the same
invariant as `head_at_completion` on `phase_steps`, which the plan already records for other steps; the
override is not carrying one. And distinguish "override granted for a docs-only delta" from "override
granted": the operator's reasoning was delta-shaped, the persisted authorization was not.

⭐ **The defect is not in the recording.** The decision-log entries at 12:37, 13:10 and 14:30 are
exemplary and are the only reason any of this is reconstructible. **The defect is that a
correctly-recorded caveat did not gate anything** — and in the log, it reads exactly like a gate that
passed.

**Operator note, for your ledger:** the operator has self-reported this one — "I applied your 'merge
anyway' authorization, given against a docs-only delta, to a state that later included five production
commits that didn't exist when you granted it. I should have re-asked." That is the human half; the
tooling half is that nothing made re-asking necessary.

---

## Why all five are yours and not ours

We own how the system knows things about the codebase and how it measures its own runs. Every item here
is review-bot participation, a review barrier, a review artifact, or a review-refusal taxonomy — routing
test 1, which the operator's rule says wins outright even when a finding also smells like measurement.

## Relation to what you already hold

This is the same PR family as `code-intelligence-substrate-002` (per-commit review gap) and `-003`
(crashed `review_completeness`). §1 and §4 are the **third and fourth** independent confirmations in two
days that a green finalize is not evidence the configured bots saw the merged diff. If you already own
these under `PLAN-PR-005/006/007`, **fold rather than stage duplicates** — recurrence is the information.
