# Security Policy

Semia is a static-analysis tool for AI agent skills. We treat the
audited skill as untrusted input, and we hold our own analyzer code to the
same standard of care.

## Supported Versions

While the project is pre-1.0, only `main` and the latest released minor
receive security fixes.

| Version | Supported          |
| ------- | ------------------ |
| `main`  | :white_check_mark: |
| `0.1.x` | :white_check_mark: |
| < 0.1   | :x:                |

After 1.0 we will commit to a documented support window in this file.

## Reporting a Vulnerability

**Do not file public GitHub issues for security problems.**

Use GitHub's private vulnerability reporting to open a draft advisory:
[**Report a vulnerability**](https://github.com/berabuddies/Semia/security/advisories/new).
The advisory is private between you and the maintainers until we publish it.

Please include:

- A description of the issue and its impact.
- A minimal reproduction (steps, sample skill input, or PoC).
- Affected versions, Python versions, and operating systems.
- Whether the issue is exploitable from a malicious skill input alone, or
  requires additional access (LLM credentials, local files, etc.).
- Your name and any disclosure / credit preferences.

GitHub advisories support file attachments for PoCs and screenshots, so
sensitive material can stay inside the private thread.

### Response targets

- **Acknowledge receipt:** within 3 business days.
- **Initial assessment:** within 10 business days.
- **Fix or mitigation:** within 90 days for confirmed reports, sooner for
  high-severity issues.

### Coordinated disclosure

We follow a 90-day coordinated-disclosure window by default. We will extend
it for complex fixes when the reporter agrees, but not indefinitely. Once a
fix ships, we credit reporters in the release notes unless they ask to remain
anonymous.

## Threat Model

Semia analyzes **untrusted** skill content. The audited skill may:

- Contain prompt-injection payloads aimed at the synthesizer LLM.
- Contain malformed Markdown or source files designed to crash the parser.
- Reference network resources we must not fetch.
- Reference local paths we must not read.
- Attempt to coerce the analyzer into executing code, hooks, or installers.

If you find a way to make Semia:

- Execute a target skill's code, hooks, installers, or network requests
  during a scan;
- Exfiltrate the user's local files, environment variables, or credentials
  through crafted skill input;
- Forge or tamper with audit artifacts so a malicious skill appears benign;
- Bypass evidence-grounding so unsupported facts pass detector legality;

— that is a security vulnerability. Please report it.

## Scope

In scope:

- Code under `packages/semia-core/`, `packages/semia-cli/`, and
  `packages/semia-plugins/`.
- Build and release tooling under `build_backend/`, `Makefile`, and
  workflows in `.github/`.
- Plugin manifests under `packages/semia-plugins/*/`.
- Bundled SDL rule files under `packages/semia-core/src/semia_core/rules/`.

Out of scope (please report directly to the upstream project):

- Vulnerabilities in third-party LLM providers (OpenAI, Anthropic, etc.).
- Vulnerabilities in Souffle or its packaging.
- Vulnerabilities in host agent CLIs (Codex CLI, Claude Code, OpenClaw).

## Safe Harbor

We will not pursue legal action against good-faith security research that:

- Does not access user data beyond what is necessary to demonstrate the
  issue.
- Does not degrade service for other users.
- Does not exfiltrate or publish data discovered during testing.
- Reports the issue privately and gives us a reasonable window to fix it
  before public disclosure.

If in doubt, open a private advisory first via
[Report a vulnerability](https://github.com/berabuddies/Semia/security/advisories/new).
