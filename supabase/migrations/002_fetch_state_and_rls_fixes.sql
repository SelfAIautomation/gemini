-- ============================================================
-- Migration 002: ETag永続化 / RLS修正 / Realtimeパブリケーション修正
-- ============================================================

-- ETag / Last-Modified の永続化テーブル
-- source_registry は設定値、こちらは実行時状態を管理する
CREATE TABLE source_fetch_state (
  source_id       UUID NOT NULL REFERENCES source_registry(id) ON DELETE CASCADE,
  url             TEXT NOT NULL,
  etag            TEXT,
  last_modified   TEXT,
  content_hash    TEXT,
  last_checked_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  PRIMARY KEY (source_id, url)
);

ALTER TABLE source_fetch_state ENABLE ROW LEVEL SECURITY;

CREATE POLICY "source_fetch_state_service_only" ON source_fetch_state
  FOR ALL TO service_role USING (true);

-- fetch_logs の 1時間クエリ用インデックス
CREATE INDEX idx_fetch_logs_domain_fetched ON fetch_logs(domain, fetched_at DESC);

-- topic_events: published トピックのみ anon に公開
-- 旧ポリシー (USING (true)) を差し替え
DROP POLICY IF EXISTS "topic_events_public_read" ON topic_events;

CREATE POLICY "topic_events_public_read" ON topic_events
  FOR SELECT TO anon USING (
    EXISTS (
      SELECT 1
      FROM topics t
      WHERE t.id = topic_events.topic_id
        AND t.status = 'published'
    )
  );

-- Realtimeパブリケーション: DROP/CREATE はせず ADD TABLE で安全に追加
-- 既存の publication に追加するため、存在しない場合のみ CREATE する
DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM pg_publication WHERE pubname = 'supabase_realtime'
  ) THEN
    CREATE PUBLICATION supabase_realtime FOR TABLE topics, topic_events;
  ELSE
    -- 既存 publication に topics と topic_events を追加（既追加でもエラーにならない）
    BEGIN
      ALTER PUBLICATION supabase_realtime ADD TABLE topics;
    EXCEPTION WHEN duplicate_object THEN NULL;
    END;
    BEGIN
      ALTER PUBLICATION supabase_realtime ADD TABLE topic_events;
    EXCEPTION WHEN duplicate_object THEN NULL;
    END;
  END IF;
END $$;
