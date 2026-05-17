import { notFound } from 'next/navigation'
import { fetchTopicDetail } from '@/lib/supabase'
import type { TopicDetail, Lang } from '@/types'
import TopicDetailClient from './TopicDetailClient'

interface Props {
  params: { id: string }
  searchParams: { lang?: string }
}

export default async function TopicPage({ params, searchParams }: Props) {
  let topic: TopicDetail
  try {
    topic = (await fetchTopicDetail(params.id)) as TopicDetail
  } catch {
    notFound()
  }

  const lang: Lang = searchParams.lang === 'en' ? 'en' : 'ja'
  return <TopicDetailClient topic={topic} initialLang={lang} />
}

export async function generateMetadata({ params }: Props) {
  try {
    const topic = (await fetchTopicDetail(params.id)) as TopicDetail
    return {
      title: `${topic.title_ja} | CB Terminal`,
      description: topic.summary_ja ?? topic.title_ja,
    }
  } catch {
    return { title: 'CB Terminal' }
  }
}
