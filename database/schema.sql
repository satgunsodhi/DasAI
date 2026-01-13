-- DasAI Discord Copilot Database Schema
-- Run this in your Supabase SQL Editor

-- Enable UUID extension
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Enable pgvector extension for RAG embeddings
-- NOTE: In Supabase, go to Database > Extensions and enable "vector" first
CREATE EXTENSION IF NOT EXISTS "vector";

-- Bot Configuration Table
CREATE TABLE IF NOT EXISTS bot_config (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    bot_name TEXT NOT NULL DEFAULT 'DasAI Assistant',
    system_instructions TEXT NOT NULL DEFAULT 'You are a helpful AI assistant.',
    allowed_channels TEXT[] DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Conversation Memory Table (for rolling summaries)
CREATE TABLE IF NOT EXISTS conversation_memory (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    channel_id TEXT NOT NULL UNIQUE,
    summary TEXT NOT NULL DEFAULT '',
    message_count INTEGER DEFAULT 0,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Message History Table (for context)
CREATE TABLE IF NOT EXISTS messages (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    channel_id TEXT NOT NULL,
    user_id TEXT NOT NULL,
    username TEXT NOT NULL,
    content TEXT NOT NULL,
    bot_response TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Knowledge Documents Table (RAG)
-- Uses nomic-ai/nomic-embed-text-v1 from Hugging Face (768 dimensions)
CREATE TABLE IF NOT EXISTS knowledge_documents (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    title TEXT NOT NULL,
    filename TEXT,
    content TEXT NOT NULL,
    chunk_index INTEGER DEFAULT 0,
    embedding vector(768),  -- nomic-embed-text produces 768-dim embeddings
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Index for vector similarity search (using cosine distance)
CREATE INDEX IF NOT EXISTS idx_knowledge_embedding ON knowledge_documents 
USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);

-- Function for similarity search
CREATE OR REPLACE FUNCTION search_documents(
    query_embedding vector(768),
    match_threshold FLOAT DEFAULT 0.7,
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
    WHERE kd.embedding IS NOT NULL
        AND 1 - (kd.embedding <=> query_embedding) > match_threshold
    ORDER BY kd.embedding <=> query_embedding
    LIMIT match_count;
END;
$$;

-- Indexes for performance
CREATE INDEX IF NOT EXISTS idx_messages_channel_id ON messages(channel_id);
CREATE INDEX IF NOT EXISTS idx_messages_created_at ON messages(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_conversation_memory_channel_id ON conversation_memory(channel_id);

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

-- Policies for service role (Discord bot uses service role key)
CREATE POLICY "Allow service role full access to bot_config" ON bot_config
    FOR ALL TO service_role USING (true);

CREATE POLICY "Allow service role full access to conversation_memory" ON conversation_memory
    FOR ALL TO service_role USING (true);

CREATE POLICY "Allow service role full access to messages" ON messages
    FOR ALL TO service_role USING (true);

CREATE POLICY "Allow service role full access to knowledge_documents" ON knowledge_documents
    FOR ALL TO service_role USING (true);

-- Insert default configuration
-- Empty allowed_channels array means ALL channels are allowed
INSERT INTO bot_config (bot_name, system_instructions, allowed_channels)
VALUES (
    'DasAI Assistant',
    'You are a helpful AI assistant for a Discord server. Be friendly, concise, and helpful.

Key behaviors:
- Answer questions accurately and helpfully
- Be conversational but professional
- If you don''t know something, say so
- Keep responses concise unless detail is requested',
    '{}'  -- Empty array = all channels allowed
) ON CONFLICT DO NOTHING;

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
