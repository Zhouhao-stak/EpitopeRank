"""Auditable splice-junction peptide candidates and optional IEDB MHC-I scores.

Input CDS sequences must already be oriented 5'->3' in the correct reading
frame. An event coordinate alone cannot establish an ORF or translated protein.
"""
from __future__ import annotations

import csv
import io
import json
import re
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from epitoperank.data.loader import load_dataset

CODONS = dict(zip(
    (a+b+c for a in 'TCAG' for b in 'TCAG' for c in 'TCAG'),
    ''.join('FFLLSSSSYY**CC*WLLLLPPPPHHQQRRRRIIIMTTTTNNKKSSRRVVVVAAAADDEEGGGG'),
))
CDS_FIELDS = ('event_id', 'reference_cds', 'altered_cds', 'junction_nt')
HLA_PATTERN = re.compile(r'^HLA-[ABC]\*\d{2,3}:\d{2,3}$')
#: Upper bound on peptide x allele queries per run. IEDB is called in batches of
#: 100 peptides, so a few thousand pairs is minutes of work, not a refusal.
DEFAULT_MAX_PREDICTIONS = 20000
IEDB_URL = 'https://tools-cluster-interface.iedb.org/tools_api/mhci/'
IEDB_METHOD = 'netmhcpan_el-4.1'

# A customer should never have to know a magic filename. CDS tables are found by
# reading their header, and the column names are matched against common variants
# (English, Chinese, Excel-style headers) so hand-made tables still work.
CDS_TABLE_SUFFIXES = ('.tsv', '.txt', '.csv', '.tab')
PREFERRED_CDS_STEMS = ('splice_orfs', 'coding_pairs')
CDS_TABLE_SCAN_LIMIT = 400
CDS_TABLE_MAX_BYTES = 64 * 1024 * 1024
CDS_TABLE_HINTS = ('splice', 'cds', 'coding', 'orf', 'orf_')

CDS_FIELD_ALIASES: dict[str, tuple[str, ...]] = {
    'event_id': (
        'event_id', 'eventid', 'event id', 'event-id', 'event', 'events',
        'event_name', 'splice_event_id', 'rmats_event_id',
        '事件id', '事件ID', '事件编号', '事件', '剪接事件id', '剪接事件ID',
    ),
    'reference_cds': (
        'reference_cds', 'reference cds', 'ref_cds', 'refcds', 'reference',
        'cds_reference', 'reference_sequence', 'reference_seq', 'ref_seq',
        'normal_cds', 'wildtype_cds', 'wt_cds', 'original_cds',
        '参考cds', '参考序列', '参考编码序列', '原序列', '原始cds', '正常cds',
    ),
    'altered_cds': (
        'altered_cds', 'altered cds', 'alt_cds', 'altcds', 'altered', 'alternative_cds',
        'mutant_cds', 'mutation_cds', 'variant_cds', 'changed_cds', 'tumor_cds',
        '新序列', '变异序列', '突变序列', '改变后序列', '改变后的序列', '异常序列', '肿瘤序列',
        '异常cds', '变异cds', '突变cds', '改变后cds', '肿瘤cds',
    ),
    'junction_nt': (
        'junction_nt', 'junction nt', 'junction', 'junction_position',
        'junction_pos', 'junction_index', 'junction_site', 'junction_boundary',
        'junction_offset', 'nt_at_junction',
        '连接点', '连接点位置', '连接位点', '断裂点', '剪接连接点',
    ),
}


#: Human-facing labels used by the mapping dialog and error messages.
CDS_FIELD_LABELS = {
    'event_id': '事件 ID',
    'reference_cds': '参考（正常）编码序列',
    'altered_cds': '改变后（变异）编码序列',
    'junction_nt': '新剪接连接点位置（整数）',
}

#: Short labels for one-line hints, where the long form is too noisy.
CDS_FIELD_SHORT = {
    'event_id': '事件ID',
    'reference_cds': '参考序列',
    'altered_cds': '变异序列',
    'junction_nt': '连接点位置',
}

