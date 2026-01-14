import discord
from discord.ext import commands
from discord import app_commands
import os
import sys
import asyncio
from dotenv import load_dotenv
from typing import Optional, Any, Dict, List
from supabase import create_client, Client
from huggingface_hub import InferenceClient

# Load environment variables
load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')
SUPABASE_URL = os.getenv('SUPABASE_URL')
SUPABASE_KEY = os.getenv('SUPABASE_SERVICE_ROLE_KEY')

# Hugging Face Configuration
HF_API_KEY = os.getenv('HF_API_KEY')
HF_MODEL = os.getenv('HF_MODEL', 'meta-llama/Llama-3.2-3B-Instruct')
HF_EMBED_MODEL = os.getenv('HF_EMBED_MODEL', 'sentence-transformers/all-MiniLM-L6-v2')

# Initialize clients
supabase: Optional[Client] = create_client(SUPABASE_URL, SUPABASE_KEY) if SUPABASE_URL and SUPABASE_KEY else None
hf_client: Optional[InferenceClient] = InferenceClient(token=HF_API_KEY) if HF_API_KEY else None
hf_available = False
embedding_available = False

def _sync_chat_test():
    """Synchronous wrapper for chat test."""
    assert hf_client is not None
    return hf_client.chat_completion(
        messages=[{'role': 'user', 'content': 'Hi'}],
        model=HF_MODEL,
        max_tokens=5
    )


def _sync_embed_test():
    """Synchronous wrapper for embed test."""
    assert hf_client is not None
    return hf_client.feature_extraction(
        text='test',
        model=HF_EMBED_MODEL
    )


async def check_hf_api():
    """Check if Hugging Face API is available."""
    global hf_available, embedding_available
    
    if not HF_API_KEY or not hf_client:
        print('HF_API_KEY not set. AI features disabled.')
        return
    
    try:
        # Test chat model using official SDK
        loop = asyncio.get_event_loop()
        response = await loop.run_in_executor(None, _sync_chat_test)
        if response and response.choices:
            hf_available = True
            print(f'Hugging Face API connected - Model: {HF_MODEL}')
        else:
            print(f'Hugging Face API error: No response from model')
            
    except Exception as e:
        print(f'Hugging Face chat API error: {e}')
    
    try:
        # Test embedding model
        loop = asyncio.get_event_loop()
        embed_response = await loop.run_in_executor(None, _sync_embed_test)
        if embed_response is not None:
            embedding_available = True
            print(f'Embedding model available: {HF_EMBED_MODEL}')
        else:
            print(f'Embedding model not available. RAG disabled.')
                
    except Exception as e:
        print(f'Embedding API error: {e}')
        print('RAG features disabled.')


def _sync_chat(messages: list, model: str) -> Any:
    """Synchronous wrapper for chat completion."""
    assert hf_client is not None
    return hf_client.chat_completion(
        messages=messages,
        model=model,
        max_tokens=1000,
        temperature=0.7
    )


def _sync_embed(text: str) -> Any:
    """Synchronous wrapper for embedding."""
    assert hf_client is not None
    return hf_client.feature_extraction(
        text=text,
        model=HF_EMBED_MODEL
    )


async def hf_chat(messages: list, model: Optional[str] = None) -> str:
    """Send chat request to Hugging Face Inference API using official SDK."""
    if not hf_available or not hf_client:
        return "AI is not configured. Please set HF_API_KEY."
    
    model = model or HF_MODEL
    
    try:
        # Run synchronous HF client in executor to not block event loop
        loop = asyncio.get_event_loop()
        response = await loop.run_in_executor(
            None,
            lambda: _sync_chat(messages, model)
        )
        
        if response and response.choices and len(response.choices) > 0:
            return response.choices[0].message.content or 'No response generated.'
        return 'No response generated.'
            
    except Exception as e:
        print(f'Hugging Face error: {e}')
        return f"Error: {str(e)}"


async def hf_embed(text: str) -> Optional[List[float]]:
    """Generate embeddings using Hugging Face official SDK."""
    if not embedding_available or not hf_client:
        return None
    
    try:
        loop = asyncio.get_event_loop()
        data = await loop.run_in_executor(
            None,
            lambda: _sync_embed(text)
        )
        
        # Handle numpy array return format
        if data is not None:
            # Convert numpy array to list
            if hasattr(data, 'tolist'):
                result = data.tolist()
                # If it's already a flat list, return it
                if isinstance(result, list) and len(result) > 0:
                    if not isinstance(result[0], list):
                        return result
                    # If nested, take first element
                    return result[0]
            # If it's already a list
            if isinstance(data, list):
                return data
        return None
    except Exception as e:
        print(f'Embedding error: {e}')
        return None


