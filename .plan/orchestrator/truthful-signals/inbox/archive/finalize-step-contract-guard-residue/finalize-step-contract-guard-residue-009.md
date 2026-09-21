envelope_version=1
sender_type=plan
sender_id=finalize-step-contract-guard-residue
epic=truthful-signals
kind=candidate-lesson
created=2026-08-24T10:38:27Z

component=plan-marshall:manage-architecture
category=bug

# `architecture search --content` omits `.claude/**` and `.github/**`, which CLAUDE.md's hard rule names as covered

The "Structured queries first" hard rule in `CLAUDE.md` documents the content sweep's
coverage with this parenthetical:

> dotfile trees outside the allowlist (`.claude/**`, `.github/**`) are **not** searched

Read either way, that sentence tells an agent `.claude/**` is a settled question. It is
not. The actual allowlist is two FILENAMES, not directories:

```python
# marketplace/bundles/plan-marshall/skills/manage-architecture/scripts/_cmd_manage.py:85
_FILES_DOTFILE_ALLOWLIST = frozenset({'.gitignore', '.editorconfig'})
```

Every other dotfile and every dotfile DIRECTORY is skipped, so `.claude/` and `.github/`
are absent from the inventory entirely.

## Measurement

Three independent probes, all against the live inventory (`files_scanned: 5288`):

| Probe | Expected if covered | Actual |
|-------|---------------------|--------|
| `architecture find --pattern ".claude/skills/**/SKILL.md"` | 6 project-local steps | `count: 0` |
| `architecture search --content --pattern "emitted_count"` | includes `.claude/skills/finalize-step-deploy-target/SKILL.md` | 2 files, neither under `.claude/` |
| `architecture search --content --pattern "Why .always run. instead of a skip detector"` | 1 hit (verbatim heading in that file) | `count: 0` |

The second and third probes target strings I had just read out of
`.claude/skills/finalize-step-deploy-target/SKILL.md` with the `Read` tool, so the file's
content is not in doubt — only its presence in the inventory is.

## Why this is a truthful-signals defect, not a coverage preference

This is the epic's core archetype: a `count: 0` that means *"I could not look"* wearing the
representation of *"I looked and found nothing."* The `search` verb already knows how to
distinguish those — `client-api.md` § search carries a "Complete-coverage rule" and the
response carries `files_scanned` / `unreadable[]` so a caller can tell a clean negative from
a degraded one. The dotfile-directory skip is invisible to every one of those fields: the
sweep reports a clean, complete, zero-unreadable negative over a tree it never entered.

## Blast radius

Six project-local finalize steps live under `.claude/skills/` —
`finalize-step-deploy-target`, `finalize-step-era-stamp-fill`,
`finalize-step-lessons-housekeeping`, `finalize-step-plugin-doctor`,
`finalize-step-review-retrospective`, `finalize-step-sync-plugin-cache`. They are
simultaneously outside:

- the architecture inventory (measured above), so `find` / `search --content` / `files`
  cannot see them; and
- `plugin-doctor`'s scan, which is scoped to `marketplace/bundles/`.

So a project-local finalize step is governed by no structural guard at all. The sibling
candidate on `finalize-step-deploy-target`'s unimplementable TOON-parse contract is a
concrete instance of what that gap lets through.

`.github/**` is the same shape: workflow files that `python-verify.yml`'s branch-filter
semantics are reasoned about from are invisible to a content sweep.

## Solution

Two independent fixes; the second is the load-bearing one.

1. Correct the `CLAUDE.md` hard-rule parenthetical so it names what is actually swept. The
   canonical statement belongs in `manage-architecture/standards/client-api.md` § search,
   with `CLAUDE.md` cross-referencing it rather than restating it.
2. Make the skip **observable in the response**. A caller cannot be expected to remember a
   prose carve-out; the payload already carries `files_scanned` and `unreadable[]`, and a
   `skipped_trees[]` (or equivalent) field naming the dotfile directories the walk declined
   would put this in the same class as the coverage fields that already exist. Without it,
   any future widening or narrowing of the skip set is again undetectable from the answer.

Whether `.claude/**` *should* be crawled is a separate decision. This lesson is about the
answer not saying which zero it is — and that is true regardless of which way that decision
goes.

## Impact

Every agent that follows the "Structured queries first" hard rule, which is all of them.
The rule explicitly directs agents to prefer `architecture find` / `search --content` over
`Glob`/`Grep` for file discovery and content search, and — in an `execution-context` leaf,
where `Grep`/`Glob` may not be granted at all and Bash `grep`/`find` are hook-blocked —
the structured query is frequently the ONLY search surface available. A leaf that sweeps
for a string under `.claude/` gets a confident, well-formed, complete-looking zero.
