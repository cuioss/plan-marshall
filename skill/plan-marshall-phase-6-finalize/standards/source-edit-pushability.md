# Pre-merge source-edit pushability contract

A normative contract for any finalize step that edits source files at runtime. It
governs *when* such a step may run and *what* it must do when a needed edit is
discovered too late to push.

## The contract

**A finalize step that edits tracked source MUST run before the branch is merged.**

Finalize runs on the plan's feature branch, which is squash-merged into `main` by
`default:branch-cleanup` (order 70). A source edit is only pushable — and only
covered by the PR's CI run and reviewed with the rest of the change — while the
branch is still open. Once the branch is merged, the feature branch is gone: a
further edit cannot ride the PR, cannot be squashed into the landed commit, and can
only reach `main` through a separate follow-up PR.

Therefore a step whose job is to mutate source (declared by `mutates_source: true`
in its frontmatter) MUST be ordered **before** `default:branch-cleanup`, and — when
its edit must be CI-covered — before `default:ci-verify` (order 22) as well, so the
correction is part of the verified, reviewed diff that merges.

## The reciprocal: pushability and post-run review are opposite sides of the merge gate

The merge gate partitions the pipeline, and the two frontmatter facts sit on
opposite sides of it:

- `mutates_source: true` ⇒ the step MUST be ordered **before** `default:branch-cleanup`
  (the contract above) — its edit is only pushable while the branch is open.
- `post_run_review: true` ⇒ the step MUST be ordered **after** `default:branch-cleanup`
  — its evidence is only complete once the gate has produced it.
- **No step may declare both.** The exclusion is not an independent rule bolted
  beside the two above; it falls out of them, because the two ordering obligations
  are unsatisfiable together.

The `post_run_review` discriminator (the two predicates P1 and P2 that decide
membership, and the derivation of the exclusion from P2) is owned by
[`extension-api/standards/ext-point-finalize-step.md`](../../extension-api/standards/ext-point-finalize-step.md)
§ "Implementor Frontmatter" — consult it rather than re-deriving the classification
here.

## The discover-after-merge rule

A step that discovers a needed source edit only AFTER the branch has merged MUST NOT
silently revert or drop its change to "stay clean". Silently reverting an edit that
was genuinely required leaves `main` in the very state the edit was meant to fix,
with no record that the fix is owed. Instead, the step MUST emit an **explicit
follow-up artifact** — a lesson, a follow-up plan, or a tracked issue — that names
the owed edit, so the work is visible and scheduled rather than lost.

Guessing a value that is not yet known at edit time (for example, hand-editing a PR
number before the PR exists) is a special case of the same failure: it produces an
unpushable or wrong edit that a later reader must silently reconcile. The correct
shape is a deterministic, self-resolving sentinel filled by a pre-merge step from a
value the dispatcher already provides.

This rule is also the **sanctioned route for a `post_run_review: true` step that
derives an architecture hint**. Such a step is ordered post-merge by construction,
so an in-worktree `architecture enrich` write is unpushable by definition rather
than by accident. It therefore names the owed hint in a follow-up artifact instead
of writing it — the hint is scheduled and visible, and the step keeps
`mutates_source: false` honestly rather than reproducing the very defect this
contract exists to prevent.

## Reference implementation

`project:finalize-step-era-stamp-fill` (order 21, between `create-pr` and
`ci-verify`) is the reference implementation of this contract. It resolves the
`PR-PENDING` era-stamp sentinel in `audit.py`'s `CHECK_ERA` map (and its
`test_audit.py` mirror) to the real PR number, then commits and pushes the
correction pre-merge so it rides the PR and is CI-covered. It exists precisely
because the prior convention — a prose instruction to hand-edit the PR number after
merge — was the guessed-PR-number / post-merge-unpushable era-stamp defect: an edit
that could not be pushed on `main` and was silently reverted or guessed.

## Authoring checklist

When authoring a finalize step that edits source:

- Declare `mutates_source: true` in the step's frontmatter.
- Order it before `default:branch-cleanup` (merge), and before `default:ci-verify`
  when the edit must be CI-covered.
- Commit and push the edit onto the feature branch within the step (do not defer the
  push to a later step or to the operator).
- If the step can only determine the edit after merge, emit an explicit follow-up
  artifact naming the owed edit — never silently revert.
