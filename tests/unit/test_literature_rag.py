"""Tests for full-text literature retrieval and BM25 passage ranking."""

from __future__ import annotations

import json
from urllib.error import HTTPError

import pytest

from splicegaip.knowledge.literature_rag import (
    BM25,
    RagError,
    chunk_sections,
    extract_sections,
    fetch_fulltext_xml,
    search_passages,
    tokenize,
)

XML = """<?xml version="1.0"?>
<article xmlns:xlink="http://www.w3.org/1999/xlink">
  <front><article-meta><abstract>
    <p>Splice-derived neoantigens can arise from tumour-specific exon skipping events.</p>
  </abstract></article-meta></front>
  <body>
    <sec><title>Results</title>
      <p>We identified 123 exon skipping events in the tumour cohort and validated twelve
      candidates by RT-PCR. The junction-spanning peptides were predicted to bind HLA-A*02:01
      with strong affinity and were detectable by targeted mass spectrometry in three samples.</p>
    </sec>
    <sec><title>Methods</title>
      <p>Samples were processed with a standard ribosomal depletion protocol and sequenced on a
      short-read platform. Reads were aligned with STAR and splicing events were quantified with
      rMATS using the standard junction counts workflow described previously.</p>
    </sec>
  </body>
</article>
"""

SEARCH = {
    "resultList": {"result": [{
        "pmid": "12345", "pmcid": "PMC12345", "doi": "10.1/x",
        "title": "Splice neoantigens in tumours",
        "pubYear": "2024",
        "journalInfo": {"journal": {"title": "Test Journal"}},
        "abstractText": "Splice-derived neoantigens can arise from tumour-specific exon skipping.",
    }]}
}


class FakeResponse:
    def __init__(self, payload: bytes) -> None:
        self.payload = payload

    def read(self, _size: int = -1) -> bytes:
        return self.payload

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False


def make_opener(xml: str = XML, search: dict | None = None, fail_fulltext: bool = False):
    def opener(request, timeout: float | None = None):
        url = getattr(request, "full_url", str(request))
        if "search?" in url:
            return FakeResponse(json.dumps(search or SEARCH).encode())
        if "fullTextXML" in url:
            if fail_fulltext:
                return FakeResponse(b"not xml at all")
            return FakeResponse(xml.encode())
        raise AssertionError(f"unexpected url: {url}")
    return opener


def test_extract_sections_reads_abstract_and_body() -> None:
    sections = extract_sections(XML)
    titles = [section["title"] for section in sections]
    assert "Abstract" in titles
    assert "Results" in titles
    assert "Methods" in titles
    assert any("RT-PCR" in section["text"] for section in sections)


def test_extract_sections_rejects_bad_xml() -> None:
    with pytest.raises(RagError):
        extract_sections("<article><body>")


def test_tokenize_drops_stopwords() -> None:
    tokens = tokenize("The exon skipping event is in the tumour")
    assert "the" not in tokens
    assert "exon" in tokens
    assert "skipping" in tokens


def test_chunk_sections_splits_long_text() -> None:
    text = " ".join(["word"] * 400)
    chunks = chunk_sections([{"title": "Body", "text": text}], target_words=100)
    assert len(chunks) >= 3
    assert all(chunk["section"] == "Body" for chunk in chunks)


def test_bm25_ranks_relevant_chunk_first() -> None:
    documents = [
        {"id": "a", "tokens": tokenize("exon skipping neoantigen tumour validation")},
        {"id": "b", "tokens": tokenize("ribosomal depletion sequencing alignment protocol")},
        {"id": "c", "tokens": tokenize("kinase inhibitor resistance pathway")},
    ]
    index = BM25(documents)
    ranked = index.top("exon skipping neoantigen", top_k=2)
    assert ranked
    assert ranked[0]["id"] == "a"


def test_search_passages_returns_fulltext_passages(tmp_path) -> None:
    payload = search_passages("exon skipping neoantigen", opener=make_opener(),
                              cache_dir=tmp_path, max_articles=1, max_passages=3)
    assert payload["articles"]
    assert payload["passages"]
    first = payload["passages"][0]
    assert first["article_id"] == "12345"
    assert first["source"] == "fulltext"
    assert "section" in first


def test_search_passages_falls_back_to_abstract(tmp_path) -> None:
    payload = search_passages("neoantigen", opener=make_opener(fail_fulltext=True),
                              cache_dir=tmp_path, max_articles=1, max_passages=2)
    assert payload["passages"]
    assert payload["passages"][0]["source"] == "abstract"
    assert payload["errors"]


def test_fulltext_cache_avoids_second_download(tmp_path) -> None:
    calls = {"n": 0}

    def opener(request, timeout=None):
        calls["n"] += 1
        return FakeResponse(XML.encode())

    first = fetch_fulltext_xml("PMC12345", opener=opener, cache_dir=tmp_path)
    second = fetch_fulltext_xml("PMC12345", opener=opener, cache_dir=tmp_path)
    assert first == second
    assert calls["n"] == 1


CP1252_XML = (
    '<?xml version="1.0" encoding="windows-1252"?>\n'
    "<article><body><sec><title>Results</title>"
    "<p>exon–exon junction spans the tumour-specific event.</p>"
    "</sec></body></article>"
).encode("cp1252")


