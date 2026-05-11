# Contributing to Semia

Thanks for taking the time to contribute. This project is licensed under
[Apache-2.0](LICENSE), and contributions of any size are welcome — bug
reports, documentation fixes, detector rules, and code.

## Quick start

1. Fork the repository and clone your fork.
2. Create a virtual environment and install in editable mode:
   ```bash
   python3 -m venv --clear .venv
   source .venv/bin/activate
   python -m pip install -e ".[anthropic]"
   ```
3. Install the pre-commit hooks (one-time):
   ```bash
   python -m pip install pre-commit
   pre-commit install
   pre-commit run --all-files   # establishes a clean baseline
   ```
4. Run the local quality gates:
   ```bash
   make check
   ```
5. Make your change on a topic branch.
6. Sign off your commits — see [DCO](#developer-certificate-of-origin-dco).
7. Open a pull request against `main`.

## Developer Certificate of Origin (DCO)

We require every commit to carry a `Signed-off-by` trailer per the
[Developer Certificate of Origin](https://developercertificate.org/). This
certifies that you wrote the patch (or have the right to submit it under the
project's license).

Add the sign-off automatically with:

```bash
git commit -s -m "Your message"
```

This appends a line like:

```
Signed-off-by: Jane Doe <jane@example.com>
```

We do **not** require a separate Contributor License Agreement. The
combination of Apache-2.0 + DCO is sufficient.

## Code style

- Python 3.11+; CI also runs against 3.12.
- Format and lint with `ruff` (run automatically via pre-commit).
- Keep root project runtime dependencies at zero where possible. New runtime
  dependencies in `semia-core` or `semia-cli` need a written justification
  in the PR description.
- Public APIs should have type hints.
- Tests use stdlib `unittest`; pytest is not used.

The pre-commit suite runs:

- File hygiene (trailing whitespace, end-of-file newline, large-file guard,
  merge-conflict markers, private-key detection, line-ending normalization).
- YAML / JSON / TOML syntax checks.
- `ruff` lint with auto-fix.
- `ruff format`.
- `gitleaks` against staged changes.

CI re-runs the same hooks except for `gitleaks`, which stays local-only:
the GitHub Action requires a paid license for organization repositories,
so we rely on the pre-commit hook (and its repo-wide
`pre-commit run --all-files` mode) to catch secrets before push.

## Tests

```bash
make check          # compile + tests + manifest validation
make build          # package metadata check
make release-check  # full pre-release gate
```

Add tests for any behavior change. Detector / synthesizer / evidence-aligner
changes should include golden-file fixtures under `tests/` whenever
practical.

## Commit messages

Conventional, imperative, present tense. Examples:

```
fix(detector): correct evidence alignment for nested actions
feat(cli): add --provider gemini
docs: clarify Souffle prerequisite
```

Keep the subject under 70 characters; expand in the body. Reference the
issue (`Fixes #42`) when applicable.

## Pull requests

- One logical change per PR. Split big rewrites into reviewable steps.
- Describe the *why*, not just the *what*.
- Link related issues.
- Update `CHANGELOG.md` under `## [Unreleased]` if your change is
  user-visible.
- CI must be green before merge.
- Maintainers may rebase/squash on merge to keep history clean.

## Reporting bugs

For non-security bugs, open a GitHub issue with:

- Steps to reproduce.
- Expected vs. actual behavior.
- Semia version (`semia --version`) and Python version.
- Relevant artifacts from `.semia/runs/<run-id>/` if available — please
  redact any credentials before attaching.

For **security** issues, see [SECURITY.md](SECURITY.md). Do not file public
issues for them.

## Code of Conduct

We follow version 2.1 of the
[Contributor Covenant](https://www.contributor-covenant.org/version/2/1/code_of_conduct/).
By participating in this project you agree to abide by its terms. Report
unacceptable behavior to **conduct@riema.xyz**.

## License

By contributing, you agree that your contributions will be licensed under
the [Apache License 2.0](LICENSE), the same license that covers this
project. Trademarks ("Semia" and the berabuddies marks) are
**not** licensed under Apache-2.0 — see [TRADEMARKS.md](TRADEMARKS.md).
