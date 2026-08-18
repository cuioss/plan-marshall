# Gaps — 300-the-operator-report-is-an-evidence-surface-the-inbox-cannot-see

**Source:** verification.md (same directory)   **Open items:** 6

All four deliverables landed, are correct, and survived a mutation check. The six items below are
secondary: none of them makes the ordering contract or the collision check wrong. G1–G3 are the same
seam seen from three sides — the `reads`/`destroys` half of D1 is documented but inert.

## G1 — Pin the two canonical `destroys` declarations with a test

- **Kind:** missing-test
- **Severity:** medium
- **Where:** `marketplace/bundles/plan-marshall/skills/phase-6-finalize/standards/archive-plan.md:9` — `destroys: [plan-directory]`; `marketplace/bundles/plan-marshall/skills/phase-6-finalize/standards/branch-cleanup.md:9` — `destroys: [worktree]`
- **What is wrong:** Two normative documents name these exact declarations as the anchors of the
  `reads`/`destroys` vocabulary — `extension-api/standards/finalize-step-order-bands.md:96,98` and
  `extension-api/standards/ext-point-finalize-step.md:50` — and nothing in the tree asserts they
  exist. `grep -rn destroys` over `test/` returns no hit on either declaration, and
  `_IMPLEMENTOR_FRONTMATTER_KEYS` (`extension-api/scripts/extension_discovery.py:889-897`) does not
  list `reads` or `destroys`, so the keys never reach an implementor record and no code path can
  notice their absence. Deleting either line leaves the whole tree green and both documents false.
- **Why it matters:** This is precisely the "a renumber leaves a false statement behind" failure class
  this epic targets, reproduced inside the deliverable meant to close it. A future step author reads
  the contract, sees two worked examples, and finds neither in the frontmatter.
- **Fix:** In `test/plan-marshall/phase-6-finalize/test_finalize_orchestration_routing.py`, beside
  `TestNoTwoFinalizeStepsShareAnOrder`, add a class that reads the two step docs' frontmatter directly
  (the file already resolves step-doc paths for the discovery test) and asserts
  `archive-plan` declares `destroys` containing `plan-directory` and `branch-cleanup` declares
  `destroys` containing `worktree`, with the assertion message naming
  `finalize-step-order-bands.md` § "`reads` and `destroys`" as the contract the declaration serves.
- **Done when:** Deleting either `destroys:` block from its step doc makes that test fail.
- **Module/topic:** `plan-marshall:extension-api` / `phase-6-finalize` — finalize-step ordering contract.

## G2 — Correct the settle band's insertion-room remedy: the named gaps are all post-push

- **Kind:** doc-drift
- **Severity:** medium
- **Where:** `marketplace/bundles/plan-marshall/skills/extension-api/standards/finalize-step-order-bands.md:37` (Settle table row) and `:48-52` (Settle reserved-gaps bullet)
- **What is wrong:** The band row promises "the guaranteed insertion room is in the major-step gaps
  above it", and the bullet names those gaps as `12–19, 23–29, 31–39, 41–61, 63–69`, then says "a new
  pre-push step that cannot fit is what the reserved major-step gaps … are for". Every one of those
  ranges is **above `push` (11)**. The live occupancy (`find_implementors` executed at HEAD) is
  `3,4,5,6,7,8,9,10,11` — the pre-push sub-region is fully contiguous, leaving only the integers 1–2
  free, so the remedy the contract offers a pre-push author cannot be taken. The same row also says
  the pre-push steps "pack the low integers (2–11)" when 2 is unoccupied and 11 is `push` itself.
- **Why it matters:** A third-party or project-local author who needs a `mutates_source: true` step
  ordered before the single push barrier is directed by the contract into 12–19, which runs **after**
  the push — the settle-before-push contract in `phase-6-finalize/SKILL.md:217` inverted. The dispatcher's
  post-PR re-push instrumentation masks the consequence rather than surfacing it, so the mis-numbering
  goes unnoticed.
