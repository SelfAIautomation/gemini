import { createClient } from '@supabase/supabase-js'

const url = process.env.NEXT_PUBLIC_SUPABASE_URL!
const anonKey = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!

export const supabase = createClient(url, anonKey)

export async function fetchTopics(options: {
  category?: string
  limit?: number
  offset?: number
  lang?: 'ja' | 'en'
}) {
  let query = supabase
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
  const { data, error } = await supabase
    .from('topics')
    .select('*, topic_sources(*)')
    .eq('id', id)
    .eq('status', 'published')
    .single()
  if (error) throw error
  return data
}

export async function fetchLatestSummary(periodType: '6h' | '24h') {
  const { data, error } = await supabase
    .from('summaries')
    .select('*')
    .eq('period_type', periodType)
    .order('created_at', { ascending: false })
    .limit(1)
    .single()
  if (error && error.code !== 'PGRST116') throw error
  return data
}
