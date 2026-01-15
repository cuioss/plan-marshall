---
name: js-implement-tests
description: Self-contained command for JavaScript test implementation with verification and iteration
allowed-tools: Skill, Read, Write, Edit, Glob, Grep, Bash, Task
---

# JavaScript Implement Tests Command

Self-contained command that implements Jest/Vitest tests with full standards compliance, verifies with npm-builder, and iterates until tests pass.

## CONTINUOUS IMPROVEMENT RULE

If you discover issues or improvements during execution, record them:

1. **Activate skill**: `Skill: plan-marshall:manage-lessons`
2. **Record lesson** with:
   - Component: `{type: "command", name: "js-implement-tests", bundle: "pm-dev-frontend"}`
   - Category: bug | improvement | pattern | anti-pattern
   - Summary and detail of the finding

## PARAMETERS

- **task** (required): Test implementation task description
- **files** (optional): Fully qualified path(s) of file(s) to be tested
- **workspace** (optional): Workspace name for monorepo projects

## WORKFLOW (FOLLOW EXACTLY)

### Step 1: Parse and Verify Input Parameters

**Required Parameters:**
- **task** or equivalent description: Detailed description of what aspects/behaviors to test
- **files**: (Optional) Fully qualified path(s) of existing JavaScript file(s) to be tested
- **workspace**: (Optional) Workspace name for monorepo projects; if unset, assume single package

**Verification Process:**

1. **Verify files exist** (if provided):
   - Use Grep to search for each file in codebase
   - Verify files are in src/ (not test code)
   - Confirm files are accessible for testing
   - Track results: `files_found`, `files_missing`

2. **Analyze description for completeness**:
   - Check for specific test scenarios described
   - Verify clarity on what behaviors to test
   - Identify edge cases mentioned
   - Check for ambiguous language
   - Verify coverage expectations are clear

3. **Verify workspace parameter** (if monorepo):
   - Use Read to check package.json for workspaces
   - If workspace specified: verify workspace exists
   - If workspace unset: confirm single-package project
   - Track: `workspace_name`, `is_monorepo`

4. **Decision point**:
   - If any file missing: Return error with file names not found
   - If description incomplete/ambiguous: Return specific questions to user
   - If workspace invalid: Return error with available workspaces
   - If all verified: Proceed to Step 2

**SPECIAL CASE: Fix Build/Tests Mode**

If the description explicitly indicates the task is to **fix the build or failing tests**:
- Skip Step 2 (Build Precondition) - broken build/tests ARE the task
- Proceed directly to Step 3 (Load Testing Standards)
- Step 4 verification becomes primary check that fixes worked

**Detection keywords**: "fix tests", "fix test failures", "resolve failing tests", "tests are failing", "fix build"

### Step 2: Verify Build Precondition

**Build Verification:**

1. **Determine build scope**:
   - If monorepo and workspace specified: test only that workspace
   - If monorepo and workspace unset: test all workspaces
   - If single-package: test entire project

2. **Execute test verification**:
   ```
   Task:
     subagent_type: npm-builder
     description: Verify test precondition
     prompt: |
       Execute npm test to verify all existing tests pass.

       Command: run test
       Workspace: {workspace if specified}
       Output mode: DEFAULT

       Return status and any test failures found.
   ```

3. **Analyze test result**:
   - If SUCCESS with 0 failures: Proceed to Step 3
   - If FAILURE or any test failures: Return error to user
   - All existing tests MUST pass before implementing new tests

**Critical Rule**: Do not proceed if any existing tests fail. Return immediately to user.

### Step 3: Load Testing Standards and Analyze Code

**Load Testing Standards:**

1. **Always load JavaScript unit testing skill**:
   ```
   Skill: cui-javascript-unit-testing
   ```
   This skill will conditionally load all applicable testing standards based on the context.

2. **Analyze code under test**:
   - Use Read to load each file to be tested
   - Identify structure (component? service? utility?)
   - Check for dependencies and collaborators
   - Note frameworks in use (React? Vue? Plain JS?)
   - Identify async patterns
   - Check existing test files (if any)

