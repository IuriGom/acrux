# Security — Key Facts, Concepts, and Essentials

This file is a compact reference of the foundational knowledge an AI coding assistant needs to reason about, write, review, and harden secure software.

---

## 1. Core Security Mindset

- **Confidentiality, Integrity, Availability (CIA)** are the traditional security goals.
- **Authentication (AuthN)** = proving identity. **Authorization (AuthZ)** = deciding what an identity may do.
- **Defense in depth** means no single control is the only control; layers include input validation, access control, encryption, logging, monitoring, and incident response.
- **Least privilege** grants the minimum permissions needed for the shortest time.
- **Fail securely**: when a control fails, default to deny, not allow.
- **Trust but verify**: validate every request, assume the client is malicious.
- **Security is a process, not a product**: it must be designed, tested, operated, and updated continuously.
- **Never rely on security through obscurity**: secrets and design details will be discovered.

---

## 2. Secure Software Development Lifecycle (Secure SDLC)

Key frameworks:

- **NIST SP 800-218 Secure Software Development Framework (SSDF)** — four groups:
  - Prepare the Organization
  - Protect the Software
  - Produce Well-Secured Software
  - Respond to Vulnerabilities
- **OWASP Software Assurance Maturity Model (SAMM)** — governance, design, implementation, verification, operations.
- **Microsoft Security Development Lifecycle (SDL)** — threat modeling, static analysis, dynamic analysis, secure deployment.
- **BSIMM** — measures real activities performed by organizations.

Typical secure SDLC phases:

1. Requirements: define security and privacy requirements, compliance scope.
2. Design: threat model, define trust boundaries, choose controls.
3. Implementation: follow coding standards, use reviewed libraries, avoid dangerous functions.
4. Verification: SAST, DAST, fuzzing, dependency scanning, penetration testing.
5. Release: harden configuration, manage secrets, document security assumptions.
6. Operations: patching, monitoring, incident response, vulnerability disclosure.

---

## 3. Threat Modeling

- **STRIDE** categories:
  - **Spoofing** — impersonation
  - **Tampering** — unauthorized modification
  - **Repudiation** — denial of performing an action
  - **Information Disclosure** — exposure of data
  - **Denial of Service** — availability impact
  - **Elevation of Privilege** — gaining unauthorized capabilities
- **DREAD** scoring (legacy): Damage, Reproducibility, Exploitability, Affected users, Discoverability.
- Common tools: Microsoft Threat Modeling Tool, OWASP Threat Dragon, pytm.
- Outputs: data-flow diagrams, threat list, mitigations, acceptance decisions.

---

## 4. OWASP Top 10:2025

The OWASP Top 10 is a consensus list of the most critical web application security risks.

| ID | Risk | Core Idea |
|----|------|-----------|
| A01:2025 | Broken Access Control | Missing or bypassable authorization checks |
| A02:2025 | Security Misconfiguration | Unsafe defaults, verbose errors, unnecessary features enabled |
| A03:2025 | Software Supply Chain Failures | Vulnerable dependencies, compromised build or delivery pipeline |
| A04:2025 | Cryptographic Failures | Weak, missing, or misused encryption |
| A05:2025 | Injection | Untrusted input interpreted as code/command/query |
| A06:2025 | Insecure Design | Missing security controls at design time |
| A07:2025 | Authentication Failures | Weak AuthN, credential stuffing, session issues |
| A08:2025 | Software or Data Integrity Failures | Insecure deserialization, untrusted updates |
| A09:2025 | Security Logging and Alerting Failures | Insufficient detection/response evidence |
| A10:2025 | Mishandling of Exceptional Conditions | Crashes, stack traces, logic errors under edge cases |

---

## 5. CWE Top 25 (2024)

The MITRE CWE Top 25 lists the most dangerous software weaknesses. Top entries include:

- CWE-787: Out-of-bounds Write
- CWE-79: Cross-site Scripting (XSS)
- CWE-89: SQL Injection
- CWE-416: Use After Free
- CWE-78: OS Command Injection
- CWE-20: Improper Input Validation
- CWE-125: Out-of-bounds Read
- CWE-22: Path Traversal
- CWE-352: Cross-Site Request Forgery
- CWE-434: Unrestricted Upload of File with Dangerous Type
- CWE-862: Missing Authorization
- CWE-476: NULL Pointer Dereference
- CWE-287: Improper Authentication
- CWE-190: Integer Overflow or Wraparound
- CWE-502: Deserialization of Untrusted Data
- CWE-77: Command Injection
- CWE-119: Improper Restriction of Operations within the Bounds of a Memory Buffer
- CWE-798: Use of Hard-coded Credentials
- CWE-918: Server-Side Request Forgery (SSRF)
- CWE-306: Missing Authentication for Critical Function
- CWE-362: Race Condition
- CWE-269: Improper Privilege Management
- CWE-94: Improper Control of Generation of Code
- CWE-863: Incorrect Authorization
- CWE-276: Incorrect Default Permissions

Use the CWE as a taxonomy for root-cause remediation, code review checklists, and scanner rule mapping.

---

## 6. Input Validation

- Validate **as early as possible** and **on the server side**.
- Use **allowlists** (define what is allowed) rather than **denylists**.
- Apply both **syntactic** (format) and **semantic** (business meaning) validation.
- Reject invalid input; do not silently truncate or coerce unless the transformation is safe.
- Validate data from all untrusted sources: web clients, APIs, files, partner feeds, databases restored from backups.
- Use type systems, JSON Schema, XML Schema, strong regular expressions, and built-in validators.
- Be aware of **ReDoS** (Regular expression Denial of Service); avoid nested quantifiers and catastrophic backtracking.
- Normalize Unicode (NFC) and canonicalize paths/URLs before validation.

Example Python allowlist validation:

```python
import re
from pydantic import BaseModel, Field, validator

class SignupRequest(BaseModel):
    username: str = Field(..., min_length=3, max_length=32)
    age: int = Field(..., ge=13, le=120)

    @validator('username')
    def username_alphanumeric(cls, v):
        if not re.fullmatch(r'[a-zA-Z0-9_]+', v):
            raise ValueError('username must be alphanumeric')
        return v
```

---

## 7. Output Encoding & Context

Output encoding prevents injection attacks by converting data into a safe form for the target context.

| Context | Encoding | Example |
|---------|----------|---------|
| HTML body | HTML entity encode | `<` → `&lt;` |
| HTML attribute | Attribute encode | `"` → `&quot;` |
| JavaScript | JS hex/unicode encode | `'` → `\x27` |
| CSS | CSS hex encode | `<` → `\3c` |
| URL | percent encode | space → `%20` |
| SQL | parameterized queries | never concatenate |
| OS shell | avoid shell; use execve-style APIs |
| LDAP/XPath/XML | context-specific encoding |

Use framework auto-escaping (e.g., Jinja2, React) but understand its limits.

---

## 8. Authentication Essentials

- Use strong, slow password hashing: **Argon2id**, **scrypt**, or **bcrypt**; fallback **PBKDF2-HMAC-SHA256** for FIPS.
- Store passwords as **irreversible hashes** with unique salts. Never encrypt or store plaintext passwords.
- Enforce MFA wherever feasible; it stops the vast majority of account-compromise attacks.
- NIST SP 800-63B recommends minimum 8 characters with MFA, 15 without; allow long passphrases (≥64 characters).
- Do not force periodic password rotation unless compromise is suspected.
- Use generic error messages for failed login, password reset, and registration to prevent user enumeration.
- Implement rate limiting, account lockout, CAPTCHA, and breach-password blocklists as defense in depth.
- Transmit credentials only over TLS.
- Consider passwordless/FIDO2/WebAuthn/Passkeys for high-security applications.

Password hashing example (Python with `argon2-cffi`):

```python
from argon2 import PasswordHasher

ph = PasswordHasher(time_cost=2, memory_cost=65536, parallelism=1, hash_len=32, salt_len=16)
hash_value = ph.hash("user password")
try:
    ph.verify(hash_value, "user password")
except Exception:
    # reject
    pass
```

---

## 9. Session Management

- Generate session IDs with a **CSPRNG** and ensure sufficient length (≥128 bits).
- Store session state server-side; bind tokens to the user agent/IP fingerprint only if it does not harm UX or privacy.
- Set cookies with `HttpOnly`, `Secure`, `SameSite=Strict` or `Lax`, and a short `Max-Age`/`Expires`.
- Regenerate session ID on privilege level change (login, password change, MFA step-up).
- Invalidate sessions on logout and on password change from any device.
- Avoid storing sensitive data in JWTs unless encrypted; JWTs are signed, not confidential by default.

Cookie example (HTTP header):

```http
Set-Cookie: sessionid=<token>; HttpOnly; Secure; SameSite=Strict; Path=/; Max-Age=3600
```

---

## 10. Authorization Models

- **RBAC (Role-Based Access Control)**: permissions assigned to roles, roles assigned to users. Good for coarse-grained access.
- **ABAC (Attribute-Based Access Control)**: decisions based on subject/object/environment attributes and policies. Good for fine-grained, dynamic rules.
- **ReBAC (Relationship-Based Access Control)**: access based on relationships between resources (e.g., owner, editor). Popularized by Google Zanzibar.
- **PBAC (Policy-Based Access Control)**: explicit policies, often using XACML or OPA/Rego.
- Enforce **deny by default**.
- Check authorization **on every request** for the specific resource and action.
- Never rely on client-side checks.
- Indirect object references help mitigate IDOR but are not a substitute for authorization checks.

---

## 11. Cryptography Fundamentals

### Hashing vs Encryption

