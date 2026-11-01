"""Headless screenshot capture and regression guard for the shooting-range UI."""
from __future__ import annotations
import os
from pathlib import Path
import pygame
from game import Game, HitEffect, BG, PANEL, WHITE, VERBS, UPGRADES, THEMES, draw_symbol
from weapon_fx import flight_duration
from weapon_visuals import trail as draw_weapon_trail
from weapon_choreography import draw_flight_choreography

OUT = Path(os.environ.get("SCREENSHOT_DIR", "visual-preview"))
OUT.mkdir(exist_ok=True, parents=True)


def screenshot(game: Game, state: str) -> None:
    game.render()
    png = OUT / f"{state}.png"
    pygame.image.save(game.canvas, str(png))
    print("captured", png, png.stat().st_size)

    # Test for broad unreadable white rectangles created by the old BLEND_ADD bug.
    # White glyphs are sparse; rectangles would light up >30% of these regions.
    if state in ("play", "shop", "shop_owned", "rocket_search", "rocket_lock"):
        for rect in [pygame.Rect(88, 20, 340, 58),
                     pygame.Rect(36, 100, 690, 37) if state.startswith("shop")
                     else pygame.Rect(410, 113, 430, 120)]:
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
    # Explicit screenshot states for visual comparison to supplied mockups.
    game = Game()
    game.sound_on = False
    game.mouse = (-99, -99)
    game.time_elapsed = 4.2
    screenshot(game, "menu")

    game.new_run()
    game.phase = "play"
    game.verb = next(x for x in VERBS if x.infinitive == "put")
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

    # The first time a player sees the catalog it must start on level 1.
    rocket = next(u for u in UPGRADES if u.theme.projectile == "rocket" and u.tier == 10)
    game.active_round = rocket
    game.phase = "flight"
    game.outcome = "correct"
    game.time_left = 2.7
    game.shot_from = (640, 588)
    game.shot_to = (330, 440)
    game.flight_seconds = flight_duration("rocket", 10)
    game.flight_time = game.flight_seconds * .43
    screenshot(game, "rocket_search")
    game.flight_time = game.flight_seconds * .83
    screenshot(game, "rocket_lock")

    game.phase = "shop"
    game.coins = 294
    game.correct_count = 2
    game.page = 0
    game.shop_view = "all"
    game.trial_candidate = next(u for u in UPGRADES if u.theme.projectile == "water" and u.tier == 9)
    game.toast = ""
    screenshot(game, "shop")

    game.owned = {UPGRADES[3].id, UPGRADES[19].id, rocket.id}
    game.equipped = rocket.id
    game.shop_view = "owned"
    game.page = 0
    screenshot(game, "shop_owned")

    # Every family is visible at high level in a compact contact sheet. The
    # frames avoid the old full-screen flash while keeping different shapes.
    tile_w, tile_h = 240, 185
    cols, rows = 7, 4
    sheet = pygame.Surface((cols * tile_w, rows * tile_h))
    font = game.font(13, False, "label")
    for index, theme in enumerate(THEMES):
        tile = pygame.Surface((tile_w, tile_h))
        tile.fill((9, 15, 32))
        start, end = (120, 169), (112, 78)
        progress = .97 if theme.projectile == "rocket" else .84
        draw_weapon_trail(tile, theme.projectile, 9, start, end, progress, 3.4, draw_symbol)
        draw_flight_choreography(tile, theme.projectile, 9, start, end, progress, 3.4, draw_symbol)
        caption = font.render(theme.title[:23], True, WHITE)
        tile.blit(caption, caption.get_rect(center=(120, 16)))
        col, row = index % cols, index // cols
        sheet.blit(tile, (col * tile_w, row * tile_h))
    sheet_path = OUT / "weapons_contact_sheet.png"
    pygame.image.save(sheet, str(sheet_path))
    print("captured", sheet_path, sheet_path.stat().st_size)

    game.phase = "end"
    game.completed = True
    game.correct_count = len(VERBS)
    game.bonus_awarded = 1800
    screenshot(game, "victory")
    pygame.quit()


if __name__ == "__main__":
    main()
