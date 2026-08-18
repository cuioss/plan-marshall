# Verification — 220-resolver-configuration

**Audited:** `plan.md`, `report-01.md`
**Tree state:** `62e3807` on `claude/code-intelligence-substrate-analysis-kah884` (plan landed as `c0b4f3e`, PR #1252)
**Overall verdict:** CONFIRMED WITH GAPS

The five deliverables are present, wired, and covered by non-vacuous tests (mutation-proven twice).
Two deviations from the plan's literal wording — the binding is keyed on the resolver **id** rather
than a file pattern, and no `precedence` knob was shipped — are declared, argued, and documented in
the shipped docs. One real defect survives: with every resolver switched off, `capabilities` reports
`module_edges: not_derivable` on a project whose `graph` verb still returns edges, because declared
(`internal_dependencies`) edges bypass the resolver seam entirely. The plan's own new three-state
tables do not cover that case.

## Deliverable verdicts

| # | Deliverable (short) | Report claim | Ground truth | Verdict |
|---|---|---|---|---|
| D1 | Resolver-configuration menu | "Done" — new `menu-derivation-resolvers.md`, wired into Configuration Page 4 | Menu exists, wired into Page 4 + routing + TOC + `SKILL.md` table; roster verb exists; round-trip pinned by test. **"Set precedence" is absent** — documented as inexpressible | PARTIAL |
| D2 | `derivation_resolvers` keyed section | "Done" — `run_config.py`, follows `language_servers`, no new store | Section, four verbs, two public reads, persistence into the same main-anchored store; keyed on resolver **id**, not on file pattern/language as D2's wording named | CONFIRMED (deviating key, declared) |
| D3 | Precedence + working default | "Done" — unconfigured ⇒ every resolver active; precedence documented, not shipped | Default is `True` at `run_config.py:826`; the *Done when* test drives the real `get_module_graph` and goes red when the default is flipped. Precedence shipped as documentation only | CONFIRMED (precedence half delivered as docs) |
| D4 | Retire the dead ignore negation | "Done" — negation + stale comment wording only | `.gitignore` diff is exactly `-!.claude/run-configuration.json` plus one comment word change; 47/45/1 tracked `.claude` paths re-enumerated; every neighbouring negation still live | CONFIRMED |
| D5 | Documentation | "Done" — 7 marketplace surfaces + 3 doc/ surfaces | All named surfaces carry the new section; machine-local stated explicitly in the run-config standard | CONFIRMED |

## Per-deliverable detail

### D1 — a resolver-configuration menu

- **Required (plan):** *Done when* the menu lists a discovered resolver and a change round-trips
  through it. The deliverable text also asks for "set precedence".
- **Claimed (report):** new `menu-derivation-resolvers.md` fed by a new
  `extension_api derivation-resolvers list` verb, wired into Page 4 + routing + TOC + `SKILL.md`.
- **Found:**
  - `marketplace/bundles/plan-marshall/skills/marshall-steward/references/menu-derivation-resolvers.md:1-139`
    — roster read (Step 1), presentation (Step 2), enable/disable/reset commands (Step 3), explicit
    re-read round-trip (Step 4, "Report the re-read value, not the value that was written").
  - Wiring: `menu-configuration.md:16` (TOC), `:96-98` (Page 4 option), `:126` (routing row),
    `:821-828` (section body); `marshall-steward/SKILL.md:250` (reference table).
  - Roster verb: `extension-api/scripts/extension_api.py:98-183`, subparser at `:211-222`, documented
    at `extension-api/SKILL.md:507-518`.
  - Round-trip test: `test/plan-marshall/extension-api/test_derivation_resolver_roster.py:160-181`
    (`test_binding_change_round_trips_through_the_roster`, and
    `test_round_trip_persists_to_the_machine_local_store`, which asserts the file contents between
    the write and the re-read).
- **Checks run:** ran the three new test files —
  `uv run python -m pytest test/plan-marshall/extension-api/test_derivation_resolver_roster.py test/plan-marshall/manage-run-config/test_run_config_derivation_resolver.py test/plan-marshall/script-shared/test_extension_base_derivation_resolver.py -o addopts=""` → **50 passed**; and
  `test/plan-marshall/manage-architecture/test_derivation_resolver_configuration.py` → **19 passed**.
  Re-derived the pre-change Page 4 from `git show c0b4f3e^:…/menu-configuration.md` — it carried 2
  options + Back, so the report's "one free slot, filled without restructuring" is accurate; the page
  now holds 3 options + Back (at the 4-element cap).
- **Verdict:** PARTIAL — the *Done when* is fully met, but the deliverable's "and set precedence"
  clause is not implemented. The menu instead documents precedence as inexpressible
  (`menu-derivation-resolvers.md:113-117`). The argument is sound and consistently shipped, but it is
  a deviation from the literal deliverable and is recorded as such.

### D2 — a resolver section in the run-configuration schema

- **Required (plan):** *Done when* the section persists and reloads, following the existing
  keyed-section pattern rather than a new store; the deliverable text says "mapping file pattern (or
  language) to resolver".
