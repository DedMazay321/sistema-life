package ru.sistema.player

import android.content.Context
import org.json.JSONArray
import org.json.JSONObject
import java.time.LocalDate

class PlayerStore(context: Context) {
    private val preferences = context.getSharedPreferences("player_progress", Context.MODE_PRIVATE)
    private val legacyIds = mapOf("body" to "pushups", "mind" to "read", "focus" to "important_first", "recovery" to "walk")

    fun load(): PlayerState = preferences.getString("state", null)?.let { raw ->
        runCatching { decode(raw) }.getOrElse {
            preferences.getString("state_backup", null)?.let { runCatching { decode(it) }.getOrNull() } ?: PlayerState()
        }
    } ?: PlayerState()

    fun decode(raw: String): PlayerState {
        val json = JSONObject(raw)
        val attributesJson = json.optJSONObject("attributes") ?: JSONObject()
        val attributes = GameEngine.attributeOrder.associateWith { attributesJson.optInt(it, 0).coerceAtLeast(0) }
        val customTasks = mutableListOf<CustomTask>()
        val customJson = json.optJSONArray("customTasks") ?: JSONArray()
        for (index in 0 until customJson.length()) {
            val item = customJson.optJSONObject(index) ?: continue
            val id = item.optString("id"); val category = item.optString("category", "discipline")
            if (!id.startsWith("custom:") || id in GameEngine.questById || category !in GameEngine.categoryLabels) continue
            val weekdays = (0 until (item.optJSONArray("weekdays")?.length() ?: 0)).mapNotNull {
                item.optJSONArray("weekdays")?.optInt(it)?.takeIf { day -> day in 1..7 }
            }.distinct().ifEmpty { listOf(1, 2, 3, 4, 5, 6, 7) }
            customTasks += CustomTask(id, item.optString("title"), item.optString("description"), category,
                item.optInt("xp", 20).coerceIn(5, 100), weekdays)
        }
        val customIds = customTasks.map { it.id }.toSet()
        val history = mutableMapOf<String, Set<String>>()
        val historyJson = json.optJSONObject("history") ?: JSONObject()
        for (date in historyJson.keys()) {
            if (!validDate(date)) continue
            history[date] = readStrings(historyJson.optJSONArray(date)).mapTo(mutableSetOf()) { legacyIds[it] ?: it }
                .filterTo(mutableSetOf()) { it in GameEngine.questById || it in customIds }
        }
        val dailySets = mutableMapOf<String, List<String>>()
        val dailyJson = json.optJSONObject("dailySets") ?: JSONObject()
        for (date in dailyJson.keys()) {
            if (!validDate(date)) continue
            val ids = readStrings(dailyJson.optJSONArray(date)).filter { it in GameEngine.questById }.distinct()
            if (ids.size == 6) dailySets[date] = ids
        }
        val rewards = mutableMapOf<String, Map<String, Int>>()
        val rewardsJson = json.optJSONObject("rewards") ?: JSONObject()
        for (date in rewardsJson.keys()) {
            val dayJson = rewardsJson.optJSONObject(date) ?: continue
            val values = mutableMapOf<String, Int>()
            for (id in dayJson.keys()) if (id in GameEngine.questById || id in customIds)
                values[id] = dayJson.optInt(id, 0).coerceAtLeast(0)
            rewards[date] = values
        }
        val journal = mutableMapOf<String, Map<String, JournalEntry>>()
        val journalJson = json.optJSONObject("journal") ?: JSONObject()
        for (date in journalJson.keys()) {
            if (!validDate(date)) continue
            val entriesJson = journalJson.optJSONObject(date) ?: continue
            val entries = mutableMapOf<String, JournalEntry>()
            for (id in entriesJson.keys()) {
                val entry = entriesJson.optJSONObject(id) ?: continue
                entries[id] = JournalEntry(entry.optString("note"), entry.optString("photo"))
            }
            journal[date] = entries
        }
        val validUnlocks = GameEngine.achievements.flatMap { a -> (1..4).map { "${a.id}:$it" } }.toSet()
        val difficulty = json.optString("difficulty", "standard")
        return PlayerState(
            totalXp = json.optInt("totalXp", json.optInt("total_xp", 0)).coerceAtLeast(0), attributes = attributes,
            history = history, dailySets = dailySets, rewards = rewards,
            unlockedAchievements = readStrings(json.optJSONArray("unlockedAchievements")).filterTo(mutableSetOf()) { it in validUnlocks },
            difficulty = if (difficulty in setOf("light", "standard", "challenge")) difficulty else "standard",
            customTasks = customTasks, journal = journal,
            weeklyGoals = readStringMap(json.optJSONObject("weeklyGoals")), weeklyDone = readStrings(json.optJSONArray("weeklyDone")).toSet(),
            restDays = readStrings(json.optJSONArray("restDays")).filterTo(mutableSetOf()) { validDate(it) },
            completedChains = readStrings(json.optJSONArray("completedChains")).filterTo(mutableSetOf()) { id -> GameEngine.chains.any { it.id == id } },
            reminderEnabled = json.optBoolean("reminderEnabled", false), reminderMinute = json.optInt("reminderMinute", 1200).coerceIn(0, 1439),
            pinHash = json.optString("pinHash"),
        )
    }

