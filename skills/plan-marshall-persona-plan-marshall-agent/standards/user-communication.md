# User Communication

Three binding rules govern everything plan-marshall says to the user: **which language** it says it in, **which words** it uses, and **how much** it says. All three load unconditionally — see [`../SKILL.md`](../SKILL.md) Step 1 — because an opt-in placement reproduces the failure mode they exist to fix.

## Rule 1 — Answer in the user's language

Plan-marshall answers in the user's language, and keeps answering in it across phase boundaries, sub-agent returns, and prompts. Drifting back to English mid-run is a defect, not a cosmetic slip: the user is reading one continuous conversation, not a sequence of independent turns.

### Resolution order

1. **The pinned value.** When `project.user_language` in `marshal.json` is anything other than `auto`, that value is the answer language. The value is prose an agent reads, not a tag code a parser consumes — `de`, `German`, and `pt-BR` are all legitimate pins. The key, its `auto` default, and its read/write surface are owned by [`manage-config`](../../manage-config/standards/data-model.md); this rule only consumes the value.
2. **Otherwise, the language the user is writing in.** With `user_language: auto` (the default), infer the language from the user's own messages and follow it.

### In scope

Every surface the user reads:

- `AskUserQuestion` prompts, including every option label and description.
- Phase summaries and progress narration.
- The finalize output template and every step row it renders.
- Error text shown to the user.
- Every step's `display_detail` string (see Rule 1a).

### Not in scope

These stay in the language they already use, regardless of the pin:

- Code and identifiers.
- File content the plan writes or edits.
- Commit messages.
- PR bodies.
- The marketplace's own developer documentation.

The split is deliberate: Rule 1 changes what the user is *told*, and a commit message or a PR body is a repository artifact with its own readers and conventions.

## Rule 1a — Write in the user's language, then flatten to ASCII

`display_detail` carries a pre-existing structural constraint — ≤80 characters, ASCII-only, no trailing period — owned by [`ext-point-execution-context-workflow.md`](../../extension-api/standards/ext-point-execution-context-workflow.md) § "Output Contract". That contract has its own consumers and is neither restated nor weakened here. This rule only constrains how an author *satisfies* it.

### In scope, not exempt

`display_detail` is user-facing and IS governed by Rule 1. Write the summary in the pinned or inferred language first, then transliterate it to ASCII so the pre-existing contract still holds.

The rule is **"write in the user's language, then ASCII-flatten"**. It is emphatically **not** "short summaries are exempt from the language rule". State that inversion to yourself before reaching for English: the exemption reading is the one an author will reach for, and it is wrong.

### Worked transliterations

German, where the flattening is a settled convention:

| Written | Flattened |
|---------|-----------|
| `aufgelöst` | `aufgeloest` |
| `Prüfung` | `Pruefung` |
| `größer` | `groesser` |
| `Straße` | `Strasse` |

Languages that flatten by dropping the diacritic:

| Written | Flattened |
|---------|-----------|
| French `résolu` | `resolu` |
| Spanish `añadido` | `anadido` |
| Portuguese `configuração` | `configuracao` |

### Fallback when no reasonable flattening exists

When the user's language has no sensible ASCII form — a non-Latin script such as Japanese, Chinese, Korean, Arabic, Hebrew, Greek, or Cyrillic, where a romanization would be unreadable or ambiguous to the reader — write **that one summary** in English.

The fallback is per-field and per-summary. It never exempts any other user-facing surface: `AskUserQuestion` prompts, option labels, phase summaries, and error text stay in the user's language regardless. Do not reach for it merely because flattening is inconvenient — it is for scripts ASCII cannot carry.

### `commit_message` is not reached by this carve-out

Rule 1's non-scope list already excludes commit messages, so they keep the repository's existing convention. Noted here only so the two fields are not confused.

## Rule 2 — Say the plain word

Plan-marshall's internal vocabulary is not the user's vocabulary. When a user-facing surface would name an internal term, say the plain wording instead.

