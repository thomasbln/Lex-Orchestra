// ============================================================
// LEX-ORCHESTRA — Neo4j Knowledge Graph Seed
// Idempotent: MERGE-only, safe to re-run at any time
// ============================================================


// ============================================================
// BLOCK A — SERVICE REGISTRY
// dpa_url: SET (not ON CREATE SET) so existing nodes are updated on re-seed
// ============================================================

// Payment
MERGE (s:Service {name: "Stripe"})
ON CREATE SET s.category = "payment", s.country = "USA", s.gdpr_adequate = false,
              s.dpa_required = true, s.ai_act_relevant = false, s.domains = ["stripe.com", "api.stripe.com"]
SET s.dpa_url = "https://stripe.com/de/legal/dpa";

MERGE (s:Service {name: "PayPal"})
ON CREATE SET s.category = "payment", s.country = "USA", s.gdpr_adequate = false,
              s.dpa_required = true, s.ai_act_relevant = false, s.domains = ["paypal.com", "api.paypal.com"]
SET s.dpa_url = "https://www.paypal.com/de/legalhub/paypal/data-processing-agreement";

// Backend / BaaS
MERGE (s:Service {name: "Supabase"})
ON CREATE SET s.category = "baas", s.country = "USA", s.gdpr_adequate = false,
              s.dpa_required = true, s.ai_act_relevant = false, s.domains = ["supabase.co", "supabase.com"]
SET s.dpa_url = "https://supabase.com/legal/dpa";

MERGE (s:Service {name: "Firebase"})
ON CREATE SET s.category = "baas", s.country = "USA", s.gdpr_adequate = false,
              s.dpa_required = true, s.ai_act_relevant = false, s.domains = ["firebase.google.com", "firebaseapp.com"]
SET s.dpa_url = "https://firebase.google.com/terms/data-processing-terms";

MERGE (s:Service {name: "PlanetScale"})
ON CREATE SET s.category = "database", s.country = "USA", s.gdpr_adequate = false,
              s.dpa_required = true, s.ai_act_relevant = false, s.domains = ["planetscale.com"]
SET s.dpa_url = "https://planetscale.com/legal/data-processing-addendum";

MERGE (s:Service {name: "Neon"})
ON CREATE SET s.category = "database", s.country = "USA", s.gdpr_adequate = false,
              s.dpa_required = true, s.ai_act_relevant = false, s.domains = ["neon.tech"]
SET s.dpa_url = "https://neon.tech/dpa";

// Email / Messaging
MERGE (s:Service {name: "Resend"})
ON CREATE SET s.category = "email", s.country = "USA", s.gdpr_adequate = false,
              s.dpa_required = true, s.ai_act_relevant = false, s.domains = ["resend.com", "api.resend.com"]
SET s.dpa_url = "https://resend.com/legal/dpa";

MERGE (s:Service {name: "SendGrid"})
ON CREATE SET s.category = "email", s.country = "USA", s.gdpr_adequate = false,
              s.dpa_required = true, s.ai_act_relevant = false, s.domains = ["sendgrid.com", "api.sendgrid.com"]
SET s.dpa_url = "https://www.twilio.com/en-us/legal/data-protection-addendum";

MERGE (s:Service {name: "Mailchimp"})
ON CREATE SET s.category = "email_marketing", s.country = "USA", s.gdpr_adequate = false,
              s.dpa_required = true, s.ai_act_relevant = false, s.domains = ["mailchimp.com", "list-manage.com"]
SET s.dpa_url = "https://mailchimp.com/legal/data-processing-addendum/";

MERGE (s:Service {name: "Postmark"})
ON CREATE SET s.category = "email", s.country = "USA", s.gdpr_adequate = false,
              s.dpa_required = true, s.ai_act_relevant = false, s.domains = ["postmarkapp.com"]
SET s.dpa_url = "https://wildbit.com/dpa";

MERGE (s:Service {name: "Twilio"})
ON CREATE SET s.category = "sms", s.country = "USA", s.gdpr_adequate = false,
              s.dpa_required = true, s.ai_act_relevant = false, s.domains = ["twilio.com", "api.twilio.com"]
SET s.dpa_url = "https://www.twilio.com/en-us/legal/data-protection-addendum";

// AI / LLM
MERGE (s:Service {name: "OpenAI"})
ON CREATE SET s.category = "ai_llm", s.country = "USA", s.gdpr_adequate = false,
              s.dpa_required = true, s.ai_act_relevant = true, s.domains = ["openai.com", "api.openai.com"]
SET s.dpa_url = "https://openai.com/policies/data-processing-addendum";

MERGE (s:Service {name: "Anthropic"})
ON CREATE SET s.category = "ai_llm", s.country = "USA", s.gdpr_adequate = false,
              s.dpa_required = true, s.ai_act_relevant = true, s.domains = ["anthropic.com", "api.anthropic.com"]
SET s.dpa_url = "https://www.anthropic.com/legal/data-processing-addendum";

MERGE (s:Service {name: "Google Gemini"})
ON CREATE SET s.category = "ai_llm", s.country = "USA", s.gdpr_adequate = false,
              s.dpa_required = true, s.ai_act_relevant = true, s.domains = ["generativelanguage.googleapis.com"]
SET s.dpa_url = "https://cloud.google.com/terms/data-processing-addendum";

MERGE (s:Service {name: "Mistral AI"})
ON CREATE SET s.category = "ai_llm", s.country = "France", s.gdpr_adequate = true,
              s.dpa_required = true, s.ai_act_relevant = true, s.domains = ["api.mistral.ai"]
SET s.dpa_url = "https://mistral.ai/terms/dpa";

MERGE (s:Service {name: "Hugging Face"})
ON CREATE SET s.category = "ai_platform", s.country = "USA", s.gdpr_adequate = false,
              s.dpa_required = true, s.ai_act_relevant = true, s.domains = ["huggingface.co", "api-inference.huggingface.co"]
SET s.dpa_url = "https://huggingface.co/legal/data-processing-agreement";

// Hosting / Infrastructure
MERGE (s:Service {name: "Vercel"})
ON CREATE SET s.category = "hosting", s.country = "USA", s.gdpr_adequate = false,
              s.dpa_required = true, s.ai_act_relevant = false, s.domains = ["vercel.com", "vercel.app"]
SET s.dpa_url = "https://vercel.com/legal/dpa";

MERGE (s:Service {name: "Netlify"})
ON CREATE SET s.category = "hosting", s.country = "USA", s.gdpr_adequate = false,
              s.dpa_required = true, s.ai_act_relevant = false, s.domains = ["netlify.com", "netlify.app"]
SET s.dpa_url = "https://www.netlify.com/legal/data-processing-agreement/";

MERGE (s:Service {name: "AWS"})
ON CREATE SET s.category = "cloud", s.country = "USA", s.gdpr_adequate = false,
              s.dpa_required = true, s.ai_act_relevant = false, s.domains = ["amazonaws.com", "aws.amazon.com"]
SET s.dpa_url = "https://aws.amazon.com/de/agreement/data-processing/";

MERGE (s:Service {name: "Google Cloud"})
ON CREATE SET s.category = "cloud", s.country = "USA", s.gdpr_adequate = false,
              s.dpa_required = true, s.ai_act_relevant = false, s.domains = ["googleapis.com", "cloud.google.com"]
SET s.dpa_url = "https://cloud.google.com/terms/data-processing-addendum";

MERGE (s:Service {name: "Cloudflare"})
ON CREATE SET s.category = "cdn_security", s.country = "USA", s.gdpr_adequate = false,
              s.dpa_required = true, s.ai_act_relevant = false, s.domains = ["cloudflare.com", "cloudflareinsights.com"]
SET s.dpa_url = "https://www.cloudflare.com/cloudflare-customer-dpa/";

MERGE (s:Service {name: "Hetzner"})
ON CREATE SET s.category = "hosting", s.country = "Germany", s.gdpr_adequate = true,
              s.dpa_required = true, s.ai_act_relevant = false, s.domains = ["hetzner.com", "hetzner.de"]
SET s.dpa_url = "https://www.hetzner.com/AV/";

// Auth
MERGE (s:Service {name: "Auth0"})
ON CREATE SET s.category = "auth", s.country = "USA", s.gdpr_adequate = false,
              s.dpa_required = true, s.ai_act_relevant = false, s.domains = ["auth0.com", "okta.com"]
SET s.dpa_url = "https://auth0.com/docs/secure/data-privacy-and-compliance/gdpr/gdpr-data-processing-addendum";

MERGE (s:Service {name: "Clerk"})
ON CREATE SET s.category = "auth", s.country = "USA", s.gdpr_adequate = false,
              s.dpa_required = true, s.ai_act_relevant = false, s.domains = ["clerk.com", "clerk.dev"]
SET s.dpa_url = "https://clerk.com/legal/dpa";

// Analytics / Monitoring
MERGE (s:Service {name: "Google Analytics"})
ON CREATE SET s.category = "analytics", s.country = "USA", s.gdpr_adequate = false,
              s.dpa_required = true, s.ai_act_relevant = false, s.domains = ["google-analytics.com", "analytics.google.com"]
SET s.dpa_url = "https://business.safety.google/adsprocessorterms/";

MERGE (s:Service {name: "Plausible"})
ON CREATE SET s.category = "analytics", s.country = "Germany", s.gdpr_adequate = true,
              s.dpa_required = true, s.ai_act_relevant = false, s.domains = ["plausible.io"]
SET s.dpa_url = "https://plausible.io/dpa";

MERGE (s:Service {name: "Mixpanel"})
ON CREATE SET s.category = "analytics", s.country = "USA", s.gdpr_adequate = false,
              s.dpa_required = true, s.ai_act_relevant = false, s.domains = ["mixpanel.com", "api.mixpanel.com"]
SET s.dpa_url = "https://mixpanel.com/legal/dpa/";

MERGE (s:Service {name: "PostHog"})
ON CREATE SET s.category = "analytics", s.country = "USA", s.gdpr_adequate = false,
              s.dpa_required = true, s.ai_act_relevant = false, s.domains = ["posthog.com", "app.posthog.com"]
SET s.dpa_url = "https://posthog.com/dpa";

MERGE (s:Service {name: "Sentry"})
ON CREATE SET s.category = "monitoring", s.country = "USA", s.gdpr_adequate = false,
              s.dpa_required = true, s.ai_act_relevant = false, s.domains = ["sentry.io", "o0.ingest.sentry.io"]
SET s.dpa_url = "https://sentry.io/legal/dpa/";

MERGE (s:Service {name: "Datadog"})
ON CREATE SET s.category = "monitoring", s.country = "USA", s.gdpr_adequate = false,
              s.dpa_required = true, s.ai_act_relevant = false, s.domains = ["datadoghq.com", "logs.datadoghq.com"]
SET s.dpa_url = "https://www.datadoghq.com/legal/data-processing-addendum/";

// CRM / Marketing
MERGE (s:Service {name: "HubSpot"})
ON CREATE SET s.category = "crm", s.country = "USA", s.gdpr_adequate = false,
              s.dpa_required = true, s.ai_act_relevant = false, s.domains = ["hubspot.com", "api.hubspot.com"]
SET s.dpa_url = "https://legal.hubspot.com/dpa";

MERGE (s:Service {name: "Intercom"})
ON CREATE SET s.category = "crm_support", s.country = "USA", s.gdpr_adequate = false,
              s.dpa_required = true, s.ai_act_relevant = false, s.domains = ["intercom.com", "widget.intercom.io"]
SET s.dpa_url = "https://www.intercom.com/legal/data-processing-agreement";

// Version Control / CI/CD
MERGE (s:Service {name: "GitHub"})
ON CREATE SET s.category = "vcs", s.country = "USA", s.gdpr_adequate = false,
              s.dpa_required = false, s.ai_act_relevant = false, s.domains = ["github.com", "api.github.com"]
SET s.dpa_url = "https://github.com/customer-terms/github-data-protection-agreement";

MERGE (s:Service {name: "GitHub Actions"})
ON CREATE SET s.category = "ci_cd", s.country = "USA", s.gdpr_adequate = false,
              s.dpa_required = true, s.ai_act_relevant = false, s.domains = ["github.com"]
SET s.dpa_url = "https://github.com/customer-terms/github-data-protection-agreement";

// Storage
MERGE (s:Service {name: "AWS S3"})
ON CREATE SET s.category = "storage", s.country = "USA", s.gdpr_adequate = false,
              s.dpa_required = true, s.ai_act_relevant = false, s.domains = ["s3.amazonaws.com"]
SET s.dpa_url = "https://aws.amazon.com/de/agreement/data-processing/";

MERGE (s:Service {name: "Cloudinary"})
ON CREATE SET s.category = "media_storage", s.country = "USA", s.gdpr_adequate = false,
              s.dpa_required = true, s.ai_act_relevant = false, s.domains = ["cloudinary.com", "res.cloudinary.com"]
SET s.dpa_url = "https://cloudinary.com/gdpr/data-processing-addendum";

// Additional Cloud / Hosting
MERGE (s:Service {name: "Azure"})
ON CREATE SET s.category = "cloud", s.country = "USA",
              s.gdpr_adequate = false, s.dpa_required = true,
              s.ai_act_relevant = false, s.domains = ["azure.microsoft.com", "azure.com"]
SET s.dpa_url = "https://servicetrust.microsoft.com/ViewPage/MSComplianceGuideV3";

MERGE (s:Service {name: "DigitalOcean"})
ON CREATE SET s.category = "cloud", s.country = "USA",
              s.gdpr_adequate = false, s.dpa_required = true,
              s.ai_act_relevant = false, s.domains = ["digitalocean.com", "ondigitalocean.app"]
SET s.dpa_url = "https://www.digitalocean.com/legal/data-processing-agreement";

MERGE (s:Service {name: "Render"})
ON CREATE SET s.category = "hosting", s.country = "USA",
              s.gdpr_adequate = false, s.dpa_required = true,
              s.ai_act_relevant = false, s.domains = ["render.com", "onrender.com"]
SET s.dpa_url = "https://render.com/privacy";

MERGE (s:Service {name: "Railway"})
ON CREATE SET s.category = "hosting", s.country = "USA",
              s.gdpr_adequate = false, s.dpa_required = true,
              s.ai_act_relevant = false, s.domains = ["railway.app", "up.railway.app"]
SET s.dpa_url = "https://railway.app/legal/privacy";

MERGE (s:Service {name: "Fly.io"})
ON CREATE SET s.category = "hosting", s.country = "USA",
              s.gdpr_adequate = false, s.dpa_required = true,
              s.ai_act_relevant = false, s.domains = ["fly.io", "fly.dev"]
SET s.dpa_url = "https://fly.io/legal/privacy-policy";

MERGE (s:Service {name: "Coolify"})
ON CREATE SET s.category = "hosting", s.country = "EU",
              s.gdpr_adequate = true, s.dpa_required = false,
              s.ai_act_relevant = false, s.domains = ["coolify.io"]
SET s.dpa_url = "https://coolify.io/docs/privacy";

MERGE (s:Service {name: "HashiCorp Vault"})
ON CREATE SET s.category = "security", s.country = "USA",
              s.gdpr_adequate = false, s.dpa_required = false,
              s.ai_act_relevant = false, s.domains = ["vaultproject.io", "hashicorp.com"]
SET s.dpa_url = "https://www.hashicorp.com/privacy";


// ============================================================
// SERVICE DATA PROPERTIES
// SET (not ON CREATE) — always refreshed on re-seed
// data_categories, data_subjects, processing_purpose, deletion_period
// ============================================================

MATCH (s:Service {name: "Anthropic"})
SET s.data_categories = "API-Anfragen, Modell-Inputs und -Outputs, ggf. personenbezogene Inhalte in Prompts",
    s.data_subjects = "Endnutzer der Anwendung, Entwickler",
    s.processing_purpose = "KI-gestützte Textgenerierung und -verarbeitung",
    s.deletion_period = "Gemäß Anthropic DPA — keine dauerhafte Speicherung von Prompts";

MATCH (s:Service {name: "OpenAI"})
SET s.data_categories = "API-Anfragen, Modell-Inputs und -Outputs, ggf. personenbezogene Inhalte in Prompts",
    s.data_subjects = "Endnutzer der Anwendung, Entwickler",
    s.processing_purpose = "KI-gestützte Textgenerierung und -verarbeitung",
    s.deletion_period = "Gemäß OpenAI DPA — kein Training auf API-Daten per default";

