import requests

QUEUE_TYPE_MAP = {
    400: "Draft Pick",
    420: "Ranked Solo/Duo",
    430: "Blind Pick",
    440: "Ranked Flex",
    450: "ARAM",
    700: "Clash",
    900: "URF",
    1020: "One for All",
    1400: "Ultimate Spellbook",
    830: "Co-op vs. AI (Intro)",
    840: "Co-op vs. AI (Beginner)",
    850: "Co-op vs. AI (Intermediate)",
    1300: "Nexus Blitz",
    # Add more queueId mappings as needed
}

def fetch_latest_version():
    # URL to fetch the list of available versions
    version_url = "https://ddragon.leagueoflegends.com/api/versions.json"
    response = requests.get(version_url)

    if response.status_code == 200:
        versions = response.json()
        latest_version = versions[0]  # The first item is the latest version
        print(f"Using latest version: {latest_version}")
        return latest_version
    else:
        print(f"Failed to retrieve versions: {response.status_code}")
        return None

def fetch_item_data():
    # Fetch the latest version
    latest_version = fetch_latest_version()
    if not latest_version:
        return {}

    # URL to fetch the item data from Data Dragon
    data_dragon_url = f"https://ddragon.leagueoflegends.com/cdn/{latest_version}/data/en_US/item.json"
    response = requests.get(data_dragon_url)

    if response.status_code == 200:
        item_data = response.json()['data']
        # Create a mapping of item IDs to item names
        item_name_map = {int(item_id): item_info['name'] for item_id, item_info in item_data.items()}
        return item_name_map
    else:
        print(f"Failed to retrieve item data: {response.status_code}")
        return {}

# Fetch item data and store it in ITEM_NAME_MAP
ITEM_NAME_MAP = fetch_item_data()