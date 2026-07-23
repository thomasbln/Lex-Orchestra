"""
Asset Translator — ADR-001 PII Separation
==========================================
Stores real asset details LOCALLY in PostgreSQL (Supabase on Pi).
Returns only UUIDs + anonymous types to Neo4j / LLM.

Principle (ADR-001):
  Scout finds: "STRIPE_SECRET_KEY" in app.py:42
  PostgreSQL stores: {uuid, project_id, type="api_key", name="stripe_key", file="app.py"}
  Neo4j sees:  {uuid, type="api_key", encrypted=false}  ← never the real name or path

Usage:
    translator = AssetTranslator()
    translator.setup()                         # create tables if not exists
    uuids = translator.store_assets(project_id, scout_services)
    anon  = translator.anonymize(scout_services)
    full  = translator.resolve(uuid)
"""

import logging
import os
import uuid
from dataclasses import dataclass, field
from typing import Optional

import psycopg2
import psycopg2.extras
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

def _resolve_db_url() -> str:
    # MCP_SUPABASE_URL always points to accessible host (raspberrypi.local from Mac,
    # or configured host from Pi). DATABASE_URL uses docker-internal hostname "supabase-db"
    # which only resolves inside the Docker network.
    mcp_url = os.getenv("MCP_SUPABASE_URL", "")
    db_url  = os.getenv("DATABASE_URL", "")
    if mcp_url:
        return mcp_url
    if db_url and "supabase-db" not in db_url:
        return db_url
    return db_url  # last resort, may fail outside Docker

DB_URL = _resolve_db_url()

# Explicit canonical overrides — checked before fuzzy matching.
# None means "known credential hint, not an external service node".
CANONICAL_MAP: dict[str, Optional[str]] = {
    "resend":        "Resend",
    "clerk":         "Clerk",
    "@clerk/nextjs": "Clerk",
    "neo4j":         None,  # credential hint only — not a billable third-party SaaS
}

# Known generic service names (these exist in Neo4j seed — safe to pass to graph)
# Scout output that matches these gets mapped to the canonical seed name
KNOWN_SERVICES = {
    "openai", "anthropic", "stripe", "paypal", "google analytics", "google ads",
    "aws", "amazon", "hetzner", "cloudflare", "github", "gitlab", "sendgrid",
    "mailchimp", "twilio", "slack", "hubspot", "salesforce", "zendesk",
    "intercom", "segment", "mixpanel", "amplitude", "sentry", "datadog",
    "new relic", "mongodb atlas", "supabase", "firebase", "vercel", "netlify",
    "google gemini", "mistral ai", "hugging face", "cohere", "replicate",
    "azure", "gcp",
}


@dataclass
class AssetRecord:
    """In-memory representation of a discovered asset."""
    uuid: str
    project_id: str
    type: str           # "service", "api_key", "domain", "database"
    category: str       # "payment", "ai_llm", "analytics", "storage"
    name: str           # real name — stored locally ONLY
    source: str         # "docker-compose", "package.json", ".env.example"
    confidence: float = 1.0
    encrypted: bool = False
    public: bool = False
    canonical_name: Optional[str] = None  # matching Neo4j seed name if known