MATCH (s:Service {name: "Google Gemini"})
SET s.data_categories = "API-Anfragen, Modell-Inputs und -Outputs, ggf. personenbezogene Inhalte in Prompts",
    s.data_subjects = "Endnutzer der Anwendung, Entwickler",
    s.processing_purpose = "KI-gestützte Textgenerierung und -verarbeitung",
    s.deletion_period = "Gemäß Google Cloud DPA";

MATCH (s:Service {name: "Mistral AI"})
SET s.data_categories = "API-Anfragen, Modell-Inputs und -Outputs, ggf. personenbezogene Inhalte in Prompts",
    s.data_subjects = "Endnutzer der Anwendung, Entwickler",
    s.processing_purpose = "KI-gestützte Textgenerierung und -verarbeitung",
    s.deletion_period = "Gemäß Mistral DPA — EU-Anbieter";

MATCH (s:Service {name: "Hugging Face"})
SET s.data_categories = "Modell-Inputs und -Outputs, API-Anfragen, ggf. Trainingsdaten",
    s.data_subjects = "Entwickler, Endnutzer der Anwendung",
    s.processing_purpose = "KI-Modell-Hosting, Inference, Model-Hub",
    s.deletion_period = "Gemäß Hugging Face DPA";

MATCH (s:Service {name: "Stripe"})
SET s.data_categories = "Zahlungsdaten, Kreditkartendaten (tokenisiert), Rechnungsadressen, Transaktionsdaten",
    s.data_subjects = "Käufer, Kunden, Karteninhaber",
    s.processing_purpose = "Zahlungsabwicklung, Betrugsprävention, Rechnungsstellung",
    s.deletion_period = "Gemäß Stripe DPA — Finanzdaten bis 7 Jahre (gesetzliche Aufbewahrungspflicht)";

MATCH (s:Service {name: "PayPal"})
SET s.data_categories = "Zahlungsdaten, PayPal-Kontodaten, Transaktionshistorie, Rechnungsadressen",
    s.data_subjects = "Käufer, Kunden, PayPal-Kontoinhaber",
    s.processing_purpose = "Zahlungsabwicklung, Checkout, Betrugsprävention",
    s.deletion_period = "Finanzdaten 7 Jahre gesetzliche Aufbewahrungspflicht";

MATCH (s:Service {name: "Supabase"})
SET s.data_categories = "Anwendungsdaten, Nutzerdaten, Authentifizierungsdaten, Logs, Datenbankinhalt",
    s.data_subjects = "Endnutzer der Anwendung, registrierte Nutzer",
    s.processing_purpose = "Datenbankhosting, Authentifizierung, Storage, Realtime-Funktionen",
    s.deletion_period = "Auf Anfrage des Verantwortlichen — konfigurierbar";

MATCH (s:Service {name: "Firebase"})
SET s.data_categories = "Anwendungsdaten, Nutzerdaten, Authentifizierungsdaten, Realtime-Daten, Push-Token",
    s.data_subjects = "Endnutzer der Anwendung, registrierte Nutzer",
    s.processing_purpose = "Backend-as-a-Service, Authentifizierung, Realtime-Datenbank, Storage",
    s.deletion_period = "Bei App-Löschung oder auf Anfrage — gemäß Google Cloud DPA";

MATCH (s:Service {name: "PlanetScale"})
SET s.data_categories = "Anwendungsdaten, Datenbankinhalt, Verbindungs-Logs",
    s.data_subjects = "Endnutzer der Anwendung (indirekt)",
    s.processing_purpose = "Datenbankhosting, Datenspeicherung",
    s.deletion_period = "Bei Projekt-Löschung — gemäß DPA";

MATCH (s:Service {name: "Neon"})
SET s.data_categories = "Anwendungsdaten, Datenbankinhalt, Verbindungs-Logs",
    s.data_subjects = "Endnutzer der Anwendung (indirekt)",
    s.processing_purpose = "Datenbankhosting, Datenspeicherung",
    s.deletion_period = "Bei Projekt-Löschung — gemäß DPA";

MATCH (s:Service {name: "Resend"})
SET s.data_categories = "E-Mail-Adressen, E-Mail-Inhalte, Versand-Metadaten, Delivery-Logs",
    s.data_subjects = "E-Mail-Empfänger",
    s.processing_purpose = "Transaktionale E-Mails, E-Mail-Zustellung",
    s.deletion_period = "Event-Logs 30-90 Tage — gemäß DPA";

MATCH (s:Service {name: "SendGrid"})
SET s.data_categories = "E-Mail-Adressen, E-Mail-Inhalte, Versand-Metadaten, Öffnungs- und Klickraten",
    s.data_subjects = "E-Mail-Empfänger, Newsletter-Abonnenten",
    s.processing_purpose = "Transaktionale E-Mails, Marketing-E-Mails, E-Mail-Zustellung",
    s.deletion_period = "Gemäß Twilio DPA — Event-Daten 30 Tage";

MATCH (s:Service {name: "Mailchimp"})
SET s.data_categories = "E-Mail-Adressen, Namen, Kampagnen-Interaktionen, Öffnungs- und Klickraten, Segmentierungsdaten",
    s.data_subjects = "Newsletter-Abonnenten, Kontakte",
    s.processing_purpose = "E-Mail-Marketing, Newsletter, Marketing-Automation",
    s.deletion_period = "Bei Listen-Löschung oder Konto-Kündigung";

MATCH (s:Service {name: "Postmark"})
SET s.data_categories = "E-Mail-Adressen, E-Mail-Inhalte, Versand-Metadaten, Delivery-Logs",
    s.data_subjects = "E-Mail-Empfänger",
    s.processing_purpose = "Transaktionale E-Mails, E-Mail-Zustellung",
    s.deletion_period = "Event-Logs 30-90 Tage — gemäß DPA";

MATCH (s:Service {name: "Twilio"})
SET s.data_categories = "Telefonnummern, SMS-Inhalte, Anruf-Metadaten, Kommunikationsdaten",
    s.data_subjects = "SMS-Empfänger, Anrufpartner",
    s.processing_purpose = "SMS-Versand, Sprachkommunikation, 2FA",
    s.deletion_period = "Nachrichten-Logs 30 Tage — gemäß Twilio DPA";

MATCH (s:Service {name: "Vercel"})
SET s.data_categories = "Server-Logs, IP-Adressen, technische Verbindungsdaten, gehostete Anwendungsdaten",
    s.data_subjects = "Endnutzer der Anwendung (indirekt), Entwickler",
    s.processing_purpose = "Server-Hosting, Cloud-Infrastruktur, Compute, Storage",
    s.deletion_period = "Gemäß jeweiligem DPA — bei Service-Kündigung";

MATCH (s:Service {name: "Netlify"})
SET s.data_categories = "Server-Logs, IP-Adressen, technische Verbindungsdaten, gehostete Anwendungsdaten",
    s.data_subjects = "Endnutzer der Anwendung (indirekt), Entwickler",
    s.processing_purpose = "Server-Hosting, Cloud-Infrastruktur, Compute, Storage",
    s.deletion_period = "Gemäß jeweiligem DPA — bei Service-Kündigung";

MATCH (s:Service {name: "AWS"})
SET s.data_categories = "Server-Logs, IP-Adressen, technische Verbindungsdaten, gehostete Anwendungsdaten",
    s.data_subjects = "Endnutzer der Anwendung (indirekt), Entwickler",
    s.processing_purpose = "Server-Hosting, Cloud-Infrastruktur, Compute, Storage",
    s.deletion_period = "Gemäß jeweiligem DPA — bei Service-Kündigung";

MATCH (s:Service {name: "AWS S3"})
SET s.data_categories = "Dateien und Objekte aller Art, ggf. personenbezogene Daten in gespeicherten Dateien",
    s.data_subjects = "Nutzer deren Daten gespeichert werden (indirekt)",
    s.processing_purpose = "Objekt-Storage, Datei-Hosting, Backup",
    s.deletion_period = "Bei Objekt-/Bucket-Löschung — konfigurierbar";

MATCH (s:Service {name: "Google Cloud"})
SET s.data_categories = "Server-Logs, IP-Adressen, technische Verbindungsdaten, gehostete Anwendungsdaten",
    s.data_subjects = "Endnutzer der Anwendung (indirekt), Entwickler",
    s.processing_purpose = "Server-Hosting, Cloud-Infrastruktur, Compute, Storage",
    s.deletion_period = "Gemäß jeweiligem DPA — bei Service-Kündigung";

MATCH (s:Service {name: "Azure"})
SET s.data_categories = "Server-Logs, IP-Adressen, technische Verbindungsdaten, gehostete Anwendungsdaten",
    s.data_subjects = "Endnutzer der Anwendung (indirekt), Entwickler",
    s.processing_purpose = "Server-Hosting, Cloud-Infrastruktur, Compute, Storage",
    s.deletion_period = "Gemäß jeweiligem DPA — bei Service-Kündigung";

MATCH (s:Service {name: "DigitalOcean"})
SET s.data_categories = "Server-Logs, IP-Adressen, technische Verbindungsdaten, gehostete Anwendungsdaten",
    s.data_subjects = "Endnutzer der Anwendung (indirekt), Entwickler",
    s.processing_purpose = "Server-Hosting, Cloud-Infrastruktur, Compute, Storage",
    s.deletion_period = "Gemäß jeweiligem DPA — bei Service-Kündigung";

MATCH (s:Service {name: "Render"})
SET s.data_categories = "Server-Logs, IP-Adressen, technische Verbindungsdaten, gehostete Anwendungsdaten",
    s.data_subjects = "Endnutzer der Anwendung (indirekt), Entwickler",
    s.processing_purpose = "Server-Hosting, Cloud-Infrastruktur, Compute, Storage",
    s.deletion_period = "Gemäß jeweiligem DPA — bei Service-Kündigung";

MATCH (s:Service {name: "Railway"})
SET s.data_categories = "Server-Logs, IP-Adressen, technische Verbindungsdaten, gehostete Anwendungsdaten",
    s.data_subjects = "Endnutzer der Anwendung (indirekt), Entwickler",
    s.processing_purpose = "Server-Hosting, Cloud-Infrastruktur, Compute, Storage",
    s.deletion_period = "Gemäß jeweiligem DPA — bei Service-Kündigung";

MATCH (s:Service {name: "Fly.io"})
SET s.data_categories = "Server-Logs, IP-Adressen, technische Verbindungsdaten, gehostete Anwendungsdaten",
    s.data_subjects = "Endnutzer der Anwendung (indirekt), Entwickler",
    s.processing_purpose = "Server-Hosting, Cloud-Infrastruktur, Compute, Storage",
    s.deletion_period = "Gemäß jeweiligem DPA — bei Service-Kündigung";

MATCH (s:Service {name: "Cloudflare"})
SET s.data_categories = "IP-Adressen, HTTP-Anfragen, DNS-Anfragen, Security-Logs",
    s.data_subjects = "Website-Besucher, API-Nutzer",
    s.processing_purpose = "CDN, DDoS-Schutz, DNS, WAF",
    s.deletion_period = "Gemäß Cloudflare DPA — Logs max. 30 Tage";

MATCH (s:Service {name: "Hetzner"})
SET s.data_categories = "Server-Logs, IP-Adressen, technische Verbindungsdaten",
    s.data_subjects = "Endnutzer der Anwendung (indirekt)",
    s.processing_purpose = "Server-Hosting, Infrastruktur-Bereitstellung",
    s.deletion_period = "Gemäß Hetzner AV-Vertrag — Log-Daten 7 Tage default";

MATCH (s:Service {name: "Auth0"})
SET s.data_categories = "Authentifizierungsdaten, E-Mail-Adressen, Passwort-Hashes, Login-Logs, MFA-Daten",
    s.data_subjects = "Registrierte Nutzer, Mitarbeiter",
    s.processing_purpose = "Authentifizierung, Autorisierung, Identitätsmanagement",
    s.deletion_period = "Bei Konto-Löschung — gemäß DPA";

MATCH (s:Service {name: "Clerk"})
SET s.data_categories = "Authentifizierungsdaten, E-Mail-Adressen, Passwort-Hashes, Login-Logs, MFA-Daten",
    s.data_subjects = "Registrierte Nutzer, Mitarbeiter",
    s.processing_purpose = "Authentifizierung, Autorisierung, Identitätsmanagement",
    s.deletion_period = "Bei Konto-Löschung — gemäß DPA";

MATCH (s:Service {name: "Google Analytics"})
SET s.data_categories = "IP-Adressen (anonymisiert), Nutzungsverhalten, Seitenaufrufe, Session-Daten, Gerätedaten",
    s.data_subjects = "Website-Besucher",
    s.processing_purpose = "Web-Analyse, Reichweitenmessung, Nutzerverhalten",
    s.deletion_period = "Standard 14 Monate in GA4 — konfigurierbar";

MATCH (s:Service {name: "Plausible"})
SET s.data_categories = "IP-Adressen, Nutzungsverhalten, Seitenaufrufe, Session-Daten, Gerätedaten",
    s.data_subjects = "Website-Besucher, App-Nutzer",
    s.processing_purpose = "Web-Analyse, Nutzerverhalten, Produktanalyse",
    s.deletion_period = "Konfigurierbar, standard 12-24 Monate";

MATCH (s:Service {name: "Mixpanel"})
SET s.data_categories = "IP-Adressen, Nutzungsverhalten, Seitenaufrufe, Session-Daten, Gerätedaten",
    s.data_subjects = "Website-Besucher, App-Nutzer",
    s.processing_purpose = "Web-Analyse, Nutzerverhalten, Produktanalyse",
    s.deletion_period = "Konfigurierbar, standard 12-24 Monate";

MATCH (s:Service {name: "PostHog"})
SET s.data_categories = "IP-Adressen, Nutzungsverhalten, Seitenaufrufe, Session-Daten, Gerätedaten",
    s.data_subjects = "Website-Besucher, App-Nutzer",
    s.processing_purpose = "Web-Analyse, Nutzerverhalten, Produktanalyse",
    s.deletion_period = "Konfigurierbar, standard 12-24 Monate";

MATCH (s:Service {name: "Sentry"})
SET s.data_categories = "Error-Logs, Stack-Traces, ggf. personenbezogene Daten in Fehlerberichten, IP-Adressen",
    s.data_subjects = "Anwendungsnutzer (bei Fehler)",
    s.processing_purpose = "Error-Tracking, Performance-Monitoring, Debugging",
    s.deletion_period = "Standard 90 Tage — konfigurierbar bis 365 Tage";

MATCH (s:Service {name: "Datadog"})
SET s.data_categories = "Anwendungs-Logs, Metriken, Traces, Performance-Daten, ggf. personenbezogene Daten in Logs",
    s.data_subjects = "Anwendungsnutzer (indirekt über Logs)",
    s.processing_purpose = "Monitoring, Observability, APM, Log-Management",
    s.deletion_period = "Logs 15 Monate default — konfigurierbar";

MATCH (s:Service {name: "HubSpot"})
SET s.data_categories = "Kontaktdaten, E-Mail-Adressen, Kommunikationshistorie, CRM-Einträge, Support-Tickets",
    s.data_subjects = "Kunden, Interessenten, Kontakte",
    s.processing_purpose = "CRM, Kundenkommunikation, Support, Marketing-Automation",
    s.deletion_period = "Auf Anfrage, standard bei Vertragsende";

MATCH (s:Service {name: "Intercom"})
SET s.data_categories = "Kontaktdaten, E-Mail-Adressen, Kommunikationshistorie, CRM-Einträge, Support-Tickets",
    s.data_subjects = "Kunden, Interessenten, Kontakte",
    s.processing_purpose = "CRM, Kundenkommunikation, Support, Marketing-Automation",
    s.deletion_period = "Auf Anfrage, standard bei Vertragsende";

MATCH (s:Service {name: "GitHub Actions"})
SET s.data_categories = "Source-Code, Build-Logs, Environment-Variablen, CI/CD-Artefakte",
    s.data_subjects = "Entwickler, Contributor",
    s.processing_purpose = "CI/CD-Automatisierung, Build, Test, Deploy",
    s.deletion_period = "Logs 90 Tage — konfigurierbar";

MATCH (s:Service {name: "Cloudinary"})
SET s.data_categories = "Bild- und Videodateien, Mediendaten, ggf. personenbezogene Inhalte in Medien",
    s.data_subjects = "Nutzer die Medien hochladen, Endnutzer",
    s.processing_purpose = "Medien-Hosting, Bildoptimierung, CDN-Auslieferung",
    s.deletion_period = "Bei Asset-Löschung — gemäß DPA";


