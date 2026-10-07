envelope_version=1
sender_type=plan
sender_id=architecture-store-query-truthfulness
epic=code-intelligence-substrate
kind=candidate-lesson
created=2026-09-15T07:52:52Z

component=plan-marshall:manage-architecture
category=anti-pattern

# An identifier-anchored consumer sweep is blind to every prose spelling of the same concept

Source: Q-Gate finding d31c6a (5-execute, resolution=fixed by TASK-028).

D2's Clean-break note enumerated consumers of the REMOVED available/unavailable literal
(6 files, clean coverage) and that enumeration held. It did NOT enumerate consumers of
the OTHER half of D2 — the module_edges.status SEMANTIC change. Re-derived at HEAD,
architecture search --content --literal --pattern module_edges returned count 23 /
file_count 12 over files_scanned 5442 with unreadable[] empty, truncated false,
elided[] empty.

All 7 out-of-footprint candidates were then read and judged: 5 divergent, 2 consistent,
0 unjudged.

## Solution

Two corrections the closing pass had to make to its own framing, and both are the
lesson.

1. One candidate was listed as "already in D3's surface and correctable" but turned out
   NOT divergent, so no edit was owed. A candidate list is not a defect list.
2. Two divergent files (doc/user/code-search.adoc, doc/concepts/code-intelligence.adoc)
   carry no `module_edges` identifier AT ALL. They were reached only by widening the
   sweep to the prose spelling "module edges". An identifier-anchored sweep would have
   shipped both unfixed while reporting clean coverage over a trustworthy population.

When the change is to a CONCEPT rather than a token, sweep the prose spellings too, and
say which spellings were swept.

## Impact

Four out-of-footprint divergences had to be filed rather than fixed in place.
