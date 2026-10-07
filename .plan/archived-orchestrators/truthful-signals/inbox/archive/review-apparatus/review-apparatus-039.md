envelope_version=1
sender_type=orchestrator
sender_id=review-apparatus
epic=truthful-signals
kind=finding
created=2026-09-13T21:22:39Z

# `project:finalize-step-deploy-target` documents a Step 1 command this repo's own hook denies

Observed first-party during `plan-pr-046`'s finalize (PR #1477, merged `77cb2e251`), reported by that
run and routed here from `review-apparatus` on 2026-09-13. ⭐ **Not PR/review subject matter**, so the
PR test does not claim it: this is a workflow-doc-versus-enforcement divergence, which is this epic's
theme.

## The divergence

- `project:finalize-step-deploy-target` documents **`./pw generate-claude`** as its Step 1.
- This repository's PreToolUse hook **rule R4 denies any Bash call whose first token is `./pw`**.
- The redirect R4 offers is a **dead end**: `architecture resolve --command generate-claude` returns
  `Command not found`, because a generator alias is not a canonical build command.

⇒ The documented command cannot be run, and the documented recovery cannot be reached. The step
completed on #1477 only by routing through the build executor instead — i.e. **the working invocation
is the undocumented one.**

## Operator decision, taken 2026-09-13

**The skill adopts the executor invocation as its documented Step 1.** R4 is left intact and gains no
carve-out; `architecture resolve` is not taught the alias.

The reasoning, recorded because the rejected arms were real: a carve-out would widen a deny rule whose
whole value is being unconditional, and every future generator alias would inherit the exemption
silently; teaching the resolver the alias is a resolver-contract change (generator aliases becoming
canonical build commands), which is a larger decision than the defect warrants. ⭐ The shipped
`PLAN-PR-017` settled this exact class — *a workflow doc prescribes a flag no script declares* — the
same way: **correct the doc to match the enforced surface.**

## What a fix has to cover

⛔ **Do not fix only the one line.** The failure class is *a documented command that the enforced
surface rejects*, and this instance was found only because a run happened to hit it. The deliverable is:

1. `project:finalize-step-deploy-target`'s Step 1 states the build-executor invocation that actually
   runs.
2. **Derive**, across the project-local `.claude/skills/` surface, every other documented Bash
   invocation whose first token is `./pw` — publish the population and the count, and correct each.
   A single-site fix over an underived population is the archetype this project keeps re-finding.
3. A check that keeps it true: if a documented invocation is denied by an installed hook rule, that is
   detectable at lint time rather than at finalize time on some future run.

⚠ **Lead, not instruction**: the `./pw` population above was NOT enumerated at HEAD in this checkout —
deriving it is item 2's job, and the count is unknown, not zero.
