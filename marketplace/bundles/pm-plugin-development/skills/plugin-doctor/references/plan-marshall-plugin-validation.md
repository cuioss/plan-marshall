# Plan-Marshall Plugin Validation Guide

Validation rules for skills named `plan-marshall-plugin` that contain domain manifests.

## When to Use This Guide

Load this reference when doctoring a skill where:
- `name` in frontmatter equals `plan-marshall-plugin`
- The skill contains an `extension.py` file implementing the Extension API

## Validation Script

Use the plugin-doctor extension validation:

```bash
python3 .plan/execute-script.py pm-plugin-development:plugin-doctor:validate extension \
  --bundle {bundle_name}
```

**Note**: Extract bundle name from the skill path: `marketplace/bundles/{bundle}/skills/plan-marshall-plugin`

## Domain Manifest Validation

### Required Functions

| Function | Description | Fix Type |
|----------|-------------|----------|
| `get_skill_domains()` | Domain metadata with profiles | Safe |

### Optional Functions

| Function | Description | Fix Type |
|----------|-------------|----------|
| `discover_modules()` | Project module discovery | Safe |
| `config_defaults()` | Project configuration defaults | Safe |
| `provides_triage()` | Triage skill reference | Risky |
| `provides_change_type_agents()` | Change-type to agent mappings | Risky |

### Profile Structure

The `get_skill_domains()` must return:
- `domain.key` - Domain identifier (kebab-case)
- `domain.name` - Human-readable name
- `profiles.core` - Core profile (required)
- Each profile has `defaults` and `optionals` arrays

### Profile Names

Valid profile names:
- `core` (required)
- `implementation` (optional)
- `testing` (optional)
- `quality` (optional)

Any other profile name is invalid.

## Validation Output

### Success Output

```toon
status: success
type: domain
domain: java
validation:
  functions: valid
  profiles:
    core: valid
    implementation: valid
    testing: valid
    quality: valid
  skill_references: valid
```

### Error Output

```toon
status: error
type: domain
validation:
  functions: invalid
errors:
  - Missing required function: 'get_skill_domains'
```

## Fix Patterns

### Safe Fixes

**Add missing function**:
```python
def get_skill_domains() -> dict:
    return {
        "domain": {
            "key": "my-domain",
            "name": "My Domain"
        },
        "profiles": {
            "core": {"defaults": [], "optionals": []}
        }
    }
```

### Risky Fixes

**Missing extension skill**: Cannot auto-fix. Requires either:
1. Creating the extension skill
2. Removing the extension reference

**Invalid skill reference**: Cannot auto-fix. Requires manual review of:
1. Skill existence
2. Bundle correctness
3. Skill name spelling

## Integration with doctor-skills Workflow

When `skill-name` matches `plan-marshall-plugin`:

1. **Standard analysis** (Step 3):
   - Run `analyze.py structure` on skill directory
   - Run `analyze.py markdown` on SKILL.md
   - Run `validate.py references` on SKILL.md

2. **Additional extension validation** (Step 3c):
   ```bash
   # Extract bundle from path
   BUNDLE=$(echo "{skill_path}" | sed 's|.*bundles/\([^/]*\)/.*|\1|')

   # Run extension validation
   python3 .plan/execute-script.py pm-plugin-development:plugin-doctor:validate extension \
     --bundle ${BUNDLE}
   ```

3. **Report findings**:
   - Include extension validation status in output
   - Categorize issues as safe/risky
   - Apply safe fixes automatically
   - Prompt for risky fixes
