-- DasAI Discord Copilot Database Schema
-- Run this in your Supabase SQL Editor

-- Enable UUID extension
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Enable pgvector extension for RAG embeddings
-- NOTE: In Supabase, go to Database > Extensions and enable "vector" first
CREATE EXTENSION IF NOT EXISTS "vector";

-- Bot Configuration Table (per-guild configuration)
-- Each Discord server gets its own configuration
CREATE TABLE IF NOT EXISTS bot_config (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    guild_id TEXT NOT NULL UNIQUE,
    guild_name TEXT,
    bot_name TEXT NOT NULL DEFAULT 'DasAI Assistant',
    system_instructions TEXT NOT NULL DEFAULT 'You are a helpful AI assistant.',
    allowed_channels TEXT[] DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- User Roles Table (for role-based access control)
-- Roles: 'team_lead' (full access), 'member' (basic usage)
CREATE TABLE IF NOT EXISTS user_roles (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    guild_id TEXT NOT NULL,
    user_id TEXT NOT NULL,
    username TEXT NOT NULL,
    role TEXT NOT NULL DEFAULT 'member' CHECK (role IN ('team_lead', 'member')),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(guild_id, user_id)
);

-- Conversation Memory Table (for rolling summaries)
-- Now includes guild_id for multi-server support
CREATE TABLE IF NOT EXISTS conversation_memory (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    guild_id TEXT NOT NULL,
    channel_id TEXT NOT NULL,
    summary TEXT NOT NULL DEFAULT '',
    message_count INTEGER DEFAULT 0,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(guild_id, channel_id)
);

-- Message History Table (for context)
CREATE TABLE IF NOT EXISTS messages (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    guild_id TEXT NOT NULL,
    channel_id TEXT NOT NULL,
    user_id TEXT NOT NULL,
    username TEXT NOT NULL,
    content TEXT NOT NULL,
    bot_response TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Knowledge Documents Table (RAG) - per-guild
-- Uses sentence-transformers/all-MiniLM-L6-v2 from Hugging Face (384 dimensions)
CREATE TABLE IF NOT EXISTS knowledge_documents (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    guild_id TEXT NOT NULL,
    title TEXT NOT NULL,
    filename TEXT,
    content TEXT NOT NULL,
    chunk_index INTEGER DEFAULT 0,
    embedding vector(384),  -- all-MiniLM-L6-v2 produces 384-dim embeddings
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Index for vector similarity search (using cosine distance)
CREATE INDEX IF NOT EXISTS idx_knowledge_embedding ON knowledge_documents 
USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);

-- Index for guild-based queries
CREATE INDEX IF NOT EXISTS idx_knowledge_guild ON knowledge_documents(guild_id);

-- Function for similarity search (now includes guild_id filter)
CREATE OR REPLACE FUNCTION search_documents(
    p_guild_id TEXT,
    query_embedding vector(384),
    match_threshold FLOAT DEFAULT 0.5,
    match_count INT DEFAULT 5
)
RETURNS TABLE (
    id UUID,
    title TEXT,
    content TEXT,
    similarity FLOAT
)
LANGUAGE plpgsql
AS $$
BEGIN
    RETURN QUERY
    SELECT
        kd.id,
        kd.title,
        kd.content,
        1 - (kd.embedding <=> query_embedding) AS similarity
    FROM knowledge_documents kd
    WHERE kd.guild_id = p_guild_id
        AND kd.embedding IS NOT NULL
        AND 1 - (kd.embedding <=> query_embedding) > match_threshold
    ORDER BY kd.embedding <=> query_embedding
    LIMIT match_count;
END;
$$;

-- Indexes for performance
CREATE INDEX IF NOT EXISTS idx_messages_channel_id ON messages(channel_id);
CREATE INDEX IF NOT EXISTS idx_messages_guild_id ON messages(guild_id);
CREATE INDEX IF NOT EXISTS idx_messages_created_at ON messages(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_conversation_memory_channel_id ON conversation_memory(channel_id);
CREATE INDEX IF NOT EXISTS idx_conversation_memory_guild_id ON conversation_memory(guild_id);
CREATE INDEX IF NOT EXISTS idx_bot_config_guild_id ON bot_config(guild_id);

-- Row Level Security (RLS)
ALTER TABLE bot_config ENABLE ROW LEVEL SECURITY;
ALTER TABLE conversation_memory ENABLE ROW LEVEL SECURITY;
ALTER TABLE messages ENABLE ROW LEVEL SECURITY;
ALTER TABLE knowledge_documents ENABLE ROW LEVEL SECURITY;

-- Policies for authenticated users (admin dashboard)
CREATE POLICY "Allow authenticated users to read bot_config" ON bot_config
    FOR SELECT TO authenticated USING (true);

CREATE POLICY "Allow authenticated users to update bot_config" ON bot_config
    FOR UPDATE TO authenticated USING (true);

CREATE POLICY "Allow authenticated users to insert bot_config" ON bot_config
    FOR INSERT TO authenticated WITH CHECK (true);

CREATE POLICY "Allow authenticated users full access to conversation_memory" ON conversation_memory
    FOR ALL TO authenticated USING (true);

CREATE POLICY "Allow authenticated users full access to messages" ON messages
    FOR ALL TO authenticated USING (true);

CREATE POLICY "Allow authenticated users full access to knowledge_documents" ON knowledge_documents
    FOR ALL TO authenticated USING (true);

CREATE POLICY "Allow authenticated users full access to user_roles" ON user_roles
    FOR ALL TO authenticated USING (true);

-- Policies for service role (Discord bot uses service role key)
CREATE POLICY "Allow service role full access to bot_config" ON bot_config
    FOR ALL TO service_role USING (true);

CREATE POLICY "Allow service role full access to conversation_memory" ON conversation_memory
    FOR ALL TO service_role USING (true);

CREATE POLICY "Allow service role full access to messages" ON messages
    FOR ALL TO service_role USING (true);

CREATE POLICY "Allow service role full access to knowledge_documents" ON knowledge_documents
    FOR ALL TO service_role USING (true);

CREATE POLICY "Allow service role full access to user_roles" ON user_roles
    FOR ALL TO service_role USING (true);

-- RLS for user_roles table
ALTER TABLE user_roles ENABLE ROW LEVEL SECURITY;

-- Note: Default configuration is now created automatically per-guild when the bot joins a server
-- The bot.py auto-creates a config entry for each guild on first interaction

-- Function to update timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Triggers for updated_at
CREATE TRIGGER update_bot_config_updated_at
    BEFORE UPDATE ON bot_config
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_conversation_memory_updated_at
    BEFORE UPDATE ON conversation_memory
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_user_roles_updated_at
    BEFORE UPDATE ON user_roles
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