- **Claimed (report):** `derivation_resolvers` keyed section with `get`/`set`/`list`/`remove`, plus
  `read_derivation_resolvers_section()` and `is_derivation_resolver_enabled()`, following
  `language_servers` in the same store; keyed on resolver id, with the file-pattern hypothesis
  explicitly refuted.
- **Found:** `manage-run-config/scripts/run_config.py:804-947` — the section banner and rationale
  (`:808-826`), `read_derivation_resolvers_section` (`:829`), `is_derivation_resolver_enabled`
  (`:842`), `cmd_derivation_resolver_get/set/list/remove` (`:864`, `:883`, `:903`, `:935`), argparse
  wiring at `:1360-1387`. The store path is `get_run_config_path()` →
  `resolve_main_anchored_path('run-configuration.json')` (`run_config.py:202-215`), the same store
  `language_servers` uses (`:711-801`). No new file is created.
- **Checks run:** `test_run_config_derivation_resolver.py:122-136`
  (`test_persists_into_the_keyed_section_beside_language_servers`) asserts both sections coexist in
  one config dict read back off disk. `git check-ignore -v .plan/run-configuration.json` →
  `.gitignore:45:.plan/*` — the store is git-ignored, so "machine-local" holds.
- **Verdict:** CONFIRMED on the *Done when*. The binding key is the resolver **id**, which is neither
  of the two keys D2's sentence named; the report refutes the file-pattern hypothesis with three
  arguments I re-checked against the code (`derive_edges` takes module maps and returns
  `(module, module)` pairs — `extension_base.py:1510-1543`; edges carry `{from, to, producers}` only —
  `_cmd_client_query.py:1077-1079`; the single dispatch point is `_derive_edges`, confirmed by
  grepping every caller of `discover_derivation_resolvers`, which returns exactly two: the seam and
  the roster). The refutation is correct; the deviation is declared rather than silent.

### D3 — precedence, and a working default

- **Required (plan):** ⛔ the default MUST be a working default. *Done when:* an unconfigured project
  still derives edges, asserted by test.
- **Claimed (report):** unconfigured ⇒ every discovered resolver active, asserted on an unconfigured
  project; precedence documented as not expressible rather than shipped as a dead knob.
- **Found:** `run_config.py:821-826` — `DERIVATION_RESOLVER_ENABLED_DEFAULT = True`, with an absent
  section, absent entry, and malformed entry all resolving to it (`:842-861`). The seam gate fails
  open on an unreadable store (`_cmd_client_query.py:996-1002`) and per resolver
  (`:1008-1011`); the roster does the same (`extension_api.py:137-161`); the store-listing verb does
  the same (`run_config.py:919-924`).
  Test: `test/plan-marshall/manage-architecture/test_derivation_resolver_configuration.py:142-158`
  (`test_unconfigured_project_still_derives_edges`) — drives the real `get_module_graph`, asserts the
  section is `{}` first, then asserts `resolver_count == 2` and both edges.
