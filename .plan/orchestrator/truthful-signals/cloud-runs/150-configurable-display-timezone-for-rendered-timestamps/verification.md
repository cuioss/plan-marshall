# Verification — 150-configurable-display-timezone-for-rendered-timestamps

**Verified against:** commit `ac06e4fc94782328f87d1395472a72b7e7a8559d`   **Landed as:** PR #1172, commit `72338ad33fdf9778dbd2a559754188391d698c45`   **Verdict:** implemented-with-gaps

## Method

What was actually done, in order:

1. Read `plan.md` and `report-01.md` in full.
2. Located the landed commit (`git log --oneline --all --grep '#1172'` → `72338ad3`, squash-merge, present on `main`) and read its full diff (`git show --stat`, then per-file diffs for `run_config.py`, `_display_time.py`, `manage-metrics.py`, `compile-report.py`, `report-structure.md`).
3. Checked whether any landed file was later superseded (`git log --oneline 72338ad3..HEAD -- <each of the 13 touched paths>`). `run_config.py`, `SKILL.md`, `run-config-standard.md`, `manage-metrics.py`, `compile-report.py` and `report-structure.md` were touched by later PRs (#1252, #1256, #1243, #1193, #1293, #1287, #1260, #1224, #1255, #1180, #1173, #9135f275); in every case this plan's lines survive unchanged at HEAD (re-read each site at HEAD).
4. Opened at HEAD: `_display_time.py` (whole file), `run_config.py:58` / `:960-1040` / `:1390-1420`, `manage-metrics.py:41,1631`, `compile-report.py:30,488`, `run-config-standard.md` §§ structure/Display-Timezone, `manage-run-config/SKILL.md:270`, `plan-retrospective/references/report-structure.md:49`, and all three new test files plus `timestamp_render_classification.json`.
5. Ran the plan's own tests: `UV_HTTP_TIMEOUT=600 uv run python -m pytest test/plan-marshall/manage-run-config/test_display_timezone_guard.py test_display_time_render.py test_display_timezone_knob.py -o addopts="" -q` → **25 passed** (9 knob + 13 render + 3 guard, matching the report's "25 new tests").
6. **Executed** `render_timestamp` on real inputs (`uv run python -c ...` with every bundle `scripts/` dir on `sys.path`) for `UTC`, `Asia/Kolkata`, `America/New_York`, `Europe/Berlin`, `Pacific/Chatham`, `Australia/Lord_Howe`, `Etc/GMT+5`, `America/Sao_Paulo`, and the unloadable `Not/AZone`. Results below.
7. **Three mutations**, each applied to a byte-for-byte copy saved first and restored from that copy (never `git checkout`/`restore`/`stash`):
   - `_display_time.py`: replaced the conversion return with `local.strftime(body_fmt) + utc_suffix` (drop the label) → `test_display_time_render.py` went **3 failed, 10 passed**. Restored; `md5sum` matched the pre-mutation digest.
   - `_status_core.py` (a derived STORE/COMPARE file): appended a comment naming `read_display_timezone` → `test_knob_symbols_never_reach_a_store_or_compare_site` went **RED**, naming the file and both symbols. Restored.
   - `file_ops.py::now_utc_iso`: converted the stored timestamp to `Asia/Kolkata` before formatting (the exact defect D5(c) names) → `test_stored_timestamp_is_utc_under_any_knob_value` **still PASSED**. Restored. This is finding G1.
8. Re-derived every census figure at HEAD and at the landed commit with `git grep -lE '<scan_regex>'` / `grep -rlE`, and cross-derived the `now_utc_iso()` population that the scan regex does not match.
9. Swept the tree for stale restatements: `grep -rniE "iso-8601 utc|utc timestamp"` over `marketplace/bundles` + `doc` (`*.md`, `*.adoc`); `grep -rn "display_timezone"` repo-wide; `grep -rn "Generated:"` over bundles; checked `marshall-steward/references/menu-configuration.md` for a knob catalogue; checked `manage-metrics/SKILL.md` § "Generated metrics.md" and `standards/data-format.md` § "Generated Report (metrics.md)".
10. Confirmed the cross-skill import is real at runtime: `collect_script_dirs` (`script-shared/scripts/marketplace_bundles.py:152`) puts *every* skill `scripts/` dir on the executor PYTHONPATH, so `from _display_time import render_timestamp` inside `manage-metrics.py` / `compile-report.py` resolves. Precedent for an underscore-prefixed cross-skill module already exists (`manage-metrics` imports `_plan_parsing` from `manage-solution-outline`).
11. `git status --porcelain` at finish shows nothing under `marketplace/`, `test/` or this plan's tree except the two files written here (other untracked `doc/plans/*/verification.md` files and two modified bundle scripts belong to concurrently-running sibling sessions in the same checkout, not to this verification).

