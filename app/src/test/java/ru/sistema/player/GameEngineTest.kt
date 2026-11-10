package ru.sistema.player

import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertNotEquals
import org.junit.Assert.assertTrue
import org.junit.Test
import java.time.LocalDate

class GameEngineTest {
    private val day = LocalDate.parse("2026-11-07")

    @Test fun `catalog contains 248 unique concrete quests`() {
        assertEquals(248, GameEngine.quests.size); assertEquals(248, GameEngine.questById.size)
        assertTrue(GameEngine.quests.all { it.description.isNotBlank() && (!it.description.contains("{target}") || it.base > 0) })
        assertEquals(8, GameEngine.quests.map { it.category }.distinct().size)
    }
    @Test fun `daily set has six quests and remains fixed when level changes`() {
        val initial = GameEngine.getDailyQuests(PlayerState(), day); val ids = initial.dailySets.getValue(day.toString())
        assertEquals(6, ids.size); assertEquals(6, ids.distinct().size)
        assertEquals(ids, GameEngine.getDailyQuests(initial.copy(totalXp = 5000), day).dailySets.getValue(day.toString()))
    }
    @Test fun `next day avoids yesterday quests when alternatives exist`() {
        val today = GameEngine.getDailyQuests(PlayerState(totalXp = 2000), day)
        val tomorrow = GameEngine.getDailyQuests(today, day.plusDays(1))
        assertTrue(today.dailySets.getValue(day.toString()).toSet().intersect(tomorrow.dailySets.getValue(day.plusDays(1).toString()).toSet()).isEmpty())
    }
    @Test fun `difficulty scales gradually respects cap and modes`() {
        val quest = GameEngine.questById.getValue("pushups")
        assertEquals(8, quest.target(1)); assertEquals(10, quest.target(2)); assertEquals(50, quest.target(100))
        assertEquals(6, quest.target(1, "light")); assertEquals(10, quest.target(1, "challenge"))
        assertEquals(24, GameEngine.adjustedReward(PlayerState(difficulty = "light"), quest))
        assertEquals(37, GameEngine.adjustedReward(PlayerState(difficulty = "challenge"), quest))
    }
    @Test fun `locked quests do not enter early daily sets`() {
        assertTrue(GameEngine.dailyQuests(day, 1).all { it.minLevel <= 1 })
    }
    @Test fun `quest awards actual reward and attribute once then reverses exactly`() {
        val quest = GameEngine.dailyQuestList(GameEngine.getDailyQuests(PlayerState(), day), day).first()
        val first = GameEngine.toggle(PlayerState(), quest.id, day.toString())
        assertEquals(quest.reward(1), first.state.totalXp); assertEquals(1, first.state.attributes[quest.attribute])
        val undone = GameEngine.toggle(first.state, quest.id, day.toString())
        assertEquals(0, undone.state.totalXp); assertEquals(0, undone.state.attributes[quest.attribute]); assertFalse(undone.completed)
    }
    @Test fun `full day adds and removes forty xp bonus`() {
        var state = GameEngine.getDailyQuests(PlayerState(), day); val daily = GameEngine.dailyQuestList(state, day)
        daily.dropLast(1).forEach { state = GameEngine.toggle(state, it.id, day.toString()).state }
        val before = state.totalXp; val final = GameEngine.toggle(state, daily.last().id, day.toString()); state = final.state
        assertTrue(final.dailyBonusReceived); assertEquals(before + final.reward + 40, state.totalXp)
        val undone = GameEngine.toggle(state, daily.last().id, day.toString())
        assertEquals(before, undone.state.totalXp); assertEquals(0, GameEngine.streak(undone.state, day))
    }
    @Test fun `progressive level thresholds and ranks work`() {
        assertEquals(LevelProgress(1, 0, 100, "E"), GameEngine.levelProgress(0))
        assertEquals(LevelProgress(2, 0, 125, "E"), GameEngine.levelProgress(100))
        assertEquals(LevelProgress(3, 0, 150, "E"), GameEngine.levelProgress(225))
        assertEquals("D", GameEngine.rank(4)); assertEquals("S", GameEngine.rank(25))
    }
    @Test fun `achievement tiers unlock and never disappear after undo`() {
        val first = GameEngine.toggle(PlayerState(), "pushups", day.toString())
        assertTrue("path:1" in first.state.unlockedAchievements)
        assertTrue("path:1" in GameEngine.toggle(first.state, "pushups", day.toString()).state.unlockedAchievements)
    }
    @Test fun `streak continues across complete daily sets only`() {
        var state = PlayerState()
        for (offset in 2 downTo 0) {
            val current = day.minusDays(offset.toLong()); state = GameEngine.getDailyQuests(state, current)
            for (quest in GameEngine.dailyQuestList(state, current)) state = GameEngine.toggle(state, quest.id, current.toString()).state
        }
        assertEquals(3, GameEngine.streak(state, day)); assertEquals(3, GameEngine.perfectDays(state, day))
        assertNotEquals(0, GameEngine.totalCompleted(state))
    }
    @Test fun `custom task follows schedule and awards xp`() {
        val task = CustomTask("custom:test", "Своя задача", "Записать результат", "mind", 30, listOf(6))
        val state = PlayerState(customTasks = listOf(task)); assertEquals(listOf(task), GameEngine.customDue(state, day))
        val result = GameEngine.toggle(state, task.id, day.toString())
        assertEquals(30, result.state.totalXp); assertEquals(1, GameEngine.customCompleted(result.state))
        assertEquals(1, result.state.attributes["intellect"])
    }
    @Test fun `rest day protects streak but is not perfect`() {
        val state = GameEngine.toggleRestDay(PlayerState(), day)
        assertEquals(1, GameEngine.streak(state, day)); assertEquals(0, GameEngine.perfectDays(state, day))
        assertEquals(0, GameEngine.streak(GameEngine.toggleRestDay(state, day), day))
    }
    @Test fun `weekly boss grants and removes exactly one hundred xp`() {
        val key = GameEngine.weekKey(day); val state = PlayerState(weeklyGoals = mapOf(key to "Завершить проект"))
        val done = GameEngine.toggleWeeklyDone(state, day); assertEquals(100, done.totalXp); assertTrue(key in done.weeklyDone)
        assertEquals(0, GameEngine.toggleWeeklyDone(done, day).totalXp)
    }
    @Test fun `journal and secret achievement progress persist in state`() {
        val state = PlayerState(journal = mapOf(day.toString() to mapOf("pushups" to JournalEntry("8 повторений", "photo.jpg"))))
        assertEquals(1, GameEngine.metricValue(state, "journal", day))
        val unlocks = GameEngine.syncAchievements(state, day); assertTrue(unlocks.any { it.achievement.id == "journal" })
    }
    @Test fun `seven day chain pays reward only once`() {
        var state = PlayerState()
        for (offset in 6 downTo 0) {
            val current = day.minusDays(offset.toLong())
            state = state.copy(history = state.history + (current.toString() to setOf("pushups")))
            state = GameEngine.applyChains(state, current)
        }
        assertEquals(100, state.totalXp); assertTrue("body7" in state.completedChains)
        assertEquals(100, GameEngine.applyChains(state, day).totalXp)
    }
}
