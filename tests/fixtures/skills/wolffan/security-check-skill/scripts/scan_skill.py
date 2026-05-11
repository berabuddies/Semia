#!/usr/bin/env python3
"""
Security scanner for Clawdbot skills.
Scans skill files for potential security issues.
"""

import os
import re
import sys
import json
from pathlib import Path
from typing import List, Dict, Any

class SecurityScanner:
    def __init__(self, skill_path: str):
        self.skill_path = Path(skill_path)
        self.issues = []
        self.warnings = []
        self.passed = []

    def scan(self) -> Dict[str, Any]:
        """Run all security checks on the skill."""
        results = {
            'skill_name': self.skill_path.name,
            'issues': [],
            'warnings': [],
            'passed': [],
            'summary': ''
        }

        # Check SKILL.md
        skill_md = self.skill_path / "SKILL.md"
        if skill_md.exists():
            self._check_skill_md(skill_md)
        else:
            results['issues'].append({
                'severity': 'HIGH',
                'file': 'SKILL.md',
                'issue': 'Missing required SKILL.md file'
            })

        # Scan scripts for dangerous patterns
        scripts_dir = self.skill_path / "scripts"
        if scripts_dir.exists():
            self._scan_scripts(scripts_dir)

        # Scan references for suspicious content
        refs_dir = self.skill_path / "references"
        if refs_dir.exists():
            self._scan_references(refs_dir)

        results['issues'] = self.issues
        results['warnings'] = self.warnings
        results['passed'] = self.passed

        # Generate summary
        if self.issues:
            results['summary'] = f"SECURITY ISSUES FOUND: {len(self.issues)} issue(s), {len(self.warnings)} warning(s)"
        elif self.warnings:
            results['summary'] = f"WARNINGS: {len(self.warnings)} warning(s) (no critical issues)"
        else:
            results['summary'] = "PASSED: No security issues found"

        return results

    def _check_skill_md(self, skill_md: Path):
        """Check SKILL.md for security concerns."""
        with open(skill_md, 'r', encoding='utf-8') as f:
            content = f.read()

        # Check for prompt injection patterns in the skill description
        prompt_injection_patterns = [
            r'ignore (previous|above|earlier)',
            r'disregard (previous|above|earlier)',
            r'forget (previous|above|earlier)',
            r'overwrite (previous|above|earlier)',
            r'bypass (security|restrictions|filters)',
            r'admin.*override',
            r'system.*override',
            r'replace.*instructions',
        ]

        for pattern in prompt_injection_patterns:
            if re.search(pattern, content, re.IGNORECASE):
                self.issues.append({
                    'severity': 'HIGH',
                    'file': 'SKILL.md',
                    'issue': f'Potential prompt injection pattern detected: {pattern}',
                    'recommendation': 'Review and remove suspicious instruction patterns'
                })

        # Check for external network calls in description
        network_patterns = [
            r'curl.*http[s]?://',
            r'wget.*http[s]?://',
            r'fetch.*http[s]?://',
            r'request.*http[s]?://',
        ]

        for pattern in network_patterns:
            if re.search(pattern, content, re.IGNORECASE):
                self.warnings.append({
                    'severity': 'MEDIUM',
                    'file': 'SKILL.md',
                    'issue': f'External network call pattern: {pattern}',
                    'recommendation': 'Verify all network calls are intentional and secure'
                })

        self.passed.append({
            'file': 'SKILL.md',
            'check': 'Prompt injection scan',
            'status': 'Completed'
        })

    def _scan_scripts(self, scripts_dir: Path):
        """Scan scripts directory for dangerous patterns."""
        dangerous_patterns = {
            'HIGH': [
                (r'os\.system\([^)]*rm\s+-rf', 'Deletion command'),
                (r'os\.system\([^)]*rm\s+-r/', 'Recursive deletion'),
                (r'subprocess\.call\([^)]*rm', 'Subprocess deletion'),
                (r'exec\([^)]*rm', 'Exec deletion'),
                (r'eval\(', 'eval() usage'),
                (r'__import__\([^)]*os', 'Dynamic os import'),
            ],
            'MEDIUM': [
                (r'os\.system\(', 'os.system() usage'),
                (r'subprocess\.(call|run|Popen).*shell=True', 'shell=True usage'),
                (r'open\([^)]*[\'"].*password[\'"]', 'Password in file'),
                (r'open\([^)]*[\'"].*secret[\'"]', 'Secret in file'),
                (r'open\([^)]*[\'"].*token[\'"]', 'Token in file'),
                (r'open\([^)]*[\'"].*api_key[\'"]', 'API key in file'),
            ]
        }

        for script_file in scripts_dir.glob('*.py'):
            with open(script_file, 'r', encoding='utf-8') as f:
                content = f.read()

            for severity, patterns in dangerous_patterns.items():
                for pattern, desc in patterns:
                    if re.search(pattern, content, re.IGNORECASE):
                        issue_data = {
                            'severity': severity,
                            'file': str(script_file.relative_to(self.skill_path)),
                            'issue': f'{desc} detected',
                            'recommendation': 'Review and ensure this is intentional and safe'
                        }
                        if severity == 'HIGH':
                            self.issues.append(issue_data)
                        else:
                            self.warnings.append(issue_data)

        self.passed.append({
            'directory': 'scripts/',
            'check': 'Dangerous pattern scan',
            'status': 'Completed'
        })

    def _scan_references(self, refs_dir: Path):
        """Scan references directory for suspicious content."""
        secret_patterns = [
            r'password\s*[=:]\s*[\'"][\w]+[\'"]',
            r'secret\s*[=:]\s*[\'"][\w]+[\'"]',
            r'token\s*[=:]\s*[\'"][\w]{20,}[\'"]',
            r'api[_-]?key\s*[=:]\s*[\'"][\w]{20,}[\'"]',
            r'aws[_-]?(access[_-]?key|secret[_-]?key)\s*[=:]\s*[\'"][\w]{20,}[\'"]',
        ]

        for ref_file in refs_dir.glob('*.md'):
            with open(ref_file, 'r', encoding='utf-8') as f:
                content = f.read()

            for pattern in secret_patterns:
                matches = re.findall(pattern, content, re.IGNORECASE)
                if matches:
                    self.issues.append({
                        'severity': 'HIGH',
                        'file': str(ref_file.relative_to(self.skill_path)),
                        'issue': f'Potential hardcoded secrets detected: {len(matches)} match(es)',
                        'recommendation': 'Remove hardcoded secrets and use proper secret management'
                    })

            # Check for suspicious external URLs
            url_pattern = r'https?://[^\s\)]+'
            urls = re.findall(url_pattern, content)
            for url in urls:
                if any(domain in url.lower() for domain in ['pastebin', 'raw.githubusercontent', 'bit.ly', 't.co']):
                    self.warnings.append({
                        'severity': 'LOW',
                        'file': str(ref_file.relative_to(self.skill_path)),
                        'issue': f'Suspicious URL detected: {url}',
                        'recommendation': 'Verify this URL is legitimate and safe'
                    })

        self.passed.append({
            'directory': 'references/',
            'check': 'Secret and URL scan',
            'status': 'Completed'
        })

def main():
    if len(sys.argv) < 2:
        print("Usage: python scan_skill.py <skill_path>")
        sys.exit(1)

    skill_path = sys.argv[1]
    scanner = SecurityScanner(skill_path)
    results = scanner.scan()

    # Print results
    print(json.dumps(results, indent=2))

if __name__ == '__main__':
    main()
