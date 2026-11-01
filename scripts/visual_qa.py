"""Headless screenshot capture and regression guard for the shooting-range UI."""
from __future__ import annotations
import os
from pathlib import Path
import pygame
from game import Game, HitEffect, VERBS, UPGRADES

OUT = Path(os.environ.get("SCREENSHOT_DIR", "visual-preview"))
OUT.mkdir(exist_ok=True, parents=True)

def screenshot(game: Game, state: str) -> None:
    game.render()
    png = OUT / f"{state}.png"
    pygame.image.save(game.canvas, str(png))
    print("captured", png, png.stat().st_size)
    if state in ("play", "shop"):
        for rect in [
            pygame.Rect(88, 20, 340, 58),
            pygame.Rect(36, 100, 690, 37) if state == "shop"
            else pygame.Rect(410, 113, 430, 120)
        ]:
            sample = game.canvas.subsurface(rect)
            pale = 0
            for x in range(0, rect.w, 2):
                for y in range(0, rect.h, 2):
                    r, g, b = sample.get_at((x, y))[:3]
                    if r > 222 and g > 222 and b > 222:
                        pale += 1
            frac = pale / max(1, ((rect.w + 1) // 2) * ((rect.h + 1) // 2))
            assert frac < .26, f"Pale slab in {state}: {rect} ({frac:.2%})"

def main() -> None:
    game = Game()
    game.sound_on = False
    game.mouse = (-99, -99)
    game.time_elapsed = 4.2
    screenshot(game, "menu")

    game.new_run()
    game.phase = "play"
    game.verb = next(v for v in VERBS if v.infinitive == "put")
    game.options = ("putted", "put", "putt")
    game.correct_index = 1
    game.question_age = 1.7
    game.time_left = 3.1
    game.correct_count = 3
    game.streak = 3
    game.coins = 348
    game.active_round = next(u for u in UPGRADES if u.theme.projectile == "water" and u.tier == 9)
    screenshot(game, "play")

    game.phase = "impact"
    game.hit_effects = [HitEffect("football", 640, 352, 9, .34, 1.05)]
    game.outcome = "correct"
    screenshot(game, "impact")
    game.hit_effects.clear()

    game.phase = "shop"
    game.coins = 294
    game.correct_count = 2
    game.page = 28
    game.trial_candidate = next(u for u in UPGRADES if u.theme.projectile == "water" and u.tier == 9)
    game.toast = ""
    screenshot(game, "shop")

    game.phase = "end"
    game.completed = True
    game.correct_count = len(VERBS)
    game.bonus_awarded = 1800
    screenshot(game, "victory")
    pygame.quit()

if __name__ == "__main__":
    main()
