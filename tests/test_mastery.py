"""Regression tests for finite, mastery-based runs and completion rewards."""
import random
import unittest

from vocabulary import VERBS, MasteryDeck
from upgrades import completion_bonus
from weapon_fx import WEAPONS, flight_point


class MasteryDeckTests(unittest.TestCase):
    def test_run_ends_after_all_unique_verbs_are_correct(self):
        deck = MasteryDeck(random.Random(127))
        answers = []
        for _ in VERBS:
            verb = deck.next()
            answers.append(verb.infinitive)
            deck.record(True)
        self.assertEqual(len(set(answers)), len(VERBS))
        self.assertTrue(deck.complete)
        self.assertEqual(deck.completed_count, 28)
        self.assertEqual(deck.attempts, 28)
        self.assertEqual(deck.mistakes, 0)
        with self.assertRaises(StopIteration):
            deck.next()

    def test_wrong_verb_is_requeued_until_correct(self):
        deck = MasteryDeck(random.Random(987))
        missed = deck.next()
        deck.record(False)
        self.assertEqual(deck.completed_count, 0)
        self.assertFalse(deck.complete)
        self.assertEqual(deck.mistakes, 1)
        # Never ask the same missed verb immediately while others remain.
        self.assertNotEqual(deck.next().infinitive, missed.infinitive)
        deck.record(True)
        seen = {deck.current.infinitive} if deck.current else set()
        while not deck.complete:
            verb = deck.next()
            seen.add(verb.infinitive)
            deck.record(True)
        self.assertIn(missed.infinitive, seen)
        self.assertEqual(deck.completed_count, 28)
        self.assertEqual(deck.attempts, 29)
        self.assertEqual(deck.mistakes, 1)

    def test_two_misses_then_all_correct_still_finishes(self):
        deck = MasteryDeck(random.Random(543))
        deck.next()
        deck.record(False)
        deck.next()
        deck.record(False)
        while not deck.complete:
            deck.next()
            deck.record(True)
        self.assertEqual(deck.attempts, len(VERBS) + 2)
        self.assertEqual(len(deck.remaining), 0)
        self.assertEqual(deck.mistakes, 2)

    def test_invalid_deck_sequence_rejected(self):
        deck = MasteryDeck(random.Random(9))
        with self.assertRaises(RuntimeError):
            deck.record(True)
        deck.next()
        with self.assertRaises(RuntimeError):
            deck.next()

    def test_bonus_decreases_with_mistakes(self):
        self.assertEqual([completion_bonus(m) for m in range(5)],
                         [1800, 1500, 1200, 900, 600])
        self.assertEqual(completion_bonus(100), 0)
        self.assertEqual(completion_bonus(-3), completion_bonus(0))


class WeaponSignatureTests(unittest.TestCase):
    def test_all_weapons_are_different(self):
        self.assertEqual(len(WEAPONS), len(VERBS))
        self.assertEqual(len({w.trail for w in WEAPONS.values()}), 28)
        self.assertEqual(len({w.impact for w in WEAPONS.values()}), 28)
        self.assertEqual(len({(w.motion, w.trail, w.impact) for w in WEAPONS.values()}), 28)

    def test_all_flights_end_at_the_exact_clicked_target(self):
        a, b = (630, 710), (210, 402)
        for kind in WEAPONS:
            self.assertEqual(flight_point(kind, a, b, 0), a, kind)
            self.assertAlmostEqual(flight_point(kind, a, b, 1)[0], b[0], places=7)
            self.assertAlmostEqual(flight_point(kind, a, b, 1)[1], b[1], places=7)

    def test_flight_paths_visibly_differ(self):
        a, b = (630, 710), (210, 402)
        points = {kind: tuple(round(v, 2) for p in (.34, .58, .73)
                              for v in flight_point(kind, a, b, p))
                  for kind in WEAPONS}
        self.assertGreaterEqual(len(set(points.values())), 12)
        self.assertNotEqual(points['rocket'], points['football'])
        self.assertNotEqual(points['laser'], points['firework'])


if __name__ == '__main__':
    unittest.main()
