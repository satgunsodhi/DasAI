import { createClient } from '@/lib/supabase/server'
import { redirect } from 'next/navigation'
import DashboardClient from './DashboardClient'

export default async function DashboardPage() {
  const supabase = await createClient()
  
  const { data: { user } } = await supabase.auth.getUser()
  
  if (!user) {
    redirect('/login')
  }

  // Fetch all guild configs (for guild selector)
  const { data: guilds } = await supabase
    .from('bot_config')
    .select('guild_id, guild_name, id')
    .order('guild_name', { ascending: true })

  // Fetch bot config for first guild (or null if none)
  const { data: config } = await supabase
    .from('bot_config')
    .select('*')
    .limit(1)
    .single()

  const selectedGuildId = config?.guild_id || ''

  // Fetch conversation memories for selected guild
  const { data: memories } = await supabase
    .from('conversation_memory')
    .select('*')
    .eq('guild_id', selectedGuildId)
    .order('updated_at', { ascending: false })
    .limit(10)

  // Fetch user roles for selected guild
  const { data: userRoles } = await supabase
    .from('user_roles')
    .select('*')
    .eq('guild_id', selectedGuildId)
    .order('created_at', { ascending: true })

  return (
    <DashboardClient 
      user={user} 
      initialConfig={config} 
      initialMemories={memories || []} 
      initialUserRoles={userRoles || []}
      guilds={guilds || []}
      selectedGuildId={selectedGuildId}
    />
  )
}
