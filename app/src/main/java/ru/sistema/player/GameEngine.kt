package ru.sistema.player

import java.time.LocalDate
import java.time.temporal.WeekFields
import java.util.Locale
import java.util.Random

data class Quest(
    val id: String, val title: String, val category: String, val description: String, val xp: Int,
    val minLevel: Int = 1, val base: Int = 0, val step: Int = 0, val maxTarget: Int = 0,
) {
    val attribute: String get() = GameEngine.categoryAttributes.getValue(category)
    val attributeLabel: String get() = GameEngine.attributeLabels.getValue(attribute)
    fun target(level: Int, difficulty: String = "standard"): Int {
        if (base == 0) return 0
        val normal = (base + step * (level.coerceAtLeast(1) - 1)).coerceAtMost(maxTarget)
        return when (difficulty) {
            "light" -> (normal * 0.75).toInt().coerceAtLeast(1)
            "challenge" -> (normal * 1.25).toInt().coerceAtLeast(normal)
            else -> normal
        }
    }
    fun scaledDescription(level: Int, difficulty: String = "standard"): String =
        description.replace("{target}", target(level, difficulty).toString())
    fun reward(level: Int): Int = xp + ((level.coerceAtLeast(1) - 1) * 2).coerceAtMost(20)
}

data class CustomTask(
    val id: String, val title: String, val description: String, val category: String = "discipline",
    val xp: Int = 20, val weekdays: List<Int> = listOf(1, 2, 3, 4, 5, 6, 7),
) {
    fun asQuest() = Quest(id, title, category, description, xp)
}
data class JournalEntry(val note: String = "", val photo: String = "")
data class PlayerState(
    val totalXp: Int = 0, val attributes: Map<String, Int> = emptyMap(),
    val history: Map<String, Set<String>> = emptyMap(), val dailySets: Map<String, List<String>> = emptyMap(),
    val rewards: Map<String, Map<String, Int>> = emptyMap(), val unlockedAchievements: Set<String> = emptySet(),
    val difficulty: String = "standard", val customTasks: List<CustomTask> = emptyList(),
    val journal: Map<String, Map<String, JournalEntry>> = emptyMap(),
    val weeklyGoals: Map<String, String> = emptyMap(), val weeklyDone: Set<String> = emptySet(),
    val restDays: Set<String> = emptySet(), val completedChains: Set<String> = emptySet(),
    val reminderEnabled: Boolean = false, val reminderMinute: Int = 20 * 60, val pinHash: String = "",
)
data class LevelProgress(val level: Int, val currentXp: Int, val neededXp: Int, val rank: String)
data class Achievement(
    val id: String, val title: String, val description: String, val metric: String,
    val thresholds: List<Int>, val secret: Boolean = false,
)
data class AchievementUnlock(val achievement: Achievement, val tier: Int)
data class QuestChain(val id: String, val title: String, val category: String, val days: Int, val reward: Int)
data class ToggleResult(
    val state: PlayerState, val completed: Boolean, val leveledUp: Boolean,
    val dailyBonusReceived: Boolean, val reward: Int, val newUnlocks: List<AchievementUnlock>,
)

object GameEngine {
    const val DAILY_QUEST_COUNT = 6
    const val DAILY_BONUS = 40
    const val WEEKLY_BONUS = 100
    val tierNames = listOf("БРОНЗА", "СЕРЕБРО", "ЗОЛОТО", "ПЛАТИНА")
    val categoryLabels = mapOf(
        "body" to "ТЕЛО", "mind" to "РАЗУМ", "discipline" to "ДИСЦИПЛИНА",
        "recovery" to "ВОССТАНОВЛЕНИЕ", "social" to "ОТНОШЕНИЯ", "finance" to "ФИНАНСЫ",
        "environment" to "ПОРЯДОК", "creativity" to "ТВОРЧЕСТВО",
    )
    val categoryAttributes = mapOf(
        "body" to "strength", "mind" to "intellect", "discipline" to "discipline", "recovery" to "energy",
        "social" to "empathy", "finance" to "awareness", "environment" to "discipline", "creativity" to "intellect",
    )
    val attributeOrder = listOf("strength", "intellect", "discipline", "energy", "empathy", "awareness")
    val attributeLabels = mapOf(
        "strength" to "Сила", "intellect" to "Интеллект", "discipline" to "Дисциплина",
        "energy" to "Энергия", "empathy" to "Эмпатия", "awareness" to "Осознанность",
    )
    val quests = QuestCatalog.items
    val questById = quests.associateBy { it.id }
    init { require(quests.size == 248 && questById.size == quests.size) }

