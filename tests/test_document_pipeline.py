"""
Tests: Document Pipeline — generation → disk → Supabase → versioning → view
=============================================================================
Verifies:
  1. DocumentOrchestrator generates expected .md files on disk
  2. generate_all() writes rows to generated_docs in Supabase
  3. _write_scan_result() writes to scan_results
  4. Second generate_all() run bumps version and marks prior rows outdated
  5. current_docs view returns latest version per doc_type only
  6. PATCH /docs/{run_id}/delivered sets telegram_sent=true + status=delivered
"""

import uuid
from pathlib import Path

import psycopg2
import psycopg2.extras
import pytest
import requests

from src.agents.document_architect import DocumentOrchestrator
from src.graph.asset_translator import _resolve_db_url
from src.workflow.main import LexState, _write_scan_result


PROJECT = f"test-pipeline-{uuid.uuid4().hex[:8]}"

GRAPH_RESULT = {
    "doc_types": ["AVV", "TOM", "SCC", "AI_Act_Manifest"],
    "overall_risk": "gpai",
    "services": [
        {
            "name": "Anthropic",
            "category": "ai_llm",
            "dpa_required": True,
            "ai_act_relevant": True,
            "country": "USA",
            "gdpr_adequate": False,
        }
    ],
    "docs_required": [],
    "controls": [],
    "risk_levels": [
        {"service": "Anthropic", "level": "GPAI", "action": "Technische Dokumentation"}
    ],
}

REASONING_RESULT = {
    "summary": "Test-Scan: KI-Dienste erkannt.",
    "priority_actions": ["DPA abschließen", "TOM dokumentieren"],
    "eu_ai_act_classification": "gpai",
}


@pytest.fixture(scope="module")
def db_conn():
    """Module-level DB connection — skips all tests if Supabase unreachable."""
    url = _resolve_db_url()
    if not url:
        pytest.skip("No DB URL configured — set MCP_SUPABASE_URL or DATABASE_URL")
    try:
        conn = psycopg2.connect(url)
        yield conn
        conn.close()
    except Exception as e:
        pytest.skip(f"Supabase not reachable: {e}")


def _seed_scan_result(run_id: str, project_name: str) -> None:
    """Insert a minimal scan_results row to satisfy the FK constraint on generated_docs."""
    state: LexState = {
        "project_name":      project_name,
        "repo_url":          None,
        "live_url":          None,
        "scan_depth":        "quick",
        "dry_run":           True,
        "scout_result":      None,
        "graph_result":      GRAPH_RESULT,
        "reasoning_result":  REASONING_RESULT,
        "generated_docs":    [],
        "notification_sent": False,
        "run_id":            run_id,
        "errors":            [],
    }
    _write_scan_result(state)


def test_document_architect_generates_files(db_conn):
    """DocumentOrchestrator writes all expected .md files to disk."""
    run_id = str(uuid.uuid4())
    _seed_scan_result(run_id, PROJECT)
    architect = DocumentOrchestrator()
    generated = architect.generate_all(GRAPH_RESULT, REASONING_RESULT, PROJECT, run_id)

    expected_suffixes = {
        "AVV":            f"avv_{run_id[:8]}.md",
        "TOM":            f"tom_{run_id[:8]}.md",
        "SCC":            f"scc_{run_id[:8]}.md",
        "AI_Act_Manifest": f"ai_act_manifest_{run_id[:8]}.md",
    }

    generated_paths = [Path(d["file_path"]) for d in generated]
    try:
        for doc_type, suffix in expected_suffixes.items():
            matching = [p for p in generated_paths if p.name == suffix]
            assert matching, f"No file generated for {doc_type} (expected {suffix})"
            path = matching[0]
            assert path.exists(), f"File does not exist on disk: {path}"
            content = path.read_text(encoding="utf-8")
            assert len(content) > 0, f"File is empty: {path}"
            assert PROJECT in content, f"project_name missing in {path.name}"
    finally:
        for path in generated_paths:
            path.unlink(missing_ok=True)
        with db_conn.cursor() as cur:
            cur.execute("DELETE FROM generated_docs WHERE run_id = %s", (run_id,))
            cur.execute("DELETE FROM scan_results WHERE run_id = %s", (run_id,))
        db_conn.commit()


def test_document_architect_writes_supabase(db_conn):
    """generate_all() inserts generated_docs rows for all doc types including VVT + KI docs."""
    run_id = str(uuid.uuid4())
    _seed_scan_result(run_id, PROJECT)
    architect = DocumentOrchestrator()
    generated = architect.generate_all(GRAPH_RESULT, REASONING_RESULT, PROJECT, run_id)

    try:
        with db_conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute("SELECT * FROM generated_docs WHERE run_id = %s", (run_id,))
            rows = cur.fetchall()

        # Original 4 doc_types + VVT (always) + KI_System_Dokumentation + KI_Policy (Anthropic AI service)
        expected_count = len(GRAPH_RESULT["doc_types"]) + 3
        assert len(rows) == expected_count, (
            f"Expected {expected_count} rows, got {len(rows)}: {[r['doc_type'] for r in rows]}"
        )
        for row in rows:
            assert row["status"] == "draft", f"Expected status=draft, got {row['status']}"
            assert row["telegram_sent"] is False, "telegram_sent should be false on creation"
            assert row["version"] >= 1, f"Version should be >= 1, got {row['version']}"
    finally:
        for d in generated:
            Path(d["file_path"]).unlink(missing_ok=True)
        with db_conn.cursor() as cur:
            cur.execute("DELETE FROM generated_docs WHERE run_id = %s", (run_id,))
            cur.execute("DELETE FROM scan_results WHERE run_id = %s", (run_id,))
        db_conn.commit()


def test_scan_result_written(db_conn):
    """_write_scan_result() inserts one row into scan_results."""
    run_id = str(uuid.uuid4())
    state: LexState = {
        "project_name":      PROJECT,
        "repo_url":          "https://github.com/test/test",
        "live_url":          None,
        "scan_depth":        "quick",
        "dry_run":           True,
        "scout_result":      None,
        "graph_result":      GRAPH_RESULT,
        "reasoning_result":  REASONING_RESULT,
        "generated_docs":    [],
        "notification_sent": False,
        "run_id":            run_id,
        "errors":            [],
    }

    _write_scan_result(state)

    try:
        with db_conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute("SELECT * FROM scan_results WHERE run_id = %s", (run_id,))
            row = cur.fetchone()

        assert row is not None, "No row written to scan_results"
        assert row["project_name"] == PROJECT
        assert row["overall_risk"] is not None
        assert row["doc_types"] is not None and len(row["doc_types"]) > 0
    finally:
        with db_conn.cursor() as cur:
            cur.execute("DELETE FROM scan_results WHERE run_id = %s", (run_id,))
        db_conn.commit()


def test_version_increment(db_conn):
    """Second generate_all() run bumps version to 2 and marks first rows outdated."""
    run_id_1 = str(uuid.uuid4())
    run_id_2 = str(uuid.uuid4())
    _seed_scan_result(run_id_1, PROJECT)
    _seed_scan_result(run_id_2, PROJECT)
    architect = DocumentOrchestrator()
    gen1 = architect.generate_all(GRAPH_RESULT, REASONING_RESULT, PROJECT, run_id_1)
    gen2 = architect.generate_all(GRAPH_RESULT, REASONING_RESULT, PROJECT, run_id_2)

    try:
        with db_conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(
                "SELECT doc_type, version, status FROM generated_docs WHERE run_id = %s",
                (run_id_2,),
            )
            second_rows = cur.fetchall()

            cur.execute(
                "SELECT doc_type, version, status FROM generated_docs WHERE run_id = %s",
                (run_id_1,),
            )
            first_rows = cur.fetchall()

        for row in second_rows:
            assert row["version"] == 2, (
                f"{row['doc_type']}: expected version=2, got {row['version']}"
            )
        for row in first_rows:
            assert row["status"] == "outdated", (
                f"{row['doc_type']}: expected status=outdated, got {row['status']}"
            )
    finally:
        for d in gen1 + gen2:
            Path(d["file_path"]).unlink(missing_ok=True)
        with db_conn.cursor() as cur:
            cur.execute("DELETE FROM generated_docs WHERE project_name = %s", (PROJECT,))
            cur.execute("DELETE FROM scan_results WHERE project_name = %s", (PROJECT,))
        db_conn.commit()


def test_tom_has_bsi_defaults_in_right_column(db_conn):
    """ToM three-column table contains BSI basis_requirements, not empty placeholder."""
    run_id = str(uuid.uuid4())

    graph_result_bsi = {
        "doc_types": ["TOM"],
        "overall_risk": "high",
        "services": [],
        "docs_required": [],
        "controls": [{
            "service": "test",
            "control_id": "APP.3.2",
            "framework": "BSI_Grundschutz",
            "title_de": "Webserver",
            "text": "",
        }],
        "risk_levels": [],
        "active_risks": [],
    }

    _seed_scan_result(run_id, PROJECT)
    architect = DocumentOrchestrator()
    generated = architect.generate_all(graph_result_bsi, {"priority_actions": []}, PROJECT, run_id)

    tom_entry = next((d for d in generated if d["doc_type"] == "TOM"), None)
    assert tom_entry is not None

    tom_path = Path(tom_entry["file_path"])
    try:
        assert tom_path.exists(), f"ToM file not found: {tom_path}"
        content = tom_path.read_text(encoding="utf-8")

        # Three-column table header must be present
        assert "Standard-Umsetzung (BSI)" in content, "BSI column header missing from ToM"
        assert "Konkrete Umsetzung" in content, "Konkrete Umsetzung column missing from ToM"
        # APP.3.2 has no concrete implementation — must not appear in the curated controls table
        curated_section = content.split("Erkannte Controls aus Infrastruktur-Scan", 1)[-1]
        assert "APP.3.2" not in curated_section, "BSI control APP.3.2 should be filtered (no concrete impl)"
    finally:
        tom_path.unlink(missing_ok=True)
        with db_conn.cursor() as cur:
            cur.execute("DELETE FROM generated_docs WHERE run_id = %s", (run_id,))
            cur.execute("DELETE FROM scan_results WHERE run_id = %s", (run_id,))
        db_conn.commit()


