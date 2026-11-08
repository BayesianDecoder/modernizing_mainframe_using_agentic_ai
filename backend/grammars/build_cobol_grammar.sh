#!/usr/bin/env bash
# Builds backend/grammars/cobol.so from the yutaro-sakamoto/tree-sitter-cobol
# grammar source. See README.md in this directory for why this exists —
# tree-sitter-languages does not bundle a COBOL grammar, so it's compiled
# locally instead. Requires: git, a C compiler, and tree-sitter==0.21.3
# (see requirements.txt — 0.22+ removes Language.build_library()).
set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
WORKDIR="$(mktemp -d)"
trap 'rm -rf "$WORKDIR"' EXIT

git clone --depth 1 https://github.com/yutaro-sakamoto/tree-sitter-cobol.git "$WORKDIR/tree-sitter-cobol"

python3 -c "
from tree_sitter import Language
Language.build_library('$HERE/cobol.so', ['$WORKDIR/tree-sitter-cobol'])
print('Built $HERE/cobol.so')
"
