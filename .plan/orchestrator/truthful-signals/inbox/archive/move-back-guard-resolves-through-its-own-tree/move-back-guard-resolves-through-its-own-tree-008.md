envelope_version=1
sender_type=plan
sender_id=move-back-guard-resolves-through-its-own-tree
epic=truthful-signals
kind=candidate-lesson
created=2026-08-27T18:57:11Z

# A plan whose subject IS a defect class reproduces it inside its own fixes, and the catch mechanisms are complementary by shape

**Component**: `plan-marshall:phase-6-finalize` / `plan-marshall:manage-execution-manifest`
**Shape**: which review mechanism can see which shape of one defect class.

## Observation

PLAN-TRUTH-114's subject was a class - *a resolver or guard answering from a scope that
cannot see the subject, and a claim outliving the read it was derived from*. The plan
reproduced that class inside its own edits and inside its own fixes repeatedly, and
**no single review mechanism caught more than one shape of it**. The reusable content is
the mechanism-to-shape mapping, not any one instance.

## Derivation (stated, not asserted)

Derived here by walking this plan's own finding stores: `manage-findings qgate list
--phase 6-finalize` (3 findings), `manage-findings list --type pr-comment` (11), and the
plan's build-error / test-failure findings. The table below is a **floor over the records
read**, not a partition of every defect the run produced. A further mechanism - an
operator-facing premise error - was reported by the dispatcher and is NOT independently
corroborated here, so it is named and excluded rather than counted.

| Mechanism | The shape it caught | Cited record |
|---|---|---|
| Pre-submission self-review (`ext-self-review-plan-marshall`) | A sibling document left behind when its partner was retitled; a NORMATIVE Assertion left behind when its own body was rewritten | qgate `29ee07` (branch-cleanup.md still prescribed unconditional `--force` after the SKILL.md retitle); qgate `950319` (cwd-policy.md's Section Assertion still read "exactly six consumers" after the body retired that framing) |
| The code's own user-facing strings | The same drift *inside an emitted payload* rather than in a sibling doc - the doc accurately described the string, so there was no doc-vs-code mismatch for the previous mechanism to find | qgate `33ef2d` (`git-workflow.py:2117` hint still presumed dirtiness) |
| External automated reviewer | A defective **derivation method** in the plan's own audit document - invisible to self-review because the document was internally consistent; and a `--force` contract that disagreed across three documents | pr-comment `410c92`; `11a81d`; `93fe11` |
| The fix agent's own re-run | **Test-pins-the-defect**: fixing the hint string broke a matched negative control that pinned the literal OLD string, plus a class docstring repeating the refuted claim verbatim | resolution of qgate `33ef2d` |
| CI / full build | Type and bound regressions none of the above can see | build-error `1571d2` (`no-any-return`); test-failure `c130f3`; the loader-guard `UNRESOLVED_CALL_SITE_BOUND` tipping 90 to 91 |

## Directive

1. **Budget for reproduction.** When a plan's deliverable IS a defect class, assume its
   own edits contain instances of it. "We are the ones fixing this" was the opposite of
   immunity here, every time.
2. **Do not drop a mechanism from the execution manifest on such a plan.** The shapes
   above are near-disjoint. Dropping self-review loses sibling-document drift; dropping
   automated-review loses derivation-method defects; and **a green `quality-gate` plus
   `test-compile` execute no assertion**, so only a real `module-tests` run catches the
   test-pins-the-defect shape - stated verbatim in `33ef2d`'s own resolution.
3. **After changing a user-facing string, sweep the tests that pin it** - and when
   updating the control, assert two load-bearing substrings of the NEW string rather than
   the whole literal, so the control still discriminates instead of merely being renamed.
   That is what `33ef2d`'s fix did ("Read message first" and "--force addresses a dirty
   worktree and nothing else").
4. **When self-review closes a finding, sweep the cohort tree-wide, not the delta.** Both
   qgate findings above carried `cohort_size=2`, and in each case the second member lay
   OUTSIDE the delta scope - one of them newly falsified *by this branch* rather than
   pre-existing.

## Evidence

Plan `move-back-guard-resolves-through-its-own-tree`, PR #1361, merged `5f972ac15`.
All cited hash ids are readable via `manage-findings` against that plan id.
