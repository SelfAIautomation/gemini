---
name: pre-push-review
description: Review current git diff before pushing to GitHub, checking known mistakes, tests, scope, and project rules.
---

# Pre Push Review Skill

GitHub に Push する前に、以下を必ず実行する。

## 必須確認

1. `git status` を確認する。
2. `git diff --name-only` で変更ファイル一覧を確認する。
3. `git diff` の内容を確認する。
4. `.claude/rules/10-known-mistakes.md` を読み、各 KM-XXXX と照合する。
5. `.claude/rules/20-pre-push-checklist.md` の全チェック項目を確認する。
6. 以下のコマンドのうち、このリポジトリで利用可能なものを実行する:
   - `npm run type-check`
   - `npm run lint`
   - `npm run build`
   - `python -m py_compile <変更ファイル>`
7. 実行できなかった項目は理由を明記する。
8. 今回の作業から新たな再発防止ルールが必要なら `docs/ai-lessons/MISTAKE_LOG.md` に追記する。

## 出力形式

以下の形式で報告する。

```
### Push前レビュー結果

**変更ファイル:**
- ...

**変更目的:**
- ...

**依頼範囲外の変更:**
- なし / あり（理由: ...）

**既知ミス(KM)との照合:**
- KM-0001: ✅ / ❌（内容: ...）
- ...

**実行したコマンド:**
- ...

**失敗・未実行の確認項目:**
- ...

**新たな教訓:**
- なし / あり（MISTAKE_LOG 追記済み）

**Pushしてよいか:**
- ✅ Push 可 / ❌ Push 不可（理由: ...）
```

## 使い方

```
/pre-push-review
GitHubにPushする前に、今回の差分を既知ミスと照合してレビューしてください。
```
