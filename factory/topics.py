"""Load the topics you provide.

topics.txt         one topic per line; the local AI writes the narration.
                   "kotler-001 | title" gives the topic a short English name (output folder).
topics/<name>.txt  first line = title, the rest = your own narration (optional).
Lines starting with # are ignored in both.
"""
import hashlib
import re
from dataclasses import dataclass

from . import config


@dataclass
class Topic:
    title: str
    narration: str = ""
    source: str = ""
    file_name: str = ""
    id: str = ""  # optional short English name: "kotler-001 | title" in topics.txt

    @property
    def slug(self):
        if self.id and slugify(self.id) == self.id.lower():
            return self.id.lower()
        s = slugify(self.title)
        if s.startswith("topic-") and self.file_name:  # non-English title: name the folder after the file
            return slugify(self.file_name)
        return s

    @property
    def lang(self):
        return detect_lang(self.title + " " + self.narration)


def slugify(text):
    s = re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")[:60].strip("-")
    return s or "topic-" + hashlib.sha1(text.encode("utf-8")).hexdigest()[:8]


def detect_lang(text):
    """'bn' when the text is mostly Bangla script, else 'en'."""
    bangla = sum(1 for ch in text if "ঀ" <= ch <= "৿")
    latin = sum(1 for ch in text if ch.isascii() and ch.isalpha())
    return "bn" if bangla > latin else "en"


def _lines(path):
    return [ln.strip() for ln in path.read_text(encoding="utf-8-sig").splitlines()]


def load_topics():
    topics = []
    if config.TOPICS_FILE.exists():
        for line in _lines(config.TOPICS_FILE):
            if line and not line.startswith("#"):
                tid, sep, title = line.partition(" | ")
                if sep and tid.strip().isascii() and title.strip():
                    topics.append(Topic(title.strip(), source=config.TOPICS_FILE.name, id=tid.strip()))
                else:
                    topics.append(Topic(line, source=config.TOPICS_FILE.name))
    if config.TOPICS_DIR.is_dir():
        for path in sorted(config.TOPICS_DIR.glob("*.txt")):
            lines = [ln for ln in _lines(path) if not ln.startswith("#")]
            while lines and not lines[0]:
                lines.pop(0)
            if not lines:
                continue
            narration = " ".join(ln for ln in lines[1:] if ln)
            topics.append(Topic(lines[0], narration, source=f"topics/{path.name}", file_name=path.stem))
    seen, unique = set(), []
    for t in topics:
        if t.slug not in seen:
            seen.add(t.slug)
            unique.append(t)
    return unique
