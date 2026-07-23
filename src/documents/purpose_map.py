"""Processing-purpose resolution: graph value vs. category-derived default.

A service's processing_purpose is authoritative when it comes from the graph
(project-evidenced). When the graph has no value, we fall back to a purpose
derived from the service CATEGORY — but that derived value is a tool suggestion,
not service-specific evidence, and MUST be marked as such in generated documents
(see src/templates/_marker.md.j2 'inferred' marker + docs/principles/doc-quality.md).

resolve_processing_purpose returns an is_inferred flag so VVT, SCC, and any future
consumer can drive that marking from a single source of truth.
"""
from __future__ import annotations

# Category → generic processing purpose (DE). Canonical home; VVTBuilder imports
# from here so VVT and SCC never drift apart on the derived value.
_DEFAULT_PURPOSE: dict[str, str] = {
    "database":        "Datenspeicherung und -verwaltung",
    "nosql_db":        "NoSQL-Datenspeicherung und -verwaltung",
    "cache_db":        "In-Memory-Caching und Session-Management",
    "baas":            "Backend-as-a-Service: Datenspeicherung, Authentifizierung, APIs",
    "ai_llm":          "KI-gestützte Textgenerierung und -verarbeitung",
    "ai_platform":     "KI-Plattformdienste und Modellinferenz",
    "payment":         "Zahlungsabwicklung und Transaktionsverarbeitung",
    "email":           "Transaktionaler E-Mail-Versand",
    "email_marketing": "E-Mail-Marketing und Newsletter-Versand",
    "auth":            "Authentifizierung, Autorisierung und Identity Management",
    "analytics":       "Nutzungsanalyse, Tracking und Monitoring",
    "hosting":         "Server-Hosting und Infrastrukturbereitstellung",
    "cloud":           "Cloud-Infrastruktur und verwaltete Dienste",
    "storage":         "Datei- und Objektspeicherung",
    "vector_db":       "Vektordatenbank für Embedding-Speicherung (RAG)",
    "monitoring":      "Fehler-Monitoring, Log-Aggregation und Alerting",
    "cdn_security":    "Content Delivery und Web-Application-Security",
    "vcs":             "Versionskontrolle und Quellcode-Management",
    "ci_cd":           "Continuous Integration und Deployment-Automatisierung",
    "crm":             "Customer Relationship Management und Kundendatenverwaltung",
    "crm_support":     "Support-Ticketing und Kundenservice",
    "sms":             "SMS-Versand und Mobile Messaging",
    "observability":   "LLM-Observability und KI-Audit-Trail (EU AI Act Art. 12)",
    "media_storage":   "Medien- und Asset-Speicherung",
    "search_db":       "Volltextsuche und Such-Index",
    "security":        "Security-Monitoring, SIEM und Threat Intelligence",
}

_DEFAULT_PURPOSE_EN: dict[str, str] = {
    "database":        "Data storage and management",
    "nosql_db":        "NoSQL data storage and management",
    "cache_db":        "In-memory caching and session management",
    "baas":            "Backend-as-a-Service: data storage, authentication, APIs",
    "ai_llm":          "AI-assisted text generation and processing",
    "ai_platform":     "AI platform services and model inference",
    "payment":         "Payment processing and transaction handling",
    "email":           "Transactional e-mail delivery",
    "email_marketing": "E-mail marketing and newsletter delivery",
    "auth":            "Authentication, authorisation and identity management",
    "analytics":       "Usage analytics, tracking and monitoring",
    "hosting":         "Server hosting and infrastructure provisioning",
    "cloud":           "Cloud infrastructure and managed services",
    "storage":         "File and object storage",
    "vector_db":       "Vector database for embedding storage (RAG)",
    "monitoring":      "Error monitoring, log aggregation and alerting",
    "cdn_security":    "Content delivery and web application security",
    "vcs":             "Version control and source code management",
    "ci_cd":           "Continuous integration and deployment automation",
    "crm":             "Customer relationship management and customer data",
    "crm_support":     "Support ticketing and customer service",
    "sms":             "SMS delivery and mobile messaging",
    "observability":   "LLM observability and AI audit trail (EU AI Act Art. 12)",
    "media_storage":   "Media and asset storage",
    "search_db":       "Full-text search and search index",
    "security":        "Security monitoring, SIEM and threat intelligence",
}

_CATCH_ALL_PURPOSE = "Leistungserbringung gemäß Hauptvertrag"
_CATCH_ALL_PURPOSE_EN = "Service provision under the main contract"

# B-2/L8 (EN package): N1 marker — single source for doc consumers. An EN
# document NEVER silently shows the German value; a missing _en twin renders
# this honest placeholder instead.
TRANSLATION_PENDING_EN = "☐ translation pending (German version exists)"


def pick_lang_text(de_value, en_value, lang: str = "de"):
    """Language-pure field pick for graph free-text descriptors.

    de  -> the German value (unchanged behaviour).
    en  -> the `_en` twin; if only the German value exists, the N1
           pending marker; None stays None (caller keeps its gap logic).
    """
    if lang == "en":
        if en_value:
            return en_value
        return TRANSLATION_PENDING_EN if de_value else None
    return de_value


def default_purpose(category: str | None, lang: str = "de") -> str:
    """Category → generic purpose. Catch-all for unknown/empty category."""
    if lang == "en":
        return _DEFAULT_PURPOSE_EN.get(category or "", _CATCH_ALL_PURPOSE_EN)
    return _DEFAULT_PURPOSE.get(category or "", _CATCH_ALL_PURPOSE)


def resolve_processing_purpose(
    graph_value: str | None,
    category: str | None,
    lang: str = "de",
    graph_value_en: str | None = None,
) -> tuple[str, bool]:
    """Resolve a service's processing purpose and whether it is inferred.

    Returns (purpose, is_inferred):
      - graph value present  -> (graph_value, False)  # project-evidenced, not marked
      - otherwise            -> (category_default, True)  # tool-derived, MUST be marked

    B-2/L8 (EN package, language-pure): at lang='en' the DE graph value must
    NOT leak into the document — the resolver uses the seeded `_en` twin, and
    falls back to the EN category default WITH the inferred flag when the twin
    is missing (honest: derived, not evidenced-in-English).

    The derived branch always returns a string (catch-all when the category is
    unknown), preserving the long-standing VVT behaviour of never rendering an
    empty purpose; the is_inferred flag carries the honesty.
    """
    if lang == "en":
        if graph_value_en and graph_value_en.strip():
            return graph_value_en.strip(), False
        return default_purpose(category, "en"), True
    if graph_value and graph_value.strip():
        return graph_value.strip(), False
    return default_purpose(category, lang), True
