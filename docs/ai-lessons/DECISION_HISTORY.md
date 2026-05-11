# DECISION_HISTORY.md

重要な設計判断・技術選択の根拠を記録する。
「なぜこの設計にしたか」を残すことで、将来の変更判断を楽にする。

---

## 記録テンプレート

```
### YYYY-MM-DD / DH-XXXX: 判断タイトル

#### 選択肢
何と何で迷ったか。

#### 選んだ方針
何を選んだか。

#### 理由
なぜその選択をしたか。

#### トレードオフ
捨てたものは何か。

#### 再考すべき条件
どうなったら変えるか。
```

---

### 2026-05-11 / DH-0001: ETag 永続化を source_registry ではなく source_fetch_state で管理

#### 選択肢
- A: `source_registry` に `last_etag`, `last_modified` カラムを追加
- B: `source_fetch_state` テーブルを別に作る

#### 選んだ方針
B: 別テーブルに分離

#### 理由
`source_registry` はソースの設定値（URL、カテゴリ、有効無効等）を管理する。
ETag/Last-Modified は実行時の状態（何回か叩いた結果）であり、性質が異なる。
分離することで、設定変更と状態リセットを独立して行える。

#### トレードオフ
テーブルが増えてクエリが増える。JOIN が必要になる。

#### 再考すべき条件
ソース数が増えてクエリが問題になった場合。

---

### 2026-05-11 / DH-0002: 並列処理対策に FOR UPDATE SKIP LOCKED を採用

#### 選択肢
- A: 処理中フラグ（processing=true）だけ立てて SELECT/UPDATE を分ける
- B: PostgreSQL の FOR UPDATE SKIP LOCKED でアトミックに行をロック
- C: 別途ロックテーブルを作る

#### 選んだ方針
B: FOR UPDATE SKIP LOCKED（`claim_raw_articles` RPC）

#### 理由
PostgreSQL の FOR UPDATE SKIP LOCKED は並列キュー処理のための標準パターン。
SELECT してから UPDATE する方法は TOCTOU race condition が発生する。
RPC 関数にすることで、Supabase クライアントのクエリ制約（RETURNING + LIMIT 等）を回避できる。

#### トレードオフ
RPC 関数をDBに追加する必要がある。migration が増える。

#### 再考すべき条件
Supabase からバックエンドを移行する場合。

---

### 2026-05-11 / DH-0003: Gemini Pro と Flash を用途で使い分け

#### 選択肢
- A: 全処理を Pro モデルで行う
- B: 用途別に Pro / Flash を使い分ける

#### 選んだ方針
B: 用途別使い分け

#### 理由
トピック抽出・要約（精度重視）→ Pro
翻訳（速度・コスト重視）→ Flash
コストと精度のバランスを取る。

#### トレードオフ
モデル管理が複雑になる。モデル名が変わった場合に両方を更新する必要がある。

#### 再考すべき条件
Flash の精度が Pro と同等になった場合、全処理を Flash に移行する。
