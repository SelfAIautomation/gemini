# MISTAKE_LOG.md

Claude Code の作業中に発生したミス、ユーザーからの訂正、レビュー指摘を記録する。

目的:
- 同じミスを再発させない。
- 単発の注意ではなく、再発防止ルールへ変換する。
- Push前レビューの観点を増やす。

---

## 記録テンプレート

```
### YYYY-MM-DD / ML-XXXX: タイトル

#### 状況
何をしようとしていたか。

#### 実際に起きたミス
何を間違えたか。

#### ユーザーからの訂正
何を指摘されたか。

#### 根本原因
なぜ起きたか。

#### 再発防止ルール
次回から何を必ずするか。

#### 昇格先
- [ ] .claude/rules/10-known-mistakes.md
- [ ] .claude/rules/20-pre-push-checklist.md

#### 関連コミット / PR
```

---

## 2026-05-11 / ML-0001〜ML-0020: CB Terminal実装レビューで指摘された全ミス

### 状況
CB Terminal型ニュース収集・AI処理・SSRフロントエンドを一式実装し、PR #1 として作成した。
その後3回のレビューラウンドで、以下のミスが発見・修正された。

---

### ML-0001: requirements.txt に functions-framework が不足 & hashlib2 が誤記

#### 実際に起きたミス
- Dockerfile の CMD が `functions_framework` を起動するのに、`requirements.txt` に未記載。
- `hashlib` は Python 標準ライブラリだが、存在しない `hashlib2` を書いた。

#### 根本原因
- Dockerfile の CMD と requirements.txt を別々に書いて整合確認をしなかった。
- 標準ライブラリと外部パッケージの区別を確認しなかった。

#### 再発防止ルール
- Dockerfile の CMD/ENTRYPOINT が使うモジュールが requirements.txt に含まれているか確認する。
- 標準ライブラリ（hashlib, json, os, time, datetime 等）を requirements.txt に書かない。

#### 昇格先
- [x] KM-0001, KM-0002 として `.claude/rules/10-known-mistakes.md` に反映済み

---

### ML-0002: 使わない langsmith 依存を requirements.txt に残した

#### 実際に起きたミス
`requirements.txt` に `langsmith==0.1.77` を追加したが、コード内で一度も import しなかった。

#### 根本原因
設計段階で「後で使う予定」として入れたが、実装しなかった。

#### 再発防止ルール
「後で使う予定」の依存は入れない。実装してから追加する。

#### 昇格先
- [x] KM-0003 として `.claude/rules/10-known-mistakes.md` に反映済み

---

### ML-0003: ETag / Last-Modified をメモリキャッシュに持った（Cloud Run では永続しない）

#### 実際に起きたミス
`RSSFetcher` クラスが `_etag_cache` と `_lm_cache` をインスタンス変数に持っていた。
Cloud Run は毎回起動するため、キャッシュは一切機能しない。

#### 根本原因
Cloud Run のステートレス性を考慮せず、通常の長期プロセスと同じ設計をした。

#### 再発防止ルール
Cloud Run で使う状態（キャッシュ、カウンター等）はDBに永続化する。
`source_fetch_state` テーブルに ETag/Last-Modified を保存し、起動のたびに読み込む。

#### 昇格先
- [x] KM-0004 として `.claude/rules/10-known-mistakes.md` に反映済み

---

### ML-0004: max_requests_per_hour がスキーマに定義されていたが実装で使われていなかった

#### 実際に起きたミス
`domain_rules.max_requests_per_hour` カラムを追加したが、`can_fetch()` では参照していなかった。

#### 根本原因
DBスキーマと実装コードを別々に書き、カラムを追加した際に実装側の更新を忘れた。

#### 再発防止ルール
DBカラムを追加したら、そのカラムを実際に読み書きする実装を必ず合わせて追加する。

#### 昇格先
- [x] KM-0005 として `.claude/rules/10-known-mistakes.md` に反映済み

---

### ML-0005: 304 Not Modified 時に content_hash を NULL で上書きした

#### 実際に起きたミス
304 時も 200 時と同じ `save_fetch_state()` を呼び、`content_hash=None` を upsert した。
既存の `content_hash` が NULL に上書きされる可能性があった。

#### 根本原因
304 と 200 で更新すべきフィールドが異なることを考慮せず、一つの upsert 関数を使い回した。

#### 再発防止ルール
- 304 時: `touch_fetch_state()`（last_checked_at のみ UPDATE）
- 200 時: `save_success_fetch_state()`（全フィールドを upsert）

#### 昇格先
- [x] KM-0006 として `.claude/rules/10-known-mistakes.md` に反映済み

---

### ML-0006: 並列ワーカーが同じ raw_articles を重複処理する可能性があった