- **Checks run — mutation:** set `DERIVATION_RESOLVER_ENABLED_DEFAULT = False` (byte snapshot taken to
  `$TMPDIR/verify-220-mutsweep/run_config.py.orig` first) and re-ran the file: **8 failed, 11 passed**,
  the first failure being `test_unconfigured_project_still_derives_edges`. Restored from the snapshot;
  `cmp` reports IDENTICAL and `git status --porcelain` is clean for that path. The D3 guard is
  non-vacuous.
- **Verdict:** CONFIRMED on the *Done when*. The "precedence when several resolvers claim the same
  file" half is delivered as documentation (declared-over-derived, recorded in
  `run-config-standard.md:316-330`, `ext-point-derivation-resolver.md:213+`,
  `menu-derivation-resolvers.md:113-117`, `doc/user/configuration.adoc:626`) rather than as a
  mechanism. The union-semantics argument is correct — `merge_resolver_edges` collapses a shared pair
  into one edge carrying both producer ids (`_derivation_merge.py:133-136`) — so a `precedence` field
  would indeed be dead config. Deviation declared.

### D4 — retire the dead ignore-file negation

- **Required (plan):** *Done when* the dead rule is gone and a before/after check shows no change to
  what git tracks. ⛔ Surgical: that one negation and the comment wording only.
- **Claimed (report):** tracked file set byte-identical; one ignore verdict changed (the retired path
  itself); neighbouring negations unchanged.
- **Found and re-derived in this clone:**
  - `git show c0b4f3e -- .gitignore` → exactly two removed lines (`!.claude/run-configuration.json`
    and the old comment) and one added comment line. No other hunk.
  - `.gitignore` now carries `!.claude/skills/` (`:27`), `!.claude/commands/` (`:28`),
    `!.claude/settings.json` (`:33`), `.claude/settings.local.json` (`:36`),
    `.claude/lessons-learned/*.md` (`:39`), `.plan/*` (`:45`), `!.plan/marshal.json` (`:46`).
  - `git ls-files .claude/ | wc -l` → **47**; `.claude/skills/` → **45**; `.claude/commands/` → **1**;
    `.claude/settings.json` tracked. (Re-enumerated, not copied from the report — the figures match.)
  - `git check-ignore -v .claude/skills/cloud-plan-lane/SKILL.md` → exit 1 (not ignored);
    `.claude/commands/…` → exit 1; `.claude/settings.json` → exit 1; `.plan/marshal.json` → exit 1;
    `.claude/settings.local.json` → `.gitignore:36`. Every live negation still fires.
  - The retired path: `git check-ignore -v .claude/run-configuration.json` →
    `.gitignore:24:.claude/*` (now caught by the blanket rule, as the report states);
    `git ls-files .claude/run-configuration.json` → empty; the file does not exist.
- **Verdict:** CONFIRMED. Both directions hold — the dead rule is gone, and no live negation changed
  behaviour.

### D5 — documentation

- **Required (plan):** the new menu, what it binds, and where it persists, in the user-facing
  configuration page; the new keyed section in the run-configuration schema standard, **stating
  explicitly that the store is machine-local**.
