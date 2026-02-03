import json
import csv
from collections import Counter


color_map = {'W': 'white',
             'U': 'blue',
             'B': 'black',
             'R': 'red',
             'G': 'green'}



# --- 1. CONFIG LOADER ---

def load_heuristics(filepath):
    print(f"Loading heuristics from {filepath}...")
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        print(f"Error loading heuristics: {e}")
        return []


# --- 2. CLASSIFICATION ENGINE ---

def classify_card(card, rules, edhrec_roles=None):
    name = card['Name']
    if edhrec_roles and name in edhrec_roles:
        return edhrec_roles[name]

    text = card.get('oracle_text', '').lower()
    type_line = card.get('type_line', '').lower()
    cmc = float(card.get('cmc', 0))
    
    if 'land' in type_line:
        return 'Land'

    for rule in rules:
        # CMC Caps logic
        role = rule['role']
        if role == 'Ramp' and cmc >= 5:
            continue
        if role == 'Removal' and cmc >= 6:
            continue
        if role == 'Draw' and cmc >= 6:
            continue
        if role == 'Recursion' and cmc >= 6:
            continue
        
        # Check Must Have
        match = True
        for phrase in rule['must_have']:
            if phrase not in text:
                match = False
                break
        if not match:
            continue
        
        # Check Must Not
        if 'must_not' in rule:
            for phrase in rule['must_not']:
                if phrase in text:
                    match = False
                    break
        
        if match:
            return role
            
    return 'General'


# --- 3. BUILDER LOGIC ---

def analyze_curve(card_names, collection):
    total_cmc = 0
    count = 0
    for name in card_names:
        card = collection._name_index.get(name.lower())
        if card:
            total_cmc += float(card.get('cmc', 0))
            count += 1
    
    if count == 0:
        return 37, 0.0

    avg_cmc = total_cmc / count
    target_lands = 37
    if avg_cmc > 3.8:
        target_lands = 40
    elif avg_cmc > 3.4:
        target_lands = 38
    elif avg_cmc < 2.4:
        target_lands = 35
    elif avg_cmc < 2.0:
        target_lands = 33
    return target_lands, avg_cmc


def fetch_theme_cards(theme_slug):
    """
    Fetches the EDHRec theme page JSON and extracts card names along with their roles.
    """
    import requests
    import time

    url = f"https://json.edhrec.com/pages/{theme_slug}.json"
    role_map = {}
    theme_cards = []

    try:
        response = requests.get(url)
        if response.status_code != 200:
            return [], {}

        data = response.json()
        card_lists = data.get('container', {}).get('json_dict', {}).get('cardlists', [])

        # Map specific headers to our internal roles
        header_to_role = {
            'High Synergy Cards': 'Synergy',
            'Top Cards': 'Synergy',
            'Creatures': 'Creature',
            'Instants': 'Instant',
            'Sorceries': 'Sorcery',
            'Artifacts': 'Artifact',
            'Enchantments': 'Enchantment',
            'Mana Ramp': 'Ramp',
            'Card Draw': 'Draw',
            'Removal': 'Removal',
            'Board Wipes': 'Wipe'
        }

        for cl in card_lists:
            header = cl.get('header')
            role = header_to_role.get(header, 'General')
            
            for card_view in cl.get('cardviews', []):
                name = card_view['name']
                theme_cards.append(name)
                # If a card appears in multiple lists, the first one (usually higher synergy) wins
                if name not in role_map:
                    role_map[name] = role

        return theme_cards, role_map

    except Exception as e:
        print(f"Error fetching theme {theme_slug}: {e}")
        return [], {}


# --- 4. OPTIMIZER ---

