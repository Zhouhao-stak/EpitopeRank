"""Full-text literature retrieval with a local BM25 passage index.

The existing literature skill returns titles plus abstract snippets. That is
enough to mention a paper, but not to answer "what did they actually measure?".
This module adds the missing half:

    Europe PMC search -> open-access full-text XML -> section chunks -> BM25
    -> ranked passages with PMID / PMCID / section provenance

Everything is cached on disk and every passage carries its identifier, so a
model answer can cite a passage instead of paraphrasing a title. When no full
text is available the abstract is indexed instead and flagged as such.
"""

from __future__ import annotations

import hashlib
import json
import math
import re
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from http.client import HTTPException
from pathlib import Path
from typing import Any, Callable, Iterable, Sequence
from urllib.error import HTTPError, URLError
from urllib.parse import quote_plus
from urllib.request import Request, urlopen

EUROPEPMC = "https://www.ebi.ac.uk/europepmc/webservices/rest/"
USER_AGENT = "EpitopeRank/1.0 (literature RAG)"
DEFAULT_TIMEOUT = 30.0
MAX_ARTICLE_CHARS = 400_000

_STOPWORDS = frozenset(
    "a an the and or of to in for on with by from is are was were be been being "
    "this that these those as at we our their its it can may might not no than "
    "using used use into between among also such which who whom what when where".split()
)
_TOKEN_RE = re.compile(r"[A-Za-z][A-Za-z0-9\-]{1,}")
#: XML declaration at the very start of a document (leading whitespace/BOM allowed).
_XML_DECL_RE = re.compile(r"^\s*<\?xml[^>]*\?>", re.IGNORECASE)
#: ``encoding="..."`` inside the XML declaration.
_XML_ENCODING_RE = re.compile(
    rb"<\?xml[^>]*encoding=[\"']([A-Za-z0-9._-]+)", re.IGNORECASE
)
#: Characters that are safe in a cache filename.
_SAFE_ID_RE = re.compile(r"[^A-Za-z0-9._-]+")


class RagError(RuntimeError):
    """Retrieval failed in a way the caller should surface."""


@dataclass
class Passage:
    article_id: str
    title: str
    section: str
    text: str
    score: float = 0.0
    source: str = "fulltext"

    def as_dict(self) -> dict[str, Any]:
        return {
            "article_id": self.article_id,
            "title": self.title,
            "section": self.section,
            "text": self.text,
            "score": round(self.score, 4),
            "source": self.source,
        }


def _cache_dir(explicit: str | Path | None) -> Path | None:
    if explicit:
        return Path(explicit).expanduser()
    try:
        from epitoperank.storage import default_runtime_root

        return default_runtime_root() / "literature_cache"
    except Exception:  # noqa: BLE001 - cache is optional
        return None


def _request(url: str, opener: Callable[..., Any], timeout: float) -> bytes:
    request = Request(url, headers={"User-Agent": USER_AGENT, "Accept": "*/*"})
    try:
        with opener(request, timeout=timeout) as response:
            return response.read(8_000_000)
    except HTTPError as error:
        raise RagError(f"Europe PMC HTTP {error.code}: {url}") from error
    except (URLError, TimeoutError, OSError, HTTPException) as error:
        raise RagError(f"Europe PMC unreachable: {error}") from error


