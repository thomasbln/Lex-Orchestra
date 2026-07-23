// ============================================================
// LEX-ORCHESTRA — Layer 00: Global Services
// Applies to: all deployments worldwide
// jurisdictions: ["global"]
// Idempotent: MERGE-only, safe to re-run
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
// BLOCK C2 — removed (ADR-130 build-time fix, 2026-07-14).
// Service.legal_basis was retired in ADR-100 PR 7 — the authoritative
// source is SUBJECT_TO_CONTROL[legal_basis], written by
// 10_jurisdiction/eu/12_legal_basis_backfill.cypher (Phase 3).
// Re-seeding the property here would be drift by design.
// ============================================================


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

// ============================================================
// JURISDICTION NORMALIZATION — derived from country property
// ============================================================

MATCH (s:Service)
WHERE s.country IN ["Germany", "France", "Netherlands", "Finland", "Ireland"]
SET s.jurisdictions = ["EU", "global"];

MATCH (s:Service {country: "open_source"})
SET s.jurisdictions = ["global"];

MATCH (s:Service)
WHERE s.jurisdictions IS NULL
SET s.jurisdictions = ["global"];

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
// NEW HOSTING SERVICES — Relationships
// ============================================================

// Azure, DigitalOcean, Render, Railway, Fly.io → USA
MATCH (s:Service), (c:Country {name: "USA"})
WHERE s.name IN ["Azure", "DigitalOcean", "Render", "Railway", "Fly.io"]
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

// ── ADR-075: Service region + SCC mechanism ────────────────────────────────
// Parallel to scripts/seed_both.py:seed_adr075 for manual imports.
MERGE (s:Service {name: "Stripe"})       SET s.default_region = "us-east-1",  s.requires_scc = true,  s.scc_mechanism = "EU_SCCs_2021";
MERGE (s:Service {name: "Postmark"})     SET s.default_region = "us-east-1",  s.requires_scc = true,  s.scc_mechanism = "EU_SCCs_2021";
MERGE (s:Service {name: "Twilio"})       SET s.default_region = "us-west-2",  s.requires_scc = true,  s.scc_mechanism = "EU_SCCs_2021";
MERGE (s:Service {name: "SendGrid"})     SET s.default_region = "us-east-1",  s.requires_scc = true,  s.scc_mechanism = "EU_SCCs_2021";
MERGE (s:Service {name: "AWS"})          SET s.default_region = "unknown",    s.requires_scc = false;
MERGE (s:Service {name: "Google Cloud"}) SET s.default_region = "unknown",    s.requires_scc = false;
MERGE (s:Service {name: "Azure"})        SET s.default_region = "unknown",    s.requires_scc = false;
MERGE (s:Service {name: "Hetzner"})      SET s.default_region = "eu-central", s.requires_scc = false;
MERGE (s:Service {name: "Mistral AI"})   SET s.default_region = "eu-west-3",  s.requires_scc = false;
MERGE (s:Service {name: "Supabase"})     SET s.default_region = "eu-central", s.requires_scc = false;

// ── ADR-076: HostingProvider curated list ──────────────────────────────────
// Parallel to scripts/seed_both.py:seed_adr076 for manual imports.
MERGE (h:HostingProvider {name: "AWS"})            SET h.soc2 = true,  h.iso27001 = true,  h.default_regions = ["us-east-1", "eu-central-1", "eu-west-1"], h.requires_scc_outside_eu = true;
MERGE (h:HostingProvider {name: "GCP"})            SET h.soc2 = true,  h.iso27001 = true,  h.default_regions = ["us-central1", "europe-west3"],             h.requires_scc_outside_eu = true;
MERGE (h:HostingProvider {name: "Azure"})          SET h.soc2 = true,  h.iso27001 = true,  h.default_regions = ["eastus", "westeurope"],                    h.requires_scc_outside_eu = true;
MERGE (h:HostingProvider {name: "Hetzner"})        SET h.soc2 = false, h.iso27001 = true,  h.default_regions = ["eu-central", "eu-west"],                   h.requires_scc_outside_eu = false;
MERGE (h:HostingProvider {name: "IONOS"})          SET h.soc2 = false, h.iso27001 = true,  h.default_regions = ["eu-central"],                              h.requires_scc_outside_eu = false;
MERGE (h:HostingProvider {name: "OVH"})            SET h.soc2 = true,  h.iso27001 = true,  h.default_regions = ["eu-west"],                                 h.requires_scc_outside_eu = false;
MERGE (h:HostingProvider {name: "Strato"})         SET h.soc2 = false, h.iso27001 = true,  h.default_regions = ["eu-central"],                              h.requires_scc_outside_eu = false;
MERGE (h:HostingProvider {name: "Supabase Cloud"}) SET h.soc2 = true,  h.iso27001 = false, h.default_regions = ["eu-west-1", "us-east-1"],                  h.requires_scc_outside_eu = true;
MERGE (h:HostingProvider {name: "Vercel"})         SET h.soc2 = true,  h.iso27001 = false, h.default_regions = ["global"],                                  h.requires_scc_outside_eu = true;
MERGE (h:HostingProvider {name: "Railway"})        SET h.soc2 = false, h.iso27001 = false, h.default_regions = ["us-west1"],                                h.requires_scc_outside_eu = true;
MERGE (h:HostingProvider {name: "Fly.io"})         SET h.soc2 = true,  h.iso27001 = false, h.default_regions = ["global"],                                  h.requires_scc_outside_eu = true;
MERGE (h:HostingProvider {name: "Cloudflare"})     SET h.soc2 = true,  h.iso27001 = true,  h.default_regions = ["global"],                                  h.requires_scc_outside_eu = true;
