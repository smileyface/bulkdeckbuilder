import time
import os
import csv
import glob

import src.output as output
import src.externals as externals
from loaders import configs
from logic import (curve, lands, optimize)
from logic import classifier
from src.collection import Collection

# --- CONFIGURATION ---
# Only log decks if they have at least this much synergy
MIN_SCAN_SCORE = 25
# Only EXPORT decks if they have at least this much synergy
VICTORY_THRESHOLD = 45
MAX_EXPORT_COUNT = 5    # Maximum number of decks to build


def load_collection_from_directory(directory_path):
    """
    Walks a directory, finds all .csv files, loads them, and combines them.
    Includes a fallback for when csv.Sniffer fails.
    """
    all_cards = []
    # Find all CSV files in the folder
    csv_files = glob.glob(os.path.join(directory_path, "*.csv"))

    print(f"Found {len(csv_files)} CSV files in '{directory_path}'")

    for filename in csv_files:
        print(f"Loading {filename}...")
        try:
            with open(filename, mode='r', encoding='utf-8-sig') as csvfile:
                # Read a sample to guess format
                sample = csvfile.read(2048)
                csvfile.seek(0)

                try:
                    dialect = csv.Sniffer().sniff(sample)
                except csv.Error:
                    # FALLBACK: If Sniffer fails, force standard CSV (comma)
                    print("   Warning: Could not detect delimiter for "
                          f"{filename}. Defaulting to comma.")
                    dialect = csv.excel

                reader = csv.DictReader(csvfile, dialect=dialect)

                # Clean up whitespace in keys/values and add to big list
                file_cards = []
                for row in reader:
                    # Filter out empty keys that might happen
                    # from trailing commas
                    clean_row = {k.strip(): v.strip() for k,
                                 v in row.items() if k}
                    file_cards.append(clean_row)

                all_cards.extend(file_cards)
                print(f"   -> Loaded {len(file_cards)} cards.")

        except Exception as e:
            print(f"Error loading {filename}: {e}")

    print(f"Total cards loaded: {len(all_cards)}")
    return Collection(all_cards)


def setup_environment():
    """Loads the card collection and configuration rules."""
    print("--- 1. ENVIRONMENT SETUP ---")

    print("Loading configuration files...")
    # Load Logic Rules
    classifier.spell_heuristic_rules = configs.load_heuristics(os.path.join(
        "data",
        "spell_heuristics.json"))
    classifier.land_heuristic_rules = configs.load_heuristics(os.path.join(
        "data",
        "land_heuristics.json"))

    # Load Collection
    my_collection = load_collection_from_directory("./manabox_export")
    my_collection.enrich_from_local_bulk("oracle-cards.json")

    return my_collection


def analyze_single_commander(cmd, collection):
    """
    Fetches themes for ONE commander and returns a list of
    valid candidate decks.
    """
    valid_candidates = []

    # Fetch EDHRec data
    edh_data = externals.fetch_edhrec_data(cmd['Name'])

    if not edh_data or not edh_data.get('themes'):
        return []

    # Check top 10 themes
    for theme in edh_data['themes'][:10]:
        # Unpack result (Safe handling if fetcher returns tuple or list)
        fetch_result = externals.fetch_theme_cards(theme['slug'])

        if isinstance(fetch_result, tuple):
            perfect_list, role_map = fetch_result
        else:
            perfect_list = fetch_result
            role_map = {}

        # Calculate Synergy
        owned_synergy = collection.intersection(perfect_list)
        score = len(owned_synergy)

        # Viability Threshold
        if score >= 20:
            # Use output module for printing
            output.print_candidate(cmd['Name'], theme['name'], score)

            valid_candidates.append({
                'commander': cmd['Name'],
                'theme': theme['name'],
                'score': score,
                'decklist': owned_synergy,
                'role_map': role_map
            })

        # API Throttling
        time.sleep(0.1)

    return valid_candidates


def run_analysis_pipeline(collection):
    """Iterates through all Legendary Creatures to find matches."""
    print("\n--- 2. ANALYSIS LOOP ---")

    commanders = collection.filter(type_line="Legendary Creature")
    commanders.sort(key=lambda x: x['Name'])

    total = len(commanders)
    print(f"Scanning {total} commanders...")

    all_candidates = []

    for i, cmd in enumerate(commanders):
        print(f"[{i+1}/{total}] Analyzing {cmd['Name']}...")

        candidates = analyze_single_commander(cmd, collection)
        all_candidates.extend(candidates)

    return all_candidates


def build_winner(candidate, collection):
    """
    Takes the winning candidate, runs the optimization logic, and exports.
    """
    print("\n--- 3. DECK CONSTRUCTION ---")

    # 1. Analyze Curve
    target_lands, avg_cmc = curve.analyze_curve(candidate['decklist'],
                                                collection)

    # 2. Optimize (Add Staples / Cut Chaff)
    spell_list = optimize.optimize_deck(candidate,
                                        collection,
                                        target_lands)

    # 3. Add Lands (Pip Logic)
    full_decklist, target_lands = lands.add_smart_lands(spell_list,
                                                        collection,
                                                        candidate['commander'])

    # Update Object
    candidate['decklist'] = full_decklist

    # 4. Report & Export
    output.print_deck_summary(candidate, target_lands, avg_cmc)

    safe_name = candidate['commander'].replace(" ", "_").replace(",", "")
    safe_theme = candidate['theme'].replace(" ", "_")
    filename = f"{safe_name}_{safe_theme}.txt"

    output.export_archidekt_txt(filename, candidate, collection)


def main():
    # 1. Setup
    my_collection = setup_environment()

    # 2. Analyze All
    candidates = run_analysis_pipeline(my_collection)

    # 3. Filter & Build Winners
    if candidates:
        # Sort Highest Score First
        candidates.sort(key=lambda x: x['score'], reverse=True)

        # LOGIC: Top 5 OR Score > 45 (Whichever is least / Intersection)
        # 1. Filter out anything below the Victory Threshold
        high_quality = [c for c in candidates
                        if c['score'] >= VICTORY_THRESHOLD]

        # 2. Take the Top 5 of the survivors
        winners = high_quality[:MAX_EXPORT_COUNT]

        print("\n--- 3. RESULTS ---")
        print(f"Found {len(candidates)} valid themes.")
        print(f"Filtered to {len(high_quality)} "
              f"above score {VICTORY_THRESHOLD}.")
        print(f"Exporting top {len(winners)}...")

        if not winners:
            print(f"❌ No decks met the Victory Threshold"
                  f"of {VICTORY_THRESHOLD}.")

        for winner in winners:
            build_winner(winner, my_collection)

    else:
        print("\n❌ No viable decks found matching initial criteria.")


if __name__ == "__main__":
    main()
