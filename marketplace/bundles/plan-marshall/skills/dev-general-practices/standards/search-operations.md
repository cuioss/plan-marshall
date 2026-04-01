# Content Search Patterns

Patterns for searching file content using the Grep tool. Never use Bash grep/rg.

## Basic Searches

**Find files containing a pattern:**
```
Grep(pattern="search_term", path="/directory", output_mode="files_with_matches")
# Returns list of file paths
```

**Show matching lines with line numbers:**
```
Grep(pattern="pattern", path="/path", output_mode="content", -n=true)
# Returns: "filepath:lineno:content"
```

**Count occurrences:**
```
Grep(pattern="pattern", path="/path", output_mode="count")
# Returns match counts per file
```

## Advanced Searches

**Multiple patterns (OR):**
```
Grep(pattern="pattern1|pattern2|pattern3", path="/path", output_mode="files_with_matches")
```

**Case-insensitive:**
```
Grep(pattern="todo", path="/path", output_mode="content", -i=true)
```

**With context lines:**
```
Grep(pattern="pattern", path="/file", output_mode="content", -C=3)
# Shows 3 lines before and after each match
```

**Filter by file type:**
```
Grep(pattern="pattern", path="/path", glob="*.md", output_mode="content")
```

## Reference Validation

**Check cross-references exist** (e.g., agents referencing skills):
```
# Step 1: Grep for references (e.g., "Skill: skill-name")
# Step 2: Extract referenced names
# Step 3: Glob to verify referenced files exist
# Step 4: Report broken references
```

## Performance Tips

1. **Search once, parse multiple times** -- use a broad regex, then filter results in memory
2. **Progressive filtering** -- start with `files_with_matches` to find relevant files, then `content` on those files for details
3. **Use glob parameter** to restrict search to specific file types

## Key Rules

1. **Always use Grep tool**, never Bash grep/rg
2. Choose the right `output_mode` for your needs
3. Use `-n=true` when you need line numbers
4. Use filters (`glob`, `-i`) to narrow results
5. Parse structured results systematically
