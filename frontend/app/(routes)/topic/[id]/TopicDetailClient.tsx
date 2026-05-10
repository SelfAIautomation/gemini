'use client'
import { useState } from 'react'
import { useRouter } from 'next/navigation'
import type { TopicDetail, Lang } from '@/types'
import { useKeyboard } from '@/hooks/useKeyboard'

const CATEGORY_COLOR: Record<string, string> = {
  crypto: '#00ff88', macro: '#ffaa00', gov: '#4488ff',
  breaking: '#ff4444', summary: '#aa88ff',
}

interface Props {
  topic: TopicDetail
  initialLang: Lang
}

export default function TopicDetailClient({ topic, initialLang }: Props) {
  const router = useRouter()
  const [lang, setLang] = useState<Lang>(initialLang)

  useKeyboard({
    onEscape: () => router.back(),
    onLangToggle: () => setLang(l => l === 'ja' ? 'en' : 'ja'),
  })

  const title = lang === 'ja' ? topic.title_ja : (topic.title_en ?? topic.title_ja)
  const body = lang === 'ja' ? topic.body_ja : (topic.body_en ?? topic.body_ja)
  const summary = lang === 'ja' ? topic.summary_ja : (topic.summary_en ?? topic.summary_ja)
  const color = CATEGORY_COLOR[topic.category] ?? '#888'
  const pubDate = new Date(topic.published_at).toLocaleString('ja-JP')
  const updDate = new Date(topic.updated_at).toLocaleString('ja-JP')

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100vh' }}>
      {/* Header */}
      <div style={{
        padding: '8px 16px', borderBottom: '1px solid #222',
        display: 'flex', alignItems: 'center', gap: '12px', background: '#0d0d0d',
      }}>
        <button
          onClick={() => router.back()}
          style={{ background: 'none', border: 'none', color: '#555', cursor: 'pointer', fontSize: '13px' }}
        >
          ← BACK
        </button>
        <span style={{ color: '#444', fontSize: '11px' }}>Esc で戻る</span>
        <div style={{ flex: 1 }} />
        <button
          onClick={() => setLang(l => l === 'ja' ? 'en' : 'ja')}
          style={{
            background: '#1a1a1a', border: '1px solid #333', color: '#888',
            borderRadius: '3px', padding: '2px 8px', fontSize: '11px', cursor: 'pointer',
          }}
        >
          {lang.toUpperCase()}
        </button>
      </div>

      <div style={{ flex: 1, overflowY: 'auto', padding: '24px 32px', maxWidth: '760px', margin: '0 auto', width: '100%' }}>
        {/* Meta */}
        <div style={{ display: 'flex', gap: '8px', alignItems: 'center', marginBottom: '12px' }}>
          <span style={{
            color, background: `${color}22`, border: `1px solid ${color}44`,
            padding: '2px 8px', borderRadius: '3px', fontSize: '11px', fontWeight: 700,
          }}>
            {topic.is_breaking ? '⚡ 速報' : topic.category.toUpperCase()}
          </span>
          <span style={{ color: '#555', fontSize: '11px' }}>{pubDate}</span>
          {topic.updated_at !== topic.published_at && (
            <span style={{ color: '#444', fontSize: '11px' }}>更新: {updDate}</span>
          )}
        </div>

        {/* Title */}
        <h1 style={{ color: '#e8e8e8', fontSize: '20px', fontWeight: 600, lineHeight: 1.4, marginBottom: '16px' }}>
          {title}
        </h1>

        {/* AI Summary */}
        {summary && (
          <div style={{
            background: '#111', border: '1px solid #2a2a2a',
            borderLeft: `3px solid ${color}`,
            borderRadius: '4px', padding: '12px 16px', marginBottom: '24px',
          }}>
            <div style={{ color: color, fontSize: '10px', fontWeight: 700, letterSpacing: '0.1em', marginBottom: '6px' }}>
              AI SUMMARY
            </div>
            <div style={{ color: '#ccc', fontSize: '13px', lineHeight: 1.6 }}>{summary}</div>
          </div>
        )}

        {/* Body */}
        <div style={{ color: '#bbb', fontSize: '14px', lineHeight: 1.8, whiteSpace: 'pre-wrap', marginBottom: '32px' }}>
          {body}
        </div>

        {/* Sources */}
        {topic.topic_sources?.length > 0 && (
          <div style={{ borderTop: '1px solid #1a1a1a', paddingTop: '20px' }}>
            <div style={{ color: '#555', fontSize: '11px', letterSpacing: '0.1em', marginBottom: '12px' }}>
              SOURCES
            </div>
            {topic.topic_sources.map(src => (
              <div key={src.id} style={{
                display: 'flex', gap: '8px', alignItems: 'baseline',
                marginBottom: '8px', fontSize: '12px',
              }}>
                <span style={{
                  color: '#555', background: '#1a1a1a',
                  padding: '1px 6px', borderRadius: '3px',
                  minWidth: '60px', textAlign: 'center', fontSize: '10px',
                }}>
                  {src.source_type.toUpperCase()}
                </span>
                <a
                  href={src.source_url}
                  target="_blank"
                  rel="noopener noreferrer"
                  style={{ color: '#4488ff' }}
                >
                  {src.source_name}
                </a>
                {src.posted_at && (
                  <span style={{ color: '#444', fontSize: '11px' }}>
                    {new Date(src.posted_at).toLocaleString('ja-JP')}
                  </span>
                )}
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  )
}
