# Content Search Operations Patterns

Detailed patterns for searching file content using Grep in diagnostic commands.

## Basic Search Patterns

### Pattern: Find Files Containing Text

**Use Case**: Find which files contain a specific pattern (e.g., which agents use a skill)

```python
# Find files containing "Skill: cui-javadoc"
matches = Grep(
    pattern="Skill: cui-javadoc",
    path="/bundle/path/agents",
    output_mode="files_with_matches"
)

# Result: ["/bundle/path/agents/agent1.md", "/bundle/path/agents/agent2.md"]

print(f"Found {len(matches)} agents using cui-javadoc skill:")
for file_path in matches:
    agent_name = file_path.split("/")[-1].replace(".md", "")
    print(f"  - {agent_name}")
```

### Pattern: Show Matching Lines with Context

**Use Case**: See actual usage of pattern with line numbers

```python
# Search with line numbers
matches = Grep(
    pattern="Skill: cui-",
    path="/bundle/path/agents/my-agent.md",
    output_mode="content",
    -n=true
)

# Result format: "filename:line:content"
# Example: "/path/agents/my-agent.md:37:Skill: cui-javadoc"

for match in matches:
    print(f"  {match}")
```

### Pattern: Count Occurrences

**Use Case**: Count how many times pattern appears

```python
# Count matches per file
match_counts = Grep(
    pattern="tools:",
    path="/bundle/path/agents",
    output_mode="count"
)

# Result: {"file1.md": 5, "file2.md": 3}

total_matches = sum(match_counts.values())
print(f"Found 'tools:' {total_matches} times across {len(match_counts)} files")
```

## Advanced Search Patterns

### Pattern: Multi-Pattern Search (OR)

**Use Case**: Find files containing any of several patterns

```python
# Search for multiple skill references using regex OR
matches = Grep(
    pattern="Skill: cui-javadoc|Skill: builder-maven-rules|Skill: cui-java-core",
    path="/bundle/path/agents",
    output_mode="files_with_matches"
)

print(f"Found {len(matches)} agents using CUI skills")
```

### Pattern: Extract Specific Information

**Use Case**: Find and extract command references from agents

```python
# Find SlashCommand or /cui- references
matches = Grep(
    pattern="SlashCommand|/cui-",
    path="/bundle/path/agents",
    output_mode="content",
    -n=true
)

# Parse results to extract command names
command_refs = []
for match in matches:
    # Extract command name from match line
    # Example: "agent.md:45:SlashCommand: /cui-build-and-verify"
    if "SlashCommand" in match:
        cmd = match.split("SlashCommand:")[1].strip()
        command_refs.append(cmd)
    elif "/cui-" in match:
        # Extract /cui-xxx-xxx
        parts = match.split("/cui-")
        if len(parts) > 1:
            cmd = "/cui-" + parts[1].split()[0]
            command_refs.append(cmd)

# Remove duplicates
unique_commands = list(set(command_refs))
print(f"Agents reference {len(unique_commands)} commands:")
for cmd in unique_commands:
    print(f"  - {cmd}")
```

### Pattern: Case-Insensitive Search

**Use Case**: Find pattern regardless of case

```python
# Search ignoring case
matches = Grep(
    pattern="TODO|todo|Todo",
    path="/bundle/path",
    output_mode="content",
    -i=true  # Case insensitive
)

print(f"Found {len(matches)} TODO comments")
```

### Pattern: Search with Context Lines

**Use Case**: See surrounding code around matches

```python
# Show 3 lines before and after match
matches = Grep(
    pattern="tools:",
    path="/bundle/path/agents/my-agent.md",
    output_mode="content",
    -C=3  # Context: 3 lines before and after
)

# Results show match with surrounding context
for match in matches:
    print(match)
    print("---")
```

## Integration Validation Patterns

### Pattern: Validate Agent→Command References

**Use Case**: Check if agents reference commands that exist

```python
# Step 1: Find all command references in agents
command_refs = Grep(
    pattern="/cui-",
    path="/bundle/path/agents",
    output_mode="content",
    -n=true
)

# Step 2: Extract unique command names
referenced_commands = set()
for match in command_refs:
    # Parse command name from match
    if "/cui-" in match:
        cmd_start = match.index("/cui-")
        cmd_end = match.find(" ", cmd_start)
        if cmd_end == -1:
            cmd_end = match.find(")", cmd_start)
        if cmd_end == -1:
            cmd_end = len(match)
        cmd_name = match[cmd_start:cmd_end].strip()
        referenced_commands.add(cmd_name)

# Step 3: Check which commands exist
existing_commands = Glob(pattern="*.md", path="/bundle/path/commands")
existing_cmd_names = ["/cui-" + f.split("/")[-1].replace(".md", "").replace("cui-", "") for f in existing_commands]

# Step 4: Find broken references
broken_refs = referenced_commands - set(existing_cmd_names)

if len(broken_refs) == 0:
    print("✅ All command references valid")
else:
    print(f"❌ Found {len(broken_refs)} broken command references:")
    for cmd in broken_refs:
        print(f"  - {cmd}")
```

