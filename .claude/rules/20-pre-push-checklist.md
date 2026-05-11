# Pre Push Checklist

GitHub に Push する前に、Claude Code は必ず以下を確認する。

---

## 1. 変更範囲

- [ ] `git diff --name-only` でファイル一覧を確認した
- [ ] ユーザーが依頼していないファイルを変更していない
- [ ] `.env`、`*.log`、`__pycache__`、`node_modules`、`*.tmp` を含めていない
- [ ] 変更理由が依頼内容と一致している

## 2. 既知ミスとの照合（`.claude/rules/10-known-mistakes.md`）

- [ ] requirements.txt に Dockerfile の CMD が参照するパッケージが全て入っている
- [ ] 標準ライブラリ（hashlib等）を requirements.txt に書いていない
- [ ] 使わない依存（langsmith等）を残していない
- [ ] Cloud Run で使うキャッシュはDBに永続化している（インスタンス変数ではない）
- [ ] DBカラムを追加した場合、実装コードでも読み書きしている
- [ ] 304 時に content_hash を NULL で上書きしていない
- [ ] キュー処理で SELECT→UPDATE のパターンを使っていない（FOR UPDATE SKIP LOCKED を使う）
- [ ] topic insert 失敗時に processed=true にしていない
- [ ] LLM の JSON 出力を pydantic で検証している
- [ ] 配列インデックスアクセスで `0 <= i < len(arr)` を確認している
- [ ] 外部テキストをプロンプトに含める場合、インジェクション対策を system prompt に入れている

## 3. GCP / Cloud Build

- [ ] `cloudbuild.yaml` で `$$VAR` を参照する step に `secretEnv` が設定されている
- [ ] `--no-allow-unauthenticated` の Cloud Run に Invoker 権限付与手順を README に書いた
- [ ] migration に `DROP PUBLICATION` が含まれていない

## 4. Supabase / DB

- [ ] 新しい RLS ポリシーで anon に `USING (true)` を使っていない
- [ ] Realtime Publication の変更を `ALTER ADD TABLE` で行っている
- [ ] Supabase CLI コマンドを README に書いた場合、現行 CLI の仕様と一致している
- [ ] migration の適用順序と注意事項を README に記載した

## 5. フロントエンド

- [ ] `createClient` がモジュールトップレベルで呼ばれていない（遅延初期化になっている）
- [ ] Realtime INSERT ハンドラーで id の重複チェックをしている
- [ ] `package.json` の依存が実際にコード内で import されている

## 6. HTTP API

- [ ] README に記載したパス/エンドポイントに対応するルーティングを実装した
- [ ] `Retry-After` を `int()` で直接変換していない

## 7. 実行確認（該当するものを実行）

- [ ] `npm run type-check` / `tsc --noEmit`
- [ ] `npm run lint`
- [ ] `npm run build`
- [ ] Python: `python -m py_compile *.py`
- [ ] 実行できない場合は理由を明記する

## 8. 記録更新

- [ ] 今回の作業で新たな教訓があれば `docs/ai-lessons/MISTAKE_LOG.md` に追記した
- [ ] 再発可能性が高い場合は `.claude/rules/10-known-mistakes.md` にルールとして追加した
