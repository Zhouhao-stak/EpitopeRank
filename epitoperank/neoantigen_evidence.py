"""Evidence-based filters for candidate peptides, with explicit provenance."""
from __future__ import annotations

from collections import Counter
import csv
from hashlib import sha256
from math import isfinite
from pathlib import Path

from epitoperank.neoantigen import CODONS, junction_peptides


def assess_nmd(altered_cds: str, premature_stop: str, last_junction_nt: str | int | None) -> dict:
    """50-nt rule using last exon junction measured from the coding start.

    The boundary may be downstream of the CDS in the 3' UTR. This is a
    heuristic, not evidence of actual transcript degradation.
    """
    if premature_stop != 'yes':
        return {'status': 'not_applicable', 'distance_nt': None}
    cds = altered_cds.strip().upper().replace('U', 'T')
    stops = [i for i in range(0, len(cds), 3) if CODONS.get(cds[i:i+3]) == '*']
    if not stops or last_junction_nt in (None, ''):
        return {'status': 'unknown', 'distance_nt': None}
    try:
        junction = int(last_junction_nt)
        if junction < 1:
            raise ValueError
    except (ValueError, TypeError):
        raise ValueError('last_junction_nt 必须是从编码起点计算的正整数')
    distance = junction - (stops[0] + 3)
    return {'status': 'candidate' if distance > 50 else 'not_predicted',
            'distance_nt': distance, 'rule': 'stop末端至最后外显子连接点 > 50 nt'}


def supplied_orf_candidates(rows: list[dict], event_ids: set[str]) -> dict:
    """Use externally reconstructed CDS only, separating early stops from candidates."""
    candidates, separated = [], []
    reasons: Counter[str] = Counter()
    for row in rows:
        event_id = str(row.get('event_id') or '').strip()
        try:
            if event_id not in event_ids:
                raise ValueError('事件未通过事件级过滤')
            if not str(row.get('orf_source') or '').strip():
                raise ValueError('缺少 ORF 重建来源')
            if row.get('frame_status') not in ('in_frame', 'frameshift'):
                raise ValueError('缺少上游读码框状态')
            if row.get('premature_stop') not in ('yes', 'no'):
                raise ValueError('缺少提前终止判断')
            peptides = junction_peptides(row.get('reference_cds') or '', row.get('altered_cds') or '', int(row.get('junction_nt') or ''))
            cds = (row.get('altered_cds') or '').strip().upper().replace('U', 'T')
            stops = [i for i in range(0, len(cds), 3) if CODONS[cds[i:i+3]] == '*']
            if row['premature_stop'] == 'yes' and not stops:
                raise ValueError('声明提前终止但异常 CDS 没有终止密码子')
            if row['premature_stop'] == 'no' and stops and stops[0] < len(cds) - 3:
                raise ValueError('异常 CDS 内部终止密码子与声明不一致')
            if row['premature_stop'] == 'yes':
                nmd = assess_nmd(cds, 'yes', row.get('last_junction_nt'))
                separated.append({'event_id': event_id, 'reason': '提前终止，需单独评估', 'nmd': nmd, 'peptide_count': len(peptides)})
                reasons['提前终止，单独列出'] += 1
            elif not peptides:
                reasons['无符合条件的跨连接点新肽'] += 1
            else:
                candidates.extend({'event_id': event_id, 'orf_source': row['orf_source'],
                                   'frame_status': row['frame_status'], **item} for item in peptides)
        except (ValueError, TypeError, KeyError) as error:
            reasons[str(error)] += 1
    return {'input_count': len(rows), 'surviving_count': len(rows) - sum(reasons.values()),
            'excluded_reasons': dict(reasons), 'candidates': candidates, 'separated': separated,
            'note': '读码框和提前终止状态由上游提供；NMD 仅按最后外显子连接点距离作规则预测，缺坐标时为未知。'}


