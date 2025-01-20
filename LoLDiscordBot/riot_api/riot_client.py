import requests
import discord
from config import RIOT_API_KEY
from riot_api.queue_mapping import QUEUE_TYPE_MAP
from riot_api.queue_mapping import ITEM_NAME_MAP
class RiotAPIClient:
    BASE_URL = "https://americas.api.riotgames.com"

    # Riot API Base URLs for League Endpoints
    REGION_TO_BASE_URL = {
        "NA": "https://na1.api.riotgames.com",
        "EUW": "https://euw1.api.riotgames.com",
        "EUNE": "https://eun1.api.riotgames.com",
        "KR": "https://kr.api.riotgames.com",
        "JP": "https://jp1.api.riotgames.com",
        "BR": "https://br1.api.riotgames.com",
        "LAN": "https://la1.api.riotgames.com",
        "LAS": "https://la2.api.riotgames.com",
        "OCE": "https://oc1.api.riotgames.com",
        "TR": "https://tr1.api.riotgames.com",
        "RU": "https://ru.api.riotgames.com",
    }

    def get_puuid_by_riot_id(self, riot_id):
        game_name, tag_line = riot_id.split("#")
        url = f'{self.BASE_URL}/riot/account/v1/accounts/by-riot-id/{game_name}/{tag_line}'
        response = requests.get(url, headers={'X-Riot-Token': RIOT_API_KEY})

        if response.status_code == 200:
            puuid = response.json().get('puuid', None)
            print(f"Retrieved PUUID for {riot_id}: {puuid}")
            return puuid
        else:
            print(f"Failed to retrieve PUUID for {riot_id}. Status code: {response.status_code}")
            return None
        
    def get_summoner_id(self, puuid):
        url = f"https://na1.api.riotgames.com/lol/summoner/v4/summoners/by-puuid/{puuid}"
        response = requests.get(url, headers={'X-Riot-Token': RIOT_API_KEY})
        
        if response.status_code == 200:
            return response.json()["id"]  # Riot API returns the summoner ID
        else:
            print(f"Failed to retrieve Summoner ID for PUUID {puuid}: {response.status_code}")
            return None
        
    def get_last_match_id(self, puuid):
        response = requests.get(f'{self.BASE_URL}/lol/match/v5/matches/by-puuid/{puuid}/ids?start=0&count=10',
                                headers={'X-Riot-Token': RIOT_API_KEY})
        if response.status_code == 200:
            match_ids = response.json()
            for match_id in match_ids:
                match_data = self.get_match_details(match_id)
                if match_data:
                    queue_id = match_data['info']['queueId']
                    if queue_id not in {1090, 1100}:  # Exclude TFT queue IDs
                        return match_id  # Return the first valid non-TFT match
        return None  # No valid match found
    
    def get_summoner_rank(self, puuid, queue_type="RANKED_SOLO_5x5"):
        summoner_id = self.get_summoner_id(puuid)
        if not summoner_id:
            return None

        base_url = "https://na1.api.riotgames.com"  # Default to NA
        url = f"{base_url}/lol/league/v4/entries/by-summoner/{summoner_id}"

        response = requests.get(url, headers={'X-Riot-Token': RIOT_API_KEY})

        if response.status_code == 200:
            ranks = response.json()
            for rank in ranks:
                if rank["queueType"] == queue_type:
                    return {
                        "tier": rank["tier"],
                        "rank": rank["rank"],
                        "lp": rank["leaguePoints"],
                        "wins": rank["wins"],
                        "losses": rank["losses"]
                    }
            return None  # If the player is unranked in the specified queue
        else:
            print(f"Failed to retrieve rank for PUUID {puuid}: {response.status_code}")
            return None
        
    def get_champion_mastery(self, puuid, champion_id=None):
        """Fetches champion mastery for a player. If champion_id is provided, returns mastery for that champion.
        Otherwise, returns the top 3 champions by mastery points."""
        url = f"https://na1.api.riotgames.com/lol/champion-mastery/v4/champion-masteries/by-puuid/{puuid}"
        response = requests.get(url, headers={'X-Riot-Token': RIOT_API_KEY})

        if response.status_code == 200:
            mastery_data = response.json()

            if champion_id:
                for champ in mastery_data:
                    if champ["championId"] == champion_id:
                        return {
                            "championId": champ["championId"],
                            "championLevel": champ["championLevel"],
                            "championPoints": champ["championPoints"],
                            "lastPlayTime": champ["lastPlayTime"]
                        }
                return None  # No mastery found for the given champion
            
            return mastery_data[:3]  # Return top 3 champions
        else:
            print(f"Failed to retrieve mastery for PUUID {puuid}: {response.status_code}")
            return None

    def get_match_details(self, match_id):
        response = requests.get(f'{self.BASE_URL}/lol/match/v5/matches/{match_id}',
                                headers={'X-Riot-Token': RIOT_API_KEY})
        if response.status_code == 200:
            return response.json()
        else:
            print(f"Failed to retrieve match details for match ID {match_id}: {response.status_code}")
            return None

    def extract_game_stats(self, match_data, puuid):
        if not match_data:
            return None

        # Game duration calculations
        game_duration_seconds = match_data['info']['gameDuration']
        game_duration_minutes = game_duration_seconds / 60 if game_duration_seconds > 0 else 1  # Avoid division by zero

        queue_id = match_data['info']['queueId']
        game_type = QUEUE_TYPE_MAP.get(queue_id, "Unknown")

        # Queues where Jungle role should be checked
        jungle_queues = {400, 420, 430, 440, 700}  # Draft, Solo/Duo, Blind, Flex, Clash

        support_items = {"3858", "3857", "3862", "3853", "3850", "3851", "3860", "3855"}

        for participant in match_data['info']['participants']:
            if participant['puuid'] == puuid:
                team_id = participant['teamId']
                friendly_kills = sum(p['kills'] for p in match_data['info']['participants'] if p['teamId'] == team_id)
                enemy_kills = sum(p['kills'] for p in match_data['info']['participants'] if p['teamId'] != team_id)
                kill_participation = round((participant['kills'] + participant['assists']) / friendly_kills * 100, 2) if friendly_kills > 0 else 0.0

                # Role determination
                is_support = any(str(item) in support_items for item in [
                    participant.get('item0', 0), participant.get('item1', 0), participant.get('item2', 0),
                    participant.get('item3', 0), participant.get('item4', 0), participant.get('item5', 0),
                    participant.get('item6', 0)
                ])
                is_jungle = queue_id in jungle_queues and (participant.get('spell1Id') == 11 or participant.get('spell2Id') == 11)

                if is_support:
                    role = 'Support'
                elif is_jungle:
                    role = 'Jungle'
                else:
                    role = 'Laner'

                # Derived stats
                cs = participant['totalMinionsKilled'] + participant['neutralMinionsKilled']
                cs_per_min = round(cs / game_duration_minutes, 2)
                damage_per_min = round(participant['totalDamageDealtToChampions'] / game_duration_minutes, 2)
                ward_score_per_min = round(participant['visionScore'] / game_duration_minutes, 2)

                # Map item IDs to names
                items = [ITEM_NAME_MAP.get(participant.get(f'item{i}', 0), f"Unknown Item ({participant.get(f'item{i}', 0)})") for i in range(7)]

                return {
                    'champion': participant['championName'],
                    'win': participant['win'],
                    'kills': participant['kills'],
                    'deaths': participant['deaths'],
                    'assists': participant['assists'],
                    'kill_participation': kill_participation,
                    'damage_delt': participant['totalDamageDealtToChampions'],
                    'damage_per_min': damage_per_min,
                    'cs': cs,
                    'cs_per_min': cs_per_min,
                    'ward_score': participant['visionScore'],
                    'ward_score_per_min': ward_score_per_min,
                    'gold_earned': participant['goldEarned'],
                    'gpm': round(participant['goldEarned'] / game_duration_minutes, 2),
                    'largest_multi_kill': participant['largestMultiKill'],
                    'items': items,
                    'game_duration': game_duration_seconds,
                    'friendly_kills': friendly_kills,
                    'enemy_kills': enemy_kills,
                    'game_type': game_type,
                    'role': role,  # Added role to the stats
                }
        return None

    

    def create_embed(self, riot_id, stats):
        win = stats['win']
        embed_color = discord.Color.green() if win else discord.Color.red()
        xspc = "\u00A0\u00A0"  # This adds 2 non-breaking spaces
        
        # Determine the result text based on win/loss and include the kill stats
        if stats['win']:
            result_text = f"🎉 **Victory! {xspc} | {xspc} {stats['friendly_kills']} - {stats['enemy_kills']}**"
        else:
            result_text = f"😞 **Defeat  |  {stats['friendly_kills']} - {stats['enemy_kills']}**"

        game_duration_minutes = stats['game_duration'] // 60
        game_duration_seconds = stats['game_duration'] % 60

        description = (
            f"Champion: **{stats['champion']}**\n"
            f"Game Type: **{stats['game_type']}**\n"
            f"Game Duration: **{game_duration_minutes}m {game_duration_seconds}s**"
        )

        embed = discord.Embed(
            title=f"Game Summary for {riot_id.split('#')[0]}",
            description=description,
            color=embed_color
        )
        embed.add_field(name="Result:", value=result_text, inline=False)
        embed.add_field(name="K/D/A:", value=f"**{stats['kills']}** / **{stats['deaths']}** / **{stats['assists']}**", inline=True)
        embed.add_field(name="Kill Participation:", value=f"**{stats['kill_participation']}%**", inline=True)
        embed.add_field(name="Damage Dealt:", value=f"{stats['damage_delt']:,}", inline=True)
        embed.add_field(name="Gold Earned:", value=f"**{stats['gold_earned']:,}**", inline=True)
        embed.add_field(name="CS:", value=f"{stats['cs']}", inline=True)
        embed.add_field(name="Ward Score:", value=f"{stats['ward_score']}", inline=True)
        embed.add_field(name="Gold Per Min:", value=f"{stats['gpm']}", inline=False)
        embed.set_thumbnail(url=f"http://ddragon.leagueoflegends.com/cdn/12.18.1/img/champion/{stats['champion']}.png")

        return embed
