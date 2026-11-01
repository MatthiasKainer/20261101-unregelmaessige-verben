"""The 28 irregular verbs found on the three provided workbook pages.

The 21 verbs in exercise 7 form the core; seven additional verbs appear in
other exercises, the dialogue, or task instructions. Modal 'can' is excluded,
as it is not part of the workbook's infinitive -> simple-past verb practice.

Past participles follow British school usage (get → got, not gotten).
"""
from __future__ import annotations

from dataclasses import dataclass
import random


@dataclass(frozen=True)
class Verb:
    infinitive: str
    simple_past: str
    distractor_a: str
    distractor_b: str
    source: str
    past_participle: str
    distractor_c: str
    pattern: str
    german: str
    sentence: str
    signal: str

    def options(self, rng: random.Random, count: int = 3) -> tuple[str, ...]:
        answers = [self.simple_past, self.distractor_a, self.distractor_b]
        if count >= 4:
            answers.append(self.distractor_c)
        rng.shuffle(answers)
        return tuple(answers)

    def boss_options(self, rng: random.Random, stage: str) -> tuple[str, ...]:
        if stage == "participle":
            return self._participle_options(rng)
        answers = [self.simple_past, self.distractor_a, self.distractor_b, self.distractor_c]
        return _shuffle_unique(answers, rng, self.past_participle)

    def _participle_options(self, rng: random.Random) -> tuple[str, ...]:
        pool = [
            self.past_participle,
            self.infinitive,
            self.simple_past,
            self.distractor_a,
            self.distractor_b,
            self.distractor_c,
            self.infinitive + "ed",
        ]
        return _shuffle_unique(pool, rng, self.past_participle)


def _shuffle_unique(pool: list[str], rng: random.Random, correct: str) -> tuple[str, ...]:
    uniq: list[str] = []
    for item in pool:
        if item and item not in uniq:
            uniq.append(item)
    wrong = [item for item in uniq if item != correct]
    while len(wrong) < 3:
        extra = correct + "s"
        if extra not in wrong and extra != correct:
            wrong.append(extra)
        else:
            wrong.append(f"{correct}-{len(wrong)}")
    answers = [correct, *wrong[:3]]
    rng.shuffle(answers)
    return tuple(answers)


