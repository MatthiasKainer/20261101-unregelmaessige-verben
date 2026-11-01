"""Weapon-effect rules: scaling, timer, assists, protection, coin cap."""
import random
import unittest

from effects import (
    COIN_CAP, EFFECTS, MAX_ASSISTS_PER_VERB, PRESSURE,
    compute_reward, consume_timer, deposit_time_bank, first_miss_action,
    hint_assists, hint_delay, pick_elimination, pressure_level, protection,
    question_seconds, streak_after_fail, streak_after_success, strength,
)
from upgrades import THEMES, UPGRADES, completion_bonus, reward, tier_ready
from vocabulary import VERBS, MasteryDeck, touch_stat


class EffectTableTests(unittest.TestCase):
    def test_every_weapon_has_one_effect(self):
        self.assertEqual(set(EFFECTS), {theme.projectile for theme in THEMES})
        self.assertEqual(len(EFFECTS), 28)
        families = {fx.family for fx in EFFECTS.values()}
        self.assertTrue(families <= {
            "hilfe", "zeit", "schutz", "serie", "muenzen", "praezision", "risiko", "boss"})
        self.assertGreaterEqual(len(families), 8)

    def test_tiers_never_get_weaker(self):
        for name, fx in EFFECTS.items():
            powers = [strength(fx, tier) for tier in range(1, 11)]
            for earlier, later in zip(powers, powers[1:]):
                self.assertGreaterEqual(later + 1e-9, earlier, f"{name} {powers}")

    def test_shop_cards_mention_the_effect(self):
        for upgrade in UPGRADES:
            self.assertIn(upgrade.effect.text(upgrade.tier)[:12], upgrade.description)
            self.assertTrue(upgrade.effect_line)

    def test_level_requires_previous_level(self):
        self.assertTrue(tier_ready(0, 1, set()))
        self.assertFalse(tier_ready(4, 7, set()))
        self.assertTrue(tier_ready(4, 7, {"04-06"}))
        self.assertFalse(tier_ready(4, 7, {"03-06"}))


class TimerTests(unittest.TestCase):
    def test_freeze_holds_then_releases(self):
        snow = EFFECTS["snow"]
        self.assertEqual(consume_timer(snow, 1, 0.2, 5, 0.05), 0.0)
        self.assertGreater(consume_timer(snow, 1, 5, 5, 0.05), 0)
        # Tier 10 freezes longer than tier 1.
        self.assertGreater(snow.value(10), snow.value(1))

    def test_gravity_slows_only_the_final_seconds(self):
        galaxy = EFFECTS["galaxy"]
        full = consume_timer(galaxy, 10, 1.0, 4.0, 0.10)
        slow = consume_timer(galaxy, 10, 1.0, 1.0, 0.10)
        self.assertAlmostEqual(full, 0.10)
        self.assertLess(slow, full)
        self.assertAlmostEqual(slow, 0.10 * galaxy.value(10))

    def test_time_bank_respects_the_cap(self):
        star = EFFECTS["star"]
        bank = deposit_time_bank(0, 5, star, 1)
        self.assertAlmostEqual(bank, 0.5)
        capped = deposit_time_bank(5, 5, star, 10)
        self.assertAlmostEqual(capped, star.value_b(10))

    def test_question_clock_tracks_pressure_fever_and_risk(self):
        self.assertEqual(question_seconds(0, None, 1, 0, False, False), 5.0)
        self.assertEqual(question_seconds(21, None, 1, 0, False, False), PRESSURE[4]["seconds"])
        boom = EFFECTS["explosion"]
        self.assertAlmostEqual(question_seconds(0, boom, 10, 0, False, False), 4.0)
        comet = EFFECTS["comet"]
        boosted = question_seconds(3, comet, 10, 8, False, False)
        self.assertGreater(boosted, 5)
        self.assertLessEqual(boosted, 5 + comet.value_b(10) + 0.001)
        self.assertEqual(question_seconds(27, EFFECTS["plasma"], 1, 0, False, True), 5.0)

    def test_pressure_bands(self):
        self.assertEqual([pressure_level(n) for n in (0, 6, 7, 13, 14, 20, 21, 27)],
                         [1, 1, 2, 2, 3, 3, 4, 4])


