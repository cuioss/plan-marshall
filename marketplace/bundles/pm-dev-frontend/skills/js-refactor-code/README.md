# CUI JavaScript Maintenance

Standards for systematic JavaScript code maintenance, refactoring, and test quality improvement.

## Overview

This skill provides a comprehensive framework for maintaining JavaScript codebases, including:
- **Detection** - Identifying code that needs refactoring
- **Prioritization** - Determining the order to address issues
- **Verification** - Ensuring standards compliance after changes
- **Test Quality** - Improving and maintaining test quality

## Standards Documents

### refactoring-triggers.md
Defines when and how to identify violations that require refactoring:
- Vanilla JavaScript enforcement criteria
- Test/mock code contamination detection
- Modularization triggers
- Package.json update criteria
- JSDoc requirements

### maintenance-prioritization.md
Provides framework for prioritizing maintenance work:
- HIGH priority - Critical issues (security, bugs, design flaws)
- MEDIUM priority - Maintainability (code quality, modernization)
- LOW priority - Style and optimization
- Contextual factors (impact, debt, team, risk)

### compliance-checklist.md
Comprehensive checklist for verifying standards compliance:
- Pre-maintenance baseline establishment
- Standards compliance verification
- Build and quality checks
- Module-by-module processing strategy
- Final verification steps

### test-quality-standards.md
Standards for JavaScript test quality:
- Test structure requirements (AAA pattern)
- Common anti-patterns to avoid
- Framework compliance (Jest, Testing Library)
- Mock management best practices
- Coverage requirements
- E2E test standards (Cypress)
- Test data management patterns

## When to Use

**Code Quality Audits:**
- Identifying technical debt
- Planning refactoring work
- Systematic codebase analysis

**Refactoring Work:**
- Determining what needs fixing
- Prioritizing maintenance tasks
- Verifying compliance after changes

**Test Quality Improvement:**
- Identifying test anti-patterns
- Improving test coverage
- Refactoring test code

**Code Reviews:**
- Systematic quality assessment
- Identifying improvement opportunities
- Validating completeness

## Integration

This skill is used by:
- `/js-refactor-code` - Systematic code refactoring workflow
- `/js-maintain-tests` - Test quality improvement workflow
- Code review processes
- Maintenance planning

## Relationship with Other Skills

**Complementary Skills:**
- `cui-javascript` - Implementation patterns (HOW to code)
- `cui-jsdoc` - Documentation patterns
- `cui-javascript-unit-testing` - Testing patterns
- `cui-javascript-linting` - ESLint configuration
- `cui-cypress` - E2E testing patterns

**Clear Separation:**
- This skill: WHEN to refactor, WHAT priority, HOW to verify
- Implementation skills: HOW to implement the fixes

## Quick Reference

**Workflow:**
1. Load skill to access all standards
2. Apply trigger criteria to identify issues
3. Prioritize using framework
4. Implement fixes (load implementation skills)
5. Verify using compliance checklist

**Priority Levels:**
- **HIGH**: Security, bugs, blocking issues → Fix immediately
- **MEDIUM**: Maintainability, tech debt → Schedule soon
- **LOW**: Style, preferences → Fix when convenient

## Related

- [CUI JavaScript Development Standards](../cui-javascript/SKILL.md)
- [CUI JavaScript Linting Standards](../cui-javascript-linting/SKILL.md)
- [CUI JSDoc Standards](../cui-jsdoc/SKILL.md)
- [CUI JavaScript Unit Testing Standards](../cui-javascript-unit-testing/SKILL.md)