- **Hashing** is one-way; used for passwords and integrity checks.
- **Encryption** is reversible; used for confidentiality of data at rest or in transit.
- **MAC/HMAC** provides integrity + authenticity with a secret key.
- **Digital signatures** provide integrity + authenticity + non-repudiation using asymmetric keys.

### Symmetric Encryption

- Prefer **AES-256-GCM** or **AES-128-GCM** (authenticated encryption with associated data — AEAD).
- Never use **ECB** mode except in very specific, non-security contexts.
- If only CTR/CBC is available, use **Encrypt-then-MAC** with a separate key.
- Generate IVs/nonces with a CSPRNG; for GCM, never reuse a nonce with the same key.
- For file/stream encryption, consider **ChaCha20-Poly1305**.

### Asymmetric Encryption

- Prefer **ECC** with Curve25519 (X25519/X448) or P-256/P-384 for compatibility.
- RSA keys should be at least 2048 bits (3072+ for long-term data).
- Use **OAEP** padding for RSA encryption, **PSS** for RSA signatures.
- Use established libraries: OpenSSL, libsodium, Google Tink, pyca/cryptography.

### Key Management

- Generate keys with a CSPRNG.
- Store keys in a KMS/HSM/vault, never hard-coded or in version control.
- Use envelope encryption: a data encryption key (DEK) encrypts data, a key encryption key (KEK) encrypts the DEK.
- Rotate keys on compromise, after cryptoperiod, or after large data volumes; have tested rotation runbooks.
- Separate keys from encrypted data where possible.

### Randomness

- Use a CSPRNG for all security-critical values: keys, nonces, session IDs, tokens, salts.
- Examples by language:
  - Python: `secrets` module
  - Node.js: `crypto.randomBytes`, `crypto.randomInt`
  - Go: `crypto/rand`
  - Java: `SecureRandom`
  - C: `getrandom(2)` or `arc4random` (not RC4)
- Avoid `Math.random`, `java.util.Random`, `rand()`, `mt_rand()`, `random.random()` for security.

Python cryptography example (AES-256-GCM):

```python
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
import secrets

key = AESGCM.generate_key(bit_length=256)
aesgcm = AESGCM(key)
nonce = secrets.token_bytes(12)
ciphertext = aesgcm.encrypt(nonce, b"secret message", associated_data=b"context")
plaintext = aesgcm.decrypt(nonce, ciphertext, associated_data=b"context")
```

---

## 12. Transport Layer Security (TLS)

- Use **TLS 1.3**; support **TLS 1.2** only for compatibility. Disable SSLv2, SSLv3, TLS 1.0, TLS 1.1.
- Use AEAD cipher suites: AES-GCM or ChaCha20-Poly1305.
- Disable weak ciphers: NULL, EXPORT, RC4, DES, 3DES, CBC-only suites, RSA key transport without forward secrecy.
- Use strong Diffie-Hellman groups: `x25519`, `prime256v1`, `secp384r1`, `ffdhe2048+`.
- Disable TLS compression to prevent CRIME/BREACH-style attacks.
- Use valid certificates with SHA-256, SAN matching the hostname, and strong private keys (RSA ≥2048, ECC ≥256).
- Enable HSTS with `includeSubDomains` and preload after validation.
- Use secure cookies (`Secure`, `HttpOnly`, `SameSite`).
- For service meshes or high-value APIs, consider mutual TLS (mTLS).

Example nginx TLS snippet:

```nginx
server {
    listen 443 ssl http2;
    ssl_certificate     /etc/nginx/ssl/cert.pem;
    ssl_certificate_key /etc/nginx/ssl/key.pem;
    ssl_protocols       TLSv1.2 TLSv1.3;
    ssl_ciphers         ECDHE-ECDSA-AES128-GCM-SHA256:ECDHE-RSA-AES128-GCM-SHA256:ECDHE-ECDSA-AES256-GCM-SHA384:ECDHE-RSA-AES256-GCM-SHA384:ECDHE-ECDSA-CHACHA20-POLY1305:ECDHE-RSA-CHACHA20-POLY1305:DHE-RSA-AES128-GCM-SHA256:DHE-RSA-AES256-GCM-SHA384;
    ssl_prefer_server_ciphers off;
    ssl_session_cache shared:SSL:10m;
    ssl_session_timeout 1d;
    add_header Strict-Transport-Security "max-age=63072000; includeSubDomains; preload" always;
}
```

---

## 13. Web Security Headers

| Header | Purpose |
|--------|---------|
| `Content-Security-Policy` | Restricts sources for scripts, styles, frames, forms; mitigates XSS and clickjacking |
| `Strict-Transport-Security` | Enforces HTTPS (HSTS) |
| `X-Content-Type-Options: nosniff` | Prevents MIME sniffing |
| `X-Frame-Options` | Legacy frame restriction; CSP `frame-ancestors` preferred |
| `Referrer-Policy` | Controls referrer leakage |
| `Permissions-Policy` | Restricts browser features (camera, geolocation, etc.) |
| `Cross-Origin-Resource-Policy` | Controls cross-origin resource loading |
| `Cross-Origin-Opener-Policy` | Isolates browsing contexts |
| `Cross-Origin-Embedder-Policy` | Requires CORP for embedded resources |
| `Cache-Control: no-store` | Prevents caching of sensitive responses |
| `Clear-Site-Data` | Clears cache/cookies/storage on logout |

CSP strict policy example:

```http
Content-Security-Policy: default-src 'self'; script-src 'nonce-{RANDOM}' 'strict-dynamic'; object-src 'none'; base-uri 'none'; frame-ancestors 'self'; form-action 'self';
```

---

## 14. Common Web Vulnerabilities

### Injection

- Occurs when untrusted data is sent to an interpreter as part of a command or query.
- Types: SQL, NoSQL, OS command, LDAP, XPath, Expression Language (EL), template injection.
- Prevention: parameterized queries/prepared statements, context-aware escaping, avoid dynamic evaluation, use ORMs safely.

SQL injection example (Python with `sqlite3`):

```python
# VULNERABLE
# cursor.execute(f"SELECT * FROM users WHERE name = '{name}'")

# SAFE
cursor.execute("SELECT * FROM users WHERE name = ?", (name,))
```

### Cross-Site Scripting (XSS)

- Stored, reflected, and DOM-based XSS inject malicious scripts into a page.
- Prevention: output encoding, CSP, framework auto-escaping, sanitize HTML with a library (DOMPurify, bleach), avoid `innerHTML`, avoid `eval`, validate input.

### Cross-Site Request Forgery (CSRF)

- Forces a victim's browser to perform an unwanted action on an authenticated site.
- Prevention: CSRF tokens (state-changing requests), `SameSite` cookies, re-authentication for sensitive actions, custom headers for APIs.

### Server-Side Request Forgery (SSRF)

- Server makes requests to attacker-controlled or internal destinations.
- Prevention: allowlist destinations, disable unnecessary URL schemes, enforce network segmentation, use a separate egress proxy, validate and resolve hostnames before request.

### Insecure Deserialization

- Untrusted data is deserialized into objects, leading to RCE or logic bypass.
- Prevention: avoid deserializing untrusted data; use JSON with schema validation; sign data with HMAC if needed; use language-safe formats; keep deserialization libraries patched.

### XML External Entities (XXE)

- XML parsers process external entities, leading to file disclosure, SSRF, DoS.
- Prevention: disable DTDs/external entities, use JSON, keep parsers patched.

---

## 15. API Security

- Authenticate and authorize every endpoint, including internal ones.
- Use OAuth 2.1 / OIDC for delegated access; prefer opaque access tokens or short-lived JWTs.
- Validate and strictly type all inputs (OpenAPI schemas help).
- Implement rate limiting, throttling, and quotas.
- Use API gateways for TLS termination, auth, WAF, logging, rate limiting.
- Do not expose internal identifiers directly (use UUIDs or indirect references), but still enforce authorization.
- Version APIs and avoid breaking security assumptions.
- Return minimal error details; use generic messages.
- Protect GraphQL: depth limiting, complexity analysis, cost analysis, allowlist queries.

---

## 16. Secrets Management

- Never hard-code secrets, keys, or credentials.
- Never commit secrets to version control; use `.gitignore`, pre-commit hooks, and secrets scanning (GitHub secret scanning, TruffleHog, Gitleaks).
- Store runtime secrets in a dedicated vault (HashiCorp Vault, AWS Secrets Manager, Azure Key Vault, Google Secret Manager, Doppler).
- Inject secrets via environment variables or mounted files only at runtime; rotate them automatically.
- Use short-lived credentials and dynamic secrets where possible.
- Separate secrets by environment and least privilege.

Example secure env handling (Python):

```python
import os
from pathlib import Path

# Prefer reading from a file injected by the orchestrator
def get_secret(name: str) -> str:
    path = os.environ.get(f"{name}_FILE")
    if path and Path(path).exists():
        return Path(path).read_text().strip()
    value = os.environ.get(name)
    if not value:
        raise RuntimeError(f"Missing secret {name}")
    return value
```

---

## 17. Container and Cloud Security

- Use minimal base images (distroless, Alpine, scratch) and keep them updated.
- Run containers as non-root, with read-only root filesystems and dropped capabilities.
- Scan images for CVEs (Trivy, Snyk, Grype, Clair).
- Use private registries, sign images (cosign, Notary), verify signatures in CI/CD and at runtime.
- Do not bake secrets into images; pass them at runtime.
- Network segmentation: default-deny ingress/egress, service mesh mTLS.
- Use pod security standards, seccomp/AppArmor/SELinux profiles.
- Cloud: enforce IAM least privilege, enable audit logs, encrypt data at rest and in transit, use KMS, enable guardrails (SCPs, OPA/Gatekeeper).