3. **Determine applicable testing patterns**:
   - Jest or Vitest? (check package.json)
   - Component testing needed? (React Testing Library? Vue Test Utils?)
   - Mock strategies needed? (API calls, dependencies)
   - Async testing needed? (promises, async/await)

4. **Create holistic testing view**:
   - Map test requirements to testing standards
   - Identify test data generation strategy
   - Plan mocking opportunities
   - Determine assertion patterns
   - Plan edge case coverage
   - Identify exception testing needs

### Step 4: Create Comprehensive Test Plan

**Planning Process:**

1. **Plan test file structure**:
   - Test file name (fileName.test.js or fileName.spec.js)
   - describe() blocks for organization
   - Setup/teardown (beforeEach, afterEach if needed)
   - Test method organization (group by behavior)

2. **Plan individual test cases**:
   - For each public method/function in code under test
   - For each behavior described in requirements
   - For each edge case identified
   - Happy path tests
   - Error path tests
   - Boundary condition tests

3. **Plan test data strategy**:
   - Use factories or test data builders
   - Mock external dependencies
   - Plan fixture data for complex objects

4. **Plan assertion strategy**:
   - Meaningful test names
   - Appropriate matchers (toBe, toEqual, toHaveBeenCalled, etc.)
   - Exception testing with expect().rejects or expect().toThrow()
   - Multiple assertions when needed

5. **Plan mocking strategy**:
   - Mock modules with jest.mock() or vi.mock()
   - Mock functions with jest.fn() or vi.fn()
   - Spy on methods with jest.spyOn() or vi.spyOn()
   - Mock timers if needed

### Step 5: Implement Tests Step-by-Step

**Implementation Loop:**

For each test in the plan:

1. **Create/modify test file**:
   - If test file doesn't exist: Use Write to create new test file
   - If test file exists: Use Edit to add new test cases
   - Place in same directory as source OR in __tests__/ subdirectory
   - Follow Arrange-Act-Assert pattern

2. **Apply testing standards**:
   - Use describe() for grouping related tests
   - Use test() or it() for individual test cases
   - Include clear test names (should...)
   - Use appropriate matchers
   - Mock external dependencies properly
   - Clean up after tests (restore mocks)

3. **Track implementation progress**:
   - Count test cases implemented
   - Note test patterns used
   - Track coverage areas addressed

**Implementation Patterns:**

Reference patterns from loaded `cui-javascript-unit-testing` skill:
- AAA (Arrange-Act-Assert) pattern
- describe() block organization
- Mocking patterns
- Async testing patterns

### Step 6: Verify Testing Standards Compliance

**Standards Verification Checklist:**

1. **Core Jest/Vitest Compliance**:
   - [ ] All tests follow Arrange-Act-Assert pattern
   - [ ] Test names are clear and descriptive (should...)
   - [ ] describe() blocks group related tests
   - [ ] Test independence verified (no shared state)
   - [ ] Exception testing uses expect().toThrow() or .rejects
   - [ ] No console.log in tests

2. **Mocking Compliance**:
   - [ ] External dependencies mocked properly
   - [ ] Mocks cleaned up after tests (afterEach)
   - [ ] Spies used for verification
   - [ ] Mock implementations are realistic

3. **Async Testing Compliance** (if applicable):
   - [ ] Async tests use async/await or return promises
   - [ ] expect().resolves or .rejects used correctly
   - [ ] No callback-based async patterns

4. **Test Quality Compliance**:
   - [ ] Test methods are focused and independent
   - [ ] Meaningful test names
   - [ ] Edge cases covered
   - [ ] Error conditions tested
   - [ ] No commented-out code

**Verification Process:**

1. Read all implemented test files
2. Check each item systematically
3. If ANY item unchecked: Identify violations
4. Use Edit to fix violations
5. Re-verify until ALL items checked
6. **NO TOLERANCE** for non-compliance

