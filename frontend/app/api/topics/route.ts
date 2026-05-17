import { NextRequest, NextResponse } from 'next/server'
import { fetchTopics } from '@/lib/supabase'

export const dynamic = 'force-dynamic'

const RATE_LIMIT = new Map<string, { count: number; reset: number }>()

function checkRateLimit(ip: string): boolean {
  const now = Date.now()
  const window = 60_000
  const max = 30
  const entry = RATE_LIMIT.get(ip)
  if (!entry || entry.reset < now) {
    RATE_LIMIT.set(ip, { count: 1, reset: now + window })
    return true
  }
  if (entry.count >= max) return false
  entry.count++
  return true
}

export async function GET(req: NextRequest) {
  const ip = req.headers.get('x-forwarded-for')?.split(',')[0] ?? 'unknown'
  if (!checkRateLimit(ip)) {
    return NextResponse.json({ error: 'rate_limit' }, {
      status: 429,
      headers: { 'Retry-After': '60' },
    })
  }

  const { searchParams } = req.nextUrl
  const category = searchParams.get('category') ?? undefined
  const limit = Math.min(Number(searchParams.get('limit') ?? 50), 100)
  const offset = Number(searchParams.get('offset') ?? 0)

  try {
    const topics = await fetchTopics({ category, limit, offset })
    return NextResponse.json({ topics }, {
      headers: { 'Cache-Control': 'public, s-maxage=30, stale-while-revalidate=60' }
    })
  } catch (err) {
    return NextResponse.json({ error: 'internal_error' }, { status: 500 })
  }
}
