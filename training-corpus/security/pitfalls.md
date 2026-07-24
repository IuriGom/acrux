# Security — Pitfalls, Edge Cases, and How to Avoid Them

This file catalogs common mistakes, dangerous shortcuts, and subtle edge cases that lead to security vulnerabilities. For each pitfall, it explains the problem and gives a safe alternative.

---

## 1. Trusting Client-Side Validation

**Pitfall**: Implementing validation only in the browser or mobile app.

**Why it is dangerous**: Attackers can bypass client-side checks using proxies, custom clients, or disabled JavaScript.

**Safe approach**: Always re-validate on the server. Treat client-side validation as a UX enhancement only.

---

## 2. Using Denylists for Input Validation

**Pitfall**: Rejecting inputs that contain `<script>` or `'` instead of defining what is allowed.

**Why it is dangerous**: Attackers can evade filters with encoding, case variation, null bytes, or unknown payloads. Denylists also block legitimate input like `O'Brien`.

**Safe approach**: Use allowlists (regex, type systems, schemas) and context-aware output encoding.

---

## 3. Concatenating Strings into SQL Queries

**Pitfall**: Building SQL with f-strings, `+`, or `%` formatting.

```python
# VULNERABLE
cursor.execute(f"SELECT * FROM users WHERE name = '{name}'")
```

**Why it is dangerous**: Classic SQL injection leading to data theft, modification, or RCE.

**Safe approach**: Use parameterized queries.

```python
cursor.execute("SELECT * FROM users WHERE name = ?", (name,))
```

---

## 4. Rolling Your Own Crypto

**Pitfall**: Implementing custom ciphers, hash algorithms, or protocols.

**Why it is dangerous**: Cryptography is extremely error-prone. Subtle mistakes in IV handling, padding, key derivation, or side-channel resistance break the whole design.

**Safe approach**: Use well-vetted libraries: libsodium, OpenSSL, pyca/cryptography, Google Tink, NaCl, boringssl.

---

## 5. Using Weak or Fast Hashing for Passwords

**Pitfall**: Storing passwords with MD5, SHA-1, SHA-256, or unsalted hashes.

**Why it is dangerous**: Fast hashes allow billions of guesses per second on GPUs. Rainbow tables defeat unsalted hashes.

**Safe approach**: Use Argon2id, bcrypt, scrypt, or PBKDF2 with per-user salt and appropriate work factor.

---

## 6. Reusing Nonces in AES-GCM

**Pitfall**: Using a static IV or accidentally repeating a nonce.

**Why it is dangerous**: GCM nonce reuse completely breaks confidentiality and allows forgery.

**Safe approach**: Generate a unique nonce with a CSPRNG for every encryption under a given key. Consider synthetic IVs or XChaCha20-Poly1305 for random nonces.

---

## 7. Using ECB Mode

**Pitfall**: Encrypting data with AES-ECB because it is the default or simple.

**Why it is dangerous**: ECB does not use an IV and leaks patterns in the plaintext.

**Safe approach**: Use AES-GCM, AES-CTR + HMAC, or ChaCha20-Poly1305.

---

## 8. Storing Secrets in Code or Config

**Pitfall**: Hard-coding API keys, database passwords, or private keys in source files or `.env` committed to git.

**Why it is dangerous**: Source code leaks, git history persists, and config files are often world-readable.

**Safe approach**: Use a vault, KMS, or runtime-injected secrets. Scan history and rotate any exposed secret.

---

## 9. Accepting the JWT "none" Algorithm

**Pitfall**: Verifying JWTs without specifying allowed algorithms.

```python
# VULNERABLE
jwt.decode(token, key, algorithms=None)
```

**Why it is dangerous**: An attacker can change `alg` to `none` and forge tokens.

**Safe approach**: Explicitly allow only expected algorithms and validate issuer/audience.

```python
jwt.decode(token, key, algorithms=["RS256"], audience="my-api", issuer="auth")
```

---

## 10. Using Short or Predictable Secrets

**Pitfall**: Using `secret123`, default passwords, or low-entropy JWT/HMAC keys.

**Why it is dangerous**: Offline brute-force can recover the key, allowing token forgery.

**Safe approach**: Generate keys with a CSPRNG; use at least 256 bits for HMAC and 2048-bit RSA / 256-bit ECC.

---

## 11. Returning Verbose Errors

**Pitfall**: Returning stack traces, SQL errors, or internal paths to users.

**Why it is dangerous**: Information leakage aids attackers in reconnaissance and exploit development.

**Safe approach**: Log detailed errors internally; return generic messages externally.

```python
logger.exception("database error")
return JSONResponse({"detail": "internal error"}, status_code=500)
```

---

## 12. Missing Authorization Checks

**Pitfall**: Checking only that a user is logged in, not whether they own the resource.

```python
# VULNERABLE
@app.get("/orders/{order_id}")
def get_order(order_id: str, user: User):
    return db.orders.find_one({"_id": order_id})
```

**Why it is dangerous**: IDOR/Broken Access Control allows reading other users' data.

**Safe approach**: Enforce authorization for the specific resource and action.

```python
order = db.orders.find_one({"_id": order_id, "user_id": user.id})
if not order:
    raise HTTPException(404)
```

---

## 13. Relying on Obscure IDs Alone

**Pitfall**: Assuming UUIDs or random IDs replace authorization.

**Why it is dangerous**: IDs can leak, be enumerated, or be shared. Authorization must still be enforced.

**Safe approach**: Use indirect references where helpful, but always check permissions server-side.

---

## 14. Not Using HttpOnly / Secure / SameSite Cookies

**Pitfall**: `Set-Cookie: sessionid=abc123`.

**Why it is dangerous**: XSS can steal session cookies; cookies can be sent over HTTP in MITM scenarios; CSRF is easier without SameSite.

**Safe approach**:

```http
Set-Cookie: sessionid=abc123; HttpOnly; Secure; SameSite=Strict; Path=/; Max-Age=3600
```

---

## 15. Storing Tokens in localStorage

**Pitfall**: `localStorage.setItem("token", jwt)`.

**Why it is dangerous**: Any XSS payload can exfiltrate the token.

**Safe approach**: Use `HttpOnly` cookies for session/refresh tokens, or keep short-lived access tokens in memory/closures with fingerprint binding and strict CSP.

---

## 16. Missing CSRF Protection

**Pitfall**: State-changing operations reachable via simple form POST or GET.

**Why it is dangerous**: Attackers can forge requests from a victim's browser.

**Safe approach**: Use CSRF tokens, SameSite cookies, re-authentication for sensitive actions, and require custom headers for APIs.

---

## 17. Weak CORS Configuration

