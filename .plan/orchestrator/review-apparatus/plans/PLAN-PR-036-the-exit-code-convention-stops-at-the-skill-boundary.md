# PLAN-PR-036: The exit-code convention stops at the skill boundary

epic: review-apparatus
workstream: WS-03

> Staged plan spec, created 2026-08-23 by the cloud-wave ingestion. Carries `030 G6`'s residual — the
> part PLAN-PR-027 excludes by its own § Out of scope. See `../cloud-wave-audit.md` § 8.

## Objective

Plan 030 widened the exit-code convention from `manage-*` scripts to *every* script call, in three
documents. PLAN-PR-027 extends that to the rest of `phase-6-finalize`. **Neither reaches three
documents in this epic's own review path** that invoke non-`manage-*` scripts and carry **no**
convention at all — one of them `workflow-pr-doctor/standards/automated-review-lifecycle.md`, which
invokes both `ci` and `github_pr`.

This is not a documentation tidy-up. Both CI providers' `main()` return 0 unconditionally, so a reader
following the narrow `manage-*` convention — or no convention — has **no instruction to check the
payload `status`** and will read a failed `ci` call as success. That is the mechanism by which
`create-pr.md` Step 4 could mark itself `done` on a PR that does not exist.

## Problem

Population, re-derived at HEAD: **42 files tree-wide carry an exit-code convention heading, 39 of them
the narrow `manage-*` form; 3 carry the widened form** (`phase-6-finalize/SKILL.md:44`,
`branch-cleanup.md:60`, `automatic-review/SKILL.md:172`). Under `phase-6-finalize` alone: 22 files, 20
narrow, 2 widened.

`030 G6`'s *Done when* is scoped to `phase-6-finalize`, and PLAN-PR-027 D2 satisfies it there. But the
gap's § Where also names three documents **outside** that skill which invoke non-`manage-*` scripts and
carry no convention whatsoever:

- `workflow-pr-doctor/standards/automated-review-lifecycle.md` — invokes `ci` **and** `github_pr`, and
  is a second executable `post_responses` invocation site;
- `workflow-pr-doctor/SKILL.md`;
- `workflow-integration-github/SKILL.md`.

PLAN-PR-027's § Out of scope excludes "widening the exit-code convention outside `phase-6-finalize` and
`automatic-review`" — explicitly and reasonably, to keep its own scope bounded. So all three survive
every staged plan untouched, and the first of them is squarely inside the review path this epic owns.

The underlying rule is the one the wave established: **verify a `ci` call by its payload `status`, never
by its exit code.** `ci_base.output_error` prints `status: error` at `EXIT_SUCCESS` *by design* — the
documented three-tier model — so exit code carries no failure information for this whole verb family.

## Deliverables

**D0 — GATE, mutates nothing: derive the population, do not curate it.** Sweep `marketplace/` for every
document that invokes a non-`manage-*` script through the executor, and classify each: widened
convention / narrow convention / none. **Publish the size of all three classes.** ⛔ The document set
must be derived from the invocations, not hand-listed — plan 030 derived the *obligation* per document
but hand-listed the document *set*, and that literal cost it two real members. If the derived set is
larger than the three named above, the plan is re-scoped at outline, not quietly trimmed.

**D1 — Give every no-convention document in the derived set a convention.** The widened form, verbatim
from `phase-6-finalize/SKILL.md:44`, plus the clause the wave's evidence requires: an exit code of 0
does not establish success for a `ci` call; read the payload `status`.

**D2 — State the `ci` rule once, where it belongs.** `tools-integration-ci/SKILL.md` gains the
statement that its verbs report failure as `status: error` at exit 0, that this is deliberate, and that
every caller must branch on the payload. Today the three-tier model is stated only in a code comment
(`ci_base.py:790-798`).

**D3 — Pin the closure, population-derived.** A test that derives the document set exactly as D0 did
and asserts each member carries a convention, **publishing the population size on a passing run** — not
only in an assertion message. A guard that can return zero from an empty population must publish that
population; copy the shape from
`test_bot_participation_contract.py::test_stated_blocking_counts_agree_with_the_derived_blocking_subset`,
which already sweeps tree-wide with a `scanned > 0` guard.

## ⛔⛔ FOLDED IN 2026-08-31 — the auth probe turns a bare return code into a NAMED cause, and it produced a false `[FAILED]`

The same defect one level down: not a convention that stops at a boundary, but a producer that
**invents a specific cause from a generic failure**. Root-caused first-party at HEAD
`31d42db87` while draining PLAN-PR-025A's landing.

`ci_base.check_auth_cli` (`ci_base.py`:843-862) — ⛔ **re-read the lines, they drift**:

```python
returncode, _, _ = run_fn(['auth', 'status'])
if returncode != 0:
    return False, login_message      # consumed as error_cause: auth_failed
```

**Any** non-zero exit becomes `auth_failed`, and **both streams are discarded**. `gh auth status`
validates the token over the network, so a transient network/API failure is indistinguishable
from "not authenticated" — the probe collapses *could-not-verify* into *not-authenticated* and
throws away the only evidence (`stderr`) that could separate them.

**The blast radius is the whole finalize summary.** `auth_failed` is one of the three UNANSWERED
arms in `phase-6-finalize/standards/output-template.md` § Snapshot Procedure step 4, so the
renderer stores `state = unread` and precedence rule 1 forces `[FAILED]`. **PLAN-PR-025A's fully
successful, merged run was headlined `[FAILED]` on this alone.**
⭐ **The consumer is CORRECT and must not be softened** — a summary that cannot say whether a PR
exists is not a green one. Fix the producer's claim, never the barrier that trusted it.

### Added deliverable — derive the auth verdict, and give "could not verify" its own arm