def test_declared_cp1252_is_decoded_without_replacement_glyphs(tmp_path) -> None:
    assert b"\x96" in CP1252_XML  # cp1252 en dash, invalid as standalone UTF-8

    def opener(request, timeout=None):
        return FakeResponse(CP1252_XML)

    text = fetch_fulltext_xml("PMC1252", opener=opener, cache_dir=tmp_path)
    assert "exon–exon" in text
    assert "\ufffd" not in text
    # A Unicode string carrying an encoding declaration must still parse.
    sections = extract_sections(text)
    assert any("exon–exon" in section["text"] for section in sections)


def test_force_refresh_bypasses_a_healthy_cache(tmp_path) -> None:
    calls = {"n": 0}

    def opener(request, timeout=None):
        calls["n"] += 1
        return FakeResponse(XML.encode())

    fetch_fulltext_xml("PMC1", opener=opener, cache_dir=tmp_path)
    fetch_fulltext_xml("PMC1", opener=opener, cache_dir=tmp_path)
    assert calls["n"] == 1
    fetch_fulltext_xml("PMC1", opener=opener, cache_dir=tmp_path, force_refresh=True)
    assert calls["n"] == 2


def test_corrupt_cache_is_redownloaded(tmp_path) -> None:
    (tmp_path / "PMC9.xml").write_bytes(b"\xff\xfe\x00broken utf-8")
    calls = {"n": 0}

    def opener(request, timeout=None):
        calls["n"] += 1
        return FakeResponse(XML.encode())

    text = fetch_fulltext_xml("PMC9", opener=opener, cache_dir=tmp_path)
    assert calls["n"] == 1
    assert "Results" in text


def test_cache_is_read_as_utf8(tmp_path) -> None:
    (tmp_path / "PMC7.xml").write_text(
        "<article><body><p>外显子–外显子连接</p></body></article>", encoding="utf-8"
    )

    def opener(request, timeout=None):
        raise AssertionError("a healthy cache must not trigger a download")

    text = fetch_fulltext_xml("PMC7", opener=opener, cache_dir=tmp_path)
    assert "外显子–外显子" in text


def test_cache_with_replacement_glyph_is_redownloaded(tmp_path) -> None:
    (tmp_path / "PMC8.xml").write_text("<article>exon\ufffd\ufffdexon</article>", encoding="utf-8")
    calls = {"n": 0}

    def opener(request, timeout=None):
        calls["n"] += 1
        return FakeResponse(XML.encode())

    text = fetch_fulltext_xml("PMC8", opener=opener, cache_dir=tmp_path)
    assert calls["n"] == 1
    assert "\ufffd" not in text


def test_fulltext_http_error_raises_and_search_falls_back_to_abstract(tmp_path) -> None:
    def opener(request, timeout=None):
        url = getattr(request, "full_url", str(request))
        if "search?" in url:
            return FakeResponse(json.dumps(SEARCH).encode())
        raise HTTPError(url, 503, "unavailable", {}, None)

    with pytest.raises(RagError):
        fetch_fulltext_xml("PMC12345", opener=opener, cache_dir=tmp_path)

    payload = search_passages("neoantigen", opener=opener, cache_dir=tmp_path,
                              max_articles=1, max_passages=2)
    assert payload["passages"]
    assert payload["passages"][0]["source"] == "abstract"
    assert payload["errors"]


def test_empty_search_returns_empty_payload(tmp_path) -> None:
    def opener(request, timeout=None):
        return FakeResponse(json.dumps({"resultList": {"result": []}}).encode())

    payload = search_passages("no such topic", opener=opener, max_articles=2)
    assert payload["query"] == "no such topic"
    assert payload["articles"] == []
    assert payload["passages"] == []
    assert payload["errors"] == []
    assert "No open-access articles" in payload["note"]


def test_articles_without_text_return_empty_passages(tmp_path) -> None:
    empty = {"resultList": {"result": [{
        "pmid": "999", "title": "No abstract", "abstractText": "",
    }]}}

    def opener(request, timeout=None):
        return FakeResponse(json.dumps(empty).encode())

    payload = search_passages("anything", opener=opener, max_articles=1)
    assert payload["passages"] == []
    assert payload["errors"] == []
    assert "no full text or abstract text" in payload["note"]


def test_search_passages_force_refresh_redownloads_fulltext(tmp_path) -> None:
    calls = {"n": 0}

    def opener(request, timeout=None):
        url = getattr(request, "full_url", str(request))
        if "search?" in url:
            return FakeResponse(json.dumps(SEARCH).encode())
        calls["n"] += 1
        return FakeResponse(XML.encode())

    search_passages("neoantigen", opener=opener, cache_dir=tmp_path, max_articles=1)
    search_passages("neoantigen", opener=opener, cache_dir=tmp_path, max_articles=1)
    assert calls["n"] == 1
    search_passages("neoantigen", opener=opener, cache_dir=tmp_path, max_articles=1,
                    force_refresh=True)
    assert calls["n"] == 2


def test_bm25_plural_normalisation() -> None:
    assert tokenize("neoantigens") == tokenize("neoantigen") == ["neoantigen"]
    documents = [{"id": "a", "tokens": tokenize("splice neoantigens tumour cohort")}]
    ranked = BM25(documents).top("neoantigen", top_k=1)
    assert ranked
    assert ranked[0]["id"] == "a"
