# Security — Patterns, Recipes, and Reusable Templates

This file contains idiomatic, production-ready patterns for building secure software. Use these as starting points for implementation and code review.

---

## 1. Layered Input Validation Pattern

Apply validation at every trust boundary: client (UX), API gateway, controller, service, and database.

```python
from pydantic import BaseModel, Field, validator
import re

class CreateOrderRequest(BaseModel):
    product_id: str = Field(..., min_length=1, max_length=64)
    quantity: int = Field(..., ge=1, le=100)
    coupon: str | None = Field(None, max_length=32)

    @validator('product_id')
    def product_id_format(cls, v):
        if not re.fullmatch(r'[A-Za-z0-9_-]+', v):
            raise ValueError('invalid product_id')
        return v

    @validator('coupon')
    def coupon_format(cls, v):
        if v is not None and not re.fullmatch(r'[A-Z0-9]+', v):
            raise ValueError('invalid coupon')
        return v
```

Usage:

```python
def create_order(raw_payload: dict, current_user: User):
    req = CreateOrderRequest(**raw_payload)
    # business authorization
    authorize(current_user, "order:create", req.product_id)
    # semantic validation
    if not product_exists(req.product_id):
        raise ValueError("product not found")
    return order_service.create(req)
```

---

## 2. Allowlist Regular Expression Pattern

Anchor regex at start and end; avoid overly permissive wildcards.

