# COBOL grammar for tree-sitter

`tree-sitter-languages` (the usual shortcut for getting prebuilt grammars)
does **not** ship a COBOL grammar — its compiled `languages.so` has no
`tree_sitter_cobol` symbol at all, in any version. There is also no
`tree-sitter-cobol` package on PyPI. So AST parsing here is not a switch
you flip with `pip install`; the grammar has to be compiled from source
once, locally.

## Building

```bash
backend/grammars/build_cobol_grammar.sh
```

This clones [yutaro-sakamoto/tree-sitter-cobol](https://github.com/yutaro-sakamoto/tree-sitter-cobol)
(MIT licensed; ships its generated `parser.c`, so no Node/tree-sitter-cli
needed — just a C compiler) into a temp dir and compiles it into
`backend/grammars/cobol.so` via `tree_sitter.Language.build_library`.

`cobol.so` is a local build artifact (like a `.pyc`) — it isn't committed;
regenerate it after cloning this repo or if it goes missing.

## Requirements

- `git` and a C compiler (Xcode CLT on macOS, `build-essential` on Debian/Ubuntu)
- `tree-sitter==0.21.3` exactly — 0.22+ removes `Language.build_library()`
  and the `Language(path, name)` constructor this build relies on. See the
  pin + comment in `requirements.txt`.

## Notes on the grammar itself

The grammar's node type is `"COBOL"` (uppercase) — `Language(path, "COBOL")`,
not `"cobol"`. It also represents `IF`/`EVALUATE` blocks as a **flat**
sequence of sibling statements (`if_header`, ..., `END_IF`) rather than
nesting the conditional body under the if node — `backend/parser.py`'s
`_parse_ast` walker threads a depth counter across sibling lists to detect
"is this CALL inside a conditional" rather than relying on tree nesting.
Comment node spans are zero-width in this grammar (comment text isn't
retained), so program descriptions are still pulled via a light text scan
of the leading `*` comment block rather than the AST.
