// Database types for the DasAI Discord Copilot

export interface BotConfig {
  id: string
  guild_id: string
  guild_name: string | null
  system_instructions: string
  allowed_channels: string[]
  bot_name: string
  created_at: string
  updated_at: string
}

export interface ConversationMemory {
  id: string
  guild_id: string
  channel_id: string
  summary: string
  message_count: number
  created_at: string
  updated_at: string
}

export interface Message {
  id: string
  guild_id: string
  channel_id: string
  user_id: string
  username: string
  content: string
  bot_response: string | null
  created_at: string
}

export interface KnowledgeDocument {
  id: string
  guild_id: string
  filename: string
  content: string
  embedding?: number[]
  created_at: string
}

export interface UserRole {
  id: string
  guild_id: string
  user_id: string
  username: string
  role: 'team_lead' | 'member'
  created_at: string
  updated_at: string
}

export interface GuildInfo {
  id: string
  guild_id: string
  guild_name: string | null
}
