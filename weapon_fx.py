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
    if kind == "rocket":
        # A literal three-act launch: rise -> scanning hover -> heat-seeking dive.
        # The rocket is aimed at the point that was clicked, never a random dummy.
        sx, sy = start
        tx, ty = end
        launch_y = sy - 285
        if t <= .24:
            u = t / .24
            return sx + 14 * math.sin(math.pi * u), sy + (launch_y - sy) * u
        if t <= .57:
            u = (t - .24) / .33
            return sx + 43 * math.sin(math.tau * u), launch_y - 18 * math.sin(math.pi * u)
        u = min(1.0, (t - .57) / .43)
        inv = 1 - u
        # Quadratic Bezier: the nose turns toward the selected answer.
        cx, cy = sx + (tx - sx) * .38 + 90, min(launch_y, ty) - 85
        return (inv * inv * sx + 2 * inv * u * cx + u * u * tx,
                inv * inv * launch_y + 2 * inv * u * cy + u * u * ty)
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


@dataclass(frozen=True)
class Performance:
    """A distinct 3-act animation; higher levels unlock the dramatic variations."""
    seconds: float
    launch: str
    chase: str
    finale: str


# Descriptions are intentionally unique: the designs are used in the game and
# documented in the README, not just cosmetic names for identical particles.
PERFORMANCES: dict[str, Performance] = {
    "chalk": Performance(.73, "Kreide bricht aus der Halterung", "Zickzack-Schriftspur und Staub", "Die Zielscheibe wird durchgestrichen"),
    "confetti": Performance(1.01, "Papierkapsel platzt auf", "Farbige Spirale aus Konfetti", "Konfettiregen und zwei Zugaben"),
    "ink": Performance(1.12, "Ein Tintenballon wird aufgezogen", "Tropfender Tintenklecks fliegt im Bogen", "Große Kleckse und kleine Spritzer"),
    "rubber": Performance(.95, "Flummi wird zusammengedrückt", "Drei elastische Hüpfer", "Prallender Ball und Gummiring"),
    "laser": Performance(.56, "Ladeglühen am Laser", "Präziser dünner Lichtstrahl", "Kreuzförmiger Neonblitz"),
    "star": Performance(.92, "Ein Stern beginnt zu funkeln", "Sternschnuppe mit Satelliten", "Sternennebel und funkelnde Spitzen"),
    "plane": Performance(1.21, "Papierflieger faltet seine Flügel", "Gleitflug mit Rückenwind", "Mini-Flieger ziehen Kreise"),
    "firework": Performance(1.46, "Zündschnur glimmt", "Feuerwerksrakete steigt auf", "Mehrstufige bunte Feuerwerksblüten"),
    "explosion": Performance(1.20, "Cartoon-Bombe zündet", "Schwere Kugel mit Rauchfahne", "KABOOM-Stoßwellen und Splitter"),
    "football": Performance(1.13, "Anstoß an der Torlinie", "Rotierender Fußball im hohen Bogen", "Tor-Netz wackelt und Bälle fliegen"),
    "lightning": Performance(.67, "Elektrostatik sammelt sich", "Blitz springt in Zickzacks", "Verzweigte, pulsierende Blitze"),
    "snow": Performance(1.27, "Eisnebel formt eine Schneeflocke", "Langsam schwebender Schneewirbel", "Wirbelsturm aus Schneekristallen"),
    "water": Performance(1.17, "Wasserballon füllt sich", "Schwungvoller Bogen mit Tropfen", "Schwall, Wasserfontänen und Tropfen"),
    "bubble": Performance(1.38, "Seifenblase wird aufgepustet", "Leichte Blasen steigen schwankend", "Blasenplatzer mit schimmernden Ringen"),
    "meteor": Performance(.84, "Feuriger Stein stürzt vom Himmel", "Glühender Schweif mit Funken", "Meteoritenkrater mit Trümmerregen"),
    "crystal": Performance(1.03, "Kristall lädt seinen Facettenglanz", "Rotierender Diamant mit Prismenspuren", "Splitterfächer aus farbigen Kristallen"),
    "heart": Performance(1.09, "Herz beginnt zu schlagen", "Flatternde Herzen schweben", "Herzregen und pulsierende Konturen"),
    "donut": Performance(1.12, "Donut wird in Rotation versetzt", "Zuckerglasur wirbelt durch die Luft", "Streusel-Konfetti und Donut-Ringe"),
    "pizza": Performance(1.02, "Pizzascheibe hebt ab", "Rotierendes Pizzastück im Wurfbogen", "Käseschnüre und Peperonikonfetti"),
    "rocket": Performance(2.23, "Rakete startet senkrecht mit Triebwerk", "Radar sucht, erfasst und verfolgt das angeklickte Ziel", "Raketeneinschlag mit Rauch und gestaffelten Explosionen"),
    "comet": Performance(1.12, "Ein Komet entzündet sich", "Heller Kern mit langem Schweif", "Gleißende Kometenstücke zerfallen"),
    "rainbow": Performance(1.36, "Prismastrahl öffnet sich", "Bunter Regenbogen spannt sich", "Siebenfarbige Wellen am Ziel"),
    "paint": Performance(.99, "Farbpatrone wird abgeschossen", "Tropfen ziehen Spritzspuren", "Verschiedene Farbflecken bedecken das Ziel"),
    "disco": Performance(1.14, "Discokugel wird beleuchtet", "Fliegender Spiegelball mit Lichtkegeln", "Tanzende Lichtstrahlen und Farbblitze"),
    "plasma": Performance(1.05, "Plasmafeld lädt sich auf", "Pulsierendes Plasmageschoss", "Konzentrierte Energieringe und Funken"),
    "ninja": Performance(.92, "Wurfstern schnappt aus der Hand", "Schnell rotierender Shuriken in Zickzacks", "Viele kleine Wurfsterne fliegen auseinander"),
    "galaxy": Performance(1.46, "Ein Sternennebel kondensiert", "Umlaufende Sterne spiralen zum Ziel", "Galaktischer Wirbel mit Sternensturm"),
    "gold": Performance(1.07, "Eine Münze wird hochgeschnippt", "Überschlagender Münzregen", "Goldene Jackpot-Fontäne"),
}


def flight_duration(kind: str, tier: int) -> float:
    """Long cinematic shots never penalize reaction time after mouse click."""
    return PERFORMANCES[kind].seconds + min(10, max(0, tier)) * .015


def level_showcase(tier: int) -> tuple[str, ...]:
    """Each tier actually adds a visual feature, not just a higher store price."""
    effects = ("Projektil", "Leuchtspur", "Begleitfunken", "Spezialeffekt",
               "Nebengeschoss", "Orbits", "Signatur-Welle", "Nachhall",
               "Bühnenlicht", "Finale")
    return effects[:max(1, min(int(tier), 10))]

def validate() -> None:
    assert set(WEAPONS) == {theme.projectile for theme in THEMES}
    assert len({(w.motion, w.trail, w.impact) for w in WEAPONS.values()}) == 28
    assert len({w.impact for w in WEAPONS.values()}) == 28
    assert all(.08 <= w.travel <= .5 and w.bend >= 0 for w in WEAPONS.values())
    assert set(PERFORMANCES) == set(WEAPONS)
    assert len({(a.launch, a.chase, a.finale) for a in PERFORMANCES.values()}) == 28
    assert all(.5 <= flight_duration(k, 1) <= 2.7 for k in WEAPONS)
    assert len(level_showcase(1)) == 1 and len(level_showcase(10)) == 10


validate()
