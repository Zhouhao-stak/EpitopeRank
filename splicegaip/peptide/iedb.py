"""Client for the IEDB Analysis Resource REST API.

The client is intentionally thin and auditable:

* every request is hashed and (optionally) cached on disk,
* every prediction record carries the exact method name/version and the
  request hash, so a result table can be reproduced or inspected later,
* the class-I, class-II, processing, stability and MHC-NP endpoints share one
  transport with retries and a polite inter-request delay.

Prediction is *not* the same as presentation or immunogenicity; see
``docs/PEPTIDE.md`` for the interpretation rules the platform enforces.
"""

from __future__ import annotations

import csv
import hashlib
import io
import json
import os
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable, Iterable, Sequence
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from .hla import HlaAllele, parse_panel
from .sequences import MHC_I_LENGTHS, MHC_II_LENGTHS, normalize_peptide, unique

TOOLS_URL = "https://tools-cluster-interface.iedb.org/tools_api/"
QUERY_URL = "https://query-api.iedb.org/"
USER_AGENT = "SpliceGAIP/1.0 (peptide prediction; https://github.com/)"
#: IEDB asks clients not to hammer the service; ~6 requests/second at most.
DEFAULT_MIN_INTERVAL = 0.15
#: Maximum sequences sent in one POST (IEDB gets slow with large FASTA input).
MAX_SEQUENCES_PER_REQUEST = 100


class IedbError(RuntimeError):
    """Base class for prediction-service failures."""


class IedbUnavailable(IedbError):
    """The service could not be reached (network/DNS/timeout)."""


class IedbResponseError(IedbError):
    """The service answered, but not with a usable prediction table."""


@dataclass(frozen=True)
class Method:
    """One selectable prediction model."""

    key: str
    api_method: str
    label: str
    tool: str
    mhc_class: int
    #: Column that carries the model score (kept verbatim in ``raw``).
    score_field: str = "score"

    def as_dict(self) -> dict[str, object]:
        return {
            "key": self.key,
            "api_method": self.api_method,
            "label": self.label,
            "tool": self.tool,
            "mhc_class": self.mhc_class,
        }


METHODS: dict[str, Method] = {
    "netmhcpan_el": Method("netmhcpan_el", "netmhcpan_el-4.1",
                           "NetMHCpan-4.1 EL (IEDB recommended epitope)", "mhci", 1),
    "netmhcpan_ba": Method("netmhcpan_ba", "netmhcpan_ba-4.1",
                           "NetMHCpan-4.1 BA (binding affinity)", "mhci", 1),
    "netmhcstabpan": Method("netmhcstabpan", "netmhcstabpan-1.0",
                            "NetMHCstabpan-1.0 (peptide-MHC stability)", "mhci", 1),
    "netmhciipan_el": Method("netmhciipan_el", "netmhciipan_el-4.1",
                             "NetMHCIIpan-4.1 EL (IEDB recommended epitope)", "mhcii", 2),
    "netmhciipan_ba": Method("netmhciipan_ba", "netmhciipan_ba-4.1",
                             "NetMHCIIpan-4.1 BA (binding affinity)", "mhcii", 2),
    "processing": Method("processing", "recommended",
                         "IEDB MHC-I processing (proteasome + TAP + MHC)", "processing", 1),
    "mhcnp": Method("mhcnp", "mhcnp", "MHC-NP (natural processing)", "mhcnp", 1),
}

DEFAULT_METHODS: dict[int, str] = {1: "netmhcpan_el", 2: "netmhciipan_el"}


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _default_cache_dir() -> Path:
    override = os.getenv("SPLICEGAIP_PEPTIDE_CACHE")
    if override:
        return Path(override).expanduser()
    try:
        from splicegaip.storage import default_runtime_root

        return default_runtime_root() / "peptide_cache"
    except Exception:  # noqa: BLE001 - cache is optional
        return Path.home() / ".cache" / "splicegaip-peptide"


def _env_float(name: str, default: float) -> float:
    try:
        return float(os.getenv(name, "") or default)
    except ValueError:
        return default


def _env_int(name: str, default: int) -> int:
    try:
        return int(os.getenv(name, "") or default)
    except ValueError:
        return default


