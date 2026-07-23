#!/usr/bin/env bash
#
# fujitsu_reset.sh — restore the Fujitsu clean-room host to "bare host" state.
#
# WHY THIS EXISTS
#   ADR-130 D7 rehearses the public-release install path on a machine that has
#   none of NucBox's accumulated state. A rehearsal is only worth anything if
#   the stage is empty. Re-running `make seed-all` against a graph that is
#   already seeded would come back green for the wrong reason — the volume, not
#   the seed, would be doing the work. This script guarantees the stage is empty.
#
# WHAT IT REMOVES (application layer)
#   - every container of the compose project (label com.docker.compose.project)
#   - every named volume of that project        <-- the Neo4j graph lives here
#   - the docker_lex-net network
#   - the repo clone ($HOME/Lex-Orchestra, override with LEX_REPO), including
#     .venv, every .env, legal/ output and pgdata
#   - project images, ONLY with --full
#
# WHAT IT KEEPS (host layer) — never touched
#   Docker engine + compose, git, Node, Python, the SSH config, the GitHub
#   deploy key, the docker group membership. There is no `docker system prune`
#   in this script: pruning without a project filter would take foreign images
#   and volumes with it.
#
# KNOWN TRACE — alpine:3 (13 MB) stays on the host
#   Deleting the clone needs root: pgdata is mode 700 and legal/ is written by
#   the container as root. A throwaway alpine:3 container does it, and that
#   image is left behind on purpose. Removing it would only force a re-pull on
#   the next run — purity theatre against practicality. It carries no project
#   state, and --full does not touch it either. So: "bare host" means bare of
#   Lex, not bare of Docker's own scratch layer. Stated here so nobody has to
#   rediscover it.
#
# FLAGS
#   (none)      containers + volumes + network + clone. Images are kept, so the
#               next run starts fast. This is the Thursday/Friday default.
#   --full      additionally removes the project's images. Use this when the
#               point of the run is to prove the build itself is reproducible
#               from zero — it forces a real re-pull and re-build.
#   --dry-run   prints every action without performing it. Combines with --full.
#   --help      this text.
#
# USAGE
#   On the Fujitsu:
#       bash scripts/fujitsu_reset.sh --dry-run
#       bash scripts/fujitsu_reset.sh
#
#   Over SSH from the Mac (the script is streamed, so it survives deleting its
#   own repo — note the `--` before the flags):
#       ssh fujitsu 'bash -s -- --dry-run' < scripts/fujitsu_reset.sh
#       ssh fujitsu 'bash -s -- --full'    < scripts/fujitsu_reset.sh
#
# SAFETY
#   Hard-aborts unless the hostname is the clean-room host. This script deletes
#   a Neo4j volume; on NucBox that volume is the authoritative graph, and on the
#   Mac the repo is the working tree. Neither may ever be a target.
#
# EXIT CODES
#   0  host is clean, verified
#   1  leftovers found after the reset, or a guard tripped
#
set -euo pipefail

# ── Configuration ────────────────────────────────────────────────────────────
EXPECTED_HOST="fujitsu"
REPO="${LEX_REPO:-$HOME/Lex-Orchestra}"
COMPOSE_PROJECT="docker"          # compose derives it from the docker/ directory
NETWORK="docker_lex-net"
VOLUME_PREFIX="docker_"           # docker_neo4j_data, docker_ollama_data, ...
ROOT_HELPER_IMAGE="alpine:3"      # throwaway container to delete root-owned paths

DRY_RUN=0
FULL=0

# ── Output helpers ───────────────────────────────────────────────────────────
red()  { printf "\033[31m%s\033[0m\n" "$*"; }
grn()  { printf "\033[32m%s\033[0m\n" "$*"; }
ylw()  { printf "\033[33m%s\033[0m\n" "$*"; }
hdr()  { printf "\n\033[1m── %s\033[0m\n" "$*"; }

run() {
    if [ "$DRY_RUN" -eq 1 ]; then
        printf "  \033[33m[dry-run]\033[0m %s\n" "$*"
    else
        printf "  %s\n" "$*"
        eval "$@"
    fi
}

