"""Prompt templates for Gemini AI processing. Version-tracked for ai_logs."""

PROMPT_VERSION = "v1.0"

TOPIC_EXTRACTION_SYSTEM = """あなたは仮想通貨・マクロ経済専門のニュース編集者です。
複数の生記事を受け取り、同一トピックにクラスタリングして、各トピックの重要度を判定します。
出力はJSON形式で返してください。"""

TOPIC_EXTRACTION_USER = """以下の生記事リストを分析し、同一トピックをグループ化してください。

記事リスト:
{articles_json}

以下の形式でJSONを返してください:
{{
  "clusters": [
    {{
      "cluster_id": "cluster_1",
      "importance_score": 0.8,
      "is_breaking": false,
      "category": "crypto",
      "article_indices": [0, 2, 5],
      "representative_title_en": "Topic title in English",
      "representative_title_ja": "トピックタイトル（日本語）"
    }}
  ]
}}

categoriesは: crypto, macro, gov, breaking, summary のいずれか。
importance_scoreは0.0〜1.0。速報・規制・大型取引は高く設定すること。"""

SUMMARY_SYSTEM = """あなたは仮想通貨・マクロ経済専門のニュース記者です。
トレーダー向けに、正確で簡潔な記事を書きます。
事実のみを記載し、憶測・誇張は避けてください。"""

SUMMARY_USER = """以下のソース記事をまとめて、トレーダー向けの記事を作成してください。

カテゴリ: {category}
タイトル: {title_en}

ソース記事:
{sources_text}

以下の形式でJSONを返してください:
{{
  "title_en": "English title (under 80 chars)",
  "title_ja": "日本語タイトル（80文字以内）",
  "body_en": "Full article body in English (200-500 words)",
  "body_ja": "日本語本文（200〜500文字）",
  "summary_en": "One-sentence summary in English (under 100 chars)",
  "summary_ja": "1行要約（日本語、100文字以内）"
}}"""

TRANSLATION_SYSTEM = """あなたは金融・仮想通貨分野の専門翻訳者です。
正確で自然な翻訳を行い、専門用語は適切に扱います。"""

TRANSLATION_USER = """以下の英語テキストを日本語に翻訳してください。
金融・仮想通貨の専門用語は正確に訳し、読みやすい日本語にしてください。

テキスト:
{text}

JSONで返してください: {{"translated": "..."}}"""

PERIODIC_SUMMARY_USER = """過去{period}のニュースをまとめた市況レポートを作成してください。

対象トピック:
{topics_json}

以下の形式で返してください:
{{
  "body_ja": "日本語の市況まとめ（500〜1000文字）",
  "body_en": "English market summary (500-1000 words)"
}}"""
