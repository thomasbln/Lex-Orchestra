# Scan Strategy

## Two-Stage Scan (Node 1)

```
Node 1a — GitHub Repo:
  package.json, docker-compose.yml, .env.example, src/**
  Detects: Services, sub-processors, data transfers, auth flows

Node 1b — Live URL:
  Stage 1: Cloudflare URL Scanner API
    → Third-parties, trackers, cookies, CDN
  Stage 2: Legal Page Content Fetcher
    → Impressum, Datenschutz, AGB, Cookie-Policy as raw content
```

## Credential Scanning (Highest Priority)

| Status | Meaning |
|--------|---------|
| 🔴 RED | Credential in plaintext → immediate alert, scan interrupted |
| 🟡 YELLOW | .env without .gitignore entry — manual review |
| 🟢 GREEN | All credentials via .env, no plaintext |

**Detected Patterns (RED):**
```
sk-[a-zA-Z0-9]{20,}          # OpenAI / Anthropic
sk-live-[a-zA-Z0-9]{20,}     # Stripe live
ghp_[a-zA-Z0-9]{36}          # GitHub Token
AIza[a-zA-Z0-9]{35}          # Google API Key
password = "..."              # Generic
api_key = "..."               # Generic
```

**Alert on RED:**
```
CRITICAL: credential in plaintext
Project: my-project.io
File: src/checkout.js, line 42
Type: Stripe live API key
Action: 1. rotate the key  2. move it to .env  3. clean the git history
```
The scan is interrupted and the finding appears on the scan status page.

## Legal Pages Fetcher

Checked Paths:
```
/impressum, /imprint
/datenschutz, /privacy, /datenschutzerklaerung, /privacy-policy
/agb, /terms, /tos
/cookies, /cookie-policy
```

Raw Storage Structure:
```
raw_scan/{project}/scan_{date}/
  impressum.html + impressum.txt
  datenschutz.html + datenschutz.txt
  cloudflare_result.json
  scout_result.json
```

## Cloudflare URL Scanner → Compliance Relevance

| Finding | Consequence |
|---------|-------------|
| `google-analytics.com` | Cookie consent required (TTDSG § 25) |
| `hotjar.com` | Cookie consent + AVV |
| Cookie without `httpOnly` | TTDSG review |
| No HTTPS redirect | DSGVO Art. 32 (ToM gap) |
| Impressum unreachable | DDG § 5 violation |

## OWASP LLM Top 10 — Scout Detection (when AI in stack)

| OWASP | Vulnerability | Scout Pattern |
|-------|---|---|
| LLM01 | Prompt Injection | `user_input` directly in prompt |
| LLM06 | Sensitive Data Disclosure | LLM output directly into DB |
| LLM08 | Excessive Agency | `subprocess`, `os.system`, `eval()` |

## Compliance Delta Between Scans

Scout compares current scan with the previous one:
- privacy policy changed → flagged in the scan report + `compliance_delta.md`
- New service detected → graph update + document proposal
- New credential added → RED ALERT
