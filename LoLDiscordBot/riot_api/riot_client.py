import requests
import discord
from config import RIOT_API_KEY
from riot_api.queue_mapping import QUEUE_TYPE_MAP
from riot_api.queue_mapping import ITEM_NAME_MAP
class RiotAPIClient:
    BASE_URL = "https://americas.api.riotgames.com"

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
        
    def get_last_match_id(self, puuid):
        response = requests.get(f'{self.BASE_URL}/lol/match/v5/matches/by-puuid/{puuid}/ids?start=0&count=1',
                                headers={'X-Riot-Token': RIOT_API_KEY})
        if response.status_code == 200:
            return response.json()[0]
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
        for participant in match_data['info']['participants']:
            if participant['puuid'] == puuid:
                game_duration_seconds = match_data['info']['gameDuration']
                game_duration_minutes = game_duration_seconds / 60  # Convert to minutes

                queue_id = match_data['info']['queueId']
                game_type = QUEUE_TYPE_MAP.get(queue_id, "Unknown")

                
                team_id = participant['teamId']
                friendly_kills = sum(p['kills'] for p in match_data['info']['participants'] if p['teamId'] == team_id)
                enemy_kills = sum(p['kills'] for p in match_data['info']['participants'] if p['teamId'] != team_id)
                kill_participation = round((participant['kills'] + participant['assists']) / friendly_kills * 100) if friendly_kills > 0 else 0.0
                gold_per_min = round(participant['goldEarned'] / (match_data['info']['gameDuration'] / 60))
                cs = participant['totalMinionsKilled'] + participant['neutralMinionsKilled']
                cs_per_min = round(cs / game_duration_minutes, 2) if game_duration_minutes > 0 else 0
                damage_per_min = round(participant['totalDamageDealtToChampions'] / game_duration_minutes, 2) if game_duration_minutes > 0 else 0

                # Map item IDs to names using the fetched ITEM_NAME_MAP
                items = [ITEM_NAME_MAP.get(item_id, f"Unknown Item ({item_id})") for item_id in [
                    participant['item0'], participant['item1'], participant['item2'], 
                    participant['item3'], participant['item4'], participant['item5'], participant['item6']
                ]]

                return {
                    'champion': participant['championName'],
                    'win': participant['win'],
                    'kills': participant['kills'],
                    'deaths': participant['deaths'],
                    'assists': participant['assists'],
                    'kill_participation': kill_participation,
                    'damage_delt': participant['totalDamageDealtToChampions'],
                    'damage_per_min': damage_per_min,
                    'cs': participant['totalMinionsKilled'] + participant['neutralMinionsKilled'],
                    'cs_per_min': cs_per_min,
                    'ward_score': participant['visionScore'],
                    'gold_earned': participant['goldEarned'],
                    'gpm': gold_per_min,
                    'largest_multi_kill': participant['largestMultiKill'],
                    'items': items,
                    'game_duration': match_data['info']['gameDuration'],
                    'friendly_kills': friendly_kills,
                    'enemy_kills': enemy_kills,
                    'game_type': game_type,
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
        embed.add_field(name="Damage Dealt:", value=f"{stats['damage_dealt']:,}", inline=True)
        embed.add_field(name="Gold Earned:", value=f"**{stats['gold_earned']:,}**", inline=True)
        embed.add_field(name="CS:", value=f"{stats['cs']}", inline=True)
        embed.add_field(name="Ward Score:", value=f"{stats['ward_score']}", inline=True)
        embed.add_field(name="Gold Per Min:", value=f"{stats['gpm']}", inline=False)
        embed.set_thumbnail(url=f"http://ddragon.leagueoflegends.com/cdn/12.18.1/img/champion/{stats['champion']}.png")

        return embed