# The correct simple past is always a single selectable answer. Both past
# forms of 'be' are displayed together, so neither 'was' nor 'were' is wrong.
VERBS: tuple[Verb, ...] = (
    Verb("be", "was / were", "be", "beed", "Verb-Liste, S. 34",
         "been", "been", "ABC", "sein → war", "Yesterday I ___ at school.", "Yesterday"),
    Verb("become", "became", "become", "becomed", "Verb-Liste, S. 34",
         "become", "becamed", "ABA", "werden → wurde", "Last year she ___ a doctor.", "Last year"),
    Verb("bring", "brought", "bring", "bringed", "Verb-Liste, S. 34",
         "brought", "brang", "ABB", "bringen → brachte", "He ___ his bag yesterday.", "yesterday"),
    Verb("buy", "bought", "buy", "buyed", "Verb-Liste, S. 34",
         "bought", "boughted", "ABB", "kaufen → kaufte", "I ___ a ticket last week.", "last week"),
    Verb("come", "came", "come", "comed", "Verb-Liste, S. 34",
         "come", "camed", "ABA", "kommen → kam", "They ___ home late yesterday.", "yesterday"),
    Verb("do", "did", "do", "doed", "Verb-Liste, S. 34",
         "done", "done", "ABC", "tun → tat", "I ___ my homework yesterday.", "yesterday"),
    Verb("drink", "drank", "drink", "drinked", "Verb-Liste, S. 34",
         "drunk", "drunk", "ABC", "trinken → trank", "She ___ milk this morning.", "this morning"),
    Verb("eat", "ate", "eat", "eated", "Verb-Liste, S. 34",
         "eaten", "eaten", "ABC", "essen → aß", "We ___ pizza last night.", "last night"),
    Verb("get", "got", "get", "getted", "Verb-Liste, S. 34",
         "got", "gotted", "ABB", "bekommen → bekam", "I ___ a letter yesterday.", "yesterday"),
    Verb("go", "went", "go", "goed", "Verb-Liste, S. 34",
         "gone", "gone", "ABC", "gehen → ging", "Yesterday I ___ to school.", "Yesterday"),
    Verb("give", "gave", "give", "gived", "Verb-Liste, S. 34",
         "given", "given", "ABC", "geben → gab", "She ___ me a gift yesterday.", "yesterday"),
    Verb("have", "had", "have", "haved", "Verb-Liste, S. 34",
         "had", "haded", "ABB", "haben → hatte", "I ___ a good day yesterday.", "yesterday"),
    Verb("keep", "kept", "keep", "keeped", "Verb-Liste, S. 34",
         "kept", "keept", "ABB", "behalten → behielt", "He ___ the secret last year.", "last year"),
    Verb("make", "made", "make", "maked", "Verb-Liste, S. 34",
         "made", "maded", "ABB", "machen → machte", "They ___ a cake yesterday.", "yesterday"),
    Verb("meet", "met", "meet", "meeted", "Verb-Liste, S. 34",
         "met", "meat", "ABB", "treffen → traf", "I ___ my friend yesterday.", "yesterday"),
    Verb("put", "put", "putted", "putt", "Verb-Liste, S. 34",
         "put", "puted", "AAA", "legen → legte", "Yesterday she ___ the book down.", "Yesterday"),
    Verb("run", "ran", "run", "runned", "Verb-Liste, S. 34",
         "run", "ranned", "ABA", "rennen → rannte", "He ___ to the bus yesterday.", "yesterday"),
    Verb("say", "said", "say", "sayed", "Verb-Liste, S. 34",
         "said", "sayd", "ABB", "sagen → sagte", "She ___ hello yesterday.", "yesterday"),
    Verb("speak", "spoke", "speak", "speaked", "Verb-Liste, S. 34",
         "spoken", "spoken", "ABC", "sprechen → sprach", "I ___ to him last week.", "last week"),
    Verb("tell", "told", "tell", "telled", "Verb-Liste, S. 34",
         "told", "tolded", "ABB", "erzählen → erzählte", "He ___ me a story yesterday.", "yesterday"),
    Verb("wear", "wore", "wear", "weared", "Verb-Liste, S. 34",
         "worn", "worn", "ABC", "tragen → trug", "She ___ a red coat yesterday.", "yesterday"),
    Verb("think", "thought", "think", "thinked", "S. 34: Language revision",
         "thought", "thank", "ABB", "denken → dachte", "I ___ about it yesterday.", "yesterday"),
    Verb("sell", "sold", "sell", "selled", "S. 34: Dialog, Aufgabe 8",
         "sold", "solded", "ABB", "verkaufen → verkaufte", "They ___ their bike last month.", "last month"),
    Verb("sleep", "slept", "sleep", "sleeped", "S. 33: Places to stay",
         "slept", "sleept", "ABB", "schlafen → schlief", "I ___ well last night.", "last night"),
    Verb("know", "knew", "know", "knowed", "S. 34: Dialog, Aufgabe 8",
         "known", "known", "ABC", "wissen → wusste", "I ___ the answer yesterday.", "yesterday"),
    Verb("choose", "chose", "choose", "choosed", "S. 34: Arbeitsauftrag, Aufgabe 7",
         "chosen", "chosen", "ABC", "wählen → wählte", "She ___ the blue one yesterday.", "yesterday"),
    Verb("write", "wrote", "write", "writed", "S. 35: Arbeitsauftrag, Aufgabe 10",
         "written", "written", "ABC", "schreiben → schrieb", "He ___ a letter last week.", "last week"),
    Verb("hear", "heard", "hear", "heared", "S. 34: Arbeitsauftrag, Aufgabe 7",
         "heard", "herd", "ABB", "hören → hörte", "I ___ a noise last night.", "last night"),
)

VERB_BY_NAME: dict[str, Verb] = {verb.infinitive: verb for verb in VERBS}

# Rainbow weapon: a mastered sibling in the same group, else the rule itself.
PATTERN_GROUPS: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("Endung -ought", ("bring", "buy", "think")),
    ("Endung -old", ("tell", "sell")),
    ("Endung -ept", ("keep", "sleep")),
    ("a-Laut im Past", ("drink", "run", "come", "become", "give", "eat")),
    ("o-e im Past", ("speak", "choose", "write", "wear")),
    ("Endung -ew", ("know",)),
    ("Past auf -d", ("make", "say", "have", "hear")),
    ("kurze Form", ("meet", "get")),
    ("Einzelgänger", ("be", "do", "go", "put")),
)

PATTERN_BLURB = {
    "AAA": "AAA · alle Formen gleich",
    "ABA": "ABA · Partizip = Grundform",
    "ABB": "ABB · Past = Partizip",
    "ABC": "ABC · drei verschiedene Formen",
}


