# Permission Anti-Patterns

## Suspicious Permission Patterns

### System Temp Directories
- `Read(//tmp/**)`, `Write(//tmp/**)`
- `Read(//private/tmp/**)`
- Any permission accessing `/tmp` or `/private/tmp`

### Critical System Directories
- `/dev/**` - Device files (disks, terminals, CPU)
- `/sys/**` - System information
- `/proc/**` - Process information
- `/etc/**` - System configuration
- `/boot/**` - Boot files
- `/root/**` - Root user home

### Overly Broad Wildcards
- `Read(//Users/**)` - All user files
- `Read(//\*\*)` - Entire filesystem
- `Bash(*)` - All commands

### Dangerous Commands
- `Bash(rm:*)` without specific path
- `Bash(sudo:*)`
- `Bash(chmod:*)`
- `Bash(dd:*)`

### Malformed Patterns
- Absolute paths without user-relative format (`/Users/oliver/` instead of `~/`)
- Missing wildcards where needed
- Empty patterns

### Redundant Patterns
- Specific pattern covered by broader pattern
- Example: `Read(//~/git/project/src/**)` when `Read(//~/git/project/**)` exists
- Local permissions duplicating global permissions

## Detection Algorithms

### Algorithm 1: System Directory Detection

**Pattern matching for critical system paths:**

```python
CRITICAL_SYSTEM_PATHS = [
    r'/dev/.*',
    r'/sys/.*',
    r'/proc/.*',
    r'/etc/.*',
    r'/boot/.*',
    r'/root/.*',
    r'/bin/.*',
    r'/sbin/.*',
    r'/usr/bin/.*',
    r'/usr/sbin/.*'
]

def detect_system_directory_access(permission):
    """Detect permissions accessing critical system directories."""
    path = extract_path_from_permission(permission)
    for pattern in CRITICAL_SYSTEM_PATHS:
        if re.match(pattern, path):
            return {
                'violation': 'SYSTEM_DIRECTORY_ACCESS',
                'severity': 'HIGH',
                'path': path,
                'pattern': pattern,
                'recommendation': 'Remove permission - system directories should never be accessed'
            }
    return None
```

### Algorithm 2: Temp Directory Detection

**Pattern matching for temporary directories:**

```python
TEMP_DIRECTORY_PATTERNS = [
    r'.*//tmp/.*',
    r'.*//private/tmp/.*',
    r'.*/var/tmp/.*',
    r'Read\(//tmp/\*\*\)',
    r'Write\(//tmp/\*\*\)'
]

def detect_temp_directory_access(permission):
    """Detect permissions accessing temp directories."""
    for pattern in TEMP_DIRECTORY_PATTERNS:
        if re.match(pattern, permission):
            return {
                'violation': 'TEMP_DIRECTORY_ACCESS',
                'severity': 'MEDIUM',
                'permission': permission,
                'recommendation': 'Use project-specific temp directory instead'
            }
    return None
```

### Algorithm 3: Overly Broad Wildcard Detection

**Pattern matching for dangerous wildcards:**

```python
BROAD_WILDCARD_PATTERNS = [
    (r'Read\(//\*\*\)', 'Entire filesystem'),
    (r'Read\(//Users/\*\*\)', 'All user files'),
    (r'Read\(//home/\*\*\)', 'All user files (Linux)'),
    (r'Write\(//\*\*\)', 'Entire filesystem'),
    (r'Bash\(\*\)', 'All bash commands')
]

def detect_overly_broad_wildcards(permission):
    """Detect dangerously broad wildcard patterns."""
    for pattern, description in BROAD_WILDCARD_PATTERNS:
        if re.match(pattern, permission):
            return {
                'violation': 'OVERLY_BROAD_WILDCARD',
                'severity': 'HIGH',
                'permission': permission,
                'scope': description,
                'recommendation': 'Narrow to specific directories or files needed'
            }
    return None
```

### Algorithm 4: Dangerous Command Detection

**Pattern matching for risky bash commands:**