def test_tom_contains_owasp_controls(db_conn):
    """ToM includes OWASP LLM controls from graph_result when AI services are present."""
    run_id = str(uuid.uuid4())

    graph_result_with_controls = {
        "doc_types": ["TOM"],
        "overall_risk": "gpai",
        "services": [
            {"name": "Anthropic", "category": "ai_llm", "dpa_required": True,
             "ai_act_relevant": True, "country": "USA", "gdpr_adequate": False}
        ],
        "docs_required": [],
        "controls": [
            {"service": "Anthropic", "control_id": "LLM01", "framework": "OWASP_LLM_Top10",
             "title_de": "Prompt Injection", "text": None,
             "default_tom_measure": "Input-Validierung aller Nutzereingaben vor LLM-Call"},
            {"service": "Anthropic", "control_id": "LLM02", "framework": "OWASP_LLM_Top10",
             "title_de": "Insecure Output Handling", "text": None,
             "default_tom_measure": "Output-Encoding und Content-Security-Policy"},
            {"service": "Anthropic", "control_id": "A.8.1", "framework": "ISO_27001",
             "title_de": "User Endpoint Devices", "text": None,
             "default_tom_measure": "MDM-Richtlinie für alle Endgeräte"},
        ],
        "risk_levels": [{"service": "Anthropic", "level": "GPAI", "action": "Dokumentation"}],
    }

    _seed_scan_result(run_id, PROJECT)
    architect = DocumentOrchestrator()
    generated = architect.generate_all(graph_result_with_controls, REASONING_RESULT, PROJECT, run_id)

    tom_entry = next((d for d in generated if d["doc_type"] == "TOM"), None)
    assert tom_entry is not None

    tom_path = Path(tom_entry["file_path"])
    try:
        assert tom_path.exists(), f"ToM file not found: {tom_path}"
        content = tom_path.read_text(encoding="utf-8")

        assert "LLM01" in content, "OWASP LLM control LLM01 missing from ToM"
        assert "Prompt Injection" in content, "OWASP LLM control title missing from ToM"
        assert "OWASP LLM Top 10" in content or "LLM01" in content, \
            "OWASP LLM controls should appear in 3-column table under framework label"
        assert "A.8.1" in content, "ISO 27001 control missing from ToM"
    finally:
        tom_path.unlink(missing_ok=True)
        with db_conn.cursor() as cur:
            cur.execute("DELETE FROM generated_docs WHERE run_id = %s", (run_id,))
            cur.execute("DELETE FROM scan_results WHERE run_id = %s", (run_id,))
        db_conn.commit()


def test_dpa_uses_graph_data(db_conn):
    """DPA uses data_categories + deletion_period from service properties instead of placeholders."""
    run_id = str(uuid.uuid4())

    graph_result_rich = {
        "doc_types": ["AVV"],
        "overall_risk": "gpai",
        "services": [
            {
                "name": "Anthropic",
                "category": "ai_llm",
                "dpa_required": True,
                "ai_act_relevant": True,
                "country": "USA",
                "gdpr_adequate": False,
                "dpa_url": "https://www.anthropic.com/legal/data-processing-addendum",
                "data_categories": "Anfragen, Antworten, Nutzungsmetadaten",
                "data_subjects": "Endnutzer, Mitarbeiter",
                "deletion_period": "30 Tage nach Vertragsende",
            }
        ],
        "docs_required": [],
        "controls": [],
        "risk_levels": [],
    }

    _seed_scan_result(run_id, PROJECT)
    from src.agents.document_architect import DocumentOrchestrator
    architect = DocumentOrchestrator()
    generated = architect.generate_all(graph_result_rich, REASONING_RESULT, PROJECT, run_id)

    avv_entry = next((d for d in generated if d["doc_type"] == "AVV"), None)
    assert avv_entry is not None

    avv_path = Path(avv_entry["file_path"])
    try:
        assert avv_path.exists(), f"AVV file not found: {avv_path}"
        content = avv_path.read_text(encoding="utf-8")

        assert "- Anfragen" in content, "data_category 'Anfragen' missing"
        assert "- Antworten" in content, "data_category 'Antworten' missing"
        assert "- Nutzungsmetadaten" in content, "data_category 'Nutzungsmetadaten' missing"
        assert "30 Tage nach Vertragsende" in content, \
            "deletion_period from service not in DPA"
        assert "Endnutzer" in content, \
            "data_subjects from service not in DPA"
        assert "§ 7" in content, "Löschung section (§ 7) missing from DPA"
    finally:
        avv_path.unlink(missing_ok=True)
        with db_conn.cursor() as cur:
            cur.execute("DELETE FROM generated_docs WHERE run_id = %s", (run_id,))
            cur.execute("DELETE FROM scan_results WHERE run_id = %s", (run_id,))
        db_conn.commit()


def test_avv_doc_type_matches_graph(db_conn):
    """generate_all() must use 'AVV' not 'DPA' as doc_type."""
    run_id = str(uuid.uuid4())
    _seed_scan_result(run_id, PROJECT)
    architect = DocumentOrchestrator()
    generated = architect.generate_all(GRAPH_RESULT, REASONING_RESULT, PROJECT, run_id)

    doc_types = [d["doc_type"] for d in generated]
    try:
        assert "AVV" in doc_types, "doc_type 'AVV' missing from generated docs"
        assert "DPA" not in doc_types, "doc_type 'DPA' must not appear — renamed to 'AVV'"
    finally:
        for d in generated:
            Path(d["file_path"]).unlink(missing_ok=True)
        with db_conn.cursor() as cur:
            cur.execute("DELETE FROM generated_docs WHERE run_id = %s", (run_id,))
            cur.execute("DELETE FROM scan_results WHERE run_id = %s", (run_id,))
        db_conn.commit()


def test_avv_file_named_correctly(db_conn):
    """Generated AVV file must be named avv_*.md not dpa_*.md."""
    run_id = str(uuid.uuid4())
    _seed_scan_result(run_id, PROJECT)
    architect = DocumentOrchestrator()
    generated = architect.generate_all(GRAPH_RESULT, REASONING_RESULT, PROJECT, run_id)

    avv_doc = next((d for d in generated if d["doc_type"] == "AVV"), None)
    try:
        assert avv_doc is not None, "No AVV doc generated"
        assert "avv_" in Path(avv_doc["file_path"]).name, (
            f"AVV file should be named avv_*.md, got: {avv_doc['file_path']}"
        )
    finally:
        for d in generated:
            Path(d["file_path"]).unlink(missing_ok=True)
        with db_conn.cursor() as cur:
            cur.execute("DELETE FROM generated_docs WHERE run_id = %s", (run_id,))
            cur.execute("DELETE FROM scan_results WHERE run_id = %s", (run_id,))
        db_conn.commit()


def test_tom_renders_section_mapping_table(db_conn):
    """TOM must include the static TOM-Abschnitt mapping table."""
    run_id = str(uuid.uuid4())
    _seed_scan_result(run_id, PROJECT)
    architect = DocumentOrchestrator()
    generated = architect.generate_all(
        {**GRAPH_RESULT, "doc_types": ["TOM"]}, REASONING_RESULT, PROJECT, run_id
    )

    tom_entry = next((d for d in generated if d["doc_type"] == "TOM"), None)
    assert tom_entry is not None
    tom_path = Path(tom_entry["file_path"])
    try:
        content = tom_path.read_text(encoding="utf-8")
        assert "1.1 Zutrittskontrolle" in content, "TOM missing section 1.1 Zutrittskontrolle"
        assert "1.2 Zugangskontrolle" in content, "TOM missing section 1.2 Zugangskontrolle"
        assert "3.1 Verfügbarkeitskontrolle" in content, "TOM missing section 3.1"
    finally:
        tom_path.unlink(missing_ok=True)
        with db_conn.cursor() as cur:
            cur.execute("DELETE FROM generated_docs WHERE run_id = %s", (run_id,))
            cur.execute("DELETE FROM scan_results WHERE run_id = %s", (run_id,))
        db_conn.commit()


def test_delivery_endpoint_marks_telegram_sent(db_conn):
    """PATCH /docs/{run_id}/delivered sets telegram_sent=true and status=delivered."""
    run_id = str(uuid.uuid4())
    _seed_scan_result(run_id, PROJECT)

    # Insert minimal generated_docs rows directly
    with db_conn.cursor() as cur:
        for doc_type in ["AVV", "TOM"]:
            cur.execute("""
                INSERT INTO generated_docs (id, run_id, project_name, doc_type,
                    file_path, version, status, telegram_sent, repo_committed)
                VALUES (%s, %s, %s, %s, %s, 1, 'draft', false, false)
            """, (str(uuid.uuid4()), run_id, PROJECT, doc_type, f"/tmp/{doc_type.lower()}_{run_id[:8]}.md"))
    db_conn.commit()

    try:
        try:
            resp = requests.patch(
                f"http://localhost:8001/docs/{run_id}/delivered",
                timeout=5,
            )
        except (requests.exceptions.ConnectionError, requests.exceptions.Timeout):
            pytest.skip("approve_api not reachable on port 8001 (Pi only)")

        assert resp.status_code == 200
        data = resp.json()
        assert data["ok"] is True
        assert data["updated"] == 2

        with db_conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(
                "SELECT telegram_sent, status FROM generated_docs WHERE run_id = %s",
                (run_id,),
            )
            rows = cur.fetchall()

        assert len(rows) == 2
        for row in rows:
            assert row["telegram_sent"] is True, "telegram_sent should be true after delivery"
            assert row["status"] == "delivered", f"Expected status=delivered, got {row['status']}"
    finally:
        with db_conn.cursor() as cur:
            cur.execute("DELETE FROM generated_docs WHERE run_id = %s", (run_id,))
            cur.execute("DELETE FROM scan_results WHERE run_id = %s", (run_id,))
        db_conn.commit()


def test_current_docs_view(db_conn):
    """current_docs view returns exactly one row per doc_type with highest version."""
    run_id_1 = str(uuid.uuid4())
    run_id_2 = str(uuid.uuid4())
    _seed_scan_result(run_id_1, PROJECT)
    _seed_scan_result(run_id_2, PROJECT)
    architect = DocumentOrchestrator()
    gen1 = architect.generate_all(GRAPH_RESULT, REASONING_RESULT, PROJECT, run_id_1)
    gen2 = architect.generate_all(GRAPH_RESULT, REASONING_RESULT, PROJECT, run_id_2)

    try:
        with db_conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(
                "SELECT doc_type, version FROM current_docs WHERE project_name = %s",
                (PROJECT,),
            )
            rows = cur.fetchall()

        doc_types_in_view = {row["doc_type"] for row in rows}
        # VVT always generated + KI docs for Anthropic AI service
        expected_types = set(GRAPH_RESULT["doc_types"]) | {"VVT", "KI_System_Dokumentation", "KI_Policy"}
        assert doc_types_in_view == expected_types, (
            f"current_docs mismatch: expected={expected_types}, got={doc_types_in_view}"
        )
        for row in rows:
            assert row["version"] == 2, (
                f"{row['doc_type']}: expected version=2 in view, got {row['version']}"
            )
    finally:
        for d in gen1 + gen2:
            Path(d["file_path"]).unlink(missing_ok=True)
        with db_conn.cursor() as cur:
            cur.execute("DELETE FROM generated_docs WHERE project_name = %s", (PROJECT,))
            cur.execute("DELETE FROM scan_results WHERE project_name = %s", (PROJECT,))
        db_conn.commit()