def _proteins(path: Path):
    """Stream a protein FASTA, rejecting empty and malformed databases."""
    name = None
    seq: list[str] = []
    with path.open(encoding='utf-8-sig') as handle:
        for line in handle:
            line = line.strip()
            if not line:
                continue
            if line.startswith('>'):
                if name is not None:
                    if not seq:
                        raise ValueError(f'Empty FASTA sequence: {name}')
                    yield name, ''.join(seq)
                name = line[1:].strip()
                if not name:
                    raise ValueError('Empty FASTA header')
                seq = []
            else:
                value = line.upper()
                if name is None or not value.isascii() or not value.isalpha():
                    raise ValueError(f'Invalid protein FASTA: {path.name}')
                seq.append(value)
    if name is None or not seq:
        raise ValueError(f'Empty protein FASTA: {path.name}')
    yield name, ''.join(seq)


def normal_protein_filter(candidates: list[dict], databases: dict[str, str | Path]) -> dict:
    """Apply exact peptide substring matching in the supplied ordered databases.

    Database completeness and source identity must be verified independently.
    GTEx junction-level matching and normal-tissue expression are separate inputs.
    """
    required = ('paired_normal', 'gtex', 'proteome')
    if any(not databases.get(key) for key in required):
        raise ValueError('需要提供配对正常、GTEx 翻译蛋白及全蛋白组 FASTA；缺失不能视为过滤通过')
    remaining = list(candidates)
    stages = []
    for kind in required:
        path = Path(databases[kind])
        unique = {str(c.get('peptide') or '').upper() for c in remaining}
        if '' in unique or any(not p.isascii() or not p.isalpha() for p in unique):
            raise ValueError('候选肽序列无效')
        matches = set()
        count = 0
        for _, protein in _proteins(path):
            count += 1
            matches.update(p for p in unique if p in protein)
        before = len(remaining)
        remaining = [c for c in remaining if c['peptide'].upper() not in matches]
        digest = sha256()
        with path.open('rb') as handle:
            for block in iter(lambda: handle.read(1024 * 1024), b''):
                digest.update(block)
        stages.append({'database': kind, 'path': str(path.resolve()), 'sha256': digest.hexdigest(),
                       'protein_count': count, 'input_count': before, 'surviving_count': len(remaining),
                       'excluded_reasons': {'正常蛋白序列精确匹配': before - len(remaining)}})
    return {'candidates': remaining, 'stages': stages,
            'limitations': ['仅在所提供的蛋白序列范围内进行精确匹配', '未执行 GTEx junction 匹配或正常组织表达评估']}


def expression_evidence(candidates: list[dict], records: dict[str, dict]) -> dict:
    """Annotate measured expression and recurrence without filtering recurrence."""
    reasons: Counter[str] = Counter()
    result = []
    for candidate in candidates:
        record = records.get(str(candidate.get('event_id', '')))
        if not record:
            reasons['缺少表达证据'] += 1
            continue
        expression = record.get('expression')
        unit = record.get('expression_unit')
        observed, total = record.get('recurrence_count'), record.get('recurrence_total')
        if isinstance(expression, bool) or not isinstance(expression, (int, float)) or not isfinite(expression) or expression < 0 or not unit:
            reasons['无效或缺少表达量及单位'] += 1
            continue
        if expression == 0:
            reasons['表达量为零'] += 1
            continue
        if observed is not None or total is not None:
            if type(observed) is not int or type(total) is not int or total < 1 or not 0 <= observed <= total:
                reasons['复现率计数无效'] += 1
                continue
        result.append({**candidate, 'expression': expression, 'expression_unit': unit,
                       'recurrence_count': observed, 'recurrence_total': total,
                       'recurrence': observed / total if total is not None else None})
    return {'input_count': len(candidates), 'surviving_count': len(result),
            'excluded_reasons': dict(reasons), 'candidates': result,
            'note': '复现率仅作为附加证据，不作为过滤门槛。'}


