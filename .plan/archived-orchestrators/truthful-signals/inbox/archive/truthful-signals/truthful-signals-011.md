envelope_version=1
sender_type=orchestrator
sender_id=truthful-signals
epic=truthful-signals
kind=finding
created=2026-09-15T07:12:26Z

# `detect-suspicious` reports a clean allow list while the harness warns about it on every startup

Observed 2026-09-15 in this repository. Claude Code printed a startup warning about a rule
standing in `.claude/settings.local.json`:

```text
Permission allow rule (.claude/settings.local.json):
Bash(cp -r .plan/project-architecture/* /tmp/arch-snap) has a wildcard before the rest of
the command, so it also matches any options inserted at that position and approves them
without a prompt.
```

The rule is now fixed in place (the glob replaced by the exact directory,
`Bash(cp -r .plan/project-architecture /tmp/arch-snap)`), and a sweep of all three live allow
lists — `.claude/settings.local.json` (46 rules), `.claude/settings.json` (7),
`~/.claude/settings.json` (184) — finds no remaining rule of this shape. **The single rule is
not the finding.** The finding is that our own permission tooling called that allow list clean
for as long as the rule stood.

## The signal that lied

`permission_doctor detect-suspicious` is the surface an operator runs to ask "is my allow list
sound?". It answers by matching each rule against `SUSPICIOUS_PATTERNS`
(`marketplace/bundles/plan-marshall/skills/tools-permission-doctor/scripts/permission_doctor.py`,
~lines 200-350) — a hand-maintained list of roughly twenty regexes, every one of which names a
dangerous **target**: `sudo`, `rm -rf`, `dd`, `mkfs`, `fdisk`, writes under `/tmp`, `/proc`,
`/sys`, `/boot`, `/root`, reads of `/Users/**`, unrestricted `curl`/`wget`, piping to a shell.

Not one pattern covers **malformed grammar** — a rule whose wildcard spans an argument boundary
and therefore silently pre-approves any option inserted there. So the verb returned
`suspicious_count: 0` on a settings file the harness itself flagged at every single session
start. "0 suspicious permissions" reads as "the allow list is sound"; it actually means "no rule
matched twenty hardcoded dangerous-target regexes".

This is the epic's archetype exactly: a confident clean signal whose scope is far narrower than
what its consumers read it as. The divergence is unusually sharp here because a **second,
independent instrument was simultaneously reporting the opposite verdict** on the same file.

## The knowledge already exists in this codebase — on the other side

`claude_runtime.py` refuses to render a deny rule for any path containing whitespace, and says
why in the code (`marketplace/bundles/plan-marshall/skills/platform-runtime/scripts/claude_runtime.py`,
in `_reject_unprotectable_path`):

```python
# A `Bash(...)` rule is matched as a command prefix, so a space inside
# the path moves the argument boundary: `Bash(cat ~/my creds/*)` is not
# a rule about `~/my creds`.
return 'path contains whitespace, which moves the argument boundary in a Bash rule'
```

That is the same hazard, correctly understood and fail-closed — on the **deny-rule renderer**.
The **allow-rule inspector** has none of it. The asymmetry is the defect: we know the rule and
apply it only where it protects the renderer, not where it protects the operator.

## What is NOT wrong (checked, so nobody re-derives it)

plan-marshall's own generators never emit this shape. Verified by reading each renderer:

| Surface | Emits | Wildcard position |
|---------|-------|-------------------|
| `_default_permission_rules()` | `Edit(.plan/**)`, `Read({cache}/**)` | trailing |
| `_render_permission_intent()` kind=`executor` | `Bash(python3 .plan/execute-script.py *)` | trailing |
| `_render_permission_intent()` kinds `bundle`/`skill`/`path`/`web-domain` | `Skill(...)`, `SlashCommand(...)`, `{tool}({path})`, `WebFetch(...)` | n/a |
| `permission_fix.generate_wildcard()` | `{type}({prefix}{base}-*.{ext})` | trailing |

So setup does not **create** the defect. It arrives through operator-approved ad-hoc grants (the
harness writes the command the operator approved, glob and all), and then
`permission_fix add` appends whatever string it is handed to `permissions.allow` with **no
grammar validation at all** — it checks only for an exact duplicate before appending.

## Documentation gap alongside it

The two canonical homes of the `Bash(...)` wildcard grammar both teach the forms and neither
states the boundary rule:

- `marketplace/bundles/pm-plugin-development/skills/plugin-architecture/references/frontmatter-standards.md` § Permission Patterns
- `marketplace/bundles/pm-plugin-development/skills/plugin-script-architecture/references/notation-spec.md` § Permission Pattern

Both are marked Claude target material and both show only trailing-wildcard / `:*` forms, which
are correct — but a reader is never told *why* the wildcard belongs at the tail, so nothing stops
the next hand-written rule from putting one in the middle.

## Candidate remedy

Three parts, smallest first:

1. Add a grammar-validity family to `detect-suspicious` (or a sibling verb, if mixing
   "dangerous target" and "malformed rule" into one count would itself blur a signal): flag any
   allow rule whose `*` is followed by further command text rather than terminating the rule or
   appearing as `:*`. The detector is a few lines and has a zero false-positive shape, because
   the trailing and `:*` forms are the only sanctioned ones.
2. Make `permission_fix add` refuse — or at minimum report — a rule of that shape rather than
   appending it silently. Reuse the argument-boundary reasoning already written at
   `_reject_unprotectable_path`; it should have one home, not two absent ones.
3. State the boundary rule in both grammar documents.

A population note for part 1, since the epic cares: the detector's count must be reported against
the number of allow rules actually scanned and the settings files actually resolved, so a zero
distinguishes *looked, found nothing* from *found no settings file*. `detect-suspicious` already
carries `permissions_checked`; a new family should ride the same discipline.

## Secondary observation (not this finding, recorded so it is not lost)

The same allow list carries `Bash(python3 *)`, `Bash(python3:*)` and
`Bash(env PM_ARGUMENT_NAMING_ENABLED=1 *)`. These are well-formed — trailing wildcards, not the
flagged class — but each grants effectively unrestricted execution, and `detect-suspicious` is
silent on them too. Whether a breadth family belongs next to the grammar family is a scoping
question for whoever picks this up, not a claim that these rules are wrong.