async def search_knowledge_base(guild_id: str, query: str, match_count: int = 3) -> List[Dict[str, Any]]:
    """Search knowledge base for relevant documents using semantic search (per-guild)."""
    if not supabase or not embedding_available:
        return []
    
    # Generate embedding for the query
    query_embedding = await hf_embed(query)
    if not query_embedding:
        return []
    
    try:
        # Call the similarity search function with guild_id
        result = supabase.rpc('search_documents', {
            'p_guild_id': guild_id,
            'query_embedding': query_embedding,
            'match_threshold': 0.5,
            'match_count': match_count
        }).execute()
        
        if result.data and isinstance(result.data, list):
            return [dict(row) for row in result.data]  # type: ignore
    except Exception as e:
        print(f'Knowledge search error: {e}')
    
    return []


async def add_document_to_knowledge_base(guild_id: str, title: str, content: str, filename: Optional[str] = None) -> bool:
    """Add a document to the knowledge base with embedding (per-guild)."""
    if not supabase:
        return False
    
    # Split content into chunks if too long (max ~500 tokens per chunk)
    max_chunk_size = 2000  # characters
    chunks = []
    
    if len(content) > max_chunk_size:
        # Simple chunking by paragraphs
        paragraphs = content.split('\n\n')
        current_chunk = ""
        
        for para in paragraphs:
            if len(current_chunk) + len(para) < max_chunk_size:
                current_chunk += para + "\n\n"
            else:
                if current_chunk:
                    chunks.append(current_chunk.strip())
                current_chunk = para + "\n\n"
        
        if current_chunk:
            chunks.append(current_chunk.strip())
    else:
        chunks = [content]
    
    try:
        for i, chunk in enumerate(chunks):
            # Generate embedding for the chunk
            embedding = await hf_embed(chunk) if embedding_available else None
            
            doc_data: Dict[str, Any] = {
                'guild_id': guild_id,
                'title': f"{title}" if len(chunks) == 1 else f"{title} (Part {i+1})",
                'filename': filename,
                'content': chunk,
                'chunk_index': i,
                'metadata': {'total_chunks': len(chunks)}
            }
            
            if embedding:
                doc_data['embedding'] = embedding
            
            supabase.table('knowledge_documents').insert(doc_data).execute()
        
        return True
    except Exception as e:
        print(f'Error adding document: {e}')
        return False

# Bot setup with intents
intents = discord.Intents.default()
intents.message_content = True
intents.members = True

bot = commands.Bot(command_prefix='!', intents=intents)

# Cache for bot configuration per guild
guild_config_cache: Dict[str, Dict[str, Any]] = {}  # guild_id -> config

# Role cache per guild
role_cache: Dict[str, Dict[str, str]] = {}  # guild_id -> {user_id -> role}


def get_default_config() -> Dict[str, Any]:
    """Return default configuration for a new guild."""
    return {
        'system_instructions': 'You are a helpful AI assistant for a Discord server. Be friendly, concise, and helpful.',
        'allowed_channels': [],
        'bot_name': 'DasAI Assistant'
    }


async def get_user_role(guild_id: str, user_id: str) -> Optional[str]:
    """Get a user's role from the database."""
    if not supabase:
        print(f'get_user_role: supabase not configured')
        return None
    
    # Check cache first
    if guild_id in role_cache and user_id in role_cache[guild_id]:
        cached_role = role_cache[guild_id][user_id]
        print(f'get_user_role: Cache hit for {user_id} in guild {guild_id}: {cached_role}')
        return cached_role
    
    try:
        print(f'get_user_role: Querying DB for user_id={user_id}, guild_id={guild_id}')
        result = supabase.table('user_roles').select('role').eq('guild_id', guild_id).eq('user_id', user_id).limit(1).execute()
        print(f'get_user_role: DB result: {result.data}')
        if result.data:
            row: Dict[str, Any] = dict(result.data[0])  # type: ignore
            role = str(row.get('role', 'member'))
            if guild_id not in role_cache:
                role_cache[guild_id] = {}
            role_cache[guild_id][user_id] = role
            print(f'get_user_role: Found role {role} for user {user_id}')
            return role
        else:
            print(f'get_user_role: No role found for user {user_id} in guild {guild_id}')
    except Exception as e:
        print(f'Error fetching user role: {e}')
    
    return None


