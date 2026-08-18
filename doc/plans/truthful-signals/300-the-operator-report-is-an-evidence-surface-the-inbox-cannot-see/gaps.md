# Gaps — 300-the-operator-report-is-an-evidence-surface-the-inbox-cannot-see

**Source:** verification.md (same directory)   **Open items:** 9

All four deliverables landed and survived a mutation check; D1's contract text carries one defect of
its own (G2). None of the items below makes the collision check wrong. G1 and G3 are two sides of the
same seam — the `reads`/`destroys` half of D1 is documented but inert. G6–G9 are four instances of one
stale-statement class (`finalize-step-preference-emitter` cited at `order: 61`, real order 992),
recorded per instance; G6 additionally carries the two `architecture-refresh` fixture comments.

## G1 — Pin the two canonical `destroys` declarations with a test

- **Kind:** missing-test
- **Severity:** medium
- **Where:** `marketplace/bundles/plan-marshall/skills/phase-6-finalize/standards/archive-plan.md:9-10` — `destroys:` / `  - plan-directory` (a YAML block sequence, not an inline list); `marketplace/bundles/plan-marshall/skills/phase-6-finalize/standards/branch-cleanup.md:9-10` — `destroys:` / `  - worktree`
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
  above it", and the bullet names those gaps as `12–19, 23–29, 31–39, 41–61, 63–69`. Every one of
  those ranges is **above `push` (11)**, so none of them can hold a pre-push step. The live occupancy
  (`find_implementors('…ext-point-finalize-step')` executed at HEAD) is `3,4,5,6,7,8,9,10` with `push`
  at 11 — the pre-push sub-region is contiguous, leaving only the integers 1–2 free. The bullet's own
  remedy sentence — "a new pre-push step that cannot fit is what the reserved major-step gaps **and,
  if ever needed, a deliberate re-space of the sub-cluster** are for" — therefore offers two remedies
  of which only the *second* is available; the first is structurally impossible, and the row above it
  names only the first as the guarantee. The same row also says the pre-push steps "pack the low
  integers (2–11)" when 2 is unoccupied and 11 is `push` itself.
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
- **Severity:** low — **not a D1 defect.** D1's *Done when* is that the ordering key **can express**
  `reads`/`destroys`, and it does (`ext-point-finalize-step.md:49-50`). Plan 300 explicitly assigns
  *application* to plan 302, so this is charged to the 300/302 seam, not to any row of this plan's
  deliverable table. Re-severitied from `medium` during adversarial review for that reason.
