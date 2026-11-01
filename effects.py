"""Gameplay effects for the 28 munitions. Pure data and rules, no pygame.

One equipped weapon is active. Its tier (1–10) scales a single effect.
Coin multipliers from that weapon are capped at ×4. Assisted answers
(a hint was already visible) pay half, do not advance a streak and do
not count as mastered.
"""
from __future__ import annotations

from dataclasses import dataclass


COIN_CAP = 4.0
MAX_ASSISTS_PER_VERB = 2
BOSS_MARKS = (7, 14, 21, 28)
BOSS_BASE_SECONDS = 9.0
BOSS_BASE_COINS = 150
# Stage 2 of a boss keeps at least this much time so the participle
# is readable even if the simple-past shot used the shared clock.
BOSS_STAGE_FLOOR = 3.5

# learned verbs → pressure. Speed is the peak horizontal px/s.
PRESSURE = {
    1: {"targets": 3, "speed": 0.0, "seconds": 5.0, "swap": False},
    2: {"targets": 3, "speed": 45.0, "seconds": 5.0, "swap": False},
    3: {"targets": 4, "speed": 70.0, "seconds": 5.0, "swap": False},
    4: {"targets": 4, "speed": 90.0, "seconds": 4.5, "swap": True},
}


def _tier(tier: int) -> int:
    return max(1, min(10, int(tier)))


def scaled(v1: float, v10: float, tier: int) -> float:
    t = _tier(tier)
    return v1 + (v10 - v1) * (t - 1) / 9.0


@dataclass(frozen=True)
class Effect:
    key: str
    family: str
    label: str
    v1: float
    v10: float
    v1b: float = 0.0
    v10b: float = 0.0
    v1c: float = 0.0
    v10c: float = 0.0
    assisted: bool = False
    charges: tuple[int, ...] | None = None

    def value(self, tier: int) -> float:
        return scaled(self.v1, self.v10, tier)

    def value_b(self, tier: int) -> float:
        t = _tier(tier)
        if self.key == "streak_milestone":
            return 4.0 if t >= 7 else 5.0
        if self.key == "heal":
            return 6.0 if t >= 9 else 5.0
        if self.key == "shield":
            return 2.0 if t >= 8 else 1.0
        return scaled(self.v1b, self.v10b, t)

    def value_c(self, tier: int) -> float:
        return scaled(self.v1c, self.v10c, tier)

    def charges_at(self, tier: int) -> int:
        t = _tier(tier)
        if self.charges:
            return int(self.charges[t - 1])
        if self.key == "quench":
            return int(round(scaled(1, 5, t)))
        if self.key == "shield":
            return 2 if t >= 8 else 1
        if self.key == "penalty":
            return 2 if t >= 8 else 1
        return 0

    def text(self, tier: int) -> str:
        return self.label.format(
            v=self.value(tier),
            b=self.value_b(tier),
            c=self.charges_at(tier),
            d=self.value_c(tier),
        )


