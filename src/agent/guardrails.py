import re


def suspicious(text):
    """Signal complémentaire ; les autorisations ne dépendent jamais de ce détecteur."""
    return bool(re.search(r"ignore.{0,50}(instruction|contrainte|regle)|publie.{0,40}sans.{0,20}(valid|accord)|system\s*:|reveal.{0,30}secret|exfiltr|<\|im_start\|>", text, re.I | re.S))


def unsafe_request(text):
    return bool(re.search(r"(?:demarre|démarre|pilote|désactive|desactive|contourne).{0,30}(?:machine|automate|securite|sécurité)", text, re.I))