    val chains = listOf(
        QuestChain("body7", "Семь дней движения", "body", 7, 100),
        QuestChain("mind7", "Неделя знаний", "mind", 7, 100),
        QuestChain("discipline14", "Две недели воли", "discipline", 14, 180),
        QuestChain("recovery7", "Семь дней ресурса", "recovery", 7, 100),
        QuestChain("social7", "Неделя связи", "social", 7, 100),
        QuestChain("finance7", "Финансовое внимание", "finance", 7, 100),
        QuestChain("order7", "Семь дней порядка", "environment", 7, 100),
        QuestChain("create7", "Неделя созидания", "creativity", 7, 100),
    )
    val achievements = listOf(
        Achievement("path", "Путь охотника", "Выполняй любые задания", "completed", listOf(1, 10, 50, 200)),
        Achievement("streak", "Нерушимая воля", "Поддерживай серию полных дней", "streak", listOf(1, 3, 7, 30)),
        Achievement("level", "Восхождение", "Повышай уровень игрока", "level", listOf(2, 5, 10, 20)),
        Achievement("perfect", "Безупречный день", "Закрывай все шесть заданий дня", "perfect", listOf(1, 3, 10, 30)),
        Achievement("body", "Предел тела", "Задания направления «Тело»", "body", listOf(5, 25, 75, 200)),
        Achievement("mind", "Архитектор разума", "Задания направления «Разум»", "mind", listOf(5, 25, 75, 200)),
        Achievement("discipline", "Железная дисциплина", "Задания направления «Дисциплина»", "discipline", listOf(5, 25, 75, 200)),
        Achievement("recovery", "Источник силы", "Не забывай о восстановлении", "recovery", listOf(3, 15, 50, 150)),
        Achievement("social", "Связь миров", "Развивай отношения", "social", listOf(1, 10, 30, 75)),
        Achievement("finance", "Хранитель ресурсов", "Финансовые задания", "finance", listOf(1, 10, 30, 75)),
        Achievement("order", "Властелин порядка", "Наводи порядок", "environment", listOf(3, 15, 50, 150)),
        Achievement("creativity", "Создатель", "Творческие задания", "creativity", listOf(1, 10, 30, 75)),
        Achievement("xp", "Накопленная мощь", "Получай опыт за реальные действия", "xp", listOf(100, 500, 2000, 7500)),
        Achievement("journal", "Летописец", "Секретная награда за записи результатов", "journal", listOf(1, 7, 30, 100), true),
        Achievement("boss", "Победитель недели", "Секретная награда за недельные цели", "boss", listOf(1, 4, 12, 52), true),
        Achievement("personal", "Свой путь", "Секретная награда за личные задания", "custom", listOf(1, 10, 30, 100), true),
        Achievement("variety", "Мастер всех стихий", "Секретная награда за разные направления", "variety", listOf(2, 4, 6, 8), true),
        Achievement("chains", "Неразрывная цепь", "Секретная награда за цепочки", "chains", listOf(1, 2, 4, 8), true),
    )

    fun levelProgress(totalXp: Int): LevelProgress {
        var remaining = totalXp.coerceAtLeast(0); var level = 1
        while (true) {
            val needed = 100 + (level - 1) * 25
            if (remaining < needed) return LevelProgress(level, remaining, needed, rank(level))
            remaining -= needed; level++
        }
    }
    fun level(totalXp: Int): Int = levelProgress(totalXp).level
    fun rank(level: Int): String = when { level >= 25 -> "S"; level >= 17 -> "A"; level >= 12 -> "B"; level >= 8 -> "C"; level >= 4 -> "D"; else -> "E" }

