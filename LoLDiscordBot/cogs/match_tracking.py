from discord.ext import commands, tasks
from riot_api.riot_client import RiotAPIClient
from config import DISCORD_CHANNEL_ID
from riot_api.champion_mapping import CHAMPION_NAME_TO_ID  # Import champion ID mapping
import discord

class MatchTracking(commands.Cog):
    PERFORMANCE_WEIGHTS = {
        'kills': 0.3,
        'deaths': -1.0,  
        'assists': 0.2,
        'kill_participation': 0.2,
        'damage_delt': 0.07, #low weight - Need to fix how this is calculated related to game time
        'gpm': 0.15,
        'cs_per_min': 0.1,
        'ward_score_per_min': 0.15,
        # Add more metrics and weights as needed
    }
    PERFORMANCE_THRESHOLD = 0.25  # Define the threshold for sending the message

    QUEUE_MAP = {
        "soloduo": "RANKED_SOLO_5x5",
        "flex": "RANKED_FLEX_SR",
        "tft": "RANKED_TFT",
        "tftflex": "RANKED_TFT_DOUBLE_UP",
    }

    def __init__(self, bot, test_mode=False):
        self.bot = bot
        self.test_mode = test_mode
        self.riot_client = RiotAPIClient() if not test_mode else None
        self.tracked_summoners = {
            "a6e6#NA1": {"puuid": "", "last_match": ""},
            "THECOBER#NA1": {"puuid": "", "last_match": ""},
            "i play with pee#NA1": {"puuid": "", "last_match": ""},
            "WaffleFlu#2000": {"puuid": "", "last_match": ""},
            "Raybrothon#NA1": {"puuid": "", "last_match": ""},
            "ClaySlayce#NA1": {"puuid": "", "last_match": ""},
            "mung daal69#NA1": {"puuid": "", "last_match": ""},
        }
        if not test_mode:
            # Retrieve and populate PUUIDs and last match IDs for each summoner
            for riot_id in self.tracked_summoners.keys():
                puuid = self.riot_client.get_puuid_by_riot_id(riot_id)
                if puuid:
                    self.tracked_summoners[riot_id]['puuid'] = puuid
                    last_match_id = self.riot_client.get_last_match_id(puuid)
                    if last_match_id:
                        self.tracked_summoners[riot_id]['last_match'] = last_match_id
                        print(f"Initialized {riot_id} with last match ID {last_match_id}")
                    else:
                        print(f"No matches found for {riot_id}")
                else:
                    print(f"Failed to retrieve PUUID for {riot_id}.")

            self.check_for_new_games.start()

    @tasks.loop(minutes=5)
    async def check_for_new_games(self):
        print("Checking for new games...")
        channel = self.bot.get_channel(DISCORD_CHANNEL_ID)
        if not channel:
            print("Discord channel not found or bot lacks permission to post.")
            return

        for riot_id, data in self.tracked_summoners.items():
            puuid = data['puuid']
            if not puuid:
                print(f"Skipping {riot_id} due to missing PUUID.")
                continue

            last_match_id = self.riot_client.get_last_match_id(puuid)
            print(f"Retrieved last match ID for {riot_id}: {last_match_id}")

            if last_match_id and last_match_id != data['last_match']:
                match_data = self.riot_client.get_match_details(last_match_id)
                if match_data:
                    stats = self.riot_client.extract_game_stats(match_data, puuid)
                    if stats:
                        role = stats.get('role', 'Laner') #Default laner if role is not found
                        performance_score = self.evaluate_performance(stats, stats.get('role', 'Laner'))
                        print(f"Performance score for {riot_id} ({role}): {performance_score}")

                        if performance_score < self.PERFORMANCE_THRESHOLD:
                            print(f"Posting match details for {riot_id} due to low performance.")
                            await channel.send(embed=self.riot_client.create_embed(riot_id, stats))
                        else:
                            print(f"{riot_id} performed well; not posting match details.")
                    else:
                        print(f"Failed to extract stats for {riot_id}.")
                else:
                    print(f"Failed to retrieve match details for match ID {last_match_id}.")
                self.tracked_summoners[riot_id]['last_match'] = last_match_id
            else:
                print(f"No new match found for {riot_id}.")

    def evaluate_performance(self, stats, role):
        """Evaluates the player's performance based on multiple metrics."""
    
        # Define base normalization values
        normalization_values = {
            'kills': 10, 'deaths': 10, 'assists': 15, 'kill_participation': 100,
            'damage_delt': 60000, 'gpm': 330, 'cs_per_min': 5, 'ward_score_per_min': 0.8
        }

        # Role-specific Adjustments
        role_adjustments = {
            "Support": {'damage_delt': 30000, 'ward_score_per_min': 1.3, 'cs_per_min': 1.0},
            "Jungle": {'cs_per_min': 6, 'damage_delt': 45000},
            "Laner": {}  # Default values remain the same
        }  

        # Apply role-based normalization
        if role in role_adjustments:
            for key, value in role_adjustments[role].items():
                normalization_values[key] = value

        # Normalize Metrics (Scores between 0 and 1)
        normalized_metrics = {key: min(stats[key] / max_value, 1) for key, max_value in normalization_values.items()}

        # Weighted Score Calculation
        score = sum(normalized_metrics[metric] * self.PERFORMANCE_WEIGHTS[metric] for metric in self.PERFORMANCE_WEIGHTS)

        # Apply Scaling Penalties for Low Performance in Key Metrics
        if normalized_metrics['kill_participation'] < 0.35:
            score *= 0.92  # Was 0.85 → less punishing
        if normalized_metrics['ward_score_per_min'] < 0.25:
            score *= 0.95  # Was 0.9 → less punishing
        if normalized_metrics['cs_per_min'] < 0.4:
            score *= 0.95  # Was 0.9 → less punishing
        if normalized_metrics['damage_delt'] < 0.3:
            score *= 0.93  # Was 0.85 → less punishing
        if normalized_metrics['gpm'] < 0.5:
            score *= 0.92  # Was 0.85 → less punishing

        return round(score, 3)  # Return a rounded value for easier readability
    
    @commands.command(name="lastgame")
    async def last_game(self, ctx, *, username: str):
        """Fetches and posts an embed of the last game for the given username."""
        riot_id = username.replace(" ", "")  # Ensure no spaces
        if "#" not in riot_id:
            await ctx.send("Invalid Riot ID format. Use `SummonerName#TAG`")
            return
        
        puuid = self.riot_client.get_puuid_by_riot_id(riot_id)
        if not puuid:
            await ctx.send(f"⚠️ Could not find player `{username}`.")
            return

        last_match_id = self.riot_client.get_last_match_id(puuid)
        if not last_match_id:
            await ctx.send(f"⚠️ No recent games found for `{username}`.")
            return

        match_data = self.riot_client.get_match_details(last_match_id)
        if not match_data:
            await ctx.send(f"⚠️ Failed to retrieve match details for `{username}`.")
            return

        stats = self.riot_client.extract_game_stats(match_data, puuid)
        if not stats:
            await ctx.send(f"⚠️ Unable to extract stats for `{username}`.")
            return

        embed = self.riot_client.create_embed(username, stats)
        await ctx.send(embed=embed)

    
    RANK_ICONS = {
        "IRON": "https://raw.communitydragon.org/latest/plugins/rcp-fe-lol-shared-components/global/default/iron.png",
        "BRONZE": "https://raw.communitydragon.org/latest/plugins/rcp-fe-lol-shared-components/global/default/bronze.png",
        "SILVER": "https://raw.communitydragon.org/latest/plugins/rcp-fe-lol-shared-components/global/default/silver.png",
        "GOLD": "https://raw.communitydragon.org/latest/plugins/rcp-fe-lol-shared-components/global/default/gold.png",
        "PLATINUM": "https://raw.communitydragon.org/latest/plugins/rcp-fe-lol-shared-components/global/default/platinum.png",
        "EMERALD": "https://raw.communitydragon.org/latest/plugins/rcp-fe-lol-shared-components/global/default/emerald.png",
        "DIAMOND": "https://raw.communitydragon.org/latest/plugins/rcp-fe-lol-shared-components/global/default/diamond.png",
        "MASTER": "https://raw.communitydragon.org/latest/plugins/rcp-fe-lol-shared-components/global/default/master.png",
        "GRANDMASTER": "https://raw.communitydragon.org/latest/plugins/rcp-fe-lol-shared-components/global/default/grandmaster.png",
        "CHALLENGER": "https://raw.communitydragon.org/latest/plugins/rcp-fe-lol-shared-components/global/default/challenger.png",
    }

    def generate_lp_bar(self, lp):
        total_blocks = 10  # Number of blocks in the progress bar
        filled_blocks = round(lp / 100 * total_blocks)  # LP is between 0 and 100
        empty_blocks = total_blocks - filled_blocks
        bar = "🟩" * filled_blocks + "⬜" * empty_blocks
        return bar

    @commands.command(name="rank")
    async def rank(self, ctx, *args):
        """
        Fetches the rank of a player.
        Usage:
        - `!rank a6e6#NA1` (Defaults to Solo/Duo)
        - `!rank flex a6e6#NA1`
        - `!rank tft a6e6#NA1`
        """
        if len(args) == 1:  # If only 1 argument (assume username, default to Solo/Duo)
            queue = "soloduo"
            username = args[0]
        elif len(args) == 2:  # If 2 arguments (queue type + username)
            queue = args[0].lower()
            username = args[1]
        else:
            await ctx.send("Invalid format. Use `!rank [queue] summoner#TAG` or `!rank summoner#TAG`")
            return

        puuid = self.riot_client.get_puuid_by_riot_id(username)
        if not puuid:
            await ctx.send(f"⚠️ Could not find summoner `{username}`.")
            return

        region = "NA"  # Change this dynamically later if needed
        queue_type = self.QUEUE_MAP.get(queue, "RANKED_SOLO_5x5")
        rank_data = self.riot_client.get_summoner_rank(puuid, queue_type)

        if not rank_data:
            await ctx.send(f"⚠️ `{username}` is unranked in {queue}.")
            return

        tier = rank_data["tier"]
        rank = rank_data["rank"]
        lp = rank_data["lp"]
        wins = rank_data["wins"]
        losses = rank_data["losses"]
        winrate = round((wins / (wins + losses)) * 100, 1) if (wins + losses) > 0 else 0
        lp_bar = self.generate_lp_bar(lp)
        rank_icon = self.RANK_ICONS.get(tier.upper(), None)

        embed = discord.Embed(
            title=f"Rank for {username}",
            description=f"**{tier} {rank}** - {lp} LP\n\n{lp_bar}\n\n**Wins:** {wins} | **Losses:** {losses} | **Winrate:** {winrate}%",
            color=discord.Color.blue()
        )

        if rank_icon:
            embed.set_thumbnail(url=rank_icon)

        await ctx.send(embed=embed)

    @commands.command(name="mastery")
    async def mastery(self, ctx, *args):
        """
        Fetches mastery for a summoner.
        Usage:
        - `!mastery username#TAG` (Shows top 3 champions)
        - `!mastery username#TAG champion` (Shows mastery for a specific champion)
        """
        if len(args) == 1:
            username = args[0]
            champion_id = None  # Get top 3 champions
        elif len(args) == 2:
            username = args[0]
            champion_name = args[1].capitalize()  # Format properly

            # Convert champion name to ID
            champion_id = CHAMPION_NAME_TO_ID.get(champion_name)
            if not champion_id:
                await ctx.send(f"⚠️ Invalid champion name: `{champion_name}`.")
                return
        else:
            await ctx.send("Invalid format. Use `!mastery username#TAG [champion]`.")
            return

        puuid = self.riot_client.get_puuid_by_riot_id(username)
        if not puuid:
            await ctx.send(f"⚠️ Could not find summoner `{username}`.")
            return

        region = "na1"  # Adjust this dynamically if needed

        if champion_id:
            mastery_data = self.riot_client.get_champion_mastery(puuid, champion_id, region)

            if not mastery_data:
                await ctx.send(f"⚠️ `{username}` has no mastery data for {champion_name}.")
                return

            # Convert champion name properly for the URL (no spaces, case-sensitive)
            champion_name_url = champion_name.replace(" ", "").capitalize()
            champion_icon_url = f"https://ddragon.leagueoflegends.com/cdn/14.1.1/img/champion/{champion_name_url}.png"

            embed = discord.Embed(
                title=f"{username}'s Mastery for {champion_name}",
                description=f"**Mastery Level:** {mastery_data['championLevel']}\n"
                            f"**Mastery Points:** {mastery_data['championPoints']:,}",
                color=discord.Color.blue()
            )
            embed.set_thumbnail(url=champion_icon_url)  # Add champion image

        else:
            mastery_data = self.riot_client.get_top_mastery(puuid, region)

            if not mastery_data:
                await ctx.send(f"⚠️ `{username}` has no champion mastery data.")
                return

            embed = discord.Embed(
                title=f"Top 3 Mastery Champions for {username}",
                color=discord.Color.blue()
            )

            for champ in mastery_data[:3]:
                champ_name = [name for name, id in CHAMPION_NAME_TO_ID.items() if id == champ["championId"]]
                champ_name = champ_name[0] if champ_name else "Unknown Champion"

                # Champion image URL
                champion_name_url = champ_name.replace(" ", "").capitalize()
                champion_icon_url = f"https://ddragon.leagueoflegends.com/cdn/14.1.1/img/champion/{champion_name_url}.png"

                embed.add_field(
                    name=f"{champ_name}",
                    value=f"**Level:** {champ['championLevel']}  |  **Points:** {champ['championPoints']:,}",
                    inline=False
                )
                embed.set_thumbnail(url=champion_icon_url)  # Set image to last champion (not ideal for top 3)

        await ctx.send(embed=embed)


async def setup(bot):
    await bot.add_cog(MatchTracking(bot))
