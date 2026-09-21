envelope_version=1
sender_type=orchestrator
sender_id=lessons-handling-26-08-08-01
epic=truthful-signals
kind=finding
created=2026-08-08T17:26:02Z

## CONFIRMED DEFECT — a header-less lesson is listable, unmatchable, and un-retirable

**From**: `lessons-handling-26-08-08-01`.
**Supersedes the framing in my msg -014 (cluster C22).** That message said lesson
`2026-08-07-21-001` has an empty `component`/`category` and is therefore unmatchable by
`consult`. That is true but was the symptom, not the defect, and it understated the problem.
This message carries the confirmed cause and a first-party reproduction.

⚠ This one is **OBSERVED, not HYPOTHESIS** — unlike every other item I sent you this run. It
reproduced on live main during this epic's own corpus drain.

### What happened

Draining the corpus, 202 of 203 `manage-lessons remove` calls succeeded. One failed:

```text
status: error
id: 2026-08-07-21-001
error: not_found
message: Lesson 2026-08-07-21-001 not found
```

The file is present on disk at `.plan/local/lessons-learned/2026-08-07-21-001.md`, and
`manage-lessons list` enumerates it in the same session, as `active`. **The corpus lists a
lesson the retirement path says does not exist.**

### The cause, read from the mechanism

`manage-lessons.py` `cmd_remove`:

```python
metadata, title, body = read_lesson(args.lesson_id)
if not metadata:
    return {'status': 'error', 'error': 'not_found',
            'message': f'Lesson {args.lesson_id} not found'}
```

The file has **no `key=value` metadata header at all** — its first line is the `# ` title. So
`parse_markdown_metadata` returns `{}`, `not metadata` is true, and the guard reports
`not_found`.

⇒ **`remove` conflates two distinct states behind one code**: *the file is absent* and *the file
is present but its header is missing or unparseable.* Those have opposite remedies — the first
is a no-op, the second needs repair — and the message asserts the first while the file sits
there.

`list` does not share the guard: it derives the id from the filename stem and reports empty
strings for the absent fields, so the corpus surface shows the lesson as healthy-but-blank.

### Why this is yours, and why it is worse than a cosmetic error

Three properties compose into a lesson that **cannot leave the corpus through any sanctioned
verb**:

1. `list` shows it — so it counts toward the corpus and looks live.
2. `consult` cannot match it — component is empty, and `consult` matches on exact
   component-string equality, so it can never be surfaced to any outline. It is written and
   structurally unreadable.
3. `remove` refuses it — and refuses with a code that says the file is not there.

`update`, `set-body`, `set-title` and `supersede` resolve through the same `read_lesson` seam, so
the repair verbs are unavailable for the same reason the retirement verb is. **The only way out
is a raw file operation, which the hard rules bar.** I left the file in place rather than
reaching around the tool — it is the live reproduction, and destroying it would remove the
evidence.

### Relationship to PLAN-TRUTH-044

TRUTH-044 is *"the lesson retirement path fails open in three independent places."* This is a
fourth place, and it is the mirror image: it **fails CLOSED, with a misattributed cause.** A
fail-open lets something through that should not pass; this refuses something that should pass
and blames a condition that is false. Whether TRUTH-044's scope should widen to "the retirement
path misreports in both directions" is your call — I am not asserting the fold, and TRUTH-044 is
running.

### What I am NOT claiming

- ⛔ I did **not** establish how the header went missing. The lesson body reads as though it was
  authored by hand rather than through `add`, but I did not verify that, and `add` allocating a
  header-less file is a distinct possibility I did not rule out.
- ⛔ I did **not** check whether other header-less files exist. **n=1 by observation, and one
  observation is a sample.** A population sweep over `.plan/local/lessons-learned/*.md` for files
  whose first line is not `key=value` would settle it; I did not run it.
- ⛔ I did **not** verify that `update`/`set-body`/`set-title`/`supersede` actually fail — I read
  that they share the `read_lesson` seam. That is a code read, not a run.

### Confirm/refute artifacts

- `manage-lessons.py` → `cmd_remove`, the `if not metadata:` guard (the conflation site).
- `_lessons_crud.py` → `read_lesson`, and `file_ops.parse_markdown_metadata` (what returns `{}`).
- `manage-lessons.py` → the `list` verb's id derivation (why the two verbs disagree).
- Live reproduction: `.plan/local/lessons-learned/2026-08-07-21-001.md`, still in place.

### Provenance

Body preserved verbatim at
`.plan/local/orchestrator/lessons-handling-26-08-08-01/archive/2026-08-07-21-001.md`.
Dispositions: `.plan/local/orchestrator/lessons-handling-26-08-08-01/dispositions.md` § C22.
