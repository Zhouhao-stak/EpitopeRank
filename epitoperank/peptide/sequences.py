"""Peptide sequence primitives.

Everything downstream (prediction, filtering, scoring) relies on these
helpers, so they are deliberately strict about what a peptide is:
uppercase, single-letter amino acids, no whitespace, no stop codons.
"""

from __future__ import annotations

import hashlib
import re
from bisect import bisect_right
from pathlib import Path
from typing import Iterable, Iterator

#: The 20 standard amino acids. Ambiguous codes are rejected by default
#: because they cannot be looked up in binding models or matched against a
#: reference proteome.
AA_ALPHABET = frozenset("ACDEFGHIKLMNPQRSTVWY")
AA_AMBIGUOUS = frozenset("XBZUO")
_STRICT_RE = re.compile(r"^[ACDEFGHIKLMNPQRSTVWY]+$")
#: Accepted amino-acid lengths for the two MHC classes.
MHC_I_LENGTHS: tuple[int, ...] = (8, 9, 10, 11)
MHC_II_LENGTHS: tuple[int, ...] = (15,)


class SequenceError(ValueError):
    """Raised when a peptide or FASTA record is not usable."""


# 中文备注：肽预测：规范化肽段（参数：value、allow_ambiguous）
def normalize_peptide(value: object, *, allow_ambiguous: bool = False) -> str:
    """Return an uppercase peptide, or raise :class:`SequenceError`.

    Whitespace inside the string is removed so that copy/pasted FASTA-style
    sequences do not silently become invalid.
    """
    if not isinstance(value, str):
        raise SequenceError("peptide must be a string")
    peptide = "".join(value.split()).upper()
    if not peptide:
        raise SequenceError("peptide is empty")
    allowed = AA_ALPHABET | AA_AMBIGUOUS if allow_ambiguous else AA_ALPHABET
    bad = sorted(set(peptide) - allowed)
    if bad:
        raise SequenceError(f"unsupported residue(s) in peptide: {''.join(bad)}")
    return peptide


# 中文备注：肽预测：校验肽段（参数：value、lengths、allow_ambiguous）
def validate_peptide(value: object, *, lengths: Iterable[int] = MHC_I_LENGTHS,
                     allow_ambiguous: bool = False) -> str:
    """Normalize and check that the length is one the requested model supports."""
    peptide = normalize_peptide(value, allow_ambiguous=allow_ambiguous)
    allowed = tuple(sorted(set(int(item) for item in lengths)))
    if len(peptide) not in allowed:
        raise SequenceError(
            f"peptide length {len(peptide)} is not supported (allowed: "
            f"{', '.join(str(item) for item in allowed)})"
        )
    return peptide


# 中文备注：肽预测：摘要肽段（参数：peptide）
def peptide_digest(peptide: str) -> str:
    """Stable short identifier used in caches and result tables."""
    return hashlib.sha1(peptide.encode("ascii")).hexdigest()[:16]


# 中文备注：肽预测：辅助处理unique（参数：items）
def unique(items: Iterable[str]) -> list[str]:
    """Deduplicate while preserving first-seen order."""
    return list(dict.fromkeys(items))


def file_sha256(path: str | Path, *, chunk_size: int = 1024 * 1024) -> str:
    """分块计算文件 SHA-256，用于记录参考数据的溯源校验值。"""
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for block in iter(lambda: handle.read(chunk_size), b""):
            digest.update(block)
    return digest.hexdigest()


