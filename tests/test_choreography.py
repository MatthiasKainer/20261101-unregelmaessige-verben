"""Regression checks for the cinematic ammunition, timing and persistent shop."""
import math
import random
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from upgrades import UPGRADES, PAGE_SIZE
from weapon_fx import PERFORMANCES, WEAPONS, flight_duration, flight_point, level_showcase


class PerformanceTests(unittest.TestCase):
    def test_all_28_shots_have_unique_three_act_scripts(self):
        self.assertEqual(len(PERFORMANCES), 28)
        self.assertEqual(set(PERFORMANCES), set(WEAPONS))
        self.assertEqual(len({(x.launch, x.chase, x.finale) for x in PERFORMANCES.values()}), 28)
        for kind, act in PERFORMANCES.items():
            with self.subTest(kind=kind):
                self.assertTrue(act.launch and act.chase and act.finale)
                self.assertGreater(flight_duration(kind, 1), .5)
                self.assertLess(flight_duration(kind, 10), 2.8)

    def test_rocket_starts_climbs_scans_locks_and_homes(self):
        start = (640, 707)
        targets = ((320, 430), (950, 510), (640, 360))
        for end in targets:
            with self.subTest(target=end):
                self.assertEqual(flight_point("rocket", start, end, 0), start)
                ascent = flight_point("rocket", start, end, .24)
                scanning = flight_point("rocket", start, end, .43)
                homing = flight_point("rocket", start, end, .82)
                self.assertLess(ascent[1], start[1] - 250)  # vertical motor stage
                self.assertAlmostEqual(ascent[0], start[0], delta=2)
                self.assertLess(scanning[1], start[1] - 260)
                self.assertGreater(math.dist(scanning, end), 20)
                self.assertLess(math.dist(homing, end), math.dist(scanning, end) + 90)
                self.assertEqual(flight_point("rocket", start, end, 1), end)
        self.assertGreater(flight_duration("rocket", 1), 2.0)

    def test_all_28_trajectories_end_at_click_and_are_not_same(self):
        a, b = (640, 707), (300, 390)
        for kind in PERFORMANCES:
            with self.subTest(kind=kind):
                self.assertEqual(flight_point(kind, a, b, 0), a)
                x, y = flight_point(kind, a, b, 1)
                self.assertAlmostEqual(x, b[0], places=5)
                self.assertAlmostEqual(y, b[1], places=5)
        signature = {kind: tuple(round(v, 2) for t in (.21, .49, .82)
                                 for v in flight_point(kind, a, b, t))
                     for kind in PERFORMANCES}
        self.assertGreaterEqual(len(set(signature.values())), 12)

    def test_levels_add_ten_consecutive_visual_upgrades(self):
        for tier in range(1, 11):
            with self.subTest(tier=tier):
                current = level_showcase(tier)
                self.assertEqual(len(current), tier)
                self.assertEqual(current, level_showcase(10)[:tier])
        self.assertGreater(flight_duration("rocket", 10), flight_duration("rocket", 1))

    def test_store_sorted_by_level_then_ammo_family(self):
        self.assertEqual(UPGRADES[0].tier, 1)
        self.assertEqual(UPGRADES[-1].tier, 10)
        self.assertEqual(len(UPGRADES), 280)
        self.assertEqual([u.tier for u in UPGRADES], sorted(u.tier for u in UPGRADES))
        self.assertEqual(PAGE_SIZE, 6)
        self.assertEqual({u.tier for u in UPGRADES[:PAGE_SIZE]}, {1})


try:
    import pygame
    from game import Game, STARTING_LIVES
except ImportError:
    pygame = None


