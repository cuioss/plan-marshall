---
name: js-implement-code
description: Self-contained command for JavaScript code implementation with verification and iteration
user-invocable: true
allowed-tools: Skill, Read, Write, Edit, Glob, Grep, Bash, Task
---

# JavaScript Implement Code Skill

Self-contained command that implements JavaScript code with full standards compliance, verifies with npm-builder, and iterates until clean.

## CONTINUOUS IMPROVEMENT RULE

If you discover issues or improvements during execution, record them:

1. **Activate skill**: `Skill: plan-marshall:manage-lessons`
2. **Record lesson** with:
   - Component: `{type: "command", name: "js-implement-code", bundle: "pm-dev-frontend"}`
   - Category: bug | improvement | pattern | anti-pattern
   - Summary and detail of the finding

## PARAMETERS

- **task** (required): Implementation task description
- **files** (optional): File(s), component(s), or name(s) of file(s) to implement/create
- **workspace** (optional): Workspace name for monorepo projects

## WORKFLOW (FOLLOW EXACTLY)

### Step 1: Parse and Verify Input Parameters

**Required Parameters:**
- **task** or equivalent description: Detailed, precise description of what to implement
- **files**: (Optional) Existing file(s), component(s), or name(s) of file(s) to be created
- **workspace**: (Optional) Workspace name for monorepo projects; if unset, assume single package

**Verification Process:**

1. **Parse files parameter** (if provided):
   - If existing files: Use Grep to verify existence in codebase
   - If new files: Validate naming follows JavaScript conventions
   - If component: Verify component structure exists or needs creation
   - Track results: `files_found`, `files_to_create`

2. **Analyze description for clarity**:
   - Check for ambiguous language ("maybe", "possibly", "could")
   - Verify all requirements are specific and measurable
   - Identify any missing information
   - List assumptions that need confirmation

3. **Verify workspace parameter** (if monorepo):
   - Use Read to check package.json for workspaces
   - If workspace specified: verify workspace exists
   - If workspace unset: confirm single-package project
   - Track: `workspace_name`, `is_monorepo`

4. **Decision point**:
   - If files don't exist when they should: Return error asking user to clarify
   - If description has ambiguities: Return specific questions to user
   - If description incomplete: Return list of missing information
   - If workspace invalid: Return error with available workspaces
   - If all clear: Proceed to Step 2

**SPECIAL CASE: Fix Build Mode**

If the description explicitly indicates the task is to **fix the build** (e.g., "fix compilation errors", "resolve build failures", "fix the build"):
- Skip Step 2 (Build Precondition) - broken build IS the task
- Proceed directly to Step 3 (Analyze Code Context)
- Step 4 verification becomes primary check that fix worked

**Detection keywords**: "fix build", "fix compilation", "resolve build errors", "build is broken", "doesn't compile"

### Step 2: Verify Build Precondition

**Build Verification:**

1. **Determine build scope**:
   - If monorepo and workspace specified: build only that workspace
   - If monorepo and workspace unset: build all workspaces
   - If single-package: build entire project

2. **Execute build verification**:
   ```
   Task:
     subagent_type: npm-builder
     description: Verify build precondition
     prompt: |
       Execute npm build to verify clean starting point.

       Command: run build
       Workspace: {workspace if specified}
       Output mode: DEFAULT

       Return status and any issues found.
   ```

3. **Analyze build result**:
   - If SUCCESS with 0 issues: Proceed to Step 3
   - If FAILURE or any issues: Return error to user
   - Codebase MUST compile cleanly before implementation

**Critical Rule**: Do not proceed if build has ANY errors or warnings. Return immediately to user.

### Step 3: Analyze Code Context

**Context Analysis:**

1. **Load existing files** (if working with existing code):
   - Use Read to load all related JavaScript files
   - Identify module structure, dependencies, patterns
   - Note existing patterns:
     - **Modules**: ES6 modules, CommonJS
     - **Functions**: Arrow functions, async/await, generators
     - **Classes**: ES6 classes, inheritance, composition
     - **Data**: Objects, arrays, Maps, Sets
     - **Web Components**: Custom elements, shadow DOM

