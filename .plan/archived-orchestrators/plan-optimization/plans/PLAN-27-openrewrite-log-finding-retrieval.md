# PLAN-27: openrewrite-log-finding-retrieval

epic: plan-optimization
workstream: WS-10

> Staged plan spec. Surfaced 2026-07-21 when the epic's deferred dependency watch cleared:
> cuioss/cui-open-rewrite#116 landed as PR #118 (verified — commit `a0e21ac` on cui-open-rewrite
> `main`; archived plan `2026-07-20-issue-116` request+outline confirm scope). Re-ground the exact
> WARN-line format and call sites at outline.

## Objective

The OpenRewrite recipe set now emits every finding as a per-run WARN line in the build log — file
path, line, column, recipe name, and the marker/task message — including the previously-silent
**pre-existing-marker** case (a committed marker that produces no diff). This makes a **log-based**
finding-retrieval capability possible for the first time: answer *"what did this run find?"* from the
build log, as a **complement** to the tree-scanning marker detector (PLAN-23), which answers the
different question *"are markers present in the tree now?"*.

Build the log-based retriever beside the format it parses, and wire it into `build-maven`'s output
consumption **without** narrowing or removing tree scanning.

## Why now / dependency

- **Unblocked, not before:** until #118, the build log carried nothing (a pre-existing marker produced
  no `Changes have been made` line), so log parsing was impossible — this is the exact condition the
  epic's deferred watch tracked. It is now satisfied.
- **Complement, never replacement (verified, load-bearing):** log parsing requires a full build
  (~3 min observed) and structurally cannot cover (a) an **unbuilt tree** — a pre-commit hook or a
  fresh checkout, or (b) a build that **fails before `rewrite:run` executes** (e.g. a compile error),
  where no findings are logged but markers may be present. Tree scanning (PLAN-23) stays as the cheap,
  build-independent check. This plan ADDS a signal; it removes none.

## Deliverables

### D1 — log-line finding parser in `pm-dev-java-cui`, with a provenance-bearing fixture

Parse the #118 WARN finding format into structured findings (path, line, column, recipe, message,
and the newly-detected-vs-pre-existing distinction the recipes encode in their wording). By PLAN-23's
governing principle — **ownership of the format, not choice of transport** — this parser parses the
cui recipe output format, so it lives in `pm-dev-java-cui` **beside the relocated marker detector**,
not in `build-maven`. **Fixture discipline mirrors PLAN-23 D2:** the parser is pinned by a
**real WARN-line corpus captured from actual #118 build output**, checked in with recorded provenance
(which recipe, which cui-open-rewrite version/run produced it) — never hand-written, so an upstream
wording change breaks a test rather than silently disabling the parser. **Acceptance:** the parser
extracts all fields from the real fixture for each marker-producing recipe, distinguishes
newly-detected from pre-existing findings, and a regression test fails if the WARN format drifts.

### D2 — wire log-based retrieval into `build-maven` output consumption, additively

Surface the parsed findings from a `build-maven` run that reached `rewrite:run`, consuming the
relocated `pm-dev-java-cui` parser (do NOT duplicate it). This is a **build-output consumer**, the
part that legitimately belongs in `build-maven` (invoking Maven and parsing Maven output).
**Acceptance:** a Maven run whose log contains #118 WARN findings yields those findings structurally;
a run that never reached `rewrite:run` (compile failure) yields no findings AND does not report a
false "clean" — the absence is reported as *"not observed this run"*, not *"no markers present"*
(fail-closed, ADR-009 posture). **Tree scanning is untouched** — no code path is narrowed to log-only.

### D3 — document the two-signal model and its coverage boundaries

Document that finding detection now has two complementary signals: tree scan (*"markers present in
the tree now?"* — build-independent, covers unbuilt trees and pre-`rewrite:run` failures) and log
parse (*"what did this run find?"* — richer per-finding detail incl. pre-existing markers, but
requires a completed `rewrite:run`). Make the coverage gaps explicit so no future change collapses
one into the other. **Acceptance:** the two-signal model and its boundaries are documented where the
marker-detection standard lives (post-PLAN-23, in `pm-dev-java-cui`); the log-parse coverage caveats
(needs full build; misses pre-`rewrite:run` failures and unbuilt trees) are stated.

## Out of scope / do NOT expand
- **Do NOT narrow, remove, or replace tree scanning** (PLAN-23's detector). This plan ADDS the log
  signal alongside it — the whole point is two complementary signals. Any narrowing to log-only
  contradicts the verified coverage analysis and is a defect, not a simplification.
- **Do NOT re-do PLAN-23's relocation or fixture work.** D1 CONSUMES the ownership home PLAN-23
  establishes in `pm-dev-java-cui`; it does not move the detector or redo the marker fixture.
- The `rewrite-maven-plugin`'s own `Changes have been made to …` file-level report — owned upstream,
  out of scope here (as in the #116 plan itself).
- The `maven run` success-over-BUILD-FAILURE defect — that is **PLAN-24**.

## Absorbs
- The epic's DEFERRED WATCH "build-maven log-only blocked on cui-open-rewrite#116" → resolved; the
  actionable residue (the now-buildable log-parse complement) is this plan.

## Expected Surface
- `pm-dev-java-cui` — new log-line finding parser component + provenance-bearing WARN-line fixture +
  the two-signal standard (D1/D3); sits beside PLAN-23's relocated marker detector
- `build-maven/scripts/maven.py` — build-output consumer wiring for the parser (D2); the log-parse
  path only, additive to the existing marker/build handling
- possibly `extension-api` build-API contract if a new build-output verb is exposed — confirm at outline
- tests: parser-extracts-all-fields-from-real-fixture; new-vs-pre-existing-distinction;
  format-drift-fails-regression; maven-run-surfaces-log-findings; pre-rewrite-failure-not-reported-clean

## Dependencies and Sequencing
- **Depends on: PLAN-23.** PLAN-23 relocates format ownership (the marker detector + `AUTO_SUPPRESS_RECIPES`)
  to `pm-dev-java-cui`; D1 lands the log parser in that same home. Building the parser in `build-maven`
  before PLAN-23 establishes the `pm-dev-java-cui` ownership home would re-embed cui format knowledge in a
  bundle that does not own it — the exact anti-pattern PLAN-23 exists to fix. **Sequence AFTER PLAN-23.**
- **Adjacent to PLAN-24** on `build-maven/scripts/maven.py` — different region (PLAN-24 changes `run`'s
  status derivation; this adds a log-output consumer). Trivial rebase; sequence-agnostic vs PLAN-24.
- Surface-disjoint from PLAN-20/21/22.

## Size / split guard
3 deliverables — under the ~6 presumption. D1's fixture/parser is the load-bearing part (mirrors
PLAN-23 D2's discipline); D2 is the thin build-maven consumer; D3 is docs. No split anticipated.

## Hand-Off Command
```text
/plan-marshall task="implement .plan/local/orchestrator/plan-optimization/plans/PLAN-27-openrewrite-log-finding-retrieval.md"
```

## Status Trail
- plan_marshall_plan_id: {set at launch}
- pr: {set when the PR opens}
- landing: {set when landings/PLAN-27.md is recorded}
