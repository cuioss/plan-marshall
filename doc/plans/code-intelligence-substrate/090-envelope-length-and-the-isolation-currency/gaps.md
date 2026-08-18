# Gaps — 090-envelope-length-and-the-isolation-currency

D2 shipped and holds: `doc/concepts/token-management.adoc` § 6 now argues in billing-weight /
turns-resident currency, keeps its recommendation verbatim, and carries no surviving figure in prose or
in `context-isolation.svg`. What remains falls in three groups. Inside the shipped text, two defects:
one sentence narrates the document's own previous wording (a "Current state only" violation), and the
deleted figures were replaced by an unsourced comparative claim the run itself could not measure. On
the shipped diagram, the `ref-svg-diagrams` mandatory rasterise-and-read-back gate was neither
performed nor recorded, and the lane contract gives a lane run no pointer to that skill. And three of
five deliverables (D1, D3, D4) are still blocked on a corpus no cloud run can reach, with nothing
staged anywhere to pick them up — plus the section's duplicate `~10-15 K` figure the run itself
deferred.

## G1 — Delete the transitional parenthetical from § 6

- **Kind:** doc-defect
- **Severity:** medium
- **Topic:** documentation-surface
- **Where:** `doc/concepts/token-management.adoc:63` (§ 6 "Per-dispatch context isolation")
- **Evidence:** "(The older phrasing that a variant's context is "never additive" held only of the
  *orchestrator's* context, which does not accumulate the variants' histories; against the *bill* every
  dispatch's context is additive, and it is residency, not additivity, that makes isolation pay.)" This
  narrates what the document used to say. `marketplace/bundles/pm-documents/skills/ref-documentation/references/organization-standards.md:133-139`
  ("Current State Only" — "Remove transitional, status, or deprecation information"; "Eliminate
  'changed from X to Y' references") and `CLAUDE.md` § Documentation Standards ("No version history",
  "Current state only") both forbid it, and the standalone-plan-lane carve-out does not exempt
  documentation standards.
- **Why it matters:** a concept page that carries its own edit history teaches every later editor that
  corrections are appended rather than applied, and the sentence spends a reader's attention on a
  phrasing that no longer exists anywhere in the tree.
