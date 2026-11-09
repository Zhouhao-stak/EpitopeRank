"""Tool registry.

Binds the tool functions to a :class:`RunContext` through explicit
closures (AutoGen's ``FunctionTool`` derives its JSON schema from the
function signature, so wrappers must keep a real signature) and exposes
them as AutoGen ``FunctionTool`` objects, mirroring BioGAIP's tool
registration pattern.
"""

from __future__ import annotations

from autogen_core.tools import FunctionTool

from epitoperank.tools.context import RunContext


# 中文备注：工具层：构建工具（参数：context）
def build_tools(context: RunContext) -> dict[str, FunctionTool]:
    """Build the full tool set bound to ``context``."""
    from epitoperank.tools.analysis_tools import (
        filter_significant_events as _filter_events,
        rank_candidates as _rank_candidates,
        run_enrichment as _run_enrichment,
    )
    from epitoperank.tools.data_tools import summarize_dataset as _summarize_dataset
    from epitoperank.tools.knowledge_tools import (
        collect_literature_evidence as _collect_evidence,
        interpret_candidates as _interpret_candidates,
    )
    from epitoperank.tools.report_tools import generate_report as _generate_report
    from epitoperank.tools.viz_tools import generate_figures as _generate_figures

    # 中文备注：把数据集概览写进 Methods（参数：无）
    def summarize_dataset() -> str:
        """Return a compact summary of the loaded dataset (events, samples, groups, validation)."""
        return _summarize_dataset(context)

    # 中文备注：按 FDR 与 |dPSI| 筛选显著剪接事件（参数：fdr_threshold、delta_psi_threshold）
    def filter_significant_events(
        fdr_threshold: float | None = None,
        delta_psi_threshold: float | None = None,
    ) -> str:
        """Filter AS events by FDR and |delta PSI| with quality gating. Defaults come from the platform configuration."""
        return _filter_events(context, fdr_threshold, delta_psi_threshold)

    # 中文备注：按四分量综合得分排序候选事件（参数：top_n）
    def rank_candidates(top_n: int | None = None) -> str:
        """Rank significant events by the composite candidate score (significance, effect size, biology, literature)."""
        return _rank_candidates(context, top_n)

    # 中文备注：GO/KEGG 富集分析（本地）（参数：alpha）
    def run_enrichment(alpha: float | None = None) -> str:
        """Run GO/KEGG over-representation analysis for candidate genes using the supplied annotation table."""
        return _run_enrichment(context, alpha)

    # 中文备注：生成整套发表级图表（参数：output_dir）
    def generate_figures(output_dir: str | None = None) -> str:
        """Generate the publication figure set (volcano, event composition, PSI heatmap, PSI distribution, candidate ranking, enrichment) as PNG and SVG."""
        return _generate_figures(context, output_dir)

    # 中文备注：为候选基因收集文献证据（参数：genes、max_per_gene）
    def collect_literature_evidence(genes: list[str] | None = None, max_per_gene: int = 2) -> str:
        """Collect literature evidence for candidate genes from the curated knowledge base, PubMed and the vector store."""
        return _collect_evidence(context, genes, max_per_gene)

    # 中文备注：生成有证据支撑的生物学解读（参数：无）
    def interpret_candidates() -> str:
        """Produce the evidence-grounded biological interpretation of the top candidate events."""
        return _interpret_candidates(context)

    # 中文备注：写出 HTML/PDF 报告（参数：output_dir）
    def generate_report(output_dir: str | None = None) -> str:
        """Generate the scientific report (Summary/Methods/Results/Figures/Interpretation/References) in HTML and PDF."""
        return _generate_report(context, output_dir)

    functions = [
        summarize_dataset,
        filter_significant_events,
        rank_candidates,
        run_enrichment,
        generate_figures,
        collect_literature_evidence,
        interpret_candidates,
        generate_report,
    ]
    return {
        function.__name__: FunctionTool(function, description=function.__doc__ or "")
        for function in functions
    }


__all__ = ["build_tools"]