- **Found:**
  - `manage-run-config/standards/run-config-standard.md:267-375` — "Derivation-Resolvers Section",
    with machine-local stated in its second paragraph (`:274-279`), the id-key rationale
    (`:281-290`), the active-by-default rule (`:292-301`), the reported-not-dropped rule
    (`:303-314`), and the no-precedence rationale (`:316-330`). The maintained Schema block
    (`:17-56`) and Optional Sections table (`:65-75`) both carry `derivation_resolvers`.
  - `doc/user/configuration.adoc:602-639` — user-facing page, including the git-ignored store path,
    the menu route, what it does not configure, and the switched-off-is-visible paragraph.
  - Also updated and verified: `manage-run-config/SKILL.md:250-266`,
    `extension-api/SKILL.md:507-518`, `extension-api/standards/ext-point-derivation-resolver.md:173-215`,
    `extension-api/standards/extension-contract.md:654-663`,
    `manage-architecture/standards/client-api.md:96-105`,
    `manage-architecture/standards/architecture-persistence.md:604-618`,
    `doc/concepts/code-intelligence.adoc:150-163`, `doc/user/dependency-intelligence.adoc:77,110-123`,
    `doc/adr/014-…adoc:77-99,105-115`, and four bundle hook tables
    (`pm-code-intelligence`:50, `pm-dev-python`:48, `pm-documents`:48, `pm-plugin-development`:95).
- **Verdict:** CONFIRMED. The one documentation omission I found is a missing caveat, not a missing
  surface — see G3.

## Correctness review

I read the whole shipped mechanism: the store API (`run_config.py:804-947`), the dispatch gate and
counter (`_cmd_client_query.py:930-1122`), the four `resolver_count` assignment sites
(`_cmd_client_query.py:412`, `_cmd_client_handlers.py:594,622,650`), the `capabilities` handler
(`_cmd_client_handlers.py:142-249`), the rendered footer (`_cmd_client_render.py:67-124`), the roster
(`extension_api.py:92-183`), the ABC method (`extension_base.py:1549-1580`), and the seven resolver
implementations.

**One defect found.**

- **`_cmd_client_handlers.py:196-235` — `capabilities` reports `module_edges: not_derivable` for an
  envelope whose `graph` verb returns edges.** `status` is `'derivable' if resolver_count else
  'not_derivable'`, and `resolver_count` now counts only *dispatched* resolvers. But module edges also
  come from two non-resolver sources that survive a full switch-off: a module's declared
  `internal_dependencies` (stamped `declared`, `_cmd_client_query.py:1219-1222`) and core's
  sibling cross-links (stamped `sibling-cross-link`, `:1238-1240`). Driven directly (probe script,
  `PLAN_BASE_DIR` pointed at a temp store containing `{"alpha": {"enabled": false}}`, one stub
  resolver, one module with `internal_dependencies: ['core']`):

  ```text
  resolver_count: 0
  resolvers: [{'id': 'alpha', 'edge_count': 0, 'status': 'not_dispatched', 'notes': ['configuration: …']}]
  edge_count: 1
  edges: [{'from': 'core', 'to': 'app', 'producers': ['declared']}]
  capability module_edges: {'status': 'not_derivable', 'producers': [], 'producer_count': 0, 'derived_count': 1}
  ```

  `not_derivable` with `derived_count: 1` is self-contradictory, and it is the fourth state the
  handler's own docstring (`:172-176`) says cannot exist. A consumer that gates on `status` —
  which is the verb's entire purpose ("probe once then branch" is what it exists to make sound) —
  skips a `graph` call that would have returned real edges. The state was reachable before this plan
  only with *zero registered resolvers* (never true on a real tree, since seven ship); this plan makes
  it one menu action away. See G1.

**Checked and found sound:**

- The gate has exactly one dispatch site. `grep -rn "discover_derivation_resolvers" marketplace
  --include=*.py` returns the seam (`_cmd_client_query.py:1096`) and the roster
  (`extension_api.py:130`) as the only call sites, so no edge-deriving path bypasses the binding.
- Fail-open is symmetric across all three readers (seam, roster, store-listing verb), and every
  failure mode — import failure, store read failure, per-entry failure, malformed entry, non-dict
  section, missing `enabled` key — resolves to *active*. No branch can blank the graph.
- `count_dispatched` (`:942-957`) excludes only `not_dispatched`; an `error` report still counts, and
  `test_an_errored_resolver_still_counts_as_having_run` pins that.