- **Where:** `.claude/skills/finalize-step-review-retrospective/SKILL.md:11` (order 990); `marketplace/bundles/plan-marshall/skills/phase-6-finalize/standards/finalize-step-print-phase-breakdown.md:7` (order 999); `marketplace/bundles/plan-marshall/skills/phase-6-finalize/standards/emit-landing.md:7` (order 1000)
- **What is wrong:** `grep -rn '^reads:'` over `marketplace/` and `.claude/` returns **zero** matches
  (re-run at HEAD during adversarial review — exit 0, no output). Plan 300 § D raised the key because
  the retrospective "reads a metrics file written later **and** runs after the worktree is removed";
  plan 300 built the key and assigned application to plan 302, and 302 landed (PR #1215,
  `5a5446d3`) without declaring it anywhere. Concrete un-declared reads exist and are documented in
  prose: `record-metrics.md:37` states the inline `emit-landing` step "reads this step's recorded
  facts"; `emit-landing.md:93` states it runs before `archive-plan` (1100), "which `destroys:
  [plan-directory]`"; and `test_finalize_step_print_phase_breakdown.py:102` states
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
  false`". Each restatement is currently *correct* against `ext-point-finalize-step.md` § Implementor
  Frontmatter (the `mutates_source` row at `:42` and the `post_run_review` row at `:47`, both re-read
  at HEAD), so this is a duplication risk, not a live contradiction — but the doc's own
  no-restatement claim is false as written. `:39` and `:40` are the sharper case: both sit at or after
  the merge gate, where `finalize-step-order-bands.md:14-16` says "the post-run band contract governs
  the `mutates_source` obligation and this one governs only the numeric allocation".
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
- **Where:** `doc/plans/truthful-signals/300-the-operator-report-is-an-evidence-surface-the-inbox-cannot-see/report-01.md:226`, `:230`, `:303`, `:315` — **four** occurrences of the figure, in § Findings → "Pre-PR verification sub-agent" (`:226`, `:230`), the step-by-step table (`:303`), and the closing lessons prose (`:315`)
- **What is wrong:** The prose says "**One accepted finding: the D2 restatement sweep was incomplete**
  — 11 stale order restatements survived" and "**Disposition — all 11 fixed**". Summing the table's
  own multiplicities gives **13** (`2 + 2 + 1 + 1 + 1 + 4 + 1 + 1`) across 8 files/rows. All 13 fixes
  are present in the landed diff `308528d6`, so the work is complete and only the number is wrong.
  Re-derived during adversarial review: the row multiplicities were re-summed from `report-01.md`
  itself and `grep -n '11 stale\|all 11 fixed\|11 stale restatements'` located four sites, not the two
  this gap originally named.
- **Why it matters:** The retrospective and audit machinery re-derive figures from run reports; a
  count that its own evidence table refutes is the same "a figure nobody re-derived" defect this epic
  is about, sitting in the epic's own record.
- **Fix:** Change the figure at `report-01.md:226`, `:230`, `:303` and `:315` from "11" to "13", or
  restate each as "8 sites / 13 statements" to match the table's shape.
- **Done when:** `grep -c '\b11 stale' report-01.md` returns 0, and every restatement count the report
  states — in § Findings, in the step-by-step table, and in the closing prose — equals 13, the sum of
  the disposition table's own multiplicities.
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
- **Note (adversarial review):** a broader re-sweep (`grep -rn '\b61\b' … | grep -i 'order\|emitter'`
  over `marketplace/`, `.claude/`, `test/`) found **three further instances of the same
  `order: 61` class** that neither report-01.md nor the original verification recorded. They are filed
  per instance as **G7, G8 and G9**. The class total is six sites; this row keeps its original three
  for citation stability. `finalize-step-preference-emitter.md:93` ("`#990` moved this step from
  `order: 80` to the pre-merge settle band") was examined and is **not** an instance — it is explicitly
  framed as history and the next paragraph states the move to 992.
- **Fix:** Update the two `_ORDER_RESOLVABLE_CANDIDATES` comments to `# order 10` and `# order 992`
  (the list is not order-asserted — the fixture resolves orders through the real resolver — so no
  reorder and no permutation change is needed). In `decision-rules.md:463`, rewrite the clause to say
  the correction moved the step out of the post-archive append position, and that the step now sits at
  `order: 992` in the post-run-review band, so the sentence describes the current tree rather than an
  intermediate state.
- **Done when:** No comment or prose statement in those three locations names an order the step does
  not currently declare.
- **Module/topic:** `plan-marshall:manage-execution-manifest` — composer docs and fixtures.

## G7 — Correct the false current-state order claim in `test_validate_loadable.py`

- **Kind:** stale-statement
- **Severity:** low
- **Where:** `test/plan-marshall/manage-execution-manifest/test_validate_loadable.py:309-312` (the
  `test_project_step_order_resolves_from_project_local_skill_md` docstring)
- **What is wrong:** The docstring asserts, in the present tense, that "The consumer-shipped built-in
  `default:finalize-step-preference-emitter` **now sits pre-merge at order 61 (the settle band)**, so
  the former deploy-target-vs-preference-emitter deconfliction that once explained the 81 value no
  longer applies". The step declares `order: 992` (`finalize-step-preference-emitter.md:7`) and
  `post_run_review: true`, i.e. it sits **post-merge**, in the post-run-review band — verified by
  executing `find_implementors('plan-marshall:extension-api/standards/ext-point-finalize-step')` at
  HEAD, which returns `992 default:finalize-step-preference-emitter built-in`. Both the band and the
  number are wrong, and the conclusion the docstring draws ("no longer share a neighbourhood") happens
  to remain true only by accident of the newer, larger value. This is a per-instance sibling of G6,
  discovered by a re-sweep the original verification did not run.
- **Why it matters:** Plan 300's D2 restatement sweep **edited this very file** (commit `308528d6`
  changed `push=10` → `push=11` at `:277` and three `_resolve_step_order`/`_resolve_step_order_verdict`
  pins), so a reader has positive evidence the file was reviewed for stale orders — and this sentence
  survived it. That is the "swept, clean" false signal this epic is about, one screen away from the
  edit that proves the sweep ran.
