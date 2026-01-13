# DasAI - A Self-Hosted Discord AI Copilot

[![Ask DeepWiki](https://devin.ai/assets/askdeepwiki.png)](https://deepwiki.com/satgunsodhi/dasai)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![Next.js 16](https://img.shields.io/badge/Next.js-16-black.svg)](https://nextjs.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

DasAI is a comprehensive, self-hostable Discord bot that brings the power of large language models to your server. It's designed to be a versatile AI assistant, equipped with long-term memory, a searchable knowledge base (RAG), and a full-featured web-based admin dashboard for easy configuration.

The project is built with a Python-based Discord bot, a Next.js admin panel, and integrates with Supabase for data persistence and Hugging Face for AI model inference.

---

## Table of Contents

- [Features](#features)
- [Architecture](#architecture)
- [System Design](#system-design)
- [Technology Stack](#technology-stack)
- [Database Schema](#database-schema)
- [Setup and Installation](#setup-and-installation)
- [Deployment](#deployment)
- [Bot Commands](#bot-commands)
- [Admin Dashboard](#admin-dashboard)
- [Project Structure](#project-structure)
- [Development Notes](#development-notes)
- [Contributing](#contributing)
- [License](#license)

---

## Features

| Feature | Description |
|---------|-------------|
| 🤖 **AI-Powered Chat** | Responds to messages using Hugging Face Inference API models (Mistral-7B) |
| 📚 **Knowledge Base (RAG)** | Vector database with semantic search for context-aware responses |
| 🧠 **Conversation Memory** | Rolling summaries maintain context across long conversations |
| 🎛️ **Admin Dashboard** | Secure Next.js web UI for bot configuration and management |
| 🐳 **Docker Ready** | Containerized deployment with Railway support |
| ⚡ **Slash Commands** | Modern Discord interactions for knowledge management |
| 🎭 **Custom Personality** | Define bot persona via system instructions |

---

## Architecture

DasAI follows a microservices-inspired architecture with three main components:

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              DasAI Architecture                              │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│    ┌─────────────┐         ┌─────────────┐         ┌─────────────┐         │
│    │   Discord   │         │    Admin    │         │  Hugging    │         │
│    │   Server    │         │  Dashboard  │         │    Face     │         │
│    │             │         │  (Next.js)  │         │    API      │         │
│    └──────┬──────┘         └──────┬──────┘         └──────┬──────┘         │
│           │                       │                       │                 │
│           │ Discord.py            │ Supabase SSR          │ HTTP/REST      │
│           │                       │                       │                 │
│           ▼                       ▼                       ▼                 │
│    ┌─────────────────────────────────────────────────────────────┐         │
│    │                                                             │         │
│    │                     Discord Bot (Python)                    │         │
│    │                                                             │         │
│    │  ┌───────────┐  ┌───────────┐  ┌───────────┐  ┌──────────┐ │         │
│    │  │  Message  │  │    RAG    │  │  Memory   │  │   HF     │ │         │
│    │  │  Handler  │  │  Search   │  │  Manager  │  │  Client  │ │         │
│    │  └───────────┘  └───────────┘  └───────────┘  └──────────┘ │         │
│    │                                                             │         │
│    └──────────────────────────┬──────────────────────────────────┘         │
│                               │                                             │
│                               │ Supabase Client (Service Role)              │
│                               ▼                                             │
│    ┌─────────────────────────────────────────────────────────────┐         │
│    │                                                             │         │
│    │                  Supabase (PostgreSQL + pgvector)           │         │
│    │                                                             │         │
│    │  ┌───────────┐  ┌───────────┐  ┌───────────┐  ┌──────────┐ │         │
│    │  │bot_config │  │ messages  │  │conversation│  │knowledge │ │         │
│    │  │           │  │           │  │  _memory   │  │_documents│ │         │
│    │  └───────────┘  └───────────┘  └───────────┘  └──────────┘ │         │
│    │                                                             │         │
│    └─────────────────────────────────────────────────────────────┘         │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Component Overview

| Component | Technology | Purpose |
|-----------|------------|---------|
| **Discord Bot** | Python, discord.py | Handles Discord events, AI responses, RAG queries |
| **Admin Panel** | Next.js 16, React 19 | Web UI for configuration and management |
| **Database** | Supabase (PostgreSQL + pgvector) | Persistent storage with vector search |
| **AI Backend** | Hugging Face Inference API | LLM chat and embeddings generation |

---

## System Design

### Message Flow

```
┌──────────────────────────────────────────────────────────────────────────┐
│                           Message Processing Flow                         │
└──────────────────────────────────────────────────────────────────────────┘

  User Message                                                    Bot Response
       │                                                               ▲
       ▼                                                               │
┌──────────────┐    ┌──────────────┐    ┌──────────────┐    ┌──────────────┐
│   Discord    │───▶│   Message    │───▶│   Channel    │───▶│    Config    │
│    Event     │    │   Received   │    │    Check     │    │    Fetch     │
└──────────────┘    └──────────────┘    └──────────────┘    └──────────────┘
                                                                    │
                    ┌───────────────────────────────────────────────┘
                    ▼
┌──────────────┐    ┌──────────────┐    ┌──────────────┐    ┌──────────────┐
│   Generate   │◀───│    Build     │◀───│     RAG      │◀───│   Memory     │
│   Response   │    │   Prompt     │    │    Search    │    │   Lookup     │
└──────────────┘    └──────────────┘    └──────────────┘    └──────────────┘
       │
       ▼
┌──────────────┐    ┌──────────────┐    ┌──────────────┐
│   Hugging    │───▶│    Save      │───▶│   Update     │
│   Face API   │    │   Message    │    │   Memory     │
└──────────────┘    └──────────────┘    └──────────────┘
```

### RAG (Retrieval-Augmented Generation) Pipeline

```
┌──────────────────────────────────────────────────────────────────────────┐
│                              RAG Pipeline                                 │
└──────────────────────────────────────────────────────────────────────────┘

                    Document Ingestion                    Query Processing
                    ──────────────────                    ────────────────

┌──────────────┐    ┌──────────────┐         ┌──────────────┐    ┌──────────────┐
│   Document   │───▶│    Chunk     │         │    User      │───▶│   Generate   │
│    Input     │    │   Content    │         │    Query     │    │  Embedding   │
└──────────────┘    └──────────────┘         └──────────────┘    └──────────────┘
                           │                                            │
                           ▼                                            ▼
                    ┌──────────────┐                          ┌──────────────┐
                    │   Generate   │                          │   Vector     │
                    │  Embeddings  │                          │   Search     │
                    │  (768-dim)   │                          │  (pgvector)  │
                    └──────────────┘                          └──────────────┘
                           │                                            │
                           ▼                                            ▼
                    ┌──────────────┐                          ┌──────────────┐
                    │    Store     │                          │   Retrieve   │
                    │  in Supabase │                          │   Top-K      │
                    └──────────────┘                          └──────────────┘
                                                                        │
                                                                        ▼
                                                              ┌──────────────┐
                                                              │   Augment    │
                                                              │    Prompt    │
                                                              └──────────────┘
```

---

## Technology Stack

### Backend (Discord Bot)

| Technology | Version | Purpose |
|------------|---------|---------|
| Python | 3.11+ | Runtime environment |
| discord.py | 2.3+ | Discord API wrapper |
| httpx | 0.26+ | Async HTTP client |
| supabase-py | 2.3+ | Database client |
| python-dotenv | 1.0+ | Environment management |

### Frontend (Admin Dashboard)

| Technology | Version | Purpose |
|------------|---------|---------|
| Next.js | 16.1 | React framework with App Router |
| React | 19 | UI library |
| TypeScript | 5+ | Type safety |
| Tailwind CSS | 3.4+ | Styling |
| Supabase SSR | 0.5+ | Auth & database client |
| Lucide React | - | Icons |

### Infrastructure

| Service | Purpose |
|---------|---------|
| **Supabase** | PostgreSQL database with pgvector, authentication, RLS |
| **Hugging Face** | LLM inference (Mistral-7B) and embeddings (nomic-embed-text) |
| **Railway** | Container deployment for the bot |
| **Vercel** | Admin dashboard hosting |

---

## Database Schema

### Entity Relationship Diagram

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                            Database Schema                                   │
└─────────────────────────────────────────────────────────────────────────────┘

┌─────────────────────┐          ┌─────────────────────┐
│     bot_config      │          │      messages       │
├─────────────────────┤          ├─────────────────────┤
│ id          UUID PK │          │ id          UUID PK │
│ bot_name    TEXT    │          │ channel_id  TEXT    │───┐
│ system_     TEXT    │          │ user_id     TEXT    │   │
│ instructions        │          │ username    TEXT    │   │
│ allowed_    TEXT[]  │          │ content     TEXT    │   │
│ channels            │          │ bot_response TEXT   │   │
│ created_at  TIMESTZ │          │ created_at  TIMESTZ │   │
│ updated_at  TIMESTZ │          └─────────────────────┘   │
└─────────────────────┘                                    │
                                                           │
┌─────────────────────┐          ┌─────────────────────┐   │
│ conversation_memory │          │ knowledge_documents │   │
├─────────────────────┤          ├─────────────────────┤   │
│ id          UUID PK │          │ id          UUID PK │   │
│ channel_id  TEXT UK │◀─────────│ title       TEXT    │   │
│ summary     TEXT    │          │ filename    TEXT    │   │
│ message_    INTEGER │          │ content     TEXT    │   │
│ count               │          │ chunk_index INTEGER │   │
│ created_at  TIMESTZ │          │ embedding   VECTOR  │   │
│ updated_at  TIMESTZ │          │ metadata    JSONB   │   │
└─────────────────────┘          │ created_at  TIMESTZ │   │
         ▲                       └─────────────────────┘   │
         │                                                 │
         └─────────────────────────────────────────────────┘
                        (channel_id relationship)
```

### Table Descriptions

| Table | Purpose | Key Features |
|-------|---------|--------------|
| `bot_config` | Stores bot personality and settings | System instructions, allowed channels |
| `messages` | Message history log | User messages and bot responses |
| `conversation_memory` | Rolling conversation summaries | Maintains context per channel |
| `knowledge_documents` | RAG document store | 768-dim vector embeddings for semantic search |

### Vector Search Function

```sql
-- Semantic similarity search using cosine distance
CREATE FUNCTION search_documents(
    query_embedding vector(768),
    match_threshold FLOAT DEFAULT 0.7,
    match_count INT DEFAULT 5
) RETURNS TABLE (id UUID, title TEXT, content TEXT, similarity FLOAT)
```

---

## Setup and Installation

### Prerequisites

- Python 3.11+
- Node.js 18+ and npm
- A Discord account with server admin privileges
- A [Supabase](https://supabase.io) account (free tier works)
- A [Hugging Face](https://huggingface.co) account with API token

### 1. Clone the Repository

```bash
git clone https://github.com/satgunsodhi/dasai.git
cd dasai
```

### 2. Supabase Setup

1. Create a new project on [Supabase.io](https://supabase.io)
2. Navigate to **Database** → **Extensions** and enable `vector`
3. Go to **SQL Editor** and run the contents of `database/schema.sql`
4. Copy your credentials from **Project Settings** → **API**:
   - Project URL
   - `anon` public key
   - `service_role` secret key

### 3. Discord Bot Setup

1. Go to [Discord Developer Portal](https://discord.com/developers/applications)
2. Create a **New Application** → **Bot** → **Add Bot**
3. Enable **Privileged Gateway Intents**:
   - ✅ Server Members Intent
   - ✅ Message Content Intent
4. Copy the bot token
5. Generate invite URL via **OAuth2** → **URL Generator**:
   - Scopes: `bot`, `applications.commands`
   - Permissions: `Read Messages`, `Send Messages`, `Read Message History`
6. Invite bot to your server

### 4. Configure Environment Variables

**Root `.env`** (for the bot):

```env
# Discord
DISCORD_TOKEN=your_discord_bot_token

# Supabase
SUPABASE_URL=https://your-project-id.supabase.co
SUPABASE_SERVICE_ROLE_KEY=your_service_role_key

# Hugging Face
HF_API_KEY=hf_your_api_key
HF_MODEL=mistralai/Mistral-7B-Instruct-v0.3
HF_EMBED_MODEL=nomic-ai/nomic-embed-text-v1
```

**`admin/.env.local`** (for the dashboard):

```env
NEXT_PUBLIC_SUPABASE_URL=https://your-project-id.supabase.co
NEXT_PUBLIC_SUPABASE_ANON_KEY=your_anon_public_key
```

### 5. Run the Bot

```bash
# Create virtual environment
python -m venv .venv
.venv\Scripts\activate  # Windows
# source .venv/bin/activate  # Linux/Mac

# Install dependencies
pip install -r requirements.txt

# Run
python bot.py
```

### 6. Run the Admin Dashboard

```bash
cd admin
npm install
npm run dev
```

Access at `http://localhost:3000`

> **Note:** Create admin users via Supabase Dashboard → **Authentication** → **Users**

---

## Deployment

### Discord Bot (Railway)

The repository includes `Dockerfile` and `railway.json` for easy deployment:

1. Fork this repository
2. Create new project on [Railway](https://railway.app)
3. Deploy from GitHub repo
4. Add environment variables in Railway dashboard:
   - `DISCORD_TOKEN`
   - `SUPABASE_URL`
   - `SUPABASE_SERVICE_ROLE_KEY`
   - `HF_API_KEY`
   - `HF_MODEL`
   - `HF_EMBED_MODEL`

### Admin Dashboard (Vercel)

1. Import the `admin` directory to [Vercel](https://vercel.com)
2. Set environment variables:
   - `NEXT_PUBLIC_SUPABASE_URL`
   - `NEXT_PUBLIC_SUPABASE_ANON_KEY`

---

## Bot Commands

### Slash Commands

| Command | Description | Example |
|---------|-------------|---------|
| `/ask <question>` | Ask the AI directly | `/ask What is DasAI?` |
| `/ping` | Check bot latency | `/ping` |
| `/knowledge_add <title> <content>` | Add to knowledge base | `/knowledge_add FAQ Our hours are 9-5` |
| `/knowledge_search <query>` | Semantic search | `/knowledge_search business hours` |
| `/knowledge_list` | List all documents | `/knowledge_list` |
| `/knowledge_delete <title>` | Delete document | `/knowledge_delete FAQ` |

### Prefix Commands

| Command | Description |
|---------|-------------|
| `!ping` | Legacy ping command |
| `!status` | Show bot status and configuration |
| `!sync` | Sync slash commands (admin only) |
| `!refresh` | Refresh bot configuration |

---

## Admin Dashboard

The admin dashboard provides a secure web interface for managing your bot:

### Features

- **Bot Configuration**: Edit bot name, system instructions, personality
- **Channel Management**: Configure allowed channels
- **Knowledge Base**: View, add, and delete documents
- **Conversation Memory**: Monitor and clear channel memories
- **Message History**: View recent bot interactions

### Authentication

- Uses Supabase Auth with email/password
- Protected by Row Level Security (RLS)
- Session management via cookies

---

## Project Structure

```
DasAI/
├── bot.py                    # Main Discord bot
├── requirements.txt          # Python dependencies
├── Dockerfile               # Container configuration
├── railway.json             # Railway deployment config
├── .env                     # Bot environment variables
│
├── admin/                   # Next.js admin dashboard
│   ├── src/
│   │   ├── app/
│   │   │   ├── dashboard/   # Protected dashboard pages
│   │   │   ├── login/       # Authentication
│   │   │   └── layout.tsx   # Root layout
│   │   ├── lib/
│   │   │   └── supabase/    # Supabase client utilities
│   │   └── proxy.ts         # Auth middleware
│   ├── .env.local           # Dashboard environment
│   └── package.json
│
└── database/
    └── schema.sql           # PostgreSQL schema with pgvector
```

---

## Development Notes

### Design Decisions

1. **Hugging Face over OpenAI**: Chose HF Inference API for cost-effectiveness and model variety
2. **Supabase over Firebase**: PostgreSQL with pgvector enables native vector search without external services
3. **Next.js 16 with App Router**: Modern React patterns with Server Components and Server Actions
4. **discord.py async**: Non-blocking I/O for handling concurrent Discord events

### Key Implementation Details

- **Embedding Dimensions**: 768-dim vectors (nomic-embed-text-v1)
- **Memory Strategy**: Rolling summaries every 5 messages to prevent context overflow
- **RAG Threshold**: 0.7 cosine similarity for document retrieval
- **Rate Limiting**: Handled via httpx timeouts and HF API retry logic

### Security Considerations

- Service role key used only server-side (bot)
- Anon key for client-side dashboard
- RLS policies enforce authentication
- Environment variables never committed

---

## Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit changes (`git commit -m 'Add amazing feature'`)
4. Push to branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

---

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

---

## Acknowledgments

- [discord.py](https://discordpy.readthedocs.io/) - Discord API wrapper
- [Supabase](https://supabase.io) - Backend as a Service
- [Hugging Face](https://huggingface.co) - AI model hosting
- [Next.js](https://nextjs.org) - React framework
- [pgvector](https://github.com/pgvector/pgvector) - Vector similarity search

---

<p align="center">
  Built with ❤️ by <a href="https://github.com/satgunsodhi">Satgun Sodhi</a>
</p>
