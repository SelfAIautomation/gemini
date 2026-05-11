---
name: record-mistake
description: Record a user correction or Claude Code mistake into the project mistake log and convert it into a reusable prevention rule.
---

# Record Mistake Skill

ユーザーから訂正、レビュー指摘、再発防止が必要なミスを受けた場合、この手順を実行する。

## 手順

1. ユーザーの訂正内容を1〜2文で要約する。
2. 該当する変更差分・ファイル・根本原因を確認する。
3. `docs/ai-lessons/MISTAKE_LOG.md` に以下の形式で新しいエントリを追加する:
   - 状況 / 実際に起きたミス / ユーザーからの訂正 / 根本原因 / 再発防止ルール / 昇格先
4. 再発可能性が高い場合は `.claude/rules/10-known-mistakes.md` に KM-XXXX として追加する。
5. Push前に確認すべき内容であれば `.claude/rules/20-pre-push-checklist.md` に追加する。
6. 機械的に検出できる内容であれば `scripts/ai-guard/check-before-push.ps1` へのチェック追加を提案する。

## 記録時の原則

- 感情的な反省文を書かない。「次回何を必ず確認するか」を行動として書く。
- 「注意する」「気をつける」は書かない。検証可能な行動に変換する。
  - 悪い例: 「設定ファイルに注意する」
  - 良い例: 「設定ファイルを変更する前に必ず `Read` で現在の内容を確認する」
- 既存ルールと重複する場合は追記ではなく統合する。
- 古いルールと矛盾する場合は矛盾を解消する。

## 使い方

```
/record-mistake
今のミスを docs/ai-lessons/MISTAKE_LOG.md に記録し、
再発防止ルールとして .claude/rules/10-known-mistakes.md に昇格してください。
```
