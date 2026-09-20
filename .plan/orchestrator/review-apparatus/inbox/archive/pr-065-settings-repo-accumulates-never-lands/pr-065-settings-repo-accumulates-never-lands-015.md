envelope_version=1
sender_type=plan
sender_id=pr-065-settings-repo-accumulates-never-lands
epic=review-apparatus
kind=candidate-lesson
created=2026-09-14T19:22:26Z

component=pm-plugin-development:plugin-doctor
category=bug
source_signal=qgate_finding
source_plan=pr-065-settings-repo-accumulates-never-lands
evidence=qgate findings 97e42b, 8dc9fc, 1d278d, 50a235, 150831, bcf4a8, 41aa89, a5af33, b7a0da, ad72c9 (all rejected), 2c2d94 (taken_into_account)

# 10 lint findings against 5 files in 4 bundles, all false: the rule read an unconfident parser surface as confident

`scan_manage_invocation` reported 10 `manage-invocation-invalid` errors claiming
documented flags were unregistered. Every one was refuted against live argparse:
`github_ops repo label ensure` declares `--color`, `--description` and a REQUIRED
`--label`; `profiles list` declares `--module`; `profiles classify` declares a
REQUIRED `--profile-id`; `ascii_diagrams check` / `fix` declare `--path`.

Root cause established by derivation, not inference:
`argparse_surface._derive_node` registers an unprobeable child as
`ParserNode(flags_confident=False, ...)` with an EMPTY flag set, and its module
docstring makes fail-closed-on-uncertainty normative.
`_analyze_manage_invocation.py` never reads `flags_confident` anywhere, so an
empty-because-unknown flag set is consumed as a confident "declares no flags" and
`known_flags` collapses to `UNIVERSAL_FLAGS` — which is exactly the accept-set
every one of the 10 findings reported. The sibling rule
`_analyze_argument_naming.py` DOES guard on it.

## Two corroborations worth keeping

- For `--label` and `--profile-id` the run emitted an unknown-flag finding while
  emitting NO missing-required-flag finding for the same flag. A genuinely
  derived surface cannot produce both of those at once; an empty one can.
- `ascii_diagrams check` is a ONE-level subcommand and still collapsed, which
  refutes the competing "the rule only mishandles deep nesting" hypothesis.

## Candidate rule

Every consumer of a confidence-carrying struct must read the confidence field.
One sibling rule guards it and one does not, from the same producer, in the same
bundle — so the producer's normative docstring is not reaching its consumers. A
test asserting that no analyzer validates against a node with
`flags_confident=False` would close the class rather than this instance.
