# PLAN-CIS-060: The re-grounding verdict field is unreadable one way and unwritable the other

epic: code-intelligence-substrate
workstream: WS-07

> Staged plan spec — one shippable unit of work, ready for `/plan-marshall` hand-off.
> Lives at `plans/PLAN-CIS-060-verdict-field-read-and-write-integrity.md` and is queued in the epic
> `status.json` `plans[]` field. The orchestrator EMITS the command below; it never launches the plan
> inline. This spec is SELF-SUFFICIENT: the emitted command is a one-line pointer and carries no
> brief, so every per-plan carry is authored here and nowhere else.
> See `persona-plan-orchestrator/standards/orchestration-model.md` for the tier and hand-off contract.

> ⛔ **AUTHORING CONSTRAINT — this spec's own `## Claim Labels` section MUST use top-level `- `
> bullets.** A table or a prose paragraph parses to zero claims (see D1), which would make this spec
> an instance of the very defect it fixes and would silently pass `next`'s prep-ready test. Verify
> after any edit with `corpus verdicts --slug code-intelligence-substrate` and confirm this spec
> contributes a non-zero row count.

## Objective

The re-grounding verdict field — the mechanism `next` gates prep-readiness on — is broken in **both
directions on the same input**, and the two halves have to be fixed together or the fix makes things
worse. On a spec whose `## Claim Labels` section expresses claims as a markdown **table** or as a
**prose paragraph**, the parser returns zero claims *silently*: the read side then admits the spec
vacuously (no row carries `admits: false` because there are no rows), and the write side refuses every
`--claim-index` as out of range, so the verdict can never be stamped. Fixing only the read side — the
remedy this epic previously recorded — resolves such a spec to `indeterminate` and leaves it
**permanently unemittable**, because nothing can ever stamp it back out. This plan makes an unreadable
claim section report `indeterminate` rather than zero, AND gives it a recovery path, AND adds a
population-derived detector so a third authoring form cannot reintroduce the blindness unseen.

## Deliverables

1. **The read side: an unreadable claim section resolves to `indeterminate`, never to zero claims.**
   `_parse_claims` currently returns `[]` on a missed section and on a section containing no top-level
   bullets, and those two outcomes are indistinguishable from a spec that genuinely carries no claims.
   Separate *"there are no claims"* from *"the claims could not be read"* and carry the distinction
   into `corpus verdicts` (a row with `verdict: indeterminate`, `admits: false`) and into
   `orchestrate.md`'s prep-ready test. ⛔ The section-present-but-unparsable case is the one that
   matters; a spec with no `## Claim Labels` section at all is a different state and must stay
   distinguishable from it.
   *Done when:* a spec whose claim section is a table reports `indeterminate` with `admits: false`
   rather than contributing zero rows; a spec with a genuinely empty claim section is distinguishable
   from it in the payload; and one named test pins all three states apart.

2. **The write side: a recovery path, so a spec CAN be stamped out of `indeterminate`.**
   ⛔ **This deliverable is what makes D1 safe to ship.** `corpus set-verdict` addresses claims by
   ordinal `--claim-index`, so on a zero-claim spec every index is out of range and no verdict can be
   written at all. Without a recovery path, D1 converts a silent vacuous pass into a permanent
   deadlock — a different defect, not the absence of one. Provide a path by which a spec whose claim
   section cannot be parsed can be brought back into the addressable state. ⛔ The recovery path must
   NOT be "normalize the corpus into bullets": that is a treadmill which makes the gate report green
   while staying blind to the next authoring shape, and `truthful-signals` has explicitly declined it
   on their own corpus for that reason. Whatever mechanism is chosen, the refusal must NAME the
   recovery path in its error payload — a fail-closed detector whose input no producer can repair is
   the deadlock this deliverable exists to prevent.
   *Done when:* a spec that reports `indeterminate` under D1 can be carried to a stamped, admitting
   state by a documented sequence that does not require re-authoring its claim prose; the
   `claim_index_out_of_range` refusal names that sequence; and a test walks the full
   unreadable → recovered → stamped → admits path end to end.

3. **A population-derived detector over the authoring forms, with both known-blind forms as fixtures.**
   The blindness was found twice by hand, on two different corpora, and neither time by a check. Add a
   detector that enumerates the spec corpus and reports every spec whose claim section is present but
   contributes zero parsed claims — publishing the population it scanned, never a bare count. ⛔ Per
   the epic's standing rule, a check that can return `0` from an empty population MUST publish the
   population size; copy the `test/_shared/_dispatch_roster.py` pattern. Carry **both** known-blind
   forms as fixtures — **table-form** and **prose-only** — plus a matched positive control (a
   bullet-form spec that parses non-zero), so the detector is seen to fail on real blind input rather
   than passing over an empty set.
   *Done when:* the detector reports the table-form and prose-only fixtures and stays silent on the
   bullet-form control; its output carries `specs_scanned` alongside every count; and removing the fix
   from D1 turns the detector red.

## Claim Labels

- OBSERVED: `_parse_claims` returns `[]` on a missed section — read at
  `marketplace/bundles/plan-marshall/skills/plan-orchestrator/scripts/orchestrator.py` §
  `_parse_claims` (`if start < 0: return []`, `:1233-1234`).
- OBSERVED: only a TOP-LEVEL `- ` bullet is counted as a claim, so a markdown table and a prose
  paragraph each contribute zero — read at the same file § `_parse_claims` (`if not indent:`, `:1244`).
