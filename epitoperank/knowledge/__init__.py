"""Knowledge subpackage: RAG literature evidence and PubMed retrieval."""

from epitoperank.knowledge.base import (
    BUNDLED_GENE_KNOWLEDGE,
    KnowledgeRecord,
    known_genes,
    lookup_genes,
)
from epitoperank.knowledge.pubmed import PubMedArticle, PubMedRetriever
from epitoperank.knowledge.rag import Evidence, KnowledgeService

__all__ = [
    "BUNDLED_GENE_KNOWLEDGE",
    "Evidence",
    "KnowledgeRecord",
    "KnowledgeService",
    "PubMedArticle",
    "PubMedRetriever",
    "known_genes",
    "lookup_genes",
]