class AssistAndProtectionTests(unittest.TestCase):
    def test_assisted_answer_returns_the_verb_without_a_mistake(self):
        deck = MasteryDeck(random.Random(3))
        verb = deck.next()
        deck.record(True, assisted=True)
        self.assertEqual(deck.assisted_count, 1)
        self.assertEqual(deck.mistakes, 0)
        self.assertNotIn(verb.infinitive, deck.mastered)
        self.assertEqual(deck.completed_count, 0)
        self.assertIn(verb, deck.remaining)

    def test_two_assists_then_a_clean_answer_masters_it(self):
        deck = MasteryDeck(random.Random(4))
        verb = deck.next()
        deck.record(True, assisted=True)
        # Pull until the same verb is back, answering everything else cleanly.
        seen = 0
        while seen < 2:
            current = deck.next()
            if current.infinitive == verb.infinitive:
                seen += 1
                deck.record(True, assisted=seen < 2)
            else:
                deck.record(True)
        self.assertIn(verb.infinitive, deck.mastered)
        self.assertLessEqual(deck.assisted_count, MAX_ASSISTS_PER_VERB)

    def test_hint_does_not_assist_the_past_half_of_a_boss(self):
        prism = EFFECTS["crystal"]
        self.assertTrue(prism.assisted)
        self.assertFalse(hint_assists(prism, boss=True, boss_stage="past"))
        self.assertTrue(hint_assists(prism, boss=True, boss_stage="participle"))
        self.assertIsNone(hint_delay(prism, 5, boss=False))
        self.assertEqual(hint_delay(prism, 6, boss=False), 2.5)
        self.assertEqual(hint_delay(EFFECTS["paint"], 10, boss=False), None)

    def test_fifty_fifty_never_removes_the_answer(self):
        rng = random.Random(11)
        for correct in range(4):
            for _ in range(30):
                picked = pick_elimination(correct, 4, rng)
                self.assertNotEqual(picked, correct)

    def test_rebound_opens_a_second_shot_and_penalty_is_boss_only(self):
        self.assertEqual(first_miss_action("wrong", "rebound", 1, False, 0), "rebound")
        self.assertEqual(first_miss_action("wrong", "rebound", 1, True, 0), "close")
        self.assertEqual(first_miss_action("timeout", "rebound", 2, False, 0), "close")
        self.assertEqual(first_miss_action("wrong", "penalty", 0, False, 1), "penalty")
        self.assertEqual(first_miss_action("correct", "rebound", 3, False, 2), "close")

    def test_protection_saves_a_life_not_the_verb(self):
        self.assertEqual(protection("wrong", "shield", 1, 0), "shield")
        self.assertIsNone(protection("wrong", "shield", 0, 0))
        self.assertEqual(protection("timeout", "quench", 0, 2), "quench")
        self.assertIsNone(protection("wrong", "quench", 0, 2))
        self.assertIsNone(protection("correct", "shield", 1, 1))

    def test_streak_weapons(self):
        rocket = EFFECTS["rocket"]
        self.assertEqual(streak_after_success(3, rocket, 10, 1.0, False), 5)
        self.assertEqual(streak_after_success(3, rocket, 10, 9.0, False), 4)
        self.assertEqual(streak_after_success(3, rocket, 10, 0.2, True), 3)
        disco = EFFECTS["disco"]
        kept = streak_after_fail(8, disco, 1)
        self.assertEqual(kept, int(8 * disco.value(1)))
        self.assertGreater(streak_after_fail(8, disco, 10), kept)
        self.assertEqual(streak_after_fail(8, None, 1), 0)


