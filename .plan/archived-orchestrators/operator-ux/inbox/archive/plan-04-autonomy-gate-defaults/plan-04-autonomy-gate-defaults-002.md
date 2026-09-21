envelope_version=1
sender_type=plan
sender_id=plan-04-autonomy-gate-defaults
epic=operator-ux
kind=candidate-lesson
created=2026-09-07T12:35:18Z

component=pm-plugin-development:ext-self-review-plan-marshall
category=bug
confidence=high
source_plan=plan-04-autonomy-gate-defaults

# Self-review candidate surfacer has no .adoc detectors, so AsciiDoc is invisible

## Context

The pre-submission self-review ran four rounds over a footprint containing three
`.adoc` files:

- `doc/user/configuration.adoc` (+73/-3 — the largest MODIFIED file in the diff;
  only the wholly-new 496-line test file is larger)
- `doc/user/getting-started.adoc` (+1/-1)
- `doc/user/parallelism-and-locking.adoc` (+1/-1)

The candidate surfacer produced zero candidates for any of them, in every round.

The empirical signature is visible in the finding store. Of the 10 recorded
`qgate-6-finalize` findings, the three carrying
`component: pm-plugin-development:ext-self-review-plan-marshall` — the
surfacer-attributed ones — are all on `.md` files (`wizard-flow.md` ×2,
`menu-configuration.md`). All four findings on `configuration.adoc` carry
`component: plan-marshall:phase-6-finalize` instead: they came from a leaf
reading the file directly, off-candidate.

Four of ten findings, including both findings from round 1's largest cluster,
landed on a file the surfacer structurally cannot see.

## Root cause

The detectors gate on `.md` and nothing else. `_self_review_detectors.py` carries
at least a dozen `path.endswith('.md')` guards (lines 97, 127, 210, 309, 426,
443, 821, 860, 1172, 1990, 2413) plus `.md`-scoped globs at 284 and 344, and
`self_review.py`'s documented paths-glob example is
`marketplace/bundles/*/skills/*/standards/*.md`.

The string `adoc` does not occur anywhere under
`marketplace/bundles/pm-plugin-development/skills/ext-self-review-plan-marshall/`.

This is not a tuned exclusion — AsciiDoc was never considered. The markdown
structural detectors (section symmetry, count-prose staleness, same-document
ordinal references, source-of-truth duplicates, closure-claim enumerations) all
have exact AsciiDoc analogues, and `configuration.adoc` is where this project's
user-facing normative prose actually lives.

## Proposed action

Extend the markdown detectors to AsciiDoc rather than adding a parallel
detector family. Concretely:

1. Replace the `path.endswith('.md')` guards with a shared
   `_is_prose_document(path)` predicate covering `.md` and `.adoc`.
2. Teach the section/heading detectors AsciiDoc's `=`/`==`/`===` heading form
   and its `[NOTE]`/`[IMPORTANT]`/`====` block delimiters alongside markdown's
   `#` and fenced-code forms — the fence-state tracking already present for
   ` ``` ` has a direct `----` / `====` counterpart.
3. Add a regression test asserting that a footprint containing only `.adoc`
   files yields a non-empty candidate set, so the zero cannot silently return.

Until then, the surfacer's zero over an `.adoc`-bearing footprint is a
coverage gap, not a clean result, and should be reported as such.

## Evidence

- aspect: artifact_consistency — 3 `.adoc` files in the 27-path realized
  footprint; `configuration.adoc` is the largest modified file at 76 changed
  lines.
- Finding store `qgate-6-finalize.jsonl`: 3/3 surfacer-attributed findings on
  `.md`; 4/4 `configuration.adoc` findings attributed elsewhere.
- Zero occurrences of `adoc` in the `ext-self-review-plan-marshall` tree.