2. **Analyze package structure**:
   - Use Glob to find related files in directory
   - Identify naming conventions (camelCase, PascalCase for components)
   - Check for existing test files (*.test.js, *.spec.js)
   - Note architectural layers:
     - **Components**: UI components, web components
     - **Services**: Business logic, API calls
     - **Utils**: Helper functions, utilities
     - **Types**: TypeScript types, interfaces

3. **Identify dependencies**:
   - Check imports in related files
   - Identify frameworks in use (React? Vue? Plain JS?)
   - Note testing framework (Jest? Vitest? Playwright?)
   - Check for existing utilities

4. **Document understanding**:
   - Summarize current state
   - Identify integration points
   - Note constraints or requirements
   - List related components

### Step 4: Load Standards and Create Holistic View

**Load Required Standards:**

1. **Always load core JavaScript standards**:
   ```
   Skill: cui-javascript
   ```

2. **Load additional standards on-demand based on context**:

   **Unit Testing** (load if implementing test code):
   ```
   Skill: cui-javascript-unit-testing
   ```

   **JSDoc** (load if implementing documented APIs):
   ```
   Skill: cui-jsdoc
   ```

   **Linting** (load if fixing lint issues):
   ```
   Skill: cui-javascript-linting
   ```

   **CSS** (load if implementing styles):
   ```
   Skill: cui-css
   ```

   **Cypress** (load if implementing E2E tests):
   ```
   Skill: cui-cypress
   ```

3. **Create holistic implementation view**:
   - Map requirements to standards patterns
   - Determine modern JavaScript features to use
   - Plan async/await patterns if needed
   - Select appropriate data structures
   - Identify error handling patterns
   - Plan JSDoc documentation approach

4. **Document approach**:
   - List standards to apply
   - Describe implementation strategy
   - Note critical compliance points
   - Identify potential challenges

### Step 5: Create Implementation Plan

**Planning Process:**

1. **Break down into steps**:
   - Create/modify files in logical order
   - Implement core functionality
   - Add error handling
   - Add JSDoc documentation
   - Apply modern JavaScript patterns

2. **For each step, document**:
   - What will be created/modified
   - Which standards apply
   - Expected outcome
   - Verification criteria

3. **Example plan format**:
   ```
   Step 1: Create src/utils/validator.js with input validation
   - Standards: javascript-fundamentals.md, modern-patterns.md
   - Verification: File exists, proper ES6 module exports

   Step 2: Implement validation functions with async support
   - Standards: async-programming.md, code-quality.md
   - Verification: Functions use async/await, proper error handling

   Step 3: Add JSDoc documentation
   - Standards: jsdoc-essentials.md, jsdoc-patterns.md
   - Verification: All public functions documented

   Step 4: Implement error handling with custom Error classes
   - Standards: code-quality.md
   - Verification: Proper error types, meaningful messages
   ```

### Step 6: Execute Implementation Step-by-Step

**Implementation Loop:**

For each step in the plan:

1. **Execute the step** using Write/Edit tools:
   - Create new files with Write
   - Modify existing files with Edit
   - Follow standards precisely
   - Apply patterns consistently

2. **Document critical decisions**:
   - Why specific approach chosen
   - Trade-offs considered
   - Assumptions made
   - **Add to JSDoc** (not command output)

3. **Verify step completion**:
   - Check file created/modified
   - Verify syntax correctness
   - Confirm standards applied
   - Move to next step

**Example critical decision documentation (in JSDoc):**
```javascript
/**
 * Validates user input using defensive null checks.
 *
 * **Design Decision:** Returns Promise<ValidationResult> rather than throwing exceptions
 * to allow callers to handle validation failures gracefully. Syntax errors still throw
 * as they represent programming errors, not business logic.
 *
 * @param {Object} input - The user input to validate (never null)
 * @returns {Promise<ValidationResult>} Promise resolving to validation result
 * @throws {TypeError} if input is null (programming error)
 */
```

### Step 7: Verify Build with npm (Post-Implementation)

