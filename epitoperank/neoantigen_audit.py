"""Evidence-aware preliminary audit and event-level filter for neoantigens."""
from __future__ import annotations

from collections import Counter
from math import isfinite

from epitoperank.data.loader import Dataset


# 中文备注：epitoperank：辅助处理审计（参数：dataset、evidence）
def audit(dataset: Dataset, evidence: dict) -> dict:
    """Report supplied evidence without inferring biological provenance."""
    groups = {name: len(ids) for name, ids in dataset.groups.items()}
    fields = ('normal_design', 'genome_build', 'annotation_version', 'coordinate_system',
              'input_kind', 'hla_source', 'hla_confidence')
    declared = {field: str(evidence.get(field) or '').strip() or None for field in fields}
    has_cds = evidence.get('has_frame_correct_cds') is True
    missing = []
    if not has_cds:
        missing.append('经过验证的参考和异常 CDS 及连接点')
    if not declared['genome_build']:
        missing.append('基因组版本')
    if not declared['annotation_version']:
        missing.append('转录本注释版本')
    if not declared['coordinate_system']:
        missing.append('坐标基准')
    return {'stage': 0, 'event_count': len(dataset.events), 'groups': groups,
            'declared_evidence': declared, 'has_frame_correct_cds': has_cds,
            'missing': missing,
            'boundary': '支持事件审计和已重建 ORF 的下游分析；项目内 ORF 重建请见「剪接候选新抗原」页的自动重建入口（splicing/orf_builder.py），本分阶段流程不自动串联它。NMD 距离规则需要最后外显子连接点，正常过滤需要独立参考数据。',
            'requires_confirmation': True}


# 中文备注：epitoperank：筛选剪接事件（参数：dataset、min_support、min_samples、support_is_junction_reads）
def filter_events(dataset: Dataset, *, min_support: int | None, min_samples: int | None,
                  support_is_junction_reads: bool = False) -> dict:
    """Filter only when all required quality evidence and thresholds exist."""
    if type(min_support) is not int or type(min_samples) is not int or min_support < 1 or min_samples < 1:
        raise ValueError('需要明确指定正整数 junction 支持读数及有效样本数阈值')
    if support_is_junction_reads is not True:
        raise ValueError('须先确认 total_support_reads 表示 junction 支持读数')
    reasons: Counter[str] = Counter()
    survivors = []
    for event in dataset.events:
        reason = None
        if event.fdr is None or not isfinite(event.fdr): reason = '缺少有效 FDR'
        elif not 0 <= event.fdr <= 1: reason = 'FDR 超出范围'
        elif event.fdr >= 0.05: reason = 'FDR 不满足 < 0.05'
        elif event.delta_psi is None or not isfinite(event.delta_psi): reason = '缺少有效 ΔPSI'
        elif abs(event.delta_psi) > 1: reason = 'ΔPSI 超出范围'
        elif abs(event.delta_psi) <= 0.1: reason = '|ΔPSI| 不满足 > 0.1'
        elif event.total_support_reads is None: reason = '缺少支持读数'
        elif event.total_support_reads < min_support: reason = '支持读数不足'
        elif event.valid_sample_count is None: reason = '缺少有效样本数'
        elif event.valid_sample_count < min_samples: reason = '有效样本数不足'
        elif event.single_sample_driven is None: reason = '缺少单样本驱动质量标记'
        elif event.single_sample_driven: reason = '单样本驱动'
        elif event.mapping_ambiguity is None: reason = '缺少比对歧义质量标记'
        elif event.mapping_ambiguity: reason = '存在比对歧义'
        if reason:
            reasons[reason] += 1
        else:
            survivors.append(event.event_id)
    return {'stage': 2, 'input_count': len(dataset.events), 'surviving_count': len(survivors),
            'excluded_reasons': dict(reasons), 'event_ids': survivors,
            'thresholds': {'fdr_lt': 0.05, 'absolute_delta_psi_gt': 0.1,
                           'min_support_reads': min_support, 'min_valid_samples': min_samples},
            'note': 'total_support_reads 的具体定义取决于上游工具，须确认其代表所需 junction 支持。'}
