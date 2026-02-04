import json


def load_heuristics(filepath):
    print(f"Loading heuristics from {filepath}...")
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        print(f"Error loading heuristics: {e}")
        return []