Example Dockerfile hardening:

```dockerfile
FROM python:3.12-slim
RUN apt-get update && apt-get upgrade -y && rm -rf /var/lib/apt/lists/*
RUN groupadd -r app && useradd -r -g app app
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
USER app
EXPOSE 8000
CMD ["python", "-m", "uvicorn", "main:app", "--host", "0.0.0.0"]
```

---

## 18. Dependency and Supply Chain Security

- Maintain an accurate software bill of materials (SBOM).
- Scan dependencies for known CVEs (Snyk, OWASP Dependency-Check, pip-audit, npm audit, cargo audit).
- Pin dependency versions and verify checksums/signatures.
- Use private mirrors and review transitive dependencies.
- Watch for dependency confusion: use scoped/internal registry names, `.npmrc`, `PIP_INDEX_URL`.
- Sign commits, sign artifacts, verify CI/CD pipeline integrity.
- Apply updates promptly for high/critical vulnerabilities; have a patching SLA.

---

## 19. Logging, Monitoring, and Incident Response

- Log security-relevant events: authentication success/failure, authorization failures, password changes, account lockouts, sensitive data access, config changes, errors.
- Do not log secrets, PII, session tokens, or passwords.
- Use structured logs (JSON) with synchronized timestamps.
- Forward logs to a centralized SIEM; set up alerts and playbooks.
- Implement rate-based detection for brute force, credential stuffing, and scanning.
- Have an incident response plan: preparation, identification, containment, eradication, recovery, lessons learned.
- Practice tabletop exercises and maintain contact lists.

---

## 20. Vulnerability and Risk Scoring

- **CVE** = Common Vulnerabilities and Exposures identifier.
- **CWE** = Common Weakness Enumeration (root cause category).
- **CVSS** = Common Vulnerability Scoring System (severity, not risk).
- **CISA KEV** = Known Exploited Vulnerabilities catalog; prioritize these.
- **EPSS** = Exploit Prediction Scoring System; probabilistic likelihood of exploitation.
- Risk = Threat × Vulnerability × Impact. Use threat intel, asset value, and exploitability to prioritize remediation.

---

## 21. Privacy and Compliance Basics

- **PII** = Personally Identifiable Information; minimize collection, use, retention.
- **GDPR** (EU): lawful basis, data minimization, purpose limitation, storage limitation, security, breach notification (72h), data subject rights.
- **CCPA/CPRA** (California): consumer rights, opt-out of sale/sharing.
- **PCI DSS**: protect cardholder data; avoid storing PAN/CVV when possible.
- **HIPAA**: PHI protections for healthcare (US).
- **SOC 2**: trust services criteria (security, availability, confidentiality, processing integrity, privacy).
- **ISO/IEC 27001**: information security management system standard.
- Pseudonymize/anonymize data; use tokenization for sensitive values.

---

## 22. Language-Specific Secure Coding Notes

### Python

- Use `secrets` for tokens, `hashlib` for hashing, `argon2-cffi` or `bcrypt` for passwords, `cryptography` for encryption.
- Avoid `pickle` for untrusted data; use JSON, msgpack, or protobuf.
- Use parameterized queries; avoid f-strings or `%` formatting for SQL.
- Be cautious with `eval`, `exec`, `ast.literal_eval` only for literals.
- Validate file paths with `pathlib` and restrict to intended directories.
- Use `defusedxml` for XML parsing.

### JavaScript / Node.js

- Use `crypto` for randomness and hashing; never `Math.random()`.
- Avoid `eval`, `new Function`, and dynamic `require` with user input.
- Use parameterized queries with `pg`, `mysql2`, or an ORM.
- Validate input with `zod`, `joi`, or JSON Schema.
- Set secure cookie attributes; use helmet for security headers.
- Keep dependencies updated; use lockfiles and audit.

### Go

- Use `crypto/rand`, `crypto/subtle` for constant-time comparison.
- Avoid `text/template`/`html/template` for untrusted templates if not needed; auto-escapes HTML.
- Use prepared statements with `database/sql`.
- Be careful with `unsafe`, `cgo`, and reflection.
- Race detector: `go run -race`.

### C / C++

- Avoid unsafe functions: `strcpy`, `strcat`, `sprintf`, `gets`, `scanf` with `%s`.
- Prefer bounded alternatives: `strncpy`, `strncat`, `snprintf`, `fgets`.
- Use modern C++ (`std::string`, `std::vector`, smart pointers) to avoid manual memory management.
- Enable stack canaries, ASLR, DEP/NX, FORTIFY_SOURCE, `_FORTIFY_SOURCE=2`.
- Use sanitizers during testing: AddressSanitizer, MemorySanitizer, UBSan.
- Be aware of integer overflow, format strings, use-after-free, double-free.

### Bash / Shell

- Always quote variables: `"$var"`.
- Avoid `eval` with untrusted input.
- Use `printf '%q'` for safe quoting.
- Prefer `exec` arrays or `xargs -0` for passing arguments.
- Validate inputs with allowlists.

---

## 23. Security Tools Categories

- **SAST** (Static Application Security Testing): SonarQube, Semgrep, Checkmarx, CodeQL, Bandit.
- **DAST** (Dynamic Application Security Testing): OWASP ZAP, Burp Suite, Nikto.
- **IAST** (Interactive): instrumentation-based testing.
- **SCA** (Software Composition Analysis): Snyk, OWASP Dependency-Check, Mend, FOSSA.
- **Secrets scanning**: TruffleHog, Gitleaks, GitHub secret scanning.
- **Container scanning**: Trivy, Grype, Snyk Container.
- **Infrastructure scanning**: Checkov, tfsec, CloudFormation Guard.
- **Fuzzing**: AFL++, libFuzzer, cargo-fuzz, Jazzer.

---

## 24. Quick Reference Checklist

- [ ] Threat model the feature before coding.
- [ ] Validate all untrusted input server-side.
- [ ] Use parameterized queries / prepared statements.
- [ ] Encode output for the correct context.
- [ ] Enforce authentication and authorization on every request.
- [ ] Hash passwords with Argon2id / bcrypt / scrypt.
- [ ] Use TLS 1.2+ with strong cipher suites and HSTS.
- [ ] Set a strict Content-Security-Policy.
- [ ] Use `HttpOnly` `Secure` `SameSite` cookies.
- [ ] Protect against CSRF on state-changing operations.
- [ ] Avoid deserialization of untrusted data.
- [ ] Keep dependencies patched and scanned.
- [ ] Store secrets in a vault, never in source code.
- [ ] Log security events, not secrets or PII.
- [ ] Test with SAST, DAST, dependency scanning, and fuzzing.


---

## 25. Authentication Protocols and Standards

### OAuth 2.1 / OpenID Connect (OIDC)

- **OAuth 2.1** consolidates OAuth 2.0 + security best practices. Use it for delegated API authorization, not authentication.
- **OpenID Connect** is an identity layer on top of OAuth 2.1; use it for authentication/SSO.
- Key OIDC flows:
  - **Authorization Code Flow** with PKCE is the recommended flow for public and confidential clients.
  - **Client Credentials** for machine-to-machine.
  - **Device Authorization** for input-constrained devices.
- Validate ID Tokens: signature via JWKS, issuer (`iss`), audience (`aud`), expiration (`exp`), not-before (`nbf`).
- Store tokens securely: short-lived access tokens, refresh tokens with rotation, bind to DPoP or mTLS for high-value clients.

### SAML 2.0

- XML-based federation protocol common in enterprise SSO.
- Validate signatures, enforce strict schema parsing, use secure XML parsing to prevent XXE.
- Match `InResponseTo` and prevent signature wrapping attacks.

### FIDO2 / WebAuthn / Passkeys

- Public-key cryptography bound to the origin; phishing-resistant.
- Verify attestation and origin during registration; verify challenge signature during authentication.
- Passkeys may be synced across devices; consider backup/eligibility flags for high-assurance scenarios.

---

## 26. JWT Security Details

- JWT structure: `header.payload.signature` (Base64Url).
- Always validate the algorithm (`alg`) and reject `none`, `NULL`, or unexpected algorithms.
- Use asymmetric algorithms (RS256, ES256) when many services verify tokens; keep private key on issuer.
- Use short expiration (`exp`), issuer (`iss`), audience (`aud`), JWT ID (`jti`).
- Encrypt JWTs with AES-GCM if payload contains sensitive claims.
- Key denylist on `jti` + `iss`, never raw token hash (ECDSA malleability / parsing leniency).

JWT validation pseudo-code:

```python
import jwt
from jwt.exceptions import InvalidTokenError

# expected_algorithms must be a list/tuple, never None
payload = jwt.decode(
    token,
    public_key,
    algorithms=["RS256"],
    audience="my-api",
    issuer="https://auth.example.com"
)
```

---

## 27. HTTP Security Headers Reference

Full set of recommended headers:

```http
Strict-Transport-Security: max-age=63072000; includeSubDomains; preload
Content-Security-Policy: default-src 'none'; script-src 'self'; connect-src 'self'; img-src 'self'; style-src 'self'; frame-ancestors 'none'; form-action 'self'; base-uri 'none'
X-Content-Type-Options: nosniff
X-Frame-Options: DENY
Referrer-Policy: strict-origin-when-cross-origin
Permissions-Policy: camera=(), microphone=(), geolocation=()
Cross-Origin-Resource-Policy: same-origin
Cross-Origin-Opener-Policy: same-origin
Cross-Origin-Embedder-Policy: require-corp
Cache-Control: no-store
```

