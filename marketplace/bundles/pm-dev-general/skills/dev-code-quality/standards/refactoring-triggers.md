# Refactoring Triggers

Language-agnostic criteria for identifying when code needs refactoring, based on measurable metrics and observable patterns.

## Purpose

This document defines WHEN to refactor by identifying violations and triggering conditions. It provides systematic detection criteria independent of any specific programming language.

## Code Organization Triggers

### Single Responsibility Violations

**Trigger**: Class/module has multiple unrelated responsibilities.

**Detection:**
* Classes > 500 lines
* Classes with too many methods (> 20)
* Classes handling multiple domains
* Difficulty summarizing class purpose in one sentence

**Action:** Split into focused classes following SRP.

### Package/Module Structure Problems

**Trigger**: Code organized by technical layer instead of feature.

**Detection:**
* Layer-based directory structure (controllers/, services/, models/)
* Changes to one feature require touching many directories
* Related classes scattered across packages

**Action:** Restructure to feature-based packages.

## Method Design Triggers

### Long Methods

**Trigger**: Methods over 50 lines, or methods with complex logic regardless of line count.

**Detection:**
* Methods with multiple levels of nesting
* Methods doing multiple unrelated things
* Methods with more than one clear responsibility
* Difficulty describing what the method does in one sentence

**Action:** Extract methods per code organization standards.

**Note:** Line count is secondary to single responsibility — a focused 70-line method may be acceptable, while a 45-line method doing multiple things requires refactoring.

### High Cyclomatic Complexity

**Trigger**: Methods with complexity > 15.

**Detection:**
* Count decision points: if, for, while, case, &&, ||
* Use static analysis tools (SonarQube, ESLint, etc.)
* Methods with many conditional branches

**Action:** Simplify logic, extract sub-methods, use polymorphism.

### Too Many Parameters

**Trigger**: Methods with 3+ parameters without parameter objects.

**Detection:**
* Count method parameters
* Identify methods with similar parameter groups across the codebase

**Action:** Create parameter objects.

**Exception:** Parameters representing a cohesive concept (e.g., coordinates x, y, z) or simple configuration.

### Command-Query Separation Violations

**Trigger**: Methods that both query and modify state.

**Detection:**
* Methods that return values AND modify state
* Getters with side effects
* "Get-and-set" operations without clear justification

**Action:** Separate into distinct command and query methods.

## Complexity Triggers

### Deep Nesting

**Trigger**: More than 3 levels of nesting (if/for/while/try within if/for/while/try).

**Detection:** Visual inspection of indentation, deeply indented blocks.

**Action:** Use guard clauses (early returns), extract nested blocks into helper methods.

```
// TRIGGER: 4 levels of nesting
if (valid) {
    for (item in items) {
        if (item.isActive) {
            if (item.hasPermission) {
                // deeply nested code
            }
        }
    }
}

// RESOLVED: guard clauses + extraction
if (!valid) return
for (item in items) {
    processActiveItem(item)
}
```

### Complex Boolean Expressions

**Trigger**: Conditions with 3+ boolean operators that are hard to parse.

**Detection:** Conditions spanning multiple lines, conditions with mix of &&, ||, and !.

**Action:** Extract into well-named boolean methods or variables.

```
// TRIGGER: Complex inline boolean
if (user != null && user.isActive && !user.isSuspended && user.hasPermission("admin"))

// RESOLVED: Named method
if (isActiveAdmin(user))
```

### Over-Abstraction

**Trigger**: Unnecessary layers of indirection.

**Detection:**
* Single-use abstractions
* Interfaces with only one implementation
* Wrapper classes adding no value
* Utility methods called from only one place

**Action:** Simplify or remove unnecessary abstraction layers. When uncertain if abstraction serves future needs, ask the user.

### Redundant Logic

**Trigger**: Code that can be simplified through Boolean algebra.

**Detection:**
* Conditions always evaluating to same value
* Double negatives
* Identical nested conditions
* Unnecessary else after return

**Examples:**
* `if (x) return true; else return false;` → `return x;`
* `if (!(!condition))` → `if (condition)`
* `if (x) { return; } else { doSomething(); }` → `if (x) return; doSomething();`

## Naming Triggers

### Poor Naming

**Trigger**: Unclear abbreviations or non-descriptive names.

**Detection:**
* Single-letter variables (except loop counters)
* Unclear abbreviations
* Generic names like "data", "info", "manager", "handler"
* Boolean variables without is/has/can prefix

**Action:** Rename to meaningful, descriptive names.

## Unused Code Triggers

### Dead Code

**Trigger**: Code that is never executed or called.

**Detection:** IDE warnings, static analysis tools, unreachable code paths.

**Action:** Remove after verification. Request user approval for public/protected elements.

**Do NOT remove when:**
* Framework dependencies may require "unused" methods
* Methods may be called via reflection
* Code prepared for upcoming features (ask user)
* Public API needed for backward compatibility

## Duplication Triggers

### Copy-Paste Code

**Trigger**: Same or very similar logic repeated in multiple places.

**Detection:**
* Identical code blocks in different methods
* Similar methods differing only in a few lines
* Same validation logic in multiple entry points

**Action:** Extract into shared method/function, use template patterns for structural similarity.

## Maintenance Prioritization

### High Priority

* Security vulnerabilities
* Public API contract issues
* Fundamental design problems (SRP violations, god classes)
* Error handling gaps in critical paths

### Medium Priority

* Long methods (> 50 lines)
* High complexity (> 15)
* Legacy patterns that could use modern language features
* Unused code and dead code

### Low Priority

* Style inconsistencies
* Minor documentation improvements
* Speculative performance optimizations without measured bottleneck

### Decision Guide

```
Security vulnerability?
├─> YES: HIGH (always)

Public API contract issue?
├─> YES: HIGH

Fundamental design problem (SRP, structure)?
├─> YES: HIGH

Method-level design issue (length, complexity)?
├─> YES: MEDIUM

Unused code or legacy patterns?
├─> YES: MEDIUM

Style or speculative optimization?
└─> YES: LOW (defer or batch)
```
