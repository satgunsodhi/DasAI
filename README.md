# DasAI - A Self-Hosted Discord AI Copilot

[![Ask DeepWiki](https://devin.ai/assets/askdeepwiki.png)](https://deepwiki.com/satgunsodhi/dasai)

DasAI is a comprehensive, self-hostable Discord bot that brings the power of large language models to your server. It's designed to be a versatile AI assistant, equipped with long-term memory, a searchable knowledge base (RAG), and a full-featured web-based admin dashboard for easy configuration.

The project is built with a Python-based Discord bot, a Next.js admin panel, and integrates with Supabase for data persistence and Hugging Face for AI model inference.

## Table of Contents

- [Features](#features)
- [Architecture](#architecture)
- [System Design](#system-design)
- [Technology Stack](#technology-stack)
- [Database Schema](#database-schema)
- [Setup and Installation](#setup-and-installation)
- [Deployment](#deployment)
- [Bot Commands](#bot-commands)
- [Multi-Server Support](#multi-server-support)
- [Admin Dashboard](#admin-dashboard)
- [Project Structure](#project-structure)
- [Development Notes](#development-notes)
- [Contributing](#contributing)
- [License](#license)

---

## Features

| Feature                 | Description                                                                                                     |
| ----------------------- | --------------------------------------------------------------------------------------------------------------- |
| 🤖 **AI-Powered Chat**  | Responds to messages using Hugging Face Inference API models.                                                   |
| 📚 **Knowledge Base**    | Implements Retrieval-Augmented Generation (RAG) with a vector database for context-aware responses.             |
| 🧠 **Conversation Memory** | Maintains conversational context per-channel using rolling summaries.                                         |
| 🎛️ **Admin Dashboard**  | A secure Next.js web UI for bot configuration, channel management, and knowledge base administration.           |
| 🌐 **Multi-Server Support** | Deploy to multiple Discord servers with isolated configurations, knowledge bases, and roles.                    |
| 👑 **Role-Based Access**  | `Team Lead` and `Member` roles for granular access control over bot management commands.                        |
| 🐳 **Docker Ready**       | Containerized for easy deployment using Docker, with built-in support for Railway.                              |
| ⚡ **Slash Commands**    | Utilizes modern Discord interactions for knowledge management, role assignment, and more.                       |
| 🎭 **Custom Personality** | Define the bot's persona, tone, and behavior through system instructions in the admin dashboard.                |
| 📄 **File Uploads**       | Add documents to the knowledge base by uploading `.txt`, `.md`, and `.pdf` files directly in Discord.       |
| 🕸️ **Web Search**        | Can be configured to perform web searches for real-time information to augment its responses.                   |

---

## Architecture

DasAI employs a microservices-inspired architecture, separating the bot logic, administration panel, and data persistence layers.

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              DasAI Architecture                             │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│    ┌─────────────┐         ┌─────────────┐         ┌─────────────┐        │
│    │   Discord   │         │    Admin    │         │  Hugging    │        │
│    │   Server    │         │  Dashboard  │         │    Face     │        │
│    │             │         │  (Next.js)  │         │    API      │        │
│    └──────┬──────┘         └──────┬──────┘         └──────┬──────┘        │
│           │                       │                       │                │
│           │ Discord.py            │ Supabase SSR Auth     │ HTTP/REST      │
│           │                       │                       │                │
│           ▼                       ▼                       ▼                │
│    ┌─────────────────────────────────────────────────────────────┐        │
│    │                                                             │        │
│    │                     Discord Bot (Python)                    │        │
│    │                                                             │        │
│    │  ┌───────────┐  ┌───────────┐  ┌───────────┐  ┌──────────┐ │        │
│    │  │  Message  │  │    RAG    │  │  Memory   │  │   HF     │ │        │
│    │  │  Handler  │  │  Search   │  │  Manager  │  │  Client  │ │        │
│    │  └───────────┘  └───────────┘  └───────────┘  └──────────┘ │        │
│    │                                                             │        │
│    └──────────────────────────┬──────────────────────────────────┘        │
│                               │                                            │
│                Supabase Client (Service Role Key)                          │
│                               ▼                                            │
│    ┌─────────────────────────────────────────────────────────────┐        │
│    │                                                             │        │
│    │                  Supabase (PostgreSQL + pgvector)           │        │
│    │                                                             │        │
│    │  ┌───────────┐  ┌───────────┐  ┌───────────┐  ┌──────────┐ │        │
│    │  │bot_config │  │ messages  │  │conversation│  │knowledge │ │        │
│    │  │           │  │           │  │  _memory   │  │_documents│ │        │
│    │  └───────────┘  └───────────┘  └───────────┘  └──────────┘ │        │
│    │                                                             │        │
│    └─────────────────────────────────────────────────────────────┘        │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

| Component     | Technology                            | Purpose                                               |
| ------------- | ------------------------------------- | ----------------------------------------------------- |
| **Discord Bot** | Python, discord.py                    | Handles Discord events, AI logic, and RAG queries.    |
| **Admin Panel** | Next.js, React, Tailwind CSS          | Web UI for bot configuration and data management.     |
| **Database**    | Supabase (PostgreSQL + pgvector)      | Stores configurations, messages, roles, and vectors.  |
| **AI Backend**  | Hugging Face Inference API            | Provides LLM chat completions and text embeddings.    |

---

## System Design

### Message Processing Flow

```
┌──────────────────────────────────────────────────────────────────────────┐
│                           Message Processing Flow                        │
└──────────────────────────────────────────────────────────────────────────┘

  User Message                                                    Bot Response
       │                                                               ▲
       ▼                                                               │
┌──────────────┐    ┌──────────────┐    ┌──────────────┐    ┌──────────────┐
│   Discord    │───▶│   Message    │───▶│    Channel   │───▶│    Config    │
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

### Retrieval-Augmented Generation (RAG) Pipeline

```
┌──────────────────────────────────────────────────────────────────────────┐
│                              RAG Pipeline                              │
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
                    │  (384-dim)   │                          │  (pgvector)  │
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

| Technology      | Version | Purpose                       |
| --------------- | ------- | ----------------------------- |
| Python          | 3.11+   | Runtime environment           |
| discord.py      | 2.3+    | Discord API wrapper           |
| supabase-py     | 2.3+    | Supabase database client      |
| huggingface_hub | 0.25+   | Hugging Face API client       |
| PyPDF2          | 3.0+    | PDF text extraction           |
| ddgs            | 9.10+   | DuckDuckGo web search         |

### Frontend (Admin Dashboard)

| Technology     | Version | Purpose                           |
| -------------- | ------- | --------------------------------- |
| Next.js        | 16+     | React framework with App Router   |
| React          | 19      | UI library                        |
| TypeScript     | 5+      | Type safety                       |
| Tailwind CSS   | 3.4+    | Styling                           |
| Supabase SSR   | 0.5+    | Server-side auth & data fetching  |
| Lucide React   | -       | Icons                             |

### Infrastructure

| Service        | Purpose                                            |
| -------------- | -------------------------------------------------- |
| **Supabase**   | PostgreSQL database, pgvector, authentication, RLS |
| **Hugging Face** | LLM inference and text embeddings                |
| **Railway**    | Container deployment for the Discord bot           |
| **Vercel**     | Hosting for the Next.js admin dashboard          |

---

## Database Schema

### Entity Relationship Diagram

```
┌─────────────────────┐          ┌─────────────────────┐          ┌─────────────────────┐
│     bot_config      │          │      messages       │          │      user_roles     │
├─────────────────────┤          ├─────────────────────┤          ├─────────────────────┤
│ id          UUID PK │          │ id          UUID PK │          │ id          UUID PK │
│ guild_id    TEXT UK │          │ guild_id    TEXT    │<─────────│ guild_id    TEXT    │
│ bot_name    TEXT    │          │ channel_id  TEXT    │<─┐        │ user_id     TEXT    │
│ system_     TEXT    │          │ user_id     TEXT    │  │        │ username    TEXT    │
│ instructions        │          │ content     TEXT    │  │        │ role        TEXT    │
│ allowed_    TEXT[]  │          │ bot_response TEXT   │  │        │ created_at  TIMESTZ │
│ channels            │          │ created_at  TIMESTZ │  │        │ updated_at  TIMESTZ │
│ created_at  TIMESTZ │          └─────────────────────┘  │        └─────────────────────┘
└─────────────────────┘                                  │
                                                         │
┌─────────────────────┐          ┌─────────────────────┐ │
│ conversation_memory │          │ knowledge_documents │ │
├─────────────────────┤          ├─────────────────────┤ │
│ id          UUID PK │          │ id          UUID PK │ │
│ guild_id    TEXT    │──────────│ guild_id    TEXT    │ │
│ channel_id  TEXT UK │◀─────────┘                      │
│ summary     TEXT    │          │ title       TEXT    │ │
│ message_    INTEGER │          │ content     TEXT    │ │
│ count               │          │ embedding   VECTOR(384) │
│ created_at  TIMESTZ │          │ chunk_index INTEGER │ │
│ updated_at  TIMESTZ │          │ created_at  TIMESTZ │ │
└─────────────────────┘          └─────────────────────┘ │
         ▲                                               │
         └───────────────────────────────────────────────┘
                     (Implicit guild_id & channel_id FKs)
```

### Table Descriptions

| Table                 | Purpose                                                | Key Columns                                     |
| --------------------- | ------------------------------------------------------ | ----------------------------------------------- |
| `bot_config`          | Stores bot personality and settings per Discord server.| `guild_id`, `system_instructions`, `allowed_channels` |
| `user_roles`          | Manages user permissions (`team_lead`, `member`).      | `guild_id`, `user_id`, `role`                   |
| `conversation_memory` | Stores rolling conversation summaries per channel.     | `guild_id`, `channel_id`, `summary`             |
| `messages`            | Logs user messages and bot responses for history.      | `guild_id`, `channel_id`, `content`, `bot_response` |
| `knowledge_documents` | Stores chunked documents and their vector embeddings.  | `guild_id`, `content`, `embedding` (384-dim)    |

---

## Setup and Installation

### Prerequisites

- Python 3.11+
- Node.js 18+ and npm
- A Discord account with server admin privileges
- A [Supabase](https://supabase.io) account (free tier is sufficient)
- A [Hugging Face](https://huggingface.co) account with an API token

### 1. Clone the Repository

```bash
git clone https://github.com/satgunsodhi/dasai.git
cd dasai
```

### 2. Supabase Setup

1.  Create a new project on [Supabase.io](https://supabase.io).
2.  Navigate to **Database** → **Extensions** and enable `vector`.
3.  Go to the **SQL Editor**, create a "New query", and run the entire contents of `database/schema.sql`.
4.  Navigate to **Project Settings** → **API** and copy your credentials:
    -   Project URL
    -   `anon` public key (`NEXT_PUBLIC_SUPABASE_ANON_KEY`)
    -   `service_role` secret key (`SUPABASE_SERVICE_ROLE_KEY`)

### 3. Discord Bot Setup

1.  Go to the [Discord Developer Portal](https://discord.com/developers/applications).
2.  Create a **New Application**, give it a name, and then go to the **Bot** tab.
3.  Click **Add Bot**. Under **Privileged Gateway Intents**, enable:
    -   ✅ **Server Members Intent**
    -   ✅ **Message Content Intent**
4.  Under the bot's username, click **Reset Token** to generate and copy the bot token.
5.  Generate an invite URL via **OAuth2** → **URL Generator**:
    -   Scopes: `bot`, `applications.commands`
    -   Bot Permissions: `Read Messages/View Channels`, `Send Messages`, `Read Message History`
6.  Use the generated URL to invite the bot to your Discord server.

### 4. Configure Environment Variables

Create a file named `.env` in the root directory for the bot:

```bash
# .env

# Discord
DISCORD_TOKEN=your_discord_bot_token

# Supabase
SUPABASE_URL=https://your-project-id.supabase.co
SUPABASE_SERVICE_ROLE_KEY=your_supabase_service_role_key

# Hugging Face
HF_API_KEY=hf_your_api_key
HF_MODEL=meta-llama/Llama-3.2-3B-Instruct
HF_EMBED_MODEL=sentence-transformers/all-MiniLM-L6-v2
```

Create a file named `.env.local` in the `admin/` directory for the dashboard:

```bash
# admin/.env.local

NEXT_PUBLIC_SUPABASE_URL=https://your-project-id.supabase.co
NEXT_PUBLIC_SUPABASE_ANON_KEY=your_supabase_anon_public_key
```

### 5. Run the Bot

```bash
# Create and activate a virtual environment
python -m venv .venv
# On Windows: .\.venv\Scripts\activate
# On macOS/Linux: source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Run the bot
python bot.py
```

### 6. Run the Admin Dashboard

```bash
cd admin
npm install
npm run dev
```

Access the dashboard at `http://localhost:3000`. You will need to create an admin user via the Supabase Dashboard: go to **Authentication** → **Users** → **Create user**.

---

## Deployment

### Discord Bot (Railway)

The repository is pre-configured for one-click deployment on Railway using the included `Dockerfile` and `railway.json`.

1.  Fork this repository to your GitHub account.
2.  Create a new project on [Railway](https://railway.app) and deploy from your forked repository.
3.  In the Railway project dashboard, go to **Variables** and add the environment variables from the root `.env` file.

### Admin Dashboard (Vercel)

The admin panel can be easily deployed on Vercel.

1.  Create a new project on [Vercel](https://vercel.com) and import your forked repository.
2.  Set the root directory to `admin`.
3.  Add the environment variables from `admin/.env.local` to the Vercel project settings.

---

## Bot Commands

### Slash Commands

| Command                             | Description                                         | Permission  |
| ----------------------------------- | --------------------------------------------------- | ----------- |
| `/setup`                            | Register as the first Team Lead for the server.     | First user  |
| `/ask <question>`                   | Ask the AI a direct question.                       | Everyone    |
| `/ping`                             | Check the bot's latency.                            | Everyone    |
| `/knowledge_add <title> <content>`  | Add a document to the knowledge base.               | Everyone    |
| `/knowledge_upload <title> <file>`  | Upload a TXT, MD, or PDF file to the knowledge base.  | Everyone    |
| `/knowledge_search <query>`         | Perform a semantic search of the knowledge base.    | Everyone    |
| `/knowledge_list`                   | List all documents in the knowledge base.           | Everyone    |
| `/knowledge_view <title>`           | View the content of a specific document.            | Everyone    |
| `/knowledge_delete <title>`         | Delete a document from the knowledge base.          | Team Lead   |
| `/memory_reset`                     | Clear the conversation memory for this channel.     | Team Lead   |
| `/allowlist_add`                    | Allow the bot to respond in the current channel.    | Team Lead   |
| `/role_assign @user <role>`         | Assign `Team Lead` or `Member` role to a user.      | Team Lead   |
| `/role_remove @user`                | Remove a user's assigned role.                      | Team Lead   |
| `/role_list`                        | View all registered roles in the server.            | Everyone    |
| `/web_search <query>`               | Search the web using DuckDuckGo.                    | Everyone    |
| `/research <topic>`                 | Research a topic using web search and AI summary.   | Everyone    |

### Role-Based Access Control

DasAI uses a two-tier role system to manage permissions:

| Role        | Permissions                                                                    |
| ----------- | ------------------------------------------------------------------------------ |
| **Team Lead** 👑 | Full access: manage knowledge, memory, channels, and assign roles.           |
| **Member**    👤 | Basic access: ask questions, search the knowledge base.                         |

The first user to run `/setup` in a server automatically becomes the **Team Lead** and can then assign roles to others.

---

## Multi-Server Support

DasAI is designed to run on multiple Discord servers simultaneously from a single instance, with data isolation for each server.

-   **Per-Server Configuration**: Each server has its own bot name, system instructions, and channel allowlist.
-   **Isolated Knowledge Base**: Documents added in one server are not accessible in another.
-   **Separate Memory**: Conversation memory is tracked per-channel, within each server.
-   **Independent Roles**: Team Leads and Members are assigned on a per-server basis.

The admin dashboard includes a server selector to manage each Discord server independently.

---

## Admin Dashboard

The Next.js admin dashboard provides a secure web interface for managing your bot:

-   **Configuration**: Edit the bot's name and system instructions (personality).
-   **Channel Management**: Configure which channels the bot responds in.
-   **Knowledge Base**: View, add, and delete RAG documents.
-   **Memory Management**: Monitor and clear conversation summaries for each channel.
-   **Role Management**: View and modify user roles (`Team Lead`, `Member`).
-   **Authentication**: Uses Supabase Auth with email/password and is protected by Row Level Security (RLS) policies.

---

## Project Structure

```
DasAI/
├── bot.py                    # Main Discord bot logic
├── requirements.txt          # Python dependencies
├── Dockerfile                # Image configuration for bot deployment
├── railway.json              # Railway deployment manifest
├── .env.example              # Example environment variables for the bot
│
├── admin/                    # Next.js admin dashboard
│   ├── src/
│   │   ├── app/
│   │   │   ├── dashboard/    # Protected dashboard pages
│   │   │   └── login/        # Authentication UI
│   │   └── lib/
│   │       └── supabase/     # Supabase client utilities
│   ├── .env.local.example    # Example environment variables for the dashboard
│   └── package.json
│
└── database/
    └── schema.sql            # PostgreSQL schema with tables, indexes, and RLS
```

---

## Development Notes

### Design Decisions

-   **Hugging Face over OpenAI**: Utilizes the HF Inference API for access to a wide variety of open-source models and cost-effectiveness.
-   **Supabase over Self-Hosted DB**: Leverages Supabase's integrated PostgreSQL, pgvector extension, authentication, and RLS for a streamlined backend.
-   **Next.js with App Router**: Employs modern React patterns, including Server Components and Server Actions, for an efficient and secure admin panel.
-   **`discord.py` Asynchronous Core**: Built on an async framework to handle concurrent Discord events efficiently without blocking.

### Key Implementation Details

-   **Embedding Model**: Uses `sentence-transformers/all-MiniLM-L6-v2` by default, generating 384-dimensional vectors.
-   **Memory Strategy**: Implements a rolling summary approach, condensing the conversation every 5 messages to maintain context without exceeding token limits.
-   **Security**: The bot uses a `service_role` key for full backend access, while the admin dashboard uses a public `anon` key, with data access controlled by RLS policies. Environment variables are kept out of version control.

---

## Contributing

1.  Fork the repository.
2.  Create a feature branch (`git checkout -b feature/new-feature`).
3.  Commit your changes (`git commit -m 'Add some new feature'`).
4.  Push to the branch (`git push origin feature/new-feature`).
5.  Open a Pull Request.

---

## License

This project is licensed under the MIT License.