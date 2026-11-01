"""280 permanent, individually purchasable visual upgrades (28 themes x 10)."""
from __future__ import annotations

from dataclasses import dataclass
from vocabulary import VERBS


Color = tuple[int, int, int]


@dataclass(frozen=True)
class Theme:
    title: str
    projectile: str
    color: Color
    accent: Color
    flavor: str


THEMES: tuple[Theme, ...] = (
    Theme("Kreideblitz", "chalk", (234, 236, 242), (100, 207, 247), "Kreidestaub auf der Zielscheibe"),
    Theme("Konfettikanone", "confetti", (253, 114, 159), (250, 220, 74), "Bunte Papierschnipsel"),
    Theme("Tintenspritzer", "ink", (95, 124, 242), (175, 135, 251), "Tintenkleckse und Tropfen"),
    Theme("Gummiball", "rubber", (255, 143, 76), (248, 221, 95), "Federnde Volltreffer"),
    Theme("Laser", "laser", (71, 244, 192), (86, 186, 255), "Neongrüne Lichtstrahlen"),
    Theme("Sternenstaub", "star", (255, 224, 99), (255, 151, 82), "Funkelnde Sterne"),
    Theme("Papierflieger", "plane", (245, 246, 251), (110, 187, 251), "Fliegende Papierkunst"),
    Theme("Feuerwerk", "firework", (255, 121, 101), (255, 231, 139), "Böllerfreies Feuerwerk"),
    Theme("Explosion", "explosion", (255, 91, 62), (253, 194, 65), "Comicartige KABOOM-Wolken"),
    Theme("Fußball", "football", (246, 249, 247), (66, 211, 166), "Runde Volltreffer ins Netz"),
    Theme("Gewitter", "lightning", (175, 160, 255), (255, 240, 129), "Knisternde Blitze"),
    Theme("Schneesturm", "snow", (213, 243, 255), (108, 202, 247), "Eiskalte Schneeflocken"),
    Theme("Wasserschlacht", "water", (70, 194, 255), (117, 231, 244), "Wasserfontänen und Tropfen"),
    Theme("Seifenblasen", "bubble", (190, 161, 255), (99, 220, 231), "Schillernde Luftblasen"),
    Theme("Meteoriten", "meteor", (255, 117, 74), (254, 221, 99), "Glühende Himmelsbrocken"),
    Theme("Kristallregen", "crystal", (139, 230, 246), (192, 142, 248), "Funkelnde Diamanten"),
    Theme("Herzchenhagel", "heart", (255, 113, 166), (255, 202, 221), "Herzen statt Patronen"),
    Theme("Donutwerfer", "donut", (242, 168, 114), (255, 137, 199), "Glasierte Donuts"),
    Theme("Pizzaschleuder", "pizza", (252, 198, 94), (243, 97, 91), "Heiße Käse-Pizza"),
    Theme("Raketenstart", "rocket", (255, 101, 104), (96, 203, 252), "Mini-Raketen über der Bühne"),
    Theme("Kometenschweif", "comet", (125, 201, 252), (212, 151, 255), "Leuchtende Kometen"),
    Theme("Regenbogen", "rainbow", (255, 125, 154), (110, 238, 184), "Bogenförmige Lichtspuren"),
    Theme("Farbexplosion", "paint", (125, 224, 122), (253, 121, 197), "Spritzige Farbkugeln"),
    Theme("Discokugel", "disco", (198, 219, 251), (251, 146, 227), "Spiegelglanz und Tanzlicht"),
    Theme("Plasmapuls", "plasma", (183, 99, 255), (89, 235, 249), "Elektrische Energieringe"),
    Theme("Ninja-Stern", "ninja", (164, 179, 200), (247, 109, 118), "Vierarmige Papiersterne"),
    Theme("Galaxienwirbel", "galaxy", (126, 129, 250), (248, 150, 224), "Kleine Spiralgalaxien"),
    Theme("Goldregen", "gold", (255, 212, 73), (247, 161, 82), "Klimpernde Goldmünzen"),
)


# Higher tiers don't just change color: the renderer adds corresponding
# tracer density, particles, shockwaves, additional volleys and screen pulse.
LEVELS: tuple[tuple[str, str], ...] = (
    ("Funke", "Ein markantes Projektil mit Mini-Treffer-Effekt"),
    ("Düsenantrieb", "Schnellerer Schuss mit leuchtender Spitze"),
    ("Leuchtspur", "Lange, farbige Nachziehspur"),
    ("Splitterregen", "Zusätzliche Funken beim Treffer"),
    ("Doppelschlag", "Zweiter farbiger Stoßring"),
    ("Wirbelwind", "Rotierende Nebengeschosse"),
    ("Schockwelle", "Große Welle über dem Schießstand"),
    ("Kettenreaktion", "Mehrere aufeinanderfolgende Effektwellen"),
    ("Himmelssturm", "Die komplette Bühne erstrahlt"),
    ("Finale", "Maximales Spezialfeuerwerk beim Volltreffer"),
)


@dataclass(frozen=True)
class Upgrade:
    id: str
    name: str
    description: str
    theme_index: int
    tier: int  # 1..10
    cost: int

    @property
    def theme(self) -> Theme:
        return THEMES[self.theme_index]


UPGRADES: tuple[Upgrade, ...] = tuple(
    Upgrade(
        id=f"{theme_index:02d}-{tier:02d}",
        name=f"{theme.title} · {LEVELS[tier - 1][0]}",
        description=f"{theme.flavor}. {LEVELS[tier - 1][1]}.",
        theme_index=theme_index,
        tier=tier,
        cost=int(round((12 + theme_index * 5) * (1.7 ** (tier - 1)))),
    )
    for tier in range(1, 11)
    for theme_index, theme in enumerate(THEMES)
)
UPGRADE_BY_ID: dict[str, Upgrade] = {u.id: u for u in UPGRADES}
PAGE_SIZE = 6


def shop_page(page: int) -> tuple[Upgrade, ...]:
    start = max(0, page) * PAGE_SIZE
    return UPGRADES[start : start + PAGE_SIZE]


def recommended_page(coins: int, owned: set[str]) -> int:
    """Default to an affordable unowned upgrade when one exists."""
    candidates = [(index, u) for index, u in enumerate(UPGRADES)
                  if u.id not in owned and u.cost <= coins]
    if candidates:
        return candidates[-1][0] // PAGE_SIZE
    return 0


def reward(streak: int, seconds_left: float) -> int:
    """Earn 30-82 coins. Purchases never cost real money."""
    return 30 + min(max(1, streak), 8) * 4 + int(max(0.0, seconds_left) * 4)


def validate() -> None:
    assert len(THEMES) == len(VERBS), "Exactly one projectile family per verb"
    assert len(UPGRADES) == len(VERBS) * 10
    assert len(UPGRADE_BY_ID) == len(UPGRADES)
    assert len({u.name for u in UPGRADES}) == len(UPGRADES)
    assert all(u.cost > 0 and 1 <= u.tier <= 10 for u in UPGRADES)
    assert all(len({u.cost for u in UPGRADES if u.theme_index == t}) == 10
               for t in range(len(THEMES)))


validate()
