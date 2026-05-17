# Language / Framework Specific Rules

## Python (パイプライン)

- `requirements.txt` の各行は `pip install` できる実在パッケージのみ。標準ライブラリは書かない。
- Cloud Run で動くコードはステートレスに設計する。状態はDBに持つ。
- Pub/Sub メッセージのペイロードは `base64.b64decode` して `json.loads` する。
- pydantic v2 の validator は `@field_validator` + `@classmethod` を使う（v1 の `@validator` は使わない）。
- 環境変数は `os.environ["KEY"]`（必須）と `os.environ.get("KEY", default)`（任意）を使い分ける。
- `load_dotenv()` はローカル開発用。Cloud Run では環境変数を直接設定する。

## GCP

- Cloud Run `--no-allow-unauthenticated`: Scheduler/Pub/Sub から叩く場合は Invoker IAM が必要。
- Cloud Build `availableSecrets`: step レベルで `secretEnv` を指定しないと `$$VAR` は展開されない。
- Pub/Sub push subscription: 認証は `--push-auth-service-account` で設定する。

## Supabase

- RLS は全テーブルで有効化する。anon は最小限のデータのみ公開。
- `service_role` キーはサーバーサイドのみ。フロントエンドは `anon` キーのみ使う。
- Realtime は公開が必要なテーブルだけ対象にする。管理テーブルは含めない。
- migration は `ALTER PUBLICATION ADD TABLE` を使い、`DROP PUBLICATION` は使わない。
- Supabase Python クライアントで `upsert` する場合、`on_conflict` を明示する。

## Next.js / TypeScript

- `'use client'` ディレクティブが必要なコンポーネントと不要なものを区別する。
- Server Component でのデータ取得は `lib/supabase/server.ts` のクライアントを使う。
- Client Component での Realtime は `lib/supabase/browser.ts` の `getBrowserClient()` を使う。
- 環境変数が未設定でも import 時にクラッシュしないよう、関数内で `createClient` を呼ぶ。
