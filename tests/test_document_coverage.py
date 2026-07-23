"""ADR-075: Coverage-Matrix fundament — FieldSource enum + _field_with_source helper."""
from src.agents.document_architect import FieldSource, _field_with_source


def test_field_source_values_match_adr_075():
    """The six source labels from ADR-075 § 2 must be 1:1 in the enum."""
    assert {s.value for s in FieldSource} == {"CODE", "PII", "SVC", "UC", "Q", "STD"}


def test_field_with_source_shape_code_evidence():
    out = _field_with_source("bcrypt", FieldSource.CODE, evidence="package.json:23")
    assert out == {
        "value":      "bcrypt",
        "source":     "CODE",
        "evidence":   "package.json:23",
        "confidence": None,
    }


def test_field_with_source_nullable_value_still_traceable():
    """Missing value stays None, source + evidence remain inspectable."""
    out = _field_with_source(None, FieldSource.Q)
    assert out["value"] is None
    assert out["source"] == "Q"
    assert out["evidence"] is None
    assert out["confidence"] is None


def test_field_with_source_accepts_bool_and_numeric():
    """Template fields aren't always strings — bool/int/float must pass through."""
    b = _field_with_source(True, FieldSource.CODE, evidence="nginx.conf:5")
    assert b["value"] is True
    i = _field_with_source(365, FieldSource.Q)
    assert i["value"] == 365
    f = _field_with_source(0.92, FieldSource.UC, confidence=0.92)
    assert f["value"] == 0.92
    assert f["confidence"] == 0.92