Use CSP nonces or hashes for inline scripts; avoid `'unsafe-inline'` and `'unsafe-eval'`.

---

## 28. SQL Injection Prevention

- **Always** use parameterized queries / prepared statements.
- Avoid string concatenation or interpolation for table/column names; if dynamic, use allowlists.
- Use ORMs but still validate inputs and avoid raw SQL with user data.
- Use least-privilege DB accounts: apps should not have `DROP` or `GRANT` rights.
- Enable query logging and WAF as secondary defenses, not primary.

Example in Go:

```go
rows, err := db.Query("SELECT id, name FROM users WHERE email = ?", email)
```

Example in Node.js (pg):

```js
const result = await pool.query('SELECT * FROM users WHERE email = $1', [email]);
```

---

## 29. XSS Prevention in Practice

- Use framework auto-escaping (React escapes HTML, Django templates auto-escape).
- For manual rendering, encode based on output context.
- Sanitize HTML using DOMPurify (browser) or bleach (Python) when allowing rich content.
- Avoid `innerHTML`, `document.write`, `eval`, `setTimeout`/`setInterval` with strings.
- Use Subresource Integrity (SRI) for third-party scripts.
- Set a strict CSP.

DOM example (safe):

```javascript
const el = document.createElement('div');
el.textContent = untrustedUserInput; // text, not HTML
container.appendChild(el);
```

---

## 30. CSRF Prevention

- Synchronizer token pattern: embed a cryptographically random token in forms and validate server-side.
- Set cookies with `SameSite=Lax` or `SameSite=Strict`.
- For APIs, require custom headers (`X-Requested-With`, `Content-Type: application/json`) that cross-origin requests cannot set without a preflight.
- Re-authenticate for high-value actions.

---

## 31. SSRF Prevention

- Parse URLs and validate host/IP against an allowlist.
- Resolve hostnames to IPs before connection; block private/reserved ranges.
- Disable unused URL schemes (`file://`, `gopher://`, `ftp://`).
- Use a separate egress proxy/DNS with logging.
- Avoid returning raw responses to users; handle errors generically.

Python safe URL fetch outline:

```python
from urllib.parse import urlparse
import ipaddress

ALLOWED_SCHEMES = {"https"}
BLOCKED_NETWORKS = {
    ipaddress.ip_network("10.0.0.0/8"),
    ipaddress.ip_network("172.16.0.0/12"),
    ipaddress.ip_network("192.168.0.0/16"),
    ipaddress.ip_network("127.0.0.0/8"),
    ipaddress.ip_network("169.254.0.0/16"),
    ipaddress.ip_network("::1/128"),
    ipaddress.ip_network("fc00::/7"),
    ipaddress.ip_network("fe80::/10"),
}

def is_safe_url(url: str) -> bool:
    parsed = urlparse(url)
    if parsed.scheme not in ALLOWED_SCHEMES:
        return False
    try:
        host = parsed.hostname
        if not host:
            return False
        ip = ipaddress.ip_address(host)
        return not any(ip in net for net in BLOCKED_NETWORKS)
    except ValueError:
        # hostname not an IP; allow only if in an allowlist or resolved safely
        return False
```

---

## 32. Deserialization Security

- Do not deserialize data from untrusted sources using language-native binary serializers.
- Safe alternatives: JSON with schema validation, protobuf with field allowlists, msgpack with type restrictions.
- If native serialization is required, sign with HMAC-SHA256 and verify before deserialization.
- Keep serialization libraries patched; many RCE chains exist (e.g., Java Commons Collections, Python pickle, Ruby Marshal, PHP unserialize).

---

## 33. File Upload Security

- Allowlist extensions and verify actual file type via magic bytes / rewriting library.
- Rename files on storage; do not use user-supplied filenames.
- Store uploads outside the web root or serve via a handler that sets `Content-Disposition: attachment`.
- Scan with antivirus / static analysis.
- Limit file size, compression bombs, and nested archives.
- Set correct `Content-Type`; prevent MIME sniffing with `X-Content-Type-Options: nosniff`.

---

## 34. Race Conditions and Concurrency

- **Time-of-check to time-of-use (TOCTOU)**: a property checked is changed before use.
- Use atomic operations, file locks, or database transactions with proper isolation.
- Be cautious with check-then-act patterns in payment, inventory, and authorization workflows.
- Use optimistic/pessimistic locking depending on contention.

---

## 35. Memory Safety

