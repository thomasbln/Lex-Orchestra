# 20_frameworks — license-gated framework layers (BYOS)

This directory is the slot for framework seed layers whose **content is
license-gated** and therefore not shipped in the repository:

- `20_bsi_c5.cypher` — BSI C5 controls (commercial BSI license required)
- `20_aic4.cypher` — BSI AIC4 controls (same license gate)

Bring your own licensed copy: place the file(s) here, then enable the
corresponding module in the seed configuration before running `make seed-all`.
The seed manifest deliberately never auto-includes files from this directory —
a fresh install works fully without them (the shipped frameworks live in the
other layer directories and in `scripts/seed_both.py`).

ISO 27001 follows the same bring-your-own-standard model via
`../byos/iso27001.cypher`.
