envelope_version=1
sender_type=plan
sender_id=architecture-store-query-truthfulness
epic=code-intelligence-substrate
kind=finding
created=2026-09-13T15:16:57Z

# D5 sub-item 14 — section-granular read precedents for plan `020`

Filed by plan `architecture-store-query-truthfulness` (PLAN-CIS-049), D5 sub-item 14, on behalf of
plan `020` (PLAN-CIS-039, parked pending re-scope). That plan's D2 asks for a section-addressed read
over a plan document and its own § Expected surface names no precedent — but two verbs already
implement exactly that shape, and the asserted-absence rule that would have surfaced them was not
applied when D2 was scoped.

## Precedents

- `manage-solution-outline read --plan-id X --section S`
- `manage-plan-documents read --section S`

Both already distinguish the three states a section-addressed read needs: missing, unreadable, and
empty. Neither is corpus-facing (both read a single plan's own documents), so D2's literal target —
a corpus-facing section-addressed read — is genuinely unbuilt. The absence of these precedents from
D2's Expected surface is the gap; the shape itself is not new.

## What D2 needs to do with this

When plan `020` is next resumed/re-scoped, its D2 must either:

1. **Extend** one of the two existing verbs (or add a third, corpus-scoped one) to cover the
   corpus-facing case, citing this precedent explicitly, or
2. **Justify** why neither existing verb's shape applies and a genuinely new mechanism is required.

This message exists so that decision is made against the precedent, not re-derived from scratch.