// ============================================================
// BLOCK B — RECHTSQUELLEN UND ARTIKEL
// ============================================================

MERGE (l:Law {name: "DSGVO", article: "28"})
ON CREATE SET l.title = "Auftragsverarbeiter (DPA-Pflicht)",
              l.short = "DSGVO Art. 28";

MERGE (l:Law {name: "DSGVO", article: "46"})
ON CREATE SET l.title = "Übermittlung vorbehaltlich geeigneter Garantien (SCCs)",
              l.short = "DSGVO Art. 46";

MERGE (l:Law {name: "DSGVO", article: "13"})
ON CREATE SET l.title = "Informationspflicht bei Direkterhebung",
              l.short = "DSGVO Art. 13";

MERGE (l:Law {name: "DSGVO", article: "14"})
ON CREATE SET l.title = "Informationspflicht bei Dritterhebung",
              l.short = "DSGVO Art. 14";

MERGE (l:Law {name: "DSGVO", article: "30"})
ON CREATE SET l.title = "Verzeichnis von Verarbeitungstätigkeiten (VVT)",
              l.short = "DSGVO Art. 30";

MERGE (l:Law {name: "DSGVO", article: "32"})
ON CREATE SET l.title = "Sicherheit der Verarbeitung (TOM)",
              l.short = "DSGVO Art. 32";

MERGE (l:Law {name: "DSGVO", article: "37"})
ON CREATE SET l.title = "Benennung eines Datenschutzbeauftragten",
              l.short = "DSGVO Art. 37";

MERGE (l:Law {name: "EU AI Act", article: "6"})
ON CREATE SET l.title = "Einstufung als Hochrisiko-KI-System",
              l.short = "EU AI Act Art. 6";

MERGE (l:Law {name: "EU AI Act", article: "52"})
ON CREATE SET l.title = "Transparenzpflichten für bestimmte KI-Systeme",
              l.short = "EU AI Act Art. 52";

MERGE (l:Law {name: "EU AI Act", article: "51"})
ON CREATE SET l.title = "Klassifizierung von GPAI-Modellen",
              l.short = "EU AI Act Art. 51";

MERGE (l:Law {name: "DDG", article: "5"})
ON CREATE SET
  l.title        = "Impressumspflicht (Anbieterkennzeichnung)",
  l.short        = "DDG § 5",
  l.regulation   = "Digitale-Dienste-Gesetz (DDG)",
  l.source       = "BGBl. I 2024 Nr. 149 — gesetze-im-internet.de/ddg/",
  l.valid_from   = date("2024-05-14"),
  l.applies_from = date("2024-05-14"),
  l.confidence   = 1.0,
  l.note_de      = "Ersetzt TMG § 5 seit 14.05.2024."
SET l.last_verified = date("2026-03-21");

MERGE (l:Law {name: "UWG", article: "5a"})
ON CREATE SET l.title = "Irreführung durch Unterlassen (Impressum B2B)",
              l.short = "UWG § 5a";

MERGE (l:Law {name: "TTDSG", article: "25"})
ON CREATE SET l.title = "Schutz der Privatsphäre bei Endeinrichtungen (Cookies)",
              l.short = "TTDSG § 25";

MERGE (l:Law {name: "BGB", article: "305-310"})
ON CREATE SET l.title = "AGB-Recht — Einbeziehung und Inhaltskontrolle",
              l.short = "BGB §§ 305-310";

MERGE (l:Law {name: "BGB", article: "312g"})
ON CREATE SET l.title = "Widerrufsrecht bei Fernabsatzverträgen",
              l.short = "BGB § 312g";

MERGE (l:Law {name: "PAngV", article: "1"})
ON CREATE SET l.title = "Preisangabenpflicht gegenüber Verbrauchern",
              l.short = "PAngV § 1";


// ============================================================
// BLOCK C — DOKUMENT-TYPEN
// ============================================================

MERGE (d:DocumentType {type: "DPA"})
ON CREATE SET d.name_de = "Auftragsverarbeitungsvertrag",
              d.required_for = "Alle Auftragsverarbeiter die personenbezogene Daten verarbeiten",
              d.path_template = "/legal/drafts/dpa_{service}.md";

MERGE (d:DocumentType {type: "SCC"})
ON CREATE SET d.name_de = "Standardvertragsklauseln (EU-US)",
              d.required_for = "Datentransfer in Drittländer ohne Angemessenheitsbeschluss",
              d.path_template = "/legal/drafts/scc_{service}.md";

MERGE (d:DocumentType {type: "TOM"})
ON CREATE SET d.name_de = "Technisch-organisatorische Maßnahmen",
              d.required_for = "Nachweis angemessener Sicherheit gem. DSGVO Art. 32",
              d.path_template = "/legal/tom.md";

MERGE (d:DocumentType {type: "Datenschutzerklaerung"})
ON CREATE SET d.name_de = "Datenschutzerklärung",
              d.required_for = "Informationspflicht gegenüber Betroffenen",
              d.path_template = "/legal/datenschutz.md";

MERGE (d:DocumentType {type: "Impressum"})
ON CREATE SET d.name_de = "Impressum / Anbieterkennzeichnung",
              d.required_for = "Gesetzliche Pflicht für gewerbliche Websites (DDG § 5)",
              d.path_template = "/legal/impressum.md";

MERGE (d:DocumentType {type: "AI_Act_Manifest"})
ON CREATE SET d.name_de = "EU AI Act Risiko-Manifest",
              d.required_for = "Transparenzpflicht für KI-Systeme gem. EU AI Act",
              d.path_template = "/legal/ai_act_manifest.md";

MERGE (d:DocumentType {type: "VVT"})
ON CREATE SET d.name_de = "Verzeichnis von Verarbeitungstätigkeiten",
              d.required_for = "Dokumentationspflicht gem. DSGVO Art. 30",
              d.path_template = "/legal/vvt.md";

MERGE (d:DocumentType {type: "Cookie_Consent"})
ON CREATE SET d.name_de = "Cookie-Einwilligung / Consent Banner",
              d.required_for = "Nicht-notwendige Cookies gem. TTDSG § 25",
              d.path_template = "/legal/drafts/cookie_check.md";

MERGE (d:DocumentType {type: "Audit_Report"})
ON CREATE SET d.name_de = "Compliance Audit Report",
              d.required_for = "Interner Nachweis der Compliance-Prüfung",
              d.path_template = "/legal/audit_report.md";

MERGE (d:DocumentType {type: "AGB"})
ON CREATE SET
  d.name_de = "Allgemeine Geschäftsbedingungen",
  d.required_for = "B2C-Shops, SaaS mit Endkunden, Marketplaces",
  d.business_types = ["shop", "saas_b2c", "marketplace"],
  d.legal_basis = "BGB §§ 305-310",
  d.path_template = "/legal/drafts/agb.md";

MERGE (d:DocumentType {type: "Widerrufsbelehrung"})
ON CREATE SET
  d.name_de = "Widerrufsbelehrung / Widerrufsformular",
  d.required_for = "Alle B2C-Fernabsatzverträge gem. §§ 312g, 355 BGB",
  d.business_types = ["shop", "saas_b2c"],
  d.legal_basis = "BGB §§ 312g, 355, 356",
  d.note = "14-Tage Widerrufsfrist. Muster-Widerrufsformular gesetzlich vorgeschrieben.",
  d.path_template = "/legal/drafts/widerruf.md";

MERGE (d:DocumentType {type: "Preisangaben"})
ON CREATE SET
  d.name_de = "Preisangaben / Preistransparenz",
  d.required_for = "B2C-Shops — Bruttopreise, Versandkosten, Grundpreise",
  d.business_types = ["shop"],
  d.legal_basis = "PAngV § 1",
  d.path_template = "/legal/drafts/preisangaben.md";

MERGE (d:DocumentType {type: "Lieferbedingungen"})
ON CREATE SET
  d.name_de = "Liefer- und Versandbedingungen",
  d.required_for = "Online-Shops mit physischem Warenversand",
  d.business_types = ["shop_physical"],
  d.legal_basis = "BGB § 312j",
  d.path_template = "/legal/drafts/lieferbedingungen.md";


// ============================================================
// BLOCK D — LÄNDER + TRANSFER-MECHANISMEN
// ============================================================

MERGE (c:Country {name: "USA"})
ON CREATE SET c.gdpr_adequate = false, c.requires_sccs = true,
              c.note = "Kein Angemessenheitsbeschluss. SCCs + TIA erforderlich.";

MERGE (c:Country {name: "Germany"})
ON CREATE SET c.gdpr_adequate = true, c.requires_sccs = false,
              c.note = "EU-Mitgliedstaat. DSGVO direkt anwendbar.";

MERGE (c:Country {name: "France"})
ON CREATE SET c.gdpr_adequate = true, c.requires_sccs = false,
              c.note = "EU-Mitgliedstaat. DSGVO direkt anwendbar.";

MERGE (c:Country {name: "Ireland"})
ON CREATE SET c.gdpr_adequate = true, c.requires_sccs = false,
              c.note = "EU-Mitgliedstaat. Viele Tech-Konzerne mit EU-Sitz hier.";

MERGE (c:Country {name: "UK"})
ON CREATE SET c.gdpr_adequate = true, c.requires_sccs = false,
              c.note = "Angemessenheitsbeschluss seit 2021 (UK GDPR). Überprüfung 2025.";

MERGE (c:Country {name: "Canada"})
ON CREATE SET c.gdpr_adequate = true, c.requires_sccs = false,
              c.note = "Partieller Angemessenheitsbeschluss für kommerzielle Organisationen (PIPEDA).";

MERGE (c:Country {name: "India"})
ON CREATE SET c.gdpr_adequate = false, c.requires_sccs = true,
              c.note = "Kein Angemessenheitsbeschluss. SCCs erforderlich.";

MERGE (c:Country {name: "China"})
ON CREATE SET c.gdpr_adequate = false, c.requires_sccs = true,
              c.note = "Kein Angemessenheitsbeschluss. Erhöhtes Risiko.";

// Transfer-Mechanismen
MERGE (t:TransferMechanism {name: "SCCs"})
ON CREATE SET t.name_de = "Standardvertragsklauseln",
              t.legal_basis = "DSGVO Art. 46 Abs. 2 lit. c",
              t.article = "DSGVO_46",
              t.note = "Modulares System (2021). Zusätzlich: Transfer Impact Assessment (TIA) empfohlen.";

MERGE (t:TransferMechanism {name: "BCR"})
ON CREATE SET t.name_de = "Binding Corporate Rules",
              t.legal_basis = "DSGVO Art. 46 Abs. 2 lit. b",
              t.article = "DSGVO_46",
              t.note = "Nur für konzerninterne Transfers. Genehmigungspflichtig.";

MERGE (t:TransferMechanism {name: "Angemessenheitsbeschluss"})
ON CREATE SET t.name_de = "Angemessenheitsbeschluss der EU-Kommission",
              t.legal_basis = "DSGVO Art. 45",
              t.article = "DSGVO_45",
              t.note = "Kein gesonderter Vertrag nötig. Gilt für: UK, Canada, Japan, u.a.";


// ============================================================
// BLOCK E — RISIKOSTUFEN EU AI ACT
// ============================================================

MERGE (r:RiskLevel {level: "Unacceptable", act: "EU_AI_Act"})
ON CREATE SET r.description = "Verbotene KI-Praktiken (Art. 5): Social Scoring, biometrische Fernidentifikation in Echtzeit im öffentlichen Raum, Manipulation des Unterbewusstseins",
              r.action = "Einsatz verboten";

MERGE (r:RiskLevel {level: "High", act: "EU_AI_Act"})
ON CREATE SET r.description = "Hochrisiko-KI (Anhang III): Beschäftigung, Bildung, Kreditwürdigkeit, biometrische Kategorisierung, kritische Infrastruktur",
              r.action = "Konformitätsbewertung, Registrierung EU-Datenbank, menschliche Aufsicht, Dokumentation";

MERGE (r:RiskLevel {level: "Limited", act: "EU_AI_Act"})
ON CREATE SET r.description = "Begrenzte Risiken: Chatbots, Deepfakes, emotionserkennendes KI — Transparenzpflicht gegenüber Nutzern",
              r.action = "Transparenzpflicht: Nutzer müssen wissen, dass sie mit KI interagieren";

MERGE (r:RiskLevel {level: "Minimal", act: "EU_AI_Act"})
ON CREATE SET r.description = "Minimales Risiko: KI-Spamfilter, KI in Videospielen, einfache Empfehlungsalgorithmen",
              r.action = "Keine regulatorischen Pflichten. Freiwilliger Verhaltenskodex empfohlen.";

MERGE (r:RiskLevel {level: "GPAI", act: "EU_AI_Act"})
ON CREATE SET r.description = "General Purpose AI (GPAI): Foundation Models wie GPT-4, Claude, Gemini. Ab 10^25 FLOPs: systemisches Risiko",
              r.action = "Technische Dokumentation, Urheberrechtsrichtlinie, GPAI-Code of Practice";


// ============================================================
// RELATIONSHIPS
// ============================================================

// Services → DocumentTypes (DPA für alle dpa_required Services)
MATCH (s:Service {name: "Stripe"}), (d:DocumentType {type: "DPA"})
MERGE (s)-[:REQUIRES]->(d);
MATCH (s:Service {name: "Stripe"}), (d:DocumentType {type: "SCC"})
MERGE (s)-[:REQUIRES]->(d);

MATCH (s:Service {name: "Supabase"}), (d:DocumentType {type: "DPA"})
MERGE (s)-[:REQUIRES]->(d);
MATCH (s:Service {name: "Supabase"}), (d:DocumentType {type: "SCC"})
MERGE (s)-[:REQUIRES]->(d);

MATCH (s:Service {name: "Resend"}), (d:DocumentType {type: "DPA"})
MERGE (s)-[:REQUIRES]->(d);
MATCH (s:Service {name: "Resend"}), (d:DocumentType {type: "SCC"})
MERGE (s)-[:REQUIRES]->(d);

MATCH (s:Service {name: "OpenAI"}), (d:DocumentType {type: "DPA"})
MERGE (s)-[:REQUIRES]->(d);
MATCH (s:Service {name: "OpenAI"}), (d:DocumentType {type: "SCC"})
MERGE (s)-[:REQUIRES]->(d);
MATCH (s:Service {name: "OpenAI"}), (d:DocumentType {type: "AI_Act_Manifest"})
MERGE (s)-[:REQUIRES]->(d);

MATCH (s:Service {name: "Anthropic"}), (d:DocumentType {type: "DPA"})
MERGE (s)-[:REQUIRES]->(d);
MATCH (s:Service {name: "Anthropic"}), (d:DocumentType {type: "SCC"})
MERGE (s)-[:REQUIRES]->(d);
MATCH (s:Service {name: "Anthropic"}), (d:DocumentType {type: "AI_Act_Manifest"})
MERGE (s)-[:REQUIRES]->(d);

MATCH (s:Service {name: "Google Analytics"}), (d:DocumentType {type: "DPA"})
MERGE (s)-[:REQUIRES]->(d);
MATCH (s:Service {name: "Google Analytics"}), (d:DocumentType {type: "SCC"})
MERGE (s)-[:REQUIRES]->(d);
MATCH (s:Service {name: "Google Analytics"}), (d:DocumentType {type: "Cookie_Consent"})
MERGE (s)-[:REQUIRES]->(d);

MATCH (s:Service {name: "Vercel"}), (d:DocumentType {type: "DPA"})
MERGE (s)-[:REQUIRES]->(d);
MATCH (s:Service {name: "Vercel"}), (d:DocumentType {type: "SCC"})
MERGE (s)-[:REQUIRES]->(d);

MATCH (s:Service {name: "Cloudflare"}), (d:DocumentType {type: "DPA"})
MERGE (s)-[:REQUIRES]->(d);
MATCH (s:Service {name: "Cloudflare"}), (d:DocumentType {type: "SCC"})
MERGE (s)-[:REQUIRES]->(d);

MATCH (s:Service {name: "Sentry"}), (d:DocumentType {type: "DPA"})
MERGE (s)-[:REQUIRES]->(d);
MATCH (s:Service {name: "Sentry"}), (d:DocumentType {type: "SCC"})
MERGE (s)-[:REQUIRES]->(d);

