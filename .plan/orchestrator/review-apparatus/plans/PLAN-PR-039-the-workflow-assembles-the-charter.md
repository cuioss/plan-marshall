# PLAN-PR-039: The reusable workflow assembles the charter, and the repo only declares keys

> ⛔⛔ **SUPERSEDED 2026-09-14 by `PLAN-PR-066` — do NOT emit this spec.** Its six deliverables are
> carried there as D1–D6, and `PLAN-PR-066` adds the per-repository enablement half the operator
> directed (an `enabled` flag in `.github/project.yml`; absent means disabled) plus the derived fleet
> rollout. ⛔ **This file is NOT dead and is NOT deleted**: it remains the AUTHORITATIVE TEXT of every
> deliverable body, and `PLAN-PR-066` points here rather than retyping it. ⭐ Its blocking precondition
> is DISCHARGED — `packs/` now exists on `cuioss/pr-agent-settings` `main` (`PLAN-PR-065` #1491 / #64).

epic: review-apparatus
workstream: WS-02

> Staged plan spec — one shippable unit of work, ready for `/plan-marshall` hand-off.
> Consuming half of PLAN-PR-038. ⛔ MUST NOT land before it.

## Objective

Move charter assembly from generate time to run time. The reusable workflow reads a consumer
repository's `.github/project.yml` **from its default branch**, resolves the declared pack keys
against the artifacts PLAN-PR-038 publishes to `cuioss/pr-agent-settings`, appends the repository's
own `additional_rules`, and injects the composed text into the reviewer as
`PR_REVIEWER.EXTRA_INSTRUCTIONS`. A consumer repository then carries a declaration of a few lines
and no rule text at all.

The design was settled with the operator before staging and is not to be re-litigated during
execution: read the **default branch only**; `additional_rules` is **append-only**; any failure to
read, fetch or compose **fails the review loudly**; and the composed charter is **echoed into the
run log**.

## Deliverables

1. **Read `.github/project.yml` from the consumer's DEFAULT branch.** ⛔ The workflow has NO
   `actions/checkout` step, so this is an API read, not a file read — and the default branch is a
   security requirement, not a convenience: reading the PR head would let an author change the
   rules that review their own pull request.
2. **Resolve pack keys against the published artifacts and compose.** Spine + selected packs +
   `additional_rules`, in that order, append-only.
3. **Inject as `PR_REVIEWER.EXTRA_INSTRUCTIONS` on the reviewer step.** ⛔ The reviewer is a Docker
   action, which receives ONLY the variables named in its own `env:` block — the variable must be
   declared there or it silently does not arrive.
4. **Fail loudly on every failure path, and define the no-declaration case.** An unreadable
   `project.yml`, an unknown key, an unfetchable pack, or an empty composition fails the job. ⛔ A
   silent fallback to a bare charter is a green review with no rules — this epic's exact
   false-green archetype.
5. **Echo the composed charter into the run log.** This is the audit surface for the free-text
   channel deliverable 1 opens, and it restores the legibility lost by moving the charter out of a
   file in the repository.
6. **A guard pinning the two properties that silently rot**: that the fail path fails rather than
   warns, and that `additional_rules` cannot replace the spine.

Six deliverables, at the split guard. Recorded rationale for proceeding unsplit: 1–5 are one
control-flow path through a single workflow job — splitting mid-path would ship a workflow that
reads a declaration it cannot act on, or composes a charter it cannot inject. 6 is the guard for
that same path.

## Claim Labels

- OBSERVED: the reusable workflow has **no `actions/checkout`** — its steps are harden-runner,
  Generate Review Token, Authenticate to Google Cloud, Resolve credentials path, Record run start,
  Review pull request, Verify the reviewer actually produced a review. Read at
  `cuioss/cuioss-organization/.github/workflows/reusable-pr-agent-review.yml`.
  - verdict: unverifiable | checked_at: 14d8f3ccd | by: review-apparatus/cleanup | rescoped: n/a | evidence: Foreign-only reasoning re-confirmed at HEAD: every declared path is in cuioss/cuioss-organization, unreachable by a plan-marshall git diff. Anchor has drifted: claim reads the workflow at v0.27.0 while this repo's pin moved v0.28.0 to v0.29.0 in this window. Not a refutation; the named exemption stands. Superseded by PLAN-PR-066.
- OBSERVED: dotted-key environment variables are PR-Agent's documented configuration form, already
  used by this workflow for `VERTEXAI.VERTEX_PROJECT`, `VERTEXAI.VERTEX_LOCATION` and the three
  `github_action_config.*` toggles — read in the `Review pull request` step's `env:` block.
- OBSERVED: a Docker action receives only the variables named in its own `env:` block — stated in
  that step's own comment as one of two container boundaries crossed by hand.
- OBSERVED: the default-branch-only rule is already applied to the neighbouring mechanism —
  `repo_context_files = ["CLAUDE.md", "AGENTS.md"]` with `repo_context_from_default_branch = true`,
  and the config's own comment gives the reason: pointing it at the head "would let PR content
  rewrite the reviewer's own instructions".
- OBSERVED: the fail-closed empty-review gate is scoped by an explicit action allow-list
  (`opened`, `reopened`, `ready_for_review`, `review_requested`) or an `issue_comment` whose body
  starts with `/review`; downgrading it to a warning is prohibited in its own comment.
- HYPOTHESIS: `PR_REVIEWER.EXTRA_INSTRUCTIONS` (or the `PR_REVIEWER__EXTRA_INSTRUCTIONS`
  double-underscore form) reaches `pr_reviewer.extra_instructions` — confirm/refute against the
  pinned image's settings loader (verify-at-outline). ⛔ **This is the load-bearing mechanism of the
  whole plan.** The dotted-env form is OBSERVED for `VERTEXAI.*` and `github_action_config.*`; that
  it generalises to `pr_reviewer.*` is inferred and has not been executed. If refuted, the
  injection path changes and the plan re-scopes rather than proceeds.
- HYPOTHESIS: an injected environment value OUTRANKS a repo-local `.pr_agent.toml` — confirm/refute
  at the same loader (verify-at-outline). This decides whether a consumer repository that has not
  yet deleted its generated file gets the composed charter or its stale copy, which is the entire
  risk of the migration window.
- Verify-first clause: the **no-declaration case** must be settled before scoping. A repository with
  no `pr-agent:` block in `project.yml` either fails loudly (safe, but breaks every unmigrated
  repository the moment this lands) or falls back (unsafe). The resolution is a SEQUENCING one —
  every consumer declares a block BEFORE this lands — and the outline must confirm that ordering is
  achievable before choosing the behaviour.

## Expected Surface

- OBSERVED: `cuioss/cuioss-organization/.github/workflows/reusable-pr-agent-review.yml` — the
  `Review pull request` step's `env:` block, plus new steps ahead of it
- HYPOTHESIS: `cuioss/cuioss-organization` test/guard surface for that workflow — the existing
  `test_pr_agent_review_guard.py` is named in the workflow's own comments (verify-at-outline)
- HYPOTHESIS: `cuioss/cuioss-organization` docs — the caller template and the `.github/project.yml` schema
  (verify-at-outline)

⛔ **FOREIGN REPOSITORY ONLY.** This plan touches no plan-marshall file. That is deliberate and is
what preserves WS-02's disjointness property — the charter states the workstream is "disjoint by
construction from every plan-marshall file", which makes it the candidate second parallel stream.
A plan-marshall edit here would destroy that property.

⚠ **NAMED EXEMPTION from the surface-resolution metric — recorded 2026-08-31 at cleanup, so an
unmoved count is accounted for by name rather than read as a failed correction.** `corpus surfaces`
reports this spec `derivation_status: prose`, `claimed_count: 0`, `admits_disjointness_check:
false`. **That reading is CORRECT and must not be "fixed".** Every path above is in a foreign
repository, so this repo's resolver can never claim one; inventing a plan-marshall path to make the
metric move would destroy the very property the block above protects.

⛔ **The consequence must be stated rather than left implicit: the disjointness gate reads SILENCE
for this spec, not a checked negative.** Its disjointness is established by the foreign-only
property declared here — a claim about the spec — never by the gate having compared anything. The
two coincide for this plan; they are not the same fact, and a future reader must not take the gate's
quiet as evidence. Re-confirm the foreign-only property by reading § Expected Surface before pairing
this plan with anything.

## Dependencies and Sequencing

- Depends on: **PLAN-PR-038** — the published pack artifacts. ⛔ Landing this first fails every
  review in every consumer repository.
- Depends on: **the consumer fan-out** — every repository declaring a `pr-agent:` block in
  `.github/project.yml` and deleting its generated `.pr_agent.toml`. This is NOT a deliverable of
  either spec: it is a 21-repository migration, and the organisation already has the machinery for
  exactly this shape (`release.yml` opens and auto-merges a PR in each repository listed under
  `consumers:`). Sequence it between 038 and 039.
- Overlaps with: no staged spec names the org repository. Re-run `corpus cross-check` and the live
  `manage-status list` immediately before emit.
- Adjacent to: the fail-closed empty-review gate. This plan adds a SECOND failure mode to the same
  job and must not weaken the first. ⛔ Its `exit 1` is prohibited from being downgraded to a
  warning, in its own comment.

## Hand-Off Command

```text
/plan-marshall task="implement .plan/orchestrator/review-apparatus/plans/PLAN-PR-039-the-workflow-assembles-the-charter.md"
```

## Write-Boundary

The plan implementing this spec touches only the foreign `cuioss/cuioss-organization` repository
and its tests. It creates and edits NO file under `.plan/orchestrator/` other than its own
`inbox/{sender}-{seq}` message. Because the real diff is foreign, finalize will offer to manufacture
an empty host PR scoped to bookkeeping.
