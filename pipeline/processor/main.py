"""AI processing worker: topic clustering, summarization, translation.

HTTP routing:
  POST /         → process unprocessed raw_articles
  POST /summary  → generate periodic market summary (?period=6h|24h|weekly)

Triggered by Cloud Scheduler (HTTP) or Pub/Sub push.
"""
import base64
import json
import logging
import os
from datetime import datetime, timezone

from dotenv import load_dotenv
from supabase import create_client, Client

from gemini_client import GeminiClient

load_dotenv()
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

BATCH_SIZE = int(os.environ.get("BATCH_SIZE", "20"))
VALID_PERIODS = {"6h", "24h", "weekly"}


def get_supabase() -> Client:
    return create_client(os.environ["SUPABASE_URL"], os.environ["SUPABASE_SERVICE_KEY"])


def process(request=None):
    """
    Cloud Functions / Cloud Run HTTP entry point.
    /summary?period=... → 定期まとめ生成
    それ以外           → 未処理記事のバッチ処理
    """
    # /summary ルーティング
    if request is not None:
        path = (getattr(request, "path", None) or "").rstrip("/")
        if path == "/summary":
            period = "6h"
            if hasattr(request, "args"):
                period = request.args.get("period", "6h")
            if period not in VALID_PERIODS:
                logger.warning(f"Unknown period '{period}', defaulting to 6h")
                period = "6h"
            return _run_periodic_summary(period)

    return _process_articles()


def _run_periodic_summary(period: str) -> dict:
    from summary_generator import generate_periodic_summary
    result = generate_periodic_summary(period)
    return result or {"status": "no_topics", "period": period}


def _process_articles() -> dict:
    db = get_supabase()
    ai = GeminiClient(db)

    # stale claim を先に解放（前回の Cloud Run が途中終了した場合の救済）
    try:
        released = db.rpc("release_stale_claims", {}).execute()
        if released.data and released.data > 0:
            logger.info(f"Released {released.data} stale claims")
    except Exception as e:
        logger.warning(f"release_stale_claims failed (non-fatal): {e}")

    # FOR UPDATE SKIP LOCKED でアトミックにバッチをクレーム
    try:
        articles = db.rpc("claim_raw_articles", {"batch_size": BATCH_SIZE}).execute().data
    except Exception as e:
        logger.error(f"claim_raw_articles RPC failed: {e}")
        return {"processed": 0}

    if not articles:
        logger.info("No unprocessed articles")
        return {"processed": 0}

    logger.info(f"Claimed {len(articles)} articles for processing")

    article_summaries = [
        {"index": i, "title": a["title_raw"], "body": (a["body_raw"] or "")[:300],
         "source": a["source_name"]}
        for i, a in enumerate(articles)
    ]

    cluster_result = ai.extract_topics(article_summaries)
    if not cluster_result:
        # クレームを解放して次回に再試行させる
        _release_claims(db, [a["id"] for a in articles])
        logger.error("Topic extraction failed; releasing claims")
        return {"processed": 0}

    published = 0
    processed_ids: list[str] = []

    for cluster in cluster_result.clusters:
        if not cluster.article_indices:
            continue
        # 非負・範囲内チェック（pydantic バリデーション後の二重チェック）
        cluster_articles = [
            articles[i]
            for i in cluster.article_indices
            if 0 <= i < len(articles)
        ]
        if not cluster_articles:
            continue

        summary = ai.generate_summary(
            category=cluster.category,
            title_en=cluster.representative_title_en,
            sources=cluster_articles,
        )
        if not summary:
            continue

        topic_id = _publish_topic(db, cluster, summary)
        if topic_id:
            _link_sources(db, topic_id, cluster_articles)
            published += 1

        processed_ids.extend(a["id"] for a in cluster_articles)

    _mark_processed(db, processed_ids)

    # クレームしたが処理対象にならなかった記事も完了済みにする
    all_ids = [a["id"] for a in articles]
    unhandled = list(set(all_ids) - set(processed_ids))
    if unhandled:
        _release_claims(db, unhandled)

    logger.info(f"Published {published} topics from {len(articles)} articles")
    return {"processed": published}


def _publish_topic(db: Client, cluster, summary) -> str | None:
    now = datetime.now(timezone.utc).isoformat()
    topic = {
        "title_ja": summary.title_ja,
        "title_en": summary.title_en,
        "body_ja": summary.body_ja,
        "body_en": summary.body_en,
        "summary_ja": summary.summary_ja,
        "summary_en": summary.summary_en,
        "category": cluster.category,
        "status": "published",
        "is_breaking": cluster.is_breaking,
        "importance_score": cluster.importance_score,
        "published_at": now,
        "updated_at": now,
    }
    try:
        res = db.table("topics").insert(topic).execute()
        topic_id = res.data[0]["id"]
        db.table("topic_events").insert({
            "topic_id": topic_id,
            "event_type": "breaking" if cluster.is_breaking else "created",
            "new_value": {"title_ja": topic["title_ja"]},
        }).execute()
        return topic_id
    except Exception as e:
        logger.error(f"Topic insert failed: {e}")
        return None


def _link_sources(db: Client, topic_id: str, articles: list[dict]) -> None:
    rows = [
        {
            "topic_id": topic_id,
            "source_name": a["source_name"],
            "source_url": a["source_url"],
            "source_type": a["source_type"],
            "posted_at": a.get("published_at"),
        }
        for a in articles
    ]
    try:
        db.table("topic_sources").insert(rows).execute()
    except Exception as e:
        logger.error(f"topic_sources insert failed: {e}")


def _mark_processed(db: Client, article_ids: list[str]) -> None:
    if not article_ids:
        return
    now = datetime.now(timezone.utc).isoformat()
    db.table("raw_articles").update({
        "processed": True,
        "processing": False,
        "processed_at": now,
    }).in_("id", article_ids).execute()


def _release_claims(db: Client, article_ids: list[str]) -> None:
    """処理失敗時にクレームを解放し、次回バッチで再試行できるようにする。"""
    if not article_ids:
        return
    db.table("raw_articles").update({
        "processing": False,
        "processing_started_at": None,
    }).in_("id", article_ids).execute()


def process_pubsub(event, context):
    """Cloud Functions Pub/Sub trigger."""
    if "data" in event:
        article = json.loads(base64.b64decode(event["data"]).decode("utf-8"))
        logger.info(f"Pub/Sub triggered for: {article.get('source_url')}")
    return _process_articles()


if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == "summary":
        period = sys.argv[2] if len(sys.argv) > 2 else "6h"
        _run_periodic_summary(period)
    else:
        _process_articles()
