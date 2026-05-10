"""Periodic market summary generator (6h / 24h).

Triggered by Cloud Scheduler via Pub/Sub.
"""
import logging
import os
from datetime import datetime, timedelta, timezone

from dotenv import load_dotenv
from supabase import create_client

from gemini_client import GeminiClient

load_dotenv()
logger = logging.getLogger(__name__)


def generate_periodic_summary(period_type: str = "6h"):
    db = create_client(os.environ["SUPABASE_URL"], os.environ["SUPABASE_SERVICE_KEY"])
    ai = GeminiClient(db)

    hours = 6 if period_type == "6h" else 24
    since = (datetime.now(timezone.utc) - timedelta(hours=hours)).isoformat()

    topics = (
        db.table("topics")
        .select("id, title_ja, title_en, summary_ja, category, importance_score")
        .eq("status", "published")
        .gte("published_at", since)
        .order("importance_score", desc=True)
        .limit(30)
        .execute()
        .data
    )

    if not topics:
        logger.info(f"No topics for {period_type} summary")
        return

    result = ai.generate_periodic_summary(period_type, topics)
    if not result:
        logger.error("Periodic summary generation failed")
        return

    db.table("summaries").insert({
        "period_type": period_type,
        "body_ja": result.get("body_ja", ""),
        "body_en": result.get("body_en", ""),
        "topic_ids": [t["id"] for t in topics],
    }).execute()
    logger.info(f"Generated {period_type} summary")


if __name__ == "__main__":
    import sys
    period = sys.argv[1] if len(sys.argv) > 1 else "6h"
    generate_periodic_summary(period)