def search_open_access(query: str, *, max_articles: int = 3,
                       opener: Callable[..., Any] = urlopen,
                       timeout: float = DEFAULT_TIMEOUT) -> list[dict[str, Any]]:
    """Search Europe PMC and return open-access records with abstracts."""
    text = (query or "").strip()
    if not text:
        return []
    scoped = f"({text}) AND OPEN_ACCESS:y"
    url = (f"{EUROPEPMC}search?query={quote_plus(scoped)}&format=json"
           f"&pageSize={max(1, min(max_articles * 2, 25))}&resultType=core")
    try:
        payload = json.loads(_request(url, opener, timeout).decode("utf-8", errors="replace"))
    except ValueError as error:
        raise RagError(f"Europe PMC returned invalid JSON: {error}") from error
    rows = ((payload.get("resultList") or {}).get("result") or []) if isinstance(payload, dict) else []
    results: list[dict[str, Any]] = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        results.append({
            "pmid": str(row.get("pmid") or ""),
            "pmcid": str(row.get("pmcid") or ""),
            "doi": str(row.get("doi") or ""),
            "title": str(row.get("title") or "").strip(),
            "journal": str((row.get("journalInfo") or {}).get("journal", {}).get("title") or ""),
            "year": str(row.get("pubYear") or ""),
            "abstract": str(row.get("abstractText") or "").strip(),
        })
        if len(results) >= max_articles:
            break
    return results


def _decode_xml(raw: bytes) -> str:
    """Decode JATS XML using the declared encoding, then UTF-8, then cp1252.

    Europe PMC normally serves UTF-8, but publisher-supplied full text can
    declare ``windows-1252`` (or ``ISO-8859-1``) and then contain bytes such as
    ``0x96`` for an en dash. Decoding those as UTF-8 raises, so the declared
    encoding must be tried first. A UTF-8 BOM is removed because
    ``ElementTree`` rejects a leading ``\\ufeff``.
    """
    match = _XML_ENCODING_RE.search(raw[:400])
    candidates: list[str] = []
    if match:
        declared = match.group(1).decode("ascii", "ignore").strip()
        if declared:
            candidates.append(declared)
    # ``utf-8-sig`` strips a BOM; plain ``utf-8`` is the common case.
    candidates += ["utf-8-sig", "utf-8", "cp1252"]
    seen: set[str] = set()
    for encoding in candidates:
        key = encoding.lower()
        if key in seen:
            continue
        seen.add(key)
        try:
            text = raw.decode(encoding)
        except (LookupError, UnicodeDecodeError):
            continue
        text = text.lstrip("\ufeff")
        # A cp1252 decode of a UTF-8 BOM yields the literal "ï»¿" prefix.
        if text.startswith("ï»¿"):
            text = text[3:]
        return text
    return raw.decode("utf-8", errors="replace").lstrip("\ufeff")


def fetch_fulltext_xml(pmcid: str, *, opener: Callable[..., Any] = urlopen,
                       timeout: float = DEFAULT_TIMEOUT,
                       cache_dir: str | Path | None = None,
                       force_refresh: bool = False) -> str:
    """Download and cache the JATS XML for one PMCID.

    The cache is UTF-8 text. ``force_refresh=True`` bypasses a healthy cache;
    an unreadable or empty cache file is treated as a miss and re-downloaded
    rather than crashing the caller.
    """
    identifier = (pmcid or "").strip()
    if not identifier:
        raise RagError("pmcid is required")
    directory = _cache_dir(cache_dir)
    safe_name = _SAFE_ID_RE.sub("_", identifier)
    path = directory / f"{safe_name}.xml" if directory else None
    if path and path.is_file() and not force_refresh:
        try:
            cached = path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            cached = ""
        # A cache written by an older decoder may be valid UTF-8 but full of
        # U+FFFD; refresh it instead of serving mojibake again.
        if cached.strip() and "\ufffd" not in cached:
            return cached
    url = f"{EUROPEPMC}{identifier}/fullTextXML"
    text = _decode_xml(_request(url, opener, timeout))
    if len(text) > MAX_ARTICLE_CHARS:
        text = text[:MAX_ARTICLE_CHARS]
    if path:
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(text, encoding="utf-8")
        except OSError:
            pass
    return text


def _local_name(tag: str) -> str:
    return tag.rsplit("}", 1)[-1] if "}" in tag else tag


def _text_of(element: ET.Element) -> str:
    parts: list[str] = []
    for node in element.iter():
        if _local_name(node.tag) in {"title", "p", "abstract", "label", "caption"}:
            if node.text:
                parts.append(node.text.strip())
    if not parts and element.text:
        parts.append(element.text.strip())
    return " ".join(part for part in parts if part).strip()


