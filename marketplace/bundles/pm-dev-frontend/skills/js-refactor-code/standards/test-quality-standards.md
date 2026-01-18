# JavaScript Test Quality Standards

This document defines comprehensive standards for JavaScript test quality, including test patterns, anti-patterns, structure requirements, and improvement strategies.

## Purpose

Establish clear standards for JavaScript test quality to ensure tests are maintainable, reliable, and provide value. This document defines what makes a good test and how to improve test quality systematically.

---

## Test Structure Requirements

### AAA Pattern (Arrange-Act-Assert)

All tests should follow the Arrange-Act-Assert pattern for clarity.

**Structure:**
```javascript
test('description', () => {
  // Arrange - Set up test data and conditions
  const user = { name: 'Test User', age: 30 };

  // Act - Execute the code under test
  const result = validateUser(user);

  // Assert - Verify the expected outcome
  expect(result.isValid).toBe(true);
});
```

**Requirements:**
- Clear separation between arrange, act, and assert
- Setup code at the beginning
- Single action being tested
- Assertions at the end

---

## Common JavaScript Test Anti-Patterns

Anti-patterns that compromise test quality and should be avoided or refactored.

### Overly Complex Test Setup

**Anti-Pattern:** Tests with 20+ lines of setup code.

**Problem:** Makes tests hard to understand and maintain.

**Action Required:** Extract setup to helper functions or `beforeEach`.

**Target:** Keep test setup under 10 lines.

**Example:**
```javascript
// ❌ Overly complex setup
test('user registration', () => {
  const mockDb = new MockDatabase();
  mockDb.connect();
  mockDb.createTable('users');
  const validator = new Validator();
  validator.setRules({...});
  const emailService = new EmailService();
  emailService.configure({...});
  const userService = new UserService(mockDb, validator, emailService);
  userService.setConfig({...});
  // ... more setup

  const result = userService.register(userData);
  expect(result).toBeDefined();
});

// ✅ Extracted setup
beforeEach(() => {
  setupTestEnvironment();
});

test('user registration', () => {
  const result = userService.register(userData);
  expect(result).toBeDefined();
});
```

---

### Hardcoded Test Data

**Anti-Pattern:** Literal values scattered throughout tests.

**Problem:** Makes tests brittle and hard to maintain.

**Action Required:** Extract to test fixtures or factory functions.

**Pattern:** Use data builders or factory patterns.

**Example:**
```javascript
// ❌ Hardcoded test data
test('validates user email', () => {
  const result = validateEmail('test@example.com');
  expect(result).toBe(true);
});

test('rejects invalid email', () => {
  const result = validateEmail('invalid-email');
  expect(result).toBe(false);
});

// ✅ Using test fixtures
const TEST_DATA = {
  validEmail: 'test@example.com',
  invalidEmail: 'invalid-email'
};

test('validates user email', () => {
  const result = validateEmail(TEST_DATA.validEmail);
  expect(result).toBe(true);
});

// ✅ Using factory functions
const createUser = (overrides = {}) => ({
  id: '123',
  name: 'Test User',
  email: 'test@example.com',
  ...overrides
});

test('validates user with valid email', () => {
  const user = createUser({ email: 'valid@example.com' });
  expect(validateUser(user).isValid).toBe(true);
});
```

---

### Missing Async Handling

**Anti-Pattern:** Tests without proper async/await or done callbacks.

**Problem:** Tests pass even when they shouldn't, creating false confidence.

**Action Required:** Add proper async handling.

**Pattern:** Prefer async/await over callbacks.

**Example:**
```javascript
// ❌ Missing async handling - test passes incorrectly
test('fetches user data', () => {
  fetchUser('123').then(user => {
    expect(user.name).toBe('Test User'); // Never checked!
  });
});

// ✅ Proper async/await
test('fetches user data', async () => {
  const user = await fetchUser('123');
  expect(user.name).toBe('Test User');
});

// ✅ Testing rejection
test('handles fetch error', async () => {
  await expect(fetchUser('invalid')).rejects.toThrow('User not found');
});
```

---

### DOM Testing Without Cleanup

**Anti-Pattern:** Tests that modify DOM without cleanup.