```python
DANGEROUS_COMMANDS = {
    'rm': 'File deletion - require specific paths',
    'sudo': 'Privilege escalation - prohibited',
    'chmod': 'Permission changes - require specific files',
    'chown': 'Ownership changes - require specific files',
    'dd': 'Disk operations - prohibited',
    'mkfs': 'Filesystem creation - prohibited',
    'fdisk': 'Disk partitioning - prohibited'
}

def detect_dangerous_commands(permission):
    """Detect dangerous bash command patterns."""
    if not permission.startswith('Bash('):
        return None

    # Extract command
    match = re.match(r'Bash\(([^:]+):\*\)', permission)
    if match:
        command = match.group(1)
        if command in DANGEROUS_COMMANDS:
            return {
                'violation': 'DANGEROUS_COMMAND',
                'severity': 'HIGH',
                'command': command,
                'reason': DANGEROUS_COMMANDS[command],
                'permission': permission,
                'recommendation': f'Either remove or restrict to specific paths/arguments'
            }
    return None
```

### Algorithm 5: Redundancy Detection

**Check for permissions covered by broader patterns:**

```python
def detect_redundant_permissions(permission, all_permissions):
    """Detect permissions that are redundant with broader patterns."""
    redundancies = []

    for other in all_permissions:
        if other == permission:
            continue

        # Check if 'other' is broader and covers 'permission'
        if is_broader_pattern(other, permission):
            redundancies.append({
                'violation': 'REDUNDANT_PERMISSION',
                'severity': 'LOW',
                'redundant': permission,
                'covered_by': other,
                'recommendation': f'Remove {permission} (covered by {other})'
            })

    return redundancies if redundancies else None

def is_broader_pattern(broader, specific):
    """Check if 'broader' pattern covers 'specific' pattern."""
    # Example: Read(//~/git/project/**) covers Read(//~/git/project/src/**)
    # Implementation depends on permission format
    # This is a simplified check
    if specific.startswith(broader.rstrip('*')):
        return True
    return False
```

### Algorithm 6: Path Format Validation

**Detect malformed path formats:**

```python
def detect_path_format_issues(permission):
    """Detect path format issues (absolute vs user-relative)."""
    issues = []

    # Check for absolute paths that should be user-relative
    if re.search(r'/Users/[^/]+/', permission):
        issues.append({
            'violation': 'ABSOLUTE_PATH_INSTEAD_OF_RELATIVE',
            'severity': 'LOW',
            'permission': permission,
            'recommendation': 'Use ~/ instead of /Users/username/'
        })

    # Check for empty patterns
    if permission.endswith('()'):
        issues.append({
            'violation': 'EMPTY_PATTERN',
            'severity': 'MEDIUM',
            'permission': permission,
            'recommendation': 'Remove empty permission or specify pattern'
        })

    return issues if issues else None
```

## Severity Scoring

### Scoring Formula

Each violation is scored based on multiple factors:

```python
def calculate_severity_score(violation):
    """Calculate numerical severity score (0-100)."""
    base_scores = {
        'SYSTEM_DIRECTORY_ACCESS': 100,
        'DANGEROUS_COMMAND': 90,
        'OVERLY_BROAD_WILDCARD': 80,
        'TEMP_DIRECTORY_ACCESS': 50,
        'REDUNDANT_PERMISSION': 20,
        'ABSOLUTE_PATH_INSTEAD_OF_RELATIVE': 10,
        'EMPTY_PATTERN': 30
    }

    score = base_scores.get(violation['violation'], 0)

    # Adjust for context
    if 'Write' in violation.get('permission', ''):
        score += 10  # Write is more dangerous than Read

    if 'global' in violation.get('scope', ''):
        score += 15  # Global permissions are riskier

    return min(score, 100)
```

### Risk Categories

Based on severity score:
- **CRITICAL** (90-100): Immediate security risk - block or remove
- **HIGH** (70-89): Significant risk - requires review and justification
- **MEDIUM** (40-69): Moderate risk - should be addressed
- **LOW** (0-39): Minor issue - optional cleanup

## Remediation Guidance

### Fix Strategy 1: Remove Dangerous Permissions

**For CRITICAL and HIGH severity violations:**

```
BEFORE:
Bash(sudo:*)

AFTER:
[REMOVED] - sudo access is prohibited
```

### Fix Strategy 2: Narrow Overly Broad Wildcards

**Replace broad patterns with specific paths:**

```
BEFORE:
Read(//Users/**)

AFTER:
Read(//~/git/project-name/**)
```

