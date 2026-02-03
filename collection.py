import json


# --- COLLECTION CLASS ---
class Collection:
    def __init__(self, cards):
        self.cards = cards
        # Normalize keys to lowercase for easier lookup later
        self._name_index = {c['Name'].lower(): c for c in self.cards
                            if 'Name' in c}
        self.enriched = False

    def enrich_from_local_bulk(self, bulk_json_path):
        """
        Loads Scryfall 'Oracle Cards' JSON and merges it.
        """
        print(f"Loading Scryfall Bulk Data from {bulk_json_path}...")
        try:
            with open(bulk_json_path, 'r', encoding='utf-8') as f:
                scryfall_data = json.load(f)
        except FileNotFoundError:
            print("Error: Bulk JSON file not found. Skipping enrichment.")
            return

        print("Merging data...")
        match_count = 0

        # Create a temporary index of the bulk data for speed
        bulk_index = {item['name'].lower(): item for item in scryfall_data}

        for my_card_name, my_card in self._name_index.items():
            if my_card_name in bulk_index:
                sf_card = bulk_index[my_card_name]

                # Update our card with valid data
                my_card['color_identity'] = sf_card.get('color_identity', [])
                my_card['type_line'] = sf_card.get('type_line', '')
                my_card['oracle_text'] = sf_card.get('oracle_text', '')
                my_card['cmc'] = sf_card.get('cmc', 0)
                my_card['edhrec_rank'] = sf_card.get('edhrec_rank', 99999)
                my_card['mana_cost'] = sf_card.get('mana_cost', '')
                match_count += 1

        print(f"Successfully enriched {match_count} cards from bulk data.")
        self.enriched = True

    def filter(self, **kwargs):
        filtered = []
        for card in self.cards:
            match = True
            for k, v in kwargs.items():
                # Safety check: ensure key exists before checking
                if k not in card:
                    match = False
                    break
                # Flexible string check (case-insensitive)
                if str(v).lower() not in str(card[k]).lower():
                    match = False
                    break
            if match:
                filtered.append(card)
        return filtered

    def intersection(self, edhrec_list):
        my_card_names = {c['Name'].lower() for c in self.cards if 'Name' in c}
        matches = [name for name in edhrec_list
                   if name.lower() in my_card_names]
        return matches
