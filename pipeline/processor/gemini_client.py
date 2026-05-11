"""Gemini API wrapper with cost tracking and output validation."""
import hashlib
import json
import logging
import os
import time
from typing import Any, Optional

import google.generativeai as genai
from pydantic import BaseModel, ValidationError, field_validator
from supabase import Client

from prompts import PROMPT_VERSION

logger = logging.getLogger(__name__)

genai.configure(api_key=os.environ["GEMINI_API_KEY"])

# モデル名は環境変数で差し替え可能（デフォルトは Google AI Studio / Vertex AI で確認すること）
PRO_MODEL = os.environ.get("GEMINI_PRO_MODEL", "gemini-2.5-pro")
FLASH_MODEL = os.environ.get("GEMINI_FLASH_MODEL", "gemini-2.5-flash")

# Gemini pricing (USD per 1M tokens)
# NOTE: 必ずGoogle AI Studio の最新価格表で確認・更新すること
COST_TABLE: dict[str, dict[str, float]] = {
    "gemini-2.5-pro":        {"input": 3.50,  "output": 10.50},
    "gemini-2.5-flash":      {"input": 0.15,  "output": 0.60},
    "gemini-2.0-pro":        {"input": 3.50,  "output": 10.50},
    "gemini-2.0-flash":      {"input": 0.10,  "output": 0.40},
    "gemini-2.0-flash-lite": {"input": 0.075, "output": 0.30},
}


# --------------- Pydantic 出力バリデーションモデル ---------------

class ClusterItem(BaseModel):
    cluster_id: str
    importance_score: float
    is_breaking: bool
    category: str
    article_indices: list[int]
    representative_title_en: str
    representative_title_ja: str

    @field_validator("importance_score")
    @classmethod
    def clamp_score(cls, v: float) -> float:
        return max(0.0, min(1.0, v))

    @field_validator("category")
    @classmethod
    def validate_category(cls, v: str) -> str:
        allowed = {"crypto", "macro", "gov", "breaking", "summary"}
        return v if v in allowed else "crypto"

    @field_validator("article_indices")
    @classmethod
    def non_negative_indices(cls, v: list[int]) -> list[int]:
        # 負数インデックスは Python の末尾参照になるため除外する
        return [i for i in v if i >= 0]


class ClusterResult(BaseModel):
    clusters: list[ClusterItem]


class SummaryResult(BaseModel):
    title_en: str
    title_ja: str
    body_en: str
    body_ja: str
    summary_en: str
    summary_ja: str


class TranslationResult(BaseModel):
    translated: str


class PeriodicSummaryResult(BaseModel):
    body_ja: str
    body_en: str


# ---------------------------------------------------------------


class GeminiClient:
    def __init__(self, db: Client):
        self._db = db
        self._pro = genai.GenerativeModel(PRO_MODEL)
        self._flash = genai.GenerativeModel(FLASH_MODEL)

    def extract_topics(self, articles: list[dict]) -> Optional[ClusterResult]:
        from prompts import TOPIC_EXTRACTION_SYSTEM, TOPIC_EXTRACTION_USER
        prompt = TOPIC_EXTRACTION_USER.format(articles_json=json.dumps(articles, ensure_ascii=False))
        raw = self._call(self._pro, PRO_MODEL, "topic_extraction", prompt,
                         system=TOPIC_EXTRACTION_SYSTEM)
        if raw is None:
            return None
        try:
            return ClusterResult.model_validate(raw)
        except ValidationError as e:
            logger.error(f"topic_extraction validation failed: {e}")
            return None

    def generate_summary(self, category: str, title_en: str, sources: list[dict]) -> Optional[SummaryResult]:
        from prompts import SUMMARY_SYSTEM, SUMMARY_USER
        sources_text = "\n\n".join(
            f"[{s.get('source_name', '')}] {s.get('title_raw', '')}\n{s.get('body_raw', '')[:500]}"
            for s in sources
        )
        prompt = SUMMARY_USER.format(category=category, title_en=title_en, sources_text=sources_text)
        raw = self._call(self._pro, PRO_MODEL, "summary_generation", prompt,
                         system=SUMMARY_SYSTEM)
        if raw is None:
            return None
        try:
            return SummaryResult.model_validate(raw)
        except ValidationError as e:
            logger.error(f"summary_generation validation failed: {e}")
            return None

    def translate(self, text: str) -> Optional[str]:
        from prompts import TRANSLATION_SYSTEM, TRANSLATION_USER
        prompt = TRANSLATION_USER.format(text=text)
        raw = self._call(self._flash, FLASH_MODEL, "translation", prompt,
                         system=TRANSLATION_SYSTEM)
        if raw is None:
            return None
        try:
            return TranslationResult.model_validate(raw).translated
        except ValidationError as e:
            logger.error(f"translation validation failed: {e}")
            return None

    def generate_periodic_summary(self, period: str, topics: list[dict]) -> Optional[PeriodicSummaryResult]:
        from prompts import PERIODIC_SUMMARY_USER, SUMMARY_SYSTEM
        prompt = PERIODIC_SUMMARY_USER.format(
            period=period,
            topics_json=json.dumps(topics, ensure_ascii=False)
        )
        raw = self._call(self._pro, PRO_MODEL, "periodic_summary", prompt,
                         system=SUMMARY_SYSTEM)
        if raw is None:
            return None
        try:
            return PeriodicSummaryResult.model_validate(raw)
        except ValidationError as e:
            logger.error(f"periodic_summary validation failed: {e}")
            return None

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
                output = json.loads(resp.text.strip())
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
            pricing = COST_TABLE.get(model, {"input": 0.0, "output": 0.0})
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