- Report records stay a uniform 4-key array (`{id, edge_count, status, notes}`), pinned against the
  real TOON serializer at `test_derivation_resolver_configuration.py:424-475`. The R2-1 wire defect is
  genuinely closed: a repo-wide sweep for a surviving `dispatched` key found only unrelated
  `manage-metrics` / `plan-retrospective` hits.
- Declared-wins suppression notes (`_cmd_client_query.py:1224-1230`) are keyed on producers of actual
  edges, so a `not_dispatched` record can never acquire a `declared:` note it did not earn.
- Disabled reports are merged and re-sorted by id (`:1122`), so report order is configuration-independent.
- The `resolver_count == len(resolvers)` invariant is gone from every normative surface: the only
  remaining `len(resolvers)` occurrences in `marketplace/` are the two roster `count` fields
  (`extension_api.py:176`, `run_config.py:928`), which count roster entries and are correct.

## Test adequacy

| Deliverable | Covering tests |
|---|---|
| D1 (menu round-trip) | `test_derivation_resolver_roster.py:160,175` (round-trip through the roster and through the file), plus 12 further roster tests including three fail-open paths |
| D2 (keyed section) | `test_run_config_derivation_resolver.py` — 22 tests, incl. `:122` (persists beside `language_servers`), `:139` (`configured` vs `enabled`), `:191-211` (flag-pair validation and no-write-on-reject) |
| D3 (working default) | `test_derivation_resolver_configuration.py:142` (the D3 guard), `:176` (writing the section is not an allow-list), `:483,498` (fail-open) |
| Gate behaviour | `test_derivation_resolver_configuration.py` — 19 tests: dispatch gating, `resolver_count`, `capabilities`, report shape, uniform TOON wire, rendered footer |
| ABC method | `test_extension_base_derivation_resolver.py:110,128,131` (default `[]`, override accepted, third-party default pinned) |
| Cross-stage | `test_graph_family_bundle_project.py:335-361` — roster names every discovered resolver; count checked against the dispatched population, not the roster's cardinality |

Re-derived counts: the three new test files hold **14 + 22 + 19 = 55** tests (`--collect-only`), all
green. The commit changed **20** `.py` files — **14** production, **6** test — matching the report.

**Mutation evidence (two, both proving non-vacuity):**

1. `DERIVATION_RESOLVER_ENABLED_DEFAULT: True → False` → `test_unconfigured_project_still_derives_edges`
   and 7 siblings go red (8 failed / 11 passed). The D3 guard cannot pass against the defect it names.
2. Deleted the per-entry `try/except` in `cmd_derivation_resolver_list` (`run_config.py:919-924`) →
   `test_list_survives_a_raising_entry_read` goes red (1 failed / 21 passed). The R3-7 guard-plus-test
   pair is real, not decorative.

Both mutations were restored from `$TMPDIR/verify-220-mutsweep/run_config.py.orig`; `cmp` reports the
file byte-identical to the snapshot and `git status --porcelain` shows no modification under
`marketplace/`.

**One coverage hole:** no test combines "every resolver disabled" with "a module carrying declared
`internal_dependencies`". Every disabled-path fixture (`_seed_triple`,
`test_derivation_resolver_configuration.py:74-99`) builds modules with no declared edges, which is
exactly why the G1 defect passed four verification rounds.

## Report accuracy

Re-derived, and **true of the tree now**: the 47/45/1 tracked `.claude` path enumeration; the
`.gitignore` before/after claim; `.plan/run-configuration.json` being git-ignored; the seven shipped
resolvers each implementing `derivation_file_patterns()` (7 `DerivationResolverBase` subclasses, 7
implementations); `count_dispatched` backing `resolver_count` at all four assignment sites; the pre-change
Page 4 shape; the 14-production/6-test Python split; the F3 five-site sweep (no "two Axis-C methods"
survives); the R2/R3/R4 documentation fixes at every site named; the ADR-014 amendment being scoped to
"surfaces with a dispatch control" with Axis-D explicitly exempted; and the § Step 6 contract
amendment having landed in `.claude/skills/cloud-plan-lane/SKILL.md:725-729`.