async def set_user_role(guild_id: str, user_id: str, username: str, role: str) -> bool:
    """Set a user's role in the database."""
    if not supabase:
        print('set_user_role: supabase not configured')
        return False
    
    try:
        print(f'set_user_role: Upserting {username} ({user_id}) as {role} in guild {guild_id}')
        result = supabase.table('user_roles').upsert({
            'guild_id': guild_id,
            'user_id': user_id,
            'username': username,
            'role': role
        }, on_conflict='guild_id,user_id').execute()
        
        print(f'set_user_role: Upsert result: {result}')
        
        # Update cache
        if guild_id not in role_cache:
            role_cache[guild_id] = {}
        role_cache[guild_id][user_id] = role
        return True
    except Exception as e:
        print(f'set_user_role: Error - {e}')
        return False


async def is_team_lead(guild_id: str, user_id: str) -> bool:
    """Check if a user is a team lead."""
    role = await get_user_role(guild_id, user_id)
    is_lead = role == 'team_lead'
    print(f'is_team_lead: user_id={user_id}, guild_id={guild_id}, role={role}, is_lead={is_lead}')
    return is_lead


async def remove_user_role(guild_id: str, user_id: str) -> bool:
    """Remove a user's role from the database."""
    if not supabase:
        return False
    
    try:
        supabase.table('user_roles').delete().eq('guild_id', guild_id).eq('user_id', user_id).execute()
        
        # Update cache
        if guild_id in role_cache and user_id in role_cache[guild_id]:
            del role_cache[guild_id][user_id]
        return True
    except Exception as e:
        print(f'Error removing user role: {e}')
        return False


async def has_any_team_lead(guild_id: str) -> bool:
    """Check if the guild has any team lead registered."""
    if not supabase:
        print('has_any_team_lead: supabase not configured')
        return False
    
    try:
        print(f'has_any_team_lead: Checking guild_id={guild_id}')
        result = supabase.table('user_roles').select('id').eq('guild_id', guild_id).eq('role', 'team_lead').limit(1).execute()
        has_lead = bool(result.data)
        print(f'has_any_team_lead: result={result.data}, has_lead={has_lead}')
        return has_lead
    except Exception as e:
        print(f'has_any_team_lead: Error - {e}')
        return False


async def get_guild_roles(guild_id: str) -> List[Dict[str, Any]]:
    """Get all user roles for a guild."""
    if not supabase:
        return []
    
    try:
        result = supabase.table('user_roles').select('*').eq('guild_id', guild_id).order('created_at').execute()
        if result.data:
            return [dict(row) for row in result.data]  # type: ignore
        return []
    except Exception as e:
        print(f'Error fetching guild roles: {e}')
        return []


async def fetch_bot_config(guild_id: str, guild_name: Optional[str] = None) -> Dict[str, Any]:
    """Fetch bot configuration for a specific guild from Supabase."""
    if not supabase:
        return get_default_config()
    
    # Check cache first
    if guild_id in guild_config_cache:
        return guild_config_cache[guild_id]
    
    try:
        result = supabase.table('bot_config').select('*').eq('guild_id', guild_id).limit(1).execute()
        if result.data:
            config: Dict[str, Any] = dict(result.data[0])  # type: ignore
            guild_config_cache[guild_id] = {
                'system_instructions': str(config.get('system_instructions', '')),
                'allowed_channels': list(config.get('allowed_channels', [])),
                'bot_name': str(config.get('bot_name', 'DasAI Assistant'))
            }
            return guild_config_cache[guild_id]
        else:
            # Create default config for this guild
            default_config = get_default_config()
            supabase.table('bot_config').insert({
                'guild_id': guild_id,
                'guild_name': guild_name,
                'bot_name': default_config['bot_name'],
                'system_instructions': default_config['system_instructions'],
                'allowed_channels': default_config['allowed_channels']
            }).execute()
            guild_config_cache[guild_id] = default_config
            return default_config
    except Exception as e:
        print(f'Error fetching config: {e}')
    
    return get_default_config()


async def get_conversation_memory(guild_id: str, channel_id: str) -> str:
    """Get conversation summary for a channel in a guild."""
    if not supabase:
        return ''
    
    try:
        result = supabase.table('conversation_memory').select('summary').eq('guild_id', guild_id).eq('channel_id', channel_id).limit(1).execute()
        if result.data:
            row: Dict[str, Any] = dict(result.data[0])  # type: ignore
            return str(row.get('summary', ''))
    except Exception as e:
        print(f'Error fetching memory: {e}')
    
    return ''