**Pitfall**: `Access-Control-Allow-Origin: *` with `Access-Control-Allow-Credentials: true`.

**Why it is dangerous**: Any site can make authenticated cross-origin requests.

**Safe approach**: Allowlist specific origins; never reflect arbitrary origins; avoid credentials with wildcard.

---

## 18. SSRF via URL Parsing

**Pitfall**: Passing user-supplied URLs directly to HTTP clients without validation.

**Why it is dangerous**: Attackers can access internal services, cloud metadata endpoints (`169.254.169.254`), or exfiltrate data.

**Safe approach**: Allowlist schemes/hosts, resolve and block private IPs, use an egress proxy, and restrict response handling.

---

## 19. Deserializing Untrusted Data

**Pitfall**: Using `pickle.loads`, `ObjectInputStream`, `unserialize`, `Marshal.load` on attacker-controlled data.

**Why it is dangerous**: Leads directly to remote code execution.

**Safe approach**: Use JSON/XML with schema validation, or signed/encrypted data with strict typing.

---

## 20. Insecure File Uploads

**Pitfall**: Trusting file extensions and storing uploads inside web root.

**Why it is dangerous**: Uploaded `.php`, `.jsp`, `.html`, or double extensions can execute on the server.

**Safe approach**: Verify magic bytes, allowlist types, rename files, store outside web root, serve with `Content-Disposition: attachment`, scan for malware.

---

## 21. Path Traversal

**Pitfall**: Using user input in file paths without canonicalization.

```python
# VULNERABLE
open(f"/var/data/{user_input}")
```

**Why it is dangerous**: `../../../etc/passwd` exposes arbitrary files.

**Safe approach**: Validate filenames against allowlists, use `Path.resolve()` and check it stays within base directory.

```python
from pathlib import Path
base = Path("/var/data").resolve()
requested = (base / filename).resolve()
if not str(requested).startswith(str(base)):
    raise ValueError("invalid path")
```

---

## 22. Command Injection

**Pitfall**: Passing user input to `os.system`, `subprocess.call(shell=True)`, `eval`, or backticks.

```python
# VULNERABLE
os.system(f"ping {host}")
```

**Why it is dangerous**: Shell metacharacters (`;`, `|`, `&&`, backticks) allow arbitrary command execution.

**Safe approach**: Use exec-style APIs and avoid shell interpretation.

```python
import subprocess
subprocess.run(["ping", "-c", "3", host], check=True)
```

---

## 23. Logging Sensitive Data

**Pitfall**: `logger.info(f"login attempt: {password}")`.

**Why it is dangerous**: Logs are often widely accessible and retained long-term.

**Safe approach**: Sanitize logs; never log passwords, tokens, full PAN, SSN, or unredacted PII.

---

## 24. Insecure Randomness

**Pitfall**: Using `Math.random()`, `rand()`, `java.util.Random`, or UUIDv1 for security tokens.

**Why it is dangerous**: Predictable tokens allow session hijacking, password reset abuse, and CSRF bypass.

**Safe approach**: Use a CSPRNG (`secrets`, `crypto.randomBytes`, `SecureRandom`, `crypto/rand`).

---

## 25. Timing Attacks on Comparison

**Pitfall**: Comparing secrets or tokens with `==`.

**Why it is dangerous**: Short-circuit comparison leaks timing information.

**Safe approach**: Use constant-time comparison functions.

```python
hmac.compare_digest(a, b)
```

---

## 26. Integer Overflow and Wraparound

**Pitfall**: Assuming arithmetic on bounded integers is safe.

**Why it is dangerous**: Wraparound can bypass bounds checks, cause buffer overflows, or enable financial manipulation.

**Safe approach**: Use checked arithmetic, saturate, or use big integers where appropriate. In C, check before operations; in Rust, use checked methods; in higher-level languages, validate ranges.

---

## 27. Format String Vulnerabilities

**Pitfall**: Passing user data as a format string in C (`printf(user_input)`).

**Why it is dangerous**: Can read and write memory.

**Safe approach**: Always use a literal format string: `printf("%s", user_input)`.

---

## 28. Use-After-Free and Double-Free

**Pitfall**: Accessing memory after freeing it or freeing the same pointer twice.

**Why it is dangerous**: Memory corruption, crashes, and code execution.

**Safe approach**: Use smart pointers/RAII, avoid manual memory management, and test with AddressSanitizer.

---

## 29. Buffer Overflows

**Pitfall**: Using unbounded string/copy functions in C/C++.

**Why it is dangerous**: Stack/heap overflows enable code execution.

**Safe approach**: Use bounded alternatives, safe languages, and stack canaries.

---

## 30. Race Conditions in Security Checks

**Pitfall**: Check-then-act without synchronization.

```python
if user.balance >= amount:
    user.balance -= amount
```

**Why it is dangerous**: Concurrent requests can pass the check and overdraw.

**Safe approach**: Use atomic operations or database transactions with proper isolation.

```python
BEGIN;
SELECT balance FROM accounts WHERE id = ? FOR UPDATE;
UPDATE accounts SET balance = balance - ? WHERE id = ? AND balance >= ?;
COMMIT;
```

---

## 31. ReDoS (Regex Denial of Service)

**Pitfall**: Writing regexes with nested quantifiers that backtrack catastrophically.

Example: `^(a+)+$` against `aaaaaaaaaaaaaaaaaaaaaaaaaaaa!`.

**Why it is dangerous**: Causes CPU exhaustion and DoS.

