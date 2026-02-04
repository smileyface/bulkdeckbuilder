"""
This module provides logic for classifying Magic: The Gathering cards into
functional deck-building roles (e.g., Ramp, Draw, Removal) based on their
oracle text, type line, and mana cost, utilizing both heuristic rules and
external data.
"""


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