def optimize_deck(deck_data, collection, target_lands, heuristic_rules): # <--- FIXED SIGNATURE
    print(f"\n🏗️  DECK ASSEMBLY: {deck_data['commander']}")
    print("-" * 40)

    current_list = set(deck_data['decklist'])
    commander_name = deck_data['commander']
    role_map = deck_data.get('role_map', {})

    # 1. Surgical Filters
    cmd_obj = collection._name_index.get(commander_name.lower())
    cmd_colors = set(cmd_obj.get('color_identity', []))
    banned_phrases = []

    for code, color_name in color_map.items():
        if code not in cmd_colors:
            banned_phrases.append(f"{color_name} spells you cast")
            banned_phrases.append(f"{color_name} spells cost")
            banned_phrases.append(f"{color_name} creatures you control")

    # 2. Classify Existing
    quotas = {'Ramp': 12, 'Draw': 10, 'Removal': 12, 'Wipe': 2, 'Recursion': 2}
    current_stats = {k: 0 for k in quotas}
    
    for name in current_list:
        card = collection._name_index.get(name.lower())
        if card:
            role = classify_card(card, heuristic_rules, edhrec_roles=role_map)
            if role in current_stats:
                current_stats[role] += 1

    print(f"   Stats: {current_stats['Ramp']} Ramp,"
          f"{current_stats['Draw']} Draw,"
          f"{current_stats['Removal']} Removal")

    # 3. Candidates
    candidates = []
    for card in collection.cards:
        name = card['Name']
        if 'Land' in card.get('type_line', ''):
            continue
        if name in current_list or name == commander_name:
            continue
        if not set(card.get('color_identity', [])).issubset(cmd_colors):
            continue
        
        text = card.get('oracle_text', '').lower()
        if any(phrase in text for phrase in banned_phrases):
            continue
        candidates.append(card)
        
    candidates.sort(key=lambda x: x.get('edhrec_rank', 99999))

    # 4. Fill Gaps
    added_log = []
    def add_best_role(role, qty_needed):
        count = 0
        for card in candidates:
            if count >= qty_needed: break
            if card['Name'] in current_list: continue 
            if classify_card(card, heuristic_rules, edhrec_roles=role_map) == role:
                current_list.add(card['Name'])
                added_log.append(f"+ {card['Name']} ({role})")
                count += 1

    for r, quota in quotas.items():
        if current_stats[r] < quota:
            add_best_role(r, quota - current_stats[r])

    if added_log:
        print(f"   ✅ Added {len(added_log)} Staples:")
        for item in added_log[:5]: print(f"      {item}")

    # 5. Trim
    max_non_lands = 99 - target_lands
    while len(current_list) < max_non_lands:
        for card in candidates:
            if card['Name'] not in current_list:
                current_list.add(card['Name'])
                break
    
    if len(current_list) > max_non_lands:
        deck_objects = [collection._name_index[name.lower()] for name in current_list if name.lower() in collection._name_index]
        deck_objects.sort(key=lambda x: x.get('edhrec_rank', 99999), reverse=True)
        final_list = [c['Name'] for c in deck_objects[len(current_list)-max_non_lands:]]
        print("   ✂️  Trimmed excess cards.")
        return final_list

    return list(current_list)


# --- 4. MANA BASE LOGIC ---

def _add_non_basics(deck_list, collection, slots_available, commander_name):
    """
    Scans collection for Valid Non-Basic Lands.
    Heuristic: Off-Color Fetches (Polluted Delta in Izzet) are only allowed
    if they are High Rank (< 600). Low rank off-color fetches
    (Panoramas) are banned.
    """
    cmd_obj = collection._name_index.get(commander_name.lower())
    cmd_colors = set(cmd_obj.get('color_identity', []))

    non_basics = []

    for card in collection.cards:
        name = card['Name']
        type_line = card.get('type_line', '').lower()
        rank = card.get('edhrec_rank', 99999)

        # 1. Base Filters
        if 'land' not in type_line:
            continue
        if 'basic' in type_line:
            continue
        if name in deck_list or name == commander_name:
            continue

        # 2. Identity Check (Must be legally playable)
        if not set(card.get('color_identity', [])).issubset(cmd_colors):
            continue

        # 3. "Smart" Fetch Logic
        text = card.get('oracle_text', '').lower()

        # Identify land types mentioned in the text
        # (e.g. "search... island or swamp")
        mentioned_types = [t for t, c in color_map.items() if t in text]

        if mentioned_types:
            mentioned_colors = {color_map[t] for t in mentioned_types}

            # Intersection: Does it fetch ANY of our colors?
            # Bant Panorama (W, U, G) vs Izzet (U, R) -> Matches U.
            if not mentioned_colors.intersection(cmd_colors):
                continue

            # OFF-COLOR PENALTY
            # Check if it mentions colors we DO NOT have.
            # Polluted Delta (U, B) in Izzet (U, R) -> Mentions B (Off-color).
            off_color_hits = mentioned_colors - cmd_colors

            if off_color_hits:
                # It fetches an off-color type.
                # We ONLY allow this if it is a "High Efficiency" fetch
                # (Rank < 600).
                # Polluted Delta (Rank 30) -> PASS.
                # Bant Panorama (Rank 2500) -> FAIL.
                if rank > 600:
                    continue

        non_basics.append(card)

    # Sort best first
    non_basics.sort(key=lambda x: x.get('edhrec_rank', 99999))

    added_count = 0
    log = []

    for card in non_basics:
        if added_count >= slots_available:
            break

        deck_list.append(card['Name'])
        added_count += 1
        log.append(card['Name'])

    if log:
        print(f"      ✅ Added {len(log)} Non-Basic Lands:")
        for name in log[:3]:
            print(f"         - {name}")
        if len(log) > 3:
            print(f"         ...and {len(log)-3} more.")

    return deck_list, added_count


