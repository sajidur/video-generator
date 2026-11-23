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
WORK_OUTFITS = {"suit", "shopkeeper", "doctor", "worker", "farmer", "office", "chef", "delivery", "police",
                "teacher"}  # grown-up jobs
# Specific actions look random unless the line, a prop or the place supports them.
EVIDENCE = {"work": {"laptop", "phone", "gear", "factory"}, "read": {"books"}, "carry": {"boxes"},
            "sit": set(), "walk": {"car"}, "run": set(), "phone": {"phone", "likes", "laptop"},
            "buy": {"shopping_bag", "shopping_cart", "price_tag", "produce"},
            "give": {"gift", "boxes", "shopping_bag"}, "write": {"whiteboard"}, "announce": {"megaphone"},
            "drink": set(), "push_cart": {"shopping_cart"}, "search": {"magnifier"}, "shrug": {"question"},
            "shake_hands": set(), "clap": {"trophy"}, "thumbs_up": {"rating", "likes"}}
EVIDENCE_PLACES = {"drink": {"cafe"}, "push_cart": {"shop"}, "buy": {"shop", "market", "cafe"},
                   "give": {"shop", "market", "cafe"}, "write": {"office", "classroom"}, "carry": {"warehouse"}}


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


def is_explainer(board):
    """A video that talks to "you" without a named character (vs. a story about someone)."""
    shots = board["shots"]
    name = board.get("hero_name") or detect_name(" ".join(s["narration"] for s in shots))
    return not name and sum(1 for s in shots if has(s["narration"], W["viewer"])) >= 2


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
    explainer = is_explainer(board)
    if explainer and hero != "robot":
        age = max(age, 1)
        hero = vocab.HERO_FORMS[(gender, age)]
    board["hero"] = hero
    board["mode"] = "explainer" if explainer else "story"
    first = shots[0].get("outfit") if shots and shots[0].get("outfit") in vocab.OUTFITS else None
    outfit = board.get("outfit") if board.get("outfit") in vocab.OUTFITS else (first or "casual")
    if explainer and outfit not in vocab.PRESENTER_OUTFITS:
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
        # very specific actions need support in the line, the props or the place, else they look random
        need = EVIDENCE.get(s["character"])
        if need is not None and acted != s["character"] and not (need & set(s["props"])) \
                and s["environment"] not in EVIDENCE_PLACES.get(s["character"], ()):
            s["character"] = acted or ("talk" if explainer else "idle")
        if s["character"] == "none":
            if about_hero:
                s["character"] = acted or "idle"
            elif has(t, W["viewer"]):
                s["character"] = "talk"  # the hero presents the takeaway to the viewer
        elif s["character"] == "idle" and acted and (about_hero or explainer):
            s["character"] = acted  # in a story the hero only acts out lines about themselves
        if s["character"] == "idle" and ("person" in s["props"] or explainer):
            s["character"] = "talk"  # talking to someone / presenting to the camera
        delivering = count(t, vocab.KEYWORDS["actions"]["carry"], "", vocab.KEYWORDS_BN["actions"]["carry"])
        if s["character"] in ("walk", "run") and delivering:
            s["character"] = "carry"
        # a named person from the cast who is mentioned in this line is in the shot
        names = [m["name"] for m in board.get("cast", [])]
        if s.get("with") not in names:
            s.pop("with", None)
        for m in names:
            if norm(m).lower() in norm(t).lower():
                s["with"] = m
        # selling, buying, a handshake or listening needs someone to do it with
        if (s["character"] in vocab.PARTNER_ACTIONS or s.get("with")) and not {"person", "crowd"} & set(s["props"]):
            s["props"] = (["person"] + s["props"])[:3]
    return board


NO_SPEAK = {"none", "listen", "read", "sad", "run", "drink"}
DIALOGUE = re.compile(r'["“”]')


def speaker(board, shot):
    """Who says this line on screen: "hero", "partner" or "" (a narrator we don't see).

    Explainers: the presenter speaks every line they are in (unless busy drinking, reading...).
    Stories: a narrator tells the story; a character only speaks lines that are dialogue ("...")."""
    act = shot.get("character", "none")
    mode = board.get("mode") or ("explainer" if is_explainer(board) else "story")
    if mode == "explainer":
        return "" if act in NO_SPEAK else "hero"
    if DIALOGUE.search(shot.get("narration", "")):
        if act == "listen" and ("person" in shot.get("props", []) or shot.get("with")):
            return "partner"
        if act not in NO_SPEAK:
            return "hero"
    return ""
