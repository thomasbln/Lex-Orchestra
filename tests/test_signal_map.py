"""Unit tests for signal_map.canonical() — ADR-115 A1 PSP-role launch detection.

signal_map carries *detection* only; the EDPB controller/processor role lives on
the seeded Service node (scripts/seed_both.py:seed_psp_roles). These tests assert
the detection entries canonicalize byte-exact to the seeded node names, so the
seeded role greift on match — same mechanism as paypalrestsdk→PayPal.
"""

from src.scout.signal_map import canonical


def test_psp_role_launch_entries_canonicalize_to_seeded_names():
    """The three new entries resolve to the exact names seeded by seed_psp_roles."""
    assert canonical("klarna") == "Klarna"
    assert canonical("digistore24") == "Digistore24"
    assert canonical("billwerk") == "Billwerk"


def test_psp_tokens_match_real_dependency_components_and_normalization():
    """Real SDK tokens the manifest parsers surface (scope/name split, case-insensitive,
    hyphen/underscore-stripped) map cleanly."""
    # composer `klarna/kco_rest` → scope component "klarna"; npm bare `klarna`
    assert canonical("Klarna") == "Klarna"          # case-insensitive
    # composer `author/digistore24`, npm `@pipedream/digistore24` → name component
    assert canonical("DigiStore24") == "Digistore24"
    # bare npm `billwerk`
    assert canonical("billwerk") == "Billwerk"


def test_billwerk_coverage_limit_suffix_variants_unmapped():
    """ADR-115 A1 honest coverage limit: bare `billwerk` only. The dominant composer
    integrations normalize to billwerk<suffix> and intentionally do NOT match — left
    to the Gemma4 fallback, no false-positive suffix guessing."""
    assert canonical("billwerk-plus-subscription") is None
    assert canonical("billwerk-api") is None
    assert canonical("laravel-billwerk") is None
    assert canonical("omnipay-billwerk") is None


def test_klarna_omnipay_variant_unmapped():
    """Same pattern for Klarna: omnipay/scoped wrappers don't match — but Klarna is
    still covered via the official `klarna/*` composer scope + bare npm `klarna`."""
    assert canonical("omnipay-klarna-checkout") is None
    assert canonical("react-native-klarna-inapp-sdk") is None
