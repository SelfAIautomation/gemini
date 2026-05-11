"""Domain-level rate limiter backed by Supabase domain_rules table."""
import time
from datetime import datetime, timedelta, timezone
from urllib.parse import urlparse
from supabase import Client


class DomainRateLimiter:
    def __init__(self, supabase: Client):
        self._db = supabase
        self._cache: dict[str, dict] = {}

    def _get_domain(self, url: str) -> str:
        return urlparse(url).netloc.lstrip("www.")

    def _load_rule(self, domain: str) -> dict:
        res = self._db.table("domain_rules").select("*").eq("domain", domain).maybe_single().execute()
        if res.data:
            self._cache[domain] = res.data
            return res.data
        default = {
            "domain": domain,
            "crawl_interval_seconds": 5,
            "max_requests_per_hour": 60,
            "robots_allowed": True,
            "consecutive_errors": 0,
            "enabled": True,
        }
        self._db.table("domain_rules").insert(default).execute()
        self._cache[domain] = default
        return default

    def can_fetch(self, url: str) -> bool:
        domain = self._get_domain(url)
        rule = self._cache.get(domain) or self._load_rule(domain)

        if not rule.get("enabled"):
            return False
        if not rule.get("robots_allowed"):
            return False

        # crawl_interval_seconds チェック
        last = rule.get("last_fetched_at")
        if last:
            elapsed = (datetime.now(timezone.utc) - datetime.fromisoformat(last)).total_seconds()
            if elapsed < rule["crawl_interval_seconds"]:
                return False

        # max_requests_per_hour チェック: 実際の fetch_logs を確認
        max_per_hour = rule.get("max_requests_per_hour", 60)
        one_hour_ago = (datetime.now(timezone.utc) - timedelta(hours=1)).isoformat()
        try:
            res = (
                self._db.table("fetch_logs")
                .select("id", count="exact")
                .eq("domain", domain)
                .gte("fetched_at", one_hour_ago)
                .execute()
            )
            recent_count = res.count or 0
            if recent_count >= max_per_hour:
                return False
        except Exception:
            pass  # fetch_logs 読み取り失敗時はブロックしない

        return True

    def wait_if_needed(self, url: str) -> None:
        domain = self._get_domain(url)
        rule = self._cache.get(domain) or self._load_rule(domain)
        last = rule.get("last_fetched_at")
        if last:
            elapsed = (datetime.now(timezone.utc) - datetime.fromisoformat(last)).total_seconds()
            wait = rule["crawl_interval_seconds"] - elapsed
            if wait > 0:
                time.sleep(wait)

    def record_result(self, url: str, status_code: int, error: str | None = None) -> None:
        domain = self._get_domain(url)
        rule = self._cache.get(domain) or self._load_rule(domain)
        errors = rule.get("consecutive_errors", 0)
        patch: dict = {
            "last_fetched_at": datetime.now(timezone.utc).isoformat(),
            "last_status_code": status_code,
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }
        if status_code in (200, 304):
            patch["consecutive_errors"] = 0
        elif status_code in (403, 429, 503):
            patch["consecutive_errors"] = errors + 1
            if errors + 1 >= 3:
                patch["enabled"] = False
                patch["disabled_reason"] = f"Disabled after {errors+1} consecutive {status_code} errors"
        self._db.table("domain_rules").update(patch).eq("domain", domain).execute()
        if domain in self._cache:
            self._cache[domain].update(patch)

    def handle_retry_after(self, url: str, retry_after: int) -> None:
        domain = self._get_domain(url)
        self._db.table("domain_rules").update({
            "crawl_interval_seconds": max(retry_after, 60),
            "enabled": True,
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }).eq("domain", domain).execute()
        self._cache.pop(domain, None)
        time.sleep(retry_after)

    def load_fetch_state(self, source_id: str, feed_url: str) -> tuple[str | None, str | None]:
        """ETag と Last-Modified を DB から読み込む。"""
        try:
            res = (
                self._db.table("source_fetch_state")
                .select("etag, last_modified")
                .eq("source_id", source_id)
                .eq("url", feed_url)
                .maybe_single()
                .execute()
            )
            if res.data:
                return res.data.get("etag"), res.data.get("last_modified")
        except Exception:
            pass
        return None, None

    def save_success_fetch_state(self, source_id: str, feed_url: str,
                                  etag: str | None, last_modified: str | None,
                                  content_hash: str | None) -> None:
        """200 時: ETag・Last-Modified・content_hash を全て upsert する。"""
        try:
            self._db.table("source_fetch_state").upsert({
                "source_id": source_id,
                "url": feed_url,
                "etag": etag,
                "last_modified": last_modified,
                "content_hash": content_hash,
                "last_checked_at": datetime.now(timezone.utc).isoformat(),
            }, on_conflict="source_id,url").execute()
        except Exception:
            pass

    def touch_fetch_state(self, source_id: str, feed_url: str) -> None:
        """304 時: last_checked_at のみ更新する。etag / last_modified / content_hash は保持。"""
        try:
            # UPDATE のみ（行がなければ何もしない）
            self._db.table("source_fetch_state").update({
                "last_checked_at": datetime.now(timezone.utc).isoformat(),
            }).eq("source_id", source_id).eq("url", feed_url).execute()
        except Exception:
            pass