- Memory-safety vulnerabilities (buffer overflows, use-after-free, double-free) remain a top cause of exploitable bugs.
- Prefer memory-safe languages (Rust, Go, C#, Java, Python, JavaScript) for new code.
- For C/C++, use safe subsets, static analyzers, sanitizers, and fuzzing.
- Enable exploit mitigations: ASLR, DEP/NX, stack canaries, Control-Flow Integrity (CFI), PAC/BTI.

---

## 36. Zero Trust Principles

- Never trust, always verify.
- Authenticate and authorize every access request, regardless of network location.
- Use least-privilege access.
- Assume breach: segment networks, monitor continuously, minimize blast radius.
- Apply mTLS and strong identity for service-to-service communication.

---

## 37. Common Compliance Controls

- **Encryption at rest and in transit**.
- **Access control** with role reviews and offboarding.
- **Logging and monitoring** of admin actions and sensitive access.
- **Vulnerability management** with SLAs.
- **Incident response plan** with testing.
- **Data retention and disposal** policies.
- **Third-party risk management** and vendor security reviews.
- **Security awareness training** and phishing simulations.

---

## 38. Incident Response Phases

1. **Preparation**: tools, contacts, runbooks, logging.
2. **Identification**: detect and confirm an incident.
3. **Containment**: limit impact (short-term and long-term).
4. **Eradication**: remove root cause.
5. **Recovery**: restore systems, verify integrity.
6. **Lessons Learned**: post-mortem, update controls.

---

## 39. Key Security APIs by Language

### Python

- `secrets.token_urlsafe`, `secrets.token_hex`, `secrets.randbits`
- `hashlib.scrypt`, `hashlib.pbkdf2_hmac`
- `hmac.compare_digest` for constant-time comparison
- `cryptography.hazmat.primitives` for AES-GCM, RSA, X25519
- `bcrypt` / `argon2-cffi` for password hashing
- `bleach.clean` for HTML sanitization
- `defusedxml` for safe XML parsing

### Node.js

- `crypto.randomBytes`, `crypto.randomInt`, `crypto.scrypt`, `crypto.pbkdf2`
- `crypto.createHmac`, `crypto.createCipheriv`
- `crypto.timingSafeEqual`
- `helmet` for security headers
- `jose` or `jsonwebtoken` for JWT handling

### Go

- `crypto/rand`
- `crypto/subtle.ConstantTimeCompare`
- `golang.org/x/crypto/bcrypt`, `argon2`
- `crypto/aes`, `crypto/cipher` for GCM
- `html/template` for auto-escaping

### Java

- `java.security.SecureRandom`
- `javax.crypto.Cipher` (AES/GCM/NoPadding)
- `java.security.MessageDigest`, `Mac`
- `org.springframework.security` for auth/authz
- OWASP Java Encoder for output encoding

### C/C++

- OpenSSL `EVP_*` API for crypto
- libsodium for high-level safe crypto
- `strncpy`, `strncat`, `snprintf` (bounded)
- AddressSanitizer, MemorySanitizer at test time

---

## 40. Notable Historical Vulnerabilities

- **Heartbleed** (OpenSSL): buffer over-read leaking memory.
- **Shellshock**: Bash environment variable command injection.
- **Log4Shell** (CVE-2021-44228): JNDI lookup RCE in Log4j.
- **Spring4Shell**: Spring Framework class loader manipulation.
- **MOVEit**, **GoAnywhere**, **Ivanti**: supply-chain and zero-day exploitation.
- These emphasize: keep dependencies patched, disable dangerous features, monitor, and plan for incident response.


---

## 41. Cryptography Deep Dive

### Symmetric Ciphers

Symmetric ciphers use one key for both encryption and decryption. Modern block ciphers include AES and ChaCha20.

- **AES** (Advanced Encryption Standard) supports 128, 192, and 256-bit keys. Use 128-bit or 256-bit keys depending on data sensitivity and compliance.
- **ChaCha20** is a stream cipher often used with **Poly1305** for authentication. It is preferred on devices without AES hardware acceleration and in TLS 1.3.

### Block Cipher Modes

| Mode | Properties | Recommendation |
|------|------------|----------------|
| ECB | No IV, deterministic, leaks patterns | Avoid for security |
| CBC | Requires IV, no authentication | Use with Encrypt-then-MAC; IV must be unpredictable |
| CTR | Stream-like, requires unique nonce | Secure if nonce never repeats; combine with MAC |
| GCM | Authenticated encryption (AEAD) | Preferred; never reuse nonce |
| CCM | Authenticated encryption | OK for constrained devices |
| ChaCha20-Poly1305 | AEAD stream cipher | Preferred on mobile/embedded |

### Asymmetric Cryptography

- **RSA**: widely supported. Use OAEP for encryption, PSS for signatures. Minimum 2048 bits; 3072 bits for long-term data.
- **Elliptic Curve Cryptography (ECC)**: smaller keys, faster operations. Curves: P-256 (NIST), P-384, Curve25519, Curve448, secp256k1.
- **Diffie-Hellman (DH)**: key exchange. Prefer ECDH with secure curves; for FFDH use RFC 7919 groups.
- **Post-quantum**: ML-KEM (Kyber), ML-DSA (Dilithium), SLH-DSA (SPHINCS+) are being standardized. Hybrid X25519MLKEM768 is in early deployment.

### Digital Signatures

- Provide integrity, authenticity, and non-repudiation.
- Algorithms: Ed25519, ECDSA, RSA-PSS.
- Never sign data without hashing first; use a secure hash (SHA-256 or SHA-384).

### Key Derivation Functions (KDFs)

- **Argon2id**: password hashing winner; memory-hard.
- **scrypt**: memory-hard; predecessor to Argon2.
- **bcrypt**: adaptive; widely available; 72-byte input limit.
- **PBKDF2**: NIST-approved; use ≥600k iterations with HMAC-SHA256.
- **HKDF**: for deriving keys from keying material.

### Certificates and PKI

- X.509 certificates bind a public key to an identity.
- Certificate fields: subject, issuer, validity dates, SAN, key usage, extended key usage, CRL distribution points, AIA.
- Chain validation: trust anchor → intermediate → leaf; check expiry, revocation, purpose, and hostname.
- Revocation: CRL (Certificate Revocation List), OCSP (Online Certificate Status Protocol), OCSP stapling.
- Certificate Transparency (CT): logs record issued certificates; clients can require SCTs.

Python certificate pinning example (not recommended for web; useful for thick clients):

```python
import ssl
import certifi

context = ssl.create_default_context(cafile=certifi.where())
context.minimum_version = ssl.TLSVersion.TLSv1_2
```

---

## 42. Network Security

### Firewalls and Segmentation

- Firewalls control traffic based on rules (stateless or stateful).
- Network segmentation limits lateral movement: DMZ, internal zones, micro-segmentation.
- Zero trust assumes no network segment is inherently safe.

### IDS/IPS

- **IDS** detects suspicious traffic; **IPS** blocks it.
- Signature-based vs. anomaly-based detection.
- Tools: Snort, Suricata, Zeek.

### VPNs

- Provide encrypted tunnels over untrusted networks.
- Protocols: WireGuard, OpenVPN, IPsec/IKEv2.
- Prefer modern, formally verified protocols where possible.

### DNS Security

- **DNSSEC** provides origin authentication and integrity for DNS records.
- **DoH** (DNS over HTTPS) and **DoT** (DNS over TLS) encrypt DNS queries.
- Beware of DNS rebinding and cache poisoning.

### DDoS Mitigation

- Rate limiting, CAPTCHA, WAF, CDN, anycast, upstream scrubbing.
- Architect for graceful degradation.

---

## 43. Operating System Security

### Linux Hardening

- Keep kernel and packages patched.
- Disable unused services and ports.
- Use SELinux or AppArmor.
- Apply seccomp filters.
- Configure auditd and rsyslog.
- Use `fail2ban` for brute-force protection.
- Set strong permissions; use `umask`.
- Disable root SSH login; use keys and MFA.

### Windows Hardening

- Apply Windows updates and Defender.
- Use Windows Firewall and Defender Credential Guard.
- Enable ASLR, DEP, Control Flow Guard.
- Use LAPS for local admin passwords.
- Restrict PowerShell execution policies.

### macOS Hardening

- Enable FileVault, Gatekeeper, SIP.
- Apply updates promptly.
- Use standard user accounts for daily work.

---

## 44. Cloud Security

### Shared Responsibility Model

- Cloud provider secures the cloud; customer secures what is in the cloud.
- Responsibilities vary by service model: IaaS, PaaS, SaaS.

### Identity and Access Management

- Use IAM roles, not long-term access keys.
- Enable MFA for privileged users.
- Apply least privilege and service control policies.
- Use federation/SAML/OIDC instead of local IAM users.

### Data Protection

- Encrypt data at rest (KMS-managed keys) and in transit (TLS).
- Use customer-managed keys (CMK) for regulatory requirements.
- Enable versioning and object lock for critical buckets.

### Monitoring

- Enable CloudTrail / Audit Logs / Activity Log.
- Forward logs to SIEM.
- Set up alerts for privileged actions, policy changes, and public resource exposure.

### Common Cloud Misconfigurations

- Public S3 buckets / storage containers.
- Overly permissive security groups (0.0.0.0/0).
- Unprotected snapshots and backups.
- Default credentials on managed databases.
- Exposed management ports (SSH/RDP) to the internet.

---

## 45. Mobile Security

- Store sensitive data in the OS keychain/Keystore; avoid plaintext in app storage.
- Use certificate pinning for API communication.
- Obfuscate code only as a minor deterrent; do not rely on it.
- Validate deep links and intents.
- Request minimum permissions.
- Protect against jailbreak/root detection bypasses for high-risk apps.
- Use biometric auth via platform APIs, not custom implementations.

---

## 46. WebSocket and Real-Time Security

- Authenticate during handshake; validate `Origin`.
- Authorize each channel/subscription.
- Rate-limit messages and payload sizes.
- Avoid echoing user input without encoding.
- Log connections and anomalous patterns.

---

## 47. GraphQL Security

- Limit query depth and complexity.
- Use persisted queries or allowlists.
- Implement cost analysis to reject expensive queries.
- Apply authorization at field/object resolvers.
- Disable introspection in production if not needed.
- Rate-limit and timeout queries.

---

## 48. Serverless and Function Security

- Keep functions small and single-purpose.
- Use least-privilege IAM roles per function.
- Do not store secrets in environment variables long-term; use vault integration.
- Validate all event inputs.
- Set concurrency limits to control cost/DoS.
- Monitor cold starts and execution logs.

---

## 49. Security Governance

- **Risk assessment**: identify assets, threats, vulnerabilities, likelihood, and impact.
- **Security policy**: management intent and rules.
- **Standards**: mandatory controls derived from policy.
- **Procedures**: step-by-step instructions.
- **Guidelines**: recommended practices.
- **Acceptable use policy**: defines acceptable behavior.
- **Incident response plan**: roles, communication, escalation.
- **Business continuity / disaster recovery**: RTO/RPO, backups, failover.

---

## 50. Red, Blue, and Purple Teams

- **Red team**: simulated adversaries; test detection/response.
- **Blue team**: defenders; monitor, detect, respond.
- **Purple team**: collaborative exercises to improve both.
- Use defined rules of engagement and scopes.

---

## 51. Penetration Testing Methodologies

- **OWASP Testing Guide**: web app testing methodology.
- **PTES** (Penetration Testing Execution Standard): pre-engagement, intelligence gathering, threat modeling, vulnerability analysis, exploitation, post-exploitation, reporting.
- **OSCP/PWK**: hands-on methodology.
- Always have written authorization before testing.

---

## 52. Reverse Engineering and Malware Basics

- Static analysis: disassembly (IDA Pro, Ghidra, Binary Ninja), strings, signatures.
- Dynamic analysis: debuggers, sandboxes, behavior monitoring.
- Malware types: viruses, worms, trojans, ransomware, spyware, rootkits, bots.
- Indicators of Compromise (IoCs): hashes, IPs, domains, file paths, registry keys.

---

## 53. Exploit Mitigations

- **ASLR** (Address Space Layout Randomization).
- **DEP/NX** (Data Execution Prevention / No-eXecute).
- **Stack canaries**.
- **Control-Flow Integrity (CFI)** / **CF-Guard**.
- **Pointer Authentication (PAC)** / **Branch Target Identification (BTI)** on ARM.
- **SafeSEH / SEHOP** on Windows.
- These raise the bar but do not eliminate bugs.

---

## 54. Code Signing and Reproducible Builds

- Sign binaries, packages, and container images.
- Store signing keys in HSM/KMS.
- Use timestamping to extend trust past certificate expiry.
- Reproducible builds allow independent verification that source matches binary.
- Binary transparency logs (e.g., Sigstore) improve supply-chain trust.

---

## 55. Security for AI/ML Systems

- Protect training data from poisoning and leakage.
- Validate model inputs to prevent adversarial examples and prompt injection.
- Avoid leaking sensitive training data through model outputs.
- Control access to models and inference endpoints.
- Monitor for model drift and anomalous queries.

---

## 56. Physical and Environmental Security

- Control physical access to data centers and devices.
- Use locks, badges, cameras, and environmental controls.
- Dispose of media securely (degaussing, shredding, cryptographic erasure).
- Protect against shoulder surfing and tailgating.

---

## 57. Social Engineering and Phishing

- Most breaches involve human factors.
- Train users to recognize phishing, pretexting, baiting, and quid pro quo.
- Use email authentication: SPF, DKIM, DMARC.
- Report and analyze phishing simulations.
- Implement callback verification for sensitive requests.

---

## 58. Email Security

- Enforce TLS for mail transport.
- Configure SPF, DKIM, DMARC with quarantine/reject policies.
- Use anti-phishing and anti-malware filtering.
- Disable auto-forwarding and external auto-replies where not needed.
- Encrypt sensitive email (S/MIME, PGP) when required.

---

## 59. Secure Boot and Hardware Roots of Trust

- **TPM** (Trusted Platform Module): secure key storage and attestation.
- **Secure Enclave** / **TEE** (Trusted Execution Environment): isolated execution.
- **Secure Boot**: verifies boot chain integrity.
- **Measured Boot**: records boot state for remote attestation.

---

## 60. Identity and Access Management Patterns

- Centralized identity store (LDAP, Active Directory, OIDC).
- Lifecycle management: provisioning, transfers, deprovisioning.
- Privileged Access Management (PAM): vaulting, session recording, just-in-time elevation.
- Access reviews: periodic certification of entitlements.
- Single Sign-On (SSO): improves usability and centralizes auth.

---

## 61. Data Classification

Typical levels:

- **Public**: no harm if disclosed.
- **Internal**: intended for employees.
- **Confidential**: significant harm if disclosed.
- **Restricted / Secret**: severe harm; regulated.

Classify data at creation and apply controls based on classification.

---

## 62. Secure Remote Access

- Use VPN or Zero Trust Network Access (ZTNA).
- Require MFA for all remote access.
- Use jump hosts or privileged access workstations for admin tasks.
- Monitor and record privileged sessions.
- Disable direct RDP/SSH exposure to the internet.

---

## 63. Patch Management

- Maintain an asset inventory.
- Prioritize patches by severity, exploitability, and asset criticality.
- Test patches in staging.
- Automate patching for OS and dependencies.
- Have rollback plans.
- Track mean time to patch (MTTP).

---

## 64. Vulnerability Disclosure

- Publish a `security.txt` file.
- Respond to reporters promptly and respectfully.
- Fix, test, and disclose within coordinated disclosure timelines.
- Offer safe harbor for good-faith research.
- Credit researchers unless they decline.

---

## 65. Metrics and KPIs for Security

- Vulnerability scan coverage and cadence.
- Mean time to remediate (MTTR) by severity.
- Percentage of code covered by SAST/DAST.
- Patch compliance rate.
- Phishing report rate and click rate.
- Number of open critical/high findings.
- Incident response time.
- Secrets scan hits.
- Percentage of users with MFA.

---

## 66. Security Culture

- Security is everyone's responsibility.
- Reward reporting of near-misses and potential issues.
- Avoid blame; focus on systemic fixes.
- Provide role-specific training.
- Embed security champions in development teams.

---

## 67. Common Security Certifications

- **CISSP**: broad information security management.
- **OSCP**: offensive security hands-on.
- **CEH**: ethical hacking concepts.
- **GSEC/GCIH/GWAPT**: SANS practical certifications.
- **CSSLP**: secure software development.
- **CISA/CISM**: audit and management.

---

## 68. Security Documentation

- Threat models
- Architecture decision records (ADRs) with security rationale
- Runbooks and playbooks
- Configuration baselines
- Incident response plans
- Data flow diagrams
- Asset inventory and ownership

---

## 69. Final Fact Summary

Security is a cross-cutting discipline. Strong software security combines:

- Secure design and threat modeling
- Defensive coding practices
- Strong cryptography and key management
- Robust authentication and authorization
- Safe handling of untrusted input and output
- Hardened infrastructure and dependencies
- Continuous testing and monitoring
- Prepared incident response
- A culture of security ownership

Keep these principles in mind for every feature, fix, and refactor.


---

## 70. OWASP Application Security Verification Standard (ASVS)

ASVS defines security requirements for applications at three levels:

- **Level 1**: opportunistic, minimum baseline for all apps.
- **Level 2**: standard for apps handling sensitive data.
- **Level 3**: high-value, high-assurance apps.

Chapters include architecture, authentication, session management, access control, validation, cryptography, error handling, data protection, communications, malicious code, business logic, files/resources, API, configuration.

Use ASVS as a checklist during design, implementation, and verification.

---

## 71. Language-Specific Secure Coding Details

### Python

- Use `pathlib.Path` for path operations and resolve before trust decisions.
- Avoid `pickle`, `yaml.load`, `marshal` on untrusted data.
- Use `defusedxml` or `lxml` with resolver/DTD disabled.
- Use `secrets` for tokens and `hmac.compare_digest` for comparisons.
- Use `sqlite3` parameterized queries or SQLAlchemy with bound parameters.
- Validate file uploads with `python-magic` for MIME detection.
- Use `bandit` for static analysis.

Example safe file path check:

```python
from pathlib import Path

def safe_open(base: Path, filename: str) -> Path:
    base = base.resolve()
    target = (base / filename).resolve()
    if not str(target).startswith(str(base)):
        raise ValueError("path traversal detected")
    return target
```

### JavaScript / TypeScript / Node.js

- Prefer `const` and avoid `eval` / `new Function`.
- Validate with `zod`, `joi`, or JSON Schema.
- Use `crypto` for tokens; never `Math.random()`.
- Use parameterized queries with `pg`, `mysql2`, or ORMs.
- Set `helmet()` defaults and override for strict CSP.
- Avoid `innerHTML`; use `textContent` or React's JSX escaping.
- Use `Object.create(null)` or `Map` to avoid prototype pollution.

Example prototype-pollution-safe merge:

```javascript
function safeMerge(target, source) {
  const safe = Object.create(null);
  for (const key of Object.keys(source)) {
    if (key === '__proto__' || key === 'constructor' || key === 'prototype') continue;
    safe[key] = source[key];
  }
  return Object.assign(target, safe);
}
```

### Go

- Use `crypto/rand` for security tokens.
- Use `database/sql` with `?` placeholders.
- Use `html/template` for auto-escaping HTML.
- Avoid `unsafe` and reflection on untrusted input.
- Use `crypto/subtle.ConstantTimeCompare`.
- Race detector: `go test -race`.

Example constant-time token check:

```go
import "crypto/subtle"

func checkToken(a, b []byte) bool {
    return subtle.ConstantTimeCompare(a, b) == 1
}
```

### Java

- Use `java.security.SecureRandom`.
- Use `PreparedStatement` for SQL.
- Use OWASP Java Encoder for output encoding.
- Avoid deserialization of untrusted data; use JSON or signed objects.
- Use `java.nio.file.Path` and normalize before trust.
- Configure `ObjectInputFilter` if deserialization is unavoidable.

### C#

- Use `RandomNumberGenerator` for tokens.
- Use parameterized queries with Dapper or Entity Framework.
- Use `HttpOnly`, `Secure`, `SameSite` cookie options.
- Avoid `BinaryFormatter`; use `JsonSerializer`.
- Use `StringComparison.Ordinal` for security checks.

### C / C++

- Avoid `strcpy`, `strcat`, `sprintf`, `gets`.
- Use `strncpy`, `strncat`, `snprintf`, `fgets` with bounds.
- Prefer C++ containers (`std::string`, `std::vector`) over raw buffers.
- Use smart pointers to avoid UAF/double-free.
- Enable AddressSanitizer and UBSan in tests.
- Be cautious with integer conversions and signed/unsigned mixing.

### Rust

- Ownership model prevents many memory-safety bugs.
- Use safe wrappers around `unsafe` blocks.
- Validate all inputs; avoid `unwrap()` on untrusted data.
- Use `ring` or `rustls` for cryptography and TLS.
- Use prepared statements with SQLx or Diesel.

### Bash

- Quote all variables: `"$var"`.
- Avoid `eval` and backticks.
- Use `printf '%q'` to safely quote strings.
- Validate inputs with allowlists.
- Prefer arrays for argument lists.

```bash
# Safe
read -r filename
[[ "$filename" =~ ^[a-zA-Z0-9_]+$ ]] || exit 1
cat "/var/data/$filename"
```

---

## 72. HTTP Security Headers in Detail

### Content-Security-Policy

Controls resource loading. Start strict and relax only as needed.

Example policy:

```http
Content-Security-Policy: default-src 'self'; script-src 'self' https://cdn.example.com; style-src 'self' 'unsafe-inline'; img-src 'self' data:; font-src 'self'; connect-src 'self'; frame-ancestors 'self'; form-action 'self'; base-uri 'self'
```

### Strict-Transport-Security

```http
Strict-Transport-Security: max-age=63072000; includeSubDomains; preload
```

### X-Content-Type-Options

```http
X-Content-Type-Options: nosniff
```

### Referrer-Policy

```http
Referrer-Policy: strict-origin-when-cross-origin
```

### Permissions-Policy

```http
Permissions-Policy: camera=(), microphone=(), geolocation=(), payment=()
```

### Cross-Origin headers

```http
Cross-Origin-Resource-Policy: same-origin
Cross-Origin-Opener-Policy: same-origin
Cross-Origin-Embedder-Policy: require-corp
```

---

## 73. Logging and Auditing Best Practices

- Log who, what, when, where, and outcome.
- Use UTC timestamps and synchronized clocks.
- Structure logs in JSON for parsing.
- Forward to a SIEM; set up alerts.
- Protect logs from tampering.
- Retain per policy and compliance requirements.
- Examples of events to log:
  - Authentication success/failure
  - Authorization failures
  - Password changes
  - MFA enrollment/disable
  - Account lockouts
  - Privileged actions
  - Configuration changes
  - Data exports
  - Errors and exceptions

---

## 74. Secrets Management Patterns

### Environment Variables (last resort)

- Use `_FILE` suffix to read from files when supported.
- Avoid logging env; some platforms expose `/proc/self/environ`.

### Vault Integration

- Authenticate using workload identity or approle.
- Fetch secrets at startup and cache in memory.
- Renew leases; handle rotation gracefully.

### Kubernetes

- Use `SealedSecrets`, `External Secrets Operator`, or cloud KMS integration.
- Mount secrets as files; avoid env vars for high-sensitivity values.
- Use RBAC to restrict secret access.

---

## 75. Container Security Controls

- Image signing and verification (cosign, Notary).
- Vulnerability scanning in CI and registry.
- Minimal base images (distroless, Alpine, scratch).
- Non-root execution.
- Read-only root filesystem.
- Dropped capabilities.
- Resource limits.
- Network policies.
- Runtime security (Falco, Tetragon).

---

## 76. Cloud-Native Security

### Kubernetes

- Pod Security Standards (Privileged, Baseline, Restricted).
- Network policies for segmentation.
- Admission controllers (OPA/Gatekeeper, Kyverno).
- Service mesh with mTLS (Istio, Linkerd).
- Secrets management and rotation.
- Audit logging.

### Serverless

- Least-privilege functions.
- Input validation.
- Cold-start monitoring.
- API gateway security.
- Cost/DoS controls.

### Infrastructure as Code

- Version control all IaC.
- Scan templates with Checkov, tfsec, cfn-lint.
- Use policy as code.
- Apply least privilege to deployment roles.

---

## 77. API Gateway Responsibilities

- TLS termination
- Authentication
- Authorization (coarse-grained)
- Rate limiting
- Request/response validation
- WAF
- Logging and metrics
- Routing
- Protocol translation

---

## 78. Business Logic Security

- Identify high-value workflows (payments, account changes, admin actions).
- Enforce invariants server-side.
- Limit transaction velocity.
- Require re-authentication for sensitive actions.
- Implement audit trails.
- Test negative and edge cases.

---

## 79. Denial-of-Service Considerations

- Validate and limit input sizes.
- Set timeouts on all external calls.
- Implement rate limiting and quotas.
- Use circuit breakers for dependencies.
- Limit recursion and query depth.
- Protect against slowloris and large payload attacks.
- Use CDNs and WAFs for absorption.

---

## 80. Cryptographic Agility

- Design systems to support algorithm and key size changes.
- Include version identifiers in ciphertext formats.
- Maintain backward compatibility for decryption.
- Have tested migration plans.
- Deprecate weak algorithms promptly.

---

## 81. Trusted Execution and Confidential Computing

- **Intel SGX**, **AMD SEV-SNP**, **ARM TrustZone**, **AWS Nitro Enclaves** provide isolated execution.
- Useful for processing sensitive data without exposing it to the host.
- Attestation verifies the integrity of the enclave.

---

## 82. Blockchain and Smart Contract Security (Brief)

- Reentrancy, integer overflow, access control, front-running, oracle manipulation.
- Use established patterns: checks-effects-interactions, pull over push.
- Audit contracts before mainnet deployment.
- Use formal verification and fuzzing where feasible.

---

## 83. Automotive and IoT Security

- Secure boot, signed firmware updates, hardware roots of trust.
- Network segmentation in vehicles (CAN, Ethernet).
- OTA update integrity and rollback.
- Minimize attack surface; disable debug interfaces.
- Monitor anomaly detection.

---

## 84. Human Factors in Security

- Usable security reduces workarounds.
- Avoid excessive warnings that lead to habituation.
- Design MFA that is easy to use.
- Provide clear privacy controls.
- Train regularly with realistic scenarios.

---

## 85. Procurement and Vendor Security

- Include security requirements in RFPs and contracts.
- Review SOC 2 Type II, ISO 27001, or equivalent reports.
- Understand data residency and sub-processors.
- Define incident notification SLAs.
- Plan for vendor offboarding and data deletion.

---

## 86. Privacy by Design

- Minimize data collection.
- Use data for specified purposes only.
- Limit retention.
- Provide transparency and user rights.
- Anonymize/pseudonymize where possible.
- Conduct Data Protection Impact Assessments (DPIA).

---

## 87. Secure Decommissioning

- Revoke credentials and certificates.
- Delete data securely (crypto-shredding or secure erase).
- Remove DNS entries and cloud resources.
- Update asset inventory.
- Archive logs per retention policy.

---

## 88. Red Team Rules of Engagement

- Written authorization (scope, targets, timing, constraints).
- Define out-of-scope systems and data.
- Establish communication channels and escalation paths.
- Do not exfiltrate real PII without explicit permission.
- Report findings promptly and confidentially.

---

## 89. Bug Bounty Program Basics

- Clear scope and safe-harbor policy.
- Responsive triage and payouts.
- Public disclosure options.
- Integration with development workflow.
- Program metrics and trend analysis.

---

## 90. Tabletop Exercise Format

1. Scenario: describe the attack.
2. Injection: introduce complications.
3. Discussion: walk through detection, containment, communication.
4. Hotwash: identify gaps and action items.
5. Update playbooks and controls.

---

## 91. Security Champions Program

- Embed security-minded developers in each team.
- Provide training and tooling.
- Give them time and authority to review security work.
- Share knowledge through guilds or communities of practice.

---

## 92. Secure Configuration Baselines

- Maintain hardened configs for OS, web server, database, framework.
- Use configuration management (Ansible, Chef, Puppet, Terraform).
- Scan for drift from baseline.
- Review changes through change control.

---

## 93. Certificate Management

- Use short-lived certificates where possible (e.g., Let's Encrypt 90 days).
- Automate issuance and renewal (ACME).
- Monitor expiry and revocation.
- Use CAA records to restrict issuers.
- Maintain an inventory of certificates and their locations.

---

## 94. Network Traffic Analysis

- Capture NetFlow, packet captures, and DNS logs.
- Look for beaconing, lateral movement, data exfiltration.
- Use baselines to detect anomalies.
- Correlate with endpoint telemetry.

---

## 95. Endpoint Security

- EDR/XDR deployment.
- Host firewall and application control.
- Disk encryption.
- Patch management.
- Least privilege user accounts.
- USB/device control.
- Remote wipe capability.

---

## 96. Identity Proofing Levels

NIST 800-63-3 defines Identity Assurance Levels (IAL), Authenticator Assurance Levels (AAL), and Federation Assurance Levels (FAL).

- IAL1: self-asserted.
- IAL2: remote identity proofing with evidence.
- IAL3: in-person or supervised remote proofing.
- AAL1: single-factor authentication.
- AAL2: two-factor authentication.
- AAL3: two-factor with hardware cryptographic authenticator and verifier impersonation resistance.

---

## 97. Federation Security

- Validate SAML/OIDC signatures and issuer.
- Use PKCE for public OIDC clients.
- Map federated identities to internal roles carefully.
- Monitor for account linking attacks.
- Enforce MFA at the identity provider.

---

## 98. Risk Acceptance

- Some risks cannot be fully mitigated.
- Document accepted risks with rationale, owner, compensating controls, and review date.
- Revisit accepted risks periodically.

---

## 99. Security Automation

- Automate scanning, patching, and response where safe.
- Use SOAR for playbook-driven response.
- Balance speed with human oversight for high-impact actions.
- Maintain audit trails for automated decisions.

---

## 100. Final Security Axioms

- Complexity is the enemy of security.
- Assume breach and design for resilience.
- You cannot test security in; it must be built in.
- The strongest lock is useless if the door is left open.
- Security is a conversation, not a gate.

End of facts.


---

## 101. Security Cookbook

A collection of runnable snippets for common security tasks.

### Generate a secure random token

```python
import secrets
token = secrets.token_urlsafe(32)
```

```javascript
const crypto = require('crypto');
const token = crypto.randomBytes(32).toString('base64url');
```

```go
import (
    "crypto/rand"
    "encoding/base64"
)
func token() string {
    b := make([]byte, 32)
    rand.Read(b)
    return base64.URLEncoding.EncodeToString(b)
}
```

### Hash a password

```python
from argon2 import PasswordHasher
ph = PasswordHasher(time_cost=3, memory_cost=65536, parallelism=1)
hash_value = ph.hash(password)
```

```javascript
const bcrypt = require('bcrypt');
const hash = await bcrypt.hash(password, 12);
```

```go
import "golang.org/x/crypto/bcrypt"
hash, _ := bcrypt.GenerateFromPassword([]byte(password), bcrypt.DefaultCost)
```

### Verify a password

```python
ph.verify(hash_value, password)
```

```javascript
await bcrypt.compare(password, hash);
```

```go
bcrypt.CompareHashAndPassword(hash, []byte(password))
```

### Encrypt with AES-GCM

```python
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
import os

key = os.urandom(32)
aesgcm = AESGCM(key)
nonce = os.urandom(12)
ct = aesgcm.encrypt(nonce, b"message", b"context")
pt = aesgcm.decrypt(nonce, ct, b"context")
```

```javascript
const crypto = require('crypto');
const key = crypto.randomBytes(32);
const iv = crypto.randomBytes(16);
const cipher = crypto.createCipheriv('aes-256-gcm', key, iv);
let ct = cipher.update('message', 'utf8', 'hex');
ct += cipher.final('hex');
const authTag = cipher.getAuthTag();
```

### Sign data with HMAC

```python
import hmac, hashlib
sig = hmac.new(key, message, hashlib.sha256).hexdigest()
```

```javascript
const sig = crypto.createHmac('sha256', key).update(message).digest('hex');
```

```go
import "crypto/hmac"
import "crypto/sha256"
mac := hmac.New(sha256.New, key)
mac.Write(message)
sig := mac.Sum(nil)
```

### Constant-time comparison

```python
import hmac
hmac.compare_digest(a, b)
```

```javascript
crypto.timingSafeEqual(Buffer.from(a), Buffer.from(b))
```

```go
crypto/subtle.ConstantTimeCompare([]byte(a), []byte(b)) == 1
```

### Issue a JWT

```python
import jwt
from datetime import datetime, timedelta, timezone

token = jwt.encode(
    {"sub": user_id, "exp": datetime.now(timezone.utc) + timedelta(minutes=15)},
    secret,
    algorithm="HS256",
)
```

### Validate a JWT

```python
payload = jwt.decode(token, secret, algorithms=["HS256"])
```

### Set a secure cookie

```python
response.set_cookie(
    "session",
    value=token,
    httponly=True,
    secure=True,
    samesite="Strict",
    max_age=3600,
)
```

### SQL query with parameters

```python
cursor.execute("SELECT * FROM users WHERE email = ?", (email,))
```

```javascript
await pool.query('SELECT * FROM users WHERE email = $1', [email]);
```

```go
db.QueryRow("SELECT * FROM users WHERE email = ?", email)
```

### HTML entity encode

```python
import html
html.escape(user_input)
```

```javascript
function escapeHtml(str) {
  return str.replace(/[&<>"']/g, m => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[m]));
}
```

### Validate an email address

```python
import re

def is_valid_email(email: str) -> bool:
    if len(email) > 254:
        return False
    if "@" not in email:
        return False
    local, domain = email.rsplit("@", 1)
    if len(local) > 64:
        return False
    return re.match(r"^[a-zA-Z0-9.!#$%&'*+/=?^_`{|}~-]+@[a-zA-Z0-9-]+(\.[a-zA-Z0-9-]+)*$", email) is not None
```

### Path traversal safe open

```python
from pathlib import Path

def safe_open(base: Path, name: str):
    base = base.resolve()
    target = (base / name).resolve()
    if not str(target).startswith(str(base)):
        raise ValueError("bad path")
    return open(target, "rb")
```

### Block private IPs for SSRF prevention

```python
import ipaddress

def is_private(host: str) -> bool:
    try:
        ip = ipaddress.ip_address(host)
        return ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_multicast
    except ValueError:
        return False
```

### Generate a nonce for CSP

```python
import secrets
nonce = secrets.token_urlsafe(16)
```

### Verify webhook signature

```python
import hmac, hashlib
expected = hmac.new(secret, payload, hashlib.sha256).hexdigest()
if not hmac.compare_digest(f"sha256={expected}", signature):
    raise ValueError("bad signature")
```

### Create a bcrypt hash with explicit cost

```python
import bcrypt
hash_value = bcrypt.hashpw(password.encode(), bcrypt.gensalt(rounds=12))
bcrypt.checkpw(password.encode(), hash_value)
```

### Derive a key with PBKDF2

```python
import hashlib
key = hashlib.pbkdf2_hmac('sha256', password.encode(), salt, 600000)
```

### Create a self-signed cert for testing

```bash
openssl req -x509 -newkey rsa:2048 -keyout key.pem -out cert.pem -days 365 -nodes -subj "/CN=localhost"
```

### Test TLS configuration

```bash
testssl.sh https://example.com
```

### Scan for secrets in git history

```bash
gitleaks detect --source . --verbose
truffleHog filesystem .
```

### Run a dependency audit

```bash
pip-audit
npm audit
yarn audit
cargo audit
go list -json -m all | nancy sleuth
```

### Scan a Docker image

```bash
trivy image myapp:latest
grype myapp:latest
```

### Sign a container image

```bash
cosign sign --key cosign.key myregistry/myapp:latest
```

### Verify a container image

```bash
cosign verify --key cosign.pub myregistry/myapp:latest
```

### Generate an SBOM

```bash
syft packages dir:. -o spdx-json > sbom.spdx.json
```

### Restrict SSH access

```bash
# /etc/ssh/sshd_config
PermitRootLogin no
PasswordAuthentication no
PubkeyAuthentication yes
AllowUsers alice bob
MaxAuthTries 3
```

### iptables basic rules

```bash
iptables -P INPUT DROP
iptables -P FORWARD DROP
iptables -P OUTPUT ACCEPT
iptables -A INPUT -i lo -j ACCEPT
iptables -A INPUT -m conntrack --ctstate ESTABLISHED,RELATED -j ACCEPT
iptables -A INPUT -p tcp --dport 22 -j ACCEPT
iptables -A INPUT -p tcp --dport 443 -j ACCEPT
```

### PostgreSQL row-level security

```sql
CREATE POLICY user_isolation ON orders
    FOR ALL TO app_user
    USING (user_id = current_setting('app.current_user_id')::uuid);
ALTER TABLE orders ENABLE ROW LEVEL SECURITY;
```

### Redis protected mode

```conf
requirepass strong_password
bind 127.0.0.1
protected-mode yes
rename-command FLUSHDB ""
rename-command FLUSHALL ""
```

### Kubernetes network policy default deny

```yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: default-deny-all
spec:
  podSelector: {}
  policyTypes:
    - Ingress
    - Egress
```

### AWS S3 block public access

```bash
aws s3api put-public-access-block \
  --bucket my-bucket \
  --public-access-block-configuration \
  "BlockPublicAcls=true,IgnorePublicAcls=true,BlockPublicPolicy=true,RestrictPublicBuckets=true"
```

### GitHub branch protection

```yaml
branches:
  - name: main
    protection:
      required_pull_request_reviews:
        required_approving_review_count: 1
      required_status_checks:
        strict: true
      enforce_admins: true
      required_linear_history: true
      allow_force_pushes: false
      allow_deletions: false
```

### Nginx rate limiting

```nginx
limit_req_zone $binary_remote_addr zone=login:10m rate=5r/m;

server {
    location /login {
        limit_req zone=login burst=3 nodelay;
        proxy_pass http://backend;
    }
}
```

### Fail2ban basic jail

```ini
[sshd]
enabled = true
port = ssh
filter = sshd
logpath = /var/log/auth.log
maxretry = 3
bantime = 3600
```

### Auditd rule for sensitive file access

```bash
auditctl -w /etc/shadow -p wa -k shadow_changes
```

### SELinux enforcing mode

```bash
setenforce 1
sed -i 's/SELINUX=permissive/SELINUX=enforcing/' /etc/selinux/config
```

### AppArmor profile load

```bash
aa-enforce /etc/apparmor.d/usr.bin.myapp
```

### seccomp profile for Docker

```json
{
  "defaultAction": "SCMP_ACT_ERRNO",
  "syscalls": [
    {
      "names": ["read", "write", "exit", "exit_group"],
      "action": "SCMP_ACT_ALLOW"
    }
  ]
}
```

### HashiCorp Vault KV read

```bash
vault kv get -field=password secret/data/db
```

### AWS IAM least-privilege policy

```json
{
  "Version": "2012-10-17",
  "Statement": [{
    "Effect": "Allow",
    "Action": ["s3:GetObject", "s3:PutObject"],
    "Resource": "arn:aws:s3:::bucket-name/*"
  }]
}
```

### Azure conditional access

Require MFA for admin roles and block legacy authentication.

### GCP service account key rotation

Prefer workload identity federation; avoid downloading service account keys.

### OWASP ZAP baseline scan

```bash
docker run -t owasp/zap2docker-stable zap-baseline.py -t https://example.com
```

### Semgrep security scan

```bash
semgrep --config=p/security-audit --config=p/owasp-top-ten --config=p/cwe-top-25 src/
```

### Bandit Python scan

```bash
bandit -r src/
```

### npm audit fix

```bash
npm audit fix
npm audit fix --force  # use with caution
```

### Go vulnerability check

```bash
go install golang.org/x/vuln/cmd/govulncheck@latest
govulncheck ./...
```

### Rust cargo audit

```bash
cargo install cargo-audit
cargo audit
```

### Java SpotBugs security

```bash
mvn spotbugs:spotbugs -Dspotbugs.effort=max -Dspotbugs.threshold=low
```

### C# security analyzers

Enable `Security` rule set in `.editorconfig` or Roslyn analyzers.

### Checkov IaC scan

```bash
checkov --directory .
```

### tfsec Terraform scan

```bash
tfsec .
```

### kube-score manifest check

```bash
kube-score score deployment.yaml
```

### Conftest policy check

```bash
conftest test deployment.yaml --policy policy/
```

### Security headers test

```bash
curl -I https://example.com | grep -i "strict-transport\|content-security\|x-frame\|x-content"
```

### DNSSEC check

```bash
dig +dnssec example.com DNSKEY
```

### DMARC record

```dns
_dmarc.example.com. IN TXT "v=DMARC1; p=quarantine; rua=mailto:dmarc@example.com"
```

### SPF record

```dns
example.com. IN TXT "v=spf1 include:_spf.google.com -all"
```

### DKIM record

```dns
selector._domainkey.example.com. IN TXT "v=DKIM1; k=rsa; p=..."
```

### Generate age key

```bash
age-keygen -o key.txt
```

### Encrypt file with age

```bash
age -r age1... -o file.txt.age file.txt
```

### Decrypt file with age

```bash
age -d -i key.txt -o file.txt file.txt.age
```

### GPG symmetric encryption

```bash
gpg --symmetric --cipher-algo AES256 --compress-algo 1 --s2k-digest-algo SHA512 file.txt
```

### GPG verify signature

```bash
gpg --verify file.txt.asc file.txt
```

### Create minimal Dockerfile

```dockerfile
FROM python:3.12-slim
RUN groupadd -r app && useradd -r -g app app
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
USER app
CMD ["python", "-m", "uvicorn", "main:app", "--host", "0.0.0.0"]
```

### Run container securely

```bash
docker run -d \
  --read-only \
  --tmpfs /tmp:noexec,nosuid,size=100m \
  --cap-drop ALL \
  --security-opt no-new-privileges:true \
  --user 1000:1000 \
  myapp:latest
```

### Systemd hardening

```ini
[Service]
User=app
Group=app
NoNewPrivileges=true
ProtectSystem=strict
ProtectHome=true
ReadWritePaths=/var/lib/app
ProtectKernelTunables=true
ProtectKernelModules=true
ProtectControlGroups=true
RestrictRealtime=true
RestrictSUIDSGID=true
```

### Enable ASLR

```bash
echo 2 > /proc/sys/kernel/randomize_va_space
```

### Core dump restriction

```bash
echo "* hard core 0" >> /etc/security/limits.conf
```

### Kernel ptrace restriction

```bash
echo 1 > /proc/sys/kernel/yama/ptrace_scope
```

End of cookbook.
