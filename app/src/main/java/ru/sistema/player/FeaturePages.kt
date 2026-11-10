package ru.sistema.player

import android.app.AlertDialog
import android.app.TimePickerDialog
import android.content.Context
import android.content.Intent
import android.content.pm.PackageManager
import android.graphics.Color
import android.graphics.Typeface
import android.graphics.drawable.GradientDrawable
import android.net.Uri
import android.os.Bundle
import android.text.InputType
import android.view.Gravity
import android.view.View
import android.view.ViewGroup
import android.widget.Button
import android.widget.CheckBox
import android.widget.EditText
import android.widget.LinearLayout
import android.widget.ScrollView
import android.widget.TextView
import android.widget.Toast
import java.security.MessageDigest
import java.time.LocalDate
import java.util.UUID

class FeaturePages(
    private val activity: MainActivity,
    private val currentState: () -> PlayerState,
    private val updateState: (PlayerState) -> Unit,
    private val navigate: (String) -> Unit,
) {
    var pendingPhotoQuest: String? = null
    private var exportData = ""

    fun page(name: String): View = when (name) {
        "goals" -> goalsPage(); "journal" -> journalPage(); "chains" -> chainsPage()
        "settings" -> settingsPage(); else -> morePage()
    }

    private fun base(title: String, subtitle: String): LinearLayout {
        val scroll = ScrollView(activity).apply { isFillViewport = true; overScrollMode = View.OVER_SCROLL_NEVER }
        val page = column(18).apply { setPadding(dp(16), dp(16), dp(16), dp(28)) }
        scroll.addView(page, ViewGroup.LayoutParams(ViewGroup.LayoutParams.MATCH_PARENT, ViewGroup.LayoutParams.WRAP_CONTENT))
        page.addView(text(title, 23, TEXT, true)); page.addView(text(subtitle, 11, MUTED))
        return page
    }

    private fun goalsPage(): View {
        val state = currentState(); val page = base("МОИ ЦЕЛИ", "Личные задачи и один большой результат недели")
        val boss = card(GOLD)
        boss.addView(text("НЕДЕЛЬНЫЙ БОСС  /  +100 XP", 11, GOLD, true))
        val key = GameEngine.weekKey(LocalDate.now())
        val goal = input(state.weeklyGoals[key].orEmpty(), "Например: завершить первую главу проекта")
        boss.addView(goal, match(48))
        boss.addView(button("СОХРАНИТЬ ЦЕЛЬ", ACCENT) {
            val value = goal.text.toString().trim()
            if (value.isNotEmpty()) {
                updateState(state.copy(weeklyGoals = state.weeklyGoals + (key to value))); navigate("goals")
            }
        })
        if (key in state.weeklyDone) boss.addView(text("✓  ПОБЕДА ПОЛУЧЕНА", 12, GREEN, true))
        else if (!state.weeklyGoals[key].isNullOrBlank()) boss.addView(button("ЗАВЕРШИТЬ НЕДЕЛЮ", GREEN) {
            var updated = GameEngine.toggleWeeklyDone(currentState(), LocalDate.now())
            val unlocks = GameEngine.syncAchievements(updated, LocalDate.now())
            updated = updated.copy(unlockedAchievements = updated.unlockedAchievements + unlocks.map { "${it.achievement.id}:${it.tier}" })
            updateState(updated); Toast.makeText(activity, "Недельная цель завершена: +100 XP", Toast.LENGTH_LONG).show(); navigate("goals")
        })
        page.addView(boss)
        page.addView(button("+  СОЗДАТЬ ЛИЧНОЕ ЗАДАНИЕ", ACCENT) { createTaskDialog() })
        page.addView(text("ЛИЧНЫЕ ЗАДАНИЯ", 12, TEXT, true))
        if (state.customTasks.isEmpty()) page.addView(text("Создай действие со своим критерием, наградой и расписанием.", 11, MUTED))
        state.customTasks.forEach { task ->
            val card = card(categoryColor(task.category)); val due = LocalDate.now().dayOfWeek.value in task.weekdays
            val done = task.id in state.history[LocalDate.now().toString()].orEmpty()
            card.addView(text("${GameEngine.categoryLabels[task.category]}  ·  +${task.xp} XP  ·  ${days(task.weekdays)}", 8, categoryColor(task.category), true))
            card.addView(text(task.title, 16, TEXT, true)); card.addView(text(task.description, 11, LIGHT))
            if (due) card.addView(button(if (done) "✓  ГОТОВО" else "ВЫПОЛНИТЬ СЕГОДНЯ", if (done) GREEN else ACCENT) {
                val result = GameEngine.toggle(currentState(), task.id, LocalDate.now().toString())
                updateState(result.state); navigate("goals")
            })
            card.addView(button("УДАЛИТЬ ЗАДАНИЕ", MUTED) {
                AlertDialog.Builder(activity).setTitle("Удалить задание?").setMessage("История выполнений сохранится.")
                    .setPositiveButton("УДАЛИТЬ") { _, _ -> updateState(currentState().copy(customTasks = currentState().customTasks.filterNot { it.id == task.id })); navigate("goals") }
                    .setNegativeButton("ОТМЕНА", null).show()
            })
            page.addView(card)
        }
        return page.parent as View
    }

    private fun createTaskDialog() {
        val form = column(0); form.setPadding(dp(20), dp(8), dp(20), 0)
        val title = input("", "Название")
        val criterion = input("", "Конкретный критерий завершения")
        val xp = input("20", "XP: 5–100").apply { inputType = InputType.TYPE_CLASS_NUMBER }
        val categoryKeys = GameEngine.categoryLabels.keys.toList()
        val category = android.widget.Spinner(activity).apply {
            adapter = android.widget.ArrayAdapter(activity, android.R.layout.simple_spinner_dropdown_item, GameEngine.categoryLabels.values.toList())
        }
        val checks = (1..7).map { CheckBox(activity).apply { text = listOf("ПН", "ВТ", "СР", "ЧТ", "ПТ", "СБ", "ВС")[it - 1]; isChecked = true; setTextColor(TEXT) } }
        val daysRow = LinearLayout(activity); checks.forEach { daysRow.addView(it, LinearLayout.LayoutParams(0, ViewGroup.LayoutParams.WRAP_CONTENT, 1f)) }
        listOf<View>(title, criterion, xp, category, daysRow).forEach { form.addView(it) }
        val scroll = ScrollView(activity); scroll.addView(form)
        AlertDialog.Builder(activity).setTitle("НОВОЕ ЛИЧНОЕ ЗАДАНИЕ").setView(scroll)
            .setPositiveButton("ДОБАВИТЬ") { _, _ ->
                val state = currentState(); val cat = categoryKeys[category.selectedItemPosition]
                if (title.text.isNotBlank() && criterion.text.isNotBlank() && cat in GameEngine.categoryLabels && checks.any { it.isChecked }) {
                    val task = CustomTask("custom:${UUID.randomUUID().toString().take(12)}", title.text.toString().trim(), criterion.text.toString().trim(), cat,
                        xp.text.toString().toIntOrNull()?.coerceIn(5, 100) ?: 20, checks.mapIndexedNotNull { index, box -> if (box.isChecked) index + 1 else null })
                    updateState(state.copy(customTasks = state.customTasks + task)); navigate("goals")
                } else Toast.makeText(activity, "Проверь название, критерий, направление и дни", Toast.LENGTH_LONG).show()
            }.setNegativeButton("ОТМЕНА", null).show()
    }

    private fun journalPage(): View {
        val state = currentState(); val today = LocalDate.now().toString(); val page = base("ДНЕВНИК РЕЗУЛЬТАТОВ", "Заметки и фото подтверждают реальный прогресс")
        val completed = state.history[today].orEmpty().sorted(); val quests = GameEngine.allQuests(state)
        if (completed.isEmpty()) page.addView(text("Выполни задание, чтобы добавить первую запись.", 12, MUTED))
        completed.forEach { id ->
            val quest = quests[id] ?: return@forEach; val entry = state.journal[today]?.get(id) ?: JournalEntry()
            val card = card(ACCENT_DIM)
            card.addView(text(quest.title, 15, TEXT, true)); card.addView(text(entry.note.ifEmpty { "Запись пока не добавлена" }, 11, LIGHT))
            if (entry.photo.isNotEmpty()) card.addView(text("✓  Фото прикреплено", 10, GREEN, true))
            card.addView(button("ЗАПИСАТЬ РЕЗУЛЬТАТ", ACCENT) { noteDialog(id) })
            card.addView(button("ДОБАВИТЬ ФОТО", PURPLE) {
                pendingPhotoQuest = id
                activity.startActivityForResult(
                    Intent(Intent.ACTION_OPEN_DOCUMENT)
                        .addCategory(Intent.CATEGORY_OPENABLE)
                        .setType("image/*")
                        .addFlags(Intent.FLAG_GRANT_READ_URI_PERMISSION or Intent.FLAG_GRANT_PERSISTABLE_URI_PERMISSION),
                    REQUEST_PHOTO,
                )
            })
            page.addView(card)
        }
        page.addView(text("ИСТОРИЯ ВОСХОЖДЕНИЯ", 12, TEXT, true))
        state.history.keys.sortedDescending().take(30).forEach { day ->
            val ids = state.history[day].orEmpty(); val card = card(BORDER)
            card.addView(text("$day  /  ${ids.size} действий", 10, ACCENT, true))
            card.addView(text(ids.mapNotNull { quests[it]?.title }.joinToString(" · "), 10, MUTED)); page.addView(card)
        }
        return page.parent as View
    }

    private fun noteDialog(id: String) {
        val today = LocalDate.now().toString(); val old = currentState().journal[today]?.get(id) ?: JournalEntry()
        val input = input(old.note, "Что именно получилось? Укажи измеримый результат")
        AlertDialog.Builder(activity).setTitle("РЕЗУЛЬТАТ").setView(input).setPositiveButton("СОХРАНИТЬ") { _, _ ->
            saveJournal(id, JournalEntry(input.text.toString().trim(), old.photo))
        }.setNegativeButton("ОТМЕНА", null).show()
    }

    private fun saveJournal(id: String, entry: JournalEntry) {
        val state = currentState(); val today = LocalDate.now().toString()
        var updated = state.copy(journal = state.journal + (today to (state.journal[today].orEmpty() + (id to entry))))
        val unlocks = GameEngine.syncAchievements(updated, LocalDate.now())
        updated = updated.copy(unlockedAchievements = updated.unlockedAchievements + unlocks.map { "${it.achievement.id}:${it.tier}" })
        updateState(updated); navigate("journal")
    }

    fun handleResult(requestCode: Int, data: Intent?) {
        val result = data ?: return
        val uri = result.data ?: return
        when (requestCode) {
            REQUEST_PHOTO -> pendingPhotoQuest?.let { id ->
                val grantedFlags = result.flags and
                    (Intent.FLAG_GRANT_READ_URI_PERMISSION or Intent.FLAG_GRANT_WRITE_URI_PERMISSION)
                if (grantedFlags and Intent.FLAG_GRANT_READ_URI_PERMISSION != 0) {
                    runCatching { activity.contentResolver.takePersistableUriPermission(uri, grantedFlags) }
                }
                val old = currentState().journal[LocalDate.now().toString()]?.get(id) ?: JournalEntry()
                saveJournal(id, JournalEntry(old.note, uri.toString())); pendingPhotoQuest = null
            }
            REQUEST_EXPORT -> writeUri(uri, exportData)
            REQUEST_IMPORT -> {
                val raw = runCatching { activity.contentResolver.openInputStream(uri)?.bufferedReader()?.use { it.readText() } }.getOrNull() ?: return
                runCatching { PlayerStore(activity).decode(raw) }.onSuccess { updateState(it); navigate("today") }
                    .onFailure { Toast.makeText(activity, "Не удалось прочитать резервную копию", Toast.LENGTH_LONG).show() }
            }
        }
    }

    private fun chainsPage(): View {
        val state = currentState(); val page = base("ЦЕПОЧКИ ЗАДАНИЙ", "Несколько дней подряд · бонус выдаётся один раз")
        GameEngine.chains.forEach { chain ->
            val value = GameEngine.chainProgress(state, chain, LocalDate.now()); val done = chain.id in state.completedChains
            val card = card(if (done) GREEN else BORDER)
            card.addView(text("${GameEngine.categoryLabels[chain.category]}  /  +${chain.reward} XP", 9, categoryColor(chain.category), true))
            card.addView(text(chain.title, 16, TEXT, true)); card.addView(text(if (done) "ЦЕПОЧКА ЗАВЕРШЕНА" else "$value / ${chain.days} дней", 11, if (done) GREEN else MUTED, true))
            page.addView(card)
        }
        return page.parent as View
    }

    private fun morePage(): View {
        val page = base("ЦЕНТР УПРАВЛЕНИЯ", "Все инструменты твоей персональной Системы")
        listOf("journal" to "ДНЕВНИК И ИСТОРИЯ", "stats" to "АНАЛИТИКА И ХАРАКТЕРИСТИКИ",
            "chains" to "ЦЕПОЧКИ ЗАДАНИЙ", "settings" to "НАСТРОЙКИ, КОПИИ И PIN").forEach { (key, title) ->
            page.addView(button(title, ACCENT) { navigate(key) })
        }
        page.addView(text(GameEngine.weeklyRecommendation(currentState(), LocalDate.now()), 12, GOLD))
        return page.parent as View
    }

    private fun settingsPage(): View {
        val state = currentState(); val page = base("НАСТРОЙКИ СИСТЕМЫ", "Нагрузка, отдых, уведомления, копии и защита")
        page.addView(text("АДАПТИВНАЯ СЛОЖНОСТЬ", 12, ACCENT, true))
        page.addView(text("Лёгкая: 75% цели и 80% XP · Вызов: 125% цели и XP", 10, MUTED))
        listOf("light" to "ЛЁГКИЙ ДЕНЬ", "standard" to "СТАНДАРТ", "challenge" to "ВЫЗОВ").forEach { (key, title) ->
            page.addView(button((if (state.difficulty == key) "✓  " else "") + title, if (state.difficulty == key) GREEN else ACCENT) {
                updateState(currentState().copy(difficulty = key)); navigate("settings")
            })
        }
        page.addView(text("ВОССТАНОВЛЕНИЕ", 12, GREEN, true))
        page.addView(button(if (LocalDate.now().toString() in state.restDays) "ОТМЕНИТЬ ДЕНЬ ОТДЫХА" else "СЕГОДНЯ — ПЛАНИРУЕМЫЙ ОТДЫХ", GREEN) {
            updateState(GameEngine.toggleRestDay(currentState(), LocalDate.now())); navigate("settings")
        })
        page.addView(text("УМНОЕ НАПОМИНАНИЕ", 12, GOLD, true))
        page.addView(button(if (state.reminderEnabled) "ОТКЛЮЧИТЬ УВЕДОМЛЕНИЕ" else "ВКЛЮЧИТЬ УВЕДОМЛЕНИЕ", GOLD) {
            val updated = currentState().copy(reminderEnabled = !currentState().reminderEnabled)
            if (updated.reminderEnabled && android.os.Build.VERSION.SDK_INT >= 33 &&
                activity.checkSelfPermission(android.Manifest.permission.POST_NOTIFICATIONS) != PackageManager.PERMISSION_GRANTED
            ) {
                activity.requestPermissions(arrayOf(android.Manifest.permission.POST_NOTIFICATIONS), REQUEST_NOTIFICATIONS)
            }
            updateState(updated); ReminderScheduler.schedule(activity, updated); navigate("settings")
        })
        page.addView(button("ВРЕМЯ: ${state.reminderMinute / 60}:${(state.reminderMinute % 60).toString().padStart(2, '0')}", GOLD) {
            TimePickerDialog(activity, { _, hour, minute ->
                val updated = currentState().copy(reminderMinute = hour * 60 + minute)
                updateState(updated); ReminderScheduler.schedule(activity, updated); navigate("settings")
            }, state.reminderMinute / 60, state.reminderMinute % 60, true).show()
        })
        page.addView(text("АВТООБНОВЛЕНИЕ", 12, ACCENT, true))
        page.addView(text("Проверка при запуске · безопасная загрузка из GitHub Releases", 10, MUTED))
        page.addView(button("ПРОВЕРИТЬ ОБНОВЛЕНИЕ", ACCENT) { activity.checkForUpdates() })
        page.addView(text("РЕЗЕРВНЫЕ КОПИИ И ПРИВАТНОСТЬ", 12, PURPLE, true))
        page.addView(button("ЭКСПОРТИРОВАТЬ ПРОГРЕСС", PURPLE) {
            exportData = PlayerStore(activity).encode(currentState())
            activity.startActivityForResult(Intent(Intent.ACTION_CREATE_DOCUMENT).addCategory(Intent.CATEGORY_OPENABLE).setType("application/json").putExtra(Intent.EXTRA_TITLE, "sistema-backup.json"), REQUEST_EXPORT)
        })
        page.addView(button("ИМПОРТИРОВАТЬ КОПИЮ", PURPLE) {
            activity.startActivityForResult(Intent(Intent.ACTION_OPEN_DOCUMENT).addCategory(Intent.CATEGORY_OPENABLE).setType("application/json"), REQUEST_IMPORT)
        })
        page.addView(button(if (state.pinHash.isEmpty()) "УСТАНОВИТЬ PIN" else "ИЗМЕНИТЬ ИЛИ СНЯТЬ PIN", PURPLE) { pinDialog() })
        page.addView(text("PIN потребуется при следующем запуске. На поддерживаемых устройствах также появится биометрическая разблокировка.", 10, MUTED))
        return page.parent as View
    }

    private fun pinDialog() {
        val input = input("", "4–8 цифр; пустое поле снимает защиту").apply { inputType = InputType.TYPE_CLASS_NUMBER or InputType.TYPE_NUMBER_VARIATION_PASSWORD }
        AlertDialog.Builder(activity).setTitle("PIN СИСТЕМЫ").setView(input).setPositiveButton("СОХРАНИТЬ") { _, _ ->
            val pin = input.text.toString()
            if (pin.isEmpty() || pin.length in 4..8 && pin.all(Char::isDigit)) updateState(currentState().copy(pinHash = if (pin.isEmpty()) "" else hashPin(pin)))
            else Toast.makeText(activity, "PIN должен содержать 4–8 цифр", Toast.LENGTH_LONG).show()
        }.setNegativeButton("ОТМЕНА", null).show()
    }

    private fun writeUri(uri: Uri, value: String) {
        runCatching { activity.contentResolver.openOutputStream(uri)?.bufferedWriter()?.use { it.write(value) } }
            .onSuccess { Toast.makeText(activity, "Резервная копия сохранена", Toast.LENGTH_SHORT).show() }
            .onFailure { Toast.makeText(activity, "Не удалось сохранить копию", Toast.LENGTH_LONG).show() }
    }
    private fun days(values: List<Int>): String = values.joinToString(" ") { listOf("ПН", "ВТ", "СР", "ЧТ", "ПТ", "СБ", "ВС")[it - 1] }
    private fun input(value: String, hint: String) = EditText(activity).apply { setText(value); this.hint = hint; setTextColor(TEXT); setHintTextColor(MUTED); textSize = 12f }
    private fun card(stroke: Int) = column(13).apply { background = rounded(CARD, stroke); setPadding(dp(14), dp(10), dp(14), dp(10)) }
    private fun button(value: String, color: Int, action: () -> Unit) = Button(activity).apply {
        text = value; textSize = 10f; setTextColor(color); setTypeface(typeface, Typeface.BOLD); background = rounded(Color.rgb(14, 34, 48), color); setOnClickListener { action() }
    }
    private fun text(value: String, size: Int, color: Int, bold: Boolean = false) = TextView(activity).apply {
        text = value; textSize = size.toFloat(); setTextColor(color); setPadding(0, dp(5), 0, dp(5)); if (bold) setTypeface(typeface, Typeface.BOLD)
    }
    private fun column(padding: Int) = LinearLayout(activity).apply { orientation = LinearLayout.VERTICAL; if (padding > 0) setPadding(dp(padding), dp(padding), dp(padding), dp(padding)) }
    private fun rounded(fill: Int, stroke: Int) = GradientDrawable().apply { setColor(fill); setStroke(dp(1), stroke); cornerRadius = dp(12).toFloat() }
    private fun match(height: Int) = LinearLayout.LayoutParams(ViewGroup.LayoutParams.MATCH_PARENT, dp(height))
    private fun dp(value: Int) = (value * activity.resources.displayMetrics.density + 0.5f).toInt()
    private fun categoryColor(category: String): Int = when (category) {
        "body" -> ACCENT; "mind" -> PURPLE; "discipline" -> BLUE; "recovery" -> GREEN
        "social" -> PINK; "finance" -> GOLD; "environment" -> Color.rgb(140, 197, 184); else -> Color.rgb(217, 160, 255)
    }

    companion object {
        const val REQUEST_PHOTO = 71; const val REQUEST_EXPORT = 72; const val REQUEST_IMPORT = 73
        const val REQUEST_NOTIFICATIONS = 80
        val BG = Color.rgb(5, 8, 15); val CARD = Color.rgb(14, 22, 35); val TEXT = Color.rgb(242, 247, 252)
        val MUTED = Color.rgb(130, 145, 166); val LIGHT = Color.rgb(163, 177, 196); val ACCENT = Color.rgb(111, 231, 255)
        val GREEN = Color.rgb(103, 217, 176); val GOLD = Color.rgb(216, 181, 106); val PURPLE = Color.rgb(174, 154, 255)
        val PINK = Color.rgb(240, 166, 196); val BLUE = Color.rgb(120, 175, 255); val BORDER = Color.rgb(30, 43, 61); val ACCENT_DIM = Color.rgb(43, 112, 140)
        fun hashPin(pin: String): String = MessageDigest.getInstance("SHA-256").digest(pin.toByteArray()).joinToString("") { "%02x".format(it) }
    }
}
