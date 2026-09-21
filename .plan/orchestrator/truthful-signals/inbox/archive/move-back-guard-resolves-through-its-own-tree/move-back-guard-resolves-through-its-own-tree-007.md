envelope_version=1
sender_type=plan
sender_id=move-back-guard-resolves-through-its-own-tree
epic=truthful-signals
kind=candidate-lesson
created=2026-08-27T18:57:07Z

# A name-matching caller derivation misses alias-bound imports - escalating literal to AST does not leave the class

**Component**: `plan-marshall:manage-architecture` / audit-document derivation method
**Shape**: a rigour escalation that stays inside the class it was escalating out of.

## What happened

The plan's audit document (`manage-locks/standards/cwd-keyed-store-resolution-audit.md`)
derived its resolver-consumer population with an **invocation-form textual criterion** -
matching `get_base_dir(` rather than the bare name. CodeRabbit correctly diagnosed that
as counting comments, docstrings and `def` lines as calls: `tools-file-ops/scripts/
constants.py:251` matches inside a comment, calls nothing, and was nonetheless placed in
the both-resolvers intersection.

The reviewer then supplied **its own** derivation - an AST script matching `ast.Call`
whose callee `Name.id` / `Attribute.attr` is `get_base_dir` / `get_worktree_root` - and
proposed **9 / 6 / 2 / union 13**.

That figure is short by exactly one caller. `generate_executor.py:150` does
`import get_base_dir as _get_plan_base_dir` and invokes it at lines 168 and 172. Every
derivation that matches the **name at the call site** - the reviewer's AST script
included - reports that file as a mention rather than a caller. Re-derived truth:
**10 `get_base_dir` callers, 6 `get_worktree_root`, 2 shared, union 14.**

## The generalisable rule

**Moving up a rigour ladder is not the same as leaving the defect class.** Literal
matching and AST *name* matching are two rungs of one ladder: both answer "does this
identifier appear in call position", and neither resolves the **binding**. The exit from
the class is resolving the binding, not sharpening the match. A reviewer that correctly
names the methodological defect can, in the same breath, hand you a replacement figure
produced by the next rung of the same ladder.

## Directive - deriving a caller population for a symbol

1. **Stage 1 - bare-name sweep for candidates.** Sweep the bare name, not the invocation
   form. The result is a superset by construction, and that property is what makes the
   later narrowing auditable. (Here: 22 candidates.)
2. **Stage 2 - classify each candidate with AST** into call / definition / import /
   reference / text-only residue. Exclude the definition site *as a definition*; admit a
   file on independent call evidence.
3. **Stage 3 - resolve aliases.** For every `import X as Y` and `from M import X as Y`,
   add `Y` to the call-position name set **for that file**. Skip this and the derivation
   is a mention-count wearing a call-count's label - which is precisely the failure both
   the original criterion and the reviewer's correction exhibited, one rung apart.
4. **Publish the method next to the figures.** The audit's original defect was not only
   the wrong criterion: a "Completeness" bullet claimed the method WAS published when
   only one of four figures had one. A population figure with no published derivation
   cannot be re-checked and therefore cannot be corrected - only argued about.

## Second-order note for triage

A reviewer being **right about the defect and wrong about the replacement figure** is the
common case here, not an exception. Disposition `fixed` on the diagnosis while
**re-deriving the numbers independently**. Do not adopt a reviewer's counts on the
strength of its diagnosis - the two are separate claims with separate evidence.

## Evidence

- PR #1361 finding `410c92`, thread `PRRT_kwDOQ3xasM6c5aEs`, reviewed commit `fb7687d04`
  (carries both the reviewer's AST script and the re-derivation that refutes its counts).
- `marketplace/bundles/plan-marshall/skills/manage-locks/standards/cwd-keyed-store-resolution-audit.md`
  (the two-stage method as published).
- Plan `move-back-guard-resolves-through-its-own-tree`, merged `5f972ac15`.
