# Implementation Parameter Verification

**Never implement on ambiguous requirements.** Verify parameters are clear, complete, and unambiguous before writing code.

## Required Parameters

### types Parameter

Specify existing type(s), package(s), or names of types to be created.

**Verification:**
- Existing types: Use Grep to verify existence in codebase
- New types: Validate PascalCase naming, check for naming conflicts
- Packages: Verify package structure exists

### description Parameter

Detailed, precise description of what to implement. Must have specific and measurable requirements, clear acceptance criteria, and defined error handling approach.

### module Parameter

Module name for multi-module projects. Required when multiple `pom.xml` files exist.

**Detection:**
- Use Glob to find `pom.xml` files
- If count > 1: multi-module project, module required (or inferred from types)
- If count == 1: single-module, not required

## Ambiguity Detection

### Modal Verbs (Uncertain Requirements)

Flag: `(should|could|might|may) (probably|possibly|optionally|perhaps)`

- "should probably validate" → Replace with: "Validate inputs throwing IllegalArgumentException on null"
- "could validate" → Is validation required or optional?

### Vague Quantities

Flag: `some|several|a few|many|various`

- "Add some validation" → "Add null validation and range validation (0-100)"
- "Several test cases" → "5 test cases: success, null input, empty input, invalid format, boundary"

### Conditional Requirements

Flag: `if needed|as appropriate|when necessary|as required`

- "Handle errors as appropriate" → "Handle IOException by wrapping in UncheckedIOException"
- "Validate when necessary" → "Validate all inputs: null check, range check, format check"

## Missing Information Detection

### Error Handling

Check if description specifies:
- Exception types to throw
- Exception wrapping strategy
- Error logging requirements
- Recovery or retry logic

If missing, ask: "What exceptions should be thrown for invalid inputs?"

### Validation Requirements

Check if description specifies:
- Which fields to validate
- Validation rules (null, range, format)
- Validation failure behavior

If missing, ask: "Which parameters require validation? What are the valid ranges/formats?"

### Return Value Behavior

Check if description specifies:
- Return type
- Null return behavior (Optional vs null)
- Empty collection handling

If missing, ask: "Should method return Optional<T> or allow null?"

### Scope and Boundaries

Check if description specifies:
- Which classes/methods to modify
- Whether to create new types or modify existing
- Integration points with existing code

## Verification Workflow

### Step 1: Parse Parameters

Extract types, description, module from input.

### Step 2: Verify Types

```
For existing types:
  Grep codebase for "class TypeName" / "interface TypeName"
  Track: types_found, types_missing

For new types:
  Validate ^[A-Z][a-zA-Z0-9]*$ naming
  Check for naming conflicts
```

### Step 3: Analyze Description

Run ambiguity detection patterns against description text. Check for missing information in each category above.

### Step 4: Verify Module

```
If multi-module project and module provided:
  Verify module directory exists
If multi-module and no module:
  Infer from types or ask user
```

### Step 5: Decision Point

**All checks pass** (types found/valid, no ambiguity, all info present, module valid): Proceed with implementation.

**Any check fails**: Return verification failure with specific issues and questions.

## Error Response Format

```
VERIFICATION FAILED

Issues Found:
- Type 'UserService' not found in codebase (expected to exist)
- Description ambiguous: "should probably validate" - needs definitive requirement
- Missing information: No specification for error handling approach
- Module 'auth-service' not found (available: user-service, api-gateway)

Required Actions:
1. Confirm UserService location or provide creation details
2. Clarify validation requirements
3. Specify error handling pattern
4. Correct module name

Cannot proceed until these are resolved.
```

## Clarification Questions Format

```
CLARIFICATION NEEDED

1. Error Handling:
   Q: "How should IOException be handled?"
   Options: Wrap in RuntimeException | Propagate as checked | Return empty Optional | Retry N times

2. Validation Behavior:
   Q: "What should happen when validation fails?"
   Options: Throw IllegalArgumentException | Return Optional.empty() | Return boolean false

3. Null Handling:
   Q: "Should method return null or Optional?"
```

## Integration with Workflows

```
java-implement-code:
  Step 1: Verify implementation parameters  ← THIS STANDARD
    If FAIL: Return clarification questions, STOP
    If PASS: Continue to build precondition check
```

## References

- [Build Precondition Pattern](build-precondition-pattern.md)