async def update_conversation_memory(guild_id: str, channel_id: str, new_message: str, bot_response: str):
    """Update conversation memory with new exchange."""
    if not supabase or not hf_available:
        return
    
    try:
        # Get existing memory
        existing = supabase.table('conversation_memory').select('*').eq('guild_id', guild_id).eq('channel_id', channel_id).limit(1).execute()
        
        current_summary: str = ''
        message_count: int = 0
        
        if existing.data:
            row: Dict[str, Any] = dict(existing.data[0])  # type: ignore
            current_summary = str(row.get('summary', ''))
            message_count = int(row.get('message_count', 0))
        
        # Generate updated summary every 5 messages
        if message_count % 5 == 0 and message_count > 0:
            summary_prompt = f"""Previous summary: {current_summary}

Recent exchange:
User: {new_message}
Assistant: {bot_response}

Create a brief updated summary of the conversation so far (max 200 words):"""
            
            current_summary = await hf_chat([{'role': 'user', 'content': summary_prompt}])
        
        # Upsert memory
        supabase.table('conversation_memory').upsert({
            'guild_id': guild_id,
            'channel_id': channel_id,
            'summary': current_summary,
            'message_count': message_count + 1
        }, on_conflict='guild_id,channel_id').execute()
        
    except Exception as e:
        print(f'Error updating memory: {e}')


async def save_message(guild_id: str, channel_id: str, user_id: str, username: str, content: str, bot_response: Optional[str] = None):
    """Save message to database."""
    if not supabase:
        return
    
    try:
        supabase.table('messages').insert({
            'guild_id': guild_id,
            'channel_id': channel_id,
            'user_id': user_id,
            'username': username,
            'content': content,
            'bot_response': bot_response
        }).execute()
    except Exception as e:
        print(f'Error saving message: {e}')


async def generate_ai_response(message: discord.Message, config: dict) -> str:
    """Generate AI response using Hugging Face with RAG context."""
    if not hf_available:
        return "AI is not configured. Please set HF_API_KEY."
    
    guild_id = str(message.guild.id) if message.guild else ''
    channel_id = str(message.channel.id)
    user_query = message.content
    
    # Get conversation memory
    memory = await get_conversation_memory(guild_id, channel_id)
    
    # Search knowledge base for relevant context (RAG)
    knowledge_context = ""
    if embedding_available:
        relevant_docs = await search_knowledge_base(guild_id, user_query, match_count=3)
        if relevant_docs:
            knowledge_context = "\n\n📚 **Relevant Knowledge Base Context:**\n"
            for doc in relevant_docs:
                title = doc.get('title', 'Untitled')
                content = doc.get('content', '')[:500]  # Limit content length
                similarity = doc.get('similarity', 0)
                knowledge_context += f"\n[{title}] (relevance: {similarity:.0%}):\n{content}\n"
    
    # Build system prompt
    system_prompt = config['system_instructions']
    
    if knowledge_context:
        system_prompt += f"\n\nUse the following knowledge base context to help answer questions when relevant:{knowledge_context}"
    
    if memory:
        system_prompt += f"\n\nConversation context:\n{memory}"
    
    # Get recent messages for immediate context
    recent_messages = []
    try:
        async for msg in message.channel.history(limit=10):
            if msg.id != message.id:
                role = 'assistant' if msg.author == bot.user else 'user'
                recent_messages.append({
                    'role': role,
                    'content': f"{msg.author.display_name}: {msg.content}" if role == 'user' else msg.content
                })
        recent_messages.reverse()
    except Exception as e:
        print(f'Error fetching history: {e}')
    
    # Build messages array
    messages = [
        {'role': 'system', 'content': system_prompt}
    ]
    messages.extend(recent_messages[-6:])  # Last 6 messages for context
    messages.append({'role': 'user', 'content': f"{message.author.display_name}: {user_query}"})
    
    return await hf_chat(messages)


@bot.event
async def on_ready():
    """Called when the bot is ready and connected."""
    print(f'{bot.user} has connected to Discord!')
    print(f'Bot is in {len(bot.guilds)} guild(s)')
    
    # Check Hugging Face API connection
    await check_hf_api()
    
    # List connected guilds
    for guild in bot.guilds:
        print(f'  - {guild.name} (ID: {guild.id})')
    
    # Sync slash commands
    try:
        synced = await bot.tree.sync()
        print(f'Synced {len(synced)} command(s)')
    except Exception as e:
        print(f'Failed to sync commands: {e}')