# ── Flags ────────────────────────────────────────────────────────────────────
usage() {
    # A heredoc, not `sed` over "$0": when the script is streamed through
    # `ssh fujitsu 'bash -s'` there is no file to read the header back from.
    cat <<'USAGE'
fujitsu_reset.sh — restore the Fujitsu clean-room host to "bare host" state.

REMOVES  containers, named volumes (the Neo4j graph lives there), the
         docker_lex-net network, and the repo clone including .venv, every
         .env, legal/ output and pgdata.
KEEPS    Docker engine + compose, git, Node, Python, SSH config, GitHub deploy
         key, docker group membership. No unfiltered prune, ever.

CLONE    defaults to $HOME/Lex-Orchestra (the path the README clone produces).
         Override with LEX_REPO=/some/other/path.

  (none)     containers + volumes + network + clone; images kept (fast re-test)
  --full     also remove project images (proves the build is reproducible)
  --dry-run  print what would happen, change nothing; combines with --full
  --help     this text

  bash scripts/fujitsu_reset.sh --dry-run
  ssh fujitsu 'bash -s -- --full' < scripts/fujitsu_reset.sh

Hard-aborts unless the hostname is the clean-room host: this script deletes a
Neo4j volume, and on NucBox that volume is the authoritative graph.
USAGE
}

for arg in "$@"; do
    case "$arg" in
        --dry-run) DRY_RUN=1 ;;
        --full)    FULL=1 ;;
        --help|-h) usage; exit 0 ;;
        *) red "Unknown flag: $arg (try --help)"; exit 1 ;;
    esac
done

# ── Guard: are we on the clean-room host? ────────────────────────────────────
# This is the guard that matters. Everything below deletes a Neo4j volume.
hdr "Host guard"

HOST="$(hostname -s 2>/dev/null || hostname)"
OS="$(uname -s)"

if [ "$OS" = "Darwin" ]; then
    red "ABORT: running on macOS. This script is for the Fujitsu clean-room host."
    red "       On the Mac, ~/Projects/Lex-Orchestra is your working tree."
    exit 1
fi

case "$HOST" in
    lex-nuc|nuc|raspberrypi|pi)
        red "ABORT: hostname is '$HOST'."
        red "       That is a deploy target, not the clean room. Its Neo4j volume"
        red "       is the authoritative graph. Refusing to continue."
        exit 1
        ;;
esac

if [ "$HOST" != "$EXPECTED_HOST" ]; then
    red "ABORT: hostname is '$HOST', expected '$EXPECTED_HOST'."
    red "       Refusing to delete volumes on an unrecognised host."
    exit 1
fi

grn "  host='$HOST' os='$OS' — clean-room host confirmed"

# ── Guard: is the repo path sane? ────────────────────────────────────────────
# The clone is deleted by a root container, so a wrong path here would be
# expensive. Refuse anything that does not look exactly like the clone.
REPO_OK=0
if [ -d "$REPO" ]; then
    if [ -d "$REPO/.git" ] && [ -d "$REPO/docker" ] && [ -d "$REPO/scripts" ] \
       && [ "$REPO" != "$HOME" ] && [ "$REPO" != "/" ]; then
        REPO_OK=1
        grn "  repo='$REPO' — looks like the clone (.git + docker/ + scripts/)"
    else
        red "ABORT: '$REPO' exists but does not look like the Lex-Orchestra clone."
        red "       Expected .git/, docker/ and scripts/ inside it. Refusing."
        exit 1
    fi
else
    ylw "  repo='$REPO' — not present (already removed, or never cloned)"
fi

if [ "$DRY_RUN" -eq 1 ]; then
    ylw "  DRY RUN — nothing will be changed."
fi
if [ "$FULL" -eq 1 ]; then
    ylw "  FULL    — project images will be removed as well."
fi

# ── 1. Containers: compose down (preferred) ──────────────────────────────────
# -v is the whole point: without it the Neo4j volume survives and the next
# seed-all validates against a graph it did not create.
hdr "1. Containers + volumes (compose down -v)"

if [ "$REPO_OK" -eq 1 ] && [ -f "$REPO/docker/docker-compose.yml" ]; then
    RMI=""
    [ "$FULL" -eq 1 ] && RMI="--rmi local"
    run "docker compose --project-directory '$REPO/docker' \
             -f '$REPO/docker/docker-compose.yml' \
             --profile with-neo4j --profile with-ollama \
             down -v --remove-orphans $RMI 2>&1 | sed 's/^/    /' || true"
else
    ylw "  no clone — skipping compose down, falling back to label filter"
fi

# ── 2. Containers: fallback by label ─────────────────────────────────────────
# Catches anything compose down missed (orphans, a half-removed clone, a run
# that was interrupted).
hdr "2. Containers (fallback: label com.docker.compose.project=$COMPOSE_PROJECT)"