#: Columns that only appear in rMATS junction-count tables. A file carrying one
#: of them is an event table, never a CDS lookup table, so it must not be
#: reported back as "a CDS table with missing columns" - that only confuses a
#: customer who uploaded a normal rMATS directory.
RMATS_MARKER_COLUMNS = (
    'ijcsample1', 'ijcsample2', 'sjcsample1', 'sjcsample2', 'inclevel1', 'inclevel2',
    'incformlen', 'skipformlen', 'exonstart0base', 'longexonstart0base', 'shortexonstart0base',
    'upstreamee', 'downstreames', 'firstexonstart0base', 'secondexonstart0base',
    'ijc_sample_1', 'sjc_sample_1',
)
#: ``SE.MATS.JC.txt`` / ``RI.MATS.JCEC.txt`` and friends.
RMATS_FILENAME = re.compile(r'\.MATS\.[A-Za-z]+\.(txt|tsv|csv)$', re.IGNORECASE)


# 中文备注：epitoperank：辅助处理lookslikermats（参数：header、name）
def _looks_like_rmats(header, name: str = '') -> bool:
    """True when the table is a rMATS event table rather than a CDS table."""
    if RMATS_FILENAME.search(str(name or '').strip()):
        return True
    folded = {_normalize_header(cell) for cell in header}
    return any(_normalize_header(marker) in folded for marker in RMATS_MARKER_COLUMNS)

#: How many data rows to sample when guessing a column's role from its values.
COLUMN_SAMPLE_ROWS = 200


# 中文备注：epitoperank：规范化表头（参数：name）
def _normalize_header(name: str) -> str:
    """Fold a header cell into a comparable key (case/space/underscore-free)."""
    return re.sub(r'[\s\-_\u3000]+', '', str(name or '').strip().lower())


_CANONICAL_BY_ALIAS: dict[str, str] = {
    _normalize_header(alias): canonical
    for canonical, aliases in CDS_FIELD_ALIASES.items()
    for alias in (canonical, *aliases)
}


# 中文备注：epitoperank：辅助处理canonicalCDS字段（参数：names）
def canonical_cds_fields(names) -> list[str]:
    """Map raw column names onto the four canonical CDS field names."""
    return [_CANONICAL_BY_ALIAS.get(_normalize_header(name), _normalize_header(name)) for name in names]


# 中文备注：epitoperank：辅助处理decode表文本（参数：path、limit）
def decode_table_text(path: str | Path, *, limit: int | None = None) -> str:
    """Read a text table, tolerating UTF-8, UTF-8-BOM and GBK exports."""
    raw = Path(path).read_bytes()
    if limit is not None:
        raw = raw[:limit]
    for encoding in ('utf-8-sig', 'gb18030'):
        try:
            return raw.decode(encoding)
        except UnicodeDecodeError:
            continue
    return raw.decode('utf-8-sig', errors='replace')


def sniff_delimiter(header_line: str) -> str:
    """按表头行里制表符与逗号的数量推断分隔符。"""
    return '\t' if header_line.count('\t') >= header_line.count(',') else ','


# 中文备注：epitoperank：辅助处理表列（参数：path）
def _table_columns(path: str | Path) -> tuple[list[str], str]:
    """Return (canonical columns, delimiter) from the first line of a table."""
    text = decode_table_text(path, limit=64_000)
    first = text.splitlines()[0] if text.strip() else ''
    delimiter = sniff_delimiter(first)
    header = next(csv.reader([first], delimiter=delimiter), [])
    return canonical_cds_fields(header), delimiter


# 中文备注：epitoperank：读取表行（参数：path、limit）
def read_table_rows(path: str | Path, *, limit: int | None = None
                    ) -> tuple[list[str], list[list[str]], str]:
    """Read a whole table into memory rows (used for guessing and previewing)."""
    text = decode_table_text(path)
    if not text.strip():
        return [], [], '\t'
    first_line = text.splitlines()[0]
    delimiter = sniff_delimiter(first_line)
    reader = csv.reader(io.StringIO(text), delimiter=delimiter)
    rows = [list(row) for row in reader]
    header = rows[0] if rows else []
    body = rows[1:] if rows else []
    if limit is not None:
        body = body[:limit]
    return [str(item).strip() for item in header], body, delimiter


_ACGT = set('ACGTU')
_EVENT_ID_SHAPE = re.compile(r'^(?:SE|RI|A3SS|A5SS|MXE)\s*[:;_\-]?\s*\d+$', re.IGNORECASE)


# 中文备注：epitoperank：辅助处理序列like（参数：value）
def _sequence_like(value: str) -> bool:
    """True when a cell looks like a coding sequence (not a peptide or free text)."""
    text = str(value or '').strip().upper().replace('U', 'T')
    return (len(text) >= 30 and len(text) % 3 == 0 and set(text) <= _ACGT)


