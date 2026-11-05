"""rMATS output parser.

Ported and generalized from the SplicingNexus v2 production normalizer
(``stage1_docker_adapter.normalise_rmats_results``): converts rMATS
junction-count tables for SE / A5SS / A3SS / MXE / RI events into the
standardized ``AS_event_master`` contract.

文件名兼容性说明
----------------
rMATS 官方输出叫 ``SE.MATS.JC.txt``，但实际拿到的数据几乎从不叫这个名字：
上游流水线会加上比较组前缀（``UPF1_KD_vs_ctrl_SE.MATS.JCEC.txt``）、
换成 ``.JCEC`` 计数模式、用 ``-`` 或纯数字编号、转成小写、或者压成 ``.gz``。
因此本模块**不依赖固定文件名**，改用两级识别：

1. **内容签名**（最可靠）：读表头，按 rMATS 各事件特有的坐标列判断类型。
2. **文件名线索**：把文件名切成词元，匹配 ``SE`` / ``A3SS`` / ``A5SS`` /
   ``MXE`` / ``RI``，同时识别 ``JC`` / ``JCEC`` 两种计数模式。

两者一致时置信度最高；只有文件名时也能用；只有内容时除 A3SS/A5SS
（二者表头完全相同）以外都能判定。目录里同时存在 JC 与 JCEC 时优先 JC。
"""

from __future__ import annotations

import csv
import gzip
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable, Mapping

from epitoperank.splicing.schema import StandardEvent, _to_float, _to_int

#: 支持的五类可变剪接事件。
EVENT_TYPES: tuple[str, ...] = ("SE", "A5SS", "A3SS", "MXE", "RI")

#: 官方输出文件名，仅作为“最规范命名”的加分项，不再作为唯一入口。
RMATS_EVENT_FILES: dict[str, str] = {
    "SE": "SE.MATS.JC.txt",
    "A5SS": "A5SS.MATS.JC.txt",
    "A3SS": "A3SS.MATS.JC.txt",
    "MXE": "MXE.MATS.JC.txt",
    "RI": "RI.MATS.JC.txt",
}

#: 事件类型在文件名中的词元模式。顺序按“先具体后笼统”排列，
#: 保证 ``A3SS`` 不会因为含 ``SS`` 而被误判，``SE`` 也不会吃掉别的前缀。
_FILENAME_TOKEN_PATTERNS: tuple[tuple[str, re.Pattern[str]], ...] = (
    ("A3SS", re.compile(r"(?:^|[^a-z0-9])a3ss(?:[^a-z0-9]|$)")),
    ("A5SS", re.compile(r"(?:^|[^a-z0-9])a5ss(?:[^a-z0-9]|$)")),
    ("MXE", re.compile(r"(?:^|[^a-z0-9])mxe(?:[^a-z0-9]|$)")),
    ("RI", re.compile(r"(?:^|[^a-z0-9])ri(?:[^a-z0-9]|$)")),
    ("SE", re.compile(r"(?:^|[^a-z0-9])se(?:[^a-z0-9]|$)")),
)

#: 表头特征列 -> 事件类型。用于只看内容就能判定的场景。
#: A3SS 与 A5SS 的 rMATS 输出表头逐列相同，只能给出 ``A3SS/A5SS`` 这个并列结论。
_HEADER_SIGNATURES: tuple[tuple[str, frozenset[str]], ...] = (
    ("MXE", frozenset({"1stexonstart_0base", "2ndexonend"})),
    ("RI", frozenset({"riexonstart_0base", "riexonend"})),
    ("SE", frozenset({"exonstart_0base", "upstreames", "downstreames"})),
    ("A3SS/A5SS", frozenset({"longexonstart_0base", "shortes", "flankinges"})),
)

#: 判定“这确实是一张 rMATS 表”的必需信号（任一命中即可进入解析）。
_TABLE_MARKERS: tuple[str, ...] = (
    "inclevel1",
    "inc_level_1",
    "ijc_sample_1",
    "sjc_sample_1",
    "ijc_sample1",
    "sjc_sample1",
)

