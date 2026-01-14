'use client'

import { useState, useEffect } from 'react'
import { createClient } from '@/lib/supabase/client'
import { useRouter } from 'next/navigation'
import type { User } from '@supabase/supabase-js'
import type { BotConfig, ConversationMemory, UserRole, GuildInfo } from '@/lib/types'
import { 
  Bot, 
  Settings, 
  MessageSquare, 
  Hash, 
  Save, 
  Loader2, 
  LogOut,
  Trash2,
  RefreshCw,
  CheckCircle,
  AlertCircle,
  Users,
  Crown,
  UserIcon,
  Server,
  Sparkles,
  ChevronRight
} from 'lucide-react'

interface Props {
  user: User
  initialConfig: BotConfig | null
  initialMemories: ConversationMemory[]
  initialUserRoles: UserRole[]
  guilds: GuildInfo[]
  selectedGuildId: string
}

export default function DashboardClient({ user, initialConfig, initialMemories, initialUserRoles, guilds, selectedGuildId }: Props) {
  const router = useRouter()
  const supabase = createClient()
  
  // State
  const [activeTab, setActiveTab] = useState<'instructions' | 'channels' | 'memory' | 'roles'>('instructions')
  const [saving, setSaving] = useState(false)
  const [message, setMessage] = useState<{ type: 'success' | 'error', text: string } | null>(null)
  const [currentGuildId, setCurrentGuildId] = useState(selectedGuildId)
  const [config, setConfig] = useState(initialConfig)
  
  // Form state
  const [botName, setBotName] = useState(initialConfig?.bot_name || 'DasAI Assistant')
  const [systemInstructions, setSystemInstructions] = useState(
    initialConfig?.system_instructions || 
    `You are a helpful AI assistant for a Discord server. Be friendly, concise, and helpful.

Key behaviors:
- Answer questions accurately and helpfully
- Be conversational but professional
- If you don't know something, say so
- Keep responses concise unless detail is requested`
  )
  const [allowedChannels, setAllowedChannels] = useState(
    initialConfig?.allowed_channels?.join('\n') || ''
  )
  const [memories, setMemories] = useState(initialMemories)
  const [userRoles, setUserRoles] = useState(initialUserRoles)

  // Load data for selected guild
  const loadGuildData = async (guildId: string) => {
    setSaving(true)
    
    // Fetch config for this guild
    const { data: guildConfig } = await supabase
      .from('bot_config')
      .select('*')
      .eq('guild_id', guildId)
      .single()
    
    if (guildConfig) {
      setConfig(guildConfig)
      setBotName(guildConfig.bot_name || 'DasAI Assistant')
      setSystemInstructions(guildConfig.system_instructions || '')
      setAllowedChannels(guildConfig.allowed_channels?.join('\n') || '')
    }

    // Fetch memories for this guild
    const { data: guildMemories } = await supabase
      .from('conversation_memory')
      .select('*')
      .eq('guild_id', guildId)
      .order('updated_at', { ascending: false })
      .limit(10)
    
    setMemories(guildMemories || [])

    // Fetch roles for this guild
    const { data: guildRoles } = await supabase
      .from('user_roles')
      .select('*')
      .eq('guild_id', guildId)
      .order('created_at', { ascending: true })
    
    setUserRoles(guildRoles || [])
    
    setSaving(false)
  }

  const handleGuildChange = async (guildId: string) => {
    setCurrentGuildId(guildId)
    await loadGuildData(guildId)
  }

  const showMessage = (type: 'success' | 'error', text: string) => {
    setMessage({ type, text })
    setTimeout(() => setMessage(null), 3000)
  }

  const handleSaveConfig = async () => {
    setSaving(true)
    
    const channels = allowedChannels
      .split('\n')
      .map(c => c.trim())
      .filter(c => c.length > 0)

    const configData = {
      bot_name: botName,
      system_instructions: systemInstructions,
      allowed_channels: channels,
      updated_at: new Date().toISOString()
    }

    if (config?.id) {
      // Update existing config
      const { error } = await supabase
        .from('bot_config')
        .update(configData)
        .eq('id', config.id)

      if (error) {
        console.error('Update error:', error)
        showMessage('error', 'Failed to save configuration')
      } else {
        showMessage('success', 'Configuration saved successfully!')
      }
    } else {
      // Insert new config - include required guild_id
      const { error } = await supabase
        .from('bot_config')
        .insert([{ 
          ...configData, 
          id: crypto.randomUUID(),
          guild_id: currentGuildId || 'default',
          guild_name: null
        }])

      if (error) {
        console.error('Insert error:', error)
        showMessage('error', `Failed to create configuration: ${error.message}`)
      } else {
        showMessage('success', 'Configuration created successfully!')
        router.refresh()
      }
    }

    setSaving(false)
  }

  const handleResetMemory = async (channelId?: string) => {
    setSaving(true)

    if (channelId) {
      // Reset specific channel memory
      const { error } = await supabase
        .from('conversation_memory')
        .delete()
        .eq('guild_id', currentGuildId)
        .eq('channel_id', channelId)

      if (!error) {
        setMemories(memories.filter(m => m.channel_id !== channelId))
        showMessage('success', 'Channel memory cleared')
      }
    } else {
      // Reset all memories for this guild
      const { error } = await supabase
        .from('conversation_memory')
        .delete()
        .eq('guild_id', currentGuildId)

      if (!error) {
        setMemories([])
        showMessage('success', 'All conversation memories cleared for this server')
      }
    }

    setSaving(false)
  }

  const handleDeleteRole = async (roleId: string) => {
    setSaving(true)

    const { error } = await supabase
      .from('user_roles')
      .delete()
      .eq('id', roleId)

    if (!error) {
      setUserRoles(userRoles.filter(r => r.id !== roleId))
      showMessage('success', 'User role removed')
    } else {
      showMessage('error', 'Failed to remove role')
    }

    setSaving(false)
  }

  const handleUpdateRole = async (roleId: string, newRole: 'team_lead' | 'member') => {
    setSaving(true)

    const { error } = await supabase
      .from('user_roles')
      .update({ role: newRole })
      .eq('id', roleId)

    if (!error) {
      setUserRoles(userRoles.map(r => r.id === roleId ? { ...r, role: newRole } : r))
      showMessage('success', 'Role updated')
    } else {
      showMessage('error', 'Failed to update role')
    }

    setSaving(false)
  }

  const handleLogout = async () => {
    await supabase.auth.signOut()
    router.push('/login')
    router.refresh()
  }

  return (
    <div className="min-h-screen bg-[#0a0a0a] bg-pattern">
      {/* Header */}
      <header className="sticky top-0 z-40 glass-card border-b border-white/[0.06]">
        <div className="max-w-7xl mx-auto px-6 lg:px-8">
          <div className="flex items-center justify-between h-16">
            <div className="flex items-center gap-4">
              <div className="relative">
                <div className="w-10 h-10 bg-gradient-to-br from-blue-500 to-violet-600 rounded-xl flex items-center justify-center shadow-lg shadow-blue-500/25">
                  <Bot className="w-5 h-5 text-white" />
                </div>
                <div className="absolute -top-1 -right-1 w-3 h-3 bg-emerald-400 rounded-full border-2 border-[#0a0a0a]" />
              </div>
              <div>
                <h1 className="text-lg font-semibold text-white tracking-tight">DasAI</h1>
                <p className="text-xs text-zinc-500">Control Center</p>
              </div>
            </div>
            
            <div className="flex items-center gap-6">
              {/* Guild Selector */}
              {guilds.length > 0 && (
                <div className="flex items-center gap-3 px-3 py-1.5 glass-card rounded-lg">
                  <Server className="w-4 h-4 text-zinc-500" />
                  <select
                    value={currentGuildId}
                    onChange={(e) => handleGuildChange(e.target.value)}
                    className="bg-transparent text-sm text-zinc-300 focus:outline-none cursor-pointer appearance-none pr-6 select-with-chevron"
                    title="Select Discord server"
                    aria-label="Select Discord server"
                  >
                    {guilds.map((guild) => (
                      <option key={guild.guild_id} value={guild.guild_id} className="bg-zinc-900">
                        {guild.guild_name || `Server ${guild.guild_id.slice(0, 8)}...`}
                      </option>
                    ))}
                  </select>
                </div>
              )}
              
              <div className="flex items-center gap-3">
                <span className="text-sm text-zinc-500">{user.email}</span>
                <button
                  onClick={handleLogout}
                  className="p-2 text-zinc-500 hover:text-white hover:bg-white/5 rounded-lg transition-all duration-200"
                  title="Log out"
                  aria-label="Log out"
                >
                  <LogOut className="w-4 h-4" />
                </button>
              </div>
            </div>
          </div>
        </div>
      </header>

      {/* Message Toast */}
      {message && (
        <div className={`fixed top-20 right-6 z-50 flex items-center gap-3 px-4 py-3 rounded-xl shadow-2xl backdrop-blur-xl ${
          message.type === 'success' 
            ? 'bg-emerald-500/10 border border-emerald-500/20 text-emerald-400' 
            : 'bg-red-500/10 border border-red-500/20 text-red-400'
        }`}>
          {message.type === 'success' ? (
            <CheckCircle className="w-5 h-5" />
          ) : (
            <AlertCircle className="w-5 h-5" />
          )}
          <span className="text-sm font-medium">{message.text}</span>
        </div>
      )}

      <div className="max-w-7xl mx-auto px-6 lg:px-8 py-8">
        <div className="grid grid-cols-12 gap-8">
          {/* Sidebar */}
          <nav className="col-span-12 lg:col-span-3">
            <div className="glass-card rounded-2xl p-3 space-y-1">
              <button
                onClick={() => setActiveTab('instructions')}
                className={`w-full flex items-center justify-between px-4 py-3 rounded-xl transition-all duration-200 group ${
                  activeTab === 'instructions' 
                    ? 'bg-gradient-to-r from-blue-500/10 to-violet-500/10 text-white' 
                    : 'text-zinc-400 hover:text-white hover:bg-white/5'
                }`}
              >
                <div className="flex items-center gap-3">
                  <Settings className={`w-5 h-5 ${activeTab === 'instructions' ? 'text-blue-400' : ''}`} />
                  <span className="font-medium">Instructions</span>
                </div>
                {activeTab === 'instructions' && <ChevronRight className="w-4 h-4 text-blue-400" />}
              </button>
              <button
                onClick={() => setActiveTab('channels')}
                className={`w-full flex items-center justify-between px-4 py-3 rounded-xl transition-all duration-200 group ${
                  activeTab === 'channels' 
                    ? 'bg-gradient-to-r from-blue-500/10 to-violet-500/10 text-white' 
                    : 'text-zinc-400 hover:text-white hover:bg-white/5'
                }`}
              >
                <div className="flex items-center gap-3">
                  <Hash className={`w-5 h-5 ${activeTab === 'channels' ? 'text-blue-400' : ''}`} />
                  <span className="font-medium">Channels</span>
                </div>
                {activeTab === 'channels' && <ChevronRight className="w-4 h-4 text-blue-400" />}
              </button>
              <button
                onClick={() => setActiveTab('memory')}
                className={`w-full flex items-center justify-between px-4 py-3 rounded-xl transition-all duration-200 group ${
                  activeTab === 'memory' 
                    ? 'bg-gradient-to-r from-blue-500/10 to-violet-500/10 text-white' 
                    : 'text-zinc-400 hover:text-white hover:bg-white/5'
                }`}
              >
                <div className="flex items-center gap-3">
                  <MessageSquare className={`w-5 h-5 ${activeTab === 'memory' ? 'text-blue-400' : ''}`} />
                  <span className="font-medium">Memory</span>
                </div>
                {activeTab === 'memory' && <ChevronRight className="w-4 h-4 text-blue-400" />}
              </button>
              <button
                onClick={() => setActiveTab('roles')}
                className={`w-full flex items-center justify-between px-4 py-3 rounded-xl transition-all duration-200 group ${
                  activeTab === 'roles' 
                    ? 'bg-gradient-to-r from-blue-500/10 to-violet-500/10 text-white' 
                    : 'text-zinc-400 hover:text-white hover:bg-white/5'
                }`}
              >
                <div className="flex items-center gap-3">
                  <Users className={`w-5 h-5 ${activeTab === 'roles' ? 'text-blue-400' : ''}`} />
                  <span className="font-medium">Roles</span>
                </div>
                {activeTab === 'roles' && <ChevronRight className="w-4 h-4 text-blue-400" />}
              </button>
            </div>

            {/* Status Card */}
            <div className="glass-card rounded-2xl p-5 mt-6">
              <div className="flex items-center gap-2 mb-4">
                <Sparkles className="w-4 h-4 text-amber-400" />
                <h3 className="text-sm font-medium text-zinc-300">System Status</h3>
              </div>
              <div className="space-y-3">
                <div className="flex items-center justify-between">
                  <span className="text-xs text-zinc-500">Bot</span>
                  <span className="flex items-center gap-1.5 text-xs text-emerald-400">
                    <span className="w-1.5 h-1.5 bg-emerald-400 rounded-full animate-pulse" />
                    Online
                  </span>
                </div>
                <div className="flex items-center justify-between">
                  <span className="text-xs text-zinc-500">Servers</span>
                  <span className="text-xs text-zinc-300">{guilds.length}</span>
                </div>
                <div className="flex items-center justify-between">
                  <span className="text-xs text-zinc-500">Memory Entries</span>
                  <span className="text-xs text-zinc-300">{memories.length}</span>
                </div>
              </div>
            </div>
          </nav>

          {/* Main Content */}
          <main className="col-span-12 lg:col-span-9">
            <div className="glass-card rounded-2xl p-8">
              {/* System Instructions Tab */}
              {activeTab === 'instructions' && (
                <div className="space-y-8">
                  <div>
                    <h2 className="text-2xl font-semibold text-white tracking-tight mb-2">System Instructions</h2>
                    <p className="text-zinc-500 text-sm">
                      Define your bot&apos;s personality, tone, and behavioral rules. This is the &quot;brain&quot; of your Discord Copilot.
                    </p>
                  </div>

                  <div className="space-y-2">
                    <label className="block text-sm font-medium text-zinc-400">
                      Bot Name
                    </label>
                    <input
                      type="text"
                      value={botName}
                      onChange={(e) => setBotName(e.target.value)}
                      className="w-full px-4 py-3 input-elegant rounded-xl text-white placeholder-zinc-600 focus:outline-none"
                      placeholder="DasAI Assistant"
                    />
                  </div>

                  <div className="space-y-2">
                    <label className="block text-sm font-medium text-zinc-400">
                      Instructions
                    </label>
                    <textarea
                      value={systemInstructions}
                      onChange={(e) => setSystemInstructions(e.target.value)}
                      rows={15}
                      className="w-full px-4 py-4 input-elegant rounded-xl text-white font-mono text-sm placeholder-zinc-600 focus:outline-none resize-none"
                      placeholder="Enter system instructions..."
                    />
                    <p className="text-xs text-zinc-600">
                      {systemInstructions.length} characters
                    </p>
                  </div>

                  <button
                    onClick={handleSaveConfig}
                    disabled={saving}
                    className="btn-primary flex items-center gap-2 px-6 py-3 text-white font-medium rounded-xl disabled:opacity-50 disabled:cursor-not-allowed"
                  >
                    {saving ? (
                      <Loader2 className="w-5 h-5 animate-spin" />
                    ) : (
                      <Save className="w-5 h-5" />
                    )}
                    Save Configuration
                  </button>
                </div>
              )}

              {/* Allowed Channels Tab */}
              {activeTab === 'channels' && (
                <div className="space-y-8">
                  <div>
                    <h2 className="text-2xl font-semibold text-white tracking-tight mb-2">Allowed Channels</h2>
                    <p className="text-zinc-500 text-sm">
                      Enter Discord Channel IDs where the bot is permitted to respond. One ID per line.
                    </p>
                  </div>

                  <div className="space-y-2">
                    <label className="block text-sm font-medium text-zinc-400">
                      Channel IDs
                    </label>
                    <textarea
                      value={allowedChannels}
                      onChange={(e) => setAllowedChannels(e.target.value)}
                      rows={10}
                      className="w-full px-4 py-4 input-elegant rounded-xl text-white font-mono text-sm placeholder-zinc-600 focus:outline-none resize-none"
                      placeholder="123456789012345678&#10;987654321098765432"
                    />
                    <p className="text-xs text-zinc-600">
                      To get a Channel ID: Enable Developer Mode in Discord Settings → Right-click channel → Copy Channel ID
                    </p>
                  </div>

                  <button
                    onClick={handleSaveConfig}
                    disabled={saving}
                    className="btn-primary flex items-center gap-2 px-6 py-3 text-white font-medium rounded-xl disabled:opacity-50 disabled:cursor-not-allowed"
                  >
                    {saving ? (
                      <Loader2 className="w-5 h-5 animate-spin" />
                    ) : (
                      <Save className="w-5 h-5" />
                    )}
                    Save Channels
                  </button>
                </div>
              )}

              {/* Memory Control Tab */}
              {activeTab === 'memory' && (
                <div className="space-y-8">
                  <div className="flex items-center justify-between">
                    <div>
                      <h2 className="text-2xl font-semibold text-white tracking-tight mb-2">Memory Control</h2>
                      <p className="text-zinc-500 text-sm">
                        View and manage conversation summaries stored by the bot.
                      </p>
                    </div>
                    <button
                      onClick={() => handleResetMemory()}
                      disabled={saving || memories.length === 0}
                      className="flex items-center gap-2 px-4 py-2 bg-red-500/10 border border-red-500/20 text-red-400 hover:bg-red-500/20 disabled:opacity-40 disabled:cursor-not-allowed text-sm font-medium rounded-xl transition-all duration-200"
                    >
                      <Trash2 className="w-4 h-4" />
                      Clear All
                    </button>
                  </div>

                  {memories.length === 0 ? (
                    <div className="text-center py-16">
                      <div className="w-16 h-16 mx-auto mb-4 rounded-2xl bg-zinc-800/50 flex items-center justify-center">
                        <MessageSquare className="w-8 h-8 text-zinc-600" />
                      </div>
                      <p className="text-zinc-400 font-medium">No conversation memories yet</p>
                      <p className="text-sm text-zinc-600 mt-1">Memories will appear here after the bot has conversations</p>
                    </div>
                  ) : (
                    <div className="space-y-4">
                      {memories.map((memory) => (
                        <div 
                          key={memory.id}
                          className="p-5 glass-card rounded-xl hover-lift"
                        >
                          <div className="flex items-start justify-between mb-3">
                            <div className="flex items-center gap-3">
                              <div className="w-8 h-8 rounded-lg bg-blue-500/10 flex items-center justify-center">
                                <Hash className="w-4 h-4 text-blue-400" />
                              </div>
                              <div>
                                <span className="font-mono text-sm text-zinc-300">
                                  {memory.channel_id}
                                </span>
                                <span className="ml-2 px-2 py-0.5 bg-zinc-800 rounded-full text-xs text-zinc-400">
                                  {memory.message_count} messages
                                </span>
                              </div>
                            </div>
                            <button
                              onClick={() => handleResetMemory(memory.channel_id)}
                              className="p-2 text-zinc-500 hover:text-red-400 hover:bg-red-500/10 rounded-lg transition-all duration-200"
                              title="Delete channel memory"
                              aria-label="Delete channel memory"
                            >
                              <Trash2 className="w-4 h-4" />
                            </button>
                          </div>
                          <p className="text-sm text-zinc-400 line-clamp-3 leading-relaxed">
                            {memory.summary || 'No summary available'}
                          </p>
                          <p className="mt-3 text-xs text-zinc-600">
                            Last updated: {new Date(memory.updated_at).toLocaleString()}
                          </p>
                        </div>
                      ))}
                    </div>
                  )}

                  <button
                    onClick={() => router.refresh()}
                    className="flex items-center gap-2 px-4 py-2 text-zinc-400 hover:text-white hover:bg-white/5 rounded-xl transition-all duration-200"
                  >
                    <RefreshCw className="w-4 h-4" />
                    Refresh
                  </button>
                </div>
              )}

              {/* User Roles Tab */}
              {activeTab === 'roles' && (
                <div className="space-y-8">
                  <div>
                    <h2 className="text-2xl font-semibold text-white tracking-tight mb-2">User Roles</h2>
                    <p className="text-zinc-500 text-sm">
                      Manage team members and their permissions. Team Leads can manage the bot, while Members have basic usage rights.
                    </p>
                  </div>

                  <div className="glass-card rounded-xl p-5">
                    <h3 className="text-sm font-medium text-zinc-300 mb-3">How Roles Work</h3>
                    <ul className="text-sm text-zinc-500 space-y-2">
                      <li className="flex items-start gap-2">
                        <Crown className="w-4 h-4 text-amber-400 mt-0.5 flex-shrink-0" />
                        <span><strong className="text-zinc-300">Team Lead:</strong> Can reset memory, manage channels, add/remove knowledge, assign roles</span>
                      </li>
                      <li className="flex items-start gap-2">
                        <UserIcon className="w-4 h-4 text-zinc-400 mt-0.5 flex-shrink-0" />
                        <span><strong className="text-zinc-300">Member:</strong> Can use /ask, /ping, /status, and search knowledge</span>
                      </li>
                      <li className="flex items-start gap-2">
                        <Sparkles className="w-4 h-4 text-blue-400 mt-0.5 flex-shrink-0" />
                        <span>First user to run <code className="bg-zinc-800 px-1.5 py-0.5 rounded text-zinc-300">/setup</code> in Discord becomes Team Lead</span>
                      </li>
                    </ul>
                  </div>

                  {userRoles.length === 0 ? (
                    <div className="text-center py-16">
                      <div className="w-16 h-16 mx-auto mb-4 rounded-2xl bg-zinc-800/50 flex items-center justify-center">
                        <Users className="w-8 h-8 text-zinc-600" />
                      </div>
                      <p className="text-zinc-400 font-medium">No users registered yet</p>
                      <p className="text-sm text-zinc-600 mt-1">Users can register using <code className="bg-zinc-800 px-1.5 py-0.5 rounded">/setup</code> in Discord</p>
                    </div>
                  ) : (
                    <div className="space-y-4">
                      {/* Group by guild */}
                      {Object.entries(
                        userRoles.reduce((acc, role) => {
                          if (!acc[role.guild_id]) acc[role.guild_id] = []
                          acc[role.guild_id].push(role)
                          return acc
                        }, {} as Record<string, typeof userRoles>)
                      ).map(([guildId, roles]) => (
                        <div key={guildId} className="space-y-3">
                          <h3 className="text-xs font-medium text-zinc-500 uppercase tracking-wider flex items-center gap-2">
                            <Server className="w-3 h-3" />
                            Server: {guildId.slice(0, 12)}...
                          </h3>
                          <div className="space-y-3">
                            {roles.map((role) => (
                              <div 
                                key={role.id}
                                className="p-4 glass-card rounded-xl flex items-center justify-between hover-lift"
                              >
                                <div className="flex items-center gap-4">
                                  <div className={`w-10 h-10 rounded-xl flex items-center justify-center ${
                                    role.role === 'team_lead' 
                                      ? 'bg-gradient-to-br from-amber-500/20 to-orange-500/20' 
                                      : 'bg-zinc-800/50'
                                  }`}>
                                    {role.role === 'team_lead' ? (
                                      <Crown className="w-5 h-5 text-amber-400" />
                                    ) : (
                                      <UserIcon className="w-5 h-5 text-zinc-500" />
                                    )}
                                  </div>
                                  <div>
                                    <p className="text-white font-medium">{role.username}</p>
                                    <p className="text-xs text-zinc-600 font-mono">ID: {role.user_id}</p>
                                  </div>
                                </div>
                                <div className="flex items-center gap-3">
                                  <select
                                    value={role.role}
                                    onChange={(e) => handleUpdateRole(role.id, e.target.value as 'team_lead' | 'member')}
                                    className="input-elegant text-sm rounded-lg px-3 py-1.5 text-zinc-300 focus:outline-none cursor-pointer"
                                    disabled={saving}
                                    title='Role Update'
                                  >
                                    <option value="team_lead" className="bg-zinc-900">Team Lead</option>
                                    <option value="member" className="bg-zinc-900">Member</option>
                                  </select>
                                  <button
                                    onClick={() => handleDeleteRole(role.id)}
                                    className="p-2 text-zinc-500 hover:text-red-400 hover:bg-red-500/10 rounded-lg transition-all duration-200"
                                    title="Remove user"
                                    aria-label="Remove user"
                                    disabled={saving}
                                  >
                                    <Trash2 className="w-4 h-4" />
                                  </button>
                                </div>
                              </div>
                            ))}
                          </div>
                        </div>
                      ))}
                    </div>
                  )}

                  <button
                    onClick={() => router.refresh()}
                    className="flex items-center gap-2 px-4 py-2 text-zinc-400 hover:text-white hover:bg-white/5 rounded-xl transition-all duration-200"
                  >
                    <RefreshCw className="w-4 h-4" />
                    Refresh
                  </button>
                </div>
              )}
            </div>
          </main>
        </div>
      </div>
    </div>
  )
}
