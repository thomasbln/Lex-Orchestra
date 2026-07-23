"""ADR-115 A1: render the EDPB-backed PSP controller/processor role.

The role lives graph-resident on
``(:Service)-[:ACTS_AS {role, role_source}]->(:ProcessingActivity {id:'payment_processing'})``
(seeded by ``seed_psp_roles``) and is read into ``graph_result["services"][i]`` as
``acts_as_role`` / ``acts_as_role_source`` by ``GraphClient`` (Q_META). This module
turns that signal into the role line shared *verbatim* by the AVV and VVT builders,
so the two documents generated from one scan never diverge.

Role semantics (legal-advisor gate 2026-06-03, EDPB 07/2020): a pure PSP is
``controller`` for ``payment_processing`` independent of ``integration_mode`` — the
mode (delegated/merchant_side) only governs PCI-DSS / AVV scope, never the GDPR role
(see ``payment_mode.py``). ``special_case`` (PayPal/Klarna) renders an honest
"separate legal review needed" marker carrying the seeded reasoning — never empty,
and deliberately NOT the generic ``inline_gap_marker`` ("Pflichtangabe fehlt"), which
would mislabel a sourced edge case as a missing field.
"""
from __future__ import annotations

from dataclasses import dataclass

ROLE_SPECIAL_CASE = "special_case"

# role value -> German label for the non-special roles. special_case has no label
# (it renders the honest review-needed marker instead).
_ROLE_LABELS = {
    "controller": "Verantwortlicher",
    "processor": "Auftragsverarbeiter",
    "joint_controller": "Gemeinsam Verantwortlicher",
}

_ROLE_LABELS_EN = {
    "controller": "Controller",
    "processor": "Processor",
    "joint_controller": "Joint controller",
}


@dataclass
class PSPRoleLine:
    """One rendered role statement for a service that carries an ACTS_AS role."""
    service_name: str
    role: str                  # controller | processor | joint_controller | special_case
    role_label: str | None     # German label for non-special roles; None for special_case
    role_source: str           # EDPB citation (roles) or the special-case reasoning


def psp_role_line(service: dict, lang: str = "de") -> PSPRoleLine | None:
    """Return the role line for a service that carries an ACTS_AS role, else None.

    Non-PSP services (no ``acts_as_role``) return ``None`` — the controller/processor
    question does not arise for them, so nothing is rendered (this is not a gap).
    """
    role = service.get("acts_as_role")
    if not role:
        return None
    # B-2/L9 (EN package): language-pure source citation — EN picks the seeded
    # _en twin; a missing twin renders the honest N1 pending marker, never
    # silent German in the EN document.
    if lang == "en":
        role_source = (
            service.get("acts_as_role_source_en")
            or ("☐ translation pending (German version exists)"
                if service.get("acts_as_role_source") else "")
        )
    else:
        role_source = service.get("acts_as_role_source") or ""
    return PSPRoleLine(
        service_name=service.get("name", ""),
        role=role,
        role_label=(_ROLE_LABELS_EN if lang == "en" else _ROLE_LABELS).get(role),
        role_source=role_source,
    )
