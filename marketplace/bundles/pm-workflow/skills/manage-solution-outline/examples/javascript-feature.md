# Solution: Add Form Validation Web Component

plan_id: form-validation-component
created: 2025-12-10T10:00:00Z

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

Implement the core validation logic as a mixin/controller.

**Location**: `src/validation/ValidationController.js`

**Features**:
- Rule registration (required, minLength, maxLength, pattern, custom)
- Validation state management
- Error message handling
- Debounced validation for input events

### 2. Implement cui-validated-input component

Create the web component that wraps standard inputs.

**Location**: `src/components/cui-validated-input/cui-validated-input.js`

**Attributes**:
- `rules` - JSON or comma-separated rule names
- `error-message` - Custom error message
- `validate-on` - Event trigger (input, blur, submit)

**Slots**:
- Default slot for input element
- `error` slot for custom error display

### 3. Add form-level validation coordinator

Component to coordinate validation across a form.

**Location**: `src/components/cui-validated-form/cui-validated-form.js`

**Features**:
- Collect all validated inputs
- Prevent submit if invalid
- Focus first invalid field
- Form-level error summary

### 4. Create unit tests

**Test files**:
- `src/validation/ValidationController.test.js`
- `src/components/cui-validated-input/cui-validated-input.test.js`
- `src/components/cui-validated-form/cui-validated-form.test.js`

### 5. Add Cypress E2E tests

**Location**: `cypress/e2e/validation.cy.js`

**Scenarios**:
- Required field validation
- Pattern matching
- Form submission blocking
- Accessibility (aria-invalid, error associations)

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
