'use client'
import type { Category } from '@/types'

const CATEGORIES: { key: string; label: string }[] = [
  { key: 'all', label: 'ALL' },
  { key: 'breaking', label: '速報' },
  { key: 'crypto', label: 'Crypto' },
  { key: 'macro', label: 'Macro' },
  { key: 'gov', label: 'Gov' },
  { key: 'summary', label: 'まとめ' },
]

interface Props {
  active: string
  onChange: (cat: string) => void
}

export default function CategoryFilter({ active, onChange }: Props) {
  return (
    <div style={{ display: 'flex', gap: '4px', padding: '8px 12px', borderBottom: '1px solid #222' }}>
      {CATEGORIES.map(({ key, label }) => (
        <button
          key={key}
          onClick={() => onChange(key)}
          style={{
            background: active === key ? '#333' : 'transparent',
            color: active === key ? '#e8e8e8' : '#666',
            border: active === key ? '1px solid #555' : '1px solid transparent',
            borderRadius: '3px',
            padding: '2px 8px',
            fontSize: '11px',
            fontFamily: 'monospace',
            cursor: 'pointer',
            letterSpacing: '0.05em',
          }}
        >
          {label}
        </button>
      ))}
    </div>
  )
}
