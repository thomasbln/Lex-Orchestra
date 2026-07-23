"""
Infrastructure Scout — Signal Categories 2 + 3
===============================================
Implements ADR-014 Signal Categories:
  Category 2 — Security Posture (hardcoded secrets, Docker misconfigurations)
  Category 3 — AI Deployment Signals (system prompts, LLM call patterns, use case hints)

Categories 1 (manifest scan), 4 (website scan), 5 (AI threats), 6 (platform) are handled
in main.py fallback or deferred to Phase 2.

ADR-001: file paths in security_findings are relative — anonymised upstream by AssetTranslator.
"""

import logging
import re
from pathlib import Path

from src.scout.signal_map import canonical, canonical_with_fallback

logger = logging.getLogger(__name__)

# ── Directories to skip ────────────────────────────────────────────────────────

SKIP_DIRS = {
    ".venv", "venv", ".env", "node_modules", "docs", "tests",
    ".git", "__pycache__", ".mypy_cache", ".pytest_cache",
    "dist", "build", ".next", ".nuxt",
}

# ── Category 2 — Security Posture ─────────────────────────────────────────────

SECRET_PATTERNS = [
    (r'sk-[a-zA-Z0-9]{20,}',                                         "Hardcoded OpenAI/Anthropic API key", "CRITICAL", "A.9.4.1"),
    (r'AKIA[0-9A-Z]{16}',                                             "Hardcoded AWS Access Key ID",        "CRITICAL", "A.9.4.1"),
    (r'ghp_[a-zA-Z0-9]{36}',                                          "Hardcoded GitHub token",             "HIGH",     "A.9.4.1"),
    (r'(?i)(api[_-]?key|secret[_-]?key|private[_-]?key|password)\s*[=:]\s*["\']([^"\']{8,})["\']',
     "Potential hardcoded credential",                                                                       "HIGH",     "A.9.4.1"),
    (r'-----BEGIN (?:RSA |EC )?PRIVATE KEY-----',                     "Private key in source file",         "CRITICAL", "A.10.1.1"),
]

# Lines containing these strings are skipped — they reference env vars, not real values
SECRET_SKIP_MARKERS = [
    "os.getenv", "environ", "process.env",
    "example", "placeholder", "your_", "<", ">", "TODO", "FIXME",
    "os.environ",
]

DOCKER_CHECKS = [
    ("0.0.0.0:5432",         "Database port exposed to all interfaces", "HIGH", "A.13.1.3"),
    ("0.0.0.0:3306",         "Database port exposed to all interfaces", "HIGH", "A.13.1.3"),
    ("0.0.0.0:27017",        "Database port exposed to all interfaces", "HIGH", "A.13.1.3"),
    ("privileged: true",     "Container running in privileged mode",    "HIGH", "A.12.6.1"),
    ("/var/run/docker.sock", "Docker socket mounted in container",      "HIGH", "A.12.6.1"),
]

# ── Category 3 — AI Deployment Signals ────────────────────────────────────────

SYSTEM_PROMPT_PATTERNS = [
    r'(?i)system[_\-\s]?prompt\s*[=:]',
    r'(?i)"role"\s*:\s*"system"',
    r"(?i)'role'\s*:\s*'system'",
    r'(?i)SystemMessage\(',
    r'(?i)system=["\'`]',
]

LLM_CALL_PATTERNS = [
    (r'client\.messages\.create\(',    "anthropic", "ai_llm"),
    (r'anthropic\.Anthropic\(\)',      "anthropic", "ai_llm"),
    (r'openai\.ChatCompletion',        "openai",    "ai_llm"),
    (r'client\.chat\.completions\.create\(', "openai", "ai_llm"),
    (r'from langchain',                "langchain", "ai_llm"),
    (r'ChatOpenAI\(',                  "openai",    "ai_llm"),
    (r'ChatAnthropic\(',               "anthropic", "ai_llm"),
]