**Safe approach**: Use possessive quantifiers, atomic groups, or regex engines with timeout/re linear-time guarantees (e.g., `re2`, Go's regexp).

---

## 32. XML External Entity (XXE) Attacks

**Pitfall**: Enabling DTD processing in XML parsers.

**Why it is dangerous**: Allows file disclosure, SSRF, and DoS (billion laughs).

**Safe approach**: Disable DTDs/external entities, use JSON, or use defusedxml.

```python
from defusedxml import ElementTree as ET
ET.parse(file)
```

---

## 33. Insecure Direct Object Reference (IDOR)

**Pitfall**: Using sequential numeric IDs in URLs without authorization.

**Why it is dangerous**: Users can enumerate and access other users' resources.

**Safe approach**: Use UUIDs and enforce resource-level authorization.

---

## 34. Open Redirects

**Pitfall**: Redirecting to a user-supplied URL after login or logout.

**Why it is dangerous**: Phishing and OAuth token theft.

**Safe approach**: Allowlist redirect destinations or use indirect mapping.

```python
REDIRECTS = {"dashboard": "/dashboard", "profile": "/profile"}

def safe_redirect(target: str) -> str:
    return REDIRECTS.get(target, "/")
```

---

## 35. Mass Assignment

**Pitfall**: Binding request bodies directly to model objects without allowlisting fields.

**Why it is dangerous**: Attackers can set `is_admin`, `role`, or `balance`.

**Safe approach**: Use DTOs/validation schemas that explicitly declare writable fields.

---

## 36. Insecure API Design

**Pitfall**: Exposing internal IDs, verbose errors, or admin endpoints without auth.

**Why it is dangerous**: Information disclosure and privilege escalation.

**Safe approach**: Use UUIDs, generic errors, and authenticate/authorize every endpoint.

---

## 37. Trusting Third-Party Libraries

**Pitfall**: Adding any npm/PyPI/crate package without review.

**Why it is dangerous**: Malicious or abandoned packages can steal data or backdoor builds.

**Safe approach**: Pin versions, verify checksums, scan with SCA, review popular/well-maintained packages, and minimize dependencies.

---

## 38. Dependency Confusion

**Pitfall**: Using unscoped internal package names that can be shadowed on public registries.

**Why it is dangerous**: Attackers publish a higher-version public package with the same name.

**Safe approach**: Use scoped/internal registries, namespace packages, and `.npmrc`/`pip.conf` to enforce sources.

---

## 39. Supply Chain Tampering

**Pitfall**: Pulling images or binaries without verifying signatures.

**Why it is dangerous**: Compromised build or registry can distribute malware.

**Safe approach**: Sign artifacts and images, verify signatures in CI and at runtime, use SBOMs.

---

## 40. Overly Permissive Container Privileges

**Pitfall**: Running containers as root, with full capabilities, or writable rootfs.

**Why it is dangerous**: Container escape or host compromise.

**Safe approach**: Use non-root users, drop capabilities, read-only rootfs, seccomp/AppArmor, and minimal base images.

---

## 41. Exposing Metadata Endpoints

**Pitfall**: Leaving cloud metadata endpoints (`169.254.169.254`) reachable from application code.

**Why it is dangerous**: SSRF can steal IAM credentials.

**Safe approach**: Block link-local addresses, use IMDSv2 with hop limit, restrict egress, and use short-lived instance profiles.

---

## 42. Weak TLS Configuration

**Pitfall**: Supporting TLS 1.0/1.1, weak ciphers, or no HSTS.

**Why it is dangerous**: Downgrade attacks, weak encryption, and MITM.

**Safe approach**: Use TLS 1.2/1.3 with AEAD ciphers, disable compression, enable HSTS, and use strong certificates.

---

## 43. Long-Lived Credentials

**Pitfall**: API keys or service account keys that never expire.

**Why it is dangerous**: Leaked keys grant indefinite access.

**Safe approach**: Use short-lived tokens, workload identity, automatic rotation, and vault-issued credentials.

---

## 44. Missing Account Lockout / Rate Limiting

**Pitfall**: Allowing unlimited login attempts.

**Why it is dangerous**: Credential stuffing and brute force.

**Safe approach**: Implement progressive delays, account lockout, CAPTCHA, and breach-password checks.

---

## 45. User Enumeration

**Pitfall**: Different error messages or timing for invalid user vs invalid password.

**Why it is dangerous**: Attackers can build lists of valid accounts.

**Safe approach**: Return generic errors and perform constant-time credential lookup.

---

## 46. Insecure Password Recovery

**Pitfall**: Predictable reset tokens, tokens with long expiry, or sending passwords in email.

**Why it is dangerous**: Account takeover.

**Safe approach**: Use CSPRNG tokens, single-use, time-limited, send via HTTPS link, and invalidate on password change.

---

## 47. Broken MFA Implementations

**Pitfall**: Allowing bypass codes, not validating TOTP properly, or storing seeds insecurely.

**Why it is dangerous**: MFA is bypassed.

**Safe approach**: Use standard TOTP/OATH libraries, encrypt seeds, enforce verification, and do not allow downgrade.

---

## 48. Storing Session Data in JWT

**Pitfall**: Putting large or sensitive state into JWTs to avoid server-side sessions.

**Why it is dangerous**: JWTs cannot be revoked easily; payloads are readable; large tokens bloat requests.

**Safe approach**: Keep JWTs small and short-lived; use opaque session IDs with server-side storage for mutable state.

---

## 49. Not Rotating Keys After Compromise

**Pitfall**: Continuing to use a leaked signing key or database password.

**Why it is dangerous**: Persistent unauthorized access.

**Safe approach**: Have a tested key rotation runbook; rotate immediately on suspected compromise.

---

## 50. Insecure Defaults in Frameworks

**Pitfall**: Using debug mode, permissive CORS, or auto-escaping disabled.

**Why it is dangerous**: Framework defaults may be optimized for development, not production.

**Safe approach**: Audit and harden defaults; use production config checklists.

---

## 51. Failing Open

**Pitfall**: When an auth check throws an exception, the handler proceeds.

```python
# VULNERABLE
try:
    check_auth(request)
except:
    pass
return sensitive_data()
```

**Why it is dangerous**: Errors become authorization bypasses.

**Safe approach**: Default to deny; explicitly handle failures.

---

## 52. Clickjacking

**Pitfall**: Allowing your site to be framed by any origin.

**Why it is dangerous**: Attackers overlay malicious UI to trick users.

**Safe approach**: Set `frame-ancestors 'none'` or `'self'` in CSP; legacy `X-Frame-Options: DENY`.

---

## 53. MIME Sniffing

**Pitfall**: Serving user-uploaded files without `X-Content-Type-Options: nosniff`.

**Why it is dangerous**: Browsers may interpret HTML/JS inside an uploaded file as executable.

**Safe approach**: Serve uploads with correct `Content-Type` and `nosniff`; use separate domain/cookie-less origin for untrusted content.

---

## 54. Session Fixation

**Pitfall**: Reusing the same session ID before and after authentication.

**Why it is dangerous**: Attacker can pre-set a session ID and hijack after login.

**Safe approach**: Regenerate session ID on login and privilege changes.

---

## 55. Insecure Cryptographic Padding

**Pitfall**: Using PKCS#1 v1.5 padding for RSA or no padding at all.

**Why it is dangerous**: Vulnerable to padding oracle attacks.

**Safe approach**: Use OAEP for RSA encryption, PSS for RSA signatures, or prefer ECDH/Ed25519.

---

## 56. Not Handling Exceptions Securely

**Pitfall**: Returning raw exception messages to API consumers.

**Why it is dangerous**: Leaks internals, libraries, and paths.

**Safe approach**: Catch exceptions centrally, log details, return generic responses.

---

## 57. Excessive Data Exposure

**Pitfall**: Returning full database objects in API responses.

**Why it is dangerous**: Leaks internal fields (hashes, flags, PII).

**Safe approach**: Use response DTOs; explicitly include fields needed by the client.

---

## 58. Insecure Backup Practices

**Pitfall**: Unencrypted backups, overly broad access, never tested restores.

**Why it is dangerous**: Backups become a target; ransomware can encrypt them too.

**Safe approach**: Encrypt, restrict access, test restores, and keep offline/air-gapped copies.

---

## 59. Ignoring Security Advisories

**Pitfall**: Not tracking CVEs for dependencies and OS packages.

**Why it is dangerous**: Known exploits remain unpatched.

**Safe approach**: Subscribe to advisories, scan regularly, and enforce patching SLAs.

---

## 60. Insecure CI/CD Secrets

**Pitfall**: Storing long-lived credentials in CI environment variables accessible to all builds.

**Why it is dangerous**: Compromised CI can leak production secrets.

**Safe approach**: Use OIDC/workload identity, short-lived tokens, vault integration, and branch protection.

---

## 61. Insecure Code Generation

**Pitfall**: Generating code from untrusted templates or data and executing it.

**Why it is dangerous**: RCE through template injection or eval.

**Safe approach**: Avoid dynamic code execution; use safe template engines with auto-escaping and sandboxing.

---

## 62. Subdomain Takeover

**Pitfall**: Pointing DNS to a deleted cloud resource (S3 bucket, Heroku app, etc.).

**Why it is dangerous**: Attackers can claim the resource and serve content under your domain.

**Safe approach**: Inventory DNS records, remove stale records, verify ownership before creation, and monitor for takeover tools.

---

## 63. Insecure WebSocket Usage

**Pitfall**: Not authenticating or authorizing WebSocket connections.

**Why it is dangerous**: Open persistent channels for data exfiltration or command and control.

**Safe approach**: Authenticate during handshake, validate origin, rate-limit messages, and apply authorization per channel/action.

---

## 64. GraphQL Depth/Complexity Attacks

**Pitfall**: Allowing unbounded nested queries.

**Why it is dangerous**: Expensive queries cause DoS and data over-extraction.

**Safe approach**: Limit query depth, complexity, and cost; use persisted/allowlisted queries.

---

## 65. Insecure Lambda / Serverless Configuration

**Pitfall**: Overly permissive IAM roles, public functions, or verbose error responses.

**Why it is dangerous**: Function exploitation can pivot to cloud resources.

**Safe approach**: Least privilege IAM, VPC networking, API gateway auth, centralized logging, and minimal dependencies.

---

## 66. Prototype Pollution (JavaScript)

**Pitfall**: Merging user-controlled objects without sanitizing `__proto__`, `constructor`, `prototype`.

**Why it is dangerous**: Logic bypass, RCE, or DoS.

**Safe approach**: Use structured cloning, schema validation (zod), or libraries that block prototype keys.

---

## 67. Insecure Deserialization in Python

**Pitfall**: Using `pickle`, `yaml.load`, or `marshal` on untrusted data.

**Safe approach**: Use `json`, `yaml.safe_load`, `msgpack` with strict types, or sign data with HMAC.

---

## 68. Type Juggling (PHP)

**Pitfall**: Loose comparisons (`==`) with user input and magic hashes.

**Safe approach**: Use strict comparisons (`===`) and explicit type casts.

---

## 69. Insecure Reflection (Java/.NET)

**Pitfall**: Using user input to choose classes/methods to invoke.

**Why it is dangerous**: RCE or unauthorized method calls.

**Safe approach**: Allowlist allowed classes/methods; avoid reflection driven by user input.

---

## 70. Final Pitfall Prevention Checklist

- [ ] Validate every input server-side with allowlists.
- [ ] Never concatenate untrusted data into commands/queries.
- [ ] Use parameterized queries and prepared statements.
- [ ] Encode output for the correct context.
- [ ] Use vetted cryptography and never reuse nonces.
- [ ] Store passwords with Argon2id/bcrypt/scrypt.
- [ ] Authenticate and authorize every request and resource.
- [ ] Use `HttpOnly` `Secure` `SameSite` cookies.
- [ ] Set strict CSP and security headers.
- [ ] Protect against CSRF, XSS, SSRF, and deserialization attacks.
- [ ] Do not log secrets or PII.
- [ ] Keep dependencies patched and scanned.
- [ ] Harden containers and cloud configurations.
- [ ] Have tested incident response and key rotation plans.


---

## 71. URL Validation Pitfalls

**Pitfall**: Parsing a URL with a regex and checking only the hostname string.

```python
# VULNERABLE
if "evil.com" not in url:
    requests.get(url)
```

**Why it is dangerous**: Bypasses using `@`, DNS tricks, or IDN homographs (`еxample.com` with Cyrillic `е`).

**Safe approach**: Parse with `urllib.parse` or `URL` class, validate scheme and resolved IP, and compare against an allowlist.

---

## 72. JSON Parsing Pitfalls

**Pitfall**: Trusting JSON input without schema validation.

**Why it is dangerous**: Unexpected types can cause crashes or logic bypasses (e.g., sending an array where a string is expected).

**Safe approach**: Use a validation library (Pydantic, zod, JSON Schema) before processing.

---

## 73. Authentication Bypass via HTTP Method Tampering

**Pitfall**: Enforcing auth only on `GET` but not `POST/PUT/DELETE` for the same route.

**Safe approach**: Apply authn/authz middleware globally and test all HTTP methods.

---

## 74. Bypass via HTTP Parameter Pollution

**Pitfall**: Frameworks parse repeated parameters differently; attackers can send `?role=user&role=admin`.

**Safe approach**: Treat repeated parameters as invalid, use typed request objects, and validate values strictly.

---

## 75. Insecure Use of `eval` and `exec`

**Pitfall**: `eval(user_input)` or `exec(user_input)`.

**Why it is dangerous**: Full remote code execution.

**Safe approach**: Use parsers/interpreters, safe eval libraries with allowlists, or redesign to avoid dynamic execution.

---

## 76. Server-Side Template Injection (SSTI)

**Pitfall**: Rendering templates with user input as the template string.

```python
# VULNERABLE (Jinja2)
render_template_string(template_str)
```

**Why it is dangerous**: RCE through template engine features.

**Safe approach**: Keep templates as static files; pass user data only as context variables.

---

## 77. Insecure Direct Use of `os.path.join`

**Pitfall**: `os.path.join(base, user_path)` without checking traversal.

**Safe approach**: Resolve and verify the final path is under base directory.

---

## 78. Trusting `Referer` or `Origin` Headers Alone

**Pitfall**: Using `Referer` for CSRF protection.

**Why it is dangerous**: Headers can be omitted or spoofed.

**Safe approach**: Use CSRF tokens and SameSite cookies.

---

## 79. Insecure `Authorization` Header Parsing

**Pitfall**: Splitting by space and trusting the second part without validation.

```python
# VULNERABLE
scheme, token = auth_header.split()
```

**Safe approach**: Validate scheme (`Bearer`), handle missing/malformed headers, and verify token format.

---

## 80. CORS with Reflected Origin

**Pitfall**: Returning the request `Origin` if it matches a regex loosely.

**Why it is dangerous**: `attackerexample.com` matching `*.example.com` regex.

**Safe approach**: Exact match against an allowlist of origins.

---

## 81. Insecure Use of `pickle` for Caching

**Pitfall**: Caching serialized objects in Redis/Memcached and deserializing on read.

**Why it is dangerous**: Anyone with cache access can inject malicious payloads.

**Safe approach**: Use JSON/msgpack or sign cache values with HMAC.

---

## 82. Trusting TLS Termination Headers Blindly

**Pitfall**: Using `X-Forwarded-Proto` without validating the proxy source.

**Why it is dangerous**: Clients can set headers and bypass HTTPS enforcement.

**Safe approach**: Configure trusted proxy list and strip/reject spoofed headers at the edge.

---

## 83. Insecure OAuth State Parameter

**Pitfall**: Using a static or predictable `state` value.

**Why it is dangerous**: CSRF login attacks.

**Safe approach**: Use a CSPRNG state, bind to session, and validate on callback.

---

## 84. Permissive Content-Type on Uploads

**Pitfall**: Allowing `application/octet-stream` or trusting browser-provided MIME type.

**Safe approach**: Verify magic bytes and force `Content-Type` based on detected type.

---

## 85. Ignoring Compiler Warnings and Static Analysis

**Pitfall**: Dismissing `-Wall`, `-Werror`, or linter/security findings.

**Why it is dangerous**: Warnings often indicate undefined behavior or security issues.

**Safe approach**: Treat security findings as blockers; use pre-commit hooks and CI gates.

---

## 86. Storing Unencrypted Sensitive Data Locally

**Pitfall**: Saving PII to localStorage, cookies, or mobile app storage without encryption.

**Safe approach**: Minimize stored data; encrypt at rest with platform keychain/Keystore.

---

## 87. Insecure Broadcast Receivers (Android)

**Pitfall**: Exported receivers that handle sensitive actions without permissions.

**Safe approach**: Set `android:exported="false"` or require permissions.

---

## 88. iOS App Transport Security Misconfiguration

**Pitfall**: Disabling ATS globally to support insecure endpoints.

**Safe approach**: Keep ATS enabled; whitelist only specific secure domains if necessary.

---

## 89. Hard-Coded Cryptographic Keys in Mobile Apps

**Pitfall**: Embedding keys in app binaries.

**Why it is dangerous**: Keys can be extracted via reverse engineering.

**Safe approach**: Use server-side operations or platform secure enclaves; keys should not ship with the app.

---

## 90. Insecure Deep Links / URL Schemes

**Pitfall**: Deep links that trigger sensitive actions without validation.

**Safe approach**: Validate deep-link parameters, require user confirmation, and enforce authn/authz.

---

## 91. Race Conditions in File Creation

**Pitfall**: Creating a file if it does not exist without atomic checks.

**Why it is dangerous**: Symlink attacks and overwrites.

**Safe approach**: Use `O_CREAT | O_EXCL` or platform-specific atomic APIs; validate paths.

---

## 92. Unvalidated Redirects in OAuth

**Pitfall**: Allowing arbitrary `redirect_uri`.

**Why it is dangerous**: Token theft via malicious redirect.

**Safe approach**: Pre-register and exact-match redirect URIs.

---

## 93. Weak TOTP Implementation

**Pitfall**: Not validating time window or allowing reuse.

**Safe approach**: Use standard libraries, allow small clock skew, and mark codes used to prevent replay.

---

## 94. Insecure API Key Distribution

**Pitfall**: Sending API keys to client-side code.

**Why it is dangerous**: Keys are easily extracted.

**Safe approach**: Proxy requests through your backend; use scoped, rotatable keys only for server-to-server.

---

## 95. Over-Reliance on WAF

**Pitfall**: Treating a WAF as the primary defense.

**Why it is dangerous**: WAFs can be bypassed and do not fix underlying flaws.

**Safe approach**: Build secure code first; use WAF as a monitoring and delay layer.

---

## 96. Ignoring Side Channels

**Pitfall**: Comparing HMACs with `==`, branching on secret values, or caching based on secrets.

**Safe approach**: Use constant-time operations, avoid secret-dependent branches, and pad responses.

---

## 97. Insecure Handling of Compressed Archives

**Pitfall**: Decompressing user-supplied archives without size/depth limits.

**Why it is dangerous**: Zip bombs and path traversal.

**Safe approach**: Limit total extracted size and file count, validate paths, and scan contents.

---

## 98. Exposing Internal Ports and Services

**Pitfall**: Binding services to `0.0.0.0` instead of `127.0.0.1`.

**Why it is dangerous**: Management interfaces exposed to the network.

**Safe approach**: Bind admin endpoints to localhost or internal interfaces; require authentication.

---

## 99. Insecure Default Passwords

**Pitfall**: Shipping products with default credentials.

**Safe approach**: Force password change on first use; generate random initial passwords.

---

## 100. Not Learning from Incidents

**Pitfall**: Treating security incidents as one-off fixes without root-cause analysis.

**Safe approach**: Conduct blameless post-mortems, update controls, train team, and share lessons.

---

## 101. Summary: Most Costly Mistakes

1. Trusting user input.
2. Weak or missing authentication/authorization.
3. Hard-coded or leaked secrets.
4. Vulnerable dependencies.
5. Insecure deserialization.
6. Missing input/output handling.
7. Over-privileged services.
8. Insufficient logging and monitoring.
9. Poor key management.
10. Lack of incident response preparation.

Avoid these and you have eliminated the majority of high-impact vulnerabilities.


---

## 102. Insecure Use of `subprocess` in Python

**Pitfall**: Using `shell=True` with user input.

```python
# VULNERABLE
subprocess.run(f"convert {user_path} output.png", shell=True)
```

**Safe approach**: Pass arguments as a list.

```python
subprocess.run(["convert", user_path, "output.png"], check=True)
```

---

## 103. Dangerous Defaults in Template Engines

**Pitfall**: Disabling auto-escaping or using `| safe` filter indiscriminately.

**Safe approach**: Keep auto-escaping on; explicitly mark only known-safe strings.

---

## 104. Logging Injection / Log Forging

**Pitfall**: Writing user input directly to logs without sanitization.

**Why it is dangerous**: Newline characters can forge log entries; attackers hide tracks or trigger false alerts.

**Safe approach**: Strip newlines, encode special characters, use structured logging.

---

## 105. Unchecked File Decompression

**Pitfall**: Extracting archives without limits.

**Why it is dangerous**: Zip bombs, path traversal, and excessive disk use.

**Safe approach**: Limit total size, file count, and nesting depth; validate paths.

---

## 106. Insecure Temporary Files

**Pitfall**: Using predictable temp file names.

```python
# VULNERABLE
path = "/tmp/report-" + user_id
```

**Safe approach**: Use `tempfile.mkstemp` or `NamedTemporaryFile`.

---

## 107. Unsafe Reflection in Java

**Pitfall**: `Class.forName(userInput).newInstance()`.

**Safe approach**: Allowlist allowed classes; avoid reflection based on user input.

---

## 108. Dynamic SQL Sorting

**Pitfall**: Concatenating `ORDER BY` column from user input.

**Safe approach**: Allowlist columns and directions.

```python
ALLOWED_COLUMNS = {"created_at", "name", "id"}
ALLOWED_DIRECTIONS = {"asc", "desc"}

sort_col = request.args.get("sort", "id")
sort_dir = request.args.get("dir", "asc")
if sort_col not in ALLOWED_COLUMNS or sort_dir not in ALLOWED_DIRECTIONS:
    raise ValueError("invalid sort")
query = f"SELECT * FROM items ORDER BY {sort_col} {sort_dir}"
```

---

## 109. Insecure Cookie Name

**Pitfall**: Cookie names that leak framework or purpose.

**Safe approach**: Use generic names for session IDs; rely on attributes for security.

---

## 110. Overly Broad CORS

**Pitfall**: `Access-Control-Allow-Origin: *` for an API that uses cookies.

**Safe approach**: Allowlist origins; require credentials only when necessary.

---

## 111. Unvalidated Webhook Sources

**Pitfall**: Accepting webhooks without signature verification.

**Safe approach**: Verify HMAC or mTLS; reject unknown senders.

---

## 112. Insecure `eval` Alternatives

**Pitfall**: Using `ast.literal_eval` on untrusted data for dynamic configuration.

**Safe approach**: Use JSON/schema validation; restrict to known-safe formats.

---

## 113. Lack of Request Timeouts

**Pitfall**: HTTP or database calls without timeouts.

**Why it is dangerous**: Slow or hung dependencies cause DoS.

**Safe approach**: Always set timeouts; use circuit breakers.

---

## 114. Ignoring Certificate Validation

**Pitfall**: `verify=False` in requests or disabled certificate checks.

**Why it is dangerous**: MITM attacks.

**Safe approach**: Use proper CA bundle; pin certificates where appropriate.

---

## 115. Staging Data in Production

**Pitfall**: Using production data in staging/test environments.

**Why it is dangerous**: Expands attack surface; may violate compliance.

**Safe approach**: Use synthetic or anonymized data.

---

## 116. Insecure Direct Memory Access in C

**Pitfall**: Casting user-controlled sizes to smaller types.

```c
// VULNERABLE
char *buf = malloc(size);
memcpy(buf, user_data, size);
```

**Safe approach**: Validate size, check for integer overflow, handle allocation failure.

---

## 117. Unsafe Use of `strncpy`

**Pitfall**: Believing `strncpy` always null-terminates.

**Safe approach**: Use `strncpy` with explicit null termination or prefer `snprintf`.

---

## 118. Insecure Random IDs for Database Keys

**Pitfall**: Using `rand()` or `Math.random()` for tokens.

**Safe approach**: Use CSPRNG and sufficient length.

---

## 119. Trusting HTTP Headers for Identity

**Pitfall**: Using `X-User-Id` from client without authentication at the edge.

**Safe approach**: Terminate auth at gateway and validate headers; strip inbound spoofed headers.

---

## 120. Insecure JSONP Endpoints

**Pitfall**: Supporting JSONP for cross-origin data sharing.

**Why it is dangerous**: Bypasses Same-Origin Policy and enables data theft.

**Safe approach**: Use CORS with proper credentials handling; deprecate JSONP.

---

## 121. Insecure Use of `send_file`

**Pitfall**: Serving arbitrary files based on user input.

```python
# VULNERABLE
return send_file(f"/var/data/{filename}")
```

**Safe approach**: Validate path, use allowlists, serve from dedicated directory.

---

## 122. Missing Case Sensitivity in Authorization

**Pitfall**: Comparing usernames or roles without consistent casing.

**Safe approach**: Normalize case or use canonical identifiers from identity provider.

---

## 123. Insecure Token Storage in Mobile Apps

**Pitfall**: Storing refresh tokens in `SharedPreferences` or `NSUserDefaults`.

**Safe approach**: Use Android Keystore / iOS Keychain; encrypt at rest.

---

## 124. Hard-Coded API Keys in Client Code

**Pitfall**: Embedding Google Maps, Stripe, or other keys in frontend code.

**Safe approach**: Proxy calls through your backend; use scoped keys for client-side-only services.

---

## 125. Insecure Handling of PII in Logs

**Pitfall**: Logging full email addresses, phone numbers, or account numbers.

**Safe approach**: Redact or tokenize PII; log only what is necessary.

---

## 126. Race Condition in Account Creation

**Pitfall**: Allowing duplicate account creation due to non-atomic checks.

**Safe approach**: Use unique constraints in database; handle duplicate key errors.

---

## 127. Insecure Defaults in Object Storage

**Pitfall**: S3 buckets or Azure blobs created with public access.

**Safe approach**: Block public access by default; use IAM conditions.

---

## 128. Missing Subresource Integrity on CDN Assets

**Pitfall**: Loading third-party scripts without SRI hashes.

**Why it is dangerous**: CDN compromise leads to code execution on your site.

**Safe approach**: Add integrity hashes and crossorigin attributes.

---

## 129. Insecure Password Reset Link Delivery

**Pitfall**: Sending reset links over HTTP or with long expiry.

**Safe approach**: HTTPS only, short expiry, single-use, invalidate on password change.

---

## 130. Trusting Client-Provided Timestamps

**Pitfall**: Using `client_timestamp` for ordering or audit.

**Safe approach**: Use server-generated timestamps; treat client time as advisory.

---

## 131. Insecure Handling of API Keys in Query Parameters

**Pitfall**: `?api_key=...` in URLs.

**Why it is dangerous**: Keys appear in browser history, server logs, and referrer headers.

**Safe approach**: Use `Authorization` header.

---

## 132. Missing Encryption for Backups

**Pitfall**: Unencrypted database or disk backups.

**Safe approach**: Encrypt backups; manage keys separately; test restores.

---

## 133. Insecure Use of `fork` and `exec`

**Pitfall**: Forking processes that inherit file descriptors or environment.

**Safe approach**: Close unnecessary file descriptors; sanitize environment; use `execve` with explicit args.

---

## 134. Insecure Defaults in Docker Compose

**Pitfall**: Exposing ports to all interfaces or using default credentials.

**Safe approach**: Bind sensitive services to localhost; use secrets; define networks.

---

## 135. Insecure Handling of Base64

**Pitfall**: Confusing Base64 with encryption.

**Safe approach**: Base64 is encoding, not confidentiality; encrypt sensitive data before encoding.

---

## 136. Missing Origin Validation in WebSockets

**Pitfall**: Accepting WebSocket connections from any origin.

**Safe approach**: Validate `Origin` header against allowlist.

---

## 137. Insecure Use of `String.format` for SQL

**Pitfall**: Using Java `String.format` to build SQL.

**Safe approach**: Use `PreparedStatement`.

---

## 138. Trusting User-Agent for Security Decisions

**Pitfall**: Blocking or allowing based on `User-Agent`.

**Safe approach**: User-Agent is easily spoofed; use it only for analytics or mild throttling.

---

## 139. Insecure Handling of TOTP Seeds

**Pitfall**: Storing TOTP secrets in plaintext.

**Safe approach**: Encrypt seeds at rest with a key from KMS/HSM.

---

## 140. Insecure File Permissions

**Pitfall**: World-readable private keys or config files.

**Safe approach**: Set `0600` for keys, `0700` for directories; use ACLs minimally.

---

## 141. Missing Output Encoding in APIs

**Pitfall**: Returning user data as raw JSON and relying on clients to handle safely.

**Safe approach**: API responses are less vulnerable to XSS but still validate and sanitize; if rendered in HTML, encode on output.

---

## 142. Insecure Pagination Identifiers

**Pitfall**: Using sequential integer offsets that can be enumerated.

**Safe approach**: Use opaque cursors or UUIDs and enforce authorization.

---

## 143. Insecure Use of `sudo` in Scripts

**Pitfall**: Scripts that run `sudo` with fixed passwords or broad permissions.

**Safe approach**: Use least-privilege sudoers entries; avoid password automation.

---

## 144. Insecure Cloud Metadata Access

**Pitfall**: Application code can reach `169.254.169.254`.

**Safe approach**: Block link-local egress; use IMDSv2 with hop limit 1.

---

## 145. Insecure Handling of JWT Refresh Tokens

**Pitfall**: Storing refresh tokens without rotation or expiration.

**Safe approach**: Rotate refresh tokens, detect reuse, set reasonable expiry.

---

## 146. Insecure Use of `memcpy_s` Without Checking Size

**Pitfall**: Bounded copy functions do not prevent all overflows if size is wrong.

**Safe approach**: Validate destination size and source size before copying.

---

## 147. Insecure Handling of Wildcard Certificates

**Pitfall**: Sharing a wildcard cert across many systems of different trust levels.

**Safe approach**: Scope wildcards narrowly; use ACME per-host certificates.

---

## 148. Insecure Use of `Document.domain`

**Pitfall**: Relaxing `document.domain` to allow cross-subdomain communication.

**Why it is dangerous**: Weakens same-origin protections.

**Safe approach**: Use `postMessage` with origin validation.

---

## 149. Missing Sanitization of SVG Uploads

**Pitfall**: Treating SVG as a safe image format.

**Why it is dangerous**: SVG can contain JavaScript.

**Safe approach**: Sanitize SVG, serve with `Content-Security-Policy: default-src 'none'`, or rasterize.

---

## 150. Final Pitfalls Wisdom

Most vulnerabilities arise from:

- Trusting input
- Forgetting authz
- Misusing crypto
- Leaking secrets
- Running unsafe code
- Ignoring edge cases

When in doubt, deny, validate, encode, and log.

End of pitfalls.


---

## 151. Insecure Use of `curl` in Scripts

**Pitfall**: `curl $URL` with user-controlled URL and `-k`.

**Safe approach**: Quote URL, verify TLS, use `--fail --silent --show-error`.

---

## 152. Insecure `git clone` of Untrusted Repos

**Pitfall**: Running `git clone` and executing build scripts without review.

**Why it is dangerous**: Malicious `.gitattributes`, hooks, or build scripts can run code.

**Safe approach**: Review repository, disable hooks, run builds in isolated environment.

---

## 153. Missing Canonicalization

**Pitfall**: Validating a path before resolving `..` or symbolic links.

**Safe approach**: Resolve absolute paths and verify they remain within base directory.

---

## 154. Trusting File Timestamps

**Pitfall**: Using `mtime` or `ctime` for security decisions.

**Safe approach**: Use cryptographic signatures or hashes for integrity.

---

## 155. Insecure `tmpnam` and `mktemp`

**Pitfall**: Using predictable temporary file names.

**Safe approach**: Use `mkstemp`, `tempfile`, or secure platform APIs.

---

## 156. Unsafe Signal Handling

**Pitfall**: Non-reentrant functions in signal handlers.

**Safe approach**: Set flags in signal handlers and handle in main loop.

---

## 157. Insecure Fork Without exec

**Pitfall**: Forking a process and sharing memory/descriptors.

**Safe approach**: Use `fork` + `exec` with sanitized environment.

---

## 158. Race Condition in File Existence Check

```python
# VULNERABLE
if not os.path.exists(path):
    open(path, 'w').write(data)
```

**Safe approach**: Use `O_CREAT | O_EXCL` or atomic rename operations.

---

## 159. Insecure Search Path

**Pitfall**: Current directory or writable paths in `PATH`.

**Safe approach**: Set explicit `PATH` and avoid `.` in production.

---

## 160. Insecure Library Loading

**Pitfall**: `LD_PRELOAD` or DLL search order hijacking.

**Safe approach**: Restrict library paths, sign libraries, validate integrity.

---

## 161. Information Leakage via HTTP Methods

**Pitfall**: Different responses for `OPTIONS`, `TRACE`, or `DEBUG` methods.

**Safe approach**: Disable unnecessary methods; return consistent errors.

---

## 162. Insecure `TRACE` Method

**Pitfall**: Leaving `TRACE` enabled, which can aid XSS (XST).

**Safe approach**: Disable TRACE at web server level.

---

## 163. Insecure `OPTIONS` Responses

**Pitfall**: `Allow` header listing dangerous methods.

**Safe approach**: Return minimal allowed methods.

---

## 164. Missing Cache-Control on Private Data

**Pitfall**: Sensitive pages cached by browsers or proxies.

**Safe approach**: `Cache-Control: no-store, private`.

---

## 165. Insecure Handling of ETags

**Pitfall**: ETags that leak internal state or inode numbers.

**Safe approach**: Generate opaque ETags based on content hash.

---

## 166. Insecure Compression (BREACH)

**Pitfall**: Combining HTTP compression with reflected user input and secrets.

**Safe approach**: Use CSRF tokens per request, disable compression for sensitive pages, or implement length hiding.

---

## 167. Insecure Use of ` autocomplete`

**Pitfall**: Enabling autocomplete on sensitive fields.

**Safe approach**: Use `autocomplete="off"` or `autocomplete="new-password"` as appropriate.

---

## 168. Missing Subresource Integrity

**Pitfall**: Loading third-party scripts without integrity hashes.

**Safe approach**: Compute and pin SRI hashes.

---

## 169. Insecure Handling of File Downloads

**Pitfall**: Serving files with `Content-Disposition: inline`.

**Safe approach**: Use `attachment` for untrusted uploads.

---

## 170. Insecure Content-Types

**Pitfall**: Serving HTML as `text/plain` or vice versa.

**Safe approach**: Set correct `Content-Type` for every response.

---

## 171. Insecure Use of `innerHTML`

**Pitfall**: Setting `element.innerHTML = userInput`.

**Safe approach**: Use `textContent` or sanitized HTML.

---

## 172. Insecure `postMessage` Usage

**Pitfall**: Not validating `event.origin`.

**Safe approach**: Always check origin and validate message format.

---

## 173. Insecure Web Storage

**Pitfall**: Storing sensitive tokens in `localStorage`.

**Safe approach**: Use `HttpOnly` cookies or memory-bound closures.

---

## 174. Insecure Service Worker

**Pitfall**: Service worker that caches arbitrary responses.

**Safe approach**: Validate URLs and scopes; update service workers securely.

---

## 175. Insecure Manifest File

**Pitfall**: Overly permissive web app manifest.

**Safe approach**: Restrict scope and start_url.

---

## 176. Insecure Payment Integration

**Pitfall**: Handling raw card data without PCI compliance.

**Safe approach**: Use tokenization services (Stripe, Braintree) and never store CVV.

---

## 177. Insecure Use of CAPTCHA

**Pitfall**: CAPTCHA as the only defense against bots.

**Safe approach**: Layer with rate limiting, device signals, and behavioral analysis.

---

## 178. Invisible CAPTCHA Bypass

**Pitfall**: Client-side CAPTCHA verification only.

**Safe approach**: Always verify server-side.

---

## 179. Insecure Session Timeout

**Pitfall**: Sessions that never expire or expire only on browser close.

**Safe approach**: Set absolute and idle timeouts; require re-auth for sensitive actions.

---

## 180. Insecure Concurrent Session Handling

**Pitfall**: Allowing unlimited concurrent sessions.

**Safe approach**: Limit sessions per user; notify on new sessions.

---

## 181. Insecure Device Authorization

**Pitfall**: Authorizing devices without user confirmation.

**Safe approach**: Require explicit user approval and display device details.

---

## 182. Insecure Backup Key Storage

**Pitfall**: Storing backup encryption keys with the primary key.

**Safe approach**: Use offline or geographically separated key storage.

---

## 183. Insecure Key Recovery

**Pitfall**: Weak key recovery questions or procedures.

**Safe approach**: Use multi-channel verification and audit recovery events.

---

## 184. Insecure Data Masking

**Pitfall**: Masking only part of sensitive data while logging the rest.

**Safe approach**: Redact or tokenize; do not rely on partial masking.

---

## 185. Insecure Use of `sudo` Without Password

**Pitfall**: `ALL=(ALL) NOPASSWD: ALL`.

**Safe approach**: Restrict commands and require authentication.

---

## 186. Insecure NFS / SMB Shares

**Pitfall**: World-writable network shares.

**Safe approach**: Restrict access, enable authentication, audit shares.

---

## 187. Insecure SNMP Configuration

**Pitfall**: Default community strings like `public`/`private`.

**Safe approach**: Use SNMPv3 with auth+priv; disable SNMPv1/v2c.

---

## 188. Insecure Telnet / FTP

**Pitfall**: Using cleartext management protocols.

**Safe approach**: Use SSH and SFTP/FTPS.

---

## 189. Insecure Time Synchronization

**Pitfall**: Skewed clocks breaking TLS, OTP, and audit logs.

**Safe approach**: Use NTP with authentication; monitor clock drift.

---

## 190. Insecure Logging of Command Lines

**Pitfall**: Process lists showing passwords in arguments.

**Safe approach**: Pass secrets via files or environment; avoid command-line args.

---

## 191. Insecure Use of `systemd` Timers

**Pitfall**: Running jobs as root unnecessarily.

**Safe approach**: Run with least-privilege user; sandbox service.

---

## 192. Insecure Cron Jobs

**Pitfall**: World-readable cron files containing credentials.

**Safe approach**: Store credentials in restricted files or vault; validate scripts.

---

## 193. Insecure Log Rotation

**Pitfall**: Logs readable by all users after rotation.

**Safe approach**: Set restrictive permissions on rotated logs.

---

## 194. Insecure Virtual Machine Snapshots

**Pitfall**: Snapshots containing secrets or unencrypted memory.

**Safe approach**: Encrypt snapshots; restrict access; purge old snapshots.

---

## 195. Insecure Container Registry

**Pitfall**: Public registry with private images.

**Safe approach**: Use private registries, RBAC, image signing, and scanning.

---

## 196. Insecure Use of `kubectl` Contexts

**Pitfall**: Using production credentials on personal machines.

**Safe approach**: Use short-lived tokens, PAM, and audit `kubectl` access.

---

## 197. Insecure Terraform State

**Pitfall**: Terraform state files containing secrets in plain text.

**Safe approach**: Encrypt state at rest, restrict backend access, use remote state locking.

---

## 198. Insecure Ansible Vault Password

**Pitfall**: Storing vault password in plaintext files.

**Safe approach**: Use password managers or KMS integration.

---

## 199. Insecure PagerDuty / Slack Webhooks

**Pitfall**: Webhooks without signature verification.

**Safe approach**: Verify signatures and restrict source IPs.

---

## 200. Final Summary: Pitfalls to Avoid at All Costs

1. SQL injection
2. XSS
3. Broken authn/authz
4. Insecure deserialization
5. Sensitive data exposure
6. XML external entities
7. Broken access control
8. Security misconfiguration
9. Cross-site request forgery
10. Using components with known vulnerabilities

Mastering these prevents the majority of security incidents.

End of pitfalls.
