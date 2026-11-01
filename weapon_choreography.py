"""28 deliberately different, bounded flight shows.

Drawn over the family's ordinary tracer in weapon_visuals.py. Every show
has a unique flight prop, movement cue and high-tier variant. No effect
paints over the full board; the verb and answer panels remain legible.
"""
from __future__ import annotations

import math

import pygame

from upgrades import THEMES
from weapon_fx import flight_point, level_showcase

COLORS = {theme.projectile: (theme.color, theme.accent) for theme in THEMES}
WHITE = (245, 248, 255)
CYAN = (34, 230, 255)
GOLD = (255, 197, 61)
GREEN = (182, 255, 59)


def pt(x: float, y: float) -> tuple[int, int]:
    return round(x), round(y)


def line(surface: pygame.Surface, color, a, b, width=2) -> None:
    pygame.draw.line(surface, color, pt(*a), pt(*b), max(1, round(width)))


def circle(surface: pygame.Surface, color, x, y, radius, width=0) -> None:
    pygame.draw.circle(surface, color, pt(x, y), max(1, round(radius)), max(0, round(width)))


def orbit(surface, x, y, radius, color, phase, number=4, dot=3):
    for i in range(number):
        a = phase + math.tau * i / number
        circle(surface, color, x + radius * math.cos(a), y + radius * math.sin(a), dot)


def star(surface, x, y, radius, color, spikes=5, depth=.46):
    points = []
    for i in range(spikes * 2):
        theta = i * math.pi / spikes - math.pi / 2
        rr = radius if i % 2 == 0 else radius * depth
        points.append(pt(x + rr * math.cos(theta), y + rr * math.sin(theta)))
    pygame.draw.polygon(surface, color, points)


def box(surface, x, y, radius, color, width=2):
    r = pygame.Rect(round(x - radius), round(y - radius), round(radius * 2), round(radius * 2))
    pygame.draw.rect(surface, color, r, width, border_radius=3)