    fun save(state: PlayerState) {
        val previous = preferences.getString("state", null)
        preferences.edit().putString("state", encode(state)).apply {
            if (previous != null) putString("state_backup", previous)
        }.apply()
    }
    fun encode(state: PlayerState): String {
        val attributes = JSONObject(); GameEngine.attributeOrder.forEach { attributes.put(it, state.attributes[it] ?: 0) }
        val history = JSONObject(); state.history.toSortedMap().forEach { (day, ids) -> history.put(day, JSONArray(ids.sorted())) }
        val daily = JSONObject(); state.dailySets.toSortedMap().forEach { (day, ids) -> daily.put(day, JSONArray(ids)) }
        val rewards = JSONObject(); state.rewards.toSortedMap().forEach { (day, values) ->
            val obj = JSONObject(); values.toSortedMap().forEach { (id, xp) -> obj.put(id, xp) }; rewards.put(day, obj)
        }
        val custom = JSONArray(); state.customTasks.forEach { task -> custom.put(JSONObject().put("id", task.id).put("title", task.title)
            .put("description", task.description).put("category", task.category).put("xp", task.xp).put("weekdays", JSONArray(task.weekdays))) }
        val journal = JSONObject(); state.journal.toSortedMap().forEach { (day, entries) ->
            val obj = JSONObject(); entries.forEach { (id, entry) -> obj.put(id, JSONObject().put("note", entry.note).put("photo", entry.photo)) }
            journal.put(day, obj)
        }
        val weeklyGoals = JSONObject(); state.weeklyGoals.forEach { (key, value) -> weeklyGoals.put(key, value) }
        return JSONObject().put("version", 3).put("totalXp", state.totalXp).put("attributes", attributes).put("history", history)
            .put("dailySets", daily).put("rewards", rewards).put("unlockedAchievements", JSONArray(state.unlockedAchievements.sorted()))
            .put("difficulty", state.difficulty).put("customTasks", custom).put("journal", journal).put("weeklyGoals", weeklyGoals)
            .put("weeklyDone", JSONArray(state.weeklyDone.sorted())).put("restDays", JSONArray(state.restDays.sorted()))
            .put("completedChains", JSONArray(state.completedChains.sorted())).put("reminderEnabled", state.reminderEnabled)
            .put("reminderMinute", state.reminderMinute).put("pinHash", state.pinHash).toString()
    }
    private fun readStrings(array: JSONArray?): List<String> = if (array == null) emptyList() else
        (0 until array.length()).mapNotNull { array.optString(it).takeIf(String::isNotEmpty) }
    private fun readStringMap(obj: JSONObject?): Map<String, String> = if (obj == null) emptyMap() else
        obj.keys().asSequence().associateWith { obj.optString(it) }
    private fun validDate(value: String): Boolean = runCatching { LocalDate.parse(value) }.isSuccess
}