```python
import re

VALIDATORS = {
    "zip": re.compile(r"^\d{5}(-\d{4})?$"),
    "us_state": re.compile(r"^(A[LKZR]|C[AOT]|D[EC]|FL|GA|HI|I[ADLN]|K[SY]|LA|M[ADEINOST]|N[CDEHJMVY]|O[HKR]|PA|RI|S[CD]|T[NX]|UT|V[AT]|W[AIVY])$"),
    "uuid": re.compile(r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$"),
    "email_local": re.compile(r"^[a-zA-Z0-9.!#$%&'*+/=?^_`{|}~-]+@[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?(?:\.[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?)*$"),
}

def validate(field: str, value: str) -> bool:
    pattern = VALIDATORS.get(field)
    if not pattern:
        return False
    return bool(pattern.fullmatch(value))
```

---

## 3. Parameterized Query Pattern

```python
import sqlite3

def get_user_by_email(conn: sqlite3.Connection, email: str):
    cursor = conn.cursor()
    cursor.execute(
        "SELECT id, email FROM users WHERE email = ? AND active = ?",
        (email, True),
    )
    return cursor.fetchone()
```

Node.js example:

```js
const user = await db.query(
  'SELECT id, email FROM users WHERE email = ? AND active = ?',
  [email, true]
);
```

Go example:

```go
var id int
err := db.QueryRow(
    "SELECT id FROM users WHERE email = ? AND active = ?",
    email, true,
).Scan(&id)
```

---

## 4. Context-Aware Output Encoding Pattern

```python
import html
import json
from urllib.parse import quote

class SafeRenderer:
    @staticmethod
    def html(text: str) -> str:
        return html.escape(text, quote=True)

    @staticmethod
    def html_attr(text: str) -> str:
        return html.escape(text, quote=True)

    @staticmethod
    def js(text: str) -> str:
        return json.dumps(text, ensure_ascii=True)

    @staticmethod
    def url(text: str) -> str:
        return quote(text, safe='')
```

Template usage:

```html
<div data-name="{{ SafeRenderer.html_attr(user.name) }}">{{ SafeRenderer.html(user.bio) }}</div>
<script>
  const userName = {{ SafeRenderer.js(user.name) }};
</script>
```

---

## 5. Secure Password Storage Pattern

```python
from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError

ph = PasswordHasher(
    time_cost=3,
    memory_cost=65536,
    parallelism=1,
    hash_len=32,
    salt_len=16,
)

def hash_password(plaintext: str) -> str:
    return ph.hash(plaintext)

def verify_password(stored_hash: str, plaintext: str) -> bool:
    try:
        ph.verify(stored_hash, plaintext)
        return True
    except VerifyMismatchError:
        return False
```

---

## 6. Envelope Encryption Pattern

```python
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
import secrets

# KEK managed by KMS/HSM
KEK = AESGCM.generate_key(bit_length=256)
kek_cipher = AESGCM(KEK)

def encrypt_data(plaintext: bytes, associated_data: bytes) -> dict:
    dek = AESGCM.generate_key(bit_length=256)
    aesgcm = AESGCM(dek)
    nonce = secrets.token_bytes(12)
    ciphertext = aesgcm.encrypt(nonce, plaintext, associated_data)
    encrypted_dek = kek_cipher.encrypt(secrets.token_bytes(12), dek, b"")
    return {
        "ciphertext": ciphertext,
        "nonce": nonce,
        "encrypted_dek": encrypted_dek,
        "aad": associated_data,
    }

def decrypt_data(bundle: dict) -> bytes:
    dek = kek_cipher.decrypt(bundle["encrypted_dek"][:12], bundle["encrypted_dek"][12:], b"")
    aesgcm = AESGCM(dek)
    return aesgcm.decrypt(bundle["nonce"], bundle["ciphertext"], bundle["aad"])
```

---

## 7. JWT Issuance and Validation Pattern

```python
import jwt
import secrets
from datetime import datetime, timedelta, timezone

SECRET = secrets.token_bytes(64)  # in production load from vault
ALGORITHM = "HS256"
ISSUER = "my-app"
AUDIENCE = "my-api"

class TokenService:
    def issue(self, user_id: str, roles: list[str]) -> str:
        now = datetime.now(timezone.utc)
        payload = {
            "sub": user_id,
            "iss": ISSUER,
            "aud": AUDIENCE,
            "iat": now,
            "exp": now + timedelta(minutes=15),
            "jti": secrets.token_urlsafe(16),
            "roles": roles,
        }
        return jwt.encode(payload, SECRET, algorithm=ALGORITHM)

    def validate(self, token: str) -> dict:
        return jwt.decode(
            token,
            SECRET,
            algorithms=[ALGORITHM],
            issuer=ISSUER,
            audience=AUDIENCE,
        )
```

---

## 8. Authorization Middleware Pattern

```python
from functools import wraps
from fastapi import Request, HTTPException

class Authorizer:
    def __init__(self, policy_service):
        self.policy = policy_service

    def require(self, action: str, resource_extractor):
        def decorator(handler):
            @wraps(handler)
            async def wrapper(request: Request, *args, **kwargs):
                user = request.state.user
                resource = resource_extractor(request, kwargs)
                if not self.policy.is_allowed(user, action, resource):
                    raise HTTPException(status_code=403, detail="forbidden")
                return await handler(request, *args, **kwargs)
            return wrapper
        return decorator

# Usage
authorizer = Authorizer(policy_service)

@app.post("/projects/{project_id}/deploy")
@authorizer.require("deploy", lambda req, kwargs: kwargs["project_id"])
async def deploy_project(request: Request, project_id: str):
    ...
```

---

## 9. ABAC Policy Pattern (Pseudo-code)

```python
def can_access_document(user, document, action):
    if action == "read":
        return (
            user.department == document.department
            or user.id in document.shared_with
            or user.role == "auditor" and user.is_business_hours()
        )
    if action == "delete":
        return user.id == document.owner_id and user.role != "guest"
    return False
```

Document the policy in code and test all branches with unit tests.

---

## 10. Secure File Upload Pattern

```python
import hashlib
import mimetypes
import uuid
from pathlib import Path
from werkzeug.utils import secure_filename

ALLOWED_TYPES = {"image/jpeg", "image/png", "image/gif"}
MAX_SIZE = 5 * 1024 * 1024
UPLOAD_DIR = Path("/var/uploads")

def save_upload(file_storage) -> str:
    if file_storage.content_length and file_storage.content_length > MAX_SIZE:
        raise ValueError("file too large")
    # Read and verify magic bytes
    data = file_storage.read(MAX_SIZE + 1)
    if len(data) > MAX_SIZE:
        raise ValueError("file too large")
    detected = magic.from_buffer(data, mime=True)  # python-magic
    if detected not in ALLOWED_TYPES:
        raise ValueError("file type not allowed")
    ext = mimetypes.guess_extension(detected) or ".bin"
    filename = f"{uuid.uuid4()}{ext}"
    dest = UPLOAD_DIR / filename
    dest.write_bytes(data)
    return str(dest)
```

---

## 11. OAuth 2.1 + OIDC Integration Pattern

For a web backend:

1. Register as a confidential client; obtain client ID and client secret.
2. Redirect user to the authorization server with `response_type=code`, `scope=openid profile email`, `code_challenge` (PKCE), and a state nonce.
3. Validate `state` on callback.
4. Exchange code for tokens over TLS.
5. Validate ID Token signature and claims.
6. Issue local session; store tokens securely.
7. Use access token to call resource server APIs; refresh before expiry.

Python pseudo-code:

```python
from authlib.integrations.starlette_client import OAuth

oauth = OAuth()
oauth.register(
    name="oidc",
    server_metadata_url="https://auth.example.com/.well-known/openid-configuration",
    client_id=CLIENT_ID,
    client_secret=CLIENT_SECRET,
    client_kwargs={"scope": "openid email profile"},
)

@app.get("/login")
async def login(request: Request):
    redirect_uri = request.url_for("auth_callback")
    return await oauth.oidc.authorize_redirect(request, redirect_uri)

@app.get("/callback")
async def auth_callback(request: Request):
    token = await oauth.oidc.authorize_access_token(request)
    user = token.get("userinfo")
    session["user_id"] = user["sub"]
    return RedirectResponse("/")
```

---

## 12. API Rate Limiting Pattern

```python
import time
from collections import defaultdict

class TokenBucket:
    def __init__(self, rate: float, capacity: int):
        self.rate = rate
        self.capacity = capacity
        self.tokens = capacity
        self.last = time.monotonic()

    def allow(self) -> bool:
        now = time.monotonic()
        self.tokens = min(self.capacity, self.tokens + (now - self.last) * self.rate)
        self.last = now
        if self.tokens >= 1:
            self.tokens -= 1
            return True
        return False

# Per-client buckets
buckets = defaultdict(lambda: TokenBucket(rate=1, capacity=5))

def is_rate_limited(client_id: str) -> bool:
    return not buckets[client_id].allow()
```

Production: use Redis with expiration (e.g., sliding window or token bucket in Lua).

---

## 13. Secret Injection Pattern

At runtime, load secrets from a vault or orchestrator secrets; never from source.

```python
import os
from pathlib import Path

def load_secret(name: str) -> str:
    file_env = f"{name}_FILE"
    if file_env in os.environ:
        return Path(os.environ[file_env]).read_text().strip()
    value = os.environ.get(name)
    if not value:
        raise RuntimeError(f"secret {name} not provided")
    return value

DB_PASSWORD = load_secret("DB_PASSWORD")
```

Kubernetes example:

```yaml
env:
  - name: DB_PASSWORD
    valueFrom:
      secretKeyRef:
        name: app-secrets
        key: db-password
```

---

## 14. Secure CI/CD Pipeline Pattern

1. Require signed commits and branch protection rules.
2. Use least-privilege CI credentials; no long-lived secrets in CI variables.
3. Pin action versions by SHA, not tag.
4. Scan dependencies and secrets on every PR.
5. Run SAST and unit tests; fail on critical/high findings.
6. Build in ephemeral, isolated environments; produce SBOM.
7. Sign artifacts and container images.
8. Scan container images before deploy.
9. Deploy through automated promotion with environment gates.
10. Monitor post-deploy with runtime security and rollback capability.

GitHub Actions snippet:

```yaml
jobs:
  security:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: pypa/pip-audit@v1
      - uses: returntocorp/semgrep-action@v1
        with:
          config: >-
            p/security-audit
      - run: trivy fs --severity HIGH,CRITICAL .
```

---

## 15. Immutable Infrastructure Pattern

- Build machine images / container images from version-controlled definitions.
- No SSH or manual changes in production; redeploy to update.
- Store configuration and secrets outside the image.
- Use blue/green or canary deployments.
- Roll back automatically on health check failure.

---

## 16. Defense in Depth Web Stack

```
User
  → WAF / CDN (DDoS, bot, known signatures)
  → API Gateway (TLS, rate limit, auth, routing)
  → Application (input validation, authz, business logic)
  → Service Mesh (mTLS, authz)
  → Database (least privilege, encryption at rest)
  → Audit / SIEM (logs, alerts)
```

Each layer provides independent protection.

---

## 17. Zero Trust Service-to-Service Pattern

- Every service has a workload identity (SPIFFE/SPIRE, AWS IAM roles, Kubernetes service accounts).
- Services authenticate each other via mTLS.
- Authorization enforced at every hop using policy engine (OPA, Istio authz).
- Short-lived tokens/certificates rotated automatically.
- Network segmentation restricts blast radius.

---

## 18. Secure Code Review Checklist Pattern

For each changed file, ask:

- [ ] Are all inputs validated and typed?
- [ ] Are queries parameterized?
- [ ] Is output encoded for the right context?
- [ ] Are authn/authz checks present and correct?
- [ ] Are secrets hard-coded or logged?
- [ ] Are errors handled without sensitive disclosure?
- [ ] Are dependencies added from trusted sources and pinned?
- [ ] Are race conditions possible?
- [ ] Are cryptographic operations using safe algorithms?
- [ ] Are file paths validated and sandboxed?
- [ ] Are new endpoints covered by tests?

---

## 19. Threat Modeling Recipe

1. Draw a data-flow diagram of the feature.
2. Identify assets (data, credentials, compute, reputation).
3. Identify trust boundaries (client, API, database, third party).
4. Apply STRIDE to each component/data flow.
5. Document threats, risk rating, and mitigations.
6. Track mitigations as work items and verify in code review.

Template:

```markdown
## Feature: X
### Assets
- user PII
- session tokens
### Trust Boundaries
- browser ↔ API (untrusted)
- API ↔ database (trusted)
### Threats
| ID | Component | STRIDE | Threat | Mitigation | Owner |
|----|-----------|--------|--------|------------|-------|
| T1 | Login API | Spoofing | Credential stuffing | Rate limiting, MFA | @dev |
```

---

## 20. Incident Response Runbook Pattern

```markdown
# Incident: suspected account takeover
## Detection
- Alert: multiple failed logins followed by successful login from new device/location.
## Triage
1. Confirm alert with SIEM logs.
2. Identify affected user IDs and timestamps.
## Containment
1. Force password reset and revoke active sessions for affected users.
2. Enable MFA if not already active.
## Eradication
1. Search for signs of lateral movement or data exfiltration.
## Recovery
1. Restore from known-good backups if systems were modified.
## Communication
1. Notify security team; prepare customer notice if PII accessed.
```

---

## 21. Secure Session Pattern

```python
import secrets
from datetime import datetime, timedelta, timezone

class SessionStore:
    def create(self, user_id: str) -> str:
        token = secrets.token_urlsafe(32)
        self.db.setex(
            f"session:{token}",
            timedelta(hours=8),
            {"user_id": user_id, "created": datetime.now(timezone.utc).isoformat()},
        )
        return token

    def get(self, token: str):
        return self.db.get(f"session:{token}")

    def revoke(self, token: str):
        self.db.delete(f"session:{token}")
```

Cookie attributes:

```http
Set-Cookie: session=<token>; HttpOnly; Secure; SameSite=Strict; Path=/; Max-Age=28800
```

---

## 22. Secure Logging Pattern

```python
import logging
import copy

class SafeLogger:
    SENSITIVE_KEYS = {"password", "token", "secret", "ssn", "credit_card", "cvv"}

    @classmethod
    def sanitize(cls, record: dict) -> dict:
        safe = copy.deepcopy(record)
        for key in list(safe.keys()):
            if any(s in key.lower() for s in cls.SENSITIVE_KEYS):
                safe[key] = "***"
        return safe

logger = logging.getLogger("app")

def log_event(user_id: str, action: str, details: dict):
    logger.info("security_event", extra={
        "user_id": user_id,
        "action": action,
        "details": SafeLogger.sanitize(details),
    })
```

---

## 23. Key Rotation Pattern

1. Generate new key; mark it as primary for encryption.
2. Keep old keys available for decryption.
3. Tag ciphertext with key ID/version.
4. Re-encrypt data on read or via background job.
5. After all data is re-encrypted and grace period passes, retire old key.

```python
def encrypt_with_version(plaintext: bytes, key_manager) -> dict:
    key = key_manager.current_key()
    ciphertext = key.cipher.encrypt(plaintext)
    return {"ciphertext": ciphertext, "key_id": key.id}

def decrypt_with_version(bundle: dict, key_manager) -> bytes:
    key = key_manager.get_key(bundle["key_id"])
    return key.cipher.decrypt(bundle["ciphertext"])
```

---

## 24. Subresource Integrity (SRI) Pattern

Include hashes for third-party scripts/styles:

```html
<script src="https://cdn.example.com/lib.js"
        integrity="sha384-..."
        crossorigin="anonymous"></script>
```

Generate hash:

```bash
openssl dgst -sha384 -binary file.js | openssl base64 -A
```

---

## 25. Content Security Policy Pattern

Nonce-based strict CSP:

```python
import secrets
from fastapi import Request

def set_csp_headers(response, request: Request):
    nonce = secrets.token_urlsafe(16)
    request.state.csp_nonce = nonce
    response.headers["Content-Security-Policy"] = (
        f"default-src 'self'; "
        f"script-src 'nonce-{nonce}' 'strict-dynamic'; "
        f"style-src 'self'; "
        f"img-src 'self' data:; "
        f"connect-src 'self'; "
        f"font-src 'self'; "
        f"object-src 'none'; "
        f"base-uri 'none'; "
        f"frame-ancestors 'none'; "
        f"form-action 'self';"
    )
    return response
```

Template:

```html
<script nonce="{{ request.state.csp_nonce }}">
  console.log("allowed");
</script>
```

---

## 26. CORS Safe Configuration Pattern

Do not use `Access-Control-Allow-Origin: *` with credentials.

```python
from fastapi.middleware.cors import CORSMiddleware

origins = ["https://app.example.com", "https://admin.example.com"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["Authorization", "Content-Type"],
    max_age=600,
)
```

Mirror origin only if absolutely necessary and validate against allowlist:

```python
def allowed_origin(request_origin: str) -> str | None:
    return request_origin if request_origin in origins else None
```

---

## 27. Secrets Rotation Pattern

1. Generate new secret in vault.
2. Deploy to consumers with dual-read support (try new, fallback old).
3. Update producers to write with new secret.
4. Monitor for old-secret usage.
5. Revoke old secret after grace period.

---

## 28. Micro-segmentation Pattern

- Group services by sensitivity and function.
- Default-deny network policies between groups.
- Allow only required ports and protocols.
- Enforce mTLS and service identity.
- Log all allowed and denied flows.

---

## 29. Secure Defaults Pattern

When building libraries/frameworks:

- Default to the safest option (deny by default).
- Do not enable debug mode in production.
- Require explicit opt-in for dangerous features.
- Use strong algorithms by default.
- Provide clear error messages without leaking internals.

---

## 30. Vulnerability Disclosure Pattern

1. Provide a `security.txt` file at `/.well-known/security.txt`.
2. Include contact, preferred languages, policy, and acknowledgments.
3. Respond to reports promptly and set expectations.
4. Fix, test, and disclose within a coordinated timeline.
5. Credit researchers unless they prefer anonymity.

```
Contact: mailto:security@example.com
Expires: 2027-01-01T00:00:00.000Z
Preferred-Languages: en
Policy: https://example.com/security-policy
Acknowledgments: https://example.com/hall-of-fame
```

---

## 31. Secure Defaults for Error Handling

```python
from fastapi import Request, HTTPException
from fastapi.responses import JSONResponse

async def generic_exception_handler(request: Request, exc: Exception):
    # Log full traceback and request details internally
    logger.exception("unhandled exception", extra={"path": request.url.path})
    # Return generic response to client
    return JSONResponse(
        status_code=500,
        content={"detail": "internal server error"},
    )
```

---

## 32. Security Smoke Tests Pattern

Add lightweight tests to CI:

```python
def test_login_rate_limit(client):
    for _ in range(10):
        client.post("/login", json={"user": "x", "pass": "y"})
    resp = client.post("/login", json={"user": "x", "pass": "y"})
    assert resp.status_code == 429

def test_sql_injection_blocked(client):
    resp = client.get("/users", params={"name": "' OR '1'='1"})
    assert resp.status_code in (400, 422, 200)
    # verify no unexpected data leaked

def test_xss_output_encoded(client):
    client.post("/comments", json={"text": "<script>alert(1)</script>"})
    resp = client.get("/comments")
    assert "<script>" not in resp.text
```

---

## 33. Cryptography Decision Tree

| Goal | Recommended |
|------|-------------|
| Password storage | Argon2id / bcrypt / scrypt |
| Symmetric encryption | AES-256-GCM or ChaCha20-Poly1305 |
| Asymmetric encryption | RSA-OAEP 2048+ or ECIES/X25519 |
| Digital signatures | ECDSA P-256 / Ed25519 / RSA-PSS 2048+ |
| Key derivation | Argon2id, scrypt, PBKDF2-HMAC-SHA256 |
| Random tokens | CSPRNG, at least 128 bits |
| Integrity check | HMAC-SHA256 or AEAD |

---

## 34. Reusable AuthZ Helper (Python)

```python
class Policy:
    def __init__(self):
        self.rules = []

    def allow(self, predicate):
        self.rules.append(predicate)

    def is_allowed(self, user, action, resource) -> bool:
        return any(rule(user, action, resource) for rule in self.rules)

policy = Policy()
policy.allow(lambda u, a, r: a == "read" and r.owner_id == u.id)
policy.allow(lambda u, a, r: u.role == "admin")

assert policy.is_allowed(user, "read", doc)
```

---

## 35. Template for Security Requirements

For every new feature, document:

```markdown
## Security Requirements for Feature X
- Authentication: required / optional
- Authorization: roles/attributes allowed
- Data sensitivity: public / internal / confidential / restricted
- Input sources and validation rules
- Output contexts and encoding requirements
- Crypto requirements (at rest/in transit)
- Logging and audit requirements
- Third-party integrations and trust assumptions
- Threats mitigated (STRIDE references)
```

---

## 36. Security Training Pattern

- Onboarding: secure coding fundamentals, OWASP Top 10, company policies.
- Continuous: monthly security tips, new vulnerability walkthroughs.
- Role-based: red-team concepts for developers, secure architecture for leads.
- Measure: phishing simulation pass rate, time to remediate findings, scan coverage.

---

## 37. Supply Chain Verification Pattern

```bash
# Generate SBOM
syft packages dir:. -o spdx-json > sbom.spdx.json

# Scan image
trivy image --severity HIGH,CRITICAL myapp:latest

# Verify signature
cosign verify --key cosign.pub myregistry/myapp:latest
```

---

## 38. Runtime Application Self-Protection (RASP) Pattern

Where available, enable RASP to:

- Block SQL injection attempts at runtime.
- Prevent deserialization attacks.
- Detect and block anomalous behavior.
- Integrate findings with SIEM.

Use RASP as a defense-in-depth layer, not a replacement for secure coding.

---

## 39. Browser Storage Decision Matrix

| Storage | Accessible by JS | Survives tab close | Use case |
|---------|------------------|--------------------|----------|
| `HttpOnly` cookie | No | Yes | session ID, refresh token |
| `sessionStorage` | Yes | No | short-lived client state |
| `localStorage` | Yes | Yes | non-sensitive preferences |
| Closure/private var | Yes | While page loaded | access token in SPA (mitigated by fingerprint) |

Never store plaintext passwords or long-lived secrets in `localStorage`.

---

## 40. Final Security Architecture Checklist

- [ ] Identity provider separated from application database.
- [ ] AuthN at edge/gateway; authz close to data.
- [ ] Encryption in transit everywhere.
- [ ] Encryption at rest for databases, object storage, backups.
- [ ] Secrets centralized and rotated.
- [ ] PII minimized, tokenized, and access-logged.
- [ ] All changes reviewed and tested for security.
- [ ] Monitoring, alerting, and incident response ready.
- [ ] Recovery plans tested (backups, rollback, key rotation).
- [ ] Compliance requirements mapped to controls.


---

## 41. HMAC Message Authentication Pattern

Use HMAC when you need integrity + authenticity with a shared secret.

```python
import hmac
import hashlib
import secrets

SECRET = secrets.token_bytes(32)

def sign(message: bytes) -> str:
    return hmac.new(SECRET, message, hashlib.sha256).hexdigest()

def verify(message: bytes, signature: str) -> bool:
    expected = sign(message)
    return hmac.compare_digest(expected, signature)
```

Use `hmac.compare_digest` or equivalent constant-time comparison to prevent timing attacks.

---

## 42. Digital Signature Pattern

Use asymmetric signatures when different parties verify.

```python
from cryptography.hazmat.primitives.asymmetric import ed25519

private_key = ed25519.Ed25519PrivateKey.generate()
public_key = private_key.public_key()

message = b"important action"
signature = private_key.sign(message)

try:
    public_key.verify(signature, message)
    print("signature valid")
except Exception:
    print("signature invalid")
```

---

## 43. Symmetric Encryption with Associated Data Pattern

```python
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
import os

key = os.urandom(32)
aesgcm = AESGCM(key)

def encrypt(plaintext: bytes, context: bytes) -> bytes:
    nonce = os.urandom(12)
    return nonce + aesgcm.encrypt(nonce, plaintext, context)

def decrypt(ciphertext: bytes, context: bytes) -> bytes:
    nonce, ct = ciphertext[:12], ciphertext[12:]
    return aesgcm.decrypt(nonce, ct, context)
```

Never reuse a nonce with the same GCM key.

---

## 44. Secure Random Token Pattern

```python
import secrets

def generate_token(length: int = 32) -> str:
    return secrets.token_urlsafe(length)

# Example usage
reset_token = generate_token()
```

Ensure tokens have at least 128 bits of entropy for security-critical use.

---

## 45. Constant-Time Comparison Pattern

```python
import hmac

def safe_compare(a: str, b: str) -> bool:
    return hmac.compare_digest(a.encode(), b.encode())
```

```javascript
const crypto = require('crypto');
function safeCompare(a, b) {
  return crypto.timingSafeEqual(Buffer.from(a), Buffer.from(b));
}
```

```go
import "crypto/subtle"
func safeCompare(a, b string) bool {
    return subtle.ConstantTimeCompare([]byte(a), []byte(b)) == 1
}
```

---

## 46. OAuth 2.1 PKCE Client Pattern

Public clients (SPAs, mobile) must use PKCE.

```python
import secrets
import hashlib
import base64

def generate_pkce_pair():
    verifier = base64.urlsafe_b64encode(
        secrets.token_bytes(32)
    ).rstrip(b"=").decode("ascii")
    challenge = base64.urlsafe_b64encode(
        hashlib.sha256(verifier.encode()).digest()
    ).rstrip(b"=").decode("ascii")
    return verifier, challenge

verifier, challenge = generate_pkce_pair()
# Send challenge + method=S256 to authorization endpoint
# Later send verifier with token exchange
```

---

## 47. Refresh Token Rotation Pattern

```python
class RefreshTokenStore:
    def issue(self, user_id: str) -> str:
        token = secrets.token_urlsafe(32)
        self.db.setex(f"refresh:{token}", timedelta(days=7), user_id)
        return token

    def rotate(self, old_token: str) -> str | None:
        user_id = self.db.get(f"refresh:{old_token}")
        if not user_id:
            return None
        # Detect reuse: if old token is missing but was not expired, revoke family
        if self.db.sismember("revoked_refresh", old_token):
            self.revoke_family(user_id)
            return None
        self.db.sadd("revoked_refresh", old_token)
        return self.issue(user_id)
```

---

## 48. Database Least Privilege Pattern

Create separate DB users per application function:

```sql
CREATE USER app_read WITH PASSWORD '...';
GRANT SELECT ON ALL TABLES IN SCHEMA public TO app_read;

CREATE USER app_write WITH PASSWORD '...';
GRANT SELECT, INSERT, UPDATE, DELETE ON public.orders TO app_write;

CREATE USER app_migrations WITH PASSWORD '...';
GRANT ALL PRIVILEGES ON SCHEMA public TO app_migrations;
```

Application runtime uses `app_read`/`app_write`; migrations use `app_migrations`.

---

## 49. Container Hardening Pattern

Dockerfile checklist:

- Use official minimal base image.
- Pin base image digest.
- Update system packages.
- Run as non-root user.
- Copy only required files; use multi-stage builds.
- Remove package managers and shells if possible (distroless).
- Use read-only root filesystem.
- Drop all capabilities except required ones.

```dockerfile
FROM python:3.12-slim@sha256:...
RUN apt-get update && apt-get upgrade -y \
    && rm -rf /var/lib/apt/lists/*
RUN pip install --no-cache-dir -r requirements.txt
RUN groupadd -g 1000 app && useradd -u 1000 -g app -s /sbin/nologin app
COPY --chown=app:app . /app
WORKDIR /app
USER app
EXPOSE 8000
CMD ["python", "-m", "uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
```

---

## 50. Kubernetes Pod Security Pattern

```yaml
apiVersion: v1
kind: Pod
spec:
  securityContext:
    runAsNonRoot: true
    runAsUser: 1000
    runAsGroup: 1000
    fsGroup: 1000
    seccompProfile:
      type: RuntimeDefault
  containers:
    - name: app
      image: myapp:latest
      securityContext:
        allowPrivilegeEscalation: false
        readOnlyRootFilesystem: true
        capabilities:
          drop:
            - ALL
      resources:
        limits:
          memory: "512Mi"
          cpu: "500m"
```

---

## 51. Network Policy Pattern

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
---
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: allow-app-to-db
spec:
  podSelector:
    matchLabels:
      app: database
  policyTypes:
    - Ingress
  ingress:
    - from:
        - podSelector:
            matchLabels:
              app: api
      ports:
        - protocol: TCP
          port: 5432
```

---

## 52. IaC Security Scanning Pattern

```bash
# Terraform
terraform init
terraform plan -out=tfplan
terraform show -json tfplan | checkov --file -

# CloudFormation
checkov --file template.yaml

# Kubernetes manifests
kube-score score deployment.yaml
kubectl apply --dry-run=server -f deployment.yaml
```

---

## 53. SAST Integration Pattern

Run SAST in CI on every PR with rules tuned to the language:

```yaml
- name: Semgrep
  uses: returntocorp/semgrep-action@v1
  with:
    config: >-
      p/security-audit
      p/owasp-top-ten
      p/cwe-top-25
- name: Bandit
  run: bandit -r src/
- name: CodeQL
  uses: github/codeql-action/init@v3
  with:
    languages: python
- name: Autobuild
  uses: github/codeql-action/autobuild@v3
- name: Analyze
  uses: github/codeql-action/analyze@v3
```

---

## 54. DAST Integration Pattern

Run DAST against a deployed non-production environment after functional tests:

```yaml
- name: OWASP ZAP Baseline Scan
  uses: zaproxy/action-baseline@v0.12.0
  with:
    target: 'https://staging.example.com'
    rules_file_name: '.zap/rules.tsv'
```

---

## 55. Secrets Scanning Pattern

Prevent commits and scan history:

```yaml
repos:
  - repo: https://github.com/gitleaks/gitleaks
    rev: v8.18.0
    hooks:
      - id: gitleaks
  - repo: https://github.com/Yelp/detect-secrets
    rev: v1.4.0
    hooks:
      - id: detect-secrets
```

Rotate any accidentally committed secret immediately.

---

## 56. Dependency Update Pattern

- Use lockfiles (`package-lock.json`, `poetry.lock`, `go.sum`, `Cargo.lock`).
- Enable Dependabot/Renovate with grouping rules.
- Review changelogs and security advisories for major/minor updates.
- Run tests and scans before merging.
- Keep a patching SLA: critical within 24–48h, high within 1 week.

---

## 57. API Versioning and Deprecation Pattern

- Include version in URL (`/v1/`) or header (`Accept: application/vnd.example.v1+json`).
- Maintain backward compatibility within a major version.
- Communicate deprecation with sunset headers and documentation.
- Remove old versions only after analytics show minimal usage and after notice period.

---

## 58. Configuration Security Pattern

- Keep secrets separate from config.
- Validate configuration at startup and fail fast on missing/invalid values.
- Use typed config objects (Pydantic Settings, Viper, Spring Boot Config).
- Do not expose config endpoints without authentication.
- Avoid debug mode, stack traces, and verbose errors in production.

```python
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    debug: bool = False
    database_url: str
    secret_key: str
    allowed_hosts: list[str]

    class Config:
        env_file = ".env"

settings = Settings()
if settings.debug:
    raise RuntimeError("debug must be False in production")
```

---

## 59. Health Check Security Pattern

- Expose liveness/readiness endpoints on a separate port if they leak details.
- Do not include sensitive data in health responses.
- Require authentication for detailed health endpoints in production.

```python
@app.get("/health")
async def health():
    return {"status": "ok"}

@app.get("/health/detailed")
async def detailed_health(user: CurrentUser):
    if user.role != "admin":
        raise HTTPException(403)
    return {"db": check_db(), "cache": check_cache()}
```

---

## 60. Secure Defaults for Frameworks

When scaffolding a project, always configure:

- Security headers middleware.
- CSRF protection for server-rendered forms.
- Session/cookie hardening.
- Input validation framework.
- Authn/authz middleware.
- Audit logging.
- Error handler that hides internals.
- Dependency scanning.

---

## 61. Multi-Factor Authentication Rollout Pattern

1. Enroll users by requiring a second factor at next login.
2. Provide multiple factor options (TOTP, WebAuthn, backup codes).
3. Allow grace period but notify of upcoming enforcement.
4. Require MFA for sensitive roles immediately.
5. Provide self-service recovery with identity verification.
6. Monitor and alert on MFA disable events.

---

## 62. Backup and Recovery Security Pattern

- Encrypt backups at rest and in transit.
- Store backups in a separate account/region from production.
- Test restoration regularly.
- Restrict backup access to break-glass roles.
- Retain backups per policy but purge when no longer required.

---

## 63. Secure Onboarding / Offboarding Pattern

- Provision accounts via SSO/SCIM; avoid manual account creation.
- Grant least privilege; use groups/roles tied to job function.
- Offboard: disable account, revoke sessions, rotate shared secrets, reassign data.
- Audit access after offboarding.

---

## 64. Third-Party Vendor Security Pattern

Before integrating a vendor:

- Review SOC 2, ISO 27001, or equivalent reports.
- Understand data processing and sub-processors.
- Confirm encryption, access controls, and incident response.
- Assess business continuity and data deletion practices.
- Include security requirements in contract (DPA, BAA, SLA).

---

## 65. Bug Bounty / VDP Pattern

1. Define scope clearly (domains, endpoints, out-of-scope).
2. Provide safe harbor policy.
3. Set up dedicated intake channel.
4. Triage and respond within SLA (e.g., 24h acknowledgment).
5. Fix, verify, disclose, and reward per policy.

---

## 66. Threat Intelligence Integration Pattern

- Subscribe to CISA KEV, vendor advisories, and relevant CERTs.
- Map CVEs to assets using SBOM.
- Prioritize by exploitability, asset criticality, and exposure.
- Automate ticket creation for high/critical findings.

---

## 67. Endpoint Detection Pattern

- Deploy EDR on workstations and servers.
- Centralize alerts in SIEM.
- Tune detection rules to reduce false positives.
- Maintain response playbooks for common alerts.

---

## 68. Data Loss Prevention (DLP) Pattern

- Classify data at creation/rest.
- Block exfiltration of sensitive data via email, web, and removable media.
- Monitor large/unusual data transfers.
- Encrypt sensitive data before sharing.

---

## 69. Penetration Testing Rhythm

- Annual or major-release external penetration tests.
- Quarterly internal scans and focused tests.
- Continuous bug bounty or crowdsourced testing.
- Remediate critical/high findings within SLA and retest.

---

## 70. Security Metrics Dashboard

Track:

- Mean time to remediate (MTTR) by severity.
- Open critical/high findings over time.
- SAST/DAST scan coverage.
- Dependency freshness.
- Patch cadence.
- Phishing simulation results.
- Incident count and severity.
- Secrets scan hits.

Use these metrics to drive improvement, not blame.


---

## 71. Secure Redirect Pattern

```python
from fastapi import HTTPException

ALLOWED_REDIRECTS = {
    "dashboard": "/dashboard",
    "profile": "/profile",
    "settings": "/settings",
}

def safe_redirect(target: str) -> str:
    if target not in ALLOWED_REDIRECTS:
        raise HTTPException(400, "invalid redirect target")
    return ALLOWED_REDIRECTS[target]
```

---

## 72. Mass Assignment Prevention Pattern

```python
from pydantic import BaseModel, Field

class UserUpdateRequest(BaseModel):
    display_name: str | None = Field(None, max_length=100)
    bio: str | None = Field(None, max_length=500)
    # Explicitly omit is_admin, role, balance, etc.

@app.put("/users/me")
def update_user(req: UserUpdateRequest, user: CurrentUser):
    return user_service.update(user.id, req.dict(exclude_unset=True))
```

---

## 73. Anti-Clickjacking Pattern

```http
Content-Security-Policy: frame-ancestors 'none'
X-Frame-Options: DENY
```

For pages that may be framed by a known origin:

```http
Content-Security-Policy: frame-ancestors https://trusted.example.com
```

---

## 74. Anti-MIME-Sniffing Pattern

```http
X-Content-Type-Options: nosniff
Content-Type: text/plain; charset=utf-8
```

---

## 75. Password Reset Token Pattern

```python
import secrets
from datetime import datetime, timedelta, timezone

def create_reset_token(user_id: str) -> str:
    token = secrets.token_urlsafe(32)
    expires = datetime.now(timezone.utc) + timedelta(hours=1)
    db.store_token(user_id, token, expires)
    return token

def consume_reset_token(token: str) -> str | None:
    record = db.find_token(token)
    if not record or record["expires"] < datetime.now(timezone.utc):
        return None
    db.delete_token(token)
    return record["user_id"]
```

Single-use, time-limited, and invalidated on password change.

---

## 76. Audit Logging Pattern

```python
import logging
import json

audit_logger = logging.getLogger("audit")

def audit(action: str, actor: str, resource: str, outcome: str, details: dict):
    audit_logger.info(json.dumps({
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "action": action,
        "actor": actor,
        "resource": resource,
        "outcome": outcome,
        "details": sanitize(details),
    }))
```

---

## 77. Data Sanitization Pattern

```python
import copy

SENSITIVE = {"password", "token", "secret", "ssn", "credit_card", "cvv", "api_key"}

def sanitize(obj):
    if isinstance(obj, dict):
        return {
            k: "***" if any(s in k.lower() for s in SENSITIVE) else sanitize(v)
            for k, v in obj.items()
        }
    if isinstance(obj, list):
        return [sanitize(v) for v in obj]
    return obj
```

---

## 78. Feature Flag Security Pattern

- Gate security features behind flags with explicit owners and review.
- Do not allow flags to disable authentication or authorization in production.
- Audit flag changes.
- Require approval for changes to critical flags.

---

## 79. Database Encryption Pattern

For application-level encryption of columns:

```python
from sqlalchemy import TypeDecorator, LargeBinary
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

class EncryptedString(TypeDecorator):
    impl = LargeBinary

    def process_bind_param(self, value, dialect):
        if value is None:
            return None
        nonce = os.urandom(12)
        return nonce + aesgcm.encrypt(nonce, value.encode(), None)

    def process_result_value(self, value, dialect):
        if value is None:
            return None
        nonce, ciphertext = value[:12], value[12:]
        return aesgcm.decrypt(nonce, ciphertext, None).decode()
```

---

## 80. Row-Level Security Pattern

PostgreSQL example:

```sql
CREATE POLICY user_isolation ON orders
    FOR ALL
    TO app_user
    USING (user_id = current_setting('app.current_user_id')::uuid);

ALTER TABLE orders ENABLE ROW LEVEL SECURITY;
```

Application sets the config variable per session.

---

## 81. Mutual TLS (mTLS) Pattern

Server config (nginx):

```nginx
server {
    listen 443 ssl;
    ssl_verify_client on;
    ssl_client_certificate /etc/nginx/ca.crt;
    ssl_verify_depth 2;
    location / {
        proxy_set_header X-SSL-Client-S-DN $ssl_client_s_dn;
        proxy_pass http://backend;
    }
}
```

Backend validates the forwarded identity header matches expected DN.

---

## 82. Service Account Identity Pattern

In Kubernetes:

```yaml
apiVersion: v1
kind: ServiceAccount
metadata:
  name: api-service
  annotations:
    eks.amazonaws.com/role-arn: arn:aws:iam::ACCOUNT:role/api-role
```

Pod uses this service account; no static AWS credentials needed.

---

## 83. Security Header Middleware Pattern

```python
from starlette.middleware.base import BaseHTTPMiddleware

class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
        return response
```

---

## 84. Request Size Limit Pattern

```python
from fastapi import FastAPI
from starlette.middleware.trustedhost import TrustedHostMiddleware

app = FastAPI()
app.add_middleware(TrustedHostMiddleware, allowed_hosts=["example.com", "*.example.com"])
```

Also configure reverse proxy and framework limits for body size, upload size, and header count.

---

## 85. Webhook Signature Verification Pattern

```python
import hmac
import hashlib
import json

def verify_webhook(payload: bytes, signature: str, secret: bytes) -> bool:
    expected = "sha256=" + hmac.new(secret, payload, hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, signature)
```

Always verify signatures; do not trust webhook content without authentication.

---

## 86. API Versioning Pattern

```python
from fastapi import APIRouter

v1 = APIRouter(prefix="/v1")
v2 = APIRouter(prefix="/v2")

@v1.get("/users/{user_id}")
def get_user_v1(user_id: str): ...

@v2.get("/users/{user_id}")
def get_user_v2(user_id: str): ...
```

Communicate sunset dates via API documentation and `Sunset` headers.

---

## 87. Two-Factor TOTP Pattern

```python
import pyotp

secret = pyotp.random_base32()
uri = pyotp.totp.TOTP(secret).provisioning_uri(name=user.email, issuer_name="Example")
# Show QR code from uri

# Verify
totp = pyotp.TOTP(secret)
if not totp.verify(code):
    raise AuthError("invalid code")
```

Store encrypted secrets; prevent replay by accepting each code only once.

---

## 88. Backup Encryption Pattern

```bash
# Encrypt backup with AES-256-GCM using age
tar czf - /data | age -r age1... > backup.tar.gz.age

# Decrypt
age -d -i key.txt backup.tar.gz.age | tar xzf -
```

Store encryption key separately; test restore regularly.

---

## 89. Log Forwarding Pattern

```yaml
fluent-bit:
  inputs:
    - name: tail
      path: /var/log/app/*.log
      parser: json
  outputs:
    - name: forward
      match: '*'
      host: siem.example.com
      port: 24224
```

---

## 90. Canary Token Pattern

Place fake credentials, files, or URLs in sensitive locations. If accessed, alert.

Useful for detecting:

- Unauthorized access to repositories
- Credential theft
- Lateral movement
- Insider threats

---

## 91. Decoy Database Record Pattern

Insert fake but realistic records with honeypot email addresses. Monitor for misuse.

---

## 92. Immutable Audit Log Pattern

- Append-only storage.
- Cryptographic chaining (hash of previous entry).
- Independent log shipper that attackers cannot easily modify.
- Regular snapshots to write-once storage.

---

## 93. Secure Offboarding Pattern

```python
def offboard_user(user_id: str):
    sessions.revoke_all(user_id)
    passwords.disable(user_id)
    api_keys.revoke(user_id)
    mfa.reset(user_id)
    group_memberships.remove(user_id)
    access_reviews.archive(user_id)
```

---

## 94. Least-Privilege Cloud IAM Policy Pattern

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "s3:GetObject",
        "s3:PutObject"
      ],
      "Resource": "arn:aws:s3:::example-bucket/uploads/*",
      "Condition": {
        "StringEquals": {
          "aws:PrincipalTag/Team": "app"
        }
      }
    }
  ]
}
```

---

## 95. Security Exception Process

When a control cannot be implemented:

1. Document the risk and business justification.
2. Identify compensating controls.
3. Assign risk owner.
4. Set review/expiration date.
5. Obtain management approval.
6. Reassess periodically.

---

## 96. Vulnerability Disclosure Response Pattern

1. Acknowledge receipt within 24–48 hours.
2. Confirm validity and scope.
3. Develop and test fix.
4. Coordinate disclosure date with reporter.
5. Release patch and advisory.
6. Credit reporter.

---

## 97. Secure Scaffolding Template

When starting a new service, include:

- Authn/authz middleware
- Validation framework
- Security headers middleware
- Logging and error handling
- Health/readiness endpoints
- Secrets loading
- TLS configuration
- Dependency scanning config
- Dockerfile with non-root user
- CI pipeline with security jobs

---

## 98. Secrets Rotation Rollout Pattern

1. Generate new secret in vault.
2. Update consumers to read new secret; support fallback to old.
3. Update producers to use new secret.
4. Monitor for old-secret usage.
5. Revoke old secret after grace period.

---

## 99. Defense-in-Depth API Checklist

- [ ] TLS terminated at gateway
- [ ] Mutual TLS between internal services
- [ ] AuthN at gateway
- [ ] AuthZ at service layer
- [ ] Input validation and schema enforcement
- [ ] Rate limiting per client
- [ ] Output DTOs to avoid over-exposure
- [ ] Structured logging without secrets
- [ ] Circuit breakers and timeouts
- [ ] Retry budgets and idempotency keys
- [ ] Centralized tracing

---

## 100. Final Patterns Summary

Good security patterns share traits:

- They fail closed.
- They validate at trust boundaries.
- They use allowlists, not denylists.
- They minimize secrets and privilege.
- They are observable and auditable.
- They are tested, including abuse cases.

Apply these patterns as defaults; deviate only with documented risk acceptance.

End of patterns.


---

## 101. Safe Deserialization Pattern

```python
import json
from pydantic import BaseModel, ValidationError

class TaskMessage(BaseModel):
    task_id: str
    action: str  # allowlist checked below
    payload: dict

ALLOWED_ACTIONS = {"enqueue", "cancel", "retry"}

def process_message(raw: bytes):
    try:
        msg = TaskMessage(**json.loads(raw))
    except (json.JSONDecodeError, ValidationError) as e:
        raise ValueError("invalid message") from e
    if msg.action not in ALLOWED_ACTIONS:
        raise ValueError("disallowed action")
    return dispatcher.handle(msg)
```

---

## 102. OAuth Scope Enforcement Pattern

```python
from functools import wraps

def require_scope(*scopes):
    def decorator(func):
        @wraps(func)
        async def wrapper(request, *args, **kwargs):
            token_scopes = set(request.state.token.get("scope", "").split())
            if not set(scopes).issubset(token_scopes):
                raise HTTPException(403, "insufficient scope")
            return await func(request, *args, **kwargs)
        return wrapper
    return decorator

@app.post("/invoices")
@require_scope("invoices:write")
def create_invoice(...):
    ...
```

---

## 103. API Pagination Pattern

```python
from pydantic import BaseModel
from typing import List

class PaginatedResponse(BaseModel):
    items: List[Item]
    next_cursor: str | None
    total: int | None

@app.get("/items")
def list_items(cursor: str | None = None, limit: int = 20):
    limit = min(max(limit, 1), 100)
    return item_service.list(cursor=cursor, limit=limit)
```

Limit page size to prevent abuse; use opaque cursors to avoid enumeration.

---

## 104. Idempotency Key Pattern

```python
import hashlib

class IdempotencyStore:
    def check_or_store(self, key: str, request_hash: str, result: dict):
        existing = self.db.get(key)
        if existing:
            if existing["request_hash"] != request_hash:
                raise Conflict("idempotency key reused with different request")
            return existing["result"]
        self.db.setex(key, timedelta(hours=24), {"request_hash": request_hash, "result": result})
        return None

def request_hash(method: str, path: str, body: bytes) -> str:
    return hashlib.sha256(f"{method}:{path}:".encode() + body).hexdigest()
```

---

## 105. Circuit Breaker Pattern

```python
from enum import Enum

class State(Enum):
    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"

class CircuitBreaker:
    def __init__(self, failure_threshold=5, recovery_timeout=30):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.failures = 0
        self.state = State.CLOSED
        self.last_failure_time = None

    def call(self, fn, *args, **kwargs):
        if self.state == State.OPEN:
            if time.time() - self.last_failure_time > self.recovery_timeout:
                self.state = State.HALF_OPEN
            else:
                raise ServiceUnavailable()
        try:
            result = fn(*args, **kwargs)
            self.reset()
            return result
        except Exception as e:
            self.record_failure()
            raise
```

---

## 106. Database Migration Security Pattern

- Review migrations for destructive operations and data exposure.
- Run migrations with a dedicated high-privilege account.
- Application runtime uses least-privilege accounts.
- Back up before applying migrations.
- Test migrations against production-like data.
- Log migration execution.

---

## 107. Pre-Commit Security Hooks Pattern

```yaml
repos:
  - repo: https://github.com/pre-commit/pre-commit-hooks
    rev: v4.5.0
    hooks:
      - id: detect-private-key
      - id: check-added-large-files
  - repo: https://github.com/gitleaks/gitleaks
    rev: v8.18.0
    hooks:
      - id: gitleaks
  - repo: https://github.com/returntocorp/semgrep
    rev: v1.52.0
    hooks:
      - id: semgrep
        args: ['--config', 'p/security-audit', '--error']
```

---

## 108. WAF Tuning Pattern

1. Start in monitor/log mode.
2. Review false positives.
3. Add exclusions for legitimate traffic patterns.
4. Enable blocking mode gradually.
5. Monitor blocked requests and tune rules.
6. Keep rules updated with vendor signatures.

---

## 109. SIEM Detection Rule Pattern

```yaml
title: Multiple failed logins from single IP
detection:
  selection:
    event.outcome: failure
    event.action: user-login
  condition: selection | count() by source.ip > 10
  timeframe: 5m
severity: medium
response: alert security team; enable CAPTCHA
```

---

## 110. Anomaly Detection Pattern

- Establish baselines for request volume, latency, error rates, login patterns.
- Use statistical thresholds or ML models.
- Alert on deviations, but tune to reduce false positives.
- Combine with threat intelligence and known IoCs.

---

## 111. Zero Trust Remote Access Pattern

- No VPN; access based on device health, user identity, and risk score.
- Authenticate via OIDC + MFA.
- Enforce device compliance certificates.
- Apply least-privilege access to each application.
- Log every access decision.

---

## 112. Reproducible Build Pattern

- Pin all dependencies by hash.
- Use deterministic build tools and compiler flags.
- Record build environment metadata.
- Compare build artifacts across independent builders.
- Publish signed SBOM and provenance attestations.

---

## 113. Security.txt Pattern

```
Contact: mailto:security@example.com
Expires: 2027-01-01T00:00:00.000Z
Acknowledgments: https://example.com/security-hall-of-fame
Preferred-Languages: en
Canonical: https://example.com/.well-known/security.txt
Policy: https://example.com/security-policy
Hiring: https://example.com/jobs/security
```

---

## 114. Privacy-Preserving Pattern

- Collect only necessary data.
- Use pseudonymization for analytics.
- Aggregate data to avoid re-identification.
- Provide data export and deletion APIs.
- Log access to personal data.

---

## 115. Data Retention Policy Pattern

```python
def purge_expired_data():
    cutoff = datetime.now(timezone.utc) - retention_policy.max_age
    db.execute("DELETE FROM events WHERE created_at < ?", (cutoff,))
    object_store.delete_prefix("temp/", older_than=cutoff)
```

Automate retention enforcement and verify with audits.

---

## 116. Token Binding / DPoP Pattern

Demonstrating Proof-of-Possession (DPoP) binds tokens to a public key:

1. Client generates ephemeral key pair.
2. Sends public key with token request.
3. Authorization server issues token bound to public key thumbprint.
4. Client signs each request with private key; resource server validates.

Mitigates token theft replay.

---

## 117. Credential Stuffing Mitigation Pattern

- Rate limit login attempts per IP and account.
- Use CAPTCHA after threshold.
- Check passwords against breach databases (Have I Been Pwned k-anonymity API).
- Force password reset if breached password detected.
- Encourage/enforce MFA.
- Alert on unusual login success patterns.

---

## 118. Account Takeover Detection Pattern

Monitor for:

- Login from new device/location/IP
- Multiple failed logins followed by success
- Password reset followed by immediate sensitive action
- MFA disable
- New email or phone added
- Large data export

Trigger step-up authentication or temporary account lock.

---

## 119. Bot Detection Pattern

- JavaScript challenges and behavioral biometrics.
- Rate limiting and IP reputation.
- CAPTCHA as a last resort.
- Device fingerprinting with privacy safeguards.
- Challenge suspicious traffic with proof-of-work or delayed responses.

---

## 120. Schema Validation at API Gateway Pattern

```yaml
paths:
  /orders:
    post:
      requestBody:
        required: true
        content:
          application/json:
            schema:
              type: object
              properties:
                product_id:
                  type: string
                  pattern: '^[A-Za-z0-9_-]+$'
                quantity:
                  type: integer
                  minimum: 1
                  maximum: 100
              required: [product_id, quantity]
```

Enforce schema at the gateway and again in the service.

---

## 121. Feature Flag Safety Pattern

- Separate security feature flags from business flags.
- Require approval and audit for disabling security controls.
- Use environment-specific defaults.
- Monitor flag state changes.
- Never allow a feature flag to bypass authn/authz.

---

## 122. A/B Test Security Pattern

- Do not expose PII in experiment assignment.
- Avoid experiments that weaken security controls.
- Log experiment group membership for audit.
- Ensure assignment cannot be gamed.

---

## 123. Sandboxing Pattern

Run untrusted code in a sandbox:

- Separate process with minimal privileges
- seccomp-bpf syscall filtering
- Linux namespaces and cgroups
- gVisor or Firecracker microVMs
- WebAssembly with capability restrictions

---

## 124. Secure Admin Interface Pattern

- Place admin UI on separate host or path.
- Require VPN or Zero Trust access.
- Enforce MFA and role-based access.
- Log all admin actions.
- Rate-limit and alert on suspicious admin activity.
- Disable or hide admin endpoints from public docs.

---

## 125. Certificate Pinning Pattern (Thick Clients)

```python
import hashlib

PINNED_HASH = "sha256/..."

def verify_pin(cert_der: bytes) -> bool:
    digest = hashlib.sha256(cert_der).digest()
    encoded = "sha256/" + base64.b64encode(digest).decode()
    return encoded == PINNED_HASH
```

Include a backup pin and plan for rotation; avoid HPKP in browsers.

---

## 126. Security Metrics Review Pattern

Monthly review:

- Open critical/high findings and MTTR
- New vulnerabilities introduced vs. remediated
- Scan coverage and pass rates
- Incident count and root causes
- MFA enrollment rate
- Secrets scan hits
- Dependency freshness

Use trends to prioritize security engineering work.

---

## 127. Secure Pair Programming Pattern

- Rotate driver/navigator every 15–20 minutes.
- Navigator challenges security assumptions.
- Focus on input validation, authz, and error handling.
- Run security linters continuously.
- Capture security decisions as code comments or ADRs.

---

## 128. Security Onboarding Checklist

- Acceptable use policy
- MFA setup
- Secure coding training
- Access to vault, CI, and repositories
- Threat model intro
- Incident reporting channels
- Phishing awareness

---

## 129. Third-Party Integration Security Pattern

Before integrating:

- Review security documentation and certifications.
- Assess data handling and retention.
- Evaluate SLA and incident response.
- Define security responsibilities.
- Include security requirements in contract.
- Monitor integration for anomalies.

---

## 130. Final Patterns Index

Key categories:

- Input/output handling
- Authn/authz
- Cryptography and secrets
- Web/API security
- Infrastructure and cloud
- CI/CD and supply chain
- Monitoring and incident response
- Governance and culture

Reuse and adapt these patterns to each project's risk profile.

End of patterns.


---

## 131. Input Validation Recipes

### Validate a UUID

```python
from uuid import UUID

def validate_uuid(value: str) -> str:
    return str(UUID(value))
```

### Validate a date range

```python
from datetime import date

def validate_range(start: date, end: date):
    if start > end:
        raise ValueError("start must be before end")
```

### Validate a US phone number

```python
import re

def validate_phone(value: str) -> str:
    digits = re.sub(r"\D", "", value)
    if len(digits) != 10:
        raise ValueError("invalid phone")
    return digits
```

---

## 132. Output Encoding Recipes

### JavaScript context

```python
import json

def js_string(value: str) -> str:
    return json.dumps(value)
```

### CSS context

```python
import re

def css_string(value: str) -> str:
    return re.sub(r"[^a-zA-Z0-9_-]", lambda m: f"\\{ord(m.group(0)):06x}", value)
```

### URL context

```python
from urllib.parse import quote

def url_param(value: str) -> str:
    return quote(value, safe='')
```

---

## 133. Authentication Recipes

### Brute-force protection with Redis

```python
import redis
r = redis.Redis()

def is_locked(identifier: str) -> bool:
    attempts = r.incr(f"login:{identifier}")
    if attempts == 1:
        r.expire(f"login:{identifier}", 900)
    return attempts > 5
```

### Password strength check with zxcvbn

```python
from zxcvbn import zxcvbn

def check_strength(password: str) -> dict:
    result = zxcvbn(password)
    return {"score": result["score"], "feedback": result["feedback"]["suggestions"]}
```

---

## 134. Authorization Recipes

### Ownership check decorator

```python
from functools import wraps

def require_owner(get_owner):
    def decorator(fn):
        @wraps(fn)
        def wrapper(*args, **kwargs):
            resource_owner = get_owner(*args, **kwargs)
            if resource_owner != current_user.id:
                raise Forbidden()
            return fn(*args, **kwargs)
        return wrapper
    return decorator
```

### Role hierarchy

```python
ROLE_LEVELS = {"guest": 0, "user": 1, "moderator": 2, "admin": 3}

def has_role(user, min_role: str) -> bool:
    return ROLE_LEVELS.get(user.role, 0) >= ROLE_LEVELS[min_role]
```

---

## 135. Cryptography Recipes

### Generate an RSA key pair

```python
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives import serialization

private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
pem = private_key.private_bytes(
    encoding=serialization.Encoding.PEM,
    format=serialization.PrivateFormat.PKCS8,
    encryption_algorithm=serialization.NoEncryption(),
)
```

### Sign with Ed25519

```python
from cryptography.hazmat.primitives.asymmetric import ed25519
private_key = ed25519.Ed25519PrivateKey.generate()
signature = private_key.sign(message)
public_key.verify(signature, message)
```

### Derive key with scrypt

```python
import os, hashlib
salt = os.urandom(32)
key = hashlib.scrypt(password.encode(), salt=salt, n=2**17, r=8, p=1, dklen=32)
```

---

## 136. Web Security Recipes

### Flask secure cookie

```python
from flask import make_response
resp = make_response("ok")
resp.set_cookie("session", value=token, httponly=True, secure=True, samesite="Strict")
```

### Django CSRF in templates

```html
<form method="post">{% csrf_token %}</form>
```

### Express helmet

```javascript
const helmet = require('helmet');
app.use(helmet());
app.use(helmet.contentSecurityPolicy({
  directives: {
    defaultSrc: ["'self'"],
    scriptSrc: ["'self'", "'nonce-'" + nonce],
  },
}));
```

---

## 137. Database Security Recipes

### Principle of least privilege user

```sql
CREATE USER app_read WITH PASSWORD '...';
GRANT USAGE ON SCHEMA public TO app_read;
GRANT SELECT ON ALL TABLES IN SCHEMA public TO app_read;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT SELECT ON TABLES TO app_read;
```

### Encrypt column with pgcrypto

```sql
INSERT INTO secrets (value) VALUES (pgp_sym_encrypt('secret', 'key'));
SELECT pgp_sym_decrypt(value, 'key') FROM secrets;
```

---

## 138. Container Security Recipes

### Multi-stage Go Dockerfile

```dockerfile
FROM golang:1.22-alpine AS builder
WORKDIR /app
COPY go.mod go.sum ./
RUN go mod download
COPY . .
RUN CGO_ENABLED=0 go build -o app .

FROM gcr.io/distroless/static-debian12
COPY --from=builder /app/app /app
USER nonroot:nonroot
ENTRYPOINT ["/app"]
```

### BuildKit secret mount

```dockerfile
RUN --mount=type=secret,id=api_key,target=/run/secrets/api_key \
    API_KEY=$(cat /run/secrets/api_key) ./build.sh
```

---

## 139. Cloud Security Recipes

### AWS SCP deny public S3 buckets

```json
{
  "Version": "2012-10-17",
  "Statement": [{
    "Effect": "Deny",
    "Action": "s3:PutBucketPublicAccessBlock",
    "Resource": "*"
  }]
}
```

### GCP organization policy disable service account key creation

```bash
gcloud resource-manager org-policies disable-enforce iam.disableServiceAccountKeyCreation --organization=YOUR_ORG_ID
```

---

## 140. CI/CD Security Recipes

### GitHub Actions OIDC to AWS

```yaml
permissions:
  id-token: write
  contents: read
steps:
  - uses: aws-actions/configure-aws-credentials@v4
    with:
      role-to-assume: arn:aws:iam::ACCOUNT:role/GitHubActionsRole
      aws-region: us-east-1
```

---

## 141. Monitoring and Alerting Recipes

### PromQL rate-limit alert

```promql
rate(http_requests_total{status="429"}[5m]) > 0.1
```

### SIEM query: failed logins

```sql
SELECT source_ip, COUNT(*) AS failures
FROM auth_events
WHERE outcome = 'failure'
  AND timestamp > NOW() - INTERVAL 10 MINUTE
GROUP BY source_ip
HAVING failures > 10;
```

---

## 142. Incident Response Recipes

### Isolate a compromised EC2 instance

```bash
aws ec2 create-network-interface-permission \
  --network-interface-id eni-xxx \
  --permission INSTANCE-ATTACH \
  --instance-id i-xxx
# Or change security group to isolated group
```

### Revoke all sessions for a user

```python
for token in session_store.find_by_user(user_id):
    session_store.revoke(token)
```

---

## 143. Compliance Recipes

### GDPR data export

```python
def export_user_data(user_id: str) -> dict:
    return {
        "profile": profile_repo.export(user_id),
        "orders": order_repo.export(user_id),
        "logs": audit_repo.export(user_id),
    }
```

### Data deletion

```python
def delete_user_data(user_id: str):
    profile_repo.anonymize(user_id)
    order_repo.retain_anonymized(user_id)
    session_store.revoke_all(user_id)
    backup_service.schedule_purge(user_id)
```

---

## 144. Secure Communication Recipes

### Mutual TLS client in Python

```python
import ssl
import urllib.request

ctx = ssl.create_default_context()
ctx.load_cert_chain(certfile='client.crt', keyfile='client.key')
ctx.load_verify_locations(cafile='ca.crt')
ctx.verify_mode = ssl.CERT_REQUIRED
req = urllib.request.Request('https://api.example.com/data')
resp = urllib.request.urlopen(req, context=ctx)
```

---

## 145. API Security Recipes

### OpenAPI security scheme

```yaml
components:
  securitySchemes:
    bearerAuth:
      type: http
      scheme: bearer
      bearerFormat: JWT
security:
  - bearerAuth: []
```

### Require API key header

```python
from fastapi import Security, HTTPException
from fastapi.security import APIKeyHeader

api_key_header = APIKeyHeader(name="X-API-Key")

def verify_api_key(key: str = Security(api_key_header)):
    if key != API_KEY:
        raise HTTPException(401, "invalid api key")
```

---

## 146. Testing Security Recipes

### Pytest parametric auth tests

```python
import pytest

@pytest.mark.parametrize("role,expected", [
    ("admin", 200),
    ("user", 403),
    (None, 401),
])
def test_admin_endpoint(client, role, expected):
    headers = auth_headers(role) if role else {}
    resp = client.get("/admin", headers=headers)
    assert resp.status_code == expected
```

---

## 147. Documentation Recipes

### Security ADR template

```markdown
# ADR-012: Use RS256 for service-to-service JWTs
## Status
Accepted
## Context
Multiple services need to verify tokens; shared secret distribution is risky.
## Decision
Use RS256 with a central issuer holding the private key.
## Consequences
+ Private key stays with issuer
- Slightly larger tokens
- Need JWKS endpoint and rotation process
```

---

## 148. Final Recipes Checklist

When implementing any security control, ensure:

- It is validated by tests.
- It is documented.
- It is monitored.
- It can be rotated or revoked.
- It fails securely.
- It follows least privilege.

End of patterns.
