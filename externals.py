import requests


def fetch_theme_cards(theme_slug):
    """
    The new function to fetch the 'Leaf Node' data.
    """
    url = f"https://json.edhrec.com/pages/{theme_slug}.json"

    try:
        response = requests.get(url)
        if response.status_code != 200:
            return []

        data = response.json()
        card_lists = data.get('container', {})\
                         .get('json_dict', {})\
                         .get('cardlists', [])

        theme_cards = []
        # We grab High Synergy, Top Cards, Creatures, Instants, etc.
        # to build a robust pool of "Perfect Cards"
        target_headers = ['High Synergy Cards',
                          'Top Cards',
                          'Creatures',
                          'Instants',
                          'Sorceries',
                          'Artifacts',
                          'Enchantments']

        for cl in card_lists:
            if cl.get('header') in target_headers:
                for card_view in cl.get('cardviews', []):
                    theme_cards.append(card_view['name'])

        return theme_cards

    except Exception as e:
        print(f"Error fetching theme {theme_slug}: {e}")
        return []


def fetch_edhrec_data(card_name):
    # Create the slug: 'Hurkyl, Master Wizard' -> 'hurkyl-master-wizard'
    slug = card_name.lower()\
                    .replace(',', '')\
                    .replace("'", "")\
                    .replace(' ', '-')
    url = f"https://json.edhrec.com/pages/commanders/{slug}.json"

    print(f"Fetching {slug}...")
    try:
        response = requests.get(url)
        if response.status_code != 200:
            return None

        data = response.json()

        # 1. Extract the "Paths" (Themes)
        # These are links to sub-pages (e.g., "Artifacts", "Spellslinger")
        themes = []
        # 'taglinks' usually holds the themes. Sometimes it's 'tribelinks'.
        panels = data.get('panels', {})
        raw_links = panels.get('taglinks', []) + panels.get('tribelinks', [])

        for link in raw_links:
            themes.append({
                'name': link['value'],  # e.g., "Artifacts"
                'slug': "commanders" + '/' + slug + '/' + link['slug']
            })

        # 2. Extract the "Generic" High Synergy Cards (The Root Deck)
        # This is strictly for the "Generic" build if no theme is chosen
        card_lists = data.get('container', {})\
            .get('json_dict', {})\
            .get('cardlists', [])

        synergy_cards = []
        for cl in card_lists:
            # We specifically want "High Synergy" or "Top Cards"
            if cl['header'] in ['High Synergy Cards', 'Top Cards']:
                for card_view in cl['cardviews']:
                    # EDHRec names sometimes have casing issues,
                    # simpler to clean here
                    synergy_cards.append(card_view['name'])

        return {
            'commander': card_name,
            'themes': themes,               # The Branches
            'generic_cards': synergy_cards  # The Root Data
        }

    except Exception as e:
        print(f"Error parsing EDHRec for {card_name}: {e}")
        return None
