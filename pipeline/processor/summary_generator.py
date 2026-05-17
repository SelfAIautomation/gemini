"""Periodic market summary generator (6h / 24h / weekly).

Called from main.process() when path is /summary?period=...
"""
import logging
import os
from datetime import datetime, timedelta, timezone

from dotenv import load_dotenv
from supabase import create_client

from gemini_client import GeminiClient

load_dotenv()
logger = logging.getLogger(__name__)

PERIOD_HOURS = {"6h": 6, "24h": 24, "weekly": 168}


def generate_periodic_summary(period_type: str = "6h") -> dict:
    db = create_client(os.environ["SUPABASE_URL"], os.environ["SUPABASE_SERVICE_KEY"])
    ai = GeminiClient(db)

    hours = PERIOD_HOURS.get(period_type, 6)
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
        return {"status": "no_topics", "period": period_type}

    result = ai.generate_periodic_summary(period_type, topics)
    if not result:
        logger.error("Periodic summary generation failed")
        return {"status": "ai_failed", "period": period_type}

    db.table("summaries").insert({
        "period_type": period_type,
        "body_ja": result.body_ja,
        "body_en": result.body_en,
        "topic_ids": [t["id"] for t in topics],
    }).execute()

    logger.info(f"Generated {period_type} summary from {len(topics)} topics")
    return {"status": "ok", "period": period_type, "topics_count": len(topics)}


if __name__ == "__main__":
    import sys
    period = sys.argv[1] if len(sys.argv) > 1 else "6h"
    print(generate_periodic_summary(period))
