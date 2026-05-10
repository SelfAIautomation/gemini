'use client'
import { useEffect } from 'react'

export interface KeyboardHandlers {
  onNext?: () => void       // j
  onPrev?: () => void       // k
  onTop?: () => void        // g
  onOpen?: () => void       // Enter / o
  onSearch?: () => void     // /
  onHelp?: () => void       // h
  onEscape?: () => void     // Escape
  onLangToggle?: () => void // l
}

export function useKeyboard(handlers: KeyboardHandlers) {
  useEffect(() => {
    const onKeyDown = (e: KeyboardEvent) => {
      const tag = (e.target as HTMLElement).tagName
      const isInput = tag === 'INPUT' || tag === 'TEXTAREA'

      if (e.key === 'Escape') { handlers.onEscape?.(); return }
      if (e.key === '/' && !isInput) { e.preventDefault(); handlers.onSearch?.(); return }
      if (isInput) return

      switch (e.key) {
        case 'j': handlers.onNext?.(); break
        case 'k': handlers.onPrev?.(); break
        case 'g': handlers.onTop?.(); break
        case 'o':
        case 'Enter': handlers.onOpen?.(); break
        case 'h': handlers.onHelp?.(); break
        case 'l': handlers.onLangToggle?.(); break
      }
    }
    window.addEventListener('keydown', onKeyDown)
    return () => window.removeEventListener('keydown', onKeyDown)
  }, [handlers])
}