### Pattern: Validate Agent→Skill References

**Use Case**: Check if agents reference skills that exist

```python
# Find skill references
skill_refs = Grep(
    pattern="Skill: cui-",
    path="/bundle/path/agents",
    output_mode="content",
    -n=true
)

# Extract skill names
referenced_skills = set()
for match in skill_refs:
    # Example: "agent.md:37:Skill: cui-javadoc"
    if "Skill: cui-" in match:
        skill_start = match.index("Skill: cui-") + len("Skill: ")
        skill_end = match.find(" ", skill_start)
        if skill_end == -1:
            skill_end = match.find("\n", skill_start)
        if skill_end == -1:
            skill_end = len(match)
        skill_name = match[skill_start:skill_end].strip()
        referenced_skills.add(skill_name)

# Check which skills exist in bundle
bundle_skills = Glob(pattern="*", path="/bundle/path/skills")
bundle_skill_names = [s.split("/")[-1] for s in bundle_skills]

# Find internal vs external references
internal_skills = referenced_skills & set(bundle_skill_names)
external_skills = referenced_skills - set(bundle_skill_names)

print(f"Skill Usage:")
print(f"  Internal skills: {len(internal_skills)}")
for skill in internal_skills:
    print(f"    ✅ {skill} (exists in bundle)")

print(f"  External skills: {len(external_skills)}")
for skill in external_skills:
    print(f"    ℹ️  {skill} (external dependency)")
```

### Pattern: Check Tool Declarations

**Use Case**: Verify agents declare all tools they need

```python
def check_tool_coverage(agent_path):
    """Check if agent's tools list covers all usage"""
    content = Read(file_path=agent_path)

    # Extract declared tools from frontmatter
    if content.startswith("---"):
        fm_end = content.find("---", 3)
        frontmatter = content[3:fm_end]

        # Find tools line
        declared_tools = []
        for line in frontmatter.split("\n"):
            if line.startswith("tools:"):
                tools_str = line.split("tools:")[1].strip()
                declared_tools = [t.strip() for t in tools_str.split(",")]
                break

    # Search for tool usage in workflow
    tool_patterns = {
        "Read": r"Read\(",
        "Write": r"Write\(",
        "Edit": r"Edit\(",
        "Bash": r"Bash\(",
        "Grep": r"Grep\(",
        "Glob": r"Glob\(",
        "Skill": r"Skill:",
        "Task": r"Task\("
    }

    used_tools = set()
    for tool_name, pattern in tool_patterns.items():
        matches = Grep(
            pattern=pattern,
            path=agent_path,
            output_mode="count"
        )
        if matches and matches.get(agent_path, 0) > 0:
            used_tools.add(tool_name)

    # Compare
    missing_tools = used_tools - set(declared_tools)
    unused_tools = set(declared_tools) - used_tools

    return {
        "declared": declared_tools,
        "used": list(used_tools),
        "missing": list(missing_tools),
        "unused": list(unused_tools),
        "coverage": len(used_tools - missing_tools) / len(used_tools) * 100 if used_tools else 100
    }

# Use
result = check_tool_coverage("/bundle/path/agents/my-agent.md")
if result["coverage"] == 100:
    print(f"✅ Tool coverage: 100%")
else:
    print(f"⚠️  Tool coverage: {result['coverage']:.0f}%")
    if result["missing"]:
        print(f"  Missing from tools list: {', '.join(result['missing'])}")
    if result["unused"]:
        print(f"  Declared but not used: {', '.join(result['unused'])}")
```

## Filter and Search Patterns

### Pattern: Search Only Specific File Types

**Use Case**: Search only in .md files, not .adoc

```python
# Search only .md files using glob parameter
matches = Grep(
    pattern="search_term",
    path="/path/to/directory",
    glob="*.md",  # Only search .md files
    output_mode="content"
)
```

### Pattern: Search Excluding Directories

**Use Case**: Search agents but exclude specific subdirectories

