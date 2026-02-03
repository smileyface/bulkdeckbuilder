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