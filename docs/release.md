# Release checklist

Semia Skillscan is intended to be built around Skill Behavior Mapping, with
deterministic tooling as the release boundary. A release is not ready until the
host integrations and stdlib quality gates agree.

## One-time setup for PyPI trusted publishing

The `Release` workflow uses [PyPI trusted publishing](https://docs.pypi.org/trusted-publishers/)
via GitHub OIDC, so no long-lived API token has to be stored as a GitHub
secret.

1. **PyPI side** — on https://pypi.org, open the project page →
   *Publishing* → *Add a new pending publisher* and fill in:
   - Owner: `RiemaLabs`
   - Repository name: `semia-skillscan`
   - Workflow filename: `release.yml`
   - Environment name: `pypi`
2. **GitHub side** — *Settings* → *Environments* → *New environment* `pypi`.
   Optionally restrict deployments to tags matching `v*` and require a
   reviewer before the publish job runs.

The `release.yml` workflow already requests `id-token: write` and targets the
`pypi` environment, so once the two sides agree, tagged builds will publish.

## Before tagging

1. Run `make check`.
2. Run `make build` — this now runs metadata validation, builds the wheel and
   sdist, and runs `twine check` against the artifacts.
3. Run `make release-check` to additionally verify that the release-required
   docs (`README.md`, `LICENSE`, `docs/release.md`, `docs/supply-chain.md`) are
   present.
4. Confirm `README.md` describes the current user-facing command shape.
5. Confirm integration manifests under `packages/semia-plugins/` validate in
   CI.
6. Confirm any Souffle fallback artifacts are covered by
   `docs/supply-chain.md`.
7. Confirm generated distributions in `dist/` contain only intended files.

To do a dry-run of the full release pipeline without publishing, run the
`Release` workflow via *Actions* → *Release* → *Run workflow*. It will execute
the validation + build job but skip the publish job.

## GitHub release

1. Tag releases as `vX.Y.Z`.
2. The `Release` workflow runs the validation + build job, uploads the
   distributions as `python-package-distributions`, and then runs the
   `publish-pypi` job (gated on the `pypi` environment) which uploads to
   PyPI via OIDC trusted publishing.
3. Attach release notes with:
   - user-facing changes
   - host integration compatibility notes
   - detector/rule changes
   - supply-chain changes
   - known verification gaps
4. Publish a GitHub release only after the `Release` workflow is fully green.

## Local command summary

```bash
make help
make check
make build           # metadata check + python -m build + twine check
make release-check   # check + build + verify required docs
```

`make build` and `make release-check` require the standard PyPA tooling. If
they are not on PATH, install once:

```bash
python -m pip install build twine
```

## Publishing the OpenClaw skill to ClawHub

The OpenClaw integration is distributed as a *skill* (not a code plugin) via
the official [ClawHub](https://github.com/openclaw/clawhub) registry. The
skill body is `packages/semia-plugins/openclaw/skills/semia-skillscan/`; its
frontmatter declares `requires.bins: [semia]` plus an
`install: [{kind: uv, package: semia-skillscan}]` block so ClawHub can
provision the `semia` CLI on first use.

### Automated publish (default)

The `publish-clawhub` job in `.github/workflows/release.yml` runs after
`publish-pypi` succeeds on every `v*` tag push. It enforces that the
`version:` in the skill's frontmatter matches the tag, then runs
`clawhub skill publish` with `--version <tag>` and `--changelog "Release <tag>"`.

One-time setup:

1. **ClawHub side** — `npm i -g clawhub && clawhub login` locally once to
   provision an account, then generate a publish token from the ClawHub UI
   (or `clawhub token create`, if available).
2. **GitHub side** — *Settings → Environments* → new environment `clawhub`.
   Add a secret `CLAWHUB_TOKEN` containing the token from step 1. Optionally
   restrict deployments to tags matching `v*` and require a reviewer.

Per release: bump `version:` in `SKILL.md` to match the next tag, push the
tag, and the workflow handles the rest.

### Manual publish (fallback)

If the workflow is unavailable, publish from a local checkout:

```bash
npm i -g clawhub
clawhub login                                    # or: clawhub login --token clh_...
clawhub skill publish \
  packages/semia-plugins/openclaw/skills/semia-skillscan \
  --slug semia-skillscan \
  --name "Semia Skillscan" \
  --version 0.1.0 \
  --changelog "Release 0.1.0"
```

End users install with:

```bash
openclaw plugins install clawhub:semia-skillscan
```
