envelope_version=1
sender_type=orchestrator
sender_id=lessons-routing
epic=live-blockers
kind=finding
created=2026-11-02T11:19:34Z

# ref-svg-diagrams: image macro alt text with commas, and document-global `:imagesdir:`

Severity: low. Domain content, filed under RULING 2026-10-09 (operator-confirmed for this sweep); may be discarded under the `live-blockers` FOCUS RULE.
Bundle: `pm-documents` (ref-svg-diagrams, asciidoc-embedding).

## Source

nifi-extensions `2026-07-18-21-001` (doc/ PlantUML-to-SVG migration), verbatim in `lessons-routing/lessons-archive/filed-live-blockers/sweep-2026-11-02/nifi-extensions/`.

## Observation

Review caught three recurring classes: (1) an SVG filename did not match its content; (2) alt text containing a comma was split into positional attributes and truncated; (3) a document-level `:imagesdir:` rebased every image in the page and broke sibling screenshot references.

## Ground truth (c431a8193)

`asciidoc-embedding.md:7` already ties the filename to the diagram title slug (class 1 in part). `:22` and `:44-52` describe alt text as the first positional attribute but say nothing about quoting commas. `:imagesdir:` is not mentioned anywhere in the ref-svg-diagrams standards.

## What to consider

Double-quote alt text containing a comma. Warn that `:imagesdir:` is document-global and require re-checking every other image reference when it is introduced. Add an open-and-compare check of each SVG against its filename.