def _translate_ok(value: str) -> bool:
    """判断该单元格能否作为完整密码子的序列成功翻译。"""
    try:
        translate(value)
        return True
    except ValueError:
        return False


def _looks_numeric(value: str) -> bool:
    """判断单元格是否为 1 至 9 位纯数字，可能代表连接点坐标。"""
    text = str(value or '').strip()
    return text.isdigit() and 0 < len(text) <= 9


def profile_columns(path: str | Path, event_ids: set[str] | None = None,
                    *, sample_rows: int = COLUMN_SAMPLE_ROWS) -> dict:
    """Describe every column by what its values *are*, not by what it is called.

    This is what makes a table with headers like ``序列1 / 序列2 / 位点`` workable
    without the customer renaming anything.
    """
    header, rows, delimiter = read_table_rows(path, limit=sample_rows)
    width = max([len(header)] + [len(row) for row in rows]) if (header or rows) else 0
    columns: list[dict] = []
    for index in range(width):
        raw_name = header[index] if index < len(header) else ''
        values = [str(row[index]).strip() for row in rows if index < len(row) and str(row[index]).strip()]
        total = len(values) or 1
        sequence = sum(1 for value in values if _sequence_like(value))
        translatable = sum(1 for value in values if _sequence_like(value) and _translate_ok(value))
        numeric = sum(1 for value in values if _looks_numeric(value))
        matched = sum(1 for value in values if event_ids and value in event_ids)
        id_shaped = sum(1 for value in values if _EVENT_ID_SHAPE.fullmatch(value))
        lengths = sorted({len(str(value).strip()) for value in values if _sequence_like(value)})
        columns.append({
            'index': index,
            'name': raw_name,
            'canonical': _CANONICAL_BY_ALIAS.get(_normalize_header(raw_name), ''),
            'samples': values[:3],
            'value_count': len(values),
            'sequence_ratio': sequence / total,
            'translatable_ratio': translatable / total,
            'numeric_ratio': numeric / total,
            'event_ratio': (matched / total) if event_ids else 0.0,
            'id_ratio': id_shaped / total,
            'sequence_lengths': lengths[:4],
        })
    return {'header': header, 'rows': rows, 'delimiter': delimiter,
            'columns': columns, 'row_count': len(rows)}


