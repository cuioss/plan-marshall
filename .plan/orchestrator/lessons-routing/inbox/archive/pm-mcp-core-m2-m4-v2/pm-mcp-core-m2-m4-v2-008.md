envelope_version=1
sender_type=orchestrator
sender_id=pm-mcp-core-m2-m4-v2
epic=lessons-routing
kind=candidate-lesson
created=2026-11-11T08:05:38Z

# corpus surfaces claims a whole tree for a bare directory entry in `## Expected Surface`, and nothing warns the spec author

From the verifying session of the schema transition of the epic `pm-mcp-core-m2-m4-v2` (checked 2026-11-10, forwarded 2026-11-11 by the orchestrator of that epic; the original is `schema-transition-003.md` § 2, a `finding` addressed to the skill owner).

A bare directory entry such as `doc/` in the `## Expected Surface` section of a staged plan spec claims the whole tree for the disjointness gate (`plan-marshall:plan-orchestrator` `corpus surfaces` and `corpus cross-check`). In that epic one such entry produced 89 false gate overlaps and a false overlap prompt (PLAN-V2-119 against 121, "10 files"). Reworded to 13 declarative file entries, the overlap went to 0. A spec author gets no warning when an entry is a directory, so the over-claim is invisible until the gate refuses or prompts.

Suggested remedies, either or both (the owner decides):

- `corpus surfaces` reports a warning for an entry whose `kind` is `directory` (or `recursive_glob`), naming the entry and the number of paths it claims, so the author sees the over-claim when the spec is staged.
- The plan-spec template (`templates/plan-spec.md`) states under `## Expected Surface`: "name files, never a directory, unless the plan really edits the whole tree".

It belongs to `plan-marshall` (the skill `plan-orchestrator` and its spec parser), not to the pm-mcp-core epic's plans.
