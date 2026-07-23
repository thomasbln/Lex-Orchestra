from src.documents.legal_basis_map import (
    render_legal_basis,
    render_data_subjects,
    format_company_display_name,
)


# ---------------------------------------------------------------------------
# render_legal_basis
# ---------------------------------------------------------------------------

def test_render_legal_basis_known_codes():
    assert "Vertragserfüllung" in render_legal_basis("art_6_1_b_contract")
    assert "Einwilligung" in render_legal_basis("art_6_1_a_consent")
    assert "berechtigtes Interesse" in render_legal_basis("art_6_1_f_legitimate_interests")
    assert "§ 26 BDSG" in render_legal_basis("art_88_employment_context")


def test_render_legal_basis_none_returns_empty():
    assert render_legal_basis(None) == ""
    assert render_legal_basis("") == ""


def test_render_legal_basis_unknown_code_passthrough():
    assert render_legal_basis("art_xyz_unknown") == "art_xyz_unknown"


def test_render_legal_basis_en():
    assert "Contractual necessity" in render_legal_basis("art_6_1_b_contract", lang="en")
    assert "Consent" in render_legal_basis("art_6_1_a_consent", lang="en")
    assert "Legitimate interests" in render_legal_basis("art_6_1_f_legitimate_interests", lang="en")


# ---------------------------------------------------------------------------
# render_data_subjects
# ---------------------------------------------------------------------------

def test_render_data_subjects_single():
    assert render_data_subjects(["customers"]) == "Kunden"
    assert render_data_subjects(["employees"]) == "Beschäftigte"


def test_render_data_subjects_list():
    result = render_data_subjects(["customers", "end_users"])
    assert result == "Kunden, Endnutzer"


def test_render_data_subjects_none():
    assert render_data_subjects(None) == ""
    assert render_data_subjects([]) == ""


def test_render_data_subjects_unknown_passthrough():
    assert render_data_subjects(["unknown_role"]) == "unknown_role"


def test_render_data_subjects_string_input():
    assert render_data_subjects("customers") == "Kunden"


def test_render_data_subjects_dedup_after_mapping_collision():
    # "end_users" maps to "Endnutzer" and collides with a literal "Endnutzer";
    # pre-mapping dedup would leave both -> must be collapsed AFTER mapping.
    result = render_data_subjects(["end_users", "Endnutzer"])
    assert result == "Endnutzer"


def test_render_data_subjects_dedup_case_insensitive():
    result = render_data_subjects(["Kunden", "kunden", "KUNDEN"])
    assert result == "Kunden"


def test_render_data_subjects_dedup_preserves_first_seen_order_and_casing():
    result = render_data_subjects(["Endnutzer", "customers", "end_users"])
    # "end_users" collapses into the already-seen "Endnutzer"; order preserved
    assert result == "Endnutzer, Kunden"


# ---------------------------------------------------------------------------
# format_company_display_name
# ---------------------------------------------------------------------------

def test_format_company_display_name_no_suffix():
    assert format_company_display_name("Acme", "GmbH") == "Acme (GmbH)"


def test_format_company_display_name_already_ends_with_form():
    assert format_company_display_name("Rand Industries Inc.", "Inc.") == "Rand Industries Inc."
    assert format_company_display_name("Rand Industries GmbH", "GmbH") == "Rand Industries GmbH"


def test_format_company_display_name_case_insensitive():
    assert format_company_display_name("Rand Industries INC", "Inc") == "Rand Industries INC"


def test_format_company_display_name_no_legal_form():
    assert format_company_display_name("Acme Corp", None) == "Acme Corp"
    assert format_company_display_name("Acme Corp", "") == "Acme Corp"