class AssetTranslator:
    """Translates between real asset data (local) and anonymous UUIDs (cloud-safe)."""

    def __init__(self, db_url: str = DB_URL):
        if not db_url:
            raise ValueError("DATABASE_URL or MCP_SUPABASE_URL required in .env")
        self.db_url = db_url

    def _connect(self):
        return psycopg2.connect(self.db_url)

    def setup(self) -> None:
        """Create tables if they don't exist. Safe to call multiple times."""
        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    CREATE TABLE IF NOT EXISTS assets (
                        id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                        project_id  UUID NOT NULL,
                        type        TEXT NOT NULL,
                        category    TEXT NOT NULL DEFAULT '',
                        name        TEXT NOT NULL,
                        source      TEXT NOT NULL DEFAULT '',
                        confidence  FLOAT NOT NULL DEFAULT 1.0,
                        encrypted   BOOLEAN NOT NULL DEFAULT false,
                        public      BOOLEAN NOT NULL DEFAULT false,
                        canonical_name TEXT,
                        detected_at TIMESTAMPTZ NOT NULL DEFAULT now()
                    )
                """)
                cur.execute("""
                    CREATE INDEX IF NOT EXISTS assets_project_idx
                    ON assets (project_id)
                """)
                cur.execute("""
                    CREATE UNIQUE INDEX IF NOT EXISTS assets_project_name_source_unique
                    ON assets (project_id, name, source)
                """)
                conn.commit()
        logger.info("AssetTranslator tables ready")

    def store_assets(self, project_id: str, services: list[dict]) -> list[AssetRecord]:
        """
        Store real asset data in PostgreSQL. Returns AssetRecord list with UUIDs.
        Input services format (from Scout):
          [{"name": "Stripe", "category": "payment", "source": "docker-compose.yml"}, ...]
        """
        records = []
        with self._connect() as conn:
            with conn.cursor() as cur:
                for svc in services:
                    name = svc.get("name", "unknown")
                    category = svc.get("category", "")
                    source = svc.get("source", "")
                    asset_type = svc.get("type", "service")
                    encrypted = svc.get("encrypted", False)
                    public = svc.get("public", False)
                    canonical = _canonical_name(name)

                    asset_id = str(uuid.uuid4())
                    cur.execute("""
                        INSERT INTO assets
                          (id, project_id, type, category, name, source,
                           confidence, encrypted, public, canonical_name)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                        ON CONFLICT (project_id, name, source) DO UPDATE
                          SET detected_at    = now(),
                              confidence     = EXCLUDED.confidence,
                              canonical_name = EXCLUDED.canonical_name,
                              category       = EXCLUDED.category
                        RETURNING id
                    """, (
                        asset_id, project_id, asset_type, category, name,
                        source, svc.get("confidence", 1.0),
                        encrypted, public, canonical
                    ))
                    asset_id = str(cur.fetchone()[0])
                    logger.debug("Upserted asset: %s → %s", name, asset_id)

                    records.append(AssetRecord(
                        uuid=asset_id,
                        project_id=project_id,
                        type=asset_type,
                        category=category,
                        name=name,
                        source=source,
                        encrypted=encrypted,
                        public=public,
                        canonical_name=canonical,
                    ))
                conn.commit()

        logger.info("Stored %d assets for project %s", len(records), project_id)
        return records

    def anonymize(self, records: list[AssetRecord]) -> list[dict]:
        """
        Return cloud-safe representation: UUIDs + types only, no real names.
        This is what Neo4j and the LLM are allowed to see.
        """
        return [
            {
                "uuid": r.uuid,
                "type": r.type,
                "category": r.category,
                "encrypted": r.encrypted,
                "public": r.public,
                "canonical_name": r.canonical_name,  # generic seed name (e.g. "Stripe")
            }
            for r in records
        ]

    def resolve(self, asset_uuid: str) -> Optional[dict]:
        """Look up full asset details from PostgreSQL by UUID."""
        with self._connect() as conn:
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                cur.execute("SELECT * FROM assets WHERE id = %s", (asset_uuid,))
                row = cur.fetchone()
                return dict(row) if row else None

    def resolve_many(self, uuids: list[str]) -> dict[str, dict]:
        """Look up multiple UUIDs at once. Returns {uuid: asset_dict}."""
        if not uuids:
            return {}
        with self._connect() as conn:
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                cur.execute(
                    "SELECT * FROM assets WHERE id = ANY(%s)",
                    (uuids,)
                )
                return {str(row["id"]): dict(row) for row in cur.fetchall()}

    def get_project_assets(self, project_id: str) -> list[dict]:
        """Return all assets for a project (full data — local use only)."""
        with self._connect() as conn:
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                cur.execute(
                    "SELECT * FROM assets WHERE project_id = %s ORDER BY detected_at",
                    (project_id,)
                )
                return [dict(r) for r in cur.fetchall()]


def _canonical_name(name: str) -> Optional[str]:
    """Match a detected service name to its Neo4j seed canonical name."""
    normalized = name.lower().strip()
    # Explicit overrides take precedence (handles packages like "@clerk/nextjs")
    if normalized in CANONICAL_MAP:
        return CANONICAL_MAP[normalized]
    # Fuzzy substring match against known seed names
    for known in KNOWN_SERVICES:
        if known in normalized or normalized in known:
            return known.title()
    return None