## Deliverable-by-deliverable

| # | Deliverable | Done-when condition | Implemented? | As documented? | Correct? | Complete? | Evidence (file:line / symbol / command + result) |
|---|---|---|---|---|---|---|---|
| D1 | Derive & classify the rendering surfaces | Every site enumerated and classified RENDER vs STORE/COMPARE, population stated | yes | partly | yes | **no** | `test/plan-marshall/manage-run-config/timestamp_render_classification.json` — `render_files` (2), `knob_owner_files` (2), `scan_regex`, `store_compare_derivation`, `known_store_traps`. Population re-derived at HEAD: `grep -rlE '<scan_regex>' marketplace/bundles --include=*.py` → **35 files**. But `grep -rlE 'now_utc_iso' …` → 18 files, **12 of which the scan regex never matches** — see G2 |
| D2 | The `display_timezone` knob | Exists, validates an IANA name, defaults to `UTC` | yes | yes | yes | partly | `run_config.py:58` `DISPLAY_TIMEZONE_DEFAULT='UTC'`; `:960` `_is_valid_iana_timezone`; `:977` `read_display_timezone`; `:1011/:1020` `cmd_display_timezone_get/set`; `:1389-1412` argparse wiring, `:1475-1477` dispatch. `test_display_timezone_knob.py` — 9 tests, all pass. Absent from the steward configuration menu — see G3 |
| D3 | Every rendered timestamp carries its zone label | No rendering path can emit a converted timestamp without its label; the suite fails if one does | yes | yes | yes | yes | `_display_time.py:60-93` `render_timestamp`, `:36-57` `_zone_label`. Executed: `Asia/Kolkata` → `'2026-08-11 20:00:45 IST (UTC+05:30)'`; `Pacific/Chatham` → `'2026-08-12 03:15:45 +1245 (UTC+12:45)'`; `Etc/GMT+5` → `'2026-08-11 09:30:45 -05 (UTC-05:00)'`; `Not/AZone` → `'2026-08-11 14:30:45 UTC'` (fail-safe, unconverted, honest label). Mutation dropping the label → 3 tests RED |
| D4 | Guard that the knob cannot reach the write path | Guard exists, derived over D1's classification, publishes the population examined | yes | (granularity) no | yes | **partly** | `test_display_timezone_guard.py:74-153`. Census printed at HEAD: `scanned_time_files: 35`, `render_files: 2`, `knob_owner_files: 2`, `store_compare_files: 31`, plus the 31 filenames. Leak mutation in `_status_core.py` → RED; independently re-confirmed with a leak appended to `_ledger_core.py` (a file *outside* the scanned population) → RED, so the isolation scan does walk **all** bundle `*.py` and its coverage is not limited by G2. But the exemption is whole-file: a STORE write inside a declared RENDER file is invisible to it — mutation-confirmed at `manage-metrics.py:1945` (`totals_sampled_at` routed through `render_timestamp`) → guard **still green**. See G5 |
| D5 | Four tests, each seen red pre-fix | (a) unset byte-identical; (b) positive-offset converts + labels; (c) stored unchanged under any knob value; (d) render population derived, non-empty | yes | (c) no | **(c) vacuous** | yes | (a) `test_utc_render_is_byte_identical_to_legacy_{metrics,retro}_format` — pass, and equal the pre-knob `strftime` string. (b) `test_positive_offset_zone_converts_and_labels` — pass; RED under the label mutation. (c) `test_stored_timestamp_is_utc_under_any_knob_value` (`test_display_time_render.py:120-133`) — **passes against the very defect it names**; see G1. (d) `test_classification_covers_the_live_population_and_is_non_empty` — pass, asserts `scanned`, `render_files`, `store_compare` all non-empty |

### D1 — the derived population under-covers the tree

