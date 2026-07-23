# Service Registry

Known services with compliance mapping for the Scout.

**Legend:** AVV = Auftragsverarbeitungsvertrag | SCC = Standard Contractual Clauses | AI = EU AI Act relevant | Cookie = Cookie consent required

---

## Payment

| Service | Country | GDPR-adequate | AVV | SCC | AI | Cookie | Pattern |
|---------|---------|--------------|-----|-----|----|--------|---------|
| Stripe | USA | ❌ | ✅ | ✅ | — | — | `stripe`, `@stripe/stripe-js` |
| PayPal | USA | ❌ | ✅ | ✅ | — | — | `paypal` |
| Paddle | Ireland | ✅ | ✅ | — | — | — | `paddle` |
| Mollie | Netherlands | ✅ | ✅ | — | — | — | `mollie` |
| Klarna | Sweden | ✅ | ✅ | — | — | — | `klarna` |

## Backend / BaaS

| Service | Country | GDPR-adequate | AVV | SCC | Pattern |
|---------|---------|--------------|-----|-----|---------|
| Supabase | USA | ❌ | ✅ | ✅ | `@supabase/supabase-js` |
| Firebase | USA | ❌ | ✅ | ✅ | `firebase` |
| Neon | USA | ❌ | ✅ | ✅ | `@neondatabase/serverless` |
| Appwrite | Germany | ✅ | ✅ | — | `appwrite` |

## Email / Messaging

| Service | Country | GDPR-adequate | AVV | SCC | Pattern |
|---------|---------|--------------|-----|-----|---------|
| Resend | USA | ❌ | ✅ | ✅ | `resend`, `@resend/node` |
| SendGrid | USA | ❌ | ✅ | ✅ | `@sendgrid/mail` |
| Postmark | USA | ❌ | ✅ | ✅ | `postmark` |
| Brevo | France | ✅ | ✅ | — | `@getbrevo/brevo` |
| Twilio | USA | ❌ | ✅ | ✅ | `twilio` |

## AI / LLM

| Service | Country | GDPR | AVV | SCC | AI Act | Pattern |
|---------|---------|------|-----|-----|--------|---------|
| OpenAI | USA | ❌ | ✅ | ✅ | ✅ GPAI | `openai` |
| Anthropic | USA | ❌ | ✅ | ✅ | ✅ GPAI | `@anthropic-ai/sdk` |
| Mistral AI | France | ✅ | ✅ | — | ✅ GPAI | `@mistralai/mistralai` |
| Groq | USA | ❌ | ✅ | ✅ | ✅ GPAI | `groq-sdk` |

## Hosting / Infrastructure

| Service | Country | GDPR | AVV | SCC | Pattern |
|---------|---------|------|-----|-----|---------|
| Vercel | USA | ❌ | ✅ | ✅ | `vercel`, `.vercel.app` |
| Hetzner | Germany | ✅ | ✅ | — | `hetzner.com` |
| AWS | USA | ❌ | ✅ | ✅ | `aws-sdk`, `@aws-sdk/*` |
| Cloudflare | USA | ❌ | ✅ | ✅ | `cloudflare`, `wrangler` |

## Auth / Identity

| Service | Country | GDPR | AVV | SCC | Cookie | Pattern |
|---------|---------|------|-----|-----|--------|---------|
| Clerk | USA | ❌ | ✅ | ✅ | ✅ | `@clerk/nextjs` |
| Auth0 | USA | ❌ | ✅ | ✅ | ✅ | `@auth0/nextjs-auth0` |
| Keycloak | — | — | — | — | — | `keycloak` (self-hosted) |

## Analytics / Tracking

| Service | Country | GDPR | AVV | SCC | Cookie | Pattern |
|---------|---------|------|-----|-----|--------|---------|
| Google Analytics 4 | USA | ❌ | ✅ | ✅ | ✅ REQUIRED | `gtag`, `googletagmanager.com` |
| Plausible | Germany | ✅ | ✅ | — | — | `plausible.io` |
| PostHog | USA/EU | ⚠️ | ✅ | ⚠️ | ✅ | `posthog-js` |
| Hotjar | USA | ❌ | ✅ | ✅ | ✅ REQUIRED | `hotjar` |

## Detection Logic in the Scout

```
Priority: package.json > .env.example > source code > live URL

1. package.json    → npm package name matches pattern
2. docker-compose  → image name or service URL
3. source code     → import statements, API domain constants
4. .env.example    → variable names (e.g. STRIPE_SECRET_KEY)
5. live URL scan   → Cloudflare detects domains
```
