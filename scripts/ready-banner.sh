#!/bin/sh
# scripts/ready-banner.sh — final setup step: print the URLs to reach the stack.
#
# Appended to `make seed-validate`; runs only after validation succeeds.
# Purely informative and non-blocking: it never fails the calling target
# (always exits 0) and degrades gracefully if the LAN IP or curl are absent.
#
# NOTE: this is the minimal completion banner for the manual README quickstart —
# NOT a replacement for the interactive scripts/setup.py designed in ADR-054.
# That decision stays open; this only fills the missing "you're done" step.
#
# The logo is a hardcoded 7-bit ASCII string (no figlet/toilet dependency), so
# it renders identically on any host without an extra install.

grn() { printf "\033[32m%s\033[0m\n" "$*"; }   # color helpers mirror scripts/fujitsu_reset.sh:77-80
ylw() { printf "\033[33m%s\033[0m\n" "$*"; }

# ── ASCII logo — whole block green, subtitle centered under the wordmark ──────
logo() {
    printf '\033[32m%s\033[0m\n' \
"#     ##### #   #" \
"#     #      # #" \
"#     ####    #" \
"#     #      # #" \
"##### ##### #   #" \
"" \
" ###  ####   #### #   # #####  #### ##### ####   ###" \
"#   # #   # #     #   # #     #       #   #   # #   #" \
"#   # ####  #     ##### ####   ###    #   ####  #####" \
"#   # #  #  #     #   # #         #   #   #  #  #   #" \
" ###  #   #  #### #   # ##### ####    #   #   # #   #" \
"               installed successfully"
}

# ── Determine the host's LAN IP, portable across Linux and macOS ──────────────
# Platform switch in the uname -s / Darwin style of scripts/fujitsu_reset.sh:134-136.
# `hostname -I` is Linux-only (absent on macOS/BSD), so it is only a last resort.
OS="$(uname -s)"
LAN_IP=""
if [ "$OS" = "Darwin" ]; then
    for IFACE in en0 en1 en2; do
        LAN_IP="$(ipconfig getifaddr "$IFACE" 2>/dev/null)"
        [ -n "$LAN_IP" ] && break
    done
else
    LAN_IP="$(ip -4 addr show scope global 2>/dev/null \
        | awk '/inet /{sub(/\/.*/, "", $2); print $2; exit}')"
    [ -z "$LAN_IP" ] && LAN_IP="$(hostname -I 2>/dev/null | awk '{print $1}')"
fi

# ── Optional reachability probe — informative only, never blocks ──────────────
# Probes a known-good endpoint (as scripts/infra-check.sh does) but the banner
# still prints the plain base URL for the user. HTTP services only — Supabase is
# raw Postgres (no HTTP endpoint), so it is listed but not probed.
probe() {
    command -v curl >/dev/null 2>&1 || return 0
    if curl -sf -m 2 "$1" >/dev/null 2>&1; then
        grn "  reachable"
    else
        ylw "  not reachable yet (the container may still be starting)"
    fi
}

logo
printf "\n"
printf "Dashboard (this machine):  http://localhost:3000\n"; probe http://localhost:3000
printf "API       (this machine):  http://localhost:8001\n"; probe http://localhost:8001/config/projects
printf "Neo4j     (this machine):  http://localhost:7474\n"; probe http://localhost:7474
printf "Supabase  (this machine):  postgresql://postgres:<see docker/envs/.env>@localhost:5432/postgres\n"

if [ -n "$LAN_IP" ]; then
    printf "\nFrom another device on this network:\n"
    printf "Dashboard:  http://%s:3000\n" "$LAN_IP"
    printf "API:        http://%s:8001\n" "$LAN_IP"
    printf "Neo4j:      http://%s:7474\n" "$LAN_IP"
    printf "Supabase:   postgresql://postgres:<see docker/envs/.env>@%s:5432/postgres\n" "$LAN_IP"
else
    printf "\n"
    ylw "Could not determine the LAN IP — for remote access use the host's network address."
fi

printf "\n"
grn "Next steps:"
printf "  1. Open the Dashboard: http://%s:3000\n" "${LAN_IP:-localhost}"
printf "  2. Create your first project\n"
printf "  3. Point it at a repo and run the first scan\n"
exit 0
