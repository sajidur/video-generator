"""Casting: make the actor match the story in every shot.

Runs after planning (AI or keywords) and decides, per shot:
  hero      who the main character is (gender + age; ages up when the story jumps ahead)
  outfit    what they wear (poor clothes, shop apron, suit, ...), carried over between shots
  character what they do; never "none" when the line is about them
"""
import re

from . import vocab
from .text import count, has, norm

W = vocab.CAST_WORDS
WORK_OUTFITS = {"suit", "shopkeeper", "doctor", "worker", "farmer"}  # grown-up jobs
EVIDENCE = {"work": {"laptop", "phone", "gear", "factory"}, "read": {"books"}, "carry": set(),
            "sit": set(), "walk": {"car"}, "run": set()}


def _best(text, group):
    """Best keyword match for actions/outfits (English words + Bangla stems)."""
    scores = {}
    for name, en in vocab.KEYWORDS[group].items():
        n = count(text, en, "", vocab.KEYWORDS_BN[group].get(name, ""))
        if n:
            scores[name] = n
    return max(scores, key=scores.get) if scores else None


def detect_name(text):
    m = re.search(r"\b(?:named|called)\s+([A-Z][a-z]+)", text)
    if m:
        return m.group(1)
    m = re.search(r"([ঀ-৿]+)\s+নাম(?:ে|ের|ক)", norm(text))
    return m.group(1) if m else ""


def detect_gender(text):
    male = count(text, *W["male"])
    female = count(text, *W["female"])
    return "male" if male > female else "female" if female > male else None


def _grows_up(text):
    t = norm(text.lower())
    return any(norm(p) in t for p in vocab.GROW_UP)


def cast(board):
    shots = board["shots"]
    story = " ".join(s["narration"] for s in shots)
    hero = board.get("hero") if board.get("hero") in vocab.HEROES else "boy"
    gender = vocab.HERO_GENDER[hero]
    age = vocab.HERO_AGE[hero]
    if hero != "robot":
        gender = detect_gender(story) or gender
        opening = " ".join(s["narration"] for s in shots[:2])
        if has(opening, W["old"]):
            age = 2
        elif has(opening, W["child"]):
            age = 0
        hero = vocab.HERO_FORMS[(gender, age)]
    name = board.get("hero_name") or detect_name(story)
    board["hero_name"] = name
    # Explainer (talks to "you", no named character): one consistent adult presenter.
    # Story (a named or introduced character): the actor follows the plot.
    talks_to_viewer = sum(1 for s in shots if has(s["narration"], W["viewer"]))
    explainer = not name and talks_to_viewer >= 2
    if explainer and hero != "robot":
        age = max(age, 1)
        hero = vocab.HERO_FORMS[(gender, age)]
    board["hero"] = hero
    board["mode"] = "explainer" if explainer else "story"
    first = shots[0].get("outfit") if shots and shots[0].get("outfit") in vocab.OUTFITS else None
    outfit = board.get("outfit") if board.get("outfit") in vocab.OUTFITS else (first or "casual")
    if explainer and outfit not in ("casual", "suit"):
        outfit = "casual"  # a presenter, not a farmer/doctor picked at random

    for s in shots:
        t = s["narration"]
        # outfit: only changes when the line itself says so (shop, poor, successful...);
        # a presenter in an explainer keeps one outfit for the whole video
        keyword = None if explainer else _best(t, "outfits")
        if keyword:
            outfit = keyword
        # age: the story jumps ahead, or the hero now has a grown-up job
        if hero != "robot" and age == 0 and (_grows_up(t) or outfit in WORK_OUTFITS):
            age = 1
            if outfit == "poor" and not keyword:
                outfit = "casual"
        s["outfit"] = outfit
        s["hero"] = hero if hero == "robot" else vocab.HERO_FORMS[(gender, age)]

        # presence + action
        about_hero = has(t, W["hero"]) or (name and norm(name).lower() in norm(t).lower()) \
            or has(t, W["male"] if gender == "male" else W["female"])
        acted = _best(t, "actions")
        # very specific actions need support in the line or the props, else they look random
        need = EVIDENCE.get(s["character"])
        if need is not None and acted != s["character"] and not (need & set(s["props"])):
            s["character"] = acted or ("talk" if explainer else "idle")
        if s["character"] == "none":
            if about_hero:
                s["character"] = acted or "idle"
            elif has(t, W["viewer"]):
                s["character"] = "talk"  # the hero presents the takeaway to the viewer
        elif s["character"] == "idle" and acted:
            s["character"] = acted
        if s["character"] == "idle" and ("person" in s["props"] or explainer):
            s["character"] = "talk"  # talking to someone / presenting to the camera
        delivering = count(t, vocab.KEYWORDS["actions"]["carry"], "", vocab.KEYWORDS_BN["actions"]["carry"])
        if s["character"] in ("walk", "run") and delivering:
            s["character"] = "carry"
    return board