- Capture and inspect the streams rather than the return code alone; report `auth_failed` **only**
  when the underlying tool actually says unauthenticated.
- Give the unverifiable case a **distinct** cause, so the renderer can tell a credential problem
  from a transient one. ⛔ Do not widen `auth_failed` to mean both — that is the collapse this
  fold exists to remove.
- ⛔ **Matched control required:** assert the probe returns authenticated whenever the tool exits
  0, **and** returns `auth_failed` only when it genuinely reports unauthenticated. A test that
  exercises only the failing side cannot catch an over-broad mapping.

⚠ **NOT reproducible at this HEAD** — re-runs give `success`, `no_pr_found`, and
`worktree_resolution_failed` respectively, all correctly discriminated. The **structural**
misclassification is CONFIRMED from the code above; the **specific trigger** on the day is
HYPOTHESIS, and the matched control is what settles it.

## Claim Labels

- OBSERVED (added 2026-08-31, verified first-party): `check_auth_cli` maps any non-zero
  `gh auth status` exit to the `auth_failed` cause and discards both output streams
  (`returncode, _, _`). Confirm/refute at `ci_base.py` § `check_auth_cli`.
  - verdict: corroborated | checked_at: 19453cb | by: review-apparatus/cleanup | rescoped: n/a | evidence: Re-grounded at HEAD 19453cb (was 7845a4b9a). METHOD CHANGED THIS PASS: intersection of the spec's DECLARED Expected Surface (via corpus surfaces, the single shared reader) against git diff --name-only 7845a4b9a..HEAD (204 paths). The former whole-spec-file method is RETIRED as non-discriminating - it scored hits on prose mentions of CLAUDE.md and .plan/marshal.json. ZERO declared paths moved in this window, so no premise of this spec was disturbed. NOT a line-by-line re-audit: this establishes the surface is UNDISTURBED, not that the premise was re-read.
- OBSERVED: 42 files tree-wide carry an exit-code convention heading, 39 narrow / 3 widened; under
  `phase-6-finalize`, 22 files, 20 narrow / 2 widened. Re-derived at HEAD `e8324d241`.
  - verdict: corroborated | checked_at: 26645688b | by: review-apparatus/cleanup | rescoped: n/a | evidence: Re-grounded at HEAD 26645688b, method: whole-spec-file intersection against git diff --name-only f6d058b4b..HEAD (486 paths). Fail-closed by design - the scan is over the WHOLE spec file, not a parsed Expected Surface section, because two section parsers disagreed on this corpus. Basename matching was measured last pass and DISCARDED as non-discriminating. NO running-row exclusion applied this pass: the queue has no running plan. Intersection: 3 hit(s). 3 hits, all SKILL.md surfaces (tools-integration-ci, workflow-integration-github, workflow-pr-doctor). ⚠ #1356 deliberately reworked the exit-code convention across those docs, which is this spec's exact subject - so this spec is the MOST LIKELY of the low-intersection set to be partly discharged. Re-read the three docs before scoping; do not assume the gap survives.
- OBSERVED: `ci_base.output_error` prints `status: error` and returns `EXIT_SUCCESS`
  (`ci_base.py:790-798`), with the three-tier model stated in its comment. Both provider `main()`
  functions end `dispatch → print → return 0` with no status branch.
- OBSERVED: `automated-review-lifecycle.md` invokes `ci` and `github_pr` and carries no convention
  heading; it is also the second executable `post_responses` invocation site (`:139`).
- OBSERVED: PLAN-PR-027 § Out of scope excludes widening beyond `phase-6-finalize` and
  `automatic-review`.
- HYPOTHESIS: the derived no-convention set is exactly the three documents named — confirm/refute at D0
  (verify-at-outline). **Treat a larger result as the expected outcome**, not as scope drift.
- Verify-first clause: check whether PLAN-PR-027 D2 has landed. If it has, the `phase-6-finalize`
  members are already discharged and this plan's set shrinks accordingly; re-derive rather than assume.

## Expected Surface

- OBSERVED: `marketplace/bundles/plan-marshall/skills/workflow-pr-doctor/standards/automated-review-lifecycle.md`
- OBSERVED: `marketplace/bundles/plan-marshall/skills/workflow-pr-doctor/SKILL.md`
- OBSERVED: `marketplace/bundles/plan-marshall/skills/workflow-integration-github/SKILL.md`
- OBSERVED: `marketplace/bundles/plan-marshall/skills/tools-integration-ci/SKILL.md`
- HYPOTHESIS: further documents the D0 sweep adds (verify-at-outline)
- OBSERVED: `test/plan-marshall/tools-integration-ci/` — the new population-derived guard

## Dependencies and Sequencing

- **Depends on: PLAN-PR-027** (its half (a), D1+D2+D5). Running after it means this plan's derived set
  is the genuine remainder rather than an overlapping sweep of the same documents.
- **MUST NOT run concurrently with PLAN-PR-027.**
- ⚠ **`workflow-integration-github/SKILL.md` is contended.** PLAN-PR-024 (D3, D4) and PLAN-PR-025
  (D2, D6) both write its § `github_pr fetch_findings`, and **no split governs that file**. This plan
  touches only its convention heading, at the top — disjoint from that section, but sequence it after
  both rather than relying on the disjointness holding.
- Overlaps with: PLAN-PR-029 and PLAN-PR-035 (`automated-review-lifecycle.md`, different sections).

## Hand-Off Command

```text
/plan-marshall task="implement .plan/local/orchestrator/review-apparatus/plans/PLAN-PR-036-the-exit-code-convention-stops-at-the-skill-boundary.md"
```

## Write-Boundary

The plan implementing this spec touches only its own repository source and tests. It creates and edits
NO file under `.plan/local/orchestrator/` other than its own `inbox/{sender}-{seq}` message.
