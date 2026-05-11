# Security Check Skill for Clawdbot

![Security Badge](https://img.shields.io/badge/security-audited-brightgreen)
![Version](https://img.shields.io/badge/version-1.0.0-blue)
![License](https://img.shields.io/badge/license-MIT-blue)

A comprehensive security auditing skill for Clawdbot that inspects skills before installation and performs regular security audits to detect malicious intent, prompt injection, secrets exposure, and misaligned behavior.

## 🎯 Purpose

The security-check skill provides automated tools and comprehensive checklists to ensure your Clawdbot skills remain secure. It's designed to:

- **Pre-installation security checks** - Scan any skill before installing it
- **Daily security audits** - Regular monitoring of installed skills
- **Prompt injection detection** - Identify attempts to override system instructions
- **Secrets detection** - Find hardcoded passwords, API keys, and tokens
- **Behavior verification** - Ensure skill behavior matches its description
- **Dependency auditing** - Check for vulnerable packages

## 🚀 Features

### Automated Security Scanner

A Python-based scanner that performs:

- **Prompt injection pattern detection** - Scans documentation for instruction override attempts
- **Code security analysis** - Detects dangerous patterns (eval, exec, hardcoded secrets)
- **Reference material scanning** - Checks for suspicious URLs and credential exposure
- **Severity classification** - HIGH (block), MEDIUM (review), LOW (info)

### Comprehensive Security Checklist

Detailed coverage of:

- Documentation integrity verification
- Code security patterns
- Secrets and credential exposure
- Command-behavior alignment
- File system boundary checks
- Network security considerations
- Dependency vulnerability scanning

### Prompt Injection Pattern Detection

Extensive guide covering:

- 6 categories of injection patterns
- Automated detection strategies
- Red flag indicators with examples
- Safe vs malicious pattern comparison
- Mitigation techniques

## 📋 Quick Start

### Pre-Installation Check

Before installing a new skill from ClawdHub or any source:

```bash
python3 scripts/scan_skill.py /path/to/new-skill
```

**Example output:**
```json
{
  "skill_name": "example-skill",
  "issues": [],
  "warnings": [
    {
      "severity": "MEDIUM",
      "file": "scripts/helper.py",
      "issue": "os.system() usage detected",
      "recommendation": "Review and ensure this is safe"
    }
  ],
  "passed": [
    {"file": "SKILL.md", "check": "Prompt injection scan", "status": "Completed"}
  ],
  "summary": "WARNINGS: 1 warning(s) (no critical issues)"
}
```

### Daily Security Audit

Scan all installed skills:

```bash
cd /path/to/skills
for skill in */; do
    python3 /path/to/security-check/scripts/scan_skill.py "$skill"
done
```

## 🔍 What Gets Checked

### Security Scanner Checks

1. **SKILL.md Analysis**
   - Prompt injection patterns
   - External network calls
   - Suspicious instructions

2. **Scripts Directory**
   - Dangerous command patterns (rm -rf, dd, mkfs)
   - Hardcoded secrets and credentials
   - eval() and exec() with user input
   - Unauthorized network requests
   - File operations outside skill directory

3. **References Directory**
   - Hardcoded secrets (passwords, API keys, tokens)
   - Suspicious URLs (pastebin, raw GitHub links)
   - Sensitive information exposure

### Manual Security Checklist

Use `references/security-checklist.md` for:

- Documentation integrity verification
- Code security pattern reviews
- Secrets and credential exposure checks
- Command-behavior alignment verification
- Network security assessments
- Dependency vulnerability scanning

### Prompt Injection Detection

Use `references/prompt-injection-patterns.md` for:

- Pattern identification
- Detection strategies (automated + manual)
- Red flag indicators
- Safe pattern recognition
- Mitigation techniques

## 🛡️ Security Severity Levels

### HIGH (Immediate Block)
- Prompt injection patterns detected
- Hardcoded secrets or credentials
- Data exfiltration capabilities
- Unauthorized file system access
- Dangerous file operations (rm -rf, dd, etc.)
- eval() or exec() with untrusted input

**Action:** Do not install. Report to skill author.

### MEDIUM (Review Required)
- Suspicious but not clearly malicious
- Requires user approval for specific operations
- Limited network access to unverified endpoints
- Unsafe subprocess usage (shell=True)
- Environment variable exposure risks

**Action:** Manual review. Install only if justified and understood.

### LOW (Informational)
- Suspicious URLs (may be legitimate)
- Documentation of deprecated practices
- Minor code quality issues
- Potential improvements for security

**Action:** Note for future review. Generally safe to install.

## 📊 Usage Examples

### Example 1: Safe Skill

```bash
$ python3 scripts/scan_skill.py /path/to/safe-skill
{
  "summary": "PASSED: No security issues found"
}
```

**Verdict:** ✅ SAFE - Can install

### Example 2: Skill with Warning

```bash
$ python3 scripts/scan_skill.py /path/to/suspicious-skill
{
  "issues": [],
  "warnings": [
    {
      "severity": "MEDIUM",
      "file": "scripts/network.py",
      "issue": "External network call pattern: requests.post.*http://",
      "recommendation": "Verify all network calls are intentional and secure"
    }
  ],
  "summary": "WARNINGS: 1 warning(s) (no critical issues)"
}
```

**Verdict:** ⚠️ WARNING - Manual review required before installation

### Example 3: Malicious Skill

```bash
$ python3 scripts/scan_skill.py /path/to/malicious-skill
{
  "issues": [
    {
      "severity": "HIGH",
      "file": "SKILL.md",
      "issue": "Potential prompt injection pattern detected: override.*programming",
      "recommendation": "Review and remove suspicious instruction patterns"
    },
    {
      "severity": "HIGH",
      "file": "scripts/evil.py",
      "issue": "eval() usage detected",
      "recommendation": "Review and ensure this is intentional and safe"
    }
  ],
  "summary": "SECURITY ISSUES FOUND: 2 issue(s), 0 warning(s)"
}
```

**Verdict:** ❌ BLOCKED - Do not install

## 📦 Installation

### As a Clawdbot Skill

1. Copy the skill to your Clawdbot skills directory:
   ```bash
   cp -r security-check /path/to/clawd/skills/
   ```

2. The skill will be automatically detected by Clawdbot

3. Use the scanner:
   ```bash
   python3 /path/to/clawd/skills/security-check/scripts/scan_skill.py <skill-path>
   ```

### Standalone Scanner

You can also use the scanner as a standalone tool:

```bash
git clone https://github.com/yourusername/security-check-skill.git
cd security-check-skill
python3 scripts/scan_skill.py <skill-path>
```

## 🔧 Development

### Running Tests

```bash
# Run the scanner on the security-check skill itself (self-audit)
python3 scripts/scan_skill.py .

# Scan example skills
python3 scripts/scan_skill.py /path/to/other-skill
```

### Contributing

Contributions are welcome! Please:

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Test thoroughly
5. Submit a pull request

### Areas for Improvement

- [ ] Add semantic analysis for prompt injection
- [ ] Reduce false positives with context-aware filtering
- [ ] Add behavior verification (compare description vs actual operations)
- [ ] Network security checks (suspicious domains, SSL verification)
- [ ] File system boundary enforcement
- [ ] Dependency vulnerability scanning (npm audit, pip-audit)
- [ ] Historical tracking of security posture
- [ ] Comparative analysis between skill versions
- [ ] Unit tests for scanner
- [ ] Integration with ClawdHub for security badges

## 📚 Documentation

- **SKILL.md** - Complete skill documentation and usage guide
- **references/security-checklist.md** - Comprehensive security checklist
- **references/prompt-injection-patterns.md** - Prompt injection detection guide
- **scripts/scan_skill.py** - Automated security scanner implementation

## 🔒 Security Principles

This skill follows these security principles:

1. **Zero Trust** - Verify every skill, even from trusted sources
2. **Defense in Depth** - Multiple layers of security checks
3. **Transparency** - Clear reporting of findings
4. **Continuous Monitoring** - Regular audits, not just pre-installation
5. **Community Security** - Share findings, improve ecosystem security

## 📈 Audit Results

### Recent Audit (January 30, 2026)

**Skills Audited:** 22 installed skills
**Results:**
- ✅ 20 skills: No security issues
- ⚠️ 2 skills: Documentation warnings (false positives)
- ❌ 0 skills: High severity issues

**Overall Posture:** EXCELLENT

## 🤝 Community

This skill is part of the Clawdbot ecosystem. Join the discussion:

- **Clawdbot Discord:** [Link to Discord]
- **ClawdHub:** [Link to ClawdHub]
- **GitHub Issues:** Report bugs and feature requests

## 📄 License

MIT License - see LICENSE file for details

## 🙏 Acknowledgments

- Built for the Clawdbot community
- Inspired by OWASP security guidelines
- Incorporates lessons from AI security research
- Uses pattern matching techniques from cybersecurity best practices

## 🔗 Related Resources

- [Clawdbot Documentation](https://docs.clawd.bot)
- [OWASP Top 10 for LLMs](https://owasp.org/www-project-top-10-for-large-language-model-applications/)
- [NIST AI Security Guidelines](https://www.nist.gov/itl/ai-risk-management-framework)
- [Prompt Injection Research](https://promptingguide.ai/security)

---

**Built with ❤️ for the Clawdbot community**

*Security is not a feature, it's a mindset.*
