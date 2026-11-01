"""Exercise every weapon's real pygame renderer before packaging on Windows."""
import random
import unittest

try:
    import pygame
except ImportError:
    pygame = None


@unittest.skipUnless(pygame, "pygame-ce is installed in the Windows CI job")
class VisualTests(unittest.TestCase):
    def test_every_family_draws_a_shot_and_impact_without_crashing(self):
        from game import draw_symbol
        from weapon_visuals import impact, trail
        from weapon_fx import WEAPONS
        # No physical display, sound hardware or external assets required.
        surface = pygame.Surface((1280, 720))
        for kind in WEAPONS:
            with self.subTest(kind=kind):
                surface.fill((13, 20, 39))
                for fraction in (.1, .46, 1.0):
                    trail(surface, kind, 4, (640, 700), (910, 410), fraction,
                          1.3, draw_symbol)
                for age in (0.05, 0.35, 0.68):
                    impact(surface, kind, 910, 410, age, 7, draw_symbol)
                self.assertNotEqual(pygame.transform.average_color(surface,
                                    pygame.Rect(620, 220, 560, 470))[:3], (13, 20, 39))

    def test_completion_bonus_is_paid_only_once_in_game(self):
        from game import Game
        from vocabulary import MasteryDeck, VERBS
        deck = MasteryDeck(random.Random(7))
        while not deck.complete:
            deck.next()
            deck.record(True)
        game = Game.__new__(Game)
        game.deck = deck
        game.correct_count = len(VERBS)
        game.coins = 300
        game.progress = {"best": 27, "total_hits": 27,
                         "completions": 0, "best_mistakes": None}
        game.phase = "reveal"
        game.hit_effects = []
        game.flash = 0
        game.sound = lambda _: None
        game.save_progress = lambda: None
        game.end_run()
        self.assertEqual(game.phase, "end")
        self.assertTrue(game.completed)
        self.assertEqual(game.coins, 2100)
        self.assertEqual(game.progress["completions"], 1)
        game.end_run()
        self.assertEqual(game.coins, 2100)
        self.assertEqual(game.progress["completions"], 1)


    def test_game_flow_retries_and_completes_with_decreasing_bonus(self):
        from game import Game, STARTING_LIVES
        from vocabulary import VERBS
        from upgrades import completion_bonus
        for mistakes in (0, 2, 4):
            with self.subTest(mistakes=mistakes):
                game = Game.__new__(Game)  # no sound card or display needed
                game.rng = random.Random(14)
                game.coins = 0
                game.owned = set()
                game.equipped = None
                game.progress = {"runs": 0, "best": 0, "completions": 0,
                                 "total_hits": 0, "best_mistakes": None}
                game.particles = []
                game.rings = []
                game.hit_effects = []
                game.flight_trail = []
                game.shake = game.flash = game.time_elapsed = game.toast_age = 0.0
                game.sound = lambda _: None
                game.save_progress = lambda: None
                game.new_run()
                for idx in range(mistakes):
                    game.register_shot(None, (310, 475))
                    game.resolve()
                    game.start_shop()
                    game.start_question()
                while not game.deck.complete:
                    game.register_shot(game.correct_index, (640, 475))
                    game.resolve()
                    if game.deck.complete:
                        game.end_run()
                    else:
                        game.start_shop()
                        game.start_question()
                self.assertTrue(game.completed)
                self.assertEqual(game.phase, "end")
                self.assertEqual(game.correct_count, len(VERBS))
                self.assertEqual(game.deck.attempts, len(VERBS) + mistakes)
                self.assertEqual(game.lives, STARTING_LIVES - mistakes)
                self.assertEqual(game.bonus_awarded, completion_bonus(mistakes))
                self.assertEqual(game.progress["completions"], 1)

    def test_five_mistakes_end_run_without_bonus(self):
        from game import Game, STARTING_LIVES
        game = Game.__new__(Game)
        game.rng = random.Random(10)
        game.coins = 0
        game.owned = set()
        game.equipped = None
        game.progress = {"runs": 0, "best": 0, "completions": 0,
                         "total_hits": 0, "best_mistakes": None}
        game.particles, game.rings, game.hit_effects, game.flight_trail = [], [], [], []
        game.shake = game.flash = game.time_elapsed = game.toast_age = 0.0
        game.sound = lambda _: None
        game.save_progress = lambda: None
        game.new_run()
        for i in range(STARTING_LIVES):
            game.register_shot(None, (300, 450))
            game.resolve()
            if i + 1 < STARTING_LIVES:
                game.start_shop()
                game.start_question()
        game.end_run()
        self.assertFalse(game.completed)
        self.assertEqual(game.bonus_awarded, 0)
        self.assertEqual(game.progress["completions"], 0)



if __name__ == '__main__':
    unittest.main()
