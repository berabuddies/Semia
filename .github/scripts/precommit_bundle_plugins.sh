#!/usr/bin/env bash
# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 berabuddies
#
# Pre-commit hook: rebuild plugin zipapps when bundled src has changed.
#
# Runs `make bundle-plugins` and then checks whether any .pyz file under
# packages/semia-plugins/*/bin/ now differs from the working tree's
# previously-committed bytes. If so, the hook fails the commit and tells
# the user to re-stage the regenerated bundles — mirroring how ruff's
# --fix mode and `mixed-line-ending --fix=lf` behave: the fix lands in
# the working tree, the commit aborts, the user re-stages and retries.
#
# Triggered (per .pre-commit-config.yaml) only when files under
#   packages/semia-cli/src/
#   packages/semia-core/src/
# are staged, so a docs-only or CI-only commit pays no rebuild cost.

set -euo pipefail

# Resolve to repo root regardless of where pre-commit invokes us from.
REPO_ROOT="$(git rev-parse --show-toplevel)"
cd "$REPO_ROOT"

make bundle-plugins >/dev/null

if ! git diff --quiet -- 'packages/semia-plugins/*/bin/*.pyz'; then
    cat >&2 <<'EOF'

──────────────────────────────────────────────────────────────────────
  Plugin zipapps regenerated.

  Your edits under packages/semia-{cli,core}/src/ changed bytes the
  bundles include, so make bundle-plugins produced new .pyz files.

  Re-stage them and retry the commit:

      git add packages/semia-plugins/*/bin/*.pyz
      git commit ...

  (CI runs the same drift check; this hook just catches it locally.)
──────────────────────────────────────────────────────────────────────

EOF
    exit 1
fi
