# Provenance — `MarkedSample.java`

`MarkedSample.java` in this directory is the authoritative reference for the
OpenRewrite marker syntax that `pm-dev-java-cui:search-markers`'s
`MARKER_PATTERN` detects. Its marker text is checked in **verbatim and
unmodified** from the upstream recipe project's own test resources — it is never
hand-written, and no assertion in this suite may re-derive a marker literal from
memory.

## Provenance fields

| Field | Value |
|-------|-------|
| Upstream repository | `cuioss/cui-open-rewrite` (<https://github.com/cuioss/cui-open-rewrite>) |
| File path within that repository | `src/test/java/de/cuioss/rewrite/logging/CuiLogRecordPatternRecipeTest.java` (the expected-output text block of `detectMissingLogRecordForInfo`) |
| Ref / version | commit `081e18b86378ca1603cbe532f641ecd98f943bc9` on `main`, project version `1.4.1-SNAPSHOT` |
| Recipe name | `CuiLogRecordPatternRecipe` |

## The marker form this fixture pins

```text
/*~~(TODO: <message>)~~>*/
```

The closing delimiter is `)~~>*/` — **not** `)>*/`. The `~~` is part of both the
opening and the closing delimiter, because OpenRewrite's `SearchResult` marker
printer wraps the description as `~~(<description>)~~>`. A detector regex that
terminates on `)>*/` silently matches nothing against real recipe output.

## Notes for readers

- The fixture reproduces the upstream Java source exactly, including its
  `class Test` declaration. The filename therefore does not match the type name.
  This is deliberate: the file is a **text fixture** that is read as bytes by the
  marker detector's tests and is never compiled by any build.
- The marker message itself embeds the recipe's own suppression hint
  (`// cui-rewrite:disable CuiLogRecordPatternRecipe`), which is why the message
  contains both `//` and `:` characters. Any regex change must keep matching it.
- To refresh this fixture, re-read the upstream file at a newer ref and update
  both the fixture bytes and the ref recorded above in the same change.
