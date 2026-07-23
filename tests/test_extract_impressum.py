"""Firecrawl impressum extraction — break on extraction success, not scrape success.

A thin /legal marketing page used to win the scrape race (first response with
>100 chars broke the loop) and mask a real /impressum later in the candidate
list. All dry: httpx is faked, no Firecrawl credits are spent.
"""

import asyncio

import pytest

import src.interface.approve_api as api


# >100 chars, matches none of the extraction patterns. Deliberately avoids
# ag/ug/gmbh/inc/ltd SUBSTRINGS anywhere: the company_name fallback regex runs
# IGNORECASE, so a line containing "page" or "usage" false-positives as an AG
# company (pre-existing extraction wart, tracked as post-release regex item).
MARKETING_TEXT = (
    "Welcome to our terms overview. Here we describe rules of service, "
    "acceptable use policies, and further notes for this website. "
    "Nothing about the firm itself lives here."
)

IMPRESSUM_TEXT = (
    "Impressum\n"
    "Firma: Acme Solutions GmbH\n"
    "Musterstraße 12\n"
    "10115 Berlin\n"
    "Vertreten durch: Max Mustermann\n"
    "E-Mail: info@acme.test\n"
    "Weitere Angaben nach § 5 DDG folgen hier."
)


class FakeResponse:
    def __init__(self, status_code: int, markdown: str = ""):
        self.status_code = status_code
        self._markdown = markdown

    def json(self):
        return {"data": {"markdown": self._markdown}}


class FakeAsyncClient:
    """Routes Firecrawl scrape calls by requested URL; records call order."""

    routing: dict = {}
    calls: list = []

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        return False

    async def post(self, url, headers=None, json=None, timeout=None):
        requested = json["url"]
        FakeAsyncClient.calls.append(requested)
        return FakeAsyncClient.routing.get(requested, FakeResponse(404))


@pytest.fixture
def firecrawl(monkeypatch):
    monkeypatch.setattr(api, "FIRECRAWL_API_KEY", "fc-test")
    monkeypatch.setattr(api.httpx, "AsyncClient", FakeAsyncClient)
    FakeAsyncClient.routing = {}
    FakeAsyncClient.calls = []
    return FakeAsyncClient


def _extract(url: str) -> dict:
    return asyncio.run(api.extract_impressum({"url": url}))


def test_zero_field_scrape_does_not_mask_later_impressum(firecrawl):
    """The Done-When: /legal-notice scrapes fine but extracts 0 fields — the
    loop must keep going and find the real impressum on a later candidate."""
    firecrawl.routing = {
        "https://acme.test/legal-notice": FakeResponse(200, MARKETING_TEXT),
        "https://acme.test/legal": FakeResponse(200, IMPRESSUM_TEXT),
    }

    result = _extract("https://acme.test")

    assert result["success"] is True
    assert result["source_url"] == "https://acme.test/legal"
    assert "GmbH" in result["fields"]["company_name"]
    assert result["fields"]["contact_email"] == "info@acme.test"


def test_first_candidate_with_fields_wins_without_extra_calls(firecrawl):
    firecrawl.routing = {
        "https://acme.test/impressum": FakeResponse(200, IMPRESSUM_TEXT),
    }

    result = _extract("https://acme.test")

    assert result["success"] is True
    assert result["source_url"] == "https://acme.test/impressum"
    assert firecrawl.calls == ["https://acme.test/impressum"], \
        "must break on extraction success — no further scrape spend"


def test_nothing_scrapes_is_an_honest_no_impressum_found(firecrawl):
    firecrawl.routing = {}  # every candidate 404s

    result = _extract("https://acme.test")

    assert result == {"success": False, "error": "no_impressum_found", "fields": {}}


def test_scraped_but_nothing_extractable_is_not_no_impressum_found(firecrawl):
    """Readable pages with 0 extractable fields → success with empty fields
    (UI: 'No fields extracted'), never the false 'no impressum found'."""
    firecrawl.routing = {
        "https://acme.test/legal-notice": FakeResponse(200, MARKETING_TEXT),
    }

    result = _extract("https://acme.test")

    assert result["success"] is True
    assert result["fields"] == {}
    assert result["source_url"] == "https://acme.test/legal-notice"


def test_without_api_key_reports_not_configured(monkeypatch):
    monkeypatch.setattr(api, "FIRECRAWL_API_KEY", None)

    result = _extract("https://acme.test")

    assert result == {"success": False, "error": "not_configured", "fields": {}}
