# PLAN-115: A plan-less PR can be opened but never corrected

epic: truthful-signals
workstream: WS-01

> Staged 2026-07-29 from inbox `lane-router-…-019`. ⛔ **Currently BLOCKING live work** (PR #1052).

## Objective

`ci pr create` offers a **plan-less** body source; `ci pr edit` and `ci pr prepare-comment` do not.
A caller with no plan dir can therefore **open** a PR with a body and then never **edit** that body
or **comment** on the PR through the abstraction — and the only workaround (`gh` directly) is
forbidden by a project hard rule. Give the correction paths the same plan-less escape hatch the
creation path already has.

## The asymmetry — ORCHESTRATOR-VERIFIED at HEAD

```text
ci pr create : (--plan-id PLAN_ID | --body-file PATH)   ← mutually exclusive, plan-less path EXISTS
ci pr edit   : --plan-id PLAN_ID  REQUIRED, no --body-file
ci pr prepare-comment : same restriction — so reply / thread-reply inherit it
```

⚠ **The plan-less path exists because real callers have no plan dir** — `create`'s own help text
names the steward landing cycle. An ad-hoc post-merge fix PR is the same shape. **The capability was
granted for creation and withheld from correction**, with no stated rationale.

## Why it belongs to this epic

The stale body is a **confident-but-incomplete signal**: #1052's body says "What changed" and
enumerates **two of three** changes. **A reader takes an enumeration as complete.** The commit log
carries the third, so nothing is *hidden* — but the PR body, the highest-visibility surface,
understates its own contents, and **the sanctioned toolchain offers no way to fix it.** ⇒ The correct
behaviour under the rules is to leave it wrong.

## ⛔ SECOND FACE, folded 2026-07-29 — an existing PR cannot be ADOPTED into a plan either

The title understates the defect. There are **two faces**, and closing only the first leaves ad-hoc
PRs permanently ungoverned.

**Face 1 (the title) — a plan-less PR cannot maintain itself.** `pr reply`, `pr thread-reply` and
`pr edit` hard-require `--plan-id`, which keys the `prepare-body` / `prepare-comment` scratch slot
and is guarded by `require_plan_exists` (`ci_base.py:156`), so **a synthetic id returns
`plan_not_found`**. Only `pr create` carries `--body-file`.

**Face 2 — an existing PR cannot be brought under a plan.** `manage-status create` accepts **no
branch parameter**, and the branch is derived as `feature/{plan_id}` by `phase-5-execute` as its sole
writer. **A plan created to govern an existing PR would own a different branch than the PR it
governs.** There is **no adopt verb and no supported binding.**

⇒ **Together: an ad-hoc PR stays ad-hoc for its whole life — it cannot fix itself, and it cannot be
handed to something that can.**

⭐ **This is the epic's theme in structural form.** The pre-merge participation barrier (#1051) —
built precisely to stop a merge proceeding on an absence of review — runs inside `branch-cleanup`,
which **only executes in a plan flow**. ⛔ **So the PRs most likely to carry an unreviewed absence are
exactly the ones the absence-detector cannot see**, and the only thing holding the line for them is
operator discipline.

⚠ **This corrected a live orchestrator recommendation.** The orchestrator had advised "give #1052 a
plan" as the route out of the maintenance gap. **Face 2 shows that route does not exist** — the plan
would own `feature/{plan_id}`, not the PR's branch.

**Both remedies must be evaluated, and they are NOT alternatives:**

1. A **plan-less body channel** for the reply / edit verbs, mirroring `pr create --body-file` →
   makes an ad-hoc PR **maintainable**.
2. An explicit **adopt verb** binding a plan to an existing branch and PR → makes it **governable**.

**Choosing only (1) leaves such PRs permanently outside the participation barrier.** D1 must pick
with reasons rather than defaulting to the cheaper one.

## Deliverables

1. **D1 — GATE (mutates nothing): derive the affected verb population.** ⛔ `edit` and
   `prepare-comment` are the two this defect surfaced through — **treat them as a SAMPLE.** Enumerate
   every `ci pr` verb that takes `--plan-id` and establish, per verb, whether the plan binding is
   **load-bearing** (it resolves a real per-plan artifact) or **incidental** (it only locates a
   scratch path a `--body-file` could supply directly).
2. **D2 — add the plan-less source to every verb D1 finds incidental**, mirroring `create`'s
   mutually-exclusive `(--plan-id | --body-file)` shape exactly. ⚠ **Mirror it, do not invent a
   second convention** — a divergent flag shape on sibling verbs is the doc/script drift archetype
   this epic already tracks.
3. **D3 — a verb whose plan binding IS load-bearing says so.** Where the binding cannot be relaxed,
   the refusal must name the reason rather than presenting as a generic required-argument error, so a
   plan-less caller learns *why* instead of concluding the abstraction is simply incomplete.
4. **D4 — tests, each verified to FAIL pre-fix.** (a) A plan-less `pr edit --body-file` updates a
   body. (b) A plan-less comment path posts. (c) The mutual exclusivity holds both ways on each
   changed verb. (d) The verb population is **derived**, asserted non-empty, and contains both known
   members.

## Claim Labels

- OBSERVED (orchestrator-verified at HEAD, `--help` on both verbs): the exact asymmetry above.
- OBSERVED (message-supplied, first-party): PR #1052 was opened `--body-file` describing two commits,
  a third was added, and the body could not be updated.
- OBSERVED: `CLAUDE.md` § Workflow Discipline forbids `gh`/`glab` directly, so no sanctioned
  workaround exists.
- HYPOTHESIS: `edit` and `prepare-comment` are the only affected verbs — confirm/refute at D1
  (verify-at-outline). **An asserted absence of further members is verified like a presence.**

## Expected Surface

- OBSERVED: `marketplace/bundles/plan-marshall/skills/tools-integration-ci/**` — the `pr` verb group
- OBSERVED: `test/plan-marshall/tools-integration-ci/**`
- HYPOTHESIS: `workflow-integration-github` if the body/comment path is delegated there
  (verify-at-outline)

## Dependencies and Sequencing

- Depends on: none.
- Overlaps with: ⚠ **PLAN-102** (`post-merge-review-findings`, LAUNCHED, PR #1045) touches triage
  plumbing that may reach the same comment paths — **re-check disjointness before emitting.**
- Adjacent to: PLAN-114 (orchestration plumbing) — different bundle, no overlap expected.

## Hand-Off Command

```text
/plan-marshall task="implement .plan/local/orchestrator/truthful-signals/plans/PLAN-115-plan-less-pr-can-be-opened-but-never-corrected.md"
```

## Write-Boundary

Repository source + tests only; NO `.plan/local/orchestrator/` writes other than this plan's own
`inbox/{sender}-{seq}` message. See orchestration-model.md § Ledger Write-Boundary.
