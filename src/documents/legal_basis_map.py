"""ADR-100 legal_basis codes → human-readable DE/EN renderings.

The graph stores normalized codes on SUBJECT_TO_CONTROL edges.
Document builders call render_legal_basis(code) before emitting
text into Markdown/Jinja output.
"""
from __future__ import annotations

LEGAL_BASIS_DE: dict[str, str] = {
    "art_6_1_a_consent":
        "Art. 6 Abs. 1 lit. a DSGVO (Einwilligung)",
    "art_6_1_b_contract":
        "Art. 6 Abs. 1 lit. b DSGVO (Vertragserfüllung)",
    "art_6_1_c_legal_obligation":
        "Art. 6 Abs. 1 lit. c DSGVO (rechtliche Verpflichtung)",
    "art_6_1_d_vital_interests":
        "Art. 6 Abs. 1 lit. d DSGVO (lebenswichtige Interessen)",
    "art_6_1_e_public_task":
        "Art. 6 Abs. 1 lit. e DSGVO (öffentliches Interesse)",
    "art_6_1_f_legitimate_interests":
        "Art. 6 Abs. 1 lit. f DSGVO (berechtigtes Interesse)",
    "art_9_2_special_category":
        "Art. 9 Abs. 2 DSGVO (besondere Kategorien)",
    "art_88_employment_context":
        "Art. 88 DSGVO i.V.m. § 26 BDSG (Beschäftigungskontext)",
}

LEGAL_BASIS_EN: dict[str, str] = {
    "art_6_1_a_consent":
        "Art. 6(1)(a) GDPR (Consent)",
    "art_6_1_b_contract":
        "Art. 6(1)(b) GDPR (Contractual necessity)",
    "art_6_1_c_legal_obligation":
        "Art. 6(1)(c) GDPR (Legal obligation)",
    "art_6_1_d_vital_interests":
        "Art. 6(1)(d) GDPR (Vital interests)",
    "art_6_1_e_public_task":
        "Art. 6(1)(e) GDPR (Public task)",
    "art_6_1_f_legitimate_interests":
        "Art. 6(1)(f) GDPR (Legitimate interests)",
    "art_9_2_special_category":
        "Art. 9(2) GDPR (Special category data)",
    "art_88_employment_context":
        "Art. 88 GDPR with national employment law",
}

DATA_SUBJECTS_DE: dict[str, str] = {
    "customers":        "Kunden",
    "end_users":        "Endnutzer",
    "employees":        "Beschäftigte",
    "website_visitors": "Website-Besucher",
    "applicants":       "Bewerber",
    "contractors":      "Auftragnehmer",
    "vendors":          "Lieferanten",
    "minors":           "Minderjährige",
    "patients":         "Patienten",
    "students":         "Studierende",
}

DATA_SUBJECTS_EN: dict[str, str] = {
    "customers":        "Customers",
    "end_users":        "End users",
    "employees":        "Employees",
    "website_visitors": "Website visitors",
    "applicants":       "Applicants",
    "contractors":      "Contractors",
    "vendors":          "Vendors",
    "minors":           "Minors",
    "patients":         "Patients",
    "students":         "Students",
}

_HR_CATEGORIES = frozenset({"hr_recruiting", "hr_management"})


def render_legal_basis(code: str | None, lang: str = "de") -> str:
    """Map a structured legal_basis code to human-readable text.

    Returns empty string for None/empty. Returns the raw code if unknown
    so unexpected values are visible for debugging instead of silently dropped.
    """
    if not code:
        return ""
    table = LEGAL_BASIS_DE if lang == "de" else LEGAL_BASIS_EN
    return table.get(code, code)


def render_data_subjects(subjects: list[str] | str | None, lang: str = "de") -> str:
    """Render a data_subjects value as human-readable DE phrase(s).

    Accepts list[str], single str, or None. Returns '' for empty/None.
    Unknown values are passed through as-is.
    """
    if subjects is None:
        return ""
    if isinstance(subjects, str):
        subjects = [subjects]
    if not subjects:
        return ""
    table = DATA_SUBJECTS_DE if lang == "de" else DATA_SUBJECTS_EN
    # Map FIRST, then dedup case-insensitive. Two distinct raw keys can collapse
    # to the same display label (e.g. "end_users" -> "Endnutzer" alongside a literal
    # "Endnutzer"); a pre-mapping dedup leaves those visible as duplicates.
    seen: dict[str, str] = {}
    for raw in subjects:
        label = str(table.get(raw, raw)).strip()
        key = label.lower()
        if key and key not in seen:
            seen[key] = label
    return ", ".join(seen.values())


def format_company_display_name(name: str, legal_form: str | None) -> str:
    """Avoid 'Rand Industries Inc. (Inc.)' when name already ends in the legal form token."""
    if not legal_form:
        return name
    norm_name = name.strip().lower().rstrip(".")
    norm_form = legal_form.strip().lower().rstrip(".")
    if norm_name.endswith(norm_form):
        return name
    return f"{name} ({legal_form})"


def derive_legal_basis_for_usecase(
    usecase: dict | None,
    services: list[dict],
    active_risks: set[str],
    lang: str = "de",
) -> str | None:
    """Best-effort legal_basis derivation for DSFA Step 1.

    Priority: 1) HR/employment context, 2) consent risk, 3) first service lb.
    Returns None when no basis can be derived.
    """
    if usecase and usecase.get("category") in _HR_CATEGORIES:
        return render_legal_basis("art_88_employment_context", lang)
    if "CONSENT_MANAGEMENT" in active_risks:
        return render_legal_basis("art_6_1_a_consent", lang)
    for s in services:
        lb = s.get("legal_basis")
        if lb:
            return render_legal_basis(lb, lang)
    return None
