envelope_version=1
sender_type=plan
sender_id=metrics-record-cannot-represent-re-entered-phase
epic=truthful-signals
kind=candidate-lesson
created=2026-08-09T21:02:19Z

# Candidate lesson: "cannot disagree" asserted over two byte-identical literals is agreement by coincidence, not by construction

**Source**: Q-Gate findings `6c64ad` and `44ba3b` (6-finalize), both `fixed`
**Defect class**: contract_drift / vacuous guard
**Theme fit**: confident-signal-hides-a-caveat — the confident signal is the word "cannot"

## The finding

Three surfaces — the `_count_deliverables` docstring, `data-format.md:497`, and `manage-metrics`
SKILL.md:147 — all asserted that `generate` calls the *same* section-scoped extractor that
`manage-solution-outline list-deliverables` uses, and concluded from that premise that **one plan
cannot carry two disagreeing deliverable counts** and **the two producers cannot disagree**.

The premise was false. `cmd_list_deliverables` calls `extract_deliverables`, which routes through
`split_deliverable_blocks`, whose heading regex was a **second literal copy** of the same pattern
inside `_plan_parsing.py` (line 122 for `extract_deliverable_headings`, line 147 for
`split_deliverable_blocks`).

> The counts agreed only because those two literals happened to be byte-identical. Nothing pinned
> them together. The asserted structural impossibility was not delivered by the code.

## The compounding half — the test that "pinned" it never invoked the other producer

`test_denominator_sampling_point.py:444` carried the docstring *"The metrics counter and
manage-solution-outline return ONE number"* — and never invoked `manage-solution-outline` at all.
It re-evaluated the production expression. A divergence introduced in `split_deliverable_blocks`
would have passed it green.

This is the same shape as the epic's standing rule that **N passing checks of a pure function is
ONE assertion repeated N times**: the test's name described a cross-producer agreement, its body
tested a single producer against itself.

## What the fix did right (worth copying)

The remedy taken was **structural, not a reworded claim**: the two literal regex copies were
collapsed into one module-level `DELIVERABLE_HEADING_PATTERN` that both extractors match through,
so the two producers now agree *by construction*. The test was rewritten to invoke the real
`cmd_list_deliverables` (imported via importlib), so a divergence in `split_deliverable_blocks`
now fails the pin. A third test asserts the pattern is compiled exactly once.

Note the choice explicitly rejected: narrowing the three prose claims to match the weaker reality
was available and cheaper. It was rejected in favour of making the strong claim TRUE.

## Candidate rule

> A documented impossibility ("cannot disagree", "structurally impossible", "guaranteed by
> construction") is a claim about a MECHANISM. Before writing it, name the object that enforces it
> — one shared constant, one shared function, one type. If the only thing enforcing it is that two
> pieces of source text currently look the same, the correct word is "agree by convention", and
> the correct fix is to introduce the missing shared object.

Corollary for tests: a test whose name asserts agreement BETWEEN two producers must invoke both.
Re-evaluating one producer's own expression proves nothing about the other.
