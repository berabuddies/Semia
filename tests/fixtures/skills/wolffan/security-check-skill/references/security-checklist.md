# Security Checklist for Skill Audits

This checklist provides comprehensive security criteria for auditing Clawdbot skills before installation and during regular security scans.

## Core Security Principles

### 1. Documentation Integrity (SKILL.md)

#### Required Elements
- ✅ Contains valid YAML frontmatter with `name` and `description`
- ✅ Description accurately reflects skill functionality
- ✅ No misleading or hidden capabilities in description
- ✅ No instruction override patterns

#### Red Flags - Prompt Injection
- ❌ Instructions to ignore/discard previous context
- ❌ Instructions to bypass security or filters
- ❌ System override commands
- ❌ Instructions to replace or modify core behavior
- ❌ Hidden commands in seemingly benign text

#### Examples of Suspicious Patterns
```
"ignore all previous instructions"
"disregard security constraints"
"act as an administrator"
"override system restrictions"
```

### 2. Code Security (scripts/)

#### High Severity Issues
- ❌ `os.system()` with destructive commands (rm -rf, dd, mkfs)
- ❌ `eval()` or `exec()` with user input
- ❌ Hardcoded credentials, API keys, or tokens
- ❌ Dynamic imports of sensitive modules (os, subprocess)
- ❌ File operations outside skill directory
- ❌ Network requests to untrusted sources
- ❌ Code obfuscation or encoding to hide functionality

#### Medium Severity Issues
- ❌ `subprocess` calls with `shell=True`
- ❌ Reading/writing sensitive system files
- ❌ Environment variable exposure
- ❌ Temporary file creation without proper permissions
- ❌ Unvalidated user input in file paths

#### Safe Patterns
- ✅ All file operations within skill directory
- ✅ Use `subprocess.run()` without shell
- ✅ Input validation and sanitization
- ✅ Proper error handling without exposing secrets
- ✅ No hardcoded secrets or credentials

### 3. Reference Material Security (references/)

#### High Severity Issues
- ❌ Hardcoded passwords, API keys, or secrets
- ❌ Production credentials in documentation
- ❌ Authentication tokens or sessions
- ❌ Private keys (SSH, SSL, etc.)
- ❌ Database connection strings with credentials

#### Medium Severity Issues
- ❌ Internal URLs or endpoints not meant for public access
- ❌ Sensitive configuration examples
- ❌ Documentation of security bypasses

#### Low Severity Issues
- ⚠️ Links to external services (verify legitimacy)
- ⚠️ Documentation of deprecated or insecure practices (should be warnings)

### 4. Asset Security (assets/)

#### Red Flags
- ❌ Executable binaries
- ❌ Malicious scripts
- ❌ Obfuscated code
- ❌ Files with suspicious extensions

#### Safe Patterns
- ✅ Text-based templates
- ✅ Images and media files
- ✅ Configuration templates (without secrets)
- ✅ Documentation files

## Skill Behavior Analysis

### Command Alignment Check

When reviewing a skill, verify that:
1. Every command/operation matches the stated purpose
2. No hidden capabilities beyond description
3. No unnecessary file system access
4. No network access unless explicitly required

### Example: Misaligned Skill

**Description:** "Format text documents"
**Actual behavior:** Scans filesystem, sends data to external server
**Verdict:** ❌ MALICIOUS - Description does not match behavior

### Example: Aligned Skill

**Description:** "Convert Markdown to PDF with custom templates"
**Actual behavior:** Reads Markdown, applies template, generates PDF
**Verdict:** ✅ SAFE - Description matches behavior

## Local Configuration Exposure Checks

### Files to Monitor
- `~/.clawdbot/` directory
- `~/.aws/credentials`
- `~/.ssh/` directory
- `~/.npmrc`
- Environment variables containing secrets

