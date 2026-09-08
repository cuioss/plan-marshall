# Marketplace Inventory Script Parameters

Detailed parameter documentation for `scan-marketplace-inventory.py`.

## Exit-code convention for every script call

The exit-code contract for every `python3 .plan/execute-script.py` call in this document — of EVERY notation, not only `manage-*` — is stated once in [`tools-script-executor/standards/exit-code-convention.md`](../../../../plan-marshall/skills/tools-script-executor/standards/exit-code-convention.md); it is not restated here.

## --scope (optional)

Directory scope to scan. Default: `auto`

| Value | Description |
|-------|-------------|
| `auto` | **Default**. Tries `marketplace/bundles/` first, falls back to the deployed-bundle cache |
| `marketplace` | Explicit: scans marketplace/bundles/ directory only |
| `plugin-cache` | Explicit: scans the deployed-bundle cache only (resolved target-aware via the `layout bundle-cache-root` op; the Claude deployment lives under `~/.claude/plugins/cache/plan-marshall/`) |
| `global` | Scans the user-global deployment directory (Claude: `~/.claude`) |
| `project` | Scans the project-local skill tree (resolved target-aware via the `layout skill-roots` op; Claude: `.claude/skills`) |

The `auto` default makes the script work in both the marketplace repo and other projects without specifying a scope.

**Example**:
```bash
python3 .plan/execute-script.py pm-plugin-development:tools-marketplace-inventory:scan-marketplace-inventory --scope marketplace
python3 .plan/execute-script.py pm-plugin-development:tools-marketplace-inventory:scan-marketplace-inventory --scope project
```

## --resource-types (optional)

Filter which resource types to include in the inventory. Default: `all`

| Value | Description |
|-------|-------------|
| `all` | Include all resource types (default) |
| `agents` | Include only agents |
| `commands` | Include only commands |
| `skills` | Include only skills |
| `scripts` | Include only scripts |

Multiple types can be combined with commas:
```bash
python3 .plan/execute-script.py pm-plugin-development:tools-marketplace-inventory:scan-marketplace-inventory --resource-types agents,skills
```

## --include-descriptions (optional flag)

When specified, extracts description fields from YAML frontmatter of each resource file. Requires `--format json` to see structured output.

```bash
python3 .plan/execute-script.py pm-plugin-development:tools-marketplace-inventory:scan-marketplace-inventory \
  --include-descriptions --format json
```

## --full (optional flag)

When specified, includes full details: frontmatter fields and skill subdirectory contents with nested file listings.

```bash
python3 .plan/execute-script.py pm-plugin-development:tools-marketplace-inventory:scan-marketplace-inventory \
  --full --bundles plan-marshall
```

**Output with --full.** The block below is **captured verbatim from a live run**,
narrowed to one skill with `--name-pattern tools-permission-doctor` so it fits.
It is not a hand-written illustration, and it must not be edited by hand: re-capture
it from a real run if it ever needs to change, because a hand-authored row reliably
disagrees with the emitter in exactly the ways this format's single implementation
exists to prevent.

```toon
status: success
scope: auto
base_path: /abs/path/to/marketplace/bundles
plan-marshall:
  path: marketplace/bundles/plan-marshall
  skills[1]{name,path,description,user_invocable,standards}:
    tools-permission-doctor,marketplace/bundles/plan-marshall/skills/tools-permission-doctor,Diagnose permission issues across settings files (read-only analysis),true,"[\"marketplace/bundles/plan-marshall/skills/tools-permission-doctor/standards/permission-anti-patterns.md\", \"marketplace/bundles/plan-marshall/skills/tools-permission-doctor/standards/permission-architecture.md\", \"marketplace/bundles/plan-marshall/skills/tools-permission-doctor/standards/permission-validation-standards.md\"]"
statistics:
  total_bundles: 1
  total_skills: 1
```

Three properties of that row are worth naming, because each is a place a
hand-written example gets it wrong:

- A **list cell is JSON**, escaped with **backslashes** (`\"`), not by doubling the
  quote as CSV does. The reader half recognises only the backslash form.
- Subdirectory entries are **repo-relative paths**, not bare filenames.
- `scripts` is a **sibling bucket**, never a column of the skills table — the
  columns come from the row composer, and `scripts` is not among them.

**Full mode includes:**
- Skill frontmatter: `user_invocable`, `allowed_tools`, `model`
- Skill subdirectories with their files: `standards/`, `templates/`, `references/`, `knowledge/`, `examples/`, `documents/` — `scripts/` is deliberately absent from this set, being a sibling bucket of its own rather than a column of the skills table

**Read the block, do not pattern-match it.** The output is written by the canonical
serializer, so a full-mode component list is a **uniform-array table** — one header
naming the columns, then one comma-separated row per component — not a `- name:`
entry with indented keys. Quoting is the serializer's decision, so any value carrying
a comma, a colon or a quote arrives quoted and a consumer must `parse_toon` the block
rather than split it by hand.

The column set is the **union of the keys present across that table's rows**, so it
varies with what the scanned components actually carry: a component missing a key a
sibling has renders an empty column rather than no column, and a key no component in
the table carries is absent from the header entirely. Read a column's presence from
the header of the run in hand — never from the capture above, which is one real run
over one skill and therefore shows one shape among many.

