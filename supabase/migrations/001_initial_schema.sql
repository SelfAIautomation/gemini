-- ============================================================
-- CB Terminal: Initial Schema
-- ============================================================

-- ニュースソース管理
CREATE TABLE source_registry (
  id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  source_name     TEXT NOT NULL,
  source_type     TEXT NOT NULL CHECK (source_type IN ('api', 'rss', 'html', 'manual')),
  base_url        TEXT NOT NULL,
  feed_url        TEXT,
  category        TEXT NOT NULL DEFAULT 'crypto',
  allowed         BOOLEAN NOT NULL DEFAULT true,
  terms_checked   BOOLEAN NOT NULL DEFAULT false,
  robots_checked  BOOLEAN NOT NULL DEFAULT false,
  fetch_interval  INTEGER NOT NULL DEFAULT 300,  -- seconds
  reliability_score NUMERIC(3,2) DEFAULT 0.80,
  importance_score  NUMERIC(3,2) DEFAULT 0.50,
  parser_type     TEXT NOT NULL DEFAULT 'rss',
  enabled         BOOLEAN NOT NULL DEFAULT true,
  created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- ドメイン単位のレート制限
CREATE TABLE domain_rules (
  id                      UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  domain                  TEXT NOT NULL UNIQUE,
  crawl_interval_seconds  INTEGER NOT NULL DEFAULT 5,
  max_requests_per_hour   INTEGER NOT NULL DEFAULT 60,
  robots_allowed          BOOLEAN NOT NULL DEFAULT true,
  last_fetched_at         TIMESTAMPTZ,
  last_status_code        INTEGER,
  consecutive_errors      INTEGER NOT NULL DEFAULT 0,
  disabled_reason         TEXT,
  enabled                 BOOLEAN NOT NULL DEFAULT true,
  updated_at              TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- 取得ログ
CREATE TABLE fetch_logs (
  id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  source_id       UUID REFERENCES source_registry(id),
  url             TEXT NOT NULL,
  domain          TEXT NOT NULL,
  status_code     INTEGER,
  fetched_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
  response_bytes  INTEGER,
  content_hash    TEXT,
  error_type      TEXT,
  retry_after     INTEGER,
  user_agent      TEXT,
  duration_ms     INTEGER
);

-- 生記事
CREATE TABLE raw_articles (
  id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  source_id       UUID REFERENCES source_registry(id),
  source_url      TEXT NOT NULL UNIQUE,
  source_name     TEXT NOT NULL,
  source_type     TEXT NOT NULL,
  title_raw       TEXT NOT NULL,
  body_raw        TEXT,
  published_at    TIMESTAMPTZ,
  fetched_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
  content_hash    TEXT NOT NULL,
  processed       BOOLEAN NOT NULL DEFAULT false,
  cluster_id      UUID
);

-- トピック (AI編集済み)
CREATE TABLE topics (
  id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  title_ja        TEXT NOT NULL,
  title_en        TEXT,
  body_ja         TEXT NOT NULL,
  body_en         TEXT,
  summary_ja      TEXT,
  summary_en      TEXT,
  category        TEXT NOT NULL DEFAULT 'crypto',
  status          TEXT NOT NULL DEFAULT 'draft' CHECK (status IN ('draft', 'published', 'archived')),
  is_breaking     BOOLEAN NOT NULL DEFAULT false,
  importance_score NUMERIC(3,2) DEFAULT 0.50,
  published_at    TIMESTAMPTZ,
  updated_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
  created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
  source_cluster_id UUID
);

CREATE INDEX idx_topics_published_at ON topics(published_at DESC);
CREATE INDEX idx_topics_category ON topics(category);
CREATE INDEX idx_topics_status ON topics(status);
CREATE INDEX idx_topics_is_breaking ON topics(is_breaking);

-- ソースとトピックの紐付け
CREATE TABLE topic_sources (
  id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  topic_id    UUID NOT NULL REFERENCES topics(id) ON DELETE CASCADE,
  source_name TEXT NOT NULL,
  source_url  TEXT NOT NULL,
  source_type TEXT NOT NULL,
  posted_at   TIMESTAMPTZ,
  raw_text    TEXT,
  created_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_topic_sources_topic_id ON topic_sources(topic_id);

-- トピック更新イベント (Realtime用)
CREATE TABLE topic_events (
  id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  topic_id    UUID NOT NULL REFERENCES topics(id) ON DELETE CASCADE,
  event_type  TEXT NOT NULL CHECK (event_type IN ('created', 'updated', 'breaking', 'archived')),
  old_value   JSONB,
  new_value   JSONB,
  created_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- 定期まとめ記事
CREATE TABLE summaries (
  id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  period_type TEXT NOT NULL CHECK (period_type IN ('6h', '24h', 'weekly')),
  body_ja     TEXT NOT NULL,
  body_en     TEXT,
  slide_url   TEXT,
  topic_ids   UUID[] NOT NULL DEFAULT '{}',
  created_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- AIログ
CREATE TABLE ai_logs (
  id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  job_type        TEXT NOT NULL,
  model           TEXT NOT NULL,
  prompt_version  TEXT,
  input_hash      TEXT,
  output          JSONB,
  cost_usd        NUMERIC(10,6),
  latency_ms      INTEGER,
  trace_url       TEXT,
  success         BOOLEAN NOT NULL DEFAULT true,
  error_message   TEXT,
  created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- ============================================================
-- Row Level Security
-- ============================================================
ALTER TABLE topics ENABLE ROW LEVEL SECURITY;
ALTER TABLE topic_sources ENABLE ROW LEVEL SECURITY;
ALTER TABLE topic_events ENABLE ROW LEVEL SECURITY;
ALTER TABLE summaries ENABLE ROW LEVEL SECURITY;
ALTER TABLE source_registry ENABLE ROW LEVEL SECURITY;
ALTER TABLE domain_rules ENABLE ROW LEVEL SECURITY;
ALTER TABLE fetch_logs ENABLE ROW LEVEL SECURITY;
ALTER TABLE raw_articles ENABLE ROW LEVEL SECURITY;
ALTER TABLE ai_logs ENABLE ROW LEVEL SECURITY;

-- 公開読み取り (topics, topic_sources, topic_events, summaries のみ)
CREATE POLICY "topics_public_read" ON topics
  FOR SELECT TO anon USING (status = 'published');

CREATE POLICY "topic_sources_public_read" ON topic_sources
  FOR SELECT TO anon USING (
    EXISTS (SELECT 1 FROM topics t WHERE t.id = topic_id AND t.status = 'published')
  );

CREATE POLICY "topic_events_public_read" ON topic_events
  FOR SELECT TO anon USING (true);

CREATE POLICY "summaries_public_read" ON summaries
  FOR SELECT TO anon USING (true);

-- 管理系テーブルは service_role のみ
CREATE POLICY "source_registry_service_only" ON source_registry
  FOR ALL TO service_role USING (true);

CREATE POLICY "domain_rules_service_only" ON domain_rules
  FOR ALL TO service_role USING (true);

CREATE POLICY "fetch_logs_service_only" ON fetch_logs
  FOR ALL TO service_role USING (true);

CREATE POLICY "raw_articles_service_only" ON raw_articles
  FOR ALL TO service_role USING (true);

CREATE POLICY "ai_logs_service_only" ON ai_logs
  FOR ALL TO service_role USING (true);

-- topics への書き込みは service_role のみ
CREATE POLICY "topics_service_write" ON topics
  FOR ALL TO service_role USING (true);

CREATE POLICY "topic_sources_service_write" ON topic_sources
  FOR ALL TO service_role USING (true);

CREATE POLICY "topic_events_service_write" ON topic_events
  FOR ALL TO service_role USING (true);

-- NOTE: Realtimeパブリケーションは 002_fetch_state_and_rls_fixes.sql で安全に設定する

-- ============================================================
-- Initial Source Registry
-- ============================================================
INSERT INTO source_registry (source_name, source_type, base_url, feed_url, category, parser_type, fetch_interval, reliability_score, importance_score) VALUES
  ('CoinDesk',         'rss',  'https://www.coindesk.com',        'https://www.coindesk.com/arc/outboundfeeds/rss/',                  'crypto', 'rss', 300, 0.90, 0.80),
  ('CoinTelegraph',    'rss',  'https://cointelegraph.com',        'https://cointelegraph.com/rss',                                   'crypto', 'rss', 300, 0.85, 0.75),
  ('Decrypt',          'rss',  'https://decrypt.co',               'https://decrypt.co/feed',                                        'crypto', 'rss', 300, 0.85, 0.70),
  ('The Block',        'rss',  'https://www.theblock.co',          'https://www.theblock.co/rss.xml',                                'crypto', 'rss', 300, 0.88, 0.75),
  ('Reuters Business', 'rss',  'https://www.reuters.com',          'https://feeds.reuters.com/reuters/businessNews',                  'macro',  'rss', 600, 0.95, 0.85),
  ('Bloomberg Crypto', 'rss',  'https://www.bloomberg.com',        'https://www.bloomberg.com/feeds/podcasts/crypto.xml',            'crypto', 'rss', 600, 0.92, 0.85),
  ('SEC Filings',      'rss',  'https://www.sec.gov',              'https://www.sec.gov/cgi-bin/browse-edgar?action=getcurrent&type=&dateb=&owner=include&count=10&search_text=&output=atom', 'gov', 'rss', 1800, 0.98, 0.90),
  ('Federal Register', 'rss',  'https://www.federalregister.gov',  'https://www.federalregister.gov/documents/current.rss',          'gov',    'rss', 3600, 0.95, 0.80);
