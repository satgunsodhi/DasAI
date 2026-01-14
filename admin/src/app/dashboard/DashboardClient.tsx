'use client'

import { useState } from 'react'
import { createClient } from '@/lib/supabase/client'
import { useRouter } from 'next/navigation'
import type { User } from '@supabase/supabase-js'
import type { BotConfig, ConversationMemory, UserRole } from '@/lib/types'
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
  UserIcon
} from 'lucide-react'

interface Props {
  user: User
  initialConfig: BotConfig | null
  initialMemories: ConversationMemory[]
  initialUserRoles: UserRole[]
}

export default function DashboardClient({ user, initialConfig, initialMemories, initialUserRoles }: Props) {
  const router = useRouter()
  const supabase = createClient()
  
  // State
  const [activeTab, setActiveTab] = useState<'instructions' | 'channels' | 'memory' | 'roles'>('instructions')
  const [saving, setSaving] = useState(false)
  const [message, setMessage] = useState<{ type: 'success' | 'error', text: string } | null>(null)
  
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

    if (initialConfig?.id) {
      // Update existing config
      const { error } = await supabase
        .from('bot_config')
        .update(configData)
        .eq('id', initialConfig.id)

      if (error) {
        showMessage('error', 'Failed to save configuration')
      } else {
        showMessage('success', 'Configuration saved successfully!')
      }
    } else {
      // Insert new config
      const { error } = await supabase
        .from('bot_config')
        .insert([{ ...configData, id: crypto.randomUUID() }])

      if (error) {
        showMessage('error', 'Failed to create configuration')
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
        .eq('channel_id', channelId)

      if (!error) {
        setMemories(memories.filter(m => m.channel_id !== channelId))
        showMessage('success', 'Channel memory cleared')
      }
    } else {
      // Reset all memories
      const { error } = await supabase
        .from('conversation_memory')
        .delete()
        .neq('id', '')

      if (!error) {
        setMemories([])
        showMessage('success', 'All conversation memories cleared')
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
    <div className="min-h-screen bg-gray-900">
      {/* Header */}
      <header className="bg-gray-800 border-b border-gray-700">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex items-center justify-between h-16">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 bg-indigo-600 rounded-xl flex items-center justify-center">
                <Bot className="w-6 h-6 text-white" />
              </div>
              <div>
                <h1 className="text-xl font-bold text-white">DasAI Admin</h1>
                <p className="text-xs text-gray-400">Discord Copilot Control Center</p>
              </div>
            </div>
            
            <div className="flex items-center gap-4">
              <span className="text-sm text-gray-400">{user.email}</span>
              <button
                onClick={handleLogout}
                className="p-2 text-gray-400 hover:text-white hover:bg-gray-700 rounded-lg transition"
                title="Log out"
                aria-label="Log out"
              >
                <LogOut className="w-5 h-5" />
              </button>
            </div>
          </div>
        </div>
      </header>

      {/* Message Toast */}
      {message && (
        <div className={`fixed top-20 right-4 z-50 flex items-center gap-2 px-4 py-3 rounded-lg shadow-lg ${
          message.type === 'success' ? 'bg-green-600' : 'bg-red-600'
        } text-white`}>
          {message.type === 'success' ? (
            <CheckCircle className="w-5 h-5" />
          ) : (
            <AlertCircle className="w-5 h-5" />
          )}
          {message.text}
        </div>
      )}

      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <div className="grid grid-cols-12 gap-6">
          {/* Sidebar */}
          <nav className="col-span-12 lg:col-span-3">
            <div className="bg-gray-800 rounded-xl p-2 space-y-1">
              <button
                onClick={() => setActiveTab('instructions')}
                className={`w-full flex items-center gap-3 px-4 py-3 rounded-lg transition ${
                  activeTab === 'instructions' 
                    ? 'bg-indigo-600 text-white' 
                    : 'text-gray-300 hover:bg-gray-700'
                }`}
              >
                <Settings className="w-5 h-5" />
                System Instructions
              </button>
              <button
                onClick={() => setActiveTab('channels')}
                className={`w-full flex items-center gap-3 px-4 py-3 rounded-lg transition ${
                  activeTab === 'channels' 
                    ? 'bg-indigo-600 text-white' 
                    : 'text-gray-300 hover:bg-gray-700'
                }`}
              >
                <Hash className="w-5 h-5" />
                Allowed Channels
              </button>
              <button
                onClick={() => setActiveTab('memory')}
                className={`w-full flex items-center gap-3 px-4 py-3 rounded-lg transition ${
                  activeTab === 'memory' 
                    ? 'bg-indigo-600 text-white' 
                    : 'text-gray-300 hover:bg-gray-700'
                }`}
              >
                <MessageSquare className="w-5 h-5" />
                Memory Control
              </button>
              <button
                onClick={() => setActiveTab('roles')}
                className={`w-full flex items-center gap-3 px-4 py-3 rounded-lg transition ${
                  activeTab === 'roles' 
                    ? 'bg-indigo-600 text-white' 
                    : 'text-gray-300 hover:bg-gray-700'
                }`}
              >
                <Users className="w-5 h-5" />
                User Roles
              </button>
            </div>
          </nav>

          {/* Main Content */}
          <main className="col-span-12 lg:col-span-9">
            <div className="bg-gray-800 rounded-xl p-6">
              {/* System Instructions Tab */}
              {activeTab === 'instructions' && (
                <div className="space-y-6">
                  <div>
                    <h2 className="text-xl font-semibold text-white mb-2">System Instructions</h2>
                    <p className="text-gray-400 text-sm">
                      Define your bot&apos;s personality, tone, and behavioral rules. This is the &quot;brain&quot; of your Discord Copilot.
                    </p>
                  </div>

                  <div>
                    <label className="block text-sm font-medium text-gray-300 mb-2">
                      Bot Name
                    </label>
                    <input
                      type="text"
                      value={botName}
                      onChange={(e) => setBotName(e.target.value)}
                      className="w-full px-4 py-3 bg-gray-700 border border-gray-600 rounded-lg text-white focus:outline-none focus:ring-2 focus:ring-indigo-500"
                      placeholder="DasAI Assistant"
                    />
                  </div>

                  <div>
                    <label className="block text-sm font-medium text-gray-300 mb-2">
                      Instructions
                    </label>
                    <textarea
                      value={systemInstructions}
                      onChange={(e) => setSystemInstructions(e.target.value)}
                      rows={15}
                      className="w-full px-4 py-3 bg-gray-700 border border-gray-600 rounded-lg text-white font-mono text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500 resize-none"
                      placeholder="Enter system instructions..."
                    />
                    <p className="mt-2 text-xs text-gray-500">
                      {systemInstructions.length} characters
                    </p>
                  </div>

                  <button
                    onClick={handleSaveConfig}
                    disabled={saving}
                    className="flex items-center gap-2 px-6 py-3 bg-indigo-600 hover:bg-indigo-700 disabled:bg-indigo-800 text-white font-medium rounded-lg transition"
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
                <div className="space-y-6">
                  <div>
                    <h2 className="text-xl font-semibold text-white mb-2">Allowed Channels</h2>
                    <p className="text-gray-400 text-sm">
                      Enter Discord Channel IDs where the bot is permitted to respond. One ID per line.
                    </p>
                  </div>

                  <div>
                    <label className="block text-sm font-medium text-gray-300 mb-2">
                      Channel IDs
                    </label>
                    <textarea
                      value={allowedChannels}
                      onChange={(e) => setAllowedChannels(e.target.value)}
                      rows={10}
                      className="w-full px-4 py-3 bg-gray-700 border border-gray-600 rounded-lg text-white font-mono text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500 resize-none"
                      placeholder="123456789012345678&#10;987654321098765432"
                    />
                    <p className="mt-2 text-xs text-gray-500">
                      To get a Channel ID: Enable Developer Mode in Discord Settings → Right-click channel → Copy Channel ID
                    </p>
                  </div>

                  <button
                    onClick={handleSaveConfig}
                    disabled={saving}
                    className="flex items-center gap-2 px-6 py-3 bg-indigo-600 hover:bg-indigo-700 disabled:bg-indigo-800 text-white font-medium rounded-lg transition"
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
                <div className="space-y-6">
                  <div className="flex items-center justify-between">
                    <div>
                      <h2 className="text-xl font-semibold text-white mb-2">Memory Control</h2>
                      <p className="text-gray-400 text-sm">
                        View and manage conversation summaries stored by the bot.
                      </p>
                    </div>
                    <button
                      onClick={() => handleResetMemory()}
                      disabled={saving || memories.length === 0}
                      className="flex items-center gap-2 px-4 py-2 bg-red-600 hover:bg-red-700 disabled:bg-gray-700 disabled:text-gray-500 text-white text-sm font-medium rounded-lg transition"
                    >
                      <Trash2 className="w-4 h-4" />
                      Clear All
                    </button>
                  </div>

                  {memories.length === 0 ? (
                    <div className="text-center py-12 text-gray-500">
                      <MessageSquare className="w-12 h-12 mx-auto mb-4 opacity-50" />
                      <p>No conversation memories yet</p>
                      <p className="text-sm mt-1">Memories will appear here after the bot has conversations</p>
                    </div>
                  ) : (
                    <div className="space-y-4">
                      {memories.map((memory) => (
                        <div 
                          key={memory.id}
                          className="p-4 bg-gray-700/50 rounded-lg border border-gray-600"
                        >
                          <div className="flex items-start justify-between mb-2">
                            <div className="flex items-center gap-2">
                              <Hash className="w-4 h-4 text-gray-400" />
                              <span className="font-mono text-sm text-gray-300">
                                {memory.channel_id}
                              </span>
                              <span className="px-2 py-0.5 bg-gray-600 rounded text-xs text-gray-300">
                                {memory.message_count} messages
                              </span>
                            </div>
                            <button
                              onClick={() => handleResetMemory(memory.channel_id)}
                              className="p-1.5 text-gray-400 hover:text-red-400 hover:bg-gray-600 rounded transition"
                              title="Delete channel memory"
                              aria-label="Delete channel memory"
                            >
                              <Trash2 className="w-4 h-4" />
                            </button>
                          </div>
                          <p className="text-sm text-gray-300 line-clamp-3">
                            {memory.summary || 'No summary available'}
                          </p>
                          <p className="mt-2 text-xs text-gray-500">
                            Last updated: {new Date(memory.updated_at).toLocaleString()}
                          </p>
                        </div>
                      ))}
                    </div>
                  )}

                  <button
                    onClick={() => router.refresh()}
                    className="flex items-center gap-2 px-4 py-2 text-gray-300 hover:text-white hover:bg-gray-700 rounded-lg transition"
                  >
                    <RefreshCw className="w-4 h-4" />
                    Refresh
                  </button>
                </div>
              )}

              {/* User Roles Tab */}
              {activeTab === 'roles' && (
                <div className="space-y-6">
                  <div>
                    <h2 className="text-xl font-semibold text-white mb-2">User Roles</h2>
                    <p className="text-gray-400 text-sm">
                      Manage team members and their permissions. Team Leads can manage the bot, while Members have basic usage rights.
                    </p>
                  </div>

                  <div className="bg-gray-700/30 rounded-lg p-4 border border-gray-600">
                    <h3 className="text-sm font-medium text-gray-300 mb-2">How Roles Work</h3>
                    <ul className="text-sm text-gray-400 space-y-1">
                      <li>👑 <strong>Team Lead:</strong> Can reset memory, manage channels, add/remove knowledge, assign roles</li>
                      <li>👤 <strong>Member:</strong> Can use /ask, /ping, /status, and search knowledge</li>
                      <li>💡 First user to run <code className="bg-gray-700 px-1 rounded">/setup</code> in Discord becomes Team Lead</li>
                    </ul>
                  </div>

                  {userRoles.length === 0 ? (
                    <div className="text-center py-12 text-gray-500">
                      <Users className="w-12 h-12 mx-auto mb-4 opacity-50" />
                      <p>No users registered yet</p>
                      <p className="text-sm mt-1">Users can register using <code className="bg-gray-700 px-1 rounded">/setup</code> in Discord</p>
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
                        <div key={guildId} className="space-y-2">
                          <h3 className="text-sm font-medium text-gray-400 flex items-center gap-2">
                            <Hash className="w-4 h-4" />
                            Server: {guildId}
                          </h3>
                          <div className="space-y-2">
                            {roles.map((role) => (
                              <div 
                                key={role.id}
                                className="p-4 bg-gray-700/50 rounded-lg border border-gray-600 flex items-center justify-between"
                              >
                                <div className="flex items-center gap-3">
                                  {role.role === 'team_lead' ? (
                                    <Crown className="w-5 h-5 text-yellow-500" />
                                  ) : (
                                    <UserIcon className="w-5 h-5 text-gray-400" />
                                  )}
                                  <div>
                                    <p className="text-white font-medium">{role.username}</p>
                                    <p className="text-xs text-gray-500">ID: {role.user_id}</p>
                                  </div>
                                </div>
                                <div className="flex items-center gap-2">
                                  <select
                                    value={role.role}
                                    onChange={(e) => handleUpdateRole(role.id, e.target.value as 'team_lead' | 'member')}
                                    className="bg-gray-600 border border-gray-500 text-white text-sm rounded-lg px-3 py-1.5 focus:outline-none focus:ring-2 focus:ring-indigo-500"
                                    disabled={saving}
                                  >
                                    <option value="team_lead">Team Lead</option>
                                    <option value="member">Member</option>
                                  </select>
                                  <button
                                    onClick={() => handleDeleteRole(role.id)}
                                    className="p-1.5 text-gray-400 hover:text-red-400 hover:bg-gray-600 rounded transition"
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
                    className="flex items-center gap-2 px-4 py-2 text-gray-300 hover:text-white hover:bg-gray-700 rounded-lg transition"
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