#: 只在同一种事件类型里区分 JC / JCEC 用的词元。
_COUNT_MODE_TOKENS: tuple[tuple[str, re.Pattern[str]], ...] = (
    ("JCEC", re.compile(r"(?:^|[^a-z0-9])jcec(?:[^a-z0-9]|$)")),
    ("JC", re.compile(r"(?:^|[^a-z0-9])jc(?:[^a-z0-9]|$)")),
)

#: 坐标字段，键为事件类型，值为取用的列名（统一小写）。
_RMATS_COORDINATE_FIELDS: dict[str, tuple[str, str]] = {
    "SE": ("exonstart_0base", "exonend"),
    "RI": ("upstreamee", "downstreames"),
    "A5SS": ("longexonstart_0base", "longexonend"),
    "A3SS": ("longexonstart_0base", "longexonend"),
    "MXE": ("1stexonstart_0base", "2ndexonend"),
}

#: 允许的表格扩展名（``.gz`` 另行处理）。
_TABLE_SUFFIXES: frozenset[str] = frozenset({".txt", ".tsv", ".csv", ".tab"})


@dataclass(frozen=True)
class RMATSTable:
    """一张被识别出来的 rMATS 事件表。

    :param event_type: SE / A5SS / A3SS / MXE / RI。
    :param path: 文件路径。
    :param count_mode: ``JC``、``JCEC`` 或 ``""``（文件名未标注）。
    :param detected_by: ``header`` / ``filename`` / ``both``，说明判定依据。
    """

    event_type: str
    path: Path
    count_mode: str = ""
    detected_by: str = "filename"

    @property
    def name(self) -> str:
        """返回文件名，便于日志与前端展示。"""
        return self.path.name


def _record(row: Mapping[str, Any]) -> dict[str, str]:
    """把一行 rMATS 记录归一化为「列名小写、值去掉引号与空白」的字典。

    不同 rMATS 版本（含 rMATS-turbo 与各类封装）列名大小写不一致，
    统一小写后配合别名表查找，避免因为 ``GeneSymbol`` / ``geneSymbol``
    这类差异导致整列为空。
    """
    normalized: dict[str, str] = {}
    for key, value in row.items():
        if key is None:
            continue
        normalized[key.strip().lower()] = str(value or "").strip().strip('"')
    return normalized


def _pick(row: Mapping[str, str], *aliases: str) -> str:
    """按别名顺序取第一个非空值，全部缺失时返回空串。"""
    for alias in aliases:
        value = row.get(alias)
        if value not in (None, ""):
            return value
    return ""


def _numbers(value: Any, cast: type[float] | type[int]) -> list[float] | list[int]:
    """把 rMATS 中以逗号分隔的逐样本数值字段（如 IncLevel1）解析为列表，跳过 NA 等缺失项。"""
    values: list[float] | list[int] = []
    for item in str(value or "").split(","):
        if item.strip() in {"", "NA", "nan", "NaN"}:
            continue
        try:
            values.append(cast(item.strip()))
        except ValueError:
            continue
    return values


def _mean(values: list[float]) -> float | None:
    """返回数值列表的算术平均值，空列表返回 None。"""
    return sum(values) / len(values) if values else None


def _coordinates(event_type: str, row: Mapping[str, str]) -> str:
    """拼出 ``chr:start-end``，坐标转为 1-based 闭区间。

    rMATS 的起始列是 0-based，平台契约沿用 GTF/GFF 的 1-based 闭区间，
    因此起始位点 +1。缺列时退化为空字符串而不是抛错。
    """
    fields = _RMATS_COORDINATE_FIELDS.get(event_type)
    if not fields:
        return ""
    start_field, end_field = fields
    raw_start = row.get(start_field, "")
    try:
        start = str(int(raw_start) + 1)
    except (TypeError, ValueError):
        start = raw_start
    return f"{_pick(row, 'chr', 'chrom', 'chromosome')}:{start}-{row.get(end_field, '')}"


