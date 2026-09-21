# PLAN-23: marker-detector-ownership-and-fixture

epic: plan-optimization
workstream: WS-10

> Staged plan spec. Operator-surfaced 2026-07-20 with a full structural analysis; **every technical claim
> orchestrator-VERIFIED against source before staging** (see Verified Evidence). Re-ground line citations
> at outline. Re-verified at `main` @ `138747e0d` (2026-07-22): the defect is still live —
> `_markers_search.py:23` still closes `)>*/` (missing the trailing `~~`), and `:154` still exits
> non-zero only on `ask_user_count > 0`. Citations `:23`/`:154` remain exact.

## Objective

`search-markers` is a **vacuous gate**: it has never matched a real marker, always reports
`total_markers: 0`, and always exits 0. Every workflow using it as a "no markers present" check has been
passing without checking anything. Fix the detector, and relocate it to the bundle that owns the format
it parses, so the next upstream format change fails a test instead of silently re-disabling the gate.

## Verified Evidence (orchestrator, 2026-07-20)

- **The regex cannot match.** `script-shared/scripts/build/_markers_search.py:23` —
  `MARKER_PATTERN = re.compile(r'/\*~~\(TODO:\s*(.+?)\)>\*/')`. The `~~` is present in the OPENING
  delimiter and **absent from the closing one**; real markers close `)~~>*/`. Confirmed empirically:
  the shipped pattern returns `None` against real marker text; adding `~~` matches and extracts the
  recipe name correctly.
- **The gate cannot fail.** `_markers_search.py:154` — `return 1 if result['data']['ask_user_count'] > 0
  else 0`. With zero matches, `ask_user_count` is always 0, so the command always exits 0.
- **⚠ The test suite PINS THE BUG.** `test/plan-marshall/script-shared/test_markers_search.py` has ~40
  passing tests, and **every one of them hand-writes the broken `)>*/` form** (e.g. `:35`, `:130`, `:147`
  asserts `raw_marker == '/*~~(TODO: MyRecipe refactor needed)>*/'`). The suite is self-consistent with
  the defect: it does not merely fail to catch it, it **cements** it. Fixing the regex will break ~30
  tests, and a naive fixer could "correct" the regex back. **This is the single most important fact in
  this plan** — it is why D2's fixture must be provenance-bearing, not hand-written.
- **Two consumers, not one.** `build-maven/scripts/maven.py:70` (`.java`) and
  `build-gradle/scripts/gradle.py:84` (`.java,.kt`) both wire `cmd_search_markers`.
- **Additional surface the report did not name:** `extension-api/standards/build-api-reference.md:37,245`
  declares `search-markers` as part of the **build API contract** ("Maven, Gradle only"). Relocating is
  therefore a **contract change to extension-api**, not just a file move. Also referenced at
  `extension-api/SKILL.md:62,239` and `script-shared/SKILL.md:18`.
- **cui-specific knowledge is already embedded:** `AUTO_SUPPRESS_RECIPES` (`:29-38`) hardcodes
  `CuiLogRecordPatternRecipe` and `InvalidExceptionUsageRecipe` — recipe knowledge owned by
  cuioss/cui-open-rewrite, living in a bundle with no ownership of it.
- Target bundle `pm-dev-java-cui` exists.

## Deliverables

### D1 — relocate marker scanning to `pm-dev-java-cui`

**Governing principle: ownership of the format, not choice of transport.** Parsing cui-rewrite marker
output requires knowing the cui marker format, so the component belongs beside the recipes and standards
that define it. `build-maven`'s remit is invoking Maven and parsing Maven output; marker scanning is not
a build-tool concern. Once relocated, `AUTO_SUPPRESS_RECIPES` sits beside the recipes it describes.
**Retire** the `search-markers` subcommand from build-maven AND build-gradle, and retire
`_markers_search.py` from script-shared. **build-gradle consumes the relocated component rather than
duplicating it.** **Amend the extension-api build-API contract** (`build-api-reference.md`) so
`search-markers` is no longer declared a build-tool verb — confirm at outline whether it is removed from
the table outright or re-pointed. **Acceptance:** no marker-scanning code remains in `script-shared`,
`build-maven`, or `build-gradle`; the java-cui component is the single implementation; both prior call
paths resolve to it; the extension-api contract reflects reality.

