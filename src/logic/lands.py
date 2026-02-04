color_map = {'W': 'white',
             'U': 'blue',
             'B': 'black',
             'R': 'red',
             'G': 'green'}


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
