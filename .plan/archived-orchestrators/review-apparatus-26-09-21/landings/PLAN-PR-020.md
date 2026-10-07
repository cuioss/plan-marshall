# Landing: PLAN-PR-020 — A prose routing table is not an enforcement boundary

epic: review-apparatus · workstream: WS-04 · shipped 2026-08-12
cloud run: `cloud-runs/060-a-prose-routing-table-is-not-an-enforcement-boundary/`
PR #1182 (`ff11803bf`)

> Landing analysis over the cloud-wave corpus. `report-01.md` is the run's claim; `verification.md`
> is ground truth. Where they disagree, verification wins.

**Verification verdict: `partially-implemented`** — the weakest verdict in the wave.

## What landed

The D0 8-member derivation (4 merge-shaped verbs × 2 providers) is real and reproducible against both
registries, and its null result survived four independent candidate second-instances. Seven of eight
members consult a genuine callee-side state read. Two new test files exist and run green. The
cold-read-driven GitLab refusal-message fix is correct and locked.

**Deliverables: 4 — 1 done (D0), 3 partial.**

## What did not land

- `gitlab:merge-queue` alone delegates its off-routing verdict to the provider's HTTP status **after**
  issuing the side-effecting merge-train POST.
- The GitLab preflight the other two GitLab members share fails **open** on an unresolvable project
  scope — while its docstring claims the opposite.
- The population guard is blind to a merge-shaped verb registered under a new name — **the exact
  defect D0 forbade**. Re-verified: injecting `('pr','queue-merge')` leaves both guards green (41
  passed).
- The run report contradicts its own shipped diff.

## Report claims the verification found false — 8 of 19 audited

- `**Outcome:** _in progress_` — the lane contract at landing admitted only
  `completed | partial | blocked`. Never set.
- "No production source was changed by this plan" — **contradicted by the diff the report shipped
  with**. Re-verified: `git show ff11803b --numstat` gives `gitlab_ops.py +11/−1` plus three test
  paths; the report's own F3 describes making that change two sections apart.
- The `*.py` footprint "two test files" — it is four Python paths.
- "The marshall-steward landing cycle uses `safe-merge`" — re-verified: `landing-cycle.md` § Step 5(c)
  dispatches `ci pr merge-queue` unconditionally, no routing, no fallback.
- "Dropping the 404/403-as-refusal handling flips `gitlab:merge-queue`'s off-routing test" —
  **measured: 18 passed** under that mutant.
- "A new merge-shaped verb fails `test_every_derived_member_has_an_offrouting_scenario`" — measured
  green.
- `sourcery-ai` recorded as `silent` — **it published a weekly rate-limit review on the PR-level
  reviews surface**, a third GitHub surface the run never read.
- Step 8 "Landing recorded to the operator (see below)" — nothing below it is a landing record.

## Gaps: 14 — 12 full, 2 partial, 0 uncovered

- **partial**: G6 (the record half is covered by PLAN-PR-031 D3; the **mechanism** half — "the
  reviewer-read step names all three surfaces a bot can publish on" — is carried only as a *proposal*,
  because a cloud-lane run may not amend its own contract), G8 (PLAN-PR-027 D4 adopts the
  `routing_note` option but its Done-when asks for one field where the gap demands three: routed verb,
  expected branch, and verb actually dispatched)

## Standing facts

- ⭐⭐ **A third GitHub surface exists and this epic's own runs do not read it.** PR #1182 carried a
  `sourcery-ai[bot]` **review** (id 4915308445, `state: COMMENTED`) whose body is a weekly rate-limit
  notice. The run read the conversation and inline-thread surfaces, called the bot `silent`, and
  disclosed a skip. **A rate limit reopens; a skip does not.** This is a live reliability defect in the
  epic's own instrument.
- ⭐⭐ **A "population-complete" derivation that filters membership through a hand-listed vocabulary is
  complete only over the vocabulary.** `_merge_shaped_roster.MERGE_SHAPED_VERBS` is a module-level
  frozenset; a verb outside it is invisible to both guards. The same shape recurred in plan 030.
  **Derive membership *and* vocabulary, or state the hand-list as a hand-list.**
- ⛔ **A run report can contradict the diff it shipped with.** Read `git show {squash} --name-status`
  before believing any footprint claim.
- ⭐ **An argued mutation is not a measured one.** Two structural falsifiability arguments in this run
  were measured and both were wrong.