USECASE_HINTS = [
    (r'(?i)(chatbot|chat[_\-]?widget|customer[_\-]?support)',                    "customer_service_chatbot",   0.7),
    (r'(?i)(generate[_\-]?content|content[_\-]?generat|blog[_\-]?post|marketing[_\-]?copy)', "ai_content_generator", 0.7),
    (r'(?i)(code[_\-]?review|document[_\-]?analys|contract[_\-]?analys)',        "ai_document_analyzer",       0.8),
    (r'(?i)(autonomous[_\-]?agent|agentic|langgraph|autogen|crewai)',             "ai_autonomous_agent",        0.9),
    (r'(?i)(medical[_\-]?diagn|health[_\-]?assess)',                             "ai_medical_assistant",       0.9),
    (r'(?i)(cv[_\-]?screen|resume[_\-]?screen|hiring[_\-]?decision)',            "ai_hr_screening",            0.9),
    (r'(?i)(credit[_\-]?scor|loan[_\-]?approv)',                                 "ai_credit_scoring",          0.9),
]

# ── File collection helpers ────────────────────────────────────────────────────

def _source_files(base: Path, extensions: set[str]) -> list[Path]:
    """Yield all files with given extensions, skipping SKIP_DIRS."""
    results = []
    for path in base.rglob("*"):
        rel = path.relative_to(base)
        if any(skip in rel.parts for skip in SKIP_DIRS):
            continue
        if path.suffix.lstrip(".") in extensions:
            results.append(path)
    return results


def _rel(base: Path, path: Path) -> str:
    """Return path relative to base as string."""
    try:
        return str(path.relative_to(base))
    except ValueError:
        return path.name


# ── Category 2 — Security Posture ─────────────────────────────────────────────

def _scan_security_posture(base: Path) -> list[dict]:
    findings = []

    # 2a — hardcoded secrets in source files
    source_exts = {"py", "ts", "js", "yaml", "yml"}
    env_globs = list(base.glob(".env*")) + list(base.glob("*/.env*"))
    env_files = [
        p for p in env_globs
        if not any(skip in p.relative_to(base).parts for skip in SKIP_DIRS)
        and "example" not in p.name.lower()
        and "sample" not in p.name.lower()
    ]
    code_files = _source_files(base, source_exts)

    for filepath in code_files + env_files:
        try:
            text = filepath.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            continue
        for lineno, line in enumerate(text.splitlines(), 1):
            if any(marker.lower() in line.lower() for marker in SECRET_SKIP_MARKERS):
                continue
            for pattern, description, severity, iso_control in SECRET_PATTERNS:
                if re.search(pattern, line):
                    findings.append({
                        "signal_type": "security_posture",
                        "severity":    severity,
                        "iso_control": iso_control,
                        "file":        _rel(base, filepath),
                        "line":        lineno,
                        "description": description,
                    })
                    break  # one finding per line

    # 2b — Docker misconfigurations
    dc_files = (
        list(base.glob("docker-compose.y*ml"))
        + list(base.glob("*/docker-compose.y*ml"))
        + list(base.glob("docker/*/docker-compose.y*ml"))
    )
    dc_files = [p for p in dc_files if not any(skip in p.relative_to(base).parts for skip in SKIP_DIRS)]

    for dc_path in dc_files:
        try:
            text = dc_path.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            continue
        for pattern_str, description, severity, iso_control in DOCKER_CHECKS:
            if pattern_str in text:
                findings.append({
                    "signal_type": "security_posture",
                    "severity":    severity,
                    "iso_control": iso_control,
                    "file":        _rel(base, dc_path),
                    "line":        None,
                    "description": description,
                })

    return findings


# ── Category 3 — AI Deployment Signals ────────────────────────────────────────

def _scan_deployment_signals(base: Path) -> tuple[list[dict], list[dict]]:
    """
    Returns (new_services, deployment_signals).
    new_services: services discovered from LLM call patterns in source code.
    deployment_signals: use case hints and system prompt detections.
    """
    code_files = _source_files(base, {"py", "ts", "js"})

    new_services: list[dict] = []
    signals: list[dict] = []
    seen_services: set[str] = set()
    seen_hints: set[str] = set()

    for filepath in code_files:
        try:
            text = filepath.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            continue
        rel = _rel(base, filepath)

        # 3b — LLM call patterns → services
        for pattern, raw_name, category in LLM_CALL_PATTERNS:
            if re.search(pattern, text):
                canon = canonical(raw_name) or raw_name.capitalize()
                if canon not in seen_services:
                    seen_services.add(canon)
                    new_services.append({
                        "name":       canon,
                        "category":   category,
                        "type":       "code_signal",
                        "source":     rel,
                        "confidence": 0.85,
                    })

        # 3a — system prompt patterns → deployment signal
        for pattern in SYSTEM_PROMPT_PATTERNS:
            if re.search(pattern, text):
                hint = "ai_assistant_general"
                if hint not in seen_hints:
                    seen_hints.add(hint)
                    signals.append({
                        "signal_type": "deployment",
                        "usecase_hint": hint,
                        "evidence":    f"System prompt pattern found in {rel}",
                        "confidence":  0.8,
                        "verified":    False,
                    })
                break

        # 3c — use case type hints
        for pattern, usecase_hint, confidence in USECASE_HINTS:
            if re.search(pattern, text) and usecase_hint not in seen_hints:
                seen_hints.add(usecase_hint)
                signals.append({
                    "signal_type": "deployment",
                    "usecase_hint": usecase_hint,
                    "evidence":    f"Pattern '{pattern}' matched in {rel}",
                    "confidence":  confidence,
                    "verified":    False,
                })

    return new_services, signals


