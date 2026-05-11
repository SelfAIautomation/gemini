-- ============================================================
-- Migration 003: 並列処理対策 / processing フラグ
-- ============================================================

-- raw_articles に処理状態管理カラムを追加
ALTER TABLE raw_articles
  ADD COLUMN processing         BOOLEAN     NOT NULL DEFAULT false,
  ADD COLUMN processing_started_at TIMESTAMPTZ,
  ADD COLUMN processed_at       TIMESTAMPTZ;

-- 未処理キュー用インデックス（処理中は除外）
CREATE INDEX idx_raw_articles_queue
  ON raw_articles(published_at DESC)
  WHERE processed = false AND processing = false;

-- ============================================================
-- Atomic claim: FOR UPDATE SKIP LOCKED でレース条件を防ぐ
-- 複数 Processor が同時に起動しても同じ記事を重複処理しない
-- ============================================================
CREATE OR REPLACE FUNCTION claim_raw_articles(batch_size INT)
RETURNS SETOF raw_articles
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
BEGIN
  RETURN QUERY
    UPDATE raw_articles
    SET
      processing             = true,
      processing_started_at  = now()
    WHERE id IN (
      SELECT id
      FROM raw_articles
      WHERE processed  = false
        AND processing = false
      ORDER BY published_at DESC NULLS LAST
      LIMIT batch_size
      FOR UPDATE SKIP LOCKED
    )
    RETURNING *;
END;
$$;

-- ============================================================
-- Stale claim 解放: 10分以上 processing=true のまま残った記事を戻す
-- Cloud Runが途中で落ちた場合の救済
-- ============================================================
CREATE OR REPLACE FUNCTION release_stale_claims()
RETURNS integer
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
DECLARE
  released integer;
BEGIN
  WITH released_rows AS (
    UPDATE raw_articles
    SET
      processing             = false,
      processing_started_at  = NULL
    WHERE processing = true
      AND processed  = false
      AND processing_started_at < now() - INTERVAL '10 minutes'
    RETURNING id
  )
  SELECT count(*) INTO released FROM released_rows;
  RETURN released;
END;
$$;

-- RPC は service_role のみ実行可能
REVOKE ALL ON FUNCTION claim_raw_articles(INT) FROM PUBLIC;
REVOKE ALL ON FUNCTION release_stale_claims()  FROM PUBLIC;
GRANT EXECUTE ON FUNCTION claim_raw_articles(INT) TO service_role;
GRANT EXECUTE ON FUNCTION release_stale_claims()  TO service_role;
