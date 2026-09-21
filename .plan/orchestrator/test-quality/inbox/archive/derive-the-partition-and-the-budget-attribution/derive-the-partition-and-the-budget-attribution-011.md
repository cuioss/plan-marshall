envelope_version=1
sender_type=plan
sender_id=derive-the-partition-and-the-budget-attribution
epic=test-quality
kind=candidate-lesson
created=2026-08-25T09:06:00Z

component=plan-marshall:manage-architecture
category=bug
confidence=high
source_plan=derive-the-partition-and-the-budget-attribution

# search --content patterns are regexes, so a metacharacter-bearing query can return a false zero

## Context

`architecture search --content --pattern P` was used during this run to establish that a
string did not occur anywhere in the inventory. It returned `count: 0`. The zero was a
**pattern artifact**: the query carried unescaped regex metacharacters (`./`), so what
was matched was not the string the caller meant to search for.

The caller acted on the zero as a verified absence. It was not one.

This is the same confident-zero class the epic exists to close, arriving through a new
door. Every other zero in this surface has been given a discriminator — `list-stalled`
carries `store_resolution` / `plans_root_state`, `inbox list` carries `inbox_state`,
`restore-from-plan` distinguishes `no_lesson_file` from `plan_dir_unresolved`. The
content sweep's zero has coverage discriminators (`files_scanned`, `unreadable[]`,
`truncated`) but nothing at all about whether the PATTERN was the one the caller meant.

## Root cause

The `--pattern` value is compiled as a regular expression. The verb has a `--literal`
flag and its response echoes `literal: false`, so the behaviour is discoverable — but
only to a reader who already suspects it.

The project-level guidance compounds this. CLAUDE.md and the client-api "Complete-coverage
rule" both instruct callers on exactly when a `count: 0` is trustworthy, and both frame
the answer entirely in terms of **coverage** (inventory scope, gitignore, dotfile trees).
Neither mentions that a fully-covered sweep can still return a zero because the pattern
did not mean what it looked like. A caller who follows the documented rule to the letter
concludes "not in any inventoried file" from a zero that established nothing.

## Proposed action

Two independent, cheap moves:

1. Make the trustworthy-zero rule name pattern-validity alongside coverage — a `count: 0`
   is a verified absence only when the sweep's coverage is clean **and** the pattern was
   literal or deliberately regex. The client-api `search` section and the CLAUDE.md
   `search --content` bullet are the two sites.
2. Have the response surface the risk rather than only the mode: when `literal: false`
   and the pattern contains unescaped metacharacters, say so beside the count. A caller
   who meant a literal string then sees the discriminator without having to suspect it.

Recommending `--literal` as the default posture for existence questions would close most
of the exposure on its own.

## Evidence

- observed this run: an unescaped `./` query returned `count: 0` and was read as an absence
- verified in-session: the verb echoes `literal: false` by default; `--literal` flips it to `true`
- the documented complete-coverage rule enumerates coverage caveats only, not pattern validity