def draw_flight_choreography(surface: pygame.Surface, kind: str, tier: int,
                             start: tuple[float, float], end: tuple[float, float],
                             t: float, elapsed: float, symbol) -> None:
    """Every family gets a custom animated prop. Tier upgrades stack visibly."""
    t = min(1.0, max(0.0, t))
    tier = min(10, max(1, int(tier)))
    x, y = flight_point(kind, start, end, t)
    c, a = COLORS[kind]
    beat = elapsed * 7
    effects = level_showcase(tier)
    # Incremental level perks: tiers 2,3,5,6,8,9,10 are universal but use
    # each family's colors and its real path. Tiers 4 & 7 are themed below.
    if tier >= 2:
        for i in range(2):
            at = flight_point(kind, start, end, max(0.0, t - (i + 1) * .042))
            circle(surface, c, at[0], at[1], 2 + tier // 4)
    if tier >= 3:
        orbit(surface, x, y, 17 + tier * .5, a, beat, 2 + tier // 4, 2)
    if tier >= 5:
        for i in range(2):
            old = flight_point(kind, start, end, max(0.0, t - .08 - i * .04))
            symbol(surface, old[0], old[1] + (i * 2 - 2), 5 + tier // 3,
                   kind, a, c)
    if tier >= 6:
        pygame.draw.arc(surface, c,
                        pygame.Rect(round(x - 27), round(y - 27), 54, 54),
                        beat, beat + 2.4, 2)
    if tier >= 8:
        for k in range(3):
            old = flight_point(kind, start, end, max(0.0, t - .12 - k * .05))
            circle(surface, a, *old, 3 - k // 2, 1)
    if tier >= 9 and t > .7:
        # A restrained focus spot, not the enormous additive color slabs of v3.
        circle(surface, c, end[0], end[1], 25 + 5 * math.sin(beat), 1)
    if tier == 10:
        orbit(surface, x, y, 30 + 5 * math.sin(beat), c, -beat * .7, 6, 2)

    # The following 28 one-off performances are purposely not an interchangeable
    # pile of circles. Each one has a recognizable object and staged animation.
    if kind == "chalk":
        # A handwriting slash flicks, sheds white dust and draws an X at level 7.
        for k in range(6 if tier >= 4 else 3):
            px = x - k * 12
            py = y + k * 5
            line(surface, WHITE, (px - 7, py + 5), (px + 8, py - 5), 2)
        if tier >= 7:
            line(surface, c, (end[0] - 18, end[1] - 18),
                 (end[0] + 18, end[1] + 18), 2)
    elif kind == "confetti":
        for k in range(5 + tier // 2):
            ang = k * 2.2 + beat * .7
            px = x + math.cos(ang) * (12 + 3 * k)
            py = y + math.sin(ang) * (8 + 2 * k)
            ink = ((255, 94, 147), (255, 205, 68), CYAN)[k % 3]
            pygame.draw.rect(surface, ink, (round(px), round(py), 3 + k % 4, 4 + k % 3))
        if tier >= 7:
            orbit(surface, x, y, 40, a, -beat, 9, 2)
    elif kind == "ink":
        circle(surface, c, x, y, 18 + 3 * math.sin(beat))
        for k in range(4 + tier // 3):
            circle(surface, a, x + 20 * math.sin(k * 1.7),
                   y + 15 + (beat * 6 + k * 11) % 24, 3 + k % 2)
        if tier >= 7:
            pygame.draw.ellipse(surface, c, (round(x - 29), round(y - 5), 58, 20), 2)
    elif kind == "rubber":
        stretch = abs(math.sin(t * math.pi * 5))
        pygame.draw.ellipse(surface, c, (round(x - 19 + 7 * stretch), round(y - 17),
                                         round(38 - 14 * stretch), round(34 + 8 * stretch)), 2)
        if tier >= 4:
            line(surface, a, (x - 25, y + 21), (x + 25, y + 21), 2)
        if tier >= 7:
            circle(surface, a, end[0], end[1], 12 + t * 12, 2)
    elif kind == "laser":
        # Charged focusing aperture + exact straight neon bolt.
        circle(surface, c, start[0], start[1], 8 + t * 14, 2)
        if tier >= 4:
            line(surface, WHITE, start, (x, y), 3)
        if tier >= 7:
            for dy in (-12, 12):
                line(surface, a, (x - 17, y + dy), (x + 17, y + dy), 1)
    elif kind == "star":
        star(surface, x, y, 20 + 2 * math.sin(beat), c)
        if tier >= 4:
            orbit(surface, x, y, 34, WHITE, beat, 5, 3)
        if tier >= 7:
            for theta in range(0, 360, 60):
                aa = math.radians(theta) + beat * .2
                star(surface, x + 39 * math.cos(aa), y + 39 * math.sin(aa), 5, a)
    elif kind == "plane":
        # Folded paper wings tilt during the glide.
        dx = 23 * math.cos(beat * .4)
        pygame.draw.polygon(surface, WHITE, [pt(x + 20, y - 4), pt(x - 25, y - 14),
                                            pt(x - 4 + dx * .2, y), pt(x - 24, y + 15)])
        line(surface, a, (x - 6, y), (x + 20, y - 4), 2)
        if tier >= 7:
            for k in range(3):
                old = flight_point(kind, start, end, max(0.0, t - .1 * (k + 1)))
                symbol(surface, *old, 8, kind, c, a)
    elif kind == "firework":
        # Rising fuse and secondary sparks at stage 7.
        line(surface, GOLD, (x, y + 23), (x - 3 * math.sin(beat), y + 44), 3)
        star(surface, x, y + 26, 5 + 2 * abs(math.sin(beat)), a)
        if tier >= 4:
            orbit(surface, x, y, 30, c, beat * 1.5, 5, 2)
        if tier >= 7:
            for j in range(3):
                star(surface, x + (j - 1) * 24, y - 26 - j * 4, 4, (a, c, GOLD)[j])
    elif kind == "explosion":
        # A recognizable round cartoon bomb with a sizzling fuse.
        circle(surface, (21, 31, 49), x, y, 19)
        circle(surface, c, x, y, 18, 2)
        line(surface, GOLD, (x + 11, y - 16), (x + 22, y - 31), 3)
        star(surface, x + 25, y - 33, 6 + 2 * math.sin(beat), a)
        if tier >= 7:
            for j in range(7):
                th = j * math.tau / 7 + beat * .2
                line(surface, a, (x + math.cos(th) * 24, y + math.sin(th) * 24),
                     (x + math.cos(th) * 35, y + math.sin(th) * 35), 2)
    elif kind == "football":
        # Spin, stitches and a goal frame that materializes at high level.
        circle(surface, WHITE, x, y, 21)
        star(surface, x, y, 11, (20, 38, 58), 5, .65)
        if tier >= 4:
            line(surface, a, (x - 24, y - 28), (x + 24, y - 28), 2)
        if tier >= 7 and t > .45:
            box(surface, end[0], end[1], 36, GREEN, 2)
            for j in range(-1, 2):
                line(surface, GREEN, (end[0] + j * 14, end[1] - 36),
                     (end[0] + j * 14, end[1] + 36), 1)
    elif kind == "lightning":
        # Static branch trees fork off the traveling zigzag.
        line(surface, WHITE, (x - 15, y - 13), (x, y + 5), 3)
        line(surface, a, (x, y + 5), (x + 18, y + 23), 3)
        if tier >= 4:
            for j in range(3):
                off = (j - 1) * 13
                line(surface, c, (x + off, y - 21), (x + off + 11, y + 9), 2)
        if tier >= 7:
            line(surface, WHITE, (x - 33, y), (x + 33, y), 2)
    elif kind == "snow":
        for k in range(6 + tier // 3):
            ang = k * 2.39 + elapsed * .32
            r = 17 + 8 * (k % 3)
            symbol(surface, x + math.cos(ang) * r, y + math.sin(ang) * r, 6,
                   kind, WHITE, a)
        if tier >= 7:
            circle(surface, c, x, y, 43, 2)
    elif kind == "water":
        # Balloons and falling droplets, not sparks.
        circle(surface, c, x, y, 21, 2)
        pygame.draw.polygon(surface, a, [pt(x - 5, y + 21), pt(x + 5, y + 21), pt(x, y + 30)])
        for k in range(5 + tier // 3):
            px = x + 26 * math.cos(k * 2)
            py = y + 27 * math.sin(k * 2) + (elapsed * 12 + k * 7) % 22
            circle(surface, a, px, py, 2 + k % 2)
        if tier >= 7:
            pygame.draw.arc(surface, c, (round(x - 38), round(y - 25), 76, 50),
                            0, math.pi, 2)
    elif kind == "bubble":
        circle(surface, a, x, y, 22, 2)
        circle(surface, WHITE, x - 7, y - 8, 4)
        for k in range(4 + tier // 3):
            bx = x + (k - 2) * 17 + 7 * math.sin(beat * .7 + k)
            by = y - 13 * (k % 3) - (elapsed * (6 + k)) % 22
            circle(surface, c, bx, by, 6 + k % 4, 1)
        if tier >= 7:
            orbit(surface, x, y, 42, a, beat * .3, 7, 4)
    elif kind == "meteor":
        pygame.draw.polygon(surface, c, [pt(x + 21, y - 3), pt(x - 7, y - 21),
                                        pt(x - 24, y + 4), pt(x + 5, y + 22)])
        star(surface, x, y, 9, a)
        if tier >= 4:
            for j in range(5):
                old = flight_point(kind, start, end, max(0.0, t - .03 * j))
                circle(surface, GOLD, old[0] - j * 2, old[1] + j * 2, 4)
        if tier >= 7:
            circle(surface, c, end[0], end[1], 24, 2)
    elif kind == "crystal":
        points = [pt(x, y - 25), pt(x + 18, y), pt(x, y + 25), pt(x - 18, y)]
        pygame.draw.polygon(surface, c, points, 2)
        line(surface, WHITE, (x, y - 25), (x, y + 25), 2)
        line(surface, a, (x - 18, y), (x + 18, y), 1)
        if tier >= 7:
            orbit(surface, x, y, 34, a, -beat * .4, 6, 4)
    elif kind == "heart":
        for j in range(4 + tier // 3):
            dx = math.cos(elapsed * 3 + j * 1.7) * (19 + j * 3)
            dy = math.sin(elapsed * 3 + j * 1.7) * (16 + j * 2)
            symbol(surface, x + dx, y + dy, 6 + j % 2, kind, c, a)
        if tier >= 7:
            circle(surface, a, x, y, 32 + 5 * math.sin(beat), 2)
    elif kind == "donut":
        # Icing spins as colored sprinkles orbit the torus.
        circle(surface, c, x, y, 21)
        circle(surface, (50, 26, 51), x, y, 8)
        orbit(surface, x, y, 19, a, beat, 6, 3)
        if tier >= 7:
            orbit(surface, x, y, 35, GOLD, -beat, 8, 2)
    elif kind == "pizza":
        pizza = [pt(x + 26, y), pt(x - 16, y - 18), pt(x - 16, y + 18)]
        pygame.draw.polygon(surface, GOLD, pizza)
        line(surface, c, (x - 16, y - 18), (x - 16, y + 18), 5)
        for k in range(3):
            circle(surface, (229, 72, 76), x - 6 + k * 7, y + (k - 1) * 5, 3)
        if tier >= 7:
            line(surface, GOLD, (x - 18, y + 20), (x - 11, y + 39), 3)
    elif kind == "rocket":
        # Blast-off, target search, lock, then a visibly steering homing missile.
        nose_t = min(.998, t + .01)
        tail_t = max(0.0, t - .01)
        ahead = flight_point(kind, start, end, nose_t)
        behind = flight_point(kind, start, end, tail_t)
        ang = math.atan2(ahead[1] - behind[1], ahead[0] - behind[0])
        if t < .24:
            ang = -math.pi / 2
        direction = (math.cos(ang), math.sin(ang))
        normal = (-direction[1], direction[0])
        def hull(forward, side):
            return pt(x + direction[0] * forward + normal[0] * side,
                      y + direction[1] * forward + normal[1] * side)
        pygame.draw.polygon(surface, WHITE, [hull(28, 0), hull(8, 13),
                                            hull(-18, 12), hull(-18, -12), hull(8, -13)])
        pygame.draw.polygon(surface, c, [hull(28, 0), hull(8, 13), hull(8, -13)])
        pygame.draw.polygon(surface, a, [hull(-12, 10), hull(-25, 22), hull(-21, 0)])
        pygame.draw.polygon(surface, a, [hull(-12, -10), hull(-25, -22), hull(-21, 0)])
        circle(surface, CYAN, *hull(1, 0), 5)
        tail = hull(-23, 0)
        flame = 24 + 7 * abs(math.sin(beat * 2))
        pygame.draw.polygon(surface, GOLD, [hull(-21, 7),
                                            pt(tail[0] - direction[0] * flame,
                                               tail[1] - direction[1] * flame),
                                            hull(-21, -7)])
        if t < .25:
            for k in range(6):
                circle(surface, WHITE, start[0] + (k - 3) * 12,
                       start[1] - (t * 100 + k * 6) % 48, 2 + k % 4, 1)
        elif t < .57:
            # Scanning cone, moving sweep and radar sweep around chosen answer.
            circle(surface, CYAN, end[0], end[1], 25, 2)
            circle(surface, c, end[0], end[1], 12, 1)
            rad = beat * .7
            line(surface, CYAN, (end[0], end[1]),
                 (end[0] + 25 * math.cos(rad), end[1] + 25 * math.sin(rad)), 2)
            if tier >= 4:
                box(surface, end[0], end[1], 40, a, 1)
        else:
            # On lock, a lead/target line shows that the rocket is homing.
            circle(surface, GREENISH, end[0], end[1], 15 + 5 * math.sin(beat), 2)
            if tier >= 7:
                for j in range(2):
                    symbol(surface, x - direction[0] * (35 + j * 24) + normal[0] * (j * 16 - 8),
                           y - direction[1] * (35 + j * 24) + normal[1] * (j * 16 - 8),
                           9, kind, c, a)
    elif kind == "comet":
        for k in range(7 + tier // 3):
            old = flight_point(kind, start, end, max(0.0, t - k * .028))
            star(surface, old[0], old[1], max(3, 12 - k), c if k % 2 else a)
        if tier >= 7:
            orbit(surface, x, y, 35, WHITE, beat * .4, 5, 2)
    elif kind == "rainbow":
        palette = ((255, 88, 130), GOLD, GREENISH, CYAN, (112, 111, 255), (190, 114, 255))
        for k, color in enumerate(palette):
            pygame.draw.arc(surface, color,
                            pygame.Rect(round(x - 28 - k * 2), round(y - 22 - k),
                                        56 + k * 4, 46 + k * 2), 0, math.pi, 2)
        if tier >= 7:
            star(surface, x, y - 27, 7, WHITE)
    elif kind == "paint":
        circle(surface, c, x, y, 19)
        for k in range(6 + tier // 2):
            ang = k * math.tau / (6 + tier // 2) + beat * .15
            spread = 21 + (k % 3) * 7
            circle(surface, (a, CYAN, GOLD)[k % 3],
                   x + math.cos(ang) * spread, y + math.sin(ang) * spread,
                   3 + k % 2)
        if tier >= 7:
            pygame.draw.ellipse(surface, c, (round(x - 36), round(y - 21), 72, 42), 2)
    elif kind == "disco":
        circle(surface, WHITE, x, y, 22)
        for j in range(-2, 3):
            line(surface, a, (x + j * 8, y - 21), (x + j * 8, y + 21), 1)
        orbit(surface, x, y, 33, c, beat, 4, 3)
        if tier >= 4:
            for j in range(3):
                beam_ang = beat * .3 + j * math.tau / 3
                line(surface, (CYAN, GOLD, c)[j], (x, y),
                     (x + 60 * math.cos(beam_ang), y + 60 * math.sin(beam_ang)), 2)
        if tier >= 7:
            box(surface, x, y, 42, a, 1)
    elif kind == "plasma":
        for k in range(3 + tier // 4):
            circle(surface, c if k % 2 else a, x, y,
                   13 + k * 8 + 3 * math.sin(beat + k), 2)
        if tier >= 7:
            for k in range(6):
                th = k * math.tau / 6 + beat * .2
                line(surface, WHITE, (x + 22 * math.cos(th), y + 22 * math.sin(th)),
                     (x + 41 * math.cos(th), y + 41 * math.sin(th)), 1)
    elif kind == "ninja":
        for k in range(3 if tier < 7 else 6):
            th = beat * 2 + k * math.tau / (3 if tier < 7 else 6)
            orbit_x = x + math.cos(th) * 21
            orbit_y = y + math.sin(th) * 21
            star(surface, orbit_x, orbit_y, 11, WHITE, 4, .25)
        if tier >= 4:
            line(surface, c, (x - 40, y - 40), (x + 40, y + 40), 2)
    elif kind == "galaxy":
        for j in range(12 + tier):
            angle = j * .55 + elapsed * .9
            rad = 4 + j * 2.7
            circle(surface, (WHITE, CYAN, c)[j % 3],
                   x + rad * math.cos(angle), y + rad * math.sin(angle),
                   1 + j % 3)
        if tier >= 7:
            pygame.draw.arc(surface, a, (round(x - 44), round(y - 22), 88, 44),
                            beat * .3, beat * .3 + 2.4, 2)
    elif kind == "gold":
        for k in range(5 + tier // 2):
            th = elapsed * 5 + k * 1.3
            px = x + math.cos(th) * (17 + k * 2)
            py = y + math.sin(th) * (8 + k * 3)
            pygame.draw.ellipse(surface, GOLD, (round(px - 5), round(py - 8),
                                              10, 16), 2)
        if tier >= 7:
            orbit(surface, x, y, 42, WHITE, beat, 7, 2)
    else:
        raise AssertionError(f"Missing choreography: {kind}")


GREENISH = (182, 255, 59)


def level_descriptions() -> tuple[str, ...]:
    return level_showcase(10)