MATCH (s:Service {name: "AWS"}), (d:DocumentType {type: "DPA"})
MERGE (s)-[:REQUIRES]->(d);
MATCH (s:Service {name: "AWS"}), (d:DocumentType {type: "SCC"})
MERGE (s)-[:REQUIRES]->(d);

// All DPA-required services also require TOM (DSGVO Art. 32 — inseparable from DPA)
MATCH (s:Service {dpa_required: true}), (d:DocumentType {type: "TOM"})
MERGE (s)-[:REQUIRES]->(d);

// Services → Countries
MATCH (s:Service) WHERE s.country = "USA"
MATCH (c:Country {name: "USA"})
MERGE (s)-[:LOCATED_IN]->(c);

MATCH (s:Service) WHERE s.country = "Germany"
MATCH (c:Country {name: "Germany"})
MERGE (s)-[:LOCATED_IN]->(c);

MATCH (s:Service) WHERE s.country = "France"
MATCH (c:Country {name: "France"})
MERGE (s)-[:LOCATED_IN]->(c);

// Countries → TransferMechanisms
MATCH (c:Country {requires_sccs: true}), (t:TransferMechanism {name: "SCCs"})
MERGE (c)-[:REQUIRES_MECHANISM]->(t);

MATCH (c:Country {gdpr_adequate: true}), (t:TransferMechanism {name: "Angemessenheitsbeschluss"})
WHERE c.name IN ["UK", "Canada"]
MERGE (c)-[:COVERED_BY]->(t);

// DocumentTypes → Laws
MATCH (d:DocumentType {type: "DPA"}), (l:Law {name: "DSGVO", article: "28"})
MERGE (d)-[:BASED_ON]->(l);

MATCH (d:DocumentType {type: "SCC"}), (l:Law {name: "DSGVO", article: "46"})
MERGE (d)-[:BASED_ON]->(l);

MATCH (d:DocumentType {type: "TOM"}), (l:Law {name: "DSGVO", article: "32"})
MERGE (d)-[:BASED_ON]->(l);

MATCH (d:DocumentType {type: "Datenschutzerklaerung"}), (l:Law {name: "DSGVO", article: "13"})
MERGE (d)-[:BASED_ON]->(l);
MATCH (d:DocumentType {type: "Datenschutzerklaerung"}), (l:Law {name: "DSGVO", article: "14"})
MERGE (d)-[:BASED_ON]->(l);

MATCH (d:DocumentType {type: "VVT"}), (l:Law {name: "DSGVO", article: "30"})
MERGE (d)-[:BASED_ON]->(l);

MATCH (d:DocumentType {type: "Impressum"}), (l:Law {name: "DDG", article: "5"})
MERGE (d)-[:BASED_ON]->(l);

MATCH (d:DocumentType {type: "Cookie_Consent"}), (l:Law {name: "TTDSG", article: "25"})
MERGE (d)-[:BASED_ON]->(l);

MATCH (d:DocumentType {type: "AI_Act_Manifest"}), (l:Law {name: "EU AI Act", article: "52"})
MERGE (d)-[:BASED_ON]->(l);

// ============================================================
// BLOCK F — OWASP CONTROLS (Web Top 10 + LLM Top 10)
// ============================================================

// OWASP Web Top 10 (2021)
MERGE (c:Control {framework: "OWASP_Top10", id: "A01"})
ON CREATE SET c.title = "Broken Access Control",
              c.severity = "critical", c.dsgvo_article = "32";

MERGE (c:Control {framework: "OWASP_Top10", id: "A02"})
ON CREATE SET c.title = "Cryptographic Failures",
              c.severity = "critical", c.dsgvo_article = "32";

MERGE (c:Control {framework: "OWASP_Top10", id: "A03"})
ON CREATE SET c.title = "Injection (SQL, XSS, Command)",
              c.severity = "critical", c.dsgvo_article = "32";

MERGE (c:Control {framework: "OWASP_Top10", id: "A05"})
ON CREATE SET c.title = "Security Misconfiguration",
              c.severity = "high", c.dsgvo_article = "32";

MERGE (c:Control {framework: "OWASP_Top10", id: "A07"})
ON CREATE SET c.title = "Identification and Authentication Failures",
              c.severity = "high", c.dsgvo_article = "32";

MERGE (c:Control {framework: "OWASP_Top10", id: "A09"})
ON CREATE SET c.title = "Security Logging and Monitoring Failures",
              c.severity = "medium", c.dsgvo_article = "30";

// OWASP Top 10 for LLM Applications (v1.1)
MERGE (c:Control {framework: "OWASP_LLM_Top10", id: "LLM01"})
ON CREATE SET c.title = "Prompt Injection",
              c.severity = "critical", c.dsgvo_article = "32", c.eu_ai_act = "Art. 6";

MERGE (c:Control {framework: "OWASP_LLM_Top10", id: "LLM02"})
ON CREATE SET c.title = "Insecure Output Handling",
              c.severity = "high", c.dsgvo_article = "32";

MERGE (c:Control {framework: "OWASP_LLM_Top10", id: "LLM06"})
ON CREATE SET c.title = "Sensitive Information Disclosure",
              c.severity = "critical", c.dsgvo_article = "32";

MERGE (c:Control {framework: "OWASP_LLM_Top10", id: "LLM08"})
ON CREATE SET c.title = "Excessive Agency",
              c.severity = "high", c.dsgvo_article = "25", c.eu_ai_act = "Art. 14";

MERGE (c:Control {framework: "OWASP_LLM_Top10", id: "LLM09"})
ON CREATE SET c.title = "Overreliance",
              c.severity = "medium", c.eu_ai_act = "Art. 14";

// OWASP Controls → Laws
MATCH (c:Control {framework: "OWASP_Top10"}), (l:Law {name: "DSGVO", article: "32"})
WHERE c.dsgvo_article = "32"
MERGE (c)-[:IMPLEMENTS]->(l);

MATCH (c:Control {framework: "OWASP_Top10", id: "A09"}), (l:Law {name: "DSGVO", article: "30"})
MERGE (c)-[:IMPLEMENTS]->(l);

MATCH (c:Control {framework: "OWASP_LLM_Top10"}), (l:Law {name: "DSGVO", article: "32"})
WHERE c.dsgvo_article = "32"
MERGE (c)-[:IMPLEMENTS]->(l);

MATCH (c:Control {framework: "OWASP_LLM_Top10", id: "LLM08"}), (l:Law {name: "DSGVO", article: "25"})
MERGE (c)-[:IMPLEMENTS]->(l);

MATCH (c:Control {framework: "OWASP_LLM_Top10"}), (l:Law {name: "EU AI Act", article: "6"})
WHERE c.eu_ai_act = "Art. 6"
MERGE (c)-[:IMPLEMENTS]->(l);

// AI Services → LLM Controls (müssen LLM Top 10 beachten)
MATCH (s:Service {ai_act_relevant: true}), (c:Control {framework: "OWASP_LLM_Top10"})
MERGE (s)-[:REQUIRES_CONTROL]->(c);


// ============================================================
// Services → RiskLevels (EU AI Act)
MATCH (s:Service {name: "OpenAI"}), (r:RiskLevel {level: "GPAI"})
MERGE (s)-[:TRIGGERS_RISK]->(r);

MATCH (s:Service {name: "Anthropic"}), (r:RiskLevel {level: "GPAI"})
MERGE (s)-[:TRIGGERS_RISK]->(r);

MATCH (s:Service {name: "Google Gemini"}), (r:RiskLevel {level: "GPAI"})
MERGE (s)-[:TRIGGERS_RISK]->(r);

MATCH (s:Service {name: "Mistral AI"}), (r:RiskLevel {level: "GPAI"})
MERGE (s)-[:TRIGGERS_RISK]->(r);

MATCH (s:Service {name: "Hugging Face"}), (r:RiskLevel {level: "Limited"})
MERGE (s)-[:TRIGGERS_RISK]->(r);


// ============================================================
// BLOCK G — ISO 27001:2022 ANNEX A CONTROLS
// ============================================================

// A.5 — Policies
MERGE (c:Control {framework: "ISO_27001", id: "A.5.1.1"})
ON CREATE SET c.title = "Richtlinien zur Informationssicherheit",
              c.severity = "high", c.dsgvo_article = "32",
              c.source_pdf = "ISO-27001.pdf", c.text = "";

MERGE (c:Control {framework: "ISO_27001", id: "A.5.1.2"})
ON CREATE SET c.title = "Überprüfung der Richtlinien zur Informationssicherheit",
              c.severity = "medium", c.dsgvo_article = "32",
              c.source_pdf = "ISO-27001.pdf", c.text = "";

// A.8 — Asset Management
MERGE (c:Control {framework: "ISO_27001", id: "A.8.1.1"})
ON CREATE SET c.title = "Inventarisierung von Werten",
              c.severity = "high", c.dsgvo_article = "32",
              c.source_pdf = "ISO-27001.pdf", c.text = "";

MERGE (c:Control {framework: "ISO_27001", id: "A.8.1.2"})
ON CREATE SET c.title = "Eigentümerschaft von Werten",
              c.severity = "medium", c.dsgvo_article = "32",
              c.source_pdf = "ISO-27001.pdf", c.text = "";

MERGE (c:Control {framework: "ISO_27001", id: "A.8.2.1"})
ON CREATE SET c.title = "Klassifizierung von Informationen",
              c.severity = "medium", c.dsgvo_article = "32",
              c.source_pdf = "ISO-27001.pdf", c.text = "";

// A.9 — Access Control
MERGE (c:Control {framework: "ISO_27001", id: "A.9.1.1"})
ON CREATE SET c.title = "Zugangskontrollrichtlinie",
              c.severity = "critical", c.dsgvo_article = "32",
              c.source_pdf = "ISO-27001.pdf", c.text = "";

MERGE (c:Control {framework: "ISO_27001", id: "A.9.2.1"})
ON CREATE SET c.title = "Registrierung und Deregistrierung von Benutzern",
              c.severity = "high", c.dsgvo_article = "32",
              c.source_pdf = "ISO-27001.pdf", c.text = "";

MERGE (c:Control {framework: "ISO_27001", id: "A.9.4.1"})
ON CREATE SET c.title = "Beschränkung des Informationszugangs",
              c.severity = "high", c.dsgvo_article = "32",
              c.source_pdf = "ISO-27001.pdf", c.text = "";

// A.12 — Operations
MERGE (c:Control {framework: "ISO_27001", id: "A.12.1.1"})
ON CREATE SET c.title = "Dokumentierte Betriebsabläufe",
              c.severity = "medium", c.dsgvo_article = "32",
              c.source_pdf = "ISO-27001.pdf", c.text = "";

MERGE (c:Control {framework: "ISO_27001", id: "A.12.6.1"})
ON CREATE SET c.title = "Management technischer Schwachstellen",
              c.severity = "high", c.dsgvo_article = "32",
              c.source_pdf = "ISO-27001.pdf", c.text = "";

// A.18 — Compliance
MERGE (c:Control {framework: "ISO_27001", id: "A.18.1.1"})
ON CREATE SET c.title = "Identifizierung anzuwendender Gesetze und vertraglicher Anforderungen",
              c.severity = "high", c.dsgvo_article = "32",
              c.source_pdf = "ISO-27001.pdf", c.text = "";

MERGE (c:Control {framework: "ISO_27001", id: "A.18.1.4"})
ON CREATE SET c.title = "Datenschutz und Schutz personenbezogener Informationen",
              c.severity = "critical", c.dsgvo_article = "32",
              c.source_pdf = "ISO-27001.pdf", c.text = "";

MERGE (c:Control {framework: "ISO_27001", id: "A.18.2.1"})
ON CREATE SET c.title = "Unabhängige Überprüfung der Informationssicherheit",
              c.severity = "medium", c.dsgvo_article = "32",
              c.source_pdf = "ISO-27001.pdf", c.text = "";


// ============================================================
// BLOCK H — BSI IT-GRUNDSCHUTZ KERN-BAUSTEINE
// Source: IT-Grundschutz Kompendium Edition 2023 (BSI)
// BASIS requirements extracted from official PDF
// ============================================================

// ORP.1 — Organisation
MERGE (c:Control {framework: "BSI_Grundschutz", id: "ORP.1"})
ON CREATE SET c.title = "Organisation", c.severity = "high"
SET c.description        = "Grundlegende organisatorische Regelungen für Informationssicherheit. Festlegung von Verantwortlichkeiten, Zuständigkeiten und Prozessen als Basis des Sicherheitsmanagements.",
    c.basis_requirements = [
      "ORP.1.A1 Festlegung von Verantwortlichkeiten und Regelungen",
      "ORP.1.A2 Zuweisung der Zuständigkeiten",
      "ORP.1.A3 Beaufsichtigung oder Begleitung von Fremdpersonen",
      "ORP.1.A4 Funktionstrennung zwischen unvereinbaren Aufgaben"
    ],
    c.source = "BSI IT-Grundschutz Kompendium Edition 2023";

// OPS.1.1 — Ordnungsgemäße IT-Administration (Baustein OPS.1.1.2)
MERGE (c:Control {framework: "BSI_Grundschutz", id: "OPS.1.1"})
ON CREATE SET c.title = "Ordnungsgemäße IT-Administration", c.severity = "high"
SET c.description        = "Sichere und geregelte Administration von IT-Systemen. Personalauswahl, Administrationskennungen und Schutz privilegierter Zugriffe.",
    c.basis_requirements = [
      "OPS.1.1.A1 Personalauswahl für administrative Tätigkeiten",
      "OPS.1.1.A2 Regelungen für IT-Administrationstätigkeiten",
      "OPS.1.1.A3 Geregelte Einweisung von IT-Administrationspersonal",
      "OPS.1.1.A5 Administrationskennungen",
      "OPS.1.1.A6 Schutz administrativer Kennungen"
    ],
    c.source = "BSI IT-Grundschutz Kompendium Edition 2023";

// SYS.1.1 — Allgemeiner Server
MERGE (c:Control {framework: "BSI_Grundschutz", id: "SYS.1.1"})
ON CREATE SET c.title = "Allgemeiner Server", c.severity = "high"
SET c.description        = "Grundlegende Sicherheitsanforderungen für Server. Geeigneter Aufstellungsort, Benutzerauthentisierung, Rechtevergabe und Rollentrennung.",
    c.basis_requirements = [
      "SYS.1.1.A1 Geeigneter Aufstellungsort",
      "SYS.1.1.A2 Benutzerauthentisierung an Servern",
      "SYS.1.1.A3 Restriktive Rechtevergabe",
      "SYS.1.1.A4 Rollentrennung",
      "SYS.1.1.A6 Abschaltung nicht benötigter Dienste"
    ],
    c.source = "BSI IT-Grundschutz Kompendium Edition 2023";

// NET.1.1 — Netzarchitektur und -design
MERGE (c:Control {framework: "BSI_Grundschutz", id: "NET.1.1"})
ON CREATE SET c.title = "Netzarchitektur und -design", c.severity = "high"
SET c.description        = "Planung und Dokumentation sicherer Netzinfrastrukturen. Sicherheitsrichtlinie, Dokumentation, Anforderungsspezifikation und Netztrennung in Sicherheitszonen.",
    c.basis_requirements = [
      "NET.1.1.A1 Sicherheitsrichtlinie für das Netz",
      "NET.1.1.A2 Dokumentation des Netzes",
      "NET.1.1.A3 Anforderungsspezifikation für das Netz",
      "NET.1.1.A4 Netztrennung in Sicherheitszonen"
    ],
    c.source = "BSI IT-Grundschutz Kompendium Edition 2023";

// CON.10 — Entwicklung von Webanwendungen
MERGE (c:Control {framework: "BSI_Grundschutz", id: "CON.10"})
ON CREATE SET c.title = "Entwicklung von Webanwendungen", c.severity = "high"
SET c.description        = "Sicherheitsanforderungen für die Entwicklung von Webanwendungen. Schulung, Authentisierung, Schutz vertraulicher Daten und kontrolliertes Einbinden von Inhalten.",
    c.basis_requirements = [
      "CON.10.A1 Schulung zu webanwendungsspezifischen Sicherheitsmechanismen",
      "CON.10.A2 Authentisierung bei Webanwendungen",
      "CON.10.A3 Schutz vertraulicher Daten",
      "CON.10.A4 Kontrolliertes Einbinden von Dateien und Inhalten bei Webanwendungen"
    ],
    c.source = "BSI IT-Grundschutz Kompendium Edition 2023";