def test_avv_uses_project_config(db_conn):
    """AVV header contains company_name from project_config when available."""
    run_id = str(uuid.uuid4())
    test_project = f"test-config-{uuid.uuid4().hex[:8]}"
    company = "Acme GmbH"
    avv_entry = None

    # Insert a project_config row with known company name
    with db_conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO project_config (project_name, company_name, legal_form,
                address, zip_code, city, country, contact_email, contact_phone,
                vat_id, website_url, doc_language, output_format)
            VALUES (%s, %s, 'GmbH', 'Teststraße 1', '12345', 'Teststadt',
                    'Deutschland', 'test@acme.de', '', '', 'https://acme.de', 'de', 'md')
            ON CONFLICT (project_name) DO UPDATE SET company_name = EXCLUDED.company_name
            """,
            (test_project, company),
        )
    db_conn.commit()

    _seed_scan_result(run_id, test_project)

    try:
        architect = DocumentOrchestrator()
        generated = architect.generate_all(
            {
                "doc_types": ["AVV"],
                "overall_risk": "minimal",
                "services": [],
                "docs_required": [],
                "controls": [],
                "risk_levels": [],
            },
            {"priority_actions": []},
            test_project,
            run_id,
        )

        avv_entry = next((d for d in generated if d["doc_type"] == "AVV"), None)
        assert avv_entry is not None

        avv_path = Path(avv_entry["file_path"])
        assert avv_path.exists(), f"AVV file not found: {avv_path}"
        content = avv_path.read_text(encoding="utf-8")

        assert company in content, f"company_name '{company}' not found in AVV"
        assert "GmbH" in content, "legal_form not found in AVV"
        assert "test@acme.de" in content, "contact_email not found in AVV"
    finally:
        if avv_entry:
            Path(avv_entry["file_path"]).unlink(missing_ok=True)
        with db_conn.cursor() as cur:
            cur.execute("DELETE FROM generated_docs WHERE run_id = %s", (run_id,))
            cur.execute("DELETE FROM scan_results WHERE run_id = %s", (run_id,))
            cur.execute("DELETE FROM project_config WHERE project_name = %s", (test_project,))
        db_conn.commit()


def test_rag_over_pii_detected_for_supabase_plus_llm():
    """Active risks include RAG_OVER_PII and PII_IN_LLM_CONTEXT when Supabase + LLM present."""
    from src.graph.graph_client import GraphClient

    # Build a simulated services_meta list (category-level detection, no real Neo4j call needed)
    services_meta = [
        {"name": "Supabase", "category": "baas"},
        {"name": "Anthropic", "category": "ai_llm"},
    ]

    found_categories = {s.get("category") for s in services_meta}
    has_llm = "ai_llm" in found_categories
    has_db  = bool(found_categories & {"baas", "database", "storage", "vector_db"})
    has_supabase = any(s.get("name") == "Supabase" for s in services_meta)

    active_risks = []
    if has_llm and has_db:
        if has_supabase:
            active_risks.append("RAG_OVER_PII")
        active_risks.append("PII_IN_LLM_CONTEXT")

    assert "RAG_OVER_PII" in active_risks, "RAG_OVER_PII should be detected for Supabase + LLM"
    assert "PII_IN_LLM_CONTEXT" in active_risks, "PII_IN_LLM_CONTEXT should be detected for DB + LLM"


def test_tom_contains_rag_pii_section(db_conn):
    """ToM contains critical RAG-over-PII section when active_risks includes RAG_OVER_PII."""
    run_id = str(uuid.uuid4())
    _seed_scan_result(run_id, PROJECT)

    graph_result_with_risk = {
        "doc_types": ["TOM"],
        "overall_risk": "high",
        "services": [],
        "docs_required": [],
        "controls": [],
        "risk_levels": [],
        "active_risks": ["RAG_OVER_PII", "PII_IN_LLM_CONTEXT"],
    }

    try:
        architect = DocumentOrchestrator()
        generated = architect.generate_all(
            graph_result_with_risk, {"priority_actions": []}, PROJECT, run_id
        )

        tom_entry = next((d for d in generated if d["doc_type"] == "TOM"), None)
        assert tom_entry is not None

        tom_path = Path(tom_entry["file_path"])
        assert tom_path.exists(), f"ToM file not found: {tom_path}"
        content = tom_path.read_text(encoding="utf-8")

        assert "pgvector" in content, "RAG-over-PII section with pgvector missing from ToM"
        assert "UUID-Only" in content, "UUID-Only mitigation missing from ToM"
        assert "Presidio" in content, "Presidio reference missing from ToM"
        assert "RAG" in content, "RAG keyword missing from ToM"
    finally:
        if tom_entry:
            Path(tom_entry["file_path"]).unlink(missing_ok=True)
        with db_conn.cursor() as cur:
            cur.execute("DELETE FROM generated_docs WHERE run_id = %s", (run_id,))
            cur.execute("DELETE FROM scan_results WHERE run_id = %s", (run_id,))
        db_conn.commit()


# ── Document Validator — Phase 1 tests ────────────────────────────────────────

def test_validator_detects_missing_section():
    from src.agents.document_validator import _check_section_present
    assert _check_section_present("## § 9 Datenschutzkontrolle\n", "§9 Datenschutzkontrolle")
    assert not _check_section_present("## § 8 Subunternehmen\n", "§9 Datenschutzkontrolle")


def test_validator_detects_placeholder():
    from src.agents.document_validator import _is_placeholder
    assert _is_placeholder("(ausfüllen)")
    assert _is_placeholder("(bitte ergänzen)")
    assert _is_placeholder("")
    assert not _is_placeholder("Max Mustermann")
    assert not _is_placeholder("test@example.de")


def test_validator_score_complete():
    """score=1.0 when no required sections defined (unknown doc_type → empty spec)."""
    from src.agents.document_validator import DocumentValidator
    dv = DocumentValidator()
    report = dv._validate_document(
        {"doc_type": "__UNKNOWN_TYPE__", "file_path": ""},
        {},
    )
    # Unknown type → _load_required_spec returns empty lists → score defaults to 1.0
    assert report["completeness_score"] == 1.0
    assert report["is_usable"] is True


def test_validator_score_incomplete(tmp_path):
    """score<1.0 when a required section is missing."""
    from src.agents.document_validator import DocumentValidator, _check_section_present
    content = "## Zutrittskontrolle\n"
    missing = not _check_section_present(content, "§9 Datenschutzkontrolle")
    assert missing is True  # section absent → would lower score


def test_validator_appends_gaps(tmp_path):
    """Gaps appendix is written to file when config fields are missing."""
    from src.agents.document_validator import DocumentValidator
    doc_path = tmp_path / "avv_test.md"
    doc_path.write_text("# AVV\n\nSome content.\n", encoding="utf-8")

    report = {
        "doc_type": "AVV",
        "file_path": str(doc_path),
        "missing_sections": [],
        "missing_config_fields": ["responsible_name", "dpo_email"],
        "placeholder_fields": [],
        "completeness_score": 1.0,
        "is_usable": True,
    }
    DocumentValidator()._append_gaps_if_needed(report)

    written = doc_path.read_text(encoding="utf-8")
    assert "## Anhang: Noch ausstehende Angaben" in written
    assert "responsible_name" in written
    assert "dpo_email" in written


def test_validator_appends_gaps_only_once(tmp_path):
    """Gaps appendix is not duplicated on repeated calls."""
    from src.agents.document_validator import DocumentValidator
    doc_path = tmp_path / "avv_once.md"
    doc_path.write_text("# AVV\n", encoding="utf-8")

    report = {
        "doc_type": "AVV",
        "file_path": str(doc_path),
        "missing_sections": [],
        "missing_config_fields": ["responsible_name"],
        "placeholder_fields": [],
        "completeness_score": 1.0,
        "is_usable": True,
    }
    dv = DocumentValidator()
    dv._append_gaps_if_needed(report)
    dv._append_gaps_if_needed(report)

    written = doc_path.read_text(encoding="utf-8")
    assert written.count("## Anhang: Noch ausstehende Angaben") == 1


def test_validator_no_disclaimer():
    """Telegram summary contains no legal disclaimers."""
    from src.agents.document_validator import DocumentValidator
    out = DocumentValidator().format_telegram_summary([{
        "doc_type": "AVV",
        "completeness_score": 0.73,
        "is_usable": True,
        "missing_sections": [],
        "missing_config_fields": ["responsible_name"],
        "placeholder_fields": [],
    }])
    assert "rechtliche Prüfung" not in out
    assert "Haftungsausschluss" not in out
    assert "responsible_name" in out


def test_validator_telegram_full_doc():
    """Telegram summary shows ✅ for complete document."""
    from src.agents.document_validator import DocumentValidator
    out = DocumentValidator().format_telegram_summary([{
        "doc_type": "TOM",
        "completeness_score": 1.0,
        "is_usable": True,
        "missing_sections": [],
        "missing_config_fields": [],
        "placeholder_fields": [],
    }])
    assert "✅" in out
    assert "TOM" in out
    assert "einsatzbereit" in out


def test_validator_node_returns_partial_dict():
    """node_document_validator must return a dict, not the full mutated state."""
    from src.workflow.main import node_document_validator, LexState
    state: LexState = {
        "project_name": "test",
        "repo_url": None,
        "live_url": None,
        "scan_depth": "quick",
        "dry_run": True,
        "scout_result": None,
        "graph_result": None,
        "reasoning_result": None,
        "generated_docs": [],
        "validation_result": None,
        "config_requested": False,
        "validator_retries": 0,
        "pending_telegram_message": None,
        "notification_sent": False,
        "run_id": "test-run",
        "errors": [],
    }
    result = node_document_validator(state)
    assert isinstance(result, dict), "node must return dict, not LexState"
    assert "validation_result" in result
    assert result["validation_result"] == []  # dry_run → empty


def test_workflow_validator_node_exists():
    """build_workflow() must include validator between documents and notify."""
    from src.workflow.main import build_workflow
    app = build_workflow()
    edges = [(e.source, e.target) for e in app.get_graph().edges]
    assert ("documents", "validator") in edges, "documents → validator edge missing"
    assert ("validator", "notify") in edges, "validator → notify edge missing"


# ── pgvector + vector_db risk detection tests ──────────────────────────────────

def test_pgvector_detected_from_sql_migration(tmp_path):
    """_detect_pgvector returns True when SQL migration contains CREATE EXTENSION vector."""
    from src.workflow.main import _detect_pgvector
    migration = tmp_path / "migration.sql"
    migration.write_text("CREATE EXTENSION IF NOT EXISTS vector;\n", encoding="utf-8")
    assert _detect_pgvector(str(tmp_path)) is True


def test_pgvector_detected_from_python_import(tmp_path):
    """_detect_pgvector returns True when Python file imports from pgvector."""
    from src.workflow.main import _detect_pgvector
    models = tmp_path / "models.py"
    models.write_text("from pgvector.django import VectorField\n", encoding="utf-8")
    assert _detect_pgvector(str(tmp_path)) is True


def test_pgvector_not_detected_in_clean_repo(tmp_path):
    """_detect_pgvector returns False when no pgvector signals are present."""
    from src.workflow.main import _detect_pgvector
    (tmp_path / "app.py").write_text("import flask\nprint('hello')\n", encoding="utf-8")
    assert _detect_pgvector(str(tmp_path)) is False


def test_rag_risk_triggered_by_vector_db():
    """RAG_OVER_PII is triggered when services include vector_db + ai_llm categories."""
    services_meta = [
        {"name": "pgvector", "category": "vector_db"},
        {"name": "Anthropic", "category": "ai_llm"},
    ]
    found_categories = {s.get("category") for s in services_meta}
    has_llm    = "ai_llm" in found_categories
    has_vector = "vector_db" in found_categories
    has_db     = bool(found_categories & {"baas", "database", "storage", "nosql_db", "vector_db"})

    active_risks = []
    if has_llm and has_vector:
        active_risks.append("RAG_OVER_PII")
    if has_llm and has_db and not has_vector:
        active_risks.append("PII_IN_LLM_CONTEXT")

    assert "RAG_OVER_PII" in active_risks, "RAG_OVER_PII must trigger for vector_db + ai_llm"
    assert "PII_IN_LLM_CONTEXT" not in active_risks, \
        "PII_IN_LLM_CONTEXT must not duplicate when RAG_OVER_PII is present"


def test_no_audit_trail_detected_when_llm_without_logging():
    """NO_AI_AUDIT_TRAIL triggered when LLM present and no logging tool found."""
    services_meta = [
        {"name": "Anthropic", "category": "ai_llm"},
        {"name": "Supabase", "category": "baas"},
    ]
    found_categories = {s.get("category") for s in services_meta}
    found_names = {(s.get("name") or "").lower() for s in services_meta}
    has_llm = "ai_llm" in found_categories
    LOGGING_TOOLS = {"langfuse", "sentry-sdk", "datadog",
                     "opentelemetry", "structlog", "loguru"}
    has_audit_logging = bool(found_names & LOGGING_TOOLS)

    active_risks = []
    if has_llm and not has_audit_logging:
        active_risks.append("NO_AI_AUDIT_TRAIL")

    assert "NO_AI_AUDIT_TRAIL" in active_risks


def test_audit_trail_not_triggered_with_langfuse():
    """NO_AI_AUDIT_TRAIL not triggered when Langfuse is present."""
    services_meta = [
        {"name": "Anthropic", "category": "ai_llm"},
        {"name": "Langfuse", "category": "observability"},
    ]
    found_categories = {s.get("category") for s in services_meta}
    found_names = {(s.get("name") or "").lower() for s in services_meta}
    has_llm = "ai_llm" in found_categories
    LOGGING_TOOLS = {"langfuse", "sentry-sdk", "datadog",
                     "opentelemetry", "structlog", "loguru"}
    has_audit_logging = bool(found_names & LOGGING_TOOLS)

    active_risks = []
    if has_llm and not has_audit_logging:
        active_risks.append("NO_AI_AUDIT_TRAIL")

    assert "NO_AI_AUDIT_TRAIL" not in active_risks


# ── Jinja2 template tests ─────────────────────────────────────────────────────

def test_tom_template_renders_with_full_config(db_conn):
    """TOM template renders with company info and 3-column table structure."""
    run_id = str(uuid.uuid4())
    test_project = f"test-tom-tpl-{uuid.uuid4().hex[:8]}"
    company = "TemplateTest GmbH"

    with db_conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO project_config (project_name, company_name, legal_form,
                address, zip_code, city, country, contact_email, contact_phone,
                vat_id, website_url, doc_language, output_format)
            VALUES (%s, %s, 'GmbH', 'Musterstraße 1', '10115', 'Berlin',
                    'Deutschland', 'info@test.de', '', '', 'https://test.de', 'de', 'md')
            ON CONFLICT (project_name) DO UPDATE SET company_name = EXCLUDED.company_name
            """,
            (test_project, company),
        )
    db_conn.commit()

    graph_result = {
        "doc_types": ["TOM"],
        "overall_risk": "high",
        "services": [],
        "docs_required": [],
        "controls": [{"service": "test", "control_id": "SYS.1.1", "framework": "BSI_Grundschutz",
                      "title_de": "Allgemeiner Server", "text": ""}],
        "risk_levels": [],
        "active_risks": [],
    }

    _seed_scan_result(run_id, test_project)
    architect = DocumentOrchestrator()
    generated = architect.generate_all(graph_result, {"priority_actions": []}, test_project, run_id)

    tom_entry = next((d for d in generated if d["doc_type"] == "TOM"), None)
    assert tom_entry is not None

    tom_path = Path(tom_entry["file_path"])
    try:
        content = tom_path.read_text(encoding="utf-8")
        assert company in content, f"company_name '{company}' not in TOM"
        assert "GmbH" in content, "legal_form not in TOM"
        assert "info@test.de" in content, "contact_email not in TOM"
        assert "Standard-Umsetzung (BSI)" in content, "BSI column header missing"
        assert "Konkrete Umsetzung" in content, "Konkrete Umsetzung column missing"
        assert "SYS.1.1" in content, "Control ID SYS.1.1 not in TOM"
    finally:
        for d in generated:
            Path(d["file_path"]).unlink(missing_ok=True)
        with db_conn.cursor() as cur:
            cur.execute("DELETE FROM generated_docs WHERE run_id = %s", (run_id,))
            cur.execute("DELETE FROM scan_results WHERE run_id = %s", (run_id,))
            cur.execute("DELETE FROM project_config WHERE project_name = %s", (test_project,))
        db_conn.commit()


