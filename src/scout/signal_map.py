"""
Signal Map — canonical name resolution for the Infrastructure Scout.
Maps detected package/service names to canonical Neo4j Service node names.
"""

# Maps detected names (lowercase, no separators) → canonical Neo4j Service node name.
# None means the signal is a known internal/infra component, not a billable SaaS.
SIGNAL_MAP: dict[str, str | None] = {
    "openai":                "OpenAI",
    "anthropic":             "Anthropic",
    "googleGenerativeai":    "Google Gemini",
    "mistralai":             "Mistral AI",
    "huggingfacehub":        "Hugging Face",
    "replicate":             "Replicate",
    "langchain":             None,        # framework, not a service
    "types":                 None,        # npm @types/* scope — not a service
    "express":               None,        # web framework, not a sub-processor
    "nodejs":                None,        # runtime, not a sub-processor
    "node":                  None,        # runtime alias
    "next":                  None,        # Next.js — framework you self-host, not a sub-processor
    "nextjs":                None,        # Next.js display-name variant (Gemma4 fallback)
    "react":                 None,        # UI library, not a sub-processor
    "reactdom":              None,        # react-dom — same library family
    "stripe":                "Stripe",
    "paypalrestsdk":         "PayPal",
    "braintree":             "Braintree",
    "mollie":                "Mollie",
    # ── ADR-115 A1: PSP-role launch-slice detection ──────────────────────────
    # signal_map carries detection ONLY; the EDPB controller/processor role lives
    # on the seeded Service node's ACTS_AS edge (scripts/seed_both.py:seed_psp_roles),
    # resolved via Q_META — identical mechanism to paypalrestsdk→PayPal (verified
    # live, run 22f7054b). Each display name is byte-exact the seeded node name,
    # so the seeded role greift on match.
    "klarna":                "Klarna",       # composer scope `klarna/kco_rest`; npm bare `klarna`
    "digistore24":           "Digistore24",  # composer name `*/digistore24`; npm `@pipedream/digistore24`
    # Billwerk: bare token ONLY. The dominant composer integrations
    # (billwerk-plus-subscription, billwerk-api, laravel-billwerk, omnipay-billwerk)
    # normalize to `billwerk<suffix>` and do NOT match — left to the Gemma4 fallback.
    # No suffix variants added: per-author naming would be false-positive guessing
    # (coverage limit accepted, ADR-115 A1 read-of-truth 2026-06-03).
    "billwerk":              "Billwerk",
    "sendgrid":              "SendGrid",
    "mailchimp3":            "Mailchimp",
    "twilio":                "Twilio",
    "postmarker":            "Postmark",
    "resend":                "Resend",
    "boto3":                 "AWS",
    "googlecloudstorage":    "Google Cloud",
    "azurestorageblob":      "Azure",
    "digitalocean":          "DigitalOcean",
    "auth0":                 "Auth0 / Okta",
    "clerk":                 "Clerk",
    # ADR-072: google-auth*, expo, expo-notifications intentionally unmapped —
    # Gemma4 handles them via category classification (auth / baas).
    "reactnative":           None,              # framework, not a sub-processor (deterministic)
    "expoconstants":         None,              # expo SDK-internal module (deterministic)
    "mixpanel":              "Mixpanel",
    "amplitude":             "Amplitude",
    "posthog":               "PostHog",
    "sdksentry":             "Sentry",
    "sentrysdk":             "Sentry",
    "datadog":               "Datadog",
    "supabase":              "Supabase",
    "firebaseadmin":         "Firebase",
    # ADR-072: mongodb (JS), pymongo, motor all intentionally unmapped
    # (absent from dict, fall through to Gemma4 fallback). Library presence
    # is ambiguous between self-hosted MongoDB and MongoDB Atlas — naming a
    # Sub-Processor would be a false claim. Gemma4 classifies them as
    # category="nosql_db"; Category-First-Lookup provides Controls.
    # Do NOT add `"mongodb": None` here — that would put it in the
    # "known non-service, skip Gemma4" bucket (see line ~152) alongside
    # express/nodejs/langchain. MongoDB IS a real backing service, just
    # ambiguous at the library layer.
    "redis":                 "Redis",
    "elasticsearch":         "Elasticsearch",
    "elastic":               "Elasticsearch",
    "segment":               "Segment",
    "pgvector":              "pgvector",
    "pinecone":              "Pinecone",
    "pineconeclient":        "Pinecone",
    "weaviate":              "Weaviate",
    "weaviateclient":        "Weaviate",
    "qdrant":                "Qdrant",
    "qdrantclient":          "Qdrant",
    "chromadb":              "Chroma",
    "chroma":                "Chroma",
    "llamaindex":            None,        # framework (similar to langchain)
    "vercel":                "Vercel",
    "netlify":               "Netlify",

    # PHP / Laravel (composer vendor/package → normalized)
    "stripestripe-php":          "Stripe",
    "sentrysentrylaravel":       "Sentry",
    "getsentry":                 "Sentry",       # go: github.com/getsentry/sentry-go
    "sentryruby":                "Sentry",       # ruby gem

    # Java / .NET
    "stripejava":                "Stripe",       # maven: stripe-java
    "stripenet":                 "Stripe",       # nuget: Stripe.net
    "sentryspringbootstarter":   "Sentry",
    "awssdkcore":                "AWS",          # nuget
    "azurestorageblobs":         "Azure",        # nuget

    # Go
    "stripego":                  "Stripe",       # go: github.com/stripe/stripe-go
    "awssdkgo":                  "AWS",

    # Ruby
    "awssdk":                    "AWS",

    # ADR-071/072: frameworks / local libs — deterministic None, not an LLM job
    "fastapi":               None,              # Python web framework
    "uvicorn":               None,              # ASGI server runtime
    "flask":                 None,
    "django":                None,
    "starlette":             None,              # FastAPI underlying
    "reportlab":             None,              # local PDF generation
    "pyjwt":                 None,              # local JWT library
    "jwt":                   None,              # npm: jsonwebtoken alias
    "aiohttp":               None,              # HTTP client
    "httpx":                 None,              # HTTP client
    "requests":              None,              # HTTP client
    "pydantic":              None,              # validation lib
    "sqlalchemy":            None,              # ORM, not a hosted DB
    "alembic":               None,              # migration tool

    # Additional aliases for manifest scanning
    "postmark":                  "Postmark",     # npm: postmark
    "sentry":                    "Sentry",       # direct package name
    "sentrynode":                "Sentry",       # npm: @sentry/node
    "supabasejs":                "Supabase",     # npm: @supabase/supabase-js
}