### Fix Strategy 3: Convert Absolute to Relative Paths

**Use user-relative paths:**

```
BEFORE:
Read(///Users/oliver/git/project/**)

AFTER:
Read(//~/git/project/**)
```

### Fix Strategy 4: Remove Redundant Permissions

**Eliminate permissions covered by broader patterns:**

```
BEFORE:
Read(//~/git/project/**)
Read(//~/git/project/src/**)
Read(//~/git/project/test/**)

AFTER:
Read(//~/git/project/**)
[REMOVED redundant src and test patterns]
```

### Fix Strategy 5: Replace Temp Directory Access

**Use project-specific directories:**

```
BEFORE:
Write(//tmp/**)

AFTER:
Write(//~/git/project/target/temp/**)
```

### Fix Strategy 6: Add Path Restrictions to Commands

**Narrow dangerous commands to specific paths:**

```
BEFORE:
Bash(rm:*)

AFTER:
Bash(rm:target/*)  # Only allow deletion in build output directory
```

## Integration with Validation Workflow

### Validation Sequence

1. **Run all detection algorithms** on each permission
2. **Calculate severity scores** for all violations
3. **Sort by severity** (highest first)
4. **Group by category** (system access, commands, paths, etc.)
5. **Generate remediation report** with specific fixes
6. **Block CRITICAL violations** from being added
7. **Warn on HIGH violations** requiring justification
8. **Report MEDIUM/LOW** for cleanup

### Automated Enforcement

```python
def validate_permissions(permissions):
    """Validate all permissions and return violations."""
    all_violations = []

    for permission in permissions:
        # Run all detection algorithms
        violations = [
            detect_system_directory_access(permission),
            detect_temp_directory_access(permission),
            detect_overly_broad_wildcards(permission),
            detect_dangerous_commands(permission),
            detect_path_format_issues(permission)
        ]

        # Add redundancy check
        redundant = detect_redundant_permissions(permission, permissions)
        if redundant:
            violations.extend(redundant)

        # Filter out None results and add scores
        for violation in filter(None, violations):
            violation['score'] = calculate_severity_score(violation)
            all_violations.append(violation)

    return sorted(all_violations, key=lambda v: v['score'], reverse=True)
```

## Security Risk Assessment

### HIGH RISK (Score 70-100)
- System directory access (`/etc`, `/dev`, `/sys`, `/proc`, `/boot`, `/root`)
- Dangerous commands without restrictions (`sudo`, `dd`, `mkfs`, `fdisk`)
- Overly broad wildcards (entire filesystem, all users)
- Write access to system paths

**Action**: Block or require security team approval

### MEDIUM RISK (Score 40-69)
- Temp directory access (`/tmp`, `/private/tmp`)
- Moderately broad wildcards
- Dangerous commands with some restrictions
- Redundant permissions (maintenance risk)

**Action**: Require justification and review

### LOW RISK (Score 0-39)
- Path format issues (absolute vs relative)
- Minor redundancies
- Empty patterns
- Stylistic inconsistencies

**Action**: Recommend cleanup, non-blocking

## Examples

### Example 1: System Directory Violation

```
Permission: Read(//etc/**)
Violation: SYSTEM_DIRECTORY_ACCESS
Severity: CRITICAL (100)
Recommendation: Remove - system configuration should never be accessed
Fix: [REMOVE PERMISSION]
```

### Example 2: Overly Broad Wildcard

```
Permission: Read(//Users/**)
Violation: OVERLY_BROAD_WILDCARD
Severity: HIGH (80)
Scope: All user files
Recommendation: Narrow to specific project directory
Fix: Read(//~/git/specific-project/**)
```

### Example 3: Dangerous Command

```
Permission: Bash(rm:*)
Violation: DANGEROUS_COMMAND
Severity: HIGH (90)
Recommendation: Restrict to specific paths
Fix: Bash(rm:target/*)
```

### Example 4: Redundancy

```
Permissions:
  - Read(//~/git/project/**)
  - Read(//~/git/project/src/**)
Violation: REDUNDANT_PERMISSION
Severity: LOW (20)
Recommendation: Remove specific pattern
Fix: Keep only Read(//~/git/project/**), remove Read(//~/git/project/src/**)
```

