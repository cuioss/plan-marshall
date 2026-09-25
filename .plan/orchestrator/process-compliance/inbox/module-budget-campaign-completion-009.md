envelope_version=1
sender_type=plan
sender_id=module-budget-campaign-completion
epic=process-compliance
kind=finding
created=2026-09-25T13:58:00Z
revision=1

# Process-rule issue: the documented cwd re-anchor (`cd {worktree_path}`) is not durable on the opencode target, so every `.plan/` call needs an explicit per-call cwd

Reporter: plan `module-budget-campaign-completion`, `workflow/execution.md` Step 0 entry preflight.

## Observation

`plan-marshall/workflow/execution.md` § "Step 0: Entry-point preflight" instructs the
orchestrator, on `location == worktree`, to:

> issue a STANDALONE `cd {worktree_path}` Bash call (exactly one command — no `&&`, no
> chaining) … After the `cd`, cwd is pinned to the worktree and the single uniform
> cwd-relative rule resolves every subsequent `.plan/` lookup to the worktree-resident copy.

`phase-6-finalize/SKILL.md` § "Orchestrator cwd-pinning" and the ADR-002 model rest on the
same assumption: "a subprocess cannot mutate its parent's cwd … the orchestrator reads the
returned `worktree_path` and pins its own working directory there for the remainder of
phase-5+".

On this target the `cd` does not persist across tool calls:

```
$ cd /home/oliver/git/plan-marshall/.plan/local/worktrees/module-budget-campaign-completion
$ pwd
/home/oliver/git/plan-marshall
```

Each Bash invocation runs in a fresh shell rooted at the session cwd, so the "pin" is a
no-op. Every subsequent `.plan/execute-script.py` call in this session had to be issued with
an explicit per-call working directory, and every `Skill:` dispatch inherited the MAIN
checkout as its cwd.

## Consequences, in order of severity

1. **The cwd-relative resolution rule is broken for the whole phase.** The documents state
   that a pinned cwd is what makes `.plan/` resolve to the worktree-resident plan state.
   Without a durable pin, a caller who follows the rules verbatim resolves `.plan/` on main
   and silently gets `plan_not_found` (or, worse, main's stale plan copy) for a
   phase-5+ plan.
2. **`WORKTREE` forwarding becomes load-bearing rather than a salience reminder** — the
   agent contract already says so ("`WORKTREE` is authoritative … the orchestrator resolved
   this once"). This finding is the mechanism behind
   `module-budget-campaign-completion-006`: without cwd inheritance the repo-relative
   `WORKTREE` value is the *only* thing telling a leaf where the worktree is, so it must be
   correct and must be forwarded — the opposite of what `execution.md` currently claims.
3. **It is silent.** Nothing reports a lost pin. Every symptom surfaces later as a
   wrong-tree or not-found error in a different component.

## Siblings in the same family

- `phase-6-finalize/SKILL.md` § "Return-to-main ordering" step 2, which states the return is
  "a convention rather than an enforced precondition … no script asserts it". On this target
  the convention is not even achievable, and the only guard that does assert it
  (`worktree-remove` refusing `cwd_inside_removal_target`) fires precisely because the pin
  was never established.
- `phase-5-execute` / `execution.md` statements that a dispatched subagent "inherits the
  orchestrator's pinned cwd" — not true here.

## Requested

Either (a) document the per-target reality: on opencode the pin must be re-issued per call and
`WORKTREE` must always be forwarded, or (b) make the pin observable (a resolver that reports
which checkout a call will bind to) so a lost pin is caught at the point it is established
rather than three components later.

## Evidence

- `cd` / `pwd` pair above.
- The first `manage-logging decision` call of this session was deliberately issued **after**
  the `cd`, from an explicit workdir, because the documented ordering ("log, then `cd`")
  would have logged against main, where this plan's directory does not exist. That
  reordering is itself a symptom: the documented order only works if the pin is durable.