- **Action:** delete the parenthetical. The sentence before it already states the current position
  positively ("each dispatch's context is billed in full — it is *additive to the bill*, not free. What
  isolation changes is **residency**"), so nothing is lost. If the orchestrator/bill distinction is
  worth keeping, state it directly ("the orchestrator's context does not accumulate the variants'
  histories; the bill does"), without reference to an older phrasing.
- **Done when:** `grep -n "older phrasing\|never additive" doc/concepts/token-management.adoc` returns
  nothing, and § 6 still states both that the orchestrator's context does not grow and that the bill is
  additive.
- **Effort:** S
- **Risk if fixed:** none beyond prose; the correction's substance is already carried by the preceding
  sentences.

## G2 — Re-derive or remove the `~10-15 K tokens of variant context` figure § 6 deleted as unverifiable

- **Kind:** incomplete
- **Severity:** medium
- **Topic:** documentation-surface
- **Where:** `doc/concepts/token-management.adoc:75` (§ "Where Plan Marshall deliberately spends more",
  Q-Gate bullet)
- **Evidence:** "That is a measurable extra `execution-context-{level}` dispatch per phase, ~10-15 K
  tokens of variant context, plus per-finding triage tokens at the next phase entry." This is the same
  figure removed from § 6 by this run, for the stated reason that the population needed to re-derive it
  is unreachable. The run declared it as residue (`report-01.md:153-157`) and left it. Verified still
  present in the current tree.
- **Why it matters:** the document now deletes a figure as unverifiable in one section and asserts the
  identical figure as fact two sections later. A reader who trusts § "deliberately spends more" is
  reading exactly what § 6 decided could not be stood behind, and any future run quoting it inherits an
  undated, unsourced number.
- **Action:** either re-derive `~10-15 K` from a reachable instrumented population and state it with its
  population and sampling point per `manage-metrics/standards/data-format.md`, or delete the figure and
  keep the qualitative claim ("a measurable extra dispatch per phase, plus per-finding triage tokens").
- **Done when:** `grep -n "10-15 K" doc/concepts/token-management.adoc` returns either nothing, or a
  line that also names the population the figure was measured over.
- **Effort:** S (delete) / M (re-derive, requires a corpus-bearing run)
- **Risk if fixed:** deleting removes the only order-of-magnitude signal a reader has for the Q-Gate
  overspend; the surrounding prose must still convey that the cost is real and bounded.

## G3 — Re-derive or remove the `~5-10 dispatches` figure in the same section

- **Kind:** doc-defect
- **Severity:** low
- **Topic:** documentation-surface
- **Where:** `doc/concepts/token-management.adoc:76` (§ "Where Plan Marshall deliberately spends more",
  "Complex process for minimal changes" bullet)
- **Evidence:** "a one-line fix still passes through phase-1-init … phase-6-finalize — adding ~5-10
  dispatches the change itself doesn't need." An unsourced count in the same section as G2, surviving
  the same figure sweep.
- **Why it matters:** smaller than G2 (the number is roughly derivable from the six-phase pipeline), but
  a fix run touching this section should sweep it rather than leave one unsourced figure beside a
  corrected one.
- **Action:** derive the count from the phase pipeline and its handshakes and state it as derived, or
  drop the number and say "several dispatches the change itself doesn't need".
- **Done when:** the bullet either carries no bare `~5-10` or names how the count is derived.
- **Effort:** S
- **Risk if fixed:** none.

## G4 — Run the mandatory visual confirmation on `context-isolation.svg`

- **Kind:** omission
- **Severity:** medium
- **Topic:** documentation-surface
- **Where:** `doc/resources/diagrams/context-isolation.svg` (11 text nodes replaced by PR #1185);
  rule at `marketplace/bundles/pm-documents/skills/ref-svg-diagrams/SKILL.md:25`
- **Evidence:** the skill's rule reads "Every new or modified SVG MUST be rasterised against both the
  GitHub light (`#ffffff`) and dark (`#0d1117`) backgrounds … and **the rendered PNG MUST be read back
  by the author** … before the SVG is shown to the user or committed. Authoring an SVG and trusting
  that 'the markup looks right' is forbidden". `report-01.md:10-16` lists the skills loaded
  (`cloud-plan-lane`, `ref-code-quality`, `ref-asciidoc`) and explicitly justifies omitting
  `plugin-script-architecture`; `ref-svg-diagrams` is neither loaded nor mentioned, and no rasterisation
  is recorded anywhere in the report. The edit replaced short monospace labels with much longer prose
  inside fixed-width boxes — e.g. `~3 K` → "resident for the whole run" (25 chars) in a `width=160`
  box, and three `~10–15 K` → "few resident turns" in `width=120` boxes.
- **Why it matters:** this is the defect class the rule exists for. An analytic width check (done during
  audit: the new strings are no longer than pre-existing neighbours in the same boxes, so overflow is
  unlikely) is not the check the standard asks for, and no one has looked at the rendered result in
  either theme since the change landed.
- **Action:** load `pm-documents:ref-svg-diagrams`, rasterise the current SVG against `#ffffff` and
  `#0d1117` per the skill's Step 4 recipe, read both PNGs back, and fix any clipping, overlap or
  contrast regression found. Record the confirmation in the fixing run's report.
- **Done when:** a run report states that both rasterisations were read back, names the two background
  colours used, and either reports no defect or lists the corrections made.
- **Effort:** S
- **Risk if fixed:** re-layout to cure a clip could shift neighbouring labels; keep the change inside the
  affected box and re-rasterise after.

## G5 — Give the lane's conditional skill table an SVG-diagram row

- **Kind:** omission
- **Severity:** medium
- **Topic:** plan-lane-contract
- **Where:** `.claude/skills/cloud-plan-lane/SKILL.md:106-116` (Step 1, "Conditionally, by what the plan
  touches")
- **Evidence:** the table maps surfaces to skills — workflow docs, production code, Python code, Python
  tests, `SKILL.md`/bundle structure, `.adoc` documentation, security-relevant change — and has **no**
  row for an SVG diagram, even though `pm-documents:ref-svg-diagrams` exists and imposes a mandatory
  pre-commit gate (`SKILL.md:25`). This run edited an SVG, followed the table faithfully, and never saw
  the rule; G4 is the direct consequence.
- **Why it matters:** every future lane run that touches `doc/resources/diagrams/*.svg` will miss the
  same gate for the same reason. The contract is the only skill-selection surface a lane run has.
- **Action:** add a row `| SVG diagram (`doc/resources/diagrams/*.svg`) | `pm-documents:ref-svg-diagrams` |`
  to the conditional table, keeping the existing surface/skill format.
- **Done when:** `grep -n "ref-svg-diagrams" .claude/skills/cloud-plan-lane/SKILL.md` returns a row in
  the Step 1 conditional table.
- **Effort:** S
- **Risk if fixed:** a lane run editing an SVG now owes a rasterise step it previously skipped — that is
  the intent, but it makes diagram edits slightly more expensive and requires a rasteriser to be
  reachable in the runtime; the row should say what to do when none is (report the gap rather than skip
  silently).

## G6 — Stage D1, D3 and D4 for a run that can reach an instrumented population

- **Kind:** incomplete
- **Severity:** medium
- **Topic:** measurement/metrics
- **Where:** `doc/plans/code-intelligence-substrate/090-envelope-length-and-the-isolation-currency/plan.md:84-118`
  (D1, D3, D4); `doc/plans/code-intelligence-substrate/README.md` (no per-plan status)
- **Evidence:** three of five deliverables are recorded blocked (`report-01.md:36-39`) on a corpus that
  lives under the git-ignored `.plan/` tree, which no cloud clone has (`.gitignore:45`;
  `git ls-files .plan` → 13 tracked files, none of them a metrics record). Nothing anywhere picks the
  residue up: `grep -rln "090-envelope\|envelope-length" doc/` returns only this plan's own two files,
  and no sibling plan in `doc/plans/**` references its blocked deliverables. The blocker is structural,
  not incidental — re-running this plan in the same lane produces the same three blocks.
- **Why it matters:** the epic's stated theme is the measurement substrate behind token reduction, and
  its only plan that owns the `turns_resident` factor has published nothing. The blocked work also gates
  a real lever (D4's envelope split) that no other plan targets, per `plan.md:177-180`.
- **Action:** stage a successor plan in the epic that (a) states in its own preamble that it must be
  executed on a machine holding the archived `.plan/` metrics rather than in a cloud clone, (b) carries
  D1/D3/D4 forward verbatim with their ⛔ guards, and (c) derives read-only from the emitter the sibling
  plan landed (`manage-metrics/scripts/manage-metrics.py:1539`,
  `manage-metrics/standards/data-format.md:237-244`) instead of adding a second writer. Record in the
  epic `README.md` that plan 090 shipped D2 only.
- **Done when:** a successor plan file exists under `doc/plans/code-intelligence-substrate/` naming D1,
  D3 and D4 and its corpus precondition, and it is referenced from the epic README.
- **Effort:** M
- **Risk if fixed:** a locally-executed plan does not get the lane's PR/verification cycle in the same
  form; the successor must say which contract governs it.

## G7 — Record the two plan-mandated checks the report leaves unstated (§ 4 figures, emission coordination)

- **Kind:** report-defect
- **Severity:** low
- **Topic:** documentation-surface
- **Where:** `report-01.md:41-59` (D2 detail) against `plan.md:141` and `plan.md:181-183`
- **Evidence:** the plan's Expected surface names "`doc/concepts/token-management.adoc` § 6 (and § 4's
  figures) — D2"; the report never mentions § 4. The plan's Notes require coordinating with the WS-04
  emission plan ("If it has not, derive read-only and **do not add a writer**"); the report never
  mentions it. Both were in fact satisfied — § 4 ("Skill-driven guidance — no tool exploration") carried
  no numeric figure before the change (verified against `6f1cb7b^`) or after, and no bundle file was
  touched, while the emitter had already landed in PR #1154 — but the report gives a reader no way to
  distinguish "checked, nothing to do" from "overlooked". The plan's `§ 4` pointer is itself ambiguous:
  under the document's top-level heading numbering, the figures actually needing attention sit in
  "Where Plan Marshall deliberately spends more" (G2, G3).
- **Why it matters:** a later run reading this report cannot tell which parts of the surface were swept,
  so it will re-do the sweep or, worse, assume it was done.
- **Action:** append two lines to the report's D2 detail: that § 4 carries no numeric figure (so nothing
  was owed there, and the figures the plan meant are those in "Where Plan Marshall deliberately spends
  more", tracked as residue), and that the two-factor emission had already landed in `manage-metrics`
  so no second writer was added.
- **Done when:** `report-01.md` names § 4 and the emission-coordination check, each with its outcome.
- **Effort:** S
- **Risk if fixed:** none — it is an append to a historical record; keep the existing text intact.

## G8 — Source or soften § 6's "bounded and small" cost comparison

- **Kind:** doc-defect
- **Severity:** medium
- **Topic:** documentation-surface
- **Where:** `doc/concepts/token-management.adoc:63`
- **Evidence:** "Isolation is the biggest lever because it caps that residency — and its own cost,
  re-creating each envelope's starting context, is bounded and small against the run-length read cost it
  removes." This is a quantitative comparison stated without a source, shipped by the same commit that
  deleted four figures on the ground that the population needed to re-derive them was unreachable
  (`report-01.md:56-59`). The plan itself labels the underlying arithmetic a LEAD requiring re-derivation
  at the moment of the claim (`plan.md:160`) and records D1 as blocked, so nothing measured backs it.
- **Why it matters:** it is the load-bearing justification for the document's largest architectural
  claim. If envelope re-creation is *not* small against the read cost it removes — the exact failure mode
  the plan flags as real (`plan.md:158`: a split whose second half must re-read the first half's context
  "costs more") — then the sentence misdirects every reader who acts on it, and it is written in a
  register that invites exactly that action.
- **Action:** either attach evidence (re-derive the comparison against a reachable population and state
  it with that population), or restate it as a condition rather than a fact — e.g. "isolation pays
  whenever re-creating an envelope's starting context costs less than the residency it removes, which is
  the property a split must be checked against before it is made". The second form is shippable today
  and preserves the recommendation.
- **Done when:** the sentence either names the population its comparison was measured over, or is phrased
  as the condition a split must satisfy rather than as an established magnitude.
- **Effort:** S
- **Risk if fixed:** phrasing it as a condition slightly weakens the rhetorical force of § 6; the
  recommendation ("the biggest single token-management lever") must remain unqualified, per the plan's
  ⛔ on weakening the isolation claim.

## G9 — Connect § 6's cost model to the mechanism and the fields that measure it

- **Kind:** doc-defect
- **Severity:** low
- **Topic:** documentation-surface
- **Where:** `doc/concepts/token-management.adoc:51-57`
- **Evidence:** § 6 states `cost(byte) = creation_multiplier + read_multiplier × turns_remaining` and
  "billed once at a creation multiplier and again, at a smaller read multiplier, on every subsequent
  turn it stays resident" without naming prompt caching — the mechanism that makes the read multiplier
  smaller than the creation one — and without pointing at the fields that measure both factors, which a
  sibling plan landed: `cache_creation_input_tokens` / `cache_read_input_tokens` and the persisted
  `cache_read_per_tool_use` (`marketplace/bundles/plan-marshall/skills/manage-metrics/standards/data-format.md:49,146,237-244`;
  written at `manage-metrics/scripts/manage-metrics.py:1539`). The page's Related list links
  `manage-metrics/SKILL.md` generically (`:91`) but not the decomposition.
- **Why it matters:** the whole point of the D2 correction is that the argument is now in the currency
  that is actually measured — but a reader is given no route from the claim to the measurement, so the
  model reads as an assertion rather than as something the system reports on itself.
- **Action:** add one sentence to § 6 naming prompt caching as the mechanism behind the two multipliers,
  and cross-referencing the read-cost decomposition in `manage-metrics/standards/data-format.md`
  (`cache_read ≈ cache_read_per_tool_use × tool_uses`).
- **Done when:** § 6 links to the read-cost decomposition and names the caching mechanism, and the
  identity it cites matches `data-format.md:237`.
- **Effort:** S
- **Risk if fixed:** couples a concept page to a field name that could be renamed; the cross-reference
  should point at the standards section, not restate the formula's field names in prose more than once.
