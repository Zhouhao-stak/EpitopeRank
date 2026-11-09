"""受控的外网访问工具：给智能体与 MCP 工具台共用的最小 HTTP 客户端。

设计取舍：默认只允许项目实际会用到的生物信息学域名（可用环境变量扩展），
限制响应体积与超时，并且不跟随指向非白名单域名的重定向。这样「能上网」
不等于「能任意访问」，同时保留完全禁用的开关，便于离线/可复现运行。
"""
from __future__ import annotations

import os
import urllib.parse
import urllib.request
from typing import Any

DEFAULT_DOMAINS: tuple[str, ...] = (
    "rest.ensembl.org",
    "eutils.ncbi.nlm.nih.gov",
    "www.ncbi.nlm.nih.gov",
    "tools.iedb.org",
    "tools-cluster-interface.iedb.org",
    "pubmed.ncbi.nlm.nih.gov",
    "www.ebi.ac.uk",
    "mygene.info",
    "maayanlab.cloud",
    "rest.kegg.jp",
    "string-db.org",
    "geneontology.org",
    "raw.githubusercontent.com",
    "api.github.com",
)

MAX_BYTES = 200_000
TIMEOUT = 20.0


def allowed_domains() -> set[str]:
    """返回当前允许的域名集合（环境变量可追加）。"""
    domains = set(DEFAULT_DOMAINS)
    extra = os.getenv("EPITOPERANK_ALLOWED_DOMAINS", "")
    domains.update(part.strip().lower() for part in extra.split(",") if part.strip())
    return domains


def allow_all() -> bool:
    """是否显式放开域名白名单（默认关闭）。"""
    return os.getenv("EPITOPERANK_WEB_FETCH_ALLOW_ALL", "").strip().lower() in {
        "1", "true", "yes", "on"}


# 中文备注：epitoperank：辅助处理主机（参数：url）
def _host_for(url: str) -> str:
    return (urllib.parse.urlsplit(url).hostname or "").lower()


# 中文备注：epitoperank：判断allowed（参数：host）
def _is_allowed(host: str) -> bool:
    if allow_all():
        return True
    return any(host == d or host.endswith("." + d) for d in allowed_domains())


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    """重定向目标必须同样在白名单内，否则直接拒绝。"""

    # 中文备注：epitoperank：辅助处理redirect请求（参数：req、fp、code、msg）
    def redirect_request(self, req, fp, code, msg, headers, newurl):  # noqa: D102
        if not _is_allowed(_host_for(newurl)):
            raise urllib.error.HTTPError(newurl, code, "redirect target not allowed", headers, fp)
        return super().redirect_request(req, fp, code, msg, headers, newurl)


def fetch_url(url: str, *, max_bytes: int = MAX_BYTES,
              timeout: float = TIMEOUT) -> dict[str, Any]:
    """抓取一个 URL 的文本内容，返回结构化结果（不抛异常给调用方）。

    :param url: 仅支持 http / https。
    :param max_bytes: 响应体读取上限，超出部分截断并标记 ``truncated``。
    :param timeout: 单次请求超时（秒）。
    """
    url = str(url or "").strip()
    parsed = urllib.parse.urlsplit(url)
    if parsed.scheme not in {"http", "https"} or not parsed.hostname:
        return {"ok": False, "url": url, "error": "only http/https URLs are supported"}
    host = _host_for(url)
    if not _is_allowed(host):
        return {"ok": False, "url": url, "error": f"domain not allowed: {host}",
                "allowed_domains": sorted(allowed_domains())}
    opener = urllib.request.build_opener(
        urllib.request.ProxyHandler({}), _NoRedirect())
    opener.addheaders = [("User-Agent", "EpitopeRank-Agent/1.0"),
                         ("Accept", "text/plain, application/json, text/xml, */*")]
    try:
        with opener.open(url, timeout=timeout) as resp:
            raw = resp.read(max_bytes + 1)
            content_type = resp.headers.get("Content-Type", "")
            status = resp.status
        truncated = len(raw) > max_bytes
        text = raw[:max_bytes].decode("utf-8", "replace")
        return {"ok": True, "url": url, "status": status,
                "content_type": content_type, "truncated": truncated,
                "bytes": min(len(raw), max_bytes), "text": text}
    except Exception as exc:  # noqa: BLE001 - 工具层统一返回结构化错误
        return {"ok": False, "url": url, "error": f"{type(exc).__name__}: {exc}"}
