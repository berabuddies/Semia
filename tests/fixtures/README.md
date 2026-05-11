# Test Fixtures

## `skills/`

A corpus of real public agent skills used as inputs for `semia-core`
corpus-level smoke tests.

- **Source**: copied from `semia/resources/skills/skills/`, selected via
  `semia/scope/dev_dataset.scope`.
- **Date copied**: 2026-05-11.
- **Counts**: 50 skill directories under 35 owner directories, 259 files,
  ~1.6 MB on disk.
- **Layout**: `tests/fixtures/skills/<owner>/<skill_name>/...`, preserving the
  source tree exactly.
- **Purpose**: drives `tests/core/test_skill_corpus.py`, which exercises
  `semia_core.prepare.build_prepare_bundle` and the full
  `prepare -> extract_baseline -> check_facts -> detect` pipeline against
  realistic SKILL.md content.

### Notes

- These are real public skills authored by third parties. They are included
  as **test inputs**, not as exemplars of any particular policy outcome —
  some skills may produce detector findings, and that is expected behavior
  for the corpus test (the test only asserts that the pipeline runs to
  completion).
- One skill (`contrario/aetherlang-chef/`) contains a nested `SKILL.md` in a
  sub-directory; the corpus walker treats both as valid inputs.
- No `.pyc`, `__pycache__`, or large binary files were copied. If you add
  more fixtures, keep total size under 2 MB.