@unittest.skipUnless(pygame, "requires pygame on CI")
class LiveGameTests(unittest.TestCase):
    def light_game(self):
        game = Game.__new__(Game)
        game.rng = random.Random(14)
        game.coins = 10_000
        game.owned = set()
        game.equipped = None
        game.shop_view = "all"
        game.page = 0
        game.progress = {"coins": 0, "owned": [], "equipped": None,
                         "runs": 0, "best": 0, "completions": 0,
                         "total_hits": 0, "best_mistakes": None,
                         "shop_view": "all", "shop_page": 0, "owned_page": 0,
                         "sound_on": False}
        game.sound_on = False
        game.sound = lambda _: None
        game.flash_message = lambda _: None
        game.save_progress = lambda: None
        game.trial_pending = None
        game.particles = []
        game.rings = []
        game.hit_effects = []
        game.flight_trail = []
        game.shake = game.flash = game.time_elapsed = game.toast_age = 0
        game.new_run()
        return game

    def test_timer_stops_at_click_until_cinematic_lands(self):
        game = self.light_game()
        upgrade = next(u for u in UPGRADES if u.theme.projectile == "rocket" and u.tier == 10)
        game.active_round = upgrade
        game.time_left = .20
        game.register_shot(game.correct_index, (330, 438))
        self.assertEqual(game.phase, "flight")
        self.assertGreater(game.flight_seconds, 2.3)
        game.register_shot(None, (950, 450))  # no second click
        for _ in range(43):
            game.update(.05)
        self.assertEqual(game.phase, "flight")
        self.assertAlmostEqual(game.time_left, .20, delta=.00001)
        self.assertEqual(game.lives, STARTING_LIVES)
        self.assertEqual(game.deck.attempts, 0)
        for _ in range(10):
            game.update(.05)
        self.assertEqual(game.phase, "impact")
        self.assertAlmostEqual(game.time_left, .20)
        self.assertEqual(game.deck.attempts, 1)

    def test_all_shop_opens_on_page_one_and_remembers_navigation(self):
        game = self.light_game()
        self.assertEqual(game.page, 0)
        game.change_shop_page(3)
        self.assertEqual(game.page, 3)
        game.start_shop()
        self.assertEqual(game.page, 3)
        self.assertEqual(game.shop_page_items()[0], UPGRADES[18])
        game.set_shop_view("owned")
        self.assertEqual(game.page, 0)
        game.set_shop_view("all")
        self.assertEqual(game.page, 3)
        game.change_shop_page(-1)
        self.assertEqual(game.page, 2)

    def test_rebuy_free_and_previous_purchases_selectable(self):
        game = self.light_game()
        purchase = UPGRADES[19]
        game.buy_or_equip(purchase)
        self.assertEqual(game.equipped, purchase.id)
        self.assertIn(purchase.id, game.owned)
        coins_after_purchase = game.coins
        game.trial_pending = UPGRADES[-1].id
        game.set_shop_view("owned")
        self.assertIn(purchase, game.shop_page_items())
        game.equipped = None
        game.buy_or_equip(purchase)
        self.assertEqual(game.coins, coins_after_purchase)
        self.assertIsNone(game.trial_pending)
        self.assertEqual(game.equipped, purchase.id)
        from vocabulary import MasteryDeck
        game.deck = MasteryDeck(random.Random(14))
        game.start_question()
        self.assertEqual(game.active_round.id, purchase.id)

    def test_shop_page_and_owned_items_survive_restart(self):
        game = self.light_game()
        game.owned.update([UPGRADES[1].id, UPGRADES[25].id])
        game.equipped = UPGRADES[25].id
        game.page = 4
        with tempfile.TemporaryDirectory() as folder:
            with patch("game.save_folder", return_value=Path(folder)):
                game.save_progress = Game.save_progress.__get__(game, Game)
                game.save_progress()
                loaded = Game.load_progress(game)
                self.assertEqual(loaded["shop_page"], 4)
                self.assertEqual(loaded["shop_view"], "all")
                self.assertEqual(loaded["equipped"], UPGRADES[25].id)
                self.assertEqual(set(loaded["owned"]), game.owned)
                game.set_shop_view("owned")
                loaded = Game.load_progress(game)
                self.assertEqual(loaded["shop_page"], 4)
                self.assertEqual(loaded["owned_page"], 0)
                self.assertEqual(loaded["shop_view"], "owned")

    def test_28_ammo_types_draw_bounded_distinct_shows_each_level(self):
        from game import draw_symbol, BG
        from weapon_choreography import draw_flight_choreography
        surface = pygame.Surface((1280, 720))
        results = {}
        for kind in PERFORMANCES:
            surfaces = []
            for tier in (1, 4, 7, 10):
                surface.fill(BG)
                draw_flight_choreography(surface, kind, tier,
                                        (640, 680), (490, 420), .72, 2.5, draw_symbol)
                surfaces.append(pygame.image.tobytes(surface, "RGB"))
            results[kind] = len({hash(b) for b in surfaces})
        self.assertTrue(all(n == 4 for n in results.values()), results)


if __name__ == "__main__":
    unittest.main()
