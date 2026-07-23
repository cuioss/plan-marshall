# Provenance — `rewrite-run-warnings.log`

`rewrite-run-warnings.log` in this directory is the authoritative reference for
the `cui-open-rewrite` #118 per-run WARN-line format that
`pm-dev-java-cui:parse-rewrite-log`'s `FINDING_PATTERN` parses. Its finding
lines are the **verbatim upstream WARN templates** filled with the upstream
test's own asserted fixture values — they are never hand-invented, and no
assertion in this suite may re-derive a WARN literal from memory.

## Provenance fields

| Field | Value |
|-------|-------|
| Upstream repository | `cuioss/cui-open-rewrite` (<https://github.com/cuioss/cui-open-rewrite>) |
| Pull request | #118 (merged) |
| Ref / merge commit | `a0e21ac536460c841b2135ace15a6578ff481021` on `main` |
| Templates transcribed from | `src/main/java/de/cuioss/rewrite/util/RecipeLogMessages.java` (the two WARN templates, prefix `CUI_REWRITE`, identifiers `100`/`101`) |
| Emitter | `src/main/java/de/cuioss/rewrite/util/RecipeMarkerUtil.java` (`logFinding` → `LOGGER.warn(TEMPLATE, sourcePath, line, column, recipeName, taskMessage)`) |
| Render separators | cui-java-tools `LogRecordModel.format` — `"%s-%s".formatted(prefix, identifier)` header + `": "` after-prefix separator |
| Tier-a asserted fixture values | `src/test/java/de/cuioss/rewrite/util/RecipeMarkerUtilTest.java` — line `3`, column `9`, recipe display name `TestRecipe`, task message `TODO: Throw specific not RuntimeException` |

## The line form this corpus pins

```text
CUI_REWRITE-100: Finding detected at <path>:<line>:<column> by <recipe>: <message>
CUI_REWRITE-101: Finding pre-existing at <path>:<line>:<column> by <recipe>: <message>
```

The five fields are the source file path, line, column, recipe display name, and
the marker/task message. The identifier is the authoritative classification
signal: `100` → newly-detected, `101` → pre-existing.

Key format properties every corpus line exercises, each load-bearing for the
parser:

- **Substring, never line-anchored.** Only the `CUI_REWRITE-<id>: ` application
  prefix is part of the recipe-emitted string; the surrounding log layout (JUL
  formatter / Maven `[WARNING]` / timestamp + logger name) prepends text the
  recipe never emits. The corpus therefore includes lines carrying a leading
  `[WARNING] ` and a leading timestamp+logger layout, so a parser anchored at
  `^` would silently match nothing against a real build log.
- **Greedy message to end-of-line.** The `TODO: Throw specific not
  RuntimeException` message contains an internal `": "`, so a parser that stops
  the message field at the first `": "` truncates it.

## Format-drift regression expectation

The test suite reads this corpus and asserts that every finding line still
matches the parser's `FINDING_PATTERN`. If a future upstream release changes the
template wording, the identifier, or the `CUI_REWRITE` prefix, the pinned corpus
stops matching the parser and the regression test **fails loudly** — rather than
the parser silently disabling and reporting a false "no findings". To refresh
this corpus, re-transcribe the upstream templates at a newer ref and update both
the corpus lines and the ref recorded above in the same change.

## Honest caveat

No fully-rendered upstream build-log fixture file exists to copy byte-for-byte.
These corpus lines are the verbatim upstream WARN templates
(`RecipeLogMessages.java`) filled with the upstream test's asserted fixture
values (`RecipeMarkerUtilTest.java`) — an authentic capture, not a hand-invented
format. The numeric `CUI_REWRITE-<id>: ` prefix rendering is derived from the
cui-java-tools `LogRecordModel.format` source chain (high confidence), not from a
captured live log line; the upstream test asserts the finding body as a
substring beginning at `Finding`, so it byte-confirms the body and separators but
not the numeric prefix.
