// ADR-100 §4.1 — data_subjects normalization (string → list[str])
// Allowlist: customers, end_users, employees, website_visitors
// Source mapping: patch11 mapping proposal (internal working notes)
// Applied: 2026-04-22

// [customers]
MATCH (s:Service) WHERE s.name IN ["Stripe", "PayPal", "HubSpot", "Intercom", "Mailchimp"]
SET s.data_subjects = ["customers"];

// [end_users] — hosting, DBs, LLM APIs, vector DBs, email, storage, monitoring
MATCH (s:Service) WHERE s.name IN [
  "Vercel", "Netlify", "AWS", "Google Cloud", "Azure", "DigitalOcean", "Render",
  "Railway", "Fly.io", "Coolify",
  "PlanetScale", "Neon", "Hetzner", "MariaDB", "AWS RDS", "Redis",
  "OpenAI", "Anthropic", "Google Gemini", "Mistral AI",
  "Pinecone", "Weaviate", "Qdrant", "ChromaDB",
  "Google Firestore", "MongoDB Atlas", "Elasticsearch",
  "Resend", "Postmark", "SendGrid",
  "Supabase", "Firebase",
  "Sentry", "Datadog",
  "pgvector",
  "AWS S3", "Cloudinary"
]
SET s.data_subjects = ["end_users"];

// [employees]
MATCH (s:Service) WHERE s.name IN ["GitHub", "GitHub Actions"]
SET s.data_subjects = ["employees"];

// [website_visitors]
MATCH (s:Service) WHERE s.name = "Google Analytics"
SET s.data_subjects = ["website_visitors"];

// [customers, end_users]
MATCH (s:Service) WHERE s.name = "Twilio"
SET s.data_subjects = ["customers", "end_users"];

// [website_visitors, end_users]
MATCH (s:Service) WHERE s.name IN ["Plausible", "Mixpanel", "PostHog", "Cloudflare"]
SET s.data_subjects = ["website_visitors", "end_users"];

// [end_users, employees]
MATCH (s:Service) WHERE s.name IN ["Auth0", "Clerk", "Langfuse", "Hugging Face", "Google Cloud Authentication"]
SET s.data_subjects = ["end_users", "employees"];

// stub nodes + integrations not in original string-migration
MATCH (s:Service) WHERE s.name IN ["Amplitude", "Segment"]
SET s.data_subjects = ["website_visitors", "end_users"];

MATCH (s:Service) WHERE s.name IN ["Braintree", "Mollie"]
SET s.data_subjects = ["customers"];

MATCH (s:Service) WHERE s.name IN ["Chroma", "MongoDB", "Replicate", "Telegram", "Firecrawl"]
SET s.data_subjects = ["end_users"];

// "Mistral AI EU" is a catalog stub (ADR-082 Marketplace), NOT a scanned compliance
// service — its compliance data_subjects live on the 'Mistral AI' (ai_llm) node.
// Keep [] so the ADR-100 seed validator (non-null) stays green. See ADR-106 / ADR-124.
MATCH (s:Service) WHERE s.name = "Mistral AI EU"
SET s.data_subjects = [];

MATCH (s:Service) WHERE s.name = "HashiCorp Vault"
SET s.data_subjects = ["employees"];

// eRecht24 processes no end-user personal data (legal template API)
MATCH (s:Service) WHERE s.name = "eRecht24"
SET s.data_subjects = [];
