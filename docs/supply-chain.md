# Supply-chain policy

Semia scans untrusted agent-skill content, so the release pipeline
must keep the analyzer itself boring, pinned, and auditable.

## Dependency posture

- Keep the root project stdlib-only unless a dependency is required by a
  concrete package lane.
- Prefer deterministic local checks over network-time behavior.
- Do not download executables during `semia scan`.
- Keep CI dependency installation explicit and visible in workflow logs.
- Review GitHub Actions updates before merging automated bumps.

## Souffle fallback guidance

Semia may ship a limited Souffle fallback for users without a local `souffle`
binary. Treat that fallback as a release artifact, not as an implicit runtime
download.

Required controls:

- Prefer `SEMIA_SOUFFLE_BIN` or a system `souffle` on `PATH` first.
- Package fallback binaries per platform with versioned filenames.
- Record SHA256 checksums, source version, build environment, and license data.
- Generate SBOM/provenance for fallback artifacts during release.
- Verify checksums before invoking a fallback binary.
- Never execute a fallback binary fetched at scan time.
- Keep Datalog includes restricted to Semia-controlled rule directories.
- Document how users can disable fallback execution in locked-down
  environments.

## Plugin manifests

Plugin manifests are validated in CI with a schema-light stdlib checker. The
checker intentionally verifies JSON shape and stable identity fields without
pretending to replace host-specific validation. Host-specific package validation
should be added as each plugin distribution lands.
