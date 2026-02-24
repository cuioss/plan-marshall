# Consistency and Duplication Review

## What to look for

**Term drift** — The same concept called different names across documents. Example: "script notation" in one file, "3-part notation" in another, "executor notation" in a third. Collect all terms for key concepts and flag divergence.

**Contradictory rules** — Two documents giving opposite guidance. Example: SKILL.md says "load all references upfront" while a standards doc says "load on-demand." One must be wrong.

**Redundant content** — Same information in multiple files without cross-referencing. Acceptable duplication: a brief summary in SKILL.md that points to detail in standards/. Unacceptable: full explanations repeated verbatim or near-verbatim.

**Scope overlap between documents** — Two standards files covering the same topic from slightly different angles without a clear division of responsibility. The reader (LLM) can't tell which is authoritative.

**Internal contradictions** — Within a single document, earlier sections contradicting later ones. Often happens when documents are incrementally updated without reviewing the whole.

## Judgment calls

- A one-line summary in SKILL.md restating what's detailed in `standards/foo.md` is acceptable (navigation aid)
- Cross-skill duplication (content repeated from another skill in the same bundle) is a higher severity issue than within-skill duplication
