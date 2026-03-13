# File Operations Patterns

Detailed patterns for file and directory operations in diagnostic commands.

## File Existence Validation

### Pattern: Check Single File Exists

**Use Case**: Verify a required file exists (e.g., plugin.json, README.md)

```python
# Method 1: Try to read (use if you need content anyway)
try:
    content = Read(file_path="/path/to/file")
    file_exists = True
    # Content is available for further processing
except Exception:
    file_exists = False
    content = None

# Report
if file_exists:
    print("✅ file exists")
else:
    print("❌ Missing: file (CRITICAL)")
```

**When to use**: Required files that will be read and validated.

```python
# Method 2: Use Glob (use if you only need existence check)
result = Glob(pattern="filename", path="/parent/directory")
file_exists = len(result) > 0

# Report
if file_exists:
    print("✅ filename exists")
else:
    print("❌ Missing: filename")
```

**When to use**: Quick existence check without needing content.

### Pattern: Check Multiple Files Exist

**Use Case**: Verify all required files are present in a bundle

```python
required_files = {
    ".claude-plugin/plugin.json": "CRITICAL",
    "README.md": "recommended"
}

missing_files = []
existing_files = []

for file_path, severity in required_files.items():
    full_path = f"{bundle_path}/{file_path}"
    try:
        Read(file_path=full_path)
        existing_files.append(file_path)
        print(f"✅ {file_path} exists")
    except Exception:
        missing_files.append((file_path, severity))
        if severity == "CRITICAL":
            print(f"❌ Missing: {file_path} (CRITICAL)")
        else:
            print(f"⚠️  Missing: {file_path} ({severity})")

# Summary
total_files = len(required_files)
present_files = len(existing_files)
print(f"\nFiles: {present_files}/{total_files} present")
```

## Directory Existence Validation

### Pattern: Check Single Directory Exists

**Use Case**: Verify a required directory exists (e.g., agents/, skills/)

```python
# Check if directory exists by listing contents
directory_name = "agents"
result = Glob(pattern=directory_name, path="/bundle/path")
directory_exists = len(result) > 0

# Report
if directory_exists:
    print(f"✅ {directory_name}/ exists")
else:
    print(f"❌ Missing: {directory_name}/ directory")
```

**Alternative: Check by trying to list contents**

```python
# Try to list contents (works even for empty directories)
try:
    contents = Glob(pattern="*", path=f"/bundle/path/{directory_name}")
    directory_exists = True  # Even if contents is empty []
except Exception:
    directory_exists = False

if directory_exists:
    is_empty = len(contents) == 0
    print(f"✅ {directory_name}/ exists ({len(contents)} items)")
    if is_empty:
        print(f"   ⚠️  Directory is empty")
else:
    print(f"❌ Missing: {directory_name}/")
```

### Pattern: Check Required Directory Structure

**Use Case**: Validate complete bundle structure

```python
required_structure = {
    ".claude-plugin": {"type": "directory", "critical": True},
    "agents": {"type": "directory", "critical": True},
    "commands": {"type": "directory", "critical": True},
    "skills": {"type": "directory", "critical": False},
}

structure_issues = 0

for item_name, config in required_structure.items():
    result = Glob(pattern=item_name, path="/bundle/path")
    exists = len(result) > 0

    if exists:
        print(f"✅ {item_name}/ exists")
    else:
        if config["critical"]:
            print(f"❌ Missing: {item_name}/ (CRITICAL)")
            structure_issues += 1
        else:
            print(f"⚠️  Missing: {item_name}/ (optional but recommended)")

print(f"\nStructure Score: {100 - (structure_issues * 25)}/100")
```

## File Discovery Patterns

### Pattern: Discover All Components

**Use Case**: Find all agents, commands, and skills in a bundle

```python
# Discover agents (*.md files in agents/)
agents = Glob(pattern="*.md", path="/bundle/path/agents")
agent_count = len(agents)

# Discover commands (*.md files in commands/)
commands = Glob(pattern="*.md", path="/bundle/path/commands")
command_count = len(commands)

# Discover skills (directories in skills/)
skill_dirs = Glob(pattern="*", path="/bundle/path/skills")
# Filter to only directories containing SKILL.md
skills = []
for skill_path in skill_dirs:
    skill_md = Glob(pattern="SKILL.md", path=skill_path)
    if len(skill_md) > 0:
        skills.append(skill_path)
skill_count = len(skills)

# Report
print(f"Component Inventory:")
print(f"- Agents: {agent_count}")
print(f"- Commands: {command_count}")
print(f"- Skills: {skill_count}")
print(f"- Total: {agent_count + command_count + skill_count}")
```