**Problem:** State leaks between tests causing flaky tests.

**Action Required:** Add proper cleanup in `afterEach`.

**Use:** Testing Library cleanup utilities.

**Example:**
```javascript
// ❌ No cleanup
test('renders component', () => {
  const container = document.createElement('div');
  document.body.appendChild(container);
  render(<MyComponent />, container);
  expect(container.querySelector('.my-class')).toBeInTheDocument();
});

// ✅ With cleanup
import { cleanup, render, screen } from '@testing-library/react';

afterEach(() => {
  cleanup();
});

test('renders component', () => {
  render(<MyComponent />);
  expect(screen.getByRole('button')).toBeInTheDocument();
});
```

---

### Test Independence Violations

**Anti-Pattern:** Tests that depend on shared state or execution order.

**Problem:** Flaky tests, hard to debug, can't run in parallel.

**Action Required:** Ensure each test can run independently.

**Example:**
```javascript
// ❌ Shared state between tests
let counter = 0;

test('increments counter', () => {
  counter++;
  expect(counter).toBe(1);
});

test('increments counter again', () => {
  counter++; // Depends on previous test!
  expect(counter).toBe(2);
});

// ✅ Independent tests
test('increments counter', () => {
  let counter = 0;
  counter++;
  expect(counter).toBe(1);
});

test('increments counter again', () => {
  let counter = 0;
  counter++;
  expect(counter).toBe(1);
});
```

---

## Framework Compliance Requirements

### Jest Standards

**Required patterns:**
- Use `describe` blocks for logical grouping
- Prefer `test` over `it` for consistency
- Use `expect` assertions with clear matchers
- Implement proper async test patterns

**Example:**
```javascript
describe('UserService', () => {
  describe('registerUser', () => {
    test('creates user with valid data', async () => {
      const userData = createTestUser();
      const result = await userService.registerUser(userData);
      expect(result.id).toBeDefined();
    });

    test('throws error for duplicate email', async () => {
      const userData = createTestUser();
      await userService.registerUser(userData);
      await expect(userService.registerUser(userData))
        .rejects.toThrow('Email already exists');
    });
  });
});
```

---

### Testing Library Standards

Follow Testing Library principles for component testing.

**Principles:**
- Test user behavior, not implementation
- Use semantic queries (getByRole, getByLabelText)
- Avoid testing implementation details
- Wait for async operations properly

**Query Priority (in order):**
1. `getByRole` - Best for accessibility
2. `getByLabelText` - Good for form fields
3. `getByPlaceholderText` - OK for inputs
4. `getByText` - OK for non-interactive elements
5. `getByTestId` - Last resort

**Example:**
```javascript
// ❌ Testing implementation details
test('updates state on click', () => {
  const wrapper = mount(<Counter />);
  wrapper.find('button').simulate('click');
  expect(wrapper.state('count')).toBe(1);
});

// ✅ Testing user behavior
test('increments counter on click', () => {
  render(<Counter />);
  const button = screen.getByRole('button', { name: /increment/i });
  fireEvent.click(button);
  expect(screen.getByText('Count: 1')).toBeInTheDocument();
});
```

---

## Mock and Stub Management

### Mock Best Practices

**Module Mocks:**
Use `jest.mock()` at top level for mocking entire modules.

```javascript
jest.mock('./userService');

test('handles user fetch', async () => {
  userService.fetchUser.mockResolvedValue({ id: '123', name: 'Test' });
  const result = await getUser('123');
  expect(result.name).toBe('Test');
});
```

**Function Mocks:**
Use `jest.fn()` for individual function mocks.

```javascript
test('calls callback on success', async () => {
  const callback = jest.fn();
  await processData(data, callback);
  expect(callback).toHaveBeenCalledWith({ success: true });
});
```

**Spy Pattern:**
Use `jest.spyOn()` for existing methods.

```javascript
test('logs error on failure', async () => {
  const logSpy = jest.spyOn(console, 'error').mockImplementation();
  await processData(invalidData);
  expect(logSpy).toHaveBeenCalledWith(expect.stringContaining('Error'));
  logSpy.mockRestore();
});
```

**Mock Restoration:**
Always restore mocks in `afterEach`.

