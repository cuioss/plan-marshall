envelope_version=1
sender_type=plan
sender_id=freshness-gate-says-fresh-unexamined-tree
epic=truthful-signals
kind=candidate-lesson
created=2026-09-06T17:28:26Z

component=plan-marshall:plan-retrospective
category=bug
confidence=high
source_plan=freshness-gate-says-fresh-unexamined-tree
source_pr=1425

# Four aspects report clean over an input channel the pipeline never supplies them

## Context

Four separate instances of one shape surfaced while running this retrospective. Each
aspect completes, publishes a clean or empty result, and the result is over a channel
the aspect could not read.

**(a) A forwarded finding with no receiver.** `check-artifact-consistency` graded
`affected_files_exact_match` as `warn` (3 outline-only files, 2 references-only),
downgraded it to a single `info` finding, and set `forwarded_to_manifest: true`.
`check-manifest-consistency` runs five checks — `manifest_version_recognized`,
`docs_only_diff`, `early_terminate_diff`, `tests_only_diff`, `branch_cleanup_changes`
— and **none of them is a declared-vs-realized set comparison**. The forward has no
receiver, so a real 3-file delivery gap was detected and then lost.

**(b) An aspect blind to its own declared input.** `permission-prompt-analysis` names
the session transcript as its input. The pipeline supplies only
`extract-chat-signal`'s reduction, which keeps operator-authored turns and recovered
gate decisions — here 4 turns of 1689. A permission prompt travels on the tool-result
denial channel, which the reduction drops. The aspect's zero is a zero over 4 turns.

**(c) A schema field the producer cannot emit.** `logging-gap-analysis.md`'s fragment
shape mandates a `VERIFY` observed count. `analyze-logs` publishes `top_tags[5]` only
— on this plan STATUS 79, ARTIFACT 72, STEP 50, SKILL 49, DISPATCH 37 — so any tag
outside the top five has no published count and the row can only be fabricated or
silently dropped.

**(d) A zero verdict beside its own low-confidence disclosure.** `check-dispatch-audit`
publishes `findings[0]` and `counts.total: 0` alongside `channel_completeness.confidence: low`,
`ratio: 0.27`, and `no_evidence: 9` of 16 finalize steps. The block-level honesty is
real; the section-level verdict that `compile-report` renders is `0 findings`.

## Root cause

In every case the aspect's contract and its actual input were specified separately and
drifted. (a) is a producer naming a consumer that has no matching check; (b) and (c)
are consumers declaring an input richer than the producer emits; (d) is a top-level
summary that does not inherit its own sub-block's confidence.

The common failure is that none of the four is *wrong* at the field level — each
publishes accurate values — and all four are wrong at the level a reader consumes.

## Proposed action

1. **(a)** Either add a declared-vs-realized set check to `check-manifest-consistency`,
   or drop `forwarded_to_manifest` and let `artifact-consistency` keep the `warn`.
   A forward whose target has no matching check must not downgrade the severity.
2. **(b)** Either extend `extract-chat-signal` to retain permission-denial turns, or
   change `permission-prompt-analysis` to declare the reduction as its input and
   publish its `evaluated_population` on every run, zero included.
3. **(c)** Have `analyze-logs` publish counts for the tag set the consuming schemas
   name, not only the top five; or remove the `VERIFY` row from the mandated shape.
4. **(d)** Propagate `channel_completeness.confidence` into a top-level finding, so a
   `low` confidence cannot render as a clean section.
5. Generalise: `compile-report` already probes for `sections_unattributed_zero`.
   Extend the probe to flag a section whose `findings: []` sits beside a
   self-declared low confidence or a non-zero `no_evidence` count.

## Evidence

- aspect: artifact_consistency — `affected_files_exact_match.status: warn`, `forwarded_to_manifest: true`, 3 `outline_only` files
- aspect: manifest_decisions — `checks[5]`, none comparing declared to realized sets; `findings[0]`
- aspect: permission_prompt_analysis — `raw_turn_count 1689`, `reduced_turn_count 4`, `dropped_turn_count 1685`
- aspect: log_analysis — `top_tags[5]` is the whole published tag surface
- aspect: execution_context_dispatch_audit — `findings[0]` with `confidence: low`, `no_evidence: 9`, `ratio: 0.27`
