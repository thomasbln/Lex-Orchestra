#!/usr/bin/env bash
# Preload gemma4:e4b into Ollama RAM on NucBox.
# Normally NOT needed — the ollama-warmup sidecar runs automatically on
# `docker compose up`. This script is for manual re-warm if the model was
# unloaded for any reason.
set -euo pipefail

MODEL="${OLLAMA_MODEL:-gemma4:e4b}"
OLLAMA_URL="${OLLAMA_BASE_URL:-http://localhost:11434}"
# Match the client's num_ctx to avoid an unload+reload on its first request.
NUM_CTX="${OLLAMA_NUM_CTX:-131072}"

echo "Warming up ${MODEL} at ${OLLAMA_URL} (num_ctx=${NUM_CTX})..."
curl -sf -X POST "${OLLAMA_URL}/api/generate" \
  -H "Content-Type: application/json" \
  -d "{\"model\":\"${MODEL}\",\"prompt\":\"hi\",\"stream\":false,\"keep_alive\":-1,\"options\":{\"num_ctx\":${NUM_CTX}}}" \
  -o /dev/null -w "HTTP %{http_code} in %{time_total}s\n"

echo "Done. ${MODEL} pinned in RAM (keep_alive=-1)."