**Critical Rule**: There is ZERO tolerance for testing standards violations. Every checklist item must pass.

### Step 7: Verify Tests with npm

**Test Verification:**

1. **Determine test scope** (same as Step 2)

2. **Execute tests**:
   ```
   Task:
     subagent_type: npm-builder
     description: Run tests
     prompt: |
       Execute npm test to run tests.

       Command: run test
       Workspace: {workspace if specified}
       Output mode: STRUCTURED

       Return structured results including test execution results.
   ```

3. **Analyze test result**:
   - If SUCCESS with 0 test failures: Proceed to Step 8
   - If test FAILURE:
     - Analyze failures (test bug vs production bug)
     - If test bug: Return to Step 5, fix tests
     - If production bug: Document and report
     - Repeat up to 3 iterations total for test bugs
     - If still failing after 3 iterations: Return error with details

**Iteration Counter**: Track test attempts, max 3 cycles of implement → verify → fix.

**Production Bug Detection**: If tests are correct but fail due to production code issues:
- Document the suspected production bug
- Return partial success with production issues noted
- Tests are standards-compliant and will pass once production code fixed

### Step 8: Return Test Implementation Results

**Only return to user after:**
- Test implementation is complete
- All standards compliance checks pass
- Tests execute successfully OR production bugs documented

**Success Response Format:**

```
TEST IMPLEMENTATION COMPLETE

What Was Tested:
- src/utils/validator.js: email validation, phone validation, null handling
- Coverage: all public functions, happy paths, error paths, edge cases

Test Files Created/Modified:
- src/utils/validator.test.js (created)
  - 12 test cases
  - Full function coverage
  - Mocking strategy: none needed (pure functions)

Testing Standards Applied:
✅ Core Jest (Arrange-Act-Assert, describe blocks, clear test names)
✅ Mocking (external dependencies mocked, cleanup in afterEach)
✅ Async Testing (async/await used, expect().resolves)
✅ Test Quality (focused tests, edge cases, error conditions)

Test Results: ✅ 12 tests passed, 0 failures, 0 skipped
Test Execution Time: 0.8s
Workspace: {workspace-name or "single package"}

Test Coverage Achieved:
- validateEmail(): 100% (happy path, error cases, null checks)
- validatePhone(): 100% (happy path, error cases, null checks)
- validate(): 100% (integration of both validations)

Standards Compliance: ✅ FULL COMPLIANCE
- Core Jest/Vitest: 6/6 checks passed
- Mocking: 4/4 checks passed
- Async Testing: 3/3 checks passed
- Test Quality: 4/4 checks passed

Summary:
- Iterations: {count}
- Test execution attempts: {count}
- Tests created: {count}
- Tests passed: {count}

Result: ✅ POSITIVE - All tests implemented successfully and passing
```

**Partial Success Response Format (production bugs found):**

```
TEST IMPLEMENTATION COMPLETE WITH PRODUCTION CODE ISSUES

What Was Tested:
- src/services/auth.js: authentication, token validation, session management
- Coverage: all public methods, happy paths, error paths, mocking external API

Test Files Created/Modified:
- src/services/auth.test.js (created)
  - 18 test cases
  - Full method coverage

Testing Standards Applied:
✅ Core Jest (AAA pattern, describe blocks, clear names)
✅ Mocking (API mocked, localStorage mocked)
✅ Async Testing (async/await throughout)
✅ Test Quality (focused tests, edge cases)

Test Results: ⚠️ 16 tests passed, 2 failures (production code bugs)
Test Execution Time: 1.2s
Workspace: {workspace-name or "single package"}

Standards Compliance: ✅ FULL COMPLIANCE
- All test code follows standards
- Failures are in production code

PRODUCTION CODE ISSUES DETECTED:

Issue 1:
- File: src/services/auth.js
- Method: validateToken(token)
- Failure: TypeError thrown instead of returning null
- Test: auth.test.js: should return null for invalid token
- Suspected Reason: Missing null check at method entry

Issue 2:
- File: src/services/auth.js
- Method: refreshSession()
- Failure: Returns undefined instead of rejected Promise
- Test: auth.test.js: should reject for expired session
- Suspected Reason: Missing Promise.reject() in error path

Result: ⚠️ PARTIAL SUCCESS
- All test code implemented correctly per standards
- Production code has 2 suspected defects requiring review
- Tests properly identify the issues and will pass once production code fixed
```

