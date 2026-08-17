> ⛔ **FIRST INSTRUCTION — do not skip, do not delete, do not move below the title.**
>
> Before reading the rest of this plan and before any other action, load the working contract that
> governs this run:
>
> ```text
> Skill: cloud-plan-lane
> ```
>
> It owns the branch/PR/review-comment cycle, the build gate, the pre-PR verification sub-agent, the
> run report, and the closing self-check. **Nothing in this plan overrides it** — where this plan and
> the contract disagree, the contract wins, and the disagreement is reported.
>
> If the skill cannot be loaded, **stop and report the run blocked**. Do not reconstruct the workflow
> from this file: the parts that matter most — the merge gate, the verification dispatch, the report
> — are not in here.
>
> This block is part of the plan, not part of the template. It survives into every copy.

# Every structural source directive is registered, and normative prose names acts, not tools

**Epic:** multiplattform (standalone — no orchestrator ledger; scoping brief in
`doc/plans/multiplattform/README.md`, evidence in `doc/plans/multiplattform/reference/` — full
paths, because the lane moves this plan one directory deeper)
**Branch prefix:** feature — extends the fail-closed transform vocabulary

## Problem

`marketplace/targets/body_transform_engine.py`'s `STRUCTURAL_VOCABULARY` holds only the `Skill:`
directive and `/slash` commands, so the `Read: {path}` full-line load directive — the structural
sibling of `Skill:`, used across the bundles (~130 occurrences; re-derive) — is invisible to
`assert_source_vocabulary_mapped` and emits verbatim to every non-verbatim target. Beyond the
directive, several bundle files carry **normative** Claude tool invocations the registered idiom
rewrites cannot reach: a full `AskUserQuestion:` YAML call block (the Claude parameter model as
workflow), byte-identical bare escalation lines in six ext-triage standards, "using the Write
tool" steps, literal `Read(file_path=…)` call syntax, a `CLAUDE.md`-as-authority citation, and a
README slash-invocation form outside the body-transform path. The registry is
`doc/plans/multiplattform/reference/marketplace-audit.md` §M1–§M2.

## Goal

The build fails closed on an unmapped `Read:` directive exactly as it does for `Skill:`, and no
audited bundle file instructs a Claude tool invocation outside the registered idiom carriers.

## Deliverables

1. **D1 — `read_directive` in the structural vocabulary** — engine matcher + per-target template
   (`mapping.json::directive_rewrites.read_directive`) mirroring `skill_directive`; the Claude
   target stays verbatim; fail-closed on a non-verbatim target without the template.
   *Done when:* generation rewrites a fixture `Read:` line per the OpenCode template, fails
   closed without one (red-first test), and the Claude equality check still passes.
2. **D2 — Call-schema block neutralized** — `manage-maven-profiles/SKILL.md` Step 2 states the
   question and option set as data ("escalate to the operator with these options"), not the
   Claude argument schema.
   *Done when:* no `AskUserQuestion:`-keyed block with `header`/`options`/`multiSelect` remains
   in the file; the step's decision content is preserved.
3. **D3 — ext-triage escalation lines neutralized** — in all six `pr-comment-disposition.md`
   files (re-derive the set) the bare ESCALATE-row and flow-branch lines name the act
   ("escalate to the operator"), keeping the one backticked `AskUserQuestion` as the
   registered-idiom carrier; the six files stay byte-identical to each other.
   *Done when:* a diff across the six files shows identical content and only the backticked
   occurrence of the tool name remains in each.
4. **D4 — Remaining normative tool-prose sites** — the M2-listed sites (Write-tool steps in
   `recipe-cui-logging-enforce` and the three pm-documents recipes, `link-verification.md` call
   syntax and blocks, the `testing-pytest.md` `CLAUDE.md` citation, the `pm-dev-java-cui/README.md`
   slash form, `content-review.md` second Claude mention) reworded to name the act or the owning
   rule.
   *Done when:* each named site is reworded; a sweep of the touched files finds no remaining
   unbackticked normative tool-invocation instruction.

## Out of scope

- **Registering `Write`/`Edit`/`Glob`/`Grep` as rewrite idioms** — no live-runtime evidence yet
  that a rewrite (vs. prose neutrality) is needed; the inventory §C keeps that gated on the
  validation protocol. Excluded so this plan does not speculate about an unvalidated runtime.
- **The `persona-plan-marshall-agent` tool-usage surfaces** — registered in inventory §C with the
  same validation gate; a much larger rewrite with its own risk profile.
- **plugin-doctor/authoring vocabulary** — plan `060`'s surface.

## Expected surface

- `marketplace/targets/body_transform_engine.py`, `marketplace/targets/opencode/mapping.json`,
  `marketplace/targets/opencode/transforms.md`, `test/marketplace/targets/**` — D1
- The M2-named bundle files across pm-dev-java, pm-dev-java-cui, pm-dev-python, pm-dev-oci,
  pm-dev-frontend, pm-documents, pm-requirements — D2–D4

## Claim labels

| Claim | Label | Confirm/refute artifact |
|---|---|---|
| `STRUCTURAL_VOCABULARY` holds only `skill_directive` and `slash_command` | OBSERVED | `body_transform_engine.py` — re-read before building |
| The `Read:` directive class spans ~130 occurrences repo-wide | OBSERVED, count is a lead | re-derive by full-line regex before D1; the hit list is the work list |
| The six ext-triage escalation blocks are byte-identical | OBSERVED | the six files — re-hash before editing |
| The `AskUserQuestion:` YAML block is unreachable by every existing transform | OBSERVED | `manage-maven-profiles/SKILL.md` + the engine's matchers |
| No further normative call-schema block exists in the bundles | HYPOTHESIS | sweep for fenced blocks keyed by a Claude tool name; extra hits are reported and folded into D4 |

## Verification

- `./pw verify` (Python changes — the build gate applies); D1's fail-closed test red-first.
- `generate.py --target all` exits 0 on the edited tree.
- The pre-PR verification sub-agent sweeps the changed values' consumers by kind, and **cold-reads**
  one rewritten ext-triage standard to report whether the escalation instruction still
  unambiguously directs an operator escalation — the wording failed if not.

## Notes

- Shares `marketplace/targets/**` with plan `020` — not concurrent with it. Not concurrent with
  `050`-overlapping surfaces in `060` (none: `060` is pm-plugin-development-only) — see the epic
  README concurrency table.
- Evidence registry: `doc/plans/multiplattform/reference/marketplace-audit.md` §M1–§M2.
