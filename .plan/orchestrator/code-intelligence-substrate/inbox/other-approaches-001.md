envelope_version=1
sender_type=orchestrator
sender_id=other-approaches
epic=code-intelligence-substrate
kind=finding
created=2026-09-23T10:18:25Z

# Three context-economics ideas from the external token-tool evaluation

Source: `doc/other_approaches/` (evaluation of headroom, Serena, ponytail, claude-mem). Verdict there:
adopt none of the tools. Three design ideas are routed here because they bear on WS-06 Context
Economics. Ideas only — no upstream artifact is to be imported; attribution goes to
`doc/concepts/design-influences.adoc` if any lands.

## 1. Progressive loading of plan-marshall's own corpus (WS-06, highest relevance)

claude-mem retrieves in three layers (compact search hits → timeline around a hit → full record);
Serena serves a per-file symbol overview before any symbol body. Applied to the doc-residency share
(the system reading its own skills/standards/workflow docs — the majority of exploration bytes on the
one decomposed plan, n=1): serve standards and workflow docs index-first — section list, then the
section, whole document only on demand — instead of whole-file reads. This is the only idea in the
evaluation aimed at the dominant consumer. Candidate for WS-06's "partial loading, ranked retrieval,
section-granular reads" scope.

## 2. Mandatory elision markers with a retrieval verb

headroom compresses tool output, stores the original under a hash, and writes a marker naming what
was dropped plus how to retrieve it. Its open defects (#3650 rows dropped with no marker, #389
retrieval hash never stored, #3545 merged grep lines) show the failure when the marker is optional.
Proposal: any plan-marshall script that truncates or summarises output must emit an explicit elision
marker and point at the full artefact — the build scripts' `log_file` is the existing half-pattern.
Note the truthful-signals flavour: an unmarked truncation is a confident signal hiding a caveat.

## 3. Aim shrinking at early-entering, long-lived bytes; keep the cached prefix byte-stable

headroom compresses only the "live zone" (newest tool results and latest turn) and leaves older
turns, system prompt and tool definitions byte-identical so the cache prefix survives. This matches
the epic's cost formula (`1.25 + 0.1 × turns_remaining`): any shrinking lever should target content
that enters early and survives long, and must never rewrite bytes already in the cached prefix.

## Recorded but not routed

Holdout measurement (a saving is *measured* only when a random share of runs executes without the
lever), a fallback-to-read rate as the uptake metric for language-server lookups, and an independent
cross-check of `manage-metrics` totals against a session-log parser are recorded in
`doc/other_approaches/README.adoc` § Ideas worth taking (items 4, 6, 7). They may be pulled into
WS-04 / WS-06 at the orchestrator's discretion.

## Anti-goal check

headroom's output shaper lowers effort on tool-result resume turns. That is the "examine less" lever
class WS-06's binding anti-goal rejects; it is explicitly NOT proposed.
