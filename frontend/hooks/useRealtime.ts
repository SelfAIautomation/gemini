'use client'
import { useEffect, useCallback } from 'react'
import { getBrowserClient } from '@/lib/supabase/browser'
import type { Topic } from '@/types'

export function useTopicsRealtime(
  onInsert: (topic: Topic) => void,
  onUpdate: (topic: Topic) => void,
) {
  useEffect(() => {
    const supabase = getBrowserClient()
    const channel = supabase
      .channel('topics-realtime')
      .on(
        'postgres_changes',
        { event: 'INSERT', schema: 'public', table: 'topics', filter: 'status=eq.published' },
        (payload) => onInsert(payload.new as Topic),
      )
      .on(
        'postgres_changes',
        { event: 'UPDATE', schema: 'public', table: 'topics', filter: 'status=eq.published' },
        (payload) => onUpdate(payload.new as Topic),
      )
      .subscribe()

    return () => { supabase.removeChannel(channel) }
  }, [onInsert, onUpdate])
}

export function useUnreadTopics() {
  const STORAGE_KEY = 'cb_read_topics'

  const getRead = useCallback((): Set<string> => {
    if (typeof window === 'undefined') return new Set()
    try {
      const raw = localStorage.getItem(STORAGE_KEY)
      return raw ? new Set(JSON.parse(raw)) : new Set()
    } catch {
      return new Set()
    }
  }, [])

  const markRead = useCallback((id: string) => {
    const read = getRead()
    read.add(id)
    const arr = Array.from(read).slice(-1000)
    localStorage.setItem(STORAGE_KEY, JSON.stringify(arr))
  }, [getRead])

  const isUnread = useCallback((id: string): boolean => {
    return !getRead().has(id)
  }, [getRead])

  return { markRead, isUnread }
}