# v = primary (often the number printed in the shop), b = second knob.
EFFECTS: dict[str, Effect] = {
    "chalk": Effect("hint_sentence", "hilfe", "Lückensatz nach {v:.1f} s", 3.5, 1.0, assisted=True),
    "confetti": Effect("streak_milestone", "serie", "+{v:.0f} Münzen alle {b:.0f} Treffer", 15, 120, 5, 4),
    "ink": Effect("fifty_fifty", "hilfe", "50:50 nach {v:.1f} s", 3.0, 1.2, assisted=True),
    "rubber": Effect("rebound", "schutz", "Nachschuss ×{c}, +{v:.1f} s", 0.0, 1.5,
                     charges=(1, 1, 1, 2, 2, 2, 3, 3, 3, 4)),
    "laser": Effect("aim", "praezision", "Zielfläche +{v:.0%}, Tempo −{b:.0%}", 0.08, 0.40, 0.10, 0.60),
    "star": Effect("time_bank", "zeit", "Zeitbank {v:.0%} bis {b:.0f} s", 0.10, 0.50, 2.0, 6.0),
    "plane": Effect("cheat_sheet", "hilfe", "Spickzettel nach {v:.1f} s", 3.0, 0.8, assisted=True),
    "firework": Effect("fever", "serie", "Fieber ab Combo {v:.0f} · {b:.0f} Fragen", 10, 5, 2, 5),
    "explosion": Effect("risk_shot", "risiko", "Timer −1 s, Münzen ×{v:.1f}", 1.5, 3.0),
    "football": Effect("penalty", "boss", "Elfmeter ×{c}, +{v:.0f} s", 1.0, 3.0),
    "lightning": Effect("chain_refresh", "boss", "Auffrischung {v:.0%}, +{b:.0f}", 0.20, 0.65, 15, 100),
    "snow": Effect("freeze", "zeit", "Timer {v:.1f} s eingefroren", 0.5, 2.5),
    "water": Effect("quench", "schutz", "Timeout-Schutz ×{c}", 1, 5),
    "bubble": Effect("shield", "schutz", "Schild {c}, neu nach {v:.0f}", 8, 3),
    "meteor": Effect("boss_breaker", "boss", "Boss ×{v:.1f}, +{b:.1f} s", 1.5, 4.0, 0.5, 3.0),
    "crystal": Effect("prism", "boss", "Muster nach {v:.1f} s", 3.0, 0.0, assisted=True),
    "heart": Effect("heal", "schutz", "+1 Leben alle {v:.0f}, max {b:.0f}", 10, 4, 5, 6),
    "donut": Effect("revenge", "muenzen", "Revanche +{v:.0%}", 0.25, 2.0),
    "pizza": Effect("express", "muenzen", "Trinkgeld +{v:.0f} in {b:.1f} s", 10, 60, 1.2, 2.5),
    "rocket": Effect("turbo_combo", "serie", "Serie +2 unter {v:.1f} s", 1.2, 2.5),
    "comet": Effect("momentum", "zeit", "+{v:.1f} s je Serie, max +{b:.1f} s", 0.10, 0.30, 0.5, 3.0),
    "rainbow": Effect("pattern_bridge", "hilfe", "Musterbrücke nach {v:.1f} s", 3.0, 0.8, assisted=True),
    "paint": Effect("paint_bomb", "hilfe", "Farbbombe {v:.0f} Münzen", 60, 10, assisted=True),
    "disco": Effect("combo_keep", "serie", "Serie bleibt zu {v:.0%}", 0.25, 0.75),
    "plasma": Effect("emp", "risiko", "EMP jede {v:.0f}. Frage", 6, 2),
    "ninja": Effect("bullseye", "praezision", "Zentrum {v:.0f} px, +{b:.0%}", 18, 30, 0.30, 2.0),
    "galaxy": Effect("gravity", "zeit", "Zeitlupe ×{v:.2f} ab {b:.1f} s", 0.85, 0.50, 1.5, 2.5, 0.10, 0.40),
    "gold": Effect("combo_mult", "muenzen", "+{v:.0%} Münzen je Combo", 0.05, 0.20),
}


def effect_for(projectile: str | None) -> Effect | None:
    if not projectile:
        return None
    return EFFECTS.get(projectile)


def pressure_level(learned: int) -> int:
    if learned >= 21:
        return 4
    if learned >= 14:
        return 3
    if learned >= 7:
        return 2
    return 1


def base_coins(streak: int, seconds_left: float) -> int:
    """Same curve the shop was balanced against: 30–82 on a normal hit."""
    return 30 + min(max(1, streak), 8) * 4 + int(max(0.0, seconds_left) * 4)