def _fill_basics(deck_list, collection, slots_needed, commander_name):
    """
    Fills remaining slots with Basic Lands based on Pip Count.
    """
    if slots_needed <= 0:
        return deck_list

    pip_counts = {'W': 0, 'U': 0, 'B': 0, 'R': 0, 'G': 0}

    # 1. Count Pips (Only from non-lands in the deck)
    for name in deck_list:
        if name == commander_name:
            continue
        card = collection._name_index.get(name.lower())
        if not card:
            continue
        if 'land' in card.get('type_line', '').lower():
            continue  # Don't count land pips

        cost = card.get('mana_cost', '')
        for c in pip_counts:
            pip_counts[c] += cost.count(c)

    total_pips = sum(pip_counts.values())
    cmd_obj = collection._name_index.get(commander_name.lower())
    cmd_colors = set(cmd_obj.get('color_identity', []))

    # 2. Handle Colorless/No-Pip Decks
    if total_pips == 0:
        if not cmd_colors:  # Colorless Commander (Karn/Eldrazi)
            deck_list.extend(['Wastes'] * slots_needed)
            return deck_list

        per_color = slots_needed // max(1, len(cmd_colors))
        rem = slots_needed % max(1, len(cmd_colors))

        for c in cmd_colors:
            deck_list.extend([color_map[c]] * per_color)
        if rem > 0:
            deck_list.extend([color_map[list(cmd_colors)[0]]] * rem)
        return deck_list

    # 3. Assign Basics
    sorted_colors = sorted(pip_counts.items(),
                           key=lambda x: x[1],
                           reverse=True)
    basics_added = 0

    for color_code, count in sorted_colors:
        if count == 0:
            continue
        ratio = count / total_pips
        qty = int(slots_needed * ratio)

        if qty == 0 and count > 0:
            qty = 1

        # Overflow protection
        if basics_added + qty > slots_needed:
            qty = slots_needed - basics_added

        deck_list.extend([color_map[color_code]] * qty)
        basics_added += qty
        print(f"      + {qty} {color_map[color_code]}")

    # 4. Rounding
    remainder = slots_needed - basics_added
    if remainder > 0:
        primary = color_map[sorted_colors[0][0]]
        deck_list.extend([primary] * remainder)
        print(f"      + {remainder} {primary} (Rounding)")

    return deck_list


def add_smart_lands(deck_list, collection, total_lands_needed, commander_name):
    print(f"\n   🌍 MANA BASE ({total_lands_needed} slots)")

    # Phase 1: Non-Basics
    deck_list, nb_count = _add_non_basics(deck_list,
                                          collection,
                                          total_lands_needed,
                                          commander_name)

    # Phase 2: Basics
    remaining_slots = total_lands_needed - nb_count
    deck_list = _fill_basics(deck_list,
                             collection,
                             remaining_slots,
                             commander_name)

    return deck_list


def check_curve_health(deck_list, collection):
    stats = {1:0, 2:0, 3:0, 4:0, 5:0, 6:0}
    for name in deck_list:
        card = collection.get(name)
        cmc = int(card['cmc'])
        if cmc >= 6: stats[6] += 1
        elif cmc in stats: stats[cmc] += 1
    
    # Heuristic Warnings based on Source 1
    if stats[2] < 12: print("⚠️ Warning: Low on 2-drops (Target ~18)") [cite: 176]
    if stats[4] > 12: print("⚠️ Warning: Bloated 4-drop slot (Target ~10)") [cite: 183]
    if stats[6] > 6:  print("⚠️ Warning: Too many expensive spells (Target ~5)") [cite: 189]

def check_rule(text, must_have, must_not=None):
    """
    Returns True if 'text' contains all strings in 'must_have'
    AND none of the strings in 'must_not'.
    """
    if must_not:
        for phrase in must_not:
            if phrase in text:
                return False

    for phrase in must_have:
        if phrase not in text:
            return False

    return True
