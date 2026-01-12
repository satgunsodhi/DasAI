import { createClient } from '@/lib/supabase/server'
import { redirect } from 'next/navigation'
import DashboardClient from './DashboardClient'

export default async function DashboardPage() {
  const supabase = await createClient()
  
  const { data: { user } } = await supabase.auth.getUser()
  
  if (!user) {
    redirect('/login')
  }

  // Fetch bot config
  const { data: config } = await supabase
    .from('bot_config')
    .select('*')
    .single()

  // Fetch conversation memories
  const { data: memories } = await supabase
    .from('conversation_memory')
    .select('*')
    .order('updated_at', { ascending: false })
    .limit(10)

  return (
    <DashboardClient 
      user={user} 
      initialConfig={config} 
      initialMemories={memories || []} 
    />
  )
}
