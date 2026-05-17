## Summary

<!-- 変更の目的と概要を書く -->

## Changes

<!-- 変更したファイルと内容を箇条書きで -->

## Pre Push Checklist

> Claude Code が作業した場合は `.claude/rules/20-pre-push-checklist.md` を確認すること。

- [ ] `git diff --name-only` で依頼範囲外の変更がないことを確認した
- [ ] `.claude/rules/10-known-mistakes.md` の既知ミスと照合した
- [ ] テスト / lint / type check を実行した（または実行できない理由を明記した）
- [ ] migration を追加した場合、適用順序と注意事項を記載した
- [ ] Cloud Build の secretEnv を deploy step に設定した（該当する場合）
- [ ] `--no-allow-unauthenticated` の Cloud Run に Invoker IAM 手順を README に書いた（該当する場合）

## AI Guard

- [ ] `pwsh ./scripts/ai-guard/check-before-push.ps1 -FailOnWarnings` を実行し PASSED を確認した
- [ ] Git hooks を使う場合、`pwsh ./scripts/ai-guard/install-git-hooks.ps1` を実行済み
- [ ] 新しい教訓があれば `docs/ai-lessons/MISTAKE_LOG.md` に追記した
- [ ] 設計判断があれば `docs/ai-lessons/DECISION_HISTORY.md` に追記した
- [ ] 再発防止ルールが必要なら `.claude/rules/10-known-mistakes.md` に KM-XXXX として昇格した

## New Lessons Learned

<!-- 今回の作業で新たな教訓があれば記載。なければ「なし」 -->

- なし

## Related Issues / PRs

<!-- 関連する issue や PR があれば -->