# ── ADR-027 — Risk Signal Extraction (Schicht 1: Regex) ───────────────────────

SIGNAL_PATTERNS: dict[str, list[str]] = {
    "personal_data": [
        r"req\.body\.(email|name|phone|address)",
        r"\buser_id\b",
        r"db\.insert\(user",
        r"INSERT INTO users",
    ],
    "decision_logic": [
        r"approveLoan|rejectApplication|approve\(|reject\(",
        r"if\s*\(\s*score\s*[><=]",
        r"hire\(|deny\(|disqualify\(",
    ],
    "ai_usage": [
        r"openai\.|anthropic\.",
        r"client\.messages\.create",
        r"ChatCompletion|completions\.create",
    ],
    "autonomy": [
        r"langgraph|autogen|crewai",
        r"system\.execute|auto_decide",
        r"AgentExecutor|run_agent",
    ],
    "user_interaction": [
        r"@app\.(?:post|get)\(['\"]\/chat",
        r"\bchatbot\b",
        r"req\.body\.message",
    ],
    "system_prompt": [
        r'"role"\s*:\s*"system"',
        r"SYSTEM_PROMPT\s*=",
        r"system\s*=\s*['\"`]",
    ],
    "secret_detected": [
        r"sk-[a-zA-Z0-9]{20,}",
        r"AKIA[0-9A-Z]{16}",
        r"ghp_[a-zA-Z0-9]{36}",
        r"(?i)password\s*=\s*['\"][^'\"]{8,}['\"]",
    ],
    "docker_misconfiguration": [
        r"privileged:\s*true",
        r"/var/run/docker\.sock",
        r"0\.0\.0\.0:5432",
        r"0\.0\.0\.0:3306",
    ],
}

SIGNAL_CONFIDENCE: dict[str, float] = {
    "secret_detected":         0.95,
    "docker_misconfiguration": 0.90,
    "autonomy":                0.90,
    "decision_logic":          0.80,
    "system_prompt":           0.80,
    "personal_data":           0.70,
    "ai_usage":                0.70,
    "user_interaction":        0.70,
}


def extract_risk_signals(base_path: Path) -> list[dict]:
    """
    Schicht 1 — Deterministischer Regex-Scanner (ADR-028).
    Scannt Source-Files auf Risiko-relevante Patterns.
    Gibt Signals mit signal_type, value, confidence, evidence[], source zurück.
    evidence enthält nur relative Pfade — kein Code-Inhalt (ADR-001).
    System-Prompt Inhalt wird NIEMALS extrahiert oder weitergegeben.
    """
    signals = []
    source_exts = {"py", "ts", "js", "yml", "yaml"}

    for signal_type, patterns in SIGNAL_PATTERNS.items():
        matches: list[str] = []

        for file_path in _source_files(base_path, source_exts):
            rel = _rel(base_path, file_path)
            try:
                content = file_path.read_text(encoding="utf-8", errors="ignore")
            except Exception:
                continue

            for pattern in patterns:
                found = re.findall(pattern, content, re.IGNORECASE)
                if found:
                    # Store relative path only — never code content (ADR-001)
                    matches.append(f"{rel}: {pattern}")

        if matches:
            base_confidence = SIGNAL_CONFIDENCE.get(signal_type, 0.70)
            # Slight boost per additional match, capped at 0.95
            confidence = min(base_confidence + len(matches) * 0.02, 0.95)
            signals.append({
                "signal_type": signal_type,
                "value":       "detected",
                "confidence":  round(confidence, 2),
                "evidence":    matches[:5],  # max 5 evidence strings
                "source":      "regex",
            })

    return signals


