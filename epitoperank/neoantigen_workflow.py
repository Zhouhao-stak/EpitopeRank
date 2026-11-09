"""Explicit, one-stage-at-a-time neoantigen workflow.

This workflow consumes quantified events and externally reconstructed ORFs;
it never claims to reconstruct transcripts or infer NMD.
"""
from __future__ import annotations

import csv
import hashlib
from pathlib import Path

from epitoperank.neoantigen import HLA_PATTERN, predict_iedb
from epitoperank.neoantigen_audit import audit, filter_events
from epitoperank.neoantigen_evidence import expression_evidence, normal_protein_filter, supplied_orf_candidates, gtex_junction_filter, normal_tissue_expression


def dataset_fingerprint(dataset) -> str:
    """对事件与样本生成 sha256 摘要，用于发现输入数据在阶段之间被改动。"""
    return hashlib.sha256(repr((dataset.events, dataset.samples)).encode('utf-8')).hexdigest()


def _file(directory: Path, name: str) -> Path:
    """确保输入文件位于项目数据目录内且真实存在，否则抛出 ValueError。"""
    path = (directory / name).resolve()
    if directory.resolve() not in path.parents or not path.is_file():
        raise ValueError('输入文件必须位于项目数据目录内')
    return path


def _table(path: Path) -> list[dict]:
    """读取带表头的表格（按后缀区分逗号与制表符分隔）为字典行列表。"""
    with path.open(encoding='utf-8-sig', newline='') as handle:
        return list(csv.DictReader(handle, delimiter=',' if path.suffix.lower() == '.csv' else '\t'))