## CRITICAL RULES

**Input Verification:**
- ALWAYS verify files exist in codebase
- ALWAYS check description for completeness
- ALWAYS verify workspace parameter if monorepo
- NEVER proceed with missing files or unclear requirements
- RETURN to user immediately if verification fails

**Build Precondition (Step 2):**
- ALWAYS verify all existing tests pass BEFORE implementing new tests
- NEVER proceed if any tests fail
- RETURN to user immediately if tests not passing
- All existing tests must pass before adding new ones

**Standards Loading:**
- ALWAYS load cui-javascript-unit-testing skill
- TRUST skill to load applicable standards conditionally
- ALWAYS create holistic testing view before implementing
- NEVER skip standards loading

**Code Analysis:**
- ALWAYS analyze code under test thoroughly
- ALWAYS identify applicable testing patterns
- ALWAYS plan comprehensive test coverage
- NEVER skip edge cases or error paths

**Test Implementation:**
- ALWAYS follow Arrange-Act-Assert pattern
- ALWAYS use describe() blocks for organization
- ALWAYS include clear test names
- ALWAYS mock external dependencies
- NEVER use hardcoded test data when builders/factories are better

**Test Verification:**
- ALWAYS verify tests with npm-builder
- ALWAYS use "run test" at minimum
- ANALYZE test failures (test bug vs production bug)
- FIX test bugs and iterate (max 3 iterations)
- DOCUMENT production bugs but do not fix them

**Standards Verification:**
- ALWAYS verify all testing standards compliance
- CHECK every compliance item systematically
- FIX any standards violations immediately
- ZERO tolerance for non-compliance
- Return only after full compliance achieved
- NO CHANGES to production code ever

**Return Format:**
- RETURN when test implementation is complete and standards compliant
- ALWAYS include complete test summary
- ALWAYS list files created/modified
- ALWAYS report standards compliance status
- DOCUMENT production bugs if found

## TOOL USAGE

- **Read**: Load files under test, existing tests, analyze package.json
- **Write**: Create new test files
- **Edit**: Modify existing test files, fix test bugs
- **Glob**: Find test files, package.json locations
- **Grep**: Verify files exist, search for patterns, find dependencies
- **Skill**: Load cui-javascript-unit-testing (loads all applicable testing standards)
- **Task**: Invoke npm-builder agent for test execution

## ARCHITECTURE

This is a Layer 2 self-contained command:

```
/js-implement-tests (Layer 2: Single-item orchestration)
  ├─> Implement tests directly (no agent delegation)
  ├─> Task(npm-builder) [Layer 3: executes tests]
  ├─> Analyze and iterate (max 3 cycles)
  └─> Return result
```

**Key Design:**
- Self-contained: Implements tests directly without agent delegation
- Verification: Uses npm-builder for test execution (Rule 7 compliance)
- Iteration: Max 3 test-fix cycles
- Can be invoked by users OR Layer 1 batch commands
- Production bug detection: Documents production issues without fixing them

## RELATED

- `npm-builder` - Test execution agent (Layer 3)
- `/orchestrate-js` - Orchestrates multiple test tasks (Layer 1)
- `cui-javascript-unit-testing` - Testing standards skill
- `/javascript-implement-code` - Production code implementation (Layer 2)

## USAGE EXAMPLES

```
/js-implement-tests task="Test validateEmail and validatePhone functions" files="src/utils/validator.js"

/js-implement-tests task="Create comprehensive tests for auth service" files="src/services/auth.js" workspace="packages/core"

/js-implement-tests task="Fix failing tests in UserRepository"
```
