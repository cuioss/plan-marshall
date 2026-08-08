# Plugin Development Suppression Syntax

How to suppress various types of findings in marketplace plugin development.

## Python Linting (noqa)

### Line-Level Suppression

```python
# Suppress specific rule
long_line = "This is a very long line that exceeds the limit"  # noqa: E501

# Suppress multiple rules
from module import *  # noqa: F401,F403

# Suppress all rules on line (use sparingly)
complex_expression = something()  # noqa
```

### Common noqa Codes

| Code | Meaning | When to Use |
|------|---------|-------------|
| `E501` | Line too long | Long URLs, regex patterns |
| `F401` | Imported but unused | Conditional imports |
| `F403` | Star import | Re-exporting from __init__.py |
| `E741` | Ambiguous variable name | Mathematical notation |

## Python Type Checking

### Type Ignore

```python
# Ignore type error on line
result = dynamic_func()  # type: ignore

# Ignore specific type error
value: str = get_value()  # type: ignore[assignment]

# With explanation (recommended)
data = json.loads(text)  # type: ignore[arg-type] - text is validated above
```

### Common Type Ignore Situations

| Situation | Syntax |
|-----------|--------|
| Dynamic return type | `# type: ignore[return-value]` |
| Union narrowing issue | `# type: ignore[arg-type]` |
| Third-party stub missing | `# type: ignore[import]` |

## Pytest Suppressions

### Skip Test

```python
@pytest.mark.skip(reason="Requires external service")
def test_external_api():
    pass

# Conditional skip
@pytest.mark.skipif(sys.platform == "win32", reason="Unix only")
def test_unix_feature():
    pass
```

### Expected Failure

```python
@pytest.mark.xfail(reason="Known bug, tracked in ISSUE-123")
def test_known_failure():
    pass

# Strict xfail - fails if test passes
@pytest.mark.xfail(reason="Bug fixed?", strict=True)
def test_should_still_fail():
    pass
```

### Parameterize Skip

```python
@pytest.mark.parametrize("value,expected", [
    ("valid", True),
    pytest.param("edge", False, marks=pytest.mark.skip(reason="Edge case TBD")),
])
def test_validation(value, expected):
    pass
```

## Markdown Linting

### Inline Suppression

```markdown
<!-- markdownlint-disable MD001 -->
Content that violates MD001...
<!-- markdownlint-enable MD001 -->
```

### File-Level Suppression

```markdown
<!-- markdownlint-disable -->
This entire file is not linted.
```

### Common Markdown Rules

| Rule | Meaning | When to Suppress |
|------|---------|------------------|
| `MD001` | Heading levels should increment by one | Intentional structure |
| `MD013` | Line length | Tables, URLs |
| `MD033` | No inline HTML | Necessary HTML elements |
| `MD041` | First line should be heading | Frontmatter files |

## YAML Validation

### No direct suppression - fix the issue or configure validator

For yamllint:

```yaml
# .yamllint
rules:
  line-length:
    max: 120
  truthy:
    check-keys: false
```

## Plugin-Doctor Issues

Plugin-doctor issues are typically structural and should be fixed. However, some can be explained:

### Rule 8 (Bootstrap Scripts)

Expected for initialization scripts that must use absolute paths:

```markdown
<!-- This script is a bootstrap script that initializes the skill environment.
     Rule 8 violation is expected as it needs absolute paths for initial setup. -->
```

### Frontmatter Issues

Fix by updating frontmatter, no suppression available:

```yaml
---
name: skill-name
description: Description of the skill
allowed-tools: Read, Glob
---
```

## Best Practices

### Always Include Reason

```python
# Good - explains why
@pytest.mark.skip(reason="Requires Redis server - run with integration profile")
def test_redis_connection():
    pass

# Bad - no explanation
@pytest.mark.skip
def test_redis_connection():
    pass
```

### Reference Issues for Deferred Fixes

```python
# type: ignore[return-value]  # ISSUE-456: Refactor to proper typing
```

### Scope Minimally

```python
# Good - specific rule
long_url = "https://..."  # noqa: E501

# Avoid - suppresses everything
long_url = "https://..."  # noqa
```

## When NOT to Suppress

- Test failures (fix the test or code)
- Plugin-doctor critical issues (fix for quality)
- Security-related Python issues
- Type errors in new code (type properly)
- Markdown structure issues (fix for consistency)