def _open_text(path: Path):
    """以文本方式打开表格，自动识别 ``.gz`` 压缩，编码按 utf-8-sig 兜底 latin-1。"""
    if path.suffix.lower() == ".gz":
        return gzip.open(path, "rt", encoding="utf-8-sig", errors="replace", newline="")
    return path.open("r", encoding="utf-8-sig", errors="replace", newline="")


def _is_table_name(path: Path) -> bool:
    """判断文件名是否是可能承载表格的文件（含 ``.txt.gz`` 这类双扩展名）。"""
    name = path.name.lower()
    if name.startswith("."):
        return False
    if name.endswith(".gz"):
        name = name[: -len(".gz")]
    return Path(name).suffix in _TABLE_SUFFIXES


def _read_header(path: Path) -> list[str]:
    """读取表头并归一化为小写列名列表，失败时返回空列表。"""
    try:
        with _open_text(path) as handle:
            header = next(csv.reader(handle, delimiter="\t"), None)
    except (OSError, csv.Error, UnicodeError):
        return []
    if not header:
        return []
    return [column.strip().strip('"').lower() for column in header]


def event_type_from_header(header: Iterable[str]) -> str | None:
    """按表头特征列推断事件类型。

    :return: ``SE`` / ``MXE`` / ``RI``；A3SS 与 A5SS 表头相同，返回
        ``"A3SS/A5SS"``；无法判定时返回 ``None``。
    """
    columns = {str(column).strip().lower() for column in header}
    if not columns:
        return None
    for event_type, required in _HEADER_SIGNATURES:
        if required.issubset(columns):
            return event_type
    return None


def event_type_from_filename(name: str) -> str | None:
    """从文件名推断事件类型，识别不到或有歧义时返回 None。

    只做词元级匹配（要求前后是非字母数字），所以 ``SERBP1_SE.MATS.JC.txt``
    里的 ``SERBP1`` 不会被误判成 ``SE``。
    """
    lowered = name.lower()
    if lowered.endswith(".gz"):
        lowered = lowered[: -len(".gz")]
    matched = [event_type for event_type, pattern in _FILENAME_TOKEN_PATTERNS if pattern.search(lowered)]
    if len(matched) == 1:
        return matched[0]
    return None


def count_mode_from_filename(name: str) -> str:
    """从文件名推断计数模式，返回 ``JC`` / ``JCEC`` / 空串。

    ``JC`` 只看剪接连接（junction counts），``JCEC`` 额外纳入外显子计数。
    两者同时出现（例如 ``..._JC_vs_JCEC...``）时视为未知。
    """
    lowered = name.lower()
    found = [mode for mode, pattern in _COUNT_MODE_TOKENS if pattern.search(lowered)]
    return found[0] if len(found) == 1 else ""


def _is_mats_name(name: str) -> bool:
    """文件名里是否带 ``MATS`` 标记（rMATS 官方命名特征，作为加分项而非必要条件）。"""
    return "mats" in name.lower()


def _score_table(table: RMATSTable, canonical_name: str) -> int:
    """给候选表打分，用于同一事件类型出现多份文件时择优。

    优先级依次是：内容与文件名双重确认 > 官方命名 > JC 优于 JCEC > 路径更浅。
    """
    score = 0
    if table.detected_by == "both":
        score += 40
    elif table.detected_by == "header":
        score += 30
    else:
        score += 20
    if table.path.name == canonical_name:
        score += 25
    if _is_mats_name(table.path.name):
        score += 6
    if table.count_mode == "JC":
        score += 5
    elif table.count_mode == "JCEC":
        score += 1
    score -= len(table.path.parts)
    return score


def _iter_candidate_files(directory: Path, max_depth: int) -> list[Path]:
    """列出目录（含若干层子目录）里名称像表格的文件。

    限制深度是为了不被 ``.git``、``node_modules`` 之类的深层噪音拖慢；
    真实使用中 rMATS 结果最多嵌一层 ``rmats/`` 子目录。
    """
    root_depth = len(directory.parts)
    candidates: list[Path] = []
    stack: list[Path] = [directory]
    while stack:
        current = stack.pop()
        try:
            entries = list(current.iterdir())
        except OSError:
            continue
        for entry in entries:
            try:
                if entry.is_dir():
                    if len(entry.parts) - root_depth < max_depth and not entry.name.startswith("."):
                        stack.append(entry)
                    continue
            except OSError:
                continue
            if _is_table_name(entry):
                candidates.append(entry)
    return candidates


