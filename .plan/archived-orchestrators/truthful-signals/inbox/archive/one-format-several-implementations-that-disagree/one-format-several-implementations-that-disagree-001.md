envelope_version=1
sender_type=plan
sender_id=one-format-several-implementations-that-disagree
epic=truthful-signals
kind=candidate-lesson
created=2026-09-07T18:40:50Z

category=best-practice
component=test/plan-marshall/ref-toon-format
title=Enumerating names asserts completeness; deriving from the type graph proves it

## The concrete case

A guard decided whether an `except` handler could swallow a failing
`from toon_parser import …`. Its predicate was a hand-written set:

```python
_IMPORT_CATCHING_HANDLERS = frozenset({'ImportError', 'Exception', 'BaseException'})
```

with a comment arguing these were "the BROADEST handlers a module could route
around the serializer with, which is to say the ones the guard most needs to see
rather than the ones it can afford to miss".

CodeRabbit found that `except ModuleNotFoundError:` clears the guard — and
`ModuleNotFoundError` is exactly what a genuinely missing module raises. A
fallback serializer could re-enter the tree unflagged.

## What actually failed

**Not the list — the argument.** The comment reasoned about *breadth*, and breadth
is the wrong axis. A subtype catches strictly less than `ImportError`, but what it
catches is precisely the failure that occurs. Reasoning about which names are
broad enough silently assumed breadth was the only way to catch.

That is why the fix was not a fourth entry. Adding `ModuleNotFoundError` would
have closed this instance and left the shape — the next handler nobody
enumerated — exactly as open. It is the same loop the five preceding review rounds
had already run on the clause directly below it, each round adding one more
special case for one more statement form.

The replacement derives the answer from the live exception hierarchy:

```python
caught = getattr(builtins, name, None)
if not (isinstance(caught, type) and issubclass(caught, BaseException)):
    return True                      # unresolvable -> fail CLOSED
return issubclass(caught, ImportError) or issubclass(ImportError, caught)
```

Both directions, because a subtype and a supertype are two different catches and
either one swallows. Any present or future member of that graph is now decided
correctly without the module being edited again.

## Two generalisable moves

1. **Prefer a derivation over an enumeration whenever an authoritative structure
   exists.** `issubclass` reads the real class graph; a frozenset restates it and
   drifts. This is the same rule as "derive completeness, never assert it",
   applied to a type hierarchy rather than a file population.
2. **Fail closed on the unresolvable case.** A name outside `builtins` cannot be
   reasoned about, and treating the unknown as harmless is precisely how a
   predicate gets evaded — catch something it has never heard of. Fail-closed
   costs false positives, which a control pins; fail-open costs soundness, which
   nothing catches.

## How to apply

When you find yourself writing a set of names with a comment justifying *why these
ones*, check whether the language or runtime already holds the relation you are
approximating. If it does, ask it. And when a review proposes adding one entry to
such a set, treat that as the signal to replace the set.
