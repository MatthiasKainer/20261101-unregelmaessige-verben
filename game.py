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

from effects import (
    BOSS_MARKS, BOSS_STAGE_FLOOR, PRESSURE, EFFECTS,
    boss_seconds, compute_reward, consume_timer,
    deposit_time_bank, emp_interval, fever_duration, first_miss_action,
    heal_lives, hint_assists, hint_delay, hitbox_scale, is_revenge,
    milestone_crossed, paint_cost, pick_elimination, pressure_level,
    protection, question_seconds, shield_regen_step, streak_after_fail,
    streak_after_success, target_speed_scale,
)
from upgrades import (
    PAGE_SIZE, THEMES, UPGRADES, UPGRADE_BY_ID, Upgrade,
    completion_bonus, tier_ready,
)
from vocabulary import (
    PATTERN_BLURB, VERBS, Verb, MasteryDeck,
    bridge_text, pick_review_verb, sanitize_verb_stats, touch_stat,
)
from weapon_fx import WEAPONS, flight_point, flight_duration
from weapon_visuals import trail as draw_weapon_trail, impact as draw_weapon_impact
from weapon_choreography import draw_flight_choreography

W, H = 1280, 720
FPS = 60
QUESTION_SECONDS = 5.0
STARTING_LIVES = 5

BG = (6, 9, 20)             # #060914
BG_DEEP = (11, 17, 36)       # #0B1124
PANEL = (18, 26, 54)         # #121A36
PANEL_DARK = (11, 18, 39)
WHITE = (238, 243, 255)      # #EEF3FF
MUTED = (151, 163, 201)      # #97A3C9
CYAN = (34, 230, 255)        # #22E6FF
MAGENTA = (255, 46, 136)     # #FF2E88
GOLD = (255, 197, 61)        # #FFC53D
GREEN = (182, 255, 59)       # #B6FF3B
RED = (255, 77, 94)          # #FF4D5E
ORANGE = (255, 122, 26)      # #FF7A1A
BLUE = (61, 139, 255)        # #3D8BFF
VIOLET = (181, 77, 255)      # #B54DFF
AMBER = (255, 176, 32)       # #FFB020
COMMON = (167, 178, 207)     # #A7B2CF
RARITY_COLORS = (COMMON, BLUE, VIOLET, AMBER)
RARITY_NAMES = ("GEWÖHNLICH", "SELTEN", "EPISCH", "LEGENDÄR")
PRESSURE_LABELS = {1: "TRAINING", 2: "BEWEGUNG", 3: "FALLEN", 4: "FINALE"}


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


@dataclass
class BossRound:
    verb: Verb
    mark: int
    stage: int = 0
    retries: int = 0
    failed: bool = False
    parts_ok: int = 0
    time_left: float = 9.0


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
    """Glyph-shaped glow. Additive blit of an opaque RGB copy, never a full-screen slab."""
    for d in range(passes, 0, -1):
        halo = pygame.Surface(img.get_size())
        halo.fill((0, 0, 0))
        tinted = img.copy()
        tinted.fill(color, special_flags=pygame.BLEND_RGB_MULT)
        halo.blit(tinted, (0, 0))
        dim = max(18, 70 - d * 14)
        halo.fill((dim, dim, dim), special_flags=pygame.BLEND_RGB_MULT)
        for dx, dy in ((-d, 0), (d, 0), (0, -d), (0, d)):
            surface.blit(halo, rect.move(dx, dy), special_flags=pygame.BLEND_ADD)