def _float(value: object) -> float | None:
    try:
        result = float(str(value))
    except (TypeError, ValueError):
        return None
    if result != result or result in (float("inf"), float("-inf")):
        return None
    return result


@dataclass
class IedbClient:
    """Synchronous IEDB client with retries and an optional disk cache."""

    #: IEDB is occasionally slow from shared/cloud networks; both knobs are
    #: environment-tunable so a deployment can raise the ceiling without a
    #: code change.
    timeout: float = field(default_factory=lambda: _env_float("SPLICEGAIP_PEPTIDE_TIMEOUT", 45.0))
    retries: int = field(default_factory=lambda: _env_int("SPLICEGAIP_PEPTIDE_RETRIES", 2))
    min_interval: float = DEFAULT_MIN_INTERVAL
    cache_dir: Path | None = field(default_factory=_default_cache_dir)
    cache_read: bool = True
    cache_write: bool = True
    opener: Callable[..., object] = urlopen
    sleep: Callable[[float], None] = time.sleep
    last_request_at: float = 0.0
    #: Populated with one entry per network call (for manifests).
    calls: list[dict[str, object]] = field(default_factory=list)

    # ------------------------------------------------------------------
    # Transport
    # ------------------------------------------------------------------
    def _throttle(self) -> None:
        if self.min_interval <= 0:
            return
        elapsed = time.monotonic() - self.last_request_at
        if elapsed < self.min_interval:
            self.sleep(self.min_interval - elapsed)

    def _cache_file(self, key: str) -> Path | None:
        if not self.cache_dir:
            return None
        return Path(self.cache_dir) / f"{key}.json"

    def _cache_key(self, url: str, payload: dict[str, str]) -> str:
        blob = json.dumps([url, sorted(payload.items())], ensure_ascii=False)
        return hashlib.sha256(blob.encode("utf-8")).hexdigest()[:32]

    def _read_cache(self, key: str) -> str | None:
        path = self._cache_file(key)
        if not path or not self.cache_read or not path.is_file():
            return None
        try:
            return str(json.loads(path.read_text(encoding="utf-8"))["text"])
        except (OSError, ValueError, KeyError):
            return None

    def _write_cache(self, key: str, url: str, payload: dict[str, str], text: str) -> None:
        path = self._cache_file(key)
        if not path or not self.cache_write:
            return
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(
                json.dumps(
                    {"url": url, "payload": payload, "text": text,
                     "request_id": key, "fetched_at": _now()},
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )
        except OSError:  # cache failure must never break prediction
            pass

    def _post(self, url: str, payload: dict[str, str]) -> tuple[str, str]:
        key = self._cache_key(url, payload)
        cached = self._read_cache(key)
        if cached is not None:
            self.calls.append({"url": url, "request_id": key, "cached": True})
            return cached, key
        body = urlencode(payload).encode("utf-8")
        error: Exception | None = None
        for attempt in range(self.retries + 1):
            self._throttle()
            request = Request(
                url,
                data=body,
                headers={
                    "Content-Type": "application/x-www-form-urlencoded",
                    "User-Agent": USER_AGENT,
                },
                method="POST",
            )
            try:
                with self.opener(request, timeout=self.timeout) as response:
                    raw = response.read(8_000_000)
                text = raw.decode("utf-8-sig", errors="replace")
                self.last_request_at = time.monotonic()
                self._write_cache(key, url, payload, text)
                self.calls.append({"url": url, "request_id": key, "cached": False,
                                   "status": getattr(response, "status", 200)})
                return text, key
            except HTTPError as exc:
                self.last_request_at = time.monotonic()
                error = exc
                if exc.code < 500:
                    detail = ""
                    try:
                        detail = exc.read(500).decode("utf-8", errors="replace")
                    except Exception:  # noqa: BLE001
                        pass
                    raise IedbResponseError(
                        f"IEDB returned HTTP {exc.code} for {url}: {detail.strip()[:300]}"
                    ) from exc
                self.sleep(min(2 ** attempt, 8))
            except (URLError, TimeoutError, OSError) as exc:
                self.last_request_at = time.monotonic()
                error = exc
                self.sleep(min(2 ** attempt, 8))
        raise IedbUnavailable(f"IEDB request failed after {self.retries + 1} attempts: {error}")

    def _get(self, url: str) -> object:
        key = self._cache_key(url, {})
        path = self._cache_file(key)
        if path and self.cache_read and path.is_file():
            try:
                return json.loads(path.read_text(encoding="utf-8"))["json"]
            except (OSError, ValueError, KeyError):
                pass
        request = Request(url, headers={"Accept": "application/json", "User-Agent": USER_AGENT})
        try:
            with self.opener(request, timeout=self.timeout) as response:
                raw = response.read(4_000_000)
        except HTTPError as exc:
            raise IedbResponseError(f"IEDB query API returned HTTP {exc.code}: {url}") from exc
        except (URLError, TimeoutError, OSError) as exc:
            raise IedbUnavailable(f"IEDB query API unreachable: {exc}") from exc
        payload = json.loads(raw.decode("utf-8", errors="replace"))
        if path and self.cache_write:
            try:
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(json.dumps({"url": url, "json": payload}, ensure_ascii=False),
                                encoding="utf-8")
            except OSError:
                pass
        return payload

    # ------------------------------------------------------------------
    # Parsing helpers
    # ------------------------------------------------------------------
    @staticmethod
    def _parse_table(text: str) -> list[dict[str, str]]:
        stripped = text.lstrip("\ufeff \t\r\n")
        if not stripped or stripped.lower().startswith(("error", "__all__", "input ")):
            raise IedbResponseError(f"IEDB did not return a table: {stripped[:300]!r}")
        reader = csv.DictReader(io.StringIO(stripped), delimiter="\t")
        rows = [{(key or "").strip(): (value or "").strip() for key, value in row.items()}
                for row in reader]
        # A header-only table is a legitimate "no window of this length" answer.
        return [row for row in rows if any(row.values())]

    @staticmethod
    def _lengths_present(peptides: Sequence[str], lengths: Sequence[int]) -> tuple[int, ...]:
        requested = {int(item) for item in lengths}
        present = sorted({len(item) for item in peptides} & requested)
        return tuple(present)

    @staticmethod
    def _fasta(peptides: Sequence[str]) -> tuple[str, dict[int, str]]:
        """Return FASTA text plus the ``seq_num -> peptide`` map."""
        mapping = {index + 1: peptide for index, peptide in enumerate(peptides)}
        text = "\n".join(f">p{index}\n{peptide}" for index, peptide in mapping.items())
        return text, mapping

    def _batches(self, peptides: Sequence[str]) -> Iterable[Sequence[str]]:
        for start in range(0, len(peptides), MAX_SEQUENCES_PER_REQUEST):
            yield peptides[start:start + MAX_SEQUENCES_PER_REQUEST]

    # ------------------------------------------------------------------
    # Class-I / class-II binding
    # ------------------------------------------------------------------
    def predict_mhci(self, peptides: Sequence[str], alleles: Sequence[str],
                     *, lengths: Sequence[int] = MHC_I_LENGTHS,
                     method: str = "netmhcpan_el") -> list[dict[str, object]]:
        """Predict MHC-I binding for exact-length peptides.

        IEDB pairs alleles with lengths one-to-one, so the allele is repeated
        once per requested length in a single request per allele.
        """
        spec = METHODS.get(method)
        if spec is None or spec.tool != "mhci":
            raise ValueError(f"not an MHC-I method: {method!r}")
        peptide_list = unique(normalize_peptide(item) for item in peptides)
        if not peptide_list:
            return []
        allowed = self._lengths_present(peptide_list, lengths)
        if not allowed:
            return []
        allele_list = [item.name for item in parse_panel(alleles)]
        records: list[dict[str, object]] = []
        for allele in allele_list:
            for batch in self._batches(peptide_list):
                text, mapping = self._fasta(batch)
                payload = {
                    "method": spec.api_method,
                    "sequence_text": text,
                    "allele": ",".join([allele] * len(allowed)),
                    "length": ",".join(str(item) for item in allowed),
                }
                response, request_id = self._post(TOOLS_URL + "mhci/", payload)
                records.extend(self._binding_records(response, request_id, spec, allele,
                                                    set(batch), allowed))
        return records

    def predict_mhcii(self, peptides: Sequence[str], alleles: Sequence[str],
                      *, length: int | str = 15,
                      method: str = "netmhciipan_el") -> list[dict[str, object]]:
        """Predict MHC-II binding for 11-30 aa peptides (or ``asis``)."""
        spec = METHODS.get(method)
        if spec is None or spec.tool != "mhcii":
            raise ValueError(f"not an MHC-II method: {method!r}")
        peptide_list = unique(normalize_peptide(item) for item in peptides)
        if not peptide_list:
            return []
        if length != "asis":
            length = int(length)
            if not 11 <= length <= 30:
                raise ValueError("MHC-II peptide length must be 11-30 or 'asis'")
        allele_list = [item.name for item in parse_panel(alleles)]
        records: list[dict[str, object]] = []
        for allele in allele_list:
            for batch in self._batches(peptide_list):
                text, _ = self._fasta(batch)
                payload = {
                    "method": spec.api_method,
                    "sequence_text": text,
                    "allele": allele,
                    "length": str(length),
                }
                response, request_id = self._post(TOOLS_URL + "mhcii/", payload)
                records.extend(self._binding_records(response, request_id, spec, allele,
                                                    set(batch), None))
        return records

    def _binding_records(self, text: str, request_id: str, spec: Method, allele: str,
                         peptides: set[str], lengths: Sequence[int] | None) -> list[dict[str, object]]:
        records: list[dict[str, object]] = []
        for row in self._parse_table(text):
            peptide = (row.get("peptide") or "").upper()
            if peptide not in peptides:
                continue
            if lengths is not None and _float(row.get("length")) not in set(lengths):
                continue
            percentile = _float(row.get("percentile_rank", row.get("rank")))
            records.append({
                "peptide": peptide,
                "allele": allele,
                "mhc_class": spec.mhc_class,
                "method": spec.key,
                "method_label": spec.label,
                "score": _float(row.get(spec.score_field)),
                "percentile_rank": percentile,
                "core": row.get("core_peptide", row.get("core", "")),
                "request_id": request_id,
                "source": "IEDB",
                "raw": row,
            })
        return records

    # ------------------------------------------------------------------
    # Processing / MHC-NP / stability
    # ------------------------------------------------------------------
    def predict_processing(self, peptides: Sequence[str], alleles: Sequence[str],
                           *, lengths: Sequence[int] = MHC_I_LENGTHS,
                           proteasome: str = "immuno") -> list[dict[str, object]]:
        """Predict proteasomal cleavage + TAP transport + MHC-I processing.

        The IEDB processing service returns HTTP 500 when a FASTA batch is
        combined with several lengths, so one request is sent per
        (allele, length) pair.  This is slower but reliable.
        """
        if proteasome not in ("immuno", "constitutive"):
            raise ValueError("proteasome must be 'immuno' or 'constitutive'")
        spec = METHODS["processing"]
        peptide_list = unique(normalize_peptide(item) for item in peptides)
        if not peptide_list:
            return []
        allowed = self._lengths_present(peptide_list, lengths)
        if not allowed:
            return []
        allele_list = [item.name for item in parse_panel(alleles)]
        records: list[dict[str, object]] = []
        for allele in allele_list:
            for length in allowed:
                for batch in self._batches(peptide_list):
                    text, _ = self._fasta(batch)
                    payload = {
                        "method": spec.api_method,
                        "sequence_text": text,
                        "allele": allele,
                        "length": str(length),
                        "proteasome": proteasome,
                    }
                    response, request_id = self._post(TOOLS_URL + "processing/", payload)
                    for row in self._parse_table(response):
                        peptide = (row.get("peptide") or "").upper()
                        if peptide not in set(batch):
                            continue
                        if _float(row.get("length")) != length:
                            continue
                        records.append({
                            "peptide": peptide,
                            "allele": allele,
                            "mhc_class": 1,
                            "method": "processing",
                            "method_label": spec.label,
                            "proteasome_score": _float(row.get("proteasome_score")),
                            "tap_score": _float(row.get("tap_score")),
                            "total_score": _float(row.get("total_score")),
                            "processing_score": _float(row.get("processing_score")),
                            "ic50_score": _float(row.get("ic50_score")),
                            "request_id": request_id,
                            "source": "IEDB",
                            "raw": row,
                        })
        return records

    def predict_mhcnp(self, peptides: Sequence[str], alleles: Sequence[str],
                      *, lengths: Sequence[int] = MHC_I_LENGTHS) -> list[dict[str, object]]:
        """MHC-NP: probability that a peptide is naturally processed and presented."""
        spec = METHODS["mhcnp"]
        peptide_list = unique(normalize_peptide(item) for item in peptides)
        if not peptide_list:
            return []
        allowed = self._lengths_present(peptide_list, lengths)
        if not allowed:
            return []
        allele_list = [item.name for item in parse_panel(alleles)]
        records: list[dict[str, object]] = []
        for allele in allele_list:
            for batch in self._batches(peptide_list):
                text, _ = self._fasta(batch)
                payload = {
                    "method": spec.api_method,
                    "sequence_text": text,
                    "allele": ",".join([allele] * len(allowed)),
                    "length": ",".join(str(item) for item in allowed),
                }
                response, request_id = self._post(TOOLS_URL + "mhcnp/", payload)
                for row in self._parse_table(response):
                    peptide = (row.get("peptide") or "").upper()
                    if peptide not in set(batch):
                        continue
                    records.append({
                        "peptide": peptide,
                        "allele": allele,
                        "mhc_class": 1,
                        "method": "mhcnp",
                        "method_label": spec.label,
                        "mhcnp_probability": _float(row.get("prob_score")),
                        "request_id": request_id,
                        "source": "IEDB",
                        "raw": row,
                    })
        return records

    def predict_stability(self, peptides: Sequence[str], alleles: Sequence[str]) -> list[dict[str, object]]:
        """Predict peptide-MHC stability with NetMHCstabpan-1.0."""
        return self.predict_mhci(peptides, alleles, method="netmhcstabpan")

    # ------------------------------------------------------------------
    # Known-epitope lookup
    # ------------------------------------------------------------------
    def lookup_epitopes(self, peptides: Sequence[str], *, limit: int = 3) -> dict[str, list[dict[str, object]]]:
        """Look up assay records for each peptide in the IEDB (query API).

        A hit means the exact peptide sequence has been assayed before; it
        does **not** mean this candidate is a validated neoantigen.
        """
        result: dict[str, list[dict[str, object]]] = {}
        for peptide in unique(normalize_peptide(item) for item in peptides):
            url = (f"{QUERY_URL}tcell_search?linear_sequence=eq.{peptide}"
                   f"&limit={int(limit)}")
            try:
                payload = self._get(url)
            except IedbError:
                result[peptide] = []
                continue
            rows = payload if isinstance(payload, list) else []
            result[peptide] = [
                {
                    "peptide": peptide,
                    "mhc_class": row.get("mhc_class"),
                    "mhc_restriction": row.get("mhc_restriction"),
                    "qualitative_measure": row.get("qualitative_measure"),
                    "assay": (row.get("assay_description") or "").replace("<br/>", " ")[:200],
                    "source_organism": row.get("source_organism_name"),
                    "antigen": row.get("parent_source_antigen_name") or row.get("structure_description"),
                    "pubmed_id": row.get("pubmed_id"),
                }
                for row in rows[:limit]
            ]
        return result

    # ------------------------------------------------------------------
    # Allele catalogue
    # ------------------------------------------------------------------
    def allele_catalogue(self, method: str = "netmhcpan_el") -> list[str]:
        """Return the alleles the IEDB lists for a method (network required)."""
        spec = METHODS.get(method)
        if spec is None:
            raise ValueError(f"unknown method {method!r}")
        text, _ = self._post(TOOLS_URL + f"{spec.tool}/", {"method": spec.api_method, "species": "human"})
        return [line.strip() for line in text.splitlines() if line.strip().startswith("HLA-")]


def method_table() -> list[dict[str, object]]:
    """Describe every model this client can call (for API/docs/UI)."""
    return [spec.as_dict() for spec in METHODS.values()]


def describe(allele: str) -> HlaAllele:
    """Describe one allele (thin wrapper around :func:`hla.parse_panel`)."""
    return parse_panel([allele])[0]