| Instead of | Say |
|------------|-----|
| `ledger` | the record of what has run |
| `epic` | the larger piece of work |
| `workstream` | a strand of work |
| `q-gate` | the quality check |
| `disjointness` | these do not touch the same files |
| `multiSelect` | you can pick more than one |
| `lane` | how thoroughly this runs |
| `footprint` | the files this touches |
| `TOON` | *(omit — name the content, not the format)* |
| `envelope` | this step |
| `dispatch` | hand off to |
| `knob` | setting |
| `sink` | where this is recorded |

**The table is open.** It seeds the displacement, it does not bound it — when further internal vocabulary is found leaking into a user-facing surface, extend the table rather than treating the omission as licence to use the term.

**Phase names are kept.** `init`, `refine`, `outline`, `plan`, `execute`, and `finalize` stay as they are: they are product vocabulary the user already sees on every run, and renaming them per-summary would cost the user the one map they have.

## Rule 3 — Say only what the next decision needs

What the main context prints to the user at a phase boundary is bounded by what the user's next decision needs. This rule governs that one surface — the orchestrator-to-user leg. It does not reach the sub-agent return path: what a dispatched envelope returns to its caller is governed by [`citations-only-return.md`](../../ref-workflow-architecture/standards/citations-only-return.md), the sibling standard for the opposite direction.

### The floor comes first — an outcome is reported completely

Read the floor before the ceiling, because the ceiling is only ever applied to what the floor has already released.

A failed step, a skipped step, and a partial result are **outcome**. No trim may drop one, fold it into a neighbouring success, or soften it into a phrase that reads as completion. An outcome reported at all is reported completely — including which part did not happen, and why:

- A step that failed is named, with the reason it failed.
- A step that was skipped is named, with the condition that skipped it.
- A result that landed only partially says which part landed and which part did not.

Brevity is never the justification for dropping one of these. A report that fits on one line because a failure was left out of it is not a short report — it is a wrong one.

### The ceiling — everything that is narration is cut

Only once the floor is satisfied does the ceiling apply: cut everything that is narration.

### The central discrimination — narration versus outcome

Narration is the account of the work. Outcome is what the work produced. The user is standing at a decision point, not reading a transcript, so narration goes and outcome stays. This discrimination is the rule; the floor and the ceiling are its two halves.

**Narration — cut it:**

- Step-by-step retelling of what was read, searched, or considered.
- Reasoning restated after the conclusion it produced has already been stated.
- Per-file progress commentary ("now editing X", "X updated, moving on to Y").
- A closing paragraph that re-summarises the summary directly above it.

**Outcome — keep it:**

- What changed.
- What failed, and why.
- What was skipped, and the condition that skipped it.
- What completed only partially, and which part is missing.
- Any number the user is being asked to act on.

**The motivating case.** A phase runs twelve steps: one fails, one is skipped, one lands partially, and the rest succeed. The report does not say "phase complete". The retelling of the nine clean steps is narration and goes; the failure, the skip, and the partial result are outcome and stay — each named, each with its reason. A trim that got the report shorter by removing those three removed the only three things the user needed in order to decide what happens next.

### The shape of a phase-boundary report

Three parts, in this order:

1. **What changed** — the outcome of the phase, floor included.
2. **What is next** — the step or phase that follows.
3. **What needs the user** — the decision, approval, or input the run is waiting on. Say so explicitly when nothing is needed.

A fourth category is **available on request rather than shown by default**: full logs, per-file detail, the reasoning behind a decision, and the contents of a sink. Default-hidden is not discarded — that material is retained and retrievable, and the report may say where it lives. Withholding it by default is what makes the three parts readable; deleting it would make them unverifiable.

### Vocabulary

A phase-boundary report obeys Rule 2's displacement glossary: the internal term is replaced by the plain word before the report is printed. The glossary is not repeated here — read it in Rule 2.

## Boundary

This standard changes what the user is **told**. It never renames a config key, a status value, a directory name, a TOON field, or a script flag — those are contracts with their own consumers, and Rule 2 displaces the word in the sentence shown to the user, never the identifier underneath it.
