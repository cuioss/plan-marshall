= Implementation Parameter Verification
:toc: left
:toclevels: 3
:sectnums:

== Overview

This standard defines parameter verification requirements for Java implementation tasks to detect ambiguities, missing information, and unclear requirements before beginning implementation work.

== Core Principle

**Never implement on ambiguous requirements.** Always verify parameters are clear, complete, and unambiguous before writing code.

== Required Parameters

=== types Parameter

**Purpose:** Specify existing type(s), package(s), or name(s) of types to be created

**Format:**

* Existing types: Fully qualified names or simple names to search for
* New types: Names following Java naming conventions
* Packages: Package paths where work will be performed

**Verification:**

[source]
----
If existing types:
  Use Grep to verify existence in codebase
  Track: types_found, types_missing

If new types:
  Validate naming follows Java conventions (PascalCase for classes)
  Check for naming conflicts

If package:
  Verify package structure exists
  Identify module location
----

**Examples:**

* `types=UserService` - Find existing UserService class
* `types=com.example.auth.TokenValidator` - Find specific class
* `types=com.example.model` - Work in model package
* `types=UserRepository` - Create new UserRepository class

=== description Parameter

**Purpose:** Detailed, precise description of what to implement

**Quality Criteria:**

* Specific and measurable requirements
* No ambiguous language
* Clear acceptance criteria
* Defined error handling approach

**Verification:**

Check for ambiguous patterns:

* "maybe", "possibly", "could", "might"
* "probably", "perhaps", "optionally"
* "if needed", "as appropriate"
* Vague quantities: "some", "several", "a few"

**Bad Examples:**

* "Add validation, maybe check for nulls"
* "Should probably log errors"
* "Handle exceptions as appropriate"
* "Add some tests if needed"

**Good Examples:**

* "Add null validation throwing IllegalArgumentException"
* "Log errors at ERROR level with full stack trace"
* "Handle IOException by wrapping in RuntimeException"
* "Add unit tests covering success and null input cases"

=== module Parameter

**Purpose:** Module name for multi-module projects (optional)

**When Required:**

* Multi-module Maven projects with multiple pom.xml files
* When changes span multiple modules

**When Optional:**

* Single-module projects
* When module can be inferred from types parameter

**Verification:**

[source]
----
Use Glob to find pom.xml files
Count pom.xml files found

If count > 1:
  Project is multi-module
  If module parameter provided:
    Verify module exists in project
  Else:
    Infer from types parameter or ask user

If count == 1:
  Project is single-module
  Module parameter not required
----

== Ambiguity Detection

=== Ambiguous Language Patterns

==== Modal Verbs (Uncertain Requirements)

**Problematic patterns:**

* "should probably" → What are the definitive requirements?
* "could validate" → Is validation required or optional?
* "might need to" → Is this needed or not?

**Detection:**

Search description for: `(should|could|might|may)\s+(probably|possibly|optionally|perhaps)`

**Resolution:**

Replace with definitive requirements:

* "Validate inputs throwing IllegalArgumentException on null"
* "Log errors at ERROR level"
* "Handle IOException by retrying 3 times then failing"

==== Vague Quantities

**Problematic patterns:**

* "Add some validation" → Which validations exactly?
* "Several test cases" → How many? Which scenarios?
* "A few error checks" → Which errors?

**Detection:**

Search for: `(some|several|a few|many|various)`

**Resolution:**

Specify exact requirements:

* "Add null validation and range validation (0-100)"
* "Add 5 test cases: success, null input, empty input, invalid format, boundary"
* "Check for FileNotFoundException and IOException"

==== Conditional Requirements

**Problematic patterns:**

* "If needed, add logging" → When is it needed?
* "Handle errors as appropriate" → What's appropriate?
* "Validate when necessary" → When is it necessary?

**Detection:**

Search for: `(if needed|as appropriate|when necessary|as required)`

**Resolution:**

Make requirements explicit:

* "Add DEBUG logging for method entry/exit"
* "Handle IOException by wrapping in UncheckedIOException"
* "Validate all inputs: null check, range check, format check"

=== Missing Information Detection

==== Error Handling

**Check if description specifies:**

* Exception types to throw
* Exception wrapping strategy
* Error logging requirements
* Recovery or retry logic

**If missing, ask:**