- **Fix:** In the Settle row and the Settle bullet, split the band explicitly into a **pre-push
  sub-region (1–11, currently saturated at 3–11)** and a **post-push sub-region (12–69, with the named
  gaps)**. State that the pre-push sub-region has **no** guaranteed insertion room today and that the
  sanctioned remedy for a new pre-push step is a deliberate re-space of the sub-cluster (the doc's own
  second alternative), not the major-step gaps. Correct "pack the low integers (2–11)" to the derived
  occupancy 3–10 plus `push` at 11.
- **Done when:** The Settle band text names no range above `push` as available to a pre-push step, and
  the occupancy figures it states match `find_implementors('…ext-point-finalize-step')` output.
- **Module/topic:** `plan-marshall:extension-api` — `finalize-step-order-bands.md`.

## G3 — Apply the `reads` key to the two mis-orderings that motivated it

- **Kind:** omission
- **Severity:** medium
- **Where:** `.claude/skills/finalize-step-review-retrospective/SKILL.md:11` (order 990); `marketplace/bundles/plan-marshall/skills/phase-6-finalize/standards/finalize-step-print-phase-breakdown.md:7` (order 999); `marketplace/bundles/plan-marshall/skills/phase-6-finalize/standards/emit-landing.md:7` (order 1000)
- **What is wrong:** `grep -rn '^reads:'` over `marketplace/` and `.claude/` returns **zero** matches.
  Plan 300 § D raised the key because the retrospective "reads a metrics file written later **and**
  runs after the worktree is removed"; plan 300 built the key and assigned application to plan 302,
  and 302 landed (PR #1215) without declaring it anywhere. Concrete un-declared reads exist and are
  documented in prose: `record-metrics.md:37` states the inline `emit-landing` step "reads this step's
  recorded facts", and `test_finalize_step_print_phase_breakdown.py:100-102` states
  print-phase-breakdown "reads the generated metrics.md".
- **Why it matters:** The `reads` half of D1 ships as a capability with no instance, so the
  read-before-produce / read-after-destroy error the contract advertises as "a checkable fact" remains
  exactly the runtime accident it was. An unexercised declaration is the inert-deliverable pattern
  plan 300 § E names as this epic's thesis.
- **Fix:** Add `reads: [metrics]` to `record-metrics`' consumers — `finalize-step-print-phase-breakdown.md`
  and `emit-landing.md` — and `reads: [worktree]` to any step whose body genuinely inspects the linked
  worktree (verify each by reading the step body before declaring; declare nothing a step does not
  actually read). Use the vocabulary tokens `metrics` / `worktree` / `plan-directory` fixed by
  `finalize-step-order-bands.md:86-91`.
- **Done when:** At least one step declares `reads:`, every declared token matches a `destroys` token
  or a documented producer, and the band doc's vocabulary paragraph cites a real declaration rather
  than only the two `destroys` anchors.
- **Module/topic:** `phase-6-finalize` step docs — the 300/302 seam.

## G4 — Replace the restated `mutates_source` obligations in the band doc with a pointer

- **Kind:** doc-drift
- **Severity:** low
- **Where:** `marketplace/bundles/plan-marshall/skills/extension-api/standards/finalize-step-order-bands.md:37`, `:39`, `:40`
- **What is wrong:** The doc states at `:11-18` that it "does **not** restate or alter that
  discriminator", and plan 300's Notes required the contract to "CITE it — it must not restate or
  alter the P1/P2 discriminator or the mutual-exclusion rule". Three band rows then restate the
  obligation in band terms: `:37` "A `mutates_source: true` step MUST live here", `:39` "Each MUST
  still declare `mutates_source` explicitly", `:40` "Every member MUST declare `mutates_source:
  false`". Each restatement is currently *correct* against
  `ext-point-finalize-step.md` § Implementor Frontmatter, so this is a duplication risk, not a live
  contradiction — but the doc's own no-restatement claim is false as written.
- **Why it matters:** Two documents now carry the same obligation; the next change to the post-run
  band contract (owned by `code-intelligence-substrate`) has to find this file to stay consistent,
  and the doc's self-description tells a maintainer it need not.
- **Fix:** Reduce each of the three occurrences to a pointer — e.g. "the `mutates_source` obligation
  for this band is owned by [ext-point-finalize-step.md](ext-point-finalize-step.md) § Implementor
  Frontmatter" — keeping only the numeric allocation in this file, which is what `:11-18` already
  declares to be its scope.
- **Done when:** `finalize-step-order-bands.md` states no `mutates_source` obligation of its own, and
  its "does not restate" sentence is true of the file's whole body.
- **Module/topic:** `plan-marshall:extension-api` — `finalize-step-order-bands.md`.

## G5 — Correct the stale-restatement count in report-01.md

- **Kind:** stale-statement
- **Severity:** low
- **Where:** `doc/plans/truthful-signals/300-the-operator-report-is-an-evidence-surface-the-inbox-cannot-see/report-01.md` — § Findings → "Pre-PR verification sub-agent" and its disposition table
- **What is wrong:** The prose says "**One accepted finding: the D2 restatement sweep was incomplete**
  — 11 stale order restatements survived" and "**Disposition — all 11 fixed**". Summing the table's
  own multiplicities gives **13** (`2 + 2 + 1 + 1 + 1 + 4 + 1 + 1`) across 8 files/rows. All 13 fixes
  are present in the landed diff `308528d6`, so the work is complete and only the number is wrong.
- **Why it matters:** The retrospective and audit machinery re-derive figures from run reports; a
  count that its own evidence table refutes is the same "a figure nobody re-derived" defect this epic
  is about, sitting in the epic's own record.
- **Fix:** Change both occurrences of "11" to "13", or restate as "8 sites / 13 statements" to match
  the table's shape.
- **Done when:** Every count in § Findings equals the sum of the table beneath it.
- **Module/topic:** `doc/plans/truthful-signals/300-…` — run report.

## G6 — Clear the surviving stale order comments in the manifest fixtures and decision-rules

- **Kind:** stale-statement
- **Severity:** low
- **Where:** `test/plan-marshall/manage-execution-manifest/test_manage_execution_manifest_validate.py:431` and `:432`; `marketplace/bundles/plan-marshall/skills/manage-execution-manifest/standards/decision-rules.md:463`
- **What is wrong:** `_ORDER_RESOLVABLE_CANDIDATES` still annotates `'architecture-refresh',  # order 25`
  (real order 10) and `'finalize-step-preference-emitter',  # order 61` (real order 992). Both were
  carried forward as residue by report-01.md and both are confirmed **pre-existing** — the `308528d6`
  diff touches only the `push` and `archive-plan` lines of that list. The same sweep found a third
  instance of the class the report did not record: `decision-rules.md:463` says the incident
  "moved the step to its pre-merge `order: 61`", while `finalize-step-preference-emitter.md:7`
  declares `order: 992` and `post_run_review: true`; the 61 → 992 move landed in PR #1080 without
  updating this narrative.
- **Why it matters:** All three read as current-state assertions about real steps. The
  `decision-rules.md` one is the worst of the three: it tells a reader the preference-emitter is a
  pre-merge settle-band step when it is a post-run-review step 900 slots later.
- **Fix:** Update the two `_ORDER_RESOLVABLE_CANDIDATES` comments to `# order 10` and `# order 992`
  (the list is not order-asserted — the fixture resolves orders through the real resolver — so no
  reorder and no permutation change is needed). In `decision-rules.md:463`, rewrite the clause to say
  the correction moved the step out of the post-archive append position, and that the step now sits at
  `order: 992` in the post-run-review band, so the sentence describes the current tree rather than an
  intermediate state.
- **Done when:** No comment or prose statement in those three locations names an order the step does
  not currently declare.
- **Module/topic:** `plan-marshall:manage-execution-manifest` — composer docs and fixtures.
