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

BG = (6, 9, 20)
PANEL = (18, 26, 54)
PANEL_DARK = (11, 18, 39)
WHITE = (241, 246, 255)
MUTED = (167, 178, 207)
CYAN = (34, 230, 255)
GOLD = (255, 197, 61)
GREEN = (182, 255, 59)
RED = (255, 93, 125)
ORANGE = (255, 122, 26)
BLUE = (61, 139, 255)
VIOLET = (181, 77, 255)
AMBER = (255, 176, 32)
RARITY_COLORS = (MUTED, BLUE, VIOLET, AMBER)
RARITY_NAMES = ("GEW\u00d6HNLICH", "SELTEN", "EPISCH", "LEGEND\u00c4R")


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


def bevel_points(rect: pygame.Rect | tuple[int, int, int, int], cut: int = 16) -> list[tuple[int, int]]:
    """Single asymmetric chamfer, unlike the previous multiple octagonal rims."""
    r = pygame.Rect(rect)
    cut = max(1, min(cut, r.w // 4, r.h // 4))
    return [(r.left + cut, r.top), (r.right, r.top),
            (r.right, r.bottom - cut), (r.right - cut, r.bottom),
            (r.left, r.bottom), (r.left, r.top + cut)]


def glow_circle(surface: pygame.Surface, center: tuple[int, int], radius: int,
                color: tuple[int, int, int], width: int = 2, passes: int = 5) -> None:
    """Small local SRCALPHA glow. Normal alpha-blit; never ADD an RGBA rectangle."""
    pad = max(8, passes * 4 + width + 2)
    side = 2 * (radius + pad)
    layer = pygame.Surface((side, side), pygame.SRCALPHA)
    mid = (side // 2, side // 2)
    for i in range(passes, 0, -1):
        pygame.draw.circle(layer, (*color, max(4, 26 - 4 * i)), mid,
                           radius + i * 3, max(1, width + i))
    surface.blit(layer, (center[0] - side // 2, center[1] - side // 2))


def glow_text(surface: pygame.Surface, img: pygame.Surface, rect: pygame.Rect,
              color: tuple[int, int, int], passes: int = 4) -> None:
    """Glyph-shaped glow with alpha, not a full-screen additive surface."""
    for d in range(passes, 0, -1):
        halo = img.copy()
        halo.set_alpha(max(8, 27 - d * 5))
        for dx, dy in ((-d, 0), (d, 0), (0, -d), (0, d)):
            surface.blit(halo, rect.move(dx, dy))


def draw_panel(surface: pygame.Surface, rect: pygame.Rect | tuple[int, int, int, int],
               fill: tuple[int, int, int] = PANEL,
               border: tuple[int, int, int] = CYAN,
               cut: int = 16, border_width: int = 1,
               glow_color: tuple[int, int, int] | None = None,
               shadow_offset: int = 4) -> pygame.Rect:
    r = pygame.Rect(rect)
    points = bevel_points(r, cut)
    if shadow_offset:
        pygame.draw.polygon(surface, (3, 6, 17),
                            [(x, y + shadow_offset) for x, y in points])
    if glow_color:
        # The outer halo must not erase neighboring panels or text.
        local = pygame.Surface((r.w + 18, r.h + 18), pygame.SRCALPHA)
        for i in range(5, 0, -1):
            new_r = pygame.Rect(9 - i, 9 - i, r.w + 2 * i, r.h + 2 * i)
            pygame.draw.polygon(local, (*glow_color, max(2, 13 - 2 * i)),
                                bevel_points(new_r, cut), 1)
        surface.blit(local, (r.x - 9, r.y - 9))
    pygame.draw.polygon(surface, fill, points)
    pygame.draw.polygon(surface, border, points, border_width)
    # Thin accent on top like the provided shop cards.
    if r.w > 100 and r.h > 45:
        pygame.draw.line(surface, border, (r.x + cut, r.y + 1),
                         (r.right - 1, r.y + 1), 2)
    return r


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
        self.fonts: dict[tuple[str, int, bool], pygame.font.Font] = {}
        self.font_sources = self.locate_fonts()
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

    def locate_fonts(self) -> dict[str, str | None]:
        # The GitHub Actions build bundles the three SIL-OFL fonts.
        font_dir = Path(__file__).resolve().parent / "assets" / "fonts"
        def match(names: tuple[str, ...], families: tuple[str, ...]) -> str | None:
            for name in names:
                candidate = font_dir / name
                if candidate.is_file():
                    return str(candidate)
            for family in families:
                match = pygame.font.match_font(family)
                if match:
                    return match
            return None
        return {
            "title": match(("RussoOne-Regular.ttf",), ("russo one", "dejavusans", "segoe ui", "arial")),
            "label": match(("ChakraPetch-Regular.ttf",), ("chakra petch", "segoe ui", "arial")),
            "number": match(("Orbitron-Regular.ttf",), ("orbitron", "consolas", "dejavusans", "arial")),
        }

    def font(self, size: int, bold: bool = False, family: str = "label") -> pygame.font.Font:
        key = (family, size, bold)
        if key not in self.fonts:
            source = self.font_sources.get(family)
            if source:
                font = pygame.font.Font(source, max(8, size))
            else:
                fallbacks = {"title": "arial", "label": "arial", "number": "consolas"}
                font = pygame.font.SysFont(fallbacks.get(family, "arial"), max(8, size))
            if bold and family != "title":
                font.set_bold(True)
            self.fonts[key] = font
        return self.fonts[key]

    def text(self, surface: pygame.Surface, content: str, x: float, y: float,
             size: int = 24, color: tuple[int, int, int] = WHITE,
             bold: bool = False, align: str = "left", shadow: bool = False,
             family: str = "label", max_width: int | None = None) -> pygame.Rect:
        """Fit text to its allotted slot, preventing collisions and truncation."""
        font = self.font(size, bold, family)
        if max_width is not None:
            while size > 10 and font.size(content)[0] > max_width:
                size -= 1
                font = self.font(size, bold, family)
            if font.size(content)[0] > max_width:
                while content and font.size(content + "...")[0] > max_width:
                    content = content[:-1]
                content += "..."
        img = font.render(content, True, color)
        rect = img.get_rect()
        if align == "center":
            rect.center = point(x, y)
        elif align == "right":
            rect.midright = point(x, y)
        else:
            rect.midleft = point(x, y)
        if shadow:
            # Dark two-pixel offset keeps white lettering readable.
            silhouette = font.render(content, True, (3, 7, 20))
            surface.blit(silhouette, rect.move(2, 2))
            if family == "title" and color in (CYAN, GREEN, GOLD):
                glow_text(surface, img, rect, color, 3)
        surface.blit(img, rect)
        return rect

    def make_gradient(self) -> pygame.Surface:
        gradient = pygame.Surface((W, H))
        for y in range(H):
            # Restrained top-right teal rather than the saturated gradients of v3.
            t = y / H
            pygame.draw.line(gradient, mix(BG, (10, 16, 33), t), (0, y), (W, y))
        # Thin horizontal scanlines, barely visible at native resolution.
        for y in range(0, H, 4):
            pygame.draw.line(gradient, (11, 18, 36), (0, y), (W, y), 1)
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
                self.rings.append(Ring(x, y, .38 + i * .08, .38 + i * .08,
                                       12 + i * 13, theme.color if i % 2 == 0 else theme.accent, 2))
            if tier >= 9:
                for j in range(2):
                    px = self.rng.uniform(120, 1160)
                    py = self.rng.uniform(235, 485)
                    self.rings.append(Ring(px, py, .48, .48, 10, theme.accent, 2))
            self.flash = min(.20, tier / 60)
            self.shake = 1 + tier * .35
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

    def target_float(self, idx: int) -> float:
        return math.sin(self.time_elapsed * 2.2 + idx * .85) * 8.0

    def target_rect(self, idx: int) -> pygame.Rect:
        x = (330, 640, 950)[idx]
        height = max(1, int(264 * max(.02, self.popup_progress())))
        return pygame.Rect(x - 120, 529 + int(self.target_float(idx)) - height,
                           240, height)


    def screen_mouse(self, p: tuple[int, int]) -> tuple[float, float] | None:
        sw, sh = self.window.get_size()
        scale = min(sw / W, sh / H)
        dx, dy = (sw - W * scale) / 2, (sh - H * scale) / 2
        xx, yy = (p[0] - dx) / scale, (p[1] - dy) / scale
        return (xx, yy) if 0 <= xx < W and 0 <= yy < H else None

    def click(self, pos: tuple[float, float]) -> None:
        x, y = pos
        if pygame.Rect(1196, 26, 52, 52).collidepoint(x, y):
            self.sound_on = not self.sound_on
            self.save_progress()
            return
        if self.phase == "menu":
            if pygame.Rect(452, 508, 376, 62).collidepoint(x, y):
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
            if pygame.Rect(1034, 158, 198, 56).collidepoint(x, y):
                self.trial()
            elif pygame.Rect(994, 638, 236, 51).collidepoint(x, y):
                self.sound("trial")
                self.start_question()
            elif pygame.Rect(46, 645, 52, 46).collidepoint(x, y):
                self.page = max(0, self.page - 1)
                self.sound("trial")
            elif pygame.Rect(200, 645, 52, 46).collidepoint(x, y):
                self.page = min((len(UPGRADES) - 1) // PAGE_SIZE, self.page + 1)
                self.sound("trial")
            else:
                for i, upgrade in enumerate(shop_page(self.page)):
                    col, row = i % 3, i // 3
                    rect = pygame.Rect(32 + col * 412, 233 + row * 195, 392, 179)
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
            r.radius += (65 + (self.active_round.tier if self.active_round else 0) * 4) * dt
            if r.life > 0:
                next_rings.append(r)
        self.rings = next_rings

    def button(self, rect: pygame.Rect, label: str,
               accent: tuple[int, int, int] = CYAN,
               secondary: bool = False, size: int = 19,
               disabled: bool = False) -> None:
        hover = rect.collidepoint(self.mouse) and not disabled
        if disabled:
            draw_panel(self.canvas, rect, PANEL_DARK, (62, 83, 113),
                       cut=10, border_width=1, shadow_offset=2)
            ink = (101, 120, 156)
        elif secondary:
            draw_panel(self.canvas, rect, mix(PANEL, accent, .035), accent,
                       cut=10, border_width=1, glow_color=accent if hover else None,
                       shadow_offset=2)
            ink = accent
        else:
            draw_panel(self.canvas, rect, mix(accent, WHITE, .10 if hover else 0), accent,
                       cut=12, border_width=1, glow_color=accent if hover else None,
                       shadow_offset=3)
            ink = BG
        self.text(self.canvas, label, rect.centerx, rect.centery,
                  size, ink, True, "center", family="title",
                  max_width=rect.w - 30)

    def draw_background(self) -> None:
        self.canvas.blit(self.gradient, (0, 0))
        # Clean dark background with subtle columns; no giant solid cyan/purple ellipses.
        for x in range(0, W + 1, 120):
            pygame.draw.line(self.canvas, (13, 23, 42), (x, 0), (x, H), 1)
        if self.phase not in ("play", "flight", "impact", "reveal", "menu"):
            return
        horizon = 548
        pygame.draw.line(self.canvas, (22, 69, 83), (0, horizon), (W, horizon), 2)
        for x in range(-350, W + 400, 83):
            pygame.draw.line(self.canvas, (15, 43, 62), (W // 2, horizon), (x, H), 1)
        for i in range(1, 10):
            y = horizon + int(7 + i * i * 2.1)
            if y < H:
                pygame.draw.line(self.canvas, (15, 43, 62), (0, y), (W, y), 1)


    def header(self) -> None:
        # Header matches the supplied composition: no overlapping neon tiles.
        pygame.draw.circle(self.canvas, CYAN, (55, 51), 18, 2)
        pygame.draw.circle(self.canvas, (255, 72, 154), (55, 51), 6, 2)
        for dx, dy in ((-27, 0), (27, 0), (0, -27), (0, 27)):
            pygame.draw.line(self.canvas, CYAN, (55 + dx * .70, 51 + dy * .70),
                             (55 + dx, 51 + dy), 2)
        self.text(self.canvas, "IRREGULAR", 91, 44, 29, WHITE, True,
                  family="title", max_width=195)
        self.text(self.canvas, "RANGE", 290, 44, 29, CYAN, True,
                  family="title", max_width=130)
        self.text(self.canvas, "SIMPLE PAST  //  SCHIESSSTAND", 91, 79, 13,
                  MUTED, False, family="label", max_width=310)
        draw_panel(self.canvas, (1001, 27, 187, 53), PANEL, GOLD,
                   cut=11, border_width=1, shadow_offset=2)
        draw_symbol(self.canvas, 1030, 54, 11, "gold", GOLD)
        self.text(self.canvas, f"{self.coins:,}".replace(",", "."), 1050, 53,
                  24, GOLD, True, family="number", max_width=74)
        self.text(self.canvas, "M\u00dcNZEN", 1180, 53, 12,
                  MUTED, False, "right", family="label", max_width=65)
        self.button(pygame.Rect(1196, 26, 52, 52),
                    "*" if self.sound_on else "x", CYAN,
                    secondary=True, size=24)

    def draw_hearts(self) -> None:
        slots = [
            ((32, 627, 258, 72), CYAN),
            ((300, 627, 224, 72), ORANGE),
            ((534, 627, 192, 72), CYAN),
            ((736, 627, 152, 72), GREEN),
            ((898, 627, 350, 72), CYAN),
        ]
        for r, c in slots:
            draw_panel(self.canvas, r, PANEL, c, cut=13,
                       border_width=1, shadow_offset=2)
        self.text(self.canvas, "LEBEN", 51, 660, 13, MUTED,
                  family="label")
        for i in range(STARTING_LIVES):
            color = RED if i < self.lives else (72, 81, 101)
            draw_symbol(self.canvas, 131 + i * 27, 659, 10,
                        "heart", color)
        self.text(self.canvas, "SERIE", 322, 653, 12, MUTED,
                  family="label")
        self.text(self.canvas, f"COMBO x{max(1, self.streak)}", 408, 671,
                  19, ORANGE, True, "center", family="title", max_width=180)
        self.text(self.canvas, "GELERNT", 554, 648, 13, MUTED,
                  family="label")
        self.text(self.canvas, f"{self.correct_count}/{len(VERBS)}", 669, 648,
                  20, CYAN, True, "right", family="number", max_width=115)
        rounded(self.canvas, (554, 675, 150, 7), (29, 38, 69), radius=3)
        if self.correct_count:
            rounded(self.canvas, (554, 675, max(2, int(150 * self.correct_count / len(VERBS))), 7),
                    CYAN, radius=3)
        self.text(self.canvas, "FEHLER", 754, 651, 12, MUTED,
                  family="label")
        self.text(self.canvas, str(self.deck.mistakes), 867, 651, 23,
                  GREEN if self.deck.mistakes == 0 else RED,
                  True, "right", family="number")
        self.text(self.canvas, "AUSGER\u00dcSTET", 919, 645, 12, MUTED,
                  family="label")
        if self.active_round:
            theme = self.active_round.theme
            draw_symbol(self.canvas, 932, 669, 16, theme.projectile,
                        theme.color, theme.accent)
            gear = theme.title.upper()
            self.text(self.canvas, gear, 959, 668, 18, WHITE,
                      True, family="title", max_width=216)
            self.text(self.canvas, f"LV {self.active_round.tier}", 1223, 668,
                      14, CYAN, True, "right", family="number", max_width=55)
        else:
            self.text(self.canvas, "STANDARD", 920, 668, 18, WHITE,
                      True, family="title")

    def draw_dummy(self, index: int, title: str, popup: float = 1.0,
                   state: str = "neutral") -> None:
        xpos = (330, 640, 950)[index]
        float_y = self.target_float(index)
        state_color = GREEN if state == "correct" else RED if state == "wrong" else CYAN
        w, h = 240, 264
        unit = pygame.Surface((w, h), pygame.SRCALPHA)
        center = (w // 2, 66)
        # Floating holographic concentric targets with light outlines only.
        for rad, thickness in ((62, 1), (48, 2), (35, 2), (18, 2)):
            pygame.draw.circle(unit, state_color, center, rad, thickness)
        pygame.draw.circle(unit, state_color, center, 9)
        for dx in (-78, 78):
            bx = center[0] + dx
            delta = 10 if dx < 0 else -10
            pygame.draw.polygon(unit, state_color,
                                [(bx, 66), (bx + delta, 56), (bx + delta, 76)], 2)
        pygame.draw.line(unit, state_color, (w // 2, 5), (w // 2, 0), 3)
        pygame.draw.line(unit, state_color, (w // 2, 128), (w // 2, 150), 2)
        self.text(unit, f"{index + 1}  ZIEL {index + 1}", w // 2, 162,
                  14, state_color, False, "center", family="label")
        plate = pygame.Rect(0, 174, 240, 80)
        fill = mix(PANEL, state_color, .12 if state != "neutral" else 0.015)
        draw_panel(unit, plate, fill, state_color, cut=14,
                   border_width=2 if state == "correct" else 1,
                   shadow_offset=0)
        self.text(unit, title, w // 2, 216,
                  36 if len(title) < 7 else 30, WHITE, True, "center",
                  family="title", max_width=211)
        # Target extends upward from a consistent stand, with sinusoidal bobbing.
        yfactor = max(.01, popup)
        unit = pygame.transform.smoothscale(unit, (w, max(2, int(h * yfactor))))
        footer = 529 + int(float_y)
        shadow = pygame.Surface((160, 18), pygame.SRCALPHA)
        pygame.draw.ellipse(shadow, (*state_color, 19), (0, 1, 160, 13))
        self.canvas.blit(shadow, (xpos - 80, 546))
        self.canvas.blit(unit, unit.get_rect(midbottom=(xpos, footer)))
        if state == "correct":
            glow_circle(self.canvas, (xpos, 330 + int(float_y)), 36, GREEN, 1, 3)

    def draw_play(self) -> None:
        self.header()
        self.text(self.canvas, "WIE LAUTET DAS SIMPLE PAST VON ...?", 640, 115,
                  18, MUTED, False, "center", family="label")
        self.text(self.canvas, self.verb.infinitive.upper(), 640, 172,
                  78, WHITE, True, "center", family="title", max_width=440)
        # Progress stripe and right-aligned timer ring (draw.arc as requested).
        completed = self.correct_count / len(VERBS)
        rounded(self.canvas, (427, 220, 421, 9), (26, 34, 57), radius=4)
        if completed:
            rounded(self.canvas, (427, 220, max(3, int(421 * completed)), 9), CYAN, radius=4)
        timer_rect = pygame.Rect(850, 123, 99, 99)
        ratio = max(0, min(1, self.time_left / QUESTION_SECONDS))
        tint = ORANGE if ratio < .3 else GOLD if ratio < .62 else CYAN
        pygame.draw.arc(self.canvas, (48, 58, 83), timer_rect, -math.pi / 2,
                        1.5 * math.pi, 6)
        if ratio > .001:
            pygame.draw.arc(self.canvas, tint, timer_rect, -math.pi / 2,
                            -math.pi / 2 + math.tau * ratio, 7)
        self.text(self.canvas, f"{self.time_left:0.1f}", 899, 164,
                  26, GOLD, True, "center", family="number")
        self.text(self.canvas, "SEK", 899, 192, 12, MUTED,
                  False, "center", family="label")
        popup = self.popup_progress()
        for i, word in enumerate(self.options):
            self.draw_dummy(i, word, popup)
        self.text(self.canvas, "KLICK AUF DIE RICHTIGE FORM  *  EIN SCHUSS  *  5 SEKUNDEN",
                  640, 603, 13, MUTED, False, "center", family="label")
        self.draw_hearts()
        x, y = self.mouse
        if 60 < x < 1220 and 260 < y < 530:
            pygame.draw.circle(self.canvas, CYAN, point(x, y), 15, 1)
            pygame.draw.circle(self.canvas, WHITE, point(x, y), 2)
            pygame.draw.line(self.canvas, CYAN, point(x - 20, y), point(x - 8, y), 1)
            pygame.draw.line(self.canvas, CYAN, point(x + 8, y), point(x + 20, y), 1)
            pygame.draw.line(self.canvas, CYAN, point(x, y - 20), point(x, y - 8), 1)
            pygame.draw.line(self.canvas, CYAN, point(x, y + 8), point(x, y + 20), 1)


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
        # Never obscure the header, question, clickable answer plates or HUD.
        previous = self.canvas.get_clip()
        if self.phase in ("play", "flight", "impact", "reveal"):
            self.canvas.set_clip(pygame.Rect(130, 245, 1020, 295))
        for r in self.rings:
            t = r.life / r.maxlife
            pygame.draw.circle(self.canvas, mix(BG, r.color, .45 * t), point(r.x, r.y),
                               max(1, int(r.radius)), max(1, int(r.width * t)))
        for p in self.particles:
            t = p.life / p.lifespan
            draw_symbol(self.canvas, p.x, p.y, max(3, p.size * (.45 + t * .7)),
                        p.kind, mix(BG, p.color, .45 * t))
        for e in self.hit_effects:
            if e.age >= 0:
                draw_weapon_impact(self.canvas, e.kind, e.x, e.y, e.age,
                                   min(e.tier, 10), draw_symbol, e.duration)
        self.canvas.set_clip(previous)

    def draw_reveal(self) -> None:
        self.header()
        self.text(self.canvas, "WIE LAUTET DAS SIMPLE PAST VON ...?", 640, 115,
                  18, MUTED, False, "center", family="label")
        self.text(self.canvas, self.verb.infinitive.upper(), 640, 172,
                  78, WHITE, True, "center", family="title")
        for i, word in enumerate(self.options):
            state = "correct" if i == self.correct_index else "wrong" if i == self.chosen_index else "neutral"
            self.draw_dummy(i, word, 1, state)
        success = self.outcome == "correct"
        color = GREEN if success else ORANGE if self.outcome == "timeout" else RED
        # Foreground correction panel ensures answer is readable over target FX.
        draw_panel(self.canvas, (286, 347, 708, 140), PANEL, color,
                   cut=16, border_width=2, shadow_offset=4)
        title = "TREFFER!" if success else "ZEIT ABGELAUFEN!" if self.outcome == "timeout" else "DANEBEN!"
        self.text(self.canvas, title, 640, 375, 22, color, True,
                  "center", family="title", max_width=640)
        self.text(self.canvas, "RICHTIG: " + self.verb.simple_past.upper(),
                  640, 421, 35, WHITE, True, "center", family="title", max_width=650)
        self.text(self.canvas, f"+{self.winnings} M\u00dcNZEN" if success else "-1 LEBEN",
                  640, 465, 17, GOLD if success else color, True,
                  "center", family="number")
        self.draw_hearts()


    def draw_menu(self) -> None:
        for index, title in enumerate(("go", "went", "goed")):
            self.draw_dummy(index, title, 1, "correct" if index == 1 else "neutral")
        veil = pygame.Surface((W, H), pygame.SRCALPHA)
        veil.fill((6, 9, 20, 185))
        self.canvas.blit(veil, (0, 0))
        self.header()
        draw_panel(self.canvas, (260, 156, 760, 423), PANEL, CYAN,
                   cut=18, border_width=2)
        self.text(self.canvas, "IRREGULAR RANGE", 640, 223, 47, CYAN,
                  True, "center", family="title", max_width=690)
        self.text(self.canvas, "DER SCHIESSSTAND F\u00dcR UNREGELM\u00c4SSIGE VERBEN",
                  640, 284, 18, WHITE, False, "center", family="label", max_width=690)
        self.text(self.canvas, "Treffe in 5 Sekunden die richtige Simple-Past-Form.",
                  640, 352, 18, MUTED, False, "center", family="label", max_width=670)
        self.text(self.canvas, "28 VERBEN  *  5 LEBEN  *  280 MUNITIONEN",
                  640, 415, 15, GOLD, True, "center", family="label")
        self.text(self.canvas, "M\u00fcnzen und gekaufte Munition bleiben gespeichert.",
                  640, 460, 15, MUTED, False, "center", family="label")
        self.button(pygame.Rect(452, 508, 376, 62), "JETZT SPIELEN", CYAN, size=23)
        self.text(self.canvas, f"REKORD: {self.progress['best']}/{len(VERBS)}  *  RUNS: {self.progress['completions']}",
                  640, 624, 14, GOLD, True, "center", family="label")

    def shop_card(self, upgrade: Upgrade, rect: pygame.Rect) -> None:
        owned = upgrade.id in self.owned
        equipped = upgrade.id == self.equipped
        affordable = self.coins >= upgrade.cost
        tier = upgrade.tier
        rarity_index = upgrade.theme_index % 4
        rarity_name = RARITY_NAMES[rarity_index]
        rarity_col = RARITY_COLORS[rarity_index]
        border = GREEN if equipped or (affordable and not owned) else rarity_col
        fill = mix(PANEL, rarity_col, .04)
        hover = rect.collidepoint(self.mouse)
        draw_panel(self.canvas, rect, fill, border,
                   cut=14, border_width=2 if hover else 1,
                   glow_color=border if hover else None, shadow_offset=2)
        theme = upgrade.theme
        # One recognizable symbol in a dark tile, not full-screen impact geometry.
        tile = pygame.Rect(rect.x + 18, rect.y + 21, 67, 67)
        pygame.draw.rect(self.canvas, PANEL_DARK, tile)
        pygame.draw.rect(self.canvas, mix(theme.color, PANEL, .50), tile, 1)
        draw_symbol(self.canvas, tile.centerx, tile.centery,
                    16 + 2 * math.sin(self.time_elapsed * 2 + upgrade.theme_index),
                    theme.projectile, theme.color, theme.accent)
        self.text(self.canvas, theme.title.upper(), rect.x + 100,
                  rect.y + 34, 20, WHITE, True, family="title", max_width=rect.w - 126)
        label = pygame.Rect(rect.x + 100, rect.y + 54, 106, 22)
        pygame.draw.rect(self.canvas, rarity_col, label)
        self.text(self.canvas, rarity_name, label.centerx, label.centery,
                  11, BG, True, "center", family="label", max_width=98)
        self.text(self.canvas, f"STUFE {tier}/10  *  {upgrade.name.split(' * ')[-1].split(' \u00b7 ')[-1]}",
                  rect.x + 100, rect.y + 91, 13, MUTED,
                  False, family="label", max_width=rect.w - 119)
        for i in range(10):
            seg = pygame.Rect(rect.x + 18 + i * 35, rect.y + 107, 29, 7)
            rounded(self.canvas, seg,
                    rarity_col if i < tier else (34, 42, 71), radius=2)
        state = "ANGELEGT" if equipped else "AUSR\u00dcSTEN" if owned else "KAUFEN" if affordable else "ZU TEUER"
        action_r = pygame.Rect(rect.x + 18, rect.bottom - 51, 130, 36)
        if affordable and not owned:
            draw_panel(self.canvas, action_r, GREEN, GREEN,
                       cut=8, shadow_offset=1)
            action_ink = BG
        elif equipped:
            draw_panel(self.canvas, action_r, PANEL_DARK, GREEN,
                       cut=8, shadow_offset=1)
            action_ink = GREEN
        else:
            draw_panel(self.canvas, action_r, PANEL_DARK, (70, 81, 111),
                       cut=8, shadow_offset=1)
            action_ink = MUTED
        self.text(self.canvas, state, action_r.centerx, action_r.centery,
                  14, action_ink, True, "center", family="label", max_width=118)
        if owned:
            self.text(self.canvas, "IM BESITZ", rect.right - 20,
                      rect.bottom - 34, 13, GREEN, True, "right", family="label")
        else:
            self.text(self.canvas, f"{upgrade.cost}", rect.right - 19,
                      rect.bottom - 34, 22, GOLD if affordable else MUTED,
                      True, "right", family="number", max_width=90)
            draw_symbol(self.canvas, rect.right - 94, rect.bottom - 34,
                        10, "gold", GOLD)

    def draw_shop(self) -> None:
        self.header()
        self.text(self.canvas, "MUNITIONS-WERKSTATT", 32, 115, 32,
                  WHITE, True, family="title", max_width=690)
        draw_panel(self.canvas, (930, 94, 150, 39), PANEL, CYAN,
                   cut=8, border_width=1, shadow_offset=1)
        self.text(self.canvas, f"{self.correct_count}/{len(VERBS)} GELERNT", 1005, 114,
                  14, CYAN, True, "center", family="number", max_width=134)
        draw_panel(self.canvas, (1090, 94, 158, 39), PANEL, (77, 98, 138),
                   cut=8, border_width=1, shadow_offset=1)
        self.text(self.canvas, f"{len(self.owned)}/{len(UPGRADES)} UPGRADES", 1169, 114,
                  14, MUTED, True, "center", family="number", max_width=142)
        draw_panel(self.canvas, (32, 145, 1216, 72),
                   mix(PANEL, CYAN, .065), CYAN, cut=14, border_width=1,
                   shadow_offset=3)
        draw_symbol(self.canvas, 78, 181, 23,
                    self.trial_candidate.theme.projectile,
                    self.trial_candidate.theme.color,
                    self.trial_candidate.theme.accent)
        self.text(self.canvas, "KOSTENLOSER PROBESCHUSS", 112, 172,
                  21, CYAN, True, family="title", max_width=750)
        self.text(self.canvas,
                  f"{self.trial_candidate.theme.title} * Stufe {self.trial_candidate.tier} * nur n\u00e4chste Frage",
                  112, 196, 15, WHITE, False,
                  family="label", max_width=700)
        self.button(pygame.Rect(1034, 158, 198, 56),
                    "AUSGEW\u00c4HLT" if self.trial_pending else "GRATIS TESTEN",
                    CYAN, secondary=bool(self.trial_pending), size=17)
        for i, upgrade in enumerate(shop_page(self.page)):
            x = 32 + (i % 3) * 412
            y = 233 + (i // 3) * 195
            self.shop_card(upgrade, pygame.Rect(x, y, 392, 179))
        draw_panel(self.canvas, (32, 632, 1216, 70), PANEL, (78, 103, 145),
                   cut=10, border_width=1, shadow_offset=1)
        last = (len(UPGRADES) - 1) // PAGE_SIZE
        self.button(pygame.Rect(46, 645, 52, 46), "<", CYAN,
                    secondary=True, size=26, disabled=self.page == 0)
        self.text(self.canvas, f"SEITE {self.page + 1}/{last + 1}", 149, 668,
                  15, WHITE, True, "center", family="number", max_width=95)
        self.button(pygame.Rect(200, 645, 52, 46), ">", CYAN,
                    secondary=True, size=26, disabled=self.page == last)
        self.text(self.canvas, "Klick: kaufen oder ausr\u00fcsten", 278, 666,
                  14, MUTED, family="label")
        self.button(pygame.Rect(994, 638, 236, 51),
                    "N\u00c4CHSTE FRAGE  >", CYAN, size=18)
        if self.toast and self.toast_age < 2.4:
            draw_panel(self.canvas, (404, 641, 540, 46), PANEL, GOLD, cut=8,
                       border_width=1, shadow_offset=0)
            self.text(self.canvas, self.toast[:46], 674, 664, 13,
                      WHITE, True, "center", family="label", max_width=512)


    def draw_end(self) -> None:
        self.header()
        if self.completed:
            for i in range(47):
                px = 59 + (i * 179) % 1175
                py = ((i * 83 + self.victory_age * (40 + i % 6 * 9)) % 650) + 15
                draw_symbol(self.canvas, px, py, 4 + i % 7,
                            "gold" if i % 3 == 0 else "star",
                            GOLD if i % 3 == 0 else CYAN, WHITE)
        frame = GOLD if self.completed else RED
        draw_panel(self.canvas, (241, 158, 798, 514), PANEL, frame, cut=22, border_width=3,
                   glow_color=None)
        if self.completed:
            self.text(self.canvas, "ALLE 28 VERBEN GESCHAFFT!", W // 2, 224,
                      36, GOLD, True, "center", True, family="title")
            self.text(self.canvas, "Jedes Verb einmal richtig – gut gemacht!", W // 2, 280,
                      18, GREEN, True, "center", family="label")
        else:
            self.text(self.canvas, "RUNDE BEENDET", W // 2, 224,
                      42, RED, True, "center", True, family="title")
            self.text(self.canvas, "Keine Leben mehr. Versuch die übrigen Verben erneut!", W // 2, 280,
                      16, MUTED, False, "center", family="label")
        self.text(self.canvas, f"{self.correct_count}/{len(VERBS)}", 474, 366,
                  58, CYAN, True, "center", True, family="number")
        self.text(self.canvas, "VERBEN BEHERRSCHT", 474, 411, 14, MUTED, True, "center", family="label")
        self.text(self.canvas, str(self.deck.mistakes), 804, 366,
                  58, RED if self.deck.mistakes else GREEN, True, "center", True, family="number")
        self.text(self.canvas, "FEHLER IN DIESEM RUN", 804, 411, 14, MUTED, True, "center", family="label")
        if self.completed:
            draw_panel(self.canvas, (358, 437, 564, 67), mix(PANEL, GOLD, .12), GOLD, cut=14,
                       border_width=2, glow_color=GOLD)
            self.text(self.canvas, f"+{self.bonus_awarded:,} BONUS-MÜNZEN".replace(",", "."),
                      W // 2, 470, 27, GOLD, True, "center", False, family="title")
        else:
            self.text(self.canvas, "ABSCHLUSS-BONUS: ALLE VERBEN RICHTIG LÖSEN",
                      W // 2, 472, 15, MUTED, True, "center", family="label")
        self.text(self.canvas, f"BESTER RUN: {self.progress['best']}/{len(VERBS)}  ·  ABGESCHLOSSEN: {self.progress['completions']}",
                  W // 2, 517, 13, MUTED, True, "center", family="label")
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
                              True, "center", True, family="title")
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
        self.window.fill(BG)
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