def pattern_group(infinitive: str) -> tuple[str, tuple[str, ...]] | None:
    for label, members in PATTERN_GROUPS:
        if infinitive in members:
            return label, members
    return None


def bridge_text(verb: Verb, mastered: set[str], tier: int) -> str:
    found = pattern_group(verb.infinitive)
    if found is None:
        return ""
    label, members = found
    examples = [
        f"{other.infinitive} → {other.simple_past}"
        for other in VERBS
        if other.infinitive in members
        and other.infinitive != verb.infinitive
        and other.infinitive in mastered
    ]
    if not examples:
        return label
    limit = 2 if tier >= 7 else 1
    return "wie: " + ", ".join(examples[:limit])


class VerbDeck:
    """Uses each verb once before reshuffling; avoids immediate repeats."""

    def __init__(self, rng: random.Random | None = None):
        self.rng = rng or random.Random()
        self.remaining: list[Verb] = []
        self.last: str | None = None

    def next(self) -> Verb:
        if not self.remaining:
            self.remaining = list(VERBS)
            self.rng.shuffle(self.remaining)
            if len(self.remaining) > 1 and self.remaining[-1].infinitive == self.last:
                self.remaining[0], self.remaining[-1] = self.remaining[-1], self.remaining[0]
        verb = self.remaining.pop()
        self.last = verb.infinitive
        return verb


def _box_of(entry: dict | None) -> int | None:
    if not isinstance(entry, dict) or "box" not in entry:
        return None
    try:
        return max(0, min(5, int(entry["box"])))
    except (TypeError, ValueError):
        return None


def copies_needed(entry: dict | None) -> int:
    """A verb parked in Leitner box 0 after a real attempt must be clean twice."""
    if not isinstance(entry, dict):
        return 1
    try:
        box = int(entry.get("box", 3))
        seen = int(entry.get("wrong", 0)) + int(entry.get("assisted", 0)) + int(entry.get("right", 0))
    except (TypeError, ValueError):
        return 1
    if box == 0 and seen > 0:
        return 2
    return 1


def touch_stat(stats: dict, infinitive: str, *, outcome: str, run_index: int) -> None:
    """outcome is 'clean', 'assisted' or 'wrong'."""
    previous = stats.get(infinitive)
    if not isinstance(previous, dict):
        entry = {"box": 0, "right": 0, "wrong": 0, "assisted": 0, "last_run": 0}
    else:
        def num(key: str) -> int:
            try:
                return max(0, int(previous.get(key, 0)))
            except (TypeError, ValueError):
                return 0
        entry = {
            "box": min(5, num("box")),
            "right": num("right"),
            "wrong": num("wrong"),
            "assisted": num("assisted"),
            "last_run": num("last_run"),
        }
    if outcome == "clean":
        entry["right"] += 1
        entry["box"] = min(5, entry["box"] + 1)
    elif outcome == "assisted":
        entry["assisted"] += 1
    else:
        entry["wrong"] += 1
        entry["box"] = 0
    entry["last_run"] = max(0, int(run_index))
    stats[infinitive] = entry


def sanitize_verb_stats(raw) -> dict:
    """Drop anything an old or hand-edited save might have stored."""
    clean: dict = {}
    if not isinstance(raw, dict):
        return clean
    known = set(VERB_BY_NAME)
    for key, value in raw.items():
        if key not in known or not isinstance(value, dict):
            continue
        try:
            clean[key] = {
                "box": max(0, min(5, int(value.get("box", 0)))),
                "right": max(0, int(value.get("right", 0))),
                "wrong": max(0, int(value.get("wrong", 0))),
                "assisted": max(0, int(value.get("assisted", 0))),
                "last_run": max(0, int(value.get("last_run", 0))),
            }
        except (TypeError, ValueError):
            continue
    return clean


def pick_review_verb(stats: dict, missed: set[str], mastered: set[str],
                     rng: random.Random, *, only_mastered: bool) -> Verb | None:
    """Prefer Leitner boxes 0–2 and verbs missed in this run."""
    pool: list[tuple[int, Verb]] = []
    for verb in VERBS:
        if only_mastered and verb.infinitive not in mastered:
            continue
        entry = stats.get(verb.infinitive) or {}
        try:
            box = int(entry.get("box", 0 if verb.infinitive in missed else 3))
        except (TypeError, ValueError):
            box = 3
        if verb.infinitive in missed or box <= 2 or not only_mastered:
            pool.append((box, verb))
    if only_mastered:
        pool = [(box, verb) for box, verb in pool if verb.infinitive in mastered]
    if not pool:
        if only_mastered:
            return None
        pool = [(3, verb) for verb in VERBS]
    pool.sort(key=lambda item: item[0])
    best = pool[0][0]
    band = [verb for box, verb in pool if box == best]
    return rng.choice(band)


