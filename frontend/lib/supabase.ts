/**
 * Server-side data fetching helpers (SSR / Route Handlers).
 * Browser-side Realtime は lib/supabase/browser.ts の getBrowserClient() を使うこと。
 */
import { createServerClient } from './supabase/server'

export async function fetchTopics(options: {
  category?: string
  limit?: number
  offset?: number
}) {
  const db = createServerClient()
  let query = db
    .from('topics')
    .select('id, title_ja, title_en, summary_ja, summary_en, category, is_breaking, importance_score, published_at, updated_at')
    .eq('status', 'published')
    .order('published_at', { ascending: false })
    .limit(options.limit ?? 50)

  if (options.category && options.category !== 'all') {
    query = query.eq('category', options.category)
  }
  if (options.offset) {
    query = query.range(options.offset, options.offset + (options.limit ?? 50) - 1)
  }

  const { data, error } = await query
  if (error) throw error
  return data
}

export async function fetchTopicDetail(id: string) {
  const db = createServerClient()
  const { data, error } = await db
    .from('topics')
    .select('*, topic_sources(*)')
    .eq('id', id)
    .eq('status', 'published')
    .single()
  if (error) throw error
  return data
}

export async function fetchLatestSummary(periodType: '6h' | '24h') {
  const db = createServerClient()
  const { data, error } = await db
    .from('summaries')
    .select('*')
    .eq('period_type', periodType)
    .order('created_at', { ascending: false })
    .limit(1)
    .maybeSingle()
  if (error) throw error
  return data
}
