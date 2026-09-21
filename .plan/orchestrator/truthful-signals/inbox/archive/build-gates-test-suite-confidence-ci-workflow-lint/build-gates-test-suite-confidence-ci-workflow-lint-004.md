envelope_version=1
sender_type=plan
sender_id=build-gates-test-suite-confidence-ci-workflow-lint
epic=truthful-signals
kind=candidate-lesson
created=2026-08-25T14:49:58Z

component=plan-marshall:phase-6-finalize
category=improvement
bundle=plan-marshall

# Head-dependent gates re-certify an unchanged tree because HEAD moved

PLAN-TRUTH-087 ran `verify` twice at roughly 450s each over trees whose CONTENT
was identical. The second run was triggered purely because HEAD had moved — a
rebase onto `origin/main` brought 5 upstream commits, and every gate keyed on
`head_at_completion` saw its recorded sha diverge from the live one.

Seven head-dependent gates re-fired after that rebase. All seven were
`invalidated` for `verdict_inputs_undeclared`: the gate could not state which
inputs its verdict depended on, so the framework could not establish that those
inputs were unchanged, so it conservatively assumed they were. The
conservatism is correct given an undeclared input set — the cost is paid
because the declaration is missing, not because the re-run was warranted.

The distinction that went unrepresented: a gate whose verdict depends on TREE
CONTENT is invalidated by a content change, and a rebase that fast-forwards
clean over untouched paths is not one. A gate whose verdict depends on the
merge-base relationship genuinely is head-dependent. Both were treated as the
latter.

## Solution

Give head-dependent gates a declared input set so the invalidation predicate
can be evaluated over content rather than over the sha alone. Concretely: a
gate that declares its verdict inputs (the path set it read, or a content hash
over them) can be re-validated by comparing THOSE inputs across the head move;
only a gate that declares nothing must be re-run wholesale.

`verdict_inputs_undeclared` is already the recorded reason, so the population is
observable — the seven gates that carried it on this run are the concrete
candidate list.

## Impact

At ~450s per verify and 7 gates re-firing per rebase, a plan that rebases more
than once pays this repeatedly; PLAN-TRUTH-087 recorded firing counts in the
10-14 range on several finalize steps. Every plan that rebases during finalize
is affected, and the cost scales with how busy `main` is rather than with
anything the plan did.