**Build Verification:**

1. **Determine build scope** (same as Step 2)

2. **Execute build**:
   ```
   Task:
     subagent_type: npm-builder
     description: Verify implementation build
     prompt: |
       Execute npm build to verify implementation.

       Command: run build
       Workspace: {workspace if specified}
       Output mode: STRUCTURED

       Return structured results including all errors and warnings.
   ```

3. **Analyze build result**:
   - If SUCCESS with 0 issues: Proceed to Step 8
   - If FAILURE or issues found:
     - Analyze issues (compilation errors? lint errors?)
     - If fixable: Return to Step 6, fix issues
     - Repeat up to 3 iterations total
     - If still failing after 3 iterations: Return error with details

**Iteration Counter**: Track build attempts, max 3 cycles of implement → verify → fix.

### Step 8: Verify Implementation Against Requirements

**Requirements Verification:**

1. **Review original description**:
   - List each requirement explicitly
   - Create checklist of functionality

2. **Verify each requirement**:
   - Read implemented code
   - Confirm requirement implemented
   - Check implementation correctness
   - Verify edge cases handled

3. **Decision point**:
   - If any requirement NOT implemented: Return to Step 6, implement missing functionality
   - If any requirement implemented INCORRECTLY: Return to Step 6, correct implementation
   - If all requirements verified: Proceed to Step 9

**Verification Format:**
```
Requirement Verification:

✅ Validate user email format
   - Implemented in validateEmail() function
   - Uses regex pattern for RFC 5322 compliance
   - Handles null input with TypeError

✅ Return Promise for async validation
   - All validation methods return Promise
   - Rejected promise when validation fails
   - Never returns null

❌ Log validation failures
   - ISSUE: Logging not implemented
   - FIX NEEDED: Add console logging with proper messages
```

### Step 9: Verify Standards Compliance

**Standards Verification Checklist:**

1. **Modern JavaScript Compliance**:
   - [ ] ES6+ features used appropriately
   - [ ] Arrow functions for callbacks
   - [ ] async/await for asynchronous operations
   - [ ] Destructuring for cleaner code
   - [ ] Template literals for strings
   - [ ] const/let instead of var