```javascript
afterEach(() => {
  jest.restoreAllMocks();
});
```

---

### Common Mock Issues

**Mocks Not Being Reset:**
```javascript
// ❌ Mock state leaks between tests
const mockFn = jest.fn();

test('test 1', () => {
  mockFn();
  expect(mockFn).toHaveBeenCalledTimes(1);
});

test('test 2', () => {
  expect(mockFn).toHaveBeenCalledTimes(1); // Still has state from test 1!
});

// ✅ Proper mock reset
const mockFn = jest.fn();

afterEach(() => {
  jest.clearAllMocks();
});

test('test 1', () => {
  mockFn();
  expect(mockFn).toHaveBeenCalledTimes(1);
});

test('test 2', () => {
  expect(mockFn).toHaveBeenCalledTimes(0);
});
```

**Over-Mocking:**
```javascript
// ❌ Mocking too much - testing mocks instead of code
test('user validation', () => {
  userService.validateUser.mockReturnValue(true);
  expect(userService.validateUser(user)).toBe(true); // Just testing the mock!
});

// ✅ Mock boundaries, test logic
test('user validation', () => {
  // Mock external dependencies only
  database.findUser.mockResolvedValue(existingUser);

  // Test actual validation logic
  const result = await validateUser(userData);
  expect(result.isValid).toBe(false);
  expect(result.error).toBe('Email already exists');
});
```

**Incomplete Mock Implementations:**
```javascript
// ❌ Incomplete mock
const mockDb = {
  findUser: jest.fn()
  // Missing other required methods!
};

// ✅ Complete mock or use createMockDb factory
const mockDb = {
  findUser: jest.fn(),
  saveUser: jest.fn(),
  deleteUser: jest.fn(),
  updateUser: jest.fn()
};
```

---

## Coverage Requirements

### Quality Gates

**Minimum Coverage Targets:**
- **Line coverage:** 80%
- **Branch coverage:** 80% for logic-heavy code
- **Function coverage:** 80%
- **Statement coverage:** 80%

**High-Priority Code (90%+ coverage):**
- Business logic
- Security-sensitive functionality
- Payment processing
- Data validation
- Authentication/authorization

**Acceptable Lower Coverage (60%+):**
- UI layout code
- Configuration files
- Framework boilerplate
- Simple getters/setters

---

### Coverage Verification

**Process:**
1. Run `npm run test:coverage`
2. Review coverage report
3. Identify untested critical paths
4. Add tests for gaps
5. Document intentional coverage gaps

**Intentional Gaps:**
Document why certain code is not covered:
- External library wrappers (testing library, not wrapper)
- Framework-generated code
- Code requiring manual testing (browser APIs)
- Deprecated code scheduled for removal

---

## E2E Test Maintenance

### Cypress Best Practices

**Element Selection:**
Use data attributes for stable selectors.

```javascript
// ❌ Fragile selectors
cy.get('.btn-primary').click();
cy.get('#user-email').type('test@example.com');

// ✅ Stable data attributes
cy.get('[data-cy="submit-button"]').click();
cy.get('[data-cy="email-input"]').type('test@example.com');
```

**Wait Strategies:**
Use proper wait strategies, avoid arbitrary timeouts.

```javascript
// ❌ Arbitrary timeout
cy.wait(5000);
cy.get('[data-cy="result"]').should('be.visible');

// ✅ Wait for specific condition
cy.get('[data-cy="result"]').should('be.visible');
cy.intercept('POST', '/api/users').as('createUser');
cy.wait('@createUser');
```

**Reusable Commands:**
Create custom commands for common operations.

```javascript
// cypress/support/commands.js
Cypress.Commands.add('login', (email, password) => {
  cy.visit('/login');
  cy.get('[data-cy="email"]').type(email);
  cy.get('[data-cy="password"]').type(password);
  cy.get('[data-cy="login-button"]').click();
});

// In tests
cy.login('user@example.com', 'password');
```

**Test Isolation:**
Each test should be independent.

```javascript
beforeEach(() => {
  // Reset state before each test
  cy.clearCookies();
  cy.clearLocalStorage();
  cy.visit('/');
});
```

---

## Test Data Management

### Data Factory Pattern

