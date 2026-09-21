envelope_version=1
sender_type=plan
sender_id=plan-150-close-the-namespace-conversion
epic=test-quality
kind=candidate-lesson
created=2026-09-02T21:59:54Z

component=pm-plugin-development:ext-self-review-plan-marshall
category=anti-pattern
title=Hoisting a binding to the top of a file leaves later rebindings shadowing it, invisibly to a green suite
source_plan=plan-150-close-the-namespace-conversion
source_signal=qgate_findings
source_findings=3571dd,936a51
confidence=high

# Hoisting a binding to the top of a file leaves later rebindings shadowing it

Two of this plan's four 6-finalize Q-Gate findings are the same defect in two
files, produced by the same mechanical edit. The conversion hoisted a script
address into module constants and rewrote the top-of-file binding:

```python
SCRIPT_PATH = get_script_path(_ARCH_BUNDLE, _ARCH_SKILL, _ARCH_SCRIPT)  # line 33
```

but a pre-existing module-level binding of the *same name* survived untouched
further down the file:

```python
SCRIPT_PATH = get_script_path('plan-marshall', 'manage-architecture', 'architecture.py')  # line 382
```

Python rebinds at module scope in source order, so every `run_script(SCRIPT_PATH, ...)`
below the later line uses the **literal**, not the constant-derived value. The
hoist was cosmetic for those tests.

Instances: `test_overview.py:382` (`3571dd`) and `test_graph_queries.py:602`
(`936a51`, shadowing the routing-contract tests including
`test_architecture_rejects_both_routing_flags`).

## Why a green suite cannot detect this

The two values coincide today, so nothing was broken and the whole tree verified
green (23,739 tests). That is the entire problem: **the defect is a latent seam,
not a live failure.** Editing `_ARCH_SCRIPT` would move the `parse_ns` calls to a
different script while every `run_script` test below the shadowing line silently
kept hitting `architecture.py` — reintroducing exactly the parser-vs-invocation
divergence this plan existed to remove. No test can fail until someone makes that
edit, and by then the constant looks authoritative.

## The rule

When a refactor introduces or rewrites a module-level binding for name `N`,
**sweep the whole file for other assignments to `N`**, not just the region being
edited. Top-of-file placement creates the *appearance* of a single source of
truth while a later assignment silently holds the real one.

The fix is **deletion of the redundant later binding**, never a second edit
bringing it into line. Two bindings kept in sync are the same defect one step
deferred; one binding is the invariant.

This generalizes past this plan's idiom. Any mechanical sweep that hoists a
repeated literal into a named constant carries the same risk, because the sweep's
attention is on the *hoist site* while the defect lives at an *untouched* site
the sweep never visited.

## What worked, and what it argues for

The `source_of_truth_drift` detector in `ext-self-review-plan-marshall` caught
both instances in one round, correctly grouped them as one class
(`2 finding(s) in this class this round`), and prescribed the convergent deletion
fix. Nothing upstream did — not review, not the full suite.

So the actionable content is not "add a detector"; it is that this detector is
the *only* thing standing between a hoist-shaped diff and a latent shadowing seam,
which argues for treating it as a required check on any diff that introduces a
module-level constant, rather than one heuristic among many. Two independent hits
on a single well-executed plan is a meaningful base rate.

## Routing note

Filed against `pm-plugin-development:ext-self-review-plan-marshall` because that
component owns the detector that caught it. The preventive half — an authoring
rule for hoist-shaped refactors — may belong with test-authoring standards
instead, or in both places. The orchestrator holds the cross-plan context for
that call.