LEFTOVER_C="$(docker ps -aq --filter "label=com.docker.compose.project=$COMPOSE_PROJECT" 2>/dev/null || true)"
if [ -n "$LEFTOVER_C" ]; then
    run "docker rm -f $(echo "$LEFTOVER_C" | tr '\n' ' ') >/dev/null"
else
    grn "  none left"
fi

# ── 3. Volumes: by project prefix ────────────────────────────────────────────
hdr "3. Volumes (prefix '$VOLUME_PREFIX')"

LEFTOVER_V="$(docker volume ls -q 2>/dev/null | grep "^${VOLUME_PREFIX}" || true)"
if [ -n "$LEFTOVER_V" ]; then
    echo "$LEFTOVER_V" | sed 's/^/    found: /'
    run "docker volume rm $(echo "$LEFTOVER_V" | tr '\n' ' ') >/dev/null"
else
    grn "  none left"
fi

# ── 4. Network ───────────────────────────────────────────────────────────────
hdr "4. Network ($NETWORK)"

if docker network inspect "$NETWORK" >/dev/null 2>&1; then
    run "docker network rm '$NETWORK' >/dev/null"
else
    grn "  not present"
fi

# ── 5. Repo clone (via root container) ───────────────────────────────────────
# docker/supabase/pgdata is owned by root (mode 700) and legal/ is written by
# the container as root, so a plain `rm -rf` as the login user fails. A
# throwaway container mounts the PARENT directory and removes the clone as root.
hdr "5. Repo clone ($REPO)"

if [ "$REPO_OK" -eq 1 ]; then
    PARENT="$(dirname "$REPO")"
    NAME="$(basename "$REPO")"
    echo "    (removing via root container — pgdata and legal/ are root-owned)"
    run "docker run --rm -v '$PARENT':/mnt '$ROOT_HELPER_IMAGE' \
             rm -rf '/mnt/$NAME' >/dev/null 2>&1 || rm -rf '$REPO'"
else
    grn "  not present"
fi

# ── 6. Images (only with --full) ─────────────────────────────────────────────
hdr "6. Images"

if [ "$FULL" -eq 1 ]; then
    # Explicit list — never a bare `prune -a`, which would take foreign images.
    for img in \
        "docker-lex-agent" "docker-lex-dashboard" \
        "neo4j" "supabase/postgres" "ollama/ollama" "curlimages/curl"
    do
        IDS="$(docker images -q "$img" 2>/dev/null || true)"
        if [ -n "$IDS" ]; then
            run "docker rmi -f $(echo "$IDS" | tr '\n' ' ') >/dev/null 2>&1 || true"
        fi
    done
    grn "  project images removed (next run re-pulls and re-builds from zero)"
else
    ylw "  kept (default) — pass --full to force a from-zero build"
fi

# ── 7. Verification — the actual point of this script ────────────────────────
hdr "7. Verification"

if [ "$DRY_RUN" -eq 1 ]; then
    ylw "  skipped (dry run)"
    echo ""
    ylw "DRY RUN COMPLETE — nothing was changed."
    exit 0
fi

FAIL=0
check() {  # check <label> <actual> <expected>
    if [ "$2" = "$3" ]; then
        grn "  OK    $1: $2"
    else
        red "  LEFT  $1: $2 (expected $3)"
        FAIL=1
    fi
}

C_LEFT="$(docker ps -aq --filter "label=com.docker.compose.project=$COMPOSE_PROJECT" 2>/dev/null | wc -l | tr -d ' ')"
V_LEFT="$(docker volume ls -q 2>/dev/null | grep -c "^${VOLUME_PREFIX}" || true)"
N_LEFT="$(docker network ls -q --filter "name=^${NETWORK}$" 2>/dev/null | wc -l | tr -d ' ')"
R_LEFT="$([ -d "$REPO" ] && echo 1 || echo 0)"

check "containers" "$C_LEFT" "0"
check "volumes"    "$V_LEFT" "0"
check "network"    "$N_LEFT" "0"
check "repo clone" "$R_LEFT" "0"

if [ "$FULL" -eq 1 ]; then
    I_LEFT=0
    for img in "docker-lex-agent" "docker-lex-dashboard" "neo4j" "supabase/postgres" "ollama/ollama"; do
        n="$(docker images -q "$img" 2>/dev/null | wc -l | tr -d ' ')"
        I_LEFT=$((I_LEFT + n))
    done
    check "images" "$I_LEFT" "0"
fi

echo ""
if [ "$FAIL" -eq 0 ]; then
    grn "HOST READY FOR CLEANROOM RUN"
    exit 0
else
    red "RESET INCOMPLETE — leftovers above would falsify the next run."
    exit 1
fi
