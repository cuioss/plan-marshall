envelope_version=1
sender_type=plan
sender_id=plugin-doctor-detector-coverage-residue
epic=truthful-signals
kind=candidate-lesson
created=2026-08-25T07:37:30Z

component=plan-marshall:automatic-review
category=improvement
created=2026-08-25

# An optional-tier review bot found what 17 clean required-tier self-review rounds missed

## Context

The merge candidate for this plan had passed a whole-tree quality gate (37 rules, 0 issues), 21957
module tests, a clean whole-tree plugin-doctor run, and SEVENTEEN rounds of dispatched self-review
that converged to two consecutive clean results. CodeRabbit's re-review of that exact HEAD still found
a real correctness defect in shipped code: `_analyze_argument_naming.py` counting an undecided site as
decided -- this plan's OWN subject, introduced by the plan's own commit, and missed by an earlier fix
in the same plan whose commit message claimed to close four coverage over-claims but left a fifth,
structurally identical one. Confirmed by measurement: `blind_spots` went 292 -> 304 (+12) with
`population_size` unchanged at 2792.

## Root cause

pr-agent (the manifest's REQUIRED bot) reported "no major issues" on both reviews of a diff containing
this defect. sourcery (also configured) refused both times on the 150k diff-char hard quota. CodeRabbit
(the OPTIONAL bot) was the only reviewer to catch it, and this is the SECOND time on this same PR that
CodeRabbit was the sole reviewer to read the diff at all. Self-review convergence is not a substitute
for an independent reader -- 17 rounds of the same reviewer architecture converged clean on a defect a
different reader found immediately. This is a diversity argument, not an effort argument.

## Proposed action

Reconsider the manifest's required/optional bot split against measured per-bot yield rather than
leaving it as a static default: on this plan the "optional" bot found the merge-blocking defect while
the "required" bot found nothing across two reviews of the same diff.

## Evidence

- aspect: chat_history_analysis -- operator gate decisions in this session explicitly investigated why
  no bot fired ("why not triggered? A bug? check again") before approving a manual @coderabbitai
  trigger
- Finding 5bdbb9 in this plan's qgate store (pending at plan-close, routed to review-apparatus)
- Finding a02741 (same store) -- the second automatic-review firing whose comments (including the
  CodeRabbit round that found this defect) were never ingested into the finding store, so a
  review-retrospective comparison over the store alone would have understated this exact outcome
