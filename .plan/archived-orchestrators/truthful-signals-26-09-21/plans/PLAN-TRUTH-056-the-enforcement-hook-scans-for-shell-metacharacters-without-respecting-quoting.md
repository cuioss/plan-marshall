> ⛔⛔ **SUPERSEDED 2026-08-08 — MERGED INTO `PLAN-TRUTH-013`.**
> Absorbed under the raised 12-deliverable cap, grouped by COMPONENT so that plans on different
> components stay parallel-safe. The receiving spec carries the merge rationale and this plan's
> deliverables. **Do not implement. Do not emit.** Retained as the record — *close freezes, never deletes.*

# PLAN-TRUTH-056: the enforcement hook scans for shell metacharacters without respecting quoting — so the agent edits the evidence to satisfy a lexer

epic: truthful-signals
workstream: WS-01

## Objective

The R1 one-command-per-Bash-call guard rejects a call when a shell metacharacter appears **anywhere in
the raw command string**, including **inside a quoted argument value**. A `--message` containing a
literal `;` is not a compound command — but the guard cannot tell.

⇒ ⛔⛔ **The agent's workaround is to REWRITE THE MESSAGE.** ⭐ **A guard that cannot parse quoting makes
the agent edit the record to satisfy a lexer** — in the exact stores this epic exists to keep truthful.

## OBSERVED — first-party, and the fix is already present in the same file

`platform-runtime/scripts/claude_pretooluse_hook.py`:

```python
:74   _R1_SHELL_SUBSTRINGS = ("&&", ";", "&", "$(", "`")
:177  if any(token in command for token in _R1_SHELL_SUBSTRINGS):
          return _R1_REASON
```

**A raw substring scan over the whole command string. No quoting awareness.**

⭐⭐ **And 30 lines later, the SAME MODULE does it correctly for R2 — with a docstring that states
exactly why:**

> *"The split is SHELL-LEXICAL (`shlex`), not whitespace. A detached value option can carry a quoted
> value containing spaces … **a naive `str.split()` tears that value into two tokens** … Lexical
> splitting resolves the quoting first."*
> — and on malformed quoting it *"falls back to the whitespace split rather than … turning a lexer error
> into a silent bypass."*

⇒ **`shlex` is already imported (`:16`), already used, already justified, and already has a documented
failure-mode fallback. R1 simply does not call it.**

⭐ **This is the cheapest possible fix shape: apply a technique the file already contains and already
defends.** ⛔ It is also, in this epic's terms, a **defending-documentation** instance — the module
argues in prose for lexical parsing while its first rule ignores it.

## The live case, operator-supplied

A `manage-logging decision --message "…"` whose body contained
*"(Grep/Glob tools absent in this session**;** harness redirects to Bash**;** operator authorized)"* was
rejected. **Every `;` was inside one double-quoted argument.**

⭐ **The rejected message is not incidental prose — it is a substantive evidence record**: a two-stage
consumer sweep, an explicit `READER SET = 7`, two newly-found files with line references, six
non-readers excluded **with rationale**, and the closing line *"This is the THIRD under-enumeration of
the consumer population on this plan."*

⇒ ⛔⛔ **The record that gets degraded is precisely the kind this epic depends on.** A rewrite to dodge a
character is not neutral: it drops semicolons that separate independently-verifiable clauses, and there
is **no marker distinguishing a message written freely from one written around a lexer.**

## ⛔ The substring list makes this frequent, not occasional — and one entry is the real culprit

| Token | Consequence for a quoted message body |
|---|---|
| `` ` `` | ⛔⛔ **Any backtick trips it.** Our log messages, findings and lessons use `` `code` `` constantly — **this is almost certainly why the operator sees it "often"** |
| `&` | `&&` is redundant beside it; **"R&D", "A & B" trip** |
| `;` | the reported case |
| `$(` | rarer in prose |

⚠ **HYPOTHESIS, and D0's first question**: the backtick is the dominant trigger by volume, not the
semicolon. ⛔ **Do not scope from the reported symptom** — the operator reported `;` because that is what
the workaround message names; a frequency count over rejected calls may say something different.
⭐ *A list produced by looking is a sample* — this epic's own standing rule, applied to its own intake.

## ⚠ The false-NEGATIVE direction must be checked too, or the fix trades one defect for another

Making R1 quoting-aware **must not** let a genuine compound through. ⛔ **Both directions:**