def discover_rmats_tables(
    directory: str | Path,
    max_depth: int = 2,
) -> dict[str, RMATSTable]:
    """在目录中找出五类事件表，返回 ``事件类型 -> 选中文件``。

    识别策略是「内容优先、文件名兜底、两者互证」：

    1. 读表头做内容签名，能确定的类型直接采用（A3SS/A5SS 例外，见下）；
    2. 文件名里的 ``SE``/``A3SS``/... 词元作为候选类型；
    3. A3SS 与 A5SS 表头完全一致，只能靠文件名区分——若文件名也没写，
       跳过并在调用方给出提示，绝不猜测。

    :param directory: rMATS 输出所在目录。
    :param max_depth: 向下搜索的子目录层数，默认 2。
    :return: 事件类型到表的映射，未找到的类型不出现在结果里。
    """
    path = Path(directory)
    if not path.is_dir():
        return {}
    best: dict[str, tuple[int, RMATSTable]] = {}
    for candidate in _iter_candidate_files(path, max_depth):
        header = _read_header(candidate)
        lowered_header = set(header)
        has_markers = any(marker in lowered_header for marker in _TABLE_MARKERS)
        header_type = event_type_from_header(header) if header else None
        name_type = event_type_from_filename(candidate.name)
        if not has_markers:
            # 表头缺 rMATS 特征列时，仅当文件名同时带有 MATS 与事件类型词元
            # 才接受（例如尚未写入内容的占位表）。空表、只有表头的小样本在
            # 真实交付里很常见，直接判“不是 rMATS”会让用户无所适从。
            if not (name_type and _is_mats_name(candidate.name)):
                continue
            event_type, detected_by = name_type, "filename"
        elif header_type in {"A3SS/A5SS"}:
            # 表头只能定位到 A3SS/A5SS 家族，真正的类型必须由文件名给出。
            event_type = name_type if name_type in {"A3SS", "A5SS"} else None
            detected_by = "both" if event_type else "header"
        elif header_type and name_type and header_type == name_type:
            event_type, detected_by = header_type, "both"
        elif header_type:
            event_type, detected_by = header_type, "header"
        elif name_type:
            event_type, detected_by = name_type, "filename"
        else:
            continue
        if event_type is None:
            continue
        table = RMATSTable(
            event_type=event_type,
            path=candidate,
            count_mode=count_mode_from_filename(candidate.name),
            detected_by=detected_by,
        )
        score = _score_table(table, RMATS_EVENT_FILES.get(event_type, ""))
        if event_type not in best or score > best[event_type][0]:
            best[event_type] = (score, table)
    return {event_type: table for event_type, (_, table) in best.items()}


def infer_event_type(path: str | Path) -> str | None:
    """推断单个文件属于哪类事件，内容签名优先，文件名兜底。"""
    file_path = Path(path)
    header_type = event_type_from_header(_read_header(file_path))
    name_type = event_type_from_filename(file_path.name)
    if header_type in {"A3SS/A5SS"}:
        return name_type if name_type in {"A3SS", "A5SS"} else None
    if header_type and name_type and header_type == name_type:
        return header_type
    return header_type or name_type


