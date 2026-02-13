# Security Policy

## Supported Versions

We release security updates for the following versions:

| Version | Supported          | Status |
| ------- | ------------------ | ------ |
| 1.0.x   | :white_check_mark: | Current stable release |
| < 1.0   | :x:                | Development versions, not supported |

## Reporting a Vulnerability

**Please do NOT report security vulnerabilities through public GitHub issues.**

Instead, please report security vulnerabilities using one of the following methods:

### Preferred: GitHub Security Advisories

1. Go to https://github.com/openclaw-community/openclaw-hub/security/advisories
2. Click "Report a vulnerability"
3. Fill out the advisory form with details
4. Submit - only maintainers will see the report

### Alternative: Email

If you cannot use GitHub Security Advisories, send an email to:

mgrunert.ca@gmail.com

### What to Include

Please include as much of the following information as possible:

- **Type of vulnerability** (e.g., injection, authentication bypass, data exposure)
- **Affected component** (e.g., specific provider, API endpoint, workflow engine)
- **Affected versions** (e.g., 1.0.0, commit hash)
- **Steps to reproduce** - Detailed, step-by-step instructions
- **Proof of concept** - Code or commands demonstrating the issue
- **Impact assessment** - Who/what could be affected
- **Potential fix** - If you have ideas on how to fix it

### Response Timeline

- **Initial Response**: Within 48 hours
- **Status Update**: Within 7 days
- **Fix Timeline**: Depends on severity:
  - Critical: 1-7 days
  - High: 7-14 days
  - Medium: 14-30 days
  - Low: 30-90 days

### Disclosure Policy

- We will acknowledge your report within 48 hours
- We will confirm the vulnerability and determine affected versions
- We will develop and test a fix
- We will release a security patch and CVE if applicable
- We will publicly disclose the vulnerability after a fix is available

**Coordinated Disclosure**: We ask that you do not publicly disclose the vulnerability until we have released a fix. We will credit you in the security advisory unless you prefer to remain anonymous.

## Security Best Practices

### For Users

When deploying AI Gateway, follow these security guidelines:

#### API Keys and Secrets

- **Never commit `.env` files** to version control
- **Use environment variables** for all sensitive configuration
- **Rotate API keys** regularly (every 90 days recommended)
- **Use separate keys** for development and production
- **Restrict API key permissions** to minimum required

#### Network Security

- **Run on localhost only** by default (`127.0.0.1`)
- **Use HTTPS** if exposing externally (reverse proxy recommended)
- **Implement authentication** if accessible from network
- **Use firewall rules** to restrict access
- **Enable rate limiting** to prevent abuse

#### Database Security

- **Secure database files** with appropriate file permissions
- **Backup regularly** but keep backups secure
- **Sanitize logs** before sharing (no API keys, sensitive data)
- **Use encryption at rest** for production deployments

#### Dependency Security

- **Keep dependencies updated**: `pip install --upgrade -r requirements.txt`
- **Monitor for vulnerabilities**: Use GitHub Dependabot alerts
- **Review dependency changes** before updating
- **Pin versions** in production: `pip freeze > requirements.lock`

#### Provider-Specific Security

**Ollama (Local):**
- Runs on local network by default
- Ensure proper network isolation
- Keep Ollama updated

**OpenAI/Anthropic:**
- Never log full API responses (may contain sensitive data)
- Use minimum required API permissions
- Monitor usage for anomalies
- Implement spending limits

### For Contributors

If you're contributing code:

#### Code Review Checklist

- [ ] No hardcoded secrets, API keys, or credentials
- [ ] Input validation on all user-provided data
- [ ] Proper error handling (no information leakage)
- [ ] Secure default configurations
- [ ] Dependencies are up-to-date and vulnerability-free
- [ ] Sensitive data is properly sanitized in logs
- [ ] Authentication/authorization checks where needed

#### Common Vulnerabilities to Avoid

**Injection Attacks:**
- Always validate and sanitize user input
- Use parameterized queries for database access
- Avoid `eval()` or `exec()` on user input

**Information Disclosure:**
- Don't expose stack traces in production
- Sanitize error messages
- Don't log sensitive data (API keys, tokens, PII)

**Insecure Dependencies:**
- Run `pip-audit` before submitting PRs
- Keep dependencies minimal
- Review dependency changes in PRs

## Security Features

### Current Protections

- ✅ Environment-based secrets management
- ✅ Input validation on API requests
- ✅ Structured logging with sensitive data redaction
- ✅ Localhost-only default binding
- ✅ No external network access by default
- ✅ Type-safe request/response handling (Pydantic)

### Planned Security Features

- [ ] API authentication (JWT/API keys)
- [ ] Rate limiting per client
- [ ] Request signing/verification
- [ ] Audit logging
- [ ] HTTPS support (built-in)
- [ ] Role-based access control (RBAC)

## Known Limitations

### Current Design Constraints

1. **No Built-in Authentication**: Currently designed for localhost use. If exposing externally, use a reverse proxy with authentication.

2. **API Key Storage**: API keys are stored in `.env` files. For production, consider using a secrets manager (e.g., HashiCorp Vault, AWS Secrets Manager).

3. **No Request Signing**: Requests are not cryptographically signed. Use HTTPS for network protection.

4. **Database Encryption**: SQLite database is not encrypted by default. Use OS-level encryption for sensitive data.

## Compliance

### Data Handling

- **API Keys**: Stored in environment variables only
- **Request Logs**: Contain prompts/responses - may include sensitive data
- **Metrics Database**: Contains usage stats, costs, model names
- **No PII**: We don't collect personally identifiable information

### Provider Data Policies

When using AI Gateway, you're subject to the data policies of the providers you use:

- **OpenAI**: https://openai.com/policies/privacy-policy
- **Anthropic**: https://www.anthropic.com/privacy
- **Ollama**: Local processing, no data sent externally

## Security Audits

### Internal Audits

- **Last Audit**: 2026-02-12
- **Findings**: See SECURITY-AUDIT.md for detailed report
- **Status**: All findings resolved

### External Audits

- No external security audits conducted yet
- Contributions welcome for security review

## Acknowledgments

We appreciate the security community's efforts in responsible disclosure. Contributors who report valid security issues will be acknowledged in:

- Security advisory
- CHANGELOG.md
- Project documentation

## Questions?

For non-security questions about this policy:
- Open a GitHub Discussion
- File a GitHub Issue (for policy improvements)

For security concerns, follow the reporting process above.

---

**Last Updated**: 2026-02-12  
**Policy Version**: 1.0