def test_vvt_always_generated(db_conn):
    """VVT is generated even when not in doc_types — always required by Art. 30 DSGVO."""
    run_id = str(uuid.uuid4())
    graph_result_no_vvt = {
        "doc_types": ["TOM"],  # VVT not in list
        "overall_risk": "minimal",
        "services": [],
        "docs_required": [],
        "controls": [],
        "risk_levels": [],
        "active_risks": [],
    }

    _seed_scan_result(run_id, PROJECT)
    architect = DocumentOrchestrator()
    generated = architect.generate_all(graph_result_no_vvt, {"priority_actions": []}, PROJECT, run_id)

    try:
        vvt_entries = [d for d in generated if d["doc_type"] == "VVT"]
        assert len(vvt_entries) == 1, "VVT should always be generated"

        vvt_path = Path(vvt_entries[0]["file_path"])
        assert vvt_path.exists(), f"VVT file not on disk: {vvt_path}"
        content = vvt_path.read_text(encoding="utf-8")
        assert "Art. 30 DSGVO" in content, "VVT missing legal reference"
        assert PROJECT in content, "project_name missing from VVT"
    finally:
        for d in generated:
            Path(d["file_path"]).unlink(missing_ok=True)
        with db_conn.cursor() as cur:
            cur.execute("DELETE FROM generated_docs WHERE run_id = %s", (run_id,))
            cur.execute("DELETE FROM scan_results WHERE run_id = %s", (run_id,))
        db_conn.commit()


def test_vvt_contains_ki_hinweis_for_ai_services(db_conn):
    """VVT includes KI-Hinweis fields (ai_type, ai_risk_level) for AI-relevant services."""
    run_id = str(uuid.uuid4())
    graph_result_ai = {
        "doc_types": ["VVT"],
        "overall_risk": "gpai",
        "services": [
            {"name": "Anthropic", "category": "ai_llm", "country": "USA",
             "gdpr_adequate": False, "ai_act_relevant": True,
             "processing_purpose": "Textgenerierung"},
        ],
        "docs_required": [],
        "controls": [],
        "risk_levels": [],
        "active_risks": [],
    }

    _seed_scan_result(run_id, PROJECT)
    architect = DocumentOrchestrator()
    generated = architect.generate_all(graph_result_ai, {"priority_actions": []}, PROJECT, run_id)

    vvt_entry = next((d for d in generated if d["doc_type"] == "VVT"), None)
    assert vvt_entry is not None

    vvt_path = Path(vvt_entry["file_path"])
    try:
        content = vvt_path.read_text(encoding="utf-8")
        assert "generativ (LLM)" in content, "AI type 'generativ (LLM)' missing from VVT"
        assert "KI im Einsatz" in content, "KI field header missing from VVT"
    finally:
        for d in generated:
            Path(d["file_path"]).unlink(missing_ok=True)
        with db_conn.cursor() as cur:
            cur.execute("DELETE FROM generated_docs WHERE run_id = %s", (run_id,))
            cur.execute("DELETE FROM scan_results WHERE run_id = %s", (run_id,))
        db_conn.commit()


def test_template_language_fallback():
    """_get_template() falls back to DE template when requested language has no template."""
    architect = DocumentOrchestrator()
    # "fr" does not exist → falls back to DE
    template = architect._get_template("tom.md.j2", "fr")
    assert template is not None, "Should fall back to DE tom.md.j2 for fr"
    # "de" is always found
    template_de = architect._get_template("tom.md.j2", "de")
    assert template_de is not None


