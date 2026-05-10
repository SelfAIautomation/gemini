'use client'
import { useRef, useEffect } from 'react'

interface Props {
  value: string
  onChange: (v: string) => void
  onClose: () => void
}

export default function SearchBar({ value, onChange, onClose }: Props) {
  const ref = useRef<HTMLInputElement>(null)
  useEffect(() => { ref.current?.focus() }, [])

  return (
    <div style={{
      padding: '8px 12px',
      borderBottom: '1px solid #333',
      display: 'flex', alignItems: 'center', gap: '8px',
    }}>
      <span style={{ color: '#666', fontFamily: 'monospace', fontSize: '13px' }}>/</span>
      <input
        ref={ref}
        value={value}
        onChange={(e) => onChange(e.target.value)}
        onKeyDown={(e) => { if (e.key === 'Escape') onClose() }}
        placeholder="検索..."
        style={{
          background: 'transparent',
          border: 'none',
          outline: 'none',
          color: '#e8e8e8',
          fontFamily: 'monospace',
          fontSize: '13px',
          flex: 1,
        }}
      />
      <button
        onClick={onClose}
        style={{ background: 'none', border: 'none', color: '#555', cursor: 'pointer', fontSize: '12px' }}
      >
        ESC
      </button>
    </div>
  )
}
