export type Category = 'crypto' | 'macro' | 'gov' | 'breaking' | 'summary'
export type TopicStatus = 'draft' | 'published' | 'archived'
export type Lang = 'ja' | 'en'

export interface Topic {
  id: string
  title_ja: string
  title_en: string | null
  body_ja: string
  body_en: string | null
  summary_ja: string | null
  summary_en: string | null
  category: Category
  status: TopicStatus
  is_breaking: boolean
  importance_score: number
  published_at: string
  updated_at: string
}

export interface TopicSource {
  id: string
  topic_id: string
  source_name: string
  source_url: string
  source_type: string
  posted_at: string | null
}

export interface TopicDetail extends Topic {
  topic_sources: TopicSource[]
}

export interface Summary {
  id: string
  period_type: '6h' | '24h' | 'weekly'
  body_ja: string
  body_en: string | null
  slide_url: string | null
  created_at: string
}

export interface TopicEvent {
  id: string
  topic_id: string
  event_type: 'created' | 'updated' | 'breaking' | 'archived'
  new_value: Record<string, unknown>
  created_at: string
}