```python
# Search all agents
all_matches = Grep(
    pattern="pattern",
    path="/bundle/path/agents",
    output_mode="files_with_matches"
)

# Filter out specific subdirectories
filtered_matches = [m for m in all_matches if "/deprecated/" not in m]
```

### Pattern: Recursive Search with Filtering

**Use Case**: Search all markdown files in bundle, categorize by type

```python
# Find all markdown files
all_md = Glob(pattern="**/*.md", path="/bundle/path")

# Categorize
agents = [f for f in all_md if "/agents/" in f]
commands = [f for f in all_md if "/commands/" in f]
skills = [f for f in all_md if "/skills/" in f]
docs = [f for f in all_md if f not in agents + commands + skills]

# Search each category for pattern
for category, files in [("Agents", agents), ("Commands", commands), ("Skills", skills)]:
    matches = []
    for file_path in files:
        result = Grep(
            pattern="search_pattern",
            path=file_path,
            output_mode="files_with_matches"
        )
        if result:
            matches.extend(result)

    print(f"{category}: {len(matches)} files contain pattern")
```

## Performance Optimization Patterns

### Pattern: Search Once, Parse Multiple Times

**Use Case**: Extract multiple pieces of information from one search

```python
# Single search for all references
all_refs = Grep(
    pattern="Skill:|tools:|SlashCommand",
    path="/bundle/path/agents",
    output_mode="content",
    -n=true
)

# Parse results for different information
skill_refs = [m for m in all_refs if "Skill:" in m]
tool_decls = [m for m in all_refs if "tools:" in m]
command_refs = [m for m in all_refs if "SlashCommand" in m]

print(f"From single search:")
print(f"  - Skill references: {len(skill_refs)}")
print(f"  - Tool declarations: {len(tool_decls)}")
print(f"  - Command references: {len(command_refs)}")
```

### Pattern: Progressive Filtering

**Use Case**: Start broad, then narrow down

```python
# Step 1: Find all files with any reference
files_with_refs = Grep(
    pattern="cui-",
    path="/bundle/path",
    output_mode="files_with_matches"
)

# Step 2: For each file, get detailed matches
for file_path in files_with_refs:
    matches = Grep(
        pattern="cui-.*",
        path=file_path,
        output_mode="content",
        -n=true
    )
    analyze_matches(file_path, matches)
```

## Result Parsing Patterns

### Pattern: Parse Grep Results with Line Numbers

**Use Case**: Extract line numbers and content from Grep output

```python
# Grep with line numbers returns: "filepath:lineno:content"
matches = Grep(
    pattern="pattern",
    path="/path",
    output_mode="content",
    -n=true
)

parsed_results = []
for match in matches:
    parts = match.split(":", 2)  # Split on first 2 colons only
    if len(parts) >= 3:
        file_path = parts[0]
        line_number = int(parts[1])
        content = parts[2]
        parsed_results.append({
            "file": file_path,
            "line": line_number,
            "content": content
        })

# Group by file
by_file = {}
for result in parsed_results:
    file_path = result["file"]
    if file_path not in by_file:
        by_file[file_path] = []
    by_file[file_path].append(result)

# Report
for file_path, file_matches in by_file.items():
    print(f"{file_path}: {len(file_matches)} matches")
    for match in file_matches:
        print(f"  Line {match['line']}: {match['content']}")
```

### Pattern: Extract Structured Information

**Use Case**: Parse YAML frontmatter fields from multiple files

```python
# Find all files with "tools:" declaration
files_with_tools = Grep(
    pattern="^tools:",
    path="/bundle/path/agents",
    output_mode="content",
    -n=true
)

# Extract tool lists
agent_tools = {}
for match in files_with_tools:
    file_path = match.split(":")[0]
    content = match.split(":", 2)[2].strip()

    # Parse tool list
    tools_str = content.replace("tools:", "").strip()
    tools = [t.strip() for t in tools_str.split(",")]

    agent_name = file_path.split("/")[-1].replace(".md", "")
    agent_tools[agent_name] = tools

# Analyze
for agent_name, tools in agent_tools.items():
    print(f"{agent_name}: {len(tools)} tools")
    print(f"  {', '.join(tools)}")
```

## Summary

**Content Search Best Practices**:
1. Use Grep tool (never Bash grep)
2. Choose appropriate output_mode
3. Use -n=true to get line numbers
4. Use filters (glob, -i) to narrow results
5. Parse results systematically
6. Extract structured information
7. Validate references and integrations
8. Optimize by searching once, parsing multiple times

**Result**: Comprehensive content analysis with zero user prompts and excellent performance.
