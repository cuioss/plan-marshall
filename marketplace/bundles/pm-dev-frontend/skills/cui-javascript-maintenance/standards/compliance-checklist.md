# JavaScript Standards Compliance Checklist

This document provides a comprehensive checklist for verifying JavaScript code compliance with CUI standards. Use this checklist after refactoring or maintenance work to ensure all standards are met.

## Purpose

Provide systematic verification that code meets all JavaScript standards. This checklist ensures no aspects are overlooked during maintenance work.

---

## Pre-Maintenance Baseline

Execute these checks before starting maintenance to establish a baseline:

### Build Verification
- [ ] `npm run build` completes successfully (if applicable)
- [ ] No build warnings or errors
- [ ] Build output is correct size/structure
- [ ] Source maps generated properly

### Test Execution
- [ ] `npm test` runs all tests successfully
- [ ] No test failures or errors
- [ ] All test suites complete
- [ ] No skipped tests (unless documented)

### Coverage Baseline
- [ ] `npm run test:coverage` generates report
- [ ] Record current coverage percentages:
  - Line coverage: ____%
  - Branch coverage: ____%
  - Function coverage: ____%
  - Statement coverage: ____%

### Lint Check
- [ ] `npm run lint` completes
- [ ] Record existing violations count: ____
- [ ] Categorize violations by severity

### Dependency Audit
- [ ] `npm audit` completes
- [ ] Document security vulnerabilities:
  - Critical: ____
  - High: ____
  - Moderate: ____
  - Low: ____

### Module Identification
- [ ] List all JavaScript modules/files for processing
- [ ] Identify module dependencies
- [ ] Determine processing order (dependencies first)

---

## Standards Compliance Verification

For each module/component, verify compliance with these standards:

### Vanilla JavaScript Usage

- [ ] **No jQuery usage** for operations that have native equivalents
  - [ ] No `$()` selector usage
  - [ ] No `$.ajax()` calls
  - [ ] No jQuery utility methods where native exists

- [ ] **No unnecessary library dependencies**
  - [ ] Lodash not used for native array methods
  - [ ] No request libraries where fetch works
  - [ ] Heavy libraries justified and documented

- [ ] **Library usage justified**
  - [ ] Complex operations documented as needing library
  - [ ] Threshold check: native would require 50+ lines
  - [ ] Justification comments included

### Test Code Separation

- [ ] **No test-specific imports** in production files
  - [ ] No jest imports
  - [ ] No mock imports
  - [ ] No test utility imports

- [ ] **No conditional test logic** in production
  - [ ] No `if (process.env.NODE_ENV === 'test')` blocks
  - [ ] Test behavior handled via dependency injection

- [ ] **No development-only code**
  - [ ] No debug console.log statements
  - [ ] No debugger statements
  - [ ] Debug modes properly configured

### Proper Modularization

- [ ] **Single responsibility** per module
  - [ ] Each module has one clear purpose
  - [ ] No mixed concerns (UI + business logic)
  - [ ] Clear module boundaries

- [ ] **File size appropriate**
  - [ ] No files over 400 lines (unless justified)
  - [ ] Complex files split into logical modules
  - [ ] Not over-modularized (no tiny modules)

- [ ] **No inappropriate duplication**
  - [ ] No 10+ line duplicated blocks
  - [ ] Complex logic extracted to utilities
  - [ ] Simple patterns (1-5 lines) not over-extracted

- [ ] **Clear module structure**
  - [ ] ES modules (import/export) used
  - [ ] No circular dependencies
  - [ ] Logical directory organization

### Package.json Standards

- [ ] **Dependencies current**
  - [ ] No outdated dependencies (check `npm outdated`)
  - [ ] Security vulnerabilities addressed
  - [ ] Major versions justified if not latest

- [ ] **No unused dependencies**
  - [ ] All dependencies imported/used
  - [ ] Run `depcheck` to verify
  - [ ] Removed packages not needed

- [ ] **Correct dependency categorization**
  - [ ] Runtime dependencies in `dependencies`
  - [ ] Build/test tools in `devDependencies`
  - [ ] No misplaced dependencies

- [ ] **Required scripts present**
  - [ ] `test` script defined
  - [ ] `lint` script defined
  - [ ] `format` or `format:check` defined
  - [ ] `build` script defined (if applicable)
  - [ ] `dev` script defined (if applicable)

### JSDoc Coverage

- [ ] **Public APIs documented**
  - [ ] All exported functions have JSDoc
  - [ ] JSDoc includes description
  - [ ] All `@param` tags present and correct
  - [ ] `@returns` tag present and correct
  - [ ] `@throws` tag for functions that throw