### Pattern: Discover Files Recursively

**Use Case**: Find all files of a type anywhere in bundle

```python
# Find all .md files recursively
all_md_files = Glob(pattern="**/*.md", path="/bundle/path")

# Categorize by directory
agents_files = [f for f in all_md_files if "/agents/" in f]
commands_files = [f for f in all_md_files if "/commands/" in f]
skills_files = [f for f in all_md_files if "/skills/" in f]
other_files = [f for f in all_md_files if f not in agents_files + commands_files + skills_files]

print(f"Found {len(all_md_files)} .md files:")
print(f"  - Agents: {len(agents_files)}")
print(f"  - Commands: {len(commands_files)}")
print(f"  - Skills: {len(skills_files)}")
print(f"  - Other: {len(other_files)}")
```

### Pattern: Discover Files by Multiple Extensions

**Use Case**: Find standards files in different formats

```python
# Find .md and .adoc files in standards/ directory
md_files = Glob(pattern="*.md", path="/skill/path/standards")
adoc_files = Glob(pattern="*.adoc", path="/skill/path/standards")

all_standards = md_files + adoc_files
standard_count = len(all_standards)

print(f"Standards files found: {standard_count}")
print(f"  - Markdown (.md): {len(md_files)}")
print(f"  - AsciiDoc (.adoc): {len(adoc_files)}")
```

## File Content Validation Patterns

### Pattern: Read and Validate Frontmatter

**Use Case**: Check if file has valid YAML frontmatter

```python
def validate_frontmatter(file_path):
    try:
        content = Read(file_path=file_path)

        # Check if starts with ---
        if not content.startswith("---"):
            return False, "Missing frontmatter"

        # Find end of frontmatter
        end_marker = content.find("---", 3)
        if end_marker == -1:
            return False, "Incomplete frontmatter (missing closing ---)"

        # Extract frontmatter
        frontmatter = content[3:end_marker].strip()

        # Basic validation (check for required fields)
        has_name = "name:" in frontmatter
        has_description = "description:" in frontmatter

        if not has_name:
            return False, "Missing 'name' field"
        if not has_description:
            return False, "Missing 'description' field"

        return True, "Valid frontmatter"

    except Exception as e:
        return False, f"Cannot read file: {str(e)}"

# Use pattern
file_path = "/bundle/agents/my-agent.md"
is_valid, message = validate_frontmatter(file_path)

if is_valid:
    print(f"✅ {file_path}: {message}")
else:
    print(f"❌ {file_path}: {message}")
```

### Pattern: Batch Validate Components

**Use Case**: Validate all agents/commands in a bundle

```python
# Discover all agents
agents = Glob(pattern="*.md", path="/bundle/path/agents")

# Validate each
valid_agents = []
invalid_agents = []

for agent_path in agents:
    agent_name = agent_path.split("/")[-1]
    is_valid, message = validate_frontmatter(agent_path)

    if is_valid:
        valid_agents.append(agent_name)
        print(f"✅ {agent_name}: valid")
    else:
        invalid_agents.append((agent_name, message))
        print(f"❌ {agent_name}: {message}")

# Summary
total = len(agents)
valid_count = len(valid_agents)
print(f"\nValidation Summary:")
print(f"  Total agents: {total}")
print(f"  Valid: {valid_count}")
print(f"  Invalid: {len(invalid_agents)}")
print(f"  Success rate: {(valid_count/total*100):.0f}%")
```

## Unexpected File Detection

### Pattern: Find Unexpected Files

**Use Case**: Detect files that shouldn't be in bundle root

```python
# List all items in bundle root
all_items = Glob(pattern="*", path="/bundle/path")

# List hidden items
hidden_items = Glob(pattern=".*", path="/bundle/path")

# Define expected items
expected_items = {
    ".claude-plugin",
    "agents",
    "commands",
    "skills",
    "README.md"
}

# Define known bad patterns
bad_patterns = [
    ".DS_Store",
    "node_modules",
    ".idea",
    ".vscode",
    ".tmp",
    ".bak",
    "~"
]

# Find unexpected items
unexpected = []
for item in all_items + hidden_items:
    item_name = item.split("/")[-1]

    # Skip expected items
    if item_name in expected_items:
        continue

    # Check bad patterns
    for pattern in bad_patterns:
        if pattern in item_name:
            unexpected.append((item_name, "should be in .gitignore"))
            break

# Report
if len(unexpected) == 0:
    print("✅ No unexpected files found")
else:
    print("⚠️  Unexpected files found:")
    for item_name, reason in unexpected:
        print(f"  - {item_name} ({reason})")
```

