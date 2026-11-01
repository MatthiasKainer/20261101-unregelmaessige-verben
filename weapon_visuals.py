"""Weapon-specific arcade effects. All graphics are generated at runtime.

Each of the 28 families has its own motion (weapon_fx), trail and impact.
Higher tiers increase the number, scale and persistence of visual details.
"""
from __future__ import annotations

import math
import pygame

from upgrades import THEMES
from weapon_fx import WEAPONS, flight_point

Color = tuple[int, int, int]
PALETTE = ((255, 96, 126), (255, 200, 84), (83, 231, 185),
           (93, 194, 255), (202, 134, 253), (255, 255, 238))


def xy(x: float, y: float) -> tuple[int, int]:
    return int(x), int(y)


def fade(color: Color, amount: float, bg: Color = (25, 40, 59)) -> Color:
    a = max(0.0, min(1.0, amount))
    return tuple(int(bg[i] * (1 - a) + color[i] * a) for i in range(3))


def line(surface, color, a, b, width=2):
    pygame.draw.line(surface, color, xy(*a), xy(*b), max(1, int(width)))



def trail(surface: pygame.Surface, kind: str, tier: int, start: tuple,
          end: tuple, progress: float, elapsed: float, symbol) -> tuple[float, float]:
    """Draw a recognizable projectile & trail; return its curved screen position."""
    w = WEAPONS[kind]
    theme = next(theme for theme in THEMES if theme.projectile == kind)
    p = min(1.0, max(0.0, progress))
    amount = max(8, int(46 * p))
    points = [flight_point(kind, start, end, p * i / amount) for i in range(amount + 1)]
    head = points[-1]
    color, accent = theme.color, theme.accent
    if w.trail in ("laser", "electric", "plasma"):
        if w.trail == "laser":
            for width, ink in ((17, fade(color, .22)), (8, fade(accent, .72)), (3, (250, 255, 255))):
                line(surface, ink, start, head, width + tier // 4)
            for i in range(0, len(points), 6):
                pygame.draw.circle(surface, accent, xy(*points[i]), 3 + tier // 3, 1)
        else:
            for i in range(1, len(points)):
                a, b = points[i - 1], points[i]
                if i % 2 == 0:
                    line(surface, fade(color, .6), a, b, 6 + tier // 4)
                line(surface, (238, 246, 255) if i % 3 == 0 else accent, a, b, 2)
                if i % 7 == 0:
                    dx = 12 * math.sin(elapsed * 12 + i)
                    line(surface, accent, b, (b[0] + dx, b[1] - 17), 2)
    elif w.trail == "rainbow":
        for k, rainbow_color in enumerate(PALETTE[:5]):
            shifted = [(x + (k - 2) * 5, y + (k - 2) * 4) for x, y in points]
            if len(shifted) > 1:
                pygame.draw.lines(surface, fade(rainbow_color, .84), False,
                                  [xy(*q) for q in shifted], 3 + tier // 5)
    elif w.trail in ("fire", "thrusters", "comet", "sparks", "smoke"):
        for i in range(1, len(points), 2):
            f = i / len(points)
            r = max(2, int((4 + tier * .38) * f))
            ink = (255, 77, 62) if w.trail in ("fire", "thrusters") and i % 3 == 0 else color
            pygame.draw.circle(surface, fade(ink, .18 + .8 * f), xy(*points[i]), r)
            if i % 5 == 0:
                pygame.draw.circle(surface, accent, xy(*points[i]), max(1, r // 2))
        if w.trail == "comet" and len(points) > 3:
            pygame.draw.lines(surface, fade(accent, .62), False,
                              [xy(*q) for q in points], max(2, 3 + tier // 4))
        if w.trail == "thrusters":
            x, y = head
            pygame.draw.polygon(surface, (255, 196, 52), [xy(x - 13, y + 4),
                                xy(x - 41 - tier, y + 8), xy(x - 12, y - 6)])
    else:
        for i in range(0, len(points), 3):
            t = i / max(1, len(points) - 1)
            x, y = points[i]
            r = max(3, int(2 + 6 * t + tier * .28))
            if w.trail in ("bubbles", "orbs", "coins", "footprints", "donuts"):
                if w.trail == "bubbles":
                    pygame.draw.circle(surface, fade(accent, .65), xy(x, y), r + 4, 2)
                    pygame.draw.circle(surface, (246, 249, 255), xy(x - 2, y - 2), 2)
                elif w.trail == "coins":
                    pygame.draw.ellipse(surface, color, (int(x - r), int(y - r), r + 3, r * 2), 2)
                elif w.trail == "footprints":
                    pygame.draw.circle(surface, (246, 248, 249), xy(x, y), max(2, r - 1), 1)
                else:
                    pygame.draw.circle(surface, fade(color, .4 + t * .5), xy(x, y), r, 2)
            elif w.trail in ("paper", "folds", "slices", "blades", "diamonds"):
                if w.trail == "paper":
                    pygame.draw.rect(surface, PALETTE[(i // 3) % len(PALETTE)],
                                     (int(x - r), int(y - r), r * 2, r),
                                     border_radius=1)
                else:
                    symbol(surface, x, y, r + 1, kind, fade(accent, .22 + t * .68), color)
            elif w.trail in ("drips", "drops", "paint"):
                pygame.draw.ellipse(surface, color if i % 2 else accent,
                                    (int(x - r * .6), int(y - r), r, max(3, int(r * 1.7))))
            elif w.trail == "disco":
                pygame.draw.rect(surface, PALETTE[(i // 3) % len(PALETTE)],
                                 (int(x - r), int(y - r), r * 2, r * 2))
            elif w.trail in ("twinkle", "flakes", "hearts", "sprinkles", "nebula", "powder"):
                if w.trail == "powder":
                    line(surface, color, (x - r, y + r), (x + r, y - r), max(1, r // 3))
                elif w.trail == "sprinkles":
                    line(surface, PALETTE[(i // 3) % len(PALETTE)], (x, y), (x + r, y + r), 3)
                else:
                    symbol(surface, x, y, max(3, r), kind,
                           PALETTE[(i // 3) % len(PALETTE)] if w.trail == "nebula" else accent, color)
            else:
                pygame.draw.circle(surface, fade(color, t), xy(x, y), r)
    x, y = head
    size = int(21 + min(10, tier) * .6)
    # The rotating projectile is visually different from slow moving bubbles/laser.
    spin_kinds = {"football", "ninja", "pizza", "donut", "disco", "galaxy", "crystal", "gold", "star"}
    if kind in spin_kinds:
        tile = pygame.Surface((116, 116), pygame.SRCALPHA)
        symbol(tile, 58, 58, size, kind, color, accent)
        angle = elapsed * (450 if kind in ("ninja", "football") else 230)
        spun = pygame.transform.rotozoom(tile, angle, 1)
        surface.blit(spun, spun.get_rect(center=xy(x, y)))
    elif kind in ("plasma", "laser", "lightning"):
        for rr in (size + 10, size + 3):
            pygame.draw.circle(surface, fade(color, .60), xy(x, y), rr, 2)
        symbol(surface, x, y, size, kind, color, accent)
    elif kind == "rocket":
        symbol(surface, x, y, size + 7, kind, color, accent)
    else:
        symbol(surface, x, y, size, kind, color, accent)
    return head


def impact(surface: pygame.Surface, kind: str, x: float, y: float,
           age: float, tier: int, symbol, duration: float = 1.05) -> None:
    """Distinct, animated hit celebrations (one for each weapon family)."""
    p = max(0., min(1., age / duration))
    if p >= 1:
        return
    energy = (1 - p) ** .6
    x, y = float(x), float(y)
    theme = next(t for t in THEMES if t.projectile == kind)
    c, a = theme.color, theme.accent
    bright = fade(c, energy)
    s = 1.0 + tier * .07
    radius = (24 + 155 * p) * s

    def dot(angle: float, distance: float, size: float, color: Color, symbol_kind: str | None = None):
        px, py = x + math.cos(angle) * distance, y + math.sin(angle) * distance
        if symbol_kind:
            symbol(surface, px, py, size, symbol_kind, color, a)
        else:
            pygame.draw.circle(surface, color, xy(px, py), max(1, int(size)))

    def wheel(count: int, displacement: float, size: float, icon: str | None = None,
              palette: tuple[Color, ...] = ()):  # deterministic, no per-frame flicker
        for j in range(count):
            angle = j * math.tau / count + j * .09
            dot(angle, displacement * (.65 + .12 * (j % 4)), size * energy,
                (palette or (c, a))[j % len(palette or (c, a))], icon)

    if kind == "chalk":
        for j in range(18 + tier * 2):
            angle = j * 2.39996
            distance = radius * (j % 6 + 1) / 7
            dot(angle, distance, 2 + tier // 5, fade((243, 244, 238), energy))
            if j % 3 == 0:
                px, py = x + math.cos(angle) * distance, y + math.sin(angle) * distance
                line(surface, bright, (px - 11, py + 7), (px + 11, py - 7), 2)
    elif kind == "confetti":
        for j in range(30 + tier * 3):
            angle = j * 2.39996
            d = (25 + (j * 17) % 80) * p * s
            px, py = x + math.cos(angle) * d, y + math.sin(angle) * d + 44 * p * p
            col = fade(PALETTE[j % 6], energy)
            pygame.draw.rect(surface, col, (int(px), int(py), 4 + j % 7, 3 + j % 5))
    elif kind == "ink":
        wheel(12 + tier * 2, radius * .67, 5 + 8 * energy)
        pygame.draw.circle(surface, bright, xy(x, y), max(2, int(35 * energy)))
        for j in range(10):
            ang = j * .628
            dot(ang, radius * .31, 6 * energy, a)
    elif kind == "rubber":
        for j in range(4 + tier // 2):
            dx = j * 23 - 35
            px, py = x + dx * energy, y - abs(math.sin(7 * p + j)) * 57 * energy
            pygame.draw.ellipse(surface, bright, (int(px - 17), int(py - 8), 34, 18), 3)
        pygame.draw.ellipse(surface, a, (int(x - radius), int(y - 13 * energy), int(2 * radius),
                                        max(2, int(26 * energy))), 3)
    elif kind == "laser":
        for width, col in ((16, fade(c, energy * .27)), (5, bright), (2, (250, 250, 255))):
            line(surface, col, (x - radius, y), (x + radius, y), width)
            line(surface, col, (x, y - radius), (x, y + radius), width)
        pygame.draw.circle(surface, a, xy(x, y), max(1, int(radius * .7)), max(2, int(3 * energy)))
    elif kind == "star":
        wheel(10 + tier * 2, radius, 14 * energy, "star", (c, a, (255, 255, 225)))
    elif kind == "plane":
        wheel(9 + tier, radius, 14 * energy, "plane")
        line(surface, fade(a, energy), (x - radius, y + radius * .5),
             (x + radius, y - radius * .5), 2)
    elif kind == "firework":
        for burst in range(3 + tier // 3):
            cx = x + math.sin(burst * 2.5) * (40 + 40 * p)
            cy = y - 60 * p + math.cos(burst * 1.7) * 40
            for j in range(12):
                ang = math.tau * j / 12
                dx, dy = math.cos(ang), math.sin(ang)
                line(surface, fade(PALETTE[(j + burst) % 6], energy),
                     (cx + dx * 9 * p, cy + dy * 9 * p),
                     (cx + dx * (19 + radius * .36), cy + dy * (19 + radius * .36)), 2 + tier // 5)
    elif kind == "explosion":
        for layer in range(3):
            r = radius * (.3 + .28 * layer)
            pts = [(x + math.cos(j * math.pi / 9) * r * (1.4 if j % 2 else .72),
                    y + math.sin(j * math.pi / 9) * r * (1.4 if j % 2 else .72))
                   for j in range(18)]
            pygame.draw.polygon(surface, fade((255, 72 + layer * 45, 49), energy),
                                [xy(*q) for q in pts], max(2, int(8 * energy)))
        wheel(18 + tier, radius, 6 * energy, "star", (a, c))
    elif kind == "football":
        # The impact becomes a proper soccer goal (net plus bouncing balls).
        left, top, width, height = x - radius * .85, y - radius * .67, radius * 1.7, radius * 1.15
        pygame.draw.rect(surface, fade((228, 236, 241), energy),
                         (int(left), int(top), int(width), int(height)), max(2, int(5 * energy)))
        for k in range(1, 8):
            xx = left + width * k / 8
            line(surface, fade(a, energy * .7), (xx, top), (xx, top + height), 1)
        for k in range(1, 5):
            yy = top + height * k / 5
            line(surface, fade(a, energy * .7), (left, yy), (left + width, yy), 1)
        wheel(3 + tier // 3, radius * .62, 12 * energy, "football")
    elif kind == "lightning":
        for branch in range(7 + tier):
            ang = branch * math.tau / (7 + tier)
            pts = [xy(x + math.cos(ang) * radius * t / 8 + math.sin(ang * 7 + t) * 13 * energy,
                      y + math.sin(ang) * radius * t / 8 + math.cos(ang * 4 + t) * 9 * energy)
                   for t in range(9)]
            pygame.draw.lines(surface, fade(a, energy), False, pts, 2 + tier // 4)
    elif kind == "snow":
        wheel(16 + tier * 2, radius, 14 * energy, "snow")
        pygame.draw.circle(surface, fade((218, 241, 253), .6 * energy),
                           xy(x, y), max(1, int(radius * .4)), 2)
    elif kind == "water":
        for j in range(15 + tier):
            ang = math.pi + j * math.pi / (14 + tier)
            px = x + math.cos(ang) * radius * .8
            py = y + math.sin(ang) * radius * .64 + 52 * p * p
            pygame.draw.ellipse(surface, fade(c, energy), (int(px), int(py),
                                                         5 + tier // 4, 15 + j % 5))
        pygame.draw.ellipse(surface, a, (int(x - radius), int(y - 12), int(2 * radius), 24), 3)
    elif kind == "bubble":
        for j in range(13 + tier):
            dx = math.sin(j * 2.4) * radius * .7
            py = y - ((j * 29) % 100 + 110 * p) * s
            rr = max(3, int((7 + j % 12) * energy))
            pygame.draw.circle(surface, fade(a, energy), xy(x + dx, py), rr, 2)
            pygame.draw.circle(surface, (235, 252, 255), xy(x + dx - 2, py - 2), 2)
    elif kind == "meteor":
        for layer in range(3):
            pygame.draw.circle(surface, fade((245, 88 + layer * 55, 38), energy),
                               xy(x, y), max(1, int(radius * (.85 - layer * .22))), 5)
        wheel(12, radius, 11 * energy, "meteor")
    elif kind == "crystal":
        wheel(15 + tier, radius, 15 * energy, "crystal", (c, a, (250, 251, 255)))
    elif kind == "heart":
        wheel(12 + tier, radius, 15 * energy, "heart", (c, a))
    elif kind == "donut":
        wheel(9 + tier // 2, radius, 16 * energy, "donut", (c, a))
        wheel(17 + tier, radius * .65, 3 * energy, None, PALETTE)
    elif kind == "pizza":
        wheel(8 + tier // 2, radius, 16 * energy, "pizza")
        for j in range(10):
            dot(j * 2.4, radius * .6, 5 * energy, fade((250, 220, 95), energy))
    elif kind == "rocket":
        wheel(5 + tier // 3, radius * .88, 17 * energy, "rocket")
        for j in range(19):
            ang = j * math.tau / 19
            dot(ang, radius * .55, 5 * energy, PALETTE[j % 3])
    elif kind == "comet":
        for j in range(4 + tier // 2):
            ang = j * math.tau / (4 + tier // 2)
            line(surface, fade(c if j % 2 else a, energy), (x, y),
                 (x + math.cos(ang) * radius * 1.4, y + math.sin(ang) * radius * 1.4), 4)
        wheel(9, radius, 7 * energy, "star")
    elif kind == "rainbow":
        for j, col in enumerate(PALETTE[:5]):
            rr = radius * .45 + j * 13
            pygame.draw.arc(surface, fade(col, energy),
                            (int(x - rr), int(y - rr * .6), int(2 * rr), int(rr * 1.2)),
                            math.pi, math.tau, 5 + tier // 5)
        wheel(6 + tier // 3, radius, 9 * energy, "star", PALETTE)
    elif kind == "paint":
        for j in range(23 + tier * 2):
            angle = j * 2.39996
            distance = (j * 13 % 100) / 100 * radius
            dot(angle, distance, (3 + j % 8) * energy, PALETTE[j % 6])
    elif kind == "disco":
        for j in range(14 + tier):
            theta = j * math.tau / (14 + tier)
            px, py = x + math.cos(theta) * radius, y + math.sin(theta) * radius
            col = fade(PALETTE[j % 6], energy)
            pygame.draw.rect(surface, col, (int(px), int(py),
                                            max(2, int(12 * energy)), max(2, int(12 * energy))))
            if j % 3 == 0:
                line(surface, col, (x, y), (px, py), 2)
    elif kind == "plasma":
        for j in range(3 + tier // 3):
            pygame.draw.circle(surface, fade(c if j % 2 else a, energy), xy(x, y),
                               max(1, int(radius * (j + 1) / (3 + tier // 3))), 4)
        wheel(12, radius, 9 * energy, "plasma")
    elif kind == "ninja":
        wheel(9 + tier // 3, radius, 15 * energy, "ninja")
        pygame.draw.circle(surface, fade(c, energy), xy(x, y), max(2, int(radius * .7)), 3)
    elif kind == "galaxy":
        for j in range(45 + tier * 4):
            theta = j * .55 + age * 4
            rr = math.sqrt(j / (45 + tier * 4)) * radius
            dot(theta, rr, 2.0 + (j % 4), PALETTE[j % 6])
    elif kind == "gold":
        for j in range(18 + tier * 2):
            px = x + math.sin(j * 2.4) * radius * .83
            py = y - 90 * p + (j * 29 % 100) * p + 130 * p * p
            symbol(surface, px, py, 8 + j % 7, "gold", fade(c, energy), a)
    else:
        wheel(10 + tier, radius, 8 * energy, kind)
