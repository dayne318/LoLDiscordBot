from discord.ext import commands
from riot_api.riot_client import RiotAPIClient

class CustomCommands(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.riot_client = RiotAPIClient()

    @commands.command(name='ping')
    async def ping(self, ctx):
        await ctx.send('Pong!')

    @commands.command(name='lastgame')
    async def lastgame(self, ctx, riot_id: str):
        puuid = self.riot_client.get_puuid_by_riot_id(riot_id)
        last_match_id = self.riot_client.get_last_match_id(puuid)
        match_data = self.riot_client.get_match_details(last_match_id)
        stats = self.riot_client.extract_game_stats(match_data, puuid)
        if stats:
            await ctx.send(embed=self.riot_client.create_embed(riot_id, stats))
        else:
            await ctx.send(f"Summoner {riot_id} is not being tracked.")

async def setup(bot):
    await bot.add_cog(CustomCommands(bot))