// CON.2 — enrich existing stub with PDF data
MERGE (c:Control {framework: "BSI_Grundschutz", id: "CON.2"})
ON CREATE SET c.title = "Datenschutz", c.severity = "critical"
SET c.description = "Schutz natürlicher Personen bei Datenverarbeitung. Umsetzung des Standard-Datenschutzmodells (SDM) gem. DSGVO-Anforderungen.",
    c.basis_requirements = ["CON.2.A1 Umsetzung Standard-Datenschutzmodell"],
    c.source = "BSI IT-Grundschutz Kompendium Edition 2023";

// APP.3.1 — Webanwendungen und Webservices
MERGE (c:Control {framework: "BSI_Grundschutz", id: "APP.3.1"})
ON CREATE SET
  c.title = "Webanwendungen und Webservices",
  c.severity = "high",
  c.description = "Sichere Nutzung von Webanwendungen und Webservices über HTTP(S). Schützt Informationen durch Authentisierung, Eingabevalidierung und sichere Architektur.",
  c.basis_requirements = [
    "APP.3.1.A1 Authentisierung",
    "APP.3.1.A4 Kontrolliertes Einbinden von Dateien und Inhalten",
    "APP.3.1.A7 Schutz vor unerlaubter automatisierter Nutzung",
    "APP.3.1.A14 Schutz vertraulicher Daten"
  ],
  c.source = "BSI IT-Grundschutz Kompendium Edition 2023";

MERGE (r:Requirement {id: "APP.3.1.A1", framework: "BSI_Grundschutz"})
ON CREATE SET r.title = "Authentisierung", r.level = "BASIS";
MATCH (c:Control {id: "APP.3.1", framework: "BSI_Grundschutz"}), (r:Requirement {id: "APP.3.1.A1", framework: "BSI_Grundschutz"})
MERGE (c)-[:HAS_REQUIREMENT]->(r);

MERGE (r:Requirement {id: "APP.3.1.A4", framework: "BSI_Grundschutz"})
ON CREATE SET r.title = "Kontrolliertes Einbinden von Dateien und Inhalten", r.level = "BASIS";
MATCH (c:Control {id: "APP.3.1", framework: "BSI_Grundschutz"}), (r:Requirement {id: "APP.3.1.A4", framework: "BSI_Grundschutz"})
MERGE (c)-[:HAS_REQUIREMENT]->(r);

MERGE (r:Requirement {id: "APP.3.1.A14", framework: "BSI_Grundschutz"})
ON CREATE SET r.title = "Schutz vertraulicher Daten", r.level = "BASIS";
MATCH (c:Control {id: "APP.3.1", framework: "BSI_Grundschutz"}), (r:Requirement {id: "APP.3.1.A14", framework: "BSI_Grundschutz"})
MERGE (c)-[:HAS_REQUIREMENT]->(r);

// APP.3.2 — Webserver
MERGE (c:Control {framework: "BSI_Grundschutz", id: "APP.3.2"})
ON CREATE SET
  c.title = "Webserver",
  c.severity = "high",
  c.description = "Sicherer Betrieb von Webservern. Sichere Konfiguration, TLS-Verschlüsselung, Zugriffsschutz und Protokollierung von Ereignissen.",
  c.basis_requirements = [
    "APP.3.2.A1 Sichere Konfiguration eines Webservers",
    "APP.3.2.A2 Schutz der Webserver-Dateien",
    "APP.3.2.A3 Absicherung von Datei-Uploads und -Downloads",
    "APP.3.2.A4 Protokollierung von Ereignissen",
    "APP.3.2.A5 Authentisierung",
    "APP.3.2.A7 Rechtliche Rahmenbedingungen für Webangebote",
    "APP.3.2.A11 Verschlüsselung über TLS"
  ],
  c.source = "BSI IT-Grundschutz Kompendium Edition 2023";

MERGE (r:Requirement {id: "APP.3.2.A1", framework: "BSI_Grundschutz"})
ON CREATE SET r.title = "Sichere Konfiguration eines Webservers", r.level = "BASIS";
MATCH (c:Control {id: "APP.3.2", framework: "BSI_Grundschutz"}), (r:Requirement {id: "APP.3.2.A1", framework: "BSI_Grundschutz"})
MERGE (c)-[:HAS_REQUIREMENT]->(r);

MERGE (r:Requirement {id: "APP.3.2.A11", framework: "BSI_Grundschutz"})
ON CREATE SET r.title = "Verschlüsselung über TLS", r.level = "BASIS";
MATCH (c:Control {id: "APP.3.2", framework: "BSI_Grundschutz"}), (r:Requirement {id: "APP.3.2.A11", framework: "BSI_Grundschutz"})
MERGE (c)-[:HAS_REQUIREMENT]->(r);

// APP.6 — Allgemeine Software
MERGE (c:Control {framework: "BSI_Grundschutz", id: "APP.6"})
ON CREATE SET
  c.title = "Allgemeine Software",
  c.severity = "medium",
  c.description = "Sicherer Einsatz von Software — von der Planung über sichere Beschaffung bis zur Installation und Konfiguration jeglicher Softwaretypen.",
  c.basis_requirements = [
    "APP.6.A1 Planung des Software-Einsatzes",
    "APP.6.A2 Erstellung eines Anforderungskatalogs für Software",
    "APP.6.A3 Sichere Beschaffung von Software",
    "APP.6.A4 Regelung für die Installation und Konfiguration von Software",
    "APP.6.A5 Sichere Installation von Software"
  ],
  c.source = "BSI IT-Grundschutz Kompendium Edition 2023";

// CON.1 — Kryptokonzept
MERGE (c:Control {framework: "BSI_Grundschutz", id: "CON.1"})
ON CREATE SET
  c.title = "Kryptokonzept",
  c.severity = "high",
  c.description = "Kryptografische Maßnahmen für Vertraulichkeit, Integrität und Authentizität. Auswahl geeigneter Verfahren und sicheres Schlüsselmanagement.",
  c.basis_requirements = [
    "CON.1.A1 Auswahl geeigneter kryptografischer Verfahren",
    "CON.1.A2 Datensicherung beim Einsatz kryptografischer Verfahren",
    "CON.1.A4 Geeignetes Schlüsselmanagement"
  ],
  c.source = "BSI IT-Grundschutz Kompendium Edition 2023";

MERGE (r:Requirement {id: "CON.1.A1", framework: "BSI_Grundschutz"})
ON CREATE SET r.title = "Auswahl geeigneter kryptografischer Verfahren", r.level = "BASIS";
MATCH (c:Control {id: "CON.1", framework: "BSI_Grundschutz"}), (r:Requirement {id: "CON.1.A1", framework: "BSI_Grundschutz"})
MERGE (c)-[:HAS_REQUIREMENT]->(r);

MERGE (r:Requirement {id: "CON.1.A4", framework: "BSI_Grundschutz"})
ON CREATE SET r.title = "Geeignetes Schlüsselmanagement", r.level = "BASIS";
MATCH (c:Control {id: "CON.1", framework: "BSI_Grundschutz"}), (r:Requirement {id: "CON.1.A4", framework: "BSI_Grundschutz"})
MERGE (c)-[:HAS_REQUIREMENT]->(r);

// CON.3 — Datensicherungskonzept
MERGE (c:Control {framework: "BSI_Grundschutz", id: "CON.3"})
ON CREATE SET
  c.title = "Datensicherungskonzept",
  c.severity = "high",
  c.description = "Systematische Datensicherung zur Minimierung von Datenverlust. Einflussfaktoren erheben und Verfahrensweisen für Backups festlegen.",
  c.basis_requirements = [
    "CON.3.A1 Erhebung der Einflussfaktoren für Datensicherungen",
    "CON.3.A2 Festlegung der Verfahrensweisen für die Datensicherung"
  ],
  c.source = "BSI IT-Grundschutz Kompendium Edition 2023";

MERGE (r:Requirement {id: "CON.3.A1", framework: "BSI_Grundschutz"})
ON CREATE SET r.title = "Erhebung der Einflussfaktoren für Datensicherungen", r.level = "BASIS";
MATCH (c:Control {id: "CON.3", framework: "BSI_Grundschutz"}), (r:Requirement {id: "CON.3.A1", framework: "BSI_Grundschutz"})
MERGE (c)-[:HAS_REQUIREMENT]->(r);

MERGE (r:Requirement {id: "CON.3.A2", framework: "BSI_Grundschutz"})
ON CREATE SET r.title = "Festlegung der Verfahrensweisen für die Datensicherung", r.level = "BASIS";
MATCH (c:Control {id: "CON.3", framework: "BSI_Grundschutz"}), (r:Requirement {id: "CON.3.A2", framework: "BSI_Grundschutz"})
MERGE (c)-[:HAS_REQUIREMENT]->(r);

// ORP.4 — Identitäts- und Berechtigungsmanagement
MERGE (c:Control {framework: "BSI_Grundschutz", id: "ORP.4"})
ON CREATE SET
  c.title = "Identitäts- und Berechtigungsmanagement",
  c.severity = "high",
  c.description = "Zugang zu Ressourcen auf berechtigte Personen einschränken. IAM-Prozesse, Passwortrichtlinien und Funktionstrennung.",
  c.basis_requirements = [
    "ORP.4.A1 Regelung für die Einrichtung und Löschung von Benutzenden",
    "ORP.4.A2 Einrichtung, Änderung und Entzug von Berechtigungen",
    "ORP.4.A4 Aufgabenverteilung und Funktionstrennung",
    "ORP.4.A7 Vergabe von Zugriffsrechten",
    "ORP.4.A8 Regelung des Passwortgebrauchs",
    "ORP.4.A9 Identifikation und Authentisierung",
    "ORP.4.A22 Regelung zur Passwortqualität"
  ],
  c.source = "BSI IT-Grundschutz Kompendium Edition 2023";

MERGE (r:Requirement {id: "ORP.4.A2", framework: "BSI_Grundschutz"})
ON CREATE SET r.title = "Einrichtung, Änderung und Entzug von Berechtigungen", r.level = "BASIS";
MATCH (c:Control {id: "ORP.4", framework: "BSI_Grundschutz"}), (r:Requirement {id: "ORP.4.A2", framework: "BSI_Grundschutz"})
MERGE (c)-[:HAS_REQUIREMENT]->(r);

MERGE (r:Requirement {id: "ORP.4.A9", framework: "BSI_Grundschutz"})
ON CREATE SET r.title = "Identifikation und Authentisierung", r.level = "BASIS";
MATCH (c:Control {id: "ORP.4", framework: "BSI_Grundschutz"}), (r:Requirement {id: "ORP.4.A9", framework: "BSI_Grundschutz"})
MERGE (c)-[:HAS_REQUIREMENT]->(r);

// ISMS.1 — Sicherheitsmanagement
MERGE (c:Control {framework: "BSI_Grundschutz", id: "ISMS.1"})
ON CREATE SET
  c.title = "Sicherheitsmanagement",
  c.severity = "critical",
  c.description = "Informationssicherheitsmanagement — Planungs-, Lenkungs- und Kontrollaufgaben für einen wirksamen und durchdachten Sicherheitsprozess.",
  c.basis_requirements = [
    "ISMS.1.A1 Übernahme der Gesamtverantwortung für Informationssicherheit durch die Leitung",
    "ISMS.1.A2 Festlegung der Sicherheitsziele und -strategie",
    "ISMS.1.A3 Erstellung einer Leitlinie zur Informationssicherheit",
    "ISMS.1.A4 Benennung eines oder einer Informationssicherheitsbeauftragten"
  ],
  c.source = "BSI IT-Grundschutz Kompendium Edition 2023";

MERGE (r:Requirement {id: "ISMS.1.A4", framework: "BSI_Grundschutz"})
ON CREATE SET r.title = "Benennung eines oder einer Informationssicherheitsbeauftragten", r.level = "BASIS";
MATCH (c:Control {id: "ISMS.1", framework: "BSI_Grundschutz"}), (r:Requirement {id: "ISMS.1.A4", framework: "BSI_Grundschutz"})
MERGE (c)-[:HAS_REQUIREMENT]->(r);

// OPS.1.2.5 — Fernwartung
MERGE (c:Control {framework: "BSI_Grundschutz", id: "OPS.1.2.5"})
ON CREATE SET
  c.title = "Fernwartung",
  c.severity = "high",
  c.description = "Sicherer Einsatz von Fernwartung — zeitlich begrenzter Remote-Zugriff auf IT-Systeme. Planung, Absicherung der Schnittstellen und Dokumentation.",
  c.basis_requirements = [
    "OPS.1.2.5.A1 Planung des Einsatzes der Fernwartung",
    "OPS.1.2.5.A2 Sicherer Verbindungsaufbau bei der Fernwartung von Clients",
    "OPS.1.2.5.A3 Absicherung der Schnittstellen zur Fernwartung"
  ],
  c.source = "BSI IT-Grundschutz Kompendium Edition 2023";

MERGE (r:Requirement {id: "OPS.1.2.5.A3", framework: "BSI_Grundschutz"})
ON CREATE SET r.title = "Absicherung der Schnittstellen zur Fernwartung", r.level = "BASIS";
MATCH (c:Control {id: "OPS.1.2.5", framework: "BSI_Grundschutz"}), (r:Requirement {id: "OPS.1.2.5.A3", framework: "BSI_Grundschutz"})
MERGE (c)-[:HAS_REQUIREMENT]->(r);

// OPS.2.2 — Cloud-Nutzung
MERGE (c:Control {framework: "BSI_Grundschutz", id: "OPS.2.2"})
ON CREATE SET
  c.title = "Cloud-Nutzung",
  c.severity = "high",
  c.description = "Sicheres Cloud Computing — dynamische IT-Dienstleistungen über das Netz. Strategie, Sicherheitsrichtlinie, Service-Definition und Verantwortungsbereiche.",
  c.basis_requirements = [
    "OPS.2.2.A1 Erstellung einer Strategie für die Cloud-Nutzung",
    "OPS.2.2.A2 Erstellung einer Sicherheitsrichtlinie für die Cloud-Nutzung",
    "OPS.2.2.A3 Service-Definition für Cloud-Dienste",
    "OPS.2.2.A4 Festlegung von Verantwortungsbereichen und Schnittstellen"
  ],
  c.source = "BSI IT-Grundschutz Kompendium Edition 2023";

MERGE (r:Requirement {id: "OPS.2.2.A1", framework: "BSI_Grundschutz"})
ON CREATE SET r.title = "Erstellung einer Strategie für die Cloud-Nutzung", r.level = "BASIS";
MATCH (c:Control {id: "OPS.2.2", framework: "BSI_Grundschutz"}), (r:Requirement {id: "OPS.2.2.A1", framework: "BSI_Grundschutz"})
MERGE (c)-[:HAS_REQUIREMENT]->(r);

MERGE (r:Requirement {id: "OPS.2.2.A2", framework: "BSI_Grundschutz"})
ON CREATE SET r.title = "Erstellung einer Sicherheitsrichtlinie für die Cloud-Nutzung", r.level = "BASIS";
MATCH (c:Control {id: "OPS.2.2", framework: "BSI_Grundschutz"}), (r:Requirement {id: "OPS.2.2.A2", framework: "BSI_Grundschutz"})
MERGE (c)-[:HAS_REQUIREMENT]->(r);

// DER.2.1 — Behandlung von Sicherheitsvorfällen
MERGE (c:Control {framework: "BSI_Grundschutz", id: "DER.2.1"})
ON CREATE SET
  c.title = "Behandlung von Sicherheitsvorfällen",
  c.severity = "critical",
  c.description = "Schnelle und effiziente Behandlung von Sicherheitsvorfällen. Definition, Verantwortlichkeiten, Behebung und Wiederherstellung der Betriebsumgebung.",
  c.basis_requirements = [
    "DER.2.1.A1 Definition eines Sicherheitsvorfalls",
    "DER.2.1.A2 Erstellung einer Richtlinie zur Behandlung von Sicherheitsvorfällen",
    "DER.2.1.A3 Festlegung von Verantwortlichkeiten und Ansprechpersonen",
    "DER.2.1.A4 Benachrichtigung betroffener Stellen bei Sicherheitsvorfällen",
    "DER.2.1.A5 Behebung von Sicherheitsvorfällen",
    "DER.2.1.A6 Wiederherstellung der Betriebsumgebung nach Sicherheitsvorfällen"
  ],
  c.source = "BSI IT-Grundschutz Kompendium Edition 2023";

