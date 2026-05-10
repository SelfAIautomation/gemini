import { fetchTopics } from '@/lib/supabase'
import TopicTerminal from './TopicTerminal'
import type { Topic } from '@/types'

export const revalidate = 60

export default async function HomePage() {
  let initialTopics: Topic[] = []
  try {
    initialTopics = (await fetchTopics({ limit: 100 })) as Topic[]
  } catch {
    // Supabase未設定時はサンプルデータで表示
    initialTopics = SAMPLE_TOPICS
  }

  return <TopicTerminal initialTopics={initialTopics} />
}

const SAMPLE_TOPICS: Topic[] = [
  {
    id: '1', title_ja: 'BTCが $100k を突破、機関投資家の買いが加速',
    title_en: 'BTC breaks $100k as institutional buying accelerates',
    body_ja: '本文', body_en: 'Body',
    summary_ja: '機関投資家の継続的な買いにより BTC が $100,000 を突破した。',
    summary_en: 'BTC breaks $100k on institutional demand.',
    category: 'crypto', status: 'published', is_breaking: true,
    importance_score: 0.95, published_at: new Date().toISOString(), updated_at: new Date().toISOString(),
  },
  {
    id: '2', title_ja: 'FRB、金利据え置きを決定 ─ インフレ動向を注視',
    title_en: 'Fed holds rates steady, monitors inflation data',
    body_ja: '本文', body_en: 'Body',
    summary_ja: 'FRBは政策金利を5.25-5.50%に据え置いた。',
    summary_en: 'Fed holds rates at 5.25-5.50%.',
    category: 'macro', status: 'published', is_breaking: false,
    importance_score: 0.85, published_at: new Date(Date.now() - 3600000).toISOString(), updated_at: new Date().toISOString(),
  },
  {
    id: '3', title_ja: 'SEC、イーサリアムスポットETFを承認',
    title_en: 'SEC approves Ethereum spot ETF applications',
    body_ja: '本文', body_en: 'Body',
    summary_ja: 'SECが複数のイーサリアムスポットETFを承認した。',
    summary_en: 'SEC approves multiple Ethereum spot ETFs.',
    category: 'gov', status: 'published', is_breaking: false,
    importance_score: 0.90, published_at: new Date(Date.now() - 7200000).toISOString(), updated_at: new Date().toISOString(),
  },
]