# 中文备注：epitoperank：检测映射列（参数：path、event_ids、sample_rows）
def detect_column_map(path: str | Path, event_ids: set[str] | None = None,
                      *, sample_rows: int = COLUMN_SAMPLE_ROWS) -> dict:
    """Guess the four CDS roles from header aliases *and* cell contents.

    Returns a mapping that is safe to pre-fill in a confirmation dialog. Rows are
    also replayed through ``junction_peptides`` to decide which of two sequence
    columns is the reference and which is the altered one.
    """
    profile = profile_columns(path, event_ids, sample_rows=sample_rows)
    columns = profile['columns']
    assigned: dict[str, int] = {}
    sources: dict[str, str] = {}

    # 1) Header aliases are the strongest signal when they resolve.
    for field in CDS_FIELDS:
        for column in columns:
            if column['canonical'] == field and column['index'] not in assigned.values():
                assigned[field] = column['index']
                sources[field] = 'header'
                break

    free = [column for column in columns if column['index'] not in assigned.values()]

    # 2) Fall back to content: an ID column either intersects the event table or
    #    looks like an rMATS identifier ("RI:4579").
    if 'event_id' not in assigned:
        pool = [column for column in free if column['sequence_ratio'] < 0.5]
        best = max(pool, key=lambda item: (item['event_ratio'], item['id_ratio'],
                                           -item['numeric_ratio']), default=None)
        if best is not None and (best['event_ratio'] >= 0.3 or best['id_ratio'] >= 0.5):
            assigned['event_id'] = best['index']
            sources['event_id'] = 'content'
            free = [column for column in free if column['index'] != best['index']]
        else:
            best = min(free, key=lambda item: (-item['numeric_ratio'], item['sequence_ratio']), default=None)
            if best is not None:
                assigned['event_id'] = best['index']
                sources['event_id'] = 'guess'
                free = [column for column in free if column['index'] != best['index']]

    # 3) The junction column is numeric and bounded by sequence length.
    if 'junction_nt' not in assigned:
        numeric = [column for column in free if column['numeric_ratio'] >= 0.6 and column['sequence_ratio'] < 0.2]
        if numeric:
            best = max(numeric, key=lambda item: item['numeric_ratio'])
            assigned['junction_nt'] = best['index']
            sources['junction_nt'] = 'content'
            free = [column for column in free if column['index'] != best['index']]

    # 4) Two sequence columns: decide which is reference and which is altered by
    #    replaying real rows through the peptide generator in both directions.
    sequences = [column for column in free if column['sequence_ratio'] >= 0.6]
    if len(sequences) >= 2 and ('reference_cds' not in assigned or 'altered_cds' not in assigned):
        first, second = sequences[0], sequences[1]
        verdict = _compare_sequence_orientation(profile, first, second, assigned.get('junction_nt'))
        assigned['reference_cds'] = verdict['reference']
        assigned['altered_cds'] = verdict['altered']
        sources['reference_cds'] = sources['altered_cds'] = verdict['source']
    else:
        for field in ('reference_cds', 'altered_cds'):
            if field in assigned:
                continue
            pool = [column for column in sequences if column['index'] not in assigned.values()]
            if pool:
                assigned[field] = pool[0]['index']
                sources[field] = 'content'

    mapping = {field: columns[index]['name'] for field, index in assigned.items() if index < len(columns)}
    missing = [field for field in CDS_FIELDS if field not in mapping]
    conflicted = [field for field in CDS_FIELDS
                  if field in mapping and list(mapping.values()).count(mapping[field]) > 1]
    confidence = 'high' if not missing and not conflicted and all(
        sources.get(field) == 'header' for field in CDS_FIELDS) else \
        'medium' if not missing and not conflicted else 'low'
    preview = [{'column': column['name'], 'index': column['index'],
                'samples': column['samples'], 'lengths': column['sequence_lengths'],
                'role': next((field for field, index in assigned.items() if index == column['index']), '')}
               for column in columns]
    return {'map': mapping, 'missing': missing, 'conflicted': conflicted,
            'sources': sources, 'confidence': confidence, 'preview': preview,
            'header': profile['header'], 'row_count': profile['row_count'],
            'delimiter': profile['delimiter'],
            'needs_confirmation': bool(missing or conflicted) or confidence != 'high'}


def _median_length(column: dict) -> float:
    """返回该列序列长度的平均值，用于判断哪一列是较长的参考 CDS。"""
    lengths = column.get('sequence_lengths') or [0]
    return sum(lengths) / len(lengths)


# 中文备注：epitoperank：比较序列orientation（参数：profile、first、second、junction_index）
def _compare_sequence_orientation(profile: dict, first: dict, second: dict,
                                  junction_index: int | None) -> dict:
    """Pick which sequence column is the reference and which is the altered one.

    A row only makes sense when the junction lands inside the altered CDS, so the
    rows are replayed through ``junction_peptides`` in both directions. When both
    directions happen to work the call is reported as a guess: exon skipping is the
    most common event, so the longer CDS is taken as the reference, and the UI asks
    a human to confirm.
    """
    rows = profile['rows']
    if junction_index is None:
        longer, shorter = (first, second) if _median_length(first) >= _median_length(second) else (second, first)
        return {'reference': longer['index'], 'altered': shorter['index'], 'source': 'guess'}

    def replay(reference: dict, altered: dict) -> tuple[int, int]:
        """按给定方向重放样例行，返回（产出肽的行数，有效行数）。"""
        produced = valid = 0
        for row in rows[:50]:
            try:
                reference_cds = str(row[reference['index']]).strip()
                altered_cds = str(row[altered['index']]).strip()
                junction = int(str(row[junction_index]).strip())
            except (IndexError, ValueError):
                continue
            try:
                valid += 1
                if junction_peptides(reference_cds, altered_cds, junction):
                    produced += 1
            except (ValueError, TypeError):
                continue
        return produced, valid

    forward = replay(first, second)
    reverse = replay(second, first)
    if forward != reverse:
        chosen = (first, second) if forward > reverse else (second, first)
        return {'reference': chosen[0]['index'], 'altered': chosen[1]['index'], 'source': 'content'}
    longer, shorter = (first, second) if _median_length(first) >= _median_length(second) else (second, first)
    return {'reference': longer['index'], 'altered': shorter['index'], 'source': 'guess'}