    fun dailyQuests(day: LocalDate, level: Int, previousIds: Set<String> = emptySet()): List<Quest> {
        val random = Random("sistema:$day".hashCode().toLong())
        val rotating = listOf("recovery", "social", "finance", "environment", "creativity").shuffled(random)
        val categories = listOf("body", "mind", "discipline") + rotating.take(3)
        val selected = mutableListOf<Quest>()
        for (category in categories) {
            val eligible = quests.filter { it.category == category && it.minLevel <= level }
            selected += eligible.filter { it.id !in previousIds }.ifEmpty { eligible }.shuffled(random).first()
        }
        return selected.shuffled(random)
    }
    fun getDailyQuests(state: PlayerState, day: LocalDate): PlayerState {
        val key = day.toString(); val existing = state.dailySets[key]
        if (existing != null && existing.size == 6 && existing.distinct().size == 6 && existing.all { it in questById }) return state
        val previous = state.dailySets[day.minusDays(1).toString()].orEmpty().toSet()
        val ids = dailyQuests(day, level(state.totalXp), previous).map { it.id }
        return state.copy(dailySets = state.dailySets + (key to ids))
    }
    fun dailyQuestList(state: PlayerState, day: LocalDate): List<Quest> {
        val ids = state.dailySets[day.toString()]
        return if (ids != null && ids.size == 6 && ids.all { it in questById }) ids.map { questById.getValue(it) } else dailyQuests(day, 1)
    }
    fun customDue(state: PlayerState, day: LocalDate): List<CustomTask> = state.customTasks.filter { day.dayOfWeek.value in it.weekdays }
    fun completedToday(state: PlayerState, day: LocalDate): Set<String> =
        state.history[day.toString()].orEmpty().intersect(dailyQuestList(state, day).map { it.id }.toSet())
    fun isDayComplete(state: PlayerState, day: LocalDate): Boolean = day.toString() in state.restDays || completedToday(state, day).size == 6
    fun adjustedReward(state: PlayerState, quest: Quest): Int = when (state.difficulty) {
        "light" -> (quest.reward(level(state.totalXp)) * 0.8).toInt().coerceAtLeast(5)
        "challenge" -> (quest.reward(level(state.totalXp)) * 1.25).toInt()
        else -> quest.reward(level(state.totalXp))
    }

    fun toggle(state: PlayerState, questId: String, date: String): ToggleResult {
        val quest = questById[questId] ?: state.customTasks.firstOrNull { it.id == questId }?.asQuest()
            ?: throw IllegalArgumentException("Unknown quest: $questId")
        val day = LocalDate.parse(date); val prepared = getDailyQuests(state, day)
        val oldLevel = level(prepared.totalXp); val oldToday = prepared.history[date].orEmpty()
        val wasComplete = isDayComplete(prepared, day); val completing = questId !in oldToday
        val reward = adjustedReward(prepared, quest); val newToday = oldToday.toMutableSet()
        val attributes = prepared.attributes.toMutableMap(); val rewards = prepared.rewards.toMutableMap()
        val dayRewards = rewards[date].orEmpty().toMutableMap(); var xp = prepared.totalXp; var bonus = false
        if (completing) {
            newToday += questId; xp += reward; attributes[quest.attribute] = attributes[quest.attribute].orZero() + 1
            dayRewards[questId] = reward
        } else {
            if (wasComplete && date !in prepared.restDays) xp -= DAILY_BONUS
            newToday -= questId; xp -= dayRewards[questId] ?: reward
            attributes[quest.attribute] = (attributes[quest.attribute].orZero() - 1).coerceAtLeast(0); dayRewards -= questId
        }
        rewards[date] = dayRewards
        var updated = prepared.copy(totalXp = xp.coerceAtLeast(0), attributes = attributes,
            history = prepared.history + (date to newToday.toSet()), rewards = rewards)
        if (completing && !wasComplete && isDayComplete(updated, day)) {
            updated = updated.copy(totalXp = updated.totalXp + DAILY_BONUS); bonus = true
        }
        updated = applyChains(updated, day)
        val unlocks = syncAchievements(updated, day)
        updated = updated.copy(unlockedAchievements = updated.unlockedAchievements + unlocks.map { "${it.achievement.id}:${it.tier}" })
        return ToggleResult(updated, completing, level(updated.totalXp) > oldLevel, bonus, reward, unlocks)
    }