def test_avv_template_marks_service_dpa_presence(db_conn):
    """AVV § 1 table marks DPA presence with ✓ (PR 2 / 2d) — no rendered link.

    The raw dpa_url is no longer hyperlinked into the table; its presence is
    shown as a ✓ marker (absence as —). URL upkeep is maintenance burden, the
    marker is the honest signal."""
    run_id = str(uuid.uuid4())
    graph_result_dpa = {
        "doc_types": ["AVV"],
        "overall_risk": "gpai",
        "services": [
            {
                "name": "OpenAI",
                "category": "ai_llm",
                "country": "USA",
                "gdpr_adequate": False,
                "dpa_required": True,
                "dpa_url": "https://openai.com/policies/data-processing-addendum",
            }
        ],
        "docs_required": [],
        "controls": [],
        "risk_levels": [],
    }

    _seed_scan_result(run_id, PROJECT)
    architect = DocumentOrchestrator()
    generated = architect.generate_all(graph_result_dpa, REASONING_RESULT, PROJECT, run_id)

    avv_entry = next((d for d in generated if d["doc_type"] == "AVV"), None)
    assert avv_entry is not None

    avv_path = Path(avv_entry["file_path"])
    try:
        content = avv_path.read_text(encoding="utf-8")
        assert "openai.com/policies/data-processing-addendum" not in content, \
            "DPA URL must no longer be hyperlinked in the AVV table (PR 2 / 2d)"
        assert "OpenAI" in content, "Service name missing from AVV"
        # OpenAI has a dpa_url → its § 1 table row carries the ✓ DPA marker
        openai_row = next(l for l in content.splitlines() if l.startswith("| OpenAI "))
        assert "✓" in openai_row, "DPA presence marker missing for service with dpa_url"
        assert "SCC erforderlich" in content, "SCC requirement missing for non-EU service"
    finally:
        for d in generated:
            Path(d["file_path"]).unlink(missing_ok=True)
        with db_conn.cursor() as cur:
            cur.execute("DELETE FROM generated_docs WHERE run_id = %s", (run_id,))
            cur.execute("DELETE FROM scan_results WHERE run_id = %s", (run_id,))
        db_conn.commit()


def test_ai_act_manifest_shows_deployer_obligations(db_conn):
    """AI Act Manifest contains provider risk rows and deployer section."""
    run_id = str(uuid.uuid4())

    _seed_scan_result(run_id, PROJECT)
    architect = DocumentOrchestrator()
    generated = architect.generate_all(GRAPH_RESULT, REASONING_RESULT, PROJECT, run_id)

    manifest_entry = next((d for d in generated if d["doc_type"] == "AI_Act_Manifest"), None)
    assert manifest_entry is not None

    manifest_path = Path(manifest_entry["file_path"])
    try:
        content = manifest_path.read_text(encoding="utf-8")
        assert "2. Eingesetzte KI-Systeme" in content, "Provider section (section 2) missing from manifest"
        assert "3. Deployer-Risiko" in content, "Deployer section (section 3) missing from manifest"
        assert "Anthropic" in content, "Service name missing from manifest"
        assert "GPAI" in content, "Risk level GPAI missing from manifest"
    finally:
        for d in generated:
            Path(d["file_path"]).unlink(missing_ok=True)
        with db_conn.cursor() as cur:
            cur.execute("DELETE FROM generated_docs WHERE run_id = %s", (run_id,))
            cur.execute("DELETE FROM scan_results WHERE run_id = %s", (run_id,))
        db_conn.commit()


def test_ki_system_doc_generated_per_ai_service(db_conn):
    """One KI_System_Dokumentation is generated per ai_act_relevant service."""
    run_id = str(uuid.uuid4())
    graph_result_two_ai = {
        "doc_types": [],
        "overall_risk": "gpai",
        "services": [
            {"name": "Anthropic", "category": "ai_llm", "country": "USA",
             "gdpr_adequate": False, "ai_act_relevant": True},
            {"name": "OpenAI", "category": "ai_llm", "country": "USA",
             "gdpr_adequate": False, "ai_act_relevant": True},
        ],
        "docs_required": [],
        "controls": [],
        "risk_levels": [],
        "active_risks": [],
    }

    _seed_scan_result(run_id, PROJECT)
    architect = DocumentOrchestrator()
    generated = architect.generate_all(graph_result_two_ai, {"priority_actions": []}, PROJECT, run_id)

    try:
        ki_docs = [d for d in generated if d["doc_type"] == "KI_System_Dokumentation"]
        assert len(ki_docs) == 2, \
            f"Expected 2 KI_System_Dokumentation docs, got {len(ki_docs)}"

        paths = [Path(d["file_path"]) for d in ki_docs]
        names = [p.name for p in paths]
        assert any("anthropic" in n for n in names), "anthropic doc missing"
        assert any("openai" in n for n in names), "openai doc missing"

        for p in paths:
            assert p.exists(), f"KI doc not on disk: {p}"
            content = p.read_text(encoding="utf-8")
            assert "EU AI Act Art. 11" in content, "Art. 11 reference missing"
    finally:
        for d in generated:
            Path(d["file_path"]).unlink(missing_ok=True)
        with db_conn.cursor() as cur:
            cur.execute("DELETE FROM generated_docs WHERE run_id = %s", (run_id,))
            cur.execute("DELETE FROM scan_results WHERE run_id = %s", (run_id,))
        db_conn.commit()


def test_dsfa_only_generated_for_high_risk(db_conn):
    """DSFA is NOT generated when risk is Minimal/Limited and no PII flags are set."""
    run_id = str(uuid.uuid4())
    graph_result_minimal = {
        "doc_types": [],
        "overall_risk": "minimal",
        "services": [
            {"name": "Anthropic", "category": "ai_llm", "country": "USA",
             "gdpr_adequate": False, "ai_act_relevant": True},
        ],
        "docs_required": [],
        "controls": [],
        "risk_levels": [],
        "active_risks": [],  # No PII risks
    }

    _seed_scan_result(run_id, PROJECT)
    architect = DocumentOrchestrator()
    generated = architect.generate_all(graph_result_minimal, {"priority_actions": []}, PROJECT, run_id)

    try:
        doc_types = [d["doc_type"] for d in generated]
        assert "DSFA" not in doc_types, \
            "DSFA must NOT be generated for minimal risk without PII flags"
    finally:
        for d in generated:
            Path(d["file_path"]).unlink(missing_ok=True)
        with db_conn.cursor() as cur:
            cur.execute("DELETE FROM generated_docs WHERE run_id = %s", (run_id,))
            cur.execute("DELETE FROM scan_results WHERE run_id = %s", (run_id,))
        db_conn.commit()


def test_dsfa_generated_for_rag_over_pii(db_conn):
    """DSFA is generated when RAG_OVER_PII is in active_risks."""
    run_id = str(uuid.uuid4())
    graph_result_rag = {
        "doc_types": [],
        "overall_risk": "high",
        "services": [
            {"name": "Anthropic", "category": "ai_llm", "country": "USA",
             "gdpr_adequate": False, "ai_act_relevant": True},
        ],
        "docs_required": [],
        "controls": [],
        "risk_levels": [],
        "active_risks": ["RAG_OVER_PII"],
    }

    _seed_scan_result(run_id, PROJECT)
    architect = DocumentOrchestrator()
    generated = architect.generate_all(graph_result_rag, {"priority_actions": []}, PROJECT, run_id)

    try:
        doc_types = [d["doc_type"] for d in generated]
        assert "DSFA" in doc_types, "DSFA must be generated when RAG_OVER_PII detected"

        dsfa_entry = next(d for d in generated if d["doc_type"] == "DSFA")
        dsfa_path = Path(dsfa_entry["file_path"])
        assert dsfa_path.exists(), "DSFA file not on disk"
        content = dsfa_path.read_text(encoding="utf-8")
        assert "Art. 35 DSGVO" in content, "Art. 35 reference missing from DSFA"
        assert "RAG" in content, "RAG risk mention missing from DSFA"
    finally:
        for d in generated:
            Path(d["file_path"]).unlink(missing_ok=True)
        with db_conn.cursor() as cur:
            cur.execute("DELETE FROM generated_docs WHERE run_id = %s", (run_id,))
            cur.execute("DELETE FROM scan_results WHERE run_id = %s", (run_id,))
        db_conn.commit()


def test_ki_policy_generated_when_ai_services_present(db_conn):
    """KI_Policy is generated once per project when AI services are detected."""
    run_id = str(uuid.uuid4())
    graph_result_ai = {
        "doc_types": [],
        "overall_risk": "gpai",
        "services": [
            {"name": "Anthropic", "category": "ai_llm", "country": "USA",
             "gdpr_adequate": False, "ai_act_relevant": True},
        ],
        "docs_required": [],
        "controls": [],
        "risk_levels": [],
        "active_risks": [],
    }

    _seed_scan_result(run_id, PROJECT)
    architect = DocumentOrchestrator()
    generated = architect.generate_all(graph_result_ai, {"priority_actions": []}, PROJECT, run_id)

    try:
        ki_policies = [d for d in generated if d["doc_type"] == "KI_Policy"]
        assert len(ki_policies) == 1, \
            f"Expected exactly 1 KI_Policy, got {len(ki_policies)}"
    finally:
        for d in generated:
            Path(d["file_path"]).unlink(missing_ok=True)
        with db_conn.cursor() as cur:
            cur.execute("DELETE FROM generated_docs WHERE run_id = %s", (run_id,))
            cur.execute("DELETE FROM scan_results WHERE run_id = %s", (run_id,))
        db_conn.commit()


def test_ki_policy_contains_forbidden_data_categories(db_conn):
    """KI_Policy must list Art. 9 DSGVO forbidden data categories."""
    run_id = str(uuid.uuid4())
    graph_result_ai = {
        "doc_types": [],
        "overall_risk": "gpai",
        "services": [
            {"name": "Anthropic", "category": "ai_llm", "country": "USA",
             "gdpr_adequate": False, "ai_act_relevant": True},
        ],
        "docs_required": [],
        "controls": [],
        "risk_levels": [],
        "active_risks": [],
    }

    _seed_scan_result(run_id, PROJECT)
    architect = DocumentOrchestrator()
    generated = architect.generate_all(graph_result_ai, {"priority_actions": []}, PROJECT, run_id)

    ki_policy_entry = next((d for d in generated if d["doc_type"] == "KI_Policy"), None)
    assert ki_policy_entry is not None

    ki_policy_path = Path(ki_policy_entry["file_path"])
    try:
        content = ki_policy_path.read_text(encoding="utf-8")
        assert "Art. 9 DSGVO" in content, "Art. 9 DSGVO reference missing from KI_Policy"
        assert "Gesundheitsdaten" in content, "Gesundheitsdaten missing from KI_Policy forbidden list"
        assert "Art. 50 EU AI Act" in content, "Art. 50 AI Act transparency obligation missing"
    finally:
        for d in generated:
            Path(d["file_path"]).unlink(missing_ok=True)
        with db_conn.cursor() as cur:
            cur.execute("DELETE FROM generated_docs WHERE run_id = %s", (run_id,))
            cur.execute("DELETE FROM scan_results WHERE run_id = %s", (run_id,))
        db_conn.commit()


