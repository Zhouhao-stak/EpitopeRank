"""PubMed literature retrieval.

Adapted from BioGAIP's ``bioGen/pubmed`` module (pymed based). Retrieval
is best-effort and offline-safe: when the network or the ``pymed``
package is unavailable, the knowledge service silently degrades to the
bundled knowledge base instead of failing the analysis.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from epitoperank.knowledge.base import KnowledgeRecord


@dataclass(frozen=True)
class PubMedArticle:
    """One retrieved article."""

    title: str
    abstract: str
    pmid: str
    journal: str = ""
    year: str = ""

    def summary(self, max_chars: int = 600) -> str:
        """拼成标题、期刊年份、截断后的摘要与 PMID 组成的一段文本。"""
        abstract = self.abstract.strip()
        if len(abstract) > max_chars:
            abstract = abstract[: max_chars - 3].rstrip() + "..."
        parts = [f"{self.title}"]
        if self.journal or self.year:
            parts.append(f"({self.journal} {self.year}).".replace(" )", ")"))
        if abstract:
            parts.append(abstract)
        parts.append(f"PMID {self.pmid}")
        return " ".join(parts)


class PubMedRetriever:
    """Thin wrapper around pymed with graceful degradation.

    Two safeguards keep the pipeline fast when NCBI is unreachable (common
    from some networks): a one-time connectivity pre-check and a per-query
    timeout enforced through a worker thread.
    """

    #: NCBI eutils endpoint used for the connectivity pre-check.
    _EUTILS_URL = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/einfo.fcgi"

    def __init__(
        self,
        email: str = "epitoperank@example.org",
        tool: str = "epitoperank",
        query_timeout: float = 6.0,
        connect_timeout: float = 4.0,
    ) -> None:
        """保存邮箱、工具名与查询/连接超时；pymed 导入与 NCBI 连通性均在其后才探测。"""
        self._email = email
        self._tool = tool
        self._query_timeout = query_timeout
        self._connect_timeout = connect_timeout
        self._client: Any = None
        self._available: bool | None = None
        self._reachable: bool | None = None

    @property
    # 中文备注：知识库：辅助处理available（参数：无）
    def available(self) -> bool:
        """Whether pymed is importable AND NCBI answered the pre-check."""
        if self._available is None:
            try:
                from pymed import PubMed  # noqa: F401
            except Exception:
                self._available = False
                return False
            self._available = self._check_reachable()
        return self._available

    def _check_reachable(self) -> bool:
        """请求 NCBI eutils 做一次连通性预检并缓存结果，任何异常都视为不可达。"""
        if self._reachable is not None:
            return self._reachable
        try:
            import requests

            response = requests.get(self._EUTILS_URL, timeout=self._connect_timeout)
            self._reachable = response.status_code == 200
        except Exception:
            self._reachable = False
        return self._reachable

    def _ensure_client(self) -> Any:
        """延迟创建 pymed 客户端；pymed 未安装时导入错误会向上抛出。"""
        if self._client is None:
            from pymed import PubMed

            self._client = PubMed(tool=self._tool, email=self._email)
        return self._client

    def _query(self, keyword: str, max_results: int) -> list[Any]:
        """用 pymed 执行一次关键词检索并返回结果列表（联网调用）。"""
        client = self._ensure_client()
        return list(client.query(keyword, max_results=max_results) or [])

    # 中文备注：知识库：检索search（参数：keyword、max_results）
    def search(self, keyword: str, max_results: int = 5) -> list[PubMedArticle]:
        """Search PubMed; returns an empty list on any failure or timeout."""
        if not self.available:
            return []
        try:
            from concurrent.futures import ThreadPoolExecutor, TimeoutError as FutureTimeout

            with ThreadPoolExecutor(max_workers=1) as executor:
                future = executor.submit(self._query, keyword, max_results)
                try:
                    results = future.result(timeout=self._query_timeout)
                except FutureTimeout:
                    return []
        except Exception:
            return []
        articles: list[PubMedArticle] = []
        for article in results:
            articles.append(
                PubMedArticle(
                    title=str(getattr(article, "title", "") or "").strip(),
                    abstract=str(getattr(article, "abstract", "") or "").strip(),
                    pmid=str(getattr(article, "pubmed_id", "") or ""),
                    journal=str(getattr(article, "journal", "") or ""),
                    year=str(getattr(article, "publication_date", "") or "")[:4],
                )
            )
        return articles

    # 中文备注：知识库：检索基因（参数：genes、max_per_gene）
    def search_for_genes(self, genes: list[str], max_per_gene: int = 2) -> dict[str, list[PubMedArticle]]:
        """Search alternative-splicing literature for each gene."""
        found: dict[str, list[PubMedArticle]] = {}
        for gene in genes:
            articles = self.search(f"{gene} alternative splicing", max_results=max_per_gene)
            if articles:
                found[gene] = articles
        return found


# 中文备注：知识库：辅助处理记录基因（参数：genes）
def records_for_genes(genes: list[str]) -> list[KnowledgeRecord]:
    """Convenience re-export of the bundled lookup used by tools."""
    from epitoperank.knowledge.base import lookup_genes

    return lookup_genes(genes)