def _read_tsv(path: Path, columns: set[str]) -> list[dict]:
    """读取 TSV，并在缺少必需列时直接报错，避免静默使用残缺证据表。"""
    with path.open(encoding='utf-8-sig', newline='') as handle:
        reader = csv.DictReader(handle, delimiter='\t')
        if not reader.fieldnames or not columns.issubset(reader.fieldnames):
            raise ValueError(f'{path.name} 缺少列: {", ".join(sorted(columns))}')
        return list(reader)


def gtex_junction_filter(candidates: list[dict], event_file: Path, gtex_file: Path,
                         *, event_build: str, gtex_build: str) -> dict:
    """Match declared 1-based inclusive intron coordinates including strand."""
    if not event_build or event_build != gtex_build:
        raise ValueError('事件和 GTEx 的基因组版本必须明确且一致')
    cols = {'chromosome', 'intron_start', 'intron_end', 'strand'}
    events = _read_tsv(event_file, cols | {'event_id'})
    normal = _read_tsv(gtex_file, cols)
    if not normal:
        raise ValueError('GTEx 连接点表为空，不能作为正常组织阴性证据')
    def key(row):
        """把连接点记录规整为（染色体，1-based 起点，终点，链）并校验合法性。"""
        try:
            start, end = int(row['intron_start']), int(row['intron_end'])
        except (TypeError, ValueError):
            raise ValueError('连接点坐标必须是整数')
        chrom, strand = row['chromosome'].strip(), row['strand'].strip()
        if not chrom or strand not in ('+', '-') or start < 1 or end < start:
            raise ValueError('无效连接点：需要染色体、1-based 内含子范围及链方向')
        return chrom, start, end, strand
    reference = {key(row) for row in normal}
    event_map = {}
    for row in events:
        event_id = (row.get('event_id') or '').strip()
        if not event_id:
            raise ValueError('事件连接点缺少 event_id')
        event_map.setdefault(event_id, set()).add(key(row))
    missing = {str(c.get('event_id', '')) for c in candidates} - event_map.keys()
    if missing:
        raise ValueError('事件连接点缺失: ' + ', '.join(sorted(missing)[:10]))
    remaining = [c for c in candidates if not (event_map[c['event_id']] & reference)]
    return {'input_count': len(candidates), 'surviving_count': len(remaining),
            'excluded_reasons': {'GTEx 连接点匹配': len(candidates)-len(remaining)},
            'candidates': remaining, 'genome_build': event_build,
            'note': '未检出不代表不存在；过滤依赖所提供表的覆盖度。'}


def normal_tissue_expression(candidates: list[dict], event_genes: dict[str, str], path: Path) -> dict:
    """Annotate observed gene expression; do not infer missing tissue as zero."""
    rows = _read_tsv(path, {'gene_id', 'tissue', 'expression', 'unit'})
    if not rows:
        raise ValueError('正常组织表达表为空')
    by_gene = {}
    for row in rows:
        gene, tissue, unit = (str(row.get(k) or '').strip() for k in ('gene_id', 'tissue', 'unit'))
        try:
            value = float(row['expression'])
        except (ValueError, TypeError):
            raise ValueError('正常组织表达量必须是非负数')
        if not gene or not tissue or not unit or not isfinite(value) or value < 0:
            raise ValueError('正常组织表达记录无效')
        by_gene.setdefault(gene, []).append({'tissue': tissue, 'expression': value, 'unit': unit})
    annotated = []
    for c in candidates:
        gene = event_genes.get(c['event_id'], '')
        annotated.append({**c, 'normal_tissue_expression': by_gene.get(gene, []),
                          'normal_expression_status': 'observed' if gene in by_gene else 'unknown'})
    return {'input_count': len(candidates), 'surviving_count': len(annotated),
            'candidates': annotated, 'missing_gene_count': len({event_genes.get(c['event_id'], '') for c in candidates} - by_gene.keys()),
            'note': '提供实测值供评估，未设定“高表达”阈值；缺失不视为零。'}
