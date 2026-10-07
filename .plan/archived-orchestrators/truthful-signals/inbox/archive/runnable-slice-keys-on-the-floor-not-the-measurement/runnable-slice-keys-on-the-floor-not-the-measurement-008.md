envelope_version=1
sender_type=plan
sender_id=runnable-slice-keys-on-the-floor-not-the-measurement
epic=truthful-signals
kind=candidate-lesson
created=2026-07-29T04:55:57Z

component=manage-run-config
category=bug
created=2026-07-29

# Hint constants unbound to tests let a rename silently break the contract

The `_HINT_*` constants were never imported by any test — six call sites
hardcoded the literal strings instead. That meant renaming a hint token would
have broken the resolve-hint contract with ZERO test failures; nothing was
actually pinning the string values to the constant definitions. Fixed by binding
all six sites to the constants (including the new `_HINT_UNMEASURED`) instead of
literal strings.

## Impact

When a module exposes named string/enum constants that downstream code and
tests both need to agree on, verify tests import and assert against the
constant itself, not a hardcoded literal — a hardcoded literal at a test site
passes today but provides zero protection against the constant's value
changing tomorrow.
