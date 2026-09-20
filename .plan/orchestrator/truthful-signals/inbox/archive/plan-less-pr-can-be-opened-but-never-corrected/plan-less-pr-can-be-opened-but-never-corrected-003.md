envelope_version=1
sender_type=plan
sender_id=plan-less-pr-can-be-opened-but-never-corrected
epic=truthful-signals
kind=candidate-lesson
created=2026-07-30T12:05:06Z

component=pm-plugin-development:plugin-doctor
category=bug
bundle=pm-plugin-development

# An AST detector must derive its node-shape population, not the shapes its motivating example happened to use

## Observation

The new `_analyze_plan_path_in_scripts.py` detectors (D6 of PR #1065) shipped with two
independent node-shape defects, both found by CodeRabbit and both remediated as TASK-014:

1. **Load/Store conflation.** The `Subscript` signal matched `ast.Subscript` regardless of
   its `ctx`, so it fired on both `ast.Load` (a read — the bypass the rule targets) and
   `ast.Store` (a write — an *emitting producer* legitimately assigning the value). A
   producer's own assignment was reported as a bypass read: a false positive that inverts
   the rule's meaning.

2. **Missing `ast.Attribute`.** Both detectors collected only `ast.Name` and `ast.Constant`
   nodes. A guard written as `args.body_file` is an `ast.Attribute` whose identifier lives in
   `.attr`, so it was invisible to the detector. A dormant `args.body_file` guard evaded
   detection entirely — a false negative with no visible symptom.

The detector's own test suite was green. Neither defect produced a failing signal, because
the suite exercised the node shapes the author had in mind while writing the detector.

## Why this is the epic's theme

A detector's confidence is bounded by the node-shape population it enumerated, not by the
number of tests that pass. Both defects here are the same failure: the shape population was
*sampled from the motivating example* rather than *derived from the language*.

This is the AST-level sibling of the standing rule "every set-guarding detector must be
population-derived". The set here is not a roster of files or dispatch targets — it is the
set of AST node shapes through which the target expression can be spelled.

## Corrective rule

When writing or reviewing an AST-based detector:

1. **Enumerate the spellings, not the example.** For any identifier the rule cares about,
   list every AST node type that can carry it: `ast.Name.id`, `ast.Attribute.attr`,
   `ast.Constant.value` (string keys), `ast.keyword.arg`, subscript keys. Justify each
   exclusion; do not leave one out silently.
2. **Discriminate `ctx` whenever the rule's meaning depends on read-vs-write.** A bare
   `isinstance(node, ast.Subscript)` / `ast.Name` test that ignores `node.ctx` will fire on
   producers as well as consumers. If the rule is about *reading* a value, require
   `ast.Load`; if about *writing*, require `ast.Store`.
3. **Test the negative shape explicitly.** Add a case for each enumerated spelling the
   detector must catch AND a case for the `ctx` it must NOT fire on. A detector suite with
   no false-positive case has not tested the discrimination it claims.

## Recurrence context

Both halves shipped in the *same* deliverable whose stated purpose was "guard against
straggler consumers with a population-derived check" — i.e. the population-derivation
discipline was applied to the consumer roster and not to the detector's own node shapes.
