from collections import Counter


# --- CONSOLE REPORTING ---

def print_candidate(commander, theme, score):
    """Prints a standard message when a viable deck is found."""
    print(f"   -> Found Valid Deck: {theme} (Score: {score})")


def print_deck_summary(deck_data, target_lands, avg_cmc):
    """Prints the final 'Trophy Screen' for the constructed deck."""
    commander = deck_data['commander']
    theme = deck_data['theme']
    # +1 for the Commander itself
    total_cards = len(deck_data['decklist']) + 1

    print("\n" + "="*60)
    print(f"🏆  COMPLETED: {commander}")
    print(f"    Theme:     {theme}")
    print("-" * 60)
    print(f"    Total:     {total_cards} Cards")
    print(f"    Lands:     {target_lands} slots")
    print(f"    Avg CMC:   {avg_cmc:.2f}")
    print("="*60 + "\n")


# --- FILE EXPORT ---

def export_archidekt_txt(filename, deck_data, collection):
    commander_name = deck_data['commander']
    full_list = deck_data['decklist']

    print(f"   -> Exporting file: {filename}...")

    try:
        with open(filename, 'w', encoding='utf-8') as f:
            # 1. Write Commander
            cmd_obj = collection._name_index.get(commander_name.lower())
            cmd_set = f"({cmd_obj['Set code']})"\
                if cmd_obj and 'Set code' in cmd_obj else ""

            # Use specific Archidekt syntax for Commander Zone
            f.write(f"1x {commander_name} {cmd_set} [Commander{{top}}]\n")

            # 2. Write Decklist (Grouped & Sorted)
            counts = Counter(full_list)
            for name, qty in sorted(counts.items()):
                if name.lower() == commander_name.lower():
                    continue

                # Lookup data
                card_data = collection._name_index.get(name.lower())

                # Optional: Add set codes, but skip for Basic Lands
                # to keep it clean
                set_str = ""
                if card_data and 'Set code' in card_data:
                    if "Basic Land" not in card_data.get('type_line', ''):
                        set_str = f"({card_data['Set code']})"
                collector_number = ""
                if card_data and 'Collector number' in card_data:
                    if "Basic Land" not in card_data.get('type_line', ''):
                        collector_number = f" {card_data['Collector number']}"

                f.write(f"{qty}x {name} {set_str} {collector_number}\n")

        print(f"   -> Success! Saved to {filename}")

    except Exception as e:
        print(f"   -> Error saving file: {e}")
