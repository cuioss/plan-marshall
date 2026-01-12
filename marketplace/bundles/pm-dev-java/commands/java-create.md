---
name: java-create
description: Interactive wizard for creating Java components with standards compliance
tools: Read, Write, Glob, Task, AskUserQuestion, Skill
---

# Java Create Command

Interactive wizard for creating Java components (classes, services, tests) with CUI standards compliance.

## PARAMETERS

- **type** (optional): Component type - class, service, test, enum, interface
- **name** (optional): Component name

## WORKFLOW

### Step 1: Gather Requirements

If parameters not provided, use AskUserQuestion:

```
AskUserQuestion:
  questions:
    - question: "What type of Java component do you want to create?"
      header: "Type"
      options:
        - label: "Service"
          description: "Business service with CDI injection"
        - label: "Data Class"
          description: "Immutable data carrier (record or @Value)"
        - label: "Interface"
          description: "Contract definition"
        - label: "Test"
          description: "Unit test for existing class"
      multiSelect: false
```

If type is "Test", ask for target class:
```
AskUserQuestion:
  questions:
    - question: "Which class do you want to test?"
      header: "Target"
      options:
        - label: "Enter class name"
          description: "I'll search for the class"
      multiSelect: false
```

### Step 2: Determine Location

Ask about package/location:

```
AskUserQuestion:
  questions:
    - question: "Where should this component be created?"
      header: "Package"
      options:
        - label: "Auto-detect"
          description: "Based on existing package structure"
        - label: "Specify"
          description: "I'll provide the package"
      multiSelect: false
```

### Step 3: Load Standards

```
Skill: pm-dev-java:java-core
```

Load appropriate standards based on component type:
- Service → java-core-patterns.md, java-null-safety.md, logging-standards.md
- Data Class → java-lombok-patterns.md, java-null-safety.md
- Interface → java-core-patterns.md
- Test → Load testing skill

### Step 4: Generate Component

Based on type, delegate to appropriate agent:

**For Service/Class/Interface/Enum:**
```
Task:
  subagent_type: pm-dev-java:java-implement-agent
  description: Create {type}
  prompt: |
    Create new {type} with name {name}.
    Package: {determined_package}
    Apply all loaded standards.

    Return structured result.
```

**For Test:**
```
Task:
  subagent_type: pm-dev-java:java-implement-tests-agent
  description: Create test
  prompt: |
    Create unit tests for class {target_class}.
    coverage_target=80

    Return structured result.
```

### Step 5: Verify Build

```
Skill: pm-dev-builder:builder-maven-rules
Workflow: Execute Maven Build
Parameters:
  goals: clean compile
  output_mode: errors
```

### Step 6: Confirm and Report

```
╔════════════════════════════════════════════════════════════╗
║       Java Component Created                                ║
╚════════════════════════════════════════════════════════════╝

Type: {type}
Name: {name}
Package: {package}
File: {file_path}

Standards Applied:
{list of standards applied}

Build Status: {SUCCESS/FAILURE}

Next Steps:
- Review the generated code
- Add business logic implementation
- Run tests: ./mvnw test
```

## COMPONENT TEMPLATES

### Service Template
```java
@NullMarked
package {package};

import de.cuioss.tools.logging.CuiLogger;
import jakarta.enterprise.context.ApplicationScoped;
import jakarta.inject.Inject;

/**
 * {Description from user or generated}.
 */
@ApplicationScoped
public class {Name}Service {

    private static final CuiLogger LOGGER = new CuiLogger({Name}Service.class);

    // Business logic here
}
```

### Data Class Template
```java
@NullMarked
package {package};

import lombok.Builder;
import lombok.Value;

/**
 * {Description from user or generated}.
 */
@Value
@Builder
public class {Name} {
    // Fields here
}
```

## ERROR HANDLING

- If package detection fails → Ask user for package
- If name conflicts → Suggest alternatives
- If build fails → Offer to fix or rollback

## USAGE EXAMPLES

```
# Interactive mode
/java-create

# Create service directly
/java-create type=service name=TokenValidator

# Create test for existing class
/java-create type=test name=TokenValidatorTest
```

## CONTINUOUS IMPROVEMENT RULE

If you discover issues or improvements during execution, record them:

1. **Activate skill**: `Skill: plan-marshall:manage-lessons-learned`
2. **Record lesson** with:
   - Component: `{type: "command", name: "java-create", bundle: "pm-dev-java"}`
   - Category: bug | improvement | pattern | anti-pattern
   - Summary and detail of the finding