* "What exceptions should be thrown for invalid inputs?"
* "How should checked exceptions be handled?"
* "Should errors be logged? At what level?"

==== Validation Requirements

**Check if description specifies:**

* Which fields to validate
* Validation rules (null, range, format)
* Validation failure behavior

**If missing, ask:**

* "Which parameters require validation?"
* "What are the valid ranges/formats?"
* "Should validation throw exceptions or return boolean?"

==== Return Value Behavior

**Check if description specifies:**

* Return type (if method signature not provided)
* Null return behavior (Optional vs null)
* Empty collection handling

**If missing, ask:**

* "Should method return Optional<T> or allow null?"
* "Return empty collection or null when no results?"

==== Scope and Boundaries

**Check if description specifies:**

* Which classes/methods to modify
* Whether to create new types or modify existing
* Integration points with existing code

**If missing, ask:**

* "Modify existing UserService or create new class?"
* "Add method to existing interface or create new interface?"
* "Should this integrate with existing ValidationService?"

== Verification Workflow

=== Step 1: Parse Parameters

Extract and validate:

* types → List of type names/packages
* description → Full requirement text
* module → Module name (if multi-module)

=== Step 2: Verify Types Exist/Valid

For existing types:

[source,bash]
----
# Search codebase
grep -r "class TypeName" src/
grep -r "interface TypeName" src/

# Verify found
if found:
  Track: types_found += TypeName
else:
  Track: types_missing += TypeName
----

For new types:

[source]
----
# Validate naming
if matches ^[A-Z][a-zA-Z0-9]*$:
  Valid Java class name
else:
  Invalid naming

# Check conflicts
grep -r "class TypeName" src/
if found:
  Naming conflict detected
----

=== Step 3: Analyze Description

Run ambiguity detection:

[source,python]
----
ambiguous_patterns = [
    r'\b(should|could|might|may)\s+(probably|possibly|optionally)',
    r'\b(some|several|a few|many|various)\b',
    r'\b(if needed|as appropriate|when necessary|as required)\b'
]

for pattern in ambiguous_patterns:
    matches = re.findall(pattern, description, re.IGNORECASE)
    if matches:
        flag_ambiguity(matches)
----

Check for missing information:

[source]
----
Check error handling specified:
  - Exception types mentioned?
  - Wrapping strategy defined?
  - Logging requirements stated?

Check validation requirements:
  - Fields to validate listed?
  - Validation rules defined?
  - Failure behavior specified?

Check return value behavior:
  - Return type specified?
  - Null handling defined?
  - Empty cases covered?
----

=== Step 4: Verify Module (If Multi-Module)

[source,bash]
----
# Find all pom.xml files
find . -name "pom.xml" -type f

# Count modules
module_count=$(find . -name "pom.xml" -type f | wc -l)

if module_count > 1:
  # Multi-module project
  if module parameter provided:
    # Verify exists
    if [ -d "$module" ]; then
      Valid module
    else:
      Invalid module - list available
    fi
  else:
    # Try to infer from types
    # Or ask user to specify
----

=== Step 5: Decision Point

If all checks pass:

* All types found or valid new names
* No ambiguous language in description
* All required information present
* Module valid (if multi-module)

**Action:** Proceed with implementation

If any check fails:

* Types missing when expected to exist
* Ambiguous language detected
* Missing required information
* Invalid module

**Action:** Return verification failure with specific issues and questions

== Error Response Format

=== Verification Failure Response

[source]
----
VERIFICATION FAILED

Issues Found:
- Type 'UserService' not found in codebase (expected to exist)
- Description ambiguous: "should probably validate" - needs definitive requirement
- Missing information: No specification for error handling approach
- Module 'auth-service' not found (available: user-service, api-gateway)

Required Actions:
1. Confirm UserService location or provide creation details
2. Clarify validation requirements (what validates what? which fields? what rules?)
3. Specify error handling pattern (exceptions? Optional? error codes?)
4. Correct module name or omit for single-module build

Cannot proceed until these are resolved.
----

=== Clarification Questions Format

[source]
----
CLARIFICATION NEEDED

The following requirements are unclear:

1. Error Handling:
   Q: "How should IOException be handled?"
   Options:
   - Wrap in RuntimeException
   - Let it propagate as checked exception
   - Catch and log, return empty Optional
   - Retry N times then fail