#### 実際に起きたミス
`processed=false` を SELECT してから UPDATE するパターンで実装した。
Pub/Sub が複数の Processor インスタンスを起動した場合、同じ記事を重複処理し、重複トピックが生成される。

#### 根本原因
Cloud Run のスケールアウトを考慮せず、シングルプロセス前提の設計をした。

#### 再発防止ルール
キュー処理は `FOR UPDATE SKIP LOCKED` を使う `claim_raw_articles()` RPC でアトミックにクレームする。
Stale claim は `release_stale_claims()` で定期解放する。

#### 昇格先
- [x] KM-0007 として `.claude/rules/10-known-mistakes.md` に反映済み

---

### ML-0007: topic insert 失敗でも記事を processed 扱いにした

#### 実際に起きたミス
`_publish_topic()` が失敗（None を返す）しても、`processed_ids.extend()` が unconditional に実行された。

#### 根本原因
成功・失敗のどちらでも同じ後処理を実行するフローになっていた。

#### 再発防止ルール
`processed=true` への更新は、対応する topic insert が成功した場合だけ実行する。
失敗した記事は `_release_claims()` に回して再試行させる。

#### 昇格先
- [x] KM-0008 として `.claude/rules/10-known-mistakes.md` に反映済み

---

### ML-0008: LLM の JSON 出力をバリデーションなしで使用した

#### 実際に起きたミス
Gemini の JSON 出力を `json.loads()` しただけで、pydantic による型検証なしに使用した。
`article_indices` に `-1` が含まれても検出できず、`articles[-1]`（最後の要素）が混入する可能性があった。

#### 根本原因
LLM 出力を「信頼できるデータ」として扱った。

#### 再発防止ルール
LLM 出力は必ず pydantic モデルで検証する。
`article_indices` は非負バリデーターを入れる。コード側でも `0 <= i < len(articles)` で二重確認する。

#### 昇格先
- [x] KM-0009 として `.claude/rules/10-known-mistakes.md` に反映済み

---

### ML-0009: Prompt injection 対策を入れなかった

#### 実際に起きたミス
RSS 本文をそのままプロンプトに組み込んでいたが、インジェクション対策文を system prompt に追加していなかった。

#### 根本原因
外部テキストのリスクを考慮していなかった。

#### 再発防止ルール
外部テキストをプロンプトに含める場合、`_INJECTION_GUARD` を全 system prompt に付与する。

#### 昇格先
- [x] KM-0010 として `.claude/rules/10-known-mistakes.md` に反映済み

---

### ML-0010: Cloud Build の deploy step に secretEnv を指定しなかった

#### 実際に起きたミス
`availableSecrets` は定義したが、各 deploy step に `secretEnv` を書かなかった。
`$$SUPABASE_URL` 等が展開されず、Cloud Run の環境変数が空になる。

#### 根本原因
Cloud Build の Secret Manager の仕組みを正確に理解していなかった。

#### 再発防止ルール
`$$VAR` を使う step には step レベルで `secretEnv: [VAR]` を書く。

#### 昇格先
- [x] KM-0011 として `.claude/rules/10-known-mistakes.md` に反映済み

---

### ML-0011: Cloud Run Invoker 権限付与手順を README に書かなかった

#### 実際に起きたミス
`--no-allow-unauthenticated` でデプロイしたが、Scheduler/Pub/Sub から呼び出す IAM 設定手順を README に書かなかった。

#### 根本原因
Cloud Run の認証設定と IAM 付与を別工程と認識していなかった。

#### 再発防止ルール
`--no-allow-unauthenticated` を使う Cloud Run の README には必ず Invoker IAM 付与コマンドを記載する。

#### 昇格先
- [x] KM-0012 として `.claude/rules/10-known-mistakes.md` に反映済み

---

### ML-0012: topic_events の RLS が USING (true) で全件公開だった

#### 実際に起きたミス
`topic_events` の anon ポリシーを `USING (true)` にした。
old_value / new_value に内部情報が入れば全部公開される。

#### 根本原因
「Realtime に必要だから公開」とだけ考えて、公開範囲を絞らなかった。

#### 再発防止ルール
`topic_events` の anon 公開は、`published` 状態のトピックに紐づくイベントだけに限定する。

#### 昇格先
- [x] KM-0013 として `.claude/rules/10-known-mistakes.md` に反映済み

---

### ML-0013: Realtime Publication を DROP/CREATE で実装した

#### 実際に起きたミス
migration に `DROP PUBLICATION IF EXISTS supabase_realtime; CREATE PUBLICATION ...` を書いた。
既存の Realtime 設定が全て消える可能性があった。

