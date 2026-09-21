# PLAN-87: No Extension Claims Any YAML Infrastructure Path, So Infra-Shaped Plans Classify As `unknown`

epic: truthful-signals
workstream: WS-01

> Staged plan spec — one shippable unit of work, ready for `/plan-marshall` hand-off.
> **Provenance: a cross-repo hand-off brief**, raised by API-Sheriff plan
> `plan-25-benchmark-suite-completion` (parked at phase 3-outline 2026-07-27) and relayed by the
> operator. Every claim below was **re-verified first-party against this repo's working tree** before
> being recorded — see `## Claim Labels` for what the verification changed.
> ⚠ **THEME EXCEPTION, recorded deliberately:** this is NOT the epic's `confident-signal-hides-a-caveat`
> archetype — the `unknown` bucket is an *honest* report of a real coverage gap. It lives in this epic
> because the epic tree is the orchestrator's only authoring surface and because it is a machinery-integrity
> defect; do not cite it as an instance of the flagship archetype.
> ⚠ **CAP EXCEPTION:** launched as a 6th concurrent plan against `parallelization_scope=5`, on explicit
> operator decision, to unblock a consumer repo. The cap remains 5 — this is a one-off, not a new normal.

## Objective

No registered plan-marshall extension claims **any** YAML infrastructure path. Plans whose substance is
CI-workflow YAML, docker-compose YAML, or container service-config YAML therefore classify their
deliverables into bucket `unknown`, which blocks them at the phase-4 Q-Gate. Make these paths
classifiable so infrastructure-shaped plans pass the gate honestly rather than by operator override.

## Deliverables

### D1 — GATE: settle the `ExtensionBase` / `BuildExtensionBase` architectural question (mutates nothing)

**This is the real decision and it must precede any code.** Is "declares path routes" genuinely coupled
to "owns a build system", or is that coupling incidental? A standards-only domain that knows exactly
which files it governs but is structurally barred from saying so is evidence for *incidental*. Choose
among the three options below (or a better one), and record the rationale as a decision:

1. **Give `pm-dev-oci` the Axis-B API** — reparent it to `BuildExtensionBase`, **or** split the
   classification API off `BuildExtensionBase` into a mixin a standards-only domain may also subclass,
   then add `classify_globs` returning the compose + container-config routes. Closes families #2 and #3.
   Does not close #1.
2. **Extend Maven's resource routes** with `*/src/main/docker/*` → `config`. Closes #3 only; the smallest
   possible change.
3. **Introduce a CI/infrastructure domain** owning `.github/workflows/**` and other repo-level
   automation YAML. Closes #1; the largest change. Decide whether a CI domain is warranted at all, or
   whether workflow YAML should simply be `config` under an existing domain.

⚠ **Do not scope to the three literal globs in the table below** — they are representative of the general
class, drawn from one consumer plan. Scope to the class.

### D2 — implement the D1 decision

Scoped to whatever D1 selects. All three families are almost certainly role `config` — none are compiled,
none are executed as tests. **Hard constraint: no route may be declared `production` or `test` merely to
make a path classifiable** — that would silently enlarge the `validate_tree_completeness` denominator
(see the Claim Labels note on `:386-388`), turning a classification fix into a coverage-gate change.

### D3 — tests

(a) `.github/workflows/*.yml`, `docker-compose*.yml` at any depth, and container service-config YAML each
resolve to a **claimed** bucket (not `unknown`) on a project where those files are tracked. (b) A plan
whose affected-files set is exclusively these paths passes the phase-4 Q-Gate with **no operator
override**. (c) Existing route sets are unchanged for projects with none of these files — dead-route
pruning should make this automatic, but **assert it rather than assuming it**. (d)
`validate_tree_completeness` behaviour is unaffected.

Three deliverables (D1 a gate) — well under the split guard.

## Claim Labels

Every claim below was verified against this repo's working tree on 2026-07-27 by the orchestrator. The
brief's own labels were `OBSERVED`; two are corrected here.