def parse_rmats_file(
    path: str | Path,
    event_type: str | None = None,
    group1_samples: list[str] | None = None,
    group2_samples: list[str] | None = None,
) -> list[StandardEvent]:
    """Parse one rMATS JC table into standardized events.

    :param path: rMATS output file (e.g. ``SE.MATS.JC.txt``，也接受任意命名)。
    :param event_type: one of SE / A5SS / A3SS / MXE / RI；省略时按内容与
        文件名自动推断，推断不出则返回空列表。
    :param group1_samples: sample ids of the control group (rMATS sample set 1).
    :param group2_samples: sample ids of the experimental group (rMATS sample set 2).
    """
    path = Path(path)
    if not path.is_file():
        return []
    if event_type is None:
        event_type = infer_event_type(path)
    if event_type not in _RMATS_COORDINATE_FIELDS:
        return []
    group1 = list(group1_samples or [])
    group2 = list(group2_samples or [])
    sample_ids = [*group1, *group2]
    events: list[StandardEvent] = []
    try:
        handle = _open_text(path)
    except OSError:
        return []
    with handle:
        reader = csv.DictReader(handle, delimiter="\t")
        if not reader.fieldnames:
            return []
        field_names = {str(name).strip().strip('"').lower() for name in reader.fieldnames if name}
        # 表头连一个 rMATS 特征列都没有，说明这不是 rMATS 表，直接放弃，
        # 免得把日志、说明文件解析成一堆空事件。
        if not any(marker in field_names for marker in _TABLE_MARKERS):
            return []
        for raw in reader:
            row = _record(raw)
            control_psi = _numbers(_pick(row, "inclevel1", "inc_level_1", "psi_1"), float)
            experiment_psi = _numbers(_pick(row, "inclevel2", "inc_level_2", "psi_2"), float)
            mean_control, mean_experiment = _mean(control_psi), _mean(experiment_psi)
            inclusion = sum(_numbers(_pick(row, "ijc_sample_1", "ijc_sample1"), int)) + sum(
                _numbers(_pick(row, "ijc_sample_2", "ijc_sample2"), int)
            )
            exclusion = sum(_numbers(_pick(row, "sjc_sample_1", "sjc_sample1"), int)) + sum(
                _numbers(_pick(row, "sjc_sample_2", "sjc_sample2"), int)
            )
            psi_values = [*control_psi, *experiment_psi]
            psi_by_sample = {
                sample_id: psi_values[index]
                for index, sample_id in enumerate(sample_ids)
                if index < len(psi_values)
            }
            delta = (
                None
                if mean_control is None or mean_experiment is None
                else round(mean_experiment - mean_control, 6)
            )
            events.append(
                StandardEvent(
                    event_id=f"{event_type}:{_pick(row, 'id') or len(events) + 1}",
                    gene_id=_pick(row, "geneid", "gene_id", "ensembl_gene_id"),
                    gene_symbol=_pick(row, "genesymbol", "gene_symbol", "symbol"),
                    event_type=event_type,
                    chromosome=_pick(row, "chr", "chrom", "chromosome"),
                    strand=_pick(row, "strand"),
                    genomic_coordinates=_coordinates(event_type, row),
                    coordinate_system="1-based-inclusive",
                    source_tool="rMATS",
                    mean_psi_group1=mean_control,
                    mean_psi_group2=mean_experiment,
                    delta_psi=delta,
                    p_value=_to_float(_pick(row, "pvalue", "p_value", "p-value", "pval")),
                    fdr=_to_float(_pick(row, "fdr", "qvalue", "q_value", "padj")),
                    psi_by_sample=psi_by_sample,
                    inclusion_reads=inclusion,
                    exclusion_reads=exclusion,
                    total_support_reads=inclusion + exclusion,
                    valid_sample_count=len(psi_by_sample),
                )
            )
    return events


def parse_rmats_directory(
    rmats_output: str | Path,
    group1_samples: list[str],
    group2_samples: list[str],
) -> list[StandardEvent]:
    """Parse all rMATS tables found in ``rmats_output``.

    文件按内容与命名自动识别，不要求客户改文件名；同一事件类型存在多份时
    择优（官方命名 > JC > JCEC > 路径更浅）。
    """
    events: list[StandardEvent] = []
    for event_type, table in discover_rmats_tables(rmats_output).items():
        events.extend(
            parse_rmats_file(table.path, event_type, group1_samples, group2_samples)
        )
    return events


def is_rmats_directory(path: str | Path) -> bool:
    """Heuristic: a directory containing at least one recognizable rMATS table."""
    return bool(discover_rmats_tables(path))