# ── Category 1 — Manifest Scanner ─────────────────────────────────────────────

def _scan_manifests(base: Path) -> tuple[list[str], list[str], list[dict]]:
    """
    Scan dependency manifest files for known third-party services.
    Supports: package.json, requirements.txt, Pipfile, pyproject.toml,
              composer.json, pom.xml, build.gradle, *.csproj, packages.config,
              Gemfile, go.mod
    Returns (canonical service names, LLM-classified categories, LLM raw results).
    ADR-062: unknown packages are classified via Gemma4 fallback.
    ADR-072: categories are kept even when no canonical_name is returned —
    they drive the ServiceCategory-based graph lookup.
    """
    import json

    found: set[str] = set()
    categories: set[str] = set()
    llm_results: list[dict] = []

    def add(raw_name: str) -> None:
        c = canonical(raw_name)
        if c:
            found.add(c)
            return
        # ADR-062 + ADR-072: Gemma4 fallback — accept category even without canonical_name
        c_llm, cat_llm, llm_result = canonical_with_fallback(raw_name, use_llm=True)
        if c_llm:
            found.add(c_llm)
        if cat_llm:
            categories.add(cat_llm)
        if llm_result and (c_llm or cat_llm):
            llm_results.append({**llm_result, "package_name": raw_name})

    # ── package.json (Node / JS / TS) ─────────────────────────────────────
    for pj in base.rglob("package.json"):
        if any(p in pj.parts for p in ("node_modules", ".next", "dist", "build")):
            continue
        try:
            data = json.loads(pj.read_text(encoding="utf-8", errors="ignore"))
            deps = {}
            deps.update(data.get("dependencies", {}))
            deps.update(data.get("devDependencies", {}))
            for pkg in deps:
                clean = pkg.lstrip("@")
                if "/" in clean:
                    scope, name = clean.split("/", 1)
                    add(scope)
                    add(name)
                else:
                    add(clean)
        except Exception:
            pass

    # ── requirements.txt (Python) ──────────────────────────────────────────
    for req in base.rglob("requirements*.txt"):
        try:
            for line in req.read_text(encoding="utf-8", errors="ignore").splitlines():
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                pkg = re.split(r"[>=<!;\[\s]", line)[0].strip()
                if pkg:
                    add(pkg)
        except Exception:
            pass

    # ── Pipfile (Python) ───────────────────────────────────────────────────
    for pf in base.rglob("Pipfile"):
        try:
            in_packages = False
            for line in pf.read_text(encoding="utf-8", errors="ignore").splitlines():
                if line.strip() in ("[packages]", "[dev-packages]"):
                    in_packages = True
                    continue
                if line.startswith("[") and in_packages:
                    in_packages = False
                if in_packages:
                    pkg = line.split("=")[0].strip().strip('"\'')
                    if pkg and not pkg.startswith("#"):
                        add(pkg)
        except Exception:
            pass

    # ── pyproject.toml (Python) ────────────────────────────────────────────
    for pt in base.rglob("pyproject.toml"):
        try:
            content = pt.read_text(encoding="utf-8", errors="ignore")
            for pkg in re.findall(r'["\']([a-zA-Z0-9_\-]+)(?:[>=<!\s]|["\'])', content):
                add(pkg)
        except Exception:
            pass

    # ── composer.json (PHP / Laravel) ─────────────────────────────────────
    for cj in base.rglob("composer.json"):
        try:
            data = json.loads(cj.read_text(encoding="utf-8", errors="ignore"))
            deps = {}
            deps.update(data.get("require", {}))
            deps.update(data.get("require-dev", {}))
            for pkg in deps:
                parts = pkg.split("/")
                for part in parts:
                    add(part)
                add(pkg.replace("/", "").replace("-", ""))
        except Exception:
            pass

    # ── pom.xml (Java / Maven) ────────────────────────────────────────────
    for pom in base.rglob("pom.xml"):
        try:
            content = pom.read_text(encoding="utf-8", errors="ignore")
            for artifact in re.findall(r"<artifactId>([^<]+)</artifactId>", content):
                add(artifact)
        except Exception:
            pass

    # ── build.gradle (Java / Kotlin) ──────────────────────────────────────
    for gradle in base.rglob("build.gradle*"):
        try:
            content = gradle.read_text(encoding="utf-8", errors="ignore")
            for dep in re.findall(r"""(?:implementation|compile|api)\s+['"]([^'"]+)['"]""", content):
                parts = dep.split(":")
                for part in parts:
                    add(part.split(".")[-1])
        except Exception:
            pass

    # ── *.csproj (C# / .NET) ──────────────────────────────────────────────
    for csproj in base.rglob("*.csproj"):
        try:
            content = csproj.read_text(encoding="utf-8", errors="ignore")
            for pkg in re.findall(r'<PackageReference\s+Include="([^"]+)"', content):
                add(pkg)
        except Exception:
            pass

    # ── packages.config (C# legacy) ───────────────────────────────────────
    for pc in base.rglob("packages.config"):
        try:
            content = pc.read_text(encoding="utf-8", errors="ignore")
            for pkg in re.findall(r'<package\s+id="([^"]+)"', content):
                add(pkg)
        except Exception:
            pass

    # ── Gemfile (Ruby) ────────────────────────────────────────────────────
    for gf in base.rglob("Gemfile"):
        try:
            content = gf.read_text(encoding="utf-8", errors="ignore")
            for pkg in re.findall(r"""gem\s+['"]([^'"]+)['"]""", content):
                add(pkg)
        except Exception:
            pass

    # ── go.mod (Go) ───────────────────────────────────────────────────────
    for gm in base.rglob("go.mod"):
        try:
            content = gm.read_text(encoding="utf-8", errors="ignore")
            for module in re.findall(r"^\s+([^\s]+)\s+v", content, re.MULTILINE):
                parts = module.split("/")
                for part in parts:
                    add(part)
        except Exception:
            pass

    result = sorted(found)
    category_result = sorted(categories)
    logger.info(
        "Manifest scanner: %d canonical services, %d LLM categories: services=%s categories=%s",
        len(result), len(category_result), result, category_result,
    )
    if llm_results:
        logger.info(
            "signal_map Gemma4-Fallback: %d new services classified: %s",
            len(llm_results),
            [r.get("canonical_name") for r in llm_results],
        )
    return result, category_result, llm_results


