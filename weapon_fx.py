"""Distinct flight signatures for all 28 projectile families.

Pure geometry/config: testable without initializing the pygame display. The
renderer turns each motion, trail and impact style into its own animation.
"""
from __future__ import annotations

from dataclasses import dataclass
import math

from upgrades import THEMES


@dataclass(frozen=True)
class WeaponStyle:
    motion: str
    trail: str
    impact: str
    travel: float
    bend: float
    pitch: str


WEAPONS: dict[str, WeaponStyle] = {
    "chalk":     WeaponStyle("scratch", "powder", "dust", .22, 16, "shoot"),
    "confetti":  WeaponStyle("helix", "paper", "confetti", .27, 39, "party"),
    "ink":       WeaponStyle("lob", "drips", "ink", .31, 81, "splash"),
    "rubber":    WeaponStyle("bounce", "orbs", "rubber", .27, 42, "kick"),
    "laser":     WeaponStyle("direct", "laser", "laser", .11, 0, "laser"),
    "star":      WeaponStyle("helix", "twinkle", "stars", .23, 21, "chime"),
    "plane":     WeaponStyle("glide", "folds", "planes", .33, 58, "whoosh"),
    "firework":  WeaponStyle("rocket", "sparks", "fireworks", .32, 70, "party"),
    "explosion": WeaponStyle("lob", "smoke", "boom", .36, 61, "boom"),
    "football":  WeaponStyle("kick", "footprints", "goal", .29, 91, "kick"),
    "lightning": WeaponStyle("zigzag", "electric", "thunder", .13, 19, "electric"),
    "snow":      WeaponStyle("drift", "flakes", "blizzard", .44, 68, "chime"),
    "water":     WeaponStyle("lob", "drops", "splash", .34, 72, "splash"),
    "bubble":    WeaponStyle("float", "bubbles", "bubbles", .46, 38, "bubbles"),
    "meteor":    WeaponStyle("direct", "fire", "crater", .19, 0, "boom"),
    "crystal":   WeaponStyle("zigzag", "diamonds", "shatter", .26, 21, "chime"),
    "heart":     WeaponStyle("flutter", "hearts", "love", .34, 36, "chime"),
    "donut":     WeaponStyle("toss", "sprinkles", "donuts", .34, 73, "party"),
    "pizza":     WeaponStyle("toss", "slices", "pizza", .32, 65, "whoosh"),
    "rocket":    WeaponStyle("rocket", "thrusters", "launch", .24, 105, "whoosh"),
    "comet":     WeaponStyle("direct", "comet", "comet", .20, 0, "whoosh"),
    "rainbow":   WeaponStyle("arch", "rainbow", "prism", .39, 93, "chime"),
    "paint":     WeaponStyle("scratch", "paint", "paint", .24, 32, "splash"),
    "disco":     WeaponStyle("dance", "disco", "dance", .30, 48, "party"),
    "plasma":    WeaponStyle("pulse", "plasma", "pulse", .23, 26, "electric"),
    "ninja":     WeaponStyle("zigzag", "blades", "shurikens", .19, 18, "whoosh"),
    "galaxy":    WeaponStyle("spiral", "nebula", "vortex", .38, 47, "chime"),
    "gold":      WeaponStyle("bounce", "coins", "jackpot", .31, 39, "coins"),
}


def flight_point(kind: str, start: tuple[float, float],
                 end: tuple[float, float], progress: float,
) -> tuple[float, float]:
    """A moving projectile always hits the exact clicked point at progress=1."""
    style = WEAPONS[kind]
    t = max(0.0, min(1.0, progress))
    x, y = start[0] + (end[0] - start[0]) * t, start[1] + (end[1] - start[1]) * t
    dx, dy = end[0] - start[0], end[1] - start[1]
    length = max(1, math.hypot(dx, dy))
    nx, ny = -dy / length, dx / length
    envelope = math.sin(math.pi * t)
    b = style.bend
    m = style.motion
    lateral, lift = 0.0, 0.0
    if m == "scratch":
        lateral = envelope * b * math.sin(17 * math.pi * t)
    elif m == "helix":
        lateral = envelope * b * math.sin(8 * math.pi * t)
    elif m == "lob":
        lift = 4 * t * (1 - t) * b
    elif m == "bounce":
        lift = abs(math.sin(3 * math.pi * t)) * envelope * b
    elif m == "glide":
        lateral = b * envelope * math.cos(2 * math.pi * t)
        lift = 17 * envelope
    elif m == "rocket":
        lift = 4 * t * (1 - t) * b
        lateral = .27 * b * envelope * math.sin(5 * math.pi * t)
    elif m == "kick":
        lift = 4 * t * (1 - t) * b
        lateral = 9 * envelope * math.sin(4 * math.pi * t)
    elif m == "zigzag":
        lateral = envelope * b * math.sin(13 * math.pi * t)
    elif m == "drift":
        lateral = envelope * b * math.sin(3 * math.pi * t)
        lift = 25 * envelope
    elif m == "float":
        lateral = envelope * b * math.sin(5 * math.pi * t + .4)
        lift = 46 * envelope
    elif m == "flutter":
        lateral = envelope * b * math.sin(6 * math.pi * t)
        lift = 19 * envelope
    elif m == "toss":
        lift = 4 * t * (1 - t) * b
        lateral = .28 * b * envelope * math.sin(5 * math.pi * t)
    elif m == "arch":
        lift = b * envelope
    elif m == "dance":
        lateral = b * envelope * math.sin(8 * math.pi * t)
    elif m == "pulse":
        lateral = b * envelope * math.sin(15 * math.pi * t)
    elif m == "spiral":
        lateral = b * envelope * math.sin(10 * math.pi * t)
        lift = 20 * envelope * math.cos(10 * math.pi * t)
    return x + nx * lateral, y + ny * lateral - lift


def validate() -> None:
    assert set(WEAPONS) == {theme.projectile for theme in THEMES}
    assert len({(w.motion, w.trail, w.impact) for w in WEAPONS.values()}) == 28
    assert len({w.impact for w in WEAPONS.values()}) == 28
    assert all(.08 <= w.travel <= .5 and w.bend >= 0 for w in WEAPONS.values())


validate()
