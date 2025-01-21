from discord.ext import commands
from riot_api.riot_client import RiotAPIClient

class CustomCommands(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.riot_client = RiotAPIClient()

    @commands.command(name='ping')
    async def ping(self, ctx):
        await ctx.send('Pong!')

async def setup(bot):
    await bot.add_cog(CustomCommands(bot))
