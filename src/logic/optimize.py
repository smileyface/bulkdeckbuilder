from logic.lands import color_map
from logic.lands import liquid_land_count
from logic.classifier import classify_card


def optimize_deck(deck_data, collection, target_lands):
    print(f"\n🏗️  DECK ASSEMBLY: {deck_data['commander']}")
    print("-" * 40)

    current_list = set(deck_data["decklist"])
    commander_name = deck_data["commander"]
    role_map = deck_data.get("role_map", {})

    # 1. Surgical Filters
    cmd_obj = collection._name_index.get(commander_name.lower())
    cmd_colors = set(cmd_obj.get("color_identity", []))
    banned_phrases = []

    for code, color_name in color_map.items():
        if code not in cmd_colors:
            banned_phrases.append(f"{color_name} spells you cast")
            banned_phrases.append(f"{color_name} spells cost")
            banned_phrases.append(f"{color_name} creatures you control")

    # 2. Classify Existing
    quotas = {"Ramp": 12, "Draw": 10, "Removal": 12, "Wipe": 2, "Recursion": 2}
    current_stats = {k: 0 for k in quotas}

    for name in current_list:
        card = collection._name_index.get(name.lower())
        if card:
            role = classify_card(card, edhrec_roles=role_map)
            if role in current_stats:
                current_stats[role] += 1

    print(
        f"   Stats: {current_stats['Ramp']} Ramp,"
        f"{current_stats['Draw']} Draw,"
        f"{current_stats['Removal']} Removal"
    )

    # 3. Candidates
    candidates = []
    for card in collection.cards:
        name = card["Name"]
        if "Land" in card.get("type_line", ""):
            continue
        if name in current_list or name == commander_name:
            continue
        if not set(card.get("color_identity", [])).issubset(cmd_colors):
            continue

        text = card.get("oracle_text", "").lower()
        if any(phrase in text for phrase in banned_phrases):
            continue
        candidates.append(card)

    candidates.sort(key=lambda x: x.get("edhrec_rank", 99999))

    # 4. Fill Gaps
    added_log = []

    def add_best_role(role, qty_needed):
        count = 0
        for card in candidates:
            if count >= qty_needed:
                break
            if card["Name"] in current_list:
                continue
            if classify_card(card, edhrec_roles=role_map) == role:
                current_list.add(card["Name"])
                added_log.append(f"+ {card['Name']} ({role})")
                count += 1

    for r, quota in quotas.items():
        if current_stats[r] < quota:
            add_best_role(r, quota - current_stats[r])

    if added_log:
        print(f"   ✅ Added {len(added_log)} Staples:")
        for item in added_log[:5]:
            print(f"      {item}")

    # 5. Trim
    max_non_lands = 99 - liquid_land_count(current_list, collection)
    while len(current_list) < max_non_lands:
        for card in candidates:
            if card["Name"] not in current_list:
                current_list.add(card["Name"])
                break

    if len(current_list) > max_non_lands:
        deck_objects = [
            collection._name_index[name.lower()]
            for name in current_list
            if name.lower() in collection._name_index
        ]
        deck_objects.sort(key=lambda x: x.get("edhrec_rank", 99999),
                          reverse=True)
        trimmed_cards = deck_objects[: len(current_list) - max_non_lands]
        final_list = [
            c["Name"] for c in deck_objects[len(current_list) - max_non_lands:]
        ]
        print("   ✂️  Trimmed excess cards.")
        for card in trimmed_cards:
            print(f"      - {card['Name']}")
        return final_list

    return list(current_list)