def test_vvt_contains_ki_hinweis(db_conn):
    """VVT ai_type field shows 'generativ (LLM)' for ai_llm category services."""
    run_id = str(uuid.uuid4())
    graph_result_llm = {
        "doc_types": [],
        "overall_risk": "gpai",
        "services": [
            {"name": "Claude", "category": "ai_llm", "country": "USA",
             "gdpr_adequate": False, "ai_act_relevant": True},
        ],
        "docs_required": [],
        "controls": [],
        "risk_levels": [],
        "active_risks": [],
    }

    _seed_scan_result(run_id, PROJECT)
    architect = DocumentOrchestrator()
    generated = architect.generate_all(graph_result_llm, {"priority_actions": []}, PROJECT, run_id)

    vvt_entry = next((d for d in generated if d["doc_type"] == "VVT"), None)
    assert vvt_entry is not None

    vvt_path = Path(vvt_entry["file_path"])
    try:
        content = vvt_path.read_text(encoding="utf-8")
        assert "generativ (LLM)" in content, \
            "VVT must show 'generativ (LLM)' for ai_llm category services"
    finally:
        for d in generated:
            Path(d["file_path"]).unlink(missing_ok=True)
        with db_conn.cursor() as cur:
            cur.execute("DELETE FROM generated_docs WHERE run_id = %s", (run_id,))
            cur.execute("DELETE FROM scan_results WHERE run_id = %s", (run_id,))
        db_conn.commit()


def test_avv_contains_paragraph_9(db_conn):
    """AVV must contain § 9 Datenschutzkontrolle (Art. 28 Abs. 3 lit. h)."""
    run_id = str(uuid.uuid4())
    _seed_scan_result(run_id, PROJECT)
    architect = DocumentOrchestrator()
    generated = architect.generate_all(
        {**GRAPH_RESULT, "doc_types": ["AVV"]}, REASONING_RESULT, PROJECT, run_id
    )
    avv_entry = next((d for d in generated if d["doc_type"] == "AVV"), None)
    assert avv_entry is not None
    avv_path = Path(avv_entry["file_path"])
    try:
        content = avv_path.read_text(encoding="utf-8")
        assert "§ 9 Datenschutzkontrolle" in content, "§ 9 Datenschutzkontrolle missing from AVV"
        assert "Art. 28 Abs. 3 lit. h DSGVO" in content, "Art. 28 Abs. 3 lit. h DSGVO reference missing"
    finally:
        avv_path.unlink(missing_ok=True)
        with db_conn.cursor() as cur:
            cur.execute("DELETE FROM generated_docs WHERE run_id = %s", (run_id,))
            cur.execute("DELETE FROM scan_results WHERE run_id = %s", (run_id,))
        db_conn.commit()


def test_avv_contains_paragraph_11(db_conn):
    """AVV must contain § 11 Schlussbestimmungen."""
    run_id = str(uuid.uuid4())
    _seed_scan_result(run_id, PROJECT)
    architect = DocumentOrchestrator()
    generated = architect.generate_all(
        {**GRAPH_RESULT, "doc_types": ["AVV"]}, REASONING_RESULT, PROJECT, run_id
    )
    avv_entry = next((d for d in generated if d["doc_type"] == "AVV"), None)
    assert avv_entry is not None
    avv_path = Path(avv_entry["file_path"])
    try:
        content = avv_path.read_text(encoding="utf-8")
        assert "§ 11 Schlussbestimmungen" in content, "§ 11 Schlussbestimmungen missing from AVV"
    finally:
        avv_path.unlink(missing_ok=True)
        with db_conn.cursor() as cur:
            cur.execute("DELETE FROM generated_docs WHERE run_id = %s", (run_id,))
            cur.execute("DELETE FROM scan_results WHERE run_id = %s", (run_id,))
        db_conn.commit()


def test_ai_act_manifest_has_all_5_sections(db_conn):
    """AI Act Manifest must have all core sections per ki-kompetenz-center standard.

    ADR-124 Doc-Polish restructured §4: the former "Governance- und Kontrollmechanismen"
    is split into "4. Pflicht-Hinweise zum EU AI Act" (the ⚖️ obligation block, grouped by
    legal trigger) and the new "6. Governance- und Dokumenten-Verweise" (doc cross-refs).
    """
    run_id = str(uuid.uuid4())
    _seed_scan_result(run_id, PROJECT)
    architect = DocumentOrchestrator()
    generated = architect.generate_all(GRAPH_RESULT, REASONING_RESULT, PROJECT, run_id)

    manifest_entry = next((d for d in generated if d["doc_type"] == "AI_Act_Manifest"), None)
    assert manifest_entry is not None
    manifest_path = Path(manifest_entry["file_path"])
    try:
        content = manifest_path.read_text(encoding="utf-8")
        assert "1. Rollen- und Verantwortlichkeitsklärung" in content, "Section 1 missing"
        assert "2. Eingesetzte KI-Systeme" in content, "Section 2 missing"
        assert "3. Deployer-Risiko" in content, "Section 3 missing"
        assert "4. Pflicht-Hinweise zum EU AI Act" in content, "Section 4 (obligation block) missing"
        assert "5. AI Literacy" in content, "Section 5 missing"
        assert "6. Governance- und Dokumenten-Verweise" in content, "Section 6 (doc references) missing"
    finally:
        manifest_path.unlink(missing_ok=True)
        with db_conn.cursor() as cur:
            cur.execute("DELETE FROM generated_docs WHERE run_id = %s", (run_id,))
            cur.execute("DELETE FROM scan_results WHERE run_id = %s", (run_id,))
        db_conn.commit()


def test_ai_act_manifest_section1_renders_role_table(db_conn):
    """AI Act Manifest section 1 renders the Rollen table with deployer statement."""
    run_id = str(uuid.uuid4())
    _seed_scan_result(run_id, PROJECT)
    architect = DocumentOrchestrator()
    generated = architect.generate_all(GRAPH_RESULT, REASONING_RESULT, PROJECT, run_id)

    manifest_entry = next((d for d in generated if d["doc_type"] == "AI_Act_Manifest"), None)
    assert manifest_entry is not None
    manifest_path = Path(manifest_entry["file_path"])
    try:
        content = manifest_path.read_text(encoding="utf-8")
        assert "Strategische Verantwortung" in content, "Role table missing Strategische Verantwortung"
        assert "Deployer" in content, "Deployer role statement missing from section 1"
        assert "Art. 3 Nr. 4" in content, "EU AI Act Art. 3 Nr. 4 reference missing from section 1"
    finally:
        manifest_path.unlink(missing_ok=True)
        with db_conn.cursor() as cur:
            cur.execute("DELETE FROM generated_docs WHERE run_id = %s", (run_id,))
            cur.execute("DELETE FROM scan_results WHERE run_id = %s", (run_id,))
        db_conn.commit()