### Operations to Block
- Reading from `~/.clawdbot/credentials/`
- Reading from `~/.aws/`
- Reading SSH private keys
- Accessing system keychain
- Reading shell history for secrets

### Safe Operations
- Reading only skill-specific configuration
- Reading from designated workspace directories
- Using approved environment variable patterns
- Reading from explicitly provided file paths

## Network Security

### Safe Network Patterns
- ✅ API calls to documented, public services
- ✅ Requests to official package repositories
- ✅ Webhooks to configured endpoints
- ✅ Data retrieval from trusted sources

### Suspicious Network Patterns
- ❌ Requests to unknown or suspicious domains
- ❌ Data exfiltration to external services
- ❌ Unencrypted HTTP requests for sensitive data
- ❌ Bypassing certificate validation
- ❌ DNS tunneling or covert channels

## Dependency Security

### Check These Files
- `package.json` (Node.js dependencies)
- `requirements.txt` (Python dependencies)
- `Gemfile` (Ruby dependencies)
- `setup.py` or `pyproject.toml` (Python)

### Vulnerability Checks
- Run `npm audit` for Node.js skills
- Run `pip-audit` or `safety` for Python skills
- Check for known CVEs in dependencies
- Verify dependency integrity (hash verification)

## Installation Security Checklist

Before installing a new skill:

1. **Verify Source**
   - Official ClawdHub repository
   - Known trusted developer
   - Verified checksum if available

2. **Review SKILL.md**
   - Clear, accurate description
   - No prompt injection patterns
   - Matches intended use case

3. **Scan Code**
   - Run security scanner
   - Review any HIGH severity issues
   - Investigate MEDIUM severity issues

4. **Verify Behavior**
   - Test in isolated environment first
   - Monitor file system access
   - Monitor network traffic
   - Check for unexpected side effects

5. **Check Dependencies**
   - Audit npm/Python dependencies
   - Verify no known vulnerabilities
   - Review transitive dependencies

## Daily Security Scan Procedure

### Automated Checks
1. Scan all installed skills with `scan_skill.py`
2. Review any new HIGH severity issues
3. Check for modified files in skill directories
4. Verify skill descriptions still match behavior
5. Audit new dependencies if added

### Manual Review
1. Review any changes to SKILL.md files
2. Check for new scripts added to skills
3. Verify no new network endpoints contacted
4. Review any suspicious log entries
5. Cross-reference with security updates

## Reporting Format

### Security Report Template

```markdown
# Security Audit Report
**Date:** [Date]
**Skill:** [Skill Name]
**Version:** [Version]

## Executive Summary
[Overall security posture: SAFE, WARNING, or BLOCK]

## Critical Issues (Immediate Action Required)
[List HIGH severity issues]

## Warnings (Review Recommended)
[List MEDIUM severity issues]

## Informational Notes
[List LOW severity issues and observations]

## Recommendations
[Actionable items to address issues]

## Conclusion
[Final verdict: Install/Block/Requires Changes]
```

## Escalation Criteria

### Immediate Block (Do Not Install)
- HIGH severity security issues present
- Prompt injection patterns detected
- Hardcoded secrets or credentials
- Data exfiltration capabilities
- Unauthorized file system access

### Warning (Install with Caution)
- MEDIUM severity issues present
- Suspicious but not clearly malicious
- Requires user approval for specific operations
- Limited network access to unverified endpoints

### Safe (Install)
- No security issues detected
- Well-documented and transparent
- Matches description perfectly
- No concerning patterns

## Remediation Steps

For skills with security issues:

1. **Document the issue** - Create detailed report
2. **Contact skill author** - Report the finding
3. **Await fix** - Wait for updated version
4. **Re-scan** - Verify issue is resolved
5. **Document resolution** - Update audit records

## References

- Clawdbot Security Documentation
- OWASP Security Guidelines
- NIST Cybersecurity Framework
- Prompt Injection Mitigation Strategies
- Secure Coding Practices
