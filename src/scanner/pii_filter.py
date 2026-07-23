"""
Layer 2 — Presidio PII Filter (ADR-028)
========================================
Anonymises text before passing to Layer 3 (Phi-4-mini).
Runs locally on Pi — no network call, no cloud.

ADR-028 invariant: system-prompt content MUST NEVER be passed to this function.
ADR-001: anonymised output only leaves Pi as signal label — never raw text.
"""
from __future__ import annotations

import logging

logger = logging.getLogger(__name__)

# Lazy-loaded — only initialised when first called
_analyzer = None
_anonymizer = None

ENTITIES = [
    "PERSON",
    "EMAIL_ADDRESS",
    "PHONE_NUMBER",
    "LOCATION",
    "NRP",
    "IP_ADDRESS",
    "IBAN_CODE",
    "CREDIT_CARD",
    "URL",
    "ORGANIZATION",
]

# ADR-069: spaCy en_core_web_sm tags tech names like "Anthropic" / "Claude" /
# "OpenAI" as PERSON (score 0.85), which strips semantic context Gemma4 needs
# for Layer-3 classification. Terms here are never flagged as PII, regardless
# of detected entity type. Case-insensitive (Presidio default).
TECH_ALLOW_LIST = [
    # AI / LLM providers
    "Anthropic", "OpenAI", "Claude", "GPT", "ChatGPT", "Gemma", "Gemini",
    "Mistral", "Cohere", "Hugging Face", "HuggingFace", "Llama", "Meta AI",
    "DeepSeek", "Groq", "Together AI", "Replicate", "Ollama", "LM Studio",
    # Cloud / Infrastructure
    "AWS", "Amazon Web Services", "Azure", "GCP", "Google Cloud",
    "DigitalOcean", "Vercel", "Netlify", "Cloudflare", "Fly.io", "Render",
    # Databases / Caches
    "MongoDB", "Redis", "PostgreSQL", "Postgres", "MySQL", "MariaDB",
    "SQLite", "Elasticsearch", "OpenSearch", "Neo4j", "Supabase", "Firebase",
    "PlanetScale", "Upstash",
    # Payments / Auth
    "Stripe", "Braintree", "PayPal", "Paddle", "Lemon Squeezy",
    "Auth0", "Clerk", "Okta", "Google OAuth", "GitHub OAuth",
    # Frameworks / Runtimes
    "FastAPI", "Flask", "Django", "Express", "NestJS", "Next.js", "Nuxt",
    "Remix", "SvelteKit", "React", "Vue", "Svelte", "Angular",
    "Expo", "React Native", "Flutter", "Vite", "Turbopack",
    # Observability / AI tooling
    "LangChain", "LangGraph", "LlamaIndex", "Langfuse", "Presidio",
    "Sentry", "Datadog", "New Relic", "Grafana", "Prometheus",
    # Analytics / Comms
    "Segment", "Mixpanel", "Amplitude", "PostHog",
    "Slack", "Discord", "Telegram", "Twilio", "SendGrid", "Mailgun",
    # Internal
    "Lex-Orchestra", "NucBox",
]


def _get_engines():
    """Lazy-load Presidio engines (heavy import — only on first call)."""
    global _analyzer, _anonymizer
    if _analyzer is None:
        try:
            from presidio_analyzer import AnalyzerEngine
            from presidio_analyzer.nlp_engine import NlpEngineProvider
            from presidio_anonymizer import AnonymizerEngine

            # Use small models pre-installed in Docker (Dockerfile line 33-34)
            # Default would be en_core_web_lg (400 MB) which is NOT installed.
            provider = NlpEngineProvider(nlp_configuration={
                "nlp_engine_name": "spacy",
                "models": [
                    {"lang_code": "en", "model_name": "en_core_web_sm"},
                    {"lang_code": "de", "model_name": "de_core_news_sm"},
                ],
            })
            nlp_engine = provider.create_engine()
            _analyzer = AnalyzerEngine(nlp_engine=nlp_engine)
            _anonymizer = AnonymizerEngine()
            logger.info("Presidio engines initialised (en_core_web_sm + de_core_news_sm)")
        except ImportError as e:
            logger.error("Presidio not installed: %s", e)
            raise
    return _analyzer, _anonymizer