- [ ] **No trivial comments**
  - [ ] Obvious code not commented
  - [ ] Standard patterns not over-documented
  - [ ] Comments add value

- [ ] **Documentation current**
  - [ ] JSDoc matches actual implementation
  - [ ] Parameter types correct
  - [ ] Return types correct
  - [ ] No outdated information

- [ ] **Complex logic explained**
  - [ ] Non-obvious algorithms commented
  - [ ] Business logic documented
  - [ ] Complex conditionals explained

### Code Organization

- [ ] **Separation of concerns**
  - [ ] UI components separate from business logic
  - [ ] Data fetching in service layer
  - [ ] Validation logic separated
  - [ ] Clear architectural layers

- [ ] **Module structure**
  - [ ] Consistent file naming (kebab-case)
  - [ ] Logical directory organization
  - [ ] Index files used appropriately
  - [ ] No deep nesting (max 3-4 levels)

### Modern JavaScript Patterns

- [ ] **ES Modules**
  - [ ] Using `import`/`export` (not CommonJS)
  - [ ] Named exports for utilities
  - [ ] Default exports for components (React)

- [ ] **Variable declarations**
  - [ ] `const` for immutable bindings
  - [ ] `let` for mutable bindings
  - [ ] No `var` usage

- [ ] **Functions**
  - [ ] Arrow functions for callbacks/short functions
  - [ ] Regular functions for methods/complex logic
  - [ ] No unnecessary function wrappers

- [ ] **Destructuring**
  - [ ] Object destructuring where appropriate
  - [ ] Array destructuring for clarity
  - [ ] Not over-destructured (readability)

- [ ] **Async patterns**
  - [ ] `async`/`await` preferred over callbacks
  - [ ] Proper error handling with try/catch
  - [ ] Promise.all for concurrent operations

### Code Quality

- [ ] **Complexity limits**
  - [ ] Cyclomatic complexity ≤ 15
  - [ ] Statement count ≤ 20 per function
  - [ ] Nesting depth ≤ 4 levels

- [ ] **Function size**
  - [ ] Functions under 50 lines (guideline)
  - [ ] Large functions extracted into smaller ones
  - [ ] Single responsibility per function

- [ ] **Naming**
  - [ ] Clear, descriptive names
  - [ ] Consistent naming conventions (camelCase)
  - [ ] No abbreviations unless standard
  - [ ] Boolean names start with is/has/should

---

## Build and Quality Checks

After maintenance work, run all quality checks:

### Format Verification

**Command:** `npm run format:check`

**Purpose:** Ensure consistent code formatting

**Requirements:**
- [ ] All files pass format check
- [ ] No formatting violations
- [ ] Prettier configuration followed

**If fails:**
- Run `npm run format` to auto-fix
- Re-check with `npm run format:check`

### Lint Verification

**Command:** `npm run lint`

**Purpose:** Catch code quality issues

**Requirements:**
- [ ] All lint rules pass
- [ ] No ESLint violations
- [ ] No warnings (or documented exceptions)

**If fails:**
- Run `npm run lint:fix` for auto-fixable issues
- Manually fix remaining violations
- Document any rule exceptions with rationale

### Test Execution

**Command:** `npm test`

**Purpose:** Verify functionality preserved

**Requirements:**
- [ ] All tests pass
- [ ] No test failures
- [ ] No skipped tests
- [ ] Test suite completes successfully

**If fails:**
- Fix broken tests
- Ensure no behavior changes introduced
- Add tests for new code if needed

### Coverage Analysis

**Command:** `npm run test:coverage`

**Purpose:** Ensure coverage maintained or improved

**Requirements:**
- [ ] Coverage ≥ baseline
- [ ] Line coverage ≥ 80%
- [ ] Branch coverage ≥ 80%
- [ ] No significant regression

**Coverage Comparison:**
- Before: ____%
- After: ____%
- Change: ±____%

**If regression:**
- Add tests to restore coverage
- Document intentional coverage reduction
- Get approval for coverage decrease

### Security Audit

**Command:** `npm audit`

**Purpose:** Verify no new vulnerabilities

**Requirements:**
- [ ] No new vulnerabilities introduced
- [ ] Existing vulnerabilities addressed
- [ ] Critical/High vulnerabilities = 0

**Vulnerability Comparison:**
- Before: ____
- After: ____
- Fixed: ____
- New: ____

**If new vulnerabilities:**
- Update dependencies to fix
- Document unresolvable issues
- Create tickets for follow-up

---

## Final Verification Steps

