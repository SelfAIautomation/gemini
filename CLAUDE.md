# CLAUDE.md

このリポジトリで作業する場合、Claude Code は必ず以下を守ること。

## 最重要ルール

- 実装前に `.claude/rules/00-core-rules.md` を読む。
- 過去のミスを避けるため、`.claude/rules/10-known-mistakes.md` を読む。
- GitHub に Push または PR 作成する前に `.claude/rules/20-pre-push-checklist.md` を読む。
- 仕様・構成・ファイル名・既存ルールを推測で決めない。必ず既存ファイルを確認してから変更する。
- ユーザーから訂正された内容は、単なる会話で終わらせず、`docs/ai-lessons/MISTAKE_LOG.md` に記録し、再発防止ルールへ昇格する。

## 読み込み対象

@.claude/rules/00-core-rules.md
@.claude/rules/10-known-mistakes.md
@.claude/rules/20-pre-push-checklist.md
@.claude/rules/30-language-specific.md

## Push前の必須手順

Push前に以下を実施する。

1. `git diff --name-only` で変更ファイル一覧を確認する。
2. 変更対象がユーザー依頼と一致しているか確認する。
3. `.claude/rules/10-known-mistakes.md` の既知ミスに該当しないか照合する。
4. テスト・lint・型チェックがある場合は実行する。
5. 今回の作業から新しい教訓があれば `docs/ai-lessons/MISTAKE_LOG.md` に追記する。