2. **Code Quality Compliance**:
   - [ ] Functions are focused (< 50 lines)
   - [ ] Meaningful names used throughout
   - [ ] No magic numbers or strings
   - [ ] Proper error handling
   - [ ] No console.log in production code
   - [ ] Code is DRY (Don't Repeat Yourself)

3. **Async Programming Compliance** (if applicable):
   - [ ] async/await used instead of .then() chains
   - [ ] Error handling with try/catch
   - [ ] Promise.all() for parallel operations
   - [ ] Proper cancellation support if needed

4. **JSDoc Compliance**:
   - [ ] All public functions documented
   - [ ] @param tags for all parameters
   - [ ] @returns tag for return values
   - [ ] @throws for exceptions
   - [ ] Examples provided where helpful

5. **Module Compliance**:
   - [ ] ES6 modules (import/export)
   - [ ] Named exports for utilities
   - [ ] Default export for components
   - [ ] No circular dependencies
   - [ ] Proper file organization

**Verification Process:**

1. Read implemented files
2. Check each item systematically
3. If ANY item unchecked: Identify violations
4. Return to Step 6 to fix violations
5. Re-verify until ALL items checked
6. **NO TOLERANCE** for non-compliance

**Critical Rule**: There is ZERO tolerance for standards violations. Every checklist item must pass.

### Step 10: Return Implementation Results

**Only return to user after ALL verifications pass.**

**Return Format:**

```
IMPLEMENTATION COMPLETE

What Was Implemented:
- Created src/utils/validator.js with email/phone validation
- Added proper JSDoc documentation for all public functions
- Implemented async validation with Promise-based API
- Added defensive null checks at all API boundaries

Files Created/Modified:
- src/utils/validator.js (created)
- src/utils/validation-helpers.js (created)

Standards Applied:
✅ Modern JavaScript (ES6+, async/await, destructuring, arrow functions)
✅ Code quality (focused functions, meaningful names, DRY principle)
✅ Async programming (async/await, proper error handling)
✅ JSDoc (all public APIs documented)
✅ ES6 modules (proper imports/exports)

Build Status: ✅ SUCCESS (no errors, no warnings)

Requirements Verification: ✅ ALL VERIFIED
Standards Compliance: ✅ FULL COMPLIANCE

Critical Decisions Documented in JSDoc:
- validator.js uses Promise returns for async operations (see file JSDoc)
- ValidationResult implemented with plain JavaScript object pattern (see implementation)
- Error handling uses custom ValidationError class (see class JSDoc)

Summary:
- Iterations: {count}
- Build attempts: {count}
- Files created: {count}
- Files modified: {count}
```

## CRITICAL RULES

**Input Verification:**
- ALWAYS verify files exist or can be created
- ALWAYS check description for ambiguities
- ALWAYS return to user if verification fails
- NEVER proceed with unclear requirements

**Build Precondition (Step 2):**
- ALWAYS verify clean build BEFORE implementation
- NEVER proceed if build has errors
- NEVER proceed if build has warnings
- RETURN to user immediately if build not clean

**Context Analysis:**
- ALWAYS analyze existing code patterns
- ALWAYS identify related components
- ALWAYS understand integration points
- NEVER ignore architectural context

**Standards Loading:**
- ALWAYS load cui-javascript skill
- LOAD additional skills based on context
- ALWAYS create holistic view before implementing
- NEVER skip standards loading

**Implementation:**
- ALWAYS follow plan step-by-step
- ALWAYS document critical decisions in JSDoc
- NEVER skip standards compliance
- ALWAYS apply patterns consistently

**Post-Implementation Build Verification (Step 7):**
- ALWAYS verify with npm-builder
- ALWAYS use "run build" at minimum
- NEVER proceed with build errors
- NEVER proceed with build warnings
- FIX all issues until build is clean (max 3 iterations)

**Requirements Verification:**
- ALWAYS verify against original description
- ALWAYS check each requirement explicitly
- RETURN to implementation if anything wrong
- NEVER claim completion if requirements not met

**Standards Verification:**
- ZERO TOLERANCE for non-compliance
- ALWAYS verify ALL checklist items
- RETURN to implementation if violations found
- NEVER skip verification steps
- DOUBLE CHECK everything

**Return Format:**
- ONLY return when everything verified
- ALWAYS include complete summary
- ALWAYS list files created/modified
- DOCUMENT critical decisions in JSDoc (not return message)

## TOOL USAGE

- **Read**: Load existing JavaScript files, analyze context, check package.json
- **Write**: Create new JavaScript files
- **Edit**: Modify existing JavaScript files
- **Glob**: Find related files, package.json locations
- **Grep**: Search for patterns, functions, dependencies
- **Skill**: Load cui-javascript (always) and other skills (when needed)
- **Task**: Invoke npm-builder agent for build verification

## ARCHITECTURE

This is a Layer 2 self-contained command:

```
/js-implement-code (Layer 2: Single-item orchestration)
  ├─> Implement code directly (no agent delegation)
  ├─> Task(npm-builder) [Layer 3: verifies builds]
  ├─> Analyze and iterate (max 3 cycles)
  └─> Return result
```

**Key Design:**
- Self-contained: Implements code directly without agent delegation
- Verification: Uses npm-builder for builds (Rule 7 compliance)
- Iteration: Max 3 build-fix cycles
- Can be invoked by users OR Layer 1 batch commands

## RELATED

- `npm-builder` - Build verification agent (Layer 3)
- `/orchestrate-js` - Orchestrates multiple implementations (Layer 1)
- `cui-javascript` - Core JavaScript standards skill
- `cui-jsdoc` - JSDoc documentation skill

## USAGE EXAMPLES

```
/js-implement-code task="Implement email and phone validation functions" files="src/utils/validator.js"

/js-implement-code task="Create reusable Button component with variants" files="src/components/Button.js"

/js-implement-code task="Implement REST API client" files="src/services/api.js" workspace="packages/core"
```