> **⚠ D1 activation-seam constraint + SURVEYED CORRECTION (operator + orchestrator survey, 2026-07-20).**
> A general **plugin loading-filter concept** is wanted — domain content should be in play ONLY when its
> domain is active; today the cui specifics sit in the CORE. That concept is staged as **PLAN-25**
> (design-first). **PLAN-23 does NOT block on it** — the gate is broken now.
>
> **CORRECTION — relocation ALONE does NOT achieve domain-gating. Do not claim that it does.** The
> survey established that **`generate_executor.py` is entirely domain-blind** (zero references to
> `domain`/`skill_domains`; it registers every script from every installed bundle unconditionally). So
> after D1, the detector is still exposed to every consumer — merely under a
> `pm-dev-java-cui:{skill}:{script}` notation instead of a core one. **What D1 legitimately achieves is
> OWNERSHIP INVERSION** (the format and `AUTO_SUPPRESS_RECIPES` live with the recipes that define them, so
> the next format change has an owner and a test), **not activation gating.** State it that way in the
> landing. Gating is PLAN-25's scope.
>
> **Precedent is established — the core DOES dispatch into domain bundles** (`ext-triage-{domain}` ×7,
> `arch-gate-{domain}`, `ext-self-review-plan-marshall`, `provides_outline_skill`), so a domain bundle
> owning this is normal, not novel. **But every one of those contributes a SKILL/markdown surface resolved
> by domain key — none contributes a SCRIPT the core invokes.** That is the genuinely unsolved case.
> **Recommended seam (existing, do NOT invent):** follow `ext-point-self-review-surfacing`'s shape —
> "invoke the first implementor whose script notation **resolves in the current executor**, with a
> zero-generator fallback when none resolves." It is a resolvability probe rather than true domain
> gating, but it is the established workaround and keeps PLAN-25's options open.
> **Name the seam actually used in the landing** so PLAN-25 generalizes from a real instance. If D1 finds
> itself *designing* a loading mechanism, STOP — that is PLAN-25's scope.

### D2 — fix the regex and pin the format with a PROVENANCE-BEARING fixture

Fix the closing delimiter (`)~~>*/`). **The fixture is the load-bearing part, not the regex fix** — and
it must be a **real marker captured from actual cui-rewrite output**, checked in as a test fixture with
its provenance recorded (which recipe, which version/run produced it). A hand-written fixture is exactly
what produced this defect: the existing ~40 tests were all hand-written from the same wrong assumption
and all pass. **Rewrite the existing test suite against the real format** (≈30 assertions change) — do
NOT preserve the `)>*/` literals; they encode the bug. **Acceptance:** a test asserts a match against the
checked-in real-marker fixture and FAILS if the pattern regresses; the suite contains no hand-written
marker literal that is not derived from the fixture; an upstream format change breaks a test rather than
silently disabling the gate.

### D3 — make the gate able to fail

Reconcile the exit-code contract so "markers present" is actually a failure signal. Today only
`ask_user_count > 0` exits non-zero, so a tree full of *auto-suppressible* markers still exits 0 — which,
even with the regex fixed, keeps the gate partly vacuous against the governing convention (**never commit
code with markers present** — a property of the tree). **Confirm the intended contract at outline**:
likely `total_markers > 0` exits non-zero, with auto-suppress remaining a *categorization* for the
caller rather than an exemption from the gate. **Acceptance:** a tree containing only auto-suppressible
markers exits non-zero; a clean tree exits 0; the documented contract matches the behavior.

## Out of scope / do NOT expand
- **Do NOT narrow build-maven to log-only.** Explicitly deferred pending cuioss/cui-open-rewrite#116 —
  see the epic Watch. Neither #116 outcome changes D1/D2/D3.
- **Do NOT remove tree scanning even if #116 lands.** It remains the cheap, build-independent check: log
  parsing requires a full build (~3 min observed) and cannot cover (a) checking a tree without building —
  a pre-commit hook or an unbuilt checkout, or (b) a build that fails before `rewrite:run` executes (e.g.
  a compile error), where no findings are logged but markers may be present.
- The `build-maven:maven run` success-over-BUILD-FAILURE defect — that is **PLAN-24**, a separate defect.

## Absorbs
- Operator-surfaced defect "search-markers is non-functional and sits in the wrong bundle" (2026-07-20),
  items 1 and 2 of the report → D1/D2, plus the orchestrator-found exit-code gap → D3.

## Expected Surface
- `pm-dev-java-cui` — new marker-scanning component + `AUTO_SUPPRESS_RECIPES` + standards
- `script-shared/scripts/build/_markers_search.py` (retire) + `_build_cli.py:334`
  (`add_search_markers_subparser`) + `script-shared/SKILL.md:18`
- `build-maven/scripts/maven.py:70` + SKILL.md; `build-gradle/scripts/gradle.py:84` + SKILL.md
- `extension-api/standards/build-api-reference.md:37,245` + `extension-api/SKILL.md:62,239` (contract)
- `test/plan-marshall/script-shared/test_markers_search.py` → relocate + rewrite against the fixture
- new: checked-in real-marker fixture with recorded provenance

## Dependencies and Sequencing
- Depends on: none.
- **Adjacent to PLAN-24** on `build-maven/scripts/maven.py` — different regions (D1 removes a subparser
  registration + import; PLAN-24 changes `run`'s status derivation), so a trivial rebase is expected, not
  a semantic conflict. Still startable in parallel; rebase whichever lands second.
- Surface-disjoint from PLAN-18/20/21/22.

## Size / split guard
3 deliverables — under the ~6 presumption. D1's relocation is the elastic one (two consumer bundles +
the extension-api contract + docs). If it balloons at outline, ship D2+D3 in place first (the gate starts
working immediately) and stage the relocation as a follow-up — but record it as an epic decision, and
note that doing so leaves the ownership root cause unaddressed.

## Hand-Off Command
```text
/plan-marshall task="implement .plan/local/orchestrator/plan-optimization/plans/PLAN-23-marker-detector-ownership-and-fixture.md"
```

## Status Trail
- plan_marshall_plan_id: {set at launch}
- pr: {set when the PR opens}
- landing: {set when landings/PLAN-23.md is recorded}
