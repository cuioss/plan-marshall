# PLAN-TRUTH-134: The scope extractor invents paths and drops bullets, and reports success

epic: truthful-signals
workstream: WS-01

> Staged plan spec — one shippable unit of work, ready for `/plan-marshall` hand-off.
> Staged 2026-09-04 from inbox drain message `documented-invocations-cannot-succeed-as-written-009.md`,
> a first-party observation from PLAN-TRUTH-101's own run (PR #1386).

## Objective

**`_plan_parsing._extract_scope_field`'s bullet regex carries no start-of-line anchor.** When a bullet
fails to match at its own start, the scan finds an **interior hyphen** instead and harvests the
fragment after it as if it were a path. The verb reports `status: success` throughout.

⛔ **Both failure directions fired in one plan, and the first is the worse one:** the extractor
**invented 4 paths** and **silently dropped 3 of 4 bullets** from a single survey block.

Q-Gate finding `eb52b1` (3-outline). Step 7 `sync-affected-files` parsed 39 bullets across 8 headings
in 4 deliverables and admitted **4 non-path strings into the plan's persisted footprint**:

- `affected_files` — the **MUTATION** set — gained `none - this deliverable is read-only by
  construction` and `site pin sweep names` (mangled from *"…plus any test the per-site pin sweep
  names"*).
- `read_intent_files` gained `every path returned by the prescription-derivation query named in Change
  per file below` and `site remedy is resolved)` (mangled from *"pyproject.toml (read - the alias table
  from which the per-site remedy is resolved)"*).

⭐⭐ **The first entry is the sharpest statement of the defect available: deliverable 1 declared it
mutates NOTHING, and its own no-mutation prose contributed a phantom entry to the MUTATION set. The
declaration of no-mutation became a mutation.**

And in the same pass, deliverable 3's `Files to survey:` block **lost three of its four bullets
entirely** — `.claude/skills/finalize-step-deploy-target/SKILL.md`, `pyproject.toml`, `test/**` were
not extracted at all — so the survey declaration was **simultaneously corrupt and incomplete**.

⛔⛔ **This is residue, not a closed item.** The finding was resolved by editing **that plan's outline
prose** so the regex could not mis-parse it, plus a `set-list` repair of the two footprint keys. The
root cause was diagnosed precisely in the resolution text — *"the bullet regex in
`_extract_scope_field` has no start-of-line anchor"* — **and then not fixed.** The parser is unchanged,
so **every future plan whose scope block contains a hyphenated word inside a bullet is exposed**:
`per-site`, `read-only`, `write-new`, `test-jar`, `merge-queue` — ordinary vocabulary in this corpus.

⭐ **The blast radius is the disjointness gate.** A phantom entry in `affected_files` is a path the
gate will serialize siblings behind; a dropped bullet is a path the gate cannot see at all. Both
directions of `PLAN-TRUTH-113`'s residual-error table, manufactured by a regex.

## Deliverables

1. **D0 — GATE: derive the exposed population.** Sweep the corpus of plan outlines (live and archived)
   for scope bullets containing an interior hyphen, and report how many plans' persisted footprints
   currently carry a phantom or are missing a bullet. ⛔ **Publish the swept population and its size.**
   One plan is the instance that was noticed; it is not the population, and this epic's rule forbids
   publishing it as one.
2. **D1 — anchor the bullet pattern to start-of-line** (after leading indent), so a bullet that does
   not match at its own start is **reported as unparsed** rather than re-scanned from an interior
   hyphen.
3. **D2 — publish `bullets_parsed` against `bullets_seen`, and FAIL the phase when they disagree.**
   ⭐ **The count is already computed** — it moved 39 → 38 during the repair — **it is simply not gated
   on.** This is the cheapest half of the fix and it closes the silent-drop direction even if D1 lands
   narrowly.
4. **D3 — matched controls, both directions.** A bullet carrying a hyphenated word must extract its
   real path unchanged; a malformed bullet must be reported as unparsed and must NOT contribute a
   fragment. ⛔ **The negative control is load-bearing**: an anchor that rejects legitimate indented or
   nested bullets would silently shrink every footprint in the corpus, which is the worse failure.

## Claim Labels

- OBSERVED: the four invented strings and their source prose, quoted from Q-Gate finding `eb52b1`.
  - verdict: unverifiable | checked_at: 66320e70d | by: truthful-signals/cleanup | rescoped: n/a | evidence: Q-Gate finding eb52b1 and its plan directory no longer exist under .plan/local/plans
- OBSERVED: deliverable 3's survey block lost three of four bullets, named individually.
  - verdict: unverifiable | checked_at: 66320e70d | by: truthful-signals/cleanup | rescoped: n/a | evidence: Same removed plan directory; not reproducible at HEAD
- OBSERVED: `bullets_parsed` moved 39 → 38 during the repair — the count exists and is ungated.
  - verdict: corroborated | checked_at: 66320e70d | by: truthful-signals/cleanup | rescoped: n/a | evidence: bullets_parsed is computed in _plan_parsing.py but no bullets_seen counterpart or gating check exists anywhere in source
- OBSERVED: the finding was resolved by editing the OUTLINE PROSE, not the parser; the parser is unchanged at HEAD.
  - verdict: corroborated | checked_at: 66320e70d | by: truthful-signals/cleanup | rescoped: n/a | evidence: _extract_scope_field regex at _plan_parsing.py is unchanged and still lacks a start-of-line anchor
- HYPOTHESIS: the regex has no start-of-line anchor. ⛔ Quoted from the resolution text, **not read at source by this orchestrator**. Confirm/refute at `manage-solution-outline/scripts/_plan_parsing.py` § `_extract_scope_field` (verify-at-outline).
  - verdict: corroborated | checked_at: 66320e70d | by: truthful-signals/cleanup | rescoped: n/a | evidence: _plan_parsing.py file_pattern regex has no caret anchor before the bullet hyphen, confirmed by direct read at HEAD
- HYPOTHESIS: other plans' persisted footprints already carry phantoms. ⛔ NOT checked; D0 settles it (verify-at-outline).
  - verdict: unverifiable | checked_at: 66320e70d | by: truthful-signals/cleanup | rescoped: n/a | evidence: A corpus-wide sweep for other plans phantom footprints (D0) was not independently performed

## Expected Surface

- HYPOTHESIS: `marketplace/bundles/plan-marshall/skills/manage-solution-outline/scripts/_plan_parsing.py` — `_extract_scope_field` (D1, D2) (verify-at-outline)
- HYPOTHESIS: `marketplace/bundles/plan-marshall/skills/manage-solution-outline/SKILL.md` — the `sync-affected-files` payload contract (D2) (verify-at-outline)
- HYPOTHESIS: `test/plan-marshall/manage-solution-outline/` — the D3 controls (verify-at-outline)

## Dependencies and Sequencing

- Depends on: none.
- ⚠ **Overlaps `PLAN-TRUTH-125`** on `manage-solution-outline/scripts/_plan_parsing.py`. **SERIALIZE** — `-125` is the multi-implementation format plan and touches the same module.
- Adjacent to: `PLAN-TRUTH-113` (shipped) — the disjointness gate's declared-surface reader. This spec is the **writer** side of the same surface: `-113` fixed how the surface is READ, this fixes how it is WRITTEN.
- Adjacent to: `PLAN-TRUTH-136` — `affected_files` under-recording from a different cause (loop-back work). ⛔ **Different causes, same key**; keep separate and cross-reference in the shipped docs.

## Hand-Off Command

```text
/plan-marshall task="implement .plan/local/orchestrator/truthful-signals/plans/PLAN-TRUTH-134-the-scope-extractor-invents-paths-and-drops-bullets-and-reports-success.md"
```

## Write-Boundary

The plan implementing this spec touches only its own repository source and tests. It creates and edits
NO file under `.plan/local/orchestrator/` other than its own `inbox/{sender}-{seq}` message — the
orchestrator owns every other ledger write — and reports its outcome through its PR and its inbox
message. The inbox exception's qualifiers and the sole sanctioned write mechanism are stated in
`persona-plan-orchestrator/standards/orchestration-model.md` § Ledger Write-Boundary.

## ⭐ FOLDED 2026-09-04 (b) — cui-http consolidation

**Source for every item below:** `inbox/findings-from-cui-http.md`, a consolidation relayed from the **cui-http** repository aggregating **52 lesson records** from the `quality-report-remediation` epic (19 plans, PRs #153–#186). ⛔ **The source records were REMOVED after it was written — that document is their sole surviving record.** ⛔ Nothing in it was corroborable against cui-http from this checkout; the plan-marshall surfaces it names are local and are where the value is. ⚠ Its header says *"8 themes / 27 findings"* and it enumerates **45** — **do not quote its internal counts.**

- **§3.6 — a deliverable's `Affected files:` must be a SUPERSET of its own prose.** A deliverable carries **two** descriptions of its blast radius: the structured `Affected files:` list (**machine-read** — it feeds skill resolution, lesson consult, task scoping, the verification sweep) and the free-prose change instructions (**what the implementer actually follows**). ⛔ **When the prose names a file the list omits, every machine consumer UNDER-SCOPES while the implementer OVER-EDITS.**

  ⭐⭐ **This is this spec's defect approached from the authoring side rather than the parser side, and it supplies a cheap mechanical closure check the parser fix should carry:** *"extract every path/file/type named in the prose, resolve each, assert each appears in the list."* ⭐ **And the asymmetry argument is worth keeping verbatim:** *"the asymmetry only causes harm in ONE direction, so it is worth checking even when the list looks plausible."*

  ⇒ **D2's `bullets_parsed` vs `bullets_seen` gate closes the parser half; this closes the authoring half**, and together they are the two ways a declared surface diverges from the real one at outline time.

- **§7.4 — the read-only-fact-source convention is unstated, so every deliverable relitigates it.** ⛔⛔ **HALF OF ONE PLAN'S Q-GATE VOLUME WAS ONE UNSTATED CONVENTION**, raised once per deliverable and triaged individually **four times**.

  ⭐ **The tension is REAL, which is why it kept being raised**: a documentation deliverable verified against `.java` sources must either declare them as `(read)` affected files — **flipping the deliverable out of `documentation_only` and pulling an unwarranted `module_testing` profile behind a docs-only change** — or omit them, **losing the `files_exist` guarantee.** ⇒ *"The plan resolved it correctly four times. The judgement belongs in a STANDARD, not in four accepted findings."*

  **The document's own resolution**: codify the convention once — **fact sources are not declared as affected files; in exchange each such deliverable's verification step must assert its fact sources BY NAME at execute time** — then either teach the validator the exemption or carry the rationale in the outline template.

## ⛔⛔ FOLDED 2026-09-06 — `review-apparatus-033` drain (1 item). AND ITS BLAST RADIUS REACHES THE DISJOINTNESS GATE.

### Item 8 (`-011`) — prose under `Files to survey:` parses into path fragments and is PERSISTED as read intent

⭐⭐ **This is this spec's exact subject with a second, independent instance**: the extractor invents
paths that no author wrote. This spec's corroborated claims already establish the mechanism —
`_plan_parsing.py`'s `_extract_scope_field` regex has **no start-of-line anchor** (claims 3 and 4), and
`bullets_parsed` is computed with **no `bullets_seen` counterpart and no gating check** (claim 2). ⇒
**Prose beneath a scope heading is exactly what an unanchored pattern will harvest.**

⛔⛔ **THE SENDER FLAGGED A CONSEQUENCE OUTSIDE ITS OWN COMPONENT AND WAS RIGHT TO — IT REACHES OUR
GATE.** The persisted read intent feeds the **declared footprint**, and the declared footprint is what
`corpus cross-check`'s disjointness matcher reads. ⇒ **Invented path fragments are a route by which a
plan's declared surface acquires entries nobody wrote**, and the gate then serialises siblings behind
paths that do not exist.

⭐⭐ **That pairs with this epic's OPPOSITE live defect** — our own in-flight plans declaring
`affected_files: 0` at `4-plan`. **One route adds phantom paths, the other writes none at all, and both
end at the same gate.** ⛔ **D0 must state which direction it is fixing**; a fix for invention does not
touch absence, and a reader who conflates them will read one as covering both.

---

## Superseded By

⛔ **This spec is SUPERSEDED by `PLAN-TRUTH-151-early-phase-gates-the-outline-parser-and-the-plan-tier-claim-write-back.md` (PLAN-TRUTH-151)**, recorded 2026-09-12 under the operator directive to group plans by shared target at a ceiling of 12 deliverables. It is retained in full as the audit record of why it was retired and as the authority its successor's `## Claim Labels` section POINTS at — the successor deliberately does not restate these claims, so **this document is where they are re-derived from**. Do not implement from this spec; implement from its successor.
