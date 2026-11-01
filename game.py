"""IRREGULAR RANGE – a mouse-only, self-contained Simple Past arcade game.

Run: python game.py
Windows EXE: built on GitHub Actions with PyInstaller.
No images, audio files, network access or user accounts are needed.
"""
from __future__ import annotations

import array
import json
import math
import os
from pathlib import Path
import random
import sys
from dataclasses import dataclass

import pygame

from upgrades import (
    PAGE_SIZE, THEMES, UPGRADES, UPGRADE_BY_ID, Upgrade,
    recommended_page, reward, shop_page, completion_bonus,
)
from vocabulary import VERBS, Verb, MasteryDeck
from weapon_fx import WEAPONS, flight_point
from weapon_visuals import trail as draw_weapon_trail, impact as draw_weapon_impact

W, H = 1280, 720
FPS = 60
QUESTION_SECONDS = 5.0
STARTING_LIVES = 5

BG = (13, 20, 39)
PANEL = (29, 40, 65)
WHITE = (244, 246, 252)
MUTED = (145, 162, 190)
CYAN = (89, 223, 234)
GOLD = (255, 205, 97)
GREEN = (91, 232, 168)
RED = (255, 103, 116)


@dataclass
class Particle:
    x: float
    y: float
    vx: float
    vy: float
    lifespan: float
    life: float
    size: float
    color: tuple[int, int, int]
    kind: str
    spin: float = 0.0
    drag: float = 0.985


@dataclass
class HitEffect:
    kind: str
    x: float
    y: float
    tier: int
    age: float = 0.0
    duration: float = 1.05


@dataclass
class Ring:
    x: float
    y: float
    life: float
    maxlife: float
    radius: float
    color: tuple[int, int, int]
    width: int = 3


def clamp(v: float, low: float, high: float) -> float:
    return max(low, min(high, v))


def lerp(a: float, b: float, t: float) -> float:
    return a + (b - a) * t


def mix(a: tuple[int, int, int], b: tuple[int, int, int], t: float) -> tuple[int, int, int]:
    return tuple(int(lerp(a[i], b[i], clamp(t, 0, 1))) for i in range(3))


def point(x: float, y: float) -> tuple[int, int]:
    return int(x), int(y)


def rounded(surface: pygame.Surface, rect: pygame.Rect | tuple[int, int, int, int],
            fill: tuple[int, int, int], border: tuple[int, int, int] | None = None,
            radius: int = 18, border_width: int = 2) -> None:
    pygame.draw.rect(surface, fill, rect, border_radius=radius)
    if border:
        pygame.draw.rect(surface, border, rect, width=border_width, border_radius=radius)


def polygon_star(x: float, y: float, r: float, points: int = 5, inner: float = 0.43):
    result = []
    for i in range(points * 2):
        a = -math.pi / 2 + i * math.pi / points
        d = r if i % 2 == 0 else r * inner
        result.append(point(x + math.cos(a) * d, y + math.sin(a) * d))
    return result