`timestamp_render_classification.json` states its `_population_source` as *"every timestamp call site in `marketplace/bundles/**/*.py`"*, derived by the regex `datetime\.now|utcnow|strftime|fromisoformat|astimezone|ZoneInfo|zoneinfo|\.timestamp\(\)|fromtimestamp`. That regex does not match `now_utc_iso()` — the codebase's most-used timestamp primitive (`tools-file-ops/scripts/file_ops.py:85`). Twelve bundle `.py` files produce timestamps *only* through it and therefore appear in neither the RENDER list nor the derived STORE/COMPARE remainder, at HEAD and at the landed commit alike: `manage-build-server/scripts/_marshalld_journal.py`, `manage-build-server/scripts/manage_build_server.py`, `manage-change-ledger/scripts/_ledger_core.py`, `manage-logging/scripts/plan_logging.py`, `manage-plan-documents/scripts/_documents_core.py`, `manage-status/scripts/_cmd_lifecycle.py`, `manage-status/scripts/_cmd_merge_authorization.py`, `manage-status/scripts/_status_query.py`, `manage-tasks/scripts/_tasks_core.py`, `plan-orchestrator/scripts/_orchestrator_inbox.py`, `plan-orchestrator/scripts/orchestrator.py`, `script-shared/scripts/build/_build_server_registry.py`.

I checked the two of those with the strongest human-facing character and both are defensibly STORE under the plan's own tie-break rule (*"a value that is both stored and rendered from the same site is STORE"*): `plan_logging.py:136` writes `[{timestamp}] [{level}] [{hash}] {message}` into the plan log and `plan_logging.py:685` parses that same header back; `_documents_core.py:88,98` writes `created:` / `{timestamp}` into a plan-document markdown that is persisted, not re-rendered. So **no missed RENDER site was found** — the defect is in the population claim and in the guard's published census, not (as far as I could establish) in the RENDER/STORE verdict.

Adversarial review sharpened what the omission costs: `plan.md` D1 names the surfaces to enumerate explicitly, and **three of the named surfaces fall entirely inside the twelve** — "decision and work log rendering" (`manage-logging/scripts/plan_logging.py`), "inbox listings" (`plan-orchestrator/scripts/_orchestrator_inbox.py`), and "operator-facing summaries" (`plan-orchestrator/scripts/orchestrator.py`). All three were checked by hand and are STORE under the plan's own tie-break rule (`_orchestrator_inbox.py` writes `created` at `:404` and `amended` at `:1502` as envelope header fields that `inbox-envelope.md:85` declares preserved across an amend), so the verdict is unchanged — but they were classified by absence rather than by derivation, which is what D1's Done-when forbids. G2 has been strengthened accordingly.

### D2 — settable, but not discoverable

The Done-when ("knob exists, validates an IANA name, defaults to `UTC`") is met in full and verified by test. The deliverable's wider sentence — *"settable through the ordinary configuration flow"* — is met only through the `run_config display-timezone get/set` CLI. `marshall-steward/references/menu-configuration.md` (a 12-option paginated configuration catalogue, Pages 1–4 at `:26/:47/:68/:89`) offers no display-timezone entry, while it does route to the other machine-local optional sections (`derivation_resolvers`, `language_servers`, `architecture_refresh`). The run declared this deferred, which `plan.md` § Notes permits — but see G3 for where that deferral lands.

`DISPLAY_TIMEZONE_DEFAULT` is also not seeded into `DEFAULT_STRUCTURE` (`run_config.py:60-66`, which seeds only `version`, `commands`, `maven`). Adversarial review established this is **not** a defect: every optional section in the standard's § "Optional Sections" is unseeded the same way, so the knob follows the convention rather than breaking it. The clause has been removed from G3 and recorded under § Refuted in `gaps.md`.

### D5(c) — the invariant test is vacuous

`plan.md` § Verification marks D5(c) with ⛔ as *the* invariant test. The test sets `display_timezone: 'Asia/Kolkata'`, asserts `read_display_timezone() == 'Asia/Kolkata'`, then asserts `now_utc_iso().endswith('Z')`. `Z` is a **literal character in the format string** at `file_ops.py:91` (`strftime('%Y-%m-%dT%H:%M:%SZ')`), so the suffix survives any zone conversion. Mutation-confirmed: converting the stored moment to `Asia/Kolkata` before formatting leaves the test green. See G1.

## Report accuracy

Every figure in `report-01.md` was re-derived. Findings:

