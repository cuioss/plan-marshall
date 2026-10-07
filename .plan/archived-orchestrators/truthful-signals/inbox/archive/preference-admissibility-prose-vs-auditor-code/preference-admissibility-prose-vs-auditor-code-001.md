envelope_version=1
sender_type=plan
sender_id=preference-admissibility-prose-vs-auditor-code
epic=truthful-signals
kind=candidate-lesson
created=2026-09-05T14:10:29Z

component=pm-plugin-development:ext-self-review-plan-marshall
category=bug
bundle=pm-plugin-development

# An anchor-driven sweep under-covers WITHIN its anchor, and its own coverage block cannot see the gap

## Rule

When a detector anchors on a *sub-unit* of the region a defect can occupy (the first line of a
docstring, the first line of a section, the heading of a table), a sweep driven by that anchor
surfaces **at most one site per anchored unit**. Multi-site families inside one unit are invisible
to it. The remedy that actually converges is to stop driving the round off anchors and read the
full `main...HEAD` diff for the file.

## Observation

The pre-submission self-review surfacer anchors on a docstring's FIRST line. An over-claim sitting
further down the same docstring is therefore never surfaced while the first-line claim is present.

Observed in PLAN `preference-admissibility-prose-vs-auditor-code`: a nine-site over-claim family
was resolved across **eight consecutive review rounds, each finding and deleting exactly one site**
— every round's sweep missing the next. Round 9 diagnosed the anchoring, switched to reading full
`main...HEAD` diffs, and rounds 10-12 came back clean. Twelve firings of the step were recorded
where three would have sufficed.

## Why the existing published caveats do not cover it

Two published fields would each be read as covering this, and neither does:

- **`structural_limit`** names the class the analysis cannot reach "however wide the sweep — the
  behaviour of the code under inputs the diff does not contain"
  (`extension-api/standards/ext-point-self-review-surfacing.md`). All nine sites were statically
  present in the diff. They were reachable; the anchor simply did not reach them.
- **`delta_coverage`** is **file-granular**: `files_with_candidates` counts a file once it
  surfaced *at least one* candidate. A file holding nine defect sites of which the round surfaced
  one is therefore recorded identically to a fully-covered file. The block that exists to say what
  the round observed is structurally blind to within-file under-coverage, so it will report a
  reassuring number on exactly the rounds this defect produces.

The archetype is the corpus's `volume-read-as-coverage` shape at a finer grain: N surfaced
candidates over N anchored units is a *count of anchors*, never a count of sites.

## How to apply

- **Detector side**: for any anchor whose unit can hold more than one instance of the defect, scan
  the whole unit and emit one candidate per site, not one per unit.
- **Coverage side**: a per-file `has ≥ 1 candidate` boolean cannot support a coverage claim. Where
  a within-unit population is derivable, publish sites-surfaced against sites-in-population.
- **Reviewer side**: a round that resolves *exactly one* site of an obviously repeated shape is a
  granularity symptom, not a completed round. Read the full file diff before accepting clean.
- **Loop-back side**: N consecutive rounds each closing exactly one finding is the signature. Treat
  the second such round as evidence about the instrument, not about the code.
