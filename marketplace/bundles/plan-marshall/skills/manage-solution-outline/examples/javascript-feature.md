# Solution: Add Form Validation Web Component

plan_id: form-validation-component
created: 2025-12-10T10:00:00Z
compatibility: breaking — Clean-slate approach, no deprecation nor transitionary comments

## Summary

Create a reusable form validation web component that provides declarative validation rules, real-time feedback, and accessibility support.

## Overview

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                      Form Validation Components                              │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                     <cui-validated-form>                             │   │
│  │                                                                      │   │
│  │  • Coordinates validation across inputs                             │   │
│  │  • Prevents submit if invalid                                       │   │
│  │  • Focus management                                                 │   │
│  │                                                                      │   │
│  │  ┌────────────────────┐  ┌────────────────────┐                    │   │
│  │  │<cui-validated-input│  │<cui-validated-input│   ...              │   │
│  │  │ rules="required"   │  │ rules="email"      │                    │   │
│  │  │                    │  │                    │                    │   │
│  │  │  ┌──────────────┐  │  │  ┌──────────────┐  │                    │   │
│  │  │  │ <input>      │  │  │  │ <input>      │  │                    │   │
│  │  │  └──────────────┘  │  │  └──────────────┘  │                    │   │
│  │  └─────────┬──────────┘  └─────────┬──────────┘                    │   │
│  │            │                       │                                │   │
│  └────────────┼───────────────────────┼────────────────────────────────┘   │
│               │                       │                                     │
│               ▼                       ▼                                     │
│        ┌──────────────────────────────────────────┐                        │
│        │          ValidationController            │                        │
│        │                                          │                        │
│        │  • Rule registration                     │                        │
│        │  • State management                      │                        │
│        │  • Error messages                        │                        │
│        │  • Debounced validation                  │                        │
│        └──────────────────────────────────────────┘                        │
│                                                                              │
├─────────────────────────────────────────────────────────────────────────────┤
│  src/validation/ValidationController.js                                     │
│  src/components/cui-validated-input/cui-validated-input.js                  │
│  src/components/cui-validated-form/cui-validated-form.js                    │
└─────────────────────────────────────────────────────────────────────────────┘
```

## Deliverables

### 1. Create base ValidationController class

Implement the core validation logic as a mixin/controller with rule registration, state management, and debounced validation.

**Metadata:**
- change_type: feature
- execution_mode: automated
- domain: javascript
- module: validation
- depends: none

**Profiles:**
- implementation
- module_testing

**Affected files:**
- `src/validation/ValidationController.js`
- `src/validation/ValidationController.test.js`

**Change per file:** Create `ValidationController.js` with rule registration (required, minLength, maxLength, pattern, custom), validation state management, error message handling, and debounced validation for input events. Create corresponding unit test file covering all rule types and state transitions.

**Verification:**
- Command: `npm test -- --testPathPattern=ValidationController`
- Criteria: All unit tests pass, no lint errors

**Success Criteria:**
- All built-in rule types (required, minLength, maxLength, pattern, custom) are implemented and tested
- Debounced validation fires after configurable delay
- Error message API supports both default and custom messages

### 2. Implement cui-validated-input component

Create the web component that wraps standard inputs with declarative validation rules and accessible error display.

**Metadata:**
- change_type: feature
- execution_mode: automated
- domain: javascript
- module: cui-validated-input
- depends: 1

**Profiles:**
- implementation
- module_testing

**Affected files:**
- `src/components/cui-validated-input/cui-validated-input.js`
- `src/components/cui-validated-input/cui-validated-input.test.js`

**Change per file:** Create custom element `cui-validated-input` supporting `rules`, `error-message`, and `validate-on` attributes, with a default slot for the input element and an `error` slot for custom error display. Create unit tests covering attribute handling, slot projection, and validation triggering.

**Verification:**
- Command: `npm test -- --testPathPattern=cui-validated-input`
- Criteria: All unit tests pass, no lint errors

**Success Criteria:**
- Component registers as a custom element without errors
- `rules`, `error-message`, and `validate-on` attributes are all functional
- aria-invalid and aria-describedby are set correctly on validation state changes

### 3. Add form-level validation coordinator

Component to coordinate validation across all inputs in a form, preventing submission when invalid.

**Metadata:**
- change_type: feature
- execution_mode: automated
- domain: javascript
- module: cui-validated-form
- depends: 1,2

**Profiles:**
- implementation
- module_testing

**Affected files:**
- `src/components/cui-validated-form/cui-validated-form.js`
- `src/components/cui-validated-form/cui-validated-form.test.js`

**Change per file:** Create custom element `cui-validated-form` that collects all nested `cui-validated-input` elements, intercepts form submission to prevent it when any input is invalid, focuses the first invalid field, and optionally renders a form-level error summary. Create unit tests for coordination logic and submit prevention.

**Verification:**
- Command: `npm test -- --testPathPattern=cui-validated-form`
- Criteria: All unit tests pass, no lint errors

**Success Criteria:**
- Form submission is blocked when any contained input is invalid
- First invalid field receives focus on blocked submission
- Form-level error summary lists all current validation errors

### 4. Add Cypress E2E tests

Integration tests covering full form validation scenarios including accessibility requirements.

**Metadata:**
- change_type: feature
- execution_mode: automated
- domain: javascript
- module: e2e
- depends: 1,2,3

**Profiles:**
- implementation

**Affected files:**
- `cypress/e2e/validation.cy.js`

**Change per file:** Create Cypress E2E test file covering required field validation, pattern matching, form submission blocking, and accessibility attributes (aria-invalid, error associations).

**Verification:**
- Command: `npx cypress run --spec cypress/e2e/validation.cy.js`
- Criteria: All E2E scenarios pass in headless mode

**Success Criteria:**
- Required field validation triggers on the configured event
- Pattern mismatches display the correct error message
- Form submission is blocked and focus moves to the first invalid field
- aria-invalid and error associations are present and correct for screen reader support

## Approach

1. Build ValidationController with TDD
2. Create cui-validated-input using controller
3. Add form coordinator
4. E2E tests for integration scenarios

## Dependencies

None - vanilla web components only.

## Risks and Mitigations

- **Risk**: Browser compatibility for web components
  - **Mitigation**: Use polyfills, test in target browsers