- **"33 time-bearing files — 2 RENDER, 2 owner, 29 STORE/COMPARE"** — **accurate at the landed commit.** `git grep -lE '<scan_regex>' 72338ad3 -- 'marketplace/bundles/*.py' | wc -l` → **33**, and 33 − 2 − 2 = 29. At HEAD the same derivation gives 35 → 2/2/**31** (the guard prints exactly that), i.e. ordinary tree drift since the merge, not a report error.
- **"55 real call sites (plus 2 docstring/comment mentions that are not call sites)"** — re-derives as **56 + 2** against the merge parent `72338ad3^` (58 matching lines; the two non-call-site lines are `manage-lessons/scripts/_lessons_retention.py:10` and `workflow-integration-github/scripts/github_re_review.py:126`). A one-site divergence, fully explainable by main having moved between the branch point and the merge parent. Recorded, not treated as a contradiction.
- **"`test_display_timezone_knob.py` (9 tests)"** — accurate (counted 9).
- **"After restore: 25 passed"** — accurate; re-running the three files at HEAD gives **25 passed**.
- **"8 display-timezone CLI tests failed … the one green pre-fix — `test_validate_accepts_config_with_display_timezone`"** — arithmetically consistent (9 − 1 = 8) and the named test is indeed schema-agnostic (`validate` ignores unknown top-level keys; confirmed by reading `validate_run_config` and by the test passing against a config carrying the field).
- **"The default/unset path resolves `UTC` without constructing a `ZoneInfo`"** — **confirmed** by reading both early-return branches (`run_config.py:996-997`, `_display_time.py:82-84`).
- **F1: "every OTHER 'ISO-8601 UTC' doc claim it swept describes STORE fields"** — **verdict confirmed, count corrected.** Re-running the stated sweep (`grep -rniE "iso-8601 utc|utc timestamp"` over `marketplace/bundles` + `doc`, `*.md`/`*.adoc`, excluding `doc/plans/`) returns **five** survivors, not four: `manage-findings/standards/jsonl-format.md:239` (`ts`), `manage-execution-manifest/standards/decision-rules.md:104` (`timestamp`), **`workflow-integration-sonar/SKILL.md:197` (`ts`)** — omitted from the original count — `plan-orchestrator/standards/inbox-envelope.md:88` (`amended`), and `manage-logging/standards/log-format.md:17` (`timestamp`). All five are STORE fields; the added one is written at `workflow-integration-sonar/scripts/sonar.py:348` as `datetime.now(UTC).isoformat()` into a structured envelope and is not routed through `render_timestamp`. The F1 fix itself is present and intact at HEAD (`plan-retrospective/references/report-structure.md:49`) despite three later PRs touching that file.
- **A broader sweep than F1's** (`iso-8601 utc|utc timestamp|in utc|utc time|always utc|zulu|z suffix|utc iso|iso 8601|iso-8601`) surfaced one further candidate the narrow pattern missed: `ref-workflow-architecture/standards/manage-contract.md:105-117`, a canonical Timestamp Format section declared "used across all manage-\* skills". Read at the file, it scopes itself to values "Generated via `now_utc_iso()` from `file_ops`", which excludes both RENDER sites — accurate, not stale. Recorded under § Refuted in `gaps.md`.
- **F4: "both live call sites pass no `tz`"** — **confirmed** (`manage-metrics.py:1631`, `compile-report.py:488`).
- **"`marshall-steward` carries no knob catalogue that now omits `display_timezone`"** — **partially contradicted.** `marshall-steward/references/menu-configuration.md` is an explicit 12-option catalogue of configuration surfaces and contains no display-timezone entry. It is a catalogue of *areas*, not of run-config *fields*, so the claim is defensible on a narrow reading; it is not defensible as "nothing is stale" for an operator who configures through the steward. See G3.
- **"D1 … found no beyond-grep verbatim ISO echoes into human text (inbox, status, logging, terminal title, resume summary … all checked)"** — imprecise. `plan_logging.py:136` *does* echo an ISO timestamp verbatim into human-readable log text; it is correctly out of scope as STORE (round-tripped at `:685`), but "no echoes exist" overstates it. `manage-terminal-title/scripts/manage_terminal_title.py:137` is confirmed COMPARE-only (`title_token_state` parses `set_at` solely for a staleness delta and renders no timestamp) — that half of the claim holds.
- **CI/build figures** (`15997 passed, 1 skipped`; mypy over 393 files; all required checks green; reviewer rate-limit statuses) — not re-derivable from the tree; see § What could NOT be verified.

## Out-of-scope compliance

Clean. The landed diff is 13 paths: this plan's own `plan.md` (rename into place) and `report-01.md`; `manage-run-config` (`SKILL.md`, `scripts/_display_time.py`, `scripts/run_config.py`, `standards/run-config-standard.md`); the two RENDER sites (`manage-metrics/scripts/manage-metrics.py` — one line; `plan-retrospective/scripts/compile-report.py` — one line) plus the F1 doc fix in `plan-retrospective/references/report-structure.md`; and four files under `test/plan-marshall/manage-run-config/`. Every one sits inside the declared Expected surface (run-config, plus "the render sites D1 derives", plus tests).

- **"Any change to stored or compared timestamps"** — none. No write or compare path was touched; `now_utc_iso()` and every `datetime.now(UTC)` store site are byte-identical to before.
- **"Converting historical artifacts"** — none; no archive-touching code in the diff.
- **"A per-surface timezone"** — not violated. `render_timestamp(*, tz=None)` exposes a per-call override but both live call sites omit it (verified at `manage-metrics.py:1631` and `compile-report.py:488`), so one global setting governs both surfaces.
- No collateral change: `marshall-steward/**` — named in Expected surface — was deliberately not touched, and the run said so.

## Residue carried forward

| Residue declared in report-01.md | Status in today's tree |
|---|---|
| `coderabbitai` / `sourcery-ai` rate-limited; optional re-review | Closed by time — PR #1172 is merged into `main` (`git branch --contains 72338ad3` → `main`). Not actionable. |
| "Broader knob-catalogue / steward-flow surfacing of `display_timezone` is deferred to the sibling knob-cataloguing plan in this epic" | **Still open, and mis-routed.** The sibling is `doc/plans/truthful-signals/090-surface-every-knob-in-marshal-json`, whose scope is `.plan/marshal.json` (`DEFAULT_ORCHESTRATOR`, `effort`, `parallelization_scope`) — a different config file. It cannot surface `display_timezone`, which lives in `run-configuration.json` (`grep` for `run-configuration`/`run_config`/`display_timezone` in 090's `plan.md` → no match). The steward configuration menu has no entry for it, while it does route to the three comparable optional sections. See G3. |

## What could NOT be verified

- **The run's own red-first procedure.** The report's `git stash push -u` → red → restore evidence cannot be reconstructed from the tree. I substituted three independent mutations (§ Method step 7), which confirm D3/D5(b) and D4 are non-vacuous and expose D5(c) as vacuous; D5(a) and D5(d) were not mutation-tested.
- **Build and CI figures**: `./pw verify plan-marshall` → 15997 passed / 1 skipped, `./pw quality-gate` → `total_issues: 0`, mypy over 393 files, 36 plugin-doctor rules at 0 findings. Not re-run here (full-verify cost); the tests this plan added do pass at HEAD.
- **PR-side facts**: check-run statuses, `mergeable_state: clean`, the `cuioss-review-bot` review body, and the two rate-limit messages. Only the merge itself is observable from the clone.
- **Whether the metrics/retrospective renderers behave correctly end-to-end under a non-UTC knob in a live `.plan/` project.** `render_timestamp` was executed directly and the two call sites were read, but no full `manage-metrics generate` / `plan-retrospective` run was performed (`.plan/` state is absent from this clone).
- **Whether any RENDER site exists outside `marketplace/bundles/**/*.py`** (e.g. non-Python renderers or generated target output). The plan scoped D1 to that population and I did not extend the sweep beyond it.

## Adversarial review

**Reviewed by:** an independent agent that did not write this document.

**Checked**, and by what means:

- **Every `high` gap.** G1 re-tested by re-applying the `now_utc_iso` → `astimezone(ZoneInfo('Asia/Kolkata'))`
  mutation from a byte-copy saved first (`git diff --quiet` clean beforehand; `md5sum` matched on restore;
  never `git checkout`/`restore`/`stash`). Beyond the original single-test run, the plan's **entire** suite
  was run under the mutation: **25 passed**. G1 upheld.
- **Every clean-pass row.** D3 re-tested by re-applying the label-dropping mutation to
  `_display_time.py:93` → **3 failed, 10 passed** (the exact three the original names), restored by md5.
  D4 re-tested twice: a positive control (appending a `read_display_timezone` mention to
  `manage-change-ledger/scripts/_ledger_core.py`, a file *outside* the scan-regex population) → guard
  **RED**, naming file and symbols, which confirms by execution the document's mechanism claim that the
  isolation scan walks all bundle `*.py`; and a negative control (routing `totals_sampled_at` at
  `manage-metrics.py:1945` through `render_timestamp`) → guard **green**, which is new gap G5.
- **`render_timestamp` executed**, not read, on all nine zones this document reports
  (`UTC`, `Asia/Kolkata`, `America/New_York`, `Europe/Berlin`, `Pacific/Chatham`, `Australia/Lord_Howe`,
  `Etc/GMT+5`, `America/Sao_Paulo`, `Not/AZone`) with every bundle `scripts/` dir on `sys.path`. Every
  reported string reproduced byte-for-byte.
- **Every re-derivable figure.** `25 passed` (re-run); `9 / 13 / 3` tests per file (`grep -c '^def test_'`);
  census at HEAD `35 / 2 / 2 / 31` (guard's own `-s` output); `33` at the landed commit
  (`git grep -lE '<scan_regex>' 72338ad3 -- 'marketplace/bundles/*.py' | wc -l`); `58` matching lines at
  `72338ad3^` = `56 + 2`, with both non-call-site lines identified at `_lessons_retention.py:10` and
  `github_re_review.py:126`; the 13-path landed diff (`git show --name-only 72338ad3`); the 12-file
  `now_utc_iso`-only remainder (`comm -23`), reproduced exactly.
- **Every "swept, clean" claim**, re-run with a broader pattern than the original
  (`iso-8601 utc|utc timestamp|in utc|utc time|always utc|zulu|z suffix|utc iso|iso 8601|iso-8601` over
  `marketplace/bundles` + `doc`). This corrected the survivor count from four to five and surfaced one
  further candidate, adjudicated and refuted in `gaps.md` § Refuted.
- **Every mechanism clause** asserting behaviour elsewhere: `now_utc_iso` at `file_ops.py:85/:91`;
  `format_timestamp` = `now_utc_iso()` at `plan_logging.py:86-88`; the log header round-trip at
  `plan_logging.py:132/136` → `:680-686`; `manage_terminal_title.py:137` COMPARE-only;
  `collect_script_dirs` at `marketplace_bundles.py:152` and the `_plan_parsing` cross-skill precedent at
  `manage-metrics.py:50`; `DEFAULT_STRUCTURE` at `run_config.py:60-66`; the steward menu pages and
  Routing table; plan 090's scope (grepped, no `run-configuration.json` mention); the pre-plan render-site
  lines (`git show 72338ad3 -- <the two files>`, confirming UTC output is byte-identical).

**Not re-checked** (unchanged from § What could NOT be verified, and inherited as-is): the run's own
`git stash` red-first procedure; the CI/build figures (`15997 passed`, `total_issues: 0`, mypy over 393
files, 36 plugin-doctor rules); all PR-side facts; end-to-end behaviour of `manage-metrics generate` /
`plan-retrospective` under a non-UTC knob in a live `.plan/` project; and whether any RENDER site exists
outside `marketplace/bundles/**/*.py`. Additionally not mutation-tested: D5(a) and D5(d).

| Item | Original claim | Verdict | Evidence |
|---|---|---|---|
| G1 | D5(c) is vacuous; `Z` is a format literal | **upheld** at `high` | Mutation re-applied independently → `1 passed`; whole plan suite under the mutation → `25 passed`. `file_ops.py:91` confirmed to carry `Z` inside `strftime`. Rubric fit: a guard that passes against the defect it names |
| G2 | Scan regex misses `now_utc_iso`; 12 files outside the population | **upheld** at `medium`, evidence strengthened | 35 / 18 / 12 re-derived exactly by `comm -23`. Newly established: three of the surfaces `plan.md` D1 names by hand (work-log rendering, inbox listings, operator-facing summaries) are among the 12. Not raised to `high`: no wrong behaviour, and the isolation assertion was proven unaffected by the `_ledger_core.py` positive control |
| G3 | Deferred surfacing mis-routed to plan 090; knob undiscoverable | **rewritten**, severity held at `medium` | 090's `plan.md` has no `run-configuration.json` mention — upheld. But the `DEFAULT_STRUCTURE` half was **refuted**: all five optional sections are unseeded, so `display_timezone` follows the convention. Rewritten to rest on the steward asymmetry (steward routes to `derivation_resolvers`/`language_servers`/`architecture_refresh`, not to `display_timezone`); Fix and Done-when made observable against `menu-configuration.md` |
| G4 | metrics.md `Generated:` line undocumented | **upheld** at `low` | `SKILL.md:669` and `data-format.md:687` confirmed at those exact lines; `grep "Generated:"` over all bundle `*.md` returns zero hits, so the asymmetry with `report-structure.md:49` is real. No statement is false, so `low` is correct |
| G5 | *(new)* Guard whitelists whole RENDER files; F3's stated mitigation does not exist | **added** at `high` | `manage-metrics.py:1945` mutation → guard **green**. Nine STORE writes enumerated inside that whitelisted file, plus the filename stamp at `compile-report.py:66`. `grep -ni "granular\|file-level\|whole file\|whitelist\|per-file"` over the classification artifact and the guard → **zero matches**, refuting report-01 F3's "documented in the classification artifact" |
| D4 row | Implemented / documented / correct / complete = all `yes` | **re-scored** | Now `Complete: partly`, `As documented: no` on granularity, citing G5 |
| F1 survivor count | "The four survivors are …" | **corrected** | The stated sweep returns five; `workflow-integration-sonar/SKILL.md:197` was omitted. Verdict (all STORE) unchanged — `sonar.py:348` writes it as a structured `.isoformat()` field |
| Verdict | `implemented-with-gaps` | **upheld** | All five deliverables are implemented and land in the tree; none is absent. The defects are vacuity (D5c), coverage (D1/D4) and surfacing (D2) — gaps in implemented work, not an unimplemented deliverable. `partially-implemented` would be wrong |

**Documents corrected:**

- `gaps.md` — G5 added (`high`, guard blind spot, mutation-proven). G3 rewritten: the
  `DEFAULT_STRUCTURE` clause removed and moved to a new § "Refuted during adversarial review", Where /
  Fix / Done-when re-pointed at `menu-configuration.md` with observable `grep` conditions. G2's Why-it-
  matters extended with the three plan-named surfaces and the executed positive control; Fix given
  concrete census arithmetic (35 → 47 scanned, 31 → 43 STORE/COMPARE) and per-file classification
  instructions. G1's mutation evidence extended to the whole-suite run; `manage-lessons.py:148-150` →
  `:148-151`. `file_ops.py:84` → `:85`. **Open items: 4 → 5.**
- `verification.md` — D4 row re-scored with the mutation evidence; D2 narrative corrected to drop the
  `DEFAULT_STRUCTURE` defect claim and fix `run_config.py:60-84` → `:60-66` (both occurrences);
  argparse range `:1393-1412` → `:1389-1412`; `file_ops.py:84` → `:85`; guard line range `:73-160` →
  `:74-153`; the F1 survivor count corrected from four to five with the omitted entry named; a broader-
  sweep paragraph added; the D1 narrative extended with the three plan-named surfaces; this section
  appended. Verdict unchanged.

**Residual doubt** — what a third reviewer should look at first:

1. **Whether "exactly two RENDER sites" is the right answer to the operator's actual complaint.** The
   plan's tie-break rule (*"both stored and rendered from the same site is STORE"*) was applied
   consistently, and every classification checked here holds under it — but it disqualifies almost every
   timestamp a human actually reads: the plan log header, plan-document `created:` lines, inbox listings.
   The operator who asked for this knob still reads those in UTC. That is a question about the rule, not
   about this implementation, and it belongs to whoever writes the follow-up.
2. **G5's fix shape.** The site-granular `render_call_budget` proposed there is one design; a reviewer
   may prefer AST-level checking, or may judge the honest-artifact fallback sufficient. The *defect* is
   mutation-proven; the *remedy* is a judgement call.
3. **RENDER sites outside `marketplace/bundles/**/*.py`.** Still unswept by anyone — non-Python
   renderers, markdown templates with `{timestamp}` placeholders, and the multi-target generator output
   under `marketplace/targets/`.
4. **Concurrency.** Three bundle scripts were transiently modified in the working tree by concurrent
   sibling sessions mid-review (`manage-status/scripts/_cmd_planning_lane.py`,
   `plan-marshall/scripts/_invariants.py`, `plan-orchestrator/scripts/_orchestrator_inbox.py`); none is a
   file this review mutated. At finish, `git status --porcelain -- marketplace/ test/` is **empty** and
   all four of this review's mutations are md5-verified restored to their pre-mutation digests. A third
   reviewer re-deriving counts should still confirm the tree is clean before starting.
