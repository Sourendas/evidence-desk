"""Free, keyless retrieval: pasted snippets, pasted URLs (HTTP), and Wikipedia search."""
from __future__ import annotations

import html
import ipaddress
import json
import re
import socket
import urllib.parse
import urllib.request
from dataclasses import dataclass, field

UA = "EvidenceDesk/0.1 (+https://github.com/Sourendas/evidence-desk; hackathon research agent)"
MAX_BYTES = 600_000
# 198.18.0.0/15 is the benchmarking range, commonly used as fake-IP DNS by egress proxies.
FAKE_IP_NET = ipaddress.ip_network("198.18.0.0/15")


@dataclass
class Source:
    id: str
    kind: str  # snippet | url | wikipedia
    title: str
    url: str
    text: str
    status: str = "ok"
    meta: dict = field(default_factory=dict)


class FetchError(RuntimeError):
    pass


def is_safe_url(url: str) -> bool:
    """Reject non-http(s) and private/loopback/link-local hosts (basic SSRF guard)."""
    try:
        p = urllib.parse.urlparse(url)
    except ValueError:
        return False
    if p.scheme not in ("http", "https") or not p.hostname:
        return False
    try:
        infos = socket.getaddrinfo(p.hostname, None)
    except socket.gaierror:
        return False
    for info in infos:
        ip = ipaddress.ip_address(info[4][0].split("%")[0])
        if ip in FAKE_IP_NET:  # fake-IP DNS used by some egress proxies/sandboxes; traffic still goes out
            continue
        if ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_reserved or ip.is_multicast:
            return False
    return True


def html_to_text(raw: str) -> tuple[str, str]:
    """Return (title, plain text) from an HTML document using stdlib only."""
    m = re.search(r"<title[^>]*>(.*?)</title>", raw, flags=re.S | re.I)
    title = html.unescape(re.sub(r"\s+", " ", m.group(1))).strip() if m else ""
    raw = re.sub(r"<(script|style|noscript|svg|nav|footer|header)[^>]*>.*?</\1>", " ", raw, flags=re.S | re.I)
    raw = re.sub(r"<!--.*?-->", " ", raw, flags=re.S)
    raw = re.sub(r"<(br|p|div|li|h[1-6]|tr|section|article)[^>]*>", "\n", raw, flags=re.I)
    text = re.sub(r"<[^>]+>", " ", raw)
    text = html.unescape(text)
    text = re.sub(r"[ \t\r\f\v]+", " ", text)
    text = re.sub(r"\n\s*\n+", "\n", text)
    # drop trailing reference/citation sections (common on wikis and docs)
    m2 = re.search(r"\n\s*(References|External links|Further reading|Notes|Citations)\s*(\[edit\])?\s*\n", text)
    if m2 and m2.start() > len(text) * 0.3:
        text = text[: m2.start()]
    return title, text.strip()


def http_get(url: str, timeout: float = 12.0) -> tuple[str, str]:
    if not is_safe_url(url):
        raise FetchError("blocked: not a public http(s) URL")
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "text/html,text/plain,application/json"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            ctype = r.headers.get("Content-Type", "")
            data = r.read(MAX_BYTES)
    except Exception as e:
        raise FetchError(f"fetch failed: {type(e).__name__}") from None
    return ctype, data.decode("utf-8", errors="replace")


def fetch_url(url: str, sid: str, getter=http_get) -> Source:
    try:
        ctype, body = getter(url)
    except FetchError as e:
        return Source(sid, "url", url, url, "", status=str(e))
    if "html" in ctype or body.lstrip().startswith("<"):
        title, text = html_to_text(body)
    else:
        title, text = url, body
    return Source(sid, "url", title or url, url, text[:60_000])


def wikipedia_search(query: str, limit: int = 2, getter=http_get) -> list[Source]:
    """Keyless Wikipedia search + plain-text intro extracts."""
    api = "https://en.wikipedia.org/w/api.php?"
    q = urllib.parse.urlencode(
        {"action": "query", "list": "search", "srsearch": query, "srlimit": limit, "format": "json"}
    )
    try:
        _, body = getter(api + q)
        hits = json.loads(body)["query"]["search"]
    except Exception:
        return []
    out: list[Source] = []
    for i, h in enumerate(hits[:limit]):
        title = h["title"]
        q2 = urllib.parse.urlencode(
            {"action": "query", "prop": "extracts", "explaintext": 1, "exintro": 1,
             "titles": title, "format": "json", "redirects": 1}
        )
        try:
            _, b2 = getter(api + q2)
            pages = json.loads(b2)["query"]["pages"]
            text = next(iter(pages.values())).get("extract", "")
        except Exception:
            text = ""
        url = "https://en.wikipedia.org/wiki/" + urllib.parse.quote(title.replace(" ", "_"))
        out.append(Source(f"W{i+1}", "wikipedia", f"Wikipedia: {title}", url, text,
                          status="ok" if text else "empty"))
    return out