MERGE (r:Requirement {id: "DER.2.1.A1", framework: "BSI_Grundschutz"})
ON CREATE SET r.title = "Definition eines Sicherheitsvorfalls", r.level = "BASIS";
MATCH (c:Control {id: "DER.2.1", framework: "BSI_Grundschutz"}), (r:Requirement {id: "DER.2.1.A1", framework: "BSI_Grundschutz"})
MERGE (c)-[:HAS_REQUIREMENT]->(r);

MERGE (r:Requirement {id: "DER.2.1.A5", framework: "BSI_Grundschutz"})
ON CREATE SET r.title = "Behebung von Sicherheitsvorfällen", r.level = "BASIS";
MATCH (c:Control {id: "DER.2.1", framework: "BSI_Grundschutz"}), (r:Requirement {id: "DER.2.1.A5", framework: "BSI_Grundschutz"})
MERGE (c)-[:HAS_REQUIREMENT]->(r);


// ============================================================
// BLOCK I — NIS2 RICHTLINIE (CELEX_32022L2555)
// ============================================================

MERGE (l:Law {name: "NIS2", article: "21"})
ON CREATE SET l.title = "Risikomanagement-Maßnahmen für die Netz- und Informationssicherheit",
              l.short = "NIS2 Art. 21",
              l.source_pdf = "CELEX_32022L2555_DE_TXT.pdf", l.text = "";

MERGE (l:Law {name: "NIS2", article: "23"})
ON CREATE SET l.title = "Meldepflichten bei erheblichen Sicherheitsvorfällen",
              l.short = "NIS2 Art. 23",
              l.source_pdf = "CELEX_32022L2555_DE_TXT.pdf", l.text = "";

MERGE (l:Law {name: "NIS2", article: "24"})
ON CREATE SET l.title = "Governance: Verantwortung der Leitungsorgane",
              l.short = "NIS2 Art. 24",
              l.source_pdf = "CELEX_32022L2555_DE_TXT.pdf", l.text = "";

MERGE (l:Law {name: "NIS2", article: "27"})
ON CREATE SET l.title = "Registrierung wesentlicher und wichtiger Einrichtungen",
              l.short = "NIS2 Art. 27",
              l.source_pdf = "CELEX_32022L2555_DE_TXT.pdf", l.text = "";

MERGE (l:Law {name: "NIS2", article: "32"})
ON CREATE SET l.title = "Aufsichtsmaßnahmen für wesentliche Einrichtungen",
              l.short = "NIS2 Art. 32",
              l.source_pdf = "CELEX_32022L2555_DE_TXT.pdf", l.text = "";


// ============================================================
// BLOCK J — OWASP API SECURITY TOP 10 (2023)
// ============================================================

MERGE (c:Control {framework: "OWASP_API_Top10", id: "API1"})
ON CREATE SET c.title = "Broken Object Level Authorization",
              c.severity = "critical", c.dsgvo_article = "32",
              c.source_pdf = "owasp-api-security-top-10.pdf", c.text = "";

MERGE (c:Control {framework: "OWASP_API_Top10", id: "API2"})
ON CREATE SET c.title = "Broken Authentication",
              c.severity = "critical", c.dsgvo_article = "32",
              c.source_pdf = "owasp-api-security-top-10.pdf", c.text = "";

MERGE (c:Control {framework: "OWASP_API_Top10", id: "API3"})
ON CREATE SET c.title = "Broken Object Property Level Authorization",
              c.severity = "high", c.dsgvo_article = "32",
              c.source_pdf = "owasp-api-security-top-10.pdf", c.text = "";

MERGE (c:Control {framework: "OWASP_API_Top10", id: "API4"})
ON CREATE SET c.title = "Unrestricted Resource Consumption",
              c.severity = "high", c.dsgvo_article = "32",
              c.source_pdf = "owasp-api-security-top-10.pdf", c.text = "";

MERGE (c:Control {framework: "OWASP_API_Top10", id: "API5"})
ON CREATE SET c.title = "Broken Function Level Authorization",
              c.severity = "critical", c.dsgvo_article = "32",
              c.source_pdf = "owasp-api-security-top-10.pdf", c.text = "";

MERGE (c:Control {framework: "OWASP_API_Top10", id: "API6"})
ON CREATE SET c.title = "Unrestricted Access to Sensitive Business Flows",
              c.severity = "high", c.dsgvo_article = "32",
              c.source_pdf = "owasp-api-security-top-10.pdf", c.text = "";

MERGE (c:Control {framework: "OWASP_API_Top10", id: "API7"})
ON CREATE SET c.title = "Server Side Request Forgery",
              c.severity = "high", c.dsgvo_article = "32",
              c.source_pdf = "owasp-api-security-top-10.pdf", c.text = "";

MERGE (c:Control {framework: "OWASP_API_Top10", id: "API8"})
ON CREATE SET c.title = "Security Misconfiguration",
              c.severity = "high", c.dsgvo_article = "32",
              c.source_pdf = "owasp-api-security-top-10.pdf", c.text = "";

MERGE (c:Control {framework: "OWASP_API_Top10", id: "API9"})
ON CREATE SET c.title = "Improper Inventory Management",
              c.severity = "medium", c.dsgvo_article = "32",
              c.source_pdf = "owasp-api-security-top-10.pdf", c.text = "";

MERGE (c:Control {framework: "OWASP_API_Top10", id: "API10"})
ON CREATE SET c.title = "Unsafe Consumption of APIs",
              c.severity = "medium", c.dsgvo_article = "32",
              c.source_pdf = "owasp-api-security-top-10.pdf", c.text = "";


// ============================================================
// UPDATE EXISTING NODES — source_pdf + text Properties
// ============================================================

// Bestehende Law-Nodes nachpflegen
MATCH (l:Law {name: "DSGVO"})
SET l.source_pdf = "dsgvo.pdf", l.text = coalesce(l.text, "");

MATCH (l:Law {name: "EU AI Act"})
SET l.source_pdf = "euaiact.pdf", l.text = coalesce(l.text, "");

MATCH (l:Law {name: "DDG"})
SET l.source_pdf = "", l.text = coalesce(l.text, "");

MATCH (l:Law {name: "UWG"})
SET l.source_pdf = "", l.text = coalesce(l.text, "");

MATCH (l:Law {name: "TTDSG"})
SET l.source_pdf = "", l.text = coalesce(l.text, "");

// Bestehende Control-Nodes nachpflegen
MATCH (c:Control {framework: "OWASP_Top10"})
SET c.source_pdf = "202512 - OWASP Top 10 2025 by Miglen Evlogiev.pdf",
    c.text = coalesce(c.text, "");

MATCH (c:Control {framework: "OWASP_LLM_Top10"})
SET c.source_pdf = "OWASP-Top-10-for-LLMs-v2025.pdf",
    c.text = coalesce(c.text, "");


// ============================================================
// NEUE RELATIONSHIPS
// ============================================================

// ISO 27001 Controls → DSGVO Art. 32: IMPLEMENTS
MATCH (c:Control {framework: "ISO_27001"}), (l:Law {name: "DSGVO", article: "32"})
MERGE (c)-[:IMPLEMENTS]->(l);

// BSI Grundschutz Bausteine → DSGVO Art. 32: IMPLEMENTS (select controls)
MATCH (c:Control {framework: "BSI_Grundschutz"}), (l:Law {name: "DSGVO", article: "32"})
WHERE c.id IN ["CON.1", "CON.3", "ORP.4", "DER.2.1", "APP.3.1", "APP.3.2", "ISMS.1"]
MERGE (c)-[:IMPLEMENTS]->(l);

// BSI → TOM DocumentType: CONTRIBUTES_TO
MATCH (c:Control {framework: "BSI_Grundschutz"}), (d:DocumentType {type: "TOM"})
WHERE c.id IN ["APP.3.1", "APP.3.2", "CON.1", "CON.3", "ORP.4", "ISMS.1", "DER.2.1"]
MERGE (c)-[:CONTRIBUTES_TO]->(d);

// NIS2 Art. 21 → ISO Controls A.9.x + A.12.x: BASED_ON
MATCH (l:Law {name: "NIS2", article: "21"}), (c:Control {framework: "ISO_27001"})
WHERE c.id STARTS WITH "A.9" OR c.id STARTS WITH "A.12"
MERGE (l)-[:BASED_ON]->(c);

// OWASP API Controls → DSGVO Art. 32: IMPLEMENTS
MATCH (c:Control {framework: "OWASP_API_Top10"}), (l:Law {name: "DSGVO", article: "32"})
MERGE (c)-[:IMPLEMENTS]->(l);

// AI Services → OWASP API Controls: REQUIRES_CONTROL
MATCH (s:Service {ai_act_relevant: true}), (c:Control {framework: "OWASP_API_Top10"})
MERGE (s)-[:REQUIRES_CONTROL]->(c);

// ============================================================
// NEW HOSTING SERVICES — Relationships
// ============================================================

// Azure, DigitalOcean, Render, Railway, Fly.io → USA
MATCH (s:Service), (c:Country {name: "USA"})
WHERE s.name IN ["Azure", "DigitalOcean", "Render", "Railway", "Fly.io"]
MERGE (s)-[:LOCATED_IN]->(c);

// Coolify → EU (self-hosted, EU-adequate)
MATCH (s:Service {name: "Coolify"}), (c:Country {name: "Germany"})
MERGE (s)-[:LOCATED_IN]->(c);

// USA-based new hosters → TOM required (DSGVO Art. 32)
MATCH (s:Service), (d:DocumentType {type: "TOM"})
WHERE s.name IN ["Azure", "DigitalOcean", "Render", "Railway", "Fly.io"] AND s.dpa_required = true
MERGE (s)-[:REQUIRES]->(d);

// USA-based new hosters → DPA required
MATCH (s:Service), (d:DocumentType {type: "DPA"})
WHERE s.name IN ["Azure", "DigitalOcean", "Render", "Railway", "Fly.io"] AND s.dpa_required = true
MERGE (s)-[:REQUIRES]->(d);

// USA-based new hosters → SCC required (no adequacy decision)
MATCH (s:Service), (d:DocumentType {type: "SCC"})
WHERE s.name IN ["Azure", "DigitalOcean", "Render", "Railway", "Fly.io"] AND s.gdpr_adequate = false
MERGE (s)-[:REQUIRES]->(d);

// ============================================================
// SHOP LEGAL DOCS — New DocumentType → Law relationships
// ============================================================

MATCH (d:DocumentType {type: "AGB"}), (l:Law {name: "BGB", article: "305-310"})
MERGE (d)-[:BASED_ON]->(l);

MATCH (d:DocumentType {type: "Widerrufsbelehrung"}), (l:Law {name: "BGB", article: "312g"})
MERGE (d)-[:BASED_ON]->(l);

MATCH (d:DocumentType {type: "Preisangaben"}), (l:Law {name: "PAngV", article: "1"})
MERGE (d)-[:BASED_ON]->(l);

// Cookie Consent for analytics/CRM tools
// Note: Plausible intentionally excluded — cookieless analytics, no consent required
MATCH (s:Service {name: "Mixpanel"}), (d:DocumentType {type: "Cookie_Consent"})
MERGE (s)-[:REQUIRES]->(d);

MATCH (s:Service {name: "PostHog"}), (d:DocumentType {type: "Cookie_Consent"})
MERGE (s)-[:REQUIRES]->(d);

MATCH (s:Service {name: "HubSpot"}), (d:DocumentType {type: "Cookie_Consent"})
MERGE (s)-[:REQUIRES]->(d);

MATCH (s:Service {name: "Intercom"}), (d:DocumentType {type: "Cookie_Consent"})
MERGE (s)-[:REQUIRES]->(d);

// ============================================================
// BLOCK K — CRA (Cyber Resilience Act, Regulation (EU) 2024/2847)
// Source: EUR-Lex OJ:L_202402847 (downloaded 2026-03-20)
// ============================================================

// CRA Law nodes
MERGE (l:Law {name: "CRA", article: "Annex I"})
ON CREATE SET
  l.title = "Grundlegende Cybersicherheitsanforderungen für Produkte mit digitalen Elementen",
  l.short = "CRA Anhang I",
  l.regulation = "Verordnung (EU) 2024/2847",
  l.in_force = "2024-12-10",
  l.applies_from = "2027-12-11",
  l.source = "EUR-Lex OJ:L_202402847";

MERGE (l:Law {name: "CRA", article: "13"})
ON CREATE SET
  l.title = "Pflichten der Hersteller",
  l.short = "CRA Art. 13",
  l.regulation = "Verordnung (EU) 2024/2847",
  l.applies_from = "2027-12-11",
  l.note = "Risikobewertung, Dokumentation, Supply-Chain-Sorgfalt, mind. 5 Jahre Support",
  l.source = "EUR-Lex OJ:L_202402847";

MERGE (l:Law {name: "CRA", article: "14"})
ON CREATE SET
  l.title = "Meldepflichten der Hersteller — Schwachstellen und Sicherheitsvorfälle",
  l.short = "CRA Art. 14",
  l.regulation = "Verordnung (EU) 2024/2847",
  l.applies_from = "2026-09-11",
  l.note = "24h Frühwarnung, 72h Vollmeldung, 14 Tage Abschlussbericht",
  l.source = "EUR-Lex OJ:L_202402847";

// CRA Annex I Part I — Essential cybersecurity requirements (product properties)
MERGE (r:Requirement {id: "CRA-I-1a", framework: "CRA"})
ON CREATE SET
  r.title = "Keine bekannten ausnutzbaren Schwachstellen bei Marktbereitstellung",
  r.level = "ESSENTIAL",
  r.annex = "Annex I Part I",
  r.source = "CRA Regulation (EU) 2024/2847 Annex I §2(a)";

MERGE (r:Requirement {id: "CRA-I-1b", framework: "CRA"})
ON CREATE SET
  r.title = "Sichere Standardkonfiguration und Reset-Möglichkeit",
  r.level = "ESSENTIAL",
  r.annex = "Annex I Part I",
  r.source = "CRA Regulation (EU) 2024/2847 Annex I §2(b)";

MERGE (r:Requirement {id: "CRA-I-1c", framework: "CRA"})
ON CREATE SET
  r.title = "Sicherheitsaktualisierungen möglich, inkl. automatische Updates als Standard",
  r.level = "ESSENTIAL",
  r.annex = "Annex I Part I",
  r.source = "CRA Regulation (EU) 2024/2847 Annex I §2(c)";

MERGE (r:Requirement {id: "CRA-I-1d", framework: "CRA"})
ON CREATE SET
  r.title = "Zugriffskontrolle — Authentifizierung, Identitäts- und Zugangsverwaltung",
  r.level = "ESSENTIAL",
  r.annex = "Annex I Part I",
  r.source = "CRA Regulation (EU) 2024/2847 Annex I §2(d)";

MERGE (r:Requirement {id: "CRA-I-1e", framework: "CRA"})
ON CREATE SET
  r.title = "Vertraulichkeit — Verschlüsselung gespeicherter und übertragener Daten",
  r.level = "ESSENTIAL",
  r.annex = "Annex I Part I",
  r.source = "CRA Regulation (EU) 2024/2847 Annex I §2(e)";

MERGE (r:Requirement {id: "CRA-I-1f", framework: "CRA"})
ON CREATE SET
  r.title = "Datenintegrität — Schutz vor unbefugter Manipulation, Änderungen melden",
  r.level = "ESSENTIAL",
  r.annex = "Annex I Part I",
  r.source = "CRA Regulation (EU) 2024/2847 Annex I §2(f)";

MERGE (r:Requirement {id: "CRA-I-1g", framework: "CRA"})
ON CREATE SET
  r.title = "Datenminimierung — Verarbeitung auf erforderliches Maß beschränken",
  r.level = "ESSENTIAL",
  r.annex = "Annex I Part I",
  r.source = "CRA Regulation (EU) 2024/2847 Annex I §2(g)";

MERGE (r:Requirement {id: "CRA-I-1h", framework: "CRA"})
ON CREATE SET
  r.title = "Verfügbarkeit — DoS-Resilienz, Verfügbarkeit wesentlicher Funktionen nach Sicherheitsvorfall",
  r.level = "ESSENTIAL",
  r.annex = "Annex I Part I",
  r.source = "CRA Regulation (EU) 2024/2847 Annex I §2(h)";