def extract_sections(xml_text: str) -> list[dict[str, str]]:
    """Extract ``{title, text}`` sections from JATS XML, with an abstract first.

    An XML declaration is stripped before parsing: ``ElementTree`` refuses a
    Unicode string that carries ``encoding="..."`` and publisher full text often
    does exactly that.
    """
    cleaned = _XML_DECL_RE.sub("", (xml_text or "").lstrip("\ufeff"), count=1).lstrip()
    try:
        root = ET.fromstring(cleaned)
    except ET.ParseError as error:
        raise RagError(f"cannot parse full-text XML: {error}") from error
    sections: list[dict[str, str]] = []
    for node in root.iter():
        name = _local_name(node.tag)
        if name == "abstract":
            text = _text_of(node)
            if text:
                sections.append({"title": "Abstract", "text": text})
        elif name == "body":
            for section in list(node):
                if _local_name(section.tag) != "sec":
                    continue
                title = ""
                paragraphs: list[str] = []
                for child in section:
                    child_name = _local_name(child.tag)
                    if child_name == "title":
                        title = "".join(child.itertext()).strip()
                    elif child_name == "p":
                        paragraph = "".join(child.itertext()).strip()
                        if paragraph:
                            paragraphs.append(paragraph)
                text = " ".join(paragraphs).strip()
                if text:
                    sections.append({"title": title or "Body", "text": text})
    if not sections:
        fallback = _text_of(root)
        if fallback:
            sections.append({"title": "Article", "text": fallback})
    return sections


def _stem(token: str) -> str:
    """Very small plural normaliser (no external NLP dependency)."""
    if len(token) > 4 and token.endswith("s") and not token.endswith(("ss", "us", "is", "as")):
        return token[:-1]
    return token


def tokenize(text: str) -> list[str]:
    tokens = []
    for token in _TOKEN_RE.findall(text or ""):
        lowered = token.lower()
        if lowered in _STOPWORDS:
            continue
        tokens.append(_stem(lowered))
    return tokens


def chunk_sections(sections: Sequence[dict[str, str]], *,
                   target_words: int = 170, max_chunks: int = 400) -> list[dict[str, str]]:
    """Split sections into overlapping-free word chunks that fit a context budget."""
    chunks: list[dict[str, str]] = []
    for section in sections:
        words = str(section.get("text") or "").split()
        if not words:
            continue
        step = max(40, int(target_words))
        for start in range(0, len(words), step):
            piece = " ".join(words[start:start + step]).strip()
            if len(piece.split()) < 8:
                continue
            chunks.append({"section": str(section.get("title") or "Body"), "text": piece})
            if len(chunks) >= max_chunks:
                return chunks
    return chunks


@dataclass
class BM25:
    """Minimal BM25 over already-tokenised chunks."""

    documents: list[dict[str, Any]]
    k1: float = 1.5
    b: float = 0.75
    _idf: dict[str, float] = field(default_factory=dict)
    _avgdl: float = 0.0

    def __post_init__(self) -> None:
        lengths = [len(doc.get("tokens") or []) for doc in self.documents]
        self._avgdl = sum(lengths) / len(lengths) if lengths else 0.0
        frequencies: dict[str, int] = {}
        for doc in self.documents:
            for token in set(doc.get("tokens") or []):
                frequencies[token] = frequencies.get(token, 0) + 1
        total = max(len(self.documents), 1)
        self._idf = {
            token: math.log(1 + (total - count + 0.5) / (count + 0.5))
            for token, count in frequencies.items()
        }

    def score(self, query_tokens: Sequence[str], document: dict[str, Any]) -> float:
        tokens = document.get("tokens") or []
        if not tokens:
            return 0.0
        counts: dict[str, int] = {}
        for token in tokens:
            counts[token] = counts.get(token, 0) + 1
        length = len(tokens)
        total = 0.0
        for token in query_tokens:
            frequency = counts.get(token)
            if not frequency:
                continue
            idf = self._idf.get(token, 0.0)
            denominator = frequency + self.k1 * (1 - self.b + self.b * length / (self._avgdl or 1.0))
            total += idf * frequency * (self.k1 + 1) / denominator
        return total

    def top(self, query: str, *, top_k: int = 6) -> list[dict[str, Any]]:
        query_tokens = tokenize(query)
        if not query_tokens:
            return []
        scored = [(self.score(query_tokens, doc), doc) for doc in self.documents]
        scored.sort(key=lambda item: -item[0])
        return [{**doc, "score": round(score, 4)}
                for score, doc in scored[:top_k] if score > 0]