# 中文备注：epitoperank：辅助处理inspectCDS表（参数：path、event_ids）
def inspect_cds_table(path: str | Path, event_ids: set[str] | None = None) -> dict:
    """Judge a file by header *and* contents: can the four roles be located?"""
    path = Path(path)
    info: dict = {'path': path, 'name': path.name, 'valid': False, 'has_rows': False,
                  'missing': list(CDS_FIELDS), 'header': [], 'reason': '',
                  'mapping': {}, 'mapping_source': '', 'needs_confirmation': True,
                  'confidence': 'low', 'preview': [], 'row_count': 0, 'rmats': False}
    try:
        if path.stat().st_size == 0:
            info['reason'] = '文件为空'
            return info
        names, delimiter = _table_columns(path)
        raw_header, _rows, _delimiter = read_table_rows(path, limit=5)
        info['header'] = [str(item) for item in raw_header]
        info['delimiter'] = delimiter
        if _looks_like_rmats(info['header'], path.name):
            info['rmats'] = True
            info['reason'] = 'rMATS 剪接事件表，不是编码序列表'
            return info
        info['missing'] = [field for field in CDS_FIELDS if field not in names]
        if not info['missing']:
            column_index: dict[str, int] = {}
            for position, name in enumerate(names):
                column_index.setdefault(name, position)
            info['mapping'] = {field: raw_header[index] for field, index in column_index.items()
                               if field in CDS_FIELDS and index < len(raw_header)}
            info['mapping_source'] = 'header'
            info['confidence'] = 'high'
            info['needs_confirmation'] = False
        else:
            # Unknown column names: read the values and work out the roles.
            detected = detect_column_map(path, event_ids)
            info['preview'] = detected['preview']
            if detected['missing'] or detected['conflicted']:
                info['missing'] = detected['missing'] or info['missing']
                label = '、'.join(f'{CDS_FIELD_SHORT.get(field, field)}（{field}）'
                                  for field in info['missing'])
                info['reason'] = f'缺少：{label}'
                return info
            info['mapping'] = detected['map']
            info['mapping_source'] = 'content'
            info['confidence'] = detected['confidence']
            info['needs_confirmation'] = detected['needs_confirmation']
        text = decode_table_text(path, limit=1_000_000)
        rows = [line for line in text.splitlines()[1:] if line.strip()]
        info['has_rows'] = bool(rows)
        info['row_count'] = info['row_count'] or len(rows)
        if not rows:
            info['reason'] = '只有表头，没有数据行'
            return info
        info['valid'] = True
        return info
    except (OSError, UnicodeError, csv.Error) as error:  # unreadable file -> not a candidate
        info['reason'] = f'无法读取：{error}'
        return info


# 中文备注：epitoperank：排序CDS（参数：path）
def _cds_rank(path: Path) -> tuple:
    """Prefer the historical filenames, then anything that looks CDS-ish."""
    stem = path.stem.lower()
    for index, preferred in enumerate(PREFERRED_CDS_STEMS):
        if stem == preferred:
            return (0, index, 0, stem)
    for index, hint in enumerate(CDS_TABLE_HINTS):
        if hint in stem:
            return (1, index, 0, stem)
    return (2, 0, len(stem), stem)


# 中文备注：epitoperank：发现CDS表（参数：include_partial、event_ids）
def discover_cds_tables(*directories: str | Path, include_partial: bool = False,
                        event_ids: set[str] | None = None) -> list[dict]:
    """Find CDS tables inside the given directories by inspecting file contents."""
    found: list[dict] = []
    partial: list[dict] = []
    seen: set[Path] = set()
    scanned = 0
    for directory in directories:
        folder = Path(directory or '')
        if not folder or not folder.is_dir():
            continue
        try:
            entries = sorted(folder.iterdir())
        except OSError:
            continue
        for entry in entries:
            if scanned >= CDS_TABLE_SCAN_LIMIT:
                break
            if not entry.is_file() or entry.suffix.lower() not in CDS_TABLE_SUFFIXES:
                continue
            try:
                size = entry.stat().st_size
            except OSError:
                continue
            if size == 0 or size > CDS_TABLE_MAX_BYTES:
                continue
            scanned += 1
            try:
                key = entry.resolve()
            except OSError:
                continue
            if key in seen:
                continue
            seen.add(key)
            info = inspect_cds_table(entry, event_ids)
            if info['valid']:
                found.append(info)
            elif info.get('rmats'):
                continue  # rMATS event table: never a CDS candidate, stay quiet
            elif len(info['missing']) <= len(CDS_FIELDS) - 2:
                partial.append(info)  # close enough to be worth telling the user about
    found.sort(key=lambda info: _cds_rank(info['path']))
    partial.sort(key=lambda info: _cds_rank(info['path']))
    return found + partial if include_partial else found


