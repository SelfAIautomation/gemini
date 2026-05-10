'use client'
import { useState, useCallback, useRef, useMemo, useEffect } from 'react'
import { useRouter } from 'next/navigation'
import type { Topic, Lang } from '@/types'
import { useTopicsRealtime, useUnreadTopics } from '@/hooks/useRealtime'
import { useKeyboard } from '@/hooks/useKeyboard'
import TopicRow from '@/components/TopicRow'
import CategoryFilter from '@/components/CategoryFilter'
import SearchBar from '@/components/SearchBar'
import HelpOverlay from '@/components/HelpOverlay'

interface Props {
  initialTopics: Topic[]
}

export default function TopicTerminal({ initialTopics }: Props) {
  const router = useRouter()
  const [topics, setTopics] = useState<Topic[]>(initialTopics)
  const [selectedIdx, setSelectedIdx] = useState(0)
  const [category, setCategory] = useState('all')
  const [lang, setLang] = useState<Lang>('ja')
  const [search, setSearch] = useState('')
  const [showSearch, setShowSearch] = useState(false)
  const [showHelp, setShowHelp] = useState(false)
  const [newCount, setNewCount] = useState(0)
  const listRef = useRef<HTMLDivElement>(null)
  const { markRead, isUnread } = useUnreadTopics()

  const filtered = useMemo(() => {
    let list = topics
    if (category !== 'all') list = list.filter(t => t.category === category)
    if (search) {
      const q = search.toLowerCase()
      list = list.filter(t =>
        t.title_ja.toLowerCase().includes(q) ||
        (t.title_en?.toLowerCase().includes(q)) ||
        (t.summary_ja?.toLowerCase().includes(q))
      )
    }
    return list
  }, [topics, category, search])

  const onInsert = useCallback((topic: Topic) => {
    setTopics(prev => [topic, ...prev])
    setNewCount(c => c + 1)
  }, [])

  const onUpdate = useCallback((updated: Topic) => {
    setTopics(prev => prev.map(t => t.id === updated.id ? updated : t))
  }, [])

  useTopicsRealtime(onInsert, onUpdate)

  const openSelected = useCallback(() => {
    const topic = filtered[selectedIdx]
    if (topic) {
      markRead(topic.id)
      router.push(`/topic/${topic.id}`)
    }
  }, [filtered, selectedIdx, markRead, router])

  useKeyboard({
    onNext: () => setSelectedIdx(i => Math.min(i + 1, filtered.length - 1)),
    onPrev: () => setSelectedIdx(i => Math.max(i - 1, 0)),
    onTop: () => setSelectedIdx(0),
    onOpen: openSelected,
    onSearch: () => setShowSearch(true),
    onHelp: () => setShowHelp(v => !v),
    onLangToggle: () => setLang(l => l === 'ja' ? 'en' : 'ja'),
    onEscape: () => { setShowSearch(false); setShowHelp(false); setSearch('') },
  })

  // 選択行を常にスクロール内に収める
  useEffect(() => {
    const list = listRef.current
    if (!list) return
    const rows = list.querySelectorAll('[data-topic-row]')
    rows[selectedIdx]?.scrollIntoView({ block: 'nearest' })
  }, [selectedIdx])

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100vh' }}>
      {/* Header */}
      <div style={{
        display: 'flex', alignItems: 'center', justifyContent: 'space-between',
        padding: '8px 12px', borderBottom: '1px solid #222',
        background: '#0d0d0d',
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
          <span style={{ color: '#00ff88', fontWeight: 700, letterSpacing: '0.1em' }}>CB TERMINAL</span>
          {newCount > 0 && (
            <span
              style={{
                background: '#ff4444', color: '#fff',
                fontSize: '10px', padding: '1px 6px', borderRadius: '10px',
                cursor: 'pointer',
              }}
              onClick={() => { setNewCount(0); setSelectedIdx(0) }}
            >
              +{newCount} NEW
            </span>
          )}
        </div>
        <div style={{ display: 'flex', gap: '8px', alignItems: 'center' }}>
          <button
            onClick={() => setLang(l => l === 'ja' ? 'en' : 'ja')}
            style={{
              background: '#1a1a1a', border: '1px solid #333',
              color: '#888', borderRadius: '3px', padding: '2px 8px',
              fontSize: '11px', cursor: 'pointer',
            }}
          >
            {lang.toUpperCase()}
          </button>
          <span style={{ color: '#444', fontSize: '11px' }}>[h] help</span>
        </div>
      </div>

      <CategoryFilter active={category} onChange={(c) => { setCategory(c); setSelectedIdx(0) }} />

      {showSearch && (
        <SearchBar
          value={search}
          onChange={(v) => { setSearch(v); setSelectedIdx(0) }}
          onClose={() => { setShowSearch(false); setSearch('') }}
        />
      )}

      {/* Topic List */}
      <div ref={listRef} style={{ flex: 1, overflowY: 'auto' }}>
        {filtered.length === 0 ? (
          <div style={{ padding: '24px', color: '#555', textAlign: 'center' }}>
            {search ? `"${search}" に一致する記事はありません` : '記事がありません'}
          </div>
        ) : (
          filtered.map((topic, i) => (
            <div key={topic.id} data-topic-row="">
              <TopicRow
                topic={topic}
                isSelected={i === selectedIdx}
                isUnread={isUnread(topic.id)}
                lang={lang}
                onClick={() => {
                  setSelectedIdx(i)
                  markRead(topic.id)
                  router.push(`/topic/${topic.id}`)
                }}
              />
            </div>
          ))
        )}
      </div>

      {/* Status Bar */}
      <div style={{
        padding: '4px 12px', borderTop: '1px solid #1a1a1a',
        background: '#0d0d0d', display: 'flex', gap: '16px',
        color: '#444', fontSize: '11px',
      }}>
        <span>{selectedIdx + 1}/{filtered.length}</span>
        <span>j/k 移動</span>
        <span>Enter 開く</span>
        <span>/ 検索</span>
        <span>h ヘルプ</span>
      </div>

      {showHelp && <HelpOverlay onClose={() => setShowHelp(false)} />}
    </div>
  )
}