@bot.event
async def on_message(message: discord.Message):
    """Handle incoming messages."""
    # Ignore own messages
    if message.author == bot.user:
        return
    
    # Ignore DMs
    if not message.guild:
        return
    
    # Process commands first
    await bot.process_commands(message)
    
    # Check if this is a command (starts with prefix)
    if message.content.startswith(str(bot.command_prefix)):
        return
    
    guild_id = str(message.guild.id)
    guild_name = message.guild.name
    channel_id = str(message.channel.id)
    
    # Get per-guild config
    config = await fetch_bot_config(guild_id, guild_name)
    
    # Check if channel is allowed or if bot is mentioned
    is_allowed = len(config['allowed_channels']) == 0 or channel_id in config['allowed_channels']
    is_mentioned = bot.user in message.mentions
    
    if not (is_allowed or is_mentioned):
        return
    
    # Generate and send response
    async with message.channel.typing():
        response = await generate_ai_response(message, config)
        
        # Split long responses
        if len(response) > 2000:
            chunks = [response[i:i+2000] for i in range(0, len(response), 2000)]
            for chunk in chunks:
                await message.reply(chunk, mention_author=False)
        else:
            await message.reply(response, mention_author=False)
        
        # Save to database
        await save_message(
            guild_id,
            channel_id,
            str(message.author.id),
            message.author.display_name,
            message.content,
            response
        )
        
        # Update memory
        await update_conversation_memory(guild_id, channel_id, message.content, response)


@bot.event
async def on_member_join(member):
    """Called when a member joins the server."""
    print(f'{member.name} has joined the server!')


# Prefix command example
@bot.command(name='ping')
async def ping(ctx):
    """Check the bot's latency."""
    latency = round(bot.latency * 1000)
    await ctx.send(f'Pong! 🏓 Latency: {latency}ms')


@bot.command(name='reload')
@commands.has_permissions(administrator=True)
async def reload_config(ctx):
    """Reload bot configuration from database."""
    guild_id = str(ctx.guild.id) if ctx.guild else ''
    guild_name = ctx.guild.name if ctx.guild else None
    await fetch_bot_config(guild_id, guild_name)
    await ctx.send('✅ Configuration reloaded!')


@bot.command(name='status')
async def status(ctx):
    """Check bot status and configuration."""
    guild_id = str(ctx.guild.id) if ctx.guild else ''
    guild_name = ctx.guild.name if ctx.guild else None
    config = await fetch_bot_config(guild_id, guild_name)
    embed = discord.Embed(
        title='🤖 DasAI Status',
        color=discord.Color.green() if hf_available else discord.Color.red()
    )
    embed.add_field(name='Bot Name', value=config['bot_name'], inline=True)
    embed.add_field(name='Allowed Channels', value=len(config['allowed_channels']) or 'All', inline=True)
    embed.add_field(name='AI Model', value=HF_MODEL, inline=True)
    embed.add_field(name='Embed Model', value=HF_EMBED_MODEL if embedding_available else 'Not available', inline=True)
    embed.add_field(name='Database', value='✅ Connected' if supabase else '❌ Not configured', inline=True)
    embed.add_field(name='Hugging Face', value='✅ Connected' if hf_available else '❌ Not available', inline=True)
    embed.add_field(name='RAG/Embeddings', value='✅ Enabled' if embedding_available else '❌ Disabled', inline=True)
    await ctx.send(embed=embed)


# Slash command examples
@bot.tree.command(name='ping', description='Check the bot latency')
async def slash_ping(interaction: discord.Interaction):
    """Slash command to check latency."""
    latency = round(bot.latency * 1000)
    await interaction.response.send_message(f'Pong! 🏓 Latency: {latency}ms')


@bot.tree.command(name='ask', description='Ask the AI a question')
@app_commands.describe(question='Your question for the AI')
async def ask(interaction: discord.Interaction, question: str):
    """Slash command to ask the AI a question."""
    await interaction.response.defer()
    
    guild_id = str(interaction.guild_id) if interaction.guild_id else ''
    guild_name = interaction.guild.name if interaction.guild else None
    config = await fetch_bot_config(guild_id, guild_name)
    
    if not hf_available:
        await interaction.followup.send("AI is not configured. Set HF_API_KEY in environment.")
        return
    
    # Search knowledge base for relevant context (per-guild)
    knowledge_context = ""
    if embedding_available:
        relevant_docs = await search_knowledge_base(guild_id, question, match_count=3)
        if relevant_docs:
            knowledge_context = "\n\nRelevant Knowledge:\n"
            for doc in relevant_docs:
                title = doc.get('title', 'Untitled')
                content = doc.get('content', '')[:500]
                knowledge_context += f"[{title}]: {content}\n"
    
    system_prompt = config['system_instructions']
    if knowledge_context:
        system_prompt += f"\n\nUse this context to help answer:{knowledge_context}"
    
    messages = [
        {'role': 'system', 'content': system_prompt},
        {'role': 'user', 'content': question}
    ]
    
    answer = await hf_chat(messages)
    
    if len(answer) > 2000:
        answer = answer[:1997] + '...'
    
    await interaction.followup.send(answer)


