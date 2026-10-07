envelope_version=1
sender_type=plan
sender_id=move-back-guard-resolves-through-its-own-tree
epic=truthful-signals
kind=candidate-lesson
created=2026-08-27T18:48:46Z

component=plan-marshall:manage-architecture
category=bug
confidence=high
source_plan=move-back-guard-resolves-through-its-own-tree
source_pr=1361

# search --content top-level count is a row count and reads as an occurrence count

## Context

Deliverable 7 of this plan existed specifically to replace an **asserted** population with a **derived** one. The derivation was performed four times by four different readers and produced four different answers:

| # | Derivation | Answer | Fate |
|---|-----------|--------|------|
| 1 | Outline, from `architecture search --content` top-level `count` | 6 | Published; refuted at phase-4 Q-Gate |
| 2 | Q-Gate correction (decision 0deb27) | 7 | Published; superseded by the document's own later edits |
| 3 | CodeRabbit, by hand itemization on the PR | 4 | Refuted — missed the parenthetical at line 165 |
| 4 | Verified re-derivation (`--literal` under both attributions, plus a Read) | 8 | Held |

Answer 1 was wrong because the top-level `count` is a result-**ROW** count, inflated by dual module attribution: the same file is attributed to both the `default` and `plan-marshall` modules, so its matches are counted twice. Answer 3 was wrong for the opposite reason — a name-matching hand pass that misses an aliased or parenthetical occurrence. Both errors are the same class the audited document itself warns about.

## Root cause

`search --content` publishes one number under the name `count`, and that number answers a question ("how many result rows did the inventory produce, across all module attributions") that is almost never the question a caller is asking ("how many occurrences", or "how many files"). The three quantities differ, and nothing in the output shape says which one is being read. A caller who wants an occurrence count has to know about the dual-attribution behaviour to avoid over-counting, and nothing in the response teaches them.

The ambiguity is in the output shape, not in any single reader — which is why four readers produced four answers and three of them published theirs as fact first.

## Proposed action

Have `search --content` report all three quantities distinctly and unconditionally — `row_count`, `occurrence_count`, `file_count` — retiring the bare `count` key, or at minimum labelling it (`count_basis: rows`). A caller that publishes a population figure in prose then has an unambiguous field to cite, and the "derive completeness, never assert it" discipline actually reaches a derivable number.

Secondary: the existing `--literal` mode plus the per-attribution split should be documented as the canonical way to derive an occurrence count for a claim that will be published, since that is the path that produced the only answer that survived.

## Evidence

- decision.log 0deb27 (2026-08-27T06:42:22Z) — "root cause = architecture search --content top-level count is a ROW count double-counted across the default and plan-marshall module attributions, not an occurrence count"
- decision.log dd0b33 (2026-08-27T15:20:34Z) — "architecture search --content --literal at HEAD returns match_count 4 for the audit doc under BOTH attributions … so summing over one attribution gives the documented 8 … CodeRabbit's hand itemization found 3, missing the parenthetical at :165 — which is the cancelling-errors hazard that same section warns about"
- aspect: chat_history_analysis — pivot at turn_index 7
