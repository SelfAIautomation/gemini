"""Cloud Run / Cloud Functions entry point for news collection."""
import base64
import hashlib
import json
import logging
import os
from datetime import datetime, timezone

from dotenv import load_dotenv
from google.cloud import pubsub_v1
from supabase import create_client, Client

from fetcher import RSSFetcher, FetchResult
from rate_limiter import DomainRateLimiter

load_dotenv()
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

SUPABASE_URL = os.environ["SUPABASE_URL"]
SUPABASE_SERVICE_KEY = os.environ["SUPABASE_SERVICE_KEY"]
GCP_PROJECT_ID = os.environ.get("GCP_PROJECT_ID", "")
PUBSUB_TOPIC_PROCESS = os.environ.get("PUBSUB_TOPIC_PROCESS", "news-process")


def get_supabase() -> Client:
    return create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)


def collect(request=None):
    """HTTP endpoint for Cloud Run / Cloud Functions."""
    db = get_supabase()
    fetcher = RSSFetcher()
    limiter = DomainRateLimiter(db)

    sources = db.table("source_registry").select("*").eq("enabled", True).execute().data
    logger.info(f"Collecting from {len(sources)} sources")

    publisher = pubsub_v1.PublisherClient() if GCP_PROJECT_ID else None
    topic_path = publisher.topic_path(GCP_PROJECT_ID, PUBSUB_TOPIC_PROCESS) if publisher else None

    collected = 0
    for source in sources:
        feed_url = source.get("feed_url") or source["base_url"]
        if not limiter.can_fetch(feed_url):
            logger.debug(f"Rate limited: {source['source_name']}")
            continue

        limiter.wait_if_needed(feed_url)
        result = fetcher.fetch(feed_url)
        limiter.record_result(feed_url, result.status_code, result.error)

        _log_fetch(db, source, result)

        if result.status_code == 304:
            logger.info(f"No change: {source['source_name']}")
            continue

        if result.status_code == 429:
            limiter.handle_retry_after(feed_url, result.retry_after or 60)
            continue

        if result.status_code != 200:
            logger.warning(f"Failed {result.status_code}: {source['source_name']} ({result.error})")
            continue

        new_articles = _save_raw_articles(db, source, result)
        collected += len(new_articles)

        if new_articles and publisher:
            for art in new_articles:
                _publish_to_processor(publisher, topic_path, art)

    logger.info(f"Collected {collected} new articles")
    return {"collected": collected}


def _log_fetch(db: Client, source: dict, result: FetchResult) -> None:
    from urllib.parse import urlparse
    url = source.get("feed_url") or source["base_url"]
    db.table("fetch_logs").insert({
        "source_id": source["id"],
        "url": url,
        "domain": urlparse(url).netloc.lstrip("www."),
        "status_code": result.status_code,
        "response_bytes": len(result.content.encode()) if result.content else 0,
        "content_hash": result.content_hash,
        "error_type": result.error,
        "retry_after": result.retry_after,
        "duration_ms": result.duration_ms,
        "user_agent": "CBTerminalBot/1.0",
    }).execute()


def _save_raw_articles(db: Client, source: dict, result: FetchResult) -> list[dict]:
    new_articles = []
    for entry in result.entries:
        content_hash = hashlib.sha256(
            (entry["title"] + entry["link"]).encode()
        ).hexdigest()

        existing = db.table("raw_articles").select("id").eq(
            "source_url", entry["link"]
        ).maybe_single().execute()
        if existing.data:
            continue

        article = {
            "source_id": source["id"],
            "source_url": entry["link"],
            "source_name": source["source_name"],
            "source_type": source["source_type"],
            "title_raw": entry["title"],
            "body_raw": entry.get("content") or entry.get("summary", ""),
            "published_at": entry.get("published"),
            "content_hash": content_hash,
            "processed": False,
        }
        try:
            db.table("raw_articles").insert(article).execute()
            new_articles.append(article)
        except Exception as e:
            logger.error(f"DB insert error: {e}")

    return new_articles


def _publish_to_processor(publisher, topic_path: str, article: dict) -> None:
    payload = json.dumps(article).encode("utf-8")
    future = publisher.publish(topic_path, payload)
    logger.debug(f"Published message: {future.result()}")


if __name__ == "__main__":
    collect()
