# CB Terminal Clone

仮想通貨・マクロ経済ニュースを自動収集し、Gemini AIでトピック化・要約・翻訳し、
Supabase Realtimeでブラウザに配信するニュース端末型Webアプリ。

## アーキテクチャ

```
情報ソース (RSS/API)
  ↓
GCP Cloud Scheduler (5分毎)
  ↓
Cloud Run: Collector
  - レート制限 (domain_rules)
  - ETag/Last-Modified キャッシュ
  - 429/403 の自動停止
  ↓
Pub/Sub
  ↓
Cloud Run: Processor (Gemini 2.0 Pro)
  - トピック抽出・クラスタリング
  - 重複排除
  - 要約・翻訳 (Gemini 2.0 Flash)
  - カテゴリ分類
  ↓
Supabase PostgreSQL (RLS有効)
  ↓
Supabase Realtime → ブラウザPush
  ↓
Vercel: Next.js SSR フロントエンド
```

## ディレクトリ構成

```
├── supabase/migrations/     DBスキーマ (RLS付き)
├── pipeline/
│   ├── collector/           ニュース収集ワーカー (Python)
│   └── processor/           Gemini AI処理ワーカー (Python)
└── frontend/                Next.js SSR + Supabase Realtime
```

## セットアップ

### 1. Supabase

```bash
supabase db push supabase/migrations/001_initial_schema.sql
```

### 2. パイプライン

```bash
cd pipeline/collector
cp .env.example .env  # SUPABASE_URL, SUPABASE_SERVICE_KEY, GCP_PROJECT_ID を設定
pip install -r requirements.txt
python main.py

cd ../processor
pip install -r requirements.txt
# .env に GEMINI_API_KEY を追加
python main.py
```

### 3. フロントエンド

```bash
cd frontend
cp .env.example .env.local  # NEXT_PUBLIC_SUPABASE_URL, NEXT_PUBLIC_SUPABASE_ANON_KEY を設定
npm install
npm run dev
```

## GCP デプロイ

```bash
cd pipeline
gcloud builds submit --config=cloudbuild.yaml
```

Cloud Scheduler 設定例:
- Collector: `*/5 * * * *` → Pub/Sub: `news-collect`
- まとめ (6h): `0 */6 * * *` → Pub/Sub: `news-summary-6h`
- まとめ (24h): `0 9 * * *` → Pub/Sub: `news-summary-24h`

## 設計上の注意点

- `domain_rules` テーブルで全ドメインのレート制限を管理
- 429/403 が3回続いたドメインは自動無効化
- RLS により anon は公開済みトピックのみ読み取り可
- service_role キーはサーバーサイドのみで使用
- Supabase Realtime は `topics` と `topic_events` テーブルのみ公開