## Component Inventory Comparison

### Pattern: Compare Manifest vs Actual

**Use Case**: Verify plugin.json component list matches reality

```python
# Read plugin.json
manifest_content = Read(file_path="/bundle/path/.claude-plugin/plugin.json")
import json
manifest = json.loads(manifest_content)

# Get listed components from manifest
listed_agents = manifest.get("components", {}).get("agents", [])
listed_commands = manifest.get("components", {}).get("commands", [])
listed_skills = manifest.get("components", {}).get("skills", [])

# Discover actual components
actual_agents = Glob(pattern="*.md", path="/bundle/path/agents")
actual_agent_names = [f.split("/")[-1].replace(".md", "") for f in actual_agents]

actual_commands = Glob(pattern="*.md", path="/bundle/path/commands")
actual_command_names = [f.split("/")[-1].replace(".md", "") for f in actual_commands]

actual_skills = Glob(pattern="*", path="/bundle/path/skills")
actual_skill_names = [f.split("/")[-1] for f in actual_skills]

# Compare
def compare_lists(listed, actual, component_type):
    listed_count = len(listed)
    actual_count = len(actual)

    if listed_count == actual_count:
        print(f"✅ {component_type}: manifest lists {listed_count}, found {actual_count} (matches)")
    else:
        print(f"⚠️  {component_type}: manifest lists {listed_count}, found {actual_count} (mismatch)")

        # Find missing (in manifest but not found)
        missing = set(listed) - set(actual)
        if missing:
            print(f"   Missing from filesystem: {', '.join(missing)}")

        # Find unlisted (found but not in manifest)
        unlisted = set(actual) - set(listed)
        if unlisted:
            print(f"   Not in manifest: {', '.join(unlisted)}")

compare_lists(listed_agents, actual_agent_names, "Agents")
compare_lists(listed_commands, actual_command_names, "Commands")
compare_lists(listed_skills, actual_skill_names, "Skills")
```

## Error Handling Strategies

### Graceful File Access

```python
def safe_read_file(file_path, default=None):
    """Safely read file, return default if not found"""
    try:
        return Read(file_path=file_path)
    except Exception:
        return default

# Use
content = safe_read_file("/path/to/file.md", default="")
if content:
    process_content(content)
else:
    print("File not found or empty")
```

### Graceful Directory Access

```python
def safe_list_directory(dir_path, pattern="*"):
    """Safely list directory contents, return empty list if not found"""
    try:
        return Glob(pattern=pattern, path=dir_path)
    except Exception:
        return []

# Use
files = safe_list_directory("/path/to/dir", pattern="*.md")
file_count = len(files)
print(f"Found {file_count} files")
```

### Validation with Detailed Reporting

```python
def validate_bundle_structure(bundle_path):
    """Validate bundle with detailed reporting"""
    results = {
        "valid": True,
        "issues": [],
        "warnings": []
    }

    # Check required directories
    required_dirs = [".claude-plugin", "agents", "commands"]
    for dir_name in required_dirs:
        result = Glob(pattern=dir_name, path=bundle_path)
        if len(result) == 0:
            results["valid"] = False
            results["issues"].append(f"Missing required directory: {dir_name}/")

    # Check required files
    try:
        Read(file_path=f"{bundle_path}/.claude-plugin/plugin.json")
    except Exception:
        results["valid"] = False
        results["issues"].append("Missing plugin.json")

    try:
        Read(file_path=f"{bundle_path}/README.md")
    except Exception:
        results["warnings"].append("Missing README.md")

    return results

# Use
validation = validate_bundle_structure("/path/to/bundle")
if validation["valid"]:
    print("✅ Bundle structure valid")
    if validation["warnings"]:
        print("⚠️  Warnings:")
        for warning in validation["warnings"]:
            print(f"  - {warning}")
else:
    print("❌ Bundle structure invalid")
    for issue in validation["issues"]:
        print(f"  - {issue}")
```

## Summary

**File Operations Best Practices**:
1. Use Read + try/except for file existence when you need content
2. Use Glob for quick existence checks
3. Use Glob for directory listing and discovery
4. Validate files as you discover them
5. Build comprehensive validation reports
6. Handle errors gracefully with defaults
7. Compare manifests vs reality for inventory
8. Detect unexpected files proactively

**Result**: Robust, error-tolerant diagnostic operations with zero user prompts.
