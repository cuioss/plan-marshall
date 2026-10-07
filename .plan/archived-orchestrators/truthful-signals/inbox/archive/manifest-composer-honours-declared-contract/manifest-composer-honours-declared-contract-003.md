envelope_version=1
sender_type=plan
sender_id=manifest-composer-honours-declared-contract
epic=truthful-signals
kind=candidate-lesson
created=2026-07-27T19:25:34Z

component=pm-plugin-development:plugin-doctor
category=bug
bundle=pm-plugin-development

# no-historical-prose Family 3 matches bare `an earlier` with any noun, rejecting correct positional prose

## Context

Observed first-hand during phase-6-finalize of PLAN-75
(`manifest-composer-honours-declared-contract`, PR #1025). The
`no-historical-prose-in-skills` rule flagged two lines that contain no historical
narrative at all — both used "earlier" to denote **a position in a list**, not a point
in project history:

```text
a step whose resolved `order` is less than the maximum seen at an earlier position
A step's resolved `order` is strictly less than the maximum resolved `order`
at an earlier list position.
```

Both lines describe the ascending-order gate's present-tense semantics. There is
nothing to fix in either. The finding nevertheless blocked the finalize
plugin-doctor step and cost an extra commit on the branch
(`9caa8c54e chore(finalize): reword positional 'an earlier' to satisfy
no-historical-prose gate`) whose entire content is substituting "a preceding
position" for "an earlier position" in two files.

## Root cause — the pattern is asymmetrically constrained

`_analyze_historical_prose_in_skills.py`, Family 3:

```python
_EARLIER_PROPOSAL_RE = re.compile(
    r'\b(?:an\s+earlier|the\s+earlier|earlier\s+(?:proposal|approach|version|alternative|design|form))',
    re.IGNORECASE,
)
```

The third alternation branch is correctly constrained — bare `earlier` matches only
when followed by one of six history-bearing nouns. The **first two branches are not**:
`an earlier` and `the earlier` match regardless of what noun follows, so
`an earlier position`, `an earlier list position`, `an earlier index`, `an earlier
element`, `the earlier row` all trip a rule whose own docstring describes the family as
"prose describing an alternative approach that was considered and rejected"
(example: `An earlier proposal ... suggested ... That approach was rejected`).

The analyzer's own documented intent and its implemented predicate disagree — this is
the doc-contract-divergence archetype inside a lint rule.

## Why it matters beyond one reword

A rule that blocks a build on correct prose does not improve the corpus; it trains
authors to reword *around* the detector. The reword commit here made the sentence no
clearer and fixed no defect — it purchased a green gate. Repeated, this erodes the
credibility of every finding the rule emits, including its true positives, and it is
invisible in the metrics because the "fix" looks like compliance.

Note also the asymmetry that makes this expensive: the rule's `RuleDescriptor` declares
`severity='warning'`, yet the finding was gating in practice. A rule whose declared
severity and whose operative blocking behaviour disagree is worth reconciling in its
own right.

## The rule

- A **build-gating** content-lint pattern must be constrained to its documented intent.
  Where a family already demonstrates the right shape (branch 3's noun allowlist),
  every branch in that family must carry the same constraint — a half-constrained
  alternation is an overfit hiding behind a correct sibling.
- Concretely: require a history-bearing noun after `an earlier` / `the earlier` too,
  or exclude the positional-noun set (`position`, `index`, `list`, `element`, `entry`,
  `row`, `step`, `line`) explicitly.
- Every content-lint rule promoted to build-failing needs at least one **negative**
  fixture asserting a legitimate use of its trigger token is NOT flagged. Family 3 has
  positive fixtures for the rejected-proposal shape; a positional-use negative fixture
  would have caught this before promotion.
- Prefer a documented suppression path over a reword when prose is correct: a reword
  that exists only to satisfy a detector is a silent false-positive, not a fix, and it
  leaves no record that the rule misfired.

## Related

- `2026-07-13-17-001` — plugin-doctor static analyzers over-approximate when their
  model omits a mechanism; same over-approximation family, different mechanism (there,
  a runtime dispatch; here, an under-constrained regex branch).
- `2026-07-16-08-001` — promoting a filesystem-walking analyzer to a build-failing gate
  surfaced unintended matches; same "promotion outruns precision" shape.
