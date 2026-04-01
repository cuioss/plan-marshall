# File Operations Patterns

Patterns for file and directory operations using non-prompting tools. Never use Bash for file operations.

## File Existence

**Single file** -- use Read with error handling (also gives you the content):
```
Read(file_path="/path/to/file")
# Handle error gracefully if file doesn't exist
```

**Quick existence check** -- use Glob (no content loaded):
```
Glob(pattern="filename", path="/parent/directory")
# Empty result means file doesn't exist
```

**Multiple required files:**
```
required = ["plugin.json", "README.md", "SKILL.md"]
# Glob or Read each, collect missing files, report summary
```

## Directory Existence

Use Glob to check if a directory has contents:
```
Glob(pattern="*", path="/path/to/directory")
# Empty result = directory empty or doesn't exist
```

## File Discovery

**Find files by extension:**
```
Glob(pattern="**/*.md", path="/bundle/path")
```

**Find files in specific directory:**
```
Glob(pattern="*.md", path="/bundle/agents")
```

**Multiple extensions:**
```
md_files = Glob(pattern="*.md", path="/path")
adoc_files = Glob(pattern="*.adoc", path="/path")
```

## Content Validation

**Validate frontmatter exists:**
```
content = Read(file_path="/path/to/file")
# Check starts with "---", find closing "---"
# Extract and validate required fields (name, description)
```

**Batch validate components:**
```
files = Glob(pattern="*.md", path="/bundle/agents")
# For each: Read, validate frontmatter, collect results
# Report summary: valid/invalid counts
```

## Manifest vs Filesystem Comparison

Check that plugin.json component lists match actual files:
```
# Read plugin.json, extract listed components
# Glob actual files in agents/, commands/, skills/
# Compare: find missing (listed but not found) and unlisted (found but not listed)
```

## Error Handling

Always handle missing files gracefully -- Read may fail, Glob returns empty lists. Use try/except for Read, check list length for Glob. Build validation reports with pass/fail/warn categories.

## Key Rules

1. **Read + try/except** for file existence when you need content
2. **Glob** for quick existence checks and discovery
3. **Never Bash** for file operations (find, ls, test -f, cat)
4. Validate files as you discover them
5. Handle errors gracefully with defaults
