"""Gemini API wrapper with cost tracking and LangSmith logging."""
import hashlib
import json
import logging
import os
import time
from typing import Any, Optional

import google.generativeai as genai
from supabase import Client

from prompts import PROMPT_VERSION

logger = logging.getLogger(__name__)

genai.configure(api_key=os.environ["GEMINI_API_KEY"])

# Gemini pricing (USD per 1M tokens, as of 2025)
COST_TABLE = {
    "gemini-2.0-pro": {"input": 3.50, "output": 10.50},
    "gemini-2.0-flash": {"input": 0.10, "output": 0.40},
    "gemini-2.0-flash-lite": {"input": 0.075, "output": 0.30},
}


class GeminiClient:
    def __init__(self, db: Client, pro_model: str = "gemini-2.0-pro", flash_model: str = "gemini-2.0-flash"):
        self._db = db
        self._pro = genai.GenerativeModel(pro_model)
        self._flash = genai.GenerativeModel(flash_model)
        self._pro_model_name = pro_model
        self._flash_model_name = flash_model

    def extract_topics(self, articles: list[dict]) -> Optional[dict]:
        from prompts import TOPIC_EXTRACTION_SYSTEM, TOPIC_EXTRACTION_USER
        prompt = TOPIC_EXTRACTION_USER.format(articles_json=json.dumps(articles, ensure_ascii=False))
        return self._call(self._pro, self._pro_model_name, "topic_extraction", prompt,
                          system=TOPIC_EXTRACTION_SYSTEM)

    def generate_summary(self, category: str, title_en: str, sources: list[dict]) -> Optional[dict]:
        from prompts import SUMMARY_SYSTEM, SUMMARY_USER
        sources_text = "\n\n".join(
            f"[{s.get('source_name', '')}] {s.get('title_raw', '')}\n{s.get('body_raw', '')[:500]}"
            for s in sources
        )
        prompt = SUMMARY_USER.format(category=category, title_en=title_en, sources_text=sources_text)
        return self._call(self._pro, self._pro_model_name, "summary_generation", prompt,
                          system=SUMMARY_SYSTEM)

    def translate(self, text: str) -> Optional[str]:
        from prompts import TRANSLATION_SYSTEM, TRANSLATION_USER
        prompt = TRANSLATION_USER.format(text=text)
        result = self._call(self._flash, self._flash_model_name, "translation", prompt,
                            system=TRANSLATION_SYSTEM)
        return result.get("translated") if result else None

    def generate_periodic_summary(self, period: str, topics: list[dict]) -> Optional[dict]:
        from prompts import PERIODIC_SUMMARY_USER, SUMMARY_SYSTEM
        prompt = PERIODIC_SUMMARY_USER.format(
            period=period,
            topics_json=json.dumps(topics, ensure_ascii=False)
        )
        return self._call(self._pro, self._pro_model_name, "periodic_summary", prompt,
                          system=SUMMARY_SYSTEM)

    def _call(self, model, model_name: str, job_type: str, prompt: str,
              system: str = "", retries: int = 3) -> Optional[dict]:
        input_hash = hashlib.sha256(prompt.encode()).hexdigest()
        full_prompt = f"{system}\n\n{prompt}" if system else prompt

        last_error = None
        for attempt in range(retries):
            start = time.time()
            try:
                resp = model.generate_content(
                    full_prompt,
                    generation_config=genai.GenerationConfig(
                        response_mime_type="application/json",
                        temperature=0.3,
                    )
                )
                latency_ms = int((time.time() - start) * 1000)
                text = resp.text.strip()
                output = json.loads(text)
                self._log(job_type, model_name, input_hash, output, latency_ms, True, None, resp)
                return output
            except json.JSONDecodeError as e:
                last_error = f"json_parse_error: {e}"
                logger.warning(f"{job_type} JSON parse failed (attempt {attempt+1}): {e}")
            except Exception as e:
                last_error = str(e)
                logger.warning(f"{job_type} API error (attempt {attempt+1}): {e}")
                if attempt < retries - 1:
                    time.sleep(2 ** attempt)

        self._log(job_type, model_name, input_hash, None, 0, False, last_error, None)
        return None

    def _log(self, job_type: str, model: str, input_hash: str,
             output: Any, latency_ms: int, success: bool,
             error: Optional[str], resp: Any) -> None:
        cost = 0.0
        if resp and hasattr(resp, "usage_metadata"):
            pricing = COST_TABLE.get(model, {"input": 0, "output": 0})
            cost = (
                resp.usage_metadata.prompt_token_count * pricing["input"]
                + resp.usage_metadata.candidates_token_count * pricing["output"]
            ) / 1_000_000
        try:
            self._db.table("ai_logs").insert({
                "job_type": job_type,
                "model": model,
                "prompt_version": PROMPT_VERSION,
                "input_hash": input_hash,
                "output": output,
                "cost_usd": cost,
                "latency_ms": latency_ms,
                "success": success,
                "error_message": error,
            }).execute()
        except Exception as e:
            logger.error(f"ai_logs insert failed: {e}")