def compute_reward(
    streak: int,
    seconds_left: float,
    *,
    fx: Effect | None = None,
    tier: int = 1,
    assisted: bool = False,
    fever: bool = False,
    boss: bool = False,
    boss_clear: bool = False,
    revenge: bool = False,
    express: bool = False,
    center_hit: bool = False,
    milestone: bool = False,
    extra_mult: float = 1.0,
) -> int:
    """Coins for one resolved shot. Multipliers clamp at COIN_CAP before the assist halving."""
    if boss:
        base = float(BOSS_BASE_COINS if boss_clear else 0)
        mult = fx.value(tier) if fx and fx.key == "boss_breaker" else 1.0
        mult = min(COIN_CAP, max(0.0, mult * extra_mult))
        if assisted:
            mult *= 0.5
        return int(base * mult)

    base = float(base_coins(streak, seconds_left))
    mult = 1.0
    flat = 0.0
    if fx is not None:
        key = fx.key
        if key == "risk_shot":
            mult *= fx.value(tier)
        elif key == "combo_mult":
            mult *= 1.0 + fx.value(tier) * min(10, max(0, streak))
        elif key == "revenge" and revenge:
            mult *= 1.0 + fx.value(tier)
        elif key == "penalty":
            mult *= 1.10
        elif key == "bullseye" and center_hit:
            mult *= 1.0 + fx.value_b(tier)
        elif key == "express" and express:
            flat += fx.value(tier)
        elif key == "streak_milestone" and milestone:
            flat += fx.value(tier)
    if fever:
        mult *= 2.0
    mult *= extra_mult
    mult = min(COIN_CAP, max(0.0, mult))
    if assisted:
        mult *= 0.5
        flat *= 0.5
    return max(0, int(base * mult + flat))


def consume_timer(fx: Effect | None, tier: int, question_age: float,
                  time_left: float, dt: float) -> float:
    """How many seconds of the question clock elapse this frame."""
    if fx and fx.key == "freeze" and question_age < fx.value(tier):
        return 0.0
    step = dt
    if fx and fx.key == "gravity" and time_left <= fx.value_b(tier) + 1e-9:
        step *= max(0.05, fx.value(tier))
    return step


def deposit_time_bank(bank: float, seconds_left: float, fx: Effect | None, tier: int) -> float:
    if not fx or fx.key != "time_bank":
        return bank
    return min(fx.value_b(tier), bank + max(0.0, seconds_left) * fx.value(tier))


def question_seconds(learned: int, fx: Effect | None, tier: int, streak: int,
                     fever: bool, suppressed: bool) -> float:
    band = 1 if suppressed else pressure_level(learned)
    seconds = PRESSURE[band]["seconds"]
    if fx and fx.key == "momentum" and streak > 0:
        seconds += min(fx.value_b(tier), streak * fx.value(tier))
    if fever:
        seconds += 1.0
    if fx and fx.key == "risk_shot":
        seconds -= 1.0
    # Explosion on the finale band would otherwise dip to 3.5s; never below 3.
    return max(3.0, seconds)


def boss_seconds(fx: Effect | None, tier: int) -> float:
    extra = fx.value_b(tier) if fx and fx.key == "boss_breaker" else 0.0
    return BOSS_BASE_SECONDS + extra


def hint_delay(fx: Effect | None, tier: int, *, boss: bool) -> float | None:
    """Seconds until a passive hint appears. None = this weapon does not auto-hint."""
    if fx is None:
        return None
    if fx.key in ("hint_sentence", "fifty_fifty", "cheat_sheet", "pattern_bridge"):
        return max(0.0, fx.value(tier))
    if fx.key == "prism":
        if boss:
            return max(0.0, fx.value(tier))
        if _tier(tier) >= 6:
            return 2.5
        return None
    return None


def hint_assists(fx: Effect | None, *, boss: bool, boss_stage: str | None) -> bool:
    """True when a visible hint should mark the answer as assisted."""
    if fx is None or not fx.assisted:
        return False
    # The pattern shown on the simple-past half of a boss is free teaching.
    if fx.key == "prism" and boss and boss_stage == "past":
        return False
    return True


def target_speed_scale(fx: Effect | None, tier: int) -> float:
    if fx and fx.key == "aim":
        return max(0.2, 1.0 - fx.value_b(tier))
    if fx and fx.key == "gravity":
        return max(0.2, 1.0 - fx.value_c(tier))
    return 1.0


def hitbox_scale(fx: Effect | None, tier: int) -> float:
    if fx and fx.key == "aim":
        return 1.0 + fx.value(tier)
    return 1.0


def paint_cost(fx: Effect | None, tier: int, streak: int) -> int | None:
    if not fx or fx.key != "paint_bomb":
        return None
    if _tier(tier) >= 10 and streak >= 5:
        return 0
    return max(0, int(round(fx.value(tier))))


