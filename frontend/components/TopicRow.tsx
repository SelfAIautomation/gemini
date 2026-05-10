'use client'
import type { Topic, Lang } from '@/types'

const CATEGORY_LABEL: Record<string, string> = {
  crypto: 'CRYPTO',
  macro: 'MACRO',
  gov: 'GOV',
  breaking: '速報',
  summary: 'まとめ',
}

const CATEGORY_COLOR: Record<string, string> = {
  crypto: '#00ff88',
  macro: '#ffaa00',
  gov: '#4488ff',
  breaking: '#ff4444',
  summary: '#aa88ff',
}

interface Props {
  topic: Topic
  isSelected: boolean
  isUnread: boolean
  lang: Lang
  onClick: () => void
}

export default function TopicRow({ topic, isSelected, isUnread, lang, onClick }: Props) {
  const title = lang === 'ja' ? topic.title_ja : (topic.title_en ?? topic.title_ja)
  const summary = lang === 'ja' ? topic.summary_ja : (topic.summary_en ?? topic.summary_ja)
  const color = CATEGORY_COLOR[topic.category] ?? '#888'
  const label = CATEGORY_LABEL[topic.category] ?? topic.category.toUpperCase()
  const time = new Date(topic.published_at).toLocaleTimeString('ja-JP', {
    hour: '2-digit', minute: '2-digit'
  })

  return (
    <div
      onClick={onClick}
      style={{
        padding: '6px 12px',
        cursor: 'pointer',
        borderLeft: isSelected ? `3px solid ${color}` : '3px solid transparent',
        background: isSelected ? 'rgba(255,255,255,0.04)' : 'transparent',
        display: 'grid',
        gridTemplateColumns: '52px 70px 1fr',
        gap: '8px',
        alignItems: 'start',
        borderBottom: '1px solid rgba(255,255,255,0.04)',
      }}
    >
      <span style={{ color: '#555', fontFamily: 'monospace', fontSize: '12px', paddingTop: '1px' }}>
        {time}
      </span>
      <span style={{
        color,
        fontFamily: 'monospace',
        fontSize: '11px',
        fontWeight: 700,
        paddingTop: '1px',
        letterSpacing: '0.05em',
      }}>
        {topic.is_breaking ? '⚡ 速報' : label}
      </span>
      <div>
        <div style={{
          color: isUnread ? '#e8e8e8' : '#888',
          fontSize: '13px',
          lineHeight: 1.4,
          fontWeight: isUnread ? 500 : 400,
        }}>
          {title}
        </div>
        {summary && (
          <div style={{ color: '#666', fontSize: '11px', marginTop: '2px', lineHeight: 1.3 }}>
            {summary}
          </div>
        )}
      </div>
    </div>
  )
}