MERGE (r:Requirement {id: "CRA-I-1j", framework: "CRA"})
ON CREATE SET
  r.title = "Minimale Angriffsfläche — auch bei externen Schnittstellen",
  r.level = "ESSENTIAL",
  r.annex = "Annex I Part I",
  r.source = "CRA Regulation (EU) 2024/2847 Annex I §2(j)";

MERGE (r:Requirement {id: "CRA-I-1l", framework: "CRA"})
ON CREATE SET
  r.title = "Sicherheits-Logging und -Monitoring mit Opt-out-Mechanismus",
  r.level = "ESSENTIAL",
  r.annex = "Annex I Part I",
  r.source = "CRA Regulation (EU) 2024/2847 Annex I §2(l)";

// CRA Annex I Part II — Vulnerability handling requirements
MERGE (r:Requirement {id: "CRA-II-1", framework: "CRA"})
ON CREATE SET
  r.title = "SBOM erstellen — Schwachstellen und Komponenten dokumentieren",
  r.level = "ESSENTIAL",
  r.annex = "Annex I Part II",
  r.source = "CRA Regulation (EU) 2024/2847 Annex I Part II §1";

MERGE (r:Requirement {id: "CRA-II-2", framework: "CRA"})
ON CREATE SET
  r.title = "Schwachstellen unverzüglich behandeln und beheben, Sicherheitsupdates bereitstellen",
  r.level = "ESSENTIAL",
  r.annex = "Annex I Part II",
  r.source = "CRA Regulation (EU) 2024/2847 Annex I Part II §2";

MERGE (r:Requirement {id: "CRA-II-3", framework: "CRA"})
ON CREATE SET
  r.title = "Regelmäßige Sicherheitstests und -prüfungen",
  r.level = "ESSENTIAL",
  r.annex = "Annex I Part II",
  r.source = "CRA Regulation (EU) 2024/2847 Annex I Part II §3";

MERGE (r:Requirement {id: "CRA-II-5", framework: "CRA"})
ON CREATE SET
  r.title = "Strategie für koordinierte Offenlegung von Schwachstellen (CVD-Policy)",
  r.level = "ESSENTIAL",
  r.annex = "Annex I Part II",
  r.source = "CRA Regulation (EU) 2024/2847 Annex I Part II §5";

MERGE (r:Requirement {id: "CRA-II-7", framework: "CRA"})
ON CREATE SET
  r.title = "Sicherer Update-Verteilungsmechanismus für Sicherheitsupdates",
  r.level = "ESSENTIAL",
  r.annex = "Annex I Part II",
  r.source = "CRA Regulation (EU) 2024/2847 Annex I Part II §7";

// Link requirements to Law node
MATCH (l:Law {name: "CRA", article: "Annex I"}), (r:Requirement {framework: "CRA"})
WHERE r.annex IN ["Annex I Part I", "Annex I Part II"]
MERGE (l)-[:CONTAINS]->(r);

// CRA → BSI relationships
MATCH (c:Control {framework: "BSI_Grundschutz", id: "DER.2.1"}),
      (l:Law {name: "CRA", article: "14"})
MERGE (c)-[:IMPLEMENTS]->(l);

MATCH (c:Control {framework: "BSI_Grundschutz", id: "CON.1"}),
      (l:Law {name: "CRA", article: "Annex I"})
MERGE (c)-[:IMPLEMENTS]->(l);

MATCH (c:Control {framework: "BSI_Grundschutz", id: "APP.3.1"}),
      (l:Law {name: "CRA", article: "Annex I"})
MERGE (c)-[:IMPLEMENTS]->(l);

MATCH (c:Control {framework: "BSI_Grundschutz", id: "ORP.4"}),
      (l:Law {name: "CRA", article: "Annex I"})
MERGE (c)-[:IMPLEMENTS]->(l);

// CRA → ISO 27001 relationships
MATCH (c:Control {framework: "ISO_27001"}),
      (l:Law {name: "CRA", article: "Annex I"})
WHERE c.id IN ["A.8.8", "A.8.25", "A.8.27", "A.5.7"]
MERGE (c)-[:IMPLEMENTS]->(l);


// ============================================================
// BLOCK L — NIST CSF 2.0 (CSWP 29, February 2024)
// Source: https://nvlpubs.nist.gov/nistpubs/CSWP/NIST.CSWP.29.pdf
// ============================================================

// 6 Core Functions — exact titles from PDF
MERGE (c:Control {framework: "NIST_CSF_2", id: "GV"})
ON CREATE SET
  c.title = "GOVERN",
  c.severity = "critical",
  c.description = "The organization's cybersecurity risk management strategy, expectations, and policy are established, communicated, and monitored",
  c.categories = ["GV.OC", "GV.RM", "GV.RR", "GV.PO", "GV.OV", "GV.SC"],
  c.source = "NIST CSF 2.0 CSWP 29 (February 2024)";

MERGE (c:Control {framework: "NIST_CSF_2", id: "ID"})
ON CREATE SET
  c.title = "IDENTIFY",
  c.severity = "high",
  c.description = "The organization's current cybersecurity risks are understood",
  c.categories = ["ID.AM", "ID.RA", "ID.IM"],
  c.source = "NIST CSF 2.0 CSWP 29 (February 2024)";

MERGE (c:Control {framework: "NIST_CSF_2", id: "PR"})
ON CREATE SET
  c.title = "PROTECT",
  c.severity = "high",
  c.description = "Safeguards to manage the organization's cybersecurity risks are used",
  c.categories = ["PR.AA", "PR.AT", "PR.DS", "PR.PS", "PR.IR"],
  c.source = "NIST CSF 2.0 CSWP 29 (February 2024)";

MERGE (c:Control {framework: "NIST_CSF_2", id: "DE"})
ON CREATE SET
  c.title = "DETECT",
  c.severity = "high",
  c.description = "Possible cybersecurity attacks and compromises are found and analyzed",
  c.categories = ["DE.CM", "DE.AE"],
  c.source = "NIST CSF 2.0 CSWP 29 (February 2024)";

MERGE (c:Control {framework: "NIST_CSF_2", id: "RS"})
ON CREATE SET
  c.title = "RESPOND",
  c.severity = "high",
  c.description = "Actions regarding a detected cybersecurity incident are taken",
  c.categories = ["RS.MA", "RS.AN", "RS.CO", "RS.MI"],
  c.source = "NIST CSF 2.0 CSWP 29 (February 2024)";

MERGE (c:Control {framework: "NIST_CSF_2", id: "RC"})
ON CREATE SET
  c.title = "RECOVER",
  c.severity = "high",
  c.description = "Assets and operations affected by a cybersecurity incident are restored",
  c.categories = ["RC.RP", "RC.CO"],
  c.source = "NIST CSF 2.0 CSWP 29 (February 2024)";

// Key Subcategories — web apps + AI relevant (PR + DE focus)
MERGE (c:Control {framework: "NIST_CSF_2", id: "PR.AA"})
ON CREATE SET
  c.title = "Identity Management, Authentication, and Access Control",
  c.severity = "high",
  c.description = "Access to physical and logical assets is limited to authorized users, services, and hardware and managed commensurate with the assessed risk of unauthorized access",
  c.subcategories = ["PR.AA-01", "PR.AA-03", "PR.AA-05"],
  c.source = "NIST CSF 2.0 CSWP 29 (February 2024)";

MERGE (c:Control {framework: "NIST_CSF_2", id: "PR.DS"})
ON CREATE SET
  c.title = "Data Security",
  c.severity = "high",
  c.description = "Data are managed consistent with the organization's risk strategy to protect the confidentiality, integrity, and availability of information",
  c.subcategories = ["PR.DS-01", "PR.DS-02", "PR.DS-10", "PR.DS-11"],
  c.source = "NIST CSF 2.0 CSWP 29 (February 2024)";

MERGE (c:Control {framework: "NIST_CSF_2", id: "PR.PS"})
ON CREATE SET
  c.title = "Platform Security",
  c.severity = "high",
  c.description = "Hardware, software, and services of physical and virtual platforms are managed consistent with the organization's risk strategy",
  c.subcategories = ["PR.PS-01", "PR.PS-04", "PR.PS-06"],
  c.source = "NIST CSF 2.0 CSWP 29 (February 2024)";

MERGE (c:Control {framework: "NIST_CSF_2", id: "DE.CM"})
ON CREATE SET
  c.title = "Continuous Monitoring",
  c.severity = "high",
  c.description = "Assets are monitored to find anomalies, indicators of compromise, and other potentially adverse events",
  c.subcategories = ["DE.CM-01", "DE.CM-03", "DE.CM-09"],
  c.source = "NIST CSF 2.0 CSWP 29 (February 2024)";

MERGE (c:Control {framework: "NIST_CSF_2", id: "RS.MA"})
ON CREATE SET
  c.title = "Incident Management",
  c.severity = "high",
  c.description = "Responses to detected cybersecurity incidents are managed",
  c.subcategories = ["RS.MA-01", "RS.MA-02", "RS.MA-03"],
  c.source = "NIST CSF 2.0 CSWP 29 (February 2024)";

MERGE (c:Control {framework: "NIST_CSF_2", id: "ID.RA"})
ON CREATE SET
  c.title = "Risk Assessment",
  c.severity = "high",
  c.description = "The cybersecurity risk to the organization, assets, and individuals is understood",
  c.subcategories = ["ID.RA-01", "ID.RA-03", "ID.RA-05", "ID.RA-08"],
  c.source = "NIST CSF 2.0 CSWP 29 (February 2024)";

// NIST CSF → CRA: IMPLEMENTS
MATCH (c:Control {framework: "NIST_CSF_2"}),
      (l:Law {name: "CRA", article: "Annex I"})
WHERE c.id IN ["PR", "DE", "RS", "PR.AA", "PR.DS", "DE.CM"]
MERGE (c)-[:IMPLEMENTS]->(l);

// NIST CSF → DSGVO Art. 32: IMPLEMENTS
MATCH (c:Control {framework: "NIST_CSF_2"}),
      (l:Law {name: "DSGVO", article: "32"})
WHERE c.id IN ["PR.DS", "PR.AA", "DE.CM", "RS.MA"]
MERGE (c)-[:IMPLEMENTS]->(l);

// Parent → subcategory: CONTAINS
MATCH (parent:Control {framework: "NIST_CSF_2", id: "PR"}),
      (child:Control {framework: "NIST_CSF_2"})
WHERE child.id IN ["PR.AA", "PR.DS", "PR.PS"]
MERGE (parent)-[:CONTAINS]->(child);

MATCH (parent:Control {framework: "NIST_CSF_2", id: "DE"}),
      (child:Control {framework: "NIST_CSF_2", id: "DE.CM"})
MERGE (parent)-[:CONTAINS]->(child);

MATCH (parent:Control {framework: "NIST_CSF_2", id: "RS"}),
      (child:Control {framework: "NIST_CSF_2", id: "RS.MA"})
MERGE (parent)-[:CONTAINS]->(child);

MATCH (parent:Control {framework: "NIST_CSF_2", id: "ID"}),
      (child:Control {framework: "NIST_CSF_2", id: "ID.RA"})
MERGE (parent)-[:CONTAINS]->(child);

// ============================================================
// BLOCK M — COMPLETE OWASP LLM Top 10 v2025 + Web Top 10 2025
//            + NIS2 missing articles
// Source: OWASP-Top-10-for-LLMs-v2025.pdf, 202512-OWASP-Top-10-2025.pdf,
//         CELEX_32022L2555_DE_TXT.pdf
// ============================================================

// ── OWASP LLM Top 10 v2025 — missing 5 controls ────────────────────────────

MERGE (c:Control {framework: "OWASP_LLM_Top10", id: "LLM03"})
ON CREATE SET
  c.title       = "Supply Chain",
  c.severity    = "high",
  c.description = "LLM supply chains are susceptible to vulnerabilities affecting the integrity of training data, models, and deployment platforms.",
  c.source      = "OWASP Top 10 for LLM Applications v2025"
ON MATCH SET
  c.title       = "Supply Chain",
  c.source      = "OWASP Top 10 for LLM Applications v2025";

MERGE (c:Control {framework: "OWASP_LLM_Top10", id: "LLM04"})
ON CREATE SET
  c.title       = "Data and Model Poisoning",
  c.severity    = "high",
  c.description = "Data poisoning occurs when pre-training, fine-tuning, or embedding data is manipulated to introduce vulnerabilities, backdoors, or biases.",
  c.source      = "OWASP Top 10 for LLM Applications v2025"
ON MATCH SET
  c.title       = "Data and Model Poisoning",
  c.source      = "OWASP Top 10 for LLM Applications v2025";

MERGE (c:Control {framework: "OWASP_LLM_Top10", id: "LLM05"})
ON CREATE SET
  c.title       = "Improper Output Handling",
  c.severity    = "high",
  c.description = "Insufficient validation, sanitization, and handling of LLM outputs before passing downstream to other components and systems.",
  c.source      = "OWASP Top 10 for LLM Applications v2025"
ON MATCH SET
  c.title       = "Improper Output Handling",
  c.source      = "OWASP Top 10 for LLM Applications v2025";

MERGE (c:Control {framework: "OWASP_LLM_Top10", id: "LLM07"})
ON CREATE SET
  c.title       = "System Prompt Leakage",
  c.severity    = "medium",
  c.description = "System prompts used to steer LLM behavior may contain sensitive information that was not intended to be discovered.",
  c.source      = "OWASP Top 10 for LLM Applications v2025"
ON MATCH SET
  c.title       = "System Prompt Leakage",
  c.source      = "OWASP Top 10 for LLM Applications v2025";

MERGE (c:Control {framework: "OWASP_LLM_Top10", id: "LLM10"})
ON CREATE SET
  c.title       = "Unbounded Consumption",
  c.severity    = "high",
  c.description = "LLM applications that allow excessive and uncontrolled inferences, leading to denial of service, financial damage, and model cloning.",
  c.source      = "OWASP Top 10 for LLM Applications v2025"
ON MATCH SET
  c.title       = "Unbounded Consumption",
  c.source      = "OWASP Top 10 for LLM Applications v2025";

// Update source on existing 5 LLM controls
MATCH (c:Control {framework: "OWASP_LLM_Top10"})
WHERE c.id IN ["LLM01","LLM02","LLM06","LLM08","LLM09"]
SET c.source = "OWASP Top 10 for LLM Applications v2025";

// ── OWASP Web Top 10 2025 — add 4 missing + update all titles ──────────────

MERGE (c:Control {framework: "OWASP_Top10", id: "A04"})
ON CREATE SET
  c.title       = "Cryptographic Failures",
  c.severity    = "high",
  c.description = "Cryptographic failures exposing sensitive data — includes weak algorithms, unencrypted transmissions, and improper certificate validation.",
  c.source      = "OWASP Top 10 Web Application Security Risks 2025"
ON MATCH SET
  c.title       = "Cryptographic Failures",
  c.source      = "OWASP Top 10 Web Application Security Risks 2025";

MERGE (c:Control {framework: "OWASP_Top10", id: "A06"})
ON CREATE SET
  c.title       = "Insecure Design",
  c.severity    = "high",
  c.description = "Missing or ineffective security control design — risks from insecure development lifecycle and missing threat modeling.",
  c.source      = "OWASP Top 10 Web Application Security Risks 2025"
ON MATCH SET
  c.title       = "Insecure Design",
  c.source      = "OWASP Top 10 Web Application Security Risks 2025";

MERGE (c:Control {framework: "OWASP_Top10", id: "A08"})
ON CREATE SET
  c.title       = "Integrity Failures",
  c.severity    = "high",
  c.description = "Code or infrastructure not protecting against integrity violations — relies on untrusted sources for plugins, libraries, and modules.",
  c.source      = "OWASP Top 10 Web Application Security Risks 2025"
ON MATCH SET
  c.title       = "Integrity Failures",
  c.source      = "OWASP Top 10 Web Application Security Risks 2025";

MERGE (c:Control {framework: "OWASP_Top10", id: "A10"})
ON CREATE SET
  c.title       = "Mishandling of Exceptions",
  c.severity    = "medium",
  c.description = "Improper prevention, detection, or recovery from unexpected conditions leads to crashes, logic bugs, broken auth, and data loss.",
  c.source      = "OWASP Top 10 Web Application Security Risks 2025"
ON MATCH SET
  c.title       = "Mishandling of Exceptions",
  c.source      = "OWASP Top 10 Web Application Security Risks 2025";

