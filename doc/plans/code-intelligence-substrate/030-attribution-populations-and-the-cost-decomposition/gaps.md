# Gaps — 030-attribution-populations-and-the-cost-decomposition

All four deliverables landed and are covered by non-vacuous tests, so nothing here is a re-do of the
plan's core work. What remains splits three ways. **First**, D2 documented the attribution limitation
at the *consumer* contract (`manage-metrics/standards/data-format.md`) but left the *producer's* two
contract surfaces — `platform-runtime/standards/contract.md` and the `runtime_base.py` docstring that
`manage-metrics.py:3391` names as SOURCE OF TRUTH — still asserting the un-subtracted model, so two
documents now describe one producer differently and the wrong one is the authoritative one (G1, G2).
**Second**, a later plan (#1260) added a second `cache_read_per_tool_use` over a different population
in `plan-retrospective`, which is the second emitter this plan's D3 explicitly forbade (G3).
**Third**, the published read-cost decomposition names itself inconsistently (`resident_context_per_call`
is not a field — G4, G5), asserts a per-call meaning its own population disclosure denies (G6), is
structurally absent for exactly the inline phases where that meaning would be honest (G7), and carries
one weak test guard plus one untested branch (G8, G9).

---

## G1 — Correct the cache-read attribution description in the platform-runtime contract

- **Kind:** doc-defect
- **Severity:** medium
- **Topic:** documentation-surface
- **Where:** `marketplace/bundles/plan-marshall/skills/platform-runtime/standards/contract.md:967`
  (§ "Cache-read attribution — turn-weighted residency")
- **Evidence:** the contract states "*each bucket's weight is its payload bytes multiplied by the
  number of the phase's billed turns those bytes remained in context, and the phase's recorded
  `cache_read` is divided in proportion to those weights*". The implementation divides only
  `attributable = max(0, cache_read_total - max(0, subagent_cache_read))`
  (`marketplace/bundles/plan-marshall/skills/platform-runtime/scripts/claude_runtime.py:1927`), not
  the recorded `cache_read`. The subagent-folded share never enters the split and reaches the
  residual through the remainder at `:1933`. `manage-metrics/standards/data-format.md:192` states the
  correct model ("*Payloads folded in from subagent transcripts … carry no residency weight of their
  own, so their share is disclosed in the residual*"), so the two documents disagree. Line 969's
  reconciliation paragraph names only the `total_weight == 0` case, not the subtraction.
- **Why it matters:** this is the producer's own emission contract and the surface a target
  implementer reads to build a conforming runtime. A reader who implements from it would divide the
  full recorded `cache_read` and produce named shares that spread subagent spend over buckets it was
  never observed to occupy — the exact mislabel the residual exists to prevent. It also means D2's
  *Done when* ("the limitation is documented at the emission contract") is met only at the consumer
  contract, leaving the authoritative surface carrying the claim D2 was written to qualify.
- **Action:** extend § "Cache-read attribution" to state that only the parent-observed portion is
  split — subagent-folded `cache_read` is subtracted before the division and disclosed in the
  residual — and that a window with no observed residency weight leaves the whole figure in the
  residual. Name `_attribute_cache_read` and `_fold_turn_residency`, matching
  `data-format.md:209-213`.
- **Done when:** `contract.md` § Cache-read attribution names the subtraction and the zero-weight
  branch, and a reader can no longer derive "the recorded `cache_read` is divided in proportion to
  those weights" from it. A structural-equality or drift test is not required, but the two contract
  texts must not contradict each other.
- **Effort:** S
- **Risk if fixed:** none to behaviour — documentation only. A contract-text test could exist that
  pins the current wording; check `test/plan-marshall/platform-runtime/` before editing.

---

## G2 — Correct the same description in the `runtime_base.py` contract docstring

- **Kind:** doc-defect
- **Severity:** medium
- **Topic:** documentation-surface
- **Where:** `marketplace/bundles/plan-marshall/skills/platform-runtime/scripts/runtime_base.py:733`
  (inside `Runtime.metrics_normalized_tokens.__doc__`, block 726-737)
- **Evidence:** "*each bucket's weight is its payload bytes multiplied by the number of the phase's
  turns those bytes remained in context, and the recorded `cache_read` is divided in proportion to
  those weights. Weight that cannot be tied to an observed payload … is NOT redistributed*". Same
  omission as G1. This docstring is separately load-bearing:
  `marketplace/bundles/plan-marshall/skills/manage-metrics/scripts/manage-metrics.py:3391-3393`
  declares "*SOURCE OF TRUTH is the platform-runtime contract — `Runtime.metrics_normalized_
  tokens.__doc__`'s per-phase bucket declaration*".
- **Why it matters:** a separate instance in a separate file, and the one the code itself points at.
  Fixing `contract.md` alone would leave the declared source of truth wrong, which is strictly worse
  than having them both wrong in the same way.
- **Action:** add the subtraction clause to the docstring paragraph at 726-737, phrased consistently
  with G1's fix and with `data-format.md:209-213`.
- **Done when:** `Runtime.metrics_normalized_tokens.__doc__` states that only the parent-observed
  portion is split and that subagent-folded `cache_read` reaches the residual by remainder.
- **Effort:** S
- **Risk if fixed:** none to behaviour. Confirm no docstring-mirroring test pins the current text.

---

## G3 — Resolve the two different quantities both named `cache_read_per_tool_use`

- **Kind:** bug
- **Severity:** medium
- **Topic:** measurement/metrics
- **Where:** `marketplace/bundles/plan-marshall/skills/plan-retrospective/scripts/analyze-logs.py:662`
  (in `context_position_cost`, emitted under `by_phase[*].cache_read_per_tool_use`) versus
  `marketplace/bundles/plan-marshall/skills/manage-metrics/scripts/manage-metrics.py:1539`
  (the `metrics.toon` phase-row field). Documented separately and without cross-reference at
  `plan-retrospective/references/log-analysis.md:85-89` and
  `manage-metrics/standards/data-format.md:146`.
- **Evidence:** two published figures share one name and are not the same number.
  `manage-metrics` writes `round(cache_read_input_tokens / tool_uses)` — an **int**, phase-level,
  numerator `main-context-window` (parent turns + attributed subagent transcripts), denominator
  `dispatched-subagent`. `analyze-logs` computes
  `round(cache_read_sum / tool_use_sum, 3)` — a **float**, summed over the phase's **per-dispatch**
  `metrics-dispatch-boundaries-{phase}.toon` rows, i.e. the `per-dispatch` population. Neither
  document mentions the other. This plan's D3 carried the constraint "⛔ **One writer, and it is this
  plan.** A sibling WS-06 plan carries the same anomaly from the consuming side — it must not add a
  second emitter." Timeline confirmed:
  `git show 18ddd54:…/analyze-logs.py | grep -c cache_read_per_tool_use` → `0`, and
  `git log -S cache_read_per_tool_use -- …/analyze-logs.py` → introduced by `89edc99` (#1260), i.e.
  **after** this plan landed.
- **Why it matters:** a consumer or auditor holding a figure named `cache_read_per_tool_use` cannot
  tell which population it measures, which is the exact defect class this plan exists to remove —
  reproduced on the field this plan published. The two can diverge materially: the boundary ledger is
  a declared subset of the dispatched population (`data-format.md` § "The declared dispatch-boundary
  population"), so the retrospective figure is computed over strictly fewer dispatches.
- **Action:** rename one of the two so the name states its population — e.g. the retrospective's to
  `dispatch_boundary_cache_read_per_tool_use` (matching the `dispatch_boundary_*` prefix already used
  for that population in `manage-metrics`) — and add a cross-reference in both
  `log-analysis.md` and `data-format.md` § Read-Cost Decomposition naming the other figure and
  stating they are not comparable. Update `analyze-logs.py`'s key, its docstring at `:586-594`, the
  reference doc at `log-analysis.md:85-89`, and the tests at
  `test/plan-marshall/plan-retrospective/test_analyze_logs.py:2223-2394`.
- **Done when:** `grep -rn "cache_read_per_tool_use" marketplace/` returns occurrences from exactly
  one of the two producers, and each of the two documents names the other figure and says they are
  not additively comparable.
- **Effort:** M
- **Risk if fixed:** the retrospective key is consumed by report-rendering and by
  `.claude/skills/audit-archived-plan-retrospectives` checks that read log-analysis output; a rename
  must sweep every reader or a check will silently read an absent key. Grep for the key across
  `marketplace/`, `.claude/` and `test/` before renaming.

---

## G4 — Stop naming the render's factor `resident_context_per_call`, which is not a field

- **Kind:** doc-defect
- **Severity:** low
- **Topic:** measurement/metrics
- **Where:** `marketplace/bundles/plan-marshall/skills/manage-metrics/scripts/manage-metrics.py:2315`
  (the `Read-cost decomposition` render bullet)
- **Evidence:** the bullet renders
  `… × turns ({turns:,}). resident_context_per_call is a derived-cost ratio (main-context-window
  cache_read ÷ dispatched-subagent tool_uses …)`. `resident_context_per_call` is a snake_case
  identifier that exists on no record:
  `grep -rn "resident_context_per_call" --include=*.py --include=*.md .` outside `doc/plans/` returns
  exactly two hits, both prose, and no assignment or key anywhere. The persisted field is
  `cache_read_per_tool_use` (`manage-metrics.py:1539`).
- **Why it matters:** `metrics.md` is a human-facing artifact whose whole purpose after this plan is
  that a figure names itself. A reader who sees an identifier-shaped name in the bullet and greps
  `metrics.toon` for it finds nothing, and cannot connect the rendered ratio to the field that
  carries it.
- **Action:** replace `resident_context_per_call` in the bullet text with the real field name
  `cache_read_per_tool_use`, keeping the human phrase "resident context per tool-use" for the value
  label.
- **Done when:** the rendered `Read-cost decomposition` bullet contains no identifier that is not a
  key on the phase row; the assertion at
  `test/plan-marshall/manage-metrics/test_manage_metrics.py:2244-2249` is updated accordingly.
- **Effort:** S
- **Risk if fixed:** the render-assertion test at `test_manage_metrics.py:2223` pins bullet substrings
  and must be updated in the same change.

---

## G5 — Stop naming the same phantom field in the lattice entry

- **Kind:** doc-defect
- **Severity:** low
- **Topic:** documentation-surface
- **Where:** `marketplace/bundles/plan-marshall/skills/manage-metrics/standards/data-format.md:49`
  (Direction 1 lattice row for `cache_read_per_tool_use`, "Rendered as" column)
- **Evidence:** the row says the bullet "*states the identity `cache_read ≈ resident_context_per_call
  × turns`*", while the same document's § Read-Cost Decomposition code block at `:237` states the
  identity correctly as `cache_read_input_tokens ≈ cache_read_per_tool_use × tool_uses`. One document
  states the same identity under two different names for the same factor.
- **Why it matters:** the lattice is the document a consumer reads to learn what a field measures. A
  lattice row that names a non-existent field for the figure the row is about undermines the exact
  guarantee the lattice makes ("*every field below names the population it measures*",
  `data-format.md:17`).
- **Action:** rewrite the "Rendered as" cell of the `cache_read_per_tool_use` row to use the real
  field names, matching the code block at `:237`.
- **Done when:** `grep -n "resident_context_per_call" marketplace/bundles/plan-marshall/skills/manage-metrics/standards/data-format.md`
  returns nothing.
- **Effort:** S
- **Risk if fixed:** none.

---

## G6 — Stop labelling the ratio "resident context per tool-use" while disclosing that it is not

- **Kind:** doc-defect
- **Severity:** medium
- **Topic:** measurement/metrics
- **Where:** `marketplace/bundles/plan-marshall/skills/manage-metrics/scripts/manage-metrics.py:2313-2318`
  (the value label inside the `Read-cost decomposition` bullet)
- **Evidence:** one bullet asserts and denies the same reading. It prints
  `resident context per tool-use ({int(resident):,})` — a per-call cost claim — and then says
  `main-context-window cache_read ÷ dispatched-subagent tool_uses — the two populations differ`. The
  numerator sums `message.usage.cache_read_input_tokens` over the parent transcript **and** every
  attributed subagent transcript (`claude_runtime.py:2270-2282`, `:2305`); the denominator counts
  dispatched-subagent tool uses only (`data-format.md:40`). The quotient is therefore not the average
  resident context of any single population's calls. The run's own pre-PR verification agent raised
  this (report `Findings` #2) and accepted it as designed because the plan's D3 named the formula
  literally.
- **Why it matters:** the label is what a reader carries away; the disclosure is a clause they may
  not read. This plan exists because a figure that reads as one thing while being another is the
  project's signature defect — and here the value label is the reading and the caveat is the
  correction, which is the wrong way round.
- **Action:** rename the value label in the bullet to something that does not assert a per-call
  meaning — e.g. `read-cost factor (cache_read ÷ tool_uses)` — and keep the population-span clause.
  Apply the same wording to `data-format.md:241` and `:49`, which both call it "the resident-context
  factor".
- **Done when:** no rendered or documented label for `cache_read_per_tool_use` asserts "resident
  context per call/tool-use" as a measured quantity; every surface names it as a cross-population
  cost factor.
- **Effort:** S
- **Risk if fixed:** `test_manage_metrics.py:2245` asserts the literal string
  `'resident context per tool-use (10,000)'` and must change with it. Coordinate with G4 — same
  bullet, same test.

---

## G7 — State that the read-cost decomposition is structurally absent for inline-only phases

- **Kind:** incomplete
- **Severity:** low
- **Topic:** measurement/metrics
- **Where:** `marketplace/bundles/plan-marshall/skills/manage-metrics/standards/data-format.md:241`
  (§ Read-Cost Decomposition), with the mechanism at
  `marketplace/bundles/plan-marshall/skills/manage-metrics/scripts/manage-metrics.py:1534-1541`
- **Evidence:** the contract states the mechanical condition — "*present only when both operands are
  present and `tool_uses > 0`*" — and stops there. `tool_uses` is the dispatched-subagent count
  (`data-format.md:40`), so a phase that dispatched nothing (`total_tokens_population: inline`,
  `manage-metrics.py:396-400`) carries `tool_uses` at 0 or absent, the persist guard at `:1534` never
  fires, and neither the field nor the render bullet ever appears for it. The decomposition is
  therefore systematically unavailable on precisely the phases whose `cache_read` is purely
  main-context.
- **Why it matters:** this plan's Problem section names "*verified on one phase, generalised to six*"
  as the archetype it is closing. A cost decomposition that is silently absent for a whole class of
  phases — with only a mechanical guard condition stated, not its population consequence — repeats it
  one level down. A consumer comparing phases sees the bullet on some and not others and cannot tell
  whether the phase was cheap or unmeasurable.
- **Action:** add a sentence to § Read-Cost Decomposition naming the consequence: an inline-only phase
  has no dispatched `tool_uses`, so the decomposition is not published for it, and its absence is
  "not derivable here", never "zero read cost". Cross-reference § Inline Main-Context Attribution.
- **Done when:** § Read-Cost Decomposition states which phase class never carries the factor and why,
  and a test asserts the factor is absent on a row carrying `total_tokens_population: inline` with
  non-zero `cache_read_input_tokens`.
- **Effort:** S
- **Risk if fixed:** none to behaviour if scoped to documentation plus one assertion. Actually
  *publishing* a figure for inline phases would need a main-context call count that no per-phase field
  carries today — do not attempt that under this gap.

---

## G8 — Strengthen the "no bare unattributed" render guard so a duplicate label cannot pass

- **Kind:** test-gap
- **Severity:** low
- **Topic:** tests
- **Where:** `test/plan-marshall/manage-metrics/test_manage_metrics.py:2156-2160` (the trailing loop
  in `test_render_names_quantity_and_denominator_for_each_residual`)
- **Evidence:** the loop asserts only `' of ' in line` for every rendered bullet containing
  `nattributed`. Mutation-proved insufficient: rewriting
  `_UNATTRIBUTED_RENDER['cache_read_unattributed']` to
  `('Unattributed', 'exploration_result_bytes', …)` — both residuals under an identical bare label
  over an identical denominator, i.e. D1's exact prohibited state — leaves this loop **passing**; only
  the exact-string assertions above it failed. The loop's stated purpose is to catch the general case,
  which is the case a future third residual would fall into.
- **Why it matters:** the exact-string assertions cover today's two residuals, so D1 is guarded now.
  But `_UNATTRIBUTED_RESIDUAL_FIELDS` is derived precisely so a third residual is discovered
  automatically, and the general-case guard that would then have to catch a mislabelled one cannot.
- **Action:** strengthen the loop to assert what D1 actually requires: collect every rendered
  `…nattributed` bullet's label and its named denominator field, and assert both sets have no
  duplicates and that each denominator matches the residual's entry in `_UNATTRIBUTED_RENDER`.
- **Done when:** the mutation described above (both residuals sharing a label and a denominator)
  makes this loop fail, verified by re-running it against the mutated module and restoring from a
  byte snapshot.
- **Effort:** S
- **Risk if fixed:** none — test-only.

---

## G9 — Test the absent-denominator render fallback

- **Kind:** test-gap
- **Severity:** low
- **Topic:** tests
- **Where:** `marketplace/bundles/plan-marshall/skills/manage-metrics/scripts/manage-metrics.py:2358-2362`
  (the `else` branch of the residual render)
- **Evidence:** `grep -rn "not recorded on this row" test/` returns nothing. The branch renders
  `- **{label}**: {value:,} ({note}; denominator {denom_field} not recorded on this row)` and is
  reached whenever the denominator field is absent or non-numeric on the row.
- **Why it matters:** the branch is the one place a residual is rendered **without** a denominator,
  which is the state D1 forbids in general — so its exact wording is what makes the omission legible
  rather than a silent bare `unattributed`. It is unreachable from a runtime-produced row (the
  runtime emits the full key set unconditionally, `contract.md:983`) but reachable from a truncated
  or hand-edited `metrics.toon`, which archived records demonstrably are.
- **Action:** add a test that writes a `metrics.toon` phase row carrying `cache_read_unattributed`
  without `cache_read_input_tokens`, runs `cmd_generate`, and asserts the bullet names the residual's
  quantity and states that the denominator was not recorded — i.e. that the omission is disclosed
  rather than defaulted.
- **Done when:** deleting the `else` branch (leaving only the denominator-bearing form) makes at least
  one test fail.
- **Effort:** S
- **Risk if fixed:** none — test-only.