After all changes complete:

### Build Verification

**Command:** `npm run build` (if applicable)

**Requirements:**
- [ ] Build completes successfully
- [ ] No build errors or warnings
- [ ] Bundle size acceptable (compare to baseline)
- [ ] Source maps generated

**Bundle Size Check:**
- Before: ____ KB
- After: ____ KB
- Change: ±____ KB

**If significant increase:**
- Investigate bundle size increase
- Check for unnecessary dependencies
- Review code splitting

### Manual Testing

**Requirements:**
- [ ] Test key functionality in browser
- [ ] Verify user flows work correctly
- [ ] Check for console errors
- [ ] Test in target browsers

**Browser Compatibility:**
- [ ] Chrome/Edge (latest)
- [ ] Firefox (latest)
- [ ] Safari (latest)
- [ ] Mobile browsers (if applicable)

### Documentation Update

**Requirements:**
- [ ] README updated if needed
- [ ] API documentation current
- [ ] CHANGELOG updated
- [ ] Migration guide (if breaking changes)

### Final Commit

**Requirements:**
- [ ] Clear commit message
- [ ] Follows commit standards
- [ ] References related issues/tickets
- [ ] Includes co-author attribution

---

## Module-by-Module Strategy

When processing multiple modules:

### Single Module Process

**Requirements:**
1. [ ] Focus on one module completely before next
2. [ ] Run `npm run format:check` after changes
3. [ ] Run `npm run lint` after changes
4. [ ] Run relevant tests for the module
5. [ ] Check coverage for module
6. [ ] Commit module changes before next

### Multi-Module Strategy

**Dependencies Management:**
- [ ] Process modules in dependency order (dependencies first)
- [ ] Maintain functionality after each module
- [ ] Verify inter-module compatibility after refactoring
- [ ] Test integration between modules

**Tracking:**
- [ ] List of modules: ________________
- [ ] Processing order: ________________
- [ ] Modules completed: ____/____
- [ ] Modules failed: ________________

---

## Critical Constraints Verification

Ensure these constraints were followed:

### Functionality Preservation

- [ ] **NO BEHAVIOR CHANGES** unless fixing confirmed bugs
- [ ] All existing tests continue to pass
- [ ] API compatibility maintained for public APIs
- [ ] Browser compatibility maintained

### Safety Protocols

- [ ] **Incremental changes** (small, focused commits)
- [ ] **Test coverage** maintained or improved
- [ ] **Build verification** after each change
- [ ] **Dependencies locked** (package-lock.json updated)

---

## Compliance Summary

After completing checklist:

**Overall Compliance:**
- [ ] Vanilla JavaScript: ☐ Compliant ☐ Non-Compliant ☐ Partially Compliant
- [ ] Test Code Separation: ☐ Compliant ☐ Non-Compliant ☐ Partially Compliant
- [ ] Modularization: ☐ Compliant ☐ Non-Compliant ☐ Partially Compliant
- [ ] Package.json: ☐ Compliant ☐ Non-Compliant ☐ Partially Compliant
- [ ] JSDoc Coverage: ☐ Compliant ☐ Non-Compliant ☐ Partially Compliant
- [ ] Code Organization: ☐ Compliant ☐ Non-Compliant ☐ Partially Compliant
- [ ] Modern Patterns: ☐ Compliant ☐ Non-Compliant ☐ Partially Compliant
- [ ] Code Quality: ☐ Compliant ☐ Non-Compliant ☐ Partially Compliant

**Build and Quality:**
- [ ] Format: ☐ Pass ☐ Fail
- [ ] Lint: ☐ Pass ☐ Fail
- [ ] Tests: ☐ Pass ☐ Fail (____/____ passed)
- [ ] Coverage: ☐ Pass ☐ Fail (____%)
- [ ] Security: ☐ Pass ☐ Fail (____ vulnerabilities)
- [ ] Build: ☐ Pass ☐ Fail

**Ready for Release:**
- [ ] All compliance checks passed
- [ ] All quality checks passed
- [ ] Documentation updated
- [ ] Changes committed
- [ ] Ready for code review

**Deviations:**
Document any intentional deviations from standards with rationale:
- _______________________________________________
- _______________________________________________

---

## Reference

For detailed implementation guidance:
- **refactoring-triggers.md** - When to apply refactoring
- **maintenance-prioritization.md** - How to prioritize work
- **test-quality-standards.md** - Test quality requirements
- **cui-javascript skill** - Core JavaScript patterns
- **cui-javascript-linting skill** - Linting configuration
- **cui-jsdoc skill** - Documentation standards