def emp_interval(fx: Effect | None, tier: int) -> int:
    if not fx or fx.key != "emp":
        return 0
    return max(2, int(round(fx.value(tier))))


def wrong_indices(correct: int, count: int, eliminated: set[int] | None = None) -> list[int]:
    gone = eliminated or set()
    return [i for i in range(count) if i != correct and i not in gone]


def pick_elimination(correct: int, count: int, rng, eliminated: set[int] | None = None) -> int:
    pool = wrong_indices(correct, count, eliminated)
    if not pool:
        raise RuntimeError("no wrong target left")
    return int(rng.choice(pool))


def first_miss_action(outcome: str, fx_key: str | None, charges: int,
                      rebound_used: bool, boss_retries: int) -> str:
    if outcome == "correct":
        return "close"
    if outcome != "timeout" and fx_key == "rebound" and charges > 0 and not rebound_used:
        return "rebound"
    if outcome != "timeout" and fx_key == "penalty" and boss_retries > 0:
        return "penalty"
    return "close"


def protection(outcome: str, fx_key: str | None, shield: int, quench: int) -> str | None:
    """Life-savers. They never turn the verb into a correct answer."""
    if outcome == "correct":
        return None
    if fx_key == "shield" and shield > 0:
        return "shield"
    if outcome == "timeout" and fx_key == "quench" and quench > 0:
        return "quench"
    return None


def streak_after_success(streak: int, fx: Effect | None, tier: int,
                         shot_age: float, assisted: bool) -> int:
    if assisted:
        return streak
    gain = 1
    if fx and fx.key == "turbo_combo" and shot_age < fx.value(tier):
        gain = 2
    return streak + gain


def streak_after_fail(streak: int, fx: Effect | None, tier: int) -> int:
    if fx and fx.key == "combo_keep":
        return int(streak * fx.value(tier))
    return 0


def milestone_crossed(old: int, new: int, fx: Effect | None, tier: int) -> bool:
    if not fx or fx.key != "streak_milestone" or new <= old:
        return False
    interval = max(1, int(fx.value_b(tier)))
    return new // interval > old // interval


def heal_lives(old: int, new: int, fx: Effect | None, tier: int, lives: int) -> int:
    if not fx or fx.key != "heal" or new <= old:
        return lives
    step = max(1, int(round(fx.value(tier))))
    gained = new // step - old // step
    cap = int(fx.value_b(tier))
    return min(cap, lives + max(0, gained))


def fever_duration(streak: int, fx: Effect | None, tier: int) -> int | None:
    if not fx or fx.key != "fever":
        return None
    trigger = max(1, int(round(fx.value(tier))))
    if streak >= trigger:
        return max(1, int(round(fx.value_b(tier))))
    return None


def shield_regen_step(fx: Effect | None, tier: int) -> int:
    if not fx or fx.key != "shield":
        return 0
    return max(1, int(round(fx.value(tier))))


def strength(fx: Effect, tier: int) -> float:
    """Higher means a stronger effect. Used to check that tiers never get worse."""
    key = fx.key
    if key in ("hint_sentence", "fifty_fifty", "cheat_sheet", "pattern_bridge", "prism"):
        return -fx.value(tier)
    if key == "gravity":
        return -fx.value(tier) + fx.value_b(tier) + fx.value_c(tier)
    if key in ("paint_bomb", "emp"):
        return -fx.value(tier)
    if key == "heal":
        return -fx.value(tier) + fx.value_b(tier)
    if key == "shield":
        return -fx.value(tier) + fx.value_b(tier)
    if key == "firework" or key == "fever":
        return -fx.value(tier) + fx.value_b(tier)
    return fx.value(tier) + fx.value_b(tier) + fx.value_c(tier) + fx.charges_at(tier)


def is_revenge(infinitive: str, missed: set[str], stats: dict) -> bool:
    if infinitive in missed:
        return True
    entry = stats.get(infinitive) or {}
    try:
        return int(entry.get("wrong", 0)) > 0
    except (TypeError, ValueError):
        return False
