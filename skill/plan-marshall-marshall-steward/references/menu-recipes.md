# Menu Reference: Recipes

Recipes are deterministic plan templates that bypass the iterative refine → outline → Q-Gate pipeline for well-understood transformations. Each recipe declares its own input contract, its own outline shape, and its own surgical/codebase-wide cascade hints for the manifest composer.

This reference describes the recipes available in the wizard. Recipes are discovered at runtime from three sources:

1. **Built-in** — registered via `provides_recipes()` in extension modules (e.g., `plan-marshall-plugin/extension.py`).
2. **Project-local** — `recipe-*` skills under `.claude/skills/`.
3. **Extension-provided** — `provides_recipes()` callbacks from any active extension.

Use `manage-config list-recipes` to enumerate everything currently visible to the steward, or `manage-config resolve-recipe --recipe <key>` to inspect a single recipe declaration.

---

## Built-in recipe: lesson_cleanup

| Field | Value |
|-------|-------|
| **Key** | `lesson_cleanup` |
| **Skill** | `plan-marshall:recipe-lesson-cleanup` |
| **Scope** | `single_lesson` |
| **Default change_type** | _derived from lesson kind_ |
| **Auto-suggest** | Yes (by `phase-1-init` Step 5c, doc-shaped lessons only) |

**Purpose**: Convert a single lesson-learned into a deterministic surgical plan that fixes exactly what the lesson directs and nothing else. One deliverable per lesson directive; Q-Gate skipped (recipe path is its own gate); `scope_estimate=surgical` forced so the manifest composer drops `automated-review` and `sonar-roundtrip` from Phase 6.

**Derived change_type mapping**:

| Lesson kind | change_type | Cascade rule fired |
|-------------|-------------|---------------------|
| `bug` | `bug_fix` | `surgical+bug_fix` |
| `improvement` | `enhancement` | `surgical+enhancement` |
| `anti-pattern` | `tech_debt` | `surgical+tech_debt` |

**Auto-suggest heuristic** (all three must hold):

1. No fenced code blocks tagged `python`/`py`/`java`/`js`/`javascript`/`ts`/`typescript`.
2. The first non-empty line of each `## Directive`/`## Actions` section does not start with `test`/`refactor`/`implement`/`add code`/`write code`/`migrate`.
3. The body has at least one `## Directive` or `## Actions` heading.

When the user runs `phase-1-init` with `--lesson-id <id>` and the body is doc-shaped, the auto-suggest hook silently sets `plan_source=recipe` + `recipe_key=lesson_cleanup` in status metadata and emits a `Recipe auto-suggested` decision log entry. The user can override on a subsequent run via explicit `--recipe lesson_cleanup` or by editing status metadata.

**Manual selection**:

If a user wants to force `lesson_cleanup` for a code-shaped lesson — or for any lesson regardless of body shape — they can pass `--recipe lesson_cleanup --lesson-id <id>` to `phase-1-init`. The explicit choice always wins over the heuristic.

---

## Built-in recipe: refactor-to-profile-standards

| Field | Value |
|-------|-------|
| **Key** | `refactor-to-profile-standards` |
| **Skill** | `plan-marshall:recipe-refactor-to-profile-standards` |
| **Scope** | `codebase_wide` |
| **Default change_type** | `tech_debt` |
| **Auto-suggest** | No (user must select explicitly) |

**Purpose**: Iterate package-by-package across selected modules, applying the configured profile standards to each package. Generates one deliverable per package. See `marketplace/bundles/plan-marshall/skills/recipe-refactor-to-profile-standards/SKILL.md` for the full contract.

---

## How recipes integrate with the wizard

The wizard exposes recipes through two surfaces:

1. **Configuration menu** (`menu-configuration.md`) — the user can browse registered recipes and confirm which ones are available on this project.
2. **Plan creation** (`/plan-marshall create`) — `--recipe <key>` selects the recipe; `phase-1-init` resolves it via `manage-config resolve-recipe`.

Recipe registration affects which wizard menu items appear: a recipe whose extension is not active in the project is hidden from selection lists. The auto-suggest hook in `phase-1-init` Step 5c is the only mechanism that selects a recipe without user input.

---

## Adding a new recipe

To add a new built-in recipe to plan-marshall:

1. Create the skill: `marketplace/bundles/plan-marshall/skills/recipe-<key>/SKILL.md`. Mirror the shape of `recipe-lesson-cleanup` (input contract, foundational practices, enforcement, four phase-aligned steps).
2. (Optional) Add a `standards/recipe-config.md` documenting the recipe's declaration in human-readable form.
3. Append the recipe entry to `provides_recipes()` in `plan-marshall-plugin/extension.py`. The dict shape is `{key, name, description, skill, default_change_type, scope}`.
4. Register the skill in `.claude-plugin/plugin.json` under `skills`.
5. Add an entry to this file (`menu-recipes.md`) describing the recipe for wizard users.
6. Run `/sync-plugin-cache` then `/marshall-steward` to regenerate the executor with the new skill notation.

For project-local (single-project) recipes, drop a `recipe-*` skill under `.claude/skills/` instead — the steward discovers it automatically via Source 2 in `_discover_all_recipes`. Project recipes do not require `plugin.json` registration.