#### 根本原因
idempotent な実装のつもりで DROP/CREATE を選んだが、既存設定への影響を考慮しなかった。

#### 再発防止ルール
`ALTER PUBLICATION supabase_realtime ADD TABLE table_name` を使う。
DO ブロックで「存在しなければ CREATE、存在すれば ALTER ADD」とする。

#### 昇格先
- [x] KM-0014 として `.claude/rules/10-known-mistakes.md` に反映済み

---

### ML-0014: Supabase クライアントをモジュールレベルで初期化した

#### 実際に起きたミス
`lib/supabase.ts` で `const supabase = createClient(url, key)` をモジュールトップレベルに書いた。
環境変数未設定時に import 時点でクラッシュし、try/catch のサンプル表示が効かない。

#### 根本原因
「モジュールロード時に一度だけ初期化」という発想で書いたが、エラーハンドリングとの相性を考えなかった。

#### 再発防止ルール
`createClient` は関数内で遅延初期化する。環境変数未設定は明確なエラーメッセージで伝える。
server/browser でクライアントを分ける: `lib/supabase/server.ts` と `lib/supabase/browser.ts`。

#### 昇格先
- [x] KM-0016 として `.claude/rules/10-known-mistakes.md` に反映済み

---

### ML-0015: Realtime INSERT で重複排除をしなかった

#### 実際に起きたミス
`onInsert` が `setTopics(prev => [topic, ...prev])` を無条件に実行した。
再接続時に同じトピックが複数行に増える可能性があった。

#### 根本原因
Realtime が重複イベントを送る可能性を考慮しなかった。

#### 再発防止ルール
INSERT ハンドラーで `prev.some(t => t.id === topic.id)` で重複チェックしてから追加する。

#### 昇格先
- [x] KM-0017 として `.claude/rules/10-known-mistakes.md` に反映済み

---

### ML-0016: package.json に入れた @supabase/ssr を実際には使わなかった

#### 実際に起きたミス
`@supabase/ssr` を dependencies に追加したが、コード内では `@supabase/supabase-js` の `createClient` のみを使った。

#### 根本原因
「SSR構成にするつもり」で入れたが、実装まで追いつかなかった。

#### 再発防止ルール
「後で使う予定」の依存は入れない。実装してから追加する。

#### 昇格先
- [x] KM-0018 として `.claude/rules/10-known-mistakes.md` に反映済み

---

### ML-0017: /summary エンドポイントを README に書いたが実装しなかった

#### 実際に起きたミス
README に `https://cb-processor-HASH.a.run.app/summary?period=6h` と書いたが、
`process()` 関数にはパスルーティングがなく、`/summary` を叩いても通常バッチが走った。

#### 根本原因
README を実装より先に書き、実装側と整合確認をしなかった。

#### 再発防止ルール
README に記載した URL パスに対応するルーティングを実装コードに必ず追加する。

#### 昇格先
- [x] KM-0019 として `.claude/rules/10-known-mistakes.md` に反映済み

---

### ML-0018: Retry-After の HTTP 日付形式を処理しなかった

#### 実際に起きたミス
`int(resp.headers.get("Retry-After", 60))` を使用。HTTP 日付形式（例: `Wed, 21 Oct 2026 07:28:00 GMT`）で `ValueError` になる。

#### 根本原因
`Retry-After` が秒数以外の形式でも返ることを知らなかった。

#### 再発防止ルール
`parse_retry_after()` を作り、`int()` と `parsedate_to_datetime()` の両方を試みる。

#### 昇格先
- [x] KM-0020 として `.claude/rules/10-known-mistakes.md` に反映済み

---

### ML-0019: Supabase CLI コマンドが不正確だった

#### 実際に起きたミス
README に `supabase db push supabase/migrations/001_initial_schema.sql` と書いた。
このコマンドは特定ファイル単体を適用するものではない。

#### 根本原因
Supabase CLI の仕様を確認せずに書いた。

#### 再発防止ルール
正しい手順: `supabase link --project-ref <ref>` → `supabase db push`。
または SQL Editor で手動実行することを明記する。

#### 昇格先
- [x] KM-0015 として `.claude/rules/10-known-mistakes.md` に反映済み

---

### ML-0020: topic insert 失敗時も processed=true になるコードを書いた（ML-0007 詳細）

「記録テンプレート」の繰り返しを避けるため、ML-0007 を参照。
本件で重要なのは、「成功確認前に後処理を実行するフロー」が複数箇所で発生しやすいという点。

追加再発防止:
- 副作用のある操作（DB insert、外部API呼び出し等）の後続処理は、成功確認後に書く。
- 例外が発生した場合の「巻き戻し」または「再試行可能な状態への復元」を設計段階で考える。
