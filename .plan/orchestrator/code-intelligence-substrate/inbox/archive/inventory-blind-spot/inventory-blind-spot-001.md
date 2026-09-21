envelope_version=1
sender_type=plan
sender_id=inventory-blind-spot
epic=code-intelligence-substrate
kind=landing
created=2026-07-29T15:48:45Z

## What landed

**Plan**: `inventory-blind-spot` — Fix inventory blind spot over workflow/references/examples markdown
**PR**: #1056 (`fix(inventory): index workflow/references/examples markdown`)
**Branch**: `feature/inventory-blind-spot`

The architecture file inventory could not see markdown living in skill sub-directories other than
`standards/`, `templates/`, and `scripts/`. Three changes shipped:

1. **`_classify_marketplace` residual rule** — a name-free AND extension-free residual: any remaining
   file under `skills/<skill>/**` now classifies as `skill_doc`. The rule follows the pre-existing
   `templates/**/*` precedent in the same function (which already had no extension test). Placed last,
   after the build-file and README tests, so a build file or README under a skill dir keeps its category.
2. **`FILE_CATEGORIES` vocabulary constant** — a new frozenset in `_architecture_core.py`. `architecture
   files --category X` now discriminates unknown-category (`status: error`) from in-vocabulary-but-empty
   (`status: success`, empty list) by membership in that constant, not by membership in the per-module
   files block.
3. **`_classify_generic` peer fix** — the generic (non-marketplace) classifier carried the same
   defect in its own idiom (only `README*` / `CHANGELOG*` recognised as doc).
4. **Doc contract** — `standards/client-api.md` category enumeration corrected (adds `skill_doc`,
   removes the phantom `config` category neither classifier could ever emit) and `manage-architecture`
   SKILL.md updated for the new error shape.

Deliberately **not** done: `SKILL_SUBDOC_DIRS` in `pm-plugin-development`'s `_dep_index.py` was NOT
widened. Widening it would have changed the plugin-doctor lint population by roughly 14 files, a
finding-flood the module-tests gate would not have caught. The edge scan got its own name-free walk
instead, plus a guard test pinning `SKILL_SUBDOC_DIRS` at exactly its four current kinds so a later
helpful edit cannot silently expand the blast radius.

## Measured population

The request named **3** invisible sub-directory kinds. The real measured population was **6 kinds /
138 markdown files (+4 non-markdown: 2 `.json`, 1 `.toon`, 1 `.yml`)`. An allowlist of the 3 named
kinds would have left 8 files invisible and re-broken on the seventh kind.

## Gate record

- Q-Gate: 6 findings, all resolved (5 at `3-outline`, 1 at `4-plan`). Two were `severity: error` —
  including one that proved deliverable D2 was **not implementable as written**.
- `pre-submission-self-review`: clean, 39 candidates examined.
- `pre-push-quality-gate`: 2 bundles + whole-tree green, test-compile + module-tests green.
- `plugin-doctor`: clean, 2 skills gated.
- `ci-verify`: all checks green.
- `automatic-review`: pr-agent reviewed clean; coderabbit rate-limited, operator merge-anyway.
- `review-retrospective`: 2 reviewers compared, 0 actionable comments.
- Lane: init-time operator **deep-lane override** (`lane_escalated: true`, `escalation_trigger: premise`).

## Residue the epic should track

1. **Review-bot participation re-credit defect, observed live on this PR (#1056).**
   `github_pr fetch_findings` does not re-credit a bot's already-proven participation across FIND
   calls without fresh `updated_at` movement. pr-agent genuinely reviewed at 15:07, yet read as
   `absent` on loop-back iteration 2. This is squarely on the `truthful-signals` /
   confident-signal-hides-a-caveat theme and is filed as its own candidate-lesson message.
2. **`architecture find` has no content-search fallback for dispatched leaves.** During this run a
   dispatched leaf had `Grep` denied by the harness while the project hard rule blocks Bash `grep`,
   leaving no sanctioned broad content sweep. Worked around by reading files whole. Worth a look as
   a capability gap.
3. **The 4 non-markdown files (2 `.json`, 1 `.toon`, 1 `.yml`) now classify as `skill_doc`.** That is
   the intended extension-free behaviour, but `skill_doc` is a slightly awkward name for a `.yml`.
   No action taken; flagged so the epic can decide whether a finer taxonomy is ever wanted.
