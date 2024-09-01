from discord.ext import commands, tasks
from riot_api.riot_client import RiotAPIClient
from config import DISCORD_CHANNEL_ID

class MatchTracking(commands.Cog):
    PERFORMANCE_WEIGHTS = {
        'kills': 0.3,
        'deaths': -2,  
        'assists': 0.2,
        'kill_participation': 0.0,
        'damage_delt': 0.1,
        'gpm': 0.15,
        'cs_per_min': 0.1,
        'ward_score': 0.15,
        # Add more metrics and weights as needed
    }

    PERFORMANCE_THRESHOLD = 0.4  # Define the threshold for sending the message

    def __init__(self, bot):
        self.bot = bot
        self.riot_client = RiotAPIClient()
        self.tracked_summoners = {
            "a6e6#NA1": {"puuid": "", "last_match": ""},
            "THECOBER#NA1": {"puuid": "", "last_match": ""},
            "i play with pee#NA1": {"puuid": "", "last_match": ""},
            "WaffleFlu#2000": {"puuid": "", "last_match": ""},
            "Raybrothon#NA1": {"puuid": "", "last_match": ""},
            "ClaySlayce#NA1": {"puuid": "", "last_match": ""},
            "mung daal69#NA1": {"puuid": "", "last_match": ""},
        }

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
                        performance_score = self.evaluate_performance(stats)
                        print(f"Performance score for {riot_id}: {performance_score}")

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

    def evaluate_performance(self, stats):
        score = 0

        # Normalize metrics
        normalized_kills = stats['kills'] / 10  # Assuming 10 is a good max value for kills
        normalized_deaths = (10 - stats['deaths']) / 10  # Inverting to reward fewer deaths
        normalized_assists = stats['assists'] / 15  # Assuming 15 is a good max value for assists
        normalized_kill_participation = stats['kill_participation']  # is a percentage (represented as a whole number)
        normalized_damage_delt = round(stats['damage_delt'] / 60000)  # Assuming 60,000 is a max value
        normalized_gpm = stats['gpm'] / 330  # Assuming 330 is a good max value for GPM
        normalized_cs_per_min = round(stats['cs_per_min'] / 5, 2)  # Assuming 5 is a good max value for CS per min
        normalized_ward_score = stats['ward_score'] / 45  # Assuming 45 is a good max value for ward score

        # Calculate weighted score
        score += normalized_kills * self.PERFORMANCE_WEIGHTS['kills'] 
        score += normalized_deaths * self.PERFORMANCE_WEIGHTS['deaths'] 
        score += normalized_assists * self.PERFORMANCE_WEIGHTS['assists']
        score += normalized_kill_participation * self.PERFORMANCE_WEIGHTS['kill_participation']
        score += normalized_damage_delt * self.PERFORMANCE_WEIGHTS['damage_delt']
        score += normalized_gpm * self.PERFORMANCE_WEIGHTS['gpm']
        score += normalized_cs_per_min * self.PERFORMANCE_WEIGHTS['cs_per_min']
        score += normalized_ward_score * self.PERFORMANCE_WEIGHTS['ward_score']
        # Add additional metrics if needed
        return score

async def setup(bot):
    await bot.add_cog(MatchTracking(bot))