- A `;` inside a quoted value ⇒ **allow** (the reported false positive).
- A `;` **between** tokens ⇒ **still block** (the rule's whole purpose).
- ⚠ **`shlex.split` strips quotes, so post-split token inspection loses the information about where a
  metacharacter came from.** The check must run on the **lexer's structure**, not on the reassembled
  tokens. **State the mechanism chosen and why it cannot be fooled.**
- ⛔ **Malformed quoting must fail CLOSED here, not open** — R2's documented fallback is to the
  whitespace split *"instead of turning a lexer error into a silent bypass"*. **R1 must inherit that
  posture, and its fallback is the CURRENT substring scan**, which is conservative in the right
  direction.

## Deliverables

1. **D0 — GATE: derive the trigger population, and both directions.** Which metacharacters actually
   cause rejections in practice, and at what relative frequency. ⛔ **Both**: quoted occurrences that
   should pass, and unquoted ones that must keep failing. ⚠ **The backtick hypothesis above is the first
   thing to confirm or refute** — it changes nothing about the fix but everything about the priority.
2. **D1 — R1 becomes quoting-aware, reusing R2's established technique.** ⭐ **Load-bearing, and it is a
   handful of lines.** ⛔ **Reuse `shlex` and R2's malformed-quoting fallback posture — do not invent a
   second parsing approach in a module that already has one** (two techniques for one job is how a field
   acquires two producers — `PLAN-TRUTH-049`).
3. **D2 — tests, each verified to FAIL pre-fix.** (a) **The live fixture**: the operator's exact
   `manage-logging` command is accepted. (b) A backtick, an `&`, and a `$(` inside a quoted value are
   accepted. (c) ⛔ **A genuine `cmd1; cmd2` is still BLOCKED** — the anti-regression, and the one that
   matters. (d) Malformed quoting falls back to the current conservative scan rather than passing.
4. **D3 — record what the workaround cost.** ⚠ Every trip is a rejected call **plus** a rewrite ⇒ direct
   token waste on the operator's **priority-1** axis, and a silently degraded record. ⭐ **State whether
   any past record is known to have been rewritten** — ⛔ and if that is unknowable, **say so** rather
   than implying the corpus is clean.

⚠ Four deliverables, deliberately small. ⛔ **Resist widening into a general hook-rules review** — R2 and
the other rule families are working as designed and are not in scope.

## Claim Labels

- **OBSERVED (this orchestrator, first-party, read from source)**: `_R1_SHELL_SUBSTRINGS` at `:74`; the
  raw-substring test at `:177`; `shlex` imported at `:16`; R2's lexical split and its documented
  malformed-quoting fallback at `:205-223`.
- **OBSERVED (operator, first-party)**: the rejected command, its quoted `;` characters, and that the
  workaround is to rewrite the message. ⭐ **And that it happens OFTEN** — which is what makes it a plan
  rather than a note.
- **HYPOTHESIS**: the backtick is the dominant trigger by volume. ⛔ **Unverified — D0's first question.**
- ⛔ **NOT ESTABLISHED**: how many stored records were altered by this workaround. ⚠ **There is no marker
  for it**, so the honest answer may be *unknowable* — D3 must say which.

## Expected Surface

- **OBSERVED**: `platform-runtime/scripts/claude_pretooluse_hook.py` — R1's matcher and `_R1_SHELL_SUBSTRINGS`
- **HYPOTHESIS**: its test module — the fixtures for D2
- **HYPOTHESIS**: `plan-marshall/references/hook-authoring-guide.md` — if the rule's wording is restated there

## Dependencies and Sequencing

- ✅ **Disjoint from `PLAN-TRUTH-047` (running)** — different bundle, different file.
- ⚠ Same file family as `PLAN-TRUTH-013` (hook timeout-unit confusion). **Different rule, different
  failure — SERIALIZE if both are in flight; do not merge.**
- ⭐ **Token-reduction relevance**: this is a repeated, avoidable round-trip on every affected call.
  ⚠ **Not a roadmap lever** — it is a defect fix whose saving is incidental. **Do not file it as L9.**

## Hand-Off Command

```text
/plan-marshall task="implement .plan/local/orchestrator/truthful-signals/plans/PLAN-TRUTH-056-the-enforcement-hook-scans-for-shell-metacharacters-without-respecting-quoting.md"
```

## Write-Boundary

The plan implementing this spec touches only its own repository source and tests. It creates and edits
NO file under `.plan/local/orchestrator/` other than its own `inbox/{sender}-{seq}` message. Qualifiers
are in `persona-marshall-orchestrator/standards/orchestration-model.md` § Ledger Write-Boundary.