// Update titles + source on existing 6 Web controls to 2025 version
MATCH (c:Control {framework: "OWASP_Top10", id: "A01"})
SET c.title = "Broken Access Control",
    c.source = "OWASP Top 10 Web Application Security Risks 2025";

MATCH (c:Control {framework: "OWASP_Top10", id: "A02"})
SET c.title = "Security Misconfiguration",
    c.source = "OWASP Top 10 Web Application Security Risks 2025";

MATCH (c:Control {framework: "OWASP_Top10", id: "A03"})
SET c.title = "Software Supply Chain Failures",
    c.source = "OWASP Top 10 Web Application Security Risks 2025";

MATCH (c:Control {framework: "OWASP_Top10", id: "A05"})
SET c.title = "Injection",
    c.source = "OWASP Top 10 Web Application Security Risks 2025";

MATCH (c:Control {framework: "OWASP_Top10", id: "A07"})
SET c.title = "Authentication Failures",
    c.source = "OWASP Top 10 Web Application Security Risks 2025";

MATCH (c:Control {framework: "OWASP_Top10", id: "A09"})
SET c.title = "Logging and Alerting Failures",
    c.source = "OWASP Top 10 Web Application Security Risks 2025";

// ── NIS2 — add missing articles + source attribution ───────────────────────

MERGE (l:Law {name: "NIS2", article: "2"})
ON CREATE SET
  l.title      = "Anwendungsbereich",
  l.short      = "NIS2 Art. 2",
  l.regulation = "Richtlinie (EU) 2022/2555",
  l.source     = "CELEX:32022L2555"
ON MATCH SET
  l.title      = "Anwendungsbereich",
  l.regulation = "Richtlinie (EU) 2022/2555",
  l.source     = "CELEX:32022L2555";

MERGE (l:Law {name: "NIS2", article: "3"})
ON CREATE SET
  l.title      = "Wesentliche und wichtige Einrichtungen",
  l.short      = "NIS2 Art. 3",
  l.regulation = "Richtlinie (EU) 2022/2555",
  l.source     = "CELEX:32022L2555"
ON MATCH SET
  l.title      = "Wesentliche und wichtige Einrichtungen",
  l.regulation = "Richtlinie (EU) 2022/2555",
  l.source     = "CELEX:32022L2555";

MERGE (l:Law {name: "NIS2", article: "4"})
ON CREATE SET
  l.title      = "Sektorspezifische Rechtsakte der Union",
  l.short      = "NIS2 Art. 4",
  l.regulation = "Richtlinie (EU) 2022/2555",
  l.source     = "CELEX:32022L2555"
ON MATCH SET
  l.title      = "Sektorspezifische Rechtsakte der Union",
  l.regulation = "Richtlinie (EU) 2022/2555",
  l.source     = "CELEX:32022L2555";

MERGE (l:Law {name: "NIS2", article: "6"})
ON CREATE SET
  l.title      = "Begriffsbestimmungen",
  l.short      = "NIS2 Art. 6",
  l.regulation = "Richtlinie (EU) 2022/2555",
  l.source     = "CELEX:32022L2555"
ON MATCH SET
  l.title      = "Begriffsbestimmungen",
  l.regulation = "Richtlinie (EU) 2022/2555",
  l.source     = "CELEX:32022L2555";

MERGE (l:Law {name: "NIS2", article: "7"})
ON CREATE SET
  l.title      = "Nationale Cybersicherheitsstrategie",
  l.short      = "NIS2 Art. 7",
  l.regulation = "Richtlinie (EU) 2022/2555",
  l.source     = "CELEX:32022L2555"
ON MATCH SET
  l.title      = "Nationale Cybersicherheitsstrategie",
  l.regulation = "Richtlinie (EU) 2022/2555",
  l.source     = "CELEX:32022L2555";

MERGE (l:Law {name: "NIS2", article: "10"})
ON CREATE SET
  l.title      = "Computer-Notfallteams (CSIRTs)",
  l.short      = "NIS2 Art. 10",
  l.regulation = "Richtlinie (EU) 2022/2555",
  l.source     = "CELEX:32022L2555"
ON MATCH SET
  l.title      = "Computer-Notfallteams (CSIRTs)",
  l.regulation = "Richtlinie (EU) 2022/2555",
  l.source     = "CELEX:32022L2555";

// Update existing NIS2 articles with source + regulation
MATCH (l:Law {name: "NIS2"})
WHERE l.article IN ["21","23","24","27","32"]
SET l.source     = "CELEX:32022L2555",
    l.regulation = "Richtlinie (EU) 2022/2555";

// NIS2 → DocumentType relationships
MATCH (l:Law {name: "NIS2", article: "21"}),
      (d:DocumentType {type: "TOM"})
MERGE (l)-[:REQUIRES]->(d);

MATCH (l:Law {name: "NIS2", article: "23"}),
      (d:DocumentType {type: "Audit_Report"})
MERGE (l)-[:REQUIRES]->(d);

// ── OWASP LLM Top 10 — fix titles on existing controls to v2025 ─────────────
// v1 had different numbering — v2025 reorganized:
// LLM02: Insecure Output Handling → Sensitive Information Disclosure
// LLM06: Sensitive Information Disclosure → Excessive Agency
// LLM08: Excessive Agency → Vector and Embedding Weaknesses
// LLM09: Overreliance → Misinformation

MATCH (c:Control {framework: "OWASP_LLM_Top10", id: "LLM02"})
SET c.title = "Sensitive Information Disclosure",
    c.source = "OWASP Top 10 for LLM Applications v2025";

MATCH (c:Control {framework: "OWASP_LLM_Top10", id: "LLM06"})
SET c.title = "Excessive Agency",
    c.source = "OWASP Top 10 for LLM Applications v2025";

MATCH (c:Control {framework: "OWASP_LLM_Top10", id: "LLM08"})
SET c.title = "Vector and Embedding Weaknesses",
    c.source = "OWASP Top 10 for LLM Applications v2025";

MATCH (c:Control {framework: "OWASP_LLM_Top10", id: "LLM09"})
SET c.title = "Misinformation",
    c.source = "OWASP Top 10 for LLM Applications v2025";

// ============================================================
// BLOCK N — RISK NODES (pattern-based compliance risks)
// Detected by graph_client from service category combinations.
// ============================================================

MERGE (r:Risk {id: "PII_IN_LLM_CONTEXT"})
ON CREATE SET
  r.title            = "PII-Risiko: Datenbankdaten im LLM-Kontext",
  r.severity         = "high",
  r.detection_signal = "ai_llm + baas/database/storage/vector_db",
  r.mitigation       = "UUID-Only Pattern (ADR-001) oder Presidio PII-Pre-Filter",
  r.source           = "DSGVO Art. 25 + Art. 32 + EU AI Act Art. 10"
ON MATCH SET r.source = "DSGVO Art. 25 + Art. 32 + EU AI Act Art. 10";

MERGE (r:Risk {id: "RAG_OVER_PII"})
ON CREATE SET
  r.title            = "RAG ueber personenbezogene Daten (pgvector/Embeddings)",
  r.severity         = "critical",
  r.detection_signal = "pgvector OR vector_db + ai_llm",
  r.mitigation       = "Nur anonymisierte Chunks embedden. PII-Scrubbing vor Embedding. UUID-Only im Vector-Store.",
  r.source           = "DSGVO Art. 25 + Art. 32 + Art. 5 + EU AI Act Art. 10"
ON MATCH SET r.source = "DSGVO Art. 25 + Art. 32 + Art. 5 + EU AI Act Art. 10";

MERGE (r:Risk {id: "PII_IN_LOGS"})
ON CREATE SET
  r.title            = "PII in Error-Logs und Monitoring",
  r.severity         = "high",
  r.detection_signal = "monitoring/logging service + llm_api",
  r.mitigation       = "PII-freies Logging: nur UUID-Prefix in Fehlermeldungen",
  r.source           = "DSGVO Art. 32"
ON MATCH SET r.source = "DSGVO Art. 32";

// Risk → Law VIOLATES relationships
MATCH (r:Risk {id: "PII_IN_LLM_CONTEXT"}), (l:Law {name: "DSGVO", article: "25"}) MERGE (r)-[:VIOLATES]->(l);
MATCH (r:Risk {id: "PII_IN_LLM_CONTEXT"}), (l:Law {name: "DSGVO", article: "32"}) MERGE (r)-[:VIOLATES]->(l);
MATCH (r:Risk {id: "PII_IN_LLM_CONTEXT"}), (l:Law {name: "EU AI Act", article: "10"}) MERGE (r)-[:VIOLATES]->(l);
MATCH (r:Risk {id: "PII_IN_LLM_CONTEXT"}), (d:DocumentType {type: "TOM"}) MERGE (r)-[:REQUIRES_MEASURE_IN]->(d);

MATCH (r:Risk {id: "RAG_OVER_PII"}), (l:Law {name: "DSGVO", article: "25"}) MERGE (r)-[:VIOLATES]->(l);
MATCH (r:Risk {id: "RAG_OVER_PII"}), (l:Law {name: "DSGVO", article: "32"}) MERGE (r)-[:VIOLATES]->(l);
MATCH (r:Risk {id: "RAG_OVER_PII"}), (l:Law {name: "EU AI Act", article: "10"}) MERGE (r)-[:VIOLATES]->(l);
MATCH (r:Risk {id: "RAG_OVER_PII"}), (d:DocumentType {type: "TOM"}) MERGE (r)-[:REQUIRES_MEASURE_IN]->(d);
MATCH (r:Risk {id: "RAG_OVER_PII"}), (s:Service {name: "Supabase"}) MERGE (s)-[:CAN_TRIGGER]->(r);

MATCH (r:Risk {id: "PII_IN_LOGS"}), (l:Law {name: "DSGVO", article: "32"}) MERGE (r)-[:VIOLATES]->(l);
MATCH (r:Risk {id: "PII_IN_LOGS"}), (d:DocumentType {type: "TOM"}) MERGE (r)-[:REQUIRES_MEASURE_IN]->(d);

// ============================================================
// BLOCK O — VECTOR DB + NOSQL SERVICE NODES
// ============================================================

MERGE (s:Service {name: "Pinecone"})
ON CREATE SET
  s.category        = "vector_db",
  s.country         = "USA",
  s.gdpr_adequate   = false,
  s.dpa_required    = true,
  s.dpa_url         = "https://www.pinecone.io/legal/dpa/",
  s.rag_risk        = "critical",
  s.canonical_names = ["pinecone", "pinecone-client"]
ON MATCH SET
  s.category = "vector_db",
  s.rag_risk = "critical";

MERGE (s:Service {name: "Weaviate"})
ON CREATE SET
  s.category        = "vector_db",
  s.country         = "Netherlands",
  s.gdpr_adequate   = true,
  s.dpa_required    = true,
  s.dpa_url         = "https://weaviate.io/security",
  s.rag_risk        = "critical",
  s.canonical_names = ["weaviate", "weaviate-client"]
ON MATCH SET
  s.category = "vector_db",
  s.rag_risk = "critical";

MERGE (s:Service {name: "Qdrant"})
ON CREATE SET
  s.category        = "vector_db",
  s.country         = "Germany",
  s.gdpr_adequate   = true,
  s.dpa_required    = true,
  s.dpa_url         = "https://qdrant.tech/legal/privacy-policy/",
  s.rag_risk        = "critical",
  s.canonical_names = ["qdrant", "qdrant-client"]
ON MATCH SET
  s.category = "vector_db",
  s.rag_risk = "critical";

MERGE (s:Service {name: "ChromaDB"})
ON CREATE SET
  s.category        = "vector_db",
  s.country         = "USA",
  s.gdpr_adequate   = false,
  s.dpa_required    = true,
  s.rag_risk        = "critical",
  s.canonical_names = ["chromadb", "chroma"]
ON MATCH SET
  s.category = "vector_db",
  s.rag_risk = "critical";

MERGE (s:Service {name: "pgvector"})
ON CREATE SET
  s.category          = "vector_db",
  s.country           = "open_source",
  s.gdpr_adequate     = true,
  s.dpa_required      = false,
  s.rag_risk          = "critical",
  s.detection_signals = ["CREATE EXTENSION vector", "from pgvector",
                         "VectorField(", "match_documents", "ankane/pgvector"],
  s.canonical_names   = ["pgvector", "pgvector-python"]
ON MATCH SET
  s.category = "vector_db",
  s.rag_risk = "critical";

MERGE (s:Service {name: "MongoDB Atlas"})
ON CREATE SET
  s.category        = "nosql_db",
  s.country         = "USA",
  s.gdpr_adequate   = false,
  s.dpa_required    = true,
  s.dpa_url         = "https://www.mongodb.com/legal/dpa",
  s.vector_capable  = true,
  s.canonical_names = ["pymongo", "motor", "mongoengine"]
ON MATCH SET
  s.category = "nosql_db";

MERGE (s:Service {name: "Google Firestore"})
ON CREATE SET
  s.category        = "nosql_db",
  s.country         = "USA",
  s.gdpr_adequate   = false,
  s.dpa_required    = true,
  s.dpa_url         = "https://cloud.google.com/terms/dpa",
  s.canonical_names = ["firebase-admin", "google-cloud-firestore"]
ON MATCH SET
  s.category = "nosql_db";

MERGE (s:Service {name: "MariaDB"})
ON CREATE SET
  s.category        = "database",
  s.country         = "Finland",
  s.gdpr_adequate   = true,
  s.dpa_required    = true,
  s.dpa_url         = "https://mariadb.com/about-us/legal/dpa/",
  s.canonical_names = ["mariadb", "PyMySQL", "mysql-connector-python"]
ON MATCH SET
  s.category = "database";

MERGE (s:Service {name: "AWS RDS"})
ON CREATE SET
  s.category        = "database",
  s.country         = "USA",
  s.gdpr_adequate   = false,
  s.dpa_required    = true,
  s.dpa_url         = "https://aws.amazon.com/agreement/",
  s.canonical_names = ["boto3", "rds", "psycopg2"]
ON MATCH SET
  s.category = "database";

// All vector_db services → CAN_TRIGGER → RAG_OVER_PII
MATCH (s:Service) WHERE s.category = "vector_db"
MATCH (r:Risk {id: "RAG_OVER_PII"})
MERGE (s)-[:CAN_TRIGGER]->(r);

// ============================================================
// BLOCK P — NO_AI_AUDIT_TRAIL Risk node + Langfuse Service
// ============================================================

MERGE (r:Risk {id: "NO_AI_AUDIT_TRAIL"})
ON CREATE SET
  r.title            = "Kein AI Audit Trail (EU AI Act Art. 12)",
  r.severity         = "high",
  r.detection_signal = "ai_llm without observability/logging tool",
  r.mitigation       = "Langfuse oder OpenTelemetry integrieren. Input/Output-Hash pro LLM-Call speichern.",
  r.source           = "EU AI Act Art. 12"
ON MATCH SET r.source = "EU AI Act Art. 12";

MATCH (r:Risk {id: "NO_AI_AUDIT_TRAIL"}), (l:Law {name: "EU AI Act", article: "12"})
MERGE (r)-[:VIOLATES]->(l);

MATCH (r:Risk {id: "NO_AI_AUDIT_TRAIL"}), (d:DocumentType {type: "AI_Act_Manifest"})
MERGE (r)-[:REQUIRES_MEASURE_IN]->(d);

MERGE (s:Service {name: "Langfuse"})
ON CREATE SET
  s.category                = "observability",
  s.country                 = "Germany",
  s.gdpr_adequate           = true,
  s.dpa_required            = true,
  s.dpa_url                 = "https://langfuse.com/docs/data-security-privacy",
  s.data_categories         = "LLM-Prompts, Responses, Traces, Scores",
  s.data_subjects           = "Entwickler, Endnutzer (indirekt via Prompts)",
  s.processing_purpose      = "LLM Observability, Audit Trail, A/B Testing",
  s.deletion_period         = "Konfigurierbar, self-hosted moeglich",
  s.satisfies_eu_ai_act_art12 = true,
  s.canonical_names         = ["langfuse"]
ON MATCH SET
  s.satisfies_eu_ai_act_art12 = true,
  s.category = "observability";

// Langfuse satisfies EU AI Act Art. 12
MATCH (s:Service {name: "Langfuse"}), (l:Law {name: "EU AI Act", article: "12"})
MERGE (s)-[:SATISFIES]->(l);
