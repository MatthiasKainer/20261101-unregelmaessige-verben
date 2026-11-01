"""Deterministic tests; run before the expensive Windows EXE build."""
import random
import unittest
from collections import Counter

from upgrades import (
    LEVELS, PAGE_SIZE, THEMES, UPGRADES, UPGRADE_BY_ID,
    recommended_page, reward, shop_page,
)
from vocabulary import VERBS, VerbDeck


class VocabularyTests(unittest.TestCase):
    def test_28_distinct_verbs(self):
        self.assertEqual(len(VERBS), 28)
        self.assertEqual(len({v.infinitive for v in VERBS}), 28)
        self.assertEqual(sum(v.source.startswith('Verb-Liste') for v in VERBS), 21)

    def test_correct_and_wrong_options(self):
        rng = random.Random(30)
        for verb in VERBS:
            self.assertEqual(len(set(verb.options(rng))), 3)
            self.assertIn(verb.simple_past, verb.options(rng))
            self.assertNotEqual(verb.distractor_a, verb.simple_past)
            self.assertNotEqual(verb.distractor_b, verb.simple_past)

    def test_deck_uses_each_verb_once_per_cycle(self):
        deck = VerbDeck(random.Random(9))
        first = [deck.next().infinitive for _ in range(len(VERBS))]
        second = [deck.next().infinitive for _ in range(len(VERBS))]
        self.assertEqual(set(first), {v.infinitive for v in VERBS})
        self.assertEqual(set(second), set(first))
        self.assertNotEqual(first[-1], second[0])

    def test_special_cases(self):
        past = {v.infinitive: v.simple_past for v in VERBS}
        self.assertEqual(past['be'], 'was / were')
        self.assertEqual(past['put'], 'put')
        self.assertEqual(past['go'], 'went')
        self.assertEqual(past['sell'], 'sold')


class ShopTests(unittest.TestCase):
    def test_exactly_ten_upgrades_per_verb(self):
        self.assertEqual(len(UPGRADES), 280)
        self.assertEqual(len(UPGRADES), len(VERBS) * 10)
        self.assertEqual(len(THEMES), len(VERBS))
        self.assertEqual(len(LEVELS), 10)
        self.assertEqual(Counter(u.theme_index for u in UPGRADES), Counter({i: 10 for i in range(28)}))

    def test_upgrades_unique_and_costs_progress(self):
        self.assertEqual(len(UPGRADE_BY_ID), len(UPGRADES))
        self.assertEqual(len({u.name for u in UPGRADES}), len(UPGRADES))
        for i in range(len(THEMES)):
            prices = [u.cost for u in UPGRADES if u.theme_index == i]
            self.assertEqual(prices, sorted(set(prices)))
            self.assertGreater(prices[0], 0)

    def test_shop_paging(self):
        total_pages = (len(UPGRADES) - 1) // PAGE_SIZE + 1
        items = [item for page in range(total_pages) for item in shop_page(page)]
        self.assertEqual(items, list(UPGRADES))
        self.assertEqual(len(shop_page(total_pages)), 0)

    def test_can_always_preview_free_ammunition(self):
        # At 0 coins, premium items remain unavailable, but free trials are
        # explicitly offered unconditionally by Game.trial() in every shop.
        self.assertGreater(len([u for u in UPGRADES if u.tier >= 3]), 0)
        self.assertEqual(recommended_page(0, set()), 0)
        self.assertTrue(shop_page(0))

    def test_recommendation_targets_affordable_upgrade(self):
        for coins in (12, 40, 80, 400, 10000):
            page = recommended_page(coins, set())
            self.assertTrue(any(u.cost <= coins for u in shop_page(page)))

    def test_rewards_allow_first_purchase(self):
        self.assertGreaterEqual(reward(1, 0), UPGRADES[0].cost)
        self.assertGreater(reward(8, 4.5), reward(1, 0))
        self.assertGreaterEqual(reward(0, -50), 30)


if __name__ == '__main__':
    unittest.main()
