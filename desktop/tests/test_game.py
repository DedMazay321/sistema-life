from __future__ import annotations

from datetime import date, timedelta
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from sistema.game import (
    ACHIEVEMENTS, BALANCE_BONUS_XP, CATEGORY_LABELS, CHAINS, DAILY_BONUS_XP, QUESTS, CustomTask, DevelopmentArc, JournalEntry, PlayerState,
    achievement_tier, adjusted_reward, apply_chains, chain_progress, custom_due, daily_quests,
    arc_progress, get_daily_quests, has_daily_balance, level_progress, metric_value, streak, sync_achievements, toggle_quest, toggle_weekly_done, toggle_weekly_task, week_key,
)
from sistema.storage import PlayerStore


class GameTests(unittest.TestCase):
    def setUp(self) -> None:
        self.today = date(2026, 11, 7)

    def test_library_has_248_unique_real_life_quests(self) -> None:
        self.assertEqual(248, len(QUESTS)); self.assertEqual(248, len({quest.id for quest in QUESTS}))
        self.assertEqual(8, len({quest.category for quest in QUESTS}))
        self.assertEqual(set(CATEGORY_LABELS), {quest.category for quest in QUESTS})
        self.assertTrue(all(not ("{target}" in q.description) or q.base for q in QUESTS))

    def test_daily_set_is_stable_after_level_up(self) -> None:
        state = PlayerState(); initial = get_daily_quests(state, self.today)
        self.assertEqual(6, len(initial)); state.total_xp = 1000
        self.assertEqual([q.id for q in initial], [q.id for q in get_daily_quests(state, self.today)])

    def test_daily_selection_avoids_previous_day_repeats(self) -> None:
        first = daily_quests(self.today, 1)
        second = daily_quests(self.today + timedelta(days=1), 1, [q.id for q in first])
        self.assertFalse({q.id for q in first} & {q.id for q in second})

    def test_progressive_level_thresholds(self) -> None:
        self.assertEqual(1, level_progress(0).level); self.assertEqual(2, level_progress(100).level)
        self.assertEqual(2, level_progress(224).level); self.assertEqual(3, level_progress(225).level)

    def test_quest_difficulty_scales_caps_and_modes(self) -> None:
        quest = next(item for item in QUESTS if item.id == "pushups")
        self.assertEqual(8, quest.target(1)); self.assertGreater(quest.target(5), quest.target(1)); self.assertEqual(50, quest.target(100))
        self.assertEqual(6, quest.target(1, "light")); self.assertEqual(10, quest.target(1, "challenge"))
        self.assertEqual(24, adjusted_reward(PlayerState(difficulty="light"), quest))
        self.assertEqual(37, adjusted_reward(PlayerState(difficulty="challenge"), quest))

    def test_completion_and_undo_restore_xp_and_attribute(self) -> None:
        state = PlayerState(); quest = get_daily_quests(state, self.today)[0]
        toggle_quest(state, quest, self.today); self.assertEqual(quest.xp, state.total_xp); self.assertEqual(1, state.attributes[quest.attribute])
        toggle_quest(state, quest, self.today); self.assertEqual(0, state.total_xp); self.assertEqual(0, state.attributes[quest.attribute])

    def test_full_day_bonus_and_undo_use_actual_reward(self) -> None:
        state = PlayerState(); quests = get_daily_quests(state, self.today)
        for quest in quests[:5]: toggle_quest(state, quest, self.today)
        before = state.total_xp; toggle_quest(state, quests[5], self.today)
        self.assertEqual(before + state.rewards[self.today.isoformat()][quests[5].id] + DAILY_BONUS_XP, state.total_xp)
        toggle_quest(state, quests[5], self.today); self.assertEqual(before, state.total_xp)

    def test_achievement_tiers_are_progressive_and_permanent(self) -> None:
        state = PlayerState(); state.history = {"2026-11-01": {"pushups"}}
        unlocks = sync_achievements(state, self.today); path = next(item for item in ACHIEVEMENTS if item.id == "path")
        self.assertEqual(1, achievement_tier(state, path)); self.assertTrue(any(item.id == "path" for item, _ in unlocks))
        state.history = {f"2026-10-{i + 1:02d}": {"pushups"} for i in range(10)}; sync_achievements(state, self.today)
        self.assertEqual(2, achievement_tier(state, path)); state.history = {}; sync_achievements(state, self.today)
        self.assertEqual(2, achievement_tier(state, path))

    def test_streak_uses_stored_daily_sets_and_rest_day(self) -> None:
        state = PlayerState()
        for offset in range(3):
            day = self.today - timedelta(days=offset); quests = get_daily_quests(state, day)
            state.history[day.isoformat()] = {q.id for q in quests}
        self.assertEqual(3, streak(state, self.today)); state.rest_days.add(self.today.isoformat())
        self.assertEqual(3, streak(state, self.today))

    def test_custom_task_schedule_and_rewards(self) -> None:
        task = CustomTask("custom:test", "Своя задача", "Записать результат", "mind", 30, (6,))
        state = PlayerState(custom_tasks=[task]); self.assertEqual([task], custom_due(state, self.today))
        toggle_quest(state, task.as_quest(), self.today)
        self.assertEqual(30, state.total_xp); self.assertEqual(1, metric_value(state, "custom", self.today))

    def test_weekly_boss_grants_and_removes_bonus(self) -> None:
        key = week_key(self.today); state = PlayerState(weekly_goals={key: "Готово"})
        self.assertTrue(toggle_weekly_done(state, self.today)); self.assertEqual(100, state.total_xp)
        self.assertFalse(toggle_weekly_done(state, self.today)); self.assertEqual(0, state.total_xp)

    def test_weekly_steps_toggle_without_changing_xp(self) -> None:
        key = week_key(self.today); state = PlayerState(weekly_tasks={key: ["Первый шаг"]})
        self.assertTrue(toggle_weekly_task(state, self.today, 0)); self.assertIn(f"{key}:0", state.weekly_task_done)
        self.assertFalse(toggle_weekly_task(state, self.today, 0)); self.assertEqual(0, state.total_xp)

    def test_balance_bonus_requires_four_directions_and_reverses(self) -> None:
        state = PlayerState(); quests = get_daily_quests(state, self.today)
        selected = list({quest.category: quest for quest in quests}.values())[:4]
        for quest in selected: toggle_quest(state, quest, self.today)
        self.assertTrue(has_daily_balance(state, self.today))
        self.assertIn(self.today.isoformat(), state.balance_bonus_days)
        before = state.total_xp; toggle_quest(state, selected[-1], self.today)
        self.assertFalse(has_daily_balance(state, self.today))
        self.assertEqual(before - selected[-1].xp - BALANCE_BONUS_XP, state.total_xp)

    def test_arc_progress_uses_matching_completed_actions(self) -> None:
        arc = DevelopmentArc("arc:test", "Сильное тело", "body", 3)
        state = PlayerState(history={self.today.isoformat(): {"pushups", "squats", "read"}})
        self.assertEqual(2, arc_progress(state, arc))

    def test_journal_unlocks_secret_achievement(self) -> None:
        state = PlayerState(journal={self.today.isoformat(): {"pushups": JournalEntry("8 раз", "photo.jpg")}})
        unlocks = sync_achievements(state, self.today)
        self.assertTrue(any(item.id == "journal" for item, _ in unlocks))

    def test_chain_completes_and_pays_only_once(self) -> None:
        state = PlayerState()
        for offset in range(6, -1, -1):
            day = self.today - timedelta(days=offset)
            state.history[day.isoformat()] = {"pushups"}; apply_chains(state, day)
        self.assertEqual(100, state.total_xp); self.assertIn("body7", state.completed_chains)
        apply_chains(state, self.today); self.assertEqual(100, state.total_xp)
        self.assertEqual(7, chain_progress(state, CHAINS[0], self.today))

    def test_storage_round_trip_preserves_all_progress(self) -> None:
        with tempfile.TemporaryDirectory(dir=Path(__file__).parent) as directory:
            store = PlayerStore(Path(directory)); task = CustomTask("custom:test", "Цель", "Результат", "mind", 25, (6, 7))
            state = PlayerState(custom_tasks=[task], journal={self.today.isoformat(): {"custom:test": JournalEntry("Готово", "photo.jpg")}},
                                weekly_goals={week_key(self.today): "Босс"}, weekly_tasks={week_key(self.today): ["Первый шаг"]},
                                weekly_task_done={f"{week_key(self.today)}:0"}, balance_bonus_days={self.today.isoformat()},
                                arcs=[DevelopmentArc("arc:test", "Арка", "mind", 12)], difficulty="challenge", reminder_enabled=True, pin_hash="hash")
            quest = get_daily_quests(state, self.today)[0]; toggle_quest(state, quest, self.today); store.save(state); loaded = store.load()
            for field in ("total_xp", "history", "daily_sets", "rewards", "unlocked_achievements", "difficulty",
                          "custom_tasks", "journal", "weekly_goals", "weekly_done", "rest_days", "completed_chains",
                          "reminder_enabled", "reminder_minute", "pin_hash", "arcs", "weekly_tasks", "weekly_task_done", "balance_bonus_days"):
                self.assertEqual(getattr(state, field), getattr(loaded, field), field)
            self.assertEqual(1, loaded.attributes["intellect"])

    def test_storage_recovers_backup_after_corruption(self) -> None:
        with tempfile.TemporaryDirectory(dir=Path(__file__).parent) as directory:
            store = PlayerStore(Path(directory)); store.save(PlayerState(total_xp=123)); store.save(PlayerState(total_xp=123))
            store.path.write_text("not json", encoding="utf-8"); self.assertEqual(123, store.load().total_xp)


if __name__ == "__main__":
    unittest.main()