2. Validation Behavior:
   Q: "What should happen when validation fails?"
   Options:
   - Throw IllegalArgumentException
   - Return Optional.empty()
   - Return boolean false
   - Log warning and proceed

3. Null Handling:
   Q: "Should method return null or Optional?"
   Current description says "return user" but doesn't specify null behavior.

Please clarify these points before implementation.
----

== Script Integration

=== verify-implementation-params.py

The verification script implements automated ambiguity detection:

**Input:** description text

**Output:** JSON with detected issues

[source,json]
----
{
  "ambiguities": [
    {
      "pattern": "should probably",
      "context": "should probably validate inputs",
      "issue": "Uncertain requirement"
    }
  ],
  "missing_info": [
    {
      "category": "error_handling",
      "question": "How should exceptions be handled?"
    }
  ],
  "suggestions": [
    "Specify exact validation rules",
    "Define exception handling strategy"
  ]
}
----

**Usage in workflow:**

[source]
----
1. Run verify-implementation-params.py on description
2. Review JSON output for issues
3. If issues found, return clarification questions
4. If clean, proceed with implementation
----

== Best Practices

=== For Task Requesters

**DO:**

* Use specific, measurable language
* Define all error handling explicitly
* Specify validation rules completely
* List acceptance criteria

**DON'T:**

* Use modal verbs (should, could, might)
* Leave error handling implicit
* Use vague quantities (some, several)
* Assume context is understood

=== For Implementers

**DO:**

* Always run verification before implementation
* Ask clarifying questions immediately
* Document assumptions if proceeding
* Confirm ambiguities with task requester

**DON'T:**

* Implement on ambiguous requirements
* Guess at undefined behavior
* Skip verification to save time
* Proceed with missing information

== Examples

=== Example 1: Clear Requirements (PASS)

**Input:**

[source]
----
types: UserValidator
description: |
  Add validateEmail method to UserValidator class.

  Method signature: public void validateEmail(String email)

  Validation rules:
  - Throw IllegalArgumentException if email is null
  - Throw IllegalArgumentException if email doesn't match pattern: ^[A-Za-z0-9+_.-]+@(.+)$
  - Log validation failures at WARN level with message "Invalid email: {email}"

  No return value needed (void).
module: user-service
----

**Verification Result:** ✅ PASS

* Types found: UserValidator exists
* No ambiguous language
* Error handling specified (IllegalArgumentException)
* Validation rules explicit (null check, regex pattern)
* Return behavior clear (void)
* Module valid

=== Example 2: Ambiguous Requirements (FAIL)

**Input:**

[source]
----
types: UserService
description: |
  Add some validation to the user creation logic.
  Should probably check if the email is valid.
  Maybe log errors if needed.
module: user-service
----

**Verification Result:** ❌ FAIL

**Issues Found:**

* Ambiguous: "some validation" - which validations?
* Ambiguous: "should probably check" - is this required or optional?
* Ambiguous: "Maybe log errors" - should it log or not?
* Ambiguous: "if needed" - when is it needed?
* Missing: No specification of exception handling
* Missing: No definition of "valid email"
* Missing: No logging level specified

**Required Actions:**

1. Specify exact validations required (null check? format check? uniqueness check?)
2. Confirm email validation is required (not optional)
3. Define "valid email" (regex pattern? format rules?)
4. Specify error handling (throw exception? return boolean?)
5. Clarify logging requirements (always log? what level? what message?)

== Integration with Workflows

=== java-implement-code Command

**Step 1:** Verify implementation parameters

[source]
----
Execute verify-implementation-params workflow:
  Input: description text
  Output: verification result (pass/fail)

If FAIL:
  Return clarification questions
  STOP - do not proceed

If PASS:
  Continue to build precondition check
----

=== verify-implementation-readiness Workflow

Reference this standard in java-core SKILL.md:

[source,yaml]
----
workflow: verify-implementation-readiness
parameters:
  - description: string (required)
  - types: string (required)
  - module: string (optional)

steps:
  1. Parse parameters
  2. Verify types exist/valid
  3. Run ambiguity detection (verify-implementation-params.py)
  4. Check missing information
  5. Verify module (if multi-module)
  6. Return: pass/fail with specific issues

references:
  - standards/implementation-verification.md
  - scripts/verify-implementation-params.py
----

== References

* Java Naming Conventions
* CUI Java Core Standards
* Build Precondition Pattern (build-precondition-pattern.md)
