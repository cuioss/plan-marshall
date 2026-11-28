---
implements: plan-marshall:extension-api/standards/ext-point-execution-context-workflow
mode: workflow
---

# Built-in Recipe Selection Flow

Selection workflow for the built-in **Refactor to Profile Standards** recipe. A single run covers ALL auto-detected domains × one chosen profile, enforcing a per-domain user-selected standards-skill set.

`recipe.md` Step 1a references this document as a thin pointer — the detailed selection mechanics live here, not inline in the orchestration workflow. Any consumer skill that integrates the selection screens references this document by xref rather than inlining the logic.

The flow has three steps:

- **Step A — auto-detect domains** (no selection screen): every applicable/configured domain is included automatically.
- **Step B — DYNAMIC single-select profile + data-driven package_source**: one profile per run, chosen from the union of profiles the detected domains actually expose; the package source is derived data-driven from the selected profile's declared `package_source`.
- **Step C — per-domain paginated skill multi-select**: per detected domain that exposes the chosen profile, a paginated (≤4 options/page) multi-select over that domain's standards skills, defaults pre-checked.

```text
┌──────────────────────────────────────────────────────────────────────────────┐
│              Built-in "Refactor to Profile Standards" selection flow           │
├──────────────────────────────────────────────────────────────────────────────┤
│                                                                                │
│  ┌──────────────────────────────┐                                             │
│  │ Step A  auto-detect ALL       │  no domain selection screen                │
│  │ domains from architecture     │  → recipe_domains (comma-separated)        │
│  └──────────────┬────────────────┘                                            │
│                 │                                                              │
│  ┌──────────────▼────────────────┐                                            │
│  │ Step B  single-select profile  │  DYNAMIC: union of profiles the           │
│  │ (union of domain-exposed       │  detected domains expose                  │
│  │  profiles, NOT a fixed list)   │  → recipe_profile                         │
│  │  derive recipe_package_source  │  data-driven from resolved profile        │
│  │  derive profile-suffixed       │  → refactor-to-profile-standards-{profile}│
│  │  plan_id                       │                                           │
│  └──────────────┬────────────────┘                                            │
│                 │                                                              │
│  ┌──────────────▼────────────────┐                                            │
│  │ Step C  per-domain paginated   │  ≤4 options/page, defaults pre-checked    │
│  │ multi-select skills            │  → recipe_selected_skills__{domain}       │
│  └────────────────────────────────┘                                           │
│                                                                                │
└──────────────────────────────────────────────────────────────────────────────┘
```

---

## Step A — Auto-Detect Domains

Resolve every applicable domain from the project architecture. There is **NO domain selection screen** — a single recipe run spans all detected domains automatically (e.g. a `nifi-extensions` project yields both `java` and `javascript`).

Read the configured domains:

```bash
python3 .plan/execute-script.py plan-marshall:manage-config:manage-config \
  skill-domains list
```

Intersect the configured-domains source with the architecture's applicable-domain signal so that an architecture spanning multiple language domains contributes every applicable domain:

```bash
python3 .plan/execute-script.py plan-marshall:manage-config:manage-config \
  skill-domains detect
```

The detected set is the configured domains that the project architecture actually exercises. Persist it as the comma-separated `recipe_domains` metadata field:

```bash
python3 .plan/execute-script.py plan-marshall:manage-status:manage-status metadata \
  --plan-id {plan_id} --set --field recipe_domains --value {comma_separated_detected_domains}
```

Example: a project exposing both Java and JavaScript yields `recipe_domains = java,javascript`.

---

## Step B — DYNAMIC Single-Select Profile + Data-Driven package_source

### B1. Build the profile option list dynamically

For each detected domain, enumerate the domain's exposed profiles. The `skills_by_profile` keys ARE the domain's non-`core` profiles:

```bash
python3 .plan/execute-script.py plan-marshall:manage-config:manage-config \
  get-skills-by-profile --domain {domain}
```

Take the **union** of those profile keys across all detected domains as the single-select option set. Do **NOT** hardcode a two-option `Implementation`/`Module testing` list — a domain that declares additional profiles (e.g. `documentation`, `integration_testing`) contributes them to the screen automatically.

Present the union as a single-select `AskUserQuestion`:

```text
AskUserQuestion:
  questions:
    - question: "Which profile should be refactored?"
      header: "Profile"
      options:
        # For each profile key in the union of detected domains' exposed profiles (dynamic):
        - label: "{profile_key}"
          description: "Refactor {profile_key} code across all detected domains"
      multiSelect: false
```

Persist the chosen profile:

```bash
python3 .plan/execute-script.py plan-marshall:manage-status:manage-status metadata \
  --plan-id {plan_id} --set --field recipe_profile --value {selected_profile}
```

### B2. Derive `recipe_package_source` data-driven from the resolved profile

After the user picks profile `P`, derive the package source DATA-DRIVEN from the resolved profile — NOT from a hardcoded `implementation`→`packages` / `module_testing`→`test_packages` switch. For any detected domain that exposes `P`, call `resolve-domain-skills`; its output surfaces the resolved profile's declared `package_source`:

```bash
python3 .plan/execute-script.py plan-marshall:manage-config:manage-config \
  resolve-domain-skills --domain {domain} --profile {selected_profile}
```