# ── Public interface ───────────────────────────────────────────────────────────

def run_scout(
    repo_path: str | None,
    live_url: str | None,
    depth: str = "quick",
) -> dict:
    """
    Run the Infrastructure Scout on a local repository path.

    Signal Categories implemented:
      Category 2 — Security Posture (secrets, Docker misconfig)
      Category 3 — AI Deployment Signals (system prompts, LLM calls, use case hints)

    Categories 1 (manifest scan) and 4-6 remain in main.py fallback / Phase 2.

    Returns:
        {
            "services":           list[dict],  # new code_signal services
            "security_findings":  list[dict],
            "deployment_signals": list[dict],
        }

    ADR-001: file paths in security_findings are relative — anonymised by AssetTranslator.
    """
    if not repo_path:
        logger.info("No repo_path provided — scout returning empty result")
        return {"services": [], "security_findings": [], "deployment_signals": []}

    base = Path(repo_path) if repo_path != "." else Path.cwd()
    if not base.is_dir():
        logger.warning("Scout: repo_path is not a directory: %s", repo_path)
        return {"services": [], "security_findings": [], "deployment_signals": []}

    logger.info("Scout: scanning %s (depth=%s)", base, depth)

    security_findings = _scan_security_posture(base)
    new_services, deployment_signals = _scan_deployment_signals(base)

    logger.info(
        "Scout: %d security findings, %d deployment signals, %d code services",
        len(security_findings), len(deployment_signals), len(new_services),
    )

    risk_signals = extract_risk_signals(base)
    logger.info("Scout: %d risk signals (Schicht 1)", len(risk_signals))

    manifest_services, manifest_categories, llm_classified = _scan_manifests(base)

    # Merge code-signal services with manifest services (deduplicated)
    code_service_names = [s["name"] for s in new_services if s.get("name")]
    all_service_names = sorted(set(code_service_names + manifest_services))

    logger.info(
        "Scout total: %d services, %d LLM categories → services=%s categories=%s",
        len(all_service_names), len(manifest_categories),
        all_service_names, manifest_categories,
    )

    return {
        "services":            new_services,
        "service_names":       all_service_names,
        "service_categories":  manifest_categories,   # ADR-072
        "security_findings":   security_findings,
        "deployment_signals":  deployment_signals,
        "risk_signals":        risk_signals,
        "llm_classified":      llm_classified,
    }