Create centralized test data factories.

**Example:**
```javascript
// test/factories/userFactory.js
export const createUser = (overrides = {}) => ({
  id: '123',
  name: 'Test User',
  email: 'test@example.com',
  role: 'user',
  createdAt: new Date(),
  ...overrides
});

export const createAdmin = (overrides = {}) =>
  createUser({ role: 'admin', ...overrides });

// In tests
test('validates admin permissions', () => {
  const admin = createAdmin({ email: 'admin@example.com' });
  expect(hasAdminPermissions(admin)).toBe(true);
});

test('denies user permissions', () => {
  const user = createUser();
  expect(hasAdminPermissions(user)).toBe(false);
});
```

### Fixture Files

Use fixture files for larger test data sets.

```javascript
// test/fixtures/users.json
{
  "validUser": {
    "id": "123",
    "name": "Test User",
    "email": "test@example.com"
  },
  "invalidUser": {
    "id": "",
    "name": "",
    "email": "invalid-email"
  }
}

// In tests
import usersFixture from './fixtures/users.json';

test('validates user data', () => {
  const result = validateUser(usersFixture.validUser);
  expect(result.isValid).toBe(true);
});
```

---

## Test Simplification Patterns

### Extract Complex Setup

Move setup code to helper functions.

```javascript
// test/helpers/setupTest.js
export function setupUserTest() {
  const mockDb = createMockDb();
  const userService = new UserService(mockDb);
  const testUser = createUser();
  return { mockDb, userService, testUser };
}

// In tests
test('registers user', async () => {
  const { userService, testUser } = setupUserTest();
  const result = await userService.registerUser(testUser);
  expect(result.id).toBeDefined();
});
```

### Use beforeEach Effectively

Share common setup, not state.

```javascript
// ✅ Good - share setup
describe('UserService', () => {
  let userService;

  beforeEach(() => {
    const mockDb = createMockDb();
    userService = new UserService(mockDb);
  });

  test('test 1', () => {
    // Use userService
  });

  test('test 2', () => {
    // Use userService (fresh instance)
  });
});

// ❌ Bad - sharing state
let userId;

beforeEach(() => {
  userId = '123'; // Don't share state
});
```

### Parameterize Similar Tests

Use `test.each` for data-driven tests.

```javascript
// ❌ Repetitive tests
test('validates valid email format 1', () => {
  expect(validateEmail('test@example.com')).toBe(true);
});

test('validates valid email format 2', () => {
  expect(validateEmail('user@domain.org')).toBe(true);
});

// ✅ Parameterized
test.each([
  ['test@example.com', true],
  ['user@domain.org', true],
  ['invalid-email', false],
  ['@example.com', false],
  ['user@', false]
])('validates email %s', (email, expected) => {
  expect(validateEmail(email)).toBe(expected);
});
```

---

## Async Test Best Practices

### Prefer Async/Await

```javascript
// ❌ Callback-based tests
test('loads data', (done) => {
  fetchData((data) => {
    expect(data).toBeDefined();
    done();
  });
});

// ✅ Async/await
test('loads data', async () => {
  const data = await fetchData();
  expect(data).toBeDefined();
});
```

### Proper Error Handling

```javascript
// ✅ Testing async errors
test('handles fetch error', async () => {
  await expect(fetchData('invalid')).rejects.toThrow('Data not found');
});

// ✅ Try/catch when needed
test('handles error and continues', async () => {
  try {
    await fetchData('invalid');
    fail('Should have thrown error');
  } catch (error) {
    expect(error.message).toBe('Data not found');
  }
});
```

### Avoid waitFor with Side Effects

```javascript
// ❌ Side effects in waitFor
await waitFor(() => {
  fireEvent.click(button); // Side effect!
  expect(mockFn).toHaveBeenCalled();
});

// ✅ Separate action and assertion
fireEvent.click(button);
await waitFor(() => expect(mockFn).toHaveBeenCalled());
```

---

## Reference

For implementation guidance:
- **compliance-checklist.md** - Verification checklist
- **maintenance-prioritization.md** - Test priority framework
- **cui-javascript-unit-testing skill** - Jest configuration and patterns
- **cui-cypress skill** - E2E testing standards