- OBSERVED: the heading gate carries `re.IGNORECASE`, so heading CASE is no longer a cause — read at
  the same file `:394` (`CLAIM_LABELS_HEADING_RE`). ⭐ `EXPECTED_SURFACE_HEADING_RE` at `:395` carries
  the flag too: `#1338` applied it to BOTH headings in one hunk, correcting this epic's D13 entry,
  which quotes only the first line.
- OBSERVED: `corpus set-verdict` refuses `claim_index_out_of_range` carrying `claims_total`, so on a
  zero-claim spec every index is refused — read at the same file `:1743-1746`, and re-derived by a
  live non-writing probe against `PLAN-CIS-051` at HEAD `1169fb5bf` returning `claims_total: 0`.
- OBSERVED: `next`'s prep-ready test admits a candidate iff no row carries `admits: false`, so a
  zero-row spec passes vacuously — read at `plan-orchestrator/workflow/orchestrate.md` § Step 4.
- OBSERVED: seven of this epic's staged specs (`PLAN-CIS-049` … `PLAN-CIS-055`) parse to
  `claims_total: 0` against 154 tabulated claims — probed 7/7, population-derived, recorded at
  `epic.md` § D13.
- HYPOTHESIS: the PROSE-ONLY authoring form is present in THIS epic's corpus as well as in
  `truthful-signals`' — confirm/refute by running the D3 detector over
  `.plan/local/orchestrator/code-intelligence-substrate/plans/` (verify-at-outline). ⚠ Our seven
  known-blind specs are all table-form; prose-only is so far attested only on the sibling corpus.
- HYPOTHESIS: `truthful-signals` measured 19 of 124 heading-carrying specs at zero (13 table-form, 6
  prose-only) at `91bbe7470` — confirm/refute at that epic's own corpus via `corpus verdicts --slug
  truthful-signals` (verify-at-outline). ⚠ Their first-party figure, NOT re-derived here; it is a lead
  and no deliverable is scoped on its exact value.
- Verify-first clause: D2's recovery mechanism is deliberately NOT prescribed here. The consuming phase
  must settle, against `orchestrator.py`'s actual `corpus set-verdict` argument surface, which recovery
  shape is reachable without re-authoring claim prose, and re-scope if none is.

## Expected Surface

- OBSERVED: `marketplace/bundles/plan-marshall/skills/plan-orchestrator/scripts/orchestrator.py` —
  `_parse_claims` (`:1214`), `CLAIM_LABELS_HEADING_RE` (`:394`), the `claim_index_out_of_range`
  refusal (`:1743`), and the `claims_total` emission (`:1774`).
- OBSERVED: `marketplace/bundles/plan-marshall/skills/plan-orchestrator/SKILL.md` — the
  `corpus verdicts` / `corpus set-verdict` canonical-invocation blocks and their error tables.
- OBSERVED: `marketplace/bundles/plan-marshall/skills/plan-orchestrator/workflow/orchestrate.md` —
  Step 4's prep-ready admission test and its four governing rules.
- OBSERVED: `marketplace/bundles/plan-marshall/skills/persona-plan-orchestrator/standards/orchestration-model.md`
  — § Re-Grounding Verdict Field, the admission table (the `indeterminate` row gains the recovery
  path). ⛔ This document and `orchestrator.py` are the ONLY two sanctioned carriers of the field's
  five key tokens; do not create a third.
- OBSERVED: `test/plan-marshall/plan-orchestrator/test_orchestrator_corpus.py` — the existing
  `test_only_one_module_implements_the_verdict_grammar` enumeration, plus the new three-state and
  recovery-path tests.
- HYPOTHESIS: `test/_shared/_dispatch_roster.py` is the population-derived detector pattern D3 copies —
  confirm/refute by reading it (verify-at-outline).

## Dependencies and Sequencing

- Depends on: none. ⭐ This plan is a PREREQUISITE for meaningfully emitting `PLAN-CIS-049` through
  `PLAN-CIS-055` — seven of the eleven staged specs — because until it lands their prep-ready pass is
  vacuous and their re-grounding cannot be persisted.
- Overlaps with: none among the staged specs. `PLAN-CIS-052` declares
  `plan-orchestrator/scripts/_orchestrator_inbox.py` and `plan-orchestrator/standards/inbox-envelope.md`
  — the same skill directory but disjoint files; under `parallelization_scope = 1` this is a sequencing
  note only.
- Adjacent to: `PLAN-CIS-051` (detector and auditor integrity) stays untouched. D13 originally routed
  this work there; it was staged separately on 2026-08-25 by operator decision, because CIS-051 already
  carries 8 deliverables under a recorded scope-bloat rationale and its subject is `plan-retrospective`
  detectors and `audit.py`, not the orchestrator's verdict machinery. ⛔ Do not re-fold this into
  CIS-051.

## Hand-Off Command

```text
/plan-marshall task="implement .plan/local/orchestrator/code-intelligence-substrate/plans/PLAN-CIS-060-verdict-field-read-and-write-integrity.md"
```

## Write-Boundary

The plan implementing this spec touches only its own repository source and tests. It creates and edits
NO file under `.plan/local/orchestrator/` other than its own `inbox/{sender}-{seq}` message — the
orchestrator owns every other ledger write — and reports its outcome through its PR and its inbox
message. The inbox exception's qualifiers and the sole sanctioned write mechanism are stated in
`persona-plan-orchestrator/standards/orchestration-model.md` § Ledger Write-Boundary.
