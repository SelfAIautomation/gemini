'use client'

const SHORTCUTS = [
  { key: 'j / k', desc: '次/前の記事' },
  { key: 'g', desc: '先頭に戻る' },
  { key: 'Enter / o', desc: '記事を開く' },
  { key: '/', desc: '検索' },
  { key: 'l', desc: '言語切り替え (JA/EN)' },
  { key: 'h', desc: 'ヘルプを開閉' },
  { key: 'Esc', desc: '閉じる' },
]

interface Props {
  onClose: () => void
}

export default function HelpOverlay({ onClose }: Props) {
  return (
    <div
      onClick={onClose}
      style={{
        position: 'fixed', inset: 0,
        background: 'rgba(0,0,0,0.7)',
        display: 'flex', alignItems: 'center', justifyContent: 'center',
        zIndex: 100,
      }}
    >
      <div
        onClick={(e) => e.stopPropagation()}
        style={{
          background: '#111', border: '1px solid #333',
          borderRadius: '6px', padding: '24px',
          minWidth: '300px', fontFamily: 'monospace',
        }}
      >
        <div style={{ color: '#888', fontSize: '11px', marginBottom: '16px', letterSpacing: '0.1em' }}>
          KEYBOARD SHORTCUTS
        </div>
        {SHORTCUTS.map(({ key, desc }) => (
          <div key={key} style={{ display: 'flex', gap: '16px', marginBottom: '8px' }}>
            <span style={{
              color: '#00ff88', fontSize: '12px', minWidth: '80px',
              background: '#1a1a1a', padding: '1px 6px', borderRadius: '3px',
            }}>{key}</span>
            <span style={{ color: '#aaa', fontSize: '12px' }}>{desc}</span>
          </div>
        ))}
        <div style={{ marginTop: '16px', color: '#555', fontSize: '11px' }}>
          Press Esc or click outside to close
        </div>
      </div>
    </div>
  )
}
