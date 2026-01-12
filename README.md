# Discord Bot Template

A simple Discord bot template using discord.py with both prefix commands and slash commands.

## Setup

### 1. Create a Discord Application

1. Go to the [Discord Developer Portal](https://discord.com/developers/applications)
2. Click "New Application" and give it a name
3. Go to the "Bot" section and click "Add Bot"
4. Copy the bot token

### 2. Configure the Bot

1. Copy `.env.example` to `.env`
2. Paste your bot token in the `.env` file

```
DISCORD_TOKEN=your_bot_token_here
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

### 4. Invite the Bot to Your Server

1. Go to the "OAuth2" > "URL Generator" section in the Developer Portal
2. Select the following scopes:
   - `bot`
   - `applications.commands`
3. Select the bot permissions you need (Administrator for testing, or specific permissions for production)
4. Copy the generated URL and open it in your browser
5. Select your server and authorize the bot

### 5. Run the Bot

```bash
python bot.py
```

## Features

### Prefix Commands (!)

- `!ping` - Check bot latency
- `!hello` - Get a greeting from the bot
- `!help` - Show all available commands

### Slash Commands (/)

- `/ping` - Check bot latency
- `/say <message>` - Make the bot say something
- `/userinfo [member]` - Get information about a user

## Project Structure

```
DasAI/
├── bot.py              # Main bot file
├── requirements.txt    # Python dependencies
├── .env.example        # Example environment variables
├── .env                # Your actual environment variables (create this)
└── README.md           # This file
```

## Adding More Commands

### Prefix Command Example

```python
@bot.command(name='greet')
async def greet(ctx, name: str):
    await ctx.send(f'Hello, {name}!')
```

### Slash Command Example

```python
@bot.tree.command(name='greet', description='Greet someone')
@app_commands.describe(name='The name to greet')
async def greet(interaction: discord.Interaction, name: str):
    await interaction.response.send_message(f'Hello, {name}!')
```

## Resources

- [discord.py Documentation](https://discordpy.readthedocs.io/)
- [Discord Developer Portal](https://discord.com/developers/applications)
- [Discord API Documentation](https://discord.com/developers/docs/intro)