def additive_stamp(surface: pygame.Surface, size: tuple[int, int],
                   pos: tuple[int, int], draw) -> None:
    """Draw into a black RGB buffer and add it. Black contributes nothing."""
    layer = pygame.Surface(size)
    layer.fill((0, 0, 0))
    draw(layer)
    surface.blit(layer, pos, special_flags=pygame.BLEND_ADD)


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
        self.shop_view = "all"
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
        self.shop_view = self.progress["shop_view"]
        self.page = self.progress["owned_page"] if self.shop_view == "owned" else self.progress["shop_page"]
        self.clamp_shop_page()
        self.sound_on = self.progress["sound_on"]
        self.verb_stats = dict(self.progress.get("verb_stats") or {})
        self._boot_combat_defaults()

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
            "label": match(("ChakraPetch-SemiBold.ttf", "ChakraPetch-Regular.ttf"),
                           ("chakra petch", "segoe ui", "arial")),
            "label_bold": match(("ChakraPetch-Bold.ttf", "ChakraPetch-SemiBold.ttf"),
                                ("chakra petch", "segoe ui", "arial")),
            "number": match(("Orbitron-Black.ttf", "Orbitron-Regular.ttf"),
                            ("orbitron", "consolas", "dejavusans", "arial")),
        }

    def font(self, size: int, bold: bool = False, family: str = "label") -> pygame.font.Font:
        key = (family, size, bold)
        if key not in self.fonts:
            source_family = "label_bold" if bold and family == "label" else family
            source = self.font_sources.get(source_family) or self.font_sources.get(family)
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
            t = y / H
            pygame.draw.line(gradient, mix(BG, BG_DEEP, t), (0, y), (W, y))
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
                   "best_mistakes": None, "sound_on": True,
                   "shop_page": 0, "owned_page": 0, "shop_view": "all",
                   "verb_stats": {}}
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
            max_page = max(0, (len(UPGRADES) - 1) // PAGE_SIZE)
            for key in ("shop_page", "owned_page"):
                values[key] = max(0, min(max_page, int(values[key])))
            values["shop_view"] = values["shop_view"] if values["shop_view"] in ("all", "owned") else "all"
            values["verb_stats"] = sanitize_verb_stats(values.get("verb_stats"))
            return values
        except (OSError, ValueError, TypeError, OverflowError):
            return default

    def save_progress(self) -> None:
        current_page = "owned_page" if self.shop_view == "owned" else "shop_page"
        self.progress[current_page] = self.page
        self.progress.update(coins=self.coins, owned=sorted(self.owned), equipped=self.equipped,
                             shop_view=self.shop_view, sound_on=self.sound_on,
                             verb_stats=getattr(self, "verb_stats", {}))
        folder = save_folder()
        try:
            folder.mkdir(parents=True, exist_ok=True)
            temp = folder / "progress.json.tmp"
            temp.write_text(json.dumps(self.progress, ensure_ascii=False, indent=2), encoding="utf-8")
            os.replace(temp, folder / "progress.json")
        except OSError:
            pass  # Don't break the game on protected PCs.

    def _boot_combat_defaults(self) -> None:
        """Per-run combat state. Safe to call before the first question."""
        self.mode = "normal"
        self.time_budget = QUESTION_SECONDS
        self.slot_x = [330.0, 640.0, 950.0]
        self.target_w = 240
        self.motion = 0.0
        self.eliminated: set[int] = set()
        self.elim_style = ""
        self.hint_visible = False
        self.assisted = False
        self.assisted_shot = False
        self.rebound_used = False
        self.life_note = ""
        self.paint_used = False
        self.center_dist = 999.0
        self.shot_age = 0.0
        self.swapped = False
        self.do_swap = False
        self.swap_pair = (0, 2)
        self.pressure_band = 1
        self.pressure_suppressed = False
        self.banner = ""
        self.banner_age = 99.0
        self.prompt = ""
        self.max_lives = STARTING_LIVES
        self.help_uses: dict[str, int] = {}
        self.time_bank = 0.0
        self.fever_left = 0
        self.fever_active = False
        self.charges = 0
        self.guard_key: str | None = None
        self.guard_tier = 0
        self.shield = 0
        self.shield_max = 0
        self.shield_progress = 0
        self.shield_regen = 8
        self.shield_inited = False
        self.emp_count = 0
        self.boss: BossRound | None = None
        self.boss_queued: int | None = None
        self.bosses_done: set[int] = set()
        self.bonus_queued: Verb | None = None
        if not hasattr(self, "verb_stats") or self.verb_stats is None:
            self.verb_stats = {}

    def active_fx(self):
        upgrade = getattr(self, "active_round", None)
        if not upgrade:
            return None, 1
        return EFFECTS.get(upgrade.theme.projectile), upgrade.tier

    def _equip_active(self) -> None:
        upgrade_id = self.trial_pending or self.equipped
        self.active_round = UPGRADE_BY_ID.get(upgrade_id) if upgrade_id else None
        self.trial_pending = None

    def _layout_targets(self, count: int) -> None:
        if count >= 4:
            self.slot_x = [176.0, 492.0, 808.0, 1104.0]
            self.target_w = 196
        else:
            self.slot_x = [330.0, 640.0, 950.0]
            self.target_w = 240

    def _sync_resources(self, fx, tier: int) -> None:
        if fx and fx.key in ("rebound", "quench"):
            if self.guard_key != fx.key:
                self.charges = fx.charges_at(tier)
                self.guard_key = fx.key
                self.guard_tier = tier
            elif tier > self.guard_tier:
                self.charges += max(0, fx.charges_at(tier) - fx.charges_at(self.guard_tier))
                self.guard_tier = tier
        if fx and fx.key == "shield":
            self.shield_max = int(fx.value_b(tier))
            self.shield_regen = shield_regen_step(fx, tier)
            if not self.shield_inited:
                self.shield = self.shield_max
                self.shield_inited = True
            self.shield = min(self.shield_max, self.shield)
        if fx and fx.key == "heal":
            self.max_lives = int(fx.value_b(tier))
        elif self.max_lives != STARTING_LIVES:
            self.max_lives = STARTING_LIVES
            self.lives = min(self.lives, self.max_lives)

    def _maybe_hint(self) -> None:
        if self.hint_visible or self.mode == "bonus":
            return
        if self.help_uses.get(self.verb.infinitive, 0) >= 2:
            return
        fx, tier = self.active_fx()
        delay = hint_delay(fx, tier, boss=self.mode == "boss")
        if delay is None or self.question_age < delay:
            return
        self.hint_visible = True
        if fx and fx.key == "fifty_fifty":
            try:
                idx = pick_elimination(self.correct_index, len(self.options), self.rng, self.eliminated)
            except RuntimeError:
                return
            self.eliminated.add(idx)
            self.elim_style = "ink"

    def _drop_fourth(self) -> None:
        if len(self.options) < 4 or self.mode != "normal":
            self.motion = 0.0
            return
        idx = None
        for i, word in enumerate(self.options):
            if i != self.correct_index and word == self.verb.distractor_c:
                idx = i
                break
        if idx is None:
            wrong = [i for i in range(len(self.options)) if i != self.correct_index]
            idx = wrong[-1]
        self.options = tuple(word for i, word in enumerate(self.options) if i != idx)
        self.correct_index = self.options.index(self.verb.simple_past)
        self.eliminated = set()
        self.motion = 0.0
        self.do_swap = False
        self._layout_targets(3)

    def _begin_round(self) -> None:
        if self.mode == "normal":
            self._equip_active()
        fx, tier = self.active_fx()
        self.fever_active = False
        if self.mode == "normal" and self.fever_left > 0:
            self.fever_active = True
            self.fever_left -= 1
        self._sync_resources(fx, tier)
        suppressed = False
        if fx and fx.key == "emp" and self.mode == "normal":
            interval = emp_interval(fx, tier)
            self.emp_count += 1
            if self.emp_count >= interval:
                suppressed = True
                self.emp_count = 0
        self.pressure_suppressed = suppressed
        learned = self.correct_count
        band = 1 if suppressed or self.mode != "normal" else pressure_level(learned)
        if self.mode == "normal" and band != getattr(self, "pressure_band", 1):
            self.banner = f"LEVEL {band}: {PRESSURE_LABELS[band]}!"
            self.banner_age = 0.0
            self.pressure_band = band
        elif self.mode == "normal":
            self.pressure_band = band
        spec = PRESSURE[1 if self.mode != "normal" else band]
        self.chosen_index = None
        self.question_age = 0.0
        self.shake = 0.0
        self.flight_trail.clear()
        self.eliminated = set()
        self.elim_style = ""
        self.hint_visible = False
        self.assisted = False
        self.assisted_shot = False
        self.rebound_used = False
        self.life_note = ""
        self.paint_used = False
        self.center_dist = 999.0
        self.shot_age = 0.0
        self.swapped = False
        self.outcome = ""
        self.winnings = 0
        if self.mode == "bonus":
            self.options = self.verb.options(self.rng, 3)
            self.correct_index = self.options.index(self.verb.simple_past)
            self.time_left = 3.0
            self.time_budget = 3.0
            self.motion = 0.0
            self.do_swap = False
            self.prompt = "AUFFRISCHUNG"
            self._layout_targets(3)
        elif self.mode == "boss" and self.boss is not None:
            stage = "past" if self.boss.stage == 0 else "participle"
            self.options = self.verb.boss_options(self.rng, stage)
            answer = self.verb.simple_past if stage == "past" else self.verb.past_participle
            self.correct_index = self.options.index(answer)
            if self.boss.stage == 0:
                self.boss.time_left = boss_seconds(fx, tier)
            else:
                self.boss.time_left = max(BOSS_STAGE_FLOOR, self.boss.time_left)
            self.time_left = self.boss.time_left
            self.time_budget = max(0.1, self.time_left)
            self.motion = 0.0
            self.do_swap = False
            self.prompt = "BOSS · SIMPLE PAST" if stage == "past" else "BOSS · PARTIZIP"
            self._layout_targets(4)
        else:
            count = spec["targets"]
            self.options = self.verb.options(self.rng, count)
            self.correct_index = self.options.index(self.verb.simple_past)
            self.time_left = question_seconds(
                learned, fx, tier, self.streak, self.fever_active, suppressed)
            self.time_budget = max(0.1, self.time_left)
            self.motion = spec["speed"] * target_speed_scale(fx, tier)
            self.do_swap = bool(spec["swap"]) and not suppressed
            self.prompt = ""
            self._layout_targets(count)
            if self.do_swap and count >= 2:
                idxs = list(range(count))
                self.rng.shuffle(idxs)
                self.swap_pair = (idxs[0], idxs[1])
        self.phase = "play"
        self.questions = getattr(self, "questions", 0) + 1
        self._maybe_hint()
        self.sound("pop")

    def new_run(self) -> None:
        self._boot_combat_defaults()
        self.lives = STARTING_LIVES
        self.max_lives = STARTING_LIVES
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
        if not hasattr(self, "verb_stats") or self.verb_stats is None:
            self.verb_stats = {}
        self.deck = MasteryDeck(self.rng, self.verb_stats)
        self.progress["runs"] = self.progress.get("runs", 0) + 1
        self.save_progress()
        self.start_question()

    def start_question(self) -> None:
        if self.deck.complete:
            self.end_run()
            return
        self.mode = "normal"
        self.boss = None
        self.verb = self.deck.next()
        self._begin_round()

    def start_bonus(self, verb: Verb) -> None:
        self.mode = "bonus"
        self.verb = verb
        self._begin_round()

    def open_boss(self, mark: int) -> None:
        self.bosses_done.add(mark)
        self.boss_queued = None
        self._equip_active()
        fx, tier = self.active_fx()
        verb = pick_review_verb(
            self.verb_stats, self.deck.missed, self.deck.mastered, self.rng, only_mastered=False)
        assert verb is not None
        retries = fx.charges_at(tier) if fx and fx.key == "penalty" else 0
        self.boss = BossRound(verb=verb, mark=mark, retries=retries)
        self.mode = "boss"
        self.verb = verb
        self._begin_round()

    def shop_items(self) -> tuple[Upgrade, ...]:
        """Sorted by level, with a separate view of everything already owned."""
        if self.shop_view == "owned":
            return tuple(upgrade for upgrade in UPGRADES if upgrade.id in self.owned)
        return UPGRADES

    def shop_page_items(self) -> tuple[Upgrade, ...]:
        items = self.shop_items()
        return items[self.page * PAGE_SIZE:(self.page + 1) * PAGE_SIZE]

    def shop_last_page(self) -> int:
        return max(0, (len(self.shop_items()) - 1) // PAGE_SIZE)

    def clamp_shop_page(self) -> None:
        self.page = max(0, min(self.page, self.shop_last_page()))

    def set_shop_view(self, view: str) -> None:
        if view not in ("all", "owned"):
            raise ValueError("shop view must be 'all' or 'owned'")
        self.progress["owned_page" if self.shop_view == "owned" else "shop_page"] = self.page
        self.shop_view = view
        self.page = self.progress.get("owned_page" if view == "owned" else "shop_page", 0)
        self.clamp_shop_page()
        self.save_progress()
        self.sound("trial")

    def change_shop_page(self, delta: int) -> None:
        self.page += delta
        self.clamp_shop_page()
        self.save_progress()
        self.sound("trial")

    def start_shop(self) -> None:
        if self.deck.complete or self.lives <= 0:
            self.end_run()
            return
        self.phase = "shop"
        # Do NOT jump to an affordable item: players return to their last page.
        # New save data begins on page 1 (internal index 0).
        self.clamp_shop_page()
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
            assisted = getattr(self.deck, "assisted_count", 0)
            self.bonus_awarded = completion_bonus(self.deck.mistakes, assisted)
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
        if target is not None and target in self.eliminated:
            target = None
        self.chosen_index = target
        self.outcome = "timeout" if timeout else "correct" if target == self.correct_index else "wrong"
        self.shot_age = self.question_age
        fx, _tier = self.active_fx()
        stage = None
        if self.mode == "boss" and self.boss is not None:
            stage = "past" if self.boss.stage == 0 else "participle"
        self.assisted = bool(self.hint_visible) and hint_assists(
            fx, boss=self.mode == "boss", boss_stage=stage)
        self.winnings = 0
        kind = self.active_round.theme.projectile if self.active_round else "chalk"
        tier = self.active_round.tier if self.active_round else 1
        self.flight_seconds = flight_duration(kind, tier)
        # On click, the reaction timer is frozen. Flight/impact/reveal never
        # decrement this value; a 2.3 second cinematic rocket remains fair.
        self.shot_time_left = self.time_left
        self.flight_time = 0.0
        # Launch from the stage, not underneath the bottom HUD.
        self.shot_from = (W / 2, 588)
        self.shot_to = clicked_at or (640, 472)
        self.flight_trail = []
        self.phase = "flight"
        self.sound(WEAPONS[kind].pitch if not timeout else "miss")
        if timeout:
            self.flight_seconds = 0.001

    def _payout(self, fx, tier: int, assisted: bool, revenge: bool, old_streak: int) -> int:
        radius = fx.value(tier) if fx and fx.key == "bullseye" else -1.0
        center = self.center_dist <= radius
        express = bool(fx and fx.key == "express" and self.shot_age <= fx.value_b(tier))
        milestone = milestone_crossed(old_streak, self.streak, fx, tier)
        return compute_reward(
            self.streak, self.time_left, fx=fx, tier=tier, assisted=assisted,
            fever=self.fever_active, revenge=revenge and not assisted,
            express=express, center_hit=center, milestone=milestone,
        )

    def _apply_life_loss(self, fx) -> None:
        kind = protection(
            self.outcome,
            fx.key if fx else None,
            self.shield if fx and fx.key == "shield" else 0,
            self.charges if fx and fx.key == "quench" else 0,
        )
        if kind == "shield":
            self.shield = max(0, self.shield - 1)
            self.life_note = "shield"
            return
        if kind == "quench":
            self.charges = max(0, self.charges - 1)
            self.life_note = "quench"
            return
        self.lives = max(0, self.lives - 1)

    def _on_streak(self, old: int, fx, tier: int) -> None:
        if fx and fx.key == "heal":
            self.max_lives = int(fx.value_b(tier))
            self.lives = heal_lives(old, self.streak, fx, tier, self.lives)
        if fx and fx.key == "shield":
            step = max(1, self.shield_regen)
            self.shield_progress += max(0, self.streak - old)
            while self.shield_progress >= step and self.shield < self.shield_max:
                self.shield += 1
                self.shield_progress -= step

    def _queue_followups(self, fx, tier: int) -> None:
        learned = self.deck.completed_count
        if learned in BOSS_MARKS and learned not in self.bosses_done:
            self.boss_queued = learned
            return
        if fx and fx.key == "chain_refresh" and self.deck.mastered and self.rng.random() < fx.value(tier):
            verb = pick_review_verb(
                self.verb_stats, self.deck.missed, self.deck.mastered, self.rng, only_mastered=True)
            if verb is not None:
                self.bonus_queued = verb

    def _resolve_normal(self, success: bool, fx, tier: int) -> None:
        name = self.verb.infinitive
        run_index = int(self.progress.get("runs", 0))
        revenge = is_revenge(name, self.deck.missed, self.verb_stats)
        if self.rebound_used:
            # Protection saves the life only if the second shot is right.
            # The verb still counts as not-yet-learned.
            self.deck.record(False)
            touch_stat(self.verb_stats, name, outcome="wrong", run_index=run_index)
            self.winnings = 0
            self.streak = 0
            if not success:
                self._apply_life_loss(fx)
            self.life_note = self.life_note or "rebound"
            self.correct_count = self.deck.completed_count
            self.sound("hit" if success else "miss")
            at = self.shot_to if success or self.outcome != "timeout" else (640, 430)
            self.spawn_burst(at, success)
            self.save_progress()
            return
        self.deck.record(success, assisted=self.assisted_shot)
        if success and self.assisted_shot:
            touch_stat(self.verb_stats, name, outcome="assisted", run_index=run_index)
            self.help_uses[name] = self.help_uses.get(name, 0) + 1
            self.winnings = self._payout(fx, tier, True, False, self.streak)
            self.coins += self.winnings
            self.sound("hit")
            self.spawn_burst(self.shot_to, True)
        elif success:
            touch_stat(self.verb_stats, name, outcome="clean", run_index=run_index)
            old = self.streak
            self.streak = streak_after_success(old, fx, tier, self.shot_age, False)
            self._on_streak(old, fx, tier)
            self.winnings = self._payout(fx, tier, False, revenge, old)
            self.coins += self.winnings
            self.time_bank = deposit_time_bank(self.time_bank, self.time_left, fx, tier)
            fresh = fever_duration(self.streak, fx, tier)
            if fresh:
                self.fever_left = fresh
            self._queue_followups(fx, tier)
            self.sound("hit")
            self.spawn_burst(self.shot_to, True)
        else:
            touch_stat(self.verb_stats, name, outcome="wrong", run_index=run_index)
            self.winnings = 0
            self._apply_life_loss(fx)
            self.streak = streak_after_fail(self.streak, fx, tier)
            self.shield_progress = 0
            self.sound("miss")
            at = self.shot_to if self.outcome != "timeout" else (640, 430)
            self.spawn_burst(at, False)
        self.correct_count = self.deck.completed_count
        self.save_progress()

    def _resolve_bonus(self, success: bool, fx, tier: int) -> None:
        name = self.verb.infinitive
        run_index = int(self.progress.get("runs", 0))
        if success:
            amount = int(round(fx.value_b(tier))) if fx and fx.key == "chain_refresh" else 40
            self.winnings = amount
            self.coins += amount
            touch_stat(self.verb_stats, name, outcome="clean", run_index=run_index)
            self.sound("hit")
            self.spawn_burst(self.shot_to, True)
        else:
            self.winnings = 0
            self.deck.unmaster(self.verb)
            touch_stat(self.verb_stats, name, outcome="wrong", run_index=run_index)
            self.life_note = "bonus"
            self.sound("miss")
            at = self.shot_to if self.outcome != "timeout" else (640, 430)
            self.spawn_burst(at, False)
        self.correct_count = self.deck.completed_count
        self.save_progress()

    def _resolve_boss_stage(self, success: bool) -> None:
        assert self.boss is not None
        self.boss.time_left = self.time_left
        if success:
            self.boss.parts_ok += 1
            if self.assisted_shot:
                name = self.boss.verb.infinitive
                self.help_uses[name] = self.help_uses.get(name, 0) + 1
            self.sound("hit")
            self.spawn_burst(self.shot_to, True)
        else:
            self.boss.failed = True
            self.sound("miss")
            at = self.shot_to if self.outcome != "timeout" else (640, 430)
            self.spawn_burst(at, False)
        if self.boss.stage >= 1:
            fx, tier = self.active_fx()
            clear = self.boss.parts_ok >= 2
            self.winnings = compute_reward(
                0, 0, fx=fx, tier=tier, boss=True, boss_clear=clear,
                assisted=bool(self.assisted_shot))
        else:
            self.winnings = 0

    def finish_boss(self) -> None:
        boss = self.boss
        if boss is None:
            return
        fx, tier = self.active_fx()
        clear = boss.parts_ok >= 2
        assisted = bool(self.assisted_shot and boss.stage >= 1)
        self.winnings = compute_reward(
            0, 0, fx=fx, tier=tier, boss=True, boss_clear=clear, assisted=assisted)
        if clear:
            self.coins += self.winnings
            self.sound("coins")
        else:
            self.winnings = 0
            if self.outcome != "timeout":
                self.outcome = "wrong"
            self._apply_life_loss(fx)
            self.streak = streak_after_fail(self.streak, fx, tier)
            self.deck.unmaster(boss.verb)
            touch_stat(self.verb_stats, boss.verb.infinitive, outcome="wrong",
                       run_index=int(self.progress.get("runs", 0)))
        self.correct_count = self.deck.completed_count
        self.boss = None
        self.mode = "normal"
        self.save_progress()
        if self.lives <= 0 or self.deck.complete:
            self.end_run()
        else:
            self.start_shop()

    def after_reveal(self) -> None:
        if self.lives <= 0:
            self.end_run()
            return
        if self.mode == "boss" and self.boss is not None and self.boss.stage == 0:
            self.boss.stage = 1
            self.verb = self.boss.verb
            self._begin_round()
            return
        if self.mode == "boss" and self.boss is not None:
            self.finish_boss()
            return
        if self.boss_queued:
            mark = self.boss_queued
            self.boss_queued = None
            self.open_boss(mark)
            return
        if self.bonus_queued is not None:
            verb = self.bonus_queued
            self.bonus_queued = None
            self.start_bonus(verb)
            return
        if self.deck.complete:
            self.end_run()
            return
        self.start_shop()

    def resolve(self) -> None:
        fx, tier = self.active_fx()
        retries = self.boss.retries if self.mode == "boss" and self.boss is not None else 0
        action = first_miss_action(
            self.outcome, fx.key if fx else None, self.charges, self.rebound_used, retries)
        if action == "rebound":
            self.charges -= 1
            self.rebound_used = True
            if self.chosen_index is not None:
                self.eliminated.add(self.chosen_index)
                self.elim_style = "down"
            self.streak = 0
            self.shield_progress = 0
            self.time_left = max(0.45, self.time_left + (fx.value(tier) if fx else 0.0))
            self.phase = "play"
            self.outcome = ""
            self.sound("miss")
            self.flash_message("ABGEPRALLT – NOCH EIN SCHUSS")
            return
        if action == "penalty" and self.boss is not None:
            self.boss.retries -= 1
            self.time_left = max(0.45, self.time_left + (fx.value(tier) if fx else 1.0))
            self.boss.time_left = self.time_left
            self.phase = "play"
            self.eliminated.clear()
            self.hint_visible = False
            stage = "past" if self.boss.stage == 0 else "participle"
            self.options = self.verb.boss_options(self.rng, stage)
            answer = self.verb.simple_past if stage == "past" else self.verb.past_participle
            self.correct_index = self.options.index(answer)
            self.sound("miss")
            self.flash_message("ELFMETER")
            return
        self.phase = "impact"
        self.impact_elapsed = 0.0
        self.reveal_elapsed = 0.0
        success = self.outcome == "correct"
        self.assisted_shot = bool(success and self.assisted)
        if self.mode == "boss":
            self._resolve_boss_stage(success)
            return
        if self.mode == "bonus":
            self._resolve_bonus(success, fx, tier)
            return
        self._resolve_normal(success, fx, tier)

    def use_active(self) -> None:
        """Right click: paint bomb, or a charged plasma EMP."""
        if self.phase != "play":
            return
        fx, tier = self.active_fx()
        if fx is None:
            return
        if fx.key == "paint_bomb":
            if self.paint_used:
                self.flash_message("FARBOMBE SCHON BENUTZT")
                return
            cost = paint_cost(fx, tier, self.streak)
            if cost is None:
                return
            if self.coins < cost:
                self.flash_message(f"DIR FEHLEN {cost - self.coins} MÜNZEN")
                return
            try:
                idx = pick_elimination(self.correct_index, len(self.options), self.rng, self.eliminated)
            except RuntimeError:
                return
            self.coins -= cost
            self.eliminated.add(idx)
            self.elim_style = "paint"
            self.paint_used = True
            self.hint_visible = True
            self.sound("trial")
            self.flash_message("FARBOMBE" if cost == 0 else f"FARBOMBE −{cost}")
            self.save_progress()
        elif fx.key == "emp" and self.mode == "normal" and not self.pressure_suppressed:
            interval = emp_interval(fx, tier)
            if self.emp_count < max(1, interval - 1):
                self.flash_message("EMP LÄDT NOCH")
                return
            self.pressure_suppressed = True
            self.emp_count = 0
            self.motion = 0.0
            self.do_swap = False
            self._drop_fourth()
            self.flash_message("EMP: DRUCK AUS")

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
        if upgrade.id not in self.owned and not tier_ready(upgrade.theme_index, upgrade.tier, self.owned):
            self.sound("miss")
            self.flash_message(f"ZUERST STUFE {upgrade.tier - 1} DIESER WAFFE")
            return
        if upgrade.id in self.owned:
            self.equipped = upgrade.id
            self.trial_pending = None  # selecting a purchased weapon beats a preview shot
            self.sound("trial")
            self.flash_message("AUSGERÜSTET: " + upgrade.theme.title)
        elif self.coins >= upgrade.cost:
            self.coins -= upgrade.cost
            self.owned.add(upgrade.id)
            self.equipped = upgrade.id
            self.trial_pending = None
            self.sound("buy")
            self.flash_message("GEKAUFT & AUSGERÜSTET: " + upgrade.theme.title)
        else:
            self.sound("miss")
            self.flash_message(f"DIR FEHLEN {upgrade.cost - self.coins} MÜNZEN")
        self.clamp_shop_page()
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

    def target_x(self, idx: int) -> float:
        slots = getattr(self, "slot_x", None) or [330.0, 640.0, 950.0]
        if idx >= len(slots):
            slots = [330.0, 640.0, 950.0]
        base = float(slots[idx])
        motion = getattr(self, "motion", 0.0) or 0.0
        if motion <= 0 or self.phase not in ("play", "flight", "impact", "reveal"):
            return base
        amp = 70.0 if len(self.options) <= 3 else 52.0
        return base + math.sin(self.question_age * (motion / amp) + idx * 1.7) * amp

    def target_rect(self, idx: int) -> pygame.Rect:
        x = self.target_x(idx)
        width = int(getattr(self, "target_w", 240))
        board_h = 264 if width >= 220 else 220
        height = max(1, int(board_h * max(.02, self.popup_progress())))
        rect = pygame.Rect(0, 0, width, height)
        rect.midbottom = (int(round(x)), 529 + int(self.target_float(idx)))
        fx, tier = self.active_fx()
        scale = hitbox_scale(fx, tier)
        if scale != 1.0:
            grow_w = int(rect.w * (scale - 1))
            grow_h = int(rect.h * (scale - 1))
            rect = rect.inflate(grow_w, grow_h)
        return rect

    def bullseye_center(self, idx: int) -> tuple[float, float]:
        x = self.target_x(idx)
        popup = max(.01, self.popup_progress())
        width = int(getattr(self, "target_w", 240))
        board_h = 264 if width >= 220 else 220
        footer = 529 + self.target_float(idx)
        cy = footer - board_h * popup + 66 * (board_h / 264.0) * popup
        return x, cy


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
            for i in range(len(self.options)):
                if i in self.eliminated:
                    continue
                if self.target_rect(i).collidepoint(x, y) and self.question_age >= .17:
                    hit = i
                    break
            if hit is not None:
                cx, cy = self.bullseye_center(hit)
                self.center_dist = math.hypot(x - cx, y - cy)
            else:
                self.center_dist = 999.0
            self.register_shot(hit, (x, y))
        elif self.phase == "shop":
            if pygame.Rect(1034, 158, 198, 56).collidepoint(x, y):
                self.trial()
            elif pygame.Rect(994, 638, 236, 51).collidepoint(x, y):
                self.sound("trial")
                self.start_question()
            elif pygame.Rect(46, 645, 52, 46).collidepoint(x, y):
                self.change_shop_page(-1)
            elif pygame.Rect(200, 645, 52, 46).collidepoint(x, y):
                self.change_shop_page(1)
            elif pygame.Rect(408, 645, 134, 46).collidepoint(x, y):
                self.set_shop_view("all")
            elif pygame.Rect(552, 645, 194, 46).collidepoint(x, y):
                self.set_shop_view("owned")
            else:
                for i, upgrade in enumerate(self.shop_page_items()):
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
            self.banner_age = getattr(self, "banner_age", 99.0) + dt
            fx, tier = self.active_fx()
            step = consume_timer(fx, tier, self.question_age, self.time_left, dt)
            self.time_left = max(0.0, self.time_left - step)
            self._maybe_hint()
            if self.do_swap and not self.swapped and self.question_age >= self.time_budget * 0.5:
                self.swapped = True
                i, j = self.swap_pair
                if i < len(self.slot_x) and j < len(self.slot_x):
                    self.slot_x[i], self.slot_x[j] = self.slot_x[j], self.slot_x[i]
            if self.time_left <= 0:
                if self.time_bank > 0.05:
                    self.time_left = self.time_bank
                    self.time_budget = max(self.time_budget, self.time_left)
                    self.time_bank = 0.0
                    self.flash_message("ZEITBANK")
                else:
                    self.register_shot(None, timeout=True)
        elif self.phase == "flight":
            # No time_left subtraction after a click; projectile choreography is free.
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
                self.after_reveal()
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
        # Faint square grid over the navy gradient. Dark enough to stay behind text.
        grid = (14, 22, 40)
        for x in range(0, W + 1, 48):
            pygame.draw.line(self.canvas, grid, (x, 0), (x, H), 1)
        for y in range(0, H, 48):
            pygame.draw.line(self.canvas, grid, (0, y), (W, y), 1)
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
        draw_panel(self.canvas, (1196, 26, 52, 52), PANEL, CYAN,
                   cut=9, border_width=1, shadow_offset=1)
        pygame.draw.line(self.canvas, CYAN, (1225, 38), (1225, 59), 3)
        pygame.draw.line(self.canvas, CYAN, (1225, 38), (1234, 35), 3)
        pygame.draw.ellipse(self.canvas, CYAN, (1215, 55, 10, 7))
        if not self.sound_on:
            pygame.draw.line(self.canvas, RED, (1212, 39), (1238, 66), 2)

    def _hud_effect(self) -> str:
        fx, tier = self.active_fx()
        if fx is None:
            return "AUSGERÜSTET" if getattr(self, "active_round", None) else "STANDARD"
        line = fx.text(tier)
        if fx.key == "shield":
            line = f"{line} · {self.shield}"
        elif fx.key == "time_bank" and self.time_bank > 0.05:
            line = f"Zeitbank {self.time_bank:.1f} s"
        elif self.fever_active:
            line = "FIEBER · doppelte Münzen"
        return line

    def _hint_line(self) -> str:
        fx, tier = self.active_fx()
        if not self.hint_visible or fx is None:
            return ""
        verb = self.verb
        if fx.key == "hint_sentence":
            return verb.sentence
        if fx.key == "cheat_sheet":
            return verb.german
        if fx.key == "pattern_bridge":
            mastered = self.deck.mastered if getattr(self, "deck", None) else set()
            return bridge_text(verb, mastered, tier)
        if fx.key == "prism":
            return PATTERN_BLURB.get(verb.pattern, verb.pattern)
        if fx.key == "fifty_fifty":
            return "Eine falsche Scheibe ist übermalt"
        if fx.key == "paint_bomb":
            return "Farbbombe: eine Falle ist grau"
        return fx.text(tier)

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
        hearts = max(STARTING_LIVES, getattr(self, "max_lives", STARTING_LIVES))
        gap = 22 if hearts > 5 else 27
        for i in range(hearts):
            color = RED if i < self.lives else (72, 81, 101)
            draw_symbol(self.canvas, 118 + i * gap, 659, 9 if hearts > 5 else 10,
                        "heart", color)
        if getattr(self, "shield", 0) > 0:
            for s in range(self.shield):
                draw_symbol(self.canvas, 248 - s * 16, 642, 7, "bubble", (170, 220, 255), CYAN)
        self.text(self.canvas, "SERIE", 322, 653, 12, MUTED,
                  family="label")
        self.text(self.canvas, f"COMBO x{max(1, self.streak)}", 408, 671,
                  19, ORANGE, True, "center", family="title", max_width=180)
        self.text(self.canvas, "GELERNT", 554, 648, 13, MUTED,
                  family="label")
        self.text(self.canvas, f"{self.correct_count}/{len(VERBS)}", 706, 648,
                  19, CYAN, True, "right", family="number", max_width=100)
        rounded(self.canvas, (554, 675, 150, 7), (29, 38, 69), radius=3)
        if self.correct_count:
            rounded(self.canvas, (554, 675, max(2, int(150 * self.correct_count / len(VERBS))), 7),
                    CYAN, radius=3)
        self.text(self.canvas, "FEHLER", 754, 651, 12, MUTED,
                  family="label")
        self.text(self.canvas, str(self.deck.mistakes), 867, 651, 23,
                  GREEN if self.deck.mistakes == 0 else RED,
                  True, "right", family="number")
        hud = self._hud_effect()
        self.text(self.canvas, hud, 919, 645, 12, CYAN if self.active_round else MUTED,
                  family="label", max_width=300)
        if self.active_round:
            theme = self.active_round.theme
            draw_symbol(self.canvas, 932, 669, 16, theme.projectile,
                        theme.color, theme.accent)
            gear = theme.title.upper()
            self.text(self.canvas, gear, 959, 668, 18, WHITE,
                      True, family="title", max_width=200)
            self.text(self.canvas, f"LV {self.active_round.tier}", 1223, 668,
                      14, CYAN, True, "right", family="number", max_width=55)
        else:
            self.text(self.canvas, "STANDARD", 920, 668, 18, WHITE,
                      True, family="title")

    def draw_dummy(self, index: int, title: str, popup: float = 1.0,
                   state: str = "neutral") -> None:
        xpos = self.target_x(index)
        float_y = self.target_float(index)
        if state == "eliminated":
            state_color = (90, 98, 120)
        elif state == "correct":
            state_color = GREEN
        elif state == "wrong":
            state_color = RED
        else:
            state_color = CYAN
        w, h = 240, 264
        unit = pygame.Surface((w, h), pygame.SRCALPHA)
        center = (w // 2, 66)
        # Floating holographic concentric targets with light outlines only.
        for rad, thickness in ((62, 1), (48, 2), (35, 2), (18, 2)):
            pygame.draw.circle(unit, state_color, center, rad, thickness)
        pygame.draw.circle(unit, state_color, center, 9)
        if state == "correct":
            pygame.draw.circle(unit, (*GREEN, 80), center, 58)
            pygame.draw.circle(unit, GREEN, center, 62, 4)
        for dx in (-78, 78):
            bx = center[0] + dx
            delta = 10 if dx < 0 else -10
            pygame.draw.polygon(unit, state_color,
                                [(bx, 66), (bx + delta, 56), (bx + delta, 76)], 2)
        pygame.draw.line(unit, state_color, (w // 2, 5), (w // 2, 0), 3)
        pygame.draw.line(unit, state_color, (w // 2, 128), (w // 2, 150), 2)
        pygame.draw.rect(unit, PANEL_DARK, (77, 148, 26, 24))
        pygame.draw.rect(unit, state_color, (77, 148, 26, 24), 1)
        self.text(unit, str(index + 1), 90, 160, 12, WHITE, True,
                  "center", family="number")
        self.text(unit, f"ZIEL {index + 1}", 111, 160,
                  14, state_color, False, family="label")
        plate = pygame.Rect(0, 174, 240, 80)
        fill = mix(PANEL, state_color,
                   .62 if state == "correct" else .22 if state == "wrong" else 0.015)
        draw_panel(unit, plate, fill, state_color, cut=14,
                   border_width=2 if state == "correct" else 1,
                   shadow_offset=0)
        ink = (150, 158, 176) if state == "eliminated" else WHITE
        self.text(unit, title, w // 2, 216,
                  36 if len(title) < 7 else 28, ink, True, "center",
                  family="title", max_width=211)
        if state == "eliminated":
            blot = (40, 70, 150) if getattr(self, "elim_style", "") == "ink" else (70, 74, 88)
            pygame.draw.circle(unit, blot, (w // 2, 66), 58)
            pygame.draw.circle(unit, (20, 26, 40), (w // 2, 66), 58, 3)
            if getattr(self, "elim_style", "") == "down":
                pygame.draw.line(unit, RED, (40, 200), (200, 190), 4)
        # Target extends upward from a consistent stand, with sinusoidal bobbing.
        yfactor = max(.01, popup)
        if state == "eliminated" and getattr(self, "elim_style", "") == "down":
            yfactor *= 0.22
        draw_w = int(getattr(self, "target_w", w))
        draw_h = max(2, int(h * (draw_w / w) * yfactor))
        unit = pygame.transform.smoothscale(unit, (max(2, draw_w), draw_h))
        footer = 529 + int(float_y)
        shadow = pygame.Surface((160, 18), pygame.SRCALPHA)
        pygame.draw.ellipse(shadow, (*state_color, 19), (0, 1, 160, 13))
        self.canvas.blit(shadow, (xpos - 80, 546))
        self.canvas.blit(unit, unit.get_rect(midbottom=(xpos, footer)))
        if state == "correct":
            glow_circle(self.canvas, (xpos, 330 + int(float_y)), 36, GREEN, 1, 3)

    def _question_caption(self) -> tuple[str, str]:
        mode = getattr(self, "mode", "normal")
        boss = getattr(self, "boss", None)
        if mode == "boss" and boss is not None and boss.stage >= 1:
            shown = self.verb.simple_past.upper()
            if len(shown) > 16:
                shown = shown[:16]
            return "BOSS-RUNDE  ·  PARTIZIP", f"{shown}  →  ?"
        if mode == "boss":
            return "BOSS-RUNDE  ·  SIMPLE PAST", self.verb.infinitive.upper()
        if mode == "bonus":
            return "AUFFRISCHUNG  ·  SCHON GELERNT", self.verb.infinitive.upper()
        return "WIE LAUTET DAS SIMPLE PAST VON ...?", self.verb.infinitive.upper()

    def _draw_time_segments(self) -> None:
        segments = 18
        gap = 6
        total = 420
        x0, y = 410, 218
        seg_w = (total - gap * (segments - 1)) / segments
        budget = max(0.1, getattr(self, "time_budget", QUESTION_SECONDS))
        ratio = max(0.0, min(1.0, self.time_left / budget))
        filled = int(round(ratio * segments))

        def bar_glow(layer: pygame.Surface) -> None:
            pygame.draw.rect(layer, (20, 70, 80), pygame.Rect(8, 6, total, 14), border_radius=4)
        additive_stamp(self.canvas, (total + 16, 28), (x0 - 8, y - 8), bar_glow)
        for i in range(segments):
            rect = pygame.Rect(int(x0 + i * (seg_w + gap)), y, max(4, int(seg_w)), 13)
            if i < filled:
                t = i / max(1, segments - 1)
                col = mix(CYAN, GOLD, t * 0.85)
                rounded(self.canvas, rect, col, radius=2)
            else:
                rounded(self.canvas, rect, (32, 44, 70), radius=2)

    def draw_hit_flourish(self) -> None:
        if self.phase != "impact" or self.outcome != "correct":
            return
        cx, cy = self.bullseye_center(self.correct_index)
        side = 300
        def paint(layer: pygame.Surface) -> None:
            mid = side // 2
            for i in range(16):
                angle = -math.pi / 2 + i * math.tau / 16 + self.impact_elapsed * 0.6
                inner = 34
                outer = 86 + (i % 4) * 16
                col = GREEN if i % 2 == 0 else (90, 210, 255)
                pygame.draw.line(
                    layer, col,
                    point(mid + math.cos(angle) * inner, mid + math.sin(angle) * inner),
                    point(mid + math.cos(angle) * outer, mid + math.sin(angle) * outer), 2)
            drop = random.Random(5)
            for i in range(12):
                angle = drop.random() * math.tau
                dist = 36 + drop.random() * 62
                pygame.draw.circle(
                    layer, (70, 180, 255),
                    point(mid + math.cos(angle) * dist, mid + math.sin(angle) * dist),
                    2 + (i % 3))
        additive_stamp(self.canvas, (side, side), (int(cx - side / 2), int(cy - side / 2)), paint)
        badge = pygame.Rect(int(cx + 96), int(cy - 28), 72, 32)
        draw_panel(self.canvas, badge, ORANGE, GOLD, cut=7, border_width=1, shadow_offset=0)
        self.text(self.canvas, f"+{self.winnings}", badge.centerx, badge.centery,
                  16, BG, True, "center", family="number", max_width=64)
        combo = pygame.Rect(badge.right + 8, badge.y, 48, 30)
        draw_panel(self.canvas, combo, (28, 16, 18), ORANGE, cut=7, border_width=1, shadow_offset=0)
        self.text(self.canvas, f"x{max(1, self.streak)}", combo.centerx, combo.centery,
                  15, ORANGE, True, "center", family="number", max_width=42)
        tag = pygame.Surface((132, 30), pygame.SRCALPHA)
        pygame.draw.rect(tag, GREEN, (0, 0, 132, 30))
        glyph = self.font(16, True, "title").render("TREFFER!", True, (8, 16, 10))
        tag.blit(glyph, glyph.get_rect(center=(66, 15)))
        tilted = pygame.transform.rotate(tag, -8)
        self.canvas.blit(tilted, tilted.get_rect(center=(int(cx + 78), int(cy + 86))))

    def draw_play(self) -> None:
        self.header()
        caption, word = self._question_caption()
        self.text(self.canvas, caption, 640, 112,
                  16, MUTED, False, "center", family="label", max_width=620)
        size = 78 if len(word) <= 8 else 54 if len(word) <= 14 else 40
        font = self.font(size, True, "title")
        verb_img = font.render(word, True, WHITE)
        verb_rect = verb_img.get_rect(center=(640, 168))
        glow_text(self.canvas, verb_img, verb_rect, CYAN, 3)
        self.canvas.blit(verb_img, verb_rect)
        self._draw_time_segments()
        if getattr(self, "banner", "") and getattr(self, "banner_age", 99) < 2.2 and self.phase == "play":
            self.text(self.canvas, self.banner, 640, 246, 15, GOLD, True,
                      "center", family="title", max_width=420)
        timer_rect = pygame.Rect(850, 118, 99, 99)
        budget = max(0.1, getattr(self, "time_budget", QUESTION_SECONDS))
        ratio = max(0, min(1, self.time_left / budget))
        fx, tier = self.active_fx()
        frozen = bool(fx and fx.key == "freeze" and self.phase == "play"
                      and self.question_age < fx.value(tier))
        tint = CYAN if frozen else ORANGE if ratio < .3 else GOLD
        pygame.draw.arc(self.canvas, (40, 50, 74), timer_rect, -math.pi / 2,
                        1.5 * math.pi, 6)
        if ratio > .001:
            start = -math.pi / 2
            end = start + math.tau * ratio

            def arc_glow(layer, start=start, end=end, tint=tint):
                shifted = timer_rect.move(-828, -104)
                pygame.draw.arc(layer, tint, shifted, start, end, 8)
            additive_stamp(self.canvas, (140, 140), (828, 104), arc_glow)
            pygame.draw.arc(self.canvas, tint, timer_rect, start, end, 7)
        self.text(self.canvas, f"{self.time_left:0.1f}", 899, 160,
                  26, GOLD, True, "center", family="number")
        clock_label = "EIS" if frozen else "STOP" if self.phase == "flight" else "SEK"
        self.text(self.canvas, clock_label, 899, 188, 12,
                  CYAN if frozen or self.phase in ("flight", "impact") else MUTED,
                  False, "center", family="label")
        if getattr(self, "time_bank", 0) > 0.05:
            self.text(self.canvas, f"BANK {self.time_bank:.1f}", 899, 210, 11,
                      CYAN, True, "center", family="number", max_width=90)
        popup = self.popup_progress()
        for i, word_i in enumerate(self.options):
            state = "eliminated" if i in getattr(self, "eliminated", set()) else "neutral"
            if self.phase == "impact":
                if self.outcome == "correct" and i == self.correct_index:
                    state = "correct"
                elif self.outcome != "correct" and i == self.chosen_index:
                    state = "wrong"
            self.draw_dummy(i, word_i, popup, state)
        if self.phase == "impact":
            self.draw_hit_flourish()
        hint = self._hint_line() if self.phase == "play" and self.hint_visible else ""
        if hint and fx and fx.key == "hint_sentence" and tier >= 6 and self.verb.signal in hint:
            before, _, after = hint.partition(self.verb.signal)
            bits = ((before, WHITE), (self.verb.signal, GOLD), (after, WHITE))
            widths = []
            fonts = self.font(16, False, "label")
            for text, _color in bits:
                widths.append(fonts.size(text)[0] if text else 0)
            total = sum(widths)
            x = 640 - total / 2
            y = 603
            for (text, color), width in zip(bits, widths):
                if text:
                    self.text(self.canvas, text, x, y, 16, color, False, "left", family="label")
                    x += width
        elif hint:
            self.text(self.canvas, hint, 640, 603, 16, CYAN, False,
                      "center", family="label", max_width=900)
        else:
            self.text(self.canvas, "KLICK AUF DIE RICHTIGE FORM  *  EIN SCHUSS  *  5 SEKUNDEN",
                      640, 603, 13, MUTED, False, "center", family="label")
        self.draw_hearts()
        x, y = self.mouse
        if self.phase == "play" and 60 < x < 1220 and 260 < y < 530:
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
        t = min(1.0, self.flight_time / self.flight_seconds)
        # FX stay inside the stage: never cover the verb, text or shop/HUD.
        previous_clip = self.canvas.get_clip()
        self.canvas.set_clip(pygame.Rect(70, 238, 1140, 357))
        try:
            draw_weapon_trail(self.canvas, kind, u.tier if u else 0,
                              self.shot_from, self.shot_to,
                              t, self.time_elapsed, draw_symbol)
            draw_flight_choreography(self.canvas, kind, u.tier if u else 1,
                                    self.shot_from, self.shot_to,
                                    t, self.time_elapsed, draw_symbol)
        finally:
            self.canvas.set_clip(previous_clip)
        # Particularly important for the cinematic homing missile.
        if kind == "rocket" and .27 < t < .57:
            self.text(self.canvas, "ZIELSUCHE ...", self.shot_to[0], self.shot_to[1] - 57,
                      15, CYAN, True, "center", family="label", max_width=185)
        elif kind == "rocket" and t >= .57:
            self.text(self.canvas, "ZIEL ERFASST", self.shot_to[0], self.shot_to[1] - 57,
                      15, GREEN, True, "center", family="label", max_width=185)

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
        caption, word = self._question_caption()
        self.text(self.canvas, caption, 640, 112, 16, MUTED, False,
                  "center", family="label", max_width=640)
        self.text(self.canvas, word, 640, 168,
                  64 if len(word) < 16 else 42, WHITE, True, "center",
                  family="title", max_width=760)
        for i, word_i in enumerate(self.options):
            state = "correct" if i == self.correct_index else "wrong" if i == self.chosen_index else "neutral"
            self.draw_dummy(i, word_i, 1, state)
        success = self.outcome == "correct"
        assisted = bool(getattr(self, "assisted_shot", False))
        note = getattr(self, "life_note", "")
        if success and assisted:
            color, title = GOLD, "MIT HILFE"
        elif success and note == "rebound":
            color, title = CYAN, "NACHGESCHOSSEN"
        elif success:
            color, title = GREEN, "TREFFER!"
        elif note == "shield":
            color, title = CYAN, "SCHILD HÄLT"
        elif note == "quench":
            color, title = CYAN, "GELÖSCHT"
        elif note == "bonus":
            color, title = ORANGE, "AUFFRISCHUNG DANEBEN"
        elif self.outcome == "timeout":
            color, title = ORANGE, "ZEIT ABGELAUFEN!"
        else:
            color, title = RED, "DANEBEN!"
        answer = self.verb.simple_past
        if getattr(self, "mode", "") == "boss" and getattr(self, "boss", None) and self.boss.stage >= 1:
            answer = self.verb.past_participle
        draw_panel(self.canvas, (286, 347, 708, 140), PANEL, color,
                   cut=16, border_width=2, shadow_offset=4)
        self.text(self.canvas, title, 640, 375, 22, color, True,
                  "center", family="title", max_width=640)
        self.text(self.canvas, "RICHTIG: " + answer.upper(),
                  640, 421, 35, WHITE, True, "center", family="title", max_width=650)
        if success and note == "rebound":
            footer = "LEBEN GERETTET · VERB KOMMT WIEDER"
            footer_color = CYAN
        elif success and assisted:
            footer = f"+{self.winnings} MÜNZEN · VERB KOMMT WIEDER"
            footer_color = GOLD
        elif success:
            footer = f"+{self.winnings} MÜNZEN"
            footer_color = GOLD
        elif note in ("shield", "quench", "bonus"):
            footer = "KEIN LEBEN VERLOREN"
            footer_color = CYAN
        else:
            footer = "-1 LEBEN"
            footer_color = color
        self.text(self.canvas, footer, 640, 465, 17, footer_color, True,
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
        rarity_index = (0, 1, 1, 2, 2, 3)[upgrade.theme_index % 6]
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
        self.text(self.canvas, f"STUFE {tier}/10  ·  {upgrade.effect_line}",
                  rect.x + 100, rect.y + 90, 12, CYAN,
                  False, family="label", max_width=rect.w - 118)
        for i in range(10):
            seg = pygame.Rect(rect.x + 18 + i * 35, rect.y + 108, 29, 7)
            if i < tier:
                seg_copy = seg.copy()

                def dash_glow(layer, seg_copy=seg_copy, rarity_col=rarity_col):
                    pygame.draw.rect(layer, rarity_col,
                                     pygame.Rect(5, 4, seg_copy.w, seg_copy.h), border_radius=2)
                additive_stamp(self.canvas, (seg.w + 10, seg.h + 8),
                               (seg.x - 5, seg.y - 4), dash_glow)
                rounded(self.canvas, seg, rarity_col, radius=2)
            else:
                rounded(self.canvas, seg, (34, 42, 71), radius=2)
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
        if state == "ZU TEUER":
            lock = (action_r.x + 16, action_r.centery)
            pygame.draw.rect(self.canvas, MUTED, (lock[0], lock[1] - 3, 10, 8), 1)
            pygame.draw.arc(self.canvas, MUTED, (lock[0] + 1, lock[1] - 9, 8, 8), 0, math.pi, 1)
            self.text(self.canvas, state, action_r.centerx + 8, action_r.centery,
                      13, action_ink, True, "center", family="label", max_width=100)
        else:
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
        title_font = self.font(32, True, "title")
        left = title_font.render("MUNITIONS", True, WHITE)
        hyphen = title_font.render("-", True, MAGENTA)
        right = title_font.render("WERKSTATT", True, WHITE)
        self.canvas.blit(left, (32, 96))
        self.canvas.blit(hyphen, (32 + left.get_width() + 2, 96))
        self.canvas.blit(right, (32 + left.get_width() + hyphen.get_width() + 6, 96))
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
        page_items = self.shop_page_items()
        for i, upgrade in enumerate(page_items):
            x = 32 + (i % 3) * 412
            y = 233 + (i // 3) * 195
            self.shop_card(upgrade, pygame.Rect(x, y, 392, 179))
        if not page_items:
            self.text(self.canvas, "NOCH KEINE WAFFEN GEKAUFT", 640, 351,
                      30, MUTED, True, "center", family="title", max_width=800)
            self.text(self.canvas, "Unter ALLE LEVEL kannst du deine erste Munition kaufen.",
                      640, 409, 16, WHITE, False, "center", family="label")
        draw_panel(self.canvas, (32, 632, 1216, 70), PANEL, (78, 103, 145),
                   cut=10, border_width=1, shadow_offset=1)
        last = self.shop_last_page()
        self.button(pygame.Rect(46, 645, 52, 46), "<", CYAN,
                    secondary=True, size=26, disabled=self.page == 0)
        self.text(self.canvas, f"SEITE {self.page + 1}/{last + 1}", 149, 668,
                  15, WHITE, True, "center", family="number", max_width=95)
        self.button(pygame.Rect(200, 645, 52, 46), ">", CYAN,
                    secondary=True, size=26, disabled=self.page == last)
        self.button(pygame.Rect(408, 645, 134, 46), "ALLE LEVEL", CYAN,
                    secondary=self.shop_view != "all", size=14)
        self.button(pygame.Rect(552, 645, 194, 46),
                    f"GEKAUFT ({len(self.owned)})", GREEN,
                    secondary=self.shop_view != "owned", size=14)
        self.text(self.canvas, "Klick: kaufen oder ausrüsten", 872, 668,
                  15, MUTED, False, "center", family="label", max_width=200)
        self.button(pygame.Rect(994, 638, 236, 51),
                    "NÄCHSTE FRAGE  >", CYAN, size=18)
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
        weak = [
            name for name, stat in sorted(getattr(self, "verb_stats", {}).items())
            if isinstance(stat, dict) and int(stat.get("box", 5)) <= 1
            and (int(stat.get("wrong", 0)) or int(stat.get("assisted", 0)))
        ]
        if weak:
            shown = ", ".join(weak[:8])
            self.text(self.canvas, "NOCH ÜBEN: " + shown, W // 2, 512, 14, GOLD,
                      True, "center", family="label", max_width=680)
        else:
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
                elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 3:
                    self.use_active()
                elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                    mapped = self.screen_mouse(event.pos)
                    if mapped:
                        self.click(mapped)
            self.update(dt)
            self.render()
            frames += 1
            if smoke_test and frames == 4:
                # Exercise play, a hinted shot, particle FX, the shop and a rebound.
                self.equipped = next(u.id for u in UPGRADES if u.theme.projectile == "chalk" and u.tier == 1)
                self.owned.add(self.equipped)
                self.new_run()
                self.question_age = 4.0
                self._maybe_hint()
                self.register_shot(self.correct_index, (640, 480))
            if smoke_test and frames == 10:
                while self.phase == "flight":
                    self.update(0.05)
                self.equipped = next(u.id for u in UPGRADES if u.theme.projectile == "gold" and u.tier == 5)
                self.owned.add(self.equipped)
                if self.phase != "end":
                    self.start_shop()
                    self.render()
                    if self.lives > 0 and not self.deck.complete:
                        self.start_question()
                        self.register_shot(self.correct_index, self.bullseye_center(self.correct_index))
            if smoke_test and frames == 16:
                while self.phase == "flight":
                    self.update(0.05)
                rubber = next(u.id for u in UPGRADES if u.theme.projectile == "rubber" and u.tier == 4)
                self.equipped = rubber
                self.owned.add(rubber)
                if self.lives > 0 and not self.deck.complete and self.phase != "end":
                    self.start_question()
                    self.register_shot(None, (120, 300))
                    self.resolve()
                    if self.phase == "play":
                        self.register_shot(self.correct_index, self.bullseye_center(self.correct_index))
                self.start_shop()
                self.use_active()
            if smoke_test and frames >= 22:
                break
        self.save_progress()
        pygame.quit()


def main() -> None:
    Game().loop(smoke_test="--smoke-test" in sys.argv)


if __name__ == "__main__":
    main()