Inaccuracies found:

- **The round-1 finding count does not match its own table.** The report states *"the row counts below
  are the tables' own"* and then *"| 1 | 13 | 10 from the sub-agent, 3 self-caught |"*. The round-1
  table has **14** rows (F1, F2, F2b, F3–F10 = 11 rows attributed to the R1 sub-agent, plus S1, S2, S3).
  Rounds 2, 3 and 4 count every suffixed row (R2-S1, R3-R are counted), so counting F2b as a non-row is
  inconsistent with the report's own convention — the exact arithmetic-vs-table defect R4-7 claims to
  have eliminated. See G5.
- **R3-4's stated rationale is false about the test harness.** The row says the assertion was *"green
  only because a fresh clone and CI have no store"* and that *"a developer who disables one resolver
  through the new menu turns it red"*. `test/conftest.py:1146-1200` installs an **autouse**
  `_plan_base_dir_sandbox` fixture that redirects `PLAN_BASE_DIR` (and `_config_core.RUN_CONFIG_PATH`)
  into a per-test tmp sandbox for every test not marked `allow_pollution`; neither
  `test_graph_family_bundle_project.py` nor `test_graph_resolver_provenance.py` carries that marker.
  Proved: I ran `test_graph_resolver_provenance.py` and `test_native_resolver_graph_impact.py` with
  `PLAN_BASE_DIR` pointed at a store disabling `maven` and `python` — **49 passed**, because the
  autouse fixture overrode my env. The fix R3-4 applied is still an improvement (the assertion now
  names the right quantity); its justification is not. See G6.
- **Residue 3 does not reproduce.** The report describes a pre-existing 38-failure cross-directory
  pytest pollution mode. Two multi-directory ad-hoc invocations here were clean:
  `manage-architecture + extension-api` → **900 passed**; `manage-architecture + extension-api +
  pm-plugin-development/plan-marshall-plugin + pm-dev-python` → **1078 passed**. A third combination
  (`manage-architecture + script-shared + pm-documents + pm-code-intelligence`) gave **1804 passed, 1
  failed**, and the single failure is unrelated to this plan
  (`test_argparse_surface.py::TestLiveTreeCharacterization::test_every_registered_notation_is_confident_or_explicitly_not_derivable`,
  which names `plan-marshall:manage-metrics:manage-metrics` and fails identically when that file is run
  alone — 1 failed / 47 passed). Status of residue 3 is therefore **unconfirmed**, not disproved. See G7.
- Minor, not filed as gaps: the report's line-number citations (`run_config.py:710-802`,
  `architecture-persistence.md:606`, `client-api.md:99/101/105`) describe the tree at the time of the
  finding; the content is present at ±1–2 lines today. The build-gate figures (five `./pw verify` runs,
  20103 passed / 14 skipped) are **UNVERIFIABLE** here — the brief excludes running the full suite —
  and nothing I ran contradicts them.

## Declared residue — current status