# 中文备注：肽预测：读取fasta（参数：path、kind）
def read_fasta(path: str | Path, *, kind: str = "protein") -> Iterator[tuple[str, str]]:
    """Stream ``(header, sequence)`` pairs, rejecting empty or malformed records.

    ``kind='protein'`` permits the ambiguous IUPAC codes found in UniProt
    records (X/B/Z/U/O); ``kind='peptide'`` only allows the 20 standard
    residues.  Blank lines are ignored; ``*`` stop characters are stripped
    from protein records but rejected in peptides.
    """
    path = Path(path)
    headers_seen: set[str] = set()
    name: str | None = None
    chunks: list[str] = []

    def finish() -> tuple[str, str]:
        """收尾当前 FASTA 记录：校验并返回 (header, 序列)。"""
        assert name is not None
        sequence = "".join(chunks).upper()
        if not sequence:
            raise SequenceError(f"empty FASTA sequence for {name!r} in {path.name}")
        if kind == "peptide":
            if not _STRICT_RE.fullmatch(sequence):
                raise SequenceError(f"non-standard residues in peptide FASTA record {name!r}")
        else:
            sequence = sequence.replace("*", "")
            if not sequence or not sequence.isascii() or not sequence.isalpha():
                raise SequenceError(f"invalid protein FASTA record {name!r} in {path.name}")
        return name, sequence

    with path.open(encoding="utf-8-sig") as handle:
        for raw in handle:
            line = raw.strip()
            if not line or line.startswith(";"):
                continue
            if line.startswith(">"):
                header = line[1:].strip()
                if not header:
                    raise SequenceError(f"empty FASTA header in {path.name}")
                if name is not None:
                    yield finish()
                if header in headers_seen:
                    raise SequenceError(f"duplicate FASTA header {header!r} in {path.name}")
                headers_seen.add(header)
                name, chunks = header, []
            else:
                if name is None:
                    raise SequenceError(f"sequence data before first FASTA header in {path.name}")
                chunks.append(line)
    if name is None:
        raise SequenceError(f"no FASTA records in {path.name}")
    yield finish()


class SelfReference:
    """Exact substring matching against one or more reference proteomes.

    The proteins are concatenated with a ``*`` separator (which can never be
    part of a peptide), so one :meth:`str.find` call scans the whole proteome
    at C speed.  Matches are mapped back to protein headers with a binary
    search over cumulative offsets.

    This answers a single, narrow question: *does this exact peptide occur in
    the supplied sequences?*  It is not a BLAST search; near-identical or
    paralogous sequences are not reported unless they contain the peptide.
    """

    #: Sentinel that separates proteins. Never a valid amino acid.
    SEPARATOR = "*"
    #: Cap per peptide so a low-complexity peptide cannot explode the output.
    MAX_HITS_PER_PEPTIDE = 25

    def __init__(self, proteins: Iterable[tuple[str, str]]) -> None:
        """把多条蛋白拼接成以 ``*`` 分隔的长串，并记录各蛋白起始偏移。"""
        names: list[str] = []
        parts: list[str] = []
        offsets: list[int] = []
        cursor = 0
        for name, sequence in proteins:
            sequence = sequence.upper().replace("*", "")
            if not sequence:
                continue
            names.append(name)
            offsets.append(cursor)
            parts.append(sequence)
            cursor += len(sequence) + 1  # separator
        if not names:
            raise SequenceError("reference proteome is empty")
        self.names = names
        self.offsets = offsets
        self._blob = self.SEPARATOR.join(parts)
        self.protein_count = len(names)

    @classmethod
    def from_fasta(cls, *paths: str | Path) -> "SelfReference":
        """从一或多个蛋白 FASTA 文件构建参考索引。"""
        proteins: list[tuple[str, str]] = []
        for path in paths:
            proteins.extend(read_fasta(path, kind="protein"))
        return cls(proteins)

    # 中文备注：肽预测：辅助处理hits（参数：peptides）
    def hits(self, peptides: Iterable[str]) -> dict[str, list[str]]:
        """Map each peptide to the headers of proteins that contain it exactly."""
        result: dict[str, list[str]] = {}
        for peptide in unique(peptides):
            peptide = normalize_peptide(peptide)
            found: list[str] = []
            start = 0
            while len(found) < self.MAX_HITS_PER_PEPTIDE:
                index = self._blob.find(peptide, start)
                if index < 0:
                    break
                protein = bisect_right(self.offsets, index) - 1
                header = self.names[protein]
                if not found or found[-1] != header:
                    found.append(header)
                start = index + 1
            result[peptide] = found
        return result

    def contains(self, peptide: str) -> bool:
        """判断该肽段是否作为精确子串出现在参考蛋白集合中。"""
        return self._blob.find(normalize_peptide(peptide)) >= 0