def canonical(name: str) -> str | None:
    """
    Return the Neo4j-canonical service name for a detected signal.
    Returns None if name is not in the signal map (unknown or infra-only).

    Normalization: lowercase, strip hyphens and underscores.
    Examples:
        "langchain-core" → "langchain" → None (framework)
        "firebase-admin" → "firebaseadmin" → "Firebase"
        "sentry-sdk"     → "sentrysdk"     → "Sentry"
    """
    key = name.lower().replace("-", "").replace("_", "")
    return SIGNAL_MAP.get(key)


# ── ADR-062: Gemma4 Fallback für unbekannte Pakete ────────────────────────────

_FALLBACK_CACHE: dict[str, dict | None] = {}


def canonical_with_fallback(
    name: str,
    use_llm: bool = True,
    min_confidence: float = 0.60,
) -> tuple[str | None, str | None, dict | None]:
    """
    Extended canonical lookup with Gemma4 fallback for unknown packages.
    Returns (canonical_name, category, llm_result).
    ADR-001: package_name is a dependency name (public knowledge), not PII.
    Non-fatal: any failure returns (None, None, None).
    """
    from src.scanner.llm_classifier import classify_service, is_available

    hit = canonical(name)
    if hit is not None:
        return hit, None, None

    # ADR-062: key explicitly in SIGNAL_MAP with None = known non-service, skip Gemma4
    cache_key = name.lower().replace("-", "").replace("_", "")
    if cache_key in SIGNAL_MAP:
        return None, None, None

    if cache_key in _FALLBACK_CACHE:
        cached = _FALLBACK_CACHE[cache_key]
        if cached is None:
            return None, None, None
        return cached.get("canonical_name"), cached.get("category"), cached

    if not use_llm or not is_available():
        _FALLBACK_CACHE[cache_key] = None
        return None, None, None

    result = classify_service(name)

    # ADR-062: if lowercase name fails, retry with Title Case
    # Gemma4 recognizes "Segment" as a product but not "segment"
    if result is None and name != name.capitalize():
        result = classify_service(name.capitalize())

    _FALLBACK_CACHE[cache_key] = result

    if result is None:
        return None, None, None

    confidence = result.get("confidence", 0.0)
    category = result.get("category", "unknown")
    canonical_name = result.get("canonical_name")

    # ADR-072: category is valuable even without a canonical_name — pass it through
    if confidence < min_confidence or category == "unknown":
        return None, None, result

    import logging
    logging.getLogger(__name__).info(
        "signal_map fallback: %r → canonical=%r category=%r conf=%.2f",
        name, canonical_name, category, confidence,
    )
    # canonical_name may be None here — that's intentional; category alone
    # drives the ServiceCategory-based graph lookup (ADR-061).
    return canonical_name, category, result


def clear_fallback_cache() -> None:
    """Clear session cache — useful for testing."""
    _FALLBACK_CACHE.clear()