## --name-pattern (optional)

Filter resources by name using fnmatch glob patterns. Use pipe (`|`) to separate multiple patterns.

| Pattern | Matches |
|---------|---------|
| `*-plan-*` | Names containing "-plan-" |
| `plan-*` | Names starting with "plan-" |
| `*-agent` | Names ending with "-agent" |

```bash
# Single pattern
python3 .plan/execute-script.py pm-plugin-development:tools-marketplace-inventory:scan-marketplace-inventory --name-pattern "*-plan-*"

# Multiple patterns (pipe-separated)
python3 .plan/execute-script.py pm-plugin-development:tools-marketplace-inventory:scan-marketplace-inventory --name-pattern "*-plan-*|*-specify-*|plan-*|manage-*"
```

## --content-pattern (optional)

Filter resources by content using regex patterns. Use pipe (`|`) to separate multiple patterns (OR logic). **Requires `--include-descriptions` or `--full`** to enable path resolution.

Uses Python `re.search()` with `re.MULTILINE` flag. Scripts (.py, .sh) are NOT content-filtered.

```bash
# Find files with JSON code blocks
python3 .plan/execute-script.py pm-plugin-development:tools-marketplace-inventory:scan-marketplace-inventory \
  --resource-types agents,skills \
  --content-pattern '```json' \
  --include-descriptions \
  --direct-result

# Multiple patterns (OR logic)
python3 .plan/execute-script.py pm-plugin-development:tools-marketplace-inventory:scan-marketplace-inventory \
  --resource-types skills \
  --content-pattern '```json|```toon' \
  --full \
  --direct-result
```

**Output with content filtering** includes filter stats:
```toon
status: success
scope: marketplace
content_pattern: "```json"
content_filter_stats:
  input_count: 188
  matched_count: 32
  excluded_count: 156
```

## --content-exclude (optional)

Exclude resources matching content patterns (OR logic). Use pipe (`|`) to separate multiple patterns. **Requires `--include-descriptions` or `--full`**.

```bash
# Find JSON blocks but exclude already-migrated files
python3 .plan/execute-script.py pm-plugin-development:tools-marketplace-inventory:scan-marketplace-inventory \
  --resource-types agents \
  --content-pattern '```json' \
  --content-exclude 'format: toon|output-format: toon' \
  --include-descriptions \
  --direct-result
```

### Combining --content-pattern and --content-exclude

When both are specified:
1. **Include filter**: File must match at least one include pattern
2. **Exclude filter**: File must NOT match any exclude pattern

```bash
# Find files with JSON but not configuration JSON
python3 .plan/execute-script.py pm-plugin-development:tools-marketplace-inventory:scan-marketplace-inventory \
  --bundles pm-dev-java,pm-plugin-development \
  --resource-types agents \
  --content-pattern '```json' \
  --content-exclude '## Configuration.*```json' \
  --full \
  --direct-result
```

## --bundles (optional)

Filter to specific bundles by name (comma-separated).

```bash
# Single bundle
python3 .plan/execute-script.py pm-plugin-development:tools-marketplace-inventory:scan-marketplace-inventory --bundles planning

# Multiple bundles
python3 .plan/execute-script.py pm-plugin-development:tools-marketplace-inventory:scan-marketplace-inventory --bundles "planning,pm-dev-java,pm-dev-frontend"
```

## --direct-result (optional flag)

Output full TOON directly to stdout instead of writing to file.

| Mode | Behavior |
|------|----------|
| Default (no flag) | Writes to `.plan/temp/tools-marketplace-inventory/inventory-{timestamp}.toon`, prints summary |
| `--direct-result` | Outputs full TOON inventory directly to stdout |

**When to use `--direct-result`**:
- Small inventories (filtered bundles/patterns)
- Piped usage where file I/O is not desired
- Script-to-script calls where caller parses TOON directly

## --format (optional)

Output format. Default: `toon`

| Value | Description |
|-------|-------------|
| `toon` | TOON format with bundles as top-level keys (default) |
| `json` | JSON format with `bundles` as dict keyed by bundle name |

## --include-tests (optional flag)

When specified, includes test files from `test/{bundle-name}/` directories. Discovers `test_*.py` and `conftest.py` files.

```bash
python3 .plan/execute-script.py pm-plugin-development:tools-marketplace-inventory:scan-marketplace-inventory \
  --include-tests --bundles pm-plugin-development --direct-result
```

## --include-project-skills (optional flag)

When specified, includes project-level skills from the active target's project-local skill roots (resolved via the `layout skill-roots` op; Claude: `.claude/skills/`). Creates a `project-skills` pseudo-bundle.

```bash
python3 .plan/execute-script.py pm-plugin-development:tools-marketplace-inventory:scan-marketplace-inventory \
  --include-project-skills --direct-result
```

## Combining Flags

Both `--include-tests` and `--include-project-skills` can be used together:

```bash
python3 .plan/execute-script.py pm-plugin-development:tools-marketplace-inventory:scan-marketplace-inventory \
  --include-tests \
  --include-project-skills \
  --full \
  --direct-result
```
