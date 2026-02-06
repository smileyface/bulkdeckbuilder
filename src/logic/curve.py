

def check_curve_health(deck_list, collection):
    stats = {1: 0,
             2: 0,
             3: 0,
             4: 0,
             5: 0,
             6: 0}
    for name in deck_list:
        card = collection.get(name)
        cmc = int(card['cmc'])
        if cmc >= 6:
            stats[6] += 1
        elif cmc in stats:
            stats[cmc] += 1

    # Heuristic Warnings based on Source 1
    if stats[2] < 12:
        print("⚠️ Warning: Low on 2-drops (Target ~18)")
    if stats[4] > 12:
        print("⚠️ Warning: Bloated 4-drop slot (Target ~10)")
    if stats[6] > 6:
        print("⚠️ Warning: Too many expensive spells (Target ~5)")


# Will be reimplemented to actually deal with the complexities of commander 
# curve later.
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
    return total_cmc, avg_cmc