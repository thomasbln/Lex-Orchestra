"""
Layer 3 — Local LLM Classifier (ADR-028, revisited for ADR-050)
================================================================
Classifies anonymised code snippets for EU AI Act compliance signals.
Runs via Ollama — no external API, no cloud.

Deployment targets:
  - NucBox (sovereign):  gemma4:e4b via http://ollama:11434 (ADR-050)
  - Pi (edge, legacy):   phi4-mini:3.8b-q4_K_M via localhost:11434 (ADR-028)
  - Local dev:           whatever OLLAMA_MODEL env names

The model + URL are env-var driven so the scanner runs on any target without
a code change. `OLLAMA_MODEL` and `OLLAMA_URL` are set in docker/envs/.env.*
per profile (see .env.sovereign, .env.edge).

ADR-028 invariants:
  - Input MUST be anonymised (Presidio Layer 2 applied first)
  - System-prompt content is NEVER passed as input
  - temperature=0, num_predict=8 for deterministic short output
  - Output parsing: .strip().split()[0].rstrip('.').lower()
  - Non-fatal: fallback to "none" on any error
"""
from __future__ import annotations

import json
import logging
import os

from src.llm import complete_ollama, resolve_ollama_endpoint

logger = logging.getLogger(__name__)

# ADR-127 Phase 1: endpoint lookup centralized in src/llm; resolves byte-identically
# to the prior os.getenv("OLLAMA_URL", <default>) — site reads OLLAMA_URL only.
OLLAMA_URL = resolve_ollama_endpoint(
    full_env="OLLAMA_URL", full_default="http://host.docker.internal:11434/api/generate"
)
# Env-driven. Sovereign (.env.sovereign) sets OLLAMA_MODEL=gemma4:e4b,
# edge (.env.edge) sets phi4-mini. Default is gemma4:e4b because that is the
# current primary. A hardcoded fallback was the bug this module shipped with
# for too long — it made is_available() return False on any target that had
# moved off phi4-mini, silently skipping the whole Layer 3 pipeline.
MODEL = os.getenv("OLLAMA_MODEL", "gemma4:e4b")

# Timeout in seconds — 120s covers cold-start on CPU targets
OLLAMA_TIMEOUT = int(os.getenv("OLLAMA_TIMEOUT", "120"))

TASK_CONFIGS: dict[str, tuple[str, str]] = {
    "prompt_role": (
        "Classify the role of this system prompt or AI assistant.",
        "Allowed: hr | marketing | legal | customer_service | content_generation | general | none",
    ),
    "decision_logic": (
        "Does this code make automated decisions that directly affect individuals?",
        "Allowed: yes | no",
    ),
    "art9_category": (
        "Does this code process special category data under GDPR Article 9?",
        "Allowed: health | biometric | political | religion | none",
    ),
    "autonomy_level": (
        "What is the autonomy level of this AI system?",
        "Allowed: autonomous | assistive | none",
    ),
}

CLASSIFY_PROMPT = """You are a legal compliance classifier for EU AI Act and GDPR.
Answer with EXACTLY ONE value from the allowed list. No explanation. No punctuation.

Task: {task}
{constraint}

Input:
{snippet}

Answer:"""


def _call_ollama(prompt: str, num_predict: int = 8) -> str | None:
    """Call the configured Ollama model. Returns raw response or None."""
    try:
        # ADR-127 Phase 1: transport via central client; return contract unchanged.
        data = complete_ollama(
            prompt,
            endpoint=OLLAMA_URL,
            model=MODEL,
            options={"temperature": 0, "num_predict": num_predict},
            timeout=OLLAMA_TIMEOUT,
        )
        return data.get("response", "").strip()
    except Exception as e:
        logger.warning("Ollama call failed: %s", e)
        return None


def _parse_output(raw: str | None, allowed: set[str]) -> str:
    """
    Parse model output to one of the allowed values.
    ADR-028 lesson: model may append period or comma.
    """
    if not raw:
        return "none"
    parsed = raw.strip().split()[0].rstrip(".").rstrip(",").lower()
    return parsed if parsed in allowed else "none"


def classify(task_key: str, snippet: str, run_id: str = "unknown") -> str:
    """
    Classify an anonymised code snippet for a given task.
    Returns value from allowed set — never raises.
    """
    if task_key not in TASK_CONFIGS:
        return "none"
    task, constraint = TASK_CONFIGS[task_key]
    allowed = {v.strip() for v in constraint.replace("Allowed:", "").split("|")}
    snippet = snippet[:512]
    prompt = CLASSIFY_PROMPT.format(task=task, constraint=constraint, snippet=snippet)
    raw = _call_ollama(prompt)
    result = _parse_output(raw, allowed)
    if result == "none" and raw is not None:
        result = _parse_output(_call_ollama(prompt), allowed)
    logger.debug("classify(%s) → %s", task_key, result)

    try:
        from src.utils.scan_logger import log_layer3_classification
        log_layer3_classification(run_id, task_key, result, MODEL)
    except Exception:
        pass

    return result


def classify_all(snippet: str, run_id: str = "unknown") -> dict[str, str]:
    """Run all 4 classification tasks. Returns dict of results."""
    return {task_key: classify(task_key, snippet, run_id=run_id) for task_key in TASK_CONFIGS}


def compute_dsfa_trigger(classifications: dict[str, str]) -> bool:
    """
    Compute DSFA trigger (ADR-028).
    True if Art.9 data present OR (decision_logic=yes AND autonomy=autonomous).
    """
    art9 = classifications.get("art9_category", "none") != "none"
    decision_autonomous = (
        classifications.get("decision_logic") == "yes"
        and classifications.get("autonomy_level") == "autonomous"
    )
    return art9 or decision_autonomous


def is_available() -> bool:
    """Check if Ollama + the configured MODEL are reachable."""
    try:
        return _call_ollama("Reply with: ok", num_predict=4) is not None
    except Exception:
        return False


# ── ADR-029: System prompt role classification ───────────────────────────────

SYSTEM_PROMPT_ROLE_PROMPT = """\
You are a legal compliance classifier for the EU AI Act.
Classify the role of this AI system based on its system prompt.
Answer with EXACTLY ONE value from the allowed list. No explanation.

System prompt (anonymized): {system_prompt_clean}

Allowed: hr_recruitment | credit_scoring | education_assessment | \
healthcare_decision | biometric_identification | critical_infrastructure | \
law_enforcement | customer_service | content_generation | general_assistant | none

Answer:"""

VALID_ROLES = {
    "hr_recruitment", "credit_scoring", "education_assessment",
    "healthcare_decision", "biometric_identification", "critical_infrastructure",
    "law_enforcement", "customer_service", "content_generation",
    "general_assistant", "none",
}


def classify_system_prompt_role(system_prompt_clean: str) -> tuple[str, float]:
    """
    Classify anonymized system prompt into EU AI Act UseCase role.
    Returns (role, confidence). Falls back to 'none' after one retry.
    """
    prompt = SYSTEM_PROMPT_ROLE_PROMPT.format(system_prompt_clean=system_prompt_clean)
    for attempt in range(2):
        result = _call_ollama(prompt, num_predict=16)
        if result is None:
            continue
        role = result.strip().split()[0].rstrip(".").rstrip(",").lower()
        if role in VALID_ROLES:
            confidence = 0.60 if attempt == 0 else 0.45
            logger.info("system_prompt_role classified: %s (attempt %d)", role, attempt + 1)
            return role, confidence
    logger.warning("system_prompt_role classification failed — defaulting to 'none'")
    return "none", 0.0


# ── ADR-062: Service Classification Fallback ──────────────────────────────────

SERVICE_CLASSIFY_PROMPT = """\
You are a software infrastructure classifier for GDPR compliance.
Classify this package or library name into a known SaaS service or cloud component.

Package name: {package_name}

Return ONLY valid JSON on a single line, no explanation, no markdown:
{{"canonical_name": "...", "category": "...", "country": "...", "confidence": 0.0}}

Rules:
- canonical_name: official product name (e.g. "MongoDB", "Redis", "DigitalOcean")
- category: exactly one of these values:
  baas|database|nosql_db|cache_db|ai_llm|ai_platform|payment|monitoring|email|
  email_marketing|auth|hosting|cloud|storage|vector_db|analytics|cdn_security|
  vcs|ci_cd|crm|crm_support|sms|observability|media_storage|search_db|security|unknown
- country: ISO 3166-1 alpha-3 code (USA, DEU, GBR, EU, unknown)
- confidence: float 0.0-1.0 (how certain you are)

If this is a utility/framework (pytest, express, lodash, react): category=unknown, confidence=0.1
If this is internal/private code: category=unknown, confidence=0.1
If completely unrecognized: category=unknown, confidence=0.2"""

_VALID_CATEGORIES = frozenset({
    "baas", "database", "nosql_db", "cache_db", "ai_llm", "ai_platform",
    "payment", "monitoring", "email", "email_marketing", "auth", "hosting",
    "cloud", "storage", "vector_db", "analytics", "cdn_security", "vcs",
    "ci_cd", "crm", "crm_support", "sms", "observability", "media_storage",
    "search_db", "security", "unknown",
})


def classify_service(package_name: str) -> dict | None:
    """
    Classify an unknown package/library name into a ServiceCategory via Gemma4.
    ADR-001: package_name is a dependency name (public knowledge), never PII.
    Non-fatal — returns None on parse failure or Ollama unavailable.
    """
    prompt = SERVICE_CLASSIFY_PROMPT.format(package_name=package_name[:64])
    raw = _call_ollama(prompt, num_predict=64)
    if not raw:
        return None
    try:
        clean = raw.strip()
        for fence in ("```json", "```"):
            clean = clean.lstrip(fence).rstrip(fence).strip()
        start = clean.find("{")
        end = clean.rfind("}") + 1
        if start == -1 or end == 0:
            logger.warning("classify_service: no JSON found for '%s': %s", package_name, raw[:80])
            return None
        result = json.loads(clean[start:end])
        if result.get("category") not in _VALID_CATEGORIES:
            result["category"] = "unknown"
        if not isinstance(result.get("confidence"), (int, float)):
            result["confidence"] = 0.0
        result["confidence"] = float(result["confidence"])
        if not result.get("canonical_name"):
            result["canonical_name"] = package_name.capitalize()
        return result
    except (json.JSONDecodeError, KeyError, ValueError) as e:
        logger.warning("classify_service: parse failed for '%s': %s | raw: %s",
                       package_name, e, raw[:80])
        return None