class RewardTests(unittest.TestCase):
    def test_cap_and_assist_halving(self):
        base = reward(4, 2)
        capped = compute_reward(4, 2, extra_mult=9)
        self.assertEqual(capped, int(base * COIN_CAP))
        halved = compute_reward(4, 2, extra_mult=9, assisted=True)
        self.assertEqual(halved, int(base * COIN_CAP * 0.5))
        self.assertLess(halved, capped)

    def test_gold_scales_with_combo_and_stays_under_the_cap(self):
        gold = EFFECTS["gold"]
        low = compute_reward(10, 1, fx=gold, tier=1)
        high = compute_reward(10, 1, fx=gold, tier=10)
        plain = compute_reward(10, 1)
        self.assertGreater(low, plain)
        self.assertGreater(high, low)
        self.assertLessEqual(high, int(reward(10, 1) * COIN_CAP))

    def test_flat_tips_and_milestones_add_coins(self):
        pizza = EFFECTS["pizza"]
        tipped = compute_reward(1, 1, fx=pizza, tier=10, express=True)
        plain = compute_reward(1, 1, fx=pizza, tier=10, express=False)
        self.assertEqual(tipped - plain, int(pizza.value(10)))
        confetti = EFFECTS["confetti"]
        burst = compute_reward(4, 0, fx=confetti, tier=1, milestone=True)
        self.assertEqual(burst - compute_reward(4, 0), int(confetti.value(1)))

    def test_boss_clear_uses_the_meteor_and_the_cap(self):
        meteor = EFFECTS["meteor"]
        payout = compute_reward(0, 0, fx=meteor, tier=10, boss=True, boss_clear=True)
        self.assertEqual(payout, int(150 * COIN_CAP))
        self.assertEqual(compute_reward(0, 0, fx=meteor, tier=10, boss=True, boss_clear=False), 0)

    def test_completion_bonus_charges_for_help(self):
        self.assertEqual(completion_bonus(1, 2), 1800 - 300 - 100)
        self.assertEqual(completion_bonus(0), 1800)


class LeitnerTests(unittest.TestCase):
    def test_box_zero_needs_two_clean_answers(self):
        stats = {"go": {"box": 0, "right": 1, "wrong": 2, "assisted": 0, "last_run": 1}}
        deck = MasteryDeck(random.Random(8), stats)
        self.assertEqual(deck.required["go"], 2)
        # Answer until go has been clean twice; everything else once.
        clean = {name: 0 for name in deck.required}
        guard = 0
        while not deck.complete:
            verb = deck.next()
            need = deck.required[verb.infinitive]
            assisted = False
            correct = True
            if verb.infinitive == "go" and clean["go"] == 0:
                # first clean hit must not finish it
                pass
            deck.record(correct, assisted=assisted)
            if correct and not assisted:
                clean[verb.infinitive] += 1
            self.assertLessEqual(clean[verb.infinitive], need)
            guard += 1
            self.assertLess(guard, 80)
        self.assertGreaterEqual(clean["go"], 2)
        self.assertEqual(deck.mistakes, 0)

    def test_touch_stat_moves_boxes(self):
        stats = {}
        touch_stat(stats, "go", outcome="clean", run_index=1)
        self.assertEqual(stats["go"]["box"], 1)
        touch_stat(stats, "go", outcome="assisted", run_index=1)
        self.assertEqual(stats["go"]["box"], 1)
        self.assertEqual(stats["go"]["assisted"], 1)
        touch_stat(stats, "go", outcome="wrong", run_index=2)
        self.assertEqual(stats["go"]["box"], 0)
        self.assertEqual(stats["go"]["wrong"], 1)


class VerbDataTests(unittest.TestCase):
    def test_participles_and_traps_are_present(self):
        past = {verb.infinitive: verb.past_participle for verb in VERBS}
        self.assertEqual(past["go"], "gone")
        self.assertEqual(past["get"], "got")
        self.assertEqual(past["be"], "been")
        self.assertEqual(past["put"], "put")
        traps = {verb.infinitive: verb.distractor_c for verb in VERBS}
        self.assertEqual(traps["hear"], "herd")
        self.assertEqual(traps["meet"], "meat")
        self.assertEqual(traps["think"], "thank")
        for verb in VERBS:
            self.assertIn("→", verb.german)
            self.assertNotIn(verb.simple_past.split()[0], verb.sentence)


if __name__ == "__main__":
    unittest.main()