def _snippet(text: str, query: str, *, limit: int = 420) -> str:
    tokens = set(tokenize(query))
    sentences = re.split(r"(?<=[.!?])\s+", text.strip())
    best = max(sentences, key=lambda sentence: sum(
        1 for token in set(tokenize(sentence)) if token in tokens), default=text)
    snippet = best.strip()
    return snippet if len(snippet) <= limit else snippet[:limit].rsplit(" ", 1)[0] + "…"


def search_passages(query: str, *, max_articles: int = 3, max_passages: int = 6,
                    opener: Callable[..., Any] = urlopen,
                    cache_dir: str | Path | None = None,
                    timeout: float = DEFAULT_TIMEOUT,
                    force_refresh: bool = False) -> dict[str, Any]:
    """Search open-access literature and return ranked full-text passages.

    An empty search result or an article with no usable text yields an empty
    ``passages`` list plus a ``note``; it is not an error. Full-text download
    failures are recorded in ``errors`` and the article's abstract is indexed
    instead.
    """
    articles = search_open_access(query, max_articles=max_articles, opener=opener, timeout=timeout)
    if not articles:
        return {
            "query": query,
            "articles": [],
            "passages": [],
            "errors": [],
            "note": "No open-access articles matched the query; no passages.",
        }
    documents: list[dict[str, Any]] = []
    used: list[dict[str, Any]] = []
    errors: list[str] = []
    for article in articles:
        title = article.get("title") or article.get("pmid") or article.get("pmcid") or "article"
        sections: list[dict[str, str]] = []
        source = "abstract"
        if article.get("pmcid"):
            try:
                xml_text = fetch_fulltext_xml(article["pmcid"], opener=opener,
                                              timeout=timeout, cache_dir=cache_dir,
                                              force_refresh=force_refresh)
                sections = extract_sections(xml_text)
                source = "fulltext"
            except RagError as error:
                errors.append(f"{article['pmcid']}: {error}")
        if not sections and article.get("abstract"):
            sections = [{"title": "Abstract", "text": article["abstract"]}]
        if not sections:
            continue
        identifier = article.get("pmid") or article.get("pmcid") or title
        for chunk in chunk_sections(sections):
            documents.append({
                "article_id": identifier,
                "title": title,
                "section": chunk["section"],
                "text": chunk["text"],
                "source": source,
                "tokens": tokenize(f"{title} {chunk['section']} {chunk['text']}"),
            })
        used.append({**article, "source": source, "sections": len(sections)})
    if not documents:
        return {
            "query": query,
            "articles": [],
            "passages": [],
            "errors": errors,
            "note": "Articles were found but no full text or abstract text was available.",
        }
    index = BM25(documents)
    ranked = index.top(query, top_k=max_passages)
    passages = [
        Passage(
            article_id=doc["article_id"], title=doc["title"], section=doc["section"],
            text=_snippet(doc["text"], query), score=doc["score"], source=doc["source"],
        ).as_dict()
        for doc in ranked
    ]
    return {
        "query": query,
        "articles": used,
        "passages": passages,
        "errors": errors,
        "note": "Passages are extractive quotes from open-access text; cite article_id.",
    }


def index_key(query: str, identifiers: Iterable[str]) -> str:
    """Stable identifier for reports/tests (not used for caching yet)."""
    blob = "|".join([query, *sorted(identifiers)])
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()[:16]
