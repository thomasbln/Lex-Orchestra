"""ADR-110: payment integration-mode → rendered data-category wording.

Single source of the verbatim data-category wording each integration mode
produces in the AVV / VVT / SCC documents, so the three documents generated from
one scan run never diverge. The mode itself is derived in the scanner
(``src.workflow.main._derive_stripe_integration_mode``) and attached to
``graph_result["services"][i]["integration_mode"]`` (ADR-110 Phase 2). The
builders call :func:`resolve_payment_categories` to turn that signal into either
override categories or a gap.

The graph data model is untouched — this is a render-time override only. The
``data_categories`` string on the ``Service`` node still says "Kreditkartendaten";
the document may say less, based on a signal the graph does not hold. That
divergence is the deliberate, temporary trade ADR-110 records (closed by the
Ebene-3 DataCategory-node work).
"""
from __future__ import annotations

# The three integration modes. These literals must match the values produced by
# src.workflow.main._derive_stripe_integration_mode (single vocabulary; a test
# asserts they agree).
PAYMENT_MODE_DELEGATED = "delegated"
PAYMENT_MODE_MERCHANT_SIDE = "merchant_side_possible"
PAYMENT_MODE_UNKNOWN = "unknown"

# Gap id emitted at the data-category cell when the mode is `unknown`.
PAYMENT_MODE_UNKNOWN_GAP_ID = "payment_integration_mode_unknown"

# ADR-110 plan "Festgelegter Doc-Wortlaut" — verbatim, identical across the three
# documents. Each is a single category entry (a sentence), not a category list.
_DELEGATED_TEXT = (
    "Zahlungs-Token, Transaktions- und Rechnungsdaten. Kartendaten werden direkt "
    "vom Zahlungsdienstleister verarbeitet, nicht vom Verantwortlichen."
)
_MERCHANT_SIDE_TEXT = (
    "Zahlungsdaten, Transaktionsdaten, Rechnungsadressen. [Hinweis] Integrationsart "
    "nicht verifiziert: bei serverseitiger Integration können auch Kartendaten "
    "verarbeitet werden. Bitte prüfen — bei Elements/Checkout entfällt dies."
)
# B-2/L7 (EN package): lex-authored EN twins of the ADR-110 verbatim wording.
_DELEGATED_TEXT_EN = (
    "Payment tokens, transaction and invoice data. Card data is processed "
    "directly by the payment service provider, not by the controller."
)
_MERCHANT_SIDE_TEXT_EN = (
    "Payment data, transaction data, billing addresses. [Note] Integration mode "
    "not verified: with a server-side integration, card data may also be "
    "processed. Please verify — this does not apply to Elements/Checkout."
)


def integration_mode_note(service: dict) -> str | None:
    """ADR-111: the logbook note that witnesses the ADR-110 graph↔document split.

    Returns ``None`` when the service carries no payment mode (most services).
    When a mode is present, the document's data categories are *no longer a pure
    function of the graph node* — the note records that divergence machine-readably,
    exactly the witness ADR-110's Consequences point to. ``unknown`` downgraded the
    cell to a gap; ``delegated`` / ``merchant_side_possible`` overrode the static
    ``data_categories`` string.
    """
    mode = service.get("integration_mode")
    if not mode:
        return None
    if mode == PAYMENT_MODE_UNKNOWN:
        return f"data_categories rendered as gap: integration_mode={mode} (ADR-110)"
    return (
        f"data_categories overridden by integration_mode={mode} (ADR-110); "
        f"graph data_categories string not applied"
    )


def resolve_payment_categories(service: dict, lang: str = "de") -> tuple[list[str] | None, bool]:
    """ADR-110: decide the data-category rendering for one service.

    Returns ``(override, is_gap)``:
        * ``override`` is a ``list[str]`` that **replaces** the service's own
          ``data_categories`` — set for ``delegated`` and ``merchant_side_possible``.
        * ``is_gap`` is ``True`` only for ``unknown`` — the caller must render a
          gap marker (``inline_gap_marker(PAYMENT_MODE_UNKNOWN_GAP_ID)``) at the
          categories cell instead of any text.
        * ``(None, False)`` means no payment-mode signal — the caller keeps the
          service's own ``data_categories`` unchanged (non-PSP services, or a PSP
          without a derived mode).
    """
    mode = service.get("integration_mode")
    if mode == PAYMENT_MODE_DELEGATED:
        return [_DELEGATED_TEXT_EN if lang == "en" else _DELEGATED_TEXT], False
    if mode == PAYMENT_MODE_MERCHANT_SIDE:
        return [_MERCHANT_SIDE_TEXT_EN if lang == "en" else _MERCHANT_SIDE_TEXT], False
    if mode == PAYMENT_MODE_UNKNOWN:
        return None, True
    return None, False