# 中文备注：epitoperank：推进advance（参数：state、dataset、parameters、predictor）
def advance(state: dict, dataset, parameters: dict, *, predictor=predict_iedb) -> dict:
    """Advance exactly one stage; caller must persist state only on success."""
    if parameters.get('confirm') is not True:
        raise ValueError('请先确认上一阶段结果')
    if state.get('stopped'):
        raise ValueError('流程已停止：' + state['stopped'])
    if state['dataset_fingerprint'] != dataset_fingerprint(dataset):
        raise ValueError('项目输入数据已更改，请重新进行审计')
    stage = state['next_stage']
    directory = Path(dataset.source_dir).resolve()
    new = dict(state)
    history = list(state['history'])
    if stage == 1:
        if parameters.get('input_is_quantified_events') is not True:
            raise ValueError('请确认输入是已量化事件表；不支持原始 reads/BAM 事件发现')
        ids = [event.event_id for event in dataset.events]
        if any(not item for item in ids) or len(set(ids)) != len(ids):
            raise ValueError('事件 ID 为空或重复，无法可靠关联后续证据')
        if parameters.get('event_set') not in ('complete', 'subset', 'unknown'):
            raise ValueError('请声明事件表是否完整')
        result = {'stage': 1, 'input_count': len(dataset.events), 'surviving_count': len(dataset.events),
                  'excluded_reasons': {}, 'event_set': parameters['event_set'],
                  'note': '使用上游量化事件；未重新发现事件或重新进行 BH 校正。'}
    elif stage == 2:
        result = filter_events(dataset, min_support=parameters.get('min_support'), min_samples=parameters.get('min_samples'),
                               support_is_junction_reads=parameters.get('support_is_junction_reads', False))
        new['event_ids'] = result['event_ids']
        if not new['event_ids']:
            new['stopped'] = '事件级过滤后没有存活事件'
    elif stage == 3:
        if not state.get('event_ids'):
            raise ValueError('事件级过滤没有存活事件，流程停止')
        orf_name = str(parameters.get('orf_file') or '').strip()
        if not orf_name:
            # Blank means "pick the one that looks like a CDS table"; the file
            # name is irrelevant, only the four required columns matter.
            from epitoperank.neoantigen import discover_cds_tables, pick_cds_table
            picked = pick_cds_table(discover_cds_tables(directory))
            if picked is None:
                raise ValueError('项目里没有可用的 CDS 表（需含 event_id、reference_cds、altered_cds、junction_nt）')
            orf_name = picked.name
        rows = _table(_file(directory, orf_name))
        result = supplied_orf_candidates(rows, set(state['event_ids']))
        result['stage'] = 3
        new['candidates'] = result.pop('candidates')
        if not new['candidates']:
            new['stopped'] = '没有可继续的候选肽'
    elif stage == 4:
        if not state.get('candidates'):
            raise ValueError('没有可继续的候选肽')
        files = parameters.get('protein_fastas') or {}
        databases = {k: _file(directory, str(files.get(k) or '')) for k in ('paired_normal', 'gtex', 'proteome')}
        filtered = normal_protein_filter(state['candidates'], databases)
        new['candidates'] = filtered.pop('candidates')
        result = {'stage': 4, **filtered, 'skipped': []}
        allow_skip = parameters.get('acknowledge_missing_gtex_junction_and_tissue_expression') is True
        if parameters.get('event_junctions') and parameters.get('gtex_junctions'):
            junctions = gtex_junction_filter(new['candidates'], _file(directory, parameters['event_junctions']),
                          _file(directory, parameters['gtex_junctions']), event_build=parameters.get('event_build'),
                          gtex_build=parameters.get('gtex_build'))
            new['candidates'] = junctions.pop('candidates')
            result['junction_filter'] = junctions
        elif allow_skip:
            result['skipped'].append('GTEx junction 匹配')
        else:
            raise ValueError('需要事件和 GTEx 连接点表；如要跳过须明确接受局限')
        if parameters.get('normal_expression_file'):
            expression = normal_tissue_expression(new['candidates'], {e.event_id: e.gene_id for e in dataset.events},
                                                   _file(directory, parameters['normal_expression_file']))
            new['candidates'] = expression.pop('candidates')
            result['normal_expression'] = expression
        elif allow_skip:
            result['skipped'].append('重要正常组织表达检查')
        else:
            raise ValueError('需要正常组织表达表；如要跳过须明确接受局限')
        if not new['candidates']:
            new['stopped'] = '正常蛋白过滤后没有候选肽'
    elif stage == 5:
        records = parameters.get('expression_records')
        if parameters.get('expression_file'):
            rows = _table(_file(directory, str(parameters['expression_file'])))
            records = {}
            for row in rows:
                event_id = str(row.get('event_id') or '').strip()
                if not event_id or event_id in records:
                    raise ValueError('表达表的 event_id 为空或重复')
                try:
                    records[event_id] = {'expression': float(row['expression']), 'expression_unit': row['expression_unit'],
                        'recurrence_count': int(row['recurrence_count']) if row.get('recurrence_count') else None,
                        'recurrence_total': int(row['recurrence_total']) if row.get('recurrence_total') else None}
                except (ValueError, TypeError, KeyError):
                    raise ValueError('表达表需要 event_id、expression、expression_unit，复现率计数为可选整数')
        if not isinstance(records, dict):
            raise ValueError('需要按 event_id 提供表达量及单位')
        result = expression_evidence(state['candidates'], records)
        result['stage'] = 5
        new['candidates'] = result.pop('candidates')
        if not new['candidates']:
            new['stopped'] = '无表达证据支持的候选肽'
    elif stage == 6:
        alleles = parameters.get('alleles')
        if not isinstance(alleles, list) or not alleles or any(not isinstance(a, str) or not HLA_PATTERN.fullmatch(a) for a in alleles):
            raise ValueError('需要真实 HLA-I 分型，例如 HLA-A*02:01')
        if not parameters.get('hla_source') or not parameters.get('hla_confidence'):
            raise ValueError('请提供 HLA 分型来源和置信度')
        pairs = list(dict.fromkeys((c['peptide'], a) for c in state['candidates'] for a in alleles))
        if len(pairs) > 200:
            raise ValueError('肽-HLA 组合超过上限 200')
        predictions, errors = [], []
        for peptide, allele in pairs:
            try:
                raw = predictor(peptide, allele)
                predictions.append({'peptide': peptide, 'allele': allele, 'percentile_rank': raw.get('percentile_rank'), 'raw_result': raw})
            except Exception as error:
                errors.append({'peptide': peptide, 'allele': allele, 'error': str(error)[:300]})
        result = {'stage': 6, 'input_count': len(pairs), 'surviving_count': len(predictions),
                  'excluded_reasons': {'预测失败': len(errors)}, 'prediction_errors': errors,
                  'method': 'IEDB NetMHCpan 4.1 EL', 'hla_source': parameters['hla_source'],
                  'hla_confidence': parameters['hla_confidence']}
        new['predictions'] = predictions
    elif stage == 7:
        event_lookup = {e.event_id: e for e in dataset.events}
        predictions = {}
        for prediction in state['predictions']:
            predictions.setdefault(prediction['peptide'], []).append(prediction)
        table = []
        for candidate in state['candidates']:
            event = event_lookup[candidate['event_id']]
            for pred in predictions.get(candidate['peptide'], []):
                table.append({**candidate, 'gene': event.gene_symbol, 'event_type': event.event_type,
                              'delta_psi': event.delta_psi, 'fdr': event.fdr,
                              'hla': pred['allele'], 'percentile_rank': pred['percentile_rank']})
        limitations = [
            '候选肽的 novelty 只在所提供的参考序列范围内成立，未覆盖全部正常转录本与蛋白组',
            'MHC 结合预测不等于抗原呈递、不等于免疫原性、不等于临床有效性',
            '缺少 HLA 免疫肽组质谱证据时，无法确认肽是否真被呈递',
            '缺少实验验证（四聚体 / ELISpot / 靶细胞杀伤）时，不能声称免疫原性',
            '若上游无配对 normal 或无生物学重复，则“肿瘤特异”这一结论不成立',
            'ORF 和读码框为上游声明；NMD 为距离规则预测，缺失连接点时为未知。',
            '未定义有证据支持的综合评分，候选表未作综合评分排序。',
        ]
        limitations.extend('已跳过：' + x for x in history[4].get('skipped', []))
        result = {'stage': 7, 'sections': {
            '一句话结论': '已完成所提供输入支持的阶段；存在跳过步骤和未验证的上游声明。',
            '漏斗表': history, '候选表': table,
            '方法与参数': {'event_filter': history[2].get('thresholds'), 'prediction': 'IEDB NetMHCpan 4.1 EL',
                        'declared_evidence': history[0]['declared_evidence'], 'prediction_limit': 200},
            '局限性': limitations,
            '不可据此得出的结论': ['不能证明抗原呈递、免疫原性、临床有效性或肿瘤特异性。']}}
    else:
        raise ValueError('没有可继续的阶段')
    history.append(result)
    new['history'] = history
    new['next_stage'] = stage + 1
    return new


def start(dataset, evidence: dict) -> dict:
    """初始化流程状态：先做输入审计，后续阶段的事件、候选与预测均从空开始。"""
    return {'next_stage': 1, 'dataset_fingerprint': dataset_fingerprint(dataset), 'history': [audit(dataset, evidence)], 'event_ids': [],
            'candidates': [], 'predictions': [], 'stopped': None}
