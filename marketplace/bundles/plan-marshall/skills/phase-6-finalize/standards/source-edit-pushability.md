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

## The both-sides need is representable — by a split, not by one step

A step can genuinely need **both** sides of the gate at once: it must read evidence
only the merge gate produces (`post_run_review: true`) **and** it must write tracked
source (`mutates_source: true`). "No step may declare both" (above) closes that off
for a **single** step, because the two ordering obligations are unsatisfiable
together. It does **not** make the need itself unrepresentable — **the need is
representable, by splitting the work across the merge gate into two steps**:

- a **classify (read) pass** — ordered **after** the merge gate
  (`post_run_review: true`, `mutates_source: false`). It reads the post-merge
  evidence and records its verdict to a **durable store** — a `--fact` on its step
  record, a plan-directory artifact, or the lessons corpus — and writes no tracked
  source;
- an **apply pass** — ordered in the pre-merge **settle band**
  (`mutates_source: true`). It reads the verdict the classify pass recorded and
  applies the pushable source edits, which ride the plan's own PR.

The seam between the two passes is **cross-run, and the durable store is the only
seam**. Because the apply pass is pre-merge and the classify pass post-merge, within
one run the apply pass runs **before** the classify pass — so the apply pass in run
_N_ consumes the verdict the classify pass recorded in run _N-1_. The classify pass
MUST therefore **persist** its verdict durably; it cannot hand it in-process to an
apply pass that does not run in the same window. A split that tried to pass the
verdict in-process would silently degrade to the apply pass reading nothing, which is
exactly the R1 failure this contract records.

This is **distinct** from the discover-after-merge follow-up-artifact rule (§ below).
That rule serves a step whose source edit can be **deferred** to a separate follow-up
PR; the split serves a **recurring, in-band** operation whose edits should keep
riding the plan's own PR, run over run. A step choosing between them asks: is this a
one-off owed edit (→ follow-up artifact) or a standing read-then-edit operation (→
split)?

`project:finalize-step-lessons-housekeeping` is the worked case that motivates this
rule. It runs in the settle band as a pure source-mutating **apply-style** step
(`mutates_source: true`); its Step 1 read of the retrospective's
`quality-verification-report.md` is **best-effort and non-fatal** (the report is
normally absent at its settle-band order, and it proceeds on `request.md` +
`modified_files` alone), so it does **not** itself require the post-merge classify
half and is correctly a single settle-band step today. A future step that needs that
post-merge evidence as a **hard** input takes the split above rather than declaring
both facts on one step.

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

### Its post-PR CI run is intrinsic, not a defect to relocate

A `PR-PENDING` fill commits and pushes AFTER `create-pr`, which advances the PR head
and so provokes one further CI run whenever a sentinel is present. That run is
**intrinsic to the PR-number dependency**, not an avoidable inefficiency — do not try
to remove it by relocating the commit:

- **Computing the value before the PR exists is impossible** — the real PR number is
  not known until `create-pr` (order 20) runs.
- **Deferring the resolution to after the merge is refused** — a post-merge edit is
  unpushable on `main`, which is exactly the guessed-PR-number / post-merge-unpushable
  defect this contract exists to prevent (§ "The discover-after-merge rule").
- **Riding an existing post-PR commit has no reliable carrier in the common case** —
  `create-pr` authors no commit, and a loop-back fix commit is not guaranteed to occur.
  When one *does* occur, the fill's correction rides that commit rather than pushing
  separately (the dispatcher's commit instrumentation batches it), so the extra run is
  paid only in the sentinel-only finalize.

The lever that would collapse the sentinel-only case to a single completed run —
superseding the pre-fill CI run via workflow concurrency cancellation — lives in the
CI workflow definition, not in any finalize step, and is out of this contract's scope.

## Authoring checklist

When authoring a finalize step that edits source:

- Declare `mutates_source: true` in the step's frontmatter.
- Order it before `default:branch-cleanup` (merge), and before `default:ci-verify`
  when the edit must be CI-covered.
- Commit and push the edit onto the feature branch within the step (do not defer the
  push to a later step or to the operator).
- If the step can only determine the edit after merge, emit an explicit follow-up
  artifact naming the owed edit — never silently revert.
- If the step needs **post-merge evidence AND** a source edit, do NOT declare both
  facts on one step — split it into a post-merge classify pass and a settle-band apply
  pass (§ "The both-sides need is representable — by a split").