def anonymize(text: str, language: str = "en", run_id: str = "unknown") -> str:
    """
    Strip PII from text using Presidio.
    Returns anonymised text with placeholders like <PERSON>, <EMAIL_ADDRESS>.

    Logs each detected entity for audit trail — entity type and score only,
    never the raw value (ADR-001).

    ADR-028: call on code snippets only — never on system-prompt content.
    Falls back to original text if Presidio unavailable (non-fatal).
    """
    if not text or not text.strip():
        return text

    try:
        analyzer, anonymizer = _get_engines()
        results = analyzer.analyze(
            text=text,
            language=language,
            entities=ENTITIES,
            allow_list=TECH_ALLOW_LIST,
        )

        if results:
            # Log entity types + scores only — never the raw matched text (ADR-001)
            for r in results:
                logger.debug(
                    "Presidio: entity=%s score=%.2f start=%d end=%d",
                    r.entity_type, r.score, r.start, r.end,
                )
            summary = ", ".join(f"{r.entity_type}({r.score:.2f})" for r in results)
            logger.info("Presidio: anonymised %d entities — %s", len(results), summary)

            # ADR-030: structured JSON log
            try:
                from src.utils.scan_logger import log_layer2_entity, log_layer2_summary
                for r in results:
                    log_layer2_entity(run_id, r.entity_type, r.score)
                log_layer2_summary(run_id, len(results), summary)
            except Exception:
                pass
        else:
            logger.debug("Presidio: no PII detected in snippet")

        return anonymizer.anonymize(text=text, analyzer_results=results).text

    except Exception as e:
        logger.warning("Presidio anonymization failed (non-fatal): %s", e)
        return text  # pass-through on error — pipeline continues


def anonymize_signals(signals: list[dict], run_id: str = "unknown") -> list[dict]:
    """
    Apply PII filter to evidence[] field of scan signals.
    evidence[] contains relative file paths — rarely has PII, but filter for safety.
    Returns new list — never mutates input.
    Logs summary per signal type.
    """
    cleaned = []
    for sig in signals:
        new_sig = dict(sig)
        evidence = sig.get("evidence", [])
        if evidence:
            cleaned_evidence = [anonymize(e, run_id=run_id) for e in evidence]
            new_sig["evidence"] = cleaned_evidence
            # Log if anything changed
            changed = sum(1 for a, b in zip(evidence, cleaned_evidence) if a != b)
            if changed:
                logger.info(
                    "Presidio: signal_type=%s — %d/%d evidence strings anonymised",
                    sig.get("signal_type", "?"), changed, len(evidence),
                )
        cleaned.append(new_sig)
    return cleaned


def anonymize_file_contents(
    content_snippets: dict[str, str],
    run_id: str = "unknown",
) -> None:
    """
    Run Presidio on ALL file content snippets for audit logging (ADR-049 Option C).

    The anonymised output is DISCARDED immediately — never stored or forwarded.
    Only entity types are logged (ADR-001).
    """
    if not content_snippets:
        return

    import re as _re

    DE_MARKERS = {"impressum", "anbieter", "datenschutz", "geschäftsführer",
                  "handelsregister", "umsatzsteuer", "vertretungsberechtigter"}

    all_entity_types: list[str] = []
    files_with_pii = 0

    for rel_path, snippet in content_snippets.items():
        if not snippet or not snippet.strip():
            continue

        lang = "de" if any(m in snippet.lower() for m in DE_MARKERS) else "en"

        try:
            anonymized = anonymize(snippet, language=lang, run_id=run_id)

            found_types = _re.findall(r"<([A-Z_]+)>", anonymized)
            if found_types:
                files_with_pii += 1
                all_entity_types.extend(found_types)
                logger.info(
                    "Presidio content scan: %s — found %s — anonymised, discarded",
                    rel_path, found_types,
                )
            # anonymized text is discarded here — never stored (ADR-001)

        except Exception as e:
            logger.warning("Presidio content scan failed for %s (non-fatal): %s", rel_path, e)

    try:
        from src.utils.scan_logger import log_layer2_content_scan
        log_layer2_content_scan(
            run_id=run_id,
            files_scanned=len(content_snippets),
            files_with_pii=files_with_pii,
            entity_types_found=list(dict.fromkeys(all_entity_types)),
        )
    except Exception:
        pass


def is_available() -> bool:
    """Check if Presidio is installed and functional."""
    try:
        _get_engines()
        return True
    except Exception:
        return False


# ── ADR-029: System prompt anonymization ─────────────────────────────────────

SYSTEM_PROMPT_ENTITIES = [
    "PERSON",
    "EMAIL_ADDRESS",
    "PHONE_NUMBER",
    "LOCATION",
    "NRP",
    "ORGANIZATION",   # company names common in system prompts
    "URL",            # internal endpoints
]


def anonymize_system_prompt(raw: str, language: str = "en") -> str:
    """
    Anonymize system prompt content before sending to local Phi-4-mini.
    Uses extended entity list including ORGANIZATION and URL.
    NEVER called with raw content going to external services.
    """
    if not raw or not raw.strip():
        return raw
    try:
        analyzer, anonymizer = _get_engines()
        results = analyzer.analyze(
            text=raw,
            language=language,
            entities=SYSTEM_PROMPT_ENTITIES,
            allow_list=TECH_ALLOW_LIST,
        )
        if results:
            summary = ", ".join(f"{r.entity_type}({r.score:.2f})" for r in results)
            logger.info("Presidio system_prompt: anonymised %d entities — %s", len(results), summary)
        return anonymizer.anonymize(text=raw, analyzer_results=results).text
    except Exception as e:
        logger.warning("Presidio system_prompt anonymization failed (non-fatal): %s", e)
        return raw