@bot.tree.command(name='memory_reset', description='Reset the conversation memory for this channel')
async def memory_reset(interaction: discord.Interaction):
    """Reset the rolling summary and message count for the current channel. Team Lead only."""
    await interaction.response.defer()

    if not supabase:
        await interaction.followup.send("❌ Database not configured.")
        return

    # Check if user is team lead
    guild_id = str(interaction.guild_id) if interaction.guild_id else ''
    user_id = str(interaction.user.id)
    
    if not await is_team_lead(guild_id, user_id):
        await interaction.followup.send("❌ Only Team Leads can reset conversation memory.")
        return

    channel_id = str(interaction.channel_id)
    try:
        # Upsert an empty memory for this channel
        supabase.table('conversation_memory').upsert({
            'guild_id': guild_id,
            'channel_id': channel_id,
            'summary': '',
            'message_count': 0
        }, on_conflict='guild_id,channel_id').execute()

        await interaction.followup.send("✅ Conversation memory reset for this channel.")
    except Exception as e:
        await interaction.followup.send(f"❌ Error: {e}")


@bot.tree.command(name='allowlist_add', description='Allow this channel for bot responses')
async def allowlist_add(interaction: discord.Interaction):
    """Add the current channel to the allow-listed channels in bot_config. Team Lead only."""
    await interaction.response.defer()

    if not supabase:
        await interaction.followup.send("❌ Database not configured.")
        return

    # Check if user is team lead
    guild_id = str(interaction.guild_id) if interaction.guild_id else ''
    user_id = str(interaction.user.id)
    
    if not await is_team_lead(guild_id, user_id):
        await interaction.followup.send("❌ Only Team Leads can modify the allow-list.")
        return

    channel_id = str(interaction.channel_id)
    try:
        # Get this guild's config
        result = supabase.table('bot_config').select('id, allowed_channels').eq('guild_id', guild_id).limit(1).execute()
        if not result.data:
            await interaction.followup.send("❌ No bot configuration found for this server. Run `/setup` first.")
            return

        row: Dict[str, Any] = dict(result.data[0])  # type: ignore
        config_id = str(row.get('id'))
        allowed = list(row.get('allowed_channels') or [])

        if channel_id in allowed:
            await interaction.followup.send("ℹ️ This channel is already allow-listed.")
            return

        allowed.append(channel_id)
        supabase.table('bot_config').update({'allowed_channels': allowed}).eq('id', config_id).execute()
        
        # Update cache
        if guild_id in guild_config_cache:
            guild_config_cache[guild_id]['allowed_channels'] = allowed
            
        await interaction.followup.send("✅ Channel added to allow-list.")
    except Exception as e:
        await interaction.followup.send(f"❌ Error: {e}")


@bot.tree.command(name='setup', description='Register as Team Lead (first user only)')
async def setup(interaction: discord.Interaction):
    """Register the first user as Team Lead for this server."""
    await interaction.response.defer()

    if not supabase:
        await interaction.followup.send("❌ Database not configured.")
        return

    guild_id = str(interaction.guild_id) if interaction.guild_id else ''
    user_id = str(interaction.user.id)
    username = interaction.user.display_name

    # Check if there's already a team lead
    if await has_any_team_lead(guild_id):
        await interaction.followup.send("❌ This server already has a Team Lead. Ask them to add you with `/role_assign`.")
        return

    # Register as team lead
    success = await set_user_role(guild_id, user_id, username, 'team_lead')
    
    if success:
        embed = discord.Embed(
            title='🎉 Setup Complete!',
            description=f'**{username}** is now the Team Lead for this server.',
            color=discord.Color.green()
        )
        embed.add_field(name='What you can do:', value=(
            '• `/role_assign @user` - Add team members\n'
            '• `/role_remove @user` - Remove team members\n'
            '• `/role_list` - View all roles\n'
            '• `/memory_reset` - Clear conversation memory\n'
            '• `/allowlist_add` - Allow bot in this channel\n'
            '• `/knowledge_add` - Add to knowledge base'
        ), inline=False)
        await interaction.followup.send(embed=embed)
    else:
        await interaction.followup.send("❌ Failed to complete setup. Please try again.")


