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
    # MCP_SUPABASE_URL points at the database from OUTSIDE the Docker network
    # (host name or IP of the machine running the stack). DATABASE_URL uses the
    # docker-internal hostname "supabase-db", which only resolves inside it.
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

# ── Token → catalog spelling (2026-07-28) ────────────────────────────────────
#
# This replaces the former `KNOWN_SERVICES` set, which held lowercase tokens and
# was turned into a display name by `known.title()`. That produced spellings no
# catalog entry carries — "Openai", "Aws", "GitHub"→"Github", "PayPal"→"Paypal",
# "SendGrid"→"Sendgrid", "HubSpot"→"Hubspot", "Mistral AI"→"Mistral Ai". A name
# the catalog does not know is dropped by graph_client.Q_META's hard
# `MATCH (s:Service {name: nm})`, so the service silently left the DPA processor
# list. 86 rows in `assets` still carry "Openai" from that era.
#
# `signal_map.canonical()` is asked FIRST — it is the project's one token→name
# table and is pinned against the seed catalog by
# tests/test_signal_map_catalog_pin.py. This dict only carries what that table
# does not know yet, so there is no second source of truth to drift: every entry
# here is a candidate for moving into SIGNAL_MAP.
#
# Values must be catalog names — pinned by tests/test_name_factory_pin.py.
EXTRA_CATALOG_NAMES: dict[str, str] = {
    "aws":              "AWS",
    "azure":            "Azure",
    "cloudflare":       "Cloudflare",
    "firebase":         "Firebase",
    "github":           "GitHub",
    "google analytics": "Google Analytics",
    "google gemini":    "Google Gemini",
    "hetzner":          "Hetzner",
    "hubspot":          "HubSpot",
    "hugging face":     "Hugging Face",
    "intercom":         "Intercom",
    "mailchimp":        "Mailchimp",
    "mistral ai":       "Mistral AI",
    "mongodb atlas":    "MongoDB Atlas",
    "paypal":           "PayPal",
    "slack":            "Slack",
}
#
# Note on "mongodb atlas": it is listed so an input that literally says
# "MongoDB Atlas" keeps its name — NOT so a bare `mongodb` resolves to it. The
# old code matched backwards as well ("mongodb" is a substring of "mongodb
# atlas") and did exactly that; ADR-072 (see the note in signal_map.py around
# "mongodb (JS), pymongo, motor all intentionally unmapped") rules it out,
# because library presence cannot tell self-hosted MongoDB from Atlas and naming
# a processor would be a false claim. Forward-only matching is what keeps the
# entry safe here — see ADR-130 A1.8.
#
# Deliberately absent: "amazon", "cohere", "gcp", "gitlab", "google ads",
# "new relic", "salesforce", "zendesk". No catalog entry exists for any of them.
# Mapping them would mean inventing a name the graph cannot resolve; leaving
# them out means the detection has no canonical name, which is the honest
# answer. Adding a catalog entry is the way to make them resolvable, not adding
# a row here.


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


def _catalog_spellings() -> frozenset[str]:
    """Every name this module is allowed to emit. Cheap, computed once."""
    global _CATALOG_SPELLINGS
    if _CATALOG_SPELLINGS is None:
        from src.scout.signal_map import SIGNAL_MAP
        _CATALOG_SPELLINGS = frozenset(
            {v for v in SIGNAL_MAP.values() if v}
            | set(EXTRA_CATALOG_NAMES.values())
            | {v for v in CANONICAL_MAP.values() if v}
        )
    return _CATALOG_SPELLINGS


_CATALOG_SPELLINGS: Optional[frozenset[str]] = None


def _canonical_name(name: str) -> Optional[str]:
    """Match a detected service name to its Neo4j seed canonical name.

    Rewritten 2026-07-28 (ADR-130 A1.8 follow-up). The previous version ended in
    ``known.title()`` over a lowercase token set, which invented spellings the
    catalog does not carry. Four changes, each measured before it was made:

    1. **Already-canonical input passes through untouched.** The old code re-ran
       a correct name through the factory: ``"OpenAI"`` came back as
       ``"Openai"``. This is the actual defect — not a missing mapping.
    2. **``signal_map.canonical()`` is asked before the local table**, so there
       is one token→name source of truth rather than two drifting ones.
    3. **No backwards substring match.** ``normalized in known`` carried exactly
       one case across every catalog name and 46 realistic package names —
       ``mongodb`` → ``mongodb atlas`` — and ADR-072 rules that mapping out.
    4. **Sorted, longest match first.** The old iteration ran over a ``set``;
       Python randomises string hashing per process, so with two candidate
       tokens the winner could differ between runs. No input matches two tokens
       today, which is why this never showed — it was luck, not design.
    """
    normalized = name.lower().strip()

    # 1 — already a name we are allowed to emit: hands off.
    if name in _catalog_spellings():
        return name

    # 2 — explicit overrides (packages like "@clerk/nextjs", credential hints).
    if normalized in CANONICAL_MAP:
        return CANONICAL_MAP[normalized]

    # 3 — the project's shared token table, exact lookup (it does its own
    #     hyphen/underscore stripping: "sentry-sdk" → "sentrysdk").
    from src.scout.signal_map import canonical as _signal_map_canonical
    hit = _signal_map_canonical(normalized)
    if hit:
        return hit

    # 4 — forward substring over BOTH token sets, longest first. Both are
    #     needed: SIGNAL_MAP resolves "sendgrid" but its lookup is exact, so a
    #     package like "@sendgrid/mail" only lands here. Overlapping SIGNAL_MAP
    #     keys were checked — all 21 pairs resolve to the same canonical name,
    #     and no key is shorter than five characters, so substring matching
    #     cannot fire on a fragment.
    for token, target in _substring_tokens():
        if token in normalized:
            return target
    return None


def _substring_tokens() -> list[tuple[str, str]]:
    """(token, catalog name) pairs, longest token first. Computed once."""
    global _SUBSTRING_TOKENS
    if _SUBSTRING_TOKENS is None:
        from src.scout.signal_map import SIGNAL_MAP
        merged = {k: v for k, v in SIGNAL_MAP.items() if v}
        merged.update(EXTRA_CATALOG_NAMES)
        _SUBSTRING_TOKENS = sorted(merged.items(), key=lambda kv: len(kv[0]), reverse=True)
    return _SUBSTRING_TOKENS


_SUBSTRING_TOKENS: Optional[list[tuple[str, str]]] = None