    fun toggleRestDay(state: PlayerState, day: LocalDate): PlayerState {
        val key = day.toString()
        return state.copy(restDays = if (key in state.restDays) state.restDays - key else state.restDays + key)
    }
    fun weekKey(day: LocalDate): String = "${day.get(WeekFields.ISO.weekBasedYear())}-W${day.get(WeekFields.ISO.weekOfWeekBasedYear())}"
    fun toggleWeeklyDone(state: PlayerState, day: LocalDate): PlayerState {
        val key = weekKey(day); if (state.weeklyGoals[key].isNullOrBlank()) return state
        val done = key in state.weeklyDone
        return state.copy(totalXp = (state.totalXp + if (done) -WEEKLY_BONUS else WEEKLY_BONUS).coerceAtLeast(0),
            weeklyDone = if (done) state.weeklyDone - key else state.weeklyDone + key)
    }
    fun streak(state: PlayerState, today: LocalDate): Int {
        var cursor = today; var count = 0
        while (isDayComplete(state, cursor)) { count++; cursor = cursor.minusDays(1) }
        return count
    }
    fun perfectDays(state: PlayerState, today: LocalDate): Int = state.history.keys.count { key ->
        runCatching { LocalDate.parse(key) }.getOrNull()?.let { !it.isAfter(today) && key !in state.restDays && isDayComplete(state, it) } == true
    }
    fun allQuests(state: PlayerState): Map<String, Quest> = questById + state.customTasks.associate { it.id to it.asQuest() }
    fun categoryCompleted(state: PlayerState, category: String): Int {
        val all = allQuests(state); return state.history.values.sumOf { it.count { id -> all[id]?.category == category } }
    }
    fun totalCompleted(state: PlayerState): Int {
        val all = allQuests(state); return state.history.values.sumOf { it.count { id -> id in all } }
    }
    fun customCompleted(state: PlayerState): Int {
        val ids = state.customTasks.map { it.id }.toSet(); return state.history.values.sumOf { it.count { id -> id in ids } }
    }
    fun metricValue(state: PlayerState, metric: String, today: LocalDate): Int = when (metric) {
        "completed" -> totalCompleted(state); "streak" -> streak(state, today); "level" -> level(state.totalXp)
        "perfect" -> perfectDays(state, today); "xp" -> state.totalXp; "journal" -> state.journal.values.sumOf { it.size }
        "boss" -> state.weeklyDone.size; "custom" -> customCompleted(state)
        "variety" -> state.history.values.flatten().mapNotNull { allQuests(state)[it]?.category }.distinct().size
        "chains" -> state.completedChains.size; else -> categoryCompleted(state, metric)
    }
    fun syncAchievements(state: PlayerState, today: LocalDate): List<AchievementUnlock> {
        val unlocked = mutableListOf<AchievementUnlock>()
        for (achievement in achievements) {
            val value = metricValue(state, achievement.metric, today)
            achievement.thresholds.forEachIndexed { index, threshold ->
                val tier = index + 1
                if (value >= threshold && "${achievement.id}:$tier" !in state.unlockedAchievements && unlocked.none { it.achievement.id == achievement.id && it.tier == tier })
                    unlocked += AchievementUnlock(achievement, tier)
            }
        }
        return unlocked
    }
    fun achievementTier(state: PlayerState, achievement: Achievement): Int = (1..4).count { "${achievement.id}:$it" in state.unlockedAchievements }
    fun chainProgress(state: PlayerState, chain: QuestChain, today: LocalDate): Int {
        var count = 0; var cursor = today
        while (count < chain.days && categoryCompletedOn(state, chain.category, cursor) > 0) { count++; cursor = cursor.minusDays(1) }
        return count
    }
    fun categoryCompletedOn(state: PlayerState, category: String, day: LocalDate): Int {
        val all = allQuests(state); return state.history[day.toString()].orEmpty().count { all[it]?.category == category }
    }
    fun applyChains(state: PlayerState, today: LocalDate): PlayerState {
        var xp = state.totalXp; val done = state.completedChains.toMutableSet()
        for (chain in chains) if (chain.id !in done && chainProgress(state, chain, today) >= chain.days) { done += chain.id; xp += chain.reward }
        return if (xp == state.totalXp) state else state.copy(totalXp = xp, completedChains = done)
    }
    fun weeklyRecommendation(state: PlayerState, today: LocalDate): String {
        val counts = GameEngine.categoryLabels.keys.associateWith { category ->
            (0..6).sumOf { categoryCompletedOn(state, category, today.minusDays(it.toLong())) }
        }
        val weakest = counts.minByOrNull { it.value }?.key ?: "body"
        return "На следующей неделе добавь внимание направлению «${categoryLabels[weakest]}»: сейчас здесь меньше всего действий."
    }
}
private fun Int?.orZero(): Int = this ?: 0
