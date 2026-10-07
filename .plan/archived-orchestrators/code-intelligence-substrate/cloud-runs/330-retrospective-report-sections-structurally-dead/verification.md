# Verification — 330-retrospective-report-sections-structurally-dead

**Audited:** `plan.md`, `report-01.md` (the directory holds no other file)
**Tree state:** `dd1eea1` on `claude/code-intelligence-substrate-analysis-kah884`
**Overall verdict:** CONFIRMED WITH GAPS

The plan landed as squash commit `9135f27` ("fix(plan-retrospective): the written/omitted/dropped
partition means what it says (#1287)"), 25 files changed, +2091/−66. All five deliverables are
present in the tree and satisfy their literal *Done when*. Every numeric claim in `report-01.md` that
can be re-derived from this clone was re-derived and matched exactly. The gaps are (a) the residue
the run itself declared and deliberately did not fix — still open — (b) one unreported drop-side hole
in the same partition, and (c) documentation defects in shipped skill files.

## Deliverable verdicts

| # | Deliverable (short) | Report claim | Ground truth | Verdict |
|---|---|---|---|---|
| D1 | Assert *written implies non-empty*; a zero names its checked set | Placeholder branch emits no heading; class-level fix on both render paths; `sections_unattributed_zero` reported | `compile-report.py:536-548`, `:562-578`, `:604-610`, `:295-333`; empty bundle: pre 11 written / 11 placeholders / 6 omitted → HEAD 0 / 0 / 17 (re-measured) | CONFIRMED |
| D2 | Gate: reachability of every registry row, two counts published | 17 rows examined, 2 dead (`_executive-summary`, `dispatch_boundaries`); mutated nothing | `retro_sections.py:28-80` holds exactly 17 rows; the two dead keys are exactly `SECTION_SPEC` keys − aspect-table keys; no producer writes either | CONFIRMED |
| D3 | Aspect table carries the canonical registry key, derived not transcribed | Key column added, header-anchored positional guard, three rows differ from their reference basename | `SKILL.md:180-196` (15 rows, all keys valid); guard `test_registered_aspects_render.py:321-404`; three basename-divergent rows re-derived | CONFIRMED |
| D4 | Session identity is a LIST; observer appends; multi-session representable | `session_ids` + `manage-status metadata --set --append`, atomic, `SHIM(B)` legacy read | `claude_runtime.py:1487-1594`, `_status_query.py:190-297`, `_status_core.py:398-418`; six doc surfaces updated | CONFIRMED |
| D5 | Tests re-baselined; each labelled regression or characterization | 54 test functions added; the two re-baselined assertions shipped as characterization | 54 added `def test_` lines re-derived from the squash diff (10/1/30/5/8 per file, all matching); pre-plan replay reproduces the report's quoted output verbatim | CONFIRMED |

## Per-deliverable detail

### D1 — assert the partition invariant, with the placeholder as its failing case

- **Required (plan):** *"an empty-bodied section is not listed as written, and a zero-reporting
  section names its checked set."*
- **Claimed (report):** the placeholder branch emits no heading at all; the fix is class-level over
  both render paths; `unattributed_zero_sections()` publishes `sections_unattributed_zero`, reported
  and never gating; vocabulary derived from producers and declared in `retro_sections.py`.
- **Found:**
  - `compile-report.py:536-548` — the `_executive-summary` branch: absent/empty ⇒ `omitted`,
    payload-bearing-but-unrenderable ⇒ `dropped`, never `written`.
  - `compile-report.py:427-472` `_fragment_renders_empty` — for a dict, delegates to
    `_fragment_has_payload`; `''`/`{}`/`[]`/`False` empty; `0`/`0.0` content.
  - `compile-report.py:562-578` (static loop) and `:604-610` (generic fallback, below the
    `spec_keys` skip) — both paths partition to `omitted`.
  - `compile-report.py:295-333` `unattributed_zero_sections`, wired at `:663`; status at `:653-655`
    depends only on `dropped`, so the probe is non-gating as claimed.
  - `retro_sections.py:148-162` — `ZERO_ATTRIBUTION_FIELDS` (5 names) and
    `ZERO_DECLARED_UNMEASURED_STATUSES`.
- **Checks run:**
  - Re-measured the report's before/after table on an empty bundle by loading the pre-merge module
    (`git show 9135f27^:…/compile-report.py`) and the HEAD module: pre = **11 written, 10
    `_No data provided._` + 1 `_No executive summary provided._` = 11 placeholder bodies, 6 omitted**;
    HEAD = **0 written, 0 placeholders, 17 omitted**. Identical to the report's table.
  - Mutation A: `_fragment_renders_empty` dict branch forced to `return False` (i.e. the pre-round-3
    container test's weakest form) → `7 failed, 87 passed`, failures being
    `test_an_empty_fragment_is_not_written[dict]`, all five `test_a_dict_with_no_payload_is_not_written`
    cases and `test_written_implies_payload_holds_for_every_registry_row`.
  - Mutation B: `_names_checked_set` narrowed to top-level only → exactly **one** failure,
    `test_a_population_published_one_level_down_counts_as_attribution` — confirming F30's correction
    that this is the sole witness for the nesting pass.
  - Restored both files from byte snapshots taken before mutation; `git status --porcelain` clean for
    both afterwards.
- **Verdict:** CONFIRMED. One nuance, not a defect: the second half is delivered as a *reported
  counterexample set*, not as an enforced property — which is what the plan's
  "⭐ **The counterexample set is evidence too**" sanctions. The signal has no documented consumer
  action, however (see gaps).

### D2 — GATE: registry rows against their reachability

- **Required (plan):** *"every row carries a reachability verdict and both counts are published."*
- **Claimed (report):** rows examined **17**, dead rows **2**; `_executive-summary` not registerable
  and with no producer; `dispatch_boundaries` registerable and renderable but produced only nested
  inside the `log-analysis` fragment. Nothing was mutated.
- **Found / re-derived:**
  - `len(SECTION_SPEC) == 17` (executed).
  - `SECTION_SPEC` keys − Step-3 aspect-table keys = `['_executive-summary', 'dispatch_boundaries']`
    (executed against the live table) — exactly the two dead rows, and the table's 15 keys are all
    valid registry keys.
  - `_executive-summary`: `collect-fragments.py:298-299` rejects `_`-prefixed keys; a tree-wide grep
    finds the string only in `retro_sections.py`, `compile-report.py` and `report-structure.md` —
    **no producer anywhere**.
  - `dispatch_boundaries`: `analyze-logs.py:1692` returns it as a key *of its own fragment*, so it
    lands at `fragments['log-analysis']['dispatch_boundaries']`; no `--aspect dispatch_boundaries`
    command exists in `SKILL.md` or any referenced document.
  - `git show 9135f27 --stat` shows no source change attributable to D2.
- **Verdict:** CONFIRMED. Both counts published, both verdicts reproduce first-party.

### D3 — the documentation that instructs a registration supplies the exact argument

- **Required (plan):** *"each row carries its canonical key, derived rather than transcribed."*
- **Claimed (report):** Key column added; the absence was re-derived; three of fifteen rows differ
  from their reference-document basename; the column cannot drift because a header-anchored
  positional guard pins it to `SECTION_SPEC`.
- **Found:** `plan-retrospective/SKILL.md:180-196` — header `| Order | Aspect | Key | Script(s) |
  Reference |`, 15 numbered rows each carrying a backticked key. Guard:
  `test_registered_aspects_render.py:71-108` (header assertion + positional read) and
  `:321-404` (`TestAspectTableKeysMatchTheRegistry`, 5 methods / 5 collected, including a bite test
  that runs the real parser over a deliberately corrupted copy of the live table).
- **Checks run:** re-derived the basename divergences from the table — `invariant-summary` vs
  `invariant-check-summary`, `manifest-decisions` vs `manifest-crosscheck`, `routing-decisions` vs
  `routing-decision-verification` — exactly **three of fifteen**. Executed the correspondence check:
  no table key is outside `SECTION_SPEC`. Test class collects 5, as the report states.
- **Verdict:** CONFIRMED. The plan's ⛔ "derive, never restate" is honoured in the operative sense
  (the declaring source is named and a guard fails on divergence); the run flagged this judgement
  call itself, which is the correct handling.

### D4 — the retrospective stops destroying its own primary input

- **Required (plan):** *"the identity is a list, the observer appends, and a multi-session run is
  representable."* Plus ⛔ no scalar-unchanged guard.
- **Claimed (report):** `session_ids` list; `manage-status metadata --append` as a `--set` modifier,
  idempotent, atomic inside `rmw_json`, refusing a non-list field; read returns the **last** entry
  with a `SHIM(B)` legacy fallback; `--append` refused for `--store orchestrator`; six documentation
  surfaces updated.
- **Found:**
  - `claude_runtime.py:1491-1535` — capture passes `--set --append --field session_ids`.
  - `claude_runtime.py:1568-1594` — read walks `reversed(values)`, then the `SHIM(B)`-marked legacy
    scalar with owner/floor/removal trigger recorded.
  - `_status_query.py:190-268` — the append runs inside `rmw_json`; absent ⇒ `[value]`; list ⇒
    appended unless present; non-list ⇒ `metadata_field_not_a_list` with the document left
    byte-identical (asserted on bytes by `test_manage_status_metadata.py:259-280`).
  - `_status_core.py:407-418` — orchestrator store refuses `--append` (`append_unsupported_for_store`).
  - Six read-side surfaces carry `session_ids`: `phase-6-finalize/SKILL.md:79-86`,
    `plan-marshall/workflow/execution.md:544-566`,
    `persona-plan-marshall-agent/standards/tool-usage-patterns.md:341-346`,
    `manage-status/SKILL.md:73,285`, `phase-1-init/SKILL.md:784-790`,
    `plan-marshall/SKILL.md:240`. A tree-wide grep for `metadata.session_id` / `--field session_id`
    outside `doc/plans/` returns only the deliberate legacy-fallback mentions.
  - No guard asserting the identity is unchanged exists — as the plan required.
- **Checks run:** mutated the read path to `for value in values:` (first instead of last) →
  `test_read_returns_the_most_recent_entry` fails, 274 others pass; file restored from a byte
  snapshot, `git status` clean. Read
  `test_a_resume_on_a_pre_list_plan_does_not_fail` (`test_manage_status_metadata.py:328-357`) — it is
  the plan's literal multi-session verification case and it is non-trivial.
- **Verdict:** CONFIRMED. One unstated incompleteness: a pre-list plan's legacy scalar is never
  folded into the list, so after the first post-change capture the earlier identity is no longer
  reachable through `_manage_status_read_session` (the list wins — pinned deliberately by
  `test_the_list_wins_over_a_stale_legacy_scalar`). See gaps.

### D5 — tests, RE-BASELINED

- **Required (plan):** two previously-planned assertions must not ship as regression proofs; each
  retained test labelled regression or characterization, and it must say which.
- **Claimed (report):** a per-test label table; the two re-baselined assertions shipped as
  characterization with the class docstring saying so; 54 test functions added.
- **Found:** `TestSkippedFragmentPartitionCharacterization`
  (`test_compile_report_behavior.py:621-660`) — the docstring states plainly "CHARACTERIZATION —
  pins SHIPPED behaviour. NOT a regression proof."
- **Checks run:**
  - Re-derived the added-test count: `git show 9135f27 -U0 -- test/ | grep -c "^+ *def test_"` →
    **54**; per file 10 / 1 / 30 / 5 / 8 — every sub-count in the report matches.
  - Replayed the two characterization cases against the pre-merge module with the *conditional* row
    the tests use: `PRE-PLAN | bare skipped -> omitted`, `PRE-PLAN | skipped+skip_reason -> dropped`
    — byte-for-byte the output the report quotes.
  - Collected counts for the classes the report names: `TestZeroReportingSectionNamesItsCheckedSet`
    → **21**, `TestAspectTableKeysMatchTheRegistry` → **5**, and the five parametrized cases the
    table annotates (10 + 5 + 5 + 2 + 2) → **24** collected. All match.
- **Verdict:** CONFIRMED.

## Correctness review

I read `compile-report.py` in full, `retro_sections.py` in full, the append/read paths in
`_status_query.py`, `_status_core.py` and `claude_runtime.py`, and the two new test modules. One
genuine defect was found, plus the run's own declared residue (below).

**Defect — a non-dict, non-empty fragment on a CONDITIONAL row is silently classified as a benign
omission.** `compile-report.py:550-559`: when `should_emit` refuses a fragment, the drop/omit split
is made by `_fragment_has_payload` (`:171-196`), which returns `False` for *every* non-dict. But the
compiler's other discriminator, `_fragment_renders_empty` (`:427-472`), calls the same value
**content**. Executed at HEAD:

```
'real prose the producer wrote' -> renders_empty False | has_payload False | conditional row: omitted
                                                                          | always-emit row: written
42                             -> renders_empty False | has_payload False | conditional row: omitted
                                                                          | always-emit row: written
```

So the same value is content on one render path and "nothing was lost" on the other. This is the
loud-half-goes-quiet direction of exactly the miscalibration the plan exists to kill, and no test
covers it.

**The path is reachable in production.** `parse_toon` yields `''` only for a *valueless* key; a key
carrying prose yields the prose. Executed:
`parse_toon('script-failure-analysis: the producer wrote prose instead of a fragment')` →
`{'script-failure-analysis': 'the producer wrote prose instead of a fragment'}`, and
`build_document` on that bundle returns `Script Failure Analysis` in `sections_omitted`,
`dropped == []`, status `success`. That is the same producer scenario — an aspect writing prose
instead of a fragment, accepted by `collect-fragments._read_fragment` — that the run's verification
round 2 fixed on the *written* half; the conditional half was left uncorrected. It also contradicts
`references/report-structure.md:41`, which requires a present, payload-carrying, non-rendering
fragment to be a drop. Filed as a **high** gap (G1) on that basis, not the medium this section
originally assigned.

Everything else read clean: the `chat-history-analysis` carve-out still sits **before** the status
guard (`:132-135`, pinned on rendered output by
`test_registered_aspects_render.py:532-549`); the fallback loop's emptiness check sits **below** the
`spec_keys` skip (`:598-610`), so F21's phantom heading cannot recur; `False` is filtered by identity
in `_fragment_has_payload`, `_names_checked_set` and `_has_attribution_field`, so a measured `0`
survives; the metadata append commits inside `rmw_json`'s critical section, so there is no
check-then-act window; and the orchestrator store refuses `--append` instead of silently overwriting.

## Documentation-standards sweep of the shipped surfaces

`CLAUDE.md` § Documentation Standards forbids version history and transitional narrative. Three
places the plan touched now carry a paragraph about the plan's own editing history, all read
first-party:

- `plan-retrospective/SKILL.md:311` — *"…deliberately **not enumerated here**: an earlier version of
  this sentence listed the fields and then told the reader not to restate them, and it was left
  naming three when the registry had grown to five."* The gate that would catch this,
  `no-historical-prose-in-skills`, cannot: `plan-retrospective/**` is one of the seven allowlisted
  paths recorded at `plugin-doctor/references/rule-provenance.md:205` (verified verbatim).
- `compile-report.py:442-445` — *"testing the container was one of several attempts that each closed
  a narrower case than the invariant needs — no count is given here, because a count of attempts goes
  stale on the next one."*
- `retro_sections.py:132-134` — *"Those last two were added after a sweep over the eight in-tree
  deterministic producers, which flagged `check-artifact-consistency` and `summarize-invariants` on
  every clean run."*

The last two are outside `no-historical-prose-in-skills`'s file scope entirely — that rule is
markdown-only (`rule-catalog.md:754` describes its `.py`-covering sibling as deliberately broader) —
so the allowlist reasoning applies to the first only. Filed as G10, G11, G12, all low.

## Test adequacy

| Deliverable | Covering tests | Non-vacuity evidence |
|---|---|---|
| D1 written-half | `TestWrittenImpliesNonEmpty` (12 methods / 30 collected), `test_registered_aspects_render.py` fallback cases | Mutation A (dict branch → `return False`) turns 7 red |
| D1 zero-half | `TestZeroReportingSectionNamesItsCheckedSet` (15 methods / 21 collected) | Mutation B (drop the one-level nesting pass) turns exactly the named witness red; the class also carries its own two-directional probe (`test_probe_bites_only_on_the_defect_it_names`) |
| D2 | none needed (a derivation that mutated nothing); `TestRegisterableAspectsRenderable` covers the adjacent completeness contract | anchor tests (`test_scanner_finds_the_routing_decisions_dispatch`, `…reaches_aspects_dispatched_from_their_reference_doc`) prevent a vacuous empty population |
| D3 | `TestAspectTableKeysMatchTheRegistry` (5/5) | `test_guard_bites_on_a_key_that_is_not_in_the_registry` runs the real parser over a corrupted copy of the live table and asserts the clean table is clean — F13's vacuity is genuinely repaired |
| D4 | `TestSessionIdentityIsAList` (8), `test_manage_status_metadata.py` append suite (10), `test_orchestrator_store.py:219` | Mutation (read first instead of last) turns `test_read_returns_the_most_recent_entry` red; byte-identity asserted on the refusal path |
| D5 | the label table itself | Replay against the pre-merge module reproduces the quoted characterization output |

No vacuous or tautological guard was found. The only **test gap** is the drop-side asymmetry in the
Correctness review above, and the one-directional D3 guard the run declared as survivor F15
(`registry → table` is asserted by nothing; the class docstring records this and names the re-open
condition).

## Report accuracy

Every re-derivable claim held. Specifically re-measured rather than copied:

- "17 registry rows examined, 2 dead" — 17 rows; the two dead keys are exactly the registry keys
  absent from the aspect table.
- "`origin/main` 11 written / 11 placeholders / 6 omitted → HEAD 0 / 0 / 17" — reproduced exactly by
  loading both module versions.
- "three of fifteen rows have a key differing from their reference basename" — exactly three.
- "**54 test functions**" and the 10 + 1 + 30 + 5 + 8 split — all five figures match.
- "`TestZeroReportingSectionNamesItsCheckedSet` (15 methods, 21 collected at HEAD)" and
  "`TestAspectTableKeysMatchTheRegistry` (5 methods, 5 collected)" — 21 and 5.
- "14 `*.py` files changed … (25 files changed overall)" — 14 and 25.
- The quoted pre-plan replay output — reproduced verbatim.
- The quoted CodeRabbit body ("Reviewed the PR. I found no actionable issues. …") — genuine, read
  from PR #1287 comment `5322241825`, including the "⚠️ Action not completed — Review rate limited"
  footer the report says it kept rather than smoothed over.
- Commits `6bad96f`, `8d60be8`, `498f21d`, `9107964` exist on the PR's 23-commit history with the
  deliverables the report attributes to them.
- F5's residue quotes — `SKILL.md:31` "dispatch the 14 aspect references", `:52` "9 aspects iterate
  inside one envelope", `:54` "The 8 in-context analytical aspects" — all still present verbatim.

One claim is inaccurate, minor and confined to the report:

1. **Step-8 head.** "conditions 1–3 met on head `2dd1b31` … then auto-merge armed" — the merged head
   is `1e0354390e6aed68afaa40e19d5dc53c8137adb3`, one commit later. CI did re-run and pass on that
   head (`verify / conclusion` success at 01:37, merge at 01:53), and the run *did* disclose the
   moved head in a PR comment, but the report's contract-check row does not record it. Re-confirmed
   against the PR API: `head.sha` = `1e03543…`, merged `2026-08-18T01:53:25Z`, and `2dd1b31` is the
   second-to-last of the PR's 23 commits.

A second claim this section originally listed as inaccurate is **not**. `report-01.md:214` reads
*"**Six** documentation surfaces that instruct this read were updated"* — the qualifier *that
instruct this read* is load-bearing and the sentence is exact. All six read-side surfaces were
re-verified verbatim at their cited lines; the seventh surface, `platform-runtime/SKILL.md:38`,
describes the **write** (`| session capture | APPEND current session id to
status.metadata.session_ids via manage-status; no-op on OpenCode |`), which that sentence does not
claim to cover. It is recorded under collateral below, and no gap is filed for it.

One quoted figure is **UNVERIFIABLE**: the report renders CodeRabbit's limit notice as "Next review
available in: **38 minutes**"; the comment body on GitHub now reads "50 minutes" and carries an
`updated_at` later than its `created_at`, so the body was edited after the report quoted it. No
finding is filed.

Claims that cannot be checked from this clone, each recorded rather than assumed: the per-commit
`./pw quality-gate` outputs, `mypy … 412 source files`, `./pw verify` = `20723 passed, 14 skipped`
in 372 s, and the 34-input-class round-4 differential. The branch commits are not fetched here
(`git cat-file -t 2dd1b31` → *Not a valid object name*), so only the PR API view of them is available.

## Declared residue — current status

| Residue item (from report) | Still open? | Evidence |
|---|---|---|
| 1. Three conditional rows report a false `sections_dropped` + `warning` on ordinary plans | **OPEN** | Executed at HEAD: the real clean-run `script-failure-analysis` fragment gives `should_emit: False`, `_fragment_has_payload: True`, `dropped: ['Script Failure Analysis']`. The manifest-less shapes of `check-manifest-consistency` / `check-routing-decisions` (both `status: skipped` + `reason`) give `dropped: ['Manifest Decisions', 'Routing Decisions']` |
| 2. `dispatch_boundaries` is a dead registry row | **OPEN** | `analyze-logs.py:1692` still nests it inside its own fragment; no `--aspect dispatch_boundaries` anywhere; the row is absent from the aspect table |
| 3. `_executive-summary` has no producer | **OPEN** | No producer in the tree (`_executive-summary` appears only in `retro_sections.py`, `compile-report.py` and `report-structure.md`); executed at HEAD, `Executive Summary` lands in `sections_omitted` on every bundle, so the shipped report carries none, and the compiler's written branch for the row (`compile-report.py:547-548`) is unreachable in production. ⚠ `report-structure.md:13` does **not** contradict this: it makes the section explicitly "Conditional on a body existing" and requires no heading when the fragment supplies no narrative. What it does still state is mandatory *content* for a section nothing can produce |
| 4. F1 — a self-declared skip naming its reason is classified as a drop | **OPEN** | Same execution as residue 1; `TestSkippedFragmentPartitionCharacterization:648` pins it |
| 5. F5 — aspect-count lead-ins disagree with the 15-row table | **OPEN** | `SKILL.md:31`, `:52`, `:54` unchanged; the "8 in-context analytical aspects" parenthetical itself enumerates nine items |
| 6. F15 — the aspect-table correspondence guard runs in one direction only | **OPEN** | `test_registered_aspects_render.py:331-337` records the limitation and its re-open condition; no `registry → table` assertion exists |

Nothing in the residue was closed by a later plan on this branch. The plan's own **sequencing
warning** (the retrospective reading a destroyed footprint input) is substantively owned by the
sibling plan `250-footprint-read-outside-its-window`, which has landed and whose resolver fallback is
visible at `plan-retrospective/SKILL.md:200`; the run report, however, records no disposition for the
warning at all.

## Out-of-scope and collateral

Respected. Nothing forbidden was built:

- *Making the skipped-fragment case an omission rather than a drop* — not done; F1 explicitly rejected
  as out of scope and pinned as characterization instead.
- *Making the headline section registerable* — not done; `collect-fragments.cmd_add` still rejects
  `_`-prefixed keys and no producer was added.
- *The producerless per-dispatch context-load columns* — untouched; the diff contains no
  `manage-metrics` change.
- *Fixing the finalize step ordering* — untouched; the only `phase-6-finalize/SKILL.md` change is the
  six-line `session_ids` read instruction.

Collateral beyond the retrospective bundle is all D4-driven and declared: `manage-status` (3 scripts
+ SKILL.md), `platform-runtime` (3 scripts + SKILL.md), and four read-side documentation surfaces.
`platform-runtime/SKILL.md:38` (the verb-table row) is a **write**-side surface, correctly outside
the report's six-surface *read*-side enumeration; it is covered by the report's own beyond-diff sweep
commit (`533fe2d`, "describe session capture as an append at every surface"). Nothing undeclared.

## Method and coverage

**Checked, by execution:** loaded both the HEAD and the pre-merge (`9135f27^`) `compile-report`
modules in-process and re-measured the written/omitted/dropped partition on an empty bundle, on the
real clean-run `script-failure-analysis` fragment, on the manifest-less `manifest-decisions` /
`routing-decisions` shapes, on the two skipped-fragment characterization shapes, and on non-dict
fragments; re-derived the registry size, the trigger-`None` row count, the attribution vocabulary
size, the aspect-table key set and its difference from `SECTION_SPEC`; counted added test functions
from the squash diff overall and per file; collected the parametrized test counts the report states.

**Checked, by mutation** (three mutations, each restored from a byte snapshot I took under
`$TMPDIR/verify-330-mutsweep/`, never with `git checkout`/`restore`/`stash`; `git status --porcelain`
verified clean for each file afterwards): the `_fragment_renders_empty` dict delegation, the
`_names_checked_set` nesting pass, and the `_manage_status_read_session` last-entry read.

**Checked, by reading:** all of `compile-report.py` and `retro_sections.py`; the append/read paths in
`_status_query.py`, `_status_core.py`, `claude_runtime.py`; `collect-fragments.py`'s validation;
`plan-retrospective/SKILL.md` Step 3/Step 4; `references/report-structure.md`;
`test_compile_report_behavior.py`, `test_registered_aspects_render.py`,
`test_manage_status_metadata.py`, the `TestSessionIdentityIsAList` block.

**Checked, via the GitHub API:** PR #1287 state (merged, 25 files, +2091/−66), its 23 commits, its
check runs, and its five comments (reviewer verdicts and the quoted CodeRabbit body).

**Not checked, and why:** the full `./pw verify` (out of scope per the audit brief — the reported
`20723 passed` and the `mypy … 412 source files` line are therefore UNVERIFIABLE here); the run's
34-input-class round-4 differential (the harness for it was not committed); the machine-local run
records behind the D4 near-miss (the plan itself forbids looking for them, and the defect was settled
structurally instead); the branch's individual commits' trees (not fetched into this clone).

A concurrent audit agent has `marketplace/…/manage-tasks/scripts/_qgate_closure.py` modified in this
working tree; it is untouched by this audit and unrelated to this plan.

## Adversarial review

Independent review of this document and `gaps.md`. Attacks run: A1 false positives, A2 false
negatives, A3 vacuous evidence, A4 counts and quotes, A5 actionability, A6 severity/topic,
A7 coverage, A8 internal consistency.

Reviewed at tree `ecf3187` (the audit above was taken at `dd1eea1`; the intervening commits are
`doc/plans/**` adversarial-review documents only and touch no surface either document cites). Every
production-file citation below was re-read from `git show HEAD:` rather than from the working tree,
because concurrent agents held `check-routing-decisions.py` and `_invariants.py` mutated during this
review — a working-tree read of `check-routing-decisions.py` gave line numbers 8 off from HEAD, which
would have produced a spurious stale-citation finding.

| # | Attack | What was found | Correction applied |
|---|---|---|---|
| 1 | A1 false positives | Walked every `path:line` in both documents. All held against HEAD: `compile-report.py` `:171-196` / `:295-333` / `:336-383` / `:427-472` / `:527-548` / `:550-559` / `:562-578` / `:598-610` / `:653-655` / `:663`; `retro_sections.py:32`, `:40`, `:132-147`; `collect-fragments.py:298-299`; `analyze-logs.py:1692`; `script-failure-analysis.py:506-521`; `check-manifest-consistency.py:709-718`; `check-routing-decisions.py:727-736`; `SKILL.md:31/:52/:54/:200/:311`; `report-structure.md:13/:17/:33/:37/:41/:65`; `rule-provenance.md:205`; the six `session_ids` doc surfaces; `test_registered_aspects_render.py:321-404/:331-337/:532-549`; `test_manage_status_metadata.py:328-357`; `_status_query.py:190-268`; `_status_core.py:407-418`; `claude_runtime.py:1491-1535/:1568-1594`. **Two false sub-claims found**, both inside otherwise-real gaps. (a) G6 and residue row 3 asserted that `report-structure.md:13` "lists it as section 1 of what the compiler must emit" and that "the specification and the shipped behaviour disagree" — that line explicitly makes the section "Conditional on a body existing" and requires no heading without a narrative, so the compiler conforms exactly. (b) G5 asserted "nothing can ever populate `fragments['dispatch_boundaries']`" — the key IS registerable (`valid_aspect_keys()` returns 16 keys including it), so a `collect-fragments add --aspect dispatch_boundaries` would be accepted; what is absent is a producer and a documented step | Rewrote G6's Evidence/Why-it-matters around the producer-side defect and the section-1 *content* requirement, with the ⚠ correction stated in the entry; rewrote residue row 3 the same way; rewrote G5's Evidence to say registerable-but-unproduced and to record that the data still reaches the reader inside Log Analysis |
| 2 | A2 false negatives | Re-derived every *Done when* from `plan.md` against the shipped code, not against the audit's reasoning. D1: re-measured the empty-bundle partition against both module versions — PRE `11 written / 11 placeholders / 6 omitted`, HEAD `0 / 0 / 17`, exactly as claimed. D2: `len(SECTION_SPEC) == 17`, dead set `['_executive-summary','dispatch_boundaries']`. D4: append runs inside `rmw_json`, orchestrator store refuses `--append`, no scalar-unchanged guard exists. D5: 54 added `def test_`, split 10/1/30/5/8. All five verdicts stand. **One understatement found:** the Correctness review called the non-dict drop-side asymmetry's reachability "narrow", reasoning that `parse_toon` yields `''` or a dict. Executed: `parse_toon('script-failure-analysis: the producer wrote prose instead of a fragment')` returns a bare non-empty **string**, and `build_document` on it omits the section with `dropped == []` and status `success` — the identical producer scenario the run's own round 2 fixed on the written half, silently unfixed on the conditional half | Replaced the "reachability is narrow" sentence with the executed production path and the `report-structure.md:41` contradiction; carried the same evidence into G1 |
| 3 | A3 vacuous evidence | Re-ran all three mutations the audit claims, each from a byte snapshot under the scratchpad, restored by `cp` and confirmed by md5 + `git status --porcelain` (never `git checkout`/`restore`/`stash`). Mutation A (`_fragment_renders_empty` dict branch → `return False`): **7 failed, 87 passed**, failures exactly the named seven. Mutation B (`_names_checked_set` nesting pass → `return False`): **exactly 1 failed**, `test_a_population_published_one_level_down_counts_as_attribution`. Mutation C (`reversed(values)` → `values`): **1 failed, 274 passed**, `test_read_returns_the_most_recent_entry`. All three reproduce the audit's readings exactly. Also re-read `test_guard_bites_on_a_key_that_is_not_in_the_registry` — it does run the real parser over a corrupted copy of the live table and asserts the clean table is clean, so the audit's non-vacuity claim is sound. Post-restore both suites green (369 passed) | None needed — every mutation claim reproduced |
| 4 | A4 counts and quotes | Re-derived at the moment of checking: registry 17 rows; `valid_aspect_keys()` 16; `trigger=None` rows 11; `ZERO_ATTRIBUTION_FIELDS` 5; aspect table 15 rows; three basename divergences; 54 added tests and the 10/1/30/5/8 split; `TestZeroReportingSectionNamesItsCheckedSet` 15 methods / 21 collected; `TestAspectTableKeysMatchTheRegistry` 5/5; the five parametrized cases 24 collected; `sections_unattributed_zero` exactly 3 non-binary hits; G16's five-term report search exactly 1 unrelated hit; PR #1287 merged head `1e03543…`, 23 commits, 25 files, +2091/−66. **Two defects.** (a) The Test-adequacy table stated `TestWrittenImpliesNonEmpty` "(17 tests / 30 collected)" — the class has **12** methods; 30 collected is right. (b) G8 presented a quote that silently elided the em-dash clause "— deterministic facts judged in-context" from `SKILL.md:54` | Corrected to "12 methods / 30 collected"; restored G8's quote to verbatim and noted that the em-dash clause qualifies the seventh item rather than adding a tenth |
| 5 | A5 actionability | Every entry carries a concrete path, a concrete change and an observable *Done when*. No "review X" / "consider Y" / "investigate Z" survives. G2's *Done when* correctly demands a test built from the producer's own output; G5's and G6's are correctly written as either-or, since both admit two legitimate resolutions. G15/G16 target `report-01.md`, a dated record — restating a row and adding a disposition line are both observable and do not rewrite the run's narrative | None needed; added an explicit closing clause to G6's *Done when* so the `report-structure.md:13` content requirement cannot be left orphaned by either resolution |
| 6 | A6 severity and topic | Re-graded all sixteen against the calibration. **G6 raised medium → high**: `report-structure.md:13` states mandatory content for section 1 ("a 3-5 sentence narrative … It must lead with overall severity"), `collect-fragments` structurally refuses `_`-prefixed keys, no documented injection step exists, and the compiler's own `written` branch at `:547-548` is unreachable in production — a documented contract implemented on the consumer side and unimplemented on the producer side, so every retrospective ever compiled ships without its headline synthesis. **G5 held at medium**, and the reason is now stated in the entry: nothing is lost from the document, because the per-phase data still renders inside the Log Analysis fragment's JSON block — only the dedicated table is missing. **G1 raised medium → high** on the A2 evidence (a silent content loss on a reachable path, contradicting `report-structure.md:41`), with the frequency asymmetry against G2 recorded so a fix plan still leads with G2. **G9 raised low → medium**: a missing test on a load-bearing path is medium by the calibration, and G5/G6 are the two instances that reached production precisely because the assertion is absent. G2 high, G3/G4/G7/G8 medium, G10–G16 low all confirmed. Topics: `detectors/auditor` for G1–G6 (the retrospective compiler), `bundle-docs`, `tests`, `plan-lane-contract` all match their owning surfaces; G13's `dispatch/finalize` is the least-bad available label for a `claude_runtime`/`manage-status` identity field whose consumer is the finalize session-id resolver, and is left as assigned | Four severity changes applied; preamble severity mix restated as 3 high / 6 medium / 7 low |
| 7 | A7 coverage | All five deliverables have a verdict row and a per-deliverable section; out-of-scope compliance, collateral, report accuracy, the six declared residue items and the method/coverage statement are all present. **One hole:** three gaps (G10, G11, G12 — historical prose in `SKILL.md:311`, `compile-report.py:442-445`, `retro_sections.py:132-134`) traced to nothing in `verification.md` beyond the phrase "documentation defects in shipped skill files" in the preamble | Added a "Documentation-standards sweep of the shipped surfaces" section recording all three verbatim, with the `rule-provenance.md:205` allowlist that suppresses the gate for the first and the markdown-only scope that puts the other two outside it entirely |
| 8 | A8 internal consistency | CONFIRMED WITH GAPS follows from five CONFIRMED rows plus an unreported defect and open residue. Traced both directions. **One hole:** the Report-accuracy section listed *"Six documentation surfaces … were updated"* as one of "two claims are inaccurate" while simultaneously conceding it was "defensible", and no gap was filed for it — an inconsistency in the audit's own bookkeeping. Re-checked the underlying fact: `report-01.md:214` says "Six documentation surfaces **that instruct this read**", the qualifier is load-bearing, all six read-side surfaces verify verbatim at their cited lines, and `platform-runtime/SKILL.md:38` is a **write**-side row the sentence never claimed. The report's claim is exact | Reclassified: the section now names one inaccurate claim (the Step-8 head, G15), states plainly that the six-surfaces claim is accurate as scoped, and records that no gap is filed and why; the collateral paragraph was corrected to match, naming commit `533fe2d` as the sweep that covered the write-side row |

**Residual doubt:** a further round would most likely find something in the two surfaces this one
sampled rather than exhausted. First, the *drop*-side predicate as a whole: G1–G4 were each
reproduced against one fragment shape apiece, and the remaining conditional rows
(`permission-prompt-analysis`, `chat-history-analysis`) were not driven through their producers' real
clean-run outputs — a differential over all conditional rows × all producer statuses is the check
that would settle whether the drop side has three false-loss instances or five. Second, the run
report's own prose: this review re-derived the figures both documents quote from `report-01.md`, but
did not sweep `report-01.md`'s remaining ~60 findings for internal contradiction, and the run itself
predicted that its residue would be "another statement in this branch's prose that its own later
change made false" — a prediction this round confirmed twice over in shipped files and did not test
against the report.

**Verdict on the audit:** SOUND AFTER CORRECTION — every deliverable verdict, every mutation reading
and every re-derivable figure but one held under independent re-execution, and the corrections were
to two overstated sub-claims inside real gaps, one miscounted test class, one non-verbatim quote, one
understated reachability, four severities, and two bookkeeping holes — none of which changed a
CONFIRMED to a non-CONFIRMED or invented a gap that does not exist.
