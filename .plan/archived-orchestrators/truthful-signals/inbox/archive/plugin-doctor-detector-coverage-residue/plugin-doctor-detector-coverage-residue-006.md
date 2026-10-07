envelope_version=1
sender_type=plan
sender_id=plugin-doctor-detector-coverage-residue
epic=truthful-signals
kind=candidate-lesson
created=2026-08-25T07:37:59Z

component=project:finalize-step-deploy-target
category=bug
created=2026-08-25

# finalize-step-deploy-target's SKILL.md documents a TOON stdout contract the generator does not emit

## Context

`.claude/skills/finalize-step-deploy-target/SKILL.md` section "Parse the result" instructs the
executor to branch on `status: success` vs `status: error` and to read `emitted_count` for the display
detail, prefaced by "The script returns a TOON document on stdout describing the run." The generator
actually emits two plain-text lines on stdout with no `status` field and no `emitted_count` key (e.g.
"claude: produced 1176 entries" and "claude: stamped version ... into 11 bundle plugin.json; emitted
dist-manifest.json"). The count is recoverable only by scraping "produced N entries" from prose.

## Root cause

Same doc-prescribes-a-shape-no-code-emits class already recorded twice in this plan's own findings
(`28161e` -- automatic-review's `--enabled-bots`; `776360` -- `baseline_drift` as a documented
`record-dispatch-boundary` termination cause the enum cannot accept), now a third pair of surfaces.
Two smaller co-located defects in the same document: an example `mark-step-done` invocation uses the
notation `plan-marshall:manage-status:manage_status` (underscore), which the executor rejects as
unknown; and the documented invocation is `uv run python ...` while `uv` is not on PATH in a plain
shell -- the runnable form is the pyprojectx alias `./pw generate-claude`.

## Proposed action

Correct the SKILL.md's "Parse the result" section to describe the generator's actual plain-text
output (or change the generator to emit the documented TOON shape), and fix the two co-located
notation/invocation errors in the same edit.

## Evidence

- Finding e2b602 in this plan's qgate store, hit live while running this step
- aspect: script_failure_analysis -- doc-prescribes-a-flag/value-no-script-declares is this plan's
  most-recurring finding class outside its own deliverable set (3 instances: 28161e, 776360, e2b602)