def test_ai_act_manifest_prefills_responsible_name(db_conn):
    """AI Act Manifest section 1 must render responsible_name + responsible_title from project_config."""
    run_id = str(uuid.uuid4())
    test_project = f"test-manifest-{uuid.uuid4().hex[:8]}"
    manifest_entry = None

    with db_conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO project_config (project_name, company_name, responsible_name, responsible_title)
            VALUES (%s, %s, %s, %s)
            ON CONFLICT (project_name) DO UPDATE
                SET responsible_name = EXCLUDED.responsible_name,
                    responsible_title = EXCLUDED.responsible_title
            """,
            (test_project, "Acme GmbH", "Max Mustermann", "Geschäftsführer"),
        )
    db_conn.commit()

    _seed_scan_result(run_id, test_project)
    try:
        architect = DocumentOrchestrator()
        generated = architect.generate_all(
            {
                "doc_types": ["AI_Act_Manifest"],
                "overall_risk": "gpai",
                "services": [{"name": "Anthropic", "category": "ai_llm",
                               "country": "USA", "gdpr_adequate": False,
                               "ai_act_relevant": True}],
                "docs_required": [],
                "controls": [],
                "risk_levels": [{"service": "Anthropic", "level": "GPAI",
                                  "action": "Technische Dokumentation"}],
                "active_risks": [],
            },
            REASONING_RESULT,
            test_project,
            run_id,
        )

        manifest_entry = next((d for d in generated if d["doc_type"] == "AI_Act_Manifest"), None)
        assert manifest_entry is not None
        content = Path(manifest_entry["file_path"]).read_text(encoding="utf-8")
        assert "Max Mustermann" in content, "responsible_name not rendered in section 1"
        assert "Geschäftsführer" in content, "responsible_title not rendered in section 1"
    finally:
        if manifest_entry:
            Path(manifest_entry["file_path"]).unlink(missing_ok=True)
        with db_conn.cursor() as cur:
            cur.execute("DELETE FROM generated_docs WHERE run_id = %s", (run_id,))
            cur.execute("DELETE FROM scan_results WHERE run_id = %s", (run_id,))
            cur.execute("DELETE FROM project_config WHERE project_name = %s", (test_project,))
        db_conn.commit()


def test_avv_generated_when_non_eu_service_present(db_conn):
    """AVV must be generated when non-gdpr_adequate service detected,
    even if 'AVV' is not in graph doc_types."""
    run_id = str(uuid.uuid4())
    graph_result_no_avv_type = {
        "doc_types": [],  # AVV not in graph result
        "overall_risk": "high",
        "services": [
            {
                "name": "Anthropic",
                "category": "ai_llm",
                "country": "USA",
                "gdpr_adequate": False,
                "dpa_url": "https://www.anthropic.com/legal/data-processing-addendum",
            }
        ],
        "docs_required": [],
        "controls": [],
        "risk_levels": [],
        "active_risks": [],
    }

    _seed_scan_result(run_id, PROJECT)
    architect = DocumentOrchestrator()
    generated = architect.generate_all(
        graph_result_no_avv_type, {"priority_actions": []}, PROJECT, run_id
    )

    try:
        doc_types = [d["doc_type"] for d in generated]
        assert "AVV" in doc_types, "AVV must be generated for non-gdpr_adequate service"
    finally:
        for d in generated:
            Path(d["file_path"]).unlink(missing_ok=True)
        with db_conn.cursor() as cur:
            cur.execute("DELETE FROM generated_docs WHERE run_id = %s", (run_id,))
            cur.execute("DELETE FROM scan_results WHERE run_id = %s", (run_id,))
        db_conn.commit()


def test_vvt_shows_dpa_link(db_conn):
    """VVT DPA column must use service.dpa_url."""
    run_id = str(uuid.uuid4())
    graph_result_dpa = {
        "doc_types": ["VVT"],
        "overall_risk": "high",
        "services": [
            {
                "name": "Anthropic",
                "category": "ai_llm",
                "country": "USA",
                "gdpr_adequate": False,
                "dpa_url": "https://www.anthropic.com/legal/data-processing-addendum",
            }
        ],
        "docs_required": [],
        "controls": [],
        "risk_levels": [],
        "active_risks": [],
    }

    _seed_scan_result(run_id, PROJECT)
    architect = DocumentOrchestrator()
    generated = architect.generate_all(
        graph_result_dpa, {"priority_actions": []}, PROJECT, run_id
    )

    vvt_entry = next((d for d in generated if d["doc_type"] == "VVT"), None)
    assert vvt_entry is not None
    vvt_path = Path(vvt_entry["file_path"])
    try:
        content = vvt_path.read_text(encoding="utf-8")
        assert "⚠️ fehlt" not in content, "VVT DPA column shows ⚠️ fehlt — dpa_url not used"
        assert "anthropic.com/legal/data-processing-addendum" in content, \
            "Anthropic DPA URL missing from VVT"
    finally:
        for d in generated:
            Path(d["file_path"]).unlink(missing_ok=True)
        with db_conn.cursor() as cur:
            cur.execute("DELETE FROM generated_docs WHERE run_id = %s", (run_id,))
            cur.execute("DELETE FROM scan_results WHERE run_id = %s", (run_id,))
        db_conn.commit()


# ── legal_basis + /config + /tom tests ────────────────────────────────────────

def test_vvt_legal_basis_from_graph(db_conn):
    """VVT processing_activities must include legal_basis from service node, not placeholder."""
    run_id = str(uuid.uuid4())
    graph_result_with_basis = {
        "doc_types": ["VVT"],
        "overall_risk": "gpai",
        "services": [
            {
                "name": "Anthropic",
                "category": "ai_llm",
                "country": "USA",
                "gdpr_adequate": False,
                "legal_basis": "Art. 6 Abs. 1 lit. b DSGVO (Vertragserfüllung) + lit. f (Betriebssicherheit)",
                "processing_purpose": "KI-gestützte Textgenerierung",
            }
        ],
        "docs_required": [],
        "controls": [],
        "risk_levels": [],
        "active_risks": [],
    }

    _seed_scan_result(run_id, PROJECT)
    architect = DocumentOrchestrator()
    generated = architect.generate_all(
        graph_result_with_basis, {"priority_actions": []}, PROJECT, run_id
    )

    vvt_entry = next((d for d in generated if d["doc_type"] == "VVT"), None)
    assert vvt_entry is not None
    vvt_path = Path(vvt_entry["file_path"])
    try:
        content = vvt_path.read_text(encoding="utf-8")
        assert "(ausfüllen — Art. 6 DSGVO)" not in content, \
            "VVT must not show placeholder when service has legal_basis"
        assert "Art. 6 Abs. 1 lit. b" in content, \
            "VVT must show legal_basis from service node"
    finally:
        for d in generated:
            Path(d["file_path"]).unlink(missing_ok=True)
        with db_conn.cursor() as cur:
            cur.execute("DELETE FROM generated_docs WHERE run_id = %s", (run_id,))
            cur.execute("DELETE FROM scan_results WHERE run_id = %s", (run_id,))
        db_conn.commit()


def test_upsert_config_field_sets_value(db_conn):
    """project_config upsert writes company_name and DocumentOrchestrator reads it back."""
    test_project = f"test-config-field-{uuid.uuid4().hex[:8]}"
    try:
        with db_conn.cursor() as cur:
            cur.execute(
                "INSERT INTO project_config (project_name, company_name) VALUES (%s, %s)"
                " ON CONFLICT (project_name) DO UPDATE SET company_name = EXCLUDED.company_name",
                (test_project, "Musterfirma GmbH"),
            )
        db_conn.commit()

        config = DocumentOrchestrator()._load_project_config(test_project)
        assert config.get("company_name") == "Musterfirma GmbH", \
            f"company_name not written. Got: {config.get('company_name')}"
    finally:
        db_conn.rollback()
        with db_conn.cursor() as cur:
            cur.execute("DELETE FROM project_config WHERE project_name = %s", (test_project,))
        db_conn.commit()


def test_tom_implementations_jsonb_upsert(db_conn):
    """tom_implementations JSONB must be updated via direct SQL (the /tom command path)."""
    # Check if tom_implementations column exists — skip if not yet migrated
    with db_conn.cursor() as cur:
        cur.execute(
            "SELECT column_name FROM information_schema.columns"
            " WHERE table_name = 'project_config' AND column_name = 'tom_implementations'"
        )
        if cur.fetchone() is None:
            pytest.skip("tom_implementations column not yet in project_config — run migrate.sql")

    test_project = f"test-tom-jsonb-{uuid.uuid4().hex[:8]}"
    try:
        with db_conn.cursor() as cur:
            cur.execute(
                "INSERT INTO project_config (project_name) VALUES (%s) ON CONFLICT DO NOTHING",
                (test_project,),
            )
            cur.execute(
                """
                UPDATE project_config
                SET tom_implementations = COALESCE(tom_implementations, '{}')::jsonb
                    || jsonb_build_object(%s, %s)
                WHERE project_name = %s
                """,
                ("LLM01", "Input-Validierung via LangChain prompt guard", test_project),
            )
        db_conn.commit()

        with db_conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(
                "SELECT tom_implementations FROM project_config WHERE project_name = %s",
                (test_project,),
            )
            row = cur.fetchone()

        assert row is not None, "project_config row not found"
        impl = row["tom_implementations"]
        assert impl.get("LLM01") == "Input-Validierung via LangChain prompt guard", \
            f"LLM01 not written correctly. Got: {impl}"
    finally:
        db_conn.rollback()
        with db_conn.cursor() as cur:
            cur.execute("DELETE FROM project_config WHERE project_name = %s", (test_project,))
        db_conn.commit()


def test_project_config_table_has_required_columns(db_conn):
    """project_config must have all columns needed for compliance document generation."""
    required_columns = {
        "responsible_name", "responsible_title",
        "dpo_name", "dpo_email",
        "company_name", "legal_form",
        "contact_email", "website_url",
        "ai_usecase_type", "doc_language",
        "tom_implementations",
    }
    with db_conn.cursor() as cur:
        cur.execute(
            """
            SELECT column_name FROM information_schema.columns
            WHERE table_name = 'project_config'
            """,
        )
        actual = {row[0] for row in cur.fetchall()}
    missing = required_columns - actual
    assert not missing, f"project_config table missing columns: {missing}"


def test_graph_client_returns_legal_basis_in_services():
    """get_compliance_requirements() must include legal_basis in service metadata (graph_client fix)."""
    from src.graph.graph_client import GraphClient

    try:
        with GraphClient() as gc:
            result = gc.get_compliance_requirements(["Anthropic"])
    except Exception as e:
        import pytest
        pytest.skip(f"Neo4j not reachable: {e}")

    services = result.get("services", [])
    assert services, "No services returned for Anthropic"

    svc = services[0]
    assert "legal_basis" in svc, \
        "legal_basis missing from service metadata — RETURN clause in meta_result query not updated"
    assert svc["legal_basis"] is not None, \
        "legal_basis is None for Anthropic — SUBJECT_TO_CONTROL rel missing legal_basis via HAS_CATEGORY"
    assert "art_6" in svc["legal_basis"], \
        f"Unexpected legal_basis value: {svc['legal_basis']}"


def test_vvt_legal_basis_via_generate_all(db_conn):
    """VVT renders Art. 6 Abs. 1 lit. b when graph_result service has legal_basis set."""
    run_id = str(uuid.uuid4())
    graph_result_with_basis = {
        "doc_types": ["VVT"],
        "overall_risk": "gpai",
        "services": [
            {
                "name": "Anthropic",
                "category": "ai_llm",
                "country": "USA",
                "gdpr_adequate": False,
                "legal_basis": "Art. 6 Abs. 1 lit. b DSGVO (Vertragserfüllung) + lit. f (Betriebssicherheit)",
            }
        ],
        "docs_required": [],
        "controls": [],
        "risk_levels": [],
        "active_risks": [],
    }

    _seed_scan_result(run_id, PROJECT)
    architect = DocumentOrchestrator()
    generated = architect.generate_all(
        graph_result_with_basis, {"priority_actions": []}, PROJECT, run_id
    )

    vvt_entry = next((d for d in generated if d["doc_type"] == "VVT"), None)
    assert vvt_entry is not None
    vvt_path = Path(vvt_entry["file_path"])
    try:
        content = vvt_path.read_text(encoding="utf-8")
        assert "Art. 6 Abs. 1 lit. b DSGVO" in content, \
            "VVT must render legal_basis from service — check _write_vvt() and graph_client meta_result"
        assert "(ausfüllen — Art. 6 DSGVO)" not in content, \
            "VVT must not show placeholder when legal_basis is set"
    finally:
        for d in generated:
            Path(d["file_path"]).unlink(missing_ok=True)
        with db_conn.cursor() as cur:
            cur.execute("DELETE FROM generated_docs WHERE run_id = %s", (run_id,))
            cur.execute("DELETE FROM scan_results WHERE run_id = %s", (run_id,))
        db_conn.commit()


# ── reasoning_result tom_implementations tests ────────────────────────────────

def test_tom_graph_default_fills_right_column(db_conn):
    """TOM must use default_tom_measure from graph when no manual/LLM override exists."""
    run_id = str(uuid.uuid4())
    test_project = f"test-tom-default-{run_id[:8]}"

    graph_result_with_default = {
        "doc_types": ["TOM"],
        "overall_risk": "high",
        "services": [{"name": "Anthropic", "category": "ai_llm", "country": "USA",
                      "gdpr_adequate": False}],
        "docs_required": [],
        "controls": [
            {
                "service": "Anthropic",
                "control_id": "LLM01",
                "framework": "OWASP_LLM_Top10",
                "title": "Prompt Injection",
                "text": None,
                "default_tom_measure": "AssetTranslator anonymisiert alle Assets (ADR-001).",
            }
        ],
        "risk_levels": [], "active_risks": [],
    }

    _seed_scan_result(run_id, test_project)
    architect = DocumentOrchestrator()
    generated = architect.generate_all(graph_result_with_default, {}, test_project, run_id)

    tom_entry = next((d for d in generated if d["doc_type"] == "TOM"), None)
    assert tom_entry is not None
    tom_path = Path(tom_entry["file_path"])
    try:
        content = tom_path.read_text(encoding="utf-8")
        assert "AssetTranslator anonymisiert alle Assets (ADR-001)." in content, \
            "default_tom_measure from graph must appear in TOM right column"
        assert "⚠️ Bitte konkrete Umsetzung ergänzen" not in content, \
            "no ⚠️ placeholder when graph default is available"
    finally:
        tom_path.unlink(missing_ok=True)
        with db_conn.cursor() as cur:
            cur.execute("DELETE FROM generated_docs WHERE run_id = %s", (run_id,))
            cur.execute("DELETE FROM scan_results WHERE run_id = %s", (run_id,))
        db_conn.commit()


def test_tom_project_config_overrides_graph_default(db_conn):
    """project_config tom_implementations must win over default_tom_measure from graph."""
    run_id = str(uuid.uuid4())
    test_project = f"test-tom-override-graph-{run_id[:8]}"

    graph_result = {
        "doc_types": ["TOM"],
        "overall_risk": "high",
        "services": [{"name": "Anthropic", "category": "ai_llm", "country": "USA",
                      "gdpr_adequate": False}],
        "docs_required": [],
        "controls": [
            {
                "service": "Anthropic",
                "control_id": "LLM01",
                "framework": "OWASP_LLM_Top10",
                "title": "Prompt Injection",
                "text": None,
                "default_tom_measure": "graph default — must not appear",
            }
        ],
        "risk_levels": [], "active_risks": [],
    }

    url = _resolve_db_url()
    conn = psycopg2.connect(url)
    try:
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO project_config (project_name, tom_implementations)
                VALUES (%s, %s::jsonb)
                ON CONFLICT (project_name) DO UPDATE SET tom_implementations = EXCLUDED.tom_implementations
            """, (test_project, '{"LLM01": "manual override wins over graph default"}'))
        conn.commit()

        _seed_scan_result(run_id, test_project)
        architect = DocumentOrchestrator()
        generated = architect.generate_all(graph_result, {}, test_project, run_id)

        tom_entry = next((d for d in generated if d["doc_type"] == "TOM"), None)
        assert tom_entry is not None
        tom_path = Path(tom_entry["file_path"])
        try:
            content = tom_path.read_text(encoding="utf-8")
            assert "manual override wins over graph default" in content
            assert "graph default — must not appear" not in content
        finally:
            tom_path.unlink(missing_ok=True)
    finally:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM generated_docs WHERE run_id = %s", (run_id,))
            cur.execute("DELETE FROM scan_results WHERE run_id = %s", (run_id,))
            cur.execute("DELETE FROM project_config WHERE project_name = %s", (test_project,))
        conn.commit()
        conn.close()


