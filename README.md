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
  - domain_rules によるレート制限 (interval + max/hour)
  - source_fetch_state で ETag/Last-Modified を DB 永続化
  - 429/403 が3回続いたドメインは自動無効化
  ↓
Pub/Sub (news-process)
  ↓
Cloud Run: Processor (Gemini 2.5 Pro)
  - トピック抽出・クラスタリング (pydantic バリデーション付き)
  - 重複排除
  - 要約・翻訳 (Gemini 2.5 Flash)
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
│   ├── 001_initial_schema.sql
│   ├── 002_fetch_state_and_rls_fixes.sql
│   └── 003_processing_flag.sql
├── pipeline/
│   ├── collector/           ニュース収集ワーカー (Python)
│   ├── processor/           Gemini AI処理ワーカー (Python)
│   └── cloudbuild.yaml      GCP Cloud Build 設定
└── frontend/                Next.js SSR + Supabase Realtime
    └── lib/supabase/
        ├── server.ts        SSR 用クライアント (遅延初期化)
        └── browser.ts       Realtime 用ブラウザクライアント
```

## セットアップ

### 1. Supabase

```bash
# Supabase CLI を使う場合 (supabase link 済みのプロジェクト)
supabase link --project-ref your-project-ref
supabase db push   # supabase/migrations/ 配下を順番に適用

# Supabase CLI が使えない場合は、Supabase Dashboard > SQL Editor で
# 001 → 002 → 003 の順に貼り付けて実行してください
```

> **注意**: 001 だけ実行して止めないこと。002 の RLS 修正と 003 の
> processing フラグが適用されていない状態では、本番運用は危険です。

### 2. パイプライン環境変数

```bash
# pipeline/.env (ローカル開発用)
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_SERVICE_KEY=your-service-role-key
GCP_PROJECT_ID=your-gcp-project-id
GEMINI_API_KEY=your-gemini-api-key

# User-Agent を自分のサービス用に変更すること
BOT_CONTACT_URL=https://your-domain.example/bot-info
BOT_CONTACT_EMAIL=bot@your-domain.example

# Gemini モデル名 (Google AI Studio で確認して設定)
GEMINI_PRO_MODEL=gemini-2.5-pro
GEMINI_FLASH_MODEL=gemini-2.5-flash
```

### 3. Collector ローカル実行

```bash
cd pipeline/collector
pip install -r requirements.txt
python main.py
```

### 4. Processor ローカル実行

```bash
cd pipeline/processor
pip install -r requirements.txt
python main.py
```

### 5. フロントエンド

```bash
cd frontend
cp .env.example .env.local
# .env.local に NEXT_PUBLIC_SUPABASE_URL, NEXT_PUBLIC_SUPABASE_ANON_KEY を設定
npm install
npm run dev
```

## GCP デプロイ

### Secret Manager 設定

```bash
echo -n "https://your-project.supabase.co" | \
  gcloud secrets create supabase-url --data-file=-

echo -n "your-service-role-key" | \
  gcloud secrets create supabase-service-key --data-file=-

echo -n "your-gemini-api-key" | \
  gcloud secrets create gemini-api-key --data-file=-
```

### Cloud Build 実行

```bash
cd pipeline
gcloud builds submit --config=cloudbuild.yaml
```

### Cloud Scheduler 設定

```bash
# Collector: 5分毎
gcloud scheduler jobs create http cb-collector-job \
  --schedule="*/5 * * * *" \
  --uri="https://cb-collector-HASH-an.a.run.app" \
  --oidc-service-account-email="your-sa@your-project.iam.gserviceaccount.com" \
  --location=asia-northeast1

# まとめ (6h)
gcloud scheduler jobs create http cb-summary-6h-job \
  --schedule="0 */6 * * *" \
  --uri="https://cb-processor-HASH-an.a.run.app/summary?period=6h" \
  --oidc-service-account-email="your-sa@your-project.iam.gserviceaccount.com" \
  --location=asia-northeast1

# まとめ (24h)
gcloud scheduler jobs create http cb-summary-24h-job \
  --schedule="0 9 * * *" \
  --uri="https://cb-processor-HASH-an.a.run.app/summary?period=24h" \
  --oidc-service-account-email="your-sa@your-project.iam.gserviceaccount.com" \
  --location=asia-northeast1
```

### Cloud Run Invoker 権限付与

`--no-allow-unauthenticated` でデプロイしているため、Scheduler や Pub/Sub から
呼び出すサービスアカウントに `roles/run.invoker` を付与する必要があります。

```bash
# Collector
gcloud run services add-iam-policy-binding cb-collector \
  --region=asia-northeast1 \
  --member="serviceAccount:your-sa@your-project.iam.gserviceaccount.com" \
  --role="roles/run.invoker"

# Processor
gcloud run services add-iam-policy-binding cb-processor \
  --region=asia-northeast1 \
  --member="serviceAccount:your-sa@your-project.iam.gserviceaccount.com" \
  --role="roles/run.invoker"
```

この手順を省くと Scheduler / Pub/Sub からの呼び出しが 403 で失敗します。

### Cloud Run → Pub/Sub 連携

```bash
# Pub/Sub トピック作成
gcloud pubsub topics create news-process

# Processor を Pub/Sub サブスクリプション経由で呼ぶ場合の設定
gcloud pubsub subscriptions create news-process-sub \
  --topic=news-process \
  --push-endpoint="https://cb-processor-HASH-an.a.run.app" \
  --push-auth-service-account="your-sa@your-project.iam.gserviceaccount.com"
```

## 設計上の注意点

- `domain_rules` テーブルで全ドメインの `crawl_interval_seconds` と `max_requests_per_hour` を管理
- `source_fetch_state` テーブルで ETag/Last-Modified を永続化（Cloud Run 再起動でも失われない）
  - 200 時: `save_success_fetch_state()` で全フィールドを upsert
  - 304 時: `touch_fetch_state()` で `last_checked_at` のみ更新（content_hash を NULL 上書きしない）
- 429/403 が3回続いたドメインは自動的に `enabled=false`
- Processor は `claim_raw_articles()` RPC (FOR UPDATE SKIP LOCKED) でバッチをアトミックに取得する
  - 複数 Cloud Run インスタンスが同時起動しても記事を重複処理しない
  - 10分以上 processing=true の記事は `release_stale_claims()` で自動解放
- Processor の HTTP パス: `POST /` → 通常バッチ処理、`POST /summary?period=6h|24h|weekly` → 定期まとめ
- RLS により anon は `status='published'` のトピックのみ読み取り可
- `topic_events` の anon 公開は、published トピックに紐づくイベントのみに限定
- `service_role` キーはサーバーサイドのみで使用（フロントエンドは anon key のみ）
- Supabase Realtime は `topics` と `topic_events` テーブルのみ公開
- Gemini モデル名・価格は環境変数で差し替え可能（定期的に確認・更新すること）
- migrations は **001 → 002 → 003 の順に全て適用**すること（001 だけでは RLS と処理フラグが未適用）
