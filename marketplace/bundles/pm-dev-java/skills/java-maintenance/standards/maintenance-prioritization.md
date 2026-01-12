# Maintenance Prioritization Framework

Framework for prioritizing refactoring and maintenance work based on impact and urgency.

## Purpose

This document defines how to prioritize identified code violations and maintenance tasks. It ensures high-impact improvements are addressed first while maintaining code stability.

## Prioritization Overview

Systematic prioritization ensures:
- Critical issues are addressed first
- Resources are allocated effectively
- Technical debt is managed strategically
- Maintenance work has measurable impact

## High Priority - Critical Standards Violations

### API Contract Issues

**Characteristics**:
- Affect external or public interfaces
- Risk of runtime failures
- Contract violations causing bugs
- Impact system reliability

**Examples**:
- Missing `@NonNull` annotations on public APIs
- Inconsistent null safety patterns
- Poor error handling and exception design
- Violation of Command-Query Separation

**Why High Priority**:
- Direct impact on API consumers
- Can cause runtime NullPointerExceptions
- Difficult to change once in production
- Breaking changes if fixed later

### Code Organization Problems

**Characteristics**:
- Fundamental design issues
- Make codebase difficult to maintain
- Increase risk of bugs
- Block other improvements

**Examples**:
- Single Responsibility Principle violations
- Package structure anti-patterns
- Inappropriate access modifiers
- Large, unfocused classes (god classes)

**Why High Priority**:
- Compound over time
- Make other refactoring difficult
- Increase onboarding time
- Increase bug risk

## Medium Priority - Maintainability Issues

### Method Design Problems

**Characteristics**:
- Localized to specific methods
- Reduce code readability
- Increase maintenance cost
- Limited blast radius

**Examples**:
- Long methods (see [refactoring-triggers.md](refactoring-triggers.md) for detailed criteria)
- High parameter counts without parameter objects
- Complex methods with high cyclomatic complexity (>15)
- Poor naming conventions

**Why Medium Priority**:
- Impact specific areas
- Easier to refactor incrementally
- Less risk than API changes
- Improve developer productivity

### Modern Java Adoption

**Characteristics**:
- Code works but uses outdated patterns
- Opportunities for simplification
- Improve code clarity
- Reduce boilerplate

**Examples**:
- Legacy switch statements (should use switch expressions)
- Verbose object creation patterns (should use records)
- Missing use of records for data carriers
- Underutilized stream operations

**Why Medium Priority**:
- Non-breaking improvements
- Incremental adoption possible
- Improve readability
- Reduce maintenance burden

### Code Cleanup

**Characteristics**:
- Unused or dead code
- No functional impact
- Reduce codebase size
- Improve clarity

**Examples**:
- Unused private fields and methods
- Unused local variables and parameters
- Dead code elimination (with user approval)
- Commented-out code

**Why Medium Priority**:
- No functional improvement
- Low risk to remove
- Reduces confusion
- Simplifies codebase

## Low Priority - Code Style and Optimization

### Style Consistency

**Characteristics**:
- Cosmetic improvements
- Minimal functional impact
- Nice to have
- Can be deferred

**Examples**:
- Comment formatting improvements
- Minor documentation enhancements
- Code formatting consistency
- Variable naming refinements

**Why Low Priority**:
- No functional impact
- Often subjective
- Can be batch processed
- Lower ROI

### Performance Optimizations

**Characteristics** (when low priority):
- No measured performance problem
- Speculative improvements
- Micro-optimizations
- Premature optimization

**Examples**:
- Theoretical performance improvements without profiling
- Micro-optimizations in non-critical paths
- Caching without measured need

**Why Low Priority**:
- No proven bottleneck
- May reduce readability
- Optimize based on data
- Focus on proven issues

**Note**: Performance optimizations are HIGH priority when:
- Profiling shows actual bottleneck
- User-facing performance issue
- System cannot scale
- SLA violations occurring

## Prioritization Decision Tree

```
Is there a security vulnerability?
├─> YES: HIGH PRIORITY (Security is always high)
└─> NO: Continue...

Is it a public API contract issue?
├─> YES: HIGH PRIORITY (API contracts are critical)
└─> NO: Continue...

Is it a fundamental design problem (SRP, package structure)?
├─> YES: HIGH PRIORITY (Design issues compound)
└─> NO: Continue...

Is it a method-level design issue (long methods, complexity)?
├─> YES: MEDIUM PRIORITY (Localized maintainability)
└─> NO: Continue...

Is it unused code or legacy patterns?
├─> YES: MEDIUM PRIORITY (Cleanup and modernization)
└─> NO: Continue...

Is it code style or speculative optimization?
└─> YES: LOW PRIORITY (Defer or batch)
```

## Prioritization Guidelines by Category

### Security Enhancements
- **Always HIGH** - Security cannot be compromised
- Examples: Input validation, SQL injection fixes, authentication issues

### Performance Issues
- **HIGH** if measured bottleneck with user impact
- **MEDIUM** if optimization has clear benefit
- **LOW** if speculative or micro-optimization

### Documentation
- **HIGH** if missing public API documentation
- **MEDIUM** if outdated or incomplete
- **LOW** if minor formatting or style

### Testing
- **HIGH** if critical paths lack coverage
- **MEDIUM** if coverage below targets (80%)
- **LOW** if improving already good coverage

### Dependency Management
- **HIGH** if security vulnerabilities in dependencies
- **MEDIUM** if major version updates available
- **LOW** if minor version updates

## Contextual Factors

Consider these factors when prioritizing:

### Impact Scope
- How many users/systems affected?
- How frequently is code executed?
- What's the blast radius of failure?

### Technical Debt Interest
- Is issue getting worse over time?
- Does it block other improvements?
- Will it be harder to fix later?

### Team Context
- Do we have expertise to fix it?
- How much time will it take?
- Are there dependencies on other work?

### Risk Assessment
- What's the risk of NOT fixing?
- What's the risk OF fixing (breaking changes)?
- Can we roll back if needed?

## Special Cases

### Cascading Issues
When one violation causes others:
- Fix root cause first (HIGH)
- Dependent issues may resolve automatically

### Breaking Changes
When fix requires API changes:
- Plan carefully even if HIGH priority
- Consider deprecation path
- Communicate with API consumers

### Framework Requirements
When "violations" are required by framework:
- NOT a violation (document why)
- Suppress warnings with explanation

## Workflow Integration

After identifying violations using refactoring-triggers.md:

1. **Categorize** by violation type
2. **Assign priority** using this framework
3. **Sort** HIGH → MEDIUM → LOW
4. **Execute** systematically within each priority band
5. **Verify** using compliance-checklist.md

## Related Standards

- refactoring-triggers.md - Detection criteria for violations
- compliance-checklist.md - Verification after fixes applied
