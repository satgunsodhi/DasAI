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


async def search_knowledge_base(query: str, match_count: int = 3) -> List[Dict[str, Any]]:
    """Search knowledge base for relevant documents using semantic search."""
    if not supabase or not embedding_available:
        return []
    
    # Generate embedding for the query
    query_embedding = await hf_embed(query)
    if not query_embedding:
        return []
    
    try:
        # Call the similarity search function
        result = supabase.rpc('search_documents', {
            'query_embedding': query_embedding,
            'match_threshold': 0.5,
            'match_count': match_count
        }).execute()
        
        if result.data and isinstance(result.data, list):
            return [dict(row) for row in result.data]  # type: ignore
    except Exception as e:
        print(f'Knowledge search error: {e}')
    
    return []


async def add_document_to_knowledge_base(title: str, content: str, filename: Optional[str] = None) -> bool:
    """Add a document to the knowledge base with embedding."""
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

# Cache for bot configuration
bot_config_cache = {
    'system_instructions': 'You are a helpful AI assistant.',
    'allowed_channels': [],
    'bot_name': 'DasAI Assistant',
    'last_fetch': 0
}


async def fetch_bot_config():
    """Fetch bot configuration from Supabase."""
    if not supabase:
        return bot_config_cache
    
    try:
        result = supabase.table('bot_config').select('*').limit(1).execute()
        if result.data:
            config: Dict[str, Any] = dict(result.data[0])  # type: ignore
            bot_config_cache['system_instructions'] = str(config.get('system_instructions', ''))
            bot_config_cache['allowed_channels'] = list(config.get('allowed_channels', []))
            bot_config_cache['bot_name'] = str(config.get('bot_name', 'DasAI Assistant'))
    except Exception as e:
        print(f'Error fetching config: {e}')
    
    return bot_config_cache


async def get_conversation_memory(channel_id: str) -> str:
    """Get conversation summary for a channel."""
    if not supabase:
        return ''
    
    try:
        result = supabase.table('conversation_memory').select('summary').eq('channel_id', channel_id).limit(1).execute()
        if result.data:
            row: Dict[str, Any] = dict(result.data[0])  # type: ignore
            return str(row.get('summary', ''))
    except Exception as e:
        print(f'Error fetching memory: {e}')
    
    return ''


async def update_conversation_memory(channel_id: str, new_message: str, bot_response: str):
    """Update conversation memory with new exchange."""
    if not supabase or not hf_available:
        return
    
    try:
        # Get existing memory
        existing = supabase.table('conversation_memory').select('*').eq('channel_id', channel_id).limit(1).execute()
        
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
            'channel_id': channel_id,
            'summary': current_summary,
            'message_count': message_count + 1
        }, on_conflict='channel_id').execute()
        
    except Exception as e:
        print(f'Error updating memory: {e}')


async def save_message(channel_id: str, user_id: str, username: str, content: str, bot_response: Optional[str] = None):
    """Save message to database."""
    if not supabase:
        return
    
    try:
        supabase.table('messages').insert({
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
    
    channel_id = str(message.channel.id)
    user_query = message.content
    
    # Get conversation memory
    memory = await get_conversation_memory(channel_id)
    
    # Search knowledge base for relevant context (RAG)
    knowledge_context = ""
    if embedding_available:
        relevant_docs = await search_knowledge_base(user_query, match_count=3)
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
    
    # Fetch initial config
    await fetch_bot_config()
    channels_count = len(bot_config_cache["allowed_channels"])
    print(f'Loaded config - Allowed channels: {"All" if channels_count == 0 else channels_count}')
    
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
    
    # Refresh config periodically
    config = await fetch_bot_config()
    
    channel_id = str(message.channel.id)
    
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
            channel_id,
            str(message.author.id),
            message.author.display_name,
            message.content,
            response
        )
        
        # Update memory
        await update_conversation_memory(channel_id, message.content, response)


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
    await fetch_bot_config()
    await ctx.send('✅ Configuration reloaded!')


@bot.command(name='status')
async def status(ctx):
    """Check bot status and configuration."""
    config = bot_config_cache
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
    
    config = await fetch_bot_config()
    
    if not hf_available:
        await interaction.followup.send("AI is not configured. Set HF_API_KEY in environment.")
        return
    
    # Search knowledge base for relevant context
    knowledge_context = ""
    if embedding_available:
        relevant_docs = await search_knowledge_base(question, match_count=3)
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


@bot.tree.command(name='knowledge_add', description='Add a document to the knowledge base')
@app_commands.describe(title='Title for the document', content='The content to add')
async def knowledge_add(interaction: discord.Interaction, title: str, content: str):
    """Add a document to the knowledge base."""
    await interaction.response.defer()
    
    if not supabase:
        await interaction.followup.send("❌ Database not configured.")
        return
    
    if not embedding_available:
        await interaction.followup.send("⚠️ Embeddings not available. Document will be added without semantic search capability.")
    
    success = await add_document_to_knowledge_base(title, content)
    
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
        await interaction.followup.send("❌ Embeddings not available. Run `ollama pull nomic-embed-text` to enable RAG.")
        return
    
    results = await search_knowledge_base(query, match_count=5)
    
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
    
    try:
        result = supabase.table('knowledge_documents').select('id, title, created_at').order('created_at', desc=True).limit(20).execute()
        
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
    """Delete a document from the knowledge base."""
    await interaction.response.defer()
    
    if not supabase:
        await interaction.followup.send("❌ Database not configured.")
        return
    
    try:
        result = supabase.table('knowledge_documents').delete().ilike('title', f'%{title}%').execute()
        
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