@bot.tree.command(name='role_assign', description='Assign a role to a user (Team Lead only)')
@app_commands.describe(user='The user to assign a role to', role='The role to assign')
@app_commands.choices(role=[
    app_commands.Choice(name='Team Lead', value='team_lead'),
    app_commands.Choice(name='Member', value='member')
])
async def role_assign(interaction: discord.Interaction, user: discord.Member, role: app_commands.Choice[str]):
    """Assign a role to a user. Team Lead only."""
    await interaction.response.defer()

    if not supabase:
        await interaction.followup.send("❌ Database not configured.")
        return

    guild_id = str(interaction.guild_id) if interaction.guild_id else ''
    caller_id = str(interaction.user.id)

    # Check if caller is team lead
    if not await is_team_lead(guild_id, caller_id):
        await interaction.followup.send("❌ Only Team Leads can assign roles.")
        return

    target_id = str(user.id)
    target_name = user.display_name

    success = await set_user_role(guild_id, target_id, target_name, role.value)
    
    if success:
        role_emoji = '👑' if role.value == 'team_lead' else '👤'
        await interaction.followup.send(f"{role_emoji} **{target_name}** is now a **{role.name}**.")
    else:
        await interaction.followup.send("❌ Failed to assign role. Please try again.")


@bot.tree.command(name='role_remove', description='Remove a user\'s role (Team Lead only)')
@app_commands.describe(user='The user to remove')
async def role_remove(interaction: discord.Interaction, user: discord.Member):
    """Remove a user's role from the system. Team Lead only."""
    await interaction.response.defer()

    if not supabase:
        await interaction.followup.send("❌ Database not configured.")
        return

    guild_id = str(interaction.guild_id) if interaction.guild_id else ''
    caller_id = str(interaction.user.id)
    target_id = str(user.id)

    # Check if caller is team lead
    if not await is_team_lead(guild_id, caller_id):
        await interaction.followup.send("❌ Only Team Leads can remove roles.")
        return

    # Prevent removing self if you're the only team lead
    if target_id == caller_id:
        # Check if there are other team leads
        roles = await get_guild_roles(guild_id)
        team_leads = [r for r in roles if r.get('role') == 'team_lead']
        if len(team_leads) <= 1:
            await interaction.followup.send("❌ You can't remove yourself - you're the only Team Lead!")
            return

    success = await remove_user_role(guild_id, target_id)
    
    if success:
        await interaction.followup.send(f"✅ Removed **{user.display_name}** from the role system.")
    else:
        await interaction.followup.send("❌ Failed to remove role. Please try again.")


@bot.tree.command(name='role_list', description='List all users and their roles')
async def role_list(interaction: discord.Interaction):
    """List all users with assigned roles in this server."""
    await interaction.response.defer()

    if not supabase:
        await interaction.followup.send("❌ Database not configured.")
        return

    guild_id = str(interaction.guild_id) if interaction.guild_id else ''
    roles = await get_guild_roles(guild_id)

    if not roles:
        await interaction.followup.send("ℹ️ No roles assigned yet. Use `/setup` to get started.")
        return

    embed = discord.Embed(
        title='👥 Team Roles',
        color=discord.Color.blue()
    )

    team_leads = [r for r in roles if r.get('role') == 'team_lead']
    members = [r for r in roles if r.get('role') == 'member']

    if team_leads:
        lead_list = '\n'.join([f"👑 {r.get('username', 'Unknown')}" for r in team_leads])
        embed.add_field(name='Team Leads', value=lead_list, inline=False)

    if members:
        member_list = '\n'.join([f"👤 {r.get('username', 'Unknown')}" for r in members])
        embed.add_field(name='Members', value=member_list, inline=False)

    embed.set_footer(text=f'Total: {len(roles)} user(s)')
    await interaction.followup.send(embed=embed)


@bot.tree.command(name='knowledge_add', description='Add a document to the knowledge base')
@app_commands.describe(title='Title for the document', content='The content to add')
async def knowledge_add(interaction: discord.Interaction, title: str, content: str):
    """Add a document to the knowledge base. Team Lead only."""
    await interaction.response.defer()
    
    if not supabase:
        await interaction.followup.send("❌ Database not configured.")
        return
    
    # Check if user is team lead
    guild_id = str(interaction.guild_id) if interaction.guild_id else ''
    user_id = str(interaction.user.id)
    
    if not await is_team_lead(guild_id, user_id):
        await interaction.followup.send("❌ Only Team Leads can add to the knowledge base.")
        return
    
    if not embedding_available:
        await interaction.followup.send("⚠️ Embeddings not available. Document will be added without semantic search capability.")
    
    success = await add_document_to_knowledge_base(guild_id, title, content)
    
    if success:
        await interaction.followup.send(f"✅ Added document: **{title}**")
    else:
        await interaction.followup.send(f"❌ Failed to add document.")


