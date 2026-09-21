envelope_version=1
sender_type=plan
sender_id=architecture-store-query-truthfulness
epic=code-intelligence-substrate
kind=candidate-lesson
created=2026-09-15T07:57:36Z

component=plan-marshall:plan-marshall
category=bug

# Concatenating two document regions made a marker leak across the excluded section

Source: PR #1489 CodeRabbit inline finding 0b2175 (resolution=fixed, TASK-038).

_numbered_lines_outside_section returns the pre-section region CONCATENATED with the
post-section region, and _unmarked_literal_hits carries one `previous` variable across
that seam. A marked final line before Section 2.15 therefore suppresses the first
unmarked literal AFTER it — one line of the narrowing guard's own region rendered
undetectable.

## Solution

Reset `previous` whenever the line numbers are not consecutive.

The general rule: when an exclusion is implemented by concatenating the surviving
regions, any state that depends on ADJACENCY is silently corrupted at the seam. A gap in
the line numbering is the available signal; carrying look-behind state across it is a
defect by construction.

## Impact

The narrowing exclusion added earlier in this same plan (TASK-029) introduced the seam
that this defect then exploited — a fix creating the conditions for the next finding.