# 中文备注：epitoperank：辅助处理pickCDS表（参数：candidates）
def pick_cds_table(candidates: list) -> Path | None:
    """Choose the most likely CDS table from discovered candidates."""
    paths = [Path(item['path']) if isinstance(item, dict) else Path(item) for item in candidates]
    if not paths:
        return None
    return sorted(paths, key=_cds_rank)[0]


def translate(cds: str) -> str:
    """把 CDS 翻译成蛋白序列，遇到第一个终止密码子即截断。"""
    cds = cds.strip().upper().replace('U', 'T')
    if not cds or len(cds) % 3 or set(cds) - set('ACGT'):
        raise ValueError('CDS must contain only A/C/G/T and complete codons')
    protein = ''.join(CODONS[cds[i:i+3]] for i in range(0, len(cds), 3))
    return protein.split('*', 1)[0]


# 中文备注：epitoperank：辅助处理junction候选肽（参数：reference_cds、altered_cds、junction_nt、lengths）
def junction_peptides(reference_cds: str, altered_cds: str, junction_nt: int,
                      lengths: tuple[int, ...] = (8, 9, 10, 11)) -> list[dict]:
    """Keep peptides crossing the novel exon junction, absent from reference ORF."""
    altered_cds = altered_cds.strip()
    reference = translate(reference_cds)
    altered = translate(altered_cds)
    if junction_nt <= 0 or junction_nt >= len(altered_cds):
        raise ValueError('junction_nt must be an internal nucleotide boundary in altered_cds')
    left_aa = (junction_nt - 1) // 3
    right_aa = junction_nt // 3
    if right_aa >= len(altered):
        return []  # translation terminates before the junction
    candidates = []
    for length in sorted(set(lengths)):
        if length < 8 or length > 11:
            raise ValueError('MHC-I peptide lengths must be 8..11')
        for start in range(max(0, right_aa-length+1), min(left_aa, len(altered)-length)+1):
            peptide = altered[start:start+length]
            if len(peptide) == length and peptide not in reference:
                candidates.append({'peptide': peptide, 'length': length,
                                   'start_aa': start+1, 'junction_aa': right_aa})
    return candidates


# 中文备注：epitoperank：预测IEDB（参数：peptide、allele、opener）
def predict_iedb(peptide: str, allele: str, *, opener=urlopen) -> dict:
    """Query the official IEDB MHC-I API; return its score fields verbatim."""
    if not HLA_PATTERN.fullmatch(allele):
        raise ValueError(f'Invalid class-I HLA allele: {allele}')
    body = urlencode({'method': IEDB_METHOD, 'sequence_text': peptide,
                      'allele': allele, 'length': len(peptide)}).encode()
    request = Request(IEDB_URL, data=body, headers={'Content-Type': 'application/x-www-form-urlencoded'}, method='POST')
    with opener(request, timeout=45) as response:
        content = response.read(1_000_000).decode('utf-8-sig')
    rows = list(csv.DictReader(content.splitlines(), delimiter='\t'))
    match = next((row for row in rows if row.get('peptide', '').upper() == peptide and
                  row.get('allele', allele) == allele), None)
    if not match:
        raise ValueError('IEDB response did not contain the requested peptide and allele')
    return match


# 中文备注：epitoperank：解析列索引（参数：header、column_map、detected）
def _resolve_column_index(header: list[str], column_map: dict[str, str] | None,
                          detected: dict[str, str] | None = None) -> dict[str, int]:
    """Turn a customer-confirmed (or auto-detected) mapping into column indexes."""
    names = [str(item).strip() for item in header]
    index_of = {name: position for position, name in enumerate(names)}
    canonical_positions: dict[str, int] = {}
    for position, name in enumerate(canonical_cds_fields(names)):
        canonical_positions.setdefault(name, position)

    chosen: dict[str, int] = {}
    for field in CDS_FIELDS:
        wanted = str((column_map or {}).get(field) or '').strip()
        if not wanted:
            continue
        if wanted in index_of:
            chosen[field] = index_of[wanted]
        elif wanted in canonical_positions:
            chosen[field] = canonical_positions[wanted]
        elif wanted.isdigit() and int(wanted) < len(names):
            chosen[field] = int(wanted)
        else:
            raise ValueError(f'列映射有误：表里没有列「{wanted}」（用于{CDS_FIELD_LABELS[field]}）')
    for field in CDS_FIELDS:
        if field in chosen:
            continue
        guess = str((detected or {}).get(field) or '').strip()
        if guess in index_of:
            chosen[field] = index_of[guess]
        elif field in canonical_positions:
            chosen[field] = canonical_positions[field]
    missing = [field for field in CDS_FIELDS if field not in chosen]
    if missing:
        shown = '、'.join(names[:12]) or '（空表头）'
        detail = '、'.join(f'{CDS_FIELD_LABELS[field]}（{field}）' for field in missing)
        raise ValueError(f'无法确定这些列：{detail}。当前表头：{shown}；请在列映射里手动指定。')
    return chosen


