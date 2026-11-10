package ru.sistema.player

import android.app.Activity
import android.app.AlertDialog
import android.content.res.ColorStateList
import android.graphics.Color
import android.graphics.Typeface
import android.graphics.drawable.GradientDrawable
import android.graphics.drawable.RippleDrawable
import android.os.Bundle
import android.text.Editable
import android.text.TextWatcher
import android.view.Gravity
import android.view.View
import android.view.ViewGroup
import android.view.inputmethod.InputMethodManager
import android.content.Context
import android.widget.Button
import android.widget.EditText
import android.widget.FrameLayout
import android.widget.HorizontalScrollView
import android.widget.LinearLayout
import android.widget.ProgressBar
import android.widget.ScrollView
import android.widget.Space
import android.widget.TextView
import android.widget.Toast
import java.time.LocalDate
import java.time.format.TextStyle
import java.util.Locale

class MainActivity : Activity() {
    private lateinit var store: PlayerStore
    private lateinit var state: PlayerState
    private lateinit var pageContent: FrameLayout
    private lateinit var saveStatus: TextView
    private lateinit var featurePages: FeaturePages
    private lateinit var updater: AppUpdater
    private var currentDate: LocalDate = LocalDate.now()
    private var currentPage = "today"
    private val navButtons = mutableMapOf<String, Button>()
    private var libraryItems: LinearLayout? = null
    private var searchQuery = ""
    private var selectedCategory = "all"

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        store = PlayerStore(this)
        state = store.load()
        updater = AppUpdater(this)
        window.statusBarColor = BG
        window.navigationBarColor = PANEL
        prepareToday()
        featurePages = FeaturePages(this, { state }, { updated ->
            state = updated; store.save(state); ReminderScheduler.schedule(this, state); ProgressWidgetProvider.refresh(this)
        }, { page -> showPage(page) })
        setContentView(createShell())
        showPage("today")
        ReminderScheduler.schedule(this, state)
        if (state.pinHash.isNotEmpty()) showLockPrompt()
        pageContent.postDelayed({ updater.check(false) }, 1200)
    }

    override fun onActivityResult(requestCode: Int, resultCode: Int, data: android.content.Intent?) {
        super.onActivityResult(requestCode, resultCode, data)
        if (resultCode == RESULT_OK) featurePages.handleResult(requestCode, data)
    }

    override fun onResume() {
        super.onResume()
        if (::updater.isInitialized) updater.onResume()
    }

    fun checkForUpdates() = updater.check(true)

    override fun onStart() {
        super.onStart()
        val now = LocalDate.now()
        if (now != currentDate) {
            currentDate = now
            prepareToday()
            if (::pageContent.isInitialized) showPage(currentPage)
        }
    }

    private fun prepareToday() {
        state = GameEngine.getDailyQuests(state, currentDate)
        val unlocks = GameEngine.syncAchievements(state, currentDate)
        state = state.copy(unlockedAchievements = state.unlockedAchievements + unlocks.map { "${it.achievement.id}:${it.tier}" })
        store.save(state)
    }

    private fun showLockPrompt() {
        if (android.os.Build.VERSION.SDK_INT >= 28) {
            val cancellation = android.os.CancellationSignal()
            val prompt = android.hardware.biometrics.BiometricPrompt.Builder(this)
                .setTitle("СИСТЕМА ЗАБЛОКИРОВАНА").setSubtitle("Подтверди личность")
                .setNegativeButton("ВВЕСТИ PIN", mainExecutor) { _, _ -> showPinDialog() }.build()
            prompt.authenticate(cancellation, mainExecutor, object : android.hardware.biometrics.BiometricPrompt.AuthenticationCallback() {
                override fun onAuthenticationError(errorCode: Int, errString: CharSequence) { if (errorCode != 10) showPinDialog() }
                override fun onAuthenticationFailed() { Toast.makeText(this@MainActivity, "Не распознано", Toast.LENGTH_SHORT).show() }
            })
        } else showPinDialog()
    }

    private fun showPinDialog() {
        val input = EditText(this).apply {
            hint = "PIN"; inputType = android.text.InputType.TYPE_CLASS_NUMBER or android.text.InputType.TYPE_NUMBER_VARIATION_PASSWORD
        }
        AlertDialog.Builder(this).setTitle("ВВЕДИ PIN").setView(input).setCancelable(false)
            .setPositiveButton("ОТКРЫТЬ") { _, _ ->
                if (FeaturePages.hashPin(input.text.toString()) != state.pinHash) { showPinDialog() }
            }.setNegativeButton("ВЫЙТИ") { _, _ -> finish() }.show()
    }

    private fun createShell(): View {
        val root = LinearLayout(this).apply {
            orientation = LinearLayout.VERTICAL
            setBackgroundColor(BG)
        }
        root.setOnApplyWindowInsetsListener { view, insets ->
            view.setPadding(0, insets.systemWindowInsetTop, 0, insets.systemWindowInsetBottom)
            insets
        }
        root.addView(createHeader())
        pageContent = FrameLayout(this)
        root.addView(pageContent, LinearLayout.LayoutParams(ViewGroup.LayoutParams.MATCH_PARENT, 0, 1f))
        root.addView(createNavigation())
        return root
    }

    private fun createHeader(): View {
        val row = LinearLayout(this).apply {
            orientation = LinearLayout.HORIZONTAL
            gravity = Gravity.CENTER_VERTICAL
            setPadding(dp(18), dp(9), dp(18), dp(9))
            setBackgroundColor(BG)
        }
        row.addView(RuneView(this), LinearLayout.LayoutParams(dp(39), dp(39)))
        val titles = vertical(0).apply { setPadding(dp(10), 0, 0, 0) }
        titles.addView(label("СИСТЕМА", 18, TEXT, true).apply { letterSpacing = 0.14f })
        titles.addView(label("PERSONAL ASCENSION", 8, ACCENT, true).apply { letterSpacing = 0.12f })
        row.addView(titles, LinearLayout.LayoutParams(0, ViewGroup.LayoutParams.WRAP_CONTENT, 1f))
        saveStatus = label("●  СОХРАНЕНО", 8, GREEN, true).apply { letterSpacing = 0.06f }
        row.addView(saveStatus)
        return row
    }

    private fun createNavigation(): View {
        val nav = LinearLayout(this).apply {
            orientation = LinearLayout.HORIZONTAL
            gravity = Gravity.CENTER
            setPadding(dp(7), dp(7), dp(7), dp(8))
            background = rounded(PANEL, BORDER, 0)
        }
        listOf(
            "today" to "СЕГОДНЯ", "goals" to "ЦЕЛИ", "library" to "КАТАЛОГ",
            "achievements" to "НАГРАДЫ", "more" to "ЕЩЁ",
        ).forEach { (key, title) ->
            val button = Button(this).apply {
                text = title
                textSize = 9f
                letterSpacing = 0.02f
                setTypeface(typeface, Typeface.BOLD)
                minHeight = dp(44)
                minimumHeight = dp(44)
                setPadding(dp(2), 0, dp(2), 0)
                setOnClickListener { showPage(key) }
                contentDescription = "Открыть раздел $title"
            }
            navButtons[key] = button
            nav.addView(button, LinearLayout.LayoutParams(0, dp(45), 1f).apply {
                marginStart = dp(2); marginEnd = dp(2)
            })
        }
        return nav
    }

    private fun showPage(page: String) {
        currentPage = page
        navButtons.forEach { (key, button) ->
            val active = key == page
            button.setTextColor(if (active) ACCENT else MUTED)
            button.background = ripple(if (active) ACCENT_DARK else PANEL, if (active) ACCENT_DIM else BORDER, 8)
        }
        pageContent.removeAllViews()
        val content = when (page) {
            "library" -> libraryPage()
            "achievements" -> achievementsPage()
            "stats" -> statsPage()
            "goals", "journal", "chains", "settings", "more" -> featurePages.page(page)
            else -> todayPage()
        }
        pageContent.addView(content, FrameLayout.LayoutParams(ViewGroup.LayoutParams.MATCH_PARENT, ViewGroup.LayoutParams.MATCH_PARENT))
    }

    private fun pageScroll(title: String, subtitle: String, badge: String): LinearLayout {
        val scroll = ScrollView(this).apply {
            isFillViewport = true
            clipToPadding = false
            overScrollMode = View.OVER_SCROLL_NEVER
            setBackgroundColor(BG)
        }
        val page = vertical(0).apply { setPadding(dp(16), dp(13), dp(16), dp(24)) }
        scroll.addView(page, ViewGroup.LayoutParams(ViewGroup.LayoutParams.MATCH_PARENT, ViewGroup.LayoutParams.WRAP_CONTENT))
        val top = LinearLayout(this).apply { gravity = Gravity.CENTER_VERTICAL }
        val titles = vertical(0)
        titles.addView(label(title, 23, TEXT, true))
        titles.addView(space(4))
        titles.addView(label(subtitle, 11, MUTED))
        top.addView(titles, LinearLayout.LayoutParams(0, ViewGroup.LayoutParams.WRAP_CONTENT, 1f))
        top.addView(label(badge, 9, GOLD, true).apply {
            gravity = Gravity.CENTER
            setPadding(dp(9), dp(7), dp(9), dp(7))
            background = rounded(Color.rgb(39, 32, 22), Color.rgb(99, 79, 43), 9)
        })
        page.addView(top)
        page.addView(space(15))
        return page
    }

    private fun todayPage(): View {
        val page = pageScroll("ЕЖЕДНЕВНЫЙ ПРОТОКОЛ", "${currentDate.dayOfMonth} ${monthName()} · 6 целей на сегодня", "DAILY / 06")
        page.addView(heroCard())
        page.addView(space(12))
        val daily = GameEngine.dailyQuestList(state, currentDate)
        val done = GameEngine.completedToday(state, currentDate)
        page.addView(metricsRow(
            Triple("ЗАДАНИЙ СЕГОДНЯ", "${done.size} / 6", ACCENT),
            Triple("СЕРИЯ ПОЛНЫХ ДНЕЙ", GameEngine.streak(state, currentDate).toString(), GREEN),
            Triple("СТУПЕНЕЙ ОТКРЫТО", "${state.unlockedAchievements.size} / 72", PURPLE),
        ))
        page.addView(space(20))
        val heading = LinearLayout(this)
        heading.addView(label("ЗАДАНИЯ НА СЕГОДНЯ", 12, TEXT, true), LinearLayout.LayoutParams(0, ViewGroup.LayoutParams.WRAP_CONTENT, 1f))
        heading.addView(label("+40 XP ЗА ПОЛНЫЙ ДЕНЬ", 8, ACCENT, true))
        page.addView(heading)
        page.addView(space(8))
        daily.forEachIndexed { index, quest -> page.addView(questCard(quest, index + 1, quest.id in done, true)); page.addView(space(10)) }
        if (GameEngine.isDayComplete(state, currentDate)) {
            page.addView(label("ПОЛНЫЙ ДЕНЬ ЗАВЕРШЁН  ·  +40 XP ПОЛУЧЕН", 11, ACCENT, true).apply {
                gravity = Gravity.CENTER; setPadding(dp(12), dp(15), dp(12), dp(15))
                background = rounded(CARD_DONE, Color.rgb(45, 129, 144), 12)
            })
        } else {
            page.addView(label("Действуй в реальной жизни и отмечай результат честно.\nСложность растёт постепенно вместе с тобой.", 11, MUTED).apply {
                gravity = Gravity.CENTER; setLineSpacing(dp(4).toFloat(), 1f)
            })
        }
        return page.parent as View
    }

    private fun heroCard(): View {
        val progress = GameEngine.levelProgress(state.totalXp)
        val card = vertical(17).apply { background = gradient() }
        card.addView(label("ПРОФИЛЬ ИГРОКА  /  АКТИВЕН", 9, ACCENT, true).apply { letterSpacing = 0.12f })
        card.addView(space(12))
        val body = LinearLayout(this).apply { gravity = Gravity.CENTER_VERTICAL }
        val levelColumn = vertical(0)
        levelColumn.addView(label("УРОВЕНЬ", 9, MUTED, true))
        levelColumn.addView(label(progress.level.toString(), 47, TEXT).apply {
            typeface = Typeface.create("sans-serif-light", Typeface.NORMAL); includeFontPadding = false
        })
        body.addView(levelColumn)
        val xpColumn = vertical(0).apply { setPadding(dp(20), 0, 0, 0) }
        xpColumn.addView(label("${state.totalXp} XP", 18, TEXT, true))
        xpColumn.addView(label("ОБЩИЙ ОПЫТ", 8, MUTED, true).apply { letterSpacing = 0.1f })
        xpColumn.addView(space(10))
        val bar = progressBar(progress.neededXp, progress.currentXp, ACCENT)
        xpColumn.addView(bar, LinearLayout.LayoutParams(ViewGroup.LayoutParams.MATCH_PARENT, dp(6)))
        xpColumn.addView(space(6))
        xpColumn.addView(label("${progress.currentXp} / ${progress.neededXp} XP до цели", 10, MUTED))
        body.addView(xpColumn, LinearLayout.LayoutParams(0, ViewGroup.LayoutParams.WRAP_CONTENT, 1f))
        val rank = vertical(0).apply { gravity = Gravity.CENTER_HORIZONTAL }
        rank.addView(label(progress.rank, 29, ACCENT, true).apply {
            gravity = Gravity.CENTER; background = diamondLike()
        }, LinearLayout.LayoutParams(dp(58), dp(58)))
        rank.addView(space(5)); rank.addView(label("РАНГ", 8, MUTED, true))
        body.addView(rank)
        card.addView(body)
        return card
    }

    private fun metricsRow(vararg metrics: Triple<String, String, Int>): View {
        val row = LinearLayout(this).apply { isBaselineAligned = false }
        metrics.forEachIndexed { index, metric ->
            val card = vertical(12).apply { background = rounded(CARD, BORDER, 12) }
            card.addView(label(metric.first, 7, MUTED, true).apply { letterSpacing = 0.05f; maxLines = 2 })
            card.addView(space(7))
            card.addView(label(metric.second, 21, metric.third, true))
            row.addView(card, LinearLayout.LayoutParams(0, dp(82), 1f).apply {
                if (index > 0) marginStart = dp(7)
            })
        }
        return row
    }

    private fun questCard(quest: Quest, number: Int, done: Boolean, actionable: Boolean): View {
        val level = GameEngine.level(state.totalXp)
        val color = categoryColor(quest.category)
        val card = vertical(15).apply {
            background = rounded(if (done) CARD_DONE else CARD, if (done) Color.rgb(45, 129, 144) else BORDER, 15)
        }
        val header = LinearLayout(this).apply { gravity = Gravity.TOP }
        header.addView(label(String.format(Locale.US, "%02d", number), 12, color, true).apply {
            gravity = Gravity.CENTER; background = rounded(Color.rgb(17, 31, 45), color, 10)
        }, LinearLayout.LayoutParams(dp(42), dp(44)))
        val text = vertical(0).apply { setPadding(dp(12), 0, 0, 0) }
        text.addView(label("${GameEngine.categoryLabels[quest.category]}  /  ИЗМЕРИМЫЙ РЕЗУЛЬТАТ", 7, color, true).apply { letterSpacing = 0.06f })
        text.addView(space(4))
        text.addView(label(quest.title, 16, TEXT, true))
        text.addView(space(6))
        text.addView(label(quest.scaledDescription(level, state.difficulty), 12, LIGHT_MUTED).apply { setLineSpacing(dp(3).toFloat(), 1f) })
        header.addView(text, LinearLayout.LayoutParams(0, ViewGroup.LayoutParams.WRAP_CONTENT, 1f))
        card.addView(header)
        card.addView(space(13))
        val footer = LinearLayout(this).apply { gravity = Gravity.CENTER_VERTICAL }
        val rewards = vertical(0)
        rewards.addView(label("+${GameEngine.adjustedReward(state, quest)} XP", 13, ACCENT, true))
        rewards.addView(label("+1 ${quest.attributeLabel.uppercase(Locale("ru"))}", 8, MUTED, true))
        footer.addView(rewards, LinearLayout.LayoutParams(0, ViewGroup.LayoutParams.WRAP_CONTENT, 1f))
        if (actionable) {
            footer.addView(Button(this).apply {
                setText(if (done) "✓  ГОТОВО" else "ВЫПОЛНИТЬ")
                textSize = 10f; setTypeface(typeface, Typeface.BOLD)
                setTextColor(if (done) BG else ACCENT)
                background = ripple(if (done) ACCENT else Color.rgb(14, 43, 59), if (done) ACCENT else ACCENT_DIM, 9)
                minHeight = dp(46); minimumHeight = dp(46)
                setPadding(dp(14), 0, dp(14), 0)
                contentDescription = if (done) "Отменить: ${quest.title}" else "Выполнить: ${quest.title}"
                setOnClickListener { onQuestClicked(quest) }
            }, LinearLayout.LayoutParams(ViewGroup.LayoutParams.WRAP_CONTENT, dp(46)))
        } else {
            footer.addView(label(if (level < quest.minLevel) "УРОВЕНЬ ${quest.minLevel}" else "ДОСТУПНО", 9, if (level < quest.minLevel) GOLD else GREEN, true).apply {
                setPadding(dp(8), dp(8), dp(8), dp(8))
            })
        }
        card.addView(footer)
        return card
    }

    private fun libraryPage(): View {
        val page = pageScroll("БИБЛИОТЕКА ЗАДАНИЙ", "248 конкретных действий · 8 направлений", "248 QUEST")
        val search = EditText(this).apply {
            setText(searchQuery); hint = "Найти действие или направление…"
            textSize = 13f; setTextColor(TEXT); setHintTextColor(MUTED)
            setSingleLine(true); setPadding(dp(15), 0, dp(15), 0)
            background = rounded(CARD_ELEVATED, BORDER_LIGHT, 11)
            addTextChangedListener(object : TextWatcher {
                override fun beforeTextChanged(s: CharSequence?, start: Int, count: Int, after: Int) {}
                override fun onTextChanged(s: CharSequence?, start: Int, before: Int, count: Int) {}
                override fun afterTextChanged(s: Editable?) { searchQuery = s?.toString().orEmpty(); renderLibrary() }
            })
        }
        page.addView(search, LinearLayout.LayoutParams(ViewGroup.LayoutParams.MATCH_PARENT, dp(48)))
        page.addView(space(11))
        val filterScroll = HorizontalScrollView(this).apply { isHorizontalScrollBarEnabled = false }
        val filters = LinearLayout(this)
        val categories = listOf("all" to "ВСЕ") + GameEngine.categoryLabels.map { it.key to it.value }
        categories.forEach { (key, title) ->
            filters.addView(Button(this).apply {
                text = title; textSize = 8f; setTypeface(typeface, Typeface.BOLD)
                setTextColor(if (key == selectedCategory) BG else MUTED)
                background = ripple(if (key == selectedCategory) ACCENT else CARD, BORDER, 8)
                minHeight = dp(36); minimumHeight = dp(36); setPadding(dp(11), 0, dp(11), 0)
                setOnClickListener { selectedCategory = key; showPage("library") }
            }, LinearLayout.LayoutParams(ViewGroup.LayoutParams.WRAP_CONTENT, dp(36)).apply { marginEnd = dp(6) })
        }
        filterScroll.addView(filters)
        page.addView(filterScroll)
        page.addView(space(14))
        libraryItems = vertical(0)
        page.addView(libraryItems)
        renderLibrary()
        return page.parent as View
    }

    private fun renderLibrary() {
        val container = libraryItems ?: return
        container.removeAllViews()
        val query = searchQuery.trim().lowercase(Locale("ru"))
        val filtered = GameEngine.quests.filter { quest ->
            (selectedCategory == "all" || quest.category == selectedCategory) &&
                (query.isEmpty() || quest.title.lowercase(Locale("ru")).contains(query) ||
                    quest.description.lowercase(Locale("ru")).contains(query) ||
                    GameEngine.categoryLabels[quest.category].orEmpty().lowercase(Locale("ru")).contains(query))
        }
        container.addView(label("НАЙДЕНО: ${filtered.size}", 9, MUTED, true))
        container.addView(space(9))
        filtered.forEachIndexed { index, quest ->
            container.addView(questCard(quest, GameEngine.quests.indexOf(quest) + 1, false, false))
            container.addView(space(10))
        }
        if (filtered.isEmpty()) container.addView(label("Ничего не найдено. Измени запрос или фильтр.", 13, MUTED).apply {
            gravity = Gravity.CENTER; setPadding(0, dp(30), 0, dp(30))
        })
    }

    private fun achievementsPage(): View {
        val page = pageScroll("ЗАЛ ДОСТИЖЕНИЙ", "18 путей развития · включая секретные награды", "${state.unlockedAchievements.size} / 72")
        page.addView(label("Полученные ступени остаются навсегда. Каждая следующая требует большего прогресса.", 11, MUTED).apply { setLineSpacing(dp(3).toFloat(), 1f) })
        page.addView(space(14))
        GameEngine.achievements.forEachIndexed { index, achievement ->
            val tier = GameEngine.achievementTier(state, achievement)
            val value = GameEngine.metricValue(state, achievement.metric, currentDate)
            val targetIndex = tier.coerceAtMost(3)
            val target = achievement.thresholds[targetIndex]
            val color = tierColor(tier)
            val card = vertical(15).apply { background = rounded(CARD, if (tier > 0) color else BORDER, 14) }
            val top = LinearLayout(this).apply { gravity = Gravity.CENTER_VERTICAL }
            top.addView(label(if (tier > 0) roman(tier) else "—", 12, color, true).apply {
                gravity = Gravity.CENTER; background = rounded(CARD_ELEVATED, color, 10)
            }, LinearLayout.LayoutParams(dp(48), dp(50)))
            val titles = vertical(0).apply { setPadding(dp(12), 0, 0, 0) }
            titles.addView(label(if (achievement.secret && tier == 0) "СЕКРЕТНАЯ НАГРАДА" else achievement.title, 15, TEXT, true))
            titles.addView(space(3)); titles.addView(label(if (achievement.secret && tier == 0) "Открой, чтобы узнать условие" else achievement.description, 10, MUTED))
            top.addView(titles, LinearLayout.LayoutParams(0, ViewGroup.LayoutParams.WRAP_CONTENT, 1f))
            card.addView(top); card.addView(space(13))
            val tiers = LinearLayout(this).apply { gravity = Gravity.CENTER_VERTICAL }
            (1..4).forEach { step ->
                tiers.addView(View(this).apply { background = rounded(if (step <= tier) tierColor(step) else BORDER, BORDER, 3) },
                    LinearLayout.LayoutParams(0, dp(5), 1f).apply { if (step > 1) marginStart = dp(5) })
            }
            card.addView(tiers); card.addView(space(9))
            val progress = LinearLayout(this)
            progress.addView(label(if (tier == 4) "МАКСИМАЛЬНАЯ СТУПЕНЬ" else "${GameEngine.tierNames[tier]}  ·  ЦЕЛЬ $target", 8, color, true), LinearLayout.LayoutParams(0, ViewGroup.LayoutParams.WRAP_CONTENT, 1f))
            progress.addView(label("${value.coerceAtMost(target)} / $target", 9, TEXT, true))
            card.addView(progress)
            page.addView(card); page.addView(space(10))
        }
        return page.parent as View
    }

    private fun statsPage(): View {
        val page = pageScroll("СТАТИСТИКА ИГРОКА", "Реальные действия превращаются в прогресс", "LOCAL DATA")
        page.addView(metricsRow(
            Triple("ВСЕГО ЗАДАНИЙ", GameEngine.totalCompleted(state).toString(), ACCENT),
            Triple("ПОЛНЫХ ДНЕЙ", GameEngine.perfectDays(state, currentDate).toString(), GREEN),
            Triple("ОБЩИЙ ОПЫТ", state.totalXp.toString(), GOLD),
        ))
        page.addView(space(20)); page.addView(label("ХАРАКТЕРИСТИКИ", 12, TEXT, true)); page.addView(space(9))
        val attributes = vertical(7).apply { background = rounded(CARD, BORDER, 14) }
        GameEngine.attributeOrder.forEachIndexed { index, key ->
            val value = state.attributes[key] ?: 0
            val row = LinearLayout(this).apply { gravity = Gravity.CENTER_VERTICAL; setPadding(dp(5), dp(8), dp(5), dp(8)) }
            row.addView(View(this).apply { background = rounded(attributeColor(key), attributeColor(key), 3) }, LinearLayout.LayoutParams(dp(4), dp(30)))
            row.addView(label(GameEngine.attributeLabels.getValue(key), 12, LIGHT_MUTED).apply { setPadding(dp(12), 0, 0, 0) }, LinearLayout.LayoutParams(0, ViewGroup.LayoutParams.WRAP_CONTENT, 1f))
            row.addView(label(String.format(Locale.US, "%02d", value), 22, attributeColor(key), true))
            attributes.addView(row)
            if (index < GameEngine.attributeOrder.lastIndex) attributes.addView(View(this).apply { setBackgroundColor(BORDER) }, LinearLayout.LayoutParams(ViewGroup.LayoutParams.MATCH_PARENT, dp(1)))
        }
        page.addView(attributes)
        page.addView(space(20)); page.addView(label("АКТИВНОСТЬ · 7 ДНЕЙ", 12, TEXT, true)); page.addView(space(5))
        page.addView(label("Количество выполненных заданий в наборе дня", 10, MUTED)); page.addView(space(12))
        val activity = vertical(10).apply { background = rounded(CARD, BORDER, 14) }
        for (offset in 6 downTo 0) {
            val day = currentDate.minusDays(offset.toLong())
            val count = GameEngine.completedToday(state, day).size
            val row = LinearLayout(this).apply { gravity = Gravity.CENTER_VERTICAL }
            row.addView(label(day.dayOfWeek.getDisplayName(TextStyle.SHORT, Locale("ru")).uppercase(Locale("ru")), 9, if (offset == 0) ACCENT else MUTED, true), LinearLayout.LayoutParams(dp(34), ViewGroup.LayoutParams.WRAP_CONTENT))
            row.addView(progressBar(GameEngine.DAILY_QUEST_COUNT, count, if (count == 6) GREEN else ACCENT), LinearLayout.LayoutParams(0, dp(7), 1f).apply { marginEnd = dp(10) })
            row.addView(label("$count / 6", 10, TEXT, true))
            activity.addView(row)
        }
        page.addView(activity); page.addView(space(16))
        page.addView(label("РЕКОМЕНДАЦИЯ НА НЕДЕЛЮ", 10, GOLD, true))
        page.addView(label(GameEngine.weeklyRecommendation(state, currentDate), 11, LIGHT_MUTED).apply { setPadding(0, dp(7), 0, dp(14)) })
        page.addView(label("●  ДАННЫЕ ХРАНЯТСЯ ТОЛЬКО НА ЭТОМ УСТРОЙСТВЕ", 8, GREEN, true).apply { gravity = Gravity.CENTER })
        return page.parent as View
    }

    private fun onQuestClicked(quest: Quest) {
        val result = GameEngine.toggle(state, quest.id, currentDate.toString())
        state = result.state
        store.save(state)
        ProgressWidgetProvider.refresh(this)
        showPage("today")
        when {
            result.leveledUp -> showLevelUp(result)
            result.newUnlocks.isNotEmpty() -> Toast.makeText(this, "Новая ступень: ${result.newUnlocks.first().achievement.title}", Toast.LENGTH_LONG).show()
            result.dailyBonusReceived -> Toast.makeText(this, "Полный день! Дополнительно +40 XP", Toast.LENGTH_LONG).show()
            result.completed -> Toast.makeText(this, "+${result.reward} XP · ${quest.attributeLabel} +1", Toast.LENGTH_SHORT).show()
            else -> Toast.makeText(this, "Выполнение отменено", Toast.LENGTH_SHORT).show()
        }
    }

    private fun showLevelUp(result: ToggleResult) {
        val bonus = if (result.dailyBonusReceived) "\nПолный день: дополнительно +40 XP." else ""
        AlertDialog.Builder(this)
            .setTitle("УРОВЕНЬ ПОВЫШЕН")
            .setMessage("Ты достиг уровня ${GameEngine.level(state.totalXp)}.$bonus\n\nСложность целей будет расти постепенно.")
            .setPositiveButton("ПРИНЯТЬ") { dialog, _ -> dialog.dismiss() }
            .show()
    }

    private fun vertical(padding: Int): LinearLayout = LinearLayout(this).apply {
        orientation = LinearLayout.VERTICAL
        if (padding > 0) setPadding(dp(padding), dp(padding), dp(padding), dp(padding))
    }
    private fun label(value: String, size: Int, color: Int, bold: Boolean = false): TextView = TextView(this).apply {
        text = value; textSize = size.toFloat(); setTextColor(color); setLineSpacing(0f, 1.05f)
        if (bold) setTypeface(typeface, Typeface.BOLD)
    }
    private fun space(height: Int): Space = Space(this).apply { layoutParams = LinearLayout.LayoutParams(1, dp(height)) }
    private fun rounded(fill: Int, stroke: Int, radius: Int): GradientDrawable = GradientDrawable().apply {
        setColor(fill); if (radius > 0) cornerRadius = dp(radius).toFloat(); setStroke(dp(1), stroke)
    }
    private fun gradient(): GradientDrawable = GradientDrawable(GradientDrawable.Orientation.TL_BR,
        intArrayOf(Color.rgb(18, 35, 56), Color.rgb(7, 14, 25))).apply { cornerRadius = dp(17).toFloat(); setStroke(dp(1), Color.rgb(43, 82, 111)) }
    private fun diamondLike(): GradientDrawable = GradientDrawable().apply {
        shape = GradientDrawable.OVAL; setColor(Color.rgb(16, 40, 56)); setStroke(dp(2), ACCENT_DIM)
    }
    private fun ripple(fill: Int, stroke: Int, radius: Int): RippleDrawable = RippleDrawable(
        ColorStateList.valueOf(ACCENT and 0x44FFFFFF), rounded(fill, stroke, radius), rounded(Color.WHITE, Color.WHITE, radius))
    private fun progressBar(max: Int, value: Int, color: Int): ProgressBar = ProgressBar(this, null, android.R.attr.progressBarStyleHorizontal).apply {
        this.max = max; progress = value.coerceIn(0, max); progressTintList = ColorStateList.valueOf(color)
        progressBackgroundTintList = ColorStateList.valueOf(Color.rgb(34, 50, 72))
    }
    private fun monthName(): String = listOf("января", "февраля", "марта", "апреля", "мая", "июня", "июля", "августа", "сентября", "октября", "ноября", "декабря")[currentDate.monthValue - 1]
    private fun roman(tier: Int): String = listOf("I", "II", "III", "IV")[tier - 1]
    private fun tierColor(tier: Int): Int = when (tier) {
        1 -> Color.rgb(183, 123, 82); 2 -> Color.rgb(169, 183, 201)
        3 -> Color.rgb(240, 195, 92); 4 -> Color.rgb(142, 232, 255)
        else -> Color.rgb(83, 97, 119)
    }
    private fun categoryColor(key: String): Int = when (key) {
        "body" -> ACCENT; "mind" -> PURPLE; "discipline" -> Color.rgb(120, 175, 255)
        "recovery" -> GREEN; "social" -> Color.rgb(240, 166, 196); "finance" -> GOLD
        "environment" -> Color.rgb(140, 197, 184); else -> Color.rgb(217, 160, 255)
    }
    private fun attributeColor(key: String): Int = when (key) {
        "strength" -> ACCENT; "intellect" -> PURPLE; "discipline" -> Color.rgb(120, 175, 255)
        "energy" -> GREEN; "empathy" -> Color.rgb(240, 166, 196); else -> GOLD
    }
    private fun dp(value: Int): Int = (value * resources.displayMetrics.density + 0.5f).toInt()

    companion object {
        private val BG = Color.rgb(5, 8, 15)
        private val PANEL = Color.rgb(8, 14, 24)
        private val CARD = Color.rgb(14, 22, 35)
        private val CARD_ELEVATED = Color.rgb(17, 29, 46)
        private val CARD_DONE = Color.rgb(10, 37, 45)
        private val BORDER = Color.rgb(30, 43, 61)
        private val BORDER_LIGHT = Color.rgb(48, 68, 92)
        private val TEXT = Color.rgb(242, 247, 252)
        private val MUTED = Color.rgb(130, 145, 166)
        private val LIGHT_MUTED = Color.rgb(163, 177, 196)
        private val ACCENT = Color.rgb(111, 231, 255)
        private val ACCENT_DARK = Color.rgb(18, 52, 67)
        private val ACCENT_DIM = Color.rgb(43, 112, 140)
        private val GOLD = Color.rgb(216, 181, 106)
        private val GREEN = Color.rgb(103, 217, 176)
        private val PURPLE = Color.rgb(174, 154, 255)
    }
}
