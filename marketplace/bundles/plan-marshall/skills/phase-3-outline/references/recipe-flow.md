# Recipe Flow Architecture

How recipe-sourced plans flow through the phase system, complementing the change-type routing in [architecture-diagram.md](architecture-diagram.md).

## Recipe vs Normal Plan

Normal plans discover WHAT to do from a free-form request. Recipes already know WHAT and HOW — they only discover WHERE to apply.

```
Normal Plan                              Recipe Plan
───────────                              ───────────
User request (free-form)                 User selects recipe + parameters
        │                                        │
   phase-1-init                             phase-1-init
        │                                        │
   phase-2-refine                           phase-2-refine
   (iterative Q&A,                          (scope only,
    confidence build)                        confidence=100)
        │                                        │
   phase-3-outline                          phase-3-outline
   ┌────┴────┐                              Step 2.5 intercepts
   │ detect  │                                   │
   │ change  │                              load recipe skill
   │ type    │                              with parameters
   │    │    │                                   │
   │ outline │                              recipe creates
   │ change  │                              deliverables
   │ type    │                                   │
   └────┬────┘                              (no Q-Gate — deterministic)
        │                                        │
   phase-4-plan ◄────── same from here ──►  phase-4-plan
        │                                        │
   phase-5-execute                          phase-5-execute
        │                                        │
   phase-6-finalize                         phase-6-finalize
```

## Three Recipe Categories

```
                    ┌─────────────────────────┐
                    │   Recipe Selection       │
                    │   (recipe.md Step 1)     │
                    └────────────┬─────────────┘
                                 │
         ┌───────────────────────┼───────────────────────┐
         │                       │                       │
┌────────▼─────────┐  ┌─────────▼──────────┐  ┌─────────▼──────────┐
│  Built-in Recipe │  │  Custom Recipes     │  │  Project Recipes   │
│                  │  │                     │  │                    │
│  "Refactor to    │  │  Registered via     │  │  Added via         │
│   Profile        │  │  provides_recipes() │  │  skill-domains     │
│   Standards"     │  │  in extension.py    │  │  add-recipe CLI    │
│                  │  │                     │  │                    │
│  plan-marshall:    │  │  Each has its own   │  │  source: "project" │
│  recipe-refactor-│  │  skill reference    │  │  in marshal.json   │
│  to-profile-     │  │  in marshal.json    │  │                    │
│  standards       │  │                     │  │  For projects w/o  │
│                  │  │                     │  │  domain extensions  │
└────────┬─────────┘  └─────────┬──────────┘  └─────────┬──────────┘
         │                      │                       │
auto-detect ALL domains         │                       │
select ONE profile              │                       │
 (any exposed value)     resolve-recipe returns  resolve-recipe returns
derive pkg_source        skill, change_type,     skill, change_type,
 from profile            scope                   scope (source=project)
         │                      │                       │
         └──────────────────────┼───────────────────────┘
                                │
                   ┌────────────▼───────────────────────┐
                   │  Store metadata in                 │
                   │  status.json                       │
                   │                                    │
                   │  plan_source = recipe              │
                   │  recipe_key                        │
                   │  recipe_skill                      │
                   │  recipe_domains *                  │
                   │  recipe_profile *                  │
                   │  recipe_package_source *           │
                   │  recipe_selected_skills__{domain} *│
                   │   (one per detected domain)        │
                   │                                    │
                   │  * built-in only                   │
                   └────────────────────────────────────┘
```

## Phase-3-Outline: Recipe Detection (Step 2.5)

When phase-3-outline detects `plan_source == recipe`, it bypasses the normal change-type detection and skill routing entirely:

```
phase-3-outline
     │
     ├─ Step 1: Check Q-Gate findings (re-entry, n/a for recipes)
     │
     ├─ Step 2: Load inputs (request, domains, track, ...)
     │
     ├─ Step 2.5: Recipe detection
     │       │
     │       ├── plan_source == recipe?
     │       │          │
     │       │     ┌────┴────┐
     │       │     │  YES    │
     │       │     └────┬────┘
     │       │          │
     │       │    1. Read metadata: recipe_key, recipe_skill;
     │       │       built-in → recipe_domains (plural),
     │       │       recipe_profile, recipe_package_source,
     │       │       recipe_selected_skills__{domain} (per domain);
     │       │       custom → recipe_domain (singular)
     │       │          │
     │       │    2. resolve-recipe → get default_change_type
     │       │          │
     │       │    3. Set change_type in status (skip detect agent)
     │       │          │
     │       │    4. Load recipe skill (built-in field set shown;
     │       │       custom passes the singular recipe_domain set):
     │       │       ┌────────────────────────────────────────┐
     │       │       │ Skill: {recipe_skill}                  │
     │       │       │   Input:                               │
     │       │       │     plan_id                            │
     │       │       │     recipe_domains (comma-separated)   │
     │       │       │     recipe_profile (any exposed value) │
     │       │       │     recipe_package_source (per profile)│
     │       │       │     recipe_selected_skills__{domain}   │
     │       │       │       (one per detected domain)        │
     │       │       └──────────────┬─────────────────────────┘
     │       │                      │
     │       │              skill writes:
     │       │              • deliverables
     │       │              • solution_outline.md
     │       │                      │
     │       │    5. Skip to Step 11 (no Q-Gate)
     │       │       Recipe output is deterministic —
     │       │       Q-Gate checks don't apply.
     │       │          │
     │       │     ┌────┴────┐
     │       │     │   NO    │ → continue normal Steps 3-10
     │       │     └─────────┘   (detect change type, route by track)
     │       │
     ├─ Step 3-10: Normal flow (skipped for recipes)
     │
     └─ Step 11: Write solution and return
```

## Unified Recipe Skill Interface

Both built-in and custom recipe skills are loaded by phase-3-outline through the same call. The contract (load skill → write `solution_outline.md` → return) is identical; only the input field set differs by recipe kind — the built-in recipe spans every auto-detected domain, so it carries a multi-domain field set, whereas a custom recipe carries the single-domain set.

```
phase-3-outline Step 2.5
     │
     │  Built-in recipe (multi-domain — spans ALL detected domains):
     │
     │  Skill: {recipe_skill}
     │    Input:
     │      plan_id: {plan_id}
     │      recipe_domains: {comma-separated detected domains}
     │      recipe_profile: {any profile a domain exposes}
     │      recipe_package_source: {derived from the profile}
     │      recipe_selected_skills__{domain}: {per-domain skill set}
     │        (one field per detected domain exposing the profile)
     │
     │  Custom recipe (single-domain — interface unchanged):
     │
     │  Skill: {recipe_skill}
     │    Input:
     │      plan_id: {plan_id}
     │      recipe_domain: {domain or empty}
     │      recipe_profile: {profile or empty}
     │      recipe_package_source: {package_source or empty}
     │
     │  Both kinds must write:
     │    • solution_outline.md (deliverables grouped by module)
     │
     │  Each deliverable must include:
     │    • change_type, execution_mode=automated, domain
     │    • module, profile, skills (resolved dynamically), files
     │
     └── Returns to phase-3-outline → Step 11 (no Q-Gate)
```

For the built-in recipe the multi-domain field set is always populated — `recipe_domains` lists every auto-detected domain, `recipe_profile` is the single chosen profile (any value a detected domain exposes, not limited to `implementation`/`module_testing`), `recipe_package_source` is derived data-driven from that profile's declared package source, and one `recipe_selected_skills__{domain}` field is present per detected domain that exposes the profile. Custom recipes receive the single-domain `recipe_domain`/`recipe_profile`/`recipe_package_source` set if the extension declares `profile` and `package_source` on the recipe dict; otherwise they are empty strings and the custom skill must determine these values itself.

