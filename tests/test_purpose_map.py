from src.documents.purpose_map import (
    default_purpose,
    resolve_processing_purpose,
)


def test_graph_value_wins_and_is_not_inferred():
    purpose, inferred = resolve_processing_purpose(
        "Zahlungsabwicklung, Betrugsprävention", "payment"
    )
    assert purpose == "Zahlungsabwicklung, Betrugsprävention"
    assert inferred is False


def test_empty_graph_value_falls_back_to_category_and_is_inferred():
    purpose, inferred = resolve_processing_purpose(None, "payment")
    assert purpose == "Zahlungsabwicklung und Transaktionsverarbeitung"
    assert inferred is True


def test_blank_graph_value_treated_as_empty():
    purpose, inferred = resolve_processing_purpose("   ", "nosql_db")
    assert purpose == "NoSQL-Datenspeicherung und -verwaltung"
    assert inferred is True


def test_unknown_category_uses_catch_all_still_inferred():
    purpose, inferred = resolve_processing_purpose(None, "totally_unknown_cat")
    assert purpose == "Leistungserbringung gemäß Hauptvertrag"
    assert inferred is True


def test_no_graph_no_category_uses_catch_all_inferred():
    purpose, inferred = resolve_processing_purpose(None, None)
    assert purpose == "Leistungserbringung gemäß Hauptvertrag"
    assert inferred is True


def test_default_purpose_known_categories():
    assert default_purpose("analytics") == "Nutzungsanalyse, Tracking und Monitoring"
    assert default_purpose("nosql_db") == "NoSQL-Datenspeicherung und -verwaltung"
