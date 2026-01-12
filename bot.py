import discord
from discord.ext import commands
from discord import app_commands
import os
import asyncio
from dotenv import load_dotenv
from supabase import create_client, Client
from openai import AsyncOpenAI

# Load environment variables
load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')
SUPABASE_URL = os.getenv('SUPABASE_URL')
SUPABASE_KEY = os.getenv('SUPABASE_SECRET_KEY')
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')
OPENAI_MODEL = os.getenv('OPENAI_MODEL', 'gpt-4o-mini')

# Initialize clients
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY) if SUPABASE_URL and SUPABASE_KEY else None
openai_client = AsyncOpenAI(api_key=OPENAI_API_KEY) if OPENAI_API_KEY else None

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
            config = result.data[0]
            bot_config_cache['system_instructions'] = config.get('system_instructions', '')
            bot_config_cache['allowed_channels'] = config.get('allowed_channels', [])
            bot_config_cache['bot_name'] = config.get('bot_name', 'DasAI Assistant')
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
            return result.data[0].get('summary', '')
    except Exception as e:
        print(f'Error fetching memory: {e}')
    
    return ''


async def update_conversation_memory(channel_id: str, new_message: str, bot_response: str):
    """Update conversation memory with new exchange."""
    if not supabase or not openai_client:
        return
    
    try:
        # Get existing memory
        existing = supabase.table('conversation_memory').select('*').eq('channel_id', channel_id).limit(1).execute()
        
        current_summary = ''
        message_count = 0
        
        if existing.data:
            current_summary = existing.data[0].get('summary', '')
            message_count = existing.data[0].get('message_count', 0)
        
        # Generate updated summary every 5 messages
        if message_count % 5 == 0 and message_count > 0:
            summary_prompt = f"""Previous summary: {current_summary}

Recent exchange:
User: {new_message}
Assistant: {bot_response}

Create a brief updated summary of the conversation so far (max 200 words):"""
            
            response = await openai_client.chat.completions.create(
                model=OPENAI_MODEL,
                messages=[{'role': 'user', 'content': summary_prompt}],
                max_tokens=300
            )
            current_summary = response.choices[0].message.content
        
        # Upsert memory
        supabase.table('conversation_memory').upsert({
            'channel_id': channel_id,
            'summary': current_summary,
            'message_count': message_count + 1
        }, on_conflict='channel_id').execute()
        
    except Exception as e:
        print(f'Error updating memory: {e}')


async def save_message(channel_id: str, user_id: str, username: str, content: str, bot_response: str = None):
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
    """Generate AI response using OpenAI."""
    if not openai_client:
        return "AI is not configured. Please set up the OpenAI API key."
    
    channel_id = str(message.channel.id)
    
    # Get conversation memory
    memory = await get_conversation_memory(channel_id)
    
    # Build system prompt
    system_prompt = config['system_instructions']
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
    messages.append({'role': 'user', 'content': f"{message.author.display_name}: {message.content}"})
    
    try:
        response = await openai_client.chat.completions.create(
            model=OPENAI_MODEL,
            messages=messages,
            max_tokens=1000,
            temperature=0.7
        )
        return response.choices[0].message.content
    except Exception as e:
        print(f'Error generating response: {e}')
        return f"Sorry, I encountered an error: {str(e)}"


@bot.event
async def on_ready():
    """Called when the bot is ready and connected."""
    print(f'{bot.user} has connected to Discord!')
    print(f'Bot is in {len(bot.guilds)} guild(s)')
    
    # Fetch initial config
    await fetch_bot_config()
    print(f'Loaded config - Allowed channels: {len(bot_config_cache["allowed_channels"])}')
    
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
    if message.content.startswith(bot.command_prefix):
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
        color=discord.Color.green()
    )
    embed.add_field(name='Bot Name', value=config['bot_name'], inline=True)
    embed.add_field(name='Allowed Channels', value=len(config['allowed_channels']) or 'All', inline=True)
    embed.add_field(name='AI Model', value=OPENAI_MODEL, inline=True)
    embed.add_field(name='Database', value='✅ Connected' if supabase else '❌ Not configured', inline=True)
    embed.add_field(name='OpenAI', value='✅ Connected' if openai_client else '❌ Not configured', inline=True)
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
    
    if not openai_client:
        await interaction.followup.send("AI is not configured.")
        return
    
    try:
        response = await openai_client.chat.completions.create(
            model=OPENAI_MODEL,
            messages=[
                {'role': 'system', 'content': config['system_instructions']},
                {'role': 'user', 'content': question}
            ],
            max_tokens=1000
        )
        answer = response.choices[0].message.content
        
        if len(answer) > 2000:
            answer = answer[:1997] + '...'
        
        await interaction.followup.send(answer)
    except Exception as e:
        await interaction.followup.send(f"Error: {str(e)}")


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