Full interface contract: see `plan-marshall:extension-api` [extension-contract.md](../../extension-api/standards/extension-contract.md#provides_recipes).

---

## Built-in Recipe: recipe-refactor-to-profile-standards

The built-in recipe is domain-invariant. It uses the input parameters to resolve skills and iterate packages — no domain-specific logic.

```
recipe-refactor-to-profile-standards
     │
     │  Inputs: plan_id, recipe_domains (comma-separated), recipe_profile,
     │          recipe_package_source,
     │          recipe_selected_skills__{domain} (one per detected domain)
     │
     ├─ Step 0: Gather + expand + persist coverage cell
     │
     ├─ Step 1: Resolve per-domain selected skills
     │    read recipe_selected_skills__{domain} from metadata per domain
     │    → user-finalized skill set per domain (NOT re-resolved here)
     │
     ├─ Step 2: List modules
     │    architecture modules → present to user for filtering
     │
     ├─ Step 3: Per domain × module — load packages and create deliverables
     │    │
     │    │  architecture module --module {name} --full
     │    │  → iterate {recipe_package_source} field
     │    │
     │    │  For each package:
     │    │  ┌───────────────────────────────────────────┐
     │    │  │ Deliverable:                              │
     │    │  │   title: Refactor ({profile}):            │
     │    │  │          {module}/{package}               │
     │    │  │   change_type: tech_debt                  │
     │    │  │   domain: {domain} (iterated domain)      │
     │    │  │   profile: {recipe_profile}               │
     │    │  │   skills: {domain's selected skill set}   │
     │    │  │   files: {from architecture data}         │
     │    │  └───────────────────────────────────────────┘
     │    │
     │    │  No analysis step — the task executor (phase-5-execute)
     │    │  loads the same profile skills and handles
     │    │  analysis + fixing in one pass per package.
     │    │
     │
     └─ Step 4: Write solution_outline.md grouped by domain then module
```

---

## Custom Recipe: Extension-Provided

Custom recipes are registered via `provides_recipes()` in the domain's `extension.py`, stored in marshal.json, and resolved at plan-time. They implement their own skill with domain-specific logic.

```
Custom recipe skill (e.g., pm-dev-java:recipe-null-safety)
     │
     │  Inputs: plan_id, recipe_domain, recipe_profile, recipe_package_source
     │          (may be empty — depends on recipe dict declaration)
     │
     │  The skill is free to implement any discovery/analysis logic,
     │  but must write solution_outline.md with valid deliverables.
     │
     │  Example: domain-specific analysis agent, custom file filtering,
     │  non-package-based scope units, etc.
     │
     ├─ ... domain-specific discovery ...
     ├─ ... domain-specific analysis ...
     ├─ Create deliverables (must follow deliverable contract)
     └─ Write solution_outline.md
```

Custom recipe registration:

```
extension.py                    marshal.json                     recipe.md
────────────                    ────────────                     ─────────

provides_recipes() ──────►  skill_domains.{domain}.recipes  ──► list-recipes
  returns list of dicts         stored by marshall-steward       presents to user
  with key, name, skill,                                         │
  default_change_type, ...                                  resolve-recipe
                                                                 │
                                                            stores metadata
                                                                 │
                                                            phase-3-outline
                                                            loads Skill: {skill}
```

## End-to-End: Built-in Recipe Example

Concrete example: user wants to refactor production code to standards across a multi-domain repo (java + javascript).

```
User: /plan-marshall action=recipe
         │
         ▼
  recipe.md Step 1
  ┌─────────────────────────────────────────┐
  │ Built-in: Refactor to Profile           │ ◄── user selects
  │ Custom:   (none registered)             │
  └────────────────────┬────────────────────┘
                       │
  recipe.md Step 1a
  ┌─────────────────────────────────────────┐
  │ Domains: java, javascript               │ ◄── auto-detected (ALL)
  │ Profile: implementation                 │ ◄── user selects ONE
  │ Package source: packages                │ ◄── derived from profile
  │ Skills (per domain):                    │ ◄── user multi-selects
  │   java       → java-core, java-cdi, ... │
  │   javascript → javascript, jest-...     │
  └────────────────────┬────────────────────┘
                       │
  recipe.md Step 2: execution-context (workflow=phase-1-init/SKILL.md)
         │ creates plan, plan_id = "refactor-to-profile-standards-implementation"
         │
  recipe.md Step 3: store metadata
         │ plan_source=recipe, recipe_key, recipe_skill,
         │ recipe_domains=java,javascript, recipe_profile=implementation,
         │ recipe_package_source=packages,
         │ recipe_selected_skills__java=..., recipe_selected_skills__javascript=...
         │
  ┌──────▼──────────────────────────┐
  │ phase-2-refine                  │
  │   scope=codebase_wide           │
  │   confidence=100 (auto)         │
  │   track=complex                 │
  └──────┬──────────────────────────┘
         │
  ┌──────▼──────────────────────────┐
  │ phase-3-outline                 │
  │   Step 2.5: plan_source=recipe  │
  │   → resolve-recipe              │
  │     → change_type=tech_debt     │
  │   → Skill: plan-marshall:recipe-  │
  │     refactor-to-profile-stds    │
  │     domains=java,javascript     │
  │     profile=implementation      │
  │     package_source=packages     │
  │     selected_skills__{domain}   │
  │                                 │
  │   Recipe skill:                 │
  │   1. per domain: use selected   │
  │      skills (java-core, jest..) │
  │   2. architecture modules       │
  │      → my-core, my-api, my-web  │
  │   3. Per domain × module:       │
  │      iterate pkgs → 1 deliv/pkg │
  │   4. Write solution_outline.md  │
  │                                 │
  │   (no Q-Gate — deterministic)   │
  └──────┬──────────────────────────┘
         │
  ┌──────▼──────────────────────────┐
  │ phase-4-plan                    │
  │   1 task per deliverable        │
  │   profile: implementation       │
  │   skills: per-domain selected   │
  └──────┬──────────────────────────┘
         │
  ┌──────▼──────────────────────────┐
  │ phase-5-execute                 │
  │   Per task:                     │
  │   • Load profile skills         │
  │   • Read package files          │
  │   • Analyze + fix in one pass   │
  │   • Verify build                │
  └──────┬──────────────────────────┘
         │
  ┌──────▼──────────────────────────┐
  │ phase-6-finalize                │
  │   commit, PR, review            │
  └─────────────────────────────────┘
```

## Data Flow: Status Metadata

```
recipe.md                    phase-3-outline              recipe skill
─────────                    ───────────────              ────────────

Sets in status.json:              Reads from status.json:        Receives as input (built-in):
                                       │                       │
plan_source=recipe ──────────────► plan_source ─── if recipe ──┤
recipe_key ──────────────────────► recipe_key ─── resolve ─────┤
recipe_skill ────────────────────► recipe_skill ── Skill: ─────┤
recipe_domains ──────────────────► recipe_domains ────────────►│──► recipe_domains
recipe_profile ──────────────────► recipe_profile ────────────►│──► recipe_profile
recipe_package_source ───────────► recipe_package_source ─────►│──► recipe_package_source
recipe_selected_skills__{domain} ► recipe_selected_skills__{d}►│──► recipe_selected_skills__{domain}
  (one per detected domain)                                    │       (one per detected domain)
                                                               │
                                   Also sets:                  │
                                   change_type ◄── from resolve-recipe

Custom recipes carry the single-domain recipe_domain field instead of
recipe_domains / recipe_selected_skills__{domain}.
```

## Related

- [architecture-diagram.md](architecture-diagram.md) — Change-type routing (normal plans)
- `plan-marshall:plan-marshall` workflow/recipe.md — Recipe workflow entry point
- `plan-marshall:recipe-refactor-to-profile-standards` — Built-in recipe skill
- `plan-marshall:extension-api` extension-contract.md#provides_recipes — Recipe extension API contract
