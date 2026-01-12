import discord
from discord.ext import commands
from discord import app_commands
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')

# Bot setup with intents
intents = discord.Intents.default()
intents.message_content = True
intents.members = True

bot = commands.Bot(command_prefix='!', intents=intents)


@bot.event
async def on_ready():
    """Called when the bot is ready and connected."""
    print(f'{bot.user} has connected to Discord!')
    print(f'Bot is in {len(bot.guilds)} guild(s)')
    
    # Sync slash commands
    try:
        synced = await bot.tree.sync()
        print(f'Synced {len(synced)} command(s)')
    except Exception as e:
        print(f'Failed to sync commands: {e}')


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


@bot.command(name='hello')
async def hello(ctx):
    """Say hello to the user."""
    await ctx.send(f'Hello, {ctx.author.mention}! 👋')


# Slash command examples
@bot.tree.command(name='ping', description='Check the bot latency')
async def slash_ping(interaction: discord.Interaction):
    """Slash command to check latency."""
    latency = round(bot.latency * 1000)
    await interaction.response.send_message(f'Pong! 🏓 Latency: {latency}ms')


@bot.tree.command(name='say', description='Make the bot say something')
@app_commands.describe(message='The message you want the bot to say')
async def say(interaction: discord.Interaction, message: str):
    """Slash command to make the bot repeat a message."""
    await interaction.response.send_message(message)


@bot.tree.command(name='userinfo', description='Get information about a user')
@app_commands.describe(member='The member to get info about')
async def userinfo(interaction: discord.Interaction, member: discord.Member = None):
    """Slash command to display user information."""
    member = member or interaction.user
    
    embed = discord.Embed(
        title=f'User Info - {member.name}',
        color=member.color
    )
    embed.set_thumbnail(url=member.display_avatar.url)
    embed.add_field(name='ID', value=member.id, inline=True)
    embed.add_field(name='Nickname', value=member.nick or 'None', inline=True)
    embed.add_field(name='Joined Server', value=member.joined_at.strftime('%Y-%m-%d'), inline=True)
    embed.add_field(name='Account Created', value=member.created_at.strftime('%Y-%m-%d'), inline=True)
    
    await interaction.response.send_message(embed=embed)


# Error handling
@bot.event
async def on_command_error(ctx, error):
    """Handle command errors."""
    if isinstance(error, commands.CommandNotFound):
        await ctx.send('Command not found. Use `!help` to see available commands.')
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