def _number_text(value) -> str:
    """把 None 或缺失值归一成空字符串，便于直接写入 TSV。"""
    return '' if value is None else value


# 中文备注：epitoperank：预测batched（参数：pairs）
def _predict_batched(pairs: list[tuple[str, str]]) -> tuple[list[dict], list[dict]]:
    """Query IEDB in batches (100 peptides per request) instead of one call per pair."""
    from epitoperank.peptide.iedb import IedbClient

    client = IedbClient()
    by_allele: dict[str, list[str]] = {}
    for peptide, allele in pairs:
        by_allele.setdefault(allele, []).append(peptide)
    scores: list[dict] = []
    errors: list[dict] = []
    for allele, peptides in by_allele.items():
        try:
            records = client.predict_mhci(peptides, [allele], method='netmhcpan_el')
        except Exception as error:  # noqa: BLE001 - surface the reason, keep candidates
            errors.append({'allele': allele, 'error': str(error)[:300],
                           'peptides': len(peptides)})
            continue
        found: dict[str, dict] = {}
        for record in records:
            found.setdefault(str(record.get('peptide') or '').upper(), record)
        for peptide in peptides:
            record = found.get(peptide.upper())
            if record is None:
                errors.append({'peptide': peptide, 'allele': allele,
                               'error': 'IEDB 未返回该肽的结果'})
                continue
            scores.append({
                'peptide': peptide, 'allele': allele, 'method': 'IEDB NetMHCpan 4.1 EL',
                'score': _number_text(record.get('score')),
                'percentile_rank': _number_text(record.get('percentile_rank')),
                'raw_result': json.dumps(record.get('raw') or {}, ensure_ascii=False, default=str),
            })
    return scores, errors


