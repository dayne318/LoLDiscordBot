from discord.ext import commands, tasks
from riot_api.riot_client import RiotAPIClient
from config import DISCORD_CHANNEL_ID

class MatchTracking(commands.Cog):
    PERFORMANCE_WEIGHTS = {
        'kills': 0.3,
        'deaths': -2.0,  
        'assists': 0.2,
        'kill_participation': 0.0,
        'damage_delt': 0.05, #low weight - Need to fix how this is calculated related to game time
        'gpm': 0.15,
        'cs_per_min': 0.1,
        'ward_score_per_min': 0.15,
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
                        role = stats.get('role', 'Laner') #Default laner if role is not found
                        performance_score = self.evaluate_performance(stats)
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
        score = 0
        # Define normalization values for each metric
        normalization_values = {
            'kills': 10,
            'deaths': 10,
            'assists': 15,
            'kill_participation': 100,
            'damage_delt': 60000,
            'gpm': 330,
            'cs_per_min': 5,
            'ward_score_per_min': 0.8,
        }

        # Adjust normalization based on role
        if role == 'Support':
            normalization_values['damage_delt'] = 30000  # Supports deal less damage, for example
            normalization_values['ward_score_per_min'] = 1.3  # Higher ward score expectation
            cs_per_min_threshold = 0.1  # Supports have much lower CS
            kill_participation_threshold = 0.3
            ward_score_threshold = 0.5
            gpm_score_threshold = 0.85
            damage_delt_threshold = 0.1 # Some supports don't do much damage. Don't punish them for this
        elif role == 'Jungle':
            normalization_values['cs_per_min'] = 6  # Junglers tend to have slightly higher CS/min
            kill_participation_threshold = 0.35
            ward_score_threshold = 0.4
            cs_per_min_threshold = 0.3
            damage_delt_threshold = 0.2 # Some junglers dont do much damage. Punish Jungle if not 20% of normalized value
            
        else:
            # Default laner values
            kill_participation_threshold = 0.35
            ward_score_threshold = 0.25
            cs_per_min_threshold = 0.4
            damage_delt_threshold = 0.3 # Punish laner if less than 30% damage of normalized value

        # Normalize metrics
        normalized_metrics = {key: round(stats[key] / max_value, 2) for key, max_value in normalization_values.items()}

        # Apply penalties for low values
        if normalized_metrics['kill_participation'] < kill_participation_threshold:
            score += (normalized_metrics['kill_participation'] - 1) * self.PERFORMANCE_WEIGHTS['kill_participation']
        if normalized_metrics['ward_score_per_min'] < ward_score_threshold:
            score += (normalized_metrics['ward_score_per_min'] - 1) * self.PERFORMANCE_WEIGHTS['ward_score_per_min']
        if normalized_metrics['cs_per_min'] < cs_per_min_threshold:
            score += (normalized_metrics['cs_per_min'] - 1) * self.PERFORMANCE_WEIGHTS['cs_per_min']
        if normalized_metrics['damage_delt'] < damage_delt_threshold:
            score += (normalized_metrics['damage_delt'] - 1) * self.PERFORMANCE_WEIGHTS['damage_delt']
        if normalized_metrics['gpm'] < gpm_score_threshold:
            score += (normalized_metrics['gpm'] - 1) * self.PERFORMANCE_WEIGHTS['gpm']

        # Calculate weighted score
        for metric, weight in self.PERFORMANCE_WEIGHTS.items():
            score += normalized_metrics.get(metric, 0) * weight

        return score


async def setup(bot):
    await bot.add_cog(MatchTracking(bot))
