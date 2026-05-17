import { createClient } from '@supabase/supabase-js'

function getEnv() {
  const url = process.env.NEXT_PUBLIC_SUPABASE_URL
  const key = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY
  if (!url || !key) {
    throw new Error(
      'Supabase environment variables are not configured. ' +
      'Set NEXT_PUBLIC_SUPABASE_URL and NEXT_PUBLIC_SUPABASE_ANON_KEY.'
    )
  }
  return { url, key }
}

export function createServerClient() {
  const { url, key } = getEnv()
  return createClient(url, key, {
    auth: { persistSession: false },
  })
}