@bot.tree.command(name='knowledge_search', description='Search the knowledge base')
@app_commands.describe(query='What to search for')
async def knowledge_search(interaction: discord.Interaction, query: str):
    """Search the knowledge base."""
    await interaction.response.defer()
    
    if not embedding_available:
        await interaction.followup.send("❌ Embeddings not available. Set HF_API_KEY to enable RAG.")
        return
    
    guild_id = str(interaction.guild_id) if interaction.guild_id else ''
    results = await search_knowledge_base(guild_id, query, match_count=5)
    
    if not results:
        await interaction.followup.send("No matching documents found.")
        return
    
    embed = discord.Embed(
        title=f'📚 Search Results for: "{query}"',
        color=discord.Color.blue()
    )
    
    for doc in results:
        title = doc.get('title', 'Untitled')
        content = doc.get('content', '')[:200] + '...' if len(doc.get('content', '')) > 200 else doc.get('content', '')
        similarity = doc.get('similarity', 0)
        embed.add_field(
            name=f"{title} ({similarity:.0%} match)",
            value=content,
            inline=False
        )
    
    await interaction.followup.send(embed=embed)


@bot.tree.command(name='knowledge_list', description='List all documents in the knowledge base')
async def knowledge_list(interaction: discord.Interaction):
    """List all documents in the knowledge base."""
    await interaction.response.defer()
    
    if not supabase:
        await interaction.followup.send("❌ Database not configured.")
        return
    
    guild_id = str(interaction.guild_id) if interaction.guild_id else ''
    
    try:
        result = supabase.table('knowledge_documents').select('id, title, created_at').eq('guild_id', guild_id).order('created_at', desc=True).limit(20).execute()
        
        if not result.data:
            await interaction.followup.send("📚 Knowledge base is empty.")
            return
        
        embed = discord.Embed(
            title='📚 Knowledge Base Documents',
            color=discord.Color.blue()
        )
        
        for row in result.data:
            doc: Dict[str, Any] = dict(row)  # type: ignore
            doc_title = str(doc.get('title', 'Untitled'))
            doc_id = str(doc.get('id', ''))[:8]
            embed.add_field(name=doc_title, value=f"ID: {doc_id}...", inline=False)
        
        await interaction.followup.send(embed=embed)
    except Exception as e:
        await interaction.followup.send(f"❌ Error: {e}")


@bot.tree.command(name='knowledge_delete', description='Delete a document from the knowledge base')
@app_commands.describe(title='Title of the document to delete')
async def knowledge_delete(interaction: discord.Interaction, title: str):
    """Delete a document from the knowledge base. Team Lead only."""
    await interaction.response.defer()
    
    if not supabase:
        await interaction.followup.send("❌ Database not configured.")
        return
    
    # Check if user is team lead
    guild_id = str(interaction.guild_id) if interaction.guild_id else ''
    user_id = str(interaction.user.id)
    
    if not await is_team_lead(guild_id, user_id):
        await interaction.followup.send("❌ Only Team Leads can delete from the knowledge base.")
        return
    
    try:
        result = supabase.table('knowledge_documents').delete().eq('guild_id', guild_id).ilike('title', f'%{title}%').execute()
        
        if result.data:
            count = len(result.data)
            await interaction.followup.send(f"✅ Deleted {count} document(s) matching: **{title}**")
        else:
            await interaction.followup.send(f"❌ No documents found matching: **{title}**")
    except Exception as e:
        await interaction.followup.send(f"❌ Error: {e}")


# Error handling
@bot.event
async def on_command_error(ctx, error):
    """Handle command errors."""
    if isinstance(error, commands.CommandNotFound):
        pass  # Ignore command not found
    elif isinstance(error, commands.MissingPermissions):
        await ctx.send('You do not have permission to use this command.')
    elif isinstance(error, commands.MissingRequiredArgument):
        await ctx.send(f'Missing required argument: {error.param.name}')
    else:
        await ctx.send(f'An error occurred: {error}')
        print(f'Error: {error}')


# Run the bot
if __name__ == '__main__':
    if TOKEN is None:
        print('Error: DISCORD_TOKEN not found in environment variables.')
        print('Please create a .env file with your bot token.')
    else:
        bot.run(TOKEN)
