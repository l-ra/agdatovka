"""Secret and production-host scans for checked-in synthetic fixtures."""
import re
PRODUCTION_HOSTS = re.compile(r"(?:^|[./])(datovka\.gov\.cz|isds\.cz|mojedatovaschranka\.cz)(?:$|[/])", re.I)
SECRET_PATTERNS = (re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----"), re.compile(r"\b(?:AKIA|ASIA)[A-Z0-9]{16}\b"), re.compile(r"\b(?:password|secret|token)\s*[:=]\s*['\"][^'\"]{8,}['\"]", re.I))
def scan_fixture_text(values):
    findings = []
    for value in values:
        if PRODUCTION_HOSTS.search(value): findings.append("production-host")
        if any(pattern.search(value) for pattern in SECRET_PATTERNS): findings.append("secret-like-value")
    return sorted(set(findings))
