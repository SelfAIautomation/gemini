"""RSS/Atom/HTML fetcher with ETag caching and bot-friendly headers."""
import hashlib
import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional

import feedparser
import httpx

logger = logging.getLogger(__name__)

BOT_USER_AGENT = (
    "CBTerminalBot/1.0 (+https://cb-terminal.dev/bot-info; contact: bot@cb-terminal.dev)"
)

DEFAULT_HEADERS = {
    "User-Agent": BOT_USER_AGENT,
    "Accept": "application/rss+xml, application/atom+xml, text/xml, text/html;q=0.8",
    "Accept-Language": "ja,en;q=0.9",
    "Accept-Encoding": "gzip, deflate",
    "Cache-Control": "no-cache",
}


@dataclass
class FetchResult:
    url: str
    status_code: int
    content: Optional[str] = None
    content_hash: Optional[str] = None
    etag: Optional[str] = None
    last_modified: Optional[str] = None
    retry_after: Optional[int] = None
    error: Optional[str] = None
    duration_ms: int = 0
    entries: list[dict] = field(default_factory=list)


class RSSFetcher:
    def __init__(self, timeout: int = 30):
        self._timeout = timeout
        self._etag_cache: dict[str, str] = {}
        self._lm_cache: dict[str, str] = {}

    def fetch(self, url: str) -> FetchResult:
        headers = dict(DEFAULT_HEADERS)
        if url in self._etag_cache:
            headers["If-None-Match"] = self._etag_cache[url]
        if url in self._lm_cache:
            headers["If-Modified-Since"] = self._lm_cache[url]

        start = datetime.now(timezone.utc)
        try:
            with httpx.Client(timeout=self._timeout, follow_redirects=True) as client:
                resp = client.get(url, headers=headers)
        except httpx.TimeoutException as e:
            return FetchResult(url=url, status_code=0, error=f"timeout: {e}")
        except httpx.RequestError as e:
            return FetchResult(url=url, status_code=0, error=f"request_error: {e}")

        duration = int((datetime.now(timezone.utc) - start).total_seconds() * 1000)

        if resp.status_code == 304:
            return FetchResult(url=url, status_code=304, duration_ms=duration)

        if resp.status_code == 429:
            retry = int(resp.headers.get("Retry-After", 60))
            return FetchResult(url=url, status_code=429, retry_after=retry, duration_ms=duration)

        if resp.status_code in (401, 403):
            return FetchResult(url=url, status_code=resp.status_code,
                               error=f"access_denied_{resp.status_code}", duration_ms=duration)

        if resp.status_code != 200:
            return FetchResult(url=url, status_code=resp.status_code,
                               error=f"http_{resp.status_code}", duration_ms=duration)

        content = resp.text
        content_hash = hashlib.sha256(content.encode()).hexdigest()

        etag = resp.headers.get("ETag")
        lm = resp.headers.get("Last-Modified")
        if etag:
            self._etag_cache[url] = etag
        if lm:
            self._lm_cache[url] = lm

        entries = self._parse_feed(url, content)
        return FetchResult(
            url=url,
            status_code=200,
            content=content,
            content_hash=content_hash,
            etag=etag,
            last_modified=lm,
            duration_ms=duration,
            entries=entries,
        )

    def _parse_feed(self, url: str, content: str) -> list[dict]:
        parsed = feedparser.parse(content)
        entries = []
        for e in parsed.entries:
            entry = {
                "title": e.get("title", ""),
                "link": e.get("link", ""),
                "summary": e.get("summary", ""),
                "published": self._parse_date(e),
                "content": self._extract_content(e),
            }
            if entry["link"] and entry["title"]:
                entries.append(entry)
        return entries

    def _parse_date(self, entry) -> Optional[str]:
        if hasattr(entry, "published_parsed") and entry.published_parsed:
            return datetime(*entry.published_parsed[:6], tzinfo=timezone.utc).isoformat()
        if hasattr(entry, "updated_parsed") and entry.updated_parsed:
            return datetime(*entry.updated_parsed[:6], tzinfo=timezone.utc).isoformat()
        return None

    def _extract_content(self, entry) -> str:
        if hasattr(entry, "content") and entry.content:
            return entry.content[0].get("value", "")
        return entry.get("summary", "")
