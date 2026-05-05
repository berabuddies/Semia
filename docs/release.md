# Release checklist

Semia Skillscan is intended to be built around Skill Behavior Mapping, with
deterministic tooling as the release boundary. A release is not ready until the
host integrations and stdlib quality gates agree.

## Before tagging

1. Run `make check`.
2. Run `make build`.
3. Run `make release-check`.
4. Confirm `README.md` describes the current user-facing command shape.
5. Confirm integration manifests under `packages/semia-plugins/` validate in CI.
6. Confirm any Souffle fallback artifacts are covered by `docs/supply-chain.md`.
7. Confirm generated distributions in `dist/` contain only intended files.

## GitHub release

1. Tag releases as `vX.Y.Z`.
2. Let the `Release Check` workflow run the package metadata build dry run.
3. Attach release notes with:
   - user-facing changes
   - host integration compatibility notes
   - detector/rule changes
   - supply-chain changes
   - known verification gaps
4. Publish only after CI and release-check are green.

## Local command summary

```bash
make help
make check
make build
make release-check
```

If the package lanes add real source/wheel publishing, replace the metadata
dry run with a proper `uv build` gate and update this checklist in the same
pull request.
