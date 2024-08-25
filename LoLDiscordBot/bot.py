import discord
from discord.ext import commands
import os
from dotenv import load_dotenv
from config import DISCORD_TOKEN

load_dotenv()

intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(command_prefix='!', intents=intents)

@bot.event
async def on_ready():
    # Load cogs (extensions) asynchronously
    try:
        await bot.load_extension('cogs.match_tracking')
        print("Loaded match_tracking cog.")
    except Exception as e:
        print(f"Failed to load match_tracking cog: {e}")

    try:
        await bot.load_extension('cogs.commands')
        print("Loaded commands cog.")
    except Exception as e:
        print(f"Failed to load commands cog: {e}")

    print(f'Logged in as {bot.user}')

bot.run(DISCORD_TOKEN)
