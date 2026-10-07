envelope_version=1
sender_type=plan
sender_id=finalize-step-records-are-prose-not-facts
epic=truthful-signals
kind=candidate-lesson
created=2026-08-02T11:38:45Z

component=plan-marshall:extension-api
category=anti-pattern
bundle=plan-marshall
source_plan=finalize-step-records-are-prose-not-facts
source_pr=1076
source_finding=497cf4

# A test reaching for a PRIVATE helper to assert a documented PUBLIC field is a contract-drift tell

## Observation

The plan documented, in `extension-api/standards/ext-point-finalize-step.md`, that the
`find_implementors()` record carries a `records_facts` key, and stated affirmatively that
*"records_facts is present only for a step that declares the conditional field (absent means no structured-fact obligation)"*.

The live emitter never produces that key. `_build_implementor_record` in
`extension-api/scripts/extension_discovery.py` builds the record from `_IMPLEMENTOR_FRONTMATTER_KEYS` and
conditionally adds only `verification_profile`; the token `records_facts` appears nowhere in the
extension-api scripts. A live `extension_discovery implementors` run returned the header
`implementors{name,order,default_on,presets,canonicals,description,source,path}` — no `records_facts` column.

A consumer following the documented shape would call `record.get('records_facts')` and silently receive
`None` for every step. That is a **vacuous derivation**: the consumer's set-guard would be empty and would
pass unconditionally.

## The tell that was available the whole time

**The plan's own contract test routed around the gap.** `_declared_facts` called the *private*
`extension_discovery._read_frontmatter_fields` on the doc path rather than reading the field off the public
record. The author wrote that bypass while the doc claimed the public record carried the field — and did not
read the bypass as evidence.

That bypass was a free, in-repo, pre-merge signal that the documented public shape was false. It was
written, committed, and pushed before pre-submission self-review caught the drift by a different route.

## Rule

When a test cannot make its assertion through the documented public API and reaches for a private helper,
an internal module attribute, or a re-parse of the underlying source, that bypass is **evidence about the
public API, not a test-convenience choice**. Before writing it, answer explicitly:

- Does the public surface actually carry what the doc says it carries?
- If not — is the correct fix to extend the emitter, or to correct the doc?

Either answer is fine. Silently bypassing and leaving the doc asserting the untrue shape is not.

## Aggravating factor: an affirmative false claim, not mere incompleteness

The same documented block already omitted `canonicals` and `verification_profile`, which ARE emitted.
Omission is incompleteness — a reader loses nothing they were promised. `records_facts` was different: the
doc **added** a field and **explained its absence semantics**, so a reader who checked `record.get(...) is None`
would conclude "this step declares no obligation" when the truth was "this record never carries the key".
An affirmative false claim about a field's absence semantics is strictly worse than omitting the field.

## Resolution in-plan

The `find_implementors` docstring was corrected to the record shape the emitter actually produces (adds
`canonicals`, drops the false `records_facts` claim) and now states explicitly that the conditional
obligation fields are read from frontmatter via `_read_frontmatter_fields`, not from the record.