- **Fix:** In `test_validate_loadable.py`, rewrite the third and fourth docstring sentences to state
  that `default:finalize-step-preference-emitter` sits **post-merge at `order: 992`** in the
  post-run-review band (`post_run_review: true`), so it is nowhere near the 81/85 project-step
  neighbourhood the test pins. Do not change any assertion — the test asserts only
  `deploy-target == 81` and `sync-plugin-cache == 85`, both correct.
- **Done when:** No sentence in `test_validate_loadable.py` names an order for
  `finalize-step-preference-emitter` other than the `order:` its standards doc declares, and the
  docstring's band label matches that doc's `post_run_review` fact.
- **Module/topic:** `plan-marshall:manage-execution-manifest` — order-resolution tests.

## G8 — Correct the stale `# order 61` seed annotation in the declared-step-contract regression fixture

- **Kind:** stale-statement
- **Severity:** low
- **Where:** `test/plan-marshall/manage-execution-manifest/test_declared_step_contract_regression.py:430` — `_EMITTER: None,                   # order 61` (`_EMITTER = 'finalize-step-preference-emitter'`, `:50`)
- **What is wrong:** The `_CONFIG_DECIDED_SEED` literal annotates each seeded step with its order;
  the `_EMITTER` row says `# order 61` where the step declares `order: 992`. The annotations are
  load-bearing for the reader, because the literal's own comment states it is "**Deliberately
  SCRAMBLED** relative to frontmatter order (the merge/archive tail is seeded first) so the sequence
  assertions below are not satisfied by an already-ordered seed" — a reader checks the scrambling by
  reading these numbers.
- **Why it matters:** Commit `308528d6` edited the line **two rows above it** in the same dict literal
  (`'default:archive-plan': None,  # order 1000` → `# order 1100`) and left this one. A stale number
  inside a comment block whose stated purpose is to let a reader verify an ordering property is the
  precise defect class D2's sweep existed to remove.
- **Fix:** In `test_declared_step_contract_regression.py:430`, change the trailing comment from
  `# order 61` to `# order 992`. No assertion or seed-position change is needed — the seed stays
  scrambled with 992 in that position (70, 1100, 20, 22, unresolvable, 992).
- **Done when:** Every `# order N` annotation in `_CONFIG_DECIDED_SEED` equals the `order:` its step's
  standards doc declares.
- **Module/topic:** `plan-marshall:manage-execution-manifest` — composer regression fixtures.

## G9 — Correct the stale `order 61` example in the composer's sort rationale comment

- **Kind:** stale-statement
- **Severity:** low
- **Where:** `marketplace/bundles/plan-marshall/skills/manage-execution-manifest/scripts/manage-execution-manifest.py:2282` — "`` (e.g. ``finalize-step-preference-emitter``, order 61) ``"
- **What is wrong:** The comment above the ascending-order enforcement explains the append-order bug
  and names the incident step as "`finalize-step-preference-emitter`, order 61". The step declares
  `order: 992`. This is the code-side twin of the `decision-rules.md:463` narrative already recorded
  in G6 — the two documents describe the same incident and both fixed its order at the intermediate
  value.
- **Why it matters:** The comment is the maintainer-facing rationale for the single sort choke-point.
  A reader who takes "order 61" as current concludes the emitter is a settle-band step, which inverts
  its `post_run_review: true` classification and contradicts `phase-6-finalize/SKILL.md:1214`
  ("`default:finalize-step-preference-emitter` (order 992, post-merge)").
- **Fix:** In `manage-execution-manifest.py:2282`, change the parenthetical to name the order the step
  carried **at the time of the incident** with an explicit past-tense marker — e.g.
  "(e.g. ``finalize-step-preference-emitter``, which then carried ``order: 80``; it now declares
  ``order: 992``)" — so the sentence describes history without asserting a current order. Keep the
  surrounding explanation of the append-order bug unchanged.
- **Done when:** No comment in `manage-execution-manifest.py` states an order for
  `finalize-step-preference-emitter` without marking it as historical, and any current order it states
  equals the `order:` in `finalize-step-preference-emitter.md`.
- **Module/topic:** `plan-marshall:manage-execution-manifest` — composer source comments.

## Refuted during adversarial review

**None.** Every one of G1–G6 was re-checked against the tree and upheld on its facts; two were
corrected rather than refuted (G2's *What is wrong* elided the doc's second remedy clause; G5 named two
occurrences where there are four) and one was re-severitied (G3, `medium` → `low`, because D1's
*Done when* is the capability and the plan assigns application to plan 302). The evidence for each is
in `verification.md` § Adversarial review. Three new instances (G7–G9) were added.