def validate() -> None:
    assert len(VERBS) == 28
    assert len({v.infinitive for v in VERBS}) == len(VERBS)
    patterns = {"AAA", "ABA", "ABB", "ABC"}
    covered: list[str] = []
    for label, members in PATTERN_GROUPS:
        assert label
        covered.extend(members)
    assert sorted(covered) == sorted(v.infinitive for v in VERBS)
    for verb in VERBS:
        values = [verb.simple_past, verb.distractor_a, verb.distractor_b, verb.distractor_c]
        assert all(values), f"Empty option: {verb.infinitive}"
        assert len(set(values)) == 4, f"Duplicate options: {verb.infinitive}"
        assert verb.pattern in patterns, verb.infinitive
        assert verb.past_participle, verb.infinitive
        assert "→" in verb.german, verb.infinitive
        assert "___" in verb.sentence, verb.infinitive
        assert verb.signal and verb.signal in verb.sentence, verb.infinitive
        assert verb.source, verb.infinitive
        assert verb.simple_past not in verb.sentence, verb.infinitive
        past = verb.boss_options(random.Random(1), "past")
        part = verb.boss_options(random.Random(2), "participle")
        assert len(past) == 4 and len(set(past)) == 4, verb.infinitive
        assert len(part) == 4 and len(set(part)) == 4, verb.infinitive
        assert verb.simple_past in past and verb.past_participle in part


validate()


class MasteryDeck:
    """A finite run: missed verbs return later; only clean answers count.

    Call next() once, then record() once. The run ends after every verb
    has been answered correctly without a hint. Box-0 verbs from an older
    run must be answered cleanly twice. Assisted corrects go back in the
    deck and do not increment the mistake counter.
    """

    def __init__(self, rng: random.Random | None = None, stats: dict | None = None):
        self.rng = rng or random.Random()
        self.stats = stats or {}
        self.remaining = list(VERBS)
        self.rng.shuffle(self.remaining)
        self._bring_weak_forward()
        self.current: Verb | None = None
        self.mastered: set[str] = set()
        self.mistakes = 0
        self.attempts = 0
        self.assisted_count = 0
        self.missed: set[str] = set()
        self.clean: dict[str, int] = {}
        self.required = {verb.infinitive: copies_needed(self.stats.get(verb.infinitive)) for verb in VERBS}

    def _bring_weak_forward(self) -> None:
        if not self.stats:
            return
        def box(verb: Verb) -> int:
            value = _box_of(self.stats.get(verb.infinitive))
            return 3 if value is None else value
        ordered = list(self.remaining)
        self.rng.shuffle(ordered)
        ordered.sort(key=box)
        # pop() draws from the end, so the weakest box sits there.
        self.remaining = list(reversed(ordered))

    @property
    def complete(self) -> bool:
        return len(self.mastered) == len(VERBS)

    @property
    def completed_count(self) -> int:
        return len(self.mastered)

    def next(self) -> Verb:
        if self.current is not None:
            raise RuntimeError("Resolve the current verb before requesting another")
        if not self.remaining:
            raise StopIteration("All verbs answered correctly")
        self.current = self.remaining.pop()
        return self.current

    def record(self, correct: bool, assisted: bool = False) -> None:
        if self.current is None:
            raise RuntimeError("No active verb to resolve")
        self.attempts += 1
        verb = self.current
        name = verb.infinitive
        if correct and assisted:
            self.assisted_count += 1
            self.remaining.insert(0, verb)
        elif correct:
            self.clean[name] = self.clean.get(name, 0) + 1
            if self.clean[name] >= self.required.get(name, 1):
                self.mastered.add(name)
            else:
                self.remaining.insert(0, verb)
        else:
            self.mistakes += 1
            self.missed.add(name)
            self.clean[name] = 0
            self.remaining.insert(0, verb)
        self.current = None

    def unmaster(self, verb: Verb) -> None:
        """A failed refresh or boss puts a 'known' verb back into the run."""
        self.mastered.discard(verb.infinitive)
        self.missed.add(verb.infinitive)
        self.required[verb.infinitive] = max(2, self.required.get(verb.infinitive, 1))
        self.clean[verb.infinitive] = 0
        if self.current is not None and self.current.infinitive == verb.infinitive:
            return
        if not any(item.infinitive == verb.infinitive for item in self.remaining):
            self.remaining.insert(0, verb)