def run(input_dir: str | Path, cds_table: str | Path, output_dir: str | Path,
        *, alleles: list[str] | None = None, max_predictions: int = DEFAULT_MAX_PREDICTIONS,
        predictor=None, column_map: dict[str, str] | None = None) -> dict:
    """按列映射生成跨连接点候选肽，可选调用 IEDB 打分，并写出 TSV 与 manifest。

    单行数据错误或预测失败只记入 skipped / prediction_errors，不会中断整次运行。
    """
    dataset = load_dataset(input_dir)
    events = {}
    duplicate_ids = set()
    for event in dataset.events:
        if event.event_id in events:
            duplicate_ids.add(event.event_id)
        events[event.event_id] = event
    alleles = list(dict.fromkeys(alleles or []))
    if any(not HLA_PATTERN.fullmatch(allele) for allele in alleles):
        raise ValueError('Use class-I alleles such as HLA-A*02:01')
    if max_predictions < 1:
        raise ValueError('max_predictions must be positive')
    candidates: list[dict] = []
    skipped: list[dict] = []
    table_path = Path(cds_table)
    if not table_path.is_file():
        raise ValueError(f'编码序列表不存在：{table_path}')
    header, body, delimiter = read_table_rows(table_path)
    if not header:
        raise ValueError('编码序列表是空的，没有表头')
    detected = detect_column_map(table_path, set(events))
    column_index = _resolve_column_index(header, column_map, detected['map'])
    mapping_used = {field: header[position] for field, position in column_index.items()}

    def cell(row: list[str], field: str) -> str:
        """按已确认的列映射取出单元格文本，行不足时返回空串。"""
        position = column_index[field]
        return (row[position] if position < len(row) else '').strip()

    for number, row in enumerate(body, 2):
        if not any(str(item).strip() for item in row):
            continue
        event_id = cell(row, 'event_id')
        if event_id in duplicate_ids:
            skipped.append({'line': number, 'event_id': event_id, 'reason': 'event_id is ambiguous in event table'}); continue
        event = events.get(event_id)
        if event is None:
            skipped.append({'line': number, 'event_id': event_id, 'reason': 'event_id not found'}); continue
        try:
            peptides = junction_peptides(cell(row, 'reference_cds'), cell(row, 'altered_cds'), int(cell(row, 'junction_nt') or ''))
        except (ValueError, TypeError) as error:
            skipped.append({'line': number, 'event_id': event_id, 'reason': str(error)}); continue
        for item in peptides:
            candidates.append({'event_id': event_id, 'gene_id': event.gene_id,
                'gene_symbol': event.gene_symbol, 'event_type': event.event_type,
                'fdr': event.fdr, 'delta_psi': event.delta_psi, **item})
    # Prediction is opt-in because it sends sequences to a third-party service.
    pairs = list(dict.fromkeys((item['peptide'], allele) for item in candidates for allele in alleles))
    truncated = 0
    if len(pairs) > max_predictions:
        # Never refuse the whole run because of the cap: predict the best-scoring
        # subset (candidates are already ordered by the CDS table) and say so.
        truncated = len(pairs) - max_predictions
        pairs = pairs[:max_predictions]
    scores: list[dict] = []
    errors: list[dict] = []
    if pairs and predictor is not None:
        for peptide, allele in pairs:
            try:
                result = predictor(peptide, allele)
                scores.append({'peptide': peptide, 'allele': allele, 'method': 'IEDB NetMHCpan 4.1 EL',
                               'score': result.get('score', ''),
                               'percentile_rank': result.get('percentile_rank', ''),
                               'raw_result': json.dumps(result, ensure_ascii=False)})
            except Exception as error:  # preserve candidates if prediction service fails
                errors.append({'peptide': peptide, 'allele': allele, 'error': str(error)[:300]})
    elif pairs:
        scores, errors = _predict_batched(pairs)
    target = Path(output_dir)
    target.mkdir(parents=True, exist_ok=True)
    fields = ['event_id','gene_id','gene_symbol','event_type','fdr','delta_psi',
              'peptide','length','start_aa','junction_aa']
    for name, rows, names in [('splice_peptides.tsv', candidates, fields),
                               ('mhc_i_predictions.tsv', scores, ['peptide','allele','method','score','percentile_rank','raw_result'])]:
        with (target/name).open('w', encoding='utf-8', newline='') as handle:
            writer = csv.DictWriter(handle, fieldnames=names, delimiter='\t')
            writer.writeheader(); writer.writerows(rows)
    # 自动分级：把 IEDB 原始分数按 percentile_rank 排成可直接判读的候选表
    from epitoperank.peptide.binding_tiers import rank_predictions, tier_summary, write_ranked

    ranked = rank_predictions(scores, candidates) if scores else []
    write_ranked(target/'ranked_candidates.tsv', ranked)
    binding_tiers = tier_summary(ranked)
    manifest = {'input_dir': str(Path(input_dir).resolve()), 'cds_table': str(Path(cds_table).resolve()),
                'candidate_count': len(candidates), 'prediction_count': len(scores),
                'prediction_method': 'IEDB NetMHCpan 4.1 EL' if alleles else None,
                'prediction_attempt_count': len(pairs),
                'prediction_requested_count': len(pairs) + truncated,
                'prediction_truncated': truncated,
                'prediction_unmatched': max(0, len(pairs) - len(scores) - len(errors)),
                'column_mapping': mapping_used,
                'alleles': alleles,
                'binding_tiers': binding_tiers,
                'ranked_file': 'ranked_candidates.tsv',
                'skipped': skipped, 'prediction_errors': errors,
                'workflow_status': 'exploratory_only',
                'limitations': ['This exploratory workflow does not implement the full staged neoantigen pipeline or its evidence gates',
                                'Event quality filtering, normal proteome and GTEx filtering, NMD assessment, expression and recurrence analysis are not performed',
                                'Candidate peptides require supplied, frame-correct reference and altered CDS',
                                'MHC binding prediction does not prove antigen presentation or T-cell response',
                                'Novelty is checked against the supplied reference CDS only']}
    (target/'neoantigen_manifest.json').write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding='utf-8')
    return {'path': str(target), **manifest}