| Residue item (from report) | Still open? | Evidence |
|---|---|---|
| 1. Configuration menu Page 4 is full; next entry needs a Page 5 | **Open** | `menu-configuration.md:89-108` — Page 4 holds "Derivation Resolvers", "Merge Queue", "Full Reconfigure", "Back" = the 4-element cap. No sibling plan has landed a language-server menu entry (`010-lsp-in-execute-lookup-and-write`, `240-skill-lsp-server` reports mention no menu surface; no `menu-language-servers.md` exists) |
| 2. `run-config-standard.md` "Full Example" is drifted | **Open** | `:807-859` — the block carries `commands`, `maven`, `architecture_refresh`, `ci_durations` only; the document's own `## ` sections include Language-Servers (`:208`), Derivation-Resolvers (`:267`) and Display-Timezone (`:377`), none of which appear in the "Full" example. See G4 |
| 3. Pre-existing cross-directory pytest pollution (38 failures) | **Unconfirmed** | Not reproduced in three multi-directory invocations (900, 1078, 1804 tests, one unrelated failure). See G7 |
| 4. `HARVEST_LANGUAGE` is Python-only, so `lsp` declares `['**/*.py']` | **Open, accurate** | `lsp_harvest.py:86` `HARVEST_LANGUAGE = 'python'`; `pm-code-intelligence/.../extension.py:104` returns `['**/*.py']` with the coupling stated in its docstring |
| F5/F8 dispositions (accepted / rejected as pre-existing) | Consistent with residue 1 and 2 above | — |

## Out-of-scope and collateral

- **"Writing new resolvers" (excluded) — respected.** The seven `DerivationResolverBase` subclasses in
  the tree are the seven that existed before; the commit adds only a `derivation_file_patterns()`
  method to each (`git show --stat c0b4f3e` shows +8 to +15 lines per resolver file, all method +
  docstring + hook-table rows).
- **"A project-shared resolver binding" (excluded) — respected.** The only store is the git-ignored,
  main-anchored `run-configuration.json`; no version-controlled file gained a resolver binding.
- **"Touching the live ignore-file negations" (excluded absolutely) — respected**, re-verified above.
- **Surface deviation, declared:** the plan's Expected surface put the seam read in
  `extension-api/` (**HYPOTHESIS**). The gate actually landed in
  `manage-architecture/scripts/_cmd_client_query.py`, and `manage-architecture` standards
  (`client-api.md`, `architecture-persistence.md`) plus `doc/adr/014-*.adoc`,
  `doc/concepts/code-intelligence.adoc` and `doc/user/dependency-intelligence.adoc` were edited. All
  are named in the report's deliverable table and its Step 8 Bridge row, and all are downstream
  consumers of the contract this plan changed — collateral, but declared, not silent.

## Method and coverage

- Read `plan.md` and `report-01.md` in full, then the shipped implementation end to end: `run_config.py`
  §Derivation-Resolvers, `extension_api.py`, `_cmd_client_query.py` §gate/§`_derive_edges`,
  `_cmd_client_handlers.py` §`cmd_capabilities` and the three traversal verbs, `_cmd_client_render.py`
  §provenance footer, `extension_base.py` §`DerivationResolverBase`, all seven resolver
  implementations, the menu documents, and every documentation surface D5 names.
- Ran, on this tree: the three new test files (55 tests, all green); two production mutations with
  byte-snapshot restore; four multi-directory pytest invocations (900 / 1078 / 1804 / 49 tests) to probe
  residue 3 and the machine-local-store hazard; and a standalone probe script driving the real
  `get_module_graph` / `cmd_capabilities` / `render_overview` against a temp `PLAN_BASE_DIR` store to
  reproduce the G1 defect.
- Re-derived every count stated here at the moment of stating it (`git ls-files`, `git check-ignore -v`,
  `--collect-only`, `git show --name-only`). Negative greps were confirmed against a known positive
  before being believed (e.g. the `dispatched`-key sweep returns hits in `manage-metrics`, so the empty
  result for the derivation surface is a real absence).
- **Not checked:** the report's `./pw verify` figures (full-suite run excluded by the brief); the
  behaviour of the menu as executed by an agent (a markdown workflow has no automated harness);
  reviewer-participation claims for PR #1252/#1253 beyond confirming both merge commits and the landed
  contract amendment exist.
- **Not attributed to this plan:** the single unrelated failure in
  `test/plan-marshall/script-shared/test_argparse_surface.py` (live-tree characterization over
  `plan-marshall:manage-metrics:manage-metrics`), which fails in isolation on this checkout and touches
  no surface this plan changed.
