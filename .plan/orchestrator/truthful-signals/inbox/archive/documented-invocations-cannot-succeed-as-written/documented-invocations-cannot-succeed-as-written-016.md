envelope_version=1
sender_type=plan
sender_id=documented-invocations-cannot-succeed-as-written
epic=truthful-signals
kind=candidate-lesson
created=2026-09-03T19:00:11Z

component=plan-marshall:automatic-review
category=improvement

# The review-versus-gate measurement is excluded by construction on exactly the PRs that took a fix round

Two structural gaps make the review-retrospective's central measurement unobtainable, and both are
properties of the pipeline rather than of this PR. They come from this run's `review-retrospective.md`
and reached no candidate-lesson.

## Gap 1 — no reviewed-at-all handoff reaches a post-merge-ordered step

`reviewer_coverage: 0/3` (`enabled_bots`: coderabbit, pr-agent, sourcery; `reviewed_bots`: none
supplied). The artifact states the cause plainly:

> no persisted reviewed-at-all classification reaches a step ordered at 990, after the merge gate.
> `--reviewed-bots` was therefore supplied bare, which reads as *nobody substantiated as having
> reviewed* — an excluded PR, never a clean zero.

And in its closing recommendation: *"That forces `reviewer_coverage: 0/3` here and forces the
zero-findings grade to fail closed to `indeterminate` on every future run."* The data exists —
`review_completeness`'s `bot_states`, mapped to `author_login` / `bot_kind` — it simply is not
persisted anywhere a step ordered after the merge gate can read it.

## Gap 2 — a looped-back PR has no single reviewed tree

The `pr-comment` findings carry **two** `reviewed_commit_sha` values: seven at `1e4ef8e7` and three
at `49769bd2f`, because the PR looped back and was reviewed twice. No single tree was reviewed in
full, so `reviewed_head_sha` was deliberately left empty — *"deriving one SHA (for instance by taking
the newest) would manufacture a tree identity no reviewer actually reviewed against."* Passing
nothing is the correct move, **and it excludes the PR**.

Result: `verdict: excluded`, `exclusion_reason: gate_tree_unsubstantiated`, `structural_share: null`.
Seven escapes were counted and partitioned (`gate_addressable: 1`, `gate_structural: 5`,
`unpartitioned: 1`) and no share exists.

## Compounding selection effect, from the assessor's own provenance

> on the current finalize step ordering, `finalize-step-simplify` (order 8) and
> `finalize-step-security-audit` (order 9) mutate source after the gates (5, 7) and a forward pass
> never re-gates their edits, so the ONLY measurable PRs are those where neither step committed
> anything. That is a biased population, not a random sample.

## Rule

The exclusion is honest and must stay — the failure is that the *measurable* population is
systematically the PRs that needed no fixing. Two concrete moves:

1. Persist the reviewed-at-all classification (`bot_states` → `author_login` / `bot_kind`) into plan
   state at `automatic-review` time, so a step ordered after the merge gate can read it. Without it,
   `reviewer_coverage` is `0/N` on every run by construction.
2. Model the per-round reviewed tree rather than one PR-wide SHA. A looped-back PR has a
   *sequence* of reviewed trees; the gate delta is computable per round even when it is not
   computable PR-wide.

⛔ A run of `excluded` rows across PRs means those PRs were never measurable. It does **not** mean the
gates were clean.
