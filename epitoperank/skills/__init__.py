"""Splicing-specific skills for EpitopeRank.

Skills are high-level analysis capabilities that combine:
- MCP tool calls (external databases, literature search)
- Local analysis (delta PSI computation, event classification)
- AI interpretation (clinical significance, functional impact)

Each skill is a self-contained unit that can be invoked from the UI
or programmatically from the agent team.
"""

from epitoperank.skills.gene_annotation import GeneAnnotationSkill
from epitoperank.skills.literature_search import LiteratureSearchSkill
from epitoperank.skills.pathway_enrichment import PathwayEnrichmentSkill
from epitoperank.skills.splice_interpretation import SpliceInterpretationSkill

__all__ = [
    "GeneAnnotationSkill",
    "LiteratureSearchSkill",
    "PathwayEnrichmentSkill",
    "SpliceInterpretationSkill",
]
