"""AI processing worker: topic clustering, summarization, translation.

Triggered by Cloud Pub/Sub or HTTP (Cloud Run).
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


def get_supabase() -> Client:
    return create_client(os.environ["SUPABASE_URL"], os.environ["SUPABASE_SERVICE_KEY"])


def process(request=None):
    """Process unhandled raw_articles in batches."""
    db = get_supabase()
    ai = GeminiClient(db)

    articles = (
        db.table("raw_articles")
        .select("*")
        .eq("processed", False)
        .order("published_at", desc=True)
        .limit(BATCH_SIZE)
        .execute()
        .data
    )
    if not articles:
        logger.info("No unprocessed articles")
        return {"processed": 0}

    logger.info(f"Processing {len(articles)} articles")

    article_summaries = [
        {"index": i, "title": a["title_raw"], "body": (a["body_raw"] or "")[:300],
         "source": a["source_name"]}
        for i, a in enumerate(articles)
    ]

    cluster_result = ai.extract_topics(article_summaries)
    if not cluster_result or "clusters" not in cluster_result:
        logger.error("Topic extraction failed")
        return {"processed": 0}

    published = 0
    for cluster in cluster_result["clusters"]:
        indices = cluster.get("article_indices", [])
        if not indices:
            continue
        cluster_articles = [articles[i] for i in indices if i < len(articles)]
        if not cluster_articles:
            continue

        summary = ai.generate_summary(
            category=cluster.get("category", "crypto"),
            title_en=cluster.get("representative_title_en", ""),
            sources=cluster_articles,
        )
        if not summary:
            continue

        topic_id = _publish_topic(db, cluster, summary)
        if topic_id:
            _link_sources(db, topic_id, cluster_articles)
            published += 1

        _mark_processed(db, [a["id"] for a in cluster_articles])

    logger.info(f"Published {published} topics")
    return {"processed": published}


def _publish_topic(db: Client, cluster: dict, summary: dict) -> str | None:
    now = datetime.now(timezone.utc).isoformat()
    is_breaking = cluster.get("is_breaking", False)
    topic = {
        "title_ja": summary.get("title_ja", cluster.get("representative_title_ja", "")),
        "title_en": summary.get("title_en", cluster.get("representative_title_en", "")),
        "body_ja": summary.get("body_ja", ""),
        "body_en": summary.get("body_en", ""),
        "summary_ja": summary.get("summary_ja", ""),
        "summary_en": summary.get("summary_en", ""),
        "category": cluster.get("category", "crypto"),
        "status": "published",
        "is_breaking": is_breaking,
        "importance_score": cluster.get("importance_score", 0.5),
        "published_at": now,
        "updated_at": now,
    }
    try:
        res = db.table("topics").insert(topic).execute()
        topic_id = res.data[0]["id"]
        db.table("topic_events").insert({
            "topic_id": topic_id,
            "event_type": "breaking" if is_breaking else "created",
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
    db.table("raw_articles").update({"processed": True}).in_("id", article_ids).execute()


def process_pubsub(event, context):
    """Cloud Functions Pub/Sub trigger."""
    if "data" in event:
        article = json.loads(base64.b64decode(event["data"]).decode("utf-8"))
        logger.info(f"Pub/Sub triggered for: {article.get('source_url')}")
    return process()


if __name__ == "__main__":
    process()