Read the `package_source` field from the output. The resolved profile declares the `manage-architecture module --full` field it iterates (`implementation` declares `packages`; `module_testing` declares `test_packages`). When the resolved profile declares no `package_source` (e.g. `quality`/`core` omit the key), default to `packages`. The data-driven lookup is open to any future profile/architecture-field pair without a call-layer change.

Persist the derived source:

```bash
python3 .plan/execute-script.py plan-marshall:manage-status:manage-status metadata \
  --plan-id {plan_id} --set --field recipe_package_source --value {derived_package_source}
```

### B3. Derive the profile-suffixed recipe `plan_id`

Because the profile is single-select, running the recipe once per profile must produce DISTINCT, non-colliding plans. Carry the selected profile as a NAME SUFFIX on the recipe-generated `plan_id`:

```text
plan_id = refactor-to-profile-standards-{profile}
```

The profile is kebab-cased, so the slug generalizes to ANY profile name:

- `refactor-to-profile-standards-implementation`
- `refactor-to-profile-standards-module-testing`
- `refactor-to-profile-standards-documentation`

This value is what `recipe.md` Step 2 passes as the explicit `plan_id` override to the phase-1-init dispatch (phase-1-init Step 2 already accepts an explicit `plan_id` override — no phase-1-init change is required). Two parallel recipe runs (any two distinct profiles) therefore yield distinct, non-colliding `plan_id`s AND distinct auto-generated `feature/{plan_id}` branches (phase-5-execute derives the branch as `feature/{plan_id}`).

The **profile is the ONLY suffix axis** — domain is auto-detected and a single run spans all detected domains, so there is no per-domain suffix.

---

## Step C — Per-Domain Paginated Skill Multi-Select

For each detected domain that exposes the chosen profile `P`, present a multi-select over that domain's standards skills. A detected domain that does NOT expose `P` contributes no skill screen and no `recipe_selected_skills__{domain}` field.

### C1. Resolve the domain's skills for the chosen profile

```bash
python3 .plan/execute-script.py plan-marshall:manage-config:manage-config \
  resolve-domain-skills --domain {domain} --profile {selected_profile}
```

Read `defaults` (pre-checked) and `optionals` (unchecked) from the output.

### C2. Build the multi-select option list and paginate

Build a multi-select option list: `defaults` pre-checked, `optionals` unchecked. Each `AskUserQuestion` page carries at most **4 options** (the hard limit), so a domain with more than 4 skills paginates across successive ≤4-option screens, carrying the pre-checked state on every page:

```text
AskUserQuestion:
  questions:
    - question: "Which {profile} standards skills should be enforced for the {domain} domain? (page {n} of {total})"
      header: "Skills ({domain})"
      options:
        # ≤4 skills per page; defaults pre-checked, optionals unchecked:
        - label: "{skill_notation}"
          description: "{skill_description}"
          checked: {true_for_defaults_else_false}
      multiSelect: true
```

### C3. Aggregate and persist per domain

Aggregate the user's finalized selection across all pages for the domain, then persist it as the comma-separated `recipe_selected_skills__{domain}` field:

```bash
python3 .plan/execute-script.py plan-marshall:manage-status:manage-status metadata \
  --plan-id {plan_id} --set --field recipe_selected_skills__{domain} --value {comma_separated_selected_skills}
```

Repeat Steps C1–C3 for every detected domain that exposes the chosen profile.

---

## Metadata Field Contract

The selection flow persists the following `status.json` metadata fields, consumed by `recipe.md` Step 3 and `recipe-refactor-to-profile-standards/SKILL.md`:

| Field | Shape | Source |
|-------|-------|--------|
| `recipe_domains` | Comma-separated auto-detected domain list (e.g. `java,javascript`) | Step A |
| `recipe_profile` | Single profile — any profile a detected domain exposes (NOT limited to `implementation`/`module_testing`) | Step B1 |
| `recipe_package_source` | Architecture-iteration field, derived data-driven from the selected profile's declared `package_source` (`packages`/`test_packages` today; open to any architecture field a future profile declares) | Step B2 |
| `recipe_selected_skills__{domain}` | One field per detected domain that exposes the chosen profile, holding a comma-separated list of the user-selected skill notations for that domain | Step C |

The profile option list and `recipe_package_source` are both **enumerated/derived from the domain profile declarations**, not from a fixed list:

- The profile screen options come from the `get-skills-by-profile` keys (the union across detected domains).
- `recipe_package_source` comes from the resolved profile's declared `package_source` surfaced by `resolve-domain-skills`, defaulting to `packages` when the profile declares none.

The profile-suffixed `plan_id` (`refactor-to-profile-standards-{profile}`, derived in Step B3) is the value `recipe.md` Step 2 passes as the explicit `plan_id` override to the phase-1-init dispatch.

---

## Related

- `plan-marshall:manage-config skill-domains list` / `skill-domains detect` — Domain auto-detection (Step A)
- `plan-marshall:manage-config get-skills-by-profile` — Per-domain profile enumeration (Step B1)
- `plan-marshall:manage-config resolve-domain-skills` — Per-domain skill resolution + `package_source` surfacing (Steps B2, C1)
- `plan-marshall:plan-marshall` recipe workflow (`recipe.md`) — Step 1a references this flow; Step 2 passes the profile-suffixed `plan_id`; Step 3 documents the canonical metadata field set
- `plan-marshall:recipe-refactor-to-profile-standards` SKILL.md — Consumes the persisted multi-domain field set
