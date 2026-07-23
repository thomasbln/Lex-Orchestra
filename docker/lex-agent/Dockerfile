# Lex-Orchestra Agent — LangGraph workflow container
# Platform: linux/arm64 (Raspberry Pi 4, aarch64)
# Build context: repo root (set in docker-compose.yml)

FROM python:3.13-slim

WORKDIR /app

# System deps:
#   pandoc   — legacy pypandoc path (unused, kept for compat)
#   libpq-dev / gcc — required to build psycopg[binary] from source on ARM64
#                     (psycopg-binary wheel may not exist for arm64 + Python 3.13)
#   WeasyPrint runtime (Markdown→PDF, ADR pre-DSB sprint step 2):
#     libpango/cairo/gdk-pixbuf/harfbuzz — rendering engine shared libs
#     fonts-dejavu          — body + mono font (umlauts, ≈ glyph)
#     fonts-noto-color-emoji — colour emoji fallback (🔴 ✅ ⚠️ in markers)
#     poppler-utils         — pdftoppm for in-container visual checks
RUN apt-get update && apt-get install -y --no-install-recommends \
        pandoc \
        libpq-dev \
        gcc \
        build-essential \
        git \
        libpango-1.0-0 \
        libpangocairo-1.0-0 \
        libgdk-pixbuf-2.0-0 \
        libharfbuzz0b \
        libffi8 \
        fonts-dejavu \
        fonts-noto-color-emoji \
        poppler-utils \
    && rm -rf /var/lib/apt/lists/* \
    && fc-cache -f

# WeasyPrint runs as uid 1000 (no writable system fontconfig cache there).
# Point the user cache at /app/.cache — /app is chowned to 1000 below, so it is
# writable, unlike /tmp/.cache which root-owned build steps (spacy) pre-create.
# Stops "Fontconfig error: No writable cache directories" spamming trust-chain logs.
ENV XDG_CACHE_HOME=/app/.cache

# Copy requirements from repo root (build context = repo root)
COPY requirements.txt .

# Install Python deps
# psycopg[binary] is required by langgraph-checkpoint-postgres (PostgresSaver).
# It is separate from psycopg2-binary used by asset_translator.
RUN pip install --no-cache-dir -r requirements.txt \
 && pip install --no-cache-dir "psycopg[binary]"

# Download spaCy models for Presidio (ADR-028 Layer 2)
# de_core_news_sm: German NER (PERSON, ORG, LOC) — ~15 MB
# en_core_web_sm:  English NER fallback — ~12 MB
RUN python -m spacy download de_core_news_sm \
 && python -m spacy download en_core_web_sm

# langgraph.json must be in WORKDIR — langgraph dev reads it on startup
COPY langgraph.json .

# Copy source (volumes override /app/src and /app/legal at runtime)
COPY src/ ./src/

# Ensure /app is writable by uid 1000 (pi user on Pi host)
RUN chown -R 1000:1000 /app

# No CMD — docker-compose defines the command per service
