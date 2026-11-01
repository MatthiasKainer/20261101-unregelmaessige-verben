"""The 28 irregular verbs found on the three provided workbook pages.

The 21 verbs in exercise 7 form the core; seven additional verbs appear in
other exercises, the dialogue, or task instructions. Modal 'can' is excluded,
as it is not part of the workbook's infinitive -> simple-past verb practice.
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

    def options(self, rng: random.Random) -> tuple[str, ...]:
        answers = [self.simple_past, self.distractor_a, self.distractor_b]
        rng.shuffle(answers)
        return tuple(answers)


# The correct form is always a single selectable answer. Both past forms of
# 'be' are displayed together, so neither 'was' nor 'were' is marked wrong.
VERBS: tuple[Verb, ...] = (
    Verb("be", "was / were", "be", "beed", "Verb-Liste, S. 34"),
    Verb("become", "became", "become", "becomed", "Verb-Liste, S. 34"),
    Verb("bring", "brought", "bring", "bringed", "Verb-Liste, S. 34"),
    Verb("buy", "bought", "buy", "buyed", "Verb-Liste, S. 34"),
    Verb("come", "came", "come", "comed", "Verb-Liste, S. 34"),
    Verb("do", "did", "do", "doed", "Verb-Liste, S. 34"),
    Verb("drink", "drank", "drink", "drinked", "Verb-Liste, S. 34"),
    Verb("eat", "ate", "eat", "eated", "Verb-Liste, S. 34"),
    Verb("get", "got", "get", "getted", "Verb-Liste, S. 34"),
    Verb("go", "went", "go", "goed", "Verb-Liste, S. 34"),
    Verb("give", "gave", "give", "gived", "Verb-Liste, S. 34"),
    Verb("have", "had", "have", "haved", "Verb-Liste, S. 34"),
    Verb("keep", "kept", "keep", "keeped", "Verb-Liste, S. 34"),
    Verb("make", "made", "make", "maked", "Verb-Liste, S. 34"),
    Verb("meet", "met", "meet", "meeted", "Verb-Liste, S. 34"),
    Verb("put", "put", "putted", "putt", "Verb-Liste, S. 34"),
    Verb("run", "ran", "run", "runned", "Verb-Liste, S. 34"),
    Verb("say", "said", "say", "sayed", "Verb-Liste, S. 34"),
    Verb("speak", "spoke", "speak", "speaked", "Verb-Liste, S. 34"),
    Verb("tell", "told", "tell", "telled", "Verb-Liste, S. 34"),
    Verb("wear", "wore", "wear", "weared", "Verb-Liste, S. 34"),
    Verb("think", "thought", "think", "thinked", "S. 34: Language revision"),
    Verb("sell", "sold", "sell", "selled", "S. 34: Dialog, Aufgabe 8"),
    Verb("sleep", "slept", "sleep", "sleeped", "S. 33: Places to stay"),
    Verb("know", "knew", "know", "knowed", "S. 34: Dialog, Aufgabe 8"),
    Verb("choose", "chose", "choose", "choosed", "S. 34: Arbeitsauftrag, Aufgabe 7"),
    Verb("write", "wrote", "write", "writed", "S. 35: Arbeitsauftrag, Aufgabe 10"),
    Verb("hear", "heard", "hear", "heared", "S. 34: Arbeitsauftrag, Aufgabe 7"),
)


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


def validate() -> None:
    assert len(VERBS) == 28
    assert len({v.infinitive for v in VERBS}) == len(VERBS)
    for verb in VERBS:
        values = [verb.simple_past, verb.distractor_a, verb.distractor_b]
        assert all(values), f"Empty option: {verb.infinitive}"
        assert len(set(values)) == 3, f"Duplicate options: {verb.infinitive}"
        assert verb.source, f"Missing source: {verb.infinitive}"


validate()


class MasteryDeck:
    """A finite run: missed verbs return later; only correct answers count.

    Call next() once, then record() once. The run ends after every verb
    has been answered correctly, never just after a fixed number of shots.
    """

    def __init__(self, rng: random.Random | None = None):
        self.rng = rng or random.Random()
        self.remaining = list(VERBS)
        self.rng.shuffle(self.remaining)
        self.current: Verb | None = None
        self.mastered: set[str] = set()
        self.mistakes = 0
        self.attempts = 0

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

    def record(self, correct: bool) -> None:
        if self.current is None:
            raise RuntimeError("No active verb to resolve")
        self.attempts += 1
        if correct:
            self.mastered.add(self.current.infinitive)
        else:
            self.mistakes += 1
            # Put it at the *back* of the shuffled deck, not next on top.
            # With only one unsolved verb it can of course recur immediately.
            self.remaining.insert(0, self.current)
        self.current = None