- OBSERVED (re-verified): **the gap is total.** `grep -niE 'yml|yaml|workflows'` across all four build
  extensions — `build-maven`, `build-npm`, `build-gradle`, `build-pyproject` `scripts/extension.py` —
  returns **zero hits** (grep exit 1). No extension declares a route for any YAML path of any kind.
- OBSERVED (re-verified): **the gap is structural.** `grep -rln "def classify_paths"` over
  `marketplace/bundles/` matches exactly six files — the four build extensions, plus
  `script-shared/scripts/extension/extension_base.py` and the contract doc
  `extension-api/standards/extension-contract.md`.
- ⚠ **CORRECTED CITATION — the brief cited `extension_base.py:600-603`; that is wrong in this tree.**
  `:600-603` is `route_matches` build-decision logic. The sibling-class rule ("`classify_paths` /
  `classify_path_specificity` / `classify_build_class` lives on the sibling `BuildExtensionBase`,
  subclassed by the build-system-owned extensions. A language domain extension subclasses
  `ExtensionBase` only.") is at **`:616`**. OBSERVED corroboration of the *substance*:
  `class ExtensionBase(ABC)` at `:610`, `class BuildExtensionBase(ABC)` at `:1043`, and all four Axis-B
  methods defined under the latter — `classify_paths` `:1074`, `classify_path_specificity` `:1147`,
  `classify_build_class` `:1181`, `classify_globs` `:1234`. **The claim is TRUE; only the line drifted.**
  Re-verify line numbers at outline rather than trusting any citation in this spec.
- OBSERVED (re-verified): **the natural owner structurally cannot participate.**
  `pm-dev-oci/skills/plan-marshall-plugin/extension.py:14` is `class Extension(ExtensionBase)` and
  implements only `applies_to_module` (`:17`), `provides_triage` (`:61`), `get_skill_domains` (`:65`) —
  **no `classify_globs`, no `classify_paths`**. It DOES already recognise compose files: the
  `container_filenames` tuple (`:25-36`) includes `'docker-compose'`, `'compose.yml'`, `'compose.yaml'`,
  matched at `:40`. So it recognises compose files for **skill loading** and contributes nothing to
  **path classification**. That asymmetry is the defect.
- OBSERVED (re-verified): **Maven's resource route misses the container tree.** `build-maven` declares
  `('*/src/main/resources/*', 'production')` and `('src/main/resources/*', 'production')` (`:124-125`);
  there is **no** `src/main/docker` route anywhere in the file. The API-Sheriff path lives under
  `src/main/docker/`, so the existing route cannot match it.
- OBSERVED (re-verified): `validate_tree_completeness` appends a route to `source_routes` only when
  `role in (ROLE_PRODUCTION, ROLE_TEST)` (`extension_base.py:386-388`), and derives `buildable_roots`
  from those prefixes (`:393`). **A `config` route therefore cannot change the completeness
  denominator** — which is exactly why D2's hard constraint matters.
- OBSERVED (brief, unverifiable from here): API-Sheriff `plan-25-benchmark-suite-completion` is parked at
  phase 3-outline with `solution_outline.md` written and Q-Gate clean; six deliverables, four of them
  awaiting bucket classification. Recorded as **operator-relayed context**, not as a checkable fact in
  this repo.
- HYPOTHESIS: the route contract as the brief states it — `classify_globs()` returns
  `list[tuple[str, str]]` of single-`*` fnmatch globs paired with `production`/`test`/`config`;
  two-regime matching (bare-basename matches the basename anywhere, path-bearing matches the whole
  repo-relative path with `*` spanning `/`); routes keyed by the **first** domain key from
  `get_skill_domains()`; dead routes pruned before any consumer sees them; route sets **unioned** when
  several extensions serve one domain key; longer globs win and list order is load-bearing for
  `classify_build_class`. Confirm/refute at `extension_base.py` § `route_matches` and § `classify_globs`
  (`:1234`) plus the `build-maven` reference implementation at `:93-133` (verify-at-outline).
- Verify-first clause: **D1 must confirm the route contract above against the implementing source before
  choosing an option.** The dead-route-pruning and union properties are what make "declaring a route for a
  file type absent from a given project is free" true — if either is refuted, option 1's blast radius
  changes and the choice must be re-made.

## The three unclaimed glob families

Representative, not exhaustive — scope to the general class.

| # | Glob family | Example path | Natural owner |
|---|-------------|--------------|---------------|
| 1 | `.github/workflows/**` | `.github/workflows/benchmark.yml` | none today — no CI-workflow domain exists |
| 2 | `docker-compose*.yml` (any depth) | `integration-tests/docker-compose.benchmark.yml` | `pm-dev-oci` (already matches the basename for skill loading) |
| 3 | container service-config trees | `integration-tests/src/main/docker/sheriff-config/gateway.yaml` | `pm-dev-oci`, or the owning build extension via its resource route |

## Expected Surface

- OBSERVED: `script-shared/scripts/extension/extension_base.py` — the `ExtensionBase` (`:610`) /
  `BuildExtensionBase` (`:1043`) split, the sibling-class rule at `:616`, and the Axis-B method set
  (`:1074`, `:1147`, `:1181`, `:1234`). **Edited only if D1 picks the mixin split.**
- OBSERVED: `pm-dev-oci/skills/plan-marshall-plugin/extension.py` — class declaration `:14`,
  `container_filenames` `:25-36`. **Edited only if D1 picks option 1.**
- OBSERVED: `build-maven/scripts/extension.py` — `classify_globs` `:93-133`, resource routes `:124-125`.
  **Edited only if D1 picks option 2.**
- OBSERVED: `extension-api/standards/extension-contract.md` — the contract doc must move in lock-step with
  whatever D1 changes about who may declare routes.
- HYPOTHESIS: a new CI/infrastructure domain bundle or skill, only under option 3 (verify-at-outline —
  settle whether a new domain is warranted before creating one).
- OBSERVED: tests under `test/plan-marshall/script-shared/**`, `test/plan-marshall/build-maven/**`, and
  the `pm-dev-oci` test tree, per the option chosen.

**Disjointness:** `script-shared` + `pm-dev-oci` + possibly `build-maven` + `extension-api` standards.
Disjoint from PLAN-79 (`platform-runtime`/`manage-status`/`manage-locks`), PLAN-56
(`marshall-orchestrator`), PLAN-80 (`workflow-integration-github`/`automatic-review`), PLAN-75
(`manage-execution-manifest`).
⚠ **ADJACENT TO PLAN-62, WHICH IS IN FLIGHT — the one real collision risk.** PLAN-62 touches the
`build-maven` / `build-npm` / `build-gradle` / `build-pyproject` **timeout floors**; option 2 of this plan
touches `build-maven/scripts/extension.py`. Expected to be **file-disjoint** (build engine vs extension
declaration) but they sit in the same skills. **If D1 selects option 2, re-check PLAN-62's actual touched
files before D2 edits `build-maven`** — and prefer option 1 or 3 if the overlap turns out to be real.

## Dependencies and Sequencing

- Depends on: none in this repo.
- Overlaps with: **PLAN-62** — see the disjointness warning above; adjacency, not a hard gate.
- Adjacent to: PLAN-86 (`phase-5-execute`) and PLAN-85 (`tools-integration-ci`) — no shared files.
- **Downstream unblock (cross-repo, NOT this plan's work):** once this lands *and is released and
  reinstalled*, API-Sheriff resumes with `/plan-marshall plan=plan-25-benchmark-suite-completion`. ⚠ The
  release-and-reinstall step is the operator's, and it is a genuine precondition — a merged fix that is
  not installed in the consumer does not unblock anything.

## Hand-Off Command

```text
/plan-marshall task="implement .plan/local/orchestrator/truthful-signals/plans/PLAN-87-no-extension-claims-yaml-infrastructure-paths.md"
```

## Write-Boundary

Repository source + tests only. NO writes to `.plan/local/orchestrator/` **ledger state**
(`status.json`, `epic.md`, `plans/`, `landings/`); the `inbox/` channel is the sanctioned exception for
orchestrated plans. See `persona-marshall-orchestrator/standards/orchestration-model.md`
§ Ledger Write-Boundary.
