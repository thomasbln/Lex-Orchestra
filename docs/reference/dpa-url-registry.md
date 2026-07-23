# DPA-URL Registry

> **Core feature of Lex-Orchestra:**
> The Scout detects third-party services in the code →
> Neo4j immediately delivers the direct link to the provider's DPA/AVV →
> The user knows without any research where to sign their AVV.

## Why This Matters

Signing an AVV does not mean creating your own document.
It means: **accepting the provider's DPA and archiving it.**

Every provider has its own contract. Stripe has a DPA,
Hetzner has an AV-Vertrag, Anthropic has a Data Processing Addendum.
The user must find the provider's document, accept it (often via click-through),
and document internally that they have done so.

Lex-Orchestra makes exactly this step visible automatically:
scan repo → detect services → output AVV links directly.

## How It Works

```
Scout detects: "Anthropic" in requirements.txt + .env.example
     ↓
Neo4j: Service {name: "Anthropic", avv_required: true, dpa_url: "https://..."}
     ↓
DocumentArchitect: AVV draft contains link to Anthropic DPA
     ↓
Scan report: "⚠️ Anthropic (USA) — SCCs required → https://..."
```

## Service Registry with AVV Links

### AI / LLM

| Service | Country | DSGVO Status | AVV Link |
|---|---|---|---|
| Anthropic | USA 🇺🇸 | ⚠️ SCCs required | [DPA](https://www.anthropic.com/legal/data-processing-addendum) |
| OpenAI | USA 🇺🇸 | ⚠️ SCCs required | [DPA](https://openai.com/policies/data-processing-addendum) |
| Google Gemini | USA 🇺🇸 | ⚠️ SCCs required | [DPA](https://cloud.google.com/terms/data-processing-addendum) |
| Mistral AI | France 🇫🇷 | ✅ EU-intern | [DPA](https://mistral.ai/terms/dpa) |
| Hugging Face | USA 🇺🇸 | ⚠️ SCCs required | [DPA](https://huggingface.co/legal/data-processing-agreement) |

### Hosting / Cloud

| Service | Country | DSGVO Status | AVV Link |
|---|---|---|---|
| Hetzner | Germany 🇩🇪 | ✅ EU-intern | [AV-Vertrag](https://www.hetzner.com/AV/) |
| AWS | USA 🇺🇸 | ⚠️ SCCs required | [DPA](https://aws.amazon.com/de/agreement/data-processing/) |
| Google Cloud | USA 🇺🇸 | ⚠️ SCCs required | [DPA](https://cloud.google.com/terms/data-processing-addendum) |
| Azure | USA 🇺🇸 | ⚠️ SCCs required | [DPA](https://servicetrust.microsoft.com/ViewPage/MSComplianceGuideV3) |
| DigitalOcean | USA 🇺🇸 | ⚠️ SCCs required | [DPA](https://www.digitalocean.com/legal/data-processing-agreement) |
| Vercel | USA 🇺🇸 | ⚠️ SCCs required | [DPA](https://vercel.com/legal/dpa) |
| Netlify | USA 🇺🇸 | ⚠️ SCCs required | [DPA](https://www.netlify.com/legal/data-processing-agreement/) |
| Render | USA 🇺🇸 | ⚠️ SCCs required | [Privacy](https://render.com/privacy) |
| Railway | USA 🇺🇸 | ⚠️ SCCs required | [Privacy](https://railway.app/legal/privacy) |
| Fly.io | USA 🇺🇸 | ⚠️ SCCs required | [Privacy](https://fly.io/legal/privacy-policy) |
| Cloudflare | USA 🇺🇸 | ⚠️ SCCs required | [DPA](https://www.cloudflare.com/cloudflare-customer-dpa/) |
| Coolify | EU 🇪🇺 | ✅ Self-hosted/EU | [Privacy](https://coolify.io/docs/privacy) |

### Payment

| Service | Country | DSGVO Status | AVV Link |
|---|---|---|---|
| Stripe | USA 🇺🇸 | ⚠️ SCCs required | [DPA](https://stripe.com/de/legal/dpa) |
| PayPal | USA 🇺🇸 | ⚠️ SCCs required | [DPA](https://www.paypal.com/de/legalhub/paypal/data-processing-agreement) |

### Backend / BaaS / Database

| Service | Country | DSGVO Status | AVV Link |
|---|---|---|---|
| Supabase | USA 🇺🇸 | ⚠️ SCCs required | [DPA](https://supabase.com/legal/dpa) |
| Firebase | USA 🇺🇸 | ⚠️ SCCs required | [DPA](https://firebase.google.com/terms/data-processing-terms) |
| Neon | USA 🇺🇸 | ⚠️ SCCs required | [DPA](https://neon.tech/dpa) |
| PlanetScale | USA 🇺🇸 | ⚠️ SCCs required | [DPA](https://planetscale.com/legal/data-processing-addendum) |

### Email / SMS / Communication

| Service | Country | DSGVO Status | AVV Link |
|---|---|---|---|
| Resend | USA 🇺🇸 | ⚠️ SCCs required | [DPA](https://resend.com/legal/dpa) |
| SendGrid | USA 🇺🇸 | ⚠️ SCCs required | [DPA](https://www.twilio.com/en-us/legal/data-protection-addendum) |
| Postmark | USA 🇺🇸 | ⚠️ SCCs required | [DPA](https://wildbit.com/dpa) |
| Mailchimp | USA 🇺🇸 | ⚠️ SCCs required | [DPA](https://mailchimp.com/legal/data-processing-addendum/) |
| Twilio | USA 🇺🇸 | ⚠️ SCCs required | [DPA](https://www.twilio.com/en-us/legal/data-protection-addendum) |

### Auth

| Service | Country | DSGVO Status | AVV Link |
|---|---|---|---|
| Auth0 / Okta | USA 🇺🇸 | ⚠️ SCCs required | [DPA](https://auth0.com/docs/secure/data-privacy-and-compliance/gdpr/gdpr-data-processing-addendum) |
| Clerk | USA 🇺🇸 | ⚠️ SCCs required | [DPA](https://clerk.com/legal/dpa) |

### Analytics / Monitoring

| Service | Country | DSGVO Status | AVV Link |
|---|---|---|---|
| Google Analytics | USA 🇺🇸 | ⚠️ SCCs required | [DPA](https://business.safety.google/adsprocessorterms/) |
| Mixpanel | USA 🇺🇸 | ⚠️ SCCs required | [DPA](https://mixpanel.com/legal/dpa/) |
| PostHog | USA 🇺🇸 | ⚠️ SCCs required | [DPA](https://posthog.com/dpa) |
| Plausible | Germany 🇩🇪 | ✅ EU-intern | [DPA](https://plausible.io/dpa) |
| Sentry | USA 🇺🇸 | ⚠️ SCCs required | [DPA](https://sentry.io/legal/dpa/) |
| Datadog | USA 🇺🇸 | ⚠️ SCCs required | [DPA](https://www.datadoghq.com/legal/data-processing-addendum/) |

### CRM / Support

| Service | Country | DSGVO Status | AVV Link |
|---|---|---|---|
| HubSpot | USA 🇺🇸 | ⚠️ SCCs required | [DPA](https://legal.hubspot.com/dpa) |
| Intercom | USA 🇺🇸 | ⚠️ SCCs required | [DPA](https://www.intercom.com/legal/data-processing-agreement) |

### Version Control / CI/CD

| Service | Country | DSGVO Status | AVV Link |
|---|---|---|---|
| GitHub | USA 🇺🇸 | ⚠️ SCCs required | [DPA](https://github.com/customer-terms/github-data-protection-agreement) |
| GitHub Actions | USA 🇺🇸 | ⚠️ SCCs required | [DPA](https://github.com/customer-terms/github-data-protection-agreement) |

### Storage / Media

| Service | Country | DSGVO Status | AVV Link |
|---|---|---|---|
| AWS S3 | USA 🇺🇸 | ⚠️ SCCs required | [DPA](https://aws.amazon.com/de/agreement/data-processing/) |
| Cloudinary | USA 🇺🇸 | ⚠️ SCCs required | [DPA](https://cloudinary.com/gdpr/data-processing-addendum) |

### Security / Infrastructure

| Service | Country | DSGVO Status | AVV Link |
|---|---|---|---|
| HashiCorp Vault | USA 🇺🇸 | ⚠️ SCCs required | [Privacy](https://www.hashicorp.com/privacy) |

---

## What does "SCCs required" mean?

Standard Contractual Clauses (SCCs) pursuant to DSGVO Art. 46 para. 2 lit. c are
required when a provider is based outside the EU and no
EU adequacy decision exists (as is the case for the USA).

**In practice this means:**
1. Accept the provider's DPA (usually click-through)
2. Execute SCCs as an annex to the DPA (many providers include these)
3. Document a Transfer Impact Assessment (TIA)
4. Archive internally

---

## Neo4j Graph — dpa_url Property

All services in the graph have a `dpa_url` property:

```cypher
// Query all services with DPA link
MATCH (s:Service)
WHERE s.avv_required = true
RETURN s.name, s.country, s.gdpr_adequate, s.dpa_url
ORDER BY s.category, s.name
```

```cypher
// Check services without DPA link (should return 0)
MATCH (s:Service)
WHERE s.avv_required = true AND s.dpa_url IS NULL
RETURN s.name
```

---

## Scan Output Example

After a scan, the scan report lists the DPA obligations:

```
DPA required — please complete:

⚠️ Anthropic (USA) — SCCs required
   → https://www.anthropic.com/legal/data-processing-addendum

⚠️ Supabase (USA) — SCCs required
   → https://supabase.com/legal/dpa

✅ Hetzner (Germany) — EU-adequate
   → https://www.hetzner.com/AV/
```

And in the generated AVV document (`avv_<run_id>.md`):

```markdown
## § 1 Vertragsgegenstand

- **Anthropic** (USA) — SCCs erforderlich
  → AVV abschließen: https://www.anthropic.com/legal/data-processing-addendum

- **Supabase** (USA) — SCCs erforderlich
  → AVV abschließen: https://supabase.com/legal/dpa
```

---

## Extending the Registry

Add new services in the seed layer `src/graph/layers/00_global/00_services_global.cypher`:

```cypher
MERGE (s:Service {name: "NeuerService"})
ON CREATE SET
  s.category      = "hosting",
  s.country       = "USA",
  s.gdpr_adequate = false,
  s.avv_required  = true,
  s.dpa_url       = "https://neuerservice.com/dpa",
  s.domains       = ["neuerservice.com"];

// Relationships
MATCH (s:Service {name: "NeuerService"}), (d:DocumentType {type: "AVV"})
MERGE (s)-[:REQUIRES]->(d);
MATCH (s:Service {name: "NeuerService"}), (c:Country {name: "USA"})
MERGE (s)-[:LOCATED_IN]->(c);
```

Then run the seed:
```bash
python src/graph/seed.py
```

---

*Last updated: 2026-03-23 — 36 services with dpa_url*
*All links manually verified — official DPA/AVV pages of the respective providers.*
