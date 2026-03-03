# Permission Validation Standards

Standards and patterns for validating and maintaining Claude Code permissions in settings files.

## Validation Criteria

### Format Validation

**Bash Command Patterns:**
```json
{
  "tool": "Bash",
  "pattern": "command:*"
}
```

**Requirements:**
- Must use specific command followed by `:*` wildcard
- Commands must be exact (e.g., `git:*`, not `git*` or `git:**`)
- One permission per command pattern
- No shell operators in pattern (&&, ||, ;, |)

**Read/Write/Edit File Patterns:**
```json
{
  "tool": "Read",
  "pattern": "//path/to/**"
}
```

**Requirements:**
- Must use `//` prefix for absolute paths
- Supports glob patterns (`**`, `*`)
- No redundant permissions (e.g., `//foo/**` makes `//foo/bar/**` redundant)
- Paths must be valid and exist

**Skill Patterns:**
```json
{
  "tool": "Skill",
  "pattern": "plugin:skill-name"
}
```

**Requirements:**
- Format: `plugin:skill-name` or `bundle:skill-name:*`
- Must reference existing skill in loaded plugins
- Use `:*` suffix for all skills in a bundle

**SlashCommand Patterns:**
```json
{
  "tool": "SlashCommand",
  "pattern": "/command-name:*"
}
```

**Requirements:**
- Must start with `/`
- Use `:*` suffix for parameterized commands
- Must reference existing command in loaded plugins

**WebFetch Patterns:**
```json
{
  "tool": "WebFetch",
  "pattern": "domain:example.com"
}
```

**Requirements:**
- Must use `domain:` prefix
- Domain only (no protocol, path, or port)
- Must pass security assessment (see web-security-standards skill)
- No wildcard domains (e.g., `domain:*.com` is invalid)

### Structural Validation

**No Duplicates:**
- Same tool + same pattern = duplicate (remove)
- For redundancy detection logic and algorithms, see [permission-anti-patterns.md](permission-anti-patterns.md#detection-algorithms)

**Proper Organization:**
- Group by tool type
- Order within tool type: specific before broad, alphabetical
- Consistent formatting and spacing

**Security Validation:**
- No overly permissive patterns without justification
- WebFetch domains must be vetted (see `web-security-standards` skill: domain-security-assessment.md and trusted-domains.md)
- File access patterns must be scoped appropriately
- Bash commands must be safe operations

## Common Validation Issues

### Issue 1: Duplicate Permissions

**Problem:**
```json
{"tool": "Bash", "pattern": "git:*"},
{"tool": "Bash", "pattern": "git:status"}
```

**Fix:** Remove the specific permission (second one) as it's covered by the wildcard.

### Issue 2: Incorrect Path Format

**Problem:**
```json
{"tool": "Read", "pattern": "/Users/oliver/project/**"}
```

**Fix:** Use `//` prefix for absolute paths:
```json
{"tool": "Read", "pattern": "//Users/oliver/project/**"}
```

### Issue 3: Malformed Bash Pattern

**Problem:**
```json
{"tool": "Bash", "pattern": "git*"}
{"tool": "Bash", "pattern": "git:**"}
```

**Fix:** Use correct format with colon:
```json
{"tool": "Bash", "pattern": "git:*"}
```

### Issue 4: Redundant Permissions

**Problem:**
```json
{"tool": "Read", "pattern": "//project/**"},
{"tool": "Read", "pattern": "//project/src/**"},
{"tool": "Read", "pattern": "//project/tests/**"}
```

**Fix:** Keep only the broadest pattern:
```json
{"tool": "Read", "pattern": "//project/**"}
```

### Issue 5: WebFetch with Protocol

**Problem:**
```json
{"tool": "WebFetch", "pattern": "domain:https://docs.example.com"}
```

**Fix:** Domain only, no protocol:
```json
{"tool": "WebFetch", "pattern": "domain:docs.example.com"}
```

### Issue 6: Skill Format Variations

**Problem:**
```json
{"tool": "Skill", "pattern": "my-skill"},
{"tool": "Skill", "pattern": "plugin/my-skill"},
{"tool": "Skill", "pattern": "bundle:my-bundle:my-skill"}
```

**Fix:** Use consistent plugin format:
```json
{"tool": "Skill", "pattern": "plugin:my-skill"}
```
Or bundle wildcard:
```json
{"tool": "Skill", "pattern": "bundle:my-bundle:*"}
```

**For validation implementation**, see:
- Format validation examples in sections above
- **[permission-architecture.md](permission-architecture.md#permission-scope-examples)** for comprehensive scoping examples and global/local separation guidance
- [permission-anti-patterns.md](permission-anti-patterns.md) for common issues to check
- [best-practices/lessons-learned.md](best-practices/lessons-learned.md) for validation workflow

## Permission Scoping Best Practices

### File Access Scoping

**Too Broad (Avoid):**
```json
{"tool": "Read", "pattern": "//**"}
```

**Appropriately Scoped:**
```json
{"tool": "Read", "pattern": "//~/git/project/**"},
{"tool": "Read", "pattern": "//.claude/**"}
```

### Bash Command Scoping

**Too Broad (Avoid):**
```json
{"tool": "Bash", "pattern": "**"}
```

**Appropriately Scoped:**
```json
{"tool": "Bash", "pattern": "git:*"},
{"tool": "Bash", "pattern": "npm:*"},
{"tool": "Bash", "pattern": "ls:*"}
```

### WebFetch Scoping

**Never Use (Invalid):**
```json
{"tool": "WebFetch", "pattern": "domain:*"}
```

**Appropriately Scoped:**
```json
{"tool": "WebFetch", "pattern": "domain:docs.anthropic.com"},
{"tool": "WebFetch", "pattern": "domain:api.github.com"}
```

## Automated Validation Rules

### Rule 1: Pattern Format
- `Bash`: Must match `^[a-zA-Z0-9_-]+:\*$`
- `Read/Write/Edit`: Must start with `//` or be relative path
- `Skill`: Must match `^(plugin|bundle):[a-zA-Z0-9_-]+(:[a-zA-Z0-9_-]+)?(\*)?$`
- `SlashCommand`: Must match `^/[a-zA-Z0-9_-]+(:\*)?$`
- `WebFetch`: Must match `^domain:[a-zA-Z0-9.-]+\.[a-z]{2,}$`

### Rule 2: Duplication Detection
```
For tool T and patterns P1, P2:
  If P1 == P2: Duplicate (remove P2)
  If P1 is glob and P2 matches P1: Redundant (remove P2)
```

### Rule 3: Security Requirements
```
For WebFetch permissions:
  - Domain must pass security assessment
  - Domain must have legitimate use case
  - Domain must be documented with purpose
```

### Rule 4: Path Validation
```
For file access permissions:
  - Path must exist or be valid glob pattern
  - No circular or symbolic link issues
  - Appropriate scope for use case
```

## Maintenance Procedures

### Regular Audits
- Review permissions quarterly
- Remove unused permissions
- Update patterns as project structure changes
- Validate security of approved domains

### Change Management
- Document reason when adding new permission
- Review before committing to version control
- Test that permission is necessary
- Remove when feature/need is removed

### Documentation Requirements
- Comment complex or non-obvious permissions
- Group related permissions with headers
- Document why broad patterns are necessary
- Link to security assessments for WebFetch domains