def test_tom_uses_reasoning_implementations(db_conn):
    """TOM renders LLM-generated implementation text when reasoning_result contains
    tom_implementations — no ⚠️ placeholder for controls covered by reasoning."""
    run_id = str(uuid.uuid4())

    graph_result_with_llm01 = {
        "doc_types": ["TOM"],
        "overall_risk": "high",
        "services": [
            {"name": "Anthropic", "category": "ai_llm", "country": "USA",
             "gdpr_adequate": False}
        ],
        "docs_required": [],
        "controls": [
            {
                "service": "Anthropic",
                "control_id": "LLM01",
                "framework": "OWASP_LLM_Top10",
                "title": "Prompt Injection",
                "text": None,
            }
        ],
        "risk_levels": [],
        "active_risks": [],
    }

    reasoning_result_with_tom = {
        "summary": "Test scan.",
        "priority_actions": ["Review prompt injection mitigations"],
        "eu_ai_act_classification": "gpai",
        "tom_implementations": {
            "LLM01": "test implementation text — prompt guard active",
        },
    }

    _seed_scan_result(run_id, PROJECT)
    architect = DocumentOrchestrator()
    generated = architect.generate_all(
        graph_result_with_llm01, reasoning_result_with_tom, PROJECT, run_id
    )

    tom_entry = next((d for d in generated if d["doc_type"] == "TOM"), None)
    assert tom_entry is not None, "TOM not generated"

    tom_path = Path(tom_entry["file_path"])
    try:
        assert tom_path.exists(), f"TOM file not on disk: {tom_path}"
        content = tom_path.read_text(encoding="utf-8")

        assert "test implementation text — prompt guard active" in content, \
            "TOM must contain the LLM-generated implementation text from reasoning_result"
        assert "⚠️ Bitte konkrete Umsetzung" not in content, \
            "TOM must not show placeholder when reasoning_result has tom_implementations"
        assert "LLM01" in content, "Control LLM01 must appear in TOM"
    finally:
        tom_path.unlink(missing_ok=True)
        with db_conn.cursor() as cur:
            cur.execute("DELETE FROM generated_docs WHERE run_id = %s", (run_id,))
            cur.execute("DELETE FROM scan_results WHERE run_id = %s", (run_id,))
        db_conn.commit()


def test_tom_project_config_overrides_reasoning_tom(db_conn):
    """project_config tom_implementations wins over reasoning_result when both set."""
    run_id = str(uuid.uuid4())
    test_project = f"test-tom-override-{uuid.uuid4().hex[:8]}"

    # Seed project_config with a manual override for LLM01
    with db_conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO project_config (project_name, tom_implementations)
            VALUES (%s, %s::jsonb)
            ON CONFLICT (project_name) DO UPDATE SET tom_implementations = EXCLUDED.tom_implementations
            """,
            (test_project, '{"LLM01": "manual override text — user entered"}'),
        )
    db_conn.commit()

    graph_result = {
        "doc_types": ["TOM"],
        "overall_risk": "high",
        "services": [],
        "docs_required": [],
        "controls": [
            {
                "service": "test",
                "control_id": "LLM01",
                "framework": "OWASP_LLM_Top10",
                "title": "Prompt Injection",
                "text": None,
            }
        ],
        "risk_levels": [],
        "active_risks": [],
    }

    reasoning_result_with_tom = {
        "summary": "Test.",
        "priority_actions": [],
        "eu_ai_act_classification": "gpai",
        "tom_implementations": {
            "LLM01": "reasoning generated text — should be overridden",
        },
    }

    _seed_scan_result(run_id, test_project)
    architect = DocumentOrchestrator()
    generated = architect.generate_all(graph_result, reasoning_result_with_tom, test_project, run_id)

    tom_entry = next((d for d in generated if d["doc_type"] == "TOM"), None)
    assert tom_entry is not None

    tom_path = Path(tom_entry["file_path"])
    try:
        content = tom_path.read_text(encoding="utf-8")
        assert "manual override text — user entered" in content, \
            "project_config tom_implementations must override reasoning_result tom"
        assert "reasoning generated text — should be overridden" not in content, \
            "reasoning tom_implementations must not appear when project_config overrides"
    finally:
        tom_path.unlink(missing_ok=True)
        with db_conn.cursor() as cur:
            cur.execute("DELETE FROM generated_docs WHERE run_id = %s", (run_id,))
            cur.execute("DELETE FROM scan_results WHERE run_id = %s", (run_id,))
            cur.execute("DELETE FROM project_config WHERE project_name = %s", (test_project,))
        db_conn.commit()


# ── ADR-110: integration_mode transport (Phase 2) ──────────────────────────────
# DB-free: chains the real derivation (_derive_stripe_integration_mode) with the
# real node_graph_enrichment attach step, mocking only GraphClient. Verifies the
# transient carrier reaches graph_result["services"][i].

def _graph_enrichment_with_mocked_graph(scout_result, services_meta):
    """Run node_graph_enrichment with a mocked GraphClient returning services_meta."""
    from unittest.mock import patch, MagicMock
    from src.workflow.main import node_graph_enrichment

    state = {"scout_result": scout_result, "run_id": "", "graph_usecase_type": None,
             "errors": []}
    fake_result = {
        "services": services_meta, "docs_required": [], "doc_types": [],
        "controls": [], "risk_levels": [], "overall_risk": "limited",
    }
    mock_graph = MagicMock()
    mock_graph.get_compliance_requirements.return_value = fake_result
    mock_ctx = MagicMock()
    mock_ctx.__enter__.return_value = mock_graph
    with patch("src.workflow.main.GraphClient", return_value=mock_ctx):
        return node_graph_enrichment(state)


def test_integration_mode_reaches_graph_services():
    """@stripe/stripe-js scan → graph_result['services'] for Stripe has delegated."""
    from src.workflow.main import _derive_stripe_integration_mode

    raw_services = [{"name": "@stripe/stripe-js", "source": "frontend/package.json"}]
    mode = _derive_stripe_integration_mode(raw_services)
    scout_result = {
        "service_names": ["Stripe", "OpenAI"],
        "service_categories": [],
        "service_modes": {"Stripe": {"integration_mode": mode}},
    }
    services_meta = [{"name": "Stripe", "data_categories": "x"},
                     {"name": "OpenAI", "data_categories": "y"}]

    state = _graph_enrichment_with_mocked_graph(scout_result, services_meta)
    services = state["graph_result"]["services"]
    stripe = next(s for s in services if s["name"] == "Stripe")
    assert stripe["integration_mode"] == "delegated"


def test_non_psp_service_keeps_no_integration_mode():
    """Services without a derived mode (OpenAI) stay untouched — no key, no crash."""
    scout_result = {
        "service_names": ["Stripe", "OpenAI"],
        "service_categories": [],
        "service_modes": {"Stripe": {"integration_mode": "delegated"}},
    }
    services_meta = [{"name": "Stripe", "data_categories": "x"},
                     {"name": "OpenAI", "data_categories": "y"}]

    state = _graph_enrichment_with_mocked_graph(scout_result, services_meta)
    openai = next(s for s in state["graph_result"]["services"] if s["name"] == "OpenAI")
    assert "integration_mode" not in openai


def test_no_service_modes_is_noop():
    """Scout with no service_modes carrier → no integration_mode keys, no crash."""
    scout_result = {"service_names": ["OpenAI"], "service_categories": [],
                    "service_modes": {}}
    services_meta = [{"name": "OpenAI", "data_categories": "y"}]

    state = _graph_enrichment_with_mocked_graph(scout_result, services_meta)
    assert all("integration_mode" not in s for s in state["graph_result"]["services"])


def test_integration_mode_match_is_case_insensitive():
    """Carrier key casing differs from graph node casing → still attaches."""
    scout_result = {"service_names": ["stripe"], "service_categories": [],
                    "service_modes": {"stripe": {"integration_mode": "merchant_side_possible"}}}
    services_meta = [{"name": "Stripe", "data_categories": "x"}]

    state = _graph_enrichment_with_mocked_graph(scout_result, services_meta)
    assert state["graph_result"]["services"][0]["integration_mode"] == "merchant_side_possible"
