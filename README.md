# DasAI - Discord Copilot

An admin-controlled AI Discord bot with a web dashboard for managing system instructions, allowed channels, and conversation memory.

## Architecture

```
DasAI/
├── bot.py                    # Discord bot (Python)
├── requirements.txt          # Python dependencies
├── .env                      # Bot environment variables
├── admin/                    # Next.js Admin Dashboard
│   ├── src/
│   │   ├── app/
│   │   │   ├── dashboard/    # Main admin interface
│   │   │   └── login/        # Authentication
│   │   └── lib/
│   │       └── supabase/     # Database client
│   └── package.json
└── database/
    └── schema.sql            # Supabase database schema
```

## Features

### Admin Dashboard
- **System Instructions**: Configure the bot's personality, tone, and rules
- **Allowed Channels**: Control which Discord channels the bot responds in
- **Memory Control**: View and reset conversation summaries
- **Authentication**: Secure login via Supabase Auth

### Discord Bot
- **AI Responses**: Powered by OpenAI (GPT-4o-mini by default)
- **Context Awareness**: Uses conversation memory and recent messages
- **Channel Filtering**: Only responds in admin-configured channels
- **Slash Commands**: `/ping`, `/ask`
- **Prefix Commands**: `!ping`, `!reload`, `!status`

## Setup

### 1. Supabase Setup

1. Create a new project at [supabase.com](https://supabase.com)
2. Go to SQL Editor and run the contents of `database/schema.sql`
3. Go to Authentication → Users and create an admin user
4. Copy your project URL and keys from Settings → API

### 2. Discord Bot Setup

1. Create a bot at [Discord Developer Portal](https://discord.com/developers/applications)
2. Enable these Privileged Gateway Intents:
   - Server Members Intent
   - Message Content Intent
3. Generate an invite URL with `bot` + `applications.commands` scopes
4. Configure environment:

```bash
# Copy example and fill in values
cp .env.example .env
```

```env
DISCORD_TOKEN=your_discord_bot_token
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_SERVICE_KEY=your_service_role_key
OPENAI_API_KEY=your_openai_api_key
OPENAI_MODEL=gpt-4o-mini
```

5. Install and run:

```bash
pip install -r requirements.txt
python bot.py
```

### 3. Admin Dashboard Setup

```bash
cd admin

# Install dependencies
npm install

# Configure environment
cp .env.local.example .env.local
```

```env
NEXT_PUBLIC_SUPABASE_URL=https://your-project.supabase.co
NEXT_PUBLIC_SUPABASE_ANON_KEY=your_anon_key
```

```bash
# Run development server
npm run dev

# Or build for production
npm run build
npm start
```

### 4. Deploy to Vercel

```bash
cd admin
npx vercel
```

## Bot Commands

| Command | Description |
|---------|-------------|
| `/ping` | Check bot latency |
| `/ask <question>` | Ask the AI a question |
| `!ping` | Check bot latency |
| `!status` | View bot configuration status |
| `!reload` | Reload config from database (admin only) |

## How It Works

1. **Admin configures** the bot via the web dashboard
2. **Configuration is stored** in Supabase
3. **Bot fetches config** and responds accordingly
4. **Conversations are summarized** and stored for context
5. **AI generates responses** using system instructions + memory

## Optional: RAG System

To implement knowledge base retrieval:

1. Enable the `vector` extension in Supabase
2. Upload PDFs via the admin dashboard
3. Use embeddings to find relevant content
4. Include in AI prompts

The schema already includes a `knowledge_documents` table with vector support.

## Resources

- [discord.py Documentation](https://discordpy.readthedocs.io/)
- [Supabase Documentation](https://supabase.com/docs)
- [Next.js Documentation](https://nextjs.org/docs)
- [OpenAI API](https://platform.openai.com/docs)
