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
PANEL_DARK = (10, 16, 33)
WHITE = (241, 246, 255)
MUTED = (167, 178, 207)
CYAN = (34, 230, 255)
GOLD = (255, 197, 61)
GREEN = (182, 255, 59)
RED = (255, 96, 126)
ORANGE = (255, 122, 26)
BLUE = (61, 139, 255)
VIOLET = (181, 77, 255)
AMBER = (255, 176, 32)
RARITY_COLORS = {
    "GEWÖHNLICH": MUTED,
    "SELTEN": BLUE,
    "EPISCH": VIOLET,
    "LEGENDÄR": AMBER,
}


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
    r = rect if isinstance(rect, pygame.Rect) else pygame.Rect(rect)
    cut = max(4, min(cut, r.w // 4, r.h // 4))
    return [
        (r.left + cut, r.top),
        (r.right - cut, r.top),
        (r.right, r.top + cut),
        (r.right, r.bottom - cut),
        (r.right - cut, r.bottom),
        (r.left + cut, r.bottom),
        (r.left, r.bottom - cut),
        (r.left, r.top + cut),
    ]


def glow_circle(surface: pygame.Surface, center: tuple[int, int], radius: int,
                color: tuple[int, int, int], width: int = 2, passes: int = 5) -> None:
    """Small additive glow layer; do not allocate a full-screen surface."""
    padding = int(radius + passes * 5 + width + 2)
    temp = pygame.Surface((padding * 2, padding * 2), pygame.SRCALPHA)
    for i in range(passes, 0, -1):
        alpha = int(18 + 12 * i)
        pygame.draw.circle(temp, (*color, alpha), (padding, padding),
                           radius + i * 4, max(1, width + i))
    surface.blit(temp, (center[0] - padding, center[1] - padding),
                 special_flags=pygame.BLEND_ADD)


def glow_text(surface: pygame.Surface, img: pygame.Surface, rect: pygame.Rect,
              color: tuple[int, int, int], passes: int = 5) -> None:
    """Additive text halo, bounded to the glyphs rather than the screen."""
    pad = passes * 2 + 2
    temp = pygame.Surface((img.get_width() + pad * 2,
                           img.get_height() + pad * 2), pygame.SRCALPHA)
    for i in range(passes, 0, -1):
        layer = img.copy()
        layer.set_alpha(16 + i * 8)
        for dx, dy in ((-i, 0), (i, 0), (0, -i), (0, i), (-i, -i), (i, i)):
            temp.blit(layer, (pad + dx, pad + dy))
    surface.blit(temp, (rect.left - pad, rect.top - pad),
                 special_flags=pygame.BLEND_ADD)


def draw_panel(surface: pygame.Surface, rect: pygame.Rect | tuple[int, int, int, int],
               fill: tuple[int, int, int] = PANEL,
               border: tuple[int, int, int] = CYAN,
               cut: int = 16, border_width: int = 2,
               glow_color: tuple[int, int, int] | None = None,
               shadow_offset: int = 5) -> pygame.Rect:
    """8-corner beveled panels with a thin accent edge and optional glow."""
    r = rect if isinstance(rect, pygame.Rect) else pygame.Rect(rect)
    if glow_color or shadow_offset:
        # Keep all intermediate layers local to the panel to maintain 60 FPS.
        pad = max(9, int(max(r.w, r.h) * .09) + border_width + 4)
        layer_size = (r.w + pad * 2, r.h + pad * 2 + max(0, shadow_offset))
        local = pygame.Rect(pad, pad, r.w, r.h)
        position = (r.left - pad, r.top - pad)
        if shadow_offset:
            shadow = pygame.Surface(layer_size, pygame.SRCALPHA)
            pygame.draw.polygon(shadow, (0, 0, 0, 90),
                                bevel_points(local.move(0, shadow_offset), cut))
            surface.blit(shadow, position)
        if glow_color:
            temp = pygame.Surface(layer_size, pygame.SRCALPHA)
            pts = bevel_points(local, cut)
            cx, cy = local.center
            for i in range(5, 0, -1):
                scale = 1.0 + i * .03
                expanded = [(int(cx + (px - cx) * scale),
                             int(cy + (py - cy) * scale)) for px, py in pts]
                pygame.draw.polygon(temp, (*glow_color, 12 + i * 9), expanded,
                                    max(1, border_width + i // 2))
            surface.blit(temp, position, special_flags=pygame.BLEND_ADD)
    pygame.draw.polygon(surface, fill, bevel_points(r, cut))
    pygame.draw.polygon(surface, border, bevel_points(r, cut), border_width)
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
        asset_dir = Path(__file__).with_name("assets") / "fonts"

        def find(file_names: tuple[str, ...], families: tuple[str, ...]) -> str | None:
            for name in file_names:
                path = asset_dir / name
                if path.exists():
                    return str(path)
            for family in families:
                match = pygame.font.match_font(family)
                if match:
                    return match
            return None

        return {
            "title": find(("RussoOne-Regular.ttf", "Russo_One.ttf"), ("russo one", "impact", "arial black")),
            "label": find(("ChakraPetch-Regular.ttf", "ChakraPetch-Medium.ttf"), ("chakra petch", "bahnschrift", "arial")),
            "number": find(("Orbitron-Regular.ttf", "Orbitron-Medium.ttf"), ("orbitron", "consolas", "arial")),
        }

    def font(self, size: int, bold: bool = False, family: str = "label") -> pygame.font.Font:
        key = (family, size, bold)
        if key not in self.fonts:
            source = self.font_sources.get(family)
            if source:
                self.fonts[key] = pygame.font.Font(source, size)
            else:
                fallback = {"title": "arialblack", "label": "arial", "number": "consolas"}.get(family, "arial")
                self.fonts[key] = pygame.font.SysFont(fallback, size, bold=bold)
        return self.fonts[key]

    def text(self, surface: pygame.Surface, content: str, x: float, y: float,
             size: int = 24, color: tuple[int, int, int] = WHITE,
             bold: bool = False, align: str = "left", shadow: bool = False,
             family: str = "label") -> pygame.Rect:
        font = self.font(size, bold, family)
        img = font.render(content, True, color)
        rect = img.get_rect()
        if align == "center":
            rect.center = point(x, y)
        elif align == "right":
            rect.midright = point(x, y)
        else:
            rect.midleft = point(x, y)
        if shadow:
            glow_text(surface, img, rect, color)
            dark = font.render(content, True, (2, 6, 14))
            surface.blit(dark, rect.move(2, 3))
        surface.blit(img, rect)
        return rect

    def make_gradient(self) -> pygame.Surface:
        gradient = pygame.Surface((W, H))
        top, bottom = BG, (9, 20, 48)
        for y in range(H):
            pygame.draw.line(gradient, mix(top, bottom, y / H), (0, y), (W, y))
        shade = pygame.Surface((W, H), pygame.SRCALPHA)
        pygame.draw.rect(shade, (8, 6, 18, 70), (0, 0, W, H))
        gradient.blit(shade, (0, 0))
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

    def target_float(self, idx: int) -> float:
        return math.sin(self.time_elapsed * 2.2 + idx * 0.85) * 8.0

    def target_rect(self, idx: int) -> pygame.Rect:
        x = (265, 640, 1015)[idx]
        progress = self.popup_progress()
        height = max(1, int(296 * progress))
        bottom = 597 + int(self.target_float(idx))
        return pygame.Rect(x - 124, bottom - height, 248, height)

    def screen_mouse(self, p: tuple[int, int]) -> tuple[float, float] | None:
        sw, sh = self.window.get_size()
        scale = min(sw / W, sh / H)
        dx, dy = (sw - W * scale) / 2, (sh - H * scale) / 2
        xx, yy = (p[0] - dx) / scale, (p[1] - dy) / scale
        return (xx, yy) if 0 <= xx < W and 0 <= yy < H else None

    def click(self, pos: tuple[float, float]) -> None:
        x, y = pos
        if pygame.Rect(1198, 24, 54, 58).collidepoint(x, y):
            self.sound_on = not self.sound_on
            self.save_progress()
            return
        if self.phase == "menu":
            if pygame.Rect(444, 498, 392, 72).collidepoint(x, y):
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
            if pygame.Rect(988, 163, 220, 60).collidepoint(x, y):
                self.trial()
            elif pygame.Rect(979, 632, 237, 62).collidepoint(x, y):
                self.sound("trial")
                self.start_question()
            elif pygame.Rect(62, 641, 54, 52).collidepoint(x, y):
                self.page = max(0, self.page - 1)
                self.sound("trial")
            elif pygame.Rect(223, 641, 54, 52).collidepoint(x, y):
                self.page = min((len(UPGRADES) - 1) // PAGE_SIZE, self.page + 1)
                self.sound("trial")
            else:
                for i, upgrade in enumerate(shop_page(self.page)):
                    col, row = i % 3, i // 3
                    rect = pygame.Rect(60 + col * 393, 254 + row * 184, 369, 168)
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
        border = mix(accent, WHITE, .18) if hover else accent
        if disabled:
            border = (75, 86, 112)
        fill = PANEL if secondary or disabled else mix(accent, WHITE, .08 if hover else 0.0)
        glow = None if disabled else border
        draw_panel(self.canvas, rect, fill, border, cut=14, border_width=2,
                   glow_color=glow if hover or not secondary else None)
        text_col = MUTED if disabled else WHITE if secondary else BG
        self.text(self.canvas, label, rect.centerx, rect.centery + 1, size,
                  text_col, True, "center", family="title")

    def draw_background(self) -> None:
        self.canvas.blit(self.gradient, (0, 0))
        grid = pygame.Surface((W, H), pygame.SRCALPHA)
        for x in range(0, W + 1, 40):
            pygame.draw.line(grid, (34, 230, 255, 22), (x, 0), (x, H), 1)
        for y in range(0, H + 1, 40):
            pygame.draw.line(grid, (34, 230, 255, 14), (0, y), (W, y), 1)
        horizon = 534
        pygame.draw.line(grid, (34, 230, 255, 55), (0, horizon), (W, horizon), 2)
        for x in range(-280, W + 320, 80):
            pygame.draw.line(grid, (34, 230, 255, 22), (W // 2, horizon), (x, H), 1)
        for i in range(1, 8):
            y = horizon + i * 22 + i * i * 4
            pygame.draw.line(grid, (34, 230, 255, max(8, 28 - i * 2)), (0, y), (W, y), 1)
        self.canvas.blit(grid, (0, 0))
        flare = pygame.Surface((W, H), pygame.SRCALPHA)
        pygame.draw.ellipse(flare, (34, 230, 255, 32), (-120, 380, 540, 200))
        pygame.draw.ellipse(flare, (181, 77, 255, 24), (860, 420, 460, 180))
        self.canvas.blit(flare, (0, 0), special_flags=pygame.BLEND_ADD)

    def header(self) -> None:
        glow_circle(self.canvas, (55, 52), 16, CYAN, 2)
        pygame.draw.circle(self.canvas, CYAN, (55, 52), 16, 2)
        pygame.draw.circle(self.canvas, RED, (55, 52), 5)
        pygame.draw.line(self.canvas, CYAN, (32, 52), (22, 52), 2)
        pygame.draw.line(self.canvas, CYAN, (78, 52), (88, 52), 2)
        pygame.draw.line(self.canvas, CYAN, (55, 29), (55, 19), 2)
        pygame.draw.line(self.canvas, CYAN, (55, 75), (55, 85), 2)
        self.text(self.canvas, "IRREGULAR", 92, 42, 31, WHITE, True, shadow=True, family="title")
        self.text(self.canvas, "RANGE", 295, 42, 31, CYAN, True, shadow=True, family="title")
        self.text(self.canvas, "SIMPLE PAST  //  SCHIESSSTAND", 92, 82, 14, MUTED, True, family="label")
        draw_panel(self.canvas, (980, 24, 204, 58), PANEL, GOLD, cut=14, border_width=2,
                   glow_color=GOLD)
        draw_symbol(self.canvas, 1014, 53, 14, "gold", GOLD)
        self.text(self.canvas, f"{self.coins:,}".replace(",", "."), 1042, 53, 24, GOLD, True,
                  family="number")
        self.text(self.canvas, "MÜNZEN", 1130, 53, 15, MUTED, True, family="label")
        self.button(pygame.Rect(1198, 24, 54, 58), "♪" if self.sound_on else "×", CYAN,
                    secondary=True, size=20)

    def draw_hearts(self) -> None:
        def hud(rect: tuple[int, int, int, int], border: tuple[int, int, int]):
            draw_panel(self.canvas, rect, PANEL, border, cut=12, border_width=2,
                       glow_color=border)

        hud((28, 620, 240, 74), CYAN)
        self.text(self.canvas, "LEBEN", 52, 645, 13, MUTED, True, family="label")
        for n in range(STARTING_LIVES):
            col = RED if n < self.lives else (69, 79, 107)
            draw_symbol(self.canvas, 108 + n * 28, 670, 10, "heart", col)

        hud((286, 620, 214, 74), ORANGE)
        self.text(self.canvas, "SERIE", 311, 644, 13, MUTED, True, family="label")
        self.text(self.canvas, f"COMBO x{max(1, self.streak)}", 393, 670, 24, ORANGE, True,
                  "center", True, family="title")

        hud((516, 620, 202, 74), CYAN)
        self.text(self.canvas, "GELERNT", 540, 644, 13, MUTED, True, family="label")
        self.text(self.canvas, f"{self.correct_count}/{len(VERBS)}", 617, 667, 26, CYAN, True,
                  "center", False, family="number")
        rounded(self.canvas, (540, 683, 152, 7), PANEL_DARK, radius=3)
        rounded(self.canvas, (540, 683, max(6, int(152 * self.correct_count / len(VERBS))), 7), CYAN, radius=3)

        hud((732, 620, 150, 74), GREEN if self.deck.mistakes == 0 else RED)
        self.text(self.canvas, "FEHLER", 755, 644, 13, MUTED, True, family="label")
        self.text(self.canvas, str(self.deck.mistakes), 808, 668, 30,
                  GREEN if self.deck.mistakes == 0 else RED, True, "center", False, family="number")

        hud((898, 620, 354, 74), self.active_round.theme.color if self.active_round else CYAN)
        self.text(self.canvas, "AUSGERÜSTET", 924, 644, 13, MUTED, True, family="label")
        gear = self.active_round.theme.title if self.active_round else "Standard"
        self.text(self.canvas, gear.upper()[:22], 955 if self.active_round else 924, 669, 21, WHITE, True,
                  family="title")
        if self.active_round:
            draw_symbol(self.canvas, 922, 669, 11, self.active_round.theme.projectile,
                        self.active_round.theme.color, self.active_round.theme.accent)
            self.text(self.canvas, f"LV {self.active_round.tier}", 1199, 668, 20, CYAN, True,
                      "center", False, family="number")

    def draw_dummy(self, index: int, title: str, popup: float = 1.0,
                   state: str = "neutral") -> None:
        xpos = (265, 640, 1015)[index]
        float_y = self.target_float(index)
        state_color = GREEN if state == "correct" else RED if state == "wrong" else CYAN
        w, h = 248, 296
        target = pygame.Surface((w, h), pygame.SRCALPHA)
        center = (w // 2, 64)
        glow_circle(target, center, 52, state_color, 2)
        for radius, width, color in ((52, 3, state_color), (34, 2, CYAN), (16, 2, CYAN)):
            pygame.draw.circle(target, color, center, radius, width)
        pygame.draw.circle(target, CYAN, center, 5)
        for dx in (-67, 67):
            pygame.draw.polygon(target, CYAN, [(center[0] + dx, center[1]),
                                               (center[0] + dx - (10 if dx > 0 else -10), center[1] - 9),
                                               (center[0] + dx - (10 if dx > 0 else -10), center[1] + 9)], 1)
        pygame.draw.line(target, CYAN, (center[0], 116), (center[0], 164), 2)
        self.text(target, f"ZIEL {index + 1}", center[0], 136, 14, WHITE, True, "center",
                  family="label")
        answer_rect = pygame.Rect(18, 176, 212, 84)
        fill = mix(PANEL, state_color, .18 if state != "neutral" else 0.0)
        draw_panel(target, answer_rect, fill, state_color, cut=12, border_width=2,
                   glow_color=state_color if state != "neutral" else CYAN)
        sz = 27 if len(title) >= 9 else 33 if len(title) >= 7 else 42
        self.text(target, title, w // 2, answer_rect.centery + 3, sz, WHITE, True,
                  "center", True, family="title")
        yfactor = max(.009, popup)
        target = pygame.transform.smoothscale(target, (w, max(2, int(h * yfactor))))
        shadow = pygame.Surface((184, 34), pygame.SRCALPHA)
        pygame.draw.ellipse(shadow, (34, 230, 255, 48), (0, 8, 184, 16))
        self.canvas.blit(shadow, (xpos - 92, 584 + int(float_y * .25)), special_flags=pygame.BLEND_ADD)
        dest = target.get_rect(midbottom=(xpos, 597 + int(float_y)))
        self.canvas.blit(target, dest)
        if state == "correct":
            glow_circle(self.canvas, (xpos, 323 + int(float_y)), 12, GREEN, 2)
            pygame.draw.circle(self.canvas, GREEN, (xpos, 323 + int(float_y)), 12, 2)

    def draw_play(self) -> None:
        self.header()
        self.text(self.canvas, "WIE LAUTET DAS SIMPLE PAST VON ...?", W // 2, 134,
                  19, MUTED, True, "center", family="label")
        self.text(self.canvas, self.verb.infinitive.upper(), W // 2, 204,
                  88, WHITE, True, "center", True, family="title")
        progress_ratio = self.correct_count / len(VERBS)
        rounded(self.canvas, (414, 248, 430, 12), PANEL_DARK, radius=5)
        rounded(self.canvas, (414, 248, max(1, int(430 * progress_ratio)), 12),
                mix(CYAN, GOLD, progress_ratio), radius=5)
        ring_rect = pygame.Rect(812, 136, 124, 124)
        timer_ratio = max(0, self.time_left / QUESTION_SECONDS)
        timer_col = GREEN if timer_ratio > .55 else GOLD if timer_ratio > .3 else ORANGE
        glow_circle(self.canvas, ring_rect.center, 50, timer_col, 5)
        pygame.draw.arc(self.canvas, mix(CYAN, PANEL, .55), ring_rect, -math.pi / 2,
                        1.5 * math.pi, 8)
        if timer_ratio > 0.001:
            pygame.draw.arc(self.canvas, timer_col, ring_rect, -math.pi / 2,
                            -math.pi / 2 + math.tau * timer_ratio, 8)
        self.text(self.canvas, f"{self.time_left:0.1f}", ring_rect.centerx, ring_rect.centery - 4,
                  28, WHITE, True, "center", False, family="number")
        self.text(self.canvas, "SEK", ring_rect.centerx, ring_rect.centery + 24,
                  13, MUTED, True, "center", family="label")
        popup = self.popup_progress()
        for i, word in enumerate(self.options):
            self.draw_dummy(i, word, popup)
        self.draw_hearts()
        self.text(self.canvas, "KLICK AUF DIE RICHTIGE FORM  ♦  EIN SCHUSS  ♦  5 SEKUNDEN", 641, 606,
                  14, MUTED, True, "center", family="label")
        x, y = self.mouse
        if 56 < x < 1225 and 120 < y < 610:
            glow_circle(self.canvas, point(x, y), 18, CYAN, 2)
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
        self.text(self.canvas, "WIE LAUTET DAS SIMPLE PAST VON ...?", W // 2, 134,
                  19, MUTED, True, "center", family="label")
        self.text(self.canvas, self.verb.infinitive.upper(), W // 2, 204, 88, WHITE, True,
                  "center", True, family="title")
        for i, word in enumerate(self.options):
            if i == self.correct_index:
                status = "correct"
            elif i == self.chosen_index:
                status = "wrong"
            else:
                status = "neutral"
            self.draw_dummy(i, word, 1, status)
        result_color = GREEN if self.outcome == "correct" else ORANGE if self.outcome == "timeout" else RED
        draw_panel(self.canvas, (255, 354, 770, 132), mix(PANEL, result_color, .12), result_color,
                   cut=18, border_width=3, glow_color=result_color)
        title = "TREFFER!" if self.outcome == "correct" else "ZEIT ABGELAUFEN!" if self.outcome == "timeout" else "DANEBEN!"
        self.text(self.canvas, title, W // 2, 386, 24,
                  result_color, True, "center", False, family="title")
        ans = self.verb.simple_past.upper()
        self.text(self.canvas, "RICHTIG: " + ans, W // 2, 428,
                  38 if len(ans) < 9 else 31, WHITE, True, "center", True, family="title")
        suffix = f"+{self.winnings} MÜNZEN" if self.outcome == "correct" else "−1 LEBEN"
        self.text(self.canvas, suffix, W // 2, 466, 19,
                  GOLD if self.outcome == "correct" else result_color, True, "center", family="number")
        self.draw_hearts()

    def draw_menu(self) -> None:
        for idx, choice in enumerate(("go", "went", "goed")):
            self.draw_dummy(idx, choice, 1, "correct" if idx == 1 else "neutral")
        wash = pygame.Surface((1280, 720), pygame.SRCALPHA)
        pygame.draw.rect(wash, (6, 9, 20, 168), (0, 0, 1280, 720))
        self.canvas.blit(wash, (0, 0))
        self.header()
        draw_panel(self.canvas, (256, 164, 768, 416), PANEL, CYAN, cut=22, border_width=3,
                   glow_color=CYAN)
        self.text(self.canvas, "IRREGULAR RANGE", W // 2, 236, 54, CYAN, True, "center", True, family="title")
        self.text(self.canvas, "DER SCHIESSSTAND FÜR UNREGELMÄSSIGE VERBEN", W // 2, 294,
                  18, WHITE, True, "center", family="label")
        self.text(self.canvas, "Treffe in 5 Sekunden die richtige Simple-Past-Form.", W // 2, 356,
                  19, MUTED, False, "center", family="label")
        self.text(self.canvas, "28 VERBEN PRO RUN  ♦  5 LEBEN  ♦  COIN-BONUS BEI PERFEKTEM ABSCHLUSS", W // 2, 406,
                  15, GOLD, True, "center", family="label")
        self.text(self.canvas, "Münzen und gekaufte Munition bleiben gespeichert.", W // 2, 450,
                  16, MUTED, False, "center", family="label")
        self.button(pygame.Rect(444, 498, 392, 72), "JETZT SPIELEN", CYAN, size=24)
        self.text(self.canvas, f"REKORD: {self.progress['best']}/{len(VERBS)}  ·  ABSCHLÜSSE: {self.progress['completions']}", W // 2, 618,
                  15, GOLD, True, "center", family="label")

    def shop_card(self, upgrade: Upgrade, rect: pygame.Rect) -> None:
        owned = upgrade.id in self.owned
        equipped = upgrade.id == self.equipped
        affordable = self.coins >= upgrade.cost
        hover = rect.collidepoint(self.mouse)
        rarity = ("GEWÖHNLICH", "SELTEN", "EPISCH", "LEGENDÄR")[upgrade.theme_index % 4]
        rarity_color = RARITY_COLORS[rarity]
        border = GREEN if equipped else rarity_color
        fill = mix(PANEL, border, .12 if hover else 0.04)
        draw_panel(self.canvas, rect, fill, border, cut=16, border_width=2,
                   glow_color=border if hover or equipped else None)
        theme = upgrade.theme
        icon_box = pygame.Rect(rect.x + 18, rect.y + 22, 82, 82)
        draw_panel(self.canvas, icon_box, PANEL_DARK, mix(theme.color, CYAN, .35), cut=12,
                   border_width=1, glow_color=theme.color)
        clip = self.canvas.get_clip()
        self.canvas.set_clip(icon_box.inflate(-10, -10))
        preview_age = (self.time_elapsed * .70 + (upgrade.theme_index % 4) * .17) % 1.05
        draw_weapon_impact(self.canvas, theme.projectile, icon_box.centerx, icon_box.centery,
                           preview_age, min(7, upgrade.tier), draw_symbol)
        self.canvas.set_clip(clip)
        draw_symbol(self.canvas, icon_box.centerx, icon_box.centery, 18,
                    theme.projectile, theme.color, theme.accent)
        title = theme.title.upper()
        textsize = 18 if len(title) < 15 else 15
        self.text(self.canvas, title, rect.x + 118, rect.y + 32, textsize, WHITE, True,
                  family="title")
        badge = pygame.Rect(rect.x + 118, rect.y + 52, 104, 24)
        draw_panel(self.canvas, badge, mix(PANEL, rarity_color, .15), rarity_color, cut=8,
                   border_width=1)
        self.text(self.canvas, rarity, badge.centerx, badge.centery + 1, 11, rarity_color,
                  True, "center", family="label")
        self.text(self.canvas, f"STUFE {upgrade.tier}/10 · {upgrade.name.split(' · ')[-1]}",
                  rect.x + 118, rect.y + 88, 13, MUTED, True, family="label")
        for n in range(10):
            seg = pygame.Rect(rect.x + 18 + n * 33, rect.y + 107, 28, 7)
            rounded(self.canvas, seg, theme.color if n < upgrade.tier else PANEL_DARK, radius=3)
        state = "ANGELEGT" if equipped else "AUSRÜSTEN" if owned else "KAUFEN" if affordable else "ZU TEUER"
        action_rect = pygame.Rect(rect.x + 18, rect.bottom - 44, 114, 33)
        action_fill = GREEN if (affordable and not owned) else PANEL_DARK if not equipped else mix(PANEL, GREEN, .2)
        action_border = GREEN if equipped or (affordable and not owned) else MUTED
        draw_panel(self.canvas, action_rect, action_fill, action_border, cut=10, border_width=1)
        self.text(self.canvas, state, action_rect.centerx, action_rect.centery + 1, 13,
                  BG if affordable and not owned else WHITE, True, "center", family="title")
        cost_color = GREEN if owned else GOLD if affordable else MUTED
        self.text(self.canvas, "IM BESITZ" if owned else f"{upgrade.cost}", rect.right - 42,
                  rect.bottom - 27, 21, cost_color, True, "right", False, family="number")
        if not owned:
            draw_symbol(self.canvas, rect.right - 78, rect.bottom - 27, 10, "gold", GOLD)

    def draw_shop(self) -> None:
        self.header()
        self.text(self.canvas, "MUNITIONS-WERKSTATT", 60, 116, 34, WHITE, True, family="title")
        draw_panel(self.canvas, (914, 100, 152, 42), PANEL, CYAN, cut=10, border_width=2)
        self.text(self.canvas, f"{self.correct_count}/{len(VERBS)} GELERNT", 990, 121, 16, CYAN, True,
                  "center", False, family="number")
        draw_panel(self.canvas, (1080, 100, 168, 42), PANEL, MUTED, cut=10, border_width=2)
        self.text(self.canvas, f"{len(self.owned)}/{len(UPGRADES)} UPGRADES", 1164, 121, 16, MUTED, True,
                  "center", False, family="number")
        draw_panel(self.canvas, (60, 150, 1160, 86), mix(PANEL, CYAN, .07), CYAN, cut=16, border_width=2,
                   glow_color=CYAN)
        draw_symbol(self.canvas, 102, 193, 24, self.trial_candidate.theme.projectile,
                    self.trial_candidate.theme.color, self.trial_candidate.theme.accent)
        self.text(self.canvas, "KOSTENLOSER PROBESCHUSS", 148, 180, 22, CYAN, True, family="title")
        sample = f"{self.trial_candidate.theme.title} · Stufe {self.trial_candidate.tier} · nur nächste Frage"
        self.text(self.canvas, sample, 148, 209, 15, WHITE, family="label")
        self.button(pygame.Rect(988, 163, 220, 60),
                    "AUSGEWÄHLT ✓" if self.trial_pending else "GRATIS TESTEN", CYAN,
                    secondary=bool(self.trial_pending), size=18)
        for i, upgrade in enumerate(shop_page(self.page)):
            col, row = i % 3, i // 3
            rect = pygame.Rect(60 + col * 393, 254 + row * 184, 369, 168)
            self.shop_card(upgrade, rect)
        maxpage = (len(UPGRADES) - 1) // PAGE_SIZE
        self.button(pygame.Rect(62, 641, 54, 52), "‹", CYAN, secondary=True, size=27,
                    disabled=self.page == 0)
        self.text(self.canvas, f"SEITE {self.page + 1} / {maxpage + 1}", 169, 666,
                  16, WHITE, True, "center", family="number")
        self.button(pygame.Rect(223, 641, 54, 52), "›", CYAN, secondary=True, size=27,
                    disabled=self.page == maxpage)
        self.text(self.canvas, "Klick: kaufen oder ausrüsten", 307, 665, 14, MUTED, family="label")
        self.button(pygame.Rect(979, 632, 237, 62), "NÄCHSTE FRAGE  ›", CYAN, size=18)
        if self.toast and self.toast_age < 2.4:
            draw_panel(self.canvas, (392, 634, 574, 52), mix(PANEL, GOLD, .12), GOLD, cut=12, border_width=2,
                       glow_color=GOLD)
            self.text(self.canvas, self.toast[:55], 679, 660, 14, WHITE, True, "center", family="label")

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
                   glow_color=frame)
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