def draw_symbol(surface: pygame.Surface, x: float, y: float, size: float,
                kind: str, color: tuple[int, int, int],
                accent: tuple[int, int, int] = WHITE) -> None:
    """28 distinct themed projectiles, drawn entirely with pygame primitives."""
    s = max(3, int(size))
    cx, cy = point(x, y)
    if kind == "chalk":
        pygame.draw.line(surface, color, (cx - s, cy + s // 2), (cx + s, cy - s // 2), max(2, s // 3))
        pygame.draw.circle(surface, accent, (cx + s // 2, cy - s // 2), max(2, s // 4))
    elif kind == "confetti":
        pygame.draw.rect(surface, color, (cx - s, cy - s // 3, 2 * s, max(3, s // 2)))
        pygame.draw.rect(surface, accent, (cx - s // 3, cy - s, max(3, s // 2), 2 * s))
    elif kind == "ink":
        pygame.draw.circle(surface, color, (cx, cy), s)
        for i in range(5):
            a = i * math.tau / 5
            pygame.draw.circle(surface, color, point(cx + math.cos(a) * s, cy + math.sin(a) * s), max(2, s // 3))
    elif kind == "rubber":
        pygame.draw.circle(surface, color, (cx, cy), s)
        pygame.draw.arc(surface, accent, (cx - s + 3, cy - s + 3,
                                         max(3, 2 * s - 6), max(3, 2 * s - 6)), 1, 2.65, 3)
    elif kind == "laser":
        pygame.draw.line(surface, color, (cx - 2 * s, cy), (cx + 2 * s, cy), max(2, s // 2))
        pygame.draw.circle(surface, accent, (cx, cy), max(2, s // 3))
    elif kind == "star":
        pygame.draw.polygon(surface, color, polygon_star(cx, cy, s))
    elif kind == "plane":
        pygame.draw.polygon(surface, color, [(cx - s, cy - s // 2), (cx + s, cy), (cx - s, cy + s // 2), (cx - s // 3, cy)])
        pygame.draw.line(surface, accent, (cx - s // 3, cy), (cx + s, cy), 2)
    elif kind == "firework":
        for i in range(8):
            a = math.tau * i / 8
            pygame.draw.line(surface, color, point(cx + math.cos(a) * s * 0.5, cy + math.sin(a) * s * 0.5),
                             point(cx + math.cos(a) * s * 1.2, cy + math.sin(a) * s * 1.2), 2)
        pygame.draw.circle(surface, accent, (cx, cy), max(3, s // 3))
    elif kind == "explosion":
        pygame.draw.polygon(surface, color, polygon_star(cx, cy, s, 9, 0.52))
        pygame.draw.circle(surface, accent, (cx, cy), max(3, s // 3))
    elif kind == "football":
        pygame.draw.circle(surface, WHITE, (cx, cy), s)
        pygame.draw.circle(surface, (22, 35, 51), (cx, cy), max(3, s // 3))
        for i in range(5):
            a = math.tau * i / 5
            pygame.draw.line(surface, (34, 49, 58), (cx, cy), point(cx + math.cos(a) * s * 0.88, cy + math.sin(a) * s * 0.88), 2)
        pygame.draw.circle(surface, (30, 44, 54), (cx, cy), s, 1)
    elif kind == "lightning":
        pts = [(cx - s // 3, cy - s), (cx + s // 3, cy - s // 4), (cx - s // 4, cy + s // 8),
               (cx + s // 2, cy + s), (cx + s // 6, cy + s // 8), (cx + s, cy - s // 3)]
        pygame.draw.lines(surface, color, False, pts, max(3, s // 3))
    elif kind == "snow":
        for i in range(3):
            a = math.pi * i / 3
            d = (math.cos(a) * s, math.sin(a) * s)
            pygame.draw.line(surface, color, point(cx - d[0], cy - d[1]), point(cx + d[0], cy + d[1]), 2)
        pygame.draw.circle(surface, accent, (cx, cy), max(2, s // 4))
    elif kind == "water":
        pygame.draw.polygon(surface, color, [(cx, cy - s), (cx - s // 2, cy), (cx, cy + s), (cx + s // 2, cy)])
        pygame.draw.circle(surface, accent, (cx - s // 6, cy), max(2, s // 5))
    elif kind == "bubble":
        pygame.draw.circle(surface, color, (cx, cy), s, max(2, s // 6))
        pygame.draw.circle(surface, accent, (cx - s // 3, cy - s // 3), max(2, s // 6))
    elif kind == "meteor":
        pygame.draw.polygon(surface, accent, [(cx - 2 * s, cy - s), (cx - s // 2, cy - s // 2),
                                              (cx + s, cy), (cx - s // 2, cy + s // 2)])
        pygame.draw.circle(surface, color, (cx + s // 3, cy), max(3, s // 2))
    elif kind == "crystal":
        pygame.draw.polygon(surface, color, [(cx, cy - s), (cx + s // 2, cy), (cx, cy + s), (cx - s // 2, cy)])
        pygame.draw.line(surface, accent, (cx, cy - s), (cx, cy + s), 2)
    elif kind == "heart":
        pygame.draw.circle(surface, color, (cx - s // 3, cy - s // 4), max(3, s // 2))
        pygame.draw.circle(surface, color, (cx + s // 3, cy - s // 4), max(3, s // 2))
        pygame.draw.polygon(surface, color, [(cx - s, cy - s // 4), (cx + s, cy - s // 4), (cx, cy + s)])
    elif kind == "donut":
        pygame.draw.circle(surface, color, (cx, cy), s)
        pygame.draw.circle(surface, accent, (cx, cy), max(3, s // 2))
        pygame.draw.circle(surface, (74, 48, 64), (cx, cy), max(2, s // 3))
    elif kind == "pizza":
        pygame.draw.polygon(surface, color, [(cx - s, cy - s), (cx + s, cy), (cx - s, cy + s)])
        pygame.draw.line(surface, accent, (cx - s, cy - s), (cx - s, cy + s), max(3, s // 4))
        pygame.draw.circle(surface, (220, 83, 75), (cx - s // 4, cy), max(2, s // 5))
    elif kind == "rocket":
        pygame.draw.polygon(surface, color, [(cx + s, cy), (cx, cy - s // 2), (cx - s, cy - s // 2),
                                              (cx - s, cy + s // 2), (cx, cy + s // 2)])
        pygame.draw.polygon(surface, accent, [(cx - s, cy - s // 3), (cx - 2 * s, cy), (cx - s, cy + s // 3)])
        pygame.draw.circle(surface, (39, 90, 140), (cx, cy), max(2, s // 4))
    elif kind == "comet":
        pygame.draw.line(surface, accent, (cx - 2 * s, cy + s), (cx, cy), max(2, s // 2))
        pygame.draw.circle(surface, color, (cx, cy), max(3, s // 2))
        pygame.draw.circle(surface, WHITE, (cx + s // 5, cy - s // 5), max(2, s // 5))
    elif kind == "rainbow":
        for i, c in enumerate(((255, 107, 125), (255, 219, 95), (109, 231, 165), (126, 190, 249))):
            r = s + i * 3
            pygame.draw.arc(surface, c, (cx - r, cy - r // 2, 2 * r, 2 * r), math.pi, 2 * math.pi, 3)
    elif kind == "paint":
        pygame.draw.circle(surface, color, (cx, cy), s)
        for dx, dy, k in ((-1.5, -.2, .35), (.9, -.9, .29), (.5, 1.4, .38)):
            pygame.draw.circle(surface, accent, point(cx + s * dx, cy + s * dy), max(2, int(s * k)))
    elif kind == "disco":
        pygame.draw.circle(surface, color, (cx, cy), s)
        for k in (-1, 0, 1):
            pygame.draw.line(surface, accent, (cx - s, cy + k * s // 2), (cx + s, cy + k * s // 2), 1)
            pygame.draw.line(surface, accent, (cx + k * s // 2, cy - s), (cx + k * s // 2, cy + s), 1)
    elif kind == "plasma":
        pygame.draw.circle(surface, color, (cx, cy), s, max(2, s // 4))
        pygame.draw.circle(surface, accent, (cx, cy), max(3, s // 3))
        pygame.draw.line(surface, color, (cx - s - 3, cy), (cx + s + 3, cy), 2)
    elif kind == "ninja":
        pygame.draw.polygon(surface, color, [(cx, cy - s), (cx + s // 4, cy - s // 4),
                                              (cx + s, cy), (cx + s // 4, cy + s // 4),
                                              (cx, cy + s), (cx - s // 4, cy + s // 4),
                                              (cx - s, cy), (cx - s // 4, cy - s // 4)])
        pygame.draw.circle(surface, accent, (cx, cy), max(2, s // 5))
    elif kind == "galaxy":
        pygame.draw.circle(surface, color, (cx, cy), max(3, s // 3))
        for i in range(2):
            for j in range(9):
                a = j * math.tau / 9 + i * math.pi
                d = (0.4 + 0.065 * j) * s
                pygame.draw.circle(surface, color if i == 0 else accent,
                                   point(cx + math.cos(a + j * .17) * d, cy + math.sin(a + j * .17) * d), 2)
    elif kind == "gold":
        pygame.draw.circle(surface, color, (cx, cy), s)
        pygame.draw.circle(surface, (138, 90, 30), (cx, cy), max(2, s - 3), 2)
        pygame.draw.line(surface, (138, 90, 30), (cx, cy - s // 2), (cx, cy + s // 2), 3)
    else:
        pygame.draw.circle(surface, color, (cx, cy), s)


def save_folder() -> Path:
    if os.name == "nt":
        return Path(os.environ.get("APPDATA", str(Path.home()))) / "IrregularRange"
    return Path(os.environ.get("XDG_DATA_HOME", str(Path.home() / ".local" / "share"))) / "irregular_range"


class Game:
    def __init__(self) -> None:
        pygame.mixer.pre_init(22050, -16, 1, 512)
        pygame.init()
        pygame.display.set_caption("IRREGULAR RANGE | Simple Past Schießstand")
        self.window = pygame.display.set_mode((W, H), pygame.RESIZABLE)
        self.canvas = pygame.Surface((W, H)).convert()
        self.clock = pygame.time.Clock()
        self.fonts: dict[tuple[int, bool], pygame.font.Font] = {}
        self.rng = random.Random()
        self.gradient = self.make_gradient()
        self.sounds = self.make_sounds()
        self.running = True
        self.phase = "menu"
        self.time_elapsed = 0.0
        self.mouse = (0, 0)
        self.deck = MasteryDeck(self.rng)
        self.verb: Verb = VERBS[9]
        self.options: tuple[str, ...] = ("go", "went", "goed")
        self.correct_index = 1
        self.chosen_index: int | None = None
        self.question_age = 0.0
        self.time_left = QUESTION_SECONDS
        self.flight_time = 0.0
        self.flight_seconds = 0.22
        self.shot_from = (W // 2, H - 20)
        self.shot_to = (W // 2, H // 2)
        self.flight_trail: list[tuple[float, float]] = []
        self.reveal_elapsed = 0.0
        self.impact_elapsed = 0.0
        self.outcome = ""
        self.winnings = 0
        self.lives = STARTING_LIVES
        self.streak = 0
        self.correct_count = 0
        self.questions = 0
        self.completed = False
        self.bonus_awarded = 0
        self.victory_age = 0.0
        self.active_round: Upgrade | None = None
        self.trial_pending: str | None = None
        self.trial_candidate: Upgrade = UPGRADES[-1]
        self.page = 0
        self.toast = ""
        self.toast_age = 0.0
        self.particles: list[Particle] = []
        self.rings: list[Ring] = []
        self.hit_effects: list[HitEffect] = []
        self.shake = 0.0
        self.flash = 0.0
        self.progress = self.load_progress()
        self.coins = self.progress["coins"]
        self.owned: set[str] = set(self.progress["owned"])
        self.equipped: str | None = self.progress["equipped"]
        self.sound_on = self.progress["sound_on"]

    def font(self, size: int, bold: bool = False) -> pygame.font.Font:
        key = (size, bold)
        if key not in self.fonts:
            self.fonts[key] = pygame.font.SysFont("verdana", size, bold=bold)
        return self.fonts[key]

    def text(self, surface: pygame.Surface, content: str, x: float, y: float,
             size: int = 24, color: tuple[int, int, int] = WHITE,
             bold: bool = False, align: str = "left", shadow: bool = False) -> pygame.Rect:
        font = self.font(size, bold)
        img = font.render(content, True, color)
        rect = img.get_rect()
        if align == "center":
            rect.center = point(x, y)
        elif align == "right":
            rect.midright = point(x, y)
        else:
            rect.midleft = point(x, y)
        if shadow:
            dark = font.render(content, True, (5, 10, 20))
            surface.blit(dark, rect.move(2, 3))
        surface.blit(img, rect)
        return rect

    def make_gradient(self) -> pygame.Surface:
        gradient = pygame.Surface((W, H))
        top, bottom = (8, 14, 33), (31, 47, 65)
        for y in range(H):
            pygame.draw.line(gradient, mix(top, bottom, y / H), (0, y), (W, y))
        return gradient

    def make_sounds(self) -> dict[str, pygame.mixer.Sound]:
        if not pygame.mixer.get_init():
            return {}
        result = {}
        presets = {
            "pop": (300, 470, .10),
            "shoot": (430, 110, .13),
            "hit": (440, 880, .18),
            "miss": (300, 110, .24),
            "buy": (650, 1000, .20),
            "coins": (740, 1160, .17),
            "trial": (540, 700, .13),
            "laser": (1100, 270, .22),
            "kick": (110, 230, .15),
            "electric": (1260, 430, .16),
            "splash": (240, 630, .20),
            "bubbles": (700, 940, .20),
            "party": (500, 1280, .24),
            "chime": (840, 1340, .24),
            "boom": (220, 75, .29),
            "whoosh": (310, 780, .22),
        }
        rate = 22050
        for name, (low, high, duration) in presets.items():
            samples = array.array("h")
            n = int(rate * duration)
            phase = 0.0
            for j in range(n):
                t = j / max(1, n - 1)
                freq = lerp(low, high, t)
                phase += 2 * math.pi * freq / rate
                envelope = (1 - t) ** 1.75 * min(1, t * 22)
                noise = self.rng.uniform(-.3, .3) if name in (
                    "shoot", "miss", "boom", "splash", "whoosh", "kick") else 0
                samples.append(int(10500 * envelope * (math.sin(phase) * .85 + noise)))
            try:
                result[name] = pygame.mixer.Sound(buffer=samples.tobytes())
            except pygame.error:
                pass
        return result

    def sound(self, name: str) -> None:
        if self.sound_on and name in self.sounds:
            self.sounds[name].play()

    def load_progress(self) -> dict:
        default = {"coins": 0, "owned": [], "equipped": None, "best": 0,
                   "total_hits": 0, "runs": 0, "completions": 0,
                   "best_mistakes": None, "sound_on": True}
        path = save_folder() / "progress.json"
        try:
            raw = json.loads(path.read_text(encoding="utf-8"))
            if not isinstance(raw, dict):
                return default
            values = {**default, **raw}
            values["coins"] = max(0, min(99_999_999, int(values["coins"])))
            values["best"] = max(0, min(len(VERBS), int(values["best"])))
            values["total_hits"] = max(0, int(values["total_hits"]))
            values["runs"] = max(0, int(values["runs"]))
            values["completions"] = max(0, int(values["completions"]))
            if values["best_mistakes"] is not None:
                values["best_mistakes"] = max(0, int(values["best_mistakes"]))
            owned = values["owned"] if isinstance(values["owned"], list) else []
            values["owned"] = [x for x in owned if isinstance(x, str) and x in UPGRADE_BY_ID]
            if values["equipped"] not in values["owned"]:
                values["equipped"] = None
            values["sound_on"] = bool(values["sound_on"])
            return values
        except (OSError, ValueError, TypeError, OverflowError):
            return default

    def save_progress(self) -> None:
        self.progress.update(coins=self.coins, owned=sorted(self.owned), equipped=self.equipped,
                             sound_on=self.sound_on)
        folder = save_folder()
        try:
            folder.mkdir(parents=True, exist_ok=True)
            temp = folder / "progress.json.tmp"
            temp.write_text(json.dumps(self.progress, ensure_ascii=False, indent=2), encoding="utf-8")
            os.replace(temp, folder / "progress.json")
        except OSError:
            pass  # Don't break the game on protected PCs.

    def new_run(self) -> None:
        self.lives = STARTING_LIVES
        self.correct_count = 0
        self.questions = 0
        self.streak = 0
        self.completed = False
        self.bonus_awarded = 0
        self.victory_age = 0.0
        self.trial_pending = None
        self.hit_effects.clear()
        self.particles.clear()
        self.rings.clear()
        self.deck = MasteryDeck(self.rng)
        self.progress["runs"] += 1
        self.save_progress()
        self.start_question()

    def start_question(self) -> None:
        if self.deck.complete:
            self.end_run()
            return
        self.verb = self.deck.next()
        self.options = self.verb.options(self.rng)
        self.correct_index = self.options.index(self.verb.simple_past)
        self.chosen_index = None
        self.time_left = QUESTION_SECONDS
        self.question_age = 0.0
        self.shake = 0.0
        self.flight_trail.clear()
        upgrade_id = self.trial_pending or self.equipped
        self.active_round = UPGRADE_BY_ID.get(upgrade_id) if upgrade_id else None
        self.trial_pending = None
        self.phase = "play"
        self.questions += 1
        self.sound("pop")

    def start_shop(self) -> None:
        if self.deck.complete or self.lives <= 0:
            self.end_run()
            return
        self.phase = "shop"
        self.page = recommended_page(self.coins, self.owned)
        self.trial_pending = None
        pool = [u for u in UPGRADES if u.id not in self.owned and u.tier >= 3]
        self.trial_candidate = self.rng.choice(pool or list(UPGRADES))
        self.toast = ""
        self.save_progress()

    def end_run(self) -> None:
        if self.phase == "end":
            return  # The completion bonus must never be awarded twice.
        self.completed = self.deck.complete
        self.bonus_awarded = 0
        self.victory_age = 0.0
        self.phase = "end"
        self.progress["best"] = max(self.progress["best"], self.correct_count)
        self.progress["total_hits"] += self.correct_count
        if self.completed:
            self.bonus_awarded = completion_bonus(self.deck.mistakes)
            self.coins += self.bonus_awarded
            self.progress["completions"] += 1
            prev = self.progress["best_mistakes"]
            if prev is None or self.deck.mistakes < prev:
                self.progress["best_mistakes"] = self.deck.mistakes
            self.sound("coins")
            self.flash = .6
            for i in range(5):
                self.hit_effects.append(HitEffect("firework", 260 + 185 * i,
                                                  235 + 23 * (i % 2), 4, age=-i * .13))
        self.save_progress()

    def register_shot(self, target: int | None, clicked_at: tuple[float, float] | None = None,
                      timeout: bool = False) -> None:
        if self.phase != "play":
            return
        self.chosen_index = target
        self.outcome = "timeout" if timeout else "correct" if target == self.correct_index else "wrong"
        self.winnings = reward(self.streak + 1, self.time_left) if self.outcome == "correct" else 0
        kind = self.active_round.theme.projectile if self.active_round else "chalk"
        self.flight_seconds = WEAPONS[kind].travel * (
            .86 if self.active_round and self.active_round.tier >= 2 else 1.0)
        self.flight_time = 0.0
        self.shot_from = (W / 2, H - 13)
        self.shot_to = clicked_at or (640, 472)
        self.flight_trail = []
        self.phase = "flight"
        self.sound(WEAPONS[kind].pitch if not timeout else "miss")
        if timeout:
            self.flight_seconds = 0.001

    def resolve(self) -> None:
        self.phase = "impact"
        self.impact_elapsed = 0.0
        self.reveal_elapsed = 0.0
        success = self.outcome == "correct"
        # Wrong answers, misses and timeouts go back into this run's deck.
        self.deck.record(success)
        if success:
            self.streak += 1
            self.correct_count = self.deck.completed_count
            self.coins += self.winnings
            self.sound("hit")
            self.spawn_burst(self.shot_to, True)
        else:
            self.lives = max(0, self.lives - 1)
            self.streak = 0
            self.sound("miss")
            at = self.shot_to if self.outcome != "timeout" else (640, 430)
            self.spawn_burst(at, False)
        self.save_progress()

    def spawn_burst(self, pos: tuple[float, float], success: bool) -> None:
        x, y = pos
        tier = self.active_round.tier if self.active_round else 0
        theme = self.active_round.theme if self.active_round else THEMES[0]
        count = (24 + tier * 8) if success else 12
        kind = theme.projectile if success else "chalk"
        if success:
            self.hit_effects.append(HitEffect(kind, x, y, tier))
        colors = [theme.color, theme.accent, GOLD, WHITE] if success else [RED, (222, 121, 130)]
        for _ in range(count):
            a = self.rng.uniform(0, math.tau)
            velocity = self.rng.uniform(90, 260 + tier * 25)
            life = self.rng.uniform(.45, 1.0 + tier * .055)
            self.particles.append(Particle(x, y, math.cos(a) * velocity, math.sin(a) * velocity - 70,
                                           life, life, self.rng.uniform(3.5, 6.5 + tier / 3),
                                           self.rng.choice(colors), kind, self.rng.random() * 6))
        if success:
            # New particle rings and echo waves become stronger as upgrades rise.
            for i in range(1 + tier // 3):
                self.rings.append(Ring(x, y, .55 + i * .15, .55 + i * .15,
                                       24 + i * 23, theme.color if i % 2 == 0 else theme.accent, 3 + tier // 3))
            if tier >= 6:
                for j in range(4 + tier):
                    px = self.rng.uniform(120, 1160)
                    py = self.rng.uniform(235, 485)
                    self.rings.append(Ring(px, py, .48, .48, 10, theme.accent, 2))
            self.flash = min(.55, tier / 25)
            self.shake = 3 + tier * 1.2
        else:
            self.shake = 10
            self.rings.append(Ring(x, y, .5, .5, 14, RED, 5))
        if len(self.particles) > 440:
            self.particles = self.particles[-440:]
        if len(self.rings) > 75:
            self.rings = self.rings[-75:]

    def flash_message(self, message: str) -> None:
        self.toast = message
        self.toast_age = 0.0

    def buy_or_equip(self, upgrade: Upgrade) -> None:
        if upgrade.id in self.owned:
            self.equipped = upgrade.id
            self.sound("trial")
            self.flash_message("AUSGERÜSTET: " + upgrade.theme.title)
        elif self.coins >= upgrade.cost:
            self.coins -= upgrade.cost
            self.owned.add(upgrade.id)
            self.equipped = upgrade.id
            self.sound("buy")
            self.flash_message("GEKAUFT & AUSGERÜSTET: " + upgrade.theme.title)
        else:
            self.sound("miss")
            self.flash_message(f"DIR FEHLEN {upgrade.cost - self.coins} MÜNZEN")
        self.save_progress()

    def trial(self) -> None:
        self.trial_pending = self.trial_candidate.id
        self.sound("trial")
        self.flash_message("PROBEPATRONE IST FÜR DIE NÄCHSTE FRAGE BEREIT")

    def popup_progress(self) -> float:
        t = min(1.0, self.question_age / .46)
        # Back-easing: the target overshoots, bounces and settles like a spring.
        c1 = 1.70158
        return 1 + (c1 + 1) * (t - 1) ** 3 + c1 * (t - 1) ** 2

    def target_rect(self, idx: int) -> pygame.Rect:
        x = (265, 640, 1015)[idx]
        progress = self.popup_progress()
        return pygame.Rect(x - 124, 597 - max(1, int(296 * progress)), 248,
                           max(1, int(296 * progress)))

    def screen_mouse(self, p: tuple[int, int]) -> tuple[float, float] | None:
        sw, sh = self.window.get_size()
        scale = min(sw / W, sh / H)
        dx, dy = (sw - W * scale) / 2, (sh - H * scale) / 2
        xx, yy = (p[0] - dx) / scale, (p[1] - dy) / scale
        return (xx, yy) if 0 <= xx < W and 0 <= yy < H else None

    def click(self, pos: tuple[float, float]) -> None:
        x, y = pos
        if pygame.Rect(1195, 25, 54, 54).collidepoint(x, y):
            self.sound_on = not self.sound_on
            self.save_progress()
            return
        if self.phase == "menu":
            if pygame.Rect(452, 510, 376, 69).collidepoint(x, y):
                self.sound("trial")
                self.new_run()
        elif self.phase == "play":
            hit = None
            for i in range(3):
                if self.target_rect(i).collidepoint(x, y) and self.question_age >= .17:
                    hit = i
                    break
            self.register_shot(hit, (x, y))
        elif self.phase == "shop":
            if pygame.Rect(997, 152, 208, 59).collidepoint(x, y):
                self.trial()
            elif pygame.Rect(989, 635, 227, 56).collidepoint(x, y):
                self.sound("trial")
                self.start_question()
            elif pygame.Rect(62, 635, 54, 52).collidepoint(x, y):
                self.page = max(0, self.page - 1)
                self.sound("trial")
            elif pygame.Rect(223, 635, 54, 52).collidepoint(x, y):
                self.page = min((len(UPGRADES) - 1) // PAGE_SIZE, self.page + 1)
                self.sound("trial")
            else:
                for i, upgrade in enumerate(shop_page(self.page)):
                    col, row = i % 3, i // 3
                    rect = pygame.Rect(60 + col * 393, 237 + row * 188, 369, 166)
                    if rect.collidepoint(x, y):
                        self.buy_or_equip(upgrade)
                        break
        elif self.phase == "end":
            if pygame.Rect(449, 540, 382, 58).collidepoint(x, y):
                self.new_run()
            elif pygame.Rect(501, 611, 278, 44).collidepoint(x, y):
                self.running = False

    def update(self, dt: float) -> None:
        dt = min(dt, .06)
        self.time_elapsed += dt
        self.toast_age += dt
        self.shake = max(0.0, self.shake - dt * 24)
        self.flash = max(0.0, self.flash - dt * 2)
        if self.phase == "play":
            self.question_age += dt
            self.time_left = max(0, self.time_left - dt)
            if self.time_left <= 0:
                self.register_shot(None, timeout=True)
        elif self.phase == "flight":
            self.question_age += dt
            self.flight_time += dt
            p = min(1, self.flight_time / self.flight_seconds)
            kind = self.active_round.theme.projectile if self.active_round else "chalk"
            xy = flight_point(kind, self.shot_from, self.shot_to, p)
            self.flight_trail.append(xy)
            if len(self.flight_trail) > 30:
                self.flight_trail.pop(0)
            if p >= 1:
                self.resolve()
        elif self.phase == "impact":
            self.impact_elapsed += dt
            if self.impact_elapsed >= 0.90:
                self.phase = "reveal"
                self.reveal_elapsed = 0.0
        elif self.phase == "reveal":
            self.reveal_elapsed += dt
            if self.reveal_elapsed >= 1.75:
                if self.lives <= 0 or self.deck.complete:
                    self.end_run()
                else:
                    self.start_shop()
        if self.phase == "end":
            self.victory_age += dt
        for effect in self.hit_effects:
            effect.age += dt
        self.hit_effects = [effect for effect in self.hit_effects if effect.age < effect.duration]
        next_particles = []
        for p in self.particles:
            p.life -= dt
            p.x += p.vx * dt
            p.y += p.vy * dt
            p.vy += 150 * dt
            p.vx *= p.drag
            if p.life > 0:
                next_particles.append(p)
        self.particles = next_particles
        next_rings = []
        for r in self.rings:
            r.life -= dt
            r.radius += (200 + (self.active_round.tier if self.active_round else 0) * 24) * dt
            if r.life > 0:
                next_rings.append(r)
        self.rings = next_rings

    def button(self, rect: pygame.Rect, label: str, accent: tuple[int, int, int] = CYAN,
               secondary: bool = False, size: int = 19, disabled: bool = False) -> None:
        hover = rect.collidepoint(self.mouse) and not disabled
        base = (32, 46, 67) if secondary or disabled else accent
        if hover:
            base = mix(base, WHITE, .15)
        shadow = rect.move(0, 5)
        rounded(self.canvas, shadow, (7, 13, 29), radius=15)
        rounded(self.canvas, rect, base, mix(accent, WHITE, .2) if secondary else None, radius=15)
        self.text(self.canvas, label, rect.centerx, rect.centery, size,
                  MUTED if disabled else WHITE if secondary else (15, 28, 44),
                  True, "center")

    def draw_background(self) -> None:
        self.canvas.blit(self.gradient, (0, 0))
        # Gallery spotlight beams and nighttime carnival dots.
        flare = pygame.Surface((W, H), pygame.SRCALPHA)
        pygame.draw.polygon(flare, (71, 132, 173, 16), [(0, 0), (200, 0), (455, 606), (0, 606)])
        pygame.draw.polygon(flare, (158, 94, 152, 16), [(1080, 0), (1280, 0), (1280, 606), (815, 606)])
        self.canvas.blit(flare, (0, 0))
        for i in range(55):
            xx = (i * 137 + 77) % W
            yy = (i * 89 + 31) % 380
            if (i % 4) != 0:
                c = int(70 + 22 * math.sin(self.time_elapsed * 1.1 + i))
                pygame.draw.circle(self.canvas, (c, c + 12, c + 30), (xx, yy), 1)
        # Display-stage board and hanging lights.
        rounded(self.canvas, (32, 118, 1216, 512), (21, 32, 51), (85, 103, 132), 24, 3)
        rounded(self.canvas, (46, 131, 1188, 485), (25, 40, 59), (46, 67, 90), 18, 1)
        pygame.draw.line(self.canvas, (84, 91, 98), (73, 153), (1207, 153), 4)
        for i in range(17):
            xx = 86 + i * 69
            tint = GOLD if i % 4 == 0 else CYAN
            pygame.draw.line(self.canvas, (94, 104, 112), (xx, 153), (xx, 161), 2)
            pygame.draw.circle(self.canvas, mix(tint, (70, 80, 87), .44), (xx, 166), 6)
            pygame.draw.circle(self.canvas, tint, (xx, 166), 2)
        # Foreground countertop.
        rounded(self.canvas, (20, 602, 1240, 104), (42, 51, 69), (95, 97, 99), 15)
        pygame.draw.rect(self.canvas, (66, 64, 66), (20, 616, 1240, 16))
        pygame.draw.line(self.canvas, (163, 132, 88), (26, 617), (1254, 617), 4)
        for xx in range(76, 1275, 164):
            pygame.draw.line(self.canvas, (53, 63, 80), (xx, 633), (xx, 691), 2)

    def header(self) -> None:
        self.text(self.canvas, "IRREGULAR", 60, 51, 30, WHITE, True, shadow=True)
        self.text(self.canvas, "RANGE", 307, 52, 30, CYAN, True, shadow=True)
        self.text(self.canvas, "SIMPLE PAST / SCHIESSSTAND", 62, 91, 13, MUTED, True)
        rounded(self.canvas, (908, 31, 277, 50), (29, 47, 67), (71, 91, 111), 14)
        draw_symbol(self.canvas, 941, 56, 15, "gold", GOLD)
        self.text(self.canvas, f"{self.coins:,}".replace(",", ".") + " MÜNZEN", 968, 57, 18, GOLD, True)
        self.button(pygame.Rect(1195, 25, 54, 54), "♪" if self.sound_on else "×", CYAN,
                    secondary=True, size=24)

    def draw_hearts(self) -> None:
        self.text(self.canvas, "LEBEN", 83, 672, 14, MUTED, True)
        for n in range(STARTING_LIVES):
            col = RED if n < self.lives else (77, 81, 100)
            draw_symbol(self.canvas, 169 + n * 30, 670, 10, "heart", col)
        self.text(self.canvas, "SERIE", 410, 672, 14, MUTED, True)
        self.text(self.canvas, str(self.streak), 481, 673, 20, GOLD, True)
        self.text(self.canvas, "GELERNT", 555, 672, 14, MUTED, True)
        self.text(self.canvas, f"{self.correct_count}/{len(VERBS)}", 675, 673, 20, CYAN, True)
        self.text(self.canvas, f"FEHLER: {self.deck.mistakes}", 758, 672, 13, RED, True)
        gear = self.active_round.theme.title if self.active_round else "Standardmunition"
        self.text(self.canvas, gear.upper()[:19], 1162, 674, 13, WHITE, True, align="right")

    def draw_dummy(self, index: int, title: str, popup: float = 1.0,
                   state: str = "neutral") -> None:
        xpos = (265, 640, 1015)[index]
        stand = (93, 91, 96)
        pygame.draw.rect(self.canvas, stand, (xpos - 7, 529, 14, 81))
        pygame.draw.polygon(self.canvas, (114, 109, 101),
                            [(xpos - 40, 595), (xpos + 40, 595), (xpos + 49, 604), (xpos - 49, 604)])
        w, h = 248, 296
        target = pygame.Surface((w, h), pygame.SRCALPHA)
        border = GREEN if state == "correct" else RED if state == "wrong" else (163, 131, 93)
        pygame.draw.circle(target, (159, 124, 85), (w // 2, 64), 56)
        pygame.draw.circle(target, (211, 172, 119), (w // 2, 61), 48)
        pygame.draw.polygon(target, (171, 135, 96),
                            [(28, 139), (66, 110), (182, 110), (220, 139), (231, 272), (17, 272)])
        rounded(target, (26, 122, 196, 150), (215, 176, 127), border, 13, 4)
        pygame.draw.line(target, (121, 93, 75), (47, 113), (29, 256), 3)
        pygame.draw.line(target, (121, 93, 75), (201, 113), (220, 256), 3)
        pygame.draw.circle(target, (125, 88, 59), (78, 57), 5)
        pygame.draw.circle(target, (125, 88, 59), (170, 57), 5)
        pygame.draw.arc(target, (125, 88, 59), (104, 58, 40, 31), .15, 2.9, 2)
        rounded(target, (36, 147, 176, 108), (35, 51, 67), border, 10, 4)
        sz = 24 if len(title) >= 9 else 29 if len(title) >= 7 else 38
        self.text(target, title, w // 2, 199, sz, WHITE, True, "center")
        self.text(target, f"ZIEL {index + 1}", w // 2, 128, 13, (67, 52, 40), True, "center")
        for cx, cy in ((46, 160), (201, 160), (46, 246), (201, 246)):
            pygame.draw.circle(target, (108, 115, 118), (cx, cy), 3)
        yfactor = max(.009, popup)
        target = pygame.transform.smoothscale(target, (w, max(2, int(h * yfactor))))
        dest = target.get_rect(midbottom=(xpos, 597))
        self.canvas.blit(target, dest)
        if state == "correct":
            pygame.draw.circle(self.canvas, GREEN, (xpos, 337), 11, 3)

    def draw_play(self) -> None:
        self.header()
        self.text(self.canvas, "WIE LAUTET DAS SIMPLE PAST VON ...?", W // 2, 204,
                  18, MUTED, True, "center")
        self.text(self.canvas, self.verb.infinitive.upper(), W // 2, 263,
                  65, WHITE, True, "center", True)
        timer_ratio = max(0, self.time_left / QUESTION_SECONDS)
        timer_col = RED if timer_ratio < .3 else GOLD if timer_ratio < .55 else GREEN
        rounded(self.canvas, (399, 304, 482, 15), (44, 58, 72), radius=7)
        if timer_ratio > .002:
            rounded(self.canvas, (401, 306, max(1, int(478 * timer_ratio)), 11), timer_col, radius=6)
        self.text(self.canvas, f"{self.time_left:0.1f}s", 894, 310, 17, timer_col, True)
        popup = self.popup_progress()
        for i, word in enumerate(self.options):
            self.draw_dummy(i, word, popup)
        self.draw_hearts()
        self.text(self.canvas, "KLICK AUF DIE RICHTIGE FORM · EIN SCHUSS · 5 SEKUNDEN", 641, 642,
                  12, MUTED, True, "center")
        x, y = self.mouse
        if 56 < x < 1225 and 165 < y < 610:
            pygame.draw.circle(self.canvas, CYAN, point(x, y), 18, 2)
            pygame.draw.circle(self.canvas, WHITE, point(x, y), 2)
            pygame.draw.line(self.canvas, CYAN, point(x - 25, y), point(x - 8, y), 2)
            pygame.draw.line(self.canvas, CYAN, point(x + 8, y), point(x + 25, y), 2)
            pygame.draw.line(self.canvas, CYAN, point(x, y - 25), point(x, y - 8), 2)
            pygame.draw.line(self.canvas, CYAN, point(x, y + 8), point(x, y + 25), 2)

    def draw_bullet(self) -> None:
        if self.phase != "flight" or self.outcome == "timeout":
            return
        u = self.active_round
        kind = u.theme.projectile if u else "chalk"
        draw_weapon_trail(self.canvas, kind, u.tier if u else 0,
                          self.shot_from, self.shot_to,
                          min(1.0, self.flight_time / self.flight_seconds),
                          self.time_elapsed, draw_symbol)

    def draw_particles(self) -> None:
        for r in self.rings:
            t = r.life / r.maxlife
            color = mix(BG, r.color, t)
            pygame.draw.circle(self.canvas, color, point(r.x, r.y), max(1, int(r.radius)),
                               max(1, int(r.width * t)))
        for p in self.particles:
            t = p.life / p.lifespan
            color = mix(BG, p.color, max(.10, t))
            draw_symbol(self.canvas, p.x, p.y, max(3, p.size * (.45 + t * .7)), p.kind, color)
        for e in self.hit_effects:
            if e.age >= 0:
                draw_weapon_impact(self.canvas, e.kind, e.x, e.y, e.age,
                                   e.tier, draw_symbol, e.duration)

    def draw_reveal(self) -> None:
        self.header()
        self.text(self.canvas, "WIE LAUTET DAS SIMPLE PAST VON ...?", W // 2, 204,
                  18, MUTED, True, "center")
        self.text(self.canvas, self.verb.infinitive.upper(), W // 2, 263, 65, WHITE, True,
                  "center", True)
        for i, word in enumerate(self.options):
            if i == self.correct_index:
                status = "correct"
            elif i == self.chosen_index:
                status = "wrong"
            else:
                status = "neutral"
            self.draw_dummy(i, word, 1, status)
        # Large, legible correction in every case, especially after a miss.
        box = pygame.Surface((770, 151), pygame.SRCALPHA)
        rounded(box, (0, 0, 770, 151), (11, 22, 39), GREEN if self.outcome == "correct" else RED, 22, 4)
        box.set_alpha(246)
        self.canvas.blit(box, (255, 339))
        title = "TREFFER!" if self.outcome == "correct" else "ZEIT ABGELAUFEN!" if self.outcome == "timeout" else "DANEBEN!"
        self.text(self.canvas, title, W // 2, 374, 23,
                  GREEN if self.outcome == "correct" else RED, True, "center")
        ans = self.verb.simple_past.upper()
        self.text(self.canvas, "RICHTIG: " + ans, W // 2, 423,
                  38 if len(ans) < 9 else 31, WHITE, True, "center", True)
        suffix = f"+{self.winnings} MÜNZEN" if self.outcome == "correct" else "−1 LEBEN"
        self.text(self.canvas, suffix, W // 2, 465, 17,
                  GOLD if self.outcome == "correct" else RED, True, "center")
        self.draw_hearts()

    def draw_menu(self) -> None:
        # Three target dummies make the tutorial immediately understandable.
        for idx, choice in enumerate(("go", "went", "goed")):
            self.draw_dummy(idx, choice, 1, "correct" if idx == 1 else "neutral")
        wash = pygame.Surface((1280, 720), pygame.SRCALPHA)
        pygame.draw.rect(wash, (6, 11, 26, 162), (0, 0, 1280, 720))
        self.canvas.blit(wash, (0, 0))
        self.header()
        rounded(self.canvas, (263, 178, 754, 437), (19, 32, 53), (87, 125, 146), 27, 3)
        self.text(self.canvas, "IRREGULAR RANGE", W // 2, 252, 49, CYAN, True, "center", True)
        self.text(self.canvas, "DER SCHIESSSTAND FÜR UNREGELMÄSSIGE VERBEN", W // 2, 308,
                  17, WHITE, True, "center")
        self.text(self.canvas, "Treffe in 5 Sekunden die richtige Simple-Past-Form.", W // 2, 370,
                  18, MUTED, False, "center")
        self.text(self.canvas, "28 VERBEN RICHTIG PRO RUN  ·  5 LEBEN  ·  280 UPGRADES", W // 2, 427,
                  15, GOLD, True, "center")
        self.text(self.canvas, "Münzen und gekaufte Munition bleiben gespeichert.", W // 2, 465,
                  15, MUTED, False, "center")
        self.button(pygame.Rect(452, 510, 376, 69), "JETZT SPIELEN", CYAN, size=23)
        self.text(self.canvas, f"REKORD: {self.progress['best']}/{len(VERBS)}  ·  ABSCHLÜSSE: {self.progress['completions']}", W // 2, 642,
                  15, GOLD, True, "center")

    def shop_card(self, upgrade: Upgrade, rect: pygame.Rect) -> None:
        owned = upgrade.id in self.owned
        equipped = upgrade.id == self.equipped
        affordable = self.coins >= upgrade.cost
        hover = rect.collidepoint(self.mouse)
        border = GREEN if equipped else CYAN if owned else GOLD if affordable else (66, 87, 105)
        rounded(self.canvas, rect.move(0, 5), (8, 15, 29), radius=16)
        rounded(self.canvas, rect, mix((31, 45, 68), (49, 64, 84), .35 if hover else 0), border, 16, 2)
        pygame.draw.circle(self.canvas, (22, 32, 54), (rect.x + 44, rect.y + 46), 32)
        theme = upgrade.theme
        # Animate each shop thumbnail, so projectile families look different
        # BEFORE the player buys them. Clip effects inside the preview window.
        clip = self.canvas.get_clip()
        self.canvas.set_clip(pygame.Rect(rect.x + 6, rect.y + 8, 76, 78))
        preview_age = (self.time_elapsed * .60 + (upgrade.theme_index % 4) * .17) % 1.05
        draw_weapon_impact(self.canvas, theme.projectile, rect.x + 44, rect.y + 46,
                           preview_age, min(4, upgrade.tier), draw_symbol)
        self.canvas.set_clip(clip)
        draw_symbol(self.canvas, rect.x + 44, rect.y + 46, 19,
                    theme.projectile, theme.color, theme.accent)
        title = theme.title.upper()
        textsize = 17 if len(title) < 17 else 14
        self.text(self.canvas, title, rect.x + 83, rect.y + 33, textsize, WHITE, True)
        self.text(self.canvas, f"STUFE {upgrade.tier}/10  ·  {upgrade.name.split(' · ')[-1]}",
                  rect.x + 83, rect.y + 65, 12, MUTED, True)
        pygame.draw.line(self.canvas, (67, 82, 103), (rect.x + 20, rect.y + 91),
                         (rect.right - 20, rect.y + 91), 1)
        for n in range(10):
            pygame.draw.rect(self.canvas, theme.color if n < upgrade.tier else (60, 75, 94),
                             (rect.x + 20 + n * 19, rect.y + 108, 14, 6), border_radius=2)
        state = "ANGELEGT" if equipped else "AUSRÜSTEN" if owned else "KAUFEN" if affordable else "ZU TEUER"
        self.text(self.canvas, state, rect.x + 21, rect.y + 143, 13, border, True)
        self.text(self.canvas, "IM BESITZ" if owned else f"{upgrade.cost}  MÜNZEN", rect.right - 20,
                  rect.y + 143, 13, GREEN if owned else GOLD, True, "right")

    def draw_shop(self) -> None:
        self.header()
        self.text(self.canvas, "MUNITIONS-WERKSTATT", 62, 120, 30, WHITE, True)
        self.text(self.canvas, f"{self.correct_count}/{len(VERBS)} GELERNT  ·  {len(self.owned)}/{len(UPGRADES)} UPGRADES", 1196, 119,
                  15, MUTED, True, "right")
        rounded(self.canvas, (60, 145, 1160, 79), (42, 60, 76), (98, 142, 161), 15)
        draw_symbol(self.canvas, 103, 184, 24, self.trial_candidate.theme.projectile,
                    self.trial_candidate.theme.color, self.trial_candidate.theme.accent)
        self.text(self.canvas, "KOSTENLOSER PROBESCHUSS", 152, 169, 18, CYAN, True)
        sample = f"{self.trial_candidate.theme.title} · Stufe {self.trial_candidate.tier} · nur nächste Frage"
        self.text(self.canvas, sample, 152, 201, 14, WHITE)
        self.button(pygame.Rect(997, 152, 208, 59),
                    "AUSGEWÄHLT ✓" if self.trial_pending else "GRATIS TESTEN", GREEN,
                    secondary=bool(self.trial_pending), size=16)
        for i, upgrade in enumerate(shop_page(self.page)):
            col, row = i % 3, i // 3
            rect = pygame.Rect(60 + col * 393, 237 + row * 188, 369, 166)
            self.shop_card(upgrade, rect)
        maxpage = (len(UPGRADES) - 1) // PAGE_SIZE
        self.button(pygame.Rect(62, 635, 54, 52), "‹", CYAN, secondary=True, size=27,
                    disabled=self.page == 0)
        self.text(self.canvas, f"SEITE {self.page + 1} / {maxpage + 1}", 169, 661,
                  15, WHITE, True, "center")
        self.button(pygame.Rect(223, 635, 54, 52), "›", CYAN, secondary=True, size=27,
                    disabled=self.page == maxpage)
        self.text(self.canvas, "Klick: kaufen oder ausrüsten", 307, 660, 14, MUTED)
        self.button(pygame.Rect(989, 635, 227, 56), "NÄCHSTE FRAGE  ›", GREEN, size=17)
        if self.toast and self.toast_age < 2.4:
            rounded(self.canvas, (396, 634, 570, 49), (54, 65, 83), GOLD, 12)
            self.text(self.canvas, self.toast[:55], 681, 659, 13, WHITE, True, "center")

    def draw_end(self) -> None:
        self.header()
        if self.completed:
            # A victory lap of falling coins and stars, independent of selected ammo.
            for i in range(47):
                px = 59 + (i * 179) % 1175
                py = ((i * 83 + self.victory_age * (40 + i % 6 * 9)) % 650) + 15
                draw_symbol(self.canvas, px, py, 4 + i % 7,
                            "gold" if i % 3 == 0 else "star",
                            GOLD if i % 3 == 0 else (118, 226, 238), WHITE)
        rounded(self.canvas, (241, 158, 798, 514), (21, 34, 56),
                GOLD if self.completed else (106, 135, 158), 24, 3)
        if self.completed:
            self.text(self.canvas, "ALLE 28 VERBEN GESCHAFFT!", W // 2, 224,
                      34, GOLD, True, "center", True)
            self.text(self.canvas, "Jedes Verb einmal richtig – gut gemacht!", W // 2, 280,
                      18, GREEN, True, "center")
        else:
            self.text(self.canvas, "RUNDE BEENDET", W // 2, 224,
                      42, RED, True, "center", True)
            self.text(self.canvas, "Keine Leben mehr. Versuch die übrigen Verben erneut!", W // 2, 280,
                      16, MUTED, False, "center")
        self.text(self.canvas, f"{self.correct_count}/{len(VERBS)}", 474, 366,
                  58, CYAN, True, "center", True)
        self.text(self.canvas, "VERBEN BEHERRSCHT", 474, 411, 14, MUTED, True, "center")
        self.text(self.canvas, str(self.deck.mistakes), 804, 366,
                  58, RED if self.deck.mistakes else GREEN, True, "center", True)
        self.text(self.canvas, "FEHLER IN DIESEM RUN", 804, 411, 14, MUTED, True, "center")
        if self.completed:
            rounded(self.canvas, (358, 437, 564, 67), (64, 73, 58), GOLD, 15, 2)
            self.text(self.canvas, f"+{self.bonus_awarded:,} BONUS-MÜNZEN".replace(",", "."),
                      W // 2, 470, 27, GOLD, True, "center")
        else:
            self.text(self.canvas, "ABSCHLUSS-BONUS: ALLE VERBEN RICHTIG LÖSEN",
                      W // 2, 472, 15, MUTED, True, "center")
        self.text(self.canvas, f"BESTER RUN: {self.progress['best']}/{len(VERBS)}  ·  ABGESCHLOSSEN: {self.progress['completions']}",
                  W // 2, 517, 13, MUTED, True, "center")
        self.button(pygame.Rect(449, 540, 382, 58), "NOCHMAL SPIELEN", CYAN, size=21)
        self.button(pygame.Rect(501, 611, 278, 44), "BEENDEN", CYAN, secondary=True, size=16)

    def render(self) -> None:
        self.draw_background()
        if self.phase == "menu":
            self.draw_menu()
        elif self.phase == "play":
            self.draw_play()
        elif self.phase == "flight":
            self.draw_play()
            self.draw_bullet()
        elif self.phase == "impact":
            self.draw_play()
            if self.outcome == "correct":
                kind = self.active_round.theme.projectile if self.active_round else "chalk"
                effect_words = {"football": "TOOOOR!", "explosion": "KABOOM!",
                                "firework": "FEUERWERK!", "gold": "JACKPOT!",
                                "laser": "ZAPP!", "lightning": "BLITZ!"}
                if kind in effect_words:
                    self.text(self.canvas, effect_words[kind], 640, 346, 40, GOLD,
                              True, "center", True)
        elif self.phase == "reveal":
            self.draw_particles()
            self.draw_reveal()
        elif self.phase == "shop":
            self.draw_shop()
        elif self.phase == "end":
            self.draw_end()
        if self.phase != "reveal":
            self.draw_particles()
        if self.flash > 0:
            layer = pygame.Surface((W, H), pygame.SRCALPHA)
            layer.fill((250, 247, 213, int(self.flash * 75)))
            self.canvas.blit(layer, (0, 0))
        # Letterboxing preserves mouse hit targets at any window resolution.
        sw, sh = self.window.get_size()
        scale = min(sw / W, sh / H)
        dw, dh = max(1, int(W * scale)), max(1, int(H * scale))
        x, y = (sw - dw) // 2, (sh - dh) // 2
        self.window.fill((5, 9, 19))
        image = self.canvas if (dw, dh) == (W, H) else pygame.transform.smoothscale(self.canvas, (dw, dh))
        self.window.blit(image, (x, y))
        pygame.display.flip()

    def loop(self, smoke_test: bool = False) -> None:
        frames = 0
        while self.running:
            dt = self.clock.tick(FPS) / 1000
            screen_point = self.screen_mouse(pygame.mouse.get_pos())
            self.mouse = screen_point or (-100, -100)
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    self.running = False
                elif event.type == pygame.VIDEORESIZE:
                    self.window = pygame.display.set_mode((max(640, event.w), max(360, event.h)), pygame.RESIZABLE)
                elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                    mapped = self.screen_mouse(event.pos)
                    if mapped:
                        self.click(mapped)
            self.update(dt)
            self.render()
            frames += 1
            if smoke_test and frames == 4:
                # Exercise play, timer, a correct shot, particle FX and the shop.
                self.new_run()
                self.register_shot(self.correct_index, (640, 480))
            if smoke_test and frames == 12:
                self.resolve() if self.phase == "flight" else None
                self.start_shop()
                self.trial()
                self.start_question()
                self.register_shot(None, timeout=True)
            if smoke_test and frames >= 18:
                break
        self.save_progress()
        pygame.quit()


def main() -> None:
    Game().loop(smoke_test="--smoke-test" in sys.argv)


if __name__ == "__main__":
    main()
